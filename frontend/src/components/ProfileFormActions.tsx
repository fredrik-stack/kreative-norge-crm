import { profileStatus, type SaveState } from "../editor-utils";

/** Submit the main profile form, including an explicitly associated outer footer. */
export function ProfileFormActions({ model, isNew, state, dirty, disabled, form }: {
  model: "aktør" | "person"; isNew: boolean; state: SaveState;
  dirty: boolean; disabled: boolean; form?: string;
}) {
  const status = profileStatus(state, dirty, isNew, model);
  return (
    <div className="profile-form-actions" aria-label={`Handlinger for ${model}skjema`}>
      <span className={`profile-status ${status.kind}`} role="status" aria-live="polite">
        {state !== "idle" || dirty ? status.label : ""}
      </span>
      <div className="actions">
        <button type="submit" form={form} className="primary-button"
          disabled={disabled || state === "saving" || (!isNew && !dirty && state !== "error")}>
          {isNew ? `Opprett ${model}` : `Lagre ${model}`}
        </button>
      </div>
    </div>
  );
}
