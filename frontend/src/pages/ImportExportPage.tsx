import { useMemo, useRef, useState } from "react";
import { Fragment } from "react";
import { Field } from "../components/Field";
import { useEditor } from "../context/EditorContext";
import { getExportJobFileUrl, getImportJobErrorReportUrl } from "../api";
import { useExportJobs } from "../hooks/useExportJobs";
import { useImportJobs } from "../hooks/useImportJobs";
import type { Category, ImportDecision, ImportRow, Organization, Person, Subcategory } from "../types";

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

const SIMPLE_EDITABLE_SUGGESTION_FIELDS = [
  "organization_website_url",
  "organization_instagram_url",
  "organization_tiktok_url",
  "organization_linkedin_url",
  "organization_facebook_url",
  "organization_youtube_url",
  "organization_description",
  "person_title",
  "person_website_url",
  "person_instagram_url",
  "person_tiktok_url",
  "person_linkedin_url",
  "person_facebook_url",
  "person_youtube_url",
] as const;

const FIELD_LABELS: Record<string, string> = {
  organization_website_url: "Nettside",
  organization_instagram_url: "Instagram",
  organization_tiktok_url: "TikTok",
  organization_linkedin_url: "LinkedIn",
  organization_facebook_url: "Facebook",
  organization_youtube_url: "YouTube",
  organization_description: "Beskrivelse",
  person_title: "Tittel",
  person_website_url: "Personnettside",
  person_instagram_url: "Person Instagram",
  person_tiktok_url: "Person TikTok",
  person_linkedin_url: "Person LinkedIn",
  person_facebook_url: "Person Facebook",
  person_youtube_url: "Person YouTube",
  suggested_categories: "Hovedkategori",
  suggested_subcategories: "Underkategori",
  suggested_tags: "Tags",
};

const MODE_LABELS: Record<"COMBINED" | "ORGANIZATIONS_ONLY" | "PEOPLE_ONLY", string> = {
  COMBINED: "Kombinert",
  ORGANIZATIONS_ONLY: "Aktører",
  PEOPLE_ONLY: "Personer",
};

const SOURCE_TYPE_LABELS: Record<"CSV" | "XLSX", string> = {
  CSV: "CSV",
  XLSX: "XLSX",
};

type SuggestionField = {
  value?: unknown;
  confidence?: number;
  source?: string;
  requires_review?: boolean;
};

type SuggestionState = "pending" | "accepted" | "ignored";

type ReviewDraft = {
  organizationDecision: "NONE" | "USE_EXISTING_ORGANIZATION" | "CREATE_NEW_ORGANIZATION";
  personDecision: "NONE" | "USE_EXISTING_PERSON" | "CREATE_NEW_PERSON";
  organizationId: number | "";
  personId: number | "";
  categoryId: number | "";
  subcategoryId: number | "";
  tagsText: string;
  skipRow: boolean;
  technicalOpen: boolean;
  fieldValues: Record<string, string>;
  suggestionStates: Record<string, SuggestionState>;
};

export function ImportExportPage() {
  const editor = useEditor();
  const importJobs = useImportJobs(editor.tenantId);
  const exportJobs = useExportJobs(editor.tenantId);
  const [sourceType, setSourceType] = useState<"CSV" | "XLSX">("CSV");
  const [importMode, setImportMode] = useState<"COMBINED" | "ORGANIZATIONS_ONLY" | "PEOPLE_ONLY">("COMBINED");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [expandedRowId, setExpandedRowId] = useState<number | null>(null);
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

  async function handlePreview() {
    const selectedJob = importJobs.selectedJob;
    if (!selectedJob) return;
    if (!selectedJob.file && selectedFile) {
      const uploaded = await importJobs.uploadFile(selectedFile);
      if (!uploaded) return;
    }
    await importJobs.runPreview();
  }

  return (
    <main className="import-export-layout">
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

        <div className={`import-export-grid ${importJobs.selectedJob ? "review-active" : ""}`}>
          <div className="import-export-sidebar">
            <div className="job-list">
              {importJobs.jobs.map((job) => (
                <button
                  key={job.id}
                  type="button"
                  className={`job-list-item ${job.id === importJobs.selectedJobId ? "active" : ""}`}
                  onClick={() => {
                    importJobs.setSelectedJobId(job.id);
                    setExpandedRowId(null);
                  }}
                >
                  <strong>#{job.id}</strong>
                  <span>{job.filename || job.source_type}</span>
                  <span className={`save-pill ${job.status === "COMPLETED" ? "saved" : job.status === "FAILED" ? "error" : "idle"}`}>
                    {job.status}
                  </span>
                </button>
              ))}
            </div>
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
                <select value={importMode} onChange={(e) => setImportMode(e.target.value as "COMBINED" | "ORGANIZATIONS_ONLY" | "PEOPLE_ONLY")}> 
                  <option value="COMBINED">Combined</option>
                  <option value="ORGANIZATIONS_ONLY">Aktører</option>
                  <option value="PEOPLE_ONLY">Personer</option>
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

            {importJobs.selectedJob ? (
              <ImportReviewWorkspace
                editor={editor}
                importJobs={importJobs}
                selectedFile={selectedFile}
                setSelectedFile={setSelectedFile}
                skipUnresolved={skipUnresolved}
                setSkipUnresolved={setSkipUnresolved}
                expandedRowId={expandedRowId}
                setExpandedRowId={setExpandedRowId}
                onPreview={() => void handlePreview()}
              />
            ) : (
              <div className="empty-state">Opprett eller velg en importjobb for å starte flyten.</div>
            )}
          </div>
        </div>
      </section>

      <ExportPanel
        exportJobs={exportJobs}
        format={format}
        setFormat={setFormat}
        exportType={exportType}
        setExportType={setExportType}
        filterQuery={filterQuery}
        setFilterQuery={setFilterQuery}
        fieldSelection={fieldSelection}
        setFieldSelection={setFieldSelection}
      />
    </main>
  );
}

