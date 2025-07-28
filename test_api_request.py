from fastapi.testclient import TestClient

import server

pytest_plugins = ["test_mastodon_post", "test_twitter_post", "test_note_post"]


def test_post_endpoint(temp_config):
    """Verify the generic /post endpoint works with a temp config."""
    client = TestClient(server.app)
    resp = client.post("/post", json={"text": "test", "media": ["a"]})
    assert resp.status_code == 200
    assert resp.json() == {"received": True, "media_items": 1}
