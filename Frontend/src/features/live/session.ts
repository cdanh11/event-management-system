import type { Occupancy } from '../../realtime/useOccupancy';

export type LiveChange = { id: string; delta: number; at: string };
export type LiveSession = { eventId: string; previous: number | null; changes: LiveChange[] };
export const emptyLiveSession = (eventId: string): LiveSession => ({ eventId, previous: null, changes: [] });

export function acceptOccupancy(previous: LiveSession, snapshot: Occupancy, at: string): LiveSession {
  const session = previous.eventId === snapshot.event_id ? previous : emptyLiveSession(snapshot.event_id);
  const count = snapshot.registered_count;
  if (session.previous === count) return session;
  const delta = session.previous === null ? 0 : count - session.previous;
  return {
    eventId: snapshot.event_id, previous: count,
    changes: delta ? [{ id: `${at}:${session.changes.length}:${count}`, delta, at }, ...session.changes].slice(0, 20) : session.changes,
  };
}
