# Performance plan — "my PC should not be the floor"

Status: **plan plus ready client profiles ([`tools/lite-client/`](../../tools/lite-client/)).
Nothing has been installed and no config is changed.** The lite profile
described in section 2 was written for OptiFine E7; since 2026-10-25 the pack's
client is Angelica and the profiles are the JSON files in
`tools/lite-client/profiles/` (full, lite, potato: Angelica settings plus the
QuestForge shader presets), applied by `apply-profile.ps1` and documented in
[`../setup/performance-tuning.md`](../setup/performance-tuning.md). The
measurements and the per-mod costs below still hold. Measured 2026-10-16
overnight on the 7900X / RTX 5070 Ti, with the census servers loading the CPU.
Load times below are wall-clock and so carry some of that noise. The baseline
was booted at the start and at the end of the run, and both came out the same
(7–8 s to the title screen, 111 MB live heap).

The goal has two parts:

- **(A)** A supported lite client for friends' ordinary PCs (4–6 cores,
  8–16 GB RAM, GTX 1060 or integrated graphics). It runs the same content and
  joins the same server.
- **(B)** Wins for everyone that cost neither content nor looks.

Inputs used: [`../setup/performance-tuning.md`](../setup/performance-tuning.md),
[`../setup/jvm-args.md`](../setup/jvm-args.md), the 2026-09-04 pass
([`tools/pack-fixes/performance/REPORT.md`](../../tools/pack-fixes/performance/REPORT.md)),
the shader work in [`shaders/`](shaders/) (quest-forge-58) and its benchmark
results, and quest-forge-02's modernization report.

## 1. Where the time and memory go

### Headline facts

| What | Number | Source |
|---|---|---|
| Full-pack load to title screen (7900X) | **84 s** (07:34:58 → 07:36:22, live `latest.log` of 2026-10-16) | live log |
| Full-pack live heap in a loaded world, after full GC | **1,321 MB**, metaspace 223 MB, at `-Xmx3G` | quest-forge-58, `L-A0-3G` |
| Same under Angelica | 1,368 MB, metaspace 267 MB | quest-forge-02 / 58, `L-B0-3G` |
| Block atlas / item atlas | **2048×2048 each** (16 MB RGBA each, ~22 MB with 4 mip levels) | live log, `Created:` lines |
| Atlas sprites across all jars | 11,269 PNGs, 10.5 Mpx in total | jar scan |
| Shaders off vs Vibrant High vs Enhanced Default, 1440p, 5070 Ti | 436 / 158 / 195 fps (static scene), 327 / 118 / 149 (flying) | 58, `m-A0`, `m-A1`, `L-A3` |
| 4 cores / 8 threads instead of 24 threads (shaders off) | 457 / 341 fps: no change | 58, `L-A0-4c` |

What this means:

- **Heap is not the floor.** The whole pack, singleplayer, with its integrated
  server, lives in 1.3 GB. A 3 GB heap fits on an 8 GB PC. The user's 7 GB
  heap is far more than the pack needs.
- **The texture atlas is not the problem either.** Before measuring, the guess
  was that Legends (84 MB), TragicMC (105 MB) and MCHeli (257 MB) would blow up
  the atlas. They don't. TragicMC's 105 MB is 101 MB of sound. Legends and MCHeli
  are big because of entity and armour textures and models, which stay out of
  the atlas. The two atlases, plus OptiFine's normal and specular copies when a
  shader is on, total about 110 MB of VRAM.
- **The frame budget is CPU-side and shader-bound.** The shader pack is the
  biggest single lever. Vibrant costs 2.8× and Enhanced Default 2.2× over no
  shader. Core count does not matter until clock speed does (58's stand-in kept
  full clocks).

### Per-mod cost (slim trials, title screen, `-Xmx3G`, shaders off)

Each trial is the base set (OptiFine, FastCraft, BetterFps, FastLeafDecay,
AIImprovements, SoundFilters, QuestForgeTweaks) plus the named mods. "Live" is
the used heap after the forced full GC that `jcmd GC.class_histogram` runs.
Deltas are against the base.

