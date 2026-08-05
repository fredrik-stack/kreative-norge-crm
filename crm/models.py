from decimal import Decimal

from django.db import models
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from django.conf import settings

from .validators import validate_sha256, validate_storage_key


class AppendOnlyEventError(Exception):
    """Raised when an image review event mutation is attempted through the ORM."""


IMAGE_REVIEW_EVENT_NULLABLE_LIVE_REFERENCE_FIELDS = frozenset(
    {
        "organization",
        "organization_id",
        "selection",
        "selection_id",
        "rendition_set",
        "rendition_set_id",
        "asset",
        "asset_id",
        "previous_selection",
        "previous_selection_id",
        "restored_from_selection",
        "restored_from_selection_id",
        "actor_user",
        "actor_user_id",
    }
)


def validate_technical_warnings(value) -> None:
    if not isinstance(value, list):
        raise ValidationError("Technical warnings must be a list.")
    if len(value) > 20:
        raise ValidationError("Technical warnings cannot contain more than 20 values.")
    for warning in value:
        if (
            not isinstance(warning, str)
            or not warning.strip()
            or len(warning) > 255
            or "\n" in warning
            or "\r" in warning
        ):
            raise ValidationError(
                "Each technical warning must be non-empty text of at most 255 characters."
            )


class ImageReviewEventBaseQuerySet(models.QuerySet):
    def update(self, **kwargs):
        if not kwargs or any(
            field_name not in IMAGE_REVIEW_EVENT_NULLABLE_LIVE_REFERENCE_FIELDS
            or value is not None
            for field_name, value in kwargs.items()
        ):
            raise AppendOnlyEventError(
                "Image review events only permit nulling live references."
            )
        return super().update(**kwargs)

    def delete(self):
        raise AppendOnlyEventError("Image review events cannot be deleted.")

    def bulk_update(self, objs, fields, batch_size=None):
        raise AppendOnlyEventError("Image review events cannot be bulk-updated.")

    def _update(self, values):
        raise AppendOnlyEventError("Image review events cannot be privately updated.")

    _update.queryset_only = False

    def update_or_create(self, defaults=None, create_defaults=None, **kwargs):
        raise AppendOnlyEventError(
            "Image review events cannot be updated or created by upsert."
        )

    def bulk_create(
        self,
        objs,
        batch_size=None,
        ignore_conflicts=False,
        update_conflicts=False,
        update_fields=None,
        unique_fields=None,
    ):
        if update_conflicts:
            raise AppendOnlyEventError(
                "Image review events cannot be updated by upsert."
            )
        return super().bulk_create(
            objs,
            batch_size=batch_size,
            ignore_conflicts=ignore_conflicts,
            update_conflicts=update_conflicts,
            update_fields=update_fields,
            unique_fields=unique_fields,
        )


class ImageReviewEventQuerySet(ImageReviewEventBaseQuerySet):
    def update(self, **kwargs):
        raise AppendOnlyEventError("Image review events cannot be updated.")


class ImageReviewEventBaseManager(
    models.Manager.from_queryset(ImageReviewEventBaseQuerySet)
):
    use_in_migrations = True


class ImageReviewEventManager(models.Manager.from_queryset(ImageReviewEventQuerySet)):
    use_in_migrations = True


def import_job_upload_to(instance, filename: str) -> str:
    return f"imports/tenant_{instance.tenant_id}/job_{instance.id or 'new'}/{filename}"


def import_job_report_upload_to(instance, filename: str) -> str:
    return f"imports/tenant_{instance.tenant_id}/job_{instance.id or 'new'}/reports/{filename}"


def export_job_upload_to(instance, filename: str) -> str:
    return f"exports/tenant_{instance.tenant_id}/job_{instance.id or 'new'}/{filename}"


