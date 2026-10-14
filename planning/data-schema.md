# データ構造設計（Phase 0）

## 種類
- events: event_id, title, municipality, place_id, location_label, category_ids, occurrences, age_info, indoor_outdoor, price_type, price_description, reservation_required, sources, first_seen_at, last_verified_at, status
- places: place_id, name, municipality, address, indoor_outdoor, admission, official_url, sources, last_verified_at
- offers: offer_id, title, municipality, valid_from, valid_until, eligibility, source_url, last_verified_at
- store_news: news_id, venue_id, event_type, announced_at, effective_date, verification_status, source_url

## events設計
- occurrences は occurrence_id, start_at, end_at, timezone, status を持つ配列。
- sources は source_id, url, source_event_id, fetched_at, last_checked_at, source_published_at, is_primary を持つ配列。
- 日時はISO8601、タイムゾーン Asia/Tokyo を明記。日時不明の場合はnull。
- price_type は free / paid / conditional / unknown。屋内外は indoor / outdoor / mixed / unknown。
- status は scheduled / cancelled / postponed / ended / unconfirmed。
- イベントIDと開催回IDを分け、複数日・午前午後・毎週開催を混同しない。
- Phase 1実装のJSON Schemaはschemas/に配置。start_at/end_atは日付のみも保持でき、時刻は創作しない。
- organizer_labelは確認済みの主催者名（不明はnull）。地域・カテゴリ一覧の主催者数に使用する。
- review_hold=trueのイベントは手動確認が終わるまで非公開。通常の再取得で解除しない。
- 取得状態はdata/source_state.json、レビュー候補と一覧の継続確認状態は非公開のcache/に記録する。

## 重複排除
1. 同一ソースのイベントID一致なら同一候補。
2. 別ソースでは日時・場所を必須の一致条件として、タイトルをNFKC、記号、空白で正規化。
3. タイトルだけ似ていて開催日または場所が異なるものは自動統合しない。
4. 曖昧な候補はレビュー待ちとして保存し、勝手に統合しない。
5. 複数の情報源を紐づけ、出典と属性ごとの更新日時を保持する。

## 終了・中止
- 終了した単発開催回は今週末・トップページから除外。
- 複数開催は将来の開催回だけ残す。
- 一覧から消えた、または取得失敗しただけでは中止と判定しない。
- last_verified_atが古ければ注目枠から外すなど安全側に倒す。

## 旅行サブカテゴリ
- 加古川発、4〜6人での移動・宿泊・観光を想定。
- 宿泊料金を表示するなら宿泊日・年齢・人数・部屋・食事・検索日時をセットで記録する。
- 料金を取得できなければ要確認と記載する。概算料金は見積条件を明記。
- 個人の自宅住所は公開データに一切保存しない。
