"""Growth algorithms shared by the species modules.

- space_colonise: Runions, Lane & Prusinkiewicz (2007). Twigs grow toward attraction points
  scattered in a crown envelope, which gives natural, self-spacing broadleaf branch structure.
- pipe_radii: da Vinci / pipe model, r^g = sum(child r^g), so limbs taper and fork believably.
- limb: one curved, tapering limb as a polyline (used by the recursive-branching species).
- draw_trunk / draw_roots: tapering, fluted multi-block trunks with flared root buttresses.
"""
import math
import numpy as np
from voxel import R, UP


# ---------------------------------------------------------------------------------------
# space colonisation
# ---------------------------------------------------------------------------------------
def sample_envelope(rng, n, inside, lo, hi):
    """Rejection-sample n points in the box [lo, hi] for which inside(P) (vectorised) is true."""
    lo = np.asarray(lo, float); hi = np.asarray(hi, float)
    pts = []
    tries = 0
    while sum(len(p) for p in pts) < n and tries < 60:
        P = lo + (hi - lo) * rng.random((max(n, 256) * 2, 3))
        pts.append(P[inside(P)])
        tries += 1
    P = np.concatenate(pts) if pts else np.zeros((0, 3))
    return P[:n]


def space_colonise(attr, nodes, parent, rng, step=1.0, influence=8.0, kill=2.0, iters=160,
                   tropism=(0, 0, 0), jitter=0.15, growable=None, max_nodes=12000):
    """Grow a branch skeleton toward attractors.

    attr: (A,3) attraction points. nodes: list of (3,) start nodes (e.g. a trunk chain);
    parent: their parent indices. growable: bool per start node (only those may sprout).
    Returns (nodes (N,3) array, parent (N,) int array).
    """
    nodes = [np.asarray(n, float) for n in nodes]
    parent = list(parent)
    can = list(growable) if growable is not None else [True] * len(nodes)
    attr = np.asarray(attr, float)
    alive = np.ones(len(attr), bool)
    N = np.array(nodes)
    gidx = np.array([i for i, c in enumerate(can) if c])
    d = np.linalg.norm(attr[:, None, :] - N[gidx][None, :, :], axis=2)
    near = gidx[d.argmin(1)]
    near_d = d.min(1)
    seen = {tuple(np.round(n * 2).astype(int)) for n in nodes}
    trop = np.asarray(tropism, float)
    for _ in range(iters):
        alive &= near_d > kill
        act = alive & (near_d < influence)
        if not act.any() or len(nodes) >= max_nodes:
            break
        idx = near[act]
        vec = attr[act] - np.array(nodes)[idx]
        vec /= np.maximum(np.linalg.norm(vec, axis=1, keepdims=True), 1e-6)
        uniq, inv = np.unique(idx, return_inverse=True)
        acc = np.zeros((len(uniq), 3))
        np.add.at(acc, inv, vec)
        new = []
        for k, ni in enumerate(uniq):
            v = acc[k]
            n = np.linalg.norm(v)
            v = v / n if n > 1e-3 else rng.normal(size=3)
            v = v + trop + rng.normal(scale=jitter, size=3)
            v /= np.linalg.norm(v)
            p = nodes[ni] + v * step
            key = tuple(np.round(p * 2).astype(int))
            if key in seen:
                continue
            seen.add(key)
            nodes.append(p); parent.append(int(ni)); new.append(len(nodes) - 1)
        if not new:
            break
        NP = np.array([nodes[i] for i in new])
        dn = np.linalg.norm(attr[:, None, :] - NP[None, :, :], axis=2)
        m = dn.min(1)
        better = m < near_d
        near[better] = np.array(new)[dn.argmin(1)[better]]
        near_d[better] = m[better]
    return np.array(nodes), np.array(parent)


def children_of(parent):
    kids = [[] for _ in parent]
    for i, p in enumerate(parent):
        if p >= 0:
            kids[p].append(i)
    return kids


def smooth(nodes, parent, passes=2, keep=1):
    """Laplacian smoothing along chains; the first `keep` nodes (trunk base) stay put."""
    kids = children_of(parent)
    P = nodes.copy()
    for _ in range(passes):
        Q = P.copy()
        for i in range(keep, len(P)):
            if parent[i] >= 0 and len(kids[i]) == 1:
                Q[i] = 0.5 * P[i] + 0.25 * (P[parent[i]] + P[kids[i][0]])
        P = Q
    return P


def pipe_radii(parent, gamma=2.3):
    """Relative radii by the pipe model: every tip = 1, r^g = sum(child r^g)."""
    kids = children_of(parent)
    r = np.ones(len(parent))
    for i in reversed(range(len(parent))):
        if kids[i]:
            r[i] = sum(r[k] ** gamma for k in kids[i]) ** (1 / gamma)
    return r, kids


