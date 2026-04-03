from __future__ import annotations

from dataclasses import dataclass
from copy import deepcopy

from django.db import transaction
from django.utils import timezone

from crm.models import (
    Category,
    ImportCommitLog,
    ImportDecision,
    ImportJob,
    ImportRow,
    Organization,
    OrganizationPerson,
    Person,
    PersonContact,
    Subcategory,
    Tag,
)
from crm.services.open_graph import refresh_organization_open_graph


class ImportCommitBlocked(Exception):
    pass


@dataclass
class ResolvedRowDecision:
    organization_id: int | None = None
    person_id: int | None = None
    skip: bool = False
    category_ids: list[int] | None = None
    subcategory_ids: list[int] | None = None
    accepted_ai_suggestions: dict[str, object] | None = None
    ignored_ai_suggestions: set[str] | None = None


def _log(job, row, entity_type, entity_id, action, details_json):
    ImportCommitLog.objects.create(
        import_job=job,
        import_row=row,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        details_json=details_json or {},
    )


def _resolve_decisions(row: ImportRow) -> ResolvedRowDecision:
    result = ResolvedRowDecision(category_ids=[], subcategory_ids=[], accepted_ai_suggestions={}, ignored_ai_suggestions=set())
    for decision in row.decisions.all():
        payload = decision.payload_json or {}
        if decision.decision_type == ImportDecision.DecisionType.USE_EXISTING_ORGANIZATION:
            result.organization_id = payload.get("organization_id")
        elif decision.decision_type == ImportDecision.DecisionType.USE_EXISTING_PERSON:
            result.person_id = payload.get("person_id")
        elif decision.decision_type == ImportDecision.DecisionType.SKIP_ROW:
            result.skip = True
        elif decision.decision_type == ImportDecision.DecisionType.MAP_CATEGORY and payload.get("category_id"):
            result.category_ids.append(payload["category_id"])
        elif decision.decision_type == ImportDecision.DecisionType.MAP_SUBCATEGORY and payload.get("subcategory_id"):
            result.subcategory_ids.append(payload["subcategory_id"])
        elif decision.decision_type == ImportDecision.DecisionType.ACCEPT_AI_SUGGESTION and payload.get("suggestion_key"):
            result.accepted_ai_suggestions[payload["suggestion_key"]] = payload.get("value")
        elif decision.decision_type == ImportDecision.DecisionType.IGNORE_AI_SUGGESTION and payload.get("suggestion_key"):
            result.ignored_ai_suggestions.add(payload["suggestion_key"])
    return result


def _apply_accepted_ai_suggestions(row: ImportRow, normalized_payload: dict, resolved: ResolvedRowDecision) -> dict:
    payload = deepcopy(normalized_payload)
    accepted = resolved.accepted_ai_suggestions or {}
    for suggestion_key, value in accepted.items():
        if suggestion_key == "organization_name":
            payload["organization"]["name"] = value or ""
        elif suggestion_key == "person_full_name":
            payload["person"]["full_name"] = value or ""
        elif suggestion_key == "organization_website_url":
            payload["organization"]["website_url"] = value or ""
        elif suggestion_key == "organization_description":
            payload["organization"]["description"] = value or ""
        elif suggestion_key == "suggested_tags" and isinstance(value, list):
            combined_tags = payload["organization"]["tags"] + payload["person"]["tags"] + [str(item) for item in value]
            seen = set()
            unique_tags = []
            for tag in combined_tags:
                key = tag.strip().casefold()
                if not key or key in seen:
                    continue
                seen.add(key)
                unique_tags.append(tag.strip())
            payload["organization"]["tags"] = unique_tags
            payload["person"]["tags"] = unique_tags
        elif suggestion_key == "suggested_categories" and isinstance(value, list):
            payload["organization"]["categories"] = [str(item) for item in value]
            payload["person"]["categories"] = [str(item) for item in value]
        elif suggestion_key == "suggested_subcategories" and isinstance(value, list):
            payload["organization"]["subcategories"] = [str(item) for item in value]
            payload["person"]["subcategories"] = [str(item) for item in value]
    return payload


def _get_or_create_tags(tenant, names: list[str]) -> list[Tag]:
    tags = []
    for name in names:
        tag, _ = Tag.objects.get_or_create(tenant=tenant, name=name)
        tags.append(tag)
    return tags


