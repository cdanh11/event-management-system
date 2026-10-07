import { Navigate, useLocation } from 'react-router-dom';

/** Keep old bookmarks while sign-up now shares the sign-in page. */
export function Register() {
  const location = useLocation();
  return <Navigate to="/login?mode=signup" state={location.state} replace />;
}
