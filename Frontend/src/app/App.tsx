import { useState } from 'react';
import { Navigate, Route, Routes, Link, useNavigate, useParams } from 'react-router-dom';
import { CalendarDays, CheckCircle2, LogOut, MapPin, Search, Users } from 'lucide-react';
import { useAuth } from '../features/auth/AuthContext';
import { useAsync } from '../hooks/useAsync';
import {
  eventService,
  registrationService,
  ticketService,
  checkinService,
  organizerService,
  staffService 
} from '../services/services';
import type { Event, EventStatus, Registration, Role } from '../types';

// Helpers
const formatDate = (v: string) =>
  new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(v));

const renderStatus = (s: string) => (
  <span className={`badge ${s.toLowerCase()}`}>{s.replace('_', ' ')}</span>
);

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <b>{value}</b>
    </div>
  );
}

function State({ text }: { text: string }) {
  return <div className="state">{text}</div>;
}

function homePath(role: Role) {
  return role === 'ATTENDEE' ? '/events' : role === 'STAFF' ? '/staff/check-in' : '/organizer'
}

function Home() {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace/>
  return <Navigate to={homePath(user.role)} replace/>
}

// Layout & Guards
function Layout({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  if (!user) return <Navigate to="/login" replace />;

  const links =
    user.role === 'ATTENDEE'
      ? [
          ['Explore', '/events'],
          ['My registrations', '/registrations'],
        ]
      : user.role === 'STAFF'
      ? [
          ['Dashboard', '/staff'],
          ['Check-in', '/staff/check-in'],
          ['Attendees', '/staff/attendees'],
        ]
      : [
          ['Dashboard', '/organizer'],
          ['Events', '/organizer/events'],
          ['Create event', '/organizer/create'],
        ];

  return (
    <>
      <header>
        <Link className="brand" to={homePath(user.role)}><span>e</span>evently</Link>
        <nav>
          {links.map(([label, path]) => (
            <Link key={path} to={path}>
              {label}
            </Link>
          ))}
        </nav>
        <div className="profile">
          <span className="avatar">{user.avatar}</span>
          <small>
            {user.name}
            <b>{user.role}</b>
          </small>
          <button
            className="icon"
            onClick={() => {
              logout();
              navigate('/login');
            }}
          >
            <LogOut size={18} />
          </button>
        </div>
      </header>
      <main>{children}</main>
    </>
  );
}

function RoleGate({ roles, children }: { roles: Role[]; children: React.ReactNode }) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  return roles.includes(user.role)?<>{children}</>:<Navigate to={homePath(user.role)} replace/>
}

function ConfirmDialog({open,title,message,confirmLabel='Confirm',busy,onConfirm,onCancel}:{
  open:boolean;title:string;message:string;confirmLabel?:string;busy?:boolean
  onConfirm:()=>void;onCancel:()=>void
}){
  if(!open)return null
  return <div className="modal-overlay" onClick={onCancel}>
    <div className="modal-box" onClick={e=>e.stopPropagation()}>
      <h3>{title}</h3><p>{message}</p>
      <div className="modal-actions">
        <button className="secondary" disabled={busy} onClick={onCancel}>Back</button>
        <button className="primary" disabled={busy} onClick={onConfirm}>{busy?'Please wait…':confirmLabel}</button>
      </div>
    </div>
  </div>
}

// Components
function EventCard({ event }: { event: Event }) {
  return (
    <article className="event-card">
      <img src={event.bannerImage} alt="" />
      <div className="card-body">
        {renderStatus(event.status)}
        <h3>{event.title}</h3>
        <p>
          <CalendarDays /> {formatDate(event.startTime)}
        </p>
        <p>
          <MapPin /> {event.location}
        </p>
        <div className="card-footer">
          <span>
            {event.registeredCount}/{event.capacity} going
          </span>
          <Link to={`/events/${event.id}`}>View event →</Link>
        </div>
      </div>
    </article>
  );
}

