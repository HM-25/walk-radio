"""Story stage: a local model turns one Wikipedia intro into a ~80-word spoken story.

Test on one stop: uv run python -m walkradio.story [stop_number]
"""
import json
import re
import sys
import time
from pathlib import Path

import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "gemma3:4b"
MAX_SOURCE_CHARS = 1200  # prompt reading is the bottleneck on this CPU, keep it short

PROMPT = """You are a friendly audio guide. Someone is walking past {name} in Bratislava with headphones on.
Write 70 to 80 words in English. Output only the words to be spoken.
Use ONLY facts from the source text below. If the source does not say it, do not say it.
No greeting, no stage directions, no sound effects, no headings, no lists, no emoji. Do not mention Wikipedia.

Source text ({lang} Wikipedia):
{source}"""


def _clean(text: str) -> str:
    """Drop stage directions like '(Sound of music fades in)' that TTS would read aloud."""
    text = re.sub(r"^\s*[(*\[].*?[)*\]]\s*$", "", text, flags=re.MULTILINE)
    return re.sub(r"\n{2,}", "\n\n", text).strip()


def write_story(stop: dict) -> dict:
    s = stop["summary"]
    prompt = PROMPT.format(name=stop["name"], lang=s["lang"], source=s["extract"][:MAX_SOURCE_CHARS])
    r = requests.post(OLLAMA_URL, json={
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.7, "num_predict": 200, "num_ctx": 2048},
    }, timeout=600)
    r.raise_for_status()
    d = r.json()
    return {
        "text": _clean(d["response"]),
        "model": MODEL,
        "prompt_tokens": d.get("prompt_eval_count"),
        "output_tokens": d.get("eval_count"),
        "load_s": d.get("load_duration", 0) / 1e9,
        "read_s": d.get("prompt_eval_duration", 0) / 1e9,
        "write_s": d.get("eval_duration", 0) / 1e9,
    }


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    walk = json.loads(Path("out/walk.json").read_text(encoding="utf-8"))
    stop = walk["stops"][n - 1]
    print(f"Stop {n}: {stop['name']} | source {len(stop['summary']['extract'])} chars ({stop['summary']['lang']})\n")
    t0 = time.time()
    st = write_story(stop)
    wall = time.time() - t0
    print(st["text"])
    print(f"\n{len(st['text'].split())} words | wall {wall:.1f}s = load {st['load_s']:.1f}s"
          f" + read {st['prompt_tokens']} tok in {st['read_s']:.1f}s"
          f" + write {st['output_tokens']} tok in {st['write_s']:.1f}s")
