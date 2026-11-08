from datetime import timedelta
from io import StringIO
from unittest.mock import patch
from uuid import uuid4

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import DatabaseError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase, RequestFactory, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from crm.models import (
    AccessManagementGrant as Grant, AccessManagementGrantRevocation as GrantRevocation,
    MembershipManagementAudit, SharingDomain, Tenant, TenantMembership,
    SharingAgreement, SharingAgreementAcceptance, SharingAgreementRevocation,
    SharingAccessAudit, CanonicalWriteAudit, OrganizationNoteOverlay, PersonNoteOverlay,
)
from crm.services import access_management as service
from crm.services.sharing_access import assess_access, Capability
from crm.test_phase6a1_foundation import fixture_bound
from crm import test_phase6a2_backfill as backfill_tests


@override_settings(ACCESS_MANAGEMENT_ENABLED=True, SECURE_SSL_REDIRECT=False)
class ManagementTests(TransactionTestCase):
    thread = backfill_tests.LegacyBackfillTests.thread
    _wait_for_lock_waiter = backfill_tests.LegacyBackfillTests._wait_for_lock_waiter

    def setUp(self):
        User = get_user_model()
        self.operator = User.objects.create_user(username="synthetic-operator")
        self.manager = User.objects.create_user(username="synthetic-manager")
        self.user = User.objects.create_user(username="synthetic-member")
        self.domain = SharingDomain.objects.create(name="Synthetic", slug="synthetic")
        self.foreign_domain = SharingDomain.objects.create(name="Foreign", slug="foreign")
        self.tenant = fixture_bound(Tenant, name="Synthetic Office", slug="synthetic", sharing_domain=self.domain)
        self.other = fixture_bound(Tenant, name="Other Office", slug="other", sharing_domain=self.domain)
        self.foreign = fixture_bound(Tenant, name="Foreign Office", slug="foreign", sharing_domain=self.foreign_domain)
        self.client = APIClient(); self.client.force_authenticate(self.manager)
        self.member_path = f"/api/auth/access-management/domains/{self.domain.pk}/tenants/{self.tenant.pk}/memberships/"
        self.appointment = dict(actor_id=self.operator.pk, user_id=self.manager.pk, domain_id=self.domain.pk,
            tenant_id=self.tenant.pk, action=Grant.Action.MANAGE_TENANT_MEMBERSHIPS,
            request_id=uuid4(), mandate_reference="SYNTHETIC-ONLY", expected_database=connection.settings_dict['NAME'])
        self.grant = service.appoint(**self.appointment)

    def member(self, **kwargs):
        return service.set_membership(**(dict(actor_id=self.manager.pk, tenant_id=self.tenant.pk, domain_id=self.domain.pk,
            username=self.user.username, role="redigerer", is_active=True, expected_updated_at=None) | kwargs))

    def publication(self, **kwargs):
        return service.publish_agreement(**(dict(actor_id=self.manager.pk, domain_id=self.domain.pk, version=1,
            text="Synthetic exact\nÆ  ", effective_at=timezone.now()-timedelta(days=1),
            legal_approval_reference="SYNTHETIC-LEGAL-ONLY", approved=True) | kwargs))

    def publishing_grant(self):
        return service.appoint(**(self.appointment | dict(action=Grant.Action.PUBLISH_SHARING_AGREEMENT,
            tenant_id=None, request_id=uuid4())))

    def assert_code(self, code, fn):
        with self.assertRaisesMessage(service.ManagementError, code): fn()

    def test_membership_positive_stale_and_atomic_audit(self):
        row = self.member()
        self.assertEqual(TenantMembership.objects.get().role, "redigerer")
        audit = MembershipManagementAudit.objects.get()
        self.assertEqual((audit.actor_id, audit.target_user_id, audit.tenant_id, audit.grant_id),
            (self.manager.pk, self.user.pk, self.tenant.pk, self.grant))
        self.assertIsNone(audit.previous_role)
        self.assert_code("STALE_MEMBERSHIP", lambda: self.member(is_active=False))
        self.member(expected_updated_at=row['expected_updated_at'], is_active=False)
        self.assertFalse(TenantMembership.objects.get().is_active)
        self.assertEqual(MembershipManagementAudit.objects.count(),2)
        self.assertEqual(service.list_memberships(actor_id=self.manager.pk, tenant_id=self.tenant.pk, domain_id=self.domain.pk)[0]['is_active'],False)

    def test_no_self_change_cross_tenant_domain_or_implicit_grant(self):
        self.assert_code("SELF_CHANGE_DENIED", lambda: self.member(username=self.manager.username, role="superadmin"))
        for changes in ({"tenant_id":self.other.pk}, {"tenant_id":self.foreign.pk}, {"domain_id":self.foreign_domain.pk}):
            self.assert_code("ACCESS_DENIED",lambda: self.member(**changes))
        self.user.is_staff=True; self.user.is_superuser=True; self.user.save()
        self.user.groups.add(Group.objects.create(name="superadmin"))
        TenantMembership.objects.create(user=self.user, tenant=self.tenant, role="superadmin")
        self.assert_code("ACCESS_DENIED",lambda:self.member(actor_id=self.user.pk,username=self.manager.username))
        self.assertEqual(MembershipManagementAudit.objects.count(),0)

    def test_inactive_actor_target_and_revoked_grant(self):
        for user in (self.manager,self.user):
            user.is_active=False; user.save()
            self.assert_code("ACCESS_DENIED" if user == self.manager else "TARGET_UNAVAILABLE",self.member)
            user.is_active=True; user.save()
        service.withdraw_appointment(actor_id=self.operator.pk, grant_id=self.grant,
            mandate_reference="SYNTHETIC-REVOCATION", expected_database=connection.settings_dict['NAME'])
        self.assert_code("ACCESS_DENIED",self.member)
        # Replay is historical evidence; it never revives a revoked appointment.
        self.assertEqual(service.appoint(**self.appointment),self.grant)
        self.assert_code("ACCESS_DENIED",self.member)

    def test_membership_can_end_after_account_inactivation_without_assigning_or_reactivating(self):
        row=self.member()
        self.user.is_active=False;self.user.save()
        self.assert_code('TARGET_UNAVAILABLE',lambda:self.member(expected_updated_at=row['expected_updated_at'],is_active=True))
        self.assert_code('TARGET_UNAVAILABLE',lambda:self.member(expected_updated_at=row['expected_updated_at'],is_active=False,role='superadmin'))
        changed=self.member(expected_updated_at=row['expected_updated_at'],is_active=False)
        self.assertFalse(changed['is_active']);self.assertEqual(MembershipManagementAudit.objects.count(),2)
        self.user.is_active=True;self.user.save()
        self.assertFalse(TenantMembership.objects.get().is_active)
        self.assertEqual(service.context(actor_id=self.user.pk)['memberships'],[])
        with override_settings(SHARING_ACCESS_ENABLED=True):
            self.assertEqual(assess_access(user_id=self.user.pk,tenant_id=self.tenant.pk,
                sharing_domain_id=self.domain.pk,capability=Capability.SHARED_MATCH).code,'INVALID_MEMBERSHIP')
        other=get_user_model().objects.create_user(username='synthetic-inactive-target',is_active=False)
        self.assert_code('TARGET_UNAVAILABLE',lambda:self.member(username=other.username,is_active=False))
        self.assertFalse(TenantMembership.objects.filter(user=other).exists())

    def test_target_username_is_rechecked_after_lock_wait(self):
        original_lock=service._lock
        def renamed(domain_id,*user_ids,**kwargs):
            get_user_model().objects.filter(pk=self.user.pk).update(username='synthetic-renamed')
            return original_lock(domain_id,*user_ids,**kwargs)
        with patch.object(service,'_lock',side_effect=renamed):
            self.assert_code('STALE_TARGET',self.member)
        self.assertEqual(TenantMembership.objects.count(),0)
        self.assertEqual(MembershipManagementAudit.objects.count(),0)

    def test_membership_audit_failure_rolls_back(self):
        with patch.object(MembershipManagementAudit.objects,"create",side_effect=DatabaseError("secret")):
            self.assert_code("OUTCOME_REQUIRES_READBACK",self.member)
        self.assertEqual(TenantMembership.objects.count(),0)
        self.assertEqual(MembershipManagementAudit.objects.count(),0)

    def test_publication_independent_grant_legal_reference_and_exact_text(self):
        self.assert_code("ACCESS_DENIED",self.publication)
        self.publishing_grant()
        self.assert_code("LEGAL_APPROVAL_REQUIRED",lambda:self.publication(approved=False))
        self.assert_code("INVALID_VALUES",lambda:self.publication(legal_approval_reference=" "))
        self.publication()
        agreement = SharingAgreement.objects.get()
        self.assertEqual(agreement.text,"Synthetic exact\nÆ  ")
        self.assertEqual(agreement.legal_approval_reference,"SYNTHETIC-LEGAL-ONLY")
        self.assertEqual(SharingAccessAudit.objects.get().event,"agreement_created")
        self.assert_code("ACCESS_DENIED",lambda:self.publication(domain_id=self.foreign_domain.pk,version=2))

    def test_own_acceptance_before_acceptance_and_revocation_after_membership_loss(self):
        self.member(); self.publishing_grant(); self.publication()
        current = service.context(actor_id=self.user.pk)['memberships'][0]['agreement']
        self.assertEqual(current['text'],"Synthetic exact\nÆ  ")
        self.client.force_authenticate(self.user)
        path=f"/api/auth/access-management/domains/{self.domain.pk}/acceptances/"
        payload=dict(tenant_id=self.tenant.pk, agreement_id=current['id'], confirmed=True)
        self.assertEqual(self.client.post(path,payload|{'confirmed':False}).status_code,403)
        self.assertEqual(self.client.post(path,payload|{'actor_id':self.manager.pk}).status_code,400)
        response = self.client.post(path,payload); self.assertEqual(response.status_code,201)
        aid=response.data['acceptance_id']
        self.assertEqual(self.client.post(path,payload).status_code,409)
        with override_settings(SHARING_ACCESS_ENABLED=True):
            self.assertTrue(assess_access(user_id=self.user.pk,tenant_id=self.tenant.pk,
                sharing_domain_id=self.domain.pk,capability=Capability.SHARED_MATCH).allowed)
        TenantMembership.objects.filter(user=self.user).update(is_active=False)
        self.assertEqual(service.context(actor_id=self.user.pk)['memberships'],[])
        self.assertEqual(self.client.post(f"/api/auth/access-management/acceptances/{aid}/revoke/",{}).status_code,200)
        self.assertTrue(service.context(actor_id=self.user.pk)['acceptances'][0]['revoked'])
        self.client.force_authenticate(self.manager)
        self.assertEqual(self.client.post(f"/api/auth/access-management/acceptances/{aid}/revoke/",{}).status_code,403)
        self.assertEqual(SharingAgreementRevocation.objects.count(),1)

    def test_version_transition_cross_scope_and_inactive_membership(self):
        self.member();self.publishing_grant();self.publication()
        old=SharingAgreement.objects.get()
        service.accept_agreement(actor_id=self.user.pk,tenant_id=self.tenant.pk,domain_id=self.domain.pk,agreement_id=old.pk,confirmed=True)
        self.publication(version=2,effective_at=timezone.now()-timedelta(seconds=1))
        for change,code in [({'agreement_id':old.pk},'STALE_AGREEMENT'),({'tenant_id':self.other.pk},'ACCESS_DENIED'),
                ({'domain_id':self.foreign_domain.pk},'ACCESS_DENIED')]:
            self.assert_code(code,lambda:service.accept_agreement(**(dict(actor_id=self.user.pk,tenant_id=self.tenant.pk,
                domain_id=self.domain.pk,agreement_id=SharingAgreement.objects.order_by('-version').first().pk,confirmed=True)|change)))
        with override_settings(SHARING_ACCESS_ENABLED=True):
            decision=assess_access(user_id=self.user.pk,tenant_id=self.tenant.pk,sharing_domain_id=self.domain.pk,capability=Capability.SHARED_MATCH)
            self.assertEqual(decision.code,'AGREEMENT_REQUIRED')
        TenantMembership.objects.filter(user=self.user).update(is_active=False)
        self.assert_code('ACCESS_DENIED',lambda:service.accept_agreement(actor_id=self.user.pk,tenant_id=self.tenant.pk,
            domain_id=self.domain.pk,agreement_id=SharingAgreement.objects.order_by('-version').first().pk,confirmed=True))

    def test_gates_and_no_side_effects(self):
        with override_settings(ACCESS_MANAGEMENT_ENABLED=False):
            self.assertFalse(service.context(actor_id=self.manager.pk)['enabled'])
            self.assert_code('DISABLED',self.member)
        self.assertEqual(assess_access(user_id=self.manager.pk,tenant_id=self.tenant.pk,
            sharing_domain_id=self.domain.pk,capability=Capability.SHARED_MATCH).code,'DISABLED')
        for model in (CanonicalWriteAudit, OrganizationNoteOverlay,PersonNoteOverlay,SharingAgreement,SharingAgreementAcceptance):
            self.assertEqual(model.objects.count(),0)
        self.assertFalse(__import__('django.conf',fromlist=['settings']).settings.CANONICAL_WRITER_ENABLED)

    def test_appointment_replay_self_and_database_checks(self):
        self.assertEqual(service.appoint(**self.appointment),self.grant)
        self.assert_code('APPOINTMENT_CONFLICT',lambda:service.appoint(**(self.appointment|{'mandate_reference':'changed'})))
        self.assert_code('SELF_APPOINTMENT_DENIED',lambda:service.appoint(**(self.appointment|{'user_id':self.operator.pk})))
        self.assert_code('INVALID_APPOINTMENT',lambda:service.appoint(**(self.appointment|{'expected_database':'wrong'})))
        self.assert_code('INVALID_SCOPE',lambda:service.appoint(**(self.appointment|{'tenant_id':self.foreign.pk})))
        self.assertEqual(Grant.objects.count(),1)

    def test_command_dry_run_and_apply_requires_explicit_database_and_mandate(self):
        stream=StringIO()
        call_command('appoint_access_manager',operator_id=self.operator.pk,mandate_reference='SYNTHETIC',
            expected_database='not-connected',stdout=stream)
        self.assertIn('PLAN_ONLY',stream.getvalue());self.assertEqual(Grant.objects.count(),1)
        with self.assertRaises(CommandError):
            call_command('appoint_access_manager',apply=True,operator_id=self.operator.pk,mandate_reference='SYNTHETIC',
                expected_database='wrong',user_id=self.user.pk,domain_id=self.domain.pk,
                tenant_id=self.tenant.pk,action=Grant.Action.MANAGE_TENANT_MEMBERSHIPS,request_id=uuid4())

    def test_api_cannot_choose_actor_or_access_wrong_scope(self):
        payload=dict(username=self.user.username,role='leser',is_active=True,expected_updated_at=None)
        self.assertEqual(self.client.post(self.member_path,payload|{'actor_id':self.operator.pk},format='json').status_code,400)
        self.assertEqual(self.client.post(self.member_path,payload,format='json').status_code,200)
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.get(self.member_path).status_code,403)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/api/auth/access-management/').status_code,403)

    def test_admin_no_mutation_even_for_superuser_and_history_immutable(self):
        self.manager.is_superuser=True;self.manager.is_staff=True;self.manager.save()
        request=RequestFactory().get('/admin/');request.user=self.manager
        modeladmin=admin.site._registry[TenantMembership]
        self.assertFalse(modeladmin.has_add_permission(request));self.assertFalse(modeladmin.has_change_permission(request))
        self.assertFalse(modeladmin.has_delete_permission(request))
        self.member()
        for model in (Grant,MembershipManagementAudit):
            with self.assertRaises(Exception):model.objects.all().delete()
            with self.assertRaises(DatabaseError),transaction.atomic():
                with connection.cursor() as c:c.execute(f'DELETE FROM {model._meta.db_table}')

    def test_concurrent_membership_change_and_revocation_reauthorize(self):
        # A command waiting on the common domain lock must see revocation after the wait.
        with transaction.atomic():
            SharingDomain.objects.select_for_update().get(pk=self.domain.pk)
            worker,outcome=self.thread(self.member)
            self._wait_for_lock_waiter()
            GrantRevocation.objects.create(grant_id=self.grant,actor_id=self.operator.pk,mandate_reference='SYNTHETIC')
        worker.join(5)
        self.assertFalse(worker.is_alive());self.assertEqual(len(outcome),1);self.assertIsInstance(outcome[0],service.ManagementError)
        self.assertEqual(str(outcome[0]),'ACCESS_DENIED');self.assertEqual(TenantMembership.objects.count(),0)

    def test_concurrent_membership_writes_reject_stale(self):
        row=self.member()
        with transaction.atomic():
            SharingDomain.objects.select_for_update().get(pk=self.domain.pk)
            worker,outcome=self.thread(lambda:self.member(expected_updated_at=row['expected_updated_at'],role='leser'))
            self._wait_for_lock_waiter()
            TenantMembership.objects.filter(user=self.user).update(role='gruppeadmin',updated_at=timezone.now())
        worker.join(5)
        self.assertFalse(worker.is_alive());self.assertEqual(str(outcome[0]),'STALE_MEMBERSHIP')
        self.assertEqual(TenantMembership.objects.get().role,'gruppeadmin')

    def test_publication_readback_is_only_for_own_domain_publisher(self):
        self.publishing_grant();self.publication()
        metadata=service.context(actor_id=self.manager.pk)['published_agreements']
        self.assertEqual(len(metadata),1);self.assertEqual(metadata[0]['text'],'Synthetic exact\nÆ  ')
        self.assertEqual(service.context(actor_id=self.user.pk)['published_agreements'],[])
        foreign_author=get_user_model().objects.create_user(username='synthetic-foreign-author')
        SharingAgreement.objects.create(sharing_domain=self.foreign_domain,version=1,text='Foreign synthetic',
            effective_at=timezone.now(),created_by=foreign_author)
        self.assertEqual(len(service.context(actor_id=self.manager.pk)['published_agreements']),1)

    def test_reverse_refuses_existing_appointment(self):
        with self.assertRaisesMessage(RuntimeError,'Cannot reverse management history'),transaction.atomic():
            MigrationExecutor(connection).migrate([('crm','0038_canonical_writer_foundation')])
        self.assertEqual(Grant.objects.count(),1)

    def test_csrf_and_authenticated_inactive_user(self):
        client=APIClient(enforce_csrf_checks=True)
        client.force_login(self.manager)
        self.assertEqual(client.post(self.member_path,dict(username=self.user.username,role='leser',
            is_active=True,expected_updated_at=None),format='json').status_code,403)
        self.manager.is_active=False;self.manager.save()
        self.assertEqual(self.client.get('/api/auth/access-management/').status_code,403)
        self.assertEqual(TenantMembership.objects.count(),0)

    def test_lock_timeout_has_no_membership_or_audit(self):
        with transaction.atomic():
            SharingDomain.objects.select_for_update().get(pk=self.domain.pk)
            worker,errors=self.thread(self.member)
            self._wait_for_lock_waiter();worker.join(4)
            self.assertFalse(worker.is_alive())
        self.assertEqual(len(errors),1);self.assertEqual(str(errors[0]),'OUTCOME_REQUIRES_READBACK')
        self.assertEqual(TenantMembership.objects.count(),0);self.assertEqual(MembershipManagementAudit.objects.count(),0)

    def test_publication_audit_failure_is_atomic(self):
        self.publishing_grant()
        with connection.cursor() as c:
            c.execute("""CREATE FUNCTION crm_synthetic_management_audit_fail() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN RAISE EXCEPTION 'synthetic'; END $$;
                CREATE TRIGGER synthetic_management_audit_fail BEFORE INSERT ON crm_sharingaccessaudit
                FOR EACH ROW EXECUTE FUNCTION crm_synthetic_management_audit_fail();""")
        try:
            self.assert_code('OUTCOME_REQUIRES_READBACK',self.publication)
            self.assertEqual(SharingAgreement.objects.count(),0);self.assertEqual(SharingAccessAudit.objects.count(),0)
        finally:
            with connection.cursor() as c:
                c.execute('DROP TRIGGER synthetic_management_audit_fail ON crm_sharingaccessaudit; DROP FUNCTION crm_synthetic_management_audit_fail()')


