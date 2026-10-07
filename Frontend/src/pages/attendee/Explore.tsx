import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search } from 'lucide-react';
import { useAuth } from '../../features/auth/useAuth';
import { useQuery } from '../../hooks/useQuery';
import { useGlobalSearch } from '../../components/layout/AppShell';
import { registrationService, ticketService } from '../../services/services';
import { registrationEvents } from '../../features/events/eventCache';
import { loadAgenda, visibleAgenda, type AgendaTab } from '../../features/events/agenda';
import { AgendaRow, PosterBand } from '../../components/ui/Agenda';
import { Button } from '../../components/ui/Button';
import { EmptyState, ErrorBlock, Skeleton } from '../../components/ui/states';
import { PageHeader } from '../../components/ui/PageHeader';
import { Tabs } from '../../components/ui/Tabs';
import { useToast } from '../../components/ui/Toast';
import { useNow } from '../../realtime/useNow';
import { friendlyError } from '../../lib/errors';
import { strings } from '../../copy/strings';
import type { Registration } from '../../types';

function AgendaList({ tab, q, registered, clearSearch, onTicket, busyRegistration }: {
  tab: AgendaTab; q: string; registered: Map<string, Registration>; clearSearch: () => void;
  onTicket: (registration: Registration) => void; busyRegistration: string | null;
}) {
  const pages = useRef(1);
  const now = useNow(30_000);
  const query = useQuery((signal) => loadAgenda(tab, q, pages.current, signal), [tab, q], { refetchInterval: 20_000 });
  const items = visibleAgenda(query.data?.items ?? [], tab, now);
  const loadMore = async () => {
    pages.current += 1;
    if (!await query.refetch()) pages.current -= 1;
  };
  return <section className="agenda-list" aria-busy={query.isLoading || query.isRefreshing}>
    {query.error && <ErrorBlock message={friendlyError(query.error)} onRetry={() => void query.refetch()} />}
    {query.isLoading ? <><Skeleton kind="row" /><Skeleton kind="row" /><Skeleton kind="row" /></>
      : items.length ? items.map((event) => <AgendaRow key={event.id} event={event} now={now} registration={registered.get(event.id)} onTicket={onTicket} ticketBusy={busyRegistration === registered.get(event.id)?.id} />)
        : !query.error && <EmptyState title={strings.explore.empty} body={strings.explore.emptyBody}
          action={<Button variant="secondary" onClick={clearSearch}>{strings.explore.clearSearch}</Button>} />}
    {query.data?.hasMore && <div className="agenda-more"><Button variant="secondary" loading={query.isRefreshing} onClick={() => void loadMore()}>{strings.explore.loadMore}</Button></div>}
  </section>;
}

export function Explore() {
  const { user } = useAuth();
  const { q, setQ } = useGlobalSearch();
  const navigate = useNavigate();
  const { toast } = useToast();
  const now = useNow(30_000);
  const [debouncedQ, setDebouncedQ] = useState(q);
  const [tab, setTab] = useState<AgendaTab>('open');
  const [busy, setBusy] = useState<string | null>(null);
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQ(q), 300);
    return () => clearTimeout(timer);
  }, [q]);
  const mine = useQuery(async (signal) => {
    const regs = await registrationService.mine(user!.id, signal);
    return { regs, events: await registrationEvents(regs, signal) };
  }, [user?.id], { enabled: !!user, refetchInterval: 20_000 });
  const registered = useMemo(() => new Map(mine.data?.regs.map((reg) => [reg.eventId, reg])), [mine.data]);
  const next = mine.data?.regs.filter((reg) => reg.status === 'REGISTERED')
    .map((reg) => ({ reg, event: mine.data!.events.get(reg.eventId)! }))
    .filter(({ event }) => event && ['PUBLISHED', 'ONGOING', 'STARTED'].includes(event.status) && +new Date(event.endTime) > now)
    .sort((a, b) => Number(b.event.status === 'STARTED') - Number(a.event.status === 'STARTED') || +new Date(a.event.startTime) - +new Date(b.event.startTime))[0];
  const openTicket = async (registration: Registration) => {
    if (busy) return;
    setBusy(registration.id);
    try { navigate(`/tickets/${(await ticketService.forRegistration(registration.id)).id}`); }
    catch (error) { toast(friendlyError(error), 'error'); }
    finally { setBusy(null); }
  };
  return <div className="explore-page">
    <PageHeader title={strings.explore.title} />
    {next && <PosterBand event={next.event} onTicket={() => void openTicket(next.reg)} busy={busy !== null} />}
    {mine.error && <ErrorBlock message={friendlyError(mine.error)} onRetry={() => void mine.refetch()} />}
    <div className="agenda-toolbar">
      <label className="agenda-search"><Search size={18} aria-hidden /><input aria-label={strings.explore.search} placeholder={strings.explore.search} value={q} onChange={(e) => setQ(e.target.value)} /></label>
      <Tabs tabs={[{ key: 'open', label: strings.explore.open }, { key: 'happening', label: strings.explore.happening }, { key: 'past', label: strings.explore.past }]} active={tab} onChange={setTab} />
      <select className="input agenda-sort" aria-label={strings.explore.sort} defaultValue="soonest"><option value="soonest">{strings.explore.sortSoonest}</option></select>
    </div>
    <AgendaList key={`${tab}:${debouncedQ.trim()}`} tab={tab} q={debouncedQ} registered={registered} onTicket={registration => void openTicket(registration)} busyRegistration={busy} clearSearch={() => { setQ(''); setTab('open'); }} />
  </div>;
}
