from hashlib import sha256
from io import BytesIO
from pathlib import Path
import tempfile
import uuid
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, SimpleTestCase, TestCase, override_settings
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
    BridgeAuthorization,
    ImageSafetyBridgeUnavailable,
)
from .services.images.public_urls import (
    InvalidPublicMediaKey,
    build_public_media_url,
    validate_canonical_public_key,
)


class ServingBridge:
    authorization = None
    error = None
    calls = []

    def __init__(self, *, timeout):
        self.timeout = timeout

    @classmethod
    def reset(cls):
        cls.authorization = None
        cls.error = None
        cls.calls = []

    def authorize(self, **payload):
        type(self).calls.append((self.timeout, payload))
        if type(self).error is not None:
            raise type(self).error
        return type(self).authorization


@override_settings(
    IMAGE_ASSET_FEATURE_ENABLED=True,
    PUBLIC_IMAGE_RELEASE_MATERIALIZATION_ENABLED=True,
    PUBLIC_IMAGE_SERVING_ENABLED=True,
    PUBLIC_SITE_ORIGIN="https://staging.example.no",
    PUBLIC_MEDIA_ORIGIN="https://media.example.no",
)
class PublicImageServingTests(TestCase):
    def setUp(self):
        ServingBridge.reset()
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
            "crm.services.images.serving.ImageSafetyBridgeClient", ServingBridge
        )
        self.bridge_patch.start()
        self.addCleanup(self.bridge_patch.stop)

        user = get_user_model().objects.create_user(username="serving-user")
        self.tenant = Tenant.objects.create(name="Serving", slug="serving")
        self.organization = Organization.objects.create(
            tenant=self.tenant,
            name="Published serving organization",
            is_published=True,
        )
        asset = ImageAsset.objects.create(
            tenant=self.tenant,
            private_storage_key="assets/serving.jpg",
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
        specifications = (
            ("square", "webp", "WEBP", (8, 8)),
            ("landscape", "png", "PNG", (9, 6)),
            ("share", "jpeg", "JPEG", (12, 7)),
        )
        renditions = []
        for variant, output_format, pillow_format, size in specifications:
            buffer = BytesIO()
            Image.new("RGB", size, "green").save(buffer, pillow_format)
            data = buffer.getvalue()
            checksum = sha256(data).hexdigest()
            extension = "jpg" if output_format == "jpeg" else output_format
            key = (
                f"tenants/{self.tenant.pk}/artifacts/test-v1/"
                f"{'a' * 64}/{'b' * 64}/{variant}-{checksum}.{extension}"
            )
            rendition = ImageRendition.objects.create(
                tenant=self.tenant,
                rendition_set=rendition_set,
                variant=variant,
                output_format=output_format,
                width=size[0],
                height=size[1],
                file_size_bytes=len(data),
                checksum_sha256=checksum,
                artifact_storage_key=key,
            )
            renditions.append((rendition, data))
        self.selection = OrganizationImageSelection.objects.create(
            tenant=self.tenant,
            organization=self.organization,
            selection_kind="asset",
            rendition_set=rendition_set,
            alt_text="Serving image",
            public_credit="",
            revision=1,
            status="active",
            locked_by=user,
            locked_at=timezone.now(),
        )
        self.release_id = str(uuid.uuid4())
        self.release = OrganizationImageRelease.objects._insert_from_release_service(
            [
                OrganizationImageRelease(
                    release_id=self.release_id,
                    tenant=self.tenant,
                    organization=self.organization,
                    selection=self.selection,
                    selection_revision_snapshot=1,
                    rendition_set=rendition_set,
                    key_schema_version=1,
                )
            ]
        )[0]
        mappings = []
        for rendition, data in renditions:
            key = build_public_release_key(
                self.release_id, rendition.variant, rendition.output_format
            )
            mappings.append(
                OrganizationImageReleaseRendition(
                    release=self.release,
                    rendition=rendition,
                    variant=rendition.variant,
                    output_format=rendition.output_format,
                    artifact_storage_key_snapshot=rendition.artifact_storage_key,
                    artifact_checksum_sha256_snapshot=rendition.checksum_sha256,
                    public_storage_key=key,
                )
            )
            path = self.delivery_root / key
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        self.mappings = tuple(
            OrganizationImageReleaseRendition.objects._insert_from_release_service(
                mappings
            )
        )
        ServingBridge.authorization = BridgeAuthorization(
            authorized=True,
            category="authorized",
            release_id=self.release_id,
            variant="square",
            read_cursor=7,
        )

    def url(self, variant="square", extension="webp", release_id=None):
        return (
            f"/media/releases/{release_id or self.release_id}/"
            f"{variant}.{extension}"
        )

    def test_get_and_head_return_only_controlled_internal_redirect_metadata(self):
        for method in ("get", "head"):
            with self.subTest(method=method):
                response = getattr(self.client, method)(
                    self.url(),
                    HTTP_HOST="attacker.example",
                    HTTP_X_FORWARDED_HOST="attacker.example",
                    HTTP_X_FORWARDED_PROTO="http",
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.content, b"")
                self.assertEqual(response["Content-Type"], "image/webp")
                self.assertEqual(
                    response["X-Accel-Redirect"],
                    f"/_protected-public-image/releases/{self.release_id}/square.webp",
                )
                self.assertEqual(
                    response["Cache-Control"],
                    "private, max-age=60, must-revalidate",
                )
                self.assertEqual(response["X-Content-Type-Options"], "nosniff")
                serialized = repr(dict(response.items()))
                self.assertNotIn(str(self.delivery_root), serialized)
                self.assertNotIn("/srv/", serialized)

        self.assertEqual(len(ServingBridge.calls), 2)
        timeout, payload = ServingBridge.calls[0]
        self.assertEqual(timeout, 5.0)
        self.assertEqual(payload["tenant_id"], self.tenant.pk)
        self.assertEqual(payload["organization_id"], self.organization.pk)
        self.assertEqual(payload["release_id"], self.release_id)
        self.assertEqual(payload["variant"], "square")
        self.assertEqual(
            payload["public_storage_key"],
            f"releases/{self.release_id}/square.webp",
        )

    def test_only_get_and_head_are_allowed(self):
        csrf_client = Client(enforce_csrf_checks=True)
        for method in ("post", "put", "patch", "delete"):
            with self.subTest(method=method):
                response = getattr(csrf_client, method)(self.url())
                self.assertEqual(response.status_code, 405)
                self.assertEqual(response.content, b"")
                self.assertEqual(response["Cache-Control"], "no-store")
                self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertEqual(ServingBridge.calls, [])

    def test_serving_events_have_a_dedicated_info_console_logger(self):
        logger_config = settings.LOGGING["loggers"]["crm.public_image_serving"]
        self.assertEqual(logger_config["level"], "INFO")
        self.assertFalse(logger_config["propagate"])
        self.assertEqual(
            logger_config["handlers"], ["public_image_serving_console"]
        )
        handler_config = settings.LOGGING["handlers"][
            "public_image_serving_console"
        ]
        self.assertEqual(handler_config["class"], "logging.StreamHandler")
        self.assertEqual(handler_config["formatter"], "public_image_serving")

    def test_conditional_revalidation_still_runs_gates_then_returns_304(self):
        first = self.client.get(self.url())
        etag = first["ETag"]

        response = self.client.get(self.url(), HTTP_IF_NONE_MATCH=f'W/{etag}')

        self.assertEqual(response.status_code, 304)
        self.assertEqual(response.content, b"")
        self.assertEqual(response["ETag"], etag)
        self.assertEqual(
            response["Cache-Control"], "private, max-age=60, must-revalidate"
        )
        self.assertNotIn("X-Accel-Redirect", response)
        self.assertEqual(len(ServingBridge.calls), 2)

    def test_disabled_unknown_malformed_unpublished_and_inactive_are_404(self):
        with override_settings(PUBLIC_IMAGE_SERVING_ENABLED=False):
            self.assertEqual(self.client.get(self.url()).status_code, 404)
        self.assertEqual(
            self.client.get(self.url(release_id=str(uuid.uuid4()))).status_code, 404
        )
        malformed_paths = (
            f"/media/releases/{self.release_id.upper()}/square.webp",
            f"/media/releases/{self.release_id}/portrait.webp",
            f"/media/releases/{self.release_id}/square.gif",
            f"/media/releases/{self.release_id}/../square.webp",
        )
        for path in malformed_paths:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.content, b"")
                self.assertEqual(response["Cache-Control"], "no-store")
                self.assertEqual(response["X-Content-Type-Options"], "nosniff")

        Organization.objects.filter(pk=self.organization.pk).update(is_published=False)
        self.assertEqual(self.client.get(self.url()).status_code, 404)
        Organization.objects.filter(pk=self.organization.pk).update(is_published=True)
        OrganizationImageSelection.objects.filter(pk=self.selection.pk).update(
            status="archived"
        )
        self.assertEqual(self.client.get(self.url()).status_code, 404)

    def test_extension_mismatch_and_mapping_inconsistency_fail_closed(self):
        self.assertEqual(self.client.get(self.url(extension="png")).status_code, 404)
        with patch(
            "crm.services.images.serving.build_public_release_key",
            return_value="releases/wrong/square.webp",
        ):
            response = self.client.get(self.url())
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response["Cache-Control"], "no-store")

    def test_negative_authorization_is_404_and_bridge_failure_is_503(self):
        ServingBridge.authorization = BridgeAuthorization(
            authorized=False,
            category="not_active",
            release_id=self.release_id,
            variant="square",
            read_cursor=7,
        )
        negative = self.client.get(self.url())
        self.assertEqual(negative.status_code, 404)
        self.assertEqual(negative["Cache-Control"], "no-store")

        ServingBridge.error = ImageSafetyBridgeUnavailable(
            "safety_unavailable", "synthetic failure", retryable=True
        )
        unavailable = self.client.get(self.url())
        self.assertEqual(unavailable.status_code, 503)
        self.assertEqual(unavailable["Cache-Control"], "no-store")

    def test_every_request_verifies_all_three_files_and_rejects_unsafe_objects(self):
        landscape = next(item for item in self.mappings if item.variant == "landscape")
        landscape_path = self.delivery_root / landscape.public_storage_key
        original = landscape_path.read_bytes()

        landscape_path.unlink()
        self.assertEqual(self.client.get(self.url()).status_code, 503)
        landscape_path.write_bytes(original)

        landscape_path.write_bytes(b"x" * len(original))
        self.assertEqual(self.client.get(self.url()).status_code, 503)
        landscape_path.write_bytes(original)

        target = self.delivery_root / "target.webp"
        target.write_bytes(original)
        landscape_path.unlink()
        landscape_path.symlink_to(target)
        self.assertEqual(self.client.get(self.url()).status_code, 503)


@override_settings(PUBLIC_MEDIA_ORIGIN="https://media.example.no")
class PublicMediaUrlTests(SimpleTestCase):
    def test_builder_uses_only_configured_origin_and_canonical_key(self):
        release_id = str(uuid.uuid4())
        key = build_public_release_key(release_id, "share", "jpeg")

        self.assertEqual(
            build_public_media_url(key),
            f"https://media.example.no/media/releases/{release_id}/share.jpg",
        )

    def test_builder_rejects_noncanonical_or_caller_supplied_urls(self):
        for value in (
            "https://attacker.example/image.webp",
            "../release.webp",
            "releases/not-a-uuid/square.webp",
            f"releases/{uuid.uuid1()}/square.webp",
        ):
            with self.subTest(value=value):
                with self.assertRaises(InvalidPublicMediaKey):
                    validate_canonical_public_key(value)
