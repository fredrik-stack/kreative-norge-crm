"""Synthetic API -> processing -> approval -> ledger -> PUBLIC integration."""
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.parse import urlsplit

from PIL import Image
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import OperationalError
from django.test import TransactionTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from crm.models import Organization, OrganizationImageRelease, OrganizationImageSelection, ImageReviewEvent, Tenant, TenantMembership
from crm.services.images.brave import BraveImageSearchError, search_brave_images
from crm.services.images.candidates import discover_brave_image_candidates, render_candidate_preview, ImageCandidatePermissionDenied
from crm import test_image_release_workflow as workflow
from image_safety.anchor import anchor_current_head
from image_safety.bridge import SafetyBridgeOperations
from image_safety.ledger import PublicImageSafetyLedger


@override_settings(IMAGE_ASSET_FEATURE_ENABLED=True, SECURE_SSL_REDIRECT=False)
class BraveAccountBoundaryTests(TestCase):
    def setUp(self):
        self.owner=get_user_model().objects.create_user(username='synthetic-owner')
        self.other=get_user_model().objects.create_user(username='synthetic-other',is_staff=True,is_superuser=True)
        self.tenant=Tenant.objects.create(name='Synthetic',slug='synthetic')
        self.org=Organization.objects.create(tenant=self.tenant,name='Synthetic actor')
        TenantMembership.objects.create(user=self.owner,tenant=self.tenant,role='redigerer')
        self.scope=override_settings(BRAVE_IMAGE_SEARCH_USER_ID=self.owner.pk,BRAVE_IMAGE_SEARCH_API_KEY='synthetic-only-not-a-real-key')
        self.scope.enable();self.addCleanup(self.scope.disable)
        self.client=APIClient()
        self.root=f'/api/tenants/{self.tenant.pk}/organizations/{self.org.pk}/images/'

    def test_only_explicit_active_account_may_reach_provider(self):
        transport=Mock(return_value=(200,'application/json',b'{"results":[]}'))
        self.assertEqual(search_brave_images('Synthetic',actor=self.owner,transport=transport),())
        transport.assert_called_once();transport.reset_mock()
        for actor in (None,self.other):
            with self.subTest(actor=actor),self.assertRaises(BraveImageSearchError):
                search_brave_images('Synthetic',actor=actor,transport=transport)
        with override_settings(BRAVE_IMAGE_SEARCH_USER_ID=None),self.assertRaises(BraveImageSearchError):
            search_brave_images('Synthetic',actor=self.owner,transport=transport)
        get_user_model().objects.filter(pk=self.owner.pk).update(is_active=False)
        with self.assertRaises(BraveImageSearchError):search_brave_images('Synthetic',actor=self.owner,transport=transport)
        transport.assert_not_called()

    def test_api_superuser_does_not_bypass_account_boundary(self):
        self.client.force_authenticate(self.other)
        for method,path,payload in [('get','search-context/',{}),('post','brave-search/',{'query':'Synthetic','query_edited':True})]:
            with self.subTest(path=path):
                response=getattr(self.client,method)(self.root+path,payload,format='json')
                self.assertEqual(response.status_code,403)
                self.assertEqual(response.json()['code'],'brave_not_authorized')
        state=self.client.get(self.root+'state/').json();self.assertFalse(state['brave_search_enabled'])
        self.client.force_authenticate(self.owner)
        context=self.client.get(self.root+'search-context/')
        self.assertEqual(context.status_code,200)
        self.assertEqual(context['Cache-Control'],'private, no-store, max-age=0')
        self.assertTrue(self.client.get(self.root+'state/').json()['brave_search_enabled'])
        self.assertEqual(self.client.get(self.root.replace(str(self.tenant.pk)+'/organizations','999999/organizations')+'search-context/').status_code,403)

    def test_old_brave_refs_cannot_outlive_account_authority(self):
        from crm.test_brave_image_search import brave_result
        with patch('crm.services.images.candidates.search_brave_images',return_value=(brave_result(),)):
            _,_,candidates=discover_brave_image_candidates(actor=self.owner,tenant_id=self.tenant.pk,organization_id=self.org.pk,query='Synthetic',query_edited=True)
        with override_settings(BRAVE_IMAGE_SEARCH_USER_ID=self.other.pk),patch('crm.services.images.candidates.fetch_external_resource') as fetch:
            with self.assertRaises(ImageCandidatePermissionDenied):
                render_candidate_preview(actor=self.owner,tenant_id=self.tenant.pk,organization_id=self.org.pk,candidate_ref=candidates[0].candidate_ref)
            fetch.assert_not_called()


