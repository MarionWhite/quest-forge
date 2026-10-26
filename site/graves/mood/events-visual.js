// Visual events: mobs leaning out from behind a corner, spider eyes in a side passage, a creeper standing still in the dark.
// All of them are never explained and never resolved: the visitor never gets a clean look. They retract when the camera
// turns away or comes close, and they only start from a place the eye cannot see now.
import * as THREE from "three";
import { makeMob, whenMobTexturesLoaded } from "../../lib/mc/mobs.js";
import { patchBake } from "../krypt.js";
import { at, clear, inView, offAxis, findPeek, findHidden, findEyesSpot, findSeen, dark } from "./geo.js";

const PEEK_MOB = { peek_zombie: "Zombie", peek_skeleton: "Skeleton", peek_creeper: "Creeper", peek_witch: "Witch", peek_enderman: "Enderman" };
const ease = (x) => { x = Math.max(0, Math.min(1, x)); return x * x * (3 - 2 * x); };

function dressMob(id, amb) {
  let m = null;
  try { m = makeMob(id); } catch (e) { m = null; }
  if (!m) return null;
  const a = new THREE.Vector3(amb, amb * 0.92, amb * 0.9);
  m.root.traverse((o) => {
    if (!o.isMesh || !o.material) return;
    for (const mt of Array.isArray(o.material) ? o.material : [o.material]) {
      if (!mt.isMeshLambertMaterial) continue;
      if (patchBake) patchBake(mt, { fixed: a });
      if (mt.emissive) mt.emissive.setRGB(0.028, 0.032, 0.05);   // a faint cold rim of light, no torchlight on it
    }
  });
  const pivot = new THREE.Group(); pivot.rotation.order = "YXZ"; pivot.add(m.root);
  m.pivot = pivot; pivot.visible = false;
  return m;
}
function faceEye(pivot, eye, roll = 0) {
  const dx = eye.x - pivot.position.x, dz = eye.z - pivot.position.z;
  pivot.rotation.set(0, Math.atan2(-dx, -dz), roll, "YXZ");   // a mob's front is -z
}
function dispose(ctx, m) { if (m && m.pivot) ctx.scene.remove(m.pivot); }

export function peekEvent(ctx, kind) {
  const fr = ctx.frame(), rng = ctx.rng;
  const spot = findPeek(ctx.kr, fr, rng, 18, 30, null, kind === "peek_enderman" ? 2.9 : 1.8);
  if (!spot) return null;
  const m = dressMob(PEEK_MOB[kind], 0.05);
  if (!m) return null;
  ctx.scene.add(m.pivot);
  const { P, H } = spot;
  const hold = 0.6 + rng() * 0.6;
  const cur = H.clone();
  let phase = ctx.dump ? "out" : "armed", t0 = 0, lean = 0, quick = false, retractFrom = 0, armedFor = 0;
  const lateral = Math.sign(((P.x - H.x) * fr.fwd.z - (P.z - H.z) * fr.fwd.x)) || 1;
  let eyes = null;
  if (kind === "peek_enderman") {
    eyes = new THREE.Group();
    for (const dx of [-0.1, 0.1]) { const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: glow(), color: 0xc040ff, blending: THREE.AdditiveBlending, depthWrite: false, transparent: true, fog: false, opacity: 0 })); sp.scale.set(0.2, 0.12, 1); sp.userData.dx = dx; eyes.add(sp); }
    ctx.scene.add(eyes);
  }
  const head = () => cur.clone().setY(cur.y + (kind === "peek_enderman" ? 2.4 : 1.6));
  const ev = {
    dur: 40, ready: whenMobTexturesLoaded(), mob: m, spot,
    update(t, dt) {
      const f = ctx.frame(), hp = head();
      const dist = Math.hypot(P.x - f.eye.x, P.z - f.eye.z);
      if (phase === "armed") {
        armedFor += dt;
        if (armedFor > 16 || dist < 16) return true;
        if (dist <= 31 && dist >= 17 && offAxis(f, hp) < 0.42 && inView(ctx.kr.camera, hp, 0.1)) { phase = "out"; t0 = t; }
      }
      if (phase === "out") {
        lean = ease((t - t0) / 0.8);
        if (lean >= 1) { phase = "hold"; t0 = t; }
      } else if (phase === "hold") {
        lean = 1;
        if (t - t0 > hold) { phase = "back"; t0 = t; retractFrom = 1; }
      } else if (phase === "back") {
        lean = retractFrom * (1 - ease((t - t0) / (quick ? 0.22 : 0.55)));
        if (lean <= 0) { dispose(ctx, m); if (eyes) ctx.scene.remove(eyes); return true; }
      }
      if ((phase === "out" || phase === "hold") && !ctx.dump) {
        if (offAxis(f, hp) > 0.8 || dist < 15) { phase = "back"; t0 = t; retractFrom = lean; quick = true; }
      }
      cur.lerpVectors(H, P, lean);
      cur.y += Math.sin(t * 1.7) * 0.01;
      m.pivot.position.copy(cur);
      faceEye(m.pivot, f.eye, lateral * 0.2 * lean);
      m.pivot.visible = phase !== "armed" && lean > 0.001;
      if (m.anim) m.anim(t, dt, { walk: 0 });
      if (eyes) {
        const r = f.right, q = ev.mob.pivot.position, toE = new THREE.Vector3(f.eye.x - q.x, 0, f.eye.z - q.z).normalize();
        for (const sp of eyes.children) { sp.position.set(q.x + r.x * sp.userData.dx + toE.x * 0.28, q.y + 2.52, q.z + r.z * sp.userData.dx + toE.z * 0.28); sp.material.opacity = m.pivot.visible ? 0.95 * Math.min(1, lean * 1.5) : 0; }
      }
      return false;
    },
    stop() { dispose(ctx, m); if (eyes) ctx.scene.remove(eyes); }
  };
  return ev;
}

