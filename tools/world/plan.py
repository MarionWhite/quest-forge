"""Low-resolution world plan -> full-resolution WorldPainter pieces (decision 0003).

The plan is drawn at 1 pixel = 16 blocks (one chunk) and lives in a directory as three
hand-editable images:
  height.png  16-bit grey, value = y * 257 (sea level 62)
  biome.png   8-bit grey, value = biome ID (docs/survey/biome-ids.tsv; 255 is never used)
  relief.png  8-bit grey, how much fine detail the expansion adds there (0 flat .. 255 craggy)

  py -3.10 tools/world/plan.py render SPEC.yaml PLANDIR      # draft the plan from a design spec
  py -3.10 tools/world/plan.py preview PLANDIR               # colour map with labels -> PLANDIR/preview.png
  py -3.10 tools/world/plan.py expand PLANDIR OUTDIR --piece I J [--piece-size 16384]

`expand` writes OUTDIR/piece_I_J/{height.png,biome.png,origin.txt} for tools/world/wp_piece.js.
All noise is a function of world coordinates, so neighbouring pieces meet without a seam.
"""
import argparse, json, math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

PX = 16          # blocks per plan pixel
SEA = 62
OCEAN, DEEP_OCEAN, RIVER, BEACH, STONE_BEACH = 0, 24, 7, 16, 25


# ---------------------------------------------------------------- noise (world-coordinate)

def _hash(ix, iz, seed):
    h = (ix.astype(np.int64) * 374761393 + iz.astype(np.int64) * 668265263 + seed * 2246822519) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFFFF) / float(0xFFFFFF)


def value_noise(x, z, cell, seed):
    """Smooth value noise in [-1, 1] at world coords x, z (arrays, blocks)."""
    fx, fz = x / cell, z / cell
    ix, iz = np.floor(fx).astype(np.int64), np.floor(fz).astype(np.int64)
    tx, tz = fx - ix, fz - iz
    tx, tz = tx * tx * (3 - 2 * tx), tz * tz * (3 - 2 * tz)
    a, b = _hash(ix, iz, seed), _hash(ix + 1, iz, seed)
    c, d = _hash(ix, iz + 1, seed), _hash(ix + 1, iz + 1, seed)
    return (a + (b - a) * tx + (c - a) * tz + (a - b - c + d) * tx * tz) * 2 - 1


def fbm(x, z, cell, octaves, seed, gain=0.5):
    total, amp, norm = 0.0, 1.0, 0.0
    for o in range(octaves):
        total = total + amp * value_noise(x, z, cell, seed + o * 101)
        norm += amp
        amp *= gain
        cell /= 2.0
    return total / norm


def ridged(x, z, cell, octaves, seed):
    """Ridged multifractal in [0, 1]: sharp crests where the noise crosses zero."""
    total, amp, norm, prev = 0.0, 1.0, 0.0, 1.0
    for o in range(octaves):
        r = (1 - np.abs(value_noise(x, z, cell, seed + o * 131))) ** 2
        total = total + amp * r * prev
        prev = r
        norm += amp
        amp *= 0.5
        cell /= 2.0
    return total / norm


# ---------------------------------------------------------------- render: spec -> plan

def _poly(draw_size, pts, size):
    """Spec coordinates are blocks with 0,0 at the centre; return plan-pixel tuples."""
    half = size / 2
    return [((x + half) / PX, (z + half) / PX) for x, z in pts]


def region_polygon(r):
    """A region is a polygon, a ring sector {sector: [deg0, deg1, r0, r1]} (0 deg = east,
    90 = south, as Minecraft's +z) or a circle {circle: [x, z, radius]}."""
    if "polygon" in r:
        return r["polygon"]
    if "sector" in r:
        a0, a1, r0, r1 = r["sector"]
        if a1 < a0:
            a1 += 360
        steps = max(4, int((a1 - a0) / 3))
        angs = [math.radians(a0 + (a1 - a0) * i / steps) for i in range(steps + 1)]
        outer = [(r1 * math.cos(a), r1 * math.sin(a)) for a in angs]
        inner = [(r0 * math.cos(a), r0 * math.sin(a)) for a in reversed(angs)] if r0 > 0 else [(0, 0)]
        return outer + inner
    x, z, rad = r["circle"]
    return [(x + rad * math.cos(2 * math.pi * i / 32), z + rad * math.sin(2 * math.pi * i / 32)) for i in range(32)]


