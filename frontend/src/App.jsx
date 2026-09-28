import { useDashboard } from './hooks/useDashboard.js';
import { useEffect, useState } from 'react';
import {
  Sun,
  LayoutDashboard,
  Users,
  MessageCircle,
  RefreshCw,
  ChevronRight,
  Coffee,
} from 'lucide-react';
import Overview from './pages/Overview.jsx';
import Agents from './pages/Agents.jsx';
import Conversations from './pages/Conversations.jsx';
const names = {
  overview: 'Overview',
  agents: 'Agents',
  conversations: 'Conversations',
};
const headings = {
  overview: {
    eyebrow: 'SUPPORT ANALYTICS',
    title: 'Support overview',
    description: 'Message volume, conversation status, and response times.',
  },
  agents: {
    eyebrow: 'AGENT PERFORMANCE',
    title: 'Agent performance',
    description:
      'Response times, resolution times, and reassigned chats by agent.',
  },
  conversations: {
    eyebrow: 'CUSTOMER MESSAGES',
    title: 'Conversations',
    description: 'View message history and reply to approved test recipients.',
  },
};

export default function App() {
  const [now, setNow] = useState(() => Date.now() / 1000);
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now() / 1000), 15000);
    return () => clearInterval(timer);
  }, []);
  const { data, busy, error, updated, refresh } = useDashboard();
  const [view, setView] = useState('overview');
  const [selected, setSelected] = useState(null);
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState('all');
  const conversations = data?.conversations || [];
  function openConversation(id) {
    setSelected(id);
    setQuery('');
    setFilter('all');
    setView('conversations');
  }
  return (
    <div className="shell">
      <aside className="sidebar">
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            setView('overview');
          }}
        >
          <span className="brandmark">
            <Sun size={25} />
          </span>
          <div>
            Support<span>Support analytics</span>
          </div>
        </a>
        <div className="nav-label">WORKSPACE</div>
        <nav aria-label="Main navigation">
          {[
            ['overview', LayoutDashboard],
            ['conversations', MessageCircle],
            ['agents', Users],
          ].map(([key, Icon]) => (
            <button
              key={key}
              className={view === key ? 'active' : ''}
              aria-current={view === key ? 'page' : undefined}
              onClick={() => setView(key)}
            >
              <Icon size={19} />
              {names[key]}
              {key === 'conversations' && data && (
                <span className="count">{conversations.length}</span>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="store-mark">Z</div>
          <div>
            <strong>Zoko Customer Sales</strong>
            <small>Test workspace</small>
          </div>
        </div>
      </aside>
      <main>
        <div className="topbar">
          <span>
            Workspace <ChevronRight size={14} /> {names[view]}
          </span>
          <span className="capture">
            <span />
            Captured store activity
          </span>
        </div>
        <header className="page-heading">
          <div>
            <div className="eyebrow">{headings[view].eyebrow}</div>
            <h1>{headings[view].title}</h1>
            <p>{headings[view].description}</p>
          </div>
          <button
            className="secondary refresh"
            disabled={busy}
            onClick={refresh}
          >
            <RefreshCw size={15} className={busy ? 'spin' : ''} />
            {busy ? 'Refreshing' : 'Refresh'}
          </button>
        </header>
        {error && (
          <div role="alert" className="error">
            {error}
          </div>
        )}
        {!data ? (
          <div className="empty">
            <Coffee size={30} />
            <h2>
              {busy ? 'Loading workspace…' : 'Your workspace is unavailable.'}
            </h2>
            <p>Use Refresh to try again.</p>
          </div>
        ) : (
          <>
            {view === 'overview' && (
              <Overview
                data={data}
                onOpenConversation={openConversation}
                onViewConversations={() => setView('conversations')}
              />
            )}
            {view === 'agents' && (
              <Agents
                data={data}
                now={now}
                onOpenConversation={openConversation}
              />
            )}
            {/* Keep the composer mounted so navigation preserves unsent drafts. */}
            <div hidden={view !== 'conversations'}>
              <Conversations
                data={data}
                now={now}
                selected={selected}
                onSelect={setSelected}
                query={query}
                onQueryChange={setQuery}
                filter={filter}
                onFilterChange={setFilter}
                onRefresh={refresh}
              />
            </div>
            <footer>
              <span>Showing messages captured since tracking began</span>
              <span>
                {updated &&
                  `Updated ${updated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`}
              </span>
            </footer>
            {data.metrics.warnings.length > 0 && (
              <p role="status" className="footnote">
                {data.metrics.warnings.length} data-quality warnings. Some
                incomplete events were excluded from metrics.
              </p>
            )}
          </>
        )}
      </main>
    </div>
  );
}
