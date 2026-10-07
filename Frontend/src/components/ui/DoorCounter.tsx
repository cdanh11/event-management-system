import { strings } from '../../copy/strings';

/** Stable place keys keep unchanged digits still; only a changed digit rolls in. */
export function DoorCounter({ count, capacity }: { count: number; capacity: number }) {
  const digits = String(count).split('');
  return <div className="door-counter" role="status" aria-live="polite" aria-atomic="true">
    <span className="sr-only">{count} {strings.live.registered} {strings.live.ofCapacity(capacity)}</span>
    <div className="door-count-digits" aria-hidden="true">{digits.map((digit, index) => <span className="door-digit-place" key={digits.length - index}>
      <span className="door-digit" key={digit}>{digit}</span>
    </span>)}</div>
    <p aria-hidden="true">{strings.live.ofCapacity(capacity)} {strings.live.registered}</p>
  </div>;
}
