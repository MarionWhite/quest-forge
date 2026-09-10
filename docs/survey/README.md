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
LegendsMod ore is **among the most abundant in the pack** and appears nowhere in
the old dataset at all. Measured over 4 seeds and 165,525 Overworld chunks:
`redIronOre` **72.6**/chunk, `copperOre` **65.4**, `cassiteriteOre` **64.6**.
(An earlier single-world scan quoted 77, 68 and 66; the four-seed figures
supersede it.)

VoltzEngine and Railcraft's ores, written off as "unmeasurable, varies
4×–180× between seeds", are in fact among the *steadiest* things in the pack:
`veStoneOre` 93.7 ±9.8 and `veGemOre` 56.4 ±7.8, and `Railcraft:ore` 20.07 ±1.56
summed over its ten metadata values. Most ores land under 6% coefficient of
variation across seeds; the "4×–180×" swing was an artefact of the old
instrument, not of worldgen.

> An earlier revision of this file said those three "scan cleanly at 25.1, 23.8
> and 30.2 per chunk". **Nothing reproduces those figures.** Railcraft's poor
> ores are metadata 8, 9 and 10 of `Railcraft:ore`, measured at 0.66, 2.46 and
> 0.96 blocks/chunk; the block's largest component is metadata 7 at 11.69. The
> three numbers are left here only so nobody re-derives them from the same
> source.

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
- **A Forge server install**, which the pack does not contain. The client
  instance has only `bin/lib/forge-…-universal.jar`, and that jar alone gets you
  `ClassNotFoundException: net.minecraft.launchwrapper.Launch` — it needs the
  vanilla server jar and a maven `libraries/` tree beside it, which the Forge
  *installer* produces and the universal jar does not fetch:

  ```bash
  V=1.7.10-10.13.4.1558-1.7.10
  curl -O "https://maven.minecraftforge.net/net/minecraftforge/forge/$V/forge-$V-installer.jar"
  java -jar "forge-$V-installer.jar" --installServer
  ```

  That leaves `minecraft_server.1.7.10.jar` and `libraries/` in the working
  directory; pass both to `build_server.py`. The client's `bin/lib/` is a flat
  directory, not a maven layout, and will not substitute.

**On Windows**, two more things:

- **Path length.** With `LongPathsEnabled` unset, building a server under a deep
  directory fails with `WinError 206` partway through copying mods —
  CarpentersBlocks' nested cached-resource directories are ~145 characters on
  their own. Keep the server root short, e.g. `C:\qfs\n1`.
- **A JDK 8**, not just a JRE, if you need to re-apply the CodeChickenLib patch
  below (`javac`/`javap`). Java 8 on `PATH` is enough to *run* a server.

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

Expect `mods: 109 kept, 10 dropped` (it was 105 when this was first written —
the pack has grown; the ten dropped are the fixed client-only list). FML then
reports **132 mods** loaded, which counts the coremods and libraries the jars
bring with them. If ChocolateQuest is missing, something is wrong: it must be
present.

It also copies `config/`, `scripts/`, `structures/` and — importantly —
`legends/`.

> **Six dimensions are prebuilt maps, not generated terrain.** LegendsMod ships
> `legends/maps/{outerspace,tython,korriban,tatooine,kingpinTakedown,dim54}`
> (132 MB) and copies the relevant one into the world the first time dimension
> 30, 34, 35, 36, 53 or 58 loads. Miss that directory and the failure is
> **completely silent from the survey's point of view**: the mod logs one
> `FileNotFoundException` among thousands of boot lines, the dimension still
> registers and still loads, pregeneration still reports `40000 chunks, 0
> failed` — and not one region file is written. Two of the six are dimensions
> this document classifies as carrying real ore, so the run looks complete
> while six dimensions are quietly missing.
>
> The check that catches it is counting region files per dimension afterwards,
> not reading the pregen output. A generated dimension at `--radius 100` should
> have **64** region files (chunks −100…100 span regions −4…3 on each axis).
> Zero means this.
>
> Because these are fixed maps, their ore is whatever the shipped map contains.
> The sample is the map's own extent, not the radius you asked for, and there is
> no seed-to-seed variance to report — the same map is copied every time.

