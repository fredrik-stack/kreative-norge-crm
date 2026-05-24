import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Fragment } from "react";
import { createPortal } from "react-dom";
import { Field } from "../components/Field";
import { useEditor } from "../context/EditorContext";
import { getExportJobFileUrl, lookupImportJobBrreg, type OrganizationPatch } from "../api";
import { useExportJobs } from "../hooks/useExportJobs";
import { useImportJobs } from "../hooks/useImportJobs";
import type { Category, ImportDecision, ImportRow, Organization, Subcategory } from "../types";

const EXPORT_FIELD_OPTIONS = [
  "organization_name",
  "organization_org_number",
  "organization_email",
  "organization_phone",
  "organization_municipalities",
  "organization_categories",
  "organization_subcategories",
  "organization_tags",
  "organization_internal_tags",
  "organization_is_published",
  "person_full_name",
  "person_title",
  "person_email",
  "person_phone",
  "person_municipality",
  "person_categories",
  "person_subcategories",
  "person_tags",
  "person_internal_tags",
  "link_status",
  "link_publish_person",
];

const SIMPLE_EDITABLE_SUGGESTION_FIELDS = [
  "organization_name",
  "organization_org_number",
  "organization_email",
  "organization_municipalities",
  "organization_website_url",
  "organization_instagram_url",
  "organization_tiktok_url",
  "organization_linkedin_url",
  "organization_facebook_url",
  "organization_youtube_url",
  "organization_description",
  "person_title",
  "person_email",
  "person_municipality",
  "person_website_url",
  "person_instagram_url",
  "person_tiktok_url",
  "person_linkedin_url",
  "person_facebook_url",
  "person_youtube_url",
] as const;

const FIELD_LABELS: Record<string, string> = {
  organization_name: "Aktørnavn",
  organization_org_number: "Org.nr",
  organization_email: "E-post",
  organization_municipalities: "Kommune / steder",
  organization_website_url: "Nettside",
  organization_instagram_url: "Instagram",
  organization_tiktok_url: "TikTok",
  organization_linkedin_url: "LinkedIn",
  organization_facebook_url: "Facebook",
  organization_youtube_url: "YouTube",
  organization_description: "Beskrivelse",
  person_title: "Tittel",
  person_email: "Person e-post",
  person_municipality: "Personkommune",
  person_website_url: "Personnettside",
  person_instagram_url: "Person Instagram",
  person_tiktok_url: "Person TikTok",
  person_linkedin_url: "Person LinkedIn",
  person_facebook_url: "Person Facebook",
  person_youtube_url: "Person YouTube",
  suggested_categories: "Hovedkategori",
  suggested_subcategories: "Underkategori",
};

const SUBCATEGORY_ALIASES: Record<string, string> = {
  "produksjon": "Filmproduksjon",
  "foto/lys": "Foto/ Lys",
  "foto / lys": "Foto/ Lys",
};

const CANONICAL_CATEGORY_ORDER = [
  "Musikk",
  "Film",
  "Kunst & Design",
  "Scenekunst",
] as const;

