"""Low-resolution world plan -> full-resolution WorldPainter pieces (decision 0003).

The plan is drawn at 1 pixel = 16 blocks (one chunk) and lives in a directory as three
hand-editable images:
  height.png  16-bit grey, value = y * 257 (sea level 62)
  biome.png   8-bit grey, value = biome ID (docs/survey/biome-ids.tsv; 255 is never used)
  relief.png  8-bit grey, how much fine detail the expansion adds there (0 flat .. 255 craggy)

  py -3.10 tools/world/plan.py render SPEC.yaml PLANDIR      # draft the plan from a design spec
  py -3.10 tools/world/plan.py preview PLANDIR               # colour map with labels -> PLANDIR/preview.png
  py -3.10 tools/world/plan.py expand PLANDIR OUTDIR --piece I J [--piece-size 16384]

`expand` writes OUTDIR/piece_I_J/{height,biome,water,surface,terrain}.png, origin.txt for wp_piece.js.
All noise is a function of world coordinates, so neighbouring pieces meet without a seam.
"""
import argparse, json, math, os, re, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

SURFACES = ["black_sand", "scorched", "packed_ice"]   # surface.png value = index + 1
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


def hash_str(t):
    """Stable string hash (Python's hash() changes between runs)."""
    v = 2166136261
    for ch in t.encode("utf-8"):
        v = ((v ^ ch) * 16777619) & 0xFFFFFFFF
    return v


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


def pond_distance(x, z, p, seed):
    """Normalised distance to a lake centre (1 = shore). The lake is stretched (aspect),
    turned (rot) and its shore pushed in and out by noise at two scales, so no lake is a
    circle. The same function runs at plan and at block resolution, so both agree."""
    cx, cz, r = p["at"][0], p["at"][1], p["r"]
    c, s = math.cos(p.get("rot", 0.0)), math.sin(p.get("rot", 0.0))
    dx, dz = x - cx, z - cz
    u, v = (dx * c + dz * s), (-dx * s + dz * c) * p.get("aspect", 1.0)
    wob = 1 + 0.45 * fbm(x, z, max(r * 0.7, 64), 3, seed) + 0.15 * fbm(x, z, max(r * 0.2, 24), 2, seed + 1)
    return np.hypot(u, v) / (r * np.maximum(wob, 0.35))


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


_NAMES = None


def names_cache():
    global _NAMES
    if _NAMES is None:
        _NAMES = biome_names()
    return _NAMES


RAIN = [  # relative rainfall by biome family; first match wins
    (r"rainforest|jungle|tropic|bayou|mangrove|lush|bamboo|redwood", 3.0),
    (r"swamp|marsh|fen|bog|wetland|quagmire|land of lakes|shield|silkglade|fungi|sludge", 2.2),
    (r"kelp|temperate|seasonal|maple|deciduous|grove|mystic|roofed|ominous|spectral", 1.4),
    (r"desert|outback|mesa|xeric|canyon|wasteland|dry|scrub|oasis", 0.25),
    (r"steppe|savanna|brush|prairie|chaparral", 0.55),
    (r"tundra|glacier|ice|polar|arctic|alps|frost|crag|volcan", 0.6),
]


def rainfall(biome, overrides=None):
    """Rainfall per plan pixel from the painted biome (spec auto_rivers.rain: {regex: value} adds or overrides)."""
    names = names_cache()
    lut = np.ones(256, np.float32)
    rules = list((overrides or {}).items()) + RAIN
    for bid, nm in names.items():
        for pat, v in rules:
            if re.search(pat, nm, re.I):
                lut[bid] = v
                break
    return lut[biome]


class Drainage:
    """Coarse drainage of the plan's terrain: filled levels, downstream receivers, flow counts."""

    def __init__(self, F, rec, acc, land_c, cell_blocks, half):
        self.F, self.rec, self.acc, self.land_c = F, rec, acc, land_c
        self.cell, self.half, self.nc = cell_blocks, half, F.shape[0]

    def ij(self, x, z):
        return (min(self.nc - 1, max(0, int((z + self.half) / self.cell))),
                min(self.nc - 1, max(0, int((x + self.half) / self.cell))))

    def level_at(self, x, z):
        i, j = self.ij(x, z)
        return float(self.F[i, j]) if self.land_c[i, j] else float(SEA)

    def centre(self, k):
        i, j = divmod(k, self.nc)
        return ((j + 0.5) * self.cell - self.half, (i + 0.5) * self.cell - self.half)


def drainage(h, land, size, half, cell_blocks=128, rain=None):
    """Priority-flood drainage on a coarse grid (Barnes et al. 2014): every land cell gets a
    filled level that never rises downstream and a receiver one step closer to the sea."""
    import heapq
    n = h.shape[0]
    c = max(1, int(round(cell_blocks / PX)))
    nc = n // c
    hc = h[:nc * c, :nc * c].reshape(nc, c, nc, c).mean(axis=(1, 3))
    land_c = land[:nc * c, :nc * c].reshape(nc, c, nc, c).mean(axis=(1, 3)) > 0.5
    F = np.where(land_c, hc, SEA).astype(np.float64).ravel()
    lc = land_c.ravel()
    rec = np.full(nc * nc, -1, np.int64)
    done = ~lc.copy()
    heap = []
    # Seed with the ocean cells that touch land; everything drains to one of them.
    ocean = ~land_c
    edge = ocean & ndimage.binary_dilation(land_c, structure=np.ones((3, 3)))
    for k in np.flatnonzero(edge.ravel()):
        heapq.heappush(heap, (float(SEA), int(k)))
    order = []
    nbrs = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    while heap:
        f, k = heapq.heappop(heap)
        i, j = divmod(k, nc)
        for di, dj in nbrs:
            a, b = i + di, j + dj
            if 0 <= a < nc and 0 <= b < nc:
                q = a * nc + b
                if not done[q]:
                    done[q] = True
                    F[q] = max(F[q], f + 1e-3)
                    rec[q] = k
                    order.append(q)
                    heapq.heappush(heap, (F[q], q))
    # Flow carries rainfall: wet biomes (rainforest, swamp) feed rivers far faster than desert.
    if rain is not None:
        rc = rain[:nc * c, :nc * c].reshape(nc, c, nc, c).mean(axis=(1, 3)).ravel()
        acc = np.where(lc, rc, 0.0).astype(np.float64)
    else:
        acc = lc.astype(np.float64)
    for q in reversed(order):
        r = rec[q]
        if r >= 0 and lc[r]:
            acc[r] += acc[q]
    return Drainage(F.reshape(nc, nc), rec, acc, land_c, c * PX, half)


