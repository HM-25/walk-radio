"""Wikipedia intros, used to ground the stories so the small model doesn't invent history."""
import time

import requests

from . import USER_AGENT, cache

MIN_EXTRACT_CHARS = 150  # shorter than this isn't enough to build a story on
POLITE_DELAY_S = 1.0     # Wikimedia 429s fast without this

_session = requests.Session()
_session.headers["User-Agent"] = USER_AGENT


def _split_tag(tag: str) -> tuple[str, str]:
    """OSM wikipedia tag is 'lang:Title'. No prefix -> assume English."""
    lang, sep, title = tag.partition(":")
    if sep and 2 <= len(lang) <= 3 and lang.isalpha():
        return lang, title
    return "en", tag


def _get(url: str, params: dict) -> dict:
    for attempt in range(4):
        time.sleep(POLITE_DELAY_S)
        r = _session.get(url, params=params, timeout=20)
        if r.status_code == 429:
            wait = int(r.headers.get("Retry-After", 0)) or 5 * 2 ** attempt
            print(f"  wikipedia rate limit, waiting {wait}s")
            time.sleep(wait)
            continue
        r.raise_for_status()
        return r.json()
    r.raise_for_status()


def _intro(lang: str, title: str) -> dict | None:
    """Plain-text intro section + English langlink, in one API call."""
    data = _get(f"https://{lang}.wikipedia.org/w/api.php", {
        "action": "query", "prop": "extracts|langlinks|info|pageprops",
        "exintro": 1, "explaintext": 1, "lllang": "en", "inprop": "url",
        "titles": title, "redirects": 1, "format": "json", "formatversion": 2,
    })
    page = data["query"]["pages"][0]
    if page.get("missing") or "disambiguation" in page.get("pageprops", {}):
        return None
    links = page.get("langlinks", [])
    return {
        "lang": lang,
        "title": page["title"],
        "extract": page.get("extract", "").strip(),
        "url": page.get("fullurl"),
        "en_title": links[0]["title"] if links else None,
    }


def fetch_summary(tag: str) -> dict | None:
    """Intro for an OSM wikipedia tag, preferring the English article if it's long enough.

    Returns None if there's no usable article. Misses are cached too.
    """
    cached = cache.get("wiki-intro", tag)
    if cached is not None:
        return cached or None

    lang, title = _split_tag(tag)
    try:
        result = _intro(lang, title)
        en_title = result and result.pop("en_title")
        if en_title and lang != "en":
            en = _intro("en", en_title)
            if en and len(en["extract"]) >= MIN_EXTRACT_CHARS:
                en.pop("en_title")
                result = en
    except requests.RequestException as e:
        print(f"  wikipedia failed for {tag}: {e}")
        return None  # don't cache network errors

    if result is None or len(result["extract"]) < MIN_EXTRACT_CHARS:
        cache.put("wiki-intro", tag, {})
        return None
    cache.put("wiki-intro", tag, result)
    return result
