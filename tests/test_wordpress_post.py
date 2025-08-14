import base64
import json

import pytest
from fastapi.testclient import TestClient

import requests
import server
import services.post_to_wordpress as wp_service
import tempfile
from pathlib import Path


class DummyResponse:
    def __init__(self, data, status_code=200):
        self._data = data
        self.status_code = status_code
        self.text = json.dumps(data)

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"status {self.status_code}")


def make_client(monkeypatch, config):
    """Setup server with given config and patch requests.post."""
    calls = {"uploads": [], "post": None, "alt_updates": []}

    def fake_post(url, *args, **kwargs):
        if url.endswith("oauth2/token"):
            return DummyResponse({"access_token": "tok"})
        if url.endswith("/media/new"):
            calls["uploads"].append(kwargs["files"]["media[]"])
            return DummyResponse({"media": [{"id": 1, "source_url": "http://img"}]})
        if "/media/1" in url:
            calls["alt_updates"].append(kwargs.get("json"))
            return DummyResponse({"id": 1, **(kwargs.get("json") or {})})
        if url.endswith("/posts/new"):
            calls["post"] = kwargs.get("json")
            return DummyResponse({"ID": 10, "URL": "http://post"})
        raise AssertionError(f"Unexpected URL {url}")

    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.setattr(requests.Session, "post", lambda self, url, *a, **kw: fake_post(url, *a, **kw))

    monkeypatch.setattr(server, "CONFIG", config, raising=False)
    monkeypatch.setattr(wp_service, "CONFIG", config, raising=False)
    monkeypatch.setattr(wp_service, "WP_CLIENT", None, raising=False)

    monkeypatch.setattr(
        server,
        "WORDPRESS_ACCOUNT_ERRORS",
        server.validate_wordpress_accounts(config),
        raising=False,
    )
    monkeypatch.setattr(
        server,
        "WORDPRESS_CLIENTS",
        server.create_wordpress_clients(),
        raising=False,
    )
    return TestClient(server.app), calls


def test_wordpress_post_success(monkeypatch):
    cfg = {
        "wordpress": {
            "accounts": {
                "acc": {
                    "site": "mysite", "client_id": "id", "client_secret": "sec",
                    "username": "user", "password": "pwd",
                }
            }
        }
    }
    client, calls = make_client(monkeypatch, cfg)
    data = b"imgdata"
    encoded = base64.b64encode(data).decode()
    resp = client.post(
        "/wordpress/post",
        json={
            "account": "acc",
            "title": "T",
            "content": "C",
            "media": [{"filename": "img.png", "data": encoded, "alt": "ALT"}],
            "paid_content": "Paid",
            "paid_title": "PT",
            "paid_message": "Msg",
            "plan_id": "p1",
        },
    )
    assert resp.status_code == 200
    assert resp.json() == {"id": 10, "link": "http://post", "site": "wordpress"}
    assert len(calls["uploads"]) == 1
    filename, content = calls["uploads"][0]
    assert filename == "img.png"
    assert content == data
    payload = calls["post"]
    assert payload["featured_image"] == 1
    assert "http://img" in payload["content"]
    assert calls["alt_updates"][0]["alt_text"] == "ALT"
    assert 'alt="ALT"' in payload["content"]
    assert payload["title"] == "T"
    assert "wp:jetpack/subscribers-only-content" in payload["content"]
    assert "<h2>PT</h2>" in payload["content"]
    assert "<p>Paid</p>" in payload["content"]
    assert '"message": "Msg"' in payload["content"]
    assert '"title": "PT"' in payload["content"]
    assert '"planId": "p1"' in payload["content"]
    assert "paid_content" not in payload


def test_wordpress_post_with_categories_tags(monkeypatch):
    cfg = {
        "wordpress": {
            "accounts": {
                "acc": {
                    "site": "mysite",
                    "client_id": "id",
                    "client_secret": "sec",
                    "username": "user",
                    "password": "pwd",
                }
            }
        }
    }
    client, calls = make_client(monkeypatch, cfg)
    resp = client.post(
        "/wordpress/post",
        json={
            "account": "acc",
            "title": "T",
            "content": "C",
            "categories": ["News", "Tech"],
            "tags": ["python", "fastapi"],
        },
    )
    assert resp.status_code == 200
    payload = calls["post"]
    assert payload["categories"] == "News,Tech"
    assert payload["tags"] == "python,fastapi"


def test_wordpress_post_paid_block(monkeypatch):
    cfg = {
        "wordpress": {
            "accounts": {
                "acc": {
                    "site": "mysite",
                    "client_id": "id",
                    "client_secret": "sec",
                    "username": "user",
                    "password": "pwd",
                    "plan_id": "cfg",
                }
            }
        }
    }
    client, calls = make_client(monkeypatch, cfg)
    resp = client.post(
        "/wordpress/post",
        json={
            "account": "acc",
            "title": "T",
            "content": "C",
            "paid_content": "Secret",
            "paid_title": "Hidden",
            "paid_message": "M",
        },
    )
    assert resp.status_code == 200
    payload = calls["post"]
    assert payload["title"] == "T"
    assert "wp:jetpack/subscribers-only-content" in payload["content"]
    assert "<h2>Hidden</h2>" in payload["content"]
    assert "<p>Secret</p>" in payload["content"]
    assert '"message": "M"' in payload["content"]
    assert '"title": "Hidden"' in payload["content"]
    assert '"planId": "cfg"' in payload["content"]
    assert "paid_content" not in payload


def test_wordpress_post_misconfigured(monkeypatch):
    cfg = {
        "wordpress": {
            "accounts": {
                "acc": {
                    "site": "https://wordpress.example",
                    "client_id": "YOUR_CLIENT_ID",
                    "client_secret": "YOUR_CLIENT_SECRET",
                    "username": "YOUR_USERNAME",
                    "password": "YOUR_PASSWORD",
                }
            }
        }
    }
    client, calls = make_client(monkeypatch, cfg)
    encoded = base64.b64encode(b"x").decode()
    resp = client.post(
        "/wordpress/post",
        json={
            "account": "acc",
            "title": "T",
            "content": "C",
            "media": [{"filename": "img.png", "data": encoded}],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["error"] == "Account misconfigured"
    assert calls["uploads"] == []
    assert calls["post"] is None


def test_wordpress_post_cleans_temp_files_on_service_exception(monkeypatch, tmp_path):
    monkeypatch.setattr(server, "WORDPRESS_ACCOUNT_ERRORS", set(), raising=False)
    monkeypatch.setattr(server, "WORDPRESS_CLIENTS", {"acc": object()}, raising=False)

    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(server, "service_post_to_wordpress", boom)

    created: list[Path] = []
    original_ntf = tempfile.NamedTemporaryFile

    def fake_ntf(*args, **kwargs):
        kwargs.setdefault("delete", False)
        kwargs["dir"] = tmp_path
        tmp = original_ntf(*args, **kwargs)
        created.append(Path(tmp.name))
        return tmp

    monkeypatch.setattr(tempfile, "NamedTemporaryFile", fake_ntf)

    data = base64.b64encode(b"x").decode()
    media_item = server.WordpressMediaItem(filename="img.png", data=data)

    with pytest.raises(RuntimeError):
        server.post_to_wordpress("acc", "T", "C", media=[media_item])

    assert created, "temporary file was not created"
    for p in created:
        assert not p.exists()
