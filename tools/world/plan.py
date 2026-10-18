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
import argparse, json, math, os, re, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

SURFACES = ["black_sand"]   # surface.png value = index + 1
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


def meander(points, amp, seed, step=160.0):
    """Densify a polyline and push it sideways with smooth noise, so rivers wander."""
    if amp <= 0:
        return points
    out, s = [], 0.0
    for (x1, z1), (x2, z2) in zip(points, points[1:]):
        L = math.hypot(x2 - x1, z2 - z1)
        nx, nz = -(z2 - z1) / (L or 1), (x2 - x1) / (L or 1)
        steps = max(1, int(L / step))
        for i in range(steps):
            t = i / steps
            off = amp * float(fbm(np.array([s + t * L]), np.array([seed * 13.0]), 900, 3, seed)[0])
            out.append((x1 + (x2 - x1) * t + nx * off, z1 + (z2 - z1) * t + nz * off))
        s += L
    out.append(tuple(points[-1]))   # ends stay put, so tributaries still meet their river
    out[0] = tuple(points[0])
    return out


def pond_distance(x, z, cx, cz, r, seed):
    """Normalised distance to a lake centre (1 = shore); the shore wobbles with noise.
    The same function runs at plan and at block resolution, so both agree on the shape."""
    wob = 1 + 0.3 * fbm(x, z, max(r * 0.8, 64), 2, seed)
    return np.hypot(x - cx, z - cz) / (r * wob)


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
        if "at" not in r:
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
    def warped_mask(polys, wxx, wzz):
        img = Image.new("L", (n, n), 0)
        for p in polys:
            ImageDraw.Draw(img).polygon(_poly(n, p, size), fill=255)
        return ndimage.map_coordinates((np.asarray(img) > 0).astype(np.float32),
                                       [(wzz + half) / PX - 0.5, (wxx + half) / PX - 0.5], order=1, mode="constant") > 0.5

    land = warped_mask([spec["coast"]], wx, wz)
    # Lakes ({polygon} or {circle: [x, z, r]}) cut the land; islands come after, so an island
    # can stand in a lake.
    lakes = [region_polygon(l) for l in spec.get("lakes", [])]
    if lakes:
        land &= ~warped_mask(lakes, gx + 0.3 * (wx - gx), gz + 0.3 * (wz - gz))
    isl = [region_polygon(i) if isinstance(i, dict) else i for i in spec.get("islands", [])]
    if isl:
        land |= warped_mask(isl, gx + 0.3 * (wx - gx), gz + 0.3 * (wz - gz))

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
    # Regions given as {at: [x, z], size: s} split the land between them by (warped) nearest
    # centre, size-weighted: organic shapes with no drawn borders.
    cells = [k for k, r in enumerate(spec["regions"]) if "at" in r]
    if cells:
        best = np.full((n, n), np.inf, np.float32)
        cell_owner = np.full((n, n), -1, np.int32)
        for k in cells:
            (cx, cz), s = spec["regions"][k]["at"], spec["regions"][k].get("size", 1.0)
            dd = np.hypot(rx - cx, rz - cz) / s
            closer = dd < best
            best[closer], cell_owner[closer] = dd[closer], k
    sea_regions = []
    for k, r in enumerate(spec["regions"]):
        if "at" in r:
            m = cell_owner == k
        else:
            ri = Image.new("L", (n, n), 0)
            ImageDraw.Draw(ri).polygon(_poly(n, r["polygon"], size), fill=255)
            m = ndimage.map_coordinates((np.asarray(ri) > 0).astype(np.float32),
                                        [(rz + half) / PX - 0.5, (rx + half) / PX - 0.5], order=1, mode="constant") > 0.5
        if r.get("sea"):          # a sea biome (reef, kelp): painted over water only, after the floor;
            sea_regions.append((m, r["biome"], r.get("shallow", False)))   # shallow: the shelf only
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
    # A region paints one biome ({biome: id}) or a patchwork ({biomes: [[id, weight], ...]}):
    # each biome gets its own noise field plus a weight bias, and the highest wins.
    for k, r in enumerate(spec["regions"]):
        if r.get("sea"):
            continue
        m = land & (owner == k)
        mix = r.get("biomes") or [[r["biome"], 1]]
        if len(mix) == 1:
            biome[m] = mix[0][0]
            continue
        ws = np.array([w for _, w in mix], np.float32)
        ws = ws / ws.sum()
        patch = r.get("patch", 1600)
        score = np.stack([fbm(gx[m], gz[m], patch, 3, seed + 1000 + 37 * b) + 2.2 * (w - ws.mean())
                          for (b, _), w in zip(mix, ws)])
        biome[m] = np.array([b for b, _ in mix], np.uint8)[score.argmax(0)]
        r.setdefault("biome", mix[0][0])
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
    for m, b, shallow in sea_regions:
        biome[m & ~land & ((depth < 0.6) if shallow else True)] = b

    # Rivers: meandering carved channels. {points, width, biome (default River), meander
    # (blocks of sideways wander), dry: true for a shallow dry bed with no water}.
    for ri_k, river in enumerate(spec.get("rivers", [])):
        pts = meander(river["points"], river.get("meander", 220), seed + 500 + ri_k)
        ri = Image.new("L", (n, n), 0)
        ImageDraw.Draw(ri).line(_poly(n, pts, size), fill=255, width=max(1, round(river.get("width", 32) / PX)), joint="curve")
        m = (np.asarray(ri) > 0) & land
        d = ndimage.distance_transform_edt(~m) * PX
        bank = np.clip(d / river.get("valley", 160), 0, 1) ** 0.5
        if river.get("dry"):
            h = np.where(land, h - river.get("depth", 5) * (1 - bank), h)
        else:
            h = np.where(land, np.minimum(h, SEA - 3 + (h - SEA + 3) * bank), h)
        biome[m] = river.get("biome", RIVER)
        relief = np.where(m, 0, relief)

    # Lakes inside the land, at their own surface level (WorldPainter sets that water level per
    # block). Explicit {ponds: [{at, r, depth, biome}]} plus per-region {lakes: [count, rmin, rmax]}.
    ponds = [dict(p) for p in spec.get("ponds", [])]
    taken = np.zeros((n, n), bool)
    for k, r in enumerate(spec["regions"]):
        if "lakes" not in r or r.get("sea"):
            continue
        count, rmin, rmax = r["lakes"]
        rng = np.random.default_rng(seed + 7000 + k)
        ok = land & (owner == k) & (d_in > 400 + rmax) & (biome != RIVER) & (h > SEA)
        cand = np.argwhere(ok)
        rng.shuffle(cand)
        placed = 0
        for zz, xx in cand:
            if placed >= count:
                break
            if taken[zz, xx]:
                continue
            rad = float(rng.uniform(rmin, rmax))
            ponds.append({"at": [float(xx * PX - half + PX / 2), float(zz * PX - half + PX / 2)], "r": rad})
            sp = int(2.5 * rmax / PX)
            taken[max(0, zz - sp):zz + sp, max(0, xx - sp):xx + sp] = True
            placed += 1
    water = np.zeros((n, n), np.float32)
    for i, p in enumerate(ponds):
        p["id"] = i
        p.setdefault("depth", max(4, min(14, p["r"] / 40)))
        cx, cz, rad = p["at"][0], p["at"][1], p["r"]
        j0, j1 = max(0, int((cx - 1.7 * rad + half) / PX)), min(n, int((cx + 1.7 * rad + half) / PX) + 2)
        i0, i1 = max(0, int((cz - 1.7 * rad + half) / PX)), min(n, int((cz + 1.7 * rad + half) / PX) + 2)
        if j1 <= j0 or i1 <= i0:
            continue
        sl = (slice(i0, i1), slice(j0, j1))
        bx, bz = gx[sl], gz[sl]
        d = pond_distance(bx, bz, cx, cz, rad, seed + 9000 + i)
        rr = np.hypot(bx - cx, bz - cz)
        ring = (rr > rad * 1.2) & (rr < rad * 1.6) & land[sl]
        if not ring.any():
            continue
        p["level"] = int(max(SEA, math.floor(np.percentile(h[sl][ring], 10)) - 1))
        inside = (d < 1) & land[sl]
        h[sl] = np.where(inside, np.minimum(h[sl], p["level"] - 1 - p["depth"] * (1 - d * d)), h[sl])
        water[sl] = np.where(inside, p["level"], water[sl])
        relief[sl] = np.where(inside, 0, relief[sl])
        if "biome" in p:
            biome[sl][inside] = p["biome"]
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
    Image.fromarray(water.astype(np.uint8)).save(f"{plan_dir}/water.png")
    # Surface materials the expansion carries to WorldPainter ({circle|polygon, material}).
    surf = np.zeros((n, n), np.uint8)
    for s_ in spec.get("surfaces", []):
        si = Image.new("L", (n, n), 0)
        ImageDraw.Draw(si).polygon(_poly(n, region_polygon(s_), size), fill=255)
        surf[np.asarray(si) > 0] = SURFACES.index(s_["material"]) + 1
    Image.fromarray(surf).save(f"{plan_dir}/surface.png")
    meta = {k: spec[k] for k in ("size", "seed") if k in spec}
    meta["ponds"] = [p for p in ponds if "level" in p]
    # Biome patches are labelled in the preview from biome.png by their real names; regions
    # only carry their tier, shown at the centre of the land they own.
    meta["regions"] = []
    for k, r in enumerate(spec["regions"]):
        zz, xx = np.nonzero(land & (owner == k))
        if len(xx) and "tier" in r:
            meta["regions"].append({"tier": r["tier"], "x": float(xx.mean() * PX - half), "z": float(zz.mean() * PX - half)})
    Image.fromarray(np.where(land, owner + 1, 0).astype(np.uint8)).save(f"{plan_dir}/regions.png")
    meta["points"] = spec.get("points", [])
    json.dump(meta, open(f"{plan_dir}/plan.json", "w"), indent=1)
    print(f"plan {n}x{n} px ({size} blocks): land {land.mean():.0%}, max y {h.max():.0f}")


