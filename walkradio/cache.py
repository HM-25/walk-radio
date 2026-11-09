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
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        # Truncated by an interrupted run: treat as a miss so it gets refetched
        p.unlink(missing_ok=True)
        return None


def put(namespace: str, key: str, value) -> None:
    p = _path(namespace, key)
    p.parent.mkdir(parents=True, exist_ok=True)
    # Write to a temp file and swap it in, so an interrupted run never leaves a half-written entry
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)
