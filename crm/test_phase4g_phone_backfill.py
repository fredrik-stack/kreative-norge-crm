import json
import os
from pathlib import Path
from io import StringIO
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from crm.models import Organization, Person, PersonContact, Tenant
from crm.services.phone_backfill import phone_backfill_fingerprints


class Phase4GPhoneBackfillTests(TestCase):
    def setUp(self):
        self.tenants = [
            Tenant.objects.create(name=f"Tenant {index}", slug=f"phase4g-{index}")
            for index in range(1, 4)
        ]

    @property
    def tenant_ids(self):
        return [tenant.id for tenant in self.tenants]

    def command_options(self, **overrides):
        options = {
            "tenant_ids": self.tenant_ids,
            "expect_total_tenants": 3,
            "default_region": "NO",
        }
        options.update(overrides)
        return options

    def run_command(self, **options):
        output = StringIO()
        call_command(
            "backfill_phone_identity",
            stdout=output,
            **self.command_options(**options),
        )
        return json.loads(output.getvalue())

    def secure_manifest_path(self, filename="phase4g-manifest.json"):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        os.chmod(temporary.name, 0o700)
        return Path(temporary.name) / filename

    def create_matching_primary_phone(self, *, tenant, raw_phone, name):
        person = Person.objects.create(
            tenant=tenant,
            full_name=name,
            phone=raw_phone,
        )
        contact = PersonContact.objects.create(
            tenant=tenant,
            person=person,
            type="PHONE",
            value=raw_phone,
            is_primary=True,
            is_public=True,
        )
        return person, contact

    def test_default_mode_is_redacted_dry_run_with_no_writes(self):
        raw_phone = "22 12 34 56"
        organization = Organization.objects.create(
            tenant=self.tenants[0],
            name="Dry run",
            phone=raw_phone,
            is_published=True,
            publish_phone=True,
        )
        before = phone_backfill_fingerprints(self.tenant_ids)

        first = self.run_command()
        second = self.run_command()

        organization.refresh_from_db()
        for tenant in self.tenants:
            tenant.refresh_from_db()
            self.assertIsNone(tenant.default_phone_region)
        self.assertIsNone(organization.phone_normalized)
        self.assertEqual(first, second)
        self.assertEqual(first["mode"], "DRY_RUN")
        self.assertEqual(first["changes_total"], 4)
        self.assertEqual(first["changes_applied"], 0)
        self.assertEqual(first["fingerprints_before"], before)
        self.assertEqual(first["fingerprints_after"], before)
        self.assertNotIn(raw_phone, json.dumps(first))

    def test_tenant_gate_requires_exact_complete_expected_scope(self):
        with self.assertRaises(CommandError):
            self.run_command(tenant_ids=self.tenant_ids[:2])

        Tenant.objects.create(name="Unexpected", slug="phase4g-unexpected")
        with self.assertRaises(CommandError):
            self.run_command()

    def test_apply_backfills_valid_identity_preserves_raw_and_publication_and_is_idempotent(self):
        national_raw = "22 12 34 56"
        plus_raw = "+46 8 505 103 00"
        invalid_raw = "123"
        national = Organization.objects.create(
            tenant=self.tenants[0],
            name="National",
            phone=national_raw,
            is_published=True,
            publish_phone=True,
        )
        plus = Organization.objects.create(
            tenant=self.tenants[1],
            name="Plus",
            phone=plus_raw,
        )
        invalid = Organization.objects.create(
            tenant=self.tenants[2],
            name="Invalid",
            phone=invalid_raw,
        )
        _, primary = self.create_matching_primary_phone(
            tenant=self.tenants[0],
            raw_phone=national_raw,
            name="Primary national",
        )
        contact_only_person = Person.objects.create(
            tenant=self.tenants[1],
            full_name="Contact only",
        )
        contact_only = PersonContact.objects.create(
            tenant=self.tenants[1],
            person=contact_only_person,
            type="PHONE",
            value=plus_raw,
            is_public=False,
        )
        shared_people = [
            Person.objects.create(
                tenant=self.tenants[2],
                full_name=f"Shared {index}",
            )
            for index in range(2)
        ]
        shared_contacts = [
            PersonContact.objects.create(
                tenant=self.tenants[2],
                person=person,
                type="PHONE",
                value="900 12 345",
            )
            for person in shared_people
        ]
        consistent = Organization.objects.create(
            tenant=self.tenants[2],
            name="Already canonical",
            phone=plus_raw,
            phone_normalized="+46850510300",
        )
        before = phone_backfill_fingerprints(self.tenant_ids)
        manifest_path = self.secure_manifest_path()

        report = self.run_command(
            apply=True,
            batch_id="phase4g-test-apply",
            manifest_path=str(manifest_path),
        )

        for tenant in self.tenants:
            tenant.refresh_from_db()
            self.assertEqual(tenant.default_phone_region, "NO")
        national.refresh_from_db()
        plus.refresh_from_db()
        invalid.refresh_from_db()
        primary.refresh_from_db()
        contact_only.refresh_from_db()
        consistent.refresh_from_db()
        for contact in shared_contacts:
            contact.refresh_from_db()
        self.assertEqual(national.phone, national_raw)
        self.assertEqual(national.phone_normalized, "+4722123456")
        self.assertEqual(national.phone_normalization_region, "NO")
        self.assertTrue(national.is_published)
        self.assertTrue(national.publish_phone)
        self.assertEqual(plus.phone, plus_raw)
        self.assertEqual(plus.phone_normalized, "+46850510300")
        self.assertIsNone(plus.phone_normalization_region)
        self.assertIsNone(invalid.phone_normalized)
        self.assertEqual(primary.normalized_value, "+4722123456")
        self.assertEqual(primary.normalization_region, "NO")
        self.assertTrue(primary.is_public)
        self.assertEqual(contact_only.normalized_value, "+46850510300")
        self.assertIsNone(contact_only.normalization_region)
        self.assertTrue(
            all(
                contact.normalized_value == "+4790012345"
                for contact in shared_contacts
            )
        )
        self.assertEqual(consistent.phone_normalized, "+46850510300")

        after = phone_backfill_fingerprints(self.tenant_ids)
        self.assertEqual(before["raw_phone"], after["raw_phone"])
        self.assertEqual(before["publication"], after["publication"])
        self.assertNotEqual(before["additive_identity"], after["additive_identity"])
        self.assertEqual(report["changes_applied"], report["changes_total"])
        self.assertEqual(
            report["classifications"]["Organization"][str(self.tenants[2].id)][
                "INVALID:NOT_POSSIBLE"
            ],
            1,
        )

        manifest_text = manifest_path.read_text(encoding="utf-8")
        self.assertEqual(manifest_path.stat().st_mode & 0o777, 0o600)
        manifest = json.loads(manifest_text)
        self.assertEqual(manifest["batch_id"], "phase4g-test-apply")
        self.assertNotIn(f'"{national_raw}"', manifest_text)
        self.assertNotIn(f'"{plus_raw}"', manifest_text)
        self.assertNotIn(f'"{invalid_raw}"', manifest_text)
        self.assertNotIn('"+4722123456"', manifest_text)
        self.assertNotIn('"+46850510300"', manifest_text)
        self.assertTrue(all("new" not in change for change in manifest["changes"]))
        self.assertTrue(
            all(
                set(change["old"])
                <= {
                    "default_phone_region",
                    "phone_normalized",
                    "phone_normalization_region",
                    "normalized_value",
                    "normalization_region",
                }
                for change in manifest["changes"]
            )
        )
        self.assertEqual(
            report["identity_changes_by_model_tenant_result"]["Organization"][
                str(self.tenants[0].id)
            ]["VALID:NONE"],
            1,
        )
        self.assertFalse(
            any(
                change["model"] == "Organization" and change["pk"] == consistent.id
                for change in manifest["changes"]
            )
        )

        idempotent = self.run_command()
        self.assertEqual(idempotent["changes_total"], 0)
        self.assertEqual(idempotent["tenant_already_configured"], 3)
        self.assertGreaterEqual(
            sum(idempotent["existing_identity_consistent"].values()),
            7,
        )

        rollback_dry_run_output = StringIO()
        call_command(
            "backfill_phone_identity",
            rollback_manifest=str(manifest_path),
            stdout=rollback_dry_run_output,
        )
        rollback_dry_run = json.loads(rollback_dry_run_output.getvalue())
        self.assertEqual(rollback_dry_run["mode"], "ROLLBACK_DRY_RUN")
        national.refresh_from_db()
        self.assertEqual(national.phone_normalized, "+4722123456")

        rollback_output = StringIO()
        call_command(
            "backfill_phone_identity",
            rollback_manifest=str(manifest_path),
            apply=True,
            stdout=rollback_output,
        )
        rollback = json.loads(rollback_output.getvalue())
        self.assertEqual(rollback["mode"], "ROLLBACK_APPLY")
        self.assertEqual(rollback["changes_applied"], report["changes_applied"])
        national.refresh_from_db()
        primary.refresh_from_db()
        consistent.refresh_from_db()
        self.assertIsNone(national.phone_normalized)
        self.assertIsNone(primary.normalized_value)
        self.assertEqual(consistent.phone_normalized, "+46850510300")
        for tenant in self.tenants:
            tenant.refresh_from_db()
            self.assertIsNone(tenant.default_phone_region)
        self.assertEqual(phone_backfill_fingerprints(self.tenant_ids), before)

    def test_conflicting_existing_canonical_value_blocks_apply_without_manifest(self):
        organization = Organization.objects.create(
            tenant=self.tenants[0],
            name="Conflict",
            phone="22 12 34 56",
            phone_normalized="+4790012345",
            phone_normalization_region="NO",
        )
        manifest_path = self.secure_manifest_path()

        with self.assertRaises(CommandError):
            self.run_command(
                apply=True,
                batch_id="phase4g-conflict",
                manifest_path=str(manifest_path),
            )

        organization.refresh_from_db()
        self.assertEqual(organization.phone_normalized, "+4790012345")
        self.assertFalse(manifest_path.exists())
        self.assertTrue(
            all(tenant.default_phone_region is None for tenant in self.tenants)
        )

    def test_person_primary_integrity_and_cross_tenant_contact_block_forward_run(self):
        Person.objects.create(
            tenant=self.tenants[0],
            full_name="Missing primary",
            phone="22 12 34 56",
        )
        with self.assertRaises(CommandError):
            self.run_command()

        Person.objects.all().delete()
        person = Person.objects.create(
            tenant=self.tenants[0],
            full_name="Wrong tenant contact",
        )
        PersonContact.objects.create(
            tenant=self.tenants[1],
            person=person,
            type="PHONE",
            value="22 12 34 56",
        )
        with self.assertRaises(CommandError):
            self.run_command()

    def test_apply_requires_secure_external_no_clobber_manifest(self):
        with self.assertRaises(CommandError):
            self.run_command(apply=True, batch_id="phase4g-no-manifest")

        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        os.chmod(temporary.name, 0o755)
        insecure_path = Path(temporary.name) / "manifest.json"
        with self.assertRaises(CommandError):
            self.run_command(
                apply=True,
                batch_id="phase4g-insecure",
                manifest_path=str(insecure_path),
            )
        self.assertFalse(insecure_path.exists())
        self.assertTrue(all(tenant.default_phone_region is None for tenant in self.tenants))

    def test_rollback_refuses_post_batch_drift_without_partial_restore(self):
        first = Organization.objects.create(
            tenant=self.tenants[0],
            name="First",
            phone="22 12 34 56",
        )
        second = Organization.objects.create(
            tenant=self.tenants[1],
            name="Second",
            phone="22 12 34 57",
        )
        manifest_path = self.secure_manifest_path()
        self.run_command(
            apply=True,
            batch_id="phase4g-drift",
            manifest_path=str(manifest_path),
        )
        Organization.objects.filter(pk=second.pk).update(
            phone_normalized="+4790012345",
            phone_normalization_region=None,
        )

        with self.assertRaises(CommandError):
            call_command(
                "backfill_phone_identity",
                rollback_manifest=str(manifest_path),
                apply=True,
                stdout=StringIO(),
            )

        first.refresh_from_db()
        self.assertEqual(first.phone_normalized, "+4722123456")
        self.assertTrue(
            all(
                Tenant.objects.get(pk=tenant.pk).default_phone_region == "NO"
                for tenant in self.tenants
            )
        )

    def test_rollback_refuses_tampered_manifest_schema(self):
        Organization.objects.create(
            tenant=self.tenants[0],
            name="Tamper target",
            phone="22 12 34 56",
        )
        manifest_path = self.secure_manifest_path()
        self.run_command(
            apply=True,
            batch_id="phase4g-tamper",
            manifest_path=str(manifest_path),
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["new_state_sha256"] = 123
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        with self.assertRaises(CommandError):
            call_command(
                "backfill_phone_identity",
                rollback_manifest=str(manifest_path),
                apply=True,
                stdout=StringIO(),
            )

        self.assertTrue(
            all(
                Tenant.objects.get(pk=tenant.pk).default_phone_region == "NO"
                for tenant in self.tenants
            )
        )
