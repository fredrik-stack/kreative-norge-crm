from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

import boto3
from botocore import UNSIGNED
from botocore.client import Config
from botocore.exceptions import ClientError
from django.core.files.base import ContentFile
from django.core.files.storage import storages

from .contracts import ContractError, ImmutableConflict, checksum_bytes, validate_key


PUBLIC_CACHE_CONTROL = "public, max-age=31536000, immutable"
PRIVATE_CACHE_CONTROL = "private, no-store"


@dataclass(frozen=True)
class StoredObject:
    alias: str
    bucket: str | None
    key: str
    checksum: str
    content_type: str
    cache_control: str | None
    created: bool

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def configure_django_environment(
    lab_root: Path,
    *,
    endpoint: str,
    private_bucket: str = "phase3b2-private",
    public_bucket: str = "phase3b2-public",
) -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "test_settings")
    os.environ["PHASE3B2_LAB_ROOT"] = str(lab_root)
    os.environ["PHASE3B2_S3_ENDPOINT"] = endpoint
    os.environ["PHASE3B2_PRIVATE_BUCKET"] = private_bucket
    os.environ["PHASE3B2_PUBLIC_BUCKET"] = public_bucket
    os.environ.setdefault("PHASE3B2_ACCESS_KEY", "phase3b2-test")
    os.environ.setdefault("PHASE3B2_SECRET_KEY", "phase3b2-test")


def reset_moto(endpoint: str) -> None:
    request = Request(f"{endpoint.rstrip('/')}/moto-api/reset", data=b"", method="POST")
    with urlopen(request, timeout=5) as response:
        if response.status != 200:
            raise RuntimeError(f"Moto reset failed: {response.status}")


