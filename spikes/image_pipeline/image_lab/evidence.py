from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont

from .core import PROCESSING_VERSION, VARIANTS, SourceRejected, UpscaleRequired, checksum_bytes
from .fixtures import generate_fixtures
from .pillow_backend import (
    create_rendition,
    encode_image,
    format_capabilities as pillow_format_capabilities,
    inspect_source,
    quality_observation,
    render_fallback,
    sensitive_metadata,
    write_static_emergency_fallbacks,
)


def _font(size: int):
    return ImageFont.load_default(size=size)


def _image_from_bytes(data: bytes) -> Image.Image:
    with Image.open(BytesIO(data)) as opened:
        opened.load()
        return opened.convert("RGBA").copy()


def _rejection_panel(name: str, code: str) -> Image.Image:
    image = Image.new("RGB", (640, 400), (112, 35, 38))
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 20, 620, 380), outline=(245, 190, 190), width=5)
    draw.text((320, 125), "AVVIST", font=_font(60), fill=(255, 235, 235), anchor="mm")
    draw.text((320, 225), name, font=_font(34), fill="white", anchor="mm")
    draw.text((320, 300), code, font=_font(27), fill=(255, 210, 160), anchor="mm")
    return image


def build_contact_sheet(
    panels: Iterable[tuple[str, Image.Image]],
    output_path: Path,
    *,
    columns: int = 4,
) -> dict[str, object]:
    panel_list = list(panels)
    cell_width, cell_height = 420, 310
    image_width, image_height = 380, 235
    rows = (len(panel_list) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * cell_width, rows * cell_height), (242, 244, 241))
    draw = ImageDraw.Draw(sheet)

    for index, (caption, source) in enumerate(panel_list):
        column = index % columns
        row = index // columns
        origin_x = column * cell_width
        origin_y = row * cell_height
        preview = source.convert("RGBA")
        preview.thumbnail((image_width, image_height), Image.Resampling.LANCZOS)
        checker = Image.new("RGBA", (image_width, image_height), (228, 232, 226, 255))
        checker_draw = ImageDraw.Draw(checker)
        block = 24
        for y in range(0, image_height, block):
            for x in range(0, image_width, block):
                if (x // block + y // block) % 2:
                    checker_draw.rectangle(
                        (x, y, min(image_width, x + block), min(image_height, y + block)),
                        fill=(247, 248, 246, 255),
                    )
        checker.alpha_composite(
            preview,
            dest=((image_width - preview.width) // 2, (image_height - preview.height) // 2),
        )
        sheet.paste(checker.convert("RGB"), (origin_x + 20, origin_y + 15))
        draw.rectangle(
            (origin_x + 20, origin_y + 15, origin_x + 20 + image_width, origin_y + 15 + image_height),
            outline=(116, 125, 116),
            width=2,
        )
        draw.text(
            (origin_x + cell_width // 2, origin_y + 270),
            caption,
            font=_font(23),
            fill=(27, 49, 41),
            anchor="mm",
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    buffer = BytesIO()
    sheet.save(buffer, format="WEBP", quality=78, method=6, exif=b"", icc_profile=b"", xmp=b"")
    data = buffer.getvalue()
    output_path.write_bytes(data)
    return {
        "filename": output_path.name,
        "panels": len(panel_list),
        "width": sheet.width,
        "height": sheet.height,
        "byte_size": len(data),
        "checksum": checksum_bytes(data),
    }


def _run_benchmark(
    spike_root: Path,
    *,
    backend: str,
    fixture_path: Path,
    fit: str,
    output_format: str,
    iterations: int,
) -> dict[str, object]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(spike_root)
    command = [
        sys.executable,
        "-m",
        "image_lab.benchmark_worker",
        "--backend",
        backend,
        "--path",
        str(fixture_path),
        "--fit",
        fit,
        "--format",
        output_format,
        "--iterations",
        str(iterations),
    ]
    completed = subprocess.run(
        command,
        cwd=spike_root,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(completed.stdout)


def _format_comparison(source, *, fit: str, variant: str) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for output_format in ("JPEG", "PNG", "WEBP", "AVIF"):
        try:
            info, _ = create_rendition(
                source,
                variant=variant,
                fit=fit,
                focus=(0.72, 0.44),
                output_format=output_format,
            )
            result[output_format] = {
                "available": True,
                "byte_size": info.byte_size,
                "checksum": info.checksum,
                "has_alpha": info.has_alpha,
                "sensitive_metadata": sorted(sensitive_metadata(info.metadata_keys)),
            }
        except Exception as exc:
            result[output_format] = {"available": False, "error": str(exc)}
    return result


def collect_evidence(
    *,
    spike_root: Path,
    output_root: Path,
    static_root: Path | None = None,
    committed_contact_sheet: Path | None = None,
    iterations: int = 3,
) -> dict[str, object]:
    output_root.mkdir(parents=True, exist_ok=True)
    fixture_root = output_root / "fixtures"
    fixture_specs = generate_fixtures(fixture_root)
    accepted: dict[str, object] = {}
    rejected: dict[str, object] = {}
    loaded = {}

    for fixture in fixture_specs:
        try:
            source = inspect_source(
                fixture.path(fixture_root),
                declared_mime=fixture.declared_mime,
                semantic_flags=fixture.semantic_flags,
            )
            loaded[fixture.name] = source
            source_result = source.info.as_dict()
            source_result["path"] = fixture.filename
            source_result["quality"] = quality_observation(source.info)
            source_result["expected"] = fixture.expected
            accepted[fixture.name] = source_result
        except SourceRejected as exc:
            rejected[fixture.name] = {
                "code": exc.code,
                "message": str(exc),
                "expected": fixture.expected,
            }

    unexpected_accepts = sorted(
        fixture.name for fixture in fixture_specs if fixture.expected == "reject" and fixture.name in accepted
    )
    unexpected_rejects = sorted(
        fixture.name for fixture in fixture_specs if fixture.expected == "accept" and fixture.name in rejected
    )
    if unexpected_accepts or unexpected_rejects:
        raise RuntimeError(
            f"fixture contract mismatch: accepts={unexpected_accepts}, rejects={unexpected_rejects}"
        )

    panels: list[tuple[str, Image.Image]] = []
    renditions: dict[str, object] = {}

    wide_logo = loaded["wide_logo"]
    landscape_photo = loaded["landscape_photo"]
    panels.append(("Original: bred logo", wide_logo.image.copy()))
    for variant in VARIANTS:
        info, data = create_rendition(
            wide_logo,
            variant=variant,
            fit="contain",
            output_format="PNG",
            output_root=output_root,
        )
        renditions[f"logo_{variant}"] = info.as_dict()
        panels.append((f"Logo contain: {variant}", _image_from_bytes(data)))

    panels.append(("Original: landskapsfoto", landscape_photo.image.copy()))
    for variant in VARIANTS:
        info, data = create_rendition(
            landscape_photo,
            variant=variant,
            fit="cover",
            focus=(0.5, 0.5),
            output_format="JPEG",
            output_root=output_root,
        )
        renditions[f"photo_center_{variant}"] = info.as_dict()
        panels.append((f"Foto cover: {variant}", _image_from_bytes(data)))

    shifted_info, shifted_data = create_rendition(
        landscape_photo,
        variant="square",
        fit="cover",
        focus=(0.82, 0.44),
        output_format="JPEG",
        output_root=output_root,
    )
    renditions["photo_shifted_square"] = shifted_info.as_dict()
    panels.append(("Foto: flyttet fokus", _image_from_bytes(shifted_data)))

    fallback_results: dict[str, object] = {}
    for variant in VARIANTS:
        fallback = render_fallback("Arktisk Kulturverksted", "Scenekunst", variant=variant)
        data = encode_image(fallback, "JPEG")
        target = output_root / "fallback" / f"fallback-{variant}.jpg"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        fallback_results[variant] = {
            "width": fallback.width,
            "height": fallback.height,
            "byte_size": len(data),
            "checksum": checksum_bytes(data),
        }
        panels.append((f"Fallback: {variant}", _image_from_bytes(data)))

    for name in ("corrupt", "mime_mismatch", "pixel_bomb", "generic_platform_icon"):
        failure = rejected[name]
        panels.append((f"Avvist: {name}", _rejection_panel(name, str(failure["code"]))))

    determinism_runs = [
        create_rendition(
            landscape_photo,
            variant="share",
            fit="cover",
            focus=(0.72, 0.44),
            output_format="JPEG",
        )[0]
        for _ in range(3)
    ]
    determinism = {
        "runs": len(determinism_runs),
        "unique_checksums": len({item.checksum for item in determinism_runs}),
        "unique_sizes": len({item.byte_size for item in determinism_runs}),
        "unique_metadata_sets": len({item.metadata_keys for item in determinism_runs}),
        "byte_identical": len({item.checksum for item in determinism_runs}) == 1,
    }

    static_fallbacks = write_static_emergency_fallbacks(static_root or output_root / "static")
    static_fallbacks = {
        variant: {**values, "path": Path(str(values["path"])).name}
        for variant, values in static_fallbacks.items()
    }

    contact_target = output_root / "phase3b1-contact-sheet.webp"
    contact_sheet = build_contact_sheet(panels, contact_target)
    if committed_contact_sheet:
        committed_contact_sheet.parent.mkdir(parents=True, exist_ok=True)
        committed_contact_sheet.write_bytes(contact_target.read_bytes())

    try:
        from .pyvips_backend import format_capabilities as pyvips_format_capabilities
        from .pyvips_backend import versions as pyvips_versions

        pyvips_probe: dict[str, object] = {
            "available": True,
            "versions": pyvips_versions(),
            "formats": pyvips_format_capabilities(),
        }
    except Exception as exc:
        pyvips_probe = {"available": False, "error": str(exc)}

    benchmarks: dict[str, object] = {}
    benchmark_cases = {
        "photo_cover": (fixture_root / "landscape-photo.jpg", "cover", "JPEG"),
        "logo_contain": (fixture_root / "wide-logo.png", "contain", "PNG"),
    }
    for case_name, (path, fit, output_format) in benchmark_cases.items():
        case_results: dict[str, object] = {}
        for backend in ("pillow", "pyvips"):
            try:
                case_results[backend] = _run_benchmark(
                    spike_root,
                    backend=backend,
                    fixture_path=path,
                    fit=fit,
                    output_format=output_format,
                    iterations=iterations,
                )
            except (subprocess.CalledProcessError, OSError, json.JSONDecodeError) as exc:
                case_results[backend] = {
                    "available": False,
                    "error": getattr(exc, "stderr", None) or str(exc),
                }
        benchmarks[case_name] = case_results

    small_image_result: dict[str, object]
    try:
        create_rendition(
            loaded["small_image"],
            variant="square",
            fit="cover",
            output_format="JPEG",
        )
        small_image_result = {"blocked_upscale": False}
    except UpscaleRequired as exc:
        small_image_result = {"blocked_upscale": True, "message": str(exc)}

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "phase 3B.1 isolated prototype; not CRM runtime",
        "processing_version": PROCESSING_VERSION,
        "environment": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "fixture_summary": {
            "total": len(fixture_specs),
            "accepted": len(accepted),
            "rejected": len(rejected),
        },
        "accepted_fixtures": accepted,
        "rejected_fixtures": rejected,
        "renditions": renditions,
        "fallback": fallback_results,
        "static_emergency_fallback": static_fallbacks,
        "small_image": small_image_result,
        "determinism": determinism,
        "format_capabilities": {
            "pillow": pillow_format_capabilities(),
            "pyvips": pyvips_probe,
        },
        "format_comparison": {
            "photo_square": _format_comparison(landscape_photo, fit="cover", variant="square"),
            "logo_landscape": _format_comparison(wide_logo, fit="contain", variant="landscape"),
        },
        "benchmarks": benchmarks,
        "contact_sheet": contact_sheet,
    }
    (output_root / "evidence.json").write_text(
        json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return result
