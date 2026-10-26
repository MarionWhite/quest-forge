// Steve's life on the plateau: a loop of small purposeful things with natural walking between them, and
// the call sequence for a Lucky Block ("!", sprint, hop onto the dais, mine). Written as coroutines:
// an activity is a generator that yields a number (wait seconds) or a function(dt) -> done.
//
// Steve is a player: he never walks through a prop (nav.js plans every walk around the occupancy map and
// pushes him out of anything he touches), he uses the table, furnace and chest from their front, and what
// is in his hand always matches what he is doing (ore, ingots, logs, planks, sticks, the new pickaxe).
import * as THREE from 'three';
import { tex, mulberry } from './stage.js';
import { L } from './camp.js';
import { makeMob } from './mobs.js';
import { nav } from './nav.js';

const TAU = Math.PI * 2;
const wrapA = (a) => { a = (a + Math.PI) % TAU; if (a < 0) a += TAU; return a - Math.PI; };
const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
const lerp = (a, b, k) => a + (b - a) * k;
const smooth = (x) => { x = clamp(x, 0, 1); return x * x * (3 - 2 * x); };
export const yawFor = (dx, dz) => Math.atan2(-dx, -dz); // front is -z at yaw 0
const dirOf = (yaw) => ({ x: -Math.sin(yaw), z: -Math.cos(yaw) });
const SUN_H = { x: -0.13, z: -0.99 };

// Steve's body: planned around with a margin (R_P), checked against his real width (R_H).
export const R_P = 0.45, R_H = 0.3;

// ---------------------------------------------------------------- the held item, 1.7.10's third-person transform
// RenderPlayer.renderEquippedItems: from the right arm's pivot, translate (-1/16, 7/16, 1/16), then
//   block items   : translate (0, 3/16, -5/16), rotate X 20, Y 45, scale (-3/8, -3/8, 3/8)
//   full-3D items : (tools, sticks) translate (0, 3/16, 0), scale (5/8, -5/8, 5/8), rotate X -100, Y 45
//   flat items    : translate (1/4, 3/16, -3/16), scale 3/8, rotate Z 60, X -90, Z 20
// and then ItemRenderer.renderItem for a sprite: translate (0, -0.3, 0), scale 1.5, rotate Y 50, Z 335,
// translate (-15/16, -1/16, 0), and the sprite drawn from (0,0) to (1,1) with a 1/16 thickness.
// The model library draws y up where the game draws y down, so every matrix is mirrored (D) before use.
const mT = (x, y, z) => new THREE.Matrix4().makeTranslation(x, y, z);
const mS = (x, y, z) => new THREE.Matrix4().makeScale(x, y, z);
const mRx = (d) => new THREE.Matrix4().makeRotationX(d * Math.PI / 180);
const mRy = (d) => new THREE.Matrix4().makeRotationY(d * Math.PI / 180);
const mRz = (d) => new THREE.Matrix4().makeRotationZ(d * Math.PI / 180);
const mul = (...ms) => ms.reduce((a, m) => a.multiply(m), new THREE.Matrix4());
const D = mS(1, -1, 1);
const SPRITE_M = mul(mT(0, -0.3, 0), mS(1.5, 1.5, 1.5), mRy(50), mRz(335), mT(-0.9375, -0.0625, 0));
const HAND_M = mT(-0.0625, 0.4375, 0.0625);
const FULL3D = new Set(['wood_pickaxe', 'stone_pickaxe', 'iron_pickaxe', 'stick', 'fishing_rod_uncast', 'fishing_rod_cast']);
const ROD = new Set(['fishing_rod_uncast', 'fishing_rod_cast']);
function heldMatrix(spec) {
  if (spec.block) return mul(D, HAND_M, mT(0, 0.1875, -0.3125), mRx(20), mRy(45), mS(-0.375, -0.375, 0.375));
  if (FULL3D.has(spec.item)) {
    const parts = [D, HAND_M];
    if (ROD.has(spec.item)) parts.push(mRz(180), mT(0, -0.125, 0));
    parts.push(mT(0, 0.1875, 0), mS(0.625, -0.625, 0.625), mRx(-100), mRy(45), SPRITE_M);
    return mul(...parts);
  }
  return mul(D, HAND_M, mT(0.25, 0.1875, -0.1875), mS(0.375, 0.375, 0.375), mRz(60), mRx(-90), mRz(20), SPRITE_M);
}

// An item sprite as the game draws it: a front and a back face and a one-pixel-thick edge wherever a
// neighbouring pixel is empty. Built from the sprite's own alpha once its image is in.
const ITEM_GEO = new Map();
function buildItemGeo(img) {
  const N = img.width, M = img.height;
  const cv = document.createElement('canvas'); cv.width = N; cv.height = M;
  const g = cv.getContext('2d'); g.drawImage(img, 0, 0);
  const data = g.getImageData(0, 0, N, M).data;
  const op = (x, y) => x >= 0 && y >= 0 && x < N && y < M && data[(y * N + x) * 4 + 3] > 20;
  const d = 0.0625;
  const P = [], U = [], Nn = [], I = [];
  const quad = (pts, uv, n) => {
    const k = P.length / 3;
    for (let i = 0; i < 4; i++) { P.push(...pts[i]); U.push(uv[0], uv[1]); Nn.push(...n); }
    I.push(k, k + 1, k + 2, k, k + 2, k + 3);
  };
  // front and back: the game's u runs against x
  const face = (z, n) => {
    const k = P.length / 3;
    const c = [[0, 0], [1, 0], [1, 1], [0, 1]];
    for (const [x, y] of c) { P.push(x, y, z); U.push(1 - x, y); Nn.push(...n); }
    I.push(k, k + 1, k + 2, k, k + 2, k + 3);
  };
  face(0, [0, 0, 1]); face(-d, [0, 0, -1]);
  let tip = null, best = -1e9;
  for (let ry = 0; ry < M; ry++) for (let px = 0; px < N; px++) {
    if (!op(px, ry)) continue;
    const x0 = 1 - (px + 1) / N, x1 = 1 - px / N, y0 = 1 - (ry + 1) / M, y1 = 1 - ry / M;
    const u = (px + 0.5) / N, v = 1 - (ry + 0.5) / M;
    const sc = px + (N - 1 - ry);
    if (sc > best) { best = sc; tip = [(x0 + x1) / 2, (y0 + y1) / 2, -d / 2]; }
    const side = (pts, n) => { const k = P.length / 3; for (const p of pts) { P.push(...p); U.push(u, v); Nn.push(...n); } I.push(k, k + 1, k + 2, k, k + 2, k + 3); };
    if (!op(px - 1, ry)) side([[x1, y0, 0], [x1, y0, -d], [x1, y1, -d], [x1, y1, 0]], [1, 0, 0]);
    if (!op(px + 1, ry)) side([[x0, y0, 0], [x0, y1, 0], [x0, y1, -d], [x0, y0, -d]], [-1, 0, 0]);
    if (!op(px, ry - 1)) side([[x0, y1, 0], [x1, y1, 0], [x1, y1, -d], [x0, y1, -d]], [0, 1, 0]);
    if (!op(px, ry + 1)) side([[x0, y0, 0], [x0, y0, -d], [x1, y0, -d], [x1, y0, 0]], [0, -1, 0]);
  }
  void quad;
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(P, 3));
  geo.setAttribute('uv', new THREE.Float32BufferAttribute(U, 2));
  geo.setAttribute('normal', new THREE.Float32BufferAttribute(Nn, 3));
  geo.setIndex(I);
  geo.userData.tip = tip || [0.1, 0.9, -d / 2];
  return geo;
}
function flatItemGeo() {
  const g = new THREE.PlaneGeometry(1, 1); g.translate(0.5, 0.5, 0);
  const uv = g.attributes.uv; for (let i = 0; i < uv.count; i++) uv.setX(i, 1 - uv.getX(i));
  g.userData.tip = [0.1, 0.9, 0];
  return g;
}
const itemMats = new Map();
function itemMat(name) {
  if (!itemMats.has(name)) itemMats.set(name, new THREE.MeshLambertMaterial({ map: tex('items/' + name + '.png'), alphaTest: 0.4, side: THREE.DoubleSide, emissive: 0x202020 }));
  return itemMats.get(name);
}
const pendingItems = new Set();
function itemMesh(name) {
  let geo = ITEM_GEO.get(name);
  const t = tex('items/' + name + '.png');
  if (!geo && t.image && t.image.width) { geo = buildItemGeo(t.image); ITEM_GEO.set(name, geo); }
  const m = new THREE.Mesh(geo || flatItemGeo(), itemMat(name));
  m.userData.item = name;
  if (!geo) pendingItems.add(m);
  return m;
}
function refreshItems() {
  for (const m of pendingItems) {
    const name = m.userData.item, t = tex('items/' + name + '.png');
    if (!m.parent && !m.userData.keep) { pendingItems.delete(m); continue; }
    if (t.image && t.image.width) { const g = buildItemGeo(t.image); ITEM_GEO.set(name, g); m.geometry = g; pendingItems.delete(m); }
  }
}
const BLOCK_FILES = {
  log_oak: { top: 'log_oak_top.png', side: 'log_oak.png' },
  crafting_table: { top: 'crafting_table_top.png', side: 'crafting_table_side.png', bottom: 'planks_oak.png' },
};
const PRELOAD = ['iron_pickaxe', 'stone_pickaxe', 'wood_pickaxe', 'stick', 'iron_ingot', 'coal', 'apple', 'diamond', 'feather', 'bread', 'fish_cod_raw', 'fish_cod_cooked', 'fishing_rod_uncast', 'fishing_rod_cast'];

