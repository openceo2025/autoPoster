from services.post_to_wordpress import create_wp_client, WP_CLIENT


def list_posts(account: str | None, page: int, number: int) -> dict:
    """Retrieve posts from WordPress."""
    client = WP_CLIENT if account is None else create_wp_client(account)
    if client is None:
        return {"error": "WordPress client unavailable"}
    try:
        posts = client.list_posts(page=page, number=number)
    except Exception as exc:
        return {"error": str(exc)}
    return {"posts": posts}


def delete_posts(account: str | None, ids: list[int]) -> dict:
    """Delete multiple WordPress posts and report successes and failures."""
    client = WP_CLIENT if account is None else create_wp_client(account)
    if client is None:
        return {"error": "WordPress client unavailable"}

    deleted: list[int] = []
    errors: dict[str, str] = {}
    for pid in ids:
        try:
            deleted_id = client.delete_post(pid)
            deleted.append(deleted_id)
        except Exception as exc:
            errors[str(pid)] = str(exc)

    return {"deleted": deleted, "errors": errors}
