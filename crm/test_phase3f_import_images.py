from __future__ import annotations

import importlib
import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.test import TestCase, override_settings
from django.utils import timezone

from crm.models import (
    ImageAsset,
    ImageRendition,
    ImageRenditionSet,
    ImageReviewEvent,
    ImmutableImportImageDecisionError,
    ImportImageDecision,
    ImportJob,
    ImportRow,
    Organization,
    OrganizationImageSelection,
    Tenant,
    TenantMembership,
)
from crm.services.images.safety_guards import (
    ImageSafetyGuardUnavailable,
    ImageSourceChecksumDenied,
)
from crm.services.images.selections import AssetApprovalEvidence


image_decisions = importlib.import_module("crm.services.import.image_decisions")
import_commit = importlib.import_module("crm.services.import.commit")


@override_settings(
    IMAGE_ASSET_FEATURE_ENABLED=True,
    IMPORT_IMAGE_DECISIONS_ENABLED=True,
    PUBLIC_IMAGE_RELEASE_MATERIALIZATION_ENABLED=False,
)
class Phase3FImportImageDecisionTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Import image", slug="import-image")
        self.other_tenant = Tenant.objects.create(name="Other", slug="import-image-other")
        self.actor = get_user_model().objects.create_user(username="import-image-editor")
        TenantMembership.objects.create(
            tenant=self.tenant,
            user=self.actor,
            role=TenantMembership.Role.REDIGERER,
        )
        self.job = ImportJob.objects.create(
            tenant=self.tenant,
            created_by=self.actor,
            source_type=ImportJob.SourceType.CSV,
            import_mode=ImportJob.ImportMode.ORGANIZATIONS_ONLY,
            status=ImportJob.Status.PREVIEW_READY,
        )
        self.row = ImportRow.objects.create(
            import_job=self.job,
            row_number=1,
            row_status=ImportRow.RowStatus.VALID,
            proposed_action=ImportRow.ProposedAction.UPDATE,
        )
        self.organization = Organization.objects.create(
            tenant=self.tenant,
            name="Reviewed actor",
            is_published=True,
            publish_phone=True,
        )
        self.snapshot = {"name": "Reviewed actor", "org_number": "", "website_url": ""}
        self.counter = 0

    def image_domain(self, *, tenant=None, complete=True):
        tenant = tenant or self.tenant
        self.counter += 1
        asset = ImageAsset.objects.create(
            tenant=tenant,
            private_storage_key=f"assets/{tenant.pk}-{self.counter}.jpg",
            checksum_sha256=f"{self.counter:x}" * 64,
            original_format=ImageAsset.OriginalFormat.JPEG,
            mime_type="image/jpeg",
            width=1200,
            height=800,
            file_size_bytes=1000,
            validation_version="validation-v1",
        )
        rendition_set = ImageRenditionSet.objects.create(
            tenant=tenant,
            asset=asset,
            fit_mode=ImageRenditionSet.FitMode.COVER,
            processing_version="processing-v1",
            render_config_hash_sha256=f"{self.counter + 8:x}"[-1] * 64,
        )
        variants = [ImageRendition.Variant.SQUARE]
        if complete:
            variants.extend([ImageRendition.Variant.LANDSCAPE, ImageRendition.Variant.SHARE])
        for index, variant in enumerate(variants, start=1):
            ImageRendition.objects.create(
                tenant=tenant,
                rendition_set=rendition_set,
                variant=variant,
                output_format=ImageRendition.OutputFormat.WEBP,
                width=500 + index,
                height=500 + index,
                file_size_bytes=100 + index,
                checksum_sha256=f"{self.counter + index:x}"[-1] * 64,
                artifact_storage_key=f"renditions/{tenant.pk}-{self.counter}-{variant}.webp",
            )
        return asset, rendition_set

    def active_selection(self):
        return OrganizationImageSelection.objects.filter(
            tenant=self.tenant,
            organization=self.organization,
            status=OrganizationImageSelection.Status.ACTIVE,
        ).first()

    def existing_fallback(self, *, revision=1):
        return OrganizationImageSelection.objects.create(
            tenant=self.tenant,
            organization=self.organization,
            selection_kind=OrganizationImageSelection.SelectionKind.SYSTEM_FALLBACK,
            alt_text="Existing fallback",
            revision=revision,
            status=OrganizationImageSelection.Status.ACTIVE,
            locked_by=self.actor,
            locked_at=timezone.now(),
        )

    def create_decision(self, kind, *, selection=None, asset=None, rendition_set=None, **kwargs):
        evidence = None
        if kind == ImportImageDecision.DecisionKind.SET_APPROVED_IMAGE:
            evidence = AssetApprovalEvidence(
                source_type=ImageReviewEvent.SourceType.UPLOAD,
                provider="import-review",
            )
        return image_decisions.create_import_image_decision(
            import_row_id=self.row.pk,
            actor=self.actor,
            decision_kind=kind,
            proposed_actor_snapshot=self.snapshot,
            target_organization_id=self.organization.pk,
            expected_selection_id=selection.pk if selection else None,
            expected_selection_revision=selection.revision if selection else 0,
            asset_id=asset.pk if asset else None,
            rendition_set_id=rendition_set.pk if rendition_set else None,
            approved_alt_text=kwargs.get(
                "alt_text",
                "" if kind == ImportImageDecision.DecisionKind.KEEP_LOCKED_IMAGE else "Approved actor image",
            ),
            approved_public_credit="Photographer" if asset else "",
            asset_evidence=evidence,
        )

    def apply(self, decision, *, snapshot=None):
        return image_decisions.apply_import_image_decision(
            decision=decision,
            organization=self.organization,
            organization_was_created=False,
            proposed_actor_snapshot=snapshot or self.snapshot,
        )

    @staticmethod
    def normalized_payload(name="Committed image actor"):
        return {
            "organization": {
                "name": name,
                "org_number": "",
                "email": "",
                "phone": "",
                "municipalities": "Oslo",
                "description": "",
                "note": "",
                "is_published": False,
                "publish_phone": False,
                "website_url": "https://committed.example.no",
                "instagram_url": "",
                "tiktok_url": "",
                "linkedin_url": "",
                "facebook_url": "",
                "youtube_url": "",
                "tags": [],
                "categories": [],
                "subcategories": [],
            },
            "person": {
                "full_name": "",
                "title": "",
                "email": "",
                "phone": "",
                "email_public": False,
                "phone_public": False,
                "municipality": "",
                "website_url": "",
                "instagram_url": "",
                "tiktok_url": "",
                "linkedin_url": "",
                "facebook_url": "",
                "youtube_url": "",
                "note": "",
                "tags": [],
                "categories": [],
                "subcategories": [],
                "secondary_contacts": [],
            },
            "link": {"status": "ACTIVE", "publish_person": False},
        }

    def test_keep_is_an_explicit_no_write(self):
        selection = self.existing_fallback()
        decision = self.create_decision(
            ImportImageDecision.DecisionKind.KEEP_LOCKED_IMAGE,
            selection=selection,
        )
        result = self.apply(decision)
        self.assertFalse(result.changed)
        self.assertEqual(result.selection, selection)
        self.assertEqual(ImageReviewEvent.objects.count(), 0)
        self.assertEqual(OrganizationImageSelection.objects.count(), 1)

    def test_import_without_typed_decision_preserves_existing_locked_selection(self):
        selection = self.existing_fallback()
        normalized = self.normalized_payload(name=self.organization.name)
        normalized["organization"]["is_published"] = self.organization.is_published
        normalized["organization"]["publish_phone"] = self.organization.publish_phone
        self.row.normalized_payload_json = normalized
        self.row.match_result_json = {"organization": {"exact_id": self.organization.pk}}
        self.row.row_status = ImportRow.RowStatus.VALID
        self.row.proposed_action = ImportRow.ProposedAction.UPDATE
        self.row.save(
            update_fields=[
                "normalized_payload_json",
                "match_result_json",
                "row_status",
                "proposed_action",
                "updated_at",
            ]
        )
        result = import_commit.commit_import_job(self.job)
        selection.refresh_from_db()
        self.assertEqual(result.status, ImportJob.Status.COMPLETED)
        self.assertEqual(selection.status, OrganizationImageSelection.Status.ACTIVE)
        self.assertEqual(OrganizationImageSelection.objects.count(), 1)
        self.assertEqual(ImageReviewEvent.objects.count(), 0)

    @patch("crm.services.images.candidates.fetch_external_resource")
    @patch("crm.services.open_graph.refresh_organization_open_graph")
    def test_set_creates_one_selection_and_one_import_bound_event_on_retry(self, refresh, fetch):
        asset, rendition_set = self.image_domain()
        decision = self.create_decision(
            ImportImageDecision.DecisionKind.SET_APPROVED_IMAGE,
            asset=asset,
            rendition_set=rendition_set,
        )
        first = self.apply(decision)
        second = self.apply(decision)
        self.assertEqual(first.selection.pk, second.selection.pk)
        self.assertEqual(first.event.pk, second.event.pk)
        self.assertEqual(OrganizationImageSelection.objects.count(), 1)
        self.assertEqual(ImageReviewEvent.objects.count(), 1)
        self.assertEqual(first.event.import_image_decision_id, decision.pk)
        self.assertEqual(first.event.actor_user_id, self.actor.pk)
        self.assertEqual(
            first.event.approval_text_version_snapshot,
            decision.approval_text_version_snapshot,
        )
        self.assertEqual(first.event.approval_text_snapshot, decision.approval_text_snapshot)
        refresh.assert_not_called()
        fetch.assert_not_called()

    def test_applied_retry_revalidates_tenant_target_and_actor_snapshot(self):
        asset, rendition_set = self.image_domain()
        decision = self.create_decision(
            ImportImageDecision.DecisionKind.SET_APPROVED_IMAGE,
            asset=asset,
            rendition_set=rendition_set,
        )
        original = self.apply(decision)
        self.assertEqual(self.apply(decision).event.pk, original.event.pk)

        wrong_target = Organization.objects.create(tenant=self.tenant, name="Wrong target")
        wrong_tenant_target = Organization.objects.create(
            tenant=self.other_tenant,
            name="Wrong tenant target",
        )
        for organization, snapshot in (
            (wrong_target, self.snapshot),
            (wrong_tenant_target, self.snapshot),
            (self.organization, {"name": "Changed after apply"}),
        ):
            with self.subTest(organization=organization.pk, snapshot=snapshot), self.assertRaises(
                image_decisions.ImportImageDecisionError
            ):
                image_decisions.apply_import_image_decision(
                    decision=decision,
                    organization=organization,
                    organization_was_created=False,
                    proposed_actor_snapshot=snapshot,
                )

    def test_decision_is_orm_immutable_after_review(self):
        decision = self.create_decision(ImportImageDecision.DecisionKind.KEEP_LOCKED_IMAGE)
        decision.decision_kind = ImportImageDecision.DecisionKind.USE_APPROVED_FALLBACK
        with self.assertRaises(ImmutableImportImageDecisionError):
            decision.save()
        with self.assertRaises(ImmutableImportImageDecisionError):
            ImportImageDecision.objects.filter(pk=decision.pk).update(
                decision_kind=ImportImageDecision.DecisionKind.USE_APPROVED_FALLBACK
            )
        with self.assertRaises(ImmutableImportImageDecisionError):
            decision.delete()
        with self.assertRaises(ImmutableImportImageDecisionError):
            ImportImageDecision.objects.bulk_create(
                [],
                update_conflicts=True,
                update_fields=["decision_kind"],
                unique_fields=["id"],
            )

    def test_stored_actor_snapshot_tampering_is_rejected(self):
        decision = self.create_decision(ImportImageDecision.DecisionKind.KEEP_LOCKED_IMAGE)
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE crm_importimagedecision SET proposed_actor_snapshot = %s WHERE id = %s",
                [json.dumps({"name": "Tampered actor"}), decision.pk],
            )
        decision.refresh_from_db()
        with self.assertRaises(image_decisions.ImportImageDecisionConflict):
            self.apply(decision)

    def test_rendition_recipe_or_artifact_drift_is_rejected(self):
        for drift in ("recipe", "artifact"):
            with self.subTest(drift=drift):
                self.row = ImportRow.objects.create(
                    import_job=self.job,
                    row_number=10 if drift == "recipe" else 11,
                )
                asset, rendition_set = self.image_domain()
                decision = self.create_decision(
                    ImportImageDecision.DecisionKind.SET_APPROVED_IMAGE,
                    asset=asset,
                    rendition_set=rendition_set,
                )
                if drift == "recipe":
                    ImageRenditionSet.objects.filter(pk=rendition_set.pk).update(
                        processing_version="processing-v2"
                    )
                else:
                    ImageRendition.objects.filter(
                        rendition_set=rendition_set,
                        variant=ImageRendition.Variant.SQUARE,
                    ).update(checksum_sha256="f" * 64)
                with self.assertRaises(image_decisions.ImportImageDecisionNotReady):
                    self.apply(decision)

    def test_event_uses_reviewed_approval_copy_when_runtime_constants_change(self):
        asset, rendition_set = self.image_domain()
        decision = self.create_decision(
            ImportImageDecision.DecisionKind.SET_APPROVED_IMAGE,
            asset=asset,
            rendition_set=rendition_set,
        )
        with patch(
            "crm.services.images.selections.IMAGE_APPROVAL_TEXT_VERSION",
            "image-approval-v999",
        ), patch(
            "crm.services.images.selections.IMAGE_APPROVAL_TEXT",
            "Changed after review",
        ):
            result = self.apply(decision)
        self.assertEqual(
            result.event.approval_text_version_snapshot,
            decision.approval_text_version_snapshot,
        )
        self.assertEqual(result.event.approval_text_snapshot, decision.approval_text_snapshot)

    def test_set_replacement_uses_expected_revision(self):
        previous = self.existing_fallback()
        asset, rendition_set = self.image_domain()
        decision = self.create_decision(
            ImportImageDecision.DecisionKind.SET_APPROVED_IMAGE,
            selection=previous,
            asset=asset,
            rendition_set=rendition_set,
        )
        result = self.apply(decision)
        previous.refresh_from_db()
        self.assertEqual(previous.status, OrganizationImageSelection.Status.ARCHIVED)
        self.assertEqual(result.selection.revision, 2)
        self.assertEqual(result.selection.selection_kind, OrganizationImageSelection.SelectionKind.ASSET)
        self.organization.refresh_from_db()
        self.assertTrue(self.organization.is_published)
        self.assertTrue(self.organization.publish_phone)

    def test_fallback_first_and_asset_replacement_use_existing_domain_paths(self):
        first_decision = self.create_decision(
            ImportImageDecision.DecisionKind.USE_APPROVED_FALLBACK,
            alt_text="Approved fallback",
        )
        first = self.apply(first_decision)
        self.assertEqual(first.selection.revision, 1)
        self.assertEqual(first.selection.selection_kind, OrganizationImageSelection.SelectionKind.SYSTEM_FALLBACK)

        self.row = ImportRow.objects.create(
            import_job=self.job,
            row_number=2,
            row_status=ImportRow.RowStatus.VALID,
        )
        other = Organization.objects.create(tenant=self.tenant, name="Asset actor")
        self.organization = other
        self.snapshot = {"name": "Asset actor"}
        asset, rendition_set = self.image_domain()
        set_decision = self.create_decision(
            ImportImageDecision.DecisionKind.SET_APPROVED_IMAGE,
            asset=asset,
            rendition_set=rendition_set,
        )
        asset_result = self.apply(set_decision)
        self.row = ImportRow.objects.create(
            import_job=self.job,
            row_number=3,
            row_status=ImportRow.RowStatus.VALID,
        )
        fallback_decision = self.create_decision(
            ImportImageDecision.DecisionKind.USE_APPROVED_FALLBACK,
            selection=asset_result.selection,
            alt_text="Approved fallback",
        )
        fallback = self.apply(fallback_decision)
        self.assertEqual(fallback.selection.revision, 2)
        self.assertEqual(
            fallback.event.event_type,
            ImageReviewEvent.EventType.SELECTION_REMOVED_TO_FALLBACK,
        )

    def test_stale_selection_and_stale_actor_snapshot_fail_closed(self):
        decision = self.create_decision(ImportImageDecision.DecisionKind.KEEP_LOCKED_IMAGE)
        self.existing_fallback()
        with self.assertRaises(image_decisions.ImportImageDecisionConflict):
            self.apply(decision)

        self.row = ImportRow.objects.create(import_job=self.job, row_number=2)
        selection = self.active_selection()
        second = self.create_decision(
            ImportImageDecision.DecisionKind.KEEP_LOCKED_IMAGE,
            selection=selection,
        )
        with self.assertRaises(image_decisions.ImportImageDecisionConflict):
            self.apply(second, snapshot={"name": "Changed actor"})

    def test_wrong_tenant_and_incomplete_rendition_set_are_rejected(self):
        other_asset, other_set = self.image_domain(tenant=self.other_tenant)
        with self.assertRaises(image_decisions.ImportImageDecisionNotReady):
            self.create_decision(
                ImportImageDecision.DecisionKind.SET_APPROVED_IMAGE,
                asset=other_asset,
                rendition_set=other_set,
            )
        asset, incomplete = self.image_domain(complete=False)
        with self.assertRaises(image_decisions.ImportImageDecisionNotReady):
            self.create_decision(
                ImportImageDecision.DecisionKind.SET_APPROVED_IMAGE,
                asset=asset,
                rendition_set=incomplete,
            )

    @override_settings(PUBLIC_IMAGE_RELEASE_MATERIALIZATION_ENABLED=True)
    def test_denied_checksum_and_unavailable_safety_are_fail_closed(self):
        for row_number, error in (
            (1, ImageSourceChecksumDenied("denied")),
            (2, ImageSafetyGuardUnavailable("unavailable")),
        ):
            if row_number > 1:
                self.row = ImportRow.objects.create(import_job=self.job, row_number=row_number)
            asset, rendition_set = self.image_domain()
            with self.subTest(stage="review", error=type(error).__name__), patch(
                "crm.services.import.image_decisions.require_source_checksum_allowed",
                side_effect=error,
            ):
                with self.assertRaises(image_decisions.ImportImageDecisionNotReady):
                    self.create_decision(
                        ImportImageDecision.DecisionKind.SET_APPROVED_IMAGE,
                        asset=asset,
                        rendition_set=rendition_set,
                    )

            with override_settings(PUBLIC_IMAGE_RELEASE_MATERIALIZATION_ENABLED=False):
                decision = self.create_decision(
                    ImportImageDecision.DecisionKind.SET_APPROVED_IMAGE,
                    asset=asset,
                    rendition_set=rendition_set,
                )
            with self.subTest(stage="commit", error=type(error).__name__), patch(
                "crm.services.images.selections.require_source_checksum_allowed",
                side_effect=error,
            ):
                with self.assertRaises(Exception) as raised:
                    self.apply(decision)
            self.assertIn(
                raised.exception.__class__.__name__,
                {"ImageSelectionChecksumDenied", "ImageSelectionSafetyUnavailable"},
            )
            self.assertFalse(ImageReviewEvent.objects.filter(import_image_decision=decision).exists())

    def test_database_xor_and_model_tenant_structure_reject_invalid_rows(self):
        asset, _ = self.image_domain()
        snapshot, snapshot_hash = image_decisions.canonical_actor_snapshot(self.snapshot)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ImportImageDecision.objects.create(
                    import_row=self.row,
                    decided_by=self.actor,
                    decision_kind=ImportImageDecision.DecisionKind.KEEP_LOCKED_IMAGE,
                    asset=asset,
                    proposed_actor_snapshot=snapshot,
                    canonical_snapshot_hash_sha256=snapshot_hash,
                )

        other_row = ImportRow.objects.create(import_job=self.job, row_number=2)
        invalid = ImportImageDecision(
            import_row=other_row,
            decided_by=self.actor,
            decision_kind=ImportImageDecision.DecisionKind.KEEP_LOCKED_IMAGE,
            target_organization=Organization.objects.create(
                tenant=self.other_tenant,
                name="Wrong tenant target",
            ),
            proposed_actor_snapshot=snapshot,
            canonical_snapshot_hash_sha256=snapshot_hash,
        )
        with self.assertRaises(ValidationError):
            invalid.full_clean()

    def test_new_actor_snapshot_and_publication_state_are_preserved(self):
        new_row = ImportRow.objects.create(import_job=self.job, row_number=2)
        new_snapshot = {"name": "New actor", "is_published": False}
        decision = image_decisions.create_import_image_decision(
            import_row_id=new_row.pk,
            actor=self.actor,
            decision_kind=ImportImageDecision.DecisionKind.USE_APPROVED_FALLBACK,
            proposed_actor_snapshot=new_snapshot,
            approved_alt_text="Approved fallback",
        )
        organization = Organization.objects.create(
            tenant=self.tenant,
            name="New actor",
            is_published=False,
            publish_phone=False,
        )
        result = image_decisions.apply_import_image_decision(
            decision=decision,
            organization=organization,
            organization_was_created=True,
            proposed_actor_snapshot=new_snapshot,
        )
        organization.refresh_from_db()
        self.assertTrue(result.changed)
        self.assertFalse(organization.is_published)
        self.assertFalse(organization.publish_phone)

    @patch("crm.services.images.releases.create_organization_image_release")
    @patch("crm.services.images.candidates.fetch_external_resource")
    @patch("crm.services.open_graph.refresh_organization_open_graph")
    def test_import_commit_applies_prepared_selection_with_db_only_and_no_public_release(
        self,
        refresh,
        fetch,
        create_release,
    ):
        job = ImportJob.objects.create(
            tenant=self.tenant,
            created_by=self.actor,
            source_type=ImportJob.SourceType.CSV,
            import_mode=ImportJob.ImportMode.ORGANIZATIONS_ONLY,
            status=ImportJob.Status.PREVIEW_READY,
        )
        normalized = self.normalized_payload()
        row = ImportRow.objects.create(
            import_job=job,
            row_number=1,
            normalized_payload_json=normalized,
            row_status=ImportRow.RowStatus.VALID,
            proposed_action=ImportRow.ProposedAction.CREATE,
        )
        asset, rendition_set = self.image_domain()
        decision = image_decisions.create_import_image_decision(
            import_row_id=row.pk,
            actor=self.actor,
            decision_kind=ImportImageDecision.DecisionKind.SET_APPROVED_IMAGE,
            proposed_actor_snapshot=normalized["organization"],
            asset_id=asset.pk,
            rendition_set_id=rendition_set.pk,
            approved_alt_text="Approved import image",
            approved_public_credit="Photographer",
            asset_evidence=AssetApprovalEvidence(
                source_type=ImageReviewEvent.SourceType.UPLOAD,
                provider="import-review",
            ),
        )
        result = import_commit.commit_import_job(job)
        organization = Organization.objects.get(
            tenant=self.tenant,
            name="Committed image actor",
        )
        selection = OrganizationImageSelection.objects.get(
            tenant=self.tenant,
            organization=organization,
            status=OrganizationImageSelection.Status.ACTIVE,
        )
        self.assertEqual(result.status, ImportJob.Status.COMPLETED)
        self.assertEqual(selection.rendition_set_id, rendition_set.pk)
        self.assertEqual(selection.review_events.get().import_image_decision_id, decision.pk)
        self.assertFalse(organization.is_published)
        self.assertFalse(organization.publish_phone)
        refresh.assert_not_called()
        fetch.assert_not_called()
        create_release.assert_not_called()

    @override_settings(IMPORT_IMAGE_DECISIONS_ENABLED=False)
    def test_feature_gate_blocks_typed_creation_without_affecting_existing_import_rows(self):
        with self.assertRaises(image_decisions.ImportImageDecisionFeatureDisabled):
            self.create_decision(ImportImageDecision.DecisionKind.KEEP_LOCKED_IMAGE)
        self.assertEqual(ImportRow.objects.count(), 1)
        self.assertEqual(ImportImageDecision.objects.count(), 0)
