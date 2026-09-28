import SupportSignals from '../SupportSignals.jsx';
import { Avatar, Timing } from '../components/SupportUI.jsx';

export default function Agents({ data, now, onOpenConversation }) {
  const { agents } = data;
  return (
    <>
      <SupportSignals data={data} now={now} onOpen={onOpenConversation} />
      <div className="section-intro">
        <span>{agents.length} agents in captured activity</span>
        <span>All time · Human replies only</span>
      </div>
      <div className="agent-grid">
        {data.metrics.agents.map((a) => (
          <article className="panel agent-card" key={a.agent_id}>
            <div className="agent-header">
              <Avatar name={a.name} />
              <div>
                <h2>{a.name?.trim() || 'Unnamed agent'}</h2>
                <p>Support agent</p>
              </div>
            </div>
            <Timing title="First human reply" stat={a.frt} />
            <Timing title="Resolution" stat={a.resolution} />
            <div className="transfer">
              <span>Reassigned chats received</span>
              <strong>{a.reassigned_chats_received}</strong>
            </div>
          </article>
        ))}
      </div>
      <p className="footnote">
        Average is the mean duration. Median is the middle duration. A dash
        means there are no measured conversations yet.
      </p>
    </>
  );
}