function ImportReviewWorkspace(props: {
  editor: ReturnType<typeof useEditor>;
  importJobs: ReturnType<typeof useImportJobs>;
  selectedFile: File | null;
  setSelectedFile: (file: File | null) => void;
  skipUnresolved: boolean;
  setSkipUnresolved: (value: boolean) => void;
  expandedRowId: number | null;
  setExpandedRowId: (rowId: number | null) => void;
  onPreview: () => void;
}) {
  const { editor, importJobs, selectedFile, setSelectedFile, skipUnresolved, setSkipUnresolved, expandedRowId, setExpandedRowId, onPreview } = props;
  const selectedJob = importJobs.selectedJob!;
  const rows = importJobs.rowsPage?.results ?? [];
  const summary = selectedJob.summary_json ?? {};
  const unresolvedCount = Number(summary.review_required_rows ?? 0);
  const mode = selectedJob.import_mode;
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const showPersonColumns = mode !== "ORGANIZATIONS_ONLY";
  const orgLabel = mode === "PEOPLE_ONLY" ? "Knyttet aktør" : "Aktør";
  const linkLabel = mode === "PEOPLE_ONLY" ? "Lenker og profiler" : "Nettside / lenker";

  return (
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
        <SummaryCard label="OpenAI-rader" value={summary.rows_using_openai} />
        <SummaryCard label="Fallback-rader" value={summary.rows_using_fallback} />
        <SummaryCard label="Uten forslag" value={summary.rows_with_no_useful_ai_suggestions} />
        <SummaryCard label="AI-feil" value={summary.rows_with_ai_errors} />
      </div>

      <div className="import-toolbar">
        <Field label="Last opp CSV/XLSX">
          <div className="file-picker-field">
            <input
              ref={fileInputRef}
              className="visually-hidden-input"
              aria-label="Last opp CSV/XLSX"
              type="file"
              accept=".csv,.xlsx"
              onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
            />
            <button type="button" className="ghost-button" onClick={() => fileInputRef.current?.click()}>
              Velg fil
            </button>
            <span className="meta">{selectedFile?.name || selectedJob.filename || "Ingen fil valgt ennå"}</span>
          </div>
        </Field>
        <div className="selected-file-card" aria-live="polite">
          <span className="meta">Valgt fil og modus</span>
          <strong>{selectedFile?.name || selectedJob.filename || "Ingen fil valgt ennå"}</strong>
          <span className="meta">
            {MODE_LABELS[mode]} · {SOURCE_TYPE_LABELS[selectedJob.source_type as "CSV" | "XLSX"] ?? selectedJob.source_type}
          </span>
          <span className={`save-pill ${selectedJob.status === "COMPLETED" ? "saved" : selectedJob.status === "FAILED" ? "error" : "idle"}`}>
            {selectedJob.status}
          </span>
        </div>
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
          onClick={onPreview}
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
          placeholder="Søk i importerte rader"
          value={importJobs.rowsQuery.search ?? ""}
          onChange={(e) => importJobs.setRowsQuery((current) => ({ ...current, search: e.target.value, page: 1 }))}
        />
      </div>

      <div className="overview-table-wrap import-review-wrap">
        <table className="overview-table import-review-table">
          <thead>
            <tr>
              <th>Rad</th>
              <th>{orgLabel}</th>
              {showPersonColumns ? <th>Person</th> : null}
              <th>Org.nr</th>
              <th>Kommune</th>
              <th>Nå hovedkategori</th>
              <th>AI hovedkategori</th>
              <th>Nå underkategori</th>
              <th>AI underkategori</th>
              <th>Nå tags</th>
              <th>AI tags</th>
              <th>Nå nettside</th>
              <th>AI nettside</th>
              <th>Nå profiler</th>
              <th>AI profiler</th>
              <th>Nå beskrivelse</th>
              <th>AI beskrivelse</th>
              <th>Provider</th>
              <th>Status</th>
              <th>Advarsler</th>
              <th>Feil</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const expanded = expandedRowId === row.id;
              const categorySuggestions = getSuggestionValues(row, "suggested_categories");
              const subcategorySuggestions = getSuggestionValues(row, "suggested_subcategories");
              const tagSuggestions = getSuggestionValues(row, "suggested_tags");
              const websiteSuggestion = getSuggestionText(row, "organization_website_url") || getSuggestionText(row, "person_website_url");
              const currentWebsite = getFirstText(
                row.raw_payload_json.organization_website_url,
                row.raw_payload_json.person_website_url,
              );
              const currentSocials = summarizeLinkValues([
                getFirstText(row.raw_payload_json.organization_instagram_url),
                getFirstText(row.raw_payload_json.organization_tiktok_url),
                getFirstText(row.raw_payload_json.organization_linkedin_url),
                getFirstText(row.raw_payload_json.organization_facebook_url),
                getFirstText(row.raw_payload_json.organization_youtube_url),
                getFirstText(row.raw_payload_json.person_instagram_url),
                getFirstText(row.raw_payload_json.person_tiktok_url),
                getFirstText(row.raw_payload_json.person_linkedin_url),
                getFirstText(row.raw_payload_json.person_facebook_url),
                getFirstText(row.raw_payload_json.person_youtube_url),
              ]);
              const socialSuggestions = summarizeLinkValues(
                SIMPLE_EDITABLE_SUGGESTION_FIELDS.filter(
                  (key) => key.endsWith("_url") && key !== "organization_website_url" && key !== "person_website_url",
                )
                  .map((key) => getSuggestionText(row, key))
                  .filter(Boolean),
              );
              const currentDescription = getFirstText(row.raw_payload_json.organization_description, row.raw_payload_json.person_note);
              const suggestedDescription = getSuggestionText(row, "organization_description");
              const provider = getProviderLabel(row);
              const diagnosticMeta = getDiagnosticMeta(row);
              const suggestionCount = countSuggestionFields(row);

              return (
                <Fragment key={row.id}>
                  <tr key={row.id} className={expanded ? "expanded" : ""}>
                    <td>{row.row_number}</td>
                    <td>
                      <ReviewValueCell current={getFirstText(row.raw_payload_json.organization_name)} fallback="—" />
                    </td>
                    {showPersonColumns ? (
                      <td>
                        <ReviewValueCell current={getFirstText(row.raw_payload_json.person_full_name)} fallback="—" />
                      </td>
                    ) : null}
                    <td>{getFirstText(row.raw_payload_json.organization_org_number) || "—"}</td>
                    <td>
                      <ReviewValueCell
                        current={getFirstText(row.raw_payload_json.organization_municipalities, row.raw_payload_json.person_municipality)}
                        fallback="—"
                      />
                    </td>
                    <td>
                      <ReviewSuggestionCell currentValues={splitCsvText(getFirstText(row.raw_payload_json.organization_categories, row.raw_payload_json.person_categories))} suggestedValues={[]} />
                    </td>
                    <td>
                      <ReviewSuggestionCell currentValues={[]} suggestedValues={categorySuggestions} />
                    </td>
                    <td>
                      <ReviewSuggestionCell currentValues={splitCsvText(getFirstText(row.raw_payload_json.organization_subcategories, row.raw_payload_json.person_subcategories))} suggestedValues={[]} />
                    </td>
                    <td>
                      <ReviewSuggestionCell currentValues={[]} suggestedValues={subcategorySuggestions} />
                    </td>
                    <td>
                      <ReviewSuggestionCell currentValues={splitCsvText(getFirstText(row.raw_payload_json.organization_tags, row.raw_payload_json.person_tags))} suggestedValues={[]} />
                    </td>
                    <td>
                      <ReviewSuggestionCell currentValues={[]} suggestedValues={tagSuggestions} />
                    </td>
                    <td>
                      <ReviewValueCell current={currentWebsite} fallback="Mangler" />
                    </td>
                    <td>
                      <ReviewValueCell current={websiteSuggestion} fallback="Ingen forslag" />
                    </td>
                    <td>
                      <ReviewLinkCell values={currentSocials} emptyLabel="Ingen lenker" />
                    </td>
                    <td>
                      <ReviewLinkCell values={socialSuggestions} emptyLabel="Ingen forslag" />
                    </td>
                    <td>
                      <ReviewTextCell value={currentDescription} emptyLabel="Mangler" />
                    </td>
                    <td>
                      <ReviewTextCell value={suggestedDescription} emptyLabel="Ingen forslag" />
                    </td>
                    <td>
                      <div className="review-provider-cell">
                        <span className={`mini-pill ${provider.variant}`}>{provider.label}</span>
                        <span className="meta">{suggestionCount > 0 ? `${suggestionCount} forslag` : "Ingen forslag"}</span>
                        {diagnosticMeta.helper ? <span className="meta">{diagnosticMeta.helper}</span> : null}
                      </div>
                    </td>
                    <td><span className="mini-pill subcategory">{row.row_status}</span></td>
                    <td>{row.warnings_json.length}</td>
                    <td>{row.validation_errors_json.length}</td>
                    <td>
                      <div className="review-url-cell">
                        <button type="button" className="ghost-button compact-button" onClick={() => setExpandedRowId(expanded ? null : row.id)}>
                          {expanded ? "Lukk" : "Review"}
                        </button>
                      </div>
                    </td>
                  </tr>
                  {expanded ? (
                    <tr key={`${row.id}-editor`} className="import-review-editor-row">
                      <td colSpan={showPersonColumns ? 21 : 20}>
                        <InlineReviewEditor
                          row={row}
                          organizations={editor.organizations}
                          persons={editor.persons}
                          categories={editor.categories}
                          subcategories={editor.subcategories}
                          onSave={(payload) =>
                            void importJobs
                              .saveDecisions([{ row_id: row.id, decisions: payload }])
                              .then(() => setExpandedRowId(null))
                          }
                        />
                      </td>
                    </tr>
                  ) : null}
                </Fragment>
              );
            })}
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
        ) : (
          <span className="meta">Review-rader kan gjennomgås og justeres direkte i oversikten.</span>
        )}
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
  );
}

