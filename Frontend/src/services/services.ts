import { request } from '../api/apiClient';
import { parseEventDate, toEventPayloadDate } from '../lib/datetime';
import type { CheckIn, CheckinRecord, Event, EventStatus, Registration, StaffAssignment, Ticket, User } from '../types';

type ApiEvent = {
  id: string;
  organizer_id: string;
  title: string;
  description: string;
  location: string;
  start_time: string;
  end_time: string;
  capacity: number;
  registered_count: number;
  status: EventStatus;
  category: string;
  banner_image: string;
  created_at: string;
};

const event = (e: ApiEvent): Event => ({
  id: e.id,
  organizerId: e.organizer_id,
  title: e.title,
  description: e.description,
  location: e.location,
  startTime: parseEventDate(e.start_time).toISOString(),
  endTime: parseEventDate(e.end_time).toISOString(),
  capacity: e.capacity,
  registeredCount: e.registered_count,
  status: e.status,
  category: e.category,
  bannerImage: e.banner_image,
  createdAt: e.created_at,
});

type EventInput = Omit<Event, 'id' | 'registeredCount' | 'status' | 'createdAt' | 'organizerId'>;
type EventUpdate = Partial<Pick<Event, 'title' | 'description' | 'location' | 'startTime' | 'endTime' | 'capacity' | 'category' | 'bannerImage'>>;

const eventPayload = (value: EventInput | EventUpdate) => ({
  ...(value.title !== undefined && { title: value.title }),
  ...(value.description !== undefined && { description: value.description }),
  ...(value.location !== undefined && { location: value.location }),
  ...(value.startTime !== undefined && { start_time: toEventPayloadDate(value.startTime) }),
  ...(value.endTime !== undefined && { end_time: toEventPayloadDate(value.endTime) }),
  ...(value.capacity !== undefined && { capacity: value.capacity }),
  ...(value.category !== undefined && { category: value.category }),
  ...(value.bannerImage !== undefined && { banner_image: value.bannerImage }),
});

type ApiRegistration = {
  id: string;
  event_id: string;
  attendee_id: string;
  registered_at: string;
  status: Registration['status'];
};

const registration = (r: ApiRegistration): Registration => ({
  id: r.id,
  eventId: r.event_id,
  attendeeId: r.attendee_id,
  registeredAt: r.registered_at,
  status: r.status,
});

type ApiTicket = {
  id: string;
  registration_id: string;
  ticket_code: string;
  qr_value: string;
  status: Ticket['status'];
  issued_at: string;
};

const ticket = (t: ApiTicket): Ticket => ({
  id: t.id,
  registrationId: t.registration_id,
  ticketCode: t.ticket_code,
  qrValue: t.qr_value,
  status: t.status,
  issuedAt: t.issued_at,
});

type ApiCheckin = {
  id: string;
  ticket_id: string;
  event_id: string;
  attendee_id: string;
  checked_in_by: string;
  checked_in_at: string;
  status: CheckIn['status'];
};

const checkin = (c: ApiCheckin): CheckIn => ({
  id: c.id,
  ticketId: c.ticket_id,
  eventId: c.event_id,
  attendeeId: c.attendee_id,
  checkedInBy: c.checked_in_by,
  checkedInAt: c.checked_in_at,
  status: c.status,
});

type ApiStaffAssignment = {
  id: string;
  event_id: string;
  staff_id: string;
  staff_name: string;
  staff_email: string;
  created_at: string;
};

const staffAssignment = (a: ApiStaffAssignment): StaffAssignment => ({
  id: a.id,
  eventId: a.event_id,
  staffId: a.staff_id,
  staffName: a.staff_name,
  staffEmail: a.staff_email,
  createdAt: a.created_at,
});

