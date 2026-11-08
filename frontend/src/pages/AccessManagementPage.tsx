import { useEffect, useState } from "react";
import {
  ApiError, getManagementContext, getManagedMemberships, saveManagedMembership,
  publishSharingAgreement, acceptSharingAgreement, revokeSharingAcceptance,
  type ManagementContext, type ManagementMembership,
} from "../api";

const roles = ["leser", "redigerer", "gruppeadmin", "superadmin"];
const emptyMember: ManagementMembership = {username: "", role: "leser", is_active: true, expected_updated_at: null};

export function AccessManagementPage({ username }: {username: string}) {
  const [context, setContext] = useState<ManagementContext | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const refresh = async () => setContext(await getManagementContext());
  useEffect(() => { void refresh().catch(() => setError("Kunne ikke hente tilgangsstatus.")); }, []);
  async function run(action: () => Promise<unknown>) {
    setBusy(true); setError(""); setMessage("");
    try { await action(); await refresh(); setMessage("Handlingen er registrert. Delt CRM-tilgang er fortsatt av."); }
    catch (e) {
      const code = e instanceof ApiError ? (e.data as {code?: string})?.code : null;
      setError(code ? `Handlingen ble ikke bekreftet (${code}). Hent status på nytt før et nytt forsøk.` : "Handlingen ble ikke bekreftet. Hent status på nytt før et nytt forsøk.");
    } finally { setBusy(false); }
  }
  if (!context) return <section className="panel access-management-page"><h1>Tilgang og avtale</h1><p>{error || "Henter status…"}</p></section>;
  if (!context.enabled) return <section className="panel access-management-page"><h1>Tilgang og avtale</h1><p>Tilgangsforvaltning er ikke aktivert.</p></section>;
  return <section className="panel access-management-page">
    <h1>Tilgang og avtale</h1>
    <p>Denne siden åpner ikke delt CRM-tilgang. Dagens legacytilgang styres fortsatt separat.</p>
    {error && <p role="alert">{error}</p>}{message && <p role="status">{message}</p>}
    <button className="ghost-button" type="button" disabled={busy} onClick={() => void run(refresh)}>Hent status på nytt</button>
    {context.memberships.map(m => {
      const a = m.agreement;
      const accepted = a && context.acceptances.some(x => x.agreement_id === a.id && !x.revoked);
      return <section key={m.tenant_id} className="panel">
        <h2>Delingsavtale – {m.tenant_name}</h2>
        {!a ? <p>Ingen gjeldende avtale.</p> : <AgreementAcceptance key={a.id} text={a.text} version={a.version}
          accepted={!!accepted} busy={busy} accept={() => run(() => acceptSharingAgreement(m.domain_id, m.tenant_id, a.id))} />}
      </section>;
    })}
    {context.acceptances.filter(a => !a.revoked).map(a => <p key={a.id}>
      Egen aksept, domene {a.domain_id}, versjon {a.version}. <button className="ghost-button" type="button" disabled={busy}
        onClick={() => void run(() => revokeSharingAcceptance(a.id))}>Tilbakekall min aksept</button>
    </p>)}
    {context.grants.filter(g => g.action === "manage_tenant_memberships" && g.tenant_id).map(g =>
      <Memberships key={`${g.domain_id}-${g.tenant_id}`} domain={g.domain_id} tenant={g.tenant_id!} name={g.tenant_name || ""}
        username={username} run={run} busy={busy} />)}
    {context.published_agreements.map(a => <details key={a.id}><summary>Publisert i domene {a.domain_id}: versjon {a.version}, gjelder fra {a.effective_at}</summary>
      <p>Juridisk referanse: {a.legal_approval_reference}</p><pre style={{whiteSpace:"pre-wrap", font:"inherit"}}>{a.text}</pre></details>)}
    {context.grants.filter(g => g.action === "publish_sharing_agreement").map(g =>
      <Publication key={g.domain_id} domain={g.domain_id} name={g.domain_name} run={run} busy={busy} />)}
  </section>;
}

