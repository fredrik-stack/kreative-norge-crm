from __future__ import annotations

from urllib.parse import urlparse

from crm.models import Category, Organization, Person, Subcategory, Tag, Tenant
from .normalizers import normalize_name, normalize_space

GENERIC_EMAIL_DOMAINS = {
    "gmail.com",
    "hotmail.com",
    "icloud.com",
    "live.com",
    "outlook.com",
    "yahoo.com",
}


def _score_candidates(candidates: list[dict], reason: str, score: float) -> list[dict]:
    return [
        {
            "id": candidate["id"],
            "label": candidate.get("label"),
            "score": score,
            "reason": reason,
        }
        for candidate in candidates
    ]


def _suggest_name(value: str) -> str | None:
    if not value:
        return None
    suggested = normalize_space(value).title()
    return suggested if suggested and suggested != value else None


def _domain_from_email(email: str) -> str | None:
    if "@" not in email:
        return None
    domain = email.split("@", 1)[1].lower()
    if domain in GENERIC_EMAIL_DOMAINS:
        return None
    return domain


def _infer_website_url(normalized_payload: dict) -> str | None:
    organization = normalized_payload["organization"]
    if organization.get("website_url"):
        return None
    email_domain = _domain_from_email(organization.get("email", ""))
    if email_domain:
        return f"https://{email_domain}"
    return None


def _suggest_description(normalized_payload: dict) -> str | None:
    organization = normalized_payload["organization"]
    if organization.get("description"):
        return None
    note = organization.get("note", "").strip()
    if note:
        return note[:200]
    name = organization.get("name", "").strip()
    categories = organization.get("categories", [])
    if name and categories:
        return f"{name} er registrert under {categories[0]}."
    return None


def _collect_text_blobs(normalized_payload: dict) -> list[str]:
    organization = normalized_payload["organization"]
    person = normalized_payload["person"]
    return [
        organization.get("name", ""),
        organization.get("description", ""),
        organization.get("note", ""),
        person.get("full_name", ""),
        person.get("title", ""),
        person.get("note", ""),
    ]


def _unique_casefold(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.strip()
        key = normalized.casefold()
        if not normalized or key in seen:
            continue
        seen.add(key)
        result.append(normalized)
    return result


def _suggest_existing_tags(tenant: Tenant, normalized_payload: dict) -> list[str]:
    text = " ".join(_collect_text_blobs(normalized_payload)).casefold()
    if not text:
        return []
    tag_names = list(Tag.objects.filter(tenant=tenant).values_list("name", flat=True))
    return _unique_casefold([name for name in tag_names if name.casefold() in text])


def _suggest_taxonomy(queryset, text: str) -> list[str]:
    if not text:
        return []
    return _unique_casefold(
        [name for name in queryset.values_list("name", flat=True) if normalize_name(name) in text]
    )


def generate_ai_suggestions(tenant: Tenant, normalized_payload: dict, match_result: dict) -> dict:
    organization = normalized_payload["organization"]
    person = normalized_payload["person"]
    text_blob = normalize_name(" ".join(_collect_text_blobs(normalized_payload)))

    suggested_fields: dict[str, dict] = {}

    organization_name = _suggest_name(organization.get("name", ""))
    if organization_name:
        suggested_fields["organization_name"] = {
            "value": organization_name,
            "confidence": 0.84,
            "source": "heuristic_normalizer",
            "requires_review": True,
        }

    person_name = _suggest_name(person.get("full_name", ""))
    if person_name:
        suggested_fields["person_full_name"] = {
            "value": person_name,
            "confidence": 0.84,
            "source": "heuristic_normalizer",
            "requires_review": True,
        }

    website_url = _infer_website_url(normalized_payload)
    if website_url:
        suggested_fields["organization_website_url"] = {
            "value": website_url,
            "confidence": 0.74,
            "source": "heuristic_enrichment",
            "requires_review": True,
        }

    description = _suggest_description(normalized_payload)
    if description:
        suggested_fields["organization_description"] = {
            "value": description,
            "confidence": 0.68,
            "source": "heuristic_enrichment",
            "requires_review": True,
        }

    tag_suggestions = _suggest_existing_tags(tenant, normalized_payload)
    if tag_suggestions:
        suggested_fields["suggested_tags"] = {
            "value": tag_suggestions,
            "confidence": 0.61,
            "source": "heuristic_taxonomy",
            "requires_review": True,
        }

    category_names = _suggest_taxonomy(Category.objects.all(), text_blob)
    if category_names:
        suggested_fields["suggested_categories"] = {
            "value": category_names,
            "confidence": 0.59,
            "source": "heuristic_taxonomy",
            "requires_review": True,
        }

    subcategory_names = _suggest_taxonomy(Subcategory.objects.select_related("category").all(), text_blob)
    if subcategory_names:
        suggested_fields["suggested_subcategories"] = {
            "value": subcategory_names,
            "confidence": 0.57,
            "source": "heuristic_taxonomy",
            "requires_review": True,
        }

    organization_candidates = []
    if match_result.get("organization", {}).get("status") == "FUZZY":
        organization_candidates = _score_candidates(
            match_result["organization"].get("candidates", []),
            "fuzzy_name",
            0.72,
        )

    person_candidates = []
    if match_result.get("person", {}).get("status") == "FUZZY":
        person_candidates = _score_candidates(
            match_result["person"].get("candidates", []),
            "fuzzy_name",
            0.7,
        )

    return {
        "organization_match_candidates": organization_candidates,
        "person_match_candidates": person_candidates,
        "suggested_fields": suggested_fields,
        "provider": "heuristic_fallback",
    }
