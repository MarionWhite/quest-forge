"""Difficulty layer for a continent plan: danger tiers per plan pixel, spawn pockets and picker ratings.

    py -3.10 tools/world/difficulty.py PLANDIR SPEC.yaml [--out DIR] [--map ILLUSTRATED.png --preview OUT.png]
                                       [--write-spawns] [--bake qf-tiers.bin[.gz]]
    py -3.10 tools/world/difficulty.py --read-grid qf-tiers.bin[.gz] [--at X Z ...]

Reads the plan layers tools/world/plan.py writes (regions.png, biome.png, height.png, land.png,
water.png, plan.json) and a difficulty spec (docs/design/world/r14/difficulty.yaml). Writes, into
--out (default PLANDIR):
  difficulty.png   tier per plan pixel (2..5 on land and the inner sea, 6 = beyond)
  difficulty.json  land share per tier and each spawn's rating
--preview draws the tiers as a tinted overlay with a legend, over --map (an illustrated map from
illustrate.py, ideally --no-labels; the plan must fill its inner frame) or else the plan preview.
--write-spawns replaces the spawn points in PLANDIR/plan.json with the spec's, rating included,
so illustrate.py labels them ("Spawn: Hard").
--bake writes the tier grid the game reads (qf-content's difficulty hook): one byte per chunk over
the whole plan, with the header described at write_grid(). A name ending in .gz is gzipped (the
mod reads either). Copy it into a world as <world>/data/qf-tiers.bin.
--read-grid checks a baked file: header, tier counts, and the tier at each --at X Z.

The layer is independent of terrain: it changes no blocks. Design: a base tier per region (the
zone covering most of the region's land), blended across region borders; T5 hot zones that pull
difficulty up with a smooth falloff; a small pocket around each spawn (T2, then a ramp back; there
is no T1); and the outer sea and ring marked T6, the way to the outskirts.
"""
import argparse
import gzip
import hashlib
import json
import math
import os
import struct
import sys
import zlib

import numpy as np
import yaml
from PIL import Image, ImageDraw
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from plan import RIVER  # noqa: E402

MIN_TIER = 2   # no T1 (the author's decision, 2026-10-25): the spawn pockets are T2
TIER_NAMES = {1: "Safe", 2: "Spawn pocket", 3: "Quite difficult", 4: "Hard", 5: "Very difficult", 6: "Beyond"}
TIER_COLS = {1: (96, 168, 92), 2: (176, 186, 84), 3: (214, 164, 70), 4: (200, 96, 46), 5: (150, 24, 40),
             6: (66, 26, 92)}


