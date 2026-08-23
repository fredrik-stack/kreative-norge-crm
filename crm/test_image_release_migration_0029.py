import uuid

from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


class OrganizationImageReleaseSelectionGateMigrationTests(TransactionTestCase):
    migrate_from = ("crm", "0028_image_rendition_zoom")
    migrate_to = ("crm", "0029_release_selection_revision_gate")

    def tearDown(self):
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM crm_organizationimagereleaserendition")
            cursor.execute("DELETE FROM crm_organizationimagerelease")
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def _migrate_from_and_create_scope(self):
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        apps = executor.loader.project_state([self.migrate_from]).apps
        Tenant = apps.get_model("crm", "Tenant")
        Organization = apps.get_model("crm", "Organization")
        Asset = apps.get_model("crm", "ImageAsset")
        RenditionSet = apps.get_model("crm", "ImageRenditionSet")
        Selection = apps.get_model("crm", "OrganizationImageSelection")
        User = apps.get_model("auth", "User")

        tenant = Tenant.objects.create(name="Release gate", slug=f"release-gate-{uuid.uuid4()}")
        organization = Organization.objects.create(tenant=tenant, name="Release gate org")
        user = User.objects.create(username=f"release-gate-{uuid.uuid4()}")
        asset = Asset.objects.create(
            tenant=tenant,
            private_storage_key=f"tenants/{tenant.pk}/originals/gate.jpg",
            checksum_sha256="a" * 64,
            original_format="jpeg",
            mime_type="image/jpeg",
            width=1600,
            height=900,
            file_size_bytes=100,
            validation_version="test-v1",
        )
        rendition_set = RenditionSet.objects.create(
            tenant=tenant,
            asset=asset,
            fit_mode="cover",
            focus_x="0.5000",
            focus_y="0.5000",
            zoom="1.0000",
            processing_version="test-v1",
            render_config_hash_sha256="b" * 64,
        )
        selection = Selection.objects.create(
            tenant=tenant,
            organization=organization,
            selection_kind="asset",
            rendition_set=rendition_set,
            alt_text="",
            public_credit="",
            revision=3,
            status="active",
            locked_by=user,
            locked_at=timezone.now(),
        )
        return executor, apps, tenant, organization, rendition_set, selection

    @staticmethod
    def _insert_old_release(apps, tenant, organization, rendition_set, selection):
        Release = apps.get_model("crm", "OrganizationImageRelease")
        release = Release(
            release_id=uuid.uuid4(),
            tenant=tenant,
            organization=organization,
            selection=selection,
            rendition_set=rendition_set,
            key_schema_version=1,
        )
        return Release._base_manager._insert_from_release_service([release])[0]

    def test_empty_table_migrates_without_default_or_backfill(self):
        executor, _, _, _, _, _ = self._migrate_from_and_create_scope()

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        apps = executor.loader.project_state([self.migrate_to]).apps
        field = apps.get_model("crm", "OrganizationImageRelease")._meta.get_field(
            "selection_revision_snapshot"
        )

        self.assertFalse(field.null)
        self.assertFalse(field.has_default())
        self.assertEqual(
            apps.get_model("crm", "OrganizationImageRelease")._base_manager.count(),
            0,
        )

    def test_existing_release_aborts_without_synthetic_snapshot(self):
        _, apps, tenant, organization, rendition_set, selection = (
            self._migrate_from_and_create_scope()
        )
        release = self._insert_old_release(
            apps, tenant, organization, rendition_set, selection
        )

        executor = MigrationExecutor(connection)
        with self.assertRaisesRegex(RuntimeError, "must be empty"):
            executor.migrate([self.migrate_to])

        with connection.cursor() as cursor:
            columns = {
                item.name
                for item in connection.introspection.get_table_description(
                    cursor, "crm_organizationimagerelease"
                )
            }
            cursor.execute(
                "SELECT release_id FROM crm_organizationimagerelease WHERE id = %s",
                [release.pk],
            )
            stored_release_id = cursor.fetchone()[0]
        self.assertNotIn("selection_revision_snapshot", columns)
        self.assertEqual(stored_release_id, release.release_id)

    def test_database_constraints_reject_duplicate_selection_and_zero_snapshot(self):
        executor, _, tenant, organization, rendition_set, selection = (
            self._migrate_from_and_create_scope()
        )
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])

        statement = (
            "INSERT INTO crm_organizationimagerelease "
            "(release_id, tenant_id, organization_id, selection_id, "
            "rendition_set_id, selection_revision_snapshot, key_schema_version, created_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, 1, %s)"
        )
        values = [
            str(uuid.uuid4()),
            tenant.pk,
            organization.pk,
            selection.pk,
            rendition_set.pk,
            selection.revision,
            timezone.now(),
        ]
        with connection.cursor() as cursor:
            cursor.execute(statement, values)

        duplicate_values = [*values]
        duplicate_values[0] = str(uuid.uuid4())
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(statement, duplicate_values)

        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM crm_organizationimagerelease")
        zero_values = [*values]
        zero_values[0] = str(uuid.uuid4())
        zero_values[5] = 0
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(statement, zero_values)
