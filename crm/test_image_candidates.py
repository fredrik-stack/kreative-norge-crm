from __future__ import annotations

from io import BytesIO
from pathlib import Path
import socket
import tempfile
import time
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.files.storage import storages
from django.test import SimpleTestCase, TestCase, override_settings
from PIL import Image

from crm.models import (
    ImageAsset,
    ImageRendition,
    ImageRenditionSet,
    ImageReviewEvent,
    Organization,
    OrganizationImageRelease,
    OrganizationImageSelection,
    Tenant,
    TenantMembership,
)
from crm.services.images.candidates import (
    CandidatePreview,
    ImageCandidateFeatureDisabledError,
    ImageCandidateFlowError,
    approve_official_image_candidate,
    discover_official_image_candidates,
    get_organization_image_state,
    process_official_image_candidate,
    read_rendition_preview,
    render_candidate_preview,
)
from crm.services.images.fetch import (
    MAX_REDIRECTS,
    SecureFetchResult,
    SecureImageFetchError,
    _default_connection_factory,
    fetch_external_resource,
    normalize_external_url,
)


def image_bytes(image_format: str = "JPEG", size: tuple[int, int] = (1400, 1000)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, (20, 100, 190)).save(buffer, image_format)
    return buffer.getvalue()


def transparent_palette_png_bytes() -> bytes:
    image = Image.new("P", (2, 1))
    image.putpalette([255, 0, 0, 0, 255, 0] + [0, 0, 0] * 254)
    image.putdata([0, 1])
    buffer = BytesIO()
    image.save(buffer, "PNG", transparency=0)
    return buffer.getvalue()


class FakeResponse:
    def __init__(self, status=200, headers=None, body=b""):
        self.status = status
        self.headers = headers or {}
        self.body = body
        self.offset = 0

    def getheader(self, key):
        return self.headers.get(key)

    def read(self, size=-1):
        if size < 0:
            size = len(self.body) - self.offset
        chunk = self.body[self.offset : self.offset + size]
        self.offset += len(chunk)
        return chunk


class FakeConnection:
    def __init__(self, response):
        self.response = response
        self.requests = []
        self.closed = False

    def request(self, method, path, headers=None):
        self.requests.append((method, path, headers or {}))

    def getresponse(self):
        return self.response

    def close(self):
        self.closed = True


class FakeConnectionFactory:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.connections = []

    def __call__(self, scheme, hostname, port, pinned_ip, connect_timeout, read_timeout):
        self.calls.append((scheme, hostname, port, pinned_ip, connect_timeout, read_timeout))
        connection = FakeConnection(self.responses.pop(0))
        self.connections.append(connection)
        return connection


