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
          onClick={() => {
            editor.setSelectedOrgId("new");
            navigate("/organizations/new");
          }}
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
            onClick={() => {
              editor.setSelectedOrgId(org.id);
              navigate(`/organizations/${org.id}`);
            }}
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
                onClick={() => {
                  editor.setSelectedOrgId(editor.organizations[0].id);
                  navigate(`/organizations/${editor.organizations[0].id}`);
                }}
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

            <SelectionChecklist
              title="Tags"
              description="Tenant-spesifikke etiketter for intern filtrering og senere public visning."
              options={editor.tags.map((tag) => ({ id: tag.id, label: tag.name, meta: tag.slug }))}
              selectedIds={editor.draft.tag_ids}
              onToggle={(id) =>
                editor.setDraft((state) => ({
                  ...state,
                  tag_ids: toggleId(state.tag_ids, id),
                }))
              }
            />

            <SelectionChecklist
              title="Kategorier og underkategorier"
              description="Velg underkategorier. Hovedkategori vises automatisk via underkategorien."
              options={editor.subcategories.map((item) => ({
                id: item.id,
                label: item.name,
                meta: item.category.name,
              }))}
              selectedIds={editor.draft.subcategory_ids}
              onToggle={(id) =>
                editor.setDraft((state) => ({
                  ...state,
                  subcategory_ids: toggleId(state.subcategory_ids, id),
                }))
              }
            />

            <div className="grid two">
              <Field label="Website URL" error={editor.organizationFieldErrors.website_url}>
                <input
                  type="url"
                  value={editor.draft.website_url ?? ""}
                  onChange={(e) => editor.setDraft((s) => ({ ...s, website_url: e.target.value }))}
                  placeholder="https://..."
                />
              </Field>
              <Field label="Facebook URL" error={editor.organizationFieldErrors.facebook_url}>
                <input
                  type="url"
                  value={editor.draft.facebook_url ?? ""}
                  onChange={(e) => editor.setDraft((s) => ({ ...s, facebook_url: e.target.value }))}
                  placeholder="https://facebook.com/..."
                />
              </Field>
            </div>

            <div className="grid two">
              <Field label="Instagram URL" error={editor.organizationFieldErrors.instagram_url}>
                <input
                  type="url"
                  value={editor.draft.instagram_url ?? ""}
                  onChange={(e) => editor.setDraft((s) => ({ ...s, instagram_url: e.target.value }))}
                  placeholder="https://instagram.com/..."
                />
              </Field>
              <Field label="TikTok URL" error={editor.organizationFieldErrors.tiktok_url}>
                <input
                  type="url"
                  value={editor.draft.tiktok_url ?? ""}
                  onChange={(e) => editor.setDraft((s) => ({ ...s, tiktok_url: e.target.value }))}
                  placeholder="https://tiktok.com/@..."
                />
              </Field>
            </div>

            <div className="grid two">
              <Field label="LinkedIn URL" error={editor.organizationFieldErrors.linkedin_url}>
                <input
                  type="url"
                  value={editor.draft.linkedin_url ?? ""}
                  onChange={(e) => editor.setDraft((s) => ({ ...s, linkedin_url: e.target.value }))}
                  placeholder="https://linkedin.com/..."
                />
              </Field>
            </div>

            <Field label="YouTube URL" error={editor.organizationFieldErrors.youtube_url}>
              <input
                type="url"
                value={editor.draft.youtube_url ?? ""}
                onChange={(e) => editor.setDraft((s) => ({ ...s, youtube_url: e.target.value }))}
                placeholder="https://youtube.com/..."
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

          <OrganizationLinksPanel navigate={navigate} />
        </>
      )}
    </section>
  );
}

