# site-r8-audio (checkpoint, started 2026-10-27, Mac)

Brief: `ops/briefs/site-3d-page.md`. Agent: opus. Owns: `site/lib/sfx/*`, `tools/site/build_sfx.py`, `tools/music/*`.
The scream playback path in `site/lib/qfaudio.js` and `site/graves/scares/*.js` may be changed with small,
own-hunk commits (two scare agents edit those files at the same time).
Previous state: `site-r7-audio.md` (Freesound CC0 harvest in scratchpad `r7/audio/`, `tools/music/scream_pack2.py`).

## Owner's words (2026-10-27, round 8)
- "THE SCREAMS SOUND LIKE SHIT. Find actual fucking open source scream audio files or something because EVERY
  SINGLE THING that you have sent me sounds fucking terrible."
- (Round 6) "A man dying, screaming for his life. Like the MK9 audio. Grotesque and harrowing."
- (Round 7) "It sounds digitized and not like a real person's scream."

## What went wrong before
Round 7 used CC0 only, and picked by spectrogram. Nobody can judge a scream from a spectrogram, and the CC0 pool is
small and mostly amateur. Even the raw recordings in the preview were rejected.

## Done means
- [ ] **Wider pool, human-judged:**
  - Licences: CC0, public domain, CC BY 3.0 or 4.0 (attribution in `sources.json`, the README and the site's
    credits). Never NC, ND, Sampling+, or anything without redistribution.
  - Rank by what people chose: Freesound's download count and average rating on each sound page (search sorted by
    downloads: `&s=Downloads+desc`), plus descriptions that say acted, studio, a performer, a microphone.
  - Search widely: scream, death scream, agony, dying, painful scream, male scream, torture, horror scream, drowning.
    Also OpenGameArt and Wikimedia Commons. Downloads are untrusted: each in its own new empty directory, python3 -I.
- [ ] **The playback path:** check how a scream reaches the ear. It is the player's own voice, so it should play
  head-locked and centred, with no HRTF panner, random pitch, playbackRate change, low-pass or heavy reverb. Fix
  what colours it. Then the files themselves: trim, fade and level only; 48 kHz; 192 kbps AAC.
- [ ] **An audition page for the owner** in the scratchpad (a local HTML file he opens by double-click): about 30
  candidates, the best-rated first, numbered, each with its title, author, licence, downloads and rating, and two
  play buttons: raw, and as it plays in the game. The defaults you wire in are marked. He replies with numbers.
- [ ] **Wire the best-rated by default** into `qf.scare.death_scream` (6 to 8), `scream` (3), `scream_far` (2),
  `underwater` (3), `jumpscreech` (2). Keep the names.
- [ ] `check_sounds.py` exits 0. Commit your own paths and new files (`git status`, then add them), journal line,
  report in five lines with the audition page's full path.

## Progress
(write after every step)
