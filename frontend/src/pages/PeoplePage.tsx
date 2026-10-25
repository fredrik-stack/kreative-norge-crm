import { ProfileSection, ProfileValidationSummary, revealInvalidProfileField } from "../components/ProfileSection";
import { useReadDialog } from "../hooks/useReadDialog";
import { ProfileFormActions } from "../components/ProfileFormActions";
import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { Field } from "../components/Field";
import { PhoneLink } from "../components/PhoneLink";
import { PhoneRegionSelect } from "../components/PhoneRegionSelect";
import { useEditor } from "../context/EditorContext";
import { filterSubcategoriesForCategory, sortedCategories as sortCategoriesByTaxonomy } from "../editorTaxonomy";
import { useRouteSyncedSelection } from "../hooks/useRouteSyncedSelection";

export function PeoplePage() {
  const editor = useEditor();
  const { navigate, paramValue: personId } = useRouteSyncedSelection({
    routeParam: "personId",
    basePath: "/people",
    selectedId: editor.selectedPersonId,
    setSelectedId: editor.setSelectedPersonId,
    syncWhenParamMissing: false,
  });

  const inOverviewMode = !personId;
  const personRouteIsNew = personId === "new";
  const personRouteParsed = personId && !personRouteIsNew ? Number(personId) : null;
  const personRouteIsNumeric =
    typeof personRouteParsed === "number" && !Number.isNaN(personRouteParsed);
  const invalidPersonRoute =
    editor.tenantId !== null &&
    editor.tenantDataLoaded &&
    !!personId &&
    !personRouteIsNew &&
    (!personRouteIsNumeric || !editor.persons.some((person) => person.id === personRouteParsed));

  const filterSummary = editor.overviewFilterSummary;

  useEffect(() => {
    if (editor.tenantDataLoaded && !inOverviewMode && !editor.canWrite) {
      navigate("/people");
    }
  }, [editor.canWrite, editor.tenantDataLoaded, inOverviewMode, navigate]);

  if (inOverviewMode) {
    return (
      <main className="editor-overview-layout">
        <PeopleOverviewPanel persons={editor.filteredOverviewPersons} navigate={navigate} filterSummary={filterSummary} />
      </main>
    );
  }

  if (!editor.canWrite) return null;

  return (
    <section className="people-workspace no-sidebar">
      <PeopleEditorPanel navigate={navigate} personId={personId} invalidPersonRoute={invalidPersonRoute} />
    </section>
  );
}

