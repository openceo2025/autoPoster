import json
from pathlib import Path
from typing import List, Optional, Dict

import os
import tempfile

import base64
from io import BytesIO
from mastodon import Mastodon
import tweepy
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import urllib.parse

from fastapi import FastAPI
from pydantic import BaseModel

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"

# Load config if available
if CONFIG_PATH.exists():
    with CONFIG_PATH.open() as f:
        CONFIG = json.load(f)
else:
    CONFIG = {}

app = FastAPI(title="autoPoster")

# By default Selenium runs in headless mode.  When the server is started with
# the --show-browser flag this global is set to False so a visible browser is
# launched instead.
HEADLESS = True


def validate_mastodon_accounts(config: Dict) -> Dict[str, str]:
    """Validate Mastodon account configuration and return a map of errors."""
    errors: Dict[str, str] = {}
    accounts = config.get("mastodon", {}).get("accounts")
    if not accounts:
        errors["_general"] = "mastodon.accounts section missing or empty"
        return errors

    for name, info in accounts.items():
        account_errors = []
        instance = info.get("instance_url")
        token = info.get("access_token")

        if not instance:
            account_errors.append("missing instance_url")
        elif "mastodon.example" in instance:
            account_errors.append("instance_url looks like a placeholder")

        if not token:
            account_errors.append("missing access_token")
        elif token == "YOUR_TOKEN":
            account_errors.append("access_token looks like a placeholder")

        if account_errors:
            errors[name] = "; ".join(account_errors)
    return errors


MASTODON_ACCOUNT_ERRORS = validate_mastodon_accounts(CONFIG)
if MASTODON_ACCOUNT_ERRORS:
    for acc, err in MASTODON_ACCOUNT_ERRORS.items():
        print(f"Mastodon config error for {acc}: {err}")


def create_mastodon_clients():
    """Create Mastodon clients for all configured accounts."""
    clients = {}
    accounts = CONFIG.get("mastodon", {}).get("accounts", {})
    for name, info in accounts.items():
        if name in MASTODON_ACCOUNT_ERRORS:
            continue
        try:
            clients[name] = Mastodon(
                access_token=info["access_token"],
                api_base_url=info["instance_url"],
            )
        except Exception as exc:
            # Log error but continue creating other clients
            print(f"Failed to init Mastodon client for {name}: {exc}")
    return clients


MASTODON_CLIENTS = create_mastodon_clients()


def validate_note_accounts(config: Dict) -> Dict[str, str]:
    """Validate Note account configuration and return a map of errors."""
    errors: Dict[str, str] = {}
    accounts = config.get("note", {}).get("accounts")
    if not accounts:
        errors["_general"] = "note.accounts section missing or empty"
        return errors

    placeholders = {
        "username": "your_username",
        "password": "your_password",
    }

    for name, info in accounts.items():
        account_errors = []
        for key, placeholder in placeholders.items():
            val = info.get(key)
            if not val:
                account_errors.append(f"missing {key}")
            elif val == placeholder:
                account_errors.append(f"{key} looks like a placeholder")

        if account_errors:
            errors[name] = "; ".join(account_errors)
    return errors


NOTE_ACCOUNT_ERRORS = validate_note_accounts(CONFIG)
if NOTE_ACCOUNT_ERRORS:
    for acc, err in NOTE_ACCOUNT_ERRORS.items():
        print(f"Note config error for {acc}: {err}")


def load_note_accounts():
    """Return credentials for configured Note accounts."""
    accounts = {}
    cfg_accounts = CONFIG.get("note", {}).get("accounts", {})
    for name, info in cfg_accounts.items():
        if name in NOTE_ACCOUNT_ERRORS:
            continue
        accounts[name] = info
    return accounts


NOTE_ACCOUNTS = load_note_accounts()

