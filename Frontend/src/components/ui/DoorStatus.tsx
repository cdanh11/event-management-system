import type { Event } from '../../types';
import { doorDescription } from '../../lib/status';
import { useNow } from '../../realtime/useNow';

export function DoorStatus({ event }: { event: Event }) {
  const now = useNow(1000);
  return <p className="door-status">{doorDescription(event, now)}</p>;
}
