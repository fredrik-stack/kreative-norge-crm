from __future__ import annotations

from crm.models import Category, Subcategory


def validate_normalized_row(tenant, normalized_payload: dict) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    organization = normalized_payload["organization"]
    person = normalized_payload["person"]
    link = normalized_payload["link"]

    if not organization["name"] and not person["full_name"]:
        errors.append("Row must contain at least an organization or a person.")

    if organization["email"] and "@" not in organization["email"]:
        errors.append("Organization email is invalid.")
    if person["email"] and "@" not in person["email"]:
        errors.append("Person email is invalid.")

    if link["status"] and link["status"] not in {"ACTIVE", "INACTIVE"}:
        errors.append("Link status must be ACTIVE or INACTIVE.")

    existing_categories = {
        item.casefold(): item
        for item in Category.objects.values_list("name", flat=True)
    }
    existing_subcategories = {
        item.casefold(): item
        for item in Subcategory.objects.values_list("name", flat=True)
    }

    for name in organization["categories"] + person["categories"]:
        if name.casefold() not in existing_categories:
            warnings.append(f"Unknown category: {name}")
    for name in organization["subcategories"] + person["subcategories"]:
        if name.casefold() not in existing_subcategories:
            warnings.append(f"Unknown subcategory: {name}")

    seen_secondary = set()
    for contact in person["secondary_contacts"]:
        key = (contact["type"], contact["value"].casefold())
        if key in seen_secondary:
            warnings.append(f"Duplicate secondary contact: {contact['value']}")
            continue
        seen_secondary.add(key)
        if contact["type"] == "EMAIL" and "@" not in contact["value"]:
            errors.append(f"Invalid secondary email: {contact['value']}")

    return errors, warnings
