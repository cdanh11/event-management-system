import { errors } from '../copy/strings';
import type { ApiError } from '../types';

export function friendlyError(error: unknown): string {
  const value = error as Partial<ApiError> | undefined;
  if (value?.code && value.code in errors) return errors[value.code as keyof typeof errors];
  if (value?.status && value.status >= 500) return errors.server;
  if (error instanceof TypeError) return errors.network;
  return errors.fallback;
}

export function fieldErrors(error: unknown): Record<string, string> {
  const details = (error as Partial<ApiError>)?.details;
  return Object.fromEntries((details ?? []).map(({ loc, msg }) => [String(loc.at(-1) ?? 'form'), msg]));
}
