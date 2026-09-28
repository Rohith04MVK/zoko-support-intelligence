import {
  MessageCircle,
  Users,
  Clock3,
  Check,
  ArrowUpRight,
  ArrowRight,
} from 'lucide-react';
import { Avatar, Badge, Metric, Timing } from '../components/SupportUI.jsx';
import { formatDate } from '../format.js';

export default function Overview({
  data,
  onOpenConversation,
  onViewConversations,
}) {
  const { customers, conversations } = data;
  const sorted = [...conversations].sort((a, b) => b.started_at - a.started_at);
  const customer = (id) =>
    customers.find((customer) => customer.id === id) || {};
  return (
    <>
      <div className="metrics">
        <Metric
          title="Messages"
          value={data.metrics.total_messages}
          note="Incoming + outgoing, counted once"
          icon={MessageCircle}
        />
        <Metric
          title="Conversations"
          value={conversations.length}
          note="Across your captured customer chats"
          icon={Users}
        />
        <Metric
          title="Still open"
          value={conversations.length - data.metrics.closed_conversations}
          note="Conversations without a closure event"
          icon={Clock3}
          accent
        />
        <Metric
          title="Closed"
          value={data.metrics.closed_conversations}
          note="Conversations with a closure event"
          icon={Check}
        />
      </div>
      <div className="overview-grid">
        <section className="panel response-panel">
          <div className="section-title">
            <div>
              <h2>Response and resolution times</h2>
              <p>Average and median durations across measured conversations.</p>
            </div>
            <span className="pill">All time</span>
          </div>
          <Timing title="First human reply" stat={data.metrics.frt} />
          <Timing
            title="Conversation resolution"
            stat={data.metrics.resolution}
          />
          <details className="definitions">
            <summary>What do these numbers mean?</summary>
            <p>
              <b>Average</b> is the total time divided by the number of measured
              conversations. <b>Median</b> is the middle time: half are shorter,
              half longer. First reply excludes bots. Resolution runs from the
              first incoming message to closure. Unanswered or open chats are
              excluded from the respective timing metric.
            </p>
          </details>
        </section>
        <section className="panel recent">
          <div className="section-title">
            <div>
              <h2>Recent conversations</h2>
              <p>Latest conversations by start time.</p>
            </div>
            <MessageCircle size={21} />
          </div>
          {sorted.slice(0, 4).map((c) => (
            <button
              className="recent-row"
              key={c.id}
              onClick={() => onOpenConversation(c.id)}
            >
              <Avatar name={customer(c.customer_id).name} />
              <span>
                <strong>
                  {customer(c.customer_id).name || 'Unknown customer'}
                </strong>
                <small>{formatDate(c.started_at)}</small>
              </span>
              <Badge closed={c.closed_at != null} />
              <ArrowUpRight size={17} />
            </button>
          ))}
          {!sorted.length && (
            <p className="empty">No conversations captured.</p>
          )}
          <button className="text-button" onClick={onViewConversations}>
            View all conversations <ArrowRight size={16} />
          </button>
        </section>
      </div>
      <section className="panel customer-panel">
        <div className="section-title">
          <div>
            <h2>Messages by customer</h2>
            <p>Total incoming and outgoing messages per customer.</p>
          </div>
        </div>
        <div className="customer-stats">
          {customers.map((c) => (
            <div key={c.id}>
              <Avatar name={c.name} />
              <span>{c.name || 'Unknown customer'}</span>
              <strong>
                {data.metrics.messages_per_customer[c.id] || 0}
                <small> messages</small>
              </strong>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}
