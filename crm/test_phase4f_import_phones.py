import importlib
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from crm.models import (
    ImportDecision,
    ImportJob,
    ImportRow,
    Organization,
    Person,
    PersonContact,
    Tenant,
)

commit_import_job = importlib.import_module(
    "crm.services.import.commit"
).commit_import_job
match_row_entities = importlib.import_module(
    "crm.services.import.matchers"
).match_row_entities
import_normalizers = importlib.import_module("crm.services.import.normalizers")
build_import_template_config = import_normalizers.build_import_template_config
normalize_import_row = import_normalizers.normalize_import_row
_row_outcome = importlib.import_module("crm.services.import.preview")._row_outcome
validate_normalized_row = importlib.import_module(
    "crm.services.import.validators"
).validate_normalized_row


@override_settings(SECURE_SSL_REDIRECT=False)
class Phase4FImportJobRegionApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            username="phase4f-admin",
            password="test-password",
        )
        self.client.force_authenticate(self.user)
        self.tenant = Tenant.objects.create(
            name="Import tenant",
            slug="phase4f-import",
            default_phone_region="NO",
        )

    def create_job(self, payload=None):
        return self.client.post(
            f"/api/tenants/{self.tenant.id}/import-jobs/",
            payload
            or {
                "source_type": ImportJob.SourceType.CSV,
                "import_mode": ImportJob.ImportMode.COMBINED,
            },
            format="json",
        )

    def test_explicit_job_region_overrides_tenant_default(self):
        response = self.create_job(
            {
                "source_type": ImportJob.SourceType.CSV,
                "import_mode": ImportJob.ImportMode.COMBINED,
                "phone_region": "se",
            }
        )
        self.assertEqual(response.status_code, 201, response.content)
        job = ImportJob.objects.get(pk=response.json()["id"])
        self.assertEqual(job.config_json["phone_region"], "SE")

    def test_tenant_default_is_snapshotted_and_later_change_does_not_rewrite_job(self):
        response = self.create_job()
        self.assertEqual(response.status_code, 201, response.content)
        job = ImportJob.objects.get(pk=response.json()["id"])
        self.assertEqual(job.config_json["phone_region"], "NO")

        self.tenant.default_phone_region = "SE"
        self.tenant.save(update_fields=["default_phone_region"])
        job.refresh_from_db()
        self.assertEqual(job.config_json["phone_region"], "NO")

    def test_explicit_null_can_disable_tenant_default_and_invalid_region_is_rejected(self):
        response = self.create_job(
            {
                "source_type": ImportJob.SourceType.CSV,
                "import_mode": ImportJob.ImportMode.PEOPLE_ONLY,
                "phone_region": None,
            }
        )
        self.assertEqual(response.status_code, 201, response.content)
        job = ImportJob.objects.get(pk=response.json()["id"])
        self.assertIsNone(job.config_json["phone_region"])

        invalid = self.create_job(
            {
                "source_type": ImportJob.SourceType.CSV,
                "import_mode": ImportJob.ImportMode.PEOPLE_ONLY,
                "phone_region": "ZZ",
            }
        )
        self.assertEqual(invalid.status_code, 400)


