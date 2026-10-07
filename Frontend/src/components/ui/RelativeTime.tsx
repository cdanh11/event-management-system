import { useNow } from '../../realtime/useNow';
import { formatDateTime, formatRelative } from '../../lib/datetime';

/* "just now / 2 min ago", refreshed every 30s via the shared clock,
   absolute time on hover. */
export function RelativeTime({ value, every = 30_000 }: { value: string; every?: number }) {
  const now = useNow(every);
  return (
    <span title={formatDateTime(value)}>
      {formatRelative(value, now, every === 1000)}
    </span>
  );
}
