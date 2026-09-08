# Quest Forge menu / loading-screen music (2026-09-04)

Two cues, one emotional cut:

| Screen | Cue | Feel | Ref image |
|---|---|---|---|
| Forge splash (~3.5 min on the Mac) | **"Hall of the Knight"** | low male chant over a drone, horn calls, one deep boom per phrase. Scale, confidence, "I am the knight" | `_splash-knight-glow/loading_mural.png` |
| Main menu (CustomMenu, ant scene) | **"The Hall Goes Quiet"** | real crickets outside. A deep, distant creaking groan; the field goes silent. The dread drone rises in the gap they leave, then recedes and the crickets creep back | `_splash-knight-glow/smoke_menu.png` |

The transition is the point: the chant is cut dead when the splash closes, then the menu opens onto an
ordinary night outside. Nothing is wrong yet. Then something is. No crossfade.

Both cues are **seamless loops** (tail crossfaded under the head in `synth.py::seamless`, seam error < 0.03).

## Round 2 (user feedback on round 1)
- Loading: the metered taiko on every bar was the problem ("annoying synth drum"). v2 keeps drone + chant +
  horns and leaves exactly one soft distant boom at the start of each 4-bar phrase. Added a low throat-drone
  voice under the sub so the bed is less "synth".
- Menu: the v1 dread drone is dropped for an environmental scene. Timeline of the 119 s loop:
  0–23 s crickets (6 field crickets + a tree-cricket trill, dulled as if through a wall) · 22 s groan begins
  · 23.6 s crickets cut, staggered over ~1 s · groan peaks ~27 s, reverb tail to ~33 s · 33–92 s quiet filler
  (wind bed, 31 Hz rumble, five drips, one wood knock at 52 s, a smaller creak at 64 s) · 92–112 s crickets
  return one every ~3.4 s · loops back to full crickets.

## Round 3 (user feedback on round 2)
Loading cue **approved as v2 — do not change it.** The menu cue was rebuilt:
- Synthetic crickets were the worst part, so they are gone. v3 uses a real CC0 field recording (see Credits).
- The groan was liked but wanted deeper: resonances dropped roughly an octave (41/78/122/190/300/470 Hz,
  was 66/131/205/318/497/780), the sub now slides 34 → 21 Hz with an octave-down growl under it, and it runs
  14 s instead of 11 with a heavier, darker reverb.
- The wind / drips / knock filler was cut entirely. The **v1 dread drone** now rises into the silence the
  crickets leave: beating E1 sub, E/Bb tritone pad with a slow filter drift, breathing LFO, three distant
  impacts, one unresolved high F5. It recedes so the crickets can return and the loop closes.

Timeline of the ~140 s **v4** loop (same scene as loved v3, groan restored then intensified):

| Time | What |
|---|---|
| 0–18 s | real crickets, full |
| 18 s | the groan begins, far off — all six modes already speaking |
| 20.5 s | the field goes silent, staggered across three frequency bands over ~0.6 s |
| 21–23 s | groan already above the cricket bed (+6.5 dB). No hole. |
| 23–25 s | climax, +13.1 dB over the crickets — same creak, slightly overwhelming |
| 25–32 s | fall, into a long reverb tail |
| 29–95 s | dread drone swells out of the tail; impacts at 46 / 68 / 88 s, unresolved F5 at 60 s |
| 95–122 s | drone recedes |
| 112–140 s | crickets return, quiet and dull first, then full → seam |

### Groan: rejected turns, then v4
**Round 4 (rejected).** "A little hollow" was read as a spectral defect and "fixed" with twelve modes,
wide skirts, and a constant material-noise layer. That flattened the notches and turned a creak into a
rumble. The notches **are** the identity.

**Round 5 (rejected, worse).** Reverted timbre but delivered intensity as a long late quiet climb
(20 s, peak at 72 %, modes gated in one at a time, extra `shape**0.45` duck). Result: more distant and
quieter. Post-cut 21–23 s sat at −34 dB, 8 dB *below* the crickets, with the event delayed to 30–32 s.

**v4.** Loved v3 timbre restored — 14 s mid-peak sine, six narrow modes at
41/78/122/190/300/470 Hz with ±4.5 % skirts, sub 34→21 + octave-down growl, 900 Hz roof, same dark
reverb (`decay=6.5`, `wet=0.62`, `tone=1100`). Intensity is a build *on top of that instrument*:
more energy in the existing body toward the climax, mild saturation (`drive = 1 + 0.5·shape`), and a
quieter octave-of-body layer. No new bright texture, no extra reverb, no 12-mode fill.

v4 measured: crickets −25.6 dB, post-cut −19.1 dB (**+6.5 dB**), climax −12.6 dB (**+13.1 dB**),
drone −24.9 dB (**+0.7 dB**).

**v5.** Same instrument and mix as v4; only the swell is louder. Climax **+15.1 dB**
over the crickets. Kept for A/B.

**v6.** Same 6-mode creak, louder bass-heavy swell. Too fried and too close (dry peak layer +
hard sat). Kept for A/B. Climax **+22.3 dB**.

