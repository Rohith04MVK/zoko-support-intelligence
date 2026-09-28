async function readResponse(response, fallbackMessage) {
  const result = await response.json();
  if (!response.ok) {
    throw new Error(result.error || fallbackMessage);
  }
  return result;
}

export async function fetchDashboard(signal) {
  const response = await fetch('/api/dashboard', { signal });
  return readResponse(
    response,
    'Unable to load conversations. Refresh to retry.',
  );
}

export async function postMessage(path, payload, csrf) {
  const response = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf },
    body: JSON.stringify(payload),
  });
  return readResponse(response, 'The request could not be completed.');
}
