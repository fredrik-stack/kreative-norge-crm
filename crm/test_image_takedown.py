from pathlib import Path
import os
import tempfile
import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from drf_spectacular.generators import SchemaGenerator

from image_safety.release_keys import PUBLIC_RELEASE_EXTENSIONS, build_public_release_key

from .models import (
    ImageAsset,
    ImageRendition,
    ImageRenditionSet,
    ImageReviewEvent,
    Organization,
    OrganizationImageRelease,
    OrganizationImageReleaseRendition,
    OrganizationImageSelection,
    Tenant,
    TenantMembership,
)
from .services.images.bridge_client import (
    BridgeDeny,
    BridgeChecksumCheck,
    BridgeLegacyGuard,
    ImageSafetyBridgeUnavailable,
)
from .services.images.takedown import (
    ImageTakedownConflict,
    ImageTakedownPermissionDenied,
    ImageTakedownUnavailable,
    formal_takedown_organization_image,
)
from .services.images.releases import (
    ImageReleaseChecksumDenied,
    create_organization_image_release,
)
from .services.images.selections import (
    AssetApprovalEvidence,
    ImageSelectionChecksumDenied,
    lock_organization_image_selection,
    restore_archived_organization_image_selection,
)


class TakedownBridge:
    calls = []
    denied = set()

    @classmethod
    def reset(cls):
        cls.calls = []
        cls.denied = set()

    def __init__(self, *args, **kwargs):
        pass

    def deny(self, **payload):
        type(self).calls.append(payload)
        identity = (
            payload["release_id"],
            payload["tenant_id"],
            payload["source_checksum_sha256"],
            payload["reason_code"],
        )
        retry = identity in type(self).denied
        type(self).denied.add(identity)
        return BridgeDeny(
            release_event_id=f"release-denial:v1:{payload['release_id']}",
            release_event_sequence=3,
            checksum_event_id=(
                "tenant-checksum-denial:v1:"
                f"{payload['tenant_id']}:{payload['source_checksum_sha256']}"
            ),
            checksum_event_sequence=4,
            release_disposition="idempotent_retry" if retry else "new",
            checksum_disposition="idempotent_retry" if retry else "new",
            anchor_cursor=4,
        )


