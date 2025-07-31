from pathlib import Path
import requests

class NoteAuthError(Exception):
    """Raised when authentication with Note fails."""


class NoteClient:
    """Simple client for Note API."""

    def __init__(self, config: dict, session: requests.Session | None = None):
        self.config = config or {}
        self.session = session or requests.Session()
        note_cfg = self.config.get("note", {})
        self.base_url = note_cfg.get("base_url", "https://note.com").rstrip("/")

    def login(self) -> None:
        """Authenticate and store cookies in the session."""
        note_cfg = self.config.get("note", {})
        username = note_cfg.get("username")
        password = note_cfg.get("password")
        url = f"{self.base_url}/api/v1/sessions/sign_in"
        resp = self.session.post(
            url, json={"login": username, "password": password}
        )
        self.session.cookies.update(resp.cookies)
        print(f'Login status: {resp.status_code}, body: {resp.text}')
        if resp.status_code not in (200, 201):
            raise NoteAuthError(f"Login failed with status {resp.status_code}")

    def upload_image(self, path: Path) -> str:
        """Upload an image and return the CDN URL from the API response."""
        url = f"{self.base_url}/api/v1/upload_image"
        try:
            with path.open("rb") as fh:
                resp = self.session.post(url, files={"file": fh})
            resp.raise_for_status()
            data = resp.json()
            if "data" in data:
                data = data["data"]
            return data.get("url") or data.get("cdn_url")
        except Exception as exc:  # Mimic the simple try/except pattern
            raise RuntimeError(f"Image upload failed: {exc}") from exc

    def create_draft(self, title: str, body_html: str) -> dict:
        """Create a draft text note and return identifiers."""
        post_url = f"{self.base_url}/api/v1/text_notes"
        try:
            resp = self.session.post(
                post_url,
                json={"name": title, "body": "", "template_key": None},
            )
            resp.raise_for_status()
            data = resp.json()
            note_id = data.get("id")
            note_key = data.get("key")
            draft_url = data.get("draft_url")
            put_url = f"{self.base_url}/api/v1/text_notes/{note_id}"
            resp2 = self.session.put(
                put_url,
                json={"name": title, "body": body_html, "status": "draft"},
            )
            resp2.raise_for_status()
            return {
                "note_id": note_id,
                "note_key": note_key,
                "draft_url": draft_url,
            }
        except Exception as exc:  # Mimic the simple try/except pattern
            raise RuntimeError(f"Draft creation failed: {exc}") from exc
