#!/usr/bin/env python3
"""Download the TLC files used to build the Bronze layer.

The files are intentionally kept outside Git. This script downloads the
January--June 2024 Yellow and Green trip records plus the TLC zone lookup into
the repository's ``raw/`` directory, where ``build_domain.py`` expects them.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "raw"
TRIP_DATA_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data"
MISC_DATA_URL = "https://d37ci6vzurychx.cloudfront.net/misc"
DEFAULT_MONTHS = [f"2024-{month:02d}" for month in range(1, 7)]


def _download(url: str, destination: Path, force: bool) -> None:
    if destination.exists() and not force:
        print(f"skip  {destination} (already exists; use --force to replace)")
        return

    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".part", dir=destination.parent
    )
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "sample-nyctaxi-comp/1.0"},
        )
        print(f"fetch {url}")
        with urllib.request.urlopen(request) as response, temporary.open("wb") as output:
            shutil.copyfileobj(response, output, length=1024 * 1024)
        temporary.replace(destination)
        print(f"save  {destination}")
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _valid_month(value: str) -> str:
    if len(value) != 7 or value[4] != "-" or not value[:4].isdigit() or not value[5:].isdigit():
        raise argparse.ArgumentTypeError(f"invalid month {value!r}; expected YYYY-MM")
    month = int(value[5:])
    if month < 1 or month > 12:
        raise argparse.ArgumentTypeError(f"invalid month {value!r}; expected YYYY-MM")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--months",
        nargs="+",
        type=_valid_month,
        default=DEFAULT_MONTHS,
        metavar="YYYY-MM",
        help="months to download (default: 2024-01 through 2024-06)",
    )
    parser.add_argument(
        "--fleet",
        choices=("yellow", "green", "both"),
        default="both",
        help="fleet files to download (default: both)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"download directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--skip-zone-lookup",
        action="store_true",
        help="do not download taxi_zone_lookup.csv",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace files that already exist",
    )
    args = parser.parse_args()

    fleets = ("yellow", "green") if args.fleet == "both" else (args.fleet,)
    for fleet in fleets:
        for month in args.months:
            filename = f"{fleet}_tripdata_{month}.parquet"
            _download(f"{TRIP_DATA_URL}/{filename}", args.output_dir / filename, args.force)

    if not args.skip_zone_lookup:
        _download(
            f"{MISC_DATA_URL}/taxi_zone_lookup.csv",
            args.output_dir / "taxi_zone_lookup.csv",
            args.force,
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        raise SystemExit(130)
