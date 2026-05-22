import json
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
    InternalTag,
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
from .services.open_graph import ImageCandidate, choose_best_thumbnail, fallback_preview_image, fetch_open_graph
from .serializers import PersonSerializer
import_commit_module = importlib.import_module("crm.services.import.commit")
import_matchers_module = importlib.import_module("crm.services.import.matchers")
import_normalizers_module = importlib.import_module("crm.services.import.normalizers")
import_ai_suggestions_module = importlib.import_module("crm.services.import.ai_suggestions")
import_preview_module = importlib.import_module("crm.services.import.preview")
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
                "import_mode": ImportJob.ImportMode.ORGANIZATIONS_ONLY,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.content)
        created = ImportJob.objects.get(id=response.json()["id"])
        self.assertEqual(created.tenant_id, self.tenant.id)
        self.assertEqual(created.created_by_id, self.user.id)
        self.assertEqual(created.status, ImportJob.Status.DRAFT)

    def test_create_import_job_rejects_combined_mode(self):
        response = self.client.post(
            self.import_jobs_url(),
            {
                "source_type": ImportJob.SourceType.CSV,
                "import_mode": ImportJob.ImportMode.COMBINED,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn("import_mode", response.json())

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

    def test_import_template_config_includes_internal_tag_columns(self):
        organization_columns = build_import_template_config(ImportJob.ImportMode.ORGANIZATIONS_ONLY)["columns"]
        people_columns = build_import_template_config(ImportJob.ImportMode.PEOPLE_ONLY)["columns"]
        combined_columns = build_import_template_config(ImportJob.ImportMode.COMBINED)["columns"]

        self.assertIn("organization_internal_tags", organization_columns)
        self.assertIn("person_internal_tags", people_columns)
        self.assertIn("organization_internal_tags", combined_columns)
        self.assertIn("person_internal_tags", combined_columns)

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

    def test_brreg_lookup_endpoint_returns_candidate_for_org_number(self):
        BrregCandidate = importlib.import_module("crm.services.import.brreg").BrregCandidate

        with patch("crm.views.candidate_for_org_number", return_value=BrregCandidate(
            org_number="934051106",
            name="Nordlyd Ungdomsbedrift",
            municipality="Tromsø",
            postal_place="Tromsø",
            website_url="https://nordlyd.no",
            email="post@nordlyd.no",
            score=0.0,
        )):
            response = self.client.post(
                f"{self.import_jobs_url()}{self.import_job.id}/brreg-lookup/",
                {"org_number": "934 051 106"},
                format="json",
            )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["org_number"], "934051106")
        self.assertEqual(response.json()["municipality"], "Tromsø")

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
            "organization_internal_tags": "prioritet, partner",
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
            "person_internal_tags": "følges opp",
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

    @override_settings(OPENAI_IMPORT_ENABLED=True, OPENAI_API_KEY="test-key")
    def test_preview_marks_ai_as_pending_without_blocking_on_generation(self):
        self._upload_csv()
        pending_payload = {
            "organization_match_candidates": [],
            "person_match_candidates": [],
            "suggested_fields": {},
            "provider": "pending_openai",
            "diagnostic": {
                "primary_provider": "pending_openai",
                "provider_status": "pending_openai",
                "fallback_reason": "awaiting_openai",
                "openai_attempted": False,
                "openai_error": None,
                "useful_suggestion_count": 0,
            },
        }
        with patch.object(import_preview_module, "build_pending_ai_suggestions", return_value=pending_payload):
            response = self.client.post(f"{self.import_jobs_url()}{self.job.id}/preview/", {}, format="json")
        self.assertEqual(response.status_code, 200, response.content)

        self.job.refresh_from_db()
        row = self.job.rows.get()
        self.assertEqual(row.ai_suggestions_json["diagnostic"]["provider_status"], "pending_openai")
        self.assertEqual(self.job.summary_json["ai_generation_status"], "pending")
        self.assertEqual(self.job.summary_json["rows_ai_pending"], 1)

    def test_preview_falls_back_when_pending_ai_builder_errors(self):
        self._upload_csv()
        with patch.object(import_preview_module, "build_pending_ai_suggestions", side_effect=RuntimeError("preview boom")):
            response = self.client.post(f"{self.import_jobs_url()}{self.job.id}/preview/", {}, format="json")
        self.assertEqual(response.status_code, 200, response.content)

        self.job.refresh_from_db()
        row = self.job.rows.get()
        self.assertEqual(row.ai_suggestions_json["diagnostic"]["provider_status"], "fallback_preview_error")
        self.assertEqual(row.ai_suggestions_json["diagnostic"]["openai_error"], "preview boom")
        self.assertEqual(self.job.summary_json["rows_ai_failed"], 1)
        self.assertEqual(self.job.summary_json["ai_generation_status"], "failed")

    @override_settings(OPENAI_IMPORT_ENABLED=True, OPENAI_API_KEY="test-key")
    def test_generate_ai_endpoint_processes_pending_rows_in_batches(self):
        self._upload_csv([self.base_row, self.base_row | {"organization_name": "Nordlyd 2", "organization_org_number": "987654321"}])
        pending_payload = {
            "organization_match_candidates": [],
            "person_match_candidates": [],
            "suggested_fields": {},
            "provider": "pending_openai",
            "diagnostic": {
                "primary_provider": "pending_openai",
                "provider_status": "pending_openai",
                "fallback_reason": "awaiting_openai",
                "openai_attempted": False,
                "openai_error": None,
                "useful_suggestion_count": 0,
            },
        }
        with patch.object(import_preview_module, "build_pending_ai_suggestions", return_value=pending_payload):
            self.client.post(f"{self.import_jobs_url()}{self.job.id}/preview/", {}, format="json")

        fake_suggestion = {
            "organization_match_candidates": [],
            "person_match_candidates": [],
            "suggested_fields": {
                "organization_website_url": {
                    "value": "https://nordlyd.no",
                    "confidence": 0.81,
                    "source": "ai_enrichment",
                    "requires_review": True,
                }
            },
            "provider": "openai",
            "diagnostic": {
                "primary_provider": "openai",
                "provider_status": "openai",
                "fallback_reason": None,
                "openai_attempted": True,
                "openai_error": None,
                "useful_suggestion_count": 1,
            },
        }

        with patch.object(import_preview_module, "generate_ai_suggestions", return_value=fake_suggestion), patch.object(
            import_preview_module,
            "openai_is_ready",
            return_value=True,
        ):
            response = self.client.post(
                f"{self.import_jobs_url()}{self.job.id}/generate-ai/",
                {"batch_size": 1},
                format="json",
            )
        self.assertEqual(response.status_code, 200, response.content)
        self.job.refresh_from_db()
        self.assertEqual(self.job.summary_json["rows_ai_completed"], 1)
        self.assertEqual(self.job.summary_json["rows_ai_pending"], 1)
        self.assertEqual(self.job.summary_json["ai_generation_status"], "running")

    @override_settings(OPENAI_IMPORT_ENABLED=True, OPENAI_API_KEY="test-key")
    def test_generate_ai_endpoint_falls_back_when_row_generation_errors(self):
        self._upload_csv()
        pending_payload = {
            "organization_match_candidates": [],
            "person_match_candidates": [],
            "suggested_fields": {},
            "provider": "pending_openai",
            "diagnostic": {
                "primary_provider": "pending_openai",
                "provider_status": "pending_openai",
                "fallback_reason": "awaiting_openai",
                "openai_attempted": False,
                "openai_error": None,
                "useful_suggestion_count": 0,
            },
        }
        with patch.object(import_preview_module, "build_pending_ai_suggestions", return_value=pending_payload):
            self.client.post(f"{self.import_jobs_url()}{self.job.id}/preview/", {}, format="json")

        with patch.object(import_preview_module, "generate_ai_suggestions", side_effect=RuntimeError("openai boom")), patch.object(
            import_preview_module,
            "openai_is_ready",
            return_value=True,
        ):
            response = self.client.post(
                f"{self.import_jobs_url()}{self.job.id}/generate-ai/",
                {"batch_size": 1},
                format="json",
            )
        self.assertEqual(response.status_code, 200, response.content)
        self.job.refresh_from_db()
        row = self.job.rows.get()
        self.assertEqual(row.ai_suggestions_json["diagnostic"]["provider_status"], "fallback_openai_error")
        self.assertEqual(row.ai_suggestions_json["diagnostic"]["openai_error"], "openai boom")
        self.assertEqual(self.job.summary_json["rows_ai_failed"], 1)
        self.assertEqual(self.job.summary_json["rows_ai_pending"], 0)
        self.assertEqual(self.job.summary_json["ai_generation_status"], "failed")

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

    def test_person_import_suggests_existing_actor_from_contact_domain(self):
        existing = Organization.objects.create(
            tenant=self.tenant,
            name="Nordlyd AS",
            website_url="https://nordlyd.no",
        )
        match = match_row_entities(
            self.tenant,
            normalize_import_row(
                self.base_row
                | {
                    "organization_name": "",
                    "organization_org_number": "",
                    "organization_email": "",
                    "organization_website_url": "",
                    "person_email": "ada@nordlyd.no",
                }
            ),
        )
        self.assertEqual(match["organization"]["status"], "FUZZY")
        self.assertEqual(match["organization"]["rule"], "CONTACT_DOMAIN")
        self.assertEqual(match["organization"]["candidates"][0]["id"], existing.id)

    def test_organizations_only_preview_requires_review_for_exact_existing_actor(self):
        existing = Organization.objects.create(
            tenant=self.tenant,
            name="Nordlyd AS",
            org_number="123456789",
            municipalities="Oslo",
            website_url="https://nordlyd.no",
        )
        job = ImportJob.objects.create(
            tenant=self.tenant,
            created_by=self.user,
            source_type=ImportJob.SourceType.CSV,
            import_mode=ImportJob.ImportMode.ORGANIZATIONS_ONLY,
            status=ImportJob.Status.UPLOADED,
        )
        row = {
            key: value
            for key, value in self.base_row.items()
            if key.startswith("organization_")
        }
        row["organization_internal_tags"] = ""
        row["organization_tags"] = ""
        upload = SimpleUploadedFile(
            "import.csv",
            ",".join(row.keys()).encode("utf-8") + b"\n" + ",".join(str(value) for value in row.values()).encode("utf-8"),
            content_type="text/csv",
        )
        job.file = upload
        job.filename = "import.csv"
        job.save(update_fields=["file", "filename", "updated_at"])

        response = self.client.post(f"{self.import_jobs_url()}{job.id}/preview/", {}, format="json")
        self.assertEqual(response.status_code, 200, response.content)

        preview_row = job.rows.get()
        self.assertEqual(preview_row.row_status, ImportRow.RowStatus.REVIEW_REQUIRED)
        self.assertEqual(preview_row.proposed_action, ImportRow.ProposedAction.UPDATE)
        self.assertEqual(preview_row.match_result_json["organization"]["exact_id"], existing.id)
        self.assertEqual(
            preview_row.ai_suggestions_json["organization_match_candidates"][0]["id"],
            existing.id,
        )

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
        self.assertEqual(set(organization.categories.values_list("name", flat=True)), {"Musikk"})
        self.assertEqual(set(organization.subcategories.values_list("name", flat=True)), {"Artister & Band"})
        self.assertEqual(person.title, "Manager")
        self.assertEqual(set(person.categories.values_list("name", flat=True)), {"Musikk"})
        self.assertEqual(set(person.subcategories.values_list("name", flat=True)), {"Artister & Band"})
        self.assertEqual(person.contacts.filter(type="EMAIL", is_primary=True).count(), 1)
        self.assertEqual(person.contacts.filter(type="PHONE", is_primary=True).count(), 1)
        self.assertTrue(person.contacts.filter(value="ada.booking@example.com", is_public=False).exists())
        self.assertTrue(Tag.objects.filter(tenant=self.tenant, name="jazz").exists())
        self.assertTrue(InternalTag.objects.filter(tenant=self.tenant, name="prioritet").exists())
        self.assertEqual(set(organization.internal_tags.values_list("name", flat=True)), {"prioritet", "partner"})
        self.assertEqual(set(person.internal_tags.values_list("name", flat=True)), {"følges opp"})
        self.assertGreater(self.job.commit_logs.count(), 0)
        refresh_mock.assert_called_once()

    @patch("crm.services.import.commit.refresh_organization_open_graph")
    def test_commit_can_clear_organization_internal_tags_via_review(self, refresh_mock):
        row = self.base_row | {"organization_internal_tags": "arrangør Nordland"}
        self._upload_csv([row])
        self.client.post(f"{self.import_jobs_url()}{self.job.id}/preview/", {}, format="json")
        preview_row = self.job.rows.get()

        decisions_response = self.client.post(
            f"{self.import_jobs_url()}{self.job.id}/decisions/",
            {
                "rows": [
                    {
                        "row_id": preview_row.id,
                        "decisions": [
                            {
                                "decision_type": "ACCEPT_AI_SUGGESTION",
                                "payload_json": {"suggestion_key": "organization_internal_tags", "value": []},
                            }
                        ],
                    }
                ]
            },
            format="json",
        )
        self.assertEqual(decisions_response.status_code, 200, decisions_response.content)

        commit_response = self.client.post(
            f"{self.import_jobs_url()}{self.job.id}/commit/",
            {"skip_unresolved": False},
            format="json",
        )
        self.assertEqual(commit_response.status_code, 200, commit_response.content)

        organization = Organization.objects.get(tenant=self.tenant, org_number="123456789")
        self.assertEqual(list(organization.internal_tags.values_list("name", flat=True)), [])
        refresh_mock.assert_called_once()

    @patch("crm.services.import.commit.refresh_organization_open_graph")
    def test_manual_review_changes_persist_through_commit(self, refresh_mock):
        self.job.import_mode = ImportJob.ImportMode.ORGANIZATIONS_ONLY
        self.job.save(update_fields=["import_mode", "updated_at"])
        row = {key: value for key, value in self.base_row.items() if key.startswith("organization_")}
        row["organization_email"] = ""
        row["organization_website_url"] = ""
        row["organization_description"] = ""
        row["organization_is_published"] = ""
        row["organization_internal_tags"] = ""
        self._upload_csv([row])

        preview_response = self.client.post(f"{self.import_jobs_url()}{self.job.id}/preview/", {}, format="json")
        self.assertEqual(preview_response.status_code, 200, preview_response.content)
        preview_row = self.job.rows.get()

        scenekunst = Category.objects.get(name="Scenekunst")
        teater = Subcategory.objects.get(name="Teater")
        decisions_response = self.client.post(
            f"{self.import_jobs_url()}{self.job.id}/decisions/",
            {
                "rows": [
                    {
                        "row_id": preview_row.id,
                        "decisions": [
                            {"decision_type": "MAP_CATEGORY", "payload_json": {"category_id": scenekunst.id}},
                            {"decision_type": "MAP_SUBCATEGORY", "payload_json": {"subcategory_id": teater.id}},
                            {
                                "decision_type": "ACCEPT_AI_SUGGESTION",
                                "payload_json": {
                                    "suggestion_key": "organization_email",
                                    "value": "kontakt@sortlandjazz.no",
                                    "manual_override": True,
                                },
                            },
                            {
                                "decision_type": "ACCEPT_AI_SUGGESTION",
                                "payload_json": {
                                    "suggestion_key": "organization_website_url",
                                    "value": "https://sortlandjazz.no",
                                    "manual_override": True,
                                },
                            },
                            {
                                "decision_type": "ACCEPT_AI_SUGGESTION",
                                "payload_json": {
                                    "suggestion_key": "organization_description",
                                    "value": "Sortland Jazz og viseklubb arrangerer konserter i Sortland.",
                                    "manual_override": True,
                                },
                            },
                            {
                                "decision_type": "ACCEPT_AI_SUGGESTION",
                                "payload_json": {
                                    "suggestion_key": "organization_internal_tags",
                                    "value": ["arrangor", "nordland"],
                                    "manual_override": True,
                                },
                            },
                            {
                                "decision_type": "ACCEPT_AI_SUGGESTION",
                                "payload_json": {
                                    "suggestion_key": "organization_is_published",
                                    "value": True,
                                    "manual_override": True,
                                },
                            },
                        ],
                    }
                ]
            },
            format="json",
        )
        self.assertEqual(decisions_response.status_code, 200, decisions_response.content)

        commit_response = self.client.post(f"{self.import_jobs_url()}{self.job.id}/commit/", {"skip_unresolved": False}, format="json")
        self.assertEqual(commit_response.status_code, 200, commit_response.content)

        organization = Organization.objects.get(tenant=self.tenant, org_number="123456789")
        self.assertEqual(organization.email, "kontakt@sortlandjazz.no")
        self.assertEqual(organization.website_url, "https://sortlandjazz.no")
        self.assertEqual(organization.description, "Sortland Jazz og viseklubb arrangerer konserter i Sortland.")
        self.assertTrue(organization.is_published)
        self.assertEqual(set(organization.categories.values_list("name", flat=True)), {"Scenekunst"})
        self.assertEqual(set(organization.subcategories.values_list("name", flat=True)), {"Teater"})
        self.assertEqual(set(organization.internal_tags.values_list("name", flat=True)), {"arrangor", "nordland"})
        refresh_mock.assert_called_once()

    @patch("crm.services.import.commit.refresh_organization_open_graph")
    def test_manual_review_can_clear_imported_subcategories(self, refresh_mock):
        self.job.import_mode = ImportJob.ImportMode.ORGANIZATIONS_ONLY
        self.job.save(update_fields=["import_mode", "updated_at"])
        row = {key: value for key, value in self.base_row.items() if key.startswith("organization_")}
        row["organization_subcategories"] = "Artister & Band"
        self._upload_csv([row])

        preview_response = self.client.post(f"{self.import_jobs_url()}{self.job.id}/preview/", {}, format="json")
        self.assertEqual(preview_response.status_code, 200, preview_response.content)
        preview_row = self.job.rows.get()

        decisions_response = self.client.post(
            f"{self.import_jobs_url()}{self.job.id}/decisions/",
            {
                "rows": [
                    {
                        "row_id": preview_row.id,
                        "decisions": [
                            {
                                "decision_type": "ACCEPT_AI_SUGGESTION",
                                "payload_json": {
                                    "suggestion_key": "suggested_subcategories",
                                    "value": [],
                                    "manual_override": True,
                                },
                            },
                        ],
                    }
                ]
            },
            format="json",
        )
        self.assertEqual(decisions_response.status_code, 200, decisions_response.content)

        commit_response = self.client.post(f"{self.import_jobs_url()}{self.job.id}/commit/", {"skip_unresolved": False}, format="json")
        self.assertEqual(commit_response.status_code, 200, commit_response.content)

        organization = Organization.objects.get(tenant=self.tenant, org_number="123456789")
        self.assertEqual(organization.subcategories.count(), 0)
        refresh_mock.assert_called_once()

    @patch("crm.services.import.commit.refresh_organization_open_graph")
    def test_organizations_only_commit_preserves_exact_subcategories(self, refresh_mock):
        job = ImportJob.objects.create(
            tenant=self.tenant,
            created_by=self.user,
            source_type=ImportJob.SourceType.CSV,
            import_mode=ImportJob.ImportMode.ORGANIZATIONS_ONLY,
            status=ImportJob.Status.UPLOADED,
        )
        row = {
            key: value
            for key, value in self.base_row.items()
            if key.startswith("organization_")
        }
        row["organization_internal_tags"] = ""
        row["organization_tags"] = ""
        upload = SimpleUploadedFile("import.csv", ",".join(row.keys()).encode("utf-8") + b"\n" + ",".join(str(value) for value in row.values()).encode("utf-8"), content_type="text/csv")
        job.file = upload
        job.filename = "import.csv"
        job.save(update_fields=["file", "filename", "updated_at"])

        preview_response = self.client.post(f"{self.import_jobs_url()}{job.id}/preview/", {}, format="json")
        self.assertEqual(preview_response.status_code, 200, preview_response.content)

        commit_response = self.client.post(
            f"{self.import_jobs_url()}{job.id}/commit/",
            {"skip_unresolved": False},
            format="json",
        )
        self.assertEqual(commit_response.status_code, 200, commit_response.content)

        organization = Organization.objects.get(tenant=self.tenant, org_number="123456789")
        self.assertEqual(set(organization.subcategories.values_list("name", flat=True)), {"Artister & Band"})
        refresh_mock.assert_called_once()

    @patch("crm.services.import.commit.refresh_organization_open_graph")
    def test_organizations_only_commit_accepts_subcategory_alias(self, refresh_mock):
        job = ImportJob.objects.create(
            tenant=self.tenant,
            created_by=self.user,
            source_type=ImportJob.SourceType.CSV,
            import_mode=ImportJob.ImportMode.ORGANIZATIONS_ONLY,
            status=ImportJob.Status.UPLOADED,
        )
        row = {
            key: value
            for key, value in self.base_row.items()
            if key.startswith("organization_")
        }
        row["organization_subcategories"] = "Artister og band"
        row["organization_internal_tags"] = ""
        row["organization_tags"] = ""
        upload = SimpleUploadedFile("import.csv", ",".join(row.keys()).encode("utf-8") + b"\n" + ",".join(str(value) for value in row.values()).encode("utf-8"), content_type="text/csv")
        job.file = upload
        job.filename = "import.csv"
        job.save(update_fields=["file", "filename", "updated_at"])

        preview_response = self.client.post(f"{self.import_jobs_url()}{job.id}/preview/", {}, format="json")
        self.assertEqual(preview_response.status_code, 200, preview_response.content)

        commit_response = self.client.post(
            f"{self.import_jobs_url()}{job.id}/commit/",
            {"skip_unresolved": False},
            format="json",
        )
        self.assertEqual(commit_response.status_code, 200, commit_response.content)

        organization = Organization.objects.get(tenant=self.tenant, org_number="123456789")
        self.assertEqual(set(organization.subcategories.values_list("name", flat=True)), {"Artister & Band"})
        refresh_mock.assert_called_once()

    @patch("crm.services.import.commit.refresh_organization_open_graph")
    def test_commit_preserves_existing_subcategories_when_import_row_has_none(self, refresh_mock):
        existing = Organization.objects.create(
            tenant=self.tenant,
            name="Nordlyd AS",
            org_number="123456789",
            website_url="https://nordlyd.no",
        )
        existing.categories.set([self.music])
        existing.subcategories.set([self.band])

        row = self.base_row | {
            "organization_categories": "",
            "organization_subcategories": "",
        }
        self._upload_csv([row])
        preview_response = self.client.post(f"{self.import_jobs_url()}{self.job.id}/preview/", {}, format="json")
        self.assertEqual(preview_response.status_code, 200, preview_response.content)

        commit_response = self.client.post(
            f"{self.import_jobs_url()}{self.job.id}/commit/",
            {"skip_unresolved": False},
            format="json",
        )
        self.assertEqual(commit_response.status_code, 200, commit_response.content)

        existing.refresh_from_db()
        self.assertEqual(set(existing.subcategories.values_list("name", flat=True)), {"Artister & Band"})
        self.assertEqual(set(existing.categories.values_list("name", flat=True)), {"Musikk"})
        refresh_mock.assert_called_once()

    @patch("crm.services.import.commit.refresh_organization_open_graph")
    def test_commit_preserves_existing_subcategories_when_review_row_has_unknown_subcategory(self, refresh_mock):
        existing = Organization.objects.create(
            tenant=self.tenant,
            name="Nordlyd AS",
            org_number="123456789",
            website_url="https://nordlyd.no",
        )
        existing.categories.set([self.music])
        existing.subcategories.set([self.band])

        row = self.base_row | {
            "organization_subcategories": "Ukjent underkategori",
        }
        self._upload_csv([row])
        preview_response = self.client.post(f"{self.import_jobs_url()}{self.job.id}/preview/", {}, format="json")
        self.assertEqual(preview_response.status_code, 200, preview_response.content)

        preview_row = self.job.rows.get()
        self.assertEqual(preview_row.row_status, ImportRow.RowStatus.REVIEW_REQUIRED)

        decisions_response = self.client.post(
            f"{self.import_jobs_url()}{self.job.id}/decisions/",
            {"rows": [{"row_id": preview_row.id, "decisions": []}]},
            format="json",
        )
        self.assertEqual(decisions_response.status_code, 200, decisions_response.content)

        commit_response = self.client.post(
            f"{self.import_jobs_url()}{self.job.id}/commit/",
            {"skip_unresolved": False},
            format="json",
        )
        self.assertEqual(commit_response.status_code, 200, commit_response.content)

        existing.refresh_from_db()
        self.assertEqual(set(existing.subcategories.values_list("name", flat=True)), {"Artister & Band"})
        refresh_mock.assert_called_once()

    @patch("crm.services.import.commit.refresh_organization_open_graph")
    def test_commit_uses_mapped_category_instead_of_original_import_category(self, refresh_mock):
        scenekunst = Category.objects.get(name="Scenekunst")

        row = self.base_row | {
            "organization_categories": "Musikk",
            "organization_subcategories": "",
        }
        self._upload_csv([row])
        preview_response = self.client.post(f"{self.import_jobs_url()}{self.job.id}/preview/", {}, format="json")
        self.assertEqual(preview_response.status_code, 200, preview_response.content)

        preview_row = self.job.rows.get()
        decisions_response = self.client.post(
            f"{self.import_jobs_url()}{self.job.id}/decisions/",
            {
                "rows": [
                    {
                        "row_id": preview_row.id,
                        "decisions": [
                            {
                                "decision_type": "MAP_CATEGORY",
                                "payload_json": {"category_id": scenekunst.id},
                            }
                        ],
                    }
                ]
            },
            format="json",
        )
        self.assertEqual(decisions_response.status_code, 200, decisions_response.content)

        commit_response = self.client.post(
            f"{self.import_jobs_url()}{self.job.id}/commit/",
            {"skip_unresolved": False},
            format="json",
        )
        self.assertEqual(commit_response.status_code, 200, commit_response.content)

        organization = Organization.objects.get(tenant=self.tenant, org_number="123456789")
        self.assertEqual(set(organization.categories.values_list("name", flat=True)), {"Scenekunst"})
        refresh_mock.assert_called_once()

    @patch("crm.services.import.commit.refresh_organization_open_graph")
    def test_use_existing_organization_preserves_existing_committed_data(self, refresh_mock):
        existing = Organization.objects.create(
            tenant=self.tenant,
            name="Smeltedigelen musikkfestival",
            org_number="999888777",
            email="behold@festival.no",
            municipalities="Bodø",
            website_url="https://festival.no",
            description="Behold denne teksten",
        )
        existing.categories.set([self.music])
        existing.subcategories.set([self.band])
        existing.internal_tags.add(InternalTag.objects.create(tenant=self.tenant, name="godkjent"))

        row = self.base_row | {
            "organization_name": "Smeltedigelen musikkfestival",
            "organization_org_number": "",
            "organization_email": "overskriv@festival.no",
            "organization_municipalities": "Oslo",
            "organization_website_url": "https://feil.no",
            "organization_description": "Ny dårlig tekst",
            "organization_categories": "Scenekunst",
            "organization_subcategories": "Teater",
            "organization_internal_tags": "arrangør Nordland",
        }
        self._upload_csv([row])
        preview_response = self.client.post(f"{self.import_jobs_url()}{self.job.id}/preview/", {}, format="json")
        self.assertEqual(preview_response.status_code, 200, preview_response.content)

        preview_row = self.job.rows.get()
        decisions_response = self.client.post(
            f"{self.import_jobs_url()}{self.job.id}/decisions/",
            {
                "rows": [
                    {
                        "row_id": preview_row.id,
                        "decisions": [
                            {
                                "decision_type": "USE_EXISTING_ORGANIZATION",
                                "payload_json": {"organization_id": existing.id},
                            }
                        ],
                    }
                ]
            },
            format="json",
        )
        self.assertEqual(decisions_response.status_code, 200, decisions_response.content)

        commit_response = self.client.post(
            f"{self.import_jobs_url()}{self.job.id}/commit/",
            {"skip_unresolved": False},
            format="json",
        )
        self.assertEqual(commit_response.status_code, 200, commit_response.content)

        existing.refresh_from_db()
        self.assertEqual(existing.email, "behold@festival.no")
        self.assertEqual(existing.municipalities, "Bodø")
        self.assertEqual(existing.website_url, "https://festival.no")
        self.assertEqual(existing.description, "Behold denne teksten")
        self.assertEqual(set(existing.categories.values_list("name", flat=True)), {"Musikk"})
        self.assertEqual(set(existing.subcategories.values_list("name", flat=True)), {"Artister & Band"})
        self.assertEqual(set(existing.internal_tags.values_list("name", flat=True)), {"godkjent"})
        refresh_mock.assert_not_called()

    @patch("crm.services.import.commit.refresh_organization_open_graph")
    def test_commit_normalizes_website_urls_without_scheme(self, refresh_mock):
        row = self.base_row | {
            "organization_org_number": "987654321",
            "organization_website_url": "nordlyd.no",
        }
        self._upload_csv([row])
        preview_response = self.client.post(f"{self.import_jobs_url()}{self.job.id}/preview/", {}, format="json")
        self.assertEqual(preview_response.status_code, 200, preview_response.content)

        commit_response = self.client.post(
            f"{self.import_jobs_url()}{self.job.id}/commit/",
            {"skip_unresolved": False},
            format="json",
        )
        self.assertEqual(commit_response.status_code, 200, commit_response.content)

        organization = Organization.objects.get(tenant=self.tenant, org_number="987654321")
        self.assertEqual(organization.website_url, "https://nordlyd.no")
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
        self.assertIn("diagnostic", row.ai_suggestions_json)
        self.assertEqual(row.normalized_payload_json["organization"]["website_url"], "")

    @override_settings(OPENAI_IMPORT_ENABLED=False)
    def test_generate_ai_suggestions_marks_fallback_when_openai_disabled(self):
        suggestions = generate_ai_suggestions(self.tenant, normalize_import_row(self.base_row), {"organization": {}, "person": {}})
        self.assertEqual(suggestions["provider"], "heuristic_fallback")
        self.assertEqual(suggestions["diagnostic"]["provider_status"], "fallback_openai_disabled")
        self.assertEqual(suggestions["diagnostic"]["fallback_reason"], "openai_disabled")

    @override_settings(
        OPENAI_IMPORT_ENABLED=True,
        OPENAI_API_KEY="test-key",
        OPENAI_IMPORT_MODEL="gpt-5.4",
        OPENAI_IMPORT_TIMEOUT=5,
    )
    def test_generate_ai_suggestions_marks_fallback_reason_when_openai_errors(self):
        class FakeResponses:
            def create(self, **kwargs):
                raise RuntimeError("boom")

        class FakeOpenAI:
            def __init__(self, api_key, timeout):
                self.responses = FakeResponses()

        with patch.object(import_ai_suggestions_module, "OpenAI", FakeOpenAI):
            suggestions = generate_ai_suggestions(
                self.tenant,
                normalize_import_row(
                    self.base_row
                    | {
                        "organization_municipalities": "",
                        "organization_website_url": "",
                        "organization_description": "",
                        "organization_categories": "",
                        "organization_subcategories": "",
                    }
                ),
                {"organization": {}, "person": {}},
            )

        self.assertEqual(suggestions["provider"], "heuristic_fallback")
        self.assertEqual(suggestions["diagnostic"]["provider_status"], "fallback_openai_error")
        self.assertEqual(suggestions["diagnostic"]["openai_error"], "boom")

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
                '{"suggested_fields":{"organization_municipalities":{"value":"Oslo","confidence":0.84,"source":"ai_enrichment","requires_review":true},'
                '"organization_website_url":{"value":"https://nordlyd.no","confidence":0.81,"source":"ai_enrichment","requires_review":true},'
                '"organization_instagram_url":{"value":"https://instagram.com/nordlyd","confidence":0.73,"source":"ai_enrichment","requires_review":true},'
                '"suggested_categories":{"value":["Musikk"],"confidence":0.91,"source":"ai_enrichment","requires_review":true},'
                '"suggested_subcategories":{"value":["Artister & Band"],"confidence":0.79,"source":"ai_enrichment","requires_review":true},'
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
                normalize_import_row(
                    self.base_row
                    | {
                        "organization_municipalities": "",
                        "organization_website_url": "",
                        "organization_description": "",
                        "organization_categories": "",
                        "organization_subcategories": "",
                        "organization_tags": "",
                        "person_categories": "",
                        "person_subcategories": "",
                        "person_tags": "",
                    }
                ),
                {"organization": {}, "person": {}},
            )

        self.assertEqual(suggestions["provider"], "openai")
        self.assertEqual(suggestions["organization_match_candidates"], [])
        self.assertEqual(suggestions["suggested_fields"]["organization_municipalities"]["value"], "Oslo")
        self.assertEqual(
            suggestions["suggested_fields"]["organization_website_url"]["value"],
            "https://nordlyd.no",
        )
        self.assertEqual(
            suggestions["suggested_fields"]["organization_instagram_url"]["value"],
            "https://instagram.com/nordlyd",
        )
        self.assertEqual(suggestions["suggested_fields"]["suggested_categories"]["value"], ["Musikk"])
        self.assertEqual(suggestions["suggested_fields"]["suggested_subcategories"]["value"], ["Artister & Band"])
        self.assertEqual(suggestions["diagnostic"]["provider_status"], "openai")
        self.assertNotIn("organization_is_published", suggestions["suggested_fields"])

    @override_settings(
        OPENAI_IMPORT_ENABLED=True,
        OPENAI_API_KEY="test-key",
        OPENAI_IMPORT_MODEL="gpt-5.4",
        OPENAI_IMPORT_TIMEOUT=5,
    )
    def test_generate_ai_suggestions_reuses_enrichment_context_for_person_imports(self):
        SearchSignals = importlib.import_module("crm.services.import.search_enrichment").SearchSignals

        class FakeResponse:
            output_text = '{"suggested_fields":{},"provider":"openai"}'

        class FakeResponses:
            def create(self, **kwargs):
                return FakeResponse()

        class FakeOpenAI:
            def __init__(self, api_key, timeout):
                self.responses = FakeResponses()

        with patch.object(import_ai_suggestions_module, "OpenAI", FakeOpenAI), patch.object(
            import_ai_suggestions_module,
            "search_organization_signals",
            return_value=SearchSignals(
                website_url="https://nordlyd.no",
                emails=[],
                socials={},
                text_snippets=[],
                org_numbers=[],
                website_candidates=[],
                social_candidates={},
                municipality_candidates=[],
                confirmed_signals={},
            ),
        ) as organization_search_mock, patch.object(
            import_ai_suggestions_module,
            "search_person_signals",
            return_value=SearchSignals(
                website_url="https://adastorm.no",
                emails=["ada@adastorm.no"],
                socials={"person_instagram_url": "https://instagram.com/adastorm"},
                text_snippets=["Ada Storm er musiker i Bodø."],
                website_candidates=[],
                social_candidates={},
                municipality_candidates=[{"value": "Bodø", "score": 0.8, "source": "search"}],
                confirmed_signals={},
            ),
        ) as person_search_mock, patch.object(
            import_ai_suggestions_module,
            "_extract_contact_signals_from_website",
            return_value={"emails": [], "phones": [], "socials": {}, "text_snippet": "", "final_url": ""},
        ) as website_signal_mock:
            generate_ai_suggestions(
                self.tenant,
                normalize_import_row(
                    self.base_row
                    | {
                        "organization_name": "",
                        "organization_org_number": "",
                        "organization_email": "",
                        "organization_website_url": "",
                        "person_full_name": "Ada Storm",
                        "person_email": "",
                        "person_website_url": "",
                        "person_instagram_url": "",
                        "person_municipality": "",
                    }
                ),
                {"organization": {}, "person": {}},
            )

        self.assertEqual(organization_search_mock.call_count, 1)
        self.assertEqual(person_search_mock.call_count, 1)
        self.assertEqual(website_signal_mock.call_count, 1)

    @override_settings(
        OPENAI_IMPORT_ENABLED=True,
        OPENAI_API_KEY="test-key",
        OPENAI_IMPORT_MODEL="gpt-5.4",
        OPENAI_IMPORT_TIMEOUT=5,
        OPENAI_IMPORT_WEB_SEARCH_ENABLED=True,
        OPENAI_IMPORT_WEB_SEARCH_MODEL="gpt-5.4",
        OPENAI_IMPORT_WEB_SEARCH_TIMEOUT=5,
    )
    def test_generate_ai_suggestions_can_use_openai_web_search_for_weak_person_signals(self):
        SearchSignals = importlib.import_module("crm.services.import.search_enrichment").SearchSignals

        class FakeResponses:
            def __init__(self):
                self.calls = []

            def create(self, **kwargs):
                self.calls.append(kwargs)
                if kwargs.get("tools"):
                    return type(
                        "FakeWebSearchResponse",
                        (),
                        {
                            "output_text": (
                                '{"suggested_fields":{"person_instagram_url":{"value":"https://instagram.com/adastorm","confidence":0.84,"source":"openai_web_search","requires_review":true}},'
                                '"provider":"openai_web_search"}'
                            )
                        },
                    )()
                return type(
                    "FakeOpenAIResponse",
                    (),
                    {"output_text": '{"suggested_fields":{},"provider":"openai"}'},
                )()

        fake_responses = FakeResponses()

        class FakeOpenAI:
            def __init__(self, api_key, timeout):
                self.responses = fake_responses

        with patch.object(import_ai_suggestions_module, "OpenAI", FakeOpenAI), patch.object(
            import_ai_suggestions_module,
            "search_organization_signals",
            return_value=SearchSignals(
                website_url="https://nordlyd.no",
                emails=[],
                socials={},
                text_snippets=[],
                org_numbers=[],
                website_candidates=[],
                social_candidates={},
                municipality_candidates=[],
                confirmed_signals={},
            ),
        ), patch.object(
            import_ai_suggestions_module,
            "search_person_signals",
            return_value=SearchSignals(
                website_url=None,
                emails=[],
                socials={},
                text_snippets=[],
                website_candidates=[],
                social_candidates={},
                municipality_candidates=[],
                confirmed_signals={},
            ),
        ), patch.object(
            import_ai_suggestions_module,
            "_extract_contact_signals_from_website",
            return_value={"emails": [], "phones": [], "socials": {}, "text_snippet": "", "final_url": ""},
        ):
            suggestions = generate_ai_suggestions(
                self.tenant,
                normalize_import_row(
                    self.base_row
                    | {
                        "organization_name": "Nordlyd AS",
                        "organization_org_number": "",
                        "organization_email": "",
                        "organization_website_url": "",
                        "person_full_name": "Ada Storm",
                        "person_email": "",
                        "person_website_url": "",
                        "person_instagram_url": "",
                        "person_facebook_url": "",
                        "person_linkedin_url": "",
                        "person_youtube_url": "",
                        "person_tiktok_url": "",
                        "person_municipality": "",
                    }
                ),
                {"organization": {}, "person": {}},
            )

        self.assertEqual(suggestions["suggested_fields"]["person_instagram_url"]["value"], "https://instagram.com/adastorm")
        self.assertEqual(suggestions["diagnostic"]["provider_status"], "openai_web_search")
        self.assertEqual(len(fake_responses.calls), 2)
        self.assertTrue(fake_responses.calls[1].get("tools"))
        web_search_payload = json.loads(fake_responses.calls[1]["input"])
        self.assertEqual(web_search_payload["rules"]["social_platform_scope"], ["instagram", "facebook", "tiktok"])
        self.assertEqual(web_search_payload["rules"]["skip_platforms"], ["linkedin", "youtube"])
        self.assertNotIn("person_linkedin_url", web_search_payload["rules"]["allowed_fields"])
        self.assertNotIn("person_youtube_url", web_search_payload["rules"]["allowed_fields"])

    @override_settings(
        OPENAI_IMPORT_ENABLED=True,
        OPENAI_API_KEY="test-key",
        OPENAI_IMPORT_MODEL="gpt-5.4",
        OPENAI_IMPORT_TIMEOUT=5,
    )
    def test_generate_ai_suggestions_discards_invalid_taxonomy_and_non_norwegian_description(self):
        class FakeResponse:
            output_text = (
                '{"suggested_fields":{"suggested_categories":{"value":["Musikk"],"confidence":0.9,"source":"ai_enrichment","requires_review":true},'
                '"suggested_subcategories":{"value":["Interiørarkitektur"],"confidence":0.7,"source":"ai_enrichment","requires_review":true}},'
                '"provider":"openai"}'
            )

        class FakeResponses:
            def create(self, **kwargs):
                return FakeResponse()

        class FakeOpenAI:
            def __init__(self, api_key, timeout):
                self.responses = FakeResponses()

        with patch.object(import_ai_suggestions_module, "OpenAI", FakeOpenAI):
            suggestions = generate_ai_suggestions(
                self.tenant,
                normalize_import_row(
                    self.base_row
                    | {
                        "organization_description": "",
                        "organization_categories": "",
                        "organization_subcategories": "",
                        "organization_tags": "",
                        "person_categories": "",
                        "person_subcategories": "",
                        "person_tags": "",
                    }
                ),
                {"organization": {}, "person": {}},
            )

        self.assertEqual(suggestions["suggested_fields"]["suggested_categories"]["value"], ["Musikk"])
        self.assertNotIn("suggested_subcategories", suggestions["suggested_fields"])
        self.assertNotIn("organization_description", suggestions["suggested_fields"])

    @override_settings(
        OPENAI_IMPORT_ENABLED=False,
        OPENAI_API_KEY="",
    )
    def test_generate_ai_suggestions_can_use_website_signals_for_contacts_and_taxonomy(self):
        Organization.objects.create(
            tenant=self.tenant,
            name="Bergen Scenehus",
            municipalities="Bergen",
        )

        with patch.object(
            import_ai_suggestions_module,
            "_extract_contact_signals_from_website",
            return_value={
                "emails": ["post@scenehuset.no"],
                "phones": ["+47 55 55 55 55"],
                "socials": {"organization_instagram_url": "https://instagram.com/scenehuset"},
                "text_snippet": "Artister & Band i Bergen med jazz konserter og produksjon.",
                "final_url": "https://scenehuset.no",
            },
        ):
            suggestions = generate_ai_suggestions(
                self.tenant,
                normalize_import_row(self.base_row | {
                    "organization_email": "",
                    "organization_phone": "",
                    "organization_municipalities": "",
                    "organization_categories": "",
                    "organization_subcategories": "",
                    "organization_tags": "",
                    "person_categories": "",
                    "person_subcategories": "",
                    "person_tags": "",
                }),
                {"organization": {}, "person": {}},
            )

        self.assertEqual(suggestions["diagnostic"]["provider_status"], "fallback_openai_disabled")
        self.assertEqual(suggestions["suggested_fields"]["organization_email"]["value"], "post@scenehuset.no")
        self.assertEqual(suggestions["suggested_fields"]["organization_municipalities"]["value"], "Bergen")
        self.assertEqual(suggestions["suggested_fields"]["organization_instagram_url"]["value"], "https://instagram.com/scenehuset")
        self.assertEqual(suggestions["suggested_fields"]["suggested_subcategories"]["value"], ["Artister & Band"])
        self.assertEqual(suggestions["suggested_fields"]["suggested_categories"]["value"], ["Musikk"])
        self.assertNotIn("suggested_tags", suggestions["suggested_fields"])

    @override_settings(OPENAI_IMPORT_ENABLED=False, OPENAI_API_KEY="")
    def test_generate_ai_suggestions_skips_private_like_organization_email_suggestions(self):
        with patch.object(
            import_ai_suggestions_module,
            "_extract_contact_signals_from_website",
            return_value={
                "emails": ["ola@nordlyd.no"],
                "phones": [],
                "socials": {},
                "text_snippet": "Nordlyd kontaktinformasjon.",
                "final_url": "https://nordlyd.no",
            },
        ), patch.object(
            import_ai_suggestions_module,
            "search_organization_signals",
            return_value=importlib.import_module("crm.services.import.search_enrichment").SearchSignals(
                website_url="https://nordlyd.no",
                emails=["ola@nordlyd.no"],
                socials={},
                text_snippets=[],
                org_numbers=[],
            ),
        ):
            suggestions = generate_ai_suggestions(
                self.tenant,
                normalize_import_row(self.base_row | {"organization_email": ""}),
                {"organization": {}, "person": {}},
            )

        self.assertNotIn("organization_email", suggestions["suggested_fields"])

    @override_settings(OPENAI_IMPORT_ENABLED=False, OPENAI_API_KEY="")
    def test_generate_ai_suggestions_does_not_suggest_counties_as_municipalities(self):
        Organization.objects.create(
            tenant=self.tenant,
            name="Nordland Kulturhus",
            municipalities="Nordland",
        )

        with patch.object(
            import_ai_suggestions_module,
            "_extract_contact_signals_from_website",
            return_value={
                "emails": [],
                "phones": [],
                "socials": {},
                "text_snippet": "Nordland kulturhus jobber med musikk og scenekunst i Nordland.",
                "final_url": "https://nordlandkulturhus.no",
            },
        ):
            suggestions = generate_ai_suggestions(
                self.tenant,
                normalize_import_row(self.base_row | {"organization_municipalities": "", "person_municipality": ""}),
                {"organization": {}, "person": {}},
            )

        self.assertNotIn("organization_municipalities", suggestions["suggested_fields"])
        self.assertNotIn("person_municipality", suggestions["suggested_fields"])

    @override_settings(OPENAI_IMPORT_ENABLED=False, OPENAI_API_KEY="")
    def test_generate_ai_suggestions_can_use_verified_org_number_from_search_results(self):
        BrregCandidate = importlib.import_module("crm.services.import.brreg").BrregCandidate

        with patch.object(
            import_ai_suggestions_module,
            "best_brreg_candidate",
            return_value=None,
        ), patch.object(
            import_ai_suggestions_module,
            "candidate_for_org_number",
            return_value=BrregCandidate(
                org_number="934051106",
                name="Nordlyd Ungdomsbedrift",
                municipality="Tromsø",
                postal_place="Tromsø",
                website_url="",
                email="",
                score=0.0,
            ),
        ), patch.object(
            import_ai_suggestions_module,
            "search_organization_signals",
            return_value=importlib.import_module("crm.services.import.search_enrichment").SearchSignals(
                website_url="http://www.nordlyd.no/",
                emails=[],
                socials={},
                text_snippets=[],
                org_numbers=["934051106"],
            ),
        ), patch.object(
            import_ai_suggestions_module,
            "_extract_contact_signals_from_website",
            return_value={
                "emails": [],
                "phones": [],
                "socials": {},
                "text_snippet": "",
                "final_url": "http://www.nordlyd.no/",
            },
        ):
            suggestions = generate_ai_suggestions(
                self.tenant,
                normalize_import_row(
                    self.base_row
                    | {
                        "organization_name": "Nordlyd Ungdomsbedrift",
                        "organization_org_number": "",
                        "organization_municipalities": "",
                        "organization_website_url": "",
                    }
                ),
                {"organization": {}, "person": {}},
            )

        self.assertEqual(suggestions["suggested_fields"]["organization_org_number"]["value"], "934051106")
        self.assertEqual(suggestions["suggested_fields"]["organization_municipalities"]["value"], "Tromsø")
        self.assertEqual(suggestions["suggested_fields"]["organization_website_url"]["value"], "http://nordlyd.no/")
        self.assertTrue((suggestions.get("brreg_candidates") or []))

    @override_settings(
        OPENAI_IMPORT_ENABLED=True,
        OPENAI_API_KEY="test-key",
        OPENAI_IMPORT_MODEL="gpt-5.4",
        OPENAI_IMPORT_TIMEOUT=5,
    )
    def test_openai_municipality_suggestion_rejects_county_values(self):
        class FakeResponse:
            output_text = (
                '{"suggested_fields":{"organization_municipalities":{"value":"Nordland","confidence":0.84,"source":"ai_enrichment","requires_review":true}},'
                '"provider":"openai"}'
            )

        class FakeResponses:
            def create(self, **kwargs):
                return FakeResponse()

        class FakeOpenAI:
            def __init__(self, api_key, timeout):
                self.responses = FakeResponses()

        with patch.object(import_ai_suggestions_module, "OpenAI", FakeOpenAI):
            suggestions = generate_ai_suggestions(
                self.tenant,
                normalize_import_row(self.base_row | {"organization_municipalities": ""}),
                {"organization": {}, "person": {}},
            )

        self.assertNotIn("organization_municipalities", suggestions["suggested_fields"])

    @override_settings(OPENAI_IMPORT_ENABLED=False, OPENAI_API_KEY="")
    def test_generate_ai_suggestions_skips_fields_that_already_have_values(self):
        Tag.objects.create(tenant=self.tenant, name="jazz")

        with patch.object(
            import_ai_suggestions_module,
            "_extract_contact_signals_from_website",
            return_value={
                "emails": ["post@scenehuset.no"],
                "phones": ["+47 55 55 55 55"],
                "socials": {"organization_instagram_url": "https://instagram.com/scenehuset"},
                "text_snippet": "Artister & Band i Bergen med jazz konserter og produksjon.",
                "final_url": "https://scenehuset.no",
            },
        ):
            suggestions = generate_ai_suggestions(
                self.tenant,
                normalize_import_row(self.base_row),
                {"organization": {}, "person": {}},
            )

        self.assertEqual(suggestions["diagnostic"]["provider_status"], "fallback_openai_disabled")
        self.assertNotIn("organization_email", suggestions["suggested_fields"])
        self.assertNotIn("organization_phone", suggestions["suggested_fields"])
        self.assertNotIn("organization_municipalities", suggestions["suggested_fields"])
        self.assertNotIn("suggested_categories", suggestions["suggested_fields"])
        self.assertNotIn("suggested_subcategories", suggestions["suggested_fields"])
        self.assertNotIn("suggested_tags", suggestions["suggested_fields"])

    @override_settings(OPENAI_IMPORT_ENABLED=False, OPENAI_API_KEY="")
    def test_generate_ai_suggestions_prefers_domain_email_and_website(self):
        with patch.object(
            import_ai_suggestions_module,
            "_extract_contact_signals_from_website",
            return_value={
                "emails": ["info@partner-agency.no", "kontakt@nordlyd.no"],
                "phones": ["22 22 22 22", "+47 11 11 11 11"],
                "socials": {},
                "text_snippet": "Nordlyd utvikler og produserer konserter og turneer i Oslo.",
                "final_url": "https://nordlyd.no/om-oss",
            },
        ):
            suggestions = generate_ai_suggestions(
                self.tenant,
                normalize_import_row(
                    self.base_row
                    | {
                        "organization_email": "",
                        "organization_phone": "",
                        "organization_website_url": "",
                        "organization_description": "",
                        "person_email": "booking@nordlyd.no",
                    }
                ),
                {"organization": {}, "person": {}},
            )

        self.assertEqual(suggestions["diagnostic"]["provider_status"], "fallback_openai_disabled")
        self.assertEqual(suggestions["suggested_fields"]["organization_website_url"]["value"], "https://nordlyd.no/om-oss")
        self.assertEqual(suggestions["suggested_fields"]["organization_email"]["value"], "kontakt@nordlyd.no")
        self.assertNotIn("organization_phone", suggestions["suggested_fields"])
        self.assertNotIn("organization_description", suggestions["suggested_fields"])

    @override_settings(OPENAI_IMPORT_ENABLED=False, OPENAI_API_KEY="")
    def test_generate_ai_suggestions_exposes_domain_based_actor_candidates_for_person_import(self):
        existing = Organization.objects.create(
            tenant=self.tenant,
            name="Nordlyd AS",
            website_url="https://nordlyd.no",
        )

        suggestions = generate_ai_suggestions(
            self.tenant,
            normalize_import_row(
                self.base_row
                | {
                    "organization_name": "",
                    "organization_org_number": "",
                    "organization_email": "",
                    "organization_website_url": "",
                    "organization_categories": "",
                    "organization_subcategories": "",
                    "organization_tags": "",
                    "person_email": "ada@nordlyd.no",
                    "person_categories": "",
                    "person_subcategories": "",
                    "person_tags": "",
                }
            ),
            match_row_entities(
                self.tenant,
                normalize_import_row(
                    self.base_row
                    | {
                        "organization_name": "",
                        "organization_org_number": "",
                        "organization_email": "",
                        "organization_website_url": "",
                        "organization_categories": "",
                        "organization_subcategories": "",
                        "organization_tags": "",
                        "person_email": "ada@nordlyd.no",
                        "person_categories": "",
                        "person_subcategories": "",
                        "person_tags": "",
                    }
                ),
            ),
        )

        self.assertEqual(suggestions["organization_match_candidates"][0]["id"], existing.id)
        self.assertEqual(suggestions["organization_match_candidates"][0]["reason"], "contact_domain")

    @override_settings(OPENAI_IMPORT_ENABLED=False, OPENAI_API_KEY="")
    def test_generate_ai_suggestions_can_use_brreg_org_number_and_municipality(self):
        BrregCandidate = importlib.import_module("crm.services.import.brreg").BrregCandidate
        with patch.object(
            import_ai_suggestions_module,
            "best_brreg_candidate",
            return_value=BrregCandidate(
                org_number="123456785",
                name="Nordlyd AS",
                municipality="Bodø",
                postal_place="BODØ",
                website_url="https://nordlyd.no",
                email="post@nordlyd.no",
                score=0.91,
            ),
        ), patch.object(
            import_ai_suggestions_module,
            "search_organization_signals",
            return_value=importlib.import_module("crm.services.import.search_enrichment").SearchSignals(
                website_url=None,
                emails=[],
                socials={},
                text_snippets=[],
            ),
        ), patch.object(
            import_ai_suggestions_module,
            "search_person_signals",
            return_value=importlib.import_module("crm.services.import.search_enrichment").SearchSignals(
                website_url=None,
                emails=[],
                socials={},
                text_snippets=[],
            ),
        ):
            suggestions = generate_ai_suggestions(
                self.tenant,
                normalize_import_row(
                    self.base_row
                    | {
                        "organization_org_number": "",
                        "organization_municipalities": "",
                        "organization_email": "",
                        "organization_website_url": "",
                    }
                ),
                {"organization": {}, "person": {}},
            )

        self.assertEqual(suggestions["suggested_fields"]["organization_org_number"]["value"], "123456785")
        self.assertEqual(suggestions["suggested_fields"]["organization_municipalities"]["value"], "Bodø")
        self.assertEqual(suggestions["suggested_fields"]["organization_website_url"]["value"], "https://nordlyd.no")
        self.assertEqual(suggestions["suggested_fields"]["organization_email"]["value"], "post@nordlyd.no")

    @override_settings(OPENAI_IMPORT_ENABLED=False, OPENAI_API_KEY="")
    def test_generate_ai_suggestions_uses_person_specific_search_signals(self):
        SearchSignals = importlib.import_module("crm.services.import.search_enrichment").SearchSignals
        with patch.object(
            import_ai_suggestions_module,
            "search_organization_signals",
            return_value=SearchSignals(
                website_url="https://nordlyd.no",
                emails=["kontakt@nordlyd.no"],
                socials={"organization_instagram_url": "https://instagram.com/nordlyd"},
                text_snippets=["Nordlyd er et produksjonsselskap i Oslo."],
            ),
        ), patch.object(
            import_ai_suggestions_module,
            "search_person_signals",
            return_value=SearchSignals(
                website_url="https://adastorm.no",
                emails=["ada@adastorm.no"],
                socials={"person_instagram_url": "https://instagram.com/adastorm"},
                text_snippets=["Ada Storm er musiker og produsent bosatt i Oslo."],
            ),
        ), patch.object(
            import_ai_suggestions_module,
            "_extract_contact_signals_from_website",
            return_value={"emails": [], "phones": [], "socials": {}, "text_snippet": "", "final_url": ""},
        ):
            suggestions = generate_ai_suggestions(
                self.tenant,
                normalize_import_row(
                    self.base_row
                    | {
                        "organization_name": "Nordlyd AS",
                        "organization_org_number": "",
                        "organization_email": "",
                        "organization_website_url": "",
                        "person_full_name": "Ada Storm",
                        "person_email": "",
                        "person_website_url": "",
                        "person_instagram_url": "",
                    }
                ),
                {"organization": {}, "person": {}},
            )

        self.assertEqual(suggestions["suggested_fields"]["person_email"]["value"], "ada@adastorm.no")
        self.assertEqual(suggestions["suggested_fields"]["person_website_url"]["value"], "https://adastorm.no")
        self.assertEqual(suggestions["suggested_fields"]["person_instagram_url"]["value"], "https://instagram.com/adastorm")
        self.assertEqual(suggestions["suggested_fields"]["organization_website_url"]["value"], "https://nordlyd.no")

    def test_search_person_signals_limits_social_platforms_to_instagram_facebook_and_tiktok(self):
        search_enrichment_module = importlib.import_module("crm.services.import.search_enrichment")
        seen_queries: list[str] = []

        def fake_merge_ranked_results(queries, *, target_name, context_terms=None, limit=4):
            seen_queries.extend(list(queries))
            return []

        with patch.object(search_enrichment_module, "_merge_ranked_results", side_effect=fake_merge_ranked_results):
            search_enrichment_module.search_person_signals(
                normalize_import_row(
                    self.base_row
                    | {
                        "organization_name": "Nordlyd AS",
                        "person_full_name": "Ada Storm",
                        "person_municipality": "Oslo",
                    }
                ),
                tenant=self.tenant,
            )

        joined_queries = " ".join(seen_queries).casefold()
        self.assertIn("instagram", joined_queries)
        self.assertIn("facebook", joined_queries)
        self.assertIn("tiktok", joined_queries)
        self.assertNotIn("linkedin", joined_queries)
        self.assertNotIn("youtube", joined_queries)

    def test_search_organization_signals_extracts_primary_site_and_socials_from_search_results(self):
        search_enrichment_module = importlib.import_module("crm.services.import.search_enrichment")
        fake_results = [
            {
                "url": "https://www.nordlyd.no/kontakt",
                "title": "Nordlyd AS",
                "snippet": "Kontakt Nordlyd på post@nordlyd.no for booking og info.",
            },
            {
                "url": "https://www.instagram.com/nordlyd",
                "title": "Nordlyd på Instagram",
                "snippet": "Nordlyd deler oppdateringer fra musikkmiljøet.",
            },
        ]

        with patch.object(search_enrichment_module, "_search", return_value=fake_results):
            signals = search_enrichment_module.search_organization_signals(
                normalize_import_row(
                    self.base_row
                    | {
                        "organization_email": "",
                        "organization_website_url": "",
                        "organization_instagram_url": "",
                    }
                )
            )

        self.assertEqual(signals.website_url, "https://nordlyd.no/kontakt")
        self.assertEqual(signals.socials["organization_instagram_url"], "https://instagram.com/nordlyd")
        self.assertEqual(signals.emails, ["post@nordlyd.no"])
        self.assertTrue(any("booking og info" in snippet for snippet in signals.text_snippets or []))

    def test_search_organization_signals_prefers_official_domain_over_directory_results(self):
        search_enrichment_module = importlib.import_module("crm.services.import.search_enrichment")
        fake_results = [
            {
                "url": "https://www.proff.no/selskap/sv%C3%B8mmehallen-scene",
                "title": "Svømmehallen Scene - Proff",
                "snippet": "Bransjeinformasjon om Svømmehallen Scene.",
            },
            {
                "url": "https://svommehallenscene.no",
                "title": "Svømmehallen Scene",
                "snippet": "Offisiell nettside for Svømmehallen Scene i Bodø.",
            },
            {
                "url": "https://www.facebook.com/svommehallenscene",
                "title": "Svømmehallen Scene | Facebook",
                "snippet": "Følg Svømmehallen Scene på Facebook.",
            },
        ]

        with patch.object(search_enrichment_module, "_search", return_value=fake_results):
            signals = search_enrichment_module.search_organization_signals(
                normalize_import_row(
                    self.base_row
                    | {
                        "organization_name": "Svømmehallen Scene",
                        "organization_email": "",
                        "organization_website_url": "",
                        "organization_facebook_url": "",
                    }
                )
            )

        self.assertEqual(signals.website_url, "https://svommehallenscene.no")
        self.assertEqual(signals.socials["organization_facebook_url"], "https://facebook.com/svommehallenscene")

    def test_search_organization_signals_uses_confirmed_existing_actor_prior(self):
        search_enrichment_module = importlib.import_module("crm.services.import.search_enrichment")
        Organization.objects.create(
            tenant=self.tenant,
            name="Pott og Panne",
            municipalities="Bodø",
            website_url="https://pottogpanne.no",
            facebook_url="https://facebook.com/pottogpanne",
        )
        fake_results = [
            {
                "url": "https://www.proff.no/selskap/pott-og-panne",
                "title": "Pott og Panne - Proff",
                "snippet": "Bedriftsinformasjon om Pott og Panne.",
            }
        ]

        with patch.object(search_enrichment_module, "_search", return_value=fake_results):
            signals = search_enrichment_module.search_organization_signals(
                normalize_import_row(
                    self.base_row
                    | {
                        "organization_name": "Pott og Panne",
                        "organization_municipalities": "",
                        "organization_website_url": "",
                        "organization_facebook_url": "",
                    }
                ),
                tenant=self.tenant,
            )

        self.assertEqual(signals.website_url, "https://pottogpanne.no")
        self.assertEqual(signals.socials["organization_facebook_url"], "https://facebook.com/pottogpanne")
        self.assertEqual(signals.municipality_candidates[0]["value"], "Bodø")

    @patch("crm.services.import.commit.refresh_organization_open_graph")
    def test_skip_row_decision_excludes_row_from_commit(self, refresh_mock):
        self._upload_csv()
        preview_response = self.client.post(f"{self.import_jobs_url()}{self.job.id}/preview/", {}, format="json")
        self.assertEqual(preview_response.status_code, 200, preview_response.content)
        row = self.job.rows.get()

        decisions_response = self.client.post(
            f"{self.import_jobs_url()}{self.job.id}/decisions/",
            {
                "rows": [
                    {
                        "row_id": row.id,
                        "decisions": [
                            {
                                "decision_type": "SKIP_ROW",
                                "payload_json": {},
                            }
                        ],
                    }
                ]
            },
            format="json",
        )
        self.assertEqual(decisions_response.status_code, 200, decisions_response.content)

        commit_response = self.client.post(
            f"{self.import_jobs_url()}{self.job.id}/commit/",
            {"skip_unresolved": False},
            format="json",
        )
        self.assertEqual(commit_response.status_code, 200, commit_response.content)

        row.refresh_from_db()
        self.assertEqual(row.row_status, ImportRow.RowStatus.SKIPPED)
        self.assertFalse(Organization.objects.filter(tenant=self.tenant, org_number="123456789").exists())
        refresh_mock.assert_not_called()

    def test_openai_schema_requires_all_suggested_fields_and_allows_null_values(self):
        schema = import_ai_suggestions_module._openai_schema()["schema"]
        suggested_fields = schema["properties"]["suggested_fields"]
        properties = suggested_fields["properties"]

        self.assertEqual(set(suggested_fields["required"]), set(properties.keys()))
        self.assertEqual(
            properties["organization_municipalities"],
            {
                "anyOf": [
                    {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "value": {"type": "string"},
                            "confidence": {"type": "number"},
                            "source": {"type": "string"},
                            "requires_review": {"type": "boolean"},
                        },
                        "required": ["value", "confidence", "source", "requires_review"],
                    },
                    {"type": "null"},
                ]
            },
        )

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
    def test_accepted_social_url_suggestion_can_influence_commit(self, refresh_mock):
        row = self.base_row | {"organization_instagram_url": ""}
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
                                    "suggestion_key": "organization_instagram_url",
                                    "value": "https://instagram.com/nordlyd",
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
        self.assertEqual(organization.instagram_url, "https://instagram.com/nordlyd")
        refresh_mock.assert_called_once()

    @patch("crm.services.import.commit.refresh_organization_open_graph")
    def test_accepted_municipality_suggestion_can_influence_commit(self, refresh_mock):
        row = self.base_row | {"organization_municipalities": ""}
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
                                    "suggestion_key": "organization_municipalities",
                                    "value": "Bodø",
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
        self.assertEqual(organization.municipalities, "Bodø")
        refresh_mock.assert_called_once()

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


class InternalTagModelAndApiTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Internal Tag Tenant", slug="internal-tag-tenant")
        self.other_tenant = Tenant.objects.create(name="Other Internal Tag Tenant", slug="other-internal-tag-tenant")
        grant_membership(self.user, self.tenant)
        self.primary_tag = InternalTag.objects.create(tenant=self.tenant, name="Prioritet")
        self.other_tag = InternalTag.objects.create(tenant=self.other_tenant, name="Partner")

    def tenant_internal_tags_url(self, tenant_id: int | None = None) -> str:
        return f"/api/tenants/{tenant_id or self.tenant.id}/internal-tags/"

    def test_generates_slug_on_create(self):
        self.assertEqual(self.primary_tag.slug, "prioritet")

    def test_list_is_scoped_to_tenant(self):
        response = self.client.get(self.tenant_internal_tags_url())
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["name"], "Prioritet")

    def test_create_sets_tenant_from_route(self):
        response = self.client.post(
            self.tenant_internal_tags_url(),
            {"name": "Følges opp"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        created = InternalTag.objects.get(id=response.json()["id"])
        self.assertEqual(created.tenant_id, self.tenant.id)
        self.assertEqual(created.slug, "folges-opp")

    def test_rejects_duplicate_name_in_same_tenant(self):
        response = self.client.post(
            self.tenant_internal_tags_url(),
            {"name": "Prioritet"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_organization_serializer_includes_internal_tags(self):
        organization = Organization.objects.create(tenant=self.tenant, name="Intern Org")
        organization.internal_tags.add(self.primary_tag)

        data = self.client.get(f"/api/tenants/{self.tenant.id}/organizations/").json()[0]

        self.assertEqual(len(data["internal_tags"]), 1)
        self.assertEqual(data["internal_tags"][0]["name"], "Prioritet")


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
        self.internal_tag = InternalTag.objects.create(tenant=self.tenant, name="Prioritet")

    def test_can_create_organization_without_tenant_in_payload(self):
        response = self.client.post(
            f"/api/tenants/{self.tenant.id}/organizations/",
            {
                "name": "Ny organisasjon",
                "org_number": "123456789",
                "municipalities": "Oslo",
                "tag_ids": [],
                "internal_tag_ids": [self.internal_tag.id],
                "category_ids": [],
                "subcategory_ids": [],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.content)
        created = Organization.objects.get(id=response.json()["id"])
        self.assertEqual(created.tenant_id, self.tenant.id)
        self.assertEqual(list(created.internal_tags.values_list("name", flat=True)), ["Prioritet"])

    def test_can_create_person_without_tenant_in_payload(self):
        response = self.client.post(
            f"/api/tenants/{self.tenant.id}/persons/",
            {
                "full_name": "Ny kontaktperson",
                "title": "Produsent",
                "municipality": "Oslo",
                "tag_ids": [],
                "internal_tag_ids": [self.internal_tag.id],
                "category_ids": [],
                "subcategory_ids": [],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.content)
        created = Person.objects.get(id=response.json()["id"])
        self.assertEqual(created.tenant_id, self.tenant.id)
        self.assertEqual(created.title, "Produsent")
        self.assertEqual(list(created.internal_tags.values_list("name", flat=True)), ["Prioritet"])

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
    @patch("crm.services.open_graph._image_candidate_looks_usable", return_value=True)
    def test_choose_best_thumbnail_prefers_large_non_logo_candidate(self, usable_mock):
        chosen = choose_best_thumbnail(
            "https://example.com/about",
            [
                ImageCandidate(url="/assets/logo.png", source="img", width=320, height=120, alt="Logo"),
                ImageCandidate(url="/media/portrait.jpg", source="img", width=1200, height=1200, alt="Artist"),
            ],
        )

        self.assertEqual(chosen, "https://example.com/media/portrait.jpg")
        self.assertGreaterEqual(usable_mock.call_count, 1)

    @patch("crm.services.open_graph._image_candidate_looks_usable")
    def test_choose_best_thumbnail_tries_next_candidate_when_first_fails(self, usable_mock):
        usable_mock.side_effect = [False, True]

        chosen = choose_best_thumbnail(
            "https://example.com/about",
            [
                ImageCandidate(url="/media/broken-hero.jpg", source="og:image", width=1400, height=900),
                ImageCandidate(url="/media/working-hero.jpg", source="img", width=1200, height=1200),
            ],
        )

        self.assertEqual(chosen, "https://example.com/media/working-hero.jpg")

    def test_fetch_open_graph_blocks_private_host(self):
        with self.assertRaises(ValueError):
            fetch_open_graph("http://127.0.0.1/private")

    def test_fallback_preview_image_ignores_private_host(self):
        self.assertIsNone(fallback_preview_image("http://localhost:8000"))


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
