import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../features/auth/useAuth';
import { useToast } from '../../components/ui/Toast';
import { eventService } from '../../services/services';
import { PageHeader } from '../../components/ui/PageHeader';
import { Button } from '../../components/ui/Button';
import { Field, Input, Select, Textarea } from '../../components/ui/forms';
import { strings } from '../../copy/strings';
import { toInputValue, fromInputValue } from '../../lib/datetime';
import { friendlyError } from '../../lib/errors';
import { useNow } from '../../realtime/useNow';
import { durationLabel, eventFormErrors, eventServerErrors, type EventFormValues } from '../../features/organizer/eventForm';

export function Create() {
  const now = useNow(30_000);
  const { user } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();
  const copy = strings.organizer.form;
  const [form, setForm] = useState<EventFormValues>(() => {
    const start = new Date(Date.now() + 86_400_000);
    return { title: '', description: '', location: '', startTime: toInputValue(start),
      endTime: toInputValue(new Date(+start + 10_800_000)), capacity: '100', category: copy.categories[0], bannerImage: '' };
  });
  const [touched, setTouched] = useState<Record<string, boolean>>({});
  const [serverErrors, setServerErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const errors = eventFormErrors(form, now);
  const change = (key: keyof EventFormValues, value: string) => {
    setForm(before => ({ ...before, [key]: value }));
    setServerErrors(before => ({ ...before, [key]: '' }));
    setError('');
  };
  const touch = (key: string) => setTouched(before => ({ ...before, [key]: true }));
  const show = (key: keyof typeof errors) => serverErrors[key] || (touched[key] ? errors[key] : '');
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (busy || !user) return;
    setTouched(Object.fromEntries(Object.keys(form).map(key => [key, true])));
    setError(''); setServerErrors({});
    // Validate against the actual submission time, not the last clock tick.
    if (Object.values(eventFormErrors(form, Date.now())).some(Boolean)) return;
    setBusy(true);
    try {
      const created = await eventService.create({
        title: form.title.trim(), description: form.description.trim(), location: form.location.trim(),
        category: form.category, bannerImage: form.bannerImage.trim(), capacity: Number(form.capacity),
        startTime: fromInputValue(form.startTime), endTime: fromInputValue(form.endTime),
      }, user);
      toast(copy.created, 'success');
      navigate(`/organizer/events/${created.id}`);
    } catch (err) { setError(friendlyError(err)); setServerErrors(eventServerErrors(err)); }
    finally { setBusy(false); }
  };
  const duration = durationLabel(form);
  return <div className="event-create-page">
    <PageHeader title={strings.organizer.newEvent} />
    <div className="event-create-layout">
      <form className="event-editor" onSubmit={e => void submit(e)} noValidate>
        <fieldset disabled={busy}>
          <section className="event-form-group"><h2>{copy.basics}</h2>
            <Field label={copy.title} error={show('title')} hint={`${form.title.length}/200`}>
              <Input value={form.title} onChange={e => change('title',e.target.value)} onBlur={() => touch('title')} required />
            </Field>
            <Field label={copy.description} error={show('description')}><Textarea rows={5} value={form.description} onChange={e => change('description',e.target.value)} onBlur={() => touch('description')} required /></Field>
            <Field label={copy.category} error={serverErrors.category}><Select value={form.category} onChange={e => change('category',e.target.value)}>{copy.categories.map(category => <option key={category}>{category}</option>)}</Select></Field>
          </section>
          <section className="event-form-group"><h2>{copy.whenWhere}</h2>
            <Field label={copy.start} error={show('startTime')}><Input type="datetime-local" value={form.startTime} onInput={e => change('startTime',e.currentTarget.value)} onBlur={() => touch('startTime')} required /></Field>
            <Field label={copy.end} error={show('endTime')}><Input type="datetime-local" value={form.endTime} onInput={e => change('endTime',e.currentTarget.value)} onBlur={() => touch('endTime')} required /></Field>
            {duration && <p className="hint" aria-live="polite">{copy.durationLabel(duration)}</p>}
            <Field label={copy.location} error={show('location')}><Input value={form.location} onChange={e => change('location',e.target.value)} onBlur={() => touch('location')} required /></Field>
            <Field label={copy.capacity} error={show('capacity')}><Input type="number" min={1} step={1} value={form.capacity} onChange={e => change('capacity',e.target.value)} onBlur={() => touch('capacity')} required /></Field>
          </section>
        </fieldset>
        {error && <p className="notice error" role="alert">{error}</p>}
        <div className="form-actions"><Button type="submit" loading={busy}>{copy.create}</Button><Link className="quiet-link" to="/organizer/events">{strings.common.cancel}</Link></div>
      </form>
    </div>
  </div>;
}
