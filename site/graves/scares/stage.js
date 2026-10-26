// The scare stage: a short stone-brick corridor with a side opening, torches, a camera rig, instanced
// gore particles and a mob wrapper. Everything is a pure function of time t so ?scare=&at= can seek.
import * as THREE from "three";
import { makeMob, whenMobTexturesLoaded } from "../../lib/mc/mobs.js";

export const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
export const lerp = (a, b, k) => a + (b - a) * k;
export const sstep = (a, b, x) => { const k = clamp((x - a) / (b - a)); return k * k * (3 - 2 * k); };
export const easeOut = (k) => 1 - Math.pow(1 - clamp(k), 3);
export function rngOf(seed) {
  let a = seed >>> 0;
  return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}

const TEXDIR = new URL("../tex/", import.meta.url);
const loader = new THREE.TextureLoader();
const texCache = new Map();
export function loadTex(name, rep) {
  const key = name;
  let t = texCache.get(key);
  if (!t) {
    t = new Promise((res) => loader.load(new URL(name + ".png", TEXDIR).href, (tx) => {
      tx.magFilter = THREE.NearestFilter; tx.minFilter = THREE.NearestFilter; tx.colorSpace = THREE.SRGBColorSpace;
      tx.wrapS = tx.wrapT = THREE.RepeatWrapping; res(tx);
    }, undefined, () => res(null)));
    texCache.set(key, t);
  }
  return t;
}

// Part names differ between the old rig (rArm) and the shared library (rightArm).
const ALIAS = { rArm: ["rArm", "rightArm"], lArm: ["lArm", "leftArm"], rLeg: ["rLeg", "rightLeg"], lLeg: ["lLeg", "leftLeg"] };
const DUMMY = new THREE.Object3D();
export function pt(m, k) {
  if (!m || !m.parts) return DUMMY;
  for (const n of ALIAS[k] || [k]) if (m.parts[n] && !Array.isArray(m.parts[n])) return m.parts[n];
  return DUMMY;
}
export function tint(m, hex, emissive, ei = 0.5) {
  m.root.traverse((o) => {
    if (!o.isMesh || !o.material) return;
    const mats = Array.isArray(o.material) ? o.material : [o.material];
    for (const mt of mats) {
      if (hex != null && mt.color) mt.color.setHex(hex);
      if (emissive != null && mt.emissive) { mt.emissive.setHex(emissive); mt.emissiveIntensity = ei; }
    }
  });
}
export function glow(m, amt, hex = 0xffffff) { tint(m, null, hex, amt); }

function box(w, h, d, color, basic = true) {
  const g = new THREE.BoxGeometry(w, h, d);
  return new THREE.Mesh(g, basic ? new THREE.MeshBasicMaterial({ color }) : new THREE.MeshLambertMaterial({ color }));
}
export { box };

// Mobs. Ids the shared library may not have yet get built here from the nearest vanilla model.
function blazeFallback() {
  const root = new THREE.Group(); const parts = {};
  const head = box(0.5, 0.5, 0.5, 0xd8a020, false); head.position.y = 1.55;
  head.material.emissive = new THREE.Color(0xff8a00); head.material.emissiveIntensity = 0.6;
  const face = box(0.3, 0.08, 0.02, 0x201000); face.position.set(0, 1.55, -0.26);
  root.add(head, face); parts.head = head;
  parts.rods = [];
  for (let i = 0; i < 12; i++) {
    const r = box(0.12, 0.5, 0.12, i % 2 ? 0xf0b020 : 0xffd040, false);
    r.material.emissive = new THREE.Color(0xff9000); r.material.emissiveIntensity = 0.6;
    root.add(r); parts.rods.push(r);
  }
  return { root, parts, height: 1.8, kind: "blaze" };
}
export async function getMob(name, opts = {}) {
  await whenMobTexturesLoaded();
  const tryIds = { MagmaCube: ["LavaSlime", "MagmaCube"], PigZombie: ["PigZombie"], WitherSkeleton: ["WitherSkeleton"] }[name] || [name];
  let m = null;
  for (const id of tryIds) {
    try { m = makeMob(id, opts); } catch (e) { m = null; }
    if (m && !m.unknown && m.kind !== "standin") break;
    m = null;
  }
  if (!m) m = name === "Blaze" ? blazeFallback() : makeMob("Zombie", opts);
  await whenMobTexturesLoaded();   // textures requested by makeMob must be in before the first render
  return m;
}

