from rest_framework import serializers
from .models import Tenant, Organization, Person, OrganizationPerson


class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ["id", "name", "slug", "created_at"]


class OrganizationSerializer(serializers.ModelSerializer):
    active_people = serializers.SerializerMethodField()

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
            "is_published",
            "publish_phone",
            "created_at",
            "updated_at",
            "active_people",
        ]

    def get_active_people(self, obj):
        qs = (
            obj.org_people
            .filter(status="ACTIVE")
            .select_related("person")
            .order_by("person__full_name")
        )
        return OrganizationPersonNestedSerializer(qs, many=True).data



from .models import Tenant, Organization, Person, OrganizationPerson, PersonContact


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
        fields = ["id", "full_name", "municipality", "public_contacts"]

    def get_public_contacts(self, obj):
        qs = obj.contacts.filter(is_public=True).order_by("-is_primary", "type", "value")
        return PublicPersonContactSerializer(qs, many=True).data


class PersonSerializer(serializers.ModelSerializer):
    contacts = PersonContactSerializer(many=True, read_only=True)

    class Meta:
        model = Person
        fields = [
            "id",
            "tenant",
            "full_name",
            "email",
            "phone",
            "municipality",
            "note",
            "created_at",
            "updated_at",
            "contacts",
        ]



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

    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "org_number",
            "email",
            "phone",
            "municipalities",
            "note",
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

    def to_representation(self, instance):
        """
        Respekter publish_phone: hvis den er False, ikke send phone i public.
        """
        data = super().to_representation(instance)
        if not instance.publish_phone:
            data["phone"] = None
        return data
