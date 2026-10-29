#!/usr/bin/env python3
"""r011 texture scenes: copy the showcase world and add what the r007-pack copies are judged on.

    py -3.10 -I tools/textures/build_r011_world.py [--src C:\\qfb\\textures\\world-showcase] [--dst C:\\qfb\\textures\\world-r011]

All on cleared, levelled ground south of the showcase's farm and leaves (x 220-272, z 213-238):
  x 224-237, z 216  item board: 12 x 5 item frames facing north (weapons and tools; food; materials and
                    discs; every potion effect, drinkable then splash; enchanted books, worn tools and
                    stacks)                                                     (views r11_items, r11_items_close)
  x 240-250, z 216  library wall: 9 x 3 bookshelves in an oak frame          (views r11_library, r11_shelves)
  x 252-256, z 216  TNT: a 2 x 2 stack and a lone block                       (view r11_tnt)
  x 223-269, z 222-232  mob hall: an oak hall open to the north, glowstone in the roof and floor lamps, one of each mob
                    the Patrix skins cover, 2 blocks apart, facing the camera (views r11_mobs_a/b/c)
Mobs: PersistenceRequired, movementSpeed and followRange 0 (they stand still and target nothing, so no
potion particles), under a roof so zombies and skeletons never burn and endermen never teleport. They
need -Dqf.bench.difficulty=easy (FrameBench otherwise sets peaceful, which removes the hostile ones).
The roof means the hall's light is ours: sky and block light are flood-filled here (the game does not
relight a placed glowstone before FrameBench measures).

Never writes to --src. The copy is made once; the additions are rebuilt in it on every run.
"""
import argparse, io, os, shutil, sys, uuid, zlib
from collections import deque

import numpy as np
import nbtlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_showcase as bs  # noqa: E402  (region helpers)

W = bs.W
GROUND = 67
BOX = (220, 272, 213, 238)            # x0, x1, z0, z1: cleared and relit
TOP = 84
BOARD_Z, BOARD_X0 = 216, 224
HALL_X0, HALL_X1, HALL_Z0, HALL_Z1, HALL_Y1 = 223, 269, 222, 232, 73
MOB_Z = 228.5
BAT_BEAM_Y = 70                       # r013: an oak beam block the bat hangs under
PLANKS, GLOW, SHELF, TNT, BRICK = (5, 0), (89, 0), (47, 0), (46, 0), (98, 0)
OPAQUE_SKIP = {0, 20, 102, 95, 160, 8, 9}   # air, glass (and, for the r013 tank, water) let light through


def blocks():
    b = {}
    # item board, frames on its north face (y 69-73)
    for x in range(BOARD_X0, BOARD_X0 + 14):
        for y in range(68, 75):
            b[(x, y, BOARD_Z)] = BRICK
    # library: oak frame, 9 x 3 shelves
    for x in range(240, 251):
        for y in range(68, 73):
            edge = x in (240, 250) or y in (68, 72)
            b[(x, y, BOARD_Z)] = PLANKS if edge else SHELF
    # TNT: 2 x 2 and a lone block
    for x in (252, 253):
        for y in (68, 69):
            b[(x, y, BOARD_Z)] = TNT
    b[(256, 68, BOARD_Z)] = TNT
    # mob hall: oak floor, back wall, side walls, roof with glowstone every 3 blocks
    for x in range(HALL_X0, HALL_X1 + 1):
        for z in range(HALL_Z0, HALL_Z1 + 1):
            b[(x, GROUND, z)] = PLANKS
            b[(x, HALL_Y1, z)] = GLOW if (x % 2 == 0 and z % 2 == 0) else PLANKS
            if z == int(MOB_Z) and x % 2 == 1 and HALL_X0 < x < HALL_X1:
                b[(x, GROUND, z)] = GLOW                     # floor lamps between the mobs
        for y in range(68, HALL_Y1):
            b[(x, y, HALL_Z1)] = PLANKS
    for z in range(HALL_Z0, HALL_Z1 + 1):
        for y in range(68, HALL_Y1):
            b[(HALL_X0, y, z)] = PLANKS
            b[(HALL_X1, y, z)] = PLANKS
    return b


