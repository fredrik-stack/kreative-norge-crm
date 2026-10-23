import importlib
import json
import runpy
from pathlib import Path
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.db.models.deletion import ProtectedError
from django.test import RequestFactory, TransactionTestCase, override_settings
from rest_framework.test import APIClient

from crm.models import (
    Organization, OrganizationNoteOverlay, OrganizationTenantAssignment,
    Person, PersonNoteOverlay, PersonTenantAssignment, SharingDomain, Tenant, Tag,
    ImportJob, ImportRow,
)
from crm.note_overlays import NoteOverlayError
from crm.domain_integrity import DomainStructureError
from crm.test_phase6a1_foundation import fixture_assignment, fixture_bound


@override_settings(TENANT_NOTE_OVERLAYS_ENABLED=True, SECURE_SSL_REDIRECT=False)
class NoteOverlayTests(TransactionTestCase):
    def setUp(self):
        self.domain = SharingDomain.objects.create(name="Synthetic", slug="synthetic")
        self.tenants = [fixture_bound(Tenant, name=n, slug=n, sharing_domain=self.domain)
                        for n in ("first", "second")]
        self.cases = []
        for model, assignment, overlay, field, values in (
            (Organization, OrganizationTenantAssignment, OrganizationNoteOverlay, "organization", {"name": "Actor"}),
            (Person, PersonTenantAssignment, PersonNoteOverlay, "person", {"full_name": "Person"}),
        ):
            profile = fixture_bound(model, tenant=self.tenants[0], sharing_domain=self.domain,
                                    note="legacy authoritative", **values)
            assignments = [fixture_assignment(assignment, **{field: profile, "tenant": t}) for t in self.tenants]
            self.cases.append((profile, assignments, overlay))

    def test_two_tenants_separate_notes_for_same_profile(self):
        for profile, assignments, model in self.cases:
            for assignment, note in zip(assignments, ("first private", "second private")):
                model.objects.create(assignment=assignment, note=note)
            self.assertEqual(list(model.objects.order_by("assignment__tenant_id").values_list("note", flat=True)),
                             ["first private", "second private"])
            profile.refresh_from_db()
            self.assertEqual(profile.note, "legacy authoritative")
            self.assertEqual({f.name for f in model._meta.fields}, {"id", "assignment", "note"})

    def test_null_empty_whitespace_and_text_roundtrip_without_fallback(self):
        for _, assignments, model in self.cases:
            row = model.objects.create(assignment=assignments[0], note=None)
            for note in (None, "", "  \n\t", "Æ exact\nline\r\nend "):
                row.note = note; row.save(); row.refresh_from_db()
                self.assertEqual(row.note, note)
                model.objects.filter(pk=row.pk).update(note=note)
                row.refresh_from_db(); self.assertEqual(row.note, note)
            row.note = ""; model.objects.bulk_update([row], ["note"])
            row.refresh_from_db(); self.assertEqual(row.note, "")

    def test_gate_blocks_all_ordinary_mutation_paths_and_base_manager(self):
        for _, assignments, model in self.cases:
            row = model.objects.create(assignment=assignments[0], note="retained")
            new = lambda: model(assignment=assignments[1], note="blocked")
            paths = [
                lambda: new().save(), lambda: new().save_base(raw=True),
                lambda: model.objects.create(assignment=assignments[1]),
                lambda: model.objects.get_or_create(assignment=assignments[1]),
                lambda: model.objects.update_or_create(assignment=assignments[0], defaults={"note": "blocked"}),
                lambda: model.objects.bulk_create([new()]),
                lambda: model.objects.bulk_create([new()], ignore_conflicts=True),
                lambda: model.objects.bulk_update([row], ["note"]),
                lambda: model.objects.all().update(note="blocked"),
                lambda: model._base_manager.all().update(note="blocked"),
                lambda: row.save(update_fields=["note"]), lambda: row.delete(),
                lambda: model.objects.all().delete(),
                lambda: model.objects.all()._raw_delete("default"),
            ]
            with override_settings(TENANT_NOTE_OVERLAYS_ENABLED=False):
                for path in paths:
                    with self.subTest(model=model.__name__, path=paths.index(path)):
                        with self.assertRaises(NoteOverlayError):
                            path()
            row.refresh_from_db(); self.assertEqual(row.note, "retained")
            self.assertEqual(model.objects.count(), 1)

    def test_nonboolean_gate_fails_closed(self):
        for value in (None, 1, "True", "False"):
            with override_settings(TENANT_NOTE_OVERLAYS_ENABLED=value):
                for _, assignments, model in self.cases:
                    with self.assertRaises(NoteOverlayError):
                        model.objects.create(assignment=assignments[0])

    def test_gate_on_bulk_create_update_or_create_and_delete(self):
        for _, assignments, model in self.cases:
            model.objects.bulk_create([model(assignment=a, note="bulk") for a in assignments])
            row, created = model.objects.update_or_create(assignment=assignments[0], defaults={"note": "updated"})
            self.assertFalse(created); self.assertEqual(row.note, "updated")
            row.delete()
            model.objects.all().delete()
            self.assertEqual(model.objects.count(), 0)

    def test_database_uniqueness_and_reference_integrity(self):
        for _, assignments, model in self.cases:
            model.objects.create(assignment=assignments[0])
            for values in ({"assignment": assignments[0]}, {"assignment_id": None}, {"assignment_id": 999999}):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    model.objects.create(**values)
                    connection.check_constraints()

    def test_rebinding_rejected_by_orm_and_database(self):
        for _, assignments, model in self.cases:
            row = model.objects.create(assignment=assignments[0])
            with self.assertRaises(NoteOverlayError):
                model.objects.filter(pk=row.pk).update(assignment=assignments[1])
            row.assignment = assignments[1]
            with self.assertRaises(NoteOverlayError):
                model.objects.bulk_update([row], ["assignment"])
            with self.assertRaises(IntegrityError), transaction.atomic():
                row.save()
            with self.assertRaises(IntegrityError), transaction.atomic(), connection.cursor() as cursor:
                cursor.execute(f'UPDATE "{model._meta.db_table}" SET assignment_id=%s WHERE id=%s', [assignments[1].pk, row.pk])
            with self.assertRaises(IntegrityError), transaction.atomic(), connection.cursor() as cursor:
                cursor.execute(f'UPDATE "{model._meta.db_table}" SET id=id+100000 WHERE id=%s', [row.pk])
            row.refresh_from_db(); self.assertEqual(row.assignment_id, assignments[0].pk)
            row.pk += 100000
            with self.assertRaises(NoteOverlayError):
                row.save()

    def test_upsert_cannot_rebind(self):
        for _, assignments, model in self.cases:
            row = model.objects.create(assignment=assignments[0])
            with self.assertRaises(NoteOverlayError):
                model.objects.bulk_create([model(pk=row.pk, assignment=assignments[1])],
                                          update_conflicts=True, update_fields=["assignment"], unique_fields=["id"])

    def test_existing_parent_delete_guards_remain(self):
        for profile, assignments, model in self.cases:
            model.objects.create(assignment=assignments[0])
            for target in (profile, self.tenants[0], self.domain):
                with self.assertRaises(ProtectedError):
                    target.delete()
            # Assignment's existing ORM/DB guards remain, not an overlay-owned lifecycle.
            with self.assertRaises(DomainStructureError):
                assignments[0].delete()

    def test_invalid_parent_scope_rejected_by_existing_database_contract(self):
        other_domain = SharingDomain.objects.create(name="Other", slug="other")
        other = fixture_bound(Tenant, name="Other", slug="other", sharing_domain=other_domain)
        unbound = Tenant.objects.create(name="Unbound", slug="unbound")
        for profile, assignments, _ in self.cases:
            field = "organization" if isinstance(profile, Organization) else "person"
            for tenant in (other, unbound):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    fixture_assignment(type(assignments[0]), **{field: profile, "tenant": tenant})

    def test_no_api_admin_matching_or_public_exposure_even_with_storage_gate_on(self):
        client = APIClient()
        user = get_user_model().objects.create_superuser(username="synthetic", password="synthetic")
        client.force_authenticate(user)
        matchers = importlib.import_module("crm.services.import.matchers")
        normalizers = importlib.import_module("crm.services.import.normalizers")
        for profile, assignments, model in self.cases:
            model.objects.create(assignment=assignments[0], note="OVERLAY-SECRET-SENTINEL")
            self.assertNotIn(model, admin.site._registry)
            kind = "organizations" if isinstance(profile, Organization) else "persons"
            base = f"/api/tenants/{self.tenants[0].pk}/{kind}/"
            response = client.get(f"{base}{profile.pk}/")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["note"], "legacy authoritative")
            self.assertNotIn("OVERLAY-SECRET", str(response.json()))
            response = client.patch(f"{base}{profile.pk}/", {"note": "legacy changed", "note_overlay": {"note": "forged"}}, format="json")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(model.objects.get().note, "OVERLAY-SECRET-SENTINEL")
            data = {"name": "New"} if kind == "organizations" else {"full_name": "New"}
            self.assertEqual(client.post(base, data, format="json").status_code, 201)
            self.assertEqual(model.objects.count(), 1)
            request = RequestFactory().get("/admin/"); request.user = user
            form_class = admin.site._registry[type(profile)].get_form(request, profile)
            self.assertIn("note", form_class.base_fields)
            self.assertNotIn("note_overlay", form_class.base_fields)
        from crm.serializers_public import PublicActorSerializer
        self.assertNotIn("note", PublicActorSerializer().fields)
        payload = normalizers.normalize_import_row({"organization_name": "Actor", "person_full_name": "Person"})
        result = matchers.match_row_entities(self.tenants[0], payload)
        self.assertNotIn("OVERLAY-SECRET", str(result))

    def test_legacy_import_ai_admin_and_m2m_do_not_create_or_read_overlays(self):
        normalizers = importlib.import_module("crm.services.import.normalizers")
        commit = importlib.import_module("crm.services.import.commit")
        ai = importlib.import_module("crm.services.import.ai_suggestions")
        user = get_user_model().objects.create_superuser(username="importer", password="synthetic")
        for gate in (False, True):
            with override_settings(TENANT_NOTE_OVERLAYS_ENABLED=gate):
                job = ImportJob.objects.create(tenant=self.tenants[0], created_by=user, source_type="CSV",
                                               status=ImportJob.Status.PREVIEW_READY,
                                               config_json=normalizers.build_import_template_config("COMBINED"))
                payload = normalizers.normalize_import_row({"organization_name": "Actor", "person_full_name": "Person",
                    "organization_note": "import note", "person_note": "", "organization_tags": "synthetic tag"})
                ImportRow.objects.create(import_job=job, row_number=1, normalized_payload_json=payload,
                    row_status=ImportRow.RowStatus.VALID, proposed_action=ImportRow.ProposedAction.UPDATE,
                    match_result_json={"organization": {"exact_id": self.cases[0][0].pk},
                                       "person": {"exact_id": self.cases[1][0].pk}})
                commit.commit_import_job(job)
                for profile, _, model in self.cases:
                    profile.refresh_from_db()
                    self.assertEqual(profile.note, "import note" if isinstance(profile, Organization) else None)
                    request = RequestFactory().post("/admin/"); request.user = user
                    profile.note = "admin legacy"
                    admin.site._registry[type(profile)].save_model(request, profile, None, change=True)
                    tag = Tag.objects.get(tenant=self.tenants[0], name="synthetic tag")
                    profile.tags.add(tag); profile.tags.remove(tag); profile.tags.set([tag]); profile.tags.clear()
                    self.assertEqual(model.objects.count(), 0)
                self.assertEqual(ai._suggest_description(payload), "import note")


