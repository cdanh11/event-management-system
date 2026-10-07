import { useEffect, useRef } from 'react';

/* Polling with tab-visibility pause, immediate refetch on tab visible again,
   no overlapping requests, full cleanup on unmount (see design.md §5.3). */
export function usePolling(
  fn: () => Promise<unknown>,
  ms: number,
  opts: { enabled?: boolean } = {}
) {
  const enabled = opts.enabled ?? true;
  const fnRef = useRef(fn);
  useEffect(() => {
    fnRef.current = fn;
  });

  useEffect(() => {
    if (!enabled) return;
    let alive = true;
    let inFlight = false;
    const tick = async () => {
      if (!alive || document.hidden || inFlight) return;
      inFlight = true;
      try {
        await fnRef.current();
      } catch {
        // Error state is owned by the caller (shows Retry).
      } finally {
        inFlight = false;
      }
    };
    const onVisible = () => {
      if (!document.hidden) void tick();
    };
    document.addEventListener('visibilitychange', onVisible);
    const timer = setInterval(() => void tick(), ms);
    return () => {
      alive = false;
      document.removeEventListener('visibilitychange', onVisible);
      clearInterval(timer);
    };
  }, [ms, enabled]);
}