export const eventService = {
  list: async ({ q, status, limit = 100, cursor }: { q?: string; status?: EventStatus; limit?: number; cursor?: string } = {}, signal?: AbortSignal) => {
    const params = new URLSearchParams({ limit: String(limit) });
    if (q?.trim()) params.set('q', q.trim());
    if (status) params.set('status', status);
    if (cursor) params.set('cursor', cursor);
    const items = (await request<ApiEvent[]>(`/events?${params}`, { signal })).map(event);
    return { items, nextCursor: items.length === limit ? items.at(-1)?.id : undefined };
  },
  getEvents: async (limit = 20, offset = 0, opts: { status?: string; q?: string } = {}) => {
    const params = new URLSearchParams({
      limit: String(limit),
      offset: String(offset),
    });
    if (opts.status && opts.status !== 'ALL') params.set('status', opts.status);
    if (opts.q?.trim()) params.set('q', opts.q.trim());
    return (await request<ApiEvent[]>(`/events?${params.toString()}`)).map(event);
  },

  getEvent: async (id: string, signal?: AbortSignal) =>
    event(await request<ApiEvent>(`/events/${id}`, { signal })),

  occupancy: (id: string, signal?: AbortSignal) => request<{
    event_id: string; capacity: number; registered_count: number; remaining: number; status: EventStatus;
  }>(`/events/${id}/occupancy`, { signal }),

  create: async (
    input: EventInput,
    _u: User
  ) =>
    event(
      await request<ApiEvent>('/events', {
        method: 'POST',
        body: JSON.stringify(eventPayload(input)),
      })
    ),

  reschedule: async (id: string, input: EventUpdate) =>
    event(
      await request<ApiEvent>(`/events/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(eventPayload(input)),
      })
    ),

  transition: async (id: string, s: EventStatus) =>
    event(
      await request<ApiEvent>(`/events/${id}/transition`, {
        method: 'POST',
        body: JSON.stringify({ status: s }),
      })
    ),

  notify: (id: string) =>
    request<{ event_id: string; emails_sent: number; mode: string }>(`/events/${id}/notify`, {
      method: 'POST',
    }),

  remove: (id: string) =>
    request<void>(`/events/${id}`, { method: 'DELETE' }),
};

export const registrationService = {
  mine: async (_id: string, signal?: AbortSignal) =>
    (await request<ApiRegistration[]>('/registrations/me', { signal })).map(registration),

  get: async (id: string, signal?: AbortSignal) =>
    registration(await request<ApiRegistration>(`/registrations/${id}`, { signal })),

  register: async (eventId: string, _u: User) => {
    const r = await request<{ registration: ApiRegistration; ticket: ApiTicket }>(
      `/events/${eventId}/register`,
      { method: 'POST' }
    );
    return {
      registration: registration(r.registration),
      ticket: ticket(r.ticket),
    };
  },

  cancel: async (id: string) =>
    registration(await request<ApiRegistration>(`/registrations/${id}/cancel`, { method: 'POST' })),
};

export const ticketService = {
  get: async (id: string, signal?: AbortSignal) =>
    ticket(await request<ApiTicket>(`/tickets/${id}`, { signal })),

  forRegistration: async (id: string, signal?: AbortSignal) =>
    ticket(await request<ApiTicket>(`/registrations/${id}/ticket`, { signal })),
};

export const checkinService = {
  checkin: async (code: string, _u: User, eventId?: string) =>
    checkin(
      await request<ApiCheckin>('/checkins', {
        method: 'POST',
        body: JSON.stringify({ ticket_code: code, event_id: eventId }),
      })
    ),
};

export const organizerService = {
  page: async ({ status, q, sort = 'soonest', limit = 20, offset = 0, signal }: {
    status?: string; q?: string; sort?: 'soonest' | 'popular'; limit?: number; offset?: number; signal?: AbortSignal;
  }) => {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset), sort });
    if (status && status !== 'ALL') params.set('status', status);
    if (q?.trim()) params.set('q', q.trim());
    const data = await request<{ items: ApiEvent[]; total: number; limit: number; offset: number; has_more: boolean }>(`/organizer/events?${params}`, { signal });
    return { ...data, items: data.items.map(event) };
  },
  dashboard: async (signal?: AbortSignal) => {
    const data = await request<{
      events: ApiEvent[];
      total_registrations: number;
      total_checkins: number;
    }>('/organizer/dashboard', { signal });

    return {
      ...data,
      events: data.events.map(event),
    };
  },
};

export const staffService = {
  listStaff: (signal?: AbortSignal) => request<User[]>('/users?role=STAFF', { signal }),

  assignedTo: async (eventId: string, signal?: AbortSignal) =>
    (await request<ApiStaffAssignment[]>(`/events/${eventId}/staff`, { signal })).map(staffAssignment),

  assign: (eventId: string, staffId: string) =>
    request<{ event_id: string; staff_id: string }>(`/events/${eventId}/staff`, {
      method: 'POST',
      body: JSON.stringify({ staff_id: staffId }),
    }),

  create: (input: { name: string; email: string; password: string }) =>
    request<User>('/users/staff', {
      method: 'POST',
      body: JSON.stringify(input),
    }),

  myEvents: async (signal?: AbortSignal) =>
    (await request<ApiEvent[]>('/staff/events', { signal })).map(event),
};

type ApiCheckinRecord = {
  id: string;
  ticket_code: string;
  attendee_name: string;
  checked_in_at: string;
};

export const checkinHistoryService = {
  list: async (eventId: string, limit = 20, signal?: AbortSignal) =>
    (await request<ApiCheckinRecord[]>(`/events/${eventId}/checkins?limit=${limit}`, { signal })).map(
      (r): CheckinRecord => ({
        id: r.id,
        ticketCode: r.ticket_code,
        attendeeName: r.attendee_name,
        checkedInAt: r.checked_in_at,
      })
    ),
};
