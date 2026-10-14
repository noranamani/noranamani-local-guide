# 情報源審査台帳（2026-10-14）

候補ごとに取得・利用条件を記録します。許可済みは明石市の観光施設CSV1件です。他の情報源に同じ許諾があるとは扱いません。

## Phase 1B：加古川市イベントオープンデータの調査

確認日時：2026-10-14 17:20〜17:26 JST（Asia/Tokyo）。担当：Codex。
User-Agent：`noranamani-local-guide/0.1 (+https://github.com/noranamani/noranamani-local-guide; manual source-policy review)`。
公式ページ・カタログのメタデータ・利用規約を単発で確認しました。CSV本文、NGSI API、登録者向け機能は取得・利用していません。

**判定：現時点ではイベント取込みを実装・有効化しない。** 指定されたデータセットとリソースはGETで404、CSVはHEADで404です。
利用できる最新イベントデータや現在以降の開催回を確認できません。全イベントが過去のもの、または件数0件だと判定した結果ではありません。
コード・依存パッケージ・config/sources.json・本番dataは変更せず、調査報告のみを追加します。
既存の一般HTMLソースの利用不可判定と、オープンデータのCC BY 4.0による許諾は別々に扱います。

### 公式性と到達性

加古川市公式の[オープンデータ提供案内](https://www.city.kakogawa.lg.jp/soshikikarasagasu/kikakubu/jouhouseisakuka/opendata/opendata_kaishi.html)をHTTP 200で確認しました。
このページから `opendata-api-kakogawa.jp/odp/` とBODIKの加古川市ページがリンクされています。
公式案内のページ更新日は2026-08-12です。これはイベントCSVの更新日ではありません。

| 対象 | 実測結果 | 意味 |
|---|---|---|
| [カタログのrobots.txt](https://opendata-api-kakogawa.jp/robots.txt) | GET 404 | robots不在。転載許諾やAPI登録不要を意味しない |
| [イベントデータセット](https://opendata-api-kakogawa.jp/ckan/dataset/event) | GET 404 | 現在のライセンス・リソース一覧・更新頻度を再確認できない |
| [指定リソースページ](https://opendata-api-kakogawa.jp/ckan/dataset/event/resource/43b54cf0-3cb6-44b4-af8c-574eeee5de10) | GET 404 | 列・最終更新・ダウンロード条件を確認できない |
| [指定CSV](https://opendata-api-kakogawa.jp/ckan/dataset/e1739098-1514-458e-bc9e-840ce000ef98/resource/43b54cf0-3cb6-44b4-af8c-574eeee5de10/download/rename.csv) | HEAD 404、本文GETなし | 掲載URLの存在を確認できない。ファイルの内容は未取得 |
| [カタログトップ](https://opendata-api-kakogawa.jp/odp/) | GET 200、81データセットと表示 | サイト全体が停止しているとは判定しない |
| [カタログ「イベント」検索](https://opendata-api-kakogawa.jp/ckan/dataset?q=%E3%82%A4%E3%83%99%E3%83%B3%E3%83%88) | GET 200、該当データセットなし | この検索範囲では後継のイベントCSVを発見できない |
| [カタログ「event」検索](https://opendata-api-kakogawa.jp/ckan/dataset?q=event) | GET 200、該当データセットなし | 英語名による検索でも発見できない |
| [BODIK加古川市ページ](https://odcs.bodik.jp/282103/) | GET 200、6データセットと表示 | 統計書・地図等の一部データの別配布先 |
| [BODIK加古川市「イベント」検索](https://data.bodik.jp/organization/282103?q=%E3%82%A4%E3%83%99%E3%83%B3%E3%83%88) | GET 200、該当データセットなし | 確認範囲では代替のイベントCSVなし |

これは公式ホストからのHTTP応答であり、前回のproxy CONNECT 403とは異なります。
404の原因（移転・非公開化・削除・一時的障害等）は断定しません。別ホスト・認証・CAPTCHA・プロキシを迂回して取得していません。

### 利用条件：データの再利用とAPI登録を区別

1. [加古川市オープンデータ利用規約の配布ページ](https://opendata-api-kakogawa.jp/ckan/dataset/termsofservice)と、そこからリンクされた[利用規約PDF](https://opendata-api-kakogawa.jp/ckan/dataset/8d965cb5-05ff-4074-89c5-decbf341350d/resource/e189cceb-4f28-44c2-834e-34e58867516a/download/kakogawa-city-open-data-terms-of-use.pdf)をHTTP 200で確認しました。PDFは301,488 bytes、HTTP Last-Modifiedは2024-10-08 16:03:50 JSTです。これもイベントCSVの更新日時ではありません。
2. データ利用規約第2項は、カタログ公開コンテンツを**CC BY 4.0**で利用可能と定めています。[サイトの基本方針](https://opendata-api-kakogawa.jp/odp/about/)も営利・非営利を問わない公開を明記しています。一般の市ホームページの無断転載禁止を根拠に、このオープンデータも一律に利用不可とはしません。
3. 第3項では、作品タイトル・加古川市・CC BY 4.0とライセンスURLの表示が必要です。加工する場合は改変して利用している旨を表示し、市が作成した情報と誤認させてはいけません。第三者が権利を持つ部分は別途確認が必要です。写真・ロゴ・本文を利用する判断はしていません。
4. [カタログサイト利用規約](https://opendata-api-kakogawa.jp/odp/tos/)は、冒頭で対象を「提供するAPI機能」と定義し、第2項で登録者だけが利用できると規定しています。第6項はAPI使用のクレジットと、市による内容保証がない旨の表示を要求します。データ利用規約とは別の規約です。
5. [API利用案内](https://opendata-api-kakogawa.jp/odp/api%E3%81%AE%E5%88%A9%E7%94%A8%E3%81%AB%E3%81%A4%E3%81%84%E3%81%A6-2/)は、API利用またはアプリケーション開発の希望者に申請を案内しています。匿名CSVの直接ダウンロードをこのAPI機能に含めるか、別途申請が必要かは明示的に確認できません。**CSVにも登録が必須だとは断定しませんが、不要とも断定しません。**
6. 現在の個別イベントリソースが404なので、個別注記・ライセンス例外・最新の取得条件は確認できません。CC BYの表示と「毎日更新」「2025-10-01最終更新」はPhase 1B依頼文の過去の観測情報であり、今回の実測結果として扱いません。

確信度：一般のデータ利用規約がCC BY 4.0を採用していること、APIに登録が必要なことは**高い**です。
個別イベントデータの現在の適用条件、匿名CSVへの登録要否、最新データの有無は**未確認**です。許諾を推測して有効化しません。

### 実データ・鮮度・アダプター適合性

| 項目 | 今回の結果 |
|---|---|
| CSV実レコード数 | 未確認（本文未取得） |
| 2026-10-14以降の開催回数 | 未確認。0件と数えたわけではない |
| CSVの最終更新・サイズ・文字コード・列・サンプル | いずれも未確認 |
| 本番に取り込んだ加古川市イベント | 0件（取込み未実施） |
| 既存公開データ | 明石市の実施設4件、イベント0件 |
| 対応する新アダプター/列マッピング | 追加なし |

現行event_csvは審査済みのID・タイトル・自治体・公式URL等の列が必要で、列の無い日時・会場・料金・主催者・状態を推測しません。
実CSVがないため適合性は判定できません。今後は申込期限を開催日と混同せず、複数開催回・中止・終了・日本時間・出典表示を検証してから取込みを判断します。
新しい `kakogawa_events_open_data` は正式条件が確認できた場合にだけ登録・有効化し、今回は設定を増やしません。

### 代替の公式RSS/配布先

代替RSSは、公式ホームページのリンクから発見し、形式・公表日時だけを手動確認しました。タイトル・本文・写真を本番dataに保存/再掲載せず、記事ページを自動巡回していません。

| 候補 | 実測した形式・鮮度 | 取得・掲載に必要な確認 | 今回の判断 |
|---|---|---|---|
| [明石市公式新着RSS](https://www.city.akashi.lg.jp/shise/koho/oshirase/oshirase.xml) | GET 200、RSS 1.0/RDF、100項目。項目の公表日時は2026-06-02 13:00〜2026-10-14 00:00 JST。HTTP Last-Modifiedは2026-10-14 17:00:04 JST | [一般サイトの著作権条件](https://www.city.akashi.lg.jp/seisaku/kouhou_ka/shise/koho/homepage/chosakuken.html)は無断複製・転用を禁止。RSSに対する別の再掲載許諾、開催日/場所を含む正規フィードの提供を確認する必要がある | 新着発見の次候補。自動取得・公開への取込みは未承認 |
| [姫路市公式新着RSS](https://www.city.himeji.lg.jp/rss/rss.xml) | [公式トップ](https://www.city.himeji.lg.jp/)のrel=alternateリンクから発見。GET 200、RSS 2.0、30項目。項目の公表日時は2026-10-14 11:10:04〜16:59:59 JST。HTTP Last-Modifiedは同日17:02:39 JST | [公式著作権条件](https://www.city.himeji.lg.jp/site_policy/0000000009.html)は無断二次利用を禁止。RSS固有の許諾、開催回データの提供・転載範囲を確認する必要がある | 新着発見の次候補。現在以降の開催回の件数は未確認で、取込みは未実装 |
| [加古川市が案内するBODIK配布先](https://odcs.bodik.jp/282103/) | 6データセット、最新一覧には2026-09-14の道路データ等。イベント検索は該当なし | 新しい公式イベントCSVが追加されれば、その個別ライセンス・列・更新頻度を確認 | 後継CSVの再調査先。道路/統計の更新をイベントの鮮度とは扱わない |

RSSの公表日時やHTTP Last-Modifiedは開催日時ではありません。これらを「開催予定イベントの件数」として数えません。
現時点で、最新の開催回と再利用条件を満たして本番取込み可能と確認できた代替ソースはありません。

### 市への問い合わせ・登録が必要になった場合

担当：加古川市 企画部デジタル改革推進課。公式の[問い合わせ案内](https://opendata-api-kakogawa.jp/odp/contact/)から[スマイルメール入力フォーム](https://www.smilemail-kakogawa.jp/form/index.php?section_cd=1006)へ進めます。
今回、問い合わせの送信・API申請・個人情報入力は代行していません。

先にユーザーから確認していただきたい事項：

- eventデータセットと指定CSVの404の理由、現行のCSV URLまたは後継データセット。
- 現在以降の開催回を含む更新の有無と、実際の更新頻度。「毎日」と過去の最終更新表示の関係。
- 公開CSVを登録なしで1日1回程度自動ダウンロードし、事実項目のみをCC BY 4.0の出典・加工表示付きで再利用する際に、API登録または別の申請が必要か。
- APIだけが提供経路の場合、対象データモデル・必要な認証・アクセス上限・掲載クレジット、イベント本文/写真/第三者権利の除外範囲。

登録が必要と回答された場合は、[API利用案内](https://opendata-api-kakogawa.jp/odp/api%E3%81%AE%E5%88%A9%E7%94%A8%E3%81%AB%E3%81%A4%E3%81%84%E3%81%A6-2/)掲載の申請書またはスマイルメールでユーザーが申請します。
必須項目は氏名・所属組織・メールアドレス。新規時のユーザーIDは空欄、アプリ名を記載する場合はアプリ説明も必須です。利用目的等も案内に従って記載します。
公式案内の発行目安は最大3開庁日です。発行された認証情報はチャット・Git・公開データに入れず、必要になった時点で安全な設定方法を確認します。

### Phase 1の退行確認

オフラインテスト73件が成功しました。既存の実施設4件・イベント0件を使った生成、7データセットとHTMLのvalidate --site、内部HTTP 200での4施設表示・noindex確認も成功しました。
生成は独立した一時ディレクトリで行い、config・docs・本番data・取得状態のファイル内容と更新日時が変わっていないことを確認しました。git diff --checkと報告の秘密値既知パターン・文字化け検査も成功しました。
ガジェットサイト、Oracleの定期実行、GitHub Pages設定、ChatGPT定期タスク、Search Console、note投稿は変更しません。

## 初回の接続制限（履歴）

担当：Codex。User-Agent：`noranamani-local-guide/0.1 (manual source-policy review)`。
以下は手動の取得条件調査です。記事の自動巡回・保存・転載は行っていません。

| 調査URL | 実測結果 | 判断 |
|---|---|---|
| https://www.city.kakogawa.lg.jp/robots.txt | proxy CONNECT: 403 Forbidden | robots未確認、取得不可 |
| https://www.city.himeji.lg.jp/robots.txt | proxy CONNECT: 403 Forbidden | robots未確認、取得不可 |
| https://www.city.akashi.lg.jp/robots.txt | proxy CONNECT: 403 Forbidden | robots未確認、取得不可 |
| https://www.city.akashi.lg.jp/soumu/j_kanri_ka/shise/opendata/index.html | proxy CONNECT: 403 Forbidden | カタログ・CSV実URL・個別ライセンス未確認 |
| https://www.city.himeji.lg.jp/site_policy/0000000009.html | proxy CONNECT: 403 Forbidden | 利用規約・二次利用条件未確認 |

これはクラウドの接続制限による拒否で、公式サイト側のHTTP応答ではありません。
プロキシを迂回しての再試行は行っていません。実URLの正しさや公式性も到達確認ができていません。
環境設定ドラフトに上記3ホストを追加済みですが、保存だけでは実行環境に適用されません。
環境設定の反映後、robots・ポリシー・CSV実URL・データセット単位の再利用条件を再調査してください。
追加費用、秘密値、GitHubトークンはこの調査の前提ではありません。

初回調査時点では許可済みソース0件、設定12件はすべて`enabled=false`でした。現在の状態は以下の再調査結果を参照してください。
その他の地域・商業施設・観光協会の候補は接続調査しておらず、引き続き未審査です。
初回にはRSS実フォーマットやイベント一覧の内容も未取得でした。一般ニュースRSSから開催日時を推測しません。
初回は架空CSVによるオフライン検証のみでした。再調査では下記の実CSVを審査し取得・生成まで検証しました。

## 設定変更後の再調査・許可済みソース

2026-10-14、ネットワーク設定が変更された後に再調査。プロキシ迂回・TLS検証無効化は行っていません。

| 調査先 | 観測結果 | 運用判断 |
|---|---|---|
| 加古川市・姫路市・明石市の /robots.txt | 各公式ホストからHTTP 404 | robots不在を記録。転載の許可は別途審査 |
| 明石市オープンデータ配布ページ | HTTP 200、観光施設CSVを公式ページから確認 | 対象CSVを個別審査 |
| 明石市オープンデータ利用規約PDF | HTTP 200 | 商用・複製・公衆送信・加工利用可、出典と加工表示が必要。CC BY 4.0互換 |
| 明石市観光施設CSV | HTTP 200、text/csv、UTF-8 BOM、4行、固定ID列 | 事実5列のみを取得・公開可能として有効化 |
| 加古川市著作権・免責事項 | HTTP 200、権利者の許可なく使用・転載を禁止 | HTML自動取得は無効。reuse_rights_status=denied |
| 姫路市著作権ポリシー | HTTP 200、無断二次利用禁止 | HTML取得・転載は無効。reuse_rights_status=denied |
| 明石市公式RSS | HTTP 200、RSS 1.0/RDF、item 100件 | 形式・到達性のみ確認。一般サイトの無断複製禁止があり、RSSの別途利用許諾は未確認。無効のまま |

### 明石市 観光施設一覧（akashi_open_data）

- 配布・出典ページ：https://www.city.akashi.lg.jp/soumu/j_kanri_ka/shise/opendata/index.html
- 実CSV：https://www.city.akashi.lg.jp/documents/29427/282031_tourism.csv
- 利用規約：https://www.city.akashi.lg.jp/documents/29427/opendata_kiyaku.pdf
- robots：https://www.city.akashi.lg.jp/robots.txt （実測404）
- 審査User-Agent：noranamani-local-guide/0.1。GET対象は上記CSVのみ、定期取得を登録せずCLIの日次上限1回を維持。
- robots 404はRFC 9309 §2.3.1.3に基づく不在の記録。空のrobots_rulesとrobots_http_status=404を保存し、架空のAllowルールは作成しない。
- 規約（1）の適用範囲は本配布ページのオープンデータ。一般の市サイトの記事・写真には適用しない。
- 規約（2）は出典表示と加工表示、（3）（4）は第三者権利・ロゴ等の除外、（7）は市による公式作成と誤認させる表現の禁止、（9）はCC BY 4.0互換を規定。
- 公開範囲：ID→source_event_id、名称→name、所在地_市区町村→municipality、所在地_連結表記→address、URL→official_url。
- 4件は天文科学館・文化博物館・明石公園・魚の棚商店街という公開観光施設。取り込む住所は各施設の公開所在地で、個人の自宅住所・子どもの個人情報はないことを個別確認。
- 説明文・画像・連絡先・営業時間・料金・アクセス方法・備考は保存/再掲載しない。料金・屋内外などはunknown/nullのまま。
- 発表日は配布ページの「観光施設一覧（2026年8月25日）」を2026-08-25として保持。時刻は不明。HTTP Last-Modified（2026-08-31）や取得日を発表日として上書きしない。
- レコード出典URLはCSV、公式URLは施設サイトへ分離。配布ページと利用規約へのリンク、加工表示を生成物に表示。
- 初回実CSVのSHA-256：df7412c7b1a53be48b720819254baa12d57c68ed4446d59878c91f717d6e3b85（将来更新を禁止する固定チェックサムではなく、審査した内容の監査証跡）。
- 実CLI collect→build→validate --siteを成功、施設4件・イベント0件。HTTP配信を内部で確認。新規費用・APIキー不要。
- enabled=trueはこの1件だけ。残り11件は無効。Pages公開・Oracle cronは未設定。

### その他の公式ポリシー

- 加古川市：https://www.city.kakogawa.lg.jp/soshikikarasagasu/kikakubu/kikakubukohoka/kouhou/kanrenshisutemu_saitojoho_1/1418289171987.html （権利者の許可なく使用・転載不可）
- 姫路市：https://www.city.himeji.lg.jp/site_policy/0000000009.html （無断二次利用禁止、リンク可能）
- 明石市一般サイト：https://www.city.akashi.lg.jp/seisaku/kouhou_ka/shise/koho/homepage/chosakuken.html （無断複製・転用不可、各担当への許諾問い合わせが必要）
- 明石市RSS：https://www.city.akashi.lg.jp/shise/koho/oshirase/oshirase.xml （RSS 1.0。記事本文・フィード項目は保存/転載しない）

## 有効化の判定と記録

1. 公式の配布ページと実CSV URLを確認。恒久ID・文字コード・必須列・データ更新日を記録する。
2. robotsの対象パスとUser-Agent、利用規約、データセットのライセンス、商用利用、引用・改変・出典表記条件を確認する。
3. 使用する列が日時・会場・料金等の事実であること、画像・説明本文を再掲載しないこと、個人住所を除外できることを確認する。
4. config/sources.jsonに根拠URL、checked_at、robots_url、実robots_rules、審査status、adapter、field_map、content_scope、privacy_review_statusを記録する。
5. すべてallowedになったソースだけenabled=trueにする。明示された無料区分・公共施設住所は追加の審査フラグを設定する。
6. 取得→validate→build→validate --siteを実行し、出典・日付・料金を人手でも確認する。公開や定期実行は別途承認後。

審査statusの実装値は`unverified`、`allowed`、`denied`です。審査の有効期限は30日です。
HTTP 401/403/429、未審査リダイレクト、CSV形式変更、急減、タイムアウト等は安全停止します。

## 優先度
| 情報源 | 活用候補 | 次に確認すること |
|---|---|---|
| 加古川市イベントガイド | 日付・会場・年齢 | robots、利用条件、取得範囲、RSS有無 |
| 姫路市イベントカレンダー | カテゴリ・開催期間 | 二次利用条件、robots、許諾の要否 |
| 明石市公式RSS | 新着情報発見 | 実URL、配信形式、利用条件 |
| 明石市オープンデータ | 子育て・観光施設CSV | 個別CSV・ライセンス・出典表示 |
| 高砂市・播磨町・稲美町 | 周辺地域 | イベント一覧・RSS・オープンデータ |
| アリオ加古川・ニッケ・イオンタウン | 商業施設の催事 | 取得・再利用許諾 |
| 観光協会・兵庫観光ナビ | 観光イベント | フィードの有無・利用条件 |

## 調査に必要な記録
- 確認日時、確認担当、公式ポリシーURL、robots URL、対象パスとUser-Agent
- 自動取得の可否（不明なら不可として運用）、再利用範囲、商用利用、出典条件、個別許諾の記録
- RSS / API / CSV / HTML、最終確認結果、想定アクセス頻度、異常時の停止条件
- 対象URLが存在するか、リダイレクトされないか、正しい公式ページか
- 不足があれば問い合わせ先と回答記録

## 最初に確認する公式URL
- https://www.city.kakogawa.lg.jp/cgi-bin/recruit.php/7/list/
- https://www.city.himeji.lg.jp/module/event_search.php
- https://www.city.akashi.lg.jp/shise/koho/oshirase/oshirase.xml
- https://www.city.akashi.lg.jp/soumu/j_kanri_ka/shise/opendata/index.html

## 守ること
- 無断の本文・画像転載は禁止。公開するのは確認済みの事実、短い独自案内、公式URLを基本とする。
- 検索結果画面の無断スクレイピングをデータソースとして採用しない。
- 公式情報でない新店・閉店の噂は掲載しない。
- 許可未確認のソースは config/sources.json で enabled=false のままにする。


## Phase 1C — 施設CSV候補と更新処理（2026-10-14）

新たに明石市「子育て施設一覧」、加古川市「赤ちゃんの駅」「公共施設」を**未承認候補**として登録しました。取得有効化・実CSVダウンロード・イベント掲載は行っていません。データセットの存在とライセンス表示は公式配布ページや公開カタログの情報に基づくものですが、実カラム・最新内容・匿名CSVアクセス可否は未検証です。詳細: [phase1c-source-candidates.md](phase1c-source-candidates.md)。

施設CSVの再取得について、旧実装では消えた行が `data/places.json` に残り得ました。当該ソースのスナップショット単位で置換し、他ソースを残すように変更しました。大幅な件数減少、複数出典の施設、ID衝突、イベントの施設参照切れは更新せず停止します。HTTP 304や取得失敗時の既存動作は変更しません。


## Phase 1D — 都市公園CSVを追加候補として登録（2026-10-14）

- データセット: https://opendata-api-kakogawa.jp/ckan/dataset/urbanpark
- リソース情報: https://opendata-api-kakogawa.jp/ckan/dataset/urbanpark/resource/6213c4ba-c8c4-4831-8244-9f092cfa3e92
- 公開メタデータ上でCC BY表示、CSV/登録不要（auth type none）表示、最終更新日は2024-03-22。公開メタデータと実ファイルの鮮度や権利処理は同じではありません。
- **現時点ではCSV本文の取得・列の検証は未実施**。公式URL、現在営業中/一般利用可能か、遊具・設備、公開範囲の確認が必要です。
- オープンデータカタログ全体のAPI利用申請との関係も未解決につき、取込みは`enabled=false`で保留します。掲載施設・実イベントの増加はありません。
- 施設の検索登録準備として、イベント0件でも公式施設一覧を生成する変更を実装。公式施設5件以上、別公式ホスト2種以上、7日間の連続確認などの条件を満たした場合だけインデックス可能とします。

## Phase 1G — 明石市「子育て施設一覧」CSVの個人情報を含まない列・区分調査（2026-10-14）

**結論：一般の家族向けお出かけスポットには不適合。取込み無効のまま。**

- 公式出典ページ：https://www.city.akashi.lg.jp/soumu/j_kanri_ka/shise/opendata/index.html
- 公式配布CSV：https://www.city.akashi.lg.jp/documents/29427/282031_preschool.csv
- GitHub Actions単発調査：https://github.com/noranamani/noranamani-local-guide/actions/runs/38547243878
- 調査時にHTTP 200、Content-Type `text/csv`、208行を確認。受信したCSVは記録せず、列名・分類別件数だけを出力。
- `種別` の内訳：
  - 認可外保育所56、認可私立保育所35、放課後児童クラブ28
  - 認定こども園（幼稚園型）28、認定こども園（保育所型）25、認定こども園（幼保連携型）25
  - 認可公立保育所10、私立幼稚園1
- `URL` 列は存在するが、HTTPSの公式URL欄が埋まるのは28行のみ。
- `ID`、`名称`、`種別`、`所在地_市区町村`、`所在地_連結表記`、`URL` 等の列構造を確認。ただし施設情報の公開、個々の開設状況・入場可否・イベント開催は未検証。
- **児童館・子育て支援拠点・一般向け遊び場という分類はこのCSVに存在しません。** 今後の別ソース開拓を優先。
- 調査時に個別施設名、住所、メールアドレス、連絡先、CSVレコードをGitHubへ保存・記録していません。一般公開用`data/places.json`も変更しません。
- 自動調査を繰り返さないため、初回PRイベント用ワークフローは調査後に手動実行限定の`workflow_dispatch`へ変更。以降は明示的な人手実行なしに取得しません。
