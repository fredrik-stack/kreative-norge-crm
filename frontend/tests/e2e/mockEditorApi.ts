import type { Page } from "@playwright/test";

type SessionPayload =
  | { authenticated: false; user: null }
  | { authenticated: true; user: { id: number; username: string } };

type Tenant = { id: number; name: string; slug: string; created_at: string };
type Tag = { id: number; tenant: number; name: string; slug: string; created_at: string };
type Category = { id: number; name: string; slug: string; created_at: string };
type Subcategory = {
  id: number;
  name: string;
  slug: string;
  created_at: string;
  category: Category;
};
type Organization = {
  id: number;
  tenant: number;
  name: string;
  org_number: string | null;
  email: string | null;
  phone: string | null;
  municipalities: string;
  note: string | null;
  description: string | null;
  is_published: boolean;
  publish_phone: boolean;
   website_url: string | null;
   facebook_url: string | null;
   instagram_url: string | null;
   tiktok_url: string | null;
   linkedin_url: string | null;
   youtube_url: string | null;
   og_title: string | null;
   og_description: string | null;
   og_image_url: string | null;
   og_last_fetched_at: string | null;
   primary_link: string | null;
   primary_link_field: string | null;
   preview_image_url: string | null;
   tags: Tag[];
   subcategories: Subcategory[];
  created_at: string;
  updated_at: string;
  active_people: unknown[];
};
type Person = {
  id: number;
  tenant: number;
  full_name: string;
  email: string | null;
  phone: string | null;
  municipality: string;
  note: string | null;
  website_url: string | null;
  instagram_url: string | null;
  tiktok_url: string | null;
  linkedin_url: string | null;
  facebook_url: string | null;
  youtube_url: string | null;
  tags: Tag[];
  subcategories: Subcategory[];
  created_at: string;
  updated_at: string;
  contacts: PersonContact[];
};
type OrganizationPerson = {
  id: number;
  tenant: number;
  organization: number;
  person: number;
  status: "ACTIVE" | "INACTIVE";
  publish_person: boolean;
  created_at: string;
};
type PersonContact = {
  id: number;
  tenant: number;
  person: number;
  type: "EMAIL" | "PHONE";
  value: string;
  is_primary: boolean;
  is_public: boolean;
  created_at: string;
};

type MockState = {
  authenticated: boolean;
  tenants: Tenant[];
  organizations: Organization[];
  persons: Person[];
  tags: Tag[];
  categories: Category[];
  subcategories: Subcategory[];
  organizationPeople: OrganizationPerson[];
  personContacts: PersonContact[];
};

