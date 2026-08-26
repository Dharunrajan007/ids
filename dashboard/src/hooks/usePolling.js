import { useEffect, useState } from "react";

/**
 * Poll `fetcher` every `intervalMs`, keeping the last good data when a tick
 * fails (ADR-007: the dashboard polls; no WebSockets).
 *
 * Timer-CHAINED (setTimeout after each completion), not setInterval: a slow
 * or hung request can never overlap the next one, so there is exactly one
 * in-flight request and one pending timer per hook instance. Cleanup cancels
 * both on unmount — no leaked timers, no setState-after-unmount.
 *
 * `fetcher` must be referentially stable (a module-level function): the
 * effect restarts whenever it changes.
 */
export default function usePolling(fetcher, intervalMs) {
  const [state, setState] = useState({ data: null, error: null });

  useEffect(() => {
    let alive = true;
    let timer;

    const tick = async () => {
      try {
        const data = await fetcher();
        if (alive) setState({ data, error: null });
      } catch (error) {
        // Keep the stale data visible under the disconnected banner —
        // a blank dashboard is worse than a clearly-labeled stale one.
        if (alive) setState((prev) => ({ data: prev.data, error }));
      }
      if (alive) timer = setTimeout(tick, intervalMs);
    };

    tick();
    return () => {
      alive = false;
      clearTimeout(timer);
    };
  }, [fetcher, intervalMs]);

  return state;
}
