from __future__ import annotations

import json
import re
from urllib.parse import urlparse
from typing import Any
from django.conf import settings

from crm.models import Category, Organization, Person, Subcategory, Tag, Tenant
from crm.services.open_graph import MAX_HTML_BYTES, _fetch_url
from .normalizers import normalize_name, normalize_space

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - optional dependency in local envs
    OpenAI = None


GENERIC_EMAIL_DOMAINS = {
    "gmail.com",
    "hotmail.com",
    "icloud.com",
    "live.com",
    "outlook.com",
    "yahoo.com",
}

FORBIDDEN_SUGGESTED_FIELDS = {
    "organization_is_published",
    "organization_publish_phone",
    "link_publish_person",
    "person_contact_is_public",
}

ALLOWED_SUGGESTION_FIELD_KEYS = (
    "organization_name",
    "person_full_name",
    "organization_email",
    "organization_phone",
    "organization_municipalities",
    "organization_website_url",
    "organization_instagram_url",
    "organization_tiktok_url",
    "organization_linkedin_url",
    "organization_facebook_url",
    "organization_youtube_url",
    "organization_description",
    "person_title",
    "person_email",
    "person_phone",
    "person_municipality",
    "person_website_url",
    "person_instagram_url",
    "person_tiktok_url",
    "person_linkedin_url",
    "person_facebook_url",
    "person_youtube_url",
    "suggested_tags",
    "suggested_categories",
    "suggested_subcategories",
)

OPENAI_SCHEMA_FIELD_KEYS = (
    "organization_email",
    "organization_phone",
    "organization_municipalities",
    "organization_website_url",
    "organization_instagram_url",
    "organization_tiktok_url",
    "organization_linkedin_url",
    "organization_facebook_url",
    "organization_youtube_url",
    "organization_description",
    "person_email",
    "person_phone",
    "person_municipality",
    "person_website_url",
    "person_instagram_url",
    "person_tiktok_url",
    "person_linkedin_url",
    "person_facebook_url",
    "person_youtube_url",
    "suggested_tags",
    "suggested_categories",
    "suggested_subcategories",
)

SOCIAL_DOMAINS = {
    "organization_instagram_url": "instagram.com",
    "person_instagram_url": "instagram.com",
    "organization_tiktok_url": "tiktok.com",
    "person_tiktok_url": "tiktok.com",
    "organization_linkedin_url": "linkedin.com",
    "person_linkedin_url": "linkedin.com",
    "organization_facebook_url": "facebook.com",
    "person_facebook_url": "facebook.com",
    "organization_youtube_url": "youtube.com",
    "person_youtube_url": "youtube.com",
}

ENGLISH_DESCRIPTION_MARKERS = (
    " the ",
    " and ",
    " for ",
    " with ",
    " artist ",
    " company ",
    " organizer ",
)

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_RE = re.compile(r"(?:(?:\+|00)47[\s\-]?)?(?:\d[\s\-]?){8,12}")
URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)


def openai_is_ready() -> bool:
    return bool(settings.OPENAI_IMPORT_ENABLED and settings.OPENAI_API_KEY and OpenAI is not None)


def _count_useful_suggestions(payload: dict[str, Any]) -> int:
    count = 0
    for value in (payload.get("suggested_fields") or {}).values():
        suggestion_value = (value or {}).get("value")
        if isinstance(suggestion_value, list) and suggestion_value:
            count += 1
        elif isinstance(suggestion_value, str) and suggestion_value.strip():
            count += 1
        elif suggestion_value not in (None, "", []):
            count += 1
    if payload.get("organization_match_candidates"):
        count += 1
    if payload.get("person_match_candidates"):
        count += 1
    return count


def _has_useful_suggestion(value: Any) -> bool:
    suggestion_value = (value or {}).get("value")
    if isinstance(suggestion_value, list):
        return bool([item for item in suggestion_value if str(item).strip()])
    if isinstance(suggestion_value, str):
        return bool(suggestion_value.strip())
    return suggestion_value not in (None, "", [])


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


def _sanitize_url(value: str | None) -> str | None:
    if not value:
        return None
    candidate = value.strip()
    if not candidate:
        return None
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return candidate


def _sanitize_phone(value: str | None) -> str | None:
    if not value:
        return None
    compact = re.sub(r"[^\d+]", "", value.strip())
    digits = re.sub(r"\D", "", compact)
    if len(digits) < 8:
        return None
    return value.strip()


