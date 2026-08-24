from __future__ import annotations

from io import BytesIO
import json
from types import SimpleNamespace
from unittest.mock import patch
import uuid

from django.contrib.auth import get_user_model
from django.core import signing
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image

from crm.models import (
    ImageAsset,
    ImageRendition,
    ImageRenditionSet,
    Organization,
    OrganizationImageRelease,
    OrganizationImageReleaseRendition,
    OrganizationImageSelection,
    Tenant,
    TenantMembership,
)
from crm.services.images.candidates import (
    ImageCandidateFlowError,
    get_legacy_image_candidates,
    process_image_candidate,
    render_candidate_preview,
)
from crm.services.images.legacy_inventory import audit_legacy_image_sources
from crm.services.images.fetch import SecureFetchResult
from image_safety.release_keys import build_public_release_key


def _jpeg_bytes() -> bytes:
    output = BytesIO()
    Image.new("RGB", (64, 48), (20, 100, 190)).save(output, "JPEG")
    return output.getvalue()


@override_settings(IMAGE_ASSET_FEATURE_ENABLED=True)
class Phase3FLegacyCandidateTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Legacy", slug="legacy")
        self.other_tenant = Tenant.objects.create(name="Other", slug="legacy-other")
        self.organization = Organization.objects.create(
            tenant=self.tenant,
            name="Legacy actor",
            thumbnail_image_url="https://cdn.example.no/manual.jpg",
            og_image_url="https://cdn.example.no/og.jpg",
            auto_thumbnail_url="https://cdn.example.no/manual.jpg",
        )
        self.other_organization = Organization.objects.create(
            tenant=self.other_tenant,
            name="Other actor",
        )
        self.actor = get_user_model().objects.create_user(username="legacy-editor")
        for tenant in (self.tenant, self.other_tenant):
            TenantMembership.objects.create(
                tenant=tenant,
                user=self.actor,
                role=TenantMembership.Role.REDIGERER,
            )

    @patch("crm.services.images.candidates.legacy_image_is_blocked", return_value=False)
    @patch("crm.services.images.candidates.fetch_external_resource")
    def test_listing_is_local_deduplicated_signed_and_non_mutating(self, fetch_mock, _guard):
        before = (
            ImageAsset.objects.count(),
            ImageRenditionSet.objects.count(),
            ImageRendition.objects.count(),
        )
        candidates = get_legacy_image_candidates(
            actor=self.actor,
            tenant_id=self.tenant.pk,
            organization_id=self.organization.pk,
        )
        self.assertEqual(len(candidates), 2)
        self.assertEqual(
            {item.source_key for item in candidates},
            {"thumbnail_image_url", "og_image_url"},
        )
        self.assertTrue(all(item.candidate_ref for item in candidates))
        self.assertEqual(
            before,
            (ImageAsset.objects.count(), ImageRenditionSet.objects.count(), ImageRendition.objects.count()),
        )
        fetch_mock.assert_not_called()

    @patch("crm.services.images.candidates.legacy_image_is_blocked", return_value=True)
    def test_legacy_guard_denied_or_unavailable_returns_no_candidates(self, _guard):
        self.assertEqual(
            get_legacy_image_candidates(
                actor=self.actor,
                tenant_id=self.tenant.pk,
                organization_id=self.organization.pk,
            ),
            (),
        )

    def test_existing_legacy_ref_rechecks_guard_before_preview_or_processing(self):
        with patch(
            "crm.services.images.candidates.legacy_image_is_blocked",
            return_value=False,
        ):
            candidate = get_legacy_image_candidates(
                actor=self.actor,
                tenant_id=self.tenant.pk,
                organization_id=self.organization.pk,
            )[0]

        for operation in (
            lambda: render_candidate_preview(
                actor=self.actor,
                tenant_id=self.tenant.pk,
                organization_id=self.organization.pk,
                candidate_ref=candidate.candidate_ref,
                original=True,
            ),
            lambda: process_image_candidate(
                actor=self.actor,
                tenant_id=self.tenant.pk,
                organization_id=self.organization.pk,
                candidate_ref=candidate.candidate_ref,
                image_kind="photo",
            ),
        ):
            with self.subTest(operation=operation), patch(
                "crm.services.images.candidates.legacy_image_is_blocked",
                return_value=True,
            ), patch(
                "crm.services.images.candidates.fetch_external_resource"
            ) as fetch_mock, patch(
                "crm.services.images.candidates.ingest_uploaded_image"
            ) as ingest_mock:
                with self.assertRaises(ImageCandidateFlowError) as raised:
                    operation()
                self.assertEqual(raised.exception.code, "legacy_blocked")
                fetch_mock.assert_not_called()
                ingest_mock.assert_not_called()

    @patch("crm.services.images.candidates.legacy_image_is_blocked", return_value=False)
    def test_invalid_sensitive_fragment_and_favicon_urls_are_not_candidates(self, _guard):
        self.organization.thumbnail_image_url = "ftp://cdn.example.no/file.jpg"
        self.organization.og_image_url = "https://cdn.example.no/file.jpg?token=secret"
        self.organization.auto_thumbnail_url = "https://www.google.com/s2/favicons?domain=example.no&sz=256"
        self.organization.save(
            update_fields=["thumbnail_image_url", "og_image_url", "auto_thumbnail_url"]
        )
        self.assertEqual(
            get_legacy_image_candidates(
                actor=self.actor,
                tenant_id=self.tenant.pk,
                organization_id=self.organization.pk,
            ),
            (),
        )

    @patch("crm.services.images.candidates.legacy_image_is_blocked", return_value=False)
    def test_signed_ref_is_rejected_for_wrong_organization_and_tenant(self, _guard):
        candidate = get_legacy_image_candidates(
            actor=self.actor,
            tenant_id=self.tenant.pk,
            organization_id=self.organization.pk,
        )[0]
        for tenant_id, organization_id in (
            (self.tenant.pk, self.organization.pk + 999),
            (self.other_tenant.pk, self.other_organization.pk),
        ):
            with self.subTest(tenant_id=tenant_id, organization_id=organization_id):
                with self.assertRaises(ImageCandidateFlowError) as raised:
                    render_candidate_preview(
                        actor=self.actor,
                        tenant_id=tenant_id,
                        organization_id=organization_id,
                        candidate_ref=candidate.candidate_ref,
                    )
                self.assertIn(raised.exception.code, {"not_found", "wrong_scope"})

    @patch("crm.services.images.candidates.legacy_image_is_blocked", return_value=False)
    def test_expired_ref_is_rejected_before_fetch(self, _guard):
        candidate = get_legacy_image_candidates(
            actor=self.actor,
            tenant_id=self.tenant.pk,
            organization_id=self.organization.pk,
        )[0]
        with patch("crm.services.images.candidates.REF_TTL_SECONDS", -1), patch(
            "crm.services.images.candidates.fetch_external_resource"
        ) as fetch_mock:
            with self.assertRaises(ImageCandidateFlowError) as raised:
                render_candidate_preview(
                    actor=self.actor,
                    tenant_id=self.tenant.pk,
                    organization_id=self.organization.pk,
                    candidate_ref=candidate.candidate_ref,
                )
        self.assertEqual(raised.exception.code, "expired_ref")
        fetch_mock.assert_not_called()

    @patch("crm.services.images.candidates.legacy_image_is_blocked", return_value=False)
    def test_explicit_preview_uses_secure_fetch_and_does_not_change_locked_selection(self, _guard):
        selection = OrganizationImageSelection.objects.create(
            tenant=self.tenant,
            organization=self.organization,
            selection_kind=OrganizationImageSelection.SelectionKind.SYSTEM_FALLBACK,
            alt_text="Existing locked fallback",
            revision=1,
            status=OrganizationImageSelection.Status.ACTIVE,
            locked_by=self.actor,
            locked_at=timezone.now(),
        )
        with patch("crm.services.images.candidates.fetch_external_resource") as fetch_mock:
            candidate = get_legacy_image_candidates(
                actor=self.actor,
                tenant_id=self.tenant.pk,
                organization_id=self.organization.pk,
            )[0]
        fetch_mock.assert_not_called()

        fetched = SecureFetchResult(
            requested_url="https://cdn.example.no/manual.jpg",
            final_url="https://cdn.example.no/manual.jpg",
            content_type="image/jpeg",
            body=_jpeg_bytes(),
            redirect_count=0,
        )
        with patch(
            "crm.services.images.candidates.fetch_external_resource",
            return_value=fetched,
        ) as explicit_fetch:
            preview = render_candidate_preview(
                actor=self.actor,
                tenant_id=self.tenant.pk,
                organization_id=self.organization.pk,
                candidate_ref=candidate.candidate_ref,
                original=True,
            )
        self.assertEqual(preview.content_type, "image/webp")
        explicit_fetch.assert_called_once_with(
            "https://cdn.example.no/manual.jpg",
            expected="image",
        )
        self.assertEqual(
            OrganizationImageSelection.objects.get(pk=selection.pk).status,
            OrganizationImageSelection.Status.ACTIVE,
        )
        self.assertEqual(self.organization.image_review_events.count(), 0)


