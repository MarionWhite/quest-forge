#!/usr/bin/env python3
"""Pour waterfalls where raised water meets a drop, in a stitched world's region files.

    py -3.10 tools/world/waterfalls.py WORLD [--area X Z R ...] [--min-drop 3] [--min-run 3]
        [--min-fall 5] [--min-body 64] [--land 6] [--dry-run] [--jobs 6]

WorldPainter exports raised water (plan.py expand's water.png) as still water that stops at
every lip: a river leaving a plateau ends in a pool with a dry cliff below it, and no water
falls (docs/design/world/r13-ingame-test.md). This pass finds every column of raised water
(surface above sea level) whose 4-neighbour is at least --min-drop blocks lower, ground or
water, and fills that neighbour column with falling water (block 8, metadata 8) from the
upper surface down to the pool or ground below. Only real drops count: the falling columns
must form runs of at least --min-run columns that drop --min-fall blocks somewhere, and the
water they fall from a body of at least --min-body columns. And a fall must land in water: a
lower pool or river in that column or within --land columns beyond it. So a stray puddle on a
slope gets nothing, nor does a river's 3-block step between two plan pixels (that stays a
step), nor raised river water standing over a dry bank beside it.

Run it on the stitched world BEFORE the server populates it (the decorators then work around
the falls). Changed chunks get LightPopulated=0, so the game relights them on load. The game
leaves the falls as written until a block update next to them; then they flow as normal water.
--area limits the pass to squares (centre X, Z, half-width R); without it, every region.
"""
import argparse, glob, io, os, re, struct, sys, time, zlib
from multiprocessing import Pool
import numpy as np
import nbtlib
from scipy import ndimage

SEA = 62
WATER = (8, 9)
# Not ground: air, water, and what WorldPainter or the game lays on top of it.
SOFT = {0, 8, 9, 31, 32, 37, 38, 78, 106, 111, 175}