class ManagementMigrationTests(TransactionTestCase):
    old=('crm','0038_canonical_writer_foundation')
    new=('crm','0039_access_management_journey')

    def tearDown(self):
        executor=MigrationExecutor(connection);executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_additive_roundtrip_preserves_memberships_and_no_seed(self):
        MigrationExecutor(connection).migrate([self.old])
        apps=MigrationExecutor(connection).loader.project_state([self.old]).apps
        user=apps.get_model('auth','User').objects.create(username='synthetic-old')
        tenant=apps.get_model('crm','Tenant').objects.create(name='Synthetic',slug='synthetic-old')
        membership=apps.get_model('crm','TenantMembership').objects.create(user_id=user.pk,tenant_id=tenant.pk,role='leser',is_active=False)
        before=apps.get_model('crm','TenantMembership').objects.values().get(pk=membership.pk)
        MigrationExecutor(connection).migrate([self.new])
        self.assertEqual(TenantMembership.objects.values().get(pk=membership.pk),before)
        for model in (Grant,GrantRevocation,MembershipManagementAudit):self.assertEqual(model.objects.count(),0)
        MigrationExecutor(connection).migrate([self.old]);MigrationExecutor(connection).migrate([self.new])
        self.assertEqual(TenantMembership.objects.values().get(pk=membership.pk),before)

    def test_reverse_refuses_legal_evidence(self):
        user=get_user_model().objects.create_user(username='synthetic-legal')
        domain=SharingDomain.objects.create(name='Synthetic',slug='synthetic-legal')
        SharingAgreement.objects.create(sharing_domain=domain,version=1,text='Synthetic only',
            created_by=user,effective_at=timezone.now(),legal_approval_reference='SYNTHETIC')
        with self.assertRaisesMessage(RuntimeError,'Cannot discard legal approval'),transaction.atomic():
            MigrationExecutor(connection).migrate([self.old])
