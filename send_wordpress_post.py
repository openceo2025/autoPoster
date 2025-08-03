import base64
import json
from pathlib import Path

import requests

URL = "http://localhost:8765/wordpress/post"
ACCOUNT = "nicchi"  # must match an entry in config.json
TITLE = "これはWordPressへの自動投稿テストです"
CONTENT = "自動投稿された記事の本文です"
MEDIA_PATH = "example/b6701f05-1e2e-4776-a7c3-69c13c469514.png"  # replace with an actual file path
# Text visible only to paid subscribers. Replace with your own text or set to
# ``None`` to omit the paid block entirely.
PAID_CONTENT = "ここから先は有料会員限定です"


def main():
    # Read the media file and encode as base64
    with open(MEDIA_PATH, "rb") as f:
        media_b64 = base64.b64encode(f.read()).decode("utf-8")

    payload = {
        "account": ACCOUNT,
        "title": TITLE,
        "content": CONTENT,
        "media": [
            {
                "filename": Path(MEDIA_PATH).name,
                "data": media_b64,
            }
        ],
        # Remove this key or set ``PAID_CONTENT`` to ``None`` if you do not want
        # to include a premium content block in the post.
        "paid_content": PAID_CONTENT,
    }

    headers = {"Content-Type": "application/json"}
    resp = requests.post(URL, data=json.dumps(payload), headers=headers)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text}")


if __name__ == "__main__":
    main()
