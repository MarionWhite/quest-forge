# Measuring ore generation

How to produce trustworthy per-ore, per-dimension, per-biome, per-depth numbers
for the pack — and why the previous ones should not be used.

---

## Why the old numbers were discarded

Three independent problems, each enough on its own.

**1. It measured a pack nobody plays.** The old survey server ran HBM's ore mod,
which the live pack does not have, and never loaded ChocolateQuest, which it
does. HBM's ore competes for the same stone every other ore is converting; a
controlled A/B put the effect at **+4% overall density, +6% on coal**.
ChocolateQuest carves dungeons *after* ore is placed, deleting some of it. The
server's own `disabled-mods.md` says a mod is only removed "if it cannot place a
block in the world" — both changes broke that rule, and neither was recorded in
it. All three world saves that predate 2026-09-06 have hbm loaded too, so they
are unusable for the same reason.

**2. Vein size was treated as a block count.** `WorldGenMinable(block, size)`
does not place `size` blocks — `size` is a shape parameter for the ellipsoid it
traces. Transcribing the generator and running it in isolation, the blocks a
vein actually places into pure stone are:

| nominal size | 3 | 4 | 6 | 8 | 16 | 32 |
|---|---|---|---|---|---|---|
| blocks placed | 0.47 | 2.37 | 4.41 | 5.81 | 20.04 | 104.47 |

Wildly non-linear, and far *above* nominal past size 16. The old pipeline
converted size to blocks with a single global factor, so figures derived that
way can be wrong by up to 6×.

**3. Whole mods were missing.** The old block survey listed ores from six mods.
A scan of a current world finds **1Legends ore among the most abundant in the
pack** — `redIronOre` at 77 blocks/chunk, `cassiteriteOre` at 68, `copperOre` at
66 — and none of it appears in the old dataset at all. VoltzEngine and
Railcraft's poor ores, written off as "unmeasurable, varies 4×–180× between
seeds", scan cleanly at 25.1, 23.8 and 30.2 per chunk.

## The approach now

Generate chunks with the **real game and the real mod set**, then count what is
in them. No modelling, no inference, no hooks in the generation path.

The region files are **kept**. They are the measurement, and they can be
re-scanned in seconds when the question changes — per biome, per depth, a
different definition of "ore". The old pipeline baked its analysis into the
generation run, so every new question meant another multi-hour run and another
chance for a counting bug to slip through unnoticed.

---

## Prerequisites

- **Java 8**, 64-bit. Not 11, not 17. Set `JAVA8_HOME`, or pass `--java`.
  On Apple silicon a *native arm64* JDK 8 is correct and fast: a dedicated
  server needs no LWJGL, so it never touches Rosetta.
- **Python 3.8+**. Standard library only — nothing to install.
- **Disk**: roughly 1 GB per 25,000 chunks generated.
- **RAM**: 6 GB per server. On 32 GB, run **4 concurrent jobs** and leave the
  rest for the OS.

## Step 1 — get the pack

The mod jars are not in this repository (GitHub's file limits, and they are
third-party). They ship as a release asset:

```
https://github.com/MarionWhite/quest-forge/releases
```

Download `questforge-instance.zip` and unpack it. The directory containing
`mods/` and `config/` is what the next step wants.

> Do **not** rebuild the pack by re-downloading mods from CurseForge. At least
> one jar is hand-patched — ChocolateQuest's enchantment id is byte-edited from
> 52 to 53 to stop it colliding with SSTOW — and a clean copy breaks launch.

## Step 2 — build the server

```bash
python3 tools/survey/build_server.py \
    --instance /path/to/pack/minecraft \
    --out      /path/to/qf-server \
    --forge    /path/to/forge-1.7.10-10.13.4.1558-1.7.10-universal.jar \
    --vanilla  /path/to/minecraft_server.1.7.10.jar \
    --libraries /path/to/forge/libraries
```

It copies every mod except ten client-only ones (renderers, HUDs, cosmetics),
each listed with a reason, and writes `BUILT-FROM.txt` recording what was
dropped. **The server is rebuilt from the pack, never maintained by hand** —
that is what stopped the last one from drifting into a different mod set.

