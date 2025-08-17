from pathlib import Path
import sys

from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1]))
import server


def test_wordpress_pv_csv_endpoint(monkeypatch, tmp_path):
    captured = {}

    def fake_export(accounts, days, out_dir):
        captured["accounts"] = accounts
        captured["days"] = days
        captured["out_dir"] = out_dir

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
    assert captured["accounts"] == cfg["wordpress"]["accounts"]
    assert captured["days"] == 5
    assert captured["out_dir"] == tmp_path
