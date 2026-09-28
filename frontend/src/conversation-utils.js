export function attentionReasons(conversation, messages, now) {
  if (conversation.closed_at != null) return [];
  const history = messages.filter(m => m.conversation_id === conversation.id);
  const incoming = history.filter(m => m.direction === 'incoming');
  const lastIncoming = Math.max(-Infinity, ...incoming.map(m => m.at));
  const lastHuman = Math.max(-Infinity, ...history.filter(m => m.direction === 'outgoing' && m.sender_kind === 'human').map(m => m.at));
  const reasons = [];
  if (incoming.length && lastIncoming > lastHuman) reasons.push('Awaiting human reply');
  if (now - conversation.started_at > 30 * 60) reasons.push('Open over 30 minutes');
  return reasons;
}
export function assignmentHistory(conversation, assignments) {
  return assignments.filter(a => a.conversation_id === conversation.id).sort((a,b) => a.at-b.at);
}
