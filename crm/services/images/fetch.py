from __future__ import annotations

from dataclasses import dataclass
import http.client
import ipaddress
import socket
import ssl
from typing import Callable, Iterable
from urllib.parse import parse_qsl, urljoin, urlsplit, urlunsplit

from .processing import MAX_SOURCE_BYTES


MAX_REDIRECTS = 3
CONNECT_TIMEOUT_SECONDS = 5.0
READ_TIMEOUT_SECONDS = 10.0
READ_CHUNK_BYTES = 64 * 1024
IMAGE_CONTENT_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})
HTML_CONTENT_TYPES = frozenset({"text/html", "application/xhtml+xml"})
METADATA_HOSTS = frozenset(
    {
        "metadata",
        "metadata.google.internal",
        "metadata.goog",
        "instance-data",
        "instance-data.ec2.internal",
    }
)
SENSITIVE_QUERY_KEYS = frozenset(
    {
        "credential",
        "credentials",
        "signature",
        "sig",
        "token",
        "access_token",
        "id_token",
        "refresh_token",
        "auth",
        "authorization",
        "api_key",
        "apikey",
        "access_key",
        "secret",
        "secret_key",
        "password",
        "passwd",
        "key",
        "key-pair-id",
        "jwt",
        "code",
        "policy",
        "expires",
        "sv",
        "se",
        "sp",
        "sr",
    }
)
SENSITIVE_QUERY_KEY_PREFIXES = ("x-amz-", "x-goog-")


class SecureImageFetchError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class SecureFetchResult:
    requested_url: str
    final_url: str
    content_type: str
    body: bytes
    redirect_count: int


Resolver = Callable[[str, int], Iterable[str]]
ConnectionFactory = Callable[[str, str, int, str, float, float], http.client.HTTPConnection]


def _default_resolver(hostname: str, port: int) -> tuple[str, ...]:
    try:
        results = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror as error:
        raise SecureImageFetchError("dns_failed", "Image host could not be resolved.") from error
    addresses = tuple(dict.fromkeys(item[4][0] for item in results))
    if not addresses:
        raise SecureImageFetchError("dns_failed", "Image host has no usable address.")
    return addresses


class _PinnedHTTPConnection(http.client.HTTPConnection):
    def __init__(
        self,
        hostname: str,
        port: int,
        pinned_ip: str,
        connect_timeout: float,
        read_timeout: float,
    ) -> None:
        super().__init__(hostname, port=port, timeout=connect_timeout)
        self._pinned_ip = pinned_ip
        self._read_timeout = read_timeout

    def connect(self) -> None:
        self.sock = socket.create_connection(
            (self._pinned_ip, self.port),
            timeout=self.timeout,
            source_address=self.source_address,
        )
        self.sock.settimeout(self._read_timeout)


class _PinnedHTTPSConnection(_PinnedHTTPConnection):
    def __init__(
        self,
        hostname: str,
        port: int,
        pinned_ip: str,
        connect_timeout: float,
        read_timeout: float,
    ) -> None:
        super().__init__(hostname, port, pinned_ip, connect_timeout, read_timeout)
        self._context = ssl.create_default_context()

    def connect(self) -> None:
        super().connect()
        assert self.sock is not None
        self.sock = self._context.wrap_socket(self.sock, server_hostname=self.host)
        self.sock.settimeout(self._read_timeout)


def _default_connection_factory(
    scheme: str,
    hostname: str,
    port: int,
    pinned_ip: str,
    connect_timeout: float,
    read_timeout: float,
) -> http.client.HTTPConnection:
    connection_class = _PinnedHTTPSConnection if scheme == "https" else _PinnedHTTPConnection
    return connection_class(
        hostname,
        port,
        pinned_ip,
        connect_timeout,
        read_timeout,
    )