def _extract_contact_signals_from_website(url: str | None) -> dict[str, Any]:
    safe_url = _sanitize_url(url)
    if not safe_url:
        return {}
    try:
        result = _fetch_url(
            safe_url,
            timeout_seconds=min(settings.OPENAI_IMPORT_TIMEOUT, 5),
            max_bytes=MAX_HTML_BYTES,
            allowed_content_prefixes=("text/html",),
        )
    except Exception:
        return {}

    html = result.body.decode("utf-8", errors="ignore")
    emails = list(dict.fromkeys(match.group(0) for match in EMAIL_RE.finditer(html)))
    phones = []
    for match in PHONE_RE.finditer(html):
        phone = normalize_space(match.group(0))
        if phone and phone not in phones:
            phones.append(phone)
    urls = [match.group(0).rstrip(").,;") for match in URL_RE.finditer(html)]
    socials: dict[str, str] = {}
    for candidate in urls:
        normalized = _sanitize_url(candidate)
        if not normalized:
            continue
        hostname = (urlparse(normalized).hostname or "").lower()
        for field_key, domain in SOCIAL_DOMAINS.items():
            if domain in hostname and field_key not in socials:
                socials[field_key] = normalized
    visible_text = normalize_space(re.sub(r"<[^>]+>", " ", html))
    return {
        "emails": emails[:3],
        "phones": phones[:3],
        "socials": socials,
        "text_snippet": visible_text[:1200],
        "final_url": result.final_url,
    }


def _suggest_field_from_exact_match(tenant: Tenant, match_result: dict, entity_type: str, field_name: str) -> str | None:
    exact_id = ((match_result.get(entity_type) or {}).get("exact_id"))
    if not exact_id:
        return None
    model = Organization if entity_type == "organization" else Person
    try:
        instance = model.objects.get(id=exact_id, tenant=tenant)
    except model.DoesNotExist:
        return None
    value = getattr(instance, field_name, None)
    return normalize_space(value) if isinstance(value, str) else value


def _looks_non_norwegian(text: str) -> bool:
    lowered = f" {text.casefold()} "
    if " og " in lowered or " med " in lowered or " som " in lowered:
        return False
    return any(marker in lowered for marker in ENGLISH_DESCRIPTION_MARKERS)


def _normalize_taxonomy_values(values: list[str], *, choices: list[str]) -> list[str]:
    if not values:
        return []
    lookup = {choice.casefold(): choice for choice in choices}
    normalized = []
    seen: set[str] = set()
    for value in values:
        exact = lookup.get(str(value).strip().casefold())
        if not exact:
            continue
        key = exact.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(exact)
    return normalized


def _normalize_text_suggestion(key: str, value: str) -> str | None:
    text = normalize_space(value)
    if not text:
        return None
    if key in {"organization_email", "person_email"}:
        candidate = text.casefold()
        return candidate if EMAIL_RE.fullmatch(candidate) else None
    if key in {"organization_phone", "person_phone"}:
        return _sanitize_phone(text)
    if key in {"organization_website_url", "person_website_url"}:
        return _sanitize_url(text)
    if key in SOCIAL_DOMAINS:
        url = _sanitize_url(text)
        if not url:
            return None
        host = (urlparse(url).netloc or "").casefold()
        if SOCIAL_DOMAINS[key] not in host:
            return None
        return url
    if key == "organization_description" and _looks_non_norwegian(text):
        return None
    return text


def _enforce_suggestion_quality(tenant: Tenant, payload: dict[str, Any]) -> dict[str, Any]:
    payload = payload or {}
    categories = list(Category.objects.values_list("name", flat=True))
    subcategories = list(Subcategory.objects.values_list("name", flat=True))
    suggested_fields = {}
    for key, value in (payload.get("suggested_fields") or {}).items():
        if key in {"suggested_categories", "suggested_subcategories", "suggested_tags"}:
            items = value.get("value") if isinstance(value, dict) else None
            if not isinstance(items, list):
                continue
            if key == "suggested_categories":
                normalized_items = _normalize_taxonomy_values([str(item) for item in items], choices=categories)
            elif key == "suggested_subcategories":
                normalized_items = _normalize_taxonomy_values([str(item) for item in items], choices=subcategories)
            else:
                normalized_items = _unique_casefold([str(item) for item in items])
            if not normalized_items:
                continue
            next_value = dict(value)
            next_value["value"] = normalized_items
            suggested_fields[key] = next_value
            continue
        if not isinstance(value, dict):
            continue
        normalized_text = _normalize_text_suggestion(key, str(value.get("value") or ""))
        if not normalized_text:
            continue
        next_value = dict(value)
        next_value["value"] = normalized_text
        suggested_fields[key] = next_value

    payload = dict(payload)
    payload["suggested_fields"] = suggested_fields
    if payload.get("diagnostic"):
        payload["diagnostic"]["useful_suggestion_count"] = _count_useful_suggestions(payload)
    return payload


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


