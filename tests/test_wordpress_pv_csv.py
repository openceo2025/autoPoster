from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

import services.wordpress_pv_csv as wp_pv


def test_export_views_writes_csv(monkeypatch, tmp_path):
    posts = [
        {"id": 1, "title": "one"},
        {"id": 2, "title": "two"},
    ]

    class DummyClient:
        def list_posts(self, page=1, number=100):
            return posts if page == 1 else []

        def get_post_views(self, post_id, days):  # noqa: D401
            return {"views": post_id * 10}

    client = DummyClient()
    monkeypatch.setattr(wp_pv, "WP_CLIENT", client)
    monkeypatch.setattr(wp_pv, "create_wp_client", lambda account: client)

    result = wp_pv.export_views("acc", days=7, output_dir=tmp_path)
    csv_file = tmp_path / "acc_views.csv"
    assert result == {
        "account": "acc",
        "csv": str(csv_file),
        "posts": 2,
    }
    content = csv_file.read_text().splitlines()
    assert content == [
        "post_id,title,views",
        "1,one,10",
        "2,two,20",
    ]


def test_export_views_client_error(monkeypatch):
    monkeypatch.setattr(wp_pv, "create_wp_client", lambda account: None)
    result = wp_pv.export_views("missing")
    assert result["error"] == "WordPress client unavailable"