## Step 3 — patch CodeChickenLib (required)

**Without this the server dies a couple of seconds into every pregeneration
run.** It boots fine and idles fine, so it looks like a pack bug rather than a
survey one.

`codechicken.lib.world.WorldExtension.unloadChunk` is:

```java
chunkMap.get(chunk).unload();     // line 52, no null check
```

On a dedicated server `WorldExtensionManager.onChunkDataSave` *removes* a
chunk's entry whenever the saved chunk is unmodified, and `onChunkUnLoad` then
dereferences the result anyway. Pregeneration saves and unloads chunks
constantly, so it dereferences null almost immediately:

```
java.lang.NullPointerException
    at codechicken.lib.world.WorldExtension.unloadChunk(WorldExtension.java:52)
    at codechicken.lib.world.WorldExtensionManager$WorldExtensionEventHandler.onChunkUnLoad
```

ForgeMultipart's `TickScheduler` is the only thing that registers a
`WorldExtension`, and it is not removable — it places blocks and other mods
depend on it. **Do not fix this by dropping a mod.** A changed mod set is
exactly what voided the previous survey; see
[`../decisions/0002-discard-the-ore-survey.md`](../decisions/0002-discard-the-ore-survey.md).

Patch the library instead. `tools/survey/PatchCCL.java` null-guards the six
accessors that lack the check, matching the `ifnull` CodeChickenLib's own author
already wrote for `unwatchChunk`. It only skips bookkeeping for chunks the map
has already forgotten, so it cannot move a block of worldgen.

```bash
ASM=libraries/org/ow2/asm/asm-all/5.0.3/asm-all-5.0.3.jar
CCL=srv/mods/1.7.10/CodeChickenLib-1.7.10-1.1.3.138-universal.jar

javac -cp "$ASM" -d build/ccl tools/survey/PatchCCL.java
java -cp "build/ccl:$ASM" PatchCCL "$CCL" CodeChickenLib-patched.jar
cp CodeChickenLib-patched.jar "$CCL"
```

It prints the six methods it guarded and exits non-zero if the class it
expects is missing, so a CodeChickenLib version bump cannot silently skip
the fix. On Windows use `;` instead of `:` in `-cp`.

Repeat for every node. **Patch the survey servers only — never the live
instance.** `build_server.py` copies the pack's unpatched jar every time, so
re-apply this after every rebuild.

## Step 4 — pregenerate

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

**Throughput: leave `--time-per-tick` alone.** Chunk Pregenerator will spend at
most `TimePerTick` milliseconds of each tick generating, and ships set to 40, so
on a dedicated server with nobody on it the generator sits out most of every
tick. `pregen.py` raises it to **250** after boot, which is the figure the mod's
own help text calls "the most optimal speed that you can gain". Measured on the
Nether here: **5.5 chunks/s at 40, 156 chunks/s at 250** — a 28× difference, and
the reason a full-pack survey is a few hours rather than a few days.

This cannot bias the result. It changes how much of each tick is spent
generating, not what gets generated: the same generators run against the same
seed in the same order either way.

**Interrupted runs resume themselves.** Unfinished tasks are persisted to
`survey/data/PregenTaskStorage.dat`, and with `AutoStart` on the server picks
them up as soon as the world loads — so a killed run comes back on the next
boot, ahead of what you actually asked for, and the log says:

```
Pregenerator already running. Adding Task to the TaskStorage
```

From that point the completion lines `pregen.py` waits on belong to the wrong
task. It now sends `pregen stop` and `pregen clear` immediately after boot so
every run starts from an empty queue. If you drive the server by hand, do the
same, or delete `PregenTaskStorage.dat` first.

## Step 5 — count

```bash
python3 tools/survey/scan_regions.py /path/to/qf-server/survey -o scan.json
```