// Pages
function EventsPage() {
  const { data, loading, error } = useAsync(eventService.getEvents, []);
  const [q, setQ] = useState('');
  const [filter, setFilter] = useState('ALL');

  if (loading) return <State text="Loading events…" />;
  if (error) return <State text={error.message} />;

  const list = (data ?? []).filter(
    (e) =>
      (filter === 'ALL' || e.status === filter) &&
      `${e.title} ${e.category}`.toLowerCase().includes(q.toLowerCase())
  );

  return (
    <Layout>
      <section className="hero">
        <div>
          <p className="eyebrow">FIND YOUR NEXT EXPERIENCE</p>
          <h1>
            Events worth
            <br />
            showing up for.
          </h1>
          <p>Discover thoughtfully curated events, workshops and meetups around you.</p>
        </div>
        <div className="hero-stat">
          <b>{data?.length}</b>
          <span>events to explore</span>
        </div>
      </section>

      <section className="toolbar">
        <label>
          <Search size={18} />
          <input
            placeholder="Search events"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </label>
        <select value={filter} onChange={(e) => setFilter(e.target.value)}>
          <option value="ALL">All statuses</option>
          <option value="PUBLISHED">Published</option>
          <option value="ONGOING">Ongoing</option>
          <option value="COMPLETED">Completed</option>
        </select>
      </section>

      <section>
        <div className="section-title">
          <h2>Explore events</h2>
          <span>{list.length} results</span>
        </div>
        {list.length ? (
          <div className="grid">
            {list.map((e) => (
              <EventCard key={e.id} event={e} />
            ))}
          </div>
        ) : (
          <State text="No events found." />
        )}
      </section>
    </Layout>
  );
}

function EventDetail() {
  const { id = '' } = useParams();
  const { user } = useAuth();
  const { data: event, loading, error, reload } = useAsync(() => eventService.getEvent(id), [id]);
  const { data: myRegs } = useAsync(
    () => (user ? registrationService.mine(user.id) : Promise.resolve([] as Registration[])),
    [user?.id]
  );
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const navigate = useNavigate();

  if (loading) return <Layout><State text="Loading event…"/></Layout>;
  if (error || !event) return <Layout><State text="Event not found."/></Layout>;

  const myReg = myRegs?.find(r => r.eventId === event.id);
  const full = event.registeredCount >= event.capacity;
  const isOpen = event.status === 'PUBLISHED';
  const disabled = busy || full || !isOpen || !!myReg;

  let label = 'Register now';
  if (full) label = 'Sold out';
  else if (myReg?.status === 'REGISTERED') label = 'Already registered';
  else if (myReg?.status === 'CANCELLED') label = 'Registration closed';
  else if (!isOpen) label = 'Registration unavailable';
  else if (busy) label = 'Registering…';

  const register = async () => {
    setBusy(true);
    try {
      const res = await registrationService.register(event.id, user!);
      navigate(`/tickets/${res.ticket.id}`);
    } catch (e) {
      setMessage((e as Error).message);
    } finally {
      setBusy(false);
      setConfirmOpen(false);
      void reload();
    }
  };

  const viewTicket = async () => {
    if (!myReg) return;
    const t = await ticketService.forRegistration(myReg.id);
    navigate(`/tickets/${t.id}`);
  };


  return (
    <Layout>
      <section className="detail">
        <img className="detail-image" src={event.bannerImage} alt="" />
        <div className="detail-info">
          {renderStatus(event.status)}
          <p className="eyebrow">{event.category.toUpperCase()}</p>
          <h1>{event.title}</h1>
          <p className="lead">{event.description}</p>
          <div className="facts">
            <p>
              <CalendarDays /> {formatDate(event.startTime)} — {formatDate(event.endTime)}
            </p>
            <p>
              <MapPin /> {event.location}
            </p>
            <p>
              <Users /> {event.capacity - event.registeredCount} seats remaining
            </p>
          </div>
          {message && <div className="notice error">{message}</div>}

          <button className="primary" disabled={disabled} onClick={() => setConfirmOpen(true)}>
            {label}
          </button>

          {myReg?.status === 'REGISTERED' && (
            <button className="secondary" style={{ marginLeft: 12 }} onClick={viewTicket}>
              View ticket
            </button>
          )}
        </div>
      </section>

      <ConfirmDialog
        open={confirmOpen}
        title="Confirm registration"
        message={`Register for "${event.title}"? A ticket will be issued immediately after confirming.`}
        confirmLabel="Register"
        busy={busy}
        onConfirm={register}
        onCancel={() => setConfirmOpen(false)}
      />
    </Layout>
  );
}

