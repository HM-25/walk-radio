# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `out/walk.gpx` with the stops as named waypoints (linked to their Wikipedia article) and a route in walking order.
- Warning when a story looks like Slovak instead of English.

### Changed
- Stop selection now picks the best subset, not the nearest N: the N stops and order with the shortest total route, no leg over 1200 m, from up to 12 candidates. Exact, via a subset DP, cross-checked against brute force over combinations and permutations. The default walk went from 4.4 km with a 2.2 km silent last leg to 3.2 km with no leg over 1130 m.
- Story prompt: proper names and titles stay in Slovak, optionally with a short English explanation. This stops mistranslated titles, e.g. the play "Zver sa píše s veľkým Z" had come out as "The Bear Writes with a Big Z".
- Story prompt: never pad, and the word budget scales with source length (half the source's words, 40 to 80). A two-sentence source had been padded with "beautiful", "significant landmark" and a wrong "in the heart of Bratislava"; it now gives a 21-word story.

### Fixed
- Stories that hit the output token cap are trimmed to the last complete sentence instead of ending mid-sentence ("An asphalt running track is built around it,").
- Markdown emphasis (`*title*`) is stripped before speech.
- After the "keep names in Slovak" prompt change, Gemma wrote two whole stories in Slovak. The prompt now says to write in English with only proper names in Slovak, and the CLI warns when a story looks Slovak.
- Proofread fixes to the default Kuchajda walk. These are hand edits to generated stories in `out/stories/` (not tracked in the repo), listed here because they show what the proofread step catches. None were invented facts; all were language errors from translating Slovak sources:
  - Story 2: "Tomášikovej ulica" to "Tomášikova street" (Slovak name in the wrong grammatical case).
  - Story 3: "ducks and geese" to "ducks and swans" (the source says "kačice a labute"; the same mistranslation appeared in two separate runs).
  - Story 3: "Ružinovské jazero, alebo Rohlík" to "Ružinovské jazero, or Rohlík" (the Slovak "alebo" leaked into English).
  - Story 3: one organisation had been split into two; now "the Ružinov branch of Slovenský rybársky zväz, the Slovak Anglers' Union".
  - Story 3: "Ružin Hospital" to "Ružinov hospital" (district name clipped).
  - Story 4: "residents of Štrkov" to "residents of Štrkovec" (place name clipped).
  - Story 4: "a lake in Ružinove" to "a lake in Ružinov" (Slovak locative case copied into English).

## [0.1.0] - 2026-10-08

### Added
- `walkradio` command (`uv run walkradio`) with `--lat`, `--lon`, `--radius` and `--stops` (default 5, max 8).
- OpenStreetMap lookup through the Overpass API, with fallback to three mirrors when the main server times out.
- Tag filter that keeps walk-worthy places (water, churches, parks, theatres, historic buildings) and drops districts, streets, companies, shops and mountain ranges.
- Route: the N nearest places with a usable Wikipedia article, ordered by brute-force shortest path over all permutations.
- Wikipedia intro per stop via the MediaWiki action API, preferring English and falling back to the source language, with a polite delay and backoff on rate limits.
- Story stage: gemma3:4b via Ollama writes an ~80-word spoken English story per stop, grounded only in the Wikipedia intro (temperature 0.3).
- Stories cached as editable text files in `out/stories/NN-name.txt`; existing files are reused instead of calling the model.
- Warning when a story contains non-Latin words the English voice can't pronounce.
- Audio stage: intro track (start, number of stops, rough length), one track per stop ending with "Next stop: X metres <direction>", outro with credits on the last stop.
- Piper text to speech, MP3 encoding with ffmpeg, and an `out/walk.m3u` playlist.
- `--audio-only` flag to re-render the MP3s from the text files without network or model calls.
- JSON cache for Overpass and Wikipedia responses in `cache/`.
- `spike.py`, the original 30-minute feasibility check, kept for history.
- README, MIT license, this changelog.

### Fixed
Problems found and fixed while building 0.1.0:
- The main Overpass server often returned 504 Gateway Timeout. Added fallback mirrors; later all three endpoints failed at once, so a fourth (maps.mail.ru) was added.
- Wikipedia's REST `/page/summary` endpoint only returns the first sentence, so the lake at the start point (143 characters) was rejected as too short. Switched to the MediaWiki action API intro extract (953 characters for the same article).
- Wikimedia rate-limited the first run with 429 Too Many Requests on most stops. Added a 1 second delay between requests and backoff that honours `Retry-After`.
- That first run had cached the rejected articles as "no article". The Wikipedia cache moved to a new namespace so stale entries are ignored.
- The nearest-next route zigzagged (1 km east, then 1.9 km back west). Replaced by brute-force ordering over all permutations.
- The default start moved from a rough point near the lake to the lake's centre from OpenStreetMap (relation 2880173).
- Gemma once opened a story with a stage direction, "(Sound of gentle ambient music fades in)", which the voice would read aloud. The prompt now asks for spoken words only, and lines in brackets are stripped.
- Gemma once left a Russian word ("православный") in an English story. The prompt now asks it to translate foreign words, and the CLI warns about non-Latin words.
- The intro said "Next stop: Kuchajda. You're already there." right after "This walk starts right by Kuchajda". The first leg now reads "First stop".
- Packaging: `uv_build` looked for a `walk_radio` module; the module name is now set to `walkradio`.

[Unreleased]: https://github.com/HM-25/walk-radio/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/HM-25/walk-radio/releases/tag/v0.1.0
