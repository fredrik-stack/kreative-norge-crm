import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { useLocation } from "react-router-dom";
import { Field } from "../components/Field";
import { useEditor } from "../context/EditorContext";
import { filterSubcategoriesForCategory, sortedCategories as sortCategoriesByTaxonomy } from "../editorTaxonomy";
import { saveLabel } from "../editor-utils";
import { useRouteSyncedSelection } from "../hooks/useRouteSyncedSelection";

export function OrganizationsPage() {
  const editor = useEditor();
  const location = useLocation();
  const { navigate, paramValue: orgId } = useRouteSyncedSelection({
    routeParam: "orgId",
    basePath: "/organizations",
    selectedId: editor.selectedOrgId,
    setSelectedId: editor.setSelectedOrgId,
    syncWhenParamMissing: false,
  });

  const inOverviewMode = !orgId;
  const orgRouteIsNew = orgId === "new";
  const orgRouteParsed = orgId && !orgRouteIsNew ? Number(orgId) : null;
  const orgRouteIsNumeric = typeof orgRouteParsed === "number" && !Number.isNaN(orgRouteParsed);
  const invalidOrgRoute =
    editor.tenantId !== null &&
    editor.tenantDataLoaded &&
    !!orgId &&
    !orgRouteIsNew &&
    (!orgRouteIsNumeric || !editor.organizations.some((org) => org.id === orgRouteParsed));

  const filterSummary = editor.overviewFilterSummary;
  const [overviewModalOrgId, setOverviewModalOrgId] = useState<number | null>(null);

  useEffect(() => {
    if (orgId) return;
    const params = new URLSearchParams(location.search);
    const openOrg = params.get("openOrg");
    if (!openOrg) {
      setOverviewModalOrgId(null);
      return;
    }
    const parsed = Number(openOrg);
    if (!Number.isNaN(parsed)) setOverviewModalOrgId(parsed);
  }, [location.search, orgId]);

  if (inOverviewMode) {
    return (
      <main className="editor-overview-layout">
        <OrganizationOverviewPanel
          organizations={editor.filteredOverviewOrganizations}
          navigate={navigate}
          filterSummary={filterSummary}
          modalOrgId={overviewModalOrgId}
          onModalOrgIdChange={(nextId) => {
            setOverviewModalOrgId(nextId);
            const params = new URLSearchParams(location.search);
            if (nextId === null) {
              params.delete("openOrg");
            } else {
              params.set("openOrg", String(nextId));
            }
            const nextSearch = params.toString();
            navigate(nextSearch ? `/organizations?${nextSearch}` : "/organizations");
          }}
        />
      </main>
    );
  }

  return (
    <main className="workspace no-sidebar">
      <>
        <OrganizationEditorPanel navigate={navigate} orgId={orgId} invalidOrgRoute={invalidOrgRoute} />
        <OrganizationPreviewPanel invalidOrgRoute={invalidOrgRoute} />
      </>
    </main>
  );
}

