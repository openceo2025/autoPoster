#!/usr/bin/env python3
"""Export WordPress page views for all configured accounts.

Reads ``config.json`` to obtain the list of WordPress accounts and calls
``services.wordpress_pv_csv.export_views`` for each of them.
"""

import json
from pathlib import Path

from services.wordpress_pv_csv import export_views

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"


def main() -> None:
    """Entry point for CSV generation."""
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
        try:
            export_views(name)
            print(f"Exported views for {name}")
        except Exception as exc:  # pragma: no cover - best effort logging
            print(f"Failed to export views for {name}: {exc}")


if __name__ == "__main__":  # pragma: no cover
    main()
