import json
from pathlib import Path
from typing import List, Optional, Dict

import base64
from io import BytesIO
from mastodon import Mastodon
import tweepy
from note_client import NoteClient
from services.post_to_note import post_to_note

from fastapi import FastAPI
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
        client.status_post(text, media_ids=media_ids)
    except Exception as exc:
        return {"error": str(exc)}

    return {"posted": True}


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
        client.create_tweet(text=text, media_ids=media_ids)
    except Exception as exc:
        return {"error": str(exc)}

    return {"posted": True}

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


@app.post("/note/draft")
async def note_draft(data: NotePostRequest):
    paths = [Path(p) for p in data.images] if data.images else []
    return post_to_note(data.content, paths, data.account)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8765)
