// Running for your life (round 8b: the Wither Skeleton's flight, the Zombie's): paths walked by distance, a sprint's
// speed over a path, the 1.7.10 view bobbing, and the Krypt's own light along a mob's way (so it comes out of the dark
// as dark as the dark it was in).
//   poly(pts)              a polyline in local x/z: { L, at(u) -> { x, z, dx, dz } } (u metres along it)
//   bez(a, c, b, n)        a quadratic bend from a to b with control c, as points
//   runProfile(L, o)       the distance run after dt seconds: up to o.v (m/s) in o.accel s, braking to a stop at L
//                          (o.brake m/s^2); { dur, u(dt), tAt(u) }
//   bob(c, u, amp)         EntityRenderer.setupViewBobbing on a camera c after u metres walked (amp 0.1 at a run)
//   STEP                   metres per footstep (Entity.distanceWalkedModified: a step sound each 1/0.6 m)
//   bakeMany(R, pts)       the Krypt's baked floor light at local points [{ x, z }] in one pass: [v] (grey 0..1, or null)
//   lightOf(R, pts)        bakeMany as a lookup: (x, z) -> v at the nearest sampled point
import { THREE, clamp, lerp, sstep } from "./rig.js";

export const STEP = 1 / 0.6;

export function poly(pts) {
  const seg = []; let L = 0;
  for (let i = 1; i < pts.length; i++) {
    const a = pts[i - 1], b = pts[i], l = Math.hypot(b.x - a.x, b.z - a.z);
    if (l < 1e-4) continue;
    seg.push({ a, b, l, u0: L }); L += l;
  }
  const at = (u) => {
    if (!seg.length) return { x: pts[0].x, z: pts[0].z, dx: 0, dz: 1 };
    u = clamp(u, 0, L);
    let q = seg[seg.length - 1];
    for (const s of seg) if (u <= s.u0 + s.l) { q = s; break; }
    const k = (u - q.u0) / q.l;
    return { x: lerp(q.a.x, q.b.x, k), z: lerp(q.a.z, q.b.z, k), dx: (q.b.x - q.a.x) / q.l, dz: (q.b.z - q.a.z) / q.l };
  };
  return { L, at };
}

export const bez = (a, c, b, n = 10) => [...Array(n + 1)].map((_, i) => {
  const k = i / n, w0 = (1 - k) * (1 - k), w1 = 2 * k * (1 - k), w2 = k * k;
  return { x: w0 * a.x + w1 * c.x + w2 * b.x, z: w0 * a.z + w1 * c.z + w2 * b.z };
});

export function runProfile(L, { v = 5.4, accel = 0.45, brake = 7, vEnd = 0.12, hz = 120 } = {}) {
  const us = [];
  let u = 0, t = 0; const dt = 1 / hz;
  while (u < L - 0.004 && t < 12) {
    const sp = Math.min(v * sstep(0, accel, t), Math.sqrt(2 * brake * Math.max(0, L - u)) + vEnd);
    u = Math.min(L, u + sp * dt); t += dt; us.push(u);
  }
  const dur = us.length / hz;
  const at = (x) => { const i = Math.floor(x * hz); return i < 0 ? 0 : i >= us.length ? L : us[i]; };
  const tAt = (w) => { for (let i = 0; i < us.length; i++) if (us[i] >= w) return i / hz; return dur; };
  return { dur, u: at, tAt, L };
}

// EntityRenderer.setupViewBobbing: f1 = distanceWalkedModified (0.6 per metre), f2 = the bob amount (0.1 at a run).
export function bob(c, u, amp) {
  if (amp <= 0) return c;
  const ph = u * 0.6 * Math.PI;
  c.x += Math.cos(c.yaw) * Math.sin(ph) * amp * 0.5; c.z += Math.sin(c.yaw) * Math.sin(ph) * amp * 0.5;
  c.y -= Math.abs(Math.cos(ph) * amp);
  c.roll = (c.roll || 0) + Math.sin(ph) * amp * 3 * Math.PI / 180;
  c.pitch -= Math.abs(Math.cos(ph - 0.2) * amp) * 5 * Math.PI / 180;
  return c;
}

