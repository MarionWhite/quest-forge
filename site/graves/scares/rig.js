// The scare rig: a scare plays inside the real Krypt (window.__krypt.scene), where the visitor stands.
// The Krypt keeps rendering while it is taken over; the rig hooks scene.onBeforeRender, so every frame the Krypt
// draws is evaluated at the scare's clock: the head camera, the mobs, the darkness, the overlay.
//
//   const R = await createRig(kr)        captures the camera, finds the floor, the heading and the walls
//   R.L(x, y, z)                          local -> world. x right, y up from the floor, z forward along the corridor
//   R.mob(id) / R.place(m, x, y, z, yaw)  a library mob, lit like the Krypt's figures; yaw is local (0 = facing forward)
//   R.burst(t0, [x,y,z], n, kind, o)      blocky gore, a pure function of time
//   R.evaluate(S, t) -> f                 one frame of the scare S (from its module's build(R)) at time t
//   R.dispose()                           puts the Krypt back exactly as it was
import * as THREE from "three";
import * as KR from "../krypt.js";
import { makeMob, whenMobTexturesLoaded } from "../../lib/mc/mobs.js";
import { itemTone } from "../../lib/mc/equipment.js";
import { SLOTS, heldAt, slotOf } from "./loadout.js";
import { ShaderPass } from "three/addons/postprocessing/ShaderPass.js";

