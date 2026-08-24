from __future__ import annotations

from dataclasses import asdict, dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.db.models import Prefetch

from crm.models import Organization, OrganizationImageRelease, OrganizationImageSelection
from crm.services.open_graph import is_fallback_preview_image
from image_safety.release_keys import REQUIRED_RELEASE_VARIANTS

from .bridge_client import ImageSafetyBridgeClient, ImageSafetyBridgeError
from .fetch import SecureImageFetchError, normalize_external_url
from .release_validation import (
    PublicReleaseMappingInvalid,
    PublicReleaseScopeInactive,
    validated_release_mappings,
)
from .safety_guards import legacy_image_is_blocked


LEGACY_FIELDS = ("thumbnail_image_url", "auto_thumbnail_url", "og_image_url")


@dataclass(frozen=True, slots=True)
class LegacyImageInventory:
    organizations_total: int = 0
    organizations_published: int = 0
    organizations_unpublished: int = 0
    thumbnail_image_url_set: int = 0
    auto_thumbnail_url_set: int = 0
    og_image_url_set: int = 0
    organizations_with_legacy_url: int = 0
    organizations_with_multiple_legacy_urls: int = 0
    organizations_with_duplicate_field_urls: int = 0
    organizations_with_active_typed_selection: int = 0
    organizations_with_system_fallback: int = 0
    organizations_without_selection: int = 0
    organizations_with_selection_bound_public_release: int = 0
    organizations_with_public_release: int = 0
    organizations_blocked_by_legacy_guard: int = 0
    syntactically_invalid_legacy_urls: int = 0
    favicon_derived_urls: int = 0
    credential_or_signed_url_suspicions: int = 0

    def as_dict(self) -> dict[str, int]:
        return asdict(self)


def _redacted_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        return "[INVALID URL]"
    query = urlencode([(key, "[REDACTED]") for key, _ in parse_qsl(parsed.query, keep_blank_values=True)])
    hostname = parsed.hostname or "[INVALID HOST]"
    netloc = hostname
    if port:
        netloc = f"{netloc}:{port}"
    return urlunsplit((parsed.scheme, netloc, parsed.path, query, ""))


def _has_active_public_release(
    *,
    organization: Organization,
    active_selection: OrganizationImageSelection | None,
    bridge: ImageSafetyBridgeClient,
) -> tuple[bool, bool]:
    if active_selection is None:
        return False, False
    releases = [
        release
        for release in organization.image_releases.all()
        if release.selection_id == active_selection.pk
    ]
    if len(releases) != 1:
        return bool(releases), False
    release = releases[0]
    try:
        mappings = validated_release_mappings(release)
    except (PublicReleaseScopeInactive, PublicReleaseMappingInvalid):
        return True, False
    for variant in REQUIRED_RELEASE_VARIANTS:
        mapping = mappings[variant]
        try:
            authorization = bridge.authorize(
                release_id=str(release.release_id),
                tenant_id=release.tenant_id,
                organization_id=release.organization_id,
                variant=variant,
                public_storage_key=mapping.public_storage_key,
                artifact_checksum_sha256=mapping.artifact_checksum_sha256_snapshot,
                source_checksum_sha256=release.rendition_set.asset.checksum_sha256,
            )
        except ImageSafetyBridgeError:
            return True, False
        if not authorization.authorized:
            return True, False
    return True, True


def audit_legacy_image_sources(*, verbose: bool = False) -> tuple[LegacyImageInventory, list[dict[str, object]]]:
    counters = {field.name: 0 for field in LegacyImageInventory.__dataclass_fields__.values()}
    details: list[dict[str, object]] = []
    releases = OrganizationImageRelease.objects.select_related(
        "rendition_set__asset",
    ).prefetch_related("renditions__rendition")
    organizations = Organization.objects.order_by("pk").prefetch_related(
        "image_selections",
        Prefetch("image_releases", queryset=releases),
    )
    # Inventory is diagnostic and must fail closed without multiplying the normal
    # five-second serving timeout across Organizations.
    bridge = ImageSafetyBridgeClient(timeout=0.1)
    for organization in organizations:
        counters["organizations_total"] += 1
        counters[
            "organizations_published" if organization.is_published else "organizations_unpublished"
        ] += 1
        values = {
            field_name: getattr(organization, field_name)
            for field_name in LEGACY_FIELDS
            if getattr(organization, field_name)
        }
        for field_name in values:
            counters[f"{field_name}_set"] += 1
        if values:
            counters["organizations_with_legacy_url"] += 1
            if len(values) > 1:
                counters["organizations_with_multiple_legacy_urls"] += 1
            if len(set(values.values())) < len(values):
                counters["organizations_with_duplicate_field_urls"] += 1
            if legacy_image_is_blocked(
                tenant_id=organization.tenant_id,
                organization_id=organization.pk,
            ):
                counters["organizations_blocked_by_legacy_guard"] += 1

        active_selection = next(
            (
                item
                for item in organization.image_selections.all()
                if item.status == OrganizationImageSelection.Status.ACTIVE
            ),
            None,
        )
        if active_selection is None:
            counters["organizations_without_selection"] += 1
        else:
            counters["organizations_with_active_typed_selection"] += 1
            if active_selection.selection_kind == OrganizationImageSelection.SelectionKind.SYSTEM_FALLBACK:
                counters["organizations_with_system_fallback"] += 1
        has_binding, is_active_release = _has_active_public_release(
            organization=organization,
            active_selection=active_selection,
            bridge=bridge,
        )
        if has_binding:
            counters["organizations_with_selection_bound_public_release"] += 1
        if is_active_release:
            counters["organizations_with_public_release"] += 1

        invalid_fields: list[str] = []
        favicon_fields: list[str] = []
        suspicious_fields: list[str] = []
        for field_name, value in values.items():
            if is_fallback_preview_image(value):
                counters["favicon_derived_urls"] += 1
                favicon_fields.append(field_name)
            try:
                parsed = urlsplit(value)
                if parsed.fragment:
                    raise SecureImageFetchError("invalid_url", "Fragments are unsupported.")
                normalize_external_url(value)
            except SecureImageFetchError as error:
                if error.code == "credentials_forbidden":
                    counters["credential_or_signed_url_suspicions"] += 1
                    suspicious_fields.append(field_name)
                else:
                    counters["syntactically_invalid_legacy_urls"] += 1
                    invalid_fields.append(field_name)
            except ValueError:
                counters["syntactically_invalid_legacy_urls"] += 1
                invalid_fields.append(field_name)
        if verbose and values:
            details.append(
                {
                    "organization_id": organization.pk,
                    "tenant_id": organization.tenant_id,
                    "urls": {key: _redacted_url(value) for key, value in values.items()},
                    "invalid_fields": invalid_fields,
                    "favicon_fields": favicon_fields,
                    "suspicious_fields": suspicious_fields,
                }
            )
    return LegacyImageInventory(**counters), details