const CANONICAL_SUBCATEGORY_ORDER = [
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

const MODE_LABELS: Record<"ORGANIZATIONS_ONLY" | "PEOPLE_ONLY", string> = {
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
  skipRow: boolean;
  organizationDecision: "NONE" | "USE_EXISTING_ORGANIZATION";
  personDecision: "NONE" | "USE_EXISTING_PERSON" | "CREATE_NEW_PERSON";
  organizationId: number | "";
  organizationSearchText: string;
  personId: number | "";
  categoryId: number | "";
  subcategoryId: number | "";
  categoryTouched: boolean;
  subcategoryTouched: boolean;
  tagsText: string;
  organizationInternalTagsText: string;
  personInternalTagsText: string;
  organizationIsPublished: boolean;
  fieldValues: Record<string, string>;
  suggestionStates: Record<string, SuggestionState>;
};

type QuickOrganizationFieldErrors = Partial<Record<
  | "name"
  | "org_number"
  | "email"
  | "phone"
  | "website_url"
  | "facebook_url"
  | "instagram_url"
  | "tiktok_url"
  | "linkedin_url"
  | "youtube_url",
  string
>>;

export function ImportExportPage() {
  const editor = useEditor();
  const importJobs = useImportJobs(editor.tenantId);
  const exportJobs = useExportJobs(editor.tenantId);
  const [sourceType, setSourceType] = useState<"CSV" | "XLSX">("CSV");
  const [importMode, setImportMode] = useState<"ORGANIZATIONS_ONLY" | "PEOPLE_ONLY">("ORGANIZATIONS_ONLY");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [expandedRowId, setExpandedRowId] = useState<number | null>(null);
  const [skipUnresolved, setSkipUnresolved] = useState(false);
  const [showImportHistory, setShowImportHistory] = useState(false);
  const [format, setFormat] = useState<"CSV" | "XLSX">("CSV");
  const [exportType, setExportType] = useState<"SEARCH_RESULTS" | "ADMIN_FULL" | "PERSONS_ONLY" | "ORGANIZATIONS_ONLY">("SEARCH_RESULTS");
  const [fieldSelection, setFieldSelection] = useState<string[]>([
    "organization_name",
    "person_full_name",
    "organization_email",
    "person_email",
  ]);
  const [filterQuery, setFilterQuery] = useState("");
  const primaryImportJob = useMemo(() => (
    importJobs.jobs.find((job) => job.id === importJobs.selectedJobId)
    ?? importJobs.jobs[0]
    ?? null
  ), [importJobs.jobs, importJobs.selectedJobId]);

  const visibleImportJobs = useMemo(() => {
    if (showImportHistory) return importJobs.jobs;
    return primaryImportJob ? [primaryImportJob] : [];
  }, [importJobs.jobs, primaryImportJob, showImportHistory]);

  const hiddenImportJobsCount = Math.max(importJobs.jobs.length - visibleImportJobs.length, 0);

  useEffect(() => {
    if (showImportHistory || !primaryImportJob) return;
    if (importJobs.selectedJobId === primaryImportJob.id) return;
    importJobs.setSelectedJobId(primaryImportJob.id);
  }, [showImportHistory, primaryImportJob, importJobs.selectedJobId, importJobs.setSelectedJobId]);

  async function handlePreview() {
    if (!selectedFile || !editor.tenantId) return;
    const created = await importJobs.createJob({ source_type: sourceType, import_mode: importMode });
    if (!created) return;
    const uploaded = await importJobs.uploadFile(selectedFile, created.id);
    if (!uploaded) return;
    const previewed = await importJobs.runPreview(created.id);
    if (!previewed) return;
    setSelectedFile(null);
  }

  return (
    <main className="import-export-layout">
      <section className="panel import-export-panel">
        <div className="sidebar-header">
          <div>
            <p className="eyebrow small">Import</p>
            <h2>Importjobber</h2>
          </div>
          <div className="import-header-meta">
            <span className="meta">{visibleImportJobs.length} vist</span>
            {hiddenImportJobsCount > 0 ? (
              <button
                type="button"
                className="ghost-button compact-button"
                onClick={() => setShowImportHistory((current) => !current)}
              >
                {showImportHistory ? "Skjul historikk" : `Vis historikk (${hiddenImportJobsCount})`}
              </button>
            ) : null}
          </div>
        </div>
        {importJobs.forbidden ? <div className="banner error">Du har ikke tilgang til import for denne tenanten.</div> : null}
        {importJobs.error ? <div className="banner error">{importJobs.error}</div> : null}

        <div className={`import-export-grid ${importJobs.selectedJob ? "review-active" : ""}`}>
          <div className="import-export-sidebar">
            <div className="job-list">
              {visibleImportJobs.map((job) => (
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
                <select value={importMode} onChange={(e) => setImportMode(e.target.value as "ORGANIZATIONS_ONLY" | "PEOPLE_ONLY")}> 
                  <option value="ORGANIZATIONS_ONLY">Aktører</option>
                  <option value="PEOPLE_ONLY">Personer</option>
                </select>
              </Field>
            </div>

            <ImportReviewWorkspace
              editor={editor}
              importJobs={importJobs}
              selectedFile={selectedFile}
              setSelectedFile={setSelectedFile}
              skipUnresolved={skipUnresolved}
              setSkipUnresolved={setSkipUnresolved}
              expandedRowId={expandedRowId}
              setExpandedRowId={setExpandedRowId}
              pendingImportMode={importMode}
              onPreview={() => void handlePreview()}
            />
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
  pendingImportMode: "ORGANIZATIONS_ONLY" | "PEOPLE_ONLY";
  onPreview: () => void;
}) {
  const { editor, importJobs, selectedFile, setSelectedFile, skipUnresolved, setSkipUnresolved, expandedRowId, setExpandedRowId, pendingImportMode, onPreview } = props;
  const selectedJob = importJobs.selectedJob;
  const rows = importJobs.rowsPage?.results ?? [];
  const summary = selectedJob?.summary_json ?? {};
  const unresolvedCount = Number(summary.review_required_rows ?? 0);
  const aiStatus = String(summary.ai_generation_status ?? "");
  const aiCompletedCount = Number(summary.rows_ai_completed ?? 0);
  const aiFailedCount = Number(summary.rows_ai_failed ?? 0);
  const aiOpenaiRows = Number(summary.rows_using_openai ?? 0);
  const aiFallbackRows = Number(summary.rows_using_fallback ?? 0);
  const aiHasProgress = aiCompletedCount > 0 || aiFailedCount > 0;
  const aiHasAttemptHistory =
    aiHasProgress ||
    aiOpenaiRows > 0 ||
    aiFallbackRows > 0 ||
    aiStatus === "completed" ||
    aiStatus === "failed" ||
    aiStatus === "partially_failed";
  const commitReadyStatuses = ["PREVIEW_READY", "AWAITING_REVIEW", "FAILED"];
  const commitBlockedReason = !selectedJob
    ? "Ingen preview er kjørt ennå."
    : !commitReadyStatuses.includes(selectedJob?.status ?? "")
      ? "Importjobben er ikke klar for commit ennå."
      : importJobs.busyAction === "commit"
        ? "Commit pågår…"
        : unresolvedCount > 0 && !skipUnresolved
          ? `${unresolvedCount} rad${unresolvedCount === 1 ? "" : "er"} står fortsatt til review. Fullfør review eller kryss av for å hoppe over uavklarte rader.`
          : null;
  const commitStatusHint = selectedJob?.status === "FAILED" && !commitBlockedReason
    ? "Forrige commit feilet. Du kan prøve commit på nytt."
    : null;
  const mode = normalizeImportMode(selectedJob?.import_mode, pendingImportMode);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const showPersonColumns = mode !== "ORGANIZATIONS_ONLY";
  const orgLabel = mode === "PEOPLE_ONLY" ? "Knyttet aktør" : "Aktør";
  const aiProgressLabel = getAiProgressLabel(summary);
  const expandedRow = useMemo(
    () => rows.find((candidate) => candidate.id === expandedRowId) ?? null,
    [rows, expandedRowId],
  );
  const importCategories = useMemo(
    () =>
      editor.categories
        .filter((category) => CANONICAL_CATEGORY_ORDER.includes(category.name as (typeof CANONICAL_CATEGORY_ORDER)[number]))
        .sort(
          (a, b) =>
            CANONICAL_CATEGORY_ORDER.indexOf(a.name as (typeof CANONICAL_CATEGORY_ORDER)[number]) -
            CANONICAL_CATEGORY_ORDER.indexOf(b.name as (typeof CANONICAL_CATEGORY_ORDER)[number]),
        ),
    [editor.categories],
  );
  const importSubcategories = useMemo(
    () =>
      editor.subcategories
        .filter((subcategory) => CANONICAL_SUBCATEGORY_ORDER.includes(subcategory.name as (typeof CANONICAL_SUBCATEGORY_ORDER)[number]))
        .sort(
          (a, b) =>
            CANONICAL_SUBCATEGORY_ORDER.indexOf(a.name as (typeof CANONICAL_SUBCATEGORY_ORDER)[number]) -
            CANONICAL_SUBCATEGORY_ORDER.indexOf(b.name as (typeof CANONICAL_SUBCATEGORY_ORDER)[number]),
        ),
    [editor.subcategories],
  );

  useEffect(() => {
    if (expandedRowId && !expandedRow) {
      setExpandedRowId(null);
    }
  }, [expandedRowId, expandedRow, setExpandedRowId]);

  return (
    <>
      <div className="import-toolbar">
        <Field label="Velg fil">
          <div className="file-picker-field">
            <input
              ref={fileInputRef}
              className="visually-hidden-input"
              aria-label="Velg fil"
              type="file"
              accept=".csv,.xlsx"
              onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
            />
            <button type="button" className="ghost-button" onClick={() => fileInputRef.current?.click()}>
              Velg fil
            </button>
            <span className="meta">{selectedFile?.name || selectedJob?.filename || "Ingen fil valgt ennå"}</span>
          </div>
        </Field>
        <button
          type="button"
          className="primary-button"
          disabled={!selectedFile || importJobs.busyAction === "preview" || importJobs.busyAction === "upload" || importJobs.busyAction === "create"}
          onClick={onPreview}
        >
          Kjør review
        </button>
      </div>

      <div className="import-summary-grid">
        <SummaryCard label="Rader totalt" value={summary.rows_total} />
        <SummaryCard label="Til review" value={summary.review_required_rows} />
        <SummaryCard label="AI-status" value={aiProgressLabel} />
        <SummaryCard
          label="AI fremdrift"
          value={`${Number(summary.rows_ai_completed ?? 0)} ferdig · ${Number(summary.rows_ai_pending ?? 0)} venter · ${Number(summary.rows_ai_failed ?? 0)} feilet`}
        />
      </div>

      {selectedJob ? (
        <div className="import-secondary-actions">
          <button
            type="button"
            className="ghost-button compact-button"
            disabled={
              !commitReadyStatuses.includes(selectedJob?.status ?? "") ||
              importJobs.busyAction === "generate-ai"
            }
            onClick={() =>
              void importJobs.generateAi(
                aiStatus === "failed" || aiStatus === "partially_failed",
                aiHasAttemptHistory,
              )
            }
          >
            {importJobs.busyAction === "generate-ai"
              ? "Genererer AI..."
              : aiHasAttemptHistory
                  ? "Kjør AI på nytt"
                  : "Hent AI-forslag"}
          </button>
        </div>
      ) : null}

      {!selectedJob ? <div className="empty-state">Velg fil og klikk «Kjør review» for å opprette en ny importjobb.</div> : null}

      {selectedJob ? (
      <div className="overview-table-wrap import-review-wrap">
        <table className="overview-table import-review-table">
          <thead>
            <tr>
              <th>Rad</th>
              <th>{orgLabel}</th>
              {showPersonColumns ? <th>Person</th> : null}
              {showPersonColumns ? <th>Tittel</th> : null}
              <th>Org.nr</th>
              <th>E-post</th>
              <th>AI e-post</th>
              <th>Telefon</th>
              <th>Nå kommune</th>
              <th>AI kommune</th>
              <th>Nå hovedkategori</th>
              <th>AI hovedkategori</th>
              <th>Nå underkategori</th>
              <th>AI underkategori</th>
              <th>Nå tags</th>
              <th>Nå interne tags</th>
              <th>Nå nettside</th>
              <th>AI nettside</th>
              <th>Nå profiler</th>
              <th>AI profiler</th>
              <th>Nå beskrivelse</th>
              <th>Provider</th>
              <th>Review-status</th>
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
              const currentOrganizationLabel = mode === "PEOPLE_ONLY"
                ? getCurrentOrganizationLabel(row, editor.organizations)
                : getCurrentText(row, ["organization_name"]);
              const currentPersonLabel = getCurrentText(row, ["person_full_name"]);
              const currentPersonTitle = getCurrentText(row, ["person_title"]);
              const municipalitySuggestion = mode === "ORGANIZATIONS_ONLY"
                ? getSuggestionText(row, "organization_municipalities")
                : getSuggestionText(row, "person_municipality");
              const websiteSuggestion = mode === "ORGANIZATIONS_ONLY"
                ? getSuggestionText(row, "organization_website_url")
                : getSuggestionText(row, "person_website_url");
              const currentEmail = getCurrentText(row, mode === "ORGANIZATIONS_ONLY" ? ["organization_email"] : ["person_email"]);
              const currentPhone = getCurrentText(row, mode === "ORGANIZATIONS_ONLY" ? ["organization_phone"] : ["person_phone"]);
              const suggestedEmail = mode === "ORGANIZATIONS_ONLY"
                ? getSuggestionText(row, "organization_email")
                : getSuggestionText(row, "person_email");
              const currentWebsite = mode === "ORGANIZATIONS_ONLY"
                ? getCurrentText(row, ["organization_website_url"])
                : getCurrentText(row, ["person_website_url"]);
              const currentSocials = summarizeLinkValues([
                ...(mode === "ORGANIZATIONS_ONLY"
                  ? [
                    getCurrentText(row, ["organization_instagram_url"]),
                    getCurrentText(row, ["organization_tiktok_url"]),
                    getCurrentText(row, ["organization_linkedin_url"]),
                    getCurrentText(row, ["organization_facebook_url"]),
                    getCurrentText(row, ["organization_youtube_url"]),
                  ]
                  : [
                    getCurrentText(row, ["person_instagram_url"]),
                    getCurrentText(row, ["person_tiktok_url"]),
                    getCurrentText(row, ["person_linkedin_url"]),
                    getCurrentText(row, ["person_facebook_url"]),
                    getCurrentText(row, ["person_youtube_url"]),
                  ]),
              ]);
              const socialSuggestions = summarizeLinkValues(
                SIMPLE_EDITABLE_SUGGESTION_FIELDS.filter((key) => (
                  key.endsWith("_url")
                  && key !== "organization_website_url"
                  && key !== "person_website_url"
                  && (mode === "ORGANIZATIONS_ONLY" ? key.startsWith("organization_") : key.startsWith("person_"))
                ))
                  .map((key) => getSuggestionText(row, key))
                  .filter(Boolean),
              );
              const currentDescription = mode === "ORGANIZATIONS_ONLY"
                ? getCurrentText(row, ["organization_description"])
                : getCurrentText(row, ["person_note"]);
              const provider = getProviderLabel(row);
              const diagnosticMeta = getDiagnosticMeta(row);
              const suggestionCount = countSuggestionFields(row);

              return (
                <Fragment key={row.id}>
                  <tr key={row.id} className={expanded ? "expanded" : ""}>
                    <td>{row.row_number}</td>
                    <td>
                      <ReviewValueCell current={currentOrganizationLabel} fallback="—" />
                    </td>
                    {showPersonColumns ? (
                      <td>
                        <ReviewValueCell current={currentPersonLabel} fallback="—" />
                      </td>
                    ) : null}
                    {showPersonColumns ? (
                      <td>
                        <ReviewValueCell current={currentPersonTitle} fallback="—" />
                      </td>
                    ) : null}
                    <td>{getCurrentText(row, ["organization_org_number"]) || "—"}</td>
                    <td>
                      <ReviewValueCell current={currentEmail} fallback="—" />
                    </td>
                    <td>
                      <ReviewValueCell current={suggestedEmail} fallback="Ingen forslag" onClick={() => setExpandedRowId(row.id)} clickable={Boolean(suggestedEmail)} />
                    </td>
                    <td>
                      <ReviewValueCell current={currentPhone} fallback="—" />
                    </td>
                    <td>
                      <ReviewValueCell
                        current={mode === "ORGANIZATIONS_ONLY" ? getCurrentText(row, ["organization_municipalities"]) : getCurrentText(row, ["person_municipality"])}
                        fallback="—"
                      />
                    </td>
                    <td>
                      <ReviewValueCell current={municipalitySuggestion} fallback="Ingen forslag" onClick={() => setExpandedRowId(row.id)} clickable={Boolean(municipalitySuggestion)} />
                    </td>
                    <td>
                      <ReviewSuggestionCell
                        variant="category"
                        currentValues={getCurrentCategoryValues(row, mode, editor.categories, editor.organizations)}
                        suggestedValues={[]}
                      />
                    </td>
                    <td>
                      <ReviewSuggestionCell variant="category" currentValues={[]} suggestedValues={categorySuggestions} onClick={() => setExpandedRowId(row.id)} />
                    </td>
                    <td>
                      <ReviewSuggestionCell
                        variant="subcategory"
                        currentValues={getCurrentSubcategoryValues(row, mode, editor.subcategories, editor.organizations)}
                        suggestedValues={[]}
                      />
                    </td>
                    <td>
                      <ReviewSuggestionCell variant="subcategory" currentValues={[]} suggestedValues={subcategorySuggestions} onClick={() => setExpandedRowId(row.id)} />
                    </td>
                    <td>
                      <ReviewSuggestionCell variant="tag" currentValues={getCurrentArray(row, mode === "ORGANIZATIONS_ONLY" ? ["organization_tags"] : ["person_tags"])} suggestedValues={[]} />
                    </td>
                    <td>
                      <ReviewSuggestionCell
                        variant="internal-tag"
                        currentValues={getCurrentArray(row, mode === "ORGANIZATIONS_ONLY" ? ["organization_internal_tags"] : ["person_internal_tags"])}
                        suggestedValues={[]}
                      />
                    </td>
                    <td>
                      <ReviewValueCell current={currentWebsite} fallback="Mangler" />
                    </td>
                    <td>
                      <ReviewValueCell current={websiteSuggestion} fallback="Ingen forslag" onClick={() => setExpandedRowId(row.id)} clickable={Boolean(websiteSuggestion)} />
                    </td>
                    <td>
                      <ReviewLinkCell values={currentSocials} emptyLabel="Ingen lenker" />
                    </td>
                    <td>
                      <ReviewLinkCell values={socialSuggestions} emptyLabel="Ingen forslag" onClick={() => setExpandedRowId(row.id)} clickable={socialSuggestions.length > 0} />
                    </td>
                    <td>
                      <ReviewTextCell value={currentDescription} emptyLabel="Mangler" />
                    </td>
                    <td>
                      <div className="review-provider-cell">
                        <span className={`mini-pill ${provider.variant}`}>{provider.label}</span>
                        <span className="meta">{suggestionCount > 0 ? `${suggestionCount} forslag` : "Ingen forslag"}</span>
                        {diagnosticMeta.helper ? <span className="meta">{diagnosticMeta.helper}</span> : null}
                      </div>
                    </td>
                    <td><span className="mini-pill subcategory">{getRowStatusLabel(row)}</span></td>
                    <td>{row.warnings_json.length}</td>
                    <td>{row.validation_errors_json.length}</td>
                    <td>
                      <div className="review-url-cell">
                        <button
                          type="button"
                          className="ghost-button compact-button"
                          onClick={() => {
                            if (!expanded) setExpandedRowId(row.id);
                          }}
                        >
                          {expanded ? "Åpen" : "Review"}
                        </button>
                      </div>
                    </td>
                  </tr>
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
      ) : null}

      {selectedJob && expandedRow ? (
        <ReviewRowModal onClose={() => setExpandedRowId(null)}>
          <InlineReviewEditor
            row={expandedRow}
            importMode={mode}
            organizations={editor.organizations}
            categories={importCategories}
            subcategories={importSubcategories}
            onCreateOrganization={editor.quickCreateOrganization}
            tenantId={editor.tenantId}
            importJobId={selectedJob.id}
            onSave={(payload) => importJobs.saveDecisions([{ row_id: expandedRow.id, decisions: payload }])}
            onClose={() => setExpandedRowId(null)}
          />
        </ReviewRowModal>
      ) : null}

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
        {commitBlockedReason ? <span className="meta commit-hint">{commitBlockedReason}</span> : null}
        {!commitBlockedReason && commitStatusHint ? <span className="meta commit-hint">{commitStatusHint}</span> : null}
        {selectedJob && unresolvedCount > 0 ? (
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
          disabled={Boolean(commitBlockedReason)}
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
  importMode: "ORGANIZATIONS_ONLY" | "PEOPLE_ONLY";
  organizations: Organization[];
  categories: Category[];
  subcategories: Subcategory[];
  onCreateOrganization: (draft: OrganizationPatch) => Promise<Organization>;
  tenantId: number | null;
  importJobId: number;
  onSave: (payload: Array<{ decision_type: ImportDecision["decision_type"]; payload_json?: Record<string, unknown> }>) => Promise<unknown> | null;
  onClose: () => void;
}) {
  const { row, importMode, organizations, categories, subcategories, onCreateOrganization, tenantId, importJobId, onSave, onClose } = props;
  const suggestedFields = useMemo(() => getSuggestionFields(row), [row]);
  const categorySuggestions = getSuggestionValues(row, "suggested_categories");
  const subcategorySuggestions = getSuggestionValues(row, "suggested_subcategories");
  const suggestionStates = getExistingSuggestionStates(row);
  const actorOnly = importMode === "ORGANIZATIONS_ONLY";
  const personOnly = importMode === "PEOPLE_ONLY";
  const currentCategoryNames = getCurrentCategoryValues(row, importMode, categories, organizations);
  const currentSubcategoryNames = getCurrentSubcategoryValues(row, importMode, subcategories, organizations);
  const acceptedSuggestedTags = getAcceptedArrayState(row, "suggested_tags");
  const acceptedOrganizationInternalTags = getAcceptedArrayState(row, "organization_internal_tags");
  const acceptedPersonInternalTags = getAcceptedArrayState(row, "person_internal_tags");
  const currentSubcategoryId = findSubcategoryIdByName(subcategories, currentSubcategoryNames[0] || "");
  const inferredCategoryId = findCategoryIdForSubcategory(subcategories, currentSubcategoryId);
  const [draft, setDraft] = useState<ReviewDraft>(() => {
    const initialFieldValues: Record<string, string> = {};
    SIMPLE_EDITABLE_SUGGESTION_FIELDS.forEach((key) => {
      initialFieldValues[key] =
        getAcceptedDecisionValue(row, key) ||
        getResolvedText(row, [key]);
    });
    return {
      skipRow: getExistingDecisionType(row, ["SKIP_ROW"]) === "SKIP_ROW",
      organizationDecision: getExistingDecisionType(row, ["USE_EXISTING_ORGANIZATION"]) ?? "NONE",
      personDecision: getExistingDecisionType(row, ["USE_EXISTING_PERSON", "CREATE_NEW_PERSON"]) ?? "NONE",
      organizationId: getExistingDecisionId(row, "USE_EXISTING_ORGANIZATION", "organization_id"),
      organizationSearchText: getCurrentOrganizationLabel(row, organizations),
      personId: getExistingDecisionId(row, "USE_EXISTING_PERSON", "person_id"),
      categoryId:
        getExistingDecisionId(row, "MAP_CATEGORY", "category_id") ||
        inferredCategoryId ||
        findCategoryIdByName(
          categories,
          currentCategoryNames[0] || "",
        ),
      subcategoryId:
        getExistingDecisionId(row, "MAP_SUBCATEGORY", "subcategory_id") ||
        findSubcategoryIdByName(
          subcategories,
          currentSubcategoryNames[0] || "",
        ),
      categoryTouched:
        hasAcceptedSuggestionDecision(row, "suggested_categories")
        && getAcceptedDecisionArray(row, "suggested_categories").length === 0,
      subcategoryTouched:
        hasAcceptedSuggestionDecision(row, "suggested_subcategories")
        && getAcceptedDecisionArray(row, "suggested_subcategories").length === 0,
      tagsText:
        acceptedSuggestedTags.exists
          ? acceptedSuggestedTags.value.join(", ")
          : getCurrentArray(row, actorOnly ? ["organization_tags"] : ["person_tags"]).join(", "),
      organizationInternalTagsText:
        acceptedOrganizationInternalTags.exists
          ? acceptedOrganizationInternalTags.value.join(", ")
          : getCurrentArray(row, ["organization_internal_tags"]).join(", "),
      personInternalTagsText:
        acceptedPersonInternalTags.exists
          ? acceptedPersonInternalTags.value.join(", ")
          : getCurrentArray(row, ["person_internal_tags"]).join(", "),
      organizationIsPublished:
        getAcceptedDecisionBoolean(row, "organization_is_published")
        ?? getCurrentBoolean(row, ["organization_is_published"]),
      fieldValues: initialFieldValues,
      suggestionStates,
    };
  });
  useEffect(() => {
    if (draft.categoryId) return;
    if (!currentSubcategoryId) return;
    if (!inferredCategoryId) return;
    setDraft((current) => (current.categoryId ? current : { ...current, categoryId: inferredCategoryId }));
  }, [currentSubcategoryId, draft.categoryId, inferredCategoryId]);

  const filteredSubcategories = useMemo(() => {
    const options = filterSubcategories(draft.categoryId, subcategories);
    if (!draft.subcategoryId) return options;
    const selected = subcategories.find((subcategory) => subcategory.id === draft.subcategoryId);
    if (!selected) return options;
    return options.some((subcategory) => subcategory.id === selected.id) ? options : [selected, ...options];
  }, [draft.categoryId, draft.subcategoryId, subcategories]);
  const organizationSearchMatches = useMemo(() => {
    if (!personOnly || draft.organizationDecision !== "USE_EXISTING_ORGANIZATION") return [];
    const query = draft.organizationSearchText.trim().toLowerCase();
    if (!query) return organizations.slice(0, 12);
    return organizations.filter((organization) => organization.name.toLowerCase().includes(query)).slice(0, 12);
  }, [draft.organizationDecision, draft.organizationSearchText, organizations, personOnly]);
  const selectedExistingOrganization =
    personOnly && draft.organizationDecision === "USE_EXISTING_ORGANIZATION" && draft.organizationId
      ? organizations.find((organization) => organization.id === draft.organizationId) ?? null
      : null;
  const existingOrganizationCategoryNames =
    selectedExistingOrganization && !draft.categoryTouched && !draft.subcategoryTouched && !draft.categoryId && !draft.subcategoryId
      ? selectedExistingOrganization.categories.map((category) => category.name)
      : [];
  const existingOrganizationSubcategoryNames =
    selectedExistingOrganization && !draft.categoryTouched && !draft.subcategoryTouched && !draft.categoryId && !draft.subcategoryId
      ? selectedExistingOrganization.subcategories.map((subcategory) => subcategory.name)
      : [];
  const visibleCurrentCategoryNames =
    existingOrganizationCategoryNames.length > 0 ? existingOrganizationCategoryNames : currentCategoryNames;
  const visibleCurrentSubcategoryBaseNames =
    existingOrganizationSubcategoryNames.length > 0 ? existingOrganizationSubcategoryNames : currentSubcategoryNames;
  const currentCategoryLabel = visibleCurrentCategoryNames[0] || "";
  const categorySelectValue = draft.categoryId ? String(draft.categoryId) : currentCategoryLabel;
  const visibleCurrentSubcategoryId = findSubcategoryIdByName(subcategories, visibleCurrentSubcategoryBaseNames[0] || "");
  const currentSubcategoryCategoryId = findCategoryIdForSubcategory(subcategories, visibleCurrentSubcategoryId || currentSubcategoryId);
  const canDisplayCurrentSubcategory =
    !(visibleCurrentSubcategoryId || currentSubcategoryId)
    || !draft.categoryId
    || currentSubcategoryCategoryId === draft.categoryId;
  const visibleCurrentSubcategoryNames = canDisplayCurrentSubcategory ? visibleCurrentSubcategoryBaseNames : [];
  const currentSubcategoryLabel = visibleCurrentSubcategoryNames[0] || "";
  const subcategorySelectValue = draft.subcategoryId ? String(draft.subcategoryId) : currentSubcategoryLabel;
  const visibleCategorySuggestions = (draft.suggestionStates.suggested_categories ?? "pending") === "ignored" ? [] : categorySuggestions;
  const visibleSubcategorySuggestions = (draft.suggestionStates.suggested_subcategories ?? "pending") === "ignored" ? [] : subcategorySuggestions;
  const brregCandidates = getBrregCandidates(row);
  const duplicateCandidates = asCandidateList(row.ai_suggestions_json.organization_match_candidates);
  const diagnosticMeta = getDiagnosticMeta(row);
  const organizationLockedToExisting = actorOnly && draft.organizationDecision === "USE_EXISTING_ORGANIZATION" && Boolean(draft.organizationId);
  const reviewLocked = draft.skipRow;
  const organizationDataLocked = organizationLockedToExisting || reviewLocked;
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [brregLookupState, setBrregLookupState] = useState<"idle" | "loading" | "done" | "error">("idle");
  const [brregLookupMessage, setBrregLookupMessage] = useState("");
  const lastBrregLookupRef = useRef("");
  const [createOrganizationOpen, setCreateOrganizationOpen] = useState(false);
  const [organizationCreateState, setOrganizationCreateState] = useState<"idle" | "saving" | "error">("idle");
  const [organizationCreateError, setOrganizationCreateError] = useState<string | null>(null);
  const [organizationFieldErrors, setOrganizationFieldErrors] = useState<QuickOrganizationFieldErrors>({});

  async function persistDraft(nextDraft: ReviewDraft, closeAfterSave = false) {
    setDraft(nextDraft);
    setSaveState("saving");
    try {
      await Promise.resolve(onSave(buildDecisions(row, importMode, nextDraft)));
      setSaveState("saved");
      if (closeAfterSave) {
        onClose();
        return;
      }
    } catch {
      setSaveState("error");
    }
  }

  function openCreateOrganizationModal() {
    setOrganizationCreateState("idle");
    setOrganizationCreateError(null);
    setOrganizationFieldErrors({});
    setCreateOrganizationOpen(true);
  }

  async function handleCreateOrganization(nextOrganizationDraft: OrganizationPatch) {
    const nextErrors = validateQuickOrganizationDraft(nextOrganizationDraft);
    if (Object.keys(nextErrors).length > 0) {
      setOrganizationFieldErrors(nextErrors);
      setOrganizationCreateState("error");
      setOrganizationCreateError("Rett feltene markert i rødt før du lagrer aktøren.");
      return;
    }

    setOrganizationCreateState("saving");
    setOrganizationCreateError(null);
    setOrganizationFieldErrors({});

    try {
      const createdOrganization = await onCreateOrganization(nextOrganizationDraft);
      setCreateOrganizationOpen(false);
      const nextDraft = {
        ...draft,
        organizationDecision: "USE_EXISTING_ORGANIZATION" as const,
        organizationId: createdOrganization.id,
      };
      await persistDraft(nextDraft);
      setOrganizationCreateState("idle");
    } catch (error) {
      setOrganizationCreateState("error");
      setOrganizationCreateError(error instanceof Error ? error.message : "Kunne ikke opprette aktøren.");
    }
  }

  function applyCategorySuggestion(name: string) {
    if (organizationDataLocked) return;
    const categoryId = findCategoryIdByName(categories, name);
    const nextDraft = {
      ...draft,
      categoryId,
      categoryTouched: true,
      suggestionStates: { ...draft.suggestionStates, suggested_categories: categoryId ? "accepted" : draft.suggestionStates.suggested_categories },
    };
    void persistDraft(nextDraft);
  }

  function applySubcategorySuggestion(name: string) {
    if (organizationDataLocked) return;
    const subcategoryId = findSubcategoryIdByName(subcategories, name);
    const relatedCategoryId = findCategoryIdForSubcategory(subcategories, subcategoryId);
    const nextDraft = {
      ...draft,
      categoryId: relatedCategoryId || draft.categoryId,
      subcategoryId,
      categoryTouched: true,
      subcategoryTouched: true,
      suggestionStates: {
        ...draft.suggestionStates,
        suggested_subcategories: subcategoryId ? "accepted" : draft.suggestionStates.suggested_subcategories,
      },
    };
    void persistDraft(nextDraft);
  }

  function removeTag(tag: string) {
    if (organizationDataLocked) return;
    const nextDraft = {
      ...draft,
      tagsText: splitCsvText(draft.tagsText).filter((item) => item.toLowerCase() !== tag.toLowerCase()).join(", "),
      suggestionStates: { ...draft.suggestionStates, suggested_tags: "accepted" as const },
    };
    void persistDraft(nextDraft);
  }

  function applyBrregCandidate(candidateId: number | string) {
    const candidate = brregCandidates.find((item) => item.id === String(candidateId));
    if (!candidate) return;
    const nextFieldValues = { ...draft.fieldValues };
    if (candidate.org_number) nextFieldValues.organization_org_number = candidate.org_number;
    if (candidate.municipality) nextFieldValues.organization_municipalities = candidate.municipality;
    if (candidate.website_url) nextFieldValues.organization_website_url = candidate.website_url;
    if (candidate.email) nextFieldValues.organization_email = candidate.email;
    const nextDraft = {
      ...draft,
      fieldValues: nextFieldValues,
      suggestionStates: {
        ...draft.suggestionStates,
        organization_org_number: candidate.org_number ? "accepted" as const : draft.suggestionStates.organization_org_number,
        organization_municipalities: candidate.municipality ? "accepted" as const : draft.suggestionStates.organization_municipalities,
        organization_website_url: candidate.website_url ? "accepted" as const : draft.suggestionStates.organization_website_url,
        organization_email: candidate.email ? "accepted" as const : draft.suggestionStates.organization_email,
      },
    };
    void persistDraft(nextDraft);
  }

  async function syncOrganizationNumberFromBrreg(orgNumberInput: string) {
    const normalizedOrgNumber = orgNumberInput.replace(/\D/g, "");
    if (!actorOnly || !tenantId || !importJobId || normalizedOrgNumber.length !== 9) return;
    if (lastBrregLookupRef.current === normalizedOrgNumber) return;

    setBrregLookupState("loading");
    setBrregLookupMessage("Henter fra BRREG…");
    try {
      const candidate = await lookupImportJobBrreg(tenantId, importJobId, normalizedOrgNumber);
      lastBrregLookupRef.current = normalizedOrgNumber;
      setBrregLookupState("done");
      setBrregLookupMessage(
        candidate.name
          ? `BRREG: ${candidate.name}${candidate.municipality ? ` · ${candidate.municipality}` : ""}`
          : "BRREG-data hentet",
      );
      setDraft((current) => {
        const nextFieldValues = { ...current.fieldValues };
        nextFieldValues.organization_org_number = candidate.org_number || normalizedOrgNumber;
        if (!nextFieldValues.organization_name?.trim()) {
          nextFieldValues.organization_name = candidate.name || "";
        }
        nextFieldValues.organization_municipalities = candidate.municipality || nextFieldValues.organization_municipalities || "";
        if (!nextFieldValues.organization_website_url?.trim() && candidate.website_url) {
          nextFieldValues.organization_website_url = candidate.website_url;
        }
        if (!nextFieldValues.organization_email?.trim() && candidate.email) {
          nextFieldValues.organization_email = candidate.email;
        }
        return {
          ...current,
          fieldValues: nextFieldValues,
          suggestionStates: {
            ...current.suggestionStates,
            organization_org_number: "accepted",
            organization_municipalities: candidate.municipality ? "accepted" : current.suggestionStates.organization_municipalities,
            organization_website_url: candidate.website_url ? "accepted" : current.suggestionStates.organization_website_url,
            organization_email: candidate.email ? "accepted" : current.suggestionStates.organization_email,
          },
        };
      });
    } catch (error) {
      setBrregLookupState("error");
      setBrregLookupMessage(error instanceof Error ? error.message : "Fant ikke BRREG-data for dette org.nr.");
    }
  }

  useEffect(() => {
    if (!actorOnly) return;
    const normalizedOrgNumber = (draft.fieldValues.organization_org_number || "").replace(/\D/g, "");
    if (normalizedOrgNumber.length !== 9) {
      if (brregLookupState !== "idle") {
        setBrregLookupState("idle");
        setBrregLookupMessage("");
      }
      lastBrregLookupRef.current = "";
      return;
    }
    const timer = window.setTimeout(() => {
      void syncOrganizationNumberFromBrreg(normalizedOrgNumber);
    }, 450);
    return () => window.clearTimeout(timer);
  }, [actorOnly, brregLookupState, draft.fieldValues.organization_org_number, importJobId, tenantId]);

  const visibleSuggestionFields = SIMPLE_EDITABLE_SUGGESTION_FIELDS.filter((fieldKey) => {
    if (actorOnly && (fieldKey === "organization_name" || fieldKey === "organization_org_number")) {
      return false;
    }
    return actorOnly ? fieldKey.startsWith("organization_") : fieldKey.startsWith("person_");
  });

  return (
    <div className="inline-review-editor">
      <div className="inline-review-grid single-column">
        <section className="editor-detail-section modal-section-card">
          <div className="modal-section-header">
            <h4>Rediger raskt</h4>
            <div className="review-header-meta">
              <span className={`mini-pill ${saveState === "saved" ? "category" : saveState === "error" ? "subcategory" : "tag"}`}>
                {saveState === "saving" ? "Lagrer…" : saveState === "saved" ? "Lagret" : saveState === "error" ? "Feil ved lagring" : diagnosticMeta.title}
              </span>
            </div>
          </div>
          <div className="modal-form-grid review-form-grid">
            {personOnly ? (
              <>
                <Field label="Aktørvalg">
                  <select
                    value={draft.organizationDecision}
                    onChange={(e) =>
                      setDraft((current) => ({
                        ...current,
                        organizationDecision: e.target.value as ReviewDraft["organizationDecision"],
                        organizationId: e.target.value === "USE_EXISTING_ORGANIZATION" ? current.organizationId : "",
                        organizationSearchText:
                          e.target.value === "USE_EXISTING_ORGANIZATION" ? current.organizationSearchText : "",
                      }))
                    }
                  >
                    <option value="NONE">Ingen</option>
                    <option value="USE_EXISTING_ORGANIZATION">Bruk eksisterende aktør</option>
                  </select>
                </Field>
                <div className="review-inline-cta">
                  <button type="button" className="ghost-button compact-button" onClick={openCreateOrganizationModal}>
                    Opprett ny aktør i eget vindu
                  </button>
                  <span className="meta">Aktørkobling er valgfri for personimport.</span>
                </div>
                <SuggestionCandidates
                  candidates={asCandidateList(row.ai_suggestions_json.organization_match_candidates)}
                  onUse={(id) => {
                    const organizationId = typeof id === "number" ? id : Number(id);
                    if (!organizationId) return;
                    const nextDraft = {
                      ...draft,
                      organizationDecision: "USE_EXISTING_ORGANIZATION" as const,
                      organizationId,
                      organizationSearchText:
                        organizations.find((organization) => organization.id === organizationId)?.name
                        ?? draft.organizationSearchText,
                    };
                    void persistDraft(nextDraft);
                  }}
                  emptyLabel="Ingen aktørkandidater"
                />
                {draft.organizationDecision === "USE_EXISTING_ORGANIZATION" ? (
                  <Field label="Velg aktør">
                    <div className="search-select-field">
                      <input
                        value={draft.organizationSearchText}
                        onChange={(e) =>
                          setDraft((current) => ({
                            ...current,
                            organizationSearchText: e.target.value,
                            organizationId:
                              current.organizationId &&
                              organizations.find((organization) => organization.id === current.organizationId)?.name === e.target.value
                                ? current.organizationId
                                : "",
                          }))
                        }
                        placeholder="Søk etter aktørnavn"
                      />
                      <div className="search-select-results" role="listbox" aria-label="Aktørsøk">
                        {organizationSearchMatches.length > 0 ? organizationSearchMatches.map((organization) => (
                          <button
                            key={organization.id}
                            type="button"
                            className={`search-select-option ${draft.organizationId === organization.id ? "active" : ""}`}
                            onClick={() => {
                              const nextDraft = {
                                ...draft,
                                organizationId: organization.id,
                                organizationSearchText: organization.name,
                              };
                              void persistDraft(nextDraft);
                            }}
                          >
                            <span>{organization.name}</span>
                            <span className="meta">#{organization.id}</span>
                          </button>
                        )) : (
                          <div className="search-select-empty">Ingen treff</div>
                        )}
                      </div>
                    </div>
                  </Field>
                ) : null}
              </>
            ) : null}

            {actorOnly ? (
              <Field label="Potensiell dublettkonflikt">
                <SuggestionCandidates
                  candidates={duplicateCandidates}
                  onUse={(id) => {
                    const organizationId = typeof id === "number" ? id : Number(id);
                    if (!organizationId) return;
                    const nextDraft = {
                      ...draft,
                      organizationDecision: "USE_EXISTING_ORGANIZATION" as const,
                      organizationId,
                    };
                    void persistDraft(nextDraft);
                  }}
                  emptyLabel="Ingen dublettkandidater"
                />
              </Field>
            ) : null}

            {actorOnly ? (
              <Field label="BRREG-kandidater">
                <SuggestionCandidates
                  candidates={brregCandidates}
                  onUse={applyBrregCandidate}
                  emptyLabel="Ingen BRREG-kandidater"
                />
              </Field>
            ) : null}

            <Field label="Commit">
              <label className="checkbox-row review-skip-toggle">
                <input
                  type="checkbox"
                  checked={draft.skipRow}
                  onChange={(e) => {
                    const nextDraft = {
                      ...draft,
                      skipRow: e.target.checked,
                    };
                    void persistDraft(nextDraft);
                  }}
                />
                <span>Ikke ta med denne raden i commit.</span>
              </label>
            </Field>

            {actorOnly ? (
              <Field label="Publisering">
                <label className="checkbox-row review-publish-toggle">
                  <input
                    type="checkbox"
                    checked={draft.organizationIsPublished}
                    disabled={organizationDataLocked}
                    onChange={(e) => {
                      const nextDraft = {
                        ...draft,
                        organizationIsPublished: e.target.checked,
                      };
                      void persistDraft(nextDraft);
                    }}
                  />
                  <span>Publiser aktør. Synlig i public API når slått på.</span>
                </label>
              </Field>
            ) : null}

            {reviewLocked ? (
              <p className="meta review-lock-message">
                Raden er markert for å hoppes over og tas ikke med i commit.
              </p>
            ) : null}

            {organizationLockedToExisting ? (
              <p className="meta review-lock-message">
                Eksisterende aktør er valgt. Aktørdata beholdes ved commit, og feltene under brukes ikke til å overskrive den.
              </p>
            ) : null}

            {actorOnly ? (
              <Field label="Aktørnavn">
                <div className="review-inline-field compact">
                  <input
                    value={draft.fieldValues.organization_name ?? ""}
                    disabled={organizationDataLocked}
                    onChange={(e) =>
                      setDraft((current) => ({
                        ...current,
                        fieldValues: { ...current.fieldValues, organization_name: e.target.value },
                        suggestionStates: {
                          ...current.suggestionStates,
                          organization_name: e.target.value
                            ? "accepted"
                            : getSuggestionText(row, "organization_name")
                              ? "ignored"
                              : current.suggestionStates.organization_name ?? "pending",
                        },
                      }))
                    }
                    placeholder="Offentlig navn på aktøren"
                  />
                </div>
              </Field>
            ) : null}

            {actorOnly ? (
              <Field label="Org.nr">
                <div className="review-inline-field compact">
                  <input
                    value={draft.fieldValues.organization_org_number ?? ""}
                    disabled={organizationDataLocked}
                    onChange={(e) =>
                      setDraft((current) => ({
                        ...current,
                        fieldValues: { ...current.fieldValues, organization_org_number: e.target.value },
                        suggestionStates: {
                          ...current.suggestionStates,
                          organization_org_number: e.target.value
                            ? "accepted"
                            : getSuggestionText(row, "organization_org_number")
                              ? "ignored"
                              : current.suggestionStates.organization_org_number ?? "pending",
                        },
                      }))
                    }
                    placeholder="9 sifre"
                  />
                  <div className="review-inline-actions">
                    <button
                      type="button"
                      className="ghost-button compact-button"
                      disabled={organizationDataLocked}
                      onClick={() => void syncOrganizationNumberFromBrreg(draft.fieldValues.organization_org_number || "")}
                    >
                      Synk fra BRREG
                    </button>
                    {brregLookupMessage ? (
                      <span className={`meta ${brregLookupState === "error" ? "error-text" : ""}`}>{brregLookupMessage}</span>
                    ) : null}
                  </div>
                </div>
              </Field>
            ) : null}

            <Field label="Hovedkategori">
              <select
                value={categorySelectValue}
                disabled={organizationDataLocked}
                onChange={(e) => {
                  const nextDraft = {
                    ...draft,
                    categoryId: (Number(e.target.value) || "") as number | "",
                    subcategoryId: "" as number | "",
                    categoryTouched: true,
                    subcategoryTouched: true,
                  };
                  void persistDraft(nextDraft);
                }}
              >
                <option value="">Ingen</option>
                {!draft.categoryId && currentCategoryLabel ? (
                  <option value={currentCategoryLabel}>{currentCategoryLabel}</option>
                ) : null}
                {categories.map((category) => (
                  <option key={category.id} value={category.id}>{category.name}</option>
                ))}
              </select>
              {visibleCategorySuggestions.length > 0 ? (
                <SuggestionPills
                  values={visibleCategorySuggestions}
                  emptyLabel="Ingen forslag"
                  state={draft.suggestionStates.suggested_categories ?? "pending"}
                  onAccept={(value) => applyCategorySuggestion(value)}
                  onIgnore={() => {
                    const nextDraft = {
                      ...draft,
                      suggestionStates: { ...draft.suggestionStates, suggested_categories: "ignored" as const },
                    };
                    void persistDraft(nextDraft);
                  }}
                />
              ) : null}
            </Field>
            <Field label="Underkategori">
              <select
                value={subcategorySelectValue}
                disabled={organizationDataLocked}
                onChange={(e) => {
                  const nextDraft = {
                    ...draft,
                    subcategoryId: (Number(e.target.value) || "") as number | "",
                    subcategoryTouched: true,
                  };
                  void persistDraft(nextDraft);
                }}
              >
                <option value="">Ingen</option>
                {!draft.subcategoryId && currentSubcategoryLabel ? (
                  <option value={currentSubcategoryLabel}>{currentSubcategoryLabel}</option>
                ) : null}
                {filteredSubcategories.map((subcategory) => (
                  <option key={subcategory.id} value={subcategory.id}>{subcategory.name}</option>
                ))}
              </select>
              {visibleCurrentSubcategoryNames.length > 0 ? (
                <div className="review-current-pill-row">
                  {visibleCurrentSubcategoryNames.map((name) => (
                    <span key={name} className="mini-pill subcategory">{name}</span>
                  ))}
                </div>
              ) : null}
              {visibleSubcategorySuggestions.length > 0 ? (
                <SuggestionPills
                  values={visibleSubcategorySuggestions}
                  emptyLabel="Ingen forslag"
                  state={draft.suggestionStates.suggested_subcategories ?? "pending"}
                  onAccept={(value) => applySubcategorySuggestion(value)}
                  onIgnore={() => {
                    const nextDraft = {
                      ...draft,
                      suggestionStates: { ...draft.suggestionStates, suggested_subcategories: "ignored" as const },
                    };
                    void persistDraft(nextDraft);
                  }}
                />
              ) : null}
            </Field>

            <Field label="Tags (kommaseparert)">
              <div className="tag-editor-field">
                <input
                  value={draft.tagsText}
                  disabled={organizationDataLocked}
                  onChange={(e) => setDraft((current) => ({ ...current, tagsText: e.target.value, suggestionStates: { ...current.suggestionStates, suggested_tags: "accepted" } }))}
                  placeholder="jazz, management"
                />
                {splitCsvText(draft.tagsText).length > 0 ? (
                  <div className="tag-chip-editor" aria-label="Valgte tags">
                    {splitCsvText(draft.tagsText).map((tag) => (
                      <button key={tag} type="button" className="tag-chip-edit" onClick={() => removeTag(tag)}>
                        <span>{tag}</span>
                        <span aria-hidden="true">×</span>
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>
            </Field>

            {actorOnly ? (
              <Field label="Aktør interne tags">
                <TagTextEditor
                  value={draft.organizationInternalTagsText}
                  placeholder="prioritet, partner, evalueres"
                  tone="internal"
                  disabled={organizationDataLocked}
                  onChange={(value) => setDraft((current) => ({ ...current, organizationInternalTagsText: value }))}
                />
              </Field>
            ) : null}
            {personOnly ? (
              <Field label="Person interne tags">
                <TagTextEditor
                  value={draft.personInternalTagsText}
                  placeholder="ny kontakt, sensitiv, følges opp"
                  tone="internal"
                  onChange={(value) => setDraft((current) => ({ ...current, personInternalTagsText: value }))}
                />
              </Field>
            ) : null}

            {visibleSuggestionFields.map((fieldKey) => {
              const suggestion = suggestedFields[fieldKey];
              const state = draft.suggestionStates[fieldKey] ?? "pending";
              return (
                <Field key={fieldKey} label={FIELD_LABELS[fieldKey] ?? fieldKey}>
                  <div className="review-inline-field compact">
                    <input
                      value={draft.fieldValues[fieldKey] ?? ""}
                      disabled={organizationDataLocked}
                      onChange={(e) =>
                        setDraft((current) => ({
                          ...current,
                        fieldValues: { ...current.fieldValues, [fieldKey]: e.target.value },
                        suggestionStates: {
                          ...current.suggestionStates,
                          [fieldKey]: e.target.value
                            ? "accepted"
                            : getSuggestionText(row, fieldKey)
                              ? "ignored"
                              : current.suggestionStates[fieldKey] ?? "pending",
                        },
                      }))
                    }
                      placeholder={suggestion ? `Forslag: ${renderSuggestionValue(suggestion.value)}` : "Tomt felt"}
                    />
                    {suggestion ? (
                      <div className="review-inline-actions">
                        <span className={`mini-pill ${state === "accepted" ? "category" : state === "ignored" ? "subcategory" : "tag"}`}>
                          {state === "accepted" ? "Brukt" : state === "ignored" ? "Avvist" : "Forslag"}
                        </span>
                        <button
                          type="button"
                          className="ghost-button compact-button"
                          disabled={organizationDataLocked}
                          onClick={() => {
                            const nextDraft = {
                              ...draft,
                              fieldValues: { ...draft.fieldValues, [fieldKey]: renderSuggestionValue(suggestion.value) },
                              suggestionStates: { ...draft.suggestionStates, [fieldKey]: "accepted" as const },
                            };
                            void persistDraft(nextDraft);
                          }}
                        >
                          Bruk forslag
                        </button>
                        <button
                          type="button"
                          className="ghost-button compact-button"
                          disabled={organizationDataLocked}
                          onClick={() => {
                            const nextDraft = {
                              ...draft,
                              fieldValues: { ...draft.fieldValues, [fieldKey]: "" },
                              suggestionStates: { ...draft.suggestionStates, [fieldKey]: "ignored" as const },
                            };
                            void persistDraft(nextDraft);
                          }}
                        >
                          Avvis forslag
                        </button>
                      </div>
                    ) : null}
                  </div>
                </Field>
              );
            })}
          </div>
        </section>
      </div>

      <div className="actions inline-review-actions">
        <span className={`meta review-save-feedback ${saveState === "error" ? "error-text" : ""}`}>
          {saveState === "saving"
            ? "Lagrer review..."
            : saveState === "saved"
              ? "Review lagret"
              : saveState === "error"
                ? "Kunne ikke lagre review. Prøv igjen."
                : "Lagre endringer før du går videre til neste rad."}
        </span>
        <button
          type="button"
          className="ghost-button compact-button"
          disabled={saveState === "saving"}
          onClick={onClose}
        >
          Lukk
        </button>
        <button
          type="button"
          className="primary-button compact-button"
          disabled={saveState === "saving"}
          onClick={() => void persistDraft(draft, false)}
        >
          {saveState === "saving" ? "Lagrer..." : "Lagre review"}
        </button>
      </div>

      {createOrganizationOpen ? (
        <CreateOrganizationModal
          initialDraft={buildQuickOrganizationDraft(row, draft)}
          saveState={organizationCreateState}
          error={organizationCreateError}
          fieldErrors={organizationFieldErrors}
          onClose={() => {
            if (organizationCreateState === "saving") return;
            setCreateOrganizationOpen(false);
            setOrganizationCreateState("idle");
            setOrganizationCreateError(null);
            setOrganizationFieldErrors({});
          }}
          onSave={handleCreateOrganization}
        />
      ) : null}
    </div>
  );
}

function CreateOrganizationModal(props: {
  initialDraft: OrganizationPatch;
  saveState: "idle" | "saving" | "error";
  error: string | null;
  fieldErrors: QuickOrganizationFieldErrors;
  onClose: () => void;
  onSave: (draft: OrganizationPatch) => Promise<void>;
}) {
  const { initialDraft, saveState, error, fieldErrors, onClose, onSave } = props;
  const [draft, setDraft] = useState<OrganizationPatch>(initialDraft);

  return createPortal(
    <div className="modal-backdrop" onClick={onClose}>
      <div className="detail-modal import-create-organization-modal" onClick={(event) => event.stopPropagation()}>
        <div className="modal-header">
          <p className="eyebrow small">Importreview</p>
          <h3>Opprett ny aktør</h3>
          <p className="muted">
            Lagre aktøren her, så kobles den direkte til raden du jobber med i review.
          </p>
        </div>

        <div className="modal-sections">
          <section className="modal-section-card">
            <div className="modal-form-grid review-form-grid compact-review-grid">
              <Field label="Navn" required error={fieldErrors.name}>
                <input
                  value={draft.name}
                  onChange={(event) => setDraft((current) => ({ ...current, name: event.target.value }))}
                  placeholder="Navn på aktør"
                />
              </Field>
              <Field label="Org.nr" error={fieldErrors.org_number}>
                <input
                  value={draft.org_number ?? ""}
                  onChange={(event) => setDraft((current) => ({ ...current, org_number: event.target.value }))}
                  placeholder="999 999 999"
                />
              </Field>
              <Field label="E-post" error={fieldErrors.email}>
                <input
                  value={draft.email ?? ""}
                  onChange={(event) => setDraft((current) => ({ ...current, email: event.target.value }))}
                  placeholder="post@virksomhet.no"
                />
              </Field>
              <Field label="Telefon" error={fieldErrors.phone}>
                <input
                  value={draft.phone ?? ""}
                  onChange={(event) => setDraft((current) => ({ ...current, phone: event.target.value }))}
                  placeholder="+47 99 99 99 99"
                />
              </Field>
              <Field label="Kommune / steder">
                <input
                  value={draft.municipalities}
                  onChange={(event) => setDraft((current) => ({ ...current, municipalities: event.target.value }))}
                  placeholder="Oslo, Bergen"
                />
              </Field>
              <Field label="Nettside" error={fieldErrors.website_url}>
                <input
                  value={draft.website_url ?? ""}
                  onChange={(event) => setDraft((current) => ({ ...current, website_url: event.target.value }))}
                  placeholder="https://..."
                />
              </Field>
              <Field label="Instagram" error={fieldErrors.instagram_url}>
                <input
                  value={draft.instagram_url ?? ""}
                  onChange={(event) => setDraft((current) => ({ ...current, instagram_url: event.target.value }))}
                  placeholder="https://instagram.com/..."
                />
              </Field>
              <Field label="TikTok" error={fieldErrors.tiktok_url}>
                <input
                  value={draft.tiktok_url ?? ""}
                  onChange={(event) => setDraft((current) => ({ ...current, tiktok_url: event.target.value }))}
                  placeholder="https://tiktok.com/@..."
                />
              </Field>
              <Field label="LinkedIn" error={fieldErrors.linkedin_url}>
                <input
                  value={draft.linkedin_url ?? ""}
                  onChange={(event) => setDraft((current) => ({ ...current, linkedin_url: event.target.value }))}
                  placeholder="https://linkedin.com/company/..."
                />
              </Field>
              <Field label="Facebook" error={fieldErrors.facebook_url}>
                <input
                  value={draft.facebook_url ?? ""}
                  onChange={(event) => setDraft((current) => ({ ...current, facebook_url: event.target.value }))}
                  placeholder="https://facebook.com/..."
                />
              </Field>
              <Field label="YouTube" error={fieldErrors.youtube_url}>
                <input
                  value={draft.youtube_url ?? ""}
                  onChange={(event) => setDraft((current) => ({ ...current, youtube_url: event.target.value }))}
                  placeholder="https://youtube.com/..."
                />
              </Field>
              <Field label="Beskrivelse">
                <textarea
                  rows={4}
                  value={draft.description ?? ""}
                  onChange={(event) => setDraft((current) => ({ ...current, description: event.target.value }))}
                  placeholder="Kort virksomhetsbeskrivelse"
                />
              </Field>
            </div>
          </section>
        </div>

        <div className="actions inline-review-actions modal-inline-actions">
          <span className={`meta review-save-feedback ${saveState === "error" ? "error-text" : ""}`}>
            {saveState === "saving"
              ? "Oppretter aktør..."
              : error ?? "Aktøren lagres først, og kobles deretter til denne raden."}
          </span>
          <button type="button" className="ghost-button compact-button" disabled={saveState === "saving"} onClick={onClose}>
            Avbryt
          </button>
          <button
            type="button"
            className="primary-button compact-button"
            disabled={saveState === "saving"}
            onClick={() => void onSave(draft)}
          >
            {saveState === "saving" ? "Oppretter..." : "Lagre aktør"}
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}

function ReviewRowModal(props: { children: ReactNode; onClose: () => void }) {
  return createPortal(
    <div className="modal-backdrop" onClick={props.onClose}>
      <div className="detail-modal import-review-modal" onClick={(event) => event.stopPropagation()}>
        <div className="modal-header compact">
          <p className="eyebrow small">Importreview</p>
          <h3>Rediger raskt</h3>
        </div>
        {props.children}
      </div>
    </div>,
    document.body,
  );
}

function buildQuickOrganizationDraft(row: ImportRow, draft: ReviewDraft): OrganizationPatch {
  return {
    name: getFirstText(row.raw_payload_json.organization_name) || "Ny aktør",
    org_number: getFirstText(row.raw_payload_json.organization_org_number) || "",
    email: draft.fieldValues.organization_email ?? getFirstText(row.raw_payload_json.organization_email),
    phone: draft.fieldValues.organization_phone ?? getFirstText(row.raw_payload_json.organization_phone),
    municipalities:
      draft.fieldValues.organization_municipalities ?? getFirstText(row.raw_payload_json.organization_municipalities),
    note: "",
    description: draft.fieldValues.organization_description ?? "",
    is_published: false,
    publish_phone: false,
    website_url: draft.fieldValues.organization_website_url ?? "",
    facebook_url: draft.fieldValues.organization_facebook_url ?? "",
    instagram_url: draft.fieldValues.organization_instagram_url ?? "",
    tiktok_url: draft.fieldValues.organization_tiktok_url ?? "",
    linkedin_url: draft.fieldValues.organization_linkedin_url ?? "",
    youtube_url: draft.fieldValues.organization_youtube_url ?? "",
    thumbnail_image_url: "",
    tag_ids: [],
    internal_tag_ids: [],
    category_ids: [],
    subcategory_ids: [],
  };
}

function validateQuickOrganizationDraft(draft: OrganizationPatch): QuickOrganizationFieldErrors {
  const errors: QuickOrganizationFieldErrors = {};
  const name = draft.name.trim();
  const orgNumber = (draft.org_number ?? "").trim();
  const email = (draft.email ?? "").trim();
  const phone = (draft.phone ?? "").trim();
  const websiteUrl = (draft.website_url ?? "").trim();
  const facebookUrl = (draft.facebook_url ?? "").trim();
  const instagramUrl = (draft.instagram_url ?? "").trim();
  const tiktokUrl = (draft.tiktok_url ?? "").trim();
  const linkedinUrl = (draft.linkedin_url ?? "").trim();
  const youtubeUrl = (draft.youtube_url ?? "").trim();

  if (!name) {
    errors.name = "Navn er påkrevd.";
  }
  if (orgNumber && !/^\d{9}$/.test(orgNumber.replace(/\s+/g, ""))) {
    errors.org_number = "Org.nr må være 9 sifre.";
  }
  if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    errors.email = "Ugyldig e-postadresse.";
  }
  if (phone) {
    const digits = phone.replace(/[^\d+]/g, "").replace(/\D/g, "");
    if (digits.length < 8 || digits.length > 15) {
      errors.phone = "Ugyldig telefonnummer.";
    }
  }

  [
    ["website_url", websiteUrl],
    ["facebook_url", facebookUrl],
    ["instagram_url", instagramUrl],
    ["tiktok_url", tiktokUrl],
    ["linkedin_url", linkedinUrl],
    ["youtube_url", youtubeUrl],
  ].forEach(([key, value]) => {
    if (!value) return;
    try {
      const url = new URL(value);
      if (!["http:", "https:"].includes(url.protocol)) {
        errors[key as keyof QuickOrganizationFieldErrors] = "Ugyldig URL.";
      }
    } catch {
      errors[key as keyof QuickOrganizationFieldErrors] = "Ugyldig URL.";
    }
  });

  return errors;
}

function buildDecisions(
  row: ImportRow,
  importMode: "ORGANIZATIONS_ONLY" | "PEOPLE_ONLY",
  draft: ReviewDraft,
): Array<{ decision_type: ImportDecision["decision_type"]; payload_json?: Record<string, unknown> }> {
  const decisions: Array<{ decision_type: ImportDecision["decision_type"]; payload_json?: Record<string, unknown> }> = [];
  const manualPayload = (suggestion_key: string, value: unknown) => ({
    suggestion_key,
    value,
    manual_override: true,
  });

  if (draft.skipRow) {
    return [{ decision_type: "SKIP_ROW" }];
  }

  if (draft.organizationDecision === "USE_EXISTING_ORGANIZATION" && draft.organizationId) {
    decisions.push({ decision_type: "USE_EXISTING_ORGANIZATION", payload_json: { organization_id: draft.organizationId } });
  }
  if (draft.categoryId) {
    decisions.push({ decision_type: "MAP_CATEGORY", payload_json: { category_id: draft.categoryId } });
  } else if (draft.categoryTouched) {
    decisions.push({
      decision_type: "ACCEPT_AI_SUGGESTION",
      payload_json: manualPayload("suggested_categories", []),
    });
  }
  if (draft.subcategoryId) {
    decisions.push({ decision_type: "MAP_SUBCATEGORY", payload_json: { subcategory_id: draft.subcategoryId } });
  } else if (draft.subcategoryTouched) {
    decisions.push({
      decision_type: "ACCEPT_AI_SUGGESTION",
      payload_json: manualPayload("suggested_subcategories", []),
    });
  }

  if (draft.tagsText.trim()) {
    decisions.push({
      decision_type: "ACCEPT_AI_SUGGESTION",
      payload_json: manualPayload("suggested_tags", splitCsvText(draft.tagsText)),
    });
  } else if (draft.suggestionStates.suggested_tags === "ignored") {
    decisions.push({ decision_type: "IGNORE_AI_SUGGESTION", payload_json: { suggestion_key: "suggested_tags" } });
  }

  if (importMode === "ORGANIZATIONS_ONLY") {
    if (draft.fieldValues.organization_name?.trim()) {
      decisions.push({
        decision_type: "ACCEPT_AI_SUGGESTION",
        payload_json: manualPayload("organization_name", draft.fieldValues.organization_name.trim()),
      });
    }
    if (draft.fieldValues.organization_org_number?.trim()) {
      decisions.push({
        decision_type: "ACCEPT_AI_SUGGESTION",
        payload_json: manualPayload("organization_org_number", draft.fieldValues.organization_org_number.trim()),
      });
    }
    decisions.push({
      decision_type: "ACCEPT_AI_SUGGESTION",
      payload_json: manualPayload("organization_internal_tags", splitCsvText(draft.organizationInternalTagsText)),
    });
    decisions.push({
      decision_type: "ACCEPT_AI_SUGGESTION",
      payload_json: manualPayload("organization_is_published", draft.organizationIsPublished),
    });
  }
  if (importMode === "PEOPLE_ONLY") {
    decisions.push({
      decision_type: "ACCEPT_AI_SUGGESTION",
      payload_json: manualPayload("person_internal_tags", splitCsvText(draft.personInternalTagsText)),
    });
  }

  SIMPLE_EDITABLE_SUGGESTION_FIELDS.forEach((fieldKey) => {
    if (importMode === "ORGANIZATIONS_ONLY" && !fieldKey.startsWith("organization_")) return;
    if (importMode === "PEOPLE_ONLY" && !fieldKey.startsWith("person_")) return;
    const fieldValue = draft.fieldValues[fieldKey]?.trim();
    const state = draft.suggestionStates[fieldKey] ?? "pending";
    if (fieldValue) {
      decisions.push({
        decision_type: "ACCEPT_AI_SUGGESTION",
        payload_json: manualPayload(fieldKey, fieldValue),
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

function ReviewValueCell(props: { current?: string; suggested?: string; fallback?: string; onClick?: () => void; clickable?: boolean }) {
  const displayValue = props.current || props.fallback || "—";
  const content = (
    <div className="review-value-cell">
      {isProbablyUrl(displayValue) ? (
        <a href={displayValue} target="_blank" rel="noreferrer noopener" className="review-link-chip" onClick={(event) => event.stopPropagation()}>
          {shortenDisplayText(displayValue, 42)}
        </a>
      ) : (
        <span>{displayValue}</span>
      )}
      {!props.current && props.suggested ? <span className="review-suggested-hint">Forslag: {props.suggested}</span> : null}
    </div>
  );
  if (props.clickable && props.onClick) {
    return (
      <button type="button" className="review-cell-button" onClick={props.onClick}>
        {content}
      </button>
    );
  }
  return (
    content
  );
}

function ReviewSuggestionCell(props: {
  variant: "category" | "subcategory" | "tag" | "internal-tag";
  currentValues: string[];
  suggestedValues: string[];
  onClick?: () => void;
}) {
  const values = props.currentValues.length > 0 ? props.currentValues : props.suggestedValues;
  if (values.length === 0) {
    return <span className="muted">Mangler</span>;
  }
  const content = (
    <div className="review-pill-stack">
      {values.slice(0, 3).map((value) => (
        <span key={value} className={`mini-pill ${props.currentValues.length > 0 ? props.variant : "suggested"}`}>{value}</span>
      ))}
      {values.length > 3 ? <span className="meta">+{values.length - 3}</span> : null}
    </div>
  );
  if (props.currentValues.length === 0 && props.suggestedValues.length > 0 && props.onClick) {
    return (
      <button type="button" className="review-cell-button" onClick={props.onClick}>
        {content}
      </button>
    );
  }
  return content;
}

function ReviewLinkCell(props: { values: string[]; emptyLabel: string; onClick?: () => void; clickable?: boolean }) {
  if (props.values.length === 0) {
    return <span className="muted">{props.emptyLabel}</span>;
  }
  const content = (
    <div className="review-link-stack">
      {props.values.slice(0, 3).map((value) => (
        <a
          key={value}
          className="review-link-chip"
          title={value}
          href={value}
          target="_blank"
          rel="noreferrer noopener"
          onClick={(event) => event.stopPropagation()}
        >
          {shortenDisplayText(value, 42)}
        </a>
      ))}
      {props.values.length > 3 ? <span className="meta">+{props.values.length - 3}</span> : null}
    </div>
  );
  if (props.clickable && props.onClick) {
    return (
      <button type="button" className="review-cell-button" onClick={props.onClick}>
        {content}
      </button>
    );
  }
  return content;
}

function ReviewTextCell(props: { value?: string; emptyLabel: string; onClick?: () => void; clickable?: boolean }) {
  if (!props.value) {
    return <span className="muted">{props.emptyLabel}</span>;
  }
  const content = <p className="review-copy-snippet">{shortenDisplayText(props.value, 110)}</p>;
  if (props.clickable && props.onClick) {
    return (
      <button type="button" className="review-cell-button" onClick={props.onClick}>
        {content}
      </button>
    );
  }
  return content;
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
          {props.state === "accepted" ? "Brukt" : props.state === "ignored" ? "Avvist" : "Til vurdering"}
        </span>
        <button type="button" className="ghost-button compact-button" onClick={props.onIgnore}>Avvis forslag</button>
      </div>
    </div>
  );
}

function TagTextEditor(props: {
  value: string;
  placeholder: string;
  tone?: "default" | "internal";
  disabled?: boolean;
  onChange: (value: string) => void;
}) {
  return (
    <div className="tag-editor-field">
      <input value={props.value} onChange={(e) => props.onChange(e.target.value)} placeholder={props.placeholder} disabled={props.disabled} />
      {splitCsvText(props.value).length > 0 ? (
        <div className="tag-chip-editor">
          {splitCsvText(props.value).map((tag) => (
            <button
              key={`${props.tone ?? "default"}-${tag}`}
              type="button"
              className={`tag-chip-edit ${props.tone === "internal" ? "internal-tag-chip-edit" : ""}`}
              disabled={props.disabled}
              onClick={() =>
                props.onChange(
                  splitCsvText(props.value)
                    .filter((item) => item.toLowerCase() !== tag.toLowerCase())
                    .join(", "),
                )
              }
            >
              <span>{tag}</span>
              <span aria-hidden="true">×</span>
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function SuggestionCandidates(props: {
  candidates: Array<{ id: number | string; label?: string; score?: number; reason?: string }>;
  onUse: (id: number | string) => void;
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
  const rawFields = ((row.ai_suggestions_json?.suggested_fields as Record<string, SuggestionField> | undefined) ?? {});
  const states = getExistingSuggestionStates(row);
  return Object.fromEntries(
    Object.entries(rawFields).filter(([key]) => (states[key] ?? "pending") === "pending"),
  );
}

type BrregCandidate = {
  id: string;
  label?: string;
  score?: number;
  reason?: string;
  org_number?: string;
  name?: string;
  municipality?: string;
  website_url?: string;
  email?: string;
};

function getBrregCandidates(row: ImportRow): BrregCandidate[] {
  const value = row.ai_suggestions_json?.brreg_candidates;
  return Array.isArray(value)
    ? value.filter((item): item is BrregCandidate => Boolean(item && typeof item === "object" && typeof (item as { id?: unknown }).id === "string"))
    : [];
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
  if (providerStatus === "pending_openai") {
    return { label: "Venter", variant: "tag" };
  }
  if (providerStatus === "openai") {
    return { label: "OpenAI", variant: "category" };
  }
  if (providerStatus === "openai_web_search") {
    return { label: "OpenAI + web", variant: "category" };
  }
  if (providerStatus === "openai_empty") {
    return { label: "OpenAI tom", variant: "tag" };
  }
  if (providerStatus.includes("fallback")) {
    return { label: "Fallback", variant: "subcategory" };
  }
  return { label: "Ukjent", variant: "tag" };
}

function getRowStatusLabel(row: ImportRow): string {
  const providerStatus = String((row.ai_suggestions_json?.diagnostic as Record<string, unknown> | undefined)?.provider_status || row.ai_suggestions_json?.provider || "").toLowerCase();
  if (providerStatus === "pending_openai") {
    return "AI jobber";
  }
  switch (row.row_status) {
    case "VALID":
      return "Ingen review nødvendig";
    case "REVIEW_REQUIRED":
      return "Review nødvendig";
    case "INVALID":
      return "Feil";
    case "SKIPPED":
      return "Hoppet over";
    case "COMMITTED":
      return "Commit";
    case "COMMIT_FAILED":
      return "Commit-feil";
    default:
      return row.row_status;
  }
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
  if (status === "pending_openai") {
    return {
      title: "AI venter",
      detail: "Preview er klar. OpenAI-forslag blir generert i bakgrunnen i små batcher.",
      helper: "AI pågår",
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

function getAiProgressLabel(summary: Record<string, unknown>): string {
  const status = String(summary.ai_generation_status ?? "");
  if (status === "running") return "Pågår";
  if (status === "pending") return "Venter";
  if (status === "completed") return "Ferdig";
  if (status === "failed" || status === "partially_failed") return "Trenger ny kjøring";
  return "Ikke startet";
}

function normalizeImportMode(
  value: string | undefined,
  fallback: "ORGANIZATIONS_ONLY" | "PEOPLE_ONLY",
): "ORGANIZATIONS_ONLY" | "PEOPLE_ONLY" {
  if (value === "PEOPLE_ONLY") return "PEOPLE_ONLY";
  if (value === "ORGANIZATIONS_ONLY") return "ORGANIZATIONS_ONLY";
  return fallback;
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

function isProbablyUrl(value: string): boolean {
  return /^https?:\/\//i.test(value.trim());
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

function hasAcceptedSuggestionDecision(row: ImportRow, suggestionKey: string): boolean {
  return row.decisions.some(
    (decision) => decision.decision_type === "ACCEPT_AI_SUGGESTION" && decision.payload_json.suggestion_key === suggestionKey,
  );
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

function getAcceptedArrayState(row: ImportRow, suggestionKey: string): { exists: boolean; value: string[] } {
  return {
    exists: hasAcceptedSuggestionDecision(row, suggestionKey),
    value: getAcceptedDecisionArray(row, suggestionKey),
  };
}

function getAcceptedDecisionBoolean(row: ImportRow, suggestionKey: string): boolean | null {
  const match = row.decisions.find(
    (decision) => decision.decision_type === "ACCEPT_AI_SUGGESTION" && decision.payload_json.suggestion_key === suggestionKey,
  );
  const value = match?.payload_json?.value;
  return typeof value === "boolean" ? value : null;
}

function getCurrentText(row: ImportRow, keys: string[]): string {
  for (const key of keys) {
    const accepted = getAcceptedDecisionValue(row, key);
    if (accepted) return accepted;
    const rawValue = getFirstText(row.raw_payload_json[key], getNestedSuggestedFallback(row, key));
    if (rawValue) return rawValue;
  }
  return "";
}

function getCurrentArray(row: ImportRow, keys: string[]): string[] {
  for (const key of keys) {
    const accepted = getAcceptedArrayState(row, key);
    if (accepted.exists) return accepted.value;
    const rawValue = row.raw_payload_json[key];
    if (Array.isArray(rawValue)) {
      const values = rawValue.map((item) => String(item).trim()).filter(Boolean);
      if (values.length > 0) return values;
    }
    const fromRawText = getFirstText(row.raw_payload_json[key]);
    const parsedRaw = splitCsvText(fromRawText);
    if (parsedRaw.length > 0) return parsedRaw;
    const nested = getNestedSuggestedFallbackValue(row, key);
    if (Array.isArray(nested)) {
      const values = nested.map((item) => String(item).trim()).filter(Boolean);
      if (values.length > 0) return values;
    }
    if (typeof nested === "string") {
      const parsedNested = splitCsvText(nested);
      if (parsedNested.length > 0) return parsedNested;
    }
  }
  return [];
}

function getCurrentBoolean(row: ImportRow, keys: string[]): boolean {
  for (const key of keys) {
    const accepted = getAcceptedDecisionBoolean(row, key);
    if (accepted !== null) return accepted;
    const rawValue = row.raw_payload_json[key];
    if (typeof rawValue === "boolean") return rawValue;
    if (typeof rawValue === "string") {
      const normalized = rawValue.trim().toLowerCase();
      if (["1", "true", "yes", "ja", "on"].includes(normalized)) return true;
      if (["0", "false", "no", "nei", "off"].includes(normalized)) return false;
    }
    const nested = getNestedSuggestedFallbackValue(row, key);
    if (typeof nested === "boolean") return nested;
  }
  return false;
}

function getCurrentOrganizationLabel(row: ImportRow, organizations: Organization[]): string {
  const selectedOrganizationId = getExistingDecisionId(row, "USE_EXISTING_ORGANIZATION", "organization_id");
  if (selectedOrganizationId) {
    const match = organizations.find((organization) => organization.id === selectedOrganizationId);
    if (match) return match.name;
  }
  return getFirstText(row.raw_payload_json.organization_name);
}

function getCurrentCategoryValues(
  row: ImportRow,
  importMode: "ORGANIZATIONS_ONLY" | "PEOPLE_ONLY",
  categories: Category[],
  organizations: Organization[] = [],
): string[] {
  const acceptedState = getAcceptedArrayState(row, "suggested_categories");
  if (acceptedState.exists) return acceptedState.value;
  const mappedCategoryId = getExistingDecisionId(row, "MAP_CATEGORY", "category_id");
  if (mappedCategoryId) {
    const match = categories.find((category) => category.id === mappedCategoryId);
    if (match) return [match.name];
  }
  if (importMode === "PEOPLE_ONLY") {
    const selectedOrganizationId = getExistingDecisionId(row, "USE_EXISTING_ORGANIZATION", "organization_id");
    if (selectedOrganizationId) {
      const selectedOrganization = organizations.find((organization) => organization.id === selectedOrganizationId);
      if (selectedOrganization?.categories?.length) {
        return selectedOrganization.categories.map((category) => category.name);
      }
    }
  }
  return getCurrentArray(row, importMode === "ORGANIZATIONS_ONLY" ? ["organization_categories"] : ["person_categories"]);
}

function getCurrentSubcategoryValues(
  row: ImportRow,
  importMode: "ORGANIZATIONS_ONLY" | "PEOPLE_ONLY",
  subcategories: Subcategory[],
  organizations: Organization[] = [],
): string[] {
  const acceptedState = getAcceptedArrayState(row, "suggested_subcategories");
  if (acceptedState.exists) return acceptedState.value;
  const mappedSubcategoryId = getExistingDecisionId(row, "MAP_SUBCATEGORY", "subcategory_id");
  if (mappedSubcategoryId) {
    const match = subcategories.find((subcategory) => subcategory.id === mappedSubcategoryId);
    if (match) return [match.name];
  }
  if (importMode === "PEOPLE_ONLY") {
    const selectedOrganizationId = getExistingDecisionId(row, "USE_EXISTING_ORGANIZATION", "organization_id");
    if (selectedOrganizationId) {
      const selectedOrganization = organizations.find((organization) => organization.id === selectedOrganizationId);
      if (selectedOrganization?.subcategories?.length) {
        return selectedOrganization.subcategories.map((subcategory) => subcategory.name);
      }
    }
  }
  return getCurrentArray(row, importMode === "ORGANIZATIONS_ONLY" ? ["organization_subcategories"] : ["person_subcategories"]);
}

function getResolvedText(row: ImportRow, suggestionKeys: string[]): string {
  for (const key of suggestionKeys) {
    const accepted = getAcceptedDecisionValue(row, key);
    if (accepted) return accepted;
    const rawValue = getFirstText(row.raw_payload_json[key], getNestedSuggestedFallback(row, key));
    if (rawValue) return rawValue;
  }
  return "";
}

function getResolvedArray(row: ImportRow, suggestionKey: string, rawKeys: string[]): string[] {
  const accepted = getAcceptedDecisionArray(row, suggestionKey);
  if (accepted.length > 0) return accepted;
  for (const rawKey of rawKeys) {
    const rawValue = row.raw_payload_json[rawKey];
    if (Array.isArray(rawValue)) {
      const parsedArray = rawValue.map((item) => String(item).trim()).filter(Boolean);
      if (parsedArray.length > 0) return parsedArray;
    }
    if (typeof rawValue === "string") {
      const parsedString = splitCsvText(rawValue);
      if (parsedString.length > 0) return parsedString;
    }
    const nestedValue = getNestedSuggestedFallbackValue(row, rawKey);
    if (Array.isArray(nestedValue)) {
      const parsedNested = nestedValue.map((item) => String(item).trim()).filter(Boolean);
      if (parsedNested.length > 0) return parsedNested;
    }
    const parsed = typeof nestedValue === "string" ? splitCsvText(nestedValue) : [];
    if (parsed.length > 0) return parsed;
  }
  return [];
}

function findCategoryIdByName(categories: Category[], name: string): number | "" {
  const match = categories.find((category) => category.name.toLowerCase() === name.toLowerCase());
  return match?.id ?? "";
}

function findSubcategoryIdByName(subcategories: Subcategory[], name: string): number | "" {
  const normalizedInput = normalizeSubcategoryName(name);
  const match = subcategories.find((subcategory) => normalizeSubcategoryName(subcategory.name) === normalizedInput);
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

function normalizeSubcategoryName(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) return "";
  const normalized = trimmed.toLowerCase();
  return (SUBCATEGORY_ALIASES[normalized] ?? trimmed).toLowerCase();
}

function getNestedSuggestedFallback(row: ImportRow, key: string): string {
  const nested = getNestedSuggestedFallbackValue(row, key);
  return typeof nested === "string" ? nested : "";
}

function getNestedSuggestedFallbackValue(row: ImportRow, key: string): unknown {
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
