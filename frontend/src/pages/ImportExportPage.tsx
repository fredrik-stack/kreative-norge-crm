import { useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { Field } from "../components/Field";
import { useEditor } from "../context/EditorContext";
import { getExportJobFileUrl, getImportJobErrorReportUrl } from "../api";
import { useExportJobs } from "../hooks/useExportJobs";
import { useImportJobs } from "../hooks/useImportJobs";
import type { ImportDecision, ImportRow } from "../types";

const EXPORT_FIELD_OPTIONS = [
  "organization_name",
  "organization_org_number",
  "organization_email",
  "organization_phone",
  "organization_municipalities",
  "organization_categories",
  "organization_subcategories",
  "organization_tags",
  "organization_is_published",
  "person_full_name",
  "person_title",
  "person_email",
  "person_phone",
  "person_municipality",
  "person_categories",
  "person_subcategories",
  "person_tags",
  "link_status",
  "link_publish_person",
];

export function ImportExportPage() {
  const editor = useEditor();
  const importJobs = useImportJobs(editor.tenantId);
  const exportJobs = useExportJobs(editor.tenantId);
  const [sourceType, setSourceType] = useState<"CSV" | "XLSX">("CSV");
  const [importMode, setImportMode] = useState<"COMBINED" | "ORGANIZATIONS_ONLY" | "PEOPLE_ONLY">("COMBINED");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [detailRow, setDetailRow] = useState<ImportRow | null>(null);
  const [skipUnresolved, setSkipUnresolved] = useState(false);
  const [format, setFormat] = useState<"CSV" | "XLSX">("CSV");
  const [exportType, setExportType] = useState<"SEARCH_RESULTS" | "ADMIN_FULL" | "PERSONS_ONLY" | "ORGANIZATIONS_ONLY">("SEARCH_RESULTS");
  const [fieldSelection, setFieldSelection] = useState<string[]>([
    "organization_name",
    "person_full_name",
    "organization_email",
    "person_email",
  ]);
  const [filterQuery, setFilterQuery] = useState("");

  return (
    <main className="import-export-layout">
      <ImportPanel />
      <ExportPanel />
    </main>
  );

  function ImportPanel() {
    const selectedJob = importJobs.selectedJob;
    const rows = importJobs.rowsPage?.results ?? [];
    const summary = selectedJob?.summary_json ?? {};
    const unresolvedCount = Number(summary.review_required_rows ?? 0);

    async function handlePreview() {
      if (!selectedJob) return;
      if (!selectedJob.file && selectedFile) {
        const uploaded = await importJobs.uploadFile(selectedFile);
        if (!uploaded) return;
      }
      await importJobs.runPreview();
    }

    const jobOptions = importJobs.jobs.map((job) => (
      <button
        key={job.id}
        type="button"
        className={`job-list-item ${job.id === importJobs.selectedJobId ? "active" : ""}`}
        onClick={() => importJobs.setSelectedJobId(job.id)}
      >
        <strong>#{job.id}</strong>
        <span>{job.filename || job.source_type}</span>
        <span className={`save-pill ${job.status === "COMPLETED" ? "saved" : job.status === "FAILED" ? "error" : "idle"}`}>
          {job.status}
        </span>
      </button>
    ));

    return (
      <section className="panel import-export-panel">
        <div className="sidebar-header">
          <div>
            <p className="eyebrow small">Import</p>
            <h2>Importjobber</h2>
          </div>
          <span className="meta">{importJobs.jobs.length} jobber</span>
        </div>
        {importJobs.forbidden ? <div className="banner error">Du har ikke tilgang til import for denne tenanten.</div> : null}
        {importJobs.error ? <div className="banner error">{importJobs.error}</div> : null}

        <div className="import-export-grid">
          <div className="import-export-sidebar">
            <div className="job-list">{jobOptions}</div>
          </div>
          <div className="import-export-main">
            <div className="import-actions">
              <Field label="Kildetype">
                <select value={sourceType} onChange={(e) => setSourceType(e.target.value as "CSV" | "XLSX")}>
                  <option value="CSV">CSV</option>
                  <option value="XLSX">XLSX</option>
                </select>
              </Field>
              <Field label="Importmodus">
                <select
                  value={importMode}
                  onChange={(e) => setImportMode(e.target.value as "COMBINED" | "ORGANIZATIONS_ONLY" | "PEOPLE_ONLY")}
                >
                  <option value="COMBINED">Combined</option>
                  <option value="ORGANIZATIONS_ONLY">Organizations only</option>
                  <option value="PEOPLE_ONLY">People only</option>
                </select>
              </Field>
              <button
                type="button"
                className="primary-button"
                disabled={!!importJobs.busyAction || importJobs.forbidden || !editor.tenantId}
                onClick={() => void importJobs.createJob({ source_type: sourceType, import_mode: importMode })}
              >
                Opprett importjobb
              </button>
            </div>

            {selectedJob ? (
              <>
                <div className="import-summary-grid">
                  <SummaryCard label="Rader totalt" value={summary.rows_total} />
                  <SummaryCard label="Gyldige" value={summary.valid_rows} />
                  <SummaryCard label="Ugyldige" value={summary.invalid_rows} />
                  <SummaryCard label="Review" value={summary.review_required_rows} />
                  <SummaryCard label="Aktører opprett" value={summary.organizations_create} />
                  <SummaryCard label="Aktører oppdatér" value={summary.organizations_update} />
                  <SummaryCard label="Personer opprett" value={summary.persons_create} />
                  <SummaryCard label="Personer oppdatér" value={summary.persons_update} />
                  <SummaryCard label="Lenker" value={summary.links_create} />
                  <SummaryCard label="Nye tags" value={summary.tags_new} />
                </div>

                <div className="import-toolbar">
                  <Field label="Last opp CSV/XLSX">
                    <input
                      type="file"
                      accept=".csv,.xlsx"
                      onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
                    />
                  </Field>
                  <button
                    type="button"
                    className="ghost-button"
                    disabled={!selectedFile || importJobs.busyAction === "upload"}
                    onClick={() => selectedFile && void importJobs.uploadFile(selectedFile)}
                  >
                    Last opp
                  </button>
                  <button
                    type="button"
                    className="primary-button"
                    disabled={(!selectedJob.file && !selectedFile) || importJobs.busyAction === "preview" || importJobs.busyAction === "upload"}
                    onClick={() => void handlePreview()}
                  >
                    Kjør preview
                  </button>
                  <a
                    className={`ghost-button ${selectedJob.error_report_file || summary.invalid_rows || summary.review_required_rows ? "" : "disabled-link"}`}
                    href={editor.tenantId ? getImportJobErrorReportUrl(editor.tenantId, selectedJob.id) : "#"}
                    onClick={(event) => {
                      if (!editor.tenantId) event.preventDefault();
                    }}
                  >
                    Feilrapport
                  </a>
                </div>

                <div className="import-filter-row">
                  <select
                    value={importJobs.rowsQuery.status ?? ""}
                    onChange={(e) => importJobs.setRowsQuery((current) => ({ ...current, status: e.target.value || undefined, page: 1 }))}
                  >
                    <option value="">Alle statuser</option>
                    <option value="VALID">Valid</option>
                    <option value="INVALID">Invalid</option>
                    <option value="REVIEW_REQUIRED">Review required</option>
                    <option value="SKIPPED">Skipped</option>
                    <option value="COMMITTED">Committed</option>
                  </select>
                  <select
                    value={importJobs.rowsQuery.action ?? ""}
                    onChange={(e) => importJobs.setRowsQuery((current) => ({ ...current, action: e.target.value || undefined, page: 1 }))}
                  >
                    <option value="">Alle handlinger</option>
                    <option value="CREATE">Create</option>
                    <option value="UPDATE">Update</option>
                    <option value="LINK_ONLY">Link only</option>
                    <option value="SKIP">Skip</option>
                  </select>
                  <input
                    className="search-input"
                    type="search"
                    placeholder="Søk i rader"
                    value={importJobs.rowsQuery.search ?? ""}
                    onChange={(e) => importJobs.setRowsQuery((current) => ({ ...current, search: e.target.value, page: 1 }))}
                  />
                </div>

                <div className="overview-table-wrap">
                  <table className="overview-table">
                    <thead>
                      <tr>
                        <th>Rad</th>
                        <th>Aktør</th>
                        <th>Person</th>
                        <th>Handling</th>
                        <th>Status</th>
                        <th>Advarsler</th>
                        <th>Feil</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((row) => (
                        <tr key={row.id}>
                          <td>{row.row_number}</td>
                          <td>{String(row.raw_payload_json.organization_name ?? "—")}</td>
                          <td>{String(row.raw_payload_json.person_full_name ?? "—")}</td>
                          <td><span className="mini-pill category">{row.proposed_action}</span></td>
                          <td><span className="mini-pill subcategory">{row.row_status}</span></td>
                          <td>{row.warnings_json.length}</td>
                          <td>{row.validation_errors_json.length}</td>
                          <td>
                            <button type="button" className="ghost-button compact-button" onClick={() => setDetailRow(row)}>
                              Åpne
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div className="pagination-row">
                  <button
                    type="button"
                    className="ghost-button compact-button"
                    disabled={!importJobs.rowsPage?.previous}
                    onClick={() => importJobs.setRowsQuery((current) => ({ ...current, page: Math.max(1, (current.page ?? 1) - 1) }))}
                  >
                    Forrige
                  </button>
                  <span className="meta">
                    Side {importJobs.rowsQuery.page ?? 1} av {Math.max(1, Math.ceil((importJobs.rowsPage?.count ?? 0) / 50))}
                  </span>
                  <button
                    type="button"
                    className="ghost-button compact-button"
                    disabled={!importJobs.rowsPage?.next}
                    onClick={() => importJobs.setRowsQuery((current) => ({ ...current, page: (current.page ?? 1) + 1 }))}
                  >
                    Neste
                  </button>
                </div>

                <div className="commit-bar">
                  {unresolvedCount > 0 ? (
                    <label className="checkbox-row">
                      <input type="checkbox" checked={skipUnresolved} onChange={(e) => setSkipUnresolved(e.target.checked)} />
                      Hopp over uavklarte rader ved commit
                    </label>
                  ) : null}
                  <button
                    type="button"
                    className="primary-button"
                    disabled={
                      !["PREVIEW_READY", "AWAITING_REVIEW"].includes(selectedJob.status) ||
                      importJobs.busyAction === "commit" ||
                      (unresolvedCount > 0 && !skipUnresolved)
                    }
                    onClick={() => void importJobs.commit(skipUnresolved)}
                  >
                    Commit import
                  </button>
                </div>

                <div className="import-summary-grid results-grid">
                  <SummaryCard label="Aktører opprettet" value={summary.organizations_created} />
                  <SummaryCard label="Aktører oppdatert" value={summary.organizations_updated} />
                  <SummaryCard label="Personer opprettet" value={summary.persons_created} />
                  <SummaryCard label="Personer oppdatert" value={summary.persons_updated} />
                  <SummaryCard label="Kontakter opprettet" value={summary.person_contacts_created} />
                  <SummaryCard label="Lenker opprettet" value={summary.links_created} />
                  <SummaryCard label="Rader hoppet over" value={summary.rows_skipped} />
                  <SummaryCard label="Rader feilet" value={summary.rows_failed} />
                </div>
              </>
            ) : (
              <div className="empty-state">Opprett eller velg en importjobb for å starte flyten.</div>
            )}
          </div>
        </div>

        {detailRow && editor.tenantId ? (
          <ImportRowDetailModal
            row={detailRow}
            organizations={editor.organizations}
            persons={editor.persons}
            categories={editor.categories}
            subcategories={editor.subcategories}
            onClose={() => setDetailRow(null)}
            onSave={(payload) => void importJobs.saveDecisions([{ row_id: detailRow.id, decisions: payload }]).then(() => setDetailRow(null))}
          />
        ) : null}
      </section>
    );
  }

  function ExportPanel() {
    return (
      <section className="panel import-export-panel">
        <div className="sidebar-header">
          <div>
            <p className="eyebrow small">Eksport</p>
            <h2>Eksportjobber</h2>
          </div>
          <span className="meta">{exportJobs.jobs.length} jobber</span>
        </div>
        {exportJobs.forbidden ? <div className="banner error">Du har ikke tilgang til eksport for denne tenanten.</div> : null}
        {exportJobs.error ? <div className="banner error">{exportJobs.error}</div> : null}
        <div className="import-actions export-form-grid">
          <Field label="Format">
            <select value={format} onChange={(e) => setFormat(e.target.value as "CSV" | "XLSX")}>
              <option value="CSV">CSV</option>
              <option value="XLSX">XLSX</option>
            </select>
          </Field>
          <Field label="Eksporttype">
            <select
              value={exportType}
              onChange={(e) =>
                setExportType(e.target.value as "SEARCH_RESULTS" | "ADMIN_FULL" | "PERSONS_ONLY" | "ORGANIZATIONS_ONLY")
              }
            >
              <option value="SEARCH_RESULTS">Search results</option>
              <option value="ADMIN_FULL">Admin full</option>
              <option value="PERSONS_ONLY">Persons only</option>
              <option value="ORGANIZATIONS_ONLY">Organizations only</option>
            </select>
          </Field>
          <Field label="Filtre (fritekst)">
            <input value={filterQuery} onChange={(e) => setFilterQuery(e.target.value)} placeholder="f.eks. Oslo eller jazz" />
          </Field>
        </div>
        <div className="field-group export-field-picker">
          <span className="field-label">Felter</span>
          <div className="pill-grid">
            {EXPORT_FIELD_OPTIONS.map((field) => {
              const active = fieldSelection.includes(field);
              return (
                <label key={field} className={`filter-chip ${active ? "active" : ""}`}>
                  <input
                    type="checkbox"
                    checked={active}
                    onChange={(e) => {
                      setFieldSelection((current) =>
                        e.target.checked ? [...current, field] : current.filter((item) => item !== field),
                      );
                    }}
                  />
                  <span>{field}</span>
                </label>
              );
            })}
          </div>
        </div>
        <div className="hero-actions">
          <button
            type="button"
            className="primary-button"
            disabled={exportJobs.busy || exportJobs.forbidden || fieldSelection.length === 0}
            onClick={() =>
              void exportJobs.createJob({
                export_type: exportType,
                format,
                filters_json: { q: filterQuery },
                selected_fields_json: fieldSelection,
              })
            }
          >
            Opprett eksportjobb
          </button>
        </div>
        <div className="job-list export-job-list">
          {exportJobs.jobs.map((job) => {
            const downloadUrl = getExportJobFileUrl(job.file);
            return (
              <div key={job.id} className={`job-list-item static ${job.id === exportJobs.selectedJobId ? "active" : ""}`}>
                <div>
                  <strong>#{job.id}</strong>
                  <div className="meta">{job.export_type} · {job.format}</div>
                </div>
                <div className="job-list-actions">
                  <span className={`save-pill ${job.status === "COMPLETED" ? "saved" : job.status === "FAILED" ? "error" : "idle"}`}>
                    {job.status}
                  </span>
                  {downloadUrl ? (
                    <a className="ghost-button compact-button" href={downloadUrl}>
                      Last ned
                    </a>
                  ) : null}
                </div>
              </div>
            );
          })}
        </div>
      </section>
    );
  }
}

function SummaryCard(props: { label: string; value: unknown }) {
  return (
    <div className="summary-card">
      <span className="meta">{props.label}</span>
      <strong>{String(props.value ?? 0)}</strong>
    </div>
  );
}

function ImportRowDetailModal(props: {
  row: ImportRow;
  organizations: ReturnType<typeof useEditor>["organizations"];
  persons: ReturnType<typeof useEditor>["persons"];
  categories: ReturnType<typeof useEditor>["categories"];
  subcategories: ReturnType<typeof useEditor>["subcategories"];
  onClose: () => void;
  onSave: (payload: Array<{ decision_type: ImportDecision["decision_type"]; payload_json?: Record<string, unknown> }>) => void;
}) {
  const { row, organizations, persons, categories, subcategories, onClose, onSave } = props;
  const aiSuggestions = row.ai_suggestions_json ?? {};
  const suggestedFields = ((aiSuggestions.suggested_fields as Record<string, unknown> | undefined) ?? {}) as Record<
    string,
    { value?: unknown; confidence?: number; source?: string; requires_review?: boolean }
  >;
  const organizationCandidates = Array.isArray(aiSuggestions.organization_match_candidates)
    ? (aiSuggestions.organization_match_candidates as Array<{ id: number; label?: string; score?: number; reason?: string }>)
    : [];
  const personCandidates = Array.isArray(aiSuggestions.person_match_candidates)
    ? (aiSuggestions.person_match_candidates as Array<{ id: number; label?: string; score?: number; reason?: string }>)
    : [];
  const existingDecisionMap = new Map(
    row.decisions
      .filter(
        (decision) =>
          decision.decision_type === "ACCEPT_AI_SUGGESTION" || decision.decision_type === "IGNORE_AI_SUGGESTION",
      )
      .map((decision) => [String(decision.payload_json.suggestion_key ?? ""), decision.decision_type]),
  );
  const [organizationDecision, setOrganizationDecision] = useState<"NONE" | "USE_EXISTING_ORGANIZATION" | "CREATE_NEW_ORGANIZATION">("NONE");
  const [personDecision, setPersonDecision] = useState<"NONE" | "USE_EXISTING_PERSON" | "CREATE_NEW_PERSON">("NONE");
  const [organizationId, setOrganizationId] = useState<number | "">("");
  const [personId, setPersonId] = useState<number | "">("");
  const [categoryId, setCategoryId] = useState<number | "">("");
  const [subcategoryId, setSubcategoryId] = useState<number | "">("");
  const [acceptTag, setAcceptTag] = useState(false);
  const [skipRow, setSkipRow] = useState(false);
  const [acceptedSuggestionKeys, setAcceptedSuggestionKeys] = useState<string[]>(
    Array.from(existingDecisionMap.entries())
      .filter(([, type]) => type === "ACCEPT_AI_SUGGESTION")
      .map(([key]) => key),
  );
  const [ignoredSuggestionKeys, setIgnoredSuggestionKeys] = useState<string[]>(
    Array.from(existingDecisionMap.entries())
      .filter(([, type]) => type === "IGNORE_AI_SUGGESTION")
      .map(([key]) => key),
  );

  function markSuggestion(key: string, nextState: "accept" | "ignore") {
    setAcceptedSuggestionKeys((current) =>
      nextState === "accept" ? Array.from(new Set([...current.filter((item) => item !== key), key])) : current.filter((item) => item !== key),
    );
    setIgnoredSuggestionKeys((current) =>
      nextState === "ignore" ? Array.from(new Set([...current.filter((item) => item !== key), key])) : current.filter((item) => item !== key),
    );
  }

  const modal = (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <div className="detail-modal import-row-modal" role="dialog" aria-modal="true" onClick={(event) => event.stopPropagation()}>
        <div className="sidebar-header modal-header">
          <div>
            <p className="eyebrow small">Import rad #{row.row_number}</p>
            <h2>{String(row.raw_payload_json.organization_name || row.raw_payload_json.person_full_name || "Rad")}</h2>
          </div>
          <button type="button" className="ghost-button" onClick={onClose}>Lukk</button>
        </div>
        <div className="modal-sections import-detail-grid">
          <section className="editor-detail-section modal-section-card">
            <div className="modal-section-header"><h4>Rå data</h4></div>
            <pre className="json-block">{JSON.stringify(row.raw_payload_json, null, 2)}</pre>
          </section>
          <section className="editor-detail-section modal-section-card">
            <div className="modal-section-header"><h4>Normalisert</h4></div>
            <pre className="json-block">{JSON.stringify(row.normalized_payload_json, null, 2)}</pre>
          </section>
          <section className="editor-detail-section modal-section-card">
            <div className="modal-section-header"><h4>Match</h4></div>
            <pre className="json-block">{JSON.stringify(row.match_result_json, null, 2)}</pre>
          </section>
          <section className="editor-detail-section modal-section-card">
            <div className="modal-section-header"><h4>AI-forslag</h4></div>
            <div className="detail-list">
              <strong>Aktørkandidater</strong>
              {organizationCandidates.length > 0 ? (
                <ul className="suggestion-list">
                  {organizationCandidates.map((candidate) => (
                    <li key={`org-${candidate.id}`}>
                      <div className="suggestion-row">
                        <span>{candidate.label || `Aktør #${candidate.id}`}</span>
                        <span className="meta">score {typeof candidate.score === "number" ? candidate.score.toFixed(2) : "—"} · {candidate.reason || "heuristic"}</span>
                      </div>
                      <button
                        type="button"
                        className="ghost-button compact-button"
                        onClick={() => {
                          setOrganizationDecision("USE_EXISTING_ORGANIZATION");
                          setOrganizationId(candidate.id);
                        }}
                      >
                        Bruk denne aktøren
                      </button>
                    </li>
                  ))}
                </ul>
              ) : <p className="muted">Ingen aktørkandidater.</p>}
              <strong>Personkandidater</strong>
              {personCandidates.length > 0 ? (
                <ul className="suggestion-list">
                  {personCandidates.map((candidate) => (
                    <li key={`person-${candidate.id}`}>
                      <div className="suggestion-row">
                        <span>{candidate.label || `Person #${candidate.id}`}</span>
                        <span className="meta">score {typeof candidate.score === "number" ? candidate.score.toFixed(2) : "—"} · {candidate.reason || "heuristic"}</span>
                      </div>
                      <button
                        type="button"
                        className="ghost-button compact-button"
                        onClick={() => {
                          setPersonDecision("USE_EXISTING_PERSON");
                          setPersonId(candidate.id);
                        }}
                      >
                        Bruk denne personen
                      </button>
                    </li>
                  ))}
                </ul>
              ) : <p className="muted">Ingen personkandidater.</p>}
              <strong>Feltforslag</strong>
              {Object.entries(suggestedFields).length > 0 ? (
                <ul className="suggestion-list">
                  {Object.entries(suggestedFields).map(([key, suggestion]) => {
                    const state = acceptedSuggestionKeys.includes(key) ? "accepted" : ignoredSuggestionKeys.includes(key) ? "ignored" : "pending";
                    return (
                      <li key={key} className={`suggestion-card ${state}`}>
                        <div className="suggestion-row">
                          <span className="suggestion-key">{key}</span>
                          <span className="meta">
                            {typeof suggestion.confidence === "number" ? `conf ${suggestion.confidence.toFixed(2)}` : "conf —"} · {suggestion.source || "heuristic"}
                          </span>
                        </div>
                        <pre className="json-inline">{JSON.stringify(suggestion.value, null, 2)}</pre>
                        <div className="suggestion-actions">
                          <button type="button" className="ghost-button compact-button" onClick={() => markSuggestion(key, "accept")}>
                            Godta
                          </button>
                          <button type="button" className="ghost-button compact-button" onClick={() => markSuggestion(key, "ignore")}>
                            Ignorer
                          </button>
                          <span className={`mini-pill ${state === "accepted" ? "category" : state === "ignored" ? "subcategory" : ""}`}>
                            {state === "accepted" ? "Akseptert" : state === "ignored" ? "Ignorert" : "Til vurdering"}
                          </span>
                        </div>
                      </li>
                    );
                  })}
                </ul>
              ) : <p className="muted">Ingen AI-forslag for raden.</p>}
            </div>
          </section>
          <section className="editor-detail-section modal-section-card">
            <div className="modal-section-header"><h4>Validering</h4></div>
            <div className="detail-list">
              <strong>Feil</strong>
              {row.validation_errors_json.length > 0 ? (
                <ul>{row.validation_errors_json.map((item) => <li key={item}>{item}</li>)}</ul>
              ) : <p className="muted">Ingen feil.</p>}
              <strong>Advarsler</strong>
              {row.warnings_json.length > 0 ? (
                <ul>{row.warnings_json.map((item) => <li key={item}>{item}</li>)}</ul>
              ) : <p className="muted">Ingen advarsler.</p>}
            </div>
          </section>
          <section className="editor-detail-section modal-section-card">
            <div className="modal-section-header"><h4>Vurderinger</h4></div>
            <div className="modal-form-grid">
              <Field label="Aktørvalg">
                <select value={organizationDecision} onChange={(e) => setOrganizationDecision(e.target.value as typeof organizationDecision)}>
                  <option value="NONE">Ingen</option>
                  <option value="USE_EXISTING_ORGANIZATION">Bruk eksisterende aktør</option>
                  <option value="CREATE_NEW_ORGANIZATION">Opprett ny aktør</option>
                </select>
              </Field>
              {organizationDecision === "USE_EXISTING_ORGANIZATION" ? (
                <Field label="Velg aktør">
                  <select value={organizationId} onChange={(e) => setOrganizationId(Number(e.target.value))}>
                    <option value="">Velg aktør</option>
                    {organizations.map((organization) => (
                      <option key={organization.id} value={organization.id}>{organization.name}</option>
                    ))}
                  </select>
                </Field>
              ) : null}
              <Field label="Personvalg">
                <select value={personDecision} onChange={(e) => setPersonDecision(e.target.value as typeof personDecision)}>
                  <option value="NONE">Ingen</option>
                  <option value="USE_EXISTING_PERSON">Bruk eksisterende person</option>
                  <option value="CREATE_NEW_PERSON">Opprett ny person</option>
                </select>
              </Field>
              {personDecision === "USE_EXISTING_PERSON" ? (
                <Field label="Velg person">
                  <select value={personId} onChange={(e) => setPersonId(Number(e.target.value))}>
                    <option value="">Velg person</option>
                    {persons.map((person) => (
                      <option key={person.id} value={person.id}>{person.full_name}</option>
                    ))}
                  </select>
                </Field>
              ) : null}
              <Field label="Map kategori">
                <select value={categoryId} onChange={(e) => setCategoryId(Number(e.target.value))}>
                  <option value="">Ingen</option>
                  {categories.map((category) => (
                    <option key={category.id} value={category.id}>{category.name}</option>
                  ))}
                </select>
              </Field>
              <Field label="Map underkategori">
                <select value={subcategoryId} onChange={(e) => setSubcategoryId(Number(e.target.value))}>
                  <option value="">Ingen</option>
                  {subcategories.map((subcategory) => (
                    <option key={subcategory.id} value={subcategory.id}>{subcategory.name}</option>
                  ))}
                </select>
              </Field>
              <label className="checkbox-row">
                <input type="checkbox" checked={acceptTag} onChange={(e) => setAcceptTag(e.target.checked)} />
                Godta ny tag
              </label>
              <label className="checkbox-row">
                <input type="checkbox" checked={skipRow} onChange={(e) => setSkipRow(e.target.checked)} />
                Hopp over rad
              </label>
            </div>
          </section>
        </div>
        <div className="actions modal-footer">
          <button type="button" className="ghost-button compact-button" onClick={onClose}>Avbryt</button>
          <button
            type="button"
            className="primary-button compact-button"
            onClick={() => {
              const decisions: Array<{ decision_type: ImportDecision["decision_type"]; payload_json?: Record<string, unknown> }> = [];
              if (organizationDecision === "USE_EXISTING_ORGANIZATION" && organizationId) {
                decisions.push({ decision_type: "USE_EXISTING_ORGANIZATION", payload_json: { organization_id: organizationId } });
              }
              if (organizationDecision === "CREATE_NEW_ORGANIZATION") {
                decisions.push({ decision_type: "CREATE_NEW_ORGANIZATION", payload_json: {} });
              }
              if (personDecision === "USE_EXISTING_PERSON" && personId) {
                decisions.push({ decision_type: "USE_EXISTING_PERSON", payload_json: { person_id: personId } });
              }
              if (personDecision === "CREATE_NEW_PERSON") {
                decisions.push({ decision_type: "CREATE_NEW_PERSON", payload_json: {} });
              }
              if (categoryId) {
                decisions.push({ decision_type: "MAP_CATEGORY", payload_json: { category_id: categoryId } });
              }
              if (subcategoryId) {
                decisions.push({ decision_type: "MAP_SUBCATEGORY", payload_json: { subcategory_id: subcategoryId } });
              }
              if (acceptTag) {
                decisions.push({ decision_type: "ACCEPT_NEW_TAG", payload_json: {} });
              }
              acceptedSuggestionKeys.forEach((key) => {
                decisions.push({
                  decision_type: "ACCEPT_AI_SUGGESTION",
                  payload_json: { suggestion_key: key, value: suggestedFields[key]?.value },
                });
              });
              ignoredSuggestionKeys
                .filter((key) => !acceptedSuggestionKeys.includes(key))
                .forEach((key) => {
                  decisions.push({
                    decision_type: "IGNORE_AI_SUGGESTION",
                    payload_json: { suggestion_key: key },
                  });
                });
              if (skipRow) {
                decisions.push({ decision_type: "SKIP_ROW", payload_json: {} });
              }
              onSave(decisions);
            }}
          >
            Lagre vurderinger
          </button>
        </div>
      </div>
    </div>
  );

  return createPortal(modal, document.body);
}
