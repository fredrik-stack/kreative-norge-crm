export function LoginForm(props: {
  username: string;
  password: string;
  busy: boolean;
  error: string | null;
  onUsernameChange: (value: string) => void;
  onPasswordChange: (value: string) => void;
  onSubmit: (event: React.FormEvent) => void;
}) {
  const {
    username,
    password,
    busy,
    error,
    onUsernameChange,
    onPasswordChange,
    onSubmit,
  } = props;

  return (
    <div className="app-shell">
      <div className="panel auth-panel">
        <p className="eyebrow">Kreative Norge</p>
        <h1>Logg inn</h1>
        <p className="muted">Editor UI krever innlogging.</p>
        {error ? <div className="banner error">{error}</div> : null}
        <form className="editor-form" onSubmit={onSubmit}>
          <label className="field">
            <span className="field-label">Brukernavn</span>
            <input
              autoComplete="username"
              value={username}
              onChange={(e) => onUsernameChange(e.target.value)}
              required
            />
          </label>
          <label className="field">
            <span className="field-label">Passord</span>
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => onPasswordChange(e.target.value)}
              required
            />
          </label>
          <div className="actions">
            <button type="submit" className="primary-button" disabled={busy}>
              {busy ? "Logger inn..." : "Logg inn"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
