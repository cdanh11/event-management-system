import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import ts from 'typescript';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../src');
process.env.TZ = 'Asia/Ho_Chi_Minh';

// Load actual TypeScript modules in isolated browser-like environments.
// No generated sources or additional testing dependencies are needed.
function load(relative, overrides = {}) {
  const cache = new Map();
  const storage = () => {
    const values = new Map();
    return { getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value), removeItem: key => values.delete(key) };
  };
  const context = vm.createContext({
    Date, Intl, URLSearchParams, Headers, AbortController, DOMException, Event,
    localStorage: storage(), sessionStorage: storage(),
    window: { dispatchEvent() {} },
    setTimeout, clearTimeout, setInterval, clearInterval,
    ...overrides,
  });
  function moduleAt(file) {
    if (cache.has(file)) return cache.get(file).exports;
    const source = fs.readFileSync(file, 'utf8').replace('import.meta.env.VITE_API_BASE_URL', "'http://localhost:8000'");
    const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
    const module = { exports: {} };
    cache.set(file, module);
    const run = vm.runInContext(`(function(require,module,exports){${code}\n})`, context, { filename: file });
    run(specifier => moduleAt(path.resolve(path.dirname(file), `${specifier}.ts`)), module, module.exports);
    return module.exports;
  }
  return moduleAt(path.resolve(root, relative));
}

function response(status, body) { return { status, ok: status < 400, json: async () => body }; }
const nextTick = () => new Promise(resolve => setTimeout(resolve, 0));

test('shared event range distinguishes same day, multiple days and a different year', () => {
  const { formatWhen } = load('lib/datetime.ts');
  const now = new Date('2026-10-07T09:00:00+07:00');
  assert.equal(formatWhen('2026-11-14T09:00:00+07:00','2026-11-14T12:00:00+07:00',now),'Sat, Nov 14, 9:00 AM to 12:00 PM');
  assert.equal(formatWhen('2026-11-14T09:00:00+07:00','2026-11-16T12:00:00+07:00',now),'Sat, Nov 14, 9:00 AM to Mon, Nov 16, 12:00 PM');
  assert.match(formatWhen('2027-01-01T09:00:00+07:00','2027-01-01T12:00:00+07:00',now),/2027/);
});

test('door copy respects server status even when check-in is opened early; organizer ordering keeps past events below active ones', () => {
  const { doorDescription, compareOrganizerEvents } = load('lib/status.ts');
  const now = +new Date('2026-10-07T09:00:00+07:00');
  const make = (id,status,day) => ({id,status,startTime:`2026-10-${day}T10:00:00+07:00`,endTime:`2026-10-${day}T12:00:00+07:00`});
  assert.match(doorDescription(make('early','STARTED','20'),now),/is open until/);
  assert.doesNotMatch(doorDescription(make('early','STARTED','20'),now),/Starts in/);
  assert.match(doorDescription(make('waiting','ONGOING','07'),now),/opens in/);
  const events=[make('draft','DRAFT','07'),make('old','COMPLETED','01'),make('upcoming','PUBLISHED','20'),make('recent','COMPLETED','06'),make('door','STARTED','07')];
  assert.equal(events.sort(compareOrganizerEvents).map(e=>e.id).join(','),'door,upcoming,recent,old,draft');
});

test('event forms validate real submission time, integer capacity, invalid dates and API field names', () => {
  const form = load('features/organizer/eventForm.ts');
  const now = +new Date('2026-10-06T09:00:00');
  const value = { title:'Event',description:'Description',location:'Hồ Chí Minh',capacity:'100',category:'Technology',bannerImage:'',startTime:'2026-10-07T09:00',endTime:'2026-10-07T12:00' };
  assert.ok(Object.values(form.eventFormErrors(value,now)).every(error => !error));
  assert.equal(form.durationLabel(value),'3h 00m');
  assert.ok(form.eventFormErrors({...value,capacity:'1.5'},now).capacity);
  assert.ok(form.eventFormErrors({...value,title:'x'.repeat(201)},now).title);
  assert.ok(form.scheduleErrors({...value,startTime:''},now).startTime);
  assert.ok(form.scheduleErrors({...value,startTime:'invalid'},now).startTime);
  assert.ok(form.scheduleErrors({...value,endTime:value.startTime},now).endTime);
  assert.ok(form.scheduleErrors(value,+new Date(value.startTime)).startTime);
  assert.ok(form.eventFormErrors({...value,bannerImage:'javascript:alert(1)'},now).bannerImage);
  assert.equal(form.eventServerErrors({details:[{loc:['body','start_time'],msg:'Start error'}]}).startTime,'Start error');
  assert.equal(form.eventServerErrors({details:[{loc:['body'],msg:'Time order error'}]}).endTime,'Time order error');
});

