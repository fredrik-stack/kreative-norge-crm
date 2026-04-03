from rest_framework import serializers
from .models import (
    Tenant,
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


class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ["id", "name", "slug", "created_at"]


class TagSerializer(serializers.ModelSerializer):
    def validate_name(self, value):
        tenant_id = self._get_effective_tenant_id()
        normalized = value.strip()
        if tenant_id is not None:
          qs = Tag.objects.filter(tenant_id=tenant_id, name=normalized)
          if self.instance is not None:
              qs = qs.exclude(pk=self.instance.pk)
          if qs.exists():
              raise serializers.ValidationError("Tag with this name already exists for this tenant.")
        return normalized

    def _get_effective_tenant_id(self):
        if self.instance is not None:
            return self.instance.tenant_id
        tenant = self.initial_data.get("tenant") if hasattr(self, "initial_data") else None
        if tenant:
            return int(tenant)
        view = self.context.get("view")
        if view is not None:
            tenant_id = view.kwargs.get("tenant_id")
            if tenant_id is not None:
                return int(tenant_id)
        return None

    class Meta:
        model = Tag
        fields = ["id", "tenant", "name", "slug", "created_at"]
        read_only_fields = ["tenant", "slug", "created_at"]


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "created_at"]
        read_only_fields = ["slug", "created_at"]


class SubcategorySerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source="category",
        write_only=True,
        required=False,
    )

    class Meta:
        model = Subcategory
        fields = ["id", "name", "slug", "created_at", "category", "category_id"]
        read_only_fields = ["slug", "created_at"]


class OrganizationSerializer(serializers.ModelSerializer):
    active_people = serializers.SerializerMethodField()
    primary_link = serializers.SerializerMethodField()
    primary_link_field = serializers.SerializerMethodField()
    preview_image_url = serializers.SerializerMethodField()
    tags = TagSerializer(many=True, read_only=True)
    tag_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all(),
        write_only=True,
        source="tags",
        required=False,
    )
    categories = CategorySerializer(many=True, read_only=True)
    category_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Category.objects.all(),
        write_only=True,
        source="categories",
        required=False,
    )
    subcategories = SubcategorySerializer(many=True, read_only=True)
    subcategory_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Subcategory.objects.select_related("category").all(),
        write_only=True,
        source="subcategories",
        required=False,
    )

    class Meta:
        model = Organization
        fields = [
            "id",
            "tenant",
            "name",
            "org_number",
            "email",
            "phone",
            "municipalities",
            "note",
            "description",
            "is_published",
            "publish_phone",
            "website_url",
            "facebook_url",
            "instagram_url",
            "tiktok_url",
            "linkedin_url",
            "youtube_url",
            "og_title",
            "og_description",
            "og_image_url",
            "thumbnail_image_url",
            "auto_thumbnail_url",
            "og_last_fetched_at",
            "primary_link",
            "primary_link_field",
            "preview_image_url",
            "tags",
            "tag_ids",
            "categories",
            "category_ids",
            "subcategories",
            "subcategory_ids",
            "created_at",
            "updated_at",
            "active_people",
        ]
        read_only_fields = [
            "tenant",
            "og_title",
            "og_description",
            "og_image_url",
            "auto_thumbnail_url",
            "og_last_fetched_at",
        ]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        tenant_id = self._get_effective_tenant_id()
        tags = attrs.get("tags")
        categories = attrs.get("categories")
        subcategories = attrs.get("subcategories")
        if tenant_id is not None and tags is not None:
            invalid = [tag.name for tag in tags if tag.tenant_id != tenant_id]
            if invalid:
                raise serializers.ValidationError(
                    {"tag_ids": ["All tags must belong to the same tenant as the route."]}
                )

        category_set = set(categories) if categories is not None else set(getattr(self.instance, "categories", []).all() if self.instance else [])
        subcategory_set = set(subcategories) if subcategories is not None else set(getattr(self.instance, "subcategories", []).all() if self.instance else [])

        inferred_categories = {subcategory.category for subcategory in subcategory_set}
        if category_set and inferred_categories and not inferred_categories.issubset(category_set):
            raise serializers.ValidationError(
                {"subcategory_ids": ["Selected underkategorier must belong to the selected hovedkategori."]}
            )

        if categories is not None or subcategories is not None:
            attrs["categories"] = list(category_set | inferred_categories)
        return attrs

    def _get_effective_tenant_id(self):
        if self.instance is not None:
            return self.instance.tenant_id
        tenant = self.initial_data.get("tenant") if hasattr(self, "initial_data") else None
        if tenant:
            return int(tenant)
        view = self.context.get("view")
        if view is not None:
            tenant_id = view.kwargs.get("tenant_id")
            if tenant_id is not None:
                return int(tenant_id)
        return None

    def get_active_people(self, obj):
        qs = (
            obj.org_people
            .filter(status="ACTIVE")
            .select_related("person")
            .order_by("person__full_name")
        )
        return OrganizationPersonNestedSerializer(qs, many=True).data

    def get_primary_link(self, obj):
        return obj.get_primary_link()

    def get_primary_link_field(self, obj):
        return obj.get_primary_link_field()

    def get_preview_image_url(self, obj):
        return obj.get_preview_image_url()

class PersonContactSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        attrs = super().validate(attrs)

        tenant_id = self._get_effective_tenant_id(attrs)
        person = attrs.get("person") or getattr(self.instance, "person", None)
        contact_type = attrs.get("type") or getattr(self.instance, "type", None)
        is_primary = attrs.get("is_primary")
        if is_primary is None and self.instance is not None:
            is_primary = self.instance.is_primary

        if person is not None and tenant_id is not None and person.tenant_id != tenant_id:
            raise serializers.ValidationError(
                {"person": ["Person must belong to the same tenant as the route."]}
            )

        if person is not None and contact_type and is_primary:
            qs = PersonContact.objects.filter(
                tenant_id=tenant_id or person.tenant_id,
                person=person,
                type=contact_type,
                is_primary=True,
            )
            if self.instance is not None:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {
                        "is_primary": [
                            "Only one primary contact is allowed per person and contact type."
                        ]
                    }
                )

        return attrs

    def _get_effective_tenant_id(self, attrs):
        if "tenant" in attrs and attrs["tenant"] is not None:
            return attrs["tenant"].id if hasattr(attrs["tenant"], "id") else attrs["tenant"]
        if self.instance is not None:
            return self.instance.tenant_id
        view = self.context.get("view")
        if view is not None:
            tenant_id = view.kwargs.get("tenant_id")
            if tenant_id is not None:
                return int(tenant_id)
        return None

    class Meta:
        model = PersonContact
        fields = [
            "id",
            "tenant",
            "person",
            "type",
            "value",
            "is_primary",
            "is_public",
            "created_at",
        ]
        read_only_fields = ["tenant", "created_at"]


class PublicPersonContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = PersonContact
        fields = ["id", "type", "value", "is_primary"]


class PersonForOrganizationSerializer(serializers.ModelSerializer):
    public_contacts = serializers.SerializerMethodField()

    class Meta:
        model = Person
        fields = ["id", "full_name", "title", "municipality", "public_contacts"]

    def get_public_contacts(self, obj):
        qs = obj.contacts.filter(is_public=True).order_by("-is_primary", "type", "value")
        return PublicPersonContactSerializer(qs, many=True).data


