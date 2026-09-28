import unittest
from analytics import build, summary


def msg(mid, second, incoming=True, **extra):
    return {'event': 'message:user:in' if incoming else 'message:store:out',
            'id': mid, 'customer': {'id': 'customer'},
            'platformTimestamp': f'2026-09-25T10:00:{second:02d}Z', **extra}


def change(second, agent='a', closed=False):
    return {'event': 'zoko:chat:closed' if closed else 'zoko:chat:assigned',
            'customerId': 'customer', 'eventAt': f'2026-09-25T10:00:{second:02d}Z',
            'agent': {'id': agent, 'email': agent+'@example.test', 'name': agent}}


class AnalyticsTests(unittest.TestCase):
    def test_retries_enrichment_and_order(self):
        start = msg('1', 0)
        plain = msg('2', 5, False)
        rich = {**plain, 'agentEmail': 'a@example.test'}
        rows = [change(10, closed=True), rich, start, change(1), start, plain]
        result = summary(build(rows))
        self.assertEqual(result['total_messages'], 2)
        self.assertEqual(result['frt']['average_seconds'], 5)
        self.assertEqual(result['resolution']['average_seconds'], 10)
        self.assertEqual(result, summary(build(list(reversed(rows)))))

    def test_bot_unknown_and_unanswered(self):
        rows = [msg('1', 0), msg('2', 1, False, appType='automation'), msg('3', 2, False)]
        result = summary(build(rows))
        self.assertIsNone(result['frt']['average_seconds'])
        self.assertIsNone(result['resolution']['median_seconds'])
        self.assertEqual(result['total_messages'], 3)

    def test_reassignment_and_new_conversation(self):
        rows = [msg('1', 0), change(1), change(2), change(3, 'b'), change(3, 'b'),
                msg('2', 4, False, agentEmail='b@example.test'), change(5, 'b', True), msg('3', 6)]
        data = build(rows)
        self.assertEqual(len(data['conversations']), 2)
        self.assertEqual(data['conversations'][0]['reassignments'], 1)
        self.assertIsNone(data['conversations'][1]['closed_at'])
        self.assertEqual(summary(data)['agents'][1]['reassigned_chats_received'], 1)

    def test_missing_history_and_invalid_payload(self):
        data = build([change(1, closed=True), [], {'event': 'message:user:in', 'platformTimestamp': 'bad'}])
        self.assertEqual(len(data['conversations']), 0)
        self.assertEqual(len(data['warnings']), 3)


if __name__ == '__main__':
    unittest.main()

class AttributionTests(unittest.TestCase):
    def test_direct_api_unknown_until_linked(self):
        rows = [msg('1', 0), msg('2', 8, False, appType='direct_api')]
        self.assertEqual(build(rows)['messages'][1]['sender_kind'], 'unknown')
        self.assertIsNone(summary(build(rows))['frt']['average_seconds'])
        linked = build(rows, {'2': {'id':'a','email':'a@example.test','name':'Agent A'}})
        self.assertEqual(linked['messages'][1]['sender_kind'], 'human')
        self.assertEqual(summary(linked)['frt']['average_seconds'], 8)
        self.assertEqual(linked['conversations'][0]['first_response_agent_id'], 'a')
