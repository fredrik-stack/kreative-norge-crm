from types import SimpleNamespace

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from crm.models import Person, PersonContact, Tenant, TenantMembership


@override_settings(SECURE_SSL_REDIRECT=False)
class EditorSessionIdentityTests(TestCase):
    def test_login_and_session_report_name_and_actual_admin_access_independently_of_tenant_role(self):
        tenant = Tenant.objects.create(name="Testkontor", slug="testkontor")
        for index, (staff, superuser, role) in enumerate([
            (False, False, "superadmin"), (False, False, "gruppeadmin"),
            (True, False, "leser"), (True, True, "redigerer"), (False, True, "superadmin"),
        ]):
            with self.subTest(staff=staff, superuser=superuser, role=role):
                user = get_user_model().objects.create_user(
                    username=f"identity-{index}", password="test-only-password",
                    first_name="Ada" if index else "", last_name="Eksempel" if index else "",
                    is_staff=staff, is_superuser=superuser,
                )
                TenantMembership.objects.create(user=user, tenant=tenant, role=role)
                client = APIClient()
                login = client.post("/api/auth/login/", {"username": user.username, "password": "test-only-password"}, format="json")
                self.assertEqual(login.status_code, 200)
                session = client.get("/api/auth/session/")
                for response in (login, session):
                    identity = response.json()["user"]
                    self.assertEqual(identity["display_name"], "Ada Eksempel" if index else user.username)
                    self.assertEqual(identity["can_access_admin"], admin.site.has_permission(SimpleNamespace(user=user)))
                    self.assertEqual(identity["is_superuser"], superuser)
                    self.assertEqual(identity["memberships"][0]["role"], role)


@override_settings(SECURE_SSL_REDIRECT=False)
class EditorManualContactContractTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Kontaktkontor", slug="kontaktkontor", default_phone_region="NO")
        self.user = get_user_model().objects.create_user(username="kontakt-test", password="test-only")
        TenantMembership.objects.create(user=self.user, tenant=self.tenant, role="gruppeadmin")
        self.client = APIClient()
        self.client.force_login(self.user)
        self.base = f"/api/tenants/{self.tenant.id}"

    def test_existing_sequence_preserves_ids_flags_and_removes_main_contacts_without_promotion(self):
        response = self.client.post(f"{self.base}/persons/", {"full_name": "Syntetisk Kontakt", "email": "one@example.invalid", "phone": "90012345", "phone_region": "NO"}, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        person_id = response.json()["id"]
        person_url = f"{self.base}/persons/{person_id}/"
        original = {contact.type: contact.id for contact in PersonContact.objects.filter(person_id=person_id)}
        for kind, value in [("EMAIL", "two@example.invalid"), ("PHONE", "+4791234567")]:
            created = self.client.post(f"{self.base}/person-contacts/", {"person": person_id, "type": kind, "value": value, "is_primary": False, "is_public": True}, format="json")
            self.assertEqual(created.status_code, 201, created.content)
        unchanged = list(PersonContact.objects.filter(person_id=person_id).order_by("id").values("id", "value", "is_public", "is_primary", "normalized_value"))
        response = self.client.patch(person_url, {"title": "Endret tittel"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(unchanged, list(PersonContact.objects.filter(person_id=person_id).order_by("id").values("id", "value", "is_public", "is_primary", "normalized_value")))
        for kind, field in [("EMAIL", "email"), ("PHONE", "phone")]:
            response = self.client.delete(f"{self.base}/person-contacts/{original[kind]}/")
            self.assertEqual(response.status_code, 204, response.content)
            # Existing DELETE does not clear Person. The same save action must clear it.
            response = self.client.patch(person_url, {field: None}, format="json")
            self.assertEqual(response.status_code, 200, response.content)
            self.assertFalse(PersonContact.objects.filter(pk=original[kind]).exists())
            self.assertFalse(PersonContact.objects.filter(person_id=person_id, type=kind, is_primary=True).exists())
        person = Person.objects.get(pk=person_id)
        self.assertIsNone(person.email)
        self.assertIsNone(person.phone)
        remaining = PersonContact.objects.filter(person=person)
        self.assertEqual(remaining.count(), 2)
        self.assertTrue(all(contact.is_public and not contact.is_primary for contact in remaining))

    def test_editor_cannot_delete_persisted_contact(self):
        TenantMembership.objects.filter(user=self.user).update(role="redigerer")
        person = Person.objects.create(tenant=self.tenant, full_name="Behold Kontakt")
        contact = PersonContact.objects.create(tenant=self.tenant, person=person, type="EMAIL", value="keep@example.invalid")
        self.assertEqual(self.client.delete(f"{self.base}/person-contacts/{contact.id}/").status_code, 403)
        self.assertTrue(PersonContact.objects.filter(pk=contact.id).exists())
