"""Command-line utility to export WordPress post views as CSV files.

This script reads the ``config.json`` file for WordPress account
configuration and invokes :func:`services.wordpress_pv_csv.export_views`
to generate per-post view statistics in CSV format.
"""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from services.wordpress_pv_csv import export_views

CONFIG_PATH = Path("config.json")


def load_accounts() -> dict:
    """Load WordPress account configuration from ``config.json``."""
    with CONFIG_PATH.open() as fh:
        cfg = json.load(fh)
    return cfg.get("wordpress", {}).get("accounts", {})


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export WordPress post views to CSV files.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of most recent days to include (1-30).",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path(tempfile.gettempdir()),
        help="Directory to write CSV files to.",
    )
    args = parser.parse_args()

    if not 1 <= args.days <= 30:
        parser.error("--days must be between 1 and 30")

    try:
        accounts = load_accounts()
    except FileNotFoundError:
        print("config.json not found")
        return

    if not accounts:
        print("No WordPress accounts configured")
        return

    results = export_views(accounts, args.days, args.out_dir)
    for name, info in results.items():
        if "file" in info:
            print(f"{name}: {info['file']}")
        else:
            print(f"{name}: error - {info.get('error', 'unknown error')}")


if __name__ == "__main__":  # pragma: no cover - simple CLI
    main()