// ---------------------------------------------------------------- small drawn things
function bangTexture() {
  // an 8 x 16 pixel "!" in the game's yellow with a dark edge
  const rows = [
    '..kkkk..', '.kyyyyk.', '.kyyyyk.', '.kyYYyk.', '.kyYYyk.', '.kyYYyk.', '.kyYYyk.', '.kyYYyk.',
    '..kyyk..', '..kyyk..', '..kkkk..', '........', '..kkkk..', '.kyyyyk.', '.kyyyyk.', '..kkkk..',
  ];
  const c = document.createElement('canvas');
  c.width = 8; c.height = 16;
  const g = c.getContext('2d');
  const col = { k: '#3a2a00', y: '#ffd426', Y: '#fff2a0' };
  rows.forEach((r, y) => [...r].forEach((ch, x) => { if (col[ch]) { g.fillStyle = col[ch]; g.fillRect(x, y, 1, 1); } }));
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace; t.magFilter = THREE.NearestFilter; t.minFilter = THREE.NearestFilter; t.generateMipmaps = false;
  return t;
}

export function createBrain(deps) {
  const { S, camp, fx, play, seed = 11 } = deps;
  const steve = S.steve;
  const root = steve.root, P = steve.parts;
  root.rotation.order = 'YXZ';
  const world = new THREE.Group();
  S.scene.add(world);
  // a warm fill that follows him from the camera's side, so the backlit sunset never turns him into a silhouette
  const fill = new THREE.PointLight(0xffd8b8, 14, 9, 1.4);
  S.scene.add(fill);
  let rng = mulberry(seed);
  const R = (a = 0, b = 1) => a + rng() * (b - a);
  const rest = {};
  for (const k of Object.keys(P)) rest[k] = { x: P[k].position.x, y: P[k].position.y, z: P[k].position.z, rx: P[k].rotation.x, ry: P[k].rotation.y, rz: P[k].rotation.z };
  const matCache = new Map();
  const texMat = (file) => {
    if (!matCache.has(file)) matCache.set(file, new THREE.MeshLambertMaterial({ map: tex(file) }));
    return matCache.get(file);
  };
  for (const n of PRELOAD) tex('items/' + n + '.png');

  const b = {
    t: 0, x: 3.2, z: 0.5, y: 0, vy: 0, floor: 0, air: false, yaw: Math.PI / 2, phase: 0, amp: 0, ampT: 0,
    sit: 0, sitT: 0, crouch: 0, crouchT: 0, lean: 0, leanT: 0, twist: 0, bob: 0,
    r: { x: 0, z: 0, w: 0, on: false, tx: 0, tz: 0 }, l: { x: 0, z: 0, w: 0, on: false, tx: 0, tz: 0 },
    head: { yaw: 0, pitch: 0, tyaw: 0, tpitch: 0, target: null },
    state: 'idle', frozen: false, gen: null, wait: 0, fn: null, cleanups: [], lastAct: -1, plan: [], planAt: 0,
    camPos: new THREE.Vector3(7.6, 3.4, 10.2), stepIdx: 0, arrivedAt: -1, swingClock: 0, mining: false,
    held: null, heldSpec: null, bang: null, items: [], extras: [], fireT: 2, ambT: 5, turnRate: 9,
    ign: new Set(), smelt: 0, smeltT: 0,
  };

  // ------------------------------------------------------------ sound and fx helpers
  const at = () => ({ x: b.x, y: b.y + 0.9, z: b.z });
  const snd = (name, o = {}) => play(name, { pos: o.pos || at(), ref: 6, rolloff: 0.6, ...o, pos: o.pos || at() });
  const surface = (x, z) => {
    if (x >= 2.9 && x <= 6.2 && z >= -6.4 && z <= -3.8) return 'wood';
    const ax = 5.6, az = 11.5, bx = 3.2, bz = -1.2;
    const vx = bx - ax, vz = bz - az;
    const t = clamp(((x - ax) * vx + (z - az) * vz) / (vx * vx + vz * vz), 0, 1);
    if (Math.hypot(x - (ax + vx * t), z - (az + vz * t)) < 0.8) return 'gravel';
    return 'grass';
  };
  // walk through something for the length of an activity (the dais, the bench, the block he stands on)
  const ignoring = (...kinds) => { for (const k of kinds) b.ign.add(k); onCleanup(() => { for (const k of kinds) b.ign.delete(k); }); };

  // ------------------------------------------------------------ held item, drops, the "!"
  function hold(spec) {
    if (b.held) { b.held.parent && b.held.parent.remove(b.held); b.held = null; }
    b.heldSpec = spec || null;
    if (!spec) return;
    let m;
    if (spec.block) {
      m = new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), blockMats(spec.block));
    } else {
      m = itemMesh(spec.item);
      m.userData.keep = true;
    }
    m.matrixAutoUpdate = false;
    m.matrix.copy(heldMatrix(spec));
    m.castShadow = false;
    P.rArm.add(m);
    b.held = m;
  }
  const blockMats = (name) => {
    const f = BLOCK_FILES[name];
    if (!f) { const m = texMat('blocks/' + name + '.png'); return [m, m, m, m, m, m]; }
    const side = texMat('blocks/' + f.side), top = texMat('blocks/' + f.top), bot = texMat('blocks/' + (f.bottom || f.top));
    return [side, side, top, bot, side, side];
  };
  function spawnItem(spec, pos, vel, o = {}) {
    const g = new THREE.Group();
    let m;
    if (spec.block) { m = new THREE.Mesh(new THREE.BoxGeometry(0.26, 0.26, 0.26), blockMats(spec.block)); g.add(m); }
    else {
      // a dropped sprite: the game's 0.5-scale item, centred so it spins on its own middle
      const im = itemMesh(spec.item);
      im.userData.keep = true;
      im.position.set(-0.21, -0.21, 0.013);
      im.scale.setScalar(0.42);
      m = new THREE.Group(); m.add(im); g.add(m);
    }
    g.position.set(pos.x, pos.y, pos.z);
    world.add(g);
    const it = { g, m, v: new THREE.Vector3(vel.x, vel.y, vel.z), age: 0, pickAt: o.pickAt ?? 0.7, state: 'fly', rest: 0, fromP: null, ground: o.ground ?? 0 };
    b.items.push(it);
    return it;
  }
  function stepItems(dt) {
    for (let i = b.items.length - 1; i >= 0; i--) {
      const it = b.items[i];
      it.age += dt;
      it.m.rotation.y += dt * 2.2;
      if (it.state === 'fly') {
        it.v.y -= 14 * dt;
        it.g.position.addScaledVector(it.v, dt);
        const gy = it.ground + 0.2;
        if (it.g.position.y < gy) { it.g.position.y = gy; if (it.v.y < -1) it.v.y *= -0.4; else { it.v.set(0, 0, 0); it.state = 'rest'; } it.v.x *= 0.5; it.v.z *= 0.5; }
      } else if (it.state === 'rest') {
        it.g.position.y = it.ground + 0.24 + Math.sin(it.age * 3) * 0.04;
        if (it.pickAt >= 0 && it.age > it.pickAt) { it.state = 'pick'; it.t = 0; it.fromP = it.g.position.clone(); }
      } else if (it.state === 'pick') {
        it.t += dt;
        const k = smooth(it.t / 0.28);
        it.g.position.set(lerp(it.fromP.x, b.x, k), lerp(it.fromP.y, b.y + 0.9, k), lerp(it.fromP.z, b.z, k));
        it.g.scale.setScalar(1 - 0.6 * k);
        if (it.t >= 0.28) { snd('random.pop', { volume: 0.6, pitch: [0.9, 1.2] }); world.remove(it.g); b.items.splice(i, 1); }
      } else if (it.state === 'custom') {
        if (it.update(dt)) { world.remove(it.g); b.items.splice(i, 1); }
      }
    }
  }
  const noItems = () => !b.items.some((it) => it.state !== 'custom');
  function showBang() {
    if (!b.bang) {
      const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: bangTexture(), transparent: true, depthWrite: false, fog: false }));
      s.center.set(0.5, 0);
      root.add(s);
      b.bang = s;
    }
    b.bang.visible = true;
    b.bang.userData.t0 = b.t;
  }
  function stepBang() {
    const s = b.bang;
    if (!s || !s.visible) return;
    const a = b.t - s.userData.t0;
    // pop in with an overshoot, bounce twice, then shrink away
    const grow = a < 0.2 ? smooth(a / 0.2) * 1.25 : a < 0.32 ? lerp(1.25, 1, (a - 0.2) / 0.12) : 1;
    const fade = a > 1.0 ? Math.max(0, 1 - (a - 1.0) / 0.25) : 1;
    const hop = a > 0.2 ? Math.abs(Math.sin((a - 0.2) * 9)) * 0.1 * Math.exp(-(a - 0.2) * 2.4) : 0;
    s.scale.set(0.42 * grow * fade, 0.84 * grow * fade, 1);
    s.position.set(0, 2.05 + hop, 0);
    if (a > 1.25) s.visible = false;
  }

  // ------------------------------------------------------------ pose
  const bumpFoot = () => {
    const idx = Math.floor(b.phase / Math.PI);
    if (idx !== b.stepIdx) {
      b.stepIdx = idx;
      if (b.amp > 0.35 && !b.air && b.y <= b.floor + 0.05) {
        const sf = b.floor > 0.5 ? 'stone' : b.sitStep || surface(b.x, b.z);
        snd('step.' + sf, { volume: b.amp > 1 ? 0.55 : 0.38, pitch: [0.85, 1.15] });
        if (b.amp > 1) fx.dust({ x: b.x, y: b.floor, z: b.z }, 2, { vx: dirOf(b.yaw).x * -0.6, vz: dirOf(b.yaw).z * -0.6 });
      }
    }
  };
  function applyPose(dt) {
    const k = Math.min(1, dt * 10);
    b.amp += (b.ampT - b.amp) * Math.min(1, dt * 8);
    b.crouch += (b.crouchT - b.crouch) * Math.min(1, dt * 14);
    b.sit += (b.sitT - b.sit) * Math.min(1, dt * 7);
    b.lean += (b.leanT - b.lean) * Math.min(1, dt * 8);
    for (const a of [b.r, b.l]) {
      a.w += ((a.on ? 1 : 0) - a.w) * k;
      a.x += (a.tx - a.x) * Math.min(1, dt * 22);
      a.z += (a.tz - a.z) * Math.min(1, dt * 22);
    }
    const s = Math.cos(b.phase);
    const legAmp = 0.95 * b.amp, armAmp = 0.85 * b.amp;
    const sit = b.sit;
    P.rLeg.rotation.x = lerp(s * legAmp, 1.45, sit);
    P.lLeg.rotation.x = lerp(-s * legAmp, 1.45, sit);
    P.rLeg.rotation.z = sit * -0.12; P.lLeg.rotation.z = sit * 0.12;
    const idleZ = 0.05 + Math.cos(b.t * 1.5) * 0.03;
    const rBase = -s * armAmp, lBase = s * armAmp;
    P.rArm.rotation.x = lerp(rBase, b.r.x, b.r.w) + b.crouch * 0.4;
    P.lArm.rotation.x = lerp(lBase, b.l.x, b.l.w) + b.crouch * 0.4;
    P.rArm.rotation.z = lerp(idleZ, b.r.z, b.r.w);
    P.lArm.rotation.z = lerp(-idleZ, b.l.z, b.l.w);
    // sneaking: lean the body, drop the arms and head, push the legs back
    P.body.rotation.x = -0.5 * b.crouch;
    P.body.rotation.y = b.twist;
    for (const [n, dz] of [['rLeg', 0.2], ['lLeg', 0.2]]) P[n].position.z = rest[n].z + dz * b.crouch;
    for (const n of ['rArm', 'lArm']) { P[n].position.y = rest[n].y - 0.2 * b.crouch; P[n].position.z = rest[n].z - 0.05 * b.crouch; }
    // head: smoothed toward the target set by the activity, plus a little walking bob
    const h = b.head;
    h.yaw += (h.tyaw - h.yaw) * Math.min(1, dt * 9);
    h.pitch += (h.tpitch - h.pitch) * Math.min(1, dt * 9);
    P.head.rotation.y = h.yaw;
    P.head.rotation.x = h.pitch + Math.sin(b.phase * 2) * 0.03 * b.amp + b.crouch * -0.12;
    P.head.position.y = rest.head.y - 0.1 * b.crouch;
    if (P.headwear) { P.headwear.rotation.copy(P.head.rotation); P.headwear.position.copy(P.head.position); }
    // vertical: jumps, steps, a gentle bob while walking
    if (b.air) {
      b.vy -= 26 * dt;
      b.y += b.vy * dt;
      if (b.y <= b.floor && b.vy < 0) {
        b.y = b.floor; b.vy = 0; b.air = false;
        snd('step.' + (b.floor > 0.5 ? 'stone' : surface(b.x, b.z)), { volume: 0.5 });
      }
    } else b.y += (b.floor - b.y) * Math.min(1, dt * 18);
    const bob = Math.abs(Math.sin(b.phase)) * 0.045 * b.amp;
    root.position.set(b.x, b.y + bob - 0.25 * sit, b.z);
    root.rotation.set(-b.lean, b.yaw, 0);
    bumpFoot();
  }

  // ------------------------------------------------------------ coroutine tools
  function setArm(side, x, z = 0) { const a = side === 'l' ? b.l : b.r; a.on = true; a.tx = x; a.tz = z; }
  function freeArm(side) { const a = side === 'l' ? b.l : b.r; a.on = false; }
  function relax() { freeArm('r'); freeArm('l'); b.ampT = 0; b.twist = 0; b.crouchT = 0; b.sitT = 0; b.leanT = 0; b.head.tyaw = 0; b.head.tpitch = 0; b.head.target = null; b.sitStep = null; }
  function* faceYaw(y, rate = 9, tol = 0.04) {
    yield (dt) => { const d = wrapA(y - b.yaw); b.yaw += d * Math.min(1, dt * rate); return Math.abs(d) < tol; };
  }
  function* faceDir(dx, dz, rate) { yield* faceYaw(yawFor(dx, dz), rate); }
  function* faceAt(x, z, rate) { yield* faceYaw(yawFor(x - b.x, z - b.z), rate); }
  // walk to a point along a route planned around every prop; arms swing with the stride, never with a slide
  function* walkTo(x, z, o = {}) {
    const speed = o.speed ?? 2.1;
    const ign = o.ign || b.ign;
    const pts = o.straight ? [[x, z]] : nav.path(b.x, b.z, x, z, R_P, { ign });
    b.state = o.sprint ? 'run' : 'walk';
    for (let i = 0; i < pts.length; i++) {
      const [px, pz] = pts[i];
      const last = i === pts.length - 1;
      let stuck = 0, bestD = 1e9;
      yield (dt) => {
        const dx = px - b.x, dz = pz - b.z, d = Math.hypot(dx, dz);
        if (d < (last ? 0.06 : 0.15)) return true;
        if (d < bestD - 0.01) { bestD = d; stuck = 0; } else if ((stuck += dt) > 1.6) return true;
        const want = yawFor(dx, dz);
        const diff = wrapA(want - b.yaw);
        b.yaw += diff * Math.min(1, dt * (o.turn ?? 8));
        const align = 1 - Math.min(1, Math.abs(diff) / 1.4) * 0.85;
        const slow = last ? clamp(d / 0.6, 0.35, 1) : 1;
        const sp = speed * align * slow;
        const step = Math.min(d, sp * dt);
        b.x += (dx / d) * step; b.z += (dz / d) * step;
        const f = nav.resolve(b.x, b.z, R_H, ign);
        b.x = f.x; b.z = f.z;
        b.ampT = clamp(sp / 2.1, 0.1, 1.5) * (o.crouch ? 0.7 : 1);
        b.phase += step * (o.sprint ? 2.2 : 2.7);
        if (o.sprint) { b.leanT = 0.16; setArm('r', 0); b.r.on = false; }
        if (o.onStep) o.onStep(dt, d);
        return false;
      };
    }
    b.ampT = 0; b.leanT = 0; b.state = 'idle';
    // let the stride settle
    b.phase = Math.round(b.phase / Math.PI) * Math.PI;
  }
  function* armSwing(n, period, onHit, o = {}) {
    for (let i = 0; i < n; i++) {
      let t = 0, fired = false;
      yield (dt) => {
        t += dt;
        const p = clamp(t / period, 0, 1);
        const f1 = 1 - Math.pow(1 - p, 3);
        const f2 = Math.sin(f1 * Math.PI), f3 = Math.sin(p * Math.PI) * -0.7;
        setArm('r', (o.base ?? 0.5) + f2 * (o.amp ?? 1.1) + f3 * 0.7, 0);
        b.twist = Math.sin(Math.sqrt(p) * TAU) * 0.2;
        if (!fired && p >= 0.4) { fired = true; if (onHit) onHit(i); }
        return p >= 1;
      };
    }
    freeArm('r'); b.twist = 0;
  }
  const doCleanup = () => { const c = b.cleanups.splice(0); for (const f of c.reverse()) { try { f(); } catch (e) { /* ignore */ } } };
  const onCleanup = (f) => b.cleanups.push(f);
  function jump(v = 7.4) { b.vy = v; b.air = true; }
  function* waitLanded() { yield () => !b.air; }
  function* waitItems() { yield () => noItems(); }

  // block break visuals (crack overlay + chips)
  function crackMesh(x, y, z) {
    const m = new THREE.Mesh(new THREE.BoxGeometry(1.012, 1.012, 1.012), new THREE.MeshBasicMaterial({ map: tex('blocks/destroy_stage_0.png'), transparent: true, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -4, opacity: 0.95 }));
    m.position.set(x, y, z);
    world.add(m);
    onCleanup(() => world.remove(m));
    return { m, set(stage) { m.material.map = tex('blocks/destroy_stage_' + clamp(stage, 0, 9) + '.png'); m.material.needsUpdate = true; }, remove() { world.remove(m); } };
  }
  const PALETTES = {
    'stone.png': [0x8a8a8a, 0x7a7a7a, 0x9a9a9a], 'coal_ore.png': [0x8a8a8a, 0x2a2a2a, 0x7a7a7a], 'iron_ore.png': [0x8a8a8a, 0xd8af93, 0x7a7a7a],
    'cobblestone.png': [0x7d7d7d, 0x6a6a6a, 0x8e8e8e], 'dirt.png': [0x866043, 0x6f4f36, 0x9a7050], 'planks_oak.png': [0xa07e48, 0x8a6a3a, 0xb58f55],
    'log_oak.png': [0x6b5030, 0x4d3920, 0x7a5c38],
  };
  const palette = (f) => PALETTES[f] || PALETTES['stone.png'];
  const DIG = { 'stone.png': 'dig.stone', 'coal_ore.png': 'dig.stone', 'iron_ore.png': 'dig.stone', 'cobblestone.png': 'dig.stone', 'dirt.png': 'dig.gravel', 'planks_oak.png': 'dig.wood', 'log_oak.png': 'dig.wood' };

  // a block placed by Steve (a cube that pops in); it is solid to everybody while it stands
  function placeBlock(file, x, y, z) {
    const m = new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), texMat('blocks/' + file));
    m.position.set(x, y + 0.5, z);
    m.castShadow = m.receiveShadow = true;
    world.add(m);
    const box = y === 0 ? nav.add('placed', x - 0.5, z - 0.5, x + 0.5, z + 0.5, 'placed') : null;
    const blk = { m, t: 0, file, box };
    b.extras.push(blk);
    onCleanup(() => { world.remove(m); nav.remove(box); const i = b.extras.indexOf(blk); if (i >= 0) b.extras.splice(i, 1); });
    snd(DIG[file] || 'dig.stone', { pos: { x, y: y + 0.5, z }, volume: 0.9, pitch: [0.9, 1.1] });
    fx.chips({ x, y: y + 0.5, z }, palette(file), 6, { speed: 1 });
    return blk;
  }
  function stepExtras(dt) {
    for (const e of b.extras) {
      if (e.t < 0.2) { e.t += dt; const k = e.t / 0.2; e.m.scale.setScalar(0.6 + 0.4 * Math.min(1, k) + Math.sin(Math.min(1, k) * Math.PI) * 0.12); }
    }
  }
  function breakBlock(blk, pos, file) {
    snd(DIG[file] || 'dig.stone', { pos, volume: 1, pitch: [0.8, 0.95] });
    fx.chips(pos, palette(file), 16, { speed: 2, up: 1.3 });
    world.remove(blk.m);
    nav.remove(blk.box);
    const i = b.extras.indexOf(blk); if (i >= 0) b.extras.splice(i, 1);
  }

  // ------------------------------------------------------------ the activities
  function* standAt(x, z, yaw, o = {}) {
    yield* walkTo(x, z, o);
    yield* faceYaw(yaw);
  }
  // stand in front of one of the three blocks at the table row, looking at it
  function* useFront(stand, cell) {
    yield* walkTo(stand.x, stand.z);
    yield* faceYaw(0);
    b.head.target = new THREE.Vector3(cell.cx + 0.5, 0.8, cell.cz + 0.5);
  }
  // a short right-click: the arm comes up to the block face and taps
  function* tap(n = 1, gap = 0.25) {
    for (let i = 0; i < n; i++) {
      setArm('r', 1.1, -0.12);
      yield 0.14;
      setArm('r', 0.85, -0.12);
      yield gap;
    }
  }
  const frontPos = (cell, y = 0.9, dz = 0.9) => ({ x: cell.cx + 0.5, y, z: cell.cz + dz });

  // mining a quarry block: returns the block's record and leaves its drop on the ground
  function* mineBlock(q, toolItem, swings = 6) {
    yield* standAt(q.x, L.quarryStandZ, 0);
    hold({ item: toolItem });
    onCleanup(() => hold(null));
    b.head.tpitch = q.y > 1 ? 0.1 : -0.15;
    const crack = crackMesh(q.x, q.y, q.z);
    yield 0.25;
    yield* armSwing(swings, 0.4, (i) => {
      crack.set(Math.floor(((i + 1) / swings) * 9));
      snd(DIG[q.file], { pos: { x: q.x, y: q.y, z: q.z }, volume: 0.8, pitch: [0.85, 1.05] });
      fx.chips({ x: q.x, y: q.y, z: q.z + 0.5 }, palette(q.file), 3, { speed: 0.8 });
    });
    crack.remove();
    q.mesh.visible = false; q.removed = true; nav.remove(q.box);
    const back = () => { q.mesh.visible = true; q.removed = false; nav.restore(q.box); };
    onCleanup(back);
    snd('dig.stone', { pos: { x: q.x, y: q.y, z: q.z }, volume: 1, pitch: 0.75 });
    fx.chips({ x: q.x, y: q.y, z: q.z }, palette(q.file), 18, { speed: 2, up: 1.3 });
    return back;
  }

  function* actMine() {
    // stone and coal with the wooden pickaxe; the iron ore is for the smelting chain
    const choices = camp.quarry.filter((q) => !q.removed && q.kind !== 'iron' && !(q.kind === 'stone' && q.y < 1 && camp.quarry.some((o) => o !== q && !o.removed && o.x === q.x && o.y > q.y)));
    if (!choices.length) return;
    const q = choices[Math.floor(R() * choices.length)];
    const back = yield* mineBlock(q, 'wood_pickaxe');
    spawnItem(q.kind === 'coal' ? { item: 'coal' } : { block: 'cobblestone' }, { x: q.x, y: q.y, z: q.z + 0.4 }, { x: R(-0.4, 0.4), y: 4, z: 1.4 }, { pickAt: 0.9, ground: 0 });
    yield 1.3;
    yield* waitItems();
    // put the block back: the next visitor finds the quarry whole
    b.head.tpitch = 0;
    yield* armSwing(1, 0.35, () => {
      back();
      snd('dig.stone', { pos: { x: q.x, y: q.y, z: q.z }, volume: 0.8, pitch: 1.1 });
      fx.chips({ x: q.x, y: q.y, z: q.z + 0.5 }, palette(q.file), 5, { speed: 0.8 });
    });
    yield 0.6;
    hold(null);
  }

  function* actPlace() {
    const sp = L.build;
    yield* standAt(sp.x, sp.z, Math.PI);
    hold({ block: 'cobblestone' });
    onCleanup(() => hold(null));
    yield 0.2;
    const bl = [];
    yield* armSwing(1, 0.35, () => { bl.push(placeBlock('cobblestone.png', sp.cx + 0.5, 0, sp.cz + 0.5)); });
    yield 0.5;
    b.head.tpitch = 0.25;
    yield* armSwing(1, 0.35, () => { bl.push(placeBlock('cobblestone.png', sp.cx + 0.5, 1, sp.cz + 0.5)); });
    b.head.tpitch = 0;
    yield 1.1;
    hold({ item: 'wood_pickaxe' });
    for (const blk of bl.reverse()) {
      const p = { x: blk.m.position.x, y: blk.m.position.y, z: blk.m.position.z };
      const crack = crackMesh(p.x, p.y, p.z);
      yield* armSwing(3, 0.3, (i) => { crack.set((i + 1) * 3); snd('dig.stone', { pos: p, volume: 0.7, pitch: [0.9, 1.1] }); });
      crack.remove();
      breakBlock(blk, p, 'cobblestone.png');
      spawnItem({ block: 'cobblestone' }, p, { x: R(-0.3, 0.3), y: 3.2, z: 1.2 }, { pickAt: 0.7 });
      yield 0.5;
    }
    yield 0.6;
    hold(null);
  }

  // ---- the table, furnace and chest, always used from the front (+z)
  function* craftAt(steps) {
    // steps: [[handBefore, handAfter, seconds, sound?]]: he arranges the grid and takes the result
    yield* useFront(L.tableStand, L.table);
    b.head.tpitch = -0.45;
    for (const st of steps) {
      if (st.hold !== undefined) hold(st.hold);
      for (let i = 0; i < (st.taps || 3); i++) {
        setArm(i % 2 ? 'l' : 'r', 1.05 + (i % 3) * 0.08, i % 2 ? 0.22 : -0.22);
        freeArm(i % 2 ? 'r' : 'l');
        snd('random.click', { pos: frontPos(L.table, 1, 0.6), volume: 0.4, pitch: [0.9, 1.3] });
        yield 0.3;
      }
      if (st.after !== undefined) { snd('random.pop', { pos: frontPos(L.table, 1, 0.6), volume: 0.7, pitch: 1.2 }); hold(st.after); }
      if (st.pause) yield st.pause;
    }
    relax();
  }
  function* showOff(spec, secs = 1.4) {
    hold(spec);
    setArm('r', 1.6, 0);
    b.head.tpitch = -0.2;
    snd('random.levelup', { volume: 0.35, pitch: 1.5 });
    yield secs;
    relax();
  }

  // iron: mine the ore at the rocks, smelt it, take the ingots, craft an iron pickaxe
  function* actIron() {
    const q = camp.quarry.find((o) => o.kind === 'iron' && !o.removed);
    if (!q) return;
    yield* mineBlock(q, 'stone_pickaxe', 8);
    spawnItem({ block: 'iron_ore' }, { x: q.x, y: q.y, z: q.z + 0.4 }, { x: R(-0.3, 0.3), y: 4, z: 1.4 }, { pickAt: 0.9, ground: 0 });
    yield 1.2;
    yield* waitItems();
    hold({ block: 'iron_ore' });
    b.head.tpitch = 0;
    yield 0.6;
    // the furnace: load the ore, it lights and crackles, then take the ingots
    yield* useFront(L.furnaceStand, L.furnace);
    b.head.tpitch = -0.35;
    yield* tap(1, 0.5);
    snd('random.click', { pos: frontPos(L.furnace), volume: 0.5 });
    hold(null);
    freeArm('r');
    yield 0.4;
    camp.setFurnace(true);
    onCleanup(() => { camp.setFurnace(false); b.smelt = 0; });
    snd('fire.ignite', { pos: frontPos(L.furnace, 0.5), volume: 0.5 });
    b.smelt = 1;
    let t = 0, nextCrackle = 0.3;
    yield (dt) => {
      t += dt;
      b.head.tyaw = Math.sin(t * 0.8) * 0.15;
      if (t >= nextCrackle) {
        nextCrackle = t + R(0.7, 1.2);
        snd('fire.fire', { pos: frontPos(L.furnace, 0.5), volume: 0.7, pitch: R(0.9, 1.1) });
      }
      return t > 5.2;
    };
    b.smelt = 0;
    b.head.tyaw = 0;
    yield* tap(1, 0.3);
    snd('random.pop', { pos: frontPos(L.furnace), volume: 0.7, pitch: 1.1 });
    camp.setFurnace(false);
    hold({ item: 'iron_ingot' });
    relax();
    b.head.tpitch = -0.1;
    yield 0.9;
    // the table: sticks first, then the pickaxe from three ingots and two sticks
    yield* craftAt([{ taps: 3, hold: { item: 'iron_ingot' } }, { taps: 2, hold: { item: 'stick' } }, { taps: 2, after: { item: 'iron_pickaxe' } }]);
    yield* showOff({ item: 'iron_pickaxe' }, 1.6);
    hold(null);
  }

  // wood: punch a log from the tree, craft planks, sticks and a wooden pickaxe
  function treeStand() {
    const cx = L.tree.cx + 0.5, cz = L.tree.cz + 0.5;
    for (const [dx, dz] of [[1.05, 0], [0, 1.05], [0, -1.05], [-1.05, 0], [1.05, 0.3], [1.05, -0.3]]) {
      const x = cx + dx, z = cz + dz;
      if (!nav.blocked(x, z, R_P, b.ign)) return { x, z, yaw: yawFor(-dx, -dz) };
    }
    return null;
  }
  function* actWood() {
    const st = treeStand();
    if (!st) return;
    yield* standAt(st.x, st.z, st.yaw);
    const tp = { x: L.tree.cx + 0.5, y: 1.5, z: L.tree.cz + 0.5 };
    b.head.tpitch = 0.1;
    yield 0.3;
    const crack = crackMesh(tp.x, tp.y, tp.z);
    const N = 6;
    yield* armSwing(N, 0.38, (i) => {
      crack.set(Math.floor(((i + 1) / N) * 9));
      snd('dig.wood', { pos: tp, volume: 0.9, pitch: [0.9, 1.1] });
      fx.chips({ x: tp.x + Math.sign(st.x - tp.x) * 0.5, y: 1.5, z: tp.z + Math.sign(st.z - tp.z) * 0.5 }, [0x6b5030, 0x4d3920], 3, { speed: 0.6 });
      if (i === 3) fx.solid.emit({ pos: { x: tp.x + 0.2, y: 4.2, z: tp.z + 0.4 }, vel: { x: 0.2, y: -0.3, z: 0.1 }, color: 0x59ae30, size: 0.14, life: 2.2, grav: 0.6, bounce: 0 });
    });
    crack.remove();
    snd('dig.wood', { pos: tp, volume: 1, pitch: 0.75 });
    fx.chips(tp, [0x6b5030, 0x4d3920, 0x7a5c38], 16, { speed: 2, up: 1.3 });
    spawnItem({ block: 'log_oak' }, { x: tp.x + Math.sign(st.x - tp.x) * 0.5, y: 1.4, z: tp.z + Math.sign(st.z - tp.z) * 0.5 }, { x: Math.sign(st.x - tp.x) * 0.8, y: 3, z: Math.sign(st.z - tp.z) * 0.8 }, { pickAt: 0.8, ground: 0 });
    b.head.tpitch = -0.2;
    yield 1.2;
    yield* waitItems();
    hold({ block: 'log_oak' });
    onCleanup(() => hold(null));
    b.head.tpitch = 0;
    yield 0.5;
    yield* craftAt([
      { taps: 2, hold: { block: 'log_oak' }, after: { block: 'planks_oak' } },
      { taps: 2, after: { item: 'stick' } },
      { taps: 3, after: { item: 'wood_pickaxe' } },
    ]);
    yield* showOff({ item: 'wood_pickaxe' }, 1.4);
    hold(null);
  }

  function* actChest() {
    yield* useFront(L.chestStand, L.chest);
    b.head.tpitch = -0.4;
    const cp = frontPos(L.chest, 0.6, 0.5);
    yield* tap(1, 0.3);
    snd('random.chestopen', { pos: cp, volume: 0.8 });
    onCleanup(() => camp.chest.setOpen(0));
    yield (dt) => { const k = Math.min(1, (camp.chest.open || 0) + dt * 3.5); camp.chest.setOpen(k); return k >= 1; };
    yield 0.5;
    // reach in and take something out
    const item = ['apple', 'diamond', 'coal'][Math.floor(R() * 3)];
    setArm('r', 1.3, -0.1);
    yield 0.4;
    snd('random.pop', { pos: cp, volume: 0.6, pitch: 1.2 });
    hold({ item });
    freeArm('r');
    yield 0.8;
    snd('random.chestclosed', { pos: cp, volume: 0.8 });
    yield (dt) => { const k = Math.max(0, camp.chest.open - dt * 4); camp.chest.setOpen(k); return k <= 0; };
    relax();
    b.head.tpitch = -0.15;
    setArm('r', 1.5, 0);
    yield 1.0;
    relax();
    hold(null);
    yield 0.4;
  }

  function* actFish() {
    const sp = L.pond.stand;
    yield* standAt(sp.x, sp.z, Math.PI / 2);
    hold({ item: 'fishing_rod_uncast' });
    const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(), new THREE.Vector3()]), new THREE.LineBasicMaterial({ color: 0xe8e8e8 }));
    line.frustumCulled = false; line.visible = false;
    const bobber = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.1, 0.1), new THREE.MeshBasicMaterial({ color: 0xd8341f }));
    bobber.visible = false;
    world.add(line, bobber);
    onCleanup(() => { hold(null); world.remove(line, bobber); });
    const tipW = new THREE.Vector3();
    const tip = () => {
      root.updateMatrixWorld(true);
      const t = b.held.geometry.userData.tip || [0.1, 0.9, 0];
      b.held.localToWorld(tipW.set(t[0], t[1], t[2]));
      return tipW;
    };
    const target = new THREE.Vector3(L.pond.bobber.x, -0.2, L.pond.bobber.z);
    const drawLine = (end, sag = 0.25) => {
      const a = tip();
      const pts = [a.clone(), a.clone().lerp(end, 0.5).add(new THREE.Vector3(0, -sag, 0)), end.clone()];
      line.geometry.setFromPoints(new THREE.CatmullRomCurve3(pts).getPoints(8));
    };
    b.head.tpitch = -0.1;
    yield 0.5;
    // cast: wind back, snap forward, the bobber flies
    setArm('r', -0.5, 0);
    yield 0.35;
    snd('random.bow', { volume: 0.5, pitch: 1.6 });
    setArm('r', 1.6, 0);
    hold({ item: 'fishing_rod_cast' });
    bobber.visible = line.visible = true;
    const from = tip().clone();
    let tt = 0;
    yield (dt) => {
      tt += dt;
      const k = Math.min(1, tt / 0.6);
      bobber.position.lerpVectors(from, target, k);
      bobber.position.y += Math.sin(k * Math.PI) * 1.4;
      drawLine(bobber.position, 0.1);
      return k >= 1;
    };
    snd('random.splash', { pos: target, volume: 0.5, pitch: 1.3 });
    fx.splash({ x: target.x, y: -0.2, z: target.z }, 8);
    setArm('r', 0.9, 0);
    // wait for the bite, the bobber bobbing
    let wt = 0; const bite = R(2.2, 4);
    yield (dt) => {
      wt += dt;
      bobber.position.set(target.x, -0.18 + Math.sin(wt * 3) * 0.025, target.z);
      if (wt > bite - 0.5) bobber.position.y -= 0.07 * Math.abs(Math.sin(wt * 18));
      drawLine(bobber.position, 0.15);
      return wt >= bite;
    };
    // pull
    snd('random.splash', { pos: target, volume: 0.8 });
    fx.splash({ x: target.x, y: -0.2, z: target.z }, 14);
    setArm('r', -0.2, 0);
    b.leanT = -0.12;
    bobber.visible = false; line.visible = false;
    const start = new THREE.Vector3(target.x, -0.2, target.z);
    const fish = spawnItem({ item: R() < 0.5 ? 'fish_cod_raw' : 'fish_cod_cooked' }, start, { x: 0, y: 0, z: 0 }, { pickAt: -1 });
    fish.state = 'custom';
    let ft = 0;
    fish.update = (dt) => {
      ft += dt;
      const k = Math.min(1, ft / 0.7);
      fish.g.position.set(lerp(start.x, b.x, k), lerp(start.y, b.y + 1.0, k) + Math.sin(k * Math.PI) * 1.6, lerp(start.z, b.z, k));
      fish.m.rotation.z += dt * 9;
      if (k >= 1) { snd('random.pop', { volume: 0.6, pitch: 1.1 }); return true; }
      return false;
    };
    yield 0.9;
    relax();
    b.leanT = 0;
    hold(null);
    yield 0.9;
  }

  function* actSit() {
    yield* walkTo(L.seatApproach.x, L.seatApproach.z);
    yield* faceYaw(Math.PI);
    // step onto the log
    ignoring('low');
    yield* walkTo(L.seatPos.x, L.seatPos.z, { straight: true, speed: 1.2 });
    yield* faceYaw(Math.PI);
    b.sitT = 1; b.sitStep = 'wood';
    onCleanup(() => { b.sitT = 0; });
    setArm('r', 0.95, -0.12); setArm('l', 0.95, 0.12);
    b.head.tpitch = -0.12;
    yield 1.2;
    for (let i = 0; i < 3; i++) {
      b.head.tyaw = 0.3; yield R(1.2, 2.2);
      b.head.tyaw = -0.25; yield R(1.2, 2);
    }
    b.head.tyaw = 0;
    yield 0.8;
    b.sitT = 0; relax();
    yield 0.6;
    yield* walkTo(L.seatApproach.x, L.seatApproach.z, { straight: true, speed: 1.2 });
  }

  function* actSunset() {
    yield* standAt(L.sunset.x, L.sunset.z, yawFor(SUN_H.x, SUN_H.z));
    b.head.tpitch = 0.08;
    yield 0.8;
    setArm('r', 2.3, 0.1);
    yield 5.5;
    relax();
    b.head.tyaw = 0.5; yield 0.6; b.head.tyaw = 0;
    yield 0.4;
  }

  // ---- the chicken: it wanders, notices him, flees in hops with its wings flapping; he follows at about a
  // block and swings. Either it gets away or a few hits end in a puff of feathers. Neither of them ever
  // stands inside the other, and both go around props.
  function* actChicken() {
    const kill = R() < 0.5;
    const sp = L.dance;
    const m = makeMob('Chicken', {});
    m.root.traverse((o) => { if (o.isMesh) o.castShadow = true; });
    const ch = { x: 6.0, z: 5.2, yaw: yawFor(-1, -0.2), y: 0, path: null, i: 0, hp: 4, hop: 0, flap: 0, t: 0, speed: 0, hurt: 0, dead: 0 };
    m.root.position.set(ch.x, 0, ch.z);
    m.root.rotation.y = ch.yaw;
    world.add(m.root);
    onCleanup(() => world.remove(m.root));
    const chPos = () => ({ x: ch.x, y: 0.4, z: ch.z });
    const CR = 0.28;
    const drawChicken = (dt, moving) => {
      ch.t += dt;
      const air = ch.hop > 0;
      m.root.position.set(ch.x, ch.y, ch.z);
      m.root.rotation.y = ch.yaw;
      m.root.rotation.z = ch.dead ? Math.min(1, ch.dead) * 1.45 : 0;
      if (m.anim) m.anim(ch.t * 1.6, dt, { walk: moving ? 1.4 : 0, flap: air ? 1.0 + Math.sin(ch.t * 34) * 0.9 : 0.0 });
    };
    // walk the chicken along its route; returns false when the route is finished
    const chStep = (dt, speed) => {
      while (ch.path && ch.i < ch.path.length) {
        const [px, pz] = ch.path[ch.i];
        const dx = px - ch.x, dz = pz - ch.z, d = Math.hypot(dx, dz);
        if (d < 0.1) { ch.i++; continue; }
        const step = Math.min(d, speed * dt);
        ch.x += (dx / d) * step; ch.z += (dz / d) * step;
        const f = nav.resolve(ch.x, ch.z, CR - 0.05); ch.x = f.x; ch.z = f.z;
        ch.yaw += wrapA(yawFor(dx, dz) - ch.yaw) * Math.min(1, dt * 14);
        return true;
      }
      return false;
    };
    // keep the two of them apart: neither stands inside the other
    const apart = () => {
      const dx = ch.x - b.x, dz = ch.z - b.z, d = Math.hypot(dx, dz) || 0.001, want = 0.82;
      if (d < want) { const f = nav.resolve(ch.x + (dx / d) * (want - d), ch.z + (dz / d) * (want - d), CR - 0.05); ch.x = f.x; ch.z = f.z; }
      const d2 = Math.hypot(ch.x - b.x, ch.z - b.z);
      if (d2 < want * 0.95) { const k = (want - d2); b.x -= ((ch.x - b.x) / (d2 || 1)) * k; b.z -= ((ch.z - b.z) / (d2 || 1)) * k; const f = nav.resolve(b.x, b.z, R_H, b.ign); b.x = f.x; b.z = f.z; }
    };
    // 1. Steve walks out; the chicken wanders into view and pecks about
    yield* standAt(sp.x - 0.8, sp.z - 0.4, yawFor(1, 0.3));
    snd('mob.chicken.say', { pos: chPos(), volume: 0.8 });
    let w = 0, wanderTo = null;
    yield (dt) => {
      w += dt;
      if (!ch.path || ch.i >= ch.path.length) {
        if (w > 0.8 && R() < 0.02 + dt) { const tx = clamp(ch.x - R(0.6, 1.6), 3, 8), tz = clamp(ch.z + R(-0.8, 0.8), 3.2, 8); ch.path = nav.path(ch.x, ch.z, tx, tz, CR, { step: 0.25 }); ch.i = 0; wanderTo = [tx, tz]; }
      }
      const moving = chStep(dt, 0.9);
      ch.hop = 0; ch.y = 0;
      drawChicken(dt, moving);
      b.head.target = new THREE.Vector3(ch.x, 0.4, ch.z);
      return w > 2.4;
    };
    void wanderTo;
    // 2. he goes after it
    snd('mob.chicken.say', { pos: chPos(), volume: 0.7, pitch: 1.2 });
    b.state = 'run';
    const FR = { x0: -9, x1: 9, z0: -2, z1: 9 };
    let fleeing = false, retarget = 0, hits = 0, sw = 0, swHit = false, hopPh = 0, route = null, rI = 0, steveRetarget = 0, giveUp = 0, outcome = null, deadT = 0;
    const chickenSpeed = kill ? 3.5 : 5.0;
    const steveSpeed = 4.3;
    const finish = { v: false };
    yield (dt) => {
      const dxs = ch.x - b.x, dzs = ch.z - b.z, dist = Math.hypot(dxs, dzs);
      // --- the chicken
      if (!ch.dead) {
        if (!fleeing && dist < 2.6) { fleeing = true; snd('mob.chicken.hurt', { pos: chPos(), volume: 0.7, pitch: 1.3 }); }
        if (fleeing) {
          retarget -= dt;
          if (retarget <= 0 || !ch.path || ch.i >= ch.path.length) {
            retarget = 0.5;
            // run away from Steve, bending toward open ground; around the props
            let ax = ch.x - b.x, az = ch.z - b.z; const al = Math.hypot(ax, az) || 1; ax /= al; az /= al;
            const bend = Math.sin(ch.t * 1.7) * 0.6;
            const tx = clamp(ch.x + (ax - az * bend) * 6, FR.x0, FR.x1), tz = clamp(ch.z + (az + ax * bend) * 6, FR.z0, FR.z1);
            const g = nav.nearestFree(tx, tz, CR);
            ch.path = nav.path(ch.x, ch.z, g.x, g.z, CR, { step: 0.25 }); ch.i = 0;
          }
          const moved = chStep(dt, ch.hurt > 0 ? 1.2 : chickenSpeed);
          hopPh += dt * 9.5;
          const hh = Math.abs(Math.sin(hopPh));
          ch.hop = hh > 0.12 ? 1 : 0;
          ch.y = hh * 0.28;
          if (Math.floor(hopPh / Math.PI) !== Math.floor((hopPh - dt * 9.5) / Math.PI)) snd('mob.chicken.step', { pos: chPos(), volume: 0.35, pitch: [0.9, 1.3] });
          drawChicken(dt, moved);
        } else { ch.hop = 0; ch.y = 0; drawChicken(dt, false); }
        if (ch.hurt > 0) ch.hurt -= dt;
      } else {
        deadT += dt; ch.dead = Math.min(1, deadT / 0.35); ch.hop = 0; ch.y = 0;
        drawChicken(dt, false);
        if (deadT > 0.9 && !finish.v) {
          finish.v = true;
          fx.chips({ x: ch.x, y: 0.3, z: ch.z }, [0xffffff, 0xeeeeee, 0xd8d8d8, 0xc02020], 16, { speed: 1.4, up: 2.2 });
          snd('random.pop', { pos: chPos(), volume: 0.7, pitch: 1.4 });
          world.remove(m.root);
          spawnItem({ item: 'feather' }, { x: ch.x, y: 0.5, z: ch.z }, { x: R(-0.3, 0.3), y: 3, z: R(-0.3, 0.3) }, { pickAt: 0.5, ground: 0 });
          outcome = 'killed';
          return true;
        }
      }
      // --- Steve: follow about a block behind, planned around everything; swing when close
      steveRetarget -= dt;
      const stand = 1.05;
      if (dist > stand + 0.12) {
        if (steveRetarget <= 0 || !b.chase || b.chaseI >= b.chase.length) {
          steveRetarget = 0.3;
          const nx = dxs / (dist || 1), nz = dzs / (dist || 1);
          const gx = ch.x - nx * stand, gz = ch.z - nz * stand;
          b.chase = nav.path(b.x, b.z, gx, gz, R_P, { ign: b.ign }); b.chaseI = 0;
        }
        while (b.chase && b.chaseI < b.chase.length) {
          const [px, pz] = b.chase[b.chaseI];
          const dx = px - b.x, dz = pz - b.z, d = Math.hypot(dx, dz);
          if (d < 0.1) { b.chaseI++; continue; }
          const sp2 = steveSpeed * clamp((dist - stand) / 0.8 + 0.35, 0.35, 1);
          const step = Math.min(d, sp2 * dt);
          b.x += (dx / d) * step; b.z += (dz / d) * step;
          const f = nav.resolve(b.x, b.z, R_H, b.ign); b.x = f.x; b.z = f.z;
          b.ampT = 1.35; b.leanT = 0.14; b.phase += step * 2.2;
          break;
        }
      } else { b.ampT = 0.2; b.leanT = 0.05; }
      b.yaw += wrapA(yawFor(dxs, dzs) - b.yaw) * Math.min(1, dt * 12);
      b.head.target = new THREE.Vector3(ch.x, 0.4, ch.z);
      apart();
      // swing at it whenever it is within reach
      if (!ch.dead) {
        sw -= dt;
        if (dist < 1.6 && sw <= 0) { sw = 0.5; swHit = false; b.swingT = 0; }
        if (b.swingT !== undefined && b.swingT < 0.4) {
          b.swingT += dt;
          const p = b.swingT / 0.4;
          setArm('r', 0.4 + Math.sin(p * Math.PI) * 1.6, 0);
          if (!swHit && p > 0.4) {
            swHit = true;
            if (Math.hypot(ch.x - b.x, ch.z - b.z) < 1.35 && kill) {
              hits++; ch.hurt = 0.35;
              snd('random.successful_hit', { pos: chPos(), volume: 0.6 });
              snd('mob.chicken.hurt', { pos: chPos(), volume: 0.8 });
              ch.x += (dxs / (dist || 1)) * 0.25; ch.z += (dzs / (dist || 1)) * 0.25;
              const f = nav.resolve(ch.x, ch.z, CR - 0.05); ch.x = f.x; ch.z = f.z;
              fx.chips({ x: ch.x, y: 0.4, z: ch.z }, [0xffffff, 0xeeeeee], 4, { speed: 0.8 });
              if (hits >= 4) { ch.dead = 0.01; deadT = 0; snd('mob.chicken.hurt', { pos: chPos(), volume: 0.9, pitch: 0.8 }); }
            }
          }
        } else if (b.swingT !== undefined) { b.r.on = false; b.swingT = undefined; }
      }
      // the end of the escape: he is left behind
      if (!kill) { giveUp += dist > 6 ? dt : 0; if (giveUp > 0.8 || Math.abs(ch.x) > 9 || ch.z > 8.6) { outcome = 'escaped'; return true; } }
      if (kill && !ch.dead) { giveUp += dt; if (giveUp > 9) { outcome = 'escaped'; return true; } }
      return false;
    };
    void route; void rI;
    b.chase = null; b.swingT = undefined;
    b.ampT = 0; b.leanT = 0; b.state = 'idle';
    b.phase = Math.round(b.phase / Math.PI) * Math.PI;
    freeArm('r');
    if (outcome === 'escaped') {
      // it hops off out of sight; he stops, arms out
      let ex = 0;
      setArm('r', 0.4, 0.9); setArm('l', 0.4, -0.9);
      yield (dt) => {
        ex += dt;
        ch.path = nav.path(ch.x, ch.z, clamp(ch.x + 6, -9, 12), ch.z + 2, CR, { step: 0.25 }); ch.i = 0;
        chStep(dt, 5); hopPh += dt * 9.5; ch.y = Math.abs(Math.sin(hopPh)) * 0.28; ch.hop = 1;
        drawChicken(dt, true);
        b.head.target = new THREE.Vector3(ch.x, 0.4, ch.z);
        return ex > 1.6;
      };
      fx.chips({ x: ch.x, y: 0.4, z: ch.z }, [0xffffff, 0xeeeeee], 8, { speed: 1 });
      world.remove(m.root);
      b.head.target = null;
      snd('mob.villager.no', { volume: 0.6, pitch: 0.95 });
      b.head.tyaw = 0.5; yield 0.3; b.head.tyaw = -0.5; yield 0.3; b.head.tyaw = 0;
      yield 0.8;
      relax();
    } else {
      // a feather dropped: pick it up, look at it
      b.head.target = null;
      yield* waitItems();
      hold({ item: 'feather' });
      setArm('r', 1.5, 0); b.head.tpitch = -0.2;
      yield 1.3;
      relax(); hold(null);
    }
  }

  function* actPillarFull() {
    const sp = L.pillar;
    yield* standAt(sp.x, sp.z, Math.PI);
    const blocks = [];
    ignoring('placed');
    onCleanup(() => { b.floor = 0; b.air = false; b.y = 0; for (const e of blocks) { world.remove(e.m); nav.remove(e.box); } b.extras = b.extras.filter((e) => !blocks.includes(e)); });
    for (let lvl = 0; lvl < 2; lvl++) {
      yield 0.25;
      jump(7.8);
      b.head.tpitch = -0.9;
      setArm('r', 1.0, 0);
      yield () => b.vy < 0;
      blocks.push(placeBlock('dirt.png', sp.x, lvl, sp.z));
      b.floor = lvl + 1;
      yield* waitLanded();
      freeArm('r');
    }
    b.head.tpitch = 0;
    yield 0.3;
    const y0 = b.yaw;
    b.head.tyaw = 1.0; yield 0.8; b.head.tyaw = -1.0; yield 1.0; b.head.tyaw = 0;
    let acc = 0;
    yield (dt) => { const d = dt * 2.6; b.yaw += d; acc += d; return acc >= TAU; };
    b.yaw = y0;
    yield 0.4;
    // dig down
    hold({ item: 'wood_pickaxe' });
    onCleanup(() => hold(null));
    b.head.tpitch = -0.8;
    for (let lvl = 1; lvl >= 0; lvl--) {
      const blk = blocks[lvl];
      yield* armSwing(3, 0.28, () => { snd('dig.gravel', { pos: { x: sp.x, y: lvl + 0.5, z: sp.z }, volume: 0.6, pitch: [0.9, 1.1] }); });
      breakBlock(blk, { x: sp.x, y: lvl + 0.5, z: sp.z }, 'dirt.png');
      spawnItem({ block: 'dirt' }, { x: sp.x, y: lvl + 0.6, z: sp.z }, { x: R(-0.5, 0.5), y: 2.6, z: R(0.6, 1.2) }, { pickAt: 1.0 });
      b.floor = lvl; b.air = true; b.vy = 0;
      yield* waitLanded();
    }
    b.head.tpitch = 0;
    hold(null);
    relax();
    yield 1.2;
  }

  function* actDance() {
    const sp = L.dance;
    yield* standAt(sp.x, sp.z, yawFor(b.camPos.x - sp.x, b.camPos.z - sp.z));
    yield 0.3;
    const notes = [1, 1.26, 1.5, 1.26, 1, 1.5, 1.68, 1.5];
    let tt = 0;
    const base = b.yaw;
    yield (dt) => {
      const prev = tt; tt += dt;
      const bt = tt / 0.28;
      const i = Math.floor(bt);
      if (i !== Math.floor(prev / 0.28) && i < 12) {
        snd('note.harp', { volume: 0.5, pitch: notes[i % notes.length] * 0.9 });
        fx.sparks({ x: b.x + R(-0.4, 0.4), y: b.y + 2.1, z: b.z + R(-0.4, 0.4) }, 0xffe27a, 3, { speed: 0.6 });
      }
      const ph = bt * Math.PI;
      // arms pump across the body, hips and head bob, then a turn
      const up = Math.sin(ph);
      b.r.on = b.l.on = true;
      b.r.tx = 2.9 * Math.max(0, up) - 0.2; b.l.tx = 2.9 * Math.max(0, -up) - 0.2;
      b.r.tz = -0.35; b.l.tz = 0.35;
      b.twist = Math.sin(ph) * 0.35;
      b.head.tyaw = Math.sin(ph) * -0.3; b.head.tpitch = Math.abs(Math.cos(ph)) * -0.2;
      b.y = Math.abs(Math.sin(ph)) * 0.12;
      b.floor = 0;
      if (bt > 8) b.yaw = base + smooth((bt - 8) / 4) * TAU;
      // the feet stay planted: no stride while he dances
      b.ampT = 0;
      return bt >= 12;
    };
    b.yaw = base;
    relax();
    yield 0.8;
  }

  function* actSneak() {
    const sp = L.sneak;
    yield* walkTo(sp.x, sp.z, { crouch: true, speed: 1.0, onStep: () => { b.crouchT = 1; b.sitStep = null; } });
    yield* faceYaw(yawFor(-1, -0.2));
    for (let i = 0; i < 7; i++) {
      b.crouchT = i % 2 ? 0 : 1;
      if (i % 2) snd('step.grass', { volume: 0.25, pitch: 1.4 });
      yield 0.16;
    }
    b.crouchT = 0;
    yield 0.6;
    b.head.tyaw = 0.6; yield 0.5; b.head.tyaw = 0; yield 0.4;
    relax();
  }

  const ACTS = [
    { id: 'tree', f: actWood }, { id: 'mine', f: actMine }, { id: 'iron', f: actIron }, { id: 'chest', f: actChest },
    { id: 'place', f: actPlace }, { id: 'fish', f: actFish }, { id: 'sit', f: actSit }, { id: 'sunset', f: actSunset },
    { id: 'chicken', f: actChicken }, { id: 'pillar', f: actPillarFull }, { id: 'dance', f: actDance }, { id: 'sneak', f: actSneak },
  ];
  const ALIAS = { craft: 'iron', wood: 'tree' };
  const byId = (id) => ACTS.find((a) => a.id === (ALIAS[id] || id));

  // A day in the camp: gather wood, mine stone, smelt iron and craft, then something to unwind (a shuffled
  // pick of the rest) before the chest. The chains are in order so the item in his hand always makes sense.
  function nextAct() {
    if (!b.plan.length) {
      const fun = ['place', 'fish', 'sit', 'sunset', 'chicken', 'pillar', 'dance', 'sneak'].sort(() => rng() - 0.5);
      b.plan = ['tree', 'mine', fun[0], 'iron', fun[1], 'chest', fun[2]];
      if (b.plan[0] === b.lastId) b.plan.push(b.plan.shift());
    }
    return b.plan.shift();
  }
  function* idleLoop() {
    for (;;) {
      const id = nextAct();
      const a = byId(id);
      b.lastId = id;
      b.act = id;
      try { yield* a.f(); } finally { doCleanup(); relax(); }
      b.act = null;
      // a breath between things: a glance at the camera
      if (R() < 0.5) b.head.target = b.camPos;
      yield R(0.5, 1.4);
      b.head.target = null; b.head.tyaw = 0; b.head.tpitch = 0;
    }
  }

  // ------------------------------------------------------------ the call (a Lucky Block fell)
  function* callGen() {
    doCleanup(); relax(); hold(null);
    b.air = false; b.floor = 0; b.vy = 0; b.y = Math.max(0, b.y);
    b.state = 'alert'; b.ampT = 0; b.leanT = 0;
    showBang();
    snd('qf.exclaim', { volume: 0.8 });
    b.head.target = new THREE.Vector3(0.5, 2.2, 0.5);
    setArm('r', 0.0, 0.3); setArm('l', 0.0, -0.3);
    // he flinches back, then turns hard to the dais
    yield* faceDir(0.5 - b.x, 0.5 - b.z, 18);
    yield 0.3;
    relax();
    b.state = 'run';
    yield* walkTo(2.7, 0.5, { sprint: true, speed: 6.2, turn: 12 });
    // hop up beside the block
    b.state = 'hop';
    b.ampT = 0; b.leanT = 0;
    ignoring('dais');
    yield* faceYaw(Math.PI / 2, 16);
    const x0 = b.x, x1 = 1.6;
    let u = 0;
    snd('step.stone', { volume: 0.2 });
    yield (dt) => {
      u += dt / 0.5;
      const k = Math.min(1, u);
      b.x = lerp(x0, x1, smooth(k));
      b.air = false;
      b.y = smooth(k) * 1.0 + Math.sin(k * Math.PI) * 0.45;
      b.phase += dt * 6;
      b.ampT = 0.8;
      return k >= 1;
    };
    b.floor = 1; b.y = 1; b.ampT = 0;
    snd('step.stone', { volume: 0.6 });
    fx.dust({ x: 1.6, y: 1, z: 0.5 }, 5);
    b.state = 'mine';
    b.arrivedAt = b.t;
    hold({ item: 'iron_pickaxe' });
    b.head.target = new THREE.Vector3(0.5, 1.7, 0.5);
    // swing until the page ends the break
    let sw = 0;
    yield (dt) => {
      sw += dt;
      const p = (sw % 0.5) / 0.5;
      b.swingClock = sw;
      const f1 = 1 - Math.pow(1 - p, 3);
      setArm('r', 0.5 + Math.sin(f1 * Math.PI) * 1.1 - Math.sin(p * Math.PI) * 0.5, 0);
      b.twist = Math.sin(Math.sqrt(p) * TAU) * 0.2;
      return false;
    };
  }
  function* afterGen() {
    doCleanup();
    b.state = 'after';
    freeArm('r'); b.twist = 0; hold(null);
    b.head.target = null;
    ignoring('dais');
    yield 0.35;
    // hop down, walk back to his place for the scene
    const x0 = b.x;
    let u = 0;
    b.floor = 0;
    yield (dt) => {
      u += dt / 0.4;
      const k = Math.min(1, u);
      b.x = lerp(x0, 2.7, smooth(k));
      b.y = (1 - smooth(k)) * 1.0 + Math.sin(k * Math.PI) * 0.3;
      return k >= 1;
    };
    b.y = 0;
    b.ign.delete('dais');
    yield* walkTo(3.2, 0.5, { speed: 1.8 });
    yield* faceYaw(Math.PI / 2, 8);
    b.state = 'ready';
    yield () => false;
  }

  // ------------------------------------------------------------ the runner
  function startGen(g) { if (b.gen) { try { b.gen.return(); } catch (e) { /* ignore */ } } doCleanup(); b.ign.clear(); b.gen = g; b.wait = 0; b.fn = null; }
  function runGen(dt) {
    if (b.frozen || !b.gen) return;
    for (let guard = 0; guard < 12; guard++) {
      if (b.fn) { if (b.fn(dt)) { b.fn = null; dt = 0; } else return; }
      if (b.wait > 0) { b.wait -= dt; dt = 0; if (b.wait > 0) return; }
      let r;
      try { r = b.gen.next(); } catch (e) { console.error('steve', e); b.gen = idleLoop(); return; }
      if (r.done) { b.gen = idleLoop(); return; }
      const v = r.value;
      if (typeof v === 'function') b.fn = v; else if (typeof v === 'number') b.wait = v;
    }
  }

  // ------------------------------------------------------------ public
  function headTrack() {
    const h = b.head;
    if (h.target) {
      const dx = h.target.x - b.x, dz = h.target.z - b.z;
      const yaw = clamp(wrapA(yawFor(dx, dz) - b.yaw), -1.1, 1.1);
      const hd = Math.hypot(dx, dz);
      h.tyaw = yaw;
      h.tpitch = clamp(Math.atan2(h.target.y - (b.y + 1.55), Math.max(0.3, hd)), -0.8, 0.8);
    }
  }
  // the one rule that matters: whatever the activity did, he does not end a frame inside a prop
  function keepOut() {
    const f = nav.resolve(b.x, b.z, R_H, b.ign);
    if (Math.hypot(f.x - b.x, f.z - b.z) > 0.02) nav.stats.pushed = (nav.stats.pushed || 0) + 1;
    b.x = f.x; b.z = f.z;
    nav.track('steve', b.x, b.z, R_H, b.ign);
  }
  const api = {
    state: () => b.state,
    arrivedAt: () => b.arrivedAt,
    mineClock: () => (b.state === 'mine' ? b.swingClock : -1),
    activity: () => b.act || null,
    x: () => b.x, z: () => b.z,
    pos: () => ({ x: b.x, y: b.y, z: b.z }),
    hand: () => (b.heldSpec ? (b.heldSpec.item || b.heldSpec.block) : null),
    reset(newSeed) {
      rng = mulberry(newSeed ?? seed);
      startGen(null);
      b.gen = null; b.fn = null; b.wait = 0; b.plan = []; b.lastId = null; b.act = null; b.frozen = false;
      for (const it of b.items) world.remove(it.g);
      b.items.length = 0;
      for (const e of b.extras) { world.remove(e.m); nav.remove(e.box); }
      b.extras.length = 0;
      if (b.bang) b.bang.visible = false;
      hold(null);
      for (const q of camp.quarry) { q.mesh.visible = true; q.removed = false; nav.restore(q.box); }
      camp.chest.setOpen(0);
      camp.setFurnace(false);
      Object.assign(b, { x: 3.2, z: 0.5, y: 0, vy: 0, floor: 0, air: false, yaw: Math.PI / 2, phase: 0, amp: 0, ampT: 0, sit: 0, sitT: 0, crouch: 0, crouchT: 0, lean: 0, leanT: 0, twist: 0, state: 'idle', arrivedAt: -1, swingClock: 0 });
      b.r.on = b.l.on = false; b.r.w = b.l.w = 0;
      b.head.tyaw = b.head.tpitch = b.head.yaw = b.head.pitch = 0; b.head.target = null;
      b.gen = idleLoop();
      for (const k of Object.keys(P)) { P[k].rotation.set(rest[k].rx, rest[k].ry, rest[k].rz); P[k].position.set(rest[k].x, rest[k].y, rest[k].z); }
    },
    resume() { b.frozen = false; relax(); b.state = 'idle'; startGen(idleLoop()); },
    call() { b.frozen = false; startGen(callGen()); },
    afterBreak() { startGen(afterGen()); },
    // the scene takes over: put Steve at his scene mark
    freeze() {
      b.frozen = true;
      startGen(null); b.gen = null;
      Object.assign(b, { x: 3.2, z: 0.5, y: 0, floor: 0, yaw: Math.PI / 2, ampT: 0, amp: 0, sitT: 0, sit: 0, crouchT: 0, crouch: 0, leanT: 0, lean: 0, twist: 0, state: 'scene' });
      b.r.on = b.l.on = false; b.r.w = b.l.w = 0;
      hold(null);
      if (b.bang) b.bang.visible = false;
      for (const k of Object.keys(P)) { P[k].rotation.set(rest[k].rx, rest[k].ry, rest[k].rz); P[k].position.set(rest[k].x, rest[k].y, rest[k].z); }
      root.position.set(3.2, 0, 0.5); root.rotation.set(0, Math.PI / 2, 0);
    },
    update(dt, camPos) {
      dt = Math.min(dt, 0.05);
      if (camPos) b.camPos.copy(camPos);
      b.t += dt;
      if (!b.frozen) {
        runGen(dt);
        keepOut();
        headTrack();
        applyPose(dt);
        stepBang();
        stepExtras(dt);
      }
      stepItems(dt);
      if (pendingItems.size) refreshItems();
      {
        const cx = b.camPos.x - root.position.x, cz = b.camPos.z - root.position.z, d = Math.hypot(cx, cz) || 1;
        fill.position.set(root.position.x + (cx / d) * 2.2, root.position.y + 1.9, root.position.z + (cz / d) * 2.2);
      }
      // ambience tied to the camp
      b.fireT -= dt;
      if (b.fireT <= 0) { b.fireT = R(2.6, 4.2); play('fire.fire', { pos: { x: L.fireCenter.x, y: 1, z: L.fireCenter.z }, volume: 0.5, ref: 5 }); }
    },
    // fast-forward the behaviour with no one watching (the ?idle= hook)
    fastForward(ms, camPos) { for (let t = 0; t < ms; t += 33) api.update(0.033, camPos); nav.publish(); },
    setSkin(mat) { void mat; },
    startIdle() { b.gen = idleLoop(); },
    // debug hook (?act=): run one named activity first, then the normal loop
    start(id) {
      const a = byId(id);
      if (!a) return false;
      b.act = a.id;
      startGen((function* () { try { yield* a.f(); } finally { doCleanup(); relax(); } b.act = null; yield* idleLoop(); })());
      return true;
    },
    acts: () => ACTS.map((a) => a.id),
  };
  b.gen = idleLoop();
  api.reset(seed);
  return api;
}
