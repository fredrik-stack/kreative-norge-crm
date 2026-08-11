from __future__ import annotations

import json
import socket
from urllib.parse import parse_qs, urlsplit
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core import signing
from django.test import SimpleTestCase, TestCase, override_settings

from crm.models import (
    Category,
    Organization,
    OrganizationPerson,
    Person,
    Tag,
    Tenant,
    TenantMembership,
)
from crm.services.images.brave import (
    BraveImageResult,
    BraveImageSearchError,
    build_search_context,
    prepare_search_query,
    rank_brave_results,
    search_brave_images,
)
from crm.services.images.candidates import (
    CANDIDATE_REF_SALT,
    discover_brave_image_candidates,
)


def brave_result(
    *,
    image_url: str = "https://images.example/actor.jpg",
    source_page_url: str | None = "https://publisher.example/story",
    source_domain: str | None = "publisher.example",
    title: str | None = "Actor image",
    publisher: str | None = "Publisher",
    provider_index: int = 0,
) -> BraveImageResult:
    return BraveImageResult(
        image_url=image_url,
        thumbnail_url="https://thumbs.example/actor.jpg",
        source_page_url=source_page_url,
        source_domain=source_domain,
        title=title,
        publisher=publisher,
        width=1600,
        height=900,
        provider_index=provider_index,
    )


class BraveProviderAdapterTests(SimpleTestCase):
    @override_settings(BRAVE_IMAGE_SEARCH_API_KEY="server-secret")
    def test_sends_exact_query_and_fixed_norwegian_safe_parameters(self):
        calls = []

        def transport(path, headers, timeout):
            calls.append((path, headers, timeout))
            body = json.dumps(
                {
                    "results": [
                        {
                            "title": None,
                            "url": "https://publisher.example/page",
                            "source": None,
                            "meta_url": {"hostname": "Official.Example"},
                            "thumbnail": {"src": None},
                            "properties": {
                                "url": "https://images.example/bl%C3%A5frost.jpg",
                                "width": None,
                                "height": None,
                            },
                        }
                    ]
                }
            ).encode()
            return 200, "application/json", body

        query = "Blåfrost Guovdageaidnu"
        results = search_brave_images(query, transport=transport)

        params = parse_qs(urlsplit(calls[0][0]).query)
        self.assertEqual(params["q"], [query])
        self.assertEqual(params["country"], ["NO"])
        self.assertEqual(params["search_lang"], ["nb"])
        self.assertEqual(params["safesearch"], ["strict"])
        self.assertEqual(params["spellcheck"], ["false"])
        self.assertEqual(params["count"], ["30"])
        self.assertEqual(calls[0][1]["X-Subscription-Token"], "server-secret")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].source_domain, "official.example")
        self.assertIsNone(results[0].title)
        self.assertIsNone(results[0].publisher)
        self.assertIsNone(results[0].width)
        self.assertIsNone(results[0].height)

    @override_settings(BRAVE_IMAGE_SEARCH_API_KEY="")
    def test_missing_key_is_controlled_before_transport(self):
        transport = Mock()
        with self.assertRaises(BraveImageSearchError) as context:
            search_brave_images("Tvibit", transport=transport)
        self.assertEqual(context.exception.code, "brave_not_configured")
        self.assertNotIn("key", str(context.exception).casefold())
        transport.assert_not_called()

    @override_settings(BRAVE_IMAGE_SEARCH_API_KEY="never-leak-this")
    def test_timeout_rate_limit_and_malformed_response_are_controlled_without_secret(self):
        cases = (
            (Mock(side_effect=socket.timeout()), "provider_timeout"),
            (Mock(return_value=(429, "application/json", b"{}")), "provider_rate_limited"),
            (Mock(return_value=(200, "text/html", b"<html></html>")), "provider_malformed"),
            (Mock(return_value=(200, "application/json", b"not-json")), "provider_malformed"),
            (Mock(return_value=(200, "application/json", b"{}")), "provider_malformed"),
        )
        for transport, expected_code in cases:
            with self.subTest(expected_code=expected_code):
                with self.assertRaises(BraveImageSearchError) as context:
                    search_brave_images("Parkenfestivalen", transport=transport)
                self.assertEqual(context.exception.code, expected_code)
                self.assertNotIn("never-leak-this", str(context.exception))

    @override_settings(BRAVE_IMAGE_SEARCH_API_KEY="server-secret")
    def test_deduplicates_original_urls_and_discards_unusable_results(self):
        body = json.dumps(
            {
                "results": [
                    {"properties": {"url": "https://images.example/a.jpg"}},
                    {"properties": {"url": "https://images.example/a.jpg#fragment"}},
                    {"properties": {"url": "https://images.example/b.jpg?token=secret"}},
                    {"properties": {"url": None}},
                ]
            }
        ).encode()
        results = search_brave_images(
            "Actor",
            transport=lambda path, headers, timeout: (200, "application/json", body),
        )
        self.assertEqual([item.image_url for item in results], ["https://images.example/a.jpg"])

    @override_settings(BRAVE_IMAGE_SEARCH_API_KEY="server-secret")
    def test_query_limits_are_fail_closed(self):
        for query in ("x" * 401, " ".join(["word"] * 51), "valid\nquery"):
            with self.subTest(query=query), self.assertRaises(BraveImageSearchError) as context:
                search_brave_images(query, transport=Mock())
            self.assertEqual(context.exception.code, "invalid_query")


