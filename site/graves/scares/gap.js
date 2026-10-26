// The failed jumps' shared pieces (Lava fall, Drowned grab).
//   gapSite(R, kind, o)   the gap: the Krypt's own (R.gap: from krypt-gap, or the picker's gap right ahead), or one
//                         the scare digs across the hall in front of you. Local frame (z across the gap): the gap runs
//                         z0..z1 between x0..x1; the liquid's top is at surf. deep: blocks carved under it (a shaft).
//   runUp(R, t, site, o)  the camera from the freeze to the take-off: the last strides, the crouch.
//   firstArms(R, o)       Steve's two arms in the world, shoulder to a hand point: grabbing a rim, reaching up.
import { THREE, clamp, lerp, sstep, tex, loadImg } from "./rig.js";
import { settle } from "./common.js";
import { mcBoxGeometry } from "../../lib/mc/mobs.js";

export const SURF = { lava: -2.12, water: -2.25 };

// The world box of blocks covering a local box (corners at block centres), and the exact local extents of it.
function worldBox(R, lx0, lx1, ly0, ly1, lz0, lz1) {
  const ps = [];
  for (const x of [lx0, lx1]) for (const y of [ly0, ly1]) for (const z of [lz0, lz1]) ps.push(R.L(x, y, z, new THREE.Vector3()));
  const mn = [0, 1, 2].map((i) => Math.floor(Math.min(...ps.map((p) => p.getComponent(i)))));
  const mx = [0, 1, 2].map((i) => Math.floor(Math.max(...ps.map((p) => p.getComponent(i)))));
  const cs = [];
  for (const x of [mn[0], mx[0] + 1]) for (const z of [mn[2], mx[2] + 1]) cs.push(R.toLocal({ x, y: mn[1], z }));
  return { mn, mx, x0: Math.min(...cs.map((c) => c.x)), x1: Math.max(...cs.map((c) => c.x)), z0: Math.min(...cs.map((c) => c.z)), z1: Math.max(...cs.map((c) => c.z)) };
}

export async function gapSite(R, kind, { deep = 0 } = {}) {
  const g = R.gap && R.gap.kind === kind && R.gap.pos ? R.gap : null;
  const surf = SURF[kind] ?? -2.2;
  const xL = -(R.wallL - 0.5), xR = R.wallR - 0.5;
  let site;
  if (g) {
    const gl = R.toLocal(g.pos), w = g.width || 2;
    const b = worldBox(R, xL, xR, -0.5, -0.5, gl.z, gl.z + w - 1);
    site = { own: false, w, z0: b.z0, z1: b.z1, x0: b.x0, x1: b.x1, surf, box: b };
  } else {
    const w = R.chance(0.55) ? 3 : 2, z0 = clamp(R.ahead - w - 1.6, 1.3, 2.2);
    const b = worldBox(R, xL, xR, -0.5, -0.5, z0 + 0.5, z0 + w - 0.5);
    site = { own: true, w, z0: b.z0, z1: b.z1, x0: b.x0, x1: b.x1, surf, box: b };
  }
  const { mn, mx } = site.box, fy = Math.floor(R.O.y - 0.5);   // the floor block's y
  site.carve = () => {
    if (site.own) R.carveW([mn[0], fy - 2, mn[2]], [mx[0], fy, mx[2]]);   // the floor block, the air under it, the liquid's block
    if (deep > 0) R.carveW([mn[0], fy - 3 - deep, mn[2]], [mx[0], fy - 3, mx[2]]);   // under the liquid's block: a shaft
  };
  // The liquid of a gap the scare dug (the Krypt draws its own gaps' liquid).
  const W = site.x1 - site.x0, D = site.z1 - site.z0, cx = (site.x0 + site.x1) / 2, cz = (site.z0 + site.z1) / 2;
  site.cx = cx; site.cz = cz;
  const frames = [];
  const img = await loadImg(kind === "lava" ? "k:lava_still" : "k:water_still");
  if (img) for (let f = 0; f < Math.max(1, Math.floor(img.height / 16)); f++) {
    const c = document.createElement("canvas"); c.width = c.height = 16;
    c.getContext("2d").drawImage(img, 0, f * 16, 16, 16, 0, 0, 16, 16);
    const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.magFilter = t.minFilter = THREE.NearestFilter; t.generateMipmaps = false;
    t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(W, D); frames.push(t);
  }
  // Laid flat (x across, the plane's height along the path), turned to the frame like a mob (R.place).
  const mkPlane = (mat) => { const m = new THREE.Mesh(new THREE.PlaneGeometry(W, D), mat); m.rotation.set(-Math.PI / 2, R.yaw0, 0, "YXZ"); R.at(m, cx, surf, cz); return R.add(m); };
  const top = site.own ? mkPlane(kind === "lava" ? new THREE.MeshBasicMaterial({ map: frames[0] || null, color: 0xffffff }) : new THREE.MeshBasicMaterial({ map: frames[0] || null, color: 0x3a64d8, transparent: true, opacity: 0.75, depthWrite: false })) : null;
  // From under the water: the surface lit from above, a pale rippling sheet (only its underside is drawn).
  const under = kind === "water" ? mkPlane(new THREE.MeshBasicMaterial({ map: frames[0] || null, color: 0x9cc8ff, transparent: true, opacity: 0.85, side: THREE.BackSide, depthWrite: false, fog: false })) : null;
  if (under) under.position.y += 0.01;
  site.animate = (t) => {
    if (!frames.length) return;
    const fr = frames[Math.floor(t * (kind === "lava" ? 10 : 16)) % frames.length];
    if (top) top.material.map = fr;
    if (under) under.material.map = fr;
  };
  site.top = top; site.under = under;
  return site;
}

