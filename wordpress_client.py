import logging
import requests


class WordpressAuthError(Exception):
    """Raised when authentication with WordPress fails."""


logger = logging.getLogger(__name__)


class WordpressClient:
    """Simple client for WordPress.com API."""

    TOKEN_URL = "https://public-api.wordpress.com/oauth2/token"
    API_BASE = "https://public-api.wordpress.com/rest/v1.1/sites/{site}"

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
        self.plan_id: str | None = acct.get("plan_id")
        self.access_token: str | None = None

    def authenticate(self) -> None:
        """Authenticate and store access token in headers."""
        data = {
            "grant_type": "password",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "username": self.username,
            "password": self.password,
            "scope": "global",
        }
        resp: requests.Response | None = None
        try:
            resp = self.session.post(self.TOKEN_URL, data=data)
            logger.debug(
                "Auth response status: %s, body: [redacted]", resp.status_code
            )
            resp.raise_for_status()
            token = resp.json().get("access_token")
            if not token:
                raise WordpressAuthError("No access_token in response")
            self.access_token = token
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        except Exception as exc:
            if resp is not None:
                logger.debug(
                    "Auth failure status: %s, body: [redacted]", resp.status_code
                )
            raise WordpressAuthError(f"Authentication failed: {exc}") from exc

    def upload_media(self, content: bytes, filename: str) -> dict:
        """Upload media bytes and return media ID and URL."""
        url = f"{self.API_BASE.format(site=self.site)}/media/new"
        files = {"media[]": (filename, content)}
        resp: requests.Response | None = None
        try:
            print(f"POST {url} with {filename}, {len(content)} bytes")
            resp = self.session.post(url, files=files)
            print(resp.status_code, resp.text)
            print(getattr(resp, "headers", None))
            resp.raise_for_status()
            data = resp.json()
            media = data.get("media")
            if media:
                item = media[0]
                media_id = item.get("id")
                media_url = item.get("source_url") or item.get("URL") or item.get("link")
            else:
                media_id = data.get("id")
                media_url = (
                    data.get("source_url") or data.get("URL") or data.get("link")
                )
            return {"id": media_id, "url": media_url}
        except Exception as exc:
            if resp is not None:
                print(resp.status_code, resp.text)
                print(getattr(resp, "headers", None))
            raise RuntimeError(f"Media upload failed: {exc}") from exc

    def create_post(
        self,
        title: str,
        html: str,
        featured_id: int | None = None,
        paid_content: str | None = None,
        categories: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> dict:
        """Create and publish a post with optional featured image."""
        url = f"{self.API_BASE.format(site=self.site)}/posts/new"
        payload = {"title": title, "content": html, "status": "publish"}
        if featured_id:
            payload["featured_image"] = featured_id
        if paid_content is not None:
            payload["paid_content"] = paid_content
        if categories:
            payload["categories"] = ",".join(categories)
        if tags:
            payload["tags"] = ",".join(tags)
        resp: requests.Response | None = None
        try:
            print(f"POST {url} payload: {payload}")
            resp = self.session.post(url, json=payload)
            print(resp.status_code, resp.text)
            resp.raise_for_status()
            data = resp.json()
            return {
                "id": data.get("ID"),
                "link": data.get("URL") or data.get("link"),
            }
        except Exception as exc:
            if resp is not None:
                print(resp.status_code, resp.text)
            raise RuntimeError(f"Post creation failed: {exc}") from exc

    def list_posts(
        self, page: int = 1, number: int = 10, status: str | None = None
    ) -> list[dict]:
        """Return posts with basic information.

        Parameters
        ----------
        page: int
            Page number to fetch.
        number: int
            Number of posts per page.
        status: str | None
            Optional status filter such as ``"trash"`` to list trashed posts.
        """
        url = f"{self.API_BASE.format(site=self.site)}/posts"
        params = {"page": page, "number": number}
        if status is not None:
            params["status"] = status
        resp: requests.Response | None = None
        try:
            resp = self.session.get(url, headers=self.session.headers, params=params)
            resp.raise_for_status()
            data = resp.json()
            posts: list[dict] = []
            for item in data.get("posts", []):
                posts.append(
                    {
                        "id": item.get("ID"),
                        "title": item.get("title"),
                        "date": item.get("date"),
                        "url": item.get("URL"),
                    }
                )
            return posts
        except Exception as exc:
            if resp is not None:
                print(resp.status_code, resp.text)
            raise RuntimeError(f"Fetching posts failed: {exc}") from exc

    def delete_post(self, post_id: int, permanent: bool = False) -> int:
        """Delete a post by ID and return the deleted ID.

        Parameters
        ----------
        post_id: int
            ID of the post to remove.
        permanent: bool, default False
            If ``True`` the post is permanently deleted instead of being moved
            to the trash.
        """
        url = f"{self.API_BASE.format(site=self.site)}/posts/{post_id}/delete"
        params = {"force": 1} if permanent else None
        resp: requests.Response | None = None
        try:
            resp = self.session.post(url, params=params)
            resp.raise_for_status()
            return post_id
        except Exception as exc:
            if resp is not None:
                print(resp.status_code, resp.text)
            raise RuntimeError(f"Post deletion failed: {exc}") from exc

    def empty_trash(self) -> list[int]:
        """Permanently remove all posts currently in the trash.

        Returns
        -------
        list[int]
            IDs of posts that were successfully deleted.
        """
        deleted: list[int] = []
        page = 1
        while True:
            items = self.list_posts(page=page, number=100, status="trash")
            if not items:
                break
            for item in items:
                try:
                    self.delete_post(item["id"], permanent=True)
                    deleted.append(item["id"])
                except Exception:
                    continue
            if len(items) < 100:
                break
            page += 1
        return deleted

    def get_site_info(self, fields: str | None = None) -> dict:
        """Return information about the site.

        Parameters
        ----------
        fields: str | None
            Optional comma-separated list of fields to include in the
            response.
        """
        url = self.API_BASE.format(site=self.site)
        params = {"fields": fields} if fields else None
        resp: requests.Response | None = None
        try:
            resp = self.session.get(url, params=params)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            if resp is not None:
                print(resp.status_code, resp.text)
            raise RuntimeError(f"Fetching site info failed: {exc}") from exc

    def list_media(
        self, post_id: int | None = None, page: int = 1, number: int = 100
    ) -> list[dict]:
        """Return media library items.

        Parameters
        ----------
        post_id: int | None
            If provided, filter media attached to the given post ID. Use
            ``0`` to retrieve unattached media.
        page: int
            Page number to fetch.
        number: int
            Number of items per page (max 100).
        """
        url = f"{self.API_BASE.format(site=self.site)}/media"
        params = {"page": page, "number": number}
        if post_id is not None:
            params["post_ID"] = post_id
        resp: requests.Response | None = None
        try:
            resp = self.session.get(url, params=params)
            resp.raise_for_status()
            return resp.json().get("media", [])
        except Exception as exc:
            if resp is not None:
                print(resp.status_code, resp.text)
            raise RuntimeError(f"Fetching media failed: {exc}") from exc

    def update_media_alt_text(self, media_id: int, alt_text: str) -> dict:
        """Update the alt text for a media item."""
        url = f"{self.API_BASE.format(site=self.site)}/media/{media_id}"
        payload = {"alt_text": alt_text}
        resp: requests.Response | None = None
        try:
            resp = self.session.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            if resp is not None:
                print(resp.status_code, resp.text)
            raise RuntimeError(
                f"Updating media alt text failed: {exc}"
            ) from exc

    def delete_media(self, media_id: int) -> int:
        """Delete a media item by ID and return the deleted ID."""
        url = f"{self.API_BASE.format(site=self.site)}/media/{media_id}/delete"
        resp: requests.Response | None = None
        try:
            resp = self.session.post(url)
            resp.raise_for_status()
            return media_id
        except Exception as exc:
            if resp is not None:
                print(resp.status_code, resp.text)
            raise RuntimeError(f"Media deletion failed: {exc}") from exc

    def get_post_views(self, post_id: int, days: int) -> dict:
        """Return view statistics for a post over a number of days."""
        url = f"{self.API_BASE.format(site=self.site)}/stats/post/{post_id}"
        params = {"unit": "day", "quantity": days}
        resp: requests.Response | None = None
        try:
            resp = self.session.get(url, headers=self.session.headers, params=params)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            if resp is not None:
                print(resp.status_code, resp.text)
            raise RuntimeError(f"Fetching post views failed: {exc}") from exc

    def get_search_terms(self, days: int) -> list[dict]:
        """Return search terms and view counts over a number of days."""
        url = f"{self.API_BASE.format(site=self.site)}/stats/search-terms"
        params = {"days": days}
        resp: requests.Response | None = None
        try:
            resp = self.session.get(url, headers=self.session.headers, params=params)
            resp.raise_for_status()
            data = resp.json()
            terms = data.get("search_terms", [])
            parsed: list[dict] = []
            for item in terms:
                if (
                    isinstance(item, (list, tuple))
                    and len(item) >= 2
                ):
                    parsed.append({"term": item[0], "views": item[1]})
            return parsed
        except Exception as exc:
            if resp is not None:
                print(resp.status_code, resp.text)
            raise RuntimeError(
                f"Fetching search terms failed: {exc}"
            ) from exc
