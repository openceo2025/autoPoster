from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, Any

from services.post_to_wordpress import create_wp_client


def export_views(accounts: dict, days: int, out_dir: Path) -> Dict[str, Any]:
    """Export per-post view counts for multiple WordPress accounts.

    Parameters
    ----------
    accounts: dict
        Mapping of account name to configuration. Only the keys are used to
        instantiate clients via :func:`create_wp_client`.
    days: int
        Number of most recent days to include in the CSV output.
    out_dir: Path
        Destination directory for the generated CSV file.

    Returns
    -------
    dict
        Mapping containing the path to the generated CSV file.
    """

    out_dir.mkdir(parents=True, exist_ok=True)

    # Precompute the list of days in descending order (most recent first)
    day_strs = [
        (date.today() - timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range(days)
    ]

    csv_path = out_dir / "views.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        header = ["account", "site", "post_id", "title"] + [
            f"pv_day{i + 1}" for i in range(days)
        ]
        writer.writerow(header)

        for account in accounts.keys():
            client = create_wp_client(account)
            if client is None:
                continue

            posts: list[dict] = []
            page = 1
            while True:
                try:
                    items = client.list_posts(page=page, number=100)
                except Exception:  # pragma: no cover - network errors
                    items = []
                if not items:
                    break
                posts.extend(items)
                if len(items) < 100:
                    break
                page += 1

            if not posts:
                continue

            post_ids = [p["id"] for p in posts]
            views: dict[int, list[int]] = {pid: [0] * days for pid in post_ids}

            for idx, day_str in enumerate(day_strs):
                try:
                    daily = client.get_daily_views(post_ids, day_str)
                except Exception:  # pragma: no cover - network errors
                    daily = {}
                for pid, count in daily.items():
                    if pid in views:
                        views[pid][idx] = count

            for p in posts:
                row = [account, client.site, p.get("id"), p.get("title")]
                row.extend(views.get(p.get("id"), [0] * days))
                writer.writerow(row)

    return {"file": str(csv_path)}
