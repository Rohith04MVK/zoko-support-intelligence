import unittest
from unittest.mock import patch, MagicMock
from sending import send, allowed

class SendingTests(unittest.TestCase):
    settings={'ZOKO_API_KEY':'dummy-test-key','ZOKO_ALLOWED_RECIPIENTS':'919999999999'}
    def test_reject_before_network(self):
        with patch('sending.urllib.request.urlopen') as network:
            for recipient in ['918888888888',None,'919999999999evil','']:
                with self.assertRaises(ValueError):send(recipient,'hello',self.settings)
            network.assert_not_called()
    def test_empty_allowlist(self):
        self.assertFalse(allowed('919999999999',{}))
    def test_valid_request(self):
        with patch('sending.urllib.request.urlopen') as network:
            network.return_value.__enter__.return_value=MagicMock()
            self.assertTrue(send('+91 99999 99999','test',self.settings)['accepted'])
            self.assertEqual(network.call_count,1)
            self.assertEqual(network.call_args.args[0].get_header('Apikey'),'dummy-test-key')
    def test_invalid_message(self):
        with self.assertRaises(ValueError):send('919999999999',' ',self.settings)

class SenderPersistenceTests(unittest.TestCase):
    def test_response_id_saved_with_selected_agent(self):
        import tempfile, json
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            from database import upgrade, session_scope
            from models import SendIntent
            from sqlalchemy import select
            upgrade(root/'backend/data')
            with patch('sending.ENV',root/'.env'), patch('sending.urllib.request.urlopen') as network:
                network.return_value.__enter__.return_value.read.return_value=b'{"id":"message-123"}'
                send('919999999999','hello',SendingTests.settings,agent={'id':'a','email':'a@example.test','name':'A'})
            with session_scope(root/'backend/data') as session:
                row=session.scalars(select(SendIntent)).one()
            self.assertEqual(row.message_id,'message-123')
            self.assertEqual(row.agent_id,'a')
            self.assertEqual(row.status,'accepted')
