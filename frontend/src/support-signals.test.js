import {test} from 'node:test';
import assert from 'node:assert/strict';
import {supportSignals} from './support-signals.js';
const conv=(id,extra={})=>({id,started_at:0,closed_at:null,first_response_at:null,assigned_agent_id:'a',...extra});
const msg=(at,direction='incoming',sender_kind='customer')=>({conversation_id:'c',at,direction,sender_kind});
test('wait uses oldest unanswered message, ignores bots, and follows current owner',()=>{
 const s=supportSignals([conv('c',{assigned_agent_id:'b'})],[msg(5),msg(10),msg(15,'outgoing','automation')],[{id:'a',name:'A'},{id:'b',name:'B'}],100,60);
 assert.equal(s.rows.find(r=>r.id==='b').waiting[0].seconds,95);assert.equal(s.rows.find(r=>r.id==='a').open,0);assert.equal(s.overdue.length,1);
});
test('follow-up waits reset after human reply but do not become first-response breaches',()=>{
 const s=supportSignals([conv('c',{first_response_at:10})],[msg(5),msg(10,'outgoing','human'),msg(50),msg(60)],[],100,20);
 assert.equal(s.rows.find(r=>r.id==='a').waiting[0].seconds,50);assert.equal(s.rate,100);assert.equal(s.overdue.length,0);
});
test('target boundary, closed unanswered exclusions, and unassigned work',()=>{
 const cs=[conv('a',{first_response_at:60,closed_at:70}),conv('b',{first_response_at:61}),conv('c',{assigned_agent_id:null}),conv('d',{closed_at:20})];
 const s=supportSignals(cs,[msg(0)],[],60,60);
 assert.equal(s.rate,50);assert.equal(s.answered,2);assert.equal(s.closedUnanswered,1);assert.equal(s.overdue.length,0);assert.equal(s.rows.find(r=>r.id===null).waiting.length,1);
 assert.equal(supportSignals(cs,[],[],61,60).overdue.length,1);
 assert.equal(supportSignals([],[],[],100,60).rate,null);
});
