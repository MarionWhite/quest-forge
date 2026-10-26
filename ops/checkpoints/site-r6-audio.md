# site-r6-audio (checkpoint, started 2026-10-26, Mac)

Brief: `ops/briefs/site-3d-page.md`. Agent: sonnet.
Owns: `site/lib/sfx/*`, `tools/site/build_sfx.py`, `tools/music/*`.
Previous state: `site-r5-audio.md`.

## Owner's words (2026-10-26)
- "The audio that I am assuming is the scream audio is fucking terrible. I want it to sound like
  a man fucking dying, screaming for his life. Like the MK9 audio. Grotesque and harrowing."

## Done means
- [ ] **Recorded human voice.** Synthesis is out for screams. Source real recordings under CC0
  only, for example from freesound.org filtered to the Creative Commons 0 licence, or
  OpenGameArt CC0.
  - Look for male screams of agony and terror, death rattles, choking and gurgling, and
    drowning.
  - Record each source's URL, author and licence in `site/lib/sfx/README` and in a
    `sources.json` next to the files.
  - No CC-BY-NC, no "royalty-free but no redistribution", nothing from MK or any game.
  - Downloads are untrusted data: put each in its own new empty directory, and use python3 -I.
- [ ] **Build these by processing and layering** in a script, `tools/music/scream_pack.py`. Use
  pitch, time and EQ, a saturation or crunch layer, gore foley (crunch, wet tear) and low booms,
  in the MK9 "fatality" style:
  - `qf.scare.death_scream`: 6 variants, 2 to 4 s, a man dying. Some cut off into a gurgle.
  - `qf.scare.jumpscreech`: 4 variants. A FNAF-style lunge screech: scream, mob screech, static
    burst and sub hit, very loud but not clipping.
  - `qf.scare.underwater`: 3 variants, a muffled drowning scream with bubbles.
  - `qf.scare.static`: a loop of TV static with a hum.
  - Replace the synthesized `qf.scare.scream`, `scream_far` and `shriek` with recorded-voice
    versions under the same names.
- [ ] **Mood set:**
  - `qf.mood.far_groan`, `far_rattle`, `far_vwoop`, `far_cry` and `far_hiss`, 2 each: the
    bank's mob sounds with a long cave echo and low-pass, as if 100 blocks away.
  - `qf.mood.scamper`, 4: claws skittering on stone, passing left to right.
  - `qf.mood.scrape`, 2.
  - `qf.mood.breath_near`, 2: a recorded CC0 breath, wet and close.
  - Flag the Mojang-derived ones for `--own-only`.
- [ ] `check_sounds.py` exits 0.
- [ ] Report which files a human should listen to first, and the source list.

## Progress (audio agent)
- Sourcing done: OpenGameArt CC0 pages checked one by one (licence link publicdomain/zero/1.0), downloads in
  scratchpad r6/audio/dl/<key>/. Freesound needs a login, so not used. Voice pool: deathpain (49 s of male
  pain/death screams), manhurt, maledead pack, hurtdeath pack, screech, horror1, painemo, sick, creature pack.
- Plan: `tools/music/scream_pack.py` (fetch -> decode -> layer/process -> encode), writes
  `site/lib/sfx/sources.json` and `site/lib/sfx/README.md`. Mood far_* derive from the bank (Mojang): flagged
  `"mojang": true` and dropped by `build_sfx.py --own-only`.
- DONE pass 1 (commit c301033): `tools/music/scream_pack.py` builds every event in the checklist (death_scream 6,
  jumpscreech 4, underwater 3, static loop, scream 3, scream_far 2, shriek 3, mood far_* x5 (2 each, flagged
  mojang, dropped by build_sfx --own-only), scamper 4, scrape 2, breath_near 2). sources.json + README.md written.
  Run: `QF_DL=<dir> QF_TMP=<dir> /opt/anaconda3/bin/python3 -I tools/music/scream_pack.py fetch|build [event]`
  (scratchpad r6/audio/dl2 has the downloads). check_sounds exits 0.
- Next: quality iteration by spectrogram (r6/audio/scripts/spec.py), journal line, final report.
- DONE pass 2: death screams now use the full natural length of the real recordings (spectrograms show voiced
  harmonics), all events rebuilt, check_sounds exits 0, journal line added. Remaining: only human listening.