class Tenant(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name


class TenantMembership(models.Model):
    class Role(models.TextChoices):
        SUPERADMIN = "superadmin", "Superadmin"
        GRUPPEADMIN = "gruppeadmin", "Gruppeadmin"
        REDIGERER = "redigerer", "Redigerer"
        LESER = "leser", "Leser"

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tenant_memberships")
    role = models.CharField(max_length=24, choices=Role.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("tenant", "user")]
        indexes = [
            models.Index(fields=["tenant", "role"]),
            models.Index(fields=["user", "role"]),
        ]
        ordering = ["tenant__name", "user__username"]

    def __str__(self) -> str:
        return f"{self.user} @ {self.tenant} ({self.get_role_display()})"


class ImageAsset(models.Model):
    class OriginalFormat(models.TextChoices):
        JPEG = "jpeg", "JPEG"
        PNG = "png", "PNG"
        WEBP = "webp", "WebP"

    FORMAT_MIME_TYPES = {
        OriginalFormat.JPEG: "image/jpeg",
        OriginalFormat.PNG: "image/png",
        OriginalFormat.WEBP: "image/webp",
    }

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="image_assets")
    private_storage_key = models.CharField(max_length=1024, validators=[validate_storage_key])
    checksum_sha256 = models.CharField(max_length=64, validators=[validate_sha256])
    original_format = models.CharField(max_length=8, choices=OriginalFormat.choices)
    mime_type = models.CharField(max_length=100)
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()
    file_size_bytes = models.PositiveBigIntegerField()
    validation_version = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "private_storage_key"],
                name="image_asset_tenant_private_key_uniq",
            ),
            models.CheckConstraint(
                condition=models.Q(width__gt=0),
                name="image_asset_width_gt_0",
            ),
            models.CheckConstraint(
                condition=models.Q(height__gt=0),
                name="image_asset_height_gt_0",
            ),
            models.CheckConstraint(
                condition=models.Q(file_size_bytes__gt=0),
                name="image_asset_size_gt_0",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        expected_mime_type = self.FORMAT_MIME_TYPES.get(self.original_format)
        if expected_mime_type and self.mime_type != expected_mime_type:
            raise ValidationError(
                {"mime_type": f"MIME type must be {expected_mime_type} for {self.original_format}."}
            )

    def __str__(self) -> str:
        return f"ImageAsset #{self.pk or 'new'}"


class ImageRenditionSet(models.Model):
    class FitMode(models.TextChoices):
        COVER = "cover", "Cover"
        CONTAIN = "contain", "Contain"

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="image_rendition_sets")
    asset = models.ForeignKey(ImageAsset, on_delete=models.PROTECT, related_name="rendition_sets")
    fit_mode = models.CharField(max_length=8, choices=FitMode.choices)
    focus_x = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal("0.5000"))
    focus_y = models.DecimalField(max_digits=5, decimal_places=4, default=Decimal("0.5000"))
    processing_version = models.CharField(max_length=64)
    render_config_hash_sha256 = models.CharField(max_length=64, validators=[validate_sha256])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "asset", "render_config_hash_sha256"],
                name="image_rset_tenant_asset_hash_uniq",
            ),
            models.CheckConstraint(
                condition=models.Q(focus_x__gte=0, focus_x__lte=1),
                name="image_rset_focus_x_range",
            ),
            models.CheckConstraint(
                condition=models.Q(focus_y__gte=0, focus_y__lte=1),
                name="image_rset_focus_y_range",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        if self.tenant_id and self.asset_id and self.tenant_id != self.asset.tenant_id:
            raise ValidationError({"asset": "Asset must belong to the same tenant as the rendition set."})

    def __str__(self) -> str:
        return f"ImageRenditionSet #{self.pk or 'new'}"


class ImageRendition(models.Model):
    class Variant(models.TextChoices):
        SQUARE = "square", "Square"
        LANDSCAPE = "landscape", "Landscape"
        SHARE = "share", "Share"

    class OutputFormat(models.TextChoices):
        JPEG = "jpeg", "JPEG"
        PNG = "png", "PNG"
        WEBP = "webp", "WebP"

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="image_renditions")
    rendition_set = models.ForeignKey(
        ImageRenditionSet,
        on_delete=models.PROTECT,
        related_name="renditions",
    )
    variant = models.CharField(max_length=12, choices=Variant.choices)
    output_format = models.CharField(max_length=8, choices=OutputFormat.choices)
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()
    file_size_bytes = models.PositiveBigIntegerField()
    checksum_sha256 = models.CharField(max_length=64, validators=[validate_sha256])
    artifact_storage_key = models.CharField(max_length=1024, validators=[validate_storage_key])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "rendition_set", "variant"],
                name="image_rend_tenant_set_variant_uniq",
            ),
            models.UniqueConstraint(
                fields=["tenant", "artifact_storage_key"],
                name="image_rend_tenant_artifact_key_uniq",
            ),
            models.CheckConstraint(
                condition=models.Q(width__gt=0),
                name="image_rend_width_gt_0",
            ),
            models.CheckConstraint(
                condition=models.Q(height__gt=0),
                name="image_rend_height_gt_0",
            ),
            models.CheckConstraint(
                condition=models.Q(file_size_bytes__gt=0),
                name="image_rend_size_gt_0",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        if (
            self.tenant_id
            and self.rendition_set_id
            and self.tenant_id != self.rendition_set.tenant_id
        ):
            raise ValidationError(
                {"rendition_set": "Rendition set must belong to the same tenant as the rendition."}
            )

    def __str__(self) -> str:
        return f"ImageRendition #{self.pk or 'new'} ({self.variant})"


class Tag(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="tags")
    name = models.CharField(max_length=64)
    slug = models.SlugField(max_length=80)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("tenant", "name"), ("tenant", "slug")]
        indexes = [
            models.Index(fields=["tenant", "name"]),
            models.Index(fields=["tenant", "slug"]),
        ]
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or "tag"
            slug = base_slug
            suffix = 2
            while Tag.objects.filter(tenant=self.tenant, slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{suffix}"
                suffix += 1
            self.slug = slug
        super().save(*args, **kwargs)


class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=96, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or "category"
            slug = base_slug
            suffix = 2
            while Category.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{suffix}"
                suffix += 1
            self.slug = slug
        super().save(*args, **kwargs)


class Subcategory(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="subcategories")
    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=96)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("category", "name"), ("category", "slug")]
        indexes = [
            models.Index(fields=["category", "name"]),
            models.Index(fields=["category", "slug"]),
        ]
        ordering = ["category__name", "name"]

    def __str__(self) -> str:
        return f"{self.category.name}: {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or "subcategory"
            slug = base_slug
            suffix = 2
            while Subcategory.objects.filter(category=self.category, slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{suffix}"
                suffix += 1
            self.slug = slug
        super().save(*args, **kwargs)


class Organization(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="organizations")

    name = models.CharField(max_length=255)
    org_number = models.CharField(max_length=32, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=64, null=True, blank=True)

    # MVP: vanlig tekstfelt
    municipalities = models.CharField(
        max_length=255,
        blank=True,
        help_text="Kommune(r), f.eks. Bodø eller Bodø, Tromsø",
    )

    note = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    is_published = models.BooleanField(default=False)
    publish_phone = models.BooleanField(default=False)

    website_url = models.URLField(null=True, blank=True)
    facebook_url = models.URLField(null=True, blank=True)
    instagram_url = models.URLField(null=True, blank=True)
    tiktok_url = models.URLField(null=True, blank=True)
    linkedin_url = models.URLField(null=True, blank=True)
    youtube_url = models.URLField(null=True, blank=True)

    og_title = models.CharField(max_length=255, null=True, blank=True)
    og_description = models.TextField(null=True, blank=True)
    og_image_url = models.URLField(null=True, blank=True)
    thumbnail_image_url = models.URLField(null=True, blank=True)
    auto_thumbnail_url = models.URLField(null=True, blank=True)
    og_last_fetched_at = models.DateTimeField(null=True, blank=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name="organizations")
    categories = models.ManyToManyField(Category, blank=True, related_name="organizations")
    subcategories = models.ManyToManyField(Subcategory, blank=True, related_name="organizations")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "name"]),
            models.Index(fields=["tenant", "org_number"]),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if self.org_number:
            self.org_number = self.org_number.strip().replace(" ", "").replace(".", "")
        super().save(*args, **kwargs)

    def get_primary_link(self) -> str | None:
        for value in [
            self.website_url,
            self.instagram_url,
            self.tiktok_url,
            self.linkedin_url,
            self.facebook_url,
            self.youtube_url,
        ]:
            if value:
                return value
        return None

    def get_primary_link_field(self) -> str | None:
        for field_name in [
            "website_url",
            "instagram_url",
            "tiktok_url",
            "linkedin_url",
            "facebook_url",
            "youtube_url",
        ]:
            if getattr(self, field_name):
                return field_name
        return None

    def get_preview_image_url(self) -> str | None:
        from .services.open_graph import fallback_preview_image

        return self.get_public_image_url() or fallback_preview_image(self.get_primary_link())

    def get_public_image_url(self) -> str | None:
        from .services.open_graph import is_fallback_preview_image

        for candidate in [self.thumbnail_image_url, self.auto_thumbnail_url, self.og_image_url]:
            if not candidate or is_fallback_preview_image(candidate):
                continue
            return candidate
        return None


