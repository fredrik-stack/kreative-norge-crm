from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256
import json

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from crm.models import ImageAsset, ImageRendition, ImageRenditionSet, Tenant

from .processing import (
    PROCESSING_PROFILE,
    VALIDATION_VERSION,
    ProcessedImage,
    ProcessedRendition,
    process_uploaded_image,
)
from .storage import ImmutableStorageResult, _save_immutable


REQUIRED_VARIANTS = ("square", "landscape", "share")


class ImageIngestError(RuntimeError):
    pass


class ImageIngestFeatureDisabledError(ImageIngestError):
    pass


class ImageIngestConflictError(ImageIngestError):
    pass


class UnsupportedImageProcessingProfileError(ImageIngestError):
    pass


@dataclass(frozen=True)
class ImageIngestResult:
    asset: ImageAsset
    rendition_set: ImageRenditionSet
    renditions: tuple[ImageRendition, ...]
    aggregate_created: bool
    original_storage_created: bool
    artifact_storage_created: tuple[bool, ...]
    warnings: tuple[str, ...]

    @property
    def status(self) -> str:
        return "created" if self.aggregate_created else "reused"

    @property
    def asset_id(self) -> int:
        return self.asset.pk

    @property
    def rendition_set_id(self) -> int:
        return self.rendition_set.pk

    @property
    def rendition_ids(self) -> tuple[int, ...]:
        return tuple(rendition.pk for rendition in self.renditions)


def _canonical_hash(payload: dict[str, object]) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256(serialized.encode("ascii")).hexdigest()


def _render_config(processed: ProcessedImage) -> dict[str, object]:
    return {
        "fit_mode": processed.fit_mode,
        "focus": [round(processed.focus_x, 4), round(processed.focus_y, 4)],
        "processing_version": processed.processing_version,
        "source_checksum_sha256": processed.source.checksum_sha256,
        "variants": [
            {
                "height": rendition.height,
                "output_format": rendition.output_format,
                "variant": rendition.variant,
                "width": rendition.width,
            }
            for rendition in processed.renditions
        ],
    }


def _source_key(tenant_id: int, processed: ProcessedImage) -> str:
    return (
        f"tenants/{tenant_id}/originals/{processed.source.checksum_sha256}."
        f"{processed.source.extension}"
    )


def _artifact_key(
    tenant_id: int,
    processed: ProcessedImage,
    render_config_hash: str,
    rendition: ProcessedRendition,
) -> str:
    return (
        f"tenants/{tenant_id}/artifacts/{processed.processing_version}/"
        f"{processed.source.checksum_sha256}/{render_config_hash}/"
        f"{rendition.variant}-{rendition.checksum_sha256}.{rendition.extension}"
    )


def _assert_model_values(instance, expected: dict[str, object], label: str) -> None:
    for field, value in expected.items():
        if getattr(instance, field) != value:
            raise ImageIngestConflictError(f"Existing {label} conflicts on {field}.")


def _expected_rendition_values(
    tenant_id: int,
    processed: ProcessedImage,
    render_config_hash: str,
) -> dict[str, dict[str, object]]:
    return {
        rendition.variant: {
            "tenant_id": tenant_id,
            "variant": rendition.variant,
            "output_format": rendition.output_format,
            "width": rendition.width,
            "height": rendition.height,
            "file_size_bytes": len(rendition.encoded_bytes),
            "checksum_sha256": rendition.checksum_sha256,
            "artifact_storage_key": _artifact_key(
                tenant_id,
                processed,
                render_config_hash,
                rendition,
            ),
        }
        for rendition in processed.renditions
    }