@override_settings(
    IMAGE_ASSET_FEATURE_ENABLED=True,
    PUBLIC_IMAGE_RELEASE_MATERIALIZATION_ENABLED=True,
    PUBLIC_IMAGE_TAKEDOWN_ENABLED=True,
)
class FormalImageTakedownTests(TestCase):
    def setUp(self):
        TakedownBridge.reset()
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.delivery_root = Path(self.temporary.name).resolve() / "delivery"
        self.delivery_root.mkdir()
        self.settings_override = override_settings(
            PUBLIC_IMAGE_DELIVERY_ROOT=self.delivery_root
        )
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.bridge_patch = patch(
            "crm.services.images.takedown.ImageSafetyBridgeClient", TakedownBridge
        )
        self.bridge_patch.start()
        self.addCleanup(self.bridge_patch.stop)

        self.tenant = Tenant.objects.create(name="Takedown", slug="takedown")
        self.other_tenant = Tenant.objects.create(name="Other", slug="other-takedown")
        self.admin = get_user_model().objects.create_user(username="tenant-admin")
        self.editor = get_user_model().objects.create_user(username="tenant-editor")
        self.reader = get_user_model().objects.create_user(username="tenant-reader")
        self.platform_admin = get_user_model().objects.create_superuser(
            username="platform-admin", email="platform@example.no", password="test"
        )
        TenantMembership.objects.create(
            tenant=self.tenant,
            user=self.admin,
            role=TenantMembership.Role.GRUPPEADMIN,
        )
        TenantMembership.objects.create(
            tenant=self.tenant,
            user=self.editor,
            role=TenantMembership.Role.REDIGERER,
        )
        TenantMembership.objects.create(
            tenant=self.tenant,
            user=self.reader,
            role=TenantMembership.Role.LESER,
        )
        self.organization = Organization.objects.create(
            tenant=self.tenant,
            name="Synthetic takedown actor",
            is_published=True,
            thumbnail_image_url="https://legacy.example.no/old.jpg",
            auto_thumbnail_url="https://legacy.example.no/auto.jpg",
            og_image_url="https://legacy.example.no/og.jpg",
        )
        self.asset = ImageAsset.objects.create(
            tenant=self.tenant,
            private_storage_key="tenants/1/originals/source.jpeg",
            checksum_sha256="a" * 64,
            original_format=ImageAsset.OriginalFormat.JPEG,
            mime_type="image/jpeg",
            width=1600,
            height=900,
            file_size_bytes=100,
            validation_version="validation-v1",
        )
        self.rendition_set = ImageRenditionSet.objects.create(
            tenant=self.tenant,
            asset=self.asset,
            fit_mode=ImageRenditionSet.FitMode.COVER,
            processing_version="processing-v1",
            render_config_hash_sha256="b" * 64,
        )
        specifications = (
            (ImageRendition.Variant.SQUARE, ImageRendition.OutputFormat.WEBP, 512, 512, "c"),
            (ImageRendition.Variant.LANDSCAPE, ImageRendition.OutputFormat.PNG, 800, 450, "d"),
            (ImageRendition.Variant.SHARE, ImageRendition.OutputFormat.JPEG, 1200, 630, "e"),
        )
        self.renditions = []
        for variant, output_format, width, height, checksum_character in specifications:
            checksum = checksum_character * 64
            extension = PUBLIC_RELEASE_EXTENSIONS[output_format]
            self.renditions.append(
                ImageRendition.objects.create(
                    tenant=self.tenant,
                    rendition_set=self.rendition_set,
                    variant=variant,
                    output_format=output_format,
                    width=width,
                    height=height,
                    file_size_bytes=5,
                    checksum_sha256=checksum,
                    artifact_storage_key=(
                        f"tenants/{self.tenant.pk}/artifacts/processing-v1/"
                        f"{'a' * 64}/{'b' * 64}/{variant}-{checksum}.{extension}"
                    ),
                )
            )
        self.selection = OrganizationImageSelection.objects.create(
            tenant=self.tenant,
            organization=self.organization,
            selection_kind=OrganizationImageSelection.SelectionKind.ASSET,
            rendition_set=self.rendition_set,
            alt_text="Synthetic asset",
            public_credit="Synthetic credit",
            revision=1,
            status=OrganizationImageSelection.Status.ACTIVE,
            locked_by=self.admin,
            locked_at=timezone.now(),
        )
        release = OrganizationImageRelease(
            release_id=uuid.uuid4(),
            tenant=self.tenant,
            organization=self.organization,
            selection=self.selection,
            selection_revision_snapshot=1,
            rendition_set=self.rendition_set,
            key_schema_version=1,
        )
        self.release = OrganizationImageRelease.objects._insert_from_release_service(
            [release]
        )[0]
        mappings = []
        for rendition in self.renditions:
            mappings.append(
                OrganizationImageReleaseRendition(
                    release=self.release,
                    rendition=rendition,
                    variant=rendition.variant,
                    output_format=rendition.output_format,
                    artifact_storage_key_snapshot=rendition.artifact_storage_key,
                    artifact_checksum_sha256_snapshot=rendition.checksum_sha256,
                    public_storage_key=build_public_release_key(
                        self.release.release_id,
                        rendition.variant,
                        rendition.output_format,
                    ),
                )
            )
        self.mappings = tuple(
            OrganizationImageReleaseRendition.objects._insert_from_release_service(
                mappings
            )
        )
        release_directory = (
            self.delivery_root / "releases" / str(self.release.release_id)
        )
        release_directory.mkdir(parents=True)
        for mapping in self.mappings:
            (self.delivery_root / mapping.public_storage_key).write_bytes(b"bytes")

    def test_admin_deny_first_creates_formal_audit_fallback_and_deletes_exact_origin(self):
        with self.assertLogs("crm.images.takedown", level="INFO") as logs:
            result = formal_takedown_organization_image(
                actor=self.admin,
                tenant_id=self.tenant.pk,
                organization_id=self.organization.pk,
                reason_code=ImageReviewEvent.TakedownReason.RIGHTS_REQUEST,
            )

        self.assertEqual(len(TakedownBridge.calls), 1)
        self.assertEqual(
            set(TakedownBridge.calls[0]),
            {
                "release_id", "tenant_id", "organization_id",
                "source_checksum_sha256", "reason_code",
            },
        )
        self.assertEqual(result.origin_files_deleted, 3)
        self.assertEqual(result.origin_files_already_missing, 0)
        active = OrganizationImageSelection.objects.get(
            organization=self.organization,
            status=OrganizationImageSelection.Status.ACTIVE,
        )
        self.assertEqual(active.selection_kind, "system_fallback")
        self.selection.refresh_from_db()
        self.assertEqual(self.selection.status, "archived")
        event = ImageReviewEvent.objects.get(pk=result.review_event_id)
        self.assertEqual(event.event_type, "formal_takedown")
        self.assertEqual(event.previous_selection_id, self.selection.pk)
        self.assertEqual(event.asset_checksum_sha256_snapshot, "a" * 64)
        self.assertEqual(event.release_id_snapshot, self.release.release_id)
        self.assertEqual(event.takedown_reason_code, "rights_request")
        self.assertEqual(OrganizationImageRelease.objects.count(), 1)
        self.assertEqual(OrganizationImageReleaseRendition.objects.count(), 3)
        self.assertTrue(ImageAsset.objects.filter(pk=self.asset.pk).exists())
        self.assertTrue(ImageRendition.objects.filter(rendition_set=self.rendition_set).count(), 3)
        self.assertIn("reason_code=rights_request", logs.output[0])
        self.assertIn("verification=origin_absent", logs.output[0])
        self.assertIn("correlation_id=", logs.output[0])
        self.assertNotIn(self.asset.checksum_sha256, logs.output[0])
        self.assertNotIn(self.asset.private_storage_key, logs.output[0])
        for mapping in self.mappings:
            self.assertFalse((self.delivery_root / mapping.public_storage_key).exists())

    def test_retry_reuses_formal_identity_event_and_accepts_missing_files(self):
        first = formal_takedown_organization_image(
            actor=self.admin,
            tenant_id=self.tenant.pk,
            organization_id=self.organization.pk,
            reason_code="rights_request",
        )
        second = formal_takedown_organization_image(
            actor=self.admin,
            tenant_id=self.tenant.pk,
            organization_id=self.organization.pk,
            reason_code="rights_request",
        )

        self.assertTrue(second.idempotent_retry)
        self.assertEqual(second.review_event_id, first.review_event_id)
        self.assertEqual(second.selection_id, first.selection_id)
        self.assertEqual(second.origin_files_deleted, 0)
        self.assertEqual(second.origin_files_already_missing, 3)
        self.assertEqual(
            ImageReviewEvent.objects.filter(event_type="formal_takedown").count(), 1
        )
        self.assertEqual(OrganizationImageSelection.objects.count(), 2)
        self.assertEqual(len(TakedownBridge.calls), 2)

    def test_database_failure_after_anchored_deny_retries_same_safety_identity(self):
        with patch(
            "crm.services.images.takedown._create_selection_revision",
            side_effect=RuntimeError("synthetic database failure"),
        ):
            with self.assertRaises(RuntimeError):
                formal_takedown_organization_image(
                    actor=self.admin,
                    tenant_id=self.tenant.pk,
                    organization_id=self.organization.pk,
                    reason_code="rights_request",
                )
        self.selection.refresh_from_db()
        self.assertEqual(self.selection.status, "active")
        self.assertEqual(ImageReviewEvent.objects.filter(event_type="formal_takedown").count(), 0)

        recovered = formal_takedown_organization_image(
            actor=self.admin,
            tenant_id=self.tenant.pk,
            organization_id=self.organization.pk,
            reason_code="rights_request",
        )
        self.assertEqual(recovered.release_disposition, "idempotent_retry")
        self.assertEqual(recovered.checksum_disposition, "idempotent_retry")
        self.assertEqual(len(TakedownBridge.calls), 2)

    def test_safety_failure_before_confirmation_preserves_database_and_origin(self):
        class UnavailableDenyBridge:
            def deny(self, **payload):
                raise ImageSafetyBridgeUnavailable(
                    "safety_unavailable", "synthetic anchor failure", retryable=True
                )

        with self.assertRaises(ImageTakedownUnavailable):
            formal_takedown_organization_image(
                actor=self.admin,
                tenant_id=self.tenant.pk,
                organization_id=self.organization.pk,
                reason_code="rights_request",
                bridge=UnavailableDenyBridge(),
            )

        self.selection.refresh_from_db()
        self.assertEqual(self.selection.status, "active")
        self.assertFalse(
            ImageReviewEvent.objects.filter(event_type="formal_takedown").exists()
        )
        self.assertTrue(
            all(
                (self.delivery_root / mapping.public_storage_key).is_file()
                for mapping in self.mappings
            )
        )

    def test_partial_delete_after_one_file_is_completed_by_same_retry(self):
        original_unlink = os.unlink
        attempts = 0

        def interrupt_second(filename, *, dir_fd=None):
            nonlocal attempts
            attempts += 1
            if attempts == 2:
                raise OSError("synthetic interruption after one file")
            return original_unlink(filename, dir_fd=dir_fd)

        with patch(
            "crm.services.images.materialization.os.unlink",
            side_effect=interrupt_second,
        ):
            with self.assertRaises(ImageTakedownUnavailable):
                formal_takedown_organization_image(
                    actor=self.admin,
                    tenant_id=self.tenant.pk,
                    organization_id=self.organization.pk,
                    reason_code="editorial_policy",
                )
        self.assertEqual(
            sum(
                not (self.delivery_root / mapping.public_storage_key).exists()
                for mapping in self.mappings
            ),
            1,
        )

        recovered = formal_takedown_organization_image(
            actor=self.admin,
            tenant_id=self.tenant.pk,
            organization_id=self.organization.pk,
            reason_code="editorial_policy",
        )
        self.assertTrue(recovered.idempotent_retry)
        self.assertEqual(recovered.origin_files_deleted, 2)
        self.assertEqual(recovered.origin_files_already_missing, 1)

    def test_partial_delete_after_two_files_is_completed_by_same_retry(self):
        original_unlink = os.unlink
        attempts = 0

        def interrupt_third(filename, *, dir_fd=None):
            nonlocal attempts
            attempts += 1
            if attempts == 3:
                raise OSError("synthetic interruption after two files")
            return original_unlink(filename, dir_fd=dir_fd)

        with patch(
            "crm.services.images.materialization.os.unlink",
            side_effect=interrupt_third,
        ):
            with self.assertRaises(ImageTakedownUnavailable):
                formal_takedown_organization_image(
                    actor=self.admin,
                    tenant_id=self.tenant.pk,
                    organization_id=self.organization.pk,
                    reason_code="editorial_policy",
                )
        self.assertEqual(
            sum(
                not (self.delivery_root / mapping.public_storage_key).exists()
                for mapping in self.mappings
            ),
            2,
        )

        recovered = formal_takedown_organization_image(
            actor=self.admin,
            tenant_id=self.tenant.pk,
            organization_id=self.organization.pk,
            reason_code="editorial_policy",
        )
        self.assertTrue(recovered.idempotent_retry)
        self.assertEqual(recovered.origin_files_deleted, 1)
        self.assertEqual(recovered.origin_files_already_missing, 2)

    def test_release_must_match_exact_selection_revision_before_deny(self):
        OrganizationImageSelection.objects.filter(pk=self.selection.pk).update(revision=2)

        with self.assertRaisesRegex(
            ImageTakedownConflict, "Release scope is inconsistent"
        ):
            formal_takedown_organization_image(
                actor=self.admin,
                tenant_id=self.tenant.pk,
                organization_id=self.organization.pk,
                reason_code="rights_request",
            )
        self.assertEqual(TakedownBridge.calls, [])

    def test_no_follow_delete_rejects_symlink_then_retry_completes(self):
        first_mapping = sorted(self.mappings, key=lambda item: item.variant)[0]
        target_path = self.delivery_root / first_mapping.public_storage_key
        target_path.unlink()
        sentinel = Path(self.temporary.name) / "private-sentinel"
        sentinel.write_bytes(b"private")
        target_path.symlink_to(sentinel)

        with self.assertRaises(ImageTakedownUnavailable):
            formal_takedown_organization_image(
                actor=self.admin,
                tenant_id=self.tenant.pk,
                organization_id=self.organization.pk,
                reason_code="privacy_safety",
            )

        self.assertEqual(sentinel.read_bytes(), b"private")
        self.assertTrue(target_path.is_symlink())
        target_path.unlink()
        target_path.write_bytes(b"bytes")
        recovered = formal_takedown_organization_image(
            actor=self.admin,
            tenant_id=self.tenant.pk,
            organization_id=self.organization.pk,
            reason_code="privacy_safety",
        )
        self.assertTrue(recovered.idempotent_retry)
        self.assertEqual(recovered.origin_files_deleted, 3)
        self.assertEqual(sentinel.read_bytes(), b"private")

    def test_editor_reader_wrong_tenant_and_global_group_fallback_are_denied(self):
        global_group_user = get_user_model().objects.create_user(username="global-group")
        from django.contrib.auth.models import Group

        group, _ = Group.objects.get_or_create(name="superadmin")
        global_group_user.groups.add(group)
        for actor, tenant_id in (
            (self.editor, self.tenant.pk),
            (self.reader, self.tenant.pk),
            (self.admin, self.other_tenant.pk),
            (global_group_user, self.tenant.pk),
        ):
            with self.subTest(actor=actor.username, tenant_id=tenant_id):
                with self.assertRaises(ImageTakedownPermissionDenied):
                    formal_takedown_organization_image(
                        actor=actor,
                        tenant_id=tenant_id,
                        organization_id=self.organization.pk,
                        reason_code="rights_request",
                    )
        self.assertEqual(TakedownBridge.calls, [])

    def test_platform_superadmin_and_api_use_only_reason_as_caller_target(self):
        result = formal_takedown_organization_image(
            actor=self.platform_admin,
            tenant_id=self.tenant.pk,
            organization_id=self.organization.pk,
            reason_code="legal_compliance",
        )
        self.assertEqual(result.selection_revision, 2)

        # A fresh fixture is not needed to prove the route contract: retry is supported.
        self.client.force_login(self.platform_admin)
        rejected = self.client.post(
            reverse(
                "tenant-organizations-formal-image-takedown",
                kwargs={"tenant_id": self.tenant.pk, "pk": self.organization.pk},
            ),
            {"reason_code": "legal_compliance", "release_id": str(uuid.uuid4())},
            content_type="application/json",
        )
        self.assertEqual(rejected.status_code, 400)
        response = self.client.post(
            reverse(
                "tenant-organizations-formal-image-takedown",
                kwargs={"tenant_id": self.tenant.pk, "pk": self.organization.pk},
            ),
            {"reason_code": "legal_compliance"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("release_id", response.json())
        self.assertNotIn("source_checksum_sha256", response.json())

    def test_openapi_exposes_only_allowlisted_reason_request(self):
        schema = SchemaGenerator().get_schema(request=None, public=True)
        operation = schema["paths"][
            "/api/tenants/{tenant_id}/organizations/{id}/images/takedown/"
        ]["post"]
        request_schema = operation["requestBody"]["content"][
            "application/json"
        ]["schema"]
        component_name = request_schema["$ref"].rsplit("/", 1)[-1]
        component = schema["components"]["schemas"][component_name]
        self.assertEqual(set(component["properties"]), {"reason_code"})
        self.assertEqual(component["required"], ["reason_code"])
        reason_schema = component["properties"]["reason_code"]
        if "$ref" in reason_schema:
            reason_schema = schema["components"]["schemas"][
                reason_schema["$ref"].rsplit("/", 1)[-1]
            ]
        self.assertEqual(
            set(reason_schema["enum"]),
            {"rights_request", "privacy_safety", "legal_compliance", "editorial_policy"},
        )

    @override_settings(PUBLIC_IMAGE_TAKEDOWN_ENABLED=False)
    def test_write_gate_off_prevents_new_deny_without_changing_state(self):
        response = self.client.post(
            reverse(
                "tenant-organizations-formal-image-takedown",
                kwargs={"tenant_id": self.tenant.pk, "pk": self.organization.pk},
            ),
            {"reason_code": "rights_request"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse(
                "tenant-organizations-formal-image-takedown",
                kwargs={"tenant_id": self.tenant.pk, "pk": self.organization.pk},
            ),
            {"reason_code": "rights_request"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(TakedownBridge.calls, [])
        self.assertEqual(
            OrganizationImageSelection.objects.get(pk=self.selection.pk).status,
            "active",
        )

    @override_settings(
        PUBLIC_IMAGE_TAKEDOWN_ENABLED=False,
        PUBLIC_IMAGE_API_SCHEMA_ENABLED=False,
        PUBLIC_IMAGE_PUBLIC_CUTOVER_ENABLED=False,
    )
    def test_ledger_guard_alone_blocks_all_legacy_paths_and_fails_closed(self):
        class BlockedBridge:
            def __init__(self, *args, **kwargs):
                pass

            def legacy_guard(self, **payload):
                return BridgeLegacyGuard(blocked=True, read_cursor=9)

        with patch(
            "crm.services.images.safety_guards.ImageSafetyBridgeClient",
            BlockedBridge,
        ):
            self.assertIsNone(self.organization.get_public_image_url())
            self.assertIsNone(self.organization.get_preview_image_url())

        class UnavailableBridge:
            def __init__(self, *args, **kwargs):
                pass

            def legacy_guard(self, **payload):
                raise ImageSafetyBridgeUnavailable(
                    "safety_unavailable", "synthetic", retryable=True
                )

        with patch(
            "crm.services.images.safety_guards.ImageSafetyBridgeClient",
            UnavailableBridge,
        ):
            self.assertIsNone(self.organization.get_public_image_url())
            self.assertIsNone(self.organization.get_preview_image_url())

    def test_denied_checksum_blocks_approval_restore_and_release_creation(self):
        class DeniedChecksumBridge:
            def __init__(self, *args, **kwargs):
                pass

            def check_checksum(self, **payload):
                return BridgeChecksumCheck(denied=True, read_cursor=11)

            def reserve(self, **payload):  # pragma: no cover - must never run
                raise AssertionError("reserve must not run for denied source bytes")

        with patch(
            "crm.services.images.safety_guards.ImageSafetyBridgeClient",
            DeniedChecksumBridge,
        ):
            with self.assertRaises(ImageSelectionChecksumDenied):
                lock_organization_image_selection(
                    actor=self.editor,
                    tenant_id=self.tenant.pk,
                    organization_id=self.organization.pk,
                    expected_revision=1,
                    selection_kind=OrganizationImageSelection.SelectionKind.ASSET,
                    rendition_set_id=self.rendition_set.pk,
                    alt_text="Denied bytes",
                    asset_evidence=AssetApprovalEvidence(
                        source_type=ImageReviewEvent.SourceType.UPLOAD
                    ),
                )

        self.selection.status = OrganizationImageSelection.Status.ARCHIVED
        self.selection.save(update_fields=["status"])
        fallback = OrganizationImageSelection.objects.create(
            tenant=self.tenant,
            organization=self.organization,
            selection_kind=OrganizationImageSelection.SelectionKind.SYSTEM_FALLBACK,
            rendition_set=None,
            alt_text="Standardbilde",
            public_credit="",
            revision=2,
            status=OrganizationImageSelection.Status.ACTIVE,
            locked_by=self.admin,
            locked_at=timezone.now(),
        )
        with patch(
            "crm.services.images.safety_guards.ImageSafetyBridgeClient",
            DeniedChecksumBridge,
        ):
            with self.assertRaises(ImageSelectionChecksumDenied):
                restore_archived_organization_image_selection(
                    actor=self.editor,
                    tenant_id=self.tenant.pk,
                    organization_id=self.organization.pk,
                    expected_revision=fallback.revision,
                    source_selection_id=self.selection.pk,
                )

        with patch(
            "crm.services.images.releases.ImageSafetyBridgeClient",
            DeniedChecksumBridge,
        ):
            with self.assertRaises(ImageReleaseChecksumDenied):
                create_organization_image_release(selection=self.selection)

        self.assertEqual(
            OrganizationImageSelection.objects.filter(
                organization=self.organization,
                status=OrganizationImageSelection.Status.ACTIVE,
            ).get().pk,
            fallback.pk,
        )
