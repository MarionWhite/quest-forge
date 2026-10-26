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

--v1 adds what QF Textures v1 is judged on (2026-10-25, Shader Lab round 8), all on cleared, levelled
ground west and south of the first wall:
  x 226-241, z 178  wall 2: stone bricks (plain, mossy, cracked, carved), cobble and mossy
                    cobble, bookshelves 3x3, a dirt/grass step (grass and dirt sides), and
                    emerald/lapis/redstone/coal blocks             (view texture_wall2)
  x 222-242, z 194-204  a farm: wet farmland, a water channel, ripe wheat with a row of every
                    growth stage, carrots and potatoes               (view farm)
  x 244-256, z 196-206  leaves: one lone leaf block, a 4x2 hedge, a small oak (trunk + canopy)
                                                                     (views leaves_close, tree_close)
  x 262-269, z 200  a stone-brick board with 16 item frames facing north: 8 potions over
                    8 enchanted books, for custom item textures      (view items_frames)

--modded [LIST] adds a second wall of modded blocks east of the first (x 263-281, same z, five
rows y 73 down to 69, 19 per row, the list read left to right then down; the top row is glass
panes and modded glass for the connected-pane decision 0006), for the modded-block
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
V1_AREAS = [(220, 242, 176, 192), (220, 270, 193, 212)]   # x0, x1, z0, z1 cleared for --v1
WALL_Z = 178
CLEAR_TOP = 80
TRANSPARENT = {0, 20, 95, 102, 160}
MODDED_X0, MODDED_COLS, MODDED_ROWS = 263, 19, 5   # row 0 (y 73): glass panes and modded glass, decision 0006
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


def v1_blocks():
    """{(x, y, z): (id, meta)} for --v1 (module docstring). y GROUND entries replace the grass."""
    b = {}
    for x in range(225, 243):
        b[(x, 68, WALL_Z)] = (1, 0)
    for x in range(226, 229):                       # stone bricks 3 wide: plain, plain, mossy, carved
        for y, m in zip(range(69, 73), (0, 0, 1, 3)):
            b[(x, y, WALL_Z)] = (98, m)
    b[(228, 69, WALL_Z)] = (98, 2)                  # one cracked
    for x in (230, 231):                            # cobble, mossy cobble on top
        for y in range(69, 73):
            b[(x, y, WALL_Z)] = (48 if y == 72 else 4, 0)
    for x in range(233, 236):                       # bookshelves 3x3
        for y in range(69, 72):
            b[(x, y, WALL_Z)] = (47, 0)
    b[(237, 69, WALL_Z)] = (3, 0)                   # dirt / grass step: grass sides and dirt
    b[(237, 70, WALL_Z)] = (3, 0)
    b[(237, 71, WALL_Z)] = (2, 0)
    b[(238, 69, WALL_Z)] = (2, 0)
    b[(238, 69, WALL_Z + 1)] = (2, 0)
    b[(237, 69, WALL_Z + 1)] = (3, 0)
    b[(237, 70, WALL_Z + 1)] = (2, 0)
    for x in (240, 241):                            # coal, redstone, lapis, emerald (bottom up)
        for y, ident in zip(range(69, 73), (173, 152, 22, 133)):
            b[(x, y, WALL_Z)] = (ident, 0)
    # farm
    for x in range(222, 243):
        for z in range(194, 205):
            water = x == 232
            b[(x, GROUND, z)] = (9, 0) if water else (60, 7)
            if water:
                continue
            if x < 225:
                b[(x, 68, z)] = (141, 7)            # carrots
            elif x > 239:
                b[(x, 68, z)] = (142, 7)            # potatoes
            elif z == 204:
                b[(x, 68, z)] = (59, (x - 225) % 8)  # every growth stage along the front row
            else:
                b[(x, 68, z)] = (59, 7)
    # leaves (meta 4 = oak, never decays): a lone block, a hedge, a small oak
    b[(245, 68, 199)] = (18, 4)
    for x in range(247, 251):
        for y in (68, 69):
            b[(x, y, 199)] = (18, 4)
    tx, tz = 253, 202
    for y in range(68, 73):
        b[(tx, y, tz)] = (17, 0)
    for y in range(71, 75):
        rr = 2 if y < 73 else 1
        for x in range(tx - rr, tx + rr + 1):
            for z in range(tz - rr, tz + rr + 1):
                if (x, y, z) in b:
                    continue
                if abs(x - tx) == rr and abs(z - tz) == rr and (y == 72 or (x + z + y) % 2):
                    continue                        # round the canopy's corners
                b[(x, y, z)] = (18, 4)
    b[(tx, 75, tz)] = (18, 4)
    # item board
    for x in range(261, 271):
        for y in range(68, 72):
            b[(x, y, 200)] = (98, 0)
    return b


# Item frames on the board (x 262-269, y 70 potions, y 69 books), facing north (Direction 2).
FRAME_POTIONS = [8193, 8194, 8195, 8197, 8198, 8201, 8205, 16388]      # regen, swift, fire res,
#   healing, night vision, strength, water breathing, splash poison
FRAME_BOOKS = [(0, 4), (16, 5), (20, 2), (32, 5), (33, 1), (34, 3), (35, 3), (48, 5)]   # protection,
#   sharpness, fire aspect, efficiency, silk touch, unbreaking, fortune, power


