# Ore survey runbook

Everything needed to produce the per-ore, per-dimension, per-biome, per-depth
dataset the ore webpage is built from. Written to be executed unattended on the
Windows box.

**Read this whole file before running anything.** The previous ore dataset was
thrown away in full, and the reason was not a bad calculation. It was a server
whose mod set nobody checked. Gate 1 is that check. Do not skip it to save
twenty minutes.

## What "done" means

For every ore block, in every dimension, per populated chunk:

- blocks per chunk, split by Y level
- the same split by biome, wherever a dimension has more than one
- the number of populated chunks behind each number, so precision is visible
- an explicit list of ores whose sample is too thin to publish

Numbers must describe **the pack as players run it**. That is the whole
requirement. Anything that changes what ends up in the ground -- a mod present
or absent, a config difference, a world type -- invalidates the result silently.

---

## Prerequisites

| | |
|---|---|
| the live pack instance | a Prism instance that passes `verify_pack.py` |
| `minecraft_server.1.7.10.jar` | **not** part of a client install; see below |
| a Java 8 runtime | any vendor on Windows |
| Python 3 | for the three survey scripts |
| free disk | ~6 GB per seed. Three seeds ≈ 18 GB |

The vanilla server jar is not in the repo (`*.jar` is gitignored) and Prism does
not install one for a client instance. Get it from Prism (Edit Instance →
Version → install the server) or resolve it through Mojang's
`version_manifest_v2.json`. **Verify it is 9,605,030 bytes** before using it --
that is the size of the known-good copy.

### One argument trap, because two scripts disagree

```
verify_pack.py   --instance <instance dir>              # the dir holding minecraft/
build_server.py  --instance <instance dir>\minecraft    # the minecraft/ dir itself
```

`build_server.py` exits with a clear error if you give it the wrong one. Nothing
catches the reverse.

---

## Gate 1 — prove the instance is the pack

This gate exists because the discarded dataset was measured on a server running
HBM's ore mod, which the pack does not have, and missing ChocolateQuest, which
the pack does. HBM's ore competes for the same stone; ChocolateQuest carves
dungeons *after* ore is placed. Every number that server produced described a
mod set no player has ever played.

```powershell
git pull
python tools\verify_pack.py --instance "<instance dir>" --repo .
```

Require `0 failed`. If a custom mod is stale, build and install it
(`docs/development/building-on-windows.md`) before continuing — a survey of the
wrong jar is worth nothing.

Then build the server:

```powershell
python tools\survey\build_server.py ^
  --instance "<instance dir>\minecraft" ^
  --out server\runtime-seed1 ^
  --vanilla "<path to minecraft_server.1.7.10.jar>" ^
  --seed 1 --force
```

It prints `mods: N kept, 10 dropped` and writes `BUILT-FROM.txt`. Now check the
result rather than trusting it:

1. **Kept + dropped must equal the instance's own `mods\` jar count.** Do not
   compare against a number from an earlier run — the pack gains mods.
2. **ChocolateQuest must be present** in `server\runtime-seed1\mods\`.
3. **No HBM / `hbm` jar may be present.**
4. Exactly the ten client-only mods listed in `build_server.py` were dropped,
   and nothing else.

If any of those four is wrong, **stop and report**. Do not generate.

> ChocolateQuest's jar in the live instance is byte-patched (its hardcoded
> enchantment ID 52 clashes with SSTOW; the live copy is patched to 53).
> `build_server.py` copies the instance's jar, so the patch carries over. If you
> ever replace that jar from a download, launch breaks.

---

## Gate 2 — pilot, and validate the instrument

Never start an eight-hour run on an unvalidated instrument.

```powershell
python tools\survey\pregen.py --server server\runtime-seed1 --dim 0 --radius 20
python tools\survey\scan_regions.py server\runtime-seed1\survey --dim 0 -o pilot-dim0.json
```

That is 1,681 chunks, a few minutes. Then check three things:

**a. Ore exists at all.** If vanilla coal, iron, gold, redstone, diamond and
lapis are not all present in quantity, generation ran without population and
everything downstream is void. (`pregen.py` deliberately avoids Chunk
Pregenerator's `TerrainOnly` mode for exactly this reason — ore is placed during
population. If you ever drive the server by hand, do not use `TerrainOnly`.)

**b. Vanilla rates are right.** Vanilla overworld ore is the one part of this
system with a known answer, so it is the instrument's calibration. The
generation parameters are literals in `BiomeDecorator.generateOres()`:

| ore | attempts/chunk | Y range | vein size |
|---|---|---|---|
| coal | 20 | 0–128 | 16 |
| iron | 20 | 0–64 | 8 |
| gold | 2 | 0–32 | 8 |
| redstone | 8 | 0–16 | 7 |
| diamond | 1 | 0–16 | 7 |
| lapis | 1 | centred on 16 | 6 |

Derive expected blocks/chunk from `WorldGenMinable`'s own geometry and compare.
**`size` is a shape parameter, not a block count** — the ellipsoid it fills
yields far fewer blocks than `size` for small values and more for large ones
(≈0.47 blocks at size 3, ≈20 at size 16). Treating size as a count is one of the
three faults that invalidated the last dataset.

As a loose sanity bound only — not an acceptance threshold — diamond should land
around 3–4 blocks/chunk and coal well over 100. If you are an order of magnitude
out, something is wrong with the scan, not with the game.

**c. The biome split is populated.** `pilot-dim0.json` must carry per-biome
counts with sensible names. If biomes are absent or all-one-value, fix that
before the full run — re-scanning is cheap, re-generating is not.

Report the pilot numbers before proceeding.

---

## Gate 3 — the full run

Three tiers, because a dimension with one biome and three ores does not need the
sample the overworld needs.

**Tier A — the overworld.** Biome-specific numbers are the binding constraint
here; the pack has a large biome count (TragicMC alone registers biomes across
IDs 94–128), and a biome occupying 1% of the world only yields ~1,600 chunks out
of 160,801.

```powershell
python tools\survey\pregen.py --server server\runtime-seed1 --dim 0 --radius 200
```

**Tier B — dimensions that carry ore.** 19 dimensions, radius 100 = 40,401
chunks each.

```powershell
python tools\survey\pregen.py --server server\runtime-seed1 --radius 100 ^
  --dim -1 --dim 1 --dim 7 --dim 31 --dim 32 --dim 33 --dim 34 --dim 35 ^
  --dim 36 --dim 51 --dim 58 --dim 66 --dim 80 --dim 81 --dim 82 --dim 83 ^
  --dim 85 --dim -37 --dim -42
