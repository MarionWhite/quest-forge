"""Preview renders: side elevation + top-down plan per tree, and a contact sheet per species.

Simple block colours with depth, sky-occlusion and per-block shading so leaves read as leaves
and trunks read as round. Stained glass is drawn translucent over whatever is behind it.
"""
import numpy as np
from PIL import Image, ImageDraw

BG = np.array((22, 26, 34), np.float32)
WOOL = [(233, 236, 236), (240, 118, 19), (189, 68, 179), (58, 175, 217), (248, 198, 39), (112, 185, 25),
        (237, 141, 172), (62, 68, 71), (142, 142, 134), (21, 137, 145), (121, 42, 172), (53, 57, 157),
        (114, 71, 40), (84, 109, 27), (161, 39, 34), (20, 21, 25)]
CLAY = [(210, 178, 161), (162, 84, 38), (150, 88, 109), (113, 109, 138), (186, 133, 35), (104, 118, 53),
        (162, 78, 79), (58, 42, 36), (135, 107, 98), (87, 92, 92), (118, 70, 86), (74, 60, 91),
        (77, 51, 36), (76, 83, 42), (143, 61, 47), (37, 23, 16)]
GLASSC = [(255, 255, 255), (216, 127, 51), (178, 76, 216), (102, 153, 216), (229, 229, 51), (127, 204, 25),
          (242, 127, 165), (76, 76, 76), (153, 153, 153), (76, 127, 153), (127, 63, 178), (51, 76, 178),
          (102, 76, 51), (102, 127, 51), (153, 51, 51), (25, 25, 25)]
# leaves drawn with a typical temperate-biome tint
LEAVES = {(18, 0): (72, 132, 44), (18, 1): (54, 92, 58), (18, 2): (118, 158, 82), (18, 3): (58, 145, 34),
          (161, 0): (96, 132, 40), (161, 1): (52, 98, 32)}
LOGS = {(17, 0): (104, 82, 50), (17, 1): (62, 46, 28), (17, 2): (216, 214, 204), (17, 3): (92, 70, 32),
        (162, 0): (122, 116, 104), (162, 1): (58, 44, 28)}
OTHER = {1: (128, 128, 128), 4: (112, 112, 112), 48: (92, 118, 92), 79: (150, 185, 250), 80: (242, 250, 250),
         89: (250, 215, 120), 174: (168, 196, 245), 20: (210, 230, 240), 2: (95, 160, 60), 3: (134, 96, 67)}
BRICKS = {0: (124, 124, 124), 1: (106, 124, 98), 2: (112, 110, 108), 3: (130, 130, 130)}


def build_lut():
    lut = np.zeros((4096, 16, 3), np.float32)
    lut[:] = (255, 0, 255)
    alpha = np.ones((4096, 16), np.float32)
    for m in range(16):
        lut[35, m] = WOOL[m]; lut[159, m] = CLAY[m]; lut[95, m] = GLASSC[m]; alpha[95, m] = 0.55
        lut[98, m] = BRICKS.get(m & 3, BRICKS[0])
        for (i, t), c in LEAVES.items():
            if (m & 3) == t:
                lut[i, m] = c
        for (i, t), c in LOGS.items():
            if (m & 3) == t:
                lut[i, m] = c
    for i, c in OTHER.items():
        lut[i, :] = c
    alpha[79, :] = 0.8
    return lut, alpha


LUT, ALPHA = build_lut()
LEAFY = np.zeros(4096, bool)
LEAFY[[18, 161, 35, 159, 95]] = True


def _hash(*a):
    h = np.zeros(np.broadcast(*a).shape, np.uint32)
    for k, v in enumerate(a):
        h = h * np.uint32(73856093 + k * 19349663) ^ np.asarray(v).astype(np.uint32)
    h ^= h >> 13
    h *= np.uint32(0x5bd1e995)
    h ^= h >> 15
    return (h & 1023).astype(np.float32) / 1023.0


def _shade_volume(ids, data):
    """Per-voxel colour (H,L,W,3), alpha, and a light factor from sky occlusion + texture noise."""
    H, L, W = ids.shape
    col = LUT[ids, data & 15]
    alp = ALPHA[ids, data & 15]
    solid = ids != 0
    # sky occlusion: solid blocks in the 10 layers above (soft shadow under canopies)
    above = np.zeros((H, L, W), np.float32)
    cs = np.cumsum(solid[::-1], axis=0)[::-1].astype(np.float32)        # count at and above
    k = 10
    shifted = np.zeros_like(cs)
    shifted[:-k] = cs[k:]
    above[:-1] = cs[1:] - shifted[:-1] if H > 1 else 0
    light = 1.0 - 0.055 * np.minimum(above, 9)
    y, z, x = np.indices((H, L, W))
    noise = _hash(x, y, z)
    tex = np.where(LEAFY[ids], 0.82 + 0.3 * noise, 0.9 + 0.16 * noise)
    return col, alp, (light * tex)[..., None], solid


