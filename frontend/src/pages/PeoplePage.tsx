import { Field } from "../components/Field";
import { useEditor } from "../context/EditorContext";
import { saveLabel } from "../editor-utils";
import { useRouteSyncedSelection } from "../hooks/useRouteSyncedSelection";

const CATEGORY_ORDER = [
  "Musikk",
  "Film",
  "Kunst & Design",
  "Scenekunst",
  "Kreativ teknologi",
  "Litteratur",
] as const;

const SUBCATEGORY_ORDER = [
  "Artister & Band",
  "Konsertarrangører",
  "Musikere",
  "Musikkbransjen",
  "Produsent",
  "Regi & Manus",
  "Foto/ Lys",
  "Filmlyd",
  "Filmproduksjon",
  "Visuell kunst",
  "Grafisk design",
  "Klesdesign",
  "Teater",
  "Dans",
] as const;

export function PeoplePage() {
  const editor = useEditor();
  const { navigate, paramValue: personId } = useRouteSyncedSelection({
    routeParam: "personId",
    basePath: "/people",
    selectedId: editor.selectedPersonId,
    setSelectedId: editor.setSelectedPersonId,
  });

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

  return (
    <section className="people-workspace">
      <PeopleSidebar navigate={navigate} />
      <PeopleEditorPanel navigate={navigate} personId={personId} invalidPersonRoute={invalidPersonRoute} />
    </section>
  );
}

function PeopleSidebar({ navigate }: { navigate: (to: string) => void }) {
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
      <div className="people-sidebar-actions">
        <input
          className="search-input"
          placeholder="Søk navn, e-post, telefon..."
          value={editor.personQuery}
          onChange={(e) => editor.setPersonQuery(e.target.value)}
        />
        <button
          type="button"
          className="ghost-button"
          onClick={() => {
            editor.setSelectedPersonId("new");
            navigate("/people/new");
          }}
          disabled={!editor.tenantId}
        >
          Ny person
        </button>
      </div>
      <div className="list">
        {editor.tenantDataLoading ? <div className="loading-state">Laster personer...</div> : null}
        {editor.visiblePersons.map((person) => (
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
        {!editor.tenantDataLoading && editor.visiblePersons.length === 0 ? (
          <div className="empty-state">Ingen personer funnet.</div>
        ) : null}
      </div>
    </aside>
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

          <PersonContactsPanel />
        </>
      )}
    </section>
  );
}

