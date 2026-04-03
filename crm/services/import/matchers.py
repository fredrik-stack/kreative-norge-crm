from __future__ import annotations

from django.db.models import Q

from crm.models import Organization, OrganizationPerson, Person, PersonContact, Tenant
from .normalizers import normalize_domain, normalize_name


def _candidate_payload(queryset, label_field: str) -> list[dict]:
    return [
        {"id": item.id, "label": getattr(item, label_field)}
        for item in queryset[:5]
    ]


def match_organization(tenant: Tenant, normalized_payload: dict) -> dict:
    data = normalized_payload["organization"]
    if not data["name"] and not data["org_number"]:
        return {"status": "NONE", "rule": None, "exact_id": None, "candidates": []}

    queryset = Organization.objects.filter(tenant=tenant)

    if data["org_number"]:
        exact = queryset.filter(org_number=data["org_number"]).first()
        if exact:
            return {"status": "EXACT", "rule": "ORG_NUMBER", "exact_id": exact.id, "candidates": []}

    if data["normalized_name"] and data["website_domain"]:
        for candidate in queryset.exclude(website_url=""):
            if (
                normalize_name(candidate.name) == data["normalized_name"]
                and normalize_domain(candidate.website_url) == data["website_domain"]
            ):
                return {"status": "EXACT", "rule": "NAME_AND_DOMAIN", "exact_id": candidate.id, "candidates": []}

    if data["normalized_name"] and data["municipalities"]:
        normalized_municipality = data["municipalities"].casefold()
        for candidate in queryset.exclude(municipalities=""):
            if (
                normalize_name(candidate.name) == data["normalized_name"]
                and candidate.municipalities.casefold() == normalized_municipality
            ):
                return {"status": "EXACT", "rule": "NAME_AND_MUNICIPALITY", "exact_id": candidate.id, "candidates": []}

    fuzzy = queryset.filter(name__icontains=data["name"]) if data["name"] else queryset.none()
    if fuzzy.exists():
        return {
            "status": "FUZZY",
            "rule": "FUZZY_NAME",
            "exact_id": None,
            "candidates": _candidate_payload(fuzzy, "name"),
        }

    return {"status": "NEW", "rule": None, "exact_id": None, "candidates": []}


def match_person(tenant: Tenant, normalized_payload: dict, organization_match: dict) -> dict:
    data = normalized_payload["person"]
    if not data["full_name"] and not data["email"]:
        return {"status": "NONE", "rule": None, "exact_id": None, "candidates": []}

    queryset = Person.objects.filter(tenant=tenant)

    if data["email"]:
        exact = queryset.filter(email__iexact=data["email"]).first()
        if not exact:
            contact = (
                PersonContact.objects.filter(tenant=tenant, type="EMAIL", value__iexact=data["email"])
                .select_related("person")
                .first()
            )
            exact = contact.person if contact else None
        if exact:
            return {"status": "EXACT", "rule": "EMAIL", "exact_id": exact.id, "candidates": []}

    if data["normalized_full_name"] and organization_match.get("exact_id"):
        link = (
            OrganizationPerson.objects.filter(
                tenant=tenant,
                organization_id=organization_match["exact_id"],
                person__full_name__iexact=data["full_name"],
            )
            .select_related("person")
            .first()
        )
        if link:
            return {"status": "EXACT", "rule": "NAME_AND_ORGANIZATION", "exact_id": link.person_id, "candidates": []}

    if data["normalized_full_name"] and data["municipality"]:
        exact = queryset.filter(
            full_name__iexact=data["full_name"],
            municipality__iexact=data["municipality"],
        ).first()
        if exact:
            return {"status": "EXACT", "rule": "NAME_AND_MUNICIPALITY", "exact_id": exact.id, "candidates": []}

    if data["normalized_full_name"] and data["phone"]:
        exact = queryset.filter(
            Q(full_name__iexact=data["full_name"], phone=data["phone"])
            | Q(full_name__iexact=data["full_name"], contacts__type="PHONE", contacts__value=data["phone"])
        ).distinct().first()
        if exact:
            return {"status": "EXACT", "rule": "NAME_AND_PHONE", "exact_id": exact.id, "candidates": []}

    fuzzy = queryset.filter(full_name__icontains=data["full_name"]) if data["full_name"] else queryset.none()
    if fuzzy.exists():
        return {
            "status": "FUZZY",
            "rule": "FUZZY_NAME",
            "exact_id": None,
            "candidates": _candidate_payload(fuzzy, "full_name"),
        }

    return {"status": "NEW", "rule": None, "exact_id": None, "candidates": []}


def match_row_entities(tenant: Tenant, normalized_payload: dict) -> dict:
    organization_match = match_organization(tenant, normalized_payload)
    person_match = match_person(tenant, normalized_payload, organization_match)
    return {
        "organization": organization_match,
        "person": person_match,
    }
