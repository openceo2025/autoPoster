# autoPoster

A simple REST API that receives post requests and forwards them to various services.

## Setup

1. Copy `config.sample.json` to `config.json` and fill in your account details.
   To add Mastodon accounts, include a `mastodon` section like this:

   ```json
   "mastodon": {
       "accounts": {
           "account1": {
               "instance_url": "https://mastodon.example",
               "access_token": "YOUR_TOKEN"
           }
       }
    }
    ```
   To configure Twitter accounts, add a `twitter` section with credentials for
   each account:

   ```json
   "twitter": {
       "accounts": {
           "account1": {
               "consumer_key": "YOUR_CONSUMER_KEY",
               "consumer_secret": "YOUR_CONSUMER_SECRET",
               "access_token": "YOUR_ACCESS_TOKEN",
               "access_token_secret": "YOUR_ACCESS_TOKEN_SECRET",
               "bearer_token": "YOUR_BEARER_TOKEN"
           }
       }
   }
   ```
2. Install dependencies. The project uses `Mastodon.py`, `requests`, and `tweepy`;
   the test suite relies on `pytest` and `httpx`. Install everything with:
   ```bash
   pip install -r requirements.txt
   ```
3. Install a compatible WebDriver such as **ChromeDriver** or **geckodriver**
   and ensure it is available on your `PATH` so Selenium can launch the browser.
4. Run the server:
   ```bash
   python server.py
   ```
   The API will start on `http://localhost:8765`.
5. To execute the tests, run:
   ```bash
   pytest
   ```

## Note

To automate posts on [note.com](https://note.com), add a `note` section to
`config.json` describing each account:

```json
"note": {
    "accounts": {
        "account1": {
            "username": "your_username",
            "password": "your_password"
        }
    }
}
```

The server uses Selenium with headless Chrome to publish notes. Install Google
Chrome and a matching **ChromeDriver** (or another WebDriver such as
geckodriver) and ensure the driver binary is available on your `PATH`. You do
not need to run the driver yourself&mdash;`server.py` launches it automatically
when a request to `/note/post` is processed. After logging in the automation
opens the top page, clicks **投稿** and then **新しく記事を書く** to reach the
editor.

## API

### `POST /post`

Send JSON with the following structure:

```json
{
  "text": "Post body",
  "media": ["base64string1", "base64string2"]
}
```

`media` is optional and should contain base64 encoded content of images or videos.

This initial version only acknowledges the request.

### `POST /mastodon/post`

Submit a toot to one of the configured Mastodon accounts. The JSON payload must
include the `account` key matching a name from the `mastodon.accounts` section
of `config.json`.

```json
{
  "account": "account1",
  "text": "Hello world",
  "media": ["base64image"]
}
```

`media` is optional and should be a list of base64 encoded strings representing
the files you want uploaded alongside the toot. The server decodes each
element, then uploads the bytes to Mastodon using `media_post`. If no MIME type
is specified for the upload, the server defaults to `application/octet-stream`.
No explicit size or type validation is performed, so keep each file within the limits
accepted by your Mastodon instance (often up to around 40 MB for images or
video) and in a supported format such as PNG, JPEG, GIF or MP4.

Example using `curl`:

```bash
curl -X POST http://localhost:8765/mastodon/post \
     -H 'Content-Type: application/json' \
     -d '{"account": "account1", "text": "Hello world", "media": ["b64"]}'
```

### `POST /twitter/post`

Send a tweet from one of the configured Twitter accounts. The JSON payload must
include the `account` key matching a name from the `twitter.accounts` section of
`config.json`.

```json
{
  "account": "account1",
  "text": "Hello Twitter",
  "media": ["base64image"]
}
```

`media` is optional and should be a list of base64 encoded strings representing
files that will be uploaded and attached to the tweet. Each account entry in
`config.json` needs valid `consumer_key`, `consumer_secret`, `access_token`,
`access_token_secret` and `bearer_token` values for authentication.

Example using `curl`:

```bash
curl -X POST http://localhost:8765/twitter/post \
     -H 'Content-Type: application/json' \
     -d '{"account": "account1", "text": "Hello Twitter", "media": ["b64"]}'
```

### `POST /note/post`

Post to one of the configured Note accounts. The JSON payload must include the
`account` key matching an entry under `note.accounts` in `config.json`.

```json
{
  "account": "account1",
  "text": "Hello Note",
  "media": ["base64image"],
  "thumbnail": "base64thumb",
  "paid": true,
  "tags": ["tag1", "tag2"]
}
```

`thumbnail` is optional and should contain a base64 encoded image used as the
post's thumbnail. Set `paid` to `true` to publish a paid note or `false` for a
free note. `tags` is optional and accepts a list of tags.

Example paid post:

```bash
curl -X POST http://localhost:8765/note/post \
     -H 'Content-Type: application/json' \
     -d '{"account": "account1", "text": "Hello Note", "thumbnail": "b64thumb", "paid": true, "tags": ["tag1", "tag2"]}'
```

Example free post:

```bash
curl -X POST http://localhost:8765/note/post \
     -H 'Content-Type: application/json' \
     -d '{"account": "account1", "text": "Another Note", "paid": false, "tags": []}'
```

## Troubleshooting

If requests to `/mastodon/post` or `/twitter/post` return
`{ "error": "Account misconfigured" }`, the server detected problems with your
account configuration during startup.

For Mastodon accounts, verify that:

* `mastodon.accounts` is present and not empty in `config.json`.
* Each account defines `instance_url` and `access_token` values.

For Twitter accounts, ensure every entry under `twitter.accounts` includes
`consumer_key`, `consumer_secret`, `access_token`, `access_token_secret` and
`bearer_token` without placeholder values.

Check the server logs for messages like `Mastodon config error for account1` or
`Twitter config error for account1` and update `config.json` with the correct
information before restarting the server.

