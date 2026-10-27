// Geometry helpers for the mood events, over window.__krypt (corners, solidAt) and its camera.
import * as THREE from "three";

const _m = new THREE.Matrix4(), _fr = new THREE.Frustum(), _v = new THREE.Vector3();
export const UP = new THREE.Vector3(0, 1, 0);

// The visitor's frame: eye, flat forward, flat right.
export function frameOf(kr) {
  const cam = kr.camera;
  cam.updateMatrixWorld();
  const eye = cam.position.clone();
  const f = new THREE.Vector3(0, 0, -1).applyQuaternion(cam.quaternion);
  const fwd = new THREE.Vector3(f.x, 0, f.z);
  if (fwd.lengthSq() < 1e-4) fwd.set(0, 0, -1);
  fwd.normalize();
  const right = new THREE.Vector3().crossVectors(fwd, UP).normalize();
  return { eye, fwd, right, look: f };
}
// A point in the visitor's frame: f ahead, r to the right, y above the eye.
export function at(fr, f, r, y = 0, out = new THREE.Vector3()) {
  return out.copy(fr.eye).addScaledVector(fr.fwd, f).addScaledVector(fr.right, r).setY(fr.eye.y + y);
}

// True when no solid block lies between a and b.
export function clear(kr, a, b, step = 0.4) {
  const n = Math.max(2, Math.ceil(a.distanceTo(b) / step));
  for (let i = 1; i < n; i++) {
    const t = i / n;
    if (kr.solidAt(a.x + (b.x - a.x) * t, a.y + (b.y - a.y) * t, a.z + (b.z - a.z) * t)) return false;
  }
  return true;
}
// Room for a body at the floor point p: air at the knees and over the head, floor beneath.
export function standable(kr, p, h = 2.0) {
  for (let y = 0.3; y <= h; y += 0.5) if (kr.solidAt(p.x, p.y + y, p.z)) return false;
  return kr.solidAt(p.x, p.y - 0.4, p.z);
}
export function inView(cam, p, margin = 0) {
  cam.updateMatrixWorld();
  _m.multiplyMatrices(cam.projectionMatrix, cam.matrixWorldInverse);
  _fr.setFromProjectionMatrix(_m);
  if (!margin) return _fr.containsPoint(p);
  // inside a slightly shrunk frustum: test through ndc
  _v.copy(p).project(cam);
  return _v.z < 1 && Math.abs(_v.x) < 1 - margin && Math.abs(_v.y) < 1 - margin;
}
// Angle (rad) between the camera's look direction and the direction to p.
export function offAxis(fr, p) {
  _v.copy(p).sub(fr.eye).normalize();
  return Math.acos(Math.max(-1, Math.min(1, _v.dot(fr.look))));
}

// Corners (bends and side passages) ahead of the visitor, in a distance band, nearest first.
export function cornersAhead(kr, fr, lo, hi, kinds) {
  const out = [];
  for (const c of kr.corners || []) {
    if (kinds && c.kind && !kinds.includes(c.kind)) continue;
    _v.copy(c.pos).sub(fr.eye); _v.y = 0;
    const d = _v.length();
    if (d < lo || d > hi) continue;
    if (_v.normalize().dot(fr.fwd) < 0.55) continue;
    out.push({ c, d });
  }
  return out.sort((a, b) => a.d - b.d);
}
export function perp(d) { return new THREE.Vector3(-d.z, 0, d.x); }

