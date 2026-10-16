import { useState, type FormEvent } from 'react';
import type { Event } from '../../types';
import { eventService } from '../../services/services';
import { EventCoverField } from '../../components/ui/EventCoverField';
import { Button } from '../../components/ui/Button';
import { useToast } from '../../components/ui/Toast';
import { validEventImage } from '../events/eventImages';
import { canReschedule } from '../../lib/status';
import { friendlyError } from '../../lib/errors';
import { strings } from '../../copy/strings';

export function CoverForm({ event, onChanged }: { event: Event; onChanged: (event: Event) => void }) {
  const [draft, setDraft] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const { toast } = useToast();
  const value = draft ?? event.bannerImage;
  const copy = strings.organizer.form;
  if (!canReschedule(event.status)) return null;
  const save = async (e: FormEvent) => {
    e.preventDefault();
    if (busy) return;
    if (value.trim() && !validEventImage(value)) { setError(copy.bannerInvalid); return; }
    setBusy(true); setError('');
    try {
      const updated = await eventService.reschedule(event.id, { bannerImage: value.trim() });
      onChanged(updated); setDraft(null); toast(copy.coverSaved, 'success');
    } catch (err) { setError(friendlyError(err)); }
    finally { setBusy(false); }
  };
  return <form className="event-editor event-cover-form" onSubmit={e => void save(e)} noValidate>
    <fieldset disabled={busy}>
      <EventCoverField value={value} title={event.title} category={event.category} onChange={next => { setDraft(next); setError(''); }} />
    </fieldset>
    {error && <p className="notice error" role="alert">{error}</p>}
    <Button type="submit" loading={busy} disabled={draft === null || value.trim() === event.bannerImage}>{copy.coverSave}</Button>
  </form>;
}