Reads the region files directly and emits, per dimension, every block type with
its total, its distribution by Y level, and its distribution by biome. Only
chunks with `TerrainPopulated=1` are counted — an unpopulated chunk has terrain
but no ore, and counting it would dilute every rate.

**`unpopulated_skipped` should come out at roughly the perimeter of the square
you generated**, and that is a free check that the run finished. A chunk is
populated only once its +X/+Z neighbours exist, so the outermost ring never is.
For `--radius 100` the perimeter is 4×201−4 = 800, and the four seeds here
skipped 788, 989, 918 and 954. A number far *above* that means generation was
interrupted and a swathe of chunks has terrain but no ore.

> One residual effect this does not remove: `WorldGenMinable` places veins
> centred 8 blocks into the +X/+Z neighbour, so a populated chunk sitting next
> to an unpopulated one misses part of that neighbour's spill-in. It affects
> only the outermost populated ring — about 2% of the sample, losing a fraction
> of one neighbour's contribution — so it moves a dimension-wide rate by well
> under 1%, an order of magnitude below the ~5% precision the sample sizes
> below are chosen for. It is worth knowing about before anyone reads too much
> into the third decimal place.

Block ids are read from the world's own `level.dat` (`FML/ItemData`), because
Forge assigns them per world. Entries are retained for removed mods, so a world
still names its blocks correctly even if a mod has since gone.

Counting a chunk means walking up to 65,536 block positions in Python, so this
is CPU-bound and runs **one dimension per worker process** — `--jobs` sets how
many (default: one per core, `--jobs 1` stays single-process). A full 30-
dimension pack scan is minutes rather than the couple of hours it takes
serially, which is what makes "re-scan instead of re-generating" true in
practice rather than just in principle.

**Dimensions are identified by their save folder, and two of them are not called
`DIMn`.** A `WorldProvider` may return anything from `getSaveFolder()`, and
TragicMC's two do: dim 2 saves to `Collision/` and dim 3 to `Synapse/`. The
scanner used to treat "no `DIMn` in the path" as the overworld, which counted
every block in both dimensions as Overworld ore and lost dims 2 and 3 entirely.
It now resolves the folder up front and **stops** on one it cannot name:

```
unrecognised dimension folder(s) holding region files: Foo. Name them with
--dim-folder NAME=ID.
```

To find the id, generate that dimension alone into an empty world and see which
folder takes the region files — the pregenerated area is obvious against the
single spawn region every other dimension gets. Then pass
`--dim-folder Foo=42`, or add it to `DIM_FOLDERS` in the script.

## Step 6 — average across seeds

```bash
python3 tools/survey/aggregate_scans.py scan-n*.json --all-dims --ores-only \
    --names docs/survey/dimension-names.tsv --depth --biomes -o ore-rates.json
```

One scan describes one seed. This averages the per-chunk rates across seeds and
reports the standard deviation and coefficient of variation beside each one, so
a figure that is really seed-dependent cannot be quoted as though it were not.
Rates are averaged, never summed, and an ore absent from one seed counts as 0.0
for that seed rather than as a missing sample.

`--depth` and `--biomes` are what turn the scan's `by_y` and `by_biome` tallies
into the per-depth and per-biome numbers this document promises. Without them
that data is collected and thrown away.

**Depth** is reported as the full Y band an ore occupies, where it peaks, and
the band holding the middle 90% of it — `1-111 (pk 9, 5-67)` for coal. That is
the number a player digs to, and it is *measured*, not read off a generator's
configured height range, so it already accounts for veins losing the
competition for stone near the extremes of their band.

**Biome** is reported as **enrichment**, not as a raw share. A biome covering
40% of a dimension will hold roughly 40% of every ore in it for no interesting
reason, so the raw share says almost nothing. Enrichment divides an ore's share
of its own blocks in biome B by biome B's share of all blocks counted in that
dimension: 1.0 means the ore ignores biome, 3.0 means three times the
concentration you would expect there. Most vanilla ores come out at 1.0, which
is the correct answer and a useful check that the statistic is not inventing
signal.

