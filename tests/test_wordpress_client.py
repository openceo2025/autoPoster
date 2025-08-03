import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from wordpress_client import WordpressClient


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


def _make_client():
    return WordpressClient({"wordpress": {"site": "s"}})


def test_upload_media_uses_media(monkeypatch):
    client = _make_client()

    def fake_post(url, files):
        return DummyResp({"media": [{"id": 1, "URL": "http://example/img.jpg"}]})

    monkeypatch.setattr(client.session, "post", fake_post)
    res = client.upload_media(b"x", "a.jpg")
    assert res == {"id": 1, "url": "http://example/img.jpg"}


def test_upload_media_fallback_link(monkeypatch):
    client = _make_client()

    def fake_post(url, files):
        return DummyResp({"media": [{"id": 2, "link": "http://page"}]})

    monkeypatch.setattr(client.session, "post", fake_post)
    res = client.upload_media(b"x", "a.jpg")
    assert res == {"id": 2, "url": "http://page"}
