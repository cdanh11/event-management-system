import { useCallback, useEffect, useRef, useState } from 'react';
import { Check, AlertTriangle, X } from 'lucide-react';
import { checkinHistoryService, checkinService } from '../../services/services';
import type { Event, User } from '../../types';
import { canCheckin } from '../../lib/status';
import { DoorStatus } from '../../components/ui/DoorStatus';
import { formatTime } from '../../lib/datetime';
import { friendlyError } from '../../lib/errors';
import { useQuery } from '../../hooks/useQuery';
import { Button } from '../../components/ui/Button';
import { Field, Input } from '../../components/ui/forms';
import { EmptyState, ErrorBlock, Skeleton } from '../../components/ui/states';
import { RelativeTime } from '../../components/ui/RelativeTime';
import { strings } from '../../copy/strings';
import { normalizeTicketCode, scanFailure, type ScanReceipt } from './scan';

let receiptId = 1;
export function DoorDesk({ event, user, recheck, eventName, onBusyChange, onAdmitted }: {
  event: Event; user: User; recheck: () => Promise<Event | undefined>; eventName?: (id: string) => string | undefined;
  onBusyChange?: (busy: boolean) => void;
  onAdmitted?: (eventId: string, code: string) => void;
}) {
  const [entry, setEntry] = useState({ eventId: event.id, value: '' });
  const code = entry.eventId === event.id ? entry.value : '';
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    onBusyChange?.(busy);
    return () => onBusyChange?.(false);
  }, [busy, onBusyChange]);
  const [receipts, setReceipts] = useState<ScanReceipt[]>([]);
  const locked = useRef(false);
  const input = useRef<HTMLInputElement | null>(null);
  const open = canCheckin(user.role, event.status);
  const session = receipts.filter((receipt) => receipt.eventId === event.id);
  // Keep the most recent outcome, including an admission into another assigned event.
  const result = session[0];
  const [dismissed, setDismissed] = useState<number | null>(null);
  useEffect(() => {
    if (!result) return;
    const timer = setTimeout(() => setDismissed(result.id), 5000);
    return () => clearTimeout(timer);
  }, [result]);
  useEffect(() => {
    if (open) input.current?.focus();
  }, [event.id, open]);
  const check = async () => {
    const value = normalizeTicketCode(code);
    if (!value || !open || locked.current) return;
    locked.current = true; setBusy(true);
    let receipt: ScanReceipt;
    try {
      const fresh = await recheck();
      if (!fresh) throw { code: 'FORBIDDEN' };
      if (!canCheckin(user.role, fresh.status)) throw { code: 'CHECKIN_CLOSED' };
      const admission = await checkinService.checkin(value, user, event.id);
      const otherEvent = admission.eventId !== event.id;
      onAdmitted?.(admission.eventId, value);
      // A missing history response must never turn a successful admission into an error.
      const recorded = await checkinHistoryService.list(admission.eventId, 100).catch(() => []);
      const attendee = recorded.find(row => row.ticketCode === value)?.attendeeName;
      receipt = { id: receiptId++, eventId: event.id, code: value, at: admission.checkedInAt,
        tone: 'success', title: otherEvent ? strings.staff.admittedOther(eventName?.(admission.eventId) ?? strings.staff.anotherEvent) : `${strings.staff.admitted}: ${attendee ?? value}`,
        detail: otherEvent ? strings.staff.wrongSelection : undefined };
    } catch (error) {
      receipt = { id: receiptId++, eventId: event.id, code: value, at: new Date().toISOString(), ...scanFailure(error) };
    }
    setReceipts((previous) => [receipt, ...previous].slice(0,20));
    setEntry({ eventId: event.id, value: '' }); locked.current = false; setBusy(false);
    requestAnimationFrame(() => input.current?.focus());
  };
  const Icon = result?.tone === 'success' ? Check : result?.tone === 'warning' ? AlertTriangle : X;
  return <section className="door-workspace">
    {!open && <div className="door-closed" role="status"><DoorStatus event={event} /></div>}
    <div className="door-result-region" aria-live="polite" aria-atomic="true">
      {result && dismissed !== result.id && <article key={result.id} className={`door-receipt door-receipt-${result.tone}`}>
        <Icon size={30} aria-hidden /><div><h2>{result.title}</h2><code>{result.code}</code>{result.detail && <p>{result.detail}</p>}</div>
        <time dateTime={result.at}>{formatTime(result.at)}</time>
      </article>}
    </div>
    <form className="door-scan-form" onSubmit={(e) => { e.preventDefault(); void check(); }}>
      <Field label={strings.staff.codeLabel} hint={strings.staff.scanHint}>
        <Input ref={input} value={code} onChange={(e) => setEntry({ eventId: event.id, value: normalizeTicketCode(e.target.value) })} autoComplete="off" spellCheck={false}
          disabled={!open || busy} placeholder={strings.staff.codePlaceholder} />
      </Field>
      <Button type="submit" size="lg" loading={busy} disabled={!open || !code}>{strings.staff.scan}</Button>
    </form>
    <p className="door-last-scan">{strings.staff.lastScan}{result && <>: <strong>{result.title}</strong> · <code>{result.code}</code> · <time dateTime={result.at}>{formatTime(result.at)}</time></>}</p>
  </section>;
}

export function DoorHistory({ event, onCount, sessionCodes }: { event: Event; onCount?: (eventId: string, count: number) => void; sessionCodes?: Set<string> }) {
  const history = useQuery((signal) => checkinHistoryService.list(event.id, 100, signal), [event.id], { refetchInterval: 5000 });
  useEffect(() => { if (history.data) onCount?.(event.id, history.data.length); },[event.id,history.data,onCount]);
  return <section className="door-history"><h2>{strings.staff.serverHistory}</h2><p className="hint">{strings.staff.serverHistoryHint}</p>
    {history.error && <ErrorBlock message={friendlyError(history.error)} onRetry={() => void history.refetch()} />}
    {history.isLoading ? <Skeleton kind="row" /> : history.data?.length ? <ol>{history.data.map((row) => <li key={row.id}>
      <div><b>{row.attendeeName}</b>{sessionCodes?.has(`${event.id}:${row.ticketCode}`) && <small className="checkin-you">{strings.staff.you}</small>}<code>{row.ticketCode}</code></div><time dateTime={row.checkedInAt}>{formatTime(row.checkedInAt)}<small><RelativeTime value={row.checkedInAt} /></small></time>
    </li>)}</ol> : !history.error && <EmptyState title={strings.staff.historyEmpty} />}
  </section>;
}

/** One scanner and one server history for both organizer and staff. */
export function DoorWorkspace(props: Parameters<typeof DoorDesk>[0] & { onCount?: (eventId: string, count: number) => void }) {
  const [sessionCodes, setSessionCodes] = useState<Set<string>>(() => new Set());
  const admitted = useCallback((eventId: string, code: string) => setSessionCodes(before => new Set([...before, `${eventId}:${code}`])), []);
  return <><DoorDesk {...props} onAdmitted={admitted} /><DoorHistory event={props.event} onCount={props.onCount} sessionCodes={sessionCodes} /></>;
}