def auto_rivers(cfg, flow, biome, names):
    """River polylines along real drainage lines: {cell, threshold_km2, min_width, max_width,
    meander, min_cells}. Width grows with the area drained; the biome follows the climate
    (frozen in the cold, lush in the tropics, plain River elsewhere)."""
    cell = flow.cell
    cell_km2 = (cell / 1000.0) ** 2
    thr = cfg.get("threshold_km2", 30) / cell_km2
    lc = flow.land_c.ravel()
    river = lc & (flow.acc >= thr)
    up = np.zeros_like(river)
    for k in np.flatnonzero(river):
        r = flow.rec[k]
        if r >= 0:
            up[r] = True
    heads = np.flatnonzero(river & ~up)
    amax = max(flow.acc[river].max() if river.any() else 1, 1)
    minw, maxw = cfg.get("min_width", 16), cfg.get("max_width", 110)
    seen = np.zeros_like(river)
    n_plan = biome.shape[0]
    half = flow.half
    out = []
    for hd in heads:
        path, cur = [int(hd)], int(hd)
        seen[cur] = True
        while True:
            nxt = int(flow.rec[cur])
            if nxt < 0:
                break
            path.append(nxt)
            if not lc[nxt] or seen[nxt]:
                break
            seen[nxt] = True
            cur = nxt
        if len(path) < cfg.get("min_cells", 6):
            continue
        for s in range(0, len(path) - 1, 6):
            seg = path[s:s + 7]
            if len(seg) < 2:
                continue
            a = max(flow.acc[k] for k in seg)
            w = minw + (maxw - minw) * math.sqrt(a / amax)
            pts = [flow.centre(k) for k in seg]
            mx, mz = pts[len(pts) // 2]
            pi = min(n_plan - 1, max(0, int((mz + half) / PX)))
            pj = min(n_plan - 1, max(0, int((mx + half) / PX)))
            nm = names.get(int(biome[pi, pj]), "")
            if re.search(r"snow|frost|glacier|polar|arctic|ice|tundra|frozen|alps|boreal|spike", nm, re.I):
                b = 11
            elif re.search(r"tropic|jungle|rainforest|mangrove|bamboo|bayou|lush", nm, re.I):
                b = 150
            else:
                b = RIVER
            out.append({"points": pts, "width": int(w), "meander": cfg.get("meander", int(cell * 0.35)),
                        "valley": int(120 + w * 1.5), "biome": b})
    print(f"auto rivers: {int(river.sum())} river cells, {len(heads)} heads, {len(out)} segments "
          f"(cell {cell} blocks, threshold {thr:.0f} cells)")
    return out


def fractal_land(spec, gx, gz, n, size, half, seed):
    """Land from rough sketch shapes with a fractal edge.

    spec: landmasses: [polygon, ...]        rough outlines; the noise does the detail
          coast_rough: {amp, scale, octaves} edge noise: amp in blocks (how far bays cut in and
                                             capes reach out), scale = the largest bay
          rough_zones: [{circle|polygon, mul}] scale amp locally (fjord coast 2.0, desert 0.5)
          island_chains: [{points, count, r: [rmin, rmax], jitter}] islands strung along a path
    Land is where (signed distance to the sketch + noise) > 0, so the coast breaks up at every
    scale and islands form just offshore wherever the noise is high."""
    cr = spec.get("coast_rough", {})
    amp, scale, octv = cr.get("amp", 1400), cr.get("scale", 6000), cr.get("octaves", 7)

    def poly_mask(polys):
        img = Image.new("L", (n, n), 0)
        for p in polys:
            ImageDraw.Draw(img).polygon(_poly(n, p, size), fill=255)
        return np.asarray(img) > 0

    inside = poly_mask(spec["landmasses"])
    sdf = (ndimage.distance_transform_edt(inside) - ndimage.distance_transform_edt(~inside)) * PX
    mul = np.ones((n, n), np.float32)
    for z in spec.get("rough_zones", []):
        mul = np.where(poly_mask([region_polygon(z)]), z["mul"], mul)
    mul = ndimage.gaussian_filter(mul, 2000 / PX)
    # Domain-warp the sketch's distance field so bays twist into inlets and fjords, then add
    # fractal noise whose small scales stay strong (gain 0.62) so the edge is rough at every size.
    wa = amp * 0.9 * mul
    sx = gx + wa * fbm(gx, gz, scale * 0.6, 5, seed + 3)
    sz = gz + wa * fbm(gx, gz, scale * 0.6, 5, seed + 4)
    sdf = ndimage.map_coordinates(sdf, [(sz + half) / PX - 0.5, (sx + half) / PX - 0.5], order=1, mode="nearest")
    noise = fbm(gx, gz, scale, octv, seed + 1, gain=0.62)
    noise = noise / (noise.std() + 1e-6)
    land = sdf + amp * mul * noise > 0
    # Noise can punch holes inside a landmass that read as stray inland "ocean". Fill them;
    # real lakes are placed on purpose (lakes, ponds, region lakes).
    land = ndimage.binary_fill_holes(land)
    # Island chains: islands of varied size strung along a path, jittered off it.
    rng = np.random.default_rng(seed + 4242)
    for ch in spec.get("island_chains", []):
        pts = np.array(ch["points"], float)
        seg = np.hypot(*np.diff(pts, axis=0).T)
        cum = np.concatenate([[0], np.cumsum(seg)])
        for t in np.linspace(0, cum[-1], ch.get("count", 8)):
            k = min(np.searchsorted(cum, t, side="right") - 1, len(seg) - 1)
            f = (t - cum[k]) / (seg[k] or 1)
            x, z = pts[k] + (pts[k + 1] - pts[k]) * f + rng.normal(0, ch.get("jitter", 300), 2)
            r = rng.uniform(*ch.get("r", [150, 500]))
            d = np.hypot(gx - x, gz - z) - r * (1 + 0.5 * fbm(gx, gz, max(r, 64), 3, seed + 99))
            land |= d < 0
    # Specks under ~3 plan pixels read as noise, not islands.
    lab, nl = ndimage.label(land)
    if nl:
        sizes = ndimage.sum(np.ones_like(lab), lab, range(1, nl + 1))
        land &= np.isin(lab, np.nonzero(sizes >= 3)[0] + 1)
    return land


def render(spec_path, plan_dir):
    import yaml
    spec = yaml.safe_load(open(spec_path, encoding="utf-8"))
    _cache = {}
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

    if "landmasses" in spec:
        land = fractal_land(spec, gx, gz, n, size, half, seed)
    else:
        land = warped_mask([spec["coast"]], wx, wz)
    # Lakes ({polygon} or {circle: [x, z, r]}) cut the land; islands come after, so an island
    # can stand in a lake.
    lakes = [region_polygon(l) for l in spec.get("lakes", [])]
    if lakes:
        land &= ~warped_mask(lakes, gx + 0.3 * (wx - gx), gz + 0.3 * (wz - gz))
    iwx, iwz = gx + 0.3 * (wx - gx), gz + 0.3 * (wz - gz)
    isl = [region_polygon(i) if isinstance(i, dict) else i for i in spec.get("islands", []) if not (isinstance(i, dict) and "ring" in i)]
    if isl and "landmasses" in spec:
        # Fractal maps get fractal islands: a circle's edge pushed in and out by noise scaled
        # to its size, so islands get coves and capes instead of looking stamped on.
        for i in spec.get("islands", []):
            if isinstance(i, dict) and "circle" in i:
                cx_, cz_, cr_ = i["circle"]
                d = np.hypot(gx - cx_, gz - cz_) - cr_
                land |= d + 0.55 * cr_ * fbm(gx, gz, max(cr_ * 1.2, 96), 5, seed + int(cx_ + cz_) % 997, gain=0.6) * 2.2 < 0
            elif not (isinstance(i, dict) and "ring" in i):
                land |= warped_mask([i if not isinstance(i, dict) else region_polygon(i)], iwx, iwz)
    elif isl:
        land |= warped_mask(isl, iwx, iwz)
    for i in spec.get("islands", []):   # {ring: [x, z, r_out, r_in]}: an atoll around a lagoon
        if isinstance(i, dict) and "ring" in i:
            x, z, ro, rin = i["ring"]
            land |= warped_mask([region_polygon({"circle": [x, z, ro]})], iwx, iwz) & \
                ~warped_mask([region_polygon({"circle": [x, z, rin]})], iwx, iwz)

    # Raised plateaus ({circle|polygon, top, wall}): sheer-sided table mountains (tepuis, mesas).
    plateaus = []
    for pl in spec.get("plateaus", []):
        pm = warped_mask([region_polygon(pl)], iwx, iwz) & land
        plateaus.append((pl, pm))

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
            ex, ez = (gx, gz) if r.get("exact") else (rx, rz)   # exact: no border wobble (islands)
            m = ndimage.map_coordinates((np.asarray(ri) > 0).astype(np.float32),
                                        [(ez + half) / PX - 0.5, (ex + half) / PX - 0.5], order=1, mode="constant") > 0.5
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
        if "jag" not in _cache:
            _cache["jag"] = 1 + 0.45 * fbm(gx, gz, 900, 4, seed + 7)
        jag = _cache["jag"]
        prof = np.clip(1 - d / (ridge["width"] / 2 * jag), 0, 1)
        prof = prof * prof * (3 - 2 * prof)
        # Peaks and saddles along the crest, spurs off it: ridged noise, not a smooth tube.
        ck = ("crest", ridge.get("peak_spacing", 1400))
        if ck not in _cache:
            _cache[ck] = 0.55 + 0.45 * ridged(gx, gz, ck[1], 5, seed + 8)
        crest = _cache[ck]
        h = np.where(land, np.maximum(h, h + (ridge["height"] - SEA) * prof * crest * shore), h)
        relief = np.maximum(relief, np.where(prof > 0.05, ridge.get("relief", 200) * np.minimum(1, prof * 3), 0))
        if "biome" in ridge:
            biome[land & (prof > ridge.get("biome_above", 0.35))] = ridge["biome"]
    # Soft cap: ridge heights add onto the ground beneath them, so stacked ranges could pass the
    # 256 build limit and clip flat. Squash everything above 230 smoothly into 230..252.
    over = h > 230
    h = np.where(over, 230 + 22 * np.tanh((h - 230) / 22), h)
    extra_tiers = []
    plateau_surf = []
    for pl, pm in plateaus:
        din = ndimage.distance_transform_edt(pm) * PX
        rise = np.clip(din / pl.get("wall", 64), 0, 1) ** 0.35          # sheer wall, then a flat top
        top = pl["top"] + fbm(gx, gz, 600, 3, seed + 31) * pl.get("top_relief", 10)
        h = np.where(pm, np.maximum(h, h + (top - h) * rise), h)
        relief = np.where(pm & (rise >= 0.99), np.minimum(relief, pl.get("relief", 50)), relief)
        if "biome" in pl:
            biome[pm & (rise > 0.6)] = pl["biome"]
        if "surface" in pl:          # ground material on the plateau ({surface: packed_ice})
            plateau_surf.append((pm & (rise > 0.6), SURFACES.index(pl["surface"]) + 1))
        if "tier" in pl and pm.any():
            zz, xx = np.nonzero(pm)
            extra_tiers.append({"tier": pl["tier"], "x": float(xx.mean() * PX - half), "z": float(zz.mean() * PX - half)})
    # Canyons ({points, width, depth, wall_biome, floor_biome}): a broad cut with steep walls
    # and a flat floor, wandering like a river.
    for ck, cn in enumerate(spec.get("canyons", [])):
        pts = meander(cn["points"], cn.get("meander", 500), seed + 600 + ck)
        ci = Image.new("L", (n, n), 0)
        ImageDraw.Draw(ci).line(_poly(n, pts, size), fill=255, width=1)
        d = ndimage.distance_transform_edt(~(np.asarray(ci) > 0)) * PX
        hw = cn["width"] / 2 * (1 + 0.3 * fbm(gx, gz, 1200, 3, seed + 650 + ck))
        t = np.clip(1 - d / hw, 0, 1)
        frac = np.clip(t / 0.35, 0, 1)
        frac = frac * frac * (3 - 2 * frac)
        inside = land & (t > 0)
        h = np.where(inside, h - cn["depth"] * frac, h)
        relief = np.where(inside, np.minimum(relief, 30 + 120 * (1 - frac)), relief)
        if "wall_biome" in cn:
            biome[inside & (frac < 0.95)] = cn["wall_biome"]
        if "floor_biome" in cn:
            biome[inside & (frac >= 0.95)] = cn["floor_biome"]
        if "tier" in cn:
            mid = pts[len(pts) // 2]
            extra_tiers.append({"tier": cn["tier"], "x": float(mid[0]), "z": float(mid[1])})
    # Sea floor: shelf, then deep water.
    depth = np.clip(d_out / spec.get("shelf_width", 1200), 0, 1)
    h = np.where(land, h, SEA - 4 - (SEA - 4 - spec.get("deep_floor", 28)) * depth)
    biome[~land & (depth > 0.6)] = DEEP_OCEAN
    for m, b, shallow in sea_regions:
        biome[m & ~land & ((depth < 0.6) if shallow else True)] = b
    # Deep basins ({circle, floor, wall, biome}): a sheer-walled hole in the sea floor, e.g. a
    # blue hole: a dark disc of deep water dropping out of shallow reef.
    for bs in spec.get("basins", []):
        bx_, bz_, br = bs["circle"]
        wob = 1 + 0.08 * fbm(gx, gz, max(br * 0.5, 64), 2, seed + 77)
        t = np.clip((br * wob - np.hypot(gx - bx_, gz - bz_)) / bs.get("wall", 48), 0, 1)
        inside = (t > 0) & ~land
        h = np.where(inside, np.minimum(h, h + (bs["floor"] - h) * t ** 0.5), h)
        if "biome" in bs:
            biome[inside] = bs["biome"]

    # Drainage: where water really flows over this terrain (coarse grid, priority-flood so every
    # basin drains to the sea). Feeds terrain-following auto rivers, and gives every river,
    # hand-drawn or not, a water level that steps down toward the sea instead of a sea-level trench.
    rivers = [dict(r) for r in spec.get("rivers", [])]
    flow = drainage(h, land, size, half, spec.get("auto_rivers", {}).get("cell", 128),
                    rain=rainfall(biome, spec.get("auto_rivers", {}).get("rain", {})))
    if "auto_rivers" in spec:
        rivers += auto_rivers(spec["auto_rivers"], flow, biome, names_cache())

    # Rivers: meandering carved channels. {points, width, biome (default River), meander
    # (blocks of sideways wander), dry: true for a shallow dry bed with no water}. Points run
    # from source to mouth; the water level follows the drained terrain and only ever falls.
    water = np.zeros((n, n), np.float32)
    for ri_k, river in enumerate(rivers):
        pts = meander(river["points"], river.get("meander", 220), seed + 500 + ri_k)
        lv = np.minimum.accumulate(np.array([flow.level_at(x, z) for x, z in pts]))
        ri = Image.new("L", (n, n), 0)
        li = Image.new("L", (n, n), 0)
        w = max(1, round(river.get("width", 32) / PX))
        pp = _poly(n, pts, size)
        ImageDraw.Draw(ri).line(pp, fill=255, width=w, joint="curve")
        for (a, b), l in zip(zip(pp, pp[1:]), lv[1:]):
            ImageDraw.Draw(li).line([a, b], fill=int(np.clip(l, 0, 255)), width=w)
        m = (np.asarray(ri) > 0) & land
        if not m.any():
            continue
        lvl = np.asarray(li).astype(np.float32)
        d, idx = ndimage.distance_transform_edt(~m, return_indices=True)
        d = d * PX
        bed_l = lvl[idx[0], idx[1]]                      # level of the nearest channel pixel
        bank = np.clip(d / river.get("valley", 160), 0, 1) ** 0.5
        if river.get("dry"):
            h = np.where(land, h - river.get("depth", 5) * (1 - bank), h)
        else:
            surf = np.maximum(bed_l, SEA)                  # water surface; never below the sea
            hw = max(PX, river.get("width", 32) / 2.0)     # channel half-width in blocks
            bed = surf - 3 - river.get("width", 32) / 40.0  # deeper channel for wider rivers
            valley = river.get("valley", 160)
            near = d < hw + valley
            # Channel floor inside the half-width; outside it the banks climb from just above the
            # water toward the original ground, so the water stays in its channel.
            t = np.clip((d - hw) / valley, 0, 1) ** 0.5
            bank_h = surf + 1 + (h - surf - 1) * t
            target = np.where(d <= hw, bed, np.maximum(bank_h, surf + 1))
            h = np.where(land & near, np.minimum(h, target), h)
            up = land & (d <= hw) & (surf > SEA)
            water = np.where(up, np.maximum(water, surf), water)
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
        # Seeded by the region's own definition, and candidates drawn from a fixed sequence of
        # map positions: adding a feature elsewhere (or prepending regions) can't move these lakes.
        key = json.dumps([r.get("at"), r.get("circle"), (r.get("polygon") or [None])[0], r.get("biomes"), r.get("biome")])
        rng = np.random.default_rng([seed, 7000, abs(hash_str(key))])
        ok = land & (owner == k) & (d_in > 400 + rmax) & (biome != RIVER) & (h > SEA)
        placed = 0
        for _ in range(count * 4000):
            if placed >= count:
                break
            zz, xx = int(rng.integers(0, n)), int(rng.integers(0, n))
            if not ok[zz, xx] or taken[zz, xx]:
                continue
            rad = float(rng.uniform(rmin, rmax))
            ponds.append({"at": [float(xx * PX - half + PX / 2), float(zz * PX - half + PX / 2)], "r": rad})
            sp = int(2.5 * rmax / PX)
            taken[max(0, zz - sp):zz + sp, max(0, xx - sp):xx + sp] = True
            placed += 1
    for i, p in enumerate(ponds):
        p["id"] = i
        p.setdefault("depth", max(4, min(14, p["r"] / 40)))
        p["sid"] = (int(p["at"][0]) // 16 * 7919 + int(p["at"][1]) // 16 * 104729) % 1000003   # stable per lake
        prng = np.random.default_rng([seed, 9500, p["sid"]])
        p.setdefault("rot", float(prng.uniform(0, math.pi)))
        p.setdefault("aspect", float(prng.uniform(1.0, 2.2)))
        cx, cz, rad = p["at"][0], p["at"][1], p["r"]
        j0, j1 = max(0, int((cx - 1.7 * rad + half) / PX)), min(n, int((cx + 1.7 * rad + half) / PX) + 2)
        i0, i1 = max(0, int((cz - 1.7 * rad + half) / PX)), min(n, int((cz + 1.7 * rad + half) / PX) + 2)
        if j1 <= j0 or i1 <= i0:
            continue
        sl = (slice(i0, i1), slice(j0, j1))
        bx, bz = gx[sl], gz[sl]
        d = pond_distance(bx, bz, p, seed + 9000 + p["sid"])
        rr = np.hypot(bx - cx, bz - cz)
        ring = (rr > rad * 1.2) & (rr < rad * 1.6) & land[sl]
        if "level" not in p:         # an explicit level pins a pool to its terrace
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
    # beach_skip: biomes that meet the sea directly (a glacier or an iceberg has no beach).
    beach &= ~np.isin(biome, spec.get("beach_skip", []))
    biome[beach & (biome != RIVER)] = BEACH

    os.makedirs(plan_dir, exist_ok=True)
    Image.fromarray(np.clip(h * 257, 0, 65535).astype(np.uint16)).save(f"{plan_dir}/height.png")
    Image.fromarray(biome).save(f"{plan_dir}/biome.png")
    Image.fromarray(np.clip(relief, 0, 255).astype(np.uint8)).save(f"{plan_dir}/relief.png")
    Image.fromarray(water.astype(np.uint8)).save(f"{plan_dir}/water.png")
    # Surface materials the expansion carries to WorldPainter ({circle|polygon, material}).
    surf = np.zeros((n, n), np.uint8)
    for m, code in plateau_surf:
        surf[m] = code
    for s_ in spec.get("surfaces", []):
        si = Image.new("L", (n, n), 0)
        ImageDraw.Draw(si).polygon(_poly(n, region_polygon(s_), size), fill=255)
        surf[np.asarray(si) > 0] = SURFACES.index(s_["material"]) + 1
    Image.fromarray(surf).save(f"{plan_dir}/surface.png")
    meta = {k: spec[k] for k in ("size", "seed") if k in spec}
    meta["px"] = PX
    meta["coast_warp"] = spec.get("coast_warp", 600)
    # Plateaus, so expand can recut their walls at block resolution (a 16-block plan smears a
    # cliff into a 45-degree slope). Outlines as polygons, in the spec's own coordinates.
    meta["plateaus"] = [dict({k: v for k, v in pl.items() if k not in ("circle", "polygon")},
                             polygon=[[float(x), float(z)] for x, z in region_polygon(pl)])
                        for pl, pm in plateaus if pm.any()]
    Image.fromarray((land * 255).astype(np.uint8)).save(f"{plan_dir}/land.png")
    meta["ponds"] = [p for p in ponds if "level" in p]
    # Biome patches are labelled in the preview from biome.png by their real names; regions
    # only carry their tier, shown at the centre of the land they own.
    meta["regions"] = []
    for k, r in enumerate(spec["regions"]):
        own = land & (owner == k)
        if own.any() and "tier" in r:   # marker at the most interior point (a ring's mean is in its hole)
            zz, xx = np.unravel_index(ndimage.distance_transform_edt(own).argmax(), own.shape)
            meta["regions"].append({"tier": r["tier"], "x": float(xx * PX - half), "z": float(zz * PX - half)})
    meta["regions"] += extra_tiers
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

# Ground blocks per column (terrain.png, value = index + 1; 0 = WorldPainter's height-based
# default: grass, sand at the water's edge, stone on peaks). tools/world/wp_piece.js maps each
# name to a WorldPainter terrain.
GROUNDS = ["sand", "red_sand", "mesa", "terracotta", "stone_gravel", "snow", "packed_ice", "podzol",
           "mycelium", "dirt_gravel", "black_sand", "scorched"]
GROUND_RULES = [   # biome name (as biome_names() gives it) -> ground; first match wins
    (r"ocean|river|beach|\bsea\b|reef|kelp|lagoon", None),          # water and shores: default
    (r"desert|dune|oasis|xeric", "sand"),
    (r"mesa|canyon", "mesa"),
    (r"outback", "terracotta"),
    (r"^BoP Crag$|^BoP Alps$", "stone_gravel"),
    (r"volcan", "scorched"),
    (r"wasteland", "dirt_gravel"),
    (r"glacier|tundra|ice plains|ice mountains|frost|arctic|polar|snowy|cold taiga|alps forest", "snow"),
    (r"taiga|boreal|coniferous|spruce", "podzol"),
    (r"mushroom", "mycelium"),
]
SURFACE_GROUND = {"black_sand": "black_sand", "scorched": "scorched", "packed_ice": "packed_ice"}


def ground_lut():
    """biome id -> terrain.png code, and surface.png code -> terrain.png code."""
    lut = np.zeros(256, np.uint8)
    for bid, nm in biome_names().items():
        for pat, g in GROUND_RULES:
            if re.search(pat, nm, re.I):
                lut[bid] = GROUNDS.index(g) + 1 if g else 0
                break
    slut = np.zeros(256, np.uint8)
    for k, nm in enumerate(SURFACES):
        slut[k + 1] = GROUNDS.index(SURFACE_GROUND[nm]) + 1
    return lut, slut


def recut_plateaus(plateaus, Hc, WX, WZ, DET, PW, SB, BB, ox, oz, meta, hp, bp, land, land_s, wp_):
    """Re-cut each plateau's wall at block resolution, on the canvas Hc (origin ox, oz).

    The plan is 16 blocks per pixel and expand samples it cubically, so a plateau's wall came
    out as a ~100-block 45-degree slope whatever its `wall`. Here the outline is tested per
    block (with the plan's own warps: plan.py's coast warp on top of expand's), and the wall is
    rebuilt over `wall` blocks: the lowland ground, taken from just outside the smeared band,
    rises to the top along the plan's own profile. River channels on the top run to the lip, so
    a river leaves the plateau at its top level (tools/world/waterfalls.py then pours it).
    Fills PW (block water level override, -1 = use the plan) and SB (block surface override)."""
    seed, half = meta.get("seed", 1), meta["size"] // 2
    cw = meta.get("coast_warp", 600)
    n = hp.shape[0]
    N = Hc.shape[0]
    G = 64                                       # how far outside the outline the plan's smear reaches
    for pl in plateaus:
        poly = np.array(pl["polygon"], np.float64)
        wall = max(1.0, float(pl.get("wall", 64)))
        mw = int(wall + G + 24)
        c0, c1 = max(0, int(poly[:, 0].min() - mw - ox)), min(N, int(poly[:, 0].max() + mw - ox) + 1)
        r0, r1 = max(0, int(poly[:, 1].min() - mw - oz)), min(N, int(poly[:, 1].max() + mw - oz) + 1)
        if c1 <= c0 or r1 <= r0:
            continue
        sl = (slice(r0, r1), slice(c0, c1))
        wx, wz = WX[sl].astype(np.float64), WZ[sl].astype(np.float64)
        # The polygon rasterised at 1 block, looked up at the warped position of every column.
        px0, pz0 = poly[:, 0].min() - 400, poly[:, 1].min() - 400
        pw_, ph_ = int(poly[:, 0].max() + 400 - px0) + 1, int(poly[:, 1].max() + 400 - pz0) + 1
        im = Image.new("L", (pw_, ph_), 0)
        ImageDraw.Draw(im).polygon([(x - px0, z - pz0) for x, z in poly], fill=255)
        pim = np.asarray(im) > 0

        def inside(ax, az):
            ix = ax + 0.3 * cw * fbm(ax, az, 2400, 4, seed + 1)
            iz = az + 0.3 * cw * fbm(ax, az, 2400, 4, seed + 2)
            jj, ii = np.round(ix - px0).astype(np.int64), np.round(iz - pz0).astype(np.int64)
            ok = (jj >= 0) & (jj < pw_) & (ii >= 0) & (ii < ph_)
            res = np.zeros(ax.shape, bool)
            res[ok] = pim[ii[ok], jj[ok]]
            return res

        lnd = ndimage.map_coordinates(land_s, [(wz + half) / PX - 0.5, (wx + half) / PX - 0.5], order=1, mode="nearest") > 0.5
        M = inside(wx, wz) & lnd
        if not M.any():
            continue
        H = Hc[sl]
        din = ndimage.distance_transform_edt(M)
        dout = ndimage.distance_transform_edt(~M)
        outer = ~M & (dout > G)
        if not outer.any():
            continue
        oi, oj = ndimage.distance_transform_edt(~outer, return_distances=False, return_indices=True)
        low = ndimage.gaussian_filter(H[oi, oj], 6)
        # The plan's own mask at plan resolution gives the water level on either side of the wall.
        pi0, pi1 = max(0, int((r0 + oz + half) / PX) - 4), min(n, int((r1 + oz + half) / PX) + 5)
        pj0, pj1 = max(0, int((c0 + ox + half) / PX) - 4), min(n, int((c1 + ox + half) / PX) + 5)
        pgx, pgz = np.meshgrid((np.arange(pj0, pj1) + 0.5) * PX - half, (np.arange(pi0, pi1) + 0.5) * PX - half)
        pm = inside(pgx, pgz) & (land[pi0:pi1, pj0:pj1] > 0.5)
        wpl = wp_[pi0:pi1, pj0:pj1].astype(np.int16)
        # Inside the outline, a river pixel that already took the lowland's level (the plan
        # steps the level down a pixel or two before the edge) carries the top's level instead,
        # so the top river runs to the lip rather than stopping a pixel short on a dry sill.
        if pm.any() and (~pm).any():
            thr = 0.5 * (pl["top"] + float(np.median(hp[pi0:pi1, pj0:pj1][~pm])))
            up = pm & (wpl > thr)
            lowin = pm & (wpl > 0) & (wpl <= thr)
            for _ in range(2):
                dil = ndimage.grey_dilation(np.where(up, wpl, 0), size=3)
                fill = lowin & ~up & (dil > 0)
                wpl = np.where(fill, dil, wpl)
                up |= fill
        if pm.any() and (~pm).any():
            a, b = ndimage.distance_transform_edt(~pm, return_distances=False, return_indices=True)
            w_in = wpl[a, b]
            a, b = ndimage.distance_transform_edt(pm, return_distances=False, return_indices=True)
            w_out = wpl[a, b]
            b_out = bp[pi0:pi1, pj0:pj1][a, b]
        else:
            w_in = w_out = wpl
            b_out = bp[pi0:pi1, pj0:pj1]
        bi = np.clip(((wz + half) / PX).astype(np.int64) - pi0, 0, pi1 - pi0 - 1)
        bj = np.clip(((wx + half) / PX).astype(np.int64) - pj0, 0, pj1 - pj0 - 1)
        win, wout = w_in[bi, bj], w_out[bi, bj]
        # Near the edge the smear pulled the top down (and the cubic overshoot up): set it to the top as it stands
        # further in (the nearest ground at least wall + 48 blocks inside, plus this column's own
        # fine detail), fading out by wall + 64 blocks in, where the plan's top is intact. Small
        # or flat plateaus (terraces nest, so their interior is the next tread up) use the spec top.
        inner = M & (din >= wall + 48)
        if inner.any() and pl.get("relief", 50) > 10:
            a, b = ndimage.distance_transform_edt(~inner, return_distances=False, return_indices=True)
            top = ndimage.gaussian_filter(H[a, b] - DET[sl][a, b], 4) + DET[sl]
        else:
            top = pl["top"] + fbm(wx, wz, 600, 3, seed + 31) * pl.get("top_relief", 10) + DET[sl]
        lift = np.clip((wall + 64 - din) / 32, 0, 1)
        T = H + lift * (top - H)               # both ways: the cubic sampling also overshoots at a lip
        mid = 0.5 * (low + pl["top"])
        chan = M & (win > SEA) & (win > mid)    # a river or lake on the top: keep its bed open
        T = np.where(chan, np.minimum(T, win - 2), T)
        rise = np.clip(din / wall, 0, 1) ** 0.35
        # A channel keeps its bed right to the outline: the river leaves over a sheer lip.
        wallh = np.where(low < T, np.where(chan, T, low + (T - low) * rise), H)
        zone = ~M & (dout <= G)
        Hc[sl] = np.where(M, wallh, np.where(zone, np.minimum(H, low), H)).astype(np.float32)
        # Water: the top's own level inside the outline, the lowland's outside it.
        PW[sl] = np.where(M, win, np.where(zone, wout, PW[sl]))
        if "surface" in pl:
            SB[sl][M] = SURFACES.index(pl["surface"]) + 1
        if "biome" in pl:   # the plateau's biome stops at its wall, not on the plan's 16-block pixels
            own = zone & (bp[pi0:pi1, pj0:pj1][bi, bj] == pl["biome"])
            BB[sl] = np.where(own, b_out[bi, bj], BB[sl])
            # Where the wall stands in the sea (an iceberg), the plan's land pixels round it end up
            # under water: give them the nearest sea's biome, or a glacier there freezes over.
            sea_px = land[pi0:pi1, pj0:pj1] <= 0.5
            if sea_px.any():
                a, b = ndimage.distance_transform_edt(~sea_px, return_distances=False, return_indices=True)
                b_sea = bp[pi0:pi1, pj0:pj1][a, b]
                wet = ~M & (bp[pi0:pi1, pj0:pj1][bi, bj] == pl["biome"]) & (Hc[sl] < SEA - 1)
                BB[sl] = np.where(wet, b_sea[bi, bj], BB[sl])
        print(f"  plateau top {pl['top']} wall {wall:.0f}: {int(M.sum())} blocks recut")


def expand(plan_dir, out_dir, pi, pj, piece):
    hp = np.asarray(Image.open(f"{plan_dir}/height.png")).astype(np.float32) / 257
    bp = np.asarray(Image.open(f"{plan_dir}/biome.png"))
    rp = np.asarray(Image.open(f"{plan_dir}/relief.png")).astype(np.float32) / 255
    meta = json.load(open(f"{plan_dir}/plan.json"))
    if meta.get("px", 16) != PX:
        sys.exit(f"{plan_dir} is a {meta['px']}-block draft; re-render at full resolution (no --px) before expanding")
    size, seed = meta["size"], meta.get("seed", 1)
    half = size // 2
    x0, z0 = -half + pi * piece, -half + pj * piece
    d = f"{out_dir}/piece_{pi}_{pj}"
    os.makedirs(d, exist_ok=True)
    sp = np.asarray(Image.open(f"{plan_dir}/surface.png")) if os.path.exists(f"{plan_dir}/surface.png") \
        else np.zeros_like(bp)
    land = (np.asarray(Image.open(f"{plan_dir}/land.png")) > 0).astype(np.float32) \
        if os.path.exists(f"{plan_dir}/land.png") else (hp >= SEA).astype(np.float32)
    land_s = ndimage.gaussian_filter(land, 0.8)    # so a coast cut by a plateau wall is round, not stepped
    ponds = meta.get("ponds", [])
    wp_ = np.asarray(Image.open(f"{plan_dir}/water.png")).astype(np.uint8) if os.path.exists(f"{plan_dir}/water.png") \
        else np.zeros_like(bp)
    # Plateaus that raise ground (not the biome-only stamps) and reach this piece. The canvas
    # runs E blocks past the piece, so a wall cut near the piece edge sees the ground beyond it.
    E = 128
    N = piece + 2 * E
    ox, oz = x0 - E, z0 - E
    plats = [pl for pl in meta.get("plateaus", []) if pl.get("top", 0) > SEA + 2
             and min(x for x, _ in pl["polygon"]) - 300 < ox + N and max(x for x, _ in pl["polygon"]) + 300 > ox
             and min(z for _, z in pl["polygon"]) - 300 < oz + N and max(z for _, z in pl["polygon"]) + 300 > oz]
    if not plats:
        E, N, ox, oz = 0, piece, x0, z0
    Hc = np.zeros((N, N), np.float32)
    WX = np.zeros((N, N), np.float32)
    WZ = np.zeros((N, N), np.float32)
    DET = np.zeros((N, N), np.float32) if plats else None
    xs = np.arange(N, dtype=np.float64) + ox + 0.5
    for r0 in range(0, N, 256):   # 256-row strips: ~1 GB peak; 1024 needed ~5 GB and paged
        zs = np.arange(r0, min(N, r0 + 256), dtype=np.float64) + oz + 0.5
        X, Z = np.meshgrid(xs, zs)
        # One warp for terrain and biome, so coasts and biome edges are organic and agree.
        wx = X + 40 * fbm(X, Z, 320, 3, seed + 13)
        wz = Z + 40 * fbm(X, Z, 320, 3, seed + 14)
        pz, px = (wz + half) / PX - 0.5, (wx + half) / PX - 0.5
        h = ndimage.map_coordinates(hp, [pz, px], order=3, mode="nearest")
        rel = ndimage.map_coordinates(rp, [pz, px], order=1, mode="nearest")
        detail = fbm(X, Z, 256, 6, seed + 11) * (2 + 22 * rel) + fbm(X, Z, 48, 3, seed + 12) * (0.6 + 4 * rel)
        rows = slice(r0, r0 + len(zs))
        Hc[rows] = h + detail * (0.25 + 0.75 * np.clip((h - SEA) / 8, 0, 1))
        WX[rows], WZ[rows] = wx, wz
        if DET is not None:
            DET[rows] = detail
    PW = np.full((N, N), -1, np.int16)
    SB = np.zeros((N, N), np.uint8)
    BB = np.full((N, N), 255, np.uint8)            # block biome override, 255 = use the plan
    if plats:
        recut_plateaus(plats, Hc, WX, WZ, DET, PW, SB, BB, ox, oz, meta, hp, bp, land, land_s, wp_)
    DET = None
    Hc, WX, WZ, PW, SB, BB = (a[E:E + piece, E:E + piece] for a in (Hc, WX, WZ, PW, SB, BB))
    glut, slut = ground_lut()
    H = np.zeros((piece, piece), np.uint16)
    B = np.zeros((piece, piece), np.uint8)
    S = np.zeros((piece, piece), np.uint8)
    T = np.zeros((piece, piece), np.uint8)
    Wt = np.zeros((piece, piece), np.uint8)
    xs = np.arange(piece, dtype=np.float64) + x0 + 0.5
    for r0 in range(0, piece, 256):
        zs = np.arange(r0, min(piece, r0 + 256), dtype=np.float64) + z0 + 0.5
        X, Z = np.meshgrid(xs, zs)
        rows = slice(r0, r0 + len(zs))
        wx, wz = WX[rows].astype(np.float64), WZ[rows].astype(np.float64)
        h = Hc[rows].astype(np.float64)
        # Lakes: re-carve at block resolution with the plan's own shore function, then flood
        # every depression near the lake that lies below its level.
        zlo, zhi = zs[0], zs[-1]
        for p in ponds:
            cx, cz, rad = p["at"][0], p["at"][1], p["r"]
            if cz + 1.4 * rad < zlo or cz - 1.4 * rad > zhi or cx + 1.4 * rad < x0 or cx - 1.4 * rad > x0 + piece:
                continue
            c0, c1 = max(0, int(cx - 1.4 * rad - x0)), min(piece, int(cx + 1.4 * rad - x0) + 1)
            sx, sz = X[:, c0:c1], Z[:, c0:c1]
            dd = pond_distance(sx, sz, p, seed + 9000 + p.get("sid", p["id"]))
            hs = h[:, c0:c1]
            hs = np.where(dd < 1, np.minimum(hs, p["level"] - 1 - p["depth"] * (1 - dd * dd)), hs)
            h[:, c0:c1] = hs
            if p["level"] > SEA:
                wsl = Wt[r0:r0 + len(zs), c0:c1]
                Wt[r0:r0 + len(zs), c0:c1] = np.where((dd < 1.3) & (hs < p["level"]), p["level"], wsl)
        bi = np.clip(((wz + half) / PX).astype(np.int64), 0, bp.shape[0] - 1)
        bj = np.clip(((wx + half) / PX).astype(np.int64), 0, bp.shape[1] - 1)
        # River water above sea level comes from the plan's water map (by a plateau wall, from its
        # own side of the wall): flood whatever ground lies below the river's surface there.
        pw = np.where(PW[rows] >= 0, PW[rows], wp_[bi, bj])
        Wt[rows] = np.where((pw > SEA) & (h < pw), np.maximum(Wt[rows], pw), Wt[rows])
        H[rows] = np.clip(h * 257, 0, 255 * 257).astype(np.uint16)
        B[rows] = np.where(BB[rows] != 255, BB[rows], bp[bi, bj])
        S[rows] = np.where(SB[rows] > 0, SB[rows], sp[bi, bj])
        T[rows] = np.where(S[rows] > 0, slut[S[rows]], glut[B[rows]])
    Image.fromarray(T).save(f"{d}/terrain.png")       # GROUNDS index + 1, 0 = WorldPainter's default
    json.dump(GROUNDS, open(f"{d}/grounds.json", "w"))
    Image.fromarray(H).save(f"{d}/height.png")
    Image.fromarray(B).save(f"{d}/biome.png")
    Image.fromarray(Wt).save(f"{d}/water.png")       # 0 = the world's sea level
    Image.fromarray(S).save(f"{d}/surface.png")      # SURFACES index + 1, 0 = none
    mine = [p for p in ponds if p["level"] > SEA and x0 - 1.4 * p["r"] <= p["at"][0] <= x0 + piece + 1.4 * p["r"]
            and z0 - 1.4 * p["r"] <= p["at"][1] <= z0 + piece + 1.4 * p["r"]]
    json.dump([{"x": p["at"][0], "z": p["at"][1], "r": p["r"] * 1.6, "level": p["level"]} for p in mine],
              open(f"{d}/lakes.json", "w"))
    # 512-block tiles holding raised water (lakes and rivers), so wp_piece.js scans only those.
    tiles = [[tx * 512, tz * 512] for tz in range(piece // 512) for tx in range(piece // 512)
             if Wt[tz * 512:(tz + 1) * 512, tx * 512:(tx + 1) * 512].any()]
    json.dump(tiles, open(f"{d}/water_tiles.json", "w"))
    open(f"{d}/origin.txt", "w").write(f"{x0} {z0}\n")
    print(f"piece {pi},{pj}: origin {x0},{z0}, {piece} blocks, {len(mine)} raised lakes -> {d}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("render"); a.add_argument("spec"); a.add_argument("plan")
    a.add_argument("--px", type=int, default=16, help="blocks per plan pixel; 32 = fast draft (not for expand)")
    a = sub.add_parser("preview"); a.add_argument("plan")
    a = sub.add_parser("expand"); a.add_argument("plan"); a.add_argument("out")
    a.add_argument("--piece", nargs=2, type=int, required=True); a.add_argument("--piece-size", type=int, default=16384)
    args = ap.parse_args()
    if args.cmd == "render":
        global PX
        PX = args.px
        render(args.spec, args.plan)
        preview(args.plan)
    elif args.cmd == "preview":
        preview(args.plan)
    else:
        expand(args.plan, args.out, args.piece[0], args.piece[1], args.piece_size)


if __name__ == "__main__":
    sys.exit(main())