# CSS selectors and URLs used to automate posting to Note
NOTE_SELECTORS = {
    "login_url": "https://note.com/login?redirectPath=",
    "login_username": "#email",
    "login_password": "#password",
    "login_submit": ".o-login__button button",
    # After login we navigate to the home page then open the editor via the
    # 「投稿」 button. The old ``/notes/new`` URL no longer works directly.
    "home_url": "https://note.com/",
    "post_menu": "//*[self::a or self::button][contains(., '投稿')]",
    "new_post_menu": "//span[contains(., '新しく記事を書く')]",

    # Editor fields use contenteditable DIVs instead of textareas.
    "title_area": "div[data-placeholder='記事タイトル']",
    "text_area": "div[data-placeholder='ご自由にお書きください。']",

    # File inputs appear after clicking their respective UI controls.
    "media_input": "input[type='file']",
    "thumbnail_button": "//button[contains(@aria-label, '画像をアップロード')]",
    "thumbnail_input": "input[type='file']",

    # Paid/free toggle became radio-style labels.
    "paid_tab": "//label[contains(., '有料')]/input",
    "free_tab": "//label[contains(., '無料')]/input",

    # Tags now use a placeholder attribute.
    "tag_input": "input[placeholder='ハッシュタグを追加する']",

    # Publishing now requires two buttons: "公開に進む" then "投稿する"/"更新する".
    "publish_next": "//button[contains(., '公開に進む')]",
    "publish": "//button[contains(., '投稿する') or contains(., '更新する')]",
}


def validate_twitter_accounts(config: Dict) -> Dict[str, str]:
    """Validate Twitter account configuration and return a map of errors."""
    errors: Dict[str, str] = {}
    accounts = config.get("twitter", {}).get("accounts")
    if not accounts:
        errors["_general"] = "twitter.accounts section missing or empty"
        return errors

    placeholders = {
        "consumer_key": "YOUR_CONSUMER_KEY",
        "consumer_secret": "YOUR_CONSUMER_SECRET",
        "access_token": "YOUR_ACCESS_TOKEN",
        "access_token_secret": "YOUR_ACCESS_TOKEN_SECRET",
        "bearer_token": "YOUR_BEARER_TOKEN",
    }

    for name, info in accounts.items():
        account_errors = []
        for key in placeholders:
            val = info.get(key)
            if not val:
                account_errors.append(f"missing {key}")
            elif val == placeholders[key]:
                account_errors.append(f"{key} looks like a placeholder")

        if account_errors:
            errors[name] = "; ".join(account_errors)
    return errors


TWITTER_ACCOUNT_ERRORS = validate_twitter_accounts(CONFIG)
if TWITTER_ACCOUNT_ERRORS:
    for acc, err in TWITTER_ACCOUNT_ERRORS.items():
        print(f"Twitter config error for {acc}: {err}")


def create_twitter_clients():
    """Create Tweepy clients for all configured accounts."""
    clients = {}
    accounts = CONFIG.get("twitter", {}).get("accounts", {})
    for name, info in accounts.items():
        if name in TWITTER_ACCOUNT_ERRORS:
            continue
        try:
            auth = tweepy.OAuth1UserHandler(
                info["consumer_key"],
                info["consumer_secret"],
                info["access_token"],
                info["access_token_secret"],
            )
            api = tweepy.API(auth)
            client = tweepy.Client(
                bearer_token=info["bearer_token"],
                consumer_key=info["consumer_key"],
                consumer_secret=info["consumer_secret"],
                access_token=info["access_token"],
                access_token_secret=info["access_token_secret"],
            )
            clients[name] = {"client": client, "api": api}
        except Exception as exc:
            print(f"Failed to init Twitter client for {name}: {exc}")
    return clients


TWITTER_CLIENTS = create_twitter_clients()

class PostRequest(BaseModel):
    text: str
    media: Optional[List[str]] = None  # base64 encoded strings


class MastodonPostRequest(BaseModel):
    account: str
    text: str
    media: Optional[List[str]] = None


class TwitterPostRequest(BaseModel):
    account: str
    text: str
    media: Optional[List[str]] = None


class NotePostRequest(BaseModel):
    account: str
    text: str
    media: Optional[List[str]] = None
    thumbnail: Optional[str] = None
    paid: bool
    tags: Optional[List[str]] = None