def _resolve_categories(names: list[str], mapped_ids: list[int] | None = None) -> list[Category]:
    queryset = Category.objects.none()
    if names:
        queryset = queryset | Category.objects.filter(name__in=names)
    if mapped_ids:
        queryset = queryset | Category.objects.filter(id__in=mapped_ids)
    return list(queryset.distinct())


def _resolve_subcategories(names: list[str], mapped_ids: list[int] | None = None) -> list[Subcategory]:
    queryset = Subcategory.objects.none()
    if names:
        queryset = queryset | Subcategory.objects.filter(name__in=names)
    if mapped_ids:
        queryset = queryset | Subcategory.objects.filter(id__in=mapped_ids)
    return list(queryset.distinct())


def _get_primary_contact(person: Person, contact_type: str):
    return PersonContact.objects.filter(person=person, tenant=person.tenant, type=contact_type, is_primary=True).first()


def _upsert_person_contacts(person: Person, data: dict, row: ImportRow, job: ImportJob):
    if data["email"]:
        primary = _get_primary_contact(person, "EMAIL")
        if primary:
            primary.value = data["email"]
            primary.is_public = False
            primary.save(update_fields=["value", "is_public"])
            _log(job, row, ImportCommitLog.EntityType.PERSON_CONTACT, primary.id, ImportCommitLog.Action.UPDATED, {"type": "EMAIL", "primary": True})
        else:
            primary = PersonContact.objects.create(
                tenant=person.tenant,
                person=person,
                type="EMAIL",
                value=data["email"],
                is_primary=True,
                is_public=False,
            )
            _log(job, row, ImportCommitLog.EntityType.PERSON_CONTACT, primary.id, ImportCommitLog.Action.CREATED, {"type": "EMAIL", "primary": True})

    if data["phone"]:
        primary = _get_primary_contact(person, "PHONE")
        if primary:
            primary.value = data["phone"]
            primary.is_public = False
            primary.save(update_fields=["value", "is_public"])
            _log(job, row, ImportCommitLog.EntityType.PERSON_CONTACT, primary.id, ImportCommitLog.Action.UPDATED, {"type": "PHONE", "primary": True})
        else:
            primary = PersonContact.objects.create(
                tenant=person.tenant,
                person=person,
                type="PHONE",
                value=data["phone"],
                is_primary=True,
                is_public=False,
            )
            _log(job, row, ImportCommitLog.EntityType.PERSON_CONTACT, primary.id, ImportCommitLog.Action.CREATED, {"type": "PHONE", "primary": True})

    for contact in data["secondary_contacts"]:
        secondary, created = PersonContact.objects.get_or_create(
            tenant=person.tenant,
            person=person,
            type=contact["type"],
            value=contact["value"],
            defaults={"is_primary": False, "is_public": contact["is_public"]},
        )
        if not created and secondary.is_public != contact["is_public"]:
            secondary.is_public = contact["is_public"]
            secondary.save(update_fields=["is_public"])
        _log(
            job,
            row,
            ImportCommitLog.EntityType.PERSON_CONTACT,
            secondary.id,
            ImportCommitLog.Action.CREATED if created else ImportCommitLog.Action.UPDATED,
            {"type": contact["type"], "primary": False},
        )