```

**Tier C — the ten that previously read zero.** Radius 50 = 10,201 each.

```powershell
python tools\survey\pregen.py --server server\runtime-seed1 --radius 50 ^
  --dim 2 --dim 3 --dim 4 --dim 30 --dim 50 --dim 53 --dim 55 --dim 84 ^
  --dim -38 --dim -39
```

**Re-confirm these zeros; do not inherit them.** The list came from the
invalidated run. The structural half of the argument survives — `WorldGenMinable`
only converts its target block, so a dimension not built from stone yields
nothing however many veins are attempted — but "this mod set produces zero here"
does not, because a mod that was missing before can place ore in a dimension
that previously read empty. A false zero silently deletes a dimension from the
webpage.

Roughly 1,030,000 chunks per seed. The Mac measured 36 chunks/s; a 7900X should
beat that comfortably, but time it on Tier C first and extrapolate rather than
trusting an estimate.

Two mechanical notes:

- `--task-timeout` is **per dimension** and defaults to 36000 (10 hours). Tier A
  is a single 160,801-chunk task; if your measured rate puts it near that, raise
  the flag rather than discovering the truncation afterwards.
- Negative dimension ids work as written (`--dim -1`); argparse reads them as
  values, not flags. Verified, not assumed.

### Dimension reference

All 30, names resolved (27 from `LoadingPlates.java`, validated against the
server's own registry; 2 and 3 from `pack/config/TragicMC.cfg`):

```
 -42 The Lost World      -1 The Nether        30 Outer Space       58 Imortus
 -39 Mirror World         0 Overworld         31 Mars              66 The Underworld
 -38 Torment              1 The End           32 Ilum              80 Utopia
 -37 Dream World          2 The Collision     33 Hurikane          81 Extreme Mining
                          3 Synapse           34 Tython            82 Village Mania
                          4 Compact Machines  35 Korriban          83 Danger Islands
                          7 Twilight Forest   36 Tatooine          84 Crystal
                                              50 Speed Force       85 Chaos
                                              51 Wakanda
                                              53 Kingpin Takedown
                                              55 Quantum Realm
```

---

## Gate 4 — scan

```powershell
python tools\survey\scan_regions.py server\runtime-seed1\survey -o scan-seed1.json
```

Reads the finished region files off disk. Block IDs are per-world and come from
`level.dat`'s `FML/ItemData`, so names come from the save being scanned rather
than from any assumption about mod load order. Only chunks with
`TerrainPopulated=1` are counted — an unpopulated chunk has terrain but no ore,
and counting one silently dilutes every rate.

Re-scanning is seconds. A new question — a different depth banding, a different
definition of "ore" — is a re-scan, not another generation run. The region files
are the measurement; keep them.

---

## Gate 5 — check the denominators, then top up

For every (ore, dimension, biome) cell that will be published, read the chunk
count behind it out of the scan.

Rough guide: relative error ≈ 1/√(number of veins observed). An ore at one vein
per 200 chunks yields four veins in 800 chunks — that is noise, not a
measurement. **The rare ores are exactly the ones the page most needs to be
right about**, so set the target per ore from its own rate, not one flat number
per dimension.

Where a cell is thin, re-run `pregen.py` for that dimension at a larger radius.
Chunk Pregenerator skips chunks that already exist (it reports `Chunks Skipped`),
so extending a world is incremental, not a restart.

Produce an explicit **insufficient-sample list**. An ore with a wide error bar
must be labelled that way on the page, not quietly rounded into a confident
number.

---

## Gate 6 — repeat on two more seeds

```powershell
python tools\survey\build_server.py --instance "<instance dir>\minecraft" ^
  --out server\runtime-seed2 --vanilla "<jar>" --seed 2 --force
