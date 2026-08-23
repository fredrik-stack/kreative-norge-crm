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
        env.update(
            {
                "DJANGO_DEBUG": "True",
                "IMAGE_ASSET_FEATURE_ENABLED": "False",
                "PUBLIC_IMAGE_RELEASE_MATERIALIZATION_ENABLED": "False",
                **environment,
            }
        )
        return subprocess.run(
            [sys.executable, "-c", "import config.settings"],
            cwd=settings.BASE_DIR,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_delivery_alias_has_no_base_url_and_feature_defaults_off(self):
        self.assertFalse(settings.PUBLIC_IMAGE_RELEASE_MATERIALIZATION_ENABLED)
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
