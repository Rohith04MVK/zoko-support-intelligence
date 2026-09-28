import { formatDate } from '../format.js';
export default function Feedback({
  conversation,
  latest,
  canSend,
  agent,
  busy,
  onRequest,
  now,
}) {
  const feedback = conversation.csat;
  const state = feedback?.status;
  const canRequest =
    latest && canSend && agent && (!feedback || state === 'failed');
  const status = feedbackStatus(feedback, now);
  const hint = requestHint(latest, canSend, agent);
  return (
    <section className="feedback">
      <div>
        <strong>Customer feedback</strong>
        <p>{status}</p>
      </div>
      {(!feedback || state === 'failed') && (
        <>
          <p className="feedback-question">
            “How would you rate your support experience from 1–5? Reply with one
            number: 1 = very dissatisfied, 5 = very satisfied.”
          </p>
          <button
            type="button"
            className="secondary"
            disabled={!canRequest || busy}
            onClick={onRequest}
          >
            {busy ? 'Sending…' : 'Request feedback'}
          </button>
          <small>{hint}</small>
        </>
      )}
    </section>
  );
}

function feedbackStatus(feedback, now) {
  if (feedback?.received_at != null) {
    return `Rating: ${feedback.rating}/5 · Received ${formatDate(feedback.received_at)}`;
  }
  switch (feedback?.status) {
    case 'accepted':
      if (feedback.superseded)
        return 'No rating recorded. A new support conversation followed the request.';
      if (now > feedback.expires_at)
        return 'Feedback window expired. No rating received.';
      return 'Request accepted by Zoko. Awaiting a 1–5 rating (24-hour window).';
    case 'pending':
    case 'uncertain':
      return 'Send status is unconfirmed. Check WhatsApp before taking further action; automatic retry is disabled.';
    case 'failed':
      return 'The request was not sent. Check the error below before retrying.';
    default:
      return 'Send a 1–5 rating request for this closed conversation.';
  }
}

function requestHint(latest, canSend, agent) {
  if (!latest)
    return 'Available only for the latest closed conversation, with no open chat.';
  if (!canSend) return 'Sending is restricted to approved test recipients.';
  if (!agent) return 'Choose your account under “Replying as” below.';
  return 'Sends a WhatsApp message to this test recipient.';
}
