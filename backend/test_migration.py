"""Legacy imports are repeatable without replaying accepted analytics events."""
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from sqlalchemy import select, func
from database import session_scope, engine_for
from migrate import migrate
from models import Delivery, Outbox
from test_analytics import msg


class MigrationTests(unittest.TestCase):
    def test_import_keeps_ids_acknowledgements_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with closing(sqlite3.connect(root/'events.sqlite3')) as db:
                db.execute('CREATE TABLE deliveries (id INTEGER PRIMARY KEY, received_at TEXT, event TEXT, body_sha256 TEXT, payload TEXT)')
                db.execute('INSERT INTO deliveries VALUES (7, ?, ?, ?, ?)', ('2026-09-25', 'message:user:in', 'hash', json.dumps(msg('m1', 0))))
                db.commit()
            with closing(sqlite3.connect(root/'posthog-destination.sqlite3')) as db:
                db.execute('CREATE TABLE outbox (id TEXT PRIMARY KEY, payload TEXT, sent_at TEXT)')
                db.execute('INSERT INTO outbox VALUES (?, ?, ?)', ('already-sent', '{"event":"message_recorded"}', '2026-09-25'))
                db.commit()
            self.assertEqual(migrate(root)['metrics']['total_messages'], 1)
            self.assertEqual(migrate(root)['legacy_import'], 'already completed')
            with session_scope(root) as session:
                self.assertEqual(session.scalar(select(func.count()).select_from(Delivery)), 1)
                self.assertIsNotNone(session.get(Delivery, 7))
                self.assertEqual(session.get(Outbox, ('destination','already-sent')).sent_at, '2026-09-25')
            engine_for(root).dispose()
