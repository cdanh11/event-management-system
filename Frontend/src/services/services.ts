import { request } from '../api/apiClient';
import type { CheckIn, Event, EventStatus, Registration, StaffAssignment, Ticket, User } from '../types';

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
  startTime: e.start_time,
  endTime: e.end_time,
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
  ...(value.startTime !== undefined && { start_time: value.startTime }),
  ...(value.endTime !== undefined && { end_time: value.endTime }),
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
  getEvents: async (limit = 20, offset = 0) =>
    (await request<ApiEvent[]>(`/events?limit=${limit}&offset=${offset}`)).map(event),

  getEvent: async (id: string) => 
    event(await request<ApiEvent>(`/events/${id}`)),

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
  mine: async (_id: string) =>
    (await request<ApiRegistration[]>('/registrations/me')).map(registration),

  get: async (id: string) =>
    registration(await request<ApiRegistration>(`/registrations/${id}`)),

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
  get: async (id: string) => 
    ticket(await request<ApiTicket>(`/tickets/${id}`)),

  forRegistration: async (id: string) => 
    ticket(await request<ApiTicket>(`/registrations/${id}/ticket`)),
};

export const checkinService = {
  checkin: async (code: string, _u: User) =>
    checkin(
      await request<ApiCheckin>('/checkins', {
        method: 'POST',
        body: JSON.stringify({ ticket_code: code }),
      })
    ),
};

export const organizerService = {
  dashboard: async () => {
    const data = await request<{
      events: ApiEvent[];
      total_registrations: number;
      total_checkins: number;
    }>('/organizer/dashboard');

    return {
      ...data,
      events: data.events.map(event),
    };
  },
};

export const staffService = {
  listStaff: () => request<User[]>('/users?role=STAFF'),

  assignedTo: async (eventId: string) =>
    (await request<ApiStaffAssignment[]>(`/events/${eventId}/staff`)).map(staffAssignment),

  assign: (eventId: string, staffId: string) =>
    request<{ event_id: string; staff_id: string }>(`/events/${eventId}/staff`, {
      method: 'POST',
      body: JSON.stringify({ staff_id: staffId }),
    }),
};
