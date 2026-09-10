#!/usr/bin/env python3
"""Combine scan_regions.py outputs from several seeds into reportable numbers.

WHY THIS EXISTS. survey/README.md promises "per-ore, per-dimension, per-biome,
per-depth numbers", and asks for three to five seeds so a rate comes with an
honest variance rather than one seed's quirks. scan_regions.py describes one
world along all four axes; nothing joined the seeds together, and nothing
surfaced depth or biome at all. (The merge-*.py scripts in this directory sum
the *old*, discarded instrument's text files and are unrelated.)

Rates are averaged across seeds, never summed. A block absent from one seed
counts as 0.0 for that seed rather than as a missing sample -- a seed that grew
none of an ore is evidence about the rate, not a gap in the data. Metadata
variants fold together, since "how much copper ore is there" does not
distinguish them.

WHAT COUNTS AS AN ORE. Substring matching on "ore" is wrong here, and quietly
so: this pack ships OreSpawn, which prefixes its mod id onto every one of its
block names, so `OreSpawn:OreSpawn_CrabSpawnBlock` and `..._TomatoPlant1` match
a naive test -- about 150 mob-spawn, crop and decoration blocks counted as ore.
Matching `machine_core` is the same mistake from the other side. So names are
split into camelCase/underscore tokens and a block is an ore only if a whole
token is "ore". `--audit` shows what the rule admitted and, more usefully,
every block containing the letters "ore" that it rejected.

DEPTH is reported from the by_y tallies: the Y band an ore actually occupies,
where it peaks, and the band holding the middle 90% of it. That is the number a
player digs to, and it is measured rather than read off a generator's config.

BIOME is reported as enrichment, not as a raw count. A biome that is 40% of a
dimension will hold ~40% of every ore in it for no interesting reason, so the
useful figure is (this ore's share of its blocks in biome B) divided by
(biome B's share of all blocks counted in that dimension). 1.0 means the ore
ignores the biome; 3.0 means three times the concentration you would expect.

Usage:
    aggregate_scans.py scan1.json scan2.json ... --all-dims --ores-only
    aggregate_scans.py scan*.json --dim 0 --depth --biomes -o ore-rates.json
"""
import argparse, json, math, os, re, sys

TOKEN = re.compile(r"[A-Z]+(?![a-z])|[A-Z][a-z]*|[a-z]+|[0-9]+")
ORE_TOKENS = {"ore", "ores"}

# A block making up this much of a dimension's counted volume is that
# dimension's building material, not a vein in it. WorldGenMinable converts a
# target block into ore, so whatever it converts *from* cannot itself be the
# ore. OreSpawn's Crystal dimension (84) is built out of
# `OreSpawn_OreCrystalStoneBlock` -- 88.7% of its volume, exactly as
# minecraft:stone is 76.6% of a LegendsMod dimension -- and the name carries an
# "ore" token, so without this it reports as an ore at 15,470 blocks/chunk and
# swamps every real figure. The highest genuine ore measured anywhere in this
# pack is ~0.7% of volume, so 5% is not a close call.
BULK_SHARE_PCT = 5.0

VANILLA_BIOMES = {
    0: "Ocean", 1: "Plains", 2: "Desert", 3: "Extreme Hills", 4: "Forest",
    5: "Taiga", 6: "Swampland", 7: "River", 8: "Hell", 9: "The End",
    10: "Frozen Ocean", 11: "Frozen River", 12: "Ice Plains",
    13: "Ice Mountains", 14: "Mushroom Island", 15: "Mushroom Island Shore",
    16: "Beach", 17: "Desert Hills", 18: "Forest Hills", 19: "Taiga Hills",
    20: "Extreme Hills Edge", 21: "Jungle", 22: "Jungle Hills",
    23: "Jungle Edge", 24: "Deep Ocean", 25: "Stone Beach", 26: "Cold Beach",
    27: "Birch Forest", 28: "Birch Forest Hills", 29: "Roofed Forest",
    30: "Cold Taiga", 31: "Cold Taiga Hills", 32: "Mega Taiga",
    33: "Mega Taiga Hills", 34: "Extreme Hills+", 35: "Savanna",
    36: "Savanna Plateau", 37: "Mesa", 38: "Mesa Plateau F", 39: "Mesa Plateau",
}


