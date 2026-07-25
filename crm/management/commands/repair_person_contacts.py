from __future__ import annotations

from dataclasses import dataclass

from django.core.management.base import BaseCommand
from django.db import transaction

from crm.models import Person, PersonContact, Tenant


@dataclass
class RepairReport:
    persons_examined: int = 0
    missing_contacts: int = 0
    contacts_to_create: int = 0
    value_mismatches: int = 0
    multiple_primary_conflicts: int = 0
    changes_applied: int = 0


class Command(BaseCommand):
    help = "Backfill missing private primary PersonContact rows from Person.email."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply changes. Without this flag the command only reports what would change.",
        )
        parser.add_argument(
            "--tenant",
            type=str,
            help="Limit repair to one tenant id or slug.",
        )

    def handle(self, *args, **options):
        apply_changes = options["apply"]
        tenant_filter = options.get("tenant")
        people = Person.objects.select_related("tenant").exclude(email__isnull=True).exclude(email="")

        if tenant_filter:
            tenant = self._get_tenant(tenant_filter)
            people = people.filter(tenant=tenant)

        report = RepairReport()
        conflict_lines: list[str] = []

        for person in people.order_by("tenant_id", "id"):
            report.persons_examined += 1
            primaries = list(
                PersonContact.objects.filter(
                    tenant=person.tenant,
                    person=person,
                    type="EMAIL",
                    is_primary=True,
                ).order_by("id")
            )

            if len(primaries) > 1:
                report.multiple_primary_conflicts += 1
                conflict_lines.append(
                    f"person={person.id} tenant={person.tenant_id} has {len(primaries)} primary EMAIL contacts"
                )
                continue

            if len(primaries) == 1:
                primary = primaries[0]
                if primary.value.strip().lower() != person.email.strip().lower():
                    report.value_mismatches += 1
                    conflict_lines.append(
                        f"person={person.id} tenant={person.tenant_id} Person.email differs from primary EMAIL contact {primary.id}"
                    )
                continue

            matching_non_primary = PersonContact.objects.filter(
                tenant=person.tenant,
                person=person,
                type="EMAIL",
                value__iexact=person.email,
            ).exists()
            if matching_non_primary:
                report.value_mismatches += 1
                conflict_lines.append(
                    f"person={person.id} tenant={person.tenant_id} has matching non-primary EMAIL contact"
                )
                continue

            report.missing_contacts += 1
            report.contacts_to_create += 1
            if apply_changes:
                with transaction.atomic():
                    PersonContact.objects.create(
                        tenant=person.tenant,
                        person=person,
                        type="EMAIL",
                        value=person.email,
                        is_primary=True,
                        is_public=False,
                    )
                report.changes_applied += 1

        mode = "APPLY" if apply_changes else "DRY-RUN"
        self.stdout.write(f"repair_person_contacts mode={mode}")
        self.stdout.write(f"persons_examined={report.persons_examined}")
        self.stdout.write(f"missing_contacts={report.missing_contacts}")
        self.stdout.write(f"contacts_to_create={report.contacts_to_create}")
        self.stdout.write(f"value_mismatches={report.value_mismatches}")
        self.stdout.write(f"multiple_primary_conflicts={report.multiple_primary_conflicts}")
        self.stdout.write(f"changes_applied={report.changes_applied}")
        if conflict_lines:
            self.stdout.write("conflicts:")
            for line in conflict_lines:
                self.stdout.write(f"- {line}")

    def _get_tenant(self, value: str) -> Tenant:
        if value.isdigit():
            return Tenant.objects.get(id=int(value))
        return Tenant.objects.get(slug=value)
