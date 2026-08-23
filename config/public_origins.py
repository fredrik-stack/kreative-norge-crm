from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlsplit


_DNS_HOST_RE = re.compile(
    r"(?=.{1,253}\Z)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)(?:\.(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?))*\Z"
)


class InvalidPublicOrigin(ValueError):
    pass


def _canonical_hostname(value: str) -> str:
    hostname = value.rstrip(".").casefold()
    if not hostname:
        raise InvalidPublicOrigin("Origin host is empty.")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        try:
            hostname = hostname.encode("idna").decode("ascii")
        except UnicodeError as error:
            raise InvalidPublicOrigin("Origin host is invalid.") from error
        if not _DNS_HOST_RE.fullmatch(hostname):
            raise InvalidPublicOrigin("Origin host is invalid.")
        return hostname
    return address.compressed


def exact_allowed_hostnames(values: list[str]) -> frozenset[str]:
    hostnames: set[str] = set()
    for raw_value in values:
        value = raw_value.strip()
        if not value or value == "*" or value.startswith("."):
            continue
        try:
            parsed = urlsplit(f"//{value}")
            if parsed.username is not None or parsed.password is not None:
                continue
            hostname = parsed.hostname
            parsed.port
        except ValueError:
            continue
        if hostname is None:
            continue
        try:
            hostnames.add(_canonical_hostname(hostname))
        except InvalidPublicOrigin:
            continue
    return frozenset(hostnames)


def normalize_public_origin(
    raw_value: str,
    *,
    setting_name: str,
    allowed_hosts: list[str],
    debug: bool,
) -> str:
    if not isinstance(raw_value, str) or not raw_value:
        raise InvalidPublicOrigin(f"{setting_name} must be set.")
    if raw_value != raw_value.strip() or any(
        character.isspace() or ord(character) < 32 or ord(character) == 127
        for character in raw_value
    ):
        raise InvalidPublicOrigin(f"{setting_name} contains whitespace or control characters.")
    if "\\" in raw_value:
        raise InvalidPublicOrigin(f"{setting_name} contains an invalid separator.")

    try:
        parsed = urlsplit(raw_value)
        port = parsed.port
    except ValueError as error:
        raise InvalidPublicOrigin(f"{setting_name} is not a valid URL.") from error
    scheme = parsed.scheme.casefold()
    if scheme not in {"http", "https"} or not parsed.netloc or parsed.hostname is None:
        raise InvalidPublicOrigin(f"{setting_name} requires an HTTP(S) scheme and host.")
    if not debug and scheme != "https":
        raise InvalidPublicOrigin(f"{setting_name} must use HTTPS outside DEBUG.")
    if parsed.username is not None or parsed.password is not None:
        raise InvalidPublicOrigin(f"{setting_name} cannot contain user information.")
    if parsed.path not in {"", "/"}:
        raise InvalidPublicOrigin(f"{setting_name} cannot contain a path.")
    if parsed.query:
        raise InvalidPublicOrigin(f"{setting_name} cannot contain a query.")
    if parsed.fragment:
        raise InvalidPublicOrigin(f"{setting_name} cannot contain a fragment.")

    hostname = _canonical_hostname(parsed.hostname)
    if hostname not in exact_allowed_hostnames(allowed_hosts):
        raise InvalidPublicOrigin(
            f"{setting_name} host must be an exact non-wildcard DJANGO_ALLOWED_HOSTS entry."
        )
    host = f"[{hostname}]" if ":" in hostname else hostname
    if port is not None and not (
        (scheme == "https" and port == 443) or (scheme == "http" and port == 80)
    ):
        host = f"{host}:{port}"
    return f"{scheme}://{host}"
