from pathlib import Path
import sys

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
                return {"search_terms": ["foo", "bar"]}

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
    assert resp.json() == {"terms": ["foo", "bar"]}
    assert (
        captured["url"]
        == "https://public-api.wordpress.com/rest/v1.1/sites/mysite/stats/search-terms"
    )
    assert captured["params"] == {"days": 7}