def render(spec_path, plan_dir):
    import yaml
    spec = yaml.safe_load(open(spec_path, encoding="utf-8"))
    for r in spec["regions"]:
        r["polygon"] = region_polygon(r)
    size = spec["size"]
    n = size // PX
    seed = spec.get("seed", 1)
    half = size / 2
    gx, gz = np.meshgrid((np.arange(n) + 0.5) * PX - half, (np.arange(n) + 0.5) * PX - half)

    # Land: the coast polygon, its edge broken up by domain warp.
    warp = spec.get("coast_warp", 600)
    wx = gx + warp * fbm(gx, gz, 2400, 4, seed + 1)
    wz = gz + warp * fbm(gx, gz, 2400, 4, seed + 2)
    img = Image.new("L", (n, n), 0)
    ImageDraw.Draw(img).polygon(_poly(n, spec["coast"], size), fill=255)
    for isl in spec.get("islands", []):
        ImageDraw.Draw(img).polygon(_poly(n, isl, size), fill=255)
    land0 = np.asarray(img) > 0
    land = ndimage.map_coordinates(land0.astype(np.float32), [(wz + half) / PX - 0.5, (wx + half) / PX - 0.5],
                                   order=1, mode="constant") > 0.5
    for lake in spec.get("lakes", []):
        li = Image.new("L", (n, n), 0)
        ImageDraw.Draw(li).polygon(_poly(n, lake["polygon"], size), fill=255)
        land &= ~(np.asarray(li) > 0)

    d_in = ndimage.distance_transform_edt(land) * PX       # blocks to the sea, on land
    d_out = ndimage.distance_transform_edt(~land) * PX     # blocks to land, at sea

    # Regions: biome, base height and relief, blended across a soft border.
    biome = np.full((n, n), OCEAN, np.uint8)
    base = np.zeros((n, n), np.float32)
    relief = np.zeros((n, n), np.float32)
    weight = np.zeros((n, n), np.float32)
    owner = np.full((n, n), -1, np.int32)
    rwarp = spec.get("region_warp", 500)
    rx = gx + rwarp * fbm(gx, gz, 1800, 4, seed + 3)
    rz = gz + rwarp * fbm(gx, gz, 1800, 4, seed + 4)
    sea_regions = []
    for k, r in enumerate(spec["regions"]):
        ri = Image.new("L", (n, n), 0)
        ImageDraw.Draw(ri).polygon(_poly(n, r["polygon"], size), fill=255)
        m = ndimage.map_coordinates((np.asarray(ri) > 0).astype(np.float32),
                                    [(rz + half) / PX - 0.5, (rx + half) / PX - 0.5], order=1, mode="constant") > 0.5
        if r.get("sea"):          # a sea biome (reef, kelp): painted over water only, after the floor
            sea_regions.append((m, r["biome"]))
            continue
        m &= land
        owner[m & (owner < 0)] = k
        soft = ndimage.gaussian_filter(m.astype(np.float32), spec.get("blend_px", 12))
        base += soft * r.get("base", 72)
        relief += soft * r.get("relief", 60)
        weight += soft
    unowned = land & (owner < 0)
    if unowned.any():   # land outside every region takes its nearest region
        idx = ndimage.distance_transform_edt(owner < 0, return_distances=False, return_indices=True)
        owner[unowned] = owner[idx[0][unowned], idx[1][unowned]]
    ids = np.array([r["biome"] for r in spec["regions"]], np.uint8)   # sea regions never own land
    biome[land] = ids[owner[land]]
    w = np.maximum(weight, 1e-3)
    base, relief = base / w, relief / w

    # Height: region base, eased down to the shore, plus mountain ridges.
    shore = np.clip(d_in / spec.get("shore_width", 700), 0, 1)
    shore = shore * shore * (3 - 2 * shore)
    # Rolling hills scaled by relief, so lowlands are not billiard tables.
    hills = fbm(gx, gz, 1600, 4, seed + 5) * (4 + relief * 0.12)
    h = np.where(land, SEA + 2 + (base + hills - SEA - 2) * shore, 0).astype(np.float32)
    for ridge in spec.get("ridges", []):
        if "arc" in ridge:        # {arc: [x, z, radius, deg0, deg1]}
            cx, cz, rad, a0, a1 = ridge["arc"]
            if a1 < a0:
                a1 += 360
            steps = max(2, int((a1 - a0) / 4))
            ridge["points"] = [(cx + rad * math.cos(math.radians(a0 + (a1 - a0) * i / steps)),
                                cz + rad * math.sin(math.radians(a0 + (a1 - a0) * i / steps))) for i in range(steps + 1)]
        pts = _poly(n, ridge["points"], size)
        ri = Image.new("L", (n, n), 0)
        ImageDraw.Draw(ri).line(pts, fill=255, width=1)
        d = ndimage.distance_transform_edt(~(np.asarray(ri) > 0)) * PX
        jag = 1 + 0.45 * fbm(gx, gz, 900, 4, seed + 7)
        prof = np.clip(1 - d / (ridge["width"] / 2 * jag), 0, 1)
        prof = prof * prof * (3 - 2 * prof)
        # Peaks and saddles along the crest, spurs off it: ridged noise, not a smooth tube.
        crest = 0.55 + 0.45 * ridged(gx, gz, ridge.get("peak_spacing", 1400), 5, seed + 8)
        h = np.where(land, np.maximum(h, h + (ridge["height"] - SEA) * prof * crest * shore), h)
        relief = np.maximum(relief, np.where(prof > 0.05, ridge.get("relief", 200) * np.minimum(1, prof * 3), 0))
        if "biome" in ridge:
            biome[land & (prof > ridge.get("biome_above", 0.35))] = ridge["biome"]
    # Sea floor: shelf, then deep water.
    depth = np.clip(d_out / spec.get("shelf_width", 1200), 0, 1)
    h = np.where(land, h, SEA - 4 - (SEA - 4 - spec.get("deep_floor", 28)) * depth)
    biome[~land & (depth > 0.6)] = DEEP_OCEAN
    for m, b in sea_regions:
        biome[m & ~land] = b

    # Rivers: carved channels, river biome.
    for river in spec.get("rivers", []):
        ri = Image.new("L", (n, n), 0)
        ImageDraw.Draw(ri).line(_poly(n, river["points"], size), fill=255, width=max(1, round(river.get("width", 32) / PX)))
        m = (np.asarray(ri) > 0) & land
        d = ndimage.distance_transform_edt(~m) * PX
        bank = np.clip(d / river.get("valley", 160), 0, 1) ** 0.5
        h = np.where(land, np.minimum(h, SEA - 3 + (h - SEA + 3) * bank), h)
        biome[m] = RIVER
        relief = np.where(m, 0, relief)
    # Within a few pixels of the coast, height follows a blurred land mask, so the sea-level
    # contour is smooth after cubic upsampling instead of a 16-block staircase.
    cf = ndimage.gaussian_filter(land.astype(np.float32), 1.2)
    near = np.clip(np.where(land, d_in, d_out) / (3 * PX), 0, 1)
    h = h * near + (SEA + (cf - 0.5) * 16) * (1 - near)
    beach = land & (d_in <= spec.get("beach_width", 48)) & (h < SEA + 6)
    biome[beach & (biome != RIVER)] = BEACH

    os.makedirs(plan_dir, exist_ok=True)
    Image.fromarray(np.clip(h * 257, 0, 65535).astype(np.uint16)).save(f"{plan_dir}/height.png")
    Image.fromarray(biome).save(f"{plan_dir}/biome.png")
    Image.fromarray(np.clip(relief, 0, 255).astype(np.uint8)).save(f"{plan_dir}/relief.png")
    meta = {k: spec[k] for k in ("size", "seed") if k in spec}
    # Regions are labelled by their real biome name, never an invented one.
    names = biome_names()
    meta["labels"] = [{"name": names.get(r["biome"], f"biome {r['biome']}") + (f" (T{r['tier']})" if "tier" in r else ""),
                       "polygon": r["polygon"]} for r in spec["regions"]]
    meta["points"] = spec.get("points", [])
    json.dump(meta, open(f"{plan_dir}/plan.json", "w"), indent=1)
    print(f"plan {n}x{n} px ({size} blocks): land {land.mean():.0%}, max y {h.max():.0f}")


