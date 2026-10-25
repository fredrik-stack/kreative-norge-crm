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
  const controls: ReactElement[] = [];
  function findControls(nodes: ReactNode) {
    Children.forEach(nodes, item => {
      if (!isValidElement(item)) return;
      if (["input", "select", "textarea"].includes(String(item.type))) controls.push(item);
      else findControls(item.props.children);
    });
  }
  findControls(items);
  const control = controls.length === 1 ? controls[0] : undefined;
  const controlId = control?.props.id ?? id;
  function bindControl(nodes: ReactNode): ReactNode {
    return Children.map(nodes, item => {
      if (!isValidElement(item)) return item;
      if (item === control) return cloneElement(item, {
    id: controlId,
    "aria-invalid": error ? true : undefined,
    "aria-describedby": [item.props["aria-describedby"], error ? `${id}-error` : null].filter(Boolean).join(" ") || undefined,
      });
      return item.props.children ? cloneElement(item, {}, bindControl(item.props.children)) : item;
    });
  }
  const content = bindControl(items);
  if (!control) return (
    <fieldset className={`field ${error ? "has-error" : ""}`} data-field={name} aria-describedby={error ? `${id}-error` : undefined}>
      <legend className="field-label">{label}{required ? " *" : ""}</legend>
      {content}
      {error ? <span className="field-error" id={`${id}-error`}>{error}</span> : null}
    </fieldset>
  );
  return (
    <div className={`field ${error ? "has-error" : ""}`} data-field={name}>
      <label className="field-label" htmlFor={controlId}>{label}{required ? " *" : ""}</label>
      {content}
      {error ? <span className="field-error" id={`${id}-error`}>{error}</span> : null}
    </div>
  );
}
