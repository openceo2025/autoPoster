"""Export WordPress page view statistics to CSV."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict

from services.post_to_wordpress import create_wp_client, WP_CLIENT


def export_views(
    account: str, days: int = 30, output_dir: str | Path = "."
) -> Dict[str, Any]:
    """Export view counts for all posts of the given account.

    Parameters
    ----------
    account: str
        Account identifier from ``config.json``.
    days: int
        Number of days of view statistics to retrieve per post.
    output_dir: str | Path
        Directory where the CSV file will be written.
    """
    client = WP_CLIENT if account is None else create_wp_client(account)
    if client is None:
        return {"account": account, "error": "WordPress client unavailable"}

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    csv_path = output / f"{account}_views.csv"

    posts = []
    page = 1
    while True:
        try:
            items = client.list_posts(page=page, number=100)
        except Exception as exc:
            return {"account": account, "error": str(exc)}
        if not items:
            break
        posts.extend(items)
        if len(items) < 100:
            break
        page += 1

    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["post_id", "title", "views"])
        for post in posts:
            pid = post.get("id")
            title = post.get("title")
            try:
                data = client.get_post_views(pid, days)
                views = data.get("views")
            except Exception as exc:  # pragma: no cover - best effort
                views = f"error: {exc}"
            writer.writerow([pid, title, views])

    return {"account": account, "csv": str(csv_path), "posts": len(posts)}