// A creeper that stands perfectly still in the dark. It is gone the next time it is in view.
export function stillEvent(ctx) {
  const fr = ctx.frame(), rng = ctx.rng;
  const spot = ctx.dump ? findSeen(ctx.kr, fr, rng, 9, 26) : findHidden(ctx.kr, fr, rng, 14, 28);
  if (!spot) return null;
  const m = dressMob("Creeper", 0.045);
  if (!m) return null;
  ctx.scene.add(m.pivot);
  m.pivot.position.copy(spot.P);
  const centre = spot.P.clone().setY(spot.P.y + 0.9);
  let seen = false, gone = 0, age = 0;
  return {
    dur: 60, ready: whenMobTexturesLoaded(), mob: m, spot,
    update(t, dt) {
      age += dt;
      const f = ctx.frame();
      faceEye(m.pivot, f.eye);
      m.pivot.visible = true;
      if (m.anim) m.anim(0, 0, { walk: 0 });                      // perfectly still: the pose never advances
      if (ctx.dump) return false;
      const dist = f.eye.distanceTo(centre);
      const vis = dist < 40 && inView(ctx.kr.camera, centre, 0.04) && clear(ctx.kr, f.eye, centre) ;
      if (vis) { seen = true; gone = 0; }
      else if (seen) { gone += dt; if (gone > 0.12) { dispose(ctx, m); return true; } }
      if (age > 50) { dispose(ctx, m); return true; }
      return false;
    },
    stop() { dispose(ctx, m); }
  };
}

let glowTex = null;
function glow() {
  if (glowTex) return glowTex;
  const c = document.createElement("canvas"); c.width = c.height = 64;
  const g = c.getContext("2d"), r = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  r.addColorStop(0, "rgba(255,235,210,1)"); r.addColorStop(0.18, "rgba(255,70,40,0.95)"); r.addColorStop(0.5, "rgba(190,15,10,0.35)"); r.addColorStop(1, "rgba(120,0,0,0)");
  g.fillStyle = r; g.fillRect(0, 0, 64, 64);
  glowTex = new THREE.CanvasTexture(c);
  return glowTex;
}

// Spider eyes: glow in a side passage for a moment and go dark.
export function eyesEvent(ctx) {
  const fr = ctx.frame(), rng = ctx.rng;
  const spot = findEyesSpot(ctx.kr, fr, rng, 7, 28);
  if (!spot) return null;
  const grp = new THREE.Group(), sprites = [];
  const mk = (dx, dy, s) => {
    const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: glow(), color: 0xffffff, blending: THREE.AdditiveBlending, depthWrite: false, transparent: true, fog: false, opacity: 0 }));
    sp.scale.set(s, s, 1); sp.userData = { dx, dy }; grp.add(sp); sprites.push(sp);
  };
  mk(-0.11, 0, 0.34); mk(0.11, 0, 0.34); mk(-0.05, 0.1, 0.18); mk(0.05, 0.1, 0.18); mk(-0.19, 0.05, 0.11); mk(0.19, 0.05, 0.11);
  grp.position.copy(spot.E);
  ctx.scene.add(grp);
  const hold = 1.3 + rng() * 0.9, blinkAt = 0.5 + rng() * 0.5;
  let phase = ctx.dump ? "on" : "armed", t0 = 0, armedFor = 0;
  const set = (a) => { const r = ctx.frame().right; for (const s of sprites) { s.material.opacity = a; s.position.set(s.userData.dx * r.x, s.userData.dy, s.userData.dx * r.z); } };
  return {
    dur: 30, spot, ready: Promise.resolve(),
    update(t, dt) {
      const f = ctx.frame(), dist = f.eye.distanceTo(spot.E);
      if (phase === "armed") {
        armedFor += dt;
        if (armedFor > 12 || dist < 7) { ctx.scene.remove(grp); return true; }
        if (dist < 29 && offAxis(f, spot.E) < 0.5 && inView(ctx.kr.camera, spot.E, 0.12) && clear(ctx.kr, f.eye, spot.E)) { phase = "on"; t0 = t; }
        else return false;
      }
      const a = t - t0;
      let o = ease(a / 0.35);
      if (a > blinkAt && a < blinkAt + 0.13) o = 0;                 // one blink
      if (a >= hold || (!ctx.dump && (dist < 6.5 || offAxis(f, spot.E) > 1.0))) { ctx.scene.remove(grp); return true; }
      set(o * (0.9 + 0.1 * Math.sin(t * 9)));
      return false;
    },
    stop() { ctx.scene.remove(grp); }
  };
}
