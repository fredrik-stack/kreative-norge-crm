import json
import os
import inspect
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import zipfile
import importlib
from io import BytesIO
from io import StringIO
from xml.sax.saxutils import escape
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Group
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management import call_command, CommandError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, close_old_connections, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.db.models.deletion import ProtectedError
from django.test import SimpleTestCase, TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone
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
    ImageAsset,
    ImageRendition,
    ImageRenditionSet,
    ImageReviewEvent,
    OrganizationImageSelection,
    AppendOnlyEventError,
)
from .validators import validate_storage_key
from .services.open_graph import ImageCandidate, choose_best_thumbnail, fallback_preview_image, fetch_open_graph
from .services.images.selections import (
    IMAGE_APPROVAL_TEXT,
    IMAGE_APPROVAL_TEXT_VERSION,
    AssetApprovalEvidence,
    ExpectedRevisionConflictError,
    ImageFeatureDisabledError,
    ImageSelectionConcurrencyError,
    ImageSelectionNotFoundError,
    ImageSelectionPermissionDenied,
    IncompleteRenditionSetError,
    InvalidImageSelectionError,
    InvalidImageSelectionTransitionError,
    lock_organization_image_selection,
    remove_organization_image_to_fallback,
    restore_archived_organization_image_selection,
)
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


