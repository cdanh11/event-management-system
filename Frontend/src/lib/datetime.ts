/* Single place for all date rendering.
   Backend may return naive UTC without a "Z" suffix (e.g. "2026-10-05T14:06:13.202717"):
   treat naive values as UTC, then display in the browser's timezone. Never show raw ISO. */

import { strings } from '../copy/strings';

export function parseUtc(value: string): Date {
  const hasZone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(value);
  return new Date(hasZone ? value : `${value}Z`);
}

export const parseApiDate = parseUtc;

// Local backend stores event start/end as server wall-clock (models.localnow).
// Unlike audit timestamps, naive EVENT dates must not be reinterpreted as UTC.
export function parseEventDate(value: string): Date {
  return new Date(value);
}

export function toInputValue(value: string | Date): string {
  const date = value instanceof Date ? value : parseApiDate(value);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export function fromInputValue(value: string): string {
  return new Date(value).toISOString();
}

// Sending naive local event time matches this backend's wall-clock contract.
export function toEventPayloadDate(value: string): string {
  return toInputValue(parseEventDate(value));
}

export function formatDay(value: string): string {
  return new Intl.DateTimeFormat('en-US', { weekday: 'short', month: 'short', day: 'numeric' }).format(parseApiDate(value));
}

export function formatRange(start: string, end: string): string {
  return formatWhen(start, end);
}

/** Event services normalize wall-clock dates to ISO before rendering. */
export function formatWhen(start: string, end: string, now = new Date()): string {
  const first = parseApiDate(start);
  const last = parseApiDate(end);
  const day = (date: Date) => new Intl.DateTimeFormat('en-US', {
    weekday: 'short', month: 'short', day: 'numeric',
    ...(date.getFullYear() !== now.getFullYear() && { year: 'numeric' }),
  }).format(date);
  const sameDay = first.toDateString() === last.toDateString();
  return `${day(first)}, ${timeFmt.format(first)} to ${sameDay ? '' : `${day(last)}, `}${timeFmt.format(last)}`;
}

const dateFmt = new Intl.DateTimeFormat('en-US', {
  month: 'short',
  day: 'numeric',
  year: 'numeric',
});
const timeFmt = new Intl.DateTimeFormat('en-US', { hour: 'numeric', minute: '2-digit' });


export function formatDate(value: string): string {
  return dateFmt.format(parseUtc(value));
}

export function formatTime(value: string): string {
  return timeFmt.format(parseUtc(value));
}

export function formatDateTime(value: string): string {
  const d = parseUtc(value);
  return `${formatDate(value)}, ${timeFmt.format(d)}`;
}

const MIN = 60_000;
const HOUR = 3_600_000;
const DAY = 86_400_000;

export function formatRelative(value: string, now: number = Date.now(), precise = false): string {
  const diff = now - parseUtc(value).getTime();
  if (precise && diff >= 1000 && diff < MIN) return strings.clock.secondsAgo(Math.floor(diff / 1000));
  if (diff < MIN) return strings.clock.justNow;
  if (diff < HOUR) {
    const m = Math.floor(diff / MIN);
    return strings.clock.minutesAgo(m);
  }
  if (diff < DAY) {
    const h = Math.floor(diff / HOUR);
    return strings.clock.hoursAgo(h);
  }
  const d = Math.floor(diff / DAY);
  return strings.clock.daysAgo(d);
}

export function formatCountdown(ms: number): string {
  const s = Math.max(0, Math.floor(ms / 1000));
  const d = Math.floor(s / 86400);
  const h = String(Math.floor((s % 86400) / 3600)).padStart(2, '0');
  const m = String(Math.floor((s % 3600) / 60)).padStart(2, '0');
  const sec = String(s % 60).padStart(2, '0');
  if (d > 0) return `${d}d ${h}h`;
  if (s >= 3600) return `${h}:${m}:${sec}`;
  return `${m}:${sec}`;
}
