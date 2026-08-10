from __future__ import annotations

from io import BytesIO
from io import StringIO
import os
from pathlib import Path
import tempfile
import threading
import time
from unittest.mock import patch

from django.core.management import call_command, CommandError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import close_old_connections, connection
from django.test import TestCase, TransactionTestCase, override_settings
from PIL import Image

from crm.models import ImageAsset, ImageRendition, ImageRenditionSet, Tenant
from crm.services.images import cleanup as cleanup_service
from crm.services.images.cleanup import (
    ImageOrphanCleanupError,
    cleanup_image_storage_orphans,
)
from crm.services.images.ingest import ingest_uploaded_image


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

    def test_directory_swap_to_symlink_before_delete_cannot_escape_alias_root(self):
        candidate = self._write(
            self.private_root,
            "tenants/1/originals/orphan.jpeg",
            b"planned orphan",
        )
        old = time.time() - (2 * 60 * 60)
        os.utime(candidate, (old, old))

        outside_root = self.private_root.parent / "outside"
        outside_victim = self._write(
            outside_root,
            "tenants/1/originals/orphan.jpeg",
            b"must survive",
        )
        original_open = cleanup_service._open_child_directory
        swapped = False

        def swap_before_component_open(parent_fd: int, component: str) -> int:
            nonlocal swapped
            if component == "tenants" and not swapped:
                swapped = True
                (self.private_root / "tenants").rename(
                    self.private_root / "tenants-before-swap"
                )
                (self.private_root / "tenants").symlink_to(
                    outside_root / "tenants",
                    target_is_directory=True,
                )
            return original_open(parent_fd, component)

        with patch.object(
            cleanup_service,
            "_open_child_directory",
            side_effect=swap_before_component_open,
        ):
            with self.assertRaisesRegex(
                ImageOrphanCleanupError,
                "secure no-follow deletion",
            ):
                cleanup_image_storage_orphans(apply=True, minimum_age_hours=1)

        self.assertTrue(swapped)
        self.assertEqual(outside_victim.read_bytes(), b"must survive")
        self.assertEqual(
            (
                self.private_root
                / "tenants-before-swap"
                / "1"
                / "originals"
                / "orphan.jpeg"
            ).read_bytes(),
            b"planned orphan",
        )

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


class ImageStorageConcurrencyTests(TransactionTestCase):
    reset_sequences = True

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
        self.tenant = Tenant.objects.create(
            name="Concurrent runtime tenant",
            slug="concurrent-runtime-tenant",
        )

    def tearDown(self):
        self.settings_override.disable()
        self.environment.stop()
        self.temporary_directory.cleanup()

    @staticmethod
    def _upload() -> SimpleUploadedFile:
        image = Image.new("RGB", (1400, 1000), (20, 70, 220))
        buffer = BytesIO()
        image.save(buffer, "JPEG")
        return SimpleUploadedFile(
            "concurrent.jpg",
            buffer.getvalue(),
            content_type="image/jpeg",
        )

    def test_cleanup_apply_waits_for_ingest_storage_to_database_commit(self):
        storage_written = threading.Event()
        allow_database_aggregate = threading.Event()
        cleanup_lock_attempted = threading.Event()
        cleanup_lock_acquired = threading.Event()
        cleanup_pid: list[int] = []
        outcomes: dict[str, object] = {}
        failures: list[BaseException] = []

        from crm.services.images import ingest as ingest_service

        original_aggregate = ingest_service._create_or_reuse_database_aggregate
        original_cleanup_lock = cleanup_service.acquire_image_storage_cleanup_lock

        def paused_aggregate(*args, **kwargs):
            storage_written.set()
            if not allow_database_aggregate.wait(timeout=10):
                raise AssertionError("Test did not release the ingest database aggregate.")
            return original_aggregate(*args, **kwargs)

        def observed_cleanup_lock() -> None:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_backend_pid()")
                cleanup_pid.append(cursor.fetchone()[0])
            cleanup_lock_attempted.set()
            original_cleanup_lock()
            cleanup_lock_acquired.set()

        def run_ingest() -> None:
            close_old_connections()
            try:
                outcomes["ingest"] = ingest_uploaded_image(
                    tenant=Tenant.objects.get(pk=self.tenant.pk),
                    upload=self._upload(),
                    content_mode="cover",
                )
            except BaseException as error:
                failures.append(error)
            finally:
                close_old_connections()

        def run_cleanup() -> None:
            close_old_connections()
            try:
                outcomes["cleanup"] = cleanup_image_storage_orphans(
                    apply=True,
                    minimum_age_hours=0,
                )
            except BaseException as error:
                failures.append(error)
            finally:
                close_old_connections()

        with patch.object(
            ingest_service,
            "_create_or_reuse_database_aggregate",
            side_effect=paused_aggregate,
        ), patch.object(
            cleanup_service,
            "acquire_image_storage_cleanup_lock",
            side_effect=observed_cleanup_lock,
        ):
            ingest_thread = threading.Thread(target=run_ingest)
            ingest_thread.start()
            self.assertTrue(storage_written.wait(timeout=10))

            cleanup_thread = threading.Thread(target=run_cleanup)
            cleanup_thread.start()
            self.assertTrue(cleanup_lock_attempted.wait(timeout=10))

            deadline = time.monotonic() + 10
            observed_database_wait = False
            while time.monotonic() < deadline:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT wait_event_type, wait_event "
                        "FROM pg_stat_activity WHERE pid = %s",
                        [cleanup_pid[0]],
                    )
                    wait_state = cursor.fetchone()
                if wait_state == ("Lock", "advisory"):
                    observed_database_wait = True
                    break
                cleanup_lock_attempted.wait(timeout=0.01)

            self.assertTrue(observed_database_wait)
            self.assertFalse(cleanup_lock_acquired.is_set())
            allow_database_aggregate.set()

            ingest_thread.join(timeout=10)
            cleanup_thread.join(timeout=10)

        self.assertFalse(ingest_thread.is_alive())
        self.assertFalse(cleanup_thread.is_alive())
        self.assertEqual(failures, [])
        self.assertTrue(cleanup_lock_acquired.is_set())
        self.assertEqual(outcomes["cleanup"].deleted_keys, ())

        asset = ImageAsset.objects.get()
        self.assertTrue(
            self.private_root.joinpath(*asset.private_storage_key.split("/")).is_file()
        )
        renditions = list(ImageRendition.objects.order_by("variant"))
        self.assertEqual(len(renditions), 3)
        for rendition in renditions:
            self.assertTrue(
                self.rendition_root.joinpath(
                    *rendition.artifact_storage_key.split("/")
                ).is_file()
            )
