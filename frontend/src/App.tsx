import { useMemo } from "react";
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
import { EditorOverviewPage } from "./pages/EditorOverviewPage";
import { OrganizationsPage } from "./pages/OrganizationsPage";
import { PeoplePage } from "./pages/PeoplePage";
import { useEditorData } from "./hooks/useEditorData";

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
  const onOverviewPage = location.pathname === "/organizations" || location.pathname === "/" || location.pathname === "/people";
  const onPeoplePage = location.pathname.startsWith("/people");
  const onOrganizationsPage = location.pathname.startsWith("/organizations");
  const peopleHref =
    editor.selectedPersonId === "new"
      ? "/people/new"
      : typeof editor.selectedPersonId === "number"
        ? `/people/${editor.selectedPersonId}`
        : "/people/new";
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
  });

  return (
    <div className="app-shell">
      <header className="hero">
        <div>
          <p className="eyebrow">Kreative Norge</p>
          <h1>
            <Link to="/organizations" className="editor-title-link">
              Editor CRM
            </Link>
          </h1>
          {onOverviewPage ? (
            <div className="hero-controls">
              <input
                className="search-input"
                placeholder="Søk navn, kommune, kategori eller tag..."
                value={editor.overviewQuery}
                onChange={(e) => editor.setOverviewQuery(e.target.value)}
              />
              <div className="hero-filter-grid">
                <select
                  value={editor.overviewCategorySlug}
                  onChange={(e) => {
                    editor.setOverviewCategorySlug(e.target.value);
                    editor.setOverviewSubcategorySlug("");
                  }}
                >
                  <option value="">Alle hovedkategorier</option>
                  {editor.categories.map((category) => (
                    <option key={category.id} value={category.slug}>
                      {category.name}
                    </option>
                  ))}
                </select>
                <select
                  value={editor.overviewSubcategorySlug}
                  onChange={(e) => editor.setOverviewSubcategorySlug(e.target.value)}
                  disabled={!editor.overviewCategorySlug}
                >
                  <option value="">
                    {editor.overviewCategorySlug ? "Alle underkategorier" : "Velg hovedkategori først"}
                  </option>
                  {editor.filteredOverviewSubcategories.map((subcategory) => (
                    <option key={subcategory.id} value={subcategory.slug}>
                      {subcategory.name}
                    </option>
                  ))}
                </select>
                <select value={editor.overviewTagSlug} onChange={(e) => editor.setOverviewTagSlug(e.target.value)}>
                  <option value="">Alle tags</option>
                  {editor.tags.map((tag) => (
                    <option key={tag.id} value={tag.slug}>
                      {tag.name}
                    </option>
                  ))}
                </select>
              </div>
              {editor.overviewFilterSummary ? <div className="filter-summary">{editor.overviewFilterSummary}</div> : null}
              <div className="hero-actions">
                <button
                  type="button"
                  className="primary-button"
                  onClick={() => {
                    editor.setSelectedOrgId("new");
                    navigate("/organizations/new");
                  }}
                >
                  Ny organisasjon
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
            <NavLink to="/organizations" className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
              Oversikt
            </NavLink>
            <NavLink to={peopleHref} className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
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
          <Route path="/organizations" element={<EditorOverviewPage />} />
          <Route path="/organizations/:orgId" element={<OrganizationsPage />} />
          <Route path="/people" element={<EditorOverviewPage />} />
          <Route path="/people/:personId" element={<PeoplePage />} />
        </Routes>
      </EditorProvider>

      <ConfirmNavigationModal {...unsavedGuard.modal} />
    </div>
  );
}
