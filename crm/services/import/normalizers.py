from __future__ import annotations

import re
from urllib.parse import urlparse


ORGANIZATION_IMPORT_FIELDS = [
    "organization_name",
    "organization_org_number",
    "organization_email",
    "organization_phone",
    "organization_publish_phone",
    "organization_municipalities",
    "organization_website_url",
    "organization_instagram_url",
    "organization_tiktok_url",
    "organization_linkedin_url",
    "organization_facebook_url",
    "organization_youtube_url",
    "organization_description",
    "organization_note",
    "organization_is_published",
    "organization_categories",
    "organization_subcategories",
    "organization_tags",
]

PERSON_IMPORT_FIELDS = [
    "person_full_name",
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
    "person_note",
    "person_categories",
    "person_subcategories",
    "person_tags",
    "person_secondary_emails",
    "person_secondary_phones",
    "person_secondary_emails_public",
    "person_secondary_phones_public",
    "organization_org_number",
    "organization_name",
    "link_status",
    "link_publish_person",
]

COMBINED_IMPORT_FIELDS = [
    "organization_name",
    "organization_org_number",
    "organization_email",
    "organization_phone",
    "organization_publish_phone",
    "organization_municipalities",
    "organization_website_url",
    "organization_instagram_url",
    "organization_tiktok_url",
    "organization_linkedin_url",
    "organization_facebook_url",
    "organization_youtube_url",
    "organization_description",
    "organization_note",
    "organization_is_published",
    "organization_categories",
    "organization_subcategories",
    "organization_tags",
    "person_full_name",
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
    "person_note",
    "person_categories",
    "person_subcategories",
    "person_tags",
    "link_status",
    "link_publish_person",
    "person_secondary_emails",
    "person_secondary_phones",
    "person_secondary_emails_public",
    "person_secondary_phones_public",
]

EXPECTED_IMPORT_FIELDS = COMBINED_IMPORT_FIELDS


def get_expected_import_fields(import_mode: str = "COMBINED") -> list[str]:
    if import_mode == "ORGANIZATIONS_ONLY":
        return ORGANIZATION_IMPORT_FIELDS
    if import_mode == "PEOPLE_ONLY":
        return PERSON_IMPORT_FIELDS
    return COMBINED_IMPORT_FIELDS


def build_import_template_config(import_mode: str) -> dict:
    if import_mode == "ORGANIZATIONS_ONLY":
        return {
            "template_code": "actors_v1",
            "sheet_name": "actors",
            "columns": ORGANIZATION_IMPORT_FIELDS,
        }
    if import_mode == "PEOPLE_ONLY":
        return {
            "template_code": "people_v1",
            "sheet_name": "people",
            "columns": PERSON_IMPORT_FIELDS,
        }
    return {
        "template_code": "combined_v1",
        "sheet_name": "combined",
        "columns": COMBINED_IMPORT_FIELDS,
    }


