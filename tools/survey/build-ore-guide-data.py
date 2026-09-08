#!/usr/bin/env python3
"""Assemble the player-facing ore guide's data from the three survey outputs.

Three files, three different jobs, because no one of them can answer everything:

  qfcontent-oreveins.txt   the generator's own arguments -- veins per chunk, vein
                           size, the Y band vein origins fall in. Seed-independent
                           for any generator with a fixed loop bound, which is most
                           of them, and the only figures safe to publish as exact.

  qfcontent-oresurvey.txt  blocks actually counted in finished chunks. This is what
                           a player experiences, and the only source that accounts
                           for veins losing the competition for stone. Seed-
                           dependent, so it is averaged over the three runs.

  qfcontent-orenames.txt   display names and ore-dictionary tags, which only a
                           running game can produce.

Rarity is reported as blocks per chunk from the block survey where it exists,
because that is the number a player can feel. Ores the block survey cannot see --
ones no mod registered in the ore dictionary -- fall back to the vein file's
nominal block count, scaled by the measured shortfall between nominal and actual
across every ore where both are known. That factor is reported, not assumed.
"""
import collections, json, os, re, sys

# Custom generators the vein hook never sees, whose measured rates swung 4x-180x
# between seeds with the mod set held constant. Real ores, unpublishable numbers.
UNSTABLE_MODS = {"voltzengine", "railcraft", "hardcoreenderexpansion"}

# --- scope: mineable ores and gems only --------------------------------------
#
# The vein hook fires for everything WorldGenMinable places, and in this pack that
# is mostly not ore: OreSpawn alone puts a hundred and seven mob-spawn blocks
# through it, and four mods generate their stone variants the same way.
#
# This was a regex over registry names to begin with and it was the wrong tool.
# Every rule it needed had a counterexample: "...Block" is a storage block except
# when it is OreSpawn_OreAmethystBlock; the ore dictionary settles most cases but
# Superheroes Unlimited registers its ores under names like "blackIronOre" that
# the dictionary's own ore* convention does not match, and registers palladium and
# vibranium not at all. Seventy-odd blocks is small enough to decide one at a time
# and say why, so that is what this does. Everything not excluded here is in.

EXCLUDE = {
    # Not ore: plain terrain the generator happens to place the same way.
    "minecraft:dirt:0":                     "terrain, not ore",
    "minecraft:gravel:0":                   "terrain, not ore",
    "minecraft:monster_egg:0":              "silverfish stone, drops nothing",
    "TragicMC:deadDirt:2":                  "terrain, not ore",
    "TragicMC:quicksand:2":                 "terrain, not ore",
    "legends:magma:0":                      "terrain, not ore",
    "OreSpawn:OreSpawn_LavafoamBlock:0":    "terrain, not ore",

    # Not ore: stone variants, which several mods generate through the ore path.
    "legends:granite:0":                    "stone variant",
    "legends:diorite:0":                    "stone variant",
    "legends:andesite:0":                   "stone variant",
    "chisel:granite:0":                     "stone variant",
    "chisel:diorite:0":                     "stone variant",
    "chisel:andesite:0":                    "stone variant",
    "chisel:limestone:0":                   "stone variant",
    "chisel:marble:0":                      "stone variant",

    # Not ore: storage blocks, which OreSpawn seeds into the world as treasure.
    "minecraft:gold_block:0":               "storage block",
    "minecraft:diamond_block:0":            "storage block",
    "minecraft:emerald_block:0":            "storage block",
    "OreSpawn:OreSpawn_BlockRubyBlock:0":   "storage block",

    # Not ore: a structure piece, not something you mine for the material.
    "legends:martianRelic:0":               "relic block, not an ore",
}