class PersonSerializer(serializers.ModelSerializer):
    contacts = PersonContactSerializer(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    tag_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all(),
        write_only=True,
        source="tags",
        required=False,
    )
    categories = CategorySerializer(many=True, read_only=True)
    category_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Category.objects.all(),
        write_only=True,
        source="categories",
        required=False,
    )
    subcategories = SubcategorySerializer(many=True, read_only=True)
    subcategory_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Subcategory.objects.select_related("category").all(),
        write_only=True,
        source="subcategories",
        required=False,
    )

    class Meta:
        model = Person
        fields = [
            "id",
            "tenant",
            "full_name",
            "title",
            "email",
            "phone",
            "website_url",
            "instagram_url",
            "tiktok_url",
            "linkedin_url",
            "facebook_url",
            "youtube_url",
            "tags",
            "tag_ids",
            "categories",
            "category_ids",
            "subcategories",
            "subcategory_ids",
            "municipality",
            "note",
            "created_at",
            "updated_at",
            "contacts",
        ]
        read_only_fields = ["tenant"]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        tenant_id = self._get_effective_tenant_id()
        tags = attrs.get("tags")
        categories = attrs.get("categories")
        subcategories = attrs.get("subcategories")
        if tenant_id is not None and tags is not None:
            invalid = [tag.name for tag in tags if tag.tenant_id != tenant_id]
            if invalid:
                raise serializers.ValidationError(
                    {"tag_ids": ["All tags must belong to the same tenant as the route."]}
                )

        category_set = set(categories) if categories is not None else set(getattr(self.instance, "categories", []).all() if self.instance else [])
        subcategory_set = set(subcategories) if subcategories is not None else set(getattr(self.instance, "subcategories", []).all() if self.instance else [])

        inferred_categories = {subcategory.category for subcategory in subcategory_set}
        if category_set and inferred_categories and not inferred_categories.issubset(category_set):
            raise serializers.ValidationError(
                {"subcategory_ids": ["Selected underkategorier must belong to the selected hovedkategori."]}
            )

        if categories is not None or subcategories is not None:
            attrs["categories"] = list(category_set | inferred_categories)
        return attrs

    def _get_effective_tenant_id(self):
        if self.instance is not None:
            return self.instance.tenant_id
        tenant = self.initial_data.get("tenant") if hasattr(self, "initial_data") else None
        if tenant:
            return int(tenant)
        view = self.context.get("view")
        if view is not None:
            tenant_id = view.kwargs.get("tenant_id")
            if tenant_id is not None:
                return int(tenant_id)
        return None


class OrganizationPersonSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        attrs = super().validate(attrs)

        tenant_id = self._get_effective_tenant_id(attrs)
        organization = attrs.get("organization") or getattr(self.instance, "organization", None)
        person = attrs.get("person") or getattr(self.instance, "person", None)

        errors = {}
        if tenant_id is not None and organization is not None and organization.tenant_id != tenant_id:
            errors["organization"] = ["Organization must belong to the same tenant as the route."]
        if tenant_id is not None and person is not None and person.tenant_id != tenant_id:
            errors["person"] = ["Person must belong to the same tenant as the route."]
        if organization is not None and person is not None and organization.tenant_id != person.tenant_id:
            errors["person"] = ["Person and organization must belong to the same tenant."]

        if errors:
            raise serializers.ValidationError(errors)
        return attrs

    def _get_effective_tenant_id(self, attrs):
        if "tenant" in attrs and attrs["tenant"] is not None:
            return attrs["tenant"].id if hasattr(attrs["tenant"], "id") else attrs["tenant"]
        if self.instance is not None:
            return self.instance.tenant_id
        view = self.context.get("view")
        if view is not None:
            tenant_id = view.kwargs.get("tenant_id")
            if tenant_id is not None:
                return int(tenant_id)
        return None

    class Meta:
        model = OrganizationPerson
        fields = [
            "id",
            "tenant",
            "organization",
            "person",
            "status",
            "publish_person",
            "created_at",
        ]
        read_only_fields = ["tenant", "created_at"]

class OrganizationPersonNestedSerializer(serializers.ModelSerializer):
    person = PersonForOrganizationSerializer(read_only=True)

    class Meta:
        model = OrganizationPerson
        fields = ["id", "status", "publish_person", "person", "created_at"]

class PublicPersonSerializer(serializers.ModelSerializer):
    public_contacts = serializers.SerializerMethodField()

    class Meta:
        model = Person
        fields = ["id", "full_name", "municipality", "public_contacts"]

    def get_public_contacts(self, obj):
        qs = obj.contacts.filter(is_public=True).order_by("-is_primary", "type", "value")
        return PublicPersonContactSerializer(qs, many=True).data