class Phase3FLegacyInventoryTests(TestCase):
    @patch("crm.services.images.legacy_inventory.legacy_image_is_blocked")
    def test_empty_inventory_has_zeroes_and_never_calls_safety_or_network(self, guard):
        with patch("socket.getaddrinfo", side_effect=AssertionError("DNS forbidden")):
            inventory, details = audit_legacy_image_sources()
        self.assertTrue(all(value == 0 for value in inventory.as_dict().values()))
        self.assertEqual(details, [])
        guard.assert_not_called()

    @patch("crm.services.images.legacy_inventory.legacy_image_is_blocked", return_value=False)
    def test_inventory_classifies_all_legacy_field_shapes_without_network(self, guard):
        tenant = Tenant.objects.create(name="Inventory matrix", slug="inventory-matrix")
        Organization.objects.create(
            tenant=tenant,
            name="Thumbnail only",
            is_published=True,
            thumbnail_image_url="https://cdn.example.no/thumb.jpg",
        )
        Organization.objects.create(
            tenant=tenant,
            name="OG signed",
            og_image_url="https://cdn.example.no/og.jpg?token=secret",
        )
        Organization.objects.create(
            tenant=tenant,
            name="Auto favicon",
            auto_thumbnail_url="https://www.google.com/s2/favicons?domain=example.no&sz=256",
        )
        Organization.objects.create(
            tenant=tenant,
            name="All fields",
            thumbnail_image_url="https://cdn.example.no/a.jpg",
            og_image_url="https://cdn.example.no/a.jpg",
            auto_thumbnail_url="ftp://cdn.example.no/a.jpg",
        )
        Organization.objects.create(
            tenant=tenant,
            name="Credential URL",
            thumbnail_image_url="https://user:pass@cdn.example.no/private.jpg",
        )
        with patch("socket.getaddrinfo", side_effect=AssertionError("DNS forbidden")), patch(
            "crm.services.images.fetch.fetch_external_resource",
            side_effect=AssertionError("HTTP forbidden"),
        ):
            inventory, details = audit_legacy_image_sources()
        self.assertEqual(inventory.organizations_total, 5)
        self.assertEqual(inventory.organizations_published, 1)
        self.assertEqual(inventory.organizations_unpublished, 4)
        self.assertEqual(inventory.thumbnail_image_url_set, 3)
        self.assertEqual(inventory.og_image_url_set, 2)
        self.assertEqual(inventory.auto_thumbnail_url_set, 2)
        self.assertEqual(inventory.organizations_with_legacy_url, 5)
        self.assertEqual(inventory.organizations_with_multiple_legacy_urls, 1)
        self.assertEqual(inventory.organizations_with_duplicate_field_urls, 1)
        self.assertEqual(inventory.syntactically_invalid_legacy_urls, 1)
        self.assertEqual(inventory.favicon_derived_urls, 1)
        self.assertEqual(inventory.credential_or_signed_url_suspicions, 2)
        self.assertEqual(details, [])
        self.assertEqual(guard.call_count, 5)

    @patch(
        "crm.services.images.legacy_inventory.ImageSafetyBridgeClient.authorize",
        return_value=SimpleNamespace(authorized=True),
    )
    @patch("crm.services.images.legacy_inventory.legacy_image_is_blocked", return_value=False)
    def test_inventory_distinguishes_selection_binding_and_safety_active_release(
        self,
        _guard,
        authorize,
    ):
        tenant = Tenant.objects.create(name="Release inventory", slug="release-inventory")
        actor = get_user_model().objects.create_user(username="release-inventory-editor")
        organization = Organization.objects.create(
            tenant=tenant,
            name="Release actor",
            is_published=True,
            thumbnail_image_url="https://cdn.example.no/release.jpg",
        )
        asset = ImageAsset.objects.create(
            tenant=tenant,
            private_storage_key="release-inventory/source.jpg",
            checksum_sha256="a" * 64,
            original_format=ImageAsset.OriginalFormat.JPEG,
            mime_type="image/jpeg",
            width=1200,
            height=800,
            file_size_bytes=100,
            validation_version="validation-v1",
        )
        rendition_set = ImageRenditionSet.objects.create(
            tenant=tenant,
            asset=asset,
            fit_mode=ImageRenditionSet.FitMode.COVER,
            processing_version="processing-v1",
            render_config_hash_sha256="b" * 64,
        )
        renditions = []
        for index, variant in enumerate(("square", "landscape", "share"), start=1):
            renditions.append(
                ImageRendition.objects.create(
                    tenant=tenant,
                    rendition_set=rendition_set,
                    variant=variant,
                    output_format=ImageRendition.OutputFormat.WEBP,
                    width=500 + index,
                    height=400 + index,
                    file_size_bytes=100 + index,
                    checksum_sha256=f"{index}" * 64,
                    artifact_storage_key=f"release-inventory/{variant}.webp",
                )
            )
        selection = OrganizationImageSelection.objects.create(
            tenant=tenant,
            organization=organization,
            selection_kind=OrganizationImageSelection.SelectionKind.ASSET,
            rendition_set=rendition_set,
            alt_text="Approved asset",
            revision=1,
            status=OrganizationImageSelection.Status.ACTIVE,
            locked_by=actor,
            locked_at=timezone.now(),
        )
        release_id = uuid.uuid4()
        release = OrganizationImageRelease.objects._insert_from_release_service(
            [
                OrganizationImageRelease(
                    release_id=release_id,
                    tenant=tenant,
                    organization=organization,
                    selection=selection,
                    selection_revision_snapshot=1,
                    rendition_set=rendition_set,
                    key_schema_version=1,
                )
            ]
        )[0]
        OrganizationImageReleaseRendition.objects._insert_from_release_service(
            [
                OrganizationImageReleaseRendition(
                    release=release,
                    rendition=rendition,
                    variant=rendition.variant,
                    output_format=rendition.output_format,
                    artifact_storage_key_snapshot=rendition.artifact_storage_key,
                    artifact_checksum_sha256_snapshot=rendition.checksum_sha256,
                    public_storage_key=build_public_release_key(
                        release_id,
                        rendition.variant,
                        rendition.output_format,
                    ),
                )
                for rendition in renditions
            ]
        )
        inventory, _ = audit_legacy_image_sources()
        self.assertEqual(inventory.organizations_with_active_typed_selection, 1)
        self.assertEqual(inventory.organizations_with_selection_bound_public_release, 1)
        self.assertEqual(inventory.organizations_with_public_release, 1)
        self.assertEqual(authorize.call_count, 3)

    @patch("crm.services.images.legacy_inventory.legacy_image_is_blocked", return_value=False)
    def test_inventory_is_read_only_aggregated_and_redacts_all_query_values(self, guard):
        tenant = Tenant.objects.create(name="Inventory", slug="inventory")
        organization = Organization.objects.create(
            tenant=tenant,
            name="Inventory actor",
            is_published=True,
            thumbnail_image_url="https://cdn.example.no/a.jpg?campaign=secret-value",
            og_image_url="https://cdn.example.no/a.jpg?campaign=secret-value",
            auto_thumbnail_url="https://www.google.com/s2/favicons?domain=example.no&sz=256",
        )
        before = Organization.objects.filter(pk=organization.pk).values().get()
        inventory, details = audit_legacy_image_sources(verbose=True)
        self.assertEqual(inventory.organizations_total, 1)
        self.assertEqual(inventory.organizations_published, 1)
        self.assertEqual(inventory.organizations_with_legacy_url, 1)
        self.assertEqual(inventory.organizations_with_duplicate_field_urls, 1)
        self.assertEqual(inventory.favicon_derived_urls, 1)
        self.assertNotIn("secret-value", json.dumps(details))
        self.assertIn("%5BREDACTED%5D", json.dumps(details))
        self.assertEqual(Organization.objects.filter(pk=organization.pk).values().get(), before)
        guard.assert_called_once()

    @patch("crm.services.images.legacy_inventory.legacy_image_is_blocked", return_value=True)
    def test_management_command_json_never_prints_unredacted_sensitive_value(self, _guard):
        tenant = Tenant.objects.create(name="Command", slug="inventory-command")
        Organization.objects.create(
            tenant=tenant,
            name="Command actor",
            og_image_url="https://cdn.example.no/a.jpg?token=never-print-me",
        )
        from io import StringIO

        output = StringIO()
        call_command("audit_legacy_image_sources", "--json", "--verbose", stdout=output)
        payload = output.getvalue()
        self.assertNotIn("never-print-me", payload)
        self.assertEqual(json.loads(payload)["inventory"]["organizations_total"], 1)
