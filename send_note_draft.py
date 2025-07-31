import base64
import json
import requests

URL = "http://localhost:8765/note/draft"
CONTENT = "これはNoteの下書きテストです"
IMAGE_PATH = "/path/to/image.png"  # replace with an actual file path


def main():
    # Read the image file and encode as base64
    with open(IMAGE_PATH, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode("utf-8")

    payload = {
        "content": CONTENT,
        "images": [image_b64],
    }

    headers = {"Content-Type": "application/json"}
    resp = requests.post(URL, data=json.dumps(payload), headers=headers)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text}")


if __name__ == "__main__":
    main()
