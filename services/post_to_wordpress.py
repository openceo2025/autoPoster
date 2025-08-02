import json
from pathlib import Path
from typing import List

from wordpress_client import WordpressClient

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.json"

if CONFIG_PATH.exists():
    with CONFIG_PATH.open() as fh:
        CONFIG = json.load(fh)
else:
    CONFIG = {}


def create_wp_client(account: str | None = None) -> WordpressClient | None:
    """Initialize a WordpressClient using the specified account."""
    wp_cfg = CONFIG.get("wordpress", {})
    accounts = wp_cfg.get("accounts") or {}
    if not accounts:
        print("No WordPress accounts configured")
        return None

    acct = None
    if account:
        acct = accounts.get(account)
        if not acct:
            print(f"No WordPress account configured for {account}")
            return None
    elif "default" in accounts:
        acct = accounts["default"]
    else:
        acct = next(iter(accounts.values()))

    cfg = {"wordpress": {"accounts": {"default": acct}}}

    try:
        client = WordpressClient(cfg)
        client.authenticate()
        return client
    except Exception as exc:
        print(f"Failed to init WordPress client: {exc}")
        print(f"CONFIG used for WordpressClient: {cfg}")
        return None


WP_CLIENT = create_wp_client()


def post_to_wordpress(
    title: str,
    content: str,
    images: List[Path] = [],
    account: str | None = None,
) -> dict:
    """Create a WordPress post with optional images."""
    client = WP_CLIENT if account is None else create_wp_client(account)
    if client is None:
        print("WP_CLIENT is None")
        return {"error": "WordPress client unavailable"}

    body = f"<p>{content}</p>"
    featured_id = None
    for img in images:
        if not img.exists():
            return {"error": f"Image file not found: {img}"}
        try:
            print(f"Uploading {img} ({img.stat().st_size} bytes)")
            with img.open("rb") as fh:
                uploaded = client.upload_media(fh.read(), img.name)
            print(f"Uploaded {img} -> {uploaded}")
        except Exception as exc:
            print(f"Failed image {img}: {exc}")
            raise
        url = uploaded.get("url")
        body += f'<img src="{url}" />'
        if featured_id is None:
            featured_id = uploaded.get("id")

    try:
        post_info = client.create_post(title, body, featured_id)
    except Exception as exc:
        return {"error": str(exc)}

    return post_info