// R.bakeAt walks every chunk's vertices once per point; this walks them once for all the points.
const _v = new THREE.Vector3(), _n = new THREE.Vector3(), _bb = new THREE.Box3(), _m = new THREE.Matrix3();
export function bakeMany(R, pts) {
  const W = pts.map((p) => R.L(p.x, 0, p.z));
  const acc = pts.map(() => [0, 0]);
  const grid = new Map(), key = (x, z) => x * 100003 + z;
  W.forEach((w, i) => { const k = key(Math.floor(w.x), Math.floor(w.z)); if (!grid.has(k)) grid.set(k, []); grid.get(k).push(i); });
  const box = new THREE.Box3(); for (const w of W) box.expandByPoint(w); box.expandByScalar(1.2);
  const fy = R.O.y;
  let mi = 0;
  R.kr.scene.traverse((o) => {
    const g = o.isMesh && o.geometry, bk = g && g.attributes.bake;
    if (!bk) return;
    if (!g.boundingBox) g.computeBoundingBox();
    o.updateMatrixWorld();
    if (!_bb.copy(g.boundingBox).applyMatrix4(o.matrixWorld).intersectsBox(box)) return;
    const pos = g.attributes.position, nrm = g.attributes.normal;
    _m.getNormalMatrix(o.matrixWorld); mi++;
    for (let i = 0; i < pos.count; i++) {
      _v.fromBufferAttribute(pos, i).applyMatrix4(o.matrixWorld);
      if (Math.abs(_v.y - fy) > 0.51 || !box.containsPoint(_v)) continue;
      if (nrm && _n.fromBufferAttribute(nrm, i).applyMatrix3(_m).y < 0.9) continue;
      for (const dx of [-0.51, 0.51]) for (const dz of [-0.51, 0.51]) {
        const list = grid.get(key(Math.floor(_v.x + dx), Math.floor(_v.z + dz))); if (!list) continue;
        for (const j of list) {
          const w = W[j];
          if (Math.abs(_v.x - w.x) > 0.51 || Math.abs(_v.z - w.z) > 0.51) continue;
          if (acc[j].mark === mi * 1e7 + i) continue;   // (one vertex once, however many grid cells it was looked up from)
          acc[j].mark = mi * 1e7 + i;
          acc[j][0] += (bk.getX(i) + bk.getY(i) + bk.getZ(i)) / 3; acc[j][1]++;
        }
      }
    }
  });
  return acc.map((a) => (a[1] ? a[0] / a[1] : null));
}

export function lightOf(R, pts, dflt = 0.15) {
  const v = bakeMany(R, pts), P = pts.map((p, i) => ({ x: p.x, z: p.z, v: v[i] })).filter((p) => p.v != null);
  return (x, z) => { let best = null, bd = 1e9; for (const q of P) { const d = (q.x - x) ** 2 + (q.z - z) ** 2; if (d < bd) { bd = d; best = q; } } return best ? best.v : dflt; };
}

