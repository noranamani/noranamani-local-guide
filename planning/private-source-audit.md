# Phase 1H: 公的機関以外の地域イベント情報源調査

調査日: 2026-10-14（JST）

## 結論
- まず情報源として有力なのは、**商業施設・住宅展示場の主催者自身が掲載するイベントページ**。
- 地域メディアのRSSは、**新着記事の発見用**として有望。2026-10-14に実際に取得できたRSSは3本。
- RSSが読めること、robots.txtが該当URLへのアクセスを許すこと、Google検索に載っていることは、**記事の転載・有料広告サイトでの再利用の許可ではない**。
- 現状ではどの民間候補も本番用`enabled=false`。無許諾収集/再掲載をしていない。

## RSS one-shotメタデータ監査

実行元: GitHub Actions、[調査ログ](https://github.com/noranamani/noranamani-local-guide/actions/runs/38549377977)。

対象は次の4サイトのみ。各サイトでrobots.txtを確認し、パーサーが読めるか/何件あるか/公開日時を抽出。記事本文・画像・URL一覧・個別タイトルは保存/ログ公開せず、件数等の集計だけ記録した。

| 地域メディア | フィード | 実測結果 | 最新公開日（開催日ではない） | 権利 |
|---|---|---|---|---|
| かこがわノート | https://kakogawa-note.com/feed/ | RSS2.0 / 10件 / タイトル語句4件 | 2026-10-13 | 再利用未審査 |
| 明石じゃーなる | https://akashi-journal.com/feed/ | RSS2.0 / 10件 / タイトル語句1件 | 2026-10-14 | 再利用未審査 |
| 加古川のこと | https://harimania.com/feed/ | RSS2.0 / 10件 / タイトル語句5件 | 2026-10-14 | 再利用未審査 |
| 姫路の種 | https://budou-chan.jp/feed/ | Content-Typeはapplication/rss+xml、今回の保守的なXMLパーサーで解析不可 | 未確認 | 記事・写真の無断転載禁止 |

- 4件ともrobots.txtを取得でき、検査用User-Agentによる該当フィードの確認は許可と判定された。
- 姫路の種はRSSに見えるContent-Typeが返るが、XMLとして解析できたとは判定しない。無断転載禁止：https://budou-chan.jp/contact/privacy-policy/
- RSSの公開日時はイベント開催日ではない。本文転載・画像のホットリンクは不要。
- ワークフローは初回調査後、**自動PRトリガーを削除して手動実行限定**に変更。今後勝手に巡回しない。

## 2026年10月の民間主催者による将来イベント確認

| 主催者/会場 | 公式URL | 日程・主題例（開催前に再確認） | データ品質 | 取得・再利用 |
|---|---|---|---|---|
| アリオ加古川 | https://kakogawa.ario.jp/event/ | 10/17キャラクター撮影企画、10/24ハロウィン | 日付・カテゴリ・会場など詳細あり | 無許諾転載不可。https://kakogawa.ario.jp/privacy/ |
| ニッケパークタウン | https://nikke-parktown.com/shop/event/eventnews.jsp | 10/17雪遊び企画、10/31ハロウィン | カレンダー・個別ページ・無料/整理券条件 | RSS/API不明・再掲載未承認 |
| ABCハウジング加古川 | https://abc-housing.asahi.co.jp/kinki/campaign/kakogawa/ | 10/17ワークショップ等、10/18無料観覧ショー | 日付・対象・枠数・参加条件あり | 無許諾のコンテンツ複製不可。https://abc-housing.asahi.co.jp/infouse.html |
| イオン明石 | https://www.aeon.jp/sc/akashi/event/ | 10/17キッズマルシェ、10/18工作 | 日付・時間・場所あり | RSS/API、再利用条件未審査 |
| アスピア明石 | https://www.aspia-akashi.com/event/index | 10/24赤ちゃんハイハイレース | 日付・対象・予約・無料など | 無許諾複製/二次利用不可。https://www.aspia-akashi.com/sitepolicy |
| イオンモール姫路大津 | https://www.aeon.jp/sc/himejiootsu/event/index.html | 10月の催事・ハロウィンなど | 日付・会場あり | RSS/API、再利用条件未審査 |

現場の「無料」と「誰でも予約なしで参加可能」は別。会員登録・アンケート・先着整理券・対象年齢・参加枠などを項目別に正規化しなければ誤案内になる。

## 著作権とメディア連携
- アリオ加古川: https://kakogawa.ario.jp/privacy/ 私的利用以外の無断転載を控える旨。
- ABCハウジング: https://abc-housing.asahi.co.jp/infouse.html 無許諾のコンテンツ複製不可。外部リンクは原則自由と記載。
- アスピア明石: https://www.aspia-akashi.com/sitepolicy 無許諾のデジタル素材の複製・二次利用禁止。
- Kiss PRESS: https://kisspress.jp/copyright/ 記事・写真等の利用は原則事前許諾。
- 姫路の種: https://budou-chan.jp/contact/privacy-policy/ 記事・写真の無断転載禁止。
- いこーよ: https://iko-yo.net/terms/service 機械取得・転用に関する制限があり、主な自動データ元にしない。

## 推奨する2層モデル
1. **発見キュー:** 3本の民間RSSは利用条件を確認した後に、新着URLの検知だけの用途を検討する。イベント/開店/閉店の候補は確認待ちで保存。RSS本文や写真を公開ページへ直接出さない。
2. **一次情報の検証・掲載:** 主催者や施設の公式ページで開催日、場所、料金、対象、要予約、公式URL、開催中止を項目別に確認。機械的収集と事実の再掲載の条件は施設別に確認し、許可が得られない場合は人手確認・問い合わせに留める。
3. **主催者投稿:** イベント主催者自身に日時・会場・条件・公式URLを送ってもらう申請フォームを検討。事実データの掲載許可をフォームで明示して受ける。投稿には人手審査を入れ、権利を持たない画像を無断掲載させない。

## 次に必要な作業
- アリオ加古川、ABCハウジング加古川、ニッケパークタウン等へ「日程・会場・公式URLなどの事実項目に限り1日1回収集してリンク付き掲載可か」を問い合わせる。リンクするだけの場合でも規約に従う。
- 民間RSS3本について「新着URLの内部検知と主催者公式ページへの紹介」に利用可能かを問い合わせる。許可不要との判断でも範囲を記録。
- 姫路の種のRSSはXML/配信形式の不整合を再調査（権利問題とは別）。
- 自動化の前に権利/robots/機密情報/リンク/開催日を再審査。現時点で新イベント掲載は0件。


## Phase 1I — 利用条件の確認とオフラインRSS発見キュー（2026-10-14）

### 根拠として確認した一次資料
- 文化庁: [著作物に当たらない単なる事実・データ](https://www.bunka.go.jp/seisaku/chosakuken/seidokaisetsu/chosakukensha_fumei/) は著作権許諾を要しないが、具体的な文面・画像・サイト利用条件は別途確認が必要。
- かこがわノート: [リンク方針](https://kakogawa-note.com/link/) で、個別記事リンク歓迎・連絡は基本不要。**これはRSS自動巡回や原文転載の許可ではない**。
- ABCハウジング: [サイト利用のご案内](https://abc-housing.asahi.co.jp/infouse.html) はリンク原則自由、著作権法の範囲を超える文章・写真等の無断複製は禁止。
- アスピア明石: [サイトポリシー](https://www.aspia-akashi.com/sitepolicy) でデジタル素材の複製/二次利用は禁止、トップページへのリンクは基本自由。個別イベントURLや自動機械取得については明示なし。
- Kiss PRESS: [コンテンツ二次利用](https://kisspress.jp/copyright/) に原則著作権者の許諾が必要と明記。
- 姫路の種: [注意事項](https://budou-chan.jp/contact/privacy-policy/) に記事と写真の無断加工・転載禁止。
- [文化庁のリンクに関する解説](https://www.bunka.go.jp/seisaku/bunkashingikai/chosakuken/hoki/h29_05/)も参照。通常のURLをリンクする行為と、記事の文章・写真・見出しなどを反復して再掲載する行為を区別する。後者は個別の著作権・利用条件等を確認する必要があるため、RSSタイトルを大量にコピーするアンテナ方式は採用しない。

### 技術・運用方針
- RSSのメタデータが読めたことと、第三者向けサイトでのRSS再配布・URLの自動定期取得許可は区別する。著作権対象外の**事実**を独自に記述・リンクする余地はあるが、アクセス方法の条件を別途審査する。
- `localguide/rss_discovery.py` はネットワークアクセスを**一切行わない**。手動で準備したRSS XMLを指定し、`rss_discovery_review_status=allowed`、利用条件・robots審査が許可済み、許可根拠URLと30日以内の審査日時が揃った場合だけ処理する。
- `cache/rss_discovery_queue.json` はGitで除外済み。記事リンク、情報源ID、RSS発行日、暫定分類だけ保管し、元記事タイトル/本文/画像は保存しない。すべて`review_state=needs_primary_confirmation`、`publishable=false`。これは公開用イベントデータとは分離。
- 発見キューにあるRSS発行日時は**イベント開催日ではない**。催事の日時・場所・料金・対象年齢・中止は主催者の公式ページから別途確認する。
- マニュアル起動用CLI:
  `python -m scripts.stage_approved_feed --source-id kakogawa_note_rss --xml-file /path/to/approved.xml`
  （現時点では審査未完了のため**意図的に失敗**する。許可を設定してから利用。）
- 将来の無料枠候補: [connpass API](https://help.connpass.com/api/) は個人・コミュニティ向けに審査申請後無料。企業・法人向けは有料。子連れ行事のカバー範囲とサイト運営主体の適格性を確認するまで導入しない。

**現状:** 民間RSS3件の読み取り確認のみ。再利用・内部定期巡回の許可は未確認。実イベント0件、公開設定変更なし。

## 2026-10-15 — 民間2サイトのリンク方針と機械取得許可の切り分け

**確認結果:** 2サイトともリンク設置に関する明示的な方針がある。ただし**自動収集・再掲載権まで認める根拠は見つかっていない**。本番取得は有効化しない。

| 情報源 | リンク | 自動収集と事実情報のサイト内掲載 | 複製 |
|---|---|---|---|
| かこがわノート | [公式リンク方針](https://kakogawa-note.com/link/)で個別記事へのリンク歓迎。リンク後の連絡は基本不要 | [公開RSS](https://kakogawa-note.com/feed/)は前回単発確認でRSS2.0読取成功。しかしリンク方針には日次の機械取得/広告掲載サイトへのRSS再利用の明示的許諾なし。内部新着URL検知だけでも利用条件を照会 | 記事本文・写真・見出しの無断複製・再配信の許諾を得たとは判断しない |
| ABCハウジング | [公式サイト利用のご案内](https://abc-housing.asahi.co.jp/infouse.html)でリンクは基本的に自由（名誉毀損・権利侵害等の例外あり） | [加古川住宅公園のイベント情報](https://abc-housing.asahi.co.jp/kinki/campaign/kakogawa/)を人が閲覧できる。HTMLの毎日の自動収集、事実項目の転載範囲、RSS/APIの提供は未確認 | サイト規約で文章・画像・写真・イラスト等の無断複製・利用を禁止 |

### 確認に使用した一次資料
- かこがわノート: https://kakogawa-note.com/link/ および問い合わせ https://kakogawa-note.com/contact/
- ABCハウジング: https://abc-housing.asahi.co.jp/infouse.html （ABCライフィズ株式会社、問い合わせ: ハウジング関西営業部 `kansai@abc-housing.co.jp`）
- ABCハウジングでは「観覧無料」のショーがあっても、他の催しには先着組数、小学生以下、会員アカウント、住まいのアンケート等の条件が付く。掲載時はイベント単位で確認し、無料観覧をすべての催事に広げない。
- かこがわノートの公式問い合わせページではABCハウジング加古川住宅公園を運営スポンサーと表示している。ただし、**媒体間の連携・スポンサー関係によって第三者である本サイトへ権利が移るものではない**。
- 2026-10-14の[地域RSS単発調査](https://github.com/noranamani/noranamani-local-guide/actions/runs/38549377977)では、かこがわノートのフィードを技術的に検査できた。robotsのアクセス可否と、著作物の転載許可/契約による利用許可は別物。

### 開発上の判断
1. `link_policy_status=allowed` を上記2情報源に記録。これは公式ページへ通常のハイパーリンクを設置する範囲の確認結果のみ。
2. **`terms_review_status`、`reuse_rights_status`、`robots_review_status`、`rss_discovery_review_status`、`enabled` は変更しない。** 本番の自動GETも内部キューへの自動投入も開始しない。
3. 記事の一部/タイトル/画像をそのまま掲載しない。日時・場所・料金・対象などの事実は、主催者一次情報を人手で確認し、独立した短い案内として扱う範囲を検討する。
4. 未確認の許諾は[民間情報源への確認依頼文](private-source-permission-requests.md)を使って個別に尋ねる。**送信・代理申請は未実施**。