function AgreementAcceptance({text, version, accepted, busy, accept}: {
  text: string; version: number; accepted: boolean; busy: boolean; accept: () => Promise<void>;
}) {
  const [confirmed, setConfirmed] = useState(false);
  useEffect(() => setConfirmed(false), [accepted]);
  return <><p>Gjeldende versjon: {version}. {accepted ? "Du har akseptert denne versjonen." : "Du har ikke akseptert denne versjonen."}</p>
    <pre style={{whiteSpace: "pre-wrap", font: "inherit"}}>{text}</pre>
    {!accepted && <><label className="access-check"><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)} />
      Jeg har lest og aksepterer denne avtaleversjonen.</label>
      <button className="primary-button" type="button" disabled={busy || !confirmed} onClick={() => void accept()}>Aksepter delingsavtalen</button></>}
  </>;
}

type Runner = (action: () => Promise<unknown>) => Promise<void>;
function Memberships({domain, tenant, name, username, run, busy}: {
  domain: number; tenant: number; name: string; username: string; run: Runner; busy: boolean;
}) {
  const [rows, setRows] = useState<ManagementMembership[]>([]);
  const [draft, setDraft] = useState<ManagementMembership>(emptyMember);
  const [loaded, setLoaded] = useState(false);
  const reload = async () => {setRows(await getManagedMemberships(domain, tenant)); setLoaded(true);};
  useEffect(() => {void run(reload);}, [domain, tenant]);
  return <section className="panel"><h2>Medlemskap – {name}</h2>
    <p>Medlemskap og rolle kan påvirke dagens legacytilgang. Inaktivmarkering gir ikke full tilgangsstenging.</p>
    <button className="ghost-button" type="button" disabled={busy} onClick={() => void run(reload)}>Hent medlemskap på nytt</button>
    <ul>{rows.map(row => <li key={row.username}>{row.username}: {row.role}, {row.is_active ? "aktiv" : "inaktiv"} <button
      type="button" disabled={busy || row.username === username} onClick={() => setDraft(row)}>Endre medlemskap</button></li>)}</ul>
    <form onSubmit={e => {e.preventDefault(); void run(async () => {
      await saveManagedMembership(domain, tenant, draft); await reload(); setDraft(emptyMember);
    });}}>
      <label>Eksisterende brukernavn<input required value={draft.username} readOnly={draft.expected_updated_at !== null}
        onChange={e => setDraft({...draft, username: e.target.value})} /></label>
      <label>Medlemsrolle<select value={draft.role} onChange={e => setDraft({...draft, role: e.target.value})}>
        {roles.map(role => <option key={role} value={role}>{role}</option>)}</select></label>
      <label className="access-check"><input type="checkbox" checked={draft.is_active} onChange={e => setDraft({...draft, is_active: e.target.checked})} />Aktivt medlemskap</label>
      <button className="primary-button" disabled={busy || !loaded || draft.username === username}>Lagre medlemskap</button>
      <button className="ghost-button" type="button" disabled={busy} onClick={() => setDraft(emptyMember)}>Nytt medlemskap</button>
    </form>
  </section>;
}

function Publication({domain, name, run, busy}: {domain: number; name: string; run: Runner; busy: boolean}) {
  const [version, setVersion] = useState(1);
  const [text, setText] = useState("");
  const [effective, setEffective] = useState("");
  const [reference, setReference] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  return <section className="panel"><h2>Publiser avtale – {name}</h2>
    <p>Publiseringsfullmakt gir ikke juridisk godkjenningsmyndighet. Versjonen er uforanderlig etter publisering.</p>
    <form onSubmit={e => {e.preventDefault(); void run(async () => {
      await publishSharingAgreement(domain, {version, text, effective_at: new Date(effective).toISOString(), legal_approval_reference: reference, approved: confirmed});
      setConfirmed(false);
    });}}>
      <label>Versjon<input type="number" min="1" required value={version} onChange={e => setVersion(Number(e.target.value))} /></label>
      <label>Godkjent avtaletekst<textarea required value={text} onChange={e => {setText(e.target.value); setConfirmed(false);}} /></label>
      <label>Gjelder fra (lokal tid)<input type="datetime-local" required value={effective} onChange={e => setEffective(e.target.value)} /></label>
      <label>Referanse til juridisk godkjenning<input required maxLength={200} value={reference} onChange={e => {setReference(e.target.value); setConfirmed(false);}} /></label>
      <label className="access-check"><input type="checkbox" required checked={confirmed} onChange={e => setConfirmed(e.target.checked)} />
        Teksten er godkjent av MUSIKKONTORET AS eller formelt bemyndiget representant.</label>
      <button className="primary-button" disabled={busy || !confirmed}>Publiser godkjent versjon</button>
    </form>
  </section>;
}
