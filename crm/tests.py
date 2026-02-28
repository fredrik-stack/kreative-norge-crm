from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import Organization, OrganizationPerson, Person, PersonContact, Tenant
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
        )

        data = PersonSerializer(person).data

        self.assertIn("email", data)
        self.assertIn("phone", data)
        self.assertEqual(data["email"], "person@example.com")
        self.assertEqual(data["phone"], "+4798765432")


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
