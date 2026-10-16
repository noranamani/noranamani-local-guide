# はりまよりみち｜明石市公式施設CSVの毎朝更新・運用手順

作成日: 2026-10-16

## 対象と実行時刻

- GitHub Actions: [Refresh approved Akashi facility CSV](../.github/workflows/refresh-approved-places.yml)
- 毎朝 **08:25 JST** (UTC 23:25)、mainのワークフローで自動実行。GitHub側の遅延はあり得る。
- workflow_dispatch により手動確認も可能。ただし **同じ日本時間の日付で最大1回**。
- 唯一の情報源: akashi_open_data（審査済み明石市の観光施設CSV）。
- ほか27件の審査待ち情報源、RSS、HTML、旅行広告、note、ガジェット・ガチャのジョブには触れない。
- Python 3.12、標準依存とGitHub標準GITHUB_TOKENのみ。Cloudflare API鍵や追加の有料サーバーは不要。
- 公開更新は従来どおり Cloudflare Pages のmain連携が担当。直接デプロイしない。

## 成功時の動作

1. mainの現在の設定とデータをチェックアウト。
2. Pythonのオフライン単体テストを実行。
3. **一時ディレクトリ**に config/, data/, schemas/ を複製。
4. 審査状態、情報源URL・ID・形式・1日1回制限、データ構造を確認してからCSVにアクセス。
5. ETag / Last-Modified を使用。正常な304 Not Modified時も **実際に再検証したときだけ** 最終確認日時を更新。
6. 更新CSVの列・URL・重複ID・混在情報源・イベント参照・件数急減を検査。従来の半減防止に加えて **元の75%未満になった場合は手動確認**。
7. 一時領域の新スナップショットで、Cloudflare Pages向け生成・HTML・SEO・ローカルリンク・写真を検証。
8. **全検証成功時のみ** data/places.json と data/source_state.json をコミットしてmainに通常push。強制pushなし。
9. GitHub連携済みCloudflare Pagesが通常のmainデプロイを実施。noindexは維持。

## 失敗・保留時の動作

- 取得不可・CSV不正・検証不合格では **data/places.jsonを変更しない**。
- 通信を試みた場合は日次回数を消費するため、data/source_state.jsonに試行日・試行数・失敗状態だけ記録。「正常確認日時」を勝手に進めない。
- 401 / 403 / 429 では halted=true を保持して取得を停止。原因・利用許可の再審査は人手対応。
- 情報源の権利審査が30日超の場合は自動で日付を延長せず停止。安全制限を迂回しない。
- push競合、書込み権限不足、Cloudflareデプロイ不調はログから調査。成功したと決めつけない。
- 失敗時に最終確認日時を延長しないため、通常の再ビルドでは **72時間以上古い施設が掲載除外される**。偽装して残すことはしない。

## 初回確認・7日間の試験運用

**初回**（2026-10-17朝の予定。GitHub cronには遅延・未実行の可能性あり）:
- リポジトリ → Actions → Refresh approved Akashi facility CSV
- 最新の実行が成功（緑）しているか。失敗ならログとJob summaryを確認。
- data/places.json の4施設の最終確認日時が更新されたか、data/source_state.json のattempt_dayが当日か。
- https://harima-yorimichi.pages.dev/places.html で新内容が表示されるか。旅行・写真・楽天広告への影響も確認。

**7日間**:
- 1日1回稼働、件数急減、データ欠損、意図しないソース追加、CI失敗を確認。
- 反映されない場合はmainのコミットとCloudflareの本番デプロイ履歴を照合。
- 情報源改廃、規約やrobots変更時は自動取得を停止して再審査。

## 情報源の再審査

現行 config/sources.json の akashi_open_data.checked_at は2026-10-14 17:00頃。**2026-11-13までに**、公式CSVの提供、robots、商用再利用、ライセンス、出典表示を人手で再審査する（30日以内）。再審査の完了後にchecked_atと監査記録を更新する。

日付の自動延長、別ソースへの無断切替、HTMLスクレイピングへのフォールバックは禁止。

## 手動実行

GitHub Actions画面で当ワークフローを開き、Run workflowでmainを選択して実行。同日すでに試行した場合は日次上限により新規取得を省略する。

失敗時はdata/source_state.jsonのlast_error・halted・last_attempt_atを確認。停止解除も人手の原因調査と権利再確認が必要。
