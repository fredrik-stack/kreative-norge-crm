import { Field } from "../components/Field";
import { useEditor } from "../context/EditorContext";
import { saveLabel } from "../editor-utils";
import { useRouteSyncedSelection } from "../hooks/useRouteSyncedSelection";

export function OrganizationsPage() {
  const editor = useEditor();
  const { navigate, paramValue: orgId } = useRouteSyncedSelection({
    routeParam: "orgId",
    basePath: "/organizations",
    selectedId: editor.selectedOrgId,
    setSelectedId: editor.setSelectedOrgId,
  });

  const orgRouteIsNew = orgId === "new";
  const orgRouteParsed = orgId && !orgRouteIsNew ? Number(orgId) : null;
  const orgRouteIsNumeric = typeof orgRouteParsed === "number" && !Number.isNaN(orgRouteParsed);
  const invalidOrgRoute =
    editor.tenantId !== null &&
    editor.tenantDataLoaded &&
    !!orgId &&
    !orgRouteIsNew &&
    (!orgRouteIsNumeric || !editor.organizations.some((org) => org.id === orgRouteParsed));

  return (
    <main className="workspace">
      <OrganizationsSidebar navigate={navigate} />
      <OrganizationEditorPanel navigate={navigate} orgId={orgId} invalidOrgRoute={invalidOrgRoute} />
      <OrganizationPreviewPanel invalidOrgRoute={invalidOrgRoute} />
    </main>
  );
}

function OrganizationsSidebar({ navigate }: { navigate: (to: string) => void }) {
  const editor = useEditor();
  return (
    <aside className="sidebar panel">
      <div className="sidebar-header">
        <h2>Aktører</h2>
        <span className="meta">
          {editor.organizations.length} stk
          {editor.organizationHasUnsavedChanges ? " · ulagret" : ""}
        </span>
      </div>
      <div className="people-sidebar-actions">
        <input
          className="search-input"
          placeholder="Søk navn, orgnr, kommune..."
          value={editor.query}
          onChange={(e) => editor.setQuery(e.target.value)}
        />
        <button
          type="button"
          className="ghost-button"
          onClick={() => navigate("/organizations/new")}
          disabled={!editor.tenantId}
        >
          Ny organisasjon
        </button>
      </div>

      <div className="list">
        {editor.tenantDataLoading ? <div className="loading-state">Laster aktører...</div> : null}
        {editor.visibleOrganizations.map((org) => (
          <button
            key={org.id}
            type="button"
            className={`list-item ${editor.selectedOrgId === org.id ? "active" : ""}`}
            onClick={() => navigate(`/organizations/${org.id}`)}
          >
            <div className="list-item-title">{org.name}</div>
            <div className="list-item-sub">
              <span>{org.org_number || "Uten orgnr"}</span>
              <span>{org.is_published ? "Publisert" : "Ikke publisert"}</span>
            </div>
          </button>
        ))}
        {!editor.tenantDataLoading && editor.visibleOrganizations.length === 0 ? (
          <div className="empty-state">Ingen treff for søket.</div>
        ) : null}
      </div>
    </aside>
  );
}

