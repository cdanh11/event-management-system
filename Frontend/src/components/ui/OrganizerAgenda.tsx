import { Link } from 'react-router-dom';
import type { CSSProperties } from 'react';
import type { Event } from '../../types';
import { OccupancyMeter, StatusDot } from './Agenda';
import { EventImage } from './EventImage';
import { formatWhen } from '../../lib/datetime';
import { statusColor } from '../../lib/status';
import { strings } from '../../copy/strings';

export function OrganizerAgenda({ event, reasons = [] }: { event: Event; reasons?: string[] }) {
  return <Link to={`/organizer/events/${event.id}`} className="event-card organizer-event-card" style={{ '--event-status-color': statusColor(event.status) } as CSSProperties}>
    <EventImage event={event} />
    <div className="event-card-body">
    <div className="event-card-meta"><span>{event.category}</span><StatusDot status={event.status} /></div>
    <div className="agenda-description">
      <h2 title={event.title}>{event.title}</h2>
      <p>{event.location}</p><time dateTime={event.startTime}>{formatWhen(event.startTime, event.endTime)}</time>
      {!!reasons.length && <p className="attention-reason">{reasons[0]}</p>}
    </div>
    <OccupancyMeter count={event.registeredCount} capacity={event.capacity} status={event.status} />
    <span className="event-card-manage">{strings.common.manage}<span aria-hidden>›</span></span>
    </div>
  </Link>;
}
