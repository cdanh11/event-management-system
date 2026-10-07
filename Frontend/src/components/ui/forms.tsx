import { createContext, useContext, useId, type InputHTMLAttributes, type ReactNode, type Ref, type SelectHTMLAttributes, type TextareaHTMLAttributes } from 'react';

/* Form fields with visible label, hint and inline error (never placeholder-only). */

interface FieldProps {
  label: string;
  hint?: string;
  error?: string;
  children: ReactNode;
}

const FieldContext = createContext<{ id?: string; describedBy?: string; invalid?: boolean }>({});

export function Field({ label, hint, error, children }: FieldProps) {
  const id = useId();
  return (
    <FieldContext.Provider value={{ id, describedBy: error ? `${id}-error` : hint ? `${id}-hint` : undefined, invalid: !!error }}>
    <div className="field">
      <label className="field-label" htmlFor={id}>{label}</label>
      {children}
      {hint && !error && <small id={`${id}-hint`} className="field-hint">{hint}</small>}
      {error && (
        <small id={`${id}-error`} className="field-error" role="alert">
          {error}
        </small>
      )}
    </div>
    </FieldContext.Provider>
  );
}

type InputProps = InputHTMLAttributes<HTMLInputElement> & { ref?: Ref<HTMLInputElement> };

export function Input(props: InputProps) {
  const field = useContext(FieldContext);
  return <input className="input" id={field.id} aria-describedby={field.describedBy} aria-invalid={field.invalid || undefined} {...props} />;
}

type SelectProps = SelectHTMLAttributes<HTMLSelectElement>;

export function Select(props: SelectProps) {
  const field = useContext(FieldContext);
  return <select className="input" id={field.id} aria-describedby={field.describedBy} aria-invalid={field.invalid || undefined} {...props} />;
}

type TextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement>;

export function Textarea(props: TextareaProps) {
  const field = useContext(FieldContext);
  return <textarea className="input" rows={3} id={field.id} aria-describedby={field.describedBy} aria-invalid={field.invalid || undefined} {...props} />;
}
