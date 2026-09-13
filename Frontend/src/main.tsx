import { createRoot } from 'react-dom/client'; import { BrowserRouter } from 'react-router-dom'; import { AuthProvider } from './features/auth/AuthContext'; import { App } from './app/App'; import './styles/globals.css';
createRoot(document.getElementById('root')!).render(<BrowserRouter><AuthProvider><App/></AuthProvider></BrowserRouter>)
