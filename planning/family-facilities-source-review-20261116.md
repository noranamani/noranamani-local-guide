# 2026-11-16｜加古川・姫路 おでかけ施設6候補の確認

## 今回の整理

加古川市の3施設（**日岡山公園・加古川海洋文化センター・みとろの丘**）は、すでに `data/nearby_spots.json` の独立編集カードに存在するため、重複追加しない。加古川の場所の情報は既存の写真（AI生成のイメージ表示）と公式リンクを維持する。

姫路市の3施設（**姫路科学館・姫路市立水族館・姫路市立動物園**）は2026年11月16日に公式ウェブサイトの継続掲載を確認した。新しい写真や営業時間・入館料を複製せず、`data/nearby_facility_links.json` の**手動確認済み公式リンクだけ**を近場ガイドの後段に配置する。

| 施設 | 確認した一次情報 | 限定的に掲載する事実 | 掲載しないこと |
|---|---|---|---|
| 日岡山公園 | [公園公式](https://www.city.kakogawa.lg.jp/soshikikarasagasu/kensetsubu/koenryokuchika/toshikeikaku/park/45886.html) / [再整備工事](https://www.city.kakogawa.lg.jp/soshikikarasagasu/kensetsubu/koenryokuchika/toshikouenseibi/hiokayama_saiseibi/51277.html) | 既存の公園カードを維持。2026年12月下旬以降の工事予定は今後の運用確認が必要 | 工事箇所の実際の通行可否を推測しない |
| 加古川海洋文化センター | [施設公式](https://kakogawa-mcc.com/facility/) | 既存の屋内外の学び・遊び案内 | 最新の休館日・料金の推測 |
| みとろの丘 | [加古川市公式](https://www.city.kakogawa.lg.jp/soshikikarasagasu/chiikishinkobu/mitorofurutsupaku/1415852687342.html) | 既存の自然・屋内公園案内 | レストラン等の最新営業情報の推測 |
| 姫路科学館 | [姫路市公式](https://www.city.himeji.lg.jp/atom/) / [開館情報](https://www.city.himeji.lg.jp/atom/0000033835.html) | 科学展示・プラネタリウムがある | 最新の投影・料金・空席情報 |
| 姫路市立水族館 | [姫路市公式](https://www.city.himeji.lg.jp/aqua/) | 播磨の里地・里海の生物展示がある | 最新のイベントと料金の推測 |
| 姫路市立動物園 | [姫路市公式](https://www.city.himeji.lg.jp/dobutuen/) / [アクセス](https://www.city.himeji.lg.jp/dobutuen/0000007495.html) | 動物展示、**専用駐車場なし** | 駐車料金・入園料の推測 |

## 収集・掲載条件

- 姫路の3施設は**通常のテキストリンクだけ**。施設公式HTML・写真・ロゴ・長文は取得・転載しない。
- `config/sources.json`の取得許可状態を変更しない。**明石市CSVだけの日次取得を保持**し、施設数が4件から増えたと誤って記録しない。
- 施設別の料金・定休日・割引制度を無根拠に埋めず、最新情報を公式リンクで確認するよう促す。
- 新しいカードは `nearby.html` のみ。元の9件と10枚のイメージ画像、旅行記事、楽天広告、`noindex`を維持。
- 今後の自動収集拡大は、ライセンス・robots・取得回数等の別審査と所有者承認が必要。
