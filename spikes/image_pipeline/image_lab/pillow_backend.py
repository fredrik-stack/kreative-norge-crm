from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import textwrap
import warnings

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps, ImageStat, UnidentifiedImageError

from .core import (
    MAX_FILE_BYTES,
    MAX_PIXELS,
    MIME_BY_FORMAT,
    PROCESSING_VERSION,
    VARIANTS,
    RenditionInfo,
    SourceInfo,
    SourceRejected,
    UpscaleRequired,
    checksum_bytes,
    cover_crop_box,
    detect_mime,
    immutable_rendition_key,
    normalize_focus,
)


SENSITIVE_METADATA_KEYS = {
    "comment",
    "exif",
    "icc_profile",
    "photoshop",
    "xml",
    "xmp",
}


@dataclass
class LoadedSource:
    info: SourceInfo
    image: Image.Image


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    return ImageFont.load_default(size=size)


def edge_variance(image: Image.Image) -> float:
    sample = image.convert("L")
    sample.thumbnail((512, 512), Image.Resampling.LANCZOS)
    edges = sample.filter(ImageFilter.FIND_EDGES)
    if edges.width > 4 and edges.height > 4:
        # FIND_EDGES produces an artificial high-contrast frame. Excluding it
        # keeps the score about image detail instead of canvas boundaries.
        edges = edges.crop((2, 2, edges.width - 2, edges.height - 2))
    return round(float(ImageStat.Stat(edges).var[0]), 3)


def inspect_source(
    path: Path,
    *,
    declared_mime: str | None,
    semantic_flags: tuple[str, ...] = (),
) -> LoadedSource:
    byte_size = path.stat().st_size
    if byte_size > MAX_FILE_BYTES:
        raise SourceRejected(
            "file_too_large",
            f"{byte_size} bytes exceeds the prototype limit of {MAX_FILE_BYTES}",
        )

    if "generic_platform_icon" in semantic_flags:
        raise SourceRejected(
            "blocked_platform_icon",
            "generic platform icons are policy-blocked before approval",
        )

    data = path.read_bytes()
    sniffed_format, sniffed_mime = detect_mime(data)
    if sniffed_format == "SVG":
        raise SourceRejected(
            "svg_not_allowed",
            "SVG is detected but deliberately rejected until a sandboxed rasterizer is selected",
        )
    if sniffed_format == "UNKNOWN":
        raise SourceRejected("unknown_bytes", "the bytes do not match an allowed raster format")
    if declared_mime and declared_mime.lower() != sniffed_mime:
        raise SourceRejected(
            "mime_mismatch",
            f"declared {declared_mime}, detected {sniffed_mime}",
        )

    original_max_pixels = Image.MAX_IMAGE_PIXELS
    Image.MAX_IMAGE_PIXELS = MAX_PIXELS
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            try:
                with Image.open(BytesIO(data)) as opened:
                    detected_format = (opened.format or "UNKNOWN").upper()
                    if detected_format != sniffed_format:
                        raise SourceRejected(
                            "decoder_format_mismatch",
                            f"byte sniffer returned {sniffed_format}, decoder returned {detected_format}",
                        )
                    if MIME_BY_FORMAT.get(detected_format) != sniffed_mime:
                        raise SourceRejected(
                            "decoder_mime_mismatch",
                            f"decoder format {detected_format} does not match {sniffed_mime}",
                        )

                    width, height = opened.size
                    if width <= 0 or height <= 0 or width * height > MAX_PIXELS:
                        raise SourceRejected(
                            "pixel_limit",
                            f"declared dimensions {width}x{height} exceed {MAX_PIXELS} pixels",
                        )

                    exif = opened.getexif()
                    orientation = int(exif.get(274)) if exif.get(274) else None
                    metadata_keys = set(str(key).lower() for key in opened.info)
                    if exif:
                        metadata_keys.add("exif")

                    opened.load()
                    normalized = ImageOps.exif_transpose(opened)
                    if "A" in normalized.getbands() or "transparency" in opened.info:
                        normalized = normalized.convert("RGBA")
                        alpha_min, alpha_max = normalized.getchannel("A").getextrema()
                        has_alpha = alpha_min < 255 or alpha_max < 255
                    else:
                        normalized = normalized.convert("RGB")
                        has_alpha = False
                    normalized = normalized.copy()
            except SourceRejected:
                raise
            except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
                raise SourceRejected("pixel_limit", str(exc)) from exc
            except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as exc:
                raise SourceRejected("decode_failed", str(exc)) from exc
    finally:
        Image.MAX_IMAGE_PIXELS = original_max_pixels

    info = SourceInfo(
        path=str(path),
        byte_size=byte_size,
        byte_checksum=checksum_bytes(data),
        detected_format=detected_format,
        detected_mime=sniffed_mime,
        width=width,
        height=height,
        normalized_width=normalized.width,
        normalized_height=normalized.height,
        has_alpha=has_alpha,
        exif_orientation=orientation,
        metadata_keys=tuple(sorted(metadata_keys)),
        edge_variance=edge_variance(normalized),
    )
    return LoadedSource(info=info, image=normalized)


