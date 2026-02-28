from django.db import models


class Tenant(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name


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

    is_published = models.BooleanField(default=False)
    publish_phone = models.BooleanField(default=False)

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
        

class Person(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="persons")

    full_name = models.CharField(max_length=255)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=64, null=True, blank=True)

    municipality = models.CharField(max_length=255, blank=True)
    note = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.full_name

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
