#!/usr/bin/env python3
"""Build the deterministic non-TLC source systems.

Run this after ``build_domain.py``. It creates the synthetic ``mdm_raw`` and
``ops_raw`` schemas from the landed/conformed TLC data by invoking the existing
source builders in a documented order.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--only",
        choices=("mdm", "fleet", "both"),
        default="both",
        help="source system(s) to build (default: both)",
    )
    args = parser.parse_args()

    builders = {
        "mdm": ROOT / "tools" / "build_mdm.py",
        "fleet": ROOT / "tools" / "build_fleet_ops.py",
    }
    selected = ("mdm", "fleet") if args.only == "both" else (args.only,)
    for name in selected:
        print(f"\n=== building {name} source system ===")
        subprocess.run([sys.executable, str(builders[name])], cwd=ROOT, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
