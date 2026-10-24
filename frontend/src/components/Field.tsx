import { Children, cloneElement, isValidElement, useId, type ReactNode, type ReactElement } from "react";

export function Field({
  label,
  required,
  error,
  name,
  children,
}: {
  label: string;
  required?: boolean;
  error?: string;
  name?: string;
  children: ReactNode;
}) {
  const id = useId();
  const items = Children.toArray(children);
  const control = items.find((item) => isValidElement(item) && ["input", "select", "textarea"].includes(String(item.type)));
  const content = items.map((item) => item === control ? cloneElement(item as ReactElement, {
    id,
    "aria-invalid": error ? true : undefined,
    "aria-describedby": error ? `${id}-error` : undefined,
  }) : item);
  if (!control) return (
    <fieldset className={`field ${error ? "has-error" : ""}`} data-field={name} aria-describedby={error ? `${id}-error` : undefined}>
      <legend className="field-label">{label}{required ? " *" : ""}</legend>
      {content}
      {error ? <span className="field-error" id={`${id}-error`}>{error}</span> : null}
    </fieldset>
  );
  return (
    <div className={`field ${error ? "has-error" : ""}`} data-field={name}>
      <label className="field-label" htmlFor={id}>{label}{required ? " *" : ""}</label>
      {content}
      {error ? <span className="field-error" id={`${id}-error`}>{error}</span> : null}
    </div>
  );
}
