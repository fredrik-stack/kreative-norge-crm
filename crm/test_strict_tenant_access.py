"""Synthetic PostgreSQL evidence for the opt-in legacy authority transition."""
import importlib
import os
import subprocess
import threading
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import transaction
from django.test import TransactionTestCase, override_settings
from rest_framework.test import APIClient
from rest_framework.exceptions import ValidationError

from crm.models import Tenant, TenantMembership, Organization, SharingDomain, ImportJob
from crm.permissions import get_user_tenant_role, get_user_global_role
from crm.tenant_access import require_tenant_operation
from crm.test_phase6a1_foundation import fixture_bound
from crm import test_phase6a2_backfill as backfill_tests


@override_settings(STRICT_TENANT_ACCESS_ENABLED=True, SECURE_SSL_REDIRECT=False)
class StrictTenantTests(TransactionTestCase):
    thread = backfill_tests.LegacyBackfillTests.thread
    _wait_for_lock_waiter = backfill_tests.LegacyBackfillTests._wait_for_lock_waiter

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="synthetic-member")
        self.domain = SharingDomain.objects.create(name="Synthetic", slug="synthetic")
        self.foreign_domain = SharingDomain.objects.create(name="Foreign", slug="foreign")
        self.tenant = fixture_bound(Tenant, name="Synthetic", slug="synthetic", sharing_domain=self.domain)
        self.foreign = fixture_bound(Tenant, name="Foreign", slug="foreign", sharing_domain=self.foreign_domain)
        self.org = fixture_bound(Organization, tenant=self.tenant, sharing_domain=self.domain, name="Synthetic", note="  exact\n")
        self.client = APIClient(); self.client.force_authenticate(self.user)
        self.root = f"/api/tenants/{self.tenant.pk}/"

    def member(self, role="redigerer", **values):
        return TenantMembership.objects.create(user=self.user, tenant=self.tenant, role=role, **values)

    def get(self, suffix="organizations/"):
        return self.client.get(self.root+suffix)

    def test_superuser_staff_global_groups_are_not_grants(self):
        self.user.is_superuser = self.user.is_staff = True; self.user.save()
        for role in TenantMembership.Role.values:
            self.user.groups.add(Group.objects.create(name=role))
        self.assertIsNone(get_user_global_role(self.user))
        self.assertIsNone(get_user_tenant_role(self.user, self.tenant.pk))
        self.assertEqual(self.get().status_code,403)
        self.assertEqual(self.client.get('/api/tenants/').status_code,403)
        self.assertEqual(self.client.get('/api/auth/session/').json()['user']['memberships'],[])
        self.assertFalse(self.client.get('/api/auth/session/').json()['user']['can_access_admin'])

    def test_inactive_user_membership_and_unknown_role(self):
        row = self.member(is_active=False)
        self.assertEqual(self.get().status_code,403)
        row.is_active=True; row.role="unknown"; row.save()
        self.assertEqual(self.get().status_code,403)
        row.role="redigerer"; row.save()
        get_user_model().objects.filter(pk=self.user.pk).update(is_active=False)
        # Stale request.user/is_active cannot authorize a fresh request.
        self.assertEqual(self.get().status_code,403)
        self.assertIsNone(get_user_tenant_role(self.user,self.tenant.pk))

    def test_cross_tenant_domain_and_exact_lists(self):
        TenantMembership.objects.create(user=self.user,tenant=self.foreign,role="superadmin")
        self.assertEqual(self.get().status_code,403)
        data=self.client.get('/api/tenants/').json()
        self.assertEqual([x['id'] for x in data],[self.foreign.pk])
        self.assertEqual(data[0]['current_user_role'],'superadmin')
        self.assertEqual([x['tenant'] for x in self.client.get('/api/auth/session/').json()['user']['memberships']],[self.foreign.pk])
        self.assertEqual(self.client.get(f'/api/tenants/{self.foreign.pk}/organizations/{self.org.pk}/').status_code,404)

    def test_role_action_matrix_and_no_agreement_dependency(self):
        row=self.member()
        for role in TenantMembership.Role.values:
            with self.subTest(role=role):
                row.role=role; row.save()
                self.assertEqual(self.get().status_code,200)
                response=self.client.patch(self.root+f'organizations/{self.org.pk}/',{'name':'Synthetic edited'},format='json')
                self.assertEqual(response.status_code,403 if role=='leser' else 200)
                self.assertEqual(self.get('import-jobs/').status_code,403 if role=='leser' else 200)
                self.assertEqual(self.get('export-jobs/').status_code,403 if role=='leser' else 200)
                tag=self.client.post(self.root+'tags/',{'name':'Synthetic '+role},format='json')
                self.assertEqual(tag.status_code,403 if role=='leser' else 201)
                if tag.status_code==201:
                    self.assertEqual(self.client.delete(self.root+f"tags/{tag.json()['id']}/").status_code,403 if role=='redigerer' else 204)
        self.org.refresh_from_db(); self.assertEqual(self.org.note,'  exact\n')

    def test_all_private_router_surfaces_deny_without_membership(self):
        for suffix in ['organizations/','persons/','tags/','organization-people/','person-contacts/','import-jobs/','export-jobs/',f'organizations/{self.org.pk}/images/state/']:
            with self.subTest(suffix=suffix): self.assertEqual(self.get(suffix).status_code,403)

    def test_revocation_next_request_and_role_downgrade(self):
        row=self.member(); self.assertEqual(self.get().status_code,200)
        TenantMembership.objects.filter(pk=row.pk).update(is_active=False)
        self.assertEqual(self.get().status_code,403)
        TenantMembership.objects.filter(pk=row.pk).update(is_active=True,role='leser')
        self.assertEqual(self.get().status_code,200)
        self.assertEqual(self.client.patch(self.root+f'organizations/{self.org.pk}/',{'name':'Denied'},format='json').status_code,403)
        row.delete(); self.assertEqual(self.get().status_code,403)

    def test_all_admin_routes_blocked_even_with_explicit_superadmin_membership(self):
        self.user.is_superuser=self.user.is_staff=True; self.user.set_password('synthetic'); self.user.save()
        self.member('superadmin'); client=APIClient(); client.force_login(self.user)
        for url in ['/admin/','/admin/login/','/admin/crm/organization/','/admin/crm/tenantmembership/','/admin/auth/user/','/admin/auth/group/add/']:
            for method in ['get','post']:
                with self.subTest(url=url,method=method): self.assertEqual(getattr(client,method)(url).status_code,403)

    def test_direct_actor_services_and_jobs_have_no_reusable_grant(self):
        self.user.is_superuser=True; self.user.save(); self.member('superadmin')
        from crm.services.images import candidates,selections,takedown
        decisions=importlib.import_module('crm.services.import.image_decisions')
        for fn in [candidates._validate_actor,selections._validate_actor_capability,takedown._validate_actor,decisions._require_actor]:
            with self.subTest(fn=fn):
                with self.assertRaises(Exception) as raised: fn(self.user,self.tenant.pk)
                self.assertIn(type(raised.exception).__name__,['ImageCandidatePermissionDenied','ImageSelectionPermissionDenied','ImageTakedownPermissionDenied','ImportImageDecisionPermissionDenied'])
        job=ImportJob.objects.create(tenant=self.tenant,created_by=self.user,filename='synthetic.csv')
        for module,name in [('commit','commit_import_job'),('preview','run_import_preview'),('preview','generate_import_job_ai'),('reporting','save_error_report')]:
            with self.subTest(name=name), self.assertRaises(PermissionDenied):
                getattr(importlib.import_module('crm.services.import.'+module),name)(job)
        job.refresh_from_db(); self.assertNotEqual(job.status,'COMMITTING')
        with self.assertRaises(PermissionDenied): require_tenant_operation(self.tenant.pk,{'superadmin'},actor=self.user)

    def test_authorized_api_import_reaches_guarded_service(self):
        self.member()
        job=ImportJob.objects.create(tenant=self.tenant,created_by=self.user,filename='synthetic.csv')
        def preview(job):
            require_tenant_operation(job.tenant_id,{'redigerer'},actor=self.user)
        with patch('crm.views.run_import_preview',side_effect=preview) as fn:
            response=self.client.post(self.root+f'import-jobs/{job.pk}/preview/')
        self.assertEqual(response.status_code,200); fn.assert_called_once()
        with self.assertRaises(PermissionDenied): preview(job) # no context leaks after response

    def test_image_services_use_exact_request_actor_tenant_and_action(self):
        from crm.services.images import selections, takedown
        self.member('redigerer')
        def state(**kwargs):
            selections._validate_actor_capability(self.user,self.tenant.pk)
            with self.assertRaises(selections.ImageSelectionPermissionDenied):
                selections._validate_actor_capability(self.user,self.foreign.pk)
            with self.assertRaises(takedown.ImageTakedownPermissionDenied):
                takedown._validate_actor(self.user,self.tenant.pk)
            return {}
        with patch('crm.views.get_organization_image_state',side_effect=state) as fn:
            self.assertEqual(self.get(f'organizations/{self.org.pk}/images/state/').status_code,200)
        fn.assert_called_once()

    def test_error_response_rolls_back_partial_write(self):
        self.member()
        def fail(view,serializer):
            serializer.save()
            raise ValidationError('Synthetic failure after write')
        with patch('crm.views.OrganizationViewSet.perform_update',fail):
            response=self.client.patch(self.root+f'organizations/{self.org.pk}/',{'name':'Must roll back'},format='json')
        self.assertEqual(response.status_code,400)
        self.org.refresh_from_db(); self.assertEqual(self.org.name,'Synthetic')

    def test_unsupported_operators_block_before_effects(self):
        from django.core.management import get_commands, load_command_class
        commands=['backfill_phone_identity','audit_legacy_image_sources','refresh_organization_previews','backfill_legacy_domain','verify_image_storage_persistence','copy_legacy_tenant_notes','compare_domain_reads','audit_public_image_projection','cleanup_image_storage_orphans','publish_existing_email_contacts','repair_person_contacts']
        for name in commands:
            with self.subTest(name=name), self.assertRaisesMessage(CommandError,'disabled in strict tenant mode'):
                load_command_class(get_commands()[name],name).handle()

    @override_settings(STRICT_TENANT_ACCESS_ENABLED=False)
    def test_off_mode_preserves_global_superuser_inactive_membership_and_admin(self):
        self.user.is_superuser=self.user.is_staff=True; self.user.save()
        self.assertEqual(self.get().status_code,200)
        self.assertEqual(get_user_tenant_role(self.user,self.foreign.pk),'superadmin')
        self.user.is_superuser=False; self.user.save()
        self.user.groups.add(Group.objects.create(name='redigerer'))
        self.assertEqual(self.get().status_code,200)
        self.member('leser',is_active=False)
        self.assertEqual(get_user_tenant_role(self.user,self.tenant.pk),'leser')
        self.assertEqual(self.get().status_code,200)
        self.user.is_superuser=True; self.user.save()
        client=APIClient(); client.force_login(self.user)
        self.assertEqual(client.get('/admin/').status_code,200)

    def test_public_unchanged_and_gates_independent(self):
        self.member('leser')
        with override_settings(ACCESS_MANAGEMENT_ENABLED=False,SHARING_ACCESS_ENABLED=False):
            self.assertEqual(self.get().status_code,200)
        with override_settings(ACCESS_MANAGEMENT_ENABLED=True,SHARING_ACCESS_ENABLED=True):
            self.assertEqual(self.get().status_code,200)
        strict=self.client.get('/api/public/organizations/').content
        with override_settings(STRICT_TENANT_ACCESS_ENABLED=False):
            self.assertEqual(self.client.get('/api/public/organizations/').content,strict)

    def test_inflight_write_fences_revocation_and_next_request_denies(self):
        row=self.member(); entered=threading.Event(); release=threading.Event(); responses=[]
        original=Organization.save
        def save(obj,*args,**kwargs):
            if obj.pk==self.org.pk:
                entered.set(); self.assertTrue(release.wait(5))
            return original(obj,*args,**kwargs)
        with patch.object(Organization,'save',save):
            writer,errors=self.thread(lambda:responses.append(self.client.patch(self.root+f'organizations/{self.org.pk}/',{'name':'Authorized before revoke'},format='json')))
            self.assertTrue(entered.wait(4))
            revoker,revoke_errors=self.thread(lambda:TenantMembership.objects.filter(pk=row.pk).update(is_active=False))
            self._wait_for_lock_waiter(); release.set()
            writer.join(6); revoker.join(6)
        self.assertFalse(writer.is_alive()); self.assertFalse(revoker.is_alive())
        self.assertEqual(errors+revoke_errors,[]); self.assertEqual(responses[0].status_code,200)
        self.assertEqual(self.get().status_code,403)

    def test_waiting_request_reauthorizes_after_revocation(self):
        row=self.member(); responses=[]
        with transaction.atomic():
            TenantMembership.objects.select_for_update().get(pk=row.pk)
            worker,errors=self.thread(lambda:responses.append(self.get()))
            self._wait_for_lock_waiter()
            TenantMembership.objects.filter(pk=row.pk).update(is_active=False)
        worker.join(5); self.assertFalse(worker.is_alive()); self.assertEqual(errors,[])
        self.assertEqual(responses[0].status_code,403)

    def test_lock_timeout_fails_without_write(self):
        row=self.member(); responses=[]
        with transaction.atomic():
            TenantMembership.objects.select_for_update().get(pk=row.pk)
            worker,errors=self.thread(lambda:responses.append(self.client.patch(self.root+f'organizations/{self.org.pk}/',{'name':'Denied'},format='json')))
            worker.join(5)
        self.assertFalse(worker.is_alive()); self.assertEqual(errors,[])
        self.assertEqual(responses[0].status_code,503)
        self.org.refresh_from_db(); self.assertEqual(self.org.name,'Synthetic')

    def test_invalid_gate_value_stops_startup(self):
        env=os.environ|{'STRICT_TENANT_ACCESS_ENABLED':'truue','DJANGO_SETTINGS_MODULE':'config.settings'}
        result=subprocess.run([os.sys.executable,'-c','import config.settings'],env=env,capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('Invalid STRICT_TENANT_ACCESS_ENABLED',result.stderr)
