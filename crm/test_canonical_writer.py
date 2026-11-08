import threading
from dataclasses import replace
from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import connection, transaction, DatabaseError
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase, RequestFactory, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from crm.models import (
    Organization, Person, OrganizationTenantAssignment, PersonTenantAssignment,
    SharingDomain, Tenant, TenantMembership, SharingAgreement, SharingAgreementAcceptance,
    SharingAgreementRevocation, CanonicalWriteAudit, OrganizationNoteOverlay, PersonNoteOverlay,
)
from crm.services import canonical_writer as writer
from crm.services import sharing_access
from crm.sharing_records import SharingRecordError
from crm.test_phase6a1_foundation import fixture_bound, fixture_assignment
from crm import test_phase6a2_backfill as backfill_tests


@override_settings(CANONICAL_WRITER_ENABLED=True, SHARING_ACCESS_ENABLED=True, SECURE_SSL_REDIRECT=False)
class CanonicalWriterTests(TransactionTestCase):
    thread = backfill_tests.LegacyBackfillTests.thread
    _wait_for_lock_waiter = backfill_tests.LegacyBackfillTests._wait_for_lock_waiter

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="synthetic-writer")
        self.domain = SharingDomain.objects.create(name="Synthetic", slug="synthetic")
        self.tenant = fixture_bound(Tenant, name="Synthetic", slug="synthetic", sharing_domain=self.domain)
        self.membership = TenantMembership.objects.create(user=self.user, tenant=self.tenant, role="redigerer")
        self.agreement = SharingAgreement.objects.create(sharing_domain=self.domain, version=1,
            text="Synthetic", effective_at=timezone.now()-timedelta(days=1), created_by=self.user)
        self.accepted = SharingAgreementAcceptance.objects.create(user=self.user, tenant=self.tenant, agreement=self.agreement)
        self.org = fixture_bound(Organization, tenant=self.tenant, sharing_domain=self.domain, name="Synthetic", note="PRIVATE", description=None)
        self.person = fixture_bound(Person, tenant=self.tenant, sharing_domain=self.domain, full_name="Synthetic", note="PRIVATE")
        self.org_assignment = fixture_assignment(OrganizationTenantAssignment, organization=self.org, tenant=self.tenant)
        self.person_assignment = fixture_assignment(PersonTenantAssignment, person=self.person, tenant=self.tenant)
        self.context = dict(user_id=self.user.pk, tenant_id=self.tenant.pk, sharing_domain_id=self.domain.pk,
            entity_type="organization", entity_id=self.org.pk, assignment_id=self.org_assignment.pk, capability=sharing_access.Capability.EDIT_SHARED_CORE)

    def revision(self, **kwargs):
        return writer.get_revision(**(self.context|kwargs))

    def write(self, revision, values=None, **kwargs):
        return writer.write_core(expected_revision=revision, values=values or {"name":"Changed"}, **(self.context|kwargs))

    def assert_code(self, code, fn):
        with self.assertRaisesMessage(writer.CanonicalWriteError, code): fn()

    def test_exact_patch_and_audit_atomic_counter_minimization(self):
        old = self.revision()
        self.assertEqual(old.revision, 0)
        new = self.write(old, {"name":"Æ exact ", "description":"\n exact\r\n "})
        self.org.refresh_from_db()
        self.assertEqual((self.org.name,self.org.description,self.org.note), ("Æ exact ","\n exact\r\n ","PRIVATE"))
        self.assertEqual(new, self.revision());self.assertEqual(new.revision,1);self.assertNotEqual(new.write_stamp,old.write_stamp)
        audit=CanonicalWriteAudit.objects.get()
        self.assertEqual((audit.actor_id,audit.tenant_id,audit.assignment_id,audit.sharing_domain_id,audit.agreement_id),
            (self.user.pk,self.tenant.pk,self.org_assignment.pk,self.domain.pk,self.agreement.pk))
        self.assertEqual((audit.previous_revision,audit.revision,audit.entity_type,audit.entity_id,audit.action), (0,1,'organization',self.org.pk,'edit_shared_core'))
        self.assertEqual(audit.changed_fields,['description','name'])
        self.assertNotIn("Æ exact",str(CanonicalWriteAudit.objects.values().get()))
        self.assertNotIn("PRIVATE",str(CanonicalWriteAudit.objects.values().get()))
        second=self.write(new,{"description":None});self.assertEqual(second.revision,2)
        self.assertEqual(OrganizationNoteOverlay.objects.count()+PersonNoteOverlay.objects.count(),0)

    def test_person_contract(self):
        context=self.context|dict(entity_type='person',entity_id=self.person.pk,assignment_id=self.person_assignment.pk)
        r=writer.get_revision(**context)
        writer.write_core(expected_revision=r,values={'full_name':'Exact person'},**context)
        self.person.refresh_from_db();self.assertEqual((self.person.full_name,self.person.note),('Exact person','PRIVATE'))
        self.assert_code('INVALID_FIELDS',lambda:writer.write_core(expected_revision=writer.get_revision(**context), values={'title':'not core'},**context))

    def test_fail_closed_gates_no_writes_and_invalid_capability(self):
        revision=self.revision()
        for setting in ('CANONICAL_WRITER_ENABLED','SHARING_ACCESS_ENABLED'):
            with override_settings(**{setting:False}):
                self.assert_code('WRITER_DISABLED',self.revision)
                self.assert_code('WRITER_DISABLED',lambda:self.write(revision))
        for cap in ('publish','unknown','write_private_overlay'):
            self.assert_code('INVALID_CAPABILITY',lambda:self.write(revision,capability=cap))
        self.assertEqual(CanonicalWriteAudit.objects.count(),0)
        self.org.refresh_from_db();self.assertEqual(self.org.name,'Synthetic')

    def test_scopes_membership_user_group_superuser_and_acceptance(self):
        revision=self.revision()
        for key in ('tenant_id','sharing_domain_id','assignment_id','entity_id','user_id'):
            self.assert_code('ACCESS_DENIED',lambda:self.write(revision,**{key:999999}))
        self.membership.is_active=False;self.membership.save()
        self.assert_code('INVALID_MEMBERSHIP',lambda:self.write(revision))
        self.membership.is_active=True;self.membership.role='leser';self.membership.save()
        self.user.is_superuser=True;self.user.save();self.user.groups.add(Group.objects.create(name='redigerer'))
        self.assert_code('CAPABILITY_DENIED',lambda:self.write(revision))
        self.membership.role='redigerer';self.membership.save();self.user.is_active=False;self.user.save()
        self.assert_code('INVALID_MEMBERSHIP',lambda:self.write(revision))
        self.user.is_active=True;self.user.save()
        self.membership.delete();self.assert_code('ACCESS_DENIED',lambda:self.write(revision))
        self.assertEqual(CanonicalWriteAudit.objects.count(),0)

    def test_published_actor_requires_explicit_separate_action(self):
        old=self.revision();Organization.objects.filter(pk=self.org.pk).update(is_published=True)
        self.assert_code('PUBLISHED_CAPABILITY_REQUIRED',lambda:self.write(old))
        published=self.context|{'capability':sharing_access.Capability.EDIT_PUBLISHED_CORE}
        r=writer.get_revision(**published)
        writer.write_core(expected_revision=r,values={'name':'Published changed'},**published)
        self.assertEqual(CanonicalWriteAudit.objects.get().action,'edit_published_core')
        self.org.refresh_from_db();self.assertTrue(self.org.is_published)
        self.assert_code('INVALID_FIELDS',lambda:writer.write_core(expected_revision=writer.get_revision(**published),values={'is_published':False},**published))

    def test_stale_revision_and_noop_or_invalid_fields_no_partial_write(self):
        old=self.revision();new=self.write(old)
        for stale in (old, None, replace(new,revision=2), replace(new,write_stamp=uuid4()), replace(new,entity_id=999)):
            self.assert_code('STALE_REVISION',lambda:self.write(stale,{'name':'Should not save'}))
        for values in ({'note':'PRIVATE'},{'tags':[]},{'name':'x','email':'raw@example.test'},{'tenant_id':1},{'website_url':'https://example.test'},{'canonical_write_stamp':uuid4()}):
            self.assert_code('INVALID_FIELDS',lambda:self.write(new,values))
        for values in ({'name':''},{'name':None},{'name':123},{'name':'x'*256}):
            self.assert_code('INVALID_VALUES',lambda:self.write(new,values))
        self.assert_code('NO_CHANGES',lambda:self.write(new,{'name':'Changed'}))
        self.org.refresh_from_db();self.assertEqual(self.org.name,'Changed');self.assertEqual(CanonicalWriteAudit.objects.count(),1)

    def test_legacy_raw_sql_aba_and_old_model_save_cannot_restore_stamp(self):
        old=self.revision();stale_instance=Organization.objects.get(pk=self.org.pk)
        with connection.cursor() as c:
            c.execute('UPDATE crm_organization SET name=%s WHERE id=%s',['Legacy',self.org.pk])
            c.execute('UPDATE crm_organization SET name=%s WHERE id=%s',['Synthetic',self.org.pk])
        now=self.revision();self.assertEqual(now.revision,old.revision);self.assertNotEqual(now.write_stamp,old.write_stamp)
        self.assert_code('STALE_REVISION',lambda:self.write(old))
        stale_instance.note='Still private';stale_instance.save()
        self.assertEqual(self.revision(),now)  # No canonical field delta; OLD DB stamp preserved.
        self.assertEqual(CanonicalWriteAudit.objects.count(),0)
        with connection.cursor() as c:c.execute('UPDATE crm_organization SET canonical_write_stamp=%s WHERE id=%s',[old.write_stamp,self.org.pk])
        self.assertEqual(self.revision(),now)

    def test_legacy_api_editor_admin_and_public_remain_authoritative(self):
        old=self.revision();client=APIClient();client.force_authenticate(self.user)
        self.assertEqual(client.patch(f'/api/tenants/{self.tenant.pk}/organizations/{self.org.pk}/',{'name':'Legacy API','note':'Legacy private'},format='json').status_code,200)
        self.assert_code('STALE_REVISION',lambda:self.write(old))
        self.assertEqual(self.revision().revision,0)
        self.assertEqual(CanonicalWriteAudit.objects.count(),0)
        from crm.serializers import OrganizationSerializer,PersonSerializer
        from crm.serializers_public import PublicActorSerializer
        for serializer in (OrganizationSerializer,PersonSerializer,PublicActorSerializer):
            self.assertNotIn('canonical_write_stamp',serializer().fields)
        req=RequestFactory().get('/admin/');req.user=self.user
        for model in (Organization,Person):
            self.assertNotIn('canonical_write_stamp',admin.site._registry[model].get_form(req).base_fields)
        self.assertNotIn(CanonicalWriteAudit,admin.site._registry)

    def test_audit_failure_rolls_back_core_stamp_counter_and_timestamp(self):
        old=self.revision();self.org.refresh_from_db();before=self.org.updated_at
        with patch.object(CanonicalWriteAudit.objects,'create',side_effect=RuntimeError('synthetic audit failure')):
            with self.assertRaises(RuntimeError):self.write(old)
        self.assertEqual(self.revision(),old)
        self.org.refresh_from_db();self.assertEqual(self.org.name,'Synthetic');self.assertEqual(self.org.updated_at,before)
        self.assertEqual(CanonicalWriteAudit.objects.count(),0)
        self.write(old)
        audit=CanonicalWriteAudit.objects.get()
        for fn in (lambda:audit.save(),lambda:audit.delete(),lambda:CanonicalWriteAudit.objects.update(action='x')):
            with self.assertRaises(SharingRecordError):fn()
        for sql in ('UPDATE crm_canonicalwriteaudit SET revision=revision','DELETE FROM crm_canonicalwriteaudit'):
            with self.assertRaises(DatabaseError),transaction.atomic(),connection.cursor() as c:c.execute(sql)

    def test_outer_transaction_refused(self):
        r=self.revision()
        with transaction.atomic():
            self.assert_code('OUTER_TRANSACTION_UNSUPPORTED',lambda:self.write(r))

    def test_concurrent_writers_only_one_commits(self):
        revision=self.revision();results=[];start=threading.Barrier(2)
        def update(label):
            start.wait()
            try:results.append(self.write(revision,{'name':label}).revision)
            except writer.CanonicalWriteError as e:results.append(str(e))
        a,ae=self.thread(lambda:update('First'));b,be=self.thread(lambda:update('Second'))
        a.join(8);b.join(8);self.assertFalse(a.is_alive() or b.is_alive());self.assertFalse(ae+be)
        self.assertEqual(sorted(map(str,results)),['1','STALE_REVISION']);self.assertEqual(CanonicalWriteAudit.objects.count(),1)

    def test_waiting_writer_reauthorizes_after_membership_revoke_or_user_deactivation(self):
        for model,pk,changes in ((TenantMembership,self.membership.pk,{'is_active':False}), (get_user_model(),self.user.pk,{'is_active':False})):
            revision=self.revision();outcomes=[]
            def write():
                try:self.write(revision)
                except writer.CanonicalWriteError as e:outcomes.append(str(e))
            with transaction.atomic():
                model.objects.filter(pk=pk).update(**changes)
                worker,errors=self.thread(write);self._wait_for_lock_waiter()
            worker.join(8);self.assertFalse(worker.is_alive());self.assertFalse(errors)
            self.assertEqual(outcomes,['INVALID_MEMBERSHIP']);self.assertEqual(CanonicalWriteAudit.objects.count(),0)
            model.objects.filter(pk=pk).update(is_active=True)

    def test_waiting_writer_sees_committed_acceptance_revocation(self):
        revision=self.revision();outcomes=[]
        def write():
            try:self.write(revision)
            except writer.CanonicalWriteError as e:outcomes.append(str(e))
        with transaction.atomic():
            SharingAgreementRevocation.objects.create(acceptance=self.accepted,actor=self.user)
            worker,errors=self.thread(write);self._wait_for_lock_waiter()
        worker.join(8);self.assertFalse(worker.is_alive());self.assertFalse(errors)
        self.assertEqual(outcomes,['AGREEMENT_REQUIRED']);self.assertEqual(CanonicalWriteAudit.objects.count(),0)

    def test_lock_timeout_rolls_back_and_never_retries(self):
        revision=self.revision();outcomes=[]
        def write():
            try:self.write(revision)
            except writer.CanonicalWriteError as e:outcomes.append(str(e))
        with transaction.atomic():
            Organization.objects.select_for_update().get(pk=self.org.pk)
            worker,errors=self.thread(write);self._wait_for_lock_waiter();worker.join(6)
        self.assertFalse(worker.is_alive());self.assertFalse(errors)
        self.assertEqual(outcomes,['WRITE_OUTCOME_REQUIRES_READBACK']);self.assertEqual(self.revision(),revision)

    def test_clock_crossing_effective_at_rechecked_at_update_statement(self):
        revision=self.revision()
        future=SharingAgreement.objects.create(sharing_domain=self.domain,version=2,text='Synthetic new version',
            effective_at=timezone.now()+timedelta(seconds=2),created_by=self.user)
        original=sharing_access.assess_access
        def delayed(**context):
            decision=original(**context);self.assertTrue(decision.allowed)
            with connection.cursor() as c:
                c.execute('SELECT pg_sleep(GREATEST(0,EXTRACT(EPOCH FROM (%s-clock_timestamp()))) + 0.05)',[future.effective_at])
            return decision
        with patch.object(sharing_access,'assess_access',side_effect=delayed):
            self.assert_code('STALE_AUTHORIZATION_OR_REVISION',lambda:self.write(revision))
        self.org.refresh_from_db();self.assertEqual(self.org.name,'Synthetic');self.assertEqual(CanonicalWriteAudit.objects.count(),0)

    def test_waiting_on_legacy_edit_reloads_stamp_and_publication(self):
        revision=self.revision();outcomes=[]
        def write():
            try:self.write(revision)
            except writer.CanonicalWriteError as e:outcomes.append(str(e))
        with transaction.atomic():
            Organization.objects.filter(pk=self.org.pk).update(name='Legacy concurrently changed')
            worker,errors=self.thread(write);self._wait_for_lock_waiter()
        worker.join(8);self.assertFalse(worker.is_alive());self.assertFalse(errors)
        self.assertEqual(outcomes,['STALE_REVISION']);self.assertEqual(CanonicalWriteAudit.objects.count(),0)

    def test_pending_revocation_waits_until_successful_write_commits(self):
        revision=self.revision();worker=[];errors=[]
        original=CanonicalWriteAudit.objects.create
        def append(**values):
            def revoke():SharingAgreementRevocation.objects.create(acceptance_id=self.accepted.pk,actor_id=self.user.pk)
            t,e=self.thread(revoke);worker.append(t);errors.append(e);self._wait_for_lock_waiter()
            return original(**values)
        with patch.object(CanonicalWriteAudit.objects,'create',side_effect=append):self.write(revision)
        worker[0].join(8);self.assertFalse(worker[0].is_alive());self.assertFalse(errors[0])
        self.assertEqual(CanonicalWriteAudit.objects.count(),1)
        self.assert_code('AGREEMENT_REQUIRED',self.revision)


    def test_real_cross_tenant_and_cross_domain_contexts_are_denied(self):
        revision=self.revision()
        other=fixture_bound(Tenant,name='Other',slug='other',sharing_domain=self.domain)
        TenantMembership.objects.create(user=self.user,tenant=other,role='redigerer')
        self.assert_code('ACCESS_DENIED',lambda:self.write(revision,tenant_id=other.pk))
        foreign_domain=SharingDomain.objects.create(name='Foreign',slug='foreign')
        foreign=fixture_bound(Tenant,name='Foreign',slug='foreign',sharing_domain=foreign_domain)
        TenantMembership.objects.create(user=self.user,tenant=foreign,role='redigerer')
        agreement=SharingAgreement.objects.create(sharing_domain=foreign_domain,version=1,text='Synthetic',created_by=self.user,effective_at=timezone.now()-timedelta(days=1))
        SharingAgreementAcceptance.objects.create(agreement=agreement,user=self.user,tenant=foreign)
        self.assert_code('INVALID_MEMBERSHIP',lambda:self.write(revision,sharing_domain_id=foreign_domain.pk))
        self.assertEqual(CanonicalWriteAudit.objects.count(),0)

    def test_real_database_audit_failure_rolls_back_profile(self):
        revision=self.revision()
        with connection.cursor() as c:
            c.execute("CREATE FUNCTION crm_synthetic_canonical_fail() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'synthetic audit failure'; END $$; CREATE TRIGGER synthetic_canonical_fail BEFORE INSERT ON crm_canonicalwriteaudit FOR EACH ROW EXECUTE FUNCTION crm_synthetic_canonical_fail();")
        try:
            with self.assertRaises(DatabaseError):self.write(revision)
            self.assertEqual(self.revision(),revision)
            self.org.refresh_from_db();self.assertEqual(self.org.name,'Synthetic')
        finally:
            with connection.cursor() as c:c.execute('DROP TRIGGER synthetic_canonical_fail ON crm_canonicalwriteaudit; DROP FUNCTION crm_synthetic_canonical_fail()')

    def test_service_forces_fresh_read_committed_instead_of_session_snapshot(self):
        with connection.cursor() as c:c.execute('SET SESSION CHARACTERISTICS AS TRANSACTION ISOLATION LEVEL REPEATABLE READ')
        try:
            revision=self.revision();self.assertEqual(self.write(revision).revision,1)
        finally:
            with connection.cursor() as c:c.execute('SET SESSION CHARACTERISTICS AS TRANSACTION ISOLATION LEVEL READ COMMITTED')


    def test_membership_default_ordering_does_not_upgrade_tenant_share_lock(self):
        revision=self.revision();errors=[]
        original=CanonicalWriteAudit.objects.create
        def append(**values):
            def key_share():
                with transaction.atomic(),connection.cursor() as c:
                    c.execute('SELECT id FROM crm_tenant WHERE id=%s FOR KEY SHARE NOWAIT',[self.tenant.pk])
                    self.assertEqual(c.fetchone()[0],self.tenant.pk)
            worker,e=self.thread(key_share);worker.join(4);self.assertFalse(worker.is_alive());errors.extend(e)
            return original(**values)
        with patch.object(CanonicalWriteAudit.objects,'create',side_effect=append):self.write(revision)
        self.assertFalse(errors)


