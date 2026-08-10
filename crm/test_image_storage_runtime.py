from __future__ import annotations

from io import StringIO
import os
from pathlib import Path
import tempfile
import time
from unittest.mock import patch

from django.core.management import call_command, CommandError
from django.test import TestCase, override_settings

from crm.models import ImageAsset, ImageRendition, ImageRenditionSet, Tenant
from crm.services.images.cleanup import (
    ImageOrphanCleanupError,
    cleanup_image_storage_orphans,
)


class ImageStorageRuntimeTests(TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        root = Path(self.temporary_directory.name).resolve()
        self.private_root = root / "private"
        self.rendition_root = root / "public"
        self.private_root.mkdir()
        self.rendition_root.mkdir()
        self.environment = patch.dict(
            os.environ,
            {
                "IMAGE_ORIGINALS_ROOT": str(self.private_root),
                "IMAGE_RENDITIONS_ROOT": str(self.rendition_root),
            },
        )
        self.environment.start()
        self.settings_override = override_settings(
            IMAGE_ASSET_FEATURE_ENABLED=True,
            IMAGE_ORIGINALS_ROOT=self.private_root,
            IMAGE_RENDITIONS_ROOT=self.rendition_root,
            STORAGES={
                "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
                "staticfiles": {
                    "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
                },
                "image_originals_private": {
                    "BACKEND": "django.core.files.storage.FileSystemStorage",
                    "OPTIONS": {"location": self.private_root, "base_url": None},
                },
                "image_renditions_public": {
                    "BACKEND": "django.core.files.storage.FileSystemStorage",
                    "OPTIONS": {"location": self.rendition_root, "base_url": None},
                },
            },
        )
        self.settings_override.enable()
        self.tenant = Tenant.objects.create(name="Runtime tenant", slug="runtime-tenant")

    def tearDown(self):
        self.settings_override.disable()
        self.environment.stop()
        self.temporary_directory.cleanup()

    @staticmethod
    def _write(root: Path, key: str, data: bytes = b"image bytes") -> Path:
        path = root.joinpath(*key.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def _create_referenced_files(self) -> tuple[Path, Path]:
        private_key = "tenants/1/originals/referenced.jpeg"
        artifact_key = "tenants/1/artifacts/profile/source/config/square-checksum.webp"
        asset = ImageAsset.objects.create(
            tenant=self.tenant,
            private_storage_key=private_key,
            checksum_sha256="a" * 64,
            original_format=ImageAsset.OriginalFormat.JPEG,
            mime_type="image/jpeg",
            width=1200,
            height=900,
            file_size_bytes=11,
            validation_version="test-v1",
        )
        rendition_set = ImageRenditionSet.objects.create(
            tenant=self.tenant,
            asset=asset,
            fit_mode=ImageRenditionSet.FitMode.COVER,
            processing_version="test-v1",
            render_config_hash_sha256="b" * 64,
        )
        ImageRendition.objects.create(
            tenant=self.tenant,
            rendition_set=rendition_set,
            variant=ImageRendition.Variant.SQUARE,
            output_format=ImageRendition.OutputFormat.WEBP,
            width=512,
            height=512,
            file_size_bytes=11,
            checksum_sha256="c" * 64,
            artifact_storage_key=artifact_key,
        )
        return (
            self._write(self.private_root, private_key),
            self._write(self.rendition_root, artifact_key),
        )

    def test_orphan_cleanup_is_dry_run_by_default_and_keeps_referenced_files(self):
        referenced = self._create_referenced_files()
        orphan = self._write(self.private_root, "tenants/1/originals/orphan.jpeg")
        old = time.time() - (2 * 60 * 60)
        os.utime(orphan, (old, old))

        result = cleanup_image_storage_orphans(minimum_age_hours=1)

        self.assertEqual(result.orphan_count, 1)
        self.assertEqual(result.deleted_keys, ())
        self.assertTrue(orphan.exists())
        self.assertTrue(all(path.exists() for path in referenced))

    def test_apply_deletes_only_old_unreferenced_regular_files(self):
        referenced = self._create_referenced_files()
        old_orphan = self._write(self.private_root, "tenants/1/originals/old.jpeg")
        young_orphan = self._write(self.rendition_root, "runtime-probes/young/rendition.png")
        old = time.time() - (2 * 60 * 60)
        os.utime(old_orphan, (old, old))

        result = cleanup_image_storage_orphans(apply=True, minimum_age_hours=1)

        self.assertEqual(result.deleted_keys, (("image_originals_private", "tenants/1/originals/old.jpeg"),))
        self.assertFalse(old_orphan.exists())
        self.assertTrue(young_orphan.exists())
        self.assertTrue(all(path.exists() for path in referenced))

    def test_missing_database_referenced_file_blocks_all_cleanup(self):
        self._create_referenced_files()
        orphan = self._write(self.private_root, "tenants/1/originals/orphan.jpeg")
        old = time.time() - (2 * 60 * 60)
        os.utime(orphan, (old, old))
        next(self.rendition_root.rglob("*.webp")).unlink()

        with self.assertRaisesRegex(ImageOrphanCleanupError, "database-referenced"):
            cleanup_image_storage_orphans(apply=True, minimum_age_hours=1)

        self.assertTrue(orphan.exists())

    def test_symlink_anywhere_in_storage_blocks_all_cleanup(self):
        orphan = self._write(self.private_root, "tenants/1/originals/orphan.jpeg")
        old = time.time() - (2 * 60 * 60)
        os.utime(orphan, (old, old))
        (self.rendition_root / "escape").symlink_to(self.private_root, target_is_directory=True)

        with self.assertRaisesRegex(ImageOrphanCleanupError, "contains a symlink"):
            cleanup_image_storage_orphans(apply=True, minimum_age_hours=1)

        self.assertTrue(orphan.exists())

    def test_symlink_component_in_configured_root_blocks_cleanup(self):
        linked_root = self.private_root.parent / "linked-private"
        linked_root.symlink_to(self.private_root, target_is_directory=True)

        with patch.dict(os.environ, {"IMAGE_ORIGINALS_ROOT": str(linked_root)}):
            with self.assertRaisesRegex(ImageOrphanCleanupError, "symlink components"):
                cleanup_image_storage_orphans(minimum_age_hours=1)

    def test_negative_minimum_age_is_rejected(self):
        with self.assertRaisesRegex(ImageOrphanCleanupError, "non-negative integer"):
            cleanup_image_storage_orphans(minimum_age_hours=-1)

    def test_persistence_probe_write_verify_and_explicit_cleanup(self):
        token = "a" * 32
        write_output = StringIO()
        call_command(
            "verify_image_storage_persistence",
            "--write",
            "--token",
            token,
            stdout=write_output,
        )
        self.assertIn("mode=write", write_output.getvalue())
        self.assertTrue((self.private_root / "runtime-probes" / token / "original.png").is_file())
        self.assertTrue((self.rendition_root / "runtime-probes" / token / "rendition.png").is_file())

        verify_output = StringIO()
        call_command(
            "verify_image_storage_persistence",
            "--verify",
            "--token",
            token,
            stdout=verify_output,
        )
        self.assertIn("checksum_sha256=", verify_output.getvalue())

        call_command(
            "verify_image_storage_persistence",
            "--cleanup",
            "--token",
            token,
            stdout=StringIO(),
        )
        self.assertFalse((self.private_root / "runtime-probes" / token / "original.png").exists())
        self.assertFalse((self.rendition_root / "runtime-probes" / token / "rendition.png").exists())

    @override_settings(IMAGE_ASSET_FEATURE_ENABLED=False)
    def test_persistence_probe_write_is_blocked_while_feature_is_off(self):
        with self.assertRaisesRegex(CommandError, "must be true"):
            call_command(
                "verify_image_storage_persistence",
                "--write",
                "--token",
                "b" * 32,
                stdout=StringIO(),
            )
