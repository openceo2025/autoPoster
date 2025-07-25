import json
import urllib.request


def main():
    url = "http://localhost:8765/post"
    payload = {"text": "test"}
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}

    print(f"Sending POST request to {url} with payload: {payload}")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as response:
            body = response.read().decode("utf-8")
            print(f"Response status: {response.status}")
            print(f"Response body: {body}")
    except Exception as exc:
        print(f"Request failed: {exc}")


if __name__ == "__main__":
    main()