function OrganizationEditorPanel(props: {
  navigate: (to: string) => void;
  orgId: string | undefined;
  invalidOrgRoute: boolean;
}) {
  const { navigate, orgId, invalidOrgRoute } = props;
  const editor = useEditor();

  return (
    <section className="panel editor">
      {editor.tenantDataLoading ? (
        <div className="route-missing">
          <p className="eyebrow small">Laster</p>
          <h2>Henter aktørdata...</h2>
          <p className="muted">Vent litt mens tenant-data lastes inn.</p>
        </div>
      ) : invalidOrgRoute ? (
        <div className="route-missing">
          <p className="eyebrow small">Ugyldig URL</p>
          <h2>Aktør ikke funnet</h2>
          <p className="muted">
            Ingen organisasjon matcher ruten <code>/organizations/{orgId}</code>.
          </p>
          <div className="actions">
            <button type="button" className="primary-button" onClick={() => navigate("/organizations/new")}>
              Opprett ny aktør
            </button>
            {editor.organizations[0] ? (
              <button
                type="button"
                className="ghost-button"
                onClick={() => navigate(`/organizations/${editor.organizations[0].id}`)}
              >
                Gå til første aktør
              </button>
            ) : null}
          </div>
        </div>
      ) : (
        <>
          {editor.organizationHasUnsavedChanges ? (
            <div className="inline-banner warn">Du har ulagrede endringer i aktørskjemaet.</div>
          ) : null}
          {editor.organizationLastSavedAt && !editor.organizationHasUnsavedChanges ? (
            <div className="inline-banner success">
              Sist lagret {formatTime(editor.organizationLastSavedAt)}
            </div>
          ) : null}
          <div className="editor-header">
            <div>
              <p className="eyebrow small">
                {editor.selectedOrgId === "new" ? "Ny aktør" : `Aktør #${editor.selectedOrgId ?? "-"}`}
              </p>
              <h2>{editor.draft.name || "Organisasjon"}</h2>
            </div>
            <div className={`save-pill ${editor.saveState}`}>{saveLabel(editor.saveState)}</div>
          </div>

          <form onSubmit={editor.onSubmit} className="editor-form">
            <div className="grid two">
              <Field label="Navn" required>
                <input
                  value={editor.draft.name}
                  onChange={(e) => editor.setDraft((s) => ({ ...s, name: e.target.value }))}
                  required
                />
              </Field>
              <Field label="Org.nr" error={editor.organizationFieldErrors.org_number}>
                <input
                  value={editor.draft.org_number ?? ""}
                  onChange={(e) => editor.setDraft((s) => ({ ...s, org_number: e.target.value }))}
                  inputMode="numeric"
                />
              </Field>
            </div>

            <div className="grid two">
              <Field label="E-post" error={editor.organizationFieldErrors.email}>
                <input
                  type="email"
                  value={editor.draft.email ?? ""}
                  onChange={(e) => editor.setDraft((s) => ({ ...s, email: e.target.value }))}
                />
              </Field>
              <Field label="Telefon" error={editor.organizationFieldErrors.phone}>
                <input
                  value={editor.draft.phone ?? ""}
                  onChange={(e) => editor.setDraft((s) => ({ ...s, phone: e.target.value }))}
                />
              </Field>
            </div>

            <Field label="Kommune(r)">
              <input
                value={editor.draft.municipalities}
                onChange={(e) => editor.setDraft((s) => ({ ...s, municipalities: e.target.value }))}
                placeholder="Bodø, Tromsø"
              />
            </Field>

            <Field label="Notat">
              <textarea
                rows={4}
                value={editor.draft.note ?? ""}
                onChange={(e) => editor.setDraft((s) => ({ ...s, note: e.target.value }))}
              />
            </Field>

            <div className="toggle-grid">
              <label className="toggle-card">
                <input
                  type="checkbox"
                  checked={editor.draft.is_published}
                  onChange={(e) => editor.setDraft((s) => ({ ...s, is_published: e.target.checked }))}
                />
                <div>
                  <strong>Publiser aktør</strong>
                  <p>Synlig i public API når slått på.</p>
                </div>
              </label>

              <label className="toggle-card">
                <input
                  type="checkbox"
                  checked={editor.draft.publish_phone}
                  onChange={(e) => editor.setDraft((s) => ({ ...s, publish_phone: e.target.checked }))}
                />
                <div>
                  <strong>Publiser telefon</strong>
                  <p>Telefon returneres i public API når slått på.</p>
                </div>
              </label>
            </div>

            <div className="actions">
              <button
                type="submit"
                className="primary-button"
                disabled={!editor.tenantId || editor.saveState === "saving"}
              >
                {editor.selectedOrgId === "new" ? "Opprett aktør" : "Lagre endringer"}
              </button>
              <button type="button" className="ghost-button" onClick={editor.onResetOrganizationDraft}>
                Nullstill
              </button>
              {editor.isPending ? <span className="meta">Oppdaterer visning...</span> : null}
            </div>
          </form>

          <OrganizationLinksPanel />
        </>
      )}
    </section>
  );
}

