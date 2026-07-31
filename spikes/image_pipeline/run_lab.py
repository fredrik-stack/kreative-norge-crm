#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from image_lab.evidence import collect_evidence


def main() -> None:
    spike_root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Run the isolated phase 3B.1 image lab")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--static-root", type=Path)
    parser.add_argument("--committed-contact-sheet", type=Path)
    parser.add_argument("--iterations", type=int, default=3)
    args = parser.parse_args()
    if args.iterations < 3:
        parser.error("--iterations must be at least 3 to satisfy the determinism contract")

    result = collect_evidence(
        spike_root=spike_root,
        output_root=args.output.resolve(),
        static_root=args.static_root.resolve() if args.static_root else None,
        committed_contact_sheet=(
            args.committed_contact_sheet.resolve() if args.committed_contact_sheet else None
        ),
        iterations=args.iterations,
    )
    summary = {
        "fixture_summary": result["fixture_summary"],
        "determinism": result["determinism"],
        "small_image": result["small_image"],
        "benchmarks": result["benchmarks"],
        "contact_sheet": result["contact_sheet"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