def post_to_mastodon(account: str, text: str, media: Optional[List[str]] = None):
    if account in MASTODON_ACCOUNT_ERRORS:
        return {"error": "Account misconfigured"}
    client = MASTODON_CLIENTS.get(account)
    if not client:
        return {"error": "Account not configured"}

    media_ids = None
    if media:
        media_ids = []
        for item in media:
            try:
                data = base64.b64decode(item)
                uploaded = client.media_post(BytesIO(data), mime_type="application/octet-stream")
                media_ids.append(uploaded.get("id"))
            except Exception as exc:
                return {"error": f"Media upload failed: {exc}"}

    try:
        client.status_post(text, media_ids=media_ids)
    except Exception as exc:
        return {"error": str(exc)}

    return {"posted": True}


def post_to_twitter(account: str, text: str, media: Optional[List[str]] = None):
    if account in TWITTER_ACCOUNT_ERRORS:
        return {"error": "Account misconfigured"}
    info = TWITTER_CLIENTS.get(account)
    if not info:
        return {"error": "Account not configured"}

    client = info["client"]
    api = info["api"]

    media_ids = None
    if media:
        media_ids = []
        for item in media:
            try:
                data = base64.b64decode(item)
                uploaded = api.media_upload(filename="media", file=BytesIO(data))
                media_ids.append(uploaded.media_id)
            except Exception as exc:
                return {"error": f"Media upload failed: {exc}"}

    try:
        client.create_tweet(text=text, media_ids=media_ids)
    except Exception as exc:
        return {"error": str(exc)}

    return {"posted": True}


def _temp_file_from_b64(data: str, suffix: str = "") -> str:
    """Write base64 data to a temporary file and return its path."""
    raw = base64.b64decode(data)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(raw)
    tmp.close()
    return tmp.name


