"""Tiny JSON file cache, so reruns don't hammer Overpass or Wikipedia."""
import hashlib
import json
from pathlib import Path

CACHE_DIR = Path("cache")


def _path(namespace: str, key: str) -> Path:
    digest = hashlib.sha1(key.encode()).hexdigest()[:16]
    return CACHE_DIR / namespace / f"{digest}.json"


def get(namespace: str, key: str):
    p = _path(namespace, key)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return None


def put(namespace: str, key: str, value) -> None:
    p = _path(namespace, key)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
