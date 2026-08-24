from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from PIL import Image

from image_lab.core import (
    MAX_PIXELS,
    VARIANTS,
    SourceRejected,
    UpscaleRequired,
    cover_crop_box,
    safe_declared_pixel_bomb,
)
from image_lab.fixtures import generate_fixtures
from image_lab.pillow_backend import (
    create_rendition,
    format_capabilities,
    inspect_source,
    render_fallback,
    render_image,
    sensitive_metadata,
    write_static_emergency_fallbacks,
)


class ImageLabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary_directory = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary_directory.name)
        cls.specs = {spec.name: spec for spec in generate_fixtures(cls.root)}

    @classmethod
    def tearDownClass(cls):
        cls.temporary_directory.cleanup()

    def load(self, name: str):
        spec = self.specs[name]
        return inspect_source(
            spec.path(self.root),
            declared_mime=spec.declared_mime,
            semantic_flags=spec.semantic_flags,
        )

    def rejection_code(self, name: str) -> str:
        spec = self.specs[name]
        with self.assertRaises(SourceRejected) as context:
            inspect_source(
                spec.path(self.root),
                declared_mime=spec.declared_mime,
                semantic_flags=spec.semantic_flags,
            )
        return context.exception.code

    def test_fixture_matrix_is_complete_and_synthetic(self):
        self.assertEqual(len(self.specs), 20)
        required = {
            "square_transparent_logo",
            "wide_logo",
            "tall_logo",
            "small_text_logo",
            "landscape_photo",
            "portrait_photo",
            "exif_orientation",
            "metadata_photo",
            "small_image",
            "very_wide",
            "very_tall",
            "blurry",
            "strongly_compressed",
            "corrupt",
            "mime_mismatch",
            "pixel_bomb",
            "generic_platform_icon",
            "alpha_png",
            "jpeg_without_alpha",
            "synthetic_svg",
        }
        self.assertEqual(set(self.specs), required)

    def test_corrupt_mime_mismatch_pixel_bomb_and_policy_are_rejected(self):
        self.assertEqual(self.rejection_code("corrupt"), "decode_failed")
        self.assertEqual(self.rejection_code("mime_mismatch"), "mime_mismatch")
        self.assertEqual(self.rejection_code("pixel_bomb"), "pixel_limit")
        self.assertEqual(self.rejection_code("generic_platform_icon"), "blocked_platform_icon")
        self.assertEqual(self.rejection_code("synthetic_svg"), "svg_not_allowed")

    def test_pixel_limit_is_bounded_well_below_fixture_declaration(self):
        self.assertLessEqual(MAX_PIXELS, 20_000_000)
        self.assertLess(self.specs["pixel_bomb"].path(self.root).stat().st_size, 1024)

        just_over_limit = self.root / "just-over-pixel-limit.png"
        just_over_limit.write_bytes(safe_declared_pixel_bomb(5000, 4001))
        with self.assertRaises(SourceRejected) as context:
            inspect_source(just_over_limit, declared_mime="image/png")
        self.assertEqual(context.exception.code, "pixel_limit")

    def test_exif_orientation_is_applied_before_rendering(self):
        source = self.load("exif_orientation")
        self.assertEqual(source.info.exif_orientation, 6)
        self.assertEqual((source.info.width, source.info.height), (1800, 1200))
        self.assertEqual((source.info.normalized_width, source.info.normalized_height), (1200, 1800))

    def test_public_rendition_strips_sensitive_metadata(self):
        source = self.load("metadata_photo")
        self.assertIn("exif", source.info.metadata_keys)
        info, _ = create_rendition(
            source,
            variant="landscape",
            fit="cover",
            output_format="JPEG",
        )
        self.assertEqual(sensitive_metadata(info.metadata_keys), set())

    def test_transparent_logo_is_contained_without_cutting_or_upscale(self):
        source = self.load("wide_logo")
        rendered, crop_box, upscaled = render_image(
            source.image,
            variant="landscape",
            fit="contain",
        )
        self.assertEqual(rendered.size, VARIANTS["landscape"])
        self.assertIsNone(crop_box)
        self.assertFalse(upscaled)
        alpha_box = rendered.getchannel("A").getbbox()
        self.assertIsNotNone(alpha_box)
        self.assertGreater(alpha_box[0], 0)
        self.assertGreater(alpha_box[1], 0)
        self.assertLess(alpha_box[2], rendered.width)
        self.assertLess(alpha_box[3], rendered.height)

    def test_tall_logo_is_not_cropped_in_any_variant(self):
        source = self.load("tall_logo")
        for variant, expected_size in VARIANTS.items():
            with self.subTest(variant=variant):
                rendered, crop_box, upscaled = render_image(
                    source.image,
                    variant=variant,
                    fit="contain",
                )
                self.assertEqual(rendered.size, expected_size)
                self.assertIsNone(crop_box)
                self.assertFalse(upscaled)
                self.assertIsNotNone(rendered.getchannel("A").getbbox())

    def test_photo_cover_uses_normalized_focus_without_stretching(self):
        source = self.load("landscape_photo")
        centered, _ = create_rendition(
            source,
            variant="square",
            fit="cover",
            focus=(0.5, 0.5),
            output_format="JPEG",
        )
        shifted, _ = create_rendition(
            source,
            variant="square",
            fit="cover",
            focus=(0.82, 0.44),
            output_format="JPEG",
        )
        self.assertEqual((centered.width, centered.height), VARIANTS["square"])
        self.assertNotEqual(centered.checksum, shifted.checksum)
        self.assertNotEqual(centered.crop_box, shifted.crop_box)
        crop = shifted.crop_box
        self.assertIsNotNone(crop)
        crop_ratio = (crop[2] - crop[0]) / (crop[3] - crop[1])
        self.assertAlmostEqual(crop_ratio, 1.0, places=3)

    def test_cover_crop_contract_preserves_target_aspect(self):
        for target in VARIANTS.values():
            crop = cover_crop_box((2400, 1600), target, (0.77, 0.33))
            ratio = (crop[2] - crop[0]) / (crop[3] - crop[1])
            self.assertAlmostEqual(ratio, target[0] / target[1], places=3)

    def test_small_image_is_never_automatically_upscaled(self):
        source = self.load("small_image")
        with self.assertRaises(UpscaleRequired):
            create_rendition(
                source,
                variant="square",
                fit="cover",
                output_format="JPEG",
            )
        contained, _, upscaled = render_image(source.image, variant="square", fit="contain")
        self.assertFalse(upscaled)
        alpha_box = contained.getchannel("A").getbbox()
        self.assertLessEqual(alpha_box[2] - alpha_box[0], source.info.normalized_width)
        self.assertLessEqual(alpha_box[3] - alpha_box[1], source.info.normalized_height)

    def test_all_required_variants_are_exact(self):
        source = self.load("landscape_photo")
        for variant, expected_size in VARIANTS.items():
            with self.subTest(variant=variant):
                info, _ = create_rendition(
                    source,
                    variant=variant,
                    fit="cover",
                    output_format="JPEG",
                )
                self.assertEqual((info.width, info.height), expected_size)
                self.assertFalse(info.upscaled)

    def test_fallback_is_deterministic_and_has_static_emergency_variants(self):
        for variant, expected_size in VARIANTS.items():
            first = render_fallback("Arktisk Kulturverksted", "Scenekunst", variant=variant)
            second = render_fallback("Arktisk Kulturverksted", "Scenekunst", variant=variant)
            self.assertEqual(first.size, expected_size)
            self.assertEqual(first.tobytes(), second.tobytes())
        result = write_static_emergency_fallbacks(self.root / "static")
        self.assertEqual(set(result), set(VARIANTS))
        for values in result.values():
            path = Path(str(values["path"]))
            self.assertTrue(path.exists())
            with Image.open(path) as image:
                self.assertIn(image.size, VARIANTS.values())

    def test_same_input_and_config_is_byte_identical_three_times(self):
        source = self.load("landscape_photo")
        runs = [
            create_rendition(
                source,
                variant="share",
                fit="cover",
                focus=(0.72, 0.44),
                output_format="JPEG",
            )[0]
            for _ in range(3)
        ]
        self.assertEqual(len({item.checksum for item in runs}), 1)
        self.assertEqual(len({item.byte_size for item in runs}), 1)
        self.assertEqual(len({item.metadata_keys for item in runs}), 1)

    def test_sharpness_measure_distinguishes_synthetic_blur(self):
        sharp = self.load("landscape_photo")
        blurry = self.load("blurry")
        self.assertLess(blurry.info.edge_variance, sharp.info.edge_variance)

    def test_pillow_probes_required_formats_without_mandating_avif(self):
        capabilities = format_capabilities()
        for output_format in ("JPEG", "PNG", "WEBP"):
            self.assertTrue(capabilities[output_format]["available"])
        self.assertIn("AVIF", capabilities)

    def test_pyvips_runs_equivalent_cover_and_contain(self):
        from image_lab.pyvips_backend import render_file, versions

        version_info = versions()
        self.assertIn("libvips", version_info)
        photo = render_file(
            self.specs["landscape_photo"].path(self.root),
            variant="share",
            fit="cover",
            focus=(0.72, 0.44),
            output_format="JPEG",
        )
        logo = render_file(
            self.specs["wide_logo"].path(self.root),
            variant="landscape",
            fit="contain",
            output_format="PNG",
        )
        self.assertEqual((photo["width"], photo["height"]), VARIANTS["share"])
        self.assertEqual((logo["width"], logo["height"]), VARIANTS["landscape"])

    def test_spike_is_not_wired_into_django_runtime(self):
        resolved = Path(__file__).resolve()
        repo_root = next(
            (
                parent
                for parent in resolved.parents
                if (parent / "crm").is_dir() and (parent / "config").is_dir()
            ),
            None,
        )
        if repo_root is None:
            # The dedicated lab image intentionally copies no CRM runtime.
            self.assertFalse(Path("/lab/crm").exists())
            self.assertFalse(Path("/lab/config").exists())
            return
        production_paths = [repo_root / "crm", repo_root / "config"]
        forbidden = ("spikes.image_pipeline", "image_lab")
        occurrences = []
        for production_path in production_paths:
            for path in production_path.rglob("*.py"):
                content = path.read_text(encoding="utf-8")
                if any(token in content for token in forbidden):
                    occurrences.append(str(path.relative_to(repo_root)))
        self.assertEqual(occurrences, [])
        requirements = (repo_root / "requirements.txt").read_text(encoding="utf-8").lower()
        # Production has its own Pillow-based 3C processing runtime. The spike
        # boundary is that no spike module or its pyvips dependency leaks in.
        self.assertNotIn("pyvips", requirements)


if __name__ == "__main__":
    unittest.main()
