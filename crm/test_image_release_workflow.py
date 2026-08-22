from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import tempfile
import threading
import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.storage import storages
from django.db import close_old_connections
from django.test import TransactionTestCase, override_settings
from django.utils import timezone
from PIL import Image

from image_safety.release_keys import build_public_release_key

from .models import (
    ImageAsset,
    ImageRendition,
    ImageRenditionSet,
    Organization,
    OrganizationImageRelease,
    OrganizationImageReleaseRendition,
    OrganizationImageSelection,
    Tenant,
)
from .services.images.bridge_client import (
    BridgeActivation,
    BridgeReservation,
    ImageSafetyBridgeConflict,
    ImageSafetyBridgeUnavailable,
)
from .services.images.releases import (
    InvalidImageReleaseError,
    create_organization_image_release,
)


class WorkflowBridge:
    lock = threading.Lock()
    reservations = {}
    reserve_calls = 0
    activate_calls = 0
    active = set()
    lose_reserve_response = False
    lose_activation_response = False
    reserve_hook = None

    @classmethod
    def reset(cls):
        cls.reservations = {}
        cls.reserve_calls = 0
        cls.activate_calls = 0
        cls.active = set()
        cls.lose_reserve_response = False
        cls.lose_activation_response = False
        cls.reserve_hook = None

    def reserve(self, **payload):
        with self.lock:
            type(self).reserve_calls += 1
            identity = (
                payload["tenant_id"],
                payload["organization_id"],
                payload["selection_id"],
                payload["selection_revision"],
            )
            canonical_payload = repr(payload)
            stored = self.reservations.get(identity)
            if stored is None:
                release_id = str(uuid.uuid4())
                reservation = BridgeReservation(
                    event_id="release-reservation:v1:" + ":".join(map(str, identity)),
                    event_sequence=1,
                    release_id=release_id,
                    public_keys={
                        item.variant: build_public_release_key(
                            release_id, item.variant, item.output_format
                        )
                        for item in payload["renditions"]
                    },
                    disposition="new",
                    anchor_cursor=1,
                )
                self.reservations[identity] = (canonical_payload, reservation)
            elif stored[0] != canonical_payload:
                raise ImageSafetyBridgeConflict(
                    "reservation_conflict",
                    "Reservation payload changed.",
                    retryable=False,
                )
            else:
                reservation = BridgeReservation(
                    **{**stored[1].__dict__, "disposition": "idempotent_retry"}
                )
            hook = type(self).reserve_hook
            type(self).reserve_hook = None
            if hook is not None:
                hook()
            if type(self).lose_reserve_response:
                type(self).lose_reserve_response = False
                raise ImageSafetyBridgeUnavailable(
                    "safety_unavailable", "Response lost.", retryable=True
                )
            return reservation

    def activate(self, *, release_id):
        with self.lock:
            type(self).activate_calls += 1
            disposition = "idempotent_retry" if release_id in self.active else "new"
            self.active.add(release_id)
            if type(self).lose_activation_response:
                type(self).lose_activation_response = False
                raise ImageSafetyBridgeUnavailable(
                    "safety_unavailable", "Response lost.", retryable=True
                )
            return BridgeActivation(
                event_id=f"release-activation:v1:{release_id}",
                event_sequence=2,
                release_id=release_id,
                disposition=disposition,
                anchor_cursor=2,
            )


class OrganizationImageReleaseWorkflowTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        WorkflowBridge.reset()
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name).resolve()
        self.artifact_root = root / "artifacts"
        self.delivery_root = root / "delivery"
        self.artifact_root.mkdir()
        self.settings_override = override_settings(
            IMAGE_ASSET_FEATURE_ENABLED=True,
            PUBLIC_IMAGE_RELEASE_MATERIALIZATION_ENABLED=True,
            PUBLIC_IMAGE_DELIVERY_ROOT=self.delivery_root,
            STORAGES={
                "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
                "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
                "image_renditions_public": {
                    "BACKEND": "django.core.files.storage.FileSystemStorage",
                    "OPTIONS": {"location": self.artifact_root, "base_url": None},
                },
                "public_image_delivery": {
                    "BACKEND": "django.core.files.storage.FileSystemStorage",
                    "OPTIONS": {"location": self.delivery_root, "base_url": None},
                },
            },
        )
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.bridge_patch = patch(
            "crm.services.images.releases.ImageSafetyBridgeClient", WorkflowBridge
        )
        self.bridge_patch.start()
        self.addCleanup(self.bridge_patch.stop)

        user = get_user_model().objects.create_user(username="workflow-user")
        self.tenant = Tenant.objects.create(name="Workflow", slug="workflow")
        self.organization = Organization.objects.create(
            tenant=self.tenant, name="Workflow organization"
        )
        asset = ImageAsset.objects.create(
            tenant=self.tenant,
            private_storage_key="assets/workflow.jpg",
            checksum_sha256="a" * 64,
            original_format="jpeg",
            mime_type="image/jpeg",
            width=20,
            height=20,
            file_size_bytes=100,
            validation_version="test-v1",
        )
        rendition_set = ImageRenditionSet.objects.create(
            tenant=self.tenant,
            asset=asset,
            fit_mode="cover",
            processing_version="test-v1",
            render_config_hash_sha256="b" * 64,
        )
        for index, variant in enumerate(("square", "landscape", "share"), start=1):
            size = (index + 5, index + 6)
            buffer = BytesIO()
            Image.new("RGB", size, "green").save(buffer, "WEBP")
            data = buffer.getvalue()
            checksum = sha256(data).hexdigest()
            key = (
                f"tenants/{self.tenant.pk}/artifacts/{rendition_set.processing_version}/"
                f"{asset.checksum_sha256}/{rendition_set.render_config_hash_sha256}/"
                f"{variant}-{checksum}.webp"
            )
            storage = storages["image_renditions_public"]
            path = Path(storage.path(key))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            ImageRendition.objects.create(
                tenant=self.tenant,
                rendition_set=rendition_set,
                variant=variant,
                output_format="webp",
                width=size[0],
                height=size[1],
                file_size_bytes=len(data),
                checksum_sha256=checksum,
                artifact_storage_key=key,
            )
        self.selection = OrganizationImageSelection.objects.create(
            tenant=self.tenant,
            organization=self.organization,
            selection_kind="asset",
            rendition_set=rendition_set,
            alt_text="Workflow image",
            public_credit="",
            revision=1,
            status="active",
            locked_by=user,
            locked_at=timezone.now(),
        )

    def run_workflow(self):
        return create_organization_image_release(
            selection=OrganizationImageSelection.objects.get(pk=self.selection.pk)
        )

    def test_lost_reservation_response_retries_same_uuid_without_partial_db(self):
        WorkflowBridge.lose_reserve_response = True
        with self.assertRaises(ImageSafetyBridgeUnavailable):
            self.run_workflow()
        self.assertEqual(OrganizationImageRelease.objects.count(), 0)

        result = self.run_workflow()
        reserved = next(iter(WorkflowBridge.reservations.values()))[1]
        self.assertEqual(str(result.release.release_id), reserved.release_id)
        self.assertEqual(OrganizationImageRelease.objects.count(), 1)

    def test_db_binding_failure_and_pre_file_crash_are_retryable(self):
        with patch.object(
            OrganizationImageReleaseRendition.objects,
            "_insert_from_release_service",
            side_effect=RuntimeError("synthetic binding failure"),
        ):
            with self.assertRaises(RuntimeError):
                self.run_workflow()
        self.assertEqual(OrganizationImageRelease.objects.count(), 0)

        with patch(
            "crm.services.images.releases.materialize_release",
            side_effect=RuntimeError("crash before first file"),
        ):
            with self.assertRaises(RuntimeError):
                self.run_workflow()
        self.assertEqual(OrganizationImageRelease.objects.count(), 1)
        self.assertEqual(WorkflowBridge.activate_calls, 0)

        result = self.run_workflow()
        self.assertEqual(len(result.materializations), 3)

    def test_crash_after_one_or_two_files_recovers_without_clobber(self):
        from .services.images import materialization

        original = materialization._materialize_one
        for crash_after in (1, 2):
            with self.subTest(crash_after=crash_after):
                OrganizationImageReleaseRendition._base_objects.all()._raw_delete(
                    OrganizationImageReleaseRendition._base_objects.db
                )
                OrganizationImageRelease._base_objects.all()._raw_delete(
                    OrganizationImageRelease._base_objects.db
                )
                if self.delivery_root.exists():
                    for path in self.delivery_root.rglob("*.webp"):
                        path.unlink()
                WorkflowBridge.reset()
                count = 0

                def crash(item, data):
                    nonlocal count
                    result = original(item, data)
                    count += 1
                    if count == crash_after:
                        raise RuntimeError("synthetic materialization crash")
                    return result

                with patch.object(materialization, "_materialize_one", side_effect=crash):
                    with self.assertRaises(RuntimeError):
                        self.run_workflow()
                self.assertEqual(len(list(self.delivery_root.rglob("*.webp"))), crash_after)
                self.assertEqual(WorkflowBridge.activate_calls, 0)
                result = self.run_workflow()
                self.assertEqual(len(result.materializations), 3)
                self.assertEqual(len(list(self.delivery_root.rglob("*.webp"))), 3)

    def test_activation_unavailable_or_response_lost_retries_after_verified_files(self):
        WorkflowBridge.lose_activation_response = True
        with self.assertRaises(ImageSafetyBridgeUnavailable):
            self.run_workflow()
        self.assertEqual(len(list(self.delivery_root.rglob("*.webp"))), 3)
        self.assertEqual(OrganizationImageRelease.objects.count(), 1)

        result = self.run_workflow()
        self.assertEqual(result.activation.disposition, "idempotent_retry")
        self.assertEqual([item.created for item in result.materializations], [False] * 3)

    def test_conflicts_on_changed_snapshot_or_different_ledger_uuid(self):
        WorkflowBridge.lose_reserve_response = True
        with self.assertRaises(ImageSafetyBridgeUnavailable):
            self.run_workflow()
        square = ImageRendition.objects.get(
            rendition_set=self.selection.rendition_set, variant="square"
        )
        original_checksum = square.checksum_sha256
        original_key = square.artifact_storage_key
        changed_checksum = "f" * 64
        changed_key = original_key.replace(original_checksum, changed_checksum)
        ImageRendition.objects.filter(pk=square.pk).update(
            checksum_sha256=changed_checksum,
            artifact_storage_key=changed_key,
        )
        with self.assertRaises(ImageSafetyBridgeConflict):
            self.run_workflow()
        self.assertEqual(OrganizationImageRelease.objects.count(), 0)

        ImageRendition.objects.filter(pk=square.pk).update(
            checksum_sha256=original_checksum,
            artifact_storage_key=original_key,
        )
        WorkflowBridge.reset()
        first = self.run_workflow()
        identity = next(iter(WorkflowBridge.reservations))
        original_payload, reservation = WorkflowBridge.reservations[identity]
        other_id = str(uuid.uuid4())
        WorkflowBridge.reservations[identity] = (
            original_payload,
            BridgeReservation(
                **{
                    **reservation.__dict__,
                    "release_id": other_id,
                    "public_keys": {
                        item.variant: build_public_release_key(
                            other_id, item.variant, item.output_format
                        )
                        for item in self.selection.rendition_set.renditions.all()
                    },
                }
            ),
        )
        with self.assertRaises(InvalidImageReleaseError):
            self.run_workflow()
        self.assertEqual(OrganizationImageRelease.objects.get().pk, first.release.pk)

    def test_snapshot_change_between_reserve_and_bind_fails_without_db_release(self):
        WorkflowBridge.reserve_hook = lambda: ImageRendition.objects.filter(
            rendition_set=self.selection.rendition_set, variant="square"
        ).update(width=99)

        with self.assertRaisesRegex(InvalidImageReleaseError, "changed during"):
            self.run_workflow()

        self.assertEqual(OrganizationImageRelease.objects.count(), 0)

    def test_two_concurrent_workflows_bind_one_release_and_three_mappings(self):
        barrier = threading.Barrier(2)
        failures = []

        def run():
            close_old_connections()
            try:
                barrier.wait(timeout=5)
                return self.run_workflow()
            except BaseException as error:
                failures.append(error)
                return None
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: run(), range(2)))

        self.assertEqual(failures, [])
        self.assertEqual(OrganizationImageRelease.objects.count(), 1)
        self.assertEqual(OrganizationImageReleaseRendition.objects.count(), 3)
        self.assertEqual(
            {result.release.release_id for result in results},
            {results[0].release.release_id},
        )
