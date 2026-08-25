from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import phonenumbers
from phonenumbers import NumberParseException, PhoneNumberFormat


class PhoneNormalizationStatus(str, Enum):
    VALID = "VALID"
    INVALID = "INVALID"
    NEEDS_REGION = "NEEDS_REGION"


class PhoneNormalizationReason(str, Enum):
    EMPTY_INPUT = "EMPTY_INPUT"
    REGION_REQUIRED = "REGION_REQUIRED"
    INVALID_REGION = "INVALID_REGION"
    PARSE_ERROR = "PARSE_ERROR"
    NOT_POSSIBLE = "NOT_POSSIBLE"
    NOT_VALID = "NOT_VALID"
    EXTENSION_NOT_SUPPORTED = "EXTENSION_NOT_SUPPORTED"


@dataclass(frozen=True)
class PhoneNormalizationResult:
    status: PhoneNormalizationStatus
    e164: str | None
    reason_code: PhoneNormalizationReason | None
    region_used: str | None = None


def normalize_phone(
    value: str | None,
    region: str | None = None,
) -> PhoneNormalizationResult:
    """Normalize one phone number without performing I/O or applying a region default."""
    normalized_value = (value or "").strip()
    if not normalized_value:
        return PhoneNormalizationResult(
            status=PhoneNormalizationStatus.INVALID,
            e164=None,
            reason_code=PhoneNormalizationReason.EMPTY_INPUT,
        )

    if normalized_value.startswith("+"):
        parse_region = None
    else:
        if region is None:
            return PhoneNormalizationResult(
                status=PhoneNormalizationStatus.NEEDS_REGION,
                e164=None,
                reason_code=PhoneNormalizationReason.REGION_REQUIRED,
            )

        parse_region = region.strip().upper()
        if parse_region not in phonenumbers.SUPPORTED_REGIONS:
            return PhoneNormalizationResult(
                status=PhoneNormalizationStatus.INVALID,
                e164=None,
                reason_code=PhoneNormalizationReason.INVALID_REGION,
            )

    try:
        parsed = phonenumbers.parse(normalized_value, parse_region)
    except NumberParseException:
        return PhoneNormalizationResult(
            status=PhoneNormalizationStatus.INVALID,
            e164=None,
            reason_code=PhoneNormalizationReason.PARSE_ERROR,
            region_used=parse_region,
        )

    if parsed.extension:
        return PhoneNormalizationResult(
            status=PhoneNormalizationStatus.INVALID,
            e164=None,
            reason_code=PhoneNormalizationReason.EXTENSION_NOT_SUPPORTED,
            region_used=parse_region,
        )

    if not phonenumbers.is_possible_number(parsed):
        return PhoneNormalizationResult(
            status=PhoneNormalizationStatus.INVALID,
            e164=None,
            reason_code=PhoneNormalizationReason.NOT_POSSIBLE,
            region_used=parse_region,
        )

    if not phonenumbers.is_valid_number(parsed):
        return PhoneNormalizationResult(
            status=PhoneNormalizationStatus.INVALID,
            e164=None,
            reason_code=PhoneNormalizationReason.NOT_VALID,
            region_used=parse_region,
        )

    return PhoneNormalizationResult(
        status=PhoneNormalizationStatus.VALID,
        e164=phonenumbers.format_number(parsed, PhoneNumberFormat.E164),
        reason_code=None,
        region_used=parse_region,
    )
