import { Link, useParams } from 'react-router-dom';
import { useAuth } from '../../features/auth/useAuth';
import { useQuery } from '../../hooks/useQuery';
import { TicketPass } from '../../features/tickets/TicketPass';
import { registrationService, ticketService } from '../../services/services';
import { getCachedEvent } from '../../features/events/eventCache';
import { ErrorBlock, Skeleton } from '../../components/ui/states';
import { friendlyError } from '../../lib/errors';
import { strings } from '../../copy/strings';

export function TicketPage() {
  const { id = '' } = useParams();
  const { user } = useAuth();
  const query = useQuery(async signal => {
    const ticket = await ticketService.get(id, signal);
    const registration = await registrationService.get(ticket.registrationId, signal);
    return { ticket, event: await getCachedEvent(registration.eventId, signal) };
  }, [id], { refetchInterval: 15_000 });
  if (query.isLoading) return <Skeleton kind="card" />;
  if (!query.data) return <ErrorBlock message={friendlyError(query.error)} onRetry={() => void query.refetch()} />;
  return <section className="ticket-page">
    <Link className="back-link" to="/registrations">{strings.ticket.back}</Link>
    {query.error && <ErrorBlock message={friendlyError(query.error)} onRetry={() => void query.refetch()} />}
    <TicketPass ticket={query.data.ticket} event={query.data.event} name={user?.name ?? ''} />
  </section>;
}