# OreSpawn ships no language file, so the game itself cannot name these -- the
# survey dutifully reported "tile.oresalt.name". Taken from its texture names,
# each of which was checked against the sprite.
RENAME = {
    "OreSpawn:OreSpawn_OreSaltBlock:0":         "Salt Ore",
    "OreSpawn:OreSpawn_OreRubyBlock:0":         "Ruby Ore",
    "OreSpawn:OreSpawn_OreAmethystBlock:0":     "Amethyst Ore",
    "OreSpawn:OreSpawn_OreTitaniumBlock:0":     "Titanium Ore",
    "OreSpawn:OreSpawn_OreUraniumBlock:0":      "Uranium Ore",
    "OreSpawn:OreSpawn_OreRedAntTrollBlock:0":  "Red Ant Troll Ore",
    "OreSpawn:OreSpawn_OreTermiteTrollBlock:0": "Termite Troll Ore",
}

SPAWN_BLOCK = re.compile(r"SpawnBlock:\d+$")


def in_scope(key, tags):
    """key is modid:block:meta."""
    if key in EXCLUDE:
        return False
    # OreSpawn's mob-spawn blocks: a hundred and seven of them, all the same shape.
    return not SPAWN_BLOCK.search(key)


def read_kv(path, want_chunks=False):
    """dimension|key = value rows, plus the chunks.<dim> header rows."""
    rows, chunks = {}, {}
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        left, right = (x.strip() for x in line.split("=", 1))
        if left.startswith("chunks."):
            chunks[int(left[7:])] = int(right)
            continue
        rows[left] = right
    return (rows, chunks) if want_chunks else rows


def read_depths(path):
    """dimension|key -> {y: blocks}"""
    out = {}
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        left, right = (x.strip() for x in line.split("=", 1))
        hist = {}
        for part in right.split(","):
            if ":" in part:
                y, c = part.split(":", 1)
                try:
                    hist[int(y)] = int(c)
                except ValueError:
                    pass
        if hist:
            out[left] = hist
    return out