function PeopleOverviewPanel(props: {
  persons: ReturnType<typeof useEditor>["persons"];
  navigate: (to: string) => void;
  filterSummary: string | null;
}) {
  const { persons, navigate, filterSummary } = props;
  const editor = useEditor();
  const [modalPersonId, setModalPersonId] = useState<number | null>(null);
  const organizationsById = useMemo(() => new Map(editor.organizations.map((organization) => [organization.id, organization])), [editor.organizations]);
  const linkedOrganizationsByPersonId = useMemo(() => {
    const grouped = new Map<number, Array<{ id: number; name: string }>>();
    for (const link of editor.organizationPeople) {
      const organization = organizationsById.get(link.organization);
      if (!organization) continue;
      const current = grouped.get(link.person) ?? [];
      current.push({ id: organization.id, name: organization.name });
      grouped.set(link.person, current);
    }
    return grouped;
  }, [editor.organizationPeople, organizationsById]);
  const activePerson = modalPersonId ? persons.find((person) => person.id === modalPersonId) ?? null : null;

  const constrained = Boolean(editor.overviewQuery.trim() || editor.overviewCategorySlug || editor.overviewSubcategorySlug || editor.overviewTagSlug);
  return (
    <section className="panel overview-panel">
      <div className="sidebar-header"><div><p className="eyebrow small">Kontaktoversikt</p><h2>Personer</h2><p className="meta overview-hint"><span aria-hidden="true">💡</span> Klikk på navn for utfyllende info</p></div>
        {constrained && !editor.tenantDataLoading && !editor.tenantDataError && !editor.overviewSearchPending ? <span className="meta">{persons.length} treff i innlastet utvalg</span> : null}
      </div>
      {editor.tenantDataError ? <div className="empty-state" role="alert">Personoversikten kunne ikke lastes. Prøv å laste siden på nytt.</div>
      : !editor.tenantId ? <div className="empty-state">Velg et Musikkontor for å søke etter personer.</div>
      : editor.tenantDataLoading ? <div className="empty-state" role="status">Henter persondata…</div>
      : !constrained ? <div className="search-entry"><span className="search-entry-icon" aria-hidden="true">⌕</span><h3>Finn en person</h3><p>Søk etter navn, kontaktinfo, aktør eller sted, eller velg et filter ovenfor.</p><p className="meta">Personer vises når du har avgrenset utvalget.</p></div>
      : editor.overviewSearchPending ? <div className="empty-state" role="status">Oppdaterer utvalget…</div>
      : persons.length === 0 ? <div className="empty-state">Ingen personer matcher søket eller filtrene.</div>
      : <div className="overview-table-wrap person-results">
        <table className="overview-table"><caption className="sr-only">Personer som matcher søk og filtre</caption>
          <thead><tr><th>Navn og tittel</th><th>Aktører</th><th>Kontakt</th><th>Sted</th></tr></thead>
          <tbody>{persons.map(person => {
            const linkedOrganizations = linkedOrganizationsByPersonId.get(person.id) ?? [];
            return <tr key={person.id} className={editor.selectedPersonId === person.id ? "selected-result" : undefined}>
              <td data-label="Navn og tittel"><button type="button" className="table-link person-name" onClick={() => { editor.setSelectedPersonId(person.id); setModalPersonId(person.id); }}>{person.full_name}</button>{person.title ? <span className="result-secondary">{person.title}</span> : null}<div className="result-taxonomy">{[...person.categories.map(item => item.name), ...person.subcategories.map(item => item.name), ...person.tags.map(item => item.name)].map((name, index) => <span key={`${index}:${name}`} className="mini-pill">{name}</span>)}</div></td>
              <td data-label="Aktører">{linkedOrganizations.length ? <div className="table-linked-items">{linkedOrganizations.map(organization => <button key={organization.id} type="button" className="table-link secondary" onClick={() => navigate(`/organizations?openOrg=${organization.id}`)}>{organization.name}</button>)}</div> : <span className="meta">Ingen aktørtilknytning</span>}</td>
              <td data-label="Kontakt"><div className="result-contact">{person.email ? <a href={`mailto:${person.email}`}>{person.email}</a> : null}<PhoneLink value={person.phone} dialUri={person.phone_dial_uri} countryCallingCodeHint={person.phone_country_calling_code_hint} empty={person.email ? null : "Ingen kontaktinfo"}/></div></td>
              <td data-label="Sted">{person.municipality || "—"}</td>
            </tr>;
          })}</tbody>
        </table>
      </div>}
      {activePerson && constrained ? <PersonOverviewModal person={activePerson} linkedOrganizations={linkedOrganizationsByPersonId.get(activePerson.id) ?? []} onClose={() => setModalPersonId(null)}
        onEdit={editor.canWrite ? () => { editor.setSelectedPersonId(activePerson.id); navigate(`/people/${activePerson.id}`); } : null}
        onOpenOrganization={id => navigate(`/organizations?openOrg=${id}`)} /> : null}
    </section>
  );
}

