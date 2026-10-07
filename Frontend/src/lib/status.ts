/* Canonical event status, permissions and display metadata shared by all pages. */

import type { Event, EventStatus, Role, Registration } from '../types';
import { parseApiDate, formatTime, formatCountdown } from './datetime';
import { strings } from '../copy/strings';
export type EventStatusKey = EventStatus;

export const EVENT_STATUSES: EventStatus[] = ['DRAFT', 'PUBLISHED', 'ONGOING', 'STARTED', 'COMPLETED', 'CANCELLED'];
export const LIFECYCLE_STEPS = EVENT_STATUSES.filter((status) => status !== 'CANCELLED');
export const DOOR_OPEN: EventStatus[] = ['STARTED'];
export const CHECKIN_ROLES: Role[] = ['STAFF', 'ORGANIZER'];
export const SCHEDULE_EDITABLE: EventStatus[] = ['DRAFT', 'PUBLISHED'];
export const LIVE_STATUSES: EventStatus[] = ['PUBLISHED', 'ONGOING', 'STARTED'];

export function registrationOpen(event: Event, now = Date.now()) {
  return event.status === 'PUBLISHED' && now < parseApiDate(event.startTime).getTime();
}
export const doorOpen = (status: EventStatus) => DOOR_OPEN.includes(status);
export const canCheckin = (role: Role, status: EventStatus) => CHECKIN_ROLES.includes(role) && doorOpen(status);
export const canReschedule = (status: EventStatus) => SCHEDULE_EDITABLE.includes(status);

export function registrationAction(event: Event, role: Role | undefined, registration: Registration | undefined, now: number) {
  if (event.status === 'CANCELLED') return 'event-cancelled';
  if (registration?.status === 'CANCELLED') return 'registration-cancelled';
  if (registration?.status === 'REGISTERED') return 'ticket';
  if (event.status === 'COMPLETED') return 'ended';
  if (!role) return 'sign-in';
  if (role !== 'ATTENDEE') return 'attendee-only';
  if (!registrationOpen(event, now)) return 'closed';
  if (event.registeredCount >= event.capacity) return 'sold-out';
  return 'register';
}

const TRANSITIONS: Record<EventStatus, EventStatus[]> = {
  DRAFT: ['PUBLISHED', 'CANCELLED'],
  PUBLISHED: ['ONGOING', 'STARTED', 'CANCELLED'],
  ONGOING: ['STARTED', 'CANCELLED'],
  STARTED: ['COMPLETED'],
  COMPLETED: [],
  CANCELLED: [],
};
export const nextActions = (status: EventStatus) => TRANSITIONS[status];

export function preferredLiveEvent(events: Event[]) {
  const ordered = [...events].sort((a, b) => +parseApiDate(a.startTime) - +parseApiDate(b.startTime));
  return ordered.find((event) => doorOpen(event.status))
    ?? ordered.find((event) => event.status === 'ONGOING')
    ?? ordered.find((event) => event.status === 'PUBLISHED')
    ?? [...ordered].reverse().find((event) => event.status !== 'DRAFT')
    ?? ordered[0];
}

export const STATUS_META = Object.fromEntries(EVENT_STATUSES.map(status => [status, {
  ...strings.status[status], color: `var(--status-${status.toLowerCase()}-fg)`,
}])) as Record<EventStatusKey, { label: string; hint: string; color: string }>;
export const statusColor = (status: EventStatus) => STATUS_META[status].color;
export const AGENDA_STATUSES: Record<'open' | 'happening' | 'past', EventStatus[]> = {
  open: ['PUBLISHED'], happening: ['ONGOING', 'STARTED'], past: ['COMPLETED'],
};

export function doorDescription(event: Event, now = Date.now()): string {
  if (event.status === 'DRAFT') return 'Publish the event to let people register.';
  if (event.status === 'CANCELLED') return 'This event was cancelled.';
  if (event.status === 'COMPLETED') return 'This event has ended.';
  if (event.status === 'STARTED') return `Check-in is open until ${formatTime(event.endTime)}.`;
  const opens = +parseApiDate(event.startTime) - 15 * 60_000;
  if (now >= opens) return 'Check-in is due to open. Waiting for the server status update.';
  return event.status === 'ONGOING' ? `Check-in opens in ${formatCountdown(opens - now)}.`
    : `Check-in opens at ${formatTime(new Date(opens).toISOString())}.`;
}

/** Active events first; terminal events newest first; drafts last. */
export function compareOrganizerEvents(a: Event, b: Event): number {
  const rank = (event: Event) => event.status === 'STARTED' ? 0
    : LIVE_STATUSES.includes(event.status) ? 1 : event.status === 'DRAFT' ? 3 : 2;
  const group = rank(a) - rank(b);
  if (group) return group;
  const dates = +parseApiDate(a.startTime) - +parseApiDate(b.startTime);
  return (rank(a) === 2 ? -dates : dates) || a.id.localeCompare(b.id);
}

export function statusLabel(status: string): string {
  return (STATUS_META[status as EventStatusKey] ?? { label: status }).label;
}

export function statusHint(status: string): string {
  return (STATUS_META[status as EventStatusKey] ?? { hint: '' }).hint;
}
