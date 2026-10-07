import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, CalendarDays, MapPin } from 'lucide-react';
import { useAuth } from '../../features/auth/useAuth';
import { useQuery } from '../../hooks/useQuery';
import { useOccupancy } from '../../realtime/useOccupancy';
import { useToast } from '../../components/ui/Toast';
import { eventService, registrationService, ticketService } from '../../services/services';
import { Button } from '../../components/ui/Button';
import { DoorStatus } from '../../components/ui/DoorStatus';
import { ConfirmDialog } from '../../components/ui/Modal';
import { ErrorBlock, Skeleton } from '../../components/ui/states';
import { OccupancyMeter, StatusDot } from '../../components/ui/Agenda';
import { formatWhen } from '../../lib/datetime';
import { strings } from '../../copy/strings';
import { LIVE_STATUSES, registrationAction, statusLabel } from '../../lib/status';
import { friendlyError } from '../../lib/errors';
import { useNow } from '../../realtime/useNow';
import type { EventStatus } from '../../types';

export function EventDetail() {
  const now = useNow(1000);
  const { id = '' } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [cancelOpen, setCancelOpen] = useState(false);
  const [actionError, setActionError] = useState('');
  const [busy, setBusy] = useState(false);
  const previous = useRef<{ id: string; status: string; remaining: number } | undefined>(undefined);
  const eventQuery = useQuery((signal) => eventService.getEvent(id, signal), [id], {
    refetchInterval: (data) => !data || LIVE_STATUSES.includes(data.status) ? 8000 : undefined,
  });
  const mine = useQuery((signal) => registrationService.mine(user!.id, signal), [user?.id, user?.role], { enabled: user?.role === 'ATTENDEE', refetchInterval: 15_000 });
  const { data: live } = useOccupancy(user && eventQuery.data && LIVE_STATUSES.includes(eventQuery.data.status) ? id : null, {
    refetch: async (signal) => {
      const event = await eventService.getEvent(id, signal);
      return { data: { event_id: event.id, capacity: event.capacity, registered_count: event.registeredCount,
        remaining: Math.max(0, event.capacity - event.registeredCount), status: event.status } };
    },
  });
  const event = useMemo(() => eventQuery.data && { ...eventQuery.data, status: (live?.status as EventStatus | undefined) ?? eventQuery.data.status,
    registeredCount: live?.registered_count ?? eventQuery.data.registeredCount }, [eventQuery.data, live]);
  useEffect(() => {
    if (!event) return;
    const remaining = Math.max(0, event.capacity - event.registeredCount);
    const before = previous.current;
    if (before?.id === event.id) {
      if (before.status !== event.status) toast(statusLabel(event.status), event.status === 'CANCELLED' ? 'warning' : 'info');
      if (before.remaining > 0 && remaining === 0) toast(strings.detail.justSoldOut, 'info');
    }
    previous.current = { id: event.id, status: event.status, remaining };
  }, [event, toast]);
  const myReg = mine.data?.find((reg) => reg.eventId === id);
  const openTicket = async () => {
    if (!myReg || busy) return;
    setBusy(true);
    try { navigate(`/tickets/${(await ticketService.forRegistration(myReg.id)).id}`); }
    catch (error) { toast(friendlyError(error), 'error'); }
    finally { setBusy(false); }
  };
  const register = async () => {
    if (!event || !user || busy) return;
    setBusy(true); setActionError('');
    try {
      const result = await registrationService.register(event.id, user);
      toast(strings.detail.registeredToast, 'success');
      setConfirmOpen(false);
      navigate(`/tickets/${result.ticket.id}`);
    } catch (error) {
      setActionError(friendlyError(error));
      void eventQuery.refetch(); void mine.refetch();
    } finally { setBusy(false); }
  };
  const cancel = async () => {
    if (!myReg || busy) return;
    if (event?.status !== 'PUBLISHED') { setActionError(strings.registrations.cancellationLocked); return; }
    setBusy(true); setActionError('');
    try {
      const cancelled = await registrationService.cancel(myReg.id);
      if (mine.data) mine.setData(mine.data.map(reg => reg.id === cancelled.id ? cancelled : reg));
      toast(strings.registrations.cancelToast, 'success');
      await Promise.all([mine.refetch(), eventQuery.refetch()]);
      setCancelOpen(false);
    } catch (error) { setActionError(friendlyError(error)); }
    finally { setBusy(false); }
  };
  if (eventQuery.isLoading) return <><Skeleton kind="card" /><Skeleton kind="row" /></>;
  if (!event) return <ErrorBlock message={friendlyError(eventQuery.error)} onRetry={() => void eventQuery.refetch()} />;
  const action = registrationAction(event, user?.role, myReg, now);
  let cta: ReactNode;
  if (user?.role === 'ORGANIZER') cta = <>
    {user.id === event.organizerId && <Link className="btn btn-primary" to={`/organizer/events/${id}`}>{strings.detail.manageEvent}</Link>}
    <p>{strings.detail.organizerView}</p>
  </>;
  else if (user?.role === 'STAFF') cta = <p>{strings.detail.staffView}</p>;
  else if (mine.isLoading) cta = <Button disabled>{strings.common.loading}</Button>;
  else if (mine.error && !mine.data) cta = <ErrorBlock message={friendlyError(mine.error)} onRetry={() => void mine.refetch()} />;
  else if (action === 'ticket') cta = <><p className="checked-in">{strings.detail.going}</p><Button loading={busy} onClick={() => void openTicket()}>{strings.common.viewTicket}</Button>
    {event.status === 'PUBLISHED' && <button className="text-button" onClick={() => { setActionError(''); setCancelOpen(true); }}>{strings.registrations.cancelTitle}</button>}</>;
  else if (action === 'register') cta = <Button onClick={() => { setActionError(''); setConfirmOpen(true); }}>{strings.detail.register}</Button>;
  else if (action === 'sign-in') cta = <Button onClick={() => navigate('/login', { state: { from: `/events/${id}` } })}>{strings.detail.signInToRegister}</Button>;
  else cta = <p>{action === 'event-cancelled' ? strings.detail.cancelledBanner
    : action === 'registration-cancelled' ? strings.detail.previouslyCancelled
      : action === 'ended' ? strings.detail.eventEnded : action === 'attendee-only' ? strings.detail.attendeeOnly
        : action === 'sold-out' ? strings.explore.soldOut : strings.explore.closed}</p>;
  return <div className="event-detail-page">
    <Link to="/events" className="back-link"><ArrowLeft size={15} />{strings.detail.back}</Link>
    {eventQuery.error && <ErrorBlock message={friendlyError(eventQuery.error)} onRetry={() => void eventQuery.refetch()} />}
    {event.status === 'CANCELLED' && <p className="notice error">{strings.detail.cancelledBanner}</p>}
    <div className="event-detail-layout">
      <section className="event-detail-copy">
        <h1>{event.title}</h1><p className="event-category">{event.category}</p><StatusDot status={event.status} />
        <div className="event-mobile-facts"><p>{formatWhen(event.startTime,event.endTime)}</p><p>{event.location}</p></div>
        <h2>{strings.detail.about}</h2><p className="event-description">{event.description}</p>
      </section>
      <aside className="event-reservation" aria-label={strings.detail.actionRegion}>
        <div className="reservation-facts"><p><CalendarDays size={18} /><span>{formatWhen(event.startTime,event.endTime)}</span></p><p><MapPin size={18} />{event.location}</p>
          <DoorStatus event={event} />
        </div>
        <OccupancyMeter count={event.registeredCount} capacity={event.capacity} status={event.status} />
        <div className="reservation-action">{cta}</div>
      </aside>
    </div>
    <ConfirmDialog open={confirmOpen} title={strings.detail.confirmTitle} message={strings.detail.confirmBody(event.title)} confirmLabel={strings.detail.register}
      busy={busy} error={actionError} onConfirm={() => void register()} onCancel={() => setConfirmOpen(false)} />
    <ConfirmDialog open={cancelOpen} title={strings.registrations.cancelTitle} message={strings.registrations.cancellationWarning(event.title)} confirmLabel={strings.registrations.cancelTitle}
      tone="danger" busy={busy} error={actionError} onConfirm={() => void cancel()} onCancel={() => setCancelOpen(false)} />
  </div>;
}