// Standable floor points around a corner (its turn or its mouth, and a little way into what lies beyond it).
function scatter(kr, c, r = 5.5, step = 0.8) {
  const d1 = c.dir.clone().setY(0).normalize(), out = [];
  const o = c.pos.clone().addScaledVector(d1, 2);
  for (let x = -r; x <= r; x += step) for (let z = -r; z <= r; z += step) {
    if (x * x + z * z > r * r) continue;
    const P = new THREE.Vector3(o.x + x, c.pos.y, o.z + z);
    if (standable(kr, P)) out.push(P);
  }
  return out;
}
// Standable floor cells in the fan ahead of the eye (not only around corners): the walls, pillars, alcoves, side rooms and
// door frames of the new Krypt all make edges to hide behind. lateral = signed offset from the walking line.
export function fanCells(kr, fr, lo, hi, step = 1, h = 2.0) {
  const out = [], y0 = fr.eye.y - 1.5;
  for (let f = lo - 2; f <= hi + 1; f += step) for (let l = -16; l <= 16; l += step) {
    if (Math.abs(l) > f * 0.85) continue;
    const p = at(fr, f, l, 0); p.y = y0;
    for (const dy of [0, 1, -1]) { const q = p.clone(); q.y = y0 + dy; if (standable(kr, q, h)) { q.lat = l; out.push(q); break; } }
  }
  return out;
}
// A cell that touches a wall, pillar or frame (solid within 0.8 block at chest height): where a body can half-hide.
function hug(kr, q) { const y = q.y + 1.1; return kr.solidAt(q.x + 0.8, y, q.z) || kr.solidAt(q.x - 0.8, y, q.z) || kr.solidAt(q.x, y, q.z + 0.8) || kr.solidAt(q.x, y, q.z - 0.8); }
function shuffled(a, rng) { const b = a.slice(); for (let i = b.length - 1; i > 0; i--) { const j = Math.floor(rng() * (i + 1)); [b[i], b[j]] = [b[j], b[i]]; } return b; }
const DIRS = []; for (let i = 0; i < 8; i++) DIRS.push(new THREE.Vector3(Math.cos(i * Math.PI / 4), 0, Math.sin(i * Math.PI / 4)));

// Torch positions (world), read once from the Krypt's merged torch meshes (20 vertices each) and cached per scene.
let _torch = null;
export function torches(kr) {
  if (_torch && _torch.scene === kr.scene) return _torch.list;
  const list = [];
  kr.scene.traverse((o) => {
    if (!o.isMesh || !o.material || !o.material.map || !o.material.map.image) return;
    if (!/torch_on\.png/.test(o.material.map.image.src || "")) return;
    const pos = o.geometry.attributes.position; if (!pos) return;
    o.updateMatrixWorld();
    for (let i = 0; i + 20 <= pos.count; i += 20) {
      let x = 0, y = 0, z = 0;
      for (let q = 16; q < 20; q++) { x += pos.getX(i + q); y += pos.getY(i + q); z += pos.getZ(i + q); }
      list.push(new THREE.Vector3(x / 4, y / 4, z / 4).applyMatrix4(o.matrixWorld));
    }
  });
  _torch = { scene: kr.scene, list };
  return list;
}
// True when no torch lights this point (torchlight reaches about 7 blocks).
export function dark(kr, p, reach = 7.5) {
  for (const t of torches(kr)) if (Math.hypot(t.x - p.x, t.z - p.z) < reach && Math.abs(t.y - p.y) < 6) return false;
  return true;
}
// Fraction of a body of height h standing at floor point P that the eye can see (18 rays), and whether the head shows.
export function exposure(kr, eye, P, h = 1.8) {
  const toEye = new THREE.Vector3(eye.x - P.x, 0, eye.z - P.z).normalize();
  const side = new THREE.Vector3(-toEye.z, 0, toEye.x);
  let seen = 0, n = 0, head = false;
  for (const fy of [0.1, 0.3, 0.5, 0.7, 0.85, 0.95]) for (const lat of [-0.3, -0.15, 0, 0.15, 0.3]) {
    n++;
    const q = P.clone().addScaledVector(side, lat).setY(P.y + h * fy);
    if (clear(kr, eye, q)) { seen++; if (fy >= 0.85 && lat === 0) head = true; }
  }
  return { frac: seen / n, head };
}

