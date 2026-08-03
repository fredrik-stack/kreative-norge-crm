import re
import unicodedata

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator


validate_sha256 = RegexValidator(
    regex=r"^[0-9a-f]{64}$",
    message="Enter a lowercase hexadecimal SHA-256 checksum.",
    code="invalid_sha256",
)


def validate_storage_key(value: str) -> None:
    """Validate a provider-neutral, relative storage object key."""
    if not isinstance(value, str) or not value:
        raise ValidationError("Storage key cannot be empty.", code="empty_storage_key")
    if value.startswith("/") or re.match(r"^[A-Za-z]:/", value):
        raise ValidationError("Storage key must be relative.", code="absolute_storage_key")
    if "\\" in value:
        raise ValidationError("Storage key must use forward slashes.", code="invalid_storage_separator")
    if any(unicodedata.category(character) == "Cc" for character in value):
        raise ValidationError("Storage key cannot contain control characters.", code="control_character")

    segments = value.split("/")
    if any(segment in {"", ".", ".."} for segment in segments):
        raise ValidationError("Storage key contains an unsafe path segment.", code="unsafe_storage_segment")
