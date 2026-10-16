# はりまよりみち｜写真ヒーロー＋文字重ね・本番反映 引き継ぎ（2026-10-16）

## ユーザーの現在の依頼
- 「画像はとてもいい感じなので、タイトルは画像の上に文字を乗せた感じで本番に適用お願いします。」
- その後、ChatGPTの表示ストリームが途切れ、画像だけ出る問題が発生。**新しいチャットで続行できるようにする**ことを依頼された。
- 画像生成で日本語タイトルが画像自体に焼き込まれた版は文字がおかしいため、**利用しない**。
- 必ず**文字なしの風景写真 + ブラウザで描くHTMLテキスト + CSSオーバーレイ**として実装。スクリーンショット画像にタイトルを入れない。

## GitHubの確認済み状態（2026-10-16）
- リポジトリ: https://github.com/noranamani/noranamani-local-guide
- 本番用ブランチ: `main`（確認時 HEAD `808ee6b8f11923fd08f55e1753342951dd8d5ea4`）
- **Draft PR #22**: https://github.com/noranamani/noranamani-local-guide/pull/22
- PR #22 の変更元ブランチ: `homepage-refresh-20261016`（引き継ぎ文書追加前 HEAD `412133ddb256a6fbd9e0f2d0a1a9851b7f5a6bff`）
- PR #22 は open / draft / 未マージ。最後に確認した同PRのGitHub Actions（Offline Python tests and unpublished preview）は成功: https://github.com/noranamani/noranamani-local-guide/actions/runs/38848102741
- `main` にはPR #19〜#21までマージ済み。家族旅行ページと楽天トラベルの手動広告リンクも含まれる。**既存アフィリエイトHTMLを変更しない**。
- 過去の実験ブランチ `improve-prelaunch-mobile-ui-20261016` もあるが、PR #22と変更内容が重なるため、安易に混合・マージしない。

## 画像とローカルプレビュー（このチャットで生成）
ユーザーが気に入った、文字なしの風景画像:
1. `海沿いの道と島々の絶景.png`（サイトTOP向け）
2. `淡路の海と大橋を望む花景色.png`（淡路島旅行記事向け）

使用**禁止**: `はりま海景よりみち旅.png`（画像内に日本語タイトルを生成してしまい、文字表現が不自然）。

この会話の作業コンテナには写真をWebPに変換してHTML/CSS文字重ねした**独立したローカルプレビュー**が存在する:
- `/mnt/data/harima-yorimichi-photo-preview.zip`（約382KB、HTML/CSS/WebP同梱）
- `/mnt/data/harima-photo-preview/docs/harima-hero-photo.webp`（トップ、約160KB）
- `/mnt/data/harima-photo-preview/docs/awaji-photo.webp`（淡路旅行、約200KB）
- `/mnt/data/harima-photo-preview/docs/styles.css`
- `/mnt/data/harima-photo-preview/docs/index.html`
- `/mnt/data/harima-photo-preview/docs/trip-awaji-family-one-night.html`
- 確認スクリーンショット: `/mnt/data/harima-photo-desktop-home.png`, `/mnt/data/harima-photo-mobile-home.png`, `/mnt/data/harima-photo-desktop-awaji.png`, `/mnt/data/harima-photo-mobile-awaji.png`
- 作成用ローカルスクリプト: `/mnt/data/build_harima_photo_preview.py`

**重要**: `/mnt/data/...` は別チャットで引き継がれる保証がない。ユーザーに上記ZIPをダウンロードしてもらい、必要なら新チャットにアップロードしてもらう。このMarkdownだけでは画像バイナリは復元できない。現時点では写真の画像ファイル・文字重ね実装は**GitHubのPR #22にもmainにも未反映**。

## ローカルプレビューのUI案（HTMLテキスト、画像埋め込み文字ではない）
- トップの写真に重ねる主タイトル: `はりまよりみち`（実際の `<h1>` ）
- サブコピー: `週末、ちょっとよりみちしよう。`
- ブランド上の短文: `播磨のおでかけを、確かな情報から。`
- 写真に暗めのCSSグラデーションを重ね、白い日本語テキストを読みやすくする。
- スマホ時は写真部分にタイトルとボタンが重なるレスポンシブ構成。テキストは文字選択可能。
- 淡路旅行の表紙も写真背景の上に**記事タイトルのHTML `<h1>`** を重ねる。
- 両写真に `※画像はイメージです` と表示。写真風のAI生成画像を実地で撮影したように紹介しない。
- ローカルではPC/スマホのスクリーンショットを作成済み。ただしGitHub Actionsによる**写真版ソースの統合テストは未実施**。

## GitHubに統合する際の注意
- PR #22は現在 `localguide/site.py` の `STYLE`、`HERO_SCENE`、`AWAJI_SCENE`、`create_files` でSVG静的素材とHTMLを生成。
- 写真素材を配布する場合はローカルZIPのWebPを取り込み、`create_files`/ビルド/検証/マニフェストへの登録方法を整合させる。**生成後の `docs/index.html` や `styles.css` だけを手作業で書き換える実装にしない**（次回ビルドで消える）。
- Pythonの静的ジェネレーターが文字重ねHTMLとCSSを生成し、WebPバイナリを含むサイト出力の生成と検証を行えるようにする。
- トップと淡路記事は実テキストの `<h1>` をそれぞれ1つ維持。モバイル幅390px前後/PC幅1440px前後で横スクロール、文字可読性、画像配置を確認。
- `data/travel_guides.json` 内の旅行計画や楽天アフィリエイトHTML、PR表示、リンク先を勝手に変更しない。
- 既存の掲載出典、記事の正確性、`site_url: null` による `noindex`、未確認イベント非表示などの安全制約を保持。
- 改修後は `python -m unittest discover -s tests -q`、`python -m scripts.cloudflare_build`、`python -m localguide validate --site`、GitHub Actionsを確認。必要ならPR内で改修してレビュー後マージ。
- **本番への反映は未完了**。Cloudflare Pagesの実際のプロジェクト接続/配信状態はこの時点で直接検証できていない。GitHub PRのマージは本番更新を引き起こす可能性があるため、現在のCloudflare接続とユーザーの公開意思を確認してから行う。

## 新しいチャットに貼る依頼文（テンプレート）
> 「はりまよりみち」のサイト写真＋文字重ねの実装を再開してください。GitHub連携で、まず以下の引き継ぎ資料を読んでください。
> https://github.com/noranamani/noranamani-local-guide/blob/homepage-refresh-20261016/planning/HANDOFF_HARIMA_HERO_OVERLAY_2026-10-16.md
> Draft PR #22 をベースに、写真自体に文字を描かず、トップと淡路旅行記事で写真の上に正しい日本語タイトルをHTML/CSSで重ねてください。既存の楽天広告・掲載根拠とnoindex安全制約を維持し、テスト・PC/スマホでのプレビュー確認後、本番反映までお願いします。写真素材が取得できなければ、前チャットのZIPを私にアップロードするよう依頼してください。既存の作業を消したり、PRを確認なしに無理にマージしたりしないでください。

## 作業を止めた理由
ユーザー側でassistantの応答ストリームが途中で途切れたため。GitHub側の安全なDraft PRを残したまま、引き継ぎ文書のみ保存して作業を中断する方針。
