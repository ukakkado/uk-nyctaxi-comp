#!/usr/bin/env python3
"""Run the dbt project and generate its documentation site."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DBT_DIR = ROOT / "transformation"


def _run(dbt: str, arguments: list[str], env: dict[str, str]) -> None:
    command = [dbt, *arguments]
    print("+", " ".join(command))
    subprocess.run(command, cwd=DBT_DIR, env=env, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", default="domain", help="dbt profile target (default: domain)")
    parser.add_argument(
        "--docs-only",
        action="store_true",
        help="skip dbt build and only generate documentation",
    )
    args = parser.parse_args()

    dbt = shutil.which("dbt")
    if not dbt:
        parser.error("dbt is not installed; install dbt-duckdb first")

    env = os.environ.copy()
    env["DBT_PROFILES_DIR"] = "."
    if not args.docs_only:
        _run(dbt, ["build", "--target", args.target], env)
    _run(dbt, ["docs", "generate", "--target", args.target], env)
    print(f"\nDocumentation generated under {DBT_DIR / 'target'}")
    print("Serve it with: cd transformation && DBT_PROFILES_DIR=. dbt docs serve --port 8085")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
