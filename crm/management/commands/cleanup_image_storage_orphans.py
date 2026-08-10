from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from crm.services.images.cleanup import (
    ImageOrphanCleanupError,
    cleanup_image_storage_orphans,
)


class Command(BaseCommand):
    help = "Report or delete unreferenced files inside the explicit image storage roots."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Delete eligible orphan files. Without this flag the command is dry-run only.",
        )
        parser.add_argument(
            "--minimum-age-hours",
            type=int,
            default=24,
            help="Only consider files at least this old. Defaults to 24 hours.",
        )

    def handle(self, *args, **options):
        try:
            result = cleanup_image_storage_orphans(
                apply=options["apply"],
                minimum_age_hours=options["minimum_age_hours"],
            )
        except ImageOrphanCleanupError as error:
            raise CommandError(str(error)) from error

        mode = "APPLY" if options["apply"] else "DRY-RUN"
        self.stdout.write(f"cleanup_image_storage_orphans mode={mode}")
        for plan in result.plans:
            self.stdout.write(f"alias={plan.alias}")
            self.stdout.write(f"referenced_files={len(plan.referenced_keys)}")
            self.stdout.write(f"storage_files={len(plan.file_keys)}")
            self.stdout.write(f"eligible_orphans={len(plan.orphan_keys)}")
            self.stdout.write(f"young_unreferenced_files={len(plan.young_orphan_keys)}")
        self.stdout.write(f"deleted_files={len(result.deleted_keys)}")
