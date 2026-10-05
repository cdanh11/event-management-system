import { useEffect, useRef, useState } from 'react';
import { request, wsBaseUrl } from '../api/apiClient';

export type Occupancy = {
  event_id: string;
  capacity: number;
  registered_count: number;
  remaining: number;
  status: string;
};

export type SocketStatus = 'connecting' | 'live' | 'reconnecting' | 'closed';

/**
 * Subscribe occupancy room của 1 event qua ticket handshake:
 * POST /ws/ticket (header Authorization) -> WS ?ticket= (một lần, 30s).
 * JWT không bao giờ đi trên query string.
 */
export function useOccupancySocket(eventId: string | null) {
  const [data, setData] = useState<Occupancy | null>(null);
  const [status, setStatus] = useState<SocketStatus>('connecting');
  const [error, setError] = useState<string | null>(null);
  const attempt = useRef(0);

  useEffect(() => {
    if (!eventId) return;
    let ws: WebSocket | null = null;
    let alive = true;
    let timer: ReturnType<typeof setTimeout> | undefined;

    const schedule = (fn: () => void) => {
      attempt.current += 1;
      if (attempt.current > 5) {
        if (alive) {
          setStatus('closed');
          setError('Không kết nối được realtime sau nhiều lần thử.');
        }
        return;
      }
      const backoff = Math.min(1000 * attempt.current, 5000);
      if (alive) setStatus('reconnecting');
      timer = setTimeout(fn, backoff);
    };

    const connect = async () => {
      if (!alive) return;
      setStatus(attempt.current === 0 ? 'connecting' : 'reconnecting');
      try {
        const { ticket } = await request<{ ticket: string }>('/ws/ticket', {
          method: 'POST',
        });
        if (!alive) return;
        ws = new WebSocket(
          `${wsBaseUrl()}/ws/events/${eventId}?ticket=${encodeURIComponent(ticket)}`
        );
      } catch {
        if (alive) {
          setStatus('closed');
          setError('Không lấy được WS ticket — hãy đăng nhập ORGANIZER lại.');
        }
        return;
      }

      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data as string) as Partial<Occupancy> & { type?: string };
          if (typeof msg.registered_count === 'number') {
            setData({
              event_id: (msg.event_id as string) ?? eventId,
              capacity: Number(msg.capacity ?? 0),
              registered_count: Number(msg.registered_count ?? 0),
              remaining: Number(
                msg.remaining ?? Number(msg.capacity ?? 0) - Number(msg.registered_count ?? 0)
              ),
              status: String(msg.status ?? ''),
            });
            setError(null);
          }
        } catch {
          // Bỏ qua frame lạ, giữ số cũ.
        }
      };

      ws.onopen = () => {
        attempt.current = 0;
        if (alive) setStatus('live');
      };

      ws.onclose = (ev) => {
        if (!alive) return;
        if (ev.code === 4403 || ev.code === 4404) {
          setStatus('closed');
          setError(
            ev.code === 4403
              ? 'Kênh realtime chỉ dành cho ORGANIZER.'
              : 'Event không tồn tại.'
          );
          return;
        }
        // 4401 (ticket hết hạn/dùng rồi) hoặc rớt mạng: lấy ticket mới + thử lại.
        schedule(() => void connect());
      };

      ws.onerror = () => ws?.close();
    };

    void connect();
    return () => {
      alive = false;
      if (timer) clearTimeout(timer);
      ws?.close();
    };
  }, [eventId]);

  return { data, status, error };
}
