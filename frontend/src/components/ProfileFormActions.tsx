import { useEffect, useRef } from "react";
import { profileStatus, type SaveState } from "../editor-utils";

export function ProfileFormActions(props: {
  model: "aktør" | "person";
  isNew: boolean;
  state: SaveState;
  dirty: boolean;
  disabled: boolean;
  onReset: () => void;
}) {
  const { model, isNew, state, dirty, disabled, onReset } = props;
  const status = profileStatus(state, dirty, isNew, model);
  const actionsRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const actions = actionsRef.current;
    const form = actions?.closest("form");
    if (!actions || !form) return;
    let frame = 0;
    const keepFocusVisible = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        const field = document.activeElement;
        if (!(field instanceof HTMLElement) || !form.contains(field) || actions.contains(field)) return;
        if (getComputedStyle(actions).position !== "sticky") return;
        const row = actions.getBoundingClientRect();
        const rect = field.getBoundingClientRect();
        if (row.top < window.innerHeight && row.bottom > 0 && rect.bottom > row.top && rect.top < row.bottom) {
          field.scrollIntoView({ block: "center" });
        }
      });
    };
    form.addEventListener("focusin", keepFocusVisible);
    window.addEventListener("resize", keepFocusVisible);
    const observer = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(keepFocusVisible);
    observer?.observe(actions);
    return () => {
      cancelAnimationFrame(frame);
      form.removeEventListener("focusin", keepFocusVisible);
      window.removeEventListener("resize", keepFocusVisible);
      observer?.disconnect();
    };
  }, []);
  return (
    <div ref={actionsRef} className="profile-form-actions" aria-label={`Handlinger for ${model}skjema`}>
      <div className="profile-form-actions-copy">
        <span className={`save-pill ${status.kind}`} role="status" aria-live="polite">{status.label}</span>
        <p className="meta">
          {model === "aktør"
            ? "Lagrer profilfelt, kategorisering, tags og publiseringsvalg. Bilde, preview og personkoblinger har egne handlinger."
            : "Lagrer profilfelt, kategorisering, tags og primære kontaktfelt. Kontaktkanaler lagres separat; ny kontakt må legges til med egen knapp."}
        </p>
        <p className="meta">{isNew ? "Nullstill tømmer bare profilutkastet." : "Forkast henter sist innlastede profilfelt."} Allerede lagrede endringer angres ikke.</p>
      </div>
      <div className="actions">
        <button type="submit" className="primary-button" disabled={disabled || state === "saving"}>
          {isNew ? `Opprett ${model}` : `Lagre ${model}`}
        </button>
        <button type="button" className="ghost-button" onClick={onReset} disabled={state === "saving"}>
          {isNew ? "Nullstill profilutkast" : "Forkast profilutkast"}
        </button>
      </div>
    </div>
  );
}
