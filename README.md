# autoPoster

A simple REST API that receives post requests and forwards them to various services.

## Setup

1. Copy `config.sample.json` to `config.json` and fill in your account details.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the server:
   ```bash
   python server.py
   ```
   The API will start on `http://localhost:8765`.

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
