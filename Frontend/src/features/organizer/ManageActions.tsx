import { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { eventService } from '../../services/services';
import type { Event, EventStatus } from '../../types';
import { Button } from '../../components/ui/Button';
import { ConfirmDialog } from '../../components/ui/Modal';
import { useToast } from '../../components/ui/Toast';
import { strings } from '../../copy/strings';
import { nextActions } from '../../lib/status';
import { friendlyError } from '../../lib/errors';

type Action = EventStatus | 'delete' | 'notify';
export function ManageActions({ event, onChanged, primary = true }: { event: Event; onChanged: (event: Event) => void; primary?: boolean }) {
  const [confirm, setConfirm] = useState<Action | null>(null);
  const [busy, setBusy] = useState(false);
  const working = useRef(false);
  const [error, setError] = useState('');
  const { toast } = useToast();
  const navigate = useNavigate();
  const copy = strings.manage;
  const actions = nextActions(event.status);
  const meta: Partial<Record<Action, { label: string; body: string; success?: string }>> = {
    PUBLISHED: { label:copy.publish, body:copy.publishBody, success:copy.publishedToast },
    ONGOING: { label:copy.prepare, body:copy.prepareBody + ' ' + copy.affectedCount(event.registeredCount), success:copy.preparedToast },
    STARTED: { label:copy.startEvent, body:copy.startBody + ' ' + copy.affectedCount(event.registeredCount), success:copy.startedToast },
    COMPLETED: { label:copy.completeEvent, body:copy.completeBody + ' ' + copy.affectedCount(event.registeredCount), success:copy.completedToast },
    CANCELLED: { label:copy.cancelEvent, body:copy.cancelBody(event.registeredCount), success:copy.cancelledToast },
    delete: { label:copy.deleteDraft, body:copy.deleteBody, success:copy.deletedToast },
    notify: { label:copy.notify, body:copy.notifyBody(event.registeredCount,event.title) },
  };
  const open = (action: Action) => { setError(''); setConfirm(action); };
  const perform = async () => {
    if (!confirm || working.current) return;
    const action = confirm;
    // Polling may have changed the event while a dialog was open.
    if (action !== 'notify' && !(action === 'delete' ? event.status === 'DRAFT' : actions.includes(action))) {
      setError(friendlyError({code:'INVALID_TRANSITION'})); return;
    }
    working.current = true; setBusy(true); setError('');
    try {
      if (action === 'delete') {
        await eventService.remove(event.id);
        toast(copy.deletedToast,'success');
        navigate('/organizer/events');
      } else if (action === 'notify') {
        const response = await eventService.notify(event.id);
        toast(response.mode === 'simulated' ? copy.simulatedNotify(response.emails_sent) : copy.notified(response.emails_sent),'success');
      } else {
        const next = await eventService.transition(event.id, action);
        onChanged(next); toast(meta[action]!.success!,'success');
      }
      setConfirm(null);
    } catch (err) { setError(friendlyError(err)); }
    finally { working.current = false; setBusy(false); }
  };
  const pending = confirm && meta[confirm];
  return <>
    <div className="manage-primary-actions">
      {actions.filter(action => action !== 'CANCELLED').map((action,index) => <Button key={action} variant={primary && index === 0 ? 'primary' : 'secondary'} disabled={busy} onClick={() => open(action)}>{meta[action]?.label}</Button>)}
      <Button variant="secondary" disabled={busy} onClick={() => open('notify')}>{copy.notify}</Button>
      {actions.includes('CANCELLED') && <Button variant="link" className="quiet-danger" disabled={busy} onClick={() => open('CANCELLED')}>{copy.cancelEvent}</Button>}
    </div>
    {!actions.length && <p className="hint">{copy.noActions}</p>}
    {event.status === 'DRAFT' && <div className="manage-danger-actions">
      {event.status === 'DRAFT' && <Button variant="danger" disabled={busy} onClick={() => open('delete')}>{copy.deleteDraft}</Button>}
    </div>}
    <ConfirmDialog open={!!pending} title={pending?.label ?? ''} message={pending?.body ?? ''} error={error} confirmLabel={pending?.label}
      busy={busy} tone={confirm === 'delete' || confirm === 'CANCELLED' || confirm === 'COMPLETED' ? 'danger' : 'default'}
      onCancel={() => setConfirm(null)} onConfirm={() => void perform()} />
  </>;
}
