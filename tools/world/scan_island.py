#!/usr/bin/env python3
"""Offline inspection of a 1.7.10 Anvil world for the decision-0003 proof of concept.

For every chunk in region/*.mca it reads TerrainPopulated, the stored biome array,
block IDs (with the Add nibble) and tile entities, then reports per painted biome
(the chunk's majority biome) and for the outskirts (chunks outside --painted-half):
  - chunks, populated chunks, KB per chunk
  - blocks per chunk by owning mod (names from level.dat's FML ItemData registry)
  - ore blocks per chunk (vanilla and modded), logs/leaves per chunk
  - spawners and other tile entities (dungeon / structure evidence), saved entities
  - the biome IDs the chunks carry
Optionally renders a top-down PNG (one pixel per block column, coloured by surface block).

    py -3.10 tools/world/scan_island.py WORLD_DIR [--painted-half 1280] [--png out.png]
        [--json out.json] [--biomes docs/survey/biome-ids.tsv] [--regions regions.json]
"""
import argparse, collections, glob, gzip, io, json, os, re, struct, zlib
import numpy as np
import nbtlib

VANILLA_ORES = {14: "gold_ore", 15: "iron_ore", 16: "coal_ore", 21: "lapis_ore", 56: "diamond_ore",
                73: "redstone_ore", 74: "lit_redstone_ore", 129: "emerald_ore"}
VANILLA_NAMES = {0: "air", 1: "stone", 2: "grass", 3: "dirt", 4: "cobblestone", 7: "bedrock",
                 8: "flowing_water", 9: "water", 10: "flowing_lava", 11: "lava", 12: "sand",
                 13: "gravel", 17: "log", 18: "leaves", 31: "tallgrass", 52: "mob_spawner",
                 78: "snow_layer", 79: "ice", 80: "snow", 81: "cactus", 161: "leaves2", 162: "log2"}
VANILLA_NAMES.update(VANILLA_ORES)


def load_registry(world):
    """block id -> registry name from level.dat FML ItemData (vanilla names as fallback)."""
    reg = {i: "minecraft:" + n for i, n in VANILLA_NAMES.items()}
    lvl = nbtlib.load(os.path.join(world, "level.dat"))
    fml = lvl.get("FML")
    if fml is not None and "ItemData" in fml:
        for e in fml["ItemData"]:
            k = str(e["K"])
            if k.startswith("\x01"):          # \x01 = block, \x02 = item
                reg[int(e["V"])] = k[1:]
    data = lvl["Data"]
    meta = {"generatorName": str(data.get("generatorName", "")), "seed": int(data.get("RandomSeed", 0)),
            "fml_registry": fml is not None}
    return reg, meta


def mod_of(name):
    return name.split(":", 1)[0] if ":" in name else "minecraft"


def is_ore(name, bid):
    if bid in VANILLA_ORES:
        return True
    path = name.split(":", 1)[-1]
    # camelCase / snake_case tokens: oreRuby, ore_titanium, RubyOre, amethystore...
    toks = [t.lower() for t in re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])", path)]
    return "ore" in toks or path.lower().startswith("ore") or path.lower().endswith("ore")


def chunks_in(region_path):
    with open(region_path, "rb") as f:
        data = f.read()
    if len(data) < 8192:
        return
    for i in range(1024):
        off = struct.unpack(">I", data[i * 4:i * 4 + 4])[0]
        sec, cnt = off >> 8, off & 0xFF
        if sec == 0 or cnt == 0:
            continue
        o = sec * 4096
        length, comp = struct.unpack(">IB", data[o:o + 5])
        raw = data[o + 5:o + 4 + length]
        raw = zlib.decompress(raw) if comp == 2 else gzip.decompress(raw)
        yield nbtlib.File.parse(io.BytesIO(raw)), cnt * 4096


def as_u8(tag):
    return np.frombuffer(np.asarray(tag, dtype=np.int8).tobytes(), np.uint8)


