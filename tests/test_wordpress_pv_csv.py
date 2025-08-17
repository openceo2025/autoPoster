import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import server
from fastapi.testclient import TestClient


def test_wordpress_pv_csv_endpoint(monkeypatch):
    called = {}

    def fake_export_views(days: int = 30, account: str | None = None) -> None:
        called["days"] = days
        called["account"] = account

    monkeypatch.setattr(server.wordpress_pv_csv, "export_views", fake_export_views)

    app = TestClient(server.app)
    resp = app.post(
        "/wordpress/stats/pv-csv",
        params={"days": 5, "account": "acc"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"status": "accepted"}
    assert called == {"days": 5, "account": "acc"}
