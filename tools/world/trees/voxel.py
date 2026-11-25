"""Voxel canvas for tree growth.

Trees are drawn in *roles* (trunk, branch, leaf, accent, ...), not in Minecraft blocks.
A palette (palettes.py) turns roles into block (id, meta) pairs only at export time, so the
same grown tree can be re-skinned (vanilla now, Biomes O' Plenty later) without regrowing it.

Coordinates: world space with the trunk base centre at (0, 0, 0), y up. Ground is y = 0;
negative y is below ground (root flare sunk into the terrain).
"""
import math
import numpy as np

# role ids ------------------------------------------------------------------------------
ROLES = ['air', 'trunk', 'branch', 'root', 'bark', 'leaf', 'leaf2', 'leaf3', 'leaf4',
         'accent', 'accent2', 'accent3', 'glow', 'snow', 'core']
R = {n: i for i, n in enumerate(ROLES)}
WOOD = {R['trunk'], R['branch'], R['root'], R['bark'], R['core']}
# placement priority: higher overwrites lower. Wood beats everything; leaves only fill air.
PRIO = np.zeros(len(ROLES), np.int8)
for n in ('trunk', 'branch', 'root', 'bark', 'core'):
    PRIO[R[n]] = 3
for n in ('accent', 'accent2', 'accent3', 'glow'):
    PRIO[R[n]] = 2
for n in ('leaf', 'leaf2', 'leaf3', 'leaf4', 'snow'):
    PRIO[R[n]] = 1

# log axis: 0 = up (y), 1 = x, 2 = z, 3 = bark on all sides
UP, AX_X, AX_Z, ALLBARK = 0, 1, 2, 3


def axis_of(d):
    ax = int(np.argmax(np.abs(d)))
    return {0: AX_X, 1: UP, 2: AX_Z}[ax]


