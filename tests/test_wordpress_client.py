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


def test_upload_media_source_url(monkeypatch):
    client = _make_client()

    def fake_post(url, files):
        return DummyResp({"media": [{"id": 3, "source_url": "http://example/img2.jpg"}]})

    monkeypatch.setattr(client.session, "post", fake_post)
    res = client.upload_media(b"data", "b.jpg")
    assert res == {"id": 3, "url": "http://example/img2.jpg"}


def test_upload_media_fallback_link(monkeypatch):
    client = _make_client()

    def fake_post(url, files):
        return DummyResp({"media": [{"id": 2, "link": "http://page"}]})

    monkeypatch.setattr(client.session, "post", fake_post)
    res = client.upload_media(b"x", "a.jpg")
    assert res == {"id": 2, "url": "http://page"}


def test_plan_id_from_config():
    client = WordpressClient({"wordpress": {"site": "s", "plan_id": "p1"}})
    assert client.plan_id == "p1"


def test_plan_id_default_none():
    client = WordpressClient({"wordpress": {"site": "s"}})
    assert client.plan_id is None


def test_get_search_terms_parses_views(monkeypatch):
    client = _make_client()

    def fake_get(url, headers=None, params=None):
        assert params == {"days": 7}
        return DummyResp({"search_terms": [["foo", 5], ["bar", 1]]})

    monkeypatch.setattr(client.session, "get", fake_get)
    terms = client.get_search_terms(7)
    assert terms == [
        {"term": "foo", "views": 5},
        {"term": "bar", "views": 1},
    ]


def test_create_post_returns_link(monkeypatch):
    client = _make_client()

    def fake_post(url, json):
        return DummyResp({"ID": 7, "URL": "http://example/post"})

    monkeypatch.setattr(client.session, "post", fake_post)
    res = client.create_post("T", "<p>B</p>")
    assert res == {"id": 7, "link": "http://example/post"}


def test_create_post_fallback_link(monkeypatch):
    client = _make_client()

    def fake_post(url, json):
        return DummyResp({"ID": 8, "link": "http://example/alt"})

    monkeypatch.setattr(client.session, "post", fake_post)
    res = client.create_post("T", "<p>B</p>")
    assert res == {"id": 8, "link": "http://example/alt"}


def test_get_site_info(monkeypatch):
    client = _make_client()

    def fake_get(url, params=None):
        assert params == {"fields": "icon,logo"}
        return DummyResp({"icon": {"img": "u"}})

    monkeypatch.setattr(client.session, "get", fake_get)
    info = client.get_site_info(fields="icon,logo")
    assert info == {"icon": {"img": "u"}}


def test_list_media_and_delete(monkeypatch):
    client = _make_client()

    def fake_get(url, params=None):
        assert params == {"page": 1, "number": 100, "post_ID": 0}
        return DummyResp({"media": [{"ID": 1}]})

    def fake_post(url):
        assert url.endswith("/media/1/delete")
        return DummyResp({})

    monkeypatch.setattr(client.session, "get", fake_get)
    monkeypatch.setattr(client.session, "post", fake_post)
    media = client.list_media(post_id=0)
    assert media == [{"ID": 1}]
    deleted = client.delete_media(1)
    assert deleted == 1

def test_update_media_alt_text(monkeypatch):
    client = _make_client()

    def fake_post(url, json):
        assert url.endswith("/media/5")
        assert json == {"alt_text": "New alt"}
        return DummyResp({"id": 5, "alt_text": "New alt"})

    monkeypatch.setattr(client.session, "post", fake_post)
    res = client.update_media_alt_text(5, "New alt")
    assert res == {"id": 5, "alt_text": "New alt"}
