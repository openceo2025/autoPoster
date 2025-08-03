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
    images: List[tuple[Path, str]] = [],
    account: str | None = None,
    paid_content: str | None = None,
) -> dict:
    """Create a WordPress post with optional images."""
    client = WP_CLIENT if account is None else create_wp_client(account)
    if client is None:
        print("WP_CLIENT is None")
        return {"error": "WordPress client unavailable"}

    body = f"<p>{content}</p>"
    featured_id = None
    for img_path, filename in images:
        if not img_path.exists():
            return {"error": f"Image file not found: {img_path}"}
        try:
            print(
                f"Uploading {img_path} ({img_path.stat().st_size} bytes) as {filename}"
            )
            with img_path.open("rb") as fh:
                uploaded = client.upload_media(fh.read(), filename)
            print(f"Uploaded {img_path} -> {uploaded}")
        except Exception as exc:
            print(f"Failed image {img_path}: {exc}")
            raise
        url = uploaded.get("url")
        if not url:
            print(f"No URL returned for {img_path}, skipping image tag")
            continue
        alt_text = uploaded.get("alt") or uploaded.get("title") or Path(filename).stem
        body += f'<img src="{url}" alt="{alt_text}" />'
        if featured_id is None:
            featured_id = uploaded.get("id")

    if paid_content:
        body += (
            "<!-- wp:premium-content/paid-block -->"
            f"<p>{paid_content}</p>"
            "<!-- /wp:premium-content/paid-block -->"
        )

    try:
        post_info = client.create_post(title, body, featured_id)
    except Exception as exc:
        return {"error": str(exc)}

    return post_info
