from services.post_to_wordpress import create_wp_client, WP_CLIENT


def get_post_views(account: str | None, post_id: int, days: int) -> dict:
    """Fetch view statistics for a WordPress post."""
    client = WP_CLIENT if account is None else create_wp_client(account)
    if client is None:
        return {"error": "WordPress client unavailable"}
    try:
        data = client.get_post_views(post_id, days)
    except Exception as exc:
        return {"error": str(exc)}
    return {"views": data.get("views")}

