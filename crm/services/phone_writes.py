from __future__ import annotations

from dataclasses import dataclass

from crm.services.phone_normalization import (
    PhoneNormalizationReason,
    PhoneNormalizationStatus,
    normalize_phone,
)


@dataclass(frozen=True)
class PhoneWriteIdentity:
    raw_value: str | None
    normalized_value: str | None
    normalization_region: str | None


class PhoneWriteValidationError(ValueError):
    def __init__(
        self,
        *,
        status: PhoneNormalizationStatus,
        reason_code: PhoneNormalizationReason,
    ) -> None:
        self.status = status
        self.reason_code = reason_code
        super().__init__(phone_error_message(status=status, reason_code=reason_code))


def phone_error_message(
    *,
    status: PhoneNormalizationStatus,
    reason_code: PhoneNormalizationReason,
) -> str:
    if status == PhoneNormalizationStatus.NEEDS_REGION:
        return "Velg land/region for et nasjonalt telefonnummer."
    if reason_code == PhoneNormalizationReason.INVALID_REGION:
        return "Velg en gyldig land-/regionkode."
    if reason_code == PhoneNormalizationReason.EXTENSION_NOT_SUPPORTED:
        return "Telefonnummer med internnummer støttes ikke."
    return "Telefonnummeret er ugyldig."


def prepare_phone_write(value: str | None, *, region: str | None) -> PhoneWriteIdentity:
    raw_value = (value or "").strip() or None
    if raw_value is None:
        return PhoneWriteIdentity(
            raw_value=None,
            normalized_value=None,
            normalization_region=None,
        )

    result = normalize_phone(raw_value, region=region)
    if result.status != PhoneNormalizationStatus.VALID:
        raise PhoneWriteValidationError(
            status=result.status,
            reason_code=result.reason_code or PhoneNormalizationReason.PARSE_ERROR,
        )

    return PhoneWriteIdentity(
        raw_value=raw_value,
        normalized_value=result.e164,
        normalization_region=result.region_used,
    )