class OrganizationImageSelection(models.Model):
    class SelectionKind(models.TextChoices):
        ASSET = "asset", "Asset"
        SYSTEM_FALLBACK = "system_fallback", "System fallback"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        ARCHIVED = "archived", "Archived"

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="organization_image_selections",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="image_selections",
    )
    selection_kind = models.CharField(max_length=20, choices=SelectionKind.choices)
    rendition_set = models.ForeignKey(
        ImageRenditionSet,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="organization_selections",
    )
    alt_text = models.CharField(max_length=500)
    public_credit = models.CharField(max_length=500, blank=True, default="")
    revision = models.PositiveIntegerField()
    status = models.CharField(max_length=8, choices=Status.choices)
    locked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="locked_organization_image_selections",
    )
    locked_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "organization", "revision"],
                name="img_sel_tenant_org_rev_uniq",
            ),
            models.UniqueConstraint(
                fields=["tenant", "organization"],
                condition=models.Q(status="active"),
                name="img_sel_one_active_per_org",
            ),
            models.CheckConstraint(
                condition=models.Q(revision__gt=0),
                name="img_sel_revision_gt_0",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        selection_kind="asset",
                        rendition_set__isnull=False,
                    )
                    | models.Q(
                        selection_kind="system_fallback",
                        rendition_set__isnull=True,
                    )
                ),
                name="img_sel_kind_rset_xor",
            ),
            models.CheckConstraint(
                condition=~models.Q(alt_text=""),
                name="img_sel_alt_text_not_empty",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        errors = {}

        if (
            self.tenant_id
            and self.organization_id
            and self.tenant_id != self.organization.tenant_id
        ):
            errors["organization"] = "Organization must belong to the selection tenant."

        if (
            self.tenant_id
            and self.rendition_set_id
            and self.tenant_id != self.rendition_set.tenant_id
        ):
            errors["rendition_set"] = "Rendition set must belong to the selection tenant."

        if self.selection_kind == self.SelectionKind.ASSET and not self.rendition_set_id:
            errors["rendition_set"] = "Asset selections require a rendition set."
        elif (
            self.selection_kind == self.SelectionKind.SYSTEM_FALLBACK
            and self.rendition_set_id
        ):
            errors["rendition_set"] = "System fallback selections cannot have a rendition set."

        if not self.alt_text or not self.alt_text.strip():
            errors["alt_text"] = "Alt text cannot be empty or whitespace only."
        if self.public_credit and not self.public_credit.strip():
            errors["public_credit"] = "Public credit cannot contain only whitespace."

        if errors:
            raise ValidationError(errors)

    def __str__(self) -> str:
        return (
            f"OrganizationImageSelection #{self.pk or 'new'} "
            f"(organization {self.organization_id}, revision {self.revision})"
        )


class ImageReviewEvent(models.Model):
    class EventType(models.TextChoices):
        SELECTION_LOCKED = "selection_locked", "Selection locked"
        SELECTION_REPLACED = "selection_replaced", "Selection replaced"
        SELECTION_REMOVED_TO_FALLBACK = (
            "selection_removed_to_fallback",
            "Selection removed to fallback",
        )
        SELECTION_RESTORED = "selection_restored", "Selection restored"

    class SourceType(models.TextChoices):
        OFFICIAL_WEBSITE = "official_website", "Official website"
        OPEN_GRAPH = "open_graph", "Open Graph"
        WEBSITE_IMAGE = "website_image", "Website image"
        BRAVE_IMAGE_SEARCH = "brave_image_search", "Brave image search"
        UPLOAD = "upload", "Upload"
        PASTED_URL = "pasted_url", "Pasted URL"

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="image_review_events",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="image_review_events",
    )
    selection = models.ForeignKey(
        OrganizationImageSelection,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="review_events",
    )
    rendition_set = models.ForeignKey(
        ImageRenditionSet,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="review_events",
    )
    asset = models.ForeignKey(
        ImageAsset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="review_events",
    )
    previous_selection = models.ForeignKey(
        OrganizationImageSelection,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="replacement_events",
    )
    restored_from_selection = models.ForeignKey(
        OrganizationImageSelection,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="restore_events",
    )
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="image_review_events",
    )

    event_type = models.CharField(max_length=29, choices=EventType.choices)
    organization_id_snapshot = models.PositiveBigIntegerField()
    organization_name_snapshot = models.CharField(max_length=255)
    organization_org_number_snapshot = models.CharField(max_length=32, blank=True, default="")
    selection_id_snapshot = models.PositiveBigIntegerField()
    selection_revision_snapshot = models.PositiveIntegerField()
    selection_kind_snapshot = models.CharField(
        max_length=20,
        choices=OrganizationImageSelection.SelectionKind.choices,
    )
    rendition_set_id_snapshot = models.PositiveBigIntegerField(null=True, blank=True)
    asset_id_snapshot = models.PositiveBigIntegerField(null=True, blank=True)
    asset_checksum_sha256_snapshot = models.CharField(
        max_length=64,
        blank=True,
        default="",
        validators=[validate_sha256],
    )
    asset_validation_version_snapshot = models.CharField(max_length=64, blank=True, default="")
    previous_selection_id_snapshot = models.PositiveBigIntegerField(null=True, blank=True)
    previous_selection_revision_snapshot = models.PositiveIntegerField(null=True, blank=True)
    restored_from_selection_id_snapshot = models.PositiveBigIntegerField(
        null=True,
        blank=True,
    )
    restored_from_selection_revision_snapshot = models.PositiveIntegerField(
        null=True,
        blank=True,
    )
    actor_user_id_snapshot = models.PositiveBigIntegerField()
    actor_username_snapshot = models.CharField(max_length=255)
    alt_text_snapshot = models.CharField(max_length=500)
    public_credit_snapshot = models.CharField(max_length=500, blank=True, default="")
    source_type_snapshot = models.CharField(
        max_length=32,
        choices=SourceType.choices,
        blank=True,
        default="",
    )
    source_url_snapshot = models.URLField(max_length=2048, blank=True, default="")
    source_page_url_snapshot = models.URLField(max_length=2048, blank=True, default="")
    provider_snapshot = models.CharField(max_length=255, blank=True, default="")
    technical_warnings_snapshot = models.JSONField(
        blank=True,
        default=list,
        validators=[validate_technical_warnings],
    )
    approval_text_version_snapshot = models.CharField(max_length=64, blank=True, default="")
    approval_text_snapshot = models.TextField(blank=True, default="")
    created_at = models.DateTimeField()

    _base_objects = ImageReviewEventBaseManager()
    objects = ImageReviewEventManager()

    class Meta:
        base_manager_name = "_base_objects"
        default_manager_name = "objects"
        indexes = [
            models.Index(
                fields=["tenant", "organization_id_snapshot", "created_at"],
                name="img_evt_tenant_org_time_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    organization_id_snapshot__gt=0,
                    selection_id_snapshot__gt=0,
                    selection_revision_snapshot__gt=0,
                    actor_user_id_snapshot__gt=0,
                ),
                name="img_evt_required_ids_gt_0",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        event_type="selection_locked",
                        previous_selection_id_snapshot__isnull=True,
                        previous_selection_revision_snapshot__isnull=True,
                    )
                    | models.Q(
                        event_type="selection_replaced",
                        previous_selection_id_snapshot__isnull=False,
                        previous_selection_id_snapshot__gt=0,
                        previous_selection_revision_snapshot__isnull=False,
                        previous_selection_revision_snapshot__gt=0,
                    )
                    | models.Q(
                        event_type="selection_removed_to_fallback",
                        selection_kind_snapshot="system_fallback",
                        previous_selection_id_snapshot__isnull=False,
                        previous_selection_id_snapshot__gt=0,
                        previous_selection_revision_snapshot__isnull=False,
                        previous_selection_revision_snapshot__gt=0,
                    )
                    | models.Q(
                        event_type="selection_restored",
                        previous_selection_id_snapshot__isnull=False,
                        previous_selection_id_snapshot__gt=0,
                        previous_selection_revision_snapshot__isnull=False,
                        previous_selection_revision_snapshot__gt=0,
                    )
                ),
                name="img_evt_previous_contract",
            ),
            models.CheckConstraint(
                condition=(
                    (
                        models.Q(
                            event_type__in=[
                                "selection_locked",
                                "selection_replaced",
                            ],
                            selection_kind_snapshot="asset",
                            rendition_set_id_snapshot__isnull=False,
                            rendition_set_id_snapshot__gt=0,
                            asset_id_snapshot__isnull=False,
                            asset_id_snapshot__gt=0,
                        )
                        & ~models.Q(asset_checksum_sha256_snapshot="")
                        & ~models.Q(asset_validation_version_snapshot="")
                        & ~models.Q(source_type_snapshot="")
                        & ~models.Q(approval_text_version_snapshot="")
                        & ~models.Q(approval_text_snapshot="")
                    )
                    | (
                        models.Q(
                            event_type="selection_restored",
                            selection_kind_snapshot="asset",
                            rendition_set_id_snapshot__isnull=False,
                            rendition_set_id_snapshot__gt=0,
                            asset_id_snapshot__isnull=False,
                            asset_id_snapshot__gt=0,
                            source_type_snapshot="",
                            source_url_snapshot="",
                            source_page_url_snapshot="",
                            provider_snapshot="",
                            technical_warnings_snapshot=[],
                            approval_text_version_snapshot="",
                            approval_text_snapshot="",
                        )
                        & ~models.Q(asset_checksum_sha256_snapshot="")
                        & ~models.Q(asset_validation_version_snapshot="")
                    )
                    | models.Q(
                        selection_kind_snapshot="system_fallback",
                        rendition_set_id_snapshot__isnull=True,
                        asset_id_snapshot__isnull=True,
                        asset_checksum_sha256_snapshot="",
                        asset_validation_version_snapshot="",
                        source_type_snapshot="",
                        source_url_snapshot="",
                        source_page_url_snapshot="",
                        provider_snapshot="",
                        technical_warnings_snapshot=[],
                        approval_text_version_snapshot="",
                        approval_text_snapshot="",
                    )
                ),
                name="img_evt_selection_kind_contract",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        event_type="selection_restored",
                        selection_kind_snapshot="asset",
                        restored_from_selection_id_snapshot__isnull=False,
                        restored_from_selection_id_snapshot__gt=0,
                        restored_from_selection_revision_snapshot__isnull=False,
                        restored_from_selection_revision_snapshot__gt=0,
                    )
                    | (
                        ~models.Q(event_type="selection_restored")
                        & models.Q(
                            restored_from_selection_id_snapshot__isnull=True,
                            restored_from_selection_revision_snapshot__isnull=True,
                        )
                    )
                ),
                name="img_evt_restore_contract",
            ),
            models.CheckConstraint(
                condition=models.Q(source_type_snapshot="")
                | models.Q(
                    source_type_snapshot__in=[
                        "official_website",
                        "open_graph",
                        "website_image",
                        "brave_image_search",
                        "upload",
                        "pasted_url",
                    ]
                ),
                name="img_evt_source_type_valid",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(source_type_snapshot="", source_url_snapshot="")
                    | models.Q(source_type_snapshot="upload")
                    | ~models.Q(source_url_snapshot="")
                ),
                name="img_evt_source_url_contract",
            ),
            models.CheckConstraint(
                condition=(
                    ~models.Q(organization_name_snapshot="")
                    & ~models.Q(actor_username_snapshot="")
                    & ~models.Q(alt_text_snapshot="")
                ),
                name="img_evt_required_text_not_empty",
            ),
        ]

    def save(self, *args, **kwargs):
        if self.pk is not None and self.__class__._base_objects.filter(pk=self.pk).exists():
            raise AppendOnlyEventError("Image review events cannot be updated.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise AppendOnlyEventError("Image review events cannot be deleted.")

    def __str__(self) -> str:
        return f"ImageReviewEvent #{self.pk or 'new'} ({self.event_type})"


class Person(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="persons")

    full_name = models.CharField(max_length=255)
    title = models.CharField(max_length=255, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=64, null=True, blank=True)
    website_url = models.URLField(null=True, blank=True)
    instagram_url = models.URLField(null=True, blank=True)
    tiktok_url = models.URLField(null=True, blank=True)
    linkedin_url = models.URLField(null=True, blank=True)
    facebook_url = models.URLField(null=True, blank=True)
    youtube_url = models.URLField(null=True, blank=True)

    municipality = models.CharField(max_length=255, blank=True)
    note = models.TextField(null=True, blank=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name="persons")
    categories = models.ManyToManyField(Category, blank=True, related_name="persons")
    subcategories = models.ManyToManyField(Subcategory, blank=True, related_name="persons")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.full_name

    def get_public_emails(self) -> list[str]:
        return list(
            self.contacts.filter(type="EMAIL", is_public=True)
            .order_by("-is_primary", "id")
            .values_list("value", flat=True)
        )

    def get_public_phones(self) -> list[str]:
        return list(
            self.contacts.filter(type="PHONE", is_public=True)
            .order_by("-is_primary", "id")
            .values_list("value", flat=True)
        )

class PersonContact(models.Model):
    CONTACT_TYPES = [
        ("EMAIL", "Email"),
        ("PHONE", "Phone"),
    ]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="person_contacts")
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="contacts")

    type = models.CharField(max_length=16, choices=CONTACT_TYPES)
    value = models.CharField(max_length=255)

    is_primary = models.BooleanField(default=False)
    is_public = models.BooleanField(default=False)  # til public API senere

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "type", "value"]),
        ]

    def __str__(self) -> str:
        return f"{self.person}: {self.type} {self.value}"