| Trial | Live heap | Δ heap | Metaspace | Title (s) | Atlas blocks / items | Main live objects |
|---|---|---|---|---|---|---|
| base | 111 MB | — | 31 MB | 7–8 | 1024×512 / 256×256 | — |
| **+ Decocraft** | 675 MB | **+564** | 33 | 14 | unchanged | 8.1 M `craftstudio.libgdx.Vector3` (194 MB), their arrays, about 300 MB of `byte[]`: every prop's model, CPU side, kept forever |
| **+ MCHeli** (with `assets\mcheli`) | 342 MB | **+231** | 34 | 14–16 | 1024×1024 / **2048×1024** | 3.0 M `W_Vertex`, 2.0 M `W_TextureCoordinate`, 0.66 M `W_Face`: every vehicle model parsed at startup |
| **+ Legends** (5 hero packs) | 322 MB | **+211** | 65 | 11 | 1024×512 / 1024×512 | 2.2 M `PositionTextureVertex`, 0.4 M `TexturedQuad`: armour models built at startup |
| + OreSpawn, Decocraft, CustomNPCs, Witchery, Jungle, LittleMaid, Chisel, InventoryPets | 754 MB | +643 (≈ +79 without Decocraft) | 58 | 19–20 | **2048×1024** / 1024×512 | Decocraft as above |
| + HEE, Railcraft, Twilight Forest, Transformers, TARDIS, ICBM, Psychedelicraft, Recurrent Complex, BiblioCraft, OpenBlocks | 245 MB | +134 | 62 | 12–13 | 1024×1024 / 1024×512 | spread out |
| + TragicMC | 129 MB | +18 | 36 | 7 | — | — |
| + Lycanites (all 13 packs) | 129 MB | +18 | 36 | 7 | 1024×512 / 512×512 | — |
| + every client-only mod except OptiFine (CustomMenu, DamageIndicators, MobDismemberment, MobAmputation, InventoryTweaks, Controlling, JourneyMap) | 130 MB | +19 | 38 | 13 | — | VRAM +57 MB, nearly all CustomMenu's 11 Mpx of button art |

Roughly 1,000 of the pack's 1,321 MB live heap comes from three mods: **Decocraft
(~43%), MCHeli and Legends.** All three build every model at startup and keep
it forever, whether anyone ever places that prop or flies that jet.

The per-mod deltas add up to about 1.39 GB, close to the measured 1.32 GB in a
world. That is a sanity check that nothing large was missed.

**Trap found on the way:** MCHeli reads its vehicles from
`<game dir>\assets\mcheli` (357 MB, 1,528 PNGs, 507 `.mqo` models), not from
`MCHeli.zip`. A Prism instance without that folder boots without complaint but
has no aircraft, and its 2048-wide item atlas shrinks to 512. The
client-instance release must carry `assets\mcheli`, and any slim trial that
tests MCHeli has to copy it in. Copy it rather than hard-linking, because MCHeli
writes `sounds.json` and `lang\*` into it. `tools/trial` does not do this today.

### Textures outside the atlas (VRAM, loaded the first time something is drawn)

| Jar | Non-atlas texture pixels | Largest |
|---|---|---|
| MCHeli (`assets\mcheli` holds the same art) | 762 Mpx (~3 GB if every vehicle were seen) | `tanks/aat.png` 2048², about 700 at 1024² |
| Legends | 728 Mpx | `sum/textures/gui/spiderman2099/hud.png` **4983×3417** (68 MB in VRAM; above the 4096 limit of some 2011 iGPUs), armour sheets 2250×1500 |
| OreSpawn | 20 Mpx | King / Queen 2048² |
| Lycanites | 14 Mpx | Rahovart 1024² |
| CustomMenu | 11 Mpx | 1800×240 buttons |
| QuestForge.zip (our resource pack) | 4.4 Mpx | 1800×240 menu art; **no block textures at all** |

1.7.10 uploads an entity texture the first time it is drawn and never frees it.
VRAM therefore grows over a session with how many *different* vehicles, hero
suits and bosses you have seen, not with the mod count. A 3 GB GTX 1060 has
room. An iGPU takes this from system RAM, which is one more reason the lite
heap is 3 GB and not 4.

**The QuestForge resource pack does not need a low-resolution version.** It has
no block or item textures, only title-screen art, a quest-book theme and music.

### Load time

