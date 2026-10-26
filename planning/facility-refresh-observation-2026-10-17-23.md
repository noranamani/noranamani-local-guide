# 明石市施設CSV：7日間の定期実行観察結果

観察期間：2026-10-17〜23（Asia/Tokyo）。最終集計は10/23正午時点。
対象：[Issue #29](https://github.com/noranamani/noranamani-local-guide/issues/29)。
基準main：`9fc25d98b0471288d011855cbb6dab34dad183a9`。
最終データmain：`370fd0bc0f6cd8ce2fa1c036c2fc0c0da2f7c475`。

## 判定と観測範囲

**予定した7回のschedule実行を確認。取得成功4日、事前テスト不合格で取得しなかった日3日。7日連続成功とは判定しない。** 固定日時テストと本番スナップショットの混在を2件修正し、所有者承認によるPR #39適用後、10/23の自然実行で取得が回復した。

平常時は09:00に未開始を保留し、12:00に再確認した。10/17は朝9時・12時のリアルタイム観察がなく、夕方に保存ログ・コミットを事後確認した。定期実行が丸一日未観測の日はないが、連続監視や全時刻の健全性を示す記録ではない。

[初回準備](https://github.com/noranamani/noranamani-local-guide/issues/29#issuecomment-6210525911)とIssue内の日次記録を根拠とする。GitHub Actionsの成功、Cloudflareのデプロイ成功、公開HTMLの実測を区別した。

## 日次台帳（JST）

| 日付 | schedule run | 実行時刻 | 08:25からの遅延 | 結果・公開確認 |
|---|---|---|---|---|
| 10/17 | [38990665161](https://github.com/noranamani/noranamani-local-guide/actions/runs/38990665161) | 10:23:43〜10:24:01 | 1:58:43 | 191テスト・実取得・4件保存成功。HTTP200、当日確認日時、meta/HTTP noindex確認 |
| 10/18 | [39086046895](https://github.com/noranamani/noranamani-local-guide/actions/runs/39086046895) | 10:19:10〜10:19:23 | 1:54:10 | 191テスト中7失敗、取得なし。10/17の施設・成功日時を保持、本番4件/noindex確認 |
| 10/19 | [39185494206](https://github.com/noranamani/noranamani-local-guide/actions/runs/39185494206) | 10:28:15〜10:28:34 | 2:03:15 | PR #35適用後192テスト・実取得・4件保存成功。当日反映/noindex確認 |
| 10/20 | [39356327772](https://github.com/noranamani/noranamani-local-guide/actions/runs/39356327772) | 10:58:03〜10:58:21 | 2:33:03 | 202テスト・実取得・4件保存成功。当日反映/noindex確認 |
| 10/21 | [39529344655](https://github.com/noranamani/noranamani-local-guide/actions/runs/39529344655) | 10:47:33〜10:47:47 | 2:22:33 | 202テスト中2エラー、取得なし。10/20のデータ保持、本番4件/noindex確認 |
| 10/22 | [39707030535](https://github.com/noranamani/noranamani-local-guide/actions/runs/39707030535) | 10:40:21〜10:40:40 | 2:15:21 | 同じ2エラー、取得なし。公開HTMLの監視読取が403で実表示未確認。所有者から20日の表示報告あり |
| 10/23 | [39885539618](https://github.com/noranamani/noranamani-local-guide/actions/runs/39885539618) | 10:42:43〜10:43:02 | 2:17:43 | PR #39適用後203テスト・実取得・4件保存成功。Cloudflare success、実表示は監視読取403で未確認 |

全runのeventはschedule。各日1回、合計7回。成功日は全てCSV本文を正規化した経路で、実304の発生は観測していない（HTTP番号自体はログ未出力）。単体テスト中の模擬304表示を実通信と混同しない。

## 最終日のログ・差分・状態

- run head：`f89f50a2fb21c65b5202d780286e7e7154773fb1`。
- refresh job：[120192738610](https://github.com/noranamani/noranamani-local-guide/actions/runs/39885539618/job/120192738610)、10:42:46〜10:43:01 JST。
- 取得前203テスト成功（4.314秒）、実CSV4件正規化、4→4件検証と隔離Cloudflareビルド成功。主要3ステップsuccess、REFRESH_OUTCOME=success、通常push成功。競合・権限不足なし。
- 更新コミット：[370fd0bc0f6cd8ce2fa1c036c2fc0c0da2f7c475](https://github.com/noranamani/noranamani-local-guide/commit/370fd0bc0f6cd8ce2fa1c036c2fc0c0da2f7c475)。親はrun head。全変更ファイルは`data/places.json`と`data/source_state.json`だけ。
- 4施設（明石市立天文科学館、明石市立文化博物館、明石公園、魚の棚商店街）を保持。ID・名称・住所・公式URL・出典・発表日2026-08-25は変更なし、重複・欠損なし。差分は取得・確認日時、試行日の更新のみ。
- `attempt_day=2026-10-23`、`attempts=1`、`halted=false`、`last_error=null`。
- `last_attempt_at=last_success_at=2026-10-23T10:42:56.748387+09:00`。全施設の`fetched_at/last_checked_at/last_verified_at`も同日時。ETag/Last-Modified保持。
- 更新SHAの通常push起点unittest/previewは0件（未実行）。GITHUB_TOKENによるpushは別のpush起点Actionsを連鎖起動しないため、更新ジョブ内の203テスト・隔離ビルドとは区別する。
- 更新SHAの[Cloudflare Pagesチェック](https://github.com/noranamani/noranamani-local-guide/runs/120193404928)は10:45:02 JSTにsuccess。

成功日のJob summary本文はチェックAPIではnullで未確認。ステップoutcome・実ログ・全コミット差分・JSON・Cloudflareチェックで照合した。失敗3日は取得スクリプトが起動せず、取得結果summaryも未生成。保存ステップはNo persisted changes neededで、取得試行予約・コミット・pushなし。

成功4回の更新コミットはいずれも許可JSON2ファイルだけ：`db7adff8614041822a93fadd921bb48e490f6c4c`、`2190cbe14fba034dd760bab5d83a02a756550c30`、`03081b7ddfefa63074d8d04d7e5b8e2057b38564`、`370fd0bc0f6cd8ce2fa1c036c2fc0c0da2f7c475`。旅行記事・写真・楽天source_html原文・広告リンク・公式リンク・設定への自動更新の影響なし。

## 発見した不具合と修正

1. [PR #35](https://github.com/noranamani/noranamani-local-guide/pull/35)：更新試験が本番の同日試行済み状態をコピーしてskippedになった。テストの一時領域を前日成功状態に固定。同日再実行/JST翌日の回数判定を模擬テスト。所有者承認により10/19にマージし、自然実行で回復。
2. [PR #39](https://github.com/noranamani/noranamani-local-guide/pull/39)：PR #38で追加した近場ガイド試験が固定時計10/19と本番施設10/20を混在させ、正しい未来日時検証で停止した。テスト用固定データを一時領域に分離し、未来の確認日時を拒否する試験を追加。所有者承認により10/22にマージし、10/23の自然実行で回復。

両修正はテストファイルだけ。本番の取得、安全制限、審査日、公開設定は変更していない。各PRの全テスト/オフラインビルド/サイト検証/Linux CI成功を確認してからマージした。監視の一般的なマージ禁止は継続し、上記2件以外へ承認を広げない。

## 安全条件と未実地検証の区別

実測したのは日次1run・成功日1試行、承認ソースだけの取得、許可JSONのみ保存、事前テスト失敗時の取得スキップと前回データ/成功日時保持。

日次上限とJST翌日判定、concurrency直列、401/403/429のhaltと翌日も停止、不正CSV・75%未満急減・隔離ビルド失敗時の保持、未審査redirect・HTML/CAPTCHA・2MiB超過・審査30日超・整合不良の拒否、push競合時の停止は既存実装とオフラインテストによる確認。これらの異常を本番で発生させた検証ではない。実CSVの拒否・急減・競合は観測なし。本番への故障注入、手動CSV取得、dispatch、再実行、停止解除、日次上限変更を行っていない。

`akashi_open_data`のみ有効、他27ソース無効。審査checked_atは`2026-10-14T17:00:09.066057+09:00`を保持し、自動延長なし。**2026-11-13までに人手再審査**する既存手順を維持する。72時間以上古い施設の掲載除外は再ビルド時の判定で、配信済みHTMLが時間だけで消えるとは扱わない。

## 未確認事項・引き継ぎ

- 10/22〜23の公開HTMLの独立した実測は未確認。監視環境のHTTP403/TLSエラー/ブラウザータイムアウトを記録。認証や制限を回避していない。公開HTMLの403は明石CSVからの403とは別で、haltの根拠にしていない。
- 最後の監視側の実表示確認は10/21 12:06:48 JST（HTTP200、4施設、10/20確認日時、meta noindex,follow・HTTP X-Robots-Tag noindex）。10/22の所有者の「20日」報告はマージ前の確認。
- 所有者/ChatGPTは本番`places.html`で4施設・10/23 10:42の確認日時・noindexを確認し、本記録をレビューする。Job summary本文も管理画面で補完できれば記録する。
- 7日連続成功やSEO公開承認の根拠にしない。既存noindexを維持する。
- 予定した7回の観察終了後、確認用automation `issue-29-csv-7`だけを停止する。GitHub側の毎朝CSV更新は既存設定のまま継続する。
- この文書PRはmain未マージでレビュー用。Issue #29はChatGPT/所有者レビュー前に閉じない。