// Look for a peek: P where the head and one shoulder show (at most ~35% of the body), in the dark, 18 to 30 blocks off;
// H a step to the side where all of it is hidden behind a block.
export function findPeek(kr, fr, rng, lo = 15, hi = 30, dbg = null, h = 1.8) {
  // Prefer the darkest spots; in torch-dense halls fall back to spots nearer a torch (the mob carries its own
  // fixed dim light, so the torch only matters for the background), rather than never peeking at all.
  for (const reach of [4, 2.5, 1.2]) { const r = findPeekAt(kr, fr, rng, lo, hi, dbg, h, reach); if (r) return r; }
  return null;
}
function findPeekAt(kr, fr, rng, lo, hi, dbg, h, reach) {
  const D = (k) => { if (dbg) dbg[k] = (dbg[k] || 0) + 1; };
  const found = [], eye = fr.eye;
  let corners = cornersAhead(kr, fr, lo - 3, hi);
  if (corners.length > 4) corners = corners.sort(() => rng() - 0.5).slice(0, 4);
  const sets = corners.map(({ c }) => ({ c, cells: scatter(kr, c, 6, 0.8) }));
  sets.push({ c: { pos: fr.eye, dir: fr.fwd, kind: "edge" }, cells: shuffled(fanCells(kr, fr, lo, hi, 0.5, h).filter((q) => hug(kr, q)), rng) });
  let probed = 0;
  for (const { c, cells } of sets) {
    for (const B of cells) {
      const dist = Math.hypot(B.x - eye.x, B.z - eye.z);
      if (dist < lo - 1.5 || dist > hi + 1) { D("range"); continue; }
      if (!dark(kr, B, reach)) { D("lit"); continue; }
      if (clear(kr, eye, B.clone().setY(B.y + h * 0.95))) { D("B-head-visible"); continue; }
      if (++probed > 160) break;
      if (exposure(kr, eye, B, h).frac > 0) { D("B-visible"); continue; }          // B is the hidden spot
      for (const dv of DIRS) {
        for (const t of [0.12, 0.25, 0.4, 0.55, 0.7, 0.9, 1.1]) {
          D("tried");
          const P = B.clone().addScaledVector(dv, t);
          if (!standable(kr, P)) break;
          const ex = exposure(kr, eye, P, h);
          if (ex.frac > 0.6) break;                       // further out only shows more
          if (ex.head && ex.frac > 0.15) { found.push({ P, H: B.clone(), c, d: dist, dir: dv, frac: ex.frac }); break; }
        }
      }
      if (found.length > 12) break;
    }
  }
  if (!found.length) {
    // From the other end: a floor point whose head shows and whose body mostly does not (an edge of a pillar, door frame or wall),
    // with a spot one step to the side where it is wholly hidden.
    let n = 0;
    const cells = sets.flatMap((x) => x.cells);
    for (const P of shuffled(cells, rng)) {
      const dist = Math.hypot(P.x - eye.x, P.z - eye.z);
      if (dist < lo || dist > hi) continue;
      if (!dark(kr, P, reach)) continue;
      if (!clear(kr, eye, P.clone().setY(P.y + h * 0.95))) continue;
      if (++n > 300) break;
      const ex = exposure(kr, eye, P, h);
      if (!ex.head || ex.frac > 0.6 || ex.frac < 0.15) { D("P-exposure"); continue; }
      for (const dv of DIRS) {
        const H = P.clone().addScaledVector(dv, 1.0);
        if (!standable(kr, H) || exposure(kr, eye, H, h).frac > 0) continue;
        found.push({ P, H, c: sets[0] ? sets[0].c : null, d: dist, dir: dv, frac: ex.frac }); break;
      }
      if (found.length > 8) break;
    }
  }
  if (!found.length) return null;
  return found[Math.floor(rng() * found.length)];
}

