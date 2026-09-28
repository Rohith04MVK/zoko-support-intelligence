import {test} from 'node:test';
import assert from 'node:assert/strict';
import {attentionReasons, assignmentHistory} from './conversation-utils.js';
const c={id:'c',started_at:0,closed_at:null};
const message=(at,direction,sender_kind)=>({conversation_id:'c',at,direction,sender_kind});
test('bot reply does not clear waiting status',()=>assert.deepEqual(attentionReasons(c,[message(1,'incoming','customer'),message(2,'outgoing','automation')],100),['Awaiting human reply']));
test('human reply clears waiting; a follow-up restores it',()=>{const ms=[message(1,'incoming','customer'),message(2,'outgoing','human')];assert.deepEqual(attentionReasons(c,ms,100),[]);assert.deepEqual(attentionReasons(c,[...ms,message(3,'incoming','customer')],100),['Awaiting human reply'])});
test('threshold is strictly over 30 minutes and closed chats excluded',()=>{assert.deepEqual(attentionReasons(c,[],1800),[]);assert.deepEqual(attentionReasons(c,[],1801),['Open over 30 minutes']);assert.deepEqual(attentionReasons({...c,closed_at:10},[],5000),[])});
test('history is chronological and isolated by conversation',()=>assert.deepEqual(assignmentHistory(c,[{conversation_id:'other',at:0},{conversation_id:'c',at:3},{conversation_id:'c',at:1}]).map(a=>a.at),[1,3]));
