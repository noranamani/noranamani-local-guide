# noranamani LOCAL GUIDE（仮称）

加古川・明石・姫路を中心とした家族向け地域情報自動メディア。

## 方針
- **メイン**: 地域イベント、無料・低価格のお出かけ、屋内遊び、商業施設、特売・セール、新店・閉店、直売所
- **サブ**: 加古川発・家族4〜6人向けの旅行モデルコースと宿泊施設比較
- **基盤**: Oracle Cloud Always Free / GitHub / Cloudflare Pages / Python / 既存ChatGPT契約内の編集タスク
- **追加費用目標**: 0円/月（既存契約料は除く）
- 既存の noranamani/noranamani-gadget-deals は変更しない。

## 現在の段階
Phase 1の取得基盤・正規化・検証・静的サイト生成とオフラインテストを実装済みです。
**明石市の観光施設オープンデータCSVを審査し、実施設4件の取得・生成を確認済みです。**
2026-10-14の初回調査は接続制限で拒否されましたが、設定変更後に再調査しました。利用規約は商用利用・加工・再配布を許可し、出典と加工表示が必要です。
28候補のうち、このCSV1件だけを有効化しています。残り27件は利用不可または未審査で無効です。イベントは0件、自動運用・サイト公開は未設定です。
実データ0件では掲載準備中のトップだけを生成し、架空イベント・空の地域/カテゴリページを生成しません。

## 主なファイル
- AGENTS.md: Codexおよび自動処理が守るルール
- config/: 対象地域、カテゴリ、候補情報源、ページ公開条件
- data/: 空のイベント・施設・特売・新店データ
- planning/: 情報源審査、データ設計、旅行モジュール、チェックリスト
- codex/phase1-prompt.md: Codex向け実装指示
- localguide/: Pythonの取得・正規化・検証・静的サイト生成
- schemas/: 設定・データのJSON Schema
- tests/: 外部接続しない単体・統合テスト（架空データは一時ディレクトリ内のみ）
- docs/: 検証済み静的生成物（将来Cloudflare Pagesから配信。まだ未公開）
- note/: 後日の週次note連携用

## 希望する日次時刻（未設定）
- 07:10 JST: Oracle VMが許可済みソースを取得・正規化
- 07:30 JST: ChatGPT Scheduled Taskで編集候補を更新（必須ではない）
- 07:50 JST: Oracle VMが静的サイト生成・検証・push
- 週次noteと旅行記事は、基盤が安定した後に段階的に追加

## 重要な制約
- 許諾未確認の機械取得をしない。第三者の文章・画像を無断で保存・再掲載しない。
- イベント日時・開催場所・参加費を推測しない。情報がなければ「不明」とする。
- 過去イベントの自動除外、重複判定、ソース表示、失敗時の安全停止を必須とする。
- 掲載件数が少ないカテゴリや検索用の薄いページを大量生成しない。
- Cloudflare PagesとSearch Consoleは、公開内容を検証してから設定する。

最初の作業は planning/phase1-checklist.md と codex/phase1-prompt.md を参照してください。

## ローカル開発（Linux / Python 3.12）

既存チェックアウトを使用します。クラウドタスクはすでに隔離されており、追加のworktreeは不要です。
新規導入時に実行します。既存の`.venv`は作り直さず使用してください。

```sh
cd /workspace/noranamani-local-guide
python3 -m venv .venv
.venv/bin/python -m pip install --cache-dir cache/pip -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m localguide run
.venv/bin/python -m localguide validate --site
```

`run`は取得→検証→生成を実行します。無効なソースには接続せず、取得失敗時は非ゼロで終了してサイト更新を中止します。
個別実行は`collect`、`validate`、`build`です。テストで時刻を固定する場合だけ、`--now 2026-10-14T16:00:00+09:00`を指定できます。
`--root`はテスト用の独立データセットを指定するためのオプションです。

ローカルのHTTP配信を確認するときは、生成後に次を実行します。公開設定は行いません。

```sh
.venv/bin/python -m http.server 8765 --bind 127.0.0.1 --directory docs
```

## 取得を有効にする前の審査

