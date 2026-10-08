"""walkradio CLI | places stage: OSM -> filter -> route -> Wikipedia -> walk.json"""
import argparse
import json
from pathlib import Path

from . import overpass, places, wiki

KUCHAJDA = (48.1696, 17.1449)  # lake centre, OSM relation/2880173


def main() -> None:
    ap = argparse.ArgumentParser(prog="walkradio", description="Build a walk from nearby places with a Wikipedia article.")
    ap.add_argument("--lat", type=float, default=KUCHAJDA[0])
    ap.add_argument("--lon", type=float, default=KUCHAJDA[1])
    ap.add_argument("--radius", type=int, default=2500, help="search radius in metres (default 2500)")
    ap.add_argument("--stops", type=int, default=6, help=f"number of stops, max {places.MAX_STOPS} (default 6)")
    ap.add_argument("--out", type=Path, default=Path("out/walk.json"))
    args = ap.parse_args()
    if not 1 <= args.stops <= places.MAX_STOPS:
        ap.error(f"--stops must be 1..{places.MAX_STOPS}")

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

    picked = places.pick_nearest(args.lat, args.lon, candidates, args.stops, accept)
    route = places.shortest_order(args.lat, args.lon, picked)
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
