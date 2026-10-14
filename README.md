# noranamani LOCAL GUIDE（仮称）

加古川・明石・姫路を中心とした家族向け地域情報自動メディア。

## 方針
- **メイン**: 地域イベント、無料・低価格のお出かけ、屋内遊び、商業施設、特売・セール、新店・閉店、直売所
- **サブ**: 加古川発・家族4〜6人向けの旅行モデルコースと宿泊施設比較
- **基盤**: Oracle Cloud Always Free / GitHub / GitHub Pages / Python / 既存ChatGPT契約内の編集タスク
- **追加費用目標**: 0円/月（既存契約料は除く）
- 既存の noranamani/noranamani-gadget-deals は変更しない。

## 現在の段階
このリポジトリは Phase 0（情報源・データ設計）から Phase 1（最小構成）への準備中です。
**自動収集・毎朝の実行・公開サイトは、まだ稼働していません。**
設定上の情報源はすべて無効化した状態から開始します。規約、robots.txt、再利用条件を確認するまでは有効化しません。

## 主なファイル
- AGENTS.md: Codexおよび自動処理が守るルール
- config/: 対象地域、カテゴリ、候補情報源、ページ公開条件
- data/: 空のイベント・施設・特売・新店データ
- planning/: 情報源審査、データ設計、旅行モジュール、チェックリスト
- codex/phase1-prompt.md: Codex向け実装指示
- scripts/: Pythonプログラム（Phase 1で追加）
- docs/: GitHub Pages公開物（Phase 1で追加）
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
- GitHub PagesとSearch Consoleは、公開物を生成し検証した後に設定する。

最初の作業は planning/phase1-checklist.md と codex/phase1-prompt.md を参照してください。
