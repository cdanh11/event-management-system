import { useState } from 'react';
import { useAsync } from '../../hooks/useAsync';
import { eventService } from '../../services/services';
import { useOccupancySocket } from '../../realtime/useOccupancySocket';

/**
 * Phase 0 — Dashboard realtime cho ORGANIZER.
 * Component presentational tách khỏi hook socket để sau này áp theme
 * promax chỉ cần thay JSX/CSS, không chạm logic realtime.
 */
export function LiveDashboard() {
  const { data: events } = useAsync(eventService.getEvents, []);
  const [selected, setSelected] = useState<string | null>(null);
  const activeId = selected ?? events?.[0]?.id ?? null;
  const { data, status, error } = useOccupancySocket(activeId);

  const dot =
    status === 'live' ? '#1a7f4b' : status === 'closed' ? '#b3261e' : '#b7791f';

  return (
    <section>
      <div className="section-title">
        <h2>Realtime occupancy</h2>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
          <i
            style={{
              width: 10,
              height: 10,
              borderRadius: '50%',
              background: dot,
              display: 'inline-block',
            }}
          />
          {status === 'live'
            ? 'LIVE'
            : status === 'closed'
              ? 'CLOSED'
              : status === 'reconnecting'
                ? 'RECONNECTING…'
                : 'CONNECTING…'}
        </span>
      </div>

      <div className="toolbar">
        <select
          value={activeId ?? ''}
          onChange={(e) => setSelected(e.target.value || null)}
        >
          {(events ?? []).map((e) => (
            <option key={e.id} value={e.id}>
              {e.title} — {e.status}
            </option>
          ))}
        </select>
      </div>

      {error && <div className="notice error">{error}</div>}

      {data ? (
        <div className="metrics">
          <div className="metric">
            <span>Capacity</span>
            <b>{data.capacity}</b>
          </div>
          <div className="metric">
            <span>Registered</span>
            <b>{data.registered_count}</b>
          </div>
          <div className="metric">
            <span>Remaining — tự nhảy số</span>
            <b>{data.remaining}</b>
          </div>
          <div className="metric">
            <span>Status</span>
            <b>{data.status}</b>
          </div>
        </div>
      ) : (
        !error && <p>Chờ snapshot occupancy đầu tiên từ WebSocket…</p>
      )}

      <p className="hint">
        Mở 2 trình duyệt: Admin giữ trang này, Attendee đăng ký vé — số Remaining
        phải tự cập nhật không reload.
      </p>
    </section>
  );
}
