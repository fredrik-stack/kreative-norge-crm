import { useEffect, useRef, type ReactNode, type InvalidEvent } from "react";

/** Native disclosure keeps controls mounted, including uncontrolled contact drafts. */
export function ProfileSection({ title, summary, errors = [], children }: {
  title: string; summary: string; errors?: Array<string | undefined>; children: ReactNode;
}) {
  const ref = useRef<HTMLDetailsElement>(null);
  const errorKey = errors.filter(Boolean).join("\n");
  useEffect(() => {
    if (errorKey && ref.current) ref.current.open = true;
  }, [errorKey]);
  return (
    <details className={`profile-section ${errorKey ? "has-error" : ""}`} ref={ref}>
      <summary>
        <span><strong>{title}</strong><small>{summary}</small></span>
        {errorKey ? <span className="field-error">Kontroller felt</span> : null}
      </summary>
      <div className="profile-section-body">{children}</div>
    </details>
  );
}

/** Reveal a closed section before the browser focuses a natively invalid field. */
export function revealInvalidProfileField(event: InvalidEvent<HTMLFormElement>) {
  const field = event.target as HTMLElement;
  const section = field.closest("details");
  if (!section || section.open) return;
  event.preventDefault();
  section.open = true;
  requestAnimationFrame(() => { field.focus(); field.scrollIntoView({ block: "center" }); });
}

export function ProfileValidationSummary({ errors }: { errors: Record<string, string | undefined> }) {
  const labels: Record<string, string> = { name: "Navn", full_name: "Fullt navn", org_number: "Org.nr", email: "E-post", phone: "Telefon", website_url: "Nettside", facebook_url: "Facebook", instagram_url: "Instagram", tiktok_url: "TikTok", linkedin_url: "LinkedIn", youtube_url: "YouTube" };
  const entries = Object.entries(errors).filter(([, value]) => value);
  if (!entries.length) return null;
  return <div className="profile-validation" role="alert">
    <strong>Kontroller profilfeltene</strong>
    {entries.map(([key, message]) => <button key={key} type="button" className="table-link" onClick={(event) => {
      const fields = event.currentTarget.closest("form")?.querySelectorAll<HTMLElement>(".field.has-error");
      const field = Array.from(fields ?? []).find(item => item.dataset.field === key);
      const section = field?.closest("details");
      if (section) section.open = true;
      field?.querySelector<HTMLElement>("input,select,textarea")?.focus();
      field?.scrollIntoView({ block: "center" });
    }}>{labels[key] ?? "Profilfelt"}: {message}</button>)}
  </div>;
}