function InlineReviewEditor(props: {
  row: ImportRow;
  organizations: Organization[];
  persons: Person[];
  categories: Category[];
  subcategories: Subcategory[];
  onSave: (payload: Array<{ decision_type: ImportDecision["decision_type"]; payload_json?: Record<string, unknown> }>) => void;
}) {
  const { row, organizations, persons, categories, subcategories, onSave } = props;
  const suggestedFields = useMemo(() => getSuggestionFields(row), [row]);
  const categorySuggestions = getSuggestionValues(row, "suggested_categories");
  const subcategorySuggestions = getSuggestionValues(row, "suggested_subcategories");
  const tagSuggestions = getSuggestionValues(row, "suggested_tags");
  const suggestionStates = getExistingSuggestionStates(row);
  const [draft, setDraft] = useState<ReviewDraft>(() => {
    const initialFieldValues: Record<string, string> = {};
    SIMPLE_EDITABLE_SUGGESTION_FIELDS.forEach((key) => {
      initialFieldValues[key] =
        getAcceptedDecisionValue(row, key) ||
        getSuggestionText(row, key) ||
        getFirstText(row.raw_payload_json[key], getNestedSuggestedFallback(row, key));
    });
    return {
      organizationDecision: getExistingDecisionType(row, ["USE_EXISTING_ORGANIZATION", "CREATE_NEW_ORGANIZATION"]) ?? "NONE",
      personDecision: getExistingDecisionType(row, ["USE_EXISTING_PERSON", "CREATE_NEW_PERSON"]) ?? "NONE",
      organizationId: getExistingDecisionId(row, "USE_EXISTING_ORGANIZATION", "organization_id"),
      personId: getExistingDecisionId(row, "USE_EXISTING_PERSON", "person_id"),
      categoryId: getExistingDecisionId(row, "MAP_CATEGORY", "category_id") || findCategoryIdByName(categories, categorySuggestions[0] || ""),
      subcategoryId:
        getExistingDecisionId(row, "MAP_SUBCATEGORY", "subcategory_id") ||
        findSubcategoryIdByName(subcategories, subcategorySuggestions[0] || ""),
      tagsText: getAcceptedDecisionArray(row, "suggested_tags").join(", ") || tagSuggestions.join(", "),
      skipRow: row.decisions.some((decision) => decision.decision_type === "SKIP_ROW"),
      technicalOpen: false,
      fieldValues: initialFieldValues,
      suggestionStates,
    };
  });

  const filteredSubcategories = useMemo(
    () => filterSubcategories(draft.categoryId, subcategories),
    [draft.categoryId, subcategories],
  );
  const diagnosticMeta = getDiagnosticMeta(row);

  function setSuggestionState(key: string, nextState: SuggestionState) {
    setDraft((current) => ({
      ...current,
      suggestionStates: {
        ...current.suggestionStates,
        [key]: nextState,
      },
    }));
  }

  function applyCategorySuggestion(name: string) {
    const categoryId = findCategoryIdByName(categories, name);
    setDraft((current) => ({
      ...current,
      categoryId,
      suggestionStates: { ...current.suggestionStates, suggested_categories: categoryId ? "accepted" : current.suggestionStates.suggested_categories },
    }));
  }

  function applySubcategorySuggestion(name: string) {
    const subcategoryId = findSubcategoryIdByName(subcategories, name);
    const relatedCategoryId = findCategoryIdForSubcategory(subcategories, subcategoryId);
    setDraft((current) => ({
      ...current,
      categoryId: relatedCategoryId || current.categoryId,
      subcategoryId,
      suggestionStates: {
        ...current.suggestionStates,
        suggested_subcategories: subcategoryId ? "accepted" : current.suggestionStates.suggested_subcategories,
      },
    }));
  }

  return (
    <div className="inline-review-editor">
      <div className="inline-review-grid">
        <section className="editor-detail-section modal-section-card">
          <div className="modal-section-header">
            <h4>Forslag og match</h4>
            <span className="meta">Kilde: {diagnosticMeta.title}</span>
          </div>
          {diagnosticMeta.detail ? <p className="meta review-diagnostic-copy">{diagnosticMeta.detail}</p> : null}
          <div className="review-detail-stack">
            <div>
              <strong>Aktørkandidater</strong>
              <SuggestionCandidates
                candidates={asCandidateList(row.ai_suggestions_json.organization_match_candidates)}
                onUse={(id) =>
                  setDraft((current) => ({
                    ...current,
                    organizationDecision: "USE_EXISTING_ORGANIZATION",
                    organizationId: id,
                  }))
                }
                emptyLabel="Ingen aktørkandidater"
              />
            </div>
            <div>
              <strong>Personkandidater</strong>
              <SuggestionCandidates
                candidates={asCandidateList(row.ai_suggestions_json.person_match_candidates)}
                onUse={(id) =>
                  setDraft((current) => ({
                    ...current,
                    personDecision: "USE_EXISTING_PERSON",
                    personId: id,
                  }))
                }
                emptyLabel="Ingen personkandidater"
              />
            </div>
            <div>
              <strong>Hovedkategori</strong>
              <SuggestionPills
                values={categorySuggestions}
                emptyLabel="Ingen forslag"
                state={draft.suggestionStates.suggested_categories ?? "pending"}
                onAccept={(value) => applyCategorySuggestion(value)}
                onIgnore={() => setSuggestionState("suggested_categories", "ignored")}
              />
            </div>
            <div>
              <strong>Underkategori</strong>
              <SuggestionPills
                values={subcategorySuggestions}
                emptyLabel="Ingen forslag"
                state={draft.suggestionStates.suggested_subcategories ?? "pending"}
                onAccept={(value) => applySubcategorySuggestion(value)}
                onIgnore={() => setSuggestionState("suggested_subcategories", "ignored")}
              />
            </div>
            <div>
              <strong>Tags</strong>
              <SuggestionPills
                values={tagSuggestions}
                emptyLabel="Ingen forslag"
                state={draft.suggestionStates.suggested_tags ?? "pending"}
                onAccept={() =>
                  setDraft((current) => ({
                    ...current,
                    tagsText: tagSuggestions.join(", "),
                    suggestionStates: { ...current.suggestionStates, suggested_tags: "accepted" },
                  }))
                }
                onIgnore={() => setSuggestionState("suggested_tags", "ignored")}
              />
            </div>
          </div>
        </section>

        <section className="editor-detail-section modal-section-card">
          <div className="modal-section-header"><h4>Rediger raskt</h4></div>
          <div className="modal-form-grid review-form-grid">
            <Field label="Aktørvalg">
              <select
                value={draft.organizationDecision}
                onChange={(e) => setDraft((current) => ({ ...current, organizationDecision: e.target.value as ReviewDraft["organizationDecision"] }))}
              >
                <option value="NONE">Ingen</option>
                <option value="USE_EXISTING_ORGANIZATION">Bruk eksisterende aktør</option>
                <option value="CREATE_NEW_ORGANIZATION">Opprett ny aktør</option>
              </select>
            </Field>
            {draft.organizationDecision === "USE_EXISTING_ORGANIZATION" ? (
              <Field label="Velg aktør">
                <select value={draft.organizationId} onChange={(e) => setDraft((current) => ({ ...current, organizationId: Number(e.target.value) }))}>
                  <option value="">Velg aktør</option>
                  {organizations.map((organization) => (
                    <option key={organization.id} value={organization.id}>{organization.name}</option>
                  ))}
                </select>
              </Field>
            ) : null}
            <Field label="Personvalg">
              <select
                value={draft.personDecision}
                onChange={(e) => setDraft((current) => ({ ...current, personDecision: e.target.value as ReviewDraft["personDecision"] }))}
              >
                <option value="NONE">Ingen</option>
                <option value="USE_EXISTING_PERSON">Bruk eksisterende person</option>
                <option value="CREATE_NEW_PERSON">Opprett ny person</option>
              </select>
            </Field>
            {draft.personDecision === "USE_EXISTING_PERSON" ? (
              <Field label="Velg person">
                <select value={draft.personId} onChange={(e) => setDraft((current) => ({ ...current, personId: Number(e.target.value) }))}>
                  <option value="">Velg person</option>
                  {persons.map((person) => (
                    <option key={person.id} value={person.id}>{person.full_name}</option>
                  ))}
                </select>
              </Field>
            ) : null}

            <Field label="Hovedkategori">
              <select
                value={draft.categoryId}
                onChange={(e) => setDraft((current) => ({ ...current, categoryId: Number(e.target.value) || "", subcategoryId: "" }))}
              >
                <option value="">Ingen</option>
                {categories.map((category) => (
                  <option key={category.id} value={category.id}>{category.name}</option>
                ))}
              </select>
            </Field>
            <Field label="Underkategori">
              <select
                value={draft.subcategoryId}
                onChange={(e) => setDraft((current) => ({ ...current, subcategoryId: Number(e.target.value) || "" }))}
              >
                <option value="">Ingen</option>
                {filteredSubcategories.map((subcategory) => (
                  <option key={subcategory.id} value={subcategory.id}>{subcategory.name}</option>
                ))}
              </select>
            </Field>

            <Field label="Tags (kommaseparert)">
              <input
                value={draft.tagsText}
                onChange={(e) => setDraft((current) => ({ ...current, tagsText: e.target.value, suggestionStates: { ...current.suggestionStates, suggested_tags: "accepted" } }))}
                placeholder="jazz, management"
              />
            </Field>

            {SIMPLE_EDITABLE_SUGGESTION_FIELDS.map((fieldKey) => {
              const suggestion = suggestedFields[fieldKey];
              return (
                <Field key={fieldKey} label={FIELD_LABELS[fieldKey] ?? fieldKey}>
                  <div className="review-inline-field">
                    <input
                      value={draft.fieldValues[fieldKey] ?? ""}
                      onChange={(e) =>
                        setDraft((current) => ({
                          ...current,
                          fieldValues: { ...current.fieldValues, [fieldKey]: e.target.value },
                          suggestionStates: { ...current.suggestionStates, [fieldKey]: e.target.value ? "accepted" : current.suggestionStates[fieldKey] ?? "pending" },
                        }))
                      }
                      placeholder={suggestion ? `Forslag: ${renderSuggestionValue(suggestion.value)}` : "Tomt felt"}
                    />
                    {suggestion ? (
                      <div className="review-inline-actions">
                        <button
                          type="button"
                          className="ghost-button compact-button"
                          onClick={() =>
                            setDraft((current) => ({
                              ...current,
                              fieldValues: { ...current.fieldValues, [fieldKey]: renderSuggestionValue(suggestion.value) },
                              suggestionStates: { ...current.suggestionStates, [fieldKey]: "accepted" },
                            }))
                          }
                        >
                          Godta forslag
                        </button>
                        <button
                          type="button"
                          className="ghost-button compact-button"
                          onClick={() => setSuggestionState(fieldKey, "ignored")}
                        >
                          Ignorer
                        </button>
                      </div>
                    ) : null}
                  </div>
                </Field>
              );
            })}

            <label className="checkbox-row review-checkbox-row">
              <input type="checkbox" checked={draft.skipRow} onChange={(e) => setDraft((current) => ({ ...current, skipRow: e.target.checked }))} />
              Hopp over denne raden
            </label>
          </div>
        </section>
      </div>

      <div className="review-tech-block">
        <button
          type="button"
          className="ghost-button compact-button"
          onClick={() => setDraft((current) => ({ ...current, technicalOpen: !current.technicalOpen }))}
        >
          {draft.technicalOpen ? "Skjul teknisk detalj" : "Vis teknisk detalj"}
        </button>
        {draft.technicalOpen ? (
          <div className="import-detail-grid technical-grid">
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
          </div>
        ) : null}
      </div>

      <div className="actions inline-review-actions">
        <button
          type="button"
          className="primary-button compact-button"
          onClick={() => onSave(buildDecisions(row, draft))}
        >
          Lagre review
        </button>
      </div>
    </div>
  );
}

