#!/usr/bin/env python3
"""Sum several qfcontent-oreveins.txt files from runs of the SAME mod set.

The companion to compose-vein-file.py, and the two are not interchangeable:

  * SUM (this tool) when every run could have observed every ore -- the same
    mods, different seeds. Veins add, chunk counts add, and the combined rate is
    total veins over total chunks. More seeds is a better estimate of the ores
    that vary by biome, and changes nothing for the ones that are a fixed loop
    bound, which is exactly what you want.

  * COMPOSE (the other tool) when the runs saw DIFFERENT mods. Adding those
    divides one run's veins by both runs' chunks, and every ore the other run
    could not have contained reads low by the ratio between them.

Using this tool across a mod-set change is the bug it exists to avoid, so it
refuses when one input has ores in a dimension that another input measured
without ever seeing them.

Usage:
    merge-vein-files.py out.txt in1.txt in2.txt [in3.txt ...]
"""

import sys


def read(path):
    """({dim: chunks}, {(dim, name): [veins, totalSize, minY, maxY]})"""
    chunks, rows = {}, {}
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        left, right = (p.strip() for p in line.split("=", 1))
        if left.startswith("chunks."):
            chunks[int(left[len("chunks."):])] = int(right)
        elif "|" in left:
            dim_text, name = left.split("|", 1)
            p = right.split(",")
            if len(p) >= 4:
                rows[(int(dim_text), name)] = [int(p[0]), int(p[1]), int(p[2]), int(p[3])]
    return chunks, rows


def main(argv):
    if len(argv) < 4:
        print(__doc__.strip())
        return 1

    out_path = argv[1]
    sources = []
    for path in argv[2:]:
        sources.append((path, read(path)))
        chunks, rows = sources[-1][1]
        print("  %-44s %2d dims, %5d entries, %7d chunks"
              % (path.split("/")[-1], len(chunks), len(rows), sum(chunks.values())))

    # Guard: an ore present in one run but absent from another that measured the
    # same dimension means the mod sets differed, and summing would be wrong.
    suspect = []
    for dim in set(d for _, (c, _) in sources for d in c):
        present = [set(n for (dd, n) in r if dd == dim)
                   for _, (c, r) in sources if c.get(dim)]
        if len(present) < 2:
            continue
        everywhere = set.intersection(*present)
        anywhere = set.union(*present)
        for name in anywhere - everywhere:
            suspect.append((dim, name))

    if suspect:
        print("\n%d ore/dimension pairs appear in some runs but not others." % len(suspect))
        for dim, name in suspect[:10]:
            print("    dim %-6d %s" % (dim, name))
        # Rare ores legitimately miss a short run, so this is a warning rather
        # than a refusal -- but a long list means the mod sets differed.
        if len(suspect) > 40:
            print("\nThat is too many to be sampling luck. These runs look like they had\n"
                  "different mods installed; use compose-vein-file.py instead.")
            return 2
        print("  (few enough to be sampling luck in the rare ores; continuing)")

    all_chunks, all_rows = {}, {}
    for _, (chunks, rows) in sources:
        for dim, n in chunks.items():
            all_chunks[dim] = all_chunks.get(dim, 0) + n
        for key, v in rows.items():
            acc = all_rows.get(key)
            if acc is None:
                all_rows[key] = list(v)
            else:
                acc[0] += v[0]
                acc[1] += v[1]
                acc[2] = min(acc[2], v[2])
                acc[3] = max(acc[3], v[3])

    with open(out_path, "w", encoding="utf-8") as out:
        out.write("# QuestForge ore vein parameters.\n")
        out.write("# The generator's own arguments, read by hooking WorldGenMinable.\n")
        out.write("# Format: dimension|modid:block_name:meta = veins,totalSize,minY,maxY\n")
        out.write("# chunks.<dimension> is what the veins were counted over.\n")
        out.write("#\n")
        out.write("# Summed over %d runs of the same mod set:\n" % len(sources))
        for path, (chunks, rows) in sources:
            out.write("#   %-40s %2d dims, %5d entries, %7d chunks\n"
                      % (path.split("/")[-1], len(chunks), len(rows), sum(chunks.values())))
        out.write("\n")
        for dim in sorted(all_chunks):
            out.write("chunks.%d = %d\n" % (dim, all_chunks[dim]))
        out.write("\n")
        for dim, name in sorted(all_rows):
            v = all_rows[(dim, name)]
            out.write("%d|%s = %d,%d,%d,%d\n" % (dim, name, v[0], v[1], v[2], v[3]))

    print("\nSummed %d dimensions, %d entries, %d chunks -> %s"
          % (len(all_chunks), len(all_rows), sum(all_chunks.values()), out_path))

    exact = 0
    for (dim, _), v in all_rows.items():
        rate = v[0] / all_chunks[dim]
        if abs(rate - round(rate)) <= 0.005:
            exact += 1
    print("%d of %d entries resolved to an exact integer rate." % (exact, len(all_rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