def biome_name(bid):
    """Vanilla ids, their +128 'mutated' variants, then a bare id for modded."""
    if bid in VANILLA_BIOMES:
        return VANILLA_BIOMES[bid]
    if bid - 128 in VANILLA_BIOMES:
        return VANILLA_BIOMES[bid - 128] + " M"
    return "biome %d" % bid


def tokens(name):
    """Split a block name's path into camelCase / underscore / digit tokens.

    The mod id is dropped first, and so is a repeat of it at the head of the
    path. OreSpawn names every block `OreSpawn:OreSpawn_Thing`, so keeping that
    repeat would hand an "ore" token to all ~40 of its mob-spawn and crop
    blocks and quietly inflate every OreSpawn dimension.
    """
    modid, _, path = name.partition(":")
    if not path:
        modid, path = "", name
    head = modid.lower() + "_"
    if modid and path.lower().startswith(head):
        path = path[len(head):]
    return [t.lower() for t in TOKEN.findall(path)]


def is_ore(name):
    return bool(ORE_TOKENS & set(tokens(name)))


def stats(vals):
    m = sum(vals) / len(vals)
    sd = (math.sqrt(sum((v - m) ** 2 for v in vals) / (len(vals) - 1))
          if len(vals) > 1 else 0.0)
    return m, sd, (100.0 * sd / m if m else 0.0)


def read_names(path):
    names = {}
    if not path:
        return names
    for line in open(path, encoding="utf-8"):
        parts = line.rstrip("\n").split("\t")
        if len(parts) >= 3 and parts[0].lstrip("-").isdigit():
            names[parts[0]] = (parts[1], parts[2])
    return names


def depth_stats(by_y):
    """Y band, peak and middle-90% band from a {y: count} tally."""
    ys = sorted((int(y), c) for y, c in by_y.items() if c)
    if not ys:
        return None
    total = sum(c for _, c in ys)
    peak = max(ys, key=lambda yc: yc[1])[0]
    lo, hi, run = ys[0][0], ys[-1][0], 0
    p05 = p95 = ys[0][0]
    for y, c in ys:
        run += c
        if run <= total * 0.05:
            p05 = y
        if run <= total * 0.95:
            p95 = y
    return {"y_min": lo, "y_max": hi, "y_peak": peak,
            "y_p05": p05, "y_p95": p95}


def biome_enrichment(by_biome, dim_biome_totals, top=4):
    """Biomes where this ore is over-represented relative to their volume."""
    total = sum(by_biome.values())
    vol = sum(dim_biome_totals.values())
    if not total or not vol:
        return []
    rows = []
    for b, c in by_biome.items():
        share = c / total
        bshare = dim_biome_totals.get(b, 0) / vol
        if not bshare:
            continue
        rows.append({"biome": int(b), "name": biome_name(int(b)),
                     "pct_of_ore": 100.0 * share,
                     "enrichment": share / bshare})
    rows.sort(key=lambda r: -r["enrichment"])
    return [r for r in rows if r["pct_of_ore"] >= 1.0][:top]