def smooth01(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


class Plan:
    def __init__(self, d):
        self.dir = d
        self.meta = json.load(open(f"{d}/plan.json"))
        self.h = np.asarray(Image.open(f"{d}/height.png")).astype(np.float32) / 257
        self.b = np.asarray(Image.open(f"{d}/biome.png"))
        self.reg = np.asarray(Image.open(f"{d}/regions.png")).astype(np.int32)
        self.land = (np.asarray(Image.open(f"{d}/land.png")) > 0) if os.path.exists(f"{d}/land.png") else self.reg > 0
        w = np.asarray(Image.open(f"{d}/water.png")).astype(np.float32) if os.path.exists(f"{d}/water.png") \
            else np.zeros_like(self.h)
        self.lake = (w > 0) & (self.h < w) & self.land
        self.n = self.b.shape[0]
        self.px = self.meta["px"]
        self.half = self.meta["size"] / 2
        c = (np.arange(self.n, dtype=np.float32) + 0.5) * self.px - self.half
        self.X, self.Z = c[None, :], c[:, None]

    def ij(self, x, z):
        return (int(np.clip((z + self.half) / self.px, 0, self.n - 1)),
                int(np.clip((x + self.half) / self.px, 0, self.n - 1)))


def shape_mask(p, z):
    """Boolean mask of a zone spec: circle, box, box + min_height, or biomes + depth (+ box)."""
    m = np.ones((p.n, p.n), bool)
    if "circle" in z:
        x0, z0, r = z["circle"]
        m &= (p.X - x0) ** 2 + (p.Z - z0) ** 2 <= r * r
    if "box" in z:
        x0, z0, x1, z1 = z["box"]
        m &= (p.X >= x0) & (p.X <= x1) & (p.Z >= z0) & (p.Z <= z1)
    if "min_height" in z:
        m &= p.land & (p.h >= z["min_height"])
    if "biomes" in z:
        inb = np.isin(p.b, z["biomes"])
        m &= inb & (ndimage.distance_transform_edt(inb) * p.px >= z.get("depth", 0))
    return m


def build(p, spec):
    land = p.land
    # ---- base tier per region
    bs = spec["base"]
    zt = np.full((p.n, p.n), bs.get("default", 3), np.float32)
    done = np.zeros((p.n, p.n), bool)
    for z in bs.get("zones", []):
        m = shape_mask(p, z) & ~done
        zt[m] = z["tier"]
        done |= m
    base = zt.copy()
    ids = np.unique(p.reg[land])
    for rid in ids:
        sel = land & (p.reg == rid)
        vals, cnt = np.unique(zt[sel], return_counts=True)
        base[sel] = vals[cnt.argmax()]
    sig = bs.get("blend", 500) / p.px / 2
    lf = land.astype(np.float32)
    D = ndimage.gaussian_filter(base * lf, sig) / np.maximum(ndimage.gaussian_filter(lf, sig), 1e-3)
    D = np.where(land, D, 0)
    if (~land).any():   # the inner sea carries the tier of its nearest shore
        idx = ndimage.distance_transform_edt(~land, return_distances=False, return_indices=True)
        D = D[idx[0], idx[1]]
    # ---- T5 hot zones: signed distance to each mask, roughened by noise so edges are organic
    wb = spec.get("wobble", {})
    rng = np.random.default_rng(wb.get("seed", 14))

    def noise(scale):
        g = ndimage.gaussian_filter(rng.standard_normal((p.n, p.n)).astype(np.float32), scale / p.px, mode="wrap")
        return np.clip(g / (g.std() + 1e-6), -2, 2)

    edge_n = noise(wb.get("edge_scale", 900)) * wb.get("edge", 0)
    hot_w = np.zeros_like(D)
    for z in spec.get("hot", []):
        m = shape_mask(p, z)
        if not m.any():
            print(f"warning: hot zone '{z.get('what')}' is empty")
            continue
        sd = (ndimage.distance_transform_edt(~m) - ndimage.distance_transform_edt(m)) * p.px + edge_n
        w = smooth01(1 - sd / z.get("falloff", 1500))
        hot_w = np.maximum(hot_w, w)
    D = D + np.clip(5 - D, 0, None) * hot_w
    # A low-frequency wobble (in tiers) so region-tier borders are not exact region outlines.
    if wb.get("amp", 0):
        D = D + wb["amp"] * noise(wb.get("scale", 1200)) * np.clip(5 - D, 0, 1) * np.clip(D - 2, 0, 1)
    # ---- spawn pockets: the pocket tier (T2) within `safe`, then a ramp from it to 6 over `blend`
    pk = spec.get("pocket", {})
    low, safe, blend = pk.get("tier", MIN_TIER), pk.get("safe", 500), pk.get("blend", 1200)
    for s in spec.get("spawns", []):
        d = np.hypot(p.X - s["x"], p.Z - s["z"])
        cap = np.where(d < safe, float(low), low + (6.0 - low) * (d - safe) / blend)
        D = np.minimum(D, cap)
    D = np.maximum(D, MIN_TIER)
    tier = np.clip(np.round(D), MIN_TIER, 5).astype(np.uint8)
    # ---- beyond: the edge ring of the plan and the open sea joined to it
    by = spec.get("beyond", {})
    ring = by.get("ring", 2500)
    edge = np.minimum(np.minimum(p.X + p.half, p.half - p.X), np.minimum(p.Z + p.half, p.half - p.Z)) < ring
    far = ~land & (ndimage.distance_transform_edt(~land) * p.px > by.get("open_sea", 4000))
    lab, nl = ndimage.label(far | (edge & ~land))
    keep = np.unique(lab[edge & ~land])
    beyond = np.isin(lab, keep[keep > 0]) & ~land
    tier[beyond] = 6
    D = np.where(beyond, 6.0, D)
    return tier, D, base


def check_spawns(p, spec):
    """Warnings for spawns in water, on steep ground, on a landmark or too close together."""
    warn = []
    sp = spec.get("spawns", [])
    rng = ndimage.maximum_filter(p.h, 13) - ndimage.minimum_filter(p.h, 13)
    wet = ~p.land | p.lake | (p.b == RIVER) | (p.b == 11)
    lms = [(q["x"], q["z"], q.get("name", "")) for q in p.meta.get("points", []) if q.get("kind") == "landmark"]
    for s in sp:
        i, j = p.ij(s["x"], s["z"])
        tag = s.get("where", f"{s['x']},{s['z']}")
        if wet[i, j]:
            warn.append(f"{tag}: in water")
        if rng[i, j] > 16:
            warn.append(f"{tag}: rough ground ({rng[i, j]:.0f} blocks of relief within ~200 blocks)")
        for x, z, nm in lms:
            if math.hypot(x - s["x"], z - s["z"]) < 1200:
                warn.append(f"{tag}: within 1200 blocks of {nm}")
    for a in range(len(sp)):
        for b in range(a + 1, len(sp)):
            d = math.hypot(sp[a]["x"] - sp[b]["x"], sp[a]["z"] - sp[b]["z"])
            if d < spec.get("min_spacing", 8000):
                warn.append(f"{sp[a].get('where')} / {sp[b].get('where')}: only {d:.0f} blocks apart")
    return warn


def ratings(p, spec, tier):
    """Picker rating per spawn. The score is the mean tier of the land around the spawn, from
    `inner` (past the pocket every spawn shares) out to `radius`, weighted toward the spawn
    (weight: linear falls from 1 at `inner` to 0 at `radius`; flat weighs it all alike).
    labels: [[cut, name], ...] by score; or mode: rank with split: [n Gentle, n Hard, ...] and
    names: labels by rank among the spawns, so the gentlest spawns are Gentle however hard
    the map is overall (the author's design: most of the map is hard)."""
    rs = spec.get("rating", {})
    R, R0 = rs.get("radius", 3000), rs.get("inner", 0)
    out = []
    for s in spec.get("spawns", []):
        d = np.hypot(p.X - s["x"], p.Z - s["z"])
        m = p.land & ~p.lake & (d <= R) & (d >= R0)
        w = np.clip((R - d) / max(R - R0, 1), 0, 1) if rs.get("weight", "flat") == "linear" else np.ones_like(d)
        score = float((tier * w)[m].sum() / max(w[m].sum(), 1e-9)) if m.any() else 0.0
        sp = min(math.hypot(s["x"] - o["x"], s["z"] - o["z"]) for o in spec["spawns"] if o is not s)
        out.append(dict(where=s.get("where", ""), x=s["x"], z=s["z"], score=round(score, 2), nearest_spawn=round(sp)))
    if rs.get("mode") == "rank":
        names = rs.get("names", ["Gentle", "Hard", "Brutal", "Deadly"])
        split = rs.get("split") or [len(out) // len(names)] * len(names)
        ranked = sorted(range(len(out)), key=lambda i: out[i]["score"])
        k = 0
        for nm, cnt in zip(names, split):
            for i in ranked[k:k + cnt]:
                out[i]["rating"] = nm
            k += cnt
        for i in ranked[k:]:
            out[i]["rating"] = names[-1]
    else:
        labels = rs.get("labels", [[2.75, "Gentle"], [3.2, "Hard"], [3.6, "Brutal"], [99, "Deadly"]])
        for r in out:
            r["rating"] = next(nm for t, nm in labels if r["score"] < t)
    return out


def shares(p, tier):
    m = p.land
    return {t: float((tier[m] == t).mean()) for t in range(MIN_TIER, 7)}


def preview(p, spec, D, tier, rates, sh, out, base_img=None):
    from illustrate import font, spawn_marker
    if base_img:
        canvas = Image.open(base_img).convert("RGBA")
        N = canvas.size[0]
        m0 = int(N * 0.045)
    else:
        canvas = Image.open(f"{p.dir}/preview.png").convert("RGBA")
        N, m0 = canvas.size[0], 0
    M = N - 2 * m0
    s = N / 4096
    # Continuous field upsampled, then cut into tiers: smooth borders, not plan pixels.
    Dm = np.asarray(Image.fromarray(np.where(tier == 6, 6.0, D).astype(np.float32), "F").resize((M, M), Image.BILINEAR))
    Tm = np.clip(np.round(Dm), 1, 6).astype(np.int32)
    landm = np.asarray(Image.fromarray(p.land.astype(np.float32), "F").resize((M, M), Image.BILINEAR)) > 0.5
    lut = np.zeros((7, 3), np.float32)
    for t, c in TIER_COLS.items():
        lut[t] = c
    col = lut[Tm]
    alpha = np.where(landm, 0.42, 0.0)
    alpha = np.where(~landm & (Tm == 5), 0.32, alpha)           # hot sea (the Maelstrom)
    alpha = np.where(~landm & (Tm == 6), 0.40, alpha)
    alpha = np.where(Tm == 5, alpha * 1.15, alpha)
    edge = np.zeros((M, M), bool)
    edge[1:, :] |= Tm[1:, :] != Tm[:-1, :]
    edge[:, 1:] |= Tm[:, 1:] != Tm[:, :-1]
    if round(s) > 1:   # iterations=0 would dilate until nothing changes
        edge = ndimage.binary_dilation(edge, iterations=round(s) - 1)
    edge &= landm | (Tm >= 5)
    col[edge] = (52, 30, 22)
    alpha = np.where(edge, 0.7, alpha)
    rgba = np.dstack([col, alpha[..., None] * 255]).astype(np.uint8)
    ov = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ov.paste(Image.fromarray(rgba, "RGBA"), (m0, m0))
    canvas = Image.alpha_composite(canvas, ov)

    d = ImageDraw.Draw(canvas)
    ink = (46, 34, 24, 255)
    halo = (238, 226, 196, 220)
    k = M / p.n
    f = font("palab.ttf", int(28 * s))
    for r in rates:
        x = m0 + (r["x"] + p.half) / p.px * k
        y = m0 + (r["z"] + p.half) / p.px * k
        spawn_marker(d, x, y, 15 * s, ink, max(1, s))
        d.text((x + 24 * s, y), f"Spawn: {r['rating']} ({r['score']:.1f})", font=f, anchor="lm", fill=ink,
               stroke_width=max(2, round(3 * s)), stroke_fill=halo)
    # Legend, bottom right inside the map.
    fl = font("pala.ttf", int(26 * s))
    fh = font("palab.ttf", int(30 * s))
    rows = [t for t in range(MIN_TIER, 7)]
    lw, lh = 560 * s, (90 + 46 * len(rows)) * s
    lx, ly = N - m0 - lw - 40 * s, N - m0 - lh - 40 * s
    d.rectangle((lx, ly, lx + lw, ly + lh), fill=(232, 218, 182, 235), outline=ink, width=max(2, round(3 * s)))
    d.text((lx + lw / 2, ly + 36 * s), "D I F F I C U L T Y", font=fh, anchor="mm", fill=ink)
    for i, t in enumerate(rows):
        yy = ly + (78 + 46 * i) * s
        d.rectangle((lx + 30 * s, yy, lx + 80 * s, yy + 30 * s), fill=TIER_COLS[t] + (255,), outline=ink)
        share = f"{sh[t] * 100:.0f}% of land" if t < 6 else "outer sea"
        d.text((lx + 100 * s, yy + 15 * s), f"T{t}  {TIER_NAMES[t]}", font=fl, anchor="lm", fill=ink)
        d.text((lx + lw - 30 * s, yy + 15 * s), share, font=fl, anchor="rm", fill=ink)
    canvas.convert("RGB").save(out)
    print(f"wrote {out}")


# ---- the baked tier grid (read by qf-content's com.questforge.content.difficulty.TierGrid)
GRID_MAGIC = b"QFTG"
GRID_VERSION = 1
GRID_HEADER = 64
OUTSIDE_TIER = 6


def chunk_grid(p, D, tier):
    """The tier of every chunk the plan covers (rows = z, columns = x), sampled at chunk centres.

    The continuous difficulty is interpolated bilinearly, so a 32-block plan pixel does not show
    as a 2x2 block of chunks; the beyond mask (T6) is taken from the nearest plan pixel."""
    n = int(round(p.half * 2 / 16))
    c = (np.arange(n, dtype=np.float64) + 0.5) * 16 - p.half            # chunk centres, in blocks
    u = (c + p.half) / p.px - 0.5                                         # in plan pixels
    U, V = np.meshgrid(u, u, indexing="ij")                               # U = row (z), V = column (x)
    Dc = ndimage.map_coordinates(D.astype(np.float32), [U, V], order=1, mode="nearest")
    near = np.clip(((c + p.half) // p.px).astype(np.int64), 0, p.n - 1)
    beyond = (tier == 6)[near[:, None], near[None, :]]
    out = np.clip(np.round(Dc), MIN_TIER, 5).astype(np.uint8)
    out[beyond] = 6
    return out


def write_grid(path, grid, origin_cx, origin_cz, spec_bytes):
    """Writes the tier grid. Big-endian (Java's DataInputStream), 64-byte header:

        0  4s   magic "QFTG"
        4  u16  version (1)
        6  u16  header length in bytes (64); data starts here
        8  i32  origin chunk x (the chunk of column 0)
       12  i32  origin chunk z (the chunk of row 0)
       16  i32  width in chunks (columns, along x)
       20  i32  height in chunks (rows, along z)
       24  u8   min tier in the data (2)
       25  u8   max tier in the data (6)
       26  u8   tier just outside the grid (6; the mod raises it with distance)
       27  u8   reserved (0)
       28  u32  CRC-32 of the data
       32  32s  SHA-256 of the difficulty spec (difficulty.yaml) it was baked from
       64  data: width*height bytes, row-major; chunk (cx, cz) is at (cz-z0)*width + (cx-x0)

    A path ending in .gz is gzipped; the mod detects gzip by its magic bytes either way."""
    h, w = grid.shape
    data = np.ascontiguousarray(grid, dtype=np.uint8).tobytes()
    head = struct.pack(">4sHHiiiiBBBBI32s", GRID_MAGIC, GRID_VERSION, GRID_HEADER, origin_cx, origin_cz, w, h,
                       int(grid.min()), int(grid.max()), OUTSIDE_TIER, 0, zlib.crc32(data) & 0xFFFFFFFF,
                       hashlib.sha256(spec_bytes).digest())
    assert len(head) == GRID_HEADER
    if path.endswith(".gz"):
        # mtime 0 and no file name, so the same grid always bakes to the same bytes
        with open(path, "wb") as raw, gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as f:
            f.write(head + data)
    else:
        with open(path, "wb") as f:
            f.write(head + data)
    print(f"wrote {path}: {w}x{h} chunks from chunk ({origin_cx}, {origin_cz}), {os.path.getsize(path):,} bytes")


def read_grid(path):
    raw = open(path, "rb").read()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    magic, ver, hl, x0, z0, w, h, tmin, tmax, tout, _, crc, sha = struct.unpack(">4sHHiiiiBBBBI32s", raw[:64])
    if magic != GRID_MAGIC:
        raise SystemExit(f"{path}: not a tier grid (magic {magic!r})")
    data = raw[hl:hl + w * h]
    if len(data) != w * h or zlib.crc32(data) & 0xFFFFFFFF != crc:
        raise SystemExit(f"{path}: truncated or corrupt (CRC mismatch)")
    hdr = dict(version=ver, header=hl, origin=(x0, z0), size=(w, h), tiers=(tmin, tmax), outside=tout,
               spec_sha256=sha.hex())
    return hdr, np.frombuffer(data, np.uint8).reshape(h, w)


def grid_report(path, points):
    hdr, g = read_grid(path)
    print(json.dumps(hdr))
    vals, cnt = np.unique(g, return_counts=True)
    print("chunks per tier: " + ", ".join(f"T{v} {c:,} ({c / g.size * 100:.1f}%)" for v, c in zip(vals, cnt)))
    x0, z0 = hdr["origin"]
    w, h = hdr["size"]
    for x, z in points:
        cx, cz = math.floor(x / 16), math.floor(z / 16)
        inside = 0 <= cx - x0 < w and 0 <= cz - z0 < h
        print(f"  ({x}, {z}) chunk ({cx}, {cz}): " + (f"T{g[cz - z0, cx - x0]}" if inside else "outside the grid"))


def main():
    if "--read-grid" in sys.argv:
        ap = argparse.ArgumentParser(description="check a baked tier grid")
        ap.add_argument("--read-grid", required=True)
        ap.add_argument("--at", nargs=2, type=int, action="append", default=[], metavar=("X", "Z"))
        a = ap.parse_args()
        grid_report(a.read_grid, a.at)
        return
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan_dir")
    ap.add_argument("spec")
    ap.add_argument("--out", help="directory for difficulty.png/json (default: the plan dir)")
    ap.add_argument("--map", help="illustrated map to draw the preview over (illustrate.py --no-labels)")
    ap.add_argument("--preview", help="write the tinted overlay here")
    ap.add_argument("--write-spawns", action="store_true", help="replace the spawn points in plan.json with the spec's")
    ap.add_argument("--bake", metavar="OUT.bin[.gz]", help="write the per-chunk tier grid the game reads")
    a = ap.parse_args()
    spec = yaml.safe_load(open(a.spec))
    p = Plan(a.plan_dir)
    tier, D, _ = build(p, spec)
    out = a.out or a.plan_dir
    os.makedirs(out, exist_ok=True)
    Image.fromarray(tier).save(f"{out}/difficulty.png")
    rates = ratings(p, spec, tier)
    sh = shares(p, tier)
    for w in check_spawns(p, spec):
        print("warning:", w)
    print("land share per tier: " + ", ".join(f"T{t} {v * 100:.1f}%" for t, v in sh.items() if t < 6))
    for r in rates:
        print(f"  {r['rating']:7s} {r['score']:.2f}  ({r['x']:6d}, {r['z']:6d})  {r['where']}  "
              f"[nearest spawn {r['nearest_spawn']}]")
    json.dump({"shares": {f"T{t}": round(v, 4) for t, v in sh.items()}, "spawns": rates},
              open(f"{out}/difficulty.json", "w"), indent=1)
    if a.write_spawns:
        pj = f"{a.plan_dir}/plan.json"
        meta = json.load(open(pj))
        meta["points"] = [q for q in meta.get("points", []) if q.get("kind") != "spawn"] + \
            [{"kind": "spawn", "tier": 1, "x": r["x"], "z": r["z"], "rating": r["rating"], "score": r["score"]}
             for r in rates]
        json.dump(meta, open(pj, "w"), indent=1)
        print(f"wrote {len(rates)} spawns into {pj}")
    if a.preview:
        preview(p, spec, D, tier, rates, sh, a.preview, a.map)
    if a.bake:
        grid = chunk_grid(p, D, tier)
        origin = -int(round(p.half / 16))
        write_grid(a.bake, grid, origin, origin, open(a.spec, "rb").read())


if __name__ == "__main__":
    main()
