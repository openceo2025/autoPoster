import json
from pathlib import Path
from typing import List, Optional, Dict

from fastapi import FastAPI
from pydantic import BaseModel

import mastodon_service
import twitter_service
import note_service

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"

# Load config if available
if CONFIG_PATH.exists():
    with CONFIG_PATH.open() as f:
        CONFIG = json.load(f)
else:
    CONFIG = {}

app = FastAPI(title="autoPoster")

# --- Mastodon setup ---
MASTODON_ACCOUNT_ERRORS = mastodon_service.validate_accounts(CONFIG)
if MASTODON_ACCOUNT_ERRORS:
    for acc, err in MASTODON_ACCOUNT_ERRORS.items():
        print(f"Mastodon config error for {acc}: {err}")
MASTODON_CLIENTS = mastodon_service.create_clients(CONFIG, MASTODON_ACCOUNT_ERRORS)

# --- Twitter setup ---
TWITTER_ACCOUNT_ERRORS = twitter_service.validate_accounts(CONFIG)
if TWITTER_ACCOUNT_ERRORS:
    for acc, err in TWITTER_ACCOUNT_ERRORS.items():
        print(f"Twitter config error for {acc}: {err}")
TWITTER_CLIENTS = twitter_service.create_clients(CONFIG, TWITTER_ACCOUNT_ERRORS)

# --- Note setup ---
NOTE_ACCOUNT_ERRORS = note_service.validate_accounts(CONFIG)
if NOTE_ACCOUNT_ERRORS:
    for acc, err in NOTE_ACCOUNT_ERRORS.items():
        print(f"Note config error for {acc}: {err}")
NOTE_ACCOUNTS = note_service.load_accounts(CONFIG, NOTE_ACCOUNT_ERRORS)

# Expose selectors for tests
NOTE_SELECTORS = note_service.NOTE_SELECTORS


def validate_mastodon_accounts(config: Dict) -> Dict[str, str]:
    return mastodon_service.validate_accounts(config)


def create_mastodon_clients():
    return mastodon_service.create_clients(CONFIG, MASTODON_ACCOUNT_ERRORS)


def validate_twitter_accounts(config: Dict) -> Dict[str, str]:
    return twitter_service.validate_accounts(config)


def create_twitter_clients():
    return twitter_service.create_clients(CONFIG, TWITTER_ACCOUNT_ERRORS)


def validate_note_accounts(config: Dict) -> Dict[str, str]:
    return note_service.validate_accounts(config)


def load_note_accounts():
    return note_service.load_accounts(CONFIG, NOTE_ACCOUNT_ERRORS)


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
    text: str
    media: Optional[List[str]] = None
    thumbnail: Optional[str] = None
    paid: bool
    tags: Optional[List[str]] = None


# Wrapper functions -----------------------------------------------------------

def post_to_mastodon(account: str, text: str, media: Optional[List[str]] = None):
    return mastodon_service.post_to_mastodon(
        account,
        text,
        media,
        clients=MASTODON_CLIENTS,
        account_errors=MASTODON_ACCOUNT_ERRORS,
    )


def post_to_twitter(account: str, text: str, media: Optional[List[str]] = None):
    return twitter_service.post_to_twitter(
        account,
        text,
        media,
        clients=TWITTER_CLIENTS,
        account_errors=TWITTER_ACCOUNT_ERRORS,
    )


def post_to_note(
    account: str,
    text: str,
    media: List[str],
    thumbnail: str,
    paid: bool,
    tags: List[str],
):
    return note_service.post_to_note(
        account,
        text,
        media,
        thumbnail,
        paid,
        tags,
        accounts=NOTE_ACCOUNTS,
        account_errors=NOTE_ACCOUNT_ERRORS,
    )


# API Routes -----------------------------------------------------------------

@app.get("/")
async def root():
    return {"status": "ok"}


@app.post("/post")
async def receive_post(data: PostRequest):
    media_count = len(data.media or [])
    return {"received": True, "media_items": media_count}


@app.post("/mastodon/post")
async def mastodon_post(data: MastodonPostRequest):
    return post_to_mastodon(data.account, data.text, data.media)


@app.post("/twitter/post")
async def twitter_post(data: TwitterPostRequest):
    return post_to_twitter(data.account, data.text, data.media)


@app.post("/note/post")
async def note_post(data: NotePostRequest):
    return post_to_note(
        data.account,
        data.text,
        data.media or [],
        data.thumbnail or "",
        data.paid,
        data.tags or [],
    )


if __name__ == "__main__":
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(description="autoPoster server")
    parser.add_argument(
        "--show-browser",
        action="store_true",
        help="Launch Selenium with a visible browser window",
    )
    args = parser.parse_args()

    if args.show_browser:
        note_service.HEADLESS = False

    uvicorn.run(app, host="127.0.0.1", port=8765)