export { THREE };
export const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
export const lerp = (a, b, k) => a + (b - a) * k;
export const sstep = (a, b, x) => { const k = clamp((x - a) / (b - a)); return k * k * (3 - 2 * k); };
export const easeOut = (k) => 1 - Math.pow(1 - clamp(k), 3);
export const easeIn = (k) => Math.pow(clamp(k), 3);
export function rngOf(seed) {
  let a = seed >>> 0;
  return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
// Exponential decay pulses after each time in a list (a hit, a flash).
export function pulse(t, times, tau = 0.15) {
  let v = 0;
  for (const h of times) if (t >= h) v = Math.max(v, Math.exp(-(t - h) / tau));
  return v;
}
// A keyframed value: keys [[t, v, ease?], ...]; ease names the curve INTO that key:
// s smoothstep (default), l linear, o ease-out, i ease-in, h hold (jumps at the key), x snap (very fast ease-out).
const EASE = { s: (k) => k * k * (3 - 2 * k), l: (k) => k, o: easeOut, i: easeIn, h: (k) => (k < 1 ? 0 : 1), x: (k) => 1 - Math.pow(1 - k, 6) };
export function track(keys) {
  return (t) => {
    if (t <= keys[0][0]) return keys[0][1];
    for (let i = 1; i < keys.length; i++) {
      const [t1, v1, e] = keys[i];
      if (t <= t1) {
        const [t0, v0] = keys[i - 1];
        const k = (EASE[e || "s"])(clamp((t - t0) / Math.max(1e-6, t1 - t0)));
        return v0 + (v1 - v0) * k;
      }
    }
    return keys[keys.length - 1][1];
  };
}
// Smooth value noise for hand-held shake.
export function wobble(t, seed = 0) { return Math.sin(t * 13.1 + seed) * 0.5 + Math.sin(t * 29.7 + seed * 2.1) * 0.3 + Math.sin(t * 51.3 + seed * 3.7) * 0.2; }

// ---- textures ------------------------------------------------------------------------------------
const TEX_SCARE = new URL("../tex/scare/", import.meta.url), TEX_K = new URL("../tex/", import.meta.url);
const texCache = new Map(), imgCache = new Map();
export function loadImg(name) {
  if (!imgCache.has(name)) {
    const url = name.startsWith("k:") ? new URL(name.slice(2) + ".png", TEX_K).href : name.startsWith("mc:") ? new URL("../../lib/mc/tex/" + name.slice(3) + ".png", import.meta.url).href : new URL(name + ".png", TEX_SCARE).href;
    imgCache.set(name, new Promise((res) => { const im = new Image(); im.onload = () => res(im); im.onerror = () => res(null); im.src = url; }));
  }
  return imgCache.get(name);
}
export async function tex(name, { repeat = false } = {}) {
  const key = name + (repeat ? "|r" : "");
  if (!texCache.has(key)) {
    texCache.set(key, loadImg(name).then((im) => {
      if (!im) return null;
      const t = new THREE.Texture(im);
      t.colorSpace = THREE.SRGBColorSpace; t.magFilter = THREE.NearestFilter; t.minFilter = THREE.NearestFilter; t.generateMipmaps = false;
      if (repeat) t.wrapS = t.wrapT = THREE.RepeatWrapping;
      t.needsUpdate = true; return t;
    }));
  }
  return texCache.get(key);
}
// The Krypt's block names (blockAt) to texture files in graves/tex.
const BLOCK_TEX = { stone: "stone", cobblestone: "cobblestone", mossy_cobblestone: "cobblestone_mossy", stonebrick: "stonebrick",
  mossy_stonebrick: "stonebrick_mossy", cracked_stonebrick: "stonebrick_cracked", gravel: "gravel", coal_ore: "coal_ore", iron_ore: "iron_ore",
  obsidian: "obsidian", bedrock: "bedrock", netherrack: "netherrack", glowstone: "glowstone", nether_brick: "nether_brick", soul_sand: "soul_sand",
  bookshelf: "planks_oak", planks: "planks_oak", log: "log_oak", dirt: "dirt" };
export const blockTexName = (b) => "k:" + (BLOCK_TEX[b] || "stone");

// ---- gore: instanced cubes on parabolas, each a pure function of time ------------------------------------
const PALETTE = {
  blood: [0x8a0303, 0xb30808, 0x5c0000, 0xd01010, 0x6e0202], stone: [0x7d7d7d, 0x6a6a6a, 0x555555, 0x8e8e8e],
  green: [0x5dbb2a, 0x7ee03a, 0x3c8a1a], purple: [0xcc44ff, 0x7a1fb8, 0xe9a6ff], fire: [0xffd040, 0xff8a10, 0xff4a00],
  lava: [0xff6a10, 0xc03a00, 0xffb030], bone: [0xe8e8e0, 0xc8c8c0, 0xa8a8a0], white: [0xffffff, 0xdddddd], dust: [0x4a4038, 0x6a5e50, 0x302820],
  smoke: [0x222222, 0x333333, 0x111111], spark: [0xfff2a0, 0xffd040, 0xffffff], soot: [0x1a1a1a, 0x0a0a0a, 0x2a2420], flesh: [0x7a1a10, 0x9a2a1a, 0x5a1008]
};
class Gore {
  constructor(max, rng) {
    this.max = max; this.list = []; this.rng = rng;
    const mat = new THREE.MeshBasicMaterial({ color: 0xffffff });
    this.mesh = new THREE.InstancedMesh(new THREE.BoxGeometry(1, 1, 1), mat, max);
    this.mesh.frustumCulled = false;
    this.mesh.instanceColor = new THREE.InstancedBufferAttribute(new Float32Array(max * 3), 3);
    this.mesh.count = 0;
    this.m4 = new THREE.Matrix4(); this.q = new THREE.Quaternion(); this.col = new THREE.Color(); this.p = new THREE.Vector3(); this.s = new THREE.Vector3();
  }
  burst(t0, o, n, kind = "blood", { dir = [0, 1, 0], spread = 1, speed = 3, size = 0.07, life = 1.6, grav = 9, floor = -1e9, stick = 0 } = {}) {
    const R = this.rng, pal = PALETTE[kind] || PALETTE.blood;
    for (let i = 0; i < n && this.list.length < this.max; i++) {
      const v = [(R() - .5) * 2 * spread + dir[0], (R() - .5) * 2 * spread + dir[1], (R() - .5) * 2 * spread + dir[2]];
      const sp = speed * (0.4 + R() * 0.9);
      this.list.push({ t0: t0 + R() * 0.04, p: o.slice(), v: v.map((x) => x * sp), s: size * (0.5 + R() * 1.1), life: life * (0.6 + R() * 0.6), c: pal[(R() * pal.length) | 0], g: grav, f: floor, r: R() * 6, stick });
    }
  }
  update(t) {
    const L = this.list; let k = 0;
    for (const p of L) {
      const d = t - p.t0;
      if (d < 0 || d > p.life + p.stick) continue;
      let y = p.p[1] + p.v[1] * d - 0.5 * p.g * d * d, x = p.p[0] + p.v[0] * d, z = p.p[2] + p.v[2] * d;
      let landed = false;
      if (y < p.f) {   // on the floor: it stays where it landed
        const a = p.g / 2, b = -p.v[1], c = p.f - p.p[1];
        const disc = b * b - 4 * a * c, tl = disc > 0 ? (-b + Math.sqrt(disc)) / (2 * a) : d;
        x = p.p[0] + p.v[0] * tl; z = p.p[2] + p.v[2] * tl; y = p.f; landed = true;
      }
      this.q.setFromAxisAngle(THREE.Object3D.DEFAULT_UP, p.r + (landed ? 0 : d * 4));
      const fade = d > p.life ? 1 - (d - p.life) / Math.max(0.01, p.stick) : 1;
      const sc = p.s * (landed ? 1 : 1) * clamp(fade);
      this.m4.compose(this.p.set(x, y + (landed ? sc * 0.3 : 0), z), this.q, this.s.set(sc, landed ? sc * 0.35 : sc, sc));
      this.mesh.setMatrixAt(k, this.m4);
      this.col.setHex(p.c); this.mesh.setColorAt(k, this.col);
      k++;
    }
    this.mesh.count = k;
    this.mesh.instanceMatrix.needsUpdate = true;
    if (this.mesh.instanceColor) this.mesh.instanceColor.needsUpdate = true;
  }
}

// ---- the rig ----------------------------------------------------------------------------------------
const _v = new THREE.Vector3(), _q = new THREE.Quaternion(), _e = new THREE.Euler(0, 0, 0, "YXZ"), _m = new THREE.Matrix4(), _m2 = new THREE.Matrix4();

// opts: seed (the scare's look), rand (this play's dice: a different build-up every time; fixed in dumps),
// frame { dir } (a heading to use instead of the last bend's: a gap's jump direction), gap (the Krypt's gap).
export async function createRig(kr, { seed = 1, rand = seed * 7919 + 13, frame = null, gap = null } = {}) {
  const scene = kr.scene, camera = kr.camera;
  const R = { kr, scene, camera, THREE, eye: 1.62, seed, patchBake: KR.patchBake, gap };
  // The dice: R.rand() 0..1, R.vary(x, f) = x +- f (40% by default), R.chance(p), R.pick(list).
  let mix = Math.imul((rand >>> 0) ^ 0x9e3779b9, 0x85ebca6b); mix = Math.imul(mix ^ (mix >>> 13), 0xc2b2ae35); mix ^= mix >>> 16;
  R.rand = rngOf(mix >>> 0);
  R.vary = (x, f = 0.4) => x * (1 + (R.rand() * 2 - 1) * f);
  R.chance = (p) => R.rand() < p;
  R.pick = (list) => list[Math.floor(R.rand() * list.length) % list.length];
  const solidW = typeof kr.solidAt === "function" ? (x, y, z) => !!kr.solidAt(x, y, z) : () => false;
  const blockW = typeof kr.blockAt === "function" ? (x, y, z) => kr.blockAt(x, y, z) : () => "stone";
  R.solidW = solidW; R.blockW = blockW;

  // The camera as the scare found it, to put back exactly.
  const cam0 = { pos: camera.position.clone(), quat: camera.quaternion.clone(), fov: camera.fov, near: camera.near };
  R.cam0 = cam0;

  // Heading: the last bend before the walk's position sets the leg's direction (legs run N, W or E).
  const walk = kr.getWalk ? kr.getWalk() : { s: 0, segment: "crypt" };
  R.walk = walk; R.seg = walk.segment || "crypt"; R.depth = walk.depth ?? walk.s ?? 0;
  let head = new THREE.Vector3(0, 0, -1);
  const bends = (kr.corners || []).filter((c) => c.kind !== "passage" && c.s != null && c.s <= walk.s + 1e-4).sort((a, b) => a.s - b.s);
  if (bends.length) head.copy(bends[bends.length - 1].dir).setY(0).normalize();
  // Near a bend the corridor ahead may already be the next leg: if the camera looks much more along the next leg, use it.
  const next = (kr.corners || []).filter((c) => c.kind !== "passage" && c.s != null && c.s > walk.s).sort((a, b) => a.s - b.s)[0];
  const look = new THREE.Vector3(0, 0, -1).applyQuaternion(cam0.quat).setY(0).normalize();
  if (next && next.pos.distanceTo(cam0.pos) < 4.5 && look.dot(next.dir) > look.dot(head) + 0.3) head.copy(next.dir).setY(0).normalize();
  if (frame && frame.dir) head.set(frame.dir.x, 0, frame.dir.z).normalize();
  // Snap to the block axes.
  if (Math.abs(head.x) > Math.abs(head.z)) head.set(Math.sign(head.x), 0, 0); else head.set(0, 0, Math.sign(head.z) || -1);
  const f = head, r = new THREE.Vector3(-f.z, 0, f.x);
  R.f = f; R.r = r; R.yaw0 = Math.atan2(-f.x, -f.z);

  // The floor under the camera and the ceiling over it.
  const cx = cam0.pos.x, cz = cam0.pos.z;
  let fy = Math.floor(cam0.pos.y);
  for (let n = 0; n < 8 && !solidW(cx, fy, cz); n++) fy--;
  if (!solidW(cx, fy, cz)) fy = Math.floor(cam0.pos.y - 1.5);
  const floorY = fy + 1;
  let cy = Math.floor(cam0.pos.y);
  for (let n = 0; n < 14 && !solidW(cx, cy, cz); n++) cy++;
  R.O = new THREE.Vector3(cx, floorY, cz);
  R.debug = { cam: cam0.pos.toArray().map((v) => +v.toFixed(3)), fy, cy, solidHere: solidW(cx, cam0.pos.y, cz), solidBelow: solidW(cx, cam0.pos.y - 2, cz), hasSolid: typeof kr.solidAt, src: String(kr.solidAt).slice(0, 80) };
  R.ceil = cy - floorY;   // air height over the feet

  // Local <-> world.
  R.L = (x, y, z, out = new THREE.Vector3()) => out.set(R.O.x + r.x * x + f.x * z, R.O.y + y, R.O.z + r.z * x + f.z * z);
  R.Larr = (x, y, z) => { const v = R.L(x, y, z, _v); return [v.x, v.y, v.z]; };
  R.Lp = (x, y, z) => { const v = R.L(x, y, z, _v); return { x: v.x, y: v.y, z: v.z }; };
  R.toLocal = (w) => { const dx = w.x - R.O.x, dz = w.z - R.O.z; return { x: dx * r.x + dz * r.z, y: w.y - R.O.y, z: dx * f.x + dz * f.z }; };
  R.dirW = (x, y, z) => [r.x * x + f.x * z, y, r.z * x + f.z * z];
  R.solid = (x, y, z) => { const v = R.L(x, y, z, _v); return solidW(v.x, v.y, v.z); };
  R.block = (x, y, z) => { const v = R.L(x, y, z, _v); return blockW(v.x, v.y, v.z); };
  // March from a local point along a local direction; the distance to the first solid block (or max).
  R.ray = (x, y, z, dx, dy, dz, max = 24, step = 0.1) => {
    const n = Math.hypot(dx, dy, dz) || 1; dx /= n; dy /= n; dz /= n;
    for (let d = 0; d <= max; d += step) if (R.solid(x + dx * d, y + dy * d, z + dz * d)) return d;
    return max;
  };
  // The start of the head, in local terms.
  const lp = R.toLocal(cam0.pos);
  const lookF = new THREE.Vector3(0, 0, -1).applyQuaternion(cam0.quat);
  const lf = { x: lookF.x * r.x + lookF.z * r.z, z: lookF.x * f.x + lookF.z * f.z };
  R.start = { x: lp.x, y: lp.y, z: lp.z, yaw: Math.atan2(-lf.x, lf.z), pitch: Math.asin(clamp(lookF.y, -1, 1)), fov: cam0.fov };

  // The corridor around the visitor: walls, length, openings (alcoves and passages) on either side.
  const eyeY = 1.5;
  R.wallL = R.ray(0, eyeY, 0, -1, 0, 0, 16); R.wallR = R.ray(0, eyeY, 0, 1, 0, 0, 16);
  R.ahead = R.ray(0, eyeY, 0, 0, 0, 1, 40); R.behind = R.ray(0, eyeY, 0, 0, 0, -1, 40);
  R.openings = [];
  for (const side of [-1, 1]) {
    const base = side < 0 ? R.wallL : R.wallR;
    let run = null;
    for (let z = -10; z <= 16; z += 0.5) {
      const d = R.ray(0, 1.0, z, side, 0, 0, 16);
      const open = d > base + 1.2;
      if (open && !run) run = { side, z0: z, z1: z, depth: d };
      else if (open && run) { run.z1 = z; run.depth = Math.max(run.depth, d); }
      else if (!open && run) { R.openings.push(run); run = null; }
    }
    if (run) R.openings.push(run);
  }
  for (const o of R.openings) { o.z = (o.z0 + o.z1) / 2; o.wall = o.side < 0 ? R.wallL : R.wallR; o.passage = o.depth - o.wall > 4; }
  // The side passage nearest the visitor (the Krypt's corners list knows them), as local mouth + inward direction.
  R.passages = (kr.corners || []).filter((c) => c.kind === "passage").map((c) => {
    const m = R.toLocal(c.pos); return { ...m, dist: Math.hypot(m.x, m.z), side: Math.sign(m.x) || 1 };
  }).filter((p) => p.dist < 18).sort((a, b) => a.dist - b.dist);
  // The Krypt's baked light on a block face (its chunk's per-vertex 'bake'), so a block of ours matches the wall.
  // p: the face centre (world), n: its normal (world). Returns a Vector3 or null.
  const _bb = new THREE.Box3(), _bv = new THREE.Vector3(), _bn = new THREE.Vector3();
  R.bakeAt = (p, n) => {
    const sum = new THREE.Vector3(); let cnt = 0;
    scene.traverse((o) => {
      const g = o.isMesh && o.geometry, bk = g && g.attributes.bake;
      if (!bk) return;
      if (!g.boundingBox) g.computeBoundingBox();
      o.updateMatrixWorld();
      if (_bb.copy(g.boundingBox).applyMatrix4(o.matrixWorld).distanceToPoint(p) > 1) return;
      const pos = g.attributes.position, nrm = g.attributes.normal;
      for (let i = 0; i < pos.count; i++) {
        _bv.fromBufferAttribute(pos, i).applyMatrix4(o.matrixWorld);
        if (Math.abs(_bv.x - p.x) > 0.51 || Math.abs(_bv.y - p.y) > 0.51 || Math.abs(_bv.z - p.z) > 0.51) continue;
        if (n && nrm && _bn.fromBufferAttribute(nrm, i).dot(n) < 0.9) continue;
        sum.x += bk.getX(i); sum.y += bk.getY(i); sum.z += bk.getZ(i); cnt++;
      }
    });
    return cnt ? sum.multiplyScalar(1 / cnt) : null;
  };
  // The floor block under the feet (for dressing a pit like the segment) and the wall block beside.
  R.floorBlock = blockW(cx, floorY - 0.5, cz);
  R.wallBlockL = R.block(-(R.wallL + 0.5), 1.5, 0); R.wallBlockR = R.block(R.wallR + 0.5, 1.5, 0);

  // Torches near the visitor, from the Krypt's merged torch mesh (20 vertices each).
  R.torches = [];
  scene.traverse((o) => {
    if (!o.isMesh || !o.material || !o.material.map || !o.material.map.image) return;
    const src = o.material.map.image.src || "";
    if (!/torch_on\.png/.test(src)) return;
    const pos = o.geometry.attributes.position; if (!pos) return;
    o.updateMatrixWorld();
    for (let i = 0; i + 20 <= pos.count; i += 20) {
      let x = 0, y = 0, z = 0;
      for (let q = 16; q < 20; q++) { x += pos.getX(i + q); y += pos.getY(i + q); z += pos.getZ(i + q); }
      const w = new THREE.Vector3(x / 4, y / 4, z / 4).applyMatrix4(o.matrixWorld);
      const l = R.toLocal(w);
      if (Math.hypot(l.x, l.z) < 26 && Math.abs(l.y) < 7) R.torches.push({ mesh: o, i, w, l, out: false });
    }
  });
  R.torches.sort((a, b) => a.l.z - b.l.z);

  // Everything the scare adds lives in one group. It stays hidden until the scare's first frame has placed everything
  // (R.evaluate): the Krypt keeps rendering while the scare builds, loads and warms up, and without this every mob stood
  // for a few frames wherever its build left it, in front of you, and then vanished (the owner, round 8b: "the mob will
  // flash on the screen in front of me, and disappear").
  const group = new THREE.Group(); group.name = "scare"; group.visible = false; scene.add(group);
  const view = new THREE.Group(); view.name = "scare-view"; group.add(view);
  R.group = group; R.view = view;
  R.add = (o) => { group.add(o); return o; };
  R.gore = new Gore(1400, rngOf(seed * 7 + 3)); group.add(R.gore.mesh);
  R.burst = (t0, p, n, kind, o = {}) => {
    const w = R.Larr(p[0], p[1], p[2]);
    const d = o.dir ? R.dirW(o.dir[0], o.dir[1], o.dir[2]) : [0, 1, 0];
    R.gore.burst(t0, w, n, kind, { ...o, dir: d, floor: o.floor != null ? R.O.y + o.floor : R.O.y + 0.02 });
  };
  R.light = (color, intensity = 1, dist = 8, decay = 1.6) => { const l = new THREE.PointLight(color, intensity, dist, decay); group.add(l); return l; };
  R.at = (obj, x, y, z) => { R.L(x, y, z, obj.position); return obj; };

  // Mobs: the library's model, lit by a fixed ambient (like the Krypt's figures) that follows the bake gain.
  const mobs = [];
  R.mob = (id, opts = {}) => {
    let m = null;
    try { m = makeMob(id, opts); } catch (e) { m = null; }
    if (!m) m = makeMob("Zombie", opts);
    const amb = new THREE.Vector3(...(opts.amb || [0.32, 0.28, 0.26]));
    m.amb = amb;
    const held = new Set();   // the held item's materials (equipment.js tags its holder)
    m.root.traverse((o) => { if (o.userData && o.userData.qfHeld) o.traverse((x) => { if (x.isMesh && x.material) for (const mt of [].concat(x.material)) held.add(mt); }); });
    // opts.own: an ambient of its own that the darkness (the bake gain) does not touch, for the one the scene is about.
    m.root.traverse((o) => {
      if (!o.isMesh || !o.material) return;
      const ms = Array.isArray(o.material) ? o.material : [o.material];
      for (const mt of ms) {
        if (!mt.isMeshLambertMaterial) continue;
        if (opts.own) { mt.emissive = new THREE.Color(1, 1, 1); mt.emissiveMap = mt.map; mt.emissiveIntensity = amb.x; m.ownMats = (m.ownMats || []).concat(mt); }
        else if (KR.patchBake) KR.patchBake(mt, { fixed: amb });
        if (held.has(mt)) heldLight(mt);
      }
    });
    m.setOwn = (v) => { for (const mt of m.ownMats || []) mt.emissiveIntensity = v; };
    const pivot = new THREE.Group(); pivot.rotation.order = "YXZ"; pivot.add(m.root);
    pivot.userData.qfMob = id;   // (for the flow check's J-press watch)
    m.pivot = pivot; group.add(pivot); mobs.push(m);
    return m;
  };
  R.place = (m, x, y, z, yaw = 0, pitch = 0, roll = 0) => {
    const p = m.pivot || m; R.L(x, y, z, p.position); p.rotation.set(pitch, R.yaw0 + yaw, roll, "YXZ"); return m;
  };
  // Local yaw from (x, z) looking at (tx, tz): the yaw a mob or the head needs.
  R.yawTo = (x, z, tx, tz) => Math.atan2(-(tx - x), tz - z);
  R.pitchTo = (x, y, z, tx, ty, tz) => Math.atan2(ty - y, Math.hypot(tx - x, tz - z));
  // A mob at (x, z) facing (tx, tz): its front is -z of its model, the same as the camera's, so it looks back along yaw + PI.
  R.faceYaw = (x, z, tx, tz) => R.yawTo(x, z, tx, tz);
  R.flash = (m, amt) => {   // the 1.7.10 hurt tint on a mob: red over the texture (and over its own light)
    const g = 1 - 0.6 * amt;
    m.root.traverse((o) => {
      if (!o.isMesh || !o.material) return;
      const ms = Array.isArray(o.material) ? o.material : [o.material];
      for (const mt of ms) {
        if (mt.userData.noFlash || mt.blending !== THREE.NormalBlending || !mt.color) continue;
        mt.color.setRGB(1, g, g);
        if (mt.emissiveMap && mt.emissive) mt.emissive.setRGB(1, g, g);
      }
    });
  };

  // ---- the Krypt's lights, particles and torches while the scare runs -------------------------------------
  R.env = null;
  const snuffed = new Map();   // mesh -> original position array copy
  R.snuff = (tc) => {
    if (tc.out) return; tc.out = true;
    const pos = tc.mesh.geometry.attributes.position;
    if (!snuffed.has(tc.mesh)) snuffed.set(tc.mesh, pos.array.slice());
    for (let q = 0; q < 20; q++) pos.setXYZ(tc.i + q, 0, -9999, 0);
    pos.needsUpdate = true;
  };
  R.unsnuff = (tc) => {   // that one torch lights again
    if (!tc.out) return; tc.out = false;
    const arr = snuffed.get(tc.mesh); if (!arr) return;
    const pos = tc.mesh.geometry.attributes.position;
    for (let q = 0; q < 20; q++) { const j = (tc.i + q) * 3; pos.setXYZ(tc.i + q, arr[j], arr[j + 1], arr[j + 2]); }
    pos.needsUpdate = true;
  };
  R.unsnuffAll = () => {
    for (const [mesh, arr] of snuffed) { const pos = mesh.geometry.attributes.position; pos.array.set(arr); pos.needsUpdate = true; }
    snuffed.clear(); for (const tc of R.torches) tc.out = false;
  };
  const myLights = new Set();
  const kryptLights = [], kryptPoints = [];
  scene.traverse((o) => { if (o.isPointLight || o.isSpotLight || o.isHemisphereLight) kryptLights.push(o); if (o.isPoints && o.geometry.attributes.alpha) kryptPoints.push(o); });
  const base = { bake: KR.bakeUniform ? KR.bakeUniform.value : 1 };

  // The scare's own post pass, before the Krypt's output pass: screen tear (bands of the frame thrown sideways),
  // an RGB split, and TV static. Off (skipped by the composer) unless a frame asks for it (f.fx).
  const fxPass = new ShaderPass({
    uniforms: { tDiffuse: { value: null }, tear: { value: 0 }, split: { value: 0 }, stat: { value: 0 }, seed: { value: 0 }, res: { value: new THREE.Vector2(1, 1) } },
    vertexShader: "varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }",
    fragmentShader: `uniform sampler2D tDiffuse; uniform float tear, split, stat, seed; uniform vec2 res; varying vec2 vUv;
      float h(vec2 p){ return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
      void main(){
        vec2 uv = vUv;
        float band = floor(uv.y * 18.0 + h(vec2(seed, 3.1)) * 18.0);
        float r = h(vec2(band, seed));
        float sh = (r > 0.62 ? (r - 0.62) * 2.6 : 0.0) * tear * 0.22 * (h(vec2(band, seed + 7.0)) > 0.5 ? 1.0 : -1.0);
        sh += tear * 0.012 * (h(vec2(floor(uv.y * res.y / 3.0), seed)) - 0.5);
        float roll = step(0.985, fract(uv.y * 0.7 + seed * 0.37)) * tear;
        uv.x = fract(uv.x + sh + roll * 0.05);
        float s = split * 0.014;
        vec3 c = vec3(texture2D(tDiffuse, uv + vec2(s, 0.0)).r, texture2D(tDiffuse, uv).g, texture2D(tDiffuse, uv - vec2(s, s * 0.3)).b);
        vec2 g = floor(vUv * res / 3.0);
        float n = h(g + vec2(seed * 13.7, seed * 7.3));
        n = mix(n, h(vec2(g.y, seed)), 0.35);
        c = mix(c, vec3(n * n * 0.9), clamp(stat, 0.0, 1.0));
        c *= 1.0 - 0.25 * roll;
        gl_FragColor = vec4(c, 1.0);
      }`
  });
  fxPass.enabled = false;
  const comp = kr.composer;
  if (comp && comp.passes && comp.insertPass) { try { comp.insertPass(fxPass, Math.max(0, comp.passes.length - 1)); } catch (e) { /* no composer */ } }
  R.fxPass = fxPass;

  // Apply the frame's environment just before the Krypt's scene renders (the Krypt has just set its own values).
  function applyEnv(env, fx, t) {
    const on = !R.noFx && !!fx && (fx.tear > 0.003 || fx.split > 0.003 || fx.stat > 0.003);
    fxPass.enabled = on;
    if (on) {
      const u = fxPass.uniforms;
      u.tear.value = fx.tear || 0; u.split.value = fx.split || 0; u.stat.value = fx.stat || 0; u.seed.value = Math.floor((t || 0) * 30) % 997 + 0.5;
      const rr = kr.renderer; if (rr) { rr.getDrawingBufferSize(u.res.value); }
    }
    const rr = kr.renderer;
    if (KR.bakeUniform) KR.bakeUniform.value = base.bake * (env.bake ?? 1);
    if (rr) rr.toneMappingExposure *= env.expo ?? 1;
    const lm = env.lights ?? 1;
    const dead = R.torches.filter((t) => t.out);
    for (const l of kryptLights) {
      if (myLights.has(l)) continue;
      let k = lm;
      if (dead.length) for (const t of dead) if (l.position.distanceTo(t.w) < 1.6) { k = 0; break; }
      l.intensity *= k;
    }
    if (scene.fog) {
      scene.fog.density = scene.fog.density * (env.fogMul ?? 1) + (env.fogAdd ?? 0);
      if (env.fog) { scene.fog.color.lerp(_c.setRGB(env.fog[0], env.fog[1], env.fog[2]), env.fog[3] ?? 1); if (scene.background && scene.background.isColor) scene.background.copy(scene.fog.color); }
    }
    // Torch flames that went out stop making flame particles.
    if (dead.length || env.noParticles) for (const p of kryptPoints) {
      const g = p.geometry, a = g.attributes.alpha, ps = g.attributes.position, n = g.drawRange.count;
      if (env.noParticles) { p.visible = false; continue; }
      let ch = false;
      for (let i = 0; i < Math.min(n, a.count); i++) {
        const x = ps.getX(i), y = ps.getY(i), z = ps.getZ(i);
        for (const t of dead) if ((x - t.w.x) ** 2 + (y - t.w.y) ** 2 + (z - t.w.z) ** 2 < 1.2) { a.setX(i, 0); ch = true; break; }
      }
      if (ch) a.needsUpdate = true;
    }
  }
  const _c = new THREE.Color();
  R.ownLight = (l) => { myLights.add(l); return l; };

  // ---- the head camera ------------------------------------------------------------------------------------
  // c: { x, y, z, yaw, pitch, roll, fov } local; plus effects: nausea 0..1 (the 1.7.10 warp), squash 0..1.
  // The pose is set before the scare's update (so a lunge can aim at the lens); the warp after it.
  function setPose(c) {
    R.L(c.x, c.y, c.z, camera.position);
    _e.set(c.pitch || 0, R.yaw0 + (c.yaw || 0), c.roll || 0, "YXZ");
    camera.quaternion.setFromEuler(_e);
    const fov = c.fov || cam0.fov;
    if (camera.fov !== fov) camera.fov = fov;
    camera.near = c.near || cam0.near;
    camera.updateProjectionMatrix();
    camera.updateMatrixWorld(true);
    view.position.copy(camera.position); view.quaternion.copy(camera.quaternion); view.updateMatrixWorld(true);
  }
  function setCamera(c, t, fx) {
    // Nausea: EntityRenderer rotates the view about (0,1,1) by 7 degrees a tick, squeezes x by 1/f3, and rotates back.
    const nz = fx.nausea || 0, sq = fx.squash || 0;
    if (nz > 0.001 || sq > 0.001) {
      _m.identity();
      if (nz > 0.001) {
        const ang = t * 20 * 7 * Math.PI / 180, ax = _v.set(0, 1, 1).normalize();
        let f3 = 5 / (nz * nz + 5) - nz * 0.04; f3 *= f3;
        _m.makeRotationAxis(ax, ang).multiply(_m2.makeScale(1 / f3, 1, 1)).multiply(new THREE.Matrix4().makeRotationAxis(ax, -ang));
      }
      if (sq > 0.001) _m.premultiply(_m2.makeScale(1 + sq * 0.5, 1 - sq * 0.75, 1));
      camera.projectionMatrix.multiply(_m);
      camera.projectionMatrixInverse.copy(camera.projectionMatrix).invert();
    }
    view.position.copy(camera.position); view.quaternion.copy(camera.quaternion); view.updateMatrixWorld(true);
  }

  // One frame of scare S at time t: positions everything and returns the overlay frame f.
  R.evaluate = (S, t, extra = {}) => {
    const dur = S.dur, tt = Math.min(t, dur + 3);
    const f = { t: tt, hud: true, hp: 20, hpPrev: 20, hpMode: "normal", hurt: 0, blink: false, tints: [], white: 0, black: 0, fire: 0,
      glitch: 0, vig: null, splats: [], death: clamp((t - dur - 0.5) / 0.35), env: {}, chat: null, hotbar: S.hotbar ?? slotOf(heldAt(S.held, tt)) };   // the slot of what the hand holds (loadout.js)
    // Hits: hearts, the hurt roll (EntityRenderer.hurtCameraEffect), the heart blink (GuiIngame).
    let roll = 0, hp = 20, prev = 20;
    const hits = S.hits || [];
    for (let i = 0; i < hits.length; i++) {
      const h = hits[i];
      if (tt < h.t) break;
      prev = hp; hp = Math.max(0, hp - (h.dmg ?? 4));
      const ticks = (tt - h.t) * 20;
      if (ticks < 10) { const x = 1 - ticks / 10; roll = Math.sin(x * x * x * x * Math.PI) * 14 * Math.PI / 180 * (h.side ?? 1); }
      const hr = 20 - Math.floor(ticks);
      f.blink = hr >= 10 && Math.floor(hr / 3) % 2 === 1;
      f.hurt = Math.max(f.hurt, Math.exp(-(tt - h.t) / 0.09));
    }
    if (t >= dur) hp = 0;
    f.hp = hp; f.hpPrev = prev;
    let c = S.cam(tt, f);
    c.roll = (c.roll || 0) + roll;
    if (extra.cam) c = { ...c, ...extra.cam };   // verification: a fixed local camera (?scarecam)
    // Death: from the kill, the Minecraft death roll (40 - 8000 / (deathTime + 200) degrees about the view axis).
    if (t >= dur && !S.noDeathRoll) { const dt = (tt - dur) * 20; c.roll += (40 - 8000 / (dt + 200)) * Math.PI / 180 * (S.deathSide ?? 1); }
    setPose(c);
    S.update(tt, f);
    if (t >= dur) f.gone = SLOTS.map(Boolean);   // dead: the inventory drops, the hotbar is empty (EntityPlayer.onDeath drops it all)
    R.gore.update(tt);
    // The renderer updates world matrices before scene.onBeforeRender (where the live run evaluates), so without this
    // everything was drawn where the previous frame had put it: on the first frame each mob stood at its build pose
    // (a creeper "behind you" drawn in front of you for a frame), and a mob shown and moved in the same frame (a
    // teleport, an entrance) showed for a frame where it had been.
    group.updateMatrixWorld(true);
    group.visible = true;   // placed: from here on what is in it is the script's
    setCamera(c, tt, f.env);
    R.env = f.env;
    return f;
  };
  // Live: run S from now; onFrame(f, t) after each evaluate (the overlay draws there).
  let hooked = null;
  R.run = (S, onFrame) => {
    const t0 = performance.now();
    const prevHook = scene.onBeforeRender;
    hooked = { prevHook };
    scene.onBeforeRender = function (renderer, sc, cm, rt) {
      if (prevHook) prevHook.call(this, renderer, sc, cm, rt);
      const t = (performance.now() - t0) / 1000;
      let f;
      try { f = R.evaluate(S, t); applyEnv(f.env, f.fx, t); } catch (e) { console.error("scare frame", e); return; }
      if (onFrame) onFrame(f, t);
    };
  };
  // Dump: evaluate one moment and render it now; the caller reads the canvas in the same task.
  R.renderAt = (S, t, extra = {}) => {
    const f = R.evaluate(S, t, extra);
    if (extra.pull) { camera.translateZ(extra.pull); camera.translateX(extra.pull * 0.6); camera.lookAt(view.position); camera.near = 0.05; camera.updateProjectionMatrix(); camera.updateMatrixWorld(true); }   // debug: step back to see the lens from outside
    // applyEnv works on the values the Krypt sets every frame (fog, exposure, lights); here nothing resets them, so
    // they are put back after the render (several moments are rendered in one page).
    const prev = scene.onBeforeRender, rr = kr.renderer;
    const keep = { d: scene.fog ? scene.fog.density : 0, c: scene.fog ? scene.fog.color.clone() : null, bg: scene.background && scene.background.isColor ? scene.background.clone() : null, e: rr ? rr.toneMappingExposure : 1, li: kryptLights.map((l) => l.intensity) };
    scene.onBeforeRender = function () { applyEnv(f.env, f.fx, t); };
    try { kr.composer.render(); } finally {
      scene.onBeforeRender = prev;
      if (scene.fog) { scene.fog.density = keep.d; scene.fog.color.copy(keep.c); }
      if (keep.bg) scene.background.copy(keep.bg);
      if (rr) rr.toneMappingExposure = keep.e;
      kryptLights.forEach((l, i) => { l.intensity = keep.li[i]; });
    }
    return f;
  };

  // ---- carving (the piston trap): every carve is undone on dispose -------------------------------------------
  let carved = false;
  // Each carve remeshes the chunks it touches (50-90 ms): time it so the hitch can be put where it is not seen (R.carveMs).
  R.carveW = (mn, mx) => { if (typeof kr.carve !== "function") return 0; carved = true; const t0 = performance.now(); const n = kr.carve(mn, mx); R.carveMs = (R.carveMs || 0) + performance.now() - t0; return n; };
  // Boxes in local block offsets (inclusive), turned into world block boxes.
  R.carveL = (boxes) => {
    let n = 0;
    for (const [a, b] of boxes) {
      const p = R.L(a[0] + 0.5, a[1] + 0.5, a[2] + 0.5, new THREE.Vector3()), q = R.L(b[0] + 0.5, b[1] + 0.5, b[2] + 0.5, new THREE.Vector3());
      R.carved = (R.carved || []).concat([[Math.floor(Math.min(p.x, q.x)), Math.floor(Math.min(p.y, q.y)), Math.floor(Math.min(p.z, q.z))]]);
      n += R.carveW([Math.floor(Math.min(p.x, q.x)), Math.floor(Math.min(p.y, q.y)), Math.floor(Math.min(p.z, q.z))], [Math.floor(Math.max(p.x, q.x)), Math.floor(Math.max(p.y, q.y)), Math.floor(Math.max(p.z, q.z))]);
    }
    return n;
  };
  const onceDone = new Set();
  R.once = (key, fn) => { if (onceDone.has(key)) return; onceDone.add(key); try { fn(); } catch (e) { console.error("scare once", key, e); } };

  R.dispose = () => {
    if (hooked) { scene.onBeforeRender = hooked.prevHook || function () {}; hooked = null; }
    if (comp && comp.removePass) { try { comp.removePass(fxPass); } catch (e) { /* ignore */ } }
    try { fxPass.dispose(); } catch (e) { /* ignore */ }
    R.unsnuffAll();
    for (const p of kryptPoints) p.visible = true;
    if (KR.bakeUniform) KR.bakeUniform.value = base.bake;
    if (carved && typeof kr.restore === "function") { try { kr.restore(); } catch (e) { /* ignore */ } }
    scene.remove(group);
    group.traverse((o) => {
      if (o.geometry) o.geometry.dispose();
      if (o.material) { const ms = Array.isArray(o.material) ? o.material : [o.material]; for (const m of ms) m.dispose(); }
    });
    camera.position.copy(cam0.pos); camera.quaternion.copy(cam0.quat); camera.fov = cam0.fov; camera.near = cam0.near;
    camera.updateProjectionMatrix(); camera.updateMatrixWorld(true);
  };
  R.ready = async () => {
    await whenMobTexturesLoaded(); await new Promise((r) => setTimeout(r, 0)); await whenMobTexturesLoaded();
    // Warm-up: compile every shader and upload every texture the scare will show, now, with all of it briefly
    // visible: a mob's first appearance must not cost a frame (the lunge is a quarter of a second long).
    const rr = kr.renderer; if (!rr) return;
    const vis = [];
    group.traverse((o) => { vis.push([o, o.visible]); o.visible = true; });
    try {
      rr.compile(scene, camera);
      group.traverse((o) => {
        if (!o.material) return;
        for (const mt of Array.isArray(o.material) ? o.material : [o.material]) for (const k of ["map", "emissiveMap", "alphaMap"]) if (mt[k] && mt[k].isTexture && mt[k].image) { try { rr.initTexture(mt[k]); } catch (e) { /* ignore */ } }
      });
    } catch (e) { /* warm-up is best effort */ }
    for (const [o, v] of vis) o.visible = v;
    // The post pass's program too: one ordinary frame through it at zero strength.
    if (comp && comp.render) {
      const prev = scene.onBeforeRender;
      try { fxPass.enabled = true; comp.render(); } catch (e) { /* ignore */ } finally { fxPass.enabled = false; scene.onBeforeRender = prev; }
    }
  };
  await whenMobTexturesLoaded();
  return R;
}

// A held item (bow, sword) under its mob's flat ambient. That light is the mob's, and the 1.7.10 item textures are
// dark: bow wood averages 0.07 in linear light, stone 0.13, against a skeleton's bone at about 0.4. In a dim scare
// the item fell below the screen's darkest steps, and with no direction in the light its faces and its pixel edges
// came out one tone, so a bow was a black pole and a sword edge-on a black blade. So, for every held item:
//   a lift: the item is lit as if its texture averaged at least HELD_REF (dark items up to HELD_MAX times, gold,
//     iron and diamond untouched);
//   1.7.10's item lighting (RenderHelper.enableStandardItemLighting: lights from (0.2, 1, -0.7) and (-0.2, 1, 0.7),
//     diffuse 0.6 each, ambient 0.4), scaled so a face turned to the camera's side stays at 1: the faces and the
//     edges part, and the top edge of a blade catches the light.
// Only the flat ambient is changed; the scene's own lights (a torch) light the item as before.
export const HELD_REF = 0.25, HELD_MAX = 3.5;
const HELD_GLSL = `{ vec3 nH = inverseTransformDirection(normal, viewMatrix);
  float shH = min(1.0, 0.4 + 0.6 * (max(0.0, dot(nH, vec3(0.1617, 0.8085, -0.5659))) + max(0.0, dot(nH, vec3(-0.1617, 0.8085, 0.5659)))));
  totalEmissiveRadiance *= uHeldLift * shH * 1.35; }`;
function heldLight(mt) {
  const u = { value: 1 };
  const setLift = () => { const tone = itemTone(mt.map); if (tone != null) u.value = clamp(HELD_REF / Math.max(tone, 1e-3), 1, HELD_MAX); return tone != null; };
  if (!setLift()) whenMobTexturesLoaded().then(setLift);
  const prev = mt.onBeforeCompile, prevKey = mt.customProgramCacheKey ? mt.customProgramCacheKey.bind(mt) : () => "";
  mt.onBeforeCompile = (sh, r) => {
    if (prev) prev.call(mt, sh, r);
    sh.uniforms.uHeldLift = u;
    sh.fragmentShader = sh.fragmentShader
      .replace("#include <common>", "#include <common>\nuniform float uHeldLift;")
      .replace("#include <lights_lambert_fragment>", HELD_GLSL + "\n#include <lights_lambert_fragment>");
  };
  mt.customProgramCacheKey = () => prevKey() + "+held";
  mt.userData.heldLift = u;
  mt.needsUpdate = true;
}

// Warm the caches a scare needs (mob textures, its own textures), so the freeze starts without a hitch.
export async function warm(ids = [], texNames = []) {
  const tmp = [];
  for (const id of ids) { try { tmp.push(makeMob(id)); } catch (e) { /* unknown id */ } }
  await Promise.all(texNames.map((n) => tex(n)));
  await whenMobTexturesLoaded();
  for (const m of tmp) m.root.traverse((o) => { if (o.geometry) o.geometry.dispose(); });
}

// ---- small builders the scares share ---------------------------------------------------------------------
// A textured unit cube (a block), optionally with per-face textures [px, nx, py, ny, pz, nz].
export function blockMesh(texs, { lit = true, amb = null } = {}) {
  const g = new THREE.BoxGeometry(1, 1, 1);
  const mk = (t) => {
    const m = lit ? new THREE.MeshLambertMaterial({ map: t || null }) : new THREE.MeshBasicMaterial({ map: t || null });
    if (lit && amb && KR.patchBake) KR.patchBake(m, { fixed: amb });
    return m;
  };
  const mats = Array.isArray(texs) ? texs.map(mk) : mk(texs);
  return new THREE.Mesh(g, mats);
}
// A flat textured quad (cross-plane items, webs, arrows' fletching).
export function quad(t, w = 1, h = 1, { lit = false, side = THREE.DoubleSide, alphaTest = 0.1, transparent = false, opacity = 1, color = 0xffffff, fog = true, blending = THREE.NormalBlending, depthTest = true } = {}) {
  const m = lit ? new THREE.MeshLambertMaterial({ map: t, side, alphaTest, transparent, opacity, color }) : new THREE.MeshBasicMaterial({ map: t, side, alphaTest, transparent, opacity, color, fog, blending, depthTest });
  return new THREE.Mesh(new THREE.PlaneGeometry(w, h), m);
}
