"""Offline central appointment; requires a separately approved operational mandate."""
from uuid import UUID
from django.core.management.base import BaseCommand, CommandError
from crm.services import access_management as service


class Command(BaseCommand):
    help = "Plan/apply an explicit scoped appointment or revocation. Never run without a separate mandate."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--operator-id", type=int, required=True)
        parser.add_argument("--mandate-reference", required=True)
        parser.add_argument("--expected-database", required=True)
        parser.add_argument("--user-id", type=int)
        parser.add_argument("--domain-id", type=int)
        parser.add_argument("--tenant-id", type=int)
        parser.add_argument("--action", choices=service.Grant.Action.values)
        parser.add_argument("--request-id", type=UUID)
        parser.add_argument("--revoke-grant-id", type=int)

    def handle(self, *args, **options):
        if not options["apply"]:
            # Deliberately no database connection or user lookup on this dry-run.
            self.stdout.write("PLAN_ONLY: no writes; apply requires separate mandate, verified database and exact scope.")
            return
        try:
            if options["revoke_grant_id"]:
                if any(options[k] is not None for k in ("user_id", "domain_id", "tenant_id", "action", "request_id")):
                    raise service.ManagementError("INVALID_APPOINTMENT")
                pk = service.withdraw_appointment(actor_id=options["operator_id"], grant_id=options["revoke_grant_id"],
                    mandate_reference=options["mandate_reference"], expected_database=options["expected_database"])
            else:
                pk = service.appoint(actor_id=options["operator_id"], user_id=options["user_id"],
                    domain_id=options["domain_id"], tenant_id=options["tenant_id"], action=options["action"],
                    request_id=options["request_id"], mandate_reference=options["mandate_reference"],
                    expected_database=options["expected_database"])
            self.stdout.write(f"COMMITTED_OR_REPLAYED record_id={pk}; read back the record and scope before use.")
        except service.ManagementError as exc:
            raise CommandError(str(exc)) from None
