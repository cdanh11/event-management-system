import { eventService } from '../../services/services';
import type { Event, Registration } from '../../types';

const cache = new Map<string, { event: Event; at: number }>();

export async function getCachedEvent(id: string, signal?: AbortSignal): Promise<Event> {
  const hit = cache.get(id);
  if (hit && Date.now() - hit.at < 8000) return hit.event;
  const event = await eventService.getEvent(id, signal);
  cache.set(id, { event, at: Date.now() });
  return event;
}

export async function registrationEvents(registrations: Registration[], signal?: AbortSignal) {
  const ids = [...new Set(registrations.map((registration) => registration.eventId))];
  return new Map(await Promise.all(ids.map(async (id) => [id, await getCachedEvent(id, signal)] as const)));
}
