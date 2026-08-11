from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256
from io import BytesIO
import math
import warnings

from PIL import Image, ImageCms, ImageOps, UnidentifiedImageError


MAX_SOURCE_BYTES = 15 * 1024 * 1024
MAX_SOURCE_PIXELS = 36_000_000
MIN_COVER_ZOOM = 1.0
MAX_COVER_ZOOM = 3.0
PROCESSING_PROFILE = "phase3c-pillow-v1"
VALIDATION_VERSION = "phase3c-validation-v1"

SOURCE_MIME_TYPES = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}
SOURCE_FORMATS = {key: key.lower() for key in SOURCE_MIME_TYPES}
SOURCE_EXTENSIONS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}
VARIANT_SIZES = {
    "square": (512, 512),
    "landscape": (800, 450),
    "share": (1200, 630),
}


class ImageProcessingError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class ProcessedSource:
    original_bytes: bytes
    checksum_sha256: str
    original_format: str
    mime_type: str
    extension: str
    width: int
    height: int
    color_status: str
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class ProcessedRendition:
    variant: str
    output_format: str
    mime_type: str
    extension: str
    width: int
    height: int
    encoded_bytes: bytes
    checksum_sha256: str


@dataclass(frozen=True)
class ProcessedImage:
    source: ProcessedSource
    renditions: tuple[ProcessedRendition, ...]
    fit_mode: str
    focus_x: float
    focus_y: float
    zoom: float
    processing_version: str


def checksum_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


def read_upload_bounded(upload) -> bytes:
    if not hasattr(upload, "read"):
        raise ImageProcessingError("invalid_upload", "Upload must be a readable file-like object.")

    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = upload.read(min(64 * 1024, MAX_SOURCE_BYTES + 1 - total))
        if not chunk:
            break
        if not isinstance(chunk, bytes):
            raise ImageProcessingError("invalid_upload", "Upload must return bytes.")
        chunks.append(chunk)
        total += len(chunk)
        if total > MAX_SOURCE_BYTES:
            raise ImageProcessingError(
                "file_too_large",
                f"Image exceeds the {MAX_SOURCE_BYTES}-byte source limit.",
            )
    if total == 0:
        raise ImageProcessingError("empty_upload", "Image upload is empty.")
    return b"".join(chunks)


def _sniff_format(data: bytes) -> tuple[str, str]:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG", "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "JPEG", "image/jpeg"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "WEBP", "image/webp"
    raise ImageProcessingError(
        "unsupported_format",
        "Only static JPEG, PNG, and WebP images are supported.",
    )


def normalize_focus(
    fit_mode: str,
    focus_x: float | None,
    focus_y: float | None,
) -> tuple[float, float, tuple[str, ...]]:
    if fit_mode not in {"contain", "cover"}:
        raise ImageProcessingError("invalid_fit", "Fit mode must be contain or cover.")
    if fit_mode == "contain":
        if focus_x is not None or focus_y is not None:
            raise ImageProcessingError("invalid_focus", "Contain processing does not accept focus.")
        return 0.5, 0.5, ()
    if focus_x is None and focus_y is None:
        return 0.5, 0.5, ()
    if focus_x is None or focus_y is None:
        raise ImageProcessingError(
            "invalid_focus",
            "Cover focus must provide both focus_x and focus_y.",
        )
    try:
        x = float(focus_x)
        y = float(focus_y)
    except (TypeError, ValueError) as error:
        raise ImageProcessingError("invalid_focus", "Focus values must be numeric.") from error
    if not math.isfinite(x) or not math.isfinite(y) or not 0.0 <= x <= 1.0 or not 0.0 <= y <= 1.0:
        raise ImageProcessingError(
            "invalid_focus",
            "Focus values must be normalized between 0 and 1.",
        )
    quantum = Decimal("0.0001")
    return (
        float(Decimal(str(x)).quantize(quantum)),
        float(Decimal(str(y)).quantize(quantum)),
        (),
    )


def normalize_zoom(fit_mode: str, zoom: float | None) -> float:
    if fit_mode not in {"contain", "cover"}:
        raise ImageProcessingError("invalid_fit", "Fit mode must be contain or cover.")
    if fit_mode == "contain":
        if zoom is not None:
            raise ImageProcessingError("invalid_zoom", "Contain processing does not accept zoom.")
        return MIN_COVER_ZOOM
    if zoom is None:
        return MIN_COVER_ZOOM
    try:
        value = float(zoom)
    except (TypeError, ValueError) as error:
        raise ImageProcessingError("invalid_zoom", "Zoom must be numeric.") from error
    if not math.isfinite(value) or not MIN_COVER_ZOOM <= value <= MAX_COVER_ZOOM:
        raise ImageProcessingError(
            "invalid_zoom",
            f"Zoom must be between {MIN_COVER_ZOOM} and {MAX_COVER_ZOOM}.",
        )
    return float(Decimal(str(value)).quantize(Decimal("0.0001")))


