/* eslint-disable react/only-export-components -- shell + contexts + guard colocated by design */
import { createContext, Suspense, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import { Link, Navigate, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { LogOut, Menu, X } from 'lucide-react';
import { useAuth } from '../../features/auth/useAuth';
import { useToast } from '../ui/Toast';
import type { Role } from '../../types';
import { Skeleton } from '../ui/states';
import { strings } from '../../copy/strings';
import { homePath } from '../../lib/navigation';
export { homePath } from '../../lib/navigation';

/* Global search query shared between TopNav (input) and the Explore page (list). */
const SearchContext = createContext<{ q: string; setQ: (v: string) => void }>({
  q: '',
  setQ: () => undefined,
});
export const useGlobalSearch = () => useContext(SearchContext);

function TopNavInner() {
  const { user, logout } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const [open, setOpen] = useState(false);
  const menuToggle = useRef<HTMLButtonElement | null>(null);
  useEffect(() => {
    if (!open) return;
    const close = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { setOpen(false); menuToggle.current?.focus(); }
    };
    document.addEventListener('keydown', close);
    return () => document.removeEventListener('keydown', close);
  }, [open]);
  if (!user) return null;

  const links =
    user.role === 'ATTENDEE'
      ? [
          [strings.nav.explore, '/events'],
          [strings.nav.myTickets, '/registrations'],
        ]
      : user.role === 'STAFF'
        ? [[strings.nav.door, '/staff']]
        : [
            [strings.nav.overview, '/organizer'],
            [strings.nav.events, '/organizer/events'],
            [strings.nav.live, '/organizer/live'],
          ];

  return (
    <header>
      <a className="skip-link" href="#main-content">{strings.nav.skip}</a>
      <Link className="brand" to={homePath(user.role)} aria-label={strings.nav.home}>
        <span>{strings.brandMark}</span>{strings.appName}
      </Link>
      <button
        className="icon nav-toggle"
        ref={menuToggle}
        aria-controls="primary-navigation"
        aria-label={open ? strings.nav.closeMenu : strings.nav.openMenu}
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        {open ? <X size={20} /> : <Menu size={20} />}
      </button>
      <nav id="primary-navigation" aria-label={strings.nav.primary} className={open ? 'nav-open' : ''}>
        {links.map(([label, path]) =>
          (
            <NavLink
              key={path}
              to={path}
              end={path === '/organizer'}
              className={({ isActive }) => (isActive || (path === '/registrations' && pathname.startsWith('/tickets/')) ? 'active' : '')}
              onClick={() => setOpen(false)}
            >
              {label}
            </NavLink>
          )
        )}
        {user.role === 'ORGANIZER' && (
          <NavLink to="/organizer/create" onClick={() => setOpen(false)}>
            {strings.nav.newEvent}
          </NavLink>
        )}
      </nav>
      <div className="profile">
        <small>
          {user.name}
        </small>
        <button
          className="icon"
          aria-label={strings.nav.signOut}
          onClick={() => {
            logout();
            toast(strings.nav.signedOut, 'info');
            navigate('/login');
          }}
        >
          <LogOut size={18} />
          {strings.nav.signOut}
        </button>
      </div>
    </header>
  );
}

export function OfflineBanner() {
  const [online, setOnline] = useState(navigator.onLine);
  useEffect(() => {
    const on = () => setOnline(true);
    const off = () => setOnline(false);
    window.addEventListener('online', on);
    window.addEventListener('offline', off);
    return () => {
      window.removeEventListener('online', on);
      window.removeEventListener('offline', off);
    };
  }, []);
  if (online) return null;
  return (
    <div className="offline-banner" role="alert">
      {strings.common.offline}
    </div>
  );
}

export function AppShell({ children }: { children?: ReactNode }) {
  const [q, setQ] = useState('');
  const { ready } = useAuth();
  return (
    <SearchContext.Provider value={{ q, setQ }}>
      <OfflineBanner />
      <TopNavInner />
      <main id="main-content">
        {!ready ? <Skeleton kind="row" /> : <Suspense fallback={<Skeleton kind="row" />}>{children ?? <Outlet />}</Suspense>}
      </main>
    </SearchContext.Provider>
  );
}

/* Route guard: unauthenticated -> /login (remembering the path);
   wrong role -> friendly /403. */
export function RoleGuard({ roles, children }: { roles: Role[]; children?: ReactNode }) {
  const { user, ready } = useAuth();
  const location = useLocation();
  if (!ready) return <Skeleton kind="row" />;
  if (!user) return <Navigate to="/login" state={{ from: location.pathname, expired: !!sessionStorage.getItem('evently-session-expired') }} replace />;
  if (!roles.includes(user.role)) return <div className="error-page"><h1>{strings.errors.forbiddenTitle}</h1><Link to={homePath(user.role)}>{strings.common.goHome}</Link></div>;
  return <>{children ?? <Outlet />}</>;
}
