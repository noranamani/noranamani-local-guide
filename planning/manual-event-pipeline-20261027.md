# はりまよりみち｜公式イベント案内と人手承認型の掲載（2026-10-27）

## 対象と公開状態

- [Issue #41](https://github.com/noranamani/noranamani-local-guide/issues/41)。**未許諾の民間RSS/HTML自動取得は行わない**。
- 第1段階：`data/official_event_links.json` の公開元への通常リンク6件を `event-finder.html` に表示。確認日は2026-10-27。外部サイトを静的ビルド時に読むことはない。
- 第2段階：Googleアラート、地域メディアなどで人が見つけた**URLだけ**をローカル `cache/event_candidates.json` に登録。Git管理外・非公開、原文/画像/メール本文を保存しない。
- 第3段階：確認済みイベントは `data/curated_events.json` に記録し、GitHub PRで掲載可否を承認したものだけ表示。毎日00:20 JST（GitHub Actionsの実行遅延あり）に開催終了・情報の鮮度切れをチェックし、必要なときだけ `review_state` を非公開状態に移行させてmainにpush。**実際の掲載内容の再確認・日時延長・自動取得はしない**。
- 全ページ `noindex` のまま。検索登録の判断は別作業。楽天旅行記事、広告HTML、明石市CSV日次取得には変更しない。

## 公式リンクの取り扱い

`localguide/official_event_hub.py` は審査済みの公式ホスト・日付・URL・重複・危険なHTMLを検証。リンク先の文章・画像・個別イベントの開催日時は収集しない。URL以外は当サイト独自の短い説明文。リンク先で開催日・条件を確認するよう明示する。自治体・主催者の案内が変わったときは手作業で確認し、PRで `reviewed_on` とURLを更新する。

## 候補URLを登録する（ローカルPC、外部通信なし）

```sh
python -m scripts.event_candidates add --url https://www.city.himeji.lg.jp/...
python -m scripts.event_candidates add --file candidate_urls.txt
python -m scripts.event_candidates list
```

- URLは必ずhttps。別サイトのGoogleアラートやRSS新着URLも**候補として保存するだけ**で、そのまま掲載しない。
- `candidate_urls.txt` はURLのみ改行区切り。Googleアラートのメール本文をリポジトリにコミットしない。
- `cache/` は `.gitignore` により公開・Git管理から除外されている。キューはローカルのため別PCへ自動同期されない。
- キューで生成される16桁IDを `list` で確認。候補の識別IDはURLハッシュ。重複URLは二重登録しない。

## 人が主催者一次情報を確認して承認（PR作成前）

開催日・会場・主催者の正式URL・参加条件・中止情報を公式ページで確認し、明示的に `--owner-reviewed` を指定。民間メディアURLは候補のまま保持し、公開するのは別に確認した**主催者公式URL**のみ。現段階では審査済みの公的機関/公式運営者ホスト以外のリンクを掲載用データに指定すると失敗する。追加ホストは権利・安全性の審査とPRが必要。

```sh
python -m scripts.event_candidates approve \\
  --candidate-id <listで確認したID> \\
  --id local-event-20261101 \\
  --title "人手で確認した公式イベント名" \\
  --municipality "姫路市" \\
  --venue "確認済み会場" \\
  --start-on 2026-11-01 --end-on 2026-11-01 \\
  --official-url https://www.city.himeji.lg.jp/...... \\
  --checked-at 2026-10-27T09:00:00+09:00 \\
  --review-note "主催者の公式詳細ページを手動確認" --owner-reviewed
```

この操作はローカルの `data/curated_events.json` に情報を追記するだけで、公開やpushはしない。**記録の追加はまだ掲載許可ではなく**、専用ブランチPRで日時・条件・公式URLを人がレビューし、サイト所有者がmainへの反映を承認した後に公開される。未確認の料金・年齢・定員・無料条件を補完しない。初回の `items` は空なので、実際の個別イベントは0件。

## 日次の自動チェック

```sh
python -m scripts.event_lifecycle
python -m scripts.event_lifecycle --apply
python -m unittest discover -s tests -q
python -m scripts.cloudflare_build
python -m localguide validate --site
```

- `audit`に相当するオプション無し実行は読み取り専用。重複ID、重複公式URL、同一会場・同一日付・同一イベントの二重登録、悪意あるURL、未来の確認日時で失敗。
- `--apply` は `checked_at` が72時間以上前なら `needs_recheck`、`end_on` より後の日付なら `expired` に**一方向**で変更する。停止理由はデータから判定する。確認日時の自動延長、過去イベントの復活、イベント本文の自動更新は行わない。
- 静的サイト生成時にも必ず上記判定を行うため、たとえ日次ジョブが失敗しても期限切れ情報をビルドで復活させない。**すでに公開済みの静的HTMLはGitHub Pagesの再デプロイまで自動では書き換わらない**ため、定期ジョブが成功したことも確認する必要がある。
- GitHub Actionsは、テスト・オフラインビルド成功後、状態が変わった `data/curated_events.json` だけを通常push。変更なしならpushしない。競合時はforceしないで停止する。
- 明石市公式施設CSVの別ジョブは毎朝08:25 JST、こちらのjobは00:20 JSTと分離している。

## 本番承認前の品質確認

PRの `unittest` と `preview` が全成功し、PC 1440/768pxとスマホ390/320pxでトップ・`event-finder.html` のリンク・表示・横はみ出し・キーボード操作を確認する。新しい `event-finder.html` の `noindex` とサイト全体の `X-Robots-Tag: noindex`、楽天広告HTMLの不変を確認してから所有者承認によりマージする。