@override_settings(SECURE_SSL_REDIRECT=False, PUBLIC_IMAGE_SERVING_ENABLED=True,
    PUBLIC_IMAGE_PROJECTION_ENABLED=True,PUBLIC_IMAGE_API_SCHEMA_ENABLED=True,
    PUBLIC_IMAGE_PUBLIC_CUTOVER_ENABLED=True,PUBLIC_IMAGE_TAKEDOWN_ENABLED=True,
    PUBLIC_SITE_ORIGIN='https://public.example.no',PUBLIC_MEDIA_ORIGIN='https://media.example.no')
class EditorPublicationTests(TransactionTestCase):
    reset_sequences=True

    def setUp(self):
        workflow.OrganizationImageReleaseWorkflowTests.setUp(self)
        self.target=Organization.objects.create(tenant=self.tenant,name='Synthetic PUBLIC actor',org_number='synthetic-public',is_published=True,note='private synthetic note')
        stores=settings.STORAGES|{'image_originals_private':{'BACKEND':'django.core.files.storage.FileSystemStorage','OPTIONS':{'location':Path(self.temporary.name)/'private','base_url':None}}}
        storage=override_settings(STORAGES=stores);storage.enable();self.addCleanup(storage.disable)
        ledger=PublicImageSafetyLedger(Path(self.temporary.name)/'safety'/'ledger.sqlite3');ledger.initialize();ledger.upgrade_schema_v2()
        anchor=workflow.InProcessAnchor();anchor_current_head(ledger,anchor,expected_repository_id=workflow.IN_PROCESS_REPOSITORY_ID)
        self.bridge=workflow.InProcessSafetyBridgeClient(SafetyBridgeOperations(ledger=ledger,anchor_backend=anchor,expected_repository_id=workflow.IN_PROCESS_REPOSITORY_ID))
        for module in ('releases','projection','serving','safety_guards'):
            p=patch(f'crm.services.images.{module}.ImageSafetyBridgeClient',return_value=self.bridge);p.start();self.addCleanup(p.stop)
        self.client=APIClient();self.client.force_authenticate(self.user)
        self.root=f'/api/tenants/{self.tenant.pk}/organizations/{self.target.pk}/images/'

    def upload(self,color='red'):
        body=BytesIO();Image.new('RGB',(1800,1200),color).save(body,format='PNG')
        result=self.client.post(self.root+'upload-process/',{'file':SimpleUploadedFile('synthetic.png',body.getvalue(),content_type='image/png'),'image_kind':'photo','focus_x':'.37','focus_y':'.68','zoom':'1.25'},format='multipart')
        self.assertEqual(result.status_code,200,result.data)
        return result.json()['approval_ref']

    def approve(self,ref,revision):
        result=self.client.post(self.root+'approve/',{'approval_ref':ref,'expected_revision':revision,'rights_confirmed':True,'alt_text':'Synthetic public image','public_credit':'Synthetic author'},format='json')
        self.assertEqual(result.status_code,200,result.data);return result.json()['revision']

    def publish(self,revision):
        return self.client.post(self.root+'publish/',{'expected_revision':revision,'confirmed':True},format='json')

    def public(self):
        result=APIClient().get('/api/public/actors/');self.assertEqual(result.status_code,200)
        rows=result.json();rows=rows if isinstance(rows,list) else rows['results']
        return next(x for x in rows if x['org_number']=='synthetic-public')

    def test_real_upload_approval_publication_replacement_fallback_and_history(self):
        self.assertEqual(self.public()['image']['kind'],'system_fallback')
        ref=self.upload()
        denied=self.client.post(self.root+'approve/',{'approval_ref':ref,'expected_revision':0},format='json')
        self.assertEqual(denied.status_code,400);self.assertFalse(self.target.image_selections.exists())
        revision=self.approve(ref,0)
        self.assertEqual(self.public()['image']['kind'],'system_fallback')
        self.assertEqual(OrganizationImageRelease.objects.count(),0)
        detail=self.client.get(f'/api/tenants/{self.tenant.pk}/organizations/{self.target.pk}/').json()
        self.assertIn('fallback-square.png',detail['preview_image_url'])
        event=ImageReviewEvent.objects.get(organization=self.target)
        self.assertIn('kan publiseres',event.approval_text_snapshot)
        result=self.publish(revision);self.assertEqual(result.status_code,200,result.data)
        first=result.json()['release_id'];image=self.public()['image'];self.assertEqual(image['kind'],'asset')
        editor=self.client.get(f'/api/tenants/{self.tenant.pk}/organizations/').json()
        self.assertEqual(next(r for r in editor if r['id']==self.target.pk)['preview_image_url'],image['square']['url'])
        self.assertEqual(image['credit'],'Synthetic author')
        self.assertEqual(image['alt_text'],'Synthetic public image')
        self.assertNotIn('note',self.public());self.assertNotIn('tenants/',str(image))
        for variant in ('square','landscape','share'):
            response=APIClient().get(urlsplit(image[variant]['url']).path)
            self.assertEqual(response.status_code,200);self.assertIn('X-Accel-Redirect',response)
        html=APIClient().get(f'/public/actors/id/{self.target.pk}/');self.assertEqual(html.status_code,200)
        self.assertContains(html,image['square']['url'])
        repeat=self.publish(revision);self.assertEqual(repeat.status_code,200)
        self.assertEqual(repeat.json()['release_id'],first);self.assertEqual(OrganizationImageRelease.objects.count(),1)
        second_rev=self.approve(self.upload('blue'),revision)
        self.assertEqual(self.public()['image']['kind'],'system_fallback')
        self.assertEqual(APIClient().get(urlsplit(image['square']['url']).path).status_code,404)
        second=self.publish(second_rev);self.assertEqual(second.status_code,200,second.data)
        self.assertNotEqual(second.json()['release_id'],first)
        fallback=self.client.post(self.root+'fallback/',{'expected_revision':second_rev,'confirmed':True},format='json')
        self.assertEqual(fallback.status_code,200,fallback.data)
        self.assertEqual(self.public()['image']['kind'],'system_fallback')
        self.assertEqual(OrganizationImageRelease.objects.count(),2)
        self.assertEqual(self.target.image_selections.count(),3)
        self.assertEqual(ImageReviewEvent.objects.filter(organization=self.target).count(),3)
        self.target.refresh_from_db();self.assertTrue(self.target.is_published);self.assertEqual(self.target.note,'private synthetic note')

    def test_missing_confirmation_stale_wrong_scope_reader_and_unpublished(self):
        revision=self.approve(self.upload(),0)
        self.assertEqual(self.client.post(self.root+'publish/',{'expected_revision':revision,'confirmed':'true'},format='json').status_code,400)
        self.assertEqual(self.publish(0).status_code,409)
        self.assertEqual(self.client.post(self.root+'publish/',{'expected_revision':revision,'confirmed':True,'release_id':'caller-control'},format='json').status_code,400)
        Organization.objects.filter(pk=self.target.pk).update(is_published=False)
        self.assertEqual(self.publish(revision).status_code,409)
        TenantMembership.objects.filter(user=self.user).update(role='leser')
        self.assertEqual(self.publish(revision).status_code,403)
        TenantMembership.objects.filter(user=self.user).update(role='gruppeadmin',is_active=False)
        self.assertEqual(self.publish(revision).status_code,403)
        other=Tenant.objects.create(name='Other scope',slug='other-scope')
        TenantMembership.objects.create(user=self.user,tenant=other,role='gruppeadmin')
        wrong=self.root.replace(f'/tenants/{self.tenant.pk}/',f'/tenants/{other.pk}/')
        self.assertEqual(self.client.post(wrong+'publish/',{'expected_revision':revision,'confirmed':True},format='json').status_code,404)
        self.assertEqual(OrganizationImageRelease.objects.count(),0)

    @override_settings(STRICT_TENANT_ACCESS_ENABLED=True)
    def test_publication_reuses_strict_request_boundary_without_shared_activation(self):
        revision=self.approve(self.upload(),0)
        self.assertEqual(self.publish(revision).status_code,200)

    def test_lost_activation_response_is_controlled_and_reuses_uuid(self):
        revision=self.approve(self.upload(),0);activate=self.bridge.activate
        def lose(**kwargs):
            activate(**kwargs)
            raise workflow.ImageSafetyBridgeUnavailable('synthetic_lost_response','synthetic lost response',retryable=True)
        with patch.object(self.bridge,'activate',side_effect=lose):
            response=self.publish(revision)
        self.assertEqual(response.status_code,503,response.data)
        # DB transaction rolled back, permanent reservation and bytes survive.
        self.assertEqual(OrganizationImageRelease.objects.count(),0)
        self.assertEqual(self.public()['image']['kind'],'system_fallback')
        files=sorted(p.relative_to(self.delivery_root) for p in self.delivery_root.rglob('*') if p.is_file())
        self.assertEqual(len(files),3)
        result=self.publish(revision);self.assertEqual(result.status_code,200,result.data)
        self.assertEqual(files,sorted(p.relative_to(self.delivery_root) for p in self.delivery_root.rglob('*') if p.is_file()))
        self.assertEqual(OrganizationImageRelease.objects.count(),1)

    def test_binding_failure_is_atomic_and_returns_sanitized_error(self):
        revision=self.approve(self.upload(),0)
        with patch('crm.services.images.releases._bind_release',side_effect=OperationalError('synthetic private diagnostics')):
            response=self.publish(revision)
        self.assertEqual(response.status_code,503);self.assertNotIn('diagnostics',str(response.data))
        self.assertEqual(OrganizationImageRelease.objects.count(),0)
        self.assertEqual(self.public()['image']['kind'],'system_fallback')
        self.assertEqual(self.publish(revision).status_code,200)

    def test_new_publish_route_cannot_revive_denied_bytes_after_old_state_restore(self):
        from crm.services.images.takedown import formal_takedown_organization_image
        revision=self.approve(self.upload(),0)
        self.assertEqual(self.publish(revision).status_code,200)
        old=self.target.image_selections.get(status='active')
        formal_takedown_organization_image(actor=self.user,tenant_id=self.tenant.pk,
            organization_id=self.target.pk,reason_code='rights_request',bridge=self.bridge)
        # Synthetic old DB-state restoration; ledger remains authoritative.
        self.target.image_selections.filter(status='active').update(status='archived')
        OrganizationImageSelection.objects.filter(pk=old.pk).update(status='active')
        result=self.publish(revision)
        self.assertEqual(result.status_code,409,result.data)
        self.assertEqual(result.json()['code'],'image_denied')
        self.assertEqual(self.public()['image']['kind'],'system_fallback')
        self.assertEqual(OrganizationImageRelease.objects.count(),1)

    def test_concurrent_publication_reuses_the_same_permanent_release(self):
        from django.db import transaction
        from crm import test_phase6a2_backfill as backfill_tests
        import threading
        revision=self.approve(self.upload(),0);responses=[];barrier=threading.Barrier(2)
        def call():
            client=APIClient();client.force_authenticate(self.user);barrier.wait(3)
            responses.append(client.post(self.root+'publish/',{'expected_revision':revision,'confirmed':True},format='json'))
        with transaction.atomic():
            Organization.objects.select_for_update().get(pk=self.target.pk)
            first,first_errors=backfill_tests.LegacyBackfillTests.thread(self,call)
            second,second_errors=backfill_tests.LegacyBackfillTests.thread(self,call)
            backfill_tests.LegacyBackfillTests._wait_for_lock_waiter(self)
        first.join(6);second.join(6)
        self.assertFalse(first.is_alive() or second.is_alive());self.assertEqual(first_errors+second_errors,[])
        self.assertEqual([r.status_code for r in responses],[200,200])
        self.assertEqual(responses[0].json()['release_id'],responses[1].json()['release_id'])
        self.assertEqual(OrganizationImageRelease.objects.count(),1)

    def test_waiting_publication_reauthorizes_after_user_deactivation(self):
        from django.db import transaction
        from crm import test_phase6a2_backfill as backfill_tests
        revision=self.approve(self.upload(),0);responses=[]
        with transaction.atomic():
            get_user_model().objects.select_for_update().get(pk=self.user.pk)
            worker,errors=backfill_tests.LegacyBackfillTests.thread(self,lambda:responses.append(self.publish(revision)))
            backfill_tests.LegacyBackfillTests._wait_for_lock_waiter(self)
            get_user_model().objects.filter(pk=self.user.pk).update(is_active=False)
        worker.join(6);self.assertFalse(worker.is_alive());self.assertEqual(errors,[])
        self.assertEqual(responses[0].status_code,403)
        self.assertEqual(OrganizationImageRelease.objects.count(),0)
