from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))
import services.post_to_wordpress as wp_service


class DummyClient:
    def __init__(self, config):
        self.config = config
        self.authenticated = False
        self.uploaded = []
        self.created = None
        info = (
            config.get("wordpress", {})
            .get("accounts", {})
            .get("default", {})
        )
        self.plan_id = info.get("plan_id")

    def authenticate(self):
        self.authenticated = True

    def upload_media(self, content, filename):
        self.uploaded.append((filename, content))
        idx = len(self.uploaded)
        return {"id": idx, "url": f"http://img{idx}"}

    def create_post(self, title, html, featured_id=None, paid_content=None):
        self.created = {
            "title": title,
            "html": html,
            "featured_id": featured_id,
            "paid_content": paid_content,
        }
        return {"id": 10, "link": "http://post"}


def test_create_wp_client_select_account(monkeypatch):
    # Patch WordpressClient with dummy implementation
    monkeypatch.setattr(wp_service, "WordpressClient", DummyClient)
    wp_service.CONFIG = {
        "wordpress": {
            "accounts": {
                "acc1": {"site": "s1", "plan_id": "p1"},
                "acc2": {"site": "s2", "plan_id": "p2"},
            }
        }
    }
    client = wp_service.create_wp_client("acc2")
    assert isinstance(client, DummyClient)
    assert client.authenticated is True
    # Ensure the correct account was used as default
    assert (
        client.config["wordpress"]["accounts"]["default"]["site"] == "s2"
    )
    assert client.plan_id == "p2"


def test_post_to_wordpress_uploads_and_creates(monkeypatch, tmp_path):
    dummy = DummyClient({})
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
        paid_content="Paid",
        paid_title="PTitle",
        paid_message="Msg",
        plan_id="p1",
    )
    assert resp == {"id": 10, "link": "http://post"}
    # Uploaded both images
    assert dummy.uploaded[0][0] == "x1.jpg"
    assert dummy.uploaded[1][0] == "x2.jpg"
    # HTML contains image tags
    assert '<img src="http://img1" alt="x1" />' in dummy.created["html"]
    assert '<img src="http://img2" alt="x2" />' in dummy.created["html"]
    # First image used as featured
    assert dummy.created["featured_id"] == 1
    # Paid content added as subscribers-only block in HTML and not sent separately
    assert "wp:jetpack/subscribers-only-content" in dummy.created["html"]
    assert "<h2>PTitle</h2>" in dummy.created["html"]
    assert "<p>Paid</p>" in dummy.created["html"]
    assert '"message": "Msg"' in dummy.created["html"]
    assert '"title": "PTitle"' in dummy.created["html"]
    assert '"planId": "p1"' in dummy.created["html"]
    assert dummy.created["paid_content"] is None


def test_post_to_wordpress_adds_paid_block(monkeypatch):
    dummy = DummyClient({"wordpress": {"accounts": {"default": {"plan_id": "cfg"}}}})
    monkeypatch.setattr(wp_service, "create_wp_client", lambda account=None: dummy)

    resp = wp_service.post_to_wordpress(
        "T",
        "B",
        [],
        account="acc",
        paid_content="Secret",
        paid_title="Hidden",
        paid_message="M",
    )
    assert resp == {"id": 10, "link": "http://post"}
    assert "wp:jetpack/subscribers-only-content" in dummy.created["html"]
    assert "<h2>Hidden</h2>" in dummy.created["html"]
    assert "<p>Secret</p>" in dummy.created["html"]
    assert '"message": "M"' in dummy.created["html"]
    assert '"title": "Hidden"' in dummy.created["html"]
    # plan_id defaults to client's plan_id when not provided
    assert '"planId": "cfg"' in dummy.created["html"]
    assert dummy.created["paid_content"] is None
