from __future__ import annotations

from django.db import transaction

from crm.models import Organization, OrganizationPerson
from crm.services.open_graph import refresh_organization_open_graph


SCALAR_FILL_FIELDS = (
    "org_number",
    "email",
    "phone",
    "municipalities",
    "note",
    "description",
    "website_url",
    "facebook_url",
    "instagram_url",
    "tiktok_url",
    "linkedin_url",
    "youtube_url",
    "thumbnail_image_url",
)


def merge_organization_into(*, source: Organization, target: Organization) -> Organization:
    if source.pk == target.pk:
        raise ValueError("Source and target organizations must differ.")
    if source.tenant_id != target.tenant_id:
        raise ValueError("Source and target organizations must belong to the same tenant.")

    with transaction.atomic():
        changed_fields: set[str] = set()

        for field_name in SCALAR_FILL_FIELDS:
            source_value = getattr(source, field_name, None)
            target_value = getattr(target, field_name, None)
            if target_value in (None, "") and source_value not in (None, ""):
                setattr(target, field_name, source_value)
                changed_fields.add(field_name)

        merged_is_published = bool(target.is_published or source.is_published)
        if merged_is_published != target.is_published:
            target.is_published = merged_is_published
            changed_fields.add("is_published")

        merged_publish_phone = bool(target.publish_phone or source.publish_phone)
        if merged_publish_phone != target.publish_phone:
            target.publish_phone = merged_publish_phone
            changed_fields.add("publish_phone")

        if changed_fields:
            target.save(update_fields=sorted(changed_fields | {"updated_at"}))

        target.tags.add(*source.tags.all())
        target.internal_tags.add(*source.internal_tags.all())
        target.categories.add(*source.categories.all())
        target.subcategories.add(*source.subcategories.all())

        for link in source.org_people.select_related("person").all():
            existing = OrganizationPerson.objects.filter(
                tenant=target.tenant,
                organization=target,
                person=link.person,
            ).first()
            if existing:
                updated = False
                if existing.status != "ACTIVE" and link.status == "ACTIVE":
                    existing.status = "ACTIVE"
                    updated = True
                if not existing.publish_person and link.publish_person:
                    existing.publish_person = True
                    updated = True
                if updated:
                    existing.save(update_fields=["status", "publish_person"])
                link.delete()
                continue

            link.organization = target
            link.save(update_fields=["organization"])

        source.delete()
        refresh_organization_open_graph(target, force=True)
        target.refresh_from_db()
        return target
