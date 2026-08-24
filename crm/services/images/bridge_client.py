from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import socket
import struct
from typing import Mapping

from django.conf import settings

from image_safety.release_keys import (
    REQUIRED_RELEASE_VARIANTS,
    build_public_release_key,
    canonical_release_id,
)
from image_safety.ledger import (
    activation_event_id,
    release_denial_event_id,
    reservation_event_id,
    tenant_checksum_denial_event_id,
)


PROTOCOL_VERSION = 1
MAX_FRAME_BYTES = 16 * 1024


class ImageSafetyBridgeError(RuntimeError):
    def __init__(self, code: str, message: str, *, retryable: bool):
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class ImageSafetyBridgeConflict(ImageSafetyBridgeError):
    pass


class ImageSafetyBridgeUnavailable(ImageSafetyBridgeError):
    pass


@dataclass(frozen=True)
class BridgeRenditionSnapshot:
    variant: str
    output_format: str
    artifact_storage_key: str
    artifact_checksum_sha256: str


@dataclass(frozen=True)
class BridgeReservation:
    event_id: str
    event_sequence: int
    release_id: str
    public_keys: Mapping[str, str]
    disposition: str
    anchor_cursor: int


@dataclass(frozen=True)
class BridgeActivation:
    event_id: str
    event_sequence: int
    release_id: str
    disposition: str
    anchor_cursor: int


@dataclass(frozen=True)
class BridgeAuthorization:
    authorized: bool
    category: str
    release_id: str
    variant: str
    read_cursor: int


@dataclass(frozen=True)
class BridgeDeny:
    release_event_id: str
    release_event_sequence: int
    checksum_event_id: str
    checksum_event_sequence: int
    release_disposition: str
    checksum_disposition: str
    anchor_cursor: int


@dataclass(frozen=True)
class BridgeChecksumCheck:
    denied: bool
    read_cursor: int


@dataclass(frozen=True)
class BridgeLegacyGuard:
    blocked: bool
    read_cursor: int


