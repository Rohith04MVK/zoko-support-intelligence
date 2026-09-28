"""Upgrade schema and explicitly import legacy SQLite files without modifying them.

Stop old receiver/dashboard/worker processes before running this command.
"""
import argparse
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from database import DATA, upgrade, session_scope
from models import Delivery, SendIntent, FeedbackRequest, Outbox, ImportMarker


def legacy_rows(path, query):
    if not path.exists():
        return []
    with closing(sqlite3.connect(f'file:{path}?mode=ro', uri=True)) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute(query)]


def migrate(data_dir=DATA):
    upgrade(data_dir)
    with session_scope(data_dir, write=True) as session:
        if session.get(ImportMarker, 'legacy-v1'):
            return {'legacy_import': 'already completed'}
        for row in legacy_rows(data_dir / 'events.sqlite3', 'SELECT * FROM deliveries ORDER BY id'):
            row['payload'] = json.loads(row['payload'])
            session.add(Delivery(**row))
        for row in legacy_rows(data_dir / 'sends.sqlite3', 'SELECT * FROM sends'):
            agent = json.loads(row.pop('agent'))
            session.add(SendIntent(**row, agent_id=agent['id'], agent_name=agent.get('name'), agent_email=agent.get('email')))
        for row in legacy_rows(data_dir / 'csat.sqlite3', 'SELECT record FROM requests'):
            request = json.loads(row['record'])
            session.add(FeedbackRequest(**{k:v for k,v in request.items() if k in FeedbackRequest.__table__.columns}))
        for path in data_dir.glob('posthog-*.sqlite3'):
            destination = path.stem.removeprefix('posthog-')
            for row in legacy_rows(path, 'SELECT * FROM outbox'):
                row['payload'] = json.loads(row['payload'])
                session.add(Outbox(destination=destination, **row))
        session.flush()
        from analytics import project, summary
        data = project(session)
        session.add(ImportMarker(id='legacy-v1'))
        return {'legacy_import':'completed', 'metrics':summary(data)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=DATA)
    args = parser.parse_args()
    result = migrate(args.data_dir)
    print(json.dumps(result, indent=2))