詳しい手順は[情報源審査台帳](planning/source-audit.md)を参照してください。
本実装は`event_csv`と`places_csv`のみ対応しています。HTMLやRSSは自動取得しません。
明石市の観光施設CSVは実URL・列・ライセンスを確認し、本番設定に登録済みです。他のソースのCSV実URL・列・値・ライセンスは未確認です。
公式CSVが確定したら、審査記録と明示的な列マッピングを設定します。未確認のフィードや記事本文で代用しません。

- `robots_review_status`、`terms_review_status`、`reuse_rights_status`、`privacy_review_status`がすべて`allowed`。
- `checked_at`は30日以内のタイムゾーン付き日時。`policy_url`、`permission_document`、`robots_url`は確認済みの公式URL。
- `robots_rules`に確認した実際のルールを記録。取得対象パスとUser-Agentが許可されること。robotsが実際に404の場合のみ、`robots_http_status=404`と空の`robots_rules`で不在を記録できます（RFC 9309 §2.3.1.3）。転載許諾は別途審査します。
- `content_scope=factual_metadata_only`、`attribution_required=true`、`adapter`と`field_map`を明示。
- `field_map`は正規化先の項目名→実CSV列名。`source_event_id`、`municipality`、`official_url`と、イベントなら`title`、施設なら`name`が必須。
- 日時はタイムゾーン付きISO8601または日付のみ。不明な開始・終了・年齢・料金は空欄からnull/unknownにします。日付だけの事実に時刻を付けません。
- イベントの`status`は明示値（scheduled/cancelled/postponed/ended/unconfirmed）。未指定ならunconfirmed。`price_type`はfree/paid/conditional/unknown。値を推測・自動翻訳しません。
- 無料区分には`free_value_reviewed=true`の根拠記録が必要。施設住所は`address_scope=public_facilities_only`の個別審査が必要。
- `maximum_requests_per_day`を遵守。標準は1日1回。ETag/Last-Modified対応、20秒タイムアウト、2 MiB上限。リダイレクトは移動先再審査まで停止。

401/403/429は`data/source_state.json`に停止状態を保持します。認証や制限を迂回しません。
手動再審査後にのみ該当ソースの`halted`を解除してください。失敗でも日次取得回数を消費します。
件数が前回の半分未満になった場合は異常としてデータを更新しません。
同一ソースIDの重複行は、開催回を勝手に統合せず停止します。

## 掲載・生成の安全動作

終了・中止・延期・日時不明・レビュー保留・古い確認（既定72時間超）のイベントは公開一覧から除外します。
複数開催は有効な開催回だけを表示します。取得失敗でも終了情報を復活させません。
別ソースの同一タイトルは日時・自治体・会場・属性が一致した場合だけ統合します。不一致や不足は双方を保留にし、`cache/review_queue.json`に記録します。
保留は次回取得で自動解除しません。審査した結果をdataに反映し、必要な場合だけ`review_hold`を解除します。
原文・画像は保存せず、短い事実項目と固定の独自案内を生成します。編集用JSONの文章を無審査で公開しません。

JSON Schema、参照整合性、秘密値の既知パターン、日時、HTML、ローカルリンク、canonical/sitemapを検証してからdocsを置き換えます。
検証・生成に失敗した場合は直前の正常なdocsを保持します。管理外ファイルの上書きや同時ジョブは停止します。
秘密値検知は既知形式の検査であり、未知形式の秘密や個人情報の人手審査も必要です。
明石市の配布ページ・利用規約PDF・CSVは到達性と適用条件を確認済みです。その他の未審査ソース、施設公式サイト個別の内容は未確認で、自動巡回しません。

`site_url=null`の間は全ページnoindex、canonical・sitemap・robots.txtは未生成です。
site_urlを確定した場合でも空ページはnoindexでsitemap対象外です。
地域・カテゴリ一覧は5件以上、公式3件以上、確認済みの異なる主催者2者以上、7日間の継続確認を満たした場合だけ生成します。
`organizer_label`不明は主催者数に算入しません。継続確認は`cache/page_state.json`に保持し、2日を超えて確認が途切れれば再計測します。
内部の期限切れデータは保持し、公開アーカイブは生成しません。旅行記事・note自動投稿も未実装です。

実ソースの詳細は[情報源審査台帳](planning/source-audit.md)を参照してください。CSVの出典URLと施設の公式URLを分け、加工表示を付けています。発表日は配布ページの2026-08-25を日付のまま保持し、取得日時とは区別します。304は前回検証済みCSVに変更がない確認として、発表日時・初回取得日時を保持して確認日時だけを更新します。

