import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';
import ts from 'typescript';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../src');
const tick = () => new Promise(resolve => setTimeout(resolve, 0));

// Run the actual component handlers with deterministic hook state and API doubles.
// DOM focus/layout remain browser checks; no destructive request is sent here.
function component(relative, modules) {
  const cache = new Map(), states = [], refs = [];
  let stateIndex = 0, refIndex = 0;
  const jsx = (type, props) => ({ type, props });
  const react = {
    useState(initial) { const index = stateIndex++; if (!(index in states)) states[index] = typeof initial === 'function' ? initial() : initial;
      return [states[index], value => { states[index] = typeof value === 'function' ? value(states[index]) : value; }]; },
    useRef(initial) { const index = refIndex++; return refs[index] ??= { current: initial }; },
    useMemo(fn) { return fn(); },
  };
  const context = vm.createContext({ Date, Intl, Map, Set, URL, URLSearchParams, TypeError, Error, console });
  function load(file) {
    const key = path.relative(root, file).replaceAll('\\', '/');
    if (modules[key]) return modules[key];
    if (key.startsWith('components/')) return new Proxy({}, { get: (_, name) => name });
    if (cache.has(file)) return cache.get(file).exports;
    const source = fs.readFileSync(file, 'utf8');
    const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX } }).outputText;
    const module = { exports: {} }; cache.set(file, module);
    const run = vm.runInContext(`(function(require,module,exports){${code}\n})`, context, { filename: file });
    run(specifier => {
      if (specifier === 'react') return react;
      if (specifier === 'react/jsx-runtime') return { jsx, jsxs: jsx, Fragment: 'Fragment' };
      if (specifier === 'react-router-dom') return modules.router;
      const target = path.resolve(path.dirname(file), specifier);
      return load([target + '.ts', target + '.tsx'].find(candidate => fs.existsSync(candidate)) ?? target + '.ts');
    }, module, module.exports);
    return module.exports;
  }
  const exported = load(path.resolve(root, relative));
  return (name, props = {}) => { stateIndex = 0; refIndex = 0; modules.beforeRender?.(); return exported[name](props); };
}

function elements(node, type) {
  if (!node || typeof node !== 'object') return [];
  if (Array.isArray(node)) return node.flatMap(child => elements(child, type));
  return [...(node.type === type ? [node] : []), ...elements(node.props?.children, type)];
}
const button = (tree, label) => elements(tree, 'Button').find(node => node.props.children === label);

test('Delete draft failure keeps confirmation and event; retry navigates only after success', async () => {
  let fails = true, calls = 0;
  const navigation = [], notices = [];
  const render = component('features/organizer/ManageActions.tsx', {
    router: { useNavigate: () => value => navigation.push(value) },
    'components/ui/Toast.tsx': { useToast: () => ({ toast: value => notices.push(value) }) },
    'services/services.ts': { eventService: { remove: async id => { assert.equal(id, 'draft'); calls++; if (fails) throw { code: 'FORBIDDEN' }; } } },
  });
  const props = { event: { id: 'draft', status: 'DRAFT', registeredCount: 0 }, onChanged() {} };
  let tree = render('ManageActions', props);
  button(tree, 'Delete draft').props.onClick();
  tree = render('ManageActions', props);
  elements(tree, 'ConfirmDialog')[0].props.onConfirm(); await tick();
  tree = render('ManageActions', props);
  const dialog = elements(tree, 'ConfirmDialog')[0];
  assert.equal(dialog.props.open, true); assert.equal(dialog.props.busy, false);
  assert.match(dialog.props.error, /access/); assert.deepEqual(navigation, []); assert.deepEqual(notices, []);
  fails = false; dialog.props.onConfirm(); await tick();
  assert.equal(elements(render('ManageActions', props), 'ConfirmDialog')[0].props.open, false);
  assert.equal(calls, 2); assert.deepEqual(navigation, ['/organizer/events']); assert.deepEqual(notices, ['Draft deleted.']);
});

