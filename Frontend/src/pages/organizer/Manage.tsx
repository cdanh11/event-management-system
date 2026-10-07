import { Fragment, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useAuth } from '../../features/auth/useAuth';
import { useQuery } from '../../hooks/useQuery';
import { useOccupancy } from '../../realtime/useOccupancy';
import { eventService } from '../../services/services';
import type { Event, EventStatus } from '../../types';
import { PageHeader } from '../../components/ui/PageHeader';
import { ErrorBlock, Skeleton } from '../../components/ui/states';
import { StatusDot, OccupancyMeter } from '../../components/ui/Agenda';
import { ConnectionIndicator } from '../../components/ui/ConnectionIndicator';
import { DoorStatus } from '../../components/ui/DoorStatus';
import { Tabs } from '../../components/ui/Tabs';
import { DoorWorkspace } from '../../features/door/DoorDesk';
import { ManageActions } from '../../features/organizer/ManageActions';
import { ScheduleForm } from '../../features/organizer/ScheduleForm';
import { StaffPanel } from '../../features/organizer/StaffPanel';
import { formatWhen } from '../../lib/datetime';
import { strings } from '../../copy/strings';
import { LIFECYCLE_STEPS, LIVE_STATUSES, statusLabel } from '../../lib/status';
import { friendlyError } from '../../lib/errors';
import { Forbidden } from '../errors';

function Stepper({ status }: { status: EventStatus }) {
  const cancelled = status === 'CANCELLED';
  const current = LIFECYCLE_STEPS.findIndex(step => step === status);
  if (cancelled) return <p className="notice error">{strings.manage.cancelledBanner}</p>;
  return <div>
    <ol className="event-stepper" aria-label={strings.manage.lifecycleLabel}>
      {LIFECYCLE_STEPS.map((step, index) => <Fragment key={step}>
        {index > 0 && <li className={`event-step-connector${index <= current ? ' is-done' : ''}`} aria-hidden />}
        <li aria-current={index === current ? 'step' : undefined} className={index < current ? 'is-done' : ''}>
          <span aria-hidden>{index < current ? '✓' : index === current ? '●' : index + 1}</span><b>{statusLabel(step)}</b>
        </li>
      </Fragment>)}
    </ol>
  </div>;
}
type Tab = 'overview' | 'staff' | 'schedule' | 'door';

function ManagedEvent({ initial }: { initial: Event }) {
  const { user } = useAuth();
  const query = useQuery(signal => eventService.getEvent(initial.id, signal), [initial.id], { refetchInterval: 10_000 });
  const event = query.data ?? initial;
  const [tab, setTab] = useState<Tab>('overview');
  const occupancy = useOccupancy(tab === 'overview' && LIVE_STATUSES.includes(event.status) ? event.id : null, {
    refetch: async signal => ({ data: await eventService.occupancy(event.id, signal) }),
    onSnapshot: snapshot => {
      if (snapshot.status !== event.status || snapshot.capacity !== event.capacity) void query.refetch();
    },
  });
  // REST owns lifecycle actions; a status broadcast triggers an immediate refresh.
  // Count snapshots remain live without letting an older WS frame undo a mutation.
  const current = { ...event, registeredCount: occupancy.data?.registered_count ?? event.registeredCount, capacity: occupancy.data?.capacity ?? event.capacity };
  const changed = (next: Event) => query.setData(next);
  const recheck = async () => { const fresh = await eventService.getEvent(event.id); changed(fresh); return fresh; };
  const copy = strings.manage;
  return <div className="event-manage-page">
    <Link className="back" to="/organizer/events">{copy.backEvents}</Link>
    <PageHeader title={event.title} actions={<Link className="quiet-link" to={`/events/${event.id}`}>{copy.publicPage}</Link>} />
    <div className="manage-event-meta"><StatusDot status={current.status} /><p>{formatWhen(event.startTime,event.endTime)}</p><p>{event.location}</p></div>
    {query.error && <ErrorBlock message={friendlyError(query.error)} onRetry={() => void query.refetch()} />}
    <Stepper status={current.status} />
    <ManageActions event={current} onChanged={changed} primary={tab === 'overview'} />
    <section className="manage-registration-summary" aria-live="polite">
      <p>{copy.registeredCount(current.registeredCount, current.capacity)} {occupancy.state === 'open' && <ConnectionIndicator state={occupancy.state} />}</p>
      <OccupancyMeter count={current.registeredCount} capacity={current.capacity} status={current.status} label={`${Math.max(0,current.capacity-current.registeredCount)} left`} />
    </section>
    {!!occupancy.error && <ErrorBlock message={friendlyError(occupancy.error)} onRetry={occupancy.retry} />}
    <Tabs<Tab> tabs={[{key:'overview',label:copy.overview},{key:'staff',label:copy.staff},{key:'schedule',label:copy.schedule},{key:'door',label:copy.door}]} active={tab} onChange={setTab} />
    <section className="manage-tab-content" role="tabpanel">
      {tab === 'overview' && <><dl className="event-facts">
        <dt>{copy.facts.when}</dt><dd>{formatWhen(event.startTime,event.endTime)}</dd>
        <dt>{copy.facts.where}</dt><dd>{event.location}</dd><dt>{copy.facts.category}</dt><dd>{event.category}</dd>
        <dt>{copy.facts.capacity}</dt><dd>{current.capacity}</dd><dt>{copy.facts.door}</dt><dd><DoorStatus event={current} /></dd>
      </dl><p className="event-description">{event.description}</p></>}
      {tab === 'staff' && <StaffPanel key={event.id} eventId={event.id} />}
      {tab === 'schedule' && <ScheduleForm key={event.id} event={current} onChanged={changed} />}
      {tab === 'door' && user && <DoorWorkspace event={current} user={user} recheck={recheck} />}
    </section>
  </div>;
}

export function Manage() {
  const { id = '' } = useParams();
  const { user } = useAuth();
  const query = useQuery(signal => eventService.getEvent(id, signal), [id]);
  if (query.isLoading) return <><PageHeader title={strings.detail.manageEvent} /><Skeleton kind="row" /><Skeleton kind="row" /></>;
  if (!query.data) return <ErrorBlock message={friendlyError(query.error)} onRetry={() => void query.refetch()} />;
  if (query.data.organizerId !== user?.id) return <Forbidden />;
  return <ManagedEvent key={id} initial={query.data} />;
}