def _normalize_color(image: Image.Image, icc_bytes: bytes | None) -> tuple[Image.Image, str]:
    if "A" in image.getbands():
        alpha = image.getchannel("A")
    elif "transparency" in image.info:
        alpha = image.convert("RGBA").getchannel("A")
    else:
        alpha = None
    if not icc_bytes:
        normalized = image.convert("RGB")
        if alpha is not None:
            normalized.putalpha(alpha)
        return normalized, "untagged_assumed_srgb"

    try:
        source_profile = ImageCms.ImageCmsProfile(BytesIO(icc_bytes))
        target_profile = ImageCms.createProfile("sRGB")
        profile_text = " ".join(
            (
                ImageCms.getProfileName(source_profile).strip(),
                ImageCms.getProfileDescription(source_profile).strip(),
            )
        ).lower()
    except (ImageCms.PyCMSError, OSError, TypeError, ValueError) as error:
        raise ImageProcessingError(
            "corrupt_icc_profile",
            "Embedded ICC profile cannot be read.",
        ) from error

    source_image = image if image.mode in {"RGB", "CMYK", "LAB"} else image.convert("RGB")
    try:
        normalized = ImageCms.profileToProfile(
            source_image,
            source_profile,
            target_profile,
            outputMode="RGB",
            renderingIntent=ImageCms.Intent.PERCEPTUAL,
        )
    except (ImageCms.PyCMSError, OSError, TypeError, ValueError) as error:
        raise ImageProcessingError(
            "icc_conversion_failed",
            "Embedded ICC profile cannot be converted to sRGB.",
        ) from error
    if alpha is not None:
        normalized.putalpha(alpha)
    status = "embedded_srgb" if "srgb" in profile_text else "embedded_non_srgb"
    return normalized, status


def _cover_crop_box(
    source_size: tuple[int, int],
    target_size: tuple[int, int],
    focus: tuple[float, float],
    zoom: float = MIN_COVER_ZOOM,
) -> tuple[int, int, int, int]:
    source_width, source_height = source_size
    target_width, target_height = target_size
    source_ratio = source_width / source_height
    target_ratio = target_width / target_height
    if source_ratio > target_ratio:
        crop_height = max(1, round(source_height / zoom))
        crop_width = max(1, round(crop_height * target_ratio))
    else:
        crop_width = max(1, round(source_width / zoom))
        crop_height = max(1, round(crop_width / target_ratio))
    left = min(max(0, round(focus[0] * source_width - crop_width / 2)), source_width - crop_width)
    top = min(max(0, round(focus[1] * source_height - crop_height / 2)), source_height - crop_height)
    return left, top, left + crop_width, top + crop_height