function Registrations() {
  const { user } = useAuth();
  const { data: regs, loading, reload } = useAsync(() => registrationService.mine(user!.id), [user?.id]);
  const { data: events } = useAsync(eventService.getEvents, []);
  const [msg, setMsg] = useState('');
  const [cancelTarget, setCancelTarget] = useState<{ id: string; title: string } | null>(null);
  const [busyCancel, setBusyCancel] = useState(false);
  const nav = useNavigate();  

  if (loading) return <Layout><State text="Loading your registrations…" /></Layout>;

  const doCancel = async () => {
    if (!cancelTarget) return;
    setBusyCancel(true);
    try {
      await registrationService.cancel(cancelTarget.id);
      setMsg('Registration cancelled and ticket invalidated.');
      void reload();
    } finally {
      setBusyCancel(false);
      setCancelTarget(null);
    }
  };


  return (
    <Layout>
      <section className="page-head">
        <p className="eyebrow">YOUR EVENTS</p>
        <h1>My registrations</h1>
      </section>
      {msg && <div className="notice success">{msg}</div>}
      <div className="list">
        {regs?.length ? (
          regs.map((r) => {
            const e = events?.find((x) => x.id === r.eventId);
            return (
              <div className="registration" key={r.id}>
                <div>
                  {renderStatus(r.status)}
                  <h3>{e?.title}</h3>
                  <p>
                    {e && formatDate(e.startTime)} · {e?.location}
                  </p>
                </div>
                <div>
                  {r.status === 'REGISTERED' && (
                    <>
                      <button
                        className="secondary"
                        onClick={async () => {
                          const t = await ticketService.forRegistration(r.id);
                          nav(`/tickets/${t.id}`);
                        }}
                      >
                        View ticket
                      </button>
                      <button
                        className="text-button"
                        onClick={() => setCancelTarget({ id: r.id, title: e?.title ?? 'this event' })}
                      >
                        Cancel
                      </button>
                    </>
                  )}
                </div>
              </div>
            );
          })
        ) : (
          <State text="You have no registrations yet." />
        )}
      </div>

      <ConfirmDialog
        open={!!cancelTarget}
        title="Cancel registration"
        message={`Cancel your registration for "${cancelTarget?.title}"? Your ticket will be invalidated immediately.`}
        confirmLabel="Cancel registration"
        busy={busyCancel}
        onConfirm={doCancel}
        onCancel={() => setCancelTarget(null)}
      />
    </Layout>
  );
}

