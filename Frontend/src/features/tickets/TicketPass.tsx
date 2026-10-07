import { useState } from 'react';
import { QRCodeView } from '../../components/ui/QRCodeView';
import { Button } from '../../components/ui/Button';
import { useToast } from '../../components/ui/Toast';
import { formatWhen } from '../../lib/datetime';
import type { Event, Ticket } from '../../types';
import { strings } from '../../copy/strings';

/** The pass is shared by the ticket route and future previews. */
export function TicketPass({ ticket, event, name }: { ticket: Ticket; event: Event; name: string }) {
  const { toast } = useToast();
  const [copied, setCopied] = useState(false);
  const cancelled = ticket.status === 'CANCELLED' || event.status === 'CANCELLED';
  const state = cancelled ? strings.ticket.cancelled : ticket.status === 'USED' ? strings.ticket.used : strings.ticket.valid;
  const copy = async () => {
    try { await navigator.clipboard.writeText(ticket.ticketCode); setCopied(true); toast(strings.common.copiedCode); }
    catch { toast(strings.ticket.manualCopy, 'info'); }
  };
  return <>
    <article className={`ticket-pass ${state === strings.ticket.valid ? '' : 'ticket-inactive'}`} aria-label={strings.ticket.label(state, event.title)}>
      <div className="ticket-pass-info">
        <span className="ticket-wordmark">{strings.auth.logo}</span>
        <h1>{event.title}</h1>
        <p>{formatWhen(event.startTime,event.endTime)}</p>
        <p>{event.location}</p>
        <div className="ticket-holder"><span>{name}</span><b>{state}</b></div>
      </div>
      <div className="ticket-pass-code">
        <QRCodeView value={ticket.qrValue} size={176} />
        <code>{ticket.ticketCode}</code>
        <Button variant="secondary" onClick={() => void copy()}>{copied ? strings.common.copied : strings.ticket.copyCode}</Button>
      </div>
    </article>
    <p className="ticket-instruction">{state === strings.ticket.valid ? strings.ticket.instruction : state === strings.ticket.used ? strings.ticket.usedInstruction : strings.ticket.cancelledInstruction}</p>
  </>;
}
