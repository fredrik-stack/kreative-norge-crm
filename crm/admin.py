from django.contrib import admin
from django.forms.models import BaseInlineFormSet

from .models import (
    Tenant,
    TenantMembership,
    Tag,
    Category,
    Subcategory,
    Organization,
    Person,
    OrganizationPerson,
    PersonContact,
    ImportJob,
    ImportRow,
    ImportDecision,
    ImportCommitLog,
    ExportJob,
)


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "created_at")
    search_fields = ("name", "slug")


@admin.register(TenantMembership)
class TenantMembershipAdmin(admin.ModelAdmin):
    list_display = ("id", "tenant", "user", "role", "created_at")
    list_filter = ("tenant", "role")
    search_fields = ("tenant__name", "user__username", "user__email")


class PersonContactInlineFormSet(BaseInlineFormSet):
    def save_new(self, form, commit=True):
        instance = super().save_new(form, commit=False)

        # self.instance er Person-objektet i admin
        instance.person = self.instance
        instance.tenant = self.instance.tenant

        if commit:
            instance.save()
            form.save_m2m()

        return instance



class PersonContactInline(admin.TabularInline):
    model = PersonContact
    formset = PersonContactInlineFormSet
    extra = 0
    fields = ("type", "value", "is_primary", "is_public")

class PersonContactInlineFormSet(BaseInlineFormSet):
    def save_new(self, form, commit=True):
        instance = super().save_new(form, commit=False)

        # self.instance er Person-objektet i admin
        instance.person = self.instance
        instance.tenant = self.instance.tenant

        if commit:
            instance.save()
            form.save_m2m()

        return instance


class OrganizationPersonInlineFormSet(BaseInlineFormSet):
    def save_new(self, form, commit=True):
        instance = super().save_new(form, commit=False)

        # self.instance er Organization-objektet i admin
        instance.organization = self.instance
        instance.tenant = self.instance.tenant

        if commit:
            instance.save()
            form.save_m2m()

        return instance


class OrganizationPersonInline(admin.TabularInline):
    model = OrganizationPerson
    formset = OrganizationPersonInlineFormSet
    extra = 0
    autocomplete_fields = ("person",)
    fields = ("person", "status", "publish_person")


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "tenant", "org_number", "email", "is_published", "created_at")
    list_filter = ("tenant", "is_published")
    search_fields = ("name", "org_number", "email")
    inlines = [OrganizationPersonInline]
    filter_horizontal = ("tags", "subcategories")


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ("id", "full_name", "tenant", "email", "phone", "municipality", "created_at")
    list_filter = ("tenant",)
    search_fields = ("full_name", "email", "phone")
    inlines = [PersonContactInline]
    filter_horizontal = ("tags", "subcategories")


@admin.register(OrganizationPerson)
class OrganizationPersonAdmin(admin.ModelAdmin):
    list_display = ("id", "tenant", "organization", "person", "status", "publish_person", "created_at")
    list_filter = ("tenant", "status", "publish_person")
    search_fields = ("organization__name", "person__full_name", "person__email")


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "tenant", "created_at")
    list_filter = ("tenant",)
    search_fields = ("name", "slug")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "created_at")
    search_fields = ("name", "slug")


@admin.register(Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "category", "created_at")
    list_filter = ("category",)
    search_fields = ("name", "slug", "category__name")


@admin.register(ImportJob)
class ImportJobAdmin(admin.ModelAdmin):
    list_display = ("id", "tenant", "source_type", "import_mode", "status", "filename", "created_by", "created_at")
    list_filter = ("tenant", "source_type", "import_mode", "status")
    search_fields = ("filename", "created_by__username")


@admin.register(ImportRow)
class ImportRowAdmin(admin.ModelAdmin):
    list_display = ("id", "import_job", "row_number", "row_status", "proposed_action", "created_at")
    list_filter = ("row_status", "proposed_action", "import_job__tenant")
    search_fields = ("import_job__id",)


@admin.register(ImportDecision)
class ImportDecisionAdmin(admin.ModelAdmin):
    list_display = ("id", "import_row", "decision_type", "decided_by", "created_at")
    list_filter = ("decision_type", "import_row__import_job__tenant")
    search_fields = ("decided_by__username", "import_row__import_job__id")


@admin.register(ImportCommitLog)
class ImportCommitLogAdmin(admin.ModelAdmin):
    list_display = ("id", "import_job", "import_row", "entity_type", "entity_id", "action", "created_at")
    list_filter = ("entity_type", "action", "import_job__tenant")
    search_fields = ("import_job__id", "entity_id")


@admin.register(ExportJob)
class ExportJobAdmin(admin.ModelAdmin):
    list_display = ("id", "tenant", "export_type", "format", "status", "created_by", "created_at")
    list_filter = ("tenant", "export_type", "format", "status")
    search_fields = ("created_by__username",)
