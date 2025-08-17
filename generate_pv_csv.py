#!/usr/bin/env python3
"""Export WordPress page views for all configured accounts.

Reads ``config.json`` to obtain the list of WordPress accounts and calls
``services.wordpress_pv_csv.export_views`` for each of them.

Optional ``--days`` and ``--output-dir`` arguments allow customizing the
number of days of statistics retrieved per post and the directory where CSV
files are written.
"""

import argparse
import json
from pathlib import Path

from services.wordpress_pv_csv import export_views

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Export WordPress page views to CSV files",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days of view statistics to fetch per post",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("."),
        help="Directory where CSV files will be written",
    )
    return parser.parse_args()


def main() -> None:
    """Entry point for CSV generation."""
    args = parse_args()
    try:
        with CONFIG_PATH.open() as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"Config file not found: {CONFIG_PATH}")
        return

    accounts = config.get("wordpress", {}).get("accounts", {})
    if not accounts:
        print("WordPress accounts not found in config.json")
        return

    for name in accounts.keys():
        result = export_views(name, days=args.days, output_dir=args.output_dir)
        if result.get("error"):
            print(f"Failed to export views for {name}: {result['error']}")
        else:
            csv_path = result.get("csv")
            posts = result.get("posts", 0)
            print(f"Exported {posts} posts for {name} -> {csv_path}")


if __name__ == "__main__":  # pragma: no cover
    main()
