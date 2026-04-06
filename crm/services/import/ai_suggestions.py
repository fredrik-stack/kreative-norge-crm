from __future__ import annotations

import json
from typing import Any
from django.conf import settings

from crm.models import Category, Subcategory, Tag, Tenant
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
    "organization_website_url",
    "organization_instagram_url",
    "organization_tiktok_url",
    "organization_linkedin_url",
    "organization_facebook_url",
    "organization_youtube_url",
    "organization_description",
    "person_title",
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
    "organization_website_url",
    "organization_description",
    "suggested_tags",
    "suggested_categories",
    "suggested_subcategories",
)


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


def _heuristic_suggestions(tenant: Tenant, normalized_payload: dict, match_result: dict) -> dict:
    organization = normalized_payload["organization"]
    person = normalized_payload["person"]
    text_blob = normalize_name(" ".join(_collect_text_blobs(normalized_payload)))

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
    return payload


def _sanitize_suggestions(payload: dict[str, Any], fallback_provider: str) -> dict[str, Any]:
    payload = payload or {}
    suggested_fields = {
        key: value
        for key, value in (payload.get("suggested_fields") or {}).items()
        if key not in FORBIDDEN_SUGGESTED_FIELDS and key in ALLOWED_SUGGESTION_FIELD_KEYS
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
                    "website_url",
                    "description",
                )
                if not organization.get(key)
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
            "Only suggest five field families: categories, subcategories, tags, organization website URL, and organization short description. "
            "Never suggest publish/public flags. Only return confident, reviewable values."
        ),
        "tenant_id": tenant.id,
        "normalized_payload": normalized_payload,
        "match_result": match_result,
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
            "Only suggest organization website when plausible and editorially useful.",
            "A short description should be one brief sentence, not marketing copy.",
            "Do not return keys outside the allowed_fields list.",
            "If you have no confident suggestion for a field, omit it instead of guessing.",
        ],
    }
    return json.dumps(envelope, ensure_ascii=False)


def _openai_schema() -> dict[str, Any]:
    field_value = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "value": {
                "oneOf": [
                    {"type": "string"},
                    {"type": "array", "items": {"type": "string"}},
                ]
            },
            "confidence": {"type": "number"},
            "source": {"type": "string"},
            "requires_review": {"type": "boolean"},
        },
        "required": ["value", "confidence", "source", "requires_review"],
    }
    suggested_fields_properties = {
        key: {
            "anyOf": [
                field_value,
                {"type": "null"},
            ]
        }
        for key in OPENAI_SCHEMA_FIELD_KEYS
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
                    "properties": suggested_fields_properties,
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
    return _sanitize_suggestions(parsed, "openai")


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
    return _sanitize_suggestions(merged, "openai")
