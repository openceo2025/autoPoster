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
    To post drafts to Note, include a `note` section. `base_url` is optional and
    defaults to `https://note.com`:

    ```json
      "note": {
          "accounts": {
              "default": {
                  "username": "YOUR_NOTE_USERNAME",
                  "password": "YOUR_NOTE_PASSWORD"
              }
          },
          "base_url": "https://note.com"
      }
      ```

     To publish to WordPress.com, include a `wordpress` section with account and
     OAuth2 credentials. `site` should be your WordPress.com domain or numeric
     site ID. Register an application at
     <https://developer.wordpress.com/apps/> to obtain `client_id` and
     `client_secret`, and enable the **password** grant type. The server will
     use the provided `username` and `password` to request an access token when
     posting.

     ```json
     "wordpress": {
         "accounts": {
            "account1": {
                "site": "your-site.wordpress.com",
                "client_id": "YOUR_CLIENT_ID",
                "client_secret": "YOUR_CLIENT_SECRET",
                "username": "YOUR_USERNAME",
                "password": "YOUR_PASSWORD",
                "plan_id": null
            }
        }
    }
    ```

     OAuth2 setup:

     1. Visit <https://developer.wordpress.com/apps/> and create a new
        application.
     2. Enable the **password** grant type and note the provided `client_id` and
        `client_secret`.
     3. Fill those values along with your WordPress.com `username` and
        `password` in `config.json`. Include `plan_id` if you want to restrict
        Premium Content to a specific membership plan. The server exchanges
        these for an access token via
        `https://public-api.wordpress.com/oauth2/token` when posting.
2. Install dependencies. The project uses `Mastodon.py`, `requests`, and `tweepy`;
   the test suite relies on `pytest` and `httpx`. Install everything with:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the server:
   ```bash
   python server.py
   ```
   The API will start on `http://localhost:8765`.
4. To execute the tests, run:
   ```bash
   pytest
   ```

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

### `POST /wordpress/post`

Create and publish a post on WordPress.com. The JSON body must specify the
target `account` (matching `wordpress.accounts` in `config.json`), a `title`,
and `content`. Optionally include `media`, a list of base64‑encoded images. Each
image is uploaded and inserted into the post body; the first uploaded image is
also set as the featured image (アイキャッチ). Ensure your files are within
WordPress's upload limits and in supported formats such as PNG or JPEG.

```json
{
  "account": "account1",
  "title": "Hello WP",
  "content": "Article body",
  "media": ["base64image"]
}
```

Example using `curl`:

```bash
curl -X POST http://localhost:8765/wordpress/post \
     -H 'Content-Type: application/json' \
     -d '{"account": "account1", "title": "Hello WP", "content": "Article body", "media": ["b64"]}'
```

#### Premium content (`paid_content`)
Use the optional `paid_content` field to insert a Premium Content block that is
visible only to paying subscribers. This feature requires a WordPress.com plan
that supports the Premium Content block (for example, the **Creator** or
**Commerce** plan). To limit the block to a specific membership plan, supply the
`plan_id`. You can retrieve available plan IDs with an authenticated request:

```bash
curl -H "Authorization: Bearer <TOKEN>" \
     https://public-api.wordpress.com/wpcom/v2/sites/<site>/plans
```

Use the `id` field from the response (e.g. `"plan_basic"`) as the `plan_id` in
your request. You can also customize the block's heading and upsell message with
`paid_title` and `paid_message`.

```json
{
  "account": "account1",
  "title": "Hello WP",
  "content": "Article body",
  "paid_content": "Subscriber only text",
  "paid_title": "Members only",
  "paid_message": "Subscribe to continue",
  "plan_id": "plan_basic"
}
```

Example using `curl`:

```bash
curl -X POST http://localhost:8765/wordpress/post \
     -H 'Content-Type: application/json' \
     -d '{"account": "account1", "title": "Hello WP", "content": "Article body", "paid_content": "Subscriber only text", "paid_title": "Members only", "paid_message": "Subscribe to continue", "plan_id": "plan_basic"}'
```

Sample response:

```json
{
  "id": 10,
  "link": "http://post",
  "site": "your-site.wordpress.com"
}
```

Clients should store the `{site, id}` pair for Stats API calls.

If the site does not have a plan that supports Premium Content, WordPress.com
returns an error and the API responds with a message such as `{"error":
"Paid content block requires an upgrade"}` and the post is not published.

### `POST /note/draft`

Create a draft on a configured Note account. Specify the account name in
`account`, send the draft text in `content`, and optionally include images by
providing a list of **file paths** in the `images` list. Each path should point
to a file accessible to the server and will be uploaded via
`/api/v1/upload_image` before being inserted into the draft body.

```json
{
  "account": "default",
  "content": "Hello Note",
  "images": ["example/test.png"]
}
```

Example using `curl`:

```bash
curl -X POST http://localhost:8765/note/draft \
     -H 'Content-Type: application/json' \
     -d '{"account": "default", "content": "Hello Note", "images": ["example/test.png"]}'
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


## Development status

現在このプロジェクトは一時停止中です。WordPress 投稿はカテゴリとタグを指定でき、`paid_content` を使ったプレミアムコンテンツブロックも挿入できますが、WordPress.com 側の制約により有料コンテンツ機能の検証は進んでいません。また、メディアアップロードのレスポンス解析が不完全なため、画像が壊れて表示される既知の問題があります。

次に再開する際は、上記の画像処理の修正と有料コンテンツ機能の仕上げに取り組んでください。詳細なタスクは `AGENTS.md` を参照してください。