def _create_or_reuse_database_aggregate(
    *,
    tenant: Tenant,
    processed: ProcessedImage,
    source_key: str,
    render_config_hash: str,
) -> tuple[ImageAsset, ImageRenditionSet, tuple[ImageRendition, ...], bool]:
    asset_values = {
        "checksum_sha256": processed.source.checksum_sha256,
        "original_format": processed.source.original_format,
        "mime_type": processed.source.mime_type,
        "width": processed.source.width,
        "height": processed.source.height,
        "file_size_bytes": len(processed.source.original_bytes),
        "validation_version": VALIDATION_VERSION,
    }
    expected_renditions = _expected_rendition_values(tenant.pk, processed, render_config_hash)
    focus_x = Decimal(str(round(processed.focus_x, 4))).quantize(Decimal("0.0001"))
    focus_y = Decimal(str(round(processed.focus_y, 4))).quantize(Decimal("0.0001"))

    try:
        with transaction.atomic():
            asset, asset_created = ImageAsset.objects.get_or_create(
                tenant=tenant,
                private_storage_key=source_key,
                defaults=asset_values,
            )
            _assert_model_values(asset, asset_values, "image asset")
            asset.full_clean()

            rendition_set_values = {
                "fit_mode": processed.fit_mode,
                "focus_x": focus_x,
                "focus_y": focus_y,
                "processing_version": processed.processing_version,
            }
            rendition_set, set_created = ImageRenditionSet.objects.get_or_create(
                tenant=tenant,
                asset=asset,
                render_config_hash_sha256=render_config_hash,
                defaults=rendition_set_values,
            )
            _assert_model_values(rendition_set, rendition_set_values, "rendition set")
            rendition_set.full_clean()

            existing_renditions = list(
                ImageRendition.objects.filter(rendition_set=rendition_set).order_by("variant")
            )
            if set_created:
                if existing_renditions:
                    raise ImageIngestConflictError("New rendition set unexpectedly contains renditions.")
                new_renditions = []
                for variant in REQUIRED_VARIANTS:
                    values = expected_renditions[variant]
                    rendition = ImageRendition(
                        rendition_set=rendition_set,
                        **values,
                    )
                    rendition.full_clean()
                    new_renditions.append(rendition)
                ImageRendition.objects.bulk_create(new_renditions)
                existing_renditions = list(
                    ImageRendition.objects.filter(rendition_set=rendition_set).order_by("variant")
                )
            if (
                len(existing_renditions) != 3
                or {item.variant for item in existing_renditions} != set(expected_renditions)
            ):
                raise ImageIngestConflictError(
                    "Existing rendition aggregate is incomplete; implicit repair is not allowed."
                )
            for rendition in existing_renditions:
                _assert_model_values(
                    rendition,
                    {
                        "rendition_set_id": rendition_set.pk,
                        **expected_renditions[rendition.variant],
                    },
                    f"{rendition.variant} rendition",
                )
                rendition.full_clean()
            existing_by_variant = {
                rendition.variant: rendition for rendition in existing_renditions
            }
            existing_renditions = [
                existing_by_variant[variant] for variant in REQUIRED_VARIANTS
            ]
    except ImageIngestConflictError:
        raise
    except (IntegrityError, ValidationError) as error:
        raise ImageIngestConflictError("Image aggregate conflicts with persisted data.") from error

    return asset, rendition_set, tuple(existing_renditions), asset_created or set_created


def ingest_uploaded_image(
    *,
    tenant: Tenant,
    upload,
    content_mode: str,
    focus_x: float | None = None,
    focus_y: float | None = None,
    processing_profile: str = PROCESSING_PROFILE,
) -> ImageIngestResult:
    if not settings.IMAGE_ASSET_FEATURE_ENABLED:
        raise ImageIngestFeatureDisabledError(
            "Image asset feature is disabled; image ingest is unavailable."
        )
    if processing_profile != PROCESSING_PROFILE:
        raise UnsupportedImageProcessingProfileError(
            f"Only processing profile {PROCESSING_PROFILE} is supported."
        )
    if not isinstance(tenant, Tenant) or not tenant.pk or not Tenant.objects.filter(pk=tenant.pk).exists():
        raise ImageIngestError("Tenant must be a persisted Tenant instance.")

    processed = process_uploaded_image(
        upload,
        fit_mode=content_mode,
        focus_x=focus_x,
        focus_y=focus_y,
    )
    render_config_hash = _canonical_hash(_render_config(processed))
    source_key = _source_key(tenant.pk, processed)
    original_storage = _save_immutable(
        alias="image_originals_private",
        requested_key=source_key,
        data=processed.source.original_bytes,
        content_type=processed.source.mime_type,
    )
    artifact_storage: list[ImmutableStorageResult] = []
    for rendition in processed.renditions:
        artifact_storage.append(
            _save_immutable(
                alias="image_renditions_public",
                requested_key=_artifact_key(tenant.pk, processed, render_config_hash, rendition),
                data=rendition.encoded_bytes,
                content_type=rendition.mime_type,
            )
        )

    asset, rendition_set, renditions, aggregate_created = _create_or_reuse_database_aggregate(
        tenant=tenant,
        processed=processed,
        source_key=source_key,
        render_config_hash=render_config_hash,
    )
    return ImageIngestResult(
        asset=asset,
        rendition_set=rendition_set,
        renditions=renditions,
        aggregate_created=aggregate_created,
        original_storage_created=original_storage.created,
        artifact_storage_created=tuple(item.created for item in artifact_storage),
        warnings=processed.source.warnings,
    )
