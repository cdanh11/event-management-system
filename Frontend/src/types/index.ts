export type Role = 'ATTENDEE' | 'STAFF' | 'ORGANIZER';

export type EventStatus = 
  | 'DRAFT' 
  | 'PUBLISHED' 
  | 'ONGOING' 
  | 'COMPLETED' 
  | 'CANCELLED';

export type RegistrationStatus = 'REGISTERED' | 'CANCELLED';

export type TicketStatus = 'VALID' | 'USED' | 'CANCELLED';

export interface User {
  id: string;
  name: string;
  email: string;
  role: Role;
  avatar: string;
}

export interface Event {
  id: string;
  organizerId: string;
  title: string;
  description: string;
  location: string;
  startTime: string;
  endTime: string;
  capacity: number;
  registeredCount: number;
  status: EventStatus;
  category: string;
  bannerImage: string;
  createdAt: string;
}

export interface Registration {
  id: string;
  eventId: string;
  attendeeId: string;
  registeredAt: string;
  status: RegistrationStatus;
}

export interface Ticket {
  id: string;
  registrationId: string;
  ticketCode: string;
  qrValue: string;
  status: TicketStatus;
  issuedAt: string;
}

export interface CheckIn {
  id: string;
  ticketId: string;
  eventId: string;
  attendeeId: string;
  checkedInBy: string;
  checkedInAt: string;
  status: 'SUCCESS' | 'REJECTED';
}

export interface ApiError extends Error {
  status: number;
  code: string;
}

export interface StaffAssignment {
  id: string;
  eventId: string;
  staffId: string;
  staffName: string;
  staffEmail: string;
  createdAt: string;
}