function PersonContactsPanel() {
  const editor = useEditor();
  return (
    <div className="link-section">
      <div className="sidebar-header">
        <h2>Kontaktkanaler for valgt person</h2>
        <span className="meta">{editor.personContacts.length} registrert</span>
      </div>
      <p className="muted">
        Her legger du inn faktiske kontaktkanaler for personen. <strong>Primær</strong> betyr foretrukket
        kanal av den typen. <strong>Public</strong> betyr at kanalen kan vises på offentlig aktørside/API.
      </p>

      {typeof editor.selectedPersonId === "number" ? (
        <>
          {editor.personContactsLoading ? <div className="loading-state compact">Laster kontakter...</div> : null}
          <form className="contact-create" onSubmit={editor.onCreateContact}>
            <select
              value={editor.contactDraft.type}
              onChange={(e) =>
                editor.setContactDraft((s) => ({ ...s, type: e.target.value as "EMAIL" | "PHONE" }))
              }
            >
              <option value="EMAIL">EMAIL</option>
              <option value="PHONE">PHONE</option>
            </select>
            <input
              className={editor.contactFieldErrors.value ? "input-error" : undefined}
              placeholder="verdi (epost eller telefon)"
              value={editor.contactDraft.value}
              onChange={(e) => editor.setContactDraft((s) => ({ ...s, value: e.target.value }))}
            />
            {editor.contactFieldErrors.value ? (
              <span className="field-error inline">{editor.contactFieldErrors.value}</span>
            ) : null}
            <label className="inline-check compact">
              <input
                type="checkbox"
                checked={editor.contactDraft.is_primary}
                onChange={(e) => editor.setContactDraft((s) => ({ ...s, is_primary: e.target.checked }))}
              />
              <span>Primær</span>
            </label>
            <label className="inline-check compact">
              <input
                type="checkbox"
                checked={editor.contactDraft.is_public}
                onChange={(e) => editor.setContactDraft((s) => ({ ...s, is_public: e.target.checked }))}
              />
              <span>Public</span>
            </label>
            <button type="submit" className="ghost-button" disabled={!editor.contactDraft.value.trim()}>
              Legg til kontakt
            </button>
          </form>

          <div className="link-list">
            {editor.personContacts.map((contact) => (
              <div key={contact.id} className="link-row">
                <div>
                  <div className="link-person">
                    {contact.type} · {contact.value}
                  </div>
                  <div className="meta">
                    {contact.is_primary ? "Primær" : "Sekundær"} · {contact.is_public ? "Public" : "Intern"}
                  </div>
                </div>

                <div className="link-controls">
                  <select
                    value={contact.type}
                    onChange={(e) => editor.updateContact(contact.id, { type: e.target.value as "EMAIL" | "PHONE" })}
                  >
                    <option value="EMAIL">EMAIL</option>
                    <option value="PHONE">PHONE</option>
                  </select>
                  <input
                    className="contact-inline-input"
                    value={contact.value}
                    onChange={(e) =>
                      editor.setPersonContacts((current) =>
                        current.map((c) => (c.id === contact.id ? { ...c, value: e.target.value } : c)),
                      )
                    }
                    onBlur={(e) => {
                      const next = e.target.value.trim();
                      if (next) editor.updateContact(contact.id, { value: next });
                    }}
                  />
                  <label className="inline-check compact">
                    <input
                      type="checkbox"
                      checked={contact.is_primary}
                      onChange={(e) => editor.updateContact(contact.id, { is_primary: e.target.checked })}
                    />
                    <span>Primær</span>
                  </label>
                  <label className="inline-check compact">
                    <input
                      type="checkbox"
                      checked={contact.is_public}
                      onChange={(e) => editor.updateContact(contact.id, { is_public: e.target.checked })}
                    />
                    <span>Public</span>
                  </label>
                  <button
                    type="button"
                    className="link-delete"
                    onClick={() => {
                      if (window.confirm(`Slette kontakt ${contact.type} · ${contact.value}?`)) {
                        editor.removeContact(contact.id);
                      }
                    }}
                  >
                    Fjern
                  </button>
                </div>
              </div>
            ))}
            {!editor.personContactsLoading && editor.personContacts.length === 0 ? (
              <div className="empty-state">Ingen kontakter registrert for valgt person.</div>
            ) : null}
          </div>
        </>
      ) : (
        <div className="empty-state">Velg eller opprett en person for å administrere kontakter.</div>
      )}
    </div>
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
  categories: Array<{ id: number; name: string }>;
  subcategories: Array<{ id: number; name: string; category: { id: number; name: string } }>;
  selectedCategoryIds: number[];
  selectedIds: number[];
  onSelect: (categoryId: number | null, subcategoryId: number | null) => void;
}) {
  const { title, description, categories, subcategories, selectedCategoryIds, selectedIds, onSelect } = props;
  const categoryPositions = new Map<string, number>(CATEGORY_ORDER.map((name, index) => [name, index]));
  const subcategoryPositions = new Map<string, number>(SUBCATEGORY_ORDER.map((name, index) => [name, index]));
  const allowedCategoryNames = new Set<string>(CATEGORY_ORDER);
  const allowedSubcategoryNames = new Set<string>(SUBCATEGORY_ORDER);
  const selectedSubcategoryId = selectedIds[0] ?? null;
  const selectedSubcategory =
    selectedSubcategoryId !== null ? subcategories.find((item) => item.id === selectedSubcategoryId) ?? null : null;
  const selectedCategoryId = selectedCategoryIds[0] ?? selectedSubcategory?.category.id ?? null;

  const sortedCategories = [...categories]
    .filter((category) => allowedCategoryNames.has(category.name))
    .sort(
    (left, right) =>
      (categoryPositions.get(left.name) ?? Number.MAX_SAFE_INTEGER) -
        (categoryPositions.get(right.name) ?? Number.MAX_SAFE_INTEGER) || left.name.localeCompare(right.name),
  );

  const availableSubcategories =
    selectedCategoryId === null
      ? []
      : subcategories
          .filter((item) => item.category.id === selectedCategoryId && allowedSubcategoryNames.has(item.name))
          .sort(
            (left, right) =>
              (subcategoryPositions.get(left.name) ?? Number.MAX_SAFE_INTEGER) -
                (subcategoryPositions.get(right.name) ?? Number.MAX_SAFE_INTEGER) || left.name.localeCompare(right.name),
          );

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
