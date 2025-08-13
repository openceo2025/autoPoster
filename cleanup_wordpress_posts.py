import json
from pathlib import Path
from typing import Any

from wordpress_client import WordpressClient

CONFIG_PATH = Path("config.json")


def load_config(account_key: str) -> dict[str, Any]:
    """Load configuration for the specified account.

    Parameters
    ----------
    account_key: str
        Key of the WordPress account as defined in ``config.json``.
    """
    with CONFIG_PATH.open() as f:
        cfg = json.load(f)
    accounts = cfg.get("wordpress", {}).get("accounts", {})
    acct_cfg = accounts.get(account_key)
    if not acct_cfg:
        raise ValueError(f"Account '{account_key}' not found in config")
    return {"wordpress": {"accounts": {"default": acct_cfg}}}


def main() -> None:
    account = input("Enter WordPress account identifier: ").strip()
    try:
        config = load_config(account)
    except Exception as exc:  # pragma: no cover - simple CLI error handling
        print(exc)
        return

    client = WordpressClient(config)
    try:
        client.authenticate()
    except Exception as exc:  # pragma: no cover
        print(f"Authentication failed: {exc}")
        return

    posts: list[dict[str, Any]] = []
    page = 1
    while True:
        items = client.list_posts(page=page, number=100)
        if not items:
            break
        posts.extend(items)
        if len(items) < 100:
            break
        page += 1

    if not posts:
        print("No posts found.")
        return

    posts.sort(key=lambda p: p["date"])  # oldest first
    print("Posts (oldest first):")
    for p in posts:
        print(f"{p['id']} - {p['title']} ({p['date']})")

    try:
        count = int(input("How many oldest posts to delete? ").strip())
    except ValueError:  # pragma: no cover
        print("Invalid number")
        return

    for p in posts[:count]:
        try:
            client.delete_post(p["id"])
            print(f"Deleted post {p['id']}")
        except Exception as exc:  # pragma: no cover
            print(f"Failed to delete post {p['id']}: {exc}")

    print("Cleanup complete")


if __name__ == "__main__":  # pragma: no cover
    main()
