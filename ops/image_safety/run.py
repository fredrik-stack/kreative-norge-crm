#!/usr/bin/env python3
from pathlib import Path
import sys


INSTALL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(INSTALL_DIR))

from image_safety.cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