function OrganizationOverviewPanel(props: {
  organizations: ReturnType<typeof useEditor>["organizations"];
  navigate: (to: string) => void;
  filterSummary: string | null;
  modalOrgId: number | null;
  onModalOrgIdChange: (nextId: number | null) => void;
}) {
  const { organizations, navigate, filterSummary, modalOrgId, onModalOrgIdChange } = props;
  const editor = useEditor();
  const activeOrganization = modalOrgId ? organizations.find((organization) => organization.id === modalOrgId) ?? null : null;

  return (
    <section className="panel overview-panel">
      <div className="sidebar-header">
        <div>
          <p className="eyebrow small">Oversikt</p>
          <h2>Aktørkort</h2>
        </div>
        <span className="meta">{organizations.length} synlige</span>
      </div>
      <p className="muted">
        Her ser du alle aktører i en mer lesbar kortvisning. Klikk på et kort for å åpne all informasjon, og bruk{" "}
        <strong>Rediger</strong> når du vil åpne skjemaet.
      </p>
      {filterSummary ? <div className="filter-summary">{filterSummary}</div> : null}
      <div className="editor-card-grid">
        {organizations.map((organization) => {
          const overviewPills = getOverviewPills(organization);
          return (
          <article
            key={organization.id}
            className="editor-card public-like"
            onClick={() => onModalOrgIdChange(organization.id)}
          >
            {organization.preview_image_url ? (
              <img
                src={organization.preview_image_url}
                alt={organization.name}
                className="editor-card-thumb"
              />
            ) : (
              <div className="editor-card-thumb editor-card-thumb-fallback">
                <span>{organization.name.slice(0, 2).toUpperCase()}</span>
              </div>
            )}
            <div className="editor-card-body">
              <div className="editor-card-head">
                <h3>{organization.name}</h3>
                <span className="meta">{organization.municipalities || "Ingen kommune"}</span>
              </div>
              <div className="meta-row">
                {overviewPills.map((pill) => (
                  <span key={pill.key} className={`mini-pill ${pill.kind}`}>{pill.label}</span>
                ))}
              </div>
              <div className="editor-card-actions">
                <span className={`save-pill ${organization.is_published ? "saved" : "idle"}`}>
                  {organization.is_published ? "Publisert" : "Kun intern"}
                </span>
                <button
                  type="button"
                  className="ghost-button compact-button"
                  onClick={(event) => {
                    event.stopPropagation();
                    editor.setSelectedOrgId(organization.id);
                    navigate(`/organizations/${organization.id}`);
                  }}
                >
                  Rediger
                </button>
              </div>
            </div>
          </article>
        )})}
      </div>
      {organizations.length === 0 ? <div className="empty-state">Ingen aktører matcher filtreringen.</div> : null}
      {activeOrganization ? (
        <OrganizationOverviewModal
          organization={activeOrganization}
          onClose={() => onModalOrgIdChange(null)}
          onEdit={() => {
            editor.setSelectedOrgId(activeOrganization.id);
            navigate(`/organizations/${activeOrganization.id}`);
          }}
        />
      ) : null}
    </section>
  );
}