# --- entities ---------------------------------------------------------------------------------------------------
def _uuid(key):
    u = uuid.uuid5(uuid.NAMESPACE_DNS, "qf-r011-" + key)
    most, least = u.int >> 64, u.int & ((1 << 64) - 1)
    s = lambda v: v - (1 << 64) if v >= 1 << 63 else v   # noqa: E731
    return nbtlib.Long(s(most)), nbtlib.Long(s(least))


def _base(eid, pos, yaw, key):
    most, least = _uuid(key)
    return nbtlib.Compound({
        "id": nbtlib.String(eid), "Pos": nbtlib.List[nbtlib.Double](list(pos)),
        "Motion": nbtlib.List[nbtlib.Double]([0.0, 0.0, 0.0]),
        "Rotation": nbtlib.List[nbtlib.Float]([yaw, 0.0]),
        "FallDistance": nbtlib.Float(0), "Fire": nbtlib.Short(-1), "Air": nbtlib.Short(300),
        "OnGround": nbtlib.Byte(1), "Dimension": nbtlib.Int(0), "Invulnerable": nbtlib.Byte(0),
        "PortalCooldown": nbtlib.Int(0), "UUIDMost": most, "UUIDLeast": least})


def _item(ident, dmg=0, count=1, tag=None):
    c = nbtlib.Compound({"id": nbtlib.Short(ident), "Count": nbtlib.Byte(count), "Damage": nbtlib.Short(dmg)})
    if tag is not None:
        c["tag"] = tag
    return c


def _book(eid, lvl):
    return nbtlib.Compound({"StoredEnchantments": nbtlib.List[nbtlib.Compound](
        [nbtlib.Compound({"id": nbtlib.Short(eid), "lvl": nbtlib.Short(lvl)})])})


# 1.7.10 numeric ids (vanilla items keep these in every 1.7.10 world)
I = dict(dsword=276, dpick=278, daxe=279, isword=267, ipick=257, gsword=283, ssword=272, wsword=268, bow=261,
         shears=359, flint=259, rod=346, compass=345, clock=347, map=395, pearl=368, apple=260, gapple=322,
         bread=297, beef=364, pork=320, fish=350, cake=354, cookie=357, melon=360, carrot=391, potato=393,
         pie=400, diamond=264, emerald=388, gold=266, iron=265, redstone=331, glow=348, blaze=369, tear=370,
         star=399, slime=341, eye=381, cream=378, water=326, lava=327, milk=335, xp=384, cat=2257, saddle=329,
         tag=421, cart=328, boat=333, book=340, arrow=262, seeds=295, potion=373, ebook=403, dhelm=310,
         dchest=311, ileg=308, gboots=317)
POTIONS = [8193, 8194, 8195, 8196, 8197, 8198, 8200, 8201, 8202, 8204, 8205, 8206]   # every 1.7.10 effect
BOOKS = [(0, 4), (1, 4), (2, 4), (5, 3), (7, 3), (16, 5), (17, 5), (19, 2), (20, 2), (21, 3), (33, 1), (51, 1)]
BOARD = [   # top row first, 12 per row: (id, damage, count, tag)
    [(I[k], 0, 1, None) for k in ("dsword", "isword", "gsword", "bow", "dpick", "daxe", "shears", "flint", "rod",
                                  "compass", "clock", "map")],
    [(I[k], 0, 1, None) for k in ("apple", "gapple", "bread", "beef", "pork", "fish", "cake", "cookie", "melon",
                                  "carrot", "potato", "pie")],
    [(I[k], 0, 1, None) for k in ("diamond", "emerald", "gold", "iron", "redstone", "glow", "blaze", "tear", "star",
                                  "eye", "lava", "cat")],
    [(I["potion"], d, 1, None) for d in POTIONS[:6]] + [(I["potion"], d | 16384, 1, None) for d in (8193, 8196, 8197, 8201, 8204, 8206)],
    [(I["ebook"], 0, 1, _book(*e)) for e in BOOKS[:6]]
    + [(I["dsword"], 1300, 1, None), (I["ipick"], 200, 1, None), (I["arrow"], 0, 1, None), (I["arrow"], 0, 4, None),
       (I["arrow"], 0, 16, None), (I["potion"], 8229, 1, None)],
]


