from __future__ import annotations

import csv
from datetime import datetime, timezone
from hashlib import sha256
import html
from io import BytesIO
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any

import PIL
from PIL import Image, ImageDraw

from . import LAB_VERSION
from .manifest import Manifest, ManifestError, load_manifest


class RunnerError(RuntimeError):
    pass


CHECKERBOARD_LIGHT = (238, 240, 238)
CHECKERBOARD_DARK = (210, 214, 210)
CHECKERBOARD_BLOCK = 16


def _inside(path: Path, parent: Path) -> bool:
    return path == parent or parent in path.parents


def validate_roots(dataset_root: Path, output_root: Path) -> tuple[Path, Path]:
    dataset = dataset_root.resolve()
    output = output_root.resolve()
    if _inside(output, dataset) or _inside(dataset, output):
        raise RunnerError("output-root and dataset-root must be separate trees")
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise RunnerError("output-root must not exist or must be an empty directory")
    output.mkdir(parents=True, exist_ok=True)
    return dataset, output


def _worker(spike_root: Path, output_root: Path, fixture: Any) -> dict[str, Any]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(spike_root)
    try:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "representative_lab.worker",
                "--payload",
                json.dumps(fixture.worker_payload(), sort_keys=True),
                "--output-root",
                str(output_root),
            ],
            cwd=spike_root,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
    except subprocess.TimeoutExpired as exc:
        raise RunnerError(f"isolated worker timed out for {fixture.fixture_id}") from exc
    if completed.returncode != 0:
        raise RunnerError(
            f"isolated worker failed for {fixture.fixture_id}: "
            f"{completed.stderr.strip() or 'no diagnostic'}"
        )
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RunnerError(f"isolated worker returned invalid evidence for {fixture.fixture_id}") from exc
    expected = fixture.expected_result
    actual = result.get("status")
    if actual != expected:
        detail = result.get("error", {}).get("code", actual)
        raise RunnerError(
            f"fixture {fixture.fixture_id} expected {expected}, received {actual}: {detail}"
        )
    if actual == "controlled_error":
        actual_code = result.get("error", {}).get("code")
        if actual_code != fixture.expected_error_code:
            raise RunnerError(
                f"fixture {fixture.fixture_id} expected controlled error code "
                f"{fixture.expected_error_code}, received {actual_code}"
            )
    if actual == "success":
        for variant in fixture.expected_variants:
            entry = result.get("renditions", {}).get(variant)
            if not isinstance(entry, dict) or "suitability" not in entry or "outputs" not in entry:
                raise RunnerError(f"fixture {fixture.fixture_id} has incomplete evidence for {variant}")
            if entry["suitability"].get("can_render_without_upscale") and set(entry["outputs"]) != {
                "profile_free",
                "embedded_srgb",
            }:
                raise RunnerError(f"fixture {fixture.fixture_id} lacks both sRGB output candidates")
    return result


def _write_measurements(results: list[dict[str, Any]], target: Path) -> None:
    fields = [
        "fixture_id",
        "status",
        "category",
        "fit",
        "source_bytes",
        "source_checksum",
        "format",
        "mime",
        "width",
        "height",
        "pixels",
        "aspect_ratio",
        "color_mode",
        "has_alpha",
        "icc_status",
        "edge_variance",
        "blockiness_indicator",
        "decode_ms",
        "rendition_ms",
        "peak_rss_mib",
    ]
    with target.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for result in results:
            source = result.get("source", {})
            dimensions = source.get("normalized_dimensions", [None, None])
            quality = result.get("quality_measurements", {})
            resource = result.get("resource_usage", {})
            writer.writerow(
                {
                    "fixture_id": result.get("fixture_id"),
                    "status": result.get("status"),
                    "category": result.get("category"),
                    "fit": result.get("intended_fit"),
                    "source_bytes": source.get("byte_size"),
                    "source_checksum": source.get("checksum"),
                    "format": source.get("format"),
                    "mime": source.get("mime"),
                    "width": dimensions[0],
                    "height": dimensions[1],
                    "pixels": source.get("pixel_count"),
                    "aspect_ratio": source.get("aspect_ratio"),
                    "color_mode": source.get("color_mode"),
                    "has_alpha": source.get("has_alpha"),
                    "icc_status": result.get("color_profile", {}).get("status"),
                    "edge_variance": quality.get("edge_variance"),
                    "blockiness_indicator": quality.get("blockiness_indicator"),
                    "decode_ms": resource.get("decode_and_normalize_ms"),
                    "rendition_ms": resource.get("rendition_ms"),
                    "peak_rss_mib": resource.get("peak_rss_mib"),
                }
            )


