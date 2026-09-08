#!/usr/bin/env python3
"""Sum several qfcontent-oresurvey.txt files into one.

A survey is just counts, so surveys add. That is what makes it worth running
several servers in parallel on different seeds: three machine-hours of sampling
across three world seeds is both faster to collect and a better sample than the
same time spent on one seed, because it cannot be fooled by one seed's quirks.

Usage:
    merge-ore-surveys.py out.txt in1.txt in2.txt [in3.txt ...]
"""

import sys
from collections import OrderedDict


def read(path):
    """Returns ({dim: chunks}, {(dim, ore_name): count}).

    Handles both the current "dim|name" format and the older flat one, which had
    no dimensions and was therefore all overworld.
    """
    chunks = {}
    counts = OrderedDict()

    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            left, right = line.split("=", 1)
            left, right = left.strip(), right.strip()

            try:
                value = int(right)
            except ValueError:
                continue

            if left.startswith("chunks."):
                dim = int(left[len("chunks."):])
                chunks[dim] = chunks.get(dim, 0) + value
            elif left == "chunks_sampled":
                chunks[0] = chunks.get(0, 0) + value
            elif "|" in left:
                dim_text, name = left.split("|", 1)
                key = (int(dim_text), name)
                counts[key] = counts.get(key, 0) + value
            else:
                key = (0, left)
                counts[key] = counts.get(key, 0) + value

    return chunks, counts


def main(argv):
    if len(argv) < 3:
        print(__doc__.strip())
        return 1

    out_path, in_paths = argv[1], argv[2:]

    all_chunks = {}
    totals = {}
    sources = []

    for path in in_paths:
        chunks, counts = read(path)
        if not chunks and not counts:
            print("  skipped (empty): %s" % path)
            continue

        for dim, value in chunks.items():
            all_chunks[dim] = all_chunks.get(dim, 0) + value
        for key, value in counts.items():
            totals[key] = totals.get(key, 0) + value

        sources.append((path, sum(chunks.values()), len(counts)))
        print("  %-46s %7d chunks, %3d entries"
              % (path.split("/")[-1], sum(chunks.values()), len(counts)))

    if not sources:
        print("Nothing to merge.")
        return 1

    total_chunks = sum(all_chunks.values())

    # Density, not raw count: blocks per chunk in the dimension it was seen in,
    # summed across dimensions. This is what makes uneven sampling harmless.
    density = {}
    for (dim, name), value in totals.items():
        if all_chunks.get(dim):
            density[name] = density.get(name, 0.0) + float(value) / all_chunks[dim]

    ranked = sorted(totals.items(), key=lambda kv: -kv[1])
    grand = sum(totals.values())

    with open(out_path, "w", encoding="utf-8") as out:
        out.write("# QuestForge ore survey.\n")
        out.write("# Measured by generating chunks server-side and counting what came out.\n")
        out.write("# Format: modid:block_name:metadata = blocks observed\n")
        out.write("# Delete this file to discard the measurement and start again.\n")
        out.write("#\n")
        out.write("# Merged from %d survey runs:\n" % len(sources))
        for path, chunks, kinds in sources:
            out.write("#   %-36s %7d chunks, %3d ore types\n"
                      % (path.split("/")[-1], chunks, kinds))
        for dim in sorted(all_chunks):
            out.write("chunks.%d = %d\n" % (dim, all_chunks[dim]))
        out.write("\n")

        for (dim, name), value in ranked:
            out.write("%d|%s = %d\n" % (dim, name, value))

    print("\nMerged %d chunks over %d dimensions, %d distinct ores, %d ore blocks -> %s"
          % (total_chunks, len(all_chunks), len(density), grand, out_path))
    print("\nChunks per dimension: %s"
          % ", ".join("%d:%d" % (d, all_chunks[d]) for d in sorted(all_chunks)))

    by_density = sorted(density.items(), key=lambda kv: -kv[1])
    total_density = sum(density.values())
    print("\nTop 25 by density (blocks per chunk, summed over dimensions):")
    for name, value in by_density[:25]:
        print("  %-46s %8.2f /chunk   %5.2f%% of pool"
              % (name, value, 100.0 * value / total_density))

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
