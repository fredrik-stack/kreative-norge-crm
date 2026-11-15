"""Synthetic PostgreSQL proof of ADR-011's pre-cutover identity boundary."""
import json
from django.conf import settings
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse, resolve
from crm.models import (
    SharingDomain, Tenant, Organization, OrganizationTenantAssignment,
    OrganizationNoteOverlay, InternalTag, Tag, Person, PersonContact, OrganizationPerson,
)
from crm.test_phase6a1_foundation import fixture_bound, fixture_assignment


@override_settings(
    SECURE_SSL_REDIRECT=False,
    CACHES={"default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "canonical-public-identity-tests",
    }},
)
class CanonicalPublicIdentityTests(TestCase):
    def setUp(self):
        # Synthetic request volume must not consume other suites' auth budget.
        cache.clear()
        self.addCleanup(cache.clear)
        self.domain = SharingDomain.objects.create(name="Synthetic domain", slug="canonical-public")
        self.home = fixture_bound(Tenant, name="Home", slug="public-home", sharing_domain=self.domain)
        self.other = fixture_bound(Tenant, name="Other", slug="public-other", sharing_domain=self.domain)
        self.actor = fixture_bound(Organization, tenant=self.home, sharing_domain=self.domain,
                                   name="Published actor", org_number="998544092", is_published=True,
                                   note="SECRET legacy note", email="official@example.invalid")
        self.home_assignment = fixture_assignment(OrganizationTenantAssignment, organization=self.actor, tenant=self.home)
        self.other_assignment = fixture_assignment(OrganizationTenantAssignment, organization=self.actor, tenant=self.other)

    def api_id(self, actor=None):
        return reverse("public-actors-canonical-detail", kwargs={"canonical_id": (actor or self.actor).pk})

    def api_alias(self, number=None):
        return reverse("public-actors-detail", kwargs={"org_number": number or self.actor.org_number})

    def html_alias(self, number=None):
        return reverse("public-actor-detail-legacy", kwargs={"org_number": number or self.actor.org_number})

    def test_one_pk_one_public_row_and_page_independent_of_assignments_without_writes(self):
        before = list(Organization.objects.values())
        assignment_count = OrganizationTenantAssignment.objects.count()
        for flag in ("SHARING_ACCESS_ENABLED", "CANONICAL_WRITER_ENABLED", "STRICT_TENANT_ACCESS_ENABLED", "TENANT_NOTE_OVERLAYS_ENABLED"):
            self.assertIs(getattr(settings, flag), False)
        payload = self.client.get("/api/public/actors/").json()
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["canonical_id"], self.actor.pk)
        self.assertIsInstance(payload[0]["canonical_id"], int)
        self.assertEqual(self.client.get(self.api_id()).json(), payload[0])
        page = self.client.get("/public/actors/")
        self.assertEqual([actor.pk for actor in page.context["actors"]], [self.actor.pk])
        self.assertContains(page, reverse("public-actor-detail", args=[self.actor.pk]))
        self.assertEqual(list(Organization.objects.values()), before)
        self.assertEqual(OrganizationTenantAssignment.objects.count(), assignment_count)

    def test_legacy_alias_contract_and_route_names_remain_compatible(self):
        self.assertEqual(self.api_alias(), "/api/public/actors/998544092/")
        self.assertEqual(resolve(self.api_alias()).kwargs, {"org_number": "998544092"})
        self.assertEqual(self.client.get(self.api_alias()).json(), self.client.get(self.api_id()).json())
        response = self.client.get(self.html_alias())
        self.assertRedirects(response, reverse("public-actor-detail", args=[self.actor.pk]), status_code=301)

    def test_id_route_handles_missing_empty_and_url_unsafe_aliases(self):
        for number in (None, "", "unsafe/alias?"):
            with self.subTest(number=number):
                self.actor.org_number = number
                self.actor.save(update_fields=["org_number"])
                response = self.client.get(self.api_id())
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["canonical_id"], self.actor.pk)
                self.assertEqual(self.client.get(reverse("public-actor-detail", args=[self.actor.pk])).status_code, 200)

    def test_numeric_alias_is_never_reinterpreted_as_a_primary_key(self):
        other = Organization.objects.create(tenant=self.home, name="Numeric alias actor", org_number=str(self.actor.pk), is_published=True)
        self.assertEqual(self.client.get(self.api_alias(str(self.actor.pk))).json()["canonical_id"], other.pk)
        self.assertEqual(self.client.get(self.api_id()).json()["canonical_id"], self.actor.pk)

    def test_ambiguous_published_alias_across_domains_is_404_but_pks_stay_distinct(self):
        domain = SharingDomain.objects.create(name="Another domain", slug="another-public-domain")
        tenant = fixture_bound(Tenant, name="Another", slug="another-public", sharing_domain=domain)
        duplicate = fixture_bound(Organization, tenant=tenant, sharing_domain=domain, name="Other public identity",
                                  org_number=self.actor.org_number, is_published=True)
        for path in (self.api_alias(), self.html_alias()):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 404)
            self.assertNotIn("Location", response)
            self.assertNotContains(response, duplicate.name, status_code=404)
        self.assertEqual(self.client.get(self.api_alias()).json(), self.client.get(self.api_alias("missing")).json())
        self.assertEqual(self.client.get(self.api_id()).json()["canonical_id"], self.actor.pk)
        self.assertEqual(self.client.get(self.api_id(duplicate)).json()["canonical_id"], duplicate.pk)
        self.assertEqual({row["canonical_id"] for row in self.client.get("/api/public/actors/").json()}, {self.actor.pk, duplicate.pk})

    def test_private_duplicate_does_not_disclose_or_change_alias_resolution(self):
        private = Organization.objects.create(tenant=self.other, name="SECRET private actor", org_number=self.actor.org_number)
        self.assertEqual(self.client.get(self.api_alias()).json()["canonical_id"], self.actor.pk)
        self.assertRedirects(self.client.get(self.html_alias()), reverse("public-actor-detail", args=[self.actor.pk]), status_code=301)
        self.assertEqual(self.client.get(self.api_id(private)).status_code, 404)
        self.actor.is_published = False
        self.actor.save(update_fields=["is_published"])
        for path in (self.api_id(), self.api_alias(), self.html_alias(), reverse("public-actor-detail", args=[self.actor.pk])):
            self.assertEqual(self.client.get(path).status_code, 404)
        self.assertEqual(self.client.get("/api/public/actors/").json(), [])

    def test_no_private_notes_tags_assignments_revisions_or_contact_fallback_leak(self):
        for tenant in (self.home, self.other):
            internal = InternalTag.objects.create(tenant=tenant, name=f"SECRET {tenant.slug}")
            self.actor.internal_tags.add(internal)
        # Local synthetic storage setup only; runtime remains default-off.
        with override_settings(TENANT_NOTE_OVERLAYS_ENABLED=True):
            for assignment in (self.home_assignment, self.other_assignment):
                OrganizationNoteOverlay.objects.create(assignment=assignment, note=f"SECRET overlay {assignment.pk}")
        legacy_tag = Tag.objects.create(tenant=self.home, name="Legacy visible tag")
        self.actor.tags.add(legacy_tag)
        person = fixture_bound(Person, tenant=self.home, sharing_domain=self.domain, full_name="Public contact",
                               note="SECRET person note", email="SECRET-raw@example.invalid", phone="SECRET raw phone")
        PersonContact.objects.create(tenant=self.home, person=person, type="EMAIL", value="SECRET-private@example.invalid", is_public=False)
        PersonContact.objects.create(tenant=self.home, person=person, type="EMAIL", value="public@example.invalid", is_public=True)
        OrganizationPerson.objects.create(tenant=self.home, organization=self.actor, person=person, publish_person=True)
        for path in ("/api/public/actors/", self.api_alias(), self.api_id(), "/public/actors/", reverse("public-actor-detail", args=[self.actor.pk])):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertNotIn("SECRET", response.content.decode())
        data = self.client.get(self.api_id()).json()
        self.assertEqual(data["email"], "official@example.invalid")
        self.assertEqual(data["tags"], [{"id": legacy_tag.pk, "name": legacy_tag.name, "slug": legacy_tag.slug}])
        self.assertEqual(data["people"][0]["public_contacts"], [{"type": "EMAIL", "value": "public@example.invalid"}])
        for key in ("id", "tenant", "sharing_domain", "tenant_assignments", "note", "internal_tags", "canonical_write_stamp"):
            self.assertNotIn(key, data)

    def test_read_only_paths_cannot_publish_or_change_identity_and_missing_ids_are_404(self):
        before = list(Organization.objects.values())
        for path in (self.api_alias(), self.api_id()):
            for method in ("post", "put", "patch", "delete"):
                self.assertEqual(getattr(self.client, method)(path, data=json.dumps({"canonical_id": 1, "is_published": True}), content_type="application/json").status_code, 405)
        for path in ("/api/public/actors/id/0/", "/api/public/actors/id/not-an-id/", "/api/public/actors/id/999999999/", self.api_alias("missing")):
            self.assertEqual(self.client.get(path).status_code, 404)
        self.assertEqual(list(Organization.objects.values()), before)
