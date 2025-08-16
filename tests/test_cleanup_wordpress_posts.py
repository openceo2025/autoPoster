import sys
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.append(str(Path(__file__).resolve().parents[1]))

import cleanup_wordpress_posts as cwp


def test_cleanup_wordpress_posts(tmp_path):
    cfg = {
        "wordpress": {
            "accounts": {
                "acc1": {"site": "site1"},
                "acc2": {"site": "site2"},
            }
        }
    }
    cfg_path = tmp_path / "config.json"
    cfg_path.write_text(json.dumps(cfg))

    icon1 = "https://example.com/icon1.png"
    logo1 = "https://example.com/logo1.png"
    icon2 = "https://example.com/icon2.png"
    logo2 = "https://example.com/logo2.png"

    clients: dict[str, MagicMock] = {}

    def factory(config):
        site = config["wordpress"]["accounts"]["default"]["site"]
        m = MagicMock(name=site)
        clients[site] = m
        if site == "site1":
            m.list_posts.return_value = [
                {"id": 1, "date": "2020-01-01"},
                {"id": 2, "date": "2020-02-01"},
                {"id": 3, "date": "2020-03-01"},
            ]
            m.get_site_info.return_value = {
                "icon": {"img": icon1},
                "logo": {"img": logo1},
            }
            m.list_media.side_effect = [
                [
                    {"ID": 11, "URL": icon1},
                    {"ID": 13, "URL": logo1},
                    {"ID": 12, "URL": "https://example.com/delete1.png"},
                ],
                [],
            ]
        else:
            m.list_posts.return_value = [
                {"id": 4, "date": "2021-01-01"},
                {"id": 5, "date": "2021-02-01"},
            ]
            m.get_site_info.return_value = {
                "icon": {"img": icon2},
                "logo": {"img": logo2},
            }
            m.list_media.side_effect = [
                [
                    {"ID": 21, "URL": icon2},
                    {"ID": 23, "URL": logo2},
                    {"ID": 22, "URL": "https://example.com/delete2.png"},
                ],
                [],
            ]
        return m

    with patch("cleanup_wordpress_posts.WordpressClient", side_effect=factory), \
        patch("cleanup_wordpress_posts.CONFIG_PATH", cfg_path), \
        patch("builtins.input", side_effect=["2", "2"]):
        cwp.main()

    c1 = clients["site1"]
    c2 = clients["site2"]

    c1.list_posts.assert_called_once_with(page=1, number=100)
    c1.delete_post.assert_called_once_with(1)
    c1.empty_trash.assert_called_once()
    assert c1.list_media.call_count == 2
    c1.list_media.assert_called_with(
        post_id=0, page=1, number=2, fields="ID,URL"
    )
    c1.delete_media.assert_called_once_with(12)

    c2.list_posts.assert_called_once_with(page=1, number=100)
    c2.delete_post.assert_not_called()
    c2.empty_trash.assert_not_called()
    assert c2.list_media.call_count == 2
    c2.list_media.assert_called_with(
        post_id=0, page=1, number=2, fields="ID,URL"
    )
    c2.delete_media.assert_called_once_with(22)
