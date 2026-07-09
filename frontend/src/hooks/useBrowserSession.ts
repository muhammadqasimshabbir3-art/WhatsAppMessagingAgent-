import { useCallback, useEffect, useState } from "react";
import { fetchBrowserStatus, setupBrowser, type BrowserStatus } from "../lib/browserClient";
import { isLocalBrowserApi, openWhatsAppInNewWindow } from "../lib/browserMode";

const POLL_MS = 2000;

export function useBrowserSession(enabled = true) {
  const localApi = isLocalBrowserApi();
  const [status, setStatus] = useState<BrowserStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [awaitingQr, setAwaitingQr] = useState(false);
  const [windowOpened, setWindowOpened] = useState(false);

  const refreshStatus = useCallback(async () => {
    if (!enabled || !localApi) return null;
    try {
      const next = await fetchBrowserStatus();
      setStatus(next);
      setError(null);
      if (next.logged_in) {
        setAwaitingQr(false);
      } else if (next.browser_running) {
        setAwaitingQr(true);
      }
      return next;
    } catch (err) {
      const message = err instanceof Error ? err.message : "Browser API unavailable";
      setError(message);
      return null;
    }
  }, [enabled, localApi]);

  const openBrowser = useCallback(async () => {
    setError(null);

    if (!localApi) {
      openWhatsAppInNewWindow();
      setWindowOpened(true);
      setAwaitingQr(true);
      return null;
    }

    setLoading(true);
    setAwaitingQr(true);
    try {
      const next = await setupBrowser();
      setStatus(next);
      setAwaitingQr(!next.logged_in);
      return next;
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to open browser";
      setError(message);
      setAwaitingQr(false);
      return null;
    } finally {
      setLoading(false);
    }
  }, [localApi]);

  useEffect(() => {
    if (!enabled || !localApi) return;
    void refreshStatus();
  }, [enabled, localApi, refreshStatus]);

  useEffect(() => {
    if (!enabled || !localApi || !awaitingQr || status?.logged_in) return;
    const id = window.setInterval(() => {
      void refreshStatus();
    }, POLL_MS);
    return () => window.clearInterval(id);
  }, [enabled, localApi, awaitingQr, status?.logged_in, refreshStatus]);

  const loggedIn = localApi && status?.logged_in === true;
  const browserRunning = localApi && status?.browser_running === true;

  return {
    status,
    loading,
    error,
    openBrowser,
    loggedIn,
    browserRunning,
    awaitingQr: awaitingQr && !loggedIn,
    needsQr: localApi ? !loggedIn : !windowOpened,
    isHostedUi: !localApi,
    windowOpened,
  };
}
