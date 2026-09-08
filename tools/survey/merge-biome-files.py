#!/usr/bin/env python3
"""Sum qfcontent-orebiomes.txt files from runs of the SAME mod set.

Biome counts add the way vein counts do -- each run contributes independent
observations of the same generator -- so summing is right here for exactly the
reason it is right in merge-vein-files.py, and wrong for exactly the same reason
if the mod sets differ.

    usage: merge-biome-files.py out.txt in1.txt in2.txt ...
"""
import collections, sys

def read(path):
    out = {}
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        left, right = line.split("=", 1)
        counts = {}
        for part in right.strip().split(";"):
            if ":" not in part:
                continue
            biome, n = part.rsplit(":", 1)
            try:
                counts[biome.strip()] = int(n)
            except ValueError:
                pass
        if counts:
            out[left.strip()] = counts
    return out

def main(argv):
    out_path, ins = argv[1], argv[2:]
    total = collections.defaultdict(collections.Counter)
    for p in ins:
        d = read(p)
        for key, counts in d.items():
            total[key].update(counts)
        print("  %-40s %d ore/dimension rows" % (p.split("/")[-1], len(d)))

    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("# Which biomes each ore's veins were rooted in.\n")
        fh.write("# Counted at the vein origin, summed over %d runs.\n" % len(ins))
        fh.write("# Format: dimension|modid:block:meta = biome:veins;biome:veins\n\n")
        for key in sorted(total):
            counts = total[key]
            parts = ";".join("%s:%d" % (b, n)
                             for b, n in sorted(counts.items(), key=lambda kv: -kv[1]))
            fh.write("%s = %s\n" % (key, parts))

    print("wrote %s: %d ore/dimension rows" % (out_path, len(total)))

if __name__ == "__main__":
    main(sys.argv)
