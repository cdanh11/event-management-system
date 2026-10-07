import { useCallback, useEffect, useRef, useState } from 'react';
import { socketManager, type ConnState, type OccupancyMsg } from './socket';
import { usePolling } from './usePolling';

export type Occupancy = Omit<OccupancyMsg, 'type'>;
export type LiveState = ConnState | 'polling';
type Received = { data: Occupancy; at: string; source: 'socket' | 'poll' };

/** Keep the last snapshot on reconnect; a newer socket frame beats a late REST response. */
export function useOccupancy(
  eventId: string | null,
  opts: { refetch: (signal?: AbortSignal) => Promise<{ data: Occupancy | null }>; pollMs?: number;
    onSnapshot?: (data: Occupancy, at: string, source: 'socket' | 'poll') => void } | null = null,
) {
  const [received, setReceived] = useState<Received | null>(null);
  const [failure, setFailure] = useState<{ eventId: string; error: unknown } | null>(null);
  const [connection, setConnection] = useState<{ eventId: string | null; state: ConnState }>({ eventId, state: 'connecting' });
  const options = useRef(opts);
  const active = useRef(eventId);
  const frames = useRef(0);
  const restController = useRef<AbortController | undefined>(undefined);
  const snapshot = received?.data.event_id === eventId ? received : null;
  const terminal = snapshot?.data.status === 'COMPLETED' || snapshot?.data.status === 'CANCELLED';
  const sock = terminal || !eventId ? 'closed' : connection.eventId === eventId ? connection.state : 'connecting';
  useEffect(() => { options.current = opts; });

  const resync = useCallback(async () => {
    if (!eventId || active.current !== eventId) return;
    restController.current?.abort();
    const controller = new AbortController();
    restController.current = controller;
    const revision = frames.current;
    try {
      const result = await options.current?.refetch(controller.signal);
      if (!controller.signal.aborted && active.current === eventId && revision === frames.current && result?.data?.event_id === eventId) {
        const at = new Date().toISOString();
        setReceived({ data: result.data, at, source: 'poll' });
        options.current?.onSnapshot?.(result.data, at, 'poll');
        setFailure(null);
      }
    } catch (error) {
      if (!controller.signal.aborted && active.current === eventId && revision === frames.current) setFailure({ eventId, error });
    }
  }, [eventId]);

  useEffect(() => {
    active.current = eventId;
    frames.current += 1;
    if (!eventId || terminal) return;
    let alive = true;
    void resync();
    const unsubscribe = socketManager.subscribe(eventId, (message) => {
      if (!alive) return;
      frames.current += 1;
      const at = new Date().toISOString();
      setReceived({ data: message, at, source: 'socket' });
      options.current?.onSnapshot?.(message, at, 'socket');
      setFailure(null);
    }, { onState: (state) => { if (alive) setConnection({ eventId, state }); }, onResync: () => void resync() });
    return () => { alive = false; active.current = null; frames.current += 1; restController.current?.abort(); unsubscribe(); };
  }, [eventId, terminal, resync]);

  usePolling(resync, opts?.pollMs ?? 5000, { enabled: !!eventId && !terminal && sock !== 'open' });
  return {
    data: snapshot?.data ?? null,
    updatedAt: snapshot?.at,
    source: snapshot?.source,
    error: failure?.eventId === eventId ? failure.error : undefined,
    state: sock as LiveState,
    retry: () => { if (eventId && !terminal) { socketManager.retry(eventId); void resync(); } },
  };
}
