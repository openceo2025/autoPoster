import json
import requests

URL = "http://localhost:8765/note/draft"
CONTENT = "これはNoteの下書きテストです"
IMAGE_PATH = "example/b6701f05-1e2e-4776-a7c3-69c13c469514.png"  # replace with an actual file path


def main():
    payload = {
        "account": "default",
        "content": CONTENT,
        "images": [IMAGE_PATH],
    }

    headers = {"Content-Type": "application/json"}
    resp = requests.post(URL, data=json.dumps(payload), headers=headers)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text}")


if __name__ == "__main__":
    main()
