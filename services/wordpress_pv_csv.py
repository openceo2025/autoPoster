import csv
from pathlib import Path
from typing import List, Dict

from services.post_to_wordpress import create_wp_client, CONFIG


def export_views(days: int = 30, account: str | None = None) -> None:
    """Export post view counts to CSV for one or all WordPress accounts.

    Parameters
    ----------
    days: int, default 30
        Number of days to retrieve statistics for each post.
    account: str | None, default None
        Specific account identifier from ``config.json``. When ``None``
        all configured accounts are processed.
    """
    accounts: Dict[str, Dict] = CONFIG.get("wordpress", {}).get("accounts", {})
    targets: List[str]
    if account:
        targets = [account] if account in accounts else []
    else:
        targets = list(accounts.keys())

    for acc in targets:
        client = create_wp_client(acc)
        if client is None:
            print(f"[pv_csv] {acc}: WordPress client unavailable")
            continue
        posts = []
        page = 1
        while True:
            items = client.list_posts(page=page, number=100)
            if not items:
                break
            posts.extend(items)
            if len(items) < 100:
                break
            page += 1
        rows = []
        for p in posts:
            try:
                views = client.get_post_views(p["id"], days).get("views")
            except Exception as exc:
                print(f"[pv_csv] {acc}: post {p['id']} views error: {exc}")
                views = None
            rows.append(
                {
                    "id": p.get("id"),
                    "title": p.get("title"),
                    "date": p.get("date"),
                    "url": p.get("url"),
                    "views": views,
                }
            )
        out_file = Path(f"pv_{acc}.csv")
        with out_file.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(
                fh, fieldnames=["id", "title", "date", "url", "views"]
            )
            writer.writeheader()
            writer.writerows(rows)
        print(f"[pv_csv] {acc}: exported {len(rows)} rows to {out_file}")