test('Cancellation failure remains retryable; success applies returned registration even if refetch gives no data', async () => {
  let fails = true;
  const reg = { id: 'reg', eventId: 'event', status: 'REGISTERED' };
  const query = { data: { regs: [reg], byEvent: new Map([['event', { title: 'Event', status: 'PUBLISHED', startTime: '2026-11-14T09:00:00+07:00', endTime: '2026-11-14T12:00:00+07:00' }]]), tickets: new Map([['reg', { status: 'VALID' }]]) },
    isLoading: false, refetch: async () => undefined, setData: data => { query.data = data; } };
  const render = component('pages/attendee/MyRegistrations.tsx', {
    router: { useNavigate: () => () => {} },
    'components/ui/Toast.tsx': { useToast: () => ({ toast() {} }) },
    'features/auth/useAuth.ts': { useAuth: () => ({ user: { id: 'attendee' } }) },
    'hooks/useQuery.ts': { useQuery: () => query },
    'services/services.ts': { registrationService: { cancel: async () => { if (fails) throw new TypeError('Failed to fetch'); return { ...reg, status: 'CANCELLED' }; } } },
  });
  button(render('MyRegistrations'), 'Cancel registration').props.onClick();
  elements(render('MyRegistrations'), 'ConfirmDialog')[0].props.onConfirm(); await tick();
  const dialog = elements(render('MyRegistrations'), 'ConfirmDialog')[0];
  assert.equal(dialog.props.open, true); assert.equal(dialog.props.busy, false); assert.match(dialog.props.error, /connect/);
  fails = false; dialog.props.onConfirm(); await tick();
  assert.equal(elements(render('MyRegistrations'), 'ConfirmDialog')[0].props.open, false);
  assert.equal(query.data.regs[0].status, 'CANCELLED'); assert.equal(query.data.tickets.get('reg').status, 'CANCELLED');
});

test('Cancellation opened before a lifecycle change is blocked by the current event state', async () => {
  let calls = 0;
  const event = { title: 'Event', status: 'PUBLISHED', startTime: '2026-11-14T09:00:00+07:00', endTime: '2026-11-14T12:00:00+07:00' };
  const query = { data: { regs: [{ id: 'reg', eventId: 'event', status: 'REGISTERED' }], byEvent: new Map([['event', event]]), tickets: new Map() }, isLoading: false };
  const render = component('pages/attendee/MyRegistrations.tsx', {
    router: { useNavigate: () => () => {} },
    'components/ui/Toast.tsx': { useToast: () => ({ toast() {} }) },
    'features/auth/useAuth.ts': { useAuth: () => ({ user: { id: 'attendee' } }) },
    'hooks/useQuery.ts': { useQuery: () => query },
    'services/services.ts': { registrationService: { cancel: async () => { calls++; } } },
  });
  button(render('MyRegistrations'), 'Cancel registration').props.onClick();
  event.status = 'STARTED';
  elements(render('MyRegistrations'), 'ConfirmDialog')[0].props.onConfirm(); await tick();
  assert.equal(calls, 0); assert.match(elements(render('MyRegistrations'), 'ConfirmDialog')[0].props.error, /Cancellation closed/);
});

test('Staff creation followed by assignment failure preserves the account for an Assign retry', async () => {
  let queryIndex = 0, creates = 0, assigns = 0;
  const account = { id: 'staff-new', name: 'Test Staff', email: 'test@example.com' };
  const assigned = { data: [], isLoading: false, refetch: async () => undefined };
  const accounts = { data: [], setData: data => { accounts.data = data; } };
  const render = component('features/organizer/StaffPanel.tsx', {
    beforeRender: () => { queryIndex = 0; },
    'hooks/useQuery.ts': { useQuery: () => queryIndex++ === 0 ? assigned : accounts },
    'components/ui/Toast.tsx': { useToast: () => ({ toast() {} }) },
    'services/services.ts': { staffService: { create: async () => { creates++; return account; }, assign: async (eventId, id) => {
      assert.equal(eventId, 'event'); assert.equal(id, account.id); assigns++; if (assigns === 1) throw new TypeError('Failed to fetch');
    } } },
  });
  const props = { eventId: 'event' };
  button(render('StaffPanel', props), 'New staff account').props.onClick();
  for (const [label, value] of [['Name', account.name], ['Email', account.email], ['Password', '123456']]) {
    const field = elements(render('StaffPanel', props), 'Field').find(node => node.props.label === label);
    field.props.children.props.onChange({ target: { value } });
  }
  elements(render('StaffPanel', props), 'form')[0].props.onSubmit({ preventDefault() {} }); await tick();
  let tree = render('StaffPanel', props);
  assert.equal(creates, 1); assert.equal(accounts.data.length, 1); assert.equal(elements(tree, 'form').length, 0);
  assert.match(elements(tree, 'p').find(node => node.props.role === 'alert').props.children, /created, but assignment failed/);
  assert.equal(elements(tree, 'Select')[0].props.value, account.id); assert.equal(button(tree, 'Assign').props.disabled, false);
  button(tree, 'Assign').props.onClick(); await tick(); tree = render('StaffPanel', props);
  assert.equal(creates, 1); assert.equal(assigns, 2); assert.equal(elements(tree, 'Select')[0].props.value, '');
});
