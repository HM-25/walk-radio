"""walkradio CLI | places stage: OSM -> filter -> route -> Wikipedia -> walk.json"""
import argparse
import json
from pathlib import Path

from . import overpass, places, wiki

KUHAJDA = (48.1700, 17.1370)


def main() -> None:
    ap = argparse.ArgumentParser(prog="walkradio", description="Build a walk from nearby places with a Wikipedia article.")
    ap.add_argument("--lat", type=float, default=KUHAJDA[0])
    ap.add_argument("--lon", type=float, default=KUHAJDA[1])
    ap.add_argument("--radius", type=int, default=2500, help="search radius in metres (default 2500)")
    ap.add_argument("--stops", type=int, default=6, help="number of stops (default 6)")
    ap.add_argument("--out", type=Path, default=Path("out/walk.json"))
    args = ap.parse_args()

    print(f"Searching OSM within {args.radius} m of {args.lat}, {args.lon} ...")
    raw = overpass.fetch_places(args.lat, args.lon, args.radius)
    candidates = places.filter_places(raw)
    print(f"{len(raw)} objects with a Wikipedia link, {len(candidates)} walk-worthy after filtering.\n")

    def accept(p: dict) -> bool:
        s = wiki.fetch_summary(p["wikipedia"])
        if s is None:
            print(f"  skip {p['name']} (no usable Wikipedia summary)")
            return False
        p["summary"] = s
        return True

    route = places.nearest_next(args.lat, args.lon, candidates, args.stops, accept)
    if len(route) < args.stops:
        print(f"\nOnly found {len(route)} of {args.stops} stops, try a bigger --radius.")

    total = sum(p["leg_m"] for p in route)
    print(f"\nWalk: {len(route)} stops, ~{total / 1000:.1f} km as the crow flies (real path is longer)\n")
    for i, p in enumerate(route, 1):
        frm = "start" if i == 1 else f"stop {i - 1}"
        print(f"{i}. {p['name']}  [{p['kind']}]")
        print(f"   {p['leg_m']} m {p['leg_dir']} from {frm}  |  wiki: {p['summary']['lang']}:{p['summary']['title']}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    walk = {"start": {"lat": args.lat, "lon": args.lon}, "radius_m": args.radius, "stops": route}
    args.out.write_text(json.dumps(walk, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved to {args.out}")


if __name__ == "__main__":
    main()
