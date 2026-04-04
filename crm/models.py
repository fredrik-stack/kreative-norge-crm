from django.db import models
from django.utils.text import slugify
from django.conf import settings


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
        public_emails = list(
            self.contacts.filter(type="EMAIL", is_public=True)
            .order_by("-is_primary", "id")
            .values_list("value", flat=True)
        )
        if public_emails:
            return public_emails
        return [self.email] if self.email else []

    def get_public_phones(self) -> list[str]:
        public_phones = list(
            self.contacts.filter(type="PHONE", is_public=True)
            .order_by("-is_primary", "id")
            .values_list("value", flat=True)
        )
        return public_phones

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