class SecureImageFetchTests(SimpleTestCase):
    public_resolver = staticmethod(lambda hostname, port: ("93.184.216.34",))

    def fetch(self, response, **overrides):
        factory = FakeConnectionFactory([response])
        result = fetch_external_resource(
            "https://example.com/image.jpg",
            expected="image",
            resolver=overrides.pop("resolver", self.public_resolver),
            connection_factory=factory,
            **overrides,
        )
        return result, factory

    def test_normalizes_url_and_rejects_userinfo_sensitive_queries_and_local_hosts(self):
        self.assertEqual(normalize_external_url("HTTPS://Example.COM:443/a#fragment"), "https://example.com/a")
        for url in (
            "https://user:secret@example.com/a.jpg",
            "https://example.com/a.jpg?token=secret",
            "https://example.com/a.jpg?X-Amz-Signature=secret",
            "http://localhost/a.jpg",
            "http://service.local/a.jpg",
            "http://metadata.google.internal/a.jpg",
        ):
            with self.subTest(url=url), self.assertRaises(SecureImageFetchError):
                normalize_external_url(url)

    def test_rejects_private_ipv4_ipv6_and_mixed_dns_answers(self):
        for answers in (
            ("127.0.0.1",),
            ("10.0.0.1",),
            ("::1",),
            ("fc00::1",),
            ("93.184.216.34", "10.0.0.1"),
        ):
            with self.subTest(answers=answers), self.assertRaises(SecureImageFetchError):
                fetch_external_resource(
                    "https://example.com/image.jpg",
                    expected="image",
                    resolver=lambda hostname, port, answers=answers: answers,
                    connection_factory=FakeConnectionFactory([]),
                )

    def test_connection_is_pinned_to_validated_address_and_sends_no_credentials(self):
        body = image_bytes()
        result, factory = self.fetch(
            FakeResponse(200, {"Content-Type": "image/jpeg", "Content-Length": str(len(body))}, body)
        )
        self.assertEqual(result.body, body)
        self.assertEqual(factory.calls[0][3], "93.184.216.34")
        headers = factory.connections[0].requests[0][2]
        self.assertEqual(headers["Accept-Encoding"], "identity")
        self.assertNotIn("Authorization", headers)
        self.assertNotIn("Cookie", headers)

    def test_default_connection_connects_to_pinned_ip_not_hostname(self):
        fake_socket = Mock()
        with patch("socket.create_connection", return_value=fake_socket) as create_connection:
            connection = _default_connection_factory(
                "http", "example.com", 80, "93.184.216.34", 2.0, 3.0
            )
            connection.connect()
        create_connection.assert_called_once_with(
            ("93.184.216.34", 80), timeout=2.0, source_address=None
        )
        fake_socket.settimeout.assert_called_with(3.0)

    def test_connected_peer_mismatch_fails_closed(self):
        body = image_bytes()
        connection = FakeConnection(
            FakeResponse(200, {"Content-Type": "image/jpeg"}, body)
        )
        connection.sock = Mock()
        connection.sock.getpeername.return_value = ("93.184.216.35", 443)
        with self.assertRaises(SecureImageFetchError) as context:
            fetch_external_resource(
                "https://example.com/image.jpg",
                expected="image",
                resolver=self.public_resolver,
                connection_factory=lambda *args: connection,
            )
        self.assertEqual(context.exception.code, "peer_mismatch")

    def test_redirect_revalidates_target_and_rejects_private_and_https_downgrade(self):
        redirect = FakeResponse(302, {"Location": "https://private.example/image.jpg"})
        with self.assertRaises(SecureImageFetchError) as context:
            fetch_external_resource(
                "https://example.com/start",
                expected="image",
                resolver=lambda hostname, port: ("10.0.0.8",) if hostname == "private.example" else ("93.184.216.34",),
                connection_factory=FakeConnectionFactory([redirect]),
            )
        self.assertEqual(context.exception.code, "private_address")

        with self.assertRaises(SecureImageFetchError) as context:
            fetch_external_resource(
                "https://example.com/start",
                expected="image",
                resolver=self.public_resolver,
                connection_factory=FakeConnectionFactory(
                    [FakeResponse(302, {"Location": "http://example.com/image.jpg"})]
                ),
            )
        self.assertEqual(context.exception.code, "https_downgrade")

    def test_redirect_limit_is_three(self):
        responses = [FakeResponse(302, {"Location": f"/next-{index}"}) for index in range(MAX_REDIRECTS + 1)]
        with self.assertRaises(SecureImageFetchError) as context:
            fetch_external_resource(
                "https://example.com/start",
                expected="image",
                resolver=self.public_resolver,
                connection_factory=FakeConnectionFactory(responses),
            )
        self.assertEqual(context.exception.code, "too_many_redirects")

    def test_rejects_length_stream_overflow_content_type_and_html_disguised_as_image(self):
        cases = (
            (FakeResponse(200, {"Content-Type": "image/jpeg", "Content-Length": "11"}, b""), 10, "response_too_large"),
            (FakeResponse(200, {"Content-Type": "image/jpeg"}, b"\xff\xd8\xff" + b"x" * 20), 10, "response_too_large"),
            (FakeResponse(200, {"Content-Type": "text/html"}, b"<html></html>"), 100, "content_type"),
            (FakeResponse(200, {"Content-Type": "image/jpeg"}, b"<html></html>"), 100, "image_mismatch"),
        )
        for response, max_bytes, code in cases:
            with self.subTest(code=code), self.assertRaises(SecureImageFetchError) as context:
                self.fetch(response, max_bytes=max_bytes)
            self.assertEqual(context.exception.code, code)

    def test_accepts_case_insensitive_html_prefix_as_bytes(self):
        body = b"\xef\xbb\xbf  <!DOCTYPE HTML><HTML><HEAD></HEAD></HTML>"
        factory = FakeConnectionFactory(
            [FakeResponse(200, {"Content-Type": "text/html"}, body)]
        )

        result = fetch_external_resource(
            "https://example.com/",
            expected="html",
            resolver=self.public_resolver,
            connection_factory=factory,
        )

        self.assertEqual(result.body, body)

    def test_timeout_and_remote_http_error_are_controlled(self):
        timeout_response = FakeResponse(200, {"Content-Type": "image/jpeg"}, image_bytes())
        timeout_response.read = Mock(side_effect=socket.timeout())
        for response, expected_code in (
            (timeout_response, "timeout"),
            (FakeResponse(503, {"Content-Type": "text/html"}, b"<html></html>"), "http_error"),
        ):
            with self.subTest(expected_code=expected_code), self.assertRaises(SecureImageFetchError) as context:
                self.fetch(response)
            self.assertEqual(context.exception.code, expected_code)


