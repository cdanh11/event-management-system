import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '../../hooks/useQuery';
import { organizerService } from '../../services/services';
import { PageHeader } from '../../components/ui/PageHeader';
import { Button } from '../../components/ui/Button';
import { Input, Select } from '../../components/ui/forms';
import { OrganizerAgenda } from '../../components/ui/OrganizerAgenda';
import { EmptyState, ErrorBlock, Skeleton } from '../../components/ui/states';
import { EVENT_STATUSES, statusLabel } from '../../lib/status';
import { friendlyError } from '../../lib/errors';
import { strings } from '../../copy/strings';

export function Events() {
  const [params, setParams] = useSearchParams();
  const [page, setPage] = useState(0);
  const status = params.get('status') ?? 'ALL';
  const q = params.get('q') ?? '';
  const sort = params.get('sort') === 'popular' ? 'popular' : 'soonest';
  const query = useQuery(signal => organizerService.page({ status, q, sort, limit: 20, offset: page * 20, signal }), [status, q, sort, page], { refetchInterval: 10_000 });
  const copy = strings.organizer;
  const set = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (!value || value === 'ALL' || (key === 'sort' && value === 'soonest')) next.delete(key);
    else next.set(key, value);
    setParams(next, { replace: true });
    setPage(0);
  };
  const rows = query.data?.items ?? [];

  return <div>
    <PageHeader title={copy.eventsTitle} />
    <section className="organizer-filters">
      <Input aria-label={strings.common.search} value={q} placeholder={copy.search} onChange={event => set('q', event.target.value)} />
      <Select aria-label={copy.filter} value={status} onChange={event => set('status', event.target.value)}>
        <option value="ALL">{copy.statusAll}</option>{EVENT_STATUSES.map(value => <option key={value} value={value}>{copy.statusOption(statusLabel(value))}</option>)}
      </Select>
      <Select aria-label={copy.sort} value={sort} onChange={event => set('sort', event.target.value)}>
        <option value="soonest">{copy.sortOption(copy.soonest)}</option><option value="popular">{copy.sortOption(copy.mostRegistered)}</option>
      </Select>
    </section>
    {query.error && <ErrorBlock message={friendlyError(query.error)} onRetry={() => void query.refetch()} />}
    {query.isLoading ? <><Skeleton kind="row" /><Skeleton kind="row" /><Skeleton kind="row" /></> : query.data && <section>
      <div className="section-title"><h2>{copy.eventCount(query.data.total)}</h2></div>
      {rows.length ? rows.map(event => <OrganizerAgenda key={event.id} event={event} />) : <EmptyState title={strings.common.noResults} action={<Button variant="secondary" onClick={() => {setParams({}, { replace: true });setPage(0);}}>{strings.common.clearFilters}</Button>} />}
      {(page > 0 || query.data.has_more) && <div className="agenda-more">
        <Button variant="secondary" disabled={page === 0 || query.isRefreshing} onClick={() => setPage(before => before - 1)}>{copy.previousPage}</Button>
        <span>{copy.pageNumber(page + 1)}</span>
        <Button variant="secondary" disabled={!query.data.has_more || query.isRefreshing} onClick={() => setPage(before => before + 1)}>{copy.nextPage}</Button>
      </div>}
    </section>}
  </div>;
}
