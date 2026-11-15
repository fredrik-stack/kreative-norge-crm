"""Private historical tag restoration: synthetic API and non-destructive adoption."""
import importlib
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from crm.models import InternalTag, Organization, Person, Tenant, TenantMembership
from crm.serializers import OrganizationSerializer


@override_settings(SECURE_SSL_REDIRECT=False)
class InternalTagTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Synthetic own", slug="internal-own")
        self.other = Tenant.objects.create(name="Synthetic other", slug="internal-other")
        self.user = get_user_model().objects.create_user(username="internal-editor")
        self.reader = get_user_model().objects.create_user(username="internal-reader")
        for user, role in ((self.user, "redigerer"), (self.reader, "leser")):
            TenantMembership.objects.create(user=user, tenant=self.tenant, role=role)
        self.org = Organization.objects.create(tenant=self.tenant, name="Own actor", is_published=True)
        self.person = Person.objects.create(tenant=self.tenant, full_name="Own person")
        self.tag = InternalTag.objects.create(tenant=self.tenant, name="Private workflow")
        self.foreign = InternalTag.objects.create(tenant=self.other, name="Foreign secret")
        self.org.internal_tags.add(self.tag)
        self.person.internal_tags.add(self.tag)
        self.client = APIClient(); self.client.force_authenticate(self.user)
        self.root = f"/api/tenants/{self.tenant.pk}/"

    def path(self, model, obj):
        return self.root + model + f"/{obj.pk}/"

    def test_profiles_preserve_omitted_and_clear_only_explicit_private_names(self):
        for route, obj, name in (("organizations", self.org, "name"), ("persons", self.person, "full_name")):
            with self.subTest(route=route):
                path = self.path(route, obj)
                self.assertEqual(self.client.get(path).data["internal_tags"][0]["name"], self.tag.name)
                self.assertEqual(self.client.patch(path, {name: "Updated"}, format="json").status_code, 200)
                self.assertTrue(obj.internal_tags.filter(pk=self.tag.pk).exists())
                response = self.client.patch(path, {"internal_tag_names": ["New private", "New private"]}, format="json")
                self.assertEqual(response.status_code, 200, response.data)
                self.assertEqual([tag["name"] for tag in response.data["internal_tags"]], ["New private"])
                self.assertEqual(self.client.patch(path, {"internal_tag_names": []}, format="json").status_code, 200)
                self.assertFalse(obj.internal_tags.exists())
        self.assertEqual(InternalTag.objects.filter(tenant=self.tenant, name="New private").count(), 1)
        self.assertTrue(InternalTag.objects.filter(pk=self.tag.pk).exists())

    def test_own_names_are_local_even_when_a_foreign_tag_has_the_same_name(self):
        response = self.client.patch(self.path("organizations", self.org), {"internal_tag_names": [self.foreign.name]}, format="json")
        self.assertEqual(response.status_code, 200)
        attached = self.org.internal_tags.get()
        self.assertEqual(attached.tenant_id, self.tenant.pk)
        self.assertNotEqual(attached.pk, self.foreign.pk)
        # Caller-supplied foreign IDs cannot attach anything: only local names are writable.
        response = self.client.patch(self.path("organizations", self.org), {"internal_tag_ids": [self.foreign.pk]}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(self.org.internal_tags.filter(pk=self.foreign.pk).exists())

    def test_foreign_scope_denied_and_corrupt_foreign_join_never_serialized(self):
        self.assertEqual(self.client.get(f"/api/tenants/{self.other.pk}/internal-tags/").status_code, 403)
        self.assertEqual(self.client.get(self.root + f"internal-tags/{self.foreign.pk}/").status_code, 404)
        self.org.internal_tags.add(self.foreign)
        data = self.client.get(self.path("organizations", self.org)).data
        self.assertNotIn(self.foreign.name, str(data))
        self.assertEqual(OrganizationSerializer(self.org).data["internal_tags"], [])

    def test_reader_and_anonymous_cannot_write(self):
        self.client.force_authenticate(self.reader)
        self.assertEqual(self.client.get(self.root + "internal-tags/").status_code, 200)
        self.assertEqual(self.client.patch(self.path("persons", self.person), {"internal_tag_names": []}, format="json").status_code, 403)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(self.root + "internal-tags/").status_code, 403)

    def test_inactive_user_or_membership_cannot_read_or_write_internal_tags(self):
        for user_inactive in (False, True):
            with self.subTest(user_inactive=user_inactive):
                TenantMembership.objects.filter(user=self.user).update(is_active=user_inactive)
                self.user.is_active = not user_inactive
                self.assertEqual(self.client.get(self.root + "internal-tags/").status_code, 403)
                result = self.client.patch(self.path("organizations", self.org), {"name": "Denied", "internal_tag_names": []}, format="json")
                self.assertEqual(result.status_code, 403)
                self.org.refresh_from_db(); self.assertEqual(self.org.name, "Own actor")
                self.assertTrue(self.org.internal_tags.filter(pk=self.tag.pk).exists())

    def test_invalid_tag_and_tag_storage_error_roll_back_profile_write(self):
        path = self.path("organizations", self.org)
        old_name = self.org.name
        response = self.client.patch(path, {"name": "Bad", "internal_tag_names": ["x" * 65]}, format="json")
        self.assertEqual(response.status_code, 400)
        with patch("crm.serializers.InternalTagsMixin._save_internal_tags", side_effect=RuntimeError("synthetic storage failure")):
            with self.assertRaises(RuntimeError):
                self.client.patch(path, {"name": "Must roll back", "internal_tag_names": ["New"]}, format="json")
        self.org.refresh_from_db(); self.assertEqual(self.org.name, old_name)
        self.assertTrue(self.org.internal_tags.filter(pk=self.tag.pk).exists())

    def test_public_and_brave_context_have_no_internal_tags(self):
        from django.test import override_settings
        public = self.client.get("/api/public/actors/")
        self.assertEqual(public.status_code, 200)
        self.assertNotIn(self.tag.name, str(public.data)); self.assertNotIn("internal_tags", str(public.data))
        with override_settings(IMAGE_ASSET_FEATURE_ENABLED=True, BRAVE_IMAGE_SEARCH_USER_ID=self.user.pk, BRAVE_IMAGE_SEARCH_API_KEY="synthetic-only"):
            context = self.client.get(self.path("organizations", self.org) + "images/search-context/")
        self.assertEqual(context.status_code, 200)
        self.assertNotIn(self.tag.name, str(context.data)); self.assertNotIn("internal_tags", context.data)

    def test_adoption_is_idempotent_and_state_reverse_preserves_all_values(self):
        migration = importlib.import_module("crm.migrations.0041_restore_legacy_internal_tags")
        state = MigrationExecutor(connection).loader.project_state([("crm", "0041_restore_legacy_internal_tags")])
        before = list(InternalTag.objects.order_by("pk").values())
        links = list(self.org.internal_tags.values_list("pk", flat=True))
        with connection.schema_editor(atomic=False) as editor:
            for _ in range(2):
                migration.RestoreInternalTags().database_forwards("crm", editor, state, state)
            migration.RestoreInternalTags().database_backwards("crm", editor, state, state)
        self.assertEqual(list(InternalTag.objects.order_by("pk").values()), before)
        self.assertEqual(list(self.org.internal_tags.values_list("pk", flat=True)), links)

    def test_adoption_rejects_a_reused_next_id_without_advancing_or_repairing_sequence(self):
        migration = importlib.import_module("crm.migrations.0041_restore_legacy_internal_tags")
        state = MigrationExecutor(connection).loader.project_state([("crm", "0041_restore_legacy_internal_tags")])
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_get_serial_sequence('crm_internaltag','id')")
            sequence = cursor.fetchone()[0]
            quoted = ".".join(connection.ops.quote_name(part) for part in sequence.split("."))
            cursor.execute("SELECT last_value,is_called FROM " + quoted); before = cursor.fetchone()
            cursor.execute("SELECT max(id) FROM crm_internaltag"); maximum = cursor.fetchone()[0]
            cursor.execute("SELECT setval(%s,%s,false)", [sequence, maximum])
            try:
                with connection.schema_editor(atomic=False) as editor:
                    with self.assertRaisesRegex(RuntimeError, "ID_SEQUENCE_UNSAFE"):
                        migration.RestoreInternalTags().database_forwards("crm", editor, state, state)
                cursor.execute("SELECT last_value,is_called FROM " + quoted)
                self.assertEqual(cursor.fetchone(), (maximum, False))
            finally:
                cursor.execute("SELECT setval(%s,%s,%s)", [sequence, *before])

    def test_adoption_rejects_partial_index_as_a_substitute_for_name_uniqueness(self):
        migration = importlib.import_module("crm.migrations.0041_restore_legacy_internal_tags")
        state = MigrationExecutor(connection).loader.project_state([("crm", "0041_restore_legacy_internal_tags")])
        with connection.cursor() as cursor:
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
            constraints = connection.introspection.get_constraints(cursor, "crm_internaltag")
            name = next(name for name, c in constraints.items() if c["unique"] and c["columns"] == ["tenant_id", "name"])
            cursor.execute("ALTER TABLE crm_internaltag DROP CONSTRAINT " + connection.ops.quote_name(name))
            cursor.execute("CREATE UNIQUE INDEX synthetic_partial_name ON crm_internaltag(tenant_id,name) WHERE false")
        with connection.schema_editor(atomic=False) as editor:
            with self.assertRaisesRegex(RuntimeError, "UNIQUE_MISMATCH"):
                migration.RestoreInternalTags().database_forwards("crm", editor, state, state)

    def test_adoption_rejects_id_default_that_does_not_use_its_owned_sequence(self):
        migration = importlib.import_module("crm.migrations.0041_restore_legacy_internal_tags")
        state = MigrationExecutor(connection).loader.project_state([("crm", "0041_restore_legacy_internal_tags")])
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_get_serial_sequence('crm_internaltag','id')")
            sequence = cursor.fetchone()[0]
            quoted = ".".join(connection.ops.quote_name(part) for part in sequence.split("."))
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
            cursor.execute("SELECT attidentity FROM pg_attribute WHERE attrelid='crm_internaltag'::regclass AND attname='id'")
            if cursor.fetchone()[0]:
                cursor.execute("ALTER TABLE crm_internaltag ALTER COLUMN id DROP IDENTITY")
                cursor.execute("CREATE SEQUENCE " + quoted)
                cursor.execute("ALTER SEQUENCE " + quoted + " OWNED BY crm_internaltag.id")
                cursor.execute("SELECT COALESCE(max(id),0)+1 FROM crm_internaltag")
                cursor.execute("SELECT setval(%s,%s,false)", [sequence, cursor.fetchone()[0]])
            cursor.execute("ALTER TABLE crm_internaltag ALTER COLUMN id SET DEFAULT 0")
        with connection.schema_editor(atomic=False) as editor:
            with self.assertRaisesRegex(RuntimeError, "ID_DEFAULT_UNSAFE"):
                migration.RestoreInternalTags().database_forwards("crm", editor, state, state)

    def test_adoption_rejects_cross_tenant_links_and_partial_schema(self):
        migration = importlib.import_module("crm.migrations.0041_restore_legacy_internal_tags")
        state = MigrationExecutor(connection).loader.project_state([("crm", "0041_restore_legacy_internal_tags")])
        self.org.internal_tags.add(self.foreign)
        with connection.schema_editor(atomic=False) as editor:
            with self.assertRaisesRegex(RuntimeError, "INVALID_ASSIGNMENT"):
                migration.RestoreInternalTags().database_forwards("crm", editor, state, state)
        with patch.object(connection.introspection, "table_names", return_value=["crm_internaltag"]):
            with connection.schema_editor(atomic=False) as editor:
                with self.assertRaisesRegex(RuntimeError, "PARTIAL_SCHEMA"):
                    migration.RestoreInternalTags().database_forwards("crm", editor, state, state)