def _encode_frame(value: Mapping[str, object]) -> bytes:
    body = json.dumps(
        value, ensure_ascii=True, allow_nan=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    if not body or len(body) > MAX_FRAME_BYTES:
        raise ImageSafetyBridgeError(
            "invalid_request", "Safety request exceeds the protocol limit.", retryable=False
        )
    return struct.pack("!I", len(body)) + body


def _receive_exact(connection: socket.socket, size: int) -> bytes:
    chunks = []
    remaining = size
    while remaining:
        chunk = connection.recv(remaining)
        if not chunk:
            raise ImageSafetyBridgeUnavailable(
                "safety_unavailable",
                "Safety bridge response was truncated.",
                retryable=True,
            )
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _receive_frame(connection: socket.socket) -> object:
    header = _receive_exact(connection, 4)
    length = struct.unpack("!I", header)[0]
    if length == 0 or length > MAX_FRAME_BYTES:
        raise ImageSafetyBridgeUnavailable(
            "safety_unavailable",
            "Safety bridge response length is invalid.",
            retryable=True,
        )
    body = _receive_exact(connection, length)
    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ImageSafetyBridgeUnavailable(
            "safety_unavailable",
            "Safety bridge response is malformed.",
            retryable=True,
        ) from error


def _require_object(value: object, fields: set[str], label: str) -> dict:
    if not isinstance(value, dict) or set(value) != fields:
        raise ImageSafetyBridgeUnavailable(
            "safety_unavailable",
            f"{label} has an unexpected schema.",
            retryable=True,
        )
    return value


def _canonical_uuid(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise ImageSafetyBridgeUnavailable(
            "safety_unavailable", f"{label} is invalid.", retryable=True
        )
    try:
        return canonical_release_id(value)
    except (TypeError, ValueError) as error:
        raise ImageSafetyBridgeUnavailable(
            "safety_unavailable", f"{label} is invalid.", retryable=True
        ) from error


class ImageSafetyBridgeClient:
    def __init__(self, *, socket_path: Path | None = None, timeout: float | None = None):
        self.socket_path = Path(
            socket_path or settings.PUBLIC_IMAGE_SAFETY_BRIDGE_SOCKET
        )
        self.timeout = float(
            timeout
            if timeout is not None
            else settings.PUBLIC_IMAGE_SAFETY_BRIDGE_TIMEOUT
        )
        if not self.socket_path.is_absolute():
            raise ImageSafetyBridgeError(
                "invalid_configuration",
                "Safety bridge socket path must be absolute.",
                retryable=False,
            )

    def _request(self, operation: str, payload: Mapping[str, object]) -> dict:
        frame = _encode_frame(
            {
                "protocol_version": PROTOCOL_VERSION,
                "operation": operation,
                "payload": payload,
            }
        )
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
                connection.settimeout(self.timeout)
                connection.connect(str(self.socket_path))
                connection.sendall(frame)
                response = _receive_frame(connection)
        except ImageSafetyBridgeError:
            raise
        except (OSError, socket.timeout) as error:
            raise ImageSafetyBridgeUnavailable(
                "safety_unavailable",
                "Safety bridge is unavailable.",
                retryable=True,
            ) from error

        if not isinstance(response, dict):
            raise ImageSafetyBridgeUnavailable(
                "safety_unavailable",
                "Safety bridge response is not an object.",
                retryable=True,
            )
        if response.get("protocol_version") != PROTOCOL_VERSION:
            raise ImageSafetyBridgeUnavailable(
                "safety_unavailable",
                "Safety bridge protocol version is invalid.",
                retryable=True,
            )
        if response.get("operation") != operation:
            raise ImageSafetyBridgeUnavailable(
                "safety_unavailable",
                "Safety bridge operation response does not match the request.",
                retryable=True,
            )
        if response.get("result") == "error":
            error_response = _require_object(
                response,
                {
                    "protocol_version",
                    "operation",
                    "result",
                    "code",
                    "retryable",
                    "message",
                    "correlation_id",
                },
                "Safety bridge error response",
            )
            if (
                not isinstance(error_response["code"], str)
                or not isinstance(error_response["retryable"], bool)
                or not isinstance(error_response["message"], str)
                or not isinstance(error_response["correlation_id"], str)
            ):
                raise ImageSafetyBridgeUnavailable(
                    "safety_unavailable",
                    "Safety bridge error response is malformed.",
                    retryable=True,
                )
            error_class = (
                ImageSafetyBridgeUnavailable
                if error_response["retryable"]
                else ImageSafetyBridgeConflict
            )
            raise error_class(
                error_response["code"],
                error_response["message"],
                retryable=error_response["retryable"],
            )
        if response.get("result") != "success":
            raise ImageSafetyBridgeUnavailable(
                "safety_unavailable",
                "Safety bridge result is invalid.",
                retryable=True,
            )
        return response

    @staticmethod
    def _confirmation(response: dict, event_sequence: int) -> int:
        confirmation = _require_object(
            response.get("confirmation"), {"anchored", "anchor_cursor", "archive_reused"}, "Confirmation"
        )
        cursor = confirmation["anchor_cursor"]
        if (
            confirmation["anchored"] is not True
            or not isinstance(confirmation["archive_reused"], bool)
            or isinstance(cursor, bool)
            or not isinstance(cursor, int)
            or cursor < event_sequence
        ):
            raise ImageSafetyBridgeUnavailable(
                "safety_unavailable",
                "Safety bridge confirmation is not anchored.",
                retryable=True,
            )
        return cursor

    def reserve(
        self,
        *,
        tenant_id: int,
        organization_id: int,
        selection_id: int,
        selection_revision: int,
        rendition_set_id: int,
        renditions: tuple[BridgeRenditionSnapshot, ...],
    ) -> BridgeReservation:
        request_payload = {
            "tenant_id": tenant_id,
            "organization_id": organization_id,
            "selection_id": selection_id,
            "selection_revision": selection_revision,
            "rendition_set_id": rendition_set_id,
            "renditions": [
                {
                    "variant": item.variant,
                    "output_format": item.output_format,
                    "artifact_storage_key": item.artifact_storage_key,
                    "artifact_checksum_sha256": item.artifact_checksum_sha256,
                }
                for item in renditions
            ],
        }
        response = self._request("reserve", request_payload)
        response = _require_object(
            response,
            {
                "protocol_version",
                "operation",
                "result",
                "disposition",
                "reservation",
                "confirmation",
            },
            "Reservation response",
        )
        if response["disposition"] not in {"new", "idempotent_retry"}:
            raise ImageSafetyBridgeUnavailable(
                "safety_unavailable", "Reservation disposition is invalid.", retryable=True
            )
        reservation = _require_object(
            response["reservation"],
            {"event_id", "event_sequence", "release_id", "public_keys"},
            "Reservation",
        )
        sequence = reservation["event_sequence"]
        if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence <= 0:
            raise ImageSafetyBridgeUnavailable(
                "safety_unavailable", "Reservation sequence is invalid.", retryable=True
            )
        try:
            release_id = canonical_release_id(reservation["release_id"])
        except Exception as error:
            raise ImageSafetyBridgeUnavailable(
                "safety_unavailable", "Reservation release ID is invalid.", retryable=True
            ) from error
        if not isinstance(reservation["event_id"], str) or not reservation["event_id"]:
            raise ImageSafetyBridgeUnavailable(
                "safety_unavailable", "Reservation event ID is invalid.", retryable=True
            )
        expected_event_id = reservation_event_id(
            tenant_id=tenant_id,
            organization_id=organization_id,
            selection_id=selection_id,
            selection_revision=selection_revision,
        )
        if reservation["event_id"] != expected_event_id:
            raise ImageSafetyBridgeUnavailable(
                "safety_unavailable",
                "Reservation event ID is not canonical.",
                retryable=True,
            )
        public_keys = reservation["public_keys"]
        if not isinstance(public_keys, dict) or set(public_keys) != REQUIRED_RELEASE_VARIANTS:
            raise ImageSafetyBridgeUnavailable(
                "safety_unavailable", "Reservation public keys are incomplete.", retryable=True
            )
        formats = {item.variant: item.output_format for item in renditions}
        if set(formats) != REQUIRED_RELEASE_VARIANTS:
            raise ImageSafetyBridgeError(
                "invalid_request",
                "Reservation renditions are incomplete.",
                retryable=False,
            )
        for variant, key in public_keys.items():
            if key != build_public_release_key(release_id, variant, formats[variant]):
                raise ImageSafetyBridgeUnavailable(
                    "safety_unavailable",
                    "Reservation public key is not canonical.",
                    retryable=True,
                )
        return BridgeReservation(
            event_id=reservation["event_id"],
            event_sequence=sequence,
            release_id=release_id,
            public_keys=dict(public_keys),
            disposition=response["disposition"],
            anchor_cursor=self._confirmation(response, sequence),
        )

    def activate(
        self,
        *,
        release_id: str,
        tenant_id: int,
        source_checksum_sha256: str,
    ) -> BridgeActivation:
        response = self._request(
            "activate",
            {
                "release_id": release_id,
                "tenant_id": tenant_id,
                "source_checksum_sha256": source_checksum_sha256,
            },
        )
        response = _require_object(
            response,
            {
                "protocol_version",
                "operation",
                "result",
                "disposition",
                "event",
                "confirmation",
            },
            "Activation response",
        )
        if response["disposition"] not in {"new", "idempotent_retry"}:
            raise ImageSafetyBridgeUnavailable(
                "safety_unavailable", "Activation disposition is invalid.", retryable=True
            )
        event = _require_object(
            response["event"], {"event_id", "event_sequence", "release_id"}, "Activation event"
        )
        sequence = event["event_sequence"]
        canonical_id = _canonical_uuid(event["release_id"], "Activation release ID")
        if canonical_id != _canonical_uuid(release_id, "Requested release ID"):
            raise ImageSafetyBridgeUnavailable(
                "safety_unavailable", "Activation release ID does not match.", retryable=True
            )
        if (
            not isinstance(event["event_id"], str)
            or event["event_id"] != activation_event_id(canonical_id)
            or isinstance(sequence, bool)
            or not isinstance(sequence, int)
            or sequence <= 0
        ):
            raise ImageSafetyBridgeUnavailable(
                "safety_unavailable", "Activation event is malformed.", retryable=True
            )
        return BridgeActivation(
            event_id=event["event_id"],
            event_sequence=sequence,
            release_id=canonical_id,
            disposition=response["disposition"],
            anchor_cursor=self._confirmation(response, sequence),
        )

    def authorize(
        self,
        *,
        release_id: str,
        tenant_id: int,
        organization_id: int,
        variant: str,
        public_storage_key: str,
        artifact_checksum_sha256: str,
        source_checksum_sha256: str,
    ) -> BridgeAuthorization:
        requested_release_id = _canonical_uuid(release_id, "Requested release ID")
        response = self._request(
            "authorize",
            {
                "release_id": requested_release_id,
                "tenant_id": tenant_id,
                "organization_id": organization_id,
                "variant": variant,
                "public_storage_key": public_storage_key,
                "artifact_checksum_sha256": artifact_checksum_sha256,
                "source_checksum_sha256": source_checksum_sha256,
            },
        )
        response = _require_object(
            response,
            {"protocol_version", "operation", "result", "authorization"},
            "Authorization response",
        )
        authorization = _require_object(
            response["authorization"],
            {
                "authorized",
                "category",
                "release_id",
                "variant",
                "read_cursor",
            },
            "Authorization",
        )
        canonical_id = _canonical_uuid(
            authorization["release_id"], "Authorization release ID"
        )
        cursor = authorization["read_cursor"]
        if (
            not isinstance(authorization["authorized"], bool)
            or authorization["category"]
            not in {
                "authorized", "unknown", "not_active", "scope_mismatch",
                "checksum_denied",
            }
            or canonical_id != requested_release_id
            or authorization["variant"] != variant
            or isinstance(cursor, bool)
            or not isinstance(cursor, int)
            or cursor < 0
            or (authorization["authorized"] is True
                and authorization["category"] != "authorized")
            or (authorization["authorized"] is False
                and authorization["category"] == "authorized")
        ):
            raise ImageSafetyBridgeUnavailable(
                "safety_unavailable",
                "Safety authorization response is malformed.",
                retryable=True,
            )
        return BridgeAuthorization(
            authorized=authorization["authorized"],
            category=authorization["category"],
            release_id=canonical_id,
            variant=variant,
            read_cursor=cursor,
        )

    def deny(
        self,
        *,
        release_id: str,
        tenant_id: int,
        organization_id: int,
        source_checksum_sha256: str,
        reason_code: str,
    ) -> BridgeDeny:
        canonical_id = _canonical_uuid(release_id, "Requested release ID")
        response = self._request(
            "deny",
            {
                "release_id": canonical_id,
                "tenant_id": tenant_id,
                "organization_id": organization_id,
                "source_checksum_sha256": source_checksum_sha256,
                "reason_code": reason_code,
            },
        )
        response = _require_object(
            response,
            {
                "protocol_version", "operation", "result",
                "release_disposition", "checksum_disposition", "events",
                "confirmation",
            },
            "Deny response",
        )
        dispositions = {
            response["release_disposition"], response["checksum_disposition"]
        }
        if not dispositions <= {"new", "idempotent_retry"}:
            raise ImageSafetyBridgeUnavailable(
                "safety_unavailable", "Deny disposition is invalid.", retryable=True
            )
        events = _require_object(
            response["events"],
            {"release_denied", "tenant_checksum_denied"},
            "Deny events",
        )
        release_event = _require_object(
            events["release_denied"],
            {"event_id", "event_sequence", "release_id"},
            "Release denial event",
        )
        checksum_event = _require_object(
            events["tenant_checksum_denied"],
            {"event_id", "event_sequence"},
            "Checksum denial event",
        )
        release_sequence = release_event["event_sequence"]
        checksum_sequence = checksum_event["event_sequence"]
        if (
            _canonical_uuid(release_event["release_id"], "Denied release ID")
            != canonical_id
            or release_event["event_id"] != release_denial_event_id(canonical_id)
            or checksum_event["event_id"]
            != tenant_checksum_denial_event_id(
                tenant_id=tenant_id,
                source_checksum_sha256=source_checksum_sha256,
            )
            or any(
                isinstance(sequence, bool)
                or not isinstance(sequence, int)
                or sequence <= 0
                for sequence in (release_sequence, checksum_sequence)
            )
        ):
            raise ImageSafetyBridgeUnavailable(
                "safety_unavailable", "Deny events are malformed.", retryable=True
            )
        return BridgeDeny(
            release_event_id=release_event["event_id"],
            release_event_sequence=release_sequence,
            checksum_event_id=checksum_event["event_id"],
            checksum_event_sequence=checksum_sequence,
            release_disposition=response["release_disposition"],
            checksum_disposition=response["checksum_disposition"],
            anchor_cursor=self._confirmation(
                response, max(release_sequence, checksum_sequence)
            ),
        )

    def check_checksum(
        self, *, tenant_id: int, source_checksum_sha256: str
    ) -> BridgeChecksumCheck:
        response = self._request(
            "check_checksum",
            {
                "tenant_id": tenant_id,
                "source_checksum_sha256": source_checksum_sha256,
            },
        )
        response = _require_object(
            response,
            {"protocol_version", "operation", "result", "checksum"},
            "Checksum response",
        )
        result = _require_object(
            response["checksum"], {"denied", "read_cursor"}, "Checksum result"
        )
        if (
            not isinstance(result["denied"], bool)
            or isinstance(result["read_cursor"], bool)
            or not isinstance(result["read_cursor"], int)
            or result["read_cursor"] < 0
        ):
            raise ImageSafetyBridgeUnavailable(
                "safety_unavailable", "Checksum response is malformed.", retryable=True
            )
        return BridgeChecksumCheck(**result)

    def legacy_guard(
        self, *, tenant_id: int, organization_id: int
    ) -> BridgeLegacyGuard:
        response = self._request(
            "legacy_guard",
            {"tenant_id": tenant_id, "organization_id": organization_id},
        )
        response = _require_object(
            response,
            {"protocol_version", "operation", "result", "legacy_guard"},
            "Legacy guard response",
        )
        result = _require_object(
            response["legacy_guard"], {"blocked", "read_cursor"}, "Legacy guard"
        )
        if (
            not isinstance(result["blocked"], bool)
            or isinstance(result["read_cursor"], bool)
            or not isinstance(result["read_cursor"], int)
            or result["read_cursor"] < 0
        ):
            raise ImageSafetyBridgeUnavailable(
                "safety_unavailable", "Legacy guard response is malformed.", retryable=True
            )
        return BridgeLegacyGuard(**result)
