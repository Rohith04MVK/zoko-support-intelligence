"""Public FastAPI webhook ingress. No dashboard or OpenAPI routes are exposed."""
import argparse
import asyncio
import hashlib
import json
import secrets
from datetime import datetime, timezone
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from database import DATA, session_scope
from models import Delivery

TOKEN = DATA / 'webhook-token.txt'


def initialize(data_dir=DATA):
    data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    token = data_dir / 'webhook-token.txt'
    if not token.exists():
        # Exclusive creation avoids different secrets on concurrent starts.
        try:
            with token.open('x') as file:
                file.write(secrets.token_urlsafe(32))
            token.chmod(0o600)
        except FileExistsError:
            pass
    return token


def create_app(data_dir=DATA):
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.get('/health')
    def health():
        return {'status':'ok'}

    @app.post('/webhooks/zoko/{token}')
    async def receive(token: str, request: Request):
        expected = (data_dir/'webhook-token.txt').read_text().strip()
        if not secrets.compare_digest(token, expected):
            return JSONResponse({'error':'not found'}, status_code=404)
        try:
            length = request.headers.get('content-length')
            if length is not None and not 0 < int(length) <= 2_000_000:
                return JSONResponse({'error':'body must be between 1 byte and 2 MB'}, status_code=413)
            async def read_body():
                chunks = bytearray()
                async for chunk in request.stream():
                    chunks.extend(chunk)
                    if len(chunks) > 2_000_000:
                        raise OverflowError
                return bytes(chunks)
            body = await asyncio.wait_for(read_body(), timeout=3)
            payload = json.loads(body)
        except OverflowError:
            return JSONResponse({'error':'body too large'}, status_code=413)
        except (ValueError, UnicodeError, TimeoutError):
            return JSONResponse({'error':'invalid JSON body'}, status_code=400)
        def persist():
            with session_scope(data_dir, write=True) as session:
                event = payload.get('event') if isinstance(payload, dict) else None
                session.add(Delivery(received_at=datetime.now(timezone.utc).isoformat(),
                    event=event if isinstance(event,str) else None,
                    body_sha256=hashlib.sha256(body).hexdigest(), payload=payload))
        try:
            from starlette.concurrency import run_in_threadpool
            await run_in_threadpool(persist)
        except SQLAlchemyError:
            return JSONResponse({'error':'storage unavailable; retry later'}, status_code=503)
        return {'received':True}
    return app


app = create_app()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['serve','events','path'])
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--limit', type=int, default=10)
    args = parser.parse_args()
    token = initialize()
    if args.command == 'path':
        print('/webhooks/zoko/' + token.read_text().strip())
    elif args.command == 'events':
        with session_scope() as session:
            rows = session.scalars(select(Delivery).order_by(Delivery.id.desc()).limit(max(1,min(args.limit,100))))
            print(json.dumps([{'delivery_id':r.id,'received_at':r.received_at,'event':r.event,'payload':r.payload} for r in rows],indent=2))
    else:
        import uvicorn
        uvicorn.run(app, host='127.0.0.1', port=args.port, access_log=False)


if __name__ == '__main__':
    main()
