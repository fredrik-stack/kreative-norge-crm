from rest_framework import serializers

from .models import Organization, OrganizationPerson, PersonContact, Tag, Category, Subcategory


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
    municipality = serializers.CharField(allow_blank=True, required=False)
    public_contacts = PublicPersonContactSerializer(many=True)


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
    tags = PublicTagSerializer(many=True, read_only=True)
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
            "tags",
            "subcategories",
            "people",
        )

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

    def get_preview_image_url(self, obj):
        return obj.get_preview_image_url()

    def get_thumbnail_image_url(self, obj):
        return obj.get_public_image_url()

    def get_people(self, obj):
        qs = (
            OrganizationPerson.objects.select_related("person")
            .filter(
                organization=obj,
                status="ACTIVE",
                publish_person=True,
            )
            .order_by("person__full_name", "person_id")
        )

        people_payload = []
        for op in qs:
            person = op.person

            contacts_qs = (
                PersonContact.objects.filter(person=person, is_public=True)
                .order_by("type", "value")
            )

            # Hvis du ikke vil vise personer uten public contacts, uncomment:
            # if not contacts_qs.exists():
            #     continue

            people_payload.append(
                {
                    "full_name": getattr(person, "full_name", str(person)),
                    "municipality": getattr(person, "municipality", None),
                    "public_contacts": contacts_qs,
                }
            )

        return PublicPersonSerializer(people_payload, many=True).data