```

...then Gates 3–5 again, and once more for seed 3.

Per-biome rates should not vary by seed — generation is conditional on biome, so
the seed changes which biomes appear and where, not the rate within one. That is
precisely what makes seeds a good check: **if per-biome rates disagree across
seeds by more than their error bars, something is wrong**, and it is better to
find that in the data than after publishing.

Run seed 1 through Gate 5 completely and report before starting seed 2. If
something is wrong, it is wrong for all three.

---

Three mods need a specific verdict out of this. `build-ore-guide-data.py`
carries `UNSTABLE_MODS = {voltzengine, railcraft, hardcoreenderexpansion}`,
recorded because their measured rates swung **4x to 180x between seeds with the
mod set held constant**. That was observed on the discarded instrument, so it is
now an open question with two very different answers: either their generation
really is that unstable, in which case those ores can never carry an exact number
and the atlas must say so — or it was an artefact of the old measurement, in
which case they can. Three seeds is exactly the experiment that settles it.
**Answer it explicitly.**

---

## Gate 7 — the names and ore-dictionary dump

`scan_regions.py` reads block ids out of the save's own `level.dat`, so it
produces registry names like `TragicMC:tungstenOre`. The atlas needs two things
it cannot produce:

- **display names** — "Tungsten Ore". Localisation lives in lang files, keyed
  through `tile.<name>.name`, and metadata blocks need a per-meta lookup.
- **ore-dictionary tags** — `oreTungsten`. These are what group a dozen mods'
  copper into one row, and they are also *the only non-arbitrary answer to "is
  this block actually a mineable ore?"*. `WorldGenMinable` places plenty that is
  not: OreSpawn alone puts about a hundred mob-spawn blocks through it, and four
  mods generate stone variants the same way. An `ore...` registration is the
  game's own statement that a block is mineable ore.

Only a running game produces this. The mechanism already exists — `/qfsurvey`
(`com/questforge/content/survey/`) writes `qfcontent-orenames.txt` in the form:

```
# modid:block:meta = the name shown in game | oreDict,tags
```

Read `CommandOreSurvey.java` for the exact subcommand. **This dump is still
valid** — it is a registry dump, not a measurement, so it is not affected by
what invalidated the old dataset. It does still have to be taken on the correct
mod set, so take it from the same instance Gate 1 verified.

Note it covers ores the vein hook never sees: Railcraft's poor ores and
VoltzEngine's metadata blocks never pass through `WorldGenMinable`, and keying
names off vein observations leaves exactly those nameless.

---

## Gate 8 — get it into the atlas

**This does not currently connect, and the runbook is not finished until it
does.**

- `site/ore-atlas/index.html` is a 345 KB self-contained page with its ore data
  **inlined** as `ORES = [...]`. Every number in it came from the discarded
  survey. There is no separate data file to swap.
- `tools/survey/build-ore-guide-data.py` reads **three `.txt` files in the old
  in-game format** (`qfcontent-oreveins.txt`, `qfcontent-oresurvey.txt`,
  `qfcontent-orenames.txt`). It will not read `scan_regions.py`'s JSON.

So someone has to write the bridge from scan JSON to the atlas. When doing it,
**port `build-ore-guide-data.py`'s classification logic rather than rewriting
it.** That file records real, hard-won decisions about which blocks count as
mineable ore — its own comments note the rule started as a regex over registry
names and that every rule had a counterexample ("...Block" is a storage block
except when it is `OreSpawn_OreAmethystBlock`; Superheroes Unlimited registers
ores as `blackIronOre`). Throwing that away means rediscovering it.

What changes: rarity now comes from **measured blocks per chunk in finished
chunks** for every ore, so the old fallback — scaling a nominal vein block count
by an estimated shortfall factor for ores the block survey could not see — should
disappear rather than be ported. The new scan sees every block in the world
regardless of which generator placed it, which is strictly better: it counts ore
from structures, custom generators and anything else, none of which a
`WorldGenMinable` hook can observe.

---

## What to hand back

1. `scan-seed{1,2,3}.json` — the raw per-dimension scans.
2. A merged dataset: per ore, per dimension, per biome, per Y band —
   blocks/chunk, with the populated-chunk count behind each figure.
3. Per-biome chunk counts per dimension (the denominators, on their own).
4. The insufficient-sample list from Gate 5.
5. The Tier C result: which of the ten really are empty under the current mod
   set, and which are not.
6. Cross-seed agreement: per-biome rates from the three seeds side by side.
7. `BUILT-FROM.txt` from each server, and the Gate 1 mod-set check output.
8. `qfcontent-orenames.txt` from Gate 7.
9. The verdict on VoltzEngine, Railcraft and Hardcore Ender Expansion: stable
   across seeds, or genuinely unpublishable.

Keep the region files until the dataset is accepted.

## If something looks wrong

Say so and stop. The failure mode that cost this project a full dataset was not
a wrong number that looked wrong — it was a wrong number that looked completely
reasonable, for two days, because nothing compared the thing being measured
against the thing it was supposed to be. Every gate above is one of those
comparisons. Report gate output even when it passes.
