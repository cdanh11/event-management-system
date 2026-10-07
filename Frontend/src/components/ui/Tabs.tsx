import { useRef } from 'react';

/* Tabs with purple underline + arrow-key support. */
export function Tabs<T extends string>({
  tabs,
  active,
  onChange,
  counts,
}: {
  tabs: { key: T; label: string }[];
  active: T;
  onChange: (key: T) => void;
  counts?: Partial<Record<T, number>>;
}) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);

  const onKey = (e: React.KeyboardEvent, i: number) => {
    if (!['ArrowRight', 'ArrowLeft', 'Home', 'End'].includes(e.key)) return;
    e.preventDefault();
    const next = e.key === 'Home' ? 0 : e.key === 'End' ? tabs.length - 1 : (i + (e.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length;
    refs.current[next]?.focus();
    onChange(tabs[next].key);
  };

  return (
    <div className="tabs" role="tablist">
      {tabs.map((t, i) => (
        <button
          key={t.key}
          ref={(el) => {
            refs.current[i] = el;
          }}
          role="tab"
          tabIndex={active === t.key ? 0 : -1}
          aria-selected={active === t.key}
          className={active === t.key ? 'active' : ''}
          onClick={() => onChange(t.key)}
          onKeyDown={(e) => onKey(e, i)}
        >
          {t.label}
          {counts?.[t.key] !== undefined && ` (${counts[t.key]})`}
        </button>
      ))}
    </div>
  );
}