// ---- the blocks round you and what the first frame sees ------------------------------------------------------------
// blocks(R): by offset from the block you stand in (a along local x, b along local z; y absolute, y0 the floor layer):
//   { y0, wB(a, b) -> world [x, z], S(a, y, b) solid, cL(a, b) -> local block centre, clear(a, b, h) open h high on a
//   floor, wallAt(s, b) the wall on side s at row b (blocks out, a full wall three high) or -1 }
export function blocks(R) {
  const rB = [Math.round(R.r.x), Math.round(R.r.z)], fB = [Math.round(R.f.x), Math.round(R.f.z)];
  const bx0 = Math.floor(R.O.x), bz0 = Math.floor(R.O.z), y0 = Math.round(R.O.y);
  const wB = (a, b) => [bx0 + rB[0] * a + fB[0] * b, bz0 + rB[1] * a + fB[1] * b];
  const S = (a, y, b) => { const [x, z] = wB(a, b); return R.solidW(x + 0.5, y + 0.5, z + 0.5); };
  const w = new THREE.Vector3();
  const cL = (a, b) => { const [x, z] = wB(a, b); const l = R.toLocal(w.set(x + 0.5, y0, z + 0.5)); return { x: l.x, z: l.z }; };
  const clear = (a, b, h = 3) => { for (let y = y0; y < y0 + h; y++) if (S(a, y, b)) return false; return S(a, y0 - 1, b); };
  const wallAt = (s, b) => { for (let k = 1; k <= 9; k++) if (S(s * k, y0, b) || S(s * k, y0 + 1, b)) return S(s * k, y0, b) && S(s * k, y0 + 1, b) && S(s * k, y0 + 2, b) ? k : -1; return -1; };
  return { y0, wB, S, cL, clear, wallAt };
}
// startView(R): seen0(x, y, z) local -> true when the point is in the first frame (the start camera's frustum, 8% margin)
// and in line of sight through the blocks. hidden(seen0, p): a standing mob's box at p is not.
export function startView(R) {
  const st = R.start, vf = THREE.MathUtils.degToRad(st.fov) / 2, asp = R.camera.aspect || 16 / 9;
  const tv = Math.tan(vf) * 1.08, th = Math.tan(vf) * asp * 1.08;
  const cy = Math.cos(st.yaw), sy = Math.sin(st.yaw), cp = Math.cos(st.pitch), sp = Math.sin(st.pitch);
  const fw = [-sy * cp, sp, cy * cp], rt = [cy, 0, sy], up = [sy * sp, cp, -cy * sp];
  return (x, y, z) => {
    const v = [x - st.x, y - st.y, z - st.z], dz = v[0] * fw[0] + v[1] * fw[1] + v[2] * fw[2];
    if (dz < 0.05) return false;
    if (Math.abs((v[0] * rt[0] + v[2] * rt[2]) / dz) > th || Math.abs((v[0] * up[0] + v[1] * up[1] + v[2] * up[2]) / dz) > tv) return false;
    const n = Math.hypot(v[0], v[1], v[2]);
    for (let q = 0.1; q < n - 0.08; q += 0.05) if (R.solid(st.x + v[0] * q / n, st.y + v[1] * q / n, st.z + v[2] * q / n)) return false;
    return true;
  };
}
export const hidden = (seen0, p, h = 2.3) => { for (const dx of [-0.3, 0.3]) for (const dz of [-0.3, 0.3]) for (const y of [0.3, h / 2, h]) if (seen0(p.x + dx, y, p.z + dz)) return false; return true; };
// sideSpots(R, B, seen0, o): places off the corridor (an alcove, a side way, the corner of a bend) on rows dir*k
// (k in kMin..kMax) where a mob stands out of sight of the first frame, nearest k to `want` first:
// [{ c: { x, z }, k, sd, j, c2 }] (c2: a second such place beside it, for a second mob, or null).
export function sideSpots(R, B, seen0, { dir = 1, kMin = 4, kMax = 12, want = 8, h = 2.3, minX = 1.2 } = {}) {
  const out = [];
  for (let k = kMin; k <= kMax; k++) for (const sd of [-1, 1]) {
    let j = 0; while (j < 6 && B.clear(sd * (j + 1), dir * k)) j++;
    for (let jj = 1; jj <= j; jj++) {   // (the nearest the corridor that is out of sight: it steps out soonest)
      const c = B.cL(sd * jj, dir * k);
      if (Math.abs(c.x) < minX || !hidden(seen0, c, h)) continue;
      let c2 = null;
      for (const [da, db] of [[1, 0], [0, 1], [0, -1], [-1, 0]]) {
        const a2 = sd * (jj + da), b2 = dir * k + db;
        if (!B.clear(a2, b2)) continue;
        const q = B.cL(a2, b2);
        if (Math.abs(q.x) >= minX && hidden(seen0, q, h)) { c2 = q; break; }
      }
      out.push({ c, k, sd, j: jj, c2, score: Math.abs(k - want) + 0.3 * jj + (c2 ? 0 : 1.5) });
      break;
    }
  }
  return out.sort((p, q) => p.score - q.score);
}
