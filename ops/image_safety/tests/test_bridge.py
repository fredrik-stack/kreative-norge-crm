from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import socket
import struct
import tempfile
import threading
import time
import unittest
import uuid
from unittest.mock import Mock, patch

from image_safety.anchor import AnchorBackendError, anchor_current_head
from image_safety.bridge import (
    MAX_FRAME_BYTES,
    SafetyBridgeOperations,
    SafetyBridgeServer,
    UnauthorizedPeerError,
    encode_frame,
    handle_request,
    receive_frame,
)
from image_safety.ledger import (
    EventConflictError,
    PublicImageSafetyLedger,
    ReservationRendition,
)


REPOSITORY_ID = "9" * 64


class MemoryAnchor:
    def __init__(self):
        self.archives = {}
        self.fail_create = False
        self.lock = threading.Lock()

    def verified_repository_id(self):
        return REPOSITORY_ID

    def read(self, archive_name):
        with self.lock:
            return self.archives.get(archive_name)

    def create(self, archive_name, content):
        if self.fail_create:
            raise AnchorBackendError("synthetic anchor failure")
        with self.lock:
            if archive_name in self.archives:
                raise AnchorBackendError("archive exists")
            self.archives[archive_name] = content

    def list_archives(self, prefix):
        with self.lock:
            return sorted(key for key in self.archives if key.startswith(prefix))


def reservation_payload(checksum="a" * 64):
    return {
        "tenant_id": 1,
        "organization_id": 2,
        "selection_id": 3,
        "selection_revision": 4,
        "rendition_set_id": 5,
        "renditions": [
            {
                "variant": variant,
                "output_format": "webp",
                "artifact_storage_key": f"tenants/1/artifacts/{variant}.webp",
                "artifact_checksum_sha256": checksum,
            }
            for variant in ("square", "landscape", "share")
        ],
    }


def reserve_request(checksum="a" * 64):
    return {
        "protocol_version": 1,
        "operation": "reserve",
        "payload": reservation_payload(checksum),
    }


def authorize_request(
    release_id,
    *,
    tenant_id=1,
    organization_id=2,
    variant="square",
    public_storage_key=None,
    checksum="a" * 64,
    source_checksum="c" * 64,
):
    return {
        "protocol_version": 1,
        "operation": "authorize",
        "payload": {
            "release_id": release_id,
            "tenant_id": tenant_id,
            "organization_id": organization_id,
            "variant": variant,
            "public_storage_key": public_storage_key
            or f"releases/{release_id}/{variant}.webp",
            "artifact_checksum_sha256": checksum,
            "source_checksum_sha256": source_checksum,
        },
    }


