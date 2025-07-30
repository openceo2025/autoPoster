import base64
import json
import requests

URL = "http://localhost:8765/note/post"
ACCOUNT = "nicchi"  # must match an entry in config.json
TEXT = "これはテスト投稿です"
THUMBNAIL_PATH = "example/titeletest.png"  # replace with the path to your thumbnail
MEDIA_PATHS = [
    "example/b6701f05-1e2e-4776-a7c3-69c13c469514.png",
    "example/b6701f05-1e2e-4776-a7c3-69c13c46sssss9514.jpg",
]  # optional additional images
PAID = False
TAGS = ["test", "ai生成"]


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
