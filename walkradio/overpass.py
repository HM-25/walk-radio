"""Fetch named OSM objects with a Wikipedia link around a point."""
import requests

from . import USER_AGENT, cache

# Main Overpass server often returns 504, so fall back to mirrors
ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]


def fetch_places(lat: float, lon: float, radius_m: int) -> list[dict]:
    query = f"""
[out:json][timeout:25];
nwr(around:{radius_m},{lat},{lon})["name"]["wikipedia"];
out center tags;
"""
    cached = cache.get("overpass", query)
    if cached is not None:
        return cached

    for url in ENDPOINTS:
        try:
            r = requests.post(
                url,
                data={"data": query},
                headers={"User-Agent": USER_AGENT},
                timeout=60,
            )
            r.raise_for_status()
            data = r.json()
            # A query that hits the server-side timeout still returns 200, with a
            # "remark" and partial (often empty) elements. Don't accept or cache that.
            remark = data.get("remark", "")
            if "error" in remark.lower():
                raise ValueError(remark.strip())
            elements = data["elements"]
            break
        except (requests.RequestException, ValueError, KeyError) as e:
            print(f"  {url} failed: {e}")
    else:
        raise SystemExit("All Overpass endpoints failed, try again in a minute")

    cache.put("overpass", query, elements)
    return elements
