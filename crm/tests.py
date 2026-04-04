import tempfile
import zipfile
import importlib
from io import BytesIO
from xml.sax.saxutils import escape
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from unittest.mock import patch
from rest_framework.test import APIClient

from .models import (
    Organization,
    OrganizationPerson,
    Person,
    PersonContact,
    Tag,
    Category,
    Subcategory,
    Tenant,
    TenantMembership,
    ImportJob,
    ImportRow,
    ImportDecision,
    ImportCommitLog,
    ExportJob,
)
from .services.open_graph import ImageCandidate, choose_best_thumbnail, fallback_preview_image
from .serializers import PersonSerializer
import_commit_module = importlib.import_module("crm.services.import.commit")
import_matchers_module = importlib.import_module("crm.services.import.matchers")
import_normalizers_module = importlib.import_module("crm.services.import.normalizers")
import_ai_suggestions_module = importlib.import_module("crm.services.import.ai_suggestions")
match_row_entities = import_matchers_module.match_row_entities
normalize_import_row = import_normalizers_module.normalize_import_row
build_import_template_config = import_normalizers_module.build_import_template_config
generate_ai_suggestions = import_ai_suggestions_module.generate_ai_suggestions


def grant_membership(user, tenant, role=TenantMembership.Role.REDIGERER):
    return TenantMembership.objects.create(tenant=tenant, user=user, role=role)


