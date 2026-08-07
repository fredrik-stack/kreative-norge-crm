#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from representative_lab.manifest import ManifestError
from representative_lab.runner import RunnerError, run


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the isolated phase 3B.1R representative image-quality harness"
    )
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        summary = run(
            args.dataset_root,
            args.output_root,
            argv=["--dataset-root", str(args.dataset_root), "--output-root", str(args.output_root)],
        )
    except (ManifestError, RunnerError, OSError) as exc:
        print(f"representative lab failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