84 s on the 7900X with no single hog. The largest single gaps are 7 s inside
LittleMaid's model scan and about 1 s each for the two mipmap passes. 3,022
lines of caught stack traces are printed during load, mostly soft-integration
`ClassNotFoundException`s from Witchery, ModTweaker2 and SecretRooms. In slim
trials MCHeli (+7 s, mostly scanning a 270 MB zip), Decocraft (+7 s) and the
client-only set (+5 s) are the costly ones. Expect 2–3 minutes on a friend's
4-core CPU. The lite profile saves only the client-only set's few seconds.

### Known 1.7.10 hot spots for these mod versions (not measured here)

| Where | Why it costs | What helps |
|---|---|---|
| Shader shadow pass | Every chunk and entity drawn twice. E7 can't drop entities from it | quest-forge-58's own pack; Enhanced instead of Vibrant |
| Mob-dense scenes (Lycanites, OreSpawn bosses, JAS cap 70) | Per-entity model rendering is the main-thread cost in modded 1.7.10 | Fewer entities (server side), fast graphics, no gore entities |
| MCHeli vehicles | Large `.mqo` models drawn in immediate mode every frame | Nothing client-side; just know each vehicle in view costs |
| Decocraft-heavy builds | One model per prop | Same |
| BiblioCraft shelves, StorageDrawers, Iron/Crystal chests | Item-on-face tile entity renderers redraw the items every frame | Fewer in one room |
| OptiFine Dynamic Lights | Each moving light source re-renders the chunks around it | Off in lite |
| Hats (`randomMobHat=10`) | 10% of mobs carry a hat model | Client config; left alone, it's flavour |
| JourneyMap | Background re-rendering of map tiles as chunks change | Already de-tuned in the 09-04 pass; potato drops it |
| Smooth FPS | `glFinish` every frame | Off (see win #2) |

## 2. The lite client

Ready to use in [`tools/lite-client/`](../../tools/lite-client/). It has been
tested against a scratch copy of the live options files: apply, potato and
undo all restore byte-identical files. It has not been installed anywhere.

**Content is identical by construction.** The script only:

1. Moves jars that are on `CLIENT_ONLY` in `tools/server/build_play_server.py`,
   so the server never has them.
2. Rewrites video keys in `options.txt`, `optionsof.txt` and `optionsshaders.txt`.

It never touches `config/`. OptiFine stays, because it is the performance mod.

| | Lite (GTX 1060-class, 8–16 GB) | Potato (iGPU, 8 GB), on top of lite |
|---|---|---|
| Mods out | SoundFilters, MobDismemberment, MobAmputation, CustomMenu | + JourneyMap, DamageIndicators |
| Kept | InventoryTweaks, Controlling (no measurable cost) | same |
| Shader | Off. Fast Render on (only legal with shaders off). Optional: Enhanced Default at 0.5× shadows with Fast Render off | Off |
| Render distance | 6 = the server's `view-distance`. The server sends nothing past 6, so 8 only draws the hard edge past the fog | 5 |
| Graphics | Fast (opaque leaves, fast clouds, rain, water, trees and dropped items), smooth lighting Minimum, particles Decreased, smooth biomes off, dynamic lights off, Smooth FPS off, vignette off | + smooth lighting off, particles Minimal, clouds off, CTM off, no stars, no rain splash or particle extras |
| Mipmaps / anisotropic | 2 / off | 0 / off |
| FPS cap | 90 (keeps laptops out of thermal throttling) | 60 |
| Java | `-Xmx3G` on 8 GB, 4G on 12–16 GB; G1, no pinned GC thread counts (`jvm-args.txt`) | 3G |

**Expected footprint, lite on an 8 GB PC:**

- Java heap: 1.3 GB live (measured, full pack) inside a 3 GB cap.
- Java process: about 4–4.5 GB in total. Heap plus about 250 MB of metaspace,
  the code cache, and LWJGL, OpenAL and driver memory. The title-screen trials
  ran 1.2–2.8 GB of working set at heap committed 1–1.8 GB.
- VRAM: about 50 MB at the menu. In play, the 2048² atlases (~45 MB) plus the
  entity textures you have seen (about 100–400 MB in a normal session). No
  shader buffers.
- Load time: unchanged (2–3 minutes on a 4-core CPU). The dropped mods save
  about 5 s.

**Expected frame rate.** Nobody has friend-class hardware here, so this is an
estimate. Most of the gain comes from shaders off: 2.2–2.8× by 58's numbers.
Fast graphics, Fast Render, dynamic lights off, Smooth FPS off and RD 6 add a
further 20–40% on a CPU-limited machine. That figure is typical for OptiFine on
1.7.10 and was **not measured in this pack**. The dropped mods save CPU in
fights (sound occlusion rays, gib entities) and about 20 MB of heap and 57 MB
of VRAM. **Verify** with 58's `FrameBench` by running live options vs. lite
options on the same scenes. That is an A/B the existing harness can do with
`-Shader OFF` and an options overlay, interleaved because of census load.

**Angelica was adopted** (2026-10-17; section 4 was written before). The
Angelica-era profiles (2026-10-25) keep the drop list, render distance 6 (5),
Fast graphics, particles, mipmaps and the 3 GB heap from this table, drop the
OptiFine keys (`ofFastRender`, `ofSmoothFps`, `ofFastMath` and `optionsof.txt`
as a whole do not exist under Angelica), add Celeritas's own levers
(biome blend, grass quality, texture filter, smooth lighting, dynamic lights,
the FPS reducer) and, instead of "shaders off", select the QuestForge pack's
Low (lite) or Potato preset, which are built for exactly this hardware. The E7
profile stays as the fallback for GL-3.3-less GPUs, now as the `optifine`
section of the same JSON files. Angelica's scaling with cores (1016 vs 457 fps
static, shaders off, 4 cores) is what a friend's 4-core CPU needs. iGPU
behaviour and a mixed-renderer join are still untested.

