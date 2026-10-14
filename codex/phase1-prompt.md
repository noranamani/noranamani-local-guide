# Codexへの依頼 — noranamani LOCAL GUIDE Phase 1

新リポジトリ noranamani/noranamani-local-guide の Phase 1 を実装してください。
着手前に AGENTS.md、planning/phase1-checklist.md、planning/source-audit.md、planning/data-schema.md、config/sources.json を必ず読んでください。

## 目的
加古川・明石・姫路周辺の家族向け地域イベントと無料・低価格のお出かけ情報を、
Oracle Always Free、Python、GitHub Pagesで1日1回更新できる静的サイトにする。

## 依頼
1. 公式サイトの正規URL、RSS/API/CSV、利用規約、robots.txt、再利用条件を丁寧に調査する。
2. 検証結果と参照URLをplanning/source-audit.md、config/sources.jsonに記録する。
3. 許可・ライセンスが確認できた情報源だけで、最小の取得アダプターを実装する。確認できない場合はenabled=falseを維持する。
4. 日時・開催回・会場・料金・出典の正規化、重複検出、終了イベント除外、キャンセル、取得失敗時処理を作成する。
5. 上記に対しオフライン単体テストを追加する。
6. docs/に日本語・スマートフォン優先の静的HTMLを生成する。イベント0件でも虚偽の掲載をしない。
7. title、meta description、canonical、sitemap、robotsを正しいURLが確定した場合に出力する。
8. validateで機密情報、文字化け、HTML、薄いページ、ソース欠落、日時不整合をチェックする。
9. 実装後にテスト・ビルドを実行し、変更ファイル・成功/失敗・未確認の情報源・必要な人手作業を報告する。

## 制約
- noranamani-gadget-deals は一切変更しない。
- 利用条件が未確認のHTMLを自動取得しない。ログインや制限を迂回しない。
- 公式サイトにない金額・開催日時・対象年齢を推測しない。
- 仮のサンプルデータと実データを混在しない。
- GitHub Pages設定変更、Oracle cron設定、実運用公開、有料API契約は指示があるまで実施しない。
- 旅行記事・note自動投稿は現段階で実装せず、後から連携できる設計に留める。
- 外部接続制限等で確認できない部分は、未確認として報告する。
