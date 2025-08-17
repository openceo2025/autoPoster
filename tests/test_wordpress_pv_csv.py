from __future__ import annotations

import csv
from pathlib import Path
from datetime import datetime
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from services.wordpress_pv_csv import export_views


class DummyClient:
    def __init__(self):
        self.list_calls = []
        self.views_calls = []

    def list_posts(self, page=1, number=100):
        self.list_calls.append(page)
        if page == 1:
            return [
                {"id": 1, "title": "Post1"},
                {"id": 2, "title": "Post2"},
            ]
        return []

    def get_daily_views(self, post_id, days):
        self.views_calls.append((post_id, days))
        return list(range(1, days + 1))


def test_export_views_writes_csv(monkeypatch, tmp_path):
    client = DummyClient()
    monkeypatch.setattr(
        "services.wordpress_pv_csv.create_wp_client", lambda account: client
    )
    accounts = {"acc": {"site": "mysite"}}
    paths = export_views(accounts, 7, tmp_path)
    assert len(paths) == 1
    csv_path = paths[0]
    assert csv_path.exists()
    expected_prefix = f"wp_pv_mysite_{datetime.now().strftime('%Y%m%d')}"
    assert csv_path.name.startswith(expected_prefix)
    with csv_path.open() as fh:
        rows = list(csv.reader(fh))
    header = ["site", "post_id", "title"] + [f"pv_day{i+1}" for i in range(7)]
    assert rows[0] == header
    assert rows[1][0:3] == ["mysite", "1", "Post1"]
    assert rows[2][0:3] == ["mysite", "2", "Post2"]
    assert rows[1][3:] == [str(i) for i in range(1, 8)]
    assert rows[2][3:] == [str(i) for i in range(1, 8)]
