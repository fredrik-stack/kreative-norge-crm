from __future__ import annotations

from hashlib import sha256
from io import BytesIO
from pathlib import Path
import inspect
import struct
import tempfile
from unittest.mock import patch
import zlib

from django.core.files.storage import storages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import TestCase, override_settings
from PIL import Image, ImageCms

from crm.models import (
    ImageAsset,
    ImageRendition,
    ImageRenditionSet,
    OrganizationImageRelease,
    Tenant,
)
from crm.services.images.ingest import (
    ImageIngestConflictError,
    ImageIngestFeatureDisabledError,
    UnsupportedImageProcessingProfileError,
    ingest_uploaded_image,
)
from crm.services.images.processing import (
    MAX_SOURCE_BYTES,
    ImageProcessingError,
    process_uploaded_image,
)
from crm.services.images.storage import (
    ImageStorageFeatureDisabledError,
    ImmutableImageStorageConflict,
    _save_immutable,
)


def image_bytes(
    image_format: str = "JPEG",
    *,
    size: tuple[int, int] = (1400, 1000),
    mode: str = "RGB",
    icc_profile: bytes | None = None,
    exif_orientation: int | None = None,
) -> bytes:
    color = (220, 30, 40, 180) if mode == "RGBA" else (220, 30, 40)
    image = Image.new(mode, size, color)
    # The asymmetric marks make focus and EXIF tests sensitive to geometry.
    for x in range(min(300, image.width)):
        for y in range(min(200, image.height)):
            image.putpixel((x, y), (20, 70, 220, 255) if mode == "RGBA" else (20, 70, 220))
    options: dict[str, object] = {}
    if icc_profile is not None:
        options["icc_profile"] = icc_profile
    if exif_orientation is not None:
        exif = Image.Exif()
        exif[274] = exif_orientation
        exif[315] = "metadata that must not reach renditions"
        options["exif"] = exif
    buffer = BytesIO()
    image.save(buffer, image_format, **options)
    return buffer.getvalue()


def upload(data: bytes, *, name: str = "source.jpg", content_type: str = "image/jpeg"):
    return SimpleUploadedFile(name, data, content_type=content_type)


def declared_png(width: int, height: int) -> bytes:
    def chunk(kind: bytes, payload: bytes) -> bytes:
        body = kind + payload
        return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IEND", b"")