def depth_from_tips(kids):
    """Steps to the furthest tip below each node (0 at tips)."""
    n = len(kids)
    dep = np.zeros(n, int)
    for i in reversed(range(n)):
        if kids[i]:
            dep[i] = 1 + max(dep[k] for k in kids[i])
    return dep


def draw_skeleton(g, nodes, parent, radius, role_trunk=R['branch'], start=1, trunk_until=-1,
                  min_r=0.5, max_r=None):
    """Draw every edge parent->child as a capsule using the child's radius."""
    for i in range(start, len(nodes)):
        p = parent[i]
        if p < 0:
            continue
        r1 = max(min_r, radius[i])
        r0 = max(min_r, min(radius[p], radius[i] * 1.25))
        if max_r:
            r0, r1 = min(r0, max_r), min(r1, max_r)
        role = R['trunk'] if i <= trunk_until else role_trunk
        g.capsule(nodes[p], nodes[i], r0, r1, role)


# ---------------------------------------------------------------------------------------
# recursive limbs
# ---------------------------------------------------------------------------------------
def unit(v):
    v = np.asarray(v, float)
    return v / max(np.linalg.norm(v), 1e-9)


def limb(p, d, length, rng, step=1.0, gravity=0.0, wobble=0.1, up_bend=0.0):
    """A curved limb as a list of points. gravity < 0 droops, up_bend > 0 turns tips upward."""
    pts = [np.asarray(p, float)]
    d = unit(d)
    n = max(1, int(round(length / step)))
    for k in range(n):
        f = k / max(n - 1, 1)
        d = unit(d + np.array([0, gravity + up_bend * f, 0]) + rng.normal(scale=wobble, size=3))
        pts.append(pts[-1] + d * step)
    return pts


def draw_polyline(g, pts, r0, r1, role, min_r=0.5):
    n = len(pts) - 1
    for k in range(n):
        a = r0 + (r1 - r0) * k / max(n, 1)
        b = r0 + (r1 - r0) * (k + 1) / max(n, 1)
        g.capsule(pts[k], pts[k + 1], max(min_r, a), max(min_r, b), role)


def direction(azimuth, elevation):
    """Unit vector from azimuth (radians around y) and elevation (radians above horizontal)."""
    ce = math.cos(elevation)
    return np.array([math.cos(azimuth) * ce, math.sin(elevation), math.sin(azimuth) * ce])


# ---------------------------------------------------------------------------------------
# trunks and roots
# ---------------------------------------------------------------------------------------
class Lobed:
    """Horizontal cross-section r(theta) = r * (1 + sum a_k cos(k*theta + phase_k))."""

    def __init__(self, r, lobes=()):
        self.r = r
        self.lobes = lobes
        self.rmax = r * (1 + sum(abs(a) for _, a, _ in lobes)) + 1

    def __call__(self, th):
        f = 1.0
        for k, a, ph in self.lobes:
            f = f + a * np.cos(k * th + ph)
        return self.r * f


def draw_trunk(g, y0, y1, radius_at, centre_at, rng, lobes=None, role=R['trunk']):
    """Fill trunk layers y0..y1. radius_at(y) -> float, centre_at(y) -> (x, z),
    lobes(y) -> list of (k, amplitude, phase) for buttress fluting."""
    for y in range(int(math.floor(y0)), int(math.ceil(y1)) + 1):
        r = radius_at(y)
        if r <= 0:
            continue
        cx, cz = centre_at(y)
        if r < 0.75:
            g.put(cx, y, cz, role, UP)
            continue
        g.disc_layer(y, cx, cz, Lobed(r + 0.15, lobes(y) if lobes else ()), role, UP)


def draw_roots(g, rng, n, r_trunk, reach, y_top=2.0, y_end=0.0, sink=0, role=R['root'], phase=None,
               spread=0.35, r_root=None):
    """Radial buttress roots: thick where they leave the trunk, thinning as they snake outwards.
    Returns the list of root tip positions."""
    tips = []
    phase = rng.uniform(0, 2 * math.pi) if phase is None else phase
    r_root = r_root if r_root is not None else max(0.6, r_trunk * 0.45)
    for k in range(n):
        a = phase + k * 2 * math.pi / n + rng.uniform(-spread, spread)
        L = reach * rng.uniform(0.6, 1.1)
        start = np.array([math.cos(a) * r_trunk * 0.6, y_top * rng.uniform(0.7, 1.2), math.sin(a) * r_trunk * 0.6])
        pts = [start]
        segs = max(3, int(L))
        for s in range(1, segs + 1):
            f = s / segs
            ang = a + 0.25 * math.sin(f * 3 + k)              # gentle snaking
            dist = r_trunk * 0.6 + (L) * f
            y = y_top * (1 - f) ** 1.6 + y_end * f - (sink * f if f > 0.6 else 0)
            pts.append(np.array([math.cos(ang) * dist, y, math.sin(ang) * dist]))
        for s in range(len(pts) - 1):
            f = s / (len(pts) - 1)
            r = r_root * (1 - f) + 0.5 * f
            g.capsule(pts[s], pts[s + 1], max(0.5, r), max(0.5, r * 0.9), role)
        tips.append(pts[-1])
    return tips


