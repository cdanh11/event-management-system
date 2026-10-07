import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../features/auth/useAuth';
import { homePath } from '../lib/navigation';
import { Button } from '../components/ui/Button';
import { strings } from '../copy/strings';

export function Forbidden() {
  const { user } = useAuth();
  return <section className="error-page">
    <h1>{strings.errors.forbiddenTitle}</h1>
    <Link className="btn btn-secondary" to={user ? homePath(user.role) : '/login'}>{strings.common.goHome}</Link>
  </section>;
}
export function NotFound() {
  const { user } = useAuth();
  const navigate = useNavigate();
  return <section className="error-page">
    <h1>{strings.errors.notFoundTitle}</h1>
    <Button variant="secondary" onClick={() => { if (window.history.length > 1) navigate(-1); else navigate(user ? homePath(user.role) : '/login'); }}>{strings.common.goBack}</Button>
  </section>;
}
