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


def create_note_client() -> NoteClient | None:
    """Initialize a NoteClient and log in."""
    try:
        client = NoteClient(CONFIG)
        client.login()
        return client
    except Exception as exc:
        print(f"Failed to init Note client: {exc}")
        print(f"CONFIG used for NoteClient: {CONFIG}")
        return None


NOTE_CLIENT = create_note_client()


def post_to_note(content: str, images: List[Path] = []) -> dict:
    """Create a Note draft with optional images and return draft details."""
    if NOTE_CLIENT is None:
        print('NOTE_CLIENT is None')
        return {"error": "Note client unavailable"}

    body = f"<p>{content}</p>"
    for img in images:
        try:
            url = NOTE_CLIENT.upload_image(img)
            body += f'<img src="{url}" />'
        except Exception as exc:
            return {"error": f"Image upload failed: {exc}"}

    try:
        draft_info = NOTE_CLIENT.create_draft("Auto Post", body)
    except Exception as exc:
        return {"error": str(exc)}

    return draft_info
