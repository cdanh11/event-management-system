import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from './features/auth/AuthContext';
import { App } from './app/App';
import './styles/fonts.css';
import './styles/tokens.css';
import './styles/globals.css';
import './styles/attendee.css';
import './styles/operations.css';
import './styles/auth.css';
import './styles/organizer.css';

createRoot(document.getElementById('root')!).render(
  <BrowserRouter><AuthProvider><App /></AuthProvider></BrowserRouter>,
);
