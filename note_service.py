import base64
import os
import tempfile
import urllib.parse
from io import BytesIO
from typing import Any, Dict, List, Optional

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# By default Selenium runs in headless mode. It can be toggled via the
# HEADLESS variable which the server updates when started with --show-browser.
HEADLESS = True

# CSS selectors and URLs used to automate posting to Note
NOTE_SELECTORS = {
    "login_url": "https://note.com/login?redirectPath=",
    "login_username": "#email",
    "login_password": "#password",
    "login_submit": ".o-login__button button",
    "home_url": "https://note.com/",
    "post_menu": "//*[self::button or self::a][contains(., '投稿')]",
    "new_post_menu": (
        "//*[self::button or self::a][contains(., '新しく記事を書く')"
        " or contains(@href, '/notes/new')]"
    ),
    "editor_title": "textarea[placeholder='記事タイトル'], div[data-placeholder='記事タイトル']",
    "title_area": "textarea[placeholder='記事タイトル'], div[data-placeholder='記事タイトル']",
    "text_area": "div[contenteditable='true'][role='textbox']",
    "open_menu": "//button[contains(@aria-label,'メニューを開く')]",
    "media_input": "input[type='file']",
    "media_button": "//button[contains(@aria-label, '画像') or contains(., '画像')]",
    "thumbnail_button": (
        "//button[contains(@aria-label, '画像をアップロード') or "
        "contains(., '画像をアップロード')]"
    ),
    "thumbnail_input": "input[type='file']",
    "paid_tab": "//label[contains(., '有料')]/input",
    "free_tab": "//label[contains(., '無料')]/input",
    "tag_input": "input[placeholder='ハッシュタグを追加する']",
    "publish_next": "//button[contains(., '公開に進む')]",
    "publish": "//button[contains(., '投稿する') or contains(., '更新する')]",
}


def validate_accounts(config: Dict) -> Dict[str, str]:
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