def read_region(path):
    """{(lx, lz): (compressed bytes, compression, timestamp)} for every chunk in a region file."""
    data = open(path, "rb").read()
    out = {}
    if len(data) < 8192:
        return out
    for i in range(1024):
        off = struct.unpack(">I", data[i * 4:i * 4 + 4])[0]
        sec, cnt = off >> 8, off & 0xFF
        if sec == 0 or cnt == 0:
            continue
        ts = struct.unpack(">I", data[4096 + i * 4:4096 + i * 4 + 4])[0]
        o = sec * 4096
        length, comp = struct.unpack(">IB", data[o:o + 5])
        out[(i % 32, i // 32)] = (data[o + 5:o + 4 + length], comp, ts)
    return out


def write_region(path, chunks):
    """Write a region file from {(lx, lz): (compressed bytes, compression, timestamp)}."""
    head, stamps, body = bytearray(4096), bytearray(4096), bytearray()
    sector = 2
    for (lx, lz), (raw, comp, ts) in sorted(chunks.items(), key=lambda kv: kv[0][1] * 32 + kv[0][0]):
        blob = struct.pack(">IB", len(raw) + 1, comp) + raw
        n = (len(blob) + 4095) // 4096
        i = lz * 32 + lx
        head[i * 4:i * 4 + 4] = struct.pack(">I", (sector << 8) | n)
        stamps[i * 4:i * 4 + 4] = struct.pack(">I", ts)
        body += blob + bytes(n * 4096 - len(blob))
        sector += n
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(head + stamps + body)
    os.replace(tmp, path)


def parse(raw, comp):
    import gzip
    return nbtlib.File.parse(io.BytesIO(zlib.decompress(raw) if comp == 2 else gzip.decompress(raw)))


def u8(tag):
    return np.frombuffer(np.asarray(tag, dtype=np.int8).tobytes(), np.uint8).copy()


def blocks(level):
    """(256, 16, 16) block ids, y z x (Add nibble applied), and the (256, 16, 16) metadata."""
    ids = np.zeros(65536, np.uint16)
    meta = np.zeros(65536, np.uint8)
    for s in level.get("Sections", []):
        y = int(s["Y"])
        b = u8(s["Blocks"]).astype(np.uint16)
        if "Add" in s:
            add = u8(s["Add"])
            hi = np.empty(4096, np.uint16)
            hi[0::2], hi[1::2] = add & 0x0F, add >> 4
            b |= hi << 8
        d = u8(s["Data"])
        m = np.empty(4096, np.uint8)
        m[0::2], m[1::2] = d & 0x0F, d >> 4
        ids[y * 4096:(y + 1) * 4096], meta[y * 4096:(y + 1) * 4096] = b, m
    return ids.reshape(256, 16, 16), meta.reshape(256, 16, 16)


def scan(path):
    """Per column of one region: top ground y (-1 = none) and top water y (-1 = top is not water)."""
    rx, rz = map(int, re.findall(r"r\.(-?\d+)\.(-?\d+)\.mca", path)[0])
    ground = np.full((512, 512), -1, np.int16)
    wtop = np.full((512, 512), -1, np.int16)
    have = np.zeros((512, 512), bool)
    soft = np.zeros(4096, bool)
    soft[list(SOFT)] = True
    for (lx, lz), (raw, comp, _) in read_region(path).items():
        ids, _ = blocks(parse(raw, comp)["Level"])
        solid = ~soft[ids]
        wet = (ids == 8) | (ids == 9)
        g = np.where(solid.any(0), 255 - np.argmax(solid[::-1], axis=0), -1)
        w = np.where(wet.any(0), 255 - np.argmax(wet[::-1], axis=0), -1)
        w = np.where(w > g, w, -1)
        sl = (slice(lz * 16, lz * 16 + 16), slice(lx * 16, lx * 16 + 16))
        ground[sl], wtop[sl], have[sl] = g, w, True
    return rx, rz, ground, wtop, have


def plan_falls(ground, wtop, have, min_drop, min_run, min_body, min_fall, land=6):
    """Columns to fill: {(i, j): (y_from, y_to)} on the scanned canvas."""
    surf = np.where(wtop >= 0, wtop, ground)
    raised = have & (wtop >= SEA)              # water above the sea's top block (y 61)
    lab, n = ndimage.label(raised)
    if n:
        size = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
        raised &= np.isin(lab, np.nonzero(size >= min_body)[0] + 1)
    top = np.full(ground.shape, -1, np.int16)  # the highest water that spills into each column
    for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        src = np.roll(np.where(raised, wtop, -1), (di, dj), (0, 1))
        ok = have & (src >= 0) & (surf <= src - min_drop)
        # A fall needs water to land in: lower water in this column or within `land` columns
        # further on. Raised water that only stands over a dry bank (a river's side) is no fall.
        lands = np.zeros_like(ok)
        for k in range(land + 1):
            w = np.roll(wtop, (-k * di, -k * dj), (0, 1))
            lands |= (w >= 0) & (w <= src - min_drop)
        ok &= lands
        top = np.where(ok, np.maximum(top, src), top)
    fall = top >= 0
    for a in (0, 1):                           # np.roll wraps: drop the canvas edge
        for e in (0, -1):
            idx = [slice(None), slice(None)]
            idx[a] = e
            fall[tuple(idx)] = False
    lab, n = ndimage.label(fall, structure=np.ones((3, 3)))
    if n:
        size = ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))
        drop = ndimage.maximum(np.where(fall, top - surf, 0), lab, range(1, n + 1))
        fall &= np.isin(lab, np.nonzero((size >= min_run) & (drop >= min_fall))[0] + 1)
        lab, n = ndimage.label(fall, structure=np.ones((3, 3)))
    ii, jj = np.nonzero(fall)
    return {(int(i), int(j)): (int(surf[i, j]) + 1, int(top[i, j])) for i, j in zip(ii, jj)}, n