class CanonicalWriterMigrationTests(TransactionTestCase):
    old=('crm','0037_sharing_access_foundation')
    new=('crm','0038_canonical_writer_foundation')

    def tearDown(self):
        executor=MigrationExecutor(connection);executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_additive_forward_reverse_preservation_and_nonempty_audit_guard(self):
        MigrationExecutor(connection).migrate([self.old])
        apps=MigrationExecutor(connection).loader.project_state([self.old]).apps
        tenant=apps.get_model('crm','Tenant').objects.create(name='Synthetic',slug='synthetic')
        organization=apps.get_model('crm','Organization').objects.create(tenant_id=tenant.pk,name='Synthetic',description=None,note='PRIVATE')
        original=apps.get_model('crm','Organization').objects.values().get(pk=organization.pk)
        for target in (self.new,self.old,self.new):
            MigrationExecutor(connection).migrate([target])
            state=MigrationExecutor(connection).loader.project_state([target]).apps
            row=state.get_model('crm','Organization').objects.values().get(pk=organization.pk)
            if target==self.new:
                self.assertIsNotNone(row.pop('canonical_write_stamp'))
                self.assertEqual(CanonicalWriteAudit.objects.count(),0)
            self.assertEqual(row,original)
        CanonicalWriteAudit.objects.create(actor_id=1,tenant_id=tenant.pk,assignment_id=1,sharing_domain_id=1,
            agreement_id=1,entity_type='organization',entity_id=organization.pk,action='edit_shared_core',
            previous_revision=0,revision=1,write_stamp=uuid4(),changed_fields=['name'],occurred_at=timezone.now())
        with self.assertRaises(RuntimeError),transaction.atomic():MigrationExecutor(connection).migrate([self.old])
        self.assertEqual(CanonicalWriteAudit.objects.count(),1)
