import base64
import json
import requests

URL = "http://localhost:8765/wordpress/post"
ACCOUNT = "account1"  # must match an entry in config.json
TITLE = "これはWordPressへの自動投稿テストです"
CONTENT = "自動投稿された記事の本文です"
MEDIA_PATH = "/path/to/image.png"  # replace with an actual file path


def main():
    # Read the media file and encode as base64
    with open(MEDIA_PATH, "rb") as f:
        media_b64 = base64.b64encode(f.read()).decode("utf-8")

    payload = {
        "account": ACCOUNT,
        "title": TITLE,
        "content": CONTENT,
        "media": [media_b64],
    }

    headers = {"Content-Type": "application/json"}
    resp = requests.post(URL, data=json.dumps(payload), headers=headers)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text}")


if __name__ == "__main__":
    main()