def clean_string(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", clean_string(value)).strip()


def normalize_name(value: str) -> str:
    return normalize_space(value).casefold()


def normalize_org_number(value) -> str:
    return re.sub(r"\D+", "", clean_string(value))


def normalize_phone(value) -> str:
    return normalize_space(value)


def normalize_email(value) -> str:
    return clean_string(value).lower()


def normalize_domain(url: str) -> str:
    parsed = urlparse(clean_string(url))
    host = (parsed.netloc or parsed.path).lower()
    if host.startswith("www."):
        host = host[4:]
    return host.split("/")[0]


def parse_bool(value, default: bool = False) -> bool:
    text = clean_string(value).lower()
    if not text:
        return default
    if text in {"1", "true", "yes", "ja", "y", "on"}:
        return True
    if text in {"0", "false", "no", "nei", "n", "off"}:
        return False
    return default


def split_values(value) -> list[str]:
    text = clean_string(value)
    if not text:
        return []
    return [item.strip() for item in re.split(r"[,\n;|]+", text) if item.strip()]


def _contacts(values, public_flags, contact_type: str) -> list[dict]:
    parsed_values = split_values(values)
    flags = [parse_bool(item, default=False) for item in split_values(public_flags)]
    contacts = []
    for index, value in enumerate(parsed_values):
        contacts.append(
            {
                "type": contact_type,
                "value": value,
                "is_public": flags[index] if index < len(flags) else False,
                "is_primary": False,
            }
        )
    return contacts


def normalize_import_row(raw_payload: dict, import_mode: str = "COMBINED") -> dict:
    raw_payload = raw_payload or {}
    organization_name = normalize_space(raw_payload.get("organization_name"))
    organization_org_number = normalize_org_number(raw_payload.get("organization_org_number"))
    person_full_name = normalize_space(raw_payload.get("person_full_name"))
    person_email = normalize_email(raw_payload.get("person_email"))
    person_phone = normalize_phone(raw_payload.get("person_phone"))

    normalized = {
        "organization": {
            "name": organization_name,
            "normalized_name": normalize_name(organization_name),
            "org_number": organization_org_number,
            "email": normalize_email(raw_payload.get("organization_email")),
            "phone": normalize_phone(raw_payload.get("organization_phone")),
            "publish_phone": parse_bool(raw_payload.get("organization_publish_phone"), default=False),
            "municipalities": normalize_space(raw_payload.get("organization_municipalities")),
            "website_url": clean_string(raw_payload.get("organization_website_url")),
            "website_domain": normalize_domain(raw_payload.get("organization_website_url")),
            "instagram_url": clean_string(raw_payload.get("organization_instagram_url")),
            "tiktok_url": clean_string(raw_payload.get("organization_tiktok_url")),
            "linkedin_url": clean_string(raw_payload.get("organization_linkedin_url")),
            "facebook_url": clean_string(raw_payload.get("organization_facebook_url")),
            "youtube_url": clean_string(raw_payload.get("organization_youtube_url")),
            "description": clean_string(raw_payload.get("organization_description")),
            "note": clean_string(raw_payload.get("organization_note")),
            "is_published": parse_bool(raw_payload.get("organization_is_published"), default=False),
            "categories": split_values(raw_payload.get("organization_categories")),
            "subcategories": split_values(raw_payload.get("organization_subcategories")),
            "tags": split_values(raw_payload.get("organization_tags")),
        },
        "person": {
            "full_name": person_full_name,
            "normalized_full_name": normalize_name(person_full_name),
            "title": normalize_space(raw_payload.get("person_title")),
            "email": person_email,
            "phone": person_phone,
            "municipality": normalize_space(raw_payload.get("person_municipality")),
            "website_url": clean_string(raw_payload.get("person_website_url")),
            "instagram_url": clean_string(raw_payload.get("person_instagram_url")),
            "tiktok_url": clean_string(raw_payload.get("person_tiktok_url")),
            "linkedin_url": clean_string(raw_payload.get("person_linkedin_url")),
            "facebook_url": clean_string(raw_payload.get("person_facebook_url")),
            "youtube_url": clean_string(raw_payload.get("person_youtube_url")),
            "note": clean_string(raw_payload.get("person_note")),
            "categories": split_values(raw_payload.get("person_categories")),
            "subcategories": split_values(raw_payload.get("person_subcategories")),
            "tags": split_values(raw_payload.get("person_tags")),
            "secondary_contacts": _contacts(
                raw_payload.get("person_secondary_emails"),
                raw_payload.get("person_secondary_emails_public"),
                "EMAIL",
            )
            + _contacts(
                raw_payload.get("person_secondary_phones"),
                raw_payload.get("person_secondary_phones_public"),
                "PHONE",
            ),
        },
        "link": {
            "status": normalize_space(raw_payload.get("link_status")).upper() or "ACTIVE",
            "publish_person": parse_bool(raw_payload.get("link_publish_person"), default=False),
        },
    }

    if import_mode == "ORGANIZATIONS_ONLY":
        normalized["person"] = {
            "full_name": "",
            "normalized_full_name": "",
            "title": "",
            "email": "",
            "phone": "",
            "municipality": "",
            "website_url": "",
            "instagram_url": "",
            "tiktok_url": "",
            "linkedin_url": "",
            "facebook_url": "",
            "youtube_url": "",
            "note": "",
            "categories": [],
            "subcategories": [],
            "tags": [],
            "secondary_contacts": [],
        }
        normalized["link"] = {"status": "ACTIVE", "publish_person": False}
    elif import_mode == "PEOPLE_ONLY":
        normalized["organization"] = {
            "name": organization_name,
            "normalized_name": normalize_name(organization_name),
            "org_number": organization_org_number,
            "email": "",
            "phone": "",
            "publish_phone": False,
            "municipalities": "",
            "website_url": "",
            "website_domain": "",
            "instagram_url": "",
            "tiktok_url": "",
            "linkedin_url": "",
            "facebook_url": "",
            "youtube_url": "",
            "description": "",
            "note": "",
            "is_published": False,
            "categories": [],
            "subcategories": [],
            "tags": [],
        }
        normalized["link"] = {
            "status": normalize_space(raw_payload.get("link_status")).upper() or "ACTIVE",
            "publish_person": parse_bool(raw_payload.get("link_publish_person"), default=False),
        }

    return normalized
