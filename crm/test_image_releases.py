import inspect
from pathlib import Path
import tempfile
import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.db.models.deletion import ProtectedError
from django.test import SimpleTestCase, TestCase, TransactionTestCase, override_settings
from django.utils import timezone

from .models import (
    ImageAsset,
    ImageRendition,
    ImageRenditionSet,
    ImmutableImageReleaseError,
    Organization,
    OrganizationImageRelease,
    OrganizationImageReleaseRendition,
    OrganizationImageSelection,
    Tenant,
)
from .services.images.releases import (
    ImageReleaseFeatureDisabledError,
    IncompleteImageReleaseError,
    InvalidImageReleaseError,
    InvalidPublicReleaseKeyError,
    build_public_release_key,
    create_organization_image_release,
)


class PublicReleaseKeyBuilderTests(SimpleTestCase):
    def test_builds_canonical_relative_keys_for_all_formats(self):
        release_id = uuid.UUID("5DB81680-4557-4376-B213-51D90939C425")

        self.assertEqual(
            build_public_release_key(release_id, "square", "webp"),
            "releases/5db81680-4557-4376-b213-51d90939c425/square.webp",
        )
        self.assertEqual(
            build_public_release_key(str(release_id).upper(), "landscape", "png"),
            "releases/5db81680-4557-4376-b213-51d90939c425/landscape.png",
        )
        self.assertEqual(
            build_public_release_key(release_id, "share", "jpeg"),
            "releases/5db81680-4557-4376-b213-51d90939c425/share.jpg",
        )

    def test_rejects_invalid_non_v4_uuid_variant_and_output_format(self):
        invalid_values = (
            ("not-a-uuid", "square", "webp"),
            (uuid.uuid1(), "square", "webp"),
            (uuid.uuid4(), "portrait", "webp"),
            (uuid.uuid4(), "square", "gif"),
        )

        for release_id, variant, output_format in invalid_values:
            with self.subTest(
                release_id=release_id,
                variant=variant,
                output_format=output_format,
            ):
                with self.assertRaises(InvalidPublicReleaseKeyError):
                    build_public_release_key(release_id, variant, output_format)

    def test_key_contains_only_release_uuid_variant_and_extension(self):
        key = build_public_release_key(uuid.uuid4(), "square", "webp")

        self.assertRegex(
            key,
            r"^releases/[0-9a-f-]{36}/square\.webp$",
        )
        for forbidden in (
            "tenant",
            "organization",
            "revision",
            "checksum",
            "https://",
            "/srv/",
            "token",
            "?",
        ):
            self.assertNotIn(forbidden, key)


