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
  return (
    <div className="profile-form-actions" aria-label={`Handlinger for ${model}skjema`}>
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
