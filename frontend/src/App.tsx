import { AccessManagementPage } from "./pages/AccessManagementPage";
import { getManagementContext } from "./api";
import type { AuthSession } from "./api";
import { useEffect, useMemo, useState } from "react";
import {
  Link,
  NavLink,
  Navigate,
  Route,
  RouterProvider,
  Routes,
  createBrowserRouter,
  useLocation,
  useNavigate,
} from "react-router-dom";
import { AuthGate } from "./components/AuthGate";
import { EditorIcon } from "./components/EditorIcon";
import { ConfirmNavigationModal } from "./components/ConfirmNavigationModal";
import { useUnsavedChangesGuard } from "./hooks/useUnsavedChangesGuard";
import { EditorProvider } from "./context/EditorContext";
import { OrganizationsPage } from "./pages/OrganizationsPage";
import { PeoplePage } from "./pages/PeoplePage";
import { ImportExportPage } from "./pages/ImportExportPage";
import { useEditorData } from "./hooks/useEditorData";
import { filterSubcategoriesForCategory, sortedCategories } from "./editorTaxonomy";

export default function App() {
  const router = useMemo(() => createBrowserRouter([{ path: "*", element: <AppShell /> }]), []);
  return <RouterProvider router={router} future={{ v7_startTransition: true }} />;
}

function AppShell() {
  return <AuthGate>{({ username, user, onLogout }) => <EditorShell username={username} user={user} onLogout={onLogout} />}</AuthGate>;
}

