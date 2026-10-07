import { useCallback, useEffect, useRef, useState } from 'react';

type QueryState<T> = { key: string; data?: T; error?: Error; pending: boolean };

/** Keep existing content on refresh; abort obsolete requests and pause hidden tabs. */
export function useQuery<T>(
  query: (signal: AbortSignal) => Promise<T>,
  deps: unknown[] = [],
  options: { enabled?: boolean; refetchInterval?: number | ((data: T | undefined) => number | undefined) } = {},
) {
  const key = JSON.stringify(deps);
  const enabled = options.enabled ?? true;
  const fn = useRef(query);
  const controller = useRef<AbortController | undefined>(undefined);
  const generation = useRef(0);
  const [state, setState] = useState<QueryState<T>>({ key, pending: enabled });
  const interval = typeof options.refetchInterval === 'function'
    ? options.refetchInterval(state.key === key ? state.data : undefined) : options.refetchInterval;
  useEffect(() => { fn.current = query; });

  const refetch = useCallback(async () => {
    if (!enabled) return;
    controller.current?.abort();
    const abort = new AbortController();
    controller.current = abort;
    const version = ++generation.current;
    setState((previous) => ({ key, data: previous.key === key ? previous.data : undefined, pending: true }));
    try {
      const data = await fn.current(abort.signal);
      if (!abort.signal.aborted && version === generation.current) {
        setState({ key, data, pending: false });
        return data;
      }
    } catch (error) {
      if (!abort.signal.aborted && version === generation.current) {
        if (import.meta.env.DEV) console.warn('Query failed', error);
        setState((previous) => ({ ...previous, error: error as Error, pending: false }));
      }
    }
  }, [key, enabled]);

  const setData = useCallback((data: T) => {
    controller.current?.abort();
    generation.current += 1;
    setState({ key, data, pending: false });
  }, [key]);

  useEffect(() => {
    // Start after subscription effects settle; rendering derives initial loading.
    const start = setTimeout(() => void refetch(), 0);
    return () => { clearTimeout(start); generation.current += 1; controller.current?.abort(); };
  }, [refetch]);

  useEffect(() => {
    if (!enabled || !interval) return;
    const tick = () => {
      if (!document.hidden && !controller.current?.signal.aborted && state.pending) return;
      if (!document.hidden) void refetch();
    };
    const timer = setInterval(tick, interval);
    document.addEventListener('visibilitychange', tick);
    return () => { clearInterval(timer); document.removeEventListener('visibilitychange', tick); };
  }, [enabled, interval, refetch, state.pending]);

  const current = state.key === key;
  const data = current ? state.data : undefined;
  return {
    data,
    error: current ? state.error : undefined,
    isLoading: enabled && data === undefined && (!current || state.pending),
    isRefreshing: data !== undefined && state.pending,
    refetch,
    setData,
  };
}
