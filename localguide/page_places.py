"""SEO qualification for verified facility listings, independent of event counts."""
from datetime import timedelta
from urllib.parse import urlsplit

from .core import parse_time


def qualified_places(places, policy):
    """Require multiple distinct, officially sourced venues and websites."""
    if len(places) < policy["min_places"]:
        return False
    primary = sum(any(s["is_primary"] for s in p["sources"]) for p in places)
    websites = {p["official_url"] for p in places}
    hosts = {urlsplit(p["official_url"]).hostname for p in places}
    return (primary >= policy["min_official_places"]
            and len({p["place_id"] for p in places}) == len(places)
            and len(websites) >= policy["min_places"]
            and len(hosts) >= policy["min_distinct_official_hosts"])


def sustained_listing(key, eligible, page_state, now, days):
    """Gate thin SEO pages until *consecutive* checks over the configured period.

    The state is persisted only after the static site validates; a failure cannot
    advance publication history.
    """
    if not eligible:
        page_state.pop(key, None)
        return False
    previous = page_state.get(key, {})
    first = previous.get("first_qualified_at", now.isoformat())
    first_at = parse_time(first)
    last_at = parse_time(previous.get("last_qualified_at", now.isoformat()))
    if first_at > now or last_at > now or now - last_at > timedelta(days=2):
        first_at = now
        first = now.isoformat()
    page_state[key] = {"first_qualified_at": first, "last_qualified_at": now.isoformat()}
    return now - first_at >= timedelta(days=days)
