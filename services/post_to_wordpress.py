import json
import logging
from pathlib import Path

from wordpress_client import WordpressClient

logger = logging.getLogger(__name__)

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


def build_paid_block(
    plan_id: str | None,
    paid_title: str | None,
    paid_message: str | None,
    paid_body: str,
) -> str:
    """Return HTML for a WordPress subscribers-only block."""
    # Ensure attributes have default values
    plan_id = plan_id or ""
    paid_title = paid_title or ""
    paid_message = paid_message or ""

    attrs = {
        "planId": plan_id,
        "title": paid_title,
        "message": paid_message,
    }
    attr_json = json.dumps(attrs, ensure_ascii=False)
    block = f"<!-- wp:jetpack/subscribers-only-content {attr_json} -->"
    if paid_title:
        block += f"<h2>{paid_title}</h2>"
    block += f"<p>{paid_body}</p>"
    block += "<!-- /wp:jetpack/subscribers-only-content -->"
    return block


def post_to_wordpress(
    title: str,
    content: str,
    images: list[tuple[Path, str]] | None = None,
    account: str | None = None,
    paid_content: str | None = None,
    paid_title: str | None = None,
    paid_message: str | None = None,
    plan_id: str | None = None,
    categories: list[str] | None = None,
    tags: list[str] | None = None,
) -> dict:
    """Create a WordPress post with optional images."""
    client = WP_CLIENT if account is None else create_wp_client(account)
    if client is None:
        print("WP_CLIENT is None")
        return {"error": "WordPress client unavailable"}

    body = f"<p>{content}</p>"
    featured_id = None
    images = images or []
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
        media_id = uploaded.get("id")
        try:
            if media_id is not None:
                client.update_media_alt_text(media_id, alt_text)
        except Exception as exc:
            logger.warning(
                "Failed to update alt text for media %s: %s", media_id, exc
            )
        body += (
            f'<img src="{url}" alt="{alt_text}" '
            'style="max-width:100%;height:auto;" />'
        )
        if featured_id is None:
            featured_id = media_id

    if paid_content:
        # Determine plan to use: request override or client default
        plan = plan_id or getattr(client, "plan_id", None)
        body += build_paid_block(plan, paid_title, paid_message, paid_content)

    try:
        post_info = client.create_post(
            title,
            body,
            featured_id,
            categories=categories,
            tags=tags,
        )
    except Exception as exc:
        return {"error": str(exc)}
    return {
        "id": post_info.get("id"),
        "link": post_info.get("link"),
        "site": "wordpress",
    }
