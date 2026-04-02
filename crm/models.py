from django.db import models
from django.utils.text import slugify


class Tenant(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name


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
