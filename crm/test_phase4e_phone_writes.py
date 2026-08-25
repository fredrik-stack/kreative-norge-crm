from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from crm.models import Organization, Person, PersonContact, Tenant, TenantMembership


@override_settings(SECURE_SSL_REDIRECT=False)
class Phase4EPhoneWriteApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username="phase4e-editor",
            password="test-password",
        )
        self.tenant = Tenant.objects.create(name="Tenant", slug="phase4e")
        self.other_tenant = Tenant.objects.create(name="Other", slug="phase4e-other")
        TenantMembership.objects.create(
            tenant=self.tenant,
            user=self.user,
            role=TenantMembership.Role.REDIGERER,
        )
        self.client.force_authenticate(self.user)

    def organizations_url(self, organization=None):
        base = f"/api/tenants/{self.tenant.id}/organizations/"
        return f"{base}{organization.id}/" if organization else base

    def persons_url(self, person=None):
        base = f"/api/tenants/{self.tenant.id}/persons/"
        return f"{base}{person.id}/" if person else base

    def contacts_url(self, contact=None):
        base = f"/api/tenants/{self.tenant.id}/person-contacts/"
        return f"{base}{contact.id}/" if contact else base

    def test_tenant_api_exposes_nullable_default_region_read_only(self):
        response = self.client.get("/api/tenants/")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()[0]["default_phone_region"])

        response = self.client.patch(
            f"/api/tenants/{self.tenant.id}/",
            {"default_phone_region": "NO"},
            format="json",
        )
        self.assertEqual(response.status_code, 405)
        self.tenant.refresh_from_db()
        self.assertIsNone(self.tenant.default_phone_region)

    def test_organization_international_phone_ignores_region_and_hides_identity(self):
        response = self.client.post(
            self.organizations_url(),
            {"name": "International", "phone": "+46 8 505 103 00", "phone_region": "NO"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        organization = Organization.objects.get(pk=response.json()["id"])
        self.assertEqual(organization.phone, "+46 8 505 103 00")
        self.assertEqual(organization.phone_normalized, "+46850510300")
        self.assertIsNone(organization.phone_normalization_region)
        self.assertNotIn("phone_normalized", response.json())
        self.assertIsNone(response.json()["phone_region_used"])

    def test_organization_national_phone_persists_explicit_region_and_raw(self):
        response = self.client.post(
            self.organizations_url(),
            {"name": "National", "phone": "22 12 34 56", "phone_region": "NO"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        organization = Organization.objects.get(pk=response.json()["id"])
        self.assertEqual(organization.phone, "22 12 34 56")
        self.assertEqual(organization.phone_normalized, "+4722123456")
        self.assertEqual(organization.phone_normalization_region, "NO")
        self.assertEqual(response.json()["phone_region_used"], "NO")

    def test_swedish_national_phone_uses_explicit_override(self):
        response = self.client.post(
            self.organizations_url(),
            {"name": "Swedish", "phone": "08-505 103 00", "phone_region": "SE"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        organization = Organization.objects.get(pk=response.json()["id"])
        self.assertEqual(organization.phone_normalized, "+46850510300")
        self.assertEqual(organization.phone_normalization_region, "SE")

    def test_national_without_region_returns_needs_region_message(self):
        response = self.client.post(
            self.organizations_url(),
            {"name": "Missing region", "phone": "22 12 34 56"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["phone"][0],
            "Velg land/region for et nasjonalt telefonnummer.",
        )

    def test_invalid_and_extension_are_blocked_without_dependency_errors(self):
        invalid = self.client.post(
            self.organizations_url(),
            {"name": "Invalid", "phone": "123", "phone_region": "NO"},
            format="json",
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(invalid.json()["phone"][0], "Telefonnummeret er ugyldig.")

        extension = self.client.post(
            self.organizations_url(),
            {"name": "Extension", "phone": "+47 22 12 34 56 ext 9"},
            format="json",
        )
        self.assertEqual(extension.status_code, 400)
        self.assertEqual(
            extension.json()["phone"][0],
            "Telefonnummer med internnummer støttes ikke.",
        )

    def test_organization_clear_removes_identity_without_publication_change(self):
        organization = Organization.objects.create(
            tenant=self.tenant,
            name="Clear",
            phone="22 12 34 56",
            phone_normalized="+4722123456",
            phone_normalization_region="NO",
            is_published=True,
            publish_phone=True,
        )
        response = self.client.patch(
            self.organizations_url(organization),
            {"phone": None, "phone_region": None},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        organization.refresh_from_db()
        self.assertIsNone(organization.phone)
        self.assertIsNone(organization.phone_normalized)
        self.assertIsNone(organization.phone_normalization_region)
        self.assertTrue(organization.is_published)
        self.assertTrue(organization.publish_phone)

    def test_unrelated_organization_patch_does_not_backfill_legacy_phone(self):
        organization = Organization.objects.create(
            tenant=self.tenant,
            name="Legacy",
            phone="22 12 34 56",
        )
        response = self.client.patch(
            self.organizations_url(organization),
            {"name": "Legacy renamed", "phone": "22 12 34 56", "phone_region": "NO"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        organization.refresh_from_db()
        self.assertIsNone(organization.phone_normalized)
        self.assertIsNone(organization.phone_normalization_region)

    def test_person_phone_write_syncs_primary_contact_identity_and_flags(self):
        person = Person.objects.create(
            tenant=self.tenant,
            full_name="Person",
            phone="+47 900 00 000",
        )
        contact = PersonContact.objects.create(
            tenant=self.tenant,
            person=person,
            type="PHONE",
            value="+47 900 00 000",
            is_primary=True,
            is_public=True,
        )
        response = self.client.patch(
            self.persons_url(person),
            {"phone": "08-505 103 00", "phone_region": "SE"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        person.refresh_from_db()
        contact.refresh_from_db()
        self.assertEqual(person.phone, "08-505 103 00")
        self.assertEqual(contact.value, "08-505 103 00")
        self.assertEqual(contact.normalized_value, "+46850510300")
        self.assertEqual(contact.normalization_region, "SE")
        self.assertTrue(contact.is_primary)
        self.assertTrue(contact.is_public)
        self.assertNotIn("normalized_value", response.json()["contacts"][0])

    def test_person_clear_removes_primary_phone_contact_only(self):
        person = Person.objects.create(
            tenant=self.tenant,
            full_name="Clear person",
            phone="+4790000000",
        )
        primary = PersonContact.objects.create(
            tenant=self.tenant,
            person=person,
            type="PHONE",
            value="+4790000000",
            normalized_value="+4790000000",
            is_primary=True,
        )
        secondary = PersonContact.objects.create(
            tenant=self.tenant,
            person=person,
            type="PHONE",
            value="+4791111111",
            normalized_value="+4791111111",
        )
        response = self.client.patch(
            self.persons_url(person),
            {"phone": None, "phone_region": None},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        person.refresh_from_db()
        self.assertIsNone(person.phone)
        self.assertFalse(PersonContact.objects.filter(pk=primary.pk).exists())
        self.assertTrue(PersonContact.objects.filter(pk=secondary.pk).exists())

    def test_person_primary_phone_rejects_duplicate_secondary_identity_atomically(self):
        person = Person.objects.create(
            tenant=self.tenant,
            full_name="Atomic person",
            phone="+4790000000",
        )
        primary = PersonContact.objects.create(
            tenant=self.tenant,
            person=person,
            type="PHONE",
            value="+4790000000",
            normalized_value="+4790000000",
            is_primary=True,
        )
        PersonContact.objects.create(
            tenant=self.tenant,
            person=person,
            type="PHONE",
            value="+4791111111",
            normalized_value="+4791111111",
        )
        response = self.client.patch(
            self.persons_url(person),
            {"phone": "+47 911 11 111"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        person.refresh_from_db()
        primary.refresh_from_db()
        self.assertEqual(person.phone, "+4790000000")
        self.assertEqual(primary.normalized_value, "+4790000000")

    def test_unrelated_person_patch_does_not_backfill_primary_contact(self):
        person = Person.objects.create(
            tenant=self.tenant,
            full_name="Legacy person",
            phone="22 12 34 56",
        )
        contact = PersonContact.objects.create(
            tenant=self.tenant,
            person=person,
            type="PHONE",
            value="22 12 34 56",
            is_primary=True,
        )
        response = self.client.patch(
            self.persons_url(person),
            {"title": "New title", "phone": "22 12 34 56", "phone_region": "NO"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        contact.refresh_from_db()
        self.assertIsNone(contact.normalized_value)
        self.assertIsNone(contact.normalization_region)

    def test_phone_contact_write_normalizes_and_preserves_status(self):
        person = Person.objects.create(tenant=self.tenant, full_name="Contact person")
        response = self.client.post(
            self.contacts_url(),
            {
                "person": person.id,
                "type": "PHONE",
                "value": "22 12 34 56",
                "phone_region": "NO",
                "is_primary": True,
                "is_public": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        contact = PersonContact.objects.get(pk=response.json()["id"])
        self.assertEqual(contact.normalized_value, "+4722123456")
        self.assertEqual(contact.normalization_region, "NO")
        self.assertTrue(contact.is_primary)
        self.assertTrue(contact.is_public)
        self.assertEqual(response.json()["phone_region_used"], "NO")
        self.assertNotIn("normalized_value", response.json())

    def test_phone_contact_rejects_cross_tenant_person_before_write(self):
        other_person = Person.objects.create(
            tenant=self.other_tenant,
            full_name="Other person",
        )
        response = self.client.post(
            self.contacts_url(),
            {
                "person": other_person.id,
                "type": "PHONE",
                "value": "+4790000000",
                "is_primary": False,
                "is_public": False,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(PersonContact.objects.filter(person=other_person).exists())

    def test_phone_contact_duplicate_identity_is_a_controlled_api_error(self):
        person = Person.objects.create(tenant=self.tenant, full_name="Duplicate")
        PersonContact.objects.create(
            tenant=self.tenant,
            person=person,
            type="PHONE",
            value="+47 900 00 000",
            normalized_value="+4790000000",
        )
        response = self.client.post(
            self.contacts_url(),
            {
                "person": person.id,
                "type": "PHONE",
                "value": "900 00 000",
                "phone_region": "NO",
                "is_primary": False,
                "is_public": False,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["value"][0],
            "Telefonnummeret finnes allerede på denne personen.",
        )
