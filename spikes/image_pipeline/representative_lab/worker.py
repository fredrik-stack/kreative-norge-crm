from __future__ import annotations

import argparse
from hashlib import sha256
from io import BytesIO
import json
import math
from pathlib import Path
import platform
import resource
import time
import warnings

from PIL import Image, ImageChops, ImageCms, ImageFilter, ImageOps, ImageStat, UnidentifiedImageError

from image_lab.core import VARIANTS, cover_crop_box


SAFETY_PIXEL_CEILING = 120_000_000
MAX_FILE_BYTES = 15 * 1024 * 1024
PIXEL_CANDIDATES = (20_000_000, 36_000_000, 50_000_000, 64_000_000, 100_000_000)
MIME_BY_FORMAT = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
    "TIFF": "image/tiff",
}
PRODUCTION_INPUT_FORMATS = {"JPEG", "PNG", "WEBP"}


class ControlledSourceError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def checksum(data: bytes) -> str:
    return sha256(data).hexdigest()


def peak_rss_mib() -> float:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    divisor = 1024 * 1024 if platform.system() == "Darwin" else 1024
    return round(value / divisor, 3)


def edge_variance(image: Image.Image) -> float:
    sample = image.convert("L")
    sample.thumbnail((512, 512), Image.Resampling.LANCZOS)
    edges = sample.filter(ImageFilter.FIND_EDGES)
    if edges.width > 4 and edges.height > 4:
        edges = edges.crop((2, 2, edges.width - 2, edges.height - 2))
    return round(float(ImageStat.Stat(edges).var[0]), 3)


def blockiness_indicator(image: Image.Image) -> float:
    """Return an advisory 8-pixel boundary discontinuity ratio."""

    sample = image.convert("L")
    sample.thumbnail((512, 512), Image.Resampling.LANCZOS)
    pixels = sample.load()
    boundary: list[int] = []
    interior: list[int] = []
    for y in range(sample.height):
        for x in range(1, sample.width):
            (boundary if x % 8 == 0 else interior).append(abs(pixels[x, y] - pixels[x - 1, y]))
    for y in range(1, sample.height):
        for x in range(sample.width):
            (boundary if y % 8 == 0 else interior).append(abs(pixels[x, y] - pixels[x, y - 1]))
    boundary_mean = sum(boundary) / len(boundary) if boundary else 0.0
    interior_mean = sum(interior) / len(interior) if interior else 0.0
    return round(boundary_mean / max(interior_mean, 0.001), 4)


def content_observation(image: Image.Image) -> dict[str, object]:
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    if alpha.getextrema()[0] < 255:
        box = alpha.getbbox()
        method = "alpha"
    else:
        background = Image.new("RGB", image.size, image.convert("RGB").getpixel((0, 0)))
        difference = ImageChops.difference(image.convert("RGB"), background).convert("L")
        box = difference.point(lambda value: 255 if value > 8 else 0).getbbox()
        method = "corner_background"
    total = image.width * image.height
    visible = 0 if box is None else (box[2] - box[0]) * (box[3] - box[1])
    return {
        "content_box": list(box) if box else None,
        "measurement_method": method,
        "internal_whitespace_ratio": round(1 - visible / total, 5) if total else 1.0,
    }


def standard_srgb_profile() -> tuple[ImageCms.ImageCmsProfile, bytes]:
    profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB"))
    return profile, profile.tobytes()


