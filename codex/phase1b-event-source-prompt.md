# Phase 1B — 加古川市イベントの正規データソース検証・安全な取込み

対象: `noranamani/noranamani-local-guide`。最初に `AGENTS.md`、`planning/source-audit.md`、`planning/data-schema.md`、`config/sources.json`、`localguide/`、`tests/` を読み、既存のPhase 1を壊さずに着手してください。

## 目的
明石市の施設4件を表示できるPhase 1に、公式ライセンスを確認した**開催予定の加古川市イベント**を安全に追加できるか検証し、条件を満たす場合にのみ最小限の機能を実装する。

## 第1候補（2026-10-14に公開ページで発見）
- 加古川市オープンデータのイベントデータセット: https://opendata-api-kakogawa.jp/ckan/dataset/event
- CSVリソース情報: https://opendata-api-kakogawa.jp/ckan/dataset/event/resource/43b54cf0-3cb6-44b4-af8c-574eeee5de10
- 掲載CSV URL: https://opendata-api-kakogawa.jp/ckan/dataset/e1739098-1514-458e-bc9e-840ce000ef98/resource/43b54cf0-3cb6-44b4-af8c-574eeee5de10/download/rename.csv
- カタログサイト利用規約: https://opendata-api-kakogawa.jp/odp/tos/
- API利用案内: https://opendata-api-kakogawa.jp/odp/api%E3%81%AE%E5%88%A9%E7%94%A8%E3%81%AB%E3%81%A4%E3%81%84%E3%81%A6-2/
- 加古川市公式のオープンデータ説明: https://www.city.kakogawa.lg.jp/soshikikarasagasu/kikakubu/jouhouseisakuka/opendata/opendata_kaishi.html

**注意**: カタログには「CC BY」「更新頻度: 毎日」とある一方、検索で取得できたリソース表示では **最終更新日 2025-10-01** でした（2026-10-14時点）。CSV自体の現在日時・実内容は未検証。**現在も毎日更新されているとは断定しない。**

**別の重要な注意**: オープンデータAPI利用規約は登録者向け利用を定め、API利用案内には申請手続きが記載されています。**登録が必要なAPI機能と、匿名で公開されているCSVファイルの直接ダウンロードに同じ申請が必要かは未確認**です。法的・技術的に曖昧なら自治体の確認待ちとし、無許可で利用を開始しないこと。公式サイトの一般ページでの無断転載禁止と、このCC BYデータセットのライセンスを混同しないこと。

## 調査タスク（実装より先）
1. 上記ドメインのrobots.txt、データセットとリソースのライセンス、利用規約の適用範囲、商用再利用・加工・出典表示・API登録の要否を確認し、出典URL・確認日時・実際の結果を監査台帳に記録する。
2. 公開CSVを安全に取得できる条件が確認できた場合に限り、適切なUser-Agentで**単発・低頻度の調査取得**を行う。CAPTCHA、認証、アクセス制限、プロキシ制限の回避は禁止。
3. HTTPステータス、最終更新日時、ファイルサイズ、文字コード、列名、サンプルレコード、現在日以降の開催回の件数を確認する。**期限切れの過去イベントしかない場合は本番有効化しない**。
4. 現行の`event_csv`アダプターで対応できる列を調査。市町名、会場、開催日、終了日、申込期限、主催者、公式URLなどが曖昧な行は無理に補完しない。
5. 登録申請が必要な場合は、申請先・必要事項とユーザーが行う操作を報告する。個人情報や申請を代行しない。

## 実装タスク（条件を満たす場合のみ）
1. `config/sources.json` に独立した `kakogawa_events_open_data` エントリを追加。正式審査完了までは `enabled=false` を維持。
2. すべての利用条件が確認でき、実データに現在日以降のイベントがあり、イベントの最低限の情報が取得できる場合のみ `enabled=true` としてテスト。
3. 日付型、複数日・複数回開催、日本時間、重複排除、終了・中止除外、料金不明、公式URL・出典・加工表示を維持。情報が不足するイベントを注目枠に出さない。
4. 依存パッケージを極力増やさず、既存`localguide/`に最小差分。CSVを有効にできない場合は、コードや設定を無理に増やさず、根拠付きの調査報告のみでよい。
5. 単体テストと`validate --site`で検証し、明石市の施設4件の表示を退行させない。推定値・架空イベントを公開データへ混入させない。
6. 利用できる実イベントデータを確保できなければ、加古川・明石・姫路の**別の公式RSS/CSV/公開フィード**を次候補として調べ、根拠・取得条件・鮮度を示す。ただし無断スクレイピングへ切り替えない。

## 納品
- 調査内容と公式根拠を`planning/source-audit.md`に追記。
- 審査できた設定・コード・テストだけを変更し、Pull Requestを作成。**mainへの自動マージはしない**。
- 実レコード件数、現在以降のイベント件数、テスト結果、利用許諾の確信度、未解決事項をPR本文に明記。
- `noranamani-gadget-deals`、GitHub Pages設定、Oracle cron、ChatGPT定期タスク、Search Console、note投稿はいずれも変更しない。
