import sys
from pathlib import Path

import pytest
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


def test_client_list_posts(monkeypatch):
    client = wordpress_client.WordpressClient({"wordpress": {"site": "mysite"}})
    captured = {}

    def fake_get(url, headers=None, params=None):
        captured["url"] = url
        captured["params"] = params
        return DummyResp(
            {
                "posts": [
                    {
                        "ID": 1,
                        "title": "T1",
                        "date": "2020-01-01T00:00:00",
                        "URL": "http://p1",
                    }
                ]
            }
        )

    monkeypatch.setattr(client.session, "get", fake_get)
    posts = client.list_posts(page=2, number=5)
    assert (
        captured["url"]
        == "https://public-api.wordpress.com/rest/v1.1/sites/mysite/posts"
    )
    assert captured["params"] == {"page": 2, "number": 5}
    assert posts == [
        {
            "id": 1,
            "title": "T1",
            "date": "2020-01-01T00:00:00",
            "url": "http://p1",
        }
    ]


def test_client_list_posts_status(monkeypatch):
    client = wordpress_client.WordpressClient({"wordpress": {"site": "mysite"}})
    captured = {}

    def fake_get(url, headers=None, params=None):
        captured["params"] = params
        return DummyResp({"posts": []})

    monkeypatch.setattr(client.session, "get", fake_get)
    client.list_posts(status="trash")
    assert captured["params"] == {"page": 1, "number": 10, "status": "trash"}


def test_wordpress_posts_endpoint(monkeypatch):
    captured = {}

    def fake_get(url, headers=None, params=None):
        captured["url"] = url
        captured["params"] = params
        return DummyResp(
            {
                "posts": [
                    {
                        "ID": 1,
                        "title": "T1",
                        "date": "2020-01-01T00:00:00",
                        "URL": "http://p1",
                    }
                ]
            }
        )

    cfg = {"wordpress": {"accounts": {"default": {"site": "mysite"}}}}
    client = wordpress_client.WordpressClient(cfg)
    client.access_token = "tok"
    client.session.headers.update({"Authorization": "Bearer tok"})
    monkeypatch.setattr(client.session, "get", fake_get)

    monkeypatch.setattr(wp_posts, "WP_CLIENT", client)
    monkeypatch.setattr(wp_posts, "create_wp_client", lambda account=None: client)

    app = TestClient(server.app)
    resp = app.get(
        "/wordpress/posts",
        params={"account": "acc", "page": 2, "number": 5},
    )
    assert resp.status_code == 200
    assert resp.json() == {
        "posts": [
            {
                "id": 1,
                "title": "T1",
                "date": "2020-01-01T00:00:00",
                "url": "http://p1",
            }
        ]
    }
    assert (
        captured["url"]
        == "https://public-api.wordpress.com/rest/v1.1/sites/mysite/posts"
    )
    assert captured["params"] == {"page": 2, "number": 5}


def test_service_list_posts(monkeypatch):
    class DummyClient:
        def list_posts(self, page=1, number=10):
            return [{"id": 1}]

    dummy = DummyClient()
    monkeypatch.setattr(wp_posts, "WP_CLIENT", dummy)
    monkeypatch.setattr(wp_posts, "create_wp_client", lambda account=None: dummy)
    res = wp_posts.list_posts(None, 1, 10)
    assert res == {"posts": [{"id": 1}]}


@pytest.mark.parametrize("page,number", [(0, 1), (1, 0)])
def test_wordpress_posts_invalid_params(page, number):
    app = TestClient(server.app)
    resp = app.get("/wordpress/posts", params={"page": page, "number": number})
    assert resp.status_code == 422