class Grid:
    def __init__(self, half_w, height, below=0):
        """half_w: max horizontal reach from the trunk; height: max y; below: layers under y=0."""
        self.hw = int(math.ceil(half_w)) + 2
        self.below = int(below)
        self.W = 2 * self.hw + 1
        self.H = int(math.ceil(height)) + self.below + 3
        self.role = np.zeros((self.H, self.W, self.W), np.uint8)     # (y, z, x)
        self.axis = np.zeros_like(self.role)

    # index helpers ---------------------------------------------------------------------
    def _box(self, lo, hi):
        """world-space float bounds -> clipped index slices + world coords of block centres."""
        x0 = max(int(math.floor(lo[0])) + self.hw, 0); x1 = min(int(math.ceil(hi[0])) + self.hw + 1, self.W)
        y0 = max(int(math.floor(lo[1])) + self.below, 0); y1 = min(int(math.ceil(hi[1])) + self.below + 1, self.H)
        z0 = max(int(math.floor(lo[2])) + self.hw, 0); z1 = min(int(math.ceil(hi[2])) + self.hw + 1, self.W)
        if x0 >= x1 or y0 >= y1 or z0 >= z1:
            return None
        ys = np.arange(y0, y1) - self.below
        zs = np.arange(z0, z1) - self.hw
        xs = np.arange(x0, x1) - self.hw
        return (slice(y0, y1), slice(z0, z1), slice(x0, x1)), ys[:, None, None], zs[None, :, None], xs[None, None, :]

    def _apply(self, sl, mask, role, axis):
        cur = self.role[sl]
        if PRIO[role] == 3:
            ok = mask
        else:
            ok = mask & ((cur == 0) | (PRIO[cur] < PRIO[role]))
        cur[ok] = role
        if axis is not None:
            a = self.axis[sl]
            if np.isscalar(axis):
                a[ok] = axis
            else:
                a[ok] = axis[ok]

    def put(self, x, y, z, role, axis=UP):
        xi, yi, zi = int(round(x)) + self.hw, int(round(y)) + self.below, int(round(z)) + self.hw
        if 0 <= xi < self.W and 0 <= yi < self.H and 0 <= zi < self.W:
            cur = self.role[yi, zi, xi]
            if cur == 0 or PRIO[role] > PRIO[cur] or PRIO[role] == 3:
                self.role[yi, zi, xi] = role
                self.axis[yi, zi, xi] = axis

    def get(self, x, y, z):
        xi, yi, zi = int(round(x)) + self.hw, int(round(y)) + self.below, int(round(z)) + self.hw
        if 0 <= xi < self.W and 0 <= yi < self.H and 0 <= zi < self.W:
            return int(self.role[yi, zi, xi])
        return 0

    # primitives ------------------------------------------------------------------------
    def line(self, p, q, role, axis=None):
        """6-connected voxel line (no diagonal-only gaps, so logs read as one limb)."""
        p = np.asarray(p, float); q = np.asarray(q, float)
        ax = axis_of(q - p) if axis is None else axis
        n = int(np.max(np.abs(q - p)) * 3) + 1
        prev = None
        for t in np.linspace(0, 1, n + 1):
            c = np.round(p + (q - p) * t).astype(int)
            if prev is not None:
                diff = c - prev
                if (diff != 0).sum() > 1:          # fill the corner so the path is face-connected
                    step = prev.copy()
                    for k in (1, 0, 2):
                        if diff[k] != 0:
                            step[k] += diff[k]
                            if not np.array_equal(step, c):
                                self.put(*step, role, ax)
            self.put(*c, role, ax)
            prev = c

    def capsule(self, p, q, r0, r1=None, role=None, axis=None):
        """Tapered cylinder with rounded ends between p (radius r0) and q (radius r1)."""
        r1 = r0 if r1 is None else r1
        if max(r0, r1) < 0.75:
            return self.line(p, q, role, axis)
        p = np.asarray(p, float); q = np.asarray(q, float)
        rm = max(r0, r1)
        b = self._box(np.minimum(p, q) - rm, np.maximum(p, q) + rm)
        if b is None:
            return
        sl, Y, Z, X = b
        d = q - p; L2 = float(d @ d) or 1e-9
        t = np.clip(((X - p[0]) * d[0] + (Y - p[1]) * d[1] + (Z - p[2]) * d[2]) / L2, 0, 1)
        dist2 = (X - p[0] - t * d[0]) ** 2 + (Y - p[1] - t * d[1]) ** 2 + (Z - p[2] - t * d[2]) ** 2
        r = r0 + (r1 - r0) * t
        mask = dist2 <= r * r
        self._apply(sl, mask, role, axis_of(d) if axis is None else axis)

    def blob(self, c, rx, ry, rz, role, rng, rough=0.35, fill=1.0, axis=None, bottom_cut=None):
        """Ragged ellipsoid. rough = how much the edge is eaten; fill = interior keep rate."""
        c = np.asarray(c, float)
        b = self._box(c - [rx, ry, rz], c + [rx, ry, rz])
        if b is None:
            return
        sl, Y, Z, X = b
        d = np.sqrt(((X - c[0]) / max(rx, .3)) ** 2 + ((Y - c[1]) / max(ry, .3)) ** 2 + ((Z - c[2]) / max(rz, .3)) ** 2)
        u = rng.random(d.shape)
        mask = d <= 1.0 - rough * u
        if fill < 1.0:
            mask &= (rng.random(d.shape) < fill) | (d < 0.45)
        if bottom_cut is not None:
            mask &= (Y >= c[1] - bottom_cut)
        self._apply(sl, mask, role, axis)

    def disc_layer(self, y, cx, cz, rfun, role, axis=UP):
        """One horizontal layer: blocks whose centre lies within rfun(theta) of (cx, cz)."""
        rmax = rfun.rmax
        b = self._box((cx - rmax, y, cz - rmax), (cx + rmax, y, cz + rmax))
        if b is None:
            return
        sl, Y, Z, X = b
        dx = X - cx; dz = Z - cz
        dist = np.sqrt(dx * dx + dz * dz)
        th = np.arctan2(dz, dx)
        mask = dist <= rfun(th)
        mask = np.broadcast_to(mask, self.role[sl].shape)
        self._apply(sl, mask.copy(), role, axis)

    def carve(self, mask_fn, lo, hi):
        """Set to air where mask_fn(X, Y, Z) is true (used for fire scars, hollows)."""
        b = self._box(lo, hi)
        if b is None:
            return
        sl, Y, Z, X = b
        m = np.broadcast_to(mask_fn(X, Y, Z), self.role[sl].shape)
        self.role[sl][m] = 0

    # cleanup ---------------------------------------------------------------------------
    def prune_floating_leaves(self, min_neighbours=1):
        """Drop leaf voxels with no solid face neighbour (single floating leaves look like noise)."""
        solid = self.role != 0
        n = np.zeros(solid.shape, np.int8)
        n[1:] += solid[:-1]; n[:-1] += solid[1:]
        n[:, 1:] += solid[:, :-1]; n[:, :-1] += solid[:, 1:]
        n[:, :, 1:] += solid[:, :, :-1]; n[:, :, :-1] += solid[:, :, 1:]
        leafy = PRIO[self.role] == 1
        self.role[leafy & (n < min_neighbours)] = 0

    def cropped(self):
        """(role, axis, origin) cropped to content; origin = index of world (0,0,0) in the crop."""
        nz = np.argwhere(self.role != 0)
        lo, hi = nz.min(0), nz.max(0) + 1
        sl = tuple(slice(a, b) for a, b in zip(lo, hi))
        origin = (int(self.hw - lo[2]), int(self.below - lo[0]), int(self.hw - lo[1]))   # x, y, z
        return self.role[sl].copy(), self.axis[sl].copy(), origin
