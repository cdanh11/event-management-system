import { useState, type FormEvent } from 'react';
import { useQuery } from '../../hooks/useQuery';
import { staffService } from '../../services/services';
import { Button } from '../../components/ui/Button';
import { Field, Input, Select } from '../../components/ui/forms';
import { ErrorBlock, Skeleton } from '../../components/ui/states';
import { useToast } from '../../components/ui/Toast';
import { friendlyError, fieldErrors } from '../../lib/errors';
import { strings } from '../../copy/strings';

export function StaffPanel({ eventId }: { eventId: string }) {
  const assigned = useQuery(signal => staffService.assignedTo(eventId,signal),[eventId],{refetchInterval:15_000});
  const accounts = useQuery(staffService.listStaff,[eventId]);
  const [selected, setSelected] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [values, setValues] = useState({name:'',email:'',password:''});
  const [touched, setTouched] = useState<Record<string, boolean>>({});
  const [serverErrors, setServerErrors] = useState<Record<string, string>>({});
  const { toast } = useToast();
  const copy = strings.manage;
  const ids = new Set(assigned.data?.map(person => person.staffId));
  const available = (accounts.data ?? []).filter(person => !ids.has(person.id));
  const choice = available.some(person => person.id === selected) ? selected : '';
  const errors = {
    name: !values.name.trim() ? strings.auth.nameRequired : values.name.trim().length > 120 ? strings.auth.nameLong : '',
    email: !/^\S+@\S+\.\S+$/.test(values.email.trim()) ? strings.auth.emailInvalid : '',
    password: values.password.length < 6 ? strings.auth.passwordShort : values.password.length > 128 ? strings.auth.passwordLong : '',
  };
  const show = (key: keyof typeof values) => serverErrors[key] || (touched[key] ? errors[key] : '');
  const change = (key: keyof typeof values, value: string) => { setValues(before => ({...before,[key]:value}));setServerErrors(before => ({...before,[key]:''}));setError(''); };
  const assign = async () => {
    if (!choice || busy) return;
    setBusy(true);setError('');
    try { await staffService.assign(eventId,choice);setSelected('');toast(copy.assignedToast,'success');void assigned.refetch(); }
    catch (err) { setError(friendlyError(err)); if ((err as {code?:string}).code === 'ALREADY_ASSIGNED') void assigned.refetch(); }
    finally { setBusy(false); }
  };
  const create = async (e: FormEvent) => {
    e.preventDefault();if (busy) return;
    setTouched({name:true,email:true,password:true});setError('');setServerErrors({});
    if (Object.values(errors).some(Boolean)) return;
    setBusy(true);
    try {
      const person = await staffService.create({name:values.name.trim(),email:values.email.trim(),password:values.password});
      // Creation and assignment are separate writes. Preserve the created account
      // if assignment fails so retrying cannot create a duplicate account.
      setValues({name:'',email:'',password:''});setTouched({});setShowCreate(false);setSelected(person.id);
      accounts.setData([...(accounts.data ?? []),person]);
      try { await staffService.assign(eventId,person.id);setSelected('');toast(copy.staffCreatedAssigned,'success');void assigned.refetch(); }
      catch (err) { setError(copy.staffAssignFailed+' '+friendlyError(err)); }
    } catch (err) { setError(friendlyError(err));setServerErrors(fieldErrors(err)); }
    finally { setBusy(false); }
  };
  return <div className="staff-panel">
    <h2>{copy.assigned}</h2>
    {assigned.error && <ErrorBlock message={friendlyError(assigned.error)} onRetry={() => void assigned.refetch()} />}
    {assigned.isLoading ? <Skeleton kind="row" /> : assigned.data?.length ? <ul className="assigned-staff-list">{assigned.data.map(person => <li key={person.staffId}><b>{person.staffName}</b><span>{person.staffEmail}</span></li>)}</ul> : assigned.data && <p className="hint">{copy.noStaff}</p>}
    <h2>{copy.assignStaff}</h2>
    {accounts.error && <ErrorBlock message={friendlyError(accounts.error)} onRetry={() => void accounts.refetch()} />}
    <div className="staff-assign-form"><Field label={copy.chooseStaff}><Select value={choice} disabled={busy || !assigned.data || !accounts.data} onChange={e => setSelected(e.target.value)}>
      <option value="">{copy.chooseStaff}</option>{available.map(person => <option key={person.id} value={person.id}>{person.name} — {person.email}</option>)}
    </Select></Field><Button variant="secondary" disabled={busy || !choice} onClick={() => void assign()}>{copy.assign}</Button></div>
    {!!accounts.data && !!assigned.data && !available.length && <p className="hint">{copy.noAvailableStaff}</p>}
    <Button variant="ghost" disabled={busy} onClick={() => {setShowCreate(before => !before);setError('');}}>{showCreate ? strings.common.close : copy.createStaff}</Button>
    {showCreate && <form className="event-editor staff-create-form" onSubmit={e => void create(e)} noValidate>
      <fieldset disabled={busy}>{(['name','email','password'] as const).map(key => <Field key={key} label={strings.auth[key]} hint={key === 'password' ? strings.auth.passwordHint : undefined} error={show(key)}>
        <Input type={key === 'name' ? 'text' : key} value={values[key]} autoComplete={key === 'password' ? 'new-password' : key} onChange={e => change(key,e.target.value)} onBlur={() => setTouched(before => ({...before,[key]:true}))} required />
      </Field>)}</fieldset><Button type="submit" loading={busy}>{copy.createAndAssign}</Button>
    </form>}
    {error && <p className="notice error" role="alert">{error}</p>}
  </div>;
}