## 3. General wins for everyone, ranked

None of these touch content. "Measured" means measured in this pack. Every
other gain is an estimate.

| # | Change | Gain | Risk | How to verify |
|---|---|---|---|---|
| 1 | **Ship the current QuestForgeTweaks jar** (`GlErrorTransformer`, built 2026-10-16) in the client release | Measured by 58: Vibrant went from 22–30 fps to 140–170 fps (75% of render-thread time was a stderr print) | None; already in the live instance | Check the release tarball's `QuestForgeTweaks-1.0.jar` contains `GlErrorTransformer.class` |
| 2 | **`ofSmoothFps:false`** (live has it on since the 09-04 pass) | Removes a per-frame `glFinish` stall. Typically 0–10% average and better 1% lows; no visual change | Very low. Old AMD drivers sometimes stutter more without it | FrameBench static and fly, on vs off, interleaved ×2 |
| 3 | **Client render distance 6 on the friends' server** (keep 8 in singleplayer) | Free: the server sends 6 chunks anyway. Fog now lands on the world's edge instead of showing it | None | Look at the horizon on the server at 8 vs 6 |
| 4 | **Heap: stop at 4–5 GB, `-Xms` 1–2 GB** for every client | The live set is 1.3 GB. 7 GB only adds to the RAM pressure that bites when the user runs a client and test servers together. Same pause target | Low. Keep 7 GB if the user likes; it doesn't hurt frame rate | GC log or 58's `-LiveHeap` after an hour of play |
| 5 | **Shader tier = hardware tier.** Vibrant on the 5070 Ti only. Enhanced Default at 0.5× shadow for mid cards. Off for lite. 58's own pack replaces this when it lands | 2.2–2.8× (measured, 58) | None | Already measured |
| 6 | **FPS cap** 260 → monitor refresh (e.g. 144) | Lower GPU heat and power, steadier frame pacing. No visible loss above the refresh rate | None | GPU power in `nvidia-smi` at the menu and in-world |
| 7 | **Release must include `assets\mcheli`** (357 MB) | Correctness, not speed: without it MCHeli silently has no vehicles | None | `dir assets\mcheli\helicopters` in a friend's instance |
| 8 | **Decocraft lazy model load** — **done 2026-10-25**: qf-tweaks `DecoLazyTransformer` frees each prop's per-rotation vertex arrays and decoded texture after startup and rebuilds them on first use | **Measured −491 MB live heap at the title screen (674 → 183), −460 MB in a world with props placed (653 → 193), −465 MB on a dedicated server (580 → 115).** ~~About −550 MB live heap (measured cost) and about −6 s load~~ — load time unchanged, 14 s to the title screen either way: the work is still done at startup, only the results are dropped | Low after measurement: props render identically on first sight; the rebuilt geometry was verified bit for bit against Decocraft's own (799,008 node-rotations, 0 mismatches). Switch: `config/qftweaks.cfg` `decocraft.lazyModels=false` | Done (see "Win #8, measured" below). Not yet installed into the live pack or the server; the jar goes in through `trial.py install` |
| 9 | **MCHeli / Legends lazy models**: the same idea | −231 / −211 MB (measured cost) | Medium–high: both are large closed-source mods | Same, per mod |
| 10 | `-XX:+ParallelRefProcEnabled` (in the lite args) | Small. Modded 1.7.10 holds many weak and soft references (caches, WeakHashMaps), and this parallelises their processing in GC pauses | Very low; standard G1 flag on Java 8 | GC log pause times |
| 11 | Quieter load: patch or blacklist the soft-integration `ClassNotFound` dumps (3,022 lines) | About 1–2 s of load | Low | Load-log timestamps |