# ---------------------------------------------------------------- preview

MOD_PREFIX = {"Biomes O' Plenty": "BoP ", "Realistic World Gen": "RWG ", "Welcome to the Jungle": "Jungle "}


def biome_names():
    """id -> name as the game shows it, prefixed by mod (e.g. 'BoP Redwood Forest')."""
    tsv = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "survey", "biome-ids.tsv")
    out = {}
    for line in open(tsv, encoding="utf-8"):
        if line.startswith("#") or line.startswith("id\t"):
            continue
        f = line.rstrip("\n").split("\t")
        out.setdefault(int(f[0]), MOD_PREFIX.get(f[2], "") + f[1])
    return out


def preview(plan_dir):
    h = np.asarray(Image.open(f"{plan_dir}/height.png")).astype(np.float32) / 257
    b = np.asarray(Image.open(f"{plan_dir}/biome.png"))
    meta = json.load(open(f"{plan_dir}/plan.json"))
    rng = np.random.default_rng(7)
    lut = rng.integers(60, 220, (256, 3)).astype(np.float32)
    lut[OCEAN], lut[DEEP_OCEAN], lut[RIVER], lut[BEACH] = (60, 110, 190), (30, 60, 140), (70, 130, 220), (220, 205, 150)
    rgb = lut[b]
    gy, gx = np.gradient(h)
    shade = np.clip(1 + (gx - gy) * 0.06, 0.6, 1.4)[..., None]
    land = h >= SEA
    rgb = np.where(land[..., None], rgb * shade * (0.75 + 0.35 * np.clip((h - SEA) / 140, 0, 1))[..., None], rgb)
    im = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))
    n = b.shape[0]
    scale = max(1, 2048 // n)
    im = im.resize((n * scale, n * scale), Image.NEAREST)
    dr = ImageDraw.Draw(im)
    try:
        font = ImageFont.truetype("arial.ttf", max(12, n * scale // 110))
    except OSError:
        font = ImageFont.load_default()
    half, k = meta["size"] / 2, scale / PX
    names = biome_names()
    for lab in meta["labels"]:
        # Label at the polygon's area centroid (a ring sector's vertex mean sits off the ring).
        pts = lab["polygon"]
        a = cx = cz = 0.0
        for (x1, z1), (x2, z2) in zip(pts, pts[1:] + pts[:1]):
            c = x1 * z2 - x2 * z1
            a, cx, cz = a + c, cx + (x1 + x2) * c, cz + (z1 + z2) * c
        if abs(a) < 1e-6:
            continue
        cx, cz = (cx / (3 * a) + half) * k, (cz / (3 * a) + half) * k
        dr.text((cx, cz), lab["name"], fill="white", font=font, anchor="mm", stroke_width=2, stroke_fill="black")
    for p in meta["points"]:
        x, z = (p["x"] + half) * k, (p["z"] + half) * k
        col = {"spawn": "#ffe14d", "landmark": "#ff5050"}.get(p.get("kind"), "white")
        dr.ellipse((x - 6, z - 6, x + 6, z + 6), fill=col, outline="black")
        label = p.get("name") or (p.get("kind", "point").capitalize() + (f" T{p['tier']}" if "tier" in p else ""))
        dr.text((x + 9, z), label, fill=col, font=font, anchor="lm", stroke_width=2, stroke_fill="black")
    im.save(f"{plan_dir}/preview.png")
    used = sorted(set(np.unique(b).tolist()))
    print("biomes used:", ", ".join(f"{i} {names.get(i, '?')}" for i in used))


# ---------------------------------------------------------------- expand: plan -> piece

def expand(plan_dir, out_dir, pi, pj, piece):
    hp = np.asarray(Image.open(f"{plan_dir}/height.png")).astype(np.float32) / 257
    bp = np.asarray(Image.open(f"{plan_dir}/biome.png"))
    rp = np.asarray(Image.open(f"{plan_dir}/relief.png")).astype(np.float32) / 255
    meta = json.load(open(f"{plan_dir}/plan.json"))
    size, seed = meta["size"], meta.get("seed", 1)
    half = size // 2
    x0, z0 = -half + pi * piece, -half + pj * piece
    d = f"{out_dir}/piece_{pi}_{pj}"
    os.makedirs(d, exist_ok=True)
    H = np.zeros((piece, piece), np.uint16)
    B = np.zeros((piece, piece), np.uint8)
    xs = np.arange(piece, dtype=np.float64) + x0 + 0.5
    for r0 in range(0, piece, 256):   # 256-row strips: ~1 GB peak; 1024 needed ~5 GB and paged
        zs = np.arange(r0, min(piece, r0 + 256), dtype=np.float64) + z0 + 0.5
        X, Z = np.meshgrid(xs, zs)
        # One warp for terrain and biome, so coasts and biome edges are organic and agree.
        wx = X + 40 * fbm(X, Z, 320, 3, seed + 13)
        wz = Z + 40 * fbm(X, Z, 320, 3, seed + 14)
        pz, px = (wz + half) / PX - 0.5, (wx + half) / PX - 0.5
        h = ndimage.map_coordinates(hp, [pz, px], order=3, mode="nearest")
        rel = ndimage.map_coordinates(rp, [pz, px], order=1, mode="nearest")
        detail = fbm(X, Z, 256, 6, seed + 11) * (2 + 22 * rel) + fbm(X, Z, 48, 3, seed + 12) * (0.6 + 4 * rel)
        h = h + detail * (0.25 + 0.75 * np.clip((h - SEA) / 8, 0, 1))
        H[r0:r0 + len(zs)] = np.clip(h * 257, 0, 255 * 257).astype(np.uint16)
        bi = np.clip(((wz + half) / PX).astype(np.int64), 0, bp.shape[0] - 1)
        bj = np.clip(((wx + half) / PX).astype(np.int64), 0, bp.shape[1] - 1)
        B[r0:r0 + len(zs)] = bp[bi, bj]
    Image.fromarray(H).save(f"{d}/height.png")
    Image.fromarray(B).save(f"{d}/biome.png")
    open(f"{d}/origin.txt", "w").write(f"{x0} {z0}\n")
    print(f"piece {pi},{pj}: origin {x0},{z0}, {piece} blocks -> {d}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("render"); a.add_argument("spec"); a.add_argument("plan")
    a = sub.add_parser("preview"); a.add_argument("plan")
    a = sub.add_parser("expand"); a.add_argument("plan"); a.add_argument("out")
    a.add_argument("--piece", nargs=2, type=int, required=True); a.add_argument("--piece-size", type=int, default=16384)
    args = ap.parse_args()
    if args.cmd == "render":
        render(args.spec, args.plan)
        preview(args.plan)
    elif args.cmd == "preview":
        preview(args.plan)
    else:
        expand(args.plan, args.out, args.piece[0], args.piece[1], args.piece_size)


if __name__ == "__main__":
    sys.exit(main())