class OrganizationPerson(models.Model):
    STATUS_CHOICES = [
        ("ACTIVE", "Active"),
        ("INACTIVE", "Inactive"),
    ]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="organization_people")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="org_people")
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="person_orgs")

    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="ACTIVE")
    publish_person = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("tenant", "organization", "person")

    def __str__(self) -> str:
        return f"{self.person} @ {self.organization} ({self.status})"


class ImportJob(models.Model):
    class SourceType(models.TextChoices):
        CSV = "CSV", "CSV"
        XLSX = "XLSX", "XLSX"
        GOOGLE_SHEET = "GOOGLE_SHEET", "Google Sheet"
        CHECKIN = "CHECKIN", "Checkin"
        MAILMOJO = "MAILMOJO", "Mailmojo"
        MANUAL_API = "MANUAL_API", "Manual API"

    class ImportMode(models.TextChoices):
        COMBINED = "COMBINED", "Combined"
        ORGANIZATIONS_ONLY = "ORGANIZATIONS_ONLY", "Organizations only"
        PEOPLE_ONLY = "PEOPLE_ONLY", "People only"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        UPLOADED = "UPLOADED", "Uploaded"
        PARSED = "PARSED", "Parsed"
        PREVIEW_READY = "PREVIEW_READY", "Preview ready"
        AWAITING_REVIEW = "AWAITING_REVIEW", "Awaiting review"
        COMMITTING = "COMMITTING", "Committing"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"
        CANCELLED = "CANCELLED", "Cancelled"

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="import_jobs")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="created_import_jobs")
    source_type = models.CharField(max_length=32, choices=SourceType.choices)
    import_mode = models.CharField(max_length=32, choices=ImportMode.choices)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.DRAFT)
    filename = models.CharField(max_length=255, blank=True)
    file = models.FileField(upload_to=import_job_upload_to, blank=True, null=True)
    summary_json = models.JSONField(default=dict, blank=True)
    config_json = models.JSONField(default=dict, blank=True)
    preview_report_file = models.FileField(upload_to=import_job_report_upload_to, blank=True, null=True)
    error_report_file = models.FileField(upload_to=import_job_report_upload_to, blank=True, null=True)
    committed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["tenant", "created_at"]),
            models.Index(fields=["tenant", "source_type"]),
        ]

    def __str__(self) -> str:
        return f"ImportJob #{self.pk or 'new'} ({self.tenant.slug})"


