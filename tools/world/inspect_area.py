#!/usr/bin/env python3
"""Offline inspection of populated test areas in a painted world (decision 0003).

For each square area it reads every chunk in range (region files in parallel) and reports:
  - chunks, populated chunks (TerrainPopulated), KB per chunk
  - stored biomes vs the plan (the expanded piece biome.png the world was built from)
  - per majority biome: logs/leaves, ores, BoP blocks and tile entities per chunk
  - spawners, chests and other tile entities; Recurrent Complex structures in the area
  - water where the plan has sea (plan height < 61) and land where it has land (> 63)
  - seams at x=0 / z=0 (piece edges): ground-height step and log density either side,
    against the same measures elsewhere in the area
and renders a top-down PNG (block colours, hillshade, seams marked) per area.

    py -3.10 tools/world/inspect_area.py WORLD --pieces PIECES_DIR --area NAME X Z R [--area ...]
        [--biomes docs/survey/biome-ids.tsv] [--png-dir DIR] [--json out.json] [--jobs 8]

PIECES_DIR holds plan.py expand output (piece_I_J/{height,biome}.png, origin.txt).
Block names come from level.dat's FML registry, so the world must have been loaded by the
server once. Helpers are shared with scan_island.py.
"""
import argparse, collections, glob, json, math, os, re, sys
from multiprocessing import Pool
import numpy as np
import nbtlib
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scan_island import chunks_in, chunk_blocks, as_u8, load_registry, is_ore  # noqa: E402

Image.MAX_IMAGE_PIXELS = None
SEA = 62
G = {}   # per-worker globals (category masks), set by _init


def categories(bname):
    n = 4096
    names = [bname(i).lower() for i in range(n)]
    path = [s.split(":", 1)[-1] for s in names]
    log = np.array([bool(re.search(r"(^|[^a-z])log|logs\d|^log", p)) or p in ("log", "log2") for p in path])
    leaves = np.array(["leaves" in p or "leaf" in p for p in path])
    veg = leaves | log | np.array([bool(re.search(
        r"plant|flower|tallgrass|double_plant|sapling|vine|ivy|foliage|coral|reed|cactus|mushroom|moss|"
        r"snow_layer|lily|waterlily|deadbush|fern|bamboo|kelp|seaweed|willow|web|torch|pumpkin|melon|crop|"
        r"stalk|hanging|petal|grassy|bush|sprout|lantern|^air$", p)) for p in path])
    water = np.array(["water" in p for p in path])
    ice = np.array([p in ("ice", "packed_ice") or p.endswith(":ice") for p in names])
    ore = np.array([is_ore(bname(i), i) for i in range(n)])
    veg[0] = True
    return {"log": log, "leaves": leaves, "veg": veg, "water": water, "ice": ice, "ore": ore}


def _init(cats):
    G.update(cats)


