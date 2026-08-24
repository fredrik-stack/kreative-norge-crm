import logging

from django.conf import settings
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from .models import Organization, OrganizationPerson, PersonContact, Tag, Category, Subcategory
from .services.images.projection import project_public_image


projection_logger = logging.getLogger("crm.public_image_projection")


class PublicTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name", "slug"]


class PublicCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug"]


class PublicSubcategorySerializer(serializers.ModelSerializer):
    category = PublicCategorySerializer(read_only=True)

    class Meta:
        model = Subcategory
        fields = ["id", "name", "slug", "category"]


class PublicPersonContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = PersonContact
        fields = ("type", "value")


class PublicPersonSerializer(serializers.Serializer):
    full_name = serializers.CharField()
    title = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    municipality = serializers.CharField(allow_blank=True, required=False)
    public_contacts = PublicPersonContactSerializer(many=True)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not data.get("title"):
            data.pop("title", None)
        return data


class PublicImageVariantSerializer(serializers.Serializer):
    url = serializers.URLField()
    width = serializers.IntegerField(min_value=1)
    height = serializers.IntegerField(min_value=1)


class PublicImageSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=("asset", "system_fallback"))
    alt_text = serializers.CharField(allow_blank=True)
    credit = serializers.CharField(allow_null=True)
    square = PublicImageVariantSerializer()
    landscape = PublicImageVariantSerializer()
    share = PublicImageVariantSerializer()


class PublicActorSerializer(serializers.ModelSerializer):
    # people blir bygget fra OrganizationPerson + Person + PersonContact
    people = serializers.SerializerMethodField()

    # email/phone: vi returnerer felt basert på publish toggles
    email = serializers.SerializerMethodField()
    phone = serializers.SerializerMethodField()

    # municipality / municipalities: vi støtter begge dersom du har ett av dem
    municipality = serializers.SerializerMethodField()
    municipalities = serializers.SerializerMethodField()
    primary_link = serializers.SerializerMethodField()
    primary_link_field = serializers.SerializerMethodField()
    preview_image_url = serializers.SerializerMethodField()
    thumbnail_image_url = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    tags = PublicTagSerializer(many=True, read_only=True)
    categories = PublicCategorySerializer(many=True, read_only=True)
    subcategories = PublicSubcategorySerializer(many=True, read_only=True)

    class Meta:
        model = Organization
        fields = (
            "name",
            "org_number",
            "municipality",
            "municipalities",
            "email",
            "phone",
            "website_url",
            "facebook_url",
            "instagram_url",
            "tiktok_url",
            "linkedin_url",
            "youtube_url",
            "primary_link",
            "primary_link_field",
            "thumbnail_image_url",
            "preview_image_url",
            "image",
            "tags",
            "categories",
            "subcategories",
            "people",
        )

    def get_fields(self):
        fields = super().get_fields()
        if not settings.PUBLIC_IMAGE_API_SCHEMA_ENABLED:
            fields.pop("image", None)
        return fields

    def _projection_result(self, obj):
        cache = getattr(self, "_public_image_projection_cache", None)
        if cache is None:
            cache = self._public_image_projection_cache = {}
        if obj.pk not in cache:
            cache[obj.pk] = project_public_image(obj)
        return cache[obj.pk]

    @extend_schema_field(PublicImageSerializer)
    def get_image(self, obj):
        return self._projection_result(obj).projection.as_dict()

    def get_email(self, obj):
        # antar at Organization har et email-felt, evt. returner None
        return getattr(obj, "email", None)

    def get_phone(self, obj):
        # bare hvis publish_phone=True
        if getattr(obj, "publish_phone", False):
            return getattr(obj, "phone", None)
        return None

    def get_municipality(self, obj):
        return getattr(obj, "municipality", None)

    def get_municipalities(self, obj):
        return getattr(obj, "municipalities", None)

    def get_primary_link(self, obj):
        return obj.get_primary_link()

    def get_primary_link_field(self, obj):
        return obj.get_primary_link_field()

    @extend_schema_field(
        {
            "type": "string",
            "format": "uri",
            "nullable": True,
            "deprecated": True,
        }
    )
    def get_preview_image_url(self, obj):
        if settings.PUBLIC_IMAGE_API_SCHEMA_ENABLED:
            return self._projection_result(obj).projection.square.url
        return obj.get_preview_image_url()

    @extend_schema_field(
        {
            "type": "string",
            "format": "uri",
            "nullable": True,
            "deprecated": True,
        }
    )
    def get_thumbnail_image_url(self, obj):
        if settings.PUBLIC_IMAGE_API_SCHEMA_ENABLED:
            return self._projection_result(obj).projection.square.url
        return obj.get_public_image_url()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        view = self.context.get("view")
        if (
            settings.PUBLIC_IMAGE_PROJECTION_ENABLED
            and not settings.PUBLIC_IMAGE_API_SCHEMA_ENABLED
            and getattr(view, "action", None) == "retrieve"
        ):
            result = self._projection_result(instance)
            projected_square = result.projection.square.url
            projection_logger.info(
                "event=public_image_projection_shadow organization_id=%s kind=%s "
                "reason=%s thumbnail_equal=%s preview_equal=%s authorize_count=%s",
                instance.pk,
                result.projection.kind,
                result.reason,
                data.get("thumbnail_image_url") == projected_square,
                data.get("preview_image_url") == projected_square,
                result.authorize_count,
            )
        return data

    @extend_schema_field(PublicPersonSerializer(many=True))
    def get_people(self, obj):
        links = getattr(obj, "_public_people_links", None)
        if links is None:
            links = (
                OrganizationPerson.objects.select_related("person")
                .filter(
                    organization=obj,
                    status="ACTIVE",
                    publish_person=True,
                )
                .order_by("person__full_name", "person_id")
            )

        people_payload = []
        for op in links:
            person = op.person
            contacts = getattr(person, "_public_contacts", None)
            if contacts is None:
                contacts = PersonContact.objects.filter(
                    person=person, is_public=True
                ).order_by("type", "value")

            people_payload.append(
                {
                    "full_name": getattr(person, "full_name", str(person)),
                    "title": getattr(person, "title", None),
                    "municipality": getattr(person, "municipality", None),
                    "public_contacts": contacts,
                }
            )

        return PublicPersonSerializer(people_payload, many=True).data
