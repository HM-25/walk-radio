"""Audio stage: track scripts (intro, stories + directions, outro) -> Piper -> MP3 + .m3u"""
import re
import subprocess
import tempfile
import unicodedata
import wave
from pathlib import Path

from piper import PiperVoice
from piper.phonemize_espeak import EspeakPhonemizer

VOICE = Path("voices/en_US-lessac-medium.onnx")
PAUSE_S = 1.0  # silence between the story and the "Next stop" line

DIRECTIONS = {
    "N": "north", "NE": "north-east", "E": "east", "SE": "south-east",
    "S": "south", "SW": "south-west", "W": "west", "NW": "north-west",
}


def spoken_distance(m: int) -> str:
    if m < 1000:
        return f"{max(50, round(m / 50) * 50)} metres"
    km = round(m / 1000, 1)
    return f"{km:g} kilometre" if km == 1 else f"{km:g} kilometres"


def next_stop_line(stop: dict, label: str = "Next stop") -> str:
    """Pure math, no AI: how far and which way to the next stop."""
    if stop["leg_m"] < 50:
        return f"{label}: {stop['name']}. You're already there."
    return f"{label}: {spoken_distance(stop['leg_m'])} {DIRECTIONS[stop['leg_dir']]}."


def intro_script(route: list[dict]) -> list[str]:
    straight_m = sum(p["leg_m"] for p in route)
    # Straight lines undersell real paths, ~1.3x is a common rule of thumb for city walking
    walk_km = round(straight_m * 1.3 / 1000 * 2) / 2
    minutes = round(walk_km / 4.5 * 60 / 5) * 5
    first = route[0]
    start = f"right by {first['name']}" if first["leg_m"] < 100 else "at your starting point"
    return [
        f"Welcome to Walk Radio. This walk starts {start}, in Bratislava. "
        f"There are {len(route)} stops, about {walk_km:g} kilometres on foot, roughly {minutes} minutes of walking. "
        "Put the phone in your pocket. Each track ends with directions to the next stop. "
        "When you get there, play the next track.",
        next_stop_line(first, "First stop"),
    ]


def stop_script(route: list[dict], i: int, story: str) -> list[str]:
    parts = [story]
    if i + 1 < len(route):
        parts.append(next_stop_line(route[i + 1]))
    else:
        parts.append(
            "That was the last stop. Thanks for walking with Walk Radio. "
            "Places from OpenStreetMap, facts from Wikipedia, stories written by Gemma, "
            "and this voice is Piper, all open source, all running on one old laptop. "
            "Enjoy the way home."
        )
    return parts


SLOVAK_LETTERS = set("áäčďéíĺľňóôŕšťúýžÁÄČĎÉÍĹĽŇÓÔŔŠŤÚÝŽ")
WORD = re.compile(r"\w+")


class SlovakPronouncer:
    """Swap Slovak words for Slovak IPA in Piper's inline [[ phoneme ]] syntax.

    The English voice reads "Štrkovec" as letter soup. Piper's bundled espeak-ng
    has Slovak, and every Slovak phoneme exists in the English voice's phoneme map,
    so the English voice can say the names the Slovak way. Text files stay untouched.
    """

    def __init__(self, extra_words: set[str] = frozenset()):
        self.espeak = EspeakPhonemizer()
        self.extra_words = {w.lower() for w in extra_words}  # e.g. stop names without diacritics, like Kuchajda
        self._ipa: dict[str, str] = {}

    def is_slovak(self, word: str) -> bool:
        return bool(SLOVAK_LETTERS & set(word)) or word.lower() in self.extra_words

    def ipa(self, word: str) -> str:
        if word not in self._ipa:
            sentences = self.espeak.phonemize("sk", word)
            ipa = "".join("".join(s) for s in sentences).strip(" .,;:!?")
            # Piper NFD-normalises its own phonemes but not raw [[ ]] blocks
            self._ipa[word] = unicodedata.normalize("NFD", ipa)
        return self._ipa[word]

    def __call__(self, text: str) -> str:
        return WORD.sub(lambda m: f"[[ {self.ipa(m[0])} ]]" if self.is_slovak(m[0]) else m[0], text)


def stop_name_words(route: list[dict]) -> set[str]:
    return {w for p in route for name in (p["name"], p["summary"]["title"]) for w in WORD.findall(name)}


class Renderer:
    def __init__(self, voice_path: Path = VOICE, pronounce=None):
        self.voice = PiperVoice.load(voice_path)
        self.pronounce = pronounce or (lambda text: text)

    def render(self, parts: list[str], mp3_path: Path) -> None:
        """Speak each part, join with a short pause, encode to MP3."""
        mp3_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
            with wave.open(tmp.name, "wb") as wav:
                fmt_set = False
                for n, text in enumerate(parts):
                    for chunk in self.voice.synthesize(self.pronounce(text)):
                        if not fmt_set:
                            wav.setframerate(chunk.sample_rate)
                            wav.setsampwidth(chunk.sample_width)
                            wav.setnchannels(chunk.sample_channels)
                            fmt_set = True
                        wav.writeframes(chunk.audio_int16_bytes)
                    if n + 1 < len(parts):
                        wav.writeframes(b"\x00" * int(wav.getframerate() * PAUSE_S) * wav.getsampwidth())
            subprocess.run(
                ["ffmpeg", "-loglevel", "error", "-y", "-i", tmp.name,
                 "-codec:a", "libmp3lame", "-q:a", "4", str(mp3_path)],
                check=True,
            )


def mp3_duration_s(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def write_playlist(tracks: list[tuple[Path, str]], m3u_path: Path) -> None:
    lines = ["#EXTM3U"]
    for mp3, title in tracks:
        lines.append(f"#EXTINF:{round(mp3_duration_s(mp3))},Walk Radio - {title}")
        lines.append(mp3.relative_to(m3u_path.parent).as_posix())
    m3u_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
