import { EVENT_COVERS } from '../../features/events/eventImages';
import { strings } from '../../copy/strings';
import { Field, Input, Select } from './forms';
import { EventImage } from './EventImage';

export function EventCoverField({ value, title, category, error, onChange }: {
  value: string; title: string; category: string; error?: string; onChange: (value: string) => void;
}) {
  const copy = strings.organizer.form;
  const selected = EVENT_COVERS.some(cover => cover.value === value) ? value : value ? 'custom' : '';
  return <section className="event-form-group event-cover-editor">
    <h2>{copy.banner}</h2>
    <div className="event-cover-fields">
      <Field label={copy.coverChoice}><Select value={selected} onChange={e => onChange(e.target.value === 'custom' ? '' : e.target.value)}>
        <option value="">{copy.coverAutomatic}</option>
        {EVENT_COVERS.map(cover => <option key={cover.value} value={cover.value}>{cover.label}</option>)}
        {selected === 'custom' && <option value="custom">{copy.coverCustom}</option>}
      </Select></Field>
      <Field label={copy.imageUrl} error={error} hint={copy.coverHint}>
        <Input value={value} maxLength={500} placeholder="https://…" onChange={e => onChange(e.target.value)} />
      </Field>
    </div>
    <div className="event-cover-preview" aria-label={copy.bannerPreview}>
      <EventImage key={value} event={{ title, category, bannerImage: value }} eager />
    </div>
  </section>;
}
