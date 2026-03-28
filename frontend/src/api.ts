import type {
  Category,
  Organization,
  OrganizationPerson,
  Paginated,
  PersonContact,
  Person,
  Subcategory,
  Tag,
  Tenant,
} from "./types";

const API_BASE = import.meta.env.VITE_API_BASE ?? "";
export const AUTH_ERROR_EVENT = "editor:auth-error";
type AuthUser = { id: number; username: string };
export type AuthSession = { authenticated: boolean; user: AuthUser | null };
export type AuthErrorDetail = { status: number; path: string };

export class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(status: number, message: string, data: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

function isPaginated<T>(data: T[] | Paginated<T>): data is Paginated<T> {
  return !!data && typeof data === "object" && "results" in data;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const method = (init?.method ?? "GET").toUpperCase();
  const csrfToken = method === "GET" || method === "HEAD" ? null : getCsrfCookie();
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      ...(csrfToken ? { "X-CSRFToken": csrfToken } : {}),
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    const contentType = response.headers.get("content-type") ?? "";
    let data: unknown = null;
    let message = `API ${response.status}: ${response.statusText}`;

    if (contentType.includes("application/json")) {
      data = await response.json();
      message = `API ${response.status}`;
    } else {
      const text = await response.text();
      data = text;
      message = `API ${response.status}: ${text || response.statusText}`;
    }

    if (response.status === 401 || response.status === 403) {
      notifyAuthError({ status: response.status, path });
    }
    throw new ApiError(response.status, message, data);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

function notifyAuthError(detail: AuthErrorDetail) {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent<AuthErrorDetail>(AUTH_ERROR_EVENT, { detail }));
}

export function onAuthError(listener: (detail: AuthErrorDetail) => void): () => void {
  if (typeof window === "undefined") return () => undefined;
  const handler = (event: Event) => {
    const custom = event as CustomEvent<AuthErrorDetail>;
    listener(custom.detail);
  };
  window.addEventListener(AUTH_ERROR_EVENT, handler);
  return () => window.removeEventListener(AUTH_ERROR_EVENT, handler);
}

function getCsrfCookie(): string | null {
  const match = document.cookie
    .split("; ")
    .find((part) => part.startsWith("csrftoken="));
  return match ? decodeURIComponent(match.split("=")[1]) : null;
}

export async function ensureCsrf(): Promise<void> {
  await request("/api/auth/csrf/");
}

export async function getSession(): Promise<AuthSession> {
  return request<AuthSession>("/api/auth/session/");
}

export async function loginSession(username: string, password: string): Promise<AuthSession> {
  await ensureCsrf();
  return request<AuthSession>("/api/auth/login/", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export async function logoutSession(): Promise<AuthSession> {
  await ensureCsrf();
  return request<AuthSession>("/api/auth/logout/", {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function getTenants(): Promise<Tenant[]> {
  const data = await request<Tenant[] | Paginated<Tenant>>("/api/tenants/");
  return isPaginated(data) ? data.results : data;
}

export async function getOrganizations(tenantId: number): Promise<Organization[]> {
  const data = await request<Organization[] | Paginated<Organization>>(
    `/api/tenants/${tenantId}/organizations/`,
  );
  return isPaginated(data) ? data.results : data;
}

export async function getTags(tenantId: number): Promise<Tag[]> {
  const data = await request<Tag[] | Paginated<Tag>>(`/api/tenants/${tenantId}/tags/`);
  return isPaginated(data) ? data.results : data;
}

export async function getCategories(): Promise<Category[]> {
  const data = await request<Category[] | Paginated<Category>>("/api/categories/");
  return isPaginated(data) ? data.results : data;
}

export async function getSubcategories(categoryId?: number): Promise<Subcategory[]> {
  const suffix = categoryId ? `?category=${categoryId}` : "";
  const data = await request<Subcategory[] | Paginated<Subcategory>>(`/api/subcategories/${suffix}`);
  return isPaginated(data) ? data.results : data;
}

export async function getPersons(tenantId: number): Promise<Person[]> {
  const data = await request<Person[] | Paginated<Person>>(`/api/tenants/${tenantId}/persons/`);
  return isPaginated(data) ? data.results : data;
}

export async function createPerson(
  tenantId: number,
  payload: PersonPayload,
): Promise<Person> {
  return request<Person>(`/api/tenants/${tenantId}/persons/`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function patchPerson(
  tenantId: number,
  personId: number,
  payload: PersonPayload,
): Promise<Person> {
  return request<Person>(`/api/tenants/${tenantId}/persons/${personId}/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deletePerson(tenantId: number, personId: number): Promise<void> {
  await request(`/api/tenants/${tenantId}/persons/${personId}/`, {
    method: "DELETE",
  });
}

export async function getOrganizationPeople(tenantId: number): Promise<OrganizationPerson[]> {
  const data = await request<OrganizationPerson[] | Paginated<OrganizationPerson>>(
    `/api/tenants/${tenantId}/organization-people/`,
  );
  return isPaginated(data) ? data.results : data;
}

export async function getPersonContacts(
  tenantId: number,
  personId?: number,
): Promise<PersonContact[]> {
  const suffix = personId ? `?person=${personId}` : "";
  const data = await request<PersonContact[] | Paginated<PersonContact>>(
    `/api/tenants/${tenantId}/person-contacts/${suffix}`,
  );
  return isPaginated(data) ? data.results : data;
}

export type OrganizationPatch = Pick<
  Organization,
  | "name"
  | "org_number"
  | "email"
  | "phone"
  | "municipalities"
  | "note"
  | "description"
  | "is_published"
  | "publish_phone"
  | "website_url"
  | "facebook_url"
  | "instagram_url"
  | "tiktok_url"
  | "linkedin_url"
  | "youtube_url"
> & {
  tag_ids: number[];
  subcategory_ids: number[];
};

export type PersonPayload = {
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
  tag_ids: number[];
  subcategory_ids: number[];
};

export async function patchOrganization(
  tenantId: number,
  organizationId: number,
  payload: OrganizationPatch,
): Promise<Organization> {
  return request<Organization>(`/api/tenants/${tenantId}/organizations/${organizationId}/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function refreshOrganizationPreview(
  tenantId: number,
  organizationId: number,
): Promise<Organization> {
  return request<Organization>(`/api/tenants/${tenantId}/organizations/${organizationId}/refresh-preview/`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function createOrganization(
  tenantId: number,
  payload: OrganizationPatch,
): Promise<Organization> {
  return request<Organization>(`/api/tenants/${tenantId}/organizations/`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export type OrganizationPersonCreate = Pick<
  OrganizationPerson,
  "organization" | "person" | "status" | "publish_person"
>;

export async function createOrganizationPerson(
  tenantId: number,
  payload: OrganizationPersonCreate,
): Promise<OrganizationPerson> {
  return request<OrganizationPerson>(`/api/tenants/${tenantId}/organization-people/`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export type OrganizationPersonPatch = Partial<
  Pick<OrganizationPerson, "status" | "publish_person">
>;

export async function patchOrganizationPerson(
  tenantId: number,
  linkId: number,
  payload: OrganizationPersonPatch,
): Promise<OrganizationPerson> {
  return request<OrganizationPerson>(`/api/tenants/${tenantId}/organization-people/${linkId}/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deleteOrganizationPerson(tenantId: number, linkId: number): Promise<void> {
  await request(`/api/tenants/${tenantId}/organization-people/${linkId}/`, {
    method: "DELETE",
  });
}

export type PersonContactPayload = {
  person: number;
  type: "EMAIL" | "PHONE";
  value: string;
  is_primary: boolean;
  is_public: boolean;
};

export async function createPersonContact(
  tenantId: number,
  payload: PersonContactPayload,
): Promise<PersonContact> {
  return request<PersonContact>(`/api/tenants/${tenantId}/person-contacts/`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function patchPersonContact(
  tenantId: number,
  contactId: number,
  payload: Partial<Omit<PersonContactPayload, "person">>,
): Promise<PersonContact> {
  return request<PersonContact>(`/api/tenants/${tenantId}/person-contacts/${contactId}/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deletePersonContact(
  tenantId: number,
  contactId: number,
): Promise<void> {
  await request(`/api/tenants/${tenantId}/person-contacts/${contactId}/`, {
    method: "DELETE",
  });
}
