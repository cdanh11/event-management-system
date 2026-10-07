import { useCallback, useState } from 'react';
import { useAuth } from '../../features/auth/useAuth';
import { useQuery } from '../../hooks/useQuery';
import { staffService } from '../../services/services';
import { DoorWorkspace } from '../../features/door/DoorDesk';
import { preferredLiveEvent, statusLabel } from '../../lib/status';
import { friendlyError } from '../../lib/errors';
import { formatRange } from '../../lib/datetime';
import { PageHeader } from '../../components/ui/PageHeader';
import { Field, Select } from '../../components/ui/forms';
import { StatusDot } from '../../components/ui/Agenda';
import { EmptyState, ErrorBlock, Skeleton } from '../../components/ui/states';
import { strings } from '../../copy/strings';

export function CheckinDesk() {
  const { user } = useAuth();
  const [selected, setSelected] = useState('');
  const [scanning, setScanning] = useState(false);
  const [checked, setChecked] = useState<{ eventId: string; count: number } | null>(null);
  const recordCount = useCallback((eventId: string, count: number) => setChecked({eventId,count}),[]);
  const events = useQuery(staffService.myEvents, [], { refetchInterval: 15_000 });
  const active = events.data?.find((event) => event.id === selected) ?? preferredLiveEvent(events.data ?? []);
  return <div className="door-page">
    <PageHeader title={strings.staff.title} />
    {events.error && <ErrorBlock message={friendlyError(events.error)} onRetry={() => void events.refetch()} />}
    {events.isLoading ? <><Skeleton kind="row" /><Skeleton kind="row" /></>
      : active && user ? <>
        <div className="door-picker">
          <Field label={strings.staff.picker}><Select value={active.id} disabled={scanning} onChange={(e) => setSelected(e.target.value)}>
            {events.data?.map((event) => <option key={event.id} value={event.id}>{event.title} — {statusLabel(event.status)}</option>)}
          </Select></Field><StatusDot status={active.status} />
        </div>
        <p className="door-event-place">{formatRange(active.startTime, active.endTime)}<br />{active.location}</p>
        <div className="door-context"><span>{strings.staff.checkedInCount} <b>{checked?.eventId === active.id ? checked.count === 100 ? '≥100' : checked.count : '—'}</b></span><span>{strings.staff.registered} <b>{active.registeredCount}</b> {strings.staff.of} {active.capacity}</span></div>
        <DoorWorkspace event={active} user={user} onCount={recordCount} onBusyChange={setScanning} eventName={(id) => events.data?.find((event) => event.id === id)?.title}
          recheck={async () => {
            const assigned = await staffService.myEvents();
            events.setData(assigned);
            return assigned.find((event) => event.id === active.id);
          }} />
      </> : !events.error && <EmptyState title={strings.staff.noEvents} body={strings.staff.noEventsBody} />}
  </div>;
}
