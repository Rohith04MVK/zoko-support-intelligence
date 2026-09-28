# Zoko Support Intelligence

A Python + React support analytics app, PostHog integration, and product teardown
for the Zoko Growth Engineer take-home. SQLite stores captured webhook events and
derived records. Scope: messages captured after tracking began, as clarified by Zoko.

## Included

- Message totals, per-customer counts, average/median first human response and
  resolution times, per-agent timings, and reassigned chats received.
- Conversation history, current assignment, assignment history, search and filters,
  allowlisted test-recipient sending, per-conversation drafts, and CSAT requests.
- Needs-attention queue, agent workload, response targets, seven-day comparisons,
  and repeated unanswered customer-message signals.
- PostHog conversation-to-feedback funnel, SQL daily messages chart, agent groups,
  and a non-SQL unique-agent insight filtered to messages_sent > 10.
- [Five Zoko product improvements](product-teardown.md).

## Run locally

Requires Python 3.12+, Node.js 22.12+, npm, and ngrok for
receiving external webhooks. Run commands from this repository directory.

```bash
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python backend/migrate.py
npm ci --prefix frontend
npm run build --prefix frontend
python3 backend/receiver.py serve
```

In separate terminals:

```bash
python3 backend/dashboard.py
ngrok http 8000
python3 backend/posthog_sync.py --watch
```

Open http://127.0.0.1:8001. Run the migration before starting either service.
The dashboard serves the React build and its API. For frontend development,
`npm run dev --prefix frontend` proxies API calls to the running Python dashboard.

Configure the actual keys and allowed test numbers in `.env`. Never commit it.
PostHog is optional for the local dashboard; its worker needs a project ingestion
key and US/EU ingestion host. The sending key is reread on every request.

Print the private webhook path:

```bash
python3 backend/receiver.py path
```

Append it to ngrok's HTTPS origin and configure Zoko events: Incoming message,
Outgoing message, Message delivery update, Chat assigned, and Chat closed.
The tested setup uses a blank Challenge token. The receiver handles query strings
but does not implement challenge-token verification. Keep the random path private.
Only tunnel port 8000; port 8001 exposes the local dashboard and customer data.

## Architecture and decisions

`receiver.py` persists raw deliveries before acknowledging them. `analytics.py`
rebuilds a deterministic snapshot on dashboard refresh and PostHog sync, merging
message retries by message ID and ordering events by source time. Raw events stay
unchanged. SQLAlchemy models store customers, agents, messages, conversations, assignments,
and feedback in relational tables with foreign keys and indexes. Raw webhook
payloads and PostHog event envelopes remain JSON because their shape is external.
FastAPI provides validated request contracts; Uvicorn serves the two applications.
The local API documentation is at http://127.0.0.1:8001/docs. Public webhook ingress
has no dashboard or documentation routes.

Python was chosen for familiarity and explainability. React provides the interface;
SQLite makes local setup straightforward. A production deployment would need a
authentication, verified webhook authenticity, and
incremental processing instead of rebuilding the entire history.

## Metric definitions

- A conversation starts on an incoming message when none is open for that customer,
  and ends on an observed closure. A later incoming message starts another chat,
  except for a matched CSAT response. No inactivity-based closure is inferred.
- First response runs from start to first identified human outgoing message.
  Bots and unknown senders are excluded. API sends made here are attributed using
  the exact returned message ID and the selected agent. The selection is an operator
  declaration, not authenticated identity. Missing IDs remain unattributed.
- Resolution runs from start to closure, attributed to the closure's assigned agent.
  First response is attributed to the responding human.
- Reassignments count distinct conversations transferred to an agent from a different
  known agent. Initial assignment and repeated assignment to the same agent do not count.
- All durations are elapsed time, including nights/weekends. Unanswered/open chats
  are excluded from the respective timing aggregate; sample sizes are displayed.
- Messages without an observed conversation start remain counted but unlinked.
  Closures without observed starts generate warnings rather than invented durations.

