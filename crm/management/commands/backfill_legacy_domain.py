import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from crm.services.domain_backfill import apply_backfill, dry_run, read_batch


class Command(BaseCommand):
    help = "Explicit legacy domain registration; default is a consistent read-only dry-run."

    def add_arguments(self, parser):
        parser.add_argument("--mapping", help="JSON file with complete domain/tenant identities.")
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--read-batch", action="store_true")
        parser.add_argument("--environment")
        parser.add_argument("--expected-database")
        parser.add_argument("--expected-digest")
        parser.add_argument("--batch-id")
        parser.add_argument("--operator-id", type=int)
        parser.add_argument("--code-baseline")
        parser.add_argument("--manifest-path")

    def handle(self, *args, **options):
        if options["apply"] and options["read_batch"]:
            raise CommandError("Apply and read-back are separate modes.")
        if options["read_batch"]:
            report = read_batch(environment=options["environment"], expected_database=options["expected_database"],
                                batch_id=options["batch_id"], operator_id=options["operator_id"])
        else:
            try:
                mapping = json.loads(Path(options["mapping"]).read_text())
            except (TypeError, ValueError, OSError) as error:
                raise CommandError("An explicit valid mapping file is required.") from error
            if options["apply"]:
                report = apply_backfill(mapping=mapping, environment=options["environment"],
                    expected_database=options["expected_database"], expected_digest=options["expected_digest"],
                    batch_id=options["batch_id"], operator_id=options["operator_id"],
                    code_baseline=options["code_baseline"], manifest_path=options["manifest_path"])
            else:
                report = dry_run(mapping)
        self.stdout.write(json.dumps(report, sort_keys=True, separators=(",", ":")))