function buildDecisions(
  row: ImportRow,
  draft: ReviewDraft,
): Array<{ decision_type: ImportDecision["decision_type"]; payload_json?: Record<string, unknown> }> {
  const decisions: Array<{ decision_type: ImportDecision["decision_type"]; payload_json?: Record<string, unknown> }> = [];

  if (draft.organizationDecision === "USE_EXISTING_ORGANIZATION" && draft.organizationId) {
    decisions.push({ decision_type: "USE_EXISTING_ORGANIZATION", payload_json: { organization_id: draft.organizationId } });
  }
  if (draft.organizationDecision === "CREATE_NEW_ORGANIZATION") {
    decisions.push({ decision_type: "CREATE_NEW_ORGANIZATION", payload_json: {} });
  }
  if (draft.personDecision === "USE_EXISTING_PERSON" && draft.personId) {
    decisions.push({ decision_type: "USE_EXISTING_PERSON", payload_json: { person_id: draft.personId } });
  }
  if (draft.personDecision === "CREATE_NEW_PERSON") {
    decisions.push({ decision_type: "CREATE_NEW_PERSON", payload_json: {} });
  }
  if (draft.categoryId) {
    decisions.push({ decision_type: "MAP_CATEGORY", payload_json: { category_id: draft.categoryId } });
  }
  if (draft.subcategoryId) {
    decisions.push({ decision_type: "MAP_SUBCATEGORY", payload_json: { subcategory_id: draft.subcategoryId } });
  }

  if (draft.tagsText.trim()) {
    decisions.push({
      decision_type: "ACCEPT_AI_SUGGESTION",
      payload_json: { suggestion_key: "suggested_tags", value: splitCsvText(draft.tagsText) },
    });
  } else if (draft.suggestionStates.suggested_tags === "ignored") {
    decisions.push({ decision_type: "IGNORE_AI_SUGGESTION", payload_json: { suggestion_key: "suggested_tags" } });
  }

  SIMPLE_EDITABLE_SUGGESTION_FIELDS.forEach((fieldKey) => {
    const fieldValue = draft.fieldValues[fieldKey]?.trim();
    const state = draft.suggestionStates[fieldKey] ?? "pending";
    if (fieldValue) {
      decisions.push({
        decision_type: "ACCEPT_AI_SUGGESTION",
        payload_json: { suggestion_key: fieldKey, value: fieldValue },
      });
    } else if (state === "ignored") {
      decisions.push({ decision_type: "IGNORE_AI_SUGGESTION", payload_json: { suggestion_key: fieldKey } });
    }
  });

  if (draft.suggestionStates.suggested_categories === "ignored") {
    decisions.push({ decision_type: "IGNORE_AI_SUGGESTION", payload_json: { suggestion_key: "suggested_categories" } });
  }
  if (draft.suggestionStates.suggested_subcategories === "ignored") {
    decisions.push({ decision_type: "IGNORE_AI_SUGGESTION", payload_json: { suggestion_key: "suggested_subcategories" } });
  }
  if (draft.skipRow) {
    decisions.push({ decision_type: "SKIP_ROW", payload_json: {} });
  }

  return decisions;
}

