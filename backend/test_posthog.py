import json,unittest
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session
from models import Base, Outbox
from posthog_sync import events_for,enqueue
class PostHogTests(unittest.TestCase):
    def data(self):
        return {'conversations':[{'id':'c','started_at':1,'closed_at':5,'resolution_agent_id':'a','resolution_seconds':4,'frt_seconds':2}],
                'messages':[{'id':'m','at':3,'agent_id':'a','direction':'outgoing','conversation_id':'c','sender_kind':'human','text':'PRIVATE','phone':'PRIVATE'}],
                'agents':[{'id':'a','email':'PRIVATE','name':'PRIVATE'}], 'assignments':[]}
    def test_private_fields_omitted(self):
        self.assertNotIn('PRIVATE',json.dumps(events_for(self.data(),100)))
    def test_idempotent_enqueue(self):
        engine=create_engine('sqlite://')
        Base.metadata.create_all(engine)
        with Session(engine) as c:
            enqueue(c,events_for(self.data(),100));enqueue(c,events_for(self.data(),110))
            self.assertEqual(c.scalar(select(func.count()).select_from(Outbox)),5)
    def test_groups_and_counts(self):
        events=events_for(self.data(),100)
        g=next(e for e in events if e['event']=='$groupidentify')
        self.assertEqual(g['properties']['$group_set']['messages_sent'],1)
        self.assertEqual(g['properties']['$group_set']['conversations_handled'],1)
        self.assertEqual(events[0]['distinct_id'],events[1]['distinct_id'])
