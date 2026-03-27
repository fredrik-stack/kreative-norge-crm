import { useMemo } from "react";
import {
  NavLink,
  Navigate,
  Route,
  RouterProvider,
  Routes,
  createBrowserRouter,
} from "react-router-dom";
import { AuthGate } from "./components/AuthGate";
import { ConfirmNavigationModal } from "./components/ConfirmNavigationModal";
import { useUnsavedChangesGuard } from "./hooks/useUnsavedChangesGuard";
import { EditorProvider } from "./context/EditorContext";
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
  const organizationsHref =
    editor.selectedOrgId === "new"
      ? "/organizations/new"
      : typeof editor.selectedOrgId === "number"
        ? `/organizations/${editor.selectedOrgId}`
        : "/organizations/new";
  const peopleHref =
    editor.selectedPersonId === "new"
      ? "/people/new"
      : typeof editor.selectedPersonId === "number"
        ? `/people/${editor.selectedPersonId}`
        : "/people/new";
  const dirtySummary = useMemo(() => {
    const items: string[] = [];
    if (editor.organizationHasUnsavedChanges) items.push("Aktørskjema");
    if (editor.personDraftHasUnsavedChanges) items.push("Personskjema");
    if (editor.contactDraftHasUnsavedChanges) items.push("Ny kontakt (ikke lagret)");
    return items;
  }, [
    editor.contactDraftHasUnsavedChanges,
    editor.organizationHasUnsavedChanges,
    editor.personDraftHasUnsavedChanges,
  ]);
  const unsavedGuard = useUnsavedChangesGuard({
    hasUnsavedChanges: editor.hasUnsavedChanges,
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
          <h1>Editor UI MVP</h1>
          <p className="hero-copy">
            Moderne redaktørflate for tenant-baserte aktører. Nå delt i egne sider for aktører og personer.
          </p>
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
            <NavLink to={organizationsHref} className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
              Aktører{editor.organizationHasUnsavedChanges ? " *" : ""}
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
          <Route path="/organizations" element={<Navigate to="/organizations/new" replace />} />
          <Route path="/organizations/:orgId" element={<OrganizationsPage />} />
          <Route path="/people" element={<Navigate to="/people/new" replace />} />
          <Route path="/people/:personId" element={<PeoplePage />} />
        </Routes>
      </EditorProvider>

      <ConfirmNavigationModal {...unsavedGuard.modal} />
    </div>
  );
}
