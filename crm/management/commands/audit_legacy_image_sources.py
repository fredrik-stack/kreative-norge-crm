from __future__ import annotations

import json

from django.core.management.base import BaseCommand

from crm.services.images.legacy_inventory import audit_legacy_image_sources


class Command(BaseCommand):
    help = "Audit stored legacy image sources without network access or writes."

    def add_arguments(self, parser):
        parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Include organization IDs and URLs with every query value redacted.",
        )

    def handle(self, *args, **options):
        inventory, details = audit_legacy_image_sources(verbose=options["verbose"])
        payload = {"inventory": inventory.as_dict()}
        if options["verbose"]:
            payload["details"] = details
        if options["json"]:
            self.stdout.write(json.dumps(payload, sort_keys=True))
            return
        self.stdout.write("audit_legacy_image_sources mode=READ-ONLY")
        for key, value in inventory.as_dict().items():
            self.stdout.write(f"{key}={value}")
        if details:
            self.stdout.write(json.dumps({"details": details}, sort_keys=True))
