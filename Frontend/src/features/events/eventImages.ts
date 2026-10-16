import type { Event } from '../../types';

// Photographs are shipped with the web app, so blank covers work offline too.
export const EVENT_COVERS = [
  { value: '/images/events/coding.webp', label: 'Programming' },
  { value: '/images/events/workshop.webp', label: 'Workshop & collaboration' },
  { value: '/images/events/workspace.webp', label: 'Developer workspace' },
  { value: '/images/events/infrastructure.webp', label: 'Servers & infrastructure' },
  { value: '/images/events/conference.webp', label: 'Conference & meetup' },
] as const;

export function validEventImage(value: string): boolean {
  const image = value.trim();
  if (!image || image.length > 500) return false;
  if (EVENT_COVERS.some(cover => cover.value === image)) return true;
  try {
    const url = new URL(image);
    return ['https:', 'http:'].includes(url.protocol) && !url.username && !url.password;
  } catch { return false; }
}

export function fallbackEventImage(event: Pick<Event, 'title' | 'category'>): string {
  const topic = `${event.title} ${event.category}`.toLowerCase();
  if (/postgres|database|docker|architecture|infrastructure|security|oauth|jwt/.test(topic)) return EVENT_COVERS[3].value;
  if (/meetup|forum|seminar|engineering day|documentation day|conference/.test(topic)) return EVENT_COVERS[4].value;
  if (/git|collaboration|bootcamp|workshop/.test(topic)) return EVENT_COVERS[1].value;
  if (/pydantic|validation|testing|design/.test(topic)) return EVENT_COVERS[2].value;
  return EVENT_COVERS[0].value;
}
