import json

from django.core.management.base import BaseCommand, CommandError, CommandParser

from crm.services.domain_read_shadow import EXIT_CODES, ShadowPrecondition, incomplete, measure


class SanitizedParser(CommandParser):
    def error(self, message):
        # argparse normally echoes caller values, including unrecognized arguments.
        if self.called_from_command_line:
            self.exit(4, "INVALID_ARGUMENTS\n")
        raise CommandError("INVALID_ARGUMENTS", returncode=4) from None


class Command(BaseCommand):
    help = "Operator-only Musikkontoret PK shadow; no data changes or API activation."
    requires_system_checks = []
    requires_migrations_checks = False

    def run_from_argv(self, argv):
        # This operator command always preserves its sanitized status/exit contract.
        # Django's global --traceback would otherwise re-raise CommandError as exit 1.
        return super().run_from_argv([
            *argv[:2], *(arg for arg in argv[2:] if arg != "--traceback"),
        ])

    def create_parser(self, prog_name, subcommand, **kwargs):
        parser = super().create_parser(prog_name, subcommand, **kwargs)
        parser.__class__ = SanitizedParser
        return parser

    def add_arguments(self, parser):
        parser.add_argument("--environment", required=True)
        parser.add_argument("--expected-database", required=True)
        parser.add_argument("--code-baseline", required=True,
                            help="Exact SHA externally verified against the reviewed running code/image.")

    def handle(self, *args, **options):
        try:
            report = measure(environment=options["environment"], expected_database=options["expected_database"],
                             code_baseline=options["code_baseline"])
        except ShadowPrecondition as error:
            report = incomplete(str(error))
        except KeyboardInterrupt:
            report = incomplete("INTERRUPTED")
        except Exception:
            # No traceback, SQL parameters or raw exception text, including --traceback.
            report = incomplete("MEASUREMENT_ERROR")
        self.stdout.write(json.dumps(report, sort_keys=True, separators=(",", ":")))
        if EXIT_CODES[report["status"]]:
            raise CommandError(report["status"], returncode=EXIT_CODES[report["status"]]) from None
