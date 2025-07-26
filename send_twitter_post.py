import base64
import json
import requests

URL = "http://localhost:8765/twitter/post"
ACCOUNT = "account1"  # must match an entry in config.json
TEXT = "これはTwitterへの自動投稿テストです"
MEDIA_PATH = "/path/to/image.png"  # replace with an actual file path


def main():
    # Read the media file and encode as base64
    with open(MEDIA_PATH, "rb") as f:
        media_b64 = base64.b64encode(f.read()).decode("utf-8")

    payload = {
        "account": ACCOUNT,
        "text": TEXT,
        "media": [media_b64],
    }

    headers = {"Content-Type": "application/json"}
    resp = requests.post(URL, data=json.dumps(payload), headers=headers)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text}")


if __name__ == "__main__":
    main()