test('remembered routes are scoped to the role that actually signed in', () => {
  const { postLoginPath } = load('lib/navigation.ts');
  assert.equal(postLoginPath('STAFF', '/registrations'), '/staff');
  assert.equal(postLoginPath('ORGANIZER', '/staff'), '/organizer');
  assert.equal(postLoginPath('ATTENDEE', '/organizer/live'), '/events');
  assert.equal(postLoginPath('ATTENDEE', '//external.example'), '/events');
  assert.equal(postLoginPath('ORGANIZER', '/events/event-id'), '/events/event-id');
  assert.equal(postLoginPath('ORGANIZER', '/organizer/events?q=workshop'), '/organizer/events?q=workshop');
});

test('overview reports concurrent reasons and checks staff for at most five active events', () => {
  const { attentionReasons, upcomingStaffChecks, priorityEvent } = load('features/events/organizer.ts');
  const now = Date.now();
  const make = (id, status = 'PUBLISHED', minutes = 30) => ({ id, status, startTime: new Date(now + minutes * 60000).toISOString(), endTime: new Date(now + (minutes + 180) * 60000).toISOString(), capacity: 100, registeredCount: 90 });
  assert.equal(attentionReasons(make('soon'), now, 0).length, 3);
  assert.equal(attentionReasons(make('terminal', 'COMPLETED'), now, 0).length, 0);
  assert.ok(attentionReasons(make('past', 'PUBLISHED', -1), now).some(reason => reason.includes('Past')));
  const events = [make('old', 'COMPLETED', -1000), ...Array.from({ length: 7 }, (_, i) => make(String(i), 'PUBLISHED', i + 1)), make('door', 'STARTED', -10)];
  assert.equal(upcomingStaffChecks(events, now).length, 5);
  assert.equal(priorityEvent(events, now).id, 'door');
});

test('event wall-clock and UTC check-in timestamps remain distinct; form round-trip stays 09:00', () => {
  const dates = load('lib/datetime.ts');
  const event = dates.parseEventDate('2026-10-23T09:00:00');
  assert.equal(event.getHours(), 9);
  assert.equal(dates.parseApiDate('2026-10-23T02:00:00').getHours(), 9);
  assert.equal(dates.toInputValue(event.toISOString()), '2026-10-23T09:00');
  assert.equal(dates.toEventPayloadDate(dates.fromInputValue('2026-10-23T09:00')), '2026-10-23T09:00');
  assert.equal(dates.parseApiDate('2026-10-23T09:00:00+07:00').toISOString(), '2026-10-23T02:00:00.000Z');
});

test('two simultaneous 401s share one refresh rotation', async () => {
  let rotations = 0;
  const api = load('api/apiClient.ts', { fetch: async (url, options) => {
    if (url.endsWith('/auth/refresh')) { rotations++; await nextTick(); return response(200, { access_token: 'new' }); }
    return options.headers.get('Authorization') === 'Bearer new' ? response(200, { success: true }) : response(401, { code: 'UNAUTHORIZED' });
  } });
  api.setAccessToken('old');
  const results = await Promise.all([api.request('/first'), api.request('/second')]);
  assert.equal(rotations, 1);
  assert.ok(results.every(result => result.success));
});

test('a delayed old-token 401 reuses the new token without another rotation', async () => {
  let rotations = 0;
  let release;
  const slow = new Promise(resolve => { release = resolve; });
  const api = load('api/apiClient.ts', { fetch: async (url, options) => {
    if (url.endsWith('/auth/refresh')) { rotations++; return response(200, { access_token: 'new' }); }
    if (options.headers.get('Authorization') === 'Bearer new') return response(200, {});
    if (url.endsWith('/slow')) await slow;
    return response(401, {});
  } });
  api.setAccessToken('old');
  const pending = api.request('/slow');
  await api.request('/fast');
  release();
  await pending;
  assert.equal(rotations, 1);
});

test('invalid credentials do not rotate a refresh cookie; validation details survive', async () => {
  const urls = [];
  const api = load('api/apiClient.ts', { fetch: async url => {
    urls.push(url);
    return response(401, { code: 'INVALID_CREDENTIALS', message: 'Wrong password', details: [{ loc: ['body', 'password'], msg: 'Invalid' }] });
  } });
  await assert.rejects(api.request('/auth/login'), error => error.code === 'INVALID_CREDENTIALS' && error.details[0].loc[1] === 'password');
  assert.equal(urls.length, 1);
});

test('refresh failure clears auth and broadcasts session end', async () => {
  let ended = 0;
  const api = load('api/apiClient.ts', { fetch: async () => response(401, { code: 'UNAUTHORIZED' }), window: { dispatchEvent: () => ended++ } });
  api.setAccessToken('old');
  await assert.rejects(api.request('/protected'));
  assert.equal(api.getAccessToken(), undefined);
  assert.equal(ended, 1);
});