def load_accounts(config: Dict, account_errors: Dict[str, str]):
    """Return credentials for configured Note accounts."""
    accounts = {}
    cfg_accounts = config.get("note", {}).get("accounts", {})
    for name, info in cfg_accounts.items():
        if name in account_errors:
            continue
        accounts[name] = info
    return accounts


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
    *,
    accounts: Dict[str, Dict[str, str]],
    account_errors: Dict[str, str],
) -> Dict[str, Any]:
    """Automate posting to note.com using Selenium."""

    print(f"[NOTE] Starting post for account: {account}")

    if account in account_errors:
        return {"error": "Account misconfigured"}

    creds = accounts.get(account)
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

    def _fail_step(step: str, exc: Exception):
        path = _capture_screenshot()
        msg = f"{step} failed: {exc}"
        print(f"[NOTE] {msg}; screenshot {path}")
        return {"error": msg, "screenshot": path}

    def _send_to_new_input(input_selector: str, path: str, trigger: Optional[Any] = None):
        # no clicking here
        print("[DEBUG] waiting for input element")
        try:
            WebDriverWait(driver, 20).until(
                lambda d: len(d.find_elements(By.CSS_SELECTOR, input_selector)) > 0
            )
            inputs = driver.find_elements(By.CSS_SELECTOR, input_selector)
            print(f"[DEBUG] input elements found: {len(inputs)}")
            for idx, inp in enumerate(inputs):
                try:
                    inp_id = inp.get_attribute("id")
                    inp_class = inp.get_attribute("class")
                    inp_name = inp.get_attribute("name")
                except Exception:
                    inp_id = inp_class = inp_name = None
                try:
                    in_iframe = driver.execute_script(
                        "return arguments[0].ownerDocument !== document",
                        inp,
                    )
                except Exception:
                    in_iframe = None
                try:
                    in_shadow = driver.execute_script(
                        "return arguments[0].getRootNode() instanceof ShadowRoot",
                        inp,
                    )
                except Exception:
                    in_shadow = None
                print(
                    f"[DEBUG] input {idx}: id={inp_id} class={inp_class} name={inp_name} "
                    f"iframe={in_iframe} shadow={in_shadow}"
                )
            inputs[-1].send_keys(path)
        except Exception as exc:
            raise Exception(f"{exc.__class__.__name__}: {exc}") from exc

    try:
        wait = WebDriverWait(driver, 20)

        # --- Login step ---
        try:
            login_url = NOTE_SELECTORS["login_url"] + urllib.parse.quote(
                NOTE_SELECTORS["home_url"]
            )
            login_base = NOTE_SELECTORS["login_url"].split("?")[0]
            driver.get(login_url)
            wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, NOTE_SELECTORS["login_username"])
                )
            )
            username_field = driver.find_element(By.CSS_SELECTOR, NOTE_SELECTORS["login_username"])
            username_field.clear()
            username_field.send_keys(creds["username"])
            password_field = driver.find_element(By.CSS_SELECTOR, NOTE_SELECTORS["login_password"])
            password_field.clear()
            password_field.send_keys(creds["password"])

            wait.until(
                lambda d: d.find_element(By.CSS_SELECTOR, NOTE_SELECTORS["login_submit"]).is_enabled()
            )
            login_button = driver.find_element(By.CSS_SELECTOR, NOTE_SELECTORS["login_submit"])
            login_button.click()
            WebDriverWait(driver, 40).until(
                lambda d: not d.current_url.startswith(login_base)
            )
            print("[NOTE] Logged in")
        except Exception as exc:
            msg = f"{exc} (URL: {driver.current_url})"
            return _fail_step("login", Exception(msg))

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
                EC.presence_of_element_located((By.CSS_SELECTOR, NOTE_SELECTORS["editor_title"]))
            )
            print("[NOTE] Editor opened")
        except Exception as exc:
            return _fail_step("open new post", exc)

        # --- Compose content / upload media ---
        try:
            title_text = text.splitlines()[0][:20] if text else ""
            driver.find_element(By.CSS_SELECTOR, NOTE_SELECTORS["title_area"]).send_keys(title_text)
            print("[NOTE] Title entered")
        except Exception as exc:
            return _fail_step("enter title", exc)

        try:
            body = driver.find_element(By.CSS_SELECTOR, NOTE_SELECTORS["text_area"])
            body.send_keys(text)
            print("[NOTE] Body entered")
        except Exception as exc:
            return _fail_step("enter body", exc)

        for item in media:
            try:
                print("[NOTE] Uploading media item")
                path_f = _temp_file_from_b64(item)
                menu_buttons = driver.find_elements(By.XPATH, NOTE_SELECTORS["open_menu"])
                if not menu_buttons:
                    raise Exception("menu button not found")
                menu_buttons[0].click()
                wait.until(
                    EC.presence_of_element_located((By.XPATH, NOTE_SELECTORS["media_button"]))
                )
                buttons = driver.find_elements(By.XPATH, NOTE_SELECTORS["media_button"])
                if not buttons:
                    raise Exception("media button not found")
                button = buttons[0]
                button.click()
                _send_to_new_input(NOTE_SELECTORS["media_input"], path_f)
                print("[NOTE] Media item uploaded")
            except Exception as exc:
                return _fail_step("upload media", exc)
            finally:
                os.unlink(path_f)

        if thumbnail:
            try:
                print("[NOTE] Uploading thumbnail")
                path_f = _temp_file_from_b64(thumbnail)
                buttons = driver.find_elements(By.XPATH, NOTE_SELECTORS["thumbnail_button"])
                if not buttons:
                    raise Exception("thumbnail button not found")
                button = buttons[0]
                button.click()
                _send_to_new_input(NOTE_SELECTORS["thumbnail_input"], path_f)
                print("[NOTE] Thumbnail uploaded")
            except Exception as exc:
                return _fail_step("upload thumbnail", exc)
            finally:
                os.unlink(path_f)

        try:
            if paid:
                driver.find_element(By.XPATH, NOTE_SELECTORS["paid_tab"]).click()
            else:
                driver.find_element(By.XPATH, NOTE_SELECTORS["free_tab"]).click()
            print("[NOTE] Paid/free option set")
        except Exception as exc:
            return _fail_step("set paid/free", exc)

        for tag in tags:
            try:
                tag_field = driver.find_element(By.CSS_SELECTOR, NOTE_SELECTORS["tag_input"])
                tag_field.send_keys(tag)
                tag_field.send_keys(Keys.ENTER)
                print(f"[NOTE] Tag added: {tag}")
            except Exception as exc:
                return _fail_step("add tag", exc)

        # --- Publish step ---
        try:
            wait.until(
                EC.element_to_be_clickable((By.XPATH, NOTE_SELECTORS["publish_next"]))
            )
            driver.find_element(By.XPATH, NOTE_SELECTORS["publish_next"]).click()
            print("[NOTE] Proceeding to publish")
            wait.until(
                EC.element_to_be_clickable((By.XPATH, NOTE_SELECTORS["publish"]))
            )
            driver.find_element(By.XPATH, NOTE_SELECTORS["publish"]).click()
            print("[NOTE] Publish button clicked")
            wait.until(EC.url_contains("/notes/"))
            print("[NOTE] Post published")
            return {"posted": True}
        except Exception as exc:
            return _fail_step("publish", exc)
    finally:
        print("[NOTE] Closing browser")
        driver.quit()
