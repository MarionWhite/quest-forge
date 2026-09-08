#!/usr/bin/env python3
"""Combine `/qfsurvey veins` output from several servers into one table.

Rates cannot simply be averaged. Each server reports veins-per-chunk over its own
number of watched chunks, so the combined rate is the total veins divided by the
total chunks:

    veins_i = rate_i * chunks_i          combined = sum(veins_i) / sum(chunks_i)

For the ores whose rate is a fixed loop bound this changes nothing -- every server
reports the same integer, and so does the total. It matters for the ores that vary
by biome (gold, diamond, emerald), where more seeds is a better estimate, and it
is the difference between an answer and an artefact when the servers watched
different numbers of chunks.

Usage:
    merge-vein-reports.py <server.log> [server.log ...]
"""

import re
import sys

DIM_HEADER = re.compile(r"---\s*Dimension\s*(-?\d+),\s*veins watched over\s*(\d+)\s*chunks")
ROW = re.compile(r"^\s*(.+?)\s{2,}([\d.]+)\s+([\d.]+)\s+(-?\d+)\.\.\s*(-?\d+)\s*$")


def read(path):
    """Yields (dim, chunks, ore, veins, total_size, min_y, max_y) from the LAST report."""
    blocks = []
    current = None

    for raw in open(path, encoding="utf-8", errors="replace"):
        line = re.sub(r"^.*?\[qfcontent\]:\s*", "", raw.rstrip())

        header = DIM_HEADER.search(line)
        if header:
            current = (int(header.group(1)), int(header.group(2)), [])
            blocks.append(current)
            continue

        if current is None or line.lstrip().startswith("ore "):
            continue

        row = ROW.match(line)
        if row:
            name = row.group(1).strip()
            rate, size = float(row.group(2)), float(row.group(3))
            current[2].append((name, rate * current[1], rate * current[1] * size,
                               int(row.group(4)), int(row.group(5))))

    # A log can hold several reports if /qfsurvey veins was run more than once.
    # Keep only the last one per dimension.
    latest = {}
    for dim, chunks, rows in blocks:
        latest[dim] = (chunks, rows)
    return latest


def main(argv):
    if len(argv) < 2:
        print(__doc__.strip())
        return 1

    chunks = {}
    veins = {}

    for path in argv[1:]:
        for dim, (n, rows) in read(path).items():
            chunks[dim] = chunks.get(dim, 0) + n
            for name, count, sized, lo, hi in rows:
                key = (dim, name)
                have = veins.get(key)
                if have is None:
                    veins[key] = [count, sized, lo, hi]
                else:
                    have[0] += count
                    have[1] += sized
                    have[2] = min(have[2], lo)
                    have[3] = max(have[3], hi)

    for dim in sorted(chunks):
        rows = [(name, v) for (d, name), v in veins.items() if d == dim]
        if not rows:
            continue

        print("\n=== Dimension %d  (%d chunks watched across %d servers) ==="
              % (dim, chunks[dim], len(argv) - 1))
        print("  %-44s %10s %7s %12s" % ("ore", "veins/chunk", "size", "y range"))

        for name, (count, sized, lo, hi) in sorted(rows, key=lambda r: -r[1][0]):
            rate = count / chunks[dim]
            size = sized / count if count else 0
            exact = "" if abs(rate - round(rate)) > 0.005 else "  (exact)"
            print("  %-44s %10.3f %7.1f %5d..%-5d%s"
                  % (name[:44], rate, size, lo, hi, exact))

    print("\n%d dimensions, %d ore/dimension entries." % (len(chunks), len(veins)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