def quality_observation(info: SourceInfo) -> dict[str, object]:
    minimum_side = min(info.normalized_width, info.normalized_height)
    if minimum_side < 160:
        dimension_status = "hard_fail_for_public_rendition"
    elif minimum_side < 512:
        dimension_status = "review"
    else:
        dimension_status = "pass"

    # Evidence-oriented bands only; the spike report does not make these final.
    if info.edge_variance < 5:
        sharpness_status = "hard_fail_candidate"
    elif info.edge_variance < 25:
        sharpness_status = "manual_review"
    elif info.edge_variance < 100:
        sharpness_status = "warning"
    else:
        sharpness_status = "pass"

    return {
        "dimension_status": dimension_status,
        "edge_variance": info.edge_variance,
        "sharpness_status": sharpness_status,
    }


def _contain(
    image: Image.Image,
    target_size: tuple[int, int],
    *,
    padding_ratio: float = 0.08,
) -> tuple[Image.Image, bool]:
    target_width, target_height = target_size
    padding_x = round(target_width * padding_ratio)
    padding_y = round(target_height * padding_ratio)
    available = (max(1, target_width - 2 * padding_x), max(1, target_height - 2 * padding_y))

    scale = min(available[0] / image.width, available[1] / image.height, 1.0)
    output_size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    resized = image.resize(output_size, Image.Resampling.LANCZOS) if output_size != image.size else image.copy()

    canvas = Image.new("RGBA", target_size, (0, 0, 0, 0))
    offset = ((target_width - resized.width) // 2, (target_height - resized.height) // 2)
    if "A" in resized.getbands():
        canvas.alpha_composite(resized.convert("RGBA"), dest=offset)
    else:
        canvas.paste(resized.convert("RGBA"), offset)
    return canvas, False


def _cover(
    image: Image.Image,
    target_size: tuple[int, int],
    *,
    focus: tuple[float, float],
) -> tuple[Image.Image, tuple[int, int, int, int], bool]:
    crop_box = cover_crop_box(image.size, target_size, focus)
    crop_width = crop_box[2] - crop_box[0]
    crop_height = crop_box[3] - crop_box[1]
    if crop_width < target_size[0] or crop_height < target_size[1]:
        raise UpscaleRequired(
            f"source crop {crop_width}x{crop_height} is smaller than target "
            f"{target_size[0]}x{target_size[1]}"
        )
    cropped = image.crop(crop_box)
    rendered = cropped.resize(target_size, Image.Resampling.LANCZOS)
    return rendered, crop_box, False


def render_image(
    image: Image.Image,
    *,
    variant: str,
    fit: str,
    focus: tuple[float, float] = (0.5, 0.5),
    padding_ratio: float = 0.08,
) -> tuple[Image.Image, tuple[int, int, int, int] | None, bool]:
    if variant not in VARIANTS:
        raise ValueError(f"unknown variant: {variant}")
    normalized_focus = normalize_focus(focus)
    if fit == "contain":
        rendered, upscaled = _contain(image, VARIANTS[variant], padding_ratio=padding_ratio)
        return rendered, None, upscaled
    if fit == "cover":
        return _cover(image, VARIANTS[variant], focus=normalized_focus)
    raise ValueError(f"unknown fit: {fit}")


def encode_image(image: Image.Image, output_format: str) -> bytes:
    output_format = output_format.upper()
    buffer = BytesIO()
    if output_format == "JPEG":
        image.convert("RGB").save(
            buffer,
            format="JPEG",
            quality=85,
            subsampling=0,
            optimize=False,
            progressive=False,
            exif=b"",
        )
    elif output_format == "PNG":
        image.convert("RGBA" if "A" in image.getbands() else "RGB").save(
            buffer,
            format="PNG",
            compress_level=9,
            optimize=False,
        )
    elif output_format == "WEBP":
        has_alpha = "A" in image.getbands()
        image.save(
            buffer,
            format="WEBP",
            lossless=has_alpha,
            quality=82,
            method=6,
            exact=has_alpha,
            exif=b"",
            icc_profile=b"",
            xmp=b"",
        )
    elif output_format == "AVIF":
        image.convert("RGBA" if "A" in image.getbands() else "RGB").save(
            buffer,
            format="AVIF",
            quality=55,
            speed=6,
            exif=b"",
            icc_profile=b"",
            xmp=b"",
        )
    else:
        raise ValueError(f"unsupported output format: {output_format}")
    return buffer.getvalue()


def inspect_encoded(data: bytes) -> tuple[tuple[str, ...], bool, tuple[int, int]]:
    with Image.open(BytesIO(data)) as rendered:
        rendered.load()
        metadata = tuple(sorted(str(key).lower() for key in rendered.info))
        has_alpha = "A" in rendered.getbands() or "transparency" in rendered.info
        return metadata, has_alpha, rendered.size


def create_rendition(
    source: LoadedSource,
    *,
    variant: str,
    fit: str,
    focus: tuple[float, float] = (0.5, 0.5),
    output_format: str,
    output_root: Path | None = None,
) -> tuple[RenditionInfo, bytes]:
    normalized_focus = normalize_focus(focus)
    rendered, crop_box, upscaled = render_image(
        source.image,
        variant=variant,
        fit=fit,
        focus=normalized_focus,
    )
    data = encode_image(rendered, output_format)
    metadata, has_alpha, size = inspect_encoded(data)
    immutable_key = immutable_rendition_key(
        source.info.byte_checksum,
        variant=variant,
        fit=fit,
        focus=normalized_focus,
        output_format=output_format,
    )
    if output_root is not None:
        target = output_root / immutable_key
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    info = RenditionInfo(
        variant=variant,
        fit=fit,
        focus_x=normalized_focus[0],
        focus_y=normalized_focus[1],
        width=size[0],
        height=size[1],
        output_format=output_format.upper(),
        byte_size=len(data),
        checksum=checksum_bytes(data),
        processing_version=PROCESSING_VERSION,
        immutable_key=immutable_key,
        crop_box=crop_box,
        upscaled=upscaled,
        metadata_keys=metadata,
        has_alpha=has_alpha,
    )
    return info, data


def _fallback_colors(seed_text: str) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    digest = sha256(seed_text.encode("utf-8")).digest()
    base = (20 + digest[0] % 42, 75 + digest[1] % 62, 60 + digest[2] % 70)
    accent = (170 + digest[3] % 70, 145 + digest[4] % 80, 55 + digest[5] % 90)
    return base, accent


def _fit_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    *,
    max_width: int,
    max_lines: int,
    initial_size: int,
) -> tuple[str, ImageFont.FreeTypeFont | ImageFont.ImageFont]:
    words = text.split()
    for size in range(initial_size, 19, -2):
        font = _font(size)
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            width = draw.textbbox((0, 0), candidate, font=font)[2]
            if current and width > max_width:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
        if len(lines) <= max_lines:
            return "\n".join(lines), font
    shortened = textwrap.shorten(text, width=42, placeholder="…")
    return shortened, _font(20)