# ---------------------------------------------------------------- preview

PREVIEW_PALETTE = [
    (r"dry river", (190, 160, 110)),
    (r"river", (70, 130, 220)),
    (r"ice ocean|frozenocean", (170, 200, 225)),
    (r"cold ocean", (40, 80, 150)),
    (r"hot ocean", (40, 110, 175)),
    (r"ocean", (45, 95, 165)),
    (r"coral", (70, 190, 200)),
    (r"kelp", (40, 110, 110)),
    (r"volcan|wasteland|ash", (95, 80, 80)),
    (r"snow|frost|glacier|polar|arctic|ice|tundra|frozen", (225, 232, 240)),
    (r"alps|crag|mountain|cliff|highland|extreme", (150, 150, 150)),
    (r"redwood", (120, 55, 40)),
    (r"desert|dune|mesa|outback|xeric|steppe|savanna|brush|scrub|oasis", (215, 185, 110)),
    (r"swamp|bog|fen|marsh|moor|bayou|wetland|mangrove|quagmire", (80, 100, 70)),
    (r"jungle|tropic|rainforest|bamboo", (40, 140, 50)),
    (r"ominous|dead|mystic|spectral", (90, 70, 110)),
    (r"taiga|conifer|boreal|spruce|pine", (45, 95, 75)),
    (r"cherry|lavender|flower|orchard|garden", (215, 150, 190)),
    (r"forest|wood|grove|maple|thicket", (70, 130, 55)),
    (r"plain|prairie|meadow|grass|heath|shrub|field", (140, 180, 95)),
]

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
    names = biome_names()
    rng = np.random.default_rng(7)
    lut = rng.integers(60, 220, (256, 3)).astype(np.float32)
    for bid, nm in names.items():   # family colour by name, jittered so neighbours still differ
        for pat, col in PREVIEW_PALETTE:
            if re.search(pat, nm, re.I):
                lut[bid] = np.clip(np.array(col) + rng.integers(-22, 23, 3), 0, 255)
                break
    lut[OCEAN], lut[DEEP_OCEAN], lut[RIVER], lut[BEACH] = (60, 110, 190), (30, 60, 140), (70, 130, 220), (220, 205, 150)
    rgb = lut[b]
    gy, gx = np.gradient(h)
    shade = np.clip(1 + (gx - gy) * 0.06, 0.6, 1.4)[..., None]
    land = h >= SEA
    rgb = np.where(land[..., None], rgb * shade * (0.75 + 0.35 * np.clip((h - SEA) / 140, 0, 1))[..., None], rgb)
    # Lakes above sea level (water.png), frozen where the biome is cold; then black sand.
    if os.path.exists(f"{plan_dir}/water.png"):
        wl = np.asarray(Image.open(f"{plan_dir}/water.png")).astype(np.float32)
        lake = (wl > 0) & (h < wl)
        cold = np.zeros(256, bool)
        for bid, nm in names.items():
            cold[bid] = bool(re.search(r"snow|frost|glacier|polar|arctic|ice|tundra|frozen|boreal|alps", nm, re.I))
        rgb[lake] = np.where(cold[b[lake]][:, None], (190, 225, 240), (55, 105, 200))
    if os.path.exists(f"{plan_dir}/surface.png"):
        sf = np.asarray(Image.open(f"{plan_dir}/surface.png"))
        rgb[sf == 1] = rgb[sf == 1] * 0.25 + np.array((20, 20, 24)) * 0.75
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
    small = ImageFont.truetype("arial.ttf", max(10, n * scale // 150)) if font != ImageFont.load_default() else font
    # Region borders (thin dark lines) from regions.png.
    if os.path.exists(f"{plan_dir}/regions.png"):
        reg = np.asarray(Image.open(f"{plan_dir}/regions.png")).astype(np.int32)
        edge = ((reg != np.roll(reg, 1, 0)) | (reg != np.roll(reg, 1, 1))) & (reg > 0) & (np.roll(reg, 1, 0) > 0) & (np.roll(reg, 1, 1) > 0)
        ez, ex = np.nonzero(edge)
        for z, x in zip(ez, ex):
            dr.rectangle((x * scale, z * scale, x * scale + scale - 1, z * scale + scale - 1), fill=(25, 25, 25))
    # Every biome patch big enough to read gets its real name.
    # Label each patch of each biome at its most interior pixel, so the text sits inside it.
    min_px = (n / 32) ** 2
    for bid in np.unique(b):
        if bid in (OCEAN, DEEP_OCEAN, RIVER, BEACH, 10, 11, 82, 150):   # seas and rivers: too thin or too big to label usefully
            continue
        lab, nlab = ndimage.label(b == bid)
        for i in range(1, nlab + 1):
            comp = lab == i
            if comp.sum() < min_px:
                continue
            inner = ndimage.distance_transform_edt(comp)
            zz, xx = np.unravel_index(inner.argmax(), inner.shape)
            dr.text((xx * scale, zz * scale), names.get(int(bid), f"biome {bid}"), fill="white", font=small,
                    anchor="mm", stroke_width=2, stroke_fill="black")
    for r in meta.get("regions", []):
        x, z = (r["x"] + half) * k, (r["z"] + half) * k
        dr.ellipse((x - 16, z - 16, x + 16, z + 16), fill=(20, 20, 20), outline="white", width=2)
        dr.text((x, z), f"T{r['tier']}", fill="white", font=small, anchor="mm")
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
    sp = np.asarray(Image.open(f"{plan_dir}/surface.png")) if os.path.exists(f"{plan_dir}/surface.png") \
        else np.zeros_like(bp)
    ponds = meta.get("ponds", [])
    H = np.zeros((piece, piece), np.uint16)
    B = np.zeros((piece, piece), np.uint8)
    S = np.zeros((piece, piece), np.uint8)
    Wt = np.zeros((piece, piece), np.uint8)
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
        # Lakes: re-carve at block resolution with the plan's own shore function, then flood
        # every depression near the lake that lies below its level.
        zlo, zhi = zs[0], zs[-1]
        for p in ponds:
            cx, cz, rad = p["at"][0], p["at"][1], p["r"]
            if cz + 1.4 * rad < zlo or cz - 1.4 * rad > zhi or cx + 1.4 * rad < x0 or cx - 1.4 * rad > x0 + piece:
                continue
            c0, c1 = max(0, int(cx - 1.4 * rad - x0)), min(piece, int(cx + 1.4 * rad - x0) + 1)
            sx, sz = X[:, c0:c1], Z[:, c0:c1]
            dd = pond_distance(sx, sz, cx, cz, rad, seed + 9000 + p["id"])
            hs = h[:, c0:c1]
            hs = np.where(dd < 1, np.minimum(hs, p["level"] - 1 - p["depth"] * (1 - dd * dd)), hs)
            h[:, c0:c1] = hs
            if p["level"] > SEA:
                wsl = Wt[r0:r0 + len(zs), c0:c1]
                Wt[r0:r0 + len(zs), c0:c1] = np.where((dd < 1.3) & (hs < p["level"]), p["level"], wsl)
        H[r0:r0 + len(zs)] = np.clip(h * 257, 0, 255 * 257).astype(np.uint16)
        bi = np.clip(((wz + half) / PX).astype(np.int64), 0, bp.shape[0] - 1)
        bj = np.clip(((wx + half) / PX).astype(np.int64), 0, bp.shape[1] - 1)
        B[r0:r0 + len(zs)] = bp[bi, bj]
        S[r0:r0 + len(zs)] = sp[bi, bj]
    Image.fromarray(H).save(f"{d}/height.png")
    Image.fromarray(B).save(f"{d}/biome.png")
    Image.fromarray(Wt).save(f"{d}/water.png")       # 0 = the world's sea level
    Image.fromarray(S).save(f"{d}/surface.png")      # SURFACES index + 1, 0 = none
    mine = [p for p in ponds if p["level"] > SEA and x0 - 1.4 * p["r"] <= p["at"][0] <= x0 + piece + 1.4 * p["r"]
            and z0 - 1.4 * p["r"] <= p["at"][1] <= z0 + piece + 1.4 * p["r"]]
    json.dump([{"x": p["at"][0], "z": p["at"][1], "r": p["r"] * 1.6, "level": p["level"]} for p in mine],
              open(f"{d}/lakes.json", "w"))
    open(f"{d}/origin.txt", "w").write(f"{x0} {z0}\n")
    print(f"piece {pi},{pj}: origin {x0},{z0}, {piece} blocks, {len(mine)} raised lakes -> {d}")


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
