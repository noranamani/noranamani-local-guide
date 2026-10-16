# はりまよりみち｜ChatGPT × ローカルCodex 共同開発ルール

最終更新: 2026-10-16

この文書は、サイト所有者・ChatGPT・ローカルCodex・GitHub Actionsの作業境界と引き継ぎ方法を統一するためのものです。安全性・掲載条件については、最上位の [AGENTS.md](../AGENTS.md) と既存の監査台帳を優先します。矛盾があれば作業を停止し、所有者に確認してください。

## 1. 現在の運用状況（必ず最新のGitHubと照合）

- 対象リポジトリ: `noranamani/noranamani-local-guide`。ほかの `noranamani` リポジトリは対象外。
- 正本: GitHubの `main`。ローカルCodexの作業フォルダーは正本ではない。
- Cloudflare Pages本番: https://harima-yorimichi.pages.dev/ （`main`へのpushで通常は自動デプロイ）。
- 旅行記事: 淡路島のモデルコース／2026年の実旅行をもとにした山陰旅行記。Rakuten公式発行の手動広告HTMLが含まれる。
- `config/page_rules.json` の `site_url` は `null`、現段階は全ページ `noindex`。勝手に解除しない。
- 施設データ: 審査済み明石市観光施設CSVのみ有効。毎朝08:25 JSTの [専用更新ジョブ](../.github/workflows/refresh-approved-places.yml) は`main`の施設データと取得状態を書き換えることがある。その他のソースは無断有効化しない。
- 現行状態の確認先: [先行公開記録](soft-launch-2026-10-16.md)、[施設更新手順](facility-refresh-operations.md)。古いREADMEや初回公開前のメモは実行状況の証拠にしない。

## 2. 担当と責任

| 主体 | 主な担当 | しないこと |
| --- | --- | --- |
| サイト所有者 | 優先順位、素材・体験談の提供、権利・費用・公開を伴う重要な承認、最終表示確認 | 秘密鍵や私用データを公開リポジトリへ貼らない |
| ChatGPT（GitHub連携） | 要件整理、外部情報と根拠の確認、実装指示と受け入れ条件の設計、PR差分・CIのレビュー、公開後の確認 | Codexと同じブランチを黙って同時編集しない。CI未完了を成功扱いしない |
| ローカルCodex | 承認された範囲のコード・データ・テスト実装、ローカル実行、画面幅別表示確認、PRと引き継ぎ報告の作成 | `main`への直接push、無許可の本番公開・情報取得・設定変更をしない |
| GitHub Actions | 単体テスト、オフラインサイト生成と検証、許可済みCSVの日次更新 | PRのCIでネットワーク収集や本番公開をしない |
| Cloudflare Pages | `main`にマージされた静的サイトの本番配信 | CIやGitHubマージだけで公開反映を保証したとはみなさない |

ChatGPTとCodexに独立したリアルタイム作業同期はありません。**やり取りと作業状態の正本はGitHubのブランチ・PR・引き継ぎメモ**とし、ユーザーがPR URL等を伝えて橋渡ししてください。使用環境やコネクタにより、ChatGPTがローカルPCの変更を直接見ることはできません。

## 3. 標準手順

### A. ChatGPTと仕様を決める

1. 目的・対象ページ・やらないことを確認。
2. チケットまたは[作業依頼テンプレート](../codex/TASK_HANDOFF_TEMPLATE.md)に、根拠、受け入れ条件、公開影響、想定ファイル、テストを記載。
3. コンテンツの事実・施設情報・画像出典・アフィリエイトは、人手確認の範囲を明確にする。
4. 一度に着手する実装者を決める。**Codexが実装している間、ChatGPTは同じブランチを書き換えずレビューに徹する**。

### B. Codexは専用ブランチで実装

まず未コミットのローカル作業を確認し、既存の変更を上書きしない。作業開始時の典型例:

~~~sh
git status --short
git fetch origin main
git switch main
git pull --ff-only origin main
git switch -c codex/<topic>-YYYYMMDD
~~~

- `AGENTS.md`、本書、対象コード、テスト、該当する監査記録を読む。
- 既存ブランチ・未保存作業があれば、勝手に消したり強制リセットせず、所有者に状況を伝える。
- 原則、`localguide/`などの**生成元**を編集する。`docs/`のHTML/CSSはビルドで再生成されるため、手編集だけで対処しない。
- 実装範囲外のリファクタリングや大量生成は避ける。権利・費用・公開方針が変わるならいったん停止。
- PRを作成し、タイトル・概要・検証方法・スクリーンショット・確認が必要な点を報告。

### C. 必須のローカル検証（Python 3.12）

~~~sh
python -m unittest discover -s tests -q
python -m scripts.cloudflare_build
python -m localguide validate --site
~~~