function PersonOverviewModal(props: {
  person: ReturnType<typeof useEditor>["persons"][number];
  linkedOrganizations: Array<{ id: number; name: string }>;
  onClose: () => void;
  onEdit: (() => void) | null;
  onOpenOrganization: (organizationId: number) => void;
}) {
  const { person, linkedOrganizations, onClose, onEdit, onOpenOrganization } = props;
  const externalLinks = getPersonLinkRows(person);
  const dialogRef = useReadDialog(onClose);
  const modal = (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <div ref={dialogRef} className="detail-modal" role="dialog" aria-modal="true" aria-label={person.full_name} tabIndex={-1} onClick={(event) => event.stopPropagation()}>
        <div className="sidebar-header modal-header">
          <div>
            <p className="eyebrow small">Personinformasjon</p>
            <h2>{person.full_name}</h2>
          </div>
          <button type="button" className="ghost-button" onClick={onClose}>
            Lukk
          </button>
        </div>
        <div className="editor-card modal-card person-modal-card no-thumb modal-shell">
          <div className="editor-card-body">
            <div className="editor-card-head person-modal-head">
              <div>

                <div className="person-modal-meta">
                  <span className="person-modal-role">{person.title || "Ingen tittel"}</span>
                  {person.municipality ? <span className="meta">{person.municipality}</span> : null}
                </div>
              </div>
            </div>
            <div className="meta-row">
              {person.categories.map((category) => (
                <span key={category.id} className="mini-pill category">{category.name.toUpperCase()}</span>
              ))}
              {person.subcategories.map((subcategory) => (
                <span key={subcategory.id} className="mini-pill subcategory">{subcategory.name}</span>
              ))}
              {person.tags.map((tag) => (
                <span key={tag.id} className="mini-pill tag">{tag.name}</span>
              ))}
            </div>
            <div className="modal-sections">
              <section className="editor-detail-section modal-section-card">
                <div className="modal-section-header">
                  <h4>Internt notat</h4>
                </div>
                <p className="muted editor-card-copy">{person.note || "Ingen notat lagt inn ennå."}</p>
              </section>

              <section className="editor-detail-section modal-section-card">
                <div className="modal-section-header">
                  <h4>Kontakt</h4>
                </div>
                <div className="editor-detail-grid modal-detail-grid">
                  <div>
                    <span className="meta">E-post</span>
                    {person.email ? <a href={`mailto:${person.email}`}>{person.email}</a> : <strong>—</strong>}
                  </div>
                  <div>
                    <span className="meta">Telefon</span>
                    <PhoneLink
                      value={person.phone}
                      dialUri={person.phone_dial_uri}
                      countryCallingCodeHint={person.phone_country_calling_code_hint}
                      empty={<strong>—</strong>}
                    />
                  </div>
                  <div>
                    <span className="meta">Primærlenke</span>
                    {getPersonPrimaryLink(person) ? (
                      <a href={getPersonPrimaryLink(person)!} target="_blank" rel="noreferrer">
                        {truncateLink(getPersonPrimaryLink(person)!)}
                      </a>
                    ) : (
                      <strong>—</strong>
                    )}
                  </div>
                </div>
              </section>

              <section className="editor-detail-section modal-section-card">
                <div className="modal-section-header">
                  <h4>Knyttet til</h4>
                  <span className="meta">{linkedOrganizations.length} aktører</span>
                </div>
                {linkedOrganizations.length > 0 ? (
                  <div className="table-linked-items modal-linked-items">
                    {linkedOrganizations.map((organization) => (
                      <button
                        key={`${person.id}-${organization.id}`}
                        type="button"
                        className="table-link secondary"
                        onClick={() => onOpenOrganization(organization.id)}
                      >
                        {organization.name}
                      </button>
                    ))}
                  </div>
                ) : (
                  <strong>—</strong>
                )}
              </section>

              {externalLinks.length > 0 ? (
                <section className="editor-detail-section modal-section-card">
                  <div className="modal-section-header">
                    <h4>Lenker</h4>
                    <span className="meta">{externalLinks.length} lenker</span>
                  </div>
                  <div className="editor-link-list modal-link-list">
                    {externalLinks.map((link) => (
                      <a key={`${person.id}-${link.label}`} href={link.href} target="_blank" rel="noreferrer">
                        {link.label}
                      </a>
                    ))}
                  </div>
                </section>
              ) : null}
            </div>
            <div className="actions modal-footer">
              <button type="button" className="ghost-button compact-button" onClick={onClose}>
                Lukk
              </button>
              {onEdit ? (
                <button type="button" className="primary-button compact-button" onClick={onEdit}>
                  Rediger
                </button>
              ) : null}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
  return createPortal(modal, document.body);
}

function PeopleEditorPanel(props: {
  navigate: (to: string) => void;
  personId: string | undefined;
  invalidPersonRoute: boolean;
}) {
  const { navigate, personId, invalidPersonRoute } = props;
  const editor = useEditor();
  const selectedPersonLinks =
    typeof editor.selectedPersonId === "number"
      ? editor.organizationPeople.filter((link) => link.person === editor.selectedPersonId)
      : [];
  const publicPersonLinks = selectedPersonLinks.filter(
    (link) => link.status === "ACTIVE" && link.publish_person,
  ).length;


  return (
    <section className="panel people-editor">
      {editor.tenantDataLoading ? (
        <div className="route-missing">
          <p className="eyebrow small">Laster</p>
          <h2>Henter persondata...</h2>
          <p className="muted">Vent litt mens tenant-data lastes inn.</p>
        </div>
      ) : invalidPersonRoute ? (
        <div className="route-missing">
          <p className="eyebrow small">Ugyldig URL</p>
          <h2>Person ikke funnet</h2>
          <p className="muted">
            Ingen person matcher ruten <code>/people/{personId}</code>.
          </p>
          <div className="actions">
            <button type="button" className="primary-button" onClick={() => navigate("/people/new")}>
              Opprett ny person
            </button>
            {editor.persons[0] ? (
              <button
                type="button"
                className="ghost-button"
                onClick={() => {
                  editor.setSelectedPersonId(editor.persons[0].id);
                  navigate(`/people/${editor.persons[0].id}`);
                }}
              >
                Gå til første person
              </button>
            ) : null}
          </div>
        </div>
      ) : (
        <>
          {editor.personSaveMessage ? <div className="inline-banner warn" role="alert">{editor.personSaveMessage}</div> : null}
          <form onSubmit={editor.onSubmitPerson} onInvalidCapture={revealInvalidProfileField} className="editor-form profile-form"><fieldset className="profile-fields" disabled={editor.personSaveState === "saving"}>
            <div className="editor-header profile-header">
              <div className="profile-heading">
                <button type="button" className="profile-back" onClick={() => navigate("/people")}>← Til personoversikt</button>
                <p className="eyebrow small">{!editor.persistedPersonId ? "Ny person" : `Person #${editor.persistedPersonId}`}</p>
                <h2>{editor.personDraft.full_name || "Ny person"}</h2>
                <p className="meta profile-scope">Endringer lagres når du velger Lagre person.</p>
              </div>
              <ProfileFormActions
                model="person" isNew={!editor.persistedPersonId}
                state={editor.personSaveState} dirty={editor.personDraftHasUnsavedChanges}
                disabled={!editor.tenantId || editor.personSaveBlocked}
              />
            </div>
            <ProfileValidationSummary errors={editor.personFieldErrors} />
            <div className="grid two">
              <Field label="Fullt navn" name="full_name" error={editor.personFieldErrors.full_name} required>
                <input
                  value={editor.personDraft.full_name}
                  onChange={(e) => editor.setPersonDraft((s) => ({ ...s, full_name: e.target.value }))}
                  required
                />
              </Field>
              <Field label="Tittel">
                <input
                  value={editor.personDraft.title ?? ""}
                  onChange={(e) => editor.setPersonDraft((s) => ({ ...s, title: e.target.value }))}
                  placeholder="f.eks. daglig leder, produsent eller booking"
                />
              </Field>
            </div>

            <div className="grid two">
              <Field label="Kommune">
                <input
                  value={editor.personDraft.municipality}
                  onChange={(e) => editor.setPersonDraft((s) => ({ ...s, municipality: e.target.value }))}
                />
              </Field>
            </div>

            <div className="grid two person-contact-groups">
              {(["EMAIL", "PHONE"] as const).map(type => <section key={type} className="person-contact-group" aria-label={type === "EMAIL" ? "E-postadresser" : "Telefonnumre"}>
                <h3>{type === "EMAIL" ? "E-post" : "Telefon"}</h3>
                {editor.personContactRows.filter(row => row.type === type).map((row, index) => row.removed ? <div className="contact-removal" key={row.key}><span>{row.value} · {row.deleted ? "er fjernet" : row.deleteUncertain ? "fjerning er ikke bekreftet; prøv lagring igjen med samme kontakt" : "fjernes ved lagring"}</span>{!row.deleted && !row.deleteUncertain ? <button type="button" className="table-link" onClick={() => editor.updatePersonContact(row.key, { removed: false })}>Angre fjerning</button> : null}</div> : <div key={row.key} className="person-contact-row">
                  <Field label={`${type === "EMAIL" ? "E-post" : "Telefon"}${index ? ` ${index + 1}` : ""}`} name={row.key} error={editor.personFieldErrors[row.key]}>
                    <div className={type === "PHONE" ? "contact-inline-input" : undefined}>
                      {type === "PHONE" ? <PhoneRegionSelect value={row.phone_region ?? ""} ariaLabel={`Land/region for telefon ${index + 1}`} onChange={phone_region => editor.updatePersonContact(row.key, { phone_region: phone_region || null })} /> : null}
                      <input type={type === "EMAIL" ? "email" : "tel"} value={row.value} onChange={event => editor.updatePersonContact(row.key, { value: event.target.value, ...(type === "PHONE" && event.target.value.trim().startsWith("+") ? { phone_region: null } : {}) })} />
                    </div>
                  </Field>
                  <div className="person-contact-options">
                    <label className="inline-check compact"><input type="checkbox" checked={row.is_public} onChange={event => editor.updatePersonContact(row.key, { is_public: event.target.checked })} /><span>Kan vises offentlig</span></label>
                    {(!row.id || editor.canDelete) && (!row.is_primary || row.id) ? <button type="button" className="table-link contact-remove" onClick={() => editor.updatePersonContact(row.key, { removed: true })}>Fjern</button> : null}
                  </div>
                </div>)}
                <button type="button" className="table-link add-contact" onClick={() => editor.addPersonContact(type)}>+ Legg til ekstra {type === "EMAIL" ? "e-post" : "telefon"}</button>
                {type === "PHONE" ? <small className="meta">Land/region brukes når et nasjonalt nummer endres. Nummer med + trenger ikke region.</small> : null}
              </section>)}
            </div>
            <p className="meta contact-public-context">Offentlige kontaktverdier vises bare på aktører der personen også er satt til «Vis person offentlig». {typeof editor.selectedPersonId === "number" ? `${publicPersonLinks} av ${selectedPersonLinks.length} aktørkoblinger viser personen offentlig.` : "Nye kontaktverdier er interne inntil du velger noe annet."}</p>

            <ProfileSection title="Internt notat" summary={editor.personDraft.note ? "Notat er lagt inn" : "Ingen notat"}>
            <Field label="Notat">
              <textarea
                rows={3}
                value={editor.personDraft.note ?? ""}
                onChange={(e) => editor.setPersonDraft((s) => ({ ...s, note: e.target.value }))}
              />
            </Field>

            </ProfileSection>
            <ProfileSection title="Kategorisering og tags" summary={editor.personTagInput || "Kategori, underkategori og tags"}>
            <CategorySelectFields
              title="Kategori og underkategori"
              description="Velg først en hovedkategori, og deretter en underkategori som hører til den."
              categories={editor.categories}
              subcategories={editor.subcategories}
              selectedCategoryIds={editor.personDraft.category_ids}
              selectedIds={editor.personDraft.subcategory_ids}
              onSelect={(categoryId, subcategoryId) =>
                editor.setPersonDraft((state) => ({
                  ...state,
                  category_ids: categoryId ? [categoryId] : [],
                  subcategory_ids: subcategoryId ? [subcategoryId] : [],
                }))
              }
            />

            <Field label="Tags">
              <input
                value={editor.personTagInput}
                onChange={(e) => editor.setPersonTagInput(e.target.value)}
                placeholder="f.eks. live, management, booking"
              />
              <TagSuggestions
                value={editor.personTagInput}
                tags={editor.tags}
                onSelect={(nextValue) => editor.setPersonTagInput(nextValue)}
              />
              <p className="muted" style={{ margin: "6px 0 0" }}>
                Skriv egne tags separert med komma. Maks 5 tags.
              </p>
            </Field>

            </ProfileSection>
            <ProfileSection title="Lenker og sosiale medier" summary={editor.personDraft.website_url || "Nettside og sosiale profiler"} errors={Object.entries(editor.personFieldErrors).filter(([key]) => key.endsWith("_url")).map(([,value]) => value)}>
            <div className="link-section">
              <div className="sidebar-header">
                <h2>Lenker og sosiale medier</h2>
                <span className="meta">Brukes i offentlig profil senere</span>
              </div>
              <div className="grid two">
                <Field label="Website URL" name="website_url" error={editor.personFieldErrors.website_url}>
                  <input
                    type="url"
                    value={editor.personDraft.website_url ?? ""}
                    onChange={(e) => editor.setPersonDraft((s) => ({ ...s, website_url: e.target.value }))}
                    placeholder="https://..."
                  />
                </Field>
                <Field label="Instagram URL" name="instagram_url" error={editor.personFieldErrors.instagram_url}>
                  <input
                    type="url"
                    value={editor.personDraft.instagram_url ?? ""}
                    onChange={(e) => editor.setPersonDraft((s) => ({ ...s, instagram_url: e.target.value }))}
                    placeholder="https://instagram.com/..."
                  />
                </Field>
              </div>
              <div className="grid two">
                <Field label="TikTok URL" name="tiktok_url" error={editor.personFieldErrors.tiktok_url}>
                  <input
                    type="url"
                    value={editor.personDraft.tiktok_url ?? ""}
                    onChange={(e) => editor.setPersonDraft((s) => ({ ...s, tiktok_url: e.target.value }))}
                    placeholder="https://tiktok.com/@..."
                  />
                </Field>
                <Field label="LinkedIn URL" name="linkedin_url" error={editor.personFieldErrors.linkedin_url}>
                  <input
                    type="url"
                    value={editor.personDraft.linkedin_url ?? ""}
                    onChange={(e) => editor.setPersonDraft((s) => ({ ...s, linkedin_url: e.target.value }))}
                    placeholder="https://linkedin.com/in/..."
                  />
                </Field>
              </div>
              <div className="grid two">
                <Field label="Facebook URL" name="facebook_url" error={editor.personFieldErrors.facebook_url}>
                  <input
                    type="url"
                    value={editor.personDraft.facebook_url ?? ""}
                    onChange={(e) => editor.setPersonDraft((s) => ({ ...s, facebook_url: e.target.value }))}
                    placeholder="https://facebook.com/..."
                  />
                </Field>
                <Field label="YouTube URL" name="youtube_url" error={editor.personFieldErrors.youtube_url}>
                  <input
                    type="url"
                    value={editor.personDraft.youtube_url ?? ""}
                    onChange={(e) => editor.setPersonDraft((s) => ({ ...s, youtube_url: e.target.value }))}
                    placeholder="https://youtube.com/..."
                  />
                </Field>
              </div>
            </div>

            </ProfileSection>
            <div className="actions profile-bottom-actions">
              <ProfileFormActions model="person" isNew={!editor.persistedPersonId} state={editor.personSaveState} dirty={editor.personDraftHasUnsavedChanges} disabled={!editor.tenantId || editor.personSaveBlocked} />
              <button
                type="button"
                className="link-delete"
                onClick={() => {
                  if (window.confirm("Slette valgt person? Dette kan påvirke koblinger og kontakter.")) {
                    editor.onDeletePerson();
                  }
                }}
                disabled={typeof editor.selectedPersonId !== "number" || !editor.canDelete || editor.personSaveState === "saving"}
              >
                Slett person
              </button>
            </div>
          </fieldset></form>

        </>
      )}
    </section>
  );
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

function getPersonPrimaryLink(person: {
  website_url: string | null;
  instagram_url: string | null;
  tiktok_url: string | null;
  linkedin_url: string | null;
  facebook_url: string | null;
  youtube_url: string | null;
}) {
  return (
    person.website_url ||
    person.instagram_url ||
    person.tiktok_url ||
    person.linkedin_url ||
    person.facebook_url ||
    person.youtube_url ||
    null
  );
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

function getPersonLinkRows(person: {
  website_url: string | null;
  instagram_url: string | null;
  tiktok_url: string | null;
  linkedin_url: string | null;
  facebook_url: string | null;
  youtube_url: string | null;
}) {
  return [
    { label: "Nettside", href: person.website_url },
    { label: "Instagram", href: person.instagram_url },
    { label: "TikTok", href: person.tiktok_url },
    { label: "LinkedIn", href: person.linkedin_url },
    { label: "Facebook", href: person.facebook_url },
    { label: "YouTube", href: person.youtube_url },
  ].filter((link): link is { label: string; href: string } => Boolean(link.href));
}

function truncateLink(value: string) {
  return value.length > 38 ? `${value.slice(0, 35)}...` : value;
}

function matchesPersonFilters(input: {
  person: {
    full_name: string;
    title?: string | null;
    email: string | null;
    phone: string | null;
    municipality: string;
    note: string | null;
    tags: Array<{ slug: string; name: string }>;
    categories: Array<{ slug: string; name: string }>;
    subcategories: Array<{ slug: string; name: string }>;
  };
  query: string;
  categorySlug: string;
  subcategorySlug: string;
  tagSlug: string;
}) {
  const { person, query, categorySlug, subcategorySlug, tagSlug } = input;
  const normalizedQuery = query.trim().toLowerCase();
  if (categorySlug && !person.categories.some((category) => category.slug === categorySlug)) {
    return false;
  }
  if (subcategorySlug && !person.subcategories.some((subcategory) => subcategory.slug === subcategorySlug)) {
    return false;
  }
  if (tagSlug && !person.tags.some((tag) => tag.slug === tagSlug)) {
    return false;
  }
  if (!normalizedQuery) return true;

  const haystack = [
    person.full_name,
    person.title ?? "",
    person.email ?? "",
    person.phone ?? "",
    person.municipality ?? "",
    person.note ?? "",
    ...person.tags.map((tag) => tag.name),
    ...person.categories.map((category) => category.name),
    ...person.subcategories.map((subcategory) => subcategory.name),
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