@override_settings(IMAGE_ASSET_FEATURE_ENABLED=True)
class OrganizationImageReleaseTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="release-editor",
            password="test-password",
        )
        self.tenant = Tenant.objects.create(name="Release tenant", slug="release-tenant")
        self.organization = Organization.objects.create(
            tenant=self.tenant,
            name="Release organization",
        )
        self.asset = self.create_asset(
            tenant=self.tenant,
            storage_key="assets/release-source.jpeg",
            checksum="a" * 64,
        )
        self.rendition_set = self.create_rendition_set(
            tenant=self.tenant,
            asset=self.asset,
            render_hash="b" * 64,
        )
        self.renditions = self.create_complete_renditions(
            tenant=self.tenant,
            rendition_set=self.rendition_set,
            prefix="release",
        )
        self.selection = self.create_selection(
            tenant=self.tenant,
            organization=self.organization,
            rendition_set=self.rendition_set,
        )

    def create_asset(self, *, tenant, storage_key, checksum):
        return ImageAsset.objects.create(
            tenant=tenant,
            private_storage_key=storage_key,
            checksum_sha256=checksum,
            original_format=ImageAsset.OriginalFormat.JPEG,
            mime_type="image/jpeg",
            width=1600,
            height=900,
            file_size_bytes=123456,
            validation_version="validation-v1",
        )

    def create_rendition_set(self, *, tenant, asset, render_hash):
        return ImageRenditionSet.objects.create(
            tenant=tenant,
            asset=asset,
            fit_mode=ImageRenditionSet.FitMode.COVER,
            processing_version="processing-v1",
            render_config_hash_sha256=render_hash,
        )

    def create_complete_renditions(self, *, tenant, rendition_set, prefix):
        specifications = (
            (ImageRendition.Variant.SQUARE, ImageRendition.OutputFormat.WEBP, 512, 512, "c"),
            (
                ImageRendition.Variant.LANDSCAPE,
                ImageRendition.OutputFormat.PNG,
                800,
                450,
                "d",
            ),
            (ImageRendition.Variant.SHARE, ImageRendition.OutputFormat.JPEG, 1200, 630, "e"),
        )
        return tuple(
            ImageRendition.objects.create(
                tenant=tenant,
                rendition_set=rendition_set,
                variant=variant,
                output_format=output_format,
                width=width,
                height=height,
                file_size_bytes=45678,
                checksum_sha256=checksum_character * 64,
                artifact_storage_key=f"renditions/{prefix}-{variant}.{output_format}",
            )
            for variant, output_format, width, height, checksum_character in specifications
        )

    def create_selection(
        self,
        *,
        tenant,
        organization,
        rendition_set,
        revision=1,
        status=OrganizationImageSelection.Status.ACTIVE,
    ):
        return OrganizationImageSelection.objects.create(
            tenant=tenant,
            organization=organization,
            selection_kind=OrganizationImageSelection.SelectionKind.ASSET,
            rendition_set=rendition_set,
            alt_text="Release image",
            public_credit="Photographer",
            revision=revision,
            status=status,
            locked_by=self.user,
            locked_at=timezone.now(),
        )

    def create_release(self):
        return create_organization_image_release(selection=self.selection)

    def test_service_creates_complete_canonical_immutable_aggregate(self):
        result = self.create_release()

        self.assertEqual(result.release.release_id.version, 4)
        self.assertEqual(result.release.tenant, self.tenant)
        self.assertEqual(result.release.organization, self.organization)
        self.assertEqual(result.release.selection, self.selection)
        self.assertEqual(result.release.rendition_set, self.rendition_set)
        self.assertEqual(result.release.key_schema_version, 1)
        self.assertEqual(len(result.renditions), 3)
        self.assertEqual(
            {mapping.variant for mapping in result.renditions},
            {"square", "landscape", "share"},
        )
        for mapping in result.renditions:
            self.assertEqual(
                mapping.public_storage_key,
                build_public_release_key(
                    result.release.release_id,
                    mapping.variant,
                    mapping.output_format,
                ),
            )
            self.assertEqual(
                mapping.artifact_storage_key_snapshot,
                mapping.rendition.artifact_storage_key,
            )
            self.assertEqual(
                mapping.artifact_checksum_sha256_snapshot,
                mapping.rendition.checksum_sha256,
            )

    def test_service_signature_does_not_accept_free_public_storage_key(self):
        self.assertEqual(
            set(inspect.signature(create_organization_image_release).parameters),
            {"selection"},
        )
        with self.assertRaises(TypeError):
            create_organization_image_release(
                selection=self.selection,
                public_storage_key="caller/chosen.webp",
            )

    def test_external_release_insert_paths_and_caller_uuid_are_blocked(self):
        release_values = {
            "release_id": uuid.uuid4(),
            "tenant": self.tenant,
            "organization": self.organization,
            "selection": self.selection,
            "rendition_set": self.rendition_set,
        }

        with self.assertRaises(ImmutableImageReleaseError):
            OrganizationImageRelease(**release_values).save()
        with self.assertRaises(ImmutableImageReleaseError):
            OrganizationImageRelease.objects.create(**release_values)
        with self.assertRaises(ImmutableImageReleaseError):
            OrganizationImageRelease._base_objects.create(**release_values)
        with self.assertRaises(ImmutableImageReleaseError):
            OrganizationImageRelease.objects.get_or_create(**release_values)
        with self.assertRaises(ImmutableImageReleaseError):
            OrganizationImageRelease.objects.bulk_create(
                [OrganizationImageRelease(**release_values)]
            )
        with self.assertRaises(ImmutableImageReleaseError):
            OrganizationImageRelease.objects.bulk_create(
                [OrganizationImageRelease(**release_values)],
                update_conflicts=True,
                update_fields=["organization"],
                unique_fields=["release_id"],
            )

        self.assertEqual(OrganizationImageRelease.objects.count(), 0)

    def test_external_mapping_insert_paths_and_caller_key_are_blocked(self):
        result = self.create_release()
        square = next(
            rendition
            for rendition in self.renditions
            if rendition.variant == ImageRendition.Variant.SQUARE
        )
        mapping_values = {
            "release": result.release,
            "rendition": square,
            "variant": square.variant,
            "output_format": square.output_format,
            "artifact_storage_key_snapshot": square.artifact_storage_key,
            "artifact_checksum_sha256_snapshot": square.checksum_sha256,
            "public_storage_key": "caller/chosen.webp",
        }

        with self.assertRaises(ImmutableImageReleaseError):
            OrganizationImageReleaseRendition(**mapping_values).save()
        with self.assertRaises(ImmutableImageReleaseError):
            OrganizationImageReleaseRendition.objects.create(**mapping_values)
        with self.assertRaises(ImmutableImageReleaseError):
            OrganizationImageReleaseRendition._base_objects.create(**mapping_values)
        with self.assertRaises(ImmutableImageReleaseError):
            OrganizationImageReleaseRendition.objects.get_or_create(**mapping_values)
        with self.assertRaises(ImmutableImageReleaseError):
            OrganizationImageReleaseRendition.objects.bulk_create(
                [OrganizationImageReleaseRendition(**mapping_values)]
            )
        with self.assertRaises(ImmutableImageReleaseError):
            result.release.renditions.create(
                **{
                    key: value
                    for key, value in mapping_values.items()
                    if key != "release"
                }
            )

        self.assertEqual(OrganizationImageRelease.objects.count(), 1)
        self.assertEqual(OrganizationImageReleaseRendition.objects.count(), 3)

    def test_wrong_release_uuid_variant_and_extension_are_rejected(self):
        release = self.create_release().release
        square = next(
            rendition
            for rendition in self.renditions
            if rendition.variant == ImageRendition.Variant.SQUARE
        )
        canonical = build_public_release_key(
            release.release_id,
            square.variant,
            square.output_format,
        )
        invalid_keys = (
            build_public_release_key(uuid.uuid4(), square.variant, square.output_format),
            canonical.replace("/square.", "/landscape."),
            canonical.removesuffix(".webp") + ".jpg",
            "caller/chosen.webp",
        )

        for public_storage_key in invalid_keys:
            with self.subTest(public_storage_key=public_storage_key):
                mapping = OrganizationImageReleaseRendition(
                    release=release,
                    rendition=square,
                    variant=square.variant,
                    output_format=square.output_format,
                    artifact_storage_key_snapshot=square.artifact_storage_key,
                    artifact_checksum_sha256_snapshot=square.checksum_sha256,
                    public_storage_key=public_storage_key,
                )
                with self.assertRaises(ValidationError) as error:
                    mapping.full_clean()
                self.assertIn("public_storage_key", error.exception.message_dict)

    def test_non_v4_release_id_is_rejected(self):
        release = OrganizationImageRelease(
            release_id=uuid.uuid1(),
            tenant=self.tenant,
            organization=self.organization,
            selection=self.selection,
            rendition_set=self.rendition_set,
        )

        with self.assertRaises(ValidationError) as error:
            release.full_clean()

        self.assertIn("release_id", error.exception.message_dict)

    def test_mapping_rejects_wrong_rendition_set_and_artifact_snapshots(self):
        release = self.create_release().release
        other_asset = self.create_asset(
            tenant=self.tenant,
            storage_key="assets/wrong-mapping.jpeg",
            checksum="f" * 64,
        )
        other_set = self.create_rendition_set(
            tenant=self.tenant,
            asset=other_asset,
            render_hash="1" * 64,
        )
        other_square = self.create_complete_renditions(
            tenant=self.tenant,
            rendition_set=other_set,
            prefix="wrong-mapping",
        )[0]
        mapping = OrganizationImageReleaseRendition(
            release=release,
            rendition=other_square,
            variant=other_square.variant,
            output_format=other_square.output_format,
            artifact_storage_key_snapshot="renditions/not-the-artifact.webp",
            artifact_checksum_sha256_snapshot="2" * 64,
            public_storage_key=build_public_release_key(
                release.release_id,
                other_square.variant,
                other_square.output_format,
            ),
        )

        with self.assertRaises(ValidationError) as error:
            mapping.full_clean()

        self.assertIn("rendition", error.exception.message_dict)
        self.assertIn("artifact_storage_key_snapshot", error.exception.message_dict)
        self.assertIn("artifact_checksum_sha256_snapshot", error.exception.message_dict)

    def test_system_fallback_selection_is_rejected_without_partial_rows(self):
        fallback = OrganizationImageSelection.objects.create(
            tenant=self.tenant,
            organization=self.organization,
            selection_kind=OrganizationImageSelection.SelectionKind.SYSTEM_FALLBACK,
            rendition_set=None,
            alt_text="System fallback",
            revision=2,
            status=OrganizationImageSelection.Status.ARCHIVED,
            locked_by=self.user,
            locked_at=timezone.now(),
        )

        with self.assertRaises(InvalidImageReleaseError):
            create_organization_image_release(selection=fallback)

        self.assertEqual(OrganizationImageRelease.objects.count(), 0)
        self.assertEqual(OrganizationImageReleaseRendition.objects.count(), 0)

    def test_missing_variant_is_rejected_without_partial_rows(self):
        ImageRendition.objects.get(
            rendition_set=self.rendition_set,
            variant=ImageRendition.Variant.SHARE,
        ).delete()

        with self.assertRaises(IncompleteImageReleaseError):
            self.create_release()

        self.assertEqual(OrganizationImageRelease.objects.count(), 0)
        self.assertEqual(OrganizationImageReleaseRendition.objects.count(), 0)

    def test_cross_tenant_organization_and_rendition_set_are_rejected(self):
        other_tenant = Tenant.objects.create(name="Other tenant", slug="other-release-tenant")
        other_organization = Organization.objects.create(
            tenant=other_tenant,
            name="Other organization",
        )
        wrong_organization_selection = OrganizationImageSelection.objects.create(
            tenant=self.tenant,
            organization=other_organization,
            selection_kind=OrganizationImageSelection.SelectionKind.ASSET,
            rendition_set=self.rendition_set,
            alt_text="Wrong organization",
            revision=1,
            status=OrganizationImageSelection.Status.ARCHIVED,
            locked_by=self.user,
            locked_at=timezone.now(),
        )
        other_asset = self.create_asset(
            tenant=other_tenant,
            storage_key="assets/other.jpeg",
            checksum="f" * 64,
        )
        other_set = self.create_rendition_set(
            tenant=other_tenant,
            asset=other_asset,
            render_hash="1" * 64,
        )
        self.create_complete_renditions(
            tenant=other_tenant,
            rendition_set=other_set,
            prefix="other",
        )
        wrong_set_selection = OrganizationImageSelection.objects.create(
            tenant=self.tenant,
            organization=self.organization,
            selection_kind=OrganizationImageSelection.SelectionKind.ASSET,
            rendition_set=other_set,
            alt_text="Wrong rendition set",
            revision=2,
            status=OrganizationImageSelection.Status.ARCHIVED,
            locked_by=self.user,
            locked_at=timezone.now(),
        )

        for invalid_selection in (wrong_organization_selection, wrong_set_selection):
            with self.subTest(selection_id=invalid_selection.pk):
                with self.assertRaises(InvalidImageReleaseError):
                    create_organization_image_release(selection=invalid_selection)

        self.assertEqual(OrganizationImageRelease.objects.count(), 0)

    def test_wrong_rendition_tenant_is_rejected(self):
        other_tenant = Tenant.objects.create(name="Wrong rendition", slug="wrong-rendition")
        share = ImageRendition.objects.get(
            rendition_set=self.rendition_set,
            variant=ImageRendition.Variant.SHARE,
        )
        ImageRendition.objects.filter(pk=share.pk).update(tenant=other_tenant)

        with self.assertRaises(InvalidImageReleaseError):
            self.create_release()

        self.assertEqual(OrganizationImageRelease.objects.count(), 0)

    def test_mapping_failure_rolls_back_entire_aggregate(self):
        with patch.object(
            OrganizationImageReleaseRendition.objects,
            "_insert_from_release_service",
            side_effect=RuntimeError("mapping failure"),
        ):
            with self.assertRaises(RuntimeError):
                self.create_release()

        self.assertEqual(OrganizationImageRelease.objects.count(), 0)
        self.assertEqual(OrganizationImageReleaseRendition.objects.count(), 0)

    def test_r1_and_r2_reuse_same_artifacts_with_new_ids_and_keys_without_io(self):
        organization_before = Organization.objects.filter(pk=self.organization.pk).values().get()
        selection_before = OrganizationImageSelection.objects.filter(pk=self.selection.pk).values().get()

        with tempfile.TemporaryDirectory() as temporary_directory:
            private_root = Path(temporary_directory) / "private"
            public_root = Path(temporary_directory) / "public"
            with (
                override_settings(
                    IMAGE_ORIGINALS_ROOT=private_root,
                    IMAGE_RENDITIONS_ROOT=public_root,
                ),
                patch("builtins.open", side_effect=AssertionError("filesystem I/O")),
                patch(
                    "django.core.files.storage.Storage.save",
                    side_effect=AssertionError("storage I/O"),
                ),
                patch("urllib.request.urlopen", side_effect=AssertionError("network I/O")),
            ):
                first = self.create_release()
                second = self.create_release()

            self.assertFalse(private_root.exists())
            self.assertFalse(public_root.exists())

        self.assertNotEqual(first.release.release_id, second.release.release_id)
        self.assertEqual(
            {mapping.rendition_id for mapping in first.renditions},
            {mapping.rendition_id for mapping in second.renditions},
        )
        self.assertTrue(
            {mapping.public_storage_key for mapping in first.renditions}.isdisjoint(
                {mapping.public_storage_key for mapping in second.renditions}
            )
        )
        self.assertEqual(
            Organization.objects.filter(pk=self.organization.pk).values().get(),
            organization_before,
        )
        self.assertEqual(
            OrganizationImageSelection.objects.filter(pk=self.selection.pk).values().get(),
            selection_before,
        )

    @override_settings(IMAGE_ASSET_FEATURE_ENABLED=False)
    def test_feature_disabled_rejects_release_without_rows(self):
        with self.assertRaises(ImageReleaseFeatureDisabledError):
            self.create_release()

        self.assertEqual(OrganizationImageRelease.objects.count(), 0)
        self.assertEqual(OrganizationImageReleaseRendition.objects.count(), 0)

        with self.assertRaises(ImmutableImageReleaseError):
            OrganizationImageRelease.objects.create(
                release_id=uuid.uuid4(),
                tenant=self.tenant,
                organization=self.organization,
                selection=self.selection,
                rendition_set=self.rendition_set,
            )

    def test_release_and_mapping_are_immutable_through_supported_orm_paths(self):
        result = self.create_release()
        release = result.release
        mapping = result.renditions[0]
        release.organization = Organization.objects.create(
            tenant=self.tenant,
            name="Reassociation target",
        )
        mapping.variant = ImageRendition.Variant.SHARE

        for model, instance, field, value in (
            (OrganizationImageRelease, release, "organization", release.organization),
            (
                OrganizationImageReleaseRendition,
                mapping,
                "variant",
                ImageRendition.Variant.SHARE,
            ),
        ):
            with self.subTest(model=model.__name__, operation="save"):
                with self.assertRaises(ImmutableImageReleaseError):
                    instance.save()
            with self.subTest(model=model.__name__, operation="save-update-fields"):
                with self.assertRaises(ImmutableImageReleaseError):
                    instance.save(update_fields=[field])
            with self.subTest(model=model.__name__, operation="queryset-update"):
                with self.assertRaises(ImmutableImageReleaseError):
                    model.objects.filter(pk=instance.pk).update(**{field: value})
            with self.subTest(model=model.__name__, operation="bulk-update"):
                with self.assertRaises(ImmutableImageReleaseError):
                    model.objects.bulk_update([instance], [field])
            with self.subTest(model=model.__name__, operation="private-update"):
                with self.assertRaises(ImmutableImageReleaseError):
                    model._base_objects.filter(pk=instance.pk)._update(
                        [(model._meta.get_field(field), None, value)]
                    )
            with self.subTest(model=model.__name__, operation="update-or-create"):
                with self.assertRaises(ImmutableImageReleaseError):
                    model._base_objects.update_or_create(
                        pk=instance.pk,
                        defaults={field: value},
                    )
            with self.subTest(model=model.__name__, operation="update-conflicts"):
                with self.assertRaises(ImmutableImageReleaseError):
                    model._base_objects.bulk_create(
                        [instance],
                        update_conflicts=True,
                        update_fields=[field],
                        unique_fields=["id"],
                    )
            with self.subTest(model=model.__name__, operation="ignore-conflicts"):
                with self.assertRaises(ImmutableImageReleaseError):
                    model._base_objects.bulk_create(
                        [instance],
                        ignore_conflicts=True,
                    )
            with self.subTest(model=model.__name__, operation="instance-delete"):
                with self.assertRaises(ImmutableImageReleaseError):
                    instance.delete()
            with self.subTest(model=model.__name__, operation="bulk-delete"):
                with self.assertRaises(ImmutableImageReleaseError):
                    model._base_objects.filter(pk=instance.pk).delete()

    def test_foreign_key_reassociation_is_blocked_and_historical_mapping_stays_frozen(self):
        result = self.create_release()
        release = result.release
        square_mapping = next(
            mapping for mapping in result.renditions if mapping.variant == "square"
        )
        original_release = OrganizationImageRelease.objects.filter(pk=release.pk).values().get()
        original_mapping = (
            OrganizationImageReleaseRendition.objects.filter(pk=square_mapping.pk)
            .values()
            .get()
        )
        replacement_selection = self.create_selection(
            tenant=self.tenant,
            organization=self.organization,
            rendition_set=self.rendition_set,
            revision=2,
            status=OrganizationImageSelection.Status.ARCHIVED,
        )
        other_asset = self.create_asset(
            tenant=self.tenant,
            storage_key="assets/reassociation.jpeg",
            checksum="f" * 64,
        )
        other_set = self.create_rendition_set(
            tenant=self.tenant,
            asset=other_asset,
            render_hash="1" * 64,
        )
        other_renditions = self.create_complete_renditions(
            tenant=self.tenant,
            rendition_set=other_set,
            prefix="reassociation",
        )

        with self.assertRaises(ImmutableImageReleaseError):
            OrganizationImageRelease.objects.filter(pk=release.pk).update(
                selection=replacement_selection,
                rendition_set=other_set,
            )
        with self.assertRaises(ImmutableImageReleaseError):
            OrganizationImageReleaseRendition.objects.filter(pk=square_mapping.pk).update(
                rendition=other_renditions[0],
            )

        self.assertEqual(
            OrganizationImageRelease.objects.filter(pk=release.pk).values().get(),
            original_release,
        )
        self.assertEqual(
            OrganizationImageReleaseRendition.objects.filter(pk=square_mapping.pk)
            .values()
            .get(),
            original_mapping,
        )

    def test_later_selection_and_rendition_changes_do_not_reassociate_release_history(self):
        result = self.create_release()
        release = result.release
        square_mapping = next(
            mapping for mapping in result.renditions if mapping.variant == "square"
        )
        original_release = OrganizationImageRelease.objects.filter(pk=release.pk).values().get()
        original_mapping = (
            OrganizationImageReleaseRendition.objects.filter(pk=square_mapping.pk)
            .values()
            .get()
        )
        other_organization = Organization.objects.create(
            tenant=self.tenant,
            name="Later selection organization",
        )
        other_asset = self.create_asset(
            tenant=self.tenant,
            storage_key="assets/later-selection.jpeg",
            checksum="f" * 64,
        )
        other_set = self.create_rendition_set(
            tenant=self.tenant,
            asset=other_asset,
            render_hash="1" * 64,
        )

        OrganizationImageSelection.objects.filter(pk=self.selection.pk).update(
            organization=other_organization,
            rendition_set=other_set,
            status=OrganizationImageSelection.Status.ARCHIVED,
        )
        ImageRendition.objects.filter(pk=square_mapping.rendition_id).update(
            rendition_set=other_set,
            artifact_storage_key="renditions/later-square.webp",
            checksum_sha256="2" * 64,
        )

        self.assertEqual(
            OrganizationImageRelease.objects.filter(pk=release.pk).values().get(),
            original_release,
        )
        self.assertEqual(
            OrganizationImageReleaseRendition.objects.filter(pk=square_mapping.pk)
            .values()
            .get(),
            original_mapping,
        )
        self.assertEqual(release.organization_id, self.organization.pk)
        self.assertEqual(release.rendition_set_id, self.rendition_set.pk)
        self.assertEqual(
            square_mapping.artifact_storage_key_snapshot,
            "renditions/release-square.webp",
        )
        self.assertEqual(square_mapping.artifact_checksum_sha256_snapshot, "c" * 64)

    def test_referenced_history_is_protected_from_delete(self):
        result = self.create_release()

        for instance in (
            self.tenant,
            self.organization,
            self.selection,
            self.rendition_set,
            result.renditions[0].rendition,
        ):
            with self.subTest(model=instance.__class__.__name__):
                with self.assertRaises(ProtectedError):
                    instance.delete()

    def test_database_enforces_release_id_and_public_key_uniqueness(self):
        first = self.create_release()
        second = self.create_release()
        first_mapping = first.renditions[0]
        second_mapping = second.renditions[0]

        with self.assertRaises(IntegrityError):
            with transaction.atomic(), connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE crm_organizationimagerelease SET release_id = %s WHERE id = %s",
                    [str(first.release.release_id), second.release.pk],
                )
        with self.assertRaises(IntegrityError):
            with transaction.atomic(), connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE crm_organizationimagereleaserendition "
                    "SET public_storage_key = %s WHERE id = %s",
                    [first_mapping.public_storage_key, second_mapping.pk],
                )

    def test_database_enforces_release_variant_and_rendition_uniqueness(self):
        result = self.create_release()
        square = next(mapping for mapping in result.renditions if mapping.variant == "square")
        landscape = next(
            mapping for mapping in result.renditions if mapping.variant == "landscape"
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic(), connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE crm_organizationimagereleaserendition "
                    "SET variant = %s WHERE id = %s",
                    [square.variant, landscape.pk],
                )
        with self.assertRaises(IntegrityError):
            with transaction.atomic(), connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE crm_organizationimagereleaserendition "
                    "SET rendition_id = %s WHERE id = %s",
                    [square.rendition_id, landscape.pk],
                )

    def test_database_enforces_valid_nonempty_mapping_fields(self):
        result = self.create_release()
        mapping = result.renditions[0]
        invalid_updates = (
            ("variant", "portrait"),
            ("output_format", "gif"),
            ("artifact_storage_key_snapshot", ""),
            ("artifact_checksum_sha256_snapshot", ""),
            ("public_storage_key", ""),
        )

        for field_name, value in invalid_updates:
            with self.subTest(field_name=field_name):
                with self.assertRaises(IntegrityError):
                    with transaction.atomic(), connection.cursor() as cursor:
                        cursor.execute(
                            f"UPDATE crm_organizationimagereleaserendition "
                            f"SET {field_name} = %s WHERE id = %s",
                            [value, mapping.pk],
                        )

    def test_models_are_typed_and_have_no_file_or_publication_fields(self):
        release_fields = {field.name for field in OrganizationImageRelease._meta.fields}
        mapping_fields = {
            field.name for field in OrganizationImageReleaseRendition._meta.fields
        }

        self.assertTrue(
            {"tenant", "organization", "selection", "rendition_set"}.issubset(
                release_fields
            )
        )
        self.assertTrue({"release", "rendition"}.issubset(mapping_fields))
        self.assertFalse(
            {"content_type", "object_id", "is_published", "publish_phone"}
            & (release_fields | mapping_fields)
        )
        self.assertFalse(
            any(
                field.get_internal_type() == "FileField"
                for field in (
                    *OrganizationImageRelease._meta.fields,
                    *OrganizationImageReleaseRendition._meta.fields,
                )
            )
        )