class ImageProcessingAdapterTests(TestCase):
    def test_accepts_static_jpeg_png_and_webp_from_actual_bytes(self):
        cases = (
            ("JPEG", "image/jpeg", "photo.bin"),
            ("PNG", "image/png", "photo.bin"),
            ("WEBP", "image/webp", "photo.bin"),
        )
        for image_format, mime_type, name in cases:
            with self.subTest(image_format=image_format):
                processed = process_uploaded_image(
                    upload(image_bytes(image_format), name=name, content_type=mime_type),
                    fit_mode="cover",
                )
                self.assertEqual(processed.source.original_format, image_format.lower())
                self.assertEqual(processed.source.mime_type, mime_type)

    def test_declared_mime_must_match_actual_bytes(self):
        with self.assertRaisesRegex(ImageProcessingError, "does not match") as context:
            process_uploaded_image(
                upload(image_bytes("PNG"), content_type="image/jpeg"),
                fit_mode="contain",
            )
        self.assertEqual(context.exception.code, "mime_mismatch")

    def test_bounded_reader_rejects_source_over_15_mib(self):
        data = b"\xff\xd8\xff" + b"x" * (MAX_SOURCE_BYTES - 2)
        with self.assertRaises(ImageProcessingError) as context:
            process_uploaded_image(upload(data), fit_mode="cover")
        self.assertEqual(context.exception.code, "file_too_large")

    def test_declared_dimensions_over_36_megapixels_are_rejected_before_load(self):
        with self.assertRaises(ImageProcessingError) as context:
            process_uploaded_image(
                upload(declared_png(6001, 6000), name="large.png", content_type="image/png"),
                fit_mode="contain",
            )
        self.assertEqual(context.exception.code, "pixel_limit")

    def test_unknown_corrupt_and_truncated_sources_are_controlled_errors(self):
        cases = (
            (b"not an image", "image/jpeg", "unsupported_format"),
            (image_bytes("JPEG")[:100], "image/jpeg", "decode_failed"),
            (b"\x89PNG\r\n\x1a\ncorrupt", "image/png", "decode_failed"),
        )
        for data, content_type, code in cases:
            with self.subTest(code=code):
                with self.assertRaises(ImageProcessingError) as context:
                    process_uploaded_image(upload(data, content_type=content_type), fit_mode="cover")
                self.assertEqual(context.exception.code, code)

    def test_animated_webp_is_rejected_instead_of_using_first_frame(self):
        first = Image.new("RGB", (32, 32), "red")
        second = Image.new("RGB", (32, 32), "blue")
        buffer = BytesIO()
        first.save(buffer, "WEBP", save_all=True, append_images=[second], duration=100, loop=0)
        with self.assertRaises(ImageProcessingError) as context:
            process_uploaded_image(
                upload(buffer.getvalue(), name="animated.webp", content_type="image/webp"),
                fit_mode="contain",
            )
        self.assertEqual(context.exception.code, "animated_not_supported")

    def test_cover_focus_defaults_to_center_and_validates_partial_or_out_of_range(self):
        data = image_bytes("JPEG")
        centered = process_uploaded_image(upload(data), fit_mode="cover")
        explicit = process_uploaded_image(upload(data), fit_mode="cover", focus_x=0.5, focus_y=0.5)
        shifted = process_uploaded_image(upload(data), fit_mode="cover", focus_x=0.9, focus_y=0.5)
        self.assertEqual((centered.focus_x, centered.focus_y), (0.5, 0.5))
        self.assertEqual(
            [item.checksum_sha256 for item in centered.renditions],
            [item.checksum_sha256 for item in explicit.renditions],
        )
        self.assertNotEqual(centered.renditions[0].checksum_sha256, shifted.renditions[0].checksum_sha256)
        for focus_x, focus_y in ((0.5, None), (None, 0.5), (-0.1, 0.5), (0.5, 1.1)):
            with self.subTest(focus_x=focus_x, focus_y=focus_y):
                with self.assertRaises(ImageProcessingError) as context:
                    process_uploaded_image(upload(data), fit_mode="cover", focus_x=focus_x, focus_y=focus_y)
                self.assertEqual(context.exception.code, "invalid_focus")

    def test_contain_does_not_depend_on_focus_and_never_upscales_content(self):
        data = image_bytes("PNG", size=(40, 20), mode="RGBA")
        default = process_uploaded_image(
            upload(data, name="logo.png", content_type="image/png"),
            fit_mode="contain",
        )
        supplied = process_uploaded_image(
            upload(data, name="logo.png", content_type="image/png"),
            fit_mode="contain",
            focus_x=0.1,
            focus_y=0.9,
        )
        self.assertEqual(
            [item.checksum_sha256 for item in default.renditions],
            [item.checksum_sha256 for item in supplied.renditions],
        )
        self.assertIn("focus_ignored_for_contain", supplied.source.warnings)
        with Image.open(BytesIO(default.renditions[0].encoded_bytes)) as rendered:
            alpha_box = rendered.convert("RGBA").getchannel("A").getbbox()
        self.assertEqual((alpha_box[2] - alpha_box[0], alpha_box[3] - alpha_box[1]), (40, 20))

    def test_cover_rejects_any_missing_mandatory_rendition_due_to_upscale(self):
        with self.assertRaises(ImageProcessingError) as context:
            process_uploaded_image(
                upload(image_bytes("JPEG", size=(300, 300))),
                fit_mode="cover",
            )
        self.assertEqual(context.exception.code, "upscale_required")

    def test_exif_orientation_is_applied_before_rendering(self):
        oriented = process_uploaded_image(
            upload(image_bytes("JPEG", size=(1000, 1400), exif_orientation=6)),
            fit_mode="cover",
        )
        physically_rotated_image = Image.open(BytesIO(image_bytes("JPEG", size=(1000, 1400))))
        physically_rotated_image = physically_rotated_image.transpose(Image.Transpose.ROTATE_270)
        buffer = BytesIO()
        physically_rotated_image.save(buffer, "JPEG")
        rotated = process_uploaded_image(upload(buffer.getvalue()), fit_mode="cover")
        self.assertEqual(oriented.renditions[0].width, rotated.renditions[0].width)
        with Image.open(BytesIO(oriented.renditions[0].encoded_bytes)) as first:
            with Image.open(BytesIO(rotated.renditions[0].encoded_bytes)) as second:
                self.assertEqual(first.size, second.size)
                self.assertLessEqual(
                    sum(
                        abs(a - b)
                        for a, b in zip(
                            first.convert("RGB").getpixel((256, 256)),
                            second.convert("RGB").getpixel((256, 256)),
                        )
                    ),
                    30,
                )

    def test_srgb_untagged_and_non_srgb_paths_are_explicit(self):
        profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
        embedded = process_uploaded_image(
            upload(image_bytes("JPEG", icc_profile=profile)),
            fit_mode="cover",
        )
        untagged = process_uploaded_image(upload(image_bytes("JPEG")), fit_mode="cover")
        with patch("crm.services.images.processing.ImageCms.getProfileName", return_value="Adobe RGB"):
            with patch("crm.services.images.processing.ImageCms.getProfileDescription", return_value="wide gamut"):
                non_srgb = process_uploaded_image(
                    upload(image_bytes("JPEG", icc_profile=profile)),
                    fit_mode="cover",
                )
        self.assertEqual(embedded.source.color_status, "embedded_srgb")
        self.assertEqual(untagged.source.color_status, "untagged_assumed_srgb")
        self.assertIn("untagged_assumed_srgb", untagged.source.warnings)
        self.assertEqual(non_srgb.source.color_status, "embedded_non_srgb")

    def test_corrupt_icc_profile_is_rejected(self):
        with self.assertRaises(ImageProcessingError) as context:
            process_uploaded_image(
                upload(image_bytes("PNG", icc_profile=b"not-an-icc"), name="bad.png", content_type="image/png"),
                fit_mode="contain",
            )
        self.assertEqual(context.exception.code, "corrupt_icc_profile")

    def test_rendition_contract_dimensions_formats_and_metadata(self):
        processed = process_uploaded_image(
            upload(image_bytes("JPEG", exif_orientation=1)),
            fit_mode="cover",
        )
        expected = {
            "square": ((512, 512), "WEBP"),
            "landscape": ((800, 450), "WEBP"),
            "share": ((1200, 630), "JPEG"),
        }
        for rendition in processed.renditions:
            with self.subTest(variant=rendition.variant):
                with Image.open(BytesIO(rendition.encoded_bytes)) as rendered:
                    rendered.load()
                    self.assertEqual((rendered.size, rendered.format), expected[rendition.variant])
                    self.assertFalse({"exif", "icc_profile", "comment", "xmp"} & set(rendered.info))
                    if rendition.variant == "share":
                        self.assertNotIn("progressive", rendered.info)

    def test_contain_outputs_are_profile_free_png_with_alpha(self):
        processed = process_uploaded_image(
            upload(image_bytes("PNG", size=(900, 600), mode="RGBA"), name="logo.png", content_type="image/png"),
            fit_mode="contain",
        )
        for rendition in processed.renditions:
            with Image.open(BytesIO(rendition.encoded_bytes)) as rendered:
                self.assertEqual(rendered.format, "PNG")
                self.assertIn("A", rendered.getbands())
                self.assertNotIn("icc_profile", rendered.info)

        profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
        palette_image = Image.new("P", (100, 100), 0)
        palette_image.putpalette([0, 0, 0, 255, 0, 0] + [0, 0, 0] * 254)
        for x in range(40, 60):
            for y in range(40, 60):
                palette_image.putpixel((x, y), 1)
        palette_buffer = BytesIO()
        palette_image.save(
            palette_buffer,
            "PNG",
            transparency=0,
            icc_profile=profile,
        )
        palette_processed = process_uploaded_image(
            upload(
                palette_buffer.getvalue(),
                name="palette-logo.png",
                content_type="image/png",
            ),
            fit_mode="contain",
        )
        with Image.open(BytesIO(palette_processed.renditions[0].encoded_bytes)) as rendered:
            rendered_rgba = rendered.convert("RGBA")
            alpha_box = rendered_rgba.getchannel("A").getbbox()
            self.assertEqual(rendered.format, "PNG")
            self.assertEqual(rendered_rgba.getpixel((210, 210))[3], 0)
            self.assertEqual(rendered_rgba.getpixel((256, 256))[3], 255)
            self.assertEqual(
                (alpha_box[2] - alpha_box[0], alpha_box[3] - alpha_box[1]),
                (20, 20),
            )


