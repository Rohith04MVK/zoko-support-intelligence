"""Rebuild a deterministic analytics snapshot from the immutable delivery log."""
import json
import statistics
from datetime import datetime
from pathlib import Path

DATA = Path(__file__).resolve().parent / 'data'


def timestamp(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('timestamp requires timezone')
    return result.timestamp()


def build(payloads, attributions=None, feedback_requests=None):
    attributions = attributions or {}
    feedback = {r['conversation_id']: dict(r) for r in (feedback_requests or [])}
    feedback_messages = {r['message_id']: r for r in feedback.values() if r.get('message_id') and r['status'] == 'accepted'}
    customers, agents, messages, changes, warnings = {}, {}, {}, {}, []
    for p in payloads:
        if not isinstance(p, dict):
            warnings.append('Non-object payload skipped')
            continue
        event = p.get('event', '')
        if event not in ('message:user:in', 'message:store:out', 'message:delivery:update',
                         'zoko:chat:assigned', 'zoko:chat:closed'):
            warnings.append('Unsupported event skipped')
            continue
        try:
            at = timestamp(p.get('eventAt') or p.get('platformTimestamp') or '')
        except (ValueError, TypeError, AttributeError):
            warnings.append('Event with invalid timestamp skipped')
            continue
        customer = p.get('customer') or {}
        cid = p.get('customerId') or customer.get('id')
        if cid:
            row = customers.setdefault(cid, {'id': cid, 'name': None, 'phone': None})
            row['name'] = customer.get('name') or p.get('customerName') or row['name']
            row['phone'] = p.get('phone') or p.get('platformSenderId') or row['phone']
        agent = p.get('agent') or {}
        if agent.get('id'):
            agents[agent['id']] = {'id': agent['id'], 'name': agent.get('name'), 'email': agent.get('email')}
        if event in ('message:user:in', 'message:store:out'):
            mid = p.get('id')
            if not mid or not cid:
                warnings.append('Message missing ID/customer skipped')
                continue
            row = messages.setdefault(mid, {'id': mid, 'customer_id': cid, 'at': at,
                'direction': 'incoming' if event == 'message:user:in' else 'outgoing',
                'text': None, 'agent_email': None, 'app_type': None, 'conversation_id': None})
            # Retry payloads can contain additional metadata: retain enriched fields.
            for field, key in [('text', 'text'), ('agent_email', 'agentEmail'), ('app_type', 'appType')]:
                row[field] = p.get(key) or row[field]
        elif event != 'message:delivery:update' and cid:
            key = (event, cid, at, agent.get('id'))
            changes[key] = {'event': event, 'customer_id': cid, 'at': at,
                            'agent_id': agent.get('id')}
    for mid, agent in attributions.items():
        if mid in messages and agent.get('email') and agent.get('id'):
            agents[agent['id']] = agent
            messages[mid]['agent_email'] = agent['email']
    emails = {a['email'].lower(): aid for aid, a in agents.items() if a.get('email')}
    timeline = [(m['at'], 1, m['id'], 'message', m) for m in messages.values()]
    timeline += [(c['at'], 0 if c['event'].endswith('assigned') else 2, str(key), 'change', c)
                 for key, c in changes.items()]
    conversations, active, assigned, assignments = [], {}, {}, []
    for at, _, _, kind, row in sorted(timeline):
        cid = row['customer_id']
        if kind == 'change' and row['event'].endswith('assigned'):
            previous = assigned.get(cid)
            assigned[cid] = row['agent_id']
            conv = active.get(cid)
            reassigned = bool(previous and row['agent_id'] and previous != row['agent_id'])
            assignments.append({**row, 'previous_agent_id': previous,
                                'is_reassignment': reassigned, 'conversation_id': conv['id'] if conv else None})
            if conv:
                conv['assigned_agent_id'] = row['agent_id']
                if reassigned:
                    conv['reassignments'] += 1
            continue
        conv = active.get(cid)
        if kind == 'message':
            # Exact outgoing ID links the survey to the closed chat. Only a bare
            # rating with no new support chat can be consumed as feedback.
            request = feedback_messages.get(row['id']) if row['direction'] == 'outgoing' else None
            if row['direction'] == 'incoming' and conv is None and (row.get('text') or '').strip() in ('1', '2', '3', '4', '5'):
                candidates = [r for r in feedback.values() if r['customer_id'] == cid
                    and r['status'] == 'accepted' and not r.get('received_at') and not r.get('superseded')
                    and r['asked_at'] <= at <= r['expires_at']]
                if len(candidates) == 1:
                    request = candidates[0]
                    request.update(received_at=at, rating=int(row['text'].strip()), response_message_id=row['id'])
            target = next((c for c in conversations if request and c['id'] == request['conversation_id'] and c['closed_at'] is not None), None)
            if target:
                row.update(conversation_id=target['id'], agent_id=request['agent_id'] if row['direction'] == 'outgoing' else None,
                           sender_kind='human' if row['direction'] == 'outgoing' else 'customer',
                           purpose='csat_request' if row['direction'] == 'outgoing' else 'csat_rating')
                continue
            if row['direction'] == 'incoming':
                for r in feedback.values():
                    if r['customer_id'] == cid and r['asked_at'] <= at and not r.get('received_at'):
                        r['superseded'] = True
        if kind == 'message' and row['direction'] == 'incoming' and conv is None:
            conv = {'id': 'conversation:' + row['id'], 'customer_id': cid, 'started_at': at,
                    'closed_at': None, 'first_response_at': None, 'first_response_agent_id': None,
                    'assigned_agent_id': assigned.get(cid), 'resolution_agent_id': None, 'reassignments': 0}
            conversations.append(conv)
            active[cid] = conv
        if kind == 'message':
            row['agent_id'] = emails.get((row['agent_email'] or '').lower())
            row['sender_kind'] = ('customer' if row['direction'] == 'incoming' else
                                  'human' if row['agent_email'] else
                                  'automation' if row['app_type'] == 'enigma' else 'unknown')
            row['conversation_id'] = conv['id'] if conv else None
            if conv and row['direction'] == 'outgoing' and row['sender_kind'] == 'human' and conv['first_response_at'] is None:
                conv['first_response_at'] = at
                conv['first_response_agent_id'] = row['agent_id']
        elif conv:
            conv['closed_at'] = at
            conv['resolution_agent_id'] = row['agent_id'] or conv['assigned_agent_id']
            del active[cid]
        else:
            warnings.append('Closure without observed conversation start excluded from metrics')
    for conv in conversations:
        conv['csat'] = feedback.get(conv['id'])
        conv['frt_seconds'] = None if conv['first_response_at'] is None else conv['first_response_at'] - conv['started_at']
        conv['resolution_seconds'] = None if conv['closed_at'] is None else conv['closed_at'] - conv['started_at']
    return dict(customers=list(customers.values()), agents=list(agents.values()),
                messages=list(messages.values()), conversations=conversations,
                assignments=assignments, warnings=warnings)


def distribution(values):
    values = [v for v in values if v is not None]
    return {'sample_size': len(values), 'average_seconds': statistics.mean(values) if values else None,
            'median_seconds': statistics.median(values) if values else None}


def summary(data):
    convs = data['conversations']
    per_agent = []
    for a in data['agents']:
        aid = a['id']
        per_agent.append({'agent_id': aid, 'name': a['name'],
            'frt': distribution(c['frt_seconds'] for c in convs if c['first_response_agent_id'] == aid),
            'resolution': distribution(c['resolution_seconds'] for c in convs if c['resolution_agent_id'] == aid),
            'reassigned_chats_received': len({x['conversation_id'] for x in data['assignments']
                if x['agent_id'] == aid and x['is_reassignment'] and x['conversation_id']})})
    return {'total_messages': len(data['messages']), 'total_conversations': len(convs),
            'closed_conversations': sum(c['closed_at'] is not None for c in convs),
            'messages_per_customer': {c['id']: sum(m['customer_id'] == c['id'] for m in data['messages']) for c in data['customers']},
            'frt': distribution(c['frt_seconds'] for c in convs),
            'resolution': distribution(c['resolution_seconds'] for c in convs),
            'agents': per_agent, 'warnings': data['warnings']}


def project(session):
    from sqlalchemy import select
    from models import Delivery, SendIntent, FeedbackRequest
    from repository import record, save_projection
    payloads = list(session.scalars(select(Delivery.payload).order_by(Delivery.id)))
    attributions = {r.message_id: {'id': r.agent_id, 'name': r.agent_name, 'email': r.agent_email}
                    for r in session.scalars(select(SendIntent).where(SendIntent.status == 'accepted', SendIntent.message_id.is_not(None)))}
    requests = [record(r) for r in session.scalars(select(FeedbackRequest))]
    data = build(payloads, attributions, requests)
    save_projection(session, data)
    return data


def rebuild():
    from database import session_scope
    with session_scope(DATA, write=True) as session:
        return summary(project(session))


if __name__ == '__main__':
    print(json.dumps(rebuild(), indent=2))