## Sending and feedback

Only numbers in ZOKO_ALLOWED_RECIPIENTS may receive messages; enforcement is on the
server. Send only to your own/test number. Select a known agent in the composer.
API acceptance is distinct from delivery; webhooks supply message history.
There are no automatic retries after uncertain sends. The dashboard uses CSRF
protection but has no login, so keep it local. Drafts survive navigation and data
refresh during a page session, not a browser reload.

For a live test, message the store from your allowed phone, refresh the app, reply,
and close the conversation in Zoko. Then select the latest closed conversation and
request feedback. A bare 1–5 reply within 24 hours attaches to it without changing
its response/resolution times. Normal replies start a new support conversation.
Duplicate feedback requests and uncertain retries are blocked. See
[PostHog details](analytics/posthog.md) for matching rules and event definitions.

## Validation

```bash
python3 -m unittest discover -s backend -p 'test_*.py'
node --test frontend/src/*.test.js
npm run build --prefix frontend
```

Tests use mocked sending, never live message delivery. Coverage includes event
ordering/deduplication, attribution, recipient restrictions, CSAT matching and
concurrent requests, PostHog privacy/outbox behavior, target boundaries, rolling
periods, and repeated unanswered messages. Live sending, feedback receipt, and the
PostHog funnel were also verified manually in the test account.

## Workload and first-response targets

The Agents page shows open chats and chats awaiting a human reply per current
owner, including unassigned chats. Wait starts at the oldest incoming message
since the last human response; bots and unidentified replies do not clear it.
Closed chats and CSAT messages do not contribute to waiting workload. Expand a
row to open its conversations. Reassignment happens in Zoko.

The first-response target defaults to 5 minutes, accepts 1–1440 minutes, and is
saved in this browser only. The within-target percentage covers all captured
conversations with an observed first human reply, including replies exactly at
the target. Open unanswered chats strictly past the target are listed separately
as overdue. Closed unanswered chats are also reported separately. Changing the
target recalculates captured history; no historical policy is retained. Durations
include nights and weekends. Timers update every 15 seconds; Refresh fetches new
activity. Tests cover follow-ups, bot replies, reassignment, unassigned chats,
closed unanswered chats, target boundaries, and empty samples.

Zoko clarified that only messages captured after tracking began are required.
Historical import is not a submission blocker.

## Response trends and follow-up pressure

The Agents page compares conversations started in the last rolling 7 days with
those started in the previous 7 days. Metrics are median first human response,
median resolution, and first-response target hit rate using the configured target.
Each metric shows its measured sample size. Outcomes are evaluated as observed now,
not frozen at period end; recent cohorts have had less time to resolve. Unanswered
conversations and open conversations are excluded from their respective duration
metrics. Missing samples produce no comparison rather than an invented zero.
Dates display in the browser timezone; periods span exactly seven elapsed days.

The follow-up queue shows open conversations with at least two distinct customer
messages after the latest human reply. It includes message text, current owner,
waiting time, and a conversation link, sorted by count then wait. Bots and unknown
senders do not clear this signal; CSAT messages are excluded. Multiple messages
may be one request, so this is prioritization evidence, not sentiment detection.

## Database migrations

Alembic owns the schema in `backend/data/support.sqlite3`. With services stopped,
run `python backend/migrate.py` before upgrading or starting this version. The
command imports legacy event, sending, CSAT, and PostHog outbox databases once in
a transaction, retaining original IDs and sync acknowledgements. Existing source
databases and the webhook token are left untouched. Back up `backend/data` first.
Running the command again upgrades the schema without repeating the import.

`models.py` defines persistence, `schemas.py` validates HTTP requests,
`repository.py` stores the derived projection, and `analytics.py` keeps metric
calculations independent of HTTP and the ORM. Projection writes are atomic;
sending and PostHog network calls happen outside database transactions. SQLite
serializes writers, so full-history projection rebuilds remain a scaling limit.
The migration is an explicit versioned revision in `backend/migrations/versions`.
