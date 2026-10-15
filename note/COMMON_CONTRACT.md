# note共通受け渡し仕様（local）

共通仕様: https://github.com/noranamani/noranamani-gadget-deals/blob/main/note/COMMON_CONTRACT.md

## このサイトの要件
- `note/latest/article.md` と `note/latest/manifest.json` を週次生成する。
- `manifest.json` は `schema_version: 1`, `site_id: "local"`, `issue_key: "YYYY-Www"`, `status: "ready"|"skip"`, `title`, `article_path: "article.md"`, `cover_path: null` (任意画像), `source_url`, `generated_at` を持つ。
- 地域イベント・新店舗・施設変更の実データ差分だけを使う。未公開または情報0件ならskip。
- 記事には実際に確認した公式出典URLとサイトURLを記載する。取得時刻と発表日時を混同しない。
- 運用環境側で投稿履歴を保存し、同一週・同一内容の投稿を重複させない。
- GitHubへ認証情報、Cookie、noteセッションを保存しない。
- note自動公開は本件の範囲外。まず記事生成・検証・投稿dry-runで安全性を確認する。

## TODO
前回との差分抽出、出典チェック、ゼロ件skip、記事生成、manifest生成、単体テスト、note投稿バッチv0.3との疎通。
