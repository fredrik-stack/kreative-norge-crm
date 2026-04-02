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
import { ConfirmNavigationModal } from "./components/ConfirmNavigationModal";
import { useUnsavedChangesGuard } from "./hooks/useUnsavedChangesGuard";
import { EditorProvider } from "./context/EditorContext";
import { OrganizationsPage } from "./pages/OrganizationsPage";
import { PeoplePage } from "./pages/PeoplePage";
import { useEditorData } from "./hooks/useEditorData";
import { filterSubcategoriesForCategory, sortedCategories, sortedTags } from "./editorTaxonomy";

export default function App() {
  const router = useMemo(() => createBrowserRouter([{ path: "*", element: <AppShell /> }]), []);
  return <RouterProvider router={router} future={{ v7_startTransition: true }} />;
}

function AppShell() {
  return <AuthGate>{({ username, onLogout }) => <EditorShell username={username} onLogout={onLogout} />}</AuthGate>;
}

function EditorShell({ username, onLogout }: { username: string; onLogout: () => void }) {
  const editor = useEditorData();
  const location = useLocation();
  const navigate = useNavigate();
  const isOrganizationsOverview = location.pathname === "/organizations" || location.pathname === "/";
  const isPeopleOverview = location.pathname === "/people";
  const onOverviewPage = isOrganizationsOverview || isPeopleOverview;
  const onPeoplePage = location.pathname.startsWith("/people");
  const onOrganizationsPage = location.pathname.startsWith("/organizations");
  const [overviewTagQuery, setOverviewTagQuery] = useState("");
  const [tagSearchFocused, setTagSearchFocused] = useState(false);
  const overviewEntityLabel = isPeopleOverview ? "personer" : "aktører";
  const overviewFilterSummary = buildEditorOverviewFilterSummary({
    entityLabel: overviewEntityLabel,
    query: editor.overviewQuery,
    categorySlug: editor.overviewCategorySlug,
    subcategorySlug: editor.overviewSubcategorySlug,
    tagSlug: editor.overviewTagSlug,
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
  });

  const goToEditorHome = () => {
    editor.resetOverviewFilters();
    navigate("/organizations");
  };

  useEffect(() => {
    setOverviewTagQuery(editor.tags.find((tag) => tag.slug === editor.overviewTagSlug)?.name ?? "");
  }, [editor.overviewTagSlug, editor.tags]);

  const overviewTagSuggestions = useMemo(() => {
    const query = overviewTagQuery.trim().toLocaleLowerCase("nb");
    if (!query) return [];
    return sortedTags(editor.tags)
      .filter((tag) => tag.name.toLocaleLowerCase("nb").includes(query))
      .slice(0, 8);
  }, [overviewTagQuery, editor.tags]);

  return (
    <div className="app-shell">
      <header className="hero">
        <div>
          <p className="eyebrow">Kreative Norge</p>
          <h1>
            <Link
              to="/organizations"
              className="editor-title-link"
              onClick={(event) => {
                event.preventDefault();
                goToEditorHome();
              }}
            >
              Editor CRM
            </Link>
          </h1>
          {onOverviewPage ? (
            <div className="hero-controls">
              <input
                className="search-input"
                type="search"
                placeholder="Søk navn, kommune, kategori eller tag..."
                value={editor.overviewQuery}
                onChange={(e) => editor.setOverviewQuery(e.target.value)}
              />
              <div className="hero-filter-grid">
                <select
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
                <div className="overview-tag-search">
                  <input
                    className="search-input"
                    value={overviewTagQuery}
                    placeholder="Søk tag"
                    onFocus={() => setTagSearchFocused(true)}
                    onBlur={() => {
                      window.setTimeout(() => setTagSearchFocused(false), 120);
                    }}
                    onChange={(e) => {
                      const nextValue = e.target.value;
                      setOverviewTagQuery(nextValue);
                      const raw = nextValue.trim().toLocaleLowerCase("nb");
                      const match = editor.tags.find((tag) => tag.name.toLocaleLowerCase("nb") === raw);
                      editor.setOverviewTagSlug(match?.slug ?? "");
                    }}
                  />
                  {tagSearchFocused && overviewTagSuggestions.length > 0 ? (
                    <div className="overview-tag-suggestions" role="listbox" aria-label="Tag-forslag">
                      {overviewTagSuggestions.map((tag) => (
                        <button
                          key={tag.id}
                          type="button"
                          className="overview-tag-suggestion"
                          onMouseDown={(event) => event.preventDefault()}
                          onClick={() => {
                            setOverviewTagQuery(tag.name);
                            editor.setOverviewTagSlug(tag.slug);
                            setTagSearchFocused(false);
                          }}
                        >
                          {tag.name}
                        </button>
                      ))}
                    </div>
                  ) : null}
                </div>
              </div>
              {overviewFilterSummary ? <div className="filter-summary">{overviewFilterSummary}</div> : null}
              <div className="hero-actions">
                <button
                  type="button"
                  className="primary-button"
                  onClick={() => {
                    if (isPeopleOverview) {
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
                <button type="button" className="ghost-button" onClick={goToEditorHome}>
                  Nullstill
                </button>
              </div>
            </div>
          ) : null}
        </div>
        <div className="hero-card">
          <label className="field-label" htmlFor="tenant-select">
            Aktiv tenant
          </label>
          <select
            id="tenant-select"
            value={editor.tenantId ?? ""}
            onChange={(e) => {
              const next = Number(e.target.value);
              const nextTenantId = Number.isNaN(next) ? null : next;
              unsavedGuard.requestTenantSelection(nextTenantId);
            }}
          >
            {editor.tenants.length === 0 ? <option value="">Ingen tenants funnet</option> : null}
            {editor.tenants.map((tenant) => (
              <option key={tenant.id} value={tenant.id}>
                {tenant.name} ({tenant.slug})
              </option>
            ))}
          </select>
          <nav className="top-nav" aria-label="Hovednavigasjon">
            <NavLink to="/organizations" end className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
              Aktører{editor.organizationHasUnsavedChanges && !onPeoplePage ? " *" : ""}
            </NavLink>
            <NavLink to="/people" end className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
              Personer{editor.peopleHasUnsavedChanges ? " *" : ""}
            </NavLink>
          </nav>
          <div className="session-bar">
            <span className="meta">Innlogget som {username}</span>
            <button type="button" className="ghost-button" onClick={onLogout}>
              Logg ut
            </button>
          </div>
        </div>
      </header>

      {editor.error ? <div className="banner error">{editor.error}</div> : null}

      <EditorProvider value={editor}>
        <Routes>
          <Route path="/" element={<Navigate to="/organizations" replace />} />
          <Route path="/organizations" element={<OrganizationsPage />} />
          <Route path="/organizations/:orgId" element={<OrganizationsPage />} />
          <Route path="/people" element={<PeoplePage />} />
          <Route path="/people/:personId" element={<PeoplePage />} />
        </Routes>
      </EditorProvider>

      <ConfirmNavigationModal {...unsavedGuard.modal} />
    </div>
  );
}

function buildEditorOverviewFilterSummary(input: {
  entityLabel: string;
  query: string;
  categorySlug: string;
  subcategorySlug: string;
  tagSlug: string;
}): string | null {
  const { entityLabel, query, categorySlug, subcategorySlug, tagSlug } = input;
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
