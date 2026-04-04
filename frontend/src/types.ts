export type Tenant = {
  id: number;
  name: string;
  slug: string;
  created_at: string;
  current_user_role: "superadmin" | "gruppeadmin" | "redigerer" | "leser" | null;
};

export type TenantMembership = {
  id: number;
  tenant: number;
  user: number;
  role: "superadmin" | "gruppeadmin" | "redigerer" | "leser";
  created_at: string;
  updated_at: string;
};

export type Tag = {
  id: number;
  tenant: number;
  name: string;
  slug: string;
  created_at: string;
};

export type Category = {
  id: number;
  name: string;
  slug: string;
  created_at: string;
};

export type Subcategory = {
  id: number;
  name: string;
  slug: string;
  created_at: string;
  category: Category;
};

export type OrganizationPersonNested = {
  id: number;
  status: "ACTIVE" | "INACTIVE";
  publish_person: boolean;
  created_at: string;
  person?: {
    id: number;
    full_name: string;
    title?: string | null;
    municipality: string;
    public_contacts: Array<{
      id?: number;
      type: string;
      value: string;
      is_primary?: boolean;
    }>;
  };
};

export type Person = {
  id: number;
  tenant: number;
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
  tags: Tag[];
  categories: Category[];
  subcategories: Subcategory[];
  created_at: string;
  updated_at: string;
  contacts?: PersonContact[];
};

export type OrganizationPerson = {
  id: number;
  tenant: number;
  organization: number;
  person: number;
  status: "ACTIVE" | "INACTIVE";
  publish_person: boolean;
  created_at: string;
};

export type PersonContact = {
  id: number;
  type: "EMAIL" | "PHONE";
  value: string;
  is_primary: boolean;
  is_public: boolean;
  created_at: string;
  tenant?: number;
  person?: number;
};

export type Organization = {
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
  thumbnail_image_url: string | null;
  auto_thumbnail_url: string | null;
  og_last_fetched_at: string | null;
  primary_link: string | null;
  primary_link_field: string | null;
  preview_image_url: string | null;
  tags: Tag[];
  categories: Category[];
  subcategories: Subcategory[];
  created_at: string;
  updated_at: string;
  active_people?: OrganizationPersonNested[];
};

export type Paginated<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

export type ImportJob = {
  id: number;
  tenant: number;
  created_by: number;
  source_type: "CSV" | "XLSX" | "GOOGLE_SHEET" | "CHECKIN" | "MAILMOJO" | "MANUAL_API";
  import_mode: "COMBINED" | "ORGANIZATIONS_ONLY" | "PEOPLE_ONLY";
  status:
    | "DRAFT"
    | "UPLOADED"
    | "PARSED"
    | "PREVIEW_READY"
    | "AWAITING_REVIEW"
    | "COMMITTING"
    | "COMPLETED"
    | "FAILED"
    | "CANCELLED";
  filename: string;
  file: string | null;
  summary_json: Record<string, unknown>;
  config_json: Record<string, unknown>;
  preview_report_file: string | null;
  error_report_file: string | null;
  committed_at: string | null;
  created_at: string;
  updated_at: string;
  rows_count?: number;
};

export type ImportDecision = {
  id: number;
  import_row: number;
  decided_by: number;
  decision_type:
    | "USE_EXISTING_ORGANIZATION"
    | "CREATE_NEW_ORGANIZATION"
    | "USE_EXISTING_PERSON"
    | "CREATE_NEW_PERSON"
    | "MAP_CATEGORY"
    | "MAP_SUBCATEGORY"
    | "ACCEPT_NEW_TAG"
    | "ACCEPT_AI_SUGGESTION"
    | "IGNORE_AI_SUGGESTION"
    | "SKIP_ROW";
  payload_json: Record<string, unknown>;
  created_at: string;
};

export type ImportRow = {
  id: number;
  import_job: number;
  row_number: number;
  raw_payload_json: Record<string, unknown>;
  normalized_payload_json: Record<string, unknown>;
  detected_entities_json: Record<string, unknown>;
  match_result_json: Record<string, unknown>;
  ai_suggestions_json: Record<string, unknown>;
  validation_errors_json: string[];
  warnings_json: string[];
  row_status: "VALID" | "INVALID" | "REVIEW_REQUIRED" | "SKIPPED" | "COMMITTED" | "COMMIT_FAILED";
  proposed_action: "CREATE" | "UPDATE" | "LINK_ONLY" | "SKIP";
  decision_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  decisions: ImportDecision[];
};

export type ExportJob = {
  id: number;
  tenant: number;
  created_by: number;
  export_type: "SEARCH_RESULTS" | "ADMIN_FULL" | "PERSONS_ONLY" | "ORGANIZATIONS_ONLY";
  format: "CSV" | "XLSX";
  filters_json: Record<string, unknown>;
  selected_fields_json: string[];
  status: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";
  file: string | null;
  summary_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};
