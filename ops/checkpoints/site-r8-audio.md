# site-r8-audio (checkpoint, started 2026-10-27, Mac) - DONE 2026-10-27, waiting on the owner's picks

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
- [x] **Wider pool, human-judged:**
  - Licences: CC0, public domain, CC BY 3.0 or 4.0 (attribution in `sources.json`, the README and the site's
    credits). Never NC, ND, Sampling+, or anything without redistribution.
  - Rank by what people chose: Freesound's download count and average rating on each sound page (search sorted by
    downloads: `&s=Downloads+desc`), plus descriptions that say acted, studio, a performer, a microphone.
  - Search widely: scream, death scream, agony, dying, painful scream, male scream, torture, horror scream, drowning.
    Also OpenGameArt and Wikimedia Commons. Downloads are untrusted: each in its own new empty directory, python3 -I.
- [x] **The playback path:** check how a scream reaches the ear. It is the player's own voice, so it should play
  head-locked and centred, with no HRTF panner, random pitch, playbackRate change, low-pass or heavy reverb. Fix
  what colours it. Then the files themselves: trim, fade and level only; 48 kHz; 192 kbps AAC.
- [x] **An audition page for the owner** in the scratchpad (a local HTML file he opens by double-click): about 30
  candidates, the best-rated first, numbered, each with its title, author, licence, downloads and rating, and two
  play buttons: raw, and as it plays in the game. The defaults you wire in are marked. He replies with numbers.
- [x] **Wire the best-rated by default** into `qf.scare.death_scream` (6 to 8), `scream` (3), `scream_far` (2),
  `underwater` (3), `jumpscreech` (2). Keep the names.
- [x] `check_sounds.py` exits 0. Commit your own paths and new files (`git status`, then add them), journal line,
  report in five lines with the audition page's full path.

## Progress
(write after every step)
- Scratchpad: `r8/audio/` = scripts/ (my code), pages/ (search html), dl/fs<ID>/ (one dir per download), work/, audition/.
- Playback path found (qfaudio.js + scares.js + fnaf.js deathScream): no panner (no `at`), but manifest pitch
  [.97,1.03] = random playbackRate (Chrome resamples linearly), volume 1.1-1.7 into a -10 dB 4:1 master compressor
  with auto makeup gain (then hard clip at the destination), ghast's @muffle low-passes the scream, and
  `game.player.hurt` ("oof") is layered 20 ms into every death scream. scream/scream_far unused in site JS.
- Sources: use Freesound `-hq.ogg` previews (~192k Vorbis), not r7's 128k mp3.
- DONE harvest: `scripts/harvest.py` (70 queries, sorted by downloads, all licences) -> `work/cards.json` (911);
  `scripts/pages.py` -> `work/pages.json` (427 sound pages: licence link, n ratings, desc, tags, file info, hq ogg).
  OGA (BY 3.0 "Aargh! male screams", Wilhelm-style) and Commons (BY-SA or Wilhelm) checked: nothing better, skipped.
- DONE dl: 75 recordings in `dl/fs<ID>/p.ogg` (`work/shortlist.txt`). `scripts/analyse.py` -> `work/analysis.json`
  (takes, F0, floor); `scripts/clipcheck.py` -> `work/clip.json` (likely clipped at source: decoded peak > +1 dBFS
  and >0.1% samples above -0.3 dBFS: jorickhoofd 1793xx/1803xx, MrFossy 5471xx, 556706, 219719, 31818, 163728,
  445008, 163442, RutgerMuller 104033/4/7, 79). `work/sheet_multi.png` locates takes in multi-take files.
- DONE playback commit 6a1cd83: qfaudio 'voice' bus (no panner/pitch/reverb, gain<=1, skips compressor+muffle,
  final -1 dBFS limiter for everything), muffle() reuses the master compressor, fnaf.js hurt 0.1 s before scream.
  The manifest must set bus "voice" for the 5 events (scream_pack3.py does it).
- Takes located from `work/sheet_{a,b,c,multi,583594}.png` + `work/analysis.json`; underwater extras downloaded
  (752733 real underwater mic, 725874, 583594 own-death-by-water 2:24, 488957, 482836).
- Rank = Bayesian rating (prior 3.8, weight 5 ratings) + 0.15*log10(downloads). Clipped-at-source excluded.
- DONE `tools/music/scream_pack3.py` (fetch|build|audition; 34 takes from 32 recordings in TAKES, DEFAULTS per
  event, meta in `tools/music/scream_pack3_meta.json`, licences re-verified on each page by fetch; writes
  manifest bus "voice", sources.json, README, `site/lib/sfx/credits.html`). scream_pack.py now merges via
  scream_pack3; scream_pack2.py refuses unless QF_R7=1. Run: `QF_DL=<scratch>/r8/audio/dl QF_TMP=<scratch>/r8/audio/tmp
  /opt/anaconda3/bin/python3 -I tools/music/scream_pack3.py audition <scratch>/r8/audio/audition`.
- DONE audition: `<scratch>/r8/audio/audition/index.html` (34 takes, raw float WAV + game m4a + whole ogg; loads in
  Chrome from file://; desktop/narrow screenshots `work/aud_*.png` checked). Defaults rule: best-ranked per use, max 2
  per performer, skip "maybe clipped" / double-flagged / dictaphone.
- DONE build: 18 files wired (manifest bus "voice", pitch 1, volume 1), level -12 dBFS loudest 400 ms / -1 dBTP;
  audition "In game" files are byte-identical to the site files. check_sounds exits 0. Runtime probe in headless
  Chrome (work/probe/): voice bus has no panner, gain capped 1, rate 1; sfx still spatial; muffle + mute fine.
  scares.js: one voice at a time for death_scream + underwater. Graves footer "Sound credits" link (own hunk only,
  patch `work/credits_link.patch` applied with `git apply --cached`). Journal line written.
- DONE commits (own paths only). Audition page: /private/tmp/claude-503/-Users-suaz-Desktop-QuestForge/91769071-2ed0-4412-b25d-3c510232d8e5/scratchpad/r8/audio/audition/index.html
- When the owner replies with numbers: map them to keys with `audition/candidates.json` (n -> key), put the keys in
  DEFAULTS in `tools/music/scream_pack3.py`, run `build` (QF_DL/QF_TMP as above; `fetch` re-downloads into new dirs
  if the scratchpad is gone), check_sounds, commit. If he rejects all 34: the next routes are a Freesound account
  (original WAV/AIFF downloads instead of previews, via the API) or a recorded performance.