function ExportPanel(props: {
  exportJobs: ReturnType<typeof useExportJobs>;
  format: "CSV" | "XLSX";
  setFormat: (value: "CSV" | "XLSX") => void;
  exportType: "SEARCH_RESULTS" | "ADMIN_FULL" | "PERSONS_ONLY" | "ORGANIZATIONS_ONLY";
  setExportType: (value: "SEARCH_RESULTS" | "ADMIN_FULL" | "PERSONS_ONLY" | "ORGANIZATIONS_ONLY") => void;
  filterQuery: string;
  setFilterQuery: (value: string) => void;
  fieldSelection: string[];
  setFieldSelection: (value: string[] | ((current: string[]) => string[])) => void;
}) {
  const { exportJobs, format, setFormat, exportType, setExportType, filterQuery, setFilterQuery, fieldSelection, setFieldSelection } = props;

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
          <select value={exportType} onChange={(e) => setExportType(e.target.value as "SEARCH_RESULTS" | "ADMIN_FULL" | "PERSONS_ONLY" | "ORGANIZATIONS_ONLY")}> 
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

function SummaryCard(props: { label: string; value: unknown }) {
  return (
    <div className="summary-card">
      <span className="meta">{props.label}</span>
      <strong>{String(props.value ?? 0)}</strong>
    </div>
  );
}

function ReviewValueCell(props: { current?: string; suggested?: string; fallback?: string }) {
  return (
    <div className="review-value-cell">
      <span>{props.current || props.fallback || "—"}</span>
      {!props.current && props.suggested ? <span className="review-suggested-hint">Forslag: {props.suggested}</span> : null}
    </div>
  );
}

function ReviewSuggestionCell(props: { currentValues: string[]; suggestedValues: string[] }) {
  const values = props.currentValues.length > 0 ? props.currentValues : props.suggestedValues;
  if (values.length === 0) {
    return <span className="muted">Mangler</span>;
  }
  return (
    <div className="review-pill-stack">
      {values.slice(0, 3).map((value) => (
        <span key={value} className={`mini-pill ${props.currentValues.length > 0 ? "category" : "suggested"}`}>{value}</span>
      ))}
      {values.length > 3 ? <span className="meta">+{values.length - 3}</span> : null}
    </div>
  );
}

function ReviewLinkCell(props: { values: string[]; emptyLabel: string }) {
  if (props.values.length === 0) {
    return <span className="muted">{props.emptyLabel}</span>;
  }
  return (
    <div className="review-link-stack">
      {props.values.slice(0, 3).map((value) => (
        <span key={value} className="review-link-chip" title={value}>
          {shortenDisplayText(value, 42)}
        </span>
      ))}
      {props.values.length > 3 ? <span className="meta">+{props.values.length - 3}</span> : null}
    </div>
  );
}

function ReviewTextCell(props: { value?: string; emptyLabel: string }) {
  if (!props.value) {
    return <span className="muted">{props.emptyLabel}</span>;
  }
  return <p className="review-copy-snippet">{shortenDisplayText(props.value, 110)}</p>;
}

function SuggestionPills(props: {
  values: string[];
  emptyLabel: string;
  state: SuggestionState;
  onAccept: (value: string) => void;
  onIgnore: () => void;
}) {
  if (props.values.length === 0) {
    return <p className="muted">{props.emptyLabel}</p>;
  }
  return (
    <div className="suggestion-pill-block">
      <div className="review-pill-stack">
        {props.values.map((value) => (
          <button key={value} type="button" className="suggestion-pill" onClick={() => props.onAccept(value)}>
            {value}
          </button>
        ))}
      </div>
      <div className="suggestion-actions compact">
        <span className={`mini-pill ${props.state === "accepted" ? "category" : props.state === "ignored" ? "subcategory" : ""}`}>
          {props.state === "accepted" ? "Akseptert" : props.state === "ignored" ? "Ignorert" : "Til vurdering"}
        </span>
        <button type="button" className="ghost-button compact-button" onClick={props.onIgnore}>Ignorer</button>
      </div>
    </div>
  );
}

function SuggestionCandidates(props: {
  candidates: Array<{ id: number; label?: string; score?: number; reason?: string }>;
  onUse: (id: number) => void;
  emptyLabel: string;
}) {
  if (props.candidates.length === 0) {
    return <p className="muted">{props.emptyLabel}</p>;
  }
  return (
    <ul className="suggestion-list compact">
      {props.candidates.map((candidate) => (
        <li key={candidate.id} className="suggestion-card compact">
          <div className="suggestion-row">
            <span>{candidate.label || `#${candidate.id}`}</span>
            <span className="meta">score {typeof candidate.score === "number" ? candidate.score.toFixed(2) : "—"} · {candidate.reason || "heuristic"}</span>
          </div>
          <button type="button" className="ghost-button compact-button" onClick={() => props.onUse(candidate.id)}>
            Bruk denne
          </button>
        </li>
      ))}
    </ul>
  );
}

function getSuggestionFields(row: ImportRow): Record<string, SuggestionField> {
  return ((row.ai_suggestions_json?.suggested_fields as Record<string, SuggestionField> | undefined) ?? {});
}

function getSuggestionValues(row: ImportRow, key: string): string[] {
  const value = getSuggestionFields(row)[key]?.value;
  if (Array.isArray(value)) {
    return value.map((item) => String(item)).filter(Boolean);
  }
  if (typeof value === "string" && value.trim()) {
    return splitCsvText(value);
  }
  return [];
}

function getSuggestionText(row: ImportRow, key: string): string {
  const value = getSuggestionFields(row)[key]?.value;
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return "";
}

function countSuggestionFields(row: ImportRow): number {
  const diagnosticCount = Number((row.ai_suggestions_json?.diagnostic as Record<string, unknown> | undefined)?.useful_suggestion_count ?? -1);
  if (diagnosticCount >= 0) {
    return diagnosticCount;
  }
  return Object.values(getSuggestionFields(row)).filter((field) => {
    const value = field?.value;
    if (Array.isArray(value)) return value.length > 0;
    if (typeof value === "string") return value.trim().length > 0;
    return value !== undefined && value !== null;
  }).length;
}

function getProviderLabel(row: ImportRow): { label: string; variant: "category" | "subcategory" | "tag" } {
  const providerStatus = String((row.ai_suggestions_json?.diagnostic as Record<string, unknown> | undefined)?.provider_status || row.ai_suggestions_json?.provider || "").toLowerCase();
  if (providerStatus === "openai") {
    return { label: "OpenAI", variant: "category" };
  }
  if (providerStatus === "openai_empty") {
    return { label: "OpenAI tom", variant: "tag" };
  }
  if (providerStatus.includes("fallback")) {
    return { label: "Fallback", variant: "subcategory" };
  }
  return { label: "Ukjent", variant: "tag" };
}

function getDiagnosticMeta(row: ImportRow): { title: string; detail: string; helper: string } {
  const diagnostic = (row.ai_suggestions_json?.diagnostic as Record<string, unknown> | undefined) ?? {};
  const status = String(diagnostic.provider_status || row.ai_suggestions_json?.provider || "");
  const fallbackReason = String(diagnostic.fallback_reason || "");
  const openaiError = String(diagnostic.openai_error || "");

  if (status === "openai") {
    return {
      title: "OpenAI",
      detail: "OpenAI svarte med brukbare forslag for denne raden.",
      helper: "",
    };
  }
  if (status === "openai_empty") {
    return {
      title: "OpenAI uten forslag",
      detail: "OpenAI svarte, men ga ingen brukbare forslag for denne raden.",
      helper: "Ingen brukbare OpenAI-forslag",
    };
  }
  if (status === "fallback_openai_error") {
    return {
      title: "Fallback etter OpenAI-feil",
      detail: `OpenAI feilet${openaiError ? ` (${openaiError})` : ""}, så raden bruker heuristisk fallback.`,
      helper: openaiError ? `Feil: ${openaiError}` : "OpenAI-feil",
    };
  }
  if (status === "fallback_openai_disabled") {
    return {
      title: "Fallback, OpenAI av",
      detail: "OpenAI er deaktivert i miljøet, så raden bruker heuristisk fallback.",
      helper: "OpenAI deaktivert",
    };
  }
  if (status === "fallback_openai_unavailable") {
    return {
      title: "Fallback, OpenAI utilgjengelig",
      detail: "OpenAI er ikke tilgjengelig i miljøet eller mangler konfigurasjon, så raden bruker heuristisk fallback.",
      helper: fallbackReason === "missing_api_key" ? "Mangler API-nøkkel" : "OpenAI utilgjengelig",
    };
  }
  if (status.startsWith("fallback")) {
    return {
      title: "Heuristisk fallback",
      detail: "Denne raden bruker heuristiske forslag, ikke OpenAI.",
      helper: fallbackReason === "heuristic_only" ? "Kun heuristikk" : "Fallback",
    };
  }
  return {
    title: "Ukjent provider",
    detail: "Provider-status er uklar for denne raden.",
    helper: "Sjekk preview-data",
  };
}

function renderSuggestionValue(value: unknown): string {
  if (Array.isArray(value)) return value.map((item) => String(item)).join(", ");
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return "";
}

function getFirstText(...values: unknown[]): string {
  for (const value of values) {
    if (typeof value === "string" && value.trim()) return value;
  }
  return "";
}

function splitCsvText(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function summarizeLinkValues(values: string[]): string[] {
  const unique = new Set<string>();
  values.forEach((value) => {
    const trimmed = value.trim();
    if (trimmed) unique.add(trimmed);
  });
  return Array.from(unique);
}

function shortenDisplayText(value: string, limit: number): string {
  const trimmed = value.trim();
  if (trimmed.length <= limit) {
    return trimmed;
  }
  return `${trimmed.slice(0, Math.max(0, limit - 1))}…`;
}

function asCandidateList(value: unknown): Array<{ id: number; label?: string; score?: number; reason?: string }> {
  return Array.isArray(value)
    ? value.filter((item): item is { id: number; label?: string; score?: number; reason?: string } => Boolean(item && typeof item === "object" && "id" in item))
    : [];
}

function getExistingSuggestionStates(row: ImportRow): Record<string, SuggestionState> {
  const states: Record<string, SuggestionState> = {};
  row.decisions.forEach((decision) => {
    const suggestionKey = String(decision.payload_json.suggestion_key ?? "");
    if (!suggestionKey) return;
    if (decision.decision_type === "ACCEPT_AI_SUGGESTION") states[suggestionKey] = "accepted";
    if (decision.decision_type === "IGNORE_AI_SUGGESTION") states[suggestionKey] = "ignored";
  });
  return states;
}

function getExistingDecisionType<T extends ImportDecision["decision_type"]>(row: ImportRow, decisionTypes: T[]): T | null {
  const match = row.decisions.find((decision) => decisionTypes.includes(decision.decision_type as T));
  return (match?.decision_type as T | undefined) ?? null;
}

function getExistingDecisionId(row: ImportRow, decisionType: ImportDecision["decision_type"], field: string): number | "" {
  const match = row.decisions.find((decision) => decision.decision_type === decisionType);
  const value = match?.payload_json?.[field];
  return typeof value === "number" ? value : "";
}

function getAcceptedDecisionValue(row: ImportRow, suggestionKey: string): string {
  const match = row.decisions.find(
    (decision) => decision.decision_type === "ACCEPT_AI_SUGGESTION" && decision.payload_json.suggestion_key === suggestionKey,
  );
  return renderSuggestionValue(match?.payload_json?.value);
}

function getAcceptedDecisionArray(row: ImportRow, suggestionKey: string): string[] {
  const match = row.decisions.find(
    (decision) => decision.decision_type === "ACCEPT_AI_SUGGESTION" && decision.payload_json.suggestion_key === suggestionKey,
  );
  const value = match?.payload_json?.value;
  return Array.isArray(value) ? value.map((item) => String(item)).filter(Boolean) : [];
}

function findCategoryIdByName(categories: Category[], name: string): number | "" {
  const match = categories.find((category) => category.name.toLowerCase() === name.toLowerCase());
  return match?.id ?? "";
}

function findSubcategoryIdByName(subcategories: Subcategory[], name: string): number | "" {
  const match = subcategories.find((subcategory) => subcategory.name.toLowerCase() === name.toLowerCase());
  return match?.id ?? "";
}

function findCategoryIdForSubcategory(subcategories: Subcategory[], subcategoryId: number | ""): number | "" {
  if (!subcategoryId) return "";
  const match = subcategories.find((subcategory) => subcategory.id === subcategoryId);
  return match?.category.id ?? "";
}

function filterSubcategories(categoryId: number | "", subcategories: Subcategory[]): Subcategory[] {
  if (!categoryId) return subcategories;
  return subcategories.filter((subcategory) => subcategory.category.id === categoryId);
}

function getNestedSuggestedFallback(row: ImportRow, key: string): string {
  const normalized = row.normalized_payload_json as Record<string, any>;
  if (key.startsWith("organization_")) {
    const orgKey = key.replace("organization_", "");
    return normalized.organization?.[orgKey] ?? "";
  }
  if (key.startsWith("person_")) {
    const personKey = key.replace("person_", "");
    return normalized.person?.[personKey] ?? "";
  }
  return "";
}
