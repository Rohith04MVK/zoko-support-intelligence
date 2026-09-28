import { Clock3 } from 'lucide-react';
import { formatDuration, initials } from '../format.js';
export function Avatar({ name }) {
  return <span className="avatar">{initials(name)}</span>;
}
export function Badge({ closed }) {
  return (
    <span className={'badge ' + (closed ? 'closed' : 'open')}>
      <span />
      {closed ? 'Closed' : 'Open'}
    </span>
  );
}
export function Metric({ title, value, note, icon: Icon, accent }) {
  return (
    <article className={'metric ' + (accent ? 'accent' : '')}>
      <div className="metric-label">
        <span>{title}</span>
        <Icon size={18} />
      </div>
      <strong>{value}</strong>
      <small>{note}</small>
    </article>
  );
}
export function Timing({ title, stat }) {
  return (
    <section className="timing">
      <div className="timing-title">
        <Clock3 size={17} />
        <h3>{title}</h3>
        <span>{stat.sample_size} measured</span>
      </div>
      <div className="timing-values">
        <div>
          <small>Average</small>
          <strong>{formatDuration(stat.average_seconds)}</strong>
        </div>
        <div>
          <small>Median</small>
          <strong>{formatDuration(stat.median_seconds)}</strong>
        </div>
      </div>
    </section>
  );
}
