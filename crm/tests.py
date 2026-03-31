from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from unittest.mock import patch
from rest_framework.test import APIClient

from .models import (
    Organization,
    OrganizationPerson,
    Person,
    PersonContact,
    Tag,
    Category,
    Subcategory,
    Tenant,
)
from .services.open_graph import ImageCandidate, choose_best_thumbnail, fallback_preview_image
from .serializers import PersonSerializer


@override_settings(SECURE_SSL_REDIRECT=False)
class AuthApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username="editor-auth",
            password="secret123",
        )

    def test_csrf_endpoint_returns_token_and_cookie(self):
        response = self.client.get("/api/auth/csrf/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("csrfToken", response.json())
        self.assertTrue(response.json()["csrfToken"])
        self.assertIn("csrftoken", response.cookies)

    def test_session_endpoint_returns_unauthenticated_when_logged_out(self):
        response = self.client.get("/api/auth/session/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"authenticated": False, "user": None})

    def test_login_requires_username_and_password(self):
        response = self.client.post("/api/auth/login/", {"username": ""}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("non_field_errors", response.json())

    def test_login_rejects_invalid_credentials(self):
        response = self.client.post(
            "/api/auth/login/",
            {"username": "editor-auth", "password": "wrong"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("non_field_errors", response.json())

    def test_login_creates_session_and_session_endpoint_reflects_authentication(self):
        login_response = self.client.post(
            "/api/auth/login/",
            {"username": "editor-auth", "password": "secret123"},
            format="json",
        )
        self.assertEqual(login_response.status_code, 200, login_response.content)
        self.assertTrue(login_response.json()["authenticated"])
        self.assertEqual(login_response.json()["user"]["username"], "editor-auth")

        session_response = self.client.get("/api/auth/session/")
        self.assertEqual(session_response.status_code, 200)
        self.assertEqual(session_response.json()["authenticated"], True)
        self.assertEqual(session_response.json()["user"]["username"], "editor-auth")

    def test_logout_requires_authentication(self):
        response = self.client.post("/api/auth/logout/", {}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_logout_clears_session(self):
        self.client.force_login(self.user)

        response = self.client.post("/api/auth/logout/", {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"authenticated": False, "user": None})

        session_response = self.client.get("/api/auth/session/")
        self.assertEqual(session_response.status_code, 200)
        self.assertEqual(session_response.json(), {"authenticated": False, "user": None})


@override_settings(SECURE_SSL_REDIRECT=False)
class AuthenticatedAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username="editor",
            password="secret123",
        )
        self.client.force_login(self.user)


class PersonContactViewSetTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Tenant A", slug="tenant-a")
        self.other_tenant = Tenant.objects.create(name="Tenant B", slug="tenant-b")

        self.person_a = Person.objects.create(
            tenant=self.tenant,
            full_name="Alice Example",
            email="alice@example.com",
            phone="47123456",
            municipality="Oslo",
        )
        self.person_b = Person.objects.create(
            tenant=self.tenant,
            full_name="Bob Example",
            email="bob@example.com",
            phone="47999999",
            municipality="Bergen",
        )
        self.person_other_tenant = Person.objects.create(
            tenant=self.other_tenant,
            full_name="Other Tenant Person",
        )

        self.contact_a = PersonContact.objects.create(
            tenant=self.tenant,
            person=self.person_a,
            type="EMAIL",
            value="alice.public@example.com",
            is_primary=True,
            is_public=True,
        )
        self.contact_b = PersonContact.objects.create(
            tenant=self.tenant,
            person=self.person_b,
            type="PHONE",
            value="+4740000000",
        )
        self.contact_other_tenant = PersonContact.objects.create(
            tenant=self.other_tenant,
            person=self.person_other_tenant,
            type="EMAIL",
            value="hidden@example.com",
        )
        self.primary_phone_for_person_a = PersonContact.objects.create(
            tenant=self.tenant,
            person=self.person_a,
            type="PHONE",
            value="+4742222222",
            is_primary=True,
        )

    def tenant_contacts_url(self, tenant_id: int | None = None) -> str:
        return f"/api/tenants/{tenant_id or self.tenant.id}/person-contacts/"

    def test_list_is_scoped_to_tenant(self):
        response = self.client.get(self.tenant_contacts_url())
        self.assertEqual(response.status_code, 200)

        ids = {item["id"] for item in response.json()}
        self.assertIn(self.contact_a.id, ids)
        self.assertIn(self.contact_b.id, ids)
        self.assertNotIn(self.contact_other_tenant.id, ids)

    def test_list_supports_person_query_filter(self):
        response = self.client.get(self.tenant_contacts_url(), {"person": self.person_a.id})
        self.assertEqual(response.status_code, 200)

        payload = response.json()
        self.assertEqual(len(payload), 2)
        self.assertTrue(all(item["person"] == self.person_a.id for item in payload))

    def test_create_sets_tenant_from_route(self):
        response = self.client.post(
            self.tenant_contacts_url(),
            {
                "person": self.person_a.id,
                "type": "PHONE",
                "value": "+4741111111",
                "is_primary": False,
                "is_public": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)

        created = PersonContact.objects.get(id=response.json()["id"])
        self.assertEqual(created.tenant_id, self.tenant.id)
        self.assertEqual(created.person_id, self.person_a.id)
        self.assertEqual(created.type, "PHONE")

    def test_update_contact(self):
        response = self.client.patch(
            f"{self.tenant_contacts_url()}{self.contact_b.id}/",
            {"is_primary": True, "is_public": True},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)

        self.contact_b.refresh_from_db()
        self.assertTrue(self.contact_b.is_primary)
        self.assertTrue(self.contact_b.is_public)

    def test_rejects_contact_person_from_other_tenant(self):
        response = self.client.post(
            self.tenant_contacts_url(),
            {
                "person": self.person_other_tenant.id,
                "type": "EMAIL",
                "value": "x@example.com",
                "is_primary": False,
                "is_public": False,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("person", response.json())

    def test_rejects_second_primary_contact_for_same_person_and_type(self):
        response = self.client.post(
            self.tenant_contacts_url(),
            {
                "person": self.person_a.id,
                "type": "PHONE",
                "value": "+4743333333",
                "is_primary": True,
                "is_public": False,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("is_primary", response.json())

    def test_rejects_updating_contact_to_duplicate_primary(self):
        secondary = PersonContact.objects.create(
            tenant=self.tenant,
            person=self.person_a,
            type="PHONE",
            value="+4744444444",
            is_primary=False,
        )
        response = self.client.patch(
            f"{self.tenant_contacts_url()}{secondary.id}/",
            {"is_primary": True},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("is_primary", response.json())

    def test_delete_contact(self):
        response = self.client.delete(f"{self.tenant_contacts_url()}{self.contact_b.id}/")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(PersonContact.objects.filter(id=self.contact_b.id).exists())

    def test_requires_authentication(self):
        unauth_client = APIClient()
        response = unauth_client.get(self.tenant_contacts_url())
        self.assertEqual(response.status_code, 403)


@override_settings(SECURE_SSL_REDIRECT=False)
class PersonSerializerTests(TestCase):
    def test_includes_email_and_phone_fields(self):
        tenant = Tenant.objects.create(name="Tenant", slug="tenant")
        person = Person.objects.create(
            tenant=tenant,
            full_name="Person Example",
            email="person@example.com",
            phone="+4798765432",
            municipality="Trondheim",
            website_url="https://example.com",
            instagram_url="https://instagram.com/personexample",
            tiktok_url="https://tiktok.com/@personexample",
            linkedin_url="https://linkedin.com/in/personexample",
            facebook_url="https://facebook.com/personexample",
            youtube_url="https://youtube.com/@personexample",
        )

        data = PersonSerializer(person).data

        self.assertIn("email", data)
        self.assertIn("phone", data)
        self.assertIn("website_url", data)
        self.assertIn("instagram_url", data)
        self.assertIn("tiktok_url", data)
        self.assertIn("linkedin_url", data)
        self.assertIn("facebook_url", data)
        self.assertIn("youtube_url", data)
        self.assertEqual(data["email"], "person@example.com")
        self.assertEqual(data["phone"], "+4798765432")
        self.assertEqual(data["website_url"], "https://example.com")
        self.assertEqual(data["instagram_url"], "https://instagram.com/personexample")
        self.assertEqual(data["tiktok_url"], "https://tiktok.com/@personexample")
        self.assertEqual(data["linkedin_url"], "https://linkedin.com/in/personexample")
        self.assertEqual(data["facebook_url"], "https://facebook.com/personexample")
        self.assertEqual(data["youtube_url"], "https://youtube.com/@personexample")


class TagModelAndApiTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Tag Tenant", slug="tag-tenant")
        self.other_tenant = Tenant.objects.create(name="Other Tag Tenant", slug="other-tag-tenant")
        self.primary_tag = Tag.objects.create(tenant=self.tenant, name="Scenekunst")
        self.other_tag = Tag.objects.create(tenant=self.other_tenant, name="Film")

    def tenant_tags_url(self, tenant_id: int | None = None) -> str:
        return f"/api/tenants/{tenant_id or self.tenant.id}/tags/"

    def test_generates_slug_on_create(self):
        self.assertEqual(self.primary_tag.slug, "scenekunst")

    def test_list_is_scoped_to_tenant(self):
        response = self.client.get(self.tenant_tags_url())
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["name"], "Scenekunst")

    def test_create_sets_tenant_from_route(self):
        response = self.client.post(
            self.tenant_tags_url(),
            {"name": "Musikk"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        created = Tag.objects.get(id=response.json()["id"])
        self.assertEqual(created.tenant_id, self.tenant.id)
        self.assertEqual(created.slug, "musikk")

    def test_rejects_duplicate_name_in_same_tenant(self):
        response = self.client.post(
            self.tenant_tags_url(),
            {"name": "Scenekunst"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_person_serializer_includes_tags(self):
        person = Person.objects.create(tenant=self.tenant, full_name="Tag Person")
        person.tags.add(self.primary_tag)

        data = PersonSerializer(person).data

        self.assertEqual(len(data["tags"]), 1)
        self.assertEqual(data["tags"][0]["name"], "Scenekunst")


class CategoryAndSubcategoryTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.category = Category.objects.create(name="Testkategori")
        self.subcategory = Subcategory.objects.create(category=self.category, name="Testunderkategori")
        self.other_subcategory = Subcategory.objects.create(category=self.category, name="Annen underkategori")
        self.tenant = Tenant.objects.create(name="Category Tenant", slug="category-tenant")

    def test_category_slug_is_generated(self):
        self.assertEqual(self.category.slug, "testkategori")

    def test_subcategory_slug_is_generated(self):
        self.assertEqual(self.subcategory.slug, "testunderkategori")

    def test_seeded_categories_are_available(self):
        self.assertTrue(Category.objects.filter(name="Musikk").exists())
        self.assertTrue(Subcategory.objects.filter(name="Artister & Band").exists())
        self.assertTrue(Subcategory.objects.filter(name="Filmlyd").exists())

    def test_categories_endpoint_requires_authentication(self):
        unauth_client = APIClient()
        response = unauth_client.get("/api/categories/")
        self.assertEqual(response.status_code, 403)

    def test_categories_endpoint_lists_categories(self):
        response = self.client.get("/api/categories/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(any(item["name"] == "Testkategori" for item in payload))

    def test_subcategories_endpoint_can_filter_by_category(self):
        response = self.client.get("/api/subcategories/", {"category": self.category.id})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 2)
        self.assertTrue(all(item["category"]["id"] == self.category.id for item in payload))

    def test_person_serializer_includes_subcategories(self):
        person = Person.objects.create(tenant=self.tenant, full_name="Kategori Person")
        person.subcategories.add(self.subcategory)

        data = PersonSerializer(person).data

        self.assertEqual(len(data["subcategories"]), 1)
        self.assertEqual(data["subcategories"][0]["name"], "Testunderkategori")
        self.assertEqual(data["subcategories"][0]["category"]["name"], "Testkategori")


class OrganizationPreviewRefreshTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Preview Tenant", slug="preview-tenant")
        self.organization = Organization.objects.create(
            tenant=self.tenant,
            name="Preview Org",
            website_url="https://example.com",
        )

    def test_refresh_preview_endpoint_updates_open_graph_fields(self):
        with patch("crm.views.refresh_organization_open_graph") as refresh_mock:
            refresh_mock.side_effect = self._fake_refresh
            response = self.client.post(
                f"/api/tenants/{self.tenant.id}/organizations/{self.organization.id}/refresh-preview/",
                {},
                format="json",
            )

        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        self.assertEqual(payload["og_title"], "Preview Org OG")
        self.assertEqual(payload["og_description"], "Beskrivelse fra Open Graph")
        self.assertEqual(payload["og_image_url"], "https://cdn.example.com/preview.jpg")
        self.assertEqual(payload["auto_thumbnail_url"], "https://cdn.example.com/thumbnail.jpg")
        self.assertEqual(payload["primary_link"], "https://example.com")
        self.assertEqual(payload["primary_link_field"], "website_url")
        refresh_mock.assert_called_once()

    def _fake_refresh(self, organization, force=False):
        organization.og_title = "Preview Org OG"
        organization.og_description = "Beskrivelse fra Open Graph"
        organization.og_image_url = "https://cdn.example.com/preview.jpg"
        organization.auto_thumbnail_url = "https://cdn.example.com/thumbnail.jpg"
        organization.og_last_fetched_at = organization.updated_at
        organization.save(
            update_fields=["og_title", "og_description", "og_image_url", "auto_thumbnail_url", "og_last_fetched_at"]
        )


class TenantScopedCreateTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Scoped Tenant", slug="scoped-tenant")

    def test_can_create_organization_without_tenant_in_payload(self):
        response = self.client.post(
            f"/api/tenants/{self.tenant.id}/organizations/",
            {
                "name": "Ny organisasjon",
                "org_number": "123456789",
                "municipalities": "Oslo",
                "tag_ids": [],
                "category_ids": [],
                "subcategory_ids": [],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.content)
        created = Organization.objects.get(id=response.json()["id"])
        self.assertEqual(created.tenant_id, self.tenant.id)

    def test_can_create_person_without_tenant_in_payload(self):
        response = self.client.post(
            f"/api/tenants/{self.tenant.id}/persons/",
            {
                "full_name": "Ny kontaktperson",
                "municipality": "Oslo",
                "tag_ids": [],
                "category_ids": [],
                "subcategory_ids": [],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.content)
        created = Person.objects.get(id=response.json()["id"])
        self.assertEqual(created.tenant_id, self.tenant.id)

    def test_can_create_organization_with_category_only(self):
        category = Category.objects.create(name="Kun kategori")
        response = self.client.post(
            f"/api/tenants/{self.tenant.id}/organizations/",
            {
                "name": "Kategori uten underkategori",
                "category_ids": [category.id],
                "subcategory_ids": [],
                "tag_ids": [],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.content)
        created = Organization.objects.get(id=response.json()["id"])
        self.assertEqual(list(created.categories.values_list("name", flat=True)), ["Kun kategori"])
        self.assertEqual(created.subcategories.count(), 0)

    def test_can_create_person_with_category_only(self):
        category = Category.objects.create(name="Kun personkategori")
        response = self.client.post(
            f"/api/tenants/{self.tenant.id}/persons/",
            {
                "full_name": "Kategori-person",
                "category_ids": [category.id],
                "subcategory_ids": [],
                "tag_ids": [],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.content)
        created = Person.objects.get(id=response.json()["id"])
        self.assertEqual(list(created.categories.values_list("name", flat=True)), ["Kun personkategori"])
        self.assertEqual(created.subcategories.count(), 0)


@override_settings(SECURE_SSL_REDIRECT=False)
class PublicActorSiteTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Publik kategori")
        self.subcategory = Subcategory.objects.create(category=self.category, name="Publik underkategori")
        self.tag = Tag.objects.create(tenant=Tenant.objects.create(name="Public Tenant", slug="public-tenant"), name="Etablert")
        self.organization = Organization.objects.create(
            tenant=self.tag.tenant,
            name="Nordlyd",
            org_number="123456789",
            municipalities="Oslo",
            note="Publisert aktør",
            is_published=True,
            website_url="https://example.com",
        )
        self.organization.tags.add(self.tag)
        self.organization.categories.add(self.category)
        self.organization.subcategories.add(self.subcategory)
        self.person = Person.objects.create(
            tenant=self.tag.tenant,
            full_name="Ada Artist",
            email="ada@example.com",
            phone="+4712345678",
            municipality="Oslo",
        )
        self.link = OrganizationPerson.objects.create(
            tenant=self.tag.tenant,
            organization=self.organization,
            person=self.person,
            status="ACTIVE",
            publish_person=True,
        )

        self.hidden_organization = Organization.objects.create(
            tenant=self.tag.tenant,
            name="Skjult aktør",
            org_number="987654321",
            is_published=False,
        )

    def test_public_actor_list_only_shows_published_actors(self):
        response = self.client.get("/public/actors/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nordlyd")
        self.assertNotContains(response, "Skjult aktør")

    def test_public_actor_list_can_filter_by_tag_and_category(self):
        response = self.client.get("/public/actors/", {"tag": self.tag.slug, "category": self.category.slug})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nordlyd")

    def test_public_actor_list_context_uses_expected_category_and_subcategory_order(self):
        extra_category = Category.objects.create(name="Ekstra kategori")
        Subcategory.objects.create(category=extra_category, name="Ekstra underkategori")
        response = self.client.get("/public/actors/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [category["name"] for category in response.context["available_categories"][:6]],
            ["Musikk", "Film", "Kunst & Design", "Scenekunst", "Kreativ teknologi", "Litteratur"],
        )
        self.assertEqual(
            [subcategory["name"] for subcategory in response.context["available_subcategories"][:15]],
            [
                "Artister & Band",
                "Konsertarrangører",
                "Musikere",
                "Musikkbransjen",
                "Produsent",
                "Regi & Manus",
                "Foto/ Lys",
                "Filmlyd",
                "Produksjon",
                "Arenaer",
                "Visuell kunst",
                "Grafisk design",
                "Klesdesign",
                "Teater",
                "Dans",
            ],
        )

    def test_public_actor_detail_shows_tags_and_subcategories(self):
        response = self.client.get(f"/public/actors/{self.organization.org_number}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Etablert")
        self.assertContains(response, "PUBLIK KATEGORI")
        self.assertContains(response, "Publik underkategori")

    def test_public_actor_detail_falls_back_to_person_email_but_not_phone(self):
        response = self.client.get(f"/public/actors/{self.organization.org_number}/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ada Artist")
        self.assertContains(response, "ada@example.com")
        self.assertNotContains(response, "+4712345678")

    def test_public_actor_templates_ignore_favicon_fallback_urls(self):
        self.organization.og_image_url = fallback_preview_image(self.organization.website_url)
        self.organization.save(update_fields=["og_image_url"])

        list_response = self.client.get("/public/actors/")
        detail_response = self.client.get(f"/public/actors/{self.organization.org_number}/")

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(detail_response.status_code, 200)
        self.assertNotContains(list_response, "google.com/s2/favicons")
        self.assertNotContains(detail_response, "google.com/s2/favicons")

    def test_manual_thumbnail_override_wins_for_public_image(self):
        self.organization.thumbnail_image_url = "https://cdn.example.com/manual-thumb.jpg"
        self.organization.auto_thumbnail_url = "https://cdn.example.com/auto-thumb.jpg"
        self.organization.og_image_url = "https://cdn.example.com/og.jpg"
        self.organization.save(update_fields=["thumbnail_image_url", "auto_thumbnail_url", "og_image_url"])

        response = self.client.get("/public/actors/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "https://cdn.example.com/manual-thumb.jpg")


class ThumbnailSelectionTests(TestCase):
    def test_choose_best_thumbnail_prefers_large_non_logo_candidate(self):
        chosen = choose_best_thumbnail(
            "https://example.com/about",
            [
                ImageCandidate(url="/assets/logo.png", source="img", width=320, height=120, alt="Logo"),
                ImageCandidate(url="/media/portrait.jpg", source="img", width=1200, height=1200, alt="Artist"),
            ],
        )

        self.assertEqual(chosen, "https://example.com/media/portrait.jpg")


class OrganizationPersonViewSetValidationTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.tenant = Tenant.objects.create(name="Tenant A", slug="tenant-a-links")
        self.other_tenant = Tenant.objects.create(name="Tenant B", slug="tenant-b-links")

        self.organization = Organization.objects.create(tenant=self.tenant, name="Org A")
        self.person = Person.objects.create(tenant=self.tenant, full_name="Person A")

        self.other_organization = Organization.objects.create(
            tenant=self.other_tenant,
            name="Org B",
        )
        self.other_person = Person.objects.create(
            tenant=self.other_tenant,
            full_name="Person B",
        )

    def tenant_links_url(self, tenant_id: int | None = None) -> str:
        return f"/api/tenants/{tenant_id or self.tenant.id}/organization-people/"

    def test_rejects_create_when_person_belongs_to_other_tenant(self):
        response = self.client.post(
            self.tenant_links_url(),
            {
                "organization": self.organization.id,
                "person": self.other_person.id,
                "status": "ACTIVE",
                "publish_person": False,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("person", response.json())

    def test_rejects_create_when_organization_belongs_to_other_tenant(self):
        response = self.client.post(
            self.tenant_links_url(),
            {
                "organization": self.other_organization.id,
                "person": self.person.id,
                "status": "ACTIVE",
                "publish_person": False,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("organization", response.json())

    def test_rejects_update_when_switching_person_to_other_tenant(self):
        link = OrganizationPerson.objects.create(
            tenant=self.tenant,
            organization=self.organization,
            person=self.person,
        )
        response = self.client.patch(
            f"{self.tenant_links_url()}{link.id}/",
            {"person": self.other_person.id},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("person", response.json())