@override_settings(IMAGE_ASSET_FEATURE_ENABLED=True)
class BraveQueryAndCandidateTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Search tenant", slug="search-tenant")
        self.organization = Organization.objects.create(
            tenant=self.tenant,
            name="Bodø Bluesklubb",
            municipalities="Bodø",
            website_url="https://official.example/",
        )
        self.category, _ = Category.objects.get_or_create(
            name="Musikk",
            defaults={"slug": "musikk-search"},
        )
        self.organization.categories.add(self.category)
        self.tag = Tag.objects.create(tenant=self.tenant, name="Ikke bruk", slug="ikke-bruk")
        self.organization.tags.add(self.tag)
        self.person = Person.objects.create(tenant=self.tenant, full_name="Kari Nordmann")
        OrganizationPerson.objects.create(
            tenant=self.tenant,
            organization=self.organization,
            person=self.person,
            status="ACTIVE",
        )
        self.actor = get_user_model().objects.create_user(username="search-editor", password="pw")
        TenantMembership.objects.create(
            tenant=self.tenant,
            user=self.actor,
            role=TenantMembership.Role.REDIGERER,
        )

    def test_default_query_uses_only_name_and_exactly_one_municipality(self):
        context = build_search_context(self.organization)
        self.assertEqual(context.suggested_query, "Bodø Bluesklubb Bodø")
        self.assertEqual(context.query_sources, ("organization_name", "municipality"))
        self.assertNotIn(self.tag.name, context.suggested_query)

        self.organization.municipalities = ""
        self.organization.save(update_fields=["municipalities"])
        context = build_search_context(self.organization)
        self.assertEqual(context.suggested_query, "Bodø Bluesklubb")
        self.assertEqual(context.query_sources, ("organization_name",))

        self.organization.municipalities = "Bodø, Fauske"
        self.organization.save(update_fields=["municipalities"])
        context = build_search_context(self.organization)
        self.assertEqual(context.suggested_query, "Bodø Bluesklubb")
        self.assertEqual(context.municipalities, ("Bodø", "Fauske"))

    def test_explicit_refinements_must_be_actual_crm_values(self):
        prepared = prepare_search_query(
            self.organization,
            query="Bodø Bluesklubb Bodø Musikk Kari Nordmann",
            municipality="bodø",
            category_id=self.category.pk,
            person_id=self.person.pk,
        )
        self.assertEqual(
            prepared.query_sources,
            ("organization_name", "municipality", "category", "person"),
        )

        for overrides in (
            {"municipality": "Oslo"},
            {"category_id": self.category.pk + 999},
            {"person_id": self.person.pk + 999},
        ):
            values = {
                "query": "Bodø Bluesklubb Bodø",
                "municipality": None,
                "category_id": None,
                "person_id": None,
                **overrides,
            }
            with self.subTest(overrides=overrides), self.assertRaises(BraveImageSearchError):
                prepare_search_query(self.organization, **values)

    def test_manual_query_is_sent_exactly_without_automatic_context(self):
        query = "  Blåfrost original skrivemåte  "
        prepared = prepare_search_query(
            self.organization,
            query=query,
            query_edited=True,
        )
        self.assertEqual(prepared.query, query)
        self.assertEqual(prepared.query_sources, ("manual_edit",))

    def test_manual_query_rejects_structured_refinements_that_could_rank_hidden_context(self):
        for refinement in (
            {"municipality": "Bodø"},
            {"category_id": self.category.pk},
            {"person_id": self.person.pk},
        ):
            with self.subTest(refinement=refinement), self.assertRaises(
                BraveImageSearchError
            ) as context:
                prepare_search_query(
                    self.organization,
                    query="Eksakt manuelt søk",
                    query_edited=True,
                    **refinement,
                )
            self.assertEqual(context.exception.code, "invalid_refinement")

    def test_unedited_query_cannot_hide_a_mismatch(self):
        with self.assertRaises(BraveImageSearchError) as context:
            prepare_search_query(
                self.organization,
                query="Bodø Bluesklubb skjult ord",
                query_edited=False,
            )
        self.assertEqual(context.exception.code, "query_mismatch")

    def test_official_domain_is_strongest_local_rank_signal(self):
        prepared = prepare_search_query(
            self.organization,
            query="Bodø Bluesklubb Bodø",
        )
        results = (
            brave_result(
                image_url="https://images.example/name.jpg",
                source_domain="other.example",
                title="Bodø Bluesklubb Bodø",
                provider_index=0,
            ),
            brave_result(
                image_url="https://images.example/official.jpg",
                source_page_url="https://official.example/gallery",
                source_domain="official.example",
                title=None,
                publisher=None,
                provider_index=1,
            ),
        )
        ranked = rank_brave_results(
            results,
            organization=self.organization,
            prepared_query=prepared,
        )
        self.assertEqual(ranked[0].image_url, "https://images.example/official.jpg")

    def test_candidate_ref_binds_exact_transient_query_and_scope_without_secret(self):
        provider_results = (brave_result(),)
        with patch(
            "crm.services.images.candidates.search_brave_images",
            return_value=provider_results,
        ):
            query, query_sources, candidates = discover_brave_image_candidates(
                actor=self.actor,
                tenant_id=self.tenant.pk,
                organization_id=self.organization.pk,
                query="Bodø Bluesklubb Bodø",
            )

        self.assertEqual(query, "Bodø Bluesklubb Bodø")
        self.assertEqual(query_sources, ("organization_name", "municipality"))
        self.assertEqual(len(candidates), 1)
        payload = signing.loads(candidates[0].candidate_ref, salt=CANDIDATE_REF_SALT)
        self.assertEqual(payload["tenant_id"], self.tenant.pk)
        self.assertEqual(payload["organization_id"], self.organization.pk)
        self.assertEqual(payload["user_id"], self.actor.pk)
        self.assertEqual(payload["search_query"], query)
        self.assertEqual(payload["query_sources"], list(query_sources))
        self.assertNotIn("BRAVE_IMAGE_SEARCH_API_KEY", payload)
        self.assertNotIn("server-secret", candidates[0].candidate_ref)
        self.assertEqual(Organization.objects.count(), 1)

    @override_settings(BRAVE_IMAGE_SEARCH_API_KEY="server-secret")
    def test_candidate_keeps_missing_provider_source_domain_nullable(self):
        body = json.dumps(
            {
                "results": [
                    {
                        "properties": {
                            "url": "https://image-cdn.example/actor.jpg",
                        },
                    }
                ]
            }
        ).encode()
        provider_results = search_brave_images(
            "Bodø Bluesklubb Bodø",
            transport=lambda path, headers, timeout: (
                200,
                "application/json",
                body,
            ),
        )
        self.assertIsNone(provider_results[0].source_domain)

        with patch(
            "crm.services.images.candidates.search_brave_images",
            return_value=provider_results,
        ):
            _, _, candidates = discover_brave_image_candidates(
                actor=self.actor,
                tenant_id=self.tenant.pk,
                organization_id=self.organization.pk,
                query="Bodø Bluesklubb Bodø",
            )

        self.assertIsNone(candidates[0].source_domain)
        payload = signing.loads(candidates[0].candidate_ref, salt=CANDIDATE_REF_SALT)
        self.assertIsNone(payload["source_domain"])