function TicketPage() {
  const { id = '' } = useParams();
  const { data: ticket, loading, error } = useAsync(() => ticketService.get(id), [id]);
  const { data: allEvents } = useAsync(eventService.getEvents, []);
  const { user } = useAuth();
  const { data: registration } = useAsync(async () => {
    const t = await ticketService.get(id);
    return registrationService.get(t.registrationId);
  }, [id]);

  if (loading) return <Layout><State text="Loading ticket…" /></Layout>;
  if (error || !ticket) return <Layout><State text="Ticket not found." /></Layout>;

  const event = allEvents?.find((e) => e.id === registration?.eventId);

  return (
    <Layout>
      <section className="ticket-wrap">
        <p className="eyebrow">YOUR EVENT PASS</p>
        <div className="ticket">
          <div className="ticket-main">
            <span className="ticket-brand">evently</span>
            <h1>{event?.title ?? 'Your event ticket'}</h1>
            <p>{event && formatDate(event.startTime)}</p>
            <p>{event?.location}</p>
            <hr />
            <span>ATTENDEE</span>
            <h3>{user?.name}</h3>
            <span>TICKET CODE</span>
            <h2>{ticket.ticketCode}</h2>
          </div>
          <div className="ticket-qr">
            <div className="qr">
              ▦<br />
              ▧▦
              <br />
              ▦▧
            </div>
            {renderStatus(ticket.status)}
            <small>Present this code at check-in</small>
          </div>
        </div>
      </section>
    </Layout>
  );
}

function StaffCheckin() {
  const { user } = useAuth();
  const [code, setCode] = useState('');
  const [result, setResult] = useState('');
  const [error, setError] = useState('');

  const check = async () => {
    setResult('');
    setError('');
    try {
      const c = await checkinService.checkin(code, user!);
      setResult(`Check-in successful · ${formatDate(c.checkedInAt)}`);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <Layout>
      <section className="page-head">
        <p className="eyebrow">STAFF CONSOLE</p>
        <h1>Check in an attendee</h1>
        <p>Enter a ticket code or scan the attendee’s QR code.</p>
      </section>
      <div className="checkin">
        <div className="scanner">
          ⌁<b>Camera scanner</b>
          <span>Scanner preview placeholder</span>
        </div>
        <div className="checkin-form">
          <label>
            Ticket code
            <input
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="e.g. AI-MEET-2026"
            />
          </label>
          <button className="primary" onClick={check}>
            Validate & check in
          </button>
          <button className="secondary" onClick={() => setCode('AI-MEET-2026')}>
            Use demo valid code
          </button>
          {result && (
            <div className="notice success">
              <CheckCircle2 /> {result}
            </div>
          )}
          {error && <div className="notice error">{error}</div>}
        </div>
      </div>
    </Layout>
  );
}

function Organizer() {
  const { data, loading } = useAsync(organizerService.dashboard, []);

  if (loading) return <Layout><State text="Loading dashboard…" /></Layout>;

  const d = data!;

  return (
    <Layout>
      <section className="page-head">
        <p className="eyebrow">ORGANIZER OVERVIEW</p>
        <h1>Good morning, Evently Team.</h1>
      </section>
      <div className="metrics">
        <Metric label="Total events" value={d.events.length} />
        <Metric label="Published" value={d.events.filter((e) => e.status === 'PUBLISHED').length} />
        <Metric label="Registrations" value={d.total_registrations} />
        <Metric label="Check-ins" value={d.total_checkins} />
      </div>
      <section>
        <div className="section-title">
          <h2>Your events</h2>
          <Link to="/organizer/create">+ Create event</Link>
        </div>
        <div className="table">
          {d.events.map((e) => (
            <div key={e.id}>
              <b>{e.title}</b>
              <span>{formatDate(e.startTime)}</span>
              <span>
                {e.registeredCount}/{e.capacity}
              </span>
              {renderStatus(e.status)}
              <Link to={`/organizer/events/${e.id}`}>Manage</Link>
            </div>
          ))}
        </div>
      </section>
    </Layout>
  );
}

function CreateEvent() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    title: '',
    description: '',
    location: '',
    startTime: '2026-10-30T09:00',
    endTime: '2026-10-30T17:00',
    capacity: '100',
    category: 'Technology',
    bannerImage:
      'https://images.unsplash.com/photo-1505373877841-8d25f7d46678?auto=format&fit=crop&w=1200&q=80',
  });
  const [error, setError] = useState('');

  const create = async (e: React.FormEvent) => {
    e.preventDefault();
    if (
      !form.title ||
      !form.description ||
      new Date(form.startTime) >= new Date(form.endTime) ||
      Number(form.capacity) < 1
    ) {
      setError('Please complete required fields and use a valid date range.');
      return;
    }

    const event = await eventService.create(
      {
        ...form,
        capacity: Number(form.capacity),
        startTime: new Date(form.startTime).toISOString(),
        endTime: new Date(form.endTime).toISOString(),
      },
      user!
    );
    navigate(`/organizer/events/${event.id}`);
  };



  return (
    <Layout>
      <section className="page-head">
        <p className="eyebrow">NEW EVENT</p>
        <h1>Create an event</h1>
      </section>
      <form className="form" onSubmit={create}>
        {Object.entries(form).map(([key, value]) => (
          <label key={key}>
            {key.replace(/([A-Z])/g, ' $1')}
            <input
              required={key === 'title' || key === 'description'}
              type={
                key.includes('Time')
                  ? 'datetime-local'
                  : key === 'capacity'
                  ? 'number'
                  : 'text'
              }
              value={value}
              onChange={(e) => setForm({ ...form, [key]: e.target.value })}
            />
          </label>
        ))}
        {error && <div className="notice error">{error}</div>}
        <button className="primary">Create draft event</button>
      </form>

      <p className="hint">After creating, you'll land on the event's management page where you can publish it and assign staff.</p>
    </Layout>
  );
}

