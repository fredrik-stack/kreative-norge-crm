import { http, HttpResponse } from "msw";
import type {
  Category,
  ExportJob,
  ImportDecision,
  ImportJob,
  ImportRow,
  Organization,
  OrganizationPerson,
  Person,
  PersonContact,
  Subcategory,
  Tag,
  Tenant,
  TenantMembership,
} from "../types";

type SessionState = {
  authenticated: boolean;
  user: { id: number; username: string; is_superuser: boolean; memberships: TenantMembership[] } | null;
};

let sessionState: SessionState = { authenticated: false, user: null };
let tenantsState: Tenant[] = [];
let organizationsByTenantState: Record<number, Organization[]> = {};
let personsByTenantState: Record<number, Person[]> = {};
let linksByTenantState: Record<number, OrganizationPerson[]> = {};
let contactsByTenantState: Record<number, PersonContact[]> = {};
let tagsByTenantState: Record<number, Tag[]> = {};
let categoriesState: Category[] = [];
let subcategoriesState: Subcategory[] = [];
let importJobsByTenantState: Record<number, ImportJob[]> = {};
let importRowsByJobState: Record<number, ImportRow[]> = {};
let exportJobsByTenantState: Record<number, ExportJob[]> = {};

export function resetMockSession() {
  sessionState = { authenticated: false, user: null };
}

export function resetMockEditorData() {
  categoriesState = [
    { id: 100, name: "Musikk", slug: "musikk", created_at: "2026-01-01T00:00:00Z" },
    { id: 101, name: "Visuell Kunst", slug: "visuell-kunst", created_at: "2026-01-01T00:00:00Z" },
  ];
  subcategoriesState = [
    {
      id: 200,
      name: "Jazz",
      slug: "jazz",
      created_at: "2026-01-01T00:00:00Z",
      category: categoriesState[0],
    },
    {
      id: 201,
      name: "Impro",
      slug: "impro",
      created_at: "2026-01-01T00:00:00Z",
      category: categoriesState[0],
    },
  ];
  tenantsState = [
    {
      id: 1,
      name: "Demo Tenant",
      slug: "demo",
      created_at: "2026-01-01T00:00:00Z",
      current_user_role: "redigerer",
    },
  ];
  organizationsByTenantState = {
    1: [
      {
        id: 10,
        tenant: 1,
        name: "Kreativ Demo AS",
        org_number: "123456789",
        email: "post@demo.no",
        phone: "+4712345678",
        municipalities: "Oslo",
        note: null,
        description: "Demoaktør brukt i testoppsettet.",
        is_published: true,
        publish_phone: true,
        website_url: "https://example.com",
        facebook_url: null,
        instagram_url: null,
        tiktok_url: null,
        linkedin_url: null,
        youtube_url: null,
        og_title: "Kreativ Demo AS",
        og_description: null,
        og_image_url: null,
        thumbnail_image_url: null,
        auto_thumbnail_url: null,
        og_last_fetched_at: null,
        primary_link: "https://example.com",
        primary_link_field: "website_url",
        preview_image_url: "https://example.com/favicon.ico",
        tags: [],
        categories: [],
        subcategories: [],
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
        active_people: [],
      },
    ],
  };
  personsByTenantState = {
    1: [
      {
        id: 20,
        tenant: 1,
        full_name: "Ada Editor",
        title: "Manager",
        email: "ada@example.com",
        phone: "+4799999999",
        municipality: "Oslo",
        note: null,
        website_url: null,
        instagram_url: null,
        tiktok_url: null,
        linkedin_url: null,
        facebook_url: null,
        youtube_url: null,
        tags: [],
        categories: [],
        subcategories: [],
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
        contacts: [],
      },
    ],
  };
  linksByTenantState = { 1: [] };
  contactsByTenantState = { 1: [] };
  tagsByTenantState = {
    1: [
      { id: 300, tenant: 1, name: "Etablert", slug: "etablert", created_at: "2026-01-01T00:00:00Z" },
      { id: 301, tenant: 1, name: "Turné", slug: "turne", created_at: "2026-01-01T00:00:00Z" },
    ],
  };
  importJobsByTenantState = { 1: [] };
  importRowsByJobState = {};
  exportJobsByTenantState = { 1: [] };
}