// From the freeze to the take-off at z = site.z0 - 0.3: the last two or three strides (a little faster than the
// walk), the crouch before the jump. Returns the camera at t (t <= tTake).
export function runUp(R, t, site, { tTake }) {
  const s = settle(R, t, Math.min(0.35, tTake * 0.8));
  const zT = site.z0 - 0.3, k = clamp(t / tTake);
  const c = { x: lerp(s.x, 0, sstep(0, tTake, t)), y: s.y, z: lerp(s.z, zT, k), yaw: s.yaw, pitch: lerp(s.pitch, -0.12, k), roll: 0, fov: s.fov };
  const ph = (t * 4.2) % 1;
  c.y += -0.045 * Math.abs(Math.sin(ph * Math.PI)) - 0.22 * sstep(tTake - 0.28, tTake, t);
  c.roll += 0.012 * Math.sin(t * 4.2 * Math.PI);
  return c;
}

// Steve's arms (first person, in the world): each frame set(i, shoulder, hand) in world coordinates, or hide.
export async function firstArms(R, { emissive = 0.18 } = {}) {
  const skin = await tex("mc:entity/steve");
  const mat = new THREE.MeshLambertMaterial({ map: skin, emissive: new THREE.Color(1, 1, 1), emissiveMap: skin, emissiveIntensity: emissive });
  const geo = mcBoxGeometry([-2, -2, -2, 4, 12, 4, 0], [40, 16], 64, 32, false);
  const arms = [0, 1].map(() => { const g = new THREE.Group(); const m = new THREE.Mesh(geo, mat); g.add(m); g.visible = false; R.add(g); return g; });
  const _d = new THREE.Vector3(), _y = new THREE.Vector3(0, -1, 0);
  return {
    mat,
    set(i, S, H) {
      const g = arms[i]; if (!S) { g.visible = false; return; }
      g.visible = true; g.position.copy(S);
      _d.copy(H).sub(S); const L = _d.length(); _d.normalize();
      g.quaternion.setFromUnitVectors(_y, _d);
      g.scale.set(1, clamp(L / 0.68, 0.7, 1.4), 1);
    },
    hide() { for (const g of arms) g.visible = false; }
  };
}
// The camera's basis in the world (right, up, forward), for placing first-person things.
const _q = new THREE.Quaternion();
export function camBasis(R) {
  _q.copy(R.camera.quaternion);
  return { p: R.camera.position.clone(), r: new THREE.Vector3(1, 0, 0).applyQuaternion(_q), u: new THREE.Vector3(0, 1, 0).applyQuaternion(_q), f: new THREE.Vector3(0, 0, -1).applyQuaternion(_q) };
}