function StaffAssignment({ eventId }: { eventId: string }) {
  const { data: allStaff } = useAsync(staffService.listStaff, [])
  const { data: assigned, loading, reload } = useAsync(() => staffService.assignedTo(eventId), [eventId])
  const [staffId, setStaffId] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const assign = async () => {
    if (!staffId) return
    setBusy(true); setError('')
    try { await staffService.assign(eventId, staffId); setStaffId(''); void reload() }
    catch (e) { setError((e as Error).message) }
    finally { setBusy(false) }
  }

  const assignedIds = new Set((assigned ?? []).map(a => a.staffId))
  const available = (allStaff ?? []).filter(s => !assignedIds.has(s.id))

  return <section className="actions">
    <h2>Assign staff</h2>
    <div className="toolbar" style={{ marginBottom: 14 }}>
      <select value={staffId} onChange={e => setStaffId(e.target.value)}>
        <option value="">Select a staff account…</option>
        {available.map(s => <option key={s.id} value={s.id}>{s.name} — {s.email}</option>)}
      </select>
      <button className="secondary" disabled={busy || !staffId} onClick={assign}>{busy ? 'Assigning…' : 'Assign staff'}</button>
    </div>
    {error && <div className="notice error">{error}</div>}
    {loading ? <State text="Loading assigned staff…" /> : assigned?.length ? (
      <ul style={{ margin: 0, paddingLeft: 18, color: '#3d4944' }}>
        {assigned.map(a => <li key={a.id}>{a.staffName} — {a.staffEmail}</li>)}
      </ul>
    ) : <p style={{ color: '#68716d', fontSize: 13 }}>No staff assigned yet.</p>}
  </section>
}

