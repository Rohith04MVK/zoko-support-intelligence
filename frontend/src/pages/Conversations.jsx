import { postMessage } from '../api.js';
import { useState } from 'react';
import { Search, MessageCircle, Check, Send } from 'lucide-react';
import { Avatar, Badge } from '../components/SupportUI.jsx';
import Feedback from '../components/Feedback.jsx';
import { formatDate } from '../format.js';
import { attentionReasons, assignmentHistory } from '../conversation-utils.js';

export default function Conversations({
  data,
  now,
  selected,
  onSelect,
  query,
  onQueryChange,
  filter,
  onFilterChange,
  onRefresh,
}) {
  const [drafts, setDrafts] = useState({});
  const [agent, setAgent] = useState(
    () => sessionStorage.getItem('sendingAgent') || '',
  );
  const [sending, setSending] = useState(false);
  const [statuses, setStatuses] = useState({});
  const customers = data?.customers || [];
  const agents = data?.agents || [];
  const conversations = data?.conversations || [];
  const messages = data?.messages || [];
  const customer = (id) => customers.find((c) => c.id === id) || {};
  const agentName = (id) =>
    agents.find((a) => a.id === id)?.name?.trim() || 'Unassigned';
  const sorted = [...conversations].sort((a, b) => b.started_at - a.started_at);
  const reasons = (c) => attentionReasons(c, messages, now);
  const attentionCount = sorted.filter((c) => reasons(c).length).length;
  const filtered = sorted.filter((conversation) => {
    const contact = customer(conversation.customer_id);
    const searchText =
      `${contact.name || ''} ${contact.phone || ''}`.toLowerCase();
    if (!searchText.includes(query.toLowerCase())) return false;
    switch (filter) {
      case 'attention':
        return reasons(conversation).length > 0;
      case 'open':
        return conversation.closed_at == null;
      case 'closed':
        return conversation.closed_at != null;
      default:
        return true;
    }
  });
  const current = filtered.find((c) => c.id === selected) || filtered[0];
  const currentCustomer = current ? customer(current.customer_id) : {};
  const currentMessages = messages
    .filter((m) => m.conversation_id === current?.id)
    .sort((a, b) => a.at - b.at);
  async function sendReply(e) {
    e.preventDefault();
    if (!current || sending) return;
    const id = current.id;
    setSending(true);
    setStatuses((s) => ({ ...s, [id]: 'Sending…' }));
    try {
      const result = await postMessage(
        '/api/send',
        {
          customer_id: current.customer_id,
          agent_id: agent,
          message: drafts[id] || '',
        },
        data.csrf,
      );
      setDrafts((d) => ({ ...d, [id]: '' }));
      setStatuses((s) => ({ ...s, [id]: result.message }));
    } catch (e) {
      setStatuses((s) => ({ ...s, [id]: e.message }));
    } finally {
      setSending(false);
    }
  }
  async function requestFeedback() {
    if (!current || sending) return;
    const id = current.id;
    setSending(true);
    setStatuses((s) => ({ ...s, [id]: 'Sending feedback request…' }));
    try {
      const result = await postMessage(
        '/api/csat',
        {
          customer_id: current.customer_id,
          conversation_id: id,
          agent_id: agent,
        },
        data.csrf,
      );
      setStatuses((s) => ({ ...s, [id]: result.message }));
    } catch (e) {
      setStatuses((s) => ({ ...s, [id]: e.message }));
    } finally {
      await onRefresh();
      setSending(false);
    }
  }
  return (
    <section className="panel inbox">
      <div className="chat-list">
        <div className="list-tools">
          <label className="search">
            <Search size={17} />
            <input
              aria-label="Search conversations"
              placeholder="Find a name or number"
              value={query}
              onChange={(e) => onQueryChange(e.target.value)}
            />
          </label>
          <div className="filters">
            {['all', 'open', 'closed', 'attention'].map((f) => (
              <button
                key={f}
                className={filter === f ? 'selected' : ''}
                aria-pressed={filter === f}
                onClick={() => onFilterChange(f)}
              >
                {f === 'attention'
                  ? `Needs attention (${attentionCount})`
                  : f[0].toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>
        </div>
        <p className="filter-help">
          Needs attention: awaiting a human reply or open over 30 minutes.
        </p>
        <div className="chat-items">
          {filtered.map((c) => (
            <button
              key={c.id}
              className={
                'chat-item ' + (current?.id === c.id ? 'selected' : '')
              }
              aria-pressed={current?.id === c.id}
              onClick={() => onSelect(c.id)}
            >
              <div>
                <Avatar name={customer(c.customer_id).name} />
                <span>
                  <strong>
                    {customer(c.customer_id).name || 'Unknown customer'}
                  </strong>
                  <small>{formatDate(c.started_at)}</small>
                </span>
              </div>
              <div className="chat-sub">
                <span>{agentName(c.assigned_agent_id)}</span>
                <Badge closed={c.closed_at != null} />
              </div>
              {reasons(c).length > 0 && (
                <span className="attention-reasons">
                  {reasons(c).join(' · ')}
                </span>
              )}
            </button>
          ))}
          {!filtered.length && (
            <p className="empty">No matching conversations.</p>
          )}
        </div>
      </div>
      <div className="thread">
        {current ? (
          <>
            <div className="thread-header">
              <Avatar name={currentCustomer.name} />
              <div>
                <h2>{currentCustomer.name || 'Unknown customer'}</h2>
                <small>
                  {currentCustomer.phone || 'Phone unavailable'} ·{' '}
                  {agentName(current.assigned_agent_id)}
                </small>
              </div>
              <Badge closed={current.closed_at != null} />
            </div>
            <div className="thread-messages">
              {reasons(current).length > 0 && (
                <div className="attention-banner">
                  {reasons(current).join(' · ')}
                </div>
              )}
              <details className="assignment-history" key={current.id}>
                <summary>Assignment history</summary>
                {assignmentHistory(current, data.assignments || []).length ? (
                  <ol>
                    {assignmentHistory(current, data.assignments || []).map(
                      (a, i) => (
                        <li key={`${a.at}-${i}`}>
                          <strong>
                            {a.previous_agent_id &&
                            a.previous_agent_id !== a.agent_id
                              ? `${agentName(a.previous_agent_id)} → ${agentName(a.agent_id)}`
                              : `Assigned to ${agentName(a.agent_id)}`}
                          </strong>
                          <time>{formatDate(a.at)}</time>
                        </li>
                      ),
                    )}
                  </ol>
                ) : (
                  <p>
                    No assignment changes captured during this conversation.
                  </p>
                )}
                <p>
                  Shows recorded assignments. The events do not identify who
                  triggered the change.
                </p>
              </details>
              {current.closed_at != null && (
                <Feedback
                  conversation={current}
                  latest={
                    !conversations.some(
                      (c) =>
                        c.customer_id === current.customer_id &&
                        (c.closed_at == null ||
                          c.started_at > current.started_at),
                    )
                  }
                  canSend={currentCustomer.can_send}
                  agent={agent}
                  busy={sending}
                  onRequest={requestFeedback}
                  now={now}
                />
              )}
              <div className="date-label">
                Started {formatDate(current.started_at)}
              </div>
              {currentMessages.map((m) => (
                <div key={m.id} className={'message ' + m.direction}>
                  <div className="bubble">{m.text || '[Non-text message]'}</div>
                  <small>
                    {m.purpose === 'csat_request'
                      ? 'Feedback request · '
                      : m.purpose === 'csat_rating'
                        ? 'Feedback rating · '
                        : ''}
                    {m.sender_kind === 'human'
                      ? agentName(m.agent_id)
                      : m.sender_kind === 'customer'
                        ? 'Customer'
                        : m.sender_kind === 'automation'
                          ? 'Automated reply'
                          : 'Unidentified sender'}{' '}
                    ·{' '}
                    {new Date(m.at * 1000).toLocaleTimeString([], {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </small>
                </div>
              ))}
              {current.closed_at != null && (
                <div className="date-label">
                  <Check size={13} />
                  Closed {formatDate(current.closed_at)}
                </div>
              )}
            </div>
            <form className="composer" onSubmit={sendReply}>
              <div className="composer-top">
                <label>
                  Replying as{' '}
                  <select
                    aria-label="Sending agent"
                    required
                    value={agent}
                    onChange={(e) => {
                      setAgent(e.target.value);
                      sessionStorage.setItem('sendingAgent', e.target.value);
                    }}
                  >
                    <option value="">Choose your account</option>
                    {agents.map((a) => (
                      <option key={a.id} value={a.id}>
                        {a.name?.trim()}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <textarea
                aria-label="Your reply"
                placeholder={
                  currentCustomer.can_send
                    ? 'Type a reply…'
                    : 'Replies are restricted to your test number.'
                }
                disabled={!currentCustomer.can_send || sending}
                required
                maxLength={4096}
                value={drafts[current.id] || ''}
                onChange={(e) =>
                  setDrafts((d) => ({ ...d, [current.id]: e.target.value }))
                }
              />
              <div className="composer-bottom">
                <small>
                  {currentCustomer.can_send
                    ? 'Test recipient · WhatsApp'
                    : 'Sending restricted'}
                </small>
                <button
                  className="primary"
                  disabled={
                    !currentCustomer.can_send ||
                    sending ||
                    !agent ||
                    !drafts[current.id]?.trim()
                  }
                >
                  <Send size={15} />
                  {sending ? 'Sending…' : 'Send reply'}
                </button>
              </div>
              {statuses[current.id] && (
                <p role="status" className="send-status">
                  {statuses[current.id]}
                </p>
              )}
            </form>
          </>
        ) : (
          <div className="empty">
            <MessageCircle size={30} />
            <h2>No conversation selected</h2>
            <p>Try a different search or filter.</p>
          </div>
        )}
      </div>
    </section>
  );
}
