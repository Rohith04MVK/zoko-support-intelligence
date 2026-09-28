import { test } from 'node:test';
import assert from 'node:assert/strict';
import { responseTrends, followUpPressure } from './team-insights.js';
const day = 86400;
const now = 20 * day;
const c = (id, start, reply = null, close = null) => ({
  id,
  started_at: start,
  first_response_at: reply,
  closed_at: close,
});
test('rolling cohorts use start time, exact boundary appears only in current, medians exclude incomplete outcomes', () => {
  const rows = [
    c('a', 13 * day, 13 * day + 60, 13 * day + 100),
    c('b', 14 * day, 14 * day + 120),
    c('c', 15 * day),
    c('d', 12 * day, 12 * day + 180, 12 * day + 200),
    c('old', 5 * day),
  ];
  const s = responseTrends(rows, now, 60);
  assert.equal(s.current.total, 3);
  assert.equal(s.previous.total, 1);
  assert.equal(s.current.frt, 90);
  assert.equal(s.current.resolution, 100);
  assert.equal(s.current.rate, 50);
  assert.equal(s.previous.rate, 0);
  assert.equal(responseTrends([], now, 60).current.rate, null);
});
test('follow-up queue deduplicates IDs, ignores automation and excludes closed chats and CSAT', () => {
  const m = (id, at, extra = {}) => ({
    id,
    at,
    conversation_id: 'a',
    direction: 'incoming',
    text: id,
    ...extra,
  });
  const rows = [
    m('1', 1),
    m('2', 2),
    m('2', 2),
    m('bot', 3, { direction: 'outgoing', sender_kind: 'automation' }),
    m('feedback', 4, { purpose: 'csat_rating' }),
  ];
  const result = followUpPressure([c('a', 0)], rows, 10);
  assert.equal(result.length, 1);
  assert.equal(result[0].messages.length, 2);
  assert.equal(result[0].seconds, 9);
  assert.equal(followUpPressure([c('a', 0, null, 5)], rows, 10).length, 0);
  assert.equal(
    followUpPressure(
      [c('a', 0)],
      [
        ...rows,
        m('human', 4, { direction: 'outgoing', sender_kind: 'human' }),
        m('3', 5),
      ],
      10,
    ).length,
    0,
  );
});
