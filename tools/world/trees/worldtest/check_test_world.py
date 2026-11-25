"""Check and render the WorldPainter tree-test world built by build_test_world.py.

  py -3.10 check_test_world.py [--test C:\\qf-world\\trees\\test] [--json report.json] [--only PLOT]

For every grid point of every plot it finds which schematic WorldPainter placed there, and in
which of the 8 rotations/mirrorings, by matching the exported blocks against each schematic hung
from its WEOffset point at (grid x, ground + 1, grid z). A tree that matches at zero shift stands
centred on its trunk at the right height; otherwise the best shift (dy, dz, dx) is reported, so a
floating (dy > 0), buried (dy < 0) or off-centre placement shows up. Schematics without WEOffset
tags (downloaded packs) are hung from their bottom-centre block instead. It also checks log axis
bits after rotation, lists every block ID above the ground, and writes <test>/<plot>-top.png,
<plot>-oblique.png and sheet.png.
"""
import argparse, gzip, io, json, os, struct, sys, zlib
import numpy as np
import nbtlib
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from schematic import read_schematic          # noqa: E402
from render import LUT as _LUT                # noqa: E402

LUT = _LUT.copy()          # plus the ground cover WorldPainter adds and the blocks the packs use
for bid, c in {31: (88, 140, 52), 175: (96, 150, 60), 37: (220, 210, 40), 38: (200, 50, 40), 5: (160, 130, 80),
               99: (200, 180, 150), 100: (200, 180, 150), 77: (120, 120, 120), 155: (235, 230, 222),
               160: (200, 220, 230), 88: (84, 64, 52), 82: (160, 166, 178), 85: (150, 120, 75), 43: (165, 165, 165),
               44: (165, 165, 165), 45: (150, 97, 83), 126: (160, 130, 80), 7: (50, 50, 50), 6: (80, 140, 40),
               42: (220, 220, 220), 54: (150, 110, 50), 106: (50, 100, 30)}.items():
    LUT[bid, :] = c

LOGS = (17, 162)
SHIFTS = [(dy, dz, dx) for dy in range(-3, 4) for dz in range(-3, 4) for dx in range(-3, 4)]


def u8(tag):
    return np.frombuffer(np.asarray(tag, dtype=np.int8).tobytes(), np.uint8)


def load_box(region_dir, x0, z0, x1, z1, y0=0, y1=256):
    """Blocks and data for [x0,x1) x [z0,z1) x [y0,y1), as (y, z, x) arrays."""
    ids = np.zeros((y1 - y0, z1 - z0, x1 - x0), np.uint16)
    dat = np.zeros(ids.shape, np.uint8)
    for rx in range(x0 >> 9, ((x1 - 1) >> 9) + 1):
        for rz in range(z0 >> 9, ((z1 - 1) >> 9) + 1):
            p = os.path.join(region_dir, f'r.{rx}.{rz}.mca')
            if not os.path.exists(p):
                continue
            raw = open(p, 'rb').read()
            for i in range(1024):
                off = struct.unpack('>I', raw[i * 4:i * 4 + 4])[0]
                if not off:
                    continue
                bx, bz = (rx * 32 + (i & 31)) * 16, (rz * 32 + (i >> 5)) * 16
                if bx + 16 <= x0 or bx >= x1 or bz + 16 <= z0 or bz >= z1:
                    continue
                o = (off >> 8) * 4096
                n, comp = struct.unpack('>IB', raw[o:o + 5])
                body = raw[o + 5:o + 4 + n]
                body = zlib.decompress(body) if comp == 2 else gzip.decompress(body)
                lvl = nbtlib.File.parse(io.BytesIO(body))['Level']
                for s in lvl.get('Sections', []):
                    sy = int(s['Y']) * 16
                    if sy + 16 <= y0 or sy >= y1:
                        continue
                    b = u8(s['Blocks']).astype(np.uint16)
                    if 'Add' in s:
                        a = u8(s['Add']); hi = np.empty(4096, np.uint16)
                        hi[0::2] = a & 15; hi[1::2] = a >> 4
                        b |= hi << 8
                    d = u8(s['Data']); dd = np.empty(4096, np.uint8)
                    dd[0::2] = d & 15; dd[1::2] = d >> 4
                    b = b.reshape(16, 16, 16); dd = dd.reshape(16, 16, 16)
                    ya, yb = max(sy, y0), min(sy + 16, y1)
                    za, zb = max(bz, z0), min(bz + 16, z1)
                    xa, xb = max(bx, x0), min(bx + 16, x1)
                    sl = (slice(ya - sy, yb - sy), slice(za - bz, zb - bz), slice(xa - bx, xb - bx))
                    dst = (slice(ya - y0, yb - y0), slice(za - z0, zb - z0), slice(xa - x0, xb - x0))
                    ids[dst] = b[sl]; dat[dst] = dd[sl]
    return ids, dat


