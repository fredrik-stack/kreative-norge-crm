import copy
import io
import json
import os
import subprocess
import sys
import threading
from unittest.mock import patch

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import DatabaseError, close_old_connections, connection, connections, models, transaction
from django.test import SimpleTestCase, TransactionTestCase, override_settings
from rest_framework.test import APIClient, APIRequestFactory

from crm.models import Organization, OrganizationTenantAssignment, Person, PersonTenantAssignment, SharingDomain, Tenant, TenantMembership
from crm.services import domain_read_shadow as shadow
from crm.services.domain_backfill import database_identity
from crm.test_phase6a1_foundation import fixture_assignment, fixture_bound
from crm.views import OrganizationViewSet, PersonViewSet


@override_settings(SHARING_DOMAIN_SHADOW_ENABLED=True, SECURE_SSL_REDIRECT=False)
class DomainReadShadowTests(TransactionTestCase):
    def setUp(self):
        self.domain = SharingDomain.objects.create(**shadow.DOMAIN)
        self.tenants = {i: fixture_bound(Tenant, id=i, slug=s, name=n, sharing_domain=self.domain)
                        for i, s, n in shadow.TENANTS}
        self.options = dict(environment="test", expected_database=database_identity(), code_baseline="a" * 40)
        self.org = self.bound(Organization, OrganizationTenantAssignment, "organization", name="Same", email="shared@example.invalid")
        self.person = self.bound(Person, PersonTenantAssignment, "person", full_name="Same", email="shared@example.invalid", phone="same")

    def bound(self, model, assignment, field, tenant=1, **values):
        obj = fixture_bound(model, tenant=self.tenants[tenant], sharing_domain=self.domain, **values)
        fixture_assignment(assignment, **{field: obj, "tenant": self.tenants[tenant]})
        return obj

    def measure(self):
        return shadow.measure(**self.options)

    def row(self, report, model, tenant=1):
        return next(r for r in report["comparisons"] if r["model"] == model.__name__ and r["tenant_id"] == tenant)

    def command(self, **extra):
        out = io.StringIO()
        try:
            call_command("compare_domain_reads", stdout=out, **self.options, **extra)
            code = 0
        except CommandError as error:
            code = error.returncode
        return json.loads(out.getvalue()), code

    def test_full_equal_all_fourteen_and_empty_tenants(self):
        report, code = self.command()
        self.assertEqual((report["status"], code, report["completed_comparisons"]), ("FULL_EQUAL", 0, 14))
        self.assertTrue(report["transaction_read_only"])
        self.assertEqual(report["structural_deviations"], {})
        for model in (Organization, Person):
            self.assertEqual(self.row(report, model)["legacy_count"], 1)
            self.assertEqual(self.row(report, model, 9)["legacy_count"], 0)
        self.assertTrue(all(r["full_equal"] for r in report["comparisons"]))

    def test_null_partial_without_hidden_assignment_or_writes(self):
        org = Organization.objects.create(tenant=self.tenants[1], name="Private sentinel", note="secret note")
        Person.objects.create(tenant=self.tenants[2], full_name="Private sentinel")
        before = (list(Organization.objects.values()), list(Person.objects.values()), OrganizationTenantAssignment.objects.count())
        report, code = self.command()
        self.assertEqual((report["status"], code), ("EXPLAINED_PARTIAL", 2))
        self.assertEqual(self.row(report, Organization)["null_count"], 1)
        self.assertTrue(all(r["bound_equal"] for r in report["comparisons"]))
        org.refresh_from_db(); self.assertIsNone(org.sharing_domain_id)
        self.assertEqual(before, (list(Organization.objects.values()), list(Person.objects.values()), OrganizationTenantAssignment.objects.count()))
        self.assertNotIn("Private sentinel", json.dumps(report))
        self.assertNotIn("secret note", json.dumps(report))

    def test_same_signals_keep_both_profile_pks(self):
        self.bound(Organization, OrganizationTenantAssignment, "organization", name="Same", email="shared@example.invalid")
        self.bound(Person, PersonTenantAssignment, "person", full_name="Same", email="shared@example.invalid", phone="same")
        report = self.measure()
        self.assertEqual(report["status"], "FULL_EQUAL")
        for model in (Organization, Person):
            self.assertEqual(self.row(report, model)["assignment_count"], 2)

    def test_missing_own_assignment_is_failed(self):
        fixture_bound(Person, tenant=self.tenants[1], sharing_domain=self.domain, full_name="Unassigned")
        report, code = self.command()
        self.assertEqual((report["status"], code), ("FAILED", 3))
        self.assertIn("ASSIGNMENT_CARDINALITY", report["reason_codes"])

    def test_extra_assignment_is_not_hidden_by_legacy_filter(self):
        fixture_assignment(PersonTenantAssignment, person=self.person, tenant=self.tenants[2])
        report = self.measure()
        self.assertEqual(report["status"], "FAILED")
        self.assertEqual(self.row(report, Person, 2)["assignment_only_count"], 1)
        self.assertIn("ASSIGNMENT_TENANT_MISMATCH", report["reason_codes"])

    def test_equal_counts_different_pks_are_failed(self):
        other = self.bound(Person, PersonTenantAssignment, "person", tenant=2, full_name="Other")
        fixture_assignment(PersonTenantAssignment, person=self.person, tenant=self.tenants[2])
        # A missing own assignment is also schema-legal; do not weaken DB guards.
        third = fixture_bound(Person, tenant=self.tenants[2], sharing_domain=self.domain, full_name="Missing")
        report = self.measure()
        row = self.row(report, Person, 2)
        self.assertEqual(row["legacy_count"], row["assignment_count"])
        self.assertEqual((row["legacy_only_count"], row["assignment_only_count"]), (1, 1))
        self.assertFalse(row["full_equal"])
        self.assertEqual(report["status"], "FAILED")
        self.assertNotEqual(other.pk, third.pk)

    def test_wrong_nonnull_domain_is_structural_with_synthetic_impossible_rows(self):
        profiles, assignments, sets = shadow._load_model(Person, PersonTenantAssignment, "person")
        for key, value in (("sharing_domain_id", 99), ("tenant_id", 999), ("tenant__sharing_domain_id", None)):
            altered = copy.deepcopy(profiles); altered[0][key] = value
            _, deviations = shadow._compare_model("Person", altered, assignments, sets)
            self.assertTrue(deviations)
        altered = copy.deepcopy(profiles); altered[0]["sharing_domain_id"] = 99
        rows, deviations = shadow._compare_model("Person", altered, assignments, sets)
        self.assertIn("PROFILE_DOMAIN_MISMATCH", deviations)
        self.assertEqual(rows[0]["null_count"], 0)
        for key in ("tenant_domain", "profile_domain"):
            altered = copy.deepcopy(assignments); altered[0][key] = None
            _, deviations = shadow._compare_model("Person", profiles, altered, sets)
            self.assertIn("ASSIGNMENT_DOMAIN_MISMATCH", deviations)
        for key in ("tenant_id", "profile_tenant"):
            altered = copy.deepcopy(assignments); altered[0][key] = 999
            _, deviations = shadow._compare_model("Person", profiles, altered, sets)
            self.assertIn("ASSIGNMENT_TENANT_MISMATCH", deviations)

    def test_scope_identity_and_extra_domain_tenant_rejected(self):
        Tenant.objects.filter(pk=1).update(name="Unexpected private value")
        report, code = self.command()
        self.assertEqual((report["reason_codes"], code), (["SCOPE_MISMATCH"], 4))
        self.assertNotIn("Unexpected", json.dumps(report))
        Tenant.objects.filter(pk=1).update(name=shadow.TENANTS[0][2])
        fixture_bound(Tenant, id=99, slug="extra", name="Extra", sharing_domain=self.domain)
        self.assertEqual(self.command()[0]["reason_codes"], ["SCOPE_MISMATCH"])

    def test_database_mismatch_does_not_echo_expected_identity(self):
        self.options["expected_database"] = "secret-input"
        report, code = self.command()
        self.assertEqual((report["reason_codes"], code), (["DATABASE_MISMATCH"], 4))
        self.assertNotIn("secret-input", json.dumps(report))

    def test_gate_off_before_any_database_read(self):
        with override_settings(SHARING_DOMAIN_SHADOW_ENABLED=False):
            with self.assertNumQueries(0):
                report, code = self.command()
        self.assertEqual((report["reason_codes"], code), (["GATE_DISABLED"], 4))

    def test_outer_atomic_and_autocommit_off_rejected(self):
        with transaction.atomic():
            self.assertEqual(self.command()[0]["reason_codes"], ["OUTER_TRANSACTION"])
        connection.set_autocommit(False)
        try:
            self.assertEqual(self.command()[0]["reason_codes"], ["OUTER_TRANSACTION"])
        finally:
            connection.rollback(); connection.set_autocommit(True)

    def test_other_backend_and_invalid_context_fail_closed(self):
        with patch.object(connection, "vendor", "sqlite"):
            self.assertEqual(self.command()[0]["reason_codes"], ["POSTGRESQL_REQUIRED"])
        self.options["code_baseline"] = "private-input"
        self.assertEqual(self.command()[0]["reason_codes"], ["INVALID_CONTEXT"])

    def test_repeatable_read_concurrent_create_visible_only_next_measurement(self):
        original = shadow._load_model
        errors = []
        def insert():
            close_old_connections()
            try:
                Person.objects.create(tenant_id=1, full_name="Concurrent private sentinel")
            except Exception as error:
                errors.append(error)
            finally:
                connections.close_all()
        def concurrent_load(*args):
            if args[0] is Person:
                worker = threading.Thread(target=insert); worker.start(); worker.join(5)
                self.assertFalse(worker.is_alive()); self.assertFalse(errors)
            return original(*args)
        with patch.object(shadow, "_load_model", side_effect=concurrent_load):
            self.assertEqual(self.measure()["status"], "FULL_EQUAL")
        report = self.measure()
        self.assertEqual(report["status"], "EXPLAINED_PARTIAL")
        self.assertEqual(self.row(report, Person)["null_count"], 1)

    def test_read_only_rejects_accidental_write_and_resets_connection(self):
        def write():
            Person.objects.create(tenant_id=1, full_name="Must never persist")
        with patch.object(shadow, "_require_scope", side_effect=write):
            report, code = self.command()
        self.assertEqual((report["reason_codes"], code), (["MEASUREMENT_ERROR"], 4))
        self.assertFalse(Person.objects.filter(full_name="Must never persist").exists())
        self.assertEqual(self.measure()["status"], "FULL_EQUAL")

    def test_real_statement_timeout_is_sanitized(self):
        def timeout():
            with connection.cursor() as cursor:
                cursor.execute("SET LOCAL statement_timeout = '1ms'")
                cursor.execute("SELECT pg_sleep(0.05)")
        with patch.object(shadow, "_require_scope", side_effect=timeout):
            report, code = self.command()
        self.assertEqual((report["reason_codes"], code), (["MEASUREMENT_ERROR"], 4))
        self.assertEqual(report["completed_comparisons"], 0)

    def test_late_failure_never_publishes_partial_success_or_raw_exception(self):
        original = shadow._load_model
        def late_failure(*args):
            if args[0] is Person:
                raise DatabaseError("SECRET contact@example.invalid SQL parameters")
            return original(*args)
        out, err = io.StringIO(), io.StringIO()
        with patch.object(shadow, "_load_model", side_effect=late_failure):
            with self.assertRaises(CommandError):
                call_command("compare_domain_reads", stdout=out, stderr=err, traceback=True, **self.options)
        text = out.getvalue() + err.getvalue()
        self.assertNotIn("SECRET", text); self.assertNotIn("contact@example.invalid", text)
        self.assertEqual(json.loads(out.getvalue())["completed_comparisons"], 0)

    def test_actual_legacy_views_agree_and_api_never_starts_shadow(self):
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.create_user(username="reader")
        TenantMembership.objects.create(user=user, tenant=self.tenants[1], role=TenantMembership.Role.LESER)
        client = APIClient(); client.force_authenticate(user)
        for model, view, route in ((Organization, OrganizationViewSet, "organizations"), (Person, PersonViewSet, "persons")):
            for tenant in shadow.TENANT_IDS:
                instance = view(); instance.kwargs = {"tenant_id": tenant}; instance.request = APIRequestFactory().get("/")
                self.assertEqual(set(instance.get_queryset().values_list("pk", flat=True)),
                                 set(model.objects.filter(tenant_id=tenant).values_list("pk", flat=True)))
            with patch.object(shadow, "measure", side_effect=AssertionError("API must not measure")):
                with override_settings(SHARING_DOMAIN_SHADOW_ENABLED=False):
                    off = client.get(f"/api/tenants/1/{route}/")
                with override_settings(SHARING_DOMAIN_SHADOW_ENABLED=True):
                    on = client.get(f"/api/tenants/1/{route}/")
                self.assertEqual((off.status_code, off.json()), (on.status_code, on.json()))
                self.assertEqual(client.get(f"/api/tenants/2/{route}/").status_code, 403)


class ShadowConfigurationTests(SimpleTestCase):
    def test_fail_closed_bool_parser_and_default(self):
        for raw, expected in ((None, False), ("True", True), (" on ", True), ("False", False), ("private-invalid", False)):
            env = os.environ.copy(); env.pop("SHARING_DOMAIN_SHADOW_ENABLED", None)
            if raw is not None:
                env["SHARING_DOMAIN_SHADOW_ENABLED"] = raw
            result = subprocess.run([sys.executable, "-c", "from config.settings import SHARING_DOMAIN_SHADOW_ENABLED; print(SHARING_DOMAIN_SHADOW_ENABLED)"],
                                    env=env, capture_output=True, text=True, cwd=settings.BASE_DIR)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), str(expected))

    def test_cli_parser_errors_do_not_echo_input_to_stderr(self):
        result = subprocess.run([sys.executable, "manage.py", "compare_domain_reads", "--secret-private-input"],
                                capture_output=True, text=True, cwd=settings.BASE_DIR)
        self.assertEqual(result.returncode, 4)
        self.assertIn("INVALID_ARGUMENTS", result.stderr)
        self.assertNotIn("secret-private-input", result.stderr)
