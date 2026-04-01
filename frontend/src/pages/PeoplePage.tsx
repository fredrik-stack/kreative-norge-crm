import { useMemo } from "react";
import { Field } from "../components/Field";
import { useEditor } from "../context/EditorContext";
import { filterSubcategoriesForCategory, sortedCategories as sortCategoriesByTaxonomy } from "../editorTaxonomy";
import { saveLabel } from "../editor-utils";
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

  if (inOverviewMode) {
    return (
      <main className="editor-overview-layout">
        <PeopleOverviewPanel persons={editor.filteredOverviewPersons} navigate={navigate} filterSummary={filterSummary} />
      </main>
    );
  }

  return (
    <section className="people-workspace">
      <PeopleSidebar navigate={navigate} persons={editor.persons} />
      <PeopleEditorPanel navigate={navigate} personId={personId} invalidPersonRoute={invalidPersonRoute} />
    </section>
  );
}

function PeopleSidebar(props: {
  navigate: (to: string) => void;
  persons: ReturnType<typeof useEditor>["persons"];
}) {
  const { navigate, persons } = props;
  const editor = useEditor();
  return (
    <aside className="panel people-sidebar">
      <div className="sidebar-header">
        <h2>Personer</h2>
        <span className="meta">
          {editor.persons.length} stk
          {editor.peopleHasUnsavedChanges ? " · ulagret" : ""}
        </span>
      </div>
      <div className="list">
        {editor.tenantDataLoading ? <div className="loading-state">Laster personer...</div> : null}
        {persons.map((person) => (
          <button
            key={person.id}
            type="button"
            className={`list-item ${editor.selectedPersonId === person.id ? "active" : ""}`}
            onClick={() => {
              editor.setSelectedPersonId(person.id);
              navigate(`/people/${person.id}`);
            }}
          >
            <div className="list-item-title">{person.full_name}</div>
            <div className="list-item-sub">
              <span>{person.email || person.phone || "Ingen kontakt"}</span>
              <span>{person.municipality || "Ingen kommune"}</span>
            </div>
          </button>
        ))}
        {!editor.tenantDataLoading && persons.length === 0 ? (
          <div className="empty-state">Ingen personer funnet.</div>
        ) : null}
      </div>
    </aside>
  );
}

