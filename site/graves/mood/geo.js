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
const DIRS = []; for (let i = 0; i < 8; i++) DIRS.push(new THREE.Vector3(Math.cos(i * Math.PI / 4), 0, Math.sin(i * Math.PI / 4)));

// Look for a peek: P where a head shows from the eye, H one step to the side where all of it is hidden behind a block.
export function findPeek(kr, fr, rng, lo = 12, hi = 30, dbg = null) {
  const D = (k) => { if (dbg) dbg[k] = (dbg[k] || 0) + 1; };
  const found = [], eye = fr.eye;
  let corners = cornersAhead(kr, fr, lo, hi);
  if (corners.length > 4) corners = corners.sort(() => rng() - 0.5).slice(0, 4);
  for (const { c, d } of corners) {
    for (const P of scatter(kr, c)) {
      const dist = Math.hypot(P.x - eye.x, P.z - eye.z);
      if (dist < lo - 1 || dist > hi + 2) { D("range"); continue; }
      const headP = P.clone().setY(P.y + 1.62);
      if (!clear(kr, eye, headP)) { D("headP-blocked"); continue; }
      for (const dv of DIRS) {
        D("tried");
        const H = P.clone().addScaledVector(dv, 1.0);
        if (!standable(kr, H)) { D("H-not-standable"); continue; }
        if (clear(kr, eye, H.clone().setY(H.y + 1.62)) || clear(kr, eye, H.clone().setY(H.y + 0.9)) || clear(kr, eye, H.clone().setY(H.y + 0.3))) { D("H-visible"); continue; }
        // the lean should read from the side: not straight toward or away from the eye
        const toEye = new THREE.Vector3(eye.x - P.x, 0, eye.z - P.z).normalize();
        if (Math.abs(dv.dot(toEye)) > 0.75) { D("lean-axis"); continue; }
        found.push({ P, H, c, d: dist, dir: dv });
      }
    }
  }
  if (!found.length) return null;
  return found[Math.floor(rng() * found.length)];
}

// A floor point near an opening that the eye does NOT see now (mob wait there, unseen).
export function findHidden(kr, fr, rng, lo = 10, hi = 26) {
  const out = [];
  let corners = cornersAhead(kr, fr, lo, hi);
  if (corners.length > 4) corners = corners.sort(() => rng() - 0.5).slice(0, 4);
  for (const { c, d } of corners) {
    for (const P of scatter(kr, c, 5, 1.0)) {
      const dist = Math.hypot(P.x - fr.eye.x, P.z - fr.eye.z);
      if (dist < lo || dist > hi + 2) continue;
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