def aggregate(scans, dim, ores_only, want_depth, want_biomes):
    """scans is [(label, parsed_json), ...] loaded once by the caller."""
    per, chunks, labels, volumes = [], [], [], []
    detail = {}          # block -> {"by_y": {...}, "by_biome": {...}} summed
    dim_biomes = {}      # biome -> total blocks in this dimension
    for label, d in scans:
        pop = d.get("populated_chunks", {})
        if dim not in pop or not pop[dim]:
            continue
        n = pop[dim]
        rates, vol = {}, 0
        for entry in d["dimensions"][dim].values():
            b = entry["block"]
            rates[b] = rates.get(b, 0.0) + entry["total"] / n
            vol += entry["total"]
            slot = detail.setdefault(b, {"by_y": {}, "by_biome": {}})
            for y, c in entry.get("by_y", {}).items():
                slot["by_y"][y] = slot["by_y"].get(y, 0) + c
            for bi, c in entry.get("by_biome", {}).items():
                slot["by_biome"][bi] = slot["by_biome"].get(bi, 0) + c
                dim_biomes[bi] = dim_biomes.get(bi, 0) + c
        per.append(rates); chunks.append(n); volumes.append(vol / n)
        labels.append(label)
    if not per:
        return None
    volume = sum(volumes) / len(volumes)

    names = set()
    for r in per:
        names |= set(r)
    ore_names = {b for b in names if is_ore(b)}
    keep = ore_names if ores_only else names

    rows, bulk = [], []
    for b in keep:
        vals = [r.get(b, 0.0) for r in per]
        m, sd, cv = stats(vals)
        share = (100.0 * m / volume) if volume else 0.0
        is_bulk = b in ore_names and share >= BULK_SHARE_PCT
        if is_bulk:
            bulk.append({"block": b, "mean": m, "share_pct": share})
        row = {"block": b, "ore": b in ore_names and not is_bulk,
               "bulk_terrain": is_bulk, "mean": m, "sd": sd, "cv_pct": cv,
               "share_pct": share, "min": min(vals), "max": max(vals),
               "seeds": len(vals), "per_seed": vals}
        if want_depth and b in detail:
            row["depth"] = depth_stats(detail[b]["by_y"])
        if want_biomes and b in detail:
            row["biomes"] = biome_enrichment(detail[b]["by_biome"], dim_biomes)
        rows.append(row)
    rows.sort(key=lambda r: -r["mean"])
    return {"dimension": dim, "scans": labels, "populated_chunks": chunks,
            "total_chunks": sum(chunks), "blocks_per_chunk": volume,
            "ore_per_chunk": sum(r["mean"] for r in rows if r["ore"]),
            "distinct_ores": sum(1 for r in rows if r["ore"]),
            "bulk_terrain": sorted(bulk, key=lambda r: -r["mean"]),
            "blocks": rows}


