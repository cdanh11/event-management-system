import { lazy, Suspense } from 'react';
import { Navigate, Outlet, Route, Routes } from 'react-router-dom';
import { ToastProvider } from '../components/ui/Toast';
import { AppShell, RoleGuard, homePath } from '../components/layout/AppShell';
import { useAuth } from '../features/auth/useAuth';
import { Skeleton } from '../components/ui/states';
import { strings } from '../copy/strings';

const Login = lazy(() => import('../pages/Login').then(m => ({ default: m.Login })));
const Register = lazy(() => import('../pages/Register').then(m => ({ default: m.Register })));
const Explore = lazy(() => import('../pages/attendee/Explore').then(m => ({ default: m.Explore })));
const EventDetail = lazy(() => import('../pages/attendee/EventDetail').then(m => ({ default: m.EventDetail })));
const MyRegistrations = lazy(() => import('../pages/attendee/MyRegistrations').then(m => ({ default: m.MyRegistrations })));
const Ticket = lazy(() => import('../pages/attendee/Ticket').then(m => ({ default: m.TicketPage })));
const CheckinDesk = lazy(() => import('../pages/staff/CheckinDesk').then(m => ({ default: m.CheckinDesk })));
const Dashboard = lazy(() => import('../pages/organizer/Dashboard').then(m => ({ default: m.Dashboard })));
const Events = lazy(() => import('../pages/organizer/Events').then(m => ({ default: m.Events })));
const Manage = lazy(() => import('../pages/organizer/Manage').then(m => ({ default: m.Manage })));
const Create = lazy(() => import('../pages/organizer/Create').then(m => ({ default: m.Create })));
const Live = lazy(() => import('../pages/organizer/Live').then(m => ({ default: m.Live })));
const Forbidden = lazy(() => import('../pages/errors').then(m => ({ default: m.Forbidden })));
const NotFound = lazy(() => import('../pages/errors').then(m => ({ default: m.NotFound })));

function Loading() {
  return <div role="status" aria-label={strings.common.loadingPage}><Skeleton kind="row" /><Skeleton kind="row" /></div>;
}

function IndexRoute() {
  const { user, ready } = useAuth();
  if (!ready) return <Loading />;
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={homePath(user.role)} replace />;
}

function PageOutlet() {
  return <Suspense fallback={<Loading />}><Outlet /></Suspense>;
}

export function App() {
  return (
    <ToastProvider>
        <Routes>
          <Route element={<PageOutlet />}>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
          </Route>
          <Route element={<AppShell />}>
            <Route path="/" element={<IndexRoute />} />
            <Route element={<RoleGuard roles={['ATTENDEE']} />}>
              <Route path="/events" element={<Explore />} />
              <Route path="/registrations" element={<MyRegistrations />} />
              <Route path="/tickets/:id" element={<Ticket />} />
              <Route path="/my-registrations" element={<Navigate to="/registrations" replace />} />
            </Route>
            <Route element={<RoleGuard roles={['STAFF']} />}>
              <Route path="/staff" element={<CheckinDesk />} />
              <Route path="/staff/checkin" element={<Navigate to="/staff" replace />} />
              <Route path="/staff/check-in" element={<Navigate to="/staff" replace />} />
              <Route path="/staff/attendees" element={<Navigate to="/staff" replace />} />
            </Route>
            <Route element={<RoleGuard roles={['ORGANIZER']} />}>
              <Route path="/organizer" element={<Dashboard />} />
              <Route path="/organizer/events" element={<Events />} />
              <Route path="/organizer/events/:id" element={<Manage />} />
              <Route path="/organizer/create" element={<Create />} />
              <Route path="/organizer/live" element={<Live />} />
            </Route>
            <Route path="/events/:id" element={<EventDetail />} />
            <Route path="/403" element={<Forbidden />} />
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
    </ToastProvider>
  );
}