def _heuristic_suggestions(tenant: Tenant, normalized_payload: dict, match_result: dict) -> dict:
    organization = normalized_payload["organization"]
    person = normalized_payload["person"]
    text_blob = normalize_name(" ".join(_collect_text_blobs(normalized_payload)))
    website_url = _infer_website_url(normalized_payload) or organization.get("website_url") or person.get("website_url")
    website_signals = _extract_contact_signals_from_website(website_url)

    suggested_fields: dict[str, dict[str, Any]] = {}

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

    if website_url:
        suggested_fields["organization_website_url"] = {
            "value": website_url,
            "confidence": 0.74,
            "source": "heuristic_enrichment",
            "requires_review": True,
        }

    if not organization.get("email") and website_signals.get("emails"):
        suggested_fields["organization_email"] = {
            "value": website_signals["emails"][0],
            "confidence": 0.78,
            "source": "website_contact_signal",
            "requires_review": True,
        }

    if not organization.get("phone") and website_signals.get("phones"):
        suggested_fields["organization_phone"] = {
            "value": website_signals["phones"][0],
            "confidence": 0.75,
            "source": "website_contact_signal",
            "requires_review": True,
        }

    if not person.get("email") and website_signals.get("emails"):
        suggested_fields["person_email"] = {
            "value": website_signals["emails"][0],
            "confidence": 0.62,
            "source": "website_contact_signal",
            "requires_review": True,
        }

    if not person.get("phone") and website_signals.get("phones"):
        suggested_fields["person_phone"] = {
            "value": website_signals["phones"][0],
            "confidence": 0.6,
            "source": "website_contact_signal",
            "requires_review": True,
        }

    if not organization.get("municipalities"):
        organization_municipality = _suggest_field_from_exact_match(tenant, match_result, "organization", "municipalities")
        if organization_municipality:
            suggested_fields["organization_municipalities"] = {
                "value": organization_municipality,
                "confidence": 0.82,
                "source": "matched_record",
                "requires_review": True,
            }

    if not person.get("municipality"):
        person_municipality = _suggest_field_from_exact_match(tenant, match_result, "person", "municipality")
        if person_municipality:
            suggested_fields["person_municipality"] = {
                "value": person_municipality,
                "confidence": 0.82,
                "source": "matched_record",
                "requires_review": True,
            }

    for field_name, payload_key in (
        ("instagram_url", "organization_instagram_url"),
        ("tiktok_url", "organization_tiktok_url"),
        ("linkedin_url", "organization_linkedin_url"),
        ("facebook_url", "organization_facebook_url"),
        ("youtube_url", "organization_youtube_url"),
    ):
        if not organization.get(field_name):
            exact_match_value = _suggest_field_from_exact_match(tenant, match_result, "organization", field_name)
            value = exact_match_value or website_signals.get("socials", {}).get(payload_key)
            if value:
                suggested_fields[payload_key] = {
                    "value": value,
                    "confidence": 0.8 if exact_match_value else 0.73,
                    "source": "matched_record" if exact_match_value else "website_contact_signal",
                    "requires_review": True,
                }

    for field_name, payload_key in (
        ("email", "person_email"),
        ("phone", "person_phone"),
        ("website_url", "person_website_url"),
        ("instagram_url", "person_instagram_url"),
        ("tiktok_url", "person_tiktok_url"),
        ("linkedin_url", "person_linkedin_url"),
        ("facebook_url", "person_facebook_url"),
        ("youtube_url", "person_youtube_url"),
    ):
        if not person.get(field_name):
            exact_match_value = _suggest_field_from_exact_match(tenant, match_result, "person", field_name)
            value = exact_match_value
            if not value and payload_key in {"person_email", "person_phone"}:
                values = website_signals.get("emails" if payload_key == "person_email" else "phones") or []
                value = values[0] if values else None
            if not value and payload_key in website_signals.get("socials", {}):
                value = website_signals["socials"][payload_key]
            if value:
                suggested_fields[payload_key] = {
                    "value": value,
                    "confidence": 0.8 if exact_match_value else 0.68,
                    "source": "matched_record" if exact_match_value else "website_contact_signal",
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

    payload = {
        "organization_match_candidates": organization_candidates,
        "person_match_candidates": person_candidates,
        "suggested_fields": suggested_fields,
        "provider": "heuristic_fallback",
    }
    payload["diagnostic"] = {
        "primary_provider": "heuristic_fallback",
        "provider_status": "fallback",
        "fallback_reason": "heuristic_only",
        "openai_attempted": False,
        "openai_error": None,
        "useful_suggestion_count": _count_useful_suggestions(payload),
    }
    return _enforce_suggestion_quality(tenant, payload)


def build_pending_ai_suggestions(tenant: Tenant, normalized_payload: dict, match_result: dict) -> dict:
    heuristic = _sanitize_suggestions(_heuristic_suggestions(tenant, normalized_payload, match_result), "heuristic_fallback")
    if openai_is_ready():
        heuristic["provider"] = "pending_openai"
        heuristic["diagnostic"].update(
            {
                "primary_provider": "pending_openai",
                "provider_status": "pending_openai",
                "fallback_reason": "awaiting_openai",
                "openai_attempted": False,
                "openai_error": None,
            }
        )
        return heuristic
    if not settings.OPENAI_IMPORT_ENABLED:
        heuristic["diagnostic"].update(
            {
                "provider_status": "fallback_openai_disabled",
                "fallback_reason": "openai_disabled",
                "openai_attempted": False,
            }
        )
        return heuristic
    heuristic["diagnostic"].update(
        {
            "provider_status": "fallback_openai_unavailable",
            "fallback_reason": "missing_api_key" if not settings.OPENAI_API_KEY else "openai_sdk_unavailable",
            "openai_attempted": False,
        }
    )
    return heuristic


def _sanitize_suggestions(payload: dict[str, Any], fallback_provider: str) -> dict[str, Any]:
    payload = payload or {}
    suggested_fields = {
        key: value
        for key, value in (payload.get("suggested_fields") or {}).items()
        if (
            key not in FORBIDDEN_SUGGESTED_FIELDS
            and key in ALLOWED_SUGGESTION_FIELD_KEYS
            and _has_useful_suggestion(value)
        )
    }
    organization_match_candidates = payload.get("organization_match_candidates") or []
    person_match_candidates = payload.get("person_match_candidates") or []
    sanitized = {
        "organization_match_candidates": organization_match_candidates,
        "person_match_candidates": person_match_candidates,
        "suggested_fields": suggested_fields,
        "provider": payload.get("provider") or fallback_provider,
    }
    diagnostic = payload.get("diagnostic") or {}
    sanitized["diagnostic"] = {
        "primary_provider": diagnostic.get("primary_provider") or sanitized["provider"],
        "provider_status": diagnostic.get("provider_status") or sanitized["provider"],
        "fallback_reason": diagnostic.get("fallback_reason"),
        "openai_attempted": bool(diagnostic.get("openai_attempted", False)),
        "openai_error": diagnostic.get("openai_error"),
        "useful_suggestion_count": diagnostic.get("useful_suggestion_count", _count_useful_suggestions(sanitized)),
    }
    return sanitized


def _build_openai_input(tenant: Tenant, normalized_payload: dict, match_result: dict) -> str:
    organization = normalized_payload.get("organization") or {}
    person = normalized_payload.get("person") or {}
    website_url = _infer_website_url(normalized_payload) or organization.get("website_url") or person.get("website_url")
    website_signals = _extract_contact_signals_from_website(website_url)
    taxonomy = {
        "categories": list(Category.objects.values_list("name", flat=True)),
        "subcategories": list(Subcategory.objects.values_list("name", flat=True)),
        "existing_tags": list(Tag.objects.filter(tenant=tenant).values_list("name", flat=True)),
    }
    editable_targets = {
        "organization": {
            "empty_or_missing": [
                key
                for key in (
                    "email",
                    "phone",
                    "municipalities",
                    "website_url",
                    "instagram_url",
                    "tiktok_url",
                    "linkedin_url",
                    "facebook_url",
                    "youtube_url",
                    "description",
                )
                if not organization.get(key)
            ]
        },
        "person": {
            "empty_or_missing": [
                key
                for key in (
                    "email",
                    "phone",
                    "municipality",
                    "website_url",
                    "instagram_url",
                    "tiktok_url",
                    "linkedin_url",
                    "facebook_url",
                    "youtube_url",
                )
                if not person.get(key)
            ]
        },
        "taxonomy": {
            "empty_or_missing": [
                key
                for key, value in (
                    ("categories", organization.get("categories")),
                    ("subcategories", organization.get("subcategories")),
                    ("tags", organization.get("tags")),
                )
                if not value
            ]
        },
    }
    envelope = {
        "task": (
            "Suggest editorial import-review assistance for a tenant-scoped CRM. "
            "Suggest only reviewable values for municipalities, taxonomy, websites, social profile URLs, and a short organization description in Norwegian. "
            "Never suggest publish/public flags, and never invent organization numbers."
        ),
        "tenant_id": tenant.id,
        "normalized_payload": normalized_payload,
        "match_result": match_result,
        "website_signals": website_signals,
        "taxonomy": taxonomy,
        "review_targets": editable_targets,
        "rules": {
            "forbidden_fields": sorted(FORBIDDEN_SUGGESTED_FIELDS),
            "allowed_fields": list(OPENAI_SCHEMA_FIELD_KEYS),
            "assistive_only": True,
            "requires_review": True,
            "never_auto_publish": True,
            "never_auto_commit": True,
            "prefer_empty_fields": True,
            "language_hint": "Norwegian editorial data, but return field keys in English exactly as provided.",
        },
        "instructions": [
            "Suggest main category separately from subcategory.",
            "Keep tags separate from categories and subcategories.",
            "Only use existing category and subcategory names from the provided taxonomy lists.",
            "Use website_signals for public email, public phone, municipality clues, and social profile URLs when available.",
            "Only suggest municipality when reasonably confident.",
            "Only suggest public email and phone when they are clearly present in website_signals or the normalized data.",
            "Only suggest website or social profile URLs when plausible and editorially useful.",
            "Social URLs must match the actual service domain for that field.",
            "A short description must be in Norwegian, one brief sentence, and not marketing copy.",
            "Do not return keys outside the allowed_fields list.",
            "If you have no confident suggestion for a field, omit it instead of guessing.",
        ],
    }
    return json.dumps(envelope, ensure_ascii=False)


def _openai_schema() -> dict[str, Any]:
    string_field_value = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "value": {"type": "string"},
            "confidence": {"type": "number"},
            "source": {"type": "string"},
            "requires_review": {"type": "boolean"},
        },
        "required": ["value", "confidence", "source", "requires_review"],
    }
    array_field_value = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "value": {"type": "array", "items": {"type": "string"}},
            "confidence": {"type": "number"},
            "source": {"type": "string"},
            "requires_review": {"type": "boolean"},
        },
        "required": ["value", "confidence", "source", "requires_review"],
    }
    return {
        "name": "import_ai_suggestions",
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "suggested_fields": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "organization_email": string_field_value,
                        "organization_phone": string_field_value,
                        "organization_municipalities": string_field_value,
                        "organization_website_url": string_field_value,
                        "organization_instagram_url": string_field_value,
                        "organization_tiktok_url": string_field_value,
                        "organization_linkedin_url": string_field_value,
                        "organization_facebook_url": string_field_value,
                        "organization_youtube_url": string_field_value,
                        "organization_description": string_field_value,
                        "person_email": string_field_value,
                        "person_phone": string_field_value,
                        "person_municipality": string_field_value,
                        "person_website_url": string_field_value,
                        "person_instagram_url": string_field_value,
                        "person_tiktok_url": string_field_value,
                        "person_linkedin_url": string_field_value,
                        "person_facebook_url": string_field_value,
                        "person_youtube_url": string_field_value,
                        "suggested_tags": array_field_value,
                        "suggested_categories": array_field_value,
                        "suggested_subcategories": array_field_value,
                    },
                    "required": list(OPENAI_SCHEMA_FIELD_KEYS),
                },
                "provider": {"type": "string"},
            },
            "required": [
                "suggested_fields",
                "provider",
            ],
        },
        "strict": True,
    }


