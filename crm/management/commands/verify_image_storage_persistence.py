from __future__ import annotations

from hashlib import sha256
import re

from django.conf import settings
from django.core.files.storage import storages
from django.core.management.base import BaseCommand, CommandError

from crm.services.images.storage import ImmutableImageStorageError, _save_immutable


PROBE_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDAT\x08\xd7c\xf8"
    b"\xcf\xc0\xf0\x1f\x00\x05\x00\x01\xff\x89\x99=\x1d\x00\x00\x00\x00IEND\xaeB`\x82"
)
TOKEN_PATTERN = re.compile(r"^[a-f0-9]{32}$")


def _keys(token: str) -> tuple[tuple[str, str], ...]:
    return (
        ("image_originals_private", f"runtime-probes/{token}/original.png"),
        ("image_renditions_public", f"runtime-probes/{token}/rendition.png"),
    )


def _verify(alias: str, key: str) -> None:
    storage = storages[alias]
    if not storage.exists(key):
        raise CommandError(f"Persistence probe is missing from {alias}.")
    try:
        with storage.open(key, "rb") as stored:
            actual = stored.read()
    except (OSError, ValueError) as error:
        raise CommandError(f"Persistence probe cannot be read from {alias}.") from error
    if actual != PROBE_BYTES:
        raise CommandError(f"Persistence probe checksum mismatch in {alias}.")


class Command(BaseCommand):
    help = "Write, verify, or remove an exact image-storage persistence probe."

    def add_arguments(self, parser):
        mode = parser.add_mutually_exclusive_group(required=True)
        mode.add_argument("--write", action="store_true")
        mode.add_argument("--verify", action="store_true")
        mode.add_argument("--cleanup", action="store_true")
        parser.add_argument("--token", required=True)

    def handle(self, *args, **options):
        token = options["token"]
        if not TOKEN_PATTERN.fullmatch(token):
            raise CommandError("token must contain exactly 32 lowercase hexadecimal characters")

        keys = _keys(token)
        if options["write"]:
            if not settings.IMAGE_ASSET_FEATURE_ENABLED:
                raise CommandError("IMAGE_ASSET_FEATURE_ENABLED must be true for probe writes")
            try:
                for alias, key in keys:
                    _save_immutable(
                        alias=alias,
                        requested_key=key,
                        data=PROBE_BYTES,
                        content_type="image/png",
                    )
            except ImmutableImageStorageError as error:
                raise CommandError(str(error)) from error

        for alias, key in keys:
            _verify(alias, key)

        if options["cleanup"]:
            for alias, key in keys:
                storages[alias].delete(key)
                if storages[alias].exists(key):
                    raise CommandError(f"Persistence probe cleanup failed in {alias}.")

        self.stdout.write(f"mode={'write' if options['write'] else 'verify' if options['verify'] else 'cleanup'}")
        self.stdout.write(f"token={token}")
        self.stdout.write(f"checksum_sha256={sha256(PROBE_BYTES).hexdigest()}")
        for alias, key in keys:
            self.stdout.write(f"{alias}_key={key}")
