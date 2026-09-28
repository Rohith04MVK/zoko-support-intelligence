"""Durable, manually requested feedback; never automatically retry an uncertain send."""
from sqlalchemy import select
from database import session_scope
from models import FeedbackRequest
from repository import record as to_record
import time
from pathlib import Path
from sending import send, SendRejected

DATA = Path(__file__).resolve().parent / 'data'
QUESTION = 'How would you rate your support experience from 1–5? Reply with one number: 1 = very dissatisfied, 5 = very satisfied.'
WINDOW = 24 * 60 * 60


def load_requests(data_dir=DATA):
    with session_scope(data_dir) as session:
        return [to_record(r) for r in session.scalars(select(FeedbackRequest))]


def request_feedback(data, conversation_id, agent_id, settings=None, data_dir=DATA):
    conv = next((c for c in data['conversations'] if c['id'] == conversation_id), None)
    agent = next((a for a in data['agents'] if a['id'] == agent_id), None)
    if not conv or conv['closed_at'] is None or not agent:
        raise ValueError('Select an agent and a closed conversation.')
    customer = next(c for c in data['customers'] if c['id'] == conv['customer_id'])
    peers = [c for c in data['conversations'] if c['customer_id'] == conv['customer_id']]
    if any(c['closed_at'] is None or c['started_at'] > conv['started_at'] for c in peers):
        raise ValueError('Request feedback only for the latest closed conversation, with no open chat.')
    now = time.time()
    record = {'conversation_id': conversation_id, 'customer_id': conv['customer_id'],
              'agent_id': agent_id, 'asked_at': now, 'expires_at': now + WINDOW,
              'status': 'pending', 'message_id': None}
    with session_scope(data_dir, write=True) as session:
        # Claim before I/O; SQLite write transaction serializes competing requests.
        rows = [to_record(r) for r in session.scalars(select(FeedbackRequest))]
        for row in rows:
            if row['conversation_id'] == conversation_id and row['status'] != 'failed':
                raise ValueError('Feedback was already requested or its send status is uncertain. Refresh to check.')
            if (row['customer_id'] == conv['customer_id'] and row['conversation_id'] != conversation_id
                    and row['status'] in ('pending', 'uncertain', 'accepted') and row['expires_at'] > now):
                raise ValueError('This customer already has a recent feedback request. Wait until its 24-hour window ends.')
        session.merge(FeedbackRequest(**record))
    try:
        result = send(customer.get('phone'), QUESTION, settings=settings, agent=agent, data_dir=data_dir)
        record.update(status='accepted', message_id=result.get('message_id'))
    except (ValueError, SendRejected):
        record['status'] = 'failed'
        raise
    except Exception:
        record['status'] = 'uncertain'
        raise
    finally:
        with session_scope(data_dir, write=True) as session:
            session.merge(FeedbackRequest(**record))
    return {'accepted': True, 'message': 'Feedback request accepted by Zoko. Waiting for a rating from 1–5.'}