def frames():
    out = []
    for r, row in enumerate(BOARD):
        y = 73 - r
        for c, (ident, dmg, cnt, tag) in enumerate(row):
            x, z = BOARD_X0 + 1 + c, BOARD_Z
            e = _base("ItemFrame", (x + 0.5, y + 0.5, z + 0.5 - 0.5625), 180.0, "frame-%d-%d" % (x, y))
            e.update({"OnGround": nbtlib.Byte(0), "TileX": nbtlib.Int(x), "TileY": nbtlib.Int(y), "TileZ": nbtlib.Int(z),
                      "Direction": nbtlib.Byte(2), "Dir": nbtlib.Byte(2), "Item": _item(ident, dmg, cnt, tag),
                      "ItemDropChance": nbtlib.Float(1.0), "ItemRotation": nbtlib.Byte(0)})
            out.append(e)
    return out


# (entity id, extra tags, held item) in hall order; hostile first, then passive, golem and snowman last and far
# from the hostile ones (they would target them; followRange 0 should stop that anyway)
MOBS = [("Chicken", {}, None), ("Creeper", {}, None), ("Zombie", {}, None), ("Skeleton", {}, I["bow"]),
        ("Skeleton", {"SkeletonType": nbtlib.Byte(1)}, I["ssword"]), ("Spider", {}, None), ("CaveSpider", {}, None),
        ("Enderman", {}, None), ("PigZombie", {}, I["gsword"]), ("Witch", {}, None), ("Blaze", {}, None),
        ("Slime", {"Size": nbtlib.Int(1)}, None), ("LavaSlime", {"Size": nbtlib.Int(1)}, None),
        ("Silverfish", {}, None), ("Sheep", {"Color": nbtlib.Byte(0), "Sheared": nbtlib.Byte(0)}, None),
        ("Cow", {}, None), ("Pig", {}, None), ("Ozelot", {"CatType": nbtlib.Int(0)}, None), ("Wolf", {}, None),
        ("VillagerGolem", {}, None), ("SnowMan", {}, None)]
MOB_X0 = 226
MOB_DX = 2.0
# r012 (--round 12): every mob gets a non-vanilla skin, so the hall adds the passive mobs it lacked; 26 mobs 1.75 apart
# from x 225.0 in a hall widened to x 271 (still inside BOX). Views r12_mob_1..7 in views-r012.txt.
MOBS_R012 = MOBS[:19] + [("MushroomCow", {}, None), ("EntityHorse", {"Type": nbtlib.Int(0), "Variant": nbtlib.Int(0)}, None),
                         ("Villager", {"Profession": nbtlib.Int(0)}, None), ("Squid", {}, None),
                         ("Bat", {"BatFlags": nbtlib.Byte(1)}, None)] + MOBS[19:]


