"""Join exported WorldPainter pieces into one world and point it at RWG (decision 0003).

    py -3.10 tools/world/stitch.py OUT_WORLD PIECE_EXPORT [PIECE_EXPORT ...] [--seed N] [--spawn X Z]
        [--generator RWG|BIOMESOP]

Pieces are 512-aligned, so each region file belongs to exactly one piece; a region file that
two pieces both wrote is an error, not something to merge. level.dat comes from the first
piece: WorldPainter writes generatorName=largeBiomes, so it is set to RWG with a fixed seed
(docs/design/world/poc.md). --generator BIOMESOP is the no-code fallback: until the qf-tweaks
hook exists RWG decorates painted chunks by its own noise, BoP's world type by the stored biome.
"""
import argparse, os, shutil, sys
import nbtlib


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("pieces", nargs="+")
    ap.add_argument("--seed", type=int, default=20261017)
    ap.add_argument("--spawn", nargs=2, type=int, default=None)
    ap.add_argument("--name", default="qf-continent")
    ap.add_argument("--generator", default="RWG", help="level.dat generatorName: RWG, or BIOMESOP (BoP)")
    a = ap.parse_args()

    if os.path.exists(a.out):
        sys.exit(f"{a.out} exists; stitch into a fresh directory")
    os.makedirs(os.path.join(a.out, "region"))
    seen = {}
    for p in a.pieces:
        rd = os.path.join(p, "region")
        for f in sorted(os.listdir(rd)):
            if not f.endswith(".mca"):
                continue
            if f in seen:
                sys.exit(f"{f} is in both {seen[f]} and {p}: pieces must not overlap")
            seen[f] = p
            shutil.copy2(os.path.join(rd, f), os.path.join(a.out, "region", f))
    shutil.copy2(os.path.join(a.pieces[0], "level.dat"), os.path.join(a.out, "level.dat"))

    lvl = nbtlib.load(os.path.join(a.out, "level.dat"))
    data = lvl["Data"]
    data["generatorName"] = nbtlib.String(a.generator)
    data["generatorVersion"] = nbtlib.Int(0)
    data["RandomSeed"] = nbtlib.Long(a.seed)
    data["LevelName"] = nbtlib.String(a.name)
    if a.spawn:
        data["SpawnX"], data["SpawnZ"] = nbtlib.Int(a.spawn[0]), nbtlib.Int(a.spawn[1])
    lvl.save()
    print(f"{len(seen)} region files from {len(a.pieces)} pieces -> {a.out} (generatorName={a.generator}, seed {a.seed})")


if __name__ == "__main__":
    main()
