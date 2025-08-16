import json
from pathlib import Path
from typing import Any

import concurrent.futures

from wordpress_client import WordpressClient

CONFIG_PATH = Path("config.json")
MAX_WORKERS = 5


def main() -> None:
    try:
        batch_size = int(input("削除バッチサイズ: ").strip())
        max_count = int(input("最大投稿数: ").strip())
        if batch_size <= 0:
            raise ValueError
    except ValueError:  # pragma: no cover - simple CLI error handling
        print("Invalid number")
        return

    try:
        with CONFIG_PATH.open() as f:
            cfg = json.load(f)
    except Exception as exc:  # pragma: no cover - simple CLI error handling
        print(f"Failed to load config: {exc}")
        return

    accounts: dict[str, Any] = cfg.get("wordpress", {}).get("accounts", {})
    if not accounts:
        print("No WordPress accounts configured.")
        return

    for name, acct_cfg in accounts.items():
        print(f"Processing account: {name}")
        config = {"wordpress": {"accounts": {"default": acct_cfg}}}
        client = WordpressClient(config)
        try:
            print("Authenticating...")
            client.authenticate()
            print("Authenticated")
        except Exception as exc:  # pragma: no cover
            print(f"Authentication failed for {name}: {exc}")
            continue

        posts: list[dict[str, Any]] = []
        page = 1
        while True:
            print(f"Fetching posts page {page}")
            items = client.list_posts(page=page, number=100)
            print(f"Got {len(items)} posts")
            if not items:
                break
            posts.extend(items)
            if len(items) < 100:
                break
            page += 1

        posts.sort(key=lambda p: p["date"])  # oldest first
        delete_count = max(0, len(posts) - max_count)
        deleted_posts = 0
        for p in posts[:delete_count]:
            try:
                client.delete_post(p["id"])
                deleted_posts += 1
            except Exception as exc:  # pragma: no cover
                print(f"Failed to delete post {p['id']}: {exc}")
        if deleted_posts:
            client.empty_trash()

        info = client.get_site_info(fields="icon,logo")
        protected: set[str] = set()
        for key in ("icon", "logo"):
            obj = info.get(key) or {}
            for val in obj.values():
                if isinstance(val, str):
                    protected.add(val)

        removed_media = 0
        while True:
            print("Fetching media batch")
            media = client.list_media(
                post_id=0, page=1, number=batch_size, fields="ID,URL"
            )
            if not media:
                print("Processed 0 items")
                break
            IDs = [m["ID"] for m in media if m.get("URL") not in protected]
            print(f"Deleting {len(IDs)} media items")
            deleted_batch = 0
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=MAX_WORKERS
            ) as executor:
                future_to_id = {
                    executor.submit(client.delete_media, mid): mid for mid in IDs
                }
                for future in concurrent.futures.as_completed(future_to_id):
                    mid = future_to_id[future]
                    try:
                        future.result()
                        deleted_batch += 1
                    except Exception as exc:  # pragma: no cover - simple CLI error handling
                        print(f"Failed to delete media {mid}: {exc}")
            removed_media += deleted_batch
            print(f"Deleted {deleted_batch} media items")
            print(f"Processed {len(media)} items")
            if len(media) < batch_size:
                break

        print(
            f"{name}: removed {deleted_posts} posts and {removed_media} unattached media items"
        )

    print("Cleanup complete")


if __name__ == "__main__":  # pragma: no cover
    main()