class NoteOverlayMigrationTests(TransactionTestCase):
    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def test_additive_forward_empty_reverse_preserves_all_existing_tables(self):
        old = ("crm", "0034_legacy_domain_integrity")
        executor = MigrationExecutor(connection); executor.migrate([old])
        apps = executor.loader.project_state([old]).apps
        tenant = apps.get_model("crm", "Tenant").objects.create(name="Migration", slug="migration")
        for name, values in (("Organization", {"name": "Actor"}), ("Person", {"full_name": "Person"})):
            for note in (None, "", "exact\ntext "):
                apps.get_model("crm", name).objects.create(tenant=tenant, note=note, **values)
        tables = sorted(connection.introspection.table_names())
        def snapshot():
            with connection.cursor() as cursor:
                rows = {}
                for table in tables:
                    if table != "django_migrations":
                        cursor.execute(f'SELECT * FROM "{table}" ORDER BY 1')
                        rows[table] = cursor.fetchall()
                return rows
        before = snapshot()
        latest = ("crm", "0035_tenant_note_overlay_foundation")
        for target in ([latest], [old], [latest]):
            executor = MigrationExecutor(connection); executor.migrate(target)
            self.assertEqual(snapshot(), before)
            if target == [latest]:
                for name in ("OrganizationNoteOverlay", "PersonNoteOverlay"):
                    self.assertEqual(executor.loader.project_state(target).apps.get_model("crm", name).objects.count(), 0)

    @override_settings(TENANT_NOTE_OVERLAYS_ENABLED=True)
    def test_reverse_rejects_semantic_overlay_state(self):
        domain = SharingDomain.objects.create(name="Migration", slug="migration")
        tenant = fixture_bound(Tenant, name="Migration", slug="migration", sharing_domain=domain)
        person = fixture_bound(Person, full_name="Person", tenant=tenant, sharing_domain=domain)
        assignment = fixture_assignment(PersonTenantAssignment, person=person, tenant=tenant)
        row = PersonNoteOverlay.objects.create(assignment=assignment, note="")
        with self.assertRaisesRegex(RuntimeError, "nonempty"), transaction.atomic():
            MigrationExecutor(connection).migrate([("crm", "0034_legacy_domain_integrity")])
        self.assertTrue(PersonNoteOverlay.objects.filter(pk=row.pk).exists())