- 基本はオフラインの検証コマンドを使う。`python -m localguide run`／`collect` は実ネットワーク収集を伴うため、通常のデザイン・記事作業では**実行しない**。
- HTML/CSS変更時: 1440px・768px・390px・320px等で改行、横はみ出し、画像・タイトル・リンク、キーボード操作を確認。
- 旅行記事: 実際に訪問した事実と提案を分け、宿泊条件・料金を創作しない。
- 楽天広告: `data/travel_guides.json` の公式生成 `source_html` は**原文のまま**。ラベル・href・属性・追跡パラメータを改変しない。PR表記、外部リンク、既存記事を確認。
- ページ生成のSEO設定: `noindex`、HTTPの `X-Robots-Tag`、1ページ1つの `h1` を維持。サイトマップやcanonical、解析タグの追加は別途承認。
- Cloudflare向けビルドは `docs/` のローカル成果物。CIで「プレビュー成功」と表示されても本番デプロイの成功とは異なる。

### D. PR → ChatGPTレビュー → 所有者承認 → マージ

1. Codexは変更ファイル、影響、再現手順、テスト結果、未検証箇所を[PRテンプレート](../.github/pull_request_template.md)に記録。
2. GitHub Actionsの **unittest** と **preview** が成功するまでマージしない。
3. ChatGPTはPRの最新コミットSHAと`main`の状態を照合して、差分・リンク・情報源・広告・SEO・秘密値・スマホ表示とCIを確認。不明点は未確認と書く。
4. **`main`へのマージは通常Cloudflare本番公開を誘発する。** 実装承認だけでなく、本番反映の対象・タイミングを所有者と合意する。すでに当該作業で明示的に本番反映を依頼されている場合は、チェック成功を条件に進めてよい。
5. マージ直前に`main`が更新されていた場合（毎朝のCSVジョブ等）、差分を取り込み、必要なら再テスト。`git push --force`／チェック回避は禁止。
6. マージ後: コミットSHA、PR、CI URL、実際のCloudflare表示・更新日時を報告。**本番URLが未確認なら「公開未確認」と明記**。
7. 問題が出た場合: まず影響を確認して、前回の正常版への切戻しPR／`git revert`を検討。秘密情報の露出時は別途迅速に対処。

### E. 次のチャット・Codexセッションに引き継ぐ

作業が複数セッションになる場合、[作業依頼テンプレート](../codex/TASK_HANDOFF_TEMPLATE.md)をコピーし、状況を記録する。主に次の情報が必要:

- 対象リポジトリ、最新`main`、作業ブランチとSHA、PR・GitHub Actions URL。
- 目的・受け入れ条件・やらないこと、変更したファイル、採用した設計と理由。
- **終わったこと／未完了／今すぐやる1手**を分けて記載。
- コマンドの実行結果、PC／スマホの画面確認、生成物の参照位置。
- 素材の保管場所と権利、未解決の許諾・必要なユーザー確認。
- 公開状態（未PR／CI待ち／PRレビュー中／マージ済み／Cloudflare確認済み）を正確に書く。

大きな作業は`planning/handoffs/YYYY-MM-DD-topic.md`などに記録してPRに含める。小さな作業はPR本文で十分。前セッションのローカル画像やZIPは次のセッションに存在すると仮定しない。再アップロードまたはGitHubへ適切に保存する。

## 4. 作業を止めて所有者に確認する条件

次はCodexもChatGPTも、明示的な決定なしに進めない:

- 情報源の `enabled` 変更、ロボット規則・利用許諾の再解釈、無許可のスクレイピング、APIキー利用。
- `noindex`解除、Search Console/AdSense/解析サービスの新規導入、広告・アフィリエイトの差替え。
- URLの移行、Cloudflare/ドメイン設定、課金・秘密値、外部への送信、既存の定期ジョブの大幅変更。
- 公開済み記事の訪問事実・料金・宿泊条件の確証のない編集、第三者の文章・画像の転用。
- `main`に他作業が入り競合した場合、テスト不合格、PR差分を本人が十分確認できない場合。

## 5. ローカルCodexへの最初の依頼文（再利用）

以下をCodexに渡し、具体的な依頼書のリンクを追記する:

> noranamani/noranamani-local-guide の共同開発を開始してください。最初に AGENTS.md と planning/LOCAL_CODEX_CHATGPT_WORKFLOW.md、codex/TASK_HANDOFF_TEMPLATE.md を読み、最新 main と git status を確認してください。ユーザーが指定した作業だけを専用ブランチで実装し、Python 3.12のunittest／Cloudflare向けオフラインビルド／サイト検証を実行してください。mainへ直接pushせず、PRを作り、変更点・検証・未確認点・handoffを報告してください。未承認の情報源、楽天HTMLの改変、noindex解除、課金、秘密情報、他リポジトリへの作業は禁止します。

この文書を読むだけでは、新しいスケジュール、外部公開、Codexの自動起動は発生しません。
