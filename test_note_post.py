import server
from fastapi.testclient import TestClient


def make_client(monkeypatch, return_value=None):
    called = {}

    def dummy(account, text, media, thumbnail, paid, tags):
        called['args'] = (account, text, media, thumbnail, paid, tags)
        return return_value if return_value is not None else {"posted": True}

    monkeypatch.setattr(server, "post_to_note", dummy)
    return TestClient(server.app), called


def test_note_post(monkeypatch):
    client, called = make_client(monkeypatch)
    payload = {
        "account": "acc",
        "text": "hello",
        "media": ["m1"],
        "thumbnail": "thumb",
        "paid": False,
        "tags": ["t1", "t2"],
    }
    resp = client.post("/note/post", json=payload)
    assert resp.status_code == 200
    assert resp.json() == {"posted": True}
    assert called["args"] == (
        "acc",
        "hello",
        ["m1"],
        "thumb",
        False,
        ["t1", "t2"],
    )


def test_note_post_defaults(monkeypatch):
    client, called = make_client(monkeypatch)
    payload = {
        "account": "acc",
        "text": "hello",
        "paid": True,
    }
    resp = client.post("/note/post", json=payload)
    assert resp.status_code == 200
    assert resp.json() == {"posted": True}
    assert called["args"] == ("acc", "hello", [], "", True, [])


def test_note_post_error(monkeypatch):
    client, _ = make_client(monkeypatch, return_value={"error": "fail"})
    payload = {"account": "acc", "text": "x", "paid": False}
    resp = client.post("/note/post", json=payload)
    assert resp.status_code == 200
    assert resp.json() == {"error": "fail"}
