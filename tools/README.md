# Tools

Generators and analysis scripts. Everything here produces something — an asset, a
measurement, a rewritten config — and the output is not committed. If you need a
render, run the generator.

These were consolidated from a flat scratch directory where each experiment got its
own dated folder (`_splash-4k-buffer`, `_music-20260904`, `_buttons-iron-20260904`,
and nineteen more). The names below describe what the tool does; the date it was
written is in git.

## `trial/` — boot only what a test needs

`trial.py` builds a throwaway client or server with the base visual/performance set plus the
mods a test names, enforces one client at a time and a shared RAM budget, bisects, and is the
only sanctioned way to install a jar into the live pack. See [`trial/README.md`](trial/README.md).

## `lite-client/` — the pack on weaker PCs

`apply-lite.ps1` switches a friend's client to the lite or potato profile (same content,
lighter video settings, client-only jars moved aside) and back. See
[`lite-client/README.md`](lite-client/README.md).

## `branding/` — pack art

The title screen, splash, icons and buttons. Most scripts render to PNG and then
install into the resourcepack at [`../pack/resourcepack/`](../pack/resourcepack/),
which is where the shipped versions live.

| Directory | What it generates |
|---|---|
| `menu-background` | The main-menu background plate. |
| `splash-buffer` | The Forge splash-screen buffer patch, plus the high-resolution mural that goes in it. Includes two Java probes for the buffer size. |
| `splash-bars`, `splash-fix`, `splash-boot-fix`, `splash-hires`, `splash-knight-glow` | Successive passes on the boot splash — layout, resolution, the knight artwork and its glow. |
| `buttons-iron`, `buttons-stone`, `buttons-concepts` | Menu button treatments. `buttons-concepts` holds the rejected directions. |
| `icons` | Instance and window icons at every required size. |
| `loading-plates` | The rotating loading-screen plates. |
| `emblem-pulse` | The animated pack emblem. |
| `hero-art` | Character art sourced from the Legends Mod models. |
| `optifine-morph` | OptiFine-specific rendering adjustments. |
| `pack-branding` | The assembled resourcepack: wordmark, BQ theme, icons. |
| `legacy-crazycraft` | Branding from the pack this one grew out of. Kept for reference. |

## `music/` — menu audio

Python synthesis for the title-screen music: a chant that plays over the splash and
a drone that takes over on the menu. `synth.py` is the engine; `chant_v*.py` and
`menu_v*.py` are the arrangements; `make_seamless_loop.py` handles looping and
`install_menu_music.py` places the result.

Renders are **not** committed — the scratch folder this came from held ten versions
of the same track at 20–44 MB each. Run the arrangement to get the audio back.

## `survey/` — measuring the pack

Ore distribution and pack composition.

The **current** ore pipeline is five scripts, run in this order, and is documented
step by step in [`../docs/survey/README.md`](../docs/survey/README.md):

| script | job |
|---|---|
| `build_server.py` | assemble a headless server from the live instance |
| `PatchCCL.java` | null-guard CodeChickenLib — **without it every pregeneration run crashes within seconds** |
| `pregen.py` | drive Chunk Pregenerator over stdin, one dimension at a time |
| `scan_regions.py` | count every block in the finished region files, per dimension / Y / biome |
| `aggregate_scans.py` | average several seeds into a rate with an honest standard deviation |

The `merge-*.py` scripts and `cross-check-survey.py` belong to the **previous**
survey, whose numbers were discarded — see
[decision 0002](../docs/decisions/0002-discard-the-ore-survey.md). They sum that
instrument's `qfcontent-*.txt` files and are not part of the pipeline above; keep
them only for reading the old evidence.

`pack-census/` drives the in-game `/qfcensus` command, which is the only reliable
source for facts like which enchantment IDs are occupied — see
[decision 0001](../docs/decisions/0001-chocolatequest-enchantment-id.md) for why
static analysis is not a substitute.

Output lands in [`../pack/reports/`](../pack/reports/).

## `balance/` — combat analysis

`qfcombat.py` is the one to reach for. It reads the TSV that
[`/qfcensus combat`](../docs/survey/combat.md) writes from the running game and
turns it into the three decisions the output exists to support: which
enchantments are mis-tuned for their rarity, which are mis-*implemented* (firing
at a rate that does not match their own `getProcChance`), and what the loot
weights should be if rarity is to track measured power rather than intent. It
models nothing and knows no enchantment's rules.

```bash
python tools/balance/qfcombat.py <census-config-dir>     # full report
python tools/balance/qfcombat.py <dir> --procs           # just the bug check
python tools/balance/qfcombat.py <dir> --loot --csv out.csv
```

`qfsim.py` and `qfbench.py` came first and simulate gear and enchantment
combinations against the pack's armour and damage values; `bench_output-*.txt`
are recorded runs and `geardig_raw.txt` is the extracted gear table.

They are kept for exploring a change before making it, and they are **no longer
evidence**. Both are a second implementation of rules that live in Java, so they
can be exactly right the day they are written and quietly wrong one commit later,
with output that looks identical either way. That is the same reason
`enchantment-ground-truth.md` exists. Where a simulation and a census disagree,
the census wins.

Every number any of these produce must trace to a file in the pack, or to a
measurement. A simulation built on a guessed constant is worse than no
simulation.

## `pack-fixes/` — config and quest surgery

One-off scripts that rewrite pack files in place: quest book restructuring, the
settings fix, the quest-55 repair, and the performance overlay. They are kept
because they document what was changed and can be re-run after a pack update.

## `spikes/` — throwaway experiments, kept

Standalone probes written to answer one question:

| Spike | Question it answered |
|---|---|
| `armor-probe` | How the armour damage pipeline actually resolves, including the `ISpecialArmor` path. |
| `audio` | Whether `javax.sound` could carry the jukebox. |
| `spotify` | Whether a Spotify Connect remote was viable, and whether Java 8u162's cacerts could complete the TLS handshake. |
| `capture` | Screen capture for the branding work. |
