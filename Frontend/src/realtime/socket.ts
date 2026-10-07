/* Shared WebSocket layer (see docs/design.md §4.4, §5).
   One SocketManager: ref-counted rooms per event, exponential backoff
   (1s,2s,4s,8s, max 15s + jitter), periodic keepalive pings,
   REST resync after reconnect, polling fallback when WS is unusable. */

import { request, wsBaseUrl } from '../api/apiClient';
import type { EventStatus } from '../types';
import { EVENT_STATUSES } from '../lib/status';

export type OccupancyMsg = {
  type?: string;
  event_id: string;
  capacity: number;
  registered_count: number;
  remaining: number;
  status: EventStatus;
};

export type ConnState = 'connecting' | 'open' | 'reconnecting' | 'closed';

type Listener = (msg: OccupancyMsg) => void;
type StateListener = (s: ConnState) => void;

const BACKOFF = [1000, 2000, 4000, 8000, 15000];

interface Room {
  ws: WebSocket | null;
  listeners: Set<Listener>;
  stateListeners: Set<StateListener>;
  state: ConnState;
  attempt: number;
  timer: ReturnType<typeof setTimeout> | undefined;
  lastMsg: number;
  checker: ReturnType<typeof setInterval> | undefined;
  resyncListeners: Set<() => void>;
  alive: boolean;
}

function jitter(ms: number): number {
  return Math.round(ms * (0.8 + Math.random() * 0.4));
}

class SocketManager {
  private rooms = new Map<string, Room>();

  private setState(room: Room, s: ConnState) {
    room.state = s;
    room.stateListeners.forEach((cb) => cb(s));
  }

  subscribe(
    eventId: string,
    listener: Listener,
    opts: { onState?: StateListener; onResync?: () => void } = {}
  ): () => void {
    const existing = this.rooms.get(eventId);
    let room: Room;
    if (existing) {
      room = existing;
    } else {
      room = {
        ws: null,
        listeners: new Set(),
        stateListeners: new Set(),
        state: 'connecting',
        attempt: 0,
        timer: undefined,
        lastMsg: 0,
        checker: undefined,
        resyncListeners: new Set(),
        alive: true,
      };
      this.rooms.set(eventId, room);
      const created: Room = room;
      room.checker = setInterval(() => {
        if (!created.alive || !created.listeners.size) return;
        // The server accepts ping text without replying. An idle room is healthy.
        if (created.ws?.readyState === WebSocket.OPEN) {
          try { created.ws.send('ping'); } catch { created.ws.close(); }
        }
      }, 20_000);
    }
    room.listeners.add(listener);
    if (opts.onState) {
      opts.onState(room.state);
      room.stateListeners.add(opts.onState);
    }
    if (opts.onResync) room.resyncListeners.add(opts.onResync);
    if (!existing) void this.connect(eventId, room);

    return () => {
      room.listeners.delete(listener);
      if (opts.onState) room.stateListeners.delete(opts.onState);
      if (opts.onResync) room.resyncListeners.delete(opts.onResync);
      if (!room.listeners.size) this.teardown(eventId);
    };
  }

  private teardown(eventId: string) {
    const room = this.rooms.get(eventId);
    if (!room) return;
    room.alive = false;
    if (room.timer) clearTimeout(room.timer);
    if (room.checker) clearInterval(room.checker);
    room.ws?.close();
    this.rooms.delete(eventId);
  }

  retry(eventId: string) {
    const room = this.rooms.get(eventId);
    if (!room || room.state !== 'closed') return;
    room.attempt = 0;
    void this.connect(eventId, room);
  }

  private async connect(eventId: string, room: Room) {
    if (!room.alive || !room.listeners.size) return;
    this.setState(room, room.attempt === 0 ? 'connecting' : 'reconnecting');
    let ticket: string;
    try {
      const res = await request<{ ticket: string }>('/ws/ticket', { method: 'POST' });
      ticket = res.ticket;
    } catch {
      return this.schedule(eventId, room);
    }
    if (!room.alive || !room.listeners.size) return;
    let ws: WebSocket;
    try {
      ws = new WebSocket(`${wsBaseUrl()}/ws/events/${eventId}?ticket=${encodeURIComponent(ticket)}`);
    } catch {
      return this.schedule(eventId, room);
    }
    room.ws = ws;
    room.lastMsg = Date.now();

    ws.onmessage = (e) => {
      room.lastMsg = Date.now();
      try {
        const msg = JSON.parse(e.data as string) as Partial<OccupancyMsg>;
        if (msg.event_id === eventId && typeof msg.registered_count === 'number'
          && typeof msg.capacity === 'number' && typeof msg.remaining === 'number'
          && EVENT_STATUSES.includes(msg.status as EventStatus)) {
          room.listeners.forEach((cb) =>
            cb({
              event_id: msg.event_id as string,
              capacity: Number(msg.capacity ?? 0),
              registered_count: Number(msg.registered_count ?? 0),
              remaining: Number(msg.remaining ?? 0),
              status: msg.status as EventStatus,
            })
          );
        }
      } catch {
        // Ignore malformed frames, keep last good state.
      }
    };

    ws.onopen = () => {
      if (!room.alive) return;
      const wasDown = room.attempt > 0;
      room.attempt = 0;
      this.setState(room, 'open');
      if (wasDown) room.resyncListeners.forEach((resync) => resync());
    };

    ws.onclose = (ev) => {
      if (!room.alive) return;
      if (ev.code === 4403 || ev.code === 4404) {
        this.setState(room, 'closed');
        return;
      }
      // 4401 (ticket used/expired) or network drop: mint a fresh ticket and retry.
      this.schedule(eventId, room);
    };

    ws.onerror = () => ws.close();
  }

  private schedule(eventId: string, room: Room) {
    if (!room.alive || !room.listeners.size) return;
    const idx = Math.min(room.attempt, BACKOFF.length - 1);
    const wait = room.attempt >= BACKOFF.length ? -1 : jitter(BACKOFF[idx]);
    room.attempt += 1;
    if (wait < 0) {
      this.setState(room, 'closed');
      return;
    }
    this.setState(room, 'reconnecting');
    room.timer = setTimeout(() => void this.connect(eventId, room), wait);
  }
}

export const socketManager = new SocketManager();
