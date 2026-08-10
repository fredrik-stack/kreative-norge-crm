from __future__ import annotations

from pathlib import Path
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


class StagingImageRuntimeContractTests(unittest.TestCase):
    def test_compose_binds_only_the_two_explicit_image_roots(self):
        compose = (REPOSITORY_ROOT / "docker-compose.staging.yml").read_text(encoding="utf-8")

        self.assertIn(
            "/srv/kreative-norge/media/private:/srv/kreative-norge/media/private",
            compose,
        )
        self.assertIn(
            "/srv/kreative-norge/media/public:/srv/kreative-norge/media/public",
            compose,
        )
        self.assertNotIn("/srv/kreative-norge/media:/", compose)

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

    def test_backup_allowlist_already_covers_both_host_roots(self):
        backup_example = (REPOSITORY_ROOT / "ops/backup/backup.env.example").read_text(
            encoding="utf-8"
        )

        self.assertIn(
            "HOST_MEDIA_PATHS=/srv/kreative-norge/media/default:"
            "/srv/kreative-norge/media/private:/srv/kreative-norge/media/public",
            backup_example,
        )


if __name__ == "__main__":
    unittest.main()
