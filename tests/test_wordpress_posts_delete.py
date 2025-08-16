import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.append(str(Path(__file__).resolve().parents[1]))

import server
import wordpress_client
import services.wordpress_posts as wp_posts


class DummyResp:
    def __init__(self, data):
        self._data = data
        self.status_code = 200
        self.text = "ok"
        self.headers = {}

    def json(self):
        return self._data

    def raise_for_status(self):
        pass


def test_client_delete_post(monkeypatch):
    client = wordpress_client.WordpressClient({"wordpress": {"site": "mysite"}})
    captured = {}

    def fake_post(url, params=None, **kwargs):
        captured["url"] = url
        captured["params"] = params
        return DummyResp({"ID": 5})

    monkeypatch.setattr(client.session, "post", fake_post)
    deleted = client.delete_post(5)
    assert (
        captured["url"]
        == "https://public-api.wordpress.com/rest/v1.1/sites/mysite/posts/5/delete"
    )
    assert captured["params"] is None
    assert deleted == 5


def test_client_delete_post_force(monkeypatch):
    client = wordpress_client.WordpressClient({"wordpress": {"site": "mysite"}})
    captured = {}

    def fake_post(url, params=None, **kwargs):
        captured["url"] = url
        captured["params"] = params
        return DummyResp({"ID": 9})

    monkeypatch.setattr(client.session, "post", fake_post)
    deleted = client.delete_post(9, permanent=True)
    assert (
        captured["url"]
        == "https://public-api.wordpress.com/rest/v1.1/sites/mysite/posts/9/delete"
    )
    assert captured["params"] == {"force": 1}
    assert deleted == 9


def test_service_delete_posts(monkeypatch):
    class DummyClient:
        def __init__(self):
            self.called = []

        def delete_post(self, pid):
            if pid == 2:
                raise RuntimeError("nope")
            self.called.append(pid)
            return pid

    dummy = DummyClient()
    monkeypatch.setattr(wp_posts, "WP_CLIENT", dummy)
    monkeypatch.setattr(wp_posts, "create_wp_client", lambda account=None: dummy)

    res = wp_posts.delete_posts(None, [1, 2, 3])
    assert res == {"deleted": [1, 3], "errors": {"2": "nope"}}
    assert dummy.called == [1, 3]


def test_delete_posts_endpoint(monkeypatch):
    class DummyClient:
        def __init__(self):
            self.deleted = []

        def delete_post(self, pid):
            self.deleted.append(pid)
            return pid

    dummy = DummyClient()
    monkeypatch.setattr(wp_posts, "WP_CLIENT", dummy)
    monkeypatch.setattr(wp_posts, "create_wp_client", lambda account=None: dummy)

    app = TestClient(server.app)
    resp = app.delete(
        "/wordpress/posts", params=[("ids", "1"), ("ids", "2"), ("account", "acc")]
    )
    assert resp.status_code == 200
    assert resp.json() == {"deleted": [1, 2], "errors": {}, "success": 2, "failed": 0}
    assert dummy.deleted == [1, 2]


def test_client_empty_trash(monkeypatch):
    client = wordpress_client.WordpressClient({"wordpress": {"site": "mysite"}})
    calls = {"list": [], "deleted": []}

    def fake_list_posts(page=1, number=100, status=None):
        calls["list"].append({"page": page, "number": number, "status": status})
        # Return some trashed posts on first call, then empty list to stop
        if not calls["deleted"]:
            return [{"id": 1}, {"id": 2}]
        return []

    def fake_delete_post(pid, permanent=False):
        calls["deleted"].append({"id": pid, "permanent": permanent})
        return pid

    monkeypatch.setattr(client, "list_posts", fake_list_posts)
    monkeypatch.setattr(client, "delete_post", fake_delete_post)
    res = client.empty_trash()
    assert calls["list"] == [{"page": 1, "number": 100, "status": "trash"}]
    assert calls["deleted"] == [{"id": 1, "permanent": True}, {"id": 2, "permanent": True}]
    assert res == [1, 2]