function OrganizationLinksPanel() {
  const editor = useEditor();
  return (
    <div className="link-section">
      <div className="sidebar-header">
        <h2>Personkoblinger</h2>
        <span className="meta">{editor.selectedOrganizationLinks.length} koblinger</span>
      </div>

      {typeof editor.selectedOrgId === "number" ? (
        <>
          <form className="link-create" onSubmit={editor.onCreateLink}>
            <select
              value={editor.linkPersonId ?? ""}
              onChange={(e) => editor.setLinkPersonId(e.target.value ? Number(e.target.value) : null)}
              disabled={editor.availablePersonsForLink.length === 0}
            >
              {editor.availablePersonsForLink.length === 0 ? (
                <option value="">Alle personer er allerede koblet</option>
              ) : (
                editor.availablePersonsForLink.map((person) => (
                  <option key={person.id} value={person.id}>
                    {person.full_name}
                    {person.municipality ? ` · ${person.municipality}` : ""}
                  </option>
                ))
              )}
            </select>

            <select
              value={editor.linkStatus}
              onChange={(e) => editor.setLinkStatus(e.target.value as "ACTIVE" | "INACTIVE")}
            >
              <option value="ACTIVE">ACTIVE</option>
              <option value="INACTIVE">INACTIVE</option>
            </select>

            <label className="inline-check">
              <input
                type="checkbox"
                checked={editor.linkPublishPerson}
                onChange={(e) => editor.setLinkPublishPerson(e.target.checked)}
              />
              <span>Publiser person</span>
            </label>

            <button
              type="submit"
              className="ghost-button"
              disabled={!editor.linkPersonId || editor.availablePersonsForLink.length === 0}
            >
              Knytt person
            </button>
          </form>

          <div className="link-list">
            {editor.selectedOrganizationLinks.map((link) => {
              const person = editor.personsById.get(link.person);
              return (
                <div key={link.id} className="link-row">
                  <div>
                    <div className="link-person">{person?.full_name ?? `Person #${link.person}`}</div>
                    <div className="meta">{person?.municipality || "Ingen kommune"} · ID {link.person}</div>
                  </div>

                  <div className="link-controls">
                    <select
                      value={link.status}
                      onChange={(e) =>
                        editor.updateLink(link.id, { status: e.target.value as "ACTIVE" | "INACTIVE" })
                      }
                    >
                      <option value="ACTIVE">ACTIVE</option>
                      <option value="INACTIVE">INACTIVE</option>
                    </select>

                    <label className="inline-check compact">
                      <input
                        type="checkbox"
                        checked={link.publish_person}
                        onChange={(e) => editor.updateLink(link.id, { publish_person: e.target.checked })}
                      />
                      <span>Publiser</span>
                    </label>

                    <button
                      type="button"
                      className="link-delete"
                      onClick={() => {
                        const personName = person?.full_name ?? `Person #${link.person}`;
                        if (window.confirm(`Fjerne koblingen mellom organisasjonen og ${personName}?`)) {
                          editor.removeLink(link.id);
                        }
                      }}
                    >
                      Fjern
                    </button>
                  </div>
                </div>
              );
            })}
            {editor.selectedOrganizationLinks.length === 0 ? (
              <div className="empty-state">Ingen personer koblet til denne organisasjonen.</div>
            ) : null}
          </div>
        </>
      ) : (
        <div className="empty-state">Lagre eller velg en organisasjon for å administrere personkoblinger.</div>
      )}
    </div>
  );
}

function OrganizationPreviewPanel({ invalidOrgRoute }: { invalidOrgRoute: boolean }) {
  const editor = useEditor();
  return (
    <section className="panel preview">
      {editor.tenantDataLoading ? (
        <div className="route-missing">
          <p className="eyebrow small">Laster</p>
          <h2>Preview lastes...</h2>
          <p className="muted">Preview vises når aktørdata er lastet.</p>
        </div>
      ) : invalidOrgRoute ? (
        <div className="route-missing">
          <p className="eyebrow small">Preview utilgjengelig</p>
          <h2>Ingen aktør valgt</h2>
          <p className="muted">Velg en gyldig aktør fra listen for å se preview.</p>
        </div>
      ) : (
        <>
          <div className="sidebar-header">
            <h2>Public Preview</h2>
            <span className={`dot ${editor.draft.is_published ? "green" : "gray"}`} />
          </div>

          <div className="preview-card">
            <h3>{editor.draft.name || "Ikke navngitt aktør"}</h3>
            <dl>
              <div>
                <dt>Org.nr</dt>
                <dd>{editor.draft.org_number || "Ikke satt"}</dd>
              </div>
              <div>
                <dt>Kommune(r)</dt>
                <dd>{editor.draft.municipalities || "Ikke satt"}</dd>
              </div>
              <div>
                <dt>E-post</dt>
                <dd>{editor.draft.email || "Ikke satt"}</dd>
              </div>
              <div>
                <dt>Telefon (public)</dt>
                <dd>{editor.draft.publish_phone ? editor.draft.phone || "Ikke satt" : "Skjult"}</dd>
              </div>
              <div>
                <dt>Status</dt>
                <dd>{editor.draft.is_published ? "Publisert" : "Ikke publisert"}</dd>
              </div>
            </dl>
            {editor.selectedOrganization?.active_people?.length ? (
              <div className="people-preview">
                <h4>Aktive personer (fra API)</h4>
                <ul>
                  {editor.selectedOrganization.active_people.map((link) => (
                    <li key={link.id}>
                      <span>{link.person?.full_name ?? "Ukjent person"}</span>
                      <small>
                        {link.publish_person ? "Publiseres" : "Skjult"} · {link.status}
                      </small>
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <p className="muted">Ingen aktive personer tilgjengelig i valgt organisasjon.</p>
            )}
          </div>
        </>
      )}
    </section>
  );
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("nb-NO", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}
