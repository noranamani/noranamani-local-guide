# 「はりまよりみち」追加データ源の再審査（2026-10-19）

## 方針と結論
民間イベント媒体への問い合わせ回答がない期間も、既存の承認済みCSV日次更新と、当サイト独自の常設「近場のよりみち」記事を継続する。**この調査では新しい自動収集元を有効化しない。** 一般HTMLページ、CSVの二次利用条件、APIアクセス登録を混同しない。

## 公式候補1：加古川市「都市公園」

- データセット： https://opendata-api-kakogawa.jp/ckan/dataset/urbanpark
- CSVリソース： https://opendata-api-kakogawa.jp/ckan/dataset/urbanpark/resource/6213c4ba-c8c4-4831-8244-9f092cfa3e92
- CKAN表示：CSV、ライセンス「クリエイティブ・コモンズ 表示」、認証方式なし（`auth type: none`）、最終更新は **2024-03-22**。
- 留意：カタログにデータが残ることは、2026年時点の全公園の開放状態・遊具・駐車場・有料条件の保証ではない。CSVは古く、公園一覧を現行情報として自動大量掲載しない。
- 本番採用：**保留**。公式CSV本文を取得し、ID・列・文字コード・URL欄・一般公開施設との対応を審査。適合しないレコードは除外。新規リンク先・改修状況を公式ページで再照合する。

## 公式候補2：加古川市「赤ちゃんの駅」

- データセット： https://opendata-api-kakogawa.jp/ckan/dataset/babystation
- CSVリソース： https://opendata-api-kakogawa.jp/ckan/dataset/babystation/resource/22145b82-be62-4d26-829a-ac3bf472f625
- CKAN表示：CSV/JSON、ライセンス「クリエイティブ・コモンズ 表示」、CSV更新 **2025-08-21**。
- 用途：授乳スペース、おむつ交換台、ベビーチェア付個室トイレのいずれかを備え、乳幼児と保護者が利用できる支援拠点。**公園・遊び場ではない**。
- 本番採用：**独立カテゴリ候補として保留**。名称・所在地・利用設備の種類、確認日、公式詳細URL、登録状況をCSVと市公式案内で再確認。現行 `places_csv` アダプターに無条件投入しない。

## 自動取得・二次利用の追加審査
- 加古川市オープンデータは、一般Webページの著作権条件と異なるCC BY系ライセンスが表示される。表示・改変の明示など個別条件に従う。出典: https://www.city.kakogawa.lg.jp/shiseijoho/kakogawashinoseisakuzaisei/keikaku/ict/46170.html
- 「データはCC BY」でも「APIは登録なしで自由にクロール可能」とは判断しない。匿名の公開CSV直接ダウンロードに申請が必要か、運用時のアクセス頻度制限・robots・利用規約を確認する。
- 公開予定の新機能は `data/nearby_spots.json` の5件の独自編集・手動確認済みリンクであり、この2種のCSVの機械収集とは独立。画像・第三者本文の転載なし。
- `config/sources.json` の新候補は引き続き `enabled=false`、`data/places.json` の明石市4施設・イベント0件を維持。公式採用・追加取得・SEO解除は別PRと承認を必要とする。

## 調査後の次アクション
1. まず常設ページを生成し、PC/スマホ表示、公式5リンク、安全性を検証する。
2. 別PRで「都市公園」CSVを**一度だけ**安全に検査し、掲載適格な現役施設とその公式URLを抽出できるか判定。申請が必要なら停止。
3. 赤ちゃんの駅は乳幼児向けの利用設備を案内する別の導線として設計し、混ぜない。
4. 民間媒体の返信が届いたら審査台帳に記録し、許可された情報源のみ段階的に追加する。

確認根拠：上記の加古川市・CKAN公式カタログの公開ページ（2026-10-19時点）。CSVの本文・件数・HTTPダウンロードの実行結果は本書では未検証。

## 2026-10-19追記：都市公園CSVを一括取得しない代替手段の確定

加古川市の一般サイト「公園情報一覧」と「市内の主な公園紹介」には、所在地・主な施設の説明・公園固有の公式ページが既に用意されている。

