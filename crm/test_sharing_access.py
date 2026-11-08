from datetime import timedelta
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import DatabaseError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.db.models import Value
from django.db.models.deletion import ProtectedError
from django.test import TestCase, TransactionTestCase, RequestFactory, override_settings
from django.utils import timezone

from crm.models import (
    Organization, OrganizationTenantAssignment, Person, PersonTenantAssignment,
    SharingDomain, Tenant, TenantMembership, SharingAgreement,
    SharingAgreementAcceptance, SharingAgreementRevocation, SharingAccessAudit,
)
from crm.permissions import get_user_tenant_role
from crm.services.sharing_access import assess_access, Capability
from crm.sharing_records import SharingRecordError
from crm.test_phase6a1_foundation import fixture_bound, fixture_assignment


@override_settings(SHARING_ACCESS_ENABLED=True)
class SharingAccessTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="synthetic-reader")
        self.author = get_user_model().objects.create_superuser(username="synthetic-author")
        self.domain = SharingDomain.objects.create(name="Synthetic", slug="synthetic")
        self.other_domain = SharingDomain.objects.create(name="Other", slug="other")
        self.tenant = fixture_bound(Tenant, name="First", slug="first", sharing_domain=self.domain)
        self.other = fixture_bound(Tenant, name="Second", slug="second", sharing_domain=self.domain)
        self.foreign = fixture_bound(Tenant, name="Foreign", slug="foreign", sharing_domain=self.other_domain)
        self.membership = TenantMembership.objects.create(user=self.user, tenant=self.tenant, role="redigerer")
        self.agreement = self.agree(self.domain)
        self.acceptance = self.accept(self.agreement)
        self.org = fixture_bound(Organization, tenant=self.tenant, sharing_domain=self.domain, name="Synthetic", note="private")
        self.assignment = fixture_assignment(OrganizationTenantAssignment, organization=self.org, tenant=self.tenant)

    def agree(self, domain, version=1, when=None):
        return SharingAgreement.objects.create(sharing_domain=domain, version=version,
            text="Synthetic test text only\nÆ ", effective_at=when or timezone.now()-timedelta(days=1), created_by=self.author)

    def accept(self, agreement, **kwargs):
        return SharingAgreementAcceptance.objects.create(agreement=agreement, user=kwargs.get("user", self.user), tenant=kwargs.get("tenant", self.tenant))

    def check(self, **kwargs):
        args = dict(user_id=self.user.pk, tenant_id=self.tenant.pk, sharing_domain_id=self.domain.pk, capability=Capability.SHARED_MATCH)
        args.update(kwargs)
        return assess_access(**args)

    def scoped(self, capability=Capability.WRITE_PRIVATE_OVERLAY, **kwargs):
        args = dict(capability=capability, entity_type="organization", entity_id=self.org.pk, assignment_id=self.assignment.pk)
        args.update(kwargs)
        return self.check(**args)

    def test_positive_roles_and_separate_capabilities(self):
        for role in TenantMembership.Role.values:
            self.membership.role = role; self.membership.save()
            self.assertTrue(self.check().allowed)
            self.assertTrue(self.scoped(Capability.READ_PRIVATE_OVERLAY).allowed)
            for cap in (Capability.EDIT_SHARED_CORE, Capability.EDIT_PUBLISHED_CORE, Capability.PUBLISH, Capability.WRITE_PRIVATE_OVERLAY):
                self.assertEqual(self.scoped(cap).allowed, role != "leser")
            self.assertEqual(self.check(capability=Capability.ADD_TO_OWN_TENANT, entity_type="organization", entity_id=self.org.pk).allowed, role != "leser")
            for cap in (Capability.WRITE_IMAGE_HOME, Capability.TRANSFER_IMAGE_HOME):
                self.assertFalse(self.scoped(cap).allowed)
        self.org.is_published = True; self.org.save()
        self.membership.role = "redigerer"; self.membership.save()
        self.assertEqual(self.scoped(Capability.EDIT_SHARED_CORE).code, "PUBLISHED_CAPABILITY_REQUIRED")
        self.assertTrue(self.scoped(Capability.EDIT_PUBLISHED_CORE).allowed)

    def test_default_off_no_writes_no_admin_or_endpoint_registration(self):
        with override_settings(SHARING_ACCESS_ENABLED=False), connection.execute_wrapper(self.no_writes):
            self.assertEqual(self.check().code, "DISABLED")
        for model in (SharingAgreement, SharingAgreementAcceptance, SharingAgreementRevocation, SharingAccessAudit):
            self.assertNotIn(model, admin.site._registry)
        request = RequestFactory().get("/admin/")
        request.user = self.author
        fields = admin.site._registry[TenantMembership].get_form(request).base_fields
        self.assertNotIn("is_active", fields)
        from crm.serializers import TenantMembershipSerializer
        self.assertNotIn("is_active", TenantMembershipSerializer().fields)
        with connection.execute_wrapper(self.no_writes):
            self.assertTrue(self.check().allowed)
            self.assertTrue(self.scoped().allowed)

    @staticmethod
    def no_writes(execute, sql, params, many, context):
        assert sql.lstrip().split()[0].upper() not in {"INSERT", "UPDATE", "DELETE"}
        return execute(sql, params, many, context)

    def test_no_global_group_or_superuser_bypass(self):
        self.membership.delete()
        self.user.groups.add(Group.objects.create(name="redigerer"))
        self.assertEqual(get_user_tenant_role(self.user, self.tenant.pk), "redigerer")
        self.assertEqual(self.check().code, "INVALID_MEMBERSHIP")
        self.user.is_superuser = True; self.user.save()
        self.assertEqual(self.check().code, "INVALID_MEMBERSHIP")
        self.assertEqual(self.check(user_id=self.author.pk).code, "INVALID_MEMBERSHIP")
        TenantMembership.objects.create(user=self.author, tenant=self.tenant, role="leser")
        self.assertEqual(self.check(user_id=self.author.pk).code, "AGREEMENT_REQUIRED")
        self.accept(self.agreement, user=self.author)
        self.assertTrue(self.check(user_id=self.author.pk).allowed)
        self.assertFalse(self.scoped(user_id=self.author.pk).allowed)

    def test_inactive_invalid_removed_membership_and_cached_user(self):
        self.user.is_active = False; self.user.save()
        self.assertEqual(self.check().code, "INVALID_MEMBERSHIP")
        self.user.is_active = True; self.user.save()
        self.membership.is_active = False; self.membership.save()
        self.assertEqual(self.check().code, "INVALID_MEMBERSHIP")
        # Legacy role resolution intentionally unchanged, even for new active bit.
        self.assertEqual(get_user_tenant_role(self.user, self.tenant.pk), "redigerer")
        self.membership.is_active = True; self.membership.role = "unrecognized"; self.membership.save()
        self.assertEqual(self.check().code, "CAPABILITY_DENIED")
        self.membership.delete()
        self.assertFalse(self.check().allowed)

    def test_cross_tenant_domain_and_assignment_denials(self):
        self.assertFalse(self.check(tenant_id=self.other.pk).allowed)
        self.assertFalse(self.check(sharing_domain_id=self.other_domain.pk).allowed)
        TenantMembership.objects.create(user=self.user, tenant=self.other, role="redigerer")
        # Domain acceptance is user/domain scoped, not exclusive to acceptance tenant.
        self.assertTrue(self.check(tenant_id=self.other.pk).allowed)
        self.assertEqual(self.scoped(tenant_id=self.other.pk).code, "INVALID_ASSIGNMENT")
        foreign_org = fixture_bound(Organization, tenant=self.foreign, sharing_domain=self.other_domain, name="Foreign")
        self.assertEqual(self.scoped(entity_id=foreign_org.pk).code, "INVALID_SCOPE")
        self.assertEqual(self.scoped(assignment_id=None).code, "INVALID_ASSIGNMENT")
        person = fixture_bound(Person, tenant=self.tenant, sharing_domain=self.domain, full_name="Synthetic")
        assigned = fixture_assignment(PersonTenantAssignment, person=person, tenant=self.tenant)
        self.assertTrue(self.scoped(entity_type="person", entity_id=person.pk, assignment_id=assigned.pk).allowed)
        self.assertFalse(self.scoped(Capability.PUBLISH, entity_type="person", entity_id=person.pk, assignment_id=assigned.pk).allowed)
        self.assertFalse(self.check(entity_id=self.org.pk).allowed)

    def test_missing_old_revoked_future_and_exact_effective_boundary(self):
        SharingAgreementRevocation.objects.create(acceptance=self.acceptance, actor=self.user)
        self.assertEqual(self.check().code, "AGREEMENT_REQUIRED")
        self.accept(self.agreement)  # New explicit acceptance; history remains.
        self.assertTrue(self.check().allowed)
        current = self.agree(self.domain, 2, timezone.now())
        self.assertEqual(self.check().code, "AGREEMENT_REQUIRED")
        self.accept(current)
        self.assertTrue(self.check().allowed)
        self.assertEqual(self.check().agreement_id, current.pk)
        future = self.agree(self.domain, 3, timezone.now()+timedelta(days=1))
        self.assertTrue(self.check().allowed)
        with self.assertRaises(DatabaseError), transaction.atomic():
            self.accept(future)
        with patch("crm.services.sharing_access.Now", return_value=Value(future.effective_at)):
            self.assertEqual(self.check().code, "AGREEMENT_REQUIRED")
        with self.assertRaises(DatabaseError), transaction.atomic():
            self.accept(self.agreement)

    def test_input_validation(self):
        for key in ("user_id", "tenant_id", "sharing_domain_id"):
            for value in (None, True, "1", -1, 0):
                self.assertFalse(self.check(**{key: value}).allowed)
        self.assertEqual(self.check(capability="missing").code, "UNKNOWN_CAPABILITY")
        for value in (True, "1", None):
            self.assertFalse(self.scoped(entity_id=value).allowed)

    def test_append_only_orm_sql_and_audit_minimization(self):
        records = (self.agreement, self.acceptance, SharingAccessAudit.objects.first())
        for obj in records:
            with self.assertRaises(SharingRecordError): obj.save()
            with self.assertRaises(SharingRecordError): obj.delete()
            with self.assertRaises(SharingRecordError): type(obj).objects.filter(pk=obj.pk).update(id=obj.pk)
            with self.assertRaises(SharingRecordError): type(obj).objects.filter(pk=obj.pk).delete()
            for operation in (f'UPDATE {obj._meta.db_table} SET id=id WHERE id=%s', f'DELETE FROM {obj._meta.db_table} WHERE id=%s'):
                with self.assertRaises(DatabaseError), transaction.atomic(), connection.cursor() as cursor:
                    cursor.execute(operation, [obj.pk])
        audit = list(SharingAccessAudit.objects.values())
        self.assertEqual(len(audit), 2)
        self.assertEqual({a["event"] for a in audit}, {"agreement_created", "accepted"})
        self.assertNotIn(self.agreement.text, str(audit))
        with self.assertRaises(DatabaseError), transaction.atomic(), connection.cursor() as cursor:
            cursor.execute("INSERT INTO crm_sharingaccessaudit(event,record_id,actor_id,sharing_domain_id,occurred_at) VALUES ('accepted',999,%s,%s,now())", [self.user.pk,self.domain.pk])

    def test_structural_guards_duplicate_acceptance_and_atomic_audit(self):
        count = SharingAccessAudit.objects.count()
        for create in (lambda: self.accept(self.agreement),
                       lambda: self.accept(self.agreement, tenant=self.foreign),
                       lambda: SharingAgreementRevocation.objects.create(acceptance=self.acceptance, actor=self.author),
                       lambda: self.agree(self.domain, 1, timezone.now()+timedelta(days=3))):
            with self.assertRaises(DatabaseError), transaction.atomic(): create()
        self.assertEqual(SharingAccessAudit.objects.count(), count)
        with self.assertRaises(RuntimeError), transaction.atomic():
            SharingAgreementRevocation.objects.create(acceptance=self.acceptance, actor=self.user)
            self.assertEqual(SharingAccessAudit.objects.count(), count+1)
            raise RuntimeError("synthetic rollback")
        self.assertEqual(SharingAccessAudit.objects.count(), count)
        self.assertFalse(SharingAgreementRevocation.objects.exists())
        with patch("crm.models.SharingAccessAudit.save", side_effect=RuntimeError):
            # Database trigger cannot be skipped through the Python audit model.
            revoked = SharingAgreementRevocation.objects.create(acceptance=self.acceptance, actor=self.user)
        revoked.refresh_from_db()
        self.assertEqual(SharingAccessAudit.objects.count(), count+1)
        with self.assertRaises(ProtectedError): self.tenant.delete()
        with self.assertRaises(ProtectedError): self.org.delete()
        self.assertEqual(self.org.note, "private")

    def test_no_current_agreement_and_inactive_acceptance_insert(self):
        TenantMembership.objects.create(user=self.user, tenant=self.foreign, role="redigerer")
        self.assertEqual(self.check(tenant_id=self.foreign.pk, sharing_domain_id=self.other_domain.pk).code, "AGREEMENT_REQUIRED")
        self.user.is_active=False; self.user.save()
        with self.assertRaises(DatabaseError), transaction.atomic():
            self.accept(self.agreement)
        self.user.is_active=True; self.user.save()
        self.membership.is_active=False; self.membership.save()
        with self.assertRaises(DatabaseError), transaction.atomic():
            self.accept(self.agreement)

    def test_audit_insert_failure_rolls_back_source(self):
        before = (SharingAgreement.objects.count(), SharingAccessAudit.objects.count())
        with connection.cursor() as cursor:
            cursor.execute("""
                CREATE FUNCTION crm_synthetic_fail_audit() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN RAISE EXCEPTION 'synthetic audit failure'; END $$;
                CREATE TRIGGER synthetic_fail_audit BEFORE INSERT ON crm_sharingaccessaudit
                FOR EACH ROW EXECUTE FUNCTION crm_synthetic_fail_audit();
            """)
        try:
            with self.assertRaises(DatabaseError), transaction.atomic():
                self.agree(self.domain, 2, timezone.now())
            self.assertEqual((SharingAgreement.objects.count(), SharingAccessAudit.objects.count()), before)
        finally:
            with connection.cursor() as cursor:
                cursor.execute("DROP TRIGGER synthetic_fail_audit ON crm_sharingaccessaudit; DROP FUNCTION crm_synthetic_fail_audit()")