class PublicOrganizationSerializer(serializers.ModelSerializer):
    active_people = serializers.SerializerMethodField()
    primary_link = serializers.SerializerMethodField()
    primary_link_field = serializers.SerializerMethodField()
    preview_image_url = serializers.SerializerMethodField()
    tags = TagSerializer(many=True, read_only=True)
    categories = CategorySerializer(many=True, read_only=True)
    subcategories = SubcategorySerializer(many=True, read_only=True)

    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "org_number",
            "email",
            "phone",
            "municipalities",
            "description",
            "website_url",
            "facebook_url",
            "instagram_url",
            "tiktok_url",
            "linkedin_url",
            "youtube_url",
            "thumbnail_image_url",
            "auto_thumbnail_url",
            "primary_link",
            "primary_link_field",
            "preview_image_url",
            "tags",
            "categories",
            "subcategories",
            "active_people",
        ]

    def get_active_people(self, obj):
        qs = (
            obj.org_people
            .filter(status="ACTIVE", publish_person=True)
            .select_related("person")
            .order_by("person__full_name")
        )
        # Bare personer som er markert publish_person=True
        return [
            {
                "id": link.person.id,
                "full_name": link.person.full_name,
                "municipality": link.person.municipality,
                "public_contacts": PublicPersonContactSerializer(
                    link.person.contacts.filter(is_public=True).order_by("-is_primary", "type", "value"),
                    many=True
                ).data,
            }
            for link in qs
        ]

    def get_primary_link(self, obj):
        return obj.get_primary_link()

    def get_primary_link_field(self, obj):
        return obj.get_primary_link_field()

    def get_preview_image_url(self, obj):
        return obj.get_preview_image_url()

    def to_representation(self, instance):
        """
        Respekter publish_phone: hvis den er False, ikke send phone i public.
        """
        data = super().to_representation(instance)
        if not instance.publish_phone:
            data["phone"] = None
        return data


class ImportDecisionSerializer(serializers.ModelSerializer):
    decided_by = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = ImportDecision
        fields = ["id", "import_row", "decided_by", "decision_type", "payload_json", "created_at"]
        read_only_fields = ["import_row", "decided_by", "created_at"]


class ImportDecisionCreateSerializer(serializers.Serializer):
    decision_type = serializers.ChoiceField(choices=ImportDecision.DecisionType.choices)
    payload_json = serializers.JSONField(required=False, default=dict)


class ImportJobDecisionsSerializer(serializers.Serializer):
    row_id = serializers.IntegerField()
    decisions = ImportDecisionCreateSerializer(many=True)


class ImportCommitRequestSerializer(serializers.Serializer):
    skip_unresolved = serializers.BooleanField(required=False, default=False)


class ImportRowSerializer(serializers.ModelSerializer):
    decisions = ImportDecisionSerializer(many=True, read_only=True)

    class Meta:
        model = ImportRow
        fields = [
            "id",
            "import_job",
            "row_number",
            "raw_payload_json",
            "normalized_payload_json",
            "detected_entities_json",
            "match_result_json",
            "ai_suggestions_json",
            "validation_errors_json",
            "warnings_json",
            "row_status",
            "proposed_action",
            "decision_json",
            "created_at",
            "updated_at",
            "decisions",
        ]
        read_only_fields = fields


class ImportJobSerializer(serializers.ModelSerializer):
    tenant = serializers.PrimaryKeyRelatedField(read_only=True)
    created_by = serializers.PrimaryKeyRelatedField(read_only=True)
    rows_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = ImportJob
        fields = [
            "id",
            "tenant",
            "created_by",
            "source_type",
            "import_mode",
            "status",
            "filename",
            "file",
            "summary_json",
            "config_json",
            "preview_report_file",
            "error_report_file",
            "committed_at",
            "created_at",
            "updated_at",
            "rows_count",
        ]
        read_only_fields = [
            "tenant",
            "created_by",
            "status",
            "filename",
            "file",
            "summary_json",
            "config_json",
            "preview_report_file",
            "error_report_file",
            "committed_at",
            "created_at",
            "updated_at",
            "rows_count",
        ]


class ImportJobCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportJob
        fields = ["id", "source_type", "import_mode", "status", "tenant", "created_by", "created_at"]
        read_only_fields = ["id", "status", "tenant", "created_by", "created_at"]


class ImportJobUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportJob
        fields = ["file"]

    def validate_file(self, value):
        if not value:
            raise serializers.ValidationError("File is required.")
        return value


class ExportJobSerializer(serializers.ModelSerializer):
    tenant = serializers.PrimaryKeyRelatedField(read_only=True)
    created_by = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = ExportJob
        fields = [
            "id",
            "tenant",
            "created_by",
            "export_type",
            "format",
            "filters_json",
            "selected_fields_json",
            "status",
            "file",
            "summary_json",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "tenant",
            "created_by",
            "status",
            "file",
            "summary_json",
            "created_at",
            "updated_at",
        ]
