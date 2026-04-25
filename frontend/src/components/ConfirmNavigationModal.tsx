export function ConfirmNavigationModal(props: {
  open: boolean;
  busy: boolean;
  canSaveAndContinue: boolean;
  targetLabel: string | null;
  targetKind: "route" | "tenant" | null;
  dirtySummary: string[];
  onStay: () => void;
  onSaveAndContinue: () => void;
  onDiscardAndContinue: () => void;
  stayButtonRef: React.RefObject<HTMLButtonElement>;
  saveButtonRef: React.RefObject<HTMLButtonElement>;
  leaveButtonRef: React.RefObject<HTMLButtonElement>;
}) {
  const {
    open,
    busy,
    canSaveAndContinue,
    targetLabel,
    targetKind,
    dirtySummary,
    onStay,
    onSaveAndContinue,
    onDiscardAndContinue,
    stayButtonRef,
    saveButtonRef,
    leaveButtonRef,
  } = props;

  if (!open) return null;

  return (
    <div className="modal-backdrop" role="presentation" onClick={onStay}>
      <div
        className="confirm-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="nav-confirm-title"
        aria-describedby="nav-confirm-description"
        onClick={(e) => e.stopPropagation()}
      >
        <p className="eyebrow small">Ulagrede endringer</p>
        <h2 id="nav-confirm-title">Forlate siden?</h2>
        <p id="nav-confirm-description" className="muted">
          Du har ulagrede endringer. Hvis du fortsetter nå uten å lagre, vil de gå tapt.
        </p>
        {dirtySummary.length > 0 ? (
          <div className="dirty-summary">
            <p className="meta">Ulagrede endringer:</p>
            <ul>
              {dirtySummary.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        ) : null}
        {targetLabel ? (
          <p className="meta">
            {targetKind === "tenant" ? "Ny tenant" : "Neste side"}: <code>{targetLabel}</code>
          </p>
        ) : null}
        <div className="actions">
          <button
            ref={stayButtonRef}
            type="button"
            className="ghost-button"
            onClick={onStay}
            disabled={busy}
          >
            Bli her
          </button>
          <button
            ref={saveButtonRef}
            type="button"
            className="ghost-button"
            onClick={onSaveAndContinue}
            disabled={!canSaveAndContinue}
          >
            {busy ? "Lagrer..." : "Lagre og fortsett"}
          </button>
          <button
            ref={leaveButtonRef}
            type="button"
            className="primary-button"
            onClick={onDiscardAndContinue}
            disabled={busy}
          >
            Forlat uten å lagre
          </button>
        </div>
      </div>
    </div>
  );
}
