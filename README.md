# Walk Radio

A personal audio guide for a walk, made on your own laptop. Give it a starting point, it finds interesting places nearby, writes a short spoken story for each one, and renders a playlist of MP3s. Copy the folder to your phone, put the phone in your pocket, and walk. The screen part is over before you leave the house.

Built for people who like to wander their own neighbourhood and wonder what that lake, church or odd building actually is, without staring at a map app the whole time.

Everything runs locally: no GPU, no cloud, no API keys. It was built and tested on a 2016 laptop (i5-6300U, 8 GB RAM, CPU only).

## How it works

```
OpenStreetMap  ->  filter  ->  route  ->  Wikipedia intro  ->  gemma3:4b story  ->  Piper voice  ->  MP3s + .m3u
```

1. **OpenStreetMap** (Overpass API) finds named places with a `wikipedia` tag within the radius. The main Overpass server often times out, so there are three mirror fallbacks.
2. **Filter** keeps walk-worthy things (lakes, churches, parks, theatres, historic buildings) and drops districts, streets, companies, shops and whole mountain ranges. Near the default start, 162 raw results become 11.
3. **Route** picks the N nearest places that have a usable Wikipedia article, then brute-forces the shortest walking order over all permutations (up to 8 stops). Distances are straight lines, not real paths.
4. **Wikipedia** intro for each stop is the grounding. English article if one exists, otherwise the original language (around Bratislava that means Slovak).
5. **gemma3:4b via Ollama** turns each intro into a story of about 80 words, written to be spoken, using only facts from the source text.
6. Each track ends with **"Next stop: 800 metres south-east."** That line is plain math (distance and compass bearing), no AI involved.
7. **Piper** speaks every track, ffmpeg encodes MP3, and an `.m3u` playlist ties them together: an intro track, one track per stop, and an outro with credits on the last one.

Overpass and Wikipedia responses are cached as JSON in `cache/`, so reruns don't hit the network.

## Install

You need [uv](https://docs.astral.sh/uv/), [Ollama](https://ollama.com/) and ffmpeg.

```bash
git clone https://github.com/HM-25/walk-radio.git
cd walk-radio
uv sync
ollama pull gemma3:4b
uv run python -m piper.download_voices --data-dir voices en_US-lessac-medium
```

## Usage

```bash
uv run walkradio                                 # default: Kuchajda lake, Bratislava, 2500 m, 5 stops
uv run walkradio --lat 48.1435 --lon 17.1077 --radius 2000 --stops 6
```

Output in `out/`:

```
out/walk.json          the route, stops, distances and Wikipedia sources
out/stories/01-*.txt   one editable story per stop
out/audio/00-intro.mp3 ... 05-*.mp3
out/walk.m3u           the playlist, copy the whole out/ folder to your phone
```

### Proofread, then re-render

Stories are cached as plain text files. If a file exists, it is reused and Gemma is not called again, so hand edits stick. After fixing a story:

```bash
uv run walkradio --audio-only    # re-renders the MP3s from out/stories/, no network, no Gemma
```

To regenerate one story, delete its `.txt` file and run `uv run walkradio` again.

## Honest limits

- **It is slow on a CPU.** On the test laptop a 5-stop walk takes about 5.5 minutes: around 1 minute per story with gemma3:4b, then 35 seconds for all the audio. The first run also has to load the model (18 s normally, over 2 minutes if the machine is swapping, so close the browser). `--audio-only` takes about 30 seconds.
- **Translation slips.** Around Bratislava most articles only exist in Slovak, so Gemma reads Slovak and writes English. Grounding stops it from inventing whole facts, but it still gets single words wrong. Real examples from the first run: a clay running track became an "ant track", swans became "ducks and geese", and a play called "The Beast Is Written With a Capital B" became "The Bear Writes with a Big Z". Once it left a Russian word in the text, which the CLI now warns about.
- **Short sources make fluffy stories.** If the Wikipedia intro is two sentences, Gemma pads it with words like "beautiful" and "significant landmark".
- **So there is a human step.** Read the stories before you walk (about 10 minutes for 5 stops), fix what's wrong, run `--audio-only`. Treat it as part of the workflow, not an optional extra.
- **Straight-line routes.** No real routing: distances and directions are as the crow flies, and the real walk is longer. The intro estimates walking distance as straight-line distance × 1.3.
- **No GPS triggering.** You press play on the next track when you arrive.
- **English voice only.** Slovak names are read with an English accent.

## Built for

The [DEV](https://dev.to/) Hacktoberfest 2026 challenge, Week 1 "Touch Grass": build something with open-source AI at its core that gets people off the screen and into the world. The repository was started and finished within the challenge window, October 5 to 11, 2026. Any commit made after **October 11, 2026, 23:59 PDT** will be listed here.

Commits after the deadline: none.

## Credits and licenses

Walk Radio's own code is under the [MIT License](LICENSE). It stands on these projects and datasets:

| Project | Used for | License |
|---|---|---|
| [OpenStreetMap](https://www.openstreetmap.org/copyright) | Places, positions, Wikipedia links | Data © OpenStreetMap contributors, [ODbL 1.0](https://opendatacommons.org/licenses/odbl/) |
| [Overpass API](https://overpass-api.de/) and mirrors (kumi.systems, private.coffee, maps.mail.ru) | Querying OSM | Server software AGPL-3.0; thanks to the operators for the free service |
| [Wikipedia](https://www.wikipedia.org/) | Grounding text for every story | Text [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/), source article URLs saved in `out/walk.json` |
| [Gemma 3](https://ai.google.dev/gemma) (gemma3:4b) by Google | Writing the stories | [Gemma Terms of Use](https://ai.google.dev/gemma/terms) |
| [Ollama](https://github.com/ollama/ollama) | Running Gemma locally | MIT |
| [Piper](https://github.com/OHF-Voice/piper1-gpl) (`piper-tts`) | Text to speech | GPL-3.0-or-later |
| [en_US-lessac-medium](https://huggingface.co/rhasspy/piper-voices/tree/main/en/en_US/lessac/medium) voice | The voice you hear | Trained on the [Blizzard 2013 Lessac dataset](https://www.cstr.ed.ac.uk/projects/blizzard/2013/lessac_blizzard2013/), which is under a research licence. Fine for personal use; check that licence before any commercial use of the audio |
| [ffmpeg](https://ffmpeg.org/) | WAV to MP3 | LGPL/GPL |
| [requests](https://github.com/psf/requests) | HTTP | Apache-2.0 |

**About the generated walks:** the stories are adaptations of Wikipedia text, so if you share your `out/` folder, the stories and MP3s fall under CC BY-SA 4.0 too. Credit Wikipedia and link the source articles (they're in `out/walk.json`).

**About Piper and GPL:** Walk Radio imports `piper-tts`, which is GPL-3.0-or-later. This repository only contains Walk Radio's own code (MIT, which is GPL-compatible) and does not include Piper. If you distribute Walk Radio *bundled together with* Piper, that combined package has to follow the GPL.