def commit_import_job(import_job: ImportJob, *, skip_unresolved: bool = False) -> ImportJob:
    if import_job.status not in {ImportJob.Status.PREVIEW_READY, ImportJob.Status.AWAITING_REVIEW}:
        raise ImportCommitBlocked("Import job must be previewed before commit.")

    unresolved = import_job.rows.filter(row_status=ImportRow.RowStatus.REVIEW_REQUIRED)
    if unresolved.exists() and not skip_unresolved:
        raise ImportCommitBlocked("Import job has unresolved review rows.")

    import_job.status = ImportJob.Status.COMMITTING
    import_job.save(update_fields=["status", "updated_at"])

    rows = list(import_job.rows.all().prefetch_related("decisions"))
    try:
        with transaction.atomic():
            import_job.commit_logs.all().delete()

            for row in rows:
                resolved = _resolve_decisions(row)
                if row.row_status == ImportRow.RowStatus.INVALID or resolved.skip:
                    row.row_status = ImportRow.RowStatus.SKIPPED
                    row.proposed_action = ImportRow.ProposedAction.SKIP
                    row.save(update_fields=["row_status", "proposed_action", "updated_at"])
                    _log(import_job, row, ImportCommitLog.EntityType.TAG, None, ImportCommitLog.Action.SKIPPED, {"reason": "row skipped"})
                    continue
                if row.row_status == ImportRow.RowStatus.REVIEW_REQUIRED and skip_unresolved:
                    row.row_status = ImportRow.RowStatus.SKIPPED
                    row.proposed_action = ImportRow.ProposedAction.SKIP
                    row.save(update_fields=["row_status", "proposed_action", "updated_at"])
                    _log(import_job, row, ImportCommitLog.EntityType.TAG, None, ImportCommitLog.Action.SKIPPED, {"reason": "unresolved review skipped"})
                    continue

                normalized = _apply_accepted_ai_suggestions(row, row.normalized_payload_json, resolved)
                organization_data = normalized["organization"]
                person_data = normalized["person"]
                link_data = normalized["link"]
                matches = row.match_result_json or {}
                org_tags = _get_or_create_tags(import_job.tenant, organization_data["tags"])
                person_tags = _get_or_create_tags(import_job.tenant, person_data["tags"])

                organization = None
                organization_action = None
                organization_id = resolved.organization_id or (matches.get("organization") or {}).get("exact_id")
                if organization_id:
                    organization = Organization.objects.get(id=organization_id, tenant=import_job.tenant)
                    organization_action = ImportCommitLog.Action.UPDATED
                elif organization_data["name"]:
                    organization = Organization.objects.create(
                        tenant=import_job.tenant,
                        name=organization_data["name"],
                        org_number=organization_data["org_number"] or None,
                        email=organization_data["email"] or None,
                        phone=organization_data["phone"] or None,
                        municipalities=organization_data["municipalities"],
                        description=organization_data["description"] or None,
                        note=organization_data["note"] or None,
                        is_published=organization_data["is_published"],
                        publish_phone=organization_data["publish_phone"],
                        website_url=organization_data["website_url"] or None,
                        instagram_url=organization_data["instagram_url"] or None,
                        tiktok_url=organization_data["tiktok_url"] or None,
                        linkedin_url=organization_data["linkedin_url"] or None,
                        facebook_url=organization_data["facebook_url"] or None,
                        youtube_url=organization_data["youtube_url"] or None,
                    )
                    organization_action = ImportCommitLog.Action.CREATED
                if organization and organization_action == ImportCommitLog.Action.UPDATED:
                    for field, value in {
                        "name": organization_data["name"],
                        "org_number": organization_data["org_number"] or None,
                        "email": organization_data["email"] or None,
                        "phone": organization_data["phone"] or None,
                        "municipalities": organization_data["municipalities"],
                        "description": organization_data["description"] or None,
                        "note": organization_data["note"] or None,
                        "is_published": organization_data["is_published"],
                        "publish_phone": organization_data["publish_phone"],
                        "website_url": organization_data["website_url"] or None,
                        "instagram_url": organization_data["instagram_url"] or None,
                        "tiktok_url": organization_data["tiktok_url"] or None,
                        "linkedin_url": organization_data["linkedin_url"] or None,
                        "facebook_url": organization_data["facebook_url"] or None,
                        "youtube_url": organization_data["youtube_url"] or None,
                    }.items():
                        setattr(organization, field, value)
                    organization.save()
                if organization:
                    _log(import_job, row, ImportCommitLog.EntityType.ORGANIZATION, organization.id, organization_action, {})

                person = None
                person_action = None
                person_id = resolved.person_id or (matches.get("person") or {}).get("exact_id")
                if person_id:
                    person = Person.objects.get(id=person_id, tenant=import_job.tenant)
                    person_action = ImportCommitLog.Action.UPDATED
                elif person_data["full_name"]:
                    person = Person.objects.create(
                        tenant=import_job.tenant,
                        full_name=person_data["full_name"],
                        title=person_data["title"] or None,
                        email=person_data["email"] or None,
                        phone=person_data["phone"] or None,
                        municipality=person_data["municipality"],
                        website_url=person_data["website_url"] or None,
                        instagram_url=person_data["instagram_url"] or None,
                        tiktok_url=person_data["tiktok_url"] or None,
                        linkedin_url=person_data["linkedin_url"] or None,
                        facebook_url=person_data["facebook_url"] or None,
                        youtube_url=person_data["youtube_url"] or None,
                        note=person_data["note"] or None,
                    )
                    person_action = ImportCommitLog.Action.CREATED
                if person and person_action == ImportCommitLog.Action.UPDATED:
                    for field, value in {
                        "full_name": person_data["full_name"],
                        "title": person_data["title"] or None,
                        "email": person_data["email"] or None,
                        "phone": person_data["phone"] or None,
                        "municipality": person_data["municipality"],
                        "website_url": person_data["website_url"] or None,
                        "instagram_url": person_data["instagram_url"] or None,
                        "tiktok_url": person_data["tiktok_url"] or None,
                        "linkedin_url": person_data["linkedin_url"] or None,
                        "facebook_url": person_data["facebook_url"] or None,
                        "youtube_url": person_data["youtube_url"] or None,
                        "note": person_data["note"] or None,
                    }.items():
                        setattr(person, field, value)
                    person.save()
                if person:
                    _log(import_job, row, ImportCommitLog.EntityType.PERSON, person.id, person_action, {})
                    _upsert_person_contacts(person, person_data, row, import_job)

                if organization and person:
                    link, created = OrganizationPerson.objects.get_or_create(
                        tenant=import_job.tenant,
                        organization=organization,
                        person=person,
                        defaults={"status": link_data["status"], "publish_person": link_data["publish_person"]},
                    )
                    if not created:
                        link.status = link_data["status"]
                        link.publish_person = link_data["publish_person"]
                        link.save(update_fields=["status", "publish_person"])
                    _log(
                        import_job,
                        row,
                        ImportCommitLog.EntityType.ORGANIZATION_PERSON,
                        link.id,
                        ImportCommitLog.Action.CREATED if created else ImportCommitLog.Action.LINKED,
                        {},
                    )

                if organization:
                    organization.tags.set(org_tags)
                    organization.categories.set(_resolve_categories(organization_data["categories"], resolved.category_ids))
                    organization.subcategories.set(_resolve_subcategories(organization_data["subcategories"], resolved.subcategory_ids))
                if person:
                    person.tags.set(person_tags)
                    person.categories.set(_resolve_categories(person_data["categories"], resolved.category_ids))
                    person.subcategories.set(_resolve_subcategories(person_data["subcategories"], resolved.subcategory_ids))

                if organization and organization.get_primary_link():
                    refresh_organization_open_graph(organization, force=True)

                row.row_status = ImportRow.RowStatus.COMMITTED
                row.save(update_fields=["row_status", "updated_at"])

            import_job.status = ImportJob.Status.COMPLETED
            import_job.committed_at = timezone.now()
            logs = list(import_job.commit_logs.all())
            import_job.summary_json = {
                **(import_job.summary_json or {}),
                "committed_rows": import_job.rows.filter(row_status=ImportRow.RowStatus.COMMITTED).count(),
                "rows_skipped": import_job.rows.filter(row_status=ImportRow.RowStatus.SKIPPED).count(),
                "rows_failed": import_job.rows.filter(row_status=ImportRow.RowStatus.COMMIT_FAILED).count(),
                "organizations_created": sum(
                    1
                    for log in logs
                    if log.entity_type == ImportCommitLog.EntityType.ORGANIZATION and log.action == ImportCommitLog.Action.CREATED
                ),
                "organizations_updated": sum(
                    1
                    for log in logs
                    if log.entity_type == ImportCommitLog.EntityType.ORGANIZATION and log.action == ImportCommitLog.Action.UPDATED
                ),
                "persons_created": sum(
                    1
                    for log in logs
                    if log.entity_type == ImportCommitLog.EntityType.PERSON and log.action == ImportCommitLog.Action.CREATED
                ),
                "persons_updated": sum(
                    1
                    for log in logs
                    if log.entity_type == ImportCommitLog.EntityType.PERSON and log.action == ImportCommitLog.Action.UPDATED
                ),
                "person_contacts_created": sum(
                    1
                    for log in logs
                    if log.entity_type == ImportCommitLog.EntityType.PERSON_CONTACT and log.action == ImportCommitLog.Action.CREATED
                ),
                "links_created": sum(
                    1
                    for log in logs
                    if log.entity_type == ImportCommitLog.EntityType.ORGANIZATION_PERSON
                    and log.action in {ImportCommitLog.Action.CREATED, ImportCommitLog.Action.LINKED}
                ),
            }
            import_job.save(update_fields=["status", "committed_at", "summary_json", "updated_at"])
    except Exception:
        import_job.status = ImportJob.Status.FAILED
        import_job.save(update_fields=["status", "updated_at"])
        raise

    return import_job