test('event pagination sends search, status and last-row cursor without offset', async () => {
  const urls = [];
  const services = load('services/services.ts', { fetch: async url => {
    urls.push(url);
    return response(200, [{ id: 'last-row', start_time: '2026-10-23T09:00:00', end_time: '2026-10-23T11:00:00' }]);
  } });
  const page = await services.eventService.list({ q: 'Design', status: 'PUBLISHED', limit: 1, cursor: 'previous' });
  assert.equal(page.nextCursor, 'last-row');
  assert.match(urls[0], /q=Design/);
  assert.match(urls[0], /status=PUBLISHED/);
  assert.match(urls[0], /cursor=previous/);
  assert.doesNotMatch(urls[0], /offset/);
  assert.equal(new Date(page.items[0].startTime).getHours(), 9);
});

test('door rights and transitions follow local STARTED contract', () => {
  const status = load('lib/status.ts');
  assert.equal(status.canCheckin('STAFF', 'ONGOING'), false);
  assert.equal(status.canCheckin('ORGANIZER', 'STARTED'), true);
  assert.equal(status.canReschedule('ONGOING'), false);
  assert.ok(status.nextActions('PUBLISHED').includes('STARTED'));
  assert.equal(status.preferredLiveEvent([{ id: 'old', status: 'COMPLETED', startTime: '2020-01-01Z' }, { id: 'live', status: 'STARTED', startTime: '2026-10-06Z' }]).id, 'live');
});

test('first socket subscriber connects, idle connection stays open, final unsubscribe closes it', async () => {
  const sockets = [];
  let heartbeat;
  class FakeSocket {
    static OPEN = 1;
    readyState = 0;
    closed = false;
    sent = [];
    constructor(url) { this.url = url; sockets.push(this); }
    send(value) { this.sent.push(value); }
    close() { this.closed = true; this.onclose?.({ code: 1000 }); }
  }
  const { socketManager } = load('realtime/socket.ts', {
    fetch: async () => response(200, { ticket: 'single-use' }),
    WebSocket: FakeSocket,
    setInterval: fn => { heartbeat = fn; return 1; }, clearInterval() {},
  });
  const messages = [];
  const stop = socketManager.subscribe('event-one', frame => messages.push(frame));
  await nextTick();
  assert.equal(sockets.length, 1);
  const socket = sockets[0];
  socket.readyState = FakeSocket.OPEN;
  socket.onopen();
  socket.onmessage({ data: JSON.stringify({ event_id: 'event-one', status: 'PUBLISHED', registered_count: 1, capacity: 10, remaining: 9 }) });
  socket.onmessage({ data: JSON.stringify({ event_id: 'another-event', status: 'PUBLISHED', registered_count: 8, capacity: 10, remaining: 2 }) });
  socket.onmessage({ data: JSON.stringify({ event_id: 'event-one', status: 'UNKNOWN', registered_count: 8, capacity: 10, remaining: 2 }) });
  heartbeat();
  assert.equal(socket.closed, false);
  assert.deepEqual(socket.sent, ['ping']);
  assert.equal(messages.length, 1);
  stop();
  assert.equal(socket.closed, true);
});

test('socket reconnect mints new tickets, backs off, pauses and can retry', async () => {
  const sockets = [];
  const scheduled = [];
  const states = [];
  let tickets = 0;
  class FakeSocket {
    static OPEN = 1;
    constructor(url) { this.url = url; sockets.push(this); }
    close() {}
  }
  const { socketManager } = load('realtime/socket.ts', {
    fetch: async () => response(200, { ticket: `ticket-${++tickets}` }),
    WebSocket: FakeSocket,
    setInterval: () => 1, clearInterval() {}, clearTimeout() {},
    setTimeout: (callback, delay) => { scheduled.push({ callback, delay }); return scheduled.length; },
  });
  const stop = socketManager.subscribe('event', () => {}, { onState: state => states.push(state) });
  await nextTick();
  for (let attempt = 0; attempt < 5; attempt++) {
    sockets.at(-1).onclose({ code: 1006 });
    const task = scheduled.shift();
    assert.ok(task);
    assert.ok(task.delay >= [1000, 2000, 4000, 8000, 15000][attempt] * .8);
    task.callback();
    await nextTick();
  }
  sockets.at(-1).onclose({ code: 1006 });
  assert.equal(states.at(-1), 'closed');
  assert.equal(scheduled.length, 0);
  assert.equal(tickets, 6);
  assert.equal(new Set(sockets.map(socket => socket.url)).size, 6);
  socketManager.retry('event');
  await nextTick();
  assert.equal(tickets, 7);
  assert.equal(states.at(-1), 'connecting');
  stop();
});

