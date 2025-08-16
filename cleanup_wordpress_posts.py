import json
from pathlib import Path
from typing import Any

from wordpress_client import WordpressClient

CONFIG_PATH = Path("config.json")


def main() -> None:
    try:
        max_count = int(input("最大投稿数: ").strip())
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

        page = 1
        removed_media = 0
        while True:
            print(f"Fetching media page {page}")
            media = client.list_media(post_id=0, page=page, number=100)
            if not media:
                print("Processed 0 items")
                break
            for idx, item in enumerate(media):
                url = item.get("URL")
                if url and url in protected:
                    continue
                try:
                    print(
                        f"Deleting media {idx + 1}/{len(media)}: {item['ID']}"
                    )
                    client.delete_media(item["ID"])
                    print("done", flush=True)
                    removed_media += 1
                except Exception as exc:  # pragma: no cover - simple CLI error handling
                    print(f"Failed to delete media {item['ID']}: {exc}")
            print(f"Processed {len(media)} items")
            if len(media) < 100:
                break
            page += 1

        print(
            f"{name}: removed {deleted_posts} posts and {removed_media} unattached media items"
        )

    print("Cleanup complete")


if __name__ == "__main__":  # pragma: no cover
    main()