## Phase 1C — 施設データ更新の安全性と次候補

施設CSVから行が削除された場合、審査済みの当該情報源の施設のみを次回の正常スナップショットへ入れ替え、古い行を残し続けないようにします。他情報源の施設は保持し、複数出典・ID衝突・イベントが参照している施設の削除は自動更新を止めて手動確認します。

公式の次候補として、明石市「子育て施設一覧」、加古川市「赤ちゃんの駅」「公共施設」のCSVを登録しましたが、**すべて enabled=false の審査待ち**です。保育園や児童クラブを誰でも入れる遊び場と誤表示しないよう、CSVの列・用途・ライセンス・公開範囲を確認するまで本番掲載しません。詳細は [Phase 1C候補審査](planning/phase1c-source-candidates.md) を参照してください。

Phase 1Cで新規に公開したイベントは0件です。GitHub Pages・Oracle cronは未設定です。

## Phase 1D — 施設一覧と独立した検索登録条件

- 実イベントが0件でも、確認済みの施設を `places.html` に一覧表示します（名称・所在地・料金不明表示・公式サイト・出典）。
- **既存の4施設だけでは検索登録しません**。`place_pages`の条件は、5件以上・公式データ3件以上・異なる公式サイトのホスト2種類以上・異なる公式URL5件以上・7日間連続の検証です。
- イベントの掲載条件とは独立していても、`site_url` 未設定時は `index.html` と `places.html` とも `noindex` のままです。
- 本番サイト（docs）の更新は次のサイト生成時に行われます。このPRはGitHub PagesやSearch Consoleを有効化しません。
- 加古川市「都市公園」の公式CSV候補は未審査なので `enabled=false` のまま。公開対象かどうか・データの鮮度と公式URLを確認してから判断します。

## Phase 1E — GitHub Actionsの未公開サイトプレビュー

- すべてのPRとmain更新時にオフライン単体テストを実行し、**成功した場合のみ**、チェックイン済みデータからサイトを再生成・検証します。
- `Offline Python tests and unpublished preview` の実行結果画面に、日本語の掲載件数・情報源数・noindex件数のレポートを表示します。
- `unpublished-local-guide-preview` アーティファクトは7日間ダウンロードでき、`docs/index.html`、`docs/places.html`、CSSなどをブラウザ等で確認できます。Google検索への登録・Pagesへの公開ではありません。
- `workflow_dispatch` にも対応しますが、手動実行でもネットワークからのデータ収集やGitHubへのpushは行いません。
- ビルドは公式な実データのみを使用し、架空のイベントを生成しません。失敗するとチェックが赤くなるため、問題のあるPRはマージしないでください。
- `scripts/preview_report.py` を使えばローカルでも `python -m scripts.preview_report --output preview-report.md` で安全な件数レポートを生成できます。
- **Oracle cron、note、Search Console、Pages公開は未設定のまま**です。


## Phase 1F — イベント情報源の利用申請に向けた準備

公式RSSやイベントカレンダーの候補を3件追加し、既存候補と合わせて計19件としました。うち**自動収集可能なものは明石市観光施設CSV1件のみ**です。

[イベント情報源問い合わせ資料](planning/event-source-outreach.md) に、加古川市・姫路市・明石市・兵庫県への質問文と審査項目をまとめました。RSSの発行日時をイベント開催日時に読み替えず、開催日・会場を取得できる正規のデータソースと再利用条件が確定するまでは本番に取り込みません。

[公開・毎朝更新までのチェックリスト](planning/go-live-checklist.md) を整備しています。GitHub Pages公開やOracle VMのcron設定はまだ実施しません。


## Phase 1H — 民間イベントページと地域RSS候補

公式商業施設のイベントページ（アリオ加古川、ニッケパークタウン、ABCハウジング加古川、イオン明石、アスピア明石、イオン姫路大津）には2026年10月の親子向けイベントが実在。地域メディア3件（かこがわノート、明石じゃーなる、加古川のこと）のRSSも、2026-10-14に単発メタデータ調査で取得できました。

**取得できることと、商用サイトへの転載を許されることは別**です。候補はすべて無効のまま。情報源は28件、有効なのは明石市観光施設CSV1件だけです。調査結果は [民間情報源の監査台帳](planning/private-source-audit.md) を参照してください。


