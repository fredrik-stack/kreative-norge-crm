import type { ReactNode } from "react";

export function Field({
  label,
  required,
  error,
  children,
}: {
  label: string;
  required?: boolean;
  error?: string;
  children: ReactNode;
}) {
  return (
    <label className={`field ${error ? "has-error" : ""}`}>
      <span className="field-label">
        {label}
        {required ? " *" : ""}
      </span>
      {children}
      {error ? <span className="field-error">{error}</span> : null}
    </label>
  );
}
