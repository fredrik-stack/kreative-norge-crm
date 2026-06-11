from __future__ import annotations

from dataclasses import dataclass
from copy import deepcopy

from django.db import transaction
from django.utils import timezone

from crm.models import (
    Category,
    InternalTag,
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
from .matchers import match_organization
from .normalizers import normalize_domain, normalize_name, normalize_public_url, normalize_subcategory_name, parse_bool


class ImportCommitBlocked(Exception):
    pass


@dataclass
class ResolvedRowDecision:
    organization_id: int | None = None
    organization_ids: list[int] | None = None
    person_id: int | None = None
    skip: bool = False
    category_ids: list[int] | None = None
    subcategory_ids: list[int] | None = None
    accepted_ai_suggestions: dict[str, object] | None = None
    ignored_ai_suggestions: set[str] | None = None
    manual_review_overrides: dict[str, object] | None = None


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
    result = ResolvedRowDecision(
        category_ids=[],
        subcategory_ids=[],
        organization_ids=[],
        accepted_ai_suggestions={},
        ignored_ai_suggestions=set(),
        manual_review_overrides={},
    )
    for decision in row.decisions.all():
        payload = decision.payload_json or {}
        if decision.decision_type == ImportDecision.DecisionType.USE_EXISTING_ORGANIZATION:
            organization_id = payload.get("organization_id")
            if organization_id and organization_id not in result.organization_ids:
                result.organization_ids.append(organization_id)
            result.organization_id = result.organization_ids[0] if result.organization_ids else None
        elif decision.decision_type == ImportDecision.DecisionType.USE_EXISTING_PERSON:
            result.person_id = payload.get("person_id")
        elif decision.decision_type == ImportDecision.DecisionType.SKIP_ROW:
            result.skip = True
        elif decision.decision_type == ImportDecision.DecisionType.MAP_CATEGORY and payload.get("category_id"):
            result.category_ids.append(payload["category_id"])
        elif decision.decision_type == ImportDecision.DecisionType.MAP_SUBCATEGORY and payload.get("subcategory_id"):
            result.subcategory_ids.append(payload["subcategory_id"])
        elif decision.decision_type == ImportDecision.DecisionType.ACCEPT_AI_SUGGESTION and payload.get("suggestion_key"):
            suggestion_key = payload["suggestion_key"]
            if payload.get("manual_override"):
                result.manual_review_overrides[suggestion_key] = payload.get("value")
                result.accepted_ai_suggestions[suggestion_key] = payload.get("value")
            elif suggestion_key != "organization_is_published":
                result.accepted_ai_suggestions[suggestion_key] = payload.get("value")
        elif decision.decision_type == ImportDecision.DecisionType.IGNORE_AI_SUGGESTION and payload.get("suggestion_key"):
            result.ignored_ai_suggestions.add(payload["suggestion_key"])
    return result


def _apply_accepted_ai_suggestions(row: ImportRow, normalized_payload: dict, resolved: ResolvedRowDecision) -> dict:
    payload = deepcopy(normalized_payload)
    accepted = resolved.accepted_ai_suggestions or {}
    manual_overrides = resolved.manual_review_overrides or {}
    for suggestion_key, value in accepted.items():
        if suggestion_key == "organization_name":
            payload["organization"]["name"] = value or ""
            payload["organization"]["normalized_name"] = normalize_name(value or "")
        elif suggestion_key == "organization_org_number":
            payload["organization"]["org_number"] = value or ""
        elif suggestion_key == "person_full_name":
            payload["person"]["full_name"] = value or ""
            payload["person"]["normalized_full_name"] = normalize_name(value or "")
        elif suggestion_key == "organization_email":
            payload["organization"]["email"] = value or ""
        elif suggestion_key == "organization_municipalities":
            payload["organization"]["municipalities"] = value or ""
        elif suggestion_key == "person_title":
            payload["person"]["title"] = value or ""
        elif suggestion_key == "person_email":
            payload["person"]["email"] = value or ""
        elif suggestion_key == "person_secondary_emails":
            values = [item.strip() for item in str(value or "").split(",") if item.strip()]
            non_email_contacts = [
                contact
                for contact in payload["person"]["secondary_contacts"]
                if contact.get("type") != "EMAIL"
            ]
            payload["person"]["secondary_contacts"] = non_email_contacts + [
                {"type": "EMAIL", "value": item, "is_public": False}
                for item in values
            ]
        elif suggestion_key == "person_email_conflict_strategy":
            payload["person"]["email_conflict_strategy"] = str(value or "").strip() or "ADD_AS_SECONDARY"
        elif suggestion_key == "person_municipality":
            payload["person"]["municipality"] = value or ""
        elif suggestion_key == "organization_website_url":
            normalized_url = normalize_public_url(value)
            payload["organization"]["website_url"] = normalized_url
            payload["organization"]["website_domain"] = normalize_domain(normalized_url)
        elif suggestion_key == "organization_instagram_url":
            payload["organization"]["instagram_url"] = normalize_public_url(value)
        elif suggestion_key == "organization_tiktok_url":
            payload["organization"]["tiktok_url"] = normalize_public_url(value)
        elif suggestion_key == "organization_linkedin_url":
            payload["organization"]["linkedin_url"] = normalize_public_url(value)
        elif suggestion_key == "organization_facebook_url":
            payload["organization"]["facebook_url"] = normalize_public_url(value)
        elif suggestion_key == "organization_youtube_url":
            payload["organization"]["youtube_url"] = normalize_public_url(value)
        elif suggestion_key == "organization_description":
            payload["organization"]["description"] = value or ""
        elif suggestion_key == "organization_is_published" and suggestion_key in manual_overrides:
            payload["organization"]["is_published"] = parse_bool(value, default=False)
        elif suggestion_key == "person_website_url":
            payload["person"]["website_url"] = normalize_public_url(value)
        elif suggestion_key == "person_instagram_url":
            payload["person"]["instagram_url"] = normalize_public_url(value)
        elif suggestion_key == "person_tiktok_url":
            payload["person"]["tiktok_url"] = normalize_public_url(value)
        elif suggestion_key == "person_linkedin_url":
            payload["person"]["linkedin_url"] = normalize_public_url(value)
        elif suggestion_key == "person_facebook_url":
            payload["person"]["facebook_url"] = normalize_public_url(value)
        elif suggestion_key == "person_youtube_url":
            payload["person"]["youtube_url"] = normalize_public_url(value)
        elif suggestion_key == "suggested_tags" and isinstance(value, list):
            if row.import_job.import_mode == ImportJob.ImportMode.ORGANIZATIONS_ONLY:
                combined_tags = payload["organization"]["tags"] + [str(item) for item in value]
                target_key = "organization"
            elif row.import_job.import_mode == ImportJob.ImportMode.PEOPLE_ONLY:
                combined_tags = payload["person"]["tags"] + [str(item) for item in value]
                target_key = "person"
            else:
                combined_tags = payload["organization"]["tags"] + payload["person"]["tags"] + [str(item) for item in value]
                target_key = "combined"
            seen = set()
            unique_tags = []
            for tag in combined_tags:
                key = tag.strip().casefold()
                if not key or key in seen:
                    continue
                seen.add(key)
                unique_tags.append(tag.strip())
            if target_key in {"organization", "combined"}:
                payload["organization"]["tags"] = unique_tags
            if target_key in {"person", "combined"}:
                payload["person"]["tags"] = unique_tags
        elif suggestion_key == "organization_internal_tags" and isinstance(value, list):
            payload["organization"]["internal_tags"] = [str(item).strip() for item in value if str(item).strip()]
        elif suggestion_key == "person_internal_tags" and isinstance(value, list):
            payload["person"]["internal_tags"] = [str(item).strip() for item in value if str(item).strip()]
        elif suggestion_key == "suggested_categories" and isinstance(value, list):
            if row.import_job.import_mode == ImportJob.ImportMode.ORGANIZATIONS_ONLY:
                payload["organization"]["categories"] = [str(item) for item in value]
            elif row.import_job.import_mode == ImportJob.ImportMode.PEOPLE_ONLY:
                payload["person"]["categories"] = [str(item) for item in value]
            else:
                payload["organization"]["categories"] = [str(item) for item in value]
                payload["person"]["categories"] = [str(item) for item in value]
        elif suggestion_key == "suggested_subcategories" and isinstance(value, list):
            if row.import_job.import_mode == ImportJob.ImportMode.ORGANIZATIONS_ONLY:
                payload["organization"]["subcategories"] = [str(item) for item in value]
            elif row.import_job.import_mode == ImportJob.ImportMode.PEOPLE_ONLY:
                payload["person"]["subcategories"] = [str(item) for item in value]
            else:
                payload["organization"]["subcategories"] = [str(item) for item in value]
                payload["person"]["subcategories"] = [str(item) for item in value]
    return payload


def _resolve_existing_organization(import_job: ImportJob, organization_data: dict, matches: dict, resolved: ResolvedRowDecision) -> tuple[Organization | None, str | None]:
    organization_id = resolved.organization_id or (matches.get("organization") or {}).get("exact_id")
    if organization_id:
        return Organization.objects.get(id=organization_id, tenant=import_job.tenant), ImportCommitLog.Action.UPDATED

    org_number = organization_data.get("org_number") or None
    if org_number:
        existing = Organization.objects.filter(tenant=import_job.tenant, org_number=org_number).first()
        if existing:
            return existing, ImportCommitLog.Action.UPDATED

    refreshed_matches = match_organization(import_job.tenant, {"organization": organization_data, "person": {"website_url": "", "email": ""}})
    exact_id = (refreshed_matches.get("exact_id") if isinstance(refreshed_matches, dict) else None)
    if exact_id:
        existing = Organization.objects.filter(id=exact_id, tenant=import_job.tenant).first()
        if existing:
            return existing, ImportCommitLog.Action.UPDATED

    return None, None


def _get_or_create_tags(tenant, names: list[str]) -> list[Tag]:
    tags = []
    for name in names:
        tag, _ = Tag.objects.get_or_create(tenant=tenant, name=name)
        tags.append(tag)
    return tags


def _get_or_create_internal_tags(tenant, names: list[str]) -> list[InternalTag]:
    tags = []
    for name in names:
        tag, _ = InternalTag.objects.get_or_create(tenant=tenant, name=name)
        tags.append(tag)
    return tags


def _resolve_categories(names: list[str], mapped_ids: list[int] | None = None) -> list[Category]:
    if mapped_ids:
        return list(Category.objects.filter(id__in=mapped_ids).distinct())
    queryset = Category.objects.none()
    if names:
        queryset = queryset | Category.objects.filter(name__in=names)
    return list(queryset.distinct())


def _resolve_subcategories(names: list[str], mapped_ids: list[int] | None = None) -> list[Subcategory]:
    if mapped_ids:
        return list(Subcategory.objects.filter(id__in=mapped_ids).distinct())
    normalized_names = {normalize_subcategory_name(name) for name in names if normalize_subcategory_name(name)}
    if not normalized_names:
        return []
    return [
        subcategory
        for subcategory in Subcategory.objects.select_related("category").all()
        if normalize_subcategory_name(subcategory.name) in normalized_names
    ]


def _has_taxonomy_updates(names: list[str], mapped_ids: list[int] | None = None) -> bool:
    return bool(names or mapped_ids)


def _should_apply_taxonomy_update(
    names: list[str],
    mapped_ids: list[int] | None,
    resolved_items: list[Category] | list[Subcategory],
) -> bool:
    if mapped_ids:
        return True
    if resolved_items:
        return True
    return False


def _get_primary_contact(person: Person, contact_type: str):
    return PersonContact.objects.filter(person=person, tenant=person.tenant, type=contact_type, is_primary=True).first()


def _upsert_primary_person_contact(
    person: Person,
    *,
    contact_type: str,
    value: str,
    row: ImportRow,
    job: ImportJob,
    overwrite_existing_primary: bool = True,
):
    if not value:
        return

    primary = _get_primary_contact(person, contact_type)
    scalar_field = "email" if contact_type == "EMAIL" else "phone"
    scalar_value = getattr(person, scalar_field, None)
    if primary:
        if primary.value.casefold() == value.casefold():
            if primary.is_public:
                primary.is_public = False
                primary.save(update_fields=["is_public"])
                _log(
                    job,
                    row,
                    ImportCommitLog.EntityType.PERSON_CONTACT,
                    primary.id,
                    ImportCommitLog.Action.UPDATED,
                    {"type": contact_type, "primary": True},
                )
            return
        if overwrite_existing_primary:
            primary.value = value
            primary.is_public = False
            primary.save(update_fields=["value", "is_public"])
            _log(
                job,
                row,
                ImportCommitLog.EntityType.PERSON_CONTACT,
                primary.id,
                ImportCommitLog.Action.UPDATED,
                {"type": contact_type, "primary": True},
            )
            return
        secondary, created = PersonContact.objects.get_or_create(
            tenant=person.tenant,
            person=person,
            type=contact_type,
            value=value,
            defaults={"is_primary": False, "is_public": False},
        )
        if not created and secondary.is_public:
            secondary.is_public = False
            secondary.save(update_fields=["is_public"])
        _log(
            job,
            row,
            ImportCommitLog.EntityType.PERSON_CONTACT,
            secondary.id,
            ImportCommitLog.Action.CREATED if created else ImportCommitLog.Action.UPDATED,
            {"type": contact_type, "primary": False},
        )
        return

    if scalar_value and scalar_value.casefold() != value.casefold() and not overwrite_existing_primary:
        secondary, created = PersonContact.objects.get_or_create(
            tenant=person.tenant,
            person=person,
            type=contact_type,
            value=value,
            defaults={"is_primary": False, "is_public": False},
        )
        if not created and secondary.is_public:
            secondary.is_public = False
            secondary.save(update_fields=["is_public"])
        _log(
            job,
            row,
            ImportCommitLog.EntityType.PERSON_CONTACT,
            secondary.id,
            ImportCommitLog.Action.CREATED if created else ImportCommitLog.Action.UPDATED,
            {"type": contact_type, "primary": False},
        )
        return

    primary = PersonContact.objects.create(
        tenant=person.tenant,
        person=person,
        type=contact_type,
        value=value,
        is_primary=True,
        is_public=False,
    )
    _log(job, row, ImportCommitLog.EntityType.PERSON_CONTACT, primary.id, ImportCommitLog.Action.CREATED, {"type": contact_type, "primary": True})


def _upsert_person_contacts(person: Person, data: dict, row: ImportRow, job: ImportJob, *, explicit_existing_person: bool = False):
    email_conflict_strategy = str(data.get("email_conflict_strategy") or "ADD_AS_SECONDARY").strip().upper()
    overwrite_email_primary = email_conflict_strategy == "REPLACE_PRIMARY" and data["email"]
    overwrite_phone_primary = not explicit_existing_person

    _upsert_primary_person_contact(
        person,
        contact_type="EMAIL",
        value=data["email"],
        row=row,
        job=job,
        overwrite_existing_primary=overwrite_email_primary,
    )
    _upsert_primary_person_contact(
        person,
        contact_type="PHONE",
        value=data["phone"],
        row=row,
        job=job,
        overwrite_existing_primary=overwrite_phone_primary,
    )

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

    updated_fields: list[str] = []
    primary_email = _get_primary_contact(person, "EMAIL")
    primary_phone = _get_primary_contact(person, "PHONE")
    next_email = primary_email.value if primary_email else (person.email or None)
    next_phone = primary_phone.value if primary_phone else (person.phone or None)
    if person.email != next_email:
        person.email = next_email
        updated_fields.append("email")
    if person.phone != next_phone:
        person.phone = next_phone
        updated_fields.append("phone")
    if updated_fields:
        person.save(update_fields=updated_fields)


def commit_import_job(import_job: ImportJob, *, skip_unresolved: bool = False) -> ImportJob:
    if import_job.status not in {
        ImportJob.Status.PREVIEW_READY,
        ImportJob.Status.AWAITING_REVIEW,
        ImportJob.Status.FAILED,
    }:
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
                org_internal_tags = _get_or_create_internal_tags(import_job.tenant, organization_data["internal_tags"])
                person_internal_tags = _get_or_create_internal_tags(import_job.tenant, person_data["internal_tags"])

                organization = None
                organization_action = None
                explicit_existing_organization_ids = [organization_id for organization_id in (resolved.organization_ids or []) if organization_id]
                explicit_existing_organization = bool(explicit_existing_organization_ids)
                organization, organization_action = _resolve_existing_organization(import_job, organization_data, matches, resolved)
                if not organization and organization_data["name"]:
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
                if organization and organization_action == ImportCommitLog.Action.UPDATED and not explicit_existing_organization:
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
                explicit_existing_person = resolved.person_id is not None
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
                if person and person_action == ImportCommitLog.Action.UPDATED and not explicit_existing_person:
                    for field, value in {
                        "full_name": person_data["full_name"],
                        "title": person_data["title"] or None,
                        "email": person.email or person_data["email"] or None,
                        "phone": person.phone or person_data["phone"] or None,
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
                    _upsert_person_contacts(
                        person,
                        person_data,
                        row,
                        import_job,
                        explicit_existing_person=explicit_existing_person,
                    )

                linked_organizations: list[Organization] = []
                if explicit_existing_organization_ids:
                    linked_organizations = list(
                        Organization.objects.filter(
                            tenant=import_job.tenant,
                            id__in=explicit_existing_organization_ids,
                        )
                    )
                elif organization:
                    linked_organizations = [organization]

                if person:
                    for linked_organization in linked_organizations:
                        link, created = OrganizationPerson.objects.get_or_create(
                            tenant=import_job.tenant,
                            organization=linked_organization,
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
                            {"organization_id": linked_organization.id},
                        )

                if organization:
                    if not explicit_existing_organization:
                        organization.tags.set(org_tags)
                        organization.internal_tags.set(org_internal_tags)
                        resolved_categories = _resolve_categories(organization_data["categories"], resolved.category_ids)
                        resolved_subcategories = _resolve_subcategories(organization_data["subcategories"], resolved.subcategory_ids)
                        if organization_action == ImportCommitLog.Action.CREATED or _should_apply_taxonomy_update(
                            organization_data["categories"],
                            resolved.category_ids,
                            resolved_categories,
                        ):
                            organization.categories.set(resolved_categories)
                        if organization_action == ImportCommitLog.Action.CREATED or _should_apply_taxonomy_update(
                            organization_data["subcategories"],
                            resolved.subcategory_ids,
                            resolved_subcategories,
                        ):
                            organization.subcategories.set(resolved_subcategories)
                if person:
                    if not explicit_existing_person:
                        person.tags.set(person_tags)
                        person.internal_tags.set(person_internal_tags)
                        resolved_categories = _resolve_categories(person_data["categories"], resolved.category_ids)
                        resolved_subcategories = _resolve_subcategories(person_data["subcategories"], resolved.subcategory_ids)
                        if person_action == ImportCommitLog.Action.CREATED or _should_apply_taxonomy_update(
                            person_data["categories"],
                            resolved.category_ids,
                            resolved_categories,
                        ):
                            person.categories.set(resolved_categories)
                        if person_action == ImportCommitLog.Action.CREATED or _should_apply_taxonomy_update(
                            person_data["subcategories"],
                            resolved.subcategory_ids,
                            resolved_subcategories,
                        ):
                            person.subcategories.set(resolved_subcategories)

                if organization and not explicit_existing_organization and organization.get_primary_link():
                    refresh_organization_open_graph(organization, force=True)

                row.row_status = ImportRow.RowStatus.COMMITTED
                row.save(update_fields=["row_status", "updated_at"])

            import_job.status = ImportJob.Status.COMPLETED
            import_job.committed_at = timezone.now()
            logs = list(import_job.commit_logs.all())
            committed_rows = import_job.rows.filter(row_status=ImportRow.RowStatus.COMMITTED).count()
            skipped_rows = import_job.rows.filter(row_status=ImportRow.RowStatus.SKIPPED).count()
            failed_rows = import_job.rows.filter(row_status=ImportRow.RowStatus.COMMIT_FAILED).count()
            import_job.summary_json = {
                **(import_job.summary_json or {}),
                "committed_rows": committed_rows,
                "rows_skipped": skipped_rows,
                "rows_failed": failed_rows,
                "review_required_rows": 0,
                "invalid_rows": 0,
                "valid_rows": committed_rows,
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
