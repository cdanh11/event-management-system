import type { ReactNode } from 'react';
import { SearchX } from 'lucide-react';
import { Button } from './Button';
import { strings } from '../../copy/strings';

/* EmptyState: big icon, title, copy, optional action. */
export function EmptyState({
  title,
  body,
  action,
}: {
  title: string;
  body?: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty-state">
      <SearchX size={40} aria-hidden />
      <h3>{title}</h3>
      {body && <p>{body}</p>}
      {action}
    </div>
  );
}

/* Skeleton blocks shown while loading (card / row / stat shapes). */
export function Skeleton({ kind = 'card' }: { kind?: 'card' | 'row' | 'stat' }) {
  if (kind === 'row') {
    return (
      <div className="skel-row" aria-hidden>
        <span className="skel skel-thumb" />
        <span className="skel skel-line" />
        <span className="skel skel-line short" />
      </div>
    );
  }
  if (kind === 'stat') {
    return (
      <div className="skel-stat" aria-hidden>
        <span className="skel skel-line short" />
        <span className="skel skel-num" />
      </div>
    );
  }
  return (
    <div className="skel-card" aria-hidden>
      <span className="skel skel-img" />
      <span className="skel skel-line" />
      <span className="skel skel-line short" />
    </div>
  );
}

/* ErrorBlock: message + Retry button for failed data regions. */
export function ErrorBlock({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="error-block" role="alert">
      <p>{message}</p>
      <Button variant="secondary" size="sm" onClick={onRetry}>
        {strings.common.retry}
      </Button>
    </div>
  );
}
