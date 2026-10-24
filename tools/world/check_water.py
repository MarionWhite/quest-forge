#!/usr/bin/env python3
"""Raised-water check: the plan's water.png levels vs the water the populated world actually holds.

    py -3.10 tools/world/check_water.py WORLD PIECES_DIR OUT_DIR NAME,X,Z,R [NAME,X,Z,R ...]

Written for docs/design/world/r13-ingame-test.md.
For every column where the plan raises water above sea level (and the planned ground lies
below it), is the top block water/ice, and how far is the surface from the planned level?
Also: unplanned water on land (lakes the decorators add), and ground vs plan. Saves each area as
OUT_DIR/NAME.npz (top block, top y, ground, planned water level, planned height) for profiles."""
import json, os, sys
import numpy as np
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import inspect_area as ia
from scan_island import load_registry

def main():
    if len(sys.argv) < 5:
        sys.exit(__doc__)
    world, pieces, out = sys.argv[1], sys.argv[2], sys.argv[3]
    areas = [a.split(",") for a in sys.argv[4:]]
    reg, meta = load_registry(world)
    bname = lambda i: reg.get(int(i), f"minecraft:#{int(i)}" if int(i) < 256 else f"?:{int(i)}")
    cats = ia.categories(bname)
    res = {}
    with Pool(6, initializer=ia._init, initargs=(cats,)) as pool:
        for name, X, Z, R in areas:
            X, Z, R = int(X), int(Z), int(R)
            x0, z0, w = X - R, Z - R, 2 * R
            cx0, cz0, cx1, cz1 = x0 // 16, z0 // 16, (x0 + w - 1) // 16, (z0 + w - 1) // 16
            regs = [os.path.join(world, "region", f"r.{rx}.{rz}.mca") for rx in range(cx0 >> 5, (cx1 >> 5) + 1)
                    for rz in range(cz0 >> 5, (cz1 >> 5) + 1)]
            parts = pool.map(ia.scan_region, [(r, cx0, cx1, cz0, cz1) for r in regs if os.path.exists(r)])
            tb = np.zeros((w, w), np.uint16); top = np.zeros((w, w), np.int16); have = np.zeros((w, w), bool)
            ground = np.zeros((w, w), np.int16)
            for p in parts:
                for (cx, cz), (b, t, g, _) in p["surf"].items():
                    px, pz = cx * 16 - x0, cz * 16 - z0
                    sx0, sz0, sx1, sz1 = max(0, -px), max(0, -pz), min(16, w - px), min(16, w - pz)
                    if sx0 >= sx1 or sz0 >= sz1: continue
                    sl = (slice(pz + sz0, pz + sz1), slice(px + sx0, px + sx1))
                    tb[sl], top[sl], ground[sl] = b[sz0:sz1, sx0:sx1], t[sz0:sz1, sx0:sx1], g[sz0:sz1, sx0:sx1]
                    have[sl] = True
            wl = ia.piece_crop(pieces, "water.png", x0, z0, w, w).astype(np.int16)
            ph = (ia.piece_crop(pieces, "height.png", x0, z0, w, w).astype(np.float32) / 257).astype(np.int16)
            wet = cats["water"][tb] | cats["ice"][tb]
            m = (wl > 0) & have
            r = {"raised_cols": int(m.sum())}
            if m.any():
                surf = top + 1   # water surface = y of top water block + 1
                r["raised_is_water_pct"] = round(100 * float(wet[m].mean()), 1)
                d = (surf - wl)[m & wet]
                r["surface_minus_plan"] = {"median": float(np.median(d)) if d.size else None,
                                           "within1_pct": round(100 * float((np.abs(d) <= 1).mean()), 1) if d.size else None}
                r["levels"] = {int(l): {"cols": int((wl == l)[m].sum()), "water_pct": round(100 * float(wet[(wl == l) & m].mean()), 1),
                                        "median_surface": float(np.median(surf[(wl == l) & m & wet])) if ((wl == l) & m & wet).any() else None}
                               for l in np.unique(wl[m]) if (wl == l)[m].sum() > 50}
                # dry columns the plan floods: where is the ground vs the planned level?
                dry = m & ~wet
                if dry.any():
                    r["dry_ground_minus_level"] = {"median": float(np.median((ground - wl)[dry])),
                                                   "p10": float(np.percentile((ground - wl)[dry], 10)),
                                                   "p90": float(np.percentile((ground - wl)[dry], 90))}
            # Unplanned water on land above sea (lakes RWG/BoP added, or water spilling from raised pools)
            land = have & (ph > 63) & (wl == 0)
            r["unplanned_water_on_land_pct"] = round(100 * float(wet[land].mean()), 2) if land.any() else None
            r["sea_level_water_cols"] = int((have & wet & (top + 1 == 62)).sum())
            r["ground_minus_plan_median"] = float(np.median((ground - ph)[have]))
            np.savez_compressed(os.path.join(out, f"{name}.npz"), tb=tb, top=top, ground=ground, wl=wl, ph=ph, have=have)
            res[name] = r
            print(name, json.dumps(r), flush=True)
    json.dump(res, open(os.path.join(out, "water.json"), "w"), indent=1)

if __name__ == "__main__":
    main()
