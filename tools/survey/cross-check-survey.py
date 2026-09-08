#!/usr/bin/env python3
"""Check the two ore-survey instruments against each other.

The survey measures ore twice, by unrelated means:

  1. The vein recorder hooks WorldGenMinable.generate and reports the exact
     generation parameters -- veins per chunk, vein size, height band.
  2. The block counter reads finished chunks and reports blocks per chunk.

They should reconcile. A vein of nominal size N never places all N blocks,
because it overlaps itself and the air it passes through, but the shortfall is a
property of the generator rather than of any particular ore: measured against
vanilla it is consistently 0.44 to 0.58. So

    blocks_per_chunk  ~=  veins_per_chunk * vein_size * fill

with fill in that band. An ore well outside it means one of the two instruments
is wrong, and that is worth knowing before the numbers are used for anything.

Both bugs found so far were caught exactly this way, and neither was visible by
looking at either instrument alone:

  * vein counts divided by a cumulative chunk total that included runs predating
    the recorder (every rate scaled down by 13x);
  * vein counts divided by only the chunks that passed a populated check, while
    the filter accepted veins from the whole interior (every rate scaled up by
    about 2x, but only in dimensions where chunks failed to populate).

Usage:
    cross-check-survey.py <vein-report.txt> <block-survey.txt> [more-block-surveys...]
"""

import re
import sys

FILL_LOW = 0.40
FILL_HIGH = 0.62

DIM_HEADER = re.compile(r"---\s*Dimension\s*(-?\d+),\s*veins watched over\s*(\d+)\s*chunks")
VEIN_ROW = re.compile(r"^\s*(.+?)\s{2,}([\d.]+)\s+([\d.]+)\s+(-?\d+)\.\.(-?\d+)\s*$")


def read_veins(path):
    """{dim: {display_name: (veins_per_chunk, avg_size)}} from a /qfsurvey veins dump."""
    out = {}
    dim = None
    for line in open(path, encoding="utf-8", errors="replace"):
        header = DIM_HEADER.search(line)
        if header:
            dim = int(header.group(1))
            out.setdefault(dim, {})
            continue
        if dim is None:
            continue
        row = VEIN_ROW.match(line.rstrip())
        if row and not line.lstrip().startswith("ore "):
            name = row.group(1).strip()
            out[dim][name] = (float(row.group(2)), float(row.group(3)))
    return out


def read_blocks(paths):
    """({dim: chunks}, {(dim, registry_name): blocks}) summed over survey files."""
    chunks, counts = {}, {}
    for path in paths:
        for line in open(path, encoding="utf-8", errors="replace"):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            left, right = (part.strip() for part in line.split("=", 1))
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
    return chunks, counts


def main(argv):
    if len(argv) < 3:
        print(__doc__.strip())
        return 1

    veins = read_veins(argv[1])
    chunks, counts = read_blocks(argv[2:])

    print("Ore                                         veins/ch   size   blocks/ch   fill")
    print("-" * 78)

    checked = suspect = 0

    for dim in sorted(veins):
        if not chunks.get(dim):
            continue

        # Join the two instruments on the tail of the name: the vein report has
        # display names, the survey file has registry names. Matching on the last
        # path segment, lowercased and stripped of punctuation, is crude but only
        # needs to be right for the ores worth checking.
        block_density = {}
        for (d, name), value in counts.items():
            if d != dim:
                continue
            leaf = name.split(":")[-2] if name.count(":") >= 2 else name
            block_density[normalise(leaf)] = value / chunks[dim]

        rows = []
        for name, (per_chunk, size) in veins[dim].items():
            density = block_density.get(normalise(name))
            if density is None or per_chunk <= 0 or size <= 0:
                continue
            fill = density / (per_chunk * size)
            rows.append((name, per_chunk, size, density, fill))

        if not rows:
            continue

        print("\nDimension %d  (%d chunks block-counted)" % (dim, chunks[dim]))
        for name, per_chunk, size, density, fill in sorted(rows, key=lambda r: -r[3]):
            checked += 1
            flag = ""
            if not (FILL_LOW <= fill <= FILL_HIGH):
                flag = "   <-- OUTSIDE %.2f-%.2f" % (FILL_LOW, FILL_HIGH)
                suspect += 1
            print("  %-40s %8.3f %6.1f %11.2f %6.2f%s"
                  % (name[:40], per_chunk, size, density, fill, flag))

    print("\n%d ore/dimension pairs checked, %d outside the expected fill band."
          % (checked, suspect))
    return 1 if suspect else 0


def normalise(text):
    return re.sub(r"[^a-z0-9]", "", text.lower())


if __name__ == "__main__":
    sys.exit(main(sys.argv))
