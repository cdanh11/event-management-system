import type { CheckIn, Event, Registration, Ticket, User } from '../types';

const pic = (id: number) => 
  `https://images.unsplash.com/photo-${id}?auto=format&fit=crop&w=1200&q=80`;

export const users: User[] = [
  { id: 'u1', name: 'Minh Nguyen', email: 'attendee@demo.com', role: 'ATTENDEE', avatar: 'MN' },
  { id: 'u2', name: 'Linh Tran', email: 'linh@demo.com', role: 'ATTENDEE', avatar: 'LT' },
  { id: 'u3', name: 'Huy Pham', email: 'huy@demo.com', role: 'ATTENDEE', avatar: 'HP' },
  { id: 's1', name: 'An Le', email: 'staff@demo.com', role: 'STAFF', avatar: 'AL' },
  { id: 's2', name: 'Khanh Do', email: 'khanh.staff@demo.com', role: 'STAFF', avatar: 'KD' },
  { id: 'o1', name: 'Evently Team', email: 'organizer@demo.com', role: 'ORGANIZER', avatar: 'ET' },
];

export const events: Event[] = [
  {
    id: 'e1',
    organizerId: 'o1',
    title: 'Vietnam Tech Conference 2026',
    description: 'A full day of practical talks, product ideas and meaningful connections for the technology community.',
    location: 'SECC, District 7, Ho Chi Minh City',
    startTime: '2026-10-20T08:30:00',
    endTime: '2026-10-20T17:30:00',
    capacity: 300,
    registeredCount: 184,
    status: 'PUBLISHED',
    category: 'Technology',
    bannerImage: pic(1505373877841),
    createdAt: '2026-08-01',
  },
  {
    id: 'e2',
    organizerId: 'o1',
    title: 'Design Systems Workshop',
    description: 'Build a resilient visual language and reusable interface foundations with experienced designers.',
    location: 'The Sentry, Nguyen Huu Canh',
    startTime: '2026-09-28T09:00:00',
    endTime: '2026-09-28T16:00:00',
    capacity: 50,
    registeredCount: 47,
    status: 'PUBLISHED',
    category: 'Workshop',
    bannerImage: pic(1516321318423),
    createdAt: '2026-08-04',
  },
  {
    id: 'e3',
    organizerId: 'o1',
    title: 'Career Fair: Future Makers',
    description: 'Meet leading teams, discover open roles, and take the next step in your career.',
    location: 'RMIT University Saigon South',
    startTime: '2026-10-05T08:00:00',
    endTime: '2026-10-05T15:00:00',
    capacity: 150,
    registeredCount: 150,
    status: 'PUBLISHED',
    category: 'Career',
    bannerImage: pic(1521737711867),
    createdAt: '2026-08-10',
  },
  {
    id: 'e4',
    organizerId: 'o1',
    title: 'AI Product Meetup',
    description: 'An evening for people building useful products with modern AI.',
    location: 'Toong, Vo Thi Sau',
    startTime: '2026-09-13T18:00:00',
    endTime: '2026-09-13T21:00:00',
    capacity: 80,
    registeredCount: 63,
    status: 'ONGOING',
    category: 'Technology',
    bannerImage: pic(1517048676732),
    createdAt: '2026-08-12',
  },
  {
    id: 'e5',
    organizerId: 'o1',
    title: 'Startup Pitch Night',
    description: 'Founders share their next big thing in a friendly, focused setting.',
    location: 'Nexus Building, District 1',
    startTime: '2026-08-15T18:00:00',
    endTime: '2026-08-15T21:00:00',
    capacity: 100,
    registeredCount: 89,
    status: 'COMPLETED',
    category: 'Business',
    bannerImage: pic(1556761175),
    createdAt: '2026-07-01',
  },
  {
    id: 'e6',
    organizerId: 'o1',
    title: 'Community Design Day',
    description: 'A cancelled community gathering.',
    location: 'Online',
    startTime: '2026-11-02T09:00:00',
    endTime: '2026-11-02T17:00:00',
    capacity: 60,
    registeredCount: 12,
    status: 'CANCELLED',
    category: 'Design',
    bannerImage: pic(1497366754035),
    createdAt: '2026-08-20',
  },
];

export const registrations: Registration[] = [
  { id: 'r1', eventId: 'e4', attendeeId: 'u1', registeredAt: '2026-09-10', status: 'REGISTERED' },
  { id: 'r2', eventId: 'e1', attendeeId: 'u2', registeredAt: '2026-09-01', status: 'REGISTERED' },
  { id: 'r3', eventId: 'e2', attendeeId: 'u3', registeredAt: '2026-09-05', status: 'REGISTERED' },
  { id: 'r4', eventId: 'e5', attendeeId: 'u1', registeredAt: '2026-08-01', status: 'REGISTERED' },
];

export const tickets: Ticket[] = [
  { id: 't1', registrationId: 'r1', ticketCode: 'AI-MEET-2026', qrValue: 'AI-MEET-2026', status: 'VALID', issuedAt: '2026-09-10' },
  { id: 't2', registrationId: 'r2', ticketCode: 'VTC-84L9Q', qrValue: 'VTC-84L9Q', status: 'VALID', issuedAt: '2026-09-01' },
  { id: 't3', registrationId: 'r3', ticketCode: 'DSW-3K8PX', qrValue: 'DSW-3K8PX', status: 'USED', issuedAt: '2026-09-05' },
  { id: 't4', registrationId: 'r4', ticketCode: 'SPN-9D2JK', qrValue: 'SPN-9D2JK', status: 'USED', issuedAt: '2026-08-01' },
];

export const checkins: CheckIn[] = [
  { id: 'c1', ticketId: 't3', eventId: 'e2', attendeeId: 'u3', checkedInBy: 's1', checkedInAt: '2026-09-28T09:11:00', status: 'SUCCESS' },
  { id: 'c2', ticketId: 't4', eventId: 'e5', attendeeId: 'u1', checkedInBy: 's1', checkedInAt: '2026-08-15T18:09:00', status: 'SUCCESS' },
];