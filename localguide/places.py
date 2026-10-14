"""Conservative replacement of a reviewed facility CSV snapshot.

The CSV is an authoritative snapshot for *one source*, not for all places.
Rows absent from a successful, validated refresh must not live forever.
"""
from copy import deepcopy

from .core import GuideError


def replace_places(existing, incoming, source_id):
    """Return a new list with one source's places replaced, never altering inputs.

    Mixed-provenance records and identifier collisions require manual review;
    replacing them would otherwise erase another provider's evidence.
    The caller performs its own drop-rate guard and schema validation before
    atomically committing this result.
    """
    retained = []
    incoming_ids = set()
    for place in incoming:
        place_id = place["place_id"]
        sources = place["sources"]
        if (not place_id or place_id in incoming_ids or len(sources) != 1
                or sources[0]["source_id"] != source_id):
            raise GuideError("施設CSVのIDまたは情報源が不正です。更新を停止します")
        incoming_ids.add(place_id)

    retained_ids = set()
    for place in existing:
        from_this_source = any(s["source_id"] == source_id for s in place["sources"])
        if from_this_source:
            if len(place["sources"]) != 1:
                raise GuideError("複数情報源が紐づく施設は自動置換せず確認してください")
            continue
        if place["place_id"] in incoming_ids or place["place_id"] in retained_ids:
            raise GuideError("施設IDの衝突または重複があるため更新を停止します")
        retained_ids.add(place["place_id"])
        retained.append(deepcopy(place))
    return retained + deepcopy(incoming)


def ensure_event_place_references(places, events):
    """Reject a refresh that would orphan any event's place reference."""
    place_ids = {place["place_id"] for place in places}
    if any(event.get("place_id") and event["place_id"] not in place_ids for event in events):
        raise GuideError("イベントから参照される施設がCSV更新で消失します。手動確認が必要です")