def chunk_blocks(level):
    """Flat array of 65536 block ids in (y, z, x) order, Add nibble applied."""
    ids = np.zeros(65536, np.uint16)
    for s in level.get("Sections", []):
        y = int(s["Y"])
        b = as_u8(s["Blocks"]).astype(np.uint16)
        if "Add" in s:
            add = as_u8(s["Add"])
            hi = np.empty(4096, np.uint16)
            hi[0::2] = add & 0x0F
            hi[1::2] = add >> 4
            b = b | (hi << 8)
        ids[y * 4096:(y + 1) * 4096] = b
    return ids


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("world")
    ap.add_argument("--painted-half", type=int, default=1280)
    ap.add_argument("--biomes", help="biome-ids.tsv (id, name, mod) to label biome IDs")
    ap.add_argument("--regions", help="make_test_island.py regions.json, to label painted regions")
    ap.add_argument("--png")
    ap.add_argument("--json")
    a = ap.parse_args()

    reg, meta = load_registry(a.world)
    names = {}
    if a.biomes:
        for line in open(a.biomes, encoding="utf-8"):
            if line.startswith("#") or line.startswith("id\t"):
                continue
            p = line.rstrip("\n").split("\t")
            names[int(p[0])] = f"{p[1]} [{p[2]}]"
    painted_label = {}
    if a.regions:
        for r in json.load(open(a.regions))["regions"]:
            painted_label[r["id"]] = r["name"]

    def bname(i):
        i = int(i)
        return reg.get(i, f"minecraft:#{i}" if i < 256 else f"?:{i}")

    nid = 4096
    ore_mask = np.array([is_ore(bname(i), i) for i in range(nid)])

    groups = collections.defaultdict(lambda: {
        "chunks": 0, "populated": 0, "bytes": 0, "blocks": np.zeros(nid, np.int64),
        "te": collections.Counter(), "ent": collections.Counter(), "biomes": np.zeros(256, np.int64)})
    surf = {}
    regions = sorted(glob.glob(os.path.join(a.world, "region", "*.mca")))
    total_bytes = sum(os.path.getsize(p) for p in regions)
    for rp in regions:
        for root, nbytes in chunks_in(rp):
            lv = root["Level"]
            cx, cz = int(lv["xPos"]), int(lv["zPos"])
            bio = as_u8(lv["Biomes"]) if "Biomes" in lv else np.full(256, 255, np.uint8)
            inside = max(abs(cx * 16 + 8), abs(cz * 16 + 8)) < a.painted_half
            maj = int(np.bincount(bio, minlength=256).argmax())
            g = groups[("painted", maj) if inside else ("outskirts", None)]
            g["chunks"] += 1
            g["populated"] += int(lv.get("TerrainPopulated", 0)) == 1
            g["bytes"] += nbytes
            g["biomes"] += np.bincount(bio, minlength=256)
            ids = chunk_blocks(lv)
            g["blocks"] += np.bincount(ids, minlength=nid)[:nid]
            for te in lv.get("TileEntities", []):
                g["te"][str(te.get("id", "?"))] += 1
            for en in lv.get("Entities", []):
                g["ent"][str(en.get("id", "?"))] += 1
            if a.png:
                col = ids.reshape(256, 16, 16)
                solid = col != 0
                top = 255 - np.argmax(solid[::-1], axis=0)
                tb = np.take_along_axis(col, top[None], 0)[0]
                surf[(cx, cz)] = (tb, top)

    def summarise(g):
        n = max(g["chunks"], 1)
        nz = np.nonzero(g["blocks"])[0]
        by_mod = collections.Counter()
        for i in nz:
            by_mod[mod_of(bname(i))] += int(g["blocks"][i])
        per = lambda i: round(float(g["blocks"][i]) / n, 2)
        ores = {bname(i): per(i) for i in nz if ore_mask[i]}
        wood = {bname(i): per(i) for i in nz if re.search(r"(log|leaves|leaf|wood)", bname(i).lower())}
        bop = {bname(i): per(i) for i in nz if bname(i).startswith("BiomesOPlenty:")}
        bt = [(int(b), names.get(int(b), str(int(b))), round(float(g["biomes"][b]) / 256 / n, 3))
              for b in np.argsort(-g["biomes"])[:12] if g["biomes"][b] > 0]
        return {
            "chunks": g["chunks"], "populated": g["populated"],
            "kb_per_chunk": round(g["bytes"] / n / 1024, 2),
            "non_vanilla_blocks_per_chunk": {m: round(c / n, 2) for m, c in by_mod.most_common() if m != "minecraft"},
            "ores_per_chunk": dict(sorted(ores.items(), key=lambda kv: -kv[1])),
            "bop_blocks_per_chunk": dict(sorted(bop.items(), key=lambda kv: -kv[1])[:20]),
            "logs_leaves_per_chunk": dict(sorted(wood.items(), key=lambda kv: -kv[1])),
            "tile_entities": dict(g["te"].most_common()),
            "spawners": g["te"].get("MobSpawner", 0),
            "entities": dict(g["ent"].most_common()),
            "biomes_top": bt,
        }

    out = {"world": os.path.abspath(a.world), "meta": meta, "region_files": len(regions),
           "region_mb": round(total_bytes / 1e6, 1), "groups": {}}
    for (kind, b), g in sorted(groups.items(), key=lambda kv: (kv[0][0], -kv[1]["chunks"])):
        label = "outskirts" if kind == "outskirts" else f"painted {b} {painted_label.get(b, names.get(b, ''))}"
        out["groups"][label] = summarise(g)
    allc = sum(g["chunks"] for g in groups.values())
    out["chunks"] = allc
    out["kb_per_chunk_on_disk"] = round(total_bytes / max(allc, 1) / 1024, 2)

    for label, s in out["groups"].items():
        if s["chunks"] < 4:
            continue
        print(f"== {label}: {s['chunks']} chunks, {s['populated']} populated, {s['kb_per_chunk']} KB/chunk")
        print(f"   biomes: {', '.join(f'{nm} {f:.0%}' for _, nm, f in s['biomes_top'][:5])}")
        print(f"   mods (blocks/chunk): {dict(list(s['non_vanilla_blocks_per_chunk'].items())[:8])}")
        print(f"   ores/chunk: {dict(list(s['ores_per_chunk'].items())[:12])}")
        print(f"   logs/leaves/chunk: {dict(list(s['logs_leaves_per_chunk'].items())[:8])}")
        print(f"   tile entities: {dict(list(s['tile_entities'].items())[:10])}")
        print(f"   entities: {dict(list(s['entities'].items())[:8])}")
    print(f"total {allc} chunks in {len(regions)} region files, {out['region_mb']} MB, "
          f"{out['kb_per_chunk_on_disk']} KB/chunk on disk (file size incl. sector padding)")
    if a.json:
        with open(a.json, "w") as f:
            json.dump(out, f, indent=1)
    if a.png and surf:
        render(surf, a.png, bname)