def _render_contain(image: Image.Image, target: tuple[int, int]) -> Image.Image:
    available = (round(target[0] * 0.84), round(target[1] * 0.84))
    scale = min(available[0] / image.width, available[1] / image.height, 1.0)
    size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    resized = image.resize(size, Image.Resampling.LANCZOS) if size != image.size else image.copy()
    canvas = Image.new("RGBA", target, (0, 0, 0, 0))
    offset = ((target[0] - resized.width) // 2, (target[1] - resized.height) // 2)
    canvas.alpha_composite(resized.convert("RGBA"), offset)
    return canvas


def _render_cover(
    image: Image.Image,
    target: tuple[int, int],
    focus: tuple[float, float],
    zoom: float,
) -> Image.Image:
    crop = _cover_crop_box(image.size, target, focus, zoom)
    crop_width = crop[2] - crop[0]
    crop_height = crop[3] - crop[1]
    if crop_width < target[0] or crop_height < target[1]:
        raise ImageProcessingError(
            "upscale_required",
            f"Source crop {crop_width}x{crop_height} cannot produce {target[0]}x{target[1]} without upscaling.",
        )
    return image.crop(crop).resize(target, Image.Resampling.LANCZOS)


def _encode(image: Image.Image, output_format: str) -> bytes:
    clean = image.copy()
    clean.info.clear()
    buffer = BytesIO()
    if output_format == "png":
        clean.convert("RGBA" if "A" in clean.getbands() else "RGB").save(
            buffer,
            "PNG",
            compress_level=9,
            optimize=False,
        )
    elif output_format == "webp":
        clean.save(
            buffer,
            "WEBP",
            quality=82,
            method=6,
            exact="A" in clean.getbands(),
            exif=b"",
            icc_profile=b"",
            xmp=b"",
        )
    elif output_format == "jpeg":
        if "A" in clean.getbands():
            background = Image.new("RGB", clean.size, (255, 255, 255))
            background.paste(clean.convert("RGBA"), mask=clean.convert("RGBA").getchannel("A"))
            clean = background
        clean.convert("RGB").save(
            buffer,
            "JPEG",
            quality=85,
            subsampling=0,
            optimize=False,
            progressive=False,
            exif=b"",
            icc_profile=b"",
        )
    else:
        raise ImageProcessingError("invalid_output_format", "Unsupported rendition output format.")
    return buffer.getvalue()


def process_uploaded_image(
    upload,
    *,
    fit_mode: str,
    focus_x: float | None = None,
    focus_y: float | None = None,
    zoom: float | None = None,
) -> ProcessedImage:
    original_bytes = read_upload_bounded(upload)
    source_checksum = checksum_bytes(original_bytes)
    sniffed_format, sniffed_mime = _sniff_format(original_bytes)
    declared_mime = str(getattr(upload, "content_type", "") or "").split(";", 1)[0].strip().lower()
    if declared_mime and declared_mime != sniffed_mime:
        raise ImageProcessingError(
            "mime_mismatch",
            f"Declared MIME type {declared_mime} does not match detected {sniffed_mime}.",
        )
    normalized_focus_x, normalized_focus_y, focus_warnings = normalize_focus(
        fit_mode,
        focus_x,
        focus_y,
    )
    normalized_zoom = normalize_zoom(fit_mode, zoom)

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(original_bytes)) as opened:
                decoded_format = str(opened.format or "").upper()
                if decoded_format != sniffed_format:
                    raise ImageProcessingError(
                        "decoder_format_mismatch",
                        "Decoded image format does not match the byte signature.",
                    )
                width, height = opened.size
                if width <= 0 or height <= 0 or width * height > MAX_SOURCE_PIXELS:
                    raise ImageProcessingError(
                        "pixel_limit",
                        f"Image dimensions exceed the {MAX_SOURCE_PIXELS}-pixel source limit.",
                    )
                if int(getattr(opened, "n_frames", 1)) != 1 or bool(getattr(opened, "is_animated", False)):
                    raise ImageProcessingError(
                        "animated_not_supported",
                        "Animated or multiframe images are not supported.",
                    )
                icc_bytes = opened.info.get("icc_profile")
                if icc_bytes is not None and not isinstance(icc_bytes, bytes):
                    raise ImageProcessingError("corrupt_icc_profile", "Embedded ICC profile is invalid.")
                opened.load()
                oriented = ImageOps.exif_transpose(opened).copy()
                width, height = oriented.size
    except ImageProcessingError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        raise ImageProcessingError("pixel_limit", "Image exceeds the safe decode limit.") from error
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as error:
        raise ImageProcessingError("decode_failed", "Image cannot be decoded completely.") from error

    normalized, color_status = _normalize_color(oriented, icc_bytes)
    processing_warnings = list(focus_warnings)
    if color_status == "untagged_assumed_srgb":
        processing_warnings.append("untagged_assumed_srgb")

    renditions: list[ProcessedRendition] = []
    for variant, target in VARIANT_SIZES.items():
        rendered = (
            _render_contain(normalized, target)
            if fit_mode == "contain"
            else _render_cover(
                normalized,
                target,
                (normalized_focus_x, normalized_focus_y),
                normalized_zoom,
            )
        )
        output_format = "png" if fit_mode == "contain" else "jpeg" if variant == "share" else "webp"
        encoded = _encode(rendered, output_format)
        renditions.append(
            ProcessedRendition(
                variant=variant,
                output_format=output_format,
                mime_type={"png": "image/png", "jpeg": "image/jpeg", "webp": "image/webp"}[output_format],
                extension={"png": "png", "jpeg": "jpg", "webp": "webp"}[output_format],
                width=target[0],
                height=target[1],
                encoded_bytes=encoded,
                checksum_sha256=checksum_bytes(encoded),
            )
        )

    return ProcessedImage(
        source=ProcessedSource(
            original_bytes=original_bytes,
            checksum_sha256=source_checksum,
            original_format=SOURCE_FORMATS[sniffed_format],
            mime_type=sniffed_mime,
            extension=SOURCE_EXTENSIONS[sniffed_format],
            width=width,
            height=height,
            color_status=color_status,
            warnings=tuple(processing_warnings),
        ),
        renditions=tuple(renditions),
        fit_mode=fit_mode,
        focus_x=normalized_focus_x,
        focus_y=normalized_focus_y,
        zoom=normalized_zoom,
        processing_version=PROCESSING_PROFILE,
    )