- 公式公園情報一覧：https://www.city.kakogawa.lg.jp/soshikikarasagasu/kensetsubu/koenryokuchika/toshikeikaku/park/index.html
- 市内の主な公園紹介：https://www.city.kakogawa.lg.jp/soshikikarasagasu/kensetsubu/koenryokuchika/kakogawashinoshisetsu/kouensyoukai/1452043839154.html
- 権現総合公園（2026-05-08更新）：https://www.city.kakogawa.lg.jp/soshikikarasagasu/kensetsubu/koenryokuchika/news/46090.html
- みとろの丘（加古川市の施設案内）：https://www.city.kakogawa.lg.jp/soshikikarasagasu/chiikishinkobu/mitorofurutsupaku/1415852687342.html

**採用した方法：** 通常のウェブ検索・個別参照で確認した施設の名称・特徴・公式URLから、当サイトが独自に短い紹介文を編集する。写真・記事本文を転載せず、現況や料金を未検証のまま断定しない。CSVやNGSI APIの自動取得・巡回は不要。この方法は都市公園CSVの利用申請や、回答待ちの民間RSS許可に依存しない。

**API規約の注意：** https://opendata-api-kakogawa.jp/odp/tos/ はAPI機能を登録利用者に限定している。 https://opendata-api-kakogawa.jp/odp/api%E3%81%AE%E5%88%A9%E7%94%A8%E3%81%AB%E3%81%A4%E3%81%84%E3%81%A6-2/ には利用申請が必要と記載されている。「CSVのCC BY表示」をもってAPI利用・自動ダウンロードの登録免除とは扱わない。今回、CSV本文の自動ダウンロードは実行していない。

### 公開候補として手動確認した4施設（既存5件とは別）

| 施設名 | 公的・運営者の案内 | 紹介の根拠と注意 |
|---|---|---|
| 権現総合公園 | https://www.city.kakogawa.lg.jp/soshikikarasagasu/kensetsubu/koenryokuchika/news/46090.html | 大型遊具、幼児用遊具、散策道。一般駐車場と高速側の利用時間・立入区分に注意 |
| みとろの丘 | https://www.city.kakogawa.lg.jp/soshikikarasagasu/chiikishinkobu/mitorofurutsupaku/1415852687342.html | 芝の遊び場と屋内グラスハウス。施設別営業日・隣接観光果樹園との区別が必要 |
| 鶴林寺公園 | https://www.city.kakogawa.lg.jp/soshikikarasagasu/kensetsubu/koenryokuchika/toshikeikaku/park/45661.html | 公園として市公園一覧に存在。芝生・蒸気機関車展示の記述は「市内の主な公園紹介」を参照。寺院拝観条件とは区別 |
| 志方東公園 | https://www.city.kakogawa.lg.jp/soshikikarasagasu/kensetsubu/koenryokuchika/toshikeikaku/park/45740.html | 公園として市公園一覧に存在。芝生広場は「市内の主な公園紹介」にて確認。運動施設は別利用条件 |

加えて旧来の石ケ谷公園リンクを、明石市の紹介ページから参照可能な指定管理者の園内案内 https://e-akashi.jp/isi-park/ に更新。加古川海洋文化センターは加古川市自身の施設案内 https://www.city.kakogawa.lg.jp/shiseijoho/kakogawashinoshisetsu/kyoiku_bunkashisetsu/1416287804503.html を利用する。

**除外判断：** 加古川河川敷緑地は散策候補として魅力的だが、2026年にも河原地区の工事・駐車場の利用制限が公表されているため、変動する現地状況を常設記事で簡単に保証できない。今回は新規カードを作らない。

**公開・ビルド経路：** コード管理下の `docs/` は過去のビルドスナップショットのみ。Cloudflare Pagesは `python3 -m pip install -r requirements.txt && python3 -m scripts.cloudflare_build` により、デプロイ時に最新のPython生成元とJSONから `docs/` を再生成する設定として案内済み。GitHubにコミットされた `docs/nearby.html` が存在しないことは、本番Cloudflareに当該ページが存在しない証拠にはならない。実際の本番デプロイ成功はCloudflareのProduction deployment結果、公開URL、noindexヘッダーで別途検証する。