## Phase 1I — 許可審査後に使うRSS確認待ちキュー（オフライン）

RSSから記事URLを候補として拾う処理を追加しますが、**外部への定期取得は有効化しません**。かこがわノート・明石じゃーなる・加古川のこと・姫路の種はすべて`rss_discovery_review_status=unverified`のままです。

RSS XMLを人手で準備し、利用規約、robots、内部発見用途、根拠URLと30日以内の審査が揃った場合のみ、`python -m scripts.stage_approved_feed --source-id <source_id> --xml-file <local.xml>` を利用できます。候補は`cache/rss_discovery_queue.json`へ、記事URLと発行日・暫定分類のみ保存されます。記事タイトル・本文・写真は保存せず、`data/events.json`や`docs/`へ直接掲載しません。

詳細は[民間情報源監査](planning/private-source-audit.md)。

## Phase 1J — 民間情報源のリンク方針とRSS取得許諾を区別（2026-10-15）

かこがわノートは個別記事へのリンクを歓迎し、ABCハウジングは通常のリンクを原則自由としています。しかし**RSS/HTMLの自動定期取得まで許可されたわけではありません**。各ソースにはリンク方針のみ確認済みと記録し、権利/robots/内部RSS発見/本番取得の許諾審査は未承認のままです。

- 詳細: [民間情報源監査](planning/private-source-audit.md)
- 未送信の問い合わせ草案: [民間情報源への確認依頼](planning/private-source-permission-requests.md)

本変更では本番データ0件追加・外部アクセスジョブ追加なし、GitHub Pages/Oracle cron/note設定も変更しません。

## Phase 1K — 楽天トラベルの収益化準備（公開・外部アクセスなし）

地域イベント・施設情報を主役に、加古川発・家族4〜6人の旅行記事を**サブコンテンツ**として将来追加するため、楽天トラベルの公式APIとアフィリエイトの登録条件を整理しました。

新設`config/travel_affiliate.json` は`enabled=false`かつAPI取得・広告公開も無効。実際の公開URLの楽天アフィリエイトサイト登録、GitHub Pagesの営利目的制限、楽天APIの利用/クレジット・宿泊料金の確認が済むまで有効化しません。`localguide/travel_rakuten.py` はネットワークなしのオフライン候補処理と、人数・年齢・室数・食事・旅行日程の料金見積条件のチェックだけです。

**楽天トラベル公式APIの最安料金は家族合計額ではありません**。写真/レビュー原文の保存・自動記事量産は行いません。詳細と公開前チェックは [旅行モジュール計画](planning/travel-module.md) を参照。

## Phase 1L — Cloudflare Pages公開先の選定・デプロイ準備（2026-10-15）

公開先を**Cloudflare Pages（無料枠）**に決定。GitHubは引き続きソース管理・PR/CIを担当します。初回のCloudflare GitHub連携は`pages.dev`にサイトを**実際に公開する操作**のため、現在は接続・公開しません。

- [Cloudflare Pages設定手順](planning/cloudflare-pages.md) を参照してください。Framework preset=None、ルートはリポジトリ直下、production branch=`main`、Build command=`python3 -m pip install -r requirements.txt && python3 -m scripts.cloudflare_build`、出力=`docs`。
- `.python-version` でPython 3.12を指定し、CIと本番ビルドの差を小さくします。
- `python -m scripts.cloudflare_build` は**承認済みのリポジトリ内のJSONだけ**で再ビルドし、サイト検証を実行します。ネットからの取得、メール送信、課金、Git push、Pagesデプロイはしません。
- Cloudflare用の `_headers` はサイト生成時に自動生成します。まだインデックス可能なHTMLがない間は`X-Robots-Tag: noindex`、同時にクリックジャッキング・MIME推測への標準的なヘッダーを付与します。公開条件を満たすようになったら`noindex`ヘッダーは自動で外れ、各HTMLの個別SEO判定が適用されます。
- CloudflareのプレビューURLは初期状態で一般閲覧可能（検索エンジン向け`noindex`は付与）。正式公開まで自動プレビュー展開も有効にしません。
- 現時点でイベント0件・明石市の確認済み施設4件。正式公開、URL確定、楽天アフィリエイト媒体登録、Oracle cron、Search Consoleは未実施です。

