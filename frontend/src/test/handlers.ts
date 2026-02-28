import { http, HttpResponse } from "msw";
import type { Organization, OrganizationPerson, Person, PersonContact, Tenant } from "../types";

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

export function resetMockSession() {
  sessionState = { authenticated: false, user: null };
}

export function resetMockEditorData() {
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
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
        contacts: [],
      },
    ],
  };
  linksByTenantState = { 1: [] };
  contactsByTenantState = { 1: [] };
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