REVIEW_FIELDS = [
    "fixture_id",
    "square_crop_approved",
    "landscape_crop_approved",
    "share_crop_approved",
    "relevant_content_retained",
    "color_shift_none_minor_unacceptable",
    "sharpness",
    "compression_artifacts",
    "logo_legibility",
    "internal_whitespace",
    "poster_date_or_text",
    "watermark",
    "recommended_pass_manual_review_reject",
    "reviewer_notes",
]


def _write_review_template(results: list[dict[str, Any]], json_target: Path, csv_target: Path) -> None:
    rows = [{field: (result["fixture_id"] if field == "fixture_id" else "") for field in REVIEW_FIELDS} for result in results]
    json_target.write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with csv_target.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=REVIEW_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _write_review_html(results: list[dict[str, Any]], target: Path) -> None:
    cards: list[str] = []
    for result in results:
        fixture_id = html.escape(str(result["fixture_id"]))
        if result["status"] != "success":
            error = html.escape(str(result.get("error", {}).get("code", "controlled_error")))
            cards.append(f'<article><h2>{fixture_id}</h2><p class="error">Controlled error: {error}</p></article>')
            continue
        fixture_dir = fixture_id
        preview = result["preview"]
        preview_path = html.escape(f"{fixture_dir}/{preview['relative_path']}")
        preview_class = "checkerboard" if preview.get("has_alpha") else "opaque-preview"
        preview_caption = (
            "Original preview with alpha on neutral checkerboard"
            if preview.get("has_alpha")
            else "Original preview"
        )
        images = [
            f'<figure class="{preview_class}"><img src="{preview_path}" '
            f'alt="Original preview"><figcaption>{preview_caption}</figcaption></figure>'
        ]
        for variant, evidence in result["renditions"].items():
            output = evidence["outputs"].get("profile_free")
            if output:
                path = html.escape(f"{fixture_dir}/{output['relative_path']}")
                images.append(f'<figure><img src="{path}" alt="{variant}"><figcaption>{variant}</figcaption></figure>')
        measurements = html.escape(
            json.dumps(
                {
                    "source": result["source"],
                    "color_profile": result["color_profile"],
                    "quality": result["quality_measurements"],
                    "logo": result["logo_observation"],
                    "resource": result["resource_usage"],
                },
                indent=2,
                sort_keys=True,
            )
        )
        cards.append(
            f'<article><h2>{fixture_id}</h2><div class="images">{"".join(images)}</div>'
            f'<details><summary>Technical evidence</summary><pre>{measurements}</pre></details>'
            '<fieldset><legend>Manual review</legend>'
            '<p>Crop per variant: square ___ landscape ___ share ___</p>'
            '<p>Relevant content retained: ___</p><p>Color shift: none / minor / unacceptable</p>'
            '<p>Sharpness: ___ Compression artifacts: ___ Logo legibility: ___</p>'
            '<p>Internal whitespace: ___ Poster/date/text: ___ Watermark: ___</p>'
            '<p>Recommendation: pass / manual_review / reject</p><p>Notes: ____________________</p>'
            '</fieldset></article>'
        )
    document = f"""<!doctype html>
<html lang="en"><meta charset="utf-8"><title>Phase 3B.1R local review</title>
<style>
body{{font:16px system-ui,sans-serif;margin:2rem;background:#f4f5f2;color:#17251f}}
article{{background:white;padding:1rem;margin:0 0 1.5rem;border:1px solid #ccd3cc}}
.images{{display:flex;flex-wrap:wrap;gap:1rem}}figure{{margin:0}}img{{max-width:320px;max-height:240px;border:1px solid #999}}
.checkerboard img{{background-color:rgb(238,240,238);background-image:linear-gradient(45deg,rgb(210,214,210) 25%,transparent 25%),linear-gradient(-45deg,rgb(210,214,210) 25%,transparent 25%),linear-gradient(45deg,transparent 75%,rgb(210,214,210) 75%),linear-gradient(-45deg,transparent 75%,rgb(210,214,210) 75%);background-size:32px 32px;background-position:0 0,0 16px,16px -16px,-16px 0}}
pre{{white-space:pre-wrap;overflow-wrap:anywhere}}fieldset{{margin-top:1rem}}.error{{color:#8b1f24}}
</style><body><h1>Phase 3B.1R local review</h1>
<p>Advisory evidence only. No threshold or output-profile strategy is approved by this report.</p>
{"".join(cards)}</body></html>"""
    target.write_text(document, encoding="utf-8")


