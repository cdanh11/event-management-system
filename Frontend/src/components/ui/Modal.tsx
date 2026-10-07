import { useEffect, useRef, type ReactNode } from 'react';
import { Button } from './Button';
import { strings } from '../../copy/strings';

/* Modal: overlay click + Esc to close, initial focus on the box, aria-modal.
   ConfirmDialog adds danger tone + loading confirm + optional checkbox gate. */
export function Modal({
  open,
  title,
  onClose,
  children,
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  const boxRef = useRef<HTMLDivElement>(null);
  const close = useRef(onClose);
  useEffect(() => { close.current = onClose; });

  useEffect(() => {
    if (!open) return;
    const previous = document.activeElement as HTMLElement | null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    boxRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { e.preventDefault(); close.current(); }
      if (e.key !== 'Tab') return;
      const nodes = Array.from(boxRef.current?.querySelectorAll<HTMLElement>('button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), a[href], [tabindex="0"]') ?? []);
      const first = nodes[0];
      const last = nodes.at(-1);
      if (!first) { e.preventDefault(); boxRef.current?.focus(); return; }
      if (e.shiftKey && (document.activeElement === first || document.activeElement === boxRef.current)) { e.preventDefault(); last?.focus(); }
      if (!e.shiftKey && (document.activeElement === last || document.activeElement === boxRef.current)) { e.preventDefault(); first.focus(); }
    };
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = previousOverflow;
      if (previous?.isConnected) previous.focus();
    };
  }, [open]);

  if (!open) return null;
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal-box"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        ref={boxRef}
        onClick={(e) => e.stopPropagation()}
      >
        <h3>{title}</h3>
        {children}
      </div>
    </div>
  );
}

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = strings.common.confirm,
  error,
  busy = false,
  tone = 'default',
  gate,
  gateChecked,
  onGateChange,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  error?: string;
  busy?: boolean;
  tone?: 'default' | 'danger';
  gate?: string;
  gateChecked?: boolean;
  onGateChange?: (v: boolean) => void;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const blocked = busy || (gate !== undefined && !gateChecked);
  return (
    <Modal open={open} title={title} onClose={() => { if (!busy) onCancel(); }}>
      <p>{message}</p>
      {error && <p className="notice error" role="alert">{error}</p>}
      {gate && (
        <label className="confirm-gate">
          <input
            type="checkbox"
            checked={!!gateChecked}
            onChange={(e) => onGateChange?.(e.target.checked)}
          />
          {gate}
        </label>
      )}
      <div className="modal-actions">
        <Button variant="secondary" disabled={busy} onClick={onCancel}>
          {strings.common.back}
        </Button>
        <Button
          variant={tone === 'danger' ? 'danger' : 'primary'}
          loading={busy}
          disabled={blocked}
          onClick={onConfirm}
        >
          {confirmLabel}
        </Button>
      </div>
    </Modal>
  );
}
