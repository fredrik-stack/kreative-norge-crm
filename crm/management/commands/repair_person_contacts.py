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
    matching_non_primary_conflicts: int = 0
    multiple_primary_conflicts: int = 0
    changes_applied: int = 0


class Command(BaseCommand):
    help = "Backfill missing private primary PersonContact rows from Person.email or Person.phone."

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
        parser.add_argument(
            "--contact-type",
            type=str.upper,
            choices=("EMAIL", "PHONE"),
            default="EMAIL",
            help="Contact type to repair. Defaults to EMAIL for backward compatibility.",
        )

    def handle(self, *args, **options):
        apply_changes = options["apply"]
        tenant_filter = options.get("tenant")
        contact_type = options["contact_type"]
        field_name = "email" if contact_type == "EMAIL" else "phone"
        people = (
            Person.objects.select_related("tenant")
            .exclude(**{f"{field_name}__isnull": True})
            .exclude(**{field_name: ""})
        )

        if tenant_filter:
            tenant = self._get_tenant(tenant_filter)
            people = people.filter(tenant=tenant)

        report = RepairReport()
        conflict_lines: list[str] = []
        candidate_lines: list[str] = []

        for person in people.order_by("tenant_id", "id"):
            report.persons_examined += 1
            direct_value = (getattr(person, field_name) or "").strip()
            if not direct_value:
                continue
            primaries = list(
                PersonContact.objects.filter(
                    tenant=person.tenant,
                    person=person,
                    type=contact_type,
                    is_primary=True,
                ).order_by("id")
            )

            if len(primaries) > 1:
                report.multiple_primary_conflicts += 1
                conflict_lines.append(
                    f"person={person.id} tenant={person.tenant_id} has {len(primaries)} primary {contact_type} contacts"
                )
                continue

            if len(primaries) == 1:
                primary = primaries[0]
                if self._normalized(primary.value, contact_type) != self._normalized(direct_value, contact_type):
                    report.value_mismatches += 1
                    conflict_lines.append(
                        f"person={person.id} tenant={person.tenant_id} Person.{field_name} differs from primary "
                        f"{contact_type} contact {primary.id}"
                    )
                continue

            non_primary_values = PersonContact.objects.filter(
                tenant=person.tenant,
                person=person,
                type=contact_type,
                is_primary=False,
            ).values_list("value", flat=True)
            matching_non_primary = any(
                self._normalized(value, contact_type) == self._normalized(direct_value, contact_type)
                for value in non_primary_values
            )
            if matching_non_primary:
                report.matching_non_primary_conflicts += 1
                conflict_lines.append(
                    f"person={person.id} tenant={person.tenant_id} has matching non-primary {contact_type} contact"
                )
                continue

            report.missing_contacts += 1
            report.contacts_to_create += 1
            candidate_line = (
                f"person={person.id} tenant={person.tenant_id} missing primary {contact_type} contact"
            )
            if apply_changes:
                with transaction.atomic():
                    contact = PersonContact.objects.create(
                        tenant=person.tenant,
                        person=person,
                        type=contact_type,
                        value=direct_value,
                        is_primary=True,
                        is_public=False,
                    )
                report.changes_applied += 1
                candidate_line += f" created_contact={contact.id}"
            candidate_lines.append(candidate_line)

        mode = "APPLY" if apply_changes else "DRY-RUN"
        self.stdout.write(f"repair_person_contacts mode={mode}")
        self.stdout.write(f"contact_type={contact_type}")
        self.stdout.write(f"persons_examined={report.persons_examined}")
        self.stdout.write(f"missing_contacts={report.missing_contacts}")
        self.stdout.write(f"contacts_to_create={report.contacts_to_create}")
        self.stdout.write(f"value_mismatches={report.value_mismatches}")
        self.stdout.write(f"matching_non_primary_conflicts={report.matching_non_primary_conflicts}")
        self.stdout.write(f"multiple_primary_conflicts={report.multiple_primary_conflicts}")
        self.stdout.write(f"changes_applied={report.changes_applied}")
        if candidate_lines:
            self.stdout.write("candidates:")
            for line in candidate_lines:
                self.stdout.write(f"- {line}")
        if conflict_lines:
            self.stdout.write("conflicts:")
            for line in conflict_lines:
                self.stdout.write(f"- {line}")

    def _get_tenant(self, value: str) -> Tenant:
        if value.isdigit():
            return Tenant.objects.get(id=int(value))
        return Tenant.objects.get(slug=value)

    @staticmethod
    def _normalized(value: str, contact_type: str) -> str:
        normalized = value.strip()
        return normalized.lower() if contact_type == "EMAIL" else normalized
