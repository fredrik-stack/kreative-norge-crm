from __future__ import annotations

from pathlib import Path
import re
import unittest

import yaml


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


class StagingImageRuntimeContractTests(unittest.TestCase):
    def test_web_image_keeps_delivery_gid_after_nginx_drops_privileges(self):
        dockerfile = (REPOSITORY_ROOT / "Dockerfile.web").read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "addgroup -S -g 2000 kreative-norge-public-media", dockerfile
        )
        self.assertIn("addgroup nginx kreative-norge-public-media", dockerfile)

    def test_compose_mounts_images_only_into_api(self):
        compose = yaml.safe_load(
            (REPOSITORY_ROOT / "docker-compose.staging.yml").read_text(
                encoding="utf-8"
            )
        )
        api_volumes = set(compose["services"]["api"]["volumes"])
        web_volumes = compose["services"]["web"]["volumes"]
        self.assertEqual(compose["services"]["web"]["group_add"], ["2000"])

        self.assertIn(
            "/srv/kreative-norge/media/private:/srv/kreative-norge/media/private",
            api_volumes,
        )
        self.assertIn(
            "/srv/kreative-norge/media/public:/srv/kreative-norge/media/public",
            api_volumes,
        )
        self.assertIn(
            "/srv/kreative-norge/media/public-delivery:"
            "/srv/kreative-norge/media/public-delivery",
            api_volumes,
        )
        self.assertIn(
            "/run/kreative-norge-image-safety:"
            "/run/kreative-norge-image-safety:ro",
            api_volumes,
        )
        self.assertEqual(
            set(web_volumes),
            {
                "django_static:/var/www/django-static:ro",
                "/srv/kreative-norge/media/public-delivery:"
                "/var/www/public-delivery:ro",
            },
        )
        self.assertFalse(
            any("/srv/kreative-norge/media/private" in volume for volume in web_volumes)
        )
        self.assertFalse(
            any(
                volume.startswith(
                    "/srv/kreative-norge/media/public:/srv/kreative-norge/media/public"
                )
                for volume in web_volumes
            )
        )
        self.assertFalse(any("image-safety" in volume for volume in web_volumes))
        self.assertEqual(
            sum("public-delivery" in volume for volume in web_volumes), 1
        )
        self.assertTrue(
            next(volume for volume in web_volumes if "public-delivery" in volume).endswith(
                ":ro"
            )
        )
        for volumes in (api_volumes, set(web_volumes)):
            self.assertFalse(any("/var/lib/kreative-norge-image-safety" in item for item in volumes))
            self.assertFalse(any("/etc/kreative-norge-image-safety" in item for item in volumes))
            self.assertFalse(any("borg" in item.casefold() for item in volumes))

    def test_staging_example_keeps_feature_off_with_explicit_container_roots(self):
        environment = (REPOSITORY_ROOT / ".env.staging.example").read_text(encoding="utf-8")

        self.assertIn("IMAGE_ASSET_FEATURE_ENABLED=False", environment)
        self.assertIn(
            "IMAGE_ORIGINALS_ROOT=/srv/kreative-norge/media/private",
            environment,
        )
        self.assertIn(
            "IMAGE_RENDITIONS_ROOT=/srv/kreative-norge/media/public",
            environment,
        )
        self.assertIn(
            "PUBLIC_IMAGE_DELIVERY_ROOT=/srv/kreative-norge/media/public-delivery",
            environment,
        )
        self.assertIn("PUBLIC_IMAGE_RELEASE_MATERIALIZATION_ENABLED=False", environment)
        self.assertIn("PUBLIC_IMAGE_SERVING_ENABLED=False", environment)
        self.assertIn("PUBLIC_SITE_ORIGIN=https://staging.example.no", environment)
        self.assertIn("PUBLIC_MEDIA_ORIGIN=https://staging.example.no", environment)
        self.assertIn(
            "PUBLIC_IMAGE_SAFETY_BRIDGE_SOCKET="
            "/run/kreative-norge-image-safety/bridge.sock",
            environment,
        )

    def test_nginx_accepts_the_15_mib_image_upload_contract(self):
        nginx_config = (REPOSITORY_ROOT / "deploy/staging/nginx.conf").read_text(
            encoding="utf-8"
        )
        match = re.search(r"client_max_body_size\s+(\d+)m;", nginx_config)

        self.assertIsNotNone(match)
        self.assertGreaterEqual(
            int(match.group(1)),
            16,
            "Staging ingress must allow a 15 MiB file plus multipart overhead.",
        )

    def test_nginx_routes_media_through_django_and_keeps_delivery_internal(self):
        nginx_config = (REPOSITORY_ROOT / "deploy/staging/nginx.conf").read_text(
            encoding="utf-8"
        )

        self.assertRegex(
            nginx_config,
            r"location \^~ /media/releases/ \{\s+proxy_pass http://api:8000;",
        )
        self.assertRegex(
            nginx_config,
            r"location \^~ /_protected-public-image/ \{\s+internal;\s+"
            r"alias /var/www/public-delivery/;\s+autoindex off;\s+"
            r"disable_symlinks on;",
        )
        self.assertNotIn("proxy_cache", nginx_config)

    def test_backup_allowlist_explicitly_covers_all_host_roots(self):
        backup_example = (REPOSITORY_ROOT / "ops/backup/backup.env.example").read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "HOST_MEDIA_PATHS=/srv/kreative-norge/media/default:"
            "/srv/kreative-norge/media/private:/srv/kreative-norge/media/public:"
            "/srv/kreative-norge/media/public-delivery",
            backup_example,
        )

    def test_storage_prepare_script_provisions_delivery_as_separate_root(self):
        script = (REPOSITORY_ROOT / "ops/staging/prepare-image-storage.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("DELIVERY_ROOT=/srv/kreative-norge/media/public-delivery", script)
        self.assertIn("DELIVERY_GROUP_NAME=kreative-norge-public-media", script)
        self.assertIn("DELIVERY_GROUP_ID=2000", script)
        self.assertIn('find "$DELIVERY_ROOT" -type d -exec chmod 2750', script)
        self.assertIn('find "$DELIVERY_ROOT" -type f -exec chmod 0640', script)
        self.assertNotIn("SAFETY", script)


if __name__ == "__main__":
    unittest.main()
