"""Walk Radio | 30-minute spike.
Checks the one real unknown: are there enough interesting places near the start point?
Run: uv run python spike.py
"""
import requests

LAT, LON = 48.1700, 17.1370   # near Kuhajda lake, Bratislava
RADIUS_M = 2500

query = f"""
[out:json][timeout:25];
nwr(around:{RADIUS_M},{LAT},{LON})["name"]["wikipedia"];
out center tags;
"""

# Main Overpass server often returns 504, so fall back to mirrors
ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
for url in ENDPOINTS:
    try:
        r = requests.post(
            url,
            data={"data": query},
            headers={"User-Agent": "walk-radio-spike/0.1 (hackathon project)"},
            timeout=60,
        )
        r.raise_for_status()
        break
    except requests.RequestException as e:
        print(f"{url} failed: {e}")
else:
    raise SystemExit("All Overpass endpoints failed")
places = r.json()["elements"]

print(f"Found {len(places)} places with a Wikipedia link within {RADIUS_M} m:\n")
for p in places:
    t = p["tags"]
    kind = t.get("historic") or t.get("amenity") or t.get("tourism") or t.get("natural") or t.get("building") or "?"
    print(f"- {t['name']:<40} [{kind}]  wiki: {t['wikipedia']}")