class SharingFoundationMigrationTests(TransactionTestCase):
    old = ("crm", "0036_tenant_note_copy_batch")
    new = ("crm", "0037_sharing_access_foundation")

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_additive_forward_empty_reverse_and_history_guard(self):
        MigrationExecutor(connection).migrate([self.old])
        state = MigrationExecutor(connection).loader.project_state([self.old]).apps
        user = state.get_model("auth", "User").objects.create(username="synthetic")
        tenant = state.get_model("crm", "Tenant").objects.create(name="Synthetic", slug="synthetic")
        member = state.get_model("crm", "TenantMembership").objects.create(user_id=user.pk, tenant_id=tenant.pk, role="leser")
        MigrationExecutor(connection).migrate([self.new])
        self.assertTrue(TenantMembership.objects.get(pk=member.pk).is_active)
        for model in (SharingAgreement, SharingAgreementAcceptance, SharingAgreementRevocation, SharingAccessAudit):
            self.assertEqual(model.objects.count(), 0)
        MigrationExecutor(connection).migrate([self.old])
        MigrationExecutor(connection).migrate([self.new])
        for isolation in ("REPEATABLE READ", "SERIALIZABLE"):
            with self.assertRaisesMessage(RuntimeError, "reverse requires READ COMMITTED"), transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute("SET TRANSACTION ISOLATION LEVEL " + isolation)
                MigrationExecutor(connection).migrate([self.old])
        TenantMembership.objects.filter(pk=member.pk).update(is_active=False)
        with self.assertRaises(RuntimeError), transaction.atomic():
            MigrationExecutor(connection).migrate([self.old])
        TenantMembership.objects.filter(pk=member.pk).update(is_active=True)
        domain = SharingDomain.objects.create(name="Synthetic", slug="synthetic")
        historical = MigrationExecutor(connection).loader.project_state([self.new]).apps
        historical.get_model("crm", "SharingAgreement").objects.create(sharing_domain_id=domain.pk,
            version=1, text="Synthetic", created_by_id=user.pk, effective_at=timezone.now())
        with self.assertRaises(RuntimeError), transaction.atomic():
            MigrationExecutor(connection).migrate([self.old])
        self.assertEqual(SharingAccessAudit.objects.count(), 1)


