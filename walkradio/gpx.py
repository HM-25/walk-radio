"""GPX export: stops as named waypoints plus a route in walking order, for OsmAnd, Organic Maps etc."""
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr


def write_gpx(start: tuple[float, float], route: list[dict], path: Path) -> None:
    def point(tag: str, lat: float, lon: float, name: str, desc: str | None = None) -> str:
        inner = f"<name>{escape(name)}</name>"
        if desc:
            inner += f"<desc>{escape(desc)}</desc>"
        return f'<{tag} lat="{lat:.7f}" lon="{lon:.7f}">{inner}</{tag}>'

    named = [(f"{n}. {p['name']}", p) for n, p in enumerate(route, 1)]
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<gpx version="1.1" creator="Walk Radio" xmlns="http://www.topografix.com/GPX/1/1">',
        "  <metadata><name>Walk Radio</name>"
        f"<link href={quoteattr('https://www.openstreetmap.org/copyright')}><text>Map data © OpenStreetMap contributors</text></link>"
        "</metadata>",
    ]
    lines += [f"  {point('wpt', p['lat'], p['lon'], name, p['summary'].get('url'))}" for name, p in named]
    lines.append("  <rte><name>Walk Radio</name>")
    lines.append(f"    {point('rtept', *start, 'Start')}")
    lines += [f"    {point('rtept', p['lat'], p['lon'], name)}" for name, p in named]
    lines += ["  </rte>", "</gpx>"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
