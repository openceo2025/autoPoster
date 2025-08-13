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
