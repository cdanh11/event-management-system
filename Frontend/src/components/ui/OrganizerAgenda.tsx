import { Link } from 'react-router-dom';
import type { Event } from '../../types';
import { DateBlock, OccupancyMeter, StatusDot } from './Agenda';
import { formatTime } from '../../lib/datetime';
import { statusColor } from '../../lib/status';

export function OrganizerAgenda({ event, reasons = [] }: { event: Event; reasons?: string[] }) {
  return <Link to={`/organizer/events/${event.id}`} className={`agenda-row organizer-agenda agenda-row-${event.status.toLowerCase()}`} style={{ borderLeftColor: statusColor(event.status) }}>
    <DateBlock value={event.startTime} />
    <div className="agenda-description">
      <h2>{event.title}</h2>
      <p>{event.location}</p><small>{formatTime(event.startTime)}</small>
      {reasons.length ? <p className="attention-reason">{reasons[0]}</p> : <StatusDot status={event.status} />}
    </div>
    <OccupancyMeter count={event.registeredCount} capacity={event.capacity} status={event.status} />
    <span className="agenda-arrow" aria-hidden>›</span>
  </Link>;
}
