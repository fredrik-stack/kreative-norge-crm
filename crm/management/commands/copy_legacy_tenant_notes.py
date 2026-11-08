import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from crm.services.phone_backfill import write_phone_backfill_manifest
from crm.services.tenant_note_copy import apply_copy, dry_run, public_report, read_batch


class Command(BaseCommand):
    help = "Operator-only exact note copy; default is a read-only database plan."
    requires_system_checks = []

    def create_parser(self, *args, **kwargs):
        parser = super().create_parser(*args, **kwargs)
        parser.allow_abbrev = False
        return parser

    def add_arguments(self, parser):
        parser.add_argument("--mapping")
        parser.add_argument("--plan-path", help="Private no-clobber dry-run plan output (required).")
        parser.add_argument("--receipt-path", help="Optional private no-clobber read-back output.")
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--read-batch", action="store_true")
        parser.add_argument("--environment", required=True)
        parser.add_argument("--expected-database", required=True)
        parser.add_argument("--operator-id", type=int, required=True)
        parser.add_argument("--code-baseline")
        parser.add_argument("--expected-digest")
        parser.add_argument("--batch-id")
        parser.add_argument("--manifest-path")

    def handle(self, *args, **options):
        from crm.tenant_access import block_legacy_operator
        block_legacy_operator()
        try:
            if options["apply"] and options["read_batch"]:
                raise CommandError("NOTE_COPY_EXCLUSIVE_MODES")
            common = {k: options[k] for k in ("environment", "expected_database", "operator_id")}
            if options["read_batch"]:
                if any(options[k] for k in ("mapping", "plan_path", "code_baseline", "expected_digest", "manifest_path")):
                    raise CommandError("NOTE_COPY_READ_ARGUMENTS")
                report = read_batch(**common, batch_id=options["batch_id"])
                if options["receipt_path"]:
                    write_phone_backfill_manifest(options["receipt_path"], report)
            else:
                if options["receipt_path"]:
                    raise CommandError("NOTE_COPY_RECEIPT_READ_ONLY")
                mapping = json.loads(Path(options["mapping"]).read_text())
                if options["apply"]:
                    if options["plan_path"]:
                        raise CommandError("NOTE_COPY_PLAN_DRY_RUN_ONLY")
                    report = apply_copy(**common, mapping=mapping, code_baseline=options["code_baseline"],
                        expected_digest=options["expected_digest"], batch_id=options["batch_id"],
                        manifest_path=options["manifest_path"])
                else:
                    if not options["plan_path"] or any(options[k] for k in ("expected_digest", "batch_id", "manifest_path")):
                        raise CommandError("NOTE_COPY_PLAN_ARGUMENTS")
                    report = dry_run(mapping, **common, code_baseline=options["code_baseline"])
                    write_phone_backfill_manifest(options["plan_path"], report)
        except Exception as error:
            code = str(error) if isinstance(error, CommandError) and str(error).startswith("NOTE_COPY_") else "NOTE_COPY_FAILED_USE_READ_BACK_IF_REGISTERED"
            # Suppress chained driver errors even with --traceback: they may contain notes.
            raise CommandError(code) from None
        self.stdout.write(json.dumps(public_report(report), sort_keys=True, separators=(",", ":")))
