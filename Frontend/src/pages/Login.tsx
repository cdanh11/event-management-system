import { useState } from 'react';
import { Link, Navigate, useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { Eye, EyeOff } from 'lucide-react';
import { useAuth } from '../features/auth/useAuth';
import { Button } from '../components/ui/Button';
import { Field, Input } from '../components/ui/forms';
import { strings } from '../copy/strings';
import { friendlyError, fieldErrors } from '../lib/errors';
import { postLoginPath } from '../lib/navigation';
import { useToast } from '../components/ui/Toast';

export function Login() {
  const { login, register, user, ready } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();
  const location = useLocation() as { state?: { from?: string; expired?: boolean } };
  const [params] = useSearchParams();
  const signup = params.get('mode') === 'signup';
  const [values, setValues] = useState({ name: '', email: '', password: '', confirm: '' });
  const [showPassword, setShowPassword] = useState(false);
  const [touched, setTouched] = useState<Record<string, boolean>>({});
  const [serverErrors, setServerErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const errors = {
    name: !values.name.trim() ? strings.auth.nameRequired : values.name.trim().length > 120 ? strings.auth.nameLong : '',
    email: !/^\S+@\S+\.\S+$/.test(values.email.trim()) && (signup || !/^(user|staff|organizer)[1-9][0-9]*$/i.test(values.email.trim())) ? signup ? strings.auth.emailInvalid : strings.auth.loginInvalid : '',
    password: signup ? values.password.length < 6 ? strings.auth.passwordShort : values.password.length > 128 ? strings.auth.passwordLong : '' : !values.password ? strings.auth.passwordRequired : '',
    confirm: signup && values.confirm !== values.password ? strings.auth.passwordMismatch : '',
  };
  const change = (field: keyof typeof values, value: string) => {
    setValues((before) => ({ ...before, [field]: value }));
    setServerErrors((before) => ({ ...before, [field]: '' }));
    setError('');
  };
  const blur = (field: keyof typeof values) => setTouched((before) => ({ ...before, [field]: true }));
  const visibleError = (field: keyof typeof values) => serverErrors[field] || (touched[field] ? errors[field] : '');
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (busy || !ready) return;
    setTouched({ name: signup, email: true, password: true, confirm: signup });
    setServerErrors({}); setError('');
    if (errors.email || errors.password || (signup && (errors.name || errors.confirm))) return;
    setBusy(true);
    try {
      const account = signup
        ? await register(values.name.trim(), values.email.trim(), values.password)
        : await login(values.email.trim(), values.password);
      if (signup) toast(strings.auth.created, 'success');
      navigate(postLoginPath(account.role, location.state?.from), {replace:true});
    } catch (err) { setError(friendlyError(err)); setServerErrors(fieldErrors(err)); }
    finally { setBusy(false); }
  };
  if (ready && user) return <Navigate to={postLoginPath(user.role, location.state?.from)} replace />;
  return <div className="auth-page">
    <aside className="auth-copy"><Link className="brand" to="/login"><span>{strings.brandMark}</span>{strings.auth.logo}</Link><h1>{strings.auth.slogan}<br />{strings.auth.secondLine}</h1></aside>
    <main className="auth-main"><div className="auth-mobile-brand"><Link className="brand" to="/login"><span>{strings.brandMark}</span>{strings.auth.logo}</Link><p>{strings.auth.slogan}</p></div>
      <form className="auth-form" onSubmit={(e) => void submit(e)} noValidate>
        <h2>{signup ? strings.auth.joinTitle : strings.auth.signInTitle}</h2>
        {signup && <p className="hint">{strings.auth.signupBody}</p>}
        {(location.state?.expired || sessionStorage.getItem('evently-session-expired')) && <p role="status">{strings.auth.sessionExpired}</p>}
        {signup && <Field label={strings.auth.name} error={visibleError('name')}><Input value={values.name} autoComplete="name" onChange={(e) => change('name',e.target.value)} onBlur={() => blur('name')} disabled={busy} required /></Field>}
        <Field label={signup ? strings.auth.email : strings.auth.loginIdentifier} error={visibleError('email')}><Input value={values.email} type={signup ? 'email' : 'text'} autoComplete={signup ? 'email' : 'username'} onChange={(e) => change('email',e.target.value)} onBlur={() => blur('email')} disabled={busy} required /></Field>
        <Field label={strings.auth.password} error={visibleError('password')}><span className="password-wrap">
          <Input value={values.password} type={showPassword ? 'text' : 'password'} autoComplete={signup ? 'new-password' : 'current-password'} onChange={(e) => change('password',e.target.value)} onBlur={() => blur('password')} disabled={busy} required />
          <button type="button" className="icon" aria-label={showPassword ? strings.auth.hidePassword : strings.auth.showPassword} onClick={() => setShowPassword((before) => !before)}>{showPassword ? <EyeOff size={18} /> : <Eye size={18} />}</button>
        </span></Field>
        {signup && <Field label={strings.auth.confirmPassword} error={visibleError('confirm')}><Input value={values.confirm} type={showPassword ? 'text' : 'password'} autoComplete="new-password" onChange={(e) => change('confirm',e.target.value)} onBlur={() => blur('confirm')} disabled={busy} required /></Field>}
        {error && <p className="notice error" role="alert">{error}</p>}
        <Button type="submit" loading={busy} disabled={!ready}>{signup ? strings.auth.signUp : strings.auth.signIn}</Button>
        <p className="hint">{signup ? strings.auth.signupNote : strings.auth.newHere}{' '}
          <Link to={signup ? '/login' : '/login?mode=signup'} state={location.state} onClick={() => {setError('');setTouched({});setServerErrors({});}}>{signup ? strings.auth.backToSignIn : strings.auth.createAccount}</Link></p>
        {!signup && <dl className="auth-accounts">
          <div><dt>{strings.auth.accountRoles.attendee}:</dt><dd>{strings.auth.sampleAccounts.attendee}</dd></div>
          <div><dt>{strings.auth.accountRoles.staff}:</dt><dd>{strings.auth.sampleAccounts.staff}</dd></div>
          <div><dt>{strings.auth.accountRoles.organizer}:</dt><dd>{strings.auth.sampleAccounts.organizer}</dd></div>
          <div><dt>{strings.auth.password}:</dt><dd>{strings.auth.sampleAccounts.password}</dd></div>
        </dl>}
      </form>
    </main>
  </div>;
}
