from __future__ import annotations

from django.db.models import Q

from crm.models import Organization, OrganizationPerson, Person, PersonContact, Tenant
from .normalizers import normalize_domain, normalize_name


GENERIC_EMAIL_DOMAINS = {
    "gmail.com",
    "hotmail.com",
    "icloud.com",
    "live.com",
    "outlook.com",
    "yahoo.com",
}


def _candidate_payload(queryset, label_field: str) -> list[dict]:
    return [
        {"id": item.id, "label": getattr(item, label_field)}
        for item in queryset[:5]
    ]


def _domain_from_email(email: str) -> str | None:
    value = (email or "").strip().lower()
    if "@" not in value:
        return None
    domain = value.split("@", 1)[1]
    if domain in GENERIC_EMAIL_DOMAINS:
        return None
    return domain


def _row_domains(normalized_payload: dict) -> list[str]:
    organization = normalized_payload.get("organization") or {}
    person = normalized_payload.get("person") or {}
    domains: list[str] = []
    for candidate in (
        organization.get("website_domain"),
        normalize_domain(organization.get("website_url") or ""),
        normalize_domain(person.get("website_url") or ""),
        _domain_from_email(organization.get("email") or ""),
        _domain_from_email(person.get("email") or ""),
    ):
        if candidate and candidate not in domains:
            domains.append(candidate)
    return domains


def match_organization(tenant: Tenant, normalized_payload: dict) -> dict:
    data = normalized_payload["organization"]
    if not data["name"] and not data["org_number"]:
        row_domains = _row_domains(normalized_payload)
        if not row_domains:
            return {"status": "NONE", "rule": None, "exact_id": None, "candidates": []}
    else:
        row_domains = _row_domains(normalized_payload)

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

    if row_domains:
        domain_matches = [
            candidate
            for candidate in queryset.exclude(website_url="")
            if normalize_domain(candidate.website_url) in row_domains
        ]
        if data["normalized_name"]:
            aligned = [candidate for candidate in domain_matches if normalize_name(candidate.name) == data["normalized_name"]]
            if len(aligned) == 1:
                return {
                    "status": "EXACT",
                    "rule": "NAME_AND_CONTACT_DOMAIN",
                    "exact_id": aligned[0].id,
                    "candidates": [],
                }
            if aligned:
                return {
                    "status": "FUZZY",
                    "rule": "NAME_AND_CONTACT_DOMAIN",
                    "exact_id": None,
                    "candidates": _candidate_payload(aligned, "name"),
                }
        if domain_matches:
            return {
                "status": "FUZZY",
                "rule": "CONTACT_DOMAIN",
                "exact_id": None,
                "candidates": _candidate_payload(domain_matches, "name"),
            }

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
