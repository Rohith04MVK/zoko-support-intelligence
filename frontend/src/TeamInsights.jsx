import { responseTrends, followUpPressure } from './team-insights.js';
import { formatDate } from './format.js';

function duration(seconds) {
  if (seconds == null) return '—';
  if (seconds >= 86400) return `${(seconds / 86400).toFixed(1)}d`;
  if (seconds >= 3600) return `${(seconds / 3600).toFixed(1)}h`;
  if (seconds >= 60) return `${(seconds / 60).toFixed(1)}m`;
  return `${Math.round(seconds)}s`;
}

function metricValue(value, isRate) {
  if (value == null) return '—';
  return isRate ? `${value.toFixed(1)}%` : duration(value);
}

function change(current, previous, rate) {
  if (current == null || previous == null) return 'Not enough data to compare';
  const d = current - previous;
  if (Math.abs(d) < 0.001) return 'No change';
  return rate
    ? `${Math.abs(d).toFixed(1)} percentage points ${d > 0 ? 'higher' : 'lower'}`
    : `${duration(Math.abs(d))} ${d > 0 ? 'longer' : 'shorter'}`;
}
export default function TeamInsights({ data, now, target, onOpen }) {
  const { current, previous } = responseTrends(
    data.conversations,
    now,
    target * 60,
  );
  const pressure = followUpPressure(data.conversations, data.messages, now);
  const name = (c) =>
    data.customers.find((u) => u.id === c.customer_id)?.name ||
    'Unknown customer';
  const agent = (c) =>
    c.assigned_agent_id
      ? data.agents.find((a) => a.id === c.assigned_agent_id)?.name ||
        'Unknown agent'
      : 'Unassigned';
  return (
    <>
      <section className="panel support-signals">
        <div className="section-title">
          <div>
            <h2>Response-time trends</h2>
            <p>
              Conversations started in the last 7 days compared with the
              previous 7 days.
            </p>
          </div>
        </div>
        <div className="trend-periods">
          <span>
            <b>Last 7 days</b> {formatDate(current.from)} –{' '}
            {formatDate(current.to)}
            <small>
              {current.total} conversations · {current.answered} answered ·{' '}
              {current.closed} closed
            </small>
          </span>
          <span>
            <b>Previous 7 days</b> {formatDate(previous.from)} –{' '}
            {formatDate(previous.to)}
            <small>
              {previous.total} conversations · {previous.answered} answered ·{' '}
              {previous.closed} closed
            </small>
          </span>
        </div>
        <div className="trend-cards">
          {[
            ['Median first response', 'frt', false, 'answered'],
            ['Median resolution', 'resolution', false, 'closed'],
            [
              `Within ${target}-minute first-response target`,
              'rate',
              true,
              'answered',
            ],
          ].map(([label, key, rate, sample]) => (
            <article key={key}>
              <h3>{label}</h3>
              <strong>{metricValue(current[key], rate)}</strong>
              <small>
                {current[sample]} measured
                {rate ? ` · ${current.within} within target` : ''}
              </small>
              <p>
                Previous: {metricValue(previous[key], rate)} ·{' '}
                {previous[sample]} measured
              </p>
              <span>{change(current[key], previous[key], rate)}</span>
            </article>
          ))}
        </div>
        <p className="footnote">
          Rolling periods in your local display timezone. Durations use elapsed
          time. Both groups use outcomes observed now; recent chats have had
          less time to receive a reply or close. Unanswered chats are excluded
          from response metrics and open chats from resolution. Small samples
          and incomplete capture limit comparisons; these are not agent
          rankings.
        </p>
      </section>
      <section className="panel support-signals">
        <div className="section-title">
          <div>
            <h2>Customer follow-up pressure</h2>
            <p>
              Open chats with at least two customer messages since the last
              human reply.
            </p>
          </div>
          <span className="pill">{pressure.length} chats</span>
        </div>
        {!pressure.length ? (
          <p>No open conversations currently meet this condition.</p>
        ) : (
          pressure.map((item) => (
            <details className="pressure-item" key={item.conversation.id}>
              <summary>
                <b>{name(item.conversation)}</b>
                <span>
                  {item.messages.length} unanswered messages · Waiting{' '}
                  {duration(item.seconds)} · {agent(item.conversation)}
                </span>
              </summary>
              <ol>
                {item.messages.map((m) => (
                  <li key={m.id}>
                    <time>{formatDate(m.at)}</time>
                    <p>{m.text || '[Non-text message]'}</p>
                  </li>
                ))}
              </ol>
              <button
                className="secondary"
                onClick={() => onOpen(item.conversation.id)}
              >
                Open conversation →
              </button>
            </details>
          ))
        )}
        <p className="footnote">
          Sorted by unanswered message count, then longest wait. Automated and
          unidentified replies do not clear the queue. Multiple messages can be
          parts of one request; this signal does not infer frustration. Refresh
          to fetch new replies.
        </p>
      </section>
    </>
  );
}