def classify(ore_per_chunk):
    """The survey README's three buckets, applied to what was measured."""
    if ore_per_chunk >= 2.0:
        return "real ore"
    if ore_per_chunk > 0.0:
        return "trace only"
    return "nothing placed"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scans", nargs="+")
    ap.add_argument("--dim", action="append", help="dimension id; repeatable")
    ap.add_argument("--all-dims", action="store_true")
    ap.add_argument("--ores-only", action="store_true")
    ap.add_argument("--names", help="TSV: dim<TAB>name<TAB>mod")
    ap.add_argument("--depth", action="store_true",
                    help="report the Y band each ore occupies")
    ap.add_argument("--biomes", action="store_true",
                    help="report biomes where each ore is over-represented")
    ap.add_argument("--audit", action="store_true")
    ap.add_argument("--top", type=int, default=0)
    ap.add_argument("-o", "--out")
    args = ap.parse_args()

    # Load each scan exactly once. These files are tens of megabytes for a full
    # pack, and re-reading them per dimension turned 4 reads into 120.
    scans = []
    for p in args.scans:
        scans.append((os.path.basename(p), json.load(open(p, encoding="utf-8"))))

    if args.all_dims:
        dims = set()
        for _, d in scans:
            dims |= set(d.get("populated_chunks", {}))
        dims = sorted(dims, key=int)
    elif args.dim:
        dims = args.dim
    else:
        dims = ["0"]

    names = read_names(args.names)
    results, summary = {}, []
    for dim in dims:
        agg = aggregate(scans, dim, args.ores_only, args.depth, args.biomes)
        if agg is None:
            print("dim %s: no populated chunks in any scan" % dim)
            continue
        agg["name"], agg["mod"] = names.get(dim, ("", ""))
        agg["class"] = classify(agg["ore_per_chunk"])
        results[dim] = agg
        summary.append(agg)

        label = " %s (%s)" % (agg["name"], agg["mod"]) if agg["name"] else ""
        print("\n=== dim %s%s ===" % (dim, label))
        print("%d seeds, %d populated chunks (%s)"
              % (len(agg["scans"]), agg["total_chunks"],
                 ", ".join(str(c) for c in agg["populated_chunks"])))
        print("%.3f ore blocks/chunk across %d distinct ores -> %s"
              % (agg["ore_per_chunk"], agg["distinct_ores"], agg["class"]))
        for b in agg["bulk_terrain"]:
            print("  (excluded: %s is %.1f%% of this dimension's volume at "
                  "%.0f/chunk -- it is the terrain, not a vein in it)"
                  % (b["block"], b["share_pct"], b["mean"]))
        rows = [r for r in agg["blocks"] if r["ore"] or not args.ores_only]
        if args.top:
            rows = rows[:args.top]
        if rows:
            head = "%-44s %10s %8s %6s %6s" % ("block", "mean/chunk", "sd",
                                               "cv%", "vol%")
            if args.depth:
                head += " %-22s" % "Y band (peak, 90%)"
            print(head)
            for r in rows:
                line = ("%-44s %10.4f %8.4f %5.1f%% %5.2f%%"
                        % (r["block"], r["mean"], r["sd"], r["cv_pct"],
                           r["share_pct"]))
                d = r.get("depth")
                if args.depth:
                    line += ("  %-22s" % ("%d-%d (pk %d, %d-%d)"
                                          % (d["y_min"], d["y_max"], d["y_peak"],
                                             d["y_p05"], d["y_p95"]))) if d else "  %-22s" % "-"
                print(line)
                if args.biomes and r.get("biomes"):
                    bits = ", ".join("%s x%.1f (%.0f%%)"
                                     % (x["name"], x["enrichment"], x["pct_of_ore"])
                                     for x in r["biomes"])
                    print("      biomes: %s" % bits)

    if args.audit:
        seen = set()
        for _, d in scans:
            for rows_ in d["dimensions"].values():
                for e in rows_.values():
                    seen.add(e["block"])
        admitted = sorted(b for b in seen if is_ore(b))
        rejected = sorted(b for b in seen
                          if not is_ore(b) and "ore" in b.lower())
        print("\n=== ore rule audit ===")
        print("admitted %d blocks as ore" % len(admitted))
        print("rejected %d blocks whose name contains 'ore' but has no 'ore' "
              "token:" % len(rejected))
        for b in rejected:
            print("   ", b)

    if summary:
        print("\n=== per-dimension summary ===")
        print("%-6s %-24s %-16s %12s %7s %s"
              % ("dim", "name", "mod", "ore/chunk", "ores", "class"))
        for a in sorted(summary, key=lambda x: -x["ore_per_chunk"]):
            print("%-6s %-24s %-16s %12.3f %7d %s"
                  % (a["dimension"], a["name"][:24], a["mod"][:16],
                     a["ore_per_chunk"], a["distinct_ores"], a["class"]))
        buckets = {}
        for a in summary:
            buckets.setdefault(a["class"], []).append(a["dimension"])
        print()
        for k in ("real ore", "trace only", "nothing placed"):
            if k in buckets:
                print("%-15s %2d: %s" % (k, len(buckets[k]),
                                         ", ".join(sorted(buckets[k], key=int))))

    if args.out:
        json.dump(results, open(args.out, "w", encoding="utf-8"), indent=1)
        print("\nwrote %s" % args.out)


if __name__ == "__main__":
    main()
