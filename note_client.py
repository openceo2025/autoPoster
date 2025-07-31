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
