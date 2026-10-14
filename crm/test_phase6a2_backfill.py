import copy
import json
import tempfile
import threading
from pathlib import Path
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, close_old_connections, connection, connections, models, transaction
from django.db.models.deletion import ProtectedError
from django.forms.models import model_to_dict
from django.test import RequestFactory, TransactionTestCase, override_settings
from rest_framework.test import APIClient

from crm.domain_integrity import DomainStructureError, _legacy_assignment_scope
from crm.models import (
    ImageAsset, LegacyDomainBackfillBatch, Organization, OrganizationPerson,
    OrganizationTenantAssignment, Person, PersonContact, PersonTenantAssignment,
    SharingDomain, Tenant, TenantMembership,
)
from crm.services.domain_backfill import apply_backfill, dry_run, read_batch, _snapshot


def raw_assignment(model, entity_id, tenant_id):
    field = "organization_id" if model is OrganizationTenantAssignment else "person_id"
    with connection.cursor() as cursor:
        cursor.execute(f'INSERT INTO "{model._meta.db_table}" ({field},tenant_id,created_at,updated_at) VALUES (%s,%s,now(),now()) RETURNING id', [entity_id, tenant_id])
        return cursor.fetchone()[0]


@override_settings(SECURE_SSL_REDIRECT=False)
class LegacyBackfillTests(TransactionTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.operator = get_user_model().objects.create_superuser(username="synthetic-operator", password="synthetic")
        self.tenant = Tenant.objects.create(name="Synthetic Office", slug="synthetic-office")
        self.empty = Tenant.objects.create(name="Synthetic Empty", slug="synthetic-empty")
        self.other = Tenant.objects.create(name="Outside", slug="outside")
        self.org = Organization.objects.create(tenant=self.tenant, name="Synthetic", org_number="123", phone="raw", note="private", is_published=True)
        self.person = Person.objects.create(tenant=self.tenant, full_name="Synthetic", phone="raw", note="private")
        self.foreign = Person.objects.create(tenant=self.other, full_name="Outside")
        OrganizationPerson.objects.create(tenant=self.tenant, organization=self.org, person=self.person)
        PersonContact.objects.create(tenant=self.tenant, person=self.person, type="EMAIL", value="synthetic@example.invalid")
        ImageAsset.objects.create(tenant=self.tenant, checksum_sha256="a"*64, private_storage_key="originals/synthetic.jpg", original_format="jpeg", mime_type="image/jpeg", file_size_bytes=12, width=1, height=1)
        self.mapping = {"domain": {"id": None, "name": "Synthetic Domain", "slug": "synthetic-domain"},
                        "tenants": [{"id": t.pk, "slug": t.slug, "name": t.name} for t in (self.tenant, self.empty)]}

    def options(self, batch="batch", mapping=None):
        mapping = mapping or self.mapping
        report = dry_run(mapping)
        return dict(mapping=mapping, environment="synthetic", expected_database=report["database_identity"],
                    expected_digest=report["plan"]["digest"], batch_id=batch, operator_id=self.operator.pk,
                    code_baseline="a"*40, manifest_path=str(Path(self.temp.name)/f"{batch}.json"))

    def apply(self, batch="batch"):
        return apply_backfill(**self.options(batch))

    def bound_mapping(self):
        return {**self.mapping, "domain": {**self.mapping["domain"], "id": SharingDomain.objects.get(slug="synthetic-domain").pk}}

    def test_dry_run_command_has_no_writes_and_no_seed(self):
        path = Path(self.temp.name)/"mapping.json"
        path.write_text(json.dumps(self.mapping))
        from io import StringIO
        out = StringIO()
        call_command("backfill_legacy_domain", mapping=str(path), stdout=out)
        self.assertEqual(json.loads(out.getvalue())["writes"], 0)
        self.assertEqual(SharingDomain.objects.count(), 0)
        self.assertEqual(LegacyDomainBackfillBatch.objects.count(), 0)
        self.assertIsNone(Tenant.objects.get(pk=self.tenant.pk).sharing_domain_id)

    def test_apply_preservation_scope_and_new_noop_batch(self):
        before = dry_run(self.mapping)["plan"]["snapshot"]["preserved"]
        result = self.apply()
        self.assertEqual(result["state"], "COMMITTED_VERIFIED")
        self.assertEqual(OrganizationTenantAssignment.objects.count(), 1)
        self.assertEqual(PersonTenantAssignment.objects.count(), 1)
        self.assertIsNone(Person.objects.get(pk=self.foreign.pk).sharing_domain_id)
        self.assertEqual(dry_run(self.bound_mapping())["plan"]["snapshot"]["preserved"], before)
        noop = self.options("new-noop", self.bound_mapping())
        self.assertEqual(apply_backfill(**noop)["changes_applied"], 0)
        self.assertEqual(LegacyDomainBackfillBatch.objects.count(), 2)

    def test_replay_uses_registry_not_new_manifest_path(self):
        options = self.options()
        self.apply()
        replay = apply_backfill(**options)
        self.assertEqual(replay["mode"], "READ_BACK")
        self.assertTrue(replay["current_state_matches_receipt"])
        for changes in ({"manifest_path": str(Path(self.temp.name)/"another.json")}, {"expected_digest": "f"*64}, {"operator_id": self.operator.pk+100}):
            with self.assertRaises(CommandError):
                apply_backfill(**{**options, **changes})
        self.assertEqual(LegacyDomainBackfillBatch.objects.count(), 1)

    def test_wrong_database_operator_mapping_and_target_identity(self):
        options = self.options()
        for override in ({"expected_database": "wrong"}, {"operator_id": None}, {"environment": ""}, {"code_baseline": "bad"}):
            with self.assertRaises(CommandError):
                apply_backfill(**{**options, **override})
        for field in ("id", "slug", "name"):
            mapping = copy.deepcopy(self.mapping)
            mapping["tenants"][0][field] = 999999 if field == "id" else "wrong"
            with self.assertRaises(CommandError):
                dry_run(mapping)
        for tenants in ([], self.mapping["tenants"]*2):
            with self.assertRaises(CommandError):
                dry_run({**self.mapping, "tenants": tenants})
        named = SharingDomain.objects.create(name="Synthetic Domain", slug="different-existing-slug")
        with self.assertRaises(CommandError):
            dry_run(self.mapping)
        named.delete()
        domain = SharingDomain.objects.create(name="Existing", slug="synthetic-domain")
        with self.assertRaises(CommandError):
            dry_run(self.mapping)
        mapping = {**self.mapping, "domain": {"id": domain.pk, "name": "Wrong", "slug": domain.slug}}
        with self.assertRaises(CommandError):
            dry_run(mapping)

    def test_partial_correct_state_is_explicit_and_completed(self):
        domain = SharingDomain.objects.create(name="Synthetic Domain", slug="synthetic-domain")
        models.QuerySet.update(Tenant.objects.filter(pk=self.tenant.pk), sharing_domain=domain)
        mapping = {**self.mapping, "domain": {**self.mapping["domain"], "id": domain.pk}}
        options = self.options(mapping=mapping)
        self.assertEqual(options["mapping"]["domain"]["id"], domain.pk)
        apply_backfill(**options)
        self.assertEqual(PersonTenantAssignment.objects.get().tenant_id, self.tenant.pk)

    def test_stale_plan_and_mid_apply_failure_are_atomic(self):
        options = self.options()
        Organization.objects.filter(pk=self.org.pk).update(note="changed without relying on updated_at")
        with self.assertRaises(CommandError):
            apply_backfill(**options)
        self.assertEqual(SharingDomain.objects.count(), 0)
        self.assertEqual(LegacyDomainBackfillBatch.objects.get().state, "PREPARED")
        with patch("crm.services.domain_backfill.PersonTenantAssignment.objects._insert_for_backfill", side_effect=RuntimeError("synthetic interruption")):
            with self.assertRaises(CommandError):
                self.apply("interrupted")
        self.assertEqual(SharingDomain.objects.count(), 0)
        self.assertEqual(OrganizationTenantAssignment.objects.count(), 0)
        self.assertIsNone(Tenant.objects.get(pk=self.tenant.pk).sharing_domain_id)
        with self.assertRaises(DomainStructureError):
            OrganizationTenantAssignment.objects._insert_for_backfill([])

    def test_lost_file_acknowledgement_readback_proves_commit(self):
        from crm.services.domain_backfill import write_phone_backfill_manifest
        def fail_verified(path, payload):
            if payload["state"] == "COMMITTED_VERIFIED":
                raise OSError("synthetic lost acknowledgement")
            return write_phone_backfill_manifest(path, payload)
        options = self.options()
        with patch("crm.services.domain_backfill.write_phone_backfill_manifest", side_effect=fail_verified):
            with self.assertRaises(CommandError):
                apply_backfill(**options)
        replay = apply_backfill(**options)
        self.assertEqual(replay["state"], "COMMITTED_VERIFIED")
        self.assertEqual(PersonTenantAssignment.objects.count(), 1)
        self.assertEqual(json.loads(Path(options["manifest_path"]).read_text())["state"], "PREPARED")

    def test_inbound_scope_mismatch_and_extra_assignment_are_blockers(self):
        PersonContact.objects.create(tenant=self.other, person=self.person, type="EMAIL", value="wrong@example.invalid")
        with self.assertRaises(CommandError):
            dry_run(self.mapping)
        PersonContact.objects.filter(tenant=self.other).delete()
        self.apply()
        domain = SharingDomain.objects.get()
        models.QuerySet.update(Tenant.objects.filter(pk=self.other.pk), sharing_domain=domain)
        raw_assignment(PersonTenantAssignment, self.person.pk, self.other.pk)
        with self.assertRaises(CommandError):
            dry_run(self.bound_mapping())

    def test_orm_default_base_reverse_bulk_and_instance_writes_are_closed(self):
        self.apply()
        for model, entity, field in ((OrganizationTenantAssignment, self.org, "organization"), (PersonTenantAssignment, self.person, "person")):
            values = {field: entity, "tenant": self.tenant}
            for manager in (model.objects, model._default_manager, model._base_manager, entity.tenant_assignments):
                for operation in (lambda m=manager: m.create(**values), lambda m=manager: m.get_or_create(**values),
                                  lambda m=manager: m.update_or_create(**values), lambda m=manager: m.update(tenant=self.other),
                                  lambda m=manager: m.delete(), lambda m=manager: m.bulk_create([model(**values)]),
                                  lambda m=manager: m.bulk_update([model(**values)], ["tenant"])):
                    with self.assertRaises(DomainStructureError):
                        operation()
            with self.assertRaises(DomainStructureError):
                model(**values).save()
            with self.assertRaises(DomainStructureError):
                model.objects.get().delete()
        for obj in (self.tenant, self.org, self.person):
            for manager in (type(obj).objects, type(obj)._base_manager):
                with self.assertRaises(DomainStructureError):
                    manager.filter(pk=obj.pk).update(sharing_domain=None)
                with self.assertRaises(DomainStructureError):
                    manager.bulk_update([obj], ["sharing_domain"])
            obj.sharing_domain = None
            with self.assertRaises(DomainStructureError):
                obj.save()

    def test_raw_sql_structure_mutation_is_rejected(self):
        self.apply()
        for sql, params in (
            ("UPDATE crm_tenant SET sharing_domain_id=NULL WHERE id=%s", [self.tenant.pk]),
            ("UPDATE crm_organization SET tenant_id=%s WHERE id=%s", [self.other.pk, self.org.pk]),
            ("UPDATE crm_person SET tenant_id=%s WHERE id=%s", [self.other.pk, self.person.pk]),
            ("UPDATE crm_organizationtenantassignment SET tenant_id=%s", [self.other.pk]),
            ("DELETE FROM crm_persontenantassignment", []),
        ):
            with self.assertRaises(IntegrityError), transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(sql, params)
        with self.assertRaises(IntegrityError), transaction.atomic():
            raw_assignment(PersonTenantAssignment, self.person.pk, self.other.pk)
        with self.assertRaises(IntegrityError), transaction.atomic():
            models.QuerySet.bulk_create(Tenant.objects.all(), [Tenant(name="Wrong", slug="wrong", sharing_domain_id=999999)])
            connection.check_constraints()

    def test_legacy_edit_create_admin_and_api_deletion(self):
        self.apply()
        client = APIClient()
        client.force_authenticate(self.operator)
        for model, obj, route, field in ((Organization, self.org, "organizations", "name"), (Person, self.person, "persons", "full_name")):
            url = f"/api/tenants/{self.tenant.pk}/{route}/"
            self.assertEqual(client.patch(f"{url}{obj.pk}/", {field: "Edited"}, format="json").status_code, 200)
            self.assertEqual(client.delete(f"{url}{obj.pk}/").status_code, 409)
            response = client.post(url, {field: "New"}, format="json")
            self.assertEqual(response.status_code, 201, response.content)
            new = model.objects.get(pk=response.json()["id"])
            self.assertIsNone(new.sharing_domain_id)
            self.assertEqual(new.tenant_assignments.count(), 0)
            request = RequestFactory().post("/admin/")
            request.user = self.operator
            current = model.objects.get(pk=obj.pk)
            form_class = admin.site._registry[model].get_form(request, current)
            self.assertTrue(form_class.base_fields["tenant"].disabled)
            data = model_to_dict(current)
            data["tenant"] = self.other.pk
            form = form_class(data=data, instance=current)
            self.assertTrue(form.is_valid(), form.errors)
            form.save()
            self.assertEqual(model.objects.get(pk=obj.pk).tenant_id, self.tenant.pk)
        catchup = self.options("catchup", self.bound_mapping())
        apply_backfill(**catchup)
        self.assertEqual(OrganizationTenantAssignment.objects.count(), 2)
        self.assertEqual(PersonTenantAssignment.objects.count(), 2)

    def test_organization_only_and_person_only_parent_deletion(self):
        # Separate fixtures prevent one assignment model masking the other.
        for index, model, assignment, field, name in ((1, Organization, OrganizationTenantAssignment, "organization", "name"), (2, Person, PersonTenantAssignment, "person", "full_name")):
            t = Tenant.objects.create(name=f"Isolated {index}", slug=f"isolated-{index}")
            obj = model.objects.create(tenant=t, **{name: "Synthetic"})
            d = SharingDomain.objects.create(name=f"D {index}", slug=f"d-{index}")
            models.QuerySet.update(Tenant.objects.filter(pk=t.pk), sharing_domain=d)
            models.QuerySet.update(model.objects.filter(pk=obj.pk), sharing_domain=d)
            raw_assignment(assignment, obj.pk, t.pk)
            for parent in (obj, t):
                for operation in (parent.delete, lambda p=parent: type(p).objects.filter(pk=p.pk).delete(),
                                  lambda p=parent: admin.site._registry[type(p)].delete_model(RequestFactory().get("/"), p)):
                    with self.assertRaises(ProtectedError):
                        operation()
                with self.assertRaises(IntegrityError), transaction.atomic():
                    with connection.cursor() as cursor:
                        cursor.execute(f'DELETE FROM "{parent._meta.db_table}" WHERE id=%s', [parent.pk])
                        connection.check_constraints()
                self.assertTrue(type(parent).objects.filter(pk=parent.pk).exists())

    def thread(self, fn):
        errors = []
        def run():
            close_old_connections()
            try:
                fn()
            except BaseException as error:
                errors.append(error)
            finally:
                connections.close_all()
        thread = threading.Thread(target=run)
        thread.start()
        return thread, errors

    def test_dry_run_reads_one_snapshot_despite_concurrent_edit(self):
        original = dry_run(self.mapping)["plan"]["digest"]
        snapshot = _snapshot
        def changed_snapshot():
            thread, errors = self.thread(lambda: Organization.objects.filter(pk=self.org.pk).update(note="concurrent"))
            thread.join(3)
            self.assertFalse(thread.is_alive())
            self.assertFalse(errors)
            return snapshot()
        with patch("crm.services.domain_backfill._snapshot", side_effect=changed_snapshot):
            self.assertEqual(dry_run(self.mapping)["plan"]["digest"], original)
        self.assertNotEqual(dry_run(self.mapping)["plan"]["digest"], original)

    def test_apply_replans_after_waiting_for_concurrent_edit(self):
        options = self.options()
        started = threading.Event()
        with transaction.atomic():
            Organization.objects.filter(pk=self.org.pk).update(note="uncommitted concurrent edit")
            thread, errors = self.thread(lambda: (started.set(), apply_backfill(**options)))
            self.assertTrue(started.wait(3))
            # The apply must be waiting for our ROW EXCLUSIVE table lock.
            self._wait_for_lock_waiter()
        thread.join(8)
        self.assertFalse(thread.is_alive())
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], CommandError)
        self.assertEqual(SharingDomain.objects.count(), 0)

    def _wait_for_lock_waiter(self):
        import time
        deadline = time.monotonic()+3
        while time.monotonic() < deadline:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_stat_clear_snapshot()")
                cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND wait_event_type='Lock' AND pid<>pg_backend_pid()")
                if cursor.fetchone()[0]:
                    return
            time.sleep(.02)
        self.fail("Expected a separate PostgreSQL connection waiting for a lock")

    def test_assignment_and_parent_change_both_connection_orders(self):
        self.apply()
        domain = SharingDomain.objects.get()
        for entity in (self.org, self.person):
            assignment = OrganizationTenantAssignment if isinstance(entity, Organization) else PersonTenantAssignment
            # Wrong/unbound target tenant: a concurrent binding must be read AFTER its lock.
            target = Tenant.objects.create(name=f"Target {entity._meta.model_name}", slug=f"target-{entity._meta.model_name}")
            with transaction.atomic():
                models.QuerySet.update(Tenant.objects.filter(pk=target.pk), sharing_domain=domain)
                thread, errors = self.thread(lambda: raw_assignment(assignment, entity.pk, target.pk))
                self._wait_for_lock_waiter()
            thread.join(5)
            self.assertFalse(thread.is_alive())
            self.assertFalse(errors)
            # Opposite order: assignment holds FOR SHARE; domain rebinding waits then fails.
            other_domain = SharingDomain.objects.create(name=f"Other {target.pk}", slug=f"other-{target.pk}")
            with transaction.atomic():
                another = Tenant.objects.create(name=f"Another {target.pk}", slug=f"another-{target.pk}")
                models.QuerySet.update(Tenant.objects.filter(pk=another.pk), sharing_domain=domain)
            with transaction.atomic():
                raw_assignment(assignment, entity.pk, another.pk)
                thread, errors = self.thread(lambda: models.QuerySet.update(Tenant.objects.filter(pk=another.pk), sharing_domain=other_domain))
                self._wait_for_lock_waiter()
            thread.join(5)
            self.assertFalse(thread.is_alive())
            self.assertEqual(len(errors), 1)
            self.assertIsInstance(errors[0], IntegrityError)

    def test_concurrent_same_batch_has_one_application(self):
        options = self.options()
        gate = threading.Barrier(2)
        results = []
        def apply():
            gate.wait(3)
            results.append(apply_backfill(**options))
        one, errors1 = self.thread(apply)
        two, errors2 = self.thread(apply)
        one.join(8); two.join(8)
        self.assertFalse(one.is_alive() or two.is_alive())
        self.assertFalse(errors1+errors2)
        self.assertEqual(LegacyDomainBackfillBatch.objects.count(), 1)
        self.assertEqual(OrganizationTenantAssignment.objects.count(), 1)
        self.assertEqual(sorted(r["mode"] for r in results), ["APPLY", "READ_BACK"])

    def test_read_only_snapshot_rejects_accidental_write(self):
        def accidental_write(mapping):
            Tenant.objects.create(name="Must not persist", slug="must-not-persist")
        from django.db import DatabaseError
        with patch("crm.services.domain_backfill._plan", side_effect=accidental_write):
            with self.assertRaises(DatabaseError):
                dry_run(self.mapping)
        self.assertFalse(Tenant.objects.filter(slug="must-not-persist").exists())

    def test_scope_grant_closes_on_failure_and_rejects_other_objects(self):
        with transaction.atomic():
            with _legacy_assignment_scope([]):
                with self.assertRaises(DomainStructureError):
                    PersonTenantAssignment.objects._insert_for_backfill([PersonTenantAssignment(person=self.person, tenant=self.tenant)])
            with self.assertRaises(DomainStructureError):
                PersonTenantAssignment.objects._insert([], [])
            with self.assertRaises(DomainStructureError):
                PersonTenantAssignment.objects.all()._raw_delete("default")

    def test_lock_timeout_leaves_no_semantic_writes(self):
        options = self.options()
        with transaction.atomic():
            Organization.objects.filter(pk=self.org.pk).update(note="hold lock")
            with patch("crm.services.domain_backfill.LOCK_TIMEOUT", "100ms"):
                thread, errors = self.thread(lambda: apply_backfill(**options))
                thread.join(4)
                self.assertFalse(thread.is_alive())
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], CommandError)
        self.assertEqual(SharingDomain.objects.count(), 0)
        self.assertEqual(LegacyDomainBackfillBatch.objects.get().state, "PREPARED")

    def test_concurrent_legacy_insert_invalidates_approved_scope(self):
        options = self.options()
        with transaction.atomic():
            Organization.objects.create(tenant=self.tenant, name="Concurrent new legacy actor")
            thread, errors = self.thread(lambda: apply_backfill(**options))
            self._wait_for_lock_waiter()
        thread.join(8)
        self.assertFalse(thread.is_alive())
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], CommandError)
        self.assertEqual(SharingDomain.objects.count(), 0)

    def test_readback_distinguishes_committed_history_from_later_edit(self):
        options = self.options()
        self.apply()
        Organization.objects.filter(pk=self.org.pk).update(note="legitimate later edit")
        report = read_batch(environment=options["environment"], expected_database=options["expected_database"],
                            batch_id=options["batch_id"], operator_id=self.operator.pk)
        self.assertEqual(report["state"], "COMMITTED_VERIFIED")
        self.assertFalse(report["current_state_matches_receipt"])

    def test_reverse_rejects_semantic_state(self):
        from django.db.migrations.executor import MigrationExecutor
        self.apply()
        with self.assertRaises(RuntimeError):
            MigrationExecutor(connection).migrate([("crm", "0033_domain_assignment_foundation")])
        self.assertEqual(PersonTenantAssignment.objects.count(), 1)

    def test_profile_binding_and_assignment_use_separate_connections(self):
        self.apply()
        domain = SharingDomain.objects.get()
        for model, assignment, label in ((Organization, OrganizationTenantAssignment, "name"), (Person, PersonTenantAssignment, "full_name")):
            obj = model.objects.create(tenant=self.tenant, **{label: "Concurrent unbound"})
            with transaction.atomic():
                models.QuerySet.update(model.objects.filter(pk=obj.pk), sharing_domain=domain)
                thread, errors = self.thread(lambda: raw_assignment(assignment, obj.pk, self.tenant.pk))
                self._wait_for_lock_waiter()
            thread.join(5)
            self.assertFalse(thread.is_alive())
            self.assertFalse(errors)
            second_target = Tenant.objects.create(name=f"Second {model._meta.model_name}", slug=f"second-{model._meta.model_name}")
            models.QuerySet.update(Tenant.objects.filter(pk=second_target.pk), sharing_domain=domain)
            with transaction.atomic():
                raw_assignment(assignment, obj.pk, second_target.pk)
                thread, errors = self.thread(lambda: models.QuerySet.update(model.objects.filter(pk=obj.pk), sharing_domain=None))
                self._wait_for_lock_waiter()
            thread.join(5)
            self.assertFalse(thread.is_alive())
            self.assertEqual(len(errors), 1)
            self.assertIsInstance(errors[0], IntegrityError)

    def test_bound_legacy_reads_and_public_do_not_enable_sharing(self):
        self.apply()
        user = get_user_model().objects.create_user(username="synthetic-reader", password="synthetic")
        TenantMembership.objects.create(user=user, tenant=self.tenant, role=TenantMembership.Role.LESER)
        client = APIClient()
        client.force_authenticate(user)
        for route, obj in (("organizations", self.org), ("persons", self.person)):
            response = client.get(f"/api/tenants/{self.tenant.pk}/{route}/{obj.pk}/")
            self.assertEqual(response.status_code, 200)
            for key in ("sharing_domain", "sharing_domain_id", "tenant_assignments"):
                self.assertNotIn(key, response.json())
        self.assertEqual(client.get(f"/api/tenants/{self.tenant.pk}/persons/{self.foreign.pk}/").status_code, 404)
        client.force_authenticate(user=None)
        response = client.get("/api/public/actors/")
        self.assertEqual(response.status_code, 200)
        rows = response.json()
        if isinstance(rows, dict):
            rows = rows["results"]
        self.assertEqual(len(rows), 1)
        self.assertNotIn("sharing_domain", rows[0])
        self.assertNotIn("tenant_assignments", rows[0])
        self.assertEqual(client.get("/public/actors/").status_code, 200)

    def test_two_different_batches_cannot_apply_the_same_stale_plan(self):
        first = self.options("first")
        second = {**first, "batch_id": "second", "manifest_path": str(Path(self.temp.name)/"second.json")}
        gate = threading.Barrier(2)
        results = []
        def apply(options):
            gate.wait(3)
            results.append(apply_backfill(**options))
        one, errors1 = self.thread(lambda: apply(first))
        two, errors2 = self.thread(lambda: apply(second))
        one.join(8); two.join(8)
        self.assertFalse(one.is_alive() or two.is_alive())
        self.assertEqual(len(results), 1)
        self.assertEqual(len(errors1+errors2), 1)
        self.assertIsInstance((errors1+errors2)[0], CommandError)
        self.assertEqual(OrganizationTenantAssignment.objects.count(), 1)
        self.assertEqual(PersonTenantAssignment.objects.count(), 1)
