from django.contrib import admin
from django.forms.models import BaseInlineFormSet

from .models import Tenant, Tag, Category, Subcategory, Organization, Person, OrganizationPerson, PersonContact


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "created_at")
    search_fields = ("name", "slug")


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