class OrganizationImageReleaseMigrationTests(TransactionTestCase):
    migrate_from = ("crm", "0025_restore_archived_image_selection")
    migrate_to = ("crm", "0026_organization_image_release_domain")

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_migration_is_additive_preserves_existing_data_and_is_reversible(self):
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        old_apps = executor.loader.project_state([self.migrate_from]).apps
        OldTenant = old_apps.get_model("crm", "Tenant")
        OldOrganization = old_apps.get_model("crm", "Organization")
        OldAsset = old_apps.get_model("crm", "ImageAsset")
        OldRenditionSet = old_apps.get_model("crm", "ImageRenditionSet")
        OldRendition = old_apps.get_model("crm", "ImageRendition")
        OldSelection = old_apps.get_model("crm", "OrganizationImageSelection")
        OldUser = old_apps.get_model("auth", "User")

        tenant = OldTenant.objects.create(name="Release migration", slug="release-migration")
        organization = OldOrganization.objects.create(
            tenant=tenant,
            name="Existing release organization",
        )
        user = OldUser.objects.create(username="release-migration-user")
        asset = OldAsset.objects.create(
            tenant=tenant,
            private_storage_key="assets/migration.jpeg",
            checksum_sha256="a" * 64,
            original_format="jpeg",
            mime_type="image/jpeg",
            width=1600,
            height=900,
            file_size_bytes=123456,
            validation_version="validation-v1",
        )
        rendition_set = OldRenditionSet.objects.create(
            tenant=tenant,
            asset=asset,
            fit_mode="cover",
            processing_version="processing-v1",
            render_config_hash_sha256="b" * 64,
        )
        rendition = OldRendition.objects.create(
            tenant=tenant,
            rendition_set=rendition_set,
            variant="square",
            output_format="webp",
            width=512,
            height=512,
            file_size_bytes=45678,
            checksum_sha256="c" * 64,
            artifact_storage_key="renditions/migration-square.webp",
        )
        selection = OldSelection.objects.create(
            tenant=tenant,
            organization=organization,
            selection_kind="asset",
            rendition_set=rendition_set,
            alt_text="Migration image",
            public_credit="",
            revision=1,
            status="active",
            locked_by=user,
            locked_at=timezone.now(),
        )
        snapshots = {
            "Tenant": OldTenant.objects.filter(pk=tenant.pk).values().get(),
            "Organization": OldOrganization.objects.filter(pk=organization.pk).values().get(),
            "ImageAsset": OldAsset.objects.filter(pk=asset.pk).values().get(),
            "ImageRenditionSet": OldRenditionSet.objects.filter(pk=rendition_set.pk).values().get(),
            "ImageRendition": OldRendition.objects.filter(pk=rendition.pk).values().get(),
            "OrganizationImageSelection": OldSelection.objects.filter(pk=selection.pk).values().get(),
        }

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        new_apps = executor.loader.project_state([self.migrate_to]).apps
        ids = {
            "Tenant": tenant.pk,
            "Organization": organization.pk,
            "ImageAsset": asset.pk,
            "ImageRenditionSet": rendition_set.pk,
            "ImageRendition": rendition.pk,
            "OrganizationImageSelection": selection.pk,
        }
        for model_name, expected in snapshots.items():
            with self.subTest(model_name=model_name):
                actual = (
                    new_apps.get_model("crm", model_name)
                    .objects.filter(pk=ids[model_name])
                    .values()
                    .get()
                )
                self.assertEqual(actual, expected)
        self.assertEqual(
            new_apps.get_model("crm", "OrganizationImageRelease").objects.count(),
            0,
        )
        self.assertEqual(
            new_apps.get_model(
                "crm",
                "OrganizationImageReleaseRendition",
            ).objects.count(),
            0,
        )

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        restored_apps = executor.loader.project_state([self.migrate_from]).apps
        self.assertTrue(
            restored_apps.get_model("crm", "OrganizationImageSelection")
            .objects.filter(pk=selection.pk)
            .exists()
        )
        with self.assertRaises(LookupError):
            restored_apps.get_model("crm", "OrganizationImageRelease")
