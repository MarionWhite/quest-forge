// Steve's life on the plateau: a loop of small activities with natural walking between them, and the
// call sequence for a Lucky Block ("!", sprint, hop onto the dais, mine). Written as coroutines:
// an activity is a generator that yields a number (wait seconds) or a function(dt) -> done.
import * as THREE from 'three';
import { tex, mulberry } from './stage.js';
import { L } from './camp.js';
import { makeMob } from './mobs.js';

const TAU = Math.PI * 2;
const wrapA = (a) => { a = (a + Math.PI) % TAU; if (a < 0) a += TAU; return a - Math.PI; };
const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
const lerp = (a, b, k) => a + (b - a) * k;
const smooth = (x) => { x = clamp(x, 0, 1); return x * x * (3 - 2 * x); };
export const yawFor = (dx, dz) => Math.atan2(-dx, -dz); // front is -z at yaw 0
const dirOf = (yaw) => ({ x: -Math.sin(yaw), z: -Math.cos(yaw) });
const SUN_H = { x: -0.13, z: -0.99 };

// ---------------------------------------------------------------- navigation grid
const G = { x0: -12, z0: -10, x1: 12, z1: 8, s: 0.5 };
G.w = Math.round((G.x1 - G.x0) / G.s); G.h = Math.round((G.z1 - G.z0) / G.s);
function makeNav(obstacles) {
  const blocked = new Uint8Array(G.w * G.h);
  const inObs = (x, z, m = 0) => obstacles.some((r) => x > r[0] - m && x < r[2] + m && z > r[1] - m && z < r[3] + m);
  for (let i = 0; i < G.w; i++) for (let j = 0; j < G.h; j++) {
    const x = G.x0 + (i + 0.5) * G.s, z = G.z0 + (j + 0.5) * G.s;
    if (inObs(x, z, 0.1)) blocked[j * G.w + i] = 1;
  }
  const cell = (x, z) => [clamp(Math.floor((x - G.x0) / G.s), 0, G.w - 1), clamp(Math.floor((z - G.z0) / G.s), 0, G.h - 1)];
  const free = (x, z) => { const [i, j] = cell(x, z); return !blocked[j * G.w + i] && x > G.x0 && x < G.x1 && z > G.z0 && z < G.z1; };
  const clear = (ax, az, bx, bz) => {
    const n = Math.ceil(Math.hypot(bx - ax, bz - az) / 0.2);
    for (let k = 0; k <= n; k++) if (!free(lerp(ax, bx, k / n), lerp(az, bz, k / n))) return false;
    return true;
  };
  // A*: returns waypoints from (ax,az) to (bx,bz) (the last is exactly b)
  function path(ax, az, bx, bz) {
    if (clear(ax, az, bx, bz)) return [[bx, bz]];
    const nearest = (x, z) => {
      let [i, j] = cell(x, z);
      if (!blocked[j * G.w + i]) return [i, j];
      for (let r = 1; r < 8; r++) for (let di = -r; di <= r; di++) for (let dj = -r; dj <= r; dj++) {
        const ii = i + di, jj = j + dj;
        if (ii >= 0 && jj >= 0 && ii < G.w && jj < G.h && !blocked[jj * G.w + ii]) return [ii, jj];
      }
      return [i, j];
    };
    const [si, sj] = nearest(ax, az), [ti, tj] = nearest(bx, bz);
    const N = G.w * G.h, g = new Float32Array(N).fill(1e9), from = new Int32Array(N).fill(-1), closed = new Uint8Array(N);
    const open = [[si + sj * G.w, 0]];
    g[si + sj * G.w] = 0;
    const hf = (i, j) => Math.hypot(i - ti, j - tj);
    let found = false;
    while (open.length) {
      let bi = 0;
      for (let k = 1; k < open.length; k++) if (open[k][1] < open[bi][1]) bi = k;
      const [cur] = open.splice(bi, 1)[0];
      if (closed[cur]) continue;
      closed[cur] = 1;
      const ci = cur % G.w, cj = (cur / G.w) | 0;
      if (ci === ti && cj === tj) { found = true; break; }
      for (let di = -1; di <= 1; di++) for (let dj = -1; dj <= 1; dj++) {
        if (!di && !dj) continue;
        const ni = ci + di, nj = cj + dj;
        if (ni < 0 || nj < 0 || ni >= G.w || nj >= G.h) continue;
        const nk = ni + nj * G.w;
        if (blocked[nk] || closed[nk]) continue;
        if (di && dj && (blocked[ci + nj * G.w] || blocked[ni + cj * G.w])) continue;
        const ng = g[cur] + Math.hypot(di, dj);
        if (ng < g[nk]) { g[nk] = ng; from[nk] = cur; open.push([nk, ng + hf(ni, nj)]); }
      }
    }
    if (!found) return [[bx, bz]];
    const pts = [];
    for (let k = ti + tj * G.w; k !== -1; k = from[k]) pts.push([G.x0 + ((k % G.w) + 0.5) * G.s, G.z0 + (((k / G.w) | 0) + 0.5) * G.s]);
    pts.reverse();
    pts.push([bx, bz]);
    // string-pull
    const out = [];
    let cx = ax, cz = az, i = 0;
    while (i < pts.length) {
      let far = i;
      for (let k = pts.length - 1; k > i; k--) if (clear(cx, cz, pts[k][0], pts[k][1])) { far = k; break; }
      out.push(pts[far]); cx = pts[far][0]; cz = pts[far][1]; i = far + 1;
    }
    return out;
  }
  return { path, free, clear };
}

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
  const nav = makeNav(camp.obstacles);
  let rng = mulberry(seed);
  const R = (a = 0, b = 1) => a + rng() * (b - a);
  const rest = {};
  for (const k of Object.keys(P)) rest[k] = { x: P[k].position.x, y: P[k].position.y, z: P[k].position.z, rx: P[k].rotation.x, ry: P[k].rotation.y, rz: P[k].rotation.z };
  const matCache = new Map();
  const texMat = (file) => {
    if (!matCache.has(file)) matCache.set(file, new THREE.MeshLambertMaterial({ map: tex(file) }));
    return matCache.get(file);
  };
  const flatMat = (file) => {
    const k = 'flat:' + file;
    if (!matCache.has(k)) matCache.set(k, new THREE.MeshBasicMaterial({ map: tex(file), transparent: true, alphaTest: 0.4, side: THREE.DoubleSide }));
    return matCache.get(k);
  };

  const b = {
    t: 0, x: 3.2, z: 0.5, y: 0, vy: 0, floor: 0, air: false, yaw: Math.PI / 2, phase: 0, amp: 0, ampT: 0,
    sit: 0, sitT: 0, crouch: 0, crouchT: 0, lean: 0, leanT: 0, twist: 0, bob: 0,
    r: { x: 0, z: 0, w: 0, on: false, tx: 0, tz: 0 }, l: { x: 0, z: 0, w: 0, on: false, tx: 0, tz: 0 },
    head: { yaw: 0, pitch: 0, tyaw: 0, tpitch: 0, target: null },
    state: 'idle', frozen: false, gen: null, wait: 0, fn: null, cleanups: [], lastAct: -1, bag: [],
    camPos: new THREE.Vector3(7.6, 3.4, 10.2), stepIdx: 0, arrivedAt: -1, swingClock: 0, mining: false,
    held: null, bang: null, items: [], extras: [], fireT: 2, ambT: 5, turnRate: 9,
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

  // ------------------------------------------------------------ held item, drops, the "!"
  function hold(spec) {
    if (b.held) { b.held.parent && b.held.parent.remove(b.held); b.held = null; }
    if (!spec) return;
    let m;
    if (spec.cube) {
      m = new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.3, 0.3), texMat(spec.cube));
      m.position.set(0, -0.58, -0.22);
      m.rotation.set(0.2, 0.7, 0);
    } else {
      m = new THREE.Mesh(new THREE.PlaneGeometry(0.62, 0.62), flatMat(spec.tex));
      m.position.set(0.0, -0.5, -0.3);
      m.rotation.set(0, Math.PI / 2, 0.15);
    }
    m.castShadow = false;
    P.rArm.add(m);
    b.held = m;
  }
  function spawnItem(spec, pos, vel, o = {}) {
    const g = new THREE.Group();
    let m;
    if (spec.cube) m = new THREE.Mesh(new THREE.BoxGeometry(0.26, 0.26, 0.26), texMat(spec.cube));
    else m = new THREE.Mesh(new THREE.PlaneGeometry(0.42, 0.42), flatMat(spec.tex));
    g.add(m);
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
        if (it.pickAt >= 0 && it.age > it.pickAt && it.state !== 'rest') { /* wait to land */ }
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
    // the hand-held item follows the arm; the "!" and items step themselves
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
  function* walkTo(x, z, o = {}) {
    const speed = o.speed ?? 2.1;
    const pts = o.straight ? [[x, z]] : nav.path(b.x, b.z, x, z);
    b.state = o.sprint ? 'run' : 'walk';
    for (let i = 0; i < pts.length; i++) {
      const [px, pz] = pts[i];
      const last = i === pts.length - 1;
      yield (dt) => {
        const dx = px - b.x, dz = pz - b.z, d = Math.hypot(dx, dz);
        if (d < (last ? 0.08 : 0.4)) return true;
        const want = yawFor(dx, dz);
        const diff = wrapA(want - b.yaw);
        b.yaw += diff * Math.min(1, dt * (o.turn ?? 8));
        const align = 1 - Math.min(1, Math.abs(diff) / 1.4) * 0.85;
        const slow = last ? clamp(d / 0.6, 0.35, 1) : 1;
        const sp = speed * align * slow;
        const step = Math.min(d, sp * dt);
        b.x += (dx / d) * step; b.z += (dz / d) * step;
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
  };
  const palette = (f) => PALETTES[f] || PALETTES['stone.png'];
  const DIG = { 'stone.png': 'dig.stone', 'coal_ore.png': 'dig.stone', 'iron_ore.png': 'dig.stone', 'cobblestone.png': 'dig.stone', 'dirt.png': 'dig.gravel', 'planks_oak.png': 'dig.wood' };

  // a block placed by Steve (a cube that pops in)
  function placeBlock(file, x, y, z) {
    const m = new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), texMat('blocks/' + file));
    m.position.set(x, y + 0.5, z);
    m.castShadow = m.receiveShadow = true;
    world.add(m);
    const blk = { m, t: 0, file };
    b.extras.push(blk);
    onCleanup(() => { world.remove(m); const i = b.extras.indexOf(blk); if (i >= 0) b.extras.splice(i, 1); });
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
    const i = b.extras.indexOf(blk); if (i >= 0) b.extras.splice(i, 1);
  }

  // ------------------------------------------------------------ the activities
  function* standAt(x, z, yaw, o = {}) {
    yield* walkTo(x, z, o);
    yield* faceYaw(yaw);
  }

  function* actMine() {
    const avail = camp.quarry.filter((q) => !q.removed && !(q.y > 1 && false));
    // a top block can only be taken if it is still there; the supporting block under it is left alone
    const choices = avail.filter((q) => !(q.kind === 'stone' && q.y < 1 && camp.quarry.some((o) => o !== q && !o.removed && o.x === q.x && o.y > q.y)));
    if (!choices.length) return;
    const q = choices[Math.floor(R() * choices.length)];
    yield* standAt(q.x, L.quarryStandZ + (q.y > 1 ? 0 : 0), 0);
    hold({ tex: 'items/iron_pickaxe.png' });
    onCleanup(() => hold(null));
    b.head.tpitch = q.y > 1 ? 0.1 : -0.15;
    const crack = crackMesh(q.x, q.y, q.z);
    yield 0.25;
    let hits = 0;
    const N = 6;
    yield* armSwing(N, 0.4, (i) => {
      hits++;
      crack.set(Math.floor(((i + 1) / N) * 9));
      snd(DIG[q.file], { pos: { x: q.x, y: q.y, z: q.z }, volume: 0.8, pitch: [0.85, 1.05] });
      fx.chips({ x: q.x, y: q.y, z: q.z + 0.5 }, palette(q.file), 3, { speed: 0.8 });
    });
    crack.remove();
    q.mesh.visible = false; q.removed = true;
    onCleanup(() => { q.mesh.visible = true; q.removed = false; q.mesh.scale.setScalar(1); });
    snd('dig.stone', { pos: { x: q.x, y: q.y, z: q.z }, volume: 1, pitch: 0.75 });
    fx.chips({ x: q.x, y: q.y, z: q.z }, palette(q.file), 18, { speed: 2, up: 1.3 });
    spawnItem({ cube: 'blocks/' + q.file }, { x: q.x, y: q.y, z: q.z + 0.4 }, { x: R(-0.4, 0.4), y: 4, z: 1.4 }, { pickAt: 0.9, ground: 0 });
    yield 1.5;
    // put it back: the next visitor finds the quarry whole
    b.head.tpitch = 0;
    yield* armSwing(1, 0.35, () => {
      q.mesh.visible = true; q.removed = false; q.mesh.scale.setScalar(1);
      snd('dig.stone', { pos: { x: q.x, y: q.y, z: q.z }, volume: 0.8, pitch: 1.1 });
      fx.chips({ x: q.x, y: q.y, z: q.z + 0.5 }, palette(q.file), 5, { speed: 0.8 });
    });
    yield 0.6;
    hold(null);
  }

  function* actPlace() {
    const sp = L.build;
    yield* standAt(sp.x, sp.z, Math.PI);
    hold({ cube: 'blocks/cobblestone.png' });
    onCleanup(() => hold(null));
    yield 0.2;
    const bl = [];
    yield* armSwing(1, 0.35, () => { bl.push(placeBlock('cobblestone.png', sp.cx + 0.5, 0, sp.cz + 0.5)); });
    yield 0.5;
    b.head.tpitch = 0.25;
    yield* armSwing(1, 0.35, () => { bl.push(placeBlock('cobblestone.png', sp.cx + 0.5, 1, sp.cz + 0.5)); });
    b.head.tpitch = 0;
    yield 1.1;
    hold({ tex: 'items/wood_pickaxe.png' });
    for (const blk of bl.reverse()) {
      const p = { x: blk.m.position.x, y: blk.m.position.y, z: blk.m.position.z };
      const crack = crackMesh(p.x, p.y, p.z);
      yield* armSwing(3, 0.3, (i) => { crack.set((i + 1) * 3); snd('dig.stone', { pos: p, volume: 0.7, pitch: [0.9, 1.1] }); });
      crack.remove();
      breakBlock(blk, p, 'cobblestone.png');
      spawnItem({ cube: 'blocks/cobblestone.png' }, p, { x: R(-0.3, 0.3), y: 3.2, z: 1.2 }, { pickAt: 0.7 });
      yield 0.5;
    }
    yield 0.6;
    hold(null);
  }

  function* actCraft() {
    // the furnace first, then the table
    yield* standAt(L.furnaceStand.x, L.furnaceStand.z, Math.PI);
    b.head.tpitch = -0.35;
    setArm('r', 1.0, -0.1); setArm('l', 1.0, 0.1);
    snd('random.click', { volume: 0.6 });
    yield 1.4;
    snd('fire.ignite', { pos: { x: L.furnace.cx + 0.5, y: 0.5, z: L.furnace.cz + 0.8 }, volume: 0.5 });
    yield 1.6;
    spawnItem({ tex: 'items/iron_ingot.png' }, { x: L.furnace.cx + 0.5, y: 1.1, z: L.furnace.cz + 0.4 }, { x: 0, y: 3.4, z: -1.2 }, { pickAt: 0.8, ground: 0 });
    yield 1.3;
    relax();
    yield* standAt(L.tableStand.x, L.tableStand.z, Math.PI);
    b.head.tpitch = -0.45;
    for (let i = 0; i < 6; i++) {
      setArm(i % 2 ? 'l' : 'r', 1.15 + (i % 3) * 0.1, i % 2 ? 0.25 : -0.25);
      freeArm(i % 2 ? 'r' : 'l');
      snd('random.click', { pos: { x: L.table.cx + 0.5, y: 1, z: L.table.cz + 0.5 }, volume: 0.45, pitch: [0.9, 1.3] });
      yield 0.33;
    }
    relax();
    const file = ['items/wood_pickaxe.png', 'items/bread.png', 'items/stick.png'][Math.floor(R() * 3)];
    spawnItem({ tex: file }, { x: L.table.cx + 0.5, y: 1.05, z: L.table.cz + 0.55 }, { x: 0, y: 4, z: 0.6 }, { pickAt: 0.9 });
    snd('random.pop', { pos: { x: L.table.cx + 0.5, y: 1, z: L.table.cz + 0.5 }, volume: 0.7, pitch: 1.2 });
    yield 1.4;
    hold({ tex: file }); onCleanup(() => hold(null));
    setArm('r', 1.6, 0); b.head.tpitch = -0.2;
    yield 1.2;
    relax();
    hold(null);
  }

  function* actChest() {
    yield* standAt(L.chestStand.x, L.chestStand.z, Math.PI);
    const cp = { x: L.chest.cx + 0.5, y: 0.6, z: L.chest.cz + 0.5 };
    b.head.tpitch = -0.4;
    setArm('r', 1.2, -0.15); setArm('l', 1.2, 0.15);
    yield 0.4;
    snd('random.chestopen', { pos: cp, volume: 0.8 });
    onCleanup(() => camp.chest.setOpen(0));
    yield (dt) => { const k = Math.min(1, (camp.chest.open || 0) + dt * 4); camp.chest.setOpen(k); return k >= 1; };
    yield 0.5;
    spawnItem({ tex: ['items/apple.png', 'items/diamond.png', 'items/coal.png'][Math.floor(R() * 3)] }, { x: cp.x, y: 1, z: cp.z + 0.3 }, { x: 0, y: 3.4, z: 0.8 }, { pickAt: 0.8 });
    yield 1.4;
    snd('random.chestclosed', { pos: cp, volume: 0.8 });
    yield (dt) => { const k = Math.max(0, camp.chest.open - dt * 5); camp.chest.setOpen(k); return k <= 0; };
    relax();
    yield 0.5;
  }

  function* actFish() {
    const sp = L.pond.stand;
    yield* standAt(sp.x, sp.z, Math.PI / 2);
    hold({ tex: 'items/fishing_rod_uncast.png' });
    const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(), new THREE.Vector3()]), new THREE.LineBasicMaterial({ color: 0xe8e8e8 }));
    line.frustumCulled = false; line.visible = false;
    const bobber = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.1, 0.1), new THREE.MeshBasicMaterial({ color: 0xd8341f }));
    bobber.visible = false;
    world.add(line, bobber);
    onCleanup(() => { hold(null); world.remove(line, bobber); });
    const tipW = new THREE.Vector3();
    const tip = () => { root.updateMatrixWorld(true); b.held.localToWorld(tipW.set(0.28, 0.28, 0)); return tipW; };
    const target = new THREE.Vector3(L.pond.bobber.x, -0.2, L.pond.bobber.z);
    const drawLine = (end, sag = 0.25) => {
      const a = tip(), pos = line.geometry.attributes.position;
      const pts = [a.clone(), a.clone().lerp(end, 0.5).add(new THREE.Vector3(0, -sag, 0)), end.clone()];
      line.geometry.setFromPoints(new THREE.CatmullRomCurve3(pts).getPoints(8));
      void pos;
    };
    b.head.tpitch = -0.1;
    yield 0.5;
    // cast: wind back, snap forward, the bobber flies
    setArm('r', -0.5, 0);
    yield 0.35;
    snd('random.bow', { volume: 0.5, pitch: 1.6 });
    setArm('r', 1.6, 0);
    hold({ tex: 'items/fishing_rod_cast.png' });
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
    const fish = spawnItem({ tex: Math.random() < 0.5 ? 'items/fish_cod_raw.png' : 'items/fish_cod_cooked.png' }, start, { x: 0, y: 0, z: 0 }, { pickAt: -1 });
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
    yield 0.4;
    // hold the catch up for a moment
    yield 0.5;
  }

  function* actSit() {
    yield* walkTo(L.seatApproach.x, L.seatApproach.z);
    yield* faceYaw(Math.PI);
    // step onto the log
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

  function* actTree() {
    const sp = L.tree.stand;
    yield* standAt(sp.x, sp.z, Math.PI / 2);
    const tp = { x: L.tree.cx + 0.5, y: 1.2, z: L.tree.cz + 0.5 };
    yield 0.3;
    yield* armSwing(5, 0.38, (i) => {
      snd('dig.wood', { pos: tp, volume: 0.9, pitch: [0.9, 1.1] });
      fx.chips({ x: tp.x + 0.5, y: 1.2, z: tp.z }, [0x6b5030, 0x4d3920], 3, { speed: 0.6 });
      if (i === 3) {
        // one leaf comes down
        fx.solid.emit({ pos: { x: tp.x + 0.2, y: 4.2, z: tp.z + 0.4 }, vel: { x: 0.2, y: -0.3, z: 0.1 }, color: 0x59ae30, size: 0.14, life: 2.2, grav: 0.6, bounce: 0 });
      }
    });
    yield 0.7;
    // shrug: nothing happened to the log
    setArm('r', 0.2, 0.9); setArm('l', 0.2, -0.9);
    snd('mob.villager.no', { volume: 0.6, pitch: 1.1 });
    for (let i = 0; i < 2; i++) { b.head.tyaw = 0.5; yield 0.25; b.head.tyaw = -0.5; yield 0.25; }
    b.head.tyaw = 0;
    yield 0.9;
    relax();
  }

  function* actChicken() {
    const sp = L.dance;
    yield* standAt(sp.x - 1.2, sp.z, yawFor(1, 0.3));
    const m = makeMob('Chicken', {});
    m.root.traverse((o) => { if (o.isMesh) { o.castShadow = true; } });
    let cx = -4.5, cz = sp.z + 1.4;
    m.root.position.set(cx, 0, cz);
    world.add(m.root);
    onCleanup(() => world.remove(m.root));
    let ct = 0;
    const chickenStep = (dt, spd) => {
      ct += dt; cx += spd * dt;
      m.root.position.set(cx, Math.abs(Math.sin(ct * 14)) * 0.03, cz);
      m.root.rotation.y = yawFor(1, 0);
      if (m.anim) m.anim(ct * 1.6, dt, { walk: 1.4 });
    };
    snd('mob.chicken.say', { pos: { x: cx, y: 0.4, z: cz }, volume: 0.8 });
    let t0 = 0;
    // the chicken wanders past; Steve watches it, then goes after it
    yield (dt) => { t0 += dt; chickenStep(dt, 1.3); b.head.target = new THREE.Vector3(cx, 0.4, cz); return cx > sp.x - 2.5; };
    b.state = 'run';
    let cd = 0;
    yield (dt) => {
      cd += dt; chickenStep(dt, 2.6);
      b.head.target = new THREE.Vector3(cx, 0.4, cz);
      const dx = cx - b.x, dz = cz - b.z, d = Math.hypot(dx, dz) || 1;
      const diff = wrapA(yawFor(dx, dz) - b.yaw);
      b.yaw += diff * Math.min(1, dt * 10);
      const sp2 = 4.6, step = sp2 * dt;
      b.x += (dx / d) * step; b.z += (dz / d) * step;
      b.ampT = 1.35; b.leanT = 0.14; b.phase += step * 2.2;
      if (cd > 0.55 && Math.floor(cd * 4) !== Math.floor((cd - dt) * 4)) snd('mob.chicken.say', { pos: { x: cx, y: 0.4, z: cz }, volume: 0.6, pitch: 1.3 });
      return cd > 1.3;
    };
    b.ampT = 0; b.leanT = 0; b.state = 'idle';
    // it gets away: Steve stops, arms out
    b.phase = Math.round(b.phase / Math.PI) * Math.PI;
    setArm('r', 0.4, 0.9); setArm('l', 0.4, -0.9);
    let ex = 0;
    yield (dt) => { ex += dt; chickenStep(dt, 3.4); b.head.target = new THREE.Vector3(cx, 0.4, cz); return ex > 1.8 || cx > 9; };
    b.head.target = null;
    snd('mob.villager.no', { volume: 0.6, pitch: 0.95 });
    b.head.tyaw = 0.5; yield 0.3; b.head.tyaw = -0.5; yield 0.3; b.head.tyaw = 0;
    yield 0.8;
    relax();
    world.remove(m.root);
  }

  function* actPillarFull() {
    const sp = L.pillar;
    yield* standAt(sp.x, sp.z, Math.PI);
    const blocks = [];
    onCleanup(() => { b.floor = 0; b.air = false; b.y = 0; for (const e of blocks) world.remove(e.m); b.extras = b.extras.filter((e) => !blocks.includes(e)); });
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
    hold({ tex: 'items/wood_pickaxe.png' });
    onCleanup(() => hold(null));
    b.head.tpitch = -0.8;
    for (let lvl = 1; lvl >= 0; lvl--) {
      const blk = blocks[lvl];
      yield* armSwing(3, 0.28, (i) => { snd('dig.gravel', { pos: { x: sp.x, y: lvl + 0.5, z: sp.z }, volume: 0.6, pitch: [0.9, 1.1] }); });
      breakBlock(blk, { x: sp.x, y: lvl + 0.5, z: sp.z }, 'dirt.png');
      spawnItem({ cube: 'blocks/dirt.png' }, { x: sp.x, y: lvl + 0.6, z: sp.z }, { x: R(-0.5, 0.5), y: 2.6, z: R(0.6, 1.2) }, { pickAt: 1.0 });
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
    let beat = 0, tt = 0;
    const base = b.yaw;
    yield (dt) => {
      const prev = tt; tt += dt;
      const bt = tt / 0.28;
      const i = Math.floor(bt);
      if (i !== Math.floor(prev / 0.28) && i < 12) {
        beat = i;
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
      b.ampT = 0.7; b.phase += dt * 9;
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

  // quick check that the chicken model loads; otherwise the beat is skipped
  const ACTS = [
    { id: 'mine', f: actMine }, { id: 'place', f: actPlace }, { id: 'craft', f: actCraft }, { id: 'fish', f: actFish },
    { id: 'sit', f: actSit }, { id: 'sunset', f: actSunset }, { id: 'tree', f: actTree }, { id: 'chicken', f: actChicken },
    { id: 'pillar', f: actPillarFull }, { id: 'dance', f: actDance }, { id: 'chest', f: actChest }, { id: 'sneak', f: actSneak },
  ];

  function* idleLoop() {
    for (;;) {
      if (!b.bag.length) {
        b.bag = ACTS.map((a, i) => i).sort(() => rng() - 0.5);
        if (b.bag[b.bag.length - 1] === b.lastAct) b.bag.reverse();
      }
      const i = b.bag.pop();
      b.lastAct = i;
      b.act = ACTS[i].id;
      try { yield* ACTS[i].f(); } finally { doCleanup(); relax(); }
      b.act = null;
      // a breath between things: a glance at the camera
      const glance = R() < 0.5;
      if (glance) b.head.target = b.camPos;
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
    const ax = Math.max(2.5, Math.min(3.2, b.x)) , az = 0.5;
    void ax; void az;
    yield* walkTo(2.7, 0.5, { sprint: true, speed: 6.2, turn: 12 });
    // hop up beside the block
    b.state = 'hop';
    b.ampT = 0; b.leanT = 0;
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
    hold({ tex: 'items/iron_pickaxe.png' });
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
    yield* walkTo(3.2, 0.5, { speed: 1.8 });
    yield* faceYaw(Math.PI / 2, 8);
    b.state = 'ready';
    yield () => false;
  }

  // ------------------------------------------------------------ the runner
  function startGen(g) { if (b.gen) { try { b.gen.return(); } catch (e) { /* ignore */ } } doCleanup(); b.gen = g; b.wait = 0; b.fn = null; }
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
  const api = {
    state: () => b.state,
    arrivedAt: () => b.arrivedAt,
    mineClock: () => (b.state === 'mine' ? b.swingClock : -1),
    activity: () => b.act || null,
    x: () => b.x, z: () => b.z,
    pos: () => ({ x: b.x, y: b.y, z: b.z }),
    reset(newSeed) {
      rng = mulberry(newSeed ?? seed);
      startGen(null);
      b.gen = null; b.fn = null; b.wait = 0; b.bag = []; b.lastAct = -1; b.act = null; b.frozen = false;
      for (const it of b.items) world.remove(it.g);
      b.items.length = 0;
      for (const e of b.extras) world.remove(e.m);
      b.extras.length = 0;
      if (b.bang) b.bang.visible = false;
      hold(null);
      for (const q of camp.quarry) { q.mesh.visible = true; q.removed = false; }
      camp.chest.setOpen(0);
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
        headTrack();
        applyPose(dt);
        stepBang();
        stepExtras(dt);
      }
      stepItems(dt);
      // ambience tied to the camp
      b.fireT -= dt;
      if (b.fireT <= 0) { b.fireT = R(2.6, 4.2); play('fire.fire', { pos: { x: L.fireCenter.x, y: 1, z: L.fireCenter.z }, volume: 0.5, ref: 5 }); }
    },
    // fast-forward the behaviour with no one watching (the ?idle= hook)
    fastForward(ms, camPos) { for (let t = 0; t < ms; t += 33) api.update(0.033, camPos); },
    setSkin(mat) { void mat; },
    startIdle() { b.gen = idleLoop(); },
    // debug hook (?act=): run one named activity first, then the normal loop
    start(id) {
      const a = ACTS.find((x) => x.id === id);
      if (!a) return false;
      b.act = id;
      startGen((function* () { try { yield* a.f(); } finally { doCleanup(); relax(); } b.act = null; yield* idleLoop(); })());
      return true;
    },
    acts: () => ACTS.map((a) => a.id),
  };
  b.gen = idleLoop();
  api.reset(seed);
  return api;
}