def side_view(ids, data):
    """Front elevation looking along +z. Returns (H, W, 3) uint8."""
    H, L, W = ids.shape
    col, alp, light, solid = _shade_volume(ids, data)
    depth = (1.0 - 0.4 * np.arange(L) / max(L - 1, 1))[None, :, None, None]
    # left-lit rounding: blocks with air to their left are brighter, to their right darker
    left_open = np.ones_like(solid); left_open[:, :, 1:] = ~solid[:, :, :-1]
    right_open = np.ones_like(solid); right_open[:, :, :-1] = ~solid[:, :, 1:]
    edge = (1 + 0.12 * left_open - 0.12 * right_open)[..., None]
    c = col * light * depth * edge                                          # (H,L,W,3)
    return np.clip(_composite(c, alp, solid, axis=1), 0, 255)[::-1].astype(np.uint8)


def _composite(c, alp, solid, axis):
    """Front-to-back alpha compositing along `axis` of (H,L,W,3) colours."""
    c = np.moveaxis(c, axis, 0)
    a = np.moveaxis(alp * solid, axis, 0)[..., None]
    out = np.zeros(c.shape[1:], np.float32)
    trans = np.ones(c.shape[1:3] + (1,), np.float32)
    for k in range(c.shape[0]):
        ak = a[k]
        if not ak.any():
            continue
        out += trans * ak * c[k]
        trans *= (1 - ak)
    out += trans * BG
    return out


def top_view(ids, data):
    """Plan view from above. Returns (L, W, 3) uint8, north up."""
    H, L, W = ids.shape
    col, alp, light, solid = _shade_volume(ids, data)
    hgt = (0.55 + 0.45 * np.arange(H) / max(H - 1, 1))[:, None, None, None]
    c = col * hgt * (0.85 + 0.15 * light)
    # hillshade from the top surface height (light from the north-west)
    top = np.where(solid.any(0), H - 1 - np.argmax(solid[::-1], axis=0), 0).astype(np.float32)
    if min(top.shape) >= 2:
        gz, gx = np.gradient(top)
    else:
        gz = gx = np.zeros_like(top)
    hs = np.clip(1.0 + 0.06 * (-gx - gz), 0.7, 1.25)[..., None]
    out = _composite(c[::-1], alp[::-1], solid[::-1], axis=0)
    return np.clip(out * hs, 0, 255).astype(np.uint8)


def contact_sheet(trees, out, title, sheet_w=1800):
    """trees: list of (name, size_class, ids, data). Rows grouped by size class."""
    order = ['small', 'medium', 'large', 'giant']
    groups = [(s, [t for t in trees if t[1] == s]) for s in order]
    groups = [g for g in groups if g[1]]
    rows = []                                   # (label, [(name, side_img, top_img)], scale)
    for size, ts in groups:
        maxh = max(t[2].shape[0] for t in ts)
        scale = max(1.0, min(8.0, 320.0 / maxh)) if size != 'small' else max(1.0, min(8.0, 180.0 / maxh))
        cells = []
        for name, _, ids, data in ts:
            cells.append((name, Image.fromarray(side_view(ids, data)), Image.fromarray(top_view(ids, data)), ids.shape))
        rows.append((size, cells, scale))
    # layout: wrap each size class into lines, bottom-aligned on a common ground line
    pad, lab = 10, 14
    lines = []
    for size, cells, s in rows:
        line, x = [], pad
        lines.append(('hdr', size))
        for name, side, top, shp in cells:
            sw, sh = int(side.width * s), int(side.height * s)
            tw, th = int(top.width * s * 0.75), int(top.height * s * 0.75)
            cw = sw + tw + 3 * pad
            if x + cw > sheet_w and line:
                lines.append(('cells', line)); line, x = [], pad
            line.append((x, name, side.resize((sw, sh), Image.NEAREST), top.resize((tw, th), Image.NEAREST), shp))
            x += cw
        if line:
            lines.append(('cells', line))
    total = 30 + sum(18 if k == 'hdr' else max(max(c[2].height, c[3].height) for c in v) + lab + pad
                     for k, v in lines)
    sheet = Image.new('RGB', (sheet_w, total + 8), (14, 16, 22))
    dr = ImageDraw.Draw(sheet)
    dr.text((8, 8), title, fill=(235, 235, 235))
    y = 30
    for kind, v in lines:
        if kind == 'hdr':
            dr.text((6, y + 2), v.upper(), fill=(250, 200, 120)); y += 18
            continue
        rowh = max(max(c[2].height, c[3].height) for c in v)
        for x, name, side, top, shp in v:
            sheet.paste(side, (x, y + rowh - side.height))
            sheet.paste(top, (x + side.width + 6, y + rowh - top.height))
            H, L, W = shp
            dr.text((x, y + rowh + 1), f'{name}  {W}x{L} h{H}', fill=(160, 160, 160))
        y += rowh + lab + pad
    sheet.save(out)
    return out