Expect `mods: 105 kept, 10 dropped`. If ChocolateQuest is missing, something is
wrong: it must be present.

## Step 3 — pregenerate

```bash
python3 tools/survey/pregen.py --server /path/to/qf-server --dim 0 --radius 100
```

Starts the server, waits for it to boot, drives Chunk Pregenerator over stdin,
waits for the task to report finished, and stops cleanly. `--dim` repeats.

`--radius` is in chunks around the origin: radius 100 is a 201×201 square, about
**40,000 chunks**.

> The generation type is deliberately left at the default. Chunk Pregenerator
> offers `TerrainOnly`, which is much faster — and useless here, because ore is
> placed during **population**, not terrain generation. A TerrainOnly world
> contains no ore at all.

## Step 4 — count

```bash
python3 tools/survey/scan_regions.py /path/to/qf-server/survey -o scan.json
```

Reads the region files directly and emits, per dimension, every block type with
its total, its distribution by Y level, and its distribution by biome. Only
chunks with `TerrainPopulated=1` are counted — an unpopulated chunk has terrain
but no ore, and counting it would dilute every rate.

Block ids are read from the world's own `level.dat` (`FML/ItemData`), because
Forge assigns them per world. Entries are retained for removed mods, so a world
still names its blocks correctly even if a mod has since gone.

---

## Which dimensions are worth generating

30 exist; **14 carry ore**. Ten register vein attempts and place *nothing* —
`WorldGenMinable` only converts its target block, so in a dimension not built
from stone the generator runs its whole loop and produces nothing.

| | dimensions |
|---|---|
| **Real ore** | 0, -1, -37, -42, 7, 33, 34, 51, 58, 80, 81, 82, 85 |
| **Trace only** (<2 blocks/chunk) | 1, 31, 32, 35, 36, 66, 83 |
| **Nothing placed** | 2, 3, 4, 30, 50, 53, 55, 84, -38, -39 |

Known ids: 4 = CompactMachines, 7 = TwilightForest, 80–85 = OreSpawn,
−37/−38/−39 = Witchery. The rest are config-driven or passed as parameters and
need a runtime dump to name.

## Running it on a 32 GB PC

One dimension generates on one thread, so the way to use twelve cores is
**several servers at once**, each on its own copy and its own port.

```bash
for d in 0 -1 7 34; do
  python3 tools/survey/build_server.py --instance PACK --out srv-$d --force ...
  python3 tools/survey/pregen.py --server srv-$d --dim $d --radius 100 --xmx 6G &
done
wait
```

Four jobs at 6 GB each fits 32 GB with headroom. Measured on an M1 under load:
**36 chunks/s** for a single job. Expect meaningfully better per-job on a 7900X,
times four jobs.

**Use several seeds, not just more chunks.** Ore density varies by seed because
terrain does. A very large sample from one seed is precise *about that seed* and
says nothing about the spread a player will actually meet. Three to five seeds
give the mean *and* an honest variance — set `level-seed` in `server.properties`
or pass `--seed` to `build_server.py`.

**How many chunks is enough.** Roughly 400 observed veins gives ~5% precision,
so `chunks ≈ 400 × vein_size / blocks_per_chunk`:

| ore rate (blocks/chunk) | chunks needed |
|---|---|
| 100 | ~100 |
| 1 | ~2,000 |
| 0.1 | ~20,000 |
| 0.01 | ~200,000 |

100,000 chunks per dimension resolves everything down to about 0.02
blocks/chunk. Below that, report the uncertainty rather than a clean figure.

## Troubleshooting

**Server exits immediately.** Almost always Java: check `java -version` is 1.8
and 64-bit. The log is `pregen.log` in the server directory.

**Boot takes minutes.** Normal — 132 mods. A cold boot measured 18.6s on an M1
with a warm cache, longer on first run.

**`Pregenerated: 0 Chunks`.** The area was already generated. Delete the world
folder (`survey/`) or raise `--radius`.

**Counts look low.** Check `unpopulated_skipped` in the scan output. A large
number means generation was interrupted and those chunks have terrain but no
ore.

**Numbers differ from an earlier run.** Confirm the mod set did not change.
Adding or removing any mod that places blocks invalidates the comparison — that
is exactly how the previous dataset went wrong.