// A floor point near an opening that the eye does NOT see now (mob wait there, unseen).
export function findHidden(kr, fr, rng, lo = 10, hi = 26) {
  for (const reach of [6, 3.5, 1.5]) { const r = findHiddenAt(kr, fr, rng, lo, hi, reach); if (r) return r; }
  return null;
}
function findHiddenAt(kr, fr, rng, lo, hi, reach) {
  const out = [];
  let corners = cornersAhead(kr, fr, lo, hi);
  if (corners.length > 4) corners = corners.sort(() => rng() - 0.5).slice(0, 4);
  const sets = corners.map(({ c, d }) => ({ c, d, cells: scatter(kr, c, 5, 1.0) }));
  sets.push({ c: { pos: fr.eye, dir: fr.fwd, kind: "edge" }, d: 0, cells: fanCells(kr, fr, lo, hi, 1).filter((q) => Math.abs(q.lat) >= 1.5) });
  for (const { c, d, cells } of sets) {
    for (const P of cells) {
      const dist = Math.hypot(P.x - fr.eye.x, P.z - fr.eye.z);
      if (dist < lo || dist > hi + 2) continue;
      if (!dark(kr, P, reach)) continue;
      if (clear(kr, fr.eye, P.clone().setY(P.y + 1.5)) || clear(kr, fr.eye, P.clone().setY(P.y + 0.8)) || clear(kr, fr.eye, P.clone().setY(P.y + 0.2))) continue;
      out.push({ P, c, d, dir: c.dir });
    }
  }
  return out.length ? out[Math.floor(rng() * out.length)] : null;
}

// A side opening (passage) that the eye can see into right now, with a low spot to put eyes.
export function findEyesSpot(kr, fr, rng, lo = 7, hi = 28) {
  const out = [];
  for (const { c, d } of cornersAhead(kr, fr, lo, hi)) {
    const d1 = c.dir.clone().setY(0).normalize();
    for (const dep of [2.5, 3.5, 4.5, 6]) {
      const P = c.pos.clone().addScaledVector(d1, dep);
      if (!standable(kr, P, 1.2)) continue;
      const E = P.clone().setY(P.y + 0.5);
      if (!clear(kr, fr.eye, E)) continue;
      out.push({ E, c, d, dir: d1, dep });
    }
  }
  if (!out.length) {   // side rooms, alcoves and door frames: a low spot off the walking line that the eye sees into
    for (const P of fanCells(kr, fr, lo, hi, 1, 1.2)) {
      if (Math.abs(P.lat) < 3.5) continue;
      const E = P.clone().setY(P.y + 0.5);
      if (clear(kr, fr.eye, E)) out.push({ E, c: { kind: "edge" }, d: Math.hypot(P.x - fr.eye.x, P.z - fr.eye.z), dir: new THREE.Vector3(Math.sign(P.lat) * fr.right.x, 0, Math.sign(P.lat) * fr.right.z), dep: 0 });
    }
  }
  return out.length ? out[Math.floor(rng() * out.length)] : null;
}

// Where far-off sounds come from: down a side passage or far along the path, 40 to 130 blocks off.
export function farPoint(kr, fr, rng) {
  const cands = [];
  for (const c of kr.corners || []) {
    _v.copy(c.pos).sub(fr.eye); _v.y = 0;
    const d = _v.length();
    if (d < 38 || d > 140) continue;
    cands.push(c);
  }
  if (cands.length) {
    const c = cands[Math.floor(rng() * cands.length)];
    const off = c.kind === "passage" ? 10 + rng() * 8 : 3;
    return c.pos.clone().addScaledVector(c.dir, off).setY(c.pos.y + 1.2);
  }
  const ang = (rng() - 0.5) * 1.3;
  const d = fr.fwd.clone().applyAxisAngle(UP, ang);
  return fr.eye.clone().addScaledVector(d, 55 + rng() * 25).setY(fr.eye.y - 0.3);
}

// Dump only: a spot near an opening that the eye CAN see now (to show the still creeper as the visitor first meets it).
export function findSeen(kr, fr, rng, lo = 9, hi = 26) {
  const out = [];
  for (const { c, d } of cornersAhead(kr, fr, lo, hi)) {
    for (const P of scatter(kr, c, 5, 1.0)) {
      const dist = Math.hypot(P.x - fr.eye.x, P.z - fr.eye.z);
      if (dist < lo || dist > hi + 2) continue;
      if (clear(kr, fr.eye, P.clone().setY(P.y + 1.0)) && clear(kr, fr.eye, P.clone().setY(P.y + 1.6))) out.push({ P, c, d, dir: c.dir });
    }
  }
  return out.length ? out[Math.floor(rng() * out.length)] : null;
}
