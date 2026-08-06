from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image, ImageCms, PngImagePlugin

from representative_lab.manifest import ManifestError, load_manifest
from representative_lab.runner import RunnerError, run


class RepresentativeLabTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.dataset = self.root / "dataset"
        self.files = self.dataset / "files"
        self.files.mkdir(parents=True)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def fixture(self, fixture_id: str, filename: str, **overrides):
        values = {
            "fixture_id": fixture_id,
            "filename": filename if filename.startswith("/") else f"files/{filename}",
            "category": "photo",
            "intended_fit": "cover",
            "expected_variants": ["square", "landscape", "share"],
            "rights_basis": "internal_test_only",
            "redistribution_allowed": False,
            "contains_person": False,
            "expected_color_profile": "unknown",
            "review_themes": ["crop", "color_shift", "sharpness", "compression"],
            "notes": "Synthetic fixture without identifying content.",
            "expected_result": "success",
        }
        values.update(overrides)
        return values

    def write_manifest(self, fixtures):
        (self.dataset / "manifest.json").write_text(
            json.dumps({"version": 1, "fixtures": fixtures}), encoding="utf-8"
        )

    def write_rgb(self, name="source.png", *, icc_profile=None, metadata=False):
        image = Image.new("RGB", (1210, 640), (31, 118, 77))
        for x in range(0, image.width, 40):
            for y in range(0, image.height, 40):
                image.putpixel((x, y), ((x * 3) % 255, (y * 5) % 255, 140))
        kwargs = {}
        if icc_profile is not None:
            kwargs["icc_profile"] = icc_profile
        if metadata:
            pnginfo = PngImagePlugin.PngInfo()
            pnginfo.add_text("comment", "sensitive synthetic metadata")
            kwargs["pnginfo"] = pnginfo
        path = self.files / name
        image.save(path, "PNG", **kwargs)
        return path

    def write_logo(self, name="logo.png"):
        image = Image.new("RGBA", (1000, 500), (0, 0, 0, 0))
        for x in range(300, 700):
            for y in range(180, 320):
                image.putpixel((x, y), (25, 100, 70, 255))
        path = self.files / name
        image.save(path, "PNG")
        return path

    def test_manifest_accepts_complete_contract(self):
        self.write_rgb()
        self.write_manifest([self.fixture("photo-001", "source.png")])
        manifest = load_manifest(self.dataset)
        self.assertEqual(manifest.fixtures[0].fixture_id, "photo-001")
        self.assertEqual(manifest.fixtures[0].expected_variants, ("square", "landscape", "share"))

    def test_manifest_rejects_traversal_absolute_missing_unknown_and_wrong_types(self):
        self.write_rgb()
        invalid = [
            (self.fixture("photo-001", "../outside.png"), "path traversal"),
            (self.fixture("photo-001", "/tmp/outside.png"), "relative"),
            (self.fixture("photo-001", "missing.png"), "missing"),
            (self.fixture("photo-001", "source.png", category="avatar"), "unknown value"),
            (self.fixture("photo-001", "source.png", intended_fit="stretch"), "unknown value"),
            (self.fixture("photo-001", "source.png", rights_basis="unknown"), "unknown value"),
            (self.fixture("photo-001", "source.png", redistribution_allowed="false"), "must be bool"),
            (self.fixture("photo-001", "source.png", contains_person=0), "must be bool"),
            ({**self.fixture("photo-001", "source.png"), "unexpected": True}, "unexpected fields"),
        ]
        for fixture, message in invalid:
            with self.subTest(message=message):
                self.write_manifest([fixture])
                with self.assertRaisesRegex(ManifestError, message):
                    load_manifest(self.dataset)
        (self.dataset / "manifest.json").write_text(
            json.dumps({"$schema": 42, "version": 1, "fixtures": [self.fixture("photo-001", "source.png")]}),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ManifestError, "manifest.\\$schema must be str"):
            load_manifest(self.dataset)

    def test_manifest_rejects_duplicate_fixture_and_file(self):
        self.write_rgb()
        cases = [
            [self.fixture("photo-001", "source.png"), self.fixture("photo-001", "source.png")],
            [self.fixture("photo-001", "source.png"), self.fixture("photo-002", "source.png")],
        ]
        for fixtures in cases:
            self.write_manifest(fixtures)
            with self.assertRaisesRegex(ManifestError, "duplicate"):
                load_manifest(self.dataset)

    def test_output_root_must_be_explicit_empty_and_outside_dataset(self):
        self.write_rgb()
        self.write_manifest([self.fixture("photo-001", "source.png")])
        with self.assertRaisesRegex(RunnerError, "separate trees"):
            run(self.dataset, self.dataset / "output", argv=[])
        occupied = self.root / "occupied"
        occupied.mkdir()
        (occupied / "keep.txt").write_text("keep", encoding="utf-8")
        with self.assertRaisesRegex(RunnerError, "empty"):
            run(self.dataset, occupied, argv=[])

    def test_runner_preserves_input_and_writes_complete_local_and_redacted_outputs(self):
        source = self.write_rgb(metadata=True)
        self.write_manifest([self.fixture("photo-001", "source.png")])
        before = sha256(source.read_bytes()).hexdigest()
        output = self.root / "output"
        summary = run(self.dataset, output, argv=["--synthetic-test"])
        self.assertEqual(summary["successful"], 1)
        self.assertFalse(summary["phase_3b1r_complete"])
        self.assertEqual(sha256(source.read_bytes()).hexdigest(), before)
        for name in (
            "evidence.json",
            "measurements.csv",
            "review-template.json",
            "review.csv",
            "review.html",
            "contact-sheet-local.jpg",
            "redacted-summary.json",
            "run-manifest.json",
        ):
            self.assertTrue((output / name).is_file(), name)
        evidence = json.loads((output / "evidence.json").read_text(encoding="utf-8"))
        fixture = evidence["fixtures"][0]
        profile_free = fixture["renditions"]["share"]["outputs"]["profile_free"]
        self.assertNotIn("comment", profile_free["metadata_keys"])
        self.assertNotIn("exif", profile_free["metadata_keys"])
        self.assertNotIn("icc_profile", profile_free["metadata_keys"])
        embedded = fixture["renditions"]["share"]["outputs"]["embedded_srgb"]
        self.assertTrue(embedded["icc_profile_present"])
        self.assertEqual(fixture["renditions"]["square"]["outputs"]["profile_free"]["format"], "WEBP")
        self.assertEqual(fixture["renditions"]["landscape"]["outputs"]["profile_free"]["format"], "WEBP")
        self.assertEqual(profile_free["format"], "JPEG")
        redacted_text = (output / "redacted-summary.json").read_text(encoding="utf-8")
        self.assertIn('"contains_image_bytes": false', redacted_text)
        self.assertNotIn("data:image", redacted_text)
        self.assertNotIn("original-preview", redacted_text)
        run_manifest = json.loads((output / "run-manifest.json").read_text(encoding="utf-8"))
        self.assertFalse(run_manifest["network_used"])
        self.assertFalse(run_manifest["output_policy"]["all_fixtures_allow_redistribution"])

    def test_untagged_and_srgb_sources_are_explicit_and_deterministic(self):
        untagged = self.write_rgb("untagged.png")
        srgb = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
        self.write_rgb("srgb.png", icc_profile=srgb)
        self.write_manifest(
            [self.fixture("untagged-001", untagged.name), self.fixture("srgb-001", "srgb.png")]
        )
        first = self.root / "first"
        second = self.root / "second"
        run(self.dataset, first, argv=[])
        run(self.dataset, second, argv=[])
        first_data = json.loads((first / "evidence.json").read_text(encoding="utf-8"))["fixtures"]
        second_data = json.loads((second / "evidence.json").read_text(encoding="utf-8"))["fixtures"]
        self.assertEqual(first_data[0]["color_profile"]["status"], "untagged")
        self.assertEqual(first_data[1]["color_profile"]["status"], "embedded_srgb")
        for index in range(2):
            self.assertEqual(
                first_data[index]["renditions"]["share"]["outputs"]["profile_free"]["checksum"],
                second_data[index]["renditions"]["share"]["outputs"]["profile_free"]["checksum"],
            )

    def test_valid_non_srgb_profile_converts_before_rendition_and_changes_control_pixels(self):
        lab_profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("LAB")).tobytes()
        image = Image.new("LAB", (1210, 640), (185, 75, 175))
        image.save(self.files / "lab-profile.tiff", "TIFF", icc_profile=lab_profile)
        self.write_manifest([self.fixture("non-srgb-001", "lab-profile.tiff")])
        output = self.root / "output"
        run(self.dataset, output, argv=[])
        fixture = json.loads((output / "evidence.json").read_text(encoding="utf-8"))["fixtures"][0]
        self.assertEqual(fixture["color_profile"]["status"], "embedded_non_srgb")
        self.assertTrue(fixture["color_profile"]["conversion_applied"])
        self.assertTrue(fixture["color_profile"]["pixel_values_changed"])
        self.assertFalse(fixture["source"]["production_input_eligible"])
        source_profile_checksum = fixture["color_profile"]["source_profile_checksum"]
        for output_contract in fixture["renditions"]["share"]["outputs"].values():
            self.assertNotEqual(output_contract["icc_profile_checksum"], source_profile_checksum)

    def test_corrupt_icc_is_controlled_only_when_manifest_expects_it(self):
        image = Image.new("RGB", (1210, 640), (100, 60, 30))
        image.save(self.files / "corrupt-icc.jpg", "JPEG", icc_profile=b"not-an-icc-profile")
        expected = self.fixture(
            "corrupt-icc-001",
            "corrupt-icc.jpg",
            expected_result="controlled_error",
            expected_variants=["share"],
        )
        self.write_manifest([expected])
        output = self.root / "expected"
        summary = run(self.dataset, output, argv=[])
        self.assertEqual(summary["controlled_errors"], 1)
        evidence = json.loads((output / "evidence.json").read_text(encoding="utf-8"))
        self.assertEqual(evidence["fixtures"][0]["error"]["code"], "corrupt_icc_profile")

        expected["expected_result"] = "success"
        self.write_manifest([expected])
        with self.assertRaisesRegex(RunnerError, "expected success"):
            run(self.dataset, self.root / "unexpected", argv=[])

    def test_crop_no_upscale_logo_whitespace_and_candidate_limits_are_measurements(self):
        self.write_rgb("small.png")
        # Re-save below the share dimensions so cover suitability is advisory false.
        Image.new("RGB", (400, 300), (50, 80, 110)).save(self.files / "small.png", "PNG")
        self.write_logo()
        self.write_manifest(
            [
                self.fixture("small-001", "small.png", expected_variants=["square", "share"]),
                self.fixture(
                    "logo-001",
                    "logo.png",
                    category="logo",
                    intended_fit="contain",
                    review_themes=["internal_whitespace", "logo_legibility"],
                ),
            ]
        )
        output = self.root / "output"
        run(self.dataset, output, argv=[])
        fixtures = json.loads((output / "evidence.json").read_text(encoding="utf-8"))["fixtures"]
        self.assertFalse(fixtures[0]["renditions"]["share"]["suitability"]["can_render_without_upscale"])
        self.assertEqual(fixtures[0]["renditions"]["share"]["outputs"], {})
        logo = fixtures[1]["logo_observation"]
        self.assertGreater(logo["internal_whitespace_ratio"], 0)
        self.assertNotIn("legible", logo)
        self.assertTrue(fixtures[1]["source"]["has_alpha"])
        self.assertTrue(
            fixtures[1]["renditions"]["square"]["outputs"]["profile_free"]["has_alpha"]
        )
        redacted = json.loads((output / "redacted-summary.json").read_text(encoding="utf-8"))
        self.assertEqual(set(redacted["pixel_limit_candidates"]), {"20000000", "36000000", "50000000", "64000000", "100000000"})
        candidate = redacted["pixel_limit_candidates"]["20000000"]
        self.assertIn("observed_affected_decode_ms", candidate)
        self.assertIn("observed_affected_rendition_ms", candidate)
        self.assertIn("observed_affected_peak_rss_mib", candidate)

    def test_harness_has_no_network_or_crm_runtime_dependency(self):
        repo_root = Path(__file__).resolve().parents[3]
        harness_paths = [
            repo_root / "spikes/image_pipeline/representative_lab",
            repo_root / "spikes/image_pipeline/run_representative_lab.py",
        ]
        forbidden_network = ("requests", "urllib", "http.client", "socket", "brave")
        for root in harness_paths:
            paths = [root] if root.is_file() else list(root.rglob("*.py"))
            for path in paths:
                content = path.read_text(encoding="utf-8").lower()
                self.assertFalse(any(token in content for token in forbidden_network), path)
        forbidden_runtime = ("representative_lab", "run_representative_lab")
        for production_root in (repo_root / "crm", repo_root / "config"):
            for path in production_root.rglob("*.py"):
                content = path.read_text(encoding="utf-8")
                self.assertFalse(any(token in content for token in forbidden_runtime), path)
        root_requirements = (repo_root / "requirements.txt").read_text(encoding="utf-8").lower()
        self.assertNotIn("pillow", root_requirements)
        self.assertNotIn("pyvips", root_requirements)


if __name__ == "__main__":
    unittest.main()
