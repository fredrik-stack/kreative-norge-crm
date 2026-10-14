from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction, models
from django.db.models.deletion import ProtectedError
from django.db.migrations.executor import MigrationExecutor
from django.forms.models import model_to_dict
from django.test import TestCase, TransactionTestCase, RequestFactory, override_settings
from rest_framework.test import APIClient

from crm.domain_integrity import DomainStructureError

from crm.models import (
    SharingDomain, Tenant, Organization, Person,
    OrganizationTenantAssignment, PersonTenantAssignment, TenantMembership,
)


def fixture_bound(model, **values):
    # Explicit synthetic fixture setup bypasses the application writer boundary.
    obj = model(**values)
    models.QuerySet(model=model, using="default").bulk_create([obj])
    return obj


def fixture_assignment(model, **values):
    obj = model(**values)
    models.QuerySet(model=model, using="default").bulk_create([obj])
    return obj


class AssignmentFoundationTests(TestCase):
    def setUp(self):
        self.domain = SharingDomain.objects.create(name="Synthetic", slug="synthetic")
        self.legacy = fixture_bound(Tenant, name="Legacy", slug="legacy", sharing_domain=self.domain)
        self.target = fixture_bound(Tenant, name="Target", slug="target", sharing_domain=self.domain)
        self.org = fixture_bound(Organization, name="Actor", tenant=self.legacy, sharing_domain=self.domain)
        self.person = fixture_bound(Person, full_name="Person", tenant=self.legacy, sharing_domain=self.domain)

    def cases(self):
        return [(OrganizationTenantAssignment, "organization", self.org),
                (PersonTenantAssignment, "person", self.person)]

    def test_nullable_domain_no_hidden_assignment_or_seed(self):
        tenant = Tenant.objects.create(name="Unbound", slug="unbound")
        for obj in (tenant, Organization.objects.create(name="Unbound", tenant=tenant),
                    Person.objects.create(full_name="Unbound", tenant=tenant)):
            self.assertIsNone(obj.sharing_domain_id)
        self.assertEqual(SharingDomain.objects.count(), 1)
        self.assertEqual(OrganizationTenantAssignment.objects.count(), 0)
        self.assertEqual(PersonTenantAssignment.objects.count(), 0)

    def test_valid_assignments_and_database_uniqueness(self):
        for model, field, entity in self.cases():
            with self.subTest(model=model.__name__):
                values = {field: entity, "tenant": self.target}
                obj = model(**values)
                obj.full_clean()
                fixture_assignment(model, **values)
                second = model(**{field: entity, "tenant": self.legacy})
                second.full_clean()
                fixture_assignment(model, **{field: entity, "tenant": self.legacy})
                self.assertEqual(entity.tenant_assignments.count(), 2)
                with self.assertRaises(IntegrityError), transaction.atomic():
                    fixture_assignment(model, **values)

    def test_database_rejects_null_and_dangling_targets(self):
        for model, field, entity in self.cases():
            for values in ({field: entity, "tenant": None}, {field: None, "tenant": self.target},
                           {field: entity, "tenant_id": 999999}, {f"{field}_id": 999999, "tenant": self.target}):
                with self.subTest(model=model.__name__, values=str(values)):
                    with self.assertRaises(IntegrityError), transaction.atomic():
                        fixture_assignment(model, **values)
                        # PostgreSQL FKs are deferred: check within the savepoint.
                        connection.check_constraints()

    def test_full_clean_rejects_missing_domains_cross_domain_and_missing_targets(self):
        other = SharingDomain.objects.create(name="Other", slug="other")
        wrong = fixture_bound(Tenant, name="Wrong", slug="wrong", sharing_domain=other)
        unbound = Tenant.objects.create(name="Unbound", slug="unbound")
        for model, field, entity in self.cases():
            for tenant in (wrong, unbound):
                with self.subTest(model=model.__name__, tenant=tenant.slug), self.assertRaises(ValidationError):
                    model(**{field: entity, "tenant": tenant}).full_clean()
            for values in ({f"{field}_id": 999999, "tenant": self.target},
                           {field: entity, "tenant_id": 999999},
                           {field: None, "tenant": self.target},
                           {field: entity, "tenant": None}):
                with self.assertRaises(ValidationError):
                    model(**values).full_clean()
            unbound_entity = type(entity).objects.create(tenant=unbound, **{"name" if field == "organization" else "full_name": "Unbound"})
            with self.assertRaises(ValidationError):
                model(**{field: unbound_entity, "tenant": self.target}).full_clean()

    def test_phase6a2_closes_previous_orm_and_bulk_cross_domain_bypass(self):
        other = SharingDomain.objects.create(name="Other", slug="other")
        wrong = fixture_bound(Tenant, name="Wrong", slug="wrong", sharing_domain=other)
        for model, field, entity in self.cases():
            values = {field: entity, "tenant": wrong}
            with self.assertRaises(DomainStructureError):
                model.objects.create(**values)
            with self.assertRaises(DomainStructureError):
                model.objects.bulk_create([model(**values)])
            with self.assertRaises(IntegrityError), transaction.atomic():
                fixture_assignment(model, **values)

    def test_assignment_protects_profile_target_and_legacy_tenant_without_partial_delete(self):
        for model, field, entity in self.cases():
            fixture_assignment(model, **{field: entity, "tenant": self.target})
        for obj in (self.org, self.person, self.target, self.legacy):
            for operation in (obj.delete, lambda obj=obj: type(obj).objects.filter(pk=obj.pk).delete()):
                with self.subTest(parent=type(obj).__name__), self.assertRaises(ProtectedError):
                    operation()
                self.assertTrue(type(obj).objects.filter(pk=obj.pk).exists())
                self.assertTrue(Organization.objects.filter(pk=self.org.pk).exists())
                self.assertTrue(Person.objects.filter(pk=self.person.pk).exists())
                self.assertEqual(OrganizationTenantAssignment.objects.count(), 1)
                self.assertEqual(PersonTenantAssignment.objects.count(), 1)

    def test_domain_delete_is_protected_and_unassigned_legacy_cascade_remains(self):
        with self.assertRaises(ProtectedError):
            self.domain.delete()
        org_pk, person_pk = self.org.pk, self.person.pk
        self.legacy.delete()
        self.assertFalse(Organization.objects.filter(pk=org_pk).exists())
        self.assertFalse(Person.objects.filter(pk=person_pk).exists())
        self.assertTrue(Tenant.objects.filter(pk=self.target.pk).exists())

    def test_postgresql_foreign_keys_reject_raw_parent_delete(self):
        for model, field, entity in self.cases():
            fixture_assignment(model, **{field: entity, "tenant": self.target})
        for obj in (self.org, self.person, self.target, self.legacy, self.domain):
            with self.subTest(parent=type(obj).__name__):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    with connection.cursor() as cursor:
                        cursor.execute(f'DELETE FROM "{obj._meta.db_table}" WHERE id = %s', [obj.pk])
                    connection.check_constraints()
                self.assertTrue(type(obj).objects.filter(pk=obj.pk).exists())

    def test_admin_submission_cannot_write_hidden_domain(self):
        request = RequestFactory().post("/admin/")
        request.user = get_user_model().objects.create_superuser(username="form-admin", password="test")
        for obj in (self.legacy, self.org, self.person):
            form_class = admin.site._registry[type(obj)].get_form(request, obj)
            data = model_to_dict(obj)
            data["sharing_domain"] = "999999"
            form = form_class(data=data, instance=obj)
            self.assertTrue(form.is_valid(), form.errors)
            form.save()
            obj.refresh_from_db()
            self.assertEqual(obj.sharing_domain_id, self.domain.pk)
        form_class = admin.site._registry[Tenant].get_form(request)
        form = form_class(data={"name": "New", "slug": "new-admin", "sharing_domain": self.domain.pk})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIsNone(form.save().sharing_domain_id)
        self.assertEqual(SharingDomain.objects.count(), 1)
        self.assertFalse(OrganizationTenantAssignment.objects.exists())
        self.assertFalse(PersonTenantAssignment.objects.exists())

    def test_admin_forms_exclude_domain_and_synthetic_assignments_protect_admin_deletion(self):
        request = RequestFactory().get("/admin/")
        request.user = get_user_model().objects.create_superuser(username="admin", password="test")
        for model, field, entity in self.cases():
            fixture_assignment(model, **{field: entity, "tenant": self.target})
        for obj in (self.org, self.person, self.target, self.legacy):
            model_admin = admin.site._registry[type(obj)]
            self.assertNotIn("sharing_domain", model_admin.get_form(request).base_fields)
            for operation in (
                lambda: model_admin.delete_model(request, obj),
                lambda: model_admin.delete_queryset(request, type(obj).objects.filter(pk=obj.pk)),
            ):
                with self.assertRaises(ProtectedError):
                    operation()
            self.assertTrue(type(obj).objects.filter(pk=obj.pk).exists())
        for model in (SharingDomain, OrganizationTenantAssignment, PersonTenantAssignment):
            self.assertNotIn(model, admin.site._registry)


