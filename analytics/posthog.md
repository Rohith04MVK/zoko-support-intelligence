# PostHog setup and remaining insights

## Ingestion

The backend sends events through PostHog's batch ingestion API. Configure the
project token and US/EU ingestion host in `.env`:

```
POSTHOG_PROJECT_API_KEY=your_project_token
POSTHOG_HOST=https://us.i.posthog.com
```

Run `python3 backend/posthog_sync.py` once or
`python3 backend/posthog_sync.py --watch` for a 30-second worker.
The worker rebuilds the snapshot and sends at most 100 queued events per pass.
Keep it running alongside the webhook receiver. PostHog outages leave events
queued. Source timestamps are preserved; deterministic event UUIDs and insert IDs
support deduplication on retries. Sent IDs are persisted in a per-project local
SQLite outbox. API acceptance is not a substitute for verifying events in PostHog.

No message text, customer names, phones, or agent emails are included. Agent groups
use stable Zoko agent IDs and pseudonymous display names (Agent + ID prefix).
The app still shows actual agent names locally.

## Events

- `conversation_started`: distinct_id and conversation_id both identify the
  conversation, so a customer's separate conversations do not collapse in funnels.
- `conversation_closed`: same distinct_id, source closure timestamp, duration metrics.
- `csat_asked`: same conversation identity, recorded only for an API-accepted feedback request.
- `csat_received`: same conversation identity, source reply timestamp and numeric rating.
- `message_recorded`: unique message ID, direction, sender_kind and conversation ID.
- `$groupidentify`: group type `agent`, key Zoko agent ID. Properties `messages_sent`
  and `conversations_handled` are absolute counts over captured history.
- `agent_activity_snapshot`: daily and on aggregate changes, group association plus
  messages_sent/conversations_handled. Useful for unique-agent insights.

Handled = a distinct observed conversation in which the agent was assigned,
replied, or was the assigned agent at closure. This definition is documented rather
than inferred as a Zoko-native metric. Counts cover captured data only.

Events are immutable after syncing. Later corrections to previously exported
message attribution do not rewrite old PostHog events; group totals are updated.
Before final submission, reconcile attribution and use a clean project if necessary.

## Required insights to create

1. Funnel, ordered: `conversation_started` → `conversation_closed` → `csat_asked`
   → `csat_received`. Count unique distinct IDs, which represent conversations.
   Use a 30-day conversion window for the test. The CSAT flow is implemented;
   a live feedback exchange and the saved funnel were verified in PostHog.
2. SQL insight using `daily_messages.sql`: saved as **Daily messages** on the
   **Support analytics** dashboard. Dates are UTC; label the chart accordingly.
3. Agents as PostHog groups: emitted by the worker. Verify messages_sent and
   conversations_handled in group properties.
4. Non-SQL Trends insight: event `agent_activity_snapshot`; aggregation Unique
   `agent` groups; event-property filter `messages_sent > 10`; daily interval.
   Counts agents observed above the cumulative captured-message threshold that day,
   not agents sending 10 messages during that day. Use a number view for the current
   day's snapshots if a single current count is preferred. Do not filter historical
   snapshots by today's mutable group property if historical accuracy is intended.

Check group-analytics availability before enabling billing. Public docs describe
it as a paid add-on; the brief requires approval from Zoko before any payment.
Sending group-identify events here does not enable a paid subscription.

## Current validation

20 backend tests pass, including event privacy, outbox deduplication, group totals,
and conversation funnel identity. First live ingestion accepted 23 events;
immediate repeat accepted 0. The user verified event visibility and the daily SQL chart in PostHog.
Zoko approved the paid upgrade. The user enabled Group Analytics and configured
the non-SQL insight with Unique agents and event-property messages_sent > 10.
The test data currently produces no matching events, which is a valid empty result. Project token cannot read/manage private insights.

Sources: https://posthog.com/docs/api/capture
https://posthog.com/docs/product-analytics/group-analytics

## Feedback matching and manual validation

In the app, open the latest closed conversation for an approved test recipient,
choose your sending agent, and click **Request feedback**. The fixed 1–5 question
is shown before sending. Reply from the test phone with a single digit `1`–`5`,
then refresh the app. The rating should appear on the same closed conversation.
The PostHog worker should emit `csat_asked` and `csat_received` with the original
conversation identity. No synthetic events or feedback are inserted in live data.

A request expires after 24 hours. A non-rating incoming message starts a support
conversation and supersedes its pending survey; a later rating is then a normal
support message. A rating after expiry or after the first rating is also a normal
message. Feedback messages remain in message totals but do not alter FRT or
resolution times. Outgoing surveys link by the exact Zoko response message ID;
without that ID, the accepted request is still recorded but its outgoing webhook
cannot be reliably linked to the closed conversation.

Requests are stored in the `feedback_requests` table of `backend/data/support.sqlite3`. A transaction claims the
conversation before sending, preventing duplicate concurrent submissions.
Timeouts, network failures, 5xx errors, and interrupted attempts are not retried
automatically; their status stays uncertain/pending for manual investigation.
Definitive 4xx rejections and local validation failures allow a manual retry.
An accepted request is never re-sent for the same conversation. Another request
to the same customer is blocked during an existing request's 24-hour window.
API acceptance is the funnel's “asked” milestone, not proof of delivery or reading.

Late webhook data can change derived conversation matching. Previously exported
PostHog events are immutable; reconcile a clean test sequence before submitting.
