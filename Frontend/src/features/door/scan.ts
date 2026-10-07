import { strings } from '../../copy/strings';
import { friendlyError } from '../../lib/errors';
import type { ApiError } from '../../types';

export const normalizeTicketCode = (value: string) => value.replace(/\s+/g, '').toUpperCase();
export type ScanReceipt = {
  id: number; eventId: string; code: string; at: string;
  tone: 'success' | 'warning' | 'error'; title: string; detail?: string;
};

export function scanFailure(error: unknown): Pick<ScanReceipt, 'tone' | 'title' | 'detail'> {
  const code = (error as Partial<ApiError>)?.code;
  const titles: Record<string, string> = {
    TICKET_ALREADY_USED: strings.staff.used,
    INVALID_TICKET: strings.staff.notFound,
    TICKET_CANCELLED: strings.staff.cancelled,
    CHECKIN_CLOSED: strings.staff.closed,
    FORBIDDEN: strings.staff.forbidden,
    WRONG_EVENT: strings.staff.wrongEvent,
  };
  return { tone: code === 'TICKET_ALREADY_USED' ? 'warning' : 'error', title: titles[code ?? ''] ?? strings.staff.failed, detail: friendlyError(error) };
}
