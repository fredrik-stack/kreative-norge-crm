from __future__ import annotations

from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import resolve, reverse
from django.utils import timezone
from drf_spectacular.generators import SchemaGenerator

from image_safety.release_keys import build_public_release_key

from .models import (
    ImageAsset,
    ImageRendition,
    ImageRenditionSet,
    Organization,
    OrganizationImageRelease,
    OrganizationImageReleaseRendition,
    OrganizationImageSelection,
    OrganizationPerson,
    Person,
    PersonContact,
    Tenant,
)
from .services.images.bridge_client import (
    BridgeAuthorization,
    BridgeLegacyGuard,
    ImageSafetyBridgeUnavailable,
)
from .services.images.projection import (
    prefetch_public_image_projection,
    project_public_image,
)
from .views_public import PublicActorPublicViewSet


class ProjectionBridge:
    calls = []
    category_by_variant = {}
    error = None

    def __init__(self, *, timeout):
        self.timeout = timeout

    @classmethod
    def reset(cls):
        cls.calls = []
        cls.category_by_variant = {}
        cls.error = None

    def authorize(self, **payload):
        type(self).calls.append(payload)
        if type(self).error:
            raise type(self).error
        category = type(self).category_by_variant.get(payload["variant"], "authorized")
        return BridgeAuthorization(
            authorized=category == "authorized",
            category=category,
            release_id=payload["release_id"],
            variant=payload["variant"],
            read_cursor=11,
        )

    def legacy_guard(self, **payload):
        return BridgeLegacyGuard(blocked=False, read_cursor=11)


