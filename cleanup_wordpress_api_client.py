#!/usr/bin/env python3
import json
from pathlib import Path
import requests

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"
API_URL = "http://127.0.0.1:8765/wordpress/cleanup"


def main() -> None:
    """CLI client for the ``/wordpress/cleanup`` API.

    Reads all WordPress account identifiers from ``config.json`` and sends a
    cleanup request keeping only the latest ``n`` posts for each account.
    """
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

    keep_input = input("Keep how many recent posts? ").strip()
    try:
        keep_latest = int(keep_input)
    except ValueError:
        print("Invalid number.")
        return

    items = [
        {"identifier": name, "keep_latest": keep_latest}
        for name in accounts.keys()
    ]

    resp = requests.post(API_URL, json={"items": items})
    if resp.status_code != 200:
        print(f"Request failed ({resp.status_code}): {resp.text}")
        return

    data = resp.json()
    for result in data.get("results", []):
        account = result.get("account")
        error = result.get("error")
        if error:
            print(f"{account}: {error}")
        else:
            deleted = len(result.get("deleted_posts", []))
            trash = result.get("trash_emptied", 0)
            media = result.get("deleted_media", 0)
            print(
                f"{account}: deleted {deleted} posts, emptied trash {trash}, "
                f"removed {media} media items"
            )


if __name__ == "__main__":  # pragma: no cover
    main()
