import type {
  Category,
  ExportJob,
  ImportDecision,
  ImportJob,
  ImportRow,
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
  const isFormData = typeof FormData !== "undefined" && init?.body instanceof FormData;
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: "same-origin",
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
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

export async function createTag(
  tenantId: number,
  payload: Pick<Tag, "name">,
): Promise<Tag> {
  return request<Tag>(`/api/tenants/${tenantId}/tags/`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
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
  | "thumbnail_image_url"
> & {
  tag_ids: number[];
  category_ids: number[];
  subcategory_ids: number[];
};

export type PersonPayload = {
  full_name: string;
  title: string | null;
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
  category_ids: number[];
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

export type ImportJobCreatePayload = {
  source_type: ImportJob["source_type"];
  import_mode: ImportJob["import_mode"];
};

export async function getImportJobs(tenantId: number): Promise<ImportJob[]> {
  const data = await request<ImportJob[] | Paginated<ImportJob>>(`/api/tenants/${tenantId}/import-jobs/`);
  return isPaginated(data) ? data.results : data;
}

export async function createImportJob(tenantId: number, payload: ImportJobCreatePayload): Promise<ImportJob> {
  return request<ImportJob>(`/api/tenants/${tenantId}/import-jobs/`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getImportJob(tenantId: number, importJobId: number): Promise<ImportJob> {
  return request<ImportJob>(`/api/tenants/${tenantId}/import-jobs/${importJobId}/`);
}

export async function uploadImportJobFile(tenantId: number, importJobId: number, file: File): Promise<ImportJob> {
  await ensureCsrf();
  const form = new FormData();
  form.append("file", file);
  return request<ImportJob>(`/api/tenants/${tenantId}/import-jobs/${importJobId}/upload/`, {
    method: "POST",
    body: form,
  });
}

export async function previewImportJob(tenantId: number, importJobId: number): Promise<ImportJob> {
  return request<ImportJob>(`/api/tenants/${tenantId}/import-jobs/${importJobId}/preview/`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export type ImportRowsQuery = {
  status?: string;
  action?: string;
  search?: string;
  page?: number;
};

export async function getImportRows(
  tenantId: number,
  importJobId: number,
  query: ImportRowsQuery = {},
): Promise<Paginated<ImportRow>> {
  const params = new URLSearchParams();
  if (query.status) params.set("status", query.status);
  if (query.action) params.set("action", query.action);
  if (query.search) params.set("search", query.search);
  if (query.page) params.set("page", String(query.page));
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return request<Paginated<ImportRow>>(`/api/tenants/${tenantId}/import-jobs/${importJobId}/rows/${suffix}`);
}

export type ImportDecisionPayload = {
  row_id: number;
  decisions: Array<{
    decision_type: ImportDecision["decision_type"];
    payload_json?: Record<string, unknown>;
  }>;
};

export async function saveImportJobDecisions(
  tenantId: number,
  importJobId: number,
  rows: ImportDecisionPayload[],
): Promise<{ results: Array<{ row_id: number; decisions: ImportDecision[] }> }> {
  return request(`/api/tenants/${tenantId}/import-jobs/${importJobId}/decisions/`, {
    method: "POST",
    body: JSON.stringify({ rows }),
  });
}

export async function commitImportJob(
  tenantId: number,
  importJobId: number,
  skipUnresolved: boolean,
): Promise<ImportJob> {
  return request<ImportJob>(`/api/tenants/${tenantId}/import-jobs/${importJobId}/commit/`, {
    method: "POST",
    body: JSON.stringify({ skip_unresolved: skipUnresolved }),
  });
}

export function getImportJobErrorReportUrl(tenantId: number, importJobId: number): string {
  return `${API_BASE}/api/tenants/${tenantId}/import-jobs/${importJobId}/error-report/`;
}

export type ExportJobCreatePayload = {
  export_type: ExportJob["export_type"];
  format: ExportJob["format"];
  filters_json: Record<string, unknown>;
  selected_fields_json: string[];
};

export async function getExportJobs(tenantId: number): Promise<ExportJob[]> {
  const data = await request<ExportJob[] | Paginated<ExportJob>>(`/api/tenants/${tenantId}/export-jobs/`);
  return isPaginated(data) ? data.results : data;
}

export async function createExportJob(tenantId: number, payload: ExportJobCreatePayload): Promise<ExportJob> {
  return request<ExportJob>(`/api/tenants/${tenantId}/export-jobs/`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getExportJob(tenantId: number, exportJobId: number): Promise<ExportJob> {
  return request<ExportJob>(`/api/tenants/${tenantId}/export-jobs/${exportJobId}/`);
}

export function getExportJobFileUrl(fileUrl: string | null): string | null {
  if (!fileUrl) return null;
  if (fileUrl.startsWith("http://") || fileUrl.startsWith("https://")) return fileUrl;
  return `${API_BASE}${fileUrl}`;
}
