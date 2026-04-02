import { useEffect, useState } from "react";
import {
  ApiError,
  getSession,
  loginSession,
  logoutSession,
  onAuthError,
  type AuthSession,
} from "../api";
import { LoginForm } from "./LoginForm";

export function AuthGate(props: {
  children: (auth: { username: string; onLogout: () => Promise<void> }) => React.ReactNode;
}) {
  const { children } = props;
  const [authLoading, setAuthLoading] = useState(true);
  const [session, setSession] = useState<AuthSession>({ authenticated: false, user: null });
  const [loginForm, setLoginForm] = useState({ username: "", password: "" });
  const [loginError, setLoginError] = useState<string | null>(null);
  const [loginBusy, setLoginBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getSession()
      .then((result) => {
        if (!cancelled) setSession(result);
      })
      .catch(() => {
        if (!cancelled) setSession({ authenticated: false, user: null });
      })
      .finally(() => {
        if (!cancelled) setAuthLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    return onAuthError(({ path }) => {
      if (path.startsWith("/api/auth/")) return;
      setSession({ authenticated: false, user: null });
      setLoginBusy(false);
      setLoginError("Innloggingen er utløpt. Logg inn på nytt.");
      setAuthLoading(false);
    });
  }, []);

  async function onLoginSubmit(event: React.FormEvent) {
    event.preventDefault();
    setLoginError(null);
    setLoginBusy(true);
    try {
      const next = await loginSession(loginForm.username, loginForm.password);
      window.history.replaceState({}, "", "/organizations");
      setSession(next);
      setLoginForm((s) => ({ ...s, password: "" }));
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        const data = err.data as Record<string, unknown>;
        const message = Array.isArray(data.non_field_errors)
          ? String(data.non_field_errors[0])
          : "Innlogging feilet";
        setLoginError(message);
      } else {
        setLoginError(err instanceof Error ? err.message : "Innlogging feilet");
      }
    } finally {
      setLoginBusy(false);
    }
  }

  async function onLogout() {
    try {
      await logoutSession();
    } catch {
      // Even if server session is gone/invalid, reset UI session.
    }
    setSession({ authenticated: false, user: null });
  }

  if (authLoading) {
    return (
      <div className="app-shell">
        <div className="panel auth-panel">
          <p className="eyebrow">Kreative Norge</p>
          <h1>Editor CRM</h1>
          <p className="muted">Sjekker innloggingsstatus...</p>
        </div>
      </div>
    );
  }

  if (!session.authenticated) {
    return (
      <LoginForm
        username={loginForm.username}
        password={loginForm.password}
        busy={loginBusy}
        error={loginError}
        onUsernameChange={(value) => setLoginForm((s) => ({ ...s, username: value }))}
        onPasswordChange={(value) => setLoginForm((s) => ({ ...s, password: value }))}
        onSubmit={onLoginSubmit}
      />
    );
  }

  return <>{children({ username: session.user?.username ?? "", onLogout })}</>;
}
