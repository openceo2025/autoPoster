from pathlib import Path
from fastapi.testclient import TestClient
import server


def make_client(monkeypatch, handler=None):
    if handler is None:
        handler = lambda content, images: {"note_id": 1}
    monkeypatch.setattr(server, "post_to_note", handler)
    return TestClient(server.app)


def test_create_draft_with_images(monkeypatch):
    received = {}

    def dummy(content, images):
        received["content"] = content
        received["images"] = images
        return {"note_id": 123, "note_key": "k", "draft_url": "u"}

    client = make_client(monkeypatch, dummy)
    resp = client.post(
        "/note/draft",
        json={"content": "hello", "images": ["a.png", "b.png"]},
    )
    assert resp.status_code == 200
    assert resp.json() == {"note_id": 123, "note_key": "k", "draft_url": "u"}
    assert received["content"] == "hello"
    assert received["images"] == [Path("a.png"), Path("b.png")]


def test_create_draft_no_images(monkeypatch):
    received = {}

    def dummy(content, images):
        received["images"] = images
        return {}

    client = make_client(monkeypatch, dummy)
    resp = client.post("/note/draft", json={"content": "hi"})
    assert resp.status_code == 200
    assert received["images"] == []

