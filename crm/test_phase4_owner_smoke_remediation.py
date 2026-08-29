from django.test import TestCase, override_settings
from django.urls import reverse

from crm.models import Organization, OrganizationPerson, Person, PersonContact, Tenant
from crm.serializers import OrganizationSerializer, PersonContactSerializer, PersonSerializer
from crm.services.phone_writes import phone_dial_uri


class InternalPhoneDialContractTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Dial Tenant",
            slug="dial-tenant",
            default_phone_region="SE",
        )
        self.organization = Organization.objects.create(
            tenant=self.tenant,
            name="Svensk aktør",
            phone="070 123 45 67",
            phone_normalized="+46701234567",
            phone_normalization_region="SE",
            publish_phone=False,
        )
        self.person = Person.objects.create(
            tenant=self.tenant,
            full_name="Svensk kontakt",
            phone="070 123 45 67",
        )
        self.primary_phone = PersonContact.objects.create(
            tenant=self.tenant,
            person=self.person,
            type="PHONE",
            value="070 123 45 67",
            normalized_value="+46701234567",
            normalization_region="SE",
            is_primary=True,
            is_public=False,
        )

    def test_organization_returns_raw_display_and_canonical_dial_uri(self):
        payload = OrganizationSerializer(self.organization).data

        self.assertEqual(payload["phone"], "070 123 45 67")
        self.assertEqual(payload["phone_dial_uri"], "tel:+46701234567")
        self.assertNotIn("phone_normalized", payload)

    def test_person_uses_authoritative_primary_phone_contact_for_dial_uri(self):
        PersonContact.objects.create(
            tenant=self.tenant,
            person=self.person,
            type="PHONE",
            value="22 12 34 56",
            normalized_value="+4722123456",
            normalization_region="NO",
            is_primary=False,
        )

        payload = PersonSerializer(self.person).data

        self.assertEqual(payload["phone"], "070 123 45 67")
        self.assertEqual(payload["phone_dial_uri"], "tel:+46701234567")
        self.assertNotIn("normalized_value", payload)

    def test_person_contact_returns_dial_uri_only_for_canonical_phone(self):
        payload = PersonContactSerializer(self.primary_phone).data
        self.assertEqual(payload["value"], "070 123 45 67")
        self.assertEqual(payload["phone_dial_uri"], "tel:+46701234567")
        self.assertNotIn("normalized_value", payload)

        self.primary_phone.normalized_value = None
        self.primary_phone.normalization_region = None
        self.primary_phone.save(update_fields=["normalized_value", "normalization_region"])
        payload = PersonContactSerializer(self.primary_phone).data
        self.assertEqual(payload["value"], "070 123 45 67")
        self.assertIsNone(payload["phone_dial_uri"])

    def test_norwegian_and_explicit_international_canonical_targets_are_preserved(self):
        self.assertEqual(phone_dial_uri("+4722123456"), "tel:+4722123456")
        self.assertEqual(phone_dial_uri("+46701234567"), "tel:+46701234567")
        self.assertIsNone(phone_dial_uri("0701234567"))
        self.assertIsNone(phone_dial_uri(None))

    def test_serialization_does_not_change_publication_flags(self):
        before = (self.organization.publish_phone, self.primary_phone.is_public)

        OrganizationSerializer(self.organization).data
        PersonSerializer(self.person).data
        PersonContactSerializer(self.primary_phone).data

        self.organization.refresh_from_db()
        self.primary_phone.refresh_from_db()
        self.assertEqual(
            (self.organization.publish_phone, self.primary_phone.is_public),
            before,
        )


@override_settings(SECURE_SSL_REDIRECT=False)
class PublicPhoneDialRegressionTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Public Dial", slug="public-dial")
        self.organization = Organization.objects.create(
            tenant=self.tenant,
            name="Publisert svensk aktør",
            org_number="112233445",
            is_published=True,
        )
        self.person = Person.objects.create(
            tenant=self.tenant,
            full_name="Offentlig svensk kontakt",
            phone="070 123 45 67",
        )
        self.link = OrganizationPerson.objects.create(
            tenant=self.tenant,
            organization=self.organization,
            person=self.person,
            status="ACTIVE",
            publish_person=True,
        )
        self.contact = PersonContact.objects.create(
            tenant=self.tenant,
            person=self.person,
            type="PHONE",
            value="070 123 45 67",
            normalized_value="+46701234567",
            normalization_region="SE",
            is_primary=True,
            is_public=True,
        )

    def test_public_html_keeps_raw_text_and_uses_canonical_href(self):
        response = self.client.get(
            reverse("public-actor-detail", kwargs={"actor_id": self.organization.id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="tel:+46701234567"')
        self.assertContains(response, "070 123 45 67")
        self.assertNotContains(response, 'href="tel:070 123 45 67"')

    def test_public_html_does_not_guess_a_dial_target_without_canonical_identity(self):
        self.contact.normalized_value = None
        self.contact.normalization_region = None
        self.contact.save(update_fields=["normalized_value", "normalization_region"])

        response = self.client.get(
            reverse("public-actor-detail", kwargs={"actor_id": self.organization.id})
        )

        self.assertContains(response, "070 123 45 67")
        self.assertNotContains(response, 'href="tel:070 123 45 67"')

    def test_public_api_shape_and_publication_flags_are_unchanged(self):
        response = self.client.get(
            f"/api/public/actors/{self.organization.org_number}/"
        )

        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        self.assertNotIn("phone_dial_uri", payload)
        public_contact = payload["people"][0]["public_contacts"][0]
        self.assertEqual(public_contact, {"type": "PHONE", "value": "070 123 45 67"})

        self.organization.refresh_from_db()
        self.link.refresh_from_db()
        self.contact.refresh_from_db()
        self.assertTrue(self.organization.is_published)
        self.assertTrue(self.link.publish_person)
        self.assertTrue(self.contact.is_public)