def pour(args):
    """Write the falling columns into one region file. cols: {(x, z) in region: (y0, y1)}."""
    path, cols, dry = args
    chunks = read_region(path)
    by_chunk = {}
    for (x, z), yy in cols.items():
        by_chunk.setdefault((x // 16, z // 16), []).append((x % 16, z % 16, yy))
    placed = 0
    for key, lst in by_chunk.items():
        if key not in chunks:
            continue
        raw, comp, ts = chunks[key]
        nbt = parse(raw, comp)
        lv = nbt["Level"]
        secs = {int(s["Y"]): s for s in lv["Sections"]}
        for x, z, (y0, y1) in lst:
            for y in range(y0, y1 + 1):
                sy = y >> 4
                if sy not in secs:
                    s = nbtlib.Compound({"Y": nbtlib.Byte(sy), "Blocks": nbtlib.ByteArray(np.zeros(4096, np.int8)),
                                         "Data": nbtlib.ByteArray(np.zeros(2048, np.int8)),
                                         "BlockLight": nbtlib.ByteArray(np.zeros(2048, np.int8)),
                                         "SkyLight": nbtlib.ByteArray(np.full(2048, -1, np.int8))})
                    lv["Sections"].append(s)
                    secs[sy] = s
                s = secs[sy]
                i = (y & 15) * 256 + z * 16 + x
                b, d = u8(s["Blocks"]), u8(s["Data"])
                b[i] = 8
                d[i >> 1] = (d[i >> 1] & 0xF0) | 8 if i % 2 == 0 else (d[i >> 1] & 0x0F) | 0x80
                if "Add" in s:
                    a = u8(s["Add"])
                    a[i >> 1] &= 0xF0 if i % 2 == 0 else 0x0F
                    s["Add"] = nbtlib.ByteArray(a.view(np.int8))
                s["Blocks"], s["Data"] = nbtlib.ByteArray(b.view(np.int8)), nbtlib.ByteArray(d.view(np.int8))
                placed += 1
        lv["LightPopulated"] = nbtlib.Byte(0)
        buf = io.BytesIO()
        nbt.write(buf)
        chunks[key] = (zlib.compress(buf.getvalue()), 2, ts)
    if not dry:
        write_region(path, chunks)
    return os.path.basename(path), len(by_chunk), placed


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("world")
    ap.add_argument("--area", nargs=3, type=int, action="append", metavar=("X", "Z", "R"))
    ap.add_argument("--min-drop", type=int, default=3)
    ap.add_argument("--min-run", type=int, default=3)
    ap.add_argument("--min-fall", type=int, default=5)
    ap.add_argument("--min-body", type=int, default=64)
    ap.add_argument("--land", type=int, default=6)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--jobs", type=int, default=6)
    a = ap.parse_args()
    t0 = time.time()
    allr = sorted(glob.glob(os.path.join(a.world, "region", "r.*.mca")))
    coords = {tuple(map(int, re.findall(r"r\.(-?\d+)\.(-?\d+)\.mca", p)[0])): p for p in allr}
    groups = []   # each: a set of region coords scanned together (one canvas)
    if a.area:
        for X, Z, R in a.area:
            groups.append({(rx, rz) for rx in range((X - R) // 512, (X + R) // 512 + 1)
                           for rz in range((Z - R) // 512, (Z + R) // 512 + 1) if (rx, rz) in coords})
    else:
        groups.append(set(coords))
    total = {}
    with Pool(a.jobs) as pool:
        for g in groups:
            if not g:
                continue
            rx0, rz0 = min(r[0] for r in g), min(r[1] for r in g)
            rx1, rz1 = max(r[0] for r in g), max(r[1] for r in g)
            W, Hh = (rx1 - rx0 + 1) * 512, (rz1 - rz0 + 1) * 512
            ground = np.full((Hh, W), -1, np.int16)
            wtop = np.full((Hh, W), -1, np.int16)
            have = np.zeros((Hh, W), bool)
            for rx, rz, gr, wt, hv in pool.imap_unordered(scan, [coords[r] for r in sorted(g)]):
                sl = (slice((rz - rz0) * 512, (rz - rz0 + 1) * 512), slice((rx - rx0) * 512, (rx - rx0 + 1) * 512))
                ground[sl], wtop[sl], have[sl] = gr, wt, hv
            cols, nfalls = plan_falls(ground, wtop, have, a.min_drop, a.min_run, a.min_body, a.min_fall, a.land)
            heights = [y1 - y0 + 1 for y0, y1 in cols.values()]
            print(f"regions x {rx0}..{rx1}, z {rz0}..{rz1}: {nfalls} falls, {len(cols)} columns, "
                  f"drop median {int(np.median(heights)) if heights else 0}, max {max(heights) if heights else 0} blocks", flush=True)
            for (i, j), yy in cols.items():
                rx, rz = rx0 + j // 512, rz0 + i // 512
                total.setdefault((rx, rz), {})[(j % 512, i % 512)] = yy
    with Pool(a.jobs) as pool:
        res = pool.map(pour, [(coords[r], c, a.dry_run) for r, c in sorted(total.items())])
    print(f"{'would change' if a.dry_run else 'changed'} {sum(r[1] for r in res)} chunks, "
          f"{sum(r[2] for r in res)} blocks of falling water in {len(res)} region files ({time.time() - t0:.0f} s)")


if __name__ == "__main__":
    main()