@override_settings(SECURE_SSL_REDIRECT=False)
class FoundationApiBoundaryTests(TestCase):
    def test_existing_api_ignores_new_fields_and_keeps_tenant_scope(self):
        tenant = Tenant.objects.create(name="Legacy", slug="api-legacy")
        other = Tenant.objects.create(name="Other", slug="api-other")
        domain = SharingDomain.objects.create(name="Synthetic", slug="api-synthetic")
        user = get_user_model().objects.create_user(username="editor", password="test")
        TenantMembership.objects.create(tenant=tenant, user=user, role=TenantMembership.Role.REDIGERER)
        client = APIClient()
        client.force_authenticate(user)
        for route, model, name_field in (("organizations", Organization, "name"), ("persons", Person, "full_name")):
            base = f"/api/tenants/{tenant.pk}/{route}/"
            payload = {name_field: "Legacy", "sharing_domain": domain.pk,
                       "tenant_assignments": [{"tenant": other.pk}]}
            response = client.post(base, payload, format="json")
            self.assertEqual(response.status_code, 201, response.content)
            obj = model.objects.get(pk=response.json()["id"])
            self.assertIsNone(obj.sharing_domain_id)
            self.assertEqual(obj.tenant_id, tenant.pk)
            response = client.patch(f"{base}{obj.pk}/", payload, format="json")
            self.assertEqual(response.status_code, 200, response.content)
            obj.refresh_from_db()
            self.assertIsNone(obj.sharing_domain_id)
            for key in ("sharing_domain", "sharing_domain_id", "tenant_assignments"):
                self.assertNotIn(key, response.json())
            foreign = model.objects.create(tenant=other, **{name_field: "Foreign"})
            self.assertEqual(client.get(f"{base}{foreign.pk}/").status_code, 404)
        response = client.get("/api/tenants/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("sharing_domain", response.json()[0])
        self.assertEqual(client.patch(f"/api/tenants/{tenant.pk}/", {"sharing_domain": domain.pk}, format="json").status_code, 405)
        self.assertEqual(SharingDomain.objects.count(), 1)
        self.assertEqual(OrganizationTenantAssignment.objects.count(), 0)
        self.assertEqual(PersonTenantAssignment.objects.count(), 0)


class FoundationMigrationTests(TransactionTestCase):
    migrate_from = ("crm", "0032_phone_identity_fields")

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_schema_forward_reverse_forward_preserves_legacy_data_without_backfill(self):
        executor = MigrationExecutor(connection)
        leaves = executor.loader.graph.leaf_nodes("crm")
        executor.migrate([self.migrate_from])
        apps = executor.loader.project_state([self.migrate_from]).apps
        tenant = apps.get_model("crm", "Tenant").objects.create(name="Legacy", slug="migration-legacy")
        org = apps.get_model("crm", "Organization").objects.create(tenant=tenant, name="Actor", phone="raw", note="private", is_published=True)
        person = apps.get_model("crm", "Person").objects.create(tenant=tenant, full_name="Person", phone="raw", note="private")
        # Existing image metadata must remain byte/scope-identical across the schema migration.
        ImageAsset = apps.get_model("crm", "ImageAsset")
        asset = ImageAsset.objects.create(tenant=tenant, checksum_sha256="a" * 64, private_storage_key="originals/legacy.jpg", original_format="jpeg", mime_type="image/jpeg", file_size_bytes=12, width=2, height=2, validation_version="test")
        snapshots = {name: list(apps.get_model("crm", name).objects.values()) for name in ("Tenant", "Organization", "Person", "ImageAsset")}
        for target in (leaves, [self.migrate_from], leaves):
            executor = MigrationExecutor(connection)
            executor.migrate(target)
            state = executor.loader.project_state(target).apps
            for name, rows in snapshots.items():
                actual = list(state.get_model("crm", name).objects.values())
                if target == leaves and name in ("Tenant", "Organization", "Person"):
                    self.assertTrue(all(row.pop("sharing_domain_id") is None for row in actual))
                self.assertEqual(actual, rows)
            if target == leaves:
                for name in ("SharingDomain", "OrganizationTenantAssignment", "PersonTenantAssignment"):
                    self.assertEqual(state.get_model("crm", name).objects.count(), 0)
