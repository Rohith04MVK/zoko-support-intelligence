import { useCallback, useEffect, useRef, useState } from 'react';
import { fetchDashboard } from '../api.js';

export function useDashboard() {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [updated, setUpdated] = useState(null);
  const request = useRef(null);

  const refresh = useCallback(async () => {
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    setBusy(true);
    setError('');
    try {
      const dashboard = await fetchDashboard(controller.signal);
      if (!controller.signal.aborted) {
        setData(dashboard);
        setUpdated(new Date());
      }
    } catch (error) {
      if (!controller.signal.aborted) setError(error.message);
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    return () => request.current?.abort();
  }, [refresh]);

  return { data, busy, error, updated, refresh };
}
