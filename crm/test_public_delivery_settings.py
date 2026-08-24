import os
from pathlib import Path
import subprocess
import sys
import tempfile

from django.conf import settings
from django.core.files.storage import storages
from django.test import SimpleTestCase


class PublicDeliverySettingsTests(SimpleTestCase):
    def run_settings(self, **environment):
        env = os.environ.copy()
        storage_root = Path(tempfile.gettempdir()).resolve() / "kreative-norge-origin-tests"
        for name in (
            "PUBLIC_IMAGE_SERVING_ENABLED",
            "PUBLIC_IMAGE_PROJECTION_ENABLED",
            "PUBLIC_IMAGE_API_SCHEMA_ENABLED",
            "PUBLIC_IMAGE_PUBLIC_CUTOVER_ENABLED",
            "PUBLIC_SITE_ORIGIN",
            "PUBLIC_MEDIA_ORIGIN",
        ):
            env.pop(name, None)
        env.update(
            {
                "DJANGO_DEBUG": "True",
                "IMAGE_ASSET_FEATURE_ENABLED": "False",
                "PUBLIC_IMAGE_RELEASE_MATERIALIZATION_ENABLED": "False",
                "IMAGE_ORIGINALS_ROOT": str(storage_root / "private"),
                "IMAGE_RENDITIONS_ROOT": str(storage_root / "artifacts"),
                "PUBLIC_IMAGE_DELIVERY_ROOT": str(storage_root / "delivery"),
                **environment,
            }
        )
        return subprocess.run(
            [
                sys.executable,
                "-c",
                "import config.settings as settings; "
                "print(settings.PUBLIC_SITE_ORIGIN, settings.PUBLIC_MEDIA_ORIGIN, "
                "settings.PUBLIC_IMAGE_PROJECTION_ENABLED, "
                "settings.PUBLIC_IMAGE_API_SCHEMA_ENABLED, "
                "settings.PUBLIC_IMAGE_PUBLIC_CUTOVER_ENABLED)",
            ],
            cwd=settings.BASE_DIR,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_delivery_alias_has_no_base_url_and_feature_defaults_off(self):
        self.assertFalse(settings.PUBLIC_IMAGE_RELEASE_MATERIALIZATION_ENABLED)
        self.assertFalse(settings.PUBLIC_IMAGE_SERVING_ENABLED)
        self.assertFalse(settings.PUBLIC_IMAGE_PROJECTION_ENABLED)
        self.assertFalse(settings.PUBLIC_IMAGE_API_SCHEMA_ENABLED)
        self.assertFalse(settings.PUBLIC_IMAGE_PUBLIC_CUTOVER_ENABLED)
        self.assertIsNone(
            settings.STORAGES["public_image_delivery"]["OPTIONS"]["base_url"]
        )
        delivery_storage = storages["public_image_delivery"]
        self.assertIsNone(delivery_storage.base_url)
        with self.assertRaises(NotImplementedError):
            delivery_storage.url("releases/example/square.webp")

    def test_materialization_requires_general_image_feature(self):
        result = self.run_settings(
            PUBLIC_IMAGE_RELEASE_MATERIALIZATION_ENABLED="True"
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires IMAGE_ASSET_FEATURE_ENABLED", result.stderr)

    def test_delivery_overlap_with_artifacts_repo_or_safety_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            cases = (
                {
                    "IMAGE_ORIGINALS_ROOT": str(root / "private"),
                    "IMAGE_RENDITIONS_ROOT": str(root / "artifacts"),
                    "PUBLIC_IMAGE_DELIVERY_ROOT": str(root / "artifacts" / "delivery"),
                },
                {"PUBLIC_IMAGE_DELIVERY_ROOT": str(settings.BASE_DIR / "delivery")},
                {
                    "PUBLIC_IMAGE_DELIVERY_ROOT": "/var/lib/kreative-norge-image-safety/delivery"
                },
            )
            for environment in cases:
                with self.subTest(environment=environment):
                    result = self.run_settings(**environment)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("PUBLIC_IMAGE_DELIVERY_ROOT", result.stderr)

    def test_delivery_symlink_component_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            target = root / "target"
            target.mkdir()
            linked = root / "linked"
            linked.symlink_to(target, target_is_directory=True)

            result = self.run_settings(PUBLIC_IMAGE_DELIVERY_ROOT=str(linked / "delivery"))

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symlink components", result.stderr)

    def test_serving_requires_materialization_and_both_origins(self):
        requires_materialization = self.run_settings(
            PUBLIC_IMAGE_SERVING_ENABLED="True"
        )
        self.assertNotEqual(requires_materialization.returncode, 0)
        self.assertIn(
            "requires PUBLIC_IMAGE_RELEASE_MATERIALIZATION_ENABLED",
            requires_materialization.stderr,
        )

        missing_origins = self.run_settings(
            DJANGO_DEBUG="False",
            DJANGO_ALLOWED_HOSTS="staging.example.no",
            IMAGE_ASSET_FEATURE_ENABLED="True",
            PUBLIC_IMAGE_RELEASE_MATERIALIZATION_ENABLED="True",
            PUBLIC_IMAGE_SERVING_ENABLED="True",
        )
        self.assertNotEqual(missing_origins.returncode, 0)
        self.assertIn("PUBLIC_SITE_ORIGIN must be set", missing_origins.stderr)

    def test_origins_are_normalized_against_exact_allowed_host(self):
        result = self.run_settings(
            DJANGO_DEBUG="True",
            DJANGO_ALLOWED_HOSTS="staging.example.no",
            IMAGE_ASSET_FEATURE_ENABLED="True",
            PUBLIC_IMAGE_RELEASE_MATERIALIZATION_ENABLED="True",
            PUBLIC_IMAGE_SERVING_ENABLED="True",
            PUBLIC_SITE_ORIGIN="HTTPS://STAGING.EXAMPLE.NO:443/",
            PUBLIC_MEDIA_ORIGIN="https://staging.example.no/",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.strip(),
            "https://staging.example.no https://staging.example.no False False False",
        )

    def test_projection_and_schema_dependencies_fail_closed(self):
        missing_projection_origin = self.run_settings(
            PUBLIC_IMAGE_PROJECTION_ENABLED="True",
            DJANGO_ALLOWED_HOSTS="public.example.no",
            PUBLIC_SITE_ORIGIN="https://public.example.no",
        )
        self.assertNotEqual(missing_projection_origin.returncode, 0)
        self.assertIn("PUBLIC_MEDIA_ORIGIN must be set", missing_projection_origin.stderr)

        schema_without_projection = self.run_settings(
            PUBLIC_IMAGE_API_SCHEMA_ENABLED="True"
        )
        self.assertNotEqual(schema_without_projection.returncode, 0)
        self.assertIn(
            "requires PUBLIC_IMAGE_PROJECTION_ENABLED",
            schema_without_projection.stderr,
        )

        schema_without_serving = self.run_settings(
            PUBLIC_IMAGE_PROJECTION_ENABLED="True",
            PUBLIC_IMAGE_API_SCHEMA_ENABLED="True",
            PUBLIC_SITE_ORIGIN="https://public.example.no",
            PUBLIC_MEDIA_ORIGIN="https://media.example.no",
        )
        self.assertNotEqual(schema_without_serving.returncode, 0)
        self.assertIn("requires PUBLIC_IMAGE_SERVING_ENABLED", schema_without_serving.stderr)

    def test_public_cutover_dependencies_fail_closed_and_valid_stack_starts(self):
        cutover_without_projection = self.run_settings(
            PUBLIC_IMAGE_PUBLIC_CUTOVER_ENABLED="True"
        )
        self.assertNotEqual(cutover_without_projection.returncode, 0)
        self.assertIn(
            "requires PUBLIC_IMAGE_PROJECTION_ENABLED",
            cutover_without_projection.stderr,
        )

        cutover_without_schema = self.run_settings(
            PUBLIC_IMAGE_PROJECTION_ENABLED="True",
            PUBLIC_IMAGE_PUBLIC_CUTOVER_ENABLED="True",
            PUBLIC_SITE_ORIGIN="https://public.example.no",
            PUBLIC_MEDIA_ORIGIN="https://media.example.no",
        )
        self.assertNotEqual(cutover_without_schema.returncode, 0)
        self.assertIn(
            "requires PUBLIC_IMAGE_API_SCHEMA_ENABLED",
            cutover_without_schema.stderr,
        )

        valid = self.run_settings(
            DJANGO_ALLOWED_HOSTS="public.example.no,media.example.no",
            IMAGE_ASSET_FEATURE_ENABLED="True",
            PUBLIC_IMAGE_RELEASE_MATERIALIZATION_ENABLED="True",
            PUBLIC_IMAGE_SERVING_ENABLED="True",
            PUBLIC_IMAGE_PROJECTION_ENABLED="True",
            PUBLIC_IMAGE_API_SCHEMA_ENABLED="True",
            PUBLIC_IMAGE_PUBLIC_CUTOVER_ENABLED="True",
            PUBLIC_SITE_ORIGIN="https://public.example.no",
            PUBLIC_MEDIA_ORIGIN="https://media.example.no",
        )
        self.assertEqual(valid.returncode, 0, valid.stderr)
        self.assertEqual(
            valid.stdout.strip(),
            "https://public.example.no https://media.example.no True True True",
        )

    def test_invalid_origins_fail_closed(self):
        cases = (
            ("http://staging.example.no", "must use HTTPS"),
            ("https://user:password@staging.example.no", "cannot contain user"),
            ("https://staging.example.no/media", "cannot contain a path"),
            ("https://staging.example.no?query=yes", "cannot contain a query"),
            ("https://staging.example.no#fragment", "cannot contain a fragment"),
            ("https://staging.example.no\n", "whitespace or control"),
            ("https://other.example.no", "exact non-wildcard"),
        )
        for origin, message in cases:
            with self.subTest(origin=repr(origin)):
                result = self.run_settings(
                    DJANGO_DEBUG="False",
                    DJANGO_ALLOWED_HOSTS="staging.example.no",
                    IMAGE_ASSET_FEATURE_ENABLED="True",
                    PUBLIC_IMAGE_RELEASE_MATERIALIZATION_ENABLED="True",
                    PUBLIC_IMAGE_SERVING_ENABLED="True",
                    PUBLIC_SITE_ORIGIN=origin,
                    PUBLIC_MEDIA_ORIGIN="https://staging.example.no",
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)

    def test_wildcard_allowed_host_does_not_authorize_origin(self):
        result = self.run_settings(
            DJANGO_DEBUG="False",
            DJANGO_ALLOWED_HOSTS="*",
            IMAGE_ASSET_FEATURE_ENABLED="True",
            PUBLIC_IMAGE_RELEASE_MATERIALIZATION_ENABLED="True",
            PUBLIC_IMAGE_SERVING_ENABLED="True",
            PUBLIC_SITE_ORIGIN="https://staging.example.no",
            PUBLIC_MEDIA_ORIGIN="https://staging.example.no",
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exact non-wildcard", result.stderr)