class S3Lab:
    def __init__(
        self,
        *,
        endpoint: str,
        private_bucket: str = "phase3b2-private",
        public_bucket: str = "phase3b2-public",
        versioned_public_bucket: str = "phase3b2-public-versioned",
        region: str = "us-east-1",
    ):
        self.endpoint = endpoint.rstrip("/")
        self.private_bucket = private_bucket
        self.public_bucket = public_bucket
        self.versioned_public_bucket = versioned_public_bucket
        self.region = region
        client_args = {
            "service_name": "s3",
            "endpoint_url": self.endpoint,
            "region_name": region,
            "aws_access_key_id": os.environ.get("PHASE3B2_ACCESS_KEY", "phase3b2-test"),
            "aws_secret_access_key": os.environ.get("PHASE3B2_SECRET_KEY", "phase3b2-test"),
            "config": Config(s3={"addressing_style": "path"}),
        }
        self.client = boto3.client(**client_args)
        self.anonymous = boto3.client(
            "s3",
            endpoint_url=self.endpoint,
            region_name=region,
            config=Config(signature_version=UNSIGNED, s3={"addressing_style": "path"}),
        )

    def provision(self) -> None:
        for bucket in (self.private_bucket, self.public_bucket, self.versioned_public_bucket):
            self.client.create_bucket(Bucket=bucket)
        self.client.put_bucket_versioning(
            Bucket=self.private_bucket,
            VersioningConfiguration={"Status": "Enabled"},
        )
        self.client.put_bucket_versioning(
            Bucket=self.versioned_public_bucket,
            VersioningConfiguration={"Status": "Enabled"},
        )
        self._make_public(self.public_bucket)
        self._make_public(self.versioned_public_bucket)

    def _make_public(self, bucket: str) -> None:
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "LabAnonymousRead",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{bucket}/*",
                }
            ],
        }
        self.client.put_bucket_policy(Bucket=bucket, Policy=json.dumps(policy))

    def save_alias_immutable(
        self,
        alias: str,
        key: str,
        data: bytes,
        *,
        content_type: str,
    ) -> StoredObject:
        validate_key(key)
        validate_content_type(key, content_type)
        expected_alias = "image_renditions_public" if key.startswith("public/") else "image_originals_private"
        if alias != expected_alias:
            raise ContractError(f"{key} belongs to {expected_alias}, not {alias}")
        storage = storages[alias]
        if storage.exists(key):
            with storage.open(key, "rb") as existing:
                existing_data = existing.read()
            if existing_data != data:
                raise ImmutableConflict(f"immutable object conflict for {key}")
            head = self.head(alias, key)
            return StoredObject(
                alias=alias,
                bucket=self._bucket_for_alias(alias),
                key=key,
                checksum=checksum_bytes(data),
                content_type=str(head["ContentType"]),
                cache_control=head.get("CacheControl"),
                created=False,
            )
        content = ContentFile(data, name=key.rsplit("/", 1)[-1])
        # Do not depend on the operating system's mimetypes database. Minimal
        # Linux images may not know WebP even though the application contract
        # does. S3Storage prefers this explicit content_type attribute.
        content.content_type = content_type
        saved_name = storage.save(key, content)
        if saved_name != key:
            storage.delete(saved_name)
            raise ImmutableConflict(f"storage attempted alternate name {saved_name}")
        head = self.head(alias, key)
        if head["ContentType"] != content_type:
            storage.delete(key)
            raise ContractError(
                f"content type mismatch for {key}: {head['ContentType']} != {content_type}"
            )
        return StoredObject(
            alias=alias,
            bucket=self._bucket_for_alias(alias),
            key=key,
            checksum=checksum_bytes(data),
            content_type=str(head["ContentType"]),
            cache_control=head.get("CacheControl"),
            created=True,
        )

    def put_private_artifact(self, key: str, data: bytes, *, content_type: str) -> StoredObject:
        validate_key(key)
        validate_content_type(key, content_type)
        if key.startswith("public/"):
            raise ContractError("artifact cannot use a public release prefix")
        return self._put_admin_immutable(
            self.private_bucket,
            key,
            data,
            content_type=content_type,
            cache_control=PRIVATE_CACHE_CONTROL,
            alias="private-artifact-admin",
        )

    def put_public_versioned(self, key: str, data: bytes, *, content_type: str) -> str:
        validate_key(key)
        response = self.client.put_object(
            Bucket=self.versioned_public_bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
            CacheControl=PUBLIC_CACHE_CONTROL,
            Metadata={"sha256": checksum_bytes(data), "upload-state": "complete"},
        )
        return str(response["VersionId"])

    def _put_admin_immutable(
        self,
        bucket: str,
        key: str,
        data: bytes,
        *,
        content_type: str,
        cache_control: str,
        alias: str,
    ) -> StoredObject:
        try:
            existing = self.client.get_object(Bucket=bucket, Key=key)["Body"].read()
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") not in {"404", "NoSuchKey"}:
                raise
        else:
            if existing != data:
                raise ImmutableConflict(f"immutable object conflict for {key}")
            head = self.client.head_object(Bucket=bucket, Key=key)
            return StoredObject(
                alias=alias,
                bucket=bucket,
                key=key,
                checksum=checksum_bytes(data),
                content_type=str(head["ContentType"]),
                cache_control=head.get("CacheControl"),
                created=False,
            )
        self.client.put_object(
            Bucket=bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
            CacheControl=cache_control,
            Metadata={"sha256": checksum_bytes(data), "upload-state": "complete"},
        )
        return StoredObject(alias, bucket, key, checksum_bytes(data), content_type, cache_control, True)

    def head(self, alias: str, key: str) -> dict[str, Any]:
        return self.client.head_object(Bucket=self._bucket_for_alias(alias), Key=key)

    def verified_read(self, bucket: str, key: str, expected_checksum: str) -> bytes:
        response = self.client.get_object(Bucket=bucket, Key=key)
        data = response["Body"].read()
        metadata = response.get("Metadata", {})
        if metadata.get("upload-state", "complete") != "complete":
            raise ContractError("partial upload is not readable")
        if checksum_bytes(data) != expected_checksum:
            raise ContractError("checksum mismatch")
        return data

    def anonymous_get(self, bucket: str, key: str, *, version_id: str | None = None) -> bytes:
        parameters: dict[str, str] = {"Bucket": bucket, "Key": key}
        if version_id:
            parameters["VersionId"] = version_id
        return self.anonymous.get_object(**parameters)["Body"].read()

    def anonymous_denied(self, bucket: str, key: str) -> bool:
        try:
            self.anonymous_get(bucket, key)
        except ClientError as exc:
            return exc.response.get("Error", {}).get("Code") in {
                "403",
                "AccessDenied",
                "NoSuchKey",
                "404",
            }
        return False

    def delete(self, bucket: str, key: str) -> dict[str, Any]:
        return self.client.delete_object(Bucket=bucket, Key=key)

    def exists(self, bucket: str, key: str) -> bool:
        try:
            self.client.head_object(Bucket=bucket, Key=key)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in {"404", "NoSuchKey"}:
                return False
            raise
        return True

    def object_versions(self, bucket: str, key: str) -> dict[str, list[dict[str, Any]]]:
        result = self.client.list_object_versions(Bucket=bucket, Prefix=key)
        return {
            "versions": [item for item in result.get("Versions", []) if item["Key"] == key],
            "delete_markers": [
                item for item in result.get("DeleteMarkers", []) if item["Key"] == key
            ],
        }

    def _bucket_for_alias(self, alias: str) -> str:
        if alias == "image_originals_private":
            return self.private_bucket
        if alias == "image_renditions_public":
            return self.public_bucket
        raise ContractError(f"alias {alias} is not an S3 image alias")


class PrivateAccessDenied(PermissionError):
    pass


class RecordingPrivateAccessBoundary:
    """Domain contract used where Moto's version-policy emulation is incomplete."""

    def __init__(self, s3: S3Lab):
        self.s3 = s3
        self.calls: list[dict[str, str | None]] = []

    def get(
        self,
        key: str,
        *,
        principal: str,
        version_id: str | None = None,
    ) -> bytes:
        self.calls.append({"key": key, "principal": principal, "version_id": version_id})
        if principal != "storage-admin":
            raise PrivateAccessDenied("private originals require an administrative principal")
        parameters = {"Bucket": self.s3.private_bucket, "Key": key}
        if version_id:
            parameters["VersionId"] = version_id
        return self.s3.client.get_object(**parameters)["Body"].read()


def validate_content_type(key: str, content_type: str) -> None:
    suffix = key.rsplit(".", 1)[-1].lower() if "." in key else ""
    expected = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
    }.get(suffix)
    if expected and content_type != expected:
        raise ContractError(f"content type {content_type} does not match .{suffix} key")
