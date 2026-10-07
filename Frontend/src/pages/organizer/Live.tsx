import { useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '../../hooks/useQuery';
import { useOccupancy } from '../../realtime/useOccupancy';
import { eventService, organizerService } from '../../services/services';
import type { Event } from '../../types';
import { acceptOccupancy, emptyLiveSession } from '../../features/live/session';
import { PageHeader } from '../../components/ui/PageHeader';
import { Field, Select } from '../../components/ui/forms';
import { DoorCounter } from '../../components/ui/DoorCounter';
import { ConnectionIndicator } from '../../components/ui/ConnectionIndicator';
import { EmptyState, ErrorBlock, Skeleton } from '../../components/ui/states';
import { RelativeTime } from '../../components/ui/RelativeTime';
import { StatusDot } from '../../components/ui/Agenda';
import { strings } from '../../copy/strings';
import { LIVE_STATUSES, preferredLiveEvent, statusLabel } from '../../lib/status';
import { Button } from '../../components/ui/Button';
import { friendlyError } from '../../lib/errors';

function LiveEvent({ event }: { event: Event }) {
  const sessionRef = useRef(emptyLiveSession(event.id));
  const [session, setSession] = useState(() => emptyLiveSession(event.id));
  const realtime = useOccupancy(LIVE_STATUSES.includes(event.status) ? event.id : null, {
    refetch: async (signal) => ({ data: await eventService.occupancy(event.id, signal) }),
    onSnapshot: (snapshot, at) => {
      const before = sessionRef.current;
      const after = acceptOccupancy(before, snapshot, at);
      sessionRef.current = after;
      setSession(after);
    },
  });
  const snapshot = realtime.data;
  const status = snapshot?.status ?? event.status;
  const live = LIVE_STATUSES.includes(status);
  const count = snapshot?.registered_count ?? event.registeredCount;
  const capacity = snapshot?.capacity ?? event.capacity;
  const remaining = Math.max(0, capacity - count);
  const percent = capacity > 0 ? Math.min(100, Math.round(count / capacity * 100)) : 0;
  return <>
    <section className="live-board" aria-label={event.title}>
      <div className="live-board-header"><h2>{event.title}</h2>
        {live ? <div className="live-board-connection"><ConnectionIndicator state={realtime.state} />
          {realtime.state === 'closed' && !realtime.error && <Button variant="secondary" onClick={realtime.retry}>{strings.common.retry}</Button>}</div> : <StatusDot status={status} />}
      </div>
      {!live && <p className="live-final">{status === 'DRAFT' ? strings.live.draft : strings.live.final(statusLabel(status))}</p>}
      <DoorCounter count={count} capacity={capacity} />
      <div className="live-board-fill"><b>{strings.live.left(remaining)}</b><div className="live-fill-track" role="meter" aria-label={strings.live.registered} aria-valuemin={0} aria-valuemax={capacity} aria-valuenow={Math.min(count, capacity)}>
        <i style={{width:`${percent}%`}} /></div><span>{percent}%</span>
      </div>
      <p className="live-updated">{realtime.updatedAt ? <>{strings.live.updated} <RelativeTime value={realtime.updatedAt} every={1000} /></> : live ? strings.live.snapshotWaiting : null}</p>
      {!!realtime.error && <ErrorBlock message={friendlyError(realtime.error)} onRetry={realtime.retry} />}
    </section>
    <section className="live-changes"><h2>{strings.live.changes}</h2>
      {session.changes.length ? <ol>{session.changes.map((change) => <li key={change.id}><b className={change.delta > 0 ? 'positive' : 'negative'}>{strings.live.delta(change.delta)}</b><RelativeTime value={change.at} every={1000} /></li>)}</ol>
        : <p className="empty-note">{strings.live.changesEmpty}</p>}
    </section>
  </>;
}

export function Live() {
  const query = useQuery(organizerService.dashboard, [], { refetchInterval: 10_000 });
  const [selected, setSelected] = useState('');
  const events = query.data?.events ?? [];
  const active = events.find((event) => event.id === selected) ?? preferredLiveEvent(events);
  const groups = [
    { label: strings.live.groups.live, events: events.filter((event) => event.status === 'STARTED' || event.status === 'ONGOING') },
    { label: strings.live.groups.upcoming, events: events.filter((event) => event.status === 'PUBLISHED' || event.status === 'DRAFT') },
    { label: strings.live.groups.past, events: events.filter((event) => event.status === 'COMPLETED' || event.status === 'CANCELLED') },
  ];
  return <div className="live-page">
    <PageHeader title={strings.live.title} />
    {query.error && <ErrorBlock message={friendlyError(query.error)} onRetry={() => void query.refetch()} />}
    {query.isLoading ? <Skeleton kind="card" /> : active ? <>
      <div className="live-picker"><Field label={strings.live.event}><Select value={active.id} onChange={(e) => setSelected(e.target.value)}>
        {groups.filter((group) => group.events.length).map((group) => <optgroup key={group.label} label={group.label}>{group.events.map((event) => <option key={event.id} value={event.id}>{event.title} — {statusLabel(event.status)}</option>)}</optgroup>)}
      </Select></Field><Link className="btn btn-secondary" to={`/organizer/events/${active.id}`}>{strings.live.manage}</Link></div>
      <LiveEvent key={active.id} event={active} />
    </> : !query.error && <EmptyState title={strings.live.noEvents} body={strings.live.noEventsBody} />}
  </div>;
}