@override_settings(SECURE_SSL_REDIRECT=False)
class AuthApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.tenant = Tenant.objects.create(name="Auth Tenant", slug="auth-tenant")
        self.user = get_user_model().objects.create_user(
            username="editor-auth",
            password="secret123",
        )
        TenantMembership.objects.create(
            tenant=self.tenant,
            user=self.user,
            role=TenantMembership.Role.REDIGERER,
        )

    def test_csrf_endpoint_returns_token_and_cookie(self):
        response = self.client.get("/api/auth/csrf/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("csrfToken", response.json())
        self.assertTrue(response.json()["csrfToken"])
        self.assertIn("csrftoken", response.cookies)

    def test_session_endpoint_returns_unauthenticated_when_logged_out(self):
        response = self.client.get("/api/auth/session/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"authenticated": False, "user": None})

    def test_login_requires_username_and_password(self):
        response = self.client.post("/api/auth/login/", {"username": ""}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("non_field_errors", response.json())

    def test_login_rejects_invalid_credentials(self):
        response = self.client.post(
            "/api/auth/login/",
            {"username": "editor-auth", "password": "wrong"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("non_field_errors", response.json())

    def test_login_creates_session_and_session_endpoint_reflects_authentication(self):
        login_response = self.client.post(
            "/api/auth/login/",
            {"username": "editor-auth", "password": "secret123"},
            format="json",
        )
        self.assertEqual(login_response.status_code, 200, login_response.content)
        self.assertTrue(login_response.json()["authenticated"])
        self.assertEqual(login_response.json()["user"]["username"], "editor-auth")

        session_response = self.client.get("/api/auth/session/")
        self.assertEqual(session_response.status_code, 200)
        self.assertEqual(session_response.json()["authenticated"], True)
        self.assertEqual(session_response.json()["user"]["username"], "editor-auth")
        self.assertEqual(session_response.json()["user"]["memberships"][0]["tenant"], self.tenant.id)
        self.assertEqual(session_response.json()["user"]["memberships"][0]["role"], "redigerer")

    def test_logout_requires_authentication(self):
        response = self.client.post("/api/auth/logout/", {}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_logout_clears_session(self):
        self.client.force_login(self.user)

        response = self.client.post("/api/auth/logout/", {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"authenticated": False, "user": None})

        session_response = self.client.get("/api/auth/session/")
        self.assertEqual(session_response.status_code, 200)
        self.assertEqual(session_response.json(), {"authenticated": False, "user": None})


@override_settings(SECURE_SSL_REDIRECT=False)
class AuthenticatedAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username="editor",
            password="secret123",
        )
        self.client.force_login(self.user)


@override_settings(SECURE_SSL_REDIRECT=False)
class ImportExportModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="model-user", password="secret123")
        self.tenant = Tenant.objects.create(name="Import Tenant", slug="import-tenant")

    def test_import_models_can_be_created(self):
        job = ImportJob.objects.create(
            tenant=self.tenant,
            created_by=self.user,
            source_type=ImportJob.SourceType.CSV,
            import_mode=ImportJob.ImportMode.COMBINED,
        )
        row = ImportRow.objects.create(import_job=job, row_number=1, raw_payload_json={"name": "Test"})
        decision = ImportDecision.objects.create(
            import_row=row,
            decided_by=self.user,
            decision_type=ImportDecision.DecisionType.SKIP_ROW,
            payload_json={"reason": "manual"},
        )
        log = ImportCommitLog.objects.create(
            import_job=job,
            import_row=row,
            entity_type=ImportCommitLog.EntityType.ORGANIZATION,
            entity_id="123",
            action=ImportCommitLog.Action.SKIPPED,
            details_json={"status": "noop"},
        )

        self.assertEqual(job.status, ImportJob.Status.DRAFT)
        self.assertEqual(row.row_status, ImportRow.RowStatus.REVIEW_REQUIRED)
        self.assertEqual(row.proposed_action, ImportRow.ProposedAction.SKIP)
        self.assertEqual(str(decision), f"Decision {decision.get_decision_type_display()} for row 1")
        self.assertEqual(str(log), f"{log.get_action_display()} {log.get_entity_type_display()} for job {job.id}")

    def test_export_job_can_be_created(self):
        job = ExportJob.objects.create(
            tenant=self.tenant,
            created_by=self.user,
            export_type=ExportJob.ExportType.SEARCH_RESULTS,
            format=ExportJob.Format.CSV,
        )

        self.assertEqual(job.status, ExportJob.Status.PENDING)
        self.assertEqual(str(job), f"ExportJob #{job.id} ({self.tenant.slug})")


class ImportExportAuthenticatedAPITestCase(TestCase):
    role_name = "redigerer"

    def setUp(self):
        self.client = APIClient()
        self.tenant = Tenant.objects.create(name="Tenant A", slug="tenant-a")
        self.other_tenant = Tenant.objects.create(name="Tenant B", slug="tenant-b")
        self.user = get_user_model().objects.create_user(
            username=f"{self.role_name}-user",
            password="secret123",
        )
        if self.role_name != "superadmin":
            group, _ = Group.objects.get_or_create(name=self.role_name)
            self.user.groups.add(group)
            grant_membership(self.user, self.tenant, role=self.role_name)
        else:
            self.user.is_superuser = True
            self.user.is_staff = True
            self.user.save(update_fields=["is_superuser", "is_staff"])
        self.client.force_login(self.user)

    def import_jobs_url(self, tenant_id=None):
        return f"/api/tenants/{tenant_id or self.tenant.id}/import-jobs/"

    def export_jobs_url(self, tenant_id=None):
        return f"/api/tenants/{tenant_id or self.tenant.id}/export-jobs/"


@override_settings(SECURE_SSL_REDIRECT=False, MEDIA_ROOT=tempfile.gettempdir())
class ImportExportApiTests(ImportExportAuthenticatedAPITestCase):
    role_name = "redigerer"

    def setUp(self):
        super().setUp()
        self.import_job = ImportJob.objects.create(
            tenant=self.tenant,
            created_by=self.user,
            source_type=ImportJob.SourceType.CSV,
            import_mode=ImportJob.ImportMode.COMBINED,
        )
        self.other_import_job = ImportJob.objects.create(
            tenant=self.other_tenant,
            created_by=self.user,
            source_type=ImportJob.SourceType.XLSX,
            import_mode=ImportJob.ImportMode.PEOPLE_ONLY,
        )
        self.export_job = ExportJob.objects.create(
            tenant=self.tenant,
            created_by=self.user,
            export_type=ExportJob.ExportType.SEARCH_RESULTS,
            format=ExportJob.Format.CSV,
        )
        self.other_export_job = ExportJob.objects.create(
            tenant=self.other_tenant,
            created_by=self.user,
            export_type=ExportJob.ExportType.ADMIN_FULL,
            format=ExportJob.Format.XLSX,
        )

    def test_create_import_job_sets_tenant_and_created_by(self):
        response = self.client.post(
            self.import_jobs_url(),
            {
                "tenant": self.other_tenant.id,
                "source_type": ImportJob.SourceType.CSV,
                "import_mode": ImportJob.ImportMode.COMBINED,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.content)
        created = ImportJob.objects.get(id=response.json()["id"])
        self.assertEqual(created.tenant_id, self.tenant.id)
        self.assertEqual(created.created_by_id, self.user.id)
        self.assertEqual(created.status, ImportJob.Status.DRAFT)

    def test_create_import_job_sets_template_config_for_separate_modes(self):
        response = self.client.post(
            self.import_jobs_url(),
            {
                "source_type": ImportJob.SourceType.XLSX,
                "import_mode": ImportJob.ImportMode.ORGANIZATIONS_ONLY,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.content)
        created = ImportJob.objects.get(id=response.json()["id"])
        self.assertEqual(created.config_json, build_import_template_config(ImportJob.ImportMode.ORGANIZATIONS_ONLY))

    def test_list_import_jobs_is_scoped_to_tenant(self):
        response = self.client.get(self.import_jobs_url())
        self.assertEqual(response.status_code, 200)

        ids = {item["id"] for item in response.json()}
        self.assertIn(self.import_job.id, ids)
        self.assertNotIn(self.other_import_job.id, ids)

    def test_get_import_job_detail_is_scoped_to_tenant(self):
        response = self.client.get(f"{self.import_jobs_url()}{self.import_job.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], self.import_job.id)

        response = self.client.get(f"{self.import_jobs_url()}{self.other_import_job.id}/")
        self.assertEqual(response.status_code, 404)

    def test_upload_sets_file_name_and_status(self):
        upload = SimpleUploadedFile("contacts.csv", b"name,email\nAda,ada@example.com\n", content_type="text/csv")

        response = self.client.post(f"{self.import_jobs_url()}{self.import_job.id}/upload/", {"file": upload})

        self.assertEqual(response.status_code, 200, response.content)
        self.import_job.refresh_from_db()
        self.assertEqual(self.import_job.filename, "contacts.csv")
        self.assertEqual(self.import_job.status, ImportJob.Status.UPLOADED)
        self.assertTrue(self.import_job.file.name.endswith("contacts.csv"))

    def test_rows_endpoint_returns_paginated_empty_results(self):
        response = self.client.get(f"{self.import_jobs_url()}{self.import_job.id}/rows/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 0)
        self.assertEqual(response.json()["results"], [])

    def test_rows_endpoint_returns_existing_rows(self):
        row = ImportRow.objects.create(
            import_job=self.import_job,
            row_number=1,
            raw_payload_json={"name": "Ada"},
        )
        ImportDecision.objects.create(
            import_row=row,
            decided_by=self.user,
            decision_type=ImportDecision.DecisionType.SKIP_ROW,
            payload_json={"reason": "test"},
        )

        response = self.client.get(f"{self.import_jobs_url()}{self.import_job.id}/rows/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["results"][0]["row_number"], 1)
        self.assertEqual(len(response.json()["results"][0]["decisions"]), 1)

    def test_create_export_job_sets_tenant_and_created_by(self):
        response = self.client.post(
            self.export_jobs_url(),
            {
                "tenant": self.other_tenant.id,
                "export_type": ExportJob.ExportType.PERSONS_ONLY,
                "format": ExportJob.Format.XLSX,
                "filters_json": {"q": "Ada"},
                "selected_fields_json": ["full_name"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.content)
        created = ExportJob.objects.get(id=response.json()["id"])
        self.assertEqual(created.tenant_id, self.tenant.id)
        self.assertEqual(created.created_by_id, self.user.id)
        self.assertEqual(created.status, ExportJob.Status.PENDING)

    def test_list_export_jobs_is_scoped_to_tenant(self):
        response = self.client.get(self.export_jobs_url())
        self.assertEqual(response.status_code, 200)

        ids = {item["id"] for item in response.json()}
        self.assertIn(self.export_job.id, ids)
        self.assertNotIn(self.other_export_job.id, ids)

    def test_get_export_job_detail_is_scoped_to_tenant(self):
        response = self.client.get(f"{self.export_jobs_url()}{self.export_job.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], self.export_job.id)

        response = self.client.get(f"{self.export_jobs_url()}{self.other_export_job.id}/")
        self.assertEqual(response.status_code, 404)


@override_settings(SECURE_SSL_REDIRECT=False)
class ImportExportPermissionTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Permission Tenant", slug="permission-tenant")

    def _client_for_role(self, role_name: str | None = None, *, superuser: bool = False):
        client = APIClient()
        user = get_user_model().objects.create_user(
            username=f"user-{role_name or 'anon'}-{get_user_model().objects.count()}",
            password="secret123",
        )
        if superuser:
            user.is_superuser = True
            user.is_staff = True
            user.save(update_fields=["is_superuser", "is_staff"])
        elif role_name:
            group, _ = Group.objects.get_or_create(name=role_name)
            user.groups.add(group)
            grant_membership(user, self.tenant, role=role_name)
        client.force_login(user)
        return client

    def test_superadmin_has_access(self):
        client = self._client_for_role(superuser=True)
        response = client.get(f"/api/tenants/{self.tenant.id}/import-jobs/")
        self.assertEqual(response.status_code, 200)

    def test_gruppeadmin_has_access(self):
        client = self._client_for_role("gruppeadmin")
        response = client.get(f"/api/tenants/{self.tenant.id}/import-jobs/")
        self.assertEqual(response.status_code, 200)

    def test_redigerer_has_access(self):
        client = self._client_for_role("redigerer")
        response = client.get(f"/api/tenants/{self.tenant.id}/export-jobs/")
        self.assertEqual(response.status_code, 200)

    def test_leser_is_forbidden(self):
        client = self._client_for_role("leser")
        response = client.get(f"/api/tenants/{self.tenant.id}/import-jobs/")
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_user_is_forbidden(self):
        client = APIClient()
        response = client.get(f"/api/tenants/{self.tenant.id}/import-jobs/")
        self.assertEqual(response.status_code, 403)


def build_test_xlsx(rows: list[dict]) -> bytes:
    headers = list(rows[0].keys()) if rows else []

    def cell_ref(col_index: int, row_index: int) -> str:
        result = ""
        col = col_index + 1
        while col:
            col, remainder = divmod(col - 1, 26)
            result = chr(65 + remainder) + result
        return f"{result}{row_index}"

    all_strings = headers[:]
    for row in rows:
        all_strings.extend(str(row.get(header, "")) for header in headers)
    unique_strings = []
    index_map = {}
    for value in all_strings:
        if value not in index_map:
            index_map[value] = len(unique_strings)
            unique_strings.append(value)

    shared_strings = "".join(f"<si><t>{escape(value)}</t></si>" for value in unique_strings)
    header_cells = "".join(
        f'<c r="{cell_ref(index, 1)}" t="s"><v>{index_map[header]}</v></c>'
        for index, header in enumerate(headers)
    )
    row_xml = [f'<row r="1">{header_cells}</row>']
    for row_index, row in enumerate(rows, start=2):
        cells = "".join(
            f'<c r="{cell_ref(index, row_index)}" t="s"><v>{index_map[str(row.get(header, ""))]}</v></c>'
            for index, header in enumerate(headers)
        )
        row_xml.append(f'<row r="{row_index}">{cells}</row>')

    worksheet_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(row_xml)}</sheetData>'
        "</worksheet>"
    )
    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets>'
        "</workbook>"
    )
    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" '
        'Target="sharedStrings.xml"/>'
        "</Relationships>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
        "</Types>"
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        "</Relationships>"
    )
    shared_strings_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"{shared_strings}</sst>"
    )

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", root_rels)
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        archive.writestr("xl/sharedStrings.xml", shared_strings_xml)
        archive.writestr("xl/worksheets/sheet1.xml", worksheet_xml)
    return buffer.getvalue()


@override_settings(SECURE_SSL_REDIRECT=False, MEDIA_ROOT=tempfile.gettempdir())
class ImportPhaseTwoApiTests(ImportExportAuthenticatedAPITestCase):
    role_name = "redigerer"

    def setUp(self):
        super().setUp()
        self.music = Category.objects.get(name="Musikk")
        self.band = Subcategory.objects.get(name="Artister & Band")
        self.job = ImportJob.objects.create(
            tenant=self.tenant,
            created_by=self.user,
            source_type=ImportJob.SourceType.CSV,
            import_mode=ImportJob.ImportMode.COMBINED,
            status=ImportJob.Status.UPLOADED,
        )
        self.base_row = {
            "organization_name": "Nordlyd AS",
            "organization_org_number": "123 456 789",
            "organization_email": "post@nordlyd.no",
            "organization_phone": "+4711111111",
            "organization_publish_phone": "",
            "organization_municipalities": "Oslo",
            "organization_website_url": "https://nordlyd.no",
            "organization_instagram_url": "",
            "organization_tiktok_url": "",
            "organization_linkedin_url": "",
            "organization_facebook_url": "",
            "organization_youtube_url": "",
            "organization_description": "Konsertselskap",
            "organization_note": "Internt notat",
            "organization_is_published": "",
            "organization_categories": "Musikk",
            "organization_subcategories": "Artister & Band",
            "organization_tags": "jazz, klubb",
            "person_full_name": "Ada Artist",
            "person_title": "Manager",
            "person_email": "ada@example.com",
            "person_phone": "+4722222222",
            "person_municipality": "Oslo",
            "person_website_url": "",
            "person_instagram_url": "",
            "person_tiktok_url": "",
            "person_linkedin_url": "",
            "person_facebook_url": "",
            "person_youtube_url": "",
            "person_note": "Kontaktperson",
            "person_categories": "Musikk",
            "person_subcategories": "Artister & Band",
            "person_tags": "jazz",
            "link_status": "ACTIVE",
            "link_publish_person": "",
            "person_secondary_emails": "ada.booking@example.com",
            "person_secondary_phones": "+4733333333",
            "person_secondary_emails_public": "",
            "person_secondary_phones_public": "",
        }

    def _upload_csv(self, rows=None):
        rows = rows or [self.base_row]
        headers = list(rows[0].keys())
        lines = [",".join(headers)]
        for row in rows:
            values = []
            for header in headers:
                value = str(row.get(header, ""))
                if "," in value:
                    value = f'"{value}"'
                values.append(value)
            lines.append(",".join(values))
        upload = SimpleUploadedFile("import.csv", "\n".join(lines).encode("utf-8"), content_type="text/csv")
        self.job.file = upload
        self.job.filename = "import.csv"
        self.job.save(update_fields=["file", "filename", "updated_at"])

    def _upload_xlsx(self, rows=None):
        rows = rows or [self.base_row]
        upload = SimpleUploadedFile(
            "import.xlsx",
            build_test_xlsx(rows),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.job.source_type = ImportJob.SourceType.XLSX
        self.job.file = upload
        self.job.filename = "import.xlsx"
        self.job.save(update_fields=["source_type", "file", "filename", "updated_at"])

    def test_csv_preview_creates_rows_and_summary(self):
        self._upload_csv()
        response = self.client.post(f"{self.import_jobs_url()}{self.job.id}/preview/", {}, format="json")
        self.assertEqual(response.status_code, 200, response.content)

        self.job.refresh_from_db()
        self.assertEqual(self.job.status, ImportJob.Status.PREVIEW_READY)
        self.assertEqual(self.job.rows.count(), 1)
        row = self.job.rows.get()
        self.assertEqual(row.row_status, ImportRow.RowStatus.VALID)
        self.assertEqual(row.proposed_action, ImportRow.ProposedAction.CREATE)
        self.assertEqual(self.job.summary_json["rows_total"], 1)

    def test_xlsx_preview_creates_rows(self):
        self._upload_xlsx()
        response = self.client.post(f"{self.import_jobs_url()}{self.job.id}/preview/", {}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.job.rows.count(), 1)
        self.assertEqual(self.job.rows.get().normalized_payload_json["person"]["full_name"], "Ada Artist")

    def test_organizations_only_preview_accepts_actor_template(self):
        self.job.import_mode = ImportJob.ImportMode.ORGANIZATIONS_ONLY
        self.job.save(update_fields=["import_mode", "updated_at"])
        organization_row = {
            key: value
            for key, value in self.base_row.items()
            if key.startswith("organization_")
        }
        self._upload_csv([organization_row])

        response = self.client.post(f"{self.import_jobs_url()}{self.job.id}/preview/", {}, format="json")
        self.assertEqual(response.status_code, 200, response.content)

        row = self.job.rows.get()
        self.assertEqual(row.normalized_payload_json["organization"]["name"], "Nordlyd AS")
        self.assertEqual(row.normalized_payload_json["person"]["full_name"], "")

    def test_people_only_preview_accepts_people_template_and_keeps_link_target(self):
        self.job.import_mode = ImportJob.ImportMode.PEOPLE_ONLY
        self.job.save(update_fields=["import_mode", "updated_at"])
        people_row = {
            key: value
            for key, value in self.base_row.items()
            if key.startswith("person_") or key in {"organization_org_number", "organization_name", "link_status", "link_publish_person"}
        }
        self._upload_csv([people_row])

        response = self.client.post(f"{self.import_jobs_url()}{self.job.id}/preview/", {}, format="json")
        self.assertEqual(response.status_code, 200, response.content)

        row = self.job.rows.get()
        self.assertEqual(row.normalized_payload_json["person"]["full_name"], "Ada Artist")
        self.assertEqual(row.normalized_payload_json["organization"]["org_number"], "123456789")
        self.assertEqual(row.normalized_payload_json["organization"]["name"], "Nordlyd AS")

    def test_preview_rejects_unknown_columns_for_selected_import_mode(self):
        self.job.import_mode = ImportJob.ImportMode.ORGANIZATIONS_ONLY
        self.job.save(update_fields=["import_mode", "updated_at"])
        invalid_row = {
            "organization_name": "Nordlyd AS",
            "organization_org_number": "123456789",
            "person_full_name": "Should not be here",
        }
        self._upload_csv([invalid_row])

        response = self.client.post(f"{self.import_jobs_url()}{self.job.id}/preview/", {}, format="json")
        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn("Unsupported columns", response.json()["detail"])

    def test_normalization_applies_safe_defaults(self):
        normalized = normalize_import_row(self.base_row)
        self.assertFalse(normalized["organization"]["is_published"])
        self.assertFalse(normalized["organization"]["publish_phone"])
        self.assertFalse(normalized["link"]["publish_person"])
        self.assertEqual(normalized["organization"]["org_number"], "123456789")
        self.assertEqual(normalized["person"]["secondary_contacts"][0]["is_public"], False)

    def test_validation_marks_unknown_taxonomy_for_review(self):
        invalid_row = self.base_row | {"organization_categories": "Ukjent kategori"}
        self._upload_csv([invalid_row])
        response = self.client.post(f"{self.import_jobs_url()}{self.job.id}/preview/", {}, format="json")
        self.assertEqual(response.status_code, 200)
        row = self.job.rows.get()
        self.assertEqual(row.row_status, ImportRow.RowStatus.REVIEW_REQUIRED)
        self.assertTrue(any("Unknown category:" in item for item in row.warnings_json))

    def test_organization_matching_prefers_org_number(self):
        existing = Organization.objects.create(tenant=self.tenant, name="Existing", org_number="123456789")
        match = match_row_entities(self.tenant, normalize_import_row(self.base_row))
        self.assertEqual(match["organization"]["exact_id"], existing.id)
        self.assertEqual(match["organization"]["rule"], "ORG_NUMBER")

    def test_person_matching_prefers_email(self):
        existing = Person.objects.create(tenant=self.tenant, full_name="Someone Else", email="ada@example.com")
        match = match_row_entities(self.tenant, normalize_import_row(self.base_row))
        self.assertEqual(match["person"]["exact_id"], existing.id)
        self.assertEqual(match["person"]["rule"], "EMAIL")

    def test_decisions_are_saved(self):
        review_row = self.base_row | {"organization_categories": "Ukjent kategori"}
        self._upload_csv([review_row])
        self.client.post(f"{self.import_jobs_url()}{self.job.id}/preview/", {}, format="json")
        row = self.job.rows.get()

        response = self.client.post(
            f"{self.import_jobs_url()}{self.job.id}/decisions/",
            {
                "rows": [
                    {
                        "row_id": row.id,
                        "decisions": [
                            {
                                "decision_type": "MAP_CATEGORY",
                                "payload_json": {"category_id": self.music.id},
                            }
                        ],
                    }
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        row.refresh_from_db()
        self.assertEqual(row.decisions.count(), 1)
        self.assertEqual(row.row_status, ImportRow.RowStatus.VALID)

    @patch("crm.services.import.commit.refresh_organization_open_graph")
    def test_commit_success_creates_entities_and_contacts(self, refresh_mock):
        self._upload_csv()
        self.client.post(f"{self.import_jobs_url()}{self.job.id}/preview/", {}, format="json")

        response = self.client.post(f"{self.import_jobs_url()}{self.job.id}/commit/", {"skip_unresolved": False}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, ImportJob.Status.COMPLETED)

        organization = Organization.objects.get(tenant=self.tenant, org_number="123456789")
        person = Person.objects.get(tenant=self.tenant, email="ada@example.com")
        link = OrganizationPerson.objects.get(tenant=self.tenant, organization=organization, person=person)
        self.assertEqual(link.status, "ACTIVE")
        self.assertFalse(link.publish_person)
        self.assertFalse(organization.is_published)
        self.assertFalse(organization.publish_phone)
        self.assertEqual(person.title, "Manager")
        self.assertEqual(person.contacts.filter(type="EMAIL", is_primary=True).count(), 1)
        self.assertEqual(person.contacts.filter(type="PHONE", is_primary=True).count(), 1)
        self.assertTrue(person.contacts.filter(value="ada.booking@example.com", is_public=False).exists())
        self.assertTrue(Tag.objects.filter(tenant=self.tenant, name="jazz").exists())
        self.assertGreater(self.job.commit_logs.count(), 0)
        refresh_mock.assert_called_once()

    def test_commit_is_blocked_by_unresolved_rows(self):
        review_row = self.base_row | {"organization_categories": "Ukjent kategori"}
        self._upload_csv([review_row])
        self.client.post(f"{self.import_jobs_url()}{self.job.id}/preview/", {}, format="json")

        response = self.client.post(f"{self.import_jobs_url()}{self.job.id}/commit/", {"skip_unresolved": False}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("detail", response.json())

    def test_preview_and_commit_are_tenant_scoped(self):
        self._upload_csv()
        response = self.client.post(f"/api/tenants/{self.other_tenant.id}/import-jobs/{self.job.id}/preview/", {}, format="json")
        self.assertEqual(response.status_code, 404)

    def test_rows_endpoint_filters_by_status(self):
        review_row = self.base_row | {"organization_categories": "Ukjent kategori"}
        self._upload_csv([self.base_row, review_row])
        self.client.post(f"{self.import_jobs_url()}{self.job.id}/preview/", {}, format="json")

        response = self.client.get(f"{self.import_jobs_url()}{self.job.id}/rows/", {"status": "REVIEW_REQUIRED"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)

    def test_error_report_endpoint_returns_report_file(self):
        review_row = self.base_row | {"organization_categories": "Ukjent kategori"}
        self._upload_csv([review_row])
        self.client.post(f"{self.import_jobs_url()}{self.job.id}/preview/", {}, format="json")

        response = self.client.get(f"{self.import_jobs_url()}{self.job.id}/error-report/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment;", response["Content-Disposition"])

    def test_ai_suggestions_are_generated_and_stored_separately(self):
        row = self.base_row | {"organization_website_url": "", "organization_note": "Sterk aktør i musikkfeltet."}
        self._upload_csv([row])
        response = self.client.post(f"{self.import_jobs_url()}{self.job.id}/preview/", {}, format="json")
        self.assertEqual(response.status_code, 200, response.content)

        row = self.job.rows.get()
        self.assertIn("suggested_fields", row.ai_suggestions_json)
        self.assertIn("organization_website_url", row.ai_suggestions_json["suggested_fields"])
        self.assertEqual(row.normalized_payload_json["organization"]["website_url"], "")

    def test_generate_ai_suggestions_never_sets_publish_or_public_fields(self):
        suggestions = generate_ai_suggestions(self.tenant, normalize_import_row(self.base_row), {"organization": {}, "person": {}})
        forbidden_keys = {
            "organization_is_published",
            "organization_publish_phone",
            "link_publish_person",
            "person_contact_is_public",
        }
        self.assertTrue(forbidden_keys.isdisjoint(set((suggestions.get("suggested_fields") or {}).keys())))

    @override_settings(
        OPENAI_IMPORT_ENABLED=True,
        OPENAI_API_KEY="test-key",
        OPENAI_IMPORT_MODEL="gpt-5.4",
        OPENAI_IMPORT_TIMEOUT=5,
    )
    def test_generate_ai_suggestions_can_use_openai_provider_when_available(self):
        class FakeResponse:
            output_text = (
                '{"organization_match_candidates":[{"id":12,"score":0.93,"reason":"name+domain","label":"Nordlyd AS"}],'
                '"person_match_candidates":[],'
                '"suggested_fields":{"organization_website_url":{"value":"https://nordlyd.no","confidence":0.81,"source":"ai_enrichment","requires_review":true},'
                '"organization_is_published":{"value":true,"confidence":0.99,"source":"ai_enrichment","requires_review":true}},'
                '"provider":"openai"}'
            )

        class FakeResponses:
            def create(self, **kwargs):
                self.kwargs = kwargs
                return FakeResponse()

        class FakeOpenAI:
            def __init__(self, api_key, timeout):
                self.api_key = api_key
                self.timeout = timeout
                self.responses = FakeResponses()

        with patch.object(import_ai_suggestions_module, "OpenAI", FakeOpenAI):
            suggestions = generate_ai_suggestions(
                self.tenant,
                normalize_import_row(self.base_row),
                {"organization": {}, "person": {}},
            )

        self.assertEqual(suggestions["provider"], "openai")
        self.assertEqual(suggestions["organization_match_candidates"][0]["id"], 12)
        self.assertEqual(
            suggestions["suggested_fields"]["organization_website_url"]["value"],
            "https://nordlyd.no",
        )
        self.assertNotIn("organization_is_published", suggestions["suggested_fields"])

    @patch("crm.services.import.commit.refresh_organization_open_graph")
    def test_accepted_ai_suggestion_can_influence_commit(self, refresh_mock):
        row = self.base_row | {"organization_website_url": "", "organization_note": "Sterk aktør i musikkfeltet."}
        self._upload_csv([row])
        self.client.post(f"{self.import_jobs_url()}{self.job.id}/preview/", {}, format="json")
        preview_row = self.job.rows.get()

        response = self.client.post(
            f"{self.import_jobs_url()}{self.job.id}/decisions/",
            {
                "rows": [
                    {
                        "row_id": preview_row.id,
                        "decisions": [
                            {
                                "decision_type": "ACCEPT_AI_SUGGESTION",
                                "payload_json": {
                                    "suggestion_key": "organization_description",
                                    "value": "Suggested short description",
                                },
                            }
                        ],
                    }
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)

        commit_response = self.client.post(
            f"{self.import_jobs_url()}{self.job.id}/commit/",
            {"skip_unresolved": False},
            format="json",
        )
        self.assertEqual(commit_response.status_code, 200, commit_response.content)
        organization = Organization.objects.get(tenant=self.tenant, org_number="123456789")
        self.assertEqual(organization.description, "Suggested short description")
        refresh_mock.assert_not_called()

    @patch("crm.services.import.commit.refresh_organization_open_graph")
    def test_unaccepted_ai_suggestion_does_not_influence_commit(self, refresh_mock):
        row = self.base_row | {"organization_website_url": "", "organization_note": "Sterk aktør i musikkfeltet."}
        self._upload_csv([row])
        self.client.post(f"{self.import_jobs_url()}{self.job.id}/preview/", {}, format="json")

        commit_response = self.client.post(
            f"{self.import_jobs_url()}{self.job.id}/commit/",
            {"skip_unresolved": False},
            format="json",
        )
        self.assertEqual(commit_response.status_code, 200, commit_response.content)
        organization = Organization.objects.get(tenant=self.tenant, org_number="123456789")
        self.assertEqual(organization.description, "Konsertselskap")
        refresh_mock.assert_not_called()

    @patch("crm.services.import.commit.refresh_organization_open_graph")
    def test_forbidden_publish_flags_are_not_set_even_if_ai_suggestion_is_accepted(self, refresh_mock):
        self._upload_csv()
        self.client.post(f"{self.import_jobs_url()}{self.job.id}/preview/", {}, format="json")
        preview_row = self.job.rows.get()

        response = self.client.post(
            f"{self.import_jobs_url()}{self.job.id}/decisions/",
            {
                "rows": [
                    {
                        "row_id": preview_row.id,
                        "decisions": [
                            {
                                "decision_type": "ACCEPT_AI_SUGGESTION",
                                "payload_json": {"suggestion_key": "organization_is_published", "value": True},
                            }
                        ],
                    }
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)

        commit_response = self.client.post(
            f"{self.import_jobs_url()}{self.job.id}/commit/",
            {"skip_unresolved": False},
            format="json",
        )
        self.assertEqual(commit_response.status_code, 200, commit_response.content)
        organization = Organization.objects.get(tenant=self.tenant, org_number="123456789")
        self.assertFalse(organization.is_published)
        self.assertFalse(organization.publish_phone)
        link = OrganizationPerson.objects.get(tenant=self.tenant, organization=organization)
        self.assertFalse(link.publish_person)
        self.assertFalse(PersonContact.objects.filter(person=link.person, is_public=True).exists())
        refresh_mock.assert_called_once()


class PersonContactViewSetTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Tenant A", slug="tenant-a")
        self.other_tenant = Tenant.objects.create(name="Tenant B", slug="tenant-b")
        grant_membership(self.user, self.tenant)

        self.person_a = Person.objects.create(
            tenant=self.tenant,
            full_name="Alice Example",
            email="alice@example.com",
            phone="47123456",
            municipality="Oslo",
        )
        self.person_b = Person.objects.create(
            tenant=self.tenant,
            full_name="Bob Example",
            email="bob@example.com",
            phone="47999999",
            municipality="Bergen",
        )
        self.person_other_tenant = Person.objects.create(
            tenant=self.other_tenant,
            full_name="Other Tenant Person",
        )

        self.contact_a = PersonContact.objects.create(
            tenant=self.tenant,
            person=self.person_a,
            type="EMAIL",
            value="alice.public@example.com",
            is_primary=True,
            is_public=True,
        )
        self.contact_b = PersonContact.objects.create(
            tenant=self.tenant,
            person=self.person_b,
            type="PHONE",
            value="+4740000000",
        )
        self.contact_other_tenant = PersonContact.objects.create(
            tenant=self.other_tenant,
            person=self.person_other_tenant,
            type="EMAIL",
            value="hidden@example.com",
        )
        self.primary_phone_for_person_a = PersonContact.objects.create(
            tenant=self.tenant,
            person=self.person_a,
            type="PHONE",
            value="+4742222222",
            is_primary=True,
        )

    def tenant_contacts_url(self, tenant_id: int | None = None) -> str:
        return f"/api/tenants/{tenant_id or self.tenant.id}/person-contacts/"

    def test_list_is_scoped_to_tenant(self):
        response = self.client.get(self.tenant_contacts_url())
        self.assertEqual(response.status_code, 200)

        ids = {item["id"] for item in response.json()}
        self.assertIn(self.contact_a.id, ids)
        self.assertIn(self.contact_b.id, ids)
        self.assertNotIn(self.contact_other_tenant.id, ids)

    def test_list_supports_person_query_filter(self):
        response = self.client.get(self.tenant_contacts_url(), {"person": self.person_a.id})
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertEqual(len(payload), 2)
        self.assertTrue(all(item["person"] == self.person_a.id for item in payload))

    def test_create_sets_tenant_from_route(self):
        response = self.client.post(
            self.tenant_contacts_url(),
            {
                "person": self.person_a.id,
                "type": "PHONE",
                "value": "+4741111111",
                "is_primary": False,
                "is_public": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)

        created = PersonContact.objects.get(id=response.json()["id"])
        self.assertEqual(created.tenant_id, self.tenant.id)
        self.assertEqual(created.person_id, self.person_a.id)
        self.assertEqual(created.type, "PHONE")

    def test_update_contact(self):
        response = self.client.patch(
            f"{self.tenant_contacts_url()}{self.contact_b.id}/",
            {"is_primary": True, "is_public": True},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)

        self.contact_b.refresh_from_db()
        self.assertTrue(self.contact_b.is_primary)
        self.assertTrue(self.contact_b.is_public)

    def test_rejects_contact_person_from_other_tenant(self):
        response = self.client.post(
            self.tenant_contacts_url(),
            {
                "person": self.person_other_tenant.id,
                "type": "EMAIL",
                "value": "x@example.com",
                "is_primary": False,
                "is_public": False,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("person", response.json())

    def test_rejects_second_primary_contact_for_same_person_and_type(self):
        response = self.client.post(
            self.tenant_contacts_url(),
            {
                "person": self.person_a.id,
                "type": "PHONE",
                "value": "+4743333333",
                "is_primary": True,
                "is_public": False,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("is_primary", response.json())

    def test_rejects_updating_contact_to_duplicate_primary(self):
        secondary = PersonContact.objects.create(
            tenant=self.tenant,
            person=self.person_a,
            type="PHONE",
            value="+4744444444",
            is_primary=False,
        )
        response = self.client.patch(
            f"{self.tenant_contacts_url()}{secondary.id}/",
            {"is_primary": True},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("is_primary", response.json())

    def test_delete_contact(self):
        response = self.client.delete(f"{self.tenant_contacts_url()}{self.contact_b.id}/")
        self.assertEqual(response.status_code, 403)
        self.assertTrue(PersonContact.objects.filter(id=self.contact_b.id).exists())

    def test_requires_authentication(self):
        unauth_client = APIClient()
        response = unauth_client.get(self.tenant_contacts_url())
        self.assertEqual(response.status_code, 403)


@override_settings(SECURE_SSL_REDIRECT=False)
class PersonSerializerTests(TestCase):
    def test_includes_email_and_phone_fields(self):
        tenant = Tenant.objects.create(name="Tenant", slug="tenant")
        person = Person.objects.create(
            tenant=tenant,
            full_name="Person Example",
            title="Daglig leder",
            email="person@example.com",
            phone="+4798765432",
            municipality="Trondheim",
            website_url="https://example.com",
            instagram_url="https://instagram.com/personexample",
            tiktok_url="https://tiktok.com/@personexample",
            linkedin_url="https://linkedin.com/in/personexample",
            facebook_url="https://facebook.com/personexample",
            youtube_url="https://youtube.com/@personexample",
        )

        data = PersonSerializer(person).data

        self.assertIn("email", data)
        self.assertIn("phone", data)
        self.assertIn("title", data)
        self.assertIn("website_url", data)
        self.assertIn("instagram_url", data)
        self.assertIn("tiktok_url", data)
        self.assertIn("linkedin_url", data)
        self.assertIn("facebook_url", data)
        self.assertIn("youtube_url", data)
        self.assertEqual(data["email"], "person@example.com")
        self.assertEqual(data["title"], "Daglig leder")
        self.assertEqual(data["phone"], "+4798765432")
        self.assertEqual(data["website_url"], "https://example.com")
        self.assertEqual(data["instagram_url"], "https://instagram.com/personexample")
        self.assertEqual(data["tiktok_url"], "https://tiktok.com/@personexample")
        self.assertEqual(data["linkedin_url"], "https://linkedin.com/in/personexample")
        self.assertEqual(data["facebook_url"], "https://facebook.com/personexample")
        self.assertEqual(data["youtube_url"], "https://youtube.com/@personexample")


class TagModelAndApiTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Tag Tenant", slug="tag-tenant")
        self.other_tenant = Tenant.objects.create(name="Other Tag Tenant", slug="other-tag-tenant")
        grant_membership(self.user, self.tenant)
        self.primary_tag = Tag.objects.create(tenant=self.tenant, name="Scenekunst")
        self.other_tag = Tag.objects.create(tenant=self.other_tenant, name="Film")

    def tenant_tags_url(self, tenant_id: int | None = None) -> str:
        return f"/api/tenants/{tenant_id or self.tenant.id}/tags/"

    def test_generates_slug_on_create(self):
        self.assertEqual(self.primary_tag.slug, "scenekunst")

    def test_list_is_scoped_to_tenant(self):
        response = self.client.get(self.tenant_tags_url())
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["name"], "Scenekunst")

    def test_create_sets_tenant_from_route(self):
        response = self.client.post(
            self.tenant_tags_url(),
            {"name": "Musikk"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        created = Tag.objects.get(id=response.json()["id"])
        self.assertEqual(created.tenant_id, self.tenant.id)
        self.assertEqual(created.slug, "musikk")

    def test_rejects_duplicate_name_in_same_tenant(self):
        response = self.client.post(
            self.tenant_tags_url(),
            {"name": "Scenekunst"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_person_serializer_includes_tags(self):
        person = Person.objects.create(tenant=self.tenant, full_name="Tag Person")
        person.tags.add(self.primary_tag)

        data = PersonSerializer(person).data

        self.assertEqual(len(data["tags"]), 1)
        self.assertEqual(data["tags"][0]["name"], "Scenekunst")


class CategoryAndSubcategoryTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.category = Category.objects.create(name="Testkategori")
        self.subcategory = Subcategory.objects.create(category=self.category, name="Testunderkategori")
        self.other_subcategory = Subcategory.objects.create(category=self.category, name="Annen underkategori")
        self.tenant = Tenant.objects.create(name="Category Tenant", slug="category-tenant")

    def test_category_slug_is_generated(self):
        self.assertEqual(self.category.slug, "testkategori")

    def test_subcategory_slug_is_generated(self):
        self.assertEqual(self.subcategory.slug, "testunderkategori")

    def test_seeded_categories_are_available(self):
        self.assertTrue(Category.objects.filter(name="Musikk").exists())
        self.assertTrue(Subcategory.objects.filter(name="Artister & Band").exists())
        self.assertTrue(Subcategory.objects.filter(name="Filmlyd").exists())

    def test_categories_endpoint_requires_authentication(self):
        unauth_client = APIClient()
        response = unauth_client.get("/api/categories/")
        self.assertEqual(response.status_code, 403)

    def test_categories_endpoint_lists_categories(self):
        response = self.client.get("/api/categories/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(any(item["name"] == "Testkategori" for item in payload))

    def test_subcategories_endpoint_can_filter_by_category(self):
        response = self.client.get("/api/subcategories/", {"category": self.category.id})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 2)
        self.assertTrue(all(item["category"]["id"] == self.category.id for item in payload))

    def test_person_serializer_includes_subcategories(self):
        person = Person.objects.create(tenant=self.tenant, full_name="Kategori Person")
        person.subcategories.add(self.subcategory)

        data = PersonSerializer(person).data

        self.assertEqual(len(data["subcategories"]), 1)
        self.assertEqual(data["subcategories"][0]["name"], "Testunderkategori")
        self.assertEqual(data["subcategories"][0]["category"]["name"], "Testkategori")


class OrganizationPreviewRefreshTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Preview Tenant", slug="preview-tenant")
        grant_membership(self.user, self.tenant)
        self.organization = Organization.objects.create(
            tenant=self.tenant,
            name="Preview Org",
            website_url="https://example.com",
        )

    def test_refresh_preview_endpoint_updates_open_graph_fields(self):
        with patch("crm.views.refresh_organization_open_graph") as refresh_mock:
            refresh_mock.side_effect = self._fake_refresh
            response = self.client.post(
                f"/api/tenants/{self.tenant.id}/organizations/{self.organization.id}/refresh-preview/",
                {},
                format="json",
            )

        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        self.assertEqual(payload["og_title"], "Preview Org OG")
        self.assertEqual(payload["og_description"], "Beskrivelse fra Open Graph")
        self.assertEqual(payload["og_image_url"], "https://cdn.example.com/preview.jpg")
        self.assertEqual(payload["auto_thumbnail_url"], "https://cdn.example.com/thumbnail.jpg")
        self.assertEqual(payload["primary_link"], "https://example.com")
        self.assertEqual(payload["primary_link_field"], "website_url")
        refresh_mock.assert_called_once()

    def _fake_refresh(self, organization, force=False):
        organization.og_title = "Preview Org OG"
        organization.og_description = "Beskrivelse fra Open Graph"
        organization.og_image_url = "https://cdn.example.com/preview.jpg"
        organization.auto_thumbnail_url = "https://cdn.example.com/thumbnail.jpg"
        organization.og_last_fetched_at = organization.updated_at
        organization.save(
            update_fields=["og_title", "og_description", "og_image_url", "auto_thumbnail_url", "og_last_fetched_at"]
        )


class TenantScopedCreateTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Scoped Tenant", slug="scoped-tenant")
        grant_membership(self.user, self.tenant)

    def test_can_create_organization_without_tenant_in_payload(self):
        response = self.client.post(
            f"/api/tenants/{self.tenant.id}/organizations/",
            {
                "name": "Ny organisasjon",
                "org_number": "123456789",
                "municipalities": "Oslo",
                "tag_ids": [],
                "category_ids": [],
                "subcategory_ids": [],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.content)
        created = Organization.objects.get(id=response.json()["id"])
        self.assertEqual(created.tenant_id, self.tenant.id)

    def test_can_create_person_without_tenant_in_payload(self):
        response = self.client.post(
            f"/api/tenants/{self.tenant.id}/persons/",
            {
                "full_name": "Ny kontaktperson",
                "title": "Produsent",
                "municipality": "Oslo",
                "tag_ids": [],
                "category_ids": [],
                "subcategory_ids": [],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.content)
        created = Person.objects.get(id=response.json()["id"])
        self.assertEqual(created.tenant_id, self.tenant.id)
        self.assertEqual(created.title, "Produsent")

    def test_can_create_organization_with_category_only(self):
        category = Category.objects.create(name="Kun kategori")
        response = self.client.post(
            f"/api/tenants/{self.tenant.id}/organizations/",
            {
                "name": "Kategori uten underkategori",
                "category_ids": [category.id],
                "subcategory_ids": [],
                "tag_ids": [],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.content)
        created = Organization.objects.get(id=response.json()["id"])
        self.assertEqual(list(created.categories.values_list("name", flat=True)), ["Kun kategori"])
        self.assertEqual(created.subcategories.count(), 0)

    def test_can_create_person_with_category_only(self):
        category = Category.objects.create(name="Kun personkategori")
        response = self.client.post(
            f"/api/tenants/{self.tenant.id}/persons/",
            {
                "full_name": "Kategori-person",
                "category_ids": [category.id],
                "subcategory_ids": [],
                "tag_ids": [],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.content)
        created = Person.objects.get(id=response.json()["id"])
        self.assertEqual(list(created.categories.values_list("name", flat=True)), ["Kun personkategori"])
        self.assertEqual(created.subcategories.count(), 0)


@override_settings(SECURE_SSL_REDIRECT=False)
class PublicActorSiteTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Publik kategori")
        self.subcategory = Subcategory.objects.create(category=self.category, name="Publik underkategori")
        self.tag = Tag.objects.create(tenant=Tenant.objects.create(name="Public Tenant", slug="public-tenant"), name="Etablert")
        self.organization = Organization.objects.create(
            tenant=self.tag.tenant,
            name="Nordlyd",
            org_number="123456789",
            municipalities="Oslo",
            note="Publisert aktør",
            is_published=True,
            website_url="https://example.com",
        )
        self.organization.tags.add(self.tag)
        self.organization.categories.add(self.category)
        self.organization.subcategories.add(self.subcategory)
        self.person = Person.objects.create(
            tenant=self.tag.tenant,
            full_name="Ada Artist",
            email="ada@example.com",
            phone="+4712345678",
            municipality="Oslo",
        )
        self.link = OrganizationPerson.objects.create(
            tenant=self.tag.tenant,
            organization=self.organization,
            person=self.person,
            status="ACTIVE",
            publish_person=True,
        )

        self.hidden_organization = Organization.objects.create(
            tenant=self.tag.tenant,
            name="Skjult aktør",
            org_number="987654321",
            is_published=False,
        )

    def test_public_actor_list_only_shows_published_actors(self):
        response = self.client.get("/public/actors/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nordlyd")
        self.assertNotContains(response, "Skjult aktør")

    def test_public_actor_list_can_filter_by_tag_and_category(self):
        response = self.client.get("/public/actors/", {"tag": self.tag.slug, "category": self.category.slug})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nordlyd")

    def test_public_actor_list_context_uses_expected_category_and_subcategory_order(self):
        extra_category = Category.objects.create(name="Ekstra kategori")
        Subcategory.objects.create(category=extra_category, name="Ekstra underkategori")
        response = self.client.get("/public/actors/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [category["name"] for category in response.context["available_categories"][:6]],
            ["Musikk", "Film", "Kunst & Design", "Scenekunst", "Kreativ teknologi", "Litteratur"],
        )
        self.assertEqual(
            [subcategory["name"] for subcategory in response.context["available_subcategories"][:15]],
            [
                "Artister & Band",
                "Konsertarrangører",
                "Musikere",
                "Musikkbransjen",
                "Produsent",
                "Regi & Manus",
                "Foto/ Lys",
                "Filmlyd",
                "Filmproduksjon",
                "Visuell kunst",
                "Grafisk design",
                "Klesdesign",
                "Teater",
                "Dans",
            ],
        )

    def test_public_actor_list_searches_public_text_fields(self):
        response = self.client.get("/public/actors/", {"q": "Oslo"})
        self.assertContains(response, "Nordlyd")

        response = self.client.get("/public/actors/", {"q": "Publik kategori"})
        self.assertContains(response, "Nordlyd")

        response = self.client.get("/public/actors/", {"q": "Publik underkategori"})
        self.assertContains(response, "Nordlyd")

        response = self.client.get("/public/actors/", {"q": "Etablert"})
        self.assertContains(response, "Nordlyd")

        self.organization.description = "Et sterkt miljø for nordnorsk jazz og samtidsmusikk."
        self.organization.save(update_fields=["description"])
        response = self.client.get("/public/actors/", {"q": "nordnorsk jazz"})
        self.assertContains(response, "Nordlyd")

        response = self.client.get("/public/actors/", {"q": "Ada Artist"})
        self.assertContains(response, "Nordlyd")

    def test_public_actor_list_dedupes_available_tags_by_name(self):
        other_tenant = Tenant.objects.create(name="Annen tenant", slug="annen-tenant")
        duplicate_tag = Tag.objects.create(tenant=other_tenant, name="Etablert", slug="etablert")
        other_org = Organization.objects.create(
            tenant=other_tenant,
            name="Synlig aktør",
            org_number="111222333",
            is_published=True,
        )
        other_org.tags.add(duplicate_tag)

        response = self.client.get("/public/actors/")

        self.assertEqual(response.status_code, 200)
        available_names = [tag.name for tag in response.context["available_tags"]]
        self.assertEqual(available_names.count("Etablert"), 1)

    def test_public_actor_detail_shows_tags_and_subcategories(self):
        response = self.client.get(f"/public/actors/{self.organization.org_number}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Etablert")
        self.assertContains(response, "PUBLIK KATEGORI")
        self.assertContains(response, "Publik underkategori")

    def test_public_actor_detail_falls_back_to_person_email_but_not_phone(self):
        response = self.client.get(f"/public/actors/{self.organization.org_number}/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ada Artist")
        self.assertContains(response, "ada@example.com")
        self.assertNotContains(response, "+4712345678")

    def test_public_actor_templates_ignore_favicon_fallback_urls(self):
        self.organization.og_image_url = fallback_preview_image(self.organization.website_url)
        self.organization.save(update_fields=["og_image_url"])

        list_response = self.client.get("/public/actors/")
        detail_response = self.client.get(f"/public/actors/{self.organization.org_number}/")

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(detail_response.status_code, 200)
        self.assertNotContains(list_response, "google.com/s2/favicons")
        self.assertNotContains(detail_response, "google.com/s2/favicons")

    def test_manual_thumbnail_override_wins_for_public_image(self):
        self.organization.thumbnail_image_url = "https://cdn.example.com/manual-thumb.jpg"
        self.organization.auto_thumbnail_url = "https://cdn.example.com/auto-thumb.jpg"
        self.organization.og_image_url = "https://cdn.example.com/og.jpg"
        self.organization.save(update_fields=["thumbnail_image_url", "auto_thumbnail_url", "og_image_url"])

        response = self.client.get("/public/actors/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "https://cdn.example.com/manual-thumb.jpg")


class ThumbnailSelectionTests(TestCase):
    def test_choose_best_thumbnail_prefers_large_non_logo_candidate(self):
        chosen = choose_best_thumbnail(
            "https://example.com/about",
            [
                ImageCandidate(url="/assets/logo.png", source="img", width=320, height=120, alt="Logo"),
                ImageCandidate(url="/media/portrait.jpg", source="img", width=1200, height=1200, alt="Artist"),
            ],
        )

        self.assertEqual(chosen, "https://example.com/media/portrait.jpg")


class OrganizationPersonViewSetValidationTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Tenant A", slug="tenant-a-links")
        self.other_tenant = Tenant.objects.create(name="Tenant B", slug="tenant-b-links")
        grant_membership(self.user, self.tenant)

        self.organization = Organization.objects.create(tenant=self.tenant, name="Org A")
        self.person = Person.objects.create(tenant=self.tenant, full_name="Person A")

        self.other_organization = Organization.objects.create(
            tenant=self.other_tenant,
            name="Org B",
        )
        self.other_person = Person.objects.create(
            tenant=self.other_tenant,
            full_name="Person B",
        )

    def tenant_links_url(self, tenant_id: int | None = None) -> str:
        return f"/api/tenants/{tenant_id or self.tenant.id}/organization-people/"

    def test_rejects_create_when_person_belongs_to_other_tenant(self):
        response = self.client.post(
            self.tenant_links_url(),
            {
                "organization": self.organization.id,
                "person": self.other_person.id,
                "status": "ACTIVE",
                "publish_person": False,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("person", response.json())

    def test_rejects_create_when_organization_belongs_to_other_tenant(self):
        response = self.client.post(
            self.tenant_links_url(),
            {
                "organization": self.other_organization.id,
                "person": self.person.id,
                "status": "ACTIVE",
                "publish_person": False,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("organization", response.json())

    def test_rejects_update_when_switching_person_to_other_tenant(self):
        link = OrganizationPerson.objects.create(
            tenant=self.tenant,
            organization=self.organization,
            person=self.person,
        )
        response = self.client.patch(
            f"{self.tenant_links_url()}{link.id}/",
            {"person": self.other_person.id},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("person", response.json())
