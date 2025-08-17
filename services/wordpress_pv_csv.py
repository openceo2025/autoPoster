from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from services.post_to_wordpress import create_wp_client


def export_views(accounts: dict, days: int, out_dir: Path) -> list[Path]:
    """Export daily page views for posts on multiple WordPress sites.

    Parameters
    ----------
    accounts: dict
        Mapping of account names to configuration dictionaries. The account
        name is passed to ``create_wp_client`` to initialize an authenticated
        ``WordpressClient``.
    days: int
        Number of days of statistics to retrieve for each post.
    out_dir: Path
        Directory where CSV files will be written.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y%m%d")
    generated: list[Path] = []

    for account, cfg in accounts.items():
        client = create_wp_client(account)
        if client is None:
            continue
        site = cfg.get("site") or getattr(client, "site", account)

        # fetch all posts across pages
        posts: list[dict] = []
        page = 1
        while True:
            try:
                page_posts = client.list_posts(page=page, number=100)
            except Exception:
                break
            if not page_posts:
                break
            posts.extend(page_posts)
            page += 1

        rows: list[list[str | int]] = []
        for post in posts:
            try:
                view_list = client.get_daily_views(post["id"], days)
            except Exception:
                view_list = []
            views = list(view_list)
            if len(views) < days:
                views.extend([0] * (days - len(views)))
            row = [site, post["id"], post.get("title", "")]
            row.extend(views[:days])
            rows.append(row)

        csv_path = out_dir / f"wp_pv_{site}_{today}.csv"
        header = ["site", "post_id", "title"] + [f"pv_day{i+1}" for i in range(days)]
        with csv_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(header)
            for row in rows:
                writer.writerow(row)
        generated.append(csv_path)

    return generated