**v7.** v6 intensity, distant-monster character restored: dry close layer gone,
milder saturation, darker 720 Hz roof, wetter/longer predelay, bass bloom through dark reverb
instead of in-your-face. Groan start **+1.2 dB**, climax **+20.7 dB**. The bed they called
earthquake rumble. Kept for A/B.

**v8 (current listen).** v7 quake bed unchanged, plus a distant kaiju throat-voice on top:
glottal pulses through aw→oh animal formants, 68→41 Hz moan, highpassed at 85 Hz so it is
not more rumble. Wetter/predelayed, no extra fry. Formant band ~6–8 dB hotter than v7; sub
unchanged. `out/groan_v8_excerpt.ogg` is 12–40 s of the loop.

## Files

- `synth.py` — v2 loading recipe (no metered drum) plus circular `stereo()`. Does not overwrite
  locked v2 files; loading regen is `chant_v4.py`.
- `chant_v4.py` — current loading loop: v3 chant bed + seam, rebuilt anvil stem (BSB 3589).
  Writes `out/questforge_loading_chant_v4.*` plus seam / anvil / dry-close excerpts.
- `chant_v3.py` — previous anvil (Duasun + modal). Kept for A/B; do not ship.
- `menu_v3.py` — current menu renderer (v8 output). `python3 menu_v3.py` writes
  `out/questforge_menu_night_v8.*` and `out/groan_v8_excerpt.*`. Does not overwrite earlier listens.
- `out/questforge_loading_chant_v4.ogg` — **shipped splash.** Same 53.3 s D-minor chant as v3,
  five irregular distant anvil rings from a real working smith (no modal sines).
- `out/anvil_v4_excerpt.ogg` — isolated distant rings (judge this first).
- `out/anvil_v4_dry_close.ogg` — two closer raw BSB strikes (heavy / light).
- `out/questforge_loading_chant_v3.ogg` — previous splash (rejected anvil). Same chant, old steel.
- `out/questforge_loading_chant_v2.ogg` — previous approved chant (no anvil; 12 ms right-channel hole).
- `out/questforge_menu_night_v8.ogg` — **shipped** menu cue, 140 s loop. Installed as `music.menu`.
- `out/groan_v8_excerpt.ogg` — 12–40 s of v8: v7 quake plus distant kaiju throat.
- `out/questforge_menu_night_v7.ogg` — previous listen (quake only). Kept for A/B.
- `out/groan_v7_excerpt.ogg` — 12–40 s of v7.
- `out/questforge_menu_night_v6.ogg` — previous listen (louder/fried/closer). Kept for A/B.
- `out/groan_v6_excerpt.ogg` — 12–40 s of v6.
- `out/questforge_menu_night_v5.ogg` — previous listen (same timbre, quieter peak). Kept for A/B.
- `out/groan_v5_excerpt.ogg` — 12–40 s of v5.
- `out/questforge_menu_night_v4.ogg` — previous listen (same timbre, quieter peak). Kept for A/B.
- `out/groan_v4_excerpt.ogg` — 12–40 s of v4.
- `out/questforge_menu_night_v3.ogg` — previous listen (round-5 late quiet build). Kept for A/B.
- `out/groan_build_excerpt.ogg` — 12–44 s of that rejected v3 build.
- `src/crickets_freesound_746366_CC0.mp3` — the cricket bed source (kept so the build is reproducible).
  `src/crickets_freesound_320145_CC0.mp3` — alternate, sparser and with more low rumble; unused.
- `out/*_v1.*`, `out/*_v2.*` — earlier versions kept for reference.

## Credits / licensing
- Cricket bed: "Southern Summer Evening Ambience with Crickets 5" by **RyanKingArt**, freesound.org sound
  **746366**, **CC0 / public domain**. No attribution is legally required; credited here for provenance.
  The file used is the site's high-quality mp3 preview (44.1 kHz stereo, ~147 kb/s), high-passed at 180 Hz
  and tiled with 1.5 s crossfades. If you want the lossless original, it needs a free freesound login.
- Loading anvil strikes (v4): "Anvil #1" by **Pablo BERGEL**, BigSoundBank **#3589**, **CC0**.
  Working-smith hits, distance-treated in `chant_v4.py`. Lossless flac in `src/`.
  v3 used Duasun freesound **321889** (CC0) plus a modal ring; that stem was rejected.
- Everything else in both cues is synthesized here, so the pack owns it outright. Nothing needs a credit line
  in `1-Read-Me-First/README.md` as things currently stand.
- `install_menu_music.py <track.ogg> [--live]` — rewrite-the-zip helper. **Not used for ship.**
  Live install was a surgical `zip` add of `sounds.json` + the ogg only, so existing pack
  entries (buttons, mural assets) were not recompressed.

Audition on the Mac: `afplay out/questforge_menu_night_v8.wav`
Short groan excerpt: `afplay out/groan_v8_excerpt.wav`

## Looping in-game
- Splash: `Clip.loop(LOOP_CONTINUOUSLY)` is sample-accurate, the seamless file just works.
- Menu: `MusicTickerTransformer` sets MENU min/max delay and the initial wait to 0, so the
  shipped 140 s file loops immediately.

