import json
from pathlib import Path
import socket
import struct
import tempfile
import threading
import uuid

from django.test import SimpleTestCase

from image_safety.ledger import (
    release_denial_event_id,
    reservation_event_id,
    tenant_checksum_denial_event_id,
)
from image_safety.release_keys import build_public_release_key

from .services.images.bridge_client import (
    BridgeRenditionSnapshot,
    ImageSafetyBridgeClient,
    ImageSafetyBridgeUnavailable,
)


class ImageSafetyBridgeClientTests(SimpleTestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.socket_path = Path(self.temporary.name) / "bridge.sock"
        self.release_id = str(uuid.uuid4())
        self.renditions = tuple(
            BridgeRenditionSnapshot(
                variant=variant,
                output_format="webp",
                artifact_storage_key=f"tenants/1/{variant}.webp",
                artifact_checksum_sha256="a" * 64,
            )
            for variant in ("square", "landscape", "share")
        )

    def run_server(self, responder):
        ready = threading.Event()
        self.socket_path.unlink(missing_ok=True)

        def serve():
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
                listener.bind(str(self.socket_path))
                listener.listen(1)
                ready.set()
                connection, _ = listener.accept()
                with connection:
                    header = connection.recv(4)
                    length = struct.unpack("!I", header)[0]
                    body = b""
                    while len(body) < length:
                        body += connection.recv(length - len(body))
                    responder(connection, json.loads(body))

        thread = threading.Thread(target=serve)
        thread.start()
        ready.wait(timeout=2)
        self.addCleanup(lambda: thread.join(timeout=2))
        return thread

    @staticmethod
    def send_response(connection, response):
        body = json.dumps(response, separators=(",", ":")).encode()
        connection.sendall(struct.pack("!I", len(body)) + body)

    def test_reserve_validates_and_returns_confirmed_identity(self):
        event_id = reservation_event_id(
            tenant_id=1,
            organization_id=2,
            selection_id=3,
            selection_revision=4,
        )

        def respond(connection, request):
            self.assertEqual(request["operation"], "reserve")
            self.assertNotIn("release_id", request["payload"])
            self.assertNotIn("event_id", request["payload"])
            response = {
                "protocol_version": 1,
                "operation": "reserve",
                "result": "success",
                "disposition": "new",
                "reservation": {
                    "event_id": event_id,
                    "event_sequence": 8,
                    "release_id": self.release_id,
                    "public_keys": {
                        item.variant: build_public_release_key(
                            self.release_id, item.variant, item.output_format
                        )
                        for item in self.renditions
                    },
                },
                "confirmation": {
                    "anchored": True,
                    "anchor_cursor": 8,
                    "archive_reused": False,
                },
            }
            self.send_response(connection, response)

        thread = self.run_server(respond)
        result = ImageSafetyBridgeClient(
            socket_path=self.socket_path, timeout=1
        ).reserve(
            tenant_id=1,
            organization_id=2,
            selection_id=3,
            selection_revision=4,
            rendition_set_id=5,
            renditions=self.renditions,
        )
        thread.join(timeout=2)

        self.assertEqual(result.release_id, self.release_id)
        self.assertEqual(result.anchor_cursor, 8)

    def test_missing_socket_and_truncated_response_are_retryable(self):
        client = ImageSafetyBridgeClient(socket_path=self.socket_path, timeout=0.2)
        with self.assertRaises(ImageSafetyBridgeUnavailable) as missing:
            client.activate(release_id=self.release_id)
        self.assertTrue(missing.exception.retryable)

        self.run_server(lambda connection, _: connection.sendall(struct.pack("!I", 50) + b"{}"))
        with self.assertRaises(ImageSafetyBridgeUnavailable) as truncated:
            client.activate(release_id=self.release_id)
        self.assertTrue(truncated.exception.retryable)

    def test_malformed_or_unconfirmed_response_fails_closed(self):
        response = {
            "protocol_version": 1,
            "operation": "activate",
            "result": "success",
            "disposition": "new",
            "event": {
                "event_id": f"release-activation:v1:{self.release_id}",
                "event_sequence": 2,
                "release_id": self.release_id,
            },
            "confirmation": {
                "anchored": True,
                "anchor_cursor": 1,
                "archive_reused": False,
            },
        }
        self.run_server(lambda connection, _: self.send_response(connection, response))

        with self.assertRaises(ImageSafetyBridgeUnavailable):
            ImageSafetyBridgeClient(socket_path=self.socket_path, timeout=1).activate(
                release_id=self.release_id
            )

    def test_authorize_sends_exact_identity_and_accepts_strict_response(self):
        expected_key = build_public_release_key(self.release_id, "square", "webp")

        def respond(connection, request):
            self.assertEqual(request["operation"], "authorize")
            self.assertEqual(
                request["payload"],
                {
                    "release_id": self.release_id,
                    "tenant_id": 1,
                    "organization_id": 2,
                    "variant": "square",
                    "public_storage_key": expected_key,
                    "artifact_checksum_sha256": "a" * 64,
                    "source_checksum_sha256": "b" * 64,
                },
            )
            self.send_response(
                connection,
                {
                    "protocol_version": 1,
                    "operation": "authorize",
                    "result": "success",
                    "authorization": {
                        "authorized": True,
                        "category": "authorized",
                        "release_id": self.release_id,
                        "variant": "square",
                        "read_cursor": 9,
                    },
                },
            )

        thread = self.run_server(respond)
        authorization = ImageSafetyBridgeClient(
            socket_path=self.socket_path, timeout=1
        ).authorize(
            release_id=self.release_id,
            tenant_id=1,
            organization_id=2,
            variant="square",
            public_storage_key=expected_key,
            artifact_checksum_sha256="a" * 64,
            source_checksum_sha256="b" * 64,
        )
        thread.join(timeout=2)

        self.assertTrue(authorization.authorized)
        self.assertEqual(authorization.category, "authorized")
        self.assertEqual(authorization.read_cursor, 9)

    def test_authorize_rejects_mismatched_or_inconsistent_response(self):
        expected_key = build_public_release_key(self.release_id, "square", "webp")
        responses = (
            {
                "authorized": True,
                "category": "unknown",
                "release_id": self.release_id,
                "variant": "square",
                "read_cursor": 9,
            },
            {
                "authorized": False,
                "category": "authorized",
                "release_id": self.release_id,
                "variant": "square",
                "read_cursor": 9,
            },
            {
                "authorized": True,
                "category": "authorized",
                "release_id": str(uuid.uuid4()),
                "variant": "square",
                "read_cursor": 9,
            },
            {
                "authorized": True,
                "category": "authorized",
                "release_id": self.release_id,
                "variant": "share",
                "read_cursor": 9,
            },
            {
                "authorized": True,
                "category": "authorized",
                "release_id": self.release_id,
                "variant": "square",
                "read_cursor": True,
            },
        )
        for index, authorization in enumerate(responses):
            with self.subTest(index=index):
                self.run_server(
                    lambda connection, _: self.send_response(
                        connection,
                        {
                            "protocol_version": 1,
                            "operation": "authorize",
                            "result": "success",
                            "authorization": authorization,
                        },
                    )
                )
                with self.assertRaises(ImageSafetyBridgeUnavailable):
                    ImageSafetyBridgeClient(
                        socket_path=self.socket_path, timeout=1
                    ).authorize(
                        release_id=self.release_id,
                        tenant_id=1,
                        organization_id=2,
                        variant="square",
                        public_storage_key=expected_key,
                        artifact_checksum_sha256="a" * 64,
                        source_checksum_sha256="b" * 64,
                    )

    def test_deny_checksum_and_legacy_operations_use_strict_minimal_schemas(self):
        checksum = "d" * 64
        checksum_event_id = tenant_checksum_denial_event_id(
            tenant_id=1,
            source_checksum_sha256=checksum,
        )

        def deny_response(connection, request):
            self.assertEqual(request["operation"], "deny")
            self.assertEqual(
                set(request["payload"]),
                {
                    "release_id", "tenant_id", "organization_id",
                    "source_checksum_sha256", "reason_code",
                },
            )
            self.send_response(
                connection,
                {
                    "protocol_version": 1,
                    "operation": "deny",
                    "result": "success",
                    "release_disposition": "new",
                    "checksum_disposition": "new",
                    "events": {
                        "release_denied": {
                            "event_id": release_denial_event_id(self.release_id),
                            "event_sequence": 10,
                            "release_id": self.release_id,
                        },
                        "tenant_checksum_denied": {
                            "event_id": checksum_event_id,
                            "event_sequence": 11,
                        },
                    },
                    "confirmation": {
                        "anchored": True,
                        "anchor_cursor": 11,
                        "archive_reused": False,
                    },
                },
            )

        self.run_server(deny_response)
        denied = ImageSafetyBridgeClient(
            socket_path=self.socket_path, timeout=1
        ).deny(
            release_id=self.release_id,
            tenant_id=1,
            organization_id=2,
            source_checksum_sha256=checksum,
            reason_code="rights_request",
        )
        self.assertEqual(denied.anchor_cursor, 11)
        self.assertEqual(denied.checksum_event_id, checksum_event_id)

        def checksum_response(connection, request):
            self.assertEqual(
                request,
                {
                    "protocol_version": 1,
                    "operation": "check_checksum",
                    "payload": {
                        "tenant_id": 1,
                        "source_checksum_sha256": checksum,
                    },
                },
            )
            self.send_response(
                connection,
                {
                    "protocol_version": 1,
                    "operation": "check_checksum",
                    "result": "success",
                    "checksum": {"denied": True, "read_cursor": 11},
                },
            )

        self.run_server(checksum_response)
        checked = ImageSafetyBridgeClient(
            socket_path=self.socket_path, timeout=1
        ).check_checksum(tenant_id=1, source_checksum_sha256=checksum)
        self.assertTrue(checked.denied)

        def legacy_response(connection, request):
            self.assertEqual(
                request,
                {
                    "protocol_version": 1,
                    "operation": "legacy_guard",
                    "payload": {"tenant_id": 1, "organization_id": 2},
                },
            )
            self.send_response(
                connection,
                {
                    "protocol_version": 1,
                    "operation": "legacy_guard",
                    "result": "success",
                    "legacy_guard": {"blocked": True, "read_cursor": 11},
                },
            )

        self.run_server(legacy_response)
        legacy = ImageSafetyBridgeClient(
            socket_path=self.socket_path, timeout=1
        ).legacy_guard(tenant_id=1, organization_id=2)
        self.assertTrue(legacy.blocked)
