import json
from pathlib import Path
from typing import Any, Dict, List

from services.post_to_wordpress import create_wp_client, CONFIG


def cleanup_posts(account: str, keep_latest: int) -> Dict[str, Any]:
    """Remove old posts and unattached media for a WordPress account.

    Parameters
    ----------
    account: str
        Account identifier from ``config.json``.
    keep_latest: int
        Number of most recent posts to retain.
    """
    accounts = CONFIG.get("wordpress", {}).get("accounts", {})
    if account not in accounts:
        return {"account": account, "error": "Account not found"}

    client = create_wp_client(account)
    if client is None:
        return {"account": account, "error": "WordPress client unavailable"}

    posts: List[Dict[str, Any]] = []
    page = 1
    while True:
        items = client.list_posts(page=page, number=100)
        if not items:
            break
        posts.extend(items)
        if len(items) < 100:
            break
        page += 1

    posts.sort(key=lambda p: p["date"])
    delete_count = len(posts) - keep_latest
    if delete_count <= 0:
        return {"account": account, "deleted_posts": [], "deleted_media": 0}
    print(f"[cleanup] {account}: fetched {len(posts)} posts")
    print(f"[cleanup] {account}: deleting {delete_count} posts")

    deleted: List[int] = []
    errors: Dict[str, str] = {}
    for p in posts[:delete_count]:
        try:
            client.delete_post(p["id"])
            deleted.append(p["id"])
        except Exception as exc:
            errors[str(p["id"])] = str(exc)
    print(f"[cleanup] {account}: deleted {len(deleted)} posts")

    try:
        print(f"[cleanup] {account}: emptying trash")
        trash = client.empty_trash()
        trash_count = len(trash) if isinstance(trash, list) else 0
    except Exception:
        trash_count = 0
    print(f"[cleanup] {account}: trash emptied {trash_count}")

    info = client.get_site_info(fields="icon,logo")
    protected: set[str] = set()
    for key in ("icon", "logo"):
        obj = info.get(key) or {}
        for val in obj.values():
            if isinstance(val, str):
                protected.add(val)

    removed = 0
    page = 1
    print(f"[cleanup] {account}: removing unattached media")
    while True:
        media = client.list_media(post_id=0, page=page, number=100)
        if not media:
            break
        for item in media:
            url = item.get("URL")
            if url and url in protected:
                continue
            try:
                client.delete_media(item["ID"])
                removed += 1
            except Exception:
                pass
        if len(media) < 100:
            break
        page += 1
    print(f"[cleanup] {account}: removed {removed} media items")

    return {
        "account": account,
        "deleted_posts": deleted,
        "errors": errors,
        "trash_emptied": trash_count,
        "deleted_media": removed,
    }
