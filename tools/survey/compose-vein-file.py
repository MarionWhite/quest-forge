#!/usr/bin/env python3
"""Build one qfcontent-oreveins.txt by taking each dimension from one source file.

Vein files cannot be added together the way survey files can, once the two runs
saw *different mods*. Adding them sums the veins and sums the chunks, which is
right only if both runs could have observed every ore. Install a new ore-adding
mod and run again, and the new ore's veins come from the second run's chunks
while the denominator is both runs' chunks -- so the new ore reads low by exactly
the ratio between them. That is the same failure that once made every rate in
this project read 13x low, arriving by a different route.

So this composes rather than merges: each dimension is taken whole from exactly
one file, keeping that file's veins and that file's chunk count together. Later
files win, so pass the newest run last.

    compose-vein-file.py [--survey] out.txt older.txt newer.txt [newer-still.txt ...]

Both of the survey's files have this shape -- "chunks.<dim>" lines and
"<dim>|<name> = <value>" lines -- and both need composing for the same reason,
so --survey just switches the header written into the output.

Use it when a run covers a dimension more currently than an earlier one -- a new
mod, a changed config. To combine two runs of the *same* mod set over the same
dimension, sum them instead; that case is safe and this tool is the wrong shape
for it.
"""

import sys
from collections import OrderedDict


def read(path):
    """Returns ({dim: chunks}, {dim: OrderedDict(name -> value_text)})."""
    chunks = {}
    veins = {}

    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            left, right = (part.strip() for part in line.split("=", 1))

            if left.startswith("chunks."):
                chunks[int(left[len("chunks."):])] = int(right)
            elif "|" in left:
                dim_text, name = left.split("|", 1)
                dim = int(dim_text)
                veins.setdefault(dim, OrderedDict())[name] = right

    return chunks, veins


def main(argv):
    if len(argv) < 4:
        print(__doc__.strip())
        return 1

    survey = "--survey" in argv
    argv = [a for a in argv if a != "--survey"]
    if len(argv) < 4:
        print(__doc__.strip())
        return 1

    out_path = argv[1]
    chosen_chunks = {}
    chosen_veins = {}
    provenance = {}

    for path in argv[2:]:
        chunks, veins = read(path)
        name = path.split("/")[-1]
        taken = []

        # A dimension is only claimed if the file actually watched chunks there.
        # A file that merely mentions a dimension with a zero count must not
        # displace a real measurement of it.
        for dim, count in chunks.items():
            if count <= 0:
                continue
            chosen_chunks[dim] = count
            chosen_veins[dim] = veins.get(dim, OrderedDict())
            provenance[dim] = name
            taken.append(dim)

        print("  %-40s %2d dimensions, %7d chunks"
              % (name, len(taken), sum(chunks.get(d, 0) for d in taken)))

    with open(out_path, "w", encoding="utf-8") as out:
        if survey:
            out.write("# QuestForge ore survey.\n")
            out.write("# Measured by generating chunks server-side and counting what came out.\n")
            out.write("# Format: dimension|modid:block_name:metadata = blocks observed\n")
            out.write("# chunks.<dimension> is what the blocks were counted over.\n")
        else:
            out.write("# QuestForge ore vein parameters.\n")
            out.write("# The generator's own arguments, read by hooking WorldGenMinable.\n")
            out.write("# Format: dimension|modid:block_name:meta = veins,totalSize,minY,maxY\n")
            out.write("# chunks.<dimension> is what the veins were counted over.\n")
        out.write("#\n")
        out.write("# Composed per dimension, each taken whole from one run:\n")
        for dim in sorted(provenance):
            out.write("#   dim %-6d %-38s %7d chunks\n"
                      % (dim, provenance[dim], chosen_chunks[dim]))
        out.write("\n")

        for dim in sorted(chosen_chunks):
            out.write("chunks.%d = %d\n" % (dim, chosen_chunks[dim]))
        out.write("\n")

        entries = 0
        for dim in sorted(chosen_veins):
            for name, value in chosen_veins[dim].items():
                out.write("%d|%s = %s\n" % (dim, name, value))
                entries += 1

    print("\nComposed %d dimensions, %d entries, %d chunks -> %s"
          % (len(chosen_chunks), entries, sum(chosen_chunks.values()), out_path))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
