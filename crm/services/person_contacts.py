from __future__ import annotations

from django.db import transaction

from crm.models import Person, PersonContact
from crm.services.phone_writes import PhoneWriteIdentity


CONTACT_FIELD_BY_TYPE = {
    "EMAIL": "email",
    "PHONE": "phone",
}


def ensure_primary_contact_for_person_field(
    person: Person,
    contact_type: str,
    value: str | None,
    *,
    is_public: bool | None = None,
    phone_identity: PhoneWriteIdentity | None = None,
) -> PersonContact | None:
    normalized_value = (value or "").strip()
    if not normalized_value and contact_type != "PHONE":
        return None

    with transaction.atomic():
        primary = (
            PersonContact.objects.select_for_update()
            .filter(tenant=person.tenant, person=person, type=contact_type, is_primary=True)
            .first()
        )
        if not normalized_value:
            if primary is not None:
                primary.delete()
            return None
        if primary is None:
            create_kwargs = {}
            if contact_type == "PHONE" and phone_identity is not None:
                create_kwargs = {
                    "normalized_value": phone_identity.normalized_value,
                    "normalization_region": phone_identity.normalization_region,
                }
            return PersonContact.objects.create(
                tenant=person.tenant,
                person=person,
                type=contact_type,
                value=normalized_value,
                is_primary=True,
                is_public=bool(is_public) if is_public is not None else False,
                **create_kwargs,
            )

        update_fields: list[str] = []
        if primary.value != normalized_value:
            primary.value = normalized_value
            update_fields.append("value")
        if is_public is not None and primary.is_public != is_public:
            primary.is_public = is_public
            update_fields.append("is_public")
        if contact_type == "PHONE" and phone_identity is not None:
            if primary.normalized_value != phone_identity.normalized_value:
                primary.normalized_value = phone_identity.normalized_value
                update_fields.append("normalized_value")
            if primary.normalization_region != phone_identity.normalization_region:
                primary.normalization_region = phone_identity.normalization_region
                update_fields.append("normalization_region")
        if update_fields:
            primary.save(update_fields=update_fields)
        return primary


def sync_person_fields_to_primary_contacts(
    person: Person,
    *,
    fields: set[str] | None = None,
    phone_identity: PhoneWriteIdentity | None = None,
) -> None:
    if fields is None or "email" in fields:
        ensure_primary_contact_for_person_field(person, "EMAIL", person.email)
    if fields is None or "phone" in fields:
        ensure_primary_contact_for_person_field(
            person,
            "PHONE",
            person.phone,
            phone_identity=phone_identity,
        )


def sync_primary_contact_to_person(contact: PersonContact) -> None:
    if not contact.is_primary:
        return
    field_name = CONTACT_FIELD_BY_TYPE.get(contact.type)
    if field_name is None:
        return
    person = contact.person
    if getattr(person, field_name) == contact.value:
        return
    setattr(person, field_name, contact.value)
    person.save(update_fields=[field_name, "updated_at"])
