# はりまよりみち：民間イベント案内リンクとGoogleアラート通知URL取り込み
更新: 2026-10-27（JST）｜Issue #45

## 何を公開するか
`official-events.html` には、**公的機関等の公式イベント案内11件**と別に「**地域の民間イベント情報サイト**」セクションを置きます。

| 対象 | リンク先 | リンク方針 |
|---|---|---|
| かこがわノート | https://kakogawa-note.com/category/event/ | https://kakogawa-note.com/link/ |
| ABCハウジング 加古川住宅公園 | https://abc-housing.asahi.co.jp/kinki/campaign/kakogawa/ | https://abc-housing.asahi.co.jp/infouse.html |

- **テキストリンクのみ**で、両サイトの文章・画像・記事写真・サムネイル・OGP画像・RSS見出しや抜粋を掲載しない。
- 自治体の案内と区別する。「提携」「協力」「主催」「公式掲載」の誤認を招く表現はしない。
- 各サイトのリンク利用条件を確認（2026-10-27）。リンク方針はプログラムによる**自動巡回の許可ではない**。定期スクレイピング等の外部アクセスは実装しない。
- 新しい個別イベントが0件でも、読者はリンク先から探せる。掲載日、料金、対象年齢、予約、住まいのアンケートの要否などはリンク先の主催者情報で確認する。
- データ源は `data/community_event_sources.json`、バリデータは `localguide/community_event_sources.py`。新しい民間サイト・ドメイン・リンクポリシーの変更は**別PRで再審査**する。

## 通知URLを安全に取り込む（オフライン）
候補は自動公開しません。**保存済みGoogle Alertsメールの `.eml` ファイル**または**ダウンロード済みRSS/Atomファイル**の中から、審査対象ホストのHTTPS URLだけを抽出し、既存の非公開キューへ記録する機能を追加しています。

**重要：本機能はGmailにログインしません。外部サイトを見ません。RSSをネットワーク取得しません。** Gmail/Google AlertsとGitHubの連携や、無人の受信自動監視はまだ設定されていません。エクスポート済みファイルがある場合にローカルで自動処理できる機能です。

### 使い方（ローカルCodex / Windows PowerShell）
```powershell
# リポジトリのルートで実施（Python 3.12）
New-Item -ItemType Directory -Force -Path cache/event-alert-inbox | Out-Null

# GmailでGoogle Alertsメールを選び「メッセージをダウンロード」等で
# .emlを保存。Google Alerts RSSならローカルにXML/RSSとして保存。
# **必ず cache/event-alert-inbox の中に保存**
python -m scripts.import_alert_urls --inbox cache/event-alert-inbox --dry-run
python -m scripts.import_alert_urls --inbox cache/event-alert-inbox
python -m scripts.event_candidates list
```

単一ファイルの投入例：
```powershell
python -m scripts.import_alert_urls --file cache/event-alert-inbox/alert.eml
```

- `.eml`ではHTML中のリンク先URLだけを処理（添付ファイル・メール本文・画像や記事の文章を保持しない）。
- Googleの `https://www.google.com/url?url=...` 形式なら**URLだけ安全に抽出**する。Google Alertsの管理・解除・追跡リンクは保存しない。
- `.rss` / `.xml` / `.atom`は保存済みRSS/Atomの各 `item/entry` のリンクURLだけを処理。**GoogleのアラートフィードURL自体は個人向けの識別情報を含み得る**ため、公開リポジトリに含めない。
- 許可ホストは `kakogawa-note.com`、`abc-housing.asahi.co.jp`、既存の審査済み公的公式ホスト群のみ。新しいホストはコードレビューが必要。
- `utm_`等のマーケティング用クエリを除いて同一URLを重複排除。`https`以外、個人情報や秘密を含み得るクエリ、未審査ホストは排除。
- 入力1ファイルは最大512KiB、処理は最大50ファイル/100URL。入力ファイルのHTML/RSSは保管しない。エラーがあればキュー変更前に停止。
- 非公開キュー `cache/event_candidates.json` はgitignored。**未承認の候補URL・メール本文をGitにコミットしない**。保存済みEML/RSS原本も処理後に利用者が削除してください。
- すでに入っているURLを再処理しても二重登録せず、追加は0件。**処理件数だけをコンソールに表示**し、メール中の個人情報はログへ出さない。

## 自動化の範囲と残作業
- 手動で通知ファイルをエクスポートすれば、`--inbox`で複数の通知URLを一括抽出・重複除去できます。
- Windowsタスクスケジューラから上記コマンドを呼ぶことはできますが、**通知ファイルそのものを自動取得する仕組みは未実装**。現状で定期実行を設定しても、新しいEML/XMLファイルが補充されなければ候補は増えません。
- Google Alertsの配信先（Gmail受信かRSS）や、Gmail連携の認証方法・秘密値の安全な管理方法を確定したら、将来は**権限・運用審査を経た別PR**で無人化を検討。
- 受信URLはあくまで**候補**。主催者一次情報を人が確認し `scripts.event_candidates approve` を明示実行、その後掲載PRのレビューと所有者承認がない限り本番表示されない。72時間の鮮度制限は維持。

## 確認
```sh
python -m unittest discover -s tests -q
python -m scripts.cloudflare_build
python -m localguide validate --site
```

必須レビュー：`official-events.html`で公的11件と民間2件が区分表示、noindex・個別イベント0件維持、既存楽天広告原文不変、明石市CSV定期更新を変更していないこと。320/390/768/1440pxのプレビュー表示確認。Cloudflare本番反映はPRレビュー・所有者承認後。
