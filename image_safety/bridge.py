from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError as FutureTimeout
from contextlib import contextmanager
import json
import logging
import os
import socket
import struct
import threading
from typing import Any, Callable, Mapping
import uuid

from .release_keys import REQUIRED_RELEASE_VARIANTS, canonical_release_id

from .anchor import AnchorBackend, AnchorBackendError, anchor_current_head
from .ledger import (
    AnchorConflictError,
    EventConflictError,
    ImageSafetyLedgerError,
    InvalidLedgerError,
    InvalidTransitionError,
    PublicImageSafetyLedger,
    ReservationRendition,
)


PROTOCOL_VERSION = 1
MAX_FRAME_BYTES = 16 * 1024
FRAME_TIMEOUT_SECONDS = 5.0
OPERATION_TIMEOUT_SECONDS = 45.0
SUPPORTED_OPERATIONS = frozenset({"reserve", "activate", "authorize"})
LOGGER = logging.getLogger("image_safety.bridge")


class BridgeProtocolError(Exception):
    def __init__(self, code: str, message: str, *, retryable: bool = False):
        super().__init__(message)
        self.code = code
        self.safe_message = message
        self.retryable = retryable


class UnauthorizedPeerError(Exception):
    pass


def _strict_object(value: object, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise BridgeProtocolError("invalid_request", f"{label} has an unknown schema.")
    return value


def _positive_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise BridgeProtocolError("invalid_request", f"{label} must be a positive integer.")
    return value


def _reservation_payload(value: object) -> dict[str, Any]:
    payload = _strict_object(
        value,
        {
            "tenant_id",
            "organization_id",
            "selection_id",
            "selection_revision",
            "rendition_set_id",
            "renditions",
        },
        "Reservation payload",
    )
    for field in (
        "tenant_id",
        "organization_id",
        "selection_id",
        "selection_revision",
        "rendition_set_id",
    ):
        payload[field] = _positive_int(payload[field], field)
    if not isinstance(payload["renditions"], list) or len(payload["renditions"]) != 3:
        raise BridgeProtocolError(
            "invalid_request", "Reservation requires exactly three renditions."
        )
    renditions = []
    for item in payload["renditions"]:
        rendition = _strict_object(
            item,
            {
                "variant",
                "output_format",
                "artifact_storage_key",
                "artifact_checksum_sha256",
            },
            "Reservation rendition",
        )
        if not all(isinstance(rendition[field], str) for field in rendition):
            raise BridgeProtocolError(
                "invalid_request", "Reservation rendition fields must be strings."
            )
        renditions.append(ReservationRendition(**rendition))
    payload["renditions"] = tuple(renditions)
    return payload


def _authorization_payload(value: object) -> dict[str, Any]:
    payload = _strict_object(
        value,
        {
            "release_id",
            "tenant_id",
            "organization_id",
            "variant",
            "public_storage_key",
            "artifact_checksum_sha256",
        },
        "Authorization payload",
    )
    try:
        payload["release_id"] = canonical_release_id(payload["release_id"])
    except (TypeError, ValueError) as error:
        raise BridgeProtocolError(
            "invalid_request", "release_id must be a canonical UUIDv4 string."
        ) from error
    for field in ("tenant_id", "organization_id"):
        payload[field] = _positive_int(payload[field], field)
    if payload["variant"] not in REQUIRED_RELEASE_VARIANTS:
        raise BridgeProtocolError("invalid_request", "variant is unsupported.")
    if (
        not isinstance(payload["public_storage_key"], str)
        or not payload["public_storage_key"]
        or payload["public_storage_key"].startswith("/")
        or ".." in payload["public_storage_key"].split("/")
    ):
        raise BridgeProtocolError(
            "invalid_request", "public_storage_key is invalid."
        )
    checksum = payload["artifact_checksum_sha256"]
    if (
        not isinstance(checksum, str)
        or len(checksum) != 64
        or any(character not in "0123456789abcdef" for character in checksum)
    ):
        raise BridgeProtocolError(
            "invalid_request", "artifact_checksum_sha256 is invalid."
        )
    return payload


def _request(value: object) -> tuple[str, dict[str, Any]]:
    request = _strict_object(
        value, {"protocol_version", "operation", "payload"}, "Request"
    )
    if (
        isinstance(request["protocol_version"], bool)
        or not isinstance(request["protocol_version"], int)
        or request["protocol_version"] != PROTOCOL_VERSION
    ):
        raise BridgeProtocolError(
            "unsupported_version", "Protocol version is unsupported."
        )
    operation = request["operation"]
    if not isinstance(operation, str) or operation not in SUPPORTED_OPERATIONS:
        raise BridgeProtocolError("unknown_operation", "Operation is not enabled.")
    if operation == "reserve":
        return operation, _reservation_payload(request["payload"])
    if operation == "authorize":
        return operation, _authorization_payload(request["payload"])
    payload = _strict_object(request["payload"], {"release_id"}, "Activation payload")
    if not isinstance(payload["release_id"], str):
        raise BridgeProtocolError("invalid_request", "release_id must be a UUID string.")
    return operation, payload


class _WriterPreferredReadWriteGate:
    def __init__(self) -> None:
        self._condition = threading.Condition()
        self._readers = 0
        self._writer = False
        self._waiting_writers = 0

    @contextmanager
    def read(self):
        with self._condition:
            while self._writer or self._waiting_writers:
                self._condition.wait()
            self._readers += 1
        try:
            yield
        finally:
            with self._condition:
                self._readers -= 1
                if self._readers == 0:
                    self._condition.notify_all()

    @contextmanager
    def write(self):
        with self._condition:
            self._waiting_writers += 1
            try:
                while self._writer or self._readers:
                    self._condition.wait()
                self._writer = True
            finally:
                self._waiting_writers -= 1
        try:
            yield
        finally:
            with self._condition:
                self._writer = False
                self._condition.notify_all()


class SafetyBridgeOperations:
    def __init__(
        self,
        *,
        ledger: PublicImageSafetyLedger,
        anchor_backend: AnchorBackend,
        expected_repository_id: str,
    ):
        self.ledger = ledger
        self.anchor_backend = anchor_backend
        self.expected_repository_id = expected_repository_id
        self._lifecycle_gate = _WriterPreferredReadWriteGate()

    def _health(self):
        return self.ledger.health(
            expected_repository_id=self.expected_repository_id
        )

    def _require_ready(self) -> None:
        health = self._health()
        if not health.ready and health.code in {"anchor_missing", "anchor_cursor_stale"}:
            anchor_current_head(
                self.ledger,
                self.anchor_backend,
                expected_repository_id=self.expected_repository_id,
            )
            health = self._health()
        if not health.ready:
            raise BridgeProtocolError(
                "safety_unavailable",
                "Safety ledger is not ready.",
                retryable=health.code in {"anchor_missing", "anchor_cursor_stale"},
            )

    def _require_ready_read_only(self):
        health = self._health()
        if not health.ready or health.read_cursor is None:
            raise BridgeProtocolError(
                "safety_unavailable",
                "Safety ledger is not ready.",
                retryable=False,
            )
        return health

    def _confirm(self, event) -> dict[str, Any]:
        anchor = anchor_current_head(
            self.ledger,
            self.anchor_backend,
            expected_repository_id=self.expected_repository_id,
        )
        health = self._health()
        if not health.ready or health.anchor_cursor is None:
            raise BridgeProtocolError(
                "safety_unavailable",
                "Safety event was not confirmed by the off-server anchor.",
                retryable=True,
            )
        if health.anchor_cursor < event.sequence:
            raise BridgeProtocolError(
                "safety_unavailable",
                "Safety anchor cursor does not cover the event.",
                retryable=True,
            )
        return {
            "anchored": True,
            "anchor_cursor": health.anchor_cursor,
            "archive_reused": anchor.reused_archive,
        }

    def _execute_mutation(
        self, operation: str, payload: Mapping[str, Any]
    ) -> dict[str, Any]:
        with self._lifecycle_gate.write():
            self._require_ready()
            if operation == "reserve":
                event = self.ledger.reserve_or_get(**payload)
                confirmation = self._confirm(event)
                return {
                    "protocol_version": PROTOCOL_VERSION,
                    "operation": operation,
                    "result": "success",
                    "disposition": (
                        "idempotent_retry" if event.idempotent_retry else "new"
                    ),
                    "reservation": {
                        "event_id": event.event_id,
                        "event_sequence": event.sequence,
                        "release_id": event.release_id,
                        "public_keys": {
                            variant: rendition["public_storage_key"]
                            for variant, rendition in event.payload["variants"].items()
                        },
                    },
                    "confirmation": confirmation,
                }
            if operation == "activate":
                event = self.ledger.activate_or_get(release_id=payload["release_id"])
                confirmation = self._confirm(event)
                return {
                    "protocol_version": PROTOCOL_VERSION,
                    "operation": operation,
                    "result": "success",
                    "disposition": (
                        "idempotent_retry" if event.idempotent_retry else "new"
                    ),
                    "event": {
                        "event_id": event.event_id,
                        "event_sequence": event.sequence,
                        "release_id": event.release_id,
                    },
                    "confirmation": confirmation,
                }
            raise AssertionError("unreachable mutation operation")

    def _execute_authorize(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        with self._lifecycle_gate.read():
            health = self._require_ready_read_only()
            state = self.ledger.release_state(payload["release_id"])
            category = "unknown"
            authorized = False
            if state is not None:
                category = "not_active"
                if state["state"] == "active":
                    reservation = state["reservation"]
                    rendition = reservation["variants"].get(payload["variant"])
                    expected_scope = (
                        reservation["tenant_id"] == payload["tenant_id"]
                        and reservation["organization_id"]
                        == payload["organization_id"]
                        and rendition is not None
                        and rendition["public_storage_key"]
                        == payload["public_storage_key"]
                        and rendition["artifact_checksum_sha256"]
                        == payload["artifact_checksum_sha256"]
                    )
                    authorized = bool(expected_scope)
                    category = "authorized" if authorized else "scope_mismatch"
            return {
                "protocol_version": PROTOCOL_VERSION,
                "operation": "authorize",
                "result": "success",
                "authorization": {
                    "authorized": authorized,
                    "category": category,
                    "release_id": payload["release_id"],
                    "variant": payload["variant"],
                    "read_cursor": health.read_cursor,
                },
            }

    def execute(self, operation: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        if operation == "authorize":
            return self._execute_authorize(payload)
        return self._execute_mutation(operation, payload)


def _error_response(
    operation: str | None,
    error: BridgeProtocolError,
    correlation_id: str,
) -> dict[str, Any]:
    return {
        "protocol_version": PROTOCOL_VERSION,
        "operation": operation,
        "result": "error",
        "code": error.code,
        "retryable": error.retryable,
        "message": error.safe_message,
        "correlation_id": correlation_id,
    }


def handle_request(value: object, operations: SafetyBridgeOperations) -> dict[str, Any]:
    correlation_id = str(uuid.uuid4())
    operation = value.get("operation") if isinstance(value, dict) else None
    try:
        operation, payload = _request(value)
        return operations.execute(operation, payload)
    except BridgeProtocolError as error:
        return _error_response(operation, error, correlation_id)
    except EventConflictError:
        return _error_response(
            operation,
            BridgeProtocolError(
                "reservation_conflict",
                "Reservation conflicts with existing safety state.",
            ),
            correlation_id,
        )
    except InvalidTransitionError as error:
        detail = str(error).casefold()
        if "unknown" in detail:
            code = "unknown_release"
        elif "terminal" in detail:
            code = "terminal_rejection"
        else:
            code = "invalid_transition"
        return _error_response(
            operation,
            BridgeProtocolError(code, "Safety lifecycle transition was rejected."),
            correlation_id,
        )
    except InvalidLedgerError:
        return _error_response(
            operation,
            BridgeProtocolError("invalid_request", "Request payload is invalid."),
            correlation_id,
        )
    except (AnchorBackendError, AnchorConflictError, ImageSafetyLedgerError):
        return _error_response(
            operation,
            BridgeProtocolError(
                "safety_unavailable",
                "Safety ledger is unavailable.",
                retryable=True,
            ),
            correlation_id,
        )
    except Exception:
        # Never attach exception details here: they can contain repository paths,
        # command output, or other operator-only data.
        LOGGER.error(
            "bridge operation failed correlation_id=%s code=internal_error",
            correlation_id,
        )
        return _error_response(
            operation,
            BridgeProtocolError(
                "internal_error", "Safety bridge failed closed.", retryable=True
            ),
            correlation_id,
        )


def _receive_exact(connection: socket.socket, size: int) -> bytes:
    chunks = []
    remaining = size
    while remaining:
        chunk = connection.recv(remaining)
        if not chunk:
            raise BridgeProtocolError("invalid_request", "Request frame is truncated.")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def receive_frame(connection: socket.socket) -> object:
    connection.settimeout(FRAME_TIMEOUT_SECONDS)
    header = _receive_exact(connection, 4)
    length = struct.unpack("!I", header)[0]
    if length == 0 or length > MAX_FRAME_BYTES:
        raise BridgeProtocolError("invalid_request", "Request frame length is invalid.")
    body = _receive_exact(connection, length)
    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise BridgeProtocolError("invalid_request", "Request is not valid UTF-8 JSON.") from error


def encode_frame(value: Mapping[str, Any]) -> bytes:
    body = json.dumps(
        value, ensure_ascii=True, allow_nan=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    if not body or len(body) > MAX_FRAME_BYTES:
        raise BridgeProtocolError("internal_error", "Response frame is invalid.")
    return struct.pack("!I", len(body)) + body


def peer_credentials(connection: socket.socket) -> tuple[int, int, int]:
    if not hasattr(socket, "SO_PEERCRED"):
        raise UnauthorizedPeerError("SO_PEERCRED is unavailable.")
    raw = connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
    return struct.unpack("3i", raw)


def require_peer(connection: socket.socket, *, expected_uid: int, expected_gid: int) -> None:
    _, uid, gid = peer_credentials(connection)
    if uid != expected_uid or gid != expected_gid:
        raise UnauthorizedPeerError("Socket peer identity was rejected.")


class SafetyBridgeServer:
    def __init__(
        self,
        *,
        listener: socket.socket,
        operations: SafetyBridgeOperations,
        expected_uid: int = 0,
        expected_gid: int = 0,
        peer_validator: Callable[[socket.socket], None] | None = None,
    ):
        self.listener = listener
        self.operations = operations
        self.expected_uid = expected_uid
        self.expected_gid = expected_gid
        self.peer_validator = peer_validator
        self.mutation_executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="safety-bridge-mutation"
        )
        self.authorization_executor = ThreadPoolExecutor(
            max_workers=8, thread_name_prefix="safety-bridge-authorize"
        )
        self.connection_executor = ThreadPoolExecutor(
            max_workers=16, thread_name_prefix="safety-bridge-connection"
        )
        self.pending: Future | None = None
        self.pending_lock = threading.Lock()

    def _validate_peer(self, connection: socket.socket) -> None:
        if self.peer_validator is not None:
            self.peer_validator(connection)
            return
        require_peer(
            connection, expected_uid=self.expected_uid, expected_gid=self.expected_gid
        )

    def serve_connection(self, connection: socket.socket) -> None:
        operation = None
        try:
            self._validate_peer(connection)
            request = receive_frame(connection)
            operation = request.get("operation") if isinstance(request, dict) else None
            if operation == "authorize":
                future = self.authorization_executor.submit(
                    handle_request, request, self.operations
                )
                try:
                    response = future.result(timeout=OPERATION_TIMEOUT_SECONDS)
                except FutureTimeout:
                    response = _error_response(
                        operation,
                        BridgeProtocolError(
                            "timeout",
                            "Safety authorization timed out.",
                            retryable=True,
                        ),
                        str(uuid.uuid4()),
                    )
            else:
                with self.pending_lock:
                    if self.pending is not None and not self.pending.done():
                        future = None
                    else:
                        self.pending = self.mutation_executor.submit(
                            handle_request, request, self.operations
                        )
                        future = self.pending
                if future is None:
                    response = _error_response(
                        operation,
                        BridgeProtocolError(
                            "safety_unavailable",
                            "A previous safety mutation is still completing.",
                            retryable=True,
                        ),
                        str(uuid.uuid4()),
                    )
                else:
                    try:
                        response = future.result(timeout=OPERATION_TIMEOUT_SECONDS)
                    except FutureTimeout:
                        response = _error_response(
                            operation,
                            BridgeProtocolError(
                                "timeout",
                                "Safety operation outcome is unknown; retry the same request.",
                                retryable=True,
                            ),
                            str(uuid.uuid4()),
                        )
            connection.sendall(encode_frame(response))
        except UnauthorizedPeerError:
            LOGGER.warning("unauthorized_peer")
        except BridgeProtocolError as error:
            response = _error_response(operation, error, str(uuid.uuid4()))
            try:
                connection.sendall(encode_frame(response))
            except OSError:
                pass
        except (OSError, socket.timeout):
            LOGGER.warning("bridge_connection_failed operation=%s", operation)
        finally:
            connection.close()

    def serve_forever(self) -> None:
        while True:
            connection, _ = self.listener.accept()
            self.connection_executor.submit(self.serve_connection, connection)


def systemd_listener() -> socket.socket:
    try:
        listen_pid = int(os.environ.get("LISTEN_PID", "0"))
        listen_fds = int(os.environ.get("LISTEN_FDS", "0"))
    except ValueError as error:
        raise RuntimeError("Invalid systemd socket activation environment.") from error
    if listen_pid != os.getpid() or listen_fds != 1:
        raise RuntimeError("Exactly one systemd-activated socket is required.")
    listener = socket.fromfd(3, socket.AF_UNIX, socket.SOCK_STREAM)
    listener.setblocking(True)
    return listener
