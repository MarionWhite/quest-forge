"""Procedural tree generator for the Quest Forge world -> MCEdit .schematic for WorldPainter.

  py -3.10 treegen.py                         # every species, default counts, vanilla palette
  py -3.10 treegen.py redwood mangrove        # just these species
  py -3.10 treegen.py cherry --sizes medium --count 4 --seed 7
  py -3.10 treegen.py autumn --palette vanilla-leaves --out C:/tmp/trees
  py -3.10 treegen.py redwood --palette bop --idmap C:/qfs/friends/world/level.dat
  py -3.10 treegen.py --list

Writes <out>/<species>/<species>_<size>_<n>.schematic and <out>/<species>-preview.png
(side elevation + plan view of every tree). Same seed -> same trees.
"""
import argparse
import importlib
import os
import sys
import time
import zlib

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from palettes import PALETTES, load_idmap          # noqa: E402
from schematic import to_blocks, write_schematic   # noqa: E402
from render import contact_sheet                   # noqa: E402

SPECIES = ['redwood', 'mangrove', 'baobab', 'ice', 'eucalyptus', 'petrified', 'autumn', 'cherry']
SIZES = ['small', 'medium', 'large', 'giant']
DEFAULT_OUT = r'C:\qf-world\trees\generated'


def module(name):
    return importlib.import_module(f'species.{name}')


def tree_seed(master, species, size, n):
    return zlib.crc32(f'{master}:{species}:{size}:{n}'.encode())


def generate(species, out, master=1, palette='vanilla', idmap=None, sizes=None, count=None, preview=True,
             log=print):
    mod = module(species)
    pal = PALETTES[palette][species]
    d = os.path.join(out, species)
    os.makedirs(d, exist_ok=True)
    trees = []
    for size in SIZES:
        if sizes and size not in sizes:
            continue
        n_size = count if count is not None else mod.COUNTS.get(size, 0)
        for n in range(1, n_size + 1):
            seed = tree_seed(master, species, size, n)
            rng = np.random.default_rng(seed)
            t0 = time.time()
            g, info = mod.grow(rng, size)
            role, axis, origin = g.cropped()
            ids, data = to_blocks(role, axis, pal, np.random.default_rng(seed + 1), idmap)
            name = f'{species}_{size}_{n:02d}'
            write_schematic(os.path.join(d, name + '.schematic'), ids, data, origin)
            H, L, W = ids.shape
            log(f'  {name:24s} {W:3d}x{L:3d} h{H:3d}  {time.time() - t0:5.1f}s  {info}')
            trees.append((name.replace(species + '_', ''), size, ids, data))
    if preview and trees:
        p = os.path.join(out, f'{species}-preview.png')
        contact_sheet(trees, p, f'{species}  ({len(trees)} trees, palette {palette}, seed {master})  '
                                f'- side elevation + plan view per tree, rows by size class')
        log(f'  preview -> {p}')
    return len(trees)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('species', nargs='*', help=f'any of {", ".join(SPECIES)} (default: all)')
    ap.add_argument('--out', default=DEFAULT_OUT)
    ap.add_argument('--seed', type=int, default=1, help='master seed (default 1)')
    ap.add_argument('--palette', default='vanilla', choices=sorted(PALETTES))
    ap.add_argument('--idmap', help='level.dat whose FML registry resolves modded block names')
    ap.add_argument('--sizes', help='comma list of size classes to generate')
    ap.add_argument('--count', type=int, help='trees per size class (overrides the species default)')
    ap.add_argument('--no-preview', action='store_true')
    ap.add_argument('--list', action='store_true', help='list species and default counts')
    a = ap.parse_args()
    if a.list:
        for s in SPECIES:
            m = module(s)
            print(f'{s:11s} {sum(m.COUNTS.values()):3d}  {m.COUNTS}')
        return
    idmap = load_idmap(a.idmap) if a.idmap else None
    sizes = a.sizes.split(',') if a.sizes else None
    total = 0
    for s in (a.species or SPECIES):
        if s not in SPECIES:
            sys.exit(f'unknown species {s!r}; choose from {SPECIES}')
        print(s)
        total += generate(s, a.out, a.seed, a.palette, idmap, sizes, a.count, not a.no_preview)
    print(f'{total} trees written under {a.out}')


if __name__ == '__main__':
    main()