def hang(g, p, length, role, axis=UP):
    """Vertical strand hanging down from p (icicles, vines, petals, drop roots)."""
    x, y, z = p
    for k in range(int(length)):
        g.put(x, y - k, z, role, axis)


# ---------------------------------------------------------------------------------------
# broadleaf crown = trunk chain + space colonisation + pipe radii
# ---------------------------------------------------------------------------------------
def trunk_chain(base, top, rng, step=1.0, wobble=0.2):
    """Straight-ish chain of nodes from base to top (the colonisation seed)."""
    base = np.asarray(base, float); top = np.asarray(top, float)
    n = max(2, int(np.linalg.norm(top - base) / step))
    pts = [base + (top - base) * k / n for k in range(n + 1)]
    for k in range(1, n):
        pts[k] = pts[k] + np.array([rng.normal(0, wobble), 0, rng.normal(0, wobble)])
    return pts


def grow_crown(g, rng, chain, attr, r_base, sprout_from=0.6, step=1.0, influence=7.0, kill=1.8,
               tropism=(0, 0.1, 0), gamma=2.4, min_r=0.5, iters=160, jitter=0.15, draw=True,
               trunk_role=R['trunk'], branch_role=R['branch'], taper=0.0):
    """Grow a colonised crown off `chain` (list of points) and draw it.
    sprout_from: fraction of the chain below which no side branches start.
    taper: extra radius reduction per unit height up the chain (0 = pure pipe model).
    Returns dict(nodes, parent, radius, kids, tips, depth)."""
    nch = len(chain)
    parent = [-1] + list(range(nch - 1))
    growable = [k >= int(sprout_from * (nch - 1)) for k in range(nch)]
    nodes, parent = space_colonise(attr, chain, parent, rng, step=step, influence=influence, kill=kill,
                                   tropism=tropism, growable=growable, iters=iters, jitter=jitter)
    nodes = smooth(nodes, parent, passes=2, keep=nch)
    rel, kids = pipe_radii(parent, gamma)
    radius = rel * (r_base / rel[0])
    if taper:
        for i in range(nch):
            radius[i] = max(radius[i], r_base * (1 - taper * i / max(nch - 1, 1)))
    if draw:
        draw_skeleton(g, nodes, parent, radius, role_trunk=branch_role, start=nch, min_r=min_r)
        for i in range(1, nch):
            g.capsule(nodes[i - 1], nodes[i], max(min_r, radius[i - 1]), max(min_r, radius[i]), trunk_role)
    tips = [i for i in range(len(nodes)) if not kids[i]]
    depth = depth_from_tips(kids)
    twigs = [i for i in range(nch, len(nodes)) if depth[i] <= 1]
    return dict(nodes=nodes, parent=parent, radius=radius, kids=kids, tips=tips, depth=depth, twigs=twigs,
                chain=nch)


def ellipsoid(cy, rx, ry, rz=None, cx=0.0, cz=0.0, ymin=None):
    """Vectorised inside-test for sample_envelope."""
    rz = rx if rz is None else rz

    def inside(P):
        d = ((P[:, 0] - cx) / rx) ** 2 + ((P[:, 1] - cy) / ry) ** 2 + ((P[:, 2] - cz) / rz) ** 2
        m = d <= 1
        if ymin is not None:
            m &= P[:, 1] >= ymin
        return m
    return inside


def cloud(rng, cy, rx, ry, n=6, ymin=None, lobe=0.55, cx=0.0, cz=0.0, flat_top=False):
    """Irregular crown envelope: a shrunken core ellipsoid plus n lobes pushed toward its rim.
    Gives clumpy crowns with bays and gaps instead of one smooth blob."""
    lobes = [(cx, cy, cz, rx * 0.6, ry * 0.6)]
    for _ in range(n):
        a = rng.uniform(0, 2 * math.pi)
        e = rng.uniform(-0.6, 0.8 if not flat_top else 0.3)
        d = rng.uniform(0.45, 0.75)
        lobes.append((cx + math.cos(a) * rx * d * math.cos(e * 0.8), cy + ry * d * math.sin(e),
                      cz + math.sin(a) * rx * d * math.cos(e * 0.8),
                      rx * lobe * rng.uniform(0.75, 1.15), ry * lobe * rng.uniform(0.8, 1.2)))

    def inside(P):
        m = np.zeros(len(P), bool)
        for x, y, z, a, b in lobes:
            m |= ((P[:, 0] - x) / a) ** 2 + ((P[:, 1] - y) / b) ** 2 + ((P[:, 2] - z) / a) ** 2 <= 1
        if ymin is not None:
            m &= P[:, 1] >= ymin
        return m
    return inside