> The `merge-*.py` scripts in `tools/survey/` are **not** for this. They sum the
> old, discarded instrument's `qfcontent-*.txt` files and have nothing to do
> with region scans.

**What counts as an ore.** `"ore" in name` is wrong here and quietly so: this
pack ships OreSpawn, which prefixes its mod id onto every one of its block
names, so `OreSpawn:OreSpawn_CrabSpawnBlock` and `..._TomatoPlant1` match it —
about 150 mob-spawn, crop and decoration blocks counted as ore. Matching
`machine_core` is the same mistake from the other side. So names are split into
camelCase/underscore tokens and a block is an ore only if a whole token is
`ore`. Run with `--audit` to see what the rule admitted and, more usefully,
every block containing the letters "ore" that it rejected.

---

## Which dimensions carry ore

**Measured, not estimated.** 4 seeds x 40,401 chunks per dimension,
**4,781,092 populated chunks** in total, scanned 2026-09-09. Every one of the 30
dimensions was generated and counted; nothing here is inferred from a
generator's configuration.

**All 30 exist. 16 carry real ore, 9 carry traces, 5 place nothing.** The
earlier figure in this file -- "14 carry ore", with ten placing nothing -- was
wrong in both directions, and every one of the five corrections is a dimension
listed as placing nothing that in fact carries ore:

| dim | name | mod | ore blocks/chunk | ores | measured | previously listed as |
|---:|---|---|---:|---:|---|---|
| 0 | Overworld | minecraft | 1140.985 | 41 | real ore | real ore |
| 58 | DIM 54 | LegendsMod | 1017.186 | 27 | real ore | real ore |
| 81 | Dimension-Extreme | OreSpawn | 761.606 | 20 | real ore | real ore |
| 51 | Wakanda | LegendsMod | 545.564 | 13 | real ore | real ore |
| 80 | Dimension-Utopia | OreSpawn | 539.694 | 20 | real ore | real ore |
| 82 | Dimension-VillageMania | OreSpawn | 537.138 | 19 | real ore | real ore |
| 34 | Tython | LegendsMod | 523.111 | 12 | real ore | real ore |
| -37 | Dream | Witchery | 471.541 | 13 | real ore | real ore |
| -42 | Lost World | thejungleMod | 271.021 | 4 | real ore | real ore |
| 7 | Twilight Forest | TwilightForest | 265.587 | 13 | real ore | real ore |
| 84 | Dimension-Crystal | OreSpawn | 215.660 | 6 | real ore | nothing placed **(was wrong)** |
| 85 | Dimension-Chaos | OreSpawn | 208.871 | 17 | real ore | real ore |
| 33 | Hurikane | LegendsMod | 195.244 | 3 | real ore | real ore |
| -1 | Nether | minecraft | 139.341 | 4 | real ore | real ore |
| 2 | The Collision | TragicMC | 88.284 | 2 | real ore | nothing placed **(was wrong)** |
| 53 | Kingpin Takedown | LegendsMod | 28.521 | 19 | real ore | nothing placed **(was wrong)** |
| 1 | The End | minecraft | 1.070 | 12 | trace only | trace only |
| 66 | Hell | LegendsMod | 0.011 | 5 | trace only | trace only |
| 83 | Dimension-Islands | OreSpawn | 0.007 | 3 | trace only | trace only |
| 30 | Outer Space | LegendsMod | 0.004 | 1 | trace only | nothing placed **(was wrong)** |
| 35 | Korriban | LegendsMod | 0.002 | 4 | trace only | trace only |
| 55 | Quantum Realm | LegendsMod | 0.002 | 1 | trace only | nothing placed **(was wrong)** |
| 36 | Tatooine | LegendsMod | 0.000 | 2 | trace only | trace only |
| 32 | Ilum | LegendsMod | 0.000 | 1 | trace only | trace only |
| 31 | Mars | LegendsMod | 0.000 | 1 | trace only | trace only |
| -39 | Mirror | Witchery | 0.000 | 0 | nothing placed | nothing placed |
| -38 | Torment | Witchery | 0.000 | 0 | nothing placed | nothing placed |
| 3 | Synapse | TragicMC | 0.000 | 0 | nothing placed | nothing placed |
| 4 | CompactMachinesWorld | CompactMachines | 0.000 | 0 | nothing placed | nothing placed |
| 50 | Speed Force | LegendsMod | 0.000 | 0 | nothing placed | nothing placed |

