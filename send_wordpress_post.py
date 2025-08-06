import base64
import json
from pathlib import Path

import requests

URL = "http://localhost:8765/wordpress/post"
ACCOUNT = "nicchi"  # must match an entry in config.json
TITLE = "これはWordPressへの自動投稿テストです12"
CONTENT = "自動投稿された記事の本文です"
MEDIA_PATH = "example/sss.png"  # replace with an actual file path
# Text visible only to paid subscribers. Replace with your own text or set to
# ``None`` to omit the paid block entirely.
PAID_CONTENT = None
# Heading displayed above the premium content block. Set to ``None`` to omit
# the heading entirely.
PAID_TITLE = None
# Message shown to visitors without access. Set to ``None`` to use the
# WordPress default message.
PAID_MESSAGE = None
# Subscription plan that grants access to the paid block. Set to ``None`` to
# use the plan configured for the WordPress account.
PLAN_ID = None# これたぶん25じゃない？


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
        # Heading for the premium block; set ``PAID_TITLE`` to ``None`` or remove
        # this key to omit the heading entirely.
        "paid_title": PAID_TITLE,
        # Message shown to visitors without access; set ``PAID_MESSAGE`` to
        # ``None`` or remove the key to use WordPress's default message.
        "paid_message": PAID_MESSAGE,
        # Identifier of the subscription plan that unlocks the premium block;
        # set ``PLAN_ID`` to ``None`` or remove the key to use the plan
        # configured for the WordPress account.
        "plan_id": PLAN_ID,
    }

    headers = {"Content-Type": "application/json"}
    resp = requests.post(URL, data=json.dumps(payload), headers=headers)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text}")


if __name__ == "__main__":
    main()
