import json
from pathlib import Path
from typing import List, Optional, Dict

import base64
from io import BytesIO
from mastodon import Mastodon
import tweepy
from note_client import NoteClient
from wordpress_client import WordpressClient
from services.post_to_note import post_to_note
from services.post_to_wordpress import post_to_wordpress as service_post_to_wordpress
from services.wordpress_stats import (
    get_post_views as service_get_post_views,
    get_search_terms as service_get_search_terms,
)
from services.wordpress_posts import (
    list_posts as service_list_posts,
    delete_posts as service_delete_posts,
)
import os
import tempfile

from fastapi import FastAPI, Query, Request
from pydantic import BaseModel

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"
print(f"Loading config from {CONFIG_PATH}")

# Load config if available
if CONFIG_PATH.exists():
    with CONFIG_PATH.open() as f:
        CONFIG = json.load(f)
else:
    CONFIG = {}
print(json.dumps(CONFIG.get('note', {}), indent=2))

app = FastAPI(title="autoPoster")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log incoming API requests with method, path and body."""
    body = await request.body()
    try:
        body_text = body.decode("utf-8")
    except Exception:
        body_text = str(body)
    print(f"{request.method} {request.url.path} {body_text}")
    response = await call_next(request)
    return response


def validate_mastodon_accounts(config: Dict) -> Dict[str, str]:
    """Validate Mastodon account configuration and return a map of errors."""
    errors: Dict[str, str] = {}
    accounts = config.get("mastodon", {}).get("accounts")
    if not accounts:
        errors["_general"] = "mastodon.accounts section missing or empty"
        return errors

    for name, info in accounts.items():
        account_errors = []
        instance = info.get("instance_url")
        token = info.get("access_token")

        if not instance:
            account_errors.append("missing instance_url")
        elif "mastodon.example" in instance:
            account_errors.append("instance_url looks like a placeholder")

        if not token:
            account_errors.append("missing access_token")
        elif token == "YOUR_TOKEN":
            account_errors.append("access_token looks like a placeholder")

        if account_errors:
            errors[name] = "; ".join(account_errors)
    return errors


MASTODON_ACCOUNT_ERRORS = validate_mastodon_accounts(CONFIG)
if MASTODON_ACCOUNT_ERRORS:
    for acc, err in MASTODON_ACCOUNT_ERRORS.items():
        print(f"Mastodon config error for {acc}: {err}")


def create_mastodon_clients():
    """Create Mastodon clients for all configured accounts."""
    clients = {}
    accounts = CONFIG.get("mastodon", {}).get("accounts", {})
    for name, info in accounts.items():
        if name in MASTODON_ACCOUNT_ERRORS:
            continue
        try:
            clients[name] = Mastodon(
                access_token=info["access_token"],
                api_base_url=info["instance_url"],
            )
        except Exception as exc:
            # Log error but continue creating other clients
            print(f"Failed to init Mastodon client for {name}: {exc}")
    return clients


MASTODON_CLIENTS = create_mastodon_clients()


def validate_note_accounts(config: Dict) -> Dict[str, str]:
    """Validate Note account configuration and return a map of errors."""
    errors: Dict[str, str] = {}
    accounts = config.get("note", {}).get("accounts")
    if not accounts:
        errors["_general"] = "note.accounts section missing or empty"
        return errors

    for name, info in accounts.items():
        account_errors = []
        username = info.get("username")
        password = info.get("password")
        if not username:
            account_errors.append("missing username")
        if not password:
            account_errors.append("missing password")
        if account_errors:
            errors[name] = "; ".join(account_errors)
    return errors


NOTE_ACCOUNT_ERRORS = validate_note_accounts(CONFIG)
if NOTE_ACCOUNT_ERRORS:
    for acc, err in NOTE_ACCOUNT_ERRORS.items():
        print(f"Note config error for {acc}: {err}")


def create_note_clients():
    """Create Note clients for all configured accounts."""
    clients = {}
    note_cfg = CONFIG.get("note", {})
    accounts = note_cfg.get("accounts", {})
    base_url = note_cfg.get("base_url")
    for name, info in accounts.items():
        if name in NOTE_ACCOUNT_ERRORS:
            continue
        cfg = {"note": {"username": info.get("username"), "password": info.get("password")}}
        if base_url:
            cfg["note"]["base_url"] = base_url
        try:
            client = NoteClient(cfg)
            client.login()
            clients[name] = client
        except Exception as exc:
            print(f"Failed to init Note client for {name}: {exc}")
    return clients


NOTE_CLIENTS = create_note_clients()


def validate_twitter_accounts(config: Dict) -> Dict[str, str]:
    """Validate Twitter account configuration and return a map of errors."""
    errors: Dict[str, str] = {}
    accounts = config.get("twitter", {}).get("accounts")
    if not accounts:
        errors["_general"] = "twitter.accounts section missing or empty"
        return errors

    placeholders = {
        "consumer_key": "YOUR_CONSUMER_KEY",
        "consumer_secret": "YOUR_CONSUMER_SECRET",
        "access_token": "YOUR_ACCESS_TOKEN",
        "access_token_secret": "YOUR_ACCESS_TOKEN_SECRET",
        "bearer_token": "YOUR_BEARER_TOKEN",
    }

    for name, info in accounts.items():
        account_errors = []
        for key in placeholders:
            val = info.get(key)
            if not val:
                account_errors.append(f"missing {key}")
            elif val == placeholders[key]:
                account_errors.append(f"{key} looks like a placeholder")

        if account_errors:
            errors[name] = "; ".join(account_errors)
    return errors


TWITTER_ACCOUNT_ERRORS = validate_twitter_accounts(CONFIG)
if TWITTER_ACCOUNT_ERRORS:
    for acc, err in TWITTER_ACCOUNT_ERRORS.items():
        print(f"Twitter config error for {acc}: {err}")


def create_twitter_clients():
    """Create Tweepy clients for all configured accounts."""
    clients = {}
    accounts = CONFIG.get("twitter", {}).get("accounts", {})
    for name, info in accounts.items():
        if name in TWITTER_ACCOUNT_ERRORS:
            continue
        try:
            auth = tweepy.OAuth1UserHandler(
                info["consumer_key"],
                info["consumer_secret"],
                info["access_token"],
                info["access_token_secret"],
            )
            api = tweepy.API(auth)
            client = tweepy.Client(
                bearer_token=info["bearer_token"],
                consumer_key=info["consumer_key"],
                consumer_secret=info["consumer_secret"],
                access_token=info["access_token"],
                access_token_secret=info["access_token_secret"],
            )
            clients[name] = {"client": client, "api": api}
        except Exception as exc:
            print(f"Failed to init Twitter client for {name}: {exc}")
    return clients


TWITTER_CLIENTS = create_twitter_clients()


def validate_wordpress_accounts(config: Dict) -> Dict[str, str]:
    """Validate WordPress account configuration and return a map of errors."""
    errors: Dict[str, str] = {}
    accounts = config.get("wordpress", {}).get("accounts")
    if not accounts:
        errors["_general"] = "wordpress.accounts section missing or empty"
        return errors

    placeholders = {
        "client_id": "YOUR_CLIENT_ID",
        "client_secret": "YOUR_CLIENT_SECRET",
        "username": "YOUR_USERNAME",
        "password": "YOUR_PASSWORD",
    }

    for name, info in accounts.items():
        account_errors = []
        site = info.get("site")
        if not site:
            account_errors.append("missing site")
        elif "wordpress.example" in site:
            account_errors.append("site looks like a placeholder")

        for key, placeholder in placeholders.items():
            val = info.get(key)
            if not val:
                account_errors.append(f"missing {key}")
            elif val == placeholder:
                account_errors.append(f"{key} looks like a placeholder")

        if account_errors:
            errors[name] = "; ".join(account_errors)

    return errors


WORDPRESS_ACCOUNT_ERRORS = validate_wordpress_accounts(CONFIG)
if WORDPRESS_ACCOUNT_ERRORS:
    for acc, err in WORDPRESS_ACCOUNT_ERRORS.items():
        print(f"WordPress config error for {acc}: {err}")


def create_wordpress_clients():
    """Create WordPress clients for all configured accounts."""
    clients = {}
    accounts = CONFIG.get("wordpress", {}).get("accounts", {})
    for name, info in accounts.items():
        if name in WORDPRESS_ACCOUNT_ERRORS:
            continue
        cfg = {"wordpress": {"accounts": {"default": info}}}
        try:
            client = WordpressClient(cfg)
            client.authenticate()
            clients[name] = client
        except Exception as exc:
            print(f"Failed to init WordPress client for {name}: {exc}")
    return clients


WORDPRESS_CLIENTS = create_wordpress_clients()

class PostRequest(BaseModel):
    text: str
    media: Optional[List[str]] = None  # base64 encoded strings


class MastodonPostRequest(BaseModel):
    account: str
    text: str
    media: Optional[List[str]] = None


class TwitterPostRequest(BaseModel):
    account: str
    text: str
    media: Optional[List[str]] = None


class NotePostRequest(BaseModel):
    account: str
    content: str
    images: Optional[List[str]] = None


class WordpressMediaItem(BaseModel):
    filename: str
    data: str
    alt: Optional[str] = None


class WordpressPostRequest(BaseModel):
    account: str
    title: str
    content: str
    slug: Optional[str] = None
    media: Optional[List[WordpressMediaItem]] = None
    paid_content: Optional[str] = None
    paid_title: Optional[str] = None
    paid_message: Optional[str] = None
    plan_id: Optional[str] = None
    categories: Optional[List[str]] = None
    tags: Optional[List[str]] = None


def post_to_mastodon(account: str, text: str, media: Optional[List[str]] = None):
    if account in MASTODON_ACCOUNT_ERRORS:
        return {"error": "Account misconfigured"}
    client = MASTODON_CLIENTS.get(account)
    if not client:
        return {"error": "Account not configured"}

    media_ids = None
    if media:
        media_ids = []
        for item in media:
            try:
                data = base64.b64decode(item)
                uploaded = client.media_post(BytesIO(data), mime_type="application/octet-stream")
                media_ids.append(uploaded.get("id"))
            except Exception as exc:
                return {"error": f"Media upload failed: {exc}"}

    try:
        status = client.status_post(text, media_ids=media_ids)
    except Exception as exc:
        return {"error": str(exc)}

    return {
        "id": status.get("id"),
        "link": status.get("url"),
        "site": "mastodon",
    }


def post_to_twitter(account: str, text: str, media: Optional[List[str]] = None):
    if account in TWITTER_ACCOUNT_ERRORS:
        return {"error": "Account misconfigured"}
    info = TWITTER_CLIENTS.get(account)
    if not info:
        return {"error": "Account not configured"}

    client = info["client"]
    api = info["api"]

    media_ids = None
    if media:
        media_ids = []
        for item in media:
            try:
                data = base64.b64decode(item)
                uploaded = api.media_upload(filename="media", file=BytesIO(data))
                media_ids.append(uploaded.media_id)
            except Exception as exc:
                return {"error": f"Media upload failed: {exc}"}

    try:
        response = client.create_tweet(text=text, media_ids=media_ids)
    except Exception as exc:
        return {"error": str(exc)}

    tweet_id = None
    if hasattr(response, "data") and isinstance(response.data, dict):
        tweet_id = response.data.get("id")
    elif isinstance(response, dict):
        tweet_id = response.get("id") or response.get("data", {}).get("id")

    try:
        username = api.verify_credentials().screen_name
    except Exception:
        username = ""

    url = (
        f"https://twitter.com/{username}/status/{tweet_id}"
        if tweet_id and username
        else None
    )
    return {
        "id": tweet_id,
        "link": url,
        "site": "twitter",
    }


def post_to_wordpress(
    account: str,
    title: str,
    content: str,
    slug: Optional[str] = None,
    media: Optional[List[WordpressMediaItem]] = None,
    paid_content: Optional[str] = None,
    paid_title: Optional[str] = None,
    paid_message: Optional[str] = None,
    plan_id: Optional[str] = None,
    categories: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
):
    if account in WORDPRESS_ACCOUNT_ERRORS:
        return {"error": "Account misconfigured"}
    client = WORDPRESS_CLIENTS.get(account)
    if not client:
        return {"error": "Account not configured"}

    images: List[tuple[Path, str, Optional[str]]] = []
    if media:
        for item in media:
            try:
                data = base64.b64decode(item.data)
                tmp = tempfile.NamedTemporaryFile(
                    delete=False, suffix=Path(item.filename).suffix
                )
                tmp.write(data)
                tmp.flush()
                tmp.close()
                images.append((Path(tmp.name), item.filename, item.alt))
            except Exception as exc:
                for p, _, _ in images:
                    try:
                        os.unlink(p)
                    except Exception:
                        pass
                return {"error": f"Media upload failed: {exc}"}

    try:
        result = service_post_to_wordpress(
            title,
            content,
            images,
            account,
            paid_content=paid_content,
            paid_title=paid_title,
            paid_message=paid_message,
            plan_id=plan_id,
            categories=categories,
            tags=tags,
            slug=slug,
        )
    finally:
        for p, _, _ in images:
            try:
                os.unlink(p)
            except Exception:
                pass
    return result

@app.get("/")
async def root():
    return {"status": "ok"}

@app.post("/post")
async def receive_post(data: PostRequest):
    # For now just log that data was received
    media_count = len(data.media or [])
    return {"received": True, "media_items": media_count}


@app.post("/mastodon/post")
async def mastodon_post(data: MastodonPostRequest):
    return post_to_mastodon(data.account, data.text, data.media)


@app.post("/twitter/post")
async def twitter_post(data: TwitterPostRequest):
    return post_to_twitter(data.account, data.text, data.media)


@app.post("/wordpress/post")
async def wordpress_post(data: WordpressPostRequest):
    post_info = post_to_wordpress(
        data.account,
        data.title,
        data.content,
        slug=data.slug,
        media=data.media,
        paid_content=data.paid_content,
        paid_title=data.paid_title,
        paid_message=data.paid_message,
        plan_id=data.plan_id,
        categories=data.categories,
        tags=data.tags,
    )
    return post_info


@app.get("/wordpress/posts")
async def wordpress_posts(
    page: int = Query(1, gt=0),
    number: int = Query(10, gt=0),
    account: str | None = None,
):
    return service_list_posts(account, page, number)


@app.delete("/wordpress/posts")
async def wordpress_delete_posts(
    ids: List[int] = Query(...),
    account: str | None = None,
):
    result = service_delete_posts(account, ids)
    success = len(result.get("deleted", []))
    failed = len(result.get("errors", {}))
    return {**result, "success": success, "failed": failed}


@app.get("/wordpress/stats/views")
async def wordpress_post_views(
    post_id: int = Query(..., gt=0),
    days: int = Query(..., gt=0, le=30),
    account: str | None = None,
):
    return service_get_post_views(account, post_id, days)


@app.get("/wordpress/stats/search-terms")
async def wordpress_search_terms(
    days: int = Query(..., gt=0, le=30),
    account: str | None = None,
):
    return service_get_search_terms(account, days)


@app.post("/note/draft")
async def note_draft(data: NotePostRequest):
    paths = [Path(p) for p in data.images] if data.images else []
    return post_to_note(data.content, paths, data.account)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8765)
