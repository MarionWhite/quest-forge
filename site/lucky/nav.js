// Navigation for the Lucky Block page: one occupancy map of every solid thing on the plateau (the camp
// props, the stage's trees, rocks and dais, the pond), A* paths with string pulling, a push-out for
// anything that ends up inside a prop, and a counter that proves nobody did.
//
// Everything is in world blocks, ground at y = 0. A box is an axis-aligned rectangle [x0, z0, x1, z1]
// with a kind: 'solid' (blocks, furnace, tree trunks), 'leaf' (canopy a tall mob can walk through),
// 'fence' (rails and posts), 'low' (a bench a small mob could cross), 'water' (the pond). An agent has
// a radius; a point is blocked when the agent's square, centred there, overlaps a box.
const BUCKET = 2;
const KEY = (i, j) => (i + 4096) * 8192 + (j + 4096);

class Heap {
  constructor() { this.k = []; this.v = []; }
  get size() { return this.k.length; }
  push(key, val) {
    const k = this.k, v = this.v;
    let i = k.length; k.push(key); v.push(val);
    while (i > 0) { const p = (i - 1) >> 1; if (k[p] <= key) break; k[i] = k[p]; v[i] = v[p]; i = p; }
    k[i] = key; v[i] = val;
  }
  pop() {
    const k = this.k, v = this.v, out = v[0], lk = k.pop(), lv = v.pop(), n = k.length;
    if (n) {
      let i = 0;
      for (;;) {
        let c = 2 * i + 1;
        if (c >= n) break;
        if (c + 1 < n && k[c + 1] < k[c]) c++;
        if (k[c] >= lk) break;
        k[i] = k[c]; v[i] = v[c]; i = c;
      }
      k[i] = lk; v[i] = lv;
    }
    return out;
  }
}

