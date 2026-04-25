from django.core.management.base import BaseCommand

from crm.models import Organization
from crm.services.open_graph import refresh_organization_open_graph


class Command(BaseCommand):
    help = "Refresh Open Graph preview metadata for organizations."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", type=int, default=None)
        parser.add_argument("--published-only", action="store_true")
        parser.add_argument("--force", action="store_true")

    def handle(self, *args, **options):
        qs = Organization.objects.all().order_by("id")
        tenant_id = options.get("tenant_id")
        if tenant_id is not None:
            qs = qs.filter(tenant_id=tenant_id)
        if options.get("published_only"):
            qs = qs.filter(is_published=True)

        total = qs.count()
        self.stdout.write(f"Refreshing metadata for {total} organizations")

        for org in qs:
            refresh_organization_open_graph(org, force=options.get("force", False))
            self.stdout.write(f" - {org.id}: {org.name}")

        self.stdout.write(self.style.SUCCESS("Done"))
