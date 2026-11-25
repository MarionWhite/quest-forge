"""Clean the downloaded tree packs into WorldPainter-ready copies.

    py -3.10 -I tools/world/trees/clean_packs.py [--root C:/qf-world/trees] [--only PACK ...]

Reads the packs under <root> (the `-1.7.10` remapped copies where they exist) and writes cleaned
copies to <root>/cleaned/<pack>/<same relative path>, plus <root>/cleaned/report.tsv. The packs are
untrusted downloads: this only parses their NBT, never runs anything from them, and never writes
into them.

Per schematic:
- strips bedrock (7) and the 1.8+ technical blocks that may survive as raw IDs (166 barrier,
  217 structure void, 255 structure block) wherever they are;
- finds the trunk: vertical log columns (17/162, axis bits 0 or 12) at least half as tall as the
  tallest column, grouped into 8-connected clusters in plan; the cluster that reaches lowest is the
  trunk, ties going to the one with more logs. Without logs, huge-mushroom stems (99/100 meta 10/15)
  stand in; without either, the lowest remaining layer is the base and its centroid the centre;
- tall grass, flowers or saplings in the lower 40 % of the object mark the surface the author built
  on, so their lowest layer becomes the base (H2CO3 models its ground this way; its logs are all
  six-sided bark, so roots and trunk look alike);
- otherwise a ground plate (grass, dirt, stone, sand, gravel, clay, mycelium, soul sand, farmland, cobble)
  round the trunk foot at or above the lowest trunk log raises the base to the layer above the plate;
- deletes those ground blocks below the base. Logs below the base are kept: they are roots and go
  into the ground;
- crops empty borders (only when the file has no entities or tile entities, whose coordinates would
  otherwise shift);
- writes WEOffsetX/Y/Z so WorldPainter puts the trunk-base centre at terrain height + 1, and fixes the
  misspelt `Materials "Aplha"` in one Jamziboy file.
Rock folders are skipped: they have no trunk and their stone is the object.
"""
import argparse
import os
import sys
from collections import Counter

import nbtlib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from schematic import read_schematic   # noqa: E402

# pack folder -> source sub-folder (the 1.7.10 copy where the pack has one)
PACKS = {
    'h2co3-1k-treepack': 'trees-1.7.10',
    'h2co3-1k-trees-3k-bushes': 'objects-1.7.10',
    'jamziboy-conquered-trees-rocks': 'Treerepository',
    'murokmakto-vol1-boreal': '',
    'mythix13-tree-repository': '',
    'plutouthere-god-tree-pack': 'schematic-1.7.10',
    'sijmenvb-worldpainter-trees': 'schematic-1.7.10',
}
SKIP_DIRS = {'rocks', 'rockrepository'}
STRIP = np.array([7, 166, 217, 255])
GROUND = np.array([1, 2, 3, 4, 12, 13, 24, 60, 82, 88, 110])
LOGS = np.array([17, 162])
PLANTS = np.array([6, 31, 32, 37, 38, 39, 40, 175])   # saplings, grass, fern, dead bush, flowers, tall plants


def clusters(mask):
    """8-connected components of a 2D bool mask -> list of [(z, x), ...]."""
    seen = np.zeros_like(mask)
    out = []
    for z0, x0 in zip(*np.nonzero(mask)):
        if seen[z0, x0]:
            continue
        stack, comp = [(z0, x0)], []
        seen[z0, x0] = True
        while stack:
            z, x = stack.pop()
            comp.append((z, x))
            for dz in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    zz, xx = z + dz, x + dx
                    if 0 <= zz < mask.shape[0] and 0 <= xx < mask.shape[1] and mask[zz, xx] and not seen[zz, xx]:
                        seen[zz, xx] = True
                        stack.append((zz, xx))
        out.append(comp)
    return out


def find_trunk(b, d):
    """-> (base_y, cz, cx, how) or None. b, d are (y, z, x)."""
    stem = np.isin(b, LOGS) & (((d & 12) == 0) | ((d & 12) == 12))
    how = 'log'
    if not stem.any():
        stem = np.isin(b, [99, 100]) & np.isin(d & 15, [10, 15])
        how = 'mushroom-stem'
    if not stem.any():
        return None
    cols = stem.sum(0)
    tall = cols >= max(1, 0.5 * cols.max())
    best = None
    for comp in clusters(tall):
        zz = np.array([c[0] for c in comp]); xx = np.array([c[1] for c in comp])
        colmask = np.zeros_like(tall); colmask[zz, xx] = True
        ys = np.nonzero((stem & colmask[None]).any((1, 2)))[0]
        key = (ys[0], -cols[zz, xx].sum())
        if best is None or key < best[0]:
            best = (key, colmask)
    _, colmask = best
    base = best[0][0]
    foot = (stem[base:base + 3] & colmask[None]).sum(0)      # the lowest three trunk layers
    fz, fx = np.nonzero(foot)
    w = foot[fz, fx]
    fz, fx = np.average(fz, weights=w), np.average(fx, weights=w)
    return base, int(round(fz.mean() - 1e-6)), int(round(fx.mean() - 1e-6)), how, colmask


