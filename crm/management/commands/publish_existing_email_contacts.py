from __future__ import annotations

from dataclasses import dataclass

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from crm.models import Organization, OrganizationPerson, Person, PersonContact, Tenant


EXCEPTION_LINKS = (
    ("Nordland fylkeskommune", "Kathrine Schem"),
    ("Nordland fylkeskommune", "Ole-Thomas Kolberg"),
    ("Bådin", "Jonas Jørgensen Moe"),
)


@dataclass
class PublishReport:
    email_contacts_total: int = 0
    email_contacts_public_before: int = 0
    email_contacts_to_publish: int = 0
    active_person_links_total: int = 0
    active_publish_true_before: int = 0
    active_links_to_change: int = 0
    exception_links_to_unpublish: int = 0
    changes_applied: int = 0


class Command(BaseCommand):
    help = "Publish existing email contacts and active person links, except approved relation-specific exclusions."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply changes. Without this flag the command only reports what would change.",
        )
        parser.add_argument(
            "--tenant",
            type=str,
            help="Limit updates to one tenant id or slug.",
        )

    def handle(self, *args, **options):
        apply_changes = options["apply"]
        tenant_filter = options.get("tenant")
        tenant = self._get_tenant(tenant_filter) if tenant_filter else None

        exception_links = self._resolve_exception_links(tenant=tenant)
        exception_ids = {link.id for link in exception_links}

        emails = PersonContact.objects.filter(type="EMAIL")
        active_links = OrganizationPerson.objects.filter(status="ACTIVE")
        if tenant:
            emails = emails.filter(tenant=tenant)
            active_links = active_links.filter(tenant=tenant)

        report = PublishReport(
            email_contacts_total=emails.count(),
            email_contacts_public_before=emails.filter(is_public=True).count(),
            email_contacts_to_publish=emails.filter(is_public=False).count(),
            active_person_links_total=active_links.count(),
            active_publish_true_before=active_links.filter(publish_person=True).count(),
        )

        link_changes = []
        for link in active_links.select_related("organization", "person").order_by("tenant_id", "id"):
            desired_publish = link.id not in exception_ids
            if link.publish_person != desired_publish:
                link_changes.append((link, desired_publish))
                if not desired_publish:
                    report.exception_links_to_unpublish += 1

        report.active_links_to_change = len(link_changes)

        if apply_changes:
            with transaction.atomic():
                email_changes = emails.filter(is_public=False).update(is_public=True)
                link_change_count = 0
                for link, desired_publish in link_changes:
                    link.publish_person = desired_publish
                    link.save(update_fields=["publish_person"])
                    link_change_count += 1
                report.changes_applied = email_changes + link_change_count

        mode = "APPLY" if apply_changes else "DRY-RUN"
        self.stdout.write(f"publish_existing_email_contacts mode={mode}")
        self.stdout.write(f"email_contacts_total={report.email_contacts_total}")
        self.stdout.write(f"email_contacts_public_before={report.email_contacts_public_before}")
        self.stdout.write(f"email_contacts_to_publish={report.email_contacts_to_publish}")
        self.stdout.write(f"active_person_links_total={report.active_person_links_total}")
        self.stdout.write(f"active_publish_true_before={report.active_publish_true_before}")
        self.stdout.write(f"active_links_to_change={report.active_links_to_change}")
        self.stdout.write(f"exception_links_to_unpublish={report.exception_links_to_unpublish}")
        self.stdout.write(f"changes_applied={report.changes_applied}")
        self.stdout.write("exceptions:")
        for link in exception_links:
            self.stdout.write(
                "- "
                f"organization={link.organization.name} "
                f"person={link.person.full_name} "
                f"link_id={link.id} "
                f"status={link.status} "
                f"publish_person={link.publish_person}"
            )

    def _resolve_exception_links(self, *, tenant: Tenant | None) -> list[OrganizationPerson]:
        links: list[OrganizationPerson] = []
        errors: list[str] = []
        for organization_name, person_name in EXCEPTION_LINKS:
            organizations = Organization.objects.filter(name=organization_name)
            people = Person.objects.filter(full_name=person_name)
            if tenant:
                organizations = organizations.filter(tenant=tenant)
                people = people.filter(tenant=tenant)

            orgs = list(organizations.order_by("id"))
            persons = list(people.order_by("id"))
            if len(orgs) != 1 or len(persons) != 1:
                errors.append(
                    f"{organization_name} :: {person_name} resolved orgs={len(orgs)} persons={len(persons)}"
                )
                continue

            matches = list(
                OrganizationPerson.objects.filter(
                    organization=orgs[0],
                    person=persons[0],
                    status="ACTIVE",
                )
                .select_related("organization", "person")
                .order_by("id")
            )
            if tenant:
                matches = [link for link in matches if link.tenant_id == tenant.id]
            if len(matches) != 1:
                errors.append(
                    f"{organization_name} :: {person_name} resolved active links={len(matches)}"
                )
                continue
            links.append(matches[0])

        if errors:
            raise CommandError(
                "Exception links were not resolved uniquely. No changes were applied.\n"
                + "\n".join(f"- {line}" for line in errors)
            )
        return links

    def _get_tenant(self, value: str) -> Tenant:
        if value.isdigit():
            return Tenant.objects.get(id=int(value))
        return Tenant.objects.get(slug=value)
