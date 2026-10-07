import { useState, type FormEvent } from 'react';
import type { Event } from '../../types';
import { eventService } from '../../services/services';
import { Button } from '../../components/ui/Button';
import { Field, Input } from '../../components/ui/forms';
import { useToast } from '../../components/ui/Toast';
import { strings } from '../../copy/strings';
import { canReschedule } from '../../lib/status';
import { fromInputValue, toInputValue } from '../../lib/datetime';
import { friendlyError } from '../../lib/errors';
import { scheduleErrors, durationLabel, eventServerErrors, type ScheduleValues } from './eventForm';
import { useNow } from '../../realtime/useNow';

export function ScheduleForm({ event, onChanged }: { event: Event; onChanged: (event: Event) => void }) {
  const [draft, setDraft] = useState<ScheduleValues | null>(null);
  const [touched, setTouched] = useState<Record<string, boolean>>({});
  const [serverErrors, setServerErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const now = useNow(30_000);
  const { toast } = useToast();
  const value = draft ?? {startTime:toInputValue(event.startTime),endTime:toInputValue(event.endTime)};
  const errors = scheduleErrors(value,now);
  const copy = strings.organizer.form;
  const editable = canReschedule(event.status);
  const change = (key: keyof ScheduleValues, next: string) => { setDraft({...value,[key]:next}); setServerErrors(before => ({...before,[key]:''})); setError(''); };
  const show = (key: keyof ScheduleValues) => serverErrors[key] || (touched[key] ? errors[key] : '');
  const save = async (e: FormEvent) => {
    e.preventDefault(); if (!editable || busy) return;
    setTouched({startTime:true,endTime:true}); setError(''); setServerErrors({});
    if (Object.values(scheduleErrors(value,Date.now())).some(Boolean)) return;
    setBusy(true);
    try {
      const updated = await eventService.reschedule(event.id,{startTime:fromInputValue(value.startTime),endTime:fromInputValue(value.endTime)});
      onChanged(updated); setDraft(null); setTouched({}); toast(strings.manage.savedSchedule,'success');
    } catch (err) { setError(friendlyError(err)); setServerErrors(eventServerErrors(err)); }
    finally { setBusy(false); }
  };
  const duration = durationLabel(value);
  if (!editable) return <p className="notice">{strings.manage.lockedSchedule}</p>;
  return <form className="event-editor schedule-editor" onSubmit={e => void save(e)} noValidate>
    {!editable && <p className="notice">{strings.manage.lockedSchedule}</p>}
    {event.registeredCount > 0 && <p className="notice">{strings.manage.scheduleWarning(event.registeredCount)}</p>}
    <fieldset disabled={!editable || busy}>
      <Field label={copy.start} error={editable ? show('startTime') : ''}><Input type="datetime-local" value={value.startTime} onInput={e => change('startTime',e.currentTarget.value)} onBlur={() => setTouched(before => ({...before,startTime:true}))} required /></Field>
      <Field label={copy.end} error={editable ? show('endTime') : ''}><Input type="datetime-local" value={value.endTime} onInput={e => change('endTime',e.currentTarget.value)} onBlur={() => setTouched(before => ({...before,endTime:true}))} required /></Field>
      {duration && <p className="hint">{copy.durationLabel(duration)}</p>}
    </fieldset>
    {error && <p className="notice error" role="alert">{error}</p>}
    <Button type="submit" disabled={!editable} loading={busy}>{strings.manage.saveSchedule}</Button>
  </form>;
}