### Win #8, measured (2026-10-25)

Slim trial `decolazy` (base set + Decocraft + the qf-content debug jar for the
scene), `-Xmx3G`, `--shader off`, 1920×1080, the same superflat world both
times; the patched run is the same jar with the switch on. Live heap is the
`jcmd` full-GC method, now `trial.py heap`. In-world means eleven props of
different tile types placed in two rows (decobench, chair, barrel, candle stick
with its particle emitter, bed, door, jukebox, stained glass, Christmas tree,
tea set, faucet; Decocraft's own placement rule refused a hanging lantern on
open ground in both runs), the camera 10 blocks back.

| | Stock Decocraft | Lazy models | Δ |
|---|---|---|---|
| Client, title screen | 674 MB | 183 MB | **−491 MB** |
| Client, in the world with the props placed | 653 MB | 193 MB | **−460 MB** |
| Dedicated server (base set + Decocraft) | 580 MB | 115 MB | **−465 MB** |
| `Vector3` objects alive | 8.08 M (185 MB) + their arrays (56 MB) | 96 K (2.3 MB) in-world | |
| `byte[]` alive (the decoded textures live here) | 261 MB | 39–45 MB | |
| Load to the title screen | 14 s | 14 s | none |

What the patch does: Decocraft's `CraftStudioModelWrapper` constructor still
computes the 16 placement rotations of every node (that is where the wrapper's
own extents, item scales and resource costs come from), but the per-node corner
arrays behind them are dropped once the constructor is done; the rotation a
prop is drawn or collided with is recomputed once, under the wrapper's lock,
from Decocraft's own matrix chain, and kept. Each of the 794 models' decoded
PNG keeps being uploaded to the GPU at the two startup reloads and is then
dropped; the raw PNG bytes (10.7 MB in total) stay, so F3+T decodes them
again (that reload now costs a second or two more). Nothing else changes:
placement rules, collision boxes, item rendering and the Decobench's resource
costs come from the same numbers as before. With `-Dqf.decolazy.verify=true`
the helper recomputes every rotation of every wrapper at startup and compares
with Decocraft's arrays: 799,008 node-rotations, 0 mismatches, 312 ms.

What did not happen: the hoped-for ~6 s of load time. Decocraft's startup cost
is the computation (16 rotations × 50 K nodes, 794 PNG decodes, a full-pixel
colour scan per prop for the Decobench, two mipmap uploads), not the keeping;
this patch only changes the keeping. Deferring the colour scan and the
texture decode is possible (both feed public fields read by a handful of
Decobench call sites) and would be a second, smaller patch.

The slim-trial numbers predict the full pack: Decocraft was 564 MB of the
1,321 MB live heap measured in a loaded world, so the full pack should land
near 850 MB. Worth measuring once the jar is installed (`trial.py heap` on a
full-pack boot).

Considered and **not** recommended (keeping REPORT.md's verdicts, with reasons):

- **FoamFix, Hodgepodge, UniMixins, ArchaicFix, Neodymium, Entity Culling** on
  E7. FoamFix's author doesn't support OptiFine and it breaks HBM-style
  renderers. The mixin stack is the modernization path (section 4), not a drop-in
  next to E7 and FastCraft.
- **A second FastCraft, or removing FastCraft.** 1.25 is the OptiFine-shader
  build. `asyncCulling=true` is already on.
- **`-XX:+UseStringDeduplication`.** Plausibly saves 5–10% of heap, but heap
  isn't the floor. It could not be A/B tested here, because `trial.py` cannot
  pass JVM flags. Not worth an untested flag.
- **Xmx 8 GB or more, Java 8 builds newer than the tested 8u241, Java 17+**
  without the modernization stack.
- **Turning down Hats, Lycanites particles or TragicMC overlays for everyone.**
  These are flavour. Leave them to a per-player choice.

## 4. What depends on the modernization decision

quest-forge-02's report: both renderers fit 3 GB. Angelica scales with cores
and E7 doesn't. Angelica needs GL 3.3 core (a GTX 1060 or any 2012+ iGPU is
fine; Intel HD 2000/3000 must stay on E7). A client without Angelica,
Hodgepodge or lwjgl3ify is accepted in principle, but a mismatched join is
untested and GTNHLib may be needed on both sides.

