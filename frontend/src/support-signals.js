// Workload uses current ownership; first-response performance uses the first responder.
export function supportSignals(
  conversations,
  messages,
  agents,
  now,
  targetSeconds,
) {
  const rows = new Map(
    agents.map((a) => [
      a.id,
      { id: a.id, name: a.name || 'Unnamed agent', open: 0, waiting: [] },
    ]),
  );
  rows.set(null, { id: null, name: 'Unassigned', open: 0, waiting: [] });
  const answered = [];
  const overdue = [];
  for (const c of conversations) {
    if (c.first_response_at != null) answered.push(c);
    if (c.closed_at != null) continue;
    const aid = c.assigned_agent_id || null;
    if (!rows.has(aid))
      rows.set(aid, { id: aid, name: 'Unknown agent', open: 0, waiting: [] });
    const row = rows.get(aid);
    row.open++;
    const history = messages.filter(
      (m) => m.conversation_id === c.id && !m.purpose?.startsWith('csat_'),
    );
    const human = Math.max(
      -Infinity,
      ...history
        .filter((m) => m.direction === 'outgoing' && m.sender_kind === 'human')
        .map((m) => m.at),
    );
    const unanswered = history.filter(
      (m) => m.direction === 'incoming' && m.at > human,
    );
    if (unanswered.length)
      row.waiting.push({
        conversation: c,
        seconds: Math.max(0, now - Math.min(...unanswered.map((m) => m.at))),
      });
    if (c.first_response_at == null && now - c.started_at > targetSeconds)
      overdue.push(c);
  }
  const within = answered.filter(
    (c) => c.first_response_at - c.started_at <= targetSeconds,
  ).length;
  return {
    rows: [...rows.values()]
      .map((r) => ({
        ...r,
        waiting: r.waiting.sort((a, b) => b.seconds - a.seconds),
      }))
      .sort((a, b) => b.waiting.length - a.waiting.length || b.open - a.open),
    answered: answered.length,
    within,
    rate: answered.length ? Math.round((100 * within) / answered.length) : null,
    overdue: overdue.sort((a, b) => a.started_at - b.started_at),
    closedUnanswered: conversations.filter(
      (c) => c.closed_at != null && c.first_response_at == null,
    ).length,
  };
}
