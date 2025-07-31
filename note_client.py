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
        resp = self.session.post(url, data={"login": username, "password": password})
        self.session.cookies.update(resp.cookies)
        if resp.status_code != 200:
            raise NoteAuthError(f"Login failed with status {resp.status_code}")

    def upload_image(self, path: Path) -> str:
        """Upload an image and return the CDN URL from the API response."""
        url = f"{self.base_url}/api/v1/upload_image"
        try:
            with path.open("rb") as fh:
                resp = self.session.post(url, files={"file": fh})
            resp.raise_for_status()
            data = resp.json()
            return data.get("url") or data["cdn_url"]
        except Exception as exc:  # Mimic the simple try/except pattern
            raise RuntimeError(f"Image upload failed: {exc}") from exc
