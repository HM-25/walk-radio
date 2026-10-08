# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/HM-25/walk-radio/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/HM-25/walk-radio/releases/tag/v0.1.0
