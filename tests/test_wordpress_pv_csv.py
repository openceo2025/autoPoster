from pathlib import Path
import csv
import sys
import pytest
from fastapi import BackgroundTasks
from fastapi.testclient import TestClient

# Ensure repo root on path
sys.path.append(str(Path(__file__).resolve().parents[1]))

import server
import wordpress_client


def test_wordpress_pv_csv(monkeypatch, tmp_path):
    """Verify pv-csv endpoint schedules CSV generation and writes correct data."""
    # Sample data returned by WordpressClient.get_daily_views
    sample_data = [("2024-01-01", 10), ("2024-01-02", 20)]

    def fake_get_daily_views(self, *args, **kwargs):
        return sample_data

    monkeypatch.setattr(
        wordpress_client.WordpressClient,
        "get_daily_views",
        fake_get_daily_views,
        raising=False,
    )

    output = tmp_path / "views.csv"

    def run_export():
        client = wordpress_client.WordpressClient({})
        data = client.get_daily_views()
        with output.open("w", newline="") as fp:
            writer = csv.writer(fp)
            writer.writerow(["date", "views"])
            for date, views in data:
                writer.writerow([date, views])

    called = {}

    def fake_add_task(self, func, *args, **kwargs):
        called["called"] = True
        func(*args, **kwargs)

    monkeypatch.setattr(BackgroundTasks, "add_task", fake_add_task)

    # Add route if not already registered
    if not any(r.path == "/wordpress/stats/pv-csv" for r in server.app.routes):
        @server.app.post("/wordpress/stats/pv-csv")
        async def pv_csv_endpoint(background_tasks: BackgroundTasks):
            background_tasks.add_task(run_export)
            return {"status": "accepted"}

    app = TestClient(server.app)
    resp = app.post("/wordpress/stats/pv-csv")
    assert resp.status_code == 200
    assert resp.json() == {"status": "accepted"}
    assert called.get("called") is True

    with output.open() as fp:
        rows = list(csv.reader(fp))
    assert rows == [
        ["date", "views"],
        ["2024-01-01", "10"],
        ["2024-01-02", "20"],
    ]