def render(surf, path, bname):
    from PIL import Image
    xs = [k[0] for k in surf]
    zs = [k[1] for k in surf]
    x0, z0 = min(xs), min(zs)
    w, h = (max(xs) - x0 + 1) * 16, (max(zs) - z0 + 1) * 16
    img = np.zeros((h, w, 3), np.uint8)
    lut = np.zeros((4096, 3), np.float32)
    for i in range(4096):
        n = bname(i).lower()
        c = (120, 120, 120)
        if i == 0: c = (0, 0, 0)
        elif "water" in n: c = (40, 70, 170)
        elif "lava" in n: c = (220, 90, 20)
        elif "leaves" in n or "leaf" in n: c = (30, 100, 30)
        elif "log" in n or "wood" in n: c = (100, 70, 40)
        elif n.endswith(":grass") or "grass" in n and "tall" not in n: c = (90, 150, 60)
        elif "sand" in n: c = (220, 205, 150)
        elif "snow" in n or "ice" in n: c = (235, 240, 250)
        elif "dirt" in n or "mud" in n: c = (120, 90, 60)
        elif "flower" in n or "plant" in n or "tallgrass" in n or "foliage" in n: c = (110, 170, 70)
        if n.startswith("biomesoplenty:") and "water" not in n:
            c = (min(255, c[0] + 60), c[1], min(255, c[2] + 60))   # BoP blocks tinted magenta
        lut[i] = c
    for (cx, cz), (tb, top) in surf.items():
        px, pz = (cx - x0) * 16, (cz - z0) * 16
        shade = np.clip(0.75 + (top.astype(np.float32) - 64) / 160.0, 0.5, 1.25)[..., None]
        img[pz:pz + 16, px:px + 16] = np.clip(lut[tb] * shade, 0, 255).astype(np.uint8)
    Image.fromarray(img).save(path)
    print(f"rendered {w}x{h} px -> {path} (top-left = chunk {x0},{z0})")


if __name__ == "__main__":
    main()