export async function setupMockEditorApi(page: Page, seed?: Partial<MockState>) {
  const now = "2026-01-01T00:00:00Z";
  const state: MockState = {
    authenticated: false,
    tenants: [{ id: 1, name: "Demo Tenant", slug: "demo", created_at: now }],
    categories: [{ id: 100, name: "Musikk", slug: "musikk", created_at: now }],
    subcategories: [
      {
        id: 200,
        name: "Jazz",
        slug: "jazz",
        created_at: now,
        category: { id: 100, name: "Musikk", slug: "musikk", created_at: now },
      },
    ],
    tags: [{ id: 300, tenant: 1, name: "Etablert", slug: "etablert", created_at: now }],
    organizations: [
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
        subcategories: [],
        created_at: now,
        updated_at: now,
        active_people: [],
      },
    ],
    persons: [
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
        created_at: now,
        updated_at: now,
        contacts: [],
      },
    ],
    organizationPeople: [],
    personContacts: [],
    ...seed,
  };

  await page.route("**/api/auth/session/", async (route) => {
    const session: SessionPayload = state.authenticated
      ? { authenticated: true, user: { id: 1, username: "editor" } }
      : { authenticated: false, user: null };
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(session) });
  });

  await page.route("**/api/auth/csrf/", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ csrfToken: "pw-csrf" }),
      headers: { "set-cookie": "csrftoken=pw-csrf; Path=/" },
    });
  });

  await page.route("**/api/auth/login/", async (route) => {
    const body = route.request().postDataJSON() as { username?: string; password?: string };
    if (body.username === "editor" && body.password === "secret123") {
      state.authenticated = true;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ authenticated: true, user: { id: 1, username: "editor" } }),
      });
      return;
    }
    await route.fulfill({
      status: 400,
      contentType: "application/json",
      body: JSON.stringify({ non_field_errors: ["Ugyldig brukernavn eller passord."] }),
    });
  });

  await page.route("**/api/auth/logout/", async (route) => {
    state.authenticated = false;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ authenticated: false, user: null }),
    });
  });

  await page.route("**/api/tenants/", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(state.tenants) });
  });

  await page.route("**/api/categories/", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(state.categories) });
  });

  await page.route("**/api/subcategories/", async (route) => {
    const url = new URL(route.request().url());
    const categoryId = url.searchParams.get("category");
    const payload = categoryId
      ? state.subcategories.filter((item) => item.category.id === Number(categoryId))
      : state.subcategories;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(payload) });
  });

  await page.route("**/api/tenants/1/tags/", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(state.tags) });
  });

  await page.route("**/api/tenants/1/organizations/", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(state.organizations),
      });
      return;
    }
    if (route.request().method() === "POST") {
      const payload = route.request().postDataJSON() as Partial<Organization>;
      const nextId = Math.max(0, ...state.organizations.map((o) => o.id)) + 1;
      const created: Organization = {
        id: nextId,
        tenant: 1,
        name: payload.name ?? "",
        org_number: payload.org_number ?? null,
        email: payload.email ?? null,
        phone: payload.phone ?? null,
        municipalities: payload.municipalities ?? "",
        note: payload.note ?? null,
        description: payload.description ?? null,
        is_published: Boolean(payload.is_published),
        publish_phone: Boolean(payload.publish_phone),
        website_url: payload.website_url ?? null,
        facebook_url: payload.facebook_url ?? null,
        instagram_url: payload.instagram_url ?? null,
        tiktok_url: payload.tiktok_url ?? null,
        linkedin_url: payload.linkedin_url ?? null,
        youtube_url: payload.youtube_url ?? null,
        og_title: null,
        og_description: null,
        og_image_url: null,
        thumbnail_image_url: payload.thumbnail_image_url ?? null,
        auto_thumbnail_url: null,
        og_last_fetched_at: null,
        primary_link: payload.website_url ?? payload.instagram_url ?? payload.tiktok_url ?? payload.linkedin_url ?? payload.facebook_url ?? payload.youtube_url ?? null,
        primary_link_field:
          payload.website_url ? "website_url"
          : payload.instagram_url ? "instagram_url"
          : payload.tiktok_url ? "tiktok_url"
          : payload.linkedin_url ? "linkedin_url"
          : payload.facebook_url ? "facebook_url"
          : payload.youtube_url ? "youtube_url"
          : null,
        preview_image_url: null,
        tags: state.tags.filter((tag) => (payload as { tag_ids?: number[] }).tag_ids?.includes(tag.id)),
        subcategories: state.subcategories.filter((item) =>
          (payload as { subcategory_ids?: number[] }).subcategory_ids?.includes(item.id),
        ),
        created_at: now,
        updated_at: now,
        active_people: [],
      };
      state.organizations.push(created);
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify(created),
      });
      return;
    }
    await route.fallback();
  });

  await page.route("**/api/tenants/1/organizations/*/", async (route) => {
    const method = route.request().method();
    const match = route.request().url().match(/\/api\/tenants\/1\/organizations\/(\d+)\/$/);
    const orgId = Number(match?.[1] ?? 0);
    const idx = state.organizations.findIndex((o) => o.id === orgId);
    if (idx < 0) {
      await route.fulfill({
        status: 404,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Not found." }),
      });
      return;
    }
    if (method === "PATCH") {
      const payload = route.request().postDataJSON() as Partial<Organization>;
      const current = state.organizations[idx];
      state.organizations[idx] = {
        ...current,
        ...payload,
        primary_link:
          payload.website_url ?? payload.instagram_url ?? payload.tiktok_url ?? payload.linkedin_url ?? payload.facebook_url ?? payload.youtube_url ?? current.primary_link,
        primary_link_field:
          payload.website_url ? "website_url"
          : payload.instagram_url ? "instagram_url"
          : payload.tiktok_url ? "tiktok_url"
          : payload.linkedin_url ? "linkedin_url"
          : payload.facebook_url ? "facebook_url"
          : payload.youtube_url ? "youtube_url"
          : current.primary_link_field,
        preview_image_url: current.preview_image_url,
        description: payload.description ?? current.description,
        tags: state.tags.filter((tag) => (payload as { tag_ids?: number[] }).tag_ids?.includes(tag.id) ?? current.tags.some((item) => item.id === tag.id)),
        subcategories: state.subcategories.filter((item) =>
          (payload as { subcategory_ids?: number[] }).subcategory_ids?.includes(item.id) ?? current.subcategories.some((existing) => existing.id === item.id),
        ),
        updated_at: now,
      };
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(state.organizations[idx]),
      });
      return;
    }
    if (method === "POST" && route.request().url().endsWith("/refresh-preview/")) {
      const current = state.organizations[idx];
      state.organizations[idx] = {
        ...current,
        og_title: `${current.name} preview`,
        og_description: "Open Graph metadata hentet fra primærlenke.",
        og_image_url: current.preview_image_url ?? current.og_image_url ?? "https://example.com/preview.jpg",
        thumbnail_image_url: current.thumbnail_image_url,
        auto_thumbnail_url: current.auto_thumbnail_url ?? current.preview_image_url ?? current.og_image_url ?? "https://example.com/preview.jpg",
        preview_image_url: current.preview_image_url ?? current.og_image_url ?? "https://example.com/preview.jpg",
        og_last_fetched_at: now,
      };
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(state.organizations[idx]),
      });
      return;
    }
    await route.fallback();
  });

  await page.route("**/api/tenants/1/persons", async (route) => {
    await route.continue();
  });
  await page.route("**/api/tenants/1/persons/", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(state.persons) });
      return;
    }
    if (route.request().method() === "POST") {
      const payload = route.request().postDataJSON() as Partial<Person>;
      const nextId = Math.max(0, ...state.persons.map((p) => p.id)) + 1;
      const created: Person = {
        id: nextId,
        tenant: 1,
        full_name: payload.full_name ?? "",
        email: payload.email ?? null,
        phone: payload.phone ?? null,
        municipality: payload.municipality ?? "",
        note: payload.note ?? null,
        website_url: payload.website_url ?? null,
        instagram_url: payload.instagram_url ?? null,
        tiktok_url: payload.tiktok_url ?? null,
        linkedin_url: payload.linkedin_url ?? null,
        facebook_url: payload.facebook_url ?? null,
        youtube_url: payload.youtube_url ?? null,
        tags: state.tags.filter((tag) => (payload as { tag_ids?: number[] }).tag_ids?.includes(tag.id)),
        subcategories: state.subcategories.filter((item) =>
          (payload as { subcategory_ids?: number[] }).subcategory_ids?.includes(item.id),
        ),
        created_at: now,
        updated_at: now,
        contacts: [],
      };
      state.persons.push(created);
      await route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify(created) });
      return;
    }
    await route.fallback();
  });

  await page.route("**/api/tenants/1/persons/*/", async (route) => {
    const method = route.request().method();
    const match = route.request().url().match(/\/api\/tenants\/1\/persons\/(\d+)\/$/);
    const personId = Number(match?.[1] ?? 0);
    const idx = state.persons.findIndex((p) => p.id === personId);
    if (idx < 0) {
      await route.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ detail: "Not found." }) });
      return;
    }
    if (method === "PATCH") {
      const payload = route.request().postDataJSON() as Partial<Person>;
      state.persons[idx] = {
        ...state.persons[idx],
        ...payload,
        tags: state.tags.filter((tag) => (payload as { tag_ids?: number[] }).tag_ids?.includes(tag.id) ?? state.persons[idx].tags.some((item) => item.id === tag.id)),
        subcategories: state.subcategories.filter((item) =>
          (payload as { subcategory_ids?: number[] }).subcategory_ids?.includes(item.id) ??
          state.persons[idx].subcategories.some((existing) => existing.id === item.id),
        ),
        updated_at: now,
      };
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(state.persons[idx]) });
      return;
    }
    if (method === "DELETE") {
      state.persons.splice(idx, 1);
      await route.fulfill({ status: 204, body: "" });
      return;
    }
    await route.fallback();
  });

  await page.route("**/api/tenants/1/organization-people/", async (route) => {
    const method = route.request().method();
    if (method === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(state.organizationPeople),
      });
      return;
    }
    if (method === "POST") {
      const payload = route.request().postDataJSON() as Partial<OrganizationPerson>;
      const nextId = Math.max(0, ...state.organizationPeople.map((link) => link.id)) + 1;
      const created: OrganizationPerson = {
        id: nextId,
        tenant: 1,
        organization: Number(payload.organization),
        person: Number(payload.person),
        status: (payload.status ?? "ACTIVE") as "ACTIVE" | "INACTIVE",
        publish_person: Boolean(payload.publish_person),
        created_at: now,
      };
      state.organizationPeople.push(created);
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify(created),
      });
      return;
    }
    await route.fallback();
  });

  await page.route("**/api/tenants/1/organization-people/*/", async (route) => {
    const method = route.request().method();
    const match = route.request().url().match(/\/api\/tenants\/1\/organization-people\/(\d+)\/$/);
    const linkId = Number(match?.[1] ?? 0);
    const idx = state.organizationPeople.findIndex((link) => link.id === linkId);
    if (idx < 0) {
      await route.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ detail: "Not found." }) });
      return;
    }
    if (method === "PATCH") {
      const payload = route.request().postDataJSON() as Partial<OrganizationPerson>;
      state.organizationPeople[idx] = { ...state.organizationPeople[idx], ...payload };
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(state.organizationPeople[idx]),
      });
      return;
    }
    if (method === "DELETE") {
      state.organizationPeople.splice(idx, 1);
      await route.fulfill({ status: 204, body: "" });
      return;
    }
    await route.fallback();
  });

  await page.route(/.*\/api\/tenants\/1\/person-contacts\/?(?:\?.*)?$/, async (route) => {
    const method = route.request().method();
    const url = new URL(route.request().url());
    if (method === "GET") {
      const personParam = url.searchParams.get("person");
      const payload = personParam
        ? state.personContacts.filter((c) => c.person === Number(personParam))
        : state.personContacts;
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(payload) });
      return;
    }
    if (method === "POST") {
      const payload = route.request().postDataJSON() as Partial<PersonContact>;
      const nextId = Math.max(0, ...state.personContacts.map((c) => c.id)) + 1;
      const created: PersonContact = {
        id: nextId,
        tenant: 1,
        person: Number(payload.person),
        type: (payload.type ?? "EMAIL") as "EMAIL" | "PHONE",
        value: String(payload.value ?? ""),
        is_primary: Boolean(payload.is_primary),
        is_public: Boolean(payload.is_public),
        created_at: now,
      };
      state.personContacts.push(created);
      const person = state.persons.find((p) => p.id === created.person);
      if (person) person.contacts = [...(person.contacts ?? []), created];
      await route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify(created) });
      return;
    }
    await route.fallback();
  });

  await page.route("**/api/tenants/1/person-contacts/*/", async (route) => {
    const method = route.request().method();
    const match = route.request().url().match(/\/api\/tenants\/1\/person-contacts\/(\d+)\/$/);
    const contactId = Number(match?.[1] ?? 0);
    const idx = state.personContacts.findIndex((c) => c.id === contactId);
    if (idx < 0) {
      await route.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ detail: "Not found." }) });
      return;
    }
    if (method === "PATCH") {
      const payload = route.request().postDataJSON() as Partial<PersonContact>;
      state.personContacts[idx] = { ...state.personContacts[idx], ...payload };
      const updated = state.personContacts[idx];
      state.persons = state.persons.map((p) =>
        p.id === updated.person
          ? {
              ...p,
              contacts: (p.contacts ?? []).map((c) => (c.id === updated.id ? updated : c)),
            }
          : p,
      );
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(updated) });
      return;
    }
    if (method === "DELETE") {
      const [removed] = state.personContacts.splice(idx, 1);
      if (removed) {
        state.persons = state.persons.map((p) =>
          p.id === removed.person
            ? { ...p, contacts: (p.contacts ?? []).filter((c) => c.id !== removed.id) }
            : p,
        );
      }
      await route.fulfill({ status: 204, body: "" });
      return;
    }
    await route.fallback();
  });

  return state;
}

export async function loginAsEditor(page: Page) {
  await page.getByLabel("Brukernavn").fill("editor");
  await page.getByLabel("Passord").fill("secret123");
  await page.getByRole("button", { name: "Logg inn" }).click();
}