// Gore: instanced cubes flying on parabolas. Deterministic: each particle is a function of t.
const PALETTE = {
  blood: [0x8a0303, 0xb30808, 0x5c0000, 0xd01010], stone: [0x7d7d7d, 0x6a6a6a, 0x555555, 0x8e8e8e],
  green: [0x5dbb2a, 0x7ee03a, 0x3c8a1a], purple: [0xcc44ff, 0x7a1fb8, 0xe9a6ff], fire: [0xffd040, 0xff8a10, 0xff4a00],
  lava: [0xff6a10, 0xc03a00, 0xffb030], bone: [0xe8e8e0, 0xc8c8c0, 0xa8a8a0], white: [0xffffff, 0xdddddd], dust: [0x4a4038, 0x6a5e50, 0x302820]
};
export class Gore {
  constructor(max, rng) {
    this.max = max; this.n = 0; this.list = []; this.rng = rng;
    const mat = new THREE.MeshBasicMaterial({ color: 0xffffff });
    this.mesh = new THREE.InstancedMesh(new THREE.BoxGeometry(1, 1, 1), mat, max);
    this.mesh.frustumCulled = false;
    this.mesh.instanceColor = new THREE.InstancedBufferAttribute(new Float32Array(max * 3), 3);
    this.mesh.count = 0;
    this.m4 = new THREE.Matrix4(); this.q = new THREE.Quaternion(); this.col = new THREE.Color();
  }
  // dir: central direction, spread: how wide, speed in m/s
  burst(t0, o, n, kind = "blood", { dir = [0, 1, 0], spread = 1, speed = 3, size = 0.07, life = 1.6, grav = 9, floor = 0.03 } = {}) {
    const R = this.rng, pal = PALETTE[kind] || PALETTE.blood;
    for (let i = 0; i < n && this.list.length < this.max; i++) {
      const v = [(R() - .5) * 2 * spread + dir[0], (R() - .5) * 2 * spread + dir[1], (R() - .5) * 2 * spread + dir[2]];
      const sp = speed * (0.4 + R() * 0.9);
      this.list.push({ t0: t0 + R() * 0.04, p: o.slice(), v: v.map((x) => x * sp), s: size * 0.7 * (0.5 + R() * 1.1), life: life * (0.6 + R() * 0.6), c: pal[(R() * pal.length) | 0], g: grav, f: floor, r: R() * 6 });
    }
  }
  update(t) {
    const L = this.list; let k = 0;
    for (let i = 0; i < L.length; i++) {
      const p = L[i], d = t - p.t0;
      if (d < 0 || d > p.life) continue;
      let y = p.p[1] + p.v[1] * d - 0.5 * p.g * d * d;
      if (y < p.f) y = p.f;
      this.q.setFromAxisAngle(THREE.Object3D.DEFAULT_UP, p.r + d * 4);
      const sc = p.s * (d > p.life * 0.8 ? 1 - (d - p.life * 0.8) / (p.life * 0.2) : 1);
      this.m4.compose(new THREE.Vector3(p.p[0] + p.v[0] * d, y, p.p[2] + p.v[2] * d), this.q, new THREE.Vector3(sc, sc, sc));
      this.mesh.setMatrixAt(k, this.m4);
      this.col.setHex(p.c); this.mesh.setColorAt(k, this.col);
      k++;
    }
    this.mesh.count = k;
    this.mesh.instanceMatrix.needsUpdate = true;
    if (this.mesh.instanceColor) this.mesh.instanceColor.needsUpdate = true;
  }
}