@override_settings(IMAGE_ASSET_FEATURE_ENABLED=True)
class ImageIngestServiceTests(TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        root = Path(self.temporary_directory.name)
        self.private_root = root / "private"
        self.artifact_root = root / "artifacts"
        self.storage_override = override_settings(
            STORAGES={
                "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
                "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
                "image_originals_private": {
                    "BACKEND": "django.core.files.storage.FileSystemStorage",
                    "OPTIONS": {"location": self.private_root, "base_url": None},
                },
                "image_renditions_public": {
                    "BACKEND": "django.core.files.storage.FileSystemStorage",
                    "OPTIONS": {"location": self.artifact_root, "base_url": None},
                },
            }
        )
        self.storage_override.enable()
        self.tenant = Tenant.objects.create(name="Image tenant", slug="image-tenant")

    def tearDown(self):
        self.storage_override.disable()
        self.temporary_directory.cleanup()

    def ingest(self, data: bytes | None = None, **kwargs):
        data = data or image_bytes("JPEG")
        return ingest_uploaded_image(
            tenant=self.tenant,
            upload=upload(data),
            content_mode="cover",
            **kwargs,
        )

    def test_service_creates_complete_aggregate_and_preserves_original_bytes(self):
        source = image_bytes("JPEG", size=(1000, 1400), exif_orientation=6)
        result = self.ingest(source)
        self.assertTrue(result.aggregate_created)
        self.assertEqual(ImageAsset.objects.count(), 1)
        self.assertEqual(ImageRenditionSet.objects.count(), 1)
        self.assertEqual(ImageRendition.objects.count(), 3)
        self.assertEqual([item.variant for item in result.renditions], ["square", "landscape", "share"])
        self.assertEqual(result.status, "created")
        self.assertEqual(result.asset_id, result.asset.pk)
        self.assertEqual(result.rendition_set_id, result.rendition_set.pk)
        self.assertEqual(result.rendition_ids, tuple(item.pk for item in result.renditions))
        self.assertEqual(OrganizationImageRelease.objects.count(), 0)
        self.assertEqual((result.asset.width, result.asset.height), (1400, 1000))
        self.assertEqual(
            [(item.width, item.height) for item in result.renditions],
            [(512, 512), (800, 450), (1200, 630)],
        )
        with storages["image_originals_private"].open(result.asset.private_storage_key, "rb") as stored:
            self.assertEqual(stored.read(), source)
        self.assertEqual(result.asset.checksum_sha256, sha256(source).hexdigest())
        for rendition in result.renditions:
            with storages["image_renditions_public"].open(rendition.artifact_storage_key, "rb") as stored:
                stored_bytes = stored.read()
            self.assertEqual(rendition.checksum_sha256, sha256(stored_bytes).hexdigest())

    def test_keys_are_internal_tenant_scoped_and_not_caller_parameters(self):
        parameters = set(inspect.signature(ingest_uploaded_image).parameters)
        self.assertFalse(
            parameters
            & {
                "storage_key",
                "private_storage_key",
                "artifact_storage_key",
                "checksum",
                "release_id",
                "public_storage_key",
            }
        )
        source = image_bytes("JPEG")
        first = self.ingest(source)
        other = Tenant.objects.create(name="Other tenant", slug="other-tenant")
        second = ingest_uploaded_image(
            tenant=other,
            upload=upload(source),
            content_mode="cover",
        )
        self.assertNotEqual(first.asset.private_storage_key, second.asset.private_storage_key)
        self.assertIn(f"tenants/{self.tenant.pk}/", first.asset.private_storage_key)
        self.assertIn(f"tenants/{other.pk}/", second.asset.private_storage_key)
        for first_rendition, second_rendition in zip(first.renditions, second.renditions):
            self.assertEqual(first_rendition.variant, second_rendition.variant)
            self.assertEqual(first_rendition.checksum_sha256, second_rendition.checksum_sha256)
            self.assertNotEqual(
                first_rendition.artifact_storage_key,
                second_rendition.artifact_storage_key,
            )
        self.assertFalse(any(item.artifact_storage_key.startswith("releases/") for item in first.renditions))

    def test_identical_retry_reuses_storage_and_complete_database_aggregate(self):
        source = image_bytes("JPEG")
        first = self.ingest(source)
        second = self.ingest(source)
        self.assertTrue(first.aggregate_created)
        self.assertFalse(second.aggregate_created)
        self.assertEqual(second.status, "reused")
        self.assertFalse(second.original_storage_created)
        self.assertEqual(second.artifact_storage_created, (False, False, False))
        self.assertEqual(first.asset.pk, second.asset.pk)
        self.assertEqual(first.rendition_set.pk, second.rendition_set.pk)
        self.assertEqual([item.pk for item in first.renditions], [item.pk for item in second.renditions])

    def test_existing_storage_key_with_different_bytes_fails_closed(self):
        result = self.ingest()
        key = result.renditions[0].artifact_storage_key
        path = self.artifact_root / key
        path.write_bytes(b"conflicting bytes")
        with self.assertRaises(ImmutableImageStorageConflict):
            self.ingest()

    def test_partial_or_mismatched_existing_aggregate_fails_closed(self):
        for mutation in ("partial", "mismatch"):
            with self.subTest(mutation=mutation):
                result = self.ingest()
                if mutation == "partial":
                    result.renditions[0].delete()
                else:
                    ImageRendition.objects.filter(pk=result.renditions[0].pk).update(
                        checksum_sha256="f" * 64
                    )
                with self.assertRaises(ImageIngestConflictError):
                    self.ingest()
                ImageRendition.objects.all().delete()
                ImageRenditionSet.objects.all().delete()
                ImageAsset.objects.all().delete()

    def test_storage_failure_at_each_write_position_never_creates_database_rows(self):
        real_save = _save_immutable
        for failure_position in range(1, 5):
            with self.subTest(failure_position=failure_position):
                calls = 0

                def failing_save(**kwargs):
                    nonlocal calls
                    calls += 1
                    if calls == failure_position:
                        raise OSError("simulated storage failure")
                    return real_save(**kwargs)

                with patch("crm.services.images.ingest._save_immutable", side_effect=failing_save):
                    with self.assertRaises(OSError):
                        self.ingest()
                self.assertEqual(ImageAsset.objects.count(), 0)
                self.assertEqual(ImageRenditionSet.objects.count(), 0)
                self.assertEqual(ImageRendition.objects.count(), 0)

        corrupting_storage = ExactKeyCorruptingStorage()
        with patch(
            "crm.services.images.storage.storages",
            {
                "image_originals_private": corrupting_storage,
                "image_renditions_public": corrupting_storage,
            },
        ):
            with self.assertRaises(ImmutableImageStorageConflict):
                self.ingest()
        self.assertEqual(len(corrupting_storage.saved), 1)
        self.assertEqual(ImageAsset.objects.count(), 0)
        self.assertEqual(ImageRenditionSet.objects.count(), 0)
        self.assertEqual(ImageRendition.objects.count(), 0)

    def test_database_failure_after_storage_leaves_reusable_unserved_orphans(self):
        source = image_bytes("JPEG")
        with patch(
            "crm.services.images.ingest._create_or_reuse_database_aggregate",
            side_effect=ImageIngestConflictError("simulated database failure"),
        ):
            with self.assertRaises(ImageIngestConflictError):
                self.ingest(source)
        self.assertEqual(ImageAsset.objects.count(), 0)
        self.assertTrue(any(self.private_root.rglob("*.*")))
        self.assertEqual(len(list(self.artifact_root.rglob("*.*"))), 3)
        retry = self.ingest(source)
        self.assertTrue(retry.aggregate_created)
        self.assertFalse(retry.original_storage_created)
        self.assertEqual(retry.artifact_storage_created, (False, False, False))

    def test_database_insert_failure_rolls_back_the_entire_aggregate(self):
        with patch.object(ImageRendition.objects, "bulk_create", side_effect=IntegrityError("simulated")):
            with self.assertRaises(ImageIngestConflictError):
                self.ingest()
        self.assertEqual(ImageAsset.objects.count(), 0)
        self.assertEqual(ImageRenditionSet.objects.count(), 0)
        self.assertEqual(ImageRendition.objects.count(), 0)
        self.assertTrue(any(self.private_root.rglob("*.*")))
        self.assertEqual(len(list(self.artifact_root.rglob("*.*"))), 3)

    def test_unsupported_processing_profile_and_icc_transform_failure_precede_writes(self):
        with self.assertRaises(UnsupportedImageProcessingProfileError):
            self.ingest(processing_profile="caller-profile")
        self.assertFalse(self.private_root.exists())
        self.assertFalse(self.artifact_root.exists())

        profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
        cmyk_image = Image.new("CMYK", (1400, 1000), (0, 255, 255, 0))
        cmyk_buffer = BytesIO()
        cmyk_image.save(cmyk_buffer, "JPEG", icc_profile=profile)
        with self.assertRaises(ImageProcessingError) as context:
            self.ingest(cmyk_buffer.getvalue())
        self.assertEqual(context.exception.code, "icc_conversion_failed")
        self.assertEqual(ImageAsset.objects.count(), 0)
        self.assertEqual(ImageRenditionSet.objects.count(), 0)
        self.assertEqual(ImageRendition.objects.count(), 0)
        self.assertFalse(self.private_root.exists())
        self.assertFalse(self.artifact_root.exists())

    @override_settings(IMAGE_ASSET_FEATURE_ENABLED=False)
    def test_feature_flag_off_blocks_service_before_processing_or_storage(self):
        with self.assertRaises(ImageIngestFeatureDisabledError):
            self.ingest()
        self.assertEqual(ImageAsset.objects.count(), 0)
        self.assertFalse(self.private_root.exists())
        self.assertFalse(self.artifact_root.exists())


class RenameOnCollisionStorage:
    def __init__(self):
        self.saved: dict[str, bytes] = {}
        self.deleted: list[str] = []

    def exists(self, key):
        return False

    def save(self, key, content):
        renamed = key.replace(".webp", "_renamed.webp")
        self.saved[renamed] = content.read()
        return renamed

    def delete(self, key):
        self.deleted.append(key)
        self.saved.pop(key, None)


class ExactKeyCorruptingStorage:
    def __init__(self):
        self.saved: dict[str, bytes] = {}

    def exists(self, key):
        return False

    def save(self, key, content):
        self.saved[key] = content.read() + b"corrupt"
        return key

    def open(self, key, mode="rb"):
        return BytesIO(self.saved[key])


class ImmutableImageStorageTests(TestCase):
    @override_settings(IMAGE_ASSET_FEATURE_ENABLED=False)
    def test_private_storage_primitive_cannot_bypass_disabled_feature(self):
        with self.assertRaises(ImageStorageFeatureDisabledError):
            _save_immutable(
                alias="image_renditions_public",
                requested_key="tenants/1/artifacts/profile/hash/config/square-checksum.webp",
                data=b"artifact bytes",
                content_type="image/webp",
            )

    @override_settings(IMAGE_ASSET_FEATURE_ENABLED=True)
    def test_backend_collision_rename_is_rejected_and_never_accepted_as_identity(self):
        backend = RenameOnCollisionStorage()
        requested = "tenants/1/artifacts/profile/hash/config/square-checksum.webp"
        with patch("crm.services.images.storage.storages", {"image_renditions_public": backend}):
            with self.assertRaisesRegex(ImmutableImageStorageConflict, "exact requested key"):
                _save_immutable(
                    alias="image_renditions_public",
                    requested_key=requested,
                    data=b"artifact bytes",
                    content_type="image/webp",
                )
        self.assertEqual(backend.saved, {})
        self.assertEqual(backend.deleted, [requested.replace(".webp", "_renamed.webp")])
