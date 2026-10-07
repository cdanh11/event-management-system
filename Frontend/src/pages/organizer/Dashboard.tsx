import { Link } from 'react-router-dom';
import { useQuery } from '../../hooks/useQuery';
import { organizerService, staffService } from '../../services/services';
import { PageHeader } from '../../components/ui/PageHeader';
import { OrganizerAgenda } from '../../components/ui/OrganizerAgenda';
import { EmptyState, ErrorBlock, Skeleton } from '../../components/ui/states';
import { attentionReasons, priorityEvent, upcomingStaffChecks } from '../../features/events/organizer';
import { formatCountdown } from '../../lib/datetime';
import { friendlyError } from '../../lib/errors';
import { useNow } from '../../realtime/useNow';
import { strings } from '../../copy/strings';

export function Dashboard() {
  const now = useNow(30_000);
  const query = useQuery(organizerService.dashboard, [], { refetchInterval: 10_000 });
  const events = query.data?.events ?? [];
  const checks = upcomingStaffChecks(events, now);
  const checkKey = checks.map(event => event.id).join(',');
  const staff = useQuery(async signal => Object.fromEntries(await Promise.all(checks.map(async event =>
    [event.id, (await staffService.assignedTo(event.id, signal)).length] as const))), [checkKey], { enabled: checks.length > 0, refetchInterval: 10_000 });
  const priority = priorityEvent(events, now);
  const attention = events.map(event => ({ event, reasons: attentionReasons(event, now, staff.data?.[event.id]) }))
    .filter(row => row.reasons.length).sort((a, b) => a.event.id === priority?.id ? -1 : b.event.id === priority?.id ? 1 : +new Date(a.event.startTime) - +new Date(b.event.startTime));
  const next = [...events].filter(event => !['COMPLETED', 'CANCELLED'].includes(event.status))
    .sort((a, b) => +new Date(a.startTime) - +new Date(b.startTime)).slice(0, 5);
  const copy = strings.organizer;

  return <div>
    <PageHeader title={copy.overview} />
    {query.error && <ErrorBlock message={friendlyError(query.error)} onRetry={() => void query.refetch()} />}
    {query.isLoading ? <><Skeleton kind="row" /><Skeleton kind="stat" /><Skeleton kind="row" /></> : query.data && <>
      {priority && <section className="organizer-priority">
        <p>{priority.status === 'STARTED' ? copy.currentEvent(priority.title)
          : priority.status === 'DRAFT' ? copy.draftEvent(priority.title)
            : copy.nextEvent(priority.title,formatCountdown(+new Date(priority.startTime)-now))}</p>
        <Link className="btn btn-primary" to={`/organizer/events/${priority.id}`}>{strings.common.manage}</Link>
      </section>}
      {!priority && <p className="hint">{copy.nothingScheduled}</p>}
      <section className="organizer-totals" aria-label={copy.overview}>
        <div className="organizer-total-main"><span>{copy.registered}</span><strong>{query.data.total_registrations}</strong></div>
        <div><span>{copy.checkedIn}</span><b>{query.data.total_checkins}</b></div>
        <div><span>{copy.eventsTitle}</span><b>{events.length}</b><small>{copy.publishedCount(events.filter(event => event.status === 'PUBLISHED').length)}</small></div>
      </section>
      {events.length ? <>
        <section><div className="section-title"><h2>{copy.needsAttention}</h2></div>
          {staff.error && <ErrorBlock message={friendlyError(staff.error)} onRetry={() => void staff.refetch()} />}
          {attention.length ? attention.slice(0,5).map(row => <OrganizerAgenda key={row.event.id} {...row} />) : <p className="hint">{copy.noAttention}</p>}
          <Link className="quiet-link" to="/organizer/events">{copy.allEvents}</Link>
        </section>
        <section><div className="section-title"><h2>{copy.nextEvents}</h2><Link to="/organizer/events">{copy.eventsTitle}</Link></div>
          {next.map(event => <OrganizerAgenda key={event.id} event={event} />)}
        </section>
      </> : <EmptyState title={copy.empty} body={copy.emptyBody} />}
    </>}
  </div>;
}