function OrganizationLinksPanel({ navigate }: { navigate: (to: string) => void }) {
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
                      className="ghost-button"
                      onClick={() => {
                        editor.setSelectedPersonId(link.person);
                        navigate(`/people/${link.person}`);
                      }}
                    >
                      Rediger
                    </button>

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
            <div className="actions">
              <span className={`dot ${editor.draft.is_published ? "green" : "gray"}`} />
              <button
                type="button"
                className="ghost-button"
                onClick={editor.onRefreshOrganizationPreview}
                disabled={typeof editor.selectedOrgId !== "number" || editor.previewRefreshState === "saving"}
              >
                {editor.previewRefreshState === "saving" ? "Henter preview..." : "Oppdater preview"}
              </button>
            </div>
          </div>

          <div className="preview-card">
            {editor.selectedOrganization?.preview_image_url ? (
              <img
                src={editor.selectedOrganization.preview_image_url}
                alt={editor.draft.name || "Preview"}
                style={{ width: "100%", height: 180, objectFit: "cover", borderRadius: 10, marginBottom: 12 }}
              />
            ) : null}
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
              <div>
                <dt>Primærlenke</dt>
                <dd>{primaryLink(editor.draft) || "Ikke satt"}</dd>
              </div>
              <div>
                <dt>Kildetype</dt>
                <dd>{linkFieldLabel(editor.selectedOrganization?.primary_link_field) || "Ikke valgt"}</dd>
              </div>
              <div>
                <dt>OG-tittel</dt>
                <dd>{editor.selectedOrganization?.og_title || "Ikke hentet"}</dd>
              </div>
              <div>
                <dt>OG-beskrivelse</dt>
                <dd>{editor.selectedOrganization?.og_description || "Ikke hentet"}</dd>
              </div>
              <div>
                <dt>Sist hentet</dt>
                <dd>{editor.selectedOrganization?.og_last_fetched_at ? formatDateTime(editor.selectedOrganization.og_last_fetched_at) : "Aldri"}</dd>
              </div>
              <div>
                <dt>Tags</dt>
                <dd>{selectedNames(editor.tags, editor.draft.tag_ids) || "Ingen valgt"}</dd>
              </div>
              <div>
                <dt>Underkategorier</dt>
                <dd>{selectedSubcategoryNames(editor.subcategories, editor.draft.subcategory_ids) || "Ingen valgt"}</dd>
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

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("nb-NO", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function primaryLink(draft: {
  website_url: string | null;
  instagram_url: string | null;
  tiktok_url: string | null;
  linkedin_url: string | null;
  facebook_url: string | null;
  youtube_url: string | null;
}): string | null {
  return (
    draft.website_url ||
    draft.instagram_url ||
    draft.tiktok_url ||
    draft.linkedin_url ||
    draft.facebook_url ||
    draft.youtube_url ||
    null
  );
}

function linkFieldLabel(field: string | null | undefined): string | null {
  switch (field) {
    case "website_url":
      return "Website";
    case "instagram_url":
      return "Instagram";
    case "tiktok_url":
      return "TikTok";
    case "linkedin_url":
      return "LinkedIn";
    case "facebook_url":
      return "Facebook";
    case "youtube_url":
      return "YouTube";
    default:
      return null;
  }
}

function SelectionChecklist(props: {
  title: string;
  description: string;
  options: Array<{ id: number; label: string; meta?: string }>;
  selectedIds: number[];
  onToggle: (id: number) => void;
}) {
  const { title, description, options, selectedIds, onToggle } = props;
  return (
    <div className="link-section">
      <div className="sidebar-header">
        <h2>{title}</h2>
        <span className="meta">{selectedIds.length} valgt</span>
      </div>
      <p className="muted">{description}</p>
      <div className="link-list">
        {options.map((option) => (
          <label key={option.id} className="link-row">
            <div>
              <div className="link-person">{option.label}</div>
              {option.meta ? <div className="meta">{option.meta}</div> : null}
            </div>
            <label className="inline-check compact">
              <input
                type="checkbox"
                checked={selectedIds.includes(option.id)}
                onChange={() => onToggle(option.id)}
              />
              <span>Valgt</span>
            </label>
          </label>
        ))}
        {options.length === 0 ? <div className="empty-state">Ingen valg tilgjengelig ennå.</div> : null}
      </div>
    </div>
  );
}

function toggleId(values: number[], id: number): number[] {
  return values.includes(id) ? values.filter((value) => value !== id) : [...values, id];
}

function selectedNames(options: Array<{ id: number; name: string }>, ids: number[]): string {
  return options
    .filter((item) => ids.includes(item.id))
    .map((item) => item.name)
    .join(", ");
}

function selectedSubcategoryNames(options: Array<{ id: number; name: string; category: { name: string } }>, ids: number[]): string {
  return options
    .filter((item) => ids.includes(item.id))
    .map((item) => `${item.category.name}: ${item.name}`)
    .join(", ");
}
