#!/usr/bin/env python3
"""Copy the shader-review world and build a texture showcase wall in the copy.

    py -3.10 -I tools/textures/build_showcase.py [--src C:\\qfb\\world-master] [--dst C:\\qfb\\textures\\world-showcase]

The bench gallery (FrameBench) sets its blocks two apart, so connected textures never show.
This wall, on a levelled plain beside the plains_noon view (behind golden_lit's camera, so that
view is unchanged), has block groups big enough for CTM and for judging texture detail:

  x 245-248  clear glass 4x4 (connected-glass CTM)
  x 250-252  light-blue stained glass 3x3
  x 254-256  stone with eight ores set in it
  x 258-259  gold, iron and diamond blocks, glowstone on top
  y 68 is a stone plinth under all of it; z 178 is the wall, the camera stands south of it
  (views-world-master.txt: texture_wall, glass_close).

--modded [LIST] adds a second wall of modded blocks east of the first (x 263-281, same z, four
rows y 72 down to 69, 19 per row, the list read left to right then down), for the modded-block
texture loop (docs/design/textures/modded-blocks.md, "Render requests"; the default list is
tools/textures/showcase-modded.txt). LIST holds one `modid:name@meta` per line; the numeric IDs
come from the copied world's own level.dat (FML's registry), so a name the world does not know
is reported and skipped, never guessed. Views modded_wall and modded_close look at it.

Never writes to --src. The copy is made once; the wall is rebuilt in it on every run.
"""
import argparse, io, os, shutil, struct, sys, types, zlib

import numpy as np
import nbtlib


# --- region file helpers (the same as tools/world/waterfalls.py's) ---------------------
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


W = types.SimpleNamespace(read_region=read_region, write_region=write_region, parse=parse, u8=u8, blocks=blocks)

X0, X1, Z0, Z1, GROUND = 242, 262, 176, 192, 67
WALL_Z = 178
CLEAR_TOP = 80
TRANSPARENT = {0, 20, 95, 102, 160}
MODDED_X0, MODDED_COLS, MODDED_ROWS = 263, 19, 4
HERE = os.path.dirname(os.path.abspath(__file__))


def registry_ids(world):
    """{'modid:name': id} from the world's level.dat (FML ItemData; block keys start with \\x01)."""
    root = nbtlib.load(os.path.join(world, "level.dat"))
    fml = root["FML"] if "FML" in root else root[""]["FML"]
    out = {}
    for e in fml["ItemData"]:
        k = str(e["K"])
        if k.startswith("\x01"):
            out[k[1:]] = int(e["V"])
    return out


def read_modded_list(path):
    out = []
    for l in open(path, encoding="utf-8"):
        l = l.split("#", 1)[0].strip()
        if l:
            name, _, meta = l.partition("@")
            out.append((name, int(meta or 0)))
    return out


def modded_wall(entries, ids):
    """{(x, y, z): (id, meta)} for the modded wall, and the names the world does not register."""
    b, missing = {}, []
    for x in range(MODDED_X0 - 1, MODDED_X0 + MODDED_COLS + 1):
        b[(x, 68, WALL_Z)] = (1, 0)
    for i, (name, meta) in enumerate(entries[:MODDED_COLS * MODDED_ROWS]):
        if name not in ids:
            missing.append(name)
            continue
        x = MODDED_X0 + i % MODDED_COLS
        y = 68 + MODDED_ROWS - i // MODDED_COLS      # the first line of the list is the top row
        b[(x, y, WALL_Z)] = (ids[name], meta)
    return b, missing


