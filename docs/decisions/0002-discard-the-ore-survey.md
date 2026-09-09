# 0002 — Discard the ore survey and re-measure from finished chunks

**Date:** 2026-09-08
**Status:** accepted

## Decision

Every ore figure in `pack/reports/` and on the published ore atlas is void. Do
not filter, rescale or patch them. Re-measure by generating chunks with the live
mod set and counting the region files.

## Why

Three independent faults, each sufficient on its own.

### The survey measured a pack nobody plays

`server/README.md` states it outright: the survey server "runs HBM's ore mod
that the live pack does not, drops ChocolateQuest, and adds JourneyMapServer."
Verified — `server/config/` carries `hbm.cfg`, `hbmTemplate.json`,
`MobProperties/hbm` and a JAS handler for hbm, while the live pack has no hbm
jar and does ship `chocolateQuest-1.7.10-1.1d.jar`.

Both differences move ore counts:

- hbm is an **ore mod**. Its veins convert the same stone every other ore is
  competing for. A controlled A/B with hbm as the only variable measured
  **+4% overall density, +6% on coal** when it was removed.
- ChocolateQuest carves **underground dungeons**, and mod generators run
  *after* vanilla ore is placed (`GameRegistry.generateWorld` is called once
  `ChunkProviderGenerate.populate` has returned). Its absence means ore that
  would have been destroyed was counted.

Neither appears in `disabled-mods.md`, whose stated rule is that a mod is only
removed "if it cannot place a block in the world". Both broke that rule. The
logs show ChocolateQuest was never *dropped* — it was never loaded at all.

All three world saves older than 2026-09-06 also have hbm in their
`FML.ModList`, so they cannot substitute as ground truth.

### Vein size was treated as a block count

`WorldGenMinable(block, size)` does not place `size` blocks. `size` parameterises
the ellipsoid it traces. Transcribed from the 1.7.10 source and run standalone
against pure stone:

| nominal size | 3 | 4 | 6 | 8 | 16 | 32 |
|---|---|---|---|---|---|---|
| blocks placed | 0.47 | 2.37 | 4.41 | 5.81 | 20.04 | 104.47 |

Non-linear, and far above nominal past size 16. The pipeline converted size to
blocks using one global factor measured across all ores, so anything derived
that way is wrong by up to 6×. The residual it was absorbing ranged 12%–84% with
no structure; the corrected model
(`veins/chunk × G(size) × stone(band)`) leaves a term that clusters 59–85% and
tracks depth — two ores sharing y0–15 both land on 63%.

### Whole mods were absent, and "unmeasurable" ones were not

The block survey listed ores from six mods. Scanning a current world finds
**1Legends ore among the most abundant in the pack** — `redIronOre` 77
blocks/chunk, `cassiteriteOre` 68, `copperOre` 66 — none of it in the old
dataset. VoltzEngine and Railcraft's poor ores, published as "varies by region"
because their measured rates swung 4×–180× between seeds, scan cleanly at 25.1,
23.8 and 30.2 per chunk. VoltzEngine in particular declares its entire
distribution in `content/voltzengine/ores/*/world.json`
(`minY`, `maxY`, `branchSize`, `chunkLimit`).

Separately, rows blended distinct call sites: `minecraft:diamond_ore = 1.954
veins, size 6.51` averages two or more generators into one that does not exist.
Non-integer rates and fractional vein sizes are the tell.

The two instruments meant to cross-check each other overlapped on **17 of 213**
blocks.

## What replaces it

Generate with the real game and the real mod set; count what is in the chunks.
Tooling and full procedure: [`../survey/README.md`](../survey/README.md).

The region files are **kept**. They are the measurement, and a new question —
per biome, per depth, a different definition of "ore" — becomes a re-scan of
data already on disk instead of another multi-hour run. Baking the analysis into
the generation run is what made the old pipeline both slow to question and hard
to audit.

Static extraction of the generators is retained, but only as a narrow validator:
confirming an ore absent from a sample is genuinely absent, pinning rates too
rare to count, and explaining figures on the page. It is not the source of
truth, because it would require reading 31 classes, resolving config fields, and
modelling terrain interaction, per-provider sequencing and post-hoc overwrite —
five places to be silently wrong.

## Consequences

- The published ore atlas is wrong and should not be cited until re-measured.
- Any comparison across a mod-set change is invalid. Re-measure instead.
- `server/config/` still encodes the old server's hbm-bearing delta. Do not
  reuse it; `build_server.py` rebuilds from the live instance every time,
  which is what stops the drift recurring.