class ImageStorageSettingsTests(SimpleTestCase):
    settings_environment_names = (
        "IMAGE_ASSET_FEATURE_ENABLED",
        "IMAGE_ORIGINALS_ROOT",
        "IMAGE_RENDITIONS_ROOT",
    )

    def run_settings_process(self, source, **environment_overrides):
        environment = os.environ.copy()
        for name in self.settings_environment_names:
            environment.pop(name, None)
        environment.update(
            {
                "DJANGO_DEBUG": "True",
                "DJANGO_SETTINGS_MODULE": "config.settings",
            }
        )
        for name, value in environment_overrides.items():
            if value is None:
                environment.pop(name, None)
            else:
                environment[name] = str(value)

        return subprocess.run(
            [sys.executable, "-c", source],
            cwd=Path(__file__).resolve().parents[1],
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

    def settings_snapshot(self, **environment_overrides):
        result = self.run_settings_process(
            """
import json
from django.conf import settings
from django.core.files.storage import storages

private_storage = storages["image_originals_private"]
public_storage = storages["image_renditions_public"]
print(json.dumps({
    "feature_enabled": settings.IMAGE_ASSET_FEATURE_ENABLED,
    "aliases": sorted(settings.STORAGES),
    "default_backend": settings.STORAGES["default"]["BACKEND"],
    "default_options": settings.STORAGES["default"].get("OPTIONS"),
    "staticfiles_backend": settings.STORAGES["staticfiles"]["BACKEND"],
    "private_class": private_storage.__class__.__name__,
    "public_class": public_storage.__class__.__name__,
    "private_location": private_storage.location,
    "public_location": public_storage.location,
    "same_instance": private_storage is public_storage,
}))
""",
            **environment_overrides,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def assert_settings_rejected(self, expected_message, **environment_overrides):
        result = self.run_settings_process(
            "from django.conf import settings; print(settings.IMAGE_ORIGINALS_ROOT)",
            **environment_overrides,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected_message, result.stderr)

    def test_image_asset_feature_flag_defaults_to_false(self):
        self.assertIs(self.settings_snapshot()["feature_enabled"], False)

    def test_image_asset_feature_flag_accepts_explicit_true(self):
        snapshot = self.settings_snapshot(IMAGE_ASSET_FEATURE_ENABLED="true")

        self.assertIs(snapshot["feature_enabled"], True)

    def test_image_asset_feature_flag_accepts_explicit_false(self):
        snapshot = self.settings_snapshot(IMAGE_ASSET_FEATURE_ENABLED="false")

        self.assertIs(snapshot["feature_enabled"], False)

    def test_image_asset_feature_flag_rejects_unknown_value_fail_closed(self):
        snapshot = self.settings_snapshot(IMAGE_ASSET_FEATURE_ENABLED="enable-maybe")

        self.assertIs(snapshot["feature_enabled"], False)

    def test_storage_aliases_preserve_defaults_and_separate_image_storages(self):
        snapshot = self.settings_snapshot()

        self.assertEqual(
            snapshot["aliases"],
            [
                "default",
                "image_originals_private",
                "image_renditions_public",
                "staticfiles",
            ],
        )
        self.assertEqual(
            snapshot["default_backend"],
            "django.core.files.storage.FileSystemStorage",
        )
        self.assertIsNone(snapshot["default_options"])
        self.assertEqual(
            snapshot["staticfiles_backend"],
            "django.contrib.staticfiles.storage.StaticFilesStorage",
        )
        self.assertEqual(snapshot["private_class"], "FileSystemStorage")
        self.assertEqual(snapshot["public_class"], "FileSystemStorage")
        self.assertFalse(snapshot["same_instance"])
        self.assertNotEqual(
            snapshot["private_location"],
            snapshot["public_location"],
        )

    def test_relative_image_storage_root_is_rejected(self):
        self.assert_settings_rejected(
            "IMAGE_ORIGINALS_ROOT must be an absolute path",
            IMAGE_ORIGINALS_ROOT="relative/private",
        )

    def test_empty_explicit_image_storage_root_is_rejected(self):
        self.assert_settings_rejected(
            "IMAGE_ORIGINALS_ROOT cannot be empty",
            IMAGE_ORIGINALS_ROOT="",
        )

    def test_identical_image_storage_roots_are_rejected(self):
        self.assert_settings_rejected(
            "IMAGE_ORIGINALS_ROOT and IMAGE_RENDITIONS_ROOT cannot overlap",
            IMAGE_ORIGINALS_ROOT="/var/tmp/kreative-images",
            IMAGE_RENDITIONS_ROOT="/var/tmp/kreative-images",
        )

    def test_filesystem_root_is_rejected(self):
        self.assert_settings_rejected(
            "IMAGE_ORIGINALS_ROOT cannot be the filesystem root",
            IMAGE_ORIGINALS_ROOT="/",
        )

    def test_staticfiles_overlap_is_rejected(self):
        repository_root = Path(__file__).resolve().parents[1]
        self.assert_settings_rejected(
            "IMAGE_ORIGINALS_ROOT cannot overlap STATIC_ROOT",
            IMAGE_ORIGINALS_ROOT=repository_root / "staticfiles" / "images",
        )

    def test_application_repository_overlap_is_rejected(self):
        repository_root = Path(__file__).resolve().parents[1]
        self.assert_settings_rejected(
            "IMAGE_ORIGINALS_ROOT must be outside the application repository",
            DJANGO_DEBUG="False",
            IMAGE_ORIGINALS_ROOT=repository_root / "media-private",
            IMAGE_RENDITIONS_ROOT="/var/tmp/kreative-images-public",
        )

    def test_non_debug_enabled_feature_rejects_both_missing_roots(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            local_default_root = (
                Path(temporary_directory) / "kreative-norge-crm-media"
            )

            self.assert_settings_rejected(
                "IMAGE_ORIGINALS_ROOT must be set when image assets are enabled outside debug",
                DJANGO_DEBUG="False",
                IMAGE_ASSET_FEATURE_ENABLED="true",
                TMPDIR=temporary_directory,
            )
            self.assertFalse(local_default_root.exists())

    def test_non_debug_enabled_feature_rejects_missing_private_root(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            public_root = Path(temporary_directory) / "public"

            self.assert_settings_rejected(
                "IMAGE_ORIGINALS_ROOT must be set when image assets are enabled outside debug",
                DJANGO_DEBUG="False",
                IMAGE_ASSET_FEATURE_ENABLED="true",
                IMAGE_RENDITIONS_ROOT=public_root,
                TMPDIR=temporary_directory,
            )
            self.assertFalse(public_root.exists())

    def test_non_debug_enabled_feature_rejects_missing_public_root(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            private_root = Path(temporary_directory) / "private"

            self.assert_settings_rejected(
                "IMAGE_RENDITIONS_ROOT must be set when image assets are enabled outside debug",
                DJANGO_DEBUG="False",
                IMAGE_ASSET_FEATURE_ENABLED="true",
                IMAGE_ORIGINALS_ROOT=private_root,
                TMPDIR=temporary_directory,
            )
            self.assertFalse(private_root.exists())

    def test_non_debug_enabled_feature_accepts_explicit_separate_roots(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            private_root = Path(temporary_directory) / "private"
            public_root = Path(temporary_directory) / "public"

            snapshot = self.settings_snapshot(
                DJANGO_DEBUG="False",
                IMAGE_ASSET_FEATURE_ENABLED="true",
                IMAGE_ORIGINALS_ROOT=private_root,
                IMAGE_RENDITIONS_ROOT=public_root,
                TMPDIR=temporary_directory,
            )

            self.assertIs(snapshot["feature_enabled"], True)
            self.assertEqual(
                Path(snapshot["private_location"]),
                private_root.resolve(strict=False),
            )
            self.assertEqual(
                Path(snapshot["public_location"]),
                public_root.resolve(strict=False),
            )
            self.assertFalse(private_root.exists())
            self.assertFalse(public_root.exists())

    def test_non_debug_disabled_feature_accepts_missing_roots(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            local_default_root = (
                Path(temporary_directory) / "kreative-norge-crm-media"
            )

            snapshot = self.settings_snapshot(
                DJANGO_DEBUG="False",
                IMAGE_ASSET_FEATURE_ENABLED="false",
                TMPDIR=temporary_directory,
            )

            self.assertIs(snapshot["feature_enabled"], False)
            self.assertFalse(local_default_root.exists())

    def test_debug_accepts_missing_roots_for_enabled_feature(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            local_default_root = (
                Path(temporary_directory) / "kreative-norge-crm-media"
            )

            snapshot = self.settings_snapshot(
                DJANGO_DEBUG="True",
                IMAGE_ASSET_FEATURE_ENABLED="true",
                TMPDIR=temporary_directory,
            )

            self.assertIs(snapshot["feature_enabled"], True)
            self.assertFalse(local_default_root.exists())

    def test_settings_load_and_system_check_do_not_create_storage_paths(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            private_root = Path(temporary_directory) / "private" / "originals"
            public_root = Path(temporary_directory) / "public" / "renditions"
            environment_overrides = {
                "IMAGE_ORIGINALS_ROOT": private_root,
                "IMAGE_RENDITIONS_ROOT": public_root,
            }

            snapshot = self.settings_snapshot(**environment_overrides)
            self.assertEqual(
                Path(snapshot["private_location"]),
                private_root.resolve(strict=False),
            )
            self.assertEqual(
                Path(snapshot["public_location"]),
                public_root.resolve(strict=False),
            )
            self.assertFalse(private_root.exists())
            self.assertFalse(public_root.exists())

            environment = os.environ.copy()
            for name in self.settings_environment_names:
                environment.pop(name, None)
            environment.update(
                {
                    "DJANGO_DEBUG": "True",
                    "DJANGO_SETTINGS_MODULE": "config.settings",
                    "IMAGE_ORIGINALS_ROOT": str(private_root),
                    "IMAGE_RENDITIONS_ROOT": str(public_root),
                }
            )
            result = subprocess.run(
                [sys.executable, "manage.py", "check"],
                cwd=Path(__file__).resolve().parents[1],
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(private_root.exists())
            self.assertFalse(public_root.exists())


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
            "person_email_public": "",
            "person_phone": "+4722222222",
            "person_phone_public": "",
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
        self.assertFalse(person.contacts.get(type="EMAIL", is_primary=True).is_public)
        self.assertFalse(person.contacts.get(type="PHONE", is_primary=True).is_public)
        self.assertTrue(person.contacts.filter(value="ada.booking@example.com", is_public=False).exists())
        self.assertTrue(Tag.objects.filter(tenant=self.tenant, name="jazz").exists())
        self.assertGreater(self.job.commit_logs.count(), 0)
        refresh_mock.assert_called_once()

    @patch("crm.services.import.commit.refresh_organization_open_graph")
    def test_commit_can_publish_primary_person_email_explicitly(self, refresh_mock):
        self._upload_csv([self.base_row | {"person_email_public": "ja"}])
        self.client.post(f"{self.import_jobs_url()}{self.job.id}/preview/", {}, format="json")

        response = self.client.post(f"{self.import_jobs_url()}{self.job.id}/commit/", {"skip_unresolved": False}, format="json")
        self.assertEqual(response.status_code, 200, response.content)

        contact = PersonContact.objects.get(type="EMAIL", value="ada@example.com", is_primary=True)
        self.assertTrue(contact.is_public)
        refresh_mock.assert_called_once()

    @patch("crm.services.import.commit.refresh_organization_open_graph")
    def test_commit_without_person_email_public_preserves_existing_public_flag(self, refresh_mock):
        organization = Organization.objects.create(
            tenant=self.tenant,
            name="Nordlyd Existing",
            org_number="123456789",
        )
        person = Person.objects.create(
            tenant=self.tenant,
            full_name="Ada Artist",
            email="ada@example.com",
        )
        contact = PersonContact.objects.create(
            tenant=self.tenant,
            person=person,
            type="EMAIL",
            value="ada@example.com",
            is_primary=True,
            is_public=True,
        )
        OrganizationPerson.objects.create(
            tenant=self.tenant,
            organization=organization,
            person=person,
            status="ACTIVE",
            publish_person=True,
        )

        row = {key: value for key, value in self.base_row.items() if key != "person_email_public"}
        self._upload_csv([row])
        self.client.post(f"{self.import_jobs_url()}{self.job.id}/preview/", {}, format="json")

        response = self.client.post(f"{self.import_jobs_url()}{self.job.id}/commit/", {"skip_unresolved": False}, format="json")
        self.assertEqual(response.status_code, 200, response.content)

        contact.refresh_from_db()
        self.assertTrue(contact.is_public)
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
                normalize_import_row(self.base_row),
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
                '"organization_description":{"value":"Nordlyd er en norsk arrangor.","confidence":0.77,"source":"ai_enrichment","requires_review":true},'
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
                normalize_import_row(self.base_row),
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
    def test_generate_ai_suggestions_discards_invalid_taxonomy_and_non_norwegian_description(self):
        class FakeResponse:
            output_text = (
                '{"suggested_fields":{"organization_description":{"value":"The company creates events for artists.","confidence":0.8,"source":"ai_enrichment","requires_review":true},'
                '"suggested_categories":{"value":["Musikk"],"confidence":0.9,"source":"ai_enrichment","requires_review":true},'
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
                normalize_import_row(self.base_row),
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
        Tag.objects.create(tenant=self.tenant, name="jazz")
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
                }),
                {"organization": {}, "person": {}},
            )

        self.assertEqual(suggestions["diagnostic"]["provider_status"], "fallback_openai_disabled")
        self.assertEqual(suggestions["suggested_fields"]["organization_email"]["value"], "post@scenehuset.no")
        self.assertEqual(suggestions["suggested_fields"]["organization_phone"]["value"], "+47 55 55 55 55")
        self.assertEqual(suggestions["suggested_fields"]["organization_municipalities"]["value"], "Bergen")
        self.assertEqual(suggestions["suggested_fields"]["organization_instagram_url"]["value"], "https://instagram.com/scenehuset")
        self.assertEqual(suggestions["suggested_fields"]["suggested_subcategories"]["value"], ["Artister & Band"])
        self.assertEqual(suggestions["suggested_fields"]["suggested_categories"]["value"], ["Musikk"])
        self.assertEqual(suggestions["suggested_fields"]["suggested_tags"]["value"], ["jazz"])

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

    def test_list_includes_private_contact_channels(self):
        response = self.client.get(self.tenant_contacts_url(), {"person": self.person_b.id})
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["id"], self.contact_b.id)
        self.assertFalse(payload[0]["is_public"])

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

    def test_primary_email_contact_update_syncs_person_email(self):
        response = self.client.patch(
            f"{self.tenant_contacts_url()}{self.contact_a.id}/",
            {"value": "alice.new@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)

        self.person_a.refresh_from_db()
        self.assertEqual(self.person_a.email, "alice.new@example.com")

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


class PersonContactSyncApiTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Sync Tenant", slug="sync-tenant")
        grant_membership(self.user, self.tenant)

    def persons_url(self, person_id: int | None = None) -> str:
        base = f"/api/tenants/{self.tenant.id}/persons/"
        return f"{base}{person_id}/" if person_id else base

    def test_create_person_with_email_creates_private_primary_contact(self):
        response = self.client.post(
            self.persons_url(),
            {
                "full_name": "Ada Sync",
                "email": "ada.sync@example.com",
                "phone": "",
                "municipality": "Oslo",
                "tag_ids": [],
                "category_ids": [],
                "subcategory_ids": [],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)

        person = Person.objects.get(id=response.json()["id"])
        contact = PersonContact.objects.get(person=person, type="EMAIL", is_primary=True)
        self.assertEqual(contact.value, "ada.sync@example.com")
        self.assertFalse(contact.is_public)

    def test_create_person_with_phone_creates_private_primary_contact(self):
        response = self.client.post(
            self.persons_url(),
            {
                "full_name": "Phone Sync",
                "email": "",
                "phone": "+4798765432",
                "municipality": "Bergen",
                "tag_ids": [],
                "category_ids": [],
                "subcategory_ids": [],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)

        person = Person.objects.get(id=response.json()["id"])
        contact = PersonContact.objects.get(person=person, type="PHONE", is_primary=True)
        self.assertEqual(contact.value, "+4798765432")
        self.assertFalse(contact.is_public)

    def test_update_person_email_preserves_existing_public_flag(self):
        person = Person.objects.create(
            tenant=self.tenant,
            full_name="Ada Existing",
            email="ada.old@example.com",
            municipality="Oslo",
        )
        contact = PersonContact.objects.create(
            tenant=self.tenant,
            person=person,
            type="EMAIL",
            value="ada.old@example.com",
            is_primary=True,
            is_public=True,
        )

        response = self.client.patch(
            self.persons_url(person.id),
            {"email": "ada.new@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)

        contact.refresh_from_db()
        self.assertEqual(contact.value, "ada.new@example.com")
        self.assertTrue(contact.is_public)

    def test_update_person_phone_preserves_existing_public_flag(self):
        person = Person.objects.create(
            tenant=self.tenant,
            full_name="Phone Existing",
            phone="+4711111111",
            municipality="Tromsø",
        )
        contact = PersonContact.objects.create(
            tenant=self.tenant,
            person=person,
            type="PHONE",
            value="+4711111111",
            is_primary=True,
            is_public=True,
        )

        response = self.client.patch(
            self.persons_url(person.id),
            {"phone": "+4722222222"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)

        contact.refresh_from_db()
        self.assertEqual(contact.value, "+4722222222")
        self.assertTrue(contact.is_public)


class RepairPersonContactsCommandTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Repair Tenant", slug="repair-tenant")

    def test_dry_run_does_not_change_database(self):
        Person.objects.create(
            tenant=self.tenant,
            full_name="Missing Contact",
            email="missing@example.com",
        )

        out = StringIO()
        call_command("repair_person_contacts", stdout=out)

        self.assertIn("mode=DRY-RUN", out.getvalue())
        self.assertIn("contacts_to_create=1", out.getvalue())
        self.assertEqual(PersonContact.objects.count(), 0)

    def test_apply_creates_missing_private_primary_contact(self):
        person = Person.objects.create(
            tenant=self.tenant,
            full_name="Missing Contact",
            email="missing@example.com",
        )

        out = StringIO()
        call_command("repair_person_contacts", "--apply", stdout=out)

        contact = PersonContact.objects.get(person=person, type="EMAIL", is_primary=True)
        self.assertEqual(contact.value, "missing@example.com")
        self.assertFalse(contact.is_public)
        self.assertIn("changes_applied=1", out.getvalue())

    def test_apply_is_idempotent(self):
        Person.objects.create(
            tenant=self.tenant,
            full_name="Missing Contact",
            email="missing@example.com",
        )

        call_command("repair_person_contacts", "--apply", stdout=StringIO())
        out = StringIO()
        call_command("repair_person_contacts", "--apply", stdout=out)

        self.assertEqual(PersonContact.objects.count(), 1)
        self.assertIn("contacts_to_create=0", out.getvalue())
        self.assertIn("changes_applied=0", out.getvalue())

    def test_phone_dry_run_finds_missing_contact_without_exposing_value(self):
        private_phone = "+4799990000"
        Person.objects.create(
            tenant=self.tenant,
            full_name="Phone Missing",
            phone=private_phone,
        )

        out = StringIO()
        call_command("repair_person_contacts", "--contact-type", "PHONE", stdout=out)

        self.assertIn("mode=DRY-RUN", out.getvalue())
        self.assertIn("contact_type=PHONE", out.getvalue())
        self.assertIn("contacts_to_create=1", out.getvalue())
        self.assertNotIn(private_phone, out.getvalue())
        self.assertFalse(PersonContact.objects.exists())

    def test_phone_apply_creates_one_private_primary_contact_and_is_idempotent(self):
        person = Person.objects.create(
            tenant=self.tenant,
            full_name="Phone Missing",
            phone="+4799990001",
        )

        call_command(
            "repair_person_contacts",
            "--contact-type",
            "PHONE",
            "--apply",
            stdout=StringIO(),
        )
        contact = PersonContact.objects.get(person=person, type="PHONE")
        self.assertTrue(contact.is_primary)
        self.assertFalse(contact.is_public)

        out = StringIO()
        call_command(
            "repair_person_contacts",
            "--contact-type",
            "PHONE",
            "--apply",
            stdout=out,
        )
        self.assertEqual(PersonContact.objects.filter(person=person, type="PHONE").count(), 1)
        self.assertIn("contacts_to_create=0", out.getvalue())
        self.assertIn("changes_applied=0", out.getvalue())

    def test_phone_repair_can_be_limited_to_tenant(self):
        other_tenant = Tenant.objects.create(name="Other Tenant", slug="other-tenant")
        included = Person.objects.create(
            tenant=self.tenant,
            full_name="Included",
            phone="+4799990002",
        )
        excluded = Person.objects.create(
            tenant=other_tenant,
            full_name="Excluded",
            phone="+4799990003",
        )

        call_command(
            "repair_person_contacts",
            "--contact-type",
            "PHONE",
            "--tenant",
            self.tenant.slug,
            "--apply",
            stdout=StringIO(),
        )

        self.assertTrue(PersonContact.objects.filter(person=included, type="PHONE").exists())
        self.assertFalse(PersonContact.objects.filter(person=excluded, type="PHONE").exists())

    def test_phone_repair_reports_primary_value_mismatch_without_change(self):
        person = Person.objects.create(
            tenant=self.tenant,
            full_name="Mismatch",
            phone="+4799990004",
        )
        primary = PersonContact.objects.create(
            tenant=self.tenant,
            person=person,
            type="PHONE",
            value="+4799990005",
            is_primary=True,
            is_public=True,
        )

        out = StringIO()
        call_command(
            "repair_person_contacts",
            "--contact-type",
            "PHONE",
            "--apply",
            stdout=out,
        )

        primary.refresh_from_db()
        self.assertEqual(primary.value, "+4799990005")
        self.assertTrue(primary.is_public)
        self.assertIn("value_mismatches=1", out.getvalue())
        self.assertIn("changes_applied=0", out.getvalue())

    def test_phone_repair_reports_matching_non_primary_without_change(self):
        person = Person.objects.create(
            tenant=self.tenant,
            full_name="Non Primary",
            phone="+4799990006",
        )
        contact = PersonContact.objects.create(
            tenant=self.tenant,
            person=person,
            type="PHONE",
            value="+4799990006",
            is_primary=False,
            is_public=False,
        )

        out = StringIO()
        call_command(
            "repair_person_contacts",
            "--contact-type",
            "PHONE",
            "--apply",
            stdout=out,
        )

        contact.refresh_from_db()
        self.assertFalse(contact.is_primary)
        self.assertFalse(contact.is_public)
        self.assertIn("matching_non_primary_conflicts=1", out.getvalue())
        self.assertIn("changes_applied=0", out.getvalue())

    def test_phone_repair_reports_multiple_primaries_without_change(self):
        person = Person.objects.create(
            tenant=self.tenant,
            full_name="Multiple Primary",
            phone="+4799990007",
        )
        first = PersonContact.objects.create(
            tenant=self.tenant,
            person=person,
            type="PHONE",
            value="+4799990007",
            is_primary=True,
            is_public=False,
        )
        second = PersonContact.objects.create(
            tenant=self.tenant,
            person=person,
            type="PHONE",
            value="+4799990008",
            is_primary=True,
            is_public=True,
        )

        out = StringIO()
        call_command(
            "repair_person_contacts",
            "--contact-type",
            "PHONE",
            "--apply",
            stdout=out,
        )

        first.refresh_from_db()
        second.refresh_from_db()
        self.assertFalse(first.is_public)
        self.assertTrue(second.is_public)
        self.assertIn("multiple_primary_conflicts=1", out.getvalue())
        self.assertIn("changes_applied=0", out.getvalue())

    def test_phone_repair_does_not_change_email_contacts(self):
        person = Person.objects.create(
            tenant=self.tenant,
            full_name="Separate Types",
            email="separate@example.com",
            phone="+4799990009",
        )
        email = PersonContact.objects.create(
            tenant=self.tenant,
            person=person,
            type="EMAIL",
            value="separate@example.com",
            is_primary=True,
            is_public=True,
        )

        call_command(
            "repair_person_contacts",
            "--contact-type",
            "PHONE",
            "--apply",
            stdout=StringIO(),
        )

        email.refresh_from_db()
        self.assertTrue(email.is_primary)
        self.assertTrue(email.is_public)


class PublishExistingEmailContactsCommandTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Publish Tenant", slug="publish-tenant")
        self.nordland = Organization.objects.create(tenant=self.tenant, name="Nordland fylkeskommune")
        self.badin = Organization.objects.create(tenant=self.tenant, name="Bådin")
        self.other_org = Organization.objects.create(tenant=self.tenant, name="Annen aktør")
        self.kathrine = self._person("Kathrine Schjem", "kathrine@example.com")
        self.ole = self._person("Ole-Thomas Kolberg", "ole@example.com")
        self.jonas = self._person("Jonas Jørgensen Moe", "jonas@example.com")
        self.public_elsewhere = self._person("Public Elsewhere", "public@example.com")

        self.kathrine_link = self._link(self.nordland, self.kathrine, publish_person=True)
        self.ole_link = self._link(self.nordland, self.ole, publish_person=True)
        self.jonas_link = self._link(self.badin, self.jonas, publish_person=True)
        self.other_link = self._link(self.other_org, self.public_elsewhere, publish_person=False)
        self.same_person_other_link = self._link(self.other_org, self.jonas, publish_person=False)

    def _person(self, name, email):
        person = Person.objects.create(tenant=self.tenant, full_name=name, email=email)
        PersonContact.objects.create(
            tenant=self.tenant,
            person=person,
            type="EMAIL",
            value=email,
            is_primary=True,
            is_public=False,
        )
        return person

    def _link(self, organization, person, *, publish_person):
        return OrganizationPerson.objects.create(
            tenant=self.tenant,
            organization=organization,
            person=person,
            status="ACTIVE",
            publish_person=publish_person,
        )

    def test_dry_run_does_not_change_database(self):
        out = StringIO()

        call_command("publish_existing_email_contacts", stdout=out)

        self.assertIn("mode=DRY-RUN", out.getvalue())
        self.assertIn("email_contacts_to_publish=4", out.getvalue())
        self.assertIn("active_links_to_change=5", out.getvalue())
        self.assertEqual(PersonContact.objects.filter(is_public=True).count(), 0)
        self.other_link.refresh_from_db()
        self.assertFalse(self.other_link.publish_person)

    def test_apply_publishes_email_contacts_and_active_links_except_exceptions(self):
        out = StringIO()

        call_command("publish_existing_email_contacts", "--apply", stdout=out)

        self.assertEqual(PersonContact.objects.filter(type="EMAIL", is_public=True).count(), 4)
        self.kathrine_link.refresh_from_db()
        self.ole_link.refresh_from_db()
        self.jonas_link.refresh_from_db()
        self.other_link.refresh_from_db()
        self.same_person_other_link.refresh_from_db()
        self.assertFalse(self.kathrine_link.publish_person)
        self.assertFalse(self.ole_link.publish_person)
        self.assertFalse(self.jonas_link.publish_person)
        self.assertTrue(self.other_link.publish_person)
        self.assertTrue(self.same_person_other_link.publish_person)
        self.assertIn("exception_links_to_unpublish=3", out.getvalue())

    def test_same_exception_person_can_be_public_at_another_organization(self):
        call_command("publish_existing_email_contacts", "--apply", stdout=StringIO())

        self.jonas_link.refresh_from_db()
        self.same_person_other_link.refresh_from_db()

        self.assertFalse(self.jonas_link.publish_person)
        self.assertTrue(self.same_person_other_link.publish_person)

    def test_phone_public_status_is_unchanged(self):
        phone = PersonContact.objects.create(
            tenant=self.tenant,
            person=self.public_elsewhere,
            type="PHONE",
            value="+4711111111",
            is_primary=True,
            is_public=False,
        )

        call_command("publish_existing_email_contacts", "--apply", stdout=StringIO())

        phone.refresh_from_db()
        self.assertFalse(phone.is_public)

    def test_apply_is_idempotent(self):
        call_command("publish_existing_email_contacts", "--apply", stdout=StringIO())
        out = StringIO()

        call_command("publish_existing_email_contacts", "--apply", stdout=out)

        self.assertIn("email_contacts_to_publish=0", out.getvalue())
        self.assertIn("active_links_to_change=0", out.getvalue())
        self.assertIn("changes_applied=0", out.getvalue())

    def test_command_aborts_when_exception_does_not_resolve_uniquely(self):
        self.kathrine.full_name = "Kathrine Skjem"
        self.kathrine.save(update_fields=["full_name"])

        with self.assertRaises(CommandError):
            call_command("publish_existing_email_contacts", "--apply", stdout=StringIO())

        self.assertEqual(PersonContact.objects.filter(is_public=True).count(), 0)


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
            title="Daglig leder",
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
        self.public_email_contact = PersonContact.objects.create(
            tenant=self.tag.tenant,
            person=self.person,
            type="EMAIL",
            value="ada.public@example.com",
            is_primary=True,
            is_public=True,
        )
        self.private_email_contact = PersonContact.objects.create(
            tenant=self.tag.tenant,
            person=self.person,
            type="EMAIL",
            value="ada.private@example.com",
            is_public=False,
        )
        self.public_phone_contact = PersonContact.objects.create(
            tenant=self.tag.tenant,
            person=self.person,
            type="PHONE",
            value="+4744444444",
            is_primary=True,
            is_public=True,
        )

        self.hidden_organization = Organization.objects.create(
            tenant=self.tag.tenant,
            name="Skjult aktør",
            org_number="987654321",
            is_published=False,
        )

    def detail_url(self, organization):
        return reverse("public-actor-detail", kwargs={"actor_id": organization.id})

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
        response = self.client.get(self.detail_url(self.organization))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Etablert")
        self.assertContains(response, "PUBLIK KATEGORI")
        self.assertContains(response, "Publik underkategori")

    def test_public_actor_detail_uses_public_contacts_without_direct_field_fallback(self):
        response = self.client.get(self.detail_url(self.organization))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ada Artist")
        self.assertContains(response, "ada.public@example.com")
        self.assertContains(response, "+4744444444")
        self.assertNotContains(response, "ada@example.com")
        self.assertNotContains(response, "ada.private@example.com")
        self.assertNotContains(response, "+4712345678")

    def test_public_api_uses_same_contact_rules_as_html(self):
        response = self.client.get(f"/api/public/actors/{self.organization.org_number}/")
        self.assertEqual(response.status_code, 200, response.content)

        people = response.json()["people"]
        ada = next(person for person in people if person["full_name"] == "Ada Artist")
        self.assertEqual(ada["title"], "Daglig leder")
        values = {contact["value"] for contact in ada["public_contacts"]}
        self.assertIn("ada.public@example.com", values)
        self.assertIn("+4744444444", values)
        self.assertNotIn("ada@example.com", values)
        self.assertNotIn("ada.private@example.com", values)
        self.assertNotIn("+4712345678", values)

    def test_public_title_is_shown_in_api_and_html(self):
        api_response = self.client.get(f"/api/public/actors/{self.organization.org_number}/")
        html_response = self.client.get(self.detail_url(self.organization))

        self.assertEqual(api_response.status_code, 200, api_response.content)
        self.assertEqual(html_response.status_code, 200)
        ada = next(person for person in api_response.json()["people"] if person["full_name"] == "Ada Artist")
        self.assertEqual(ada["title"], "Daglig leder")
        self.assertContains(html_response, '<p class="person-title">Daglig leder</p>', html=True)

    def test_missing_public_title_is_omitted_cleanly(self):
        self.person.title = ""
        self.person.save(update_fields=["title"])

        api_response = self.client.get(f"/api/public/actors/{self.organization.org_number}/")
        html_response = self.client.get(self.detail_url(self.organization))

        self.assertEqual(api_response.status_code, 200, api_response.content)
        self.assertEqual(html_response.status_code, 200)
        ada = next(person for person in api_response.json()["people"] if person["full_name"] == "Ada Artist")
        self.assertNotIn("title", ada)
        self.assertNotContains(html_response, 'class="person-title"')

    def test_public_api_does_not_fallback_to_person_email_without_public_contact(self):
        self.public_email_contact.delete()

        response = self.client.get(f"/api/public/actors/{self.organization.org_number}/")
        self.assertEqual(response.status_code, 200, response.content)

        ada = next(person for person in response.json()["people"] if person["full_name"] == "Ada Artist")
        values = {contact["value"] for contact in ada["public_contacts"]}
        self.assertNotIn("ada@example.com", values)
        self.assertNotIn("ada.private@example.com", values)

    def test_publish_person_false_hides_person_even_with_public_contact(self):
        self.link.publish_person = False
        self.link.save(update_fields=["publish_person"])

        api_response = self.client.get(f"/api/public/actors/{self.organization.org_number}/")
        html_response = self.client.get(self.detail_url(self.organization))

        self.assertEqual(api_response.status_code, 200, api_response.content)
        self.assertEqual(html_response.status_code, 200)
        self.assertEqual(api_response.json()["people"], [])
        self.assertNotContains(html_response, "Ada Artist")

    def test_inactive_link_hides_person_even_with_public_phone(self):
        self.link.status = "INACTIVE"
        self.link.save(update_fields=["status"])

        api_response = self.client.get(f"/api/public/actors/{self.organization.org_number}/")
        html_response = self.client.get(self.detail_url(self.organization))

        self.assertEqual(api_response.status_code, 200, api_response.content)
        self.assertEqual(html_response.status_code, 200)
        self.assertEqual(api_response.json()["people"], [])
        self.assertNotContains(html_response, "Ada Artist")

    def test_public_actor_templates_ignore_favicon_fallback_urls(self):
        self.organization.og_image_url = fallback_preview_image(self.organization.website_url)
        self.organization.save(update_fields=["og_image_url"])

        list_response = self.client.get("/public/actors/")
        detail_response = self.client.get(self.detail_url(self.organization))

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

    def test_public_actor_list_links_to_canonical_id_detail_url(self):
        response = self.client.get("/public/actors/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'href="{self.detail_url(self.organization)}"')
        self.assertNotContains(response, f"/public/actors/{self.organization.org_number}/")

    def test_public_actor_detail_works_without_org_number(self):
        self.organization.org_number = None
        self.organization.save(update_fields=["org_number"])

        list_response = self.client.get("/public/actors/")
        detail_response = self.client.get(self.detail_url(self.organization))

        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, f'href="{self.detail_url(self.organization)}"')
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, "Nordlyd")

    def test_public_actor_detail_works_with_url_unsafe_org_number(self):
        self.organization.org_number = "123 456/789?"
        self.organization.save(update_fields=["org_number"])

        response = self.client.get(self.detail_url(self.organization))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nordlyd")

    def test_all_public_actor_card_links_return_detail_pages(self):
        Organization.objects.create(
            tenant=self.tag.tenant,
            name="Aktør uten orgnummer",
            org_number=None,
            is_published=True,
        )

        response = self.client.get("/public/actors/")
        hrefs = []
        for part in response.content.decode().split('href="')[1:]:
            href = part.split('"', 1)[0]
            if href.startswith("/public/actors/id/"):
                hrefs.append(href)

        self.assertGreaterEqual(len(hrefs), 2)
        for href in hrefs:
            detail_response = self.client.get(href)
            self.assertEqual(detail_response.status_code, 200, href)

    def test_public_actor_canonical_detail_shows_correct_actor(self):
        other = Organization.objects.create(
            tenant=self.tag.tenant,
            name="Annen synlig aktør",
            org_number=None,
            is_published=True,
        )

        response = self.client.get(self.detail_url(other))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Annen synlig aktør")
        self.assertNotContains(response, "Nordlyd")

    def test_public_actor_canonical_detail_hides_unpublished_actor(self):
        response = self.client.get(self.detail_url(self.hidden_organization))

        self.assertEqual(response.status_code, 404)

    def test_public_actor_legacy_org_number_redirects_to_canonical_detail(self):
        response = self.client.get(f"/public/actors/{self.organization.org_number}/")

        self.assertEqual(response.status_code, 301)
        self.assertEqual(response["Location"], self.detail_url(self.organization))

    def test_check_public_actor_links_command_reports_no_broken_links(self):
        Organization.objects.create(
            tenant=self.tag.tenant,
            name="Aktør uten orgnummer",
            org_number=None,
            is_published=True,
        )
        out = StringIO()

        call_command("check_public_actor_links", stdout=out)

        self.assertIn("broken_links=0", out.getvalue())


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


class ImageStorageKeyValidatorTests(SimpleTestCase):
    def test_accepts_provider_neutral_relative_key(self):
        validate_storage_key("tenants/42/assets/ab/cd/original.webp")

    def test_rejects_unsafe_storage_keys(self):
        invalid_keys = (
            "",
            "/absolute/key.webp",
            "C:/absolute/key.webp",
            "tenant\\asset.webp",
            "./asset.webp",
            "tenant/../asset.webp",
            "tenant//asset.webp",
            "tenant/asset\n.webp",
        )

        for storage_key in invalid_keys:
            with self.subTest(storage_key=repr(storage_key)):
                with self.assertRaises(ValidationError):
                    validate_storage_key(storage_key)


class ImageDomainModelTests(TestCase):
    checksum_a = "a" * 64
    checksum_b = "b" * 64
    checksum_c = "c" * 64

    def setUp(self):
        self.tenant = Tenant.objects.create(name="Image tenant", slug="image-tenant")
        self.other_tenant = Tenant.objects.create(name="Other image tenant", slug="other-image-tenant")

    def create_asset(self, *, tenant=None, storage_key="assets/original.jpeg", checksum=None, **overrides):
        values = {
            "tenant": tenant or self.tenant,
            "private_storage_key": storage_key,
            "checksum_sha256": checksum or self.checksum_a,
            "original_format": ImageAsset.OriginalFormat.JPEG,
            "mime_type": "image/jpeg",
            "width": 1600,
            "height": 900,
            "file_size_bytes": 123456,
            "validation_version": "validation-v1",
        }
        values.update(overrides)
        return ImageAsset.objects.create(**values)

    def create_rendition_set(self, *, asset=None, tenant=None, render_hash=None, **overrides):
        asset = asset or self.create_asset()
        values = {
            "tenant": tenant or self.tenant,
            "asset": asset,
            "fit_mode": ImageRenditionSet.FitMode.COVER,
            "processing_version": "processing-v1",
            "render_config_hash_sha256": render_hash or self.checksum_b,
        }
        values.update(overrides)
        return ImageRenditionSet.objects.create(**values)

    def create_rendition(
        self,
        *,
        rendition_set=None,
        tenant=None,
        variant=ImageRendition.Variant.SQUARE,
        storage_key="renditions/square.webp",
        checksum=None,
        **overrides,
    ):
        rendition_set = rendition_set or self.create_rendition_set()
        values = {
            "tenant": tenant or self.tenant,
            "rendition_set": rendition_set,
            "variant": variant,
            "output_format": ImageRendition.OutputFormat.WEBP,
            "width": 512,
            "height": 512,
            "file_size_bytes": 45678,
            "checksum_sha256": checksum or self.checksum_c,
            "artifact_storage_key": storage_key,
        }
        values.update(overrides)
        return ImageRendition.objects.create(**values)

    def test_models_use_integer_primary_keys_and_no_file_fields_or_organization_relation(self):
        for model in (ImageAsset, ImageRenditionSet, ImageRendition):
            with self.subTest(model=model.__name__):
                self.assertEqual(model._meta.pk.get_internal_type(), "BigAutoField")
                self.assertNotIn("organization", {field.name for field in model._meta.fields})
                self.assertFalse(
                    any(field.get_internal_type() == "FileField" for field in model._meta.fields)
                )

    def test_contract_fields_are_required_and_non_null(self):
        required_fields = {
            ImageAsset: {
                "tenant",
                "private_storage_key",
                "checksum_sha256",
                "original_format",
                "mime_type",
                "width",
                "height",
                "file_size_bytes",
                "validation_version",
            },
            ImageRenditionSet: {
                "tenant",
                "asset",
                "fit_mode",
                "focus_x",
                "focus_y",
                "processing_version",
                "render_config_hash_sha256",
            },
            ImageRendition: {
                "tenant",
                "rendition_set",
                "variant",
                "output_format",
                "width",
                "height",
                "file_size_bytes",
                "checksum_sha256",
                "artifact_storage_key",
            },
        }

        for model, field_names in required_fields.items():
            for field_name in field_names:
                with self.subTest(model=model.__name__, field_name=field_name):
                    field = model._meta.get_field(field_name)
                    self.assertFalse(field.null)
                    self.assertFalse(field.blank)

    def test_model_choice_fields_reject_values_outside_the_contract(self):
        asset = ImageAsset(
            tenant=self.tenant,
            private_storage_key="assets/invalid-format.gif",
            checksum_sha256=self.checksum_a,
            original_format="gif",
            mime_type="image/gif",
            width=100,
            height=100,
            file_size_bytes=100,
            validation_version="validation-v1",
        )
        with self.assertRaises(ValidationError) as asset_error:
            asset.full_clean()
        self.assertIn("original_format", asset_error.exception.message_dict)

        valid_asset = self.create_asset()
        rendition_set = ImageRenditionSet(
            tenant=self.tenant,
            asset=valid_asset,
            fit_mode="stretch",
            processing_version="processing-v1",
            render_config_hash_sha256=self.checksum_b,
        )
        with self.assertRaises(ValidationError) as set_error:
            rendition_set.full_clean()
        self.assertIn("fit_mode", set_error.exception.message_dict)

        valid_set = self.create_rendition_set(asset=valid_asset)
        rendition = ImageRendition(
            tenant=self.tenant,
            rendition_set=valid_set,
            variant="portrait",
            output_format="gif",
            width=100,
            height=100,
            file_size_bytes=100,
            checksum_sha256=self.checksum_c,
            artifact_storage_key="renditions/invalid.gif",
        )
        with self.assertRaises(ValidationError) as rendition_error:
            rendition.full_clean()
        self.assertIn("variant", rendition_error.exception.message_dict)
        self.assertIn("output_format", rendition_error.exception.message_dict)

    def test_image_asset_accepts_all_formats_with_matching_mime_types(self):
        format_mime_pairs = (
            (ImageAsset.OriginalFormat.JPEG, "image/jpeg"),
            (ImageAsset.OriginalFormat.PNG, "image/png"),
            (ImageAsset.OriginalFormat.WEBP, "image/webp"),
        )

        for index, (original_format, mime_type) in enumerate(format_mime_pairs):
            with self.subTest(original_format=original_format):
                asset = ImageAsset(
                    tenant=self.tenant,
                    private_storage_key=f"assets/original-{index}.{original_format}",
                    checksum_sha256=chr(ord("a") + index) * 64,
                    original_format=original_format,
                    mime_type=mime_type,
                    width=1,
                    height=1,
                    file_size_bytes=1,
                    validation_version="validation-v1",
                )
                asset.full_clean()

    def test_image_asset_rejects_mime_mismatch_and_invalid_checksum(self):
        mismatch = ImageAsset(
            tenant=self.tenant,
            private_storage_key="assets/mismatch.png",
            checksum_sha256=self.checksum_a,
            original_format=ImageAsset.OriginalFormat.PNG,
            mime_type="image/jpeg",
            width=100,
            height=100,
            file_size_bytes=100,
            validation_version="validation-v1",
        )
        with self.assertRaises(ValidationError) as mismatch_error:
            mismatch.full_clean()
        self.assertIn("mime_type", mismatch_error.exception.message_dict)

        invalid_checksum = ImageAsset(
            tenant=self.tenant,
            private_storage_key="assets/uppercase.jpeg",
            checksum_sha256="A" * 64,
            original_format=ImageAsset.OriginalFormat.JPEG,
            mime_type="image/jpeg",
            width=100,
            height=100,
            file_size_bytes=100,
            validation_version="validation-v1",
        )
        with self.assertRaises(ValidationError) as checksum_error:
            invalid_checksum.full_clean()
        self.assertIn("checksum_sha256", checksum_error.exception.message_dict)

    def test_image_asset_storage_key_is_unique_per_tenant_but_checksum_is_not(self):
        self.create_asset()
        self.create_asset(storage_key="assets/copy.jpeg", checksum=self.checksum_a)
        self.create_asset(tenant=self.other_tenant, storage_key="assets/original.jpeg")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.create_asset(storage_key="assets/original.jpeg", checksum=self.checksum_b)

    def test_image_asset_dimensions_and_size_must_be_positive(self):
        for field_name, invalid_value in (
            ("width", 0),
            ("width", -1),
            ("height", 0),
            ("height", -1),
            ("file_size_bytes", 0),
            ("file_size_bytes", -1),
        ):
            with self.subTest(field_name=field_name, invalid_value=invalid_value):
                with self.assertRaises(IntegrityError):
                    with transaction.atomic():
                        self.create_asset(
                            storage_key=f"assets/{field_name}-{invalid_value}.jpeg",
                            **{field_name: invalid_value},
                        )

    def test_rendition_set_defaults_choices_uniqueness_and_asset_protection(self):
        asset = self.create_asset()
        rendition_set = self.create_rendition_set(asset=asset)
        self.assertEqual(rendition_set.focus_x, 0.5)
        self.assertEqual(rendition_set.focus_y, 0.5)
        self.assertEqual(
            set(ImageRenditionSet.FitMode.values),
            {"cover", "contain"},
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.create_rendition_set(asset=asset, render_hash=self.checksum_b)
        with self.assertRaises(ProtectedError):
            asset.delete()

    def test_rendition_set_allows_same_hash_for_different_asset(self):
        first_asset = self.create_asset()
        second_asset = self.create_asset(storage_key="assets/second.jpeg", checksum=self.checksum_b)
        self.create_rendition_set(asset=first_asset, render_hash=self.checksum_c)
        self.create_rendition_set(asset=second_asset, render_hash=self.checksum_c)

    def test_rendition_set_rejects_cross_tenant_asset_in_clean(self):
        asset = self.create_asset(tenant=self.other_tenant)
        rendition_set = ImageRenditionSet(
            tenant=self.tenant,
            asset=asset,
            fit_mode=ImageRenditionSet.FitMode.CONTAIN,
            processing_version="processing-v1",
            render_config_hash_sha256=self.checksum_b,
        )

        with self.assertRaises(ValidationError) as error:
            rendition_set.full_clean()
        self.assertIn("asset", error.exception.message_dict)

    def test_rendition_set_focus_is_inclusive_and_database_constrained(self):
        lower = self.create_rendition_set(focus_x=0, focus_y=0)
        upper_asset = self.create_asset(storage_key="assets/upper.jpeg", checksum=self.checksum_b)
        upper = self.create_rendition_set(
            asset=upper_asset,
            render_hash=self.checksum_c,
            focus_x=1,
            focus_y=1,
        )
        self.assertEqual(lower.focus_x, 0)
        self.assertEqual(upper.focus_y, 1)

        for field_name, invalid_value in (("focus_x", -0.0001), ("focus_x", 1.0001), ("focus_y", -0.0001), ("focus_y", 1.0001)):
            with self.subTest(field_name=field_name, invalid_value=invalid_value):
                asset = self.create_asset(
                    storage_key=f"assets/{field_name}-{str(invalid_value).replace('.', '_')}.jpeg",
                    checksum=self.checksum_c,
                )
                with self.assertRaises(IntegrityError):
                    with transaction.atomic():
                        self.create_rendition_set(
                            asset=asset,
                            render_hash=self.checksum_a,
                            **{field_name: invalid_value},
                        )

    def test_rendition_choices_uniqueness_and_rendition_set_protection(self):
        rendition_set = self.create_rendition_set()
        self.create_rendition(rendition_set=rendition_set)
        self.assertEqual(
            set(ImageRendition.Variant.values),
            {"square", "landscape", "share"},
        )
        self.assertEqual(
            set(ImageRendition.OutputFormat.values),
            {"jpeg", "png", "webp"},
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.create_rendition(
                    rendition_set=rendition_set,
                    variant=ImageRendition.Variant.SQUARE,
                    storage_key="renditions/other-square.webp",
                )
        with self.assertRaises(ProtectedError):
            rendition_set.delete()

    def test_rendition_artifact_key_is_unique_per_tenant_but_checksum_is_not(self):
        first_set = self.create_rendition_set()
        second_asset = self.create_asset(storage_key="assets/second.jpeg", checksum=self.checksum_b)
        second_set = self.create_rendition_set(asset=second_asset, render_hash=self.checksum_c)
        self.create_rendition(rendition_set=first_set, checksum=self.checksum_a)
        self.create_rendition(
            rendition_set=second_set,
            variant=ImageRendition.Variant.LANDSCAPE,
            storage_key="renditions/landscape.webp",
            checksum=self.checksum_a,
        )

        third_asset = self.create_asset(storage_key="assets/third.jpeg", checksum=self.checksum_c)
        third_set = self.create_rendition_set(asset=third_asset, render_hash=self.checksum_a)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.create_rendition(
                    rendition_set=third_set,
                    variant=ImageRendition.Variant.SHARE,
                    storage_key="renditions/square.webp",
                )

        other_asset = self.create_asset(
            tenant=self.other_tenant,
            storage_key="assets/other.jpeg",
        )
        other_set = self.create_rendition_set(
            tenant=self.other_tenant,
            asset=other_asset,
            render_hash=self.checksum_b,
        )
        self.create_rendition(
            tenant=self.other_tenant,
            rendition_set=other_set,
            storage_key="renditions/square.webp",
        )

    def test_rendition_rejects_cross_tenant_set_and_invalid_checksum_in_clean(self):
        other_asset = self.create_asset(tenant=self.other_tenant)
        other_set = self.create_rendition_set(
            tenant=self.other_tenant,
            asset=other_asset,
        )
        rendition = ImageRendition(
            tenant=self.tenant,
            rendition_set=other_set,
            variant=ImageRendition.Variant.SHARE,
            output_format=ImageRendition.OutputFormat.JPEG,
            width=1200,
            height=630,
            file_size_bytes=100,
            checksum_sha256="C" * 64,
            artifact_storage_key="renditions/share.jpeg",
        )

        with self.assertRaises(ValidationError) as error:
            rendition.full_clean()
        self.assertIn("rendition_set", error.exception.message_dict)
        self.assertIn("checksum_sha256", error.exception.message_dict)

    def test_rendition_dimensions_and_size_must_be_positive(self):
        rendition_set = self.create_rendition_set()
        for index, (field_name, invalid_value) in enumerate(
            (
                ("width", 0),
                ("width", -1),
                ("height", 0),
                ("height", -1),
                ("file_size_bytes", 0),
                ("file_size_bytes", -1),
            )
        ):
            with self.subTest(field_name=field_name, invalid_value=invalid_value):
                with self.assertRaises(IntegrityError):
                    with transaction.atomic():
                        self.create_rendition(
                            rendition_set=rendition_set,
                            variant=(
                                ImageRendition.Variant.SQUARE,
                                ImageRendition.Variant.LANDSCAPE,
                                ImageRendition.Variant.SHARE,
                            )[index % 3],
                            storage_key=f"renditions/{field_name}-{index}.webp",
                            **{field_name: invalid_value},
                        )

    def test_model_operations_do_not_create_storage_directories_or_files(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            private_root = Path(temporary_directory) / "private"
            public_root = Path(temporary_directory) / "public"
            with override_settings(
                IMAGE_ORIGINALS_ROOT=private_root,
                IMAGE_RENDITIONS_ROOT=public_root,
            ):
                asset = self.create_asset()
                rendition_set = self.create_rendition_set(asset=asset)
                self.create_rendition(rendition_set=rendition_set)

            self.assertFalse(private_root.exists())
            self.assertFalse(public_root.exists())
            self.assertEqual(list(Path(temporary_directory).iterdir()), [])


class ImageDomainMigrationTests(TransactionTestCase):
    migrate_from = ("crm", "0020_tenantmembership")
    migrate_to = ("crm", "0021_image_domain_foundation")

    def test_migration_preserves_existing_tenant_and_organization_data_and_is_reversible(self):
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        old_apps = executor.loader.project_state([self.migrate_from]).apps
        OldTenant = old_apps.get_model("crm", "Tenant")
        OldOrganization = old_apps.get_model("crm", "Organization")
        tenant = OldTenant.objects.create(name="Migration tenant", slug="migration-tenant")
        organization = OldOrganization.objects.create(tenant=tenant, name="Existing organization")

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        new_apps = executor.loader.project_state([self.migrate_to]).apps
        NewTenant = new_apps.get_model("crm", "Tenant")
        NewOrganization = new_apps.get_model("crm", "Organization")
        self.assertTrue(NewTenant.objects.filter(pk=tenant.pk, slug="migration-tenant").exists())
        self.assertTrue(
            NewOrganization.objects.filter(pk=organization.pk, name="Existing organization").exists()
        )
        for model_name in ("ImageAsset", "ImageRenditionSet", "ImageRendition"):
            self.assertIsNotNone(new_apps.get_model("crm", model_name))

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        restored_apps = executor.loader.project_state([self.migrate_from]).apps
        RestoredTenant = restored_apps.get_model("crm", "Tenant")
        RestoredOrganization = restored_apps.get_model("crm", "Organization")
        self.assertTrue(RestoredTenant.objects.filter(pk=tenant.pk).exists())
        self.assertTrue(RestoredOrganization.objects.filter(pk=organization.pk).exists())

        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())


# Keep the focused release-domain test cases visible to CI's explicit `crm.tests` label.
from .test_image_releases import (  # noqa: E402, F401
    OrganizationImageReleaseMigrationTests,
    OrganizationImageReleaseTests,
    PublicReleaseKeyBuilderTests,
)


class OrganizationImageSelectionModelTests(TestCase):
    checksum_a = "a" * 64
    checksum_b = "b" * 64

    def setUp(self):
        self.tenant = Tenant.objects.create(name="Selection tenant", slug="selection-tenant")
        self.other_tenant = Tenant.objects.create(
            name="Other selection tenant",
            slug="other-selection-tenant",
        )
        self.organization = Organization.objects.create(
            tenant=self.tenant,
            name="Selection organization",
        )
        self.other_organization = Organization.objects.create(
            tenant=self.other_tenant,
            name="Other selection organization",
        )
        self.user = get_user_model().objects.create_user(
            username="selection-locker",
            password="test-password",
        )

    def create_asset(self, *, tenant=None, storage_key="assets/selection.jpeg", checksum=None):
        return ImageAsset.objects.create(
            tenant=tenant or self.tenant,
            private_storage_key=storage_key,
            checksum_sha256=checksum or self.checksum_a,
            original_format=ImageAsset.OriginalFormat.JPEG,
            mime_type="image/jpeg",
            width=1600,
            height=900,
            file_size_bytes=123456,
            validation_version="validation-v1",
        )

    def create_rendition_set(
        self,
        *,
        tenant=None,
        asset=None,
        storage_key="assets/selection.jpeg",
        checksum=None,
        render_hash=None,
    ):
        tenant = tenant or self.tenant
        asset = asset or self.create_asset(
            tenant=tenant,
            storage_key=storage_key,
            checksum=checksum,
        )
        return ImageRenditionSet.objects.create(
            tenant=tenant,
            asset=asset,
            fit_mode=ImageRenditionSet.FitMode.COVER,
            processing_version="processing-v1",
            render_config_hash_sha256=render_hash or self.checksum_b,
        )

    def create_selection(self, **overrides):
        values = {
            "tenant": self.tenant,
            "organization": self.organization,
            "selection_kind": OrganizationImageSelection.SelectionKind.ASSET,
            "alt_text": "Organization image",
            "public_credit": "",
            "revision": 1,
            "status": OrganizationImageSelection.Status.ACTIVE,
            "locked_by": self.user,
            "locked_at": timezone.now(),
        }
        values.update(overrides)
        if "rendition_set" not in overrides:
            values["rendition_set"] = self.create_rendition_set()
        return OrganizationImageSelection.objects.create(**values)

    def test_valid_active_asset_selection_references_exact_set_and_asset(self):
        rendition_set = self.create_rendition_set()
        selection = OrganizationImageSelection(
            tenant=self.tenant,
            organization=self.organization,
            selection_kind=OrganizationImageSelection.SelectionKind.ASSET,
            rendition_set=rendition_set,
            alt_text="Organization image",
            public_credit="",
            revision=1,
            status=OrganizationImageSelection.Status.ACTIVE,
            locked_by=self.user,
            locked_at=timezone.now(),
        )

        selection.full_clean()
        selection.save()

        self.assertEqual(selection.rendition_set, rendition_set)
        self.assertEqual(selection.rendition_set.asset, rendition_set.asset)
        self.assertEqual(selection.public_credit, "")

    def test_asset_alt_text_defaults_to_blank_without_hidden_fallback(self):
        selection = OrganizationImageSelection(
            tenant=self.tenant,
            organization=self.organization,
            selection_kind=OrganizationImageSelection.SelectionKind.ASSET,
            rendition_set=self.create_rendition_set(),
            revision=1,
            status=OrganizationImageSelection.Status.ACTIVE,
            locked_by=self.user,
            locked_at=timezone.now(),
        )

        selection.full_clean()
        selection.save()
        selection.refresh_from_db()

        self.assertEqual(selection.alt_text, "")
        self.assertNotEqual(selection.alt_text, self.organization.name)

    def test_valid_active_system_fallback_selection_can_be_created(self):
        selection = OrganizationImageSelection(
            tenant=self.tenant,
            organization=self.organization,
            selection_kind=OrganizationImageSelection.SelectionKind.SYSTEM_FALLBACK,
            rendition_set=None,
            alt_text="Kreative Norge standardbilde",
            public_credit="",
            revision=1,
            status=OrganizationImageSelection.Status.ACTIVE,
            locked_by=self.user,
            locked_at=timezone.now(),
        )

        selection.full_clean()
        selection.save()

        self.assertIsNone(selection.rendition_set)

    def test_clean_rejects_invalid_asset_and_fallback_combinations(self):
        rendition_set = self.create_rendition_set()
        invalid_selections = (
            OrganizationImageSelection(
                tenant=self.tenant,
                organization=self.organization,
                selection_kind=OrganizationImageSelection.SelectionKind.ASSET,
                rendition_set=None,
                alt_text="Missing rendition set",
                revision=1,
                status=OrganizationImageSelection.Status.ACTIVE,
                locked_by=self.user,
                locked_at=timezone.now(),
            ),
            OrganizationImageSelection(
                tenant=self.tenant,
                organization=self.organization,
                selection_kind=OrganizationImageSelection.SelectionKind.SYSTEM_FALLBACK,
                rendition_set=rendition_set,
                alt_text="Unexpected rendition set",
                revision=1,
                status=OrganizationImageSelection.Status.ACTIVE,
                locked_by=self.user,
                locked_at=timezone.now(),
            ),
        )

        for selection in invalid_selections:
            with self.subTest(selection_kind=selection.selection_kind):
                with self.assertRaises(ValidationError) as error:
                    selection.full_clean()
                self.assertIn("rendition_set", error.exception.message_dict)

    def test_database_rejects_invalid_asset_and_fallback_combinations(self):
        rendition_set = self.create_rendition_set()
        invalid_values = (
            {
                "selection_kind": OrganizationImageSelection.SelectionKind.ASSET,
                "rendition_set": None,
            },
            {
                "selection_kind": OrganizationImageSelection.SelectionKind.SYSTEM_FALLBACK,
                "rendition_set": rendition_set,
            },
        )

        for index, invalid_value in enumerate(invalid_values, start=1):
            with self.subTest(invalid_value=invalid_value):
                with self.assertRaises(IntegrityError):
                    with transaction.atomic():
                        OrganizationImageSelection.objects.create(
                            tenant=self.tenant,
                            organization=self.organization,
                            alt_text="Invalid selection",
                            revision=index,
                            status=OrganizationImageSelection.Status.ARCHIVED,
                            locked_by=self.user,
                            locked_at=timezone.now(),
                            **invalid_value,
                        )

    def test_clean_rejects_cross_tenant_organization_and_rendition_set(self):
        local_set = self.create_rendition_set()
        other_set = self.create_rendition_set(
            tenant=self.other_tenant,
            storage_key="assets/other-selection.jpeg",
        )
        invalid_selections = (
            OrganizationImageSelection(
                tenant=self.tenant,
                organization=self.other_organization,
                selection_kind=OrganizationImageSelection.SelectionKind.ASSET,
                rendition_set=local_set,
                alt_text="Wrong organization tenant",
                revision=1,
                status=OrganizationImageSelection.Status.ACTIVE,
                locked_by=self.user,
                locked_at=timezone.now(),
            ),
            OrganizationImageSelection(
                tenant=self.tenant,
                organization=self.organization,
                selection_kind=OrganizationImageSelection.SelectionKind.ASSET,
                rendition_set=other_set,
                alt_text="Wrong rendition tenant",
                revision=1,
                status=OrganizationImageSelection.Status.ACTIVE,
                locked_by=self.user,
                locked_at=timezone.now(),
            ),
        )

        for selection in invalid_selections:
            with self.subTest(organization_id=selection.organization_id):
                with self.assertRaises(ValidationError) as error:
                    selection.full_clean()
                self.assertTrue(
                    {"organization", "rendition_set"}.intersection(error.exception.message_dict)
                )

    def test_database_foreign_keys_alone_do_not_guarantee_cross_tenant_match(self):
        local_set = self.create_rendition_set()
        other_set = self.create_rendition_set(
            tenant=self.other_tenant,
            storage_key="assets/other-database-selection.jpeg",
        )

        wrong_organization = OrganizationImageSelection.objects.create(
            tenant=self.tenant,
            organization=self.other_organization,
            selection_kind=OrganizationImageSelection.SelectionKind.ASSET,
            rendition_set=local_set,
            alt_text="Database boundary evidence",
            revision=1,
            status=OrganizationImageSelection.Status.ARCHIVED,
            locked_by=self.user,
            locked_at=timezone.now(),
        )
        wrong_rendition_set = OrganizationImageSelection.objects.create(
            tenant=self.tenant,
            organization=self.organization,
            selection_kind=OrganizationImageSelection.SelectionKind.ASSET,
            rendition_set=other_set,
            alt_text="Database boundary evidence",
            revision=2,
            status=OrganizationImageSelection.Status.ARCHIVED,
            locked_by=self.user,
            locked_at=timezone.now(),
        )

        self.assertNotEqual(wrong_organization.tenant_id, wrong_organization.organization.tenant_id)
        self.assertNotEqual(wrong_rendition_set.tenant_id, wrong_rendition_set.rendition_set.tenant_id)

    def test_database_allows_only_one_active_selection_per_organization(self):
        self.create_selection()

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.create_selection(
                    selection_kind=OrganizationImageSelection.SelectionKind.SYSTEM_FALLBACK,
                    rendition_set=None,
                    revision=2,
                )

    def test_active_selections_for_different_organizations_are_allowed(self):
        second_organization = Organization.objects.create(
            tenant=self.tenant,
            name="Second selection organization",
        )
        self.create_selection()
        self.create_selection(
            organization=second_organization,
            selection_kind=OrganizationImageSelection.SelectionKind.SYSTEM_FALLBACK,
            rendition_set=None,
        )

        self.assertEqual(
            OrganizationImageSelection.objects.filter(status="active").count(),
            2,
        )

    def test_revision_must_be_positive_and_unique_per_tenant_organization(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.create_selection(revision=0)

        self.create_selection(status=OrganizationImageSelection.Status.ARCHIVED)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.create_selection(
                    selection_kind=OrganizationImageSelection.SelectionKind.SYSTEM_FALLBACK,
                    rendition_set=None,
                    revision=1,
                    status=OrganizationImageSelection.Status.ACTIVE,
                )

    def test_multiple_archived_revisions_and_one_active_revision_are_allowed(self):
        rendition_set = self.create_rendition_set()
        self.create_selection(
            rendition_set=rendition_set,
            revision=1,
            status=OrganizationImageSelection.Status.ARCHIVED,
        )
        self.create_selection(
            selection_kind=OrganizationImageSelection.SelectionKind.SYSTEM_FALLBACK,
            rendition_set=None,
            revision=2,
            status=OrganizationImageSelection.Status.ACTIVE,
        )
        self.create_selection(
            rendition_set=rendition_set,
            revision=3,
            status=OrganizationImageSelection.Status.ARCHIVED,
        )

        self.assertEqual(OrganizationImageSelection.objects.count(), 3)
        self.assertEqual(
            OrganizationImageSelection.objects.filter(status="archived").count(),
            2,
        )

    def test_locked_by_and_locked_at_are_required(self):
        for field_name in ("locked_by", "locked_at"):
            with self.subTest(field_name=field_name):
                with self.assertRaises(IntegrityError):
                    with transaction.atomic():
                        self.create_selection(**{field_name: None})

    def test_locked_by_user_is_protected(self):
        self.create_selection()

        with self.assertRaises(ProtectedError):
            self.user.delete()

    def test_clean_rejects_whitespace_alt_and_empty_fallback_alt(self):
        rendition_set = self.create_rendition_set()
        invalid_selections = (
            OrganizationImageSelection(
                tenant=self.tenant,
                organization=self.organization,
                selection_kind=OrganizationImageSelection.SelectionKind.ASSET,
                rendition_set=rendition_set,
                alt_text="   ",
                revision=1,
                status=OrganizationImageSelection.Status.ACTIVE,
                locked_by=self.user,
                locked_at=timezone.now(),
            ),
            OrganizationImageSelection(
                tenant=self.tenant,
                organization=self.organization,
                selection_kind=OrganizationImageSelection.SelectionKind.SYSTEM_FALLBACK,
                rendition_set=None,
                alt_text="",
                revision=1,
                status=OrganizationImageSelection.Status.ACTIVE,
                locked_by=self.user,
                locked_at=timezone.now(),
            ),
            OrganizationImageSelection(
                tenant=self.tenant,
                organization=self.organization,
                selection_kind=OrganizationImageSelection.SelectionKind.SYSTEM_FALLBACK,
                rendition_set=None,
                alt_text="   ",
                revision=1,
                status=OrganizationImageSelection.Status.ACTIVE,
                locked_by=self.user,
                locked_at=timezone.now(),
            ),
            OrganizationImageSelection(
                tenant=self.tenant,
                organization=self.organization,
                selection_kind=OrganizationImageSelection.SelectionKind.ASSET,
                rendition_set=rendition_set,
                alt_text="Valid alt text",
                public_credit="   ",
                revision=1,
                status=OrganizationImageSelection.Status.ACTIVE,
                locked_by=self.user,
                locked_at=timezone.now(),
            ),
        )

        for selection in invalid_selections:
            with self.subTest(
                selection_kind=selection.selection_kind,
                alt_text=selection.alt_text,
                public_credit=selection.public_credit,
            ):
                with self.assertRaises(ValidationError):
                    selection.full_clean()

    def test_database_allows_blank_asset_alt_but_rejects_blank_fallback_alt(self):
        asset_selection = self.create_selection(
            alt_text="",
            status=OrganizationImageSelection.Status.ARCHIVED,
        )
        self.assertEqual(asset_selection.alt_text, "")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.create_selection(
                    selection_kind=OrganizationImageSelection.SelectionKind.SYSTEM_FALLBACK,
                    rendition_set=None,
                    alt_text="",
                    revision=2,
                    status=OrganizationImageSelection.Status.ARCHIVED,
                )

    def test_text_is_not_normalized_or_rewritten_on_save(self):
        selection = self.create_selection(
            alt_text="  Organization image  ",
            public_credit="  Photographer  ",
        )
        selection.refresh_from_db()

        self.assertEqual(selection.alt_text, "  Organization image  ")
        self.assertEqual(selection.public_credit, "  Photographer  ")

    def test_rendition_set_is_protected_and_organization_cascades(self):
        rendition_set = self.create_rendition_set()
        selection = self.create_selection(rendition_set=rendition_set)

        with self.assertRaises(ProtectedError):
            rendition_set.delete()

        self.organization.delete()
        self.assertFalse(OrganizationImageSelection.objects.filter(pk=selection.pk).exists())

    def test_selection_does_not_duplicate_asset_or_rendition_recipe_fields(self):
        field_names = {field.name for field in OrganizationImageSelection._meta.fields}

        self.assertFalse({"asset", "fit_mode", "focus_x", "focus_y", "processing_version"} & field_names)
        self.assertFalse(
            any(
                field.get_internal_type() == "FileField"
                for field in OrganizationImageSelection._meta.fields
            )
        )
        self.assertFalse({"storage_key", "is_published", "publish_phone"} & field_names)

    def test_selection_model_operations_do_not_create_storage_directories_or_files(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            private_root = Path(temporary_directory) / "private"
            public_root = Path(temporary_directory) / "public"
            with override_settings(
                IMAGE_ORIGINALS_ROOT=private_root,
                IMAGE_RENDITIONS_ROOT=public_root,
            ):
                self.create_selection()

            self.assertFalse(private_root.exists())
            self.assertFalse(public_root.exists())
            self.assertEqual(list(Path(temporary_directory).iterdir()), [])


class OrganizationImageSelectionMigrationTests(TransactionTestCase):
    migrate_from = ("crm", "0021_image_domain_foundation")
    migrate_to = ("crm", "0022_organization_image_selection")

    def test_migration_preserves_existing_image_domain_data_and_is_reversible(self):
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        old_apps = executor.loader.project_state([self.migrate_from]).apps
        OldTenant = old_apps.get_model("crm", "Tenant")
        OldOrganization = old_apps.get_model("crm", "Organization")
        OldImageAsset = old_apps.get_model("crm", "ImageAsset")
        OldImageRenditionSet = old_apps.get_model("crm", "ImageRenditionSet")
        OldImageRendition = old_apps.get_model("crm", "ImageRendition")

        tenant = OldTenant.objects.create(name="Selection migration", slug="selection-migration")
        organization = OldOrganization.objects.create(tenant=tenant, name="Existing organization")
        asset = OldImageAsset.objects.create(
            tenant=tenant,
            private_storage_key="assets/existing.jpeg",
            checksum_sha256="a" * 64,
            original_format="jpeg",
            mime_type="image/jpeg",
            width=1600,
            height=900,
            file_size_bytes=123456,
            validation_version="validation-v1",
        )
        rendition_set = OldImageRenditionSet.objects.create(
            tenant=tenant,
            asset=asset,
            fit_mode="cover",
            processing_version="processing-v1",
            render_config_hash_sha256="b" * 64,
        )
        rendition = OldImageRendition.objects.create(
            tenant=tenant,
            rendition_set=rendition_set,
            variant="square",
            output_format="webp",
            width=512,
            height=512,
            file_size_bytes=45678,
            checksum_sha256="c" * 64,
            artifact_storage_key="renditions/existing-square.webp",
        )
        existing_ids = {
            "tenant": tenant.pk,
            "organization": organization.pk,
            "asset": asset.pk,
            "rendition_set": rendition_set.pk,
            "rendition": rendition.pk,
        }
        existing_snapshots = {
            "Tenant": OldTenant.objects.filter(pk=tenant.pk).values().get(),
            "Organization": OldOrganization.objects.filter(pk=organization.pk).values().get(),
            "ImageAsset": OldImageAsset.objects.filter(pk=asset.pk).values().get(),
            "ImageRenditionSet": OldImageRenditionSet.objects.filter(pk=rendition_set.pk).values().get(),
            "ImageRendition": OldImageRendition.objects.filter(pk=rendition.pk).values().get(),
        }

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        new_apps = executor.loader.project_state([self.migrate_to]).apps
        snapshot_ids = {
            "Tenant": existing_ids["tenant"],
            "Organization": existing_ids["organization"],
            "ImageAsset": existing_ids["asset"],
            "ImageRenditionSet": existing_ids["rendition_set"],
            "ImageRendition": existing_ids["rendition"],
        }
        for model_name, expected_snapshot in existing_snapshots.items():
            with self.subTest(model_name=model_name):
                actual_snapshot = (
                    new_apps.get_model("crm", model_name)
                    .objects.filter(pk=snapshot_ids[model_name])
                    .values()
                    .get()
                )
                self.assertEqual(actual_snapshot, expected_snapshot)
        self.assertEqual(new_apps.get_model("crm", "OrganizationImageSelection").objects.count(), 0)

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        restored_apps = executor.loader.project_state([self.migrate_from]).apps
        self.assertTrue(
            restored_apps.get_model("crm", "Organization").objects.filter(pk=existing_ids["organization"]).exists()
        )
        self.assertTrue(
            restored_apps.get_model("crm", "ImageRendition").objects.filter(pk=existing_ids["rendition"]).exists()
        )

        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())


@override_settings(IMAGE_ASSET_FEATURE_ENABLED=True)
class OrganizationImageSelectionCommandTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Image command tenant", slug="image-command")
        self.other_tenant = Tenant.objects.create(name="Other image tenant", slug="other-image")
        self.organization = Organization.objects.create(
            tenant=self.tenant,
            name="Command organization",
            org_number="123456789",
            is_published=True,
            publish_phone=True,
            thumbnail_image_url="https://example.com/thumbnail.jpg",
            auto_thumbnail_url="https://example.com/automatic.jpg",
            og_image_url="https://example.com/open-graph.jpg",
        )
        self.actor = get_user_model().objects.create_user(
            username="image-editor",
            password="test-password",
        )
        TenantMembership.objects.create(
            tenant=self.tenant,
            user=self.actor,
            role=TenantMembership.Role.REDIGERER,
        )
        self.image_counter = 0

    def create_image_domain(self, *, tenant=None, variants=None):
        tenant = tenant or self.tenant
        variants = variants or (
            ImageRendition.Variant.SQUARE,
            ImageRendition.Variant.LANDSCAPE,
            ImageRendition.Variant.SHARE,
        )
        self.image_counter += 1
        counter = self.image_counter
        asset = ImageAsset.objects.create(
            tenant=tenant,
            private_storage_key=f"assets/{tenant.pk}-{counter}.jpeg",
            checksum_sha256=f"{counter:x}"[-1] * 64,
            original_format=ImageAsset.OriginalFormat.JPEG,
            mime_type="image/jpeg",
            width=1600,
            height=900,
            file_size_bytes=123456,
            validation_version="validation-v1",
        )
        rendition_set = ImageRenditionSet.objects.create(
            tenant=tenant,
            asset=asset,
            fit_mode=ImageRenditionSet.FitMode.COVER,
            processing_version="processing-v1",
            render_config_hash_sha256=f"{counter + 8:x}"[-1] * 64,
        )
        for index, variant in enumerate(variants, start=1):
            ImageRendition.objects.create(
                tenant=tenant,
                rendition_set=rendition_set,
                variant=variant,
                output_format=ImageRendition.OutputFormat.WEBP,
                width=512 + index,
                height=512 + index,
                file_size_bytes=20000 + index,
                checksum_sha256=f"{counter + index:x}"[-1] * 64,
                artifact_storage_key=f"renditions/{tenant.pk}-{counter}-{variant}.webp",
            )
        return asset, rendition_set

    def evidence(self, **overrides):
        values = {
            "source_type": ImageReviewEvent.SourceType.OFFICIAL_WEBSITE,
            "source_url": "https://example.com/image.jpg",
            "source_page_url": "https://example.com/about",
            "provider": "official-site",
            "technical_warnings": ("low contrast",),
        }
        values.update(overrides)
        return AssetApprovalEvidence(**values)

    def lock_fallback(self, **overrides):
        values = {
            "actor": self.actor,
            "tenant_id": self.tenant.pk,
            "organization_id": self.organization.pk,
            "expected_revision": 0,
            "selection_kind": OrganizationImageSelection.SelectionKind.SYSTEM_FALLBACK,
            "alt_text": "Kreative Norge standardbilde",
        }
        values.update(overrides)
        return lock_organization_image_selection(**values)

    def lock_asset(self, rendition_set, **overrides):
        values = {
            "actor": self.actor,
            "tenant_id": self.tenant.pk,
            "organization_id": self.organization.pk,
            "expected_revision": 0,
            "selection_kind": OrganizationImageSelection.SelectionKind.ASSET,
            "rendition_set_id": rendition_set.pk,
            "alt_text": "Godkjent aktørbilde",
            "public_credit": "Fotograf",
            "asset_evidence": self.evidence(),
        }
        values.update(overrides)
        return lock_organization_image_selection(**values)

    def remove_to_fallback(self, **overrides):
        values = {
            "actor": self.actor,
            "tenant_id": self.tenant.pk,
            "organization_id": self.organization.pk,
            "expected_revision": 1,
            "fallback_alt_text": "Kreative Norge standardbilde",
        }
        values.update(overrides)
        return remove_organization_image_to_fallback(**values)

    def restore_archived(self, source_selection, **overrides):
        active_selection = OrganizationImageSelection.objects.get(
            tenant=self.tenant,
            organization=self.organization,
            status=OrganizationImageSelection.Status.ACTIVE,
        )
        values = {
            "actor": self.actor,
            "tenant_id": self.tenant.pk,
            "organization_id": self.organization.pk,
            "expected_revision": active_selection.revision,
            "source_selection_id": source_selection.pk,
        }
        values.update(overrides)
        return restore_archived_organization_image_selection(**values)

    @override_settings(IMAGE_ASSET_FEATURE_ENABLED=False)
    def test_disabled_feature_fails_before_any_write_or_existing_change(self):
        existing = OrganizationImageSelection.objects.create(
            tenant=self.tenant,
            organization=self.organization,
            selection_kind=OrganizationImageSelection.SelectionKind.SYSTEM_FALLBACK,
            rendition_set=None,
            alt_text="Existing fallback",
            revision=1,
            status=OrganizationImageSelection.Status.ACTIVE,
            locked_by=self.actor,
            locked_at=timezone.now(),
        )
        before = OrganizationImageSelection.objects.filter(pk=existing.pk).values().get()

        with self.assertRaises(ImageFeatureDisabledError):
            self.lock_fallback(expected_revision=1)

        self.assertEqual(
            OrganizationImageSelection.objects.filter(pk=existing.pk).values().get(),
            before,
        )
        self.assertEqual(ImageReviewEvent.objects.count(), 0)

    def test_allowed_capability_matrix_is_tenant_scoped(self):
        cases = (
            ("platform-admin", None, True),
            ("tenant-admin", TenantMembership.Role.SUPERADMIN, False),
            ("group-admin", TenantMembership.Role.GRUPPEADMIN, False),
            ("editor", TenantMembership.Role.REDIGERER, False),
        )
        for index, (username, role, is_superuser) in enumerate(cases, start=1):
            organization = Organization.objects.create(
                tenant=self.tenant,
                name=f"Capability organization {index}",
            )
            user = get_user_model().objects.create_user(
                username=username,
                password="test-password",
                is_superuser=is_superuser,
                is_staff=is_superuser,
            )
            if role:
                TenantMembership.objects.create(tenant=self.tenant, user=user, role=role)

            with self.subTest(role=role, is_superuser=is_superuser):
                result = self.lock_fallback(actor=user, organization_id=organization.pk)
                self.assertEqual(result.selection.tenant_id, self.tenant.pk)

    def test_reader_missing_wrong_tenant_inactive_and_anonymous_are_denied(self):
        reader = get_user_model().objects.create_user(username="reader", password="test-password")
        TenantMembership.objects.create(
            tenant=self.tenant,
            user=reader,
            role=TenantMembership.Role.LESER,
        )
        no_membership = get_user_model().objects.create_user(
            username="no-membership",
            password="test-password",
        )
        wrong_tenant = get_user_model().objects.create_user(
            username="wrong-tenant",
            password="test-password",
        )
        TenantMembership.objects.create(
            tenant=self.other_tenant,
            user=wrong_tenant,
            role=TenantMembership.Role.REDIGERER,
        )
        inactive = get_user_model().objects.create_user(
            username="inactive-editor",
            password="test-password",
            is_active=False,
        )
        TenantMembership.objects.create(
            tenant=self.tenant,
            user=inactive,
            role=TenantMembership.Role.REDIGERER,
        )

        for actor in (reader, no_membership, wrong_tenant, inactive, AnonymousUser()):
            with self.subTest(actor=str(actor)):
                with self.assertRaises(ImageSelectionPermissionDenied):
                    self.lock_fallback(actor=actor)

        self.assertEqual(OrganizationImageSelection.objects.count(), 0)
        self.assertEqual(ImageReviewEvent.objects.count(), 0)

    def test_first_fallback_is_revision_one_and_has_no_false_approval(self):
        result = self.lock_fallback()

        self.assertEqual(result.selection.revision, 1)
        self.assertEqual(result.selection.status, OrganizationImageSelection.Status.ACTIVE)
        self.assertEqual(result.selection.locked_by, self.actor)
        self.assertIsNone(result.previous_selection)
        self.assertEqual(result.event.event_type, ImageReviewEvent.EventType.SELECTION_LOCKED)
        self.assertEqual(result.event.created_at, result.selection.locked_at)
        self.assertEqual(result.event.actor_user, self.actor)
        self.assertIsNone(result.event.previous_selection_id_snapshot)
        self.assertIsNone(result.event.rendition_set_id_snapshot)
        self.assertIsNone(result.event.asset_id_snapshot)
        self.assertEqual(result.event.asset_checksum_sha256_snapshot, "")
        self.assertEqual(result.event.source_type_snapshot, "")
        self.assertEqual(result.event.technical_warnings_snapshot, [])
        self.assertEqual(result.event.approval_text_version_snapshot, "")
        self.assertEqual(result.event.approval_text_snapshot, "")

    def test_first_asset_lock_preserves_blank_alt_in_selection_and_event(self):
        _, rendition_set = self.create_image_domain()

        result = self.lock_asset(rendition_set, alt_text="")

        result.selection.refresh_from_db()
        result.event.refresh_from_db()
        self.assertEqual(result.selection.alt_text, "")
        self.assertEqual(result.event.alt_text_snapshot, "")
        self.assertNotEqual(result.selection.alt_text, self.organization.name)

    def test_asset_event_uses_internal_approval_and_validated_provenance(self):
        asset, rendition_set = self.create_image_domain()
        evidence = self.evidence(
            source_type=ImageReviewEvent.SourceType.BRAVE_IMAGE_SEARCH,
            provider="brave",
            technical_warnings=("small source", "manual crop reviewed"),
        )

        result = self.lock_asset(rendition_set, asset_evidence=evidence)

        self.assertEqual(result.event.rendition_set_id_snapshot, rendition_set.pk)
        self.assertEqual(result.event.asset_id_snapshot, asset.pk)
        self.assertEqual(result.event.asset_checksum_sha256_snapshot, asset.checksum_sha256)
        self.assertEqual(
            result.event.asset_validation_version_snapshot,
            asset.validation_version,
        )
        self.assertEqual(result.event.source_type_snapshot, evidence.source_type)
        self.assertEqual(result.event.source_url_snapshot, evidence.source_url)
        self.assertEqual(result.event.source_page_url_snapshot, evidence.source_page_url)
        self.assertEqual(result.event.provider_snapshot, evidence.provider)
        self.assertEqual(
            result.event.technical_warnings_snapshot,
            list(evidence.technical_warnings),
        )
        self.assertEqual(result.event.approval_text_version_snapshot, IMAGE_APPROVAL_TEXT_VERSION)
        self.assertEqual(result.event.approval_text_snapshot, IMAGE_APPROVAL_TEXT)
        self.assertNotIn(
            "approval_text",
            inspect.signature(lock_organization_image_selection).parameters,
        )

    def test_remove_asset_to_fallback_writes_exact_revision_and_event_contract(self):
        _, rendition_set = self.create_image_domain()
        first = self.lock_asset(rendition_set)
        previous_before = OrganizationImageSelection.objects.filter(
            pk=first.selection.pk
        ).values().get()
        fallback_alt_text = "  Kreative Norge standardbilde  "

        result = self.remove_to_fallback(fallback_alt_text=fallback_alt_text)

        previous_after = OrganizationImageSelection.objects.filter(
            pk=first.selection.pk
        ).values().get()
        self.assertEqual(
            previous_after,
            {**previous_before, "status": OrganizationImageSelection.Status.ARCHIVED},
        )
        self.assertEqual(result.previous_selection.pk, first.selection.pk)
        self.assertEqual(result.selection.selection_kind, OrganizationImageSelection.SelectionKind.SYSTEM_FALLBACK)
        self.assertEqual(result.selection.revision, 2)
        self.assertEqual(result.selection.status, OrganizationImageSelection.Status.ACTIVE)
        self.assertEqual(result.selection.alt_text, fallback_alt_text)
        self.assertEqual(result.selection.public_credit, "")
        self.assertIsNone(result.selection.rendition_set_id)
        self.assertEqual(result.selection.locked_at, result.event.created_at)
        self.assertEqual(
            result.event.event_type,
            ImageReviewEvent.EventType.SELECTION_REMOVED_TO_FALLBACK,
        )
        self.assertEqual(result.event.selection_id, result.selection.pk)
        self.assertEqual(result.event.selection_revision_snapshot, 2)
        self.assertEqual(result.event.previous_selection_id, first.selection.pk)
        self.assertEqual(result.event.previous_selection_id_snapshot, first.selection.pk)
        self.assertEqual(result.event.previous_selection_revision_snapshot, 1)
        self.assertEqual(
            result.event.selection_kind_snapshot,
            OrganizationImageSelection.SelectionKind.SYSTEM_FALLBACK,
        )
        self.assertIsNone(result.event.rendition_set_id_snapshot)
        self.assertIsNone(result.event.asset_id_snapshot)
        self.assertEqual(result.event.asset_checksum_sha256_snapshot, "")
        self.assertEqual(result.event.asset_validation_version_snapshot, "")
        self.assertEqual(result.event.source_type_snapshot, "")
        self.assertEqual(result.event.source_url_snapshot, "")
        self.assertEqual(result.event.source_page_url_snapshot, "")
        self.assertEqual(result.event.provider_snapshot, "")
        self.assertEqual(result.event.technical_warnings_snapshot, [])
        self.assertEqual(result.event.approval_text_version_snapshot, "")
        self.assertEqual(result.event.approval_text_snapshot, "")
        self.assertEqual(
            OrganizationImageSelection.objects.filter(
                organization=self.organization,
                status=OrganizationImageSelection.Status.ACTIVE,
            ).count(),
            1,
        )

    def test_remove_feature_off_preserves_selection_and_event_history(self):
        _, rendition_set = self.create_image_domain()
        first = self.lock_asset(rendition_set)
        selection_before = OrganizationImageSelection.objects.filter(
            pk=first.selection.pk
        ).values().get()
        event_before = ImageReviewEvent.objects.filter(pk=first.event.pk).values().get()

        with override_settings(IMAGE_ASSET_FEATURE_ENABLED=False):
            with self.assertRaises(ImageFeatureDisabledError):
                self.remove_to_fallback()

        self.assertEqual(
            OrganizationImageSelection.objects.filter(pk=first.selection.pk).values().get(),
            selection_before,
        )
        self.assertEqual(
            ImageReviewEvent.objects.filter(pk=first.event.pk).values().get(),
            event_before,
        )
        self.assertEqual(OrganizationImageSelection.objects.count(), 1)
        self.assertEqual(ImageReviewEvent.objects.count(), 1)

    def test_remove_rejects_missing_or_fallback_active_selection_without_writes(self):
        with self.assertRaises(InvalidImageSelectionTransitionError):
            self.remove_to_fallback(expected_revision=0)
        self.assertEqual(OrganizationImageSelection.objects.count(), 0)
        self.assertEqual(ImageReviewEvent.objects.count(), 0)

        fallback = self.lock_fallback()
        selection_before = OrganizationImageSelection.objects.filter(
            pk=fallback.selection.pk
        ).values().get()
        event_before = ImageReviewEvent.objects.filter(pk=fallback.event.pk).values().get()
        with self.assertRaises(InvalidImageSelectionTransitionError):
            self.remove_to_fallback(expected_revision=1)

        self.assertEqual(
            OrganizationImageSelection.objects.filter(pk=fallback.selection.pk).values().get(),
            selection_before,
        )
        self.assertEqual(
            ImageReviewEvent.objects.filter(pk=fallback.event.pk).values().get(),
            event_before,
        )

    def test_remove_rejects_conflict_and_invalid_alt_text_without_writes(self):
        _, rendition_set = self.create_image_domain()
        first = self.lock_asset(rendition_set)
        selection_before = OrganizationImageSelection.objects.filter(
            pk=first.selection.pk
        ).values().get()

        with self.assertRaises(ExpectedRevisionConflictError):
            self.remove_to_fallback(expected_revision=0)
        for fallback_alt_text in ("", "   ", None, 123):
            with self.subTest(fallback_alt_text=fallback_alt_text):
                with self.assertRaises(InvalidImageSelectionError):
                    self.remove_to_fallback(fallback_alt_text=fallback_alt_text)

        self.assertEqual(
            OrganizationImageSelection.objects.filter(pk=first.selection.pk).values().get(),
            selection_before,
        )
        self.assertEqual(OrganizationImageSelection.objects.count(), 1)
        self.assertEqual(ImageReviewEvent.objects.count(), 1)

    def test_remove_uses_same_allowed_capability_matrix(self):
        cases = (
            ("remove-platform-admin", None, True),
            ("remove-tenant-admin", TenantMembership.Role.SUPERADMIN, False),
            ("remove-group-admin", TenantMembership.Role.GRUPPEADMIN, False),
            ("remove-editor", TenantMembership.Role.REDIGERER, False),
        )
        for index, (username, role, is_superuser) in enumerate(cases, start=1):
            organization = Organization.objects.create(
                tenant=self.tenant,
                name=f"Removal capability organization {index}",
            )
            user = get_user_model().objects.create_user(
                username=username,
                password="test-password",
                is_superuser=is_superuser,
                is_staff=is_superuser,
            )
            if role:
                TenantMembership.objects.create(tenant=self.tenant, user=user, role=role)
            _, rendition_set = self.create_image_domain()
            self.lock_asset(
                rendition_set,
                organization_id=organization.pk,
            )

            with self.subTest(role=role, is_superuser=is_superuser):
                result = self.remove_to_fallback(
                    actor=user,
                    organization_id=organization.pk,
                )
                self.assertEqual(result.selection.tenant_id, self.tenant.pk)

    def test_remove_denies_unauthorized_actors_and_cross_tenant_organization(self):
        _, rendition_set = self.create_image_domain()
        first = self.lock_asset(rendition_set)
        reader = get_user_model().objects.create_user(
            username="remove-reader",
            password="test-password",
        )
        TenantMembership.objects.create(
            tenant=self.tenant,
            user=reader,
            role=TenantMembership.Role.LESER,
        )
        no_membership = get_user_model().objects.create_user(
            username="remove-no-membership",
            password="test-password",
        )
        wrong_tenant = get_user_model().objects.create_user(
            username="remove-wrong-tenant",
            password="test-password",
        )
        TenantMembership.objects.create(
            tenant=self.other_tenant,
            user=wrong_tenant,
            role=TenantMembership.Role.REDIGERER,
        )
        inactive = get_user_model().objects.create_user(
            username="remove-inactive",
            password="test-password",
            is_active=False,
        )
        TenantMembership.objects.create(
            tenant=self.tenant,
            user=inactive,
            role=TenantMembership.Role.REDIGERER,
        )

        for actor in (reader, no_membership, wrong_tenant, inactive, AnonymousUser()):
            with self.subTest(actor=str(actor)):
                with self.assertRaises(ImageSelectionPermissionDenied):
                    self.remove_to_fallback(actor=actor)

        other_organization = Organization.objects.create(
            tenant=self.other_tenant,
            name="Cross-tenant removal organization",
        )
        with self.assertRaises(ImageSelectionNotFoundError):
            self.remove_to_fallback(organization_id=other_organization.pk)

        first.selection.refresh_from_db()
        self.assertEqual(first.selection.status, OrganizationImageSelection.Status.ACTIVE)
        self.assertEqual(OrganizationImageSelection.objects.count(), 1)
        self.assertEqual(ImageReviewEvent.objects.count(), 1)

    def test_generic_lock_rejects_asset_to_fallback_and_fallback_to_fallback(self):
        _, rendition_set = self.create_image_domain()
        first = self.lock_asset(rendition_set)
        with self.assertRaises(InvalidImageSelectionTransitionError):
            self.lock_fallback(expected_revision=1)
        first.selection.refresh_from_db()
        self.assertEqual(first.selection.status, OrganizationImageSelection.Status.ACTIVE)

        self.remove_to_fallback()
        with self.assertRaises(InvalidImageSelectionTransitionError):
            self.lock_fallback(expected_revision=2)

        self.assertEqual(OrganizationImageSelection.objects.count(), 2)
        self.assertEqual(ImageReviewEvent.objects.count(), 2)

    def test_remove_event_failure_rolls_back_and_keeps_asset_active(self):
        _, rendition_set = self.create_image_domain()
        first = self.lock_asset(rendition_set)
        selection_before = OrganizationImageSelection.objects.filter(
            pk=first.selection.pk
        ).values().get()

        with patch.object(ImageReviewEvent, "save", side_effect=RuntimeError("event failure")):
            with self.assertRaisesRegex(RuntimeError, "event failure"):
                self.remove_to_fallback()

        self.assertEqual(
            OrganizationImageSelection.objects.filter(pk=first.selection.pk).values().get(),
            selection_before,
        )
        self.assertEqual(OrganizationImageSelection.objects.count(), 1)
        self.assertEqual(ImageReviewEvent.objects.count(), 1)

    def test_invalid_warning_and_sensitive_url_evidence_are_rejected_without_writes(self):
        _, rendition_set = self.create_image_domain()
        invalid_evidence = (
            self.evidence(technical_warnings=("x" * 256,)),
            self.evidence(technical_warnings="not-a-list"),
            self.evidence(source_url="https://example.com/image.jpg?token=secret"),
        )

        for evidence in invalid_evidence:
            with self.subTest(evidence=evidence):
                with self.assertRaises(InvalidImageSelectionError):
                    self.lock_asset(rendition_set, asset_evidence=evidence)

        self.assertEqual(OrganizationImageSelection.objects.count(), 0)
        self.assertEqual(ImageReviewEvent.objects.count(), 0)

    def test_snapshot_urls_reject_unsafe_schemes_credentials_and_fragments(self):
        _, rendition_set = self.create_image_domain()
        unsafe_urls = (
            "ftp://example.com/image.jpg",
            "//example.com/image.jpg",
            "https://user@example.com/image.jpg",
            "https://:password@example.com/image.jpg",
            "https://example.com/image.jpg#private",
        )

        for field_name in ("source_url", "source_page_url"):
            for unsafe_url in unsafe_urls:
                with self.subTest(field_name=field_name, unsafe_url=unsafe_url):
                    with self.assertRaises(InvalidImageSelectionError):
                        self.lock_asset(
                            rendition_set,
                            asset_evidence=self.evidence(**{field_name: unsafe_url}),
                        )

        self.assertEqual(OrganizationImageSelection.objects.count(), 0)
        self.assertEqual(ImageReviewEvent.objects.count(), 0)

    def test_snapshot_urls_reject_sensitive_query_keys_case_insensitively(self):
        _, rendition_set = self.create_image_domain()
        sensitive_keys = (
            "credential",
            "credentials",
            "signature",
            "sig",
            "token",
            "access_token",
            "id_token",
            "refresh_token",
            "auth",
            "authorization",
            "api_key",
            "apikey",
            "access_key",
            "secret",
            "secret_key",
            "password",
            "passwd",
            "sv",
            "se",
            "sp",
            "sr",
            "x-amz-credential",
            "x-goog-signature",
        )

        for field_name in ("source_url", "source_page_url"):
            for index, sensitive_key in enumerate(sensitive_keys):
                query_key = sensitive_key.upper() if index % 2 else sensitive_key
                unsafe_url = f"https://example.com/image.jpg?{query_key}=private"
                with self.subTest(field_name=field_name, query_key=query_key):
                    with self.assertRaises(InvalidImageSelectionError):
                        self.lock_asset(
                            rendition_set,
                            asset_evidence=self.evidence(**{field_name: unsafe_url}),
                        )

        self.assertEqual(OrganizationImageSelection.objects.count(), 0)
        self.assertEqual(ImageReviewEvent.objects.count(), 0)

    def test_snapshot_urls_allow_benign_http_query_parameters_without_rewriting(self):
        _, rendition_set = self.create_image_domain()
        source_url = "http://example.com/image.jpg?width=512&format=webp"
        source_page_url = "https://example.com/gallery?page=2&layout=grid"

        result = self.lock_asset(
            rendition_set,
            asset_evidence=self.evidence(
                source_url=source_url,
                source_page_url=source_page_url,
            ),
        )

        self.assertEqual(result.event.source_url_snapshot, source_url)
        self.assertEqual(result.event.source_page_url_snapshot, source_page_url)

    def test_asset_requires_evidence_and_upload_or_brave_may_have_blank_source_url(self):
        _, rendition_set = self.create_image_domain()

        with self.assertRaises(InvalidImageSelectionError):
            self.lock_asset(rendition_set, asset_evidence=None)

        result = self.lock_asset(
            rendition_set,
            asset_evidence=self.evidence(
                source_type=ImageReviewEvent.SourceType.UPLOAD,
                source_url="",
            ),
        )
        self.assertEqual(result.event.source_type_snapshot, ImageReviewEvent.SourceType.UPLOAD)
        self.assertEqual(result.event.source_url_snapshot, "")

        brave_organization = Organization.objects.create(
            tenant=self.tenant,
            name="Brave source organization",
        )
        _, brave_rendition_set = self.create_image_domain()
        brave_result = self.lock_asset(
            brave_rendition_set,
            organization_id=brave_organization.pk,
            asset_evidence=self.evidence(
                source_type=ImageReviewEvent.SourceType.BRAVE_IMAGE_SEARCH,
                source_url="",
            ),
        )
        self.assertEqual(
            brave_result.event.source_type_snapshot,
            ImageReviewEvent.SourceType.BRAVE_IMAGE_SEARCH,
        )
        self.assertEqual(brave_result.event.source_url_snapshot, "")

    def test_replacement_archives_only_status_and_writes_previous_snapshot(self):
        _, first_rendition_set = self.create_image_domain()
        _, second_rendition_set = self.create_image_domain()
        first = self.lock_asset(first_rendition_set)
        previous_before = OrganizationImageSelection.objects.filter(
            pk=first.selection.pk
        ).values().get()

        replacement = self.lock_asset(
            second_rendition_set,
            expected_revision=1,
            alt_text="",
        )

        previous_after = OrganizationImageSelection.objects.filter(
            pk=first.selection.pk
        ).values().get()
        expected_previous = {**previous_before, "status": OrganizationImageSelection.Status.ARCHIVED}
        self.assertEqual(previous_after, expected_previous)
        self.assertEqual(replacement.selection.revision, 2)
        self.assertEqual(replacement.event.event_type, ImageReviewEvent.EventType.SELECTION_REPLACED)
        self.assertEqual(replacement.event.previous_selection_id_snapshot, first.selection.pk)
        self.assertEqual(replacement.event.previous_selection_revision_snapshot, 1)
        self.assertEqual(replacement.selection.alt_text, "")
        self.assertEqual(replacement.event.alt_text_snapshot, "")
        self.assertNotEqual(replacement.selection.alt_text, self.organization.name)
        self.assertEqual(
            OrganizationImageSelection.objects.filter(status="active").count(),
            1,
        )

    def test_fallback_can_be_replaced_by_asset_and_old_set_reselected_as_new_revision(self):
        _, rendition_set = self.create_image_domain()
        first = self.lock_asset(rendition_set)
        fallback = self.remove_to_fallback()
        third = self.lock_asset(rendition_set, expected_revision=2)

        first.selection.refresh_from_db()
        fallback.selection.refresh_from_db()
        self.assertEqual(first.selection.status, OrganizationImageSelection.Status.ARCHIVED)
        self.assertEqual(fallback.selection.status, OrganizationImageSelection.Status.ARCHIVED)
        self.assertEqual(third.selection.revision, 3)
        self.assertNotEqual(third.selection.pk, first.selection.pk)
        self.assertEqual(third.selection.rendition_set_id, first.selection.rendition_set_id)
        self.assertEqual(
            list(
                OrganizationImageSelection.objects.filter(organization=self.organization)
                .order_by("revision")
                .values_list("revision", flat=True)
            ),
            [1, 2, 3],
        )

    def test_expected_revision_conflict_has_zero_writes(self):
        first = self.lock_fallback()
        before = OrganizationImageSelection.objects.filter(pk=first.selection.pk).values().get()

        with self.assertRaises(ExpectedRevisionConflictError):
            self.lock_fallback(expected_revision=0, alt_text="Conflicting fallback")

        self.assertEqual(
            OrganizationImageSelection.objects.filter(pk=first.selection.pk).values().get(),
            before,
        )
        self.assertEqual(OrganizationImageSelection.objects.count(), 1)
        self.assertEqual(ImageReviewEvent.objects.count(), 1)

    def test_rendition_gate_rejects_missing_and_cross_tenant_data(self):
        _, incomplete_set = self.create_image_domain(
            variants=(ImageRendition.Variant.SQUARE, ImageRendition.Variant.LANDSCAPE)
        )
        with self.assertRaises(IncompleteRenditionSetError):
            self.lock_asset(incomplete_set)

        _, other_set = self.create_image_domain(tenant=self.other_tenant)
        with self.assertRaises(ImageSelectionNotFoundError):
            self.lock_asset(other_set)

        foreign_asset, _ = self.create_image_domain(tenant=self.other_tenant)
        mismatched_set = ImageRenditionSet.objects.create(
            tenant=self.tenant,
            asset=foreign_asset,
            fit_mode=ImageRenditionSet.FitMode.COVER,
            processing_version="processing-v1",
            render_config_hash_sha256="f" * 64,
        )
        with self.assertRaises(ImageSelectionNotFoundError):
            self.lock_asset(mismatched_set)

        self.assertEqual(OrganizationImageSelection.objects.count(), 0)
        self.assertEqual(ImageReviewEvent.objects.count(), 0)

    def test_rendition_gate_rejects_cross_tenant_rendition(self):
        _, rendition_set = self.create_image_domain()
        ImageRendition.objects.create(
            tenant=self.other_tenant,
            rendition_set=rendition_set,
            variant=ImageRendition.Variant.SQUARE,
            output_format=ImageRendition.OutputFormat.WEBP,
            width=512,
            height=512,
            file_size_bytes=12345,
            checksum_sha256="e" * 64,
            artifact_storage_key="renditions/foreign-square.webp",
        )

        with self.assertRaises(ImageSelectionNotFoundError):
            self.lock_asset(rendition_set)

        self.assertEqual(OrganizationImageSelection.objects.count(), 0)

    def test_database_prevents_duplicate_required_variant(self):
        _, rendition_set = self.create_image_domain()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ImageRendition.objects.create(
                    tenant=self.tenant,
                    rendition_set=rendition_set,
                    variant=ImageRendition.Variant.SQUARE,
                    output_format=ImageRendition.OutputFormat.WEBP,
                    width=512,
                    height=512,
                    file_size_bytes=12345,
                    checksum_sha256="d" * 64,
                    artifact_storage_key="renditions/duplicate-square.webp",
                )

    def test_fallback_rejects_rendition_and_asset_evidence(self):
        _, rendition_set = self.create_image_domain()
        invalid_values = (
            {"rendition_set_id": rendition_set.pk},
            {"asset_evidence": self.evidence()},
        )
        for values in invalid_values:
            with self.subTest(values=values):
                with self.assertRaises(InvalidImageSelectionError):
                    self.lock_fallback(**values)

        self.assertEqual(OrganizationImageSelection.objects.count(), 0)

    def test_selection_text_validation_is_translated_to_domain_error(self):
        invalid_values = (
            {"alt_text": ""},
            {"alt_text": "   "},
            {"public_credit": "   "},
        )
        for values in invalid_values:
            with self.subTest(values=values):
                with self.assertRaises(InvalidImageSelectionError):
                    self.lock_fallback(**values)
        self.assertEqual(OrganizationImageSelection.objects.count(), 0)

    def test_asset_whitespace_only_alt_is_rejected_without_writes(self):
        _, rendition_set = self.create_image_domain()

        with self.assertRaises(InvalidImageSelectionError):
            self.lock_asset(rendition_set, alt_text="   ")

        self.assertEqual(OrganizationImageSelection.objects.count(), 0)
        self.assertEqual(ImageReviewEvent.objects.count(), 0)

    def test_event_database_source_url_contract_covers_every_source_type(self):
        _, rendition_set = self.create_image_domain()
        template_event = self.lock_asset(rendition_set).event
        template_values = (
            ImageReviewEvent._base_objects.filter(pk=template_event.pk).values().get()
        )
        template_values.pop("id")

        source_types = tuple(value for value, _label in ImageReviewEvent.SourceType.choices)
        for source_type in source_types:
            with self.subTest(source_type=source_type, source_url="nonempty"):
                event = ImageReviewEvent._base_objects.create(
                    **{
                        **template_values,
                        "source_type_snapshot": source_type,
                        "source_url_snapshot": "https://example.com/retained-source.jpg",
                    }
                )
                self.assertEqual(event.source_type_snapshot, source_type)

        for source_type in (
            ImageReviewEvent.SourceType.UPLOAD,
            ImageReviewEvent.SourceType.BRAVE_IMAGE_SEARCH,
        ):
            with self.subTest(source_type=source_type, source_url="blank"):
                event = ImageReviewEvent._base_objects.create(
                    **{
                        **template_values,
                        "source_type_snapshot": source_type,
                        "source_url_snapshot": "",
                    }
                )
                self.assertEqual(event.source_url_snapshot, "")

        for source_type in (
            ImageReviewEvent.SourceType.OFFICIAL_WEBSITE,
            ImageReviewEvent.SourceType.OPEN_GRAPH,
            ImageReviewEvent.SourceType.WEBSITE_IMAGE,
            ImageReviewEvent.SourceType.PASTED_URL,
        ):
            with self.subTest(source_type=source_type, source_url="blank"):
                with self.assertRaises(IntegrityError):
                    with transaction.atomic():
                        ImageReviewEvent._base_objects.create(
                            **{
                                **template_values,
                                "source_type_snapshot": source_type,
                                "source_url_snapshot": "",
                            }
                        )

    def test_event_database_allows_blank_alt_but_keeps_actor_and_org_required(self):
        _, rendition_set = self.create_image_domain()
        result = self.lock_asset(rendition_set, alt_text="")
        self.assertEqual(result.event.alt_text_snapshot, "")

        template_values = (
            ImageReviewEvent._base_objects.filter(pk=result.event.pk).values().get()
        )
        template_values.pop("id")
        for required_field in (
            "organization_name_snapshot",
            "actor_username_snapshot",
        ):
            with self.subTest(required_field=required_field):
                with self.assertRaises(IntegrityError):
                    with transaction.atomic():
                        ImageReviewEvent._base_objects.create(
                            **{**template_values, required_field: ""}
                        )

    def test_event_failure_rolls_back_first_selection(self):
        with patch.object(ImageReviewEvent, "save", side_effect=RuntimeError("event failure")):
            with self.assertRaisesRegex(RuntimeError, "event failure"):
                self.lock_fallback()

        self.assertEqual(OrganizationImageSelection.objects.count(), 0)
        self.assertEqual(ImageReviewEvent.objects.count(), 0)

    def test_event_failure_rolls_back_replacement_and_keeps_old_active(self):
        _, first_rendition_set = self.create_image_domain()
        _, second_rendition_set = self.create_image_domain()
        first = self.lock_asset(first_rendition_set)

        with patch.object(ImageReviewEvent, "save", side_effect=RuntimeError("event failure")):
            with self.assertRaisesRegex(RuntimeError, "event failure"):
                self.lock_asset(second_rendition_set, expected_revision=1)

        first.selection.refresh_from_db()
        self.assertEqual(first.selection.status, OrganizationImageSelection.Status.ACTIVE)
        self.assertEqual(OrganizationImageSelection.objects.count(), 1)
        self.assertEqual(ImageReviewEvent.objects.count(), 1)

    def test_event_is_append_only_through_supported_orm_paths(self):
        event = self.lock_fallback().event

        event.alt_text_snapshot = "Changed"
        with self.assertRaises(AppendOnlyEventError):
            event.save()
        with self.assertRaises(AppendOnlyEventError):
            event.delete()
        with self.assertRaises(AppendOnlyEventError):
            ImageReviewEvent.objects.filter(pk=event.pk).update(alt_text_snapshot="Changed")
        with self.assertRaises(AppendOnlyEventError):
            ImageReviewEvent.objects.filter(pk=event.pk).delete()
        with self.assertRaises(AppendOnlyEventError):
            ImageReviewEvent.objects.bulk_update([event], ["alt_text_snapshot"])

        event.refresh_from_db()
        self.assertEqual(event.alt_text_snapshot, "Kreative Norge standardbilde")

    def test_base_manager_allows_reads_and_only_null_live_reference_updates(self):
        event = self.lock_fallback().event
        before = ImageReviewEvent._base_objects.filter(pk=event.pk).values().get()

        updated = ImageReviewEvent._base_objects.filter(pk=event.pk).update(
            organization=None,
        )
        after = ImageReviewEvent._base_objects.filter(pk=event.pk).values().get()

        self.assertEqual(updated, 1)
        self.assertEqual(after, {**before, "organization_id": None})
        with self.assertRaises(AppendOnlyEventError):
            ImageReviewEvent._base_objects.filter(pk=event.pk).update(
                organization=self.organization,
            )

    def test_base_manager_blocks_general_mutation_paths(self):
        event = self.lock_fallback().event
        event.alt_text_snapshot = "Changed"

        with self.assertRaises(AppendOnlyEventError):
            ImageReviewEvent._base_objects.filter(pk=event.pk).update(
                alt_text_snapshot="Changed",
            )
        with self.assertRaises(AppendOnlyEventError):
            ImageReviewEvent._base_objects.filter(pk=event.pk).delete()
        with self.assertRaises(AppendOnlyEventError):
            ImageReviewEvent._base_objects.bulk_update([event], ["alt_text_snapshot"])
        with self.assertRaises(AppendOnlyEventError):
            ImageReviewEvent._base_objects.filter(pk=event.pk)._update(
                [
                    (
                        ImageReviewEvent._meta.get_field("alt_text_snapshot"),
                        None,
                        "Changed",
                    )
                ]
            )
        with self.assertRaises(AppendOnlyEventError):
            ImageReviewEvent._base_objects.update_or_create(
                pk=event.pk,
                defaults={"alt_text_snapshot": "Changed"},
            )
        with self.assertRaises(AppendOnlyEventError):
            ImageReviewEvent._base_objects.bulk_create(
                [event],
                update_conflicts=True,
                update_fields=["alt_text_snapshot"],
                unique_fields=["id"],
            )

        event.refresh_from_db()
        self.assertEqual(event.alt_text_snapshot, "Kreative Norge standardbilde")

    def test_set_null_and_actor_deletion_change_only_live_event_references(self):
        asset, rendition_set = self.create_image_domain()
        self.lock_asset(rendition_set)
        event = self.lock_asset(rendition_set, expected_revision=1).event
        before = ImageReviewEvent._base_objects.filter(pk=event.pk).values().get()

        self.organization.delete()
        self.actor.delete()
        ImageRendition.objects.filter(rendition_set=rendition_set).delete()
        rendition_set.delete()
        asset.delete()
        after = ImageReviewEvent._base_objects.filter(pk=event.pk).values().get()

        expected = {
            **before,
            "organization_id": None,
            "selection_id": None,
            "rendition_set_id": None,
            "asset_id": None,
            "previous_selection_id": None,
            "actor_user_id": None,
        }
        self.assertEqual(after, expected)

    def test_tenant_cascade_deletes_events_despite_base_queryset_delete_guard(self):
        event_id = self.lock_fallback().event.pk

        self.tenant.delete()

        self.assertFalse(ImageReviewEvent._base_objects.filter(pk=event_id).exists())

    def test_database_constraints_use_snapshots_not_live_foreign_keys(self):
        event = self.lock_fallback().event
        values = ImageReviewEvent._base_objects.filter(pk=event.pk).values().get()
        values.pop("id")
        values["event_type"] = ImageReviewEvent.EventType.SELECTION_REPLACED

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ImageReviewEvent.objects.create(**values)

        values["event_type"] = ImageReviewEvent.EventType.SELECTION_REMOVED_TO_FALLBACK
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ImageReviewEvent.objects.create(**values)

        values["event_type"] = ImageReviewEvent.EventType.SELECTION_LOCKED
        values["asset_id_snapshot"] = 99
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ImageReviewEvent.objects.create(**values)

    def test_removed_event_database_constraint_requires_fallback_selection(self):
        _, first_rendition_set = self.create_image_domain()
        _, second_rendition_set = self.create_image_domain()
        self.lock_asset(first_rendition_set)
        replacement = self.lock_asset(second_rendition_set, expected_revision=1)
        values = ImageReviewEvent._base_objects.filter(
            pk=replacement.event.pk
        ).values().get()
        values.pop("id")
        values["event_type"] = ImageReviewEvent.EventType.SELECTION_REMOVED_TO_FALLBACK

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ImageReviewEvent.objects.create(**values)

    def test_command_preserves_publication_people_contacts_and_legacy_images(self):
        _, rendition_set = self.create_image_domain()
        self.lock_asset(rendition_set)
        person = Person.objects.create(
            tenant=self.tenant,
            full_name="Public person",
            email="person@example.com",
            phone="12345678",
        )
        link = OrganizationPerson.objects.create(
            tenant=self.tenant,
            organization=self.organization,
            person=person,
            publish_person=True,
        )
        contact = PersonContact.objects.create(
            tenant=self.tenant,
            person=person,
            type="EMAIL",
            value="person@example.com",
            is_primary=True,
            is_public=True,
        )
        organization_before = Organization.objects.filter(pk=self.organization.pk).values().get()
        person_before = Person.objects.filter(pk=person.pk).values().get()
        link_before = OrganizationPerson.objects.filter(pk=link.pk).values().get()
        contact_before = PersonContact.objects.filter(pk=contact.pk).values().get()

        self.remove_to_fallback()

        self.assertEqual(
            Organization.objects.filter(pk=self.organization.pk).values().get(),
            organization_before,
        )
        self.assertEqual(Person.objects.filter(pk=person.pk).values().get(), person_before)
        self.assertEqual(
            OrganizationPerson.objects.filter(pk=link.pk).values().get(),
            link_before,
        )
        self.assertEqual(
            PersonContact.objects.filter(pk=contact.pk).values().get(),
            contact_before,
        )

    def test_command_and_event_model_do_not_use_storage_or_create_files(self):
        _, rendition_set = self.create_image_domain()
        self.lock_asset(rendition_set)
        with tempfile.TemporaryDirectory() as temporary_directory:
            private_root = Path(temporary_directory) / "private"
            public_root = Path(temporary_directory) / "public"
            with override_settings(
                IMAGE_ORIGINALS_ROOT=private_root,
                IMAGE_RENDITIONS_ROOT=public_root,
            ):
                self.remove_to_fallback()

            self.assertFalse(private_root.exists())
            self.assertFalse(public_root.exists())
            self.assertEqual(list(Path(temporary_directory).iterdir()), [])

        self.assertFalse(
            any(
                field.get_internal_type() == "FileField"
                for field in ImageReviewEvent._meta.fields
            )
        )

    def test_restore_archived_asset_from_fallback_creates_new_revision_without_new_approval(self):
        asset, rendition_set = self.create_image_domain()
        source = self.lock_asset(
            rendition_set,
            alt_text="  Tidligere alt-tekst  ",
            public_credit="  Tidligere kreditering  ",
        ).selection
        active = self.remove_to_fallback().selection
        source_before = OrganizationImageSelection.objects.filter(pk=source.pk).values().get()
        active_before = OrganizationImageSelection.objects.filter(pk=active.pk).values().get()

        result = self.restore_archived(source)

        source.refresh_from_db()
        active.refresh_from_db()
        self.assertEqual(
            OrganizationImageSelection.objects.filter(pk=source.pk).values().get(),
            source_before,
        )
        self.assertEqual(
            OrganizationImageSelection.objects.filter(pk=active.pk).values().get(),
            {**active_before, "status": OrganizationImageSelection.Status.ARCHIVED},
        )
        self.assertEqual(result.previous_selection, active)
        self.assertEqual(result.selection.revision, 3)
        self.assertEqual(result.selection.status, OrganizationImageSelection.Status.ACTIVE)
        self.assertEqual(result.selection.selection_kind, OrganizationImageSelection.SelectionKind.ASSET)
        self.assertEqual(result.selection.rendition_set_id, source.rendition_set_id)
        self.assertEqual(result.selection.alt_text, source.alt_text)
        self.assertEqual(result.selection.public_credit, source.public_credit)
        self.assertEqual(result.selection.locked_by, self.actor)
        self.assertEqual(result.selection.locked_at, result.event.created_at)
        self.assertEqual(
            OrganizationImageSelection.objects.filter(
                organization=self.organization,
                status=OrganizationImageSelection.Status.ACTIVE,
            ).count(),
            1,
        )
        self.assertEqual(result.event.event_type, ImageReviewEvent.EventType.SELECTION_RESTORED)
        self.assertEqual(result.event.selection, result.selection)
        self.assertEqual(result.event.previous_selection, active)
        self.assertEqual(result.event.restored_from_selection, source)
        self.assertEqual(result.event.previous_selection_id_snapshot, active.pk)
        self.assertEqual(result.event.previous_selection_revision_snapshot, active.revision)
        self.assertEqual(result.event.restored_from_selection_id_snapshot, source.pk)
        self.assertEqual(result.event.restored_from_selection_revision_snapshot, source.revision)
        self.assertEqual(result.event.rendition_set_id_snapshot, rendition_set.pk)
        self.assertEqual(result.event.asset_id_snapshot, asset.pk)
        self.assertEqual(result.event.asset_checksum_sha256_snapshot, asset.checksum_sha256)
        self.assertEqual(
            result.event.asset_validation_version_snapshot,
            asset.validation_version,
        )
        self.assertEqual(result.event.alt_text_snapshot, source.alt_text)
        self.assertEqual(result.event.public_credit_snapshot, source.public_credit)
        self.assertEqual(result.event.approval_text_version_snapshot, "")
        self.assertEqual(result.event.approval_text_snapshot, "")
        self.assertEqual(result.event.source_type_snapshot, "")
        self.assertEqual(result.event.source_url_snapshot, "")
        self.assertEqual(result.event.source_page_url_snapshot, "")
        self.assertEqual(result.event.provider_snapshot, "")
        self.assertEqual(result.event.technical_warnings_snapshot, [])

    def test_restore_archived_asset_over_active_asset_and_reuses_source_more_than_once(self):
        _, first_rendition_set = self.create_image_domain()
        _, second_rendition_set = self.create_image_domain()
        source = self.lock_asset(first_rendition_set).selection
        active_asset = self.lock_asset(second_rendition_set, expected_revision=1).selection

        first_restore = self.restore_archived(source)
        self.assertEqual(first_restore.previous_selection, active_asset)
        self.assertEqual(first_restore.selection.revision, 3)
        self.assertEqual(first_restore.selection.rendition_set_id, source.rendition_set_id)

        fallback = self.remove_to_fallback(
            expected_revision=3,
            fallback_alt_text="Fallback before repeated restore",
        ).selection
        second_restore = self.restore_archived(
            source,
            expected_revision=4,
        )
        source.refresh_from_db()
        self.assertEqual(source.status, OrganizationImageSelection.Status.ARCHIVED)
        self.assertEqual(second_restore.previous_selection, fallback)
        self.assertEqual(second_restore.selection.revision, 5)
        self.assertNotEqual(first_restore.selection.pk, source.pk)
        self.assertNotEqual(second_restore.selection.pk, source.pk)
        self.assertNotEqual(first_restore.selection.pk, second_restore.selection.pk)
        self.assertEqual(
            ImageReviewEvent.objects.filter(
                event_type=ImageReviewEvent.EventType.SELECTION_RESTORED,
                restored_from_selection=source,
            ).count(),
            2,
        )

    def test_restore_feature_off_and_revision_conflict_make_no_writes(self):
        _, rendition_set = self.create_image_domain()
        source = self.lock_asset(rendition_set).selection
        self.remove_to_fallback()
        selections_before = list(OrganizationImageSelection.objects.order_by("pk").values())
        events_before = list(ImageReviewEvent.objects.order_by("pk").values())

        with override_settings(IMAGE_ASSET_FEATURE_ENABLED=False):
            with self.assertRaises(ImageFeatureDisabledError):
                self.restore_archived(source)
        with self.assertRaises(ExpectedRevisionConflictError):
            self.restore_archived(source, expected_revision=1)

        self.assertEqual(list(OrganizationImageSelection.objects.order_by("pk").values()), selections_before)
        self.assertEqual(list(ImageReviewEvent.objects.order_by("pk").values()), events_before)

    def test_restore_rejects_missing_active_and_missing_source_without_writes(self):
        _, rendition_set = self.create_image_domain()
        archived_source = OrganizationImageSelection.objects.create(
            tenant=self.tenant,
            organization=self.organization,
            selection_kind=OrganizationImageSelection.SelectionKind.ASSET,
            rendition_set=rendition_set,
            alt_text="Archived source",
            revision=1,
            status=OrganizationImageSelection.Status.ARCHIVED,
            locked_by=self.actor,
            locked_at=timezone.now(),
        )
        with self.assertRaises(InvalidImageSelectionTransitionError):
            restore_archived_organization_image_selection(
                actor=self.actor,
                tenant_id=self.tenant.pk,
                organization_id=self.organization.pk,
                expected_revision=0,
                source_selection_id=archived_source.pk,
            )

        active = OrganizationImageSelection.objects.create(
            tenant=self.tenant,
            organization=self.organization,
            selection_kind=OrganizationImageSelection.SelectionKind.SYSTEM_FALLBACK,
            rendition_set=None,
            alt_text="Active fallback",
            revision=2,
            status=OrganizationImageSelection.Status.ACTIVE,
            locked_by=self.actor,
            locked_at=timezone.now(),
        )
        before = list(OrganizationImageSelection.objects.order_by("pk").values())
        with self.assertRaises(ImageSelectionNotFoundError):
            self.restore_archived(active, source_selection_id=999999)
        self.assertEqual(list(OrganizationImageSelection.objects.order_by("pk").values()), before)
        self.assertEqual(ImageReviewEvent.objects.count(), 0)

    def test_restore_source_is_scoped_to_tenant_and_organization(self):
        active = self.lock_fallback().selection
        other_organization = Organization.objects.create(
            tenant=self.tenant,
            name="Other restore organization",
        )
        _, other_org_rendition_set = self.create_image_domain()
        other_org_source = OrganizationImageSelection.objects.create(
            tenant=self.tenant,
            organization=other_organization,
            selection_kind=OrganizationImageSelection.SelectionKind.ASSET,
            rendition_set=other_org_rendition_set,
            alt_text="Other organization source",
            revision=1,
            status=OrganizationImageSelection.Status.ARCHIVED,
            locked_by=self.actor,
            locked_at=timezone.now(),
        )
        other_actor = get_user_model().objects.create_user(
            username="other-restore-editor",
            password="test-password",
        )
        TenantMembership.objects.create(
            tenant=self.other_tenant,
            user=other_actor,
            role=TenantMembership.Role.REDIGERER,
        )
        _, other_tenant_rendition_set = self.create_image_domain(tenant=self.other_tenant)
        other_tenant_organization = Organization.objects.create(
            tenant=self.other_tenant,
            name="Other tenant restore organization",
        )
        other_tenant_source = OrganizationImageSelection.objects.create(
            tenant=self.other_tenant,
            organization=other_tenant_organization,
            selection_kind=OrganizationImageSelection.SelectionKind.ASSET,
            rendition_set=other_tenant_rendition_set,
            alt_text="Other tenant source",
            revision=1,
            status=OrganizationImageSelection.Status.ARCHIVED,
            locked_by=other_actor,
            locked_at=timezone.now(),
        )
        before = OrganizationImageSelection.objects.filter(pk=active.pk).values().get()

        for source in (other_org_source, other_tenant_source):
            with self.subTest(source=source.pk):
                with self.assertRaises(ImageSelectionNotFoundError):
                    self.restore_archived(source)

        self.assertEqual(OrganizationImageSelection.objects.filter(pk=active.pk).values().get(), before)
        self.assertEqual(ImageReviewEvent.objects.count(), 1)

    def test_restore_rejects_active_fallback_and_same_or_newer_revision_sources(self):
        active_fallback = self.lock_fallback().selection
        with self.assertRaises(InvalidImageSelectionTransitionError):
            self.restore_archived(active_fallback)

        _, rendition_set = self.create_image_domain()
        newer_archived_asset = OrganizationImageSelection.objects.create(
            tenant=self.tenant,
            organization=self.organization,
            selection_kind=OrganizationImageSelection.SelectionKind.ASSET,
            rendition_set=rendition_set,
            alt_text="Newer archived asset",
            revision=2,
            status=OrganizationImageSelection.Status.ARCHIVED,
            locked_by=self.actor,
            locked_at=timezone.now(),
        )
        with self.assertRaises(InvalidImageSelectionTransitionError):
            self.restore_archived(newer_archived_asset)

        _, replacement_rendition_set = self.create_image_domain()
        active_asset = self.lock_asset(replacement_rendition_set, expected_revision=1).selection
        active_fallback.refresh_from_db()
        with self.assertRaises(InvalidImageSelectionTransitionError):
            self.restore_archived(active_fallback, expected_revision=active_asset.revision)
        with self.assertRaises(InvalidImageSelectionTransitionError):
            self.restore_archived(active_asset, expected_revision=active_asset.revision)

        self.assertEqual(OrganizationImageSelection.objects.filter(status="active").count(), 1)
        self.assertEqual(ImageReviewEvent.objects.count(), 2)

    def test_restore_rejects_incomplete_rendition_set_without_writes(self):
        _, incomplete_rendition_set = self.create_image_domain(
            variants=(ImageRendition.Variant.SQUARE,),
        )
        source = OrganizationImageSelection.objects.create(
            tenant=self.tenant,
            organization=self.organization,
            selection_kind=OrganizationImageSelection.SelectionKind.ASSET,
            rendition_set=incomplete_rendition_set,
            alt_text="Incomplete source",
            revision=1,
            status=OrganizationImageSelection.Status.ARCHIVED,
            locked_by=self.actor,
            locked_at=timezone.now(),
        )
        active = OrganizationImageSelection.objects.create(
            tenant=self.tenant,
            organization=self.organization,
            selection_kind=OrganizationImageSelection.SelectionKind.SYSTEM_FALLBACK,
            rendition_set=None,
            alt_text="Active fallback",
            revision=2,
            status=OrganizationImageSelection.Status.ACTIVE,
            locked_by=self.actor,
            locked_at=timezone.now(),
        )
        before = list(OrganizationImageSelection.objects.order_by("pk").values())

        with self.assertRaises(IncompleteRenditionSetError):
            self.restore_archived(source)

        self.assertEqual(list(OrganizationImageSelection.objects.order_by("pk").values()), before)
        self.assertEqual(active.status, OrganizationImageSelection.Status.ACTIVE)
        self.assertEqual(ImageReviewEvent.objects.count(), 0)

    def test_restore_uses_allowed_capability_matrix(self):
        cases = (
            ("restore-platform-admin", None, True),
            ("restore-tenant-admin", TenantMembership.Role.SUPERADMIN, False),
            ("restore-group-admin", TenantMembership.Role.GRUPPEADMIN, False),
            ("restore-editor", TenantMembership.Role.REDIGERER, False),
        )
        for index, (username, role, is_superuser) in enumerate(cases, start=1):
            organization = Organization.objects.create(
                tenant=self.tenant,
                name=f"Restore capability organization {index}",
            )
            user = get_user_model().objects.create_user(
                username=username,
                password="test-password",
                is_superuser=is_superuser,
                is_staff=is_superuser,
            )
            if role:
                TenantMembership.objects.create(tenant=self.tenant, user=user, role=role)
            _, rendition_set = self.create_image_domain()
            source = OrganizationImageSelection.objects.create(
                tenant=self.tenant,
                organization=organization,
                selection_kind=OrganizationImageSelection.SelectionKind.ASSET,
                rendition_set=rendition_set,
                alt_text="Capability source",
                revision=1,
                status=OrganizationImageSelection.Status.ARCHIVED,
                locked_by=self.actor,
                locked_at=timezone.now(),
            )
            OrganizationImageSelection.objects.create(
                tenant=self.tenant,
                organization=organization,
                selection_kind=OrganizationImageSelection.SelectionKind.SYSTEM_FALLBACK,
                rendition_set=None,
                alt_text="Capability fallback",
                revision=2,
                status=OrganizationImageSelection.Status.ACTIVE,
                locked_by=self.actor,
                locked_at=timezone.now(),
            )

            with self.subTest(role=role, is_superuser=is_superuser):
                result = restore_archived_organization_image_selection(
                    actor=user,
                    tenant_id=self.tenant.pk,
                    organization_id=organization.pk,
                    expected_revision=2,
                    source_selection_id=source.pk,
                )
                self.assertEqual(result.selection.tenant_id, self.tenant.pk)

    def test_restore_denies_unauthorized_actors_without_writes(self):
        _, rendition_set = self.create_image_domain()
        source = self.lock_asset(rendition_set).selection
        self.remove_to_fallback()
        reader = get_user_model().objects.create_user(username="restore-reader", password="test-password")
        TenantMembership.objects.create(tenant=self.tenant, user=reader, role=TenantMembership.Role.LESER)
        no_membership = get_user_model().objects.create_user(username="restore-none", password="test-password")
        wrong_tenant = get_user_model().objects.create_user(username="restore-wrong", password="test-password")
        TenantMembership.objects.create(
            tenant=self.other_tenant,
            user=wrong_tenant,
            role=TenantMembership.Role.REDIGERER,
        )
        inactive = get_user_model().objects.create_user(
            username="restore-inactive",
            password="test-password",
            is_active=False,
        )
        TenantMembership.objects.create(
            tenant=self.tenant,
            user=inactive,
            role=TenantMembership.Role.REDIGERER,
        )
        selections_before = list(OrganizationImageSelection.objects.order_by("pk").values())
        events_before = list(ImageReviewEvent.objects.order_by("pk").values())

        for actor in (reader, no_membership, wrong_tenant, inactive, AnonymousUser()):
            with self.subTest(actor=str(actor)):
                with self.assertRaises(ImageSelectionPermissionDenied):
                    self.restore_archived(source, actor=actor)

        self.assertEqual(list(OrganizationImageSelection.objects.order_by("pk").values()), selections_before)
        self.assertEqual(list(ImageReviewEvent.objects.order_by("pk").values()), events_before)

    def test_restore_event_failure_rolls_back_new_revision_and_archiving(self):
        _, rendition_set = self.create_image_domain()
        source = self.lock_asset(rendition_set).selection
        active = self.remove_to_fallback().selection
        source_before = OrganizationImageSelection.objects.filter(pk=source.pk).values().get()
        active_before = OrganizationImageSelection.objects.filter(pk=active.pk).values().get()

        with patch.object(ImageReviewEvent, "save", side_effect=RuntimeError("restore event failure")):
            with self.assertRaisesRegex(RuntimeError, "restore event failure"):
                self.restore_archived(source)

        self.assertEqual(OrganizationImageSelection.objects.filter(pk=source.pk).values().get(), source_before)
        self.assertEqual(OrganizationImageSelection.objects.filter(pk=active.pk).values().get(), active_before)
        self.assertEqual(OrganizationImageSelection.objects.count(), 2)
        self.assertEqual(ImageReviewEvent.objects.count(), 2)

    def test_restore_source_set_null_preserves_snapshots_and_manager_blocks_snapshot_changes(self):
        _, rendition_set = self.create_image_domain()
        source = self.lock_asset(rendition_set).selection
        self.remove_to_fallback()
        event = self.restore_archived(source).event
        snapshots = (
            event.restored_from_selection_id_snapshot,
            event.restored_from_selection_revision_snapshot,
        )

        with self.assertRaises(AppendOnlyEventError):
            ImageReviewEvent.objects.filter(pk=event.pk).update(
                restored_from_selection_id_snapshot=999,
            )
        with self.assertRaises(AppendOnlyEventError):
            ImageReviewEvent._base_objects.filter(pk=event.pk).update(
                restored_from_selection_id_snapshot=999,
            )

        source.delete()
        event = ImageReviewEvent._base_objects.get(pk=event.pk)
        self.assertIsNone(event.restored_from_selection_id)
        self.assertEqual(
            (
                event.restored_from_selection_id_snapshot,
                event.restored_from_selection_revision_snapshot,
            ),
            snapshots,
        )

    def test_restore_event_database_constraints_require_restore_snapshots_and_no_approval(self):
        _, rendition_set = self.create_image_domain()
        source = self.lock_asset(rendition_set).selection
        self.remove_to_fallback()
        restored_event = self.restore_archived(source).event
        values = ImageReviewEvent._base_objects.filter(pk=restored_event.pk).values().get()
        values.pop("id")

        for field_name in (
            "restored_from_selection_id_snapshot",
            "restored_from_selection_revision_snapshot",
        ):
            invalid = {**values, field_name: None}
            with self.subTest(field_name=field_name):
                with self.assertRaises(IntegrityError):
                    with transaction.atomic():
                        ImageReviewEvent.objects.create(**invalid)

        invalid_approval = {
            **values,
            "approval_text_version_snapshot": IMAGE_APPROVAL_TEXT_VERSION,
            "approval_text_snapshot": IMAGE_APPROVAL_TEXT,
        }
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ImageReviewEvent.objects.create(**invalid_approval)

        locked_event = ImageReviewEvent.objects.exclude(pk=restored_event.pk).first()
        non_restore_values = ImageReviewEvent._base_objects.filter(pk=locked_event.pk).values().get()
        non_restore_values.pop("id")
        non_restore_values["restored_from_selection_id_snapshot"] = source.pk
        non_restore_values["restored_from_selection_revision_snapshot"] = source.revision
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ImageReviewEvent.objects.create(**non_restore_values)

    def test_restore_preserves_publication_legacy_fields_and_performs_no_storage_io(self):
        _, rendition_set = self.create_image_domain()
        source = self.lock_asset(rendition_set).selection
        self.remove_to_fallback()
        person = Person.objects.create(
            tenant=self.tenant,
            full_name="Restore public person",
            email="restore@example.com",
            phone="12345678",
        )
        link = OrganizationPerson.objects.create(
            tenant=self.tenant,
            organization=self.organization,
            person=person,
            publish_person=True,
        )
        contact = PersonContact.objects.create(
            tenant=self.tenant,
            person=person,
            type="EMAIL",
            value="restore@example.com",
            is_primary=True,
            is_public=True,
        )
        organization_before = Organization.objects.filter(pk=self.organization.pk).values().get()
        person_before = Person.objects.filter(pk=person.pk).values().get()
        link_before = OrganizationPerson.objects.filter(pk=link.pk).values().get()
        contact_before = PersonContact.objects.filter(pk=contact.pk).values().get()

        with tempfile.TemporaryDirectory() as temporary_directory:
            private_root = Path(temporary_directory) / "private"
            public_root = Path(temporary_directory) / "public"
            with override_settings(
                IMAGE_ORIGINALS_ROOT=private_root,
                IMAGE_RENDITIONS_ROOT=public_root,
            ):
                self.restore_archived(source)
            self.assertFalse(private_root.exists())
            self.assertFalse(public_root.exists())
            self.assertEqual(list(Path(temporary_directory).iterdir()), [])

        self.assertEqual(Organization.objects.filter(pk=self.organization.pk).values().get(), organization_before)
        self.assertEqual(Person.objects.filter(pk=person.pk).values().get(), person_before)
        self.assertEqual(OrganizationPerson.objects.filter(pk=link.pk).values().get(), link_before)
        self.assertEqual(PersonContact.objects.filter(pk=contact.pk).values().get(), contact_before)
        self.assertEqual(
            set(inspect.signature(restore_archived_organization_image_selection).parameters),
            {"actor", "tenant_id", "organization_id", "expected_revision", "source_selection_id"},
        )


@override_settings(IMAGE_ASSET_FEATURE_ENABLED=True)
class OrganizationImageSelectionConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.tenant = Tenant.objects.create(name="Concurrency tenant", slug="concurrency")
        self.organization = Organization.objects.create(
            tenant=self.tenant,
            name="Concurrency organization",
        )
        self.actors = []
        for index in range(2):
            actor = get_user_model().objects.create_user(
                username=f"concurrency-editor-{index}",
                password="test-password",
            )
            TenantMembership.objects.create(
                tenant=self.tenant,
                user=actor,
                role=TenantMembership.Role.REDIGERER,
            )
            self.actors.append(actor)

    def test_same_expected_revision_is_serialized_by_organization_lock(self):
        barrier = threading.Barrier(2)
        outcomes = []
        outcome_lock = threading.Lock()

        def run_command(actor_id):
            close_old_connections()
            actor = get_user_model().objects.get(pk=actor_id)
            barrier.wait(timeout=10)
            try:
                result = lock_organization_image_selection(
                    actor=actor,
                    tenant_id=self.tenant.pk,
                    organization_id=self.organization.pk,
                    expected_revision=0,
                    selection_kind=OrganizationImageSelection.SelectionKind.SYSTEM_FALLBACK,
                    alt_text="Concurrent fallback",
                )
                outcome = ("success", result.selection.revision)
            except (ExpectedRevisionConflictError, ImageSelectionConcurrencyError) as error:
                outcome = ("conflict", type(error).__name__)
            finally:
                close_old_connections()
            with outcome_lock:
                outcomes.append(outcome)

        threads = [
            threading.Thread(target=run_command, args=(actor.pk,))
            for actor in self.actors
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=20)

        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual([outcome[0] for outcome in outcomes].count("success"), 1)
        self.assertEqual([outcome[0] for outcome in outcomes].count("conflict"), 1)
        self.assertEqual(OrganizationImageSelection.objects.count(), 1)
        self.assertEqual(ImageReviewEvent.objects.count(), 1)
        self.assertEqual(
            OrganizationImageSelection.objects.filter(status="active").count(),
            1,
        )
        self.assertEqual(
            list(OrganizationImageSelection.objects.values_list("revision", flat=True)),
            [1],
        )

    def test_concurrent_removal_creates_at_most_one_fallback_revision(self):
        asset = ImageAsset.objects.create(
            tenant=self.tenant,
            private_storage_key="assets/concurrent-removal.jpeg",
            checksum_sha256="a" * 64,
            original_format=ImageAsset.OriginalFormat.JPEG,
            mime_type="image/jpeg",
            width=1600,
            height=900,
            file_size_bytes=123456,
            validation_version="validation-v1",
        )
        rendition_set = ImageRenditionSet.objects.create(
            tenant=self.tenant,
            asset=asset,
            fit_mode=ImageRenditionSet.FitMode.COVER,
            processing_version="processing-v1",
            render_config_hash_sha256="b" * 64,
        )
        for index, variant in enumerate(
            (
                ImageRendition.Variant.SQUARE,
                ImageRendition.Variant.LANDSCAPE,
                ImageRendition.Variant.SHARE,
            ),
            start=1,
        ):
            ImageRendition.objects.create(
                tenant=self.tenant,
                rendition_set=rendition_set,
                variant=variant,
                output_format=ImageRendition.OutputFormat.WEBP,
                width=512 + index,
                height=512 + index,
                file_size_bytes=20000 + index,
                checksum_sha256=f"{index}" * 64,
                artifact_storage_key=f"renditions/concurrent-removal-{variant}.webp",
            )
        first = lock_organization_image_selection(
            actor=self.actors[0],
            tenant_id=self.tenant.pk,
            organization_id=self.organization.pk,
            expected_revision=0,
            selection_kind=OrganizationImageSelection.SelectionKind.ASSET,
            rendition_set_id=rendition_set.pk,
            alt_text="Concurrent asset",
            asset_evidence=AssetApprovalEvidence(
                source_type=ImageReviewEvent.SourceType.UPLOAD,
            ),
        )
        barrier = threading.Barrier(2)
        outcomes = []
        outcome_lock = threading.Lock()

        def run_command(actor_id):
            close_old_connections()
            actor = get_user_model().objects.get(pk=actor_id)
            barrier.wait(timeout=10)
            try:
                result = remove_organization_image_to_fallback(
                    actor=actor,
                    tenant_id=self.tenant.pk,
                    organization_id=self.organization.pk,
                    expected_revision=1,
                    fallback_alt_text="Concurrent fallback",
                )
                outcome = ("success", result.selection.revision)
            except (
                ExpectedRevisionConflictError,
                ImageSelectionConcurrencyError,
                InvalidImageSelectionTransitionError,
            ) as error:
                outcome = ("conflict", type(error).__name__)
            finally:
                close_old_connections()
            with outcome_lock:
                outcomes.append(outcome)

        threads = [
            threading.Thread(target=run_command, args=(actor.pk,))
            for actor in self.actors
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=20)

        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual([outcome[0] for outcome in outcomes].count("success"), 1)
        self.assertEqual([outcome[0] for outcome in outcomes].count("conflict"), 1)
        first.selection.refresh_from_db()
        self.assertEqual(first.selection.status, OrganizationImageSelection.Status.ARCHIVED)
        self.assertEqual(OrganizationImageSelection.objects.count(), 2)
        self.assertEqual(ImageReviewEvent.objects.count(), 2)
        self.assertEqual(
            OrganizationImageSelection.objects.filter(
                status=OrganizationImageSelection.Status.ACTIVE,
            ).count(),
            1,
        )
        self.assertEqual(
            ImageReviewEvent.objects.filter(
                event_type=ImageReviewEvent.EventType.SELECTION_REMOVED_TO_FALLBACK,
            ).count(),
            1,
        )

    def test_concurrent_restore_creates_exactly_one_new_revision_and_event(self):
        asset = ImageAsset.objects.create(
            tenant=self.tenant,
            private_storage_key="assets/concurrent-restore.jpeg",
            checksum_sha256="d" * 64,
            original_format=ImageAsset.OriginalFormat.JPEG,
            mime_type="image/jpeg",
            width=1600,
            height=900,
            file_size_bytes=123456,
            validation_version="validation-v1",
        )
        rendition_set = ImageRenditionSet.objects.create(
            tenant=self.tenant,
            asset=asset,
            fit_mode=ImageRenditionSet.FitMode.COVER,
            processing_version="processing-v1",
            render_config_hash_sha256="e" * 64,
        )
        for index, variant in enumerate(
            (
                ImageRendition.Variant.SQUARE,
                ImageRendition.Variant.LANDSCAPE,
                ImageRendition.Variant.SHARE,
            ),
            start=1,
        ):
            ImageRendition.objects.create(
                tenant=self.tenant,
                rendition_set=rendition_set,
                variant=variant,
                output_format=ImageRendition.OutputFormat.WEBP,
                width=512 + index,
                height=512 + index,
                file_size_bytes=20000 + index,
                checksum_sha256=f"{index + 3}" * 64,
                artifact_storage_key=f"renditions/concurrent-restore-{variant}.webp",
            )
        source = OrganizationImageSelection.objects.create(
            tenant=self.tenant,
            organization=self.organization,
            selection_kind=OrganizationImageSelection.SelectionKind.ASSET,
            rendition_set=rendition_set,
            alt_text="Concurrent restore source",
            public_credit="Concurrent credit",
            revision=1,
            status=OrganizationImageSelection.Status.ARCHIVED,
            locked_by=self.actors[0],
            locked_at=timezone.now(),
        )
        active = OrganizationImageSelection.objects.create(
            tenant=self.tenant,
            organization=self.organization,
            selection_kind=OrganizationImageSelection.SelectionKind.SYSTEM_FALLBACK,
            rendition_set=None,
            alt_text="Concurrent active fallback",
            revision=2,
            status=OrganizationImageSelection.Status.ACTIVE,
            locked_by=self.actors[0],
            locked_at=timezone.now(),
        )
        barrier = threading.Barrier(2)
        outcomes = []
        outcome_lock = threading.Lock()

        def run_command(actor_id):
            close_old_connections()
            actor = get_user_model().objects.get(pk=actor_id)
            barrier.wait(timeout=10)
            try:
                result = restore_archived_organization_image_selection(
                    actor=actor,
                    tenant_id=self.tenant.pk,
                    organization_id=self.organization.pk,
                    expected_revision=2,
                    source_selection_id=source.pk,
                )
                outcome = ("success", result.selection.revision)
            except (ExpectedRevisionConflictError, ImageSelectionConcurrencyError) as error:
                outcome = ("conflict", type(error).__name__)
            finally:
                close_old_connections()
            with outcome_lock:
                outcomes.append(outcome)

        threads = [
            threading.Thread(target=run_command, args=(actor.pk,))
            for actor in self.actors
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=20)

        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual([outcome[0] for outcome in outcomes].count("success"), 1)
        self.assertEqual([outcome[0] for outcome in outcomes].count("conflict"), 1)
        source.refresh_from_db()
        active.refresh_from_db()
        self.assertEqual(source.status, OrganizationImageSelection.Status.ARCHIVED)
        self.assertEqual(active.status, OrganizationImageSelection.Status.ARCHIVED)
        self.assertEqual(OrganizationImageSelection.objects.count(), 3)
        self.assertEqual(
            OrganizationImageSelection.objects.filter(status=OrganizationImageSelection.Status.ACTIVE).count(),
            1,
        )
        self.assertEqual(
            ImageReviewEvent.objects.filter(
                event_type=ImageReviewEvent.EventType.SELECTION_RESTORED,
            ).count(),
            1,
        )


class ImageReviewEventMigrationTests(TransactionTestCase):
    migrate_from = ("crm", "0022_organization_image_selection")
    migrate_to = ("crm", "0023_imagereviewevent")

    def test_additive_event_migration_preserves_existing_image_data_and_reverses(self):
        migration_module = importlib.import_module("crm.migrations.0023_imagereviewevent")
        self.assertEqual(len(migration_module.Migration.operations), 1)
        self.assertEqual(
            migration_module.Migration.operations[0].__class__.__name__,
            "CreateModel",
        )

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        old_apps = executor.loader.project_state([self.migrate_from]).apps
        OldTenant = old_apps.get_model("crm", "Tenant")
        OldOrganization = old_apps.get_model("crm", "Organization")
        OldImageAsset = old_apps.get_model("crm", "ImageAsset")
        OldImageRenditionSet = old_apps.get_model("crm", "ImageRenditionSet")
        OldImageRendition = old_apps.get_model("crm", "ImageRendition")
        OldSelection = old_apps.get_model("crm", "OrganizationImageSelection")
        OldUser = old_apps.get_model(*settings.AUTH_USER_MODEL.split("."))

        tenant = OldTenant.objects.create(name="Event migration", slug="event-migration")
        organization = OldOrganization.objects.create(
            tenant=tenant,
            name="Existing event organization",
        )
        user = OldUser.objects.create(username="event-migration-user")
        asset = OldImageAsset.objects.create(
            tenant=tenant,
            private_storage_key="assets/event-existing.jpeg",
            checksum_sha256="a" * 64,
            original_format="jpeg",
            mime_type="image/jpeg",
            width=1600,
            height=900,
            file_size_bytes=123456,
            validation_version="validation-v1",
        )
        rendition_set = OldImageRenditionSet.objects.create(
            tenant=tenant,
            asset=asset,
            fit_mode="cover",
            processing_version="processing-v1",
            render_config_hash_sha256="b" * 64,
        )
        rendition = OldImageRendition.objects.create(
            tenant=tenant,
            rendition_set=rendition_set,
            variant="square",
            output_format="webp",
            width=512,
            height=512,
            file_size_bytes=12345,
            checksum_sha256="c" * 64,
            artifact_storage_key="renditions/event-existing-square.webp",
        )
        selection = OldSelection.objects.create(
            tenant=tenant,
            organization=organization,
            selection_kind="asset",
            rendition_set=rendition_set,
            alt_text="Existing selection",
            public_credit="",
            revision=1,
            status="active",
            locked_by=user,
            locked_at=timezone.now(),
        )
        model_ids = {
            "Tenant": tenant.pk,
            "Organization": organization.pk,
            "ImageAsset": asset.pk,
            "ImageRenditionSet": rendition_set.pk,
            "ImageRendition": rendition.pk,
            "OrganizationImageSelection": selection.pk,
        }
        snapshots = {
            model_name: old_apps.get_model("crm", model_name)
            .objects.filter(pk=model_id)
            .values()
            .get()
            for model_name, model_id in model_ids.items()
        }

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        new_apps = executor.loader.project_state([self.migrate_to]).apps
        for model_name, expected in snapshots.items():
            with self.subTest(model_name=model_name):
                actual = (
                    new_apps.get_model("crm", model_name)
                    .objects.filter(pk=model_ids[model_name])
                    .values()
                    .get()
                )
                self.assertEqual(actual, expected)
        self.assertEqual(new_apps.get_model("crm", "ImageReviewEvent").objects.count(), 0)

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        restored_apps = executor.loader.project_state([self.migrate_from]).apps
        self.assertTrue(
            restored_apps.get_model("crm", "OrganizationImageSelection")
            .objects.filter(pk=selection.pk)
            .exists()
        )

        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())


class ImageRemovalEventMigrationTests(TransactionTestCase):
    migrate_from = ("crm", "0023_imagereviewevent")
    migrate_to = (
        "crm",
        "0024_remove_imagereviewevent_img_evt_previous_contract_and_more",
    )

    def test_event_contract_migration_preserves_old_rows_and_reapplies(self):
        migration_module = importlib.import_module(
            "crm.migrations.0024_remove_imagereviewevent_img_evt_previous_contract_and_more"
        )
        self.assertEqual(
            [operation.__class__.__name__ for operation in migration_module.Migration.operations],
            ["RemoveConstraint", "AlterField", "AddConstraint"],
        )

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        old_apps = executor.loader.project_state([self.migrate_from]).apps
        OldTenant = old_apps.get_model("crm", "Tenant")
        OldOrganization = old_apps.get_model("crm", "Organization")
        OldSelection = old_apps.get_model("crm", "OrganizationImageSelection")
        OldEvent = old_apps.get_model("crm", "ImageReviewEvent")
        OldUser = old_apps.get_model(*settings.AUTH_USER_MODEL.split("."))

        tenant = OldTenant.objects.create(name="Removal migration", slug="removal-migration")
        organization = OldOrganization.objects.create(
            tenant=tenant,
            name="Removal migration organization",
        )
        user = OldUser.objects.create(username="removal-migration-user")
        selection = OldSelection.objects.create(
            tenant=tenant,
            organization=organization,
            selection_kind="system_fallback",
            rendition_set=None,
            alt_text="Existing fallback",
            public_credit="",
            revision=1,
            status="active",
            locked_by=user,
            locked_at=timezone.now(),
        )
        event = OldEvent.objects.create(
            tenant=tenant,
            organization=organization,
            selection=selection,
            actor_user=user,
            event_type="selection_locked",
            organization_id_snapshot=organization.pk,
            organization_name_snapshot=organization.name,
            organization_org_number_snapshot="",
            selection_id_snapshot=selection.pk,
            selection_revision_snapshot=1,
            selection_kind_snapshot="system_fallback",
            actor_user_id_snapshot=user.pk,
            actor_username_snapshot=user.username,
            alt_text_snapshot=selection.alt_text,
            created_at=timezone.now(),
        )
        event_before = OldEvent.objects.filter(pk=event.pk).values().get()

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        new_apps = executor.loader.project_state([self.migrate_to]).apps
        NewEvent = new_apps.get_model("crm", "ImageReviewEvent")
        self.assertEqual(NewEvent.objects.filter(pk=event.pk).values().get(), event_before)
        event_type_field = NewEvent._meta.get_field("event_type")
        self.assertEqual(event_type_field.max_length, 29)
        self.assertIn(
            "selection_removed_to_fallback",
            {value for value, _label in event_type_field.choices},
        )

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        restored_apps = executor.loader.project_state([self.migrate_from]).apps
        self.assertEqual(
            restored_apps.get_model("crm", "ImageReviewEvent")
            .objects.filter(pk=event.pk)
            .values()
            .get(),
            event_before,
        )

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        reapplied_apps = executor.loader.project_state([self.migrate_to]).apps
        self.assertEqual(
            reapplied_apps.get_model("crm", "ImageReviewEvent")
            .objects.filter(pk=event.pk)
            .values()
            .get(),
            event_before,
        )

        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())


class ImageRestoreEventMigrationTests(TransactionTestCase):
    migrate_from = (
        "crm",
        "0024_remove_imagereviewevent_img_evt_previous_contract_and_more",
    )
    migrate_to = ("crm", "0025_restore_archived_image_selection")

    def test_restore_schema_migration_preserves_old_rows_reverses_and_reapplies(self):
        migration_module = importlib.import_module(
            "crm.migrations.0025_restore_archived_image_selection"
        )
        self.assertEqual(
            [operation.__class__.__name__ for operation in migration_module.Migration.operations],
            [
                "RemoveConstraint",
                "RemoveConstraint",
                "AddField",
                "AddField",
                "AddField",
                "AlterField",
                "AddConstraint",
                "AddConstraint",
                "AddConstraint",
            ],
        )

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        old_apps = executor.loader.project_state([self.migrate_from]).apps
        OldTenant = old_apps.get_model("crm", "Tenant")
        OldOrganization = old_apps.get_model("crm", "Organization")
        OldSelection = old_apps.get_model("crm", "OrganizationImageSelection")
        OldEvent = old_apps.get_model("crm", "ImageReviewEvent")
        OldUser = old_apps.get_model(*settings.AUTH_USER_MODEL.split("."))

        tenant = OldTenant.objects.create(name="Restore migration", slug="restore-migration")
        organization = OldOrganization.objects.create(
            tenant=tenant,
            name="Restore migration organization",
        )
        user = OldUser.objects.create(username="restore-migration-user")
        selection = OldSelection.objects.create(
            tenant=tenant,
            organization=organization,
            selection_kind="system_fallback",
            rendition_set=None,
            alt_text="Existing restore migration fallback",
            public_credit="",
            revision=1,
            status="active",
            locked_by=user,
            locked_at=timezone.now(),
        )
        event = OldEvent.objects.create(
            tenant=tenant,
            organization=organization,
            selection=selection,
            actor_user=user,
            event_type="selection_locked",
            organization_id_snapshot=organization.pk,
            organization_name_snapshot=organization.name,
            organization_org_number_snapshot="",
            selection_id_snapshot=selection.pk,
            selection_revision_snapshot=1,
            selection_kind_snapshot="system_fallback",
            actor_user_id_snapshot=user.pk,
            actor_username_snapshot=user.username,
            alt_text_snapshot=selection.alt_text,
            created_at=timezone.now(),
        )
        event_before = OldEvent.objects.filter(pk=event.pk).values().get()

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        new_apps = executor.loader.project_state([self.migrate_to]).apps
        NewEvent = new_apps.get_model("crm", "ImageReviewEvent")
        migrated_event = NewEvent.objects.filter(pk=event.pk).values().get()
        for field_name, expected in event_before.items():
            with self.subTest(field_name=field_name):
                self.assertEqual(migrated_event[field_name], expected)
        self.assertIsNone(migrated_event["restored_from_selection_id"])
        self.assertIsNone(migrated_event["restored_from_selection_id_snapshot"])
        self.assertIsNone(migrated_event["restored_from_selection_revision_snapshot"])
        self.assertIn(
            "selection_restored",
            {value for value, _label in NewEvent._meta.get_field("event_type").choices},
        )

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        restored_apps = executor.loader.project_state([self.migrate_from]).apps
        self.assertEqual(
            restored_apps.get_model("crm", "ImageReviewEvent")
            .objects.filter(pk=event.pk)
            .values()
            .get(),
            event_before,
        )

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        reapplied_apps = executor.loader.project_state([self.migrate_to]).apps
        reapplied_event = (
            reapplied_apps.get_model("crm", "ImageReviewEvent")
            .objects.filter(pk=event.pk)
            .values()
            .get()
        )
        for field_name, expected in event_before.items():
            with self.subTest(reapplied_field=field_name):
                self.assertEqual(reapplied_event[field_name], expected)

        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())


class OptionalImageAltTextMigrationTests(TransactionTestCase):
    migrate_from = ("crm", "0026_organization_image_release_domain")
    migrate_to = ("crm", "0027_optional_image_alt_text")

    def test_schema_only_migration_preserves_existing_rows_reverses_and_reapplies(self):
        migration_module = importlib.import_module(
            "crm.migrations.0027_optional_image_alt_text"
        )
        self.assertEqual(
            [
                operation.__class__.__name__
                for operation in migration_module.Migration.operations
            ],
            [
                "RemoveConstraint",
                "RemoveConstraint",
                "RemoveConstraint",
                "AlterField",
                "AlterField",
                "AddConstraint",
                "AddConstraint",
                "AddConstraint",
            ],
        )

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        old_apps = executor.loader.project_state([self.migrate_from]).apps
        OldTenant = old_apps.get_model("crm", "Tenant")
        OldOrganization = old_apps.get_model("crm", "Organization")
        OldImageAsset = old_apps.get_model("crm", "ImageAsset")
        OldImageRenditionSet = old_apps.get_model("crm", "ImageRenditionSet")
        OldSelection = old_apps.get_model("crm", "OrganizationImageSelection")
        OldEvent = old_apps.get_model("crm", "ImageReviewEvent")
        OldUser = old_apps.get_model(*settings.AUTH_USER_MODEL.split("."))

        tenant = OldTenant.objects.create(
            name="Optional alt migration",
            slug="optional-alt-migration",
        )
        organization = OldOrganization.objects.create(
            tenant=tenant,
            name="Existing optional alt organization",
        )
        user = OldUser.objects.create(username="optional-alt-migration-user")
        asset = OldImageAsset.objects.create(
            tenant=tenant,
            private_storage_key="assets/optional-alt-existing.jpeg",
            checksum_sha256="a" * 64,
            original_format="jpeg",
            mime_type="image/jpeg",
            width=1600,
            height=900,
            file_size_bytes=123456,
            validation_version="validation-v1",
        )
        rendition_set = OldImageRenditionSet.objects.create(
            tenant=tenant,
            asset=asset,
            fit_mode="cover",
            processing_version="processing-v1",
            render_config_hash_sha256="b" * 64,
        )
        selection = OldSelection.objects.create(
            tenant=tenant,
            organization=organization,
            selection_kind="asset",
            rendition_set=rendition_set,
            alt_text="Existing nonempty alt text",
            public_credit="Existing credit",
            revision=1,
            status="active",
            locked_by=user,
            locked_at=timezone.now(),
        )
        event = OldEvent.objects.create(
            tenant=tenant,
            organization=organization,
            selection=selection,
            rendition_set=rendition_set,
            asset=asset,
            actor_user=user,
            event_type="selection_locked",
            organization_id_snapshot=organization.pk,
            organization_name_snapshot=organization.name,
            organization_org_number_snapshot="",
            selection_id_snapshot=selection.pk,
            selection_revision_snapshot=selection.revision,
            selection_kind_snapshot="asset",
            rendition_set_id_snapshot=rendition_set.pk,
            asset_id_snapshot=asset.pk,
            asset_checksum_sha256_snapshot=asset.checksum_sha256,
            asset_validation_version_snapshot=asset.validation_version,
            actor_user_id_snapshot=user.pk,
            actor_username_snapshot=user.username,
            alt_text_snapshot=selection.alt_text,
            public_credit_snapshot=selection.public_credit,
            source_type_snapshot="official_website",
            source_url_snapshot="https://example.com/existing-image.jpg",
            source_page_url_snapshot="https://example.com/existing-page",
            provider_snapshot="existing-provider",
            technical_warnings_snapshot=["existing warning"],
            approval_text_version_snapshot="image-approval-v1",
            approval_text_snapshot="Existing approval text",
            created_at=timezone.now(),
        )
        selection_before = OldSelection.objects.filter(pk=selection.pk).values().get()
        event_before = OldEvent.objects.filter(pk=event.pk).values().get()

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        new_apps = executor.loader.project_state([self.migrate_to]).apps
        NewSelection = new_apps.get_model("crm", "OrganizationImageSelection")
        NewEvent = new_apps.get_model("crm", "ImageReviewEvent")
        self.assertEqual(
            NewSelection.objects.filter(pk=selection.pk).values().get(),
            selection_before,
        )
        self.assertEqual(NewEvent.objects.filter(pk=event.pk).values().get(), event_before)
        for model, field_name in (
            (NewSelection, "alt_text"),
            (NewEvent, "alt_text_snapshot"),
        ):
            with self.subTest(model=model.__name__, field_name=field_name):
                field = model._meta.get_field(field_name)
                self.assertTrue(field.blank)
                self.assertEqual(field.default, "")

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        restored_apps = executor.loader.project_state([self.migrate_from]).apps
        self.assertEqual(
            restored_apps.get_model("crm", "OrganizationImageSelection")
            .objects.filter(pk=selection.pk)
            .values()
            .get(),
            selection_before,
        )
        self.assertEqual(
            restored_apps.get_model("crm", "ImageReviewEvent")
            .objects.filter(pk=event.pk)
            .values()
            .get(),
            event_before,
        )

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        reapplied_apps = executor.loader.project_state([self.migrate_to]).apps
        self.assertEqual(
            reapplied_apps.get_model("crm", "OrganizationImageSelection")
            .objects.filter(pk=selection.pk)
            .values()
            .get(),
            selection_before,
        )
        self.assertEqual(
            reapplied_apps.get_model("crm", "ImageReviewEvent")
            .objects.filter(pk=event.pk)
            .values()
            .get(),
            event_before,
        )

        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())

    def test_reverse_is_blocked_after_blank_asset_and_event_alt_are_stored(self):
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        new_apps = executor.loader.project_state([self.migrate_to]).apps

        NewTenant = new_apps.get_model("crm", "Tenant")
        NewOrganization = new_apps.get_model("crm", "Organization")
        NewImageAsset = new_apps.get_model("crm", "ImageAsset")
        NewImageRenditionSet = new_apps.get_model("crm", "ImageRenditionSet")
        NewSelection = new_apps.get_model("crm", "OrganizationImageSelection")
        NewEvent = new_apps.get_model("crm", "ImageReviewEvent")
        NewUser = new_apps.get_model(*settings.AUTH_USER_MODEL.split("."))

        tenant = NewTenant.objects.create(
            name="Optional alt reverse boundary",
            slug="optional-alt-reverse-boundary",
        )
        organization = NewOrganization.objects.create(
            tenant=tenant,
            name="Blank alt organization",
        )
        user = NewUser.objects.create(username="optional-alt-reverse-user")
        asset = NewImageAsset.objects.create(
            tenant=tenant,
            private_storage_key="assets/optional-alt-blank.jpeg",
            checksum_sha256="c" * 64,
            original_format="jpeg",
            mime_type="image/jpeg",
            width=1600,
            height=900,
            file_size_bytes=123456,
            validation_version="validation-v1",
        )
        rendition_set = NewImageRenditionSet.objects.create(
            tenant=tenant,
            asset=asset,
            fit_mode="cover",
            processing_version="processing-v1",
            render_config_hash_sha256="d" * 64,
        )
        selection = NewSelection.objects.create(
            tenant=tenant,
            organization=organization,
            selection_kind="asset",
            rendition_set=rendition_set,
            alt_text="",
            revision=1,
            status="active",
            locked_by=user,
            locked_at=timezone.now(),
        )
        NewEvent.objects.create(
            tenant=tenant,
            organization=organization,
            selection=selection,
            rendition_set=rendition_set,
            asset=asset,
            actor_user=user,
            event_type="selection_locked",
            organization_id_snapshot=organization.pk,
            organization_name_snapshot=organization.name,
            organization_org_number_snapshot="",
            selection_id_snapshot=selection.pk,
            selection_revision_snapshot=selection.revision,
            selection_kind_snapshot="asset",
            rendition_set_id_snapshot=rendition_set.pk,
            asset_id_snapshot=asset.pk,
            asset_checksum_sha256_snapshot=asset.checksum_sha256,
            asset_validation_version_snapshot=asset.validation_version,
            actor_user_id_snapshot=user.pk,
            actor_username_snapshot=user.username,
            alt_text_snapshot="",
            source_type_snapshot="upload",
            source_url_snapshot="",
            technical_warnings_snapshot=[],
            approval_text_version_snapshot="image-approval-v1",
            approval_text_snapshot="Existing approval text",
            created_at=timezone.now(),
        )

        try:
            with self.assertRaises(IntegrityError):
                MigrationExecutor(connection).migrate([self.migrate_from])

            post_failure_executor = MigrationExecutor(connection)
            self.assertIn(
                self.migrate_to,
                post_failure_executor.loader.applied_migrations,
            )
            current_apps = post_failure_executor.loader.project_state(
                [self.migrate_to]
            ).apps
            self.assertTrue(
                current_apps.get_model("crm", "OrganizationImageSelection")
                .objects.filter(pk=selection.pk, alt_text="")
                .exists()
            )
            self.assertTrue(
                current_apps.get_model("crm", "ImageReviewEvent")
                .objects.filter(selection_id=selection.pk, alt_text_snapshot="")
                .exists()
            )
        finally:
            cleanup_executor = MigrationExecutor(connection)
            cleanup_executor.migrate(cleanup_executor.loader.graph.leaf_nodes())