class ImportRow(models.Model):
    class RowStatus(models.TextChoices):
        VALID = "VALID", "Valid"
        INVALID = "INVALID", "Invalid"
        REVIEW_REQUIRED = "REVIEW_REQUIRED", "Review required"
        SKIPPED = "SKIPPED", "Skipped"
        COMMITTED = "COMMITTED", "Committed"
        COMMIT_FAILED = "COMMIT_FAILED", "Commit failed"

    class ProposedAction(models.TextChoices):
        CREATE = "CREATE", "Create"
        UPDATE = "UPDATE", "Update"
        LINK_ONLY = "LINK_ONLY", "Link only"
        SKIP = "SKIP", "Skip"

    import_job = models.ForeignKey(ImportJob, on_delete=models.CASCADE, related_name="rows")
    row_number = models.PositiveIntegerField()
    raw_payload_json = models.JSONField(default=dict, blank=True)
    normalized_payload_json = models.JSONField(default=dict, blank=True)
    detected_entities_json = models.JSONField(default=dict, blank=True)
    match_result_json = models.JSONField(default=dict, blank=True)
    ai_suggestions_json = models.JSONField(default=dict, blank=True)
    validation_errors_json = models.JSONField(default=list, blank=True)
    warnings_json = models.JSONField(default=list, blank=True)
    row_status = models.CharField(max_length=32, choices=RowStatus.choices, default=RowStatus.REVIEW_REQUIRED)
    proposed_action = models.CharField(max_length=32, choices=ProposedAction.choices, default=ProposedAction.SKIP)
    decision_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["row_number", "id"]
        unique_together = [("import_job", "row_number")]
        indexes = [
            models.Index(fields=["import_job", "row_status"]),
            models.Index(fields=["import_job", "proposed_action"]),
        ]

    def __str__(self) -> str:
        return f"ImportRow #{self.row_number} for job {self.import_job_id}"


