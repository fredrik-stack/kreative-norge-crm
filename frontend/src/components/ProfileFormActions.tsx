import { profileStatus, type SaveState } from "../editor-utils";

/** Inside the profile's main form; separate writes keep their own controls. */
export function ProfileFormActions({ model, isNew, state, dirty, disabled, onReset }: {
  model: "aktør" | "person"; isNew: boolean; state: SaveState;
  dirty: boolean; disabled: boolean; onReset: () => void;
}) {
  const status = profileStatus(state, dirty, isNew, model);
  return (
    <div className="profile-form-actions" aria-label={`Handlinger for ${model}skjema`}>
      <span className={`profile-status ${status.kind}`} role="status" aria-live="polite">
        {state !== "idle" || dirty ? status.label : ""}
      </span>
      <div className="actions">
        <button type="button" className="ghost-button" onClick={onReset}
          disabled={state === "saving" || (!dirty && state !== "error")}>
          {isNew ? "Nullstill profilutkast" : "Forkast profilutkast"}
        </button>
        <button type="submit" className="primary-button"
          disabled={disabled || state === "saving" || (!isNew && !dirty && state !== "error")}>
          {isNew ? `Opprett ${model}` : `Lagre ${model}`}
        </button>
      </div>
    </div>
  );
}