export async function createStage(host, { phone = false } = {}) {
  const canvas = document.createElement("canvas");
  canvas.className = "qfs-gl";
  host.appendChild(canvas);
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: false, preserveDrawingBuffer: true, powerPreference: "high-performance" });
  renderer.setPixelRatio(phone ? 0.6 : Math.min(devicePixelRatio || 1, 1.5));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.25;
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x040203);
  scene.fog = new THREE.FogExp2(0x040203, 0.06);
  const camera = new THREE.PerspectiveCamera(72, 1, 0.04, 60);
  camera.rotation.order = "YXZ";
  scene.add(camera);
  scene.add(new THREE.AmbientLight(0x5a3a48, 1.1));
  const lantern = new THREE.PointLight(0xffc090, 5, 8, 1.4); camera.add(lantern);

  const [brick, mossy, gravel, cobble, torchT] = await Promise.all(["stonebrick", "stonebrick_mossy", "gravel", "cobblestone", "torch_on"].map((n) => loadTex(n)));
  const rep = (t, x, y) => { if (!t) return null; const c = t.clone(); c.needsUpdate = true; c.repeat.set(x, y); return c; };
  const plane = (w, h, tex, rx, ry, color = 0xffffff) => {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshLambertMaterial({ map: rep(tex, w, h), color, side: THREE.DoubleSide }));
    return m;
  };
  const W = 3, H = 3.2, Z0 = 2, Z1 = -22;
  const hall = new THREE.Group(); scene.add(hall);
  const len = Z0 - Z1, zc = (Z0 + Z1) / 2;
  const floor = plane(W, len, gravel); floor.rotation.x = -Math.PI / 2; floor.position.set(0, 0, zc); hall.add(floor);
  const ceil = plane(W, len, cobble); ceil.rotation.x = Math.PI / 2; ceil.position.set(0, H, zc); hall.add(ceil);
  const wallR = plane(len, H, brick); wallR.rotation.y = -Math.PI / 2; wallR.position.set(W / 2, H / 2, zc); hall.add(wallR);
  // the left wall has an opening at z -5..-3 into a side passage
  const lw = (za, zb) => { const w = plane(Math.abs(zb - za), H, mossy); w.rotation.y = Math.PI / 2; w.position.set(-W / 2, H / 2, (za + zb) / 2); hall.add(w); };
  lw(Z0, -3); lw(-5, Z1);
  const sideLen = 7, sx = -W / 2 - sideLen / 2;
  const sf = plane(sideLen, 2, gravel); sf.rotation.x = -Math.PI / 2; sf.position.set(sx, 0, -4); hall.add(sf);
  const sc = plane(sideLen, 2, cobble); sc.rotation.x = Math.PI / 2; sc.position.set(sx, H, -4); hall.add(sc);
  for (const z of [-5, -3]) { const sw = plane(sideLen, H, brick); sw.position.set(sx, H / 2, z); hall.add(sw); }
  const se = plane(2, H, brick); se.rotation.y = Math.PI / 2; se.position.set(-W / 2 - sideLen, H / 2, -4); hall.add(se);
  const back = plane(W, H, brick); back.position.set(0, H / 2, Z0); hall.add(back);
  const end = plane(W, H, brick); end.position.set(0, H / 2, Z1); hall.add(end);

  const torches = [];
  for (const [x, z] of [[1.4, -1.5], [-1.4, 0.5], [1.4, -7], [-1.4, -9], [1.4, -13]]) {
    const stick = box(0.1, 0.45, 0.1, 0x6a4a28, false); stick.position.set(x, 1.9, z);
    const flame = box(0.14, 0.14, 0.14, 0xffb030); flame.position.set(x, 2.22, z);
    const light = new THREE.PointLight(0xff8a30, 7, 11, 1.6); light.position.set(x * 0.8, 2.3, z);
    scene.add(stick, flame, light); torches.push({ light, flame, base: 7, ph: z * 3.1 });
  }
  scene.add((function () { const g = new THREE.Group(); return g; })());

  const gore = new Gore(phone ? 500 : 900, rngOf(7));
  scene.add(gore.mesh);

  const st = {
    renderer, scene, camera, canvas, gore, torches, W, H,
    size(w, h) { renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix(); },
    setCam(c) {
      camera.position.set(c.x, c.y, c.z);
      camera.rotation.set(c.pitch || 0, c.yaw || 0, c.roll || 0);
      if (camera.fov !== (c.fov || 72)) { camera.fov = c.fov || 72; camera.updateProjectionMatrix(); }
      camera.updateMatrixWorld();
    },
    light(t, flick = 1) {
      for (const k of st.torches) {
        const f = 0.8 + 0.2 * Math.sin(t * 9 + k.ph) * Math.sin(t * 5.3 + k.ph * 2);
        k.light.intensity = k.base * f * flick; k.flame.scale.setScalar(0.85 + 0.3 * f);
      }
    },
    render() { renderer.render(scene, camera); },
    dispose() {
      scene.traverse((o) => { if (o.geometry) o.geometry.dispose(); if (o.material) { const m = Array.isArray(o.material) ? o.material : [o.material]; m.forEach((x) => x.dispose()); } });
      renderer.dispose(); canvas.remove();
    }
  };
  return st;
}

export function faceTo(obj, fx, fz, tx, tz) { obj.rotation.y = Math.atan2(tx - fx, tz - fz) + Math.PI; }
export { THREE };