class BridgeFixture(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.ledger = PublicImageSafetyLedger(
            Path(self.temporary_directory.name) / "ledger.sqlite3"
        )
        self.ledger.initialize()
        self.anchor = MemoryAnchor()
        anchor_current_head(
            self.ledger,
            self.anchor,
            expected_repository_id=REPOSITORY_ID,
        )
        self.operations = SafetyBridgeOperations(
            ledger=self.ledger,
            anchor_backend=self.anchor,
            expected_repository_id=REPOSITORY_ID,
        )

    def tearDown(self):
        self.temporary_directory.cleanup()


class AtomicReservationTests(BridgeFixture):
    def _renditions(self, checksum="a" * 64):
        return tuple(
            ReservationRendition(**item)
            for item in reservation_payload(checksum)["renditions"]
        )

    def _reserve(self, checksum="a" * 64):
        return self.ledger.reserve_or_get(
            tenant_id=1,
            organization_id=2,
            selection_id=3,
            selection_revision=4,
            rendition_set_id=5,
            renditions=self._renditions(checksum),
        )

    def test_concurrent_first_reservation_reuses_one_uuid_and_event(self):
        with ThreadPoolExecutor(max_workers=2) as executor:
            events = list(executor.map(lambda _: self._reserve(), range(2)))

        self.assertEqual({event.release_id for event in events}, {events[0].release_id})
        self.assertEqual(sorted(event.idempotent_retry for event in events), [False, True])
        self.assertEqual(self.ledger.head().sequence, 1)

    def test_concurrent_different_payload_has_one_winner_and_one_conflict(self):
        gate = threading.Barrier(2)

        def reserve(checksum):
            gate.wait(timeout=5)
            try:
                return self._reserve(checksum)
            except EventConflictError as error:
                return error

        with ThreadPoolExecutor(max_workers=2) as executor:
            outcomes = list(executor.map(reserve, ("a" * 64, "b" * 64)))

        self.assertEqual(sum(not isinstance(item, Exception) for item in outcomes), 1)
        self.assertEqual(sum(isinstance(item, EventConflictError) for item in outcomes), 1)
        self.assertEqual(self.ledger.head().sequence, 1)


class BridgeOperationTests(BridgeFixture):
    def _active_release(self):
        reserved = handle_request(reserve_request(), self.operations)
        release_id = reserved["reservation"]["release_id"]
        activated = handle_request(
            {
                "protocol_version": 1,
                "operation": "activate",
                "payload": {"release_id": release_id},
            },
            self.operations,
        )
        self.assertEqual(activated["result"], "success")
        return release_id

    def test_reserve_new_retry_and_activation_new_retry_are_confirmed(self):
        first = handle_request(reserve_request(), self.operations)
        second = handle_request(reserve_request(), self.operations)
        release_id = first["reservation"]["release_id"]
        activation = {
            "protocol_version": 1,
            "operation": "activate",
            "payload": {"release_id": release_id},
        }
        active = handle_request(activation, self.operations)
        active_retry = handle_request(activation, self.operations)

        self.assertEqual(first["disposition"], "new")
        self.assertEqual(second["disposition"], "idempotent_retry")
        self.assertEqual(first["reservation"], second["reservation"])
        self.assertTrue(first["confirmation"]["anchored"])
        self.assertGreaterEqual(
            first["confirmation"]["anchor_cursor"],
            first["reservation"]["event_sequence"],
        )
        self.assertEqual(active["disposition"], "new")
        self.assertEqual(active_retry["disposition"], "idempotent_retry")

    def test_anchor_failure_returns_no_unconfirmed_reservation_and_retry_repairs(self):
        self.anchor.fail_create = True
        failed = handle_request(reserve_request(), self.operations)

        self.assertEqual(failed["result"], "error")
        self.assertEqual(failed["code"], "safety_unavailable")
        self.assertNotIn("reservation", failed)
        self.assertFalse(
            self.ledger.health(expected_repository_id=REPOSITORY_ID).ready
        )

        self.anchor.fail_create = False
        retried = handle_request(reserve_request(), self.operations)
        self.assertEqual(retried["result"], "success")
        self.assertEqual(retried["disposition"], "idempotent_retry")

    def test_changed_payload_conflicts_without_new_uuid(self):
        first = handle_request(reserve_request("a" * 64), self.operations)
        conflict = handle_request(reserve_request("b" * 64), self.operations)

        self.assertEqual(first["result"], "success")
        self.assertEqual(conflict["code"], "reservation_conflict")
        self.assertEqual(self.ledger.head().sequence, 1)

    def test_unknown_and_terminal_activation_are_rejected(self):
        unknown = handle_request(
            {
                "protocol_version": 1,
                "operation": "activate",
                "payload": {"release_id": str(uuid.uuid4())},
            },
            self.operations,
        )
        reserved = handle_request(reserve_request(), self.operations)
        release_id = reserved["reservation"]["release_id"]
        self.ledger.deny_release(
            event_id="test-deny",
            release_id=release_id,
            reason_code="security_deny",
        )
        anchor_current_head(
            self.ledger, self.anchor, expected_repository_id=REPOSITORY_ID
        )
        terminal = handle_request(
            {
                "protocol_version": 1,
                "operation": "activate",
                "payload": {"release_id": release_id},
            },
            self.operations,
        )

        self.assertEqual(unknown["code"], "unknown_release")
        self.assertEqual(terminal["code"], "terminal_rejection")

    def test_strict_schema_and_disabled_operations_fail_closed(self):
        duplicate = reservation_payload()
        duplicate["renditions"][2]["variant"] = "square"
        invalid_checksum = reservation_payload()
        invalid_checksum["renditions"][0]["artifact_checksum_sha256"] = "not-a-checksum"
        traversal = reservation_payload()
        traversal["renditions"][0]["artifact_storage_key"] = "../secret"
        cases = (
            ({"protocol_version": 2, "operation": "reserve", "payload": {}}, "unsupported_version"),
            ({"protocol_version": True, "operation": "reserve", "payload": {}}, "unsupported_version"),
            ({"protocol_version": 1, "operation": "retire", "payload": {}}, "unknown_operation"),
            ({"protocol_version": 1, "operation": "deny", "payload": {}}, "invalid_request"),
            (
                {
                    "protocol_version": 1,
                    "operation": "deny",
                    "payload": {
                        "release_id": str(uuid.uuid4()),
                        "tenant_id": 1,
                        "organization_id": 2,
                        "source_checksum_sha256": "a" * 64,
                        "reason_code": "arbitrary_internal_reason",
                    },
                },
                "invalid_request",
            ),
            ({**reserve_request(), "extra": True}, "invalid_request"),
            ({**reserve_request(), "payload": {**reservation_payload(), "tenant_id": True}}, "invalid_request"),
            ({**reserve_request(), "payload": {key: value for key, value in reservation_payload().items() if key != "selection_id"}}, "invalid_request"),
            ({**reserve_request(), "payload": {**reservation_payload(), "extra": 1}}, "invalid_request"),
            ({**reserve_request(), "payload": duplicate}, "invalid_request"),
            ({**reserve_request(), "payload": invalid_checksum}, "invalid_request"),
            ({**reserve_request(), "payload": traversal}, "invalid_request"),
            (
                authorize_request(str(uuid.uuid4()))
                | {"payload": {"release_id": str(uuid.uuid4())}},
                "invalid_request",
            ),
            (
                authorize_request(str(uuid.uuid4()), variant="portrait"),
                "invalid_request",
            ),
            (
                authorize_request(str(uuid.uuid4()), checksum="not-a-checksum"),
                "invalid_request",
            ),
        )
        for request, code in cases:
            with self.subTest(code=code):
                response = handle_request(request, self.operations)
                self.assertEqual(response["result"], "error")
                self.assertEqual(response["code"], code)
                self.assertIn("correlation_id", response)

    def test_authorize_requires_active_exact_scope_and_is_read_only(self):
        reserved = handle_request(reserve_request(), self.operations)
        release_id = reserved["reservation"]["release_id"]
        before_head = self.ledger.head()
        before_archives = dict(self.anchor.archives)

        inactive = handle_request(authorize_request(release_id), self.operations)
        unknown = handle_request(authorize_request(str(uuid.uuid4())), self.operations)
        handle_request(
            {
                "protocol_version": 1,
                "operation": "activate",
                "payload": {"release_id": release_id},
            },
            self.operations,
        )
        active_head = self.ledger.head()
        active_archives = dict(self.anchor.archives)
        exact = handle_request(authorize_request(release_id), self.operations)
        mismatches = (
            authorize_request(release_id, tenant_id=99),
            authorize_request(release_id, organization_id=99),
            authorize_request(release_id, variant="landscape", public_storage_key="releases/%s/square.webp" % release_id),
            authorize_request(release_id, checksum="b" * 64),
        )

        self.assertFalse(inactive["authorization"]["authorized"])
        self.assertEqual(inactive["authorization"]["category"], "not_active")
        self.assertFalse(unknown["authorization"]["authorized"])
        self.assertEqual(unknown["authorization"]["category"], "unknown")
        self.assertEqual(self.ledger.head(), active_head)
        self.assertEqual(self.anchor.archives, active_archives)
        self.assertTrue(exact["authorization"]["authorized"])
        self.assertEqual(exact["authorization"]["category"], "authorized")
        for request in mismatches:
            response = handle_request(request, self.operations)
            self.assertFalse(response["authorization"]["authorized"])
            self.assertEqual(response["authorization"]["category"], "scope_mismatch")
        self.assertEqual(self.ledger.head(), active_head)
        self.assertEqual(self.anchor.archives, active_archives)
        self.assertLess(before_head.sequence, active_head.sequence)
        self.assertNotEqual(before_archives, active_archives)

    def test_authorize_never_repairs_anchor_or_calls_anchor_backend(self):
        release_id = self._active_release()
        stale_payload = reservation_payload()
        self.ledger.reserve_or_get(
            tenant_id=1,
            organization_id=2,
            selection_id=99,
            selection_revision=1,
            rendition_set_id=5,
            renditions=tuple(
                ReservationRendition(**item) for item in stale_payload["renditions"]
            ),
        )
        self.assertEqual(
            self.ledger.health(expected_repository_id=REPOSITORY_ID).code,
            "anchor_cursor_stale",
        )

        with patch("image_safety.bridge.anchor_current_head") as anchor:
            response = handle_request(authorize_request(release_id), self.operations)

        self.assertEqual(response["result"], "error")
        self.assertEqual(response["code"], "safety_unavailable")
        anchor.assert_not_called()

    def test_parallel_authorizations_overlap(self):
        release_id = self._active_release()
        original = self.ledger.release_state
        overlap = threading.Barrier(2)

        def synchronized_release_state(value):
            overlap.wait(timeout=5)
            return original(value)

        with patch.object(
            self.ledger, "release_state", side_effect=synchronized_release_state
        ):
            with ThreadPoolExecutor(max_workers=2) as executor:
                responses = list(
                    executor.map(
                        lambda _: handle_request(
                            authorize_request(release_id), self.operations
                        ),
                        range(2),
                    )
                )

        self.assertTrue(all(item["authorization"]["authorized"] for item in responses))

    def test_waiting_terminal_writer_precedes_new_authorization(self):
        release_id = self._active_release()
        writer_waiting = threading.Event()
        order = []

        def terminal_write():
            writer_waiting.set()
            with self.operations._lifecycle_gate.write():
                self.ledger.deny_release(
                    event_id="test-writer-preference-deny",
                    release_id=release_id,
                    reason_code="security_deny",
                )
                anchor_current_head(
                    self.ledger,
                    self.anchor,
                    expected_repository_id=REPOSITORY_ID,
                )
                order.append("writer")

        def authorize():
            response = handle_request(authorize_request(release_id), self.operations)
            order.append("reader")
            return response

        with ThreadPoolExecutor(max_workers=2) as executor:
            with self.operations._lifecycle_gate.read():
                writer = executor.submit(terminal_write)
                writer_waiting.wait(timeout=2)
                time.sleep(0.02)
                reader = executor.submit(authorize)
                time.sleep(0.02)
            writer.result(timeout=5)
            response = reader.result(timeout=5)

        self.assertEqual(order, ["writer", "reader"])
        self.assertFalse(response["authorization"]["authorized"])
        self.assertEqual(response["authorization"]["category"], "not_active")


class BridgeV2TakedownTests(BridgeOperationTests):
    def setUp(self):
        super().setUp()
        self.ledger.upgrade_schema_v2()

    def _deny_request(self, release_id, *, tenant_id=1, checksum="d" * 64):
        return {
            "protocol_version": 1,
            "operation": "deny",
            "payload": {
                "release_id": release_id,
                "tenant_id": tenant_id,
                "organization_id": 2,
                "source_checksum_sha256": checksum,
                "reason_code": "rights_request",
            },
        }

    def test_deny_checksum_legacy_and_authorize_share_one_anchored_state(self):
        release_id = self._active_release()

        denied = handle_request(self._deny_request(release_id), self.operations)
        retried = handle_request(self._deny_request(release_id), self.operations)
        checksum = handle_request(
            {
                "protocol_version": 1,
                "operation": "check_checksum",
                "payload": {
                    "tenant_id": 1,
                    "source_checksum_sha256": "d" * 64,
                },
            },
            self.operations,
        )
        other_tenant = handle_request(
            {
                "protocol_version": 1,
                "operation": "check_checksum",
                "payload": {
                    "tenant_id": 9,
                    "source_checksum_sha256": "d" * 64,
                },
            },
            self.operations,
        )
        legacy = handle_request(
            {
                "protocol_version": 1,
                "operation": "legacy_guard",
                "payload": {"tenant_id": 1, "organization_id": 2},
            },
            self.operations,
        )
        authorization = handle_request(
            authorize_request(release_id, source_checksum="d" * 64),
            self.operations,
        )

        self.assertEqual(denied["result"], "success")
        self.assertEqual(denied["release_disposition"], "new")
        self.assertEqual(denied["checksum_disposition"], "new")
        self.assertGreaterEqual(
            denied["confirmation"]["anchor_cursor"],
            denied["events"]["tenant_checksum_denied"]["event_sequence"],
        )
        self.assertEqual(retried["release_disposition"], "idempotent_retry")
        self.assertEqual(retried["checksum_disposition"], "idempotent_retry")
        self.assertTrue(checksum["checksum"]["denied"])
        self.assertFalse(other_tenant["checksum"]["denied"])
        self.assertTrue(legacy["legacy_guard"]["blocked"])
        self.assertFalse(authorization["authorization"]["authorized"])
        self.assertEqual(
            authorization["authorization"]["category"], "checksum_denied"
        )
        self.assertTrue(self.ledger.health(expected_repository_id=REPOSITORY_ID).ready)

    def test_same_source_bytes_can_activate_in_a_different_tenant(self):
        tenant_a_release = self._active_release()
        handle_request(self._deny_request(tenant_a_release), self.operations)

        tenant_b_payload = reservation_payload()
        tenant_b_payload.update(
            {
                "tenant_id": 9,
                "organization_id": 20,
                "selection_id": 30,
                "selection_revision": 1,
                "rendition_set_id": 40,
            }
        )
        for rendition in tenant_b_payload["renditions"]:
            rendition["artifact_storage_key"] = rendition[
                "artifact_storage_key"
            ].replace("tenants/1/", "tenants/9/")
        reserved = handle_request(
            {"protocol_version": 1, "operation": "reserve", "payload": tenant_b_payload},
            self.operations,
        )
        tenant_b_release = reserved["reservation"]["release_id"]
        activated = handle_request(
            {
                "protocol_version": 1,
                "operation": "activate",
                "payload": {"release_id": tenant_b_release},
            },
            self.operations,
        )
        authorized = handle_request(
            authorize_request(
                tenant_b_release,
                tenant_id=9,
                organization_id=20,
                source_checksum="d" * 64,
            ),
            self.operations,
        )

        self.assertEqual(activated["result"], "success")
        self.assertTrue(authorized["authorization"]["authorized"])
        self.assertEqual(authorized["authorization"]["category"], "authorized")

    def test_deny_anchor_failure_is_fail_closed_and_retry_confirms_same_events(self):
        release_id = self._active_release()
        self.anchor.fail_create = True

        failed = handle_request(self._deny_request(release_id), self.operations)

        self.assertEqual(failed["result"], "error")
        self.assertEqual(failed["code"], "safety_unavailable")
        self.assertEqual(self.ledger.release_state(release_id)["state"], "denied")
        self.assertEqual(
            self.ledger.health(expected_repository_id=REPOSITORY_ID).code,
            "anchor_cursor_stale",
        )

        self.anchor.fail_create = False
        retried = handle_request(self._deny_request(release_id), self.operations)
        self.assertEqual(retried["result"], "success")
        self.assertEqual(retried["release_disposition"], "idempotent_retry")
        self.assertEqual(retried["checksum_disposition"], "idempotent_retry")
        self.assertTrue(self.ledger.health(expected_repository_id=REPOSITORY_ID).ready)

    def test_safe_republish_requires_new_source_checksum_and_new_release_identity(self):
        old_release_id = self._active_release()
        handle_request(self._deny_request(old_release_id), self.operations)
        payload = reservation_payload()
        payload["selection_id"] = 30
        payload["selection_revision"] = 6
        reservation = handle_request(
            {"protocol_version": 1, "operation": "reserve", "payload": payload},
            self.operations,
        )
        new_release_id = reservation["reservation"]["release_id"]
        handle_request(
            {
                "protocol_version": 1,
                "operation": "activate",
                "payload": {"release_id": new_release_id},
            },
            self.operations,
        )

        allowed = handle_request(
            authorize_request(new_release_id, source_checksum="e" * 64),
            self.operations,
        )
        denied_old_bytes = handle_request(
            authorize_request(new_release_id, source_checksum="d" * 64),
            self.operations,
        )

        self.assertNotEqual(new_release_id, old_release_id)
        self.assertTrue(allowed["authorization"]["authorized"])
        self.assertFalse(denied_old_bytes["authorization"]["authorized"])
        self.assertEqual(
            denied_old_bytes["authorization"]["category"], "checksum_denied"
        )


class BridgeFramingTests(BridgeFixture):
    def test_receive_frame_rejects_zero_oversize_truncated_utf8_and_json(self):
        frames = (
            struct.pack("!I", 0),
            struct.pack("!I", MAX_FRAME_BYTES + 1),
            struct.pack("!I", 5) + b"{}",
            struct.pack("!I", 1) + b"\xff",
            struct.pack("!I", 1) + b"{",
        )
        for frame in frames:
            with self.subTest(frame=frame[:8]):
                client, server = socket.socketpair()
                try:
                    client.sendall(frame)
                    client.shutdown(socket.SHUT_WR)
                    with self.assertRaises(Exception):
                        receive_frame(server)
                finally:
                    client.close()
                    server.close()

    def test_real_socket_request_response_and_safe_server_error(self):
        for operations, expected in (
            (self.operations, "success"),
            (Mock(execute=Mock(side_effect=RuntimeError("secret /root"))), "error"),
        ):
            with self.subTest(expected=expected):
                client, server_socket = socket.socketpair()
                listener = Mock()
                bridge = SafetyBridgeServer(
                    listener=listener,
                    operations=operations,
                    peer_validator=lambda _: None,
                )
                thread = threading.Thread(
                    target=bridge.serve_connection, args=(server_socket,)
                )
                thread.start()
                client.sendall(encode_frame(reserve_request()))
                response = receive_frame(client)
                thread.join(timeout=5)
                client.close()
                self.assertEqual(response["result"], expected)
                serialized = json.dumps(response)
                self.assertNotIn("/root", serialized)
                self.assertNotIn("traceback", serialized.casefold())

    def test_timeout_returns_retryable_unknown_outcome(self):
        class SlowOperations:
            def execute(self, operation, payload):
                time.sleep(0.1)
                return {"protocol_version": 1, "operation": operation, "result": "success"}

        client, server_socket = socket.socketpair()
        bridge = SafetyBridgeServer(
            listener=Mock(),
            operations=SlowOperations(),
            peer_validator=lambda _: None,
        )
        with patch("image_safety.bridge.OPERATION_TIMEOUT_SECONDS", 0.01):
            thread = threading.Thread(
                target=bridge.serve_connection, args=(server_socket,)
            )
            thread.start()
            client.sendall(encode_frame(reserve_request()))
            response = receive_frame(client)
            thread.join(timeout=5)
        client.close()

        self.assertEqual(response["code"], "timeout")
        self.assertTrue(response["retryable"])

    def test_unauthorized_peer_receives_no_domain_response(self):
        client, server_socket = socket.socketpair()
        bridge = SafetyBridgeServer(
            listener=Mock(),
            operations=self.operations,
            peer_validator=lambda _: (_ for _ in ()).throw(UnauthorizedPeerError()),
        )
        thread = threading.Thread(target=bridge.serve_connection, args=(server_socket,))
        thread.start()
        try:
            try:
                client.sendall(encode_frame(reserve_request()))
            except BrokenPipeError:
                # Linux may observe the peer rejection before sendall returns;
                # macOS commonly accepts the send and reports EOF below.
                pass
            try:
                response = client.recv(1)
            except ConnectionResetError:
                # Linux may reset a socket that is closed without reading the
                # queued request; EOF and reset both prove no domain response.
                response = b""
            self.assertEqual(response, b"")
            thread.join(timeout=5)
        finally:
            client.close()
