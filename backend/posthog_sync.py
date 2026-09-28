"""Durable PostHog outbox. Run once or use --watch for continuous ingestion."""
import argparse
import hashlib
import json
from sqlalchemy import select, func
from sqlalchemy.exc import SQLAlchemyError
from database import session_scope
from models import Outbox
from repository import snapshot
import time
import uuid
import urllib.request
import urllib.error
from datetime import datetime, timezone
from database import DATA
from sending import config


def iso(seconds):
    return datetime.fromtimestamp(seconds, timezone.utc).isoformat()


def event(name, identity, at, properties):
    key = str(uuid.uuid5(uuid.NAMESPACE_URL, 'zoko-support:' + identity))
    return {'uuid': key, 'event': name, 'distinct_id': properties.get('conversation_id') or 'support-system',
            'timestamp': iso(at), 'properties': {'$insert_id': key, 'source': 'support_intelligence', **properties}}


def events_for(data, now):
    result = []
    for c in data['conversations']:
        props = {'conversation_id': c['id']}
        result.append(event('conversation_started', 'start:'+c['id'], c['started_at'], props))
        if c['closed_at'] is not None:
            aid = c['resolution_agent_id']
            result.append(event('conversation_closed', 'close:'+c['id'], c['closed_at'],
                {**props, 'resolution_seconds': c['resolution_seconds'], 'frt_seconds': c['frt_seconds'],
                 **({'$groups': {'agent': aid}, 'agent_id': aid} if aid else {})}))
        feedback = c.get('csat')
        if feedback and feedback['status'] == 'accepted':
            result.append(event('csat_asked', 'csat-asked:'+c['id'], feedback['asked_at'], props))
            if feedback.get('received_at') is not None:
                result.append(event('csat_received', 'csat-received:'+c['id'], feedback['received_at'],
                                    {**props, 'rating': feedback['rating']}))
    for m in data['messages']:
        aid = m.get('agent_id')
        result.append(event('message_recorded', 'message:'+m['id'], m['at'],
            {'message_id': m['id'], 'conversation_id': m['conversation_id'], 'direction': m['direction'],
             'sender_kind': m['sender_kind'], **({'$groups': {'agent': aid}, 'agent_id': aid} if aid else {})}))
    for a in data['agents']:
        aid = a['id']
        sent = [m for m in data['messages'] if m.get('agent_id') == aid and m['direction'] == 'outgoing']
        handled = {m['conversation_id'] for m in sent if m['conversation_id']}
        handled.update(c['id'] for c in data['conversations'] if c['resolution_agent_id'] == aid)
        handled.update(x['conversation_id'] for x in data['assignments'] if x['agent_id'] == aid and x['conversation_id'])
        props = {'name': 'Agent '+aid[:8], 'messages_sent': len(sent), 'conversations_handled': len(handled)}
        version = hashlib.sha256(json.dumps(props, sort_keys=True).encode()).hexdigest()
        result.append(event('$groupidentify', f'group:{aid}:{version}', now,
            {'$group_type': 'agent', '$group_key': aid, '$group_set': props}))
        # Daily group snapshot allows a non-SQL unique-agent trend with a property filter.
        day = datetime.fromtimestamp(now, timezone.utc).date().isoformat()
        result.append(event('agent_activity_snapshot', f'agent:{aid}:{day}:{version}', now,
            {'agent_id': aid, '$groups': {'agent': aid}, **props}))
    return result


def enqueue(session, events, destination='test'):
    for item in events:
        if session.get(Outbox, (destination, item['uuid'])) is None:
            session.add(Outbox(destination=destination, id=item['uuid'], payload=item))
    session.flush()


def sync():
    settings = config()
    key = settings.get('POSTHOG_PROJECT_API_KEY')
    host = settings.get('POSTHOG_HOST','').rstrip('/')
    if not key or host not in ('https://us.i.posthog.com','https://eu.i.posthog.com'):
        raise ValueError('Configure PostHog project key and US/EU ingestion host in .env.')
    from analytics import project
    destination = hashlib.sha256((host+key).encode()).hexdigest()[:16]
    with session_scope(DATA, write=True) as session:
        project(session)
        enqueue(session, events_for(snapshot(session),time.time()), destination)
    with session_scope(DATA) as session:
        rows = list(session.scalars(select(Outbox).where(Outbox.destination==destination, Outbox.sent_at.is_(None)).order_by(Outbox.id).limit(100)))
    if not rows:
        return {'accepted':0,'pending':0}
    payload = {'api_key': key, 'batch': [r.payload for r in rows]}
    if rows:
        request = urllib.request.Request(host+'/batch/', data=json.dumps(payload).encode(),
                                         headers={'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(request,timeout=15) as response:
                body = response.read()
                answer = json.loads(body) if body else {}
                if isinstance(answer,dict) and answer.get('status') in (0,'error'):
                    raise RuntimeError('PostHog rejected ingestion; events remain queued.')
        except urllib.error.HTTPError as error:
            raise RuntimeError(f'PostHog HTTP {error.code}; events remain queued.') from None
        except (urllib.error.URLError,TimeoutError,ValueError):
            raise RuntimeError('PostHog ingestion could not be confirmed; events remain queued.') from None
    with session_scope(DATA, write=True) as session:
        for row in rows:
            session.get(Outbox, (destination,row.id)).sent_at = datetime.now(timezone.utc).isoformat()
        session.flush()
        pending = session.scalar(select(func.count()).select_from(Outbox).where(Outbox.destination==destination,Outbox.sent_at.is_(None)))
    return {'accepted':len(rows),'pending':pending}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--watch',action='store_true')
    args=parser.parse_args()
    while True:
        try: print(json.dumps(sync()),flush=True)
        except (RuntimeError,ValueError,SQLAlchemyError) as error:
            print(str(error),flush=True)
            if not args.watch: raise SystemExit(1)
        if not args.watch: break
        time.sleep(30)
