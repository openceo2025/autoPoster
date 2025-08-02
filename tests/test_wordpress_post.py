import base64
import json

import pytest
from fastapi.testclient import TestClient

import requests
import server
import services.post_to_wordpress as wp_service


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
    calls = {"uploads": [], "post": None}

    def fake_post(url, *args, **kwargs):
        if url.endswith("oauth2/token"):
            return DummyResponse({"access_token": "tok"})
        if url.endswith("/media/new"):
            calls["uploads"].append(kwargs["files"]["media[]"])
            return DummyResponse({"id": 1, "source_url": "http://img"})
        if url.endswith("/posts/new"):
            calls["post"] = kwargs.get("json")
            return DummyResponse({"id": 10, "link": "http://post"})
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
        json={"account": "acc", "title": "T", "content": "C", "media": [encoded]},
    )
    assert resp.status_code == 200
    assert resp.json() == {"id": 10, "link": "http://post"}
    assert len(calls["uploads"]) == 1
    filename, content = calls["uploads"][0]
    assert content == data
    payload = calls["post"]
    assert payload["featured_image"] == 1
    assert "http://img" in payload["content"]
    assert payload["title"] == "T"


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
        json={"account": "acc", "title": "T", "content": "C", "media": [encoded]},
    )
    assert resp.status_code == 200
    assert resp.json()["error"] == "Account misconfigured"
    assert calls["uploads"] == []
    assert calls["post"] is None