def normalize_external_url(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SecureImageFetchError("invalid_url", "Image URL is required.")
    if len(value.strip()) > 2048:
        raise SecureImageFetchError("invalid_url", "Image URL exceeds the supported length.")
    try:
        parsed = urlsplit(value.strip())
        port = parsed.port
    except ValueError as error:
        raise SecureImageFetchError("invalid_url", "Image URL is invalid.") from error
    scheme = parsed.scheme.casefold()
    if scheme not in {"http", "https"} or not parsed.hostname:
        raise SecureImageFetchError("invalid_url", "Image URL must use HTTP or HTTPS.")
    if parsed.username is not None or parsed.password is not None:
        raise SecureImageFetchError("credentials_forbidden", "Image URL cannot contain userinfo.")
    hostname = parsed.hostname.rstrip(".").casefold()
    if hostname == "localhost" or hostname.endswith(".localhost") or hostname.endswith(".local"):
        raise SecureImageFetchError("private_host", "Local image hosts are not allowed.")
    if hostname in METADATA_HOSTS:
        raise SecureImageFetchError("metadata_host", "Metadata hosts are not allowed.")
    query_keys = {key.strip().casefold() for key, _ in parse_qsl(parsed.query, keep_blank_values=True)}
    if any(
        key in SENSITIVE_QUERY_KEYS or key.startswith(SENSITIVE_QUERY_KEY_PREFIXES)
        for key in query_keys
    ):
        raise SecureImageFetchError(
            "credentials_forbidden",
            "Signed, credentialed, or tokenized image URLs are not allowed.",
        )
    try:
        ascii_hostname = hostname.encode("idna").decode("ascii")
    except UnicodeError as error:
        raise SecureImageFetchError("invalid_url", "Image hostname is invalid.") from error
    default_port = 443 if scheme == "https" else 80
    rendered_hostname = f"[{ascii_hostname}]" if ":" in ascii_hostname else ascii_hostname
    netloc = rendered_hostname if port in {None, default_port} else f"{rendered_hostname}:{port}"
    path = parsed.path or "/"
    return urlunsplit((scheme, netloc, path, parsed.query, ""))


def _validated_addresses(
    hostname: str,
    port: int,
    resolver: Resolver,
) -> tuple[str, ...]:
    try:
        addresses = tuple(dict.fromkeys(resolver(hostname, port)))
    except SecureImageFetchError:
        raise
    except (OSError, ValueError) as error:
        raise SecureImageFetchError("dns_failed", "Image host could not be resolved.") from error
    if not addresses:
        raise SecureImageFetchError("dns_failed", "Image host has no usable address.")
    normalized: list[str] = []
    for address in addresses:
        try:
            parsed_address = ipaddress.ip_address(address)
        except ValueError as error:
            raise SecureImageFetchError("dns_failed", "Image host returned an invalid address.") from error
        if not parsed_address.is_global:
            raise SecureImageFetchError("private_address", "Image host resolved to a non-public address.")
        normalized.append(parsed_address.compressed)
    return tuple(normalized)


def _sniff_image_content_type(body: bytes) -> str | None:
    if body.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if body.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(body) >= 12 and body[:4] == b"RIFF" and body[8:12] == b"WEBP":
        return "image/webp"
    return None


def _assert_connected_peer(connection: http.client.HTTPConnection, pinned_ip: str) -> None:
    sock = getattr(connection, "sock", None)
    if sock is None:
        return
    try:
        peer_ip = ipaddress.ip_address(sock.getpeername()[0])
        expected_ip = ipaddress.ip_address(pinned_ip)
    except (OSError, ValueError, TypeError) as error:
        raise SecureImageFetchError("peer_mismatch", "Remote peer address could not be verified.") from error
    if peer_ip != expected_ip:
        raise SecureImageFetchError("peer_mismatch", "Remote peer does not match the validated address.")


def fetch_external_resource(
    url: str,
    *,
    expected: str,
    max_bytes: int = MAX_SOURCE_BYTES,
    resolver: Resolver = _default_resolver,
    connection_factory: ConnectionFactory = _default_connection_factory,
) -> SecureFetchResult:
    if expected not in {"image", "html"}:
        raise ValueError("expected must be image or html")
    requested_url = normalize_external_url(url)
    current_url = requested_url

    for redirect_count in range(MAX_REDIRECTS + 1):
        parsed = urlsplit(current_url)
        scheme = parsed.scheme
        hostname = parsed.hostname or ""
        port = parsed.port or (443 if scheme == "https" else 80)
        addresses = _validated_addresses(hostname, port, resolver)
        connection = connection_factory(
            scheme,
            hostname,
            port,
            addresses[0],
            CONNECT_TIMEOUT_SECONDS,
            READ_TIMEOUT_SECONDS,
        )
        path = urlunsplit(("", "", parsed.path or "/", parsed.query, ""))
        try:
            connection.request(
                "GET",
                path,
                headers={
                    "Accept": "image/jpeg,image/png,image/webp" if expected == "image" else "text/html,application/xhtml+xml",
                    "Accept-Encoding": "identity",
                    "Host": parsed.netloc,
                    "User-Agent": "KreativeNorgeImageDiscovery/1.0",
                },
            )
            response = connection.getresponse()
            _assert_connected_peer(connection, addresses[0])
            status = response.status
            if status in {301, 302, 303, 307, 308}:
                location = response.getheader("Location")
                if not location:
                    raise SecureImageFetchError("invalid_redirect", "Redirect is missing a target.")
                if redirect_count >= MAX_REDIRECTS:
                    raise SecureImageFetchError("too_many_redirects", "Image fetch exceeded redirect limit.")
                target_url = normalize_external_url(urljoin(current_url, location))
                if scheme == "https" and urlsplit(target_url).scheme == "http":
                    raise SecureImageFetchError("https_downgrade", "HTTPS redirects cannot downgrade to HTTP.")
                current_url = target_url
                continue
            if status < 200 or status >= 300:
                raise SecureImageFetchError("http_error", "Remote image source returned an error.")

            content_type = (response.getheader("Content-Type") or "").split(";", 1)[0].strip().casefold()
            allowed_types = IMAGE_CONTENT_TYPES if expected == "image" else HTML_CONTENT_TYPES
            if content_type not in allowed_types:
                raise SecureImageFetchError("content_type", "Remote response has an unsupported content type.")
            content_length = response.getheader("Content-Length")
            if content_length:
                try:
                    declared_size = int(content_length)
                except ValueError as error:
                    raise SecureImageFetchError("invalid_length", "Remote response has an invalid length.") from error
                if declared_size < 0 or declared_size > max_bytes:
                    raise SecureImageFetchError("response_too_large", "Remote response exceeds the size limit.")

            chunks: list[bytes] = []
            total = 0
            while True:
                chunk = response.read(min(READ_CHUNK_BYTES, max_bytes + 1 - total))
                if not chunk:
                    break
                chunks.append(chunk)
                total += len(chunk)
                if total > max_bytes:
                    raise SecureImageFetchError("response_too_large", "Remote response exceeds the size limit.")
            body = b"".join(chunks)
            if not body:
                raise SecureImageFetchError("empty_response", "Remote response is empty.")
            if expected == "image":
                sniffed_type = _sniff_image_content_type(body)
                if sniffed_type is None or sniffed_type != content_type:
                    raise SecureImageFetchError("image_mismatch", "Remote response is not the declared image type.")
            else:
                html_prefix = body.lstrip(b"\xef\xbb\xbf\x00\t\r\n ")[:512].casefold()
                if not html_prefix.startswith((b"<!doctype html", b"<html", b"<head", b"<body")):
                    raise SecureImageFetchError("html_mismatch", "Remote response is not HTML.")
            return SecureFetchResult(
                requested_url=requested_url,
                final_url=current_url,
                content_type=content_type,
                body=body,
                redirect_count=redirect_count,
            )
        except SecureImageFetchError:
            raise
        except (TimeoutError, socket.timeout) as error:
            raise SecureImageFetchError("timeout", "Remote image source timed out.") from error
        except (http.client.HTTPException, OSError, ssl.SSLError) as error:
            raise SecureImageFetchError("connection_failed", "Remote image source could not be read.") from error
        finally:
            connection.close()

    raise SecureImageFetchError("too_many_redirects", "Image fetch exceeded redirect limit.")
