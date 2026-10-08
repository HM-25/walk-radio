"""Story stage: a local model turns one Wikipedia intro into a 40 to 80 word spoken story.

Test on one stop: uv run python -m walkradio.story [stop_number]
"""
import json
import re
import sys
import time
import unicodedata
from pathlib import Path

import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "gemma3:4b"
STORIES_DIR = Path("out/stories")
MAX_SOURCE_CHARS = 1200  # prompt reading is the bottleneck on this CPU, keep it short

PROMPT = """You are a friendly audio guide. Someone is walking past {name} in Bratislava with headphones on.
Write in English, at most {words} words. Translate the facts into English; only proper names stay in Slovak. Output only the words to be spoken.
Use ONLY facts from the source text below. If the source does not say it, do not say it. Never pad: no praise, no filler.
Keep every proper name and title (places, streets, churches, plays, organisations) exactly in the original Slovak.
You may follow a name with a short English explanation, for example: Radošinské naivné divadlo, the Radošina Naive Theatre.
No greeting, no stage directions, no sound effects, no headings, no lists, no emoji, no markdown. Do not mention Wikipedia.

Source text ({lang} Wikipedia):
{source}"""


def word_budget(source: str) -> int:
    """A short source gets a short story: half the source's words, clamped to 40..80."""
    return max(40, min(80, len(source.split()) // 2))


def _clean(text: str) -> str:
    """Drop stage directions like '(Sound of music fades in)' that TTS would read aloud."""
    text = re.sub(r"^\s*[(*\[].*?[)*\]]\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"[*_]+", "", text)  # markdown emphasis around titles
    return re.sub(r"\n{2,}", "\n\n", text).strip()


def trim_to_sentence(text: str) -> str:
    """Cut a story that hit the token cap back to its last complete sentence."""
    end = max(text.rfind(c) for c in ".!?")
    return text[: end + 1] if end > 0 else text


# Common Slovak function words; if many show up, Gemma answered in Slovak instead of English
SLOVAK_WORDS = {"je", "a", "v", "sa", "na", "z", "so", "pri", "ktorý", "ktorá", "bolo", "nachádza", "alebo"}


def looks_slovak(text: str) -> bool:
    words = re.findall(r"\w+", text.lower())
    return bool(words) and sum(w in SLOVAK_WORDS for w in words) / len(words) > 0.08


def write_story(stop: dict) -> dict:
    s = stop["summary"]
    source = s["extract"][:MAX_SOURCE_CHARS]
    prompt = PROMPT.format(name=stop["name"], lang=s["lang"], source=source, words=word_budget(source))
    r = requests.post(OLLAMA_URL, json={
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": 200, "num_ctx": 2048},
    }, timeout=600)
    r.raise_for_status()
    d = r.json()
    text = _clean(d["response"])
    if d.get("done_reason") == "length":
        text = trim_to_sentence(text)
    return {
        "text": text,
        "model": MODEL,
        "prompt_tokens": d.get("prompt_eval_count"),
        "output_tokens": d.get("eval_count"),
        "load_s": d.get("load_duration", 0) / 1e9,
        "read_s": d.get("prompt_eval_duration", 0) / 1e9,
        "write_s": d.get("eval_duration", 0) / 1e9,
    }


def slug(name: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")


def story_path(n: int, stop: dict) -> Path:
    return STORIES_DIR / f"{n:02d}-{slug(stop['name'])}.txt"


def get_story(n: int, stop: dict, generate: bool = True) -> tuple[str, bool]:
    """Story text for stop n. Reuses out/stories/NN-name.txt if it exists (hand edits win).

    Returns (text, was_generated).
    """
    path = story_path(n, stop)
    if path.exists():
        text, generated = path.read_text(encoding="utf-8").strip(), False
    elif not generate:
        raise SystemExit(f"Missing {path}, run without --audio-only first")
    else:
        st = write_story(stop)
        text, generated = st["text"], True
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
        print(f"    {len(text.split())} words, read {st['prompt_tokens']} tok in {st['read_s']:.0f}s,"
              f" write {st['output_tokens']} tok in {st['write_s']:.0f}s, load {st['load_s']:.0f}s")
    # Piper's English voice garbles other scripts (Gemma once wrote "православный")
    foreign = sorted({w for w in re.findall(r"\w+", text) if any(c.isalpha() and ord(c) > 0x24F for c in w)})
    if foreign:
        print(f"    WARNING non-Latin words, edit {path}: {', '.join(foreign)}")
    if looks_slovak(text):
        print(f"    WARNING looks like Slovak, not English, edit or delete {path}")
    return text, generated


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