export const handlers = [
  http.get("/api/auth/session/", () => {
    return HttpResponse.json(sessionState);
  }),

  http.get("/api/auth/csrf/", () => {
    return HttpResponse.json({ csrfToken: "test-csrf-token" });
  }),

  http.post("/api/auth/login/", async ({ request }) => {
    const body = (await request.json()) as { username?: string; password?: string };
    if (body.username === "editor" && body.password === "secret123") {
      sessionState = {
        authenticated: true,
        user: {
          id: 1,
          username: "editor",
          is_superuser: false,
          memberships: [
            {
              id: 1,
              tenant: 1,
              user: 1,
              role: "redigerer",
              created_at: "2026-01-01T00:00:00Z",
              updated_at: "2026-01-01T00:00:00Z",
            },
          ],
        },
      };
      return HttpResponse.json(sessionState);
    }
    return HttpResponse.json(
      { non_field_errors: ["Ugyldig brukernavn eller passord."] },
      { status: 400 },
    );
  }),

  http.post("/api/auth/logout/", () => {
    sessionState = { authenticated: false, user: null };
    return HttpResponse.json(sessionState);
  }),

  http.get("/api/tenants/", () => {
    if (!sessionState.authenticated) {
      return HttpResponse.json({ detail: "Authentication credentials were not provided." }, { status: 403 });
    }
    return HttpResponse.json(tenantsState);
  }),

  http.get("/api/tenants/:tenantId/organizations/", ({ params }) => {
    const tenantId = Number(params.tenantId);
    return HttpResponse.json(organizationsByTenantState[tenantId] ?? []);
  }),

  http.post("/api/tenants/:tenantId/organizations/:organizationId/refresh-preview/", ({ params }) => {
    const tenantId = Number(params.tenantId);
    const organizationId = Number(params.organizationId);
    const list = organizationsByTenantState[tenantId] ?? [];
    const current = list.find((item) => item.id === organizationId);
    if (!current) {
      return HttpResponse.json({ detail: "Not found." }, { status: 404 });
    }
    const updated = {
      ...current,
      og_title: `${current.name} preview`,
      og_description: "Open Graph metadata hentet fra primærlenke.",
      og_image_url: current.preview_image_url ?? current.og_image_url,
      thumbnail_image_url: current.thumbnail_image_url,
      auto_thumbnail_url: current.auto_thumbnail_url ?? current.preview_image_url ?? current.og_image_url,
      og_last_fetched_at: "2026-01-02T00:00:00Z",
    };
    organizationsByTenantState[tenantId] = list.map((item) => (item.id === organizationId ? updated : item));
    return HttpResponse.json(updated);
  }),

  http.get("/api/tenants/:tenantId/tags/", ({ params }) => {
    const tenantId = Number(params.tenantId);
    return HttpResponse.json(tagsByTenantState[tenantId] ?? []);
  }),

  http.post("/api/tenants/:tenantId/tags/", async ({ params, request }) => {
    const tenantId = Number(params.tenantId);
    const body = (await request.json()) as { name?: string };
    const current = tagsByTenantState[tenantId] ?? [];
    const normalized = (body.name ?? "").trim();
    const existing = current.find((tag) => tag.name.toLowerCase() === normalized.toLowerCase());
    if (existing) {
      return HttpResponse.json(existing);
    }
    const created = {
      id: Math.max(0, ...current.map((tag) => tag.id)) + 1,
      tenant: tenantId,
      name: normalized,
      slug: normalized.toLowerCase().replace(/\s+/g, "-"),
      created_at: "2026-01-01T00:00:00Z",
    };
    tagsByTenantState[tenantId] = [...current, created];
    return HttpResponse.json(created, { status: 201 });
  }),

  http.get("/api/categories/", () => {
    return HttpResponse.json(categoriesState);
  }),

  http.get("/api/subcategories/", ({ request }) => {
    const url = new URL(request.url);
    const category = url.searchParams.get("category");
    if (!category) return HttpResponse.json(subcategoriesState);
    return HttpResponse.json(subcategoriesState.filter((item) => item.category.id === Number(category)));
  }),

  http.get("/api/tenants/:tenantId/persons/", ({ params }) => {
    const tenantId = Number(params.tenantId);
    return HttpResponse.json(personsByTenantState[tenantId] ?? []);
  }),

  http.get("/api/tenants/:tenantId/organization-people/", ({ params }) => {
    const tenantId = Number(params.tenantId);
    return HttpResponse.json(linksByTenantState[tenantId] ?? []);
  }),

  http.get("/api/tenants/:tenantId/person-contacts/", ({ params, request }) => {
    const tenantId = Number(params.tenantId);
    const url = new URL(request.url);
    const personId = url.searchParams.get("person");
    const contacts = contactsByTenantState[tenantId] ?? [];
    if (!personId) return HttpResponse.json(contacts);
    return HttpResponse.json(contacts.filter((c) => String(c.person) === personId));
  }),

  http.get("/api/tenants/:tenantId/import-jobs/", ({ params }) => {
    const tenantId = Number(params.tenantId);
    return HttpResponse.json(importJobsByTenantState[tenantId] ?? []);
  }),

  http.post("/api/tenants/:tenantId/import-jobs/", async ({ params, request }) => {
    const tenantId = Number(params.tenantId);
    const body = (await request.json()) as Pick<ImportJob, "source_type" | "import_mode">;
    const current = importJobsByTenantState[tenantId] ?? [];
    const created: ImportJob = {
      id: Math.max(0, ...current.map((job) => job.id)) + 1,
      tenant: tenantId,
      created_by: 1,
      source_type: body.source_type,
      import_mode: body.import_mode,
      status: "DRAFT",
      filename: "",
      file: null,
      summary_json: {},
      config_json: {},
      preview_report_file: null,
      error_report_file: null,
      committed_at: null,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
      rows_count: 0,
    };
    importJobsByTenantState[tenantId] = [created, ...current];
    importRowsByJobState[created.id] = [];
    return HttpResponse.json(created, { status: 201 });
  }),

  http.get("/api/tenants/:tenantId/import-jobs/:jobId/", ({ params }) => {
    const tenantId = Number(params.tenantId);
    const jobId = Number(params.jobId);
    const job = (importJobsByTenantState[tenantId] ?? []).find((item) => item.id === jobId);
    if (!job) return HttpResponse.json({ detail: "Not found." }, { status: 404 });
    return HttpResponse.json({ ...job, rows_count: (importRowsByJobState[jobId] ?? []).length });
  }),

  http.post("/api/tenants/:tenantId/import-jobs/:jobId/upload/", async ({ params, request }) => {
    const tenantId = Number(params.tenantId);
    const jobId = Number(params.jobId);
    const jobs = importJobsByTenantState[tenantId] ?? [];
    const index = jobs.findIndex((item) => item.id === jobId);
    if (index < 0) return HttpResponse.json({ detail: "Not found." }, { status: 404 });
    const formData = await request.formData();
    const file = formData.get("file");
    const next = {
      ...jobs[index],
      filename: file instanceof File ? file.name : "import.csv",
      file: "/media/import.csv",
      status: "UPLOADED" as const,
    };
    importJobsByTenantState[tenantId] = jobs.map((job, jobIndex) => (jobIndex === index ? next : job));
    return HttpResponse.json(next);
  }),

  http.post("/api/tenants/:tenantId/import-jobs/:jobId/preview/", ({ params }) => {
    const tenantId = Number(params.tenantId);
    const jobId = Number(params.jobId);
    const jobs = importJobsByTenantState[tenantId] ?? [];
    const index = jobs.findIndex((item) => item.id === jobId);
    if (index < 0) return HttpResponse.json({ detail: "Not found." }, { status: 404 });
    const job = jobs[index];
    const actorRow: ImportRow = {
      id: 1,
      import_job: jobId,
      row_number: 1,
      raw_payload_json: {
        organization_name: "Kreativ Demo AS",
        organization_org_number: "123456789",
        organization_municipalities: "Oslo",
        organization_categories: "",
        organization_subcategories: "",
        organization_tags: "",
        organization_website_url: "",
        person_full_name: job.import_mode === "ORGANIZATIONS_ONLY" ? "" : "Ada Editor",
      },
      normalized_payload_json: {
        organization: { name: "Kreativ Demo AS", tags: ["Etablert"], categories: [], subcategories: [] },
        person: { full_name: job.import_mode === "ORGANIZATIONS_ONLY" ? "" : "Ada Editor", tags: ["Turné"] },
      },
      detected_entities_json: { has_organization: true, has_person: job.import_mode !== "ORGANIZATIONS_ONLY" },
      match_result_json: {
        organization: { status: "NEW", rule: null, exact_id: null, candidates: [] },
        person: { status: "NEW", rule: null, exact_id: null, candidates: [] },
      },
      ai_suggestions_json: {
        organization_match_candidates: [{ id: 10, label: "Kreativ Demo AS", score: 0.92, reason: "name+domain" }],
        person_match_candidates: job.import_mode === "ORGANIZATIONS_ONLY" ? [] : [{ id: 20, label: "Ada Editor", score: 0.77, reason: "name+municipality" }],
        suggested_fields: {
          organization_email: {
            value: "post@kreativdemo.no",
            confidence: 0.82,
            source: "website_contact_signal",
            requires_review: true,
          },
          organization_phone: {
            value: "+47 99 99 99 99",
            confidence: 0.76,
            source: "website_contact_signal",
            requires_review: true,
          },
          suggested_tags: {
            value: ["Turné", "Etablert"],
            confidence: 0.68,
            source: "heuristic_taxonomy",
            requires_review: true,
          },
        },
        provider: "pending_openai",
        diagnostic: {
          primary_provider: "pending_openai",
          provider_status: "pending_openai",
          fallback_reason: "awaiting_openai",
          openai_attempted: false,
          openai_error: null,
          useful_suggestion_count: 1,
        },
      },
      validation_errors_json: [],
      warnings_json: [],
      row_status: "VALID",
      proposed_action: "CREATE",
      decision_json: {},
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
      decisions: [],
    };
    const rows = [actorRow];
    importRowsByJobState[jobId] = rows;
    const updated = {
      ...jobs[index],
      status: "PREVIEW_READY" as const,
      summary_json: {
        rows_total: rows.length,
        valid_rows: rows.length,
        invalid_rows: 0,
        review_required_rows: 0,
        organizations_create: 1,
        organizations_update: 0,
        persons_create: 1,
        persons_update: 0,
        links_create: 1,
        tags_new: 2,
        rows_using_openai: 0,
        rows_using_fallback: 0,
        rows_ai_pending: 1,
        rows_ai_completed: 0,
        rows_ai_failed: 0,
        ai_generation_status: "pending",
        rows_with_no_useful_ai_suggestions: 0,
        rows_with_ai_errors: 0,
      },
    };
    importJobsByTenantState[tenantId] = jobs.map((job, jobIndex) => (jobIndex === index ? updated : job));
    return HttpResponse.json(updated);
  }),

  http.post("/api/tenants/:tenantId/import-jobs/:jobId/generate-ai/", ({ params }) => {
    const tenantId = Number(params.tenantId);
    const jobId = Number(params.jobId);
    const jobs = importJobsByTenantState[tenantId] ?? [];
    const index = jobs.findIndex((item) => item.id === jobId);
    if (index < 0) return HttpResponse.json({ detail: "Not found." }, { status: 404 });
    const rows = importRowsByJobState[jobId] ?? [];
    importRowsByJobState[jobId] = rows.map((row) => {
      const aiSuggestions = (row.ai_suggestions_json ?? {}) as Record<string, unknown>;
      const suggestedFields = ((aiSuggestions.suggested_fields as Record<string, unknown> | undefined) ?? {});
      return {
        ...row,
        ai_suggestions_json: {
          ...aiSuggestions,
          suggested_fields: {
            ...suggestedFields,
          organization_website_url: {
            value: "https://example.no",
            confidence: 0.81,
            source: "ai_enrichment",
            requires_review: true,
          },
          organization_instagram_url: {
            value: "https://instagram.com/kreativdemo",
            confidence: 0.7,
            source: "ai_enrichment",
            requires_review: true,
          },
          organization_municipalities: {
            value: "Oslo",
            confidence: 0.71,
            source: "ai_enrichment",
            requires_review: true,
          },
          organization_description: {
            value: "Produsent og arrangør innen musikk.",
            confidence: 0.72,
            source: "ai_enrichment",
            requires_review: true,
          },
          suggested_categories: {
            value: ["Musikk"],
            confidence: 0.88,
            source: "ai_enrichment",
            requires_review: true,
          },
          suggested_subcategories: {
            value: ["Jazz"],
            confidence: 0.74,
            source: "ai_enrichment",
            requires_review: true,
          },
        },
        provider: "openai",
        diagnostic: {
          primary_provider: "openai",
          provider_status: "openai",
          fallback_reason: null,
          openai_attempted: true,
            openai_error: null,
            useful_suggestion_count: 6,
          },
        },
      };
    });
    const updated = {
      ...jobs[index],
      summary_json: {
        ...(jobs[index].summary_json ?? {}),
        rows_using_openai: 1,
        rows_using_fallback: 0,
        rows_ai_pending: 0,
        rows_ai_completed: 1,
        rows_ai_failed: 0,
        ai_generation_status: "completed",
        rows_with_no_useful_ai_suggestions: 0,
        rows_with_ai_errors: 0,
      },
    };
    importJobsByTenantState[tenantId] = jobs.map((job, jobIndex) => (jobIndex === index ? updated : job));
    return HttpResponse.json(updated);
  }),

  http.get("/api/tenants/:tenantId/import-jobs/:jobId/rows/", ({ params, request }) => {
    const jobId = Number(params.jobId);
    const rows = importRowsByJobState[jobId] ?? [];
    const url = new URL(request.url);
    const status = url.searchParams.get("status");
    const action = url.searchParams.get("action");
    const search = url.searchParams.get("search")?.toLowerCase() ?? "";
    let filtered = rows;
    if (status) filtered = filtered.filter((row) => row.row_status === status);
    if (action) filtered = filtered.filter((row) => row.proposed_action === action);
    if (search) {
      filtered = filtered.filter(
        (row) =>
          JSON.stringify(row.raw_payload_json).toLowerCase().includes(search) ||
          JSON.stringify(row.normalized_payload_json).toLowerCase().includes(search),
      );
    }
    return HttpResponse.json({ count: filtered.length, next: null, previous: null, results: filtered });
  }),

  http.post("/api/tenants/:tenantId/import-jobs/:jobId/decisions/", async ({ params, request }) => {
    const jobId = Number(params.jobId);
    const body = (await request.json()) as { rows: Array<{ row_id: number; decisions: ImportDecision[] }> };
    const rows = importRowsByJobState[jobId] ?? [];
    const results = body.rows.map((item) => {
      const row = rows.find((entry) => entry.id === item.row_id);
      if (!row) return { row_id: item.row_id, decisions: [] };
      row.decisions = item.decisions.map((decision, index) => ({
        id: index + 1,
        import_row: row.id,
        decided_by: 1,
        decision_type: decision.decision_type,
        payload_json: decision.payload_json ?? {},
        created_at: "2026-01-01T00:00:00Z",
      }));
      row.row_status = item.decisions.some((decision) => decision.decision_type === "SKIP_ROW") ? "SKIPPED" : "VALID";
      return { row_id: row.id, decisions: row.decisions };
    });
    return HttpResponse.json({ results });
  }),

  http.post("/api/tenants/:tenantId/import-jobs/:jobId/commit/", async ({ params, request }) => {
    const tenantId = Number(params.tenantId);
    const jobId = Number(params.jobId);
    const body = (await request.json()) as { skip_unresolved?: boolean };
    const jobs = importJobsByTenantState[tenantId] ?? [];
    const index = jobs.findIndex((item) => item.id === jobId);
    if (index < 0) return HttpResponse.json({ detail: "Not found." }, { status: 404 });
    if (jobs[index].summary_json?.review_required_rows && !body.skip_unresolved) {
      return HttpResponse.json({ detail: "Import job has unresolved review rows." }, { status: 400 });
    }
    const updated = {
      ...jobs[index],
      status: "COMPLETED" as const,
      summary_json: {
        ...(jobs[index].summary_json ?? {}),
        organizations_created: 1,
        organizations_updated: 0,
        persons_created: 1,
        persons_updated: 0,
        person_contacts_created: 2,
        links_created: 1,
        rows_skipped: 0,
        rows_failed: 0,
      },
      error_report_file: "/api/tenants/1/import-jobs/1/error-report/",
    };
    importJobsByTenantState[tenantId] = jobs.map((job, jobIndex) => (jobIndex === index ? updated : job));
    return HttpResponse.json(updated);
  }),

  http.get("/api/tenants/:tenantId/import-jobs/:jobId/error-report/", () => {
    return new HttpResponse("row_number,row_status\n1,VALID\n", {
      status: 200,
      headers: {
        "Content-Type": "text/csv",
        "Content-Disposition": 'attachment; filename="error-report.csv"',
      },
    });
  }),

  http.get("/api/tenants/:tenantId/export-jobs/", ({ params }) => {
    const tenantId = Number(params.tenantId);
    return HttpResponse.json(exportJobsByTenantState[tenantId] ?? []);
  }),

  http.post("/api/tenants/:tenantId/export-jobs/", async ({ params, request }) => {
    const tenantId = Number(params.tenantId);
    const body = (await request.json()) as Pick<ExportJob, "export_type" | "format" | "filters_json" | "selected_fields_json">;
    const current = exportJobsByTenantState[tenantId] ?? [];
    const created: ExportJob = {
      id: Math.max(0, ...current.map((job) => job.id)) + 1,
      tenant: tenantId,
      created_by: 1,
      export_type: body.export_type,
      format: body.format,
      filters_json: body.filters_json ?? {},
      selected_fields_json: body.selected_fields_json ?? [],
      status: "PENDING",
      file: null,
      summary_json: {},
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    };
    exportJobsByTenantState[tenantId] = [created, ...current];
    return HttpResponse.json(created, { status: 201 });
  }),

  http.get("/api/tenants/:tenantId/export-jobs/:jobId/", ({ params }) => {
    const tenantId = Number(params.tenantId);
    const jobId = Number(params.jobId);
    const job = (exportJobsByTenantState[tenantId] ?? []).find((item) => item.id === jobId);
    if (!job) return HttpResponse.json({ detail: "Not found." }, { status: 404 });
    return HttpResponse.json(job);
  }),
];