class ImportDecision(models.Model):
    class DecisionType(models.TextChoices):
        USE_EXISTING_ORGANIZATION = "USE_EXISTING_ORGANIZATION", "Use existing organization"
        CREATE_NEW_ORGANIZATION = "CREATE_NEW_ORGANIZATION", "Create new organization"
        USE_EXISTING_PERSON = "USE_EXISTING_PERSON", "Use existing person"
        CREATE_NEW_PERSON = "CREATE_NEW_PERSON", "Create new person"
        MAP_CATEGORY = "MAP_CATEGORY", "Map category"
        MAP_SUBCATEGORY = "MAP_SUBCATEGORY", "Map subcategory"
        ACCEPT_NEW_TAG = "ACCEPT_NEW_TAG", "Accept new tag"
        ACCEPT_AI_SUGGESTION = "ACCEPT_AI_SUGGESTION", "Accept AI suggestion"
        IGNORE_AI_SUGGESTION = "IGNORE_AI_SUGGESTION", "Ignore AI suggestion"
        SKIP_ROW = "SKIP_ROW", "Skip row"

    import_row = models.ForeignKey(ImportRow, on_delete=models.CASCADE, related_name="decisions")
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="import_decisions")
    decision_type = models.CharField(max_length=48, choices=DecisionType.choices)
    payload_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["import_row", "decision_type"]),
        ]

    def __str__(self) -> str:
        return f"Decision {self.get_decision_type_display()} for row {self.import_row.row_number}"