class Phase4FImportPhoneContractTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="phase4f-user")
        self.tenant = Tenant.objects.create(name="Tenant", slug="phase4f")
        self.other_tenant = Tenant.objects.create(name="Other", slug="phase4f-other")

    def test_plus_number_ignores_job_region_and_blank_is_keep(self):
        plus = normalize_import_row(
            {"person_full_name": "Ada", "person_phone": "+46 8 505 103 00"},
            ImportJob.ImportMode.PEOPLE_ONLY,
            phone_region="NO",
        )["person"]["phone_normalization"]
        self.assertEqual(plus["status"], "VALID")
        self.assertEqual(plus["e164"], "+46850510300")
        self.assertIsNone(plus["region_used"])

        with patch(
            "crm.services.import.normalizers.normalize_phone_identity",
            side_effect=AssertionError("blank phone must not call adapter"),
        ):
            blank = normalize_import_row(
                {"person_full_name": "Ada", "person_phone": ""},
                ImportJob.ImportMode.PEOPLE_ONLY,
                phone_region=None,
            )["person"]["phone_normalization"]
        self.assertEqual(blank["status"], "KEEP")
        self.assertIsNone(blank["reason_code"])

    def test_national_valid_needs_region_and_invalid_are_typed_for_review(self):
        valid_payload = normalize_import_row(
            {"person_full_name": "Ada", "person_phone": "22 12 34 56"},
            ImportJob.ImportMode.PEOPLE_ONLY,
            phone_region="NO",
        )
        self.assertEqual(valid_payload["person"]["phone_normalization"]["status"], "VALID")
        self.assertEqual(valid_payload["person"]["phone_normalization"]["e164"], "+4722123456")
        self.assertEqual(valid_payload["person"]["phone_normalization"]["region_used"], "NO")

        for raw_phone, expected_status, expected_reason in (
            ("22 12 34 56", "NEEDS_REGION", "REGION_REQUIRED"),
            ("123", "INVALID", "NOT_POSSIBLE"),
        ):
            payload = normalize_import_row(
                {"person_full_name": "Ada", "person_phone": raw_phone},
                ImportJob.ImportMode.PEOPLE_ONLY,
                phone_region=None if expected_status == "NEEDS_REGION" else "NO",
            )
            phone_result = payload["person"]["phone_normalization"]
            self.assertEqual(phone_result["status"], expected_status)
            self.assertEqual(phone_result["reason_code"], expected_reason)
            errors, warnings = validate_normalized_row(self.tenant, payload)
            matches = match_row_entities(self.tenant, payload)
            row_status, action = _row_outcome(payload, errors, warnings, matches)
            self.assertEqual(row_status, ImportRow.RowStatus.REVIEW_REQUIRED)
            self.assertEqual(action, ImportRow.ProposedAction.SKIP)
            self.assertTrue(any(warning.startswith("Phone review required:") for warning in warnings))

    def test_normalized_name_and_phone_matches_but_phone_alone_never_merges(self):
        ada = Person.objects.create(tenant=self.tenant, full_name="Ada Example", phone="900 12 345")
        PersonContact.objects.create(
            tenant=self.tenant,
            person=ada,
            type="PHONE",
            value="900 12 345",
            normalized_value="+4790012345",
            normalization_region="NO",
            is_primary=True,
        )
        other_name = Person.objects.create(tenant=self.tenant, full_name="Else Example")
        PersonContact.objects.create(
            tenant=self.tenant,
            person=other_name,
            type="PHONE",
            value="+47 900 12 345",
            normalized_value="+4790012345",
            is_primary=True,
        )

        match = match_row_entities(
            self.tenant,
            normalize_import_row(
                {"person_full_name": "Ada Example", "person_phone": "+47 900 12 345"},
                ImportJob.ImportMode.PEOPLE_ONLY,
            ),
        )["person"]
        self.assertEqual(match["status"], "EXACT")
        self.assertEqual(match["rule"], "NAME_AND_PHONE")
        self.assertEqual(match["phone_signal"], "NORMALIZED")
        self.assertEqual(match["exact_id"], ada.id)

        different_name = match_row_entities(
            self.tenant,
            normalize_import_row(
                {"person_full_name": "New Person", "person_phone": "+47 900 12 345"},
                ImportJob.ImportMode.PEOPLE_ONLY,
            ),
        )["person"]
        self.assertNotEqual(different_name.get("exact_id"), other_name.id)

    def test_ambiguous_same_name_and_phone_never_auto_merges(self):
        for index in range(2):
            person = Person.objects.create(tenant=self.tenant, full_name="Same Name")
            PersonContact.objects.create(
                tenant=self.tenant,
                person=person,
                type="PHONE",
                value=f"+47 900 12 34{index}",
                normalized_value="+4790012345",
            )
        match = match_row_entities(
            self.tenant,
            normalize_import_row(
                {"person_full_name": "Same Name", "person_phone": "+47 900 12 345"},
                ImportJob.ImportMode.PEOPLE_ONLY,
            ),
        )["person"]
        self.assertEqual(match["status"], "FUZZY")
        self.assertIsNone(match["exact_id"])

    def test_legacy_raw_fallback_remains_tenant_scoped_before_backfill(self):
        legacy = Person.objects.create(
            tenant=self.tenant,
            full_name="Legacy Person",
            phone="22 12 34 56",
        )
        other = Person.objects.create(
            tenant=self.other_tenant,
            full_name="Legacy Person",
            phone="22 12 34 56",
        )
        payload = normalize_import_row(
            {"person_full_name": "Legacy Person", "person_phone": "22 12 34 56"},
            ImportJob.ImportMode.PEOPLE_ONLY,
            phone_region="NO",
        )
        match = match_row_entities(self.tenant, payload)["person"]
        self.assertEqual(match["exact_id"], legacy.id)
        self.assertNotEqual(match["exact_id"], other.id)
        self.assertEqual(match["phone_signal"], "LEGACY_RAW")

    def _commit_organization_payload(self, organization, raw_payload, *, phone_region):
        job = ImportJob.objects.create(
            tenant=self.tenant,
            created_by=self.user,
            source_type=ImportJob.SourceType.CSV,
            import_mode=ImportJob.ImportMode.ORGANIZATIONS_ONLY,
            status=ImportJob.Status.PREVIEW_READY,
            config_json=build_import_template_config(
                ImportJob.ImportMode.ORGANIZATIONS_ONLY,
                phone_region=phone_region,
            ),
        )
        payload = normalize_import_row(
            raw_payload,
            ImportJob.ImportMode.ORGANIZATIONS_ONLY,
            phone_region=phone_region,
        )
        ImportRow.objects.create(
            import_job=job,
            row_number=1,
            normalized_payload_json=payload,
            match_result_json={
                "organization": {
                    "status": "EXACT",
                    "rule": "ORG_NUMBER",
                    "exact_id": organization.id,
                    "candidates": [],
                },
                "person": {
                    "status": "NONE",
                    "rule": None,
                    "exact_id": None,
                    "candidates": [],
                },
            },
            row_status=ImportRow.RowStatus.VALID,
            proposed_action=ImportRow.ProposedAction.UPDATE,
        )
        commit_import_job(job)

    def test_commit_valid_phone_preserves_raw_identity_and_publication(self):
        organization = Organization.objects.create(
            tenant=self.tenant,
            name="Existing",
            org_number="123456789",
            is_published=True,
            publish_phone=True,
        )
        self._commit_organization_payload(
            organization,
            {
                "organization_name": "Existing",
                "organization_org_number": "123456789",
                "organization_phone": "22 12 34 56",
            },
            phone_region="NO",
        )
        organization.refresh_from_db()
        self.assertEqual(organization.phone, "22 12 34 56")
        self.assertEqual(organization.phone_normalized, "+4722123456")
        self.assertEqual(organization.phone_normalization_region, "NO")
        self.assertTrue(organization.is_published)
        self.assertTrue(organization.publish_phone)

    def test_commit_keep_or_uncertain_phone_does_not_overwrite_existing_identity(self):
        for raw_phone, region in (("", "NO"), ("22 12 34 56", None), ("123", "NO")):
            organization = Organization.objects.create(
                tenant=self.tenant,
                name=f"Existing {raw_phone or 'blank'} {region}",
                org_number=str(900000000 + Organization.objects.count()),
                phone="+47 900 00 000",
                phone_normalized="+4790000000",
                is_published=True,
                publish_phone=True,
            )
            self._commit_organization_payload(
                organization,
                {
                    "organization_name": organization.name,
                    "organization_org_number": organization.org_number,
                    "organization_phone": raw_phone,
                },
                phone_region=region,
            )
            organization.refresh_from_db()
            self.assertEqual(organization.phone, "+47 900 00 000")
            self.assertEqual(organization.phone_normalized, "+4790000000")
            self.assertTrue(organization.publish_phone)

    def test_retry_normalization_is_idempotent_and_uses_job_snapshot_only(self):
        job_config = build_import_template_config(
            ImportJob.ImportMode.PEOPLE_ONLY,
            phone_region="SE",
        )
        raw = {"person_full_name": "Retry", "person_phone": "08-505 103 00"}
        first = normalize_import_row(
            raw,
            ImportJob.ImportMode.PEOPLE_ONLY,
            phone_region=job_config["phone_region"],
        )
        self.tenant.default_phone_region = "NO"
        self.tenant.save(update_fields=["default_phone_region"])
        second = normalize_import_row(
            raw,
            ImportJob.ImportMode.PEOPLE_ONLY,
            phone_region=job_config["phone_region"],
        )
        self.assertEqual(first, second)
        self.assertEqual(second["person"]["phone_normalization"]["e164"], "+46850510300")

    def test_accepted_ai_phone_never_guesses_missing_region(self):
        job = ImportJob.objects.create(
            tenant=self.tenant,
            created_by=self.user,
            source_type=ImportJob.SourceType.CSV,
            import_mode=ImportJob.ImportMode.PEOPLE_ONLY,
            status=ImportJob.Status.PREVIEW_READY,
            config_json=build_import_template_config(
                ImportJob.ImportMode.PEOPLE_ONLY,
                phone_region=None,
            ),
        )
        row = ImportRow.objects.create(
            import_job=job,
            row_number=1,
            normalized_payload_json=normalize_import_row(
                {"person_full_name": "AI Phone Review"},
                ImportJob.ImportMode.PEOPLE_ONLY,
                phone_region=None,
            ),
            match_result_json={
                "organization": {
                    "status": "NONE",
                    "rule": None,
                    "exact_id": None,
                    "candidates": [],
                },
                "person": {
                    "status": "NEW",
                    "rule": None,
                    "exact_id": None,
                    "candidates": [],
                },
            },
            row_status=ImportRow.RowStatus.VALID,
            proposed_action=ImportRow.ProposedAction.CREATE,
        )
        ImportDecision.objects.create(
            import_row=row,
            decision_type=ImportDecision.DecisionType.ACCEPT_AI_SUGGESTION,
            payload_json={
                "suggestion_key": "person_phone",
                "value": "22 12 34 56",
            },
            decided_by=self.user,
        )

        commit_import_job(job)

        person = Person.objects.get(tenant=self.tenant, full_name="AI Phone Review")
        self.assertIsNone(person.phone)
        self.assertFalse(person.contacts.filter(type="PHONE").exists())