def render_fallback(
    actor_name: str,
    category: str | None,
    *,
    variant: str,
    emergency: bool = False,
) -> Image.Image:
    width, height = VARIANTS[variant]
    label = "BILDE MANGLER" if emergency else actor_name.strip() or "Ukjent aktør"
    category_label = None if emergency else (category.strip() if category else None)
    background, accent = _fallback_colors("emergency" if emergency else f"{label}|{category_label}")

    image = Image.new("RGB", (width, height), background)
    draw = ImageDraw.Draw(image)
    stripe_width = max(18, width // 26)
    draw.rectangle((0, 0, stripe_width, height), fill=accent)
    draw.ellipse(
        (width - height // 2, -height // 4, width + height // 5, height // 2),
        fill=tuple(min(255, value + 24) for value in background),
    )

    margin = max(28, min(width, height) // 12)
    draw.text(
        (margin + stripe_width, margin),
        "KREATIVE NORGE",
        font=_font(max(20, min(width, height) // 18)),
        fill=(220, 248, 236),
    )
    text, font = _fit_text(
        draw,
        label,
        max_width=width - (margin * 2 + stripe_width),
        max_lines=3 if variant == "square" else 2,
        initial_size=max(30, min(width, height) // 8),
    )
    draw.multiline_text(
        (margin + stripe_width, height // 2),
        text,
        font=font,
        fill=(255, 255, 255),
        anchor="lm",
        spacing=max(4, font.size // 5 if hasattr(font, "size") else 5),
    )
    if category_label:
        draw.text(
            (margin + stripe_width, height - margin),
            category_label.upper(),
            font=_font(max(18, min(width, height) // 24)),
            fill=(245, 212, 130),
            anchor="ls",
        )
    return image


def write_static_emergency_fallbacks(output_root: Path) -> dict[str, dict[str, object]]:
    output_root.mkdir(parents=True, exist_ok=True)
    result: dict[str, dict[str, object]] = {}
    for variant in VARIANTS:
        data = encode_image(render_fallback("", None, variant=variant, emergency=True), "PNG")
        path = output_root / f"emergency-fallback-{variant}.png"
        path.write_bytes(data)
        result[variant] = {
            "path": str(path),
            "byte_size": len(data),
            "checksum": checksum_bytes(data),
        }
    return result


def format_capabilities() -> dict[str, dict[str, object]]:
    sample_rgb = Image.new("RGB", (96, 64), (20, 90, 70))
    sample_rgba = Image.new("RGBA", (96, 64), (20, 90, 70, 120))
    results: dict[str, dict[str, object]] = {}
    for output_format in ("JPEG", "PNG", "WEBP", "AVIF"):
        try:
            sample = sample_rgba if output_format in {"PNG", "WEBP", "AVIF"} else sample_rgb
            data = encode_image(sample, output_format)
            metadata, has_alpha, size = inspect_encoded(data)
            results[output_format] = {
                "available": True,
                "byte_size": len(data),
                "has_alpha": has_alpha,
                "metadata_keys": list(metadata),
                "size": list(size),
            }
        except Exception as exc:  # capability probe intentionally records failures
            results[output_format] = {"available": False, "error": str(exc)}
    return results


def sensitive_metadata(metadata_keys: tuple[str, ...]) -> set[str]:
    return set(metadata_keys) & SENSITIVE_METADATA_KEYS