def _checkerboard(size: tuple[int, int]) -> Image.Image:
    background = Image.new("RGB", size, CHECKERBOARD_LIGHT)
    draw = ImageDraw.Draw(background)
    for y in range(0, size[1], CHECKERBOARD_BLOCK):
        for x in range(0, size[0], CHECKERBOARD_BLOCK):
            if (x // CHECKERBOARD_BLOCK + y // CHECKERBOARD_BLOCK) % 2:
                draw.rectangle(
                    (
                        x,
                        y,
                        min(size[0], x + CHECKERBOARD_BLOCK) - 1,
                        min(size[1], y + CHECKERBOARD_BLOCK) - 1,
                    ),
                    fill=CHECKERBOARD_DARK,
                )
    return background


def _write_contact_sheet(results: list[dict[str, Any]], output_root: Path) -> None:
    successful = [item for item in results if item["status"] == "success"]
    width, cell_height = 900, 260
    sheet = Image.new("RGB", (width, max(cell_height, len(successful) * cell_height)), "white")
    draw = ImageDraw.Draw(sheet)
    for index, result in enumerate(successful):
        y = index * cell_height
        preview_path = (
            output_root
            / str(result["fixture_id"])
            / str(result["preview"]["relative_path"])
        )
        with Image.open(preview_path) as opened:
            preview = opened.convert("RGBA")
            preview.thumbnail((360, 220), Image.Resampling.LANCZOS)
        if result["preview"].get("has_alpha"):
            composed = _checkerboard(preview.size)
            composed.paste(preview, (0, 0), preview)
        else:
            composed = preview.convert("RGB")
        sheet.paste(composed, (10, y + 10))
        draw.text((390, y + 20), str(result["fixture_id"]), fill="black")
        draw.text((390, y + 55), f"fit={result['intended_fit']} icc={result['color_profile']['status']}", fill="black")
        draw.text((390, y + 90), "Manual: pass / review / reject", fill="black")
    buffer = BytesIO()
    sheet.save(buffer, "JPEG", quality=82, exif=b"", icc_profile=b"")
    (output_root / "contact-sheet-local.jpg").write_bytes(buffer.getvalue())


def _redacted(results: list[dict[str, Any]], manifest: Manifest) -> dict[str, Any]:
    fixtures: list[dict[str, Any]] = []
    candidate_summary: dict[str, dict[str, Any]] = {}
    for limit in (20_000_000, 36_000_000, 50_000_000, 64_000_000, 100_000_000):
        affected = [
            item["fixture_id"]
            for item in results
            if item["status"] == "success" and item["source"]["pixel_count"] > limit
        ]
        candidate_summary[str(limit)] = {
            "rejected_count": len(affected),
            "affected_fixture_ids": affected,
            "affected_use_cases": sorted(
                {item["category"] for item in results if item.get("fixture_id") in affected}
            ),
            "observed_affected_decode_ms": [
                item["resource_usage"]["decode_and_normalize_ms"]
                for item in results
                if item.get("fixture_id") in affected
            ],
            "observed_affected_rendition_ms": [
                item["resource_usage"]["rendition_ms"]
                for item in results
                if item.get("fixture_id") in affected
            ],
            "observed_affected_peak_rss_mib": [
                item["resource_usage"]["peak_rss_mib"]
                for item in results
                if item.get("fixture_id") in affected
            ],
            "security_and_operations": "lower limits reduce decode exposure but may reject valid representative use cases",
        }
    for item in results:
        if item["status"] == "success":
            fixtures.append(
                {
                    "fixture_id": item["fixture_id"],
                    "status": item["status"],
                    "category": item["category"],
                    "fit": item["intended_fit"],
                    "source_checksum": item["source"]["checksum"],
                    "source_dimensions": item["source"]["normalized_dimensions"],
                    "pixel_count": item["source"]["pixel_count"],
                    "color_profile_status": item["color_profile"]["status"],
                    "quality_measurements": item["quality_measurements"],
                    "resource_usage": item["resource_usage"],
                    "renditions": {
                        variant: {
                            "suitability": value["suitability"],
                            "checksums": {
                                contract: output["checksum"] for contract, output in value["outputs"].items()
                            },
                        }
                        for variant, value in item["renditions"].items()
                    },
                }
            )
        else:
            fixtures.append(
                {
                    "fixture_id": item["fixture_id"],
                    "status": item["status"],
                    "error_code": item.get("error", {}).get("code"),
                }
            )
    return {
        "scope": "phase 3B.1R-A advisory evidence; no final rules",
        "dataset_manifest_checksum": manifest.checksum,
        "contains_image_bytes": False,
        "fixtures": fixtures,
        "pixel_limit_candidates": candidate_summary,
    }


def _file_checksum(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(dataset_root: Path, output_root: Path, *, argv: list[str]) -> dict[str, Any]:
    dataset, output = validate_roots(dataset_root, output_root)
    manifest = load_manifest(dataset)
    source_checksums = {
        fixture.fixture_id: _file_checksum(fixture.path) for fixture in manifest.fixtures
    }
    spike_root = Path(__file__).resolve().parents[1]
    results = [_worker(spike_root, output, fixture) for fixture in manifest.fixtures]
    for fixture in manifest.fixtures:
        if _file_checksum(fixture.path) != source_checksums[fixture.fixture_id]:
            raise RunnerError(f"source dataset changed during run: {fixture.fixture_id}")

    full = {
        "scope": "phase 3B.1R-A local advisory evidence; not CRM runtime",
        "lab_version": LAB_VERSION,
        "dataset_manifest_checksum": manifest.checksum,
        "fixtures": results,
    }
    (output / "evidence.json").write_text(json.dumps(full, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_measurements(results, output / "measurements.csv")
    _write_review_template(results, output / "review-template.json", output / "review.csv")
    _write_review_html(results, output / "review.html")
    _write_contact_sheet(results, output)
    redacted = _redacted(results, manifest)
    (output / "redacted-summary.json").write_text(
        json.dumps(redacted, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    run_manifest = {
        "lab_version": LAB_VERSION,
        "python": platform.python_version(),
        "pillow": PIL.__version__,
        "operating_system": platform.system(),
        "architecture": platform.machine(),
        "dataset_manifest_checksum": manifest.checksum,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "runner_arguments": argv,
        "network_used": False,
        "output_policy": {
            "commit_safe": ["redacted-summary.json"],
            "local_only": ["evidence.json", "measurements.csv", "review-template.json", "review.csv", "review.html"],
            "requires_all_redistribution_allowed": ["contact-sheet-local.jpg", "fixture previews and renditions"],
            "all_fixtures_allow_redistribution": all(item.redistribution_allowed for item in manifest.fixtures),
        },
    }
    (output / "run-manifest.json").write_text(
        json.dumps(run_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {
        "fixtures": len(results),
        "successful": sum(item["status"] == "success" for item in results),
        "controlled_errors": sum(item["status"] == "controlled_error" for item in results),
        "all_fixtures_allow_redistribution": run_manifest["output_policy"]["all_fixtures_allow_redistribution"],
        "phase_3b1r_complete": False,
    }