def clean(b, d):
    """Returns (b, d, base_y, cz, cx, how, stripped Counter)."""
    b = b.copy(); d = d.copy()
    stripped = Counter()
    m = np.isin(b, STRIP)
    for i, n in zip(*np.unique(b[m], return_counts=True)):
        stripped[int(i)] += int(n)
    b[m] = 0; d[m] = 0
    t = find_trunk(b, d)
    ground = np.isin(b, GROUND)
    if t:
        base, cz, cx, how, colmask = t
        # a ground plate round the trunk foot (footprint grown by 2) at or above the lowest log
        near = colmask.copy()
        for _ in range(2):
            g = near.copy()
            g[1:] |= near[:-1]; g[:-1] |= near[1:]; g[:, 1:] |= near[:, :-1]; g[:, :-1] |= near[:, 1:]
            near = g
        plate = np.nonzero((ground & near[None]).any((1, 2)))[0]
        plate = set(int(y) for y in plate if base <= y < base + 4)
        while base in plate:                     # contiguous upward from the lowest log
            base += 1
    else:
        how = 'layer'
        ys = np.nonzero((b != 0).any((1, 2)))[0]
        if not len(ys):
            return b, d, 0, 0, 0, 'empty', stripped
        base = ys[0]
        # bottom layers made only of ground blocks are a base plate
        while base < ys[-1] and not ((b[base] != 0) & ~ground[base]).any():
            base += 1
        cz, cx = (int(round(v.mean())) for v in np.nonzero(b[base] != 0))
    # Ground cover the author placed round the foot marks the surface: those plants stand at
    # terrain + 1, so their lowest layer is the base, whatever the logs below it do (roots).
    pl = np.nonzero(np.isin(b, PLANTS).any((1, 2)))[0]
    if len(pl) and pl[0] <= 0.4 * (b.shape[0] - 1):
        base = int(pl[0])
        how += '+plants'
    low = ground.copy(); low[base:] = False
    for i, n in zip(*np.unique(b[low], return_counts=True)):
        stripped[int(i)] += int(n)
    b[low] = 0; d[low] = 0
    return b, d, base, cz, cx, how, stripped


def write(src_nbt, b, d, offset, path):
    H, L, W = b.shape
    root = src_nbt
    root['Width'], root['Height'], root['Length'] = nbtlib.Short(W), nbtlib.Short(H), nbtlib.Short(L)
    root['Materials'] = nbtlib.String('Alpha')
    root['Blocks'] = nbtlib.ByteArray((b & 0xFF).astype(np.uint8).ravel().view(np.int8))
    root['Data'] = nbtlib.ByteArray((d & 0xF).astype(np.uint8).ravel().view(np.int8))
    hi = (b >> 8).astype(np.uint8).ravel()
    if 'AddBlocks' in root:
        del root['AddBlocks']
    if hi.any():
        if len(hi) % 2:
            hi = np.append(hi, 0)
        root['AddBlocks'] = nbtlib.ByteArray(((hi[0::2] << 4) | hi[1::2]).astype(np.uint8).view(np.int8))
    for k, v in zip(('WEOffsetX', 'WEOffsetY', 'WEOffsetZ'), offset):
        root[k] = nbtlib.Int(v)
    for k in ('WEOriginX', 'WEOriginY', 'WEOriginZ'):
        root.setdefault(k, nbtlib.Int(0))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    nbtlib.File(root, root_name='Schematic', gzipped=True).save(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root', default=r'C:\qf-world\trees')
    ap.add_argument('--only', nargs='*')
    a = ap.parse_args()
    out_root = os.path.join(a.root, 'cleaned')
    rows = []
    for pack, sub in PACKS.items():
        if a.only and pack not in a.only:
            continue
        src = os.path.join(a.root, pack, sub)
        files = []
        for dp, dn, fn in os.walk(src):
            dn[:] = [x for x in dn if x.lower() not in SKIP_DIRS]
            files += [os.path.join(dp, f) for f in fn if f.lower().endswith('.schematic')]
        tot = Counter()
        for f in sorted(files):
            rel = os.path.relpath(f, src)
            try:
                s = nbtlib.load(f)
                b, d = read_schematic(f)
            except Exception as e:          # noqa: BLE001 - a broken download is reported, not fatal
                rows.append((pack, rel, 'unreadable', str(e).replace('\t', ' '), '', '', ''))
                tot['unreadable'] += 1
                continue
            old = tuple(int(s[k]) for k in ('WEOffsetX', 'WEOffsetY', 'WEOffsetZ')) if 'WEOffsetX' in s else None
            nb, nd, base, cz, cx, how, stripped = clean(b, d)
            solid = nb != 0
            y0 = z0 = x0 = 0
            if solid.any() and not len(s.get('Entities', [])) and not len(s.get('TileEntities', [])):
                ys, zs, xs = (np.nonzero(solid.any(ax))[0] for ax in ((1, 2), (0, 2), (0, 1)))
                y0, z0, x0 = ys[0], zs[0], xs[0]
                nb = nb[y0:ys[-1] + 1, z0:zs[-1] + 1, x0:xs[-1] + 1]
                nd = nd[y0:ys[-1] + 1, z0:zs[-1] + 1, x0:xs[-1] + 1]
            offset = (-(cx - x0), -(base - y0), -(cz - z0))
            write(s, nb, nd, offset, os.path.join(out_root, pack, rel))
            n_str = sum(stripped.values())
            tot['files'] += 1
            tot['stripped'] += bool(n_str)
            tot['offset-new'] += old is None
            tot['offset-changed'] += old is not None and old != offset
            tot['trunk-' + how] += 1
            tot.update({f'id{k}': v for k, v in stripped.items()})
            rows.append((pack, rel, how, ' '.join(f'{k}x{v}' for k, v in sorted(stripped.items())),
                         ','.join(map(str, offset)), ','.join(map(str, old)) if old else '', f'{nb.shape[2]}x{nb.shape[1]}h{nb.shape[0]}'))
        print(pack, dict(tot))
    with open(os.path.join(out_root, 'report.tsv'), 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('pack\tfile\ttrunk\tstripped (id x count)\tWEOffset\told WEOffset\tsize\n')
        for r in rows:
            fh.write('\t'.join(r) + '\n')


if __name__ == '__main__':
    main()
