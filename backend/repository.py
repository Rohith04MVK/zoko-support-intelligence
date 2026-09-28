"""Persist the deterministic projection and serialize its public representation."""
from sqlalchemy import delete, select
from models import Agent, Customer, Conversation, Message, Assignment, FeedbackResult, FeedbackRequest

TABLES = {'customers': Customer, 'agents': Agent, 'conversations': Conversation,
          'messages': Message, 'assignments': Assignment}


def record(row):
    return {column.key: getattr(row, column.key) for column in row.__table__.columns}


def save_projection(session, data):
    for model in (FeedbackResult, Assignment, Message, Conversation, Customer, Agent):
        session.execute(delete(model))
    for table, model in TABLES.items():
        for index, row in enumerate(data[table]):
            values = {k: v for k, v in row.items() if k in model.__table__.columns}
            if model is Assignment:
                values['id'] = index
            session.add(model(**values))
        session.flush()
    for conv in data['conversations']:
        feedback = conv.get('csat')
        if feedback:
            session.add(FeedbackResult(conversation_id=conv['id'],
                received_at=feedback.get('received_at'), rating=feedback.get('rating'),
                response_message_id=feedback.get('response_message_id'), superseded=feedback.get('superseded', False)))
    session.flush()


def snapshot(session):
    data = {name: [record(r) for r in session.scalars(select(model))] for name, model in TABLES.items()}
    requests = {r.conversation_id: record(r) for r in session.scalars(select(FeedbackRequest))}
    results = {r.conversation_id: record(r) for r in session.scalars(select(FeedbackResult))}
    for conv in data['conversations']:
        feedback = requests.get(conv['id'])
        if feedback:
            feedback.update({k: v for k, v in results.get(conv['id'], {}).items() if v is not None})
        conv['csat'] = feedback
    return data
