"""Role grid -> blocks (via a palette) -> MCEdit .schematic (gzip NBT, Materials "Alpha")."""
import numpy as np
import nbtlib
from voxel import ROLES
from palettes import LOG_BLOCKS

AXIS_BITS = np.array([0, 4, 8, 12], np.int16)
FALLBACK = {'leaf2': 'leaf', 'leaf3': 'leaf', 'leaf4': 'leaf', 'accent2': 'accent', 'accent3': 'accent',
            'branch': 'trunk', 'root': 'trunk', 'bark': 'trunk', 'core': 'trunk', 'snow': 'leaf',
            'glow': 'accent', 'accent': 'leaf'}


def _entries(pal, role_name):
    n = role_name
    while n not in pal:
        if n not in FALLBACK:
            raise KeyError(f'palette has no block for role {role_name!r}')
        n = FALLBACK[n]
    return pal[n]


def _patch_noise(shape, rng, cell=3):
    """Low-frequency noise so mixed blocks clump into patches instead of salt-and-pepper."""
    lo = rng.random(tuple(s // cell + 2 for s in shape))
    up = lo.repeat(cell, 0).repeat(cell, 1).repeat(cell, 2)[:shape[0], :shape[1], :shape[2]]
    return 0.65 * up + 0.35 * rng.random(shape)


def to_blocks(role, axis, pal, rng, idmap=None):
    ids = np.zeros(role.shape, np.int16)
    data = np.zeros(role.shape, np.int16)
    noise = _patch_noise(role.shape, rng)
    for r in np.unique(role):
        if r == 0:
            continue
        ents = _entries(pal, ROLES[r])
        m = role == r
        idx = np.flatnonzero(m)
        order = np.argsort(noise.ravel()[idx])
        wts = np.array([e[2] for e in ents], float)
        cuts = np.round(np.cumsum(wts) / wts.sum() * len(idx)).astype(int)
        start = 0
        for (blk, meta, _), end in zip(ents, cuts):
            sel = idx[order[start:end]]
            start = end
            if isinstance(blk, str):
                if not idmap or blk not in idmap:
                    raise KeyError(f'{blk} has no numeric ID; pass --idmap <level.dat> of the target world')
                bid = idmap[blk]
            else:
                bid = blk
            ids.ravel()[sel] = bid
            if blk in LOG_BLOCKS:
                data.ravel()[sel] = (meta & 3) | AXIS_BITS[axis.ravel()[sel]]
            else:
                data.ravel()[sel] = meta
    return ids, data


def write_schematic(path, ids, data, origin):
    """ids/data are (y, z, x). origin = (x, y, z) index of the trunk base / ground point. It is
    stored as WorldEdit offsets, which WorldPainter reads as the object's placement point."""
    H, L, W = ids.shape
    root = {'Width': nbtlib.Short(W), 'Height': nbtlib.Short(H), 'Length': nbtlib.Short(L),
            'Materials': nbtlib.String('Alpha'),
            'Blocks': nbtlib.ByteArray((ids & 0xFF).astype(np.uint8).ravel().view(np.int8)),
            'Data': nbtlib.ByteArray((data & 0xF).astype(np.uint8).ravel().view(np.int8)),
            'Entities': nbtlib.List[nbtlib.Compound](), 'TileEntities': nbtlib.List[nbtlib.Compound](),
            'WEOriginX': nbtlib.Int(0), 'WEOriginY': nbtlib.Int(0), 'WEOriginZ': nbtlib.Int(0),
            'WEOffsetX': nbtlib.Int(-origin[0]), 'WEOffsetY': nbtlib.Int(-origin[1]),
            'WEOffsetZ': nbtlib.Int(-origin[2])}
    hi = (ids >> 8).astype(np.uint8).ravel()
    if hi.any():                                   # modded IDs > 255 (BoP re-skin)
        if len(hi) % 2:
            hi = np.append(hi, 0)
        root['AddBlocks'] = nbtlib.ByteArray(((hi[0::2] << 4) | hi[1::2]).astype(np.uint8).view(np.int8))
    nbtlib.File(root, root_name='Schematic', gzipped=True).save(path)


def read_schematic(path):
    f = nbtlib.load(path)
    W, H, L = int(f['Width']), int(f['Height']), int(f['Length'])
    b = np.frombuffer(np.array(f['Blocks'], dtype=np.int8).tobytes(), np.uint8).astype(np.int16)
    d = np.frombuffer(np.array(f['Data'], dtype=np.int8).tobytes(), np.uint8).astype(np.int16)
    if 'AddBlocks' in f:
        a = np.frombuffer(np.array(f['AddBlocks'], dtype=np.int8).tobytes(), np.uint8)
        add = np.zeros(len(b), np.int16)
        add[0::2] = (a >> 4)[:len(add[0::2])]
        add[1::2] = (a & 15)[:len(add[1::2])]
        b = b | (add << 8)
    return b.reshape(H, L, W), d.reshape(H, L, W)