def depth_summary(hist):
    """Peak height, the band holding the middle 80%, and a 64-bucket profile.

    The peak is what a player actually wants -- "dig at y 12" beats "somewhere in
    0 to 64" -- and the 10th-to-90th-percentile band says how tightly the ore
    sticks to it. The profile is for drawing; four-block buckets keep the page's
    data small while staying finer than anything the eye resolves on a column
    256 blocks tall.
    """
    total = sum(hist.values())
    peak = max(hist, key=lambda y: hist[y])

    lo = hi = peak
    running = 0
    for y in sorted(hist):
        running += hist[y]
        if running >= total * 0.10:
            lo = y
            break
    running = 0
    for y in sorted(hist):
        running += hist[y]
        if running >= total * 0.90:
            hi = y
            break

    profile = [0] * 64
    for y, c in hist.items():
        profile[min(63, y // 4)] += c
    top = max(profile) or 1
    return {
        "peak": peak,
        "p10": lo,
        "p90": hi,
        "min": min(hist),
        "max": max(hist),
        # normalised 0-100, so the page can draw it without knowing the totals
        "profile": [round(100.0 * c / top) for c in profile],
    }


def read_names(path):
    """modid:block:meta -> (display name, [oreDict tags])"""
    out = {}
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, rest = (x.strip() for x in line.split("=", 1))
        disp, tags = (rest.rsplit("|", 1) + [""])[:2] if "|" in rest else (rest, "")
        out[key] = (disp.strip(),
                    [t for t in (x.strip() for x in tags.split(",")) if t])
    return out


def read_per_seed(cfg):
    """blocks-per-chunk for each ore in each individual run.

    The merged file cannot answer how much the seeds disagreed, because merging is
    exactly the operation that hides it. Kept as a list per ore so the spread can
    be measured rather than assumed.
    """
    out = collections.defaultdict(list)
    for name in sorted(os.listdir(cfg)):
        if not re.match(r"^seed\d+-oresurvey\.txt$", name):
            continue
        rows, chunks = read_kv(os.path.join(cfg, name), True)
        for key, val in rows.items():
            n = chunks.get(int(key.split("|", 1)[0]), 0)
            if n:
                out[key].append(float(val) / n)
    return out


def main(cfg, out_path):
    veins, chunks = read_kv(os.path.join(cfg, "qfcontent-oreveins.txt"), True)
    per_seed = read_per_seed(cfg)
    blocks = read_kv(os.path.join(cfg, "qfcontent-oresurvey.txt"))
    names = read_names(os.path.join(cfg, "qfcontent-orenames.txt"))

    biome_path = os.path.join(cfg, "qfcontent-orebiomes.txt")
    biomes = read_kv(biome_path) if os.path.exists(biome_path) else {}

    depth_path = os.path.join(cfg, "qfcontent-oredepths.txt")
    depths = read_depths(depth_path) if os.path.exists(depth_path) else {}

    # How far the per-seed rates disagree, per ore. Three runs of the same mod set
    # on three seeds, so anything that moves here moves because the generator is
    # terrain- or biome-conditional, not because the pack changed. This replaces
    # judging trustworthiness by which mod an ore came from: it measures the thing
    # directly instead of assuming it.
    #
    # Raw spread on its own would be misleading, because a rare ore looks unstable
    # even when its generator is perfectly deterministic: thirty blocks counted
    # three times will not give the same number three times. So the observed
    # spread is compared against the spread pure counting noise would produce, and
    # only a substantial excess counts as real terrain-dependence. Blocks arrive in
    # veins rather than one at a time, so the effective sample size is veins, not
    # blocks -- treating each block as independent would understate the noise by
    # about the square root of the vein size and call steady ores unstable.
    spread, excess = {}, {}
    for key, values in per_seed.items():
        if len(values) < 2 or not any(values):
            continue
        mean = sum(values) / len(values)
        if mean <= 0:
            continue
        spread[key] = (max(values) - min(values)) / mean

        blocks_seen = float(blocks.get(key, 0))
        vein = 7.0
        if key in veins:
            v, total, _, _ = (float(x) for x in veins[key].split(","))
            if v:
                vein = max(1.0, total / v)
        effective = blocks_seen / vein
        if effective <= 0:
            continue
        # Expected range of three Poisson samples, as a fraction of their mean.
        expected = 1.69 / (effective / len(values)) ** 0.5
        excess[key] = spread[key] / expected if expected else 0.0

    # --- how far short of its nominal size a vein actually falls --------
    # WorldGenMinable asks for N blocks and places fewer: it traces an ellipsoid
    # and only converts stone, so anything already carved away is lost. Measuring
    # the ratio beats guessing at it.
    # Measured over ores only. The survey also counts OreSpawn's mob-spawn blocks
    # now, and those generate under different rules; letting them into this ratio
    # would push it around for reasons that have nothing to do with ore.
    nom = act = 0.0
    for key, val in veins.items():
        if key not in blocks:
            continue
        ore = key.split("|", 1)[1]
        if not in_scope(ore, names.get(ore, ("", []))[1]):
            continue
        v, total, _, _ = (float(x) for x in val.split(","))
        nom += total
        act += float(blocks[key])
    shortfall = (act / nom) if nom else 1.0

    per_dim = collections.defaultdict(list)
    dropped = []
    phantom = []

    # The union of both files, not just the vein file. VoltzEngine, Railcraft's
    # poor ores and HardcoreEnderExpansion never call WorldGenMinable, so the vein
    # hook cannot see them at all and they exist only as block counts. Iterating
    # the vein file alone silently drops thirty real ores -- which is precisely the
    # set whose rates are too seed-dependent to publish, and so precisely the set
    # that has to be shown as "varies by region" rather than not shown.
    for key in sorted(set(veins) | set(blocks)):
        dim_s, ore = key.split("|", 1)
        dim = int(dim_s)
        n = chunks.get(dim, 0)
        if not n:
            continue

        modid = ore.split(":", 1)[0]
        disp, tags = names.get(ore, (ore, []))
        disp = RENAME.get(ore, disp)

        if not in_scope(ore, tags):
            dropped.append(ore)
            continue

        val = veins.get(key)
        if val:
            v, total, lo, hi = (float(x) for x in val.split(","))
        else:
            v = total = 0.0
            lo, hi = -1, -1        # unknown: no vein was ever observed being placed

        # A vein being ATTEMPTED is not a vein being placed, and the difference
        # is the whole story in some dimensions. WorldGenMinable converts a target
        # block -- stone, almost always -- so in a world built out of something
        # else the generator runs its full loop and places nothing. OreSpawn's
        # Crystal dimension records 105,840 coal veins and contains no coal at
        # all; Tatooine and Korriban record eight and seven ores each that are
        # likewise never actually there. Estimating a rate from the vein
        # parameters, as this did at first, invents ore a player will never find.
        # If the block counter saw none of it in 5,292 chunks, it does not
        # generate here.
        if key not in blocks:
            phantom.append((dim, ore))
            continue
        measured = float(blocks[key])
        bpc = measured / n

        # Enough evidence to quote a rate at all?
        #
        # Ore arrives in veins, not one block at a time, so the independent
        # sample size is veins -- a row built on one block found in five
        # thousand chunks is a single sighting, and printing it as "0.0002 per
        # chunk" dresses one observation up as a four-figure measurement. Worse,
        # the stability test passes it: three seeds cannot disagree by more than
        # counting noise when there is almost nothing to count, so the page ends
        # up vouching for its least certain number. Eight veins is the floor for
        # quoting a figure; below it the ore is reported as present and the raw
        # count is shown instead.
        vein_size = (total / v) if v else 7.0
        veins_seen = measured / max(1.0, vein_size)
        trace = veins_seen < 8

        d = depths.get(key)
        summary = depth_summary(d) if d else None

        row = {
            "key": ore,
            "name": disp,
            "mod": modid,
            "tags": tags,
            "veins": round(v / n, 4) if v else None,
            "size": round(total / v, 2) if v else None,
            "lo": int(lo),
            "hi": int(hi),
            "bpc": round(bpc, 4),
            "exact": bool(v) and float(v / n).is_integer()
                     and float(total / v).is_integer(),
            "measured": measured is not None,
            "raw": int(measured),
            "trace": trace,
            # No vein parameters at all means a custom generator the hook cannot
            # see -- the same generators whose rates swing between seeds.
            # Trustworthy means reproducible: either the vein parameters came out
            # as exact integers (a fixed loop bound, identical on every seed), or
            # the three seeds agreed to within a quarter of the mean. Everything
            # else is real ore whose rate is a property of the terrain it landed
            # in, and gets shown as "varies by region" rather than as a number.
            "spread": round(spread[key], 3) if key in spread else None,
            "excess": round(excess[key], 2) if key in excess else None,
            # An ore is publishable as a number when the three seeds agreed
            # closely enough that a player would not notice the difference. Two
            # tests, because either alone gives the wrong answer: coal's quarter
            # of a million blocks make even a three percent difference between
            # seeds statistically certain, which is true and completely
            # immaterial; and a rare ore counted thirty times can differ by half
            # for no reason but the counting. So it has to be BOTH bigger than
            # counting noise explains AND big enough to matter.
            "steady": (not trace) and (
                      bool(v and float(v / n).is_integer())
                      or not (key in excess and excess[key] > 2.0
                              and spread.get(key, 0) > 0.25)),
            "depth": summary,
        }

        b = biomes.get(key)
        if b:
            counts = []
            for part in b.split(";"):
                if ":" in part:
                    name, cnt = part.rsplit(":", 1)
                    try:
                        counts.append((name.strip(), int(cnt)))
                    except ValueError:
                        pass
            counts.sort(key=lambda kv: -kv[1])
            row["biomes"] = counts
        per_dim[dim].append(row)

    data = {
        "shortfall": round(shortfall, 4),
        "chunks": chunks,
        "dims": [{"id": d, "chunks": chunks.get(d, 0), "ores": per_dim[d]}
                 for d in sorted(per_dim)],
    }
    json.dump(data, open(out_path, "w"), indent=1)
    kept = sorted({o["key"] for d in data["dims"] for o in d["ores"]})
    print("%d dimensions, %d ore rows, %d distinct ores in scope, "
          "%d block kinds dropped as not-an-ore, %d attempted-but-never-placed, "
          "%d too few to quote, vein shortfall %.3f"
          % (len(data["dims"]), sum(len(x["ores"]) for x in data["dims"]),
             len(kept), len(set(dropped)), len(phantom),
             sum(1 for x in data["dims"] for o in x["ores"] if o["trace"]),
             shortfall))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
