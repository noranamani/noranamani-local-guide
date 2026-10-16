# はりまよりみち｜先行公開の運用計画（2026-10-16）

## 方針

問い合わせ中の情報源（許諾・CSV等）は回答待ちのままにし、**許可されない自動取得は始めない**。
サイト自体は公式情報に基づく施設案内とオリジナルの旅行モデルコースを用意し、
イベント欄は「準備中」と明記して、Cloudflare Pages Freeで先行公開する。
公開対象が十分に揃う前は **SEOを全ページnoindex** とし、実際の公開URL確定後に段階的に見直す。
noindexは検索除外指示であり、閲覧パスワードではない。公開URLを知る人は閲覧できる。

## 公開できる内容

- トップ：サイト紹介、利用条件審査済みの施設、イベント0件のお知らせ、旅行ページへの導線
- 施設一覧：確認が72時間を超えた施設は自動的に非表示。再確認されるまで数が0になり得る
- 旅行一覧：人手で選び、公式サイトを確認したモデルコースを公開前試案として表示
- 淡路島1泊2日：あわじ花さじき、国営明石海峡公園、イングランドの丘に公式リンク。
  正確な訪問日・宿泊施設・宿泊定員・旅費を未確認なので価格は掲載しない
- 楽天トラベル：**未登録のURLにアフィリエイトリンクを出さない**。
  公式APIのキー・アフィリエイトID・写真/画像は静的サイトやGitHubへ保存しない
- Google広告：内容が「準備中」で少ない段階では実際のAdSense広告や申請を急がない
- 機密情報、転載画像・レビュー本文、架空のイベント、未確定の割引価格は公開しない

## 公開前の技術確認

1. Draft PRのCIが全件成功し、previewアーティファクトに index.html、travel.html、
   trip-awaji-family-one-night.html、_headers、styles.css が存在すること。
2. PC・スマホで見たときに公式リンクが開き、出典・確認状況の説明が読めること。
3. コンテンツ、機密情報、権利、リンク、広告なし状態を人手でも確認すること。
4. 上記の確認後、PRをmainにマージする。**マージ自体はCloudflare未接続ならサイト公開しない**。
5. Cloudflare側の初回GitHub連携・デプロイは外部公開なので、その操作を行う前に公開内容を確認する。

## Cloudflare Pages の初回設定（サイト所有者がログインして行う）

- https://dash.cloudflare.com/ → Workers & Pages → Create application → Pages → Connect to Git
- Freeプランのまま。GitHub許可は **noranamani/noranamani-local-guide の1リポジトリのみ**
- Project name: harima-yorimichi（空きがなければ別名を検討。事前にURLを確定扱いしない）
- Production branch: main
- Framework preset: None
- Root directory: /（リポジトリ直下）
- Build command: python3 -m pip install -r requirements.txt && python3 -m scripts.cloudflare_build
- Output directory: docs
- Python: 3.12（.python-version、必要なら環境変数 PYTHON_VERSION=3.12）
- Preview branches: None（初期設定のAllから変更。設定UIの文言は変更の可能性）
- 不要な環境変数、シークレット、課金情報、Worker/Functionsは追加しない
- Deployを押すと **pages.dev で一般公開** が開始する
- 初回URLが確定したら記録して、HTTPでnoindexがあることも検証する
- 公開開始時は config/page_rules.json の site_url は null のままなので、canonical/sitemapを作らず全HTML noindex

## 公開後の収益化手順

1. **Cloudflareで発行された実URL**を楽天アフィリエイトへサイト情報として登録する。
2. 楽天トラベルの公式機能でリンクを作るか、APIが発行した正規のアフィリエイトURLを使う。
   作成したHTMLソースを無断変更しない。API利用はApplication IDとAccess Key、
   利用規約・クレジット表示条件の追加確認が必要。
3. 対応する旅行記事に明瞭な「広告」「PR」表示を設け、広告リンクをその記事にだけ掲載する。
   アフィリエイト登録が完了していない期間に仮の広告URLを載せない。
4. 宿泊候補は定員・年齢・日程・部屋数・食事・宿泊総額を確認する。最安料金を家族総額と呼ばない。
5. 有料契約やAPI課金、個人の電話番号・住所・メール公開を勝手に行わない。
6. 内容が充実し、掲載条件と現実の運用を再審査できたら、個別ページのSEO公開を検討する。
   Google Search ConsoleとAdSenseの導入は別途条件を確認する。

## 継続更新・問い合わせ待ちの扱い

- 公式・二次利用許可が確認できたイベント情報源だけを収集対象に追加。
  回答前は新規の自動取得設定をしない。
- 既存ガジェット・ガチャのジョブ、token、cron、Secretsを使い回さない。
- 旅行モデルコースは月1〜2本を上限に、公式情報を人手で確認してから追加。
  ステータス `preview` のページは noindex のまま公開できるが、
  `approved` への切替は内容・URL・確認日時の再審査後。
- CloudflareのFree（月500ビルド）を超えないよう、追加運用コスト0円を維持する。

## 根拠リンク

- Cloudflare Git連携: https://developers.cloudflare.com/pages/get-started/git-integration/
- Cloudflare無料枠: https://developers.cloudflare.com/pages/platform/limits/
- Preview制御: https://developers.cloudflare.com/pages/configuration/branch-build-controls/
- 楽天アフィリエイト: https://affiliate.rakuten.co.jp/guideline/rule/
- 楽天トラベルアフィリエイト: https://travel.rakuten.co.jp/distributor/individual.html
- 楽天トラベルAPI: https://webservice.rakuten.co.jp/documentation/simple-hotel-search
- 施設の一次情報: https://awajihanasajiki.jp/
- 施設の一次情報: https://awaji-kaikyopark.kkr.mlit.go.jp/about
- 施設の一次情報: https://www.england-hill.com/
