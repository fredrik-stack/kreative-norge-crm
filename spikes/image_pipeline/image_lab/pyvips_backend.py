from __future__ import annotations

from pathlib import Path

from .core import UpscaleRequired, VARIANTS, checksum_bytes, cover_crop_box, normalize_focus


def _pyvips():
    import pyvips

    return pyvips


def versions() -> dict[str, object]:
    pyvips = _pyvips()
    return {
        "pyvips": pyvips.__version__,
        "libvips": ".".join(str(pyvips.version(index)) for index in range(3)),
        "suffixes": sorted(pyvips.get_suffixes()),
    }


def load_image(path: Path):
    pyvips = _pyvips()
    image = pyvips.Image.new_from_file(str(path), access="sequential")
    return image.autorot()


def _ensure_alpha(image):
    if image.hasalpha():
        return image
    return image.bandjoin(255)


def _contain(image, target_size: tuple[int, int], padding_ratio: float = 0.08):
    pyvips = _pyvips()
    target_width, target_height = target_size
    padding_x = round(target_width * padding_ratio)
    padding_y = round(target_height * padding_ratio)
    available_width = max(1, target_width - 2 * padding_x)
    available_height = max(1, target_height - 2 * padding_y)
    scale = min(available_width / image.width, available_height / image.height, 1.0)
    resized = image.resize(scale, kernel="lanczos3") if scale < 1.0 else image.copy()
    resized = _ensure_alpha(resized)
    canvas = pyvips.Image.black(target_width, target_height, bands=4)
    left = (target_width - resized.width) // 2
    top = (target_height - resized.height) // 2
    return canvas.insert(resized, left, top, expand=False)


def _cover(image, target_size: tuple[int, int], focus: tuple[float, float]):
    crop_box = cover_crop_box((image.width, image.height), target_size, focus)
    left, top, right, bottom = crop_box
    crop_width = right - left
    crop_height = bottom - top
    if crop_width < target_size[0] or crop_height < target_size[1]:
        raise UpscaleRequired(
            f"source crop {crop_width}x{crop_height} is smaller than target "
            f"{target_size[0]}x{target_size[1]}"
        )
    cropped = image.crop(left, top, crop_width, crop_height)
    rendered = cropped.resize(
        target_size[0] / crop_width,
        vscale=target_size[1] / crop_height,
        kernel="lanczos3",
    )
    if rendered.width > target_size[0] or rendered.height > target_size[1]:
        rendered = rendered.crop(0, 0, target_size[0], target_size[1])
    if rendered.width < target_size[0] or rendered.height < target_size[1]:
        rendered = rendered.embed(
            0,
            0,
            target_size[0],
            target_size[1],
            extend="copy",
        )
    return rendered


def render(image, *, variant: str, fit: str, focus: tuple[float, float] = (0.5, 0.5)):
    if variant not in VARIANTS:
        raise ValueError(f"unknown variant: {variant}")
    normalized_focus = normalize_focus(focus)
    if fit == "contain":
        return _contain(image, VARIANTS[variant])
    if fit == "cover":
        return _cover(image, VARIANTS[variant], normalized_focus)
    raise ValueError(f"unknown fit: {fit}")


def encode(image, output_format: str) -> bytes:
    output_format = output_format.upper()
    if output_format == "JPEG":
        if image.hasalpha():
            image = image.flatten(background=[255, 255, 255])
        return image.write_to_buffer(
            ".jpg",
            Q=85,
            strip=True,
            optimize_coding=False,
            interlace=False,
            subsample_mode="off",
        )
    if output_format == "PNG":
        return image.write_to_buffer(".png", compression=9, strip=True)
    if output_format == "WEBP":
        return image.write_to_buffer(
            ".webp",
            Q=82,
            lossless=image.hasalpha(),
            strip=True,
            effort=6,
        )
    if output_format == "AVIF":
        return image.write_to_buffer(".avif", Q=55, effort=6, strip=True)
    raise ValueError(f"unsupported output format: {output_format}")


def render_file(
    path: Path,
    *,
    variant: str,
    fit: str,
    focus: tuple[float, float] = (0.5, 0.5),
    output_format: str,
) -> dict[str, object]:
    image = load_image(path)
    rendered = render(image, variant=variant, fit=fit, focus=focus)
    data = encode(rendered, output_format)
    return {
        "width": rendered.width,
        "height": rendered.height,
        "bands": rendered.bands,
        "has_alpha": rendered.hasalpha(),
        "byte_size": len(data),
        "checksum": checksum_bytes(data),
        "data": data,
    }


def format_capabilities() -> dict[str, dict[str, object]]:
    pyvips = _pyvips()
    image = pyvips.Image.black(96, 64, bands=3) + [20, 90, 70]
    results: dict[str, dict[str, object]] = {}
    for output_format in ("JPEG", "PNG", "WEBP", "AVIF"):
        try:
            data = encode(image, output_format)
            results[output_format] = {"available": True, "byte_size": len(data)}
        except Exception as exc:  # capability probe intentionally records failures
            results[output_format] = {"available": False, "error": str(exc)}
    results["SVG"] = {
        "available": ".svg" in pyvips.get_suffixes(),
        "note": "suffix probe only; SVG remains rejected by prototype policy",
    }
    return results