## How each cue gets into the game

### Main menu — resource pack only, no code
1.7.10 plays the vanilla `music.menu` event on the title screen. `assets/minecraft/sounds.json` in
`QuestForge.zip` (already the only enabled pack) with `"replace": true` swaps the four vanilla tracks for ours:

```json
"music.menu": { "category": "music", "replace": true,
  "sounds": [ { "name": "music/menu/questforge_menu", "stream": true } ] }
```

Caveat: vanilla `MusicTicker` waits 100 ticks (5 s) before the first play and 1–30 s between repeats.
For the "sharp drop" that is too long. Fix = one more transformer in `tools/questforge-coremod`
(same POP/ICONST pattern as the BetterQuesting one) setting the initial delay field to ~20 ticks and the
menu gap to 0–40 ticks. The drone itself starts with ~1 s of silence, so the hard cut still reads.

### Loading screen — needs a splash patch (the Forge jar is already patched, so this is the same workflow)
The splash runs before OpenAL/paulscode exists, so it cannot use the game's sound engine. Plain
`javax.sound.sampled` works at that point (Java Sound, CoreAudio under Rosetta, DirectSound on Windows):

- add one small class to the patched Forge jar, e.g. `cpw/mods/fml/client/SplashMusic` with
  `static void start()` (open `resources/assets/minecraft/sounds/music/splash.wav` as a `Clip`, gain −6 dB,
  `loop(LOOP_CONTINUOUSLY)`, swallow all exceptions) and `static void stop()` (`clip.stop(); clip.close()`);
- inject `INVOKESTATIC SplashMusic.start` at the top of `SplashProgress.start()` and `SplashMusic.stop` at the
  top of `SplashProgress.finish()` using the `ClassFile` helper in `_emblem-pulse/apply_pulse.py`;
- compile the class with `/Library/Java/JavaVirtualMachines/jdk1.8.0_162.jdk/Contents/Home/bin/javac -target 1.6`
  so it matches the jar's class version 50.

Ship the loading cue as **WAV** (Java Sound has no Vorbis decoder without pulling in jorbis by hand).
A 60 s loop at 44.1 kHz/16-bit stereo is ~10 MB; 32 kHz mono is ~3.8 MB and is fine under a splash.
Stopping the clip in `finish()` is what produces the hard cut; do not fade it.

Splash and menu are two different audio stacks, so there is nothing to hand off. The only timing knob is the
`MusicTicker` delay above.

## Sourced candidates (if not composing)

Loading screen (chant + drums):
- Pixabay "Epic Viking Battle Music with War Drums and Nordic Chant" (VikingMusic, 2:54) — Pixabay Content
  License, no credit needed. Page discloses it is AI-generated. Closest to the brief of anything found.
- Alexander Nakarada (CC BY 4.0, credit line required in pack notes): "The Vikings", "Mjolnir", "Fólkvangr",
  "The Northern Path" (3:21, 90 bpm, dark/mystic, *instrumental, no chant*). Good drums and scale, no voices.
- Nothing on free-stock-music's Viking page is tagged with vocals; real chant under a free license is rare.
  If you want actual voices, generate it (Suno/Udio prompt: "slow Nordic male chant, taiko, D minor, 70 bpm,
  no melody lead, loopable, 60 s") or commission.

Main menu (drone):
- OpenGameArt CC0 "Horror Atmosphere" (no melody, pure atmosphere) and the CC0 Dark Music collection
  (josepharaoh99: "Derelict", "Loaben").
- Kevin MacLeod / incompetech "Ominous" and his Horror/Dark Ambient set (CC BY 4.0 or paid no-credit license).
- Honestly the synthesized drone above is already the right thing; sourced drones will be generic by comparison.

Licensing note: the pack already carries a CrazyCraft rebrand; anything CC BY needs a credits line in
`1-Read-Me-First/README.md`. CC0 / Pixabay need nothing.

## Status
**Shipped pair (2026-09-04), both looping. Relaunch Prism.**

- **Menu v8** — Java Sound `Clip.LOOP_CONTINUOUSLY` on
  `resources/.../music/menu.wav` (same samples as the shipped ogg). Vanilla
  `music.menu` cannot sample-loop (stream stop+replay = the silent break).
  `MusicTickerTransformer` now skips vanilla MENU play and calls
  `SplashMusic.onMusicTick()`. CustomMenu.jar was not rewritten.
- **Loading chant v4** — same splash Clip path and v3 chant/seam. Anvil stem
  rebuilt from BigSoundBank #3589 (no modal sines). Five irregular distant
  rings. Hard cut into the menu is unchanged. `splash.wav` is 44.1 kHz stereo.

Backups in `minecraft/_qf-backups/`:
`forge-binlib.jar.bak-before-splash-music-20260904-224156`,
`forge-prism.jar.bak-before-splash-music-20260904-224156`,
`QuestForgeTweaks-1.0.jar.bak-before-menu-loop-20260904-224156`.
