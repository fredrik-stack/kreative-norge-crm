"""CI-only PUBLIC image asset fixture and minimal read-only safety bridge."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import socket
import struct
import sys
import uuid


RELEASE_ID = uuid.UUID("11111111-1111-4111-8111-111111111111")
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def seed() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django

    django.setup()

    from django.contrib.auth import get_user_model
    from django.utils import timezone

    from crm.models import (
        ImageAsset,
        ImageRendition,
        ImageRenditionSet,
        Organization,
        OrganizationImageRelease,
        OrganizationImageReleaseRendition,
        OrganizationImageSelection,
        Tenant,
    )
    from image_safety.release_keys import build_public_release_key

    tenant, _ = Tenant.objects.get_or_create(
        slug="public-e2e", defaults={"name": "Public E2E"}
    )
    Organization.objects.get_or_create(
        tenant=tenant,
        org_number="999999999",
        defaults={
            "name": "Playwright fallback actor",
            "description": "Browser-verifisert offentlig fallbackaktør.",
            "is_published": True,
            "thumbnail_image_url": "https://legacy.invalid/forbidden.jpg",
        },
    )
    if Organization.objects.filter(
        tenant=tenant, org_number="888888888"
    ).exists():
        return

    user, _ = get_user_model().objects.get_or_create(
        username="public-image-e2e-fixture"
    )
    organization = Organization.objects.create(
        tenant=tenant,
        org_number="888888888",
        name=(
            "Playwright asset actor med et særdeles langt navn som må brytes "
            "uten horisontal overflow"
        ),
        description="Browser-verifisert offentlig assetaktør.",
        is_published=True,
        thumbnail_image_url="https://legacy.invalid/forbidden-asset.jpg",
    )
    asset = ImageAsset.objects.create(
        tenant=tenant,
        private_storage_key="e2e/private/source.jpg",
        checksum_sha256="a" * 64,
        original_format="jpeg",
        mime_type="image/jpeg",
        width=1600,
        height=900,
        file_size_bytes=100,
        validation_version="e2e-v1",
    )
    rendition_set = ImageRenditionSet.objects.create(
        tenant=tenant,
        asset=asset,
        fit_mode="cover",
        processing_version="e2e-v1",
        render_config_hash_sha256="b" * 64,
    )
    dimensions = {
        "square": (512, 512),
        "landscape": (800, 450),
        "share": (1200, 630),
    }
    renditions = []
    for index, (variant, (width, height)) in enumerate(dimensions.items(), start=1):
        checksum = f"{index:x}" * 64
        renditions.append(
            ImageRendition.objects.create(
                tenant=tenant,
                rendition_set=rendition_set,
                variant=variant,
                output_format="webp",
                width=width,
                height=height,
                file_size_bytes=100 + index,
                checksum_sha256=checksum,
                artifact_storage_key=f"e2e/artifacts/{variant}-{checksum}.webp",
            )
        )
    selection = OrganizationImageSelection.objects.create(
        tenant=tenant,
        organization=organization,
        selection_kind="asset",
        rendition_set=rendition_set,
        alt_text="Scene med godkjent alttekst",
        public_credit="Foto: Playwright",
        revision=1,
        status="active",
        locked_by=user,
        locked_at=timezone.now(),
    )
    release = OrganizationImageRelease.objects._insert_from_release_service(
        [
            OrganizationImageRelease(
                release_id=RELEASE_ID,
                tenant=tenant,
                organization=organization,
                selection=selection,
                selection_revision_snapshot=1,
                rendition_set=rendition_set,
                key_schema_version=1,
            )
        ]
    )[0]
    OrganizationImageReleaseRendition.objects._insert_from_release_service(
        [
            OrganizationImageReleaseRendition(
                release=release,
                rendition=rendition,
                variant=rendition.variant,
                output_format=rendition.output_format,
                artifact_storage_key_snapshot=rendition.artifact_storage_key,
                artifact_checksum_sha256_snapshot=rendition.checksum_sha256,
                public_storage_key=build_public_release_key(
                    RELEASE_ID,
                    rendition.variant,
                    rendition.output_format,
                ),
            )
            for rendition in renditions
        ]
    )


def _receive_exact(connection: socket.socket, size: int) -> bytes:
    payload = bytearray()
    while len(payload) < size:
        chunk = connection.recv(size - len(payload))
        if not chunk:
            raise ConnectionError("truncated frame")
        payload.extend(chunk)
    return bytes(payload)


def serve(socket_path: Path) -> None:
    socket_path.unlink(missing_ok=True)
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
        server.bind(str(socket_path))
        server.listen(8)
        while True:
            connection, _ = server.accept()
            with connection:
                try:
                    size = struct.unpack("!I", _receive_exact(connection, 4))[0]
                    request = json.loads(_receive_exact(connection, size))
                    operation = request.get("operation")
                    payload = request["payload"]
                    if operation == "authorize":
                        response = {
                            "protocol_version": 1,
                            "operation": operation,
                            "result": "success",
                            "authorization": {
                                "authorized": True,
                                "category": "authorized",
                                "release_id": payload["release_id"],
                                "variant": payload["variant"],
                                "read_cursor": 1,
                            },
                        }
                    elif operation == "check_checksum":
                        response = {
                            "protocol_version": 1,
                            "operation": operation,
                            "result": "success",
                            "checksum": {"denied": False, "read_cursor": 1},
                        }
                    elif operation == "legacy_guard":
                        response = {
                            "protocol_version": 1,
                            "operation": operation,
                            "result": "success",
                            "legacy_guard": {"blocked": False, "read_cursor": 1},
                        }
                    else:
                        raise ValueError("unsupported fixture operation")
                    body = json.dumps(response, separators=(",", ":")).encode()
                    connection.sendall(struct.pack("!I", len(body)) + body)
                except (ConnectionError, KeyError, ValueError, json.JSONDecodeError):
                    continue


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("seed")
    serve_parser = subparsers.add_parser("serve")
    serve_parser.add_argument("--socket", type=Path, required=True)
    arguments = parser.parse_args()

    if arguments.command == "seed":
        seed()
    else:
        serve(arguments.socket)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
