from hashlib import sha256
from io import BytesIO
from pathlib import Path
import tempfile
import uuid
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from PIL import Image

from image_safety.release_keys import build_public_release_key

from .services.images.materialization import (
    ImageMaterializationConflict,
    ImageMaterializationError,
    MaterializationInput,
    materialize_release,
)


def image_bytes(output_format: str, size: tuple[int, int], color: str) -> bytes:
    destination = BytesIO()
    Image.new("RGB", size, color).save(destination, format=output_format.upper())
    return destination.getvalue()


class PublicImageMaterializationTests(SimpleTestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        root = Path(self.temporary.name).resolve()
        self.artifact_root = root / "artifacts"
        self.delivery_root = root / "delivery"
        self.artifact_root.mkdir()
        self.release_id = str(uuid.uuid4())
        self.items = []
        for index, variant in enumerate(("square", "landscape", "share"), start=1):
            size = (index + 3, index + 4)
            data = image_bytes("png", size, "red")
            key = f"tenants/1/{variant}.png"
            source = self.artifact_root / key
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_bytes(data)
            self.items.append(
                MaterializationInput(
                    release_id=self.release_id,
                    variant=variant,
                    output_format="png",
                    width=size[0],
                    height=size[1],
                    file_size_bytes=len(data),
                    artifact_storage_key=key,
                    checksum_sha256=sha256(data).hexdigest(),
                    public_storage_key=build_public_release_key(
                        self.release_id, variant, "png"
                    ),
                )
            )
        self.settings = override_settings(
            IMAGE_ASSET_FEATURE_ENABLED=True,
            PUBLIC_IMAGE_RELEASE_MATERIALIZATION_ENABLED=True,
            PUBLIC_IMAGE_DELIVERY_ROOT=self.delivery_root,
            STORAGES={
                "default": {
                    "BACKEND": "django.core.files.storage.FileSystemStorage"
                },
                "staticfiles": {
                    "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
                },
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
        self.settings.enable()
        self.addCleanup(self.settings.disable)

    def destination(self, item):
        return self.delivery_root / item.public_storage_key

    def test_create_only_materialization_and_identical_retry(self):
        created = materialize_release(tuple(self.items))
        retried = materialize_release(tuple(self.items))

        self.assertEqual([item.created for item in created], [True, True, True])
        self.assertEqual([item.created for item in retried], [False, False, False])
        for item in self.items:
            self.assertEqual(
                sha256(self.destination(item).read_bytes()).hexdigest(),
                item.checksum_sha256,
            )

    def test_existing_different_bytes_are_never_overwritten(self):
        item = self.items[0]
        destination = self.destination(item)
        destination.parent.mkdir(parents=True)
        conflicting = image_bytes("png", (item.width, item.height), "blue")
        destination.write_bytes(conflicting)

        with self.assertRaises(ImageMaterializationConflict):
            materialize_release(tuple(self.items))

        self.assertEqual(destination.read_bytes(), conflicting)

    def test_partial_set_is_completed_without_replacing_existing_file(self):
        first = self.items[0]
        destination = self.destination(first)
        destination.parent.mkdir(parents=True)
        destination.write_bytes((self.artifact_root / first.artifact_storage_key).read_bytes())

        result = materialize_release(tuple(self.items))

        self.assertEqual([item.created for item in result], [False, True, True])

    def test_source_checksum_format_and_dimension_mismatch_fail_closed(self):
        cases = (
            {"checksum_sha256": "0" * 64},
            {"output_format": "jpeg", "public_storage_key": build_public_release_key(self.release_id, "square", "jpeg")},
            {"width": self.items[0].width + 1},
        )
        for changes in cases:
            with self.subTest(changes=changes):
                item = MaterializationInput(**{**self.items[0].__dict__, **changes})
                with self.assertRaises(ImageMaterializationConflict):
                    materialize_release((item, *self.items[1:]))
                self.assertFalse(self.destination(item).exists())

    def test_symlink_delivery_component_is_rejected(self):
        outside = Path(self.temporary.name) / "outside"
        outside.mkdir()
        self.delivery_root.symlink_to(outside, target_is_directory=True)

        with self.assertRaises(ImageMaterializationError):
            materialize_release(tuple(self.items))

        self.assertEqual(list(outside.iterdir()), [])

    def test_noncanonical_destination_is_rejected(self):
        invalid = MaterializationInput(
            **{**self.items[0].__dict__, "public_storage_key": "releases/other.png"}
        )

        with self.assertRaises(ImageMaterializationError):
            materialize_release((invalid, *self.items[1:]))

    def test_incomplete_variant_identity_and_filesystem_root_are_rejected(self):
        duplicate = MaterializationInput(
            **{
                **self.items[2].__dict__,
                "variant": "square",
                "public_storage_key": self.items[0].public_storage_key,
            }
        )
        with self.assertRaisesRegex(ImageMaterializationError, "square"):
            materialize_release((self.items[0], self.items[1], duplicate))

        with override_settings(PUBLIC_IMAGE_DELIVERY_ROOT=Path("/")):
            with self.assertRaisesRegex(ImageMaterializationError, "safe absolute"):
                materialize_release(tuple(self.items))

    def test_complete_set_is_read_back_again_before_success(self):
        from .services.images import materialization

        original = materialization._materialize_one
        count = 0

        def corrupt_after_last(item, data):
            nonlocal count
            result = original(item, data)
            count += 1
            if count == 3:
                self.destination(self.items[0]).write_bytes(b"changed after first read")
            return result

        with patch.object(
            materialization, "_materialize_one", side_effect=corrupt_after_last
        ):
            with self.assertRaises(ImageMaterializationConflict):
                materialize_release(tuple(self.items))
