# Cloudflare Pages — LOCAL GUIDEセットアップ（公開前の手順書）

作成日: 2026-10-15。現在は**公開先の選定とオフライン準備のみ**。Cloudflare Pages上でのプロジェクト作成、GitHub接続、初回デプロイ、DNS変更、課金登録はまだ行っていません。

## なぜCloudflare Pagesか

- GitHubのPR/CIから独立して静的コンテンツを無料で配信する。楽天トラベルのアフィリエイトをサブコンテンツとして検討する際も、GitHub Pagesの「商取引を主目的とした公開先には使えない」という制限への依存を避けられる。
- Cloudflare Pages無料枠は月500ビルド、同時1ビルド、1サイト20,000ファイル、単一ファイル最大25MiB。静的配信は無料。Cloudflare無料プランにも利用規約・禁止事項が適用される。
  https://developers.cloudflare.com/pages/platform/limits/
- `pages.dev` のサブドメインは追加の独自ドメイン購入なしで利用可能。
- Cloudflare上の初回GitHub連携は**一般公開サイトを作る**ので、ユーザーの公開承認前は操作しない。

## 正式公開を承認した後のCloudflareダッシュボードでの設定

1. https://dash.cloudflare.com/ にログイン（未登録ならCloudflareの無料アカウントを作成し、Freeプランを選択）。
2. Workers & Pages → Create application → Pages → Connect to Git（画面表示は変更される場合があります）。
3. GitHubとの連携を許可。リポジトリ選択が可能なら**Only select repositories**を選び、**`noranamani/noranamani-local-guide`だけ**に権限を与える。既存ガジェットサイトには許可しない。
4. Framework preset: `None` / Project name: `noranamani-local-guide`（利用可能なら） / Production branch: `main` / Root directory: リポジトリ直下 `/`。
5. Build command: `python3 -m pip install -r requirements.txt && python3 -m scripts.cloudflare_build`
6. Build output directory: `docs`（`/docs`ではなくルートからの相対パス）。
7. Python version: `.python-version`に`3.12`固定。必要に応じて環境変数`PYTHON_VERSION=3.12`を指定。
8. **プレビュー展開の制御**: Settings → Builds & deployments → Branch deployment controls で Preview deployments を `None` に変更。プレビュー展開はデフォルトで公開URLを持ちます。
9. この状態で**初回Deployを押すと公開が始まります**。公開後は自動的に`https://<project>.pages.dev/`を受け取れる。公開承認までは実施しない。

## ビルドの挙動・安全対策

- CloudflareはコードをGitHubからチェックアウトし、Python3.12で`requirements.txt`を導入。専用ビルドコマンドがリポジトリの`data/`を読んで最新の`docs/`を生成・検証する。
- コードの`collect`と`run`は呼ばない。**民間RSS/APIの定期取得を勝手に行わない**。Cloudflare側には秘密のキー・メールアドレスを渡さない。
- 現在`config/page_rules.json`は`site_url: null`のため、全HTMLは`noindex`。生成された`docs/_headers`はHTTPレスポンスにも`X-Robots-Tag: noindex`を追加する。画像・情報の再利用権は別途審査。
- 検索可能なページの基準を満たすまで、Cloudflare Pagesに接続していてもサイトが無断でインデックス登録されるのを防ぐ。**noindexはアクセス制限やパスワード保護ではない**。
- Pages PreviewはCloudflareが自動で`X-Robots-Tag: noindex`を付与するが、デフォルトで一般公開。閲覧を制限する必要がある場合はCloudflare Accessを構成するか、GitHub Actionsの非公開アーティファクトを使う。
- Cloudflareの`_headers`は通常の静的アセットに適用され、Functionsには自動適用されない。本プロジェクトは静的HTMLだけでFunctionsを使わない。
- 将来独自ドメインを導入する場合は、`site_url`、canonical、sitemap、robots.txtを公開URLへ合わせる。予約/広告リンクは楽天の個別掲載条件に従い公開後に別途有効化。

## 無料枠の予算
- GitHub Actionsで1日1回のコンテンツ更新をビルドする場合、30日で約30ビルド。PRのプレビュー展開をCloudflareでも自動実行すると、その分ビルド枠を消費するため、当面はNoneを推奨。
- Cloudflareの無料枠は月500ビルドで同時1件。大量PRや無限再実行には注意。
- パブリックな`pages.dev`サブドメインはCloudflare Pages側で用意される。別のドメイン購入・DNS移管・有料APIは必要なし。
- Cloudflare PagesのGit連携は既存のGitHub Actions `unittest` の成功を自動で待つとは限らない。Cloudflareのビルドコマンドでサイト検証を再実行し、サイト品質が揃ってから接続する。

## 参考（Cloudflare公式）
- https://developers.cloudflare.com/pages/get-started/git-integration/
- https://developers.cloudflare.com/pages/configuration/build-image/
- https://developers.cloudflare.com/pages/configuration/build-configuration/
- https://developers.cloudflare.com/pages/configuration/branch-build-controls/
- https://developers.cloudflare.com/pages/configuration/preview-deployments/
- https://developers.cloudflare.com/pages/configuration/headers/