# r013 (--round 13): the hall in six tight groups (one per view, camera 4.5 blocks off), the wither skeleton centred in
# view 1 (the owner could not find it in r012), the bat on an oak beam at eye height (a roof speck in r012), and the
# squid, slime and magma cube moved to glass tanks north of the hall (r012: the squid died out of water, the slimes
# hopped out of frame). Views r13_mob_1..7 in views-r013.txt.
_M = {e[0] + ("1" if "SkeletonType" in e[1] else ""): e for e in MOBS_R012}   # Skeleton1 = the wither skeleton
GROUPS_R013 = [  # (centre x, mobs left to right as the camera sees them = east to west, so listed high x first)
    (228.0, ["Creeper", "Skeleton", "Skeleton1", "Zombie"]),
    (235.5, ["Silverfish", "Enderman", "CaveSpider", "Spider"]),
    (243.0, ["Chicken", "Blaze", "Witch", "PigZombie"]),
    (250.5, ["MushroomCow", "Pig", "Cow", "Sheep"]),
    (258.0, ["Villager", "EntityHorse", "Wolf", "Ozelot"]),
    (265.5, ["SnowMan", "VillagerGolem", "Bat"]),
]
MOBS_R013 = []
for _cx, _names in GROUPS_R013:
    for _k, _n in enumerate(_names):
        MOBS_R013.append((_cx + (len(_names) - 1 - 2 * _k) * 1.75 / 2,) + _M[_n])
TANK_Z0, TANK_Z1 = 218, 221                     # glass front and back
TANKS_R013 = [  # (glass x0, x1, inner top y, water?, entity, extra)
    (258, 262, 70, True, "Squid", {}),
    (262, 265, 69, False, "Slime", {"Size": nbtlib.Int(1)}),
    (265, 268, 70, False, "LavaSlime", {"Size": nbtlib.Int(1)}),
]
GLASS, WATER = (20, 0), (9, 0)


def blocks_r013():
    b = {}
    for x0, x1, ytop, water, _, _ in TANKS_R013:
        for x in range(x0, x1 + 1):
            for z in range(TANK_Z0, TANK_Z1 + 1):
                for y in range(68, ytop + 2):
                    shell = x in (x0, x1) or z in (TANK_Z0, TANK_Z1) or y == ytop + 1
                    if water and z > TANK_Z0 + 1:            # the squid's tank is one block deep: always in frame
                        shell = True
                    if shell:
                        b[(x, y, z)] = GLASS
                    elif water:
                        b[(x, y, z)] = WATER
    return b


def mobs():
    out = []
    for i, ent in enumerate(MOBS):
        if len(ent) == 4:                                          # r013: (x, eid, extra, held)
            x, (eid, extra, held) = ent[0] + 0.0, ent[1:]
        else:
            eid, extra, held = ent
            x = MOB_X0 + MOB_DX * i + 0.5
        y = HALL_Y1 - 0.95 if eid == "Bat" else GROUND + 1.0          # a bat hangs from the roof (BatFlags 1)
        if eid == "Bat" and len(ent) == 4:
            y = BAT_BEAM_Y - 0.95                                       # r013: from the beam
        e = _base(eid, (x, y, MOB_Z), 180.0, "mob-%d" % i)    # yaw 180: facing north, the camera
        e.update({"PersistenceRequired": nbtlib.Byte(1), "CanPickUpLoot": nbtlib.Byte(0),
                  "Attributes": nbtlib.List[nbtlib.Compound]([
                      nbtlib.Compound({"Name": nbtlib.String("generic.movementSpeed"), "Base": nbtlib.Double(0.0)}),
                      nbtlib.Compound({"Name": nbtlib.String("generic.followRange"), "Base": nbtlib.Double(0.0)}),
                      nbtlib.Compound({"Name": nbtlib.String("generic.knockbackResistance"), "Base": nbtlib.Double(1.0)})]),
                  "Equipment": nbtlib.List[nbtlib.Compound](
                      [_item(held) if held else nbtlib.Compound()] + [nbtlib.Compound() for _ in range(4)])})
        e.update(extra)
        out.append(e)
    if MOBS is MOBS_R013:
        for k, (x0, x1, ytop, water, eid, extra) in enumerate(TANKS_R013):
            zc = TANK_Z0 + 1.5 if water else (TANK_Z0 + TANK_Z1 + 1) / 2.0
            e = _base(eid, ((x0 + x1 + 1) / 2.0, 68.0 + (0.3 if water else 0.0), zc), 180.0,
                      "tank-%d" % k)
            e.update({"PersistenceRequired": nbtlib.Byte(1)})
            e.update(extra)
            out.append(e)
    return out


