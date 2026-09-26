import { request } from '../api/apiClient';
import type { CheckIn, Event, EventStatus, Registration, Ticket, User } from '../types';

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

// Helper mapper: ApiEvent (snake_case) -> Event (camelCase)
const mapEvent = (e: ApiEvent): Event => ({
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

// Helper payload converter: CreateEventInput -> ApiEvent payload (snake_case)
type CreateEventInput = Omit<Event, 'id' | 'registeredCount' | 'status' | 'createdAt' | 'organizerId'>;

const mapPayload = (v: CreateEventInput) => ({
  title: v.title,
  description: v.description,
  location: v.location,
  start_time: v.startTime,
  end_time: v.endTime,
  capacity: v.capacity,
  category: v.category,
  banner_image: v.bannerImage,
});

// Services
export const eventService = {
  getEvents: async (): Promise<Event[]> => {
    const data = await request<ApiEvent[]>('/events');
    return data.map(mapEvent);
  },

  getEvent: async (id: string): Promise<Event> => {
    const data = await request<ApiEvent>(`/events/${id}`);
    return mapEvent(data);
  },

  create: async (input: CreateEventInput, _u: User): Promise<Event> => {
    const data = await request<ApiEvent>('/events', {
      method: 'POST',
      body: JSON.stringify(mapPayload(input)),
    });
    return mapEvent(data);
  },

  transition: async (id: string, s: EventStatus): Promise<Event> => {
    const data = await request<ApiEvent>(`/events/${id}/transition`, {
      method: 'POST',
      body: JSON.stringify({ status: s }),
    });
    return mapEvent(data);
  },
};

export const registrationService = {
  mine: (_id: string) => 
    request<Registration[]>('/registrations/me'),

  get: (id: string) => 
    request<Registration>(`/registrations/${id}`),

  register: (eventId: string, _u: User) => 
    request<{ registration: Registration; ticket: Ticket }>(`/events/${eventId}/register`, {
      method: 'POST',
    }),

  cancel: (id: string) => 
    request<Registration>(`/registrations/${id}/cancel`, {
      method: 'POST',
    }),
};

export const ticketService = {
  get: (id: string) => 
    request<Ticket>(`/tickets/${id}`),

  forRegistration: (id: string) => 
    request<Ticket>(`/registrations/${id}/ticket`),
};

export const checkinService = {
  checkin: (code: string, _u: User) => 
    request<CheckIn>('/checkins', {
      method: 'POST',
      body: JSON.stringify({ ticket_code: code }),
    }),
};

export const organizerService = {
  dashboard: async () => {
    type DashboardResponse = {
      events: ApiEvent[];
      total_registrations: number;
      total_checkins: number;
    };

    const data = await request<DashboardResponse>('/organizer/dashboard');
    return {
      ...data,
      events: data.events.map(mapEvent),
    };
  },
};