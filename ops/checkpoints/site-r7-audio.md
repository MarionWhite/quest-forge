# site-r7-audio (checkpoint, started 2026-10-27, Mac)

Brief: `ops/briefs/site-3d-page.md`. Agent: sonnet. Owns: `site/lib/sfx/*`, `tools/site/build_sfx.py`,
`tools/music/*`.
Previous state: `site-r6-audio.md`.

## Owner's words (2026-10-27)
- "The scream still sounds like complete shit. It sounds digitized and not like a real person's scream."
- (Round 6) "A man dying, screaming for his life. Like the MK9 audio. Grotesque and harrowing."

## Diagnosis
The round-6 screams layer up to 8 sources each, mostly short game "grunts", processed, then encoded at 32 kHz
and about 86 kbps. That combination is what sounds digital.

## Done means
- [ ] **Real performances:**
  - Find recordings of a person actually screaming, at length (1.5 to 4 s): agony, terror, death throes,
    drowning.
  - Search Freesound with the CC0 licence filter. The search pages and the HQ previews are public with no
    login: `https://freesound.org/search/?q=scream+death&f=license:%22Creative+Commons+0%22`, and each
    sound page links its preview mp3.
  - Also search Wikimedia Commons (CC0 or public domain) and OpenGameArt (CC0).
  - CC0 or public domain only. Record the URL, author and licence in `sources.json`.
  - Downloads are untrusted: put each in its own new, empty directory, and use python3 -I.
- [ ] **Minimal processing:**
  - One voice per event, at most one gore foley layer under it.
  - Pitch shift within ±1 semitone, with no time-stretch artifacts, bitcrush or saturation.
  - Trim, fade, level to about -1 dBFS peak, gentle EQ and a short room reverb only.
  - Encode these events at 44.1 or 48 kHz, 160 kbps AAC.
- [ ] **Events:**
  - `qf.scare.death_scream`: 6 to 8 variants.
  - `qf.scare.scream`: 3.
  - `qf.scare.scream_far`: 2. A real scream with distance and echo.
  - `qf.scare.underwater`: 3. A real scream through a low-pass filter, with bubbles.
  - `qf.scare.jumpscreech`: 2. A real scream with a short sharp hit, no layered screech stack.
- [ ] A ranked preview file: every candidate source raw, then the processed version, with a text list of what
  is where. The owner picks by ear. Put it in the scratchpad and name the path in the report.
- [ ] If CC0 sources can't reach the bar, say so plainly in the report, and name the 2 best routes. For example,
  a Freesound account and API key from the owner, or a recorded performance.
- [ ] `check_sounds.py` exits 0.

## Progress (audio agent)
- Freesound CC0 search + sound pages + HQ preview mp3 are public via curl (no login). Harvest scripts in scratchpad
  r7/audio/scripts (harvest.py, dlall.py); downloads r7/audio/dl/fs<ID>/ (p.mp3, meta.json). ~265 candidates.
- Next: ffprobe durations, spectral triage (voiced/loud), listen-proxy ranking, build via new script tools/music/scream_pack2.py.
- DONE pass 1: Freesound CC0 pool (265 pages checked, licence link verified), segmented by voiced-energy, spectrogram-reviewed.
  `tools/music/scream_pack2.py` (fetch|build) builds death_scream 8, scream 3, scream_far 2, underwater 3, jumpscreech 2
  from 13 Freesound CC0 recordings, one voice each, 48 kHz 160 kbps AAC. scream_pack.py skips those 5 events now.
  sources.json/README updated by merge_sources(). Raw downloads: scratchpad r7/audio/dl/fs<ID>/p.mp3.
- Next: ranked preview file, commit, journal line, report.
