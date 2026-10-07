import type { Event } from '../../types';
import { AGENDA_STATUSES } from '../../lib/status';
import { eventService } from '../../services/services';

export type AgendaTab = 'open' | 'happening' | 'past';
const statuses = AGENDA_STATUSES;

/** Refresh the pages already visible, using separate cursors for each status. */
export async function loadAgenda(tab: AgendaTab, q: string, pages: number, signal: AbortSignal) {
  const streams = await Promise.all(statuses[tab].map(async (status) => {
    let cursor: string | undefined;
    const items: Event[] = [];
    for (let page = 0; page < pages; page += 1) {
      const result = await eventService.list({ q, status, limit: 20, cursor }, signal);
      items.push(...result.items);
      cursor = result.nextCursor;
      if (!cursor) break;
    }
    return { items, hasMore: !!cursor };
  }));
  return {
    items: [...new Map(streams.flatMap((stream) => stream.items).map((event) => [event.id, event])).values()],
    hasMore: streams.some((stream) => stream.hasMore),
  };
}

export function visibleAgenda(events: Event[], tab: AgendaTab, now: number, latest = false) {
  return events.filter((event) => statuses[tab].includes(event.status)
    && (tab !== 'open' || +new Date(event.startTime) > now))
    .sort((a, b) => (latest ? -1 : 1) * (+new Date(a.startTime) - +new Date(b.startTime)) || a.id.localeCompare(b.id));
}