def item_frames(ids):
    """[(chunk x, chunk z, entity Compound)] for the board's frames. ids: the world's item ids."""
    import uuid
    out = []
    pot, book = ids.get("minecraft:potion", 373), ids.get("minecraft:enchanted_book", 403)
    rows = [(70, [(pot, d, None) for d in FRAME_POTIONS]), (69, [(book, 0, e) for e in FRAME_BOOKS])]
    for y, items in rows:
        for i, (ident, dmg, ench) in enumerate(items):
            x, z = 262 + i, 200
            item = nbtlib.Compound({"id": nbtlib.Short(ident), "Count": nbtlib.Byte(1), "Damage": nbtlib.Short(dmg)})
            if ench:
                item["tag"] = nbtlib.Compound({"StoredEnchantments": nbtlib.List[nbtlib.Compound](
                    [nbtlib.Compound({"id": nbtlib.Short(ench[0]), "lvl": nbtlib.Short(ench[1])})])})
            u = uuid.uuid5(uuid.NAMESPACE_DNS, f"qf-frame-{x}-{y}")
            most, least = (u.int >> 64), u.int & ((1 << 64) - 1)

            def sgn(v):
                return v - (1 << 64) if v >= 1 << 63 else v
            e = nbtlib.Compound({
                "id": nbtlib.String("ItemFrame"),
                "Pos": nbtlib.List[nbtlib.Double]([x + 0.5, y + 0.5, z + 0.5 - 0.5625]),
                "Motion": nbtlib.List[nbtlib.Double]([0.0, 0.0, 0.0]),
                "Rotation": nbtlib.List[nbtlib.Float]([180.0, 0.0]),
                "FallDistance": nbtlib.Float(0), "Fire": nbtlib.Short(-1), "Air": nbtlib.Short(300),
                "OnGround": nbtlib.Byte(0), "Dimension": nbtlib.Int(0), "Invulnerable": nbtlib.Byte(0),
                "PortalCooldown": nbtlib.Int(0),
                "UUIDMost": nbtlib.Long(sgn(most)), "UUIDLeast": nbtlib.Long(sgn(least)),
                "TileX": nbtlib.Int(x), "TileY": nbtlib.Int(y), "TileZ": nbtlib.Int(z),
                "Direction": nbtlib.Byte(2), "Dir": nbtlib.Byte(2),
                "Item": item, "ItemDropChance": nbtlib.Float(1.0), "ItemRotation": nbtlib.Byte(0)})
            out.append((x >> 4, z >> 4, e))
    return out


def item_ids(world):
    """{'modid:name': id} for items, from the world's level.dat (FML item keys start with \\x02)."""
    root = nbtlib.load(os.path.join(world, "level.dat"))
    fml = root["FML"] if "FML" in root else root[""]["FML"]
    return {str(e["K"])[1:]: int(e["V"]) for e in fml["ItemData"] if str(e["K"]).startswith("\x02")}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", default=r"C:\qfb\world-master")
    ap.add_argument("--dst", default=r"C:\qfb\textures\world-showcase")
    ap.add_argument("--modded", nargs="?", const=os.path.join(HERE, "showcase-modded.txt"),
                    help="also build the modded-block wall from this list (default: tools/textures/showcase-modded.txt)")
    ap.add_argument("--v1", action="store_true", help="also build the QF Textures v1 scenes (module docstring)")
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
    areas = [(X0, x1, Z0, Z1)]
    frames = []
    if a.v1:
        place.update(v1_blocks())
        areas += V1_AREAS
        frames = item_frames(item_ids(a.dst))
        print("v1 scenes: wall 2, farm, leaves, %d item frames" % len(frames))
    path = os.path.join(a.dst, "region", "r.0.0.mca")
    chunks = W.read_region(path)
    touched = 0
    todo = sorted({(cx, cz) for ax0, ax1, az0, az1 in areas
                   for cx in range(ax0 // 16, ax1 // 16 + 1) for cz in range(az0 // 16, az1 // 16 + 1)})
    for cx, cz in todo:
        if True:
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
                    if not any(ax0 <= x <= ax1 and az0 <= z <= az1 for ax0, ax1, az0, az1 in areas):
                        continue
                    for y in range(GROUND - 3, GROUND):
                        setb(lx, y, lz, 3)
                    setb(lx, GROUND, lz, *place.get((x, GROUND, z), (2, 0)))
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
            # item frames: drop any frame this script placed before, then add this run's
            ents = lv.get("Entities") or nbtlib.List[nbtlib.Compound]()
            mine = {(int(e["TileX"]), int(e["TileY"]), int(e["TileZ"])) for _, _, e in frames}
            keep = [e for e in ents if not (str(e.get("id")) == "ItemFrame" and "TileX" in e
                                            and (int(e["TileX"]), int(e["TileY"]), int(e["TileZ"])) in mine)]
            keep += [e for fx, fz, e in frames if (fx, fz) == (cx, cz)]
            if frames or ents:
                lv["Entities"] = nbtlib.List[nbtlib.Compound](keep)
            lv["LightPopulated"] = nbtlib.Byte(0)
            buf = io.BytesIO()
            nbt.write(buf)
            chunks[(cx, cz)] = (zlib.compress(buf.getvalue()), 2, ts)
            touched += 1
    W.write_region(path, chunks)
    print("showcase wall: %d blocks in %d chunks -> %s" % (len(place), touched, path))


if __name__ == "__main__":
    main()
