"""walkradio CLI | OSM -> filter -> route -> Wikipedia -> Gemma stories -> Piper MP3s + .m3u"""
import argparse
import json
import time
from pathlib import Path

from . import audio, overpass, places, story, wiki

KUCHAJDA = (48.1696, 17.1449)  # lake centre, OSM relation/2880173
OUT = Path("out")


def build_route(args) -> list[dict]:
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

    walk = {"start": {"lat": args.lat, "lon": args.lon}, "radius_m": args.radius, "stops": route}
    OUT.mkdir(exist_ok=True)
    (OUT / "walk.json").write_text(json.dumps(walk, ensure_ascii=False, indent=2), encoding="utf-8")
    return route


def main() -> None:
    ap = argparse.ArgumentParser(prog="walkradio", description="Build an audio walk from nearby places with a Wikipedia article.")
    ap.add_argument("--lat", type=float, default=KUCHAJDA[0])
    ap.add_argument("--lon", type=float, default=KUCHAJDA[1])
    ap.add_argument("--radius", type=int, default=2500, help="search radius in metres (default 2500)")
    ap.add_argument("--stops", type=int, default=5, help=f"number of stops, max {places.MAX_STOPS} (default 5)")
    ap.add_argument("--audio-only", action="store_true",
                    help="re-render MP3s from out/walk.json and out/stories/*.txt, no OSM/Wikipedia/Gemma calls")
    args = ap.parse_args()
    if not 1 <= args.stops <= places.MAX_STOPS:
        ap.error(f"--stops must be 1..{places.MAX_STOPS}")

    t0 = time.time()
    if args.audio_only:
        route = json.loads((OUT / "walk.json").read_text(encoding="utf-8"))["stops"]
        print(f"Audio only: {len(route)} stops from {OUT / 'walk.json'}")
    else:
        route = build_route(args)
    t_route = time.time()

    print("\nStories:")
    stories = []
    for n, stop in enumerate(route, 1):
        print(f"  {n:02d} {stop['name']}")
        text, generated = story.get_story(n, stop, generate=not args.audio_only)
        if not generated:
            print(f"    reused {story.story_path(n, stop)}")
        stories.append(text)
    t_stories = time.time()

    print("\nAudio:")
    renderer = audio.Renderer()
    tracks = []
    intro = OUT / "audio" / "00-intro.mp3"
    renderer.render(audio.intro_script(route), intro)
    tracks.append((intro, "Intro"))
    for n, (stop, text) in enumerate(zip(route, stories), 1):
        mp3 = OUT / "audio" / f"{story.story_path(n, stop).stem}.mp3"
        renderer.render(audio.stop_script(route, n - 1, text), mp3)
        tracks.append((mp3, f"{n}. {stop['name']}"))
    audio.write_playlist(tracks, OUT / "walk.m3u")
    t_audio = time.time()

    total_audio = sum(audio.mp3_duration_s(mp3) for mp3, _ in tracks)
    for mp3, title in tracks:
        print(f"  {mp3.name:<40} {audio.mp3_duration_s(mp3):5.1f}s  {title}")
    print(f"\n{len(tracks)} tracks, {total_audio / 60:.1f} min of audio, playlist {OUT / 'walk.m3u'}")
    print(f"Time: route {t_route - t0:.0f}s + stories {t_stories - t_route:.0f}s"
          f" + audio {t_audio - t_stories:.0f}s = {t_audio - t0:.0f}s total")


if __name__ == "__main__":
    main()