def wall():
    """{(x, y, z): (id, meta)}."""
    b = {}
    for x in range(245, 260):
        b[(x, 68, WALL_Z)] = (1, 0)
    for x in range(245, 249):
        for y in range(69, 73):
            b[(x, y, WALL_Z)] = (20, 0)
    for x in range(250, 253):
        for y in range(69, 72):
            b[(x, y, WALL_Z)] = (95, 3)
    ores = [[16, 1, 56], [1, 14, 1], [15, 1, 21], [1, 73, 129]]   # top row first
    for r, row in enumerate(ores):
        for c, ident in enumerate(row):
            b[(254 + c, 72 - r, WALL_Z)] = (ident, 0)
    for r, ident in enumerate([41, 42, 57, 89]):
        for x in (258, 259):
            b[(x, 69 + r, WALL_Z)] = (ident, 0)
    return b


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", default=r"C:\qfb\world-master")
    ap.add_argument("--dst", default=r"C:\qfb\textures\world-showcase")
    ap.add_argument("--modded", nargs="?", const=os.path.join(HERE, "showcase-modded.txt"),
                    help="also build the modded-block wall from this list (default: tools/textures/showcase-modded.txt)")
    a = ap.parse_args()
    if os.path.abspath(a.src) == os.path.abspath(a.dst):
        sys.exit("--dst must differ from --src")
    if not os.path.exists(a.dst):
        shutil.copytree(a.src, a.dst)   # a real copy, never links (hard links write through)
        print("copied", a.src, "->", a.dst)
    for lock in ("session.lock",):
        p = os.path.join(a.dst, lock)
        if os.path.exists(p):
            os.remove(p)

    place = wall()
    x1 = X1
    if a.modded:
        entries = read_modded_list(a.modded)
        extra, missing = modded_wall(entries, registry_ids(a.dst))
        place.update(extra)
        x1 = MODDED_X0 + MODDED_COLS + 2
        print("modded wall: %d of %d blocks placed" % (sum(1 for k in extra if k[1] > 68), len(entries)))
        if missing:
            print("  not in this world's registry, skipped: " + ", ".join(missing))
    path = os.path.join(a.dst, "region", "r.0.0.mca")
    chunks = W.read_region(path)
    touched = 0
    for cx in range(X0 // 16, x1 // 16 + 1):
        for cz in range(Z0 // 16, Z1 // 16 + 1):
            raw, comp, ts = chunks[(cx, cz)]
            nbt = W.parse(raw, comp)
            lv = nbt["Level"]
            secs = {int(s["Y"]): s for s in lv["Sections"]}
            arrays = {}

            def get(sy):
                if sy not in arrays:
                    if sy not in secs:
                        s = nbtlib.Compound({"Y": nbtlib.Byte(sy), "Blocks": nbtlib.ByteArray(np.zeros(4096, np.int8)),
                                             "Data": nbtlib.ByteArray(np.zeros(2048, np.int8)),
                                             "BlockLight": nbtlib.ByteArray(np.zeros(2048, np.int8)),
                                             "SkyLight": nbtlib.ByteArray(np.full(2048, -1, np.int8))})
                        lv["Sections"].append(s)
                        secs[sy] = s
                    s = secs[sy]
                    arrays[sy] = [W.u8(s["Blocks"]), W.u8(s["Data"]), W.u8(s["Add"]) if "Add" in s else None]
                return arrays[sy]

            def setb(x, y, z, ident, meta=0):
                bl, d, add = get(y >> 4)
                i = (y & 15) * 256 + z * 16 + x
                # 1.7.10 block IDs are 12 bits: the low byte in Blocks, the high nibble in Add
                # (modded IDs run past 255; the Add array is made on first need).
                bl[i] = ident & 0xFF
                hi = ident >> 8
                if add is None and hi:
                    add = np.zeros(2048, np.uint8)
                    arrays[y >> 4][2] = add
                if i % 2 == 0:
                    d[i >> 1] = (d[i >> 1] & 0xF0) | meta
                    if add is not None:
                        add[i >> 1] = (add[i >> 1] & 0xF0) | hi
                else:
                    d[i >> 1] = (d[i >> 1] & 0x0F) | (meta << 4)
                    if add is not None:
                        add[i >> 1] = (add[i >> 1] & 0x0F) | (hi << 4)

            for lx in range(16):
                for lz in range(16):
                    x, z = cx * 16 + lx, cz * 16 + lz
                    if not (X0 <= x <= x1 and Z0 <= z <= Z1):
                        continue
                    for y in range(GROUND - 3, GROUND):
                        setb(lx, y, lz, 3)
                    setb(lx, GROUND, lz, 2)
                    for y in range(GROUND + 1, CLEAR_TOP):
                        ident, meta = place.get((x, y, z), (0, 0))
                        setb(lx, y, lz, ident, meta)
            for sy, (bl, d, add) in arrays.items():
                s = secs[sy]
                s["Blocks"], s["Data"] = nbtlib.ByteArray(bl.view(np.int8)), nbtlib.ByteArray(d.view(np.int8))
                if add is not None:
                    s["Add"] = nbtlib.ByteArray(add.view(np.int8))
            # Height map: one above the top light-blocking block, so sky light starts right.
            ids, _ = W.blocks(lv)
            solid = ~np.isin(ids, list(TRANSPARENT))
            hm = np.zeros((16, 16), np.int32)
            for lz in range(16):
                for lx in range(16):
                    ys = np.nonzero(solid[:, lz, lx])[0]
                    hm[lz, lx] = (ys.max() + 1) if len(ys) else 0
            lv["HeightMap"] = nbtlib.IntArray(hm.ravel())
            lv["LightPopulated"] = nbtlib.Byte(0)
            buf = io.BytesIO()
            nbt.write(buf)
            chunks[(cx, cz)] = (zlib.compress(buf.getvalue()), 2, ts)
            touched += 1
    W.write_region(path, chunks)
    print("showcase wall: %d blocks in %d chunks -> %s" % (len(place), touched, path))


if __name__ == "__main__":
    main()
