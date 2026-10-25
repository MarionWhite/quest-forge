"""Pinned block IDs: the full pack's FML registry, as a table and as level.dat data.

In 1.7.10 FML gives modded blocks their numeric IDs per world and saves the map in level.dat
(FML -> ItemData). A schematic that uses Biomes O' Plenty blocks by number is only right in a world
that carries the same map. The canonical map is the full-pack test server C:\\qfs\\v0 (whole pack,
BoP 2.1.0.2308, RWG alpha-1.5.2, Forge 10.13.4.1614); `world` and `world-rwg` there hold identical
registries. Read it, never write it.

    py -3.10 tools/world/blockids.py extract [C:/qfs/v0/world/level.dat] [--tsv docs/survey/block-ids.tsv]
    py -3.10 tools/world/blockids.py inject SRC_LEVEL_DAT DST_LEVEL_DAT     # copy the registry into a world
    py -3.10 tools/world/blockids.py check LEVEL_DAT                         # compare a world with the TSV

`inject` copies the whole FML compound (ItemData, ModList, the alias/substitution lists,
BlockedItemIds) and the Forge compound (DefaultFluidList, DimensionData). That is what the pack
writes itself, so on first load FML adopts these IDs instead of handing out fresh ones.
tools/world/stitch.py --registry calls inject_registry() on the stitched world.
"""
import argparse
import os
import sys

import nbtlib

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_SRC = r'C:\qfs\v0\world\level.dat'
DEFAULT_TSV = os.path.join(REPO, 'docs', 'survey', 'block-ids.tsv')


def registry(level_dat):
    """{name: id} for blocks only (FML prefixes block keys with \\x01, items with \\x02)."""
    lvl = nbtlib.load(level_dat)
    return {str(e['K'])[1:]: int(e['V']) for e in lvl['FML']['ItemData'] if str(e['K']).startswith('\x01')}


def load_tsv(path=DEFAULT_TSV):
    out = {}
    with open(path, encoding='utf-8') as f:
        for line in f:
            if line.startswith('#') or line.startswith('name\t') or not line.strip():
                continue
            name, bid = line.rstrip('\n').split('\t')[:2]
            out[name] = int(bid)
    return out


def write_tsv(level_dat, path):
    lvl = nbtlib.load(level_dat)
    reg = registry(level_dat)
    mods = {str(m['ModId']): str(m['ModVersion']) for m in lvl['FML']['ModList']}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(f'# FML block registry of {level_dat} ({len(reg)} blocks, {len(mods)} mods; '
                f'Forge {mods.get("Forge")}, BiomesOPlenty {mods.get("BiomesOPlenty")}, RWG {mods.get("RWG")}).\n')
        f.write('# Written by tools/world/blockids.py extract. Inject with stitch.py --registry.\n')
        f.write('name\tid\n')
        for name, bid in sorted(reg.items(), key=lambda kv: (kv[1], kv[0])):
            f.write(f'{name}\t{bid}\n')
    return reg


def inject_registry(dst_lvl, src_path):
    """Copy FML and Forge compounds from src level.dat into the loaded nbtlib File dst_lvl."""
    src = nbtlib.load(src_path)
    if 'FML' not in src or 'ItemData' not in src['FML']:
        raise SystemExit(f'{src_path} has no FML ItemData')
    dst_lvl['FML'] = src['FML']
    if 'Forge' in src:
        dst_lvl['Forge'] = src['Forge']
    return sum(1 for e in src['FML']['ItemData'] if str(e['K']).startswith('\x01'))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    e = sub.add_parser('extract'); e.add_argument('src', nargs='?', default=DEFAULT_SRC)
    e.add_argument('--tsv', default=DEFAULT_TSV)
    i = sub.add_parser('inject'); i.add_argument('src'); i.add_argument('dst')
    c = sub.add_parser('check'); c.add_argument('level_dat'); c.add_argument('--tsv', default=DEFAULT_TSV)
    a = ap.parse_args()
    if a.cmd == 'extract':
        reg = write_tsv(a.src, a.tsv)
        bop = sum(1 for k in reg if k.startswith('BiomesOPlenty:'))
        print(f'{len(reg)} blocks ({bop} BiomesOPlenty) -> {a.tsv}')
    elif a.cmd == 'inject':
        if os.path.normcase(os.path.abspath(a.dst)).startswith(os.path.normcase(r'C:\qfs')):
            sys.exit('refusing to write into C:\\qfs')
        lvl = nbtlib.load(a.dst)
        n = inject_registry(lvl, a.src)
        lvl.save()
        print(f'{n} block IDs from {a.src} -> {a.dst}')
    else:
        want, have = load_tsv(a.tsv), registry(a.level_dat)
        diff = [(k, v, have.get(k)) for k, v in want.items() if have.get(k) != v]
        print(f'{len(want) - len(diff)}/{len(want)} match' + ''.join(f'\n  {k}: tsv {v}, world {h}' for k, v, h in diff[:40]))
        sys.exit(1 if diff else 0)


if __name__ == '__main__':
    main()
