import { strings } from '../../copy/strings';
import { fieldErrors } from '../../lib/errors';

export type ScheduleValues = { startTime: string; endTime: string };
export type EventFormValues = ScheduleValues & { title: string; description: string; location: string; capacity: string; category: string; bannerImage: string };
const copy = strings.organizer.form;
export const validDate = (value: string) => !!value && Number.isFinite(+new Date(value));
export function scheduleErrors(value: ScheduleValues, now: number) {
  const start = +new Date(value.startTime);
  const end = +new Date(value.endTime);
  return {
    startTime: !validDate(value.startTime) ? copy.startRequired : start <= now ? copy.startFuture : '',
    endTime: !validDate(value.endTime) ? copy.endRequired : Number.isFinite(start) && end <= start ? copy.endAfter : '',
  };
}
export function validImageUrl(value: string) {
  try { return ['https:', 'http:'].includes(new URL(value).protocol); } catch { return false; }
}
export function eventFormErrors(value: EventFormValues, now: number) {
  return {
    ...scheduleErrors(value, now),
    title: !value.title.trim() ? copy.titleRequired : value.title.trim().length > 200 ? copy.titleLong : '',
    description: !value.description.trim() ? copy.descriptionRequired : '',
    location: !value.location.trim() ? copy.locationRequired : '',
    capacity: !value.capacity.trim() || !Number.isSafeInteger(Number(value.capacity)) || Number(value.capacity) < 1 ? copy.capacityInvalid : '',
    bannerImage: value.bannerImage.trim() && !validImageUrl(value.bannerImage.trim()) ? copy.bannerInvalid : '',
  };
}
export function durationLabel(value: ScheduleValues) {
  const minutes = Math.round((+new Date(value.endTime) - +new Date(value.startTime)) / 60_000);
  return Number.isFinite(minutes) && minutes > 0 ? copy.duration(Math.floor(minutes / 60), minutes % 60) : '';
}
export function eventServerErrors(error: unknown) {
  const names: Record<string, string> = { start_time: 'startTime', end_time: 'endTime', banner_image: 'bannerImage', body: 'endTime' };
  return Object.fromEntries(Object.entries(fieldErrors(error)).map(([key, value]) => [names[key] ?? key, value]));
}
