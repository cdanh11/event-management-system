import { useState } from 'react';
import type { Event } from '../../types';
import { fallbackEventImage, validEventImage } from '../../features/events/eventImages';

export function EventImage({ event, eager = false }: {
  event: Pick<Event, 'title' | 'category' | 'bannerImage'>; eager?: boolean;
}) {
  const [failed, setFailed] = useState<string[]>([]);
  const supplied = event.bannerImage?.trim() ?? '';
  const fallback = fallbackEventImage(event);
  const source = validEventImage(supplied) && !failed.includes(supplied) ? supplied : fallback;
  return <div className="event-cover">
    {!failed.includes(source) && <img key={source} src={source} alt="" width={1200} height={675}
      loading={eager ? 'eager' : 'lazy'} decoding="async" referrerPolicy="no-referrer"
      onError={() => setFailed(before => before.includes(source) ? before : [...before, source])} />}
  </div>;
}