class ImportCommitLog(models.Model):
    class EntityType(models.TextChoices):
        ORGANIZATION = "ORGANIZATION", "Organization"
        PERSON = "PERSON", "Person"
        PERSON_CONTACT = "PERSON_CONTACT", "Person contact"
        ORGANIZATION_PERSON = "ORGANIZATION_PERSON", "Organization person"
        TAG = "TAG", "Tag"

    class Action(models.TextChoices):
        CREATED = "CREATED", "Created"
        UPDATED = "UPDATED", "Updated"
        LINKED = "LINKED", "Linked"
        SKIPPED = "SKIPPED", "Skipped"
        FAILED = "FAILED", "Failed"

    import_job = models.ForeignKey(ImportJob, on_delete=models.CASCADE, related_name="commit_logs")
    import_row = models.ForeignKey(ImportRow, on_delete=models.SET_NULL, null=True, blank=True, related_name="commit_logs")
    entity_type = models.CharField(max_length=32, choices=EntityType.choices)
    entity_id = models.PositiveIntegerField(null=True, blank=True)
    action = models.CharField(max_length=16, choices=Action.choices)
    details_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["import_job", "action"]),
            models.Index(fields=["import_job", "entity_type"]),
        ]

    def __str__(self) -> str:
        return f"{self.get_action_display()} {self.get_entity_type_display()} for job {self.import_job_id}"


class ExportJob(models.Model):
    class ExportType(models.TextChoices):
        SEARCH_RESULTS = "SEARCH_RESULTS", "Search results"
        ADMIN_FULL = "ADMIN_FULL", "Admin full"
        PERSONS_ONLY = "PERSONS_ONLY", "Persons only"
        ORGANIZATIONS_ONLY = "ORGANIZATIONS_ONLY", "Organizations only"

    class Format(models.TextChoices):
        CSV = "CSV", "CSV"
        XLSX = "XLSX", "XLSX"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        RUNNING = "RUNNING", "Running"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="export_jobs")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="created_export_jobs")
    export_type = models.CharField(max_length=32, choices=ExportType.choices)
    format = models.CharField(max_length=8, choices=Format.choices)
    filters_json = models.JSONField(default=dict, blank=True)
    selected_fields_json = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    file = models.FileField(upload_to=export_job_upload_to, blank=True, null=True)
    summary_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["tenant", "created_at"]),
            models.Index(fields=["tenant", "export_type"]),
        ]

    def __str__(self) -> str:
        return f"ExportJob #{self.pk or 'new'} ({self.tenant.slug})"
