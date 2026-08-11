from decimal import Decimal

from django.db import connection
from django.db.migrations.exceptions import IrreversibleError
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class ImageRenditionZoomMigrationTests(TransactionTestCase):
    migrate_from = ("crm", "0027_optional_image_alt_text")
    migrate_to = ("crm", "0028_image_rendition_zoom")

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def _legacy_rendition_set(self):
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        apps = executor.loader.project_state([self.migrate_from]).apps
        Tenant = apps.get_model("crm", "Tenant")
        ImageAsset = apps.get_model("crm", "ImageAsset")
        ImageRenditionSet = apps.get_model("crm", "ImageRenditionSet")
        tenant = Tenant.objects.create(name="Zoom migration", slug="zoom-migration")
        asset = ImageAsset.objects.create(
            tenant=tenant,
            private_storage_key="assets/zoom-migration.jpeg",
            checksum_sha256="a" * 64,
            original_format="jpeg",
            mime_type="image/jpeg",
            width=1600,
            height=900,
            file_size_bytes=1234,
            validation_version="validation-v1",
        )
        return ImageRenditionSet.objects.create(
            tenant=tenant,
            asset=asset,
            fit_mode="cover",
            processing_version="processing-v1",
            render_config_hash_sha256="b" * 64,
        )

    def test_existing_rows_get_semantic_default_and_default_only_state_reverses(self):
        legacy = self._legacy_rendition_set()
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        apps = executor.loader.project_state([self.migrate_to]).apps
        ImageRenditionSet = apps.get_model("crm", "ImageRenditionSet")
        self.assertEqual(ImageRenditionSet.objects.get(pk=legacy.pk).zoom, Decimal("1.0000"))

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        restored_apps = executor.loader.project_state([self.migrate_from]).apps
        RestoredSet = restored_apps.get_model("crm", "ImageRenditionSet")
        self.assertTrue(RestoredSet.objects.filter(pk=legacy.pk).exists())
        self.assertNotIn("zoom", {field.name for field in RestoredSet._meta.fields})

    def test_reverse_is_blocked_after_non_default_zoom_is_stored(self):
        legacy = self._legacy_rendition_set()
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        apps = executor.loader.project_state([self.migrate_to]).apps
        ImageRenditionSet = apps.get_model("crm", "ImageRenditionSet")
        ImageRenditionSet.objects.filter(pk=legacy.pk).update(zoom=Decimal("1.5000"))

        with self.assertRaises(IrreversibleError):
            MigrationExecutor(connection).migrate([self.migrate_from])

        current_executor = MigrationExecutor(connection)
        current_apps = current_executor.loader.project_state([self.migrate_to]).apps
        self.assertEqual(
            current_apps.get_model("crm", "ImageRenditionSet").objects.get(pk=legacy.pk).zoom,
            Decimal("1.5000"),
        )
