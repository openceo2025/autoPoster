# autoPoster

A simple REST API that receives post requests and forwards them to various services.

### Recent features

- Accepts ALT text for images and stores it in the WordPress media library.
- Supports post `slug` and `excerpt` fields for better SEO control.
- Appends custom or auto‑generated JSON‑LD structured data to WordPress posts.

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

All endpoints that publish content return a JSON object in the following format on success:

```json
{ "id": 1, "link": "https://example.com/post/1", "site": "service" }
```

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

Sample response:

```json
{ "id": 1, "link": "https://mastodon.example/@user/1", "site": "mastodon" }
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

Sample response:

```json
{ "id": "123", "link": "https://twitter.com/user/status/123", "site": "twitter" }
```

### `POST /wordpress/post`

Create and publish a post on WordPress.com. The JSON body must specify the
target `account` (matching `wordpress.accounts` in `config.json`), a `title`,
and `content`.

Optional fields:

- `slug`: Permalink slug used for the post URL.
- `excerpt`: Short summary or description.
- `media`: list of image objects with `filename`, base64‑encoded `data`, and
  optional `alt` text. Images are uploaded and inserted into the post body; the
  first image becomes the featured image (アイキャッチ). When provided, ALT text is
  saved to the WordPress media library.
- `json_ld`: Structured data appended to the post body as a `<script
  type="application/ld+json">` block. When omitted, a basic object is generated
  from the title and content.

Ensure your files are within WordPress's upload limits and in supported formats
such as PNG or JPEG.

```json
{
  "account": "account1",
  "title": "Hello WP",
  "content": "Article body",
  "slug": "hello-wp",
  "excerpt": "Short summary",
  "media": [
    { "filename": "img.png", "data": "base64image", "alt": "Alt text" }
  ],
  "json_ld": { "@type": "NewsArticle" }
}
```

Example using `curl`:

```bash
curl -X POST http://localhost:8765/wordpress/post \
     -H 'Content-Type: application/json' \
     -d '{"account": "account1", "title": "Hello WP", "content": "Article body", "media": [{"filename": "img.png", "data": "b64", "alt": "Alt text"}]}'
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
  "site": "wordpress"
}
```

All services respond using this common `{id, link, site}` format.

If the site does not have a plan that supports Premium Content, WordPress.com
returns an error and the API responds with a message such as `{"error":
"Paid content block requires an upgrade"}` and the post is not published.

### `GET /wordpress/stats/views`

Retrieve daily view counts for a specific post.

Query parameters:

- `account`: WordPress account name from `config.json`.
- `post_id`: ID of the post to fetch stats for.
- `days`: Number of days of statistics to return.

Example using `curl`:

```bash
curl "http://localhost:8765/wordpress/stats/views?account=account1&post_id=10&days=3"
```

Sample response:

```json
{ "views": [1, 2, 3] }
```

### `GET /wordpress/stats/search-terms`

Retrieve the search terms that led visitors to your site.

Query parameters:

- `account`: WordPress account name from `config.json`.
- `days`: Number of days of statistics to return.

Example using `curl`:

```bash
curl "http://localhost:8765/wordpress/stats/search-terms?account=account1&days=30"
```

Sample response:

```json
{
  "terms": [
    { "term": "example", "views": 5 },
    { "term": "hello", "views": 2 }
  ]
}
```

### `POST /wordpress/stats/pv-csv`

Export per-post view counts for all configured WordPress.com accounts as CSV files.

Query parameters:

- `days`: Number of recent days to include (default `30`).
- `out_dir`: Directory to write the CSV files to. Use `csv` to save them under the built-in `csv/` folder.

The generated CSV has columns in the order
`account, site, post_id, title, pv_day1 … pv_day7` when `days` is set to `7`.

Example using `curl`:

```bash
curl -X POST "http://localhost:8765/wordpress/stats/pv-csv?days=7&out_dir=csv"
```

### Standalone CSV generation

You can generate the same statistics without running the server:

```bash
python generate_pv_csv.py --days 7 --out-dir csv
```

A single file named `pv_<timestamp>.csv` (e.g., `pv_20230102_030405.csv`) is
produced in the specified directory, with one row per post and the account name
in the first column.

### `GET /wordpress/posts`

List recent posts on a WordPress.com site.

Query parameters:

- `account`: WordPress account name from `config.json`.
- `page`: Page number to fetch (default 1).
- `number`: Number of posts per page (default 10).

Example using `curl`:

```bash
curl "http://localhost:8765/wordpress/posts?account=account1&page=1&number=5"
```

Sample response:

```json
{
  "posts": [
    { "id": 1, "title": "Example", "date": "2020-01-01T00:00:00", "url": "http://post" }
  ]
}
```

### `DELETE /wordpress/posts`

Delete multiple posts on WordPress.com by ID.

Query parameters:

- `account`: WordPress account name from `config.json`.
- `ids`: One or more post IDs to delete. Specify `ids` multiple times in the query string.

Example using `curl`:

```bash
curl -X DELETE "http://localhost:8765/wordpress/posts?account=account1&ids=1&ids=2"
```

Sample response:

```json
{
  "deleted": [1, 2],
  "errors": {},
  "success": 2,
  "failed": 0
}
```

If an individual deletion fails, the `errors` object maps the post ID to an error message and the `failed` count is incremented.

### `POST /wordpress/cleanup`

Remove old posts and unattached media for one or more WordPress.com accounts.

Request body:

```json
{
  "items": [
    { "identifier": "account1", "keep_latest": 10 },
    { "identifier": "account2", "keep_latest": 5 }
  ]
}
```

For each identifier, the API keeps the specified number of most recent posts and deletes older ones. If an identifier does not match any account in `config.json`, the result contains an `error` field. After deleting posts, the trash is emptied and unattached media are removed automatically.

Sample response:

```json
{
  "results": [
    { "account": "account1", "deleted_posts": [1, 2], "errors": {}, "trash_emptied": 2, "deleted_media": 3 },
    { "account": "unknown", "error": "Account not found" }
  ]
}
```

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

Sample response:

```json
{ "id": 5, "link": "https://note.com/.../draft", "site": "note" }
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
