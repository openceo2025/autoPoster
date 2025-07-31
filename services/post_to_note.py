import json
from pathlib import Path
from typing import List

from note_client import NoteClient

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.json"

if CONFIG_PATH.exists():
    with CONFIG_PATH.open() as fh:
        CONFIG = json.load(fh)
else:
    CONFIG = {}


def create_note_client(account: str | None = None) -> NoteClient | None:
    """Initialize a NoteClient using the specified Note account."""
    note_cfg = CONFIG.get("note", {})
    accounts = note_cfg.get("accounts") or {}
    if not accounts:
        print("No Note accounts configured")
        return None

    acct = None
    if account:
        acct = accounts.get(account)
        if not acct:
            print(f"No Note account configured for {account}")
            return None
    elif "default" in accounts:
        acct = accounts["default"]
    else:
        acct = next(iter(accounts.values()))

    cfg = {"note": {"username": acct.get("username"), "password": acct.get("password")}}
    if note_cfg.get("base_url"):
        cfg["note"]["base_url"] = note_cfg["base_url"]

    try:
        client = NoteClient(cfg)
        client.login()
        return client
    except Exception as exc:
        print(f"Failed to init Note client: {exc}")
        print(f"CONFIG used for NoteClient: {cfg}")
        return None


NOTE_CLIENT = create_note_client()


def post_to_note(content: str, images: List[Path] = [], account: str | None = None) -> dict:
    """Create a Note draft with optional images and return draft details."""
    client = NOTE_CLIENT if account is None else create_note_client(account)
    if client is None:
        print('NOTE_CLIENT is None')
        return {"error": "Note client unavailable"}

    body = f"<p>{content}</p>"
    for img in images:
        if not img.exists():
            return {"error": f"Image file not found: {img}"}
        try:
            url = client.upload_image(img)
            body += f'<img src="{url}" />'
        except Exception as exc:
            return {"error": f"Image upload failed: {exc}"}

    try:
        draft_info = client.create_draft("Auto Post", body)
    except Exception as exc:
        return {"error": str(exc)}

    return draft_info
