from __future__ import annotations

import argparse
import json
from pathlib import Path
import platform
import resource
import statistics
import time

from .core import VARIANTS


def _rss_mib() -> float:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if platform.system() == "Darwin":
        return round(value / (1024 * 1024), 3)
    return round(value / 1024, 3)


def _run_pillow(path: Path, fit: str, output_format: str, iterations: int) -> dict[str, object]:
    import PIL

    from .pillow_backend import create_rendition, inspect_source

    declared_mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    checksums: dict[str, list[str]] = {variant: [] for variant in VARIANTS}
    byte_sizes: list[int] = []
    usage_before = resource.getrusage(resource.RUSAGE_SELF)
    started = time.perf_counter()
    for _ in range(iterations):
        source = inspect_source(path, declared_mime=declared_mime)
        for variant in VARIANTS:
            info, _ = create_rendition(
                source,
                variant=variant,
                fit=fit,
                focus=(0.72, 0.44) if fit == "cover" else (0.5, 0.5),
                output_format=output_format,
            )
            checksums[variant].append(info.checksum)
            byte_sizes.append(info.byte_size)
    elapsed = time.perf_counter() - started
    usage_after = resource.getrusage(resource.RUSAGE_SELF)
    user_cpu_ms = (usage_after.ru_utime - usage_before.ru_utime) * 1000
    system_cpu_ms = (usage_after.ru_stime - usage_before.ru_stime) * 1000
    return {
        "backend": "Pillow",
        "backend_version": PIL.__version__,
        "iterations": iterations,
        "renditions": iterations * len(VARIANTS),
        "elapsed_ms_total": round(elapsed * 1000, 3),
        "ms_per_rendition": round(elapsed * 1000 / (iterations * len(VARIANTS)), 3),
        "user_cpu_ms_total": round(user_cpu_ms, 3),
        "system_cpu_ms_total": round(system_cpu_ms, 3),
        "cpu_ms_per_rendition": round(
            (user_cpu_ms + system_cpu_ms) / (iterations * len(VARIANTS)), 3
        ),
        "peak_rss_mib": _rss_mib(),
        "mean_output_bytes": round(statistics.mean(byte_sizes)),
        "deterministic": all(len(set(values)) == 1 for values in checksums.values()),
        "unique_checksums_by_variant": {
            variant: len(set(values)) for variant, values in checksums.items()
        },
    }


def _run_pyvips(path: Path, fit: str, output_format: str, iterations: int) -> dict[str, object]:
    from .pyvips_backend import render_file, versions

    checksums: dict[str, list[str]] = {variant: [] for variant in VARIANTS}
    byte_sizes: list[int] = []
    usage_before = resource.getrusage(resource.RUSAGE_SELF)
    started = time.perf_counter()
    for _ in range(iterations):
        for variant in VARIANTS:
            result = render_file(
                path,
                variant=variant,
                fit=fit,
                focus=(0.72, 0.44) if fit == "cover" else (0.5, 0.5),
                output_format=output_format,
            )
            checksums[variant].append(str(result["checksum"]))
            byte_sizes.append(int(result["byte_size"]))
    elapsed = time.perf_counter() - started
    usage_after = resource.getrusage(resource.RUSAGE_SELF)
    user_cpu_ms = (usage_after.ru_utime - usage_before.ru_utime) * 1000
    system_cpu_ms = (usage_after.ru_stime - usage_before.ru_stime) * 1000
    version_info = versions()
    return {
        "backend": "pyvips/libvips",
        "backend_version": f"{version_info['pyvips']} / {version_info['libvips']}",
        "iterations": iterations,
        "renditions": iterations * len(VARIANTS),
        "elapsed_ms_total": round(elapsed * 1000, 3),
        "ms_per_rendition": round(elapsed * 1000 / (iterations * len(VARIANTS)), 3),
        "user_cpu_ms_total": round(user_cpu_ms, 3),
        "system_cpu_ms_total": round(system_cpu_ms, 3),
        "cpu_ms_per_rendition": round(
            (user_cpu_ms + system_cpu_ms) / (iterations * len(VARIANTS)), 3
        ),
        "peak_rss_mib": _rss_mib(),
        "mean_output_bytes": round(statistics.mean(byte_sizes)),
        "deterministic": all(len(set(values)) == 1 for values in checksums.values()),
        "unique_checksums_by_variant": {
            variant: len(set(values)) for variant, values in checksums.items()
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", choices=("pillow", "pyvips"), required=True)
    parser.add_argument("--path", type=Path, required=True)
    parser.add_argument("--fit", choices=("contain", "cover"), required=True)
    parser.add_argument("--format", choices=("JPEG", "PNG", "WEBP"), required=True)
    parser.add_argument("--iterations", type=int, default=3)
    args = parser.parse_args()

    if args.backend == "pillow":
        result = _run_pillow(args.path, args.fit, args.format, args.iterations)
    else:
        result = _run_pyvips(args.path, args.fit, args.format, args.iterations)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