# --- light ------------------------------------------------------------------------------------------------------
def flood_light(place):
    """Sky and block light for the box, as vanilla spreads them: sky 15 down each open column, then both
    kinds spread through non-opaque cells losing 1 per step. Returns {(x, y, z): (sky, block)}."""
    x0, x1, z0, z1 = BOX
    y0 = GROUND - 1
    nx, ny, nz = x1 - x0 + 1, TOP - y0 + 1, z1 - z0 + 1
    opaque = np.zeros((nx, ny, nz), bool)
    opaque[:, :GROUND - y0 + 1, :] = True                  # the ground up to y 67
    for (x, y, z), (ident, _) in place.items():
        if x0 <= x <= x1 and z0 <= z <= z1 and y0 <= y <= TOP:
            opaque[x - x0, y - y0, z - z0] = ident not in OPAQUE_SKIP
    sky = np.zeros((nx, ny, nz), np.int8)
    blk = np.zeros((nx, ny, nz), np.int8)
    q = deque()
    for i in range(nx):
        for k in range(nz):
            for j in range(ny - 1, -1, -1):
                if opaque[i, j, k]:
                    break
                sky[i, j, k] = 15
                q.append((i, j, k))
    for (x, y, z), (ident, _) in place.items():
        if ident == GLOW[0] and x0 <= x <= x1 and z0 <= z <= z1:
            i, j, k = x - x0, y - y0, z - z0
            blk[i, j, k] = 15
    steps = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))

    def spread(arr, q):
        while q:
            i, j, k = q.popleft()
            v = arr[i, j, k] - 1
            if v <= 0:
                continue
            for di, dj, dk in steps:
                a, b, c = i + di, j + dj, k + dk
                if 0 <= a < nx and 0 <= b < ny and 0 <= c < nz and not opaque[a, b, c] and arr[a, b, c] < v:
                    arr[a, b, c] = v
                    q.append((a, b, c))
    spread(sky, q)
    spread(blk, deque(zip(*np.nonzero(blk))))
    return x0, y0, z0, sky, blk


