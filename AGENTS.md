# AGENTS

## Status
- WordPress 投稿はカテゴリとタグの指定に対応しています。
- `paid_content` フィールドでプレミアムコンテンツブロックを挿入できますが、WordPress.com 側の制約により現在は検証を停止しています。
- 画像アップロード後のレスポンス処理が不完全なため、記事内画像が壊れる既知の問題があります。

## Next steps
- `wordpress_client.WordpressClient.upload_media` を修正し、`media` 配列レスポンスから `source_url` を取得して正しい画像 URL を挿入する。
- `services.post_to_wordpress.post_to_wordpress` で画像 URL が得られなかった場合に `<img>` タグを生成しないようガードを追加する。
- 上記の振る舞いを検証するテストを追加・更新し、`pytest` を実行して確認する。
- 有料コンテンツ機能の仕上げ（未指定時の挙動確認、ボタン生成の条件分岐など）に着手する。

このプロジェクトは現在一時停止中です。再開時は上記タスクを進めてください。
