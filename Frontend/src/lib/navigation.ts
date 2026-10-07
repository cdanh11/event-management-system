import type { Role } from '../types';

export const homePath = (role: Role) => role === 'ATTENDEE' ? '/events' : role === 'STAFF' ? '/staff' : '/organizer';

/** A remembered route must belong to the account that just signed in. */
export function postLoginPath(role: Role, from?: string) {
  if (!from || !from.startsWith('/') || from.startsWith('//')) return homePath(role);
  const path = from.split(/[?#]/)[0];
  if (/^\/events\/[^/]+\/?$/.test(path)) return from;
  if (role === 'ATTENDEE' && (/^\/tickets\/[^/]+\/?$/.test(path) || ['/events', '/registrations', '/my-registrations'].includes(path))) return from;
  if (role === 'STAFF' && (path === '/staff' || path.startsWith('/staff/'))) return from;
  if (role === 'ORGANIZER' && (path === '/organizer' || path.startsWith('/organizer/'))) return from;
  return homePath(role);
}
