from __future__ import annotations

from collections import Counter
import json
from time import perf_counter

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from crm.models import Organization
from crm.services.images.projection import (
    prefetch_public_image_projection,
    project_public_image,
)


class Command(BaseCommand):
    help = "Audit the read-only phase 3E.2 projection for the published catalog."

    def handle(self, *args, **options):
        if not settings.PUBLIC_IMAGE_PROJECTION_ENABLED:
            raise CommandError("PUBLIC_IMAGE_PROJECTION_ENABLED must be enabled.")

        started = perf_counter()
        reason_counts: Counter[str] = Counter()
        counts = Counter()
        authorize_count = 0
        queryset = prefetch_public_image_projection(
            Organization.objects.filter(is_published=True).order_by("pk")
        )

        query_count = 0

        def count_query(execute, sql, params, many, context):
            nonlocal query_count
            query_count += 1
            return execute(sql, params, many, context)

        with connection.execute_wrapper(count_query):
            organizations = tuple(queryset)
            for organization in organizations:
                result = project_public_image(organization)
                projection = result.projection
                projected_square = projection.square.url
                legacy_thumbnail = organization.get_public_image_url()
                legacy_preview = organization.get_preview_image_url()

                counts[projection.kind] += 1
                reason_counts[result.reason] += 1
                authorize_count += result.authorize_count
                counts[
                    "legacy_thumbnail_equal"
                    if legacy_thumbnail == projected_square
                    else "legacy_thumbnail_different"
                ] += 1
                counts[
                    "legacy_preview_equal"
                    if legacy_preview == projected_square
                    else "legacy_preview_different"
                ] += 1

        payload = {
            "published_organizations": len(organizations),
            "asset": counts["asset"],
            "system_fallback": counts["system_fallback"],
            "no_release": reason_counts["release_missing"],
            "safety_unavailable": reason_counts["safety_unavailable"],
            "scope_mismatch": sum(
                reason_counts[reason]
                for reason in (
                    "selection_scope_mismatch",
                    "release_scope_inactive",
                    "release_mapping_invalid",
                )
            ),
            "legacy_thumbnail_equal": counts["legacy_thumbnail_equal"],
            "legacy_thumbnail_different": counts["legacy_thumbnail_different"],
            "legacy_preview_equal": counts["legacy_preview_equal"],
            "legacy_preview_different": counts["legacy_preview_different"],
            "authorize_count": authorize_count,
            "query_count": query_count,
            "runtime_ms": round((perf_counter() - started) * 1000, 3),
            "reasons": dict(sorted(reason_counts.items())),
        }
        self.stdout.write(json.dumps(payload, sort_keys=True, separators=(",", ":")))