def scan_region(args):
    """Aggregate one region file's chunks that fall in [cx0..cx1] x [cz0..cz1]."""
    path, cx0, cx1, cz0, cz1 = args
    log, leaves, veg, water, ore = G["log"], G["leaves"], G["veg"], G["water"], G["ore"]
    out = {"groups": {}, "chunks": []}
    surf = {}
    for root, nbytes in chunks_in(path):
        lv = root["Level"]
        cx, cz = int(lv["xPos"]), int(lv["zPos"])
        if not (cx0 <= cx <= cx1 and cz0 <= cz <= cz1):
            continue
        bio = as_u8(lv["Biomes"]) if "Biomes" in lv else np.full(256, 255, np.uint8)
        maj = int(np.bincount(bio, minlength=256).argmax())
        ids = chunk_blocks(lv)
        cnt = np.bincount(ids, minlength=4096)[:4096]
        pop = int(lv.get("TerrainPopulated", 0)) == 1
        g = out["groups"].setdefault(maj, {"chunks": 0, "populated": 0, "bytes": 0,
                                           "blocks": np.zeros(4096, np.int64), "te": collections.Counter(),
                                           "ent": collections.Counter()})
        g["chunks"] += 1
        g["populated"] += pop
        g["bytes"] += nbytes
        g["blocks"] += cnt
        tes = []
        for te in lv.get("TileEntities", []):
            tid = str(te.get("id", "?"))
            g["te"][tid] += 1
            tes.append((tid, int(te.get("x", 0)), int(te.get("y", 0)), int(te.get("z", 0))))
        for en in lv.get("Entities", []):
            g["ent"][str(en.get("id", "?"))] += 1
        col = ids.reshape(256, 16, 16)
        top = 255 - np.argmax((col != 0)[::-1], axis=0)
        tb = np.take_along_axis(col, top[None], 0)[0]
        ground_mask = ~veg[col] & ~water[col]
        ground = 255 - np.argmax(ground_mask[::-1], axis=0)
        surf[(cx, cz)] = (tb.astype(np.uint16), top.astype(np.uint8), ground.astype(np.uint8), bio.reshape(16, 16))
        out["chunks"].append((cx, cz, pop, int(cnt[log].sum()), int(cnt[leaves].sum()), int(cnt[ore].sum()),
                              maj, tes))
    out["surf"] = surf
    return out


def piece_crop(pieces, name, x0, z0, w, h):
    """Crop a piece image (biome.png or height.png) mosaic to the block box [x0, x0+w) x [z0, z0+h)."""
    res = None
    for d in glob.glob(os.path.join(pieces, "piece_*")):
        ox, oz = map(int, open(os.path.join(d, "origin.txt")).read().split())
        im = Image.open(os.path.join(d, name))
        pw, ph = im.size
        ix0, iz0 = max(x0, ox), max(z0, oz)
        ix1, iz1 = min(x0 + w, ox + pw), min(z0 + h, oz + ph)
        if ix0 >= ix1 or iz0 >= iz1:
            continue
        a = np.asarray(im.crop((ix0 - ox, iz0 - oz, ix1 - ox, iz1 - oz)))
        if res is None:
            res = np.zeros((h, w), a.dtype)
        res[iz0 - z0:iz1 - z0, ix0 - x0:ix1 - x0] = a
    return res


def block_lut(bname):
    lut = np.zeros((4096, 3), np.float32)
    for i in range(4096):
        n = bname(i).lower()
        p = n.split(":", 1)[-1]
        c = (125, 125, 125)
        if i == 0: c = (0, 0, 0)
        elif "water" in p: c = (52, 88, 190)
        elif "lava" in p: c = (230, 100, 20)
        elif "leaves" in p or "leaf" in p:
            c = (38, 102, 38)
            if "biomesoplenty" in n: c = (70, 110, 45)
        elif re.search(r"log", p) or p.endswith("wood"): c = (104, 78, 46)
        elif p in ("grass",) or p.endswith("grass") and "tall" not in p: c = (96, 150, 62)
        elif "sand" in p and "stone" not in p: c = (219, 207, 160)
        elif "snow" in p or p in ("ice", "packed_ice"): c = (238, 242, 250)
        elif "dirt" in p or "mud" in p or "farmland" in p: c = (130, 96, 64)
        elif "gravel" in p: c = (140, 130, 125)
        elif "clay" in p or "hardened" in p: c = (160, 100, 70)
        elif "netherrack" in p or "ash" in p: c = (90, 80, 80)
        elif "obsidian" in p: c = (40, 30, 55)
        elif re.search(r"flower|plant|tallgrass|double_plant|foliage|fern|bush", p): c = (100, 165, 70)
        elif "mushroom" in p: c = (150, 110, 90)
        elif "cobble" in p or "brick" in p or "planks" in p or "chest" in p or "spawner" in p: c = (190, 60, 60)
        elif "stone" in p: c = (128, 128, 128)
        lut[i] = c
    return lut


def font(sz):
    try:
        return ImageFont.truetype("arial.ttf", sz)
    except OSError:
        return ImageFont.load_default()


