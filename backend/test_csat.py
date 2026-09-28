import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from analytics import build, timestamp
from csat import request_feedback, load_requests
from posthog_sync import events_for, enqueue
from sending import SendRejected
from test_analytics import msg, change
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session
from models import Base, Outbox
from database import upgrade
from contextlib import contextmanager

@contextmanager
def initialized_directory():
    with tempfile.TemporaryDirectory() as directory:
        upgrade(Path(directory))
        yield directory



class FeedbackTests(unittest.TestCase):
    def setUp(self):
        self.rows = [msg('start', 0), change(1), msg('reply', 2, False, agentEmail='a@example.test'), change(5, closed=True)]
        self.request = {'conversation_id': 'conversation:start', 'customer_id': 'customer', 'agent_id': 'a',
                        'status': 'accepted', 'asked_at': timestamp('2026-09-25T10:00:06Z'),
                        'expires_at': timestamp('2026-09-26T10:00:06Z'), 'message_id': 'survey'}

    def test_feedback_links_closed_chat_without_changing_support_times(self):
        rows = self.rows + [msg('survey', 7, False), msg('rating', 8, text=' 5 ')]
        data = build(rows + rows[::-1], feedback_requests=[self.request])
        self.assertEqual(len(data['conversations']), 1)
        conv = data['conversations'][0]
        self.assertEqual(conv['csat']['rating'], 5)
        self.assertEqual(conv['frt_seconds'], 2)
        self.assertEqual(conv['resolution_seconds'], 5)
        self.assertTrue(all(m['conversation_id'] == conv['id'] for m in data['messages']))
        self.assertEqual(build(rows[::-1], feedback_requests=[self.request])['conversations'], data['conversations'])
        events = events_for(data, self.request['asked_at'] + 10)
        funnel = [e for e in events if e['event'] in ('conversation_started', 'conversation_closed', 'csat_asked', 'csat_received')]
        self.assertEqual(len(funnel), 4)
        self.assertEqual(len({e['distinct_id'] for e in funnel}), 1)
        self.assertEqual([e['timestamp'] for e in funnel], sorted(e['timestamp'] for e in funnel))
        engine=create_engine('sqlite://')
        Base.metadata.create_all(engine)
        with Session(engine) as session:
            enqueue(session, events); enqueue(session, events)
            self.assertEqual(session.scalar(select(func.count()).select_from(Outbox)), len(events))

    def test_unrelated_customer_normal_text_and_second_rating_are_support(self):
        for extras in ([msg('normal', 8, text='I need help'), msg('rating', 9, text='5')],
                       [msg('invalid', 8, text='5 stars')],
                       [msg('early', 4, text='5')]):
            data = build(self.rows + extras, feedback_requests=[self.request])
            self.assertNotIn('received_at', data['conversations'][0]['csat'])
        data = build(self.rows + [msg('rating', 8, text='5'), msg('again', 9, text='4')], feedback_requests=[self.request])
        self.assertEqual(len(data['conversations']), 2)
        other = msg('other', 8, text='5', customer={'id': 'other'})
        data = build(self.rows + [other], feedback_requests=[self.request])
        self.assertEqual(len(data['conversations']), 2)
        self.assertNotIn('received_at', data['conversations'][0]['csat'])

    def test_expired_failed_and_uncertain_requests_do_not_consume_rating(self):
        for changes in ({'expires_at': self.request['asked_at']+1}, {'status':'failed'}, {'status':'uncertain'}):
            data = build(self.rows + [msg('rating', 8, text='5')], feedback_requests=[{**self.request, **changes}])
            self.assertEqual(len(data['conversations']), 2)
            self.assertNotIn('received_at', data['conversations'][0]['csat'])

    def test_simultaneous_requests_send_only_once(self):
        data = build(self.rows)
        with initialized_directory() as tmp, patch('csat.send', return_value={'message_id':'survey'}) as send:
            def attempt(_):
                try: return request_feedback(data, 'conversation:start', 'a', data_dir=Path(tmp))
                except ValueError: return None
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(attempt, range(2)))
            self.assertEqual(send.call_count, 1)
            self.assertEqual(sum(r is not None for r in results), 1)
            self.assertEqual(load_requests(Path(tmp))[0]['status'], 'accepted')

    def test_uncertain_send_blocks_retry_but_definitive_rejection_can_retry(self):
        for error, state, calls in [(RuntimeError('timeout'), 'uncertain', 1), (SendRejected('429'), 'failed', 2)]:
            with initialized_directory() as tmp, patch('csat.send', side_effect=error) as send:
                for _ in range(2):
                    with self.assertRaises((RuntimeError, ValueError)):
                        request_feedback(build(self.rows), 'conversation:start', 'a', data_dir=Path(tmp))
                self.assertEqual(send.call_count, calls)
                self.assertEqual(load_requests(Path(tmp))[0]['status'], state)

    def test_open_or_older_conversation_rejected_before_send(self):
        with initialized_directory() as tmp, patch('csat.send') as send:
            for rows, cid in [(self.rows[:-1], 'conversation:start'), (self.rows+[msg('new', 8)], 'conversation:start')]:
                with self.assertRaises(ValueError):
                    request_feedback(build(rows), cid, 'a', data_dir=Path(tmp))
            send.assert_not_called()

    def test_real_sending_guardrail_blocks_non_test_number(self):
        data = build(self.rows)
        data['customers'][0]['phone'] = '918888888888'
        with initialized_directory() as tmp, patch('sending.urllib.request.urlopen') as network:
            with self.assertRaises(ValueError):
                request_feedback(data, 'conversation:start', 'a', settings={'ZOKO_API_KEY':'dummy', 'ZOKO_ALLOWED_RECIPIENTS':'919999999999'}, data_dir=Path(tmp))
            network.assert_not_called()
            self.assertEqual(load_requests(Path(tmp))[0]['status'], 'failed')
