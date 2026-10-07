import { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../features/auth/useAuth';
import { useQuery } from '../../hooks/useQuery';
import { registrationService, ticketService } from '../../services/services';
import type { Registration } from '../../types';
import { Button } from '../../components/ui/Button';
import { ConfirmDialog } from '../../components/ui/Modal';
import { Countdown } from '../../components/ui/Countdown';
import { EmptyState, ErrorBlock, Skeleton } from '../../components/ui/states';
import { DateBlock, StatusDot } from '../../components/ui/Agenda';
import { PageHeader } from '../../components/ui/PageHeader';
import { Tabs } from '../../components/ui/Tabs';
import { useToast } from '../../components/ui/Toast';
import { strings } from '../../copy/strings';
import { registrationEvents } from '../../features/events/eventCache';
import { friendlyError } from '../../lib/errors';
import { statusColor } from '../../lib/status';
import { formatWhen } from '../../lib/datetime';

type Tab = 'upcoming' | 'past' | 'cancelled';

export function MyRegistrations() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [tab, setTab] = useState<Tab>('upcoming');
  const [cancelTarget, setCancelTarget] = useState<{ id: string; title: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [cancelError, setCancelError] = useState('');

  const { data, isLoading: loading, error, refetch: reload, setData } = useQuery(
    async (signal) => {
      const regs = await registrationService.mine(user!.id, signal);
      const [byEvent, tickets] = await Promise.all([
        registrationEvents(regs, signal),
        Promise.all(regs.map(async (reg) => [reg.id, await ticketService.forRegistration(reg.id, signal)] as const)),
      ]);
      return { regs, byEvent, tickets: new Map(tickets) };
    },
    [user?.id], { enabled: !!user, refetchInterval: 15_000 }
  );
  const regs = data?.regs;
  const byEvent = useMemo(() => data?.byEvent ?? new Map(), [data]);

  const groups = useMemo(() => {
    const all = regs ?? [];
    const upcoming = all.filter((r) => {
      const e = byEvent.get(r.eventId);
      return r.status === 'REGISTERED' && (!e || (e.status !== 'COMPLETED' && e.status !== 'CANCELLED'));
    });
    const past = all.filter((r) => {
      const e = byEvent.get(r.eventId);
      return r.status === 'REGISTERED' && e?.status === 'COMPLETED';
    });
    const cancelled = all.filter((r) => r.status === 'CANCELLED' || byEvent.get(r.eventId)?.status === 'CANCELLED');
    return { upcoming, past, cancelled } as Record<Tab, Registration[]>;
  }, [regs, byEvent]);

  if (loading) {
    return (
      <div>
        <Skeleton kind="row" />
        <Skeleton kind="row" />
      </div>
    );
  }

  const list = groups[tab];

  const openTicket = async (regId: string) => {
    try {
      const ticket = data?.tickets.get(regId) ?? await ticketService.forRegistration(regId);
      navigate(`/tickets/${ticket.id}`);
    } catch (e) {
      toast(friendlyError(e), 'error');
    }
  };

  const doCancel = async () => {
    if (!cancelTarget || busy) return;
    const registration = data?.regs.find(reg => reg.id === cancelTarget.id);
    if (!registration || byEvent.get(registration.eventId)?.status !== 'PUBLISHED') {
      setCancelError(strings.registrations.cancellationLocked); return;
    }
    setBusy(true); setCancelError('');
    try {
      const cancelled = await registrationService.cancel(cancelTarget.id);
      if (data) {
        const tickets = new Map(data.tickets);
        const ticket = tickets.get(cancelled.id);
        if (ticket) tickets.set(cancelled.id, { ...ticket, status: 'CANCELLED' });
        setData({ ...data, regs: data.regs.map(reg => reg.id === cancelled.id ? cancelled : reg), tickets });
      }
      toast(strings.registrations.cancelToast, 'success');
      setTab('cancelled');
      setCancelTarget(null);
      void reload();
    } catch (e) {
      setCancelError(friendlyError(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <PageHeader title={strings.registrations.title} />
      {error && <ErrorBlock message={friendlyError(error)} onRetry={() => void reload()} />}
      <Tabs<Tab>
        tabs={[
          { key: 'upcoming', label: strings.registrations.tabs.upcoming },
          { key: 'past', label: strings.registrations.tabs.past },
          { key: 'cancelled', label: strings.registrations.tabs.cancelled },
        ]}
        active={tab}
        onChange={setTab}
        counts={{ upcoming: groups.upcoming.length, past: groups.past.length, cancelled: groups.cancelled.length }}
      />
      {list.length ? (
        <div className="list" style={{ marginTop: 16 }}>
          {list.map((r) => {
            const e = byEvent.get(r.eventId);
            const canCancel =
              tab === 'upcoming' && r.status === 'REGISTERED' && e?.status === 'PUBLISHED';
            return (
              <article className={`ticket-stub${tab === 'cancelled' ? ' is-cancelled' : ''}`} key={r.id}
                style={{borderLeftColor: tab === 'cancelled' ? statusColor('CANCELLED') : data?.tickets.get(r.id)?.status === 'USED' ? statusColor('STARTED') : e ? statusColor(e.status) : undefined}}>
                {e && <DateBlock value={e.startTime} />}
                <div className="ticket-stub-description">
                  <h2>{e && <Link className="agenda-event-link" to={`/events/${e.id}`}>{e.title}</Link>}</h2>
                  <p>{e?.location}</p>
                  {e && <small>{formatWhen(e.startTime,e.endTime)}</small>}
                  {e?.status === 'CANCELLED' ? <small>{strings.registrations.cancelledEvent}</small>
                    : r.status === 'CANCELLED' ? <small>{strings.registrations.cancelledTicket}</small>
                      : data?.tickets.get(r.id)?.status === 'USED' ? <span className="checked-in">{strings.explore.checkedIn}</span>
                        : e?.status === 'STARTED' ? <span className="checked-in">{strings.explore.doorOpen}</span>
                          : e && tab === 'upcoming' ? <Countdown compact startTime={e.startTime} endTime={e.endTime} />
                            : e && <StatusDot status={e.status} />}
                </div>
                <div className="reg-actions">
                  {data?.tickets.has(r.id) && (
                    <Button variant="link" size="sm" onClick={() => void openTicket(r.id)}>
                      {strings.common.viewTicket}
                    </Button>
                  )}
                  {canCancel ? (
                    <Button
                      variant="link"
                      className="quiet-danger"
                      size="sm"
                      onClick={() => { setCancelError(''); setCancelTarget({ id: r.id, title: e?.title ?? strings.common.thisEvent }); }}
                    >
                      {strings.registrations.cancelTitle}
                    </Button>
                  ) : (
                    tab === 'upcoming' &&
                    r.status === 'REGISTERED' && (
                      <small className="hint">
                        {strings.registrations.cancellationLocked}
                      </small>
                    )
                  )}
                </div>
              </article>
            );
          })}
        </div>
      ) : (
        !error && <EmptyState title={strings.registrations.empty} body={strings.registrations.emptyBody} />
      )}

      <ConfirmDialog
        open={!!cancelTarget}
        title={strings.registrations.cancelTitle}
        message={strings.registrations.cancellationWarning(cancelTarget?.title ?? '')}
        confirmLabel={strings.registrations.cancelTitle}
        tone="danger"
        busy={busy}
        error={cancelError}
        onConfirm={() => void doCancel()}
        onCancel={() => setCancelTarget(null)}
      />
    </div>
  );
}
