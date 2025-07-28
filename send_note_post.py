import base64
import json
import requests

URL = "http://localhost:8765/note/post"
ACCOUNT = "account1"  # must match an entry in config.json
TEXT = "これはnoteへの自動投稿テストです"
THUMBNAIL_PATH = "/path/to/thumbnail.png"  # replace with an actual file path
MEDIA_PATHS = ["/path/to/image1.png", "/path/to/image2.png"]  # optional additional images
PAID = False
TAGS = ["test", "auto"]


def _encode_file(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def main():
    thumbnail_b64 = _encode_file(THUMBNAIL_PATH) if THUMBNAIL_PATH else ""
    media_b64 = [_encode_file(p) for p in MEDIA_PATHS if p]

    payload = {
        "account": ACCOUNT,
        "text": TEXT,
        "media": media_b64,
        "thumbnail": thumbnail_b64,
        "paid": PAID,
        "tags": TAGS,
    }

    headers = {"Content-Type": "application/json"}
    resp = requests.post(URL, data=json.dumps(payload), headers=headers)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text}")


if __name__ == "__main__":
    main()
