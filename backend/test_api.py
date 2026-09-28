"""Exercise real HTTP contracts and relational projection without external sends."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import select, func, text
from database import upgrade, session_scope, engine_for
from models import Delivery
from receiver import create_app as ingress, initialize
from dashboard import create_app as dashboard
from test_analytics import msg, change
from analytics import build, summary


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name)
        upgrade(self.data)
        self.path = '/webhooks/zoko/' + initialize(self.data).read_text()
        self.receiver = TestClient(ingress(self.data))
        self.dashboard = TestClient(dashboard(self.data))

    def tearDown(self):
        self.receiver.close()
        self.dashboard.close()
        engine_for(self.data).dispose()
        self.tmp.cleanup()

    def test_ingress_projection_and_retries(self):
        rows = [msg('1', 0), change(1), msg('2', 5, False, agentEmail='a@example.test'), change(10, closed=True)]
        for row in rows + rows:
            self.assertEqual(self.receiver.post(self.path, json=row).status_code, 200)
        result = self.dashboard.get('/api/dashboard')
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()['metrics'], summary(build(rows)))
        self.assertEqual(len(result.json()['messages']), 2)
        self.assertEqual(self.dashboard.get('/api/dashboard').json()['metrics'], result.json()['metrics'])
        with session_scope(self.data) as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(Delivery)), 8)
            self.assertEqual(list(session.execute(text('PRAGMA foreign_key_check'))), [])

    def test_invalid_webhooks_and_public_isolation(self):
        self.assertEqual(self.receiver.post('/webhooks/zoko/wrong', json={}).status_code, 404)
        self.assertEqual(self.receiver.post(self.path, content='{').status_code, 400)
        self.assertEqual(self.receiver.post(self.path, content='x'*2_000_001).status_code, 413)
        for path in ['/docs', '/openapi.json', '/api/dashboard']:
            self.assertEqual(self.receiver.get(path).status_code, 404)
        with session_scope(self.data) as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(Delivery)), 0)

    def test_csrf_and_validation_do_not_send(self):
        token = self.dashboard.get('/api/dashboard').json()['csrf']
        with patch('dashboard.send') as send:
            self.assertEqual(self.dashboard.post('/api/send', json={}).status_code, 403)
            self.assertEqual(self.dashboard.post('/api/send', headers={'X-CSRF-Token':token}, json={'customer_id':'x','agent_id':'a','message':' '}).status_code, 422)
            self.assertEqual(self.dashboard.post('/api/send', headers={'X-CSRF-Token':token}, json={'customer_id':'x','agent_id':'a','message':'hello'}).status_code, 400)
            send.assert_not_called()