function PeopleOverviewPanel(props: {
  persons: ReturnType<typeof useEditor>["persons"];
  navigate: (to: string) => void;
  filterSummary: string | null;
}) {
  const { persons, navigate, filterSummary } = props;
  const editor = useEditor();
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

  return (
    <section className="panel overview-panel">
      <div className="sidebar-header">
        <div>
          <p className="eyebrow small">Oversikt</p>
          <h2>Personer</h2>
        </div>
        <span className="meta">{persons.length} synlige</span>
      </div>
      <p className="muted">
        Her ser du alle personer i en tabellvisning som gjør det enklere å skanne mange navn, organisasjoner og kontaktpunkter.
      </p>
      {filterSummary ? <div className="filter-summary">{filterSummary}</div> : null}
      <div className="overview-table-wrap">
        <table className="overview-table">
          <thead>
            <tr>
              <th>Navn</th>
              <th>Tittel</th>
              <th>Organisasjon / bedrift</th>
              <th>Primærlenke</th>
              <th>E-post</th>
              <th>Telefon</th>
              <th>Kommune</th>
              <th>Kategori</th>
              <th>Tags</th>
            </tr>
          </thead>
          <tbody>
            {persons.map((person) => {
              const linkedOrganizations = linkedOrganizationsByPersonId.get(person.id) ?? [];
              const primaryLink = getPersonPrimaryLink(person);
              return (
                <tr key={person.id}>
                  <td>
                    <button
                      type="button"
                      className="table-link"
                      onClick={() => {
                        editor.setSelectedPersonId(person.id);
                        navigate(`/people/${person.id}`);
                      }}
                    >
                      {person.full_name}
                    </button>
                  </td>
                  <td>
                    <span className="meta">—</span>
                  </td>
                  <td>
                    {linkedOrganizations.length > 0 ? (
                      <div className="table-linked-items">
                        {linkedOrganizations.map((organization) => (
                          <button
                            key={`${person.id}-${organization.id}`}
                            type="button"
                            className="table-link secondary"
                            onClick={() => {
                              editor.setSelectedOrgId(organization.id);
                              navigate(`/organizations/${organization.id}`);
                            }}
                          >
                            {organization.name}
                          </button>
                        ))}
                      </div>
                    ) : (
                      <span className="meta">Ikke knyttet til aktør</span>
                    )}
                  </td>
                  <td>
                    {primaryLink ? (
                      <a href={primaryLink} target="_blank" rel="noreferrer">
                        {truncateLink(primaryLink)}
                      </a>
                    ) : (
                      <span className="meta">—</span>
                    )}
                  </td>
                  <td>{person.email ? <a href={`mailto:${person.email}`}>{person.email}</a> : "—"}</td>
                  <td>{person.phone || "—"}</td>
                  <td>{person.municipality || "—"}</td>
                  <td>{formatPersonCategoryLabel(person)}</td>
                  <td>{person.tags && person.tags.length > 0 ? person.tags.map((tag) => tag.name).join(", ") : "—"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {persons.length === 0 ? <div className="empty-state">Ingen personer matcher filtreringen.</div> : null}
    </section>
  );
}

function PeopleEditorPanel(props: {
  navigate: (to: string) => void;
  personId: string | undefined;
  invalidPersonRoute: boolean;
}) {
  const { navigate, personId, invalidPersonRoute } = props;
  const editor = useEditor();

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
          {editor.peopleHasUnsavedChanges ? (
            <div className="inline-banner warn">Du har ulagrede endringer i personskjemaet.</div>
          ) : null}
          {editor.personLastSavedAt && !editor.peopleHasUnsavedChanges ? (
            <div className="inline-banner success">Sist lagret {formatTime(editor.personLastSavedAt)}</div>
          ) : null}
          <div className="editor-header">
            <div>
              <p className="eyebrow small">
                {editor.selectedPersonId === "new" ? "Ny person" : `Person #${editor.selectedPersonId ?? "-"}`}
              </p>
              <h2>{editor.personDraft.full_name || "Person"}</h2>
            </div>
            <div className={`save-pill ${editor.personSaveState}`}>{saveLabel(editor.personSaveState)}</div>
          </div>

          <form onSubmit={editor.onSubmitPerson} className="editor-form">
            <div className="grid two">
              <Field label="Fullt navn" required>
                <input
                  value={editor.personDraft.full_name}
                  onChange={(e) => editor.setPersonDraft((s) => ({ ...s, full_name: e.target.value }))}
                  required
                />
              </Field>
              <Field label="Kommune">
                <input
                  value={editor.personDraft.municipality}
                  onChange={(e) => editor.setPersonDraft((s) => ({ ...s, municipality: e.target.value }))}
                />
              </Field>
            </div>

            <div className="grid two">
              <Field label="E-post" error={editor.personFieldErrors.email}>
                <input
                  type="email"
                  value={editor.personDraft.email ?? ""}
                  onChange={(e) => editor.setPersonDraft((s) => ({ ...s, email: e.target.value }))}
                />
              </Field>
              <Field label="Telefon" error={editor.personFieldErrors.phone}>
                <input
                  value={editor.personDraft.phone ?? ""}
                  onChange={(e) => editor.setPersonDraft((s) => ({ ...s, phone: e.target.value }))}
                />
              </Field>
            </div>

            <Field label="Notat">
              <textarea
                rows={3}
                value={editor.personDraft.note ?? ""}
                onChange={(e) => editor.setPersonDraft((s) => ({ ...s, note: e.target.value }))}
              />
            </Field>

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
              <p className="muted" style={{ margin: "6px 0 0" }}>
                Skriv egne tags separert med komma. Maks 5 tags.
              </p>
            </Field>

            <div className="link-section">
              <div className="sidebar-header">
                <h2>Lenker og sosiale medier</h2>
                <span className="meta">Brukes i offentlig profil senere</span>
              </div>
              <div className="grid two">
                <Field label="Website URL" error={editor.personFieldErrors.website_url}>
                  <input
                    type="url"
                    value={editor.personDraft.website_url ?? ""}
                    onChange={(e) => editor.setPersonDraft((s) => ({ ...s, website_url: e.target.value }))}
                    placeholder="https://..."
                  />
                </Field>
                <Field label="Instagram URL" error={editor.personFieldErrors.instagram_url}>
                  <input
                    type="url"
                    value={editor.personDraft.instagram_url ?? ""}
                    onChange={(e) => editor.setPersonDraft((s) => ({ ...s, instagram_url: e.target.value }))}
                    placeholder="https://instagram.com/..."
                  />
                </Field>
              </div>
              <div className="grid two">
                <Field label="TikTok URL" error={editor.personFieldErrors.tiktok_url}>
                  <input
                    type="url"
                    value={editor.personDraft.tiktok_url ?? ""}
                    onChange={(e) => editor.setPersonDraft((s) => ({ ...s, tiktok_url: e.target.value }))}
                    placeholder="https://tiktok.com/@..."
                  />
                </Field>
                <Field label="LinkedIn URL" error={editor.personFieldErrors.linkedin_url}>
                  <input
                    type="url"
                    value={editor.personDraft.linkedin_url ?? ""}
                    onChange={(e) => editor.setPersonDraft((s) => ({ ...s, linkedin_url: e.target.value }))}
                    placeholder="https://linkedin.com/in/..."
                  />
                </Field>
              </div>
              <div className="grid two">
                <Field label="Facebook URL" error={editor.personFieldErrors.facebook_url}>
                  <input
                    type="url"
                    value={editor.personDraft.facebook_url ?? ""}
                    onChange={(e) => editor.setPersonDraft((s) => ({ ...s, facebook_url: e.target.value }))}
                    placeholder="https://facebook.com/..."
                  />
                </Field>
                <Field label="YouTube URL" error={editor.personFieldErrors.youtube_url}>
                  <input
                    type="url"
                    value={editor.personDraft.youtube_url ?? ""}
                    onChange={(e) => editor.setPersonDraft((s) => ({ ...s, youtube_url: e.target.value }))}
                    placeholder="https://youtube.com/..."
                  />
                </Field>
              </div>
            </div>

            <div className="actions">
              <button
                type="submit"
                className="primary-button"
                disabled={!editor.tenantId || editor.personSaveState === "saving"}
              >
                {editor.selectedPersonId === "new" ? "Opprett person" : "Lagre person"}
              </button>
              <button type="button" className="ghost-button" onClick={editor.onResetPersonDraft}>
                Nullstill
              </button>
              <button
                type="button"
                className="link-delete"
                onClick={() => {
                  if (window.confirm("Slette valgt person? Dette kan påvirke koblinger og kontakter.")) {
                    editor.onDeletePerson();
                  }
                }}
                disabled={typeof editor.selectedPersonId !== "number"}
              >
                Slett person
              </button>
            </div>
          </form>

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

function truncateLink(value: string) {
  return value.length > 38 ? `${value.slice(0, 35)}...` : value;
}

function formatPersonCategoryLabel(person: {
  categories?: Array<{ name: string }>;
  subcategories?: Array<{ name: string }>;
}) {
  const category = person.categories?.[0]?.name;
  const subcategory = person.subcategories?.[0]?.name;
  if (category && subcategory) return `${category} > ${subcategory}`;
  if (category) return category;
  if (subcategory) return subcategory;
  return "—";
}

function matchesPersonFilters(input: {
  person: {
    full_name: string;
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