def set_nibble(arr, i, v):
    if i % 2 == 0:
        arr[i >> 1] = (arr[i >> 1] & 0xF0) | v
    else:
        arr[i >> 1] = (arr[i >> 1] & 0x0F) | (v << 4)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", default=r"C:\qfb\textures\world-showcase")
    ap.add_argument("--dst", default=r"C:\qfb\textures\world-r011")
    ap.add_argument("--round", type=int, default=11, choices=(11, 12, 13))
    a = ap.parse_args()
    if a.round == 12:
        global MOBS, MOB_X0, MOB_DX, HALL_X1
        MOBS, MOB_X0, MOB_DX, HALL_X1 = MOBS_R012, 224.5, 1.75, 271
    if a.round == 13:
        MOBS, HALL_X1 = MOBS_R013, 271
    if os.path.abspath(a.src) == os.path.abspath(a.dst):
        sys.exit("--dst must differ from --src")
    if not os.path.exists(a.dst):
        shutil.copytree(a.src, a.dst)        # a real copy, never links (hard links write through)
        print("copied", a.src, "->", a.dst)
    lock = os.path.join(a.dst, "session.lock")
    if os.path.exists(lock):
        os.remove(lock)

    place = blocks()
    if a.round == 13:
        place.update(blocks_r013())
        bat_x = next(int(m[0]) for m in MOBS_R013 if m[1] == "Bat")
        place[(bat_x, BAT_BEAM_Y, int(MOB_Z))] = PLANKS
    ents = frames() + mobs()
    mine = {(int(e["UUIDMost"]), int(e["UUIDLeast"])) for e in ents}
    lx0, ly0, lz0, sky, blk = flood_light(place)
    x0, x1, z0, z1 = BOX
    path = os.path.join(a.dst, "region", "r.0.0.mca")
    chunks = W.read_region(path)
    todo = sorted({(cx, cz) for cx in range(x0 // 16, x1 // 16 + 1) for cz in range(z0 // 16, z1 // 16 + 1)})
    for cx, cz in todo:
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
                arrays[sy] = [W.u8(s["Blocks"]), W.u8(s["Data"]), W.u8(s["SkyLight"]), W.u8(s["BlockLight"]),
                              W.u8(s["Add"]) if "Add" in s else None]
            return arrays[sy]

        for lx in range(16):
            for lz in range(16):
                x, z = cx * 16 + lx, cz * 16 + lz
                if not (x0 <= x <= x1 and z0 <= z <= z1):
                    continue
                for y in range(GROUND - 3, TOP + 1):
                    if y < GROUND:
                        ident, meta = (3, 0)
                    elif y == GROUND:
                        ident, meta = place.get((x, y, z), (2, 0))
                    else:
                        ident, meta = place.get((x, y, z), (0, 0))
                    bl, d, sl, bkl, add = get(y >> 4)
                    i = (y & 15) * 256 + lz * 16 + lx
                    bl[i] = ident & 0xFF
                    set_nibble(d, i, meta)
                    if add is not None:
                        set_nibble(add, i, 0)
                    if y >= ly0:
                        set_nibble(sl, i, int(sky[x - lx0, y - ly0, z - lz0]))
                        set_nibble(bkl, i, int(blk[x - lx0, y - ly0, z - lz0]))
                for y in range(TOP + 1, 256):            # open sky above the box
                    if (y >> 4) in secs or (y >> 4) in arrays:
                        bl, d, sl, bkl, add = get(y >> 4)
                        set_nibble(sl, (y & 15) * 256 + lz * 16 + lx, 15)
        for sy, (bl, d, sl, bkl, add) in arrays.items():
            s = secs[sy]
            s["Blocks"], s["Data"] = nbtlib.ByteArray(bl.view(np.int8)), nbtlib.ByteArray(d.view(np.int8))
            s["SkyLight"], s["BlockLight"] = nbtlib.ByteArray(sl.view(np.int8)), nbtlib.ByteArray(bkl.view(np.int8))
            if add is not None:
                s["Add"] = nbtlib.ByteArray(add.view(np.int8))
        ids, _ = W.blocks(lv)
        solid = ~np.isin(ids, list(bs.TRANSPARENT))
        hm = np.zeros((16, 16), np.int32)
        for lz in range(16):
            for lx in range(16):
                ys = np.nonzero(solid[:, lz, lx])[0]
                hm[lz, lx] = (ys.max() + 1) if len(ys) else 0
        lv["HeightMap"] = nbtlib.IntArray(hm.ravel())
        old = lv.get("Entities") or nbtlib.List[nbtlib.Compound]()
        keep = [e for e in old if (int(e.get("UUIDMost", 0)), int(e.get("UUIDLeast", 0))) not in mine]
        for e in ents:
            px, pz = float(e["Pos"][0]), float(e["Pos"][2])
            if (int(px // 16), int(pz // 16)) == (cx, cz):
                keep.append(e)
        lv["Entities"] = nbtlib.List[nbtlib.Compound](keep)
        buf = io.BytesIO()
        nbt.write(buf)
        chunks[(cx, cz)] = (zlib.compress(buf.getvalue()), 2, ts)
    W.write_region(path, chunks)
    print("r011 scenes: %d blocks, %d item frames, %d mobs in %d chunks -> %s"
          % (len(place), len(frames()), len(MOBS), len(todo), path))


if __name__ == "__main__":
    main()