class NoteInventoryTests(TransactionTestCase):
    def setUp(self):
        from crm.services.domain_read_shadow import DOMAIN, TENANTS
        from crm.services.domain_backfill import database_identity
        domain = SharingDomain.objects.create(**DOMAIN)
        self.tenants = {i: fixture_bound(Tenant, id=i, slug=s, name=n, sharing_domain=domain)
                        for i, s, n in TENANTS}
        self.domain = domain
        self.inventory = runpy.run_path(str(Path(__file__).resolve().parents[1] / "ops/staging/inventory-tenant-notes.py"))["inventory"]
        self.args = (database_identity(), "a" * 40)

    def test_exact_note_categories_assignment_prerequisites_and_sanitized_tags(self):
        for note in (None, "", "  \n\t", "SECRET-NOTE-SENTINEL"):
            profile = fixture_bound(Person, full_name="SECRET-PROFILE", tenant=self.tenants[1], sharing_domain=self.domain, note=note)
            fixture_assignment(PersonTenantAssignment, person=profile, tenant=self.tenants[1])
        Person.objects.create(tenant=self.tenants[2], full_name="unbound")
        tag = Tag.objects.create(tenant=self.tenants[1], name="SECRET-TAG", slug="secret")
        Tag.objects.create(tenant=self.tenants[1], name="UNUSED-SECRET", slug="unused")
        for profile in Person.objects.filter(tenant_id=1): profile.tags.add(tag)
        report = self.inventory(*self.args)
        self.assertEqual(report["completed_rows"], 14)
        row = next(r for r in report["rows"] if r["tenant_id"]==1 and r["model"]=="Person")
        self.assertEqual(row["notes"], {"null":1,"empty":1,"whitespace":1,"text":1})
        self.assertEqual((row["eligible_own_assignment"], row["tag_links"], row["distinct_linked_tags"]), (4,4,1))
        row = next(r for r in report["rows"] if r["tenant_id"]==2 and r["model"]=="Person")
        self.assertEqual((row["null_domain"],row["missing_own_assignment"]), (1,1))
        self.assertEqual(report["tags"][0]["unused_tags"],1)
        self.assertNotIn("SECRET",json.dumps(report))
        self.assertEqual(report["deviations"],{})
        self.assertEqual(PersonNoteOverlay.objects.count(),0)

    def test_cross_tenant_tag_links_and_nonlegacy_assignments_are_not_filtered_out(self):
        profile=fixture_bound(Organization,name="Actor",tenant=self.tenants[1],sharing_domain=self.domain,is_published=True)
        fixture_assignment(OrganizationTenantAssignment,organization=profile,tenant=self.tenants[2])
        tag=Tag.objects.create(tenant=self.tenants[2],name="private",slug="private")
        profile.tags.add(tag)
        report=self.inventory(*self.args)
        self.assertEqual(report["deviations"]["tag_cross_tenant_link"],1)
        self.assertEqual(report["deviations"]["nonlegacy_assignment"],1)
        row=next(r for r in report["rows"] if r["model"]=="Organization" and r["tenant_id"]==1)
        self.assertEqual((row["missing_own_assignment"],row["published_actor_tag_links"]),(1,1))

    def test_wrong_scope_database_and_outer_transaction_rejected(self):
        with self.assertRaisesRegex(RuntimeError,"DATABASE_MISMATCH"):
            self.inventory("wrong",self.args[1])
        with transaction.atomic(), self.assertRaisesRegex(RuntimeError,"TRANSACTION_CONTEXT"):
            self.inventory(*self.args)
        self.tenants[1].name="unexpected";self.tenants[1].save(update_fields=["name"])
        with self.assertRaisesRegex(Exception,"SCOPE_MISMATCH"):
            self.inventory(*self.args)

    def test_inventory_readonly_transaction_rejects_accidental_write(self):
        def accidental():
            Person.objects.create(tenant=self.tenants[1],full_name="must not persist")
        from django.db import DatabaseError
        with patch.dict(self.inventory.__globals__, {"_require_scope":accidental}):
            with self.assertRaises(DatabaseError): self.inventory(*self.args)
        self.assertEqual(Person.objects.count(),0)