function EditorShell({ username, user, onLogout }: { username: string; user: AuthSession["user"]; onLogout: () => void }) {
  const editor = useEditorData();
  const [managementEnabled, setManagementEnabled] = useState(false);
  useEffect(() => { let active = true;
    getManagementContext().then(value => {if (active) setManagementEnabled(value.enabled);}).catch(() => {});
    return () => {active = false;};
  }, []);
  const location = useLocation();
  const navigate = useNavigate();
  const isOrganizationsOverview = location.pathname === "/organizations" || location.pathname === "/";
  const isPeopleOverview = location.pathname === "/people";
  const onOverviewPage = isOrganizationsOverview || isPeopleOverview;
  const onPeoplePage = location.pathname.startsWith("/people");
  const onOrganizationsPage = location.pathname.startsWith("/organizations");
  const [overviewTagQuery, setOverviewTagQuery] = useState("");
  const [tagSearchFocused, setTagSearchFocused] = useState(false);
  const [tagChoiceIsExplicit, setTagChoiceIsExplicit] = useState(false);
  const overviewEntityLabel = isPeopleOverview ? "personer" : "aktører";
  const overviewFilterSummary = buildEditorOverviewFilterSummary({
    entityLabel: overviewEntityLabel,
    query: editor.overviewQuery,
    categorySlug: editor.overviewCategorySlug,
    subcategorySlug: editor.overviewSubcategorySlug,
    tagLabel: editor.overviewTagLabel,
  });
  const dirtySummary = useMemo(() => {
    const items: string[] = [];
    if (onOrganizationsPage && editor.organizationHasUnsavedChanges) items.push("Aktørskjema");
    if (onPeoplePage && editor.personDraftHasUnsavedChanges) items.push("Personskjema");
    if (onPeoplePage && editor.contactDraftHasUnsavedChanges) items.push("Ny kontakt (ikke lagret)");
    return items;
  }, [
    editor.contactDraftHasUnsavedChanges,
    editor.organizationHasUnsavedChanges,
    editor.personDraftHasUnsavedChanges,
    onOrganizationsPage,
    onPeoplePage,
  ]);
  const unsavedGuard = useUnsavedChangesGuard({
    hasUnsavedChanges: onPeoplePage
      ? editor.peopleHasUnsavedChanges
      : onOrganizationsPage
        ? editor.organizationHasUnsavedChanges
        : editor.hasUnsavedChanges,
    tenants: editor.tenants,
    dirtySummary,
    applyTenantSelection: editor.applyTenantSelection,
    saveAllPendingChanges: editor.saveAllPendingChanges,
    discardAllPendingChanges: editor.discardAllPendingChanges,
    isSaving: editor.saveState === "saving" || editor.personSaveState === "saving" || editor.organizationDeleting,
  });

  const goToEditorHome = () => {
    resetOverviewFilters();
    navigate("/organizations");
  };

  useEffect(() => {
    if (editor.tenantDataLoaded && !editor.canImportExport && ["/import", "/export", "/import-export"].includes(location.pathname)) {
      navigate("/organizations", { replace: true });
    }
  }, [editor.canImportExport, editor.tenantDataLoaded, location.pathname, navigate]);

  useEffect(() => {
    setOverviewTagQuery("");
    setTagSearchFocused(false);
    setTagChoiceIsExplicit(false);
  }, [editor.tenantId]);

  useEffect(() => {
    if (tagChoiceIsExplicit) return;
    const raw = overviewTagQuery.trim().toLocaleLowerCase("nb");
    const matches = editor.overviewTagChoices.filter(tag => tag.name.toLocaleLowerCase("nb") === raw);
    editor.setOverviewTagKey(matches.length === 1 ? matches[0].key : "");
  }, [overviewTagQuery, editor.overviewTagChoices, editor.setOverviewTagKey, tagChoiceIsExplicit]);

  const overviewTagSuggestions = useMemo(() => {
    const query = overviewTagQuery.trim().toLocaleLowerCase("nb");
    if (!query) return [];
    return editor.overviewTagChoices
      .filter(tag => tag.name.toLocaleLowerCase("nb").includes(query))
      .slice(0, 8);
  }, [overviewTagQuery, editor.overviewTagChoices]);
  function resetOverviewFilters() {
    setOverviewTagQuery("");
    setTagSearchFocused(false);
    setTagChoiceIsExplicit(false);
    editor.resetOverviewFilters();
  }
  const initials = (user?.display_name || username).split(/\s+/).map(part => part[0]).slice(0, 2).join("").toUpperCase();

  return (
    <div className="app-shell editor-shell compact-editor">
      <aside className="editor-sidebar" aria-label="Editor-meny">
        <header className="editor-brand-header">
          <Link to="/organizations" className="editor-brand"><strong>Editor CRM</strong></Link>
          <div className="editor-mobile-session"><span className="user-initials" aria-hidden="true">{initials}</span><button type="button" className="editor-logout-icon" aria-label="Logg ut" title="Logg ut" onClick={() => unsavedGuard.requestAction("Logg ut", onLogout)}><EditorIcon name="logout" /></button></div>
        </header>
        <nav className={`editor-nav${editor.canImportExport ? "" : " read-only-nav"}`} aria-label="Hovednavigasjon">
          <NavLink to="/organizations" className={({isActive}) => `nav-link ${isActive ? "active" : ""}`}><EditorIcon name="actors" />Aktører</NavLink>
          <NavLink to="/people" className={({isActive}) => `nav-link ${isActive ? "active" : ""}`}><EditorIcon name="people" />Personer</NavLink>
          {editor.canImportExport ? <>
            <NavLink to="/import" className={({isActive}) => `nav-link ${isActive || location.pathname === "/import-export" ? "active" : ""}`}><EditorIcon name="import" />Import</NavLink>
            <NavLink to="/export" className={({isActive}) => `nav-link ${isActive ? "active" : ""}`}><EditorIcon name="export" />Eksport</NavLink>
          </> : null}
          {managementEnabled ? <NavLink to="/access" className="nav-link">Tilgang og avtale</NavLink> : null}
          <button type="button" className="nav-link nav-unavailable" disabled title="Kart er ikke tilgjengelig ennå"><EditorIcon name="map" />Kart</button>
          {user?.can_access_admin ? <a href="/admin/" className="nav-link editor-admin-link" onClick={event => { event.preventDefault(); unsavedGuard.requestAction("Admin", () => window.location.assign("/admin/")); }}><EditorIcon name="admin" />Admin</a> : null}
        </nav>
        <div className="editor-user-panel">
          <div className="editor-user-heading"><span className="user-initials" aria-hidden="true">{initials}</span><div><strong>{user?.display_name || username}</strong>{user?.is_superuser ? <small>Plattform-superbruker</small> : null}<small>{({superadmin:"Superadmin",gruppeadmin:"Gruppeadmin",redigerer:"Redigerer",leser:"Leser"} as Record<string,string>)[editor.currentTenantRole ?? ""] ?? "Ingen tenanttilgang"} i aktivt kontor</small></div></div>
          <label className="field-label" htmlFor="tenant-select">Aktivt Musikkontor</label>
          <select id="tenant-select" value={editor.tenantId ?? ""} onChange={event => unsavedGuard.requestTenantSelection(Number(event.target.value) || null)}>
            {editor.tenants.length === 0 ? <option value="">Ingen kontor</option> : null}
            {editor.tenants.map(tenant => <option key={tenant.id} value={tenant.id}>{tenant.name}</option>)}
          </select>
          <button type="button" className="table-link logout-button" onClick={() => unsavedGuard.requestAction("Logg ut", onLogout)}>Logg ut</button>
        </div>
      </aside>
      <div className="editor-main">
      {onOverviewPage ? <section className="overview-tools" aria-label={isPeopleOverview ? "Søk og filtrer personer" : "Søk og filtrer aktører"}>
          {onOverviewPage ? (
            <div className="hero-controls">
              <input
                className="search-input"
                type="search"
                aria-label={isPeopleOverview ? "Søk personer" : "Søk aktører"}
                placeholder={isPeopleOverview ? "Søk personer, aktører, kontaktinfo eller sted" : "Søk navn, sted, kategori eller tag"}
                value={editor.overviewQuery}
                onChange={(e) => editor.setOverviewQuery(e.target.value)}
              />
              <div className="hero-filter-grid">
                <select
                  aria-label="Hovedkategori"
                  className="overview-select"
                  value={editor.overviewCategorySlug}
                  onChange={(e) => {
                    editor.setOverviewCategorySlug(e.target.value);
                    editor.setOverviewSubcategorySlug("");
                  }}
                >
                  <option value="">Alle hovedkategorier</option>
                  {sortedCategories(editor.categories).map((category) => (
                    <option key={category.id} value={category.slug}>
                      {category.name}
                    </option>
                  ))}
                </select>
                <select
                  className="overview-select"
                  aria-label="Underkategori"
                  value={editor.overviewSubcategorySlug}
                  onChange={(e) => editor.setOverviewSubcategorySlug(e.target.value)}
                  disabled={!editor.overviewCategorySlug}
                >
                  <option value="">
                    {editor.overviewCategorySlug ? "Alle underkategorier" : "Velg hovedkategori først"}
                  </option>
                  {filterSubcategoriesForCategory(editor.subcategories, editor.overviewCategorySlug).map((subcategory) => (
                    <option key={subcategory.id} value={subcategory.slug}>
                      {subcategory.name}
                    </option>
                  ))}
                </select>
                <div className="overview-tag-search" onBlur={event => {
                  if (!event.currentTarget.contains(event.relatedTarget)) setTagSearchFocused(false);
                }}>
                  <input
                    className="search-input"
                    value={overviewTagQuery}
                    aria-label="Søk tag"
                    disabled={!editor.tenantDataLoaded || editor.tenantDataLoading || Boolean(editor.tenantDataError)}
                    placeholder="Søk tag"
                    onFocus={() => setTagSearchFocused(true)}
                    onChange={(e) => {
                      const nextValue = e.target.value;
                      setTagSearchFocused(true);
                      setOverviewTagQuery(nextValue);
                      setTagChoiceIsExplicit(false);
                    }}
                  />
                  {tagSearchFocused && overviewTagSuggestions.length > 0 ? (
                    <div className="overview-tag-suggestions" role="listbox" aria-label="Tag-forslag">
                      {overviewTagSuggestions.map((tag) => (
                        <button
                          key={tag.key}
                          type="button"
                          className="overview-tag-suggestion"
                          onMouseDown={(event) => event.preventDefault()}
                          onClick={() => {
                            setOverviewTagQuery(tag.name);
                            setTagChoiceIsExplicit(true);
                            editor.setOverviewTagKey(tag.key);
                            setTagSearchFocused(false);
                          }}
                        >
                          <span>{tag.name}</span>
                          <span className={`mini-pill ${tag.kind === "internal" ? "internal-tag" : "tag"}`}>{tag.kind === "internal" ? "Intern tag" : "Tag"}</span>
                        </button>
                      ))}
                    </div>
                  ) : null}
                </div>
              </div>
              {overviewFilterSummary ? <div className="filter-summary">{overviewFilterSummary}</div> : null}
              <div className="hero-actions">
                {editor.canWrite ? (
                  <button
                    type="button"
                    className="primary-button"
                    onClick={() => {
                      if (isPeopleOverview) {
                        editor.startNewPerson();
                        editor.setSelectedPersonId("new");
                        navigate("/people/new");
                        return;
                      }
                      editor.setSelectedOrgId("new");
                      navigate("/organizations/new");
                    }}
                  >
                    {isPeopleOverview ? "Ny person" : "Ny aktør"}
                  </button>
                ) : null}
                <button type="button" className="ghost-button" onClick={resetOverviewFilters}>
                  Nullstill filtre
                </button>
              </div>
            </div>
          ) : null}

      </section> : null}

      {editor.error ? <div className="banner error">{editor.error}</div> : null}

      <EditorProvider value={editor}>
        <Routes>
          <Route path="/access" element={<AccessManagementPage username={username} />} />
          <Route path="/" element={<Navigate to="/organizations" replace />} />
          <Route path="/organizations" element={<OrganizationsPage />} />
          <Route path="/organizations/:orgId" element={<OrganizationsPage />} />
          <Route path="/people" element={<PeoplePage />} />
          <Route path="/people/:personId" element={<PeoplePage />} />
          <Route path="/import-export" element={editor.canImportExport ? <ImportExportPage mode="import" /> : null} />
          <Route path="/import" element={editor.canImportExport ? <ImportExportPage mode="import" /> : null} />
          <Route path="/export" element={editor.canImportExport ? <ImportExportPage mode="export" /> : null} />
        </Routes>
      </EditorProvider>

      </div>
      <ConfirmNavigationModal {...unsavedGuard.modal} />
    </div>
  );
}

function buildEditorOverviewFilterSummary(input: {
  entityLabel: string;
  query: string;
  categorySlug: string;
  subcategorySlug: string;
  tagLabel: string;
}): string | null {
  const { entityLabel, query, categorySlug, subcategorySlug, tagLabel } = input;
  const parts: string[] = [];
  if (query.trim()) parts.push(`søk "${query.trim()}"`);
  if (categorySlug) parts.push(`hovedkategori ${humanizeSlug(categorySlug)}`);
  if (subcategorySlug) parts.push(`underkategori ${humanizeSlug(subcategorySlug)}`);
  if (tagLabel) parts.push(tagLabel);
  if (parts.length === 0) return null;
  return `Viser ${entityLabel} filtrert på ${parts.join(", ")}.`;
}

function humanizeSlug(value: string) {
  return value.replace(/-/g, " ");
}
