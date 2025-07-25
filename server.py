import json
from pathlib import Path
from typing import List, Optional

from mastodon import Mastodon

from fastapi import FastAPI
from pydantic import BaseModel

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"

# Load config if available
if CONFIG_PATH.exists():
    with CONFIG_PATH.open() as f:
        CONFIG = json.load(f)
else:
    CONFIG = {}

app = FastAPI(title="autoPoster")

class PostRequest(BaseModel):
    text: str
    media: Optional[List[str]] = None  # base64 encoded strings


class MastodonPostRequest(BaseModel):
    account: str
    text: str
    media: Optional[List[str]] = None

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
    accounts = CONFIG.get("mastodon", {}).get("accounts", {})
    account_conf = accounts.get(data.account)
    if not account_conf:
        return {"error": "Account not configured"}

    client = Mastodon(
        access_token=account_conf["access_token"],
        api_base_url=account_conf["instance_url"],
    )

    client.status_post(data.text, media_ids=None)
    return {"posted": True}

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8765)