def transforms(ids, dat, origin):
    """The 8 horizontal rotations/mirrorings of a schematic about its origin column.
    Yields (name, ids, data, origin); log axis bits are swapped on quarter turns."""
    oy, oz, ox = origin
    for mirror in (False, True):
        a, d, z, x = ids, dat, oz, ox
        if mirror:
            a, d, x = a[:, :, ::-1], d[:, :, ::-1], a.shape[2] - 1 - x
        for q in range(4):
            yield f'{"m" if mirror else ""}r{q * 90}', np.ascontiguousarray(a), np.ascontiguousarray(d), (oy, z, x)
            a = np.rot90(a, 1, axes=(1, 2)); d = np.rot90(d, 1, axes=(1, 2)).copy()
            z, x = a.shape[1] - 1 - x, z
            lg = np.isin(a, LOGS)
            ax = d & 12
            ew, ns = lg & (ax == 4), lg & (ax == 8)
            d[ew] = (d[ew] & 3) | 8
            d[ns] = (d[ns] & 3) | 4


def match(world, wdat, ground, gx, gz, cand, shift=(0, 0, 0)):
    """Fraction of the candidate's blocks found in the world (by ID), and log-axis agreement."""
    a, d, (oy, oz, ox) = cand
    dy, dz, dx = shift
    y0, z0, x0 = ground + 1 - oy + dy, gz - oz + dz, gx - ox + dx
    H, L, W = a.shape
    if y0 < 0 or z0 < 0 or x0 < 0 or y0 + H > world.shape[0] or z0 + L > world.shape[1] or x0 + W > world.shape[2]:
        return 0.0, 0.0
    w = world[y0:y0 + H, z0:z0 + L, x0:x0 + W]
    m = a != 0
    hit = (w == a) & m
    f = hit.sum() / max(m.sum(), 1)
    lg = hit & np.isin(a, LOGS)
    wd = wdat[y0:y0 + H, z0:z0 + L, x0:x0 + W]
    axis_ok = ((wd & 12) == (d & 12))[lg].mean() if lg.any() else 1.0
    return float(f), float(axis_ok)


def oblique(ids, dat, ground, scale=3):
    """Dimetric view from the south-east and above. ids are (y, z, x)."""
    Y, L, W = ids.shape
    solid = ids != 0
    air = ~solid
    expo = np.zeros_like(solid)
    expo[:-1] |= air[1:]; expo[:, :-1] |= air[:, 1:]; expo[:, :, :-1] |= air[:, :, 1:]
    expo[-1] = True; expo[:, -1] = True; expo[:, :, -1] = True
    v = solid & expo
    v[:ground] = False
    y, z, x = np.nonzero(v)
    col = LUT[ids[y, z, x], dat[y, z, x] & 15].copy()
    top_open = np.ones_like(solid); top_open[:-1] = air[1:]
    east_open = np.ones_like(solid); east_open[:, :, :-1] = air[:, :, 1:]
    shade = np.where(top_open[y, z, x], 1.0, np.where(east_open[y, z, x], 0.8, 0.64))
    cs = np.cumsum(solid[::-1], 0)[::-1]
    occ = np.clip(cs[y, z, x] - 1, 0, 12)
    col *= (shade * (1 - 0.03 * occ))[:, None]
    s = scale
    u = (x - z + L) * s
    vv = ((x + z) * 0.5 - (y - ground) * 1.2) * s
    vv = (vv - vv.min()).astype(int)
    order = np.argsort(x + z + 0.83 * y, kind='stable')
    u, vv, col = u[order], vv[order], col[order]
    img = np.zeros((int(vv.max()) + 3 * s, (W + L) * s + 2 * s, 3), np.float32)
    img[:] = (24, 28, 36)
    for du in range(2 * s):
        for dv in range(int(2.2 * s)):
            img[vv + dv, u + du] = col
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))


def topdown(ids, dat):
    Y, L, W = ids.shape
    solid = ids != 0
    top = Y - 1 - np.argmax(solid[::-1], 0)
    zz, xx = np.mgrid[0:L, 0:W]
    col = LUT[ids[top, zz, xx], dat[top, zz, xx] & 15]
    gz, gx = np.gradient(top.astype(np.float32))
    hs = np.clip(1 + 0.08 * (-gx - gz), 0.6, 1.3)
    hgt = 0.7 + 0.3 * (top - top.min()) / max(np.ptp(top), 1)
    return Image.fromarray(np.clip(col * (hs * hgt)[..., None], 0, 255).astype(np.uint8))


