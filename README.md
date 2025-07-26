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
2. Install dependencies. The project uses `Mastodon.py` and `requests`; the test
   suite relies on `pytest` and `httpx`. Install everything with:
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
the files you want uploaded alongside the toot.

Example using `curl`:

```bash
curl -X POST http://localhost:8765/mastodon/post \
     -H 'Content-Type: application/json' \
     -d '{"account": "account1", "text": "Hello world", "media": ["b64"]}'
```

