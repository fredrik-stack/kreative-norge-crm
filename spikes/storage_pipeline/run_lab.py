from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import tempfile

from storage_lab.storage import configure_django_environment, reset_moto


def main() -> int:
    parser = argparse.ArgumentParser(description="Run isolated phase 3B.2 storage evidence lab")
    parser.add_argument("--endpoint", default=os.environ.get("PHASE3B2_S3_ENDPOINT", "http://localhost:5000"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--no-reset", action="store_true")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="phase3b2-work-") as temporary:
        work_root = Path(temporary)
        configure_django_environment(work_root, endpoint=args.endpoint)
        import django

        django.setup()
        if not args.no_reset:
            reset_moto(args.endpoint)

        from storage_lab.scenario import execute_takedown_restore_scenario

        evidence = execute_takedown_restore_scenario(work_root, endpoint=args.endpoint)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "ok",
        "evidence": str(args.output),
        "r1": evidence["key_contract"]["r1"],
        "r2": evidence["key_contract"]["r2"],
        "t0_t5": "passed",
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