@override_settings(IMAGE_ASSET_FEATURE_ENABLED=True)
class OfficialImageCandidateFlowTests(TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        root = Path(self.temporary_directory.name)
        self.storage_override = override_settings(
            STORAGES={
                "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
                "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
                "image_originals_private": {
                    "BACKEND": "django.core.files.storage.FileSystemStorage",
                    "OPTIONS": {"location": root / "private", "base_url": None},
                },
                "image_renditions_public": {
                    "BACKEND": "django.core.files.storage.FileSystemStorage",
                    "OPTIONS": {"location": root / "artifacts", "base_url": None},
                },
            }
        )
        self.storage_override.enable()
        self.tenant = Tenant.objects.create(name="Candidate tenant", slug="candidate-tenant")
        self.other_tenant = Tenant.objects.create(name="Other", slug="candidate-other")
        self.organization = Organization.objects.create(
            tenant=self.tenant,
            name="Official actor",
            website_url="https://official.example/",
            og_image_url="https://cdn.example/stored.jpg",
            auto_thumbnail_url="https://cdn.example/auto.jpg",
            is_published=True,
            publish_phone=True,
        )
        self.other_organization = Organization.objects.create(
            tenant=self.other_tenant,
            name="Other actor",
            website_url="https://other.example/",
        )
        self.actor = get_user_model().objects.create_user(username="candidate-editor", password="pw")
        TenantMembership.objects.create(
            tenant=self.tenant,
            user=self.actor,
            role=TenantMembership.Role.REDIGERER,
        )
        TenantMembership.objects.create(
            tenant=self.other_tenant,
            user=self.actor,
            role=TenantMembership.Role.REDIGERER,
        )
        self.image = image_bytes()
        self.html = b"""
            <html><head>
              <meta property='og:image' content='https://cdn.example/og.jpg'>
              <meta name='twitter:image' content='/twitter.jpg'>
            </head><body>
              <img src='/hero.jpg' width='1200' height='800'>
              <img src='/hero.jpg' width='1200' height='800'>
              <img src='/one.jpg'><img src='/two.jpg'><img src='/three.jpg'><img src='/four.jpg'>
            </body></html>
        """

    def tearDown(self):
        self.storage_override.disable()
        self.temporary_directory.cleanup()

    def fake_fetch(self, url, *, expected, max_bytes=15 * 1024 * 1024, **kwargs):
        if expected == "html":
            return SecureFetchResult(url, "https://official.example/", "text/html", self.html, 0)
        return SecureFetchResult(url, url, "image/jpeg", self.image, 0)

    def discover(self):
        with patch("crm.services.images.candidates.fetch_external_resource", side_effect=self.fake_fetch):
            return discover_official_image_candidates(
                actor=self.actor,
                tenant_id=self.tenant.pk,
                organization_id=self.organization.pk,
            )

    def process(self, candidate_ref, **kwargs):
        with patch("crm.services.images.candidates.fetch_external_resource", side_effect=self.fake_fetch):
            return process_official_image_candidate(
                actor=self.actor,
                tenant_id=self.tenant.pk,
                organization_id=self.organization.pk,
                candidate_ref=candidate_ref,
                image_kind="photo",
                **kwargs,
            )

    def test_discovery_includes_stored_and_page_candidates_ordered_deduplicated_and_capped(self):
        candidates = self.discover()
        self.assertEqual(len(candidates), 6)
        self.assertEqual(candidates[0].source_type, ImageReviewEvent.SourceType.OPEN_GRAPH)
        self.assertEqual(candidates[0].source_domain, "official.example")
        self.assertEqual(len({item.candidate_ref for item in candidates}), 6)

    def test_candidate_preview_is_bounded_ephemeral_and_private_data_is_not_persisted(self):
        candidate = self.discover()[0]
        before = (ImageAsset.objects.count(), ImageRenditionSet.objects.count(), ImageRendition.objects.count())
        with patch("crm.services.images.candidates.fetch_external_resource", side_effect=self.fake_fetch):
            preview = render_candidate_preview(
                actor=self.actor,
                tenant_id=self.tenant.pk,
                organization_id=self.organization.pk,
                candidate_ref=candidate.candidate_ref,
            )
        self.assertEqual(preview.content_type, "image/webp")
        self.assertLessEqual(max(preview.width, preview.height), 640)
        self.assertLessEqual(len(preview.body), 1_000_000)
        self.assertEqual(before, (ImageAsset.objects.count(), ImageRenditionSet.objects.count(), ImageRendition.objects.count()))
        self.assertFalse(any((Path(self.temporary_directory.name) / "private").rglob("*")))

    def test_candidate_preview_preserves_palette_trns_transparency(self):
        candidate = self.discover()[0]
        palette_png = transparent_palette_png_bytes()

        def fetch_palette(url, *, expected, **kwargs):
            return SecureFetchResult(url, url, "image/png", palette_png, 0)

        with patch("crm.services.images.candidates.fetch_external_resource", side_effect=fetch_palette):
            preview = render_candidate_preview(
                actor=self.actor,
                tenant_id=self.tenant.pk,
                organization_id=self.organization.pk,
                candidate_ref=candidate.candidate_ref,
            )

        with Image.open(BytesIO(preview.body)) as decoded:
            decoded.load()
            self.assertEqual(decoded.convert("RGBA").getpixel((0, 0))[3], 0)
            self.assertEqual(decoded.convert("RGBA").getpixel((1, 0))[3], 255)

    def test_processes_only_selected_candidate_with_center_photo_and_complete_idempotent_aggregate(self):
        candidates = self.discover()
        selected = candidates[1]
        first = self.process(selected.candidate_ref)
        second = self.process(selected.candidate_ref)
        self.assertEqual(first.rendition_set_id, second.rendition_set_id)
        self.assertEqual(set(first.variants), {"square", "landscape", "share"})
        rendition_set = ImageRenditionSet.objects.get(pk=first.rendition_set_id)
        self.assertEqual(rendition_set.fit_mode, "cover")
        self.assertEqual((float(rendition_set.focus_x), float(rendition_set.focus_y)), (0.5, 0.5))
        self.assertEqual(OrganizationImageSelection.objects.count(), 0)
        self.assertEqual(ImageReviewEvent.objects.count(), 0)
        self.assertEqual(OrganizationImageRelease.objects.count(), 0)
        self.assertEqual(ImageAsset.objects.count(), 1)

    def test_logo_maps_to_contain_without_focus(self):
        candidate = self.discover()[0]
        with patch("crm.services.images.candidates.fetch_external_resource", side_effect=self.fake_fetch):
            result = process_official_image_candidate(
                actor=self.actor,
                tenant_id=self.tenant.pk,
                organization_id=self.organization.pk,
                candidate_ref=candidate.candidate_ref,
                image_kind="logo",
            )
        self.assertEqual(ImageRenditionSet.objects.get(pk=result.rendition_set_id).fit_mode, "contain")

    def test_tampered_wrong_user_and_cross_tenant_candidate_refs_are_rejected(self):
        candidate_ref = self.discover()[0].candidate_ref
        other_user = get_user_model().objects.create_user(username="other-editor", password="pw")
        TenantMembership.objects.create(
            tenant=self.tenant,
            user=other_user,
            role=TenantMembership.Role.REDIGERER,
        )
        cases = (
            (self.actor, self.tenant.pk, candidate_ref + "x"),
            (other_user, self.tenant.pk, candidate_ref),
            (self.actor, self.other_tenant.pk, candidate_ref),
        )
        for actor, tenant_id, ref in cases:
            with self.subTest(actor=actor.username, tenant_id=tenant_id), self.assertRaises(ImageCandidateFlowError):
                render_candidate_preview(
                    actor=actor,
                    tenant_id=tenant_id,
                    organization_id=(
                        self.other_organization.pk
                        if tenant_id == self.other_tenant.pk
                        else self.organization.pk
                    ),
                    candidate_ref=ref,
                )

    def test_expired_candidate_ref_is_rejected_before_network(self):
        candidate_ref = self.discover()[0].candidate_ref
        with patch("django.core.signing.time.time", return_value=time.time() + 1900):
            with patch("crm.services.images.candidates.fetch_external_resource") as fetch:
                with self.assertRaises(ImageCandidateFlowError) as context:
                    render_candidate_preview(
                        actor=self.actor,
                        tenant_id=self.tenant.pk,
                        organization_id=self.organization.pk,
                        candidate_ref=candidate_ref,
                    )
        self.assertEqual(context.exception.code, "expired_ref")
        fetch.assert_not_called()

    def test_cross_tenant_discovery_and_state_are_rejected_before_fetch(self):
        with patch("crm.services.images.candidates.fetch_external_resource") as fetch:
            with self.assertRaises(ImageCandidateFlowError):
                discover_official_image_candidates(
                    actor=self.actor,
                    tenant_id=self.other_tenant.pk,
                    organization_id=self.organization.pk,
                )
            with self.assertRaises(ImageCandidateFlowError):
                get_organization_image_state(
                    actor=self.actor,
                    tenant_id=self.other_tenant.pk,
                    organization_id=self.organization.pk,
                )
        fetch.assert_not_called()

    def test_approval_creates_first_then_replacement_and_preserves_publication_flags(self):
        first = self.process(self.discover()[0].candidate_ref)
        first_result = approve_official_image_candidate(
            actor=self.actor,
            tenant_id=self.tenant.pk,
            organization_id=self.organization.pk,
            approval_ref=first.approval_ref,
            expected_revision=0,
            alt_text="Offisielt foto av aktøren",
            public_credit="Fotograf",
        )
        self.assertEqual(first_result.event.event_type, ImageReviewEvent.EventType.SELECTION_LOCKED)
        self.assertEqual(first_result.event.source_type_snapshot, ImageReviewEvent.SourceType.OPEN_GRAPH)
        self.assertEqual(first_result.event.asset_checksum_sha256_snapshot, first_result.selection.rendition_set.asset.checksum_sha256)
        self.assertTrue(first_result.event.approval_text_snapshot)

        second = self.process(self.discover()[1].candidate_ref, focus_x=0.4, focus_y=0.6)
        second_result = approve_official_image_candidate(
            actor=self.actor,
            tenant_id=self.tenant.pk,
            organization_id=self.organization.pk,
            approval_ref=second.approval_ref,
            expected_revision=1,
            alt_text="Nytt offisielt aktørfoto",
        )
        self.assertEqual(second_result.selection.revision, 2)
        self.assertEqual(second_result.event.event_type, ImageReviewEvent.EventType.SELECTION_REPLACED)
        self.assertEqual(OrganizationImageSelection.objects.filter(status="active").count(), 1)
        self.organization.refresh_from_db()
        self.assertTrue(self.organization.is_published)
        self.assertTrue(self.organization.publish_phone)
        self.assertEqual(OrganizationImageRelease.objects.count(), 0)

    def test_approval_ref_rejects_tampering_wrong_user_and_revision_conflict(self):
        processed = self.process(self.discover()[0].candidate_ref)
        with self.assertRaises(ImageCandidateFlowError):
            approve_official_image_candidate(
                actor=self.actor,
                tenant_id=self.tenant.pk,
                organization_id=self.organization.pk,
                approval_ref=processed.approval_ref + "x",
                expected_revision=0,
                alt_text="Valid alt text",
            )
        other_user = get_user_model().objects.create_user(username="approval-other", password="pw")
        TenantMembership.objects.create(
            tenant=self.tenant,
            user=other_user,
            role=TenantMembership.Role.REDIGERER,
        )
        with self.assertRaises(ImageCandidateFlowError) as context:
            approve_official_image_candidate(
                actor=other_user,
                tenant_id=self.tenant.pk,
                organization_id=self.organization.pk,
                approval_ref=processed.approval_ref,
                expected_revision=0,
                alt_text="Valid alt text",
            )
        self.assertEqual(context.exception.code, "wrong_scope")
        with self.assertRaises(ImageCandidateFlowError) as context:
            approve_official_image_candidate(
                actor=self.actor,
                tenant_id=self.other_tenant.pk,
                organization_id=self.other_organization.pk,
                approval_ref=processed.approval_ref,
                expected_revision=0,
                alt_text="Cross-tenant attempt",
            )
        self.assertEqual(context.exception.code, "wrong_scope")
        approve_official_image_candidate(
            actor=self.actor,
            tenant_id=self.tenant.pk,
            organization_id=self.organization.pk,
            approval_ref=processed.approval_ref,
            expected_revision=0,
            alt_text="Valid alt text",
        )
        with self.assertRaises(Exception) as context:
            approve_official_image_candidate(
                actor=self.actor,
                tenant_id=self.tenant.pk,
                organization_id=self.organization.pk,
                approval_ref=processed.approval_ref,
                expected_revision=0,
                alt_text="Stale revision",
            )
        self.assertEqual(context.exception.__class__.__name__, "ExpectedRevisionConflictError")

    def test_expired_approval_ref_cannot_create_selection_or_event(self):
        processed = self.process(self.discover()[0].candidate_ref)
        with patch("django.core.signing.time.time", return_value=time.time() + 1900):
            with self.assertRaises(ImageCandidateFlowError) as context:
                approve_official_image_candidate(
                    actor=self.actor,
                    tenant_id=self.tenant.pk,
                    organization_id=self.organization.pk,
                    approval_ref=processed.approval_ref,
                    expected_revision=0,
                    alt_text="Expired approval",
                )
        self.assertEqual(context.exception.code, "expired_ref")
        self.assertEqual(OrganizationImageSelection.objects.count(), 0)
        self.assertEqual(ImageReviewEvent.objects.count(), 0)

    def test_state_and_rendition_preview_are_tenant_scoped_and_checksum_verified(self):
        processed = self.process(self.discover()[0].candidate_ref)
        approve_official_image_candidate(
            actor=self.actor,
            tenant_id=self.tenant.pk,
            organization_id=self.organization.pk,
            approval_ref=processed.approval_ref,
            expected_revision=0,
            alt_text="Active image",
        )
        state = get_organization_image_state(
            actor=self.actor,
            tenant_id=self.tenant.pk,
            organization_id=self.organization.pk,
        )
        self.assertEqual(state["expected_revision"], 1)
        preview_ref = state["active_selection"]["rendition_preview_ref"]
        body, content_type = read_rendition_preview(
            actor=self.actor,
            tenant_id=self.tenant.pk,
            organization_id=self.organization.pk,
            preview_ref=preview_ref,
            variant="square",
        )
        self.assertTrue(body)
        self.assertEqual(content_type, "image/webp")
        with self.assertRaises(ImageCandidateFlowError):
            read_rendition_preview(
                actor=self.actor,
                tenant_id=self.other_tenant.pk,
                organization_id=self.other_organization.pk,
                preview_ref=preview_ref,
                variant="square",
            )

        rendition = ImageRendition.objects.get(
            tenant=self.tenant,
            rendition_set_id=processed.rendition_set_id,
            variant="square",
        )
        artifact_path = Path(storages["image_renditions_public"].path(rendition.artifact_storage_key))
        original_bytes = artifact_path.read_bytes()
        artifact_path.write_bytes(bytes([original_bytes[0] ^ 0xFF]) + original_bytes[1:])
        with self.assertRaises(ImageCandidateFlowError) as context:
            read_rendition_preview(
                actor=self.actor,
                tenant_id=self.tenant.pk,
                organization_id=self.organization.pk,
                preview_ref=preview_ref,
                variant="square",
            )
        self.assertEqual(context.exception.code, "preview_conflict")

    @override_settings(IMAGE_ASSET_FEATURE_ENABLED=False)
    def test_feature_off_fails_before_network_storage_or_database_side_effects(self):
        operations = (
            lambda: discover_official_image_candidates(
                actor=self.actor,
                tenant_id=self.tenant.pk,
                organization_id=self.organization.pk,
            ),
            lambda: render_candidate_preview(
                actor=self.actor,
                tenant_id=self.tenant.pk,
                organization_id=self.organization.pk,
                candidate_ref="unused",
            ),
            lambda: process_official_image_candidate(
                actor=self.actor,
                tenant_id=self.tenant.pk,
                organization_id=self.organization.pk,
                candidate_ref="unused",
                image_kind="photo",
            ),
            lambda: read_rendition_preview(
                actor=self.actor,
                tenant_id=self.tenant.pk,
                organization_id=self.organization.pk,
                preview_ref="unused",
                variant="square",
            ),
            lambda: approve_official_image_candidate(
                actor=self.actor,
                tenant_id=self.tenant.pk,
                organization_id=self.organization.pk,
                approval_ref="unused",
                expected_revision=0,
                alt_text="Unused",
            ),
            lambda: get_organization_image_state(
                actor=self.actor,
                tenant_id=self.tenant.pk,
                organization_id=self.organization.pk,
            ),
        )
        storage = Mock()
        with (
            patch("crm.services.images.candidates.fetch_external_resource") as fetch,
            patch("crm.services.images.candidates.ingest_uploaded_image") as ingest,
            patch("crm.services.images.candidates.lock_organization_image_selection") as lock_selection,
            patch("crm.services.images.candidates.storages", {"image_renditions_public": storage}),
        ):
            for operation in operations:
                with self.subTest(operation=operation), self.assertRaises(ImageCandidateFeatureDisabledError):
                    operation()
        fetch.assert_not_called()
        ingest.assert_not_called()
        lock_selection.assert_not_called()
        storage.open.assert_not_called()
        self.assertEqual(ImageAsset.objects.count(), 0)
        self.assertEqual(ImageRenditionSet.objects.count(), 0)
        self.assertEqual(ImageRendition.objects.count(), 0)
        self.assertEqual(OrganizationImageSelection.objects.count(), 0)
        self.assertEqual(ImageReviewEvent.objects.count(), 0)


@override_settings(IMAGE_ASSET_FEATURE_ENABLED=True)
class OrganizationImageApiPermissionTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="API tenant", slug="api-image-tenant")
        self.organization = Organization.objects.create(
            tenant=self.tenant,
            name="API organization",
            website_url="https://official.example/",
        )
        self.reader = get_user_model().objects.create_user(username="image-reader", password="pw")
        self.editor = get_user_model().objects.create_user(username="image-api-editor", password="pw")
        TenantMembership.objects.create(
            tenant=self.tenant,
            user=self.reader,
            role=TenantMembership.Role.LESER,
        )
        TenantMembership.objects.create(
            tenant=self.tenant,
            user=self.editor,
            role=TenantMembership.Role.REDIGERER,
        )

    def test_reader_cannot_start_discovery_or_approval_but_can_read_state(self):
        self.client.force_login(self.reader)
        base = f"/api/tenants/{self.tenant.pk}/organizations/{self.organization.pk}/images"
        self.assertEqual(self.client.post(f"{base}/discover/", data={}, content_type="application/json").status_code, 403)
        self.assertEqual(self.client.post(f"{base}/approve/", data={}, content_type="application/json").status_code, 403)
        self.assertEqual(self.client.get(f"{base}/state/").status_code, 200)

    @override_settings(IMAGE_ASSET_FEATURE_ENABLED=False)
    def test_disabled_api_is_hidden(self):
        self.client.force_login(self.reader)
        base = f"/api/tenants/{self.tenant.pk}/organizations/{self.organization.pk}/images"
        self.assertEqual(self.client.get(f"{base}/state/").status_code, 404)

    def test_candidate_preview_is_private_no_store_and_never_exposes_original_path(self):
        self.client.force_login(self.editor)
        base = f"/api/tenants/{self.tenant.pk}/organizations/{self.organization.pk}/images"
        with patch(
            "crm.views.render_candidate_preview",
            return_value=CandidatePreview(b"preview", "image/webp", 120, 80),
        ):
            response = self.client.post(
                f"{base}/candidate-preview/",
                data={"candidate_ref": "signed-ref"},
                content_type="application/json",
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "private, no-store, max-age=0")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertNotContains(response, "tenants/")

    def test_organization_payload_exposes_fail_closed_feature_state(self):
        self.client.force_login(self.editor)
        response = self.client.get(
            f"/api/tenants/{self.tenant.pk}/organizations/{self.organization.pk}/"
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["image_asset_feature_enabled"])