@override_settings(IMAGE_ASSET_FEATURE_ENABLED=True)
class BraveImageApiTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="API search", slug="api-search")
        self.organization = Organization.objects.create(
            tenant=self.tenant,
            name="Tvibit",
            municipalities="Tromsø",
        )
        self.editor = get_user_model().objects.create_user(username="brave-api-editor", password="pw")
        self.reader = get_user_model().objects.create_user(username="brave-api-reader", password="pw")
        TenantMembership.objects.create(
            tenant=self.tenant,
            user=self.editor,
            role=TenantMembership.Role.REDIGERER,
        )
        TenantMembership.objects.create(
            tenant=self.tenant,
            user=self.reader,
            role=TenantMembership.Role.LESER,
        )
        self.base = f"/api/tenants/{self.tenant.pk}/organizations/{self.organization.pk}/images"

    def test_search_context_and_url_candidate_are_tenant_scoped_writer_actions(self):
        self.client.force_login(self.editor)
        context = self.client.get(f"{self.base}/search-context/")
        self.assertEqual(context.status_code, 200)
        self.assertEqual(context.json()["suggested_query"], "Tvibit Tromsø")

        direct = self.client.post(
            f"{self.base}/url-candidate/",
            data={"image_url": "https://images.example/tvibit.jpg"},
            content_type="application/json",
        )
        self.assertEqual(direct.status_code, 200)
        self.assertEqual(direct.json()["candidate"]["source_label"], "Direkte bilde-URL")

        self.client.force_login(self.reader)
        self.assertEqual(self.client.get(f"{self.base}/search-context/").status_code, 403)
        self.assertEqual(
            self.client.post(
                f"{self.base}/url-candidate/",
                data={"image_url": "https://images.example/tvibit.jpg"},
                content_type="application/json",
            ).status_code,
            403,
        )

    @override_settings(BRAVE_IMAGE_SEARCH_API_KEY="")
    def test_missing_provider_key_is_503_and_never_echoed(self):
        self.client.force_login(self.editor)
        response = self.client.post(
            f"{self.base}/brave-search/",
            data={"query": "Tvibit Tromsø", "query_edited": False},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "brave_not_configured")
        self.assertNotIn(b"BRAVE_IMAGE_SEARCH_API_KEY", response.content)

    def test_manual_query_cannot_smuggle_hidden_structured_refinement_to_provider(self):
        self.client.force_login(self.editor)
        with patch("crm.services.images.candidates.search_brave_images") as provider:
            response = self.client.post(
                f"{self.base}/brave-search/",
                data={
                    "query": "Eksakt synlig manuelt søk",
                    "query_edited": True,
                    "person_id": 999,
                },
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "invalid_refinement")
        provider.assert_not_called()