class SharingConcurrencyTests(TransactionTestCase):
    # Existing helpers propagate thread failures and close each DB connection.
    from crm.test_phase6a2_backfill import LegacyBackfillTests
    thread = LegacyBackfillTests.thread
    _wait_for_lock_waiter = LegacyBackfillTests._wait_for_lock_waiter

    def test_concurrent_duplicate_acceptance_serializes_and_audits_once(self):
        user = get_user_model().objects.create_user(username="synthetic")
        domain = SharingDomain.objects.create(name="Synthetic", slug="synthetic")
        tenant = fixture_bound(Tenant, name="Synthetic", slug="synthetic", sharing_domain=domain)
        TenantMembership.objects.create(user=user, tenant=tenant, role="leser")
        agreement = SharingAgreement.objects.create(sharing_domain=domain, version=1, text="Synthetic", created_by=user, effective_at=timezone.now())
        outcomes = []
        def accept():
            try:
                with transaction.atomic():
                    SharingAgreementAcceptance.objects.create(user_id=user.pk, tenant_id=tenant.pk, agreement_id=agreement.pk)
            except DatabaseError:
                outcomes.append("CONFLICT")
                return
            outcomes.append("ACCEPTED")
        with transaction.atomic():
            SharingAgreementAcceptance.objects.create(user=user, tenant=tenant, agreement=agreement)
            worker, errors = self.thread(accept)
            self._wait_for_lock_waiter()
        worker.join(timeout=10)
        self.assertFalse(worker.is_alive())
        self.assertFalse(errors)
        self.assertEqual(outcomes, ["CONFLICT"])
        self.assertEqual(SharingAgreementAcceptance.objects.count(), 1)
        self.assertEqual(SharingAccessAudit.objects.filter(event="accepted").count(), 1)

    def test_snapshot_isolation_rejects_all_history_inserts(self):
        user = get_user_model().objects.create_user(username="synthetic-isolation")
        domain = SharingDomain.objects.create(name="Isolation", slug="isolation")
        tenant = fixture_bound(Tenant, name="Isolation", slug="isolation", sharing_domain=domain)
        TenantMembership.objects.create(user=user, tenant=tenant, role="leser")
        agreement = SharingAgreement.objects.create(sharing_domain=domain, version=1, text="Synthetic", created_by=user, effective_at=timezone.now())
        acceptance = SharingAgreementAcceptance.objects.create(user=user, tenant=tenant, agreement=agreement)
        before = SharingAccessAudit.objects.count()
        for isolation in ("REPEATABLE READ", "SERIALIZABLE"):
            for create in (
                lambda: SharingAgreement.objects.create(sharing_domain=domain, version=2, text="Synthetic", created_by=user, effective_at=timezone.now()),
                lambda: SharingAgreementAcceptance.objects.create(user=user, tenant=tenant, agreement=agreement),
                lambda: SharingAgreementRevocation.objects.create(acceptance=acceptance, actor=user),
            ):
                with self.subTest(isolation=isolation), self.assertRaisesMessage(DatabaseError, "requires READ COMMITTED"):
                    with transaction.atomic(), connection.cursor() as cursor:
                        cursor.execute("SET TRANSACTION ISOLATION LEVEL " + isolation)
                        create()
        self.assertEqual(SharingAccessAudit.objects.count(), before)
        self.assertEqual(SharingAgreement.objects.count(), 1)
        self.assertEqual(SharingAgreementAcceptance.objects.count(), 1)
        self.assertEqual(SharingAgreementRevocation.objects.count(), 0)