Dimension names come from the mod configs and the server's own load order; the
full mapping is [`dimension-names.tsv`](dimension-names.tsv). LegendsMod owns 13
of the 30, OreSpawn 6, Witchery 3, TragicMC 2.

Two of the corrections have identifiable causes rather than being noise:

- **Dim 2, The Collision** was listed as placing nothing. It is one of the two
  dimensions whose save folder is not named `DIMn` (`Collision/`, and dim 3 is
  `Synapse/`), and the scanner used to attribute anything outside a `DIMn`
  folder to the overworld. The old classification was reading a bug, not a
  dimension.
- **Dim 53, Kingpin Takedown** and **dim 84, Dimension-Crystal** are prebuilt
  maps or map-backed dimensions. Without `legends/` on the server they generate
  nothing at all while still reporting success -- see Step 2.

**Dim 58 is the second richest ore dimension in the pack**, at 1,017
blocks/chunk across 27 ores, just behind the Overworld's 1,141 across 41. It is
also one of the six prebuilt-map dimensions, so a server built without
`legends/` measures it as empty.

## Running it on a 32 GB PC

One dimension generates on one thread, so the way to use twelve cores is
**several servers at once**, each on its own copy and its own port.

**Split by seed, not by dimension.** It is tempting to give each server one
dimension, but seeds are the axis that has to be replicated — a dimension
measured on one seed has no variance to report. Give each server its **own
seed** and let it walk every dimension:

```bash
for i in 1 2 3 4; do
  python3 tools/survey/build_server.py --instance PACK --out srv-$i --force \
      --seed $((20260910 + i)) --port $((25600 + i)) ...
  # ...apply the CodeChickenLib patch to srv-$i/mods/1.7.10/ ...
done

for i in 1 2 3 4; do
  python3 tools/survey/pregen.py --server srv-$i --radius 100 --xmx 6G \
      --dim -1 --dim 7 --dim 33 --dim 34 &
done
wait
```

**Batch the dimensions, 4 or so per invocation.** Every dimension a server
touches stays loaded, so walking all 30 in one go grows the heap for no reason.
Batching also means a failure costs one batch rather than the whole run.

Four jobs at 6 GB each fits 32 GB with headroom. Measured here on a 7900X with
all four running and `--time-per-tick 250`: **250 chunks/s per node, ~900
aggregate**, so 40,000 chunks of one dimension takes under three minutes and all
29 non-overworld dimensions take about 1.5 hours. (The old figure quoted in this
file, 36 chunks/s on an M1, was measured at the mod's default `TimePerTick` of
40 — see Step 4. It is not a hardware difference.)

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
with a warm cache and ~50s on a 7900X with four servers booting at once; longer
on first run. Budget a minute per batch for it.

**A dimension reports `40000 chunks, 0 failed` but wrote no region files.** It
is one of the six prebuilt-map dimensions and `legends/` is missing — see
Step 2. Count region files per dimension after a run; do not trust the pregen
summary alone.

**`ConcurrentModificationException` in `RegionFileCache` during
`unloadWorlds`.** A 1.7.10 race between saving chunks and unloading a world,
made likelier by the dimensions that hold thousands of open region files
(2, 30 and 55 here). It is intermittent — re-run the affected dimension. The
run script should check region counts afterwards rather than assume success.

**`Pregenerated: 0 Chunks`.** The area was already generated. Delete the world
folder (`survey/`) or raise `--radius`.

**Counts look low.** Check `unpopulated_skipped` in the scan output. A large
number means generation was interrupted and those chunks have terrain but no
ore.

**Numbers differ from an earlier run.** Confirm the mod set did not change.
Adding or removing any mod that places blocks invalidates the comparison — that
is exactly how the previous dataset went wrong.
