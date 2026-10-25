"""Difficulty layer for a continent plan: danger tiers per plan pixel, spawn pockets and picker ratings.

    py -3.10 tools/world/difficulty.py PLANDIR SPEC.yaml [--out DIR] [--map ILLUSTRATED.png --preview OUT.png]
                                       [--write-spawns]

Reads the plan layers tools/world/plan.py writes (regions.png, biome.png, height.png, land.png,
water.png, plan.json) and a difficulty spec (docs/design/world/r14/difficulty.yaml). Writes, into
--out (default PLANDIR):
  difficulty.png   tier per plan pixel (1..5 on land and the inner sea, 6 = beyond)
  difficulty.json  land share per tier and each spawn's rating
--preview draws the tiers as a tinted overlay with a legend, over --map (an illustrated map from
illustrate.py, ideally --no-labels; the plan must fill its inner frame) or else the plan preview.
--write-spawns replaces the spawn points in PLANDIR/plan.json with the spec's, rating included,
so illustrate.py labels them ("Spawn: Hard").

The layer is independent of terrain: it changes no blocks. Design: a base tier per region (the
zone covering most of the region's land), blended across region borders; T5 hot zones that pull
difficulty up with a smooth falloff; a small safe pocket around each spawn (T1, then a T2 apron,
then a ramp back); and the outer sea and ring marked T6, the way to the outskirts.
"""
import argparse
import json
import math
import os
import sys

import numpy as np
import yaml
from PIL import Image, ImageDraw
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from plan import RIVER  # noqa: E402

TIER_NAMES = {1: "Safe", 2: "Apron", 3: "Quite difficult", 4: "Hard", 5: "Very difficult", 6: "Beyond"}
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
    # ---- spawn pockets
    pk = spec.get("pocket", {})
    safe, apron, blend = pk.get("safe", 750), pk.get("apron", 800), pk.get("blend", 1200)
    for s in spec.get("spawns", []):
        d = np.hypot(p.X - s["x"], p.Z - s["z"])
        cap = np.where(d < safe, 1.0, np.where(d < safe + apron, 2.0, 2.0 + 4.0 * (d - safe - apron) / blend))
        D = np.minimum(D, cap)
    tier = np.clip(np.round(D), 1, 5).astype(np.uint8)
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
    rs = spec.get("rating", {})
    R = rs.get("radius", 3000)
    labels = rs.get("labels", [[2.75, "Gentle"], [3.2, "Hard"], [3.6, "Brutal"], [99, "Deadly"]])
    out = []
    for s in spec.get("spawns", []):
        m = p.land & ~p.lake & (np.hypot(p.X - s["x"], p.Z - s["z"]) <= R)
        score = float(tier[m].mean()) if m.any() else 0.0
        lab = next(nm for t, nm in labels if score < t)
        sp = min(math.hypot(s["x"] - o["x"], s["z"] - o["z"]) for o in spec["spawns"] if o is not s)
        out.append(dict(where=s.get("where", ""), x=s["x"], z=s["z"], score=round(score, 2), rating=lab,
                        nearest_spawn=round(sp)))
    return out


def shares(p, tier):
    m = p.land
    return {t: float((tier[m] == t).mean()) for t in range(1, 7)}


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
    rows = [t for t in range(1, 7)]
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


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan_dir")
    ap.add_argument("spec")
    ap.add_argument("--out", help="directory for difficulty.png/json (default: the plan dir)")
    ap.add_argument("--map", help="illustrated map to draw the preview over (illustrate.py --no-labels)")
    ap.add_argument("--preview", help="write the tinted overlay here")
    ap.add_argument("--write-spawns", action="store_true", help="replace the spawn points in plan.json with the spec's")
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


if __name__ == "__main__":
    main()
