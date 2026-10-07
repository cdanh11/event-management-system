/* eslint-disable react/only-export-components -- provider + hook colocated by design */
import { createContext, useCallback, useContext, useState, type ReactNode } from 'react';
import { AlertCircle, CheckCircle2, Info, TriangleAlert } from 'lucide-react';

/* Global toasts: top-right, auto-dismiss 4s, max 3 stacked, 4 tones.
   Errors surface the backend message (err.message from apiClient). */

type Tone = 'success' | 'error' | 'warning' | 'info';

interface ToastItem {
  id: number;
  tone: Tone;
  message: string;
}

const ToastContext = createContext<{
  toast: (message: string, tone?: Tone) => void;
  notify: (n: { title: string; body: string }) => void;
} | null>(null);

let nextId = 1;

const icons: Record<Tone, typeof Info> = {
  success: CheckCircle2,
  error: AlertCircle,
  warning: TriangleAlert,
  info: Info,
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);

  const push = useCallback((message: string, tone: Tone) => {
    const id = nextId++;
    setItems((prev) => [...prev.slice(-2), { id, tone, message }]);
    setTimeout(() => {
      setItems((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  }, []);

  const toast = useCallback(
    (message: string, tone: Tone = 'success') => push(message, tone),
    [push]
  );
  const notify = useCallback(
    (n: { title: string; body: string }) => push(`${n.title} — ${n.body}`, 'info'),
    [push]
  );

  return (
    <ToastContext.Provider value={{ toast, notify }}>
      {children}
      <div className="toasts" role="status" aria-live="polite">
        {items.map((t) => {
          const Icon = icons[t.tone];
          return (
            <div key={t.id} className={`toast toast-${t.tone}`}>
              <Icon size={16} aria-hidden />
              <span>{t.message}</span>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used inside ToastProvider');
  return ctx;
}
