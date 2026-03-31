export type Tenant = {
  id: number;
  name: string;
  slug: string;
  created_at: string;
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