def render(surf, box, path, title, lut):
    x0, z0, w, h = box
    tb = np.zeros((h, w), np.uint16)
    top = np.zeros((h, w), np.float32)
    have = np.zeros((h, w), bool)
    for (cx, cz), (b, t, _, _) in surf.items():
        px, pz = cx * 16 - x0, cz * 16 - z0
        if px < -15 or pz < -15 or px >= w or pz >= h:
            continue
        sx0, sz0 = max(0, -px), max(0, -pz)
        sx1, sz1 = min(16, w - px), min(16, h - pz)
        tb[pz + sz0:pz + sz1, px + sx0:px + sx1] = b[sz0:sz1, sx0:sx1]
        top[pz + sz0:pz + sz1, px + sx0:px + sx1] = t[sz0:sz1, sx0:sx1]
        have[pz + sz0:pz + sz1, px + sx0:px + sx1] = True
    rgb = lut[tb]
    gz, gx = np.gradient(top)
    shade = np.clip(1.0 + (-gx - gz) * 0.12, 0.55, 1.45)
    alt = 0.85 + 0.3 * np.clip((top - SEA) / 120, -0.3, 1)
    land = ~(tb == 8) & ~(tb == 9)
    rgb = np.where(land[..., None], rgb * (shade * alt)[..., None], rgb * (0.8 + 0.2 * shade)[..., None])
    rgb[~have] = (20, 20, 20)
    im = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))
    dr = ImageDraw.Draw(im)
    for sx in (0,):
        if x0 < sx < x0 + w:
            for z in range(0, h, 24):
                dr.line([(sx - x0, z), (sx - x0, z + 12)], fill=(255, 60, 60), width=1)
        if z0 < sx < z0 + h:
            for x in range(0, w, 24):
                dr.line([(x, sx - z0), (x + 12, sx - z0)], fill=(255, 60, 60), width=1)
    f = font(max(14, w // 70))
    dr.text((10, 8), title, fill="white", font=f, stroke_width=2, stroke_fill="black")
    # 500-block scale bar, bottom left
    y = h - 20
    dr.line([(12, y), (512, y)], fill="white", width=4)
    dr.text((12, y - 6), "500 blocks", fill="white", font=f, anchor="lb", stroke_width=2, stroke_fill="black")
    im.save(path, optimize=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("world")
    ap.add_argument("--pieces", required=True)
    ap.add_argument("--area", nargs=4, action="append", metavar=("NAME", "X", "Z", "R"), required=True)
    ap.add_argument("--biomes", default=os.path.join(os.path.dirname(__file__), "..", "..", "docs", "survey", "biome-ids.tsv"))
    ap.add_argument("--png-dir")
    ap.add_argument("--json")
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--tag", default="v0", help="render file prefix: DIR/<tag>-<area>.png")
    a = ap.parse_args()

    reg, meta = load_registry(a.world)
    bname = lambda i: reg.get(int(i), f"minecraft:#{int(i)}" if int(i) < 256 else f"?:{int(i)}")
    names = {}
    for line in open(a.biomes, encoding="utf-8"):
        if line.startswith("#") or line.startswith("id\t"):
            continue
        p = line.rstrip("\n").split("\t")
        names.setdefault(int(p[0]), f"{p[1]} [{p[2]}]")
    cats = categories(bname)
    lut = block_lut(bname)
    rc = rc_structures(a.world)
    report = {"world": os.path.abspath(a.world), "meta": meta, "areas": {}}

    with Pool(a.jobs, initializer=_init, initargs=(cats,)) as pool:
        for name, X, Z, R in a.area:
            X, Z, R = int(X), int(Z), int(R)
            bx0, bz0, bx1, bz1 = X - R, Z - R, X + R, Z + R
            cx0, cz0, cx1, cz1 = bx0 // 16, bz0 // 16, (bx1 - 1) // 16, (bz1 - 1) // 16
            regs = [os.path.join(a.world, "region", f"r.{rx}.{rz}.mca")
                    for rx in range(cx0 >> 5, (cx1 >> 5) + 1) for rz in range(cz0 >> 5, (cz1 >> 5) + 1)]
            regs = [r for r in regs if os.path.exists(r)]
            parts = pool.map(scan_region, [(r, cx0, cx1, cz0, cz1) for r in regs])
            groups, chunks, surf = {}, [], {}
            for p in parts:
                chunks += p["chunks"]
                surf.update(p["surf"])
                for b, g in p["groups"].items():
                    if b not in groups:
                        groups[b] = g
                    else:
                        t = groups[b]
                        for k in ("chunks", "populated", "bytes"):
                            t[k] += g[k]
                        t["blocks"] += g["blocks"]
                        t["te"].update(g["te"])
                        t["ent"].update(g["ent"])
            rep = summarise_area(name, (X, Z, R), groups, chunks, surf, bname, names, cats, a.pieces, rc)
            report["areas"][name] = rep
            print_area(name, rep)
            if a.png_dir:
                os.makedirs(a.png_dir, exist_ok=True)
                png = os.path.join(a.png_dir, f"{a.tag}-{name}.png")
                render(surf, (bx0, bz0, bx1 - bx0, bz1 - bz0), png,
                       f"{name}  centre {X},{Z}  r{R}  (populated, {meta['generatorName']})", lut)
                rep["png"] = png
                print(f"   render -> {png}")
            if a.json:
                with open(a.json, "w") as f:
                    json.dump(report, f, indent=1, default=str)


def rc_structures(world):
    """Recurrent Complex's generated structures as (structureID, [x, y, z] lower corner).

    On Windows the file is NOT data/reccomplex/structuredata.dat: Java wrote the name
    'reccomplex:structuredata.dat', which NTFS stores as an alternate data stream named
    structuredata.dat on an empty file 'reccomplex'. A directory listing shows a 0-byte file;
    open() with the colon path reads the stream."""
    out = []
    for p in (os.path.join(world, "data", "reccomplex:structuredata.dat"),
              os.path.join(world, "data", "reccomplex", "structuredata.dat")):
        try:
            d = nbtlib.load(p)
        except (OSError, ValueError, EOFError):
            continue
        for e in d.get("data", d).get("entries", []):
            if "lowerCoord_x" in e:
                out.append((str(e.get("structureID", "?")),
                            [int(e["lowerCoord_x"]), int(e.get("lowerCoord_y", 0)), int(e["lowerCoord_z"])]))
        break
    return out


def summarise_area(name, xzr, groups, chunks, surf, bname, names, cats, pieces, rc):
    X, Z, R = xzr
    x0, z0, w, h = X - R, Z - R, 2 * R, 2 * R
    n = sum(g["chunks"] for g in groups.values())
    rep = {"centre": [X, Z], "radius": R, "chunks": n,
           "populated": sum(g["populated"] for g in groups.values()),
           "kb_per_chunk": round(sum(g["bytes"] for g in groups.values()) / max(n, 1) / 1024, 2)}
    # Stored vs planned biome, ground vs planned height, water vs planned sea (per column).
    bio = np.full((h, w), 255, np.uint8)
    ground = np.zeros((h, w), np.float32)
    tb = np.zeros((h, w), np.uint16)
    have = np.zeros((h, w), bool)
    for (cx, cz), (b, t, gr, bi) in surf.items():
        px, pz = cx * 16 - x0, cz * 16 - z0
        sx0, sz0, sx1, sz1 = max(0, -px), max(0, -pz), min(16, w - px), min(16, h - pz)
        if sx0 >= sx1 or sz0 >= sz1:
            continue
        sl = (slice(pz + sz0, pz + sz1), slice(px + sx0, px + sx1))
        bio[sl], ground[sl], tb[sl] = bi[sz0:sz1, sx0:sx1], gr[sz0:sz1, sx0:sx1], b[sz0:sz1, sx0:sx1]
        have[sl] = True
    pb = piece_crop(pieces, "biome.png", x0, z0, w, h)
    ph = piece_crop(pieces, "height.png", x0, z0, w, h).astype(np.float32) / 257
    rep["biome_match_plan"] = round(float((bio == pb)[have].mean()), 4) if have.any() else None
    planned = collections.Counter(pb[have].tolist())
    stored = collections.Counter(bio[have].tolist())
    tot = max(int(have.sum()), 1)
    rep["biomes"] = [{"id": b, "name": names.get(b, str(b)), "plan_pct": round(100 * planned[b] / tot, 1),
                      "stored_pct": round(100 * stored[b] / tot, 1)}
                     for b, _ in (planned + stored).most_common(12)]
    dh = (ground - np.floor(ph))[have]
    rep["ground_minus_plan"] = {"mean": round(float(dh.mean()), 2), "mean_abs": round(float(np.abs(dh).mean()), 2),
                                "p99_abs": round(float(np.percentile(np.abs(dh), 99)), 1)}
    wet = cats["water"][tb] | cats["ice"][tb]
    sea, landp = (ph < SEA - 1) & have, (ph > SEA + 1) & have
    rep["water"] = {"plan_sea_cols": int(sea.sum()), "sea_is_water_pct": round(100 * float(wet[sea].mean()), 2) if sea.any() else None,
                    "plan_land_cols": int(landp.sum()), "land_is_water_pct": round(100 * float(wet[landp].mean()), 2) if landp.any() else None,
                    "ice_on_sea_pct": round(100 * float(cats["ice"][tb][sea].mean()), 2) if sea.any() else None}
    # Seams: the ground step across x=0 / z=0 vs every other column/row boundary in the area.
    seams = {}
    step_x = np.abs(np.diff(ground, axis=1))       # between column k and k+1 -> index k
    step_z = np.abs(np.diff(ground, axis=0))
    okx = have[:, 1:] & have[:, :-1]
    okz = have[1:] & have[:-1]
    logs_by_cx = collections.defaultdict(lambda: [0, 0])
    logs_by_cz = collections.defaultdict(lambda: [0, 0])
    for cx, cz, pop, nl, nlv, no, maj, _ in chunks:
        logs_by_cx[cx][0] += nl; logs_by_cx[cx][1] += 1
        logs_by_cz[cz][0] += nl; logs_by_cz[cz][1] += 1
    if x0 < 0 < x0 + w:
        k = -x0 - 1
        seams["x=0"] = {"ground_step_at_seam": round(float(step_x[:, k][okx[:, k]].mean()), 2),
                        "ground_step_elsewhere": round(float(step_x[okx].mean()), 2),
                        "plan_step_at_seam": round(float(np.abs(np.diff(ph, axis=1))[:, k].mean()), 2),
                        "logs_per_chunk_cx-1": round(logs_by_cx[-1][0] / max(logs_by_cx[-1][1], 1), 1),
                        "logs_per_chunk_cx0": round(logs_by_cx[0][0] / max(logs_by_cx[0][1], 1), 1),
                        "logs_per_chunk_area": round(sum(c[3] for c in chunks) / max(len(chunks), 1), 1)}
    if z0 < 0 < z0 + h:
        k = -z0 - 1
        seams["z=0"] = {"ground_step_at_seam": round(float(step_z[k][okz[k]].mean()), 2),
                        "ground_step_elsewhere": round(float(step_z[okz].mean()), 2),
                        "plan_step_at_seam": round(float(np.abs(np.diff(ph, axis=0))[k].mean()), 2),
                        "logs_per_chunk_cz-1": round(logs_by_cz[-1][0] / max(logs_by_cz[-1][1], 1), 1),
                        "logs_per_chunk_cz0": round(logs_by_cz[0][0] / max(logs_by_cz[0][1], 1), 1),
                        "logs_per_chunk_area": round(sum(c[3] for c in chunks) / max(len(chunks), 1), 1)}
    rep["seams"] = seams
    # Per majority-biome group.
    te_all, ent_all = collections.Counter(), collections.Counter()
    rep["groups"] = {}
    for b, g in sorted(groups.items(), key=lambda kv: -kv[1]["chunks"]):
        te_all.update(g["te"]); ent_all.update(g["ent"])
        if g["chunks"] < 8:
            continue
        nc = g["chunks"]
        nz = np.nonzero(g["blocks"])[0]
        per = lambda i: round(float(g["blocks"][i]) / nc, 2)
        top = lambda pred, k: dict(sorted(((bname(i), per(i)) for i in nz if pred(i)), key=lambda kv: -kv[1])[:k])
        rep["groups"][f"{b} {names.get(b, '')}"] = {
            "chunks": nc, "populated": g["populated"],
            "logs_per_chunk": round(float(g["blocks"][cats["log"]].sum()) / nc, 1),
            "leaves_per_chunk": round(float(g["blocks"][cats["leaves"]].sum()) / nc, 1),
            "logs_leaves": top(lambda i: cats["log"][i] or cats["leaves"][i], 8),
            "ores_per_chunk_total": round(float(g["blocks"][cats["ore"]].sum()) / nc, 1),
            "ores": top(lambda i: cats["ore"][i], 14),
            "bop": top(lambda i: bname(i).startswith("BiomesOPlenty:"), 10),
            "spawners": g["te"].get("MobSpawner", 0),
            "te": dict(g["te"].most_common(10)),
        }
    rep["tile_entities"] = dict(te_all.most_common(25))
    rep["entities"] = dict(ent_all.most_common(15))
    mods = collections.Counter()
    for g in groups.values():
        for i in np.nonzero(g["blocks"])[0]:
            m = bname(i).split(":", 1)[0] if ":" in bname(i) else "minecraft"
            if m != "minecraft":
                mods[m] += int(g["blocks"][i])
    rep["mod_blocks_per_chunk"] = {m: round(c / max(n, 1), 1) for m, c in mods.most_common(15)}
    allb = sum((g["blocks"] for g in groups.values()), np.zeros(4096, np.int64))
    rep["ores_per_chunk"] = {bname(i): round(float(allb[i]) / max(n, 1), 2)
                             for i in np.argsort(-allb) if cats["ore"][i] and allb[i] > 0}
    rep["spawners"] = te_all.get("MobSpawner", 0)
    inside = [s for s, c in rc if x0 <= c[0] < x0 + w and z0 <= c[2] < z0 + h]
    rep["reccomplex_structures"] = {"count": len(inside), "names": dict(collections.Counter(inside).most_common(12))}
    return rep


def print_area(name, r):
    print(f"== {name}: centre {r['centre']} r{r['radius']}: {r['chunks']} chunks, {r['populated']} populated, "
          f"{r['kb_per_chunk']} KB/chunk")
    print(f"   biome match plan {r['biome_match_plan']}; " +
          ", ".join(f"{b['name']} {b['plan_pct']}/{b['stored_pct']}%" for b in r["biomes"][:6]))
    print(f"   ground-plan {r['ground_minus_plan']}; water {r['water']}")
    for s, v in r["seams"].items():
        print(f"   seam {s}: {v}")
    for g, v in list(r["groups"].items())[:6]:
        print(f"   [{g}] {v['chunks']} ch: logs {v['logs_per_chunk']} leaves {v['leaves_per_chunk']} "
              f"ores {v['ores_per_chunk_total']} spawners {v['spawners']} | {dict(list(v['logs_leaves'].items())[:4])}")
    print(f"   TEs {dict(list(r['tile_entities'].items())[:12])}")
    print(f"   RC {r['reccomplex_structures']}; mods {dict(list(r['mod_blocks_per_chunk'].items())[:8])}")


if __name__ == "__main__":
    main()