@override_settings(
    IMAGE_ASSET_FEATURE_ENABLED=True,
    PUBLIC_IMAGE_RELEASE_MATERIALIZATION_ENABLED=True,
    PUBLIC_IMAGE_SERVING_ENABLED=True,
    PUBLIC_IMAGE_PROJECTION_ENABLED=True,
    PUBLIC_IMAGE_API_SCHEMA_ENABLED=False,
    PUBLIC_IMAGE_PUBLIC_CUTOVER_ENABLED=False,
    PUBLIC_SITE_ORIGIN="https://public.example.no",
    PUBLIC_MEDIA_ORIGIN="https://media.example.no",
)
class PublicImageProjectionTests(TestCase):
    def setUp(self):
        ProjectionBridge.reset()
        bridge_patch = patch(
            "crm.services.images.projection.ImageSafetyBridgeClient",
            ProjectionBridge,
        )
        bridge_patch.start()
        self.addCleanup(bridge_patch.stop)
        legacy_guard_patch = patch(
            "crm.services.images.safety_guards.ImageSafetyBridgeClient",
            ProjectionBridge,
        )
        legacy_guard_patch.start()
        self.addCleanup(legacy_guard_patch.stop)

        self.user = get_user_model().objects.create_user(username="projection-user")
        self.tenant = Tenant.objects.create(name="Projection", slug="projection")
        self.organization = Organization.objects.create(
            tenant=self.tenant,
            name="Projected actor",
            org_number="998544092",
            is_published=True,
            publish_phone=False,
            phone="12345678",
            thumbnail_image_url="https://legacy.example.no/thumbnail.jpg",
            og_image_url="https://legacy.example.no/preview.jpg",
        )
        asset = ImageAsset.objects.create(
            tenant=self.tenant,
            private_storage_key="assets/projection.jpg",
            checksum_sha256="a" * 64,
            original_format="jpeg",
            mime_type="image/jpeg",
            width=1600,
            height=900,
            file_size_bytes=100,
            validation_version="test-v1",
        )
        self.rendition_set = ImageRenditionSet.objects.create(
            tenant=self.tenant,
            asset=asset,
            fit_mode="cover",
            processing_version="test-v1",
            render_config_hash_sha256="b" * 64,
        )
        dimensions = {
            "square": (512, 512),
            "landscape": (800, 450),
            "share": (1200, 630),
        }
        renditions = []
        for index, (variant, (width, height)) in enumerate(dimensions.items(), start=1):
            checksum = f"{index:x}" * 64
            rendition = ImageRendition.objects.create(
                tenant=self.tenant,
                rendition_set=self.rendition_set,
                variant=variant,
                output_format="webp",
                width=width,
                height=height,
                file_size_bytes=100 + index,
                checksum_sha256=checksum,
                artifact_storage_key=f"artifacts/{variant}-{checksum}.webp",
            )
            renditions.append(rendition)
        self.selection = OrganizationImageSelection.objects.create(
            tenant=self.tenant,
            organization=self.organization,
            selection_kind="asset",
            rendition_set=self.rendition_set,
            alt_text="",
            public_credit="",
            revision=1,
            status="active",
            locked_by=self.user,
            locked_at=timezone.now(),
        )
        self.release_id = str(uuid.uuid4())
        self.release = OrganizationImageRelease.objects._insert_from_release_service(
            [
                OrganizationImageRelease(
                    release_id=self.release_id,
                    tenant=self.tenant,
                    organization=self.organization,
                    selection=self.selection,
                    selection_revision_snapshot=1,
                    rendition_set=self.rendition_set,
                    key_schema_version=1,
                )
            ]
        )[0]
        self.mappings = tuple(
            OrganizationImageReleaseRendition.objects._insert_from_release_service(
                [
                    OrganizationImageReleaseRendition(
                        release=self.release,
                        rendition=rendition,
                        variant=rendition.variant,
                        output_format=rendition.output_format,
                        artifact_storage_key_snapshot=rendition.artifact_storage_key,
                        artifact_checksum_sha256_snapshot=rendition.checksum_sha256,
                        public_storage_key=build_public_release_key(
                            self.release_id,
                            rendition.variant,
                            rendition.output_format,
                        ),
                    )
                    for rendition in renditions
                ]
            )
        )

    def prefetched_organization(self):
        return prefetch_public_image_projection(
            Organization.objects.filter(pk=self.organization.pk)
        ).get()

    def test_asset_projection_is_complete_absolute_and_host_independent(self):
        result = project_public_image(self.prefetched_organization())

        self.assertEqual(result.projection.kind, "asset")
        self.assertEqual(result.projection.alt_text, "")
        self.assertIsNone(result.projection.credit)
        self.assertEqual(result.authorize_count, 3)
        self.assertEqual(result.safety_cursor, 11)
        self.assertEqual(
            (result.projection.square.width, result.projection.square.height),
            (512, 512),
        )
        self.assertEqual(
            (result.projection.landscape.width, result.projection.landscape.height),
            (800, 450),
        )
        self.assertEqual(
            (result.projection.share.width, result.projection.share.height),
            (1200, 630),
        )
        for variant in ("square", "landscape", "share"):
            url = getattr(result.projection, variant).url
            self.assertTrue(url.startswith("https://media.example.no/media/releases/"))
            self.assertNotIn("attacker", url)
        self.assertEqual(
            {call["variant"] for call in ProjectionBridge.calls},
            {"square", "landscape", "share"},
        )
        self.assertEqual(
            {call["source_checksum_sha256"] for call in ProjectionBridge.calls},
            {"a" * 64},
        )

        self.selection.public_credit = "Foto: Test"
        self.selection.save(update_fields=["public_credit"])
        credited = project_public_image(self.organization)
        self.assertEqual(credited.projection.credit, "Foto: Test")

    def test_fallback_is_static_versioned_and_never_legacy(self):
        no_selection = Organization.objects.create(
            tenant=self.tenant,
            name="No selection",
            org_number="111111111",
            is_published=True,
            thumbnail_image_url="https://legacy.example.no/unsafe.jpg",
        )
        result = project_public_image(no_selection)

        self.assertEqual(result.projection.kind, "system_fallback")
        self.assertEqual(result.reason, "no_active_selection")
        self.assertEqual(result.projection.alt_text, "")
        self.assertIsNone(result.projection.credit)
        self.assertEqual(
            result.projection.square.url,
            "https://public.example.no/static/crm/public-image-fallback/v1/"
            "fallback-square.png",
        )
        self.assertNotIn("legacy.example.no", repr(result.projection))

        fallback_root = (
            Path(__file__).resolve().parent
            / "static"
            / "crm"
            / "public-image-fallback"
            / "v1"
        )
        expected = {
            "fallback-square.png": (12423, "25c248"),
            "fallback-landscape.png": (11510, "3cc8c5"),
            "fallback-share.png": (17174, "1afe1d"),
        }
        for filename, (size, checksum_prefix) in expected.items():
            payload = (fallback_root / filename).read_bytes()
            self.assertEqual(len(payload), size)
            self.assertTrue(sha256(payload).hexdigest().startswith(checksum_prefix))
            emergency_payload = (fallback_root / f"emergency-{filename}").read_bytes()
            self.assertEqual(payload, emergency_payload)

    def test_selection_and_release_absence_fall_back_without_authorization(self):
        fallback_org = Organization.objects.create(
            tenant=self.tenant,
            name="Explicit fallback",
            org_number="444444444",
            is_published=True,
        )
        OrganizationImageSelection.objects.create(
            tenant=self.tenant,
            organization=fallback_org,
            selection_kind="system_fallback",
            rendition_set=None,
            alt_text="Technical fallback",
            public_credit="",
            revision=1,
            status="active",
            locked_by=self.user,
            locked_at=timezone.now(),
        )
        no_release_org = Organization.objects.create(
            tenant=self.tenant,
            name="No release",
            org_number="555555555",
            is_published=True,
        )
        OrganizationImageSelection.objects.create(
            tenant=self.tenant,
            organization=no_release_org,
            selection_kind="asset",
            rendition_set=self.rendition_set,
            alt_text="",
            public_credit="",
            revision=1,
            status="active",
            locked_by=self.user,
            locked_at=timezone.now(),
        )
        archived_org = Organization.objects.create(
            tenant=self.tenant,
            name="Archived selection",
            org_number="666666666",
            is_published=True,
        )
        OrganizationImageSelection.objects.create(
            tenant=self.tenant,
            organization=archived_org,
            selection_kind="system_fallback",
            rendition_set=None,
            alt_text="Archived fallback",
            public_credit="",
            revision=1,
            status="archived",
            locked_by=self.user,
            locked_at=timezone.now(),
        )

        explicit = project_public_image(fallback_org)
        missing = project_public_image(no_release_org)
        archived = project_public_image(archived_org)

        self.assertEqual(explicit.projection.kind, "system_fallback")
        self.assertEqual(explicit.reason, "selection_system_fallback")
        self.assertEqual(missing.projection.kind, "system_fallback")
        self.assertEqual(missing.reason, "release_missing")
        self.assertEqual(archived.projection.kind, "system_fallback")
        self.assertEqual(archived.reason, "no_active_selection")
        self.assertEqual(ProjectionBridge.calls, [])

    def test_safety_failure_and_any_negative_variant_fail_closed(self):
        for category in ("unknown", "not_active", "scope_mismatch", "checksum_denied"):
            with self.subTest(category=category):
                ProjectionBridge.reset()
                ProjectionBridge.category_by_variant = {"share": category}
                result = project_public_image(self.prefetched_organization())
                self.assertEqual(result.projection.kind, "system_fallback")
                self.assertEqual(result.reason, f"safety_{category}")
                self.assertNotIn("/media/releases/", repr(result.projection))

        ProjectionBridge.reset()
        ProjectionBridge.error = ImageSafetyBridgeUnavailable(
            "safety_unavailable", "synthetic", retryable=True
        )
        unavailable = project_public_image(self.prefetched_organization())
        self.assertEqual(unavailable.projection.kind, "system_fallback")
        self.assertEqual(unavailable.reason, "safety_unavailable")

    def test_unpublished_scope_revision_and_mapping_fail_closed(self):
        cases = []

        unpublished = self.prefetched_organization()
        unpublished.is_published = False
        cases.append((unpublished, "organization_unpublished"))

        wrong_revision = self.prefetched_organization()
        wrong_revision._public_image_projection_selections[0]._projection_releases[
            0
        ].selection_revision_snapshot = 2
        cases.append((wrong_revision, "release_scope_inactive"))

        wrong_tenant = self.prefetched_organization()
        other_tenant = Tenant.objects.create(name="Other", slug="other")
        wrong_tenant._public_image_projection_selections[0]._projection_releases[
            0
        ].tenant_id = other_tenant.pk
        cases.append((wrong_tenant, "release_scope_inactive"))

        other_organization = Organization.objects.create(
            tenant=self.tenant,
            name="Other organization",
            org_number="777777777",
            is_published=True,
        )
        wrong_release_organization = self.prefetched_organization()
        wrong_release_organization._public_image_projection_selections[
            0
        ]._projection_releases[0].organization_id = other_organization.pk
        cases.append((wrong_release_organization, "release_scope_inactive"))

        wrong_selection_organization = self.prefetched_organization()
        wrong_selection_organization._public_image_projection_selections[
            0
        ].organization_id = other_organization.pk
        cases.append((wrong_selection_organization, "selection_scope_mismatch"))

        malformed_key = self.prefetched_organization()
        release = malformed_key._public_image_projection_selections[
            0
        ]._projection_releases[0]
        release.renditions.all()[0].public_storage_key = "releases/wrong/square.webp"
        cases.append((malformed_key, "release_mapping_invalid"))

        missing_mapping = self.prefetched_organization()
        release = missing_mapping._public_image_projection_selections[
            0
        ]._projection_releases[0]
        release._prefetched_objects_cache["renditions"] = list(
            release.renditions.all()
        )[:2]
        cases.append((missing_mapping, "release_mapping_invalid"))

        for organization, expected_reason in cases:
            with self.subTest(reason=expected_reason):
                ProjectionBridge.reset()
                result = project_public_image(organization)
                self.assertEqual(result.projection.kind, "system_fallback")
                self.assertEqual(result.reason, expected_reason)
                self.assertEqual(ProjectionBridge.calls, [])

    def test_projection_does_not_materialize_read_files_or_write_database(self):
        before = (
            Organization.objects.count(),
            OrganizationImageSelection.objects.count(),
            OrganizationImageRelease.objects.count(),
        )
        with patch(
            "crm.services.images.materialization.materialize_release",
            side_effect=AssertionError("materialization is forbidden"),
        ), patch(
            "crm.services.images.materialization.verify_materialized_rendition",
            side_effect=AssertionError("storage reads are forbidden"),
        ):
            result = project_public_image(self.prefetched_organization())
        after = (
            Organization.objects.count(),
            OrganizationImageSelection.objects.count(),
            OrganizationImageRelease.objects.count(),
        )

        self.assertEqual(result.projection.kind, "asset")
        self.assertEqual(after, before)

    def test_prefetch_avoids_projection_database_n_plus_one(self):
        Organization.objects.create(
            tenant=self.tenant,
            name="Fallback actor",
            org_number="222222222",
            is_published=True,
        )
        queryset = prefetch_public_image_projection(
            Organization.objects.filter(is_published=True).order_by("pk")
        )
        with CaptureQueriesContext(connection) as queries:
            results = [project_public_image(item) for item in queryset]

        self.assertEqual(len(results), 2)
        self.assertLessEqual(len(queries), 5)
        self.assertEqual(len(ProjectionBridge.calls), 3)

    def test_api_list_prefetches_public_people_and_contacts_without_n_plus_one(self):
        for index in range(6):
            organization = Organization.objects.create(
                tenant=self.tenant,
                name=f"Fallback actor {index}",
                org_number=f"22222222{index}",
                is_published=True,
            )
            person = Person.objects.create(
                tenant=self.tenant,
                full_name=f"Public person {index}",
            )
            OrganizationPerson.objects.create(
                tenant=self.tenant,
                organization=organization,
                person=person,
                status="ACTIVE",
                publish_person=True,
            )
            PersonContact.objects.create(
                tenant=self.tenant,
                person=person,
                type="EMAIL",
                value=f"person-{index}@example.no",
                is_public=True,
            )

        with override_settings(PUBLIC_IMAGE_API_SCHEMA_ENABLED=True):
            with CaptureQueriesContext(connection) as queries:
                response = self.client.get("/api/public/actors/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 7)
        self.assertLessEqual(len(queries), 16)
        fallback_actor = next(
            actor for actor in response.json() if actor["org_number"] == "222222220"
        )
        self.assertEqual(
            fallback_actor["people"][0]["public_contacts"],
            [{"type": "EMAIL", "value": "person-0@example.no"}],
        )

    def test_canonical_route_and_legacy_contract_remain_unchanged_off(self):
        list_match = resolve("/api/public/actors/")
        detail_match = resolve("/api/public/actors/998544092/")
        self.assertIs(list_match.func.cls, PublicActorPublicViewSet)
        self.assertIs(detail_match.func.cls, PublicActorPublicViewSet)
        self.assertEqual(detail_match.kwargs, {"org_number": "998544092"})
        self.assertEqual(
            reverse("public-actors-detail", args=["998544092"]),
            "/api/public/actors/998544092/",
        )

        with override_settings(
            PUBLIC_IMAGE_PROJECTION_ENABLED=False,
            PUBLIC_IMAGE_API_SCHEMA_ENABLED=False,
        ):
            response = self.client.get("/api/public/actors/998544092/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(response.json()),
            {
                "name",
                "org_number",
                "municipality",
                "municipalities",
                "email",
                "phone",
                "website_url",
                "facebook_url",
                "instagram_url",
                "tiktok_url",
                "linkedin_url",
                "youtube_url",
                "primary_link",
                "primary_link_field",
                "thumbnail_image_url",
                "preview_image_url",
                "tags",
                "categories",
                "subcategories",
                "people",
            },
        )
        self.assertNotIn("image", response.json())
        self.assertEqual(
            response.json()["thumbnail_image_url"],
            "https://legacy.example.no/thumbnail.jpg",
        )
        self.assertIsNone(response.json()["phone"])
        self.assertEqual(
            self.client.get("/api/public/actors/000000000/").status_code,
            404,
        )

        public_list = self.client.get("/public/actors/")
        public_detail = self.client.get(
            reverse("public-actor-detail", args=[self.organization.pk])
        )
        self.assertContains(public_list, "https://legacy.example.no/thumbnail.jpg")
        self.assertContains(public_detail, "https://legacy.example.no/thumbnail.jpg")
        self.assertNotContains(public_list, 'rel="canonical"')
        self.assertNotContains(public_detail, 'rel="canonical"')
        self.assertNotContains(public_detail, 'class="public-image-cutover"')
        self.assertNotContains(public_detail, 'class="image-shell"')
        self.assertContains(public_detail, "grid-template-columns: 112px")
        self.assertContains(public_detail, "--tag: #4f332c")

    @override_settings(PUBLIC_IMAGE_API_SCHEMA_ENABLED=True)
    def test_target_api_aliases_equal_projection_for_asset_and_fallback(self):
        asset = self.client.get("/api/public/actors/998544092/")
        self.assertEqual(asset.status_code, 200)
        payload = asset.json()
        self.assertEqual(payload["image"]["kind"], "asset")
        self.assertEqual(
            payload["thumbnail_image_url"],
            payload["preview_image_url"],
        )
        self.assertEqual(
            payload["thumbnail_image_url"], payload["image"]["square"]["url"]
        )

        fallback_org = Organization.objects.create(
            tenant=self.tenant,
            name="Fallback API actor",
            org_number="333333333",
            is_published=True,
        )
        fallback = self.client.get(
            f"/api/public/actors/{fallback_org.org_number}/"
        ).json()
        self.assertEqual(fallback["image"]["kind"], "system_fallback")
        self.assertEqual(
            fallback["thumbnail_image_url"], fallback["preview_image_url"]
        )
        self.assertEqual(
            fallback["thumbnail_image_url"], fallback["image"]["square"]["url"]
        )

    @override_settings(
        PUBLIC_IMAGE_API_SCHEMA_ENABLED=True,
        PUBLIC_IMAGE_PUBLIC_CUTOVER_ENABLED=True,
        ALLOWED_HOSTS=["attacker.example"],
    )
    def test_public_cutover_uses_projection_metadata_credit_and_configured_origin(self):
        self.selection.alt_text = "Scene under nordlyset"
        self.selection.public_credit = "Foto: Testfotograf"
        self.selection.save(update_fields=["alt_text", "public_credit"])
        self.organization.description = '  En <offentlig> & "trygg" beskrivelse.  '
        self.organization.save(update_fields=["description"])

        public_list = self.client.get(
            "/public/actors/?q=Projected",
            HTTP_HOST="attacker.example",
            HTTP_X_FORWARDED_HOST="forwarded.attacker.example",
            HTTP_X_FORWARDED_PROTO="http",
        )
        detail_path = reverse("public-actor-detail", args=[self.organization.pk])
        public_detail = self.client.get(
            detail_path,
            HTTP_HOST="attacker.example",
            HTTP_X_FORWARDED_HOST="forwarded.attacker.example",
            HTTP_X_FORWARDED_PROTO="http",
        )
        api_detail = self.client.get(
            "/api/public/actors/998544092/",
            HTTP_HOST="attacker.example",
            HTTP_X_FORWARDED_HOST="forwarded.attacker.example",
            HTTP_X_FORWARDED_PROTO="http",
        )
        api_list = self.client.get(
            "/api/public/actors/",
            HTTP_HOST="attacker.example",
            HTTP_X_FORWARDED_HOST="forwarded.attacker.example",
            HTTP_X_FORWARDED_PROTO="http",
        )

        self.assertEqual(public_list.status_code, 200)
        self.assertEqual(public_detail.status_code, 200)
        self.assertEqual(api_detail.status_code, 200)
        self.assertEqual(api_list.status_code, 200)
        payload = api_detail.json()
        square_url = payload["image"]["square"]["url"]
        share_url = payload["image"]["share"]["url"]
        self.assertEqual(
            set(payload["image"]),
            {"kind", "alt_text", "credit", "square", "landscape", "share"},
        )
        self.assertEqual(payload["image"]["credit"], "Foto: Testfotograf")
        self.assertEqual(payload["thumbnail_image_url"], square_url)
        self.assertEqual(payload["preview_image_url"], square_url)
        self.assertEqual(api_list.json()[0]["image"], payload["image"])

        self.assertContains(public_list, f'src="{square_url}"')
        self.assertContains(public_detail, f'src="{square_url}"')
        self.assertContains(public_detail, f'content="{share_url}"')
        self.assertContains(public_detail, 'content="1200"')
        self.assertContains(public_detail, 'content="630"')
        self.assertContains(public_detail, 'alt="Scene under nordlyset"')
        self.assertContains(public_detail, "Foto: Testfotograf")
        self.assertContains(
            public_detail,
            "En &lt;offentlig&gt; &amp; &quot;trygg&quot; beskrivelse.",
        )
        self.assertContains(public_detail, "grid-template-columns: 160px")
        self.assertContains(public_detail, "--tag: #4a8755")

        fallback_square = (
            "https://public.example.no/static/crm/public-image-fallback/v1/"
            "fallback-square.png"
        )
        self.assertContains(public_list, f'data-fallback-src="{fallback_square}"')
        self.assertContains(public_detail, f'data-fallback-src="{fallback_square}"')
        self.assertContains(public_detail, "this.onerror=null")
        self.assertContains(public_detail, "this.alt=''")
        self.assertNotContains(public_list, "legacy.example.no")
        self.assertNotContains(public_detail, "legacy.example.no")

        list_html = public_list.content.decode()
        detail_html = public_detail.content.decode()
        self.assertIn(
            '<link rel="canonical" href="https://public.example.no/public/actors/"',
            list_html,
        )
        self.assertIn(
            f'<link rel="canonical" href="https://public.example.no{detail_path}"',
            detail_html,
        )
        self.assertNotIn("attacker.example", list_html)
        self.assertNotIn("attacker.example", detail_html)
        self.assertNotIn("forwarded.attacker.example", detail_html)
        serialized = json.dumps(payload)
        for forbidden in (
            "tenant_id",
            "selection_id",
            "artifact_storage_key",
            "checksum",
            "safety_cursor",
            "private_storage_key",
            "legacy.example.no",
        ):
            self.assertNotIn(forbidden, serialized)

    @override_settings(
        PUBLIC_IMAGE_API_SCHEMA_ENABLED=True,
        PUBLIC_IMAGE_PUBLIC_CUTOVER_ENABLED=True,
    )
    def test_public_cutover_fails_closed_to_blank_alt_fallback_without_legacy(self):
        ProjectionBridge.error = ImageSafetyBridgeUnavailable(
            "safety_unavailable", "synthetic", retryable=True
        )

        public_list = self.client.get("/public/actors/")
        public_detail = self.client.get(
            reverse("public-actor-detail", args=[self.organization.pk])
        )
        api_detail = self.client.get("/api/public/actors/998544092/")

        fallback_square = (
            "https://public.example.no/static/crm/public-image-fallback/v1/"
            "fallback-square.png"
        )
        fallback_share = (
            "https://public.example.no/static/crm/public-image-fallback/v1/"
            "fallback-share.png"
        )
        self.assertEqual(api_detail.json()["image"]["kind"], "system_fallback")
        self.assertEqual(api_detail.json()["image"]["alt_text"], "")
        self.assertContains(public_list, f'src="{fallback_square}" alt=""')
        self.assertContains(public_detail, f'src="{fallback_square}" alt=""')
        self.assertContains(public_detail, f'content="{fallback_share}"')
        self.assertNotContains(public_detail, "og:image:alt")
        self.assertNotContains(public_detail, "twitter:image:alt")
        self.assertNotContains(public_list, "legacy.example.no")
        self.assertNotContains(public_detail, "legacy.example.no")
        self.assertNotContains(public_list, "onerror=")
        self.assertNotContains(public_detail, "onerror=")
        self.assertNotContains(public_detail, self.release_id)
        self.assertNotContains(public_detail, "safety_unavailable")

    @override_settings(
        PUBLIC_IMAGE_API_SCHEMA_ENABLED=True,
        PUBLIC_IMAGE_PUBLIC_CUTOVER_ENABLED=True,
    )
    def test_public_cutover_denied_checksum_retired_and_unknown_never_use_legacy(self):
        for category in ("denied", "checksum_denied", "retired", "unknown"):
            with self.subTest(category=category):
                ProjectionBridge.reset()
                ProjectionBridge.category_by_variant = {"share": category}

                api_detail = self.client.get("/api/public/actors/998544092/")
                public_list = self.client.get("/public/actors/")
                public_detail = self.client.get(
                    reverse("public-actor-detail", args=[self.organization.pk])
                )

                self.assertEqual(
                    api_detail.json()["image"]["kind"], "system_fallback"
                )
                self.assertNotContains(public_list, "legacy.example.no")
                self.assertNotContains(public_detail, "legacy.example.no")
                self.assertContains(public_list, "fallback-square.png")
                self.assertContains(public_detail, "fallback-share.png")

    @override_settings(
        PUBLIC_IMAGE_API_SCHEMA_ENABLED=True,
        PUBLIC_IMAGE_PUBLIC_CUTOVER_ENABLED=True,
    )
    def test_public_cutover_prefetch_keeps_list_query_count_constant(self):
        with CaptureQueriesContext(connection) as one_actor_queries:
            first = self.client.get("/public/actors/")
        self.assertEqual(first.status_code, 200)

        Organization.objects.bulk_create(
            [
                Organization(
                    tenant=self.tenant,
                    name=f"Fallback actor {index}",
                    org_number=f"70000000{index}",
                    is_published=True,
                )
                for index in range(5)
            ]
        )
        ProjectionBridge.reset()
        with CaptureQueriesContext(connection) as six_actor_queries:
            second = self.client.get("/public/actors/")

        self.assertEqual(second.status_code, 200)
        self.assertEqual(len(six_actor_queries), len(one_actor_queries))
        self.assertEqual(len(ProjectionBridge.calls), 3)

    def test_shadow_detail_logs_but_does_not_change_or_expose_response(self):
        with self.assertLogs("crm.public_image_projection", level="INFO") as logs:
            response = self.client.get("/api/public/actors/998544092/")

        payload = response.json()
        self.assertNotIn("image", payload)
        self.assertEqual(
            payload["thumbnail_image_url"],
            "https://legacy.example.no/thumbnail.jpg",
        )
        self.assertNotIn("reason", payload)
        self.assertIn("event=public_image_projection_shadow", logs.output[0])
        self.assertNotIn(self.release_id, logs.output[0])
        self.assertNotIn("https://", logs.output[0])

    def test_shadow_list_avoids_unused_projection_prefetch_and_bridge_calls(self):
        with patch(
            "crm.views_public.prefetch_public_image_projection",
            side_effect=AssertionError("list shadow must use the catalog audit"),
        ):
            response = self.client.get("/api/public/actors/")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("image", response.json()[0])
        self.assertEqual(ProjectionBridge.calls, [])

    def test_catalog_audit_is_json_read_only_and_contains_required_counts(self):
        before = Organization.objects.count()
        output = StringIO()
        call_command("audit_public_image_projection", stdout=output)
        payload = json.loads(output.getvalue())

        self.assertEqual(payload["published_organizations"], 1)
        self.assertEqual(payload["asset"], 1)
        self.assertEqual(payload["system_fallback"], 0)
        self.assertEqual(payload["authorize_count"], 3)
        self.assertGreaterEqual(payload["query_count"], 1)
        self.assertEqual(Organization.objects.count(), before)
        self.assertNotIn(self.release_id, output.getvalue())
        self.assertNotIn("https://", output.getvalue())

    def test_openapi_switches_exact_target_contract_without_duplicate_path(self):
        with override_settings(PUBLIC_IMAGE_API_SCHEMA_ENABLED=False):
            legacy_schema = SchemaGenerator().get_schema(request=None, public=True)
        legacy_component = legacy_schema["components"]["schemas"]["PublicActor"]
        self.assertNotIn("image", legacy_component["properties"])
        self.assertNotIn("PublicImage", legacy_schema["components"]["schemas"])

        with override_settings(PUBLIC_IMAGE_API_SCHEMA_ENABLED=True):
            target_schema = SchemaGenerator().get_schema(request=None, public=True)
        actor = target_schema["components"]["schemas"]["PublicActor"]
        self.assertIn("image", actor["properties"])
        self.assertEqual(
            set(target_schema["components"]["schemas"]["PublicImage"]["properties"]),
            {"kind", "alt_text", "credit", "square", "landscape", "share"},
        )
        public_image = target_schema["components"]["schemas"]["PublicImage"]
        self.assertTrue(public_image["properties"]["credit"]["nullable"])
        self.assertEqual(
            target_schema["components"]["schemas"]["KindEnum"]["enum"],
            ["asset", "system_fallback"],
        )
        variant = target_schema["components"]["schemas"]["PublicImageVariant"]
        self.assertEqual(variant["properties"]["url"]["format"], "uri")
        self.assertEqual(variant["properties"]["width"]["type"], "integer")
        self.assertEqual(variant["properties"]["height"]["type"], "integer")
        self.assertTrue(actor["properties"]["thumbnail_image_url"]["deprecated"])
        self.assertTrue(actor["properties"]["preview_image_url"]["deprecated"])
        detail_path = target_schema["paths"]["/api/public/actors/{org_number}/"]
        self.assertEqual(set(detail_path), {"get"})
        parameter = detail_path["get"]["parameters"][0]
        self.assertEqual(parameter["name"], "org_number")
