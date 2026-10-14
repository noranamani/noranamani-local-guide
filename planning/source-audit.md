# 情報源の初期審査台帳（2026-10-14）

このファイルは **候補の記録** です。robots.txt、利用規約、API/CSV、商用再利用の条件を満たしたことは意味しません。

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
