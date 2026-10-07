import { Link } from 'react-router-dom';
import type { CSSProperties } from 'react';
import type { Event, EventStatus, Registration } from '../../types';
import { statusLabel, statusColor, registrationOpen, registrationAction } from '../../lib/status';
import { formatTime } from '../../lib/datetime';
import { strings } from '../../copy/strings';
import { Countdown } from './Countdown';

export function DateBlock({ value }: { value: string }) {
  const date = new Date(value);
  return <time className="agenda-date" dateTime={value}>
    <b>{date.getDate()}</b>
    <span>{date.toLocaleDateString('en-US', { month: 'short' })}</span>
    <small>{date.toLocaleDateString('en-US', { weekday: 'short' })}</small>
  </time>;
}

export function StatusDot({ status }: { status: EventStatus }) {
  return <span className={`status-dot status-dot-${status.toLowerCase()}`} style={{ '--status-color': statusColor(status) } as CSSProperties}><i aria-hidden />{statusLabel(status)}</span>;
}

export function OccupancyMeter({ count, capacity, status, label: customLabel }: { count: number; capacity: number; status?: EventStatus; label?: string }) {
  const remaining = Math.max(0, capacity - count);
  const percent = capacity > 0 ? Math.min(100, count / capacity * 100) : 0;
  const terminal = status === 'COMPLETED' || status === 'CANCELLED';
  const label = customLabel ?? (terminal ? `${count} registered` : remaining === 0 ? strings.explore.soldOut
    : remaining <= capacity * .1 ? strings.explore.low(remaining) : strings.explore.left(remaining, capacity));
  return <div className={`agenda-occupancy${terminal ? ' is-terminal' : remaining === 0 ? ' is-full' : percent >= 90 ? ' is-urgent' : ''}${!terminal && remaining > 0 && percent >= 90 ? ' is-low' : ''}`}>
    <span>{label}</span>
    <div role="meter" aria-label={label} aria-valuemin={0} aria-valuemax={capacity} aria-valuenow={Math.min(count, capacity)}>
      <i style={{ width: `${percent}%` }} />
    </div>
  </div>;
}

export function AgendaRow({ event, now, registration, onTicket, ticketBusy }: { event: Event; now: number; registration?: Registration; onTicket: (registration: Registration) => void; ticketBusy: boolean }) {
  const open = registrationOpen(event, now);
  const action = registrationAction(event, 'ATTENDEE', registration, now);
  return <article className={`agenda-row agenda-row-${event.status.toLowerCase()}`} style={{ borderLeftColor: statusColor(event.status) }}>
    <DateBlock value={event.startTime} />
    <div className="agenda-description">
      <h2><Link className="agenda-event-link" to={`/events/${event.id}`}>{event.title}</Link></h2>
      <p>{event.location}</p><small>{formatTime(event.startTime)}</small>
      {event.status !== 'PUBLISHED' && <StatusDot status={event.status} />}
    </div>
    <OccupancyMeter count={event.registeredCount} capacity={event.capacity} status={event.status} />
    <div className="agenda-action">
      {action === 'ticket' ? <><span className="registered-link">{strings.detail.registeredMark}</span><button className="btn btn-link" disabled={ticketBusy} onClick={() => registration && onTicket(registration)}>{ticketBusy ? strings.common.loading : strings.common.viewTicket}</button></>
        : action === 'registration-cancelled' ? <small>{strings.registrations.cancelledTicket}</small>
        : action === 'register'
          ? <Link className="btn btn-secondary" to={`/events/${event.id}`}>{strings.detail.register}</Link>
          : event.status === 'PUBLISHED' && !open ? <small>{strings.explore.closed}</small> : null}
    </div>
  </article>;
}

export function PosterBand({ event, onTicket, busy }: { event: Event; onTicket: () => void; busy: boolean }) {
  return <section className="poster-band" aria-label={strings.explore.nextTicket}>
    <DateBlock value={event.startTime} />
    <div><small>{strings.explore.nextTicket}</small><h2><Link to={`/events/${event.id}`}>{event.title}</Link></h2><p>{event.location}</p></div>
    <div className="poster-action">
      {event.status === 'STARTED' ? <StatusDot status={event.status} /> : <Countdown compact startTime={event.startTime} endTime={event.endTime} />}
      <button className="btn btn-secondary" disabled={busy} onClick={onTicket}>{busy ? strings.common.loading : strings.common.viewTicket}</button>
    </div>
  </section>;
}
