"""Local FastAPI dashboard. Public webhooks run in a separate application."""
import secrets
from pathlib import Path
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from database import DATA, session_scope
from analytics import project, summary
from repository import snapshot
from models import Customer, Agent
from schemas import SendMessage, RequestFeedback
from sending import config, allowed, send
from csat import request_feedback

DIST = Path(__file__).resolve().parent.parent / 'frontend/dist'


def create_app(data_dir=DATA):
    app = FastAPI(title='Zoko Support Intelligence', version='2.0')
    app.state.csrf = secrets.token_urlsafe(32)

    def session_dependency():
        with session_scope(data_dir, write=True) as session:
            yield session

    def require_csrf(x_csrf_token: str = Header(default='')):
        if not secrets.compare_digest(x_csrf_token, app.state.csrf):
            raise HTTPException(403, 'Invalid CSRF token; refresh the dashboard.')

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, error):
        # Do not echo submitted messages or other input back into validation errors.
        return JSONResponse({'error':'Invalid request fields. Check customer, agent, and message.'}, status_code=422)

    @app.exception_handler(HTTPException)
    async def http_error(request, error):
        return JSONResponse({'error':error.detail}, status_code=error.status_code)

    @app.exception_handler(ValueError)
    async def value_error(request, error):
        return JSONResponse({'error':str(error)}, status_code=400)

    @app.exception_handler(RuntimeError)
    async def send_error(request, error):
        return JSONResponse({'error':str(error)}, status_code=502)

    @app.middleware('http')
    async def no_cache(request, call_next):
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        return response

    @app.get('/health')
    def health():
        return {'status':'ok'}

    @app.get('/api/dashboard')
    def dashboard(session: Session = Depends(session_dependency)):
        derived = project(session)
        records = snapshot(session)
        settings = config()
        for customer in records['customers']:
            customer['can_send'] = bool(settings.get('ZOKO_API_KEY')) and allowed(customer.get('phone'), settings)
        return {'metrics':summary(derived), 'csrf':app.state.csrf, **records}

    # Release the projection transaction before an external send. Ledgers use
    # short separate transactions so webhook receipt is not blocked by Zoko I/O.
    def sender(payload):
        with session_scope(data_dir, write=True) as session:
            project(session)
            customer = session.get(Customer, payload.customer_id)
            agent = session.get(Agent, payload.agent_id)
            if not customer or not agent:
                raise ValueError('Select a known customer and sending agent.')
            return customer.phone, {'id':agent.id, 'name':agent.name, 'email':agent.email}, snapshot(session)

    @app.post('/api/send', dependencies=[Depends(require_csrf)])
    def send_message(payload: SendMessage):
        recipient, agent, _ = sender(payload)
        return send(recipient, payload.message, agent=agent, data_dir=data_dir)

    @app.post('/api/csat', dependencies=[Depends(require_csrf)])
    def feedback(payload: RequestFeedback):
        _, _, data = sender(payload)
        conv = next((c for c in data['conversations'] if c['id']==payload.conversation_id), None)
        if not conv or conv['customer_id'] != payload.customer_id:
            raise ValueError('Conversation does not belong to this customer.')
        return request_feedback(data, payload.conversation_id, payload.agent_id, data_dir=data_dir)

    @app.get('/', include_in_schema=False)
    def index():
        if not (DIST/'index.html').exists():
            raise HTTPException(503, 'Build the frontend first: npm run build --prefix frontend')
        return FileResponse(DIST/'index.html')

    app.mount('/assets', StaticFiles(directory=DIST/'assets', check_dir=False), name='assets')
    return app


app = create_app()

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8001)
