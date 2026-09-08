# Tools

Generators and analysis scripts. Everything here produces something — an asset, a
measurement, a rewritten config — and the output is not committed. If you need a
render, run the generator.

These were consolidated from a flat scratch directory where each experiment got its
own dated folder (`_splash-4k-buffer`, `_music-20260904`, `_buttons-iron-20260904`,
and nineteen more). The names below describe what the tool does; the date it was
written is in git.

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

Ore distribution and pack composition. The merge scripts combine runs from the four
survey-server nodes; `cross-check-survey.py` verifies two independent runs agree.

`pack-census/` drives the in-game `/qfcensus` command, which is the only reliable
source for facts like which enchantment IDs are occupied — see
[decision 0001](../docs/decisions/0001-chocolatequest-enchantment-id.md) for why
static analysis is not a substitute.

Output lands in [`../pack/reports/`](../pack/reports/).

## `balance/` — combat simulation

`qfsim.py` and `qfbench.py` simulate gear and enchantment combinations against the
pack's actual armour and damage values. `bench_output-*.txt` are recorded runs;
`geardig_raw.txt` is the extracted gear table.

Every number these produce must trace to a file in the pack. A simulation built on
a guessed constant is worse than no simulation.

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