function ManageEvent() {
  const { id = '' } = useParams();
  const { data: event, loading, reload } = useAsync(() => eventService.getEvent(id), [id]);
  const [error, setError] = useState('');

  if (loading) return <Layout><State text="Loading event…" /></Layout>;
  if (!event) return <Layout><State text="Event not found." /></Layout>;

  const transitionState = async (s: EventStatus) => {
    try {
      await eventService.transition(id, s);
      void reload();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <Layout>
      <section className="page-head">
        <p className="eyebrow">EVENT MANAGEMENT</p>
        <h1>{event.title}</h1>
        {renderStatus(event.status)}
      </section>

      <div className="metrics">
        <Metric label="Capacity" value={event.capacity} />
        <Metric label="Registered" value={event.registeredCount} />
        <Metric label="Remaining" value={event.capacity - event.registeredCount} />
        <Metric label="Check-in rate" value="—" />
      </div>

      {error && <div className="notice error">{error}</div>}

      <section className="actions">
        <h2>Lifecycle</h2>
        {event.status === 'DRAFT' && (
          <button className="primary" onClick={() => transitionState('PUBLISHED')}>
            Publish event
          </button>
        )}
        {event.status === 'PUBLISHED' && (
          <button className="primary" onClick={() => transitionState('ONGOING')}>
            Start event
          </button>
        )}
        {event.status === 'ONGOING' && (
          <button className="primary" onClick={() => transitionState('COMPLETED')}>
            Mark completed
          </button>
        )}
        {['DRAFT', 'PUBLISHED'].includes(event.status) && (
          <button className="text-button" onClick={() => transitionState('CANCELLED')}>
            Cancel event
          </button>
        )}
      </section>
      <StaffAssignment eventId={event.id}/>
    </Layout>
  );
}

function Login() {
  const { login, user } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('attendee@demo.com');
  const [password, setPassword] = useState('123456');
  const [error, setError] = useState('');

  if(user)return <Navigate to={homePath(user.role)}/>;

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const u = await login(email, password);
      navigate(homePath(u.role));
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <div className="login">
      <div className="login-copy">
        <Link className="brand" to="/login">
          <span>e</span>evently
        </Link>
        <h1>
          Where people
          <br />
          meet possibilities.
        </h1>
        <p>One place to discover, manage, and experience memorable events.</p>
      </div>

      <form onSubmit={submit}>
        <p className="eyebrow">WELCOME BACK</p>
        <h2>Sign in to Evently</h2>
        <label>
          Email
          <input value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        {error && <div className="notice error">{error}</div>}
        <button className="primary">Sign in</button>
        <p className="hint">
          Demo: attendee@demo.com · staff@demo.com · organizer@demo.com
          <br />
          Password: 123456
        </p>
      </form>
    </div>
  );
}

// Main Router App
export function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<Home/>}/>
      <Route path="/events" element={<RoleGate roles={['ATTENDEE']}><EventsPage/></RoleGate>}/>
      <Route path="/events/:id" element={<RoleGate roles={['ATTENDEE']}><EventDetail/></RoleGate>}/>
      <Route
        path="/registrations"
        element={
          <RoleGate roles={['ATTENDEE']}>
            <Registrations />
          </RoleGate>
        }
      />
      <Route
        path="/tickets/:id"
        element={
          <RoleGate roles={['ATTENDEE']}>
            <TicketPage />
          </RoleGate>
        }
      />
      <Route
        path="/staff"
        element={
          <RoleGate roles={['STAFF']}>
            <StaffCheckin />
          </RoleGate>
        }
      />
      <Route
        path="/staff/check-in"
        element={
          <RoleGate roles={['STAFF']}>
            <StaffCheckin />
          </RoleGate>
        }
      />
      <Route
        path="/staff/attendees"
        element={
          <RoleGate roles={['STAFF']}>
            <StaffCheckin />
          </RoleGate>
        }
      />
      <Route
        path="/organizer"
        element={
          <RoleGate roles={['ORGANIZER']}>
            <Organizer />
          </RoleGate>
        }
      />
      <Route
        path="/organizer/events"
        element={
          <RoleGate roles={['ORGANIZER']}>
            <Organizer />
          </RoleGate>
        }
      />
      <Route
        path="/organizer/create"
        element={
          <RoleGate roles={['ORGANIZER']}>
            <CreateEvent />
          </RoleGate>
        }
      />
      <Route
        path="/organizer/events/:id"
        element={
          <RoleGate roles={['ORGANIZER']}>
            <ManageEvent />
          </RoleGate>
        }
      />
      <Route path="*" element={<Home/>}/>
    </Routes>
  );
}