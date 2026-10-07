import type { Event } from '../../types';
import { strings } from '../../copy/strings';

export function upcomingStaffChecks(events: Event[], now: number) {
  return events.filter(event => ['PUBLISHED', 'ONGOING', 'STARTED'].includes(event.status) && +new Date(event.endTime) > now)
    .sort((a, b) => +new Date(a.startTime) - +new Date(b.startTime)).slice(0, 5);
}

export function attentionReasons(event: Event, now: number, staffCount?: number) {
  const copy = strings.organizer.attentionReasons;
  const reasons: string[] = [];
  if (event.status === 'DRAFT') reasons.push(copy.draft);
  if (event.status === 'ONGOING') reasons.push(copy.preparing);
  if (event.status === 'STARTED') reasons.push(copy.started);
  if (event.status === 'PUBLISHED') {
    const until = +new Date(event.startTime) - now;
    if (until <= 0) reasons.push(copy.overdue);
    else if (until <= 3_600_000) reasons.push(copy.soon);
    if (event.registeredCount >= event.capacity) reasons.push(copy.full);
    else if (event.registeredCount >= event.capacity * .9) reasons.push(copy.nearlyFull);
  }
  if (['PUBLISHED', 'ONGOING'].includes(event.status) && +new Date(event.startTime) > now && staffCount === 0) reasons.push(copy.noStaff);
  return reasons;
}

export function priorityEvent(events: Event[], now: number) {
  const ordered = [...events].sort((a, b) => +new Date(a.startTime) - +new Date(b.startTime));
  return ordered.find(event => event.status === 'STARTED')
    ?? ordered.find(event => event.status === 'ONGOING')
    ?? ordered.find(event => event.status === 'PUBLISHED' && +new Date(event.endTime) > now)
    ?? ordered.find(event => event.status === 'DRAFT');
}
