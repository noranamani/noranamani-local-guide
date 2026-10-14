# 情報源審査台帳（2026-10-14）

候補ごとに取得・利用条件を記録します。許可済みは明石市の観光施設CSV1件です。他の情報源に同じ許諾があるとは扱いません。

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
