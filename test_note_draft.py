from pathlib import Path
from fastapi.testclient import TestClient
import server


def make_client(monkeypatch, handler=None):
    if handler is None:
        handler = lambda content, images, account: {"note_id": 1}
    monkeypatch.setattr(server, "post_to_note", handler)
    return TestClient(server.app)


def test_create_draft_with_images(monkeypatch):
    received = {}

    def dummy(content, images, account):
        received["content"] = content
        received["images"] = images
        received["account"] = account
        return {"note_id": 123, "note_key": "k", "draft_url": "u"}

    client = make_client(monkeypatch, dummy)
    resp = client.post(
        "/note/draft",
        json={"account": "acc1", "content": "hello", "images": ["a.png", "b.png"]},
    )
    assert resp.status_code == 200
    assert resp.json() == {"note_id": 123, "note_key": "k", "draft_url": "u"}
    assert received["content"] == "hello"
    assert received["images"] == [Path("a.png"), Path("b.png")]
    assert received["account"] == "acc1"


def test_create_draft_no_images(monkeypatch):
    received = {}

    def dummy(content, images, account):
        received["images"] = images
        received["account"] = account
        return {}

    client = make_client(monkeypatch, dummy)
    resp = client.post("/note/draft", json={"account": "acc2", "content": "hi"})
    assert resp.status_code == 200
    assert received["images"] == []
    assert received["account"] == "acc2"


def test_account_parameter_passed(monkeypatch):
    received = {}

    def dummy(content, images, account):
        received["account"] = account
        return {}

    client = make_client(monkeypatch, dummy)
    resp = client.post("/note/draft", json={"account": "special", "content": "x"})
    assert resp.status_code == 200
    assert received["account"] == "special"

