#!/usr/bin/env python3
"""Height map + biome map for the decision-0003 proof-of-concept island.

Writes two 8-bit greyscale PNGs, one pixel per block, covering x,z in [-H, H):
  height.png  pixel = terrain height (sea level 62, sea floor ~38)
  biome.png   pixel = biome ID (the pinned IDs in pack/config), ocean = 24 Deep Ocean
and regions.json naming each painted region. wp_build_island.js turns them into a
WorldPainter world and exports it for Minecraft 1.2-1.12 (Anvil) with population on.

    py -3.10 tools/world/make_test_island.py OUTDIR [--half 1280] [--radius 1000]
"""
import argparse, json, os
import numpy as np
from PIL import Image

# ~10 regions: BoP (pinned IDs from pack/config/biomesoplenty/ids.cfg), RWG (pack/config/RWG.cfg),
# one vanilla control. Ominous Woods is one RWG never places itself.
REGIONS = [
    ("BoP Redwood Forest", 196), ("BoP Tundra", 247), ("BoP Boreal Forest", 66),
    ("BoP Mystic Grove", 185), ("BoP Ominous Woods", 187), ("BoP Lavender Fields", 147),
    ("RWG Redwood", 225), ("RWG Snow Forest", 217), ("RWG Hot Desert", 222),
    ("Vanilla Forest", 4),
]
OCEAN = 24


def fbm(n, rng, octaves=5, base=8):
    """Cheap fractal noise: sum of bilinearly upsampled random grids."""
    out = np.zeros((n, n), np.float32)
    amp, cells, total = 1.0, base, 0.0
    for _ in range(octaves):
        g = rng.standard_normal((cells + 1, cells + 1)).astype(np.float32)
        img = Image.fromarray(g, mode="F").resize((n, n), Image.BILINEAR)
        out += amp * np.asarray(img)
        total += amp
        amp *= 0.5
        cells *= 2
    return out / total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--half", type=int, default=1280, help="map covers [-half, half) on both axes")
    ap.add_argument("--radius", type=int, default=1000, help="island radius in blocks")
    ap.add_argument("--seed", type=int, default=3)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    rng = np.random.default_rng(a.seed)
    n = 2 * a.half
    ax = np.arange(n, dtype=np.float32) - a.half
    x, z = np.meshgrid(ax, ax)            # row = z, column = x
    r = np.hypot(x, z)
    coast = a.radius * (1 + 0.12 * fbm(n, rng, 4, 6))   # wobbly coastline
    land = np.clip((coast - r) / 120.0, -1, 1)           # >0 on land, ramps over 120 blocks
    hills = fbm(n, rng, 6, 10)
    h = np.where(land > 0,
                 63 + 6 * land + 18 * np.clip(hills, 0, None) * land,
                 62 + 24 * land)                         # sea floor down to 38
    # one mountain range in the north-west for terrain variety
    ridge = np.exp(-(((x + 350) * 0.6 + (z + 300) * 0.8) ** 2) / (2 * 140 ** 2)) * (r < a.radius * 0.8)
    h = h + ridge * (55 + 25 * fbm(n, rng, 5, 16))
    h = np.clip(h, 5, 250).astype(np.uint8)

    # Voronoi regions from seed points spread inside the island
    k = len(REGIONS)
    ang = np.linspace(0, 2 * np.pi, k, endpoint=False) + 0.3
    rad = np.where(np.arange(k) % 2 == 0, 0.62, 0.3) * a.radius
    seeds = np.stack([rad * np.cos(ang), rad * np.sin(ang)], 1)
    jitter = 60 * fbm(n, rng, 3, 8)                       # ragged borders
    d = np.stack([np.hypot(x - sx + jitter, z - sz - jitter) for sx, sz in seeds])
    idx = d.argmin(0)
    ids = np.array([b for _, b in REGIONS], np.uint8)
    biome = np.where(h > 62, ids[idx], OCEAN).astype(np.uint8)

    Image.fromarray(h, "L").save(os.path.join(a.out, "height.png"))
    Image.fromarray(biome, "L").save(os.path.join(a.out, "biome.png"))
    meta = {"half": a.half, "radius": a.radius, "ocean": OCEAN, "regions": [
        {"name": nm, "id": int(b), "seed_x": float(sx), "seed_z": float(sz),
         "blocks": int(((biome == b)).sum())}
        for (nm, b), (sx, sz) in zip(REGIONS, seeds)]}
    with open(os.path.join(a.out, "regions.json"), "w") as f:
        json.dump(meta, f, indent=1)
    print(f"land {int((h > 62).sum()):,} blocks, {k} regions -> {a.out}")


if __name__ == "__main__":
    main()