export const nav = createNav();
export function createNav() {
  const boxes = [];
  const buckets = new Map();
  const maxR = 4.0; // the widest agent: every box is registered this far out
  const ground = new Map(); // "x,z" -> ground height in blocks (terrain only)
  let nextId = 1;
  const stats = { samples: 0, violations: 0, first: [], by: {}, last: {} };

  const forBuckets = (b, fn) => {
    const i0 = Math.floor((b.x0 - maxR) / BUCKET), i1 = Math.floor((b.x1 + maxR) / BUCKET);
    const j0 = Math.floor((b.z0 - maxR) / BUCKET), j1 = Math.floor((b.z1 + maxR) / BUCKET);
    for (let i = i0; i <= i1; i++) for (let j = j0; j <= j1; j++) fn(KEY(i, j));
  };
  function add(id, x0, z0, x1, z1, kind = 'solid') {
    const b = { id: id || 'b' + nextId++, x0: Math.min(x0, x1), z0: Math.min(z0, z1), x1: Math.max(x0, x1), z1: Math.max(z0, z1), kind, off: false };
    boxes.push(b);
    forBuckets(b, (k) => { let a = buckets.get(k); if (!a) buckets.set(k, a = []); a.push(b); });
    return b;
  }
  function remove(b) { if (b) b.off = true; }
  function restore(b) { if (b) b.off = false; }

  const hit = (b, x, z, r) => !b.off && x > b.x0 - r && x < b.x1 + r && z > b.z0 - r && z < b.z1 + r;
  // the first box the agent overlaps, or null. ign: a Set of ids or kinds to walk through
  function blockerAt(x, z, r, ign) {
    const a = buckets.get(KEY(Math.floor(x / BUCKET), Math.floor(z / BUCKET)));
    if (!a) return null;
    for (const b of a) if (hit(b, x, z, r) && !(ign && (ign.has(b.kind) || ign.has(b.id)))) return b;
    return null;
  }
  const blocked = (x, z, r, ign) => !!blockerAt(x, z, r, ign);

  function segFree(ax, az, bx, bz, r, ign) {
    const n = Math.max(1, Math.ceil(Math.hypot(bx - ax, bz - az) / 0.08));
    for (let k = 0; k <= n; k++) if (blocked(ax + (bx - ax) * k / n, az + (bz - az) * k / n, r, ign)) return false;
    return true;
  }

  // push a point out of whatever it is inside (minimum translation), a few passes
  function resolve(x, z, r, ign) {
    for (let pass = 0; pass < 8; pass++) {
      const b = blockerAt(x, z, r, ign);
      if (!b) break;
      const c = [[b.x0 - r - 0.002, z], [b.x1 + r + 0.002, z], [x, b.z0 - r - 0.002], [x, b.z1 + r + 0.002]];
      c.sort((p, q) => Math.hypot(p[0] - x, p[1] - z) - Math.hypot(q[0] - x, q[1] - z));
      const free = c.find((p) => !blockerAt(p[0], p[1], r, ign));
      const pick = free || c[0];
      x = pick[0]; z = pick[1];
    }
    return { x, z };
  }
  // the nearest free point to (x, z), spiralling out
  function nearestFree(x, z, r, ign, maxD = 6) {
    if (!blocked(x, z, r, ign)) return { x, z };
    for (let d = 0.25; d <= maxD; d += 0.25) {
      const n = Math.max(8, Math.round(d * 16));
      for (let k = 0; k < n; k++) {
        const a = (k / n) * Math.PI * 2, px = x + Math.cos(a) * d, pz = z + Math.sin(a) * d;
        if (!blocked(px, pz, r, ign)) return { x: px, z: pz };
      }
    }
    return { x, z };
  }

  // A*: waypoints from a to b for an agent of radius r. The last point is b itself (moved to the nearest
  // free point if it is inside something). ok is false when no route exists.
  function path(ax, az, bx, bz, r, o = {}) {
    const ign = o.ign, step = o.step || 0.25;
    const g = nearestFree(bx, bz, r, ign);
    bx = g.x; bz = g.z;
    if (segFree(ax, az, bx, bz, r, ign)) { const p = [[bx, bz]]; p.ok = true; return p; }
    const s0 = blocked(ax, az, r, ign) ? nearestFree(ax, az, r, ign) : { x: ax, z: az };
    const pad = 8;
    const gx0 = Math.floor((Math.min(ax, bx) - pad) / step) * step, gz0 = Math.floor((Math.min(az, bz) - pad) / step) * step;
    const W = Math.ceil((Math.abs(bx - ax) + 2 * pad) / step) + 1, H = Math.ceil((Math.abs(bz - az) + 2 * pad) / step) + 1;
    const N = W * H;
    const cx = (i) => gx0 + (i + 0.5) * step, cz = (j) => gz0 + (j + 0.5) * step;
    const cellOf = (x, z) => [Math.max(0, Math.min(W - 1, Math.floor((x - gx0) / step))), Math.max(0, Math.min(H - 1, Math.floor((z - gz0) / step)))];
    const state = new Int8Array(N); // 0 unknown, 1 free, 2 blocked
    const isFree = (i, j) => { const k = i + j * W; if (!state[k]) state[k] = blocked(cx(i), cz(j), r, ign) ? 2 : 1; return state[k] === 1; };
    let [si, sj] = cellOf(s0.x, s0.z), [ti, tj] = cellOf(bx, bz);
    if (!isFree(si, sj)) { const f = nearestFree(cx(si), cz(sj), r, ign); [si, sj] = cellOf(f.x, f.z); }
    if (!isFree(ti, tj)) { const f = nearestFree(cx(ti), cz(tj), r, ign); [ti, tj] = cellOf(f.x, f.z); }
    const gS = new Float32Array(N).fill(1e9), from = new Int32Array(N).fill(-1), closed = new Uint8Array(N);
    const heap = new Heap();
    const s = si + sj * W, t = ti + tj * W;
    gS[s] = 0; heap.push(0, s);
    let found = false, guard = 0;
    while (heap.size && guard++ < 60000) {
      const cur = heap.pop();
      if (closed[cur]) continue;
      closed[cur] = 1;
      if (cur === t) { found = true; break; }
      const ci = cur % W, cj = (cur / W) | 0;
      for (let di = -1; di <= 1; di++) for (let dj = -1; dj <= 1; dj++) {
        if (!di && !dj) continue;
        const ni = ci + di, nj = cj + dj;
        if (ni < 0 || nj < 0 || ni >= W || nj >= H) continue;
        const nk = ni + nj * W;
        if (closed[nk] || !isFree(ni, nj)) continue;
        if (di && dj && (!isFree(ci + di, cj) || !isFree(ci, cj + dj))) continue;
        const ng = gS[cur] + Math.hypot(di, dj);
        if (ng < gS[nk]) { gS[nk] = ng; from[nk] = cur; heap.push(ng + Math.hypot(ni - ti, nj - tj), nk); }
      }
    }
    if (!found) { const p = [[bx, bz]]; p.ok = false; return p; }
    const pts = [];
    for (let k = t; k !== -1; k = from[k]) pts.push([cx(k % W), cz((k / W) | 0)]);
    pts.reverse();
    pts.push([bx, bz]);
    // string pull: keep only the corners
    const out = [];
    let px = ax, pz = az, i = 0;
    while (i < pts.length) {
      let far = i;
      for (let k = pts.length - 1; k > i; k--) if (segFree(px, pz, pts[k][0], pts[k][1], r, ign)) { far = k; break; }
      out.push(pts[far]); px = pts[far][0]; pz = pts[far][1]; i = far + 1;
    }
    out.ok = true;
    return out;
  }

  // ---- terrain from the stage's voxels: ground height per column, solid boxes for everything standing on it
  const TERRAIN = new Set(['grass', 'path', 'dirt']);
  function fromVoxels(vox, opts = {}) {
    const cells = { solid: new Set(), leaf: new Set(), dais: new Set() };
    for (const [k, id] of vox.m) {
      const [x, y, z] = k.split(',').map(Number);
      if (y < 0) continue;
      if (TERRAIN.has(id)) {
        const key = x + ',' + z;
        ground.set(key, Math.max(ground.get(key) || 0, y + 1));
        continue;
      }
      if (y > 1 && !opts.tall) continue;
      const kind = id === 'brick' && x >= -1 && x <= 1 && z >= -1 && z <= 1 ? 'dais' : id === 'leaves' ? 'leaf' : 'solid';
      cells[kind].add(x + ',' + z);
    }
    // a hill higher than one step blocks everybody; a one-step rise is walked over
    for (const [key, h] of ground) if (h >= 2) cells.solid.add(key);
    // merge cells into big rectangles so pushing out of one never lands inside its neighbour
    for (const [kind, set] of Object.entries(cells)) {
      const used = new Set();
      const list = [...set].map((s) => s.split(',').map(Number)).sort((p, q) => p[1] - q[1] || p[0] - q[0]);
      for (const [x, z] of list) {
        if (used.has(x + ',' + z)) continue;
        let w = 1;
        while (set.has((x + w) + ',' + z) && !used.has((x + w) + ',' + z)) w++;
        let h = 1;
        const rowOk = (zz) => { for (let i = 0; i < w; i++) if (!set.has((x + i) + ',' + zz) || used.has((x + i) + ',' + zz)) return false; return true; };
        while (rowOk(z + h)) h++;
        for (let i = 0; i < w; i++) for (let j = 0; j < h; j++) used.add((x + i) + ',' + (z + j));
        add(kind + ':' + x + ',' + z, x, z, x + w, z + h, kind);
      }
    }
  }
  function groundAt(x, z) {
    // a bilinear blend of the four nearest column heights so a one-block rise is a ramp, not a cliff
    const fx = x - 0.5, fz = z - 0.5, x0 = Math.floor(fx), z0 = Math.floor(fz), u = fx - x0, v = fz - z0;
    const h = (a, b) => Math.min(1, ground.get(a + ',' + b) || 0);
    const k = (t) => t * t * (3 - 2 * t);
    const top = h(x0, z0) * (1 - k(u)) + h(x0 + 1, z0) * k(u), bot = h(x0, z0 + 1) * (1 - k(u)) + h(x0 + 1, z0 + 1) * k(u);
    return top * (1 - k(v)) + bot * k(v);
  }

  // ---- the proof: every sampled position is checked against the hard body radius
  function track(tag, x, z, r, ign, name) {
    stats.samples++;
    if (name) stats.last[name] = [+x.toFixed(2), +z.toFixed(2), +r.toFixed(2)];
    stats.by[tag] = (stats.by[tag] || 0) + 1;
    if (stats.samples % 20 === 0) publish();
    const b = blockerAt(x, z, r, ign);
    if (b) {
      stats.violations++;
      if (stats.first.length < 24) stats.first.push([tag, +x.toFixed(2), +z.toFixed(2), b.id]);
    }
  }
  function publish() {
    try { document.documentElement.dataset.navStats = JSON.stringify({ samples: stats.samples, violations: stats.violations, pushed: stats.pushed || 0, first: stats.first, by: stats.by, last: stats.last, noroute: stats.noroute, routes: stats.routes }); } catch (e) { /* no document */ }
  }

  return { add, remove, restore, blocked, blockerAt, segFree, resolve, nearestFree, path, fromVoxels, groundAt, track, publish, stats, boxes };
}

// Follow a polyline at a speed, one step at a time. The agent object carries x, z and the path state.
// Returns the heading it moved in (or null when it has arrived).
export function followPath(a, dt, speed, nav, r, ign) {
  while (a.path && a.i < a.path.length) {
    const [px, pz] = a.path[a.i];
    const dx = px - a.x, dz = pz - a.z, d = Math.hypot(dx, dz);
    const last = a.i === a.path.length - 1;
    if (d < (last ? 0.06 : 0.12)) { a.i++; continue; }
    const step = Math.min(d, speed * dt);
    a.x += (dx / d) * step; a.z += (dz / d) * step;
    const f = nav.resolve(a.x, a.z, r, ign);
    a.x = f.x; a.z = f.z;
    return { dx: dx / d, dz: dz / d, step };
  }
  return null;
}