| Recommendation here | If Angelica is adopted |
|---|---|
| #1 GlErrorTransformer | Dead code under Angelica. Our four `Config.isShaders` checks need an Iris check too (02's list) |
| #2 Smooth FPS, Fast Render, Fast Math, the whole `optionsof.txt` profile | Gone. Angelica has its own settings; the Angelica profiles are `tools/lite-client/profiles/*.json` (2026-10-25) |
| #5 shader tiers | Complementary LOW under Angelica beat Enhanced under E7 (260 vs 195 fps static, measured by 58). The tier table moves to Angelica-compatible packs |
| #8–9 lazy models | Unchanged; #8 is done and measured (2026-10-25), #9 still worth it |
| Lite drop list, render distance 6, 3 GB heap, ParallelRefProc | Unchanged (Angelica +95 MB heap, +44 MB metaspace) |
| FastCraft / BetterFps "keep" | Angelica force-disables them |
| LittleMaid's model scan | Needs the `MmmScan` fix (already in qf-tweaks) under UniMixins |
| E7 lite | Stays as the fallback for GL-3.3-less GPUs |

## 5. Open questions for the user

1. **Turn Smooth FPS off in the live instance?** (#2.) It's a one-line change.
   Should it be A/B tested with FrameBench first?
2. **Should a friend's release be checked for `assets\mcheli` and the
   2026-10-16 QuestForgeTweaks jar?** (#1, #7.) Both are invisible when missing.
3. ~~**Worth a qf-tweaks patch for Decocraft's eager model build?** (#8.)~~
   Built and measured 2026-10-25: −460 to −491 MB on the client, −465 MB on
   the server. Open now: **install it** (client release and the friends'
   server, through `trial.py install`), and whether to spend a second patch on
   Decocraft's load time.
4. **The lite drop list removes JourneyMap only in potato.** Is the minimap
   essential enough to keep it even there?
5. **Modernization.** If Angelica is chosen, the lite profile is rewritten for
   it, and E7 lite becomes the fallback.

## Method notes

- Slim trials via `tools/trial/trial.py`, `-Xmx3G`, `--shader off`, one at a
  time, never inside another session's benchmark sequence (the driver waited
  for three quiet minutes first). 13 boots, all trials removed afterwards.
- Heap: `jcmd GC.heap_info` before and after `jcmd GC.class_histogram` (which
  forces a full GC even with `-XX:+DisableExplicitGC`). VRAM: Windows "GPU
  Process Memory" counters. Load phases from `latest.log` timestamps.
- Win #8 (2026-10-25): one before/after client cycle in trial `decolazy`
  (another agent held the client slot for the first minutes; the launch retried
  until it was free), two server boots in `decolazy-srv`. The scene is
  `tools/trial/make_flat_world.py` plus qf-content's `AutoPlace`; the patched
  run found the props already in the saved world from the baseline run and
  rendered them from disk, which is the case that matters (a built house
  loading), so the two screenshots are the same scene. Histograms and both
  screenshots: `C:\qfb\decocraft-lazy\` on the Windows PC. Title-screen probes
  ran within a second of the world starting to load, on an empty flat world.
- One Legends boot died in `OpenAL64.dll` during the back-to-back sound-engine
  restarts of the two resource reloads. The retry was clean. It is a native
  race seen once, not attributed to Legends.
- Frame rates are all quest-forge-58's (`C:\qfb\matrix-results.txt`,
  `lowend-results.txt`), taken while the census servers ran.
  The 1.4 s worst frame in `L-A0-3G` / `L-B0-3G` probably comes from that
  harness's own forced full GC, not from the 3 GB heap. That is unconfirmed.
- The jar scan and log analysis scripts are throwaway (session scratchpad). The
  numbers above are their output.