def _generate_openai_suggestions(tenant: Tenant, normalized_payload: dict, match_result: dict) -> dict | None:
    if not settings.OPENAI_IMPORT_ENABLED or not settings.OPENAI_API_KEY or OpenAI is None:
        return None

    schema = _openai_schema()
    client = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=settings.OPENAI_IMPORT_TIMEOUT)
    response = client.responses.create(
        model=settings.OPENAI_IMPORT_MODEL,
        input=_build_openai_input(tenant, normalized_payload, match_result),
        text={
            "format": {
                "type": "json_schema",
                "name": schema["name"],
                "schema": schema["schema"],
                "strict": schema["strict"],
            }
        },
    )
    output_text = getattr(response, "output_text", "") or "{}"
    parsed = json.loads(output_text)
    parsed.setdefault("organization_match_candidates", [])
    parsed.setdefault("person_match_candidates", [])
    parsed["diagnostic"] = {
        "primary_provider": "openai",
        "provider_status": "openai",
        "fallback_reason": None,
        "openai_attempted": True,
        "openai_error": None,
        "useful_suggestion_count": _count_useful_suggestions(parsed),
    }
    return _sanitize_suggestions(_enforce_suggestion_quality(tenant, parsed), "openai")


def generate_ai_suggestions(tenant: Tenant, normalized_payload: dict, match_result: dict) -> dict:
    heuristic = _sanitize_suggestions(_heuristic_suggestions(tenant, normalized_payload, match_result), "heuristic_fallback")
    if not settings.OPENAI_IMPORT_ENABLED:
        heuristic["diagnostic"].update(
            {
                "provider_status": "fallback_openai_disabled",
                "fallback_reason": "openai_disabled",
                "openai_attempted": False,
            }
        )
        return heuristic
    if not settings.OPENAI_API_KEY:
        heuristic["diagnostic"].update(
            {
                "provider_status": "fallback_openai_unavailable",
                "fallback_reason": "missing_api_key",
                "openai_attempted": False,
            }
        )
        return heuristic
    if OpenAI is None:
        heuristic["diagnostic"].update(
            {
                "provider_status": "fallback_openai_unavailable",
                "fallback_reason": "openai_sdk_unavailable",
                "openai_attempted": False,
            }
        )
        return heuristic
    try:
        openai_suggestions = _generate_openai_suggestions(tenant, normalized_payload, match_result)
    except Exception as exc:
        openai_suggestions = None
        openai_error = str(exc).strip() or exc.__class__.__name__
    else:
        openai_error = None

    if not openai_suggestions:
        heuristic["diagnostic"].update(
            {
                "provider_status": "fallback_openai_error" if openai_error else heuristic["diagnostic"].get("provider_status"),
                "fallback_reason": "openai_error" if openai_error else heuristic["diagnostic"].get("fallback_reason"),
                "openai_attempted": True,
                "openai_error": openai_error,
            }
        )
        return heuristic

    openai_count = _count_useful_suggestions(openai_suggestions)
    heuristic_count = _count_useful_suggestions(heuristic)
    merged_fields = {
        **heuristic.get("suggested_fields", {}),
        **{key: value for key, value in openai_suggestions.get("suggested_fields", {}).items() if value},
    }
    merged = {
        "organization_match_candidates": openai_suggestions.get("organization_match_candidates") or heuristic.get("organization_match_candidates", []),
        "person_match_candidates": openai_suggestions.get("person_match_candidates") or heuristic.get("person_match_candidates", []),
        "suggested_fields": merged_fields,
        "provider": openai_suggestions.get("provider") or "openai",
        "diagnostic": {
            "primary_provider": "openai",
            "provider_status": "openai" if openai_count > 0 else "openai_empty",
            "fallback_reason": None if openai_count > 0 else "openai_returned_no_useful_suggestions",
            "openai_attempted": True,
            "openai_error": None,
            "useful_suggestion_count": max(openai_count, _count_useful_suggestions({"suggested_fields": merged_fields})),
            "openai_suggestion_count": openai_count,
            "heuristic_suggestion_count": heuristic_count,
        },
    }
    return _sanitize_suggestions(_enforce_suggestion_quality(tenant, merged), "openai")
