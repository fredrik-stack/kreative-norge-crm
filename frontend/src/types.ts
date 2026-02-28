export type Tenant = {
  id: number;
  name: string;
  slug: string;
  created_at: string;
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
  is_published: boolean;
  publish_phone: boolean;
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