function OrganizationOverviewModal(props: {
  organization: ReturnType<typeof useEditor>["organizations"][number];
  onClose: () => void;
  onEdit: () => void;
}) {
  const { organization, onClose, onEdit } = props;
  const editor = useEditor();
  const externalLinks = getOrganizationLinkRows(organization);
  const contactsByPersonId = useMemo(() => {
    const grouped = new Map<number, Array<{ type: string; value: string; is_primary?: boolean; is_public?: boolean }>>();
    for (const contact of editor.personContacts) {
      if (!contact.person) continue;
      const current = grouped.get(contact.person) ?? [];
      current.push(contact);
      grouped.set(contact.person, current);
    }
    return grouped;
  }, [editor.personContacts]);
  const modal = (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <div className="detail-modal" role="dialog" aria-modal="true" onClick={(event) => event.stopPropagation()}>
        <div className="sidebar-header modal-header">
          <div>
            <p className="eyebrow small">Aktørkort</p>
            <h2>{organization.name}</h2>
          </div>
          <button type="button" className="ghost-button" onClick={onClose}>
            Lukk
          </button>
        </div>
        <div className="editor-card modal-card modal-shell">
          {organization.preview_image_url ? (
            <img src={organization.preview_image_url} alt={organization.name} className="editor-card-thumb modal-thumb" />
          ) : (
            <div className="editor-card-thumb editor-card-thumb-fallback modal-thumb">
              <span>{organization.name.slice(0, 2).toUpperCase()}</span>
            </div>
          )}
          <div className="editor-card-body">
            <div className="editor-card-head">
              <div>
                <h3>{organization.name}</h3>
                <span className="meta">{organization.municipalities || "Ingen kommune"}</span>
              </div>
              <span className={`save-pill ${organization.is_published ? "saved" : "idle"}`}>
                {organization.is_published ? "Publisert" : "Kun intern"}
              </span>
            </div>
            <div className="meta-row">
              {organization.categories.map((category) => (
                <span key={category.id} className="mini-pill category">{category.name.toUpperCase()}</span>
              ))}
              {organization.subcategories.map((subcategory) => (
                <span key={subcategory.id} className="mini-pill subcategory">{subcategory.name}</span>
              ))}
              {organization.tags.map((tag) => (
                <span key={tag.id} className="mini-pill tag">{tag.name}</span>
              ))}
            </div>
            <p className="muted editor-card-copy">
              {organization.description || organization.note || "Ingen beskrivelse lagt inn ennå."}
            </p>
            <div className="editor-detail-grid">
              <div>
                <span className="meta">E-post</span>
                {organization.email ? <a href={`mailto:${organization.email}`}>{organization.email}</a> : <strong>—</strong>}
              </div>
              <div>
                <span className="meta">Org.nr</span>
                <strong>{organization.org_number || "—"}</strong>
              </div>
              <div>
                <span className="meta">Primærlenke</span>
                {organization.primary_link ? (
                  <a href={organization.primary_link} target="_blank" rel="noreferrer">
                    {organization.primary_link}
                  </a>
                ) : (
                  <strong>—</strong>
                )}
              </div>
            </div>
            {externalLinks.length > 0 ? (
              <div className="editor-detail-section">
                <h4>Lenker</h4>
                <div className="editor-link-list">
                  {externalLinks.map((link) => (
                    <a key={`${organization.id}-${link.label}`} href={link.href} target="_blank" rel="noreferrer">
                      {link.label}
                    </a>
                  ))}
                </div>
              </div>
            ) : null}
            <div className="editor-detail-section">
              <h4>Kontaktpersoner</h4>
              {organization.active_people && organization.active_people.length > 0 ? (
                <div className="editor-contact-list">
                  {organization.active_people.map((link) => {
                    const visibleContacts = getEditorVisibleContacts(link, editor.personsById, contactsByPersonId);
                    return (
                      <div key={link.id} className="editor-contact-card">
                        <strong>{link.person?.full_name || "Ukjent person"}</strong>
                        <span className="meta">
                          {[link.person?.title || null, link.person?.municipality || null].filter(Boolean).join(" · ") || "Ingen kommune"}
                        </span>
                        {visibleContacts.length > 0 ? (
                          <div className="editor-inline-links">
                            {visibleContacts.map((contact, index) => (
                              <a
                                key={`${link.id}-${contact.type}-${index}-${contact.value}`}
                                href={contact.type === "EMAIL" ? `mailto:${contact.value}` : `tel:${contact.value}`}
                              >
                                {contact.value}
                              </a>
                            ))}
                          </div>
                        ) : (
                          <span className="meta">Ingen offentlig kontaktinfo</span>
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="empty-state compact">Ingen kontaktpersoner knyttet til aktøren.</div>
              )}
            </div>
            <div className="actions modal-footer">
              <button type="button" className="ghost-button compact-button" onClick={onClose}>
                Lukk
              </button>
              <button type="button" className="primary-button compact-button" onClick={onEdit}>
                Rediger
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
  return createPortal(modal, document.body);
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
                rows={3}
                value={editor.draft.note ?? ""}
                onChange={(e) => editor.setDraft((s) => ({ ...s, note: e.target.value }))}
                placeholder="Interne kommentarer, status eller ting som ikke skal vises offentlig."
              />
            </Field>

            <Field label="Beskrivelse">
              <textarea
                rows={5}
                value={editor.draft.description ?? ""}
                onChange={(e) => editor.setDraft((s) => ({ ...s, description: e.target.value }))}
                placeholder="Denne teksten vises offentlig under Profil på aktørsiden."
              />
              <p className="muted" style={{ margin: "6px 0 0" }}>
                Dette feltet brukes i public-visningen under Profil-seksjonen.
              </p>
            </Field>

            <CategorySelectFields
              title="Kategori og underkategori"
              description="Velg først en hovedkategori, og deretter en underkategori som hører til den."
              categories={editor.categories}
              subcategories={editor.subcategories}
              selectedCategoryIds={editor.draft.category_ids}
              selectedIds={editor.draft.subcategory_ids}
              onSelect={(categoryId, subcategoryId) =>
                editor.setDraft((state) => ({
                  ...state,
                  category_ids: categoryId ? [categoryId] : [],
                  subcategory_ids: subcategoryId ? [subcategoryId] : [],
                }))
              }
            />

            <Field label="Tags">
              <input
                value={editor.organizationTagInput}
                onChange={(e) => editor.setOrganizationTagInput(e.target.value)}
                placeholder="f.eks. live, management, booking"
              />
              <TagSuggestions
                value={editor.organizationTagInput}
                tags={editor.tags}
                onSelect={(nextValue) => editor.setOrganizationTagInput(nextValue)}
              />
              <p className="muted" style={{ margin: "6px 0 0" }}>
                Skriv egne tags separert med komma. Maks 5 tags.
              </p>
            </Field>

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
  const [linkQuery, setLinkQuery] = useState("");
  const filteredAvailablePersons = useMemo(() => {
    const normalizedQuery = linkQuery.trim().toLowerCase();
    if (!normalizedQuery) return [];
    return editor.availablePersonsForLink
      .filter((person) =>
        [person.full_name, person.email ?? "", person.phone ?? "", person.municipality ?? ""]
          .join(" ")
          .toLowerCase()
          .includes(normalizedQuery),
      )
      .slice(0, 12);
  }, [editor.availablePersonsForLink, linkQuery]);
  return (
    <div className="link-section">
      <div className="sidebar-header">
        <h2>Personkoblinger</h2>
        <span className="meta">{editor.selectedOrganizationLinks.length} koblinger</span>
      </div>

      {typeof editor.selectedOrgId === "number" ? (
        <>
          <div className="link-section">
            <div className="sidebar-header">
              <h2>Opprett ny kontaktperson for denne aktøren</h2>
              <span className={`save-pill ${editor.linkedPersonSaveState}`}>{saveLabel(editor.linkedPersonSaveState)}</span>
            </div>
            <p className="muted">
              Denne flyten oppretter personen, lager første e-post/telefon hvis du fyller det ut, og knytter personen
              direkte til aktøren.
            </p>
            <form className="editor-form" onSubmit={editor.onCreateLinkedPerson}>
              <div className="grid two">
                <Field label="Fullt navn" required error={editor.linkedPersonFieldErrors.full_name}>
                  <input
                    value={editor.linkedPersonDraft.full_name}
                    onChange={(e) => editor.setLinkedPersonDraft((s) => ({ ...s, full_name: e.target.value }))}
                    required
                  />
                </Field>
                <Field label="Tittel">
                  <input
                    value={editor.linkedPersonDraft.title}
                    onChange={(e) => editor.setLinkedPersonDraft((s) => ({ ...s, title: e.target.value }))}
                    placeholder="f.eks. daglig leder, booking eller produsent"
                  />
                </Field>
              </div>

              <div className="grid two">
                <Field label="Kommune">
                  <input
                    value={editor.linkedPersonDraft.municipality}
                    onChange={(e) => editor.setLinkedPersonDraft((s) => ({ ...s, municipality: e.target.value }))}
                  />
                </Field>
              </div>

              <div className="grid two">
                <Field label="E-post" error={editor.linkedPersonFieldErrors.email}>
                  <input
                    type="email"
                    value={editor.linkedPersonDraft.email}
                    onChange={(e) => editor.setLinkedPersonDraft((s) => ({ ...s, email: e.target.value }))}
                  />
                </Field>
                <Field label="Telefon" error={editor.linkedPersonFieldErrors.phone}>
                  <input
                    value={editor.linkedPersonDraft.phone}
                    onChange={(e) => editor.setLinkedPersonDraft((s) => ({ ...s, phone: e.target.value }))}
                  />
                </Field>
              </div>

              <div className="grid two">
                <label className="toggle-card">
                  <input
                    type="checkbox"
                    checked={editor.linkedPersonDraft.publish_email}
                    onChange={(e) => editor.setLinkedPersonDraft((s) => ({ ...s, publish_email: e.target.checked }))}
                  />
                  <div>
                    <strong>Gjør e-post offentlig</strong>
                    <p>Brukes hvis e-post legges inn nå.</p>
                  </div>
                </label>
                <label className="toggle-card">
                  <input
                    type="checkbox"
                    checked={editor.linkedPersonDraft.publish_phone}
                    onChange={(e) => editor.setLinkedPersonDraft((s) => ({ ...s, publish_phone: e.target.checked }))}
                  />
                  <div>
                    <strong>Gjør telefon offentlig</strong>
                    <p>Brukes hvis telefon legges inn nå.</p>
                  </div>
                </label>
              </div>

              <div className="grid two">
                <label className="toggle-card">
                  <input
                    type="checkbox"
                    checked={editor.linkedPersonDraft.publish_person}
                    onChange={(e) => editor.setLinkedPersonDraft((s) => ({ ...s, publish_person: e.target.checked }))}
                  />
                  <div>
                    <strong>Vis personen offentlig</strong>
                    <p>Skal denne personen vises som kontaktperson på aktørsiden?</p>
                  </div>
                </label>
                <Field label="Status på kobling">
                  <select
                    value={editor.linkedPersonDraft.status}
                    onChange={(e) =>
                      editor.setLinkedPersonDraft((s) => ({ ...s, status: e.target.value as "ACTIVE" | "INACTIVE" }))
                    }
                  >
                    <option value="ACTIVE">ACTIVE</option>
                    <option value="INACTIVE">INACTIVE</option>
                  </select>
                </Field>
              </div>

              <div className="actions">
                <button
                  type="submit"
                  className="primary-button"
                  disabled={!editor.linkedPersonDraft.full_name.trim() || editor.linkedPersonSaveState === "saving"}
                >
                  Opprett og knytt kontaktperson
                </button>
              </div>
            </form>
          </div>

          <form className="link-create searchable-link-create" onSubmit={editor.onCreateLink}>
            <div className="link-search-panel">
              <input
                type="search"
                className="search-input link-search-input"
                value={linkQuery}
                onChange={(event) => setLinkQuery(event.target.value)}
                placeholder="Søk etter person å knytte til aktøren"
                disabled={editor.availablePersonsForLink.length === 0}
              />
              {editor.availablePersonsForLink.length === 0 ? (
                <div className="empty-state compact">Alle personer er allerede koblet til denne aktøren.</div>
              ) : !linkQuery.trim() ? (
                <div className="empty-state compact">Skriv navn, kommune, e-post eller telefon for å finne riktig person.</div>
              ) : (
                <div className="link-search-results">
                  {filteredAvailablePersons.length > 0 ? (
                    filteredAvailablePersons.map((person) => {
                      const selected = editor.linkPersonId === person.id;
                      return (
                        <button
                          key={person.id}
                          type="button"
                          className={`link-search-result ${selected ? "active" : ""}`}
                          onClick={() => editor.setLinkPersonId(person.id)}
                        >
                          <strong>{person.full_name}</strong>
                          <span className="meta">
                            {[person.municipality, person.email, person.phone].filter(Boolean).join(" · ") || "Ingen kontaktinfo"}
                          </span>
                        </button>
                      );
                    })
                  ) : (
                    <div className="empty-state compact">Ingen personer matcher søket.</div>
                  )}
                </div>
              )}
            </div>
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
              Knytt eksisterende person
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
                <dt>Beskrivelse (public)</dt>
                <dd>{editor.draft.description || "Ikke satt"}</dd>
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
                <dt>Automatisk thumbnail</dt>
                <dd>{editor.selectedOrganization?.auto_thumbnail_url || "Ikke valgt"}</dd>
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
                <dt>Kategori</dt>
                <dd>{selectedNames(editor.categories, editor.draft.category_ids) || "Ingen valgt"}</dd>
              </div>
              <div>
                <dt>Underkategori</dt>
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

function CategorySelectFields(props: {
  title: string;
  description: string;
  categories: Array<{ id: number; name: string; slug: string }>;
  subcategories: Array<{ id: number; name: string; slug: string; category: { id: number; name: string; slug: string } }>;
  selectedCategoryIds: number[];
  selectedIds: number[];
  onSelect: (categoryId: number | null, subcategoryId: number | null) => void;
}) {
  const { title, description, categories, subcategories, selectedCategoryIds, selectedIds, onSelect } = props;
  const selectedSubcategoryId = selectedIds[0] ?? null;
  const selectedSubcategory =
    selectedSubcategoryId !== null ? subcategories.find((item) => item.id === selectedSubcategoryId) ?? null : null;
  const selectedCategoryId = selectedCategoryIds[0] ?? selectedSubcategory?.category.id ?? null;
  const selectedCategory = selectedCategoryId !== null ? categories.find((item) => item.id === selectedCategoryId) ?? null : null;

  const sortedCategories = sortCategoriesByTaxonomy(categories);

  const availableSubcategories =
    selectedCategory === null ? [] : filterSubcategoriesForCategory(subcategories, selectedCategory.slug);

  return (
    <div className="link-section">
      <div className="sidebar-header">
        <h2>{title}</h2>
        <span className="meta">{selectedSubcategory ? selectedSubcategory.name : "Ingen valgt"}</span>
      </div>
      <p className="muted">{description}</p>
      <div className="grid two">
        <Field label="Hovedkategori">
          <select
            value={selectedCategoryId ?? ""}
            onChange={(e) => {
              const nextCategoryId = e.target.value ? Number(e.target.value) : null;
              onSelect(nextCategoryId, null);
            }}
          >
            <option value="">Velg hovedkategori</option>
            {sortedCategories.map((category) => (
              <option key={category.id} value={category.id}>
                {category.name}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Underkategori">
          <select
            value={selectedSubcategoryId ?? ""}
            onChange={(e) => onSelect(selectedCategoryId, e.target.value ? Number(e.target.value) : null)}
            disabled={selectedCategoryId === null}
          >
            <option value="">
              {selectedCategoryId === null
                ? "Velg hovedkategori først"
                : availableSubcategories.length === 0
                  ? "Ingen underkategorier"
                  : "Ingen underkategori"}
            </option>
            {availableSubcategories.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </Field>
      </div>
    </div>
  );
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

function getOrganizationLinkRows(organization: {
  website_url: string | null;
  instagram_url: string | null;
  tiktok_url: string | null;
  linkedin_url: string | null;
  facebook_url: string | null;
  youtube_url: string | null;
}) {
  return [
    { label: "Nettside", href: organization.website_url },
    { label: "Instagram", href: organization.instagram_url },
    { label: "TikTok", href: organization.tiktok_url },
    { label: "LinkedIn", href: organization.linkedin_url },
    { label: "Facebook", href: organization.facebook_url },
    { label: "YouTube", href: organization.youtube_url },
  ].filter((link): link is { label: string; href: string } => Boolean(link.href));
}

function getOverviewPills(organization: {
  categories: Array<{ id: number; name: string }>;
  subcategories: Array<{ id: number; name: string }>;
  tags: Array<{ id: number; name: string }>;
}) {
  const pills = [
    ...organization.categories.map((category) => ({
      key: `category-${category.id}`,
      label: category.name.toUpperCase(),
      kind: "category" as const,
    })),
    ...organization.subcategories.map((subcategory) => ({
      key: `subcategory-${subcategory.id}`,
      label: subcategory.name,
      kind: "subcategory" as const,
    })),
    ...organization.tags.map((tag) => ({
      key: `tag-${tag.id}`,
      label: tag.name,
      kind: "tag" as const,
    })),
  ];
  if (pills.length <= 5) return pills;
  return [...pills.slice(0, 4), { key: "more", label: `+${pills.length - 4}`, kind: "tag" as const }];
}

function getEditorVisibleContacts(
  link: NonNullable<ReturnType<typeof useEditor>["organizations"][number]["active_people"]>[number],
  personsById: ReturnType<typeof useEditor>["personsById"],
  contactsByPersonId: Map<number, Array<{ type: string; value: string; is_primary?: boolean; is_public?: boolean }>>,
) {
  const personId = link.person?.id;
  if (!personId) return [];
  const person = personsById.get(personId);
  const personContacts = contactsByPersonId.get(personId) ?? [];
  const explicitContacts = personContacts
    .filter((contact) => contact.value)
    .sort((left, right) => Number(Boolean(right.is_primary)) - Number(Boolean(left.is_primary)));
  if (explicitContacts.length > 0) return explicitContacts;

  const fallbackContacts = [
    ...(person?.email ? [{ type: "EMAIL", value: person.email }] : []),
    ...(person?.phone ? [{ type: "PHONE", value: person.phone }] : []),
    ...((link.person?.public_contacts ?? []).map((contact) => ({
      type: contact.type,
      value: contact.value,
      is_primary: contact.is_primary,
    }))),
  ];
  const unique = new Map<string, { type: string; value: string; is_primary?: boolean }>();
  for (const contact of fallbackContacts) {
    if (!contact.value) continue;
    unique.set(`${contact.type}-${contact.value}`, contact);
  }
  return [...unique.values()];
}

function TagSuggestions(props: {
  value: string;
  tags: Array<{ id: number; name: string }>;
  onSelect: (nextValue: string) => void;
}) {
  const { value, tags, onSelect } = props;
  const suggestions = getTagSuggestions(value, tags);
  if (suggestions.length === 0) return null;

  return (
    <div className="tag-suggestions" role="listbox" aria-label="Eksisterende tags">
      {suggestions.map((tag) => (
        <button
          key={tag.id}
          type="button"
          className="mini-pill tag suggestion-chip"
          onClick={() => onSelect(applyTagSuggestion(value, tag.name))}
        >
          {tag.name}
        </button>
      ))}
    </div>
  );
}

function getTagSuggestions(value: string, tags: Array<{ id: number; name: string }>) {
  const parsed = value.split(",");
  const activeTerm = (parsed[parsed.length - 1] ?? "").trim().toLocaleLowerCase("nb");
  const chosen = new Set(
    parsed
      .slice(0, -1)
      .map((item) => item.trim().toLocaleLowerCase("nb"))
      .filter(Boolean),
  );
  if (!activeTerm) return [];
  return tags
    .filter((tag) => !chosen.has(tag.name.toLocaleLowerCase("nb")))
    .filter((tag) => tag.name.toLocaleLowerCase("nb").includes(activeTerm))
    .slice(0, 6);
}

function applyTagSuggestion(currentValue: string, tagName: string) {
  const parts = currentValue
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  if (parts.length === 0) return tagName;
  parts[parts.length - 1] = tagName;
  return parts.join(", ");
}

function matchesOrganizationFilters(input: {
  organization: {
    name: string;
    org_number: string | null;
    email: string | null;
    phone: string | null;
    municipalities: string;
    note: string | null;
    description: string | null;
    tags: Array<{ slug: string; name: string }>;
    categories: Array<{ slug: string; name: string }>;
    subcategories: Array<{ slug: string; name: string }>;
  };
  query: string;
  categorySlug: string;
  subcategorySlug: string;
  tagSlug: string;
  personNames: string[];
}) {
  const { organization, query, categorySlug, subcategorySlug, tagSlug, personNames } = input;
  const normalizedQuery = query.trim().toLowerCase();
  if (categorySlug && !organization.categories.some((category) => category.slug === categorySlug)) {
    return false;
  }
  if (subcategorySlug && !organization.subcategories.some((subcategory) => subcategory.slug === subcategorySlug)) {
    return false;
  }
  if (tagSlug && !organization.tags.some((tag) => tag.slug === tagSlug)) {
    return false;
  }
  if (!normalizedQuery) return true;

  const haystack = [
    organization.name,
    organization.org_number ?? "",
    organization.email ?? "",
    organization.phone ?? "",
    organization.municipalities ?? "",
    organization.note ?? "",
    organization.description ?? "",
    ...organization.tags.map((tag) => tag.name),
    ...organization.categories.map((category) => category.name),
    ...organization.subcategories.map((subcategory) => subcategory.name),
    ...personNames,
  ]
    .join(" ")
    .toLowerCase();

  return haystack.includes(normalizedQuery);
}

function describeEditorFilterState(input: {
  query: string;
  categorySlug: string;
  subcategorySlug: string;
  tagSlug: string;
  entityLabel: string;
}) {
  const { query, categorySlug, subcategorySlug, tagSlug, entityLabel } = input;
  const parts: string[] = [];
  if (query.trim()) parts.push(`søk "${query.trim()}"`);
  if (categorySlug) parts.push(`hovedkategori ${humanizeSlug(categorySlug)}`);
  if (subcategorySlug) parts.push(`underkategori ${humanizeSlug(subcategorySlug)}`);
  if (tagSlug) parts.push(`tag ${humanizeSlug(tagSlug)}`);
  if (parts.length === 0) return null;
  return `Viser ${entityLabel} filtrert på ${parts.join(", ")}.`;
}

function humanizeSlug(value: string) {
  return value.replace(/-/g, " ");
}
