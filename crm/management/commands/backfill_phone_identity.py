from __future__ import annotations

import json

from django.core.management.base import BaseCommand, CommandError

from crm.services.phone_backfill import (
    execute_phone_backfill,
    execute_phone_backfill_rollback,
)


class Command(BaseCommand):
    help = (
        "Dry-run or apply the tenant-scoped phase 4G canonical phone backfill. "
        "Output is aggregate and contains no raw phone values."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--tenant-id",
            action="append",
            type=int,
            dest="tenant_ids",
            help="Explicit tenant ID in the complete approved scope; repeat for each tenant.",
        )
        parser.add_argument("--expect-total-tenants", type=int)
        parser.add_argument("--default-region", type=str)
        parser.add_argument("--batch-id", type=str)
        parser.add_argument("--manifest-path", type=str)
        parser.add_argument("--rollback-manifest", type=str)
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply changes. Without this flag the command is read-only.",
        )

    def handle(self, *args, **options):
        rollback_manifest = options.get("rollback_manifest")
        if rollback_manifest:
            forbidden = (
                options.get("tenant_ids"),
                options.get("expect_total_tenants"),
                options.get("default_region"),
                options.get("batch_id"),
                options.get("manifest_path"),
            )
            if any(value is not None and value != [] for value in forbidden):
                raise CommandError(
                    "Rollback mode accepts only --rollback-manifest and optional --apply."
                )
            report = execute_phone_backfill_rollback(
                manifest_path=rollback_manifest,
                apply_changes=options["apply"],
            )
        else:
            if not options.get("tenant_ids"):
                raise CommandError("Forward mode requires repeated --tenant-id scope.")
            if options.get("expect_total_tenants") is None:
                raise CommandError("Forward mode requires --expect-total-tenants.")
            if not options.get("default_region"):
                raise CommandError("Forward mode requires explicit --default-region.")
            report = execute_phone_backfill(
                tenant_ids=options["tenant_ids"],
                expected_total_tenants=options["expect_total_tenants"],
                target_region=options["default_region"],
                apply_changes=options["apply"],
                batch_id=options.get("batch_id"),
                manifest_path=options.get("manifest_path"),
            )
        self.stdout.write(json.dumps(report, sort_keys=True, separators=(",", ":")))
