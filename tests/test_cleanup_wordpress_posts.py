from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

import services.cleanup_wordpress_posts as wp_cleanup
import services.post_to_wordpress as wp_service
import server
from fastapi.testclient import TestClient


class DummyClient:
    def __init__(self):
        self.posts = [
            {"id": 1, "date": "2020-01-01"},
            {"id": 2, "date": "2020-01-02"},
            {"id": 3, "date": "2020-01-03"},
            {"id": 4, "date": "2020-01-04"},
        ]
        self.media = [{"ID": 10, "URL": "m1"}, {"ID": 11, "URL": "m2"}]
        self.deleted_posts = []
        self.deleted_media = []

    def list_posts(self, page=1, number=100):
        return self.posts if page == 1 else []

    def delete_post(self, pid):
        self.deleted_posts.append(pid)

    def empty_trash(self):
        return self.deleted_posts

    def get_site_info(self, fields="icon,logo"):
        return {}

    def list_media(self, post_id=0, page=1, number=100):
        return self.media if page == 1 else []

    def delete_media(self, mid):
        self.deleted_media.append(mid)


def test_cleanup_service(monkeypatch):
    dummy = DummyClient()
    monkeypatch.setattr(wp_cleanup, "create_wp_client", lambda account: dummy)
    cfg = {"wordpress": {"accounts": {"acc": {}}}}
    wp_service.CONFIG = cfg
    wp_cleanup.CONFIG = cfg
    result = wp_cleanup.cleanup_posts("acc", 2)
    assert result["account"] == "acc"
    assert result["deleted_posts"] == [1, 2]
    assert result["deleted_media"] == 2


def test_cleanup_endpoint(monkeypatch):
    called: list[tuple[str, int]] = []

    def fake_task(identifier: str, keep_latest: int) -> None:
        called.append((identifier, keep_latest))

    monkeypatch.setattr(server, "_run_cleanup", fake_task)
    app = TestClient(server.app)
    resp = app.post(
        "/wordpress/cleanup",
        json={
            "items": [
                {"identifier": "a1", "keep_latest": 1},
                {"identifier": "a2", "keep_latest": 2},
            ]
        },
    )
    assert resp.status_code == 200
    assert resp.json() == {"status": "accepted"}
    # Background tasks run after response in TestClient
    assert called == [("a1", 1), ("a2", 2)]
