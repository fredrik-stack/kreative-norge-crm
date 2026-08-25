from __future__ import annotations

from dataclasses import FrozenInstanceError, fields

from django.test import SimpleTestCase

from crm.services.phone_normalization import (
    PhoneNormalizationReason,
    PhoneNormalizationResult,
    PhoneNormalizationStatus,
    normalize_phone,
)


class PhoneNormalizationTests(SimpleTestCase):
    def assert_valid(
        self,
        result: PhoneNormalizationResult,
        expected_e164: str,
        *,
        region_used: str | None,
    ) -> None:
        self.assertEqual(result.status, PhoneNormalizationStatus.VALID)
        self.assertEqual(result.e164, expected_e164)
        self.assertIsNone(result.reason_code)
        self.assertEqual(result.region_used, region_used)

    def assert_failure(
        self,
        result: PhoneNormalizationResult,
        status: PhoneNormalizationStatus,
        reason: PhoneNormalizationReason,
    ) -> None:
        self.assertEqual(result.status, status)
        self.assertEqual(result.reason_code, reason)
        self.assertIsNone(result.e164)

    def test_normalizes_norwegian_national_number_with_explicit_region(self):
        self.assert_valid(
            normalize_phone("900 12 345", "NO"),
            "+4790012345",
            region_used="NO",
        )

    def test_normalizes_region_case_and_surrounding_whitespace(self):
        self.assert_valid(
            normalize_phone("900 12 345", " no "),
            "+4790012345",
            region_used="NO",
        )

    def test_normalizes_swedish_national_number(self):
        self.assert_valid(
            normalize_phone("070-123 45 67", "SE"),
            "+46701234567",
            region_used="SE",
        )

    def test_normalizes_british_national_number(self):
        self.assert_valid(
            normalize_phone("020 8366 1177", "GB"),
            "+442083661177",
            region_used="GB",
        )

    def test_plus_number_does_not_require_region(self):
        self.assert_valid(
            normalize_phone("+47 900 12 345"),
            "+4790012345",
            region_used=None,
        )

    def test_plus_number_is_independent_of_caller_region(self):
        without_region = normalize_phone("+47 900 12 345")
        with_other_region = normalize_phone("+47 900 12 345", "SE")
        with_invalid_region = normalize_phone("+47 900 12 345", "not-a-region")

        self.assertEqual(with_other_region, without_region)
        self.assertEqual(with_invalid_region, without_region)

    def test_national_number_without_region_needs_region(self):
        self.assert_failure(
            normalize_phone("900 12 345"),
            PhoneNormalizationStatus.NEEDS_REGION,
            PhoneNormalizationReason.REGION_REQUIRED,
        )

    def test_double_zero_number_without_region_needs_region(self):
        self.assert_failure(
            normalize_phone("0047 900 12 345"),
            PhoneNormalizationStatus.NEEDS_REGION,
            PhoneNormalizationReason.REGION_REQUIRED,
        )

    def test_double_zero_number_uses_explicit_region_idd_rules(self):
        self.assert_valid(
            normalize_phone("0047 900 12 345", "NO"),
            "+4790012345",
            region_used="NO",
        )

    def test_empty_string_is_invalid(self):
        self.assert_failure(
            normalize_phone(""),
            PhoneNormalizationStatus.INVALID,
            PhoneNormalizationReason.EMPTY_INPUT,
        )

    def test_whitespace_only_is_invalid(self):
        self.assert_failure(
            normalize_phone("  \t\n"),
            PhoneNormalizationStatus.INVALID,
            PhoneNormalizationReason.EMPTY_INPUT,
        )

    def test_none_is_invalid(self):
        self.assert_failure(
            normalize_phone(None),
            PhoneNormalizationStatus.INVALID,
            PhoneNormalizationReason.EMPTY_INPUT,
        )

    def test_invalid_region_is_rejected(self):
        result = normalize_phone("900 12 345", "ZZ")

        self.assert_failure(
            result,
            PhoneNormalizationStatus.INVALID,
            PhoneNormalizationReason.INVALID_REGION,
        )
        self.assertIsNone(result.region_used)

    def test_empty_explicit_region_is_invalid(self):
        self.assert_failure(
            normalize_phone("900 12 345", ""),
            PhoneNormalizationStatus.INVALID,
            PhoneNormalizationReason.INVALID_REGION,
        )

    def test_unparseable_input_has_stable_parse_error(self):
        self.assert_failure(
            normalize_phone("not-a-phone", "NO"),
            PhoneNormalizationStatus.INVALID,
            PhoneNormalizationReason.PARSE_ERROR,
        )

    def test_impossible_number_is_distinguished(self):
        self.assert_failure(
            normalize_phone("12", "NO"),
            PhoneNormalizationStatus.INVALID,
            PhoneNormalizationReason.NOT_POSSIBLE,
        )

    def test_possible_but_invalid_number_is_distinguished(self):
        self.assert_failure(
            normalize_phone("+1 200 555 0123"),
            PhoneNormalizationStatus.INVALID,
            PhoneNormalizationReason.NOT_VALID,
        )

    def test_extension_is_rejected(self):
        self.assert_failure(
            normalize_phone("+47 900 12 345 ext. 7"),
            PhoneNormalizationStatus.INVALID,
            PhoneNormalizationReason.EXTENSION_NOT_SUPPORTED,
        )

    def test_e164_output_is_idempotent(self):
        first = normalize_phone("900 12 345", "NO")
        second = normalize_phone(first.e164)

        self.assertEqual(second, normalize_phone("+4790012345"))
        self.assert_valid(second, "+4790012345", region_used=None)

    def test_every_non_valid_result_has_no_e164_value(self):
        cases = (
            normalize_phone(None),
            normalize_phone("900 12 345"),
            normalize_phone("900 12 345", "ZZ"),
            normalize_phone("not-a-phone", "NO"),
            normalize_phone("12", "NO"),
            normalize_phone("+1 200 555 0123"),
            normalize_phone("+47 900 12 345 ext. 7"),
        )

        for result in cases:
            with self.subTest(result=result):
                self.assertNotEqual(result.status, PhoneNormalizationStatus.VALID)
                self.assertIsNone(result.e164)

    def test_reason_codes_are_stable_and_do_not_contain_raw_input(self):
        raw_value = "private-not-a-phone-123"
        first = normalize_phone(raw_value, "NO")
        second = normalize_phone(raw_value, "NO")

        self.assertEqual(first, second)
        self.assertIsInstance(first.reason_code, PhoneNormalizationReason)
        self.assertNotIn(raw_value, first.reason_code.value)
        self.assertEqual(
            {reason.value for reason in PhoneNormalizationReason},
            {
                "EMPTY_INPUT",
                "REGION_REQUIRED",
                "INVALID_REGION",
                "PARSE_ERROR",
                "NOT_POSSIBLE",
                "NOT_VALID",
                "EXTENSION_NOT_SUPPORTED",
            },
        )

    def test_typed_result_contract_is_exact_and_immutable(self):
        result = normalize_phone("+47 900 12 345")

        self.assertEqual(
            {status.value for status in PhoneNormalizationStatus},
            {"VALID", "INVALID", "NEEDS_REGION"},
        )
        self.assertEqual(
            [field.name for field in fields(PhoneNormalizationResult)],
            ["status", "e164", "reason_code", "region_used"],
        )
        with self.assertRaises(FrozenInstanceError):
            result.e164 = "+46123456789"
