import requests


class WordpressAuthError(Exception):
    """Raised when authentication with WordPress fails."""


class WordpressClient:
    """Simple client for WordPress.com API."""

    TOKEN_URL = "https://public-api.wordpress.com/oauth2/token"
    API_BASE = "https://public-api.wordpress.com/wp/v2/sites/{site}"

    def __init__(self, config: dict, session: requests.Session | None = None):
        self.config = config or {}
        self.session = session or requests.Session()
        wp_cfg = self.config.get("wordpress", {})
        accounts = wp_cfg.get("accounts")
        if accounts:
            acct = accounts.get("default") or next(iter(accounts.values()))
        else:
            acct = wp_cfg
        self.site = acct.get("site")
        self.client_id = acct.get("client_id")
        self.client_secret = acct.get("client_secret")
        self.username = acct.get("username")
        self.password = acct.get("password")
        self.access_token: str | None = None

    def authenticate(self) -> None:
        """Authenticate and store access token in headers."""
        data = {
            "grant_type": "password",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "username": self.username,
            "password": self.password,
        }
        try:
            resp = self.session.post(self.TOKEN_URL, data=data)
            resp.raise_for_status()
            token = resp.json().get("access_token")
            if not token:
                raise WordpressAuthError("No access_token in response")
            self.access_token = token
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        except Exception as exc:
            raise WordpressAuthError(f"Authentication failed: {exc}") from exc

    def upload_media(self, content: bytes, filename: str) -> dict:
        """Upload media bytes and return media ID and URL."""
        url = f"{self.API_BASE.format(site=self.site)}/media/new"
        files = {"file": (filename, content)}
        try:
            resp = self.session.post(url, files=files)
            resp.raise_for_status()
            data = resp.json()
            return {"id": data.get("id"), "url": data.get("source_url") or data.get("link")}
        except Exception as exc:
            raise RuntimeError(f"Media upload failed: {exc}") from exc

    def create_post(self, title: str, html: str, featured_id: int | None = None) -> dict:
        """Create and publish a post with optional featured image."""
        url = f"{self.API_BASE.format(site=self.site)}/posts/new"
        payload = {"title": title, "content": html, "status": "publish"}
        if featured_id:
            payload["featured_media"] = featured_id
        try:
            resp = self.session.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            raise RuntimeError(f"Post creation failed: {exc}") from exc
