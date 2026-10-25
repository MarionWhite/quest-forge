#!/usr/bin/env python3
"""Make iceberg and glacier sides ice all the way down, in a stitched world's region files.

    py -3.10 tools/world/ice_faces.py WORLD [--area X Z R ...] [--block 174] [--to 52] [--dry-run] [--jobs 6]

WorldPainter lays a terrain only 3-7 blocks deep (its top layer), and stone below it. On a
sheer berg that stands 10-30 blocks out of the sea, the face is then packed ice for the top
few blocks and stone under it (docs/design/world/r13-ingame-test.md). This pass finds every
column whose top ground block (under snow and plants) is --block, packed ice by default, and
turns the natural ground under it (stone, dirt, gravel, sand, clay, ores) into the same block
down to y --to, 10 below the sea by default, so a berg's face is ice to the waterline and on
under it. Only columns WorldPainter already topped with that block change; the plan gives
packed ice only to the bergs and the glacier snout (`surface: packed_ice`).

Run it on the stitched world before the server populates it, like tools/world/waterfalls.py.
--area limits the pass to squares (centre X, Z, half-width R); without it, every region.
"""
import argparse, glob, io, os, re, time, zlib
from multiprocessing import Pool
import numpy as np
import nbtlib
from waterfalls import read_region, write_region, parse, blocks, SOFT

# Natural ground that may turn to ice: stone, grass, dirt, cobble, sand, gravel, the ores,
# sandstone, clay, stained clay, hardened clay, snow block, ice.
NATURAL = {1, 2, 3, 4, 12, 13, 14, 15, 16, 21, 24, 56, 73, 74, 79, 80, 82, 129, 159, 172}


def convert(args):
    path, block, floor, dry = args
    chunks = read_region(path)
    soft = np.zeros(4096, bool)
    soft[list(SOFT)] = True
    nat = np.zeros(4096, bool)
    nat[list(NATURAL)] = True
    changed, cols, placed = 0, 0, 0
    for key, (raw, comp, ts) in list(chunks.items()):
        nbt = parse(raw, comp)
        lv = nbt["Level"]
        ids, meta = blocks(lv)
        solid = ~soft[ids]
        if not solid.any():
            continue
        top = 255 - np.argmax(solid[::-1], axis=0)           # (16, 16) top ground y
        has = solid.any(0)
        tb = np.take_along_axis(ids, top[None], 0)[0]
        hit = has & (tb == block) & (top > floor)
        if not hit.any():
            continue
        y = np.arange(256)[:, None, None]
        m = hit[None] & (y < top[None]) & (y >= floor) & nat[ids]
        if not m.any():
            continue
        ids[m], meta[m] = block, 0
        placed += int(m.sum())
        cols += int(hit.sum())
        changed += 1
        secs = {int(s["Y"]): s for s in lv["Sections"]}
        for sy in np.unique(np.nonzero(m)[0] >> 4):
            s = secs[int(sy)]                                 # a ground block lies in an existing section
            b = ids[sy * 16:(sy + 1) * 16].reshape(4096)
            d = meta[sy * 16:(sy + 1) * 16].reshape(4096)
            s["Blocks"] = nbtlib.ByteArray((b & 0xFF).astype(np.uint8).view(np.int8))
            s["Data"] = nbtlib.ByteArray((d[0::2] | (d[1::2] << 4)).astype(np.uint8).view(np.int8))
            if "Add" in s or (b > 255).any():
                hi = (b >> 8).astype(np.uint8)
                s["Add"] = nbtlib.ByteArray((hi[0::2] | (hi[1::2] << 4)).astype(np.uint8).view(np.int8))
        buf = io.BytesIO()
        nbt.write(buf)
        chunks[key] = (zlib.compress(buf.getvalue()), 2, ts)
    if changed and not dry:
        write_region(path, chunks)
    return os.path.basename(path), changed, cols, placed


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("world")
    ap.add_argument("--area", nargs=3, type=int, action="append", metavar=("X", "Z", "R"))
    ap.add_argument("--block", type=int, default=174, help="top block whose column turns to it (174 = packed ice)")
    ap.add_argument("--to", type=int, default=52, help="lowest y that changes")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--jobs", type=int, default=6)
    a = ap.parse_args()
    t0 = time.time()
    allr = sorted(glob.glob(os.path.join(a.world, "region", "r.*.mca")))
    if a.area:
        want = {(rx, rz) for X, Z, R in a.area for rx in range((X - R) // 512, (X + R) // 512 + 1)
                for rz in range((Z - R) // 512, (Z + R) // 512 + 1)}
        allr = [p for p in allr if tuple(map(int, re.findall(r"r\.(-?\d+)\.(-?\d+)\.mca", p)[0])) in want]
    with Pool(a.jobs) as pool:
        res = pool.map(convert, [(p, a.block, a.to, a.dry_run) for p in allr])
    res = [r for r in res if r[1]]
    print(f"{'would change' if a.dry_run else 'changed'} {sum(r[1] for r in res)} chunks, {sum(r[2] for r in res)} columns, "
          f"{sum(r[3] for r in res)} blocks to {a.block} in {len(res)} region files ({time.time() - t0:.0f} s)")


if __name__ == "__main__":
    main()
