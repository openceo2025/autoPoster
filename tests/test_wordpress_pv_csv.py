from __future__ import annotations

import csv
from pathlib import Path
import sys

from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1]))

import server
from wordpress_client import WordpressClient
import services.wordpress_pv_csv as wp_pv_csv


def test_export_views_generates_csv(monkeypatch, tmp_path):
    posts = [{"id": 1, "title": "Post 1"}, {"id": 2, "title": "Post 2"}]

    def fake_list_posts(self, page=1, number=100):
        return posts if page == 1 else []

    def fake_get_daily_views(self, post_ids, day):  # noqa: ARG001
        return {1: 3, 2: 5}

    monkeypatch.setattr(WordpressClient, "list_posts", fake_list_posts)
    monkeypatch.setattr(WordpressClient, "get_daily_views", fake_get_daily_views)

    def fake_create_wp_client(account):  # noqa: ARG001
        cfg = {"wordpress": {"accounts": {"dummy": {"site": "mysite"}}}}
        client = WordpressClient(cfg)
        client.site = "mysite"
        return client

    monkeypatch.setattr(wp_pv_csv, "create_wp_client", fake_create_wp_client)

    results = wp_pv_csv.export_views({"dummy": {}}, 1, tmp_path)
    csv_path = tmp_path / "views.csv"
    assert results == {"file": str(csv_path)}

    with csv_path.open(encoding="utf-8") as fh:
        rows = list(csv.reader(fh))

    assert rows[0] == ["account", "site", "post_id", "title", "pv_day1"]
    assert rows[1] == ["dummy", "mysite", "1", "Post 1", "3"]
    assert rows[2] == ["dummy", "mysite", "2", "Post 2", "5"]


def test_wordpress_pv_csv_endpoint(monkeypatch, tmp_path):
    called: dict[str, object] = {}

    def fake_add_task(self, func, *args, **kwargs):  # noqa: ARG001
        called["func"] = func
        called["args"] = args
        called["kwargs"] = kwargs

    monkeypatch.setattr(server.BackgroundTasks, "add_task", fake_add_task)

    def fake_export(accounts, days, out_dir):  # noqa: ARG001
        return None

    monkeypatch.setattr(server, "service_export_views", fake_export)
    cfg = {"wordpress": {"accounts": {"acc1": {}, "acc2": {}}}}
    monkeypatch.setattr(server, "CONFIG", cfg, raising=False)

    client = TestClient(server.app)
    resp = client.post(
        "/wordpress/stats/pv-csv",
        params={"days": 5, "out_dir": str(tmp_path)},
    )
    assert resp.status_code == 200
    assert resp.json() == {"status": "accepted"}
    assert called["func"] is fake_export
    assert called["args"] == (cfg["wordpress"]["accounts"], 5, tmp_path)
