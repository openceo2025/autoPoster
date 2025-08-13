from fastapi.testclient import TestClient
import server


def test_endpoints_return_common_format(monkeypatch):
    # Mastodon stub
    class DummyMasto:
        def status_post(self, text, media_ids=None):
            return {"id": 1, "url": "http://masto/1"}

        def media_post(self, *args, **kwargs):
            return {"id": "m1"}

    monkeypatch.setattr(server, "MASTODON_ACCOUNT_ERRORS", {}, raising=False)
    monkeypatch.setattr(server, "MASTODON_CLIENTS", {"acc": DummyMasto()}, raising=False)

    # Twitter stub
    class DummyAPI:
        def media_upload(self, filename, file):
            return type("M", (), {"media_id": "m1"})

        def verify_credentials(self):
            return type("U", (), {"screen_name": "user"})()

    class DummyClient:
        def create_tweet(self, text, media_ids=None):
            return type("Resp", (), {"data": {"id": "2"}})()

    monkeypatch.setattr(server, "TWITTER_ACCOUNT_ERRORS", {}, raising=False)
    monkeypatch.setattr(
        server,
        "TWITTER_CLIENTS",
        {"acc": {"client": DummyClient(), "api": DummyAPI()}},
        raising=False,
    )

    # WordPress stub
    monkeypatch.setattr(server, "WORDPRESS_ACCOUNT_ERRORS", {}, raising=False)
    monkeypatch.setattr(server, "WORDPRESS_CLIENTS", {"acc": object()}, raising=False)

    def fake_wp_post(
        account,
        title,
        content,
        media=None,
        paid_content=None,
        paid_title=None,
        paid_message=None,
        plan_id=None,
        categories=None,
        tags=None,
    ):
        return {"id": 3, "link": "http://wp/3", "site": "wordpress"}

    monkeypatch.setattr(server, "service_post_to_wordpress", fake_wp_post)

    # Note stub
    def fake_post_to_note(content, images=None, account=None):
        return {"id": 4, "link": "http://note/4", "site": "note"}

    monkeypatch.setattr(server, "post_to_note", fake_post_to_note)

    client = TestClient(server.app)

    r1 = client.post("/mastodon/post", json={"account": "acc", "text": "hi"})
    assert r1.status_code == 200
    assert r1.json() == {"id": 1, "link": "http://masto/1", "site": "mastodon"}

    r2 = client.post("/twitter/post", json={"account": "acc", "text": "hi"})
    assert r2.status_code == 200
    assert r2.json() == {
        "id": "2",
        "link": "https://twitter.com/user/status/2",
        "site": "twitter",
    }

    r3 = client.post(
        "/wordpress/post",
        json={"account": "acc", "title": "T", "content": "C"},
    )
    assert r3.status_code == 200
    assert r3.json() == {"id": 3, "link": "http://wp/3", "site": "wordpress"}

    r4 = client.post("/note/draft", json={"account": "acc", "content": "C"})
    assert r4.status_code == 200
    assert r4.json() == {"id": 4, "link": "http://note/4", "site": "note"}
