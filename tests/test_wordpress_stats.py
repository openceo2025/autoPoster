from pathlib import Path
import sys
import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))
import server
import wordpress_client
import services.wordpress_stats as wp_stats
from fastapi.testclient import TestClient


def test_wordpress_views_endpoint(monkeypatch):
    captured = {}

    def fake_get(url, headers=None, params=None):
        captured["url"] = url
        captured["params"] = params
        class DummyResp:
            status_code = 200
            def raise_for_status(self):
                pass
            def json(self):
                return {"views": [1, 2, 3]}
        return DummyResp()

    cfg = {"wordpress": {"accounts": {"default": {"site": "mysite"}}}}
    client = wordpress_client.WordpressClient(cfg)
    client.access_token = "tok"
    client.session.headers.update({"Authorization": "Bearer tok"})
    monkeypatch.setattr(client.session, "get", fake_get)

    monkeypatch.setattr(wp_stats, "WP_CLIENT", client)
    monkeypatch.setattr(wp_stats, "create_wp_client", lambda account=None: client)

    app = TestClient(server.app)
    resp = app.get(
        "/wordpress/stats/views",
        params={"account": "acc", "post_id": 10, "days": 5},
    )
    assert resp.status_code == 200
    assert resp.json() == {"views": [1, 2, 3]}
    assert (
        captured["url"]
        == "https://public-api.wordpress.com/rest/v1.1/sites/mysite/stats/post/10"
    )
    assert captured["params"] == {"unit": "day", "quantity": 5}


def test_wordpress_views_no_data(monkeypatch):
    captured = {}

    def fake_get(url, headers=None, params=None):
        captured["url"] = url
        captured["params"] = params
        class DummyResp:
            status_code = 200

            def raise_for_status(self):
                pass

            def json(self):
                return {}

        return DummyResp()

    cfg = {"wordpress": {"accounts": {"default": {"site": "mysite"}}}}
    client = wordpress_client.WordpressClient(cfg)
    client.access_token = "tok"
    client.session.headers.update({"Authorization": "Bearer tok"})
    monkeypatch.setattr(client.session, "get", fake_get)

    monkeypatch.setattr(wp_stats, "WP_CLIENT", client)
    monkeypatch.setattr(wp_stats, "create_wp_client", lambda account=None: client)

    app = TestClient(server.app)
    resp = app.get(
        "/wordpress/stats/views",
        params={"account": "acc", "post_id": 10, "days": 5},
    )
    assert resp.status_code == 200
    assert resp.json() == {"error": "No view data returned"}


def test_wordpress_search_terms_endpoint(monkeypatch):
    captured = {}

    def fake_get(url, headers=None, params=None):
        captured["url"] = url
        captured["params"] = params
        class DummyResp:
            status_code = 200

            def raise_for_status(self):
                pass

            def json(self):
                return {"search_terms": [["foo", 4], ["bar", 2]]}

        return DummyResp()

    cfg = {"wordpress": {"accounts": {"default": {"site": "mysite"}}}}
    client = wordpress_client.WordpressClient(cfg)
    client.access_token = "tok"
    client.session.headers.update({"Authorization": "Bearer tok"})
    monkeypatch.setattr(client.session, "get", fake_get)

    monkeypatch.setattr(wp_stats, "WP_CLIENT", client)
    monkeypatch.setattr(wp_stats, "create_wp_client", lambda account=None: client)

    app = TestClient(server.app)
    resp = app.get(
        "/wordpress/stats/search-terms",
        params={"account": "acc", "days": 7},
    )
    assert resp.status_code == 200
    assert resp.json() == {
        "terms": [
            {"term": "foo", "views": 4},
            {"term": "bar", "views": 2},
        ]
    }
    assert (
        captured["url"]
        == "https://public-api.wordpress.com/rest/v1.1/sites/mysite/stats/search-terms"
    )
    assert captured["params"] == {"days": 7}


@pytest.mark.parametrize("days", [0, -1])
def test_wordpress_views_invalid_days(days):
    app = TestClient(server.app)
    resp = app.get(
        "/wordpress/stats/views",
        params={"post_id": 1, "days": days},
    )
    assert resp.status_code == 422


@pytest.mark.parametrize("days", [0, -1])
def test_wordpress_search_terms_invalid_days(days):
    app = TestClient(server.app)
    resp = app.get(
        "/wordpress/stats/search-terms",
        params={"days": days},
    )
    assert resp.status_code == 422