def load_candidates(files):
    cands = []
    for f in files:
        si, sd = read_schematic(f)
        tag = nbtlib.load(f)
        if 'WEOffsetX' in tag:
            origin, tagged = (-int(tag['WEOffsetY']), -int(tag['WEOffsetZ']), -int(tag['WEOffsetX'])), True
        else:
            origin, tagged = (0, si.shape[1] // 2, si.shape[2] // 2), False
        for name, ti, td, to in transforms(si.astype(np.uint16), sd.astype(np.uint8), origin):
            cands.append(dict(file=os.path.basename(f), tf=name, a=ti, d=td, o=to, tagged=tagged))
    return cands


def check_plot(p, ids, dat, G, x0, z0):
    cands = load_candidates(p['files'])
    gpts = [(gx, gz) for gz in range(p['rect'][1], p['rect'][3]) for gx in range(p['rect'][0], p['rect'][2])
            if gx % p['grid'] == 0 and gz % p['grid'] == 0]
    rows = []
    for gx, gz in gpts:
        lx, lz = gx - x0, gz - z0
        scored = sorted(((match(ids, dat, G, lx, lz, (c['a'], c['d'], c['o'])), c) for c in cands),
                        key=lambda t: -t[0][0])
        (f, ax), c = scored[0]
        shift = (0, 0, 0)
        if f < 0.97:               # floating, buried or off-centre? try small shifts on the best few
            for (_, _), cc in scored[:6]:
                for sh in SHIFTS:
                    ff, aa = match(ids, dat, G, lx, lz, (cc['a'], cc['d'], cc['o']), sh)
                    if ff > f:
                        f, ax, c, shift = ff, aa, cc, sh
        rows.append(dict(x=gx, z=gz, match=round(f, 3), axis_ok=round(ax, 3), schematic=c['file'],
                         transform=c['tf'], shift=list(shift), tagged=c['tagged'],
                         base=int(ids[G + 1, lz, lx]), under=int(ids[G, lz, lx])))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--test', default=r'C:\qf-world\trees\test')
    ap.add_argument('--json')
    ap.add_argument('--only')
    a = ap.parse_args()
    plan = json.load(open(os.path.join(a.test, 'plan', 'plan.json')))
    region = os.path.join(a.test, 'world', plan['name'], 'region')
    G = plan['ground']
    report, tiles = {}, []
    for p in plan['plots']:
        if a.only and p['name'] != a.only:
            continue
        x0, z0, x1, z1 = p['plot']
        ids, dat = load_box(region, x0, z0, x1, z1, 0, 200)
        rows = check_plot(p, ids, dat, G, x0, z0)
        above = ids[G + 1:]
        u, n = np.unique(above[above != 0], return_counts=True)
        blocks = {int(k): int(v) for k, v in zip(u, n)}
        exact = [r for r in rows if r['match'] >= 0.97 and r['shift'] == [0, 0, 0]]
        tfs = sorted({r['transform'] for r in rows})
        report[p['name']] = dict(points=len(rows), exact=len(exact), blocks=blocks, transforms=tfs,
                                 schematics=len({r['schematic'] for r in rows}), rows=rows)
        print(f"{p['name']:11s} grid points {len(rows):3d}  trunk-centred exact fits {len(exact):3d}  "
              f"mean match {np.mean([r['match'] for r in rows]):.3f}  "
              f"log axis ok {np.mean([r['axis_ok'] for r in rows]):.3f}  "
              f"{report[p['name']]['schematics']} distinct objects  transforms {tfs}")
        for r in rows:
            if r not in exact:
                print('    not exact:', r)
        print('    block IDs above ground:', blocks)
        t = topdown(ids, dat); t.save(os.path.join(a.test, f"{p['name']}-top.png"))
        o = oblique(ids, dat, G); o.save(os.path.join(a.test, f"{p['name']}-oblique.png"))
        tiles.append((p['name'], t, o))
    if a.json:
        json.dump(report, open(a.json, 'w'), indent=1)
    if tiles and not a.only:
        cw, cols = 640, 2
        tiles = [(n, t.resize((cw // 2, cw // 2), Image.NEAREST), o.resize((cw, int(o.height * cw / o.width))))
                 for n, t, o in tiles]
        th = max(max(t.height, o.height) for _, t, o in tiles) + 24
        tw = cw + cw // 2 + 30
        sheet = Image.new('RGB', (cols * tw, th * ((len(tiles) + cols - 1) // cols)), (14, 16, 22))
        dr = ImageDraw.Draw(sheet)
        for k, (n, t, o) in enumerate(tiles):
            X, Y = (k % cols) * tw + 10, (k // cols) * th
            dr.text((X, Y + 4), n, fill=(240, 220, 160))
            sheet.paste(t, (X, Y + 20)); sheet.paste(o, (X + cw // 2 + 10, Y + 20))
        sheet.save(os.path.join(a.test, 'sheet.png'))
        print('sheet ->', os.path.join(a.test, 'sheet.png'))


if __name__ == '__main__':
    main()
