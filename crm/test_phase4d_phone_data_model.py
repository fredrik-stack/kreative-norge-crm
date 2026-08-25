from types import SimpleNamespace

from django.core.exceptions import ValidationError
from django.db import DatabaseError, connection, transaction
from django.db.migrations.exceptions import IrreversibleError
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase

from crm.models import Organization, Person, PersonContact, Tenant
from crm.serializers import OrganizationSerializer, PersonContactSerializer, TenantSerializer


class PhoneIdentityModelTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Phone tenant", slug="phone-tenant")
        self.person = Person.objects.create(tenant=self.tenant, full_name="Phone person")

    def assert_database_rejection(self, callback):
        with self.assertRaises(DatabaseError), transaction.atomic():
            callback()

    def test_new_tenant_and_existing_phone_models_have_no_hidden_defaults(self):
        organization = Organization.objects.create(
            tenant=self.tenant,
            name="Phone organization",
            phone="900 12 345",
        )
        contact = PersonContact.objects.create(
            tenant=self.tenant,
            person=self.person,
            type="PHONE",
            value="900 12 345",
        )

        self.assertIsNone(self.tenant.default_phone_region)
        self.assertIsNone(organization.phone_normalized)
        self.assertIsNone(organization.phone_normalization_region)
        self.assertIsNone(contact.normalized_value)
        self.assertIsNone(contact.normalization_region)

    def test_region_model_validator_requires_supported_uppercase_region(self):
        for region in ("no", "ZZ"):
            with self.subTest(region=region):
                tenant = Tenant(name="Invalid region", slug=f"invalid-{region}")
                tenant.default_phone_region = region
                with self.assertRaises(ValidationError):
                    tenant.full_clean()

        self.tenant.default_phone_region = "NO"
        self.tenant.full_clean()

    def test_database_region_format_constraints_reject_lowercase(self):
        self.assert_database_rejection(
            lambda: Tenant.objects.filter(pk=self.tenant.pk).update(
                default_phone_region="no"
            )
        )
        self.assert_database_rejection(
            lambda: Organization.objects.create(
                tenant=self.tenant,
                name="Invalid organization region",
                phone_normalized="+4790012345",
                phone_normalization_region="no",
            )
        )
        self.assert_database_rejection(
            lambda: PersonContact.objects.create(
                tenant=self.tenant,
                person=self.person,
                type="PHONE",
                value="invalid region",
                normalized_value="+4790012345",
                normalization_region="no",
            )
        )

    def test_database_requires_canonical_e164_shape(self):
        invalid_values = ("4790012345", "+04790012345", "+47 90012345", "+" + "1" * 16)
        for index, value in enumerate(invalid_values):
            with self.subTest(value=value):
                self.assert_database_rejection(
                    lambda value=value, index=index: Organization.objects.create(
                        tenant=self.tenant,
                        name=f"Invalid E164 {index}",
                        phone_normalized=value,
                    )
                )

        organization = Organization.objects.create(
            tenant=self.tenant,
            name="Valid E164",
            phone_normalized="+4790012345",
        )
        self.assertEqual(organization.phone_normalized, "+4790012345")

    def test_region_cannot_exist_without_normalized_value(self):
        self.assert_database_rejection(
            lambda: Organization.objects.create(
                tenant=self.tenant,
                name="Region only",
                phone_normalization_region="NO",
            )
        )
        self.assert_database_rejection(
            lambda: PersonContact.objects.create(
                tenant=self.tenant,
                person=self.person,
                type="PHONE",
                value="region only",
                normalization_region="NO",
            )
        )

    def test_phone_identity_fields_are_not_allowed_on_email_contacts(self):
        self.assert_database_rejection(
            lambda: PersonContact.objects.create(
                tenant=self.tenant,
                person=self.person,
                type="EMAIL",
                value="person@example.test",
                normalized_value="+4790012345",
            )
        )

    def test_normalized_phone_is_unique_only_within_same_person_and_type(self):
        PersonContact.objects.create(
            tenant=self.tenant,
            person=self.person,
            type="PHONE",
            value="first display",
            normalized_value="+4790012345",
            normalization_region="NO",
        )
        self.assert_database_rejection(
            lambda: PersonContact.objects.create(
                tenant=self.tenant,
                person=self.person,
                type="PHONE",
                value="second display",
                normalized_value="+4790012345",
                normalization_region="NO",
            )
        )

        other_person = Person.objects.create(
            tenant=self.tenant,
            full_name="Other phone person",
        )
        PersonContact.objects.create(
            tenant=self.tenant,
            person=other_person,
            type="PHONE",
            value="shared display",
            normalized_value="+4790012345",
        )
        self.assertEqual(
            PersonContact.objects.filter(normalized_value="+4790012345").count(),
            2,
        )

    def test_organizations_do_not_have_phone_uniqueness(self):
        for index in range(2):
            Organization.objects.create(
                tenant=self.tenant,
                name=f"Shared phone organization {index}",
                phone_normalized="+4790012345",
            )
        self.assertEqual(
            Organization.objects.filter(phone_normalized="+4790012345").count(),
            2,
        )

    def test_person_contact_tenant_consistency_is_preserved(self):
        other_tenant = Tenant.objects.create(name="Other tenant", slug="other-tenant")
        other_person = Person.objects.create(tenant=other_tenant, full_name="Other person")
        serializer = PersonContactSerializer(
            data={
                "person": other_person.pk,
                "type": "PHONE",
                "value": "+4790012345",
                "is_primary": False,
                "is_public": False,
            },
            context={"view": SimpleNamespace(kwargs={"tenant_id": self.tenant.pk})},
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("person", serializer.errors)

    def test_4d_identity_fields_remain_internal_after_4e_serializer_writes(self):
        organization = Organization.objects.create(
            tenant=self.tenant,
            name="Unchanged API organization",
        )
        organization_serializer = OrganizationSerializer(
            organization,
            data={"phone": "+47 900 12 345"},
            partial=True,
        )
        self.assertTrue(organization_serializer.is_valid(), organization_serializer.errors)
        organization_serializer.save()
        organization.refresh_from_db()

        contact = PersonContact.objects.create(
            tenant=self.tenant,
            person=self.person,
            type="PHONE",
            value="old display",
        )
        contact_serializer = PersonContactSerializer(
            contact,
            data={"value": "+46 8 505 103 00"},
            partial=True,
        )
        self.assertTrue(contact_serializer.is_valid(), contact_serializer.errors)
        contact_serializer.save()
        contact.refresh_from_db()

        self.assertEqual(organization.phone, "+47 900 12 345")
        self.assertEqual(organization.phone_normalized, "+4790012345")
        self.assertIsNone(organization.phone_normalization_region)
        self.assertEqual(contact.value, "+46 8 505 103 00")
        self.assertEqual(contact.normalized_value, "+46850510300")
        self.assertIsNone(contact.normalization_region)
        self.assertIsNone(TenantSerializer(self.tenant).data["default_phone_region"])
        self.assertNotIn("phone_normalized", OrganizationSerializer(organization).data)
        self.assertNotIn("normalized_value", PersonContactSerializer(contact).data)


class PhoneIdentityMigrationTests(TransactionTestCase):
    migrate_from = ("crm", "0031_import_image_decision_contract")
    migrate_to = ("crm", "0032_phone_identity_fields")

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_schema_forward_and_reverse_preserve_existing_raw_and_publication_data(self):
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        old_apps = executor.loader.project_state([self.migrate_from]).apps
        OldTenant = old_apps.get_model("crm", "Tenant")
        OldOrganization = old_apps.get_model("crm", "Organization")
        OldPerson = old_apps.get_model("crm", "Person")
        OldPersonContact = old_apps.get_model("crm", "PersonContact")

        tenant = OldTenant.objects.create(name="Existing tenant", slug="existing-tenant")
        organization = OldOrganization.objects.create(
            tenant=tenant,
            name="Existing organization",
            phone="900 12 345",
            is_published=True,
            publish_phone=True,
        )
        person = OldPerson.objects.create(
            tenant=tenant,
            full_name="Existing person",
            phone="900 12 345",
        )
        contact = OldPersonContact.objects.create(
            tenant=tenant,
            person=person,
            type="PHONE",
            value="900 12 345",
            is_primary=True,
            is_public=True,
        )

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        new_apps = executor.loader.project_state([self.migrate_to]).apps
        NewTenant = new_apps.get_model("crm", "Tenant")
        NewOrganization = new_apps.get_model("crm", "Organization")
        NewPerson = new_apps.get_model("crm", "Person")
        NewPersonContact = new_apps.get_model("crm", "PersonContact")

        migrated_tenant = NewTenant.objects.get(pk=tenant.pk)
        migrated_organization = NewOrganization.objects.get(pk=organization.pk)
        migrated_person = NewPerson.objects.get(pk=person.pk)
        migrated_contact = NewPersonContact.objects.get(pk=contact.pk)
        self.assertIsNone(migrated_tenant.default_phone_region)
        self.assertEqual(migrated_organization.phone, "900 12 345")
        self.assertTrue(migrated_organization.is_published)
        self.assertTrue(migrated_organization.publish_phone)
        self.assertIsNone(migrated_organization.phone_normalized)
        self.assertIsNone(migrated_organization.phone_normalization_region)
        self.assertEqual(migrated_person.phone, "900 12 345")
        self.assertEqual(migrated_contact.value, "900 12 345")
        self.assertTrue(migrated_contact.is_primary)
        self.assertTrue(migrated_contact.is_public)
        self.assertIsNone(migrated_contact.normalized_value)
        self.assertIsNone(migrated_contact.normalization_region)
        self.assertIsNone(
            NewTenant.objects.create(name="New tenant", slug="new-tenant").default_phone_region
        )

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        reversed_apps = executor.loader.project_state([self.migrate_from]).apps
        reversed_organization = reversed_apps.get_model("crm", "Organization").objects.get(
            pk=organization.pk
        )
        reversed_person = reversed_apps.get_model("crm", "Person").objects.get(pk=person.pk)
        reversed_contact = reversed_apps.get_model("crm", "PersonContact").objects.get(
            pk=contact.pk
        )
        self.assertEqual(reversed_organization.phone, "900 12 345")
        self.assertTrue(reversed_organization.publish_phone)
        self.assertEqual(reversed_person.phone, "900 12 345")
        self.assertEqual(reversed_contact.value, "900 12 345")
        self.assertTrue(reversed_contact.is_primary)
        self.assertTrue(reversed_contact.is_public)

    def test_reverse_is_blocked_after_phone_identity_data_is_stored(self):
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        apps = executor.loader.project_state([self.migrate_to]).apps
        TenantAt4D = apps.get_model("crm", "Tenant")
        TenantAt4D.objects.create(
            name="Configured tenant",
            slug="configured-tenant",
            default_phone_region="NO",
        )

        executor = MigrationExecutor(connection)
        with self.assertRaises(IrreversibleError):
            executor.migrate([self.migrate_from])
