import { useEffect, useRef } from 'react';
import { Timer } from 'lucide-react';
import { useNow } from '../../realtime/useNow';
import { formatCountdown } from '../../lib/datetime';
import { strings } from '../../copy/strings';

const CHECKIN_LEAD_MS = 15 * 60_000;

/* Countdown to check-in opening (start − 15 min), then to start, then to end.
   Ticks every 1s when under 1 hour, every 30s otherwise. When a milestone hits
   zero, calls onZero once so the caller refetches (backend is the truth). */
export function Countdown({
  startTime,
  endTime,
  onZero,
  compact = false,
}: {
  startTime: string;
  endTime: string;
  onZero?: () => void;
  compact?: boolean;
}) {
  const start = new Date(startTime).getTime();
  const end = new Date(endTime).getTime();
  const openAt = start - CHECKIN_LEAD_MS;
  const slow = useNow(30_000);
  const upcoming = [openAt, start, end].filter((t) => t - slow > 0);
  const target = upcoming.length ? Math.min(...upcoming) : Infinity;
  const urgent = target - slow < 3_600_000;
  const now = useNow(urgent ? 1000 : 30_000);

  const phase = now < openAt ? 0 : now < start ? 1 : now < end ? 2 : 3;
  const previous = useRef({ start, end, phase });
  useEffect(() => {
    const before = previous.current;
    if (before.start === start && before.end === end && before.phase !== phase) onZero?.();
    previous.current = { start, end, phase };
  }, [start, end, phase, onZero]);

  let text: string | null = null;
  if (start > now) text = strings.clock.startsIn(formatCountdown(start - now));
  else if (end > now) text = strings.clock.endsIn(formatCountdown(end - now));
  if (!text) return null;

  if (compact) {
    return (
      <span className="countdown-inline" aria-live="polite">
        <Timer size={13} /> {text}
      </span>
    );
  }
  return (
    <div className="countdown" aria-live="polite">
      <Timer />
      <span>{text}</span>
    </div>
  );
}
