-- Enable UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =========
-- Tenancy & Users
-- =========

CREATE TABLE tenant (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL,
  slug TEXT UNIQUE NOT NULL, -- "musikkontoret", "partner-org-1"
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE app_user (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email TEXT UNIQUE NOT NULL,
  full_name TEXT NOT NULL,
  password_hash TEXT, -- if not using SSO-only
  is_platform_superadmin BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_login_at TIMESTAMPTZ
);

-- user membership in tenants + role per tenant
CREATE TYPE tenant_role AS ENUM ('TENANT_ADMIN', 'EDITOR', 'READER');

CREATE TABLE tenant_membership (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  role tenant_role NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, user_id)
);

-- invitations (email invite into tenant)
CREATE TABLE tenant_invite (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
  invited_email TEXT NOT NULL,
  role tenant_role NOT NULL DEFAULT 'EDITOR',
  token TEXT UNIQUE NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  accepted_at TIMESTAMPTZ,
  created_by UUID REFERENCES app_user(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =========
-- Categories & Tags
-- =========

CREATE TABLE category (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
  name TEXT NOT NULL,                 -- "MUSIKK"
  parent_id UUID REFERENCES category(id) ON DELETE SET NULL, -- subcategory
  sort_order INT NOT NULL DEFAULT 0,
  UNIQUE (tenant_id, name, parent_id)
);

CREATE TABLE tag (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  created_by UUID REFERENCES app_user(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, lower(name))
);

-- =========
-- Core Entities: Organization & Person
-- =========

CREATE TYPE person_status AS ENUM ('ACTIVE', 'INACTIVE');

CREATE TABLE organization (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,

  name TEXT NOT NULL,
  org_number TEXT, -- orgnr, can be null for unknown
  email TEXT,
  phone TEXT,

  -- municipality handling: store municipality codes or names (MVP: name)
  -- You can later change to FK to a reference table of Norwegian municipalities.
  municipalities TEXT[] NOT NULL DEFAULT '{}',

  note TEXT,

  -- publish controls for public directory
  is_published BOOLEAN NOT NULL DEFAULT false,
  publish_phone BOOLEAN NOT NULL DEFAULT false,

  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  UNIQUE (tenant_id, org_number) -- allows dedup by orgnr inside tenant
);

-- social links for org/person, order matters for "first chosen field"
CREATE TYPE link_type AS ENUM ('WEBSITE', 'INSTAGRAM', 'TIKTOK', 'LINKEDIN', 'FACEBOOK', 'YOUTUBE');

CREATE TABLE entity_link (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
  entity_type TEXT NOT NULL CHECK (entity_type IN ('ORG','PERSON')),
  entity_id UUID NOT NULL,
  link_type link_type NOT NULL,
  url TEXT NOT NULL,
  sort_order INT NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX entity_link_entity_idx ON entity_link(tenant_id, entity_type, entity_id);

CREATE TABLE person (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,

  full_name TEXT NOT NULL,
  phone TEXT,
  emails TEXT[] NOT NULL DEFAULT '{}', -- multiple emails

  municipality TEXT, -- single municipality for person (per krav)
  note TEXT,

  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Relationship: org has many people; person can belong to many orgs (with status)
CREATE TABLE organization_person (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,

  organization_id UUID NOT NULL REFERENCES organization(id) ON DELETE CASCADE,
  person_id UUID NOT NULL REFERENCES person(id) ON DELETE CASCADE,

  status person_status NOT NULL DEFAULT 'ACTIVE',

  -- publish toggle for showing associated persons on public actor page
  publish_person BOOLEAN NOT NULL DEFAULT false,

  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, organization_id, person_id)
);

-- Categories assignment
CREATE TABLE organization_category (
  tenant_id UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
  organization_id UUID NOT NULL REFERENCES organization(id) ON DELETE CASCADE,
  category_id UUID NOT NULL REFERENCES category(id) ON DELETE CASCADE,
  PRIMARY KEY (tenant_id, organization_id, category_id)
);

CREATE TABLE person_category (
  tenant_id UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
  person_id UUID NOT NULL REFERENCES person(id) ON DELETE CASCADE,
  category_id UUID NOT NULL REFERENCES category(id) ON DELETE CASCADE,
  PRIMARY KEY (tenant_id, person_id, category_id)
);

-- Tags assignment
CREATE TABLE organization_tag (
  tenant_id UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
  organization_id UUID NOT NULL REFERENCES organization(id) ON DELETE CASCADE,
  tag_id UUID NOT NULL REFERENCES tag(id) ON DELETE CASCADE,
  PRIMARY KEY (tenant_id, organization_id, tag_id)
);

CREATE TABLE person_tag (
  tenant_id UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
  person_id UUID NOT NULL REFERENCES person(id) ON DELETE CASCADE,
  tag_id UUID NOT NULL REFERENCES tag(id) ON DELETE CASCADE,
  PRIMARY KEY (tenant_id, person_id, tag_id)
);

-- =========
-- Public directory projection (optional but useful)
-- =========
-- You can compute actor pages on the fly,
-- or store a materialized snapshot for speed.
-- MVP: compute on the fly via API filters on organization fields.

-- =========
-- Imports (CSV/XLSX/Google Sheets)
-- =========

CREATE TYPE import_source_type AS ENUM ('CSV', 'XLSX', 'GOOGLE_SHEET');

CREATE TYPE import_status AS ENUM ('UPLOADED', 'MAPPED', 'VALIDATED', 'READY_TO_MERGE', 'MERGED', 'FAILED');

CREATE TABLE import_job (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
  created_by UUID REFERENCES app_user(id),

  source_type import_source_type NOT NULL,
  source_name TEXT NOT NULL, -- filename or sheet name
  status import_status NOT NULL DEFAULT 'UPLOADED',

  -- mapping config: store JSON mapping col->field
  mapping_json JSONB,

  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- raw/staging rows
CREATE TABLE import_row (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  import_job_id UUID NOT NULL REFERENCES import_job(id) ON DELETE CASCADE,
  row_number INT NOT NULL,

  raw_json JSONB NOT NULL,        -- original row
  normalized_json JSONB,          -- normalized output
  suggested_entity_type TEXT CHECK (suggested_entity_type IN ('ORG','PERSON')),
  match_candidates JSONB,         -- list of candidate IDs + score
  chosen_match_id UUID,           -- if user chooses existing record to merge into
  action TEXT CHECK (action IN ('CREATE_NEW','MERGE_INTO','SKIP')) DEFAULT 'CREATE_NEW',
  issues JSONB,                   -- validation issues
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  UNIQUE(import_job_id, row_number)
);

-- simple audit log (recommended even in MVP)
CREATE TABLE audit_log (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
  user_id UUID REFERENCES app_user(id),
  action TEXT NOT NULL,
  entity_type TEXT,
  entity_id UUID,
  meta JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Keep updated_at fresh (use trigger in real implementation)