def normalize_color(image: Image.Image, icc_bytes: bytes | None) -> tuple[Image.Image, dict[str, object]]:
    srgb_profile, srgb_bytes = standard_srgb_profile()
    sample_points = ((0, 0), (max(0, image.width // 2), max(0, image.height // 2)))

    def raw_sample(point: tuple[int, int]) -> list[int]:
        value = image.getpixel(point)
        values = list(value) if isinstance(value, tuple) else [int(value)]
        return [int(channel) for channel in values]

    before_samples = [raw_sample(point) for point in sample_points]

    if not icc_bytes:
        converted = image.convert("RGB")
        if "A" in image.getbands():
            converted.putalpha(image.getchannel("A"))
        after_samples = [list(converted.getpixel(point)) for point in sample_points]
        return converted, {
            "status": "untagged",
            "assumption": "pixel values treated as sRGB for candidate review",
            "profile_name": None,
            "conversion_applied": False,
            "pixel_samples_before": before_samples,
            "pixel_samples_after": after_samples,
            "pixel_values_changed": before_samples != after_samples,
            "output_contract_candidates": ["converted_srgb_profile_free", "converted_srgb_with_standard_profile"],
            "standard_srgb_profile_checksum": checksum(srgb_bytes),
        }

    try:
        source_profile = ImageCms.ImageCmsProfile(BytesIO(icc_bytes))
        profile_name = ImageCms.getProfileName(source_profile).strip()
        description = ImageCms.getProfileDescription(source_profile).strip()
    except (OSError, TypeError, ValueError) as exc:
        raise ControlledSourceError("corrupt_icc_profile", f"ICC profile cannot be read: {exc}") from exc

    profile_text = f"{profile_name} {description}".lower()
    status = "embedded_srgb" if "srgb" in profile_text else "embedded_non_srgb"
    alpha = image.getchannel("A") if "A" in image.getbands() else None
    source_for_conversion = image.convert("RGB") if image.mode not in {"RGB", "CMYK", "LAB"} else image
    try:
        converted = ImageCms.profileToProfile(
            source_for_conversion,
            source_profile,
            srgb_profile,
            outputMode="RGB",
            renderingIntent=ImageCms.Intent.PERCEPTUAL,
        )
    except (OSError, TypeError, ValueError) as exc:
        raise ControlledSourceError("icc_conversion_failed", f"ICC conversion failed: {exc}") from exc
    if alpha is not None:
        converted.putalpha(alpha)
    after_samples = [list(converted.convert("RGB").getpixel(point)) for point in sample_points]
    return converted, {
        "status": status,
        "assumption": None,
        "profile_name": profile_name or description or "readable profile",
        "source_profile_checksum": checksum(icc_bytes),
        "conversion_applied": True,
        "pixel_samples_before": before_samples,
        "pixel_samples_after": after_samples,
        "pixel_values_changed": before_samples != after_samples,
        "output_contract_candidates": ["converted_srgb_profile_free", "converted_srgb_with_standard_profile"],
        "standard_srgb_profile_checksum": checksum(srgb_bytes),
    }


def encode(image: Image.Image, output_format: str, *, embed_srgb: bool) -> bytes:
    _, srgb_bytes = standard_srgb_profile()
    buffer = BytesIO()
    profile = srgb_bytes if embed_srgb else b""
    image = image.copy()
    image.info.clear()
    if output_format == "PNG":
        image.save(buffer, "PNG", compress_level=9, optimize=False, icc_profile=profile)
    elif output_format == "WEBP":
        has_alpha = "A" in image.getbands() and image.getchannel("A").getextrema()[0] < 255
        image.save(
            buffer,
            "WEBP",
            lossless=has_alpha,
            quality=82,
            method=6,
            exact=has_alpha,
            exif=b"",
            icc_profile=profile,
            xmp=b"",
        )
    else:
        image.convert("RGB").save(
            buffer,
            "JPEG",
            quality=85,
            subsampling=0,
            optimize=False,
            progressive=False,
            exif=b"",
            icc_profile=profile,
        )
    return buffer.getvalue()


def inspect_output(data: bytes) -> dict[str, object]:
    with Image.open(BytesIO(data)) as opened:
        opened.load()
        keys = sorted(str(key).lower() for key in opened.info)
        profile = opened.info.get("icc_profile")
        return {
            "format": opened.format,
            "mime": MIME_BY_FORMAT.get(str(opened.format).upper(), "application/octet-stream"),
            "dimensions": list(opened.size),
            "metadata_keys": keys,
            "has_alpha": (
                "A" in opened.getbands()
                and opened.convert("RGBA").getchannel("A").getextrema()[0] < 255
            ),
            "icc_profile_present": bool(profile),
            "icc_profile_checksum": checksum(profile) if isinstance(profile, bytes) else None,
        }


def render_variant(image: Image.Image, variant: str, fit: str) -> tuple[Image.Image | None, dict[str, object]]:
    target = VARIANTS[variant]
    if fit == "cover":
        crop = cover_crop_box(image.size, target, (0.5, 0.5))
        crop_size = (crop[2] - crop[0], crop[3] - crop[1])
        margin = min(crop_size[0] / target[0], crop_size[1] / target[1])
        observation = {
            "crop_box": list(crop),
            "crop_area_ratio": round(crop_size[0] * crop_size[1] / (image.width * image.height), 6),
            "scaling_margin": round(margin, 5),
            "can_render_without_upscale": margin >= 1,
        }
        if margin < 1:
            return None, observation
        return image.crop(crop).resize(target, Image.Resampling.LANCZOS), observation

    available = (round(target[0] * 0.84), round(target[1] * 0.84))
    scale = min(available[0] / image.width, available[1] / image.height, 1.0)
    resized_size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    resized = image.resize(resized_size, Image.Resampling.LANCZOS) if resized_size != image.size else image.copy()
    canvas = Image.new("RGBA", target, (0, 0, 0, 0))
    canvas.alpha_composite(resized.convert("RGBA"), ((target[0] - resized.width) // 2, (target[1] - resized.height) // 2))
    return canvas, {
        "crop_box": None,
        "crop_area_ratio": 1.0,
        "scaling_margin": round(min(image.width / max(1, resized.width), image.height / max(1, resized.height)), 5),
        "can_render_without_upscale": True,
        "effective_content_dimensions": list(resized.size),
    }


def write_preview(image: Image.Image, target: Path) -> dict[str, object]:
    preview = image.copy()
    preview.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
    data = encode(preview, "JPEG", embed_srgb=False)
    target.write_bytes(data)
    return {"relative_path": target.name, "checksum": checksum(data), "byte_size": len(data), **inspect_output(data)}


def analyze(payload: dict[str, object], output_root: Path) -> dict[str, object]:
    source_path = Path(str(payload["path"]))
    source_size = source_path.stat().st_size
    if source_size > MAX_FILE_BYTES:
        raise ControlledSourceError(
            "file_too_large",
            f"source has {source_size} bytes; approved configurable default is {MAX_FILE_BYTES}",
        )
    source_bytes = source_path.read_bytes()
    decode_started = time.perf_counter()
    try:
        with warnings.catch_warnings():
            # Candidate measurement reaches 100 MP. The isolated worker uses
            # its own lower safety ceiling without mutating Pillow's process
            # global Image.MAX_IMAGE_PIXELS value.
            warnings.simplefilter("ignore", Image.DecompressionBombWarning)
            with Image.open(BytesIO(source_bytes)) as opened:
                actual_format = str(opened.format or "UNKNOWN").upper()
                frame_count = int(getattr(opened, "n_frames", 1))
                original_size = opened.size
                pixels = opened.width * opened.height
                if pixels > SAFETY_PIXEL_CEILING:
                    raise ControlledSourceError(
                        "safety_pixel_ceiling",
                        f"declared image has {pixels} pixels; lab safety ceiling is {SAFETY_PIXEL_CEILING}",
                    )
                metadata_keys = sorted(str(key).lower() for key in opened.info)
                icc = opened.info.get("icc_profile")
                if icc is not None and not isinstance(icc, bytes):
                    raise ControlledSourceError("corrupt_icc_profile", "ICC profile is not byte data")
                exif = opened.getexif()
                orientation = int(exif.get(274)) if exif.get(274) else None
                opened.load()
                normalized = ImageOps.exif_transpose(opened).copy()
    except ControlledSourceError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ControlledSourceError("pixel_guard", str(exc)) from exc
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as exc:
        raise ControlledSourceError("decode_failed", str(exc)) from exc
    color_normalized, color = normalize_color(normalized, icc)
    expected_profile = payload.get("expected_color_profile")
    color["expected_profile"] = expected_profile
    expected_text = str(expected_profile or "").strip().lower()
    observed_text = f"{color.get('status', '')} {color.get('profile_name', '')}".lower()
    color["expectation_requires_review"] = (
        bool(expected_text)
        and expected_text not in {"unknown", "not_known"}
        and expected_text not in observed_text
    )
    color_normalized = color_normalized.convert("RGBA" if "A" in color_normalized.getbands() else "RGB")
    decode_ms = round((time.perf_counter() - decode_started) * 1000, 3)
    fixture_root = output_root / str(payload["fixture_id"])
    fixture_root.mkdir(parents=True, exist_ok=False)
    preview = write_preview(color_normalized, fixture_root / "original-preview.jpg")
    rendition_started = time.perf_counter()
    renditions: dict[str, object] = {}
    for variant in payload["expected_variants"]:
        rendered, suitability = render_variant(color_normalized, str(variant), str(payload["intended_fit"]))
        entry: dict[str, object] = {"suitability": suitability, "outputs": {}}
        if rendered is not None:
            output_format = (
                "PNG"
                if payload["category"] == "logo"
                else "JPEG"
                if variant == "share"
                else "WEBP"
            )
            suffix = {"PNG": "png", "JPEG": "jpg", "WEBP": "webp"}[output_format]
            entry["rendered_content_observation"] = content_observation(rendered)
            for contract, embed in (("profile_free", False), ("embedded_srgb", True)):
                data = encode(rendered, output_format, embed_srgb=embed)
                relative = f"{variant}-{contract}.{suffix}"
                (fixture_root / relative).write_bytes(data)
                entry["outputs"][contract] = {
                    "relative_path": relative,
                    "byte_size": len(data),
                    "checksum": checksum(data),
                    **inspect_output(data),
                }
        renditions[str(variant)] = entry
    rendition_ms = round((time.perf_counter() - rendition_started) * 1000, 3)
    has_alpha = "A" in color_normalized.getbands() and color_normalized.getchannel("A").getextrema()[0] < 255
    logo_observation = content_observation(color_normalized) if payload["category"] == "logo" else None

    return {
        "status": "success",
        "fixture_id": payload["fixture_id"],
        "category": payload["category"],
        "intended_fit": payload["intended_fit"],
        "rights_basis": payload["rights_basis"],
        "redistribution_allowed": payload["redistribution_allowed"],
        "contains_person": payload["contains_person"],
        "review_themes": payload["review_themes"],
        "notes": payload["notes"],
        "source": {
            "byte_size": len(source_bytes),
            "checksum": checksum(source_bytes),
            "format": actual_format,
            "mime": MIME_BY_FORMAT.get(actual_format, "application/octet-stream"),
            "frame_count": frame_count,
            "production_input_eligible": actual_format in PRODUCTION_INPUT_FORMATS and frame_count == 1,
            "production_input_note": (
                None
                if actual_format in PRODUCTION_INPUT_FORMATS and frame_count == 1
                else "accepted for lab evidence only; processing profile v1 input remains static JPEG/PNG/WebP"
            ),
            "original_dimensions": list(original_size),
            "normalized_dimensions": list(color_normalized.size),
            "pixel_count": math.prod(original_size),
            "aspect_ratio": round(color_normalized.width / color_normalized.height, 6),
            "color_mode": normalized.mode,
            "has_alpha": has_alpha,
            "exif_orientation": orientation,
            "icc_profile_present": icc is not None,
            "metadata_keys": metadata_keys,
        },
        "color_profile": color,
        "quality_measurements": {
            "edge_variance": edge_variance(color_normalized),
            "blockiness_indicator": blockiness_indicator(color_normalized),
            "classification": "advisory_measurements_only",
        },
        "logo_observation": logo_observation,
        "pixel_limit_candidates": {
            str(limit): {"would_reject": math.prod(original_size) > limit} for limit in PIXEL_CANDIDATES
        },
        "preview": preview,
        "renditions": renditions,
        "resource_usage": {
            "decode_and_normalize_ms": decode_ms,
            "rendition_ms": rendition_ms,
            "peak_rss_mib": peak_rss_mib(),
            "measurement_scope": "isolated_child_process",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--payload", required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    payload = json.loads(args.payload)
    try:
        result = analyze(payload, args.output_root.resolve())
    except ControlledSourceError as exc:
        result = {
            "status": "controlled_error",
            "fixture_id": payload.get("fixture_id"),
            "error": {"code": exc.code, "message": str(exc)},
            "resource_usage": {"peak_rss_mib": peak_rss_mib(), "measurement_scope": "isolated_child_process"},
        }
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
