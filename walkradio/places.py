"""Filter raw OSM results down to walk-worthy places, and order them into a walk."""
import math

# A place is kept if it matches at least one of these (key -> allowed values, "*" = any)
KEEP = {
    "historic": "*",
    "heritage": "*",
    "tourism": {"attraction", "viewpoint", "museum", "artwork", "gallery", "picnic_site"},
    "natural": {"water", "peak", "spring", "wood", "cave_entrance", "tree", "rock", "wetland"},
    "leisure": {"park", "nature_reserve", "garden"},
    "amenity": {"place_of_worship", "theatre", "fountain", "grave_yard", "arts_centre"},
    "landuse": {"cemetery", "forest"},
    "water": {"lake", "pond", "river"},
    "man_made": {"tower", "water_tower"},
    "building": {"church", "chapel", "cathedral"},
}

# ...and dropped if it has any of these, unless it's historic/heritage.
# Catches districts, streets, companies, shops and whole mountain ranges.
DROP_KEYS = {"boundary", "place", "highway", "admin_level", "route", "shop", "office", "brand", "public_transport"}
DROP_VALUES = {"natural": {"mountain_range", "plain", "flat", "valley", "ridge"}}

EARTH_R = 6_371_000
COMPASS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]


def _kind(tags: dict) -> str | None:
    for key, allowed in KEEP.items():
        v = tags.get(key)
        if v and (allowed == "*" or v in allowed):
            return f"{key}={v}"
    return None


def _position(el: dict) -> tuple[float, float] | None:
    if "lat" in el:
        return el["lat"], el["lon"]
    if "center" in el:
        return el["center"]["lat"], el["center"]["lon"]
    return None


def filter_places(elements: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for el in elements:
        tags = el.get("tags", {})
        kind = _kind(tags)
        if not kind:
            continue
        protected = "historic" in tags or "heritage" in tags
        if not protected:
            if DROP_KEYS & tags.keys():
                continue
            if any(tags.get(k) in vals for k, vals in DROP_VALUES.items()):
                continue
        pos = _position(el)
        wiki = tags["wikipedia"]
        if pos is None or wiki in seen:
            continue
        seen.add(wiki)
        out.append({
            "osm": f"{el['type']}/{el['id']}",
            "name": tags["name"],
            "kind": kind,
            "lat": pos[0],
            "lon": pos[1],
            "wikipedia": wiki,
        })
    return out


def distance_m(lat1, lon1, lat2, lon2) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_R * math.asin(math.sqrt(a))


def bearing(lat1, lon1, lat2, lon2) -> str:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dl) * math.cos(p2)
    y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    deg = (math.degrees(math.atan2(x, y)) + 360) % 360
    return COMPASS[round(deg / 45) % 8]


def nearest_next(lat: float, lon: float, candidates: list[dict], stops: int, accept) -> list[dict]:
    """Greedy walk: from the current point, go to the nearest unvisited place.

    `accept(place)` is called on each pick; if it returns False the place is skipped
    (e.g. no usable Wikipedia summary) and the next nearest is tried.
    """
    remaining = list(candidates)
    route = []
    cur = (lat, lon)
    while remaining and len(route) < stops:
        remaining.sort(key=lambda p: distance_m(*cur, p["lat"], p["lon"]))
        p = remaining.pop(0)
        if not accept(p):
            continue
        p["leg_m"] = round(distance_m(*cur, p["lat"], p["lon"]))
        p["leg_dir"] = bearing(*cur, p["lat"], p["lon"])
        route.append(p)
        cur = (p["lat"], p["lon"])
    return route