def post_to_note(
    account: str,
    text: str,
    media: List[str],
    thumbnail: str,
    paid: bool,
    tags: List[str],
):
    """Automate posting to note.com using Selenium."""

    # Debug: announce which account we're using
    print(f"[NOTE] Starting post for account: {account}")

    if account in NOTE_ACCOUNT_ERRORS:
        return {"error": "Account misconfigured"}

    creds = NOTE_ACCOUNTS.get(account)
    if not creds:
        return {"error": "Account not configured"}

    options = ChromeOptions()
    if HEADLESS:
        options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    print("[NOTE] Launching Chrome")
    driver = webdriver.Chrome(options=options)

    def _capture_screenshot():
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        tmp.close()
        try:
            driver.save_screenshot(tmp.name)
        except Exception as exc:
            print(f"[NOTE] Failed to save screenshot: {exc}")
        return tmp.name

    try:
        wait = WebDriverWait(driver, 20)

        # --- Login step ---
        try:
            # Load the login page directly with a redirectPath parameter so the form shows
            login_url = NOTE_SELECTORS["login_url"] + urllib.parse.quote(
                NOTE_SELECTORS["home_url"]
            )
            login_base = NOTE_SELECTORS["login_url"].split("?")[0]
            driver.get(login_url)
            # Wait for the login form fields to appear
            wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, NOTE_SELECTORS["login_username"])
                )
            )
            username_field = driver.find_element(
                By.CSS_SELECTOR, NOTE_SELECTORS["login_username"]
            )
            username_field.clear()
            username_field.send_keys(creds["username"])
            password_field = driver.find_element(
                By.CSS_SELECTOR, NOTE_SELECTORS["login_password"]
            )
            password_field.clear()
            password_field.send_keys(creds["password"])

            # Wait until the login button becomes enabled before clicking
            wait.until(
                lambda d: d.find_element(
                    By.CSS_SELECTOR, NOTE_SELECTORS["login_submit"]
                ).is_enabled()
            )
            login_button = driver.find_element(
                By.CSS_SELECTOR, NOTE_SELECTORS["login_submit"]
            )
            login_button.click()
            # Sometimes the first click is missed; send a second one
            login_button.click()
            wait.until(lambda d: not d.current_url.startswith(login_base))
        except Exception as exc:
            path = _capture_screenshot()
            msg = f"login failed: {exc}"
            print(f"[NOTE] {msg}; screenshot {path}")
            return {"error": msg, "screenshot": path}

        # --- Open new post page ---
        try:
            driver.get(NOTE_SELECTORS["home_url"])
            wait.until(
                EC.element_to_be_clickable((By.XPATH, NOTE_SELECTORS["post_menu"]))
            )
            driver.find_element(By.XPATH, NOTE_SELECTORS["post_menu"]).click()
            wait.until(
                EC.element_to_be_clickable((By.XPATH, NOTE_SELECTORS["new_post_menu"]))
            )
            driver.find_element(By.XPATH, NOTE_SELECTORS["new_post_menu"]).click()
            wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, NOTE_SELECTORS["text_area"]))
            )
        except Exception as exc:
            path = _capture_screenshot()
            msg = f"open new post failed: {exc}"
            print(f"[NOTE] {msg}; screenshot {path}")
            return {"error": msg, "screenshot": path}

        # --- Compose content / upload media ---
        try:
            title_text = text.splitlines()[0][:20] if text else ""
            driver.find_element(By.CSS_SELECTOR, NOTE_SELECTORS["title_area"]).send_keys(title_text)

            body = driver.find_element(By.CSS_SELECTOR, NOTE_SELECTORS["text_area"])
            body.send_keys(text)

            for item in media:
                path_f = _temp_file_from_b64(item)
                driver.find_element(By.CSS_SELECTOR, NOTE_SELECTORS["media_input"]).send_keys(path_f)
                os.unlink(path_f)

            if thumbnail:
                path_f = _temp_file_from_b64(thumbnail)
                driver.find_element(By.XPATH, NOTE_SELECTORS["thumbnail_button"]).click()
                wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, NOTE_SELECTORS["thumbnail_input"]))
                )
                driver.find_element(By.CSS_SELECTOR, NOTE_SELECTORS["thumbnail_input"]).send_keys(path_f)
                os.unlink(path_f)

            if paid:
                driver.find_element(By.XPATH, NOTE_SELECTORS["paid_tab"]).click()
            else:
                driver.find_element(By.XPATH, NOTE_SELECTORS["free_tab"]).click()

            for tag in tags:
                tag_field = driver.find_element(By.CSS_SELECTOR, NOTE_SELECTORS["tag_input"])
                tag_field.send_keys(tag)
                tag_field.send_keys(Keys.ENTER)
        except Exception as exc:
            path = _capture_screenshot()
            msg = f"compose failed: {exc}"
            print(f"[NOTE] {msg}; screenshot {path}")
            return {"error": msg, "screenshot": path}

        # --- Publish step ---
        try:
            driver.find_element(By.XPATH, NOTE_SELECTORS["publish_next"]).click()
            wait.until(
                EC.element_to_be_clickable((By.XPATH, NOTE_SELECTORS["publish"]))
            )
            driver.find_element(By.XPATH, NOTE_SELECTORS["publish"]).click()
            wait.until(EC.url_contains("/notes/"))
            print("[NOTE] Post published")
            return {"posted": True}
        except Exception as exc:
            path = _capture_screenshot()
            msg = f"publish failed: {exc}"
            print(f"[NOTE] {msg}; screenshot {path}")
            return {"error": msg, "screenshot": path}
    finally:
        print("[NOTE] Closing browser")
        driver.quit()

@app.get("/")
async def root():
    return {"status": "ok"}

@app.post("/post")
async def receive_post(data: PostRequest):
    # For now just log that data was received
    media_count = len(data.media or [])
    return {"received": True, "media_items": media_count}


@app.post("/mastodon/post")
async def mastodon_post(data: MastodonPostRequest):
    return post_to_mastodon(data.account, data.text, data.media)


@app.post("/twitter/post")
async def twitter_post(data: TwitterPostRequest):
    return post_to_twitter(data.account, data.text, data.media)


@app.post("/note/post")
async def note_post(data: NotePostRequest):
    return post_to_note(
        data.account,
        data.text,
        data.media or [],
        data.thumbnail or "",
        data.paid,
        data.tags or [],
    )

if __name__ == "__main__":
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser(description="autoPoster server")
    parser.add_argument(
        "--show-browser",
        action="store_true",
        help="Launch Selenium with a visible browser window",
    )
    args = parser.parse_args()

    if args.show_browser:
        HEADLESS = False

    uvicorn.run(app, host="127.0.0.1", port=8765)
