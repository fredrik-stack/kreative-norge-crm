import copy
import json
import tempfile
import threading
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import DatabaseError, OperationalError, connection, connections, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase, override_settings
from rest_framework.test import APIClient

from crm.models import (
    Organization, OrganizationNoteOverlay, OrganizationTenantAssignment,
    Person, PersonNoteOverlay, PersonTenantAssignment, SharingDomain, Tag,
    Tenant, TenantNoteCopyBatch,
)
from crm.note_overlays import NoteOverlayError
from crm.services import tenant_note_copy as service
from crm.test_phase6a1_foundation import fixture_assignment, fixture_bound
from crm import test_phase6a2_backfill as backfill_tests


@override_settings(TENANT_NOTE_OVERLAYS_ENABLED=True, SECURE_SSL_REDIRECT=False)
class TenantNoteCopyTests(TransactionTestCase):
    thread = backfill_tests.LegacyBackfillTests.thread
    _wait_for_lock_waiter = backfill_tests.LegacyBackfillTests._wait_for_lock_waiter

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.operator = get_user_model().objects.create_superuser(username="synthetic-note-operator")
        self.domain = SharingDomain.objects.create(name="Synthetic", slug="synthetic")
        self.tenant = fixture_bound(Tenant, name="Synthetic", slug="synthetic", sharing_domain=self.domain)
        self.empty = fixture_bound(Tenant, name="Empty", slug="empty", sharing_domain=self.domain)
        self.mapping = {"domain": {"id": self.domain.pk, "name": self.domain.name, "slug": self.domain.slug},
                        "tenants": [{"id": t.pk, "name": t.name, "slug": t.slug} for t in (self.tenant, self.empty)]}
        self.profiles = []
        self.values = (None, "", " \n\t", "Æ exact\nline\r\nend ", "NULL")
        for model, assignment, _, field in service.CASES:
            for value in self.values:
                label = {"name": "Synthetic"} if model is Organization else {"full_name": "Synthetic"}
                profile = fixture_bound(model, tenant=self.tenant, sharing_domain=self.domain, note=value, **label)
                assigned = fixture_assignment(assignment, **{field: profile.pk, "tenant": self.tenant})
                self.profiles.append((profile, assigned))
        self.unbound = Organization.objects.create(tenant=self.tenant, name="Deferred", note="deferred private")
        Tag.objects.create(tenant=self.tenant, name="Synthetic private tag")
        self.context = dict(environment="synthetic", expected_database=service.database_identity(),
                            operator_id=self.operator.pk, code_baseline="a" * 40)

    def options(self, batch="synthetic-batch"):
        plan = service.dry_run(self.mapping, **self.context)["plan"]
        return dict(mapping=self.mapping, **self.context, expected_digest=plan["digest"],
                    batch_id=batch, manifest_path=str(Path(self.temp.name) / (batch + ".json")))

    def read(self, batch="synthetic-batch"):
        return service.read_batch(**{k: self.context[k] for k in ("environment", "expected_database", "operator_id")},
                                  batch_id=batch)

    def assert_empty(self):
        self.assertEqual(OrganizationNoteOverlay.objects.count(), 0)
        self.assertEqual(PersonNoteOverlay.objects.count(), 0)

    def test_exact_copy_null_absence_and_all_legacy_preservation(self):
        before = service._snapshot()
        result = service.apply_copy(**self.options())
        self.assertEqual(result["state"], "COMMITTED_VERIFIED")
        self.assertEqual(len(result["receipt"]["changes"]), 8)
        for profile, assigned in self.profiles:
            overlay = OrganizationNoteOverlay if isinstance(profile, Organization) else PersonNoteOverlay
            if profile.note is None:
                self.assertFalse(overlay.objects.filter(assignment=assigned).exists())
            else:
                self.assertEqual(overlay.objects.get(assignment=assigned).note, profile.note)
        after = service._snapshot()
        for table in before:
            if table not in service.OVERLAY_TABLES:
                self.assertEqual(before[table], after[table])
        read = self.read()
        self.assertTrue(read["source_matches_plan"])
        self.assertTrue(read["targets_match_receipt"])
        self.assertTrue(read["current_state_matches_receipt"])
        private = Path(self.options("unused")["manifest_path"]).parent / "synthetic-batch.json"
        self.assertEqual(private.stat().st_mode & 0o777, 0o600)
        self.assertTrue(Path(str(private) + ".verified.json").exists())

    def test_dry_run_cli_has_no_db_writes_private_plan_and_sanitized_stdout(self):
        mapping_path = Path(self.temp.name) / "mapping.json"
        mapping_path.write_text(json.dumps(self.mapping))
        plan_path = Path(self.temp.name) / "plan.json"
        out = StringIO()
        statements = []
        def record(execute, sql, params, many, context):
            statements.append(sql.strip().split()[0].upper())
            return execute(sql, params, many, context)
        with connection.execute_wrapper(record):
            call_command("copy_legacy_tenant_notes", mapping=str(mapping_path), plan_path=str(plan_path),
                         **self.context, stdout=out)
        self.assertFalse({"INSERT", "UPDATE", "DELETE"}.intersection(statements))
        self.assertEqual(TenantNoteCopyBatch.objects.count(), 0)
        public, private = json.loads(out.getvalue()), json.loads(plan_path.read_text())
        self.assertEqual(public["state"], "READY")
        self.assertEqual(public["writes"], 0)
        self.assertNotIn("sources", public)
        self.assertIn("sources", private["plan"])
        self.assertNotIn(self.values[3], plan_path.read_text())
        self.assertEqual(plan_path.stat().st_mode & 0o777, 0o600)
        call_options = dict(mapping=str(mapping_path), plan_path=str(plan_path), **self.context)
        with self.assertRaises(CommandError):
            call_command("copy_legacy_tenant_notes", **call_options)

    def test_gate_off_blocks_new_apply_but_allows_read_only_replay(self):
        options = self.options()
        with override_settings(TENANT_NOTE_OVERLAYS_ENABLED=False):
            with self.assertRaises(NoteOverlayError):
                service.apply_copy(**options)
        self.assertFalse(TenantNoteCopyBatch.objects.exists())
        service.apply_copy(**options)
        with override_settings(TENANT_NOTE_OVERLAYS_ENABLED=False):
            self.assertEqual(service.apply_copy(**options)["mode"], "READ_BACK")

    def test_external_transaction_and_read_only_snapshot_write_are_rejected(self):
        options = self.options()
        with transaction.atomic(), self.assertRaises(CommandError):
            service.apply_copy(**options)
        connection.set_autocommit(False)
        try:
            with self.assertRaises(CommandError):
                service.apply_copy(**options)
        finally:
            connection.rollback()
            connection.set_autocommit(True)
        def accidental_write(*args):
            Organization.objects.filter(pk=self.unbound.pk).update(note="not allowed")
        with patch.object(service, "_plan", side_effect=accidental_write):
            with self.assertRaises(DatabaseError):
                service.dry_run(self.mapping, **self.context)
        self.assertFalse(TenantNoteCopyBatch.objects.exists())

    def test_all_existing_target_values_are_conflicts_including_null_sources(self):
        profile, assigned = self.profiles[0]
        for value in self.values:
            with self.subTest(value=value):
                row = OrganizationNoteOverlay.objects.create(assignment=assigned, note=value)
                options = self.options()
                report = service.dry_run(self.mapping, **self.context)
                self.assertEqual(report["state"], "BLOCKED")
                with self.assertRaises(CommandError):
                    service.apply_copy(**options)
                self.assertEqual(OrganizationNoteOverlay.objects.get(pk=row.pk).note, value)
                row.delete()
                TenantNoteCopyBatch.objects.all().delete()

    def test_extra_assignment_never_copies_to_another_tenant(self):
        profile, _ = self.profiles[1]
        fixture_assignment(OrganizationTenantAssignment, organization=profile, tenant=self.empty)
        report = service.dry_run(self.mapping, **self.context)
        self.assertEqual(report["state"], "BLOCKED")
        with self.assertRaises(CommandError):
            service.apply_copy(**self.options())
        self.assert_empty()

    def test_missing_and_corrupt_assignments_are_visible_blockers(self):
        missing = fixture_bound(Person, full_name="Missing", tenant=self.tenant, sharing_domain=self.domain, note="copy")
        report = service.dry_run(self.mapping, **self.context)
        self.assertTrue(any(b.get("profile_id") == missing.pk for b in report["plan"]["blockers"]))
        other_domain = SharingDomain.objects.create(name="Other", slug="other")
        foreign = fixture_bound(Tenant, name="Other", slug="other", sharing_domain=other_domain)
        # Deliberately corrupt a synthetic endpoint to prove inspection does not
        # filter it away. Real database triggers remain enabled outside this tx.
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute("SET LOCAL session_replication_role = replica")
            cursor.execute("INSERT INTO crm_persontenantassignment (person_id,tenant_id,created_at,updated_at) VALUES (%s,%s,now(),now())", [missing.pk, foreign.pk])
        report = service.dry_run(self.mapping, **self.context)
        self.assertIn("ASSIGNMENT_SCOPE", {b["reason"] for b in report["plan"]["blockers"]})
        with self.assertRaises(CommandError):
            service.apply_copy(**self.options())
        self.assert_empty()

    def test_context_scope_and_private_paths_fail_closed(self):
        options = self.options()
        for changes in ({"expected_database": "wrong"}, {"operator_id": None}, {"environment": ""},
                        {"code_baseline": "invalid"}, {"manifest_path": "relative.json"},
                        {"batch_id": "../bad"}, {"expected_digest": "bad"}):
            with self.subTest(changes=changes), self.assertRaises(CommandError):
                service.apply_copy(**{**options, **changes})
        for section, field, value in (("domain", "id", None), ("domain", "name", "wrong")):
            mapping = copy.deepcopy(self.mapping)
            mapping[section][field] = value
            with self.assertRaises(CommandError):
                service.dry_run(mapping, **self.context)
        mapping = copy.deepcopy(self.mapping)
        mapping["tenants"][0]["slug"] = "wrong"
        with self.assertRaises(CommandError):
            service.dry_run(mapping, **self.context)
        symlink = Path(self.temp.name) / "link.json"
        symlink.symlink_to(Path(self.temp.name) / "missing")
        with self.assertRaises(CommandError):
            service.apply_copy(**{**options, "manifest_path": str(symlink)})
        self.assert_empty()

    def test_orphan_profile_and_tenant_endpoints_cannot_disappear_from_inspection(self):
        for model, assignment, _, field in service.CASES:
            profile = next(p for p, _ in self.profiles if isinstance(p, model))
            for missing_profile in (True, False):
                with self.subTest(model=model, missing_profile=missing_profile):
                    with transaction.atomic(), connection.cursor() as cursor:
                        cursor.execute("SET LOCAL session_replication_role = replica")
                        cursor.execute(f'''INSERT INTO "{assignment._meta.db_table}"
                            ({field},tenant_id,created_at,updated_at)
                            VALUES (%s,%s,now(),now()) RETURNING id''',
                            [999999 if missing_profile else profile.pk,
                             self.tenant.pk if missing_profile else 999999])
                        orphan_id = cursor.fetchone()[0]
                    report = service.dry_run(self.mapping, **self.context)
                    self.assertEqual(report["state"], "BLOCKED")
                    self.assertTrue(any(b["model"] == model._meta.model_name
                        and b.get("assignment_id") == orphan_id and b["reason"] == "ASSIGNMENT_SCOPE"
                        for b in report["plan"]["blockers"]))
                    with self.assertRaises(CommandError):
                        service.apply_copy(**self.options(f"orphan-{model._meta.model_name}-{missing_profile}"))
                    self.assert_empty()

    def test_stale_edit_insert_or_overlay_stops_without_semantic_writes(self):
        for change in (lambda: Organization.objects.filter(pk=self.profiles[1][0].pk).update(note="new source"),
                       lambda: Organization.objects.create(tenant=self.tenant, name="New NULL"),
                       lambda: OrganizationNoteOverlay.objects.create(assignment=self.profiles[0][1], note=None)):
            options = self.options("stale-" + str(TenantNoteCopyBatch.objects.count()))
            change()
            with self.assertRaises(CommandError):
                service.apply_copy(**options)
            self.assertEqual(PersonNoteOverlay.objects.count(), 0)
            self.assertEqual(TenantNoteCopyBatch.objects.get(batch_id=options["batch_id"]).state, "PREPARED")

    def test_failure_mid_copy_is_atomic_and_prepared_never_auto_retries(self):
        options = self.options()
        before = service._snapshot()
        create = OrganizationNoteOverlay.objects.create
        calls = []
        def fail_second(**kwargs):
            calls.append(kwargs)
            if len(calls) == 2:
                raise RuntimeError("synthetic private failure")
            return create(**kwargs)
        with patch.object(OrganizationNoteOverlay.objects, "create", side_effect=fail_second):
            with self.assertRaises(CommandError):
                service.apply_copy(**options)
        self.assertEqual(len(calls), 2)
        self.assertEqual(service._snapshot(), before)
        self.assertEqual(service.apply_copy(**options)["state"], "PREPARED")
        self.assert_empty()

    def test_replay_is_read_only_and_rejects_changed_request_or_path(self):
        options = self.options()
        service.apply_copy(**options)
        statements = []
        def record(execute, sql, params, many, context):
            statements.append(sql.strip().split()[0].upper())
            return execute(sql, params, many, context)
        with connection.execute_wrapper(record), patch.object(service, "_plan") as plan:
            replay = service.apply_copy(**options)
        plan.assert_not_called()
        self.assertFalse({"INSERT", "UPDATE", "DELETE"}.intersection(statements))
        self.assertTrue(replay["current_state_matches_receipt"])
        for changes in ({"manifest_path": str(Path(self.temp.name) / "other.json")},
                        {"code_baseline": "b" * 40}, {"expected_digest": "f" * 64}):
            with self.assertRaises(CommandError):
                service.apply_copy(**{**options, **changes})

    def test_readback_separates_history_source_and_target_drift(self):
        service.apply_copy(**self.options())
        Organization.objects.filter(pk=self.profiles[1][0].pk).update(note="later legacy edit")
        read = self.read()
        self.assertEqual(read["state"], "COMMITTED_VERIFIED")
        self.assertFalse(read["source_matches_plan"])
        self.assertTrue(read["targets_match_receipt"])
        PersonNoteOverlay.objects.all().update(note=None)
        self.assertFalse(self.read()["targets_match_receipt"])
        with self.assertRaises(CommandError):
            self.read("missing")

    def _lost_commit(self, actual_commit):
        options = self.options()
        before = service._snapshot()
        db = connections["default"]
        self.addCleanup(db.close)
        real_commit = db._commit
        boundaries = []
        def commit():
            batch = TenantNoteCopyBatch.objects.get(batch_id=options["batch_id"])
            boundaries.append(batch.state)
            if batch.state == "PREPARED":
                return real_commit()
            self.assertEqual(len(batch.receipt["changes"]), 8)
            self.assertEqual(batch.receipt["after"], service._snapshot())
            observer = db.Database.connect(**db.get_connection_params())
            try:
                observer.autocommit = True
                with observer.cursor() as cursor:
                    cursor.execute("SELECT state FROM crm_tenantnotecopybatch")
                    self.assertEqual(cursor.fetchone()[0], "PREPARED")
                    cursor.execute("SELECT count(*) FROM crm_organizationnoteoverlay")
                    self.assertEqual(cursor.fetchone()[0], 0)
            finally:
                observer.close()
            if actual_commit:
                real_commit()
            db.connection.close()
            raise OperationalError("synthetic lost COMMIT response")
        with patch.object(db, "_commit", side_effect=commit):
            with self.assertRaises(CommandError):
                service.apply_copy(**options)
        db.close()
        self.assertEqual(boundaries, ["PREPARED", "COMMITTED_VERIFIED"])
        result = self.read()
        self.assertEqual(result["state"], "COMMITTED_VERIFIED" if actual_commit else "PREPARED")
        if actual_commit:
            self.assertTrue(result["current_state_matches_receipt"])
        else:
            self.assertEqual(service._snapshot(), before)
        with patch.object(service, "_plan") as plan:
            self.assertEqual(service.apply_copy(**options), result)
        plan.assert_not_called()

    def test_lost_commit_response_after_actual_commit(self):
        self._lost_commit(True)

    def test_lost_commit_response_without_actual_commit(self):
        self._lost_commit(False)

    def test_lost_file_ack_is_committed_and_cli_errors_are_sanitized(self):
        options = self.options()
        writer = service.write_phone_backfill_manifest
        def fail_ack(path, report):
            if report["state"] == "COMMITTED_VERIFIED":
                raise OSError("SYNTHETIC-SECRET-NOTE")
            return writer(path, report)
        mapping = Path(self.temp.name) / "mapping.json"
        mapping.write_text(json.dumps(self.mapping))
        with patch.object(service, "write_phone_backfill_manifest", side_effect=fail_ack):
            with self.assertRaises(CommandError) as failure:
                call_command("copy_legacy_tenant_notes", apply=True, **{**options, "mapping": str(mapping)})
        self.assertNotIn("SYNTHETIC-SECRET", str(failure.exception))
        self.assertTrue(failure.exception.__suppress_context__)
        self.assertEqual(self.read()["state"], "COMMITTED_VERIFIED")

    def test_dry_run_has_one_snapshot_despite_concurrent_edit(self):
        original = self.options()["expected_digest"]
        snapshot = service._snapshot
        def edited():
            thread, errors = self.thread(lambda: Organization.objects.filter(pk=self.unbound.pk).update(note="later"))
            thread.join(3)
            self.assertFalse(thread.is_alive())
            self.assertFalse(errors)
            return snapshot()
        with patch.object(service, "_snapshot", side_effect=edited):
            self.assertEqual(self.options()["expected_digest"], original)
        self.assertNotEqual(self.options()["expected_digest"], original)

    def test_replan_after_waiting_for_concurrent_legacy_change(self):
        options = self.options()
        with transaction.atomic():
            Organization.objects.filter(pk=self.unbound.pk).update(note="concurrent")
            thread, errors = self.thread(lambda: service.apply_copy(**options))
            self._wait_for_lock_waiter()
        thread.join(8)
        self.assertFalse(thread.is_alive())
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], CommandError)
        self.assert_empty()

    def test_lock_timeout_leaves_only_prepared_evidence(self):
        options = self.options()
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute("LOCK TABLE crm_organization IN ROW EXCLUSIVE MODE")
            with patch.object(service, "LOCK_TIMEOUT", "100ms"):
                thread, errors = self.thread(lambda: service.apply_copy(**options))
                thread.join(4)
        self.assertFalse(thread.is_alive())
        self.assertEqual(len(errors), 1)
        self.assertEqual(self.read()["state"], "PREPARED")
        self.assert_empty()

    def test_concurrent_same_batch_and_different_batches_have_one_copy(self):
        for different in (False, True):
            with self.subTest(different=different):
                first = self.options("first-" + str(different))
                second = self.options("second") if different else first
                barrier = threading.Barrier(2)
                def apply(options):
                    barrier.wait(3)
                    service.apply_copy(**options)
                threads = [self.thread(lambda o=o: apply(o)) for o in (first, second)]
                for thread, _ in threads:
                    thread.join(10)
                    self.assertFalse(thread.is_alive())
                errors = [e for _, errors in threads for e in errors]
                self.assertEqual(len(errors), int(different))
                self.assertEqual(OrganizationNoteOverlay.objects.count(), 4)
                self.assertEqual(PersonNoteOverlay.objects.count(), 4)
                OrganizationNoteOverlay.objects.all().delete()
                PersonNoteOverlay.objects.all().delete()
                TenantNoteCopyBatch.objects.all().delete()

    def test_copy_does_not_change_legacy_api_admin_or_public_contract(self):
        service.apply_copy(**self.options())
        client = APIClient()
        client.force_authenticate(self.operator)
        for profile, assignment in (self.profiles[3], self.profiles[8]):
            kind = "organizations" if isinstance(profile, Organization) else "persons"
            url = f"/api/tenants/{self.tenant.pk}/{kind}/{profile.pk}/"
            response = client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["note"], profile.note)
            self.assertEqual(client.patch(url, {"note": "later legacy"}, format="json").status_code, 200)
            overlay = OrganizationNoteOverlay if kind == "organizations" else PersonNoteOverlay
            self.assertEqual(overlay.objects.get(assignment=assignment).note, profile.note)
        self.assertNotIn(TenantNoteCopyBatch, admin.site._registry)
        self.assertNotIn(OrganizationNoteOverlay, admin.site._registry)
        from crm.serializers_public import PublicActorSerializer
        self.assertNotIn("note", PublicActorSerializer().fields)


class TenantNoteCopyMigrationTests(TransactionTestCase):
    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_empty_reverse_forward_and_nonempty_reverse_guard(self):
        old, current = ("crm", "0035_tenant_note_overlay_foundation"), ("crm", "0036_tenant_note_copy_batch")
        before = {t: v for t, v in service._snapshot().items()}
        MigrationExecutor(connection).migrate([old])
        MigrationExecutor(connection).migrate([current])
        self.assertEqual(service._snapshot(), before)
        TenantNoteCopyBatch.objects.create(environment="synthetic", database_identity="synthetic", batch_id="prepared",
            request_digest="a"*64, plan_digest="b"*64, operator_id=1, code_baseline="a"*40, manifest_path="/private/synthetic")
        with self.assertRaises(RuntimeError), transaction.atomic():
            MigrationExecutor(connection).migrate([old])
        self.assertTrue(TenantNoteCopyBatch.objects.exists())
