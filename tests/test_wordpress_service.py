from pathlib import Path
import sys

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))
import services.post_to_wordpress as wp_service


class DummyClient:
    def __init__(self, config, nested: bool = False):
        self.config = config
        self.authenticated = False
        self.uploaded = []
        self.created = None
        self.nested = nested

    def authenticate(self):
        self.authenticated = True

    def upload_media(self, content, filename):
        self.uploaded.append((filename, content))
        idx = len(self.uploaded)
        if self.nested:
            return {"media": {"ID": idx, "URL": f"http://img{idx}"}}
        return {"id": idx, "url": f"http://img{idx}"}

    def create_post(self, title, html, featured_id=None):
        self.created = {
            "title": title,
            "html": html,
            "featured_id": featured_id,
        }
        return {"id": 10, "link": "http://post"}


def test_create_wp_client_select_account(monkeypatch):
    # Patch WordpressClient with dummy implementation
    monkeypatch.setattr(wp_service, "WordpressClient", DummyClient)
    wp_service.CONFIG = {
        "wordpress": {
            "accounts": {
                "acc1": {"site": "s1"},
                "acc2": {"site": "s2"},
            }
        }
    }
    client = wp_service.create_wp_client("acc2")
    assert isinstance(client, DummyClient)
    assert client.authenticated is True
    # Ensure the correct account was used as default
    assert (
        client.config["wordpress"]["accounts"]["default"]["site"]
        == "s2"
    )


@pytest.mark.parametrize("nested", [False, True])
def test_post_to_wordpress_uploads_and_creates(monkeypatch, tmp_path, nested):
    dummy = DummyClient({}, nested=nested)
    monkeypatch.setattr(wp_service, "create_wp_client", lambda account=None: dummy)

    img1 = tmp_path / "a.jpg"
    img1.write_bytes(b"123")
    img2 = tmp_path / "b.jpg"
    img2.write_bytes(b"456")

    resp = wp_service.post_to_wordpress(
        "Title",
        "Body",
        [(img1, "x1.jpg"), (img2, "x2.jpg")],
        account="acc",
    )
    assert resp == {"id": 10, "link": "http://post"}
    # Uploaded both images
    assert dummy.uploaded[0][0] == "x1.jpg"
    assert dummy.uploaded[1][0] == "x2.jpg"
    # HTML contains image tags with alt attributes
    assert '<img src="http://img1" alt="x1.jpg" />' in dummy.created["html"]
    assert '<img src="http://img2" alt="x2.jpg" />' in dummy.created["html"]
    # First image used as featured
    assert dummy.created["featured_id"] == 1