test('agenda search uses server filters and independent cursors for both active statuses', async () => {
  const calls = [];
  const { loadAgenda } = load('features/events/agenda.ts', { fetch: async url => {
    const params = new URL(url).searchParams;
    calls.push(params);
    const status = params.get('status');
    const second = params.has('cursor');
    return response(200, Array.from({ length: second ? 1 : 20 }, (_, i) => ({
      id: `${status}-${second ? 20 : i}`, organizer_id: 'owner', status, title: 'Meetup',
      start_time: '2026-10-23T09:00:00', end_time: '2026-10-23T12:00:00', capacity: 50, registered_count: 10,
    })));
  }, URL });
  const page = await loadAgenda('happening', 'Meetup', 2, new AbortController().signal);
  assert.equal(page.items.length, 42);
  assert.equal(page.hasMore, false);
  assert.equal(calls.length, 4);
  assert.ok(calls.every(params => params.get('q') === 'Meetup' && !params.has('offset')));
  assert.deepEqual(calls.filter(params => params.has('cursor')).map(params => params.get('cursor')).sort(), ['ONGOING-19', 'STARTED-19']);
});

test('agenda hides expired registration and detail keeps existing tickets after completion', () => {
  const { visibleAgenda } = load('features/events/agenda.ts');
  const { registrationAction } = load('lib/status.ts');
  const now = +new Date('2026-10-06T09:00:00Z');
  const event = { id: 'event', status: 'PUBLISHED', startTime: '2026-10-06T08:00:00Z', capacity: 10, registeredCount: 10 };
  assert.equal(visibleAgenda([event], 'open', now).length, 0);
  assert.equal(registrationAction(event, 'ATTENDEE', undefined, now), 'closed');
  assert.equal(registrationAction({ ...event, status: 'COMPLETED' }, 'ATTENDEE', { status: 'REGISTERED' }, now), 'ticket');
  assert.equal(registrationAction({ ...event, startTime: '2026-11-01T09:00:00Z' }, 'ATTENDEE', { status: 'CANCELLED' }, now), 'registration-cancelled');
  assert.equal(registrationAction({ ...event, status: 'CANCELLED' }, undefined, undefined, now), 'event-cancelled');
});

test('door normalizes scanner input and classifies errors by code, independently of backend wording', () => {
  const scan = load('features/door/scan.ts');
  assert.equal(scan.normalizeTicketCode(' ev- ab12 \n'), 'EV-AB12');
  for (const [code, title, tone] of [
    ['TICKET_ALREADY_USED', 'Already scanned', 'warning'],
    ['INVALID_TICKET', 'Not found', 'error'],
    ['TICKET_CANCELLED', 'Ticket cancelled', 'error'],
    ['CHECKIN_CLOSED', 'Check-in closed', 'error'],
    ['FORBIDDEN', 'Access denied', 'error'],
  ]) {
    const result = scan.scanFailure({ code, message: 'Completely different wording' });
    assert.equal(result.title, title);
    assert.equal(result.tone, tone);
    assert.notEqual(result.detail, 'Completely different wording');
  }
});

test('live session stores exact deltas, ignores duplicate snapshots and resets for another room', () => {
  const live = load('features/live/session.ts');
  const frame = { event_id: 'room-one', registered_count: 63, capacity: 80, remaining: 17, status: 'STARTED' };
  let session = live.acceptOccupancy(live.emptyLiveSession('room-one'), frame, '2026-10-06T12:00:00Z');
  assert.equal(session.changes.length, 0);
  const baseline = session;
  session = live.acceptOccupancy(session, frame, '2026-10-06T12:00:01Z');
  assert.equal(session, baseline);
  session = live.acceptOccupancy(session, {...frame,registered_count:66}, '2026-10-06T12:00:02Z');
  assert.equal(session.changes[0].delta, 3);
  session = live.acceptOccupancy(session, {...frame,registered_count:64}, '2026-10-06T12:00:03Z');
  assert.equal(session.changes[0].delta, -2);
  assert.equal(session.previous, 64);
  const another = live.acceptOccupancy(session, {...frame,event_id:'room-two',registered_count:10}, '2026-10-06T12:00:04Z');
  assert.equal(another.changes.length, 0);
  assert.equal(another.previous, 10);
  for (let n = 0; n < 100; n++) session = live.acceptOccupancy(session, {...frame,registered_count:n}, `tick-${n}`);
  assert.equal(session.previous, 99);
  assert.equal(session.changes.length, 20);
});

test('precise Live update ages advance in seconds while normal relative dates remain calm', () => {
  const dates = load('lib/datetime.ts');
  const at = '2026-10-06T12:00:00Z';
  assert.equal(dates.formatRelative(at, +new Date(at)+3000, true), '3s ago');
  assert.equal(dates.formatRelative(at, +new Date(at)+3000), 'just now');
});
