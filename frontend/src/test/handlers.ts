import { http, HttpResponse } from "msw";
import type {
  Category,
  Organization,
  OrganizationPerson,
  Person,
  PersonContact,
  Subcategory,
  Tag,
  Tenant,
} from "../types";

type SessionState = {
  authenticated: boolean;
  user: { id: number; username: string } | null;
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
        og_last_fetched_at: null,
        primary_link: "https://example.com",
        primary_link_field: "website_url",
        preview_image_url: "https://example.com/favicon.ico",
        tags: [],
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
        user: { id: 1, username: "editor" },
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
      og_last_fetched_at: "2026-01-02T00:00:00Z",
    };
    organizationsByTenantState[tenantId] = list.map((item) => (item.id === organizationId ? updated : item));
    return HttpResponse.json(updated);
  }),

  http.get("/api/tenants/:tenantId/tags/", ({ params }) => {
    const tenantId = Number(params.tenantId);
    return HttpResponse.json(tagsByTenantState[tenantId] ?? []);
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
];
