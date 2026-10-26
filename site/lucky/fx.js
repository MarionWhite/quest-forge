// Shared pieces for the Lucky Block scenes: math, particles, mobs that appear with their own
// voice, lightning, fog, item sprites, the rolled-outcome helper and the scene report that
// tools/site/vet_lucky.py reads. Nothing here knows about a particular drop.
import * as THREE from 'three';
import { tex, glowTexture, iconTexture, BLOCK_TEX } from './stage.js';
import { makeMob, mobSounds } from '../lib/mc/mobs.js';
import { BLOCK_FILE } from './reel.js';
import { audio } from '../lib/qfaudio.js';

export const V = (x, y, z) => new THREE.Vector3(x, y, z);
export const clamp01 = (x) => Math.max(0, Math.min(1, x));
export const easeOut = (x) => 1 - Math.pow(1 - clamp01(x), 3);
export const easeIn = (x) => clamp01(x) * clamp01(x);
export const easeInOut = (x) => { x = clamp01(x); return x * x * (3 - 2 * x); };
export const lerp = (a, b, k) => a + (b - a) * k;
export const rnd = (a = 0, b = 1) => a + Math.random() * (b - a);
export const pick = (arr) => arr[Math.floor(Math.random() * arr.length)];

const PARAMS = new URLSearchParams(location.search);
export const SFXLOG = PARAMS.has('sfxlog');
export const DUMP = PARAMS.has('dump');

// ------------------------------------------------------------------ the scene report
// One per scene. Helpers below count what the scene makes; the scene registers its subjects
// (what the shot is about) so the vet can ask whether they are in the frame.
let REP = null;
export function newReport(key, drop) {
  REP = { key, index: drop && drop.index, mobs: 0, items: 0, blocks: 0, particles: 0, sfx: {}, subjects: [], errors: [], notes: [], t: 0, dur: 0 };
  return REP;
}
export function report() { return REP; }
export function note(s) { if (REP) REP.notes.push(s); }
export function fail(s) { if (REP) REP.errors.push(String(s)); }
// A subject: a Object3D or a function returning a Vector3; `size` is its world height.
export function watch(name, what, size = 1, main = true) {
  if (REP) REP.subjects.push({ name, what, size, main });
}
const _cam = new THREE.PerspectiveCamera();
const _fr = new THREE.Frustum();
const _m = new THREE.Matrix4();
const _p = new THREE.Vector3();
export function finishReport(rep, cam, aspect, t, dur) {
  const o = { key: rep.key, index: rep.index, t, dur, mobs: rep.mobs, items: rep.items, blocks: rep.blocks, particles: rep.particles, sfx: { ...rep.sfx }, errors: rep.errors.slice(), notes: rep.notes.slice(), subjects: [] };
  _cam.fov = cam.fov || 40; _cam.aspect = aspect || 1.5; _cam.near = 0.1; _cam.far = 200;
  _cam.position.copy(cam.pos); _cam.up.set(0, 1, 0); _cam.lookAt(cam.look); _cam.updateMatrixWorld(true); _cam.updateProjectionMatrix();
  _m.multiplyMatrices(_cam.projectionMatrix, _cam.matrixWorldInverse); _fr.setFromProjectionMatrix(_m);
  for (const s of rep.subjects) {
    let vis = true;
    if (typeof s.what === 'function') _p.copy(s.what());
    else { s.what.getWorldPosition(_p); vis = s.what.visible !== false && s.what.scale.x > 0.02; _p.y += s.size * 0.5; }
    const dist = _p.distanceTo(_cam.position);
    const view = 2 * dist * Math.tan(THREE.MathUtils.degToRad(_cam.fov) / 2);
    o.subjects.push({ name: s.name, main: s.main, visible: vis, inFrustum: vis && _fr.containsPoint(_p), screenH: +(s.size / view).toFixed(3), pos: [+_p.x.toFixed(1), +_p.y.toFixed(1), +_p.z.toFixed(1)] });
  }
  return o;
}

// ------------------------------------------------------------------ sound
// Every call is logged for the vet (and to the console under ?sfxlog), then handed to the engine.
let lastSay = -9;
export function sfx(name, o = {}) {
  if (!name) return;
  if (REP) REP.sfx[name] = (REP.sfx[name] || 0) + 1;
  if (SFXLOG) console.info('sfx', name);
  try { audio.play(name, o); } catch (e) { /* the engine is optional */ }
}
// A mob's own voice, throttled so a horde of a hundred does not become a wall of noise.
export function mobSay(id, pos, kind = 'say', o = {}) {
  const now = performance.now();
  if (!o.force && now - lastSay < 90 && !DUMP) return;
  lastSay = now;
  let s = null;
  try { s = mobSounds(id); } catch (e) { s = null; }
  const name = s && s[kind];
  if (name) sfx(name, { pos: pos && { x: pos.x, y: pos.y, z: pos.z }, volume: o.volume ?? 0.9, pitch: o.pitch });
}

// ------------------------------------------------------------------ particles
export function burst(ctx, pos, o = {}) {
  const n = o.n ?? 30, life = o.life ?? 0.9, gravity = o.gravity ?? 7;
  const speed = o.speed ?? 2.4, up = o.up ?? 1.6;
  if (REP) REP.particles += n;
  const pts = new Float32Array(n * 3), vel = new Float32Array(n * 3), cols = new Float32Array(n * 3);
  const palette = (o.colors || [0xffffff]).map((c) => new THREE.Color(c));
  for (let i = 0; i < n; i++) {
    pts.set([pos.x + rnd(-0.1, 0.1), pos.y + rnd(0, 0.3), pos.z + rnd(-0.1, 0.1)], i * 3);
    const a = rnd(0, Math.PI * 2), s = speed * rnd(0.35, 1);
    vel.set([Math.cos(a) * s * (o.spread ?? 1), up * rnd(0.4, 1.2) * (o.lift ?? 1), Math.sin(a) * s * (o.spread ?? 1)], i * 3);
    const c = palette[i % palette.length];
    cols.set([c.r, c.g, c.b], i * 3);
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(pts, 3));
  geo.setAttribute('color', new THREE.BufferAttribute(cols, 3));
  const mat = new THREE.PointsMaterial({ size: o.size ?? 0.12, vertexColors: true, map: glowTexture(), transparent: true, depthWrite: false, blending: o.additive ? THREE.AdditiveBlending : THREE.NormalBlending, sizeAttenuation: true });
  const obj = new THREE.Points(geo, mat);
  obj.frustumCulled = false;
  ctx.S.temp.add(obj);
  let t = 0;
  ctx.fx.push({
    update(dt) {
      t += dt;
      for (let i = 0; i < n; i++) {
        vel[i * 3 + 1] -= gravity * dt;
        pts[i * 3] += vel[i * 3] * dt; pts[i * 3 + 1] += vel[i * 3 + 1] * dt; pts[i * 3 + 2] += vel[i * 3 + 2] * dt;
        if (!o.noFloor && pts[i * 3 + 1] < 0.02) { pts[i * 3 + 1] = 0.02; vel[i * 3 + 1] *= -0.3; vel[i * 3] *= 0.6; vel[i * 3 + 2] *= 0.6; }
      }
      geo.attributes.position.needsUpdate = true;
      mat.opacity = clamp01(1 - t / life);
      if (t >= life) { ctx.S.temp.remove(obj); geo.dispose(); mat.dispose(); return true; }
      return false;
    },
  });
}
export function puff(ctx, pos, o = {}) {
  burst(ctx, pos, { n: o.n ?? 18, colors: o.colors ?? [0xd9d6df, 0x9d98a8, 0xbfbac8], size: o.size ?? 0.45, speed: o.speed ?? 1.2, up: o.up ?? 0.8, gravity: o.gravity ?? 0.5, life: o.life ?? 1.1, spread: 1.4, noFloor: o.noFloor });
}
export function pointLight(ctx, color, intensity, dist, pos) {
  const l = new THREE.PointLight(color, intensity, dist, 1.6);
  l.position.copy(pos);
  ctx.S.temp.add(l);
  return l;
}

// ------------------------------------------------------------------ lightning and weather
// A forked bolt from the sky to (x, z): flash, thunder, shake, sparks on the ground.
export function strikeBolt(ctx, x, z, o = {}) {
  const top = o.top ?? 38, gy = o.ground ?? 0.1;
  const g = new THREE.Group();
  const mat = new THREE.MeshBasicMaterial({ color: 0xeaf2ff, transparent: true, opacity: 1, blending: THREE.AdditiveBlending, depthWrite: false, fog: false });
  const seg = (a, b, w) => {
    const len = a.distanceTo(b);
    const m = new THREE.Mesh(new THREE.CylinderGeometry(w, w, len, 5), mat);
    m.position.copy(a).add(b).multiplyScalar(0.5);
    m.lookAt(b); m.rotateX(Math.PI / 2);
    g.add(m);
  };
  const path = (from, to, n, jit, w) => {
    let prev = from.clone();
    for (let i = 1; i <= n; i++) {
      const k = i / n;
      const p = from.clone().lerp(to, k);
      if (i < n) { p.x += rnd(-jit, jit) * (1 - k * 0.4); p.z += rnd(-jit, jit) * (1 - k * 0.4); }
      seg(prev, p, w);
      if (i > 2 && i < n - 1 && Math.random() < 0.3) path(p, V(p.x + rnd(-6, 6), p.y - rnd(6, 12), p.z + rnd(-6, 6)), 4, 1.0, w * 0.5);
      prev = p;
    }
  };
  path(V(x + rnd(-3, 3), top, z + rnd(-3, 3)), V(x, gy, z), 11, 1.6, o.width ?? 0.16);
  ctx.S.temp.add(g);
  if (REP) REP.blocks += 0;
  const light = pointLight(ctx, 0xcfe0ff, 90, 40, V(x, 7, z));
  burst(ctx, V(x, 0.2, z), { n: 26, colors: [0xffffff, 0xcfe0ff, 0xffe08a], size: 0.22, speed: 3.2, up: 3, life: 0.7, additive: true, gravity: 8 });
  ctx.flashScreen('#eaf2ff', o.flash ?? 0.7, 0.4);
  ctx.shake(o.shake ?? 0.35);
  sfx('ambient.weather.thunder', { pos: { x, y: 4, z }, volume: o.volume ?? 1 });
  let t = 0;
  ctx.fx.push({
    update(dt) {
      t += dt;
      mat.opacity = t < 0.1 ? 1 : (Math.floor(t * 38) % 2 ? 0.9 : 0.35) * clamp01(1 - (t - 0.1) / 0.28);
      light.intensity = 90 * clamp01(1 - t / 0.35);
      if (t >= 0.4) { ctx.S.temp.remove(g); ctx.S.temp.remove(light); g.traverse((m) => m.geometry && m.geometry.dispose()); mat.dispose(); return true; }
      return false;
    },
  });
}
// The sky darkens (0 dusk, 1 night) and the fog closes in; call each frame with k in 0..1.
export function sky(ctx, k, o = {}) {
  const S = ctx.S;
  S.setNight(clamp01(k) * (o.night ?? 1));
  const F = S.scene.fog;
  if (!F._qf0) F._qf0 = { near: F.near, far: F.far };
  const f = clamp01(o.fog ?? k);
  F.near = lerp(F._qf0.near, o.near ?? 8, f);
  F.far = lerp(F._qf0.far, o.far ?? 36, f);
}
export function resetFog(ctx) {
  const F = ctx.S.scene.fog;
  if (F._qf0) { F.near = F._qf0.near; F.far = F._qf0.far; }
}

// ------------------------------------------------------------------ mobs
// Mobs that fly hover at a height; the rest stand on the ground (y = 0).
export const FLY = { Ghast: 4.2, Bat: 2.6, Bee: 2.0, Blaze: 2.2, Dragon: 3.4, Mothra: 4.0, Brutalfly: 3.6, WitherBoss: 4.0, Cephadrome: 9.0, Hoverboard: 0.5 };
const SMALL_STEP = { Silverfish: 0.12, CaveSpider: 0.2 };
export function isFlyer(id) { return FLY[id] != null; }

// A mob that grows in with a poof. Returns the library's mob plus the scene bookkeeping.
export function spawnMob(ctx, id, pos, o = {}) {
  const m = makeMob(id, o);
  m.root.position.copy(pos);
  if (o.rotY != null) m.root.rotation.y = o.rotY;
  m.root.traverse((x) => { if (x.isMesh) x.castShadow = true; });
  if (o.height) {
    // fit the model to a target world height (the big mobs)
    const cur = (m.height || 1.8) * m.root.scale.x;
    m.root.scale.multiplyScalar(o.height / cur);
  }
  const base = m.root.scale.clone();
  m.root.scale.setScalar(0.001);
  ctx.S.temp.add(m.root);
  if (!o.quiet) puff(ctx, pos.clone().setY(pos.y + 0.6), { n: 14, size: 0.5 });
  if (REP) REP.mobs++;
  const mob = { ...m, id, base, born: null, spoke: false, nextSay: 0, fly: o.fly ?? FLY[id] ?? 0, bob: rnd(0, 6), wh: (m.height || 1.8) * base.x, baseY: pos.y, flipY: 0 };
  if (o.watch !== false) watch(id, m.root, mob.wh, o.main !== false);
  return mob;
}
// Every frame: grow in once born, keep the animation going, speak on arrival and now and then.
export function mobTick(m, t, dt, o = {}) {
  if (m.born === null || t < m.born) return false;
  const k = clamp01((t - m.born) / (o.grow ?? 0.4));
  m.root.scale.copy(m.base).multiplyScalar(Math.max(0.001, easeOut(k)));
  if (m.fly && o.hover !== false) m.root.position.y = (m.baseY ?? 0) + m.fly + Math.sin(t * 1.6 + m.bob) * 0.18 + m.flipY;
  m.anim(t, dt, o);
  if (!m.spoke) { m.spoke = true; m.nextSay = t + rnd(1.6, 3.2); if (!o.mute) mobSay(m.id, m.root.position, o.sayKind || 'say'); }
  else if (!o.mute && t > m.nextSay) { m.nextSay = t + rnd(1.8, 3.6); mobSay(m.id, m.root.position, 'say', { volume: 0.7 }); }
  return true;
}

// ------------------------------------------------------------------ small meshes
export function plane(w, h, color, opacity, additive = false) {
  return new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ color, transparent: true, opacity, depthWrite: false, blending: additive ? THREE.AdditiveBlending : THREE.NormalBlending, side: THREE.DoubleSide }));
}
const matCache = new Map();
export function blockCube(id, size = 1, extra = {}) {
  const key = BLOCK_TEX[id];
  const file = (key && BLOCK_FILE[key]) || 'stone.png';
  const ck = file + JSON.stringify(extra);
  if (!matCache.has(ck)) { const mm = new THREE.MeshLambertMaterial({ map: tex('blocks/' + file), ...extra }); mm.userData.keep = true; matCache.set(ck, mm); }
  const m = new THREE.Mesh(new THREE.BoxGeometry(size, size, size), matCache.get(ck));
  m.castShadow = true;
  if (REP) REP.blocks++;
  return m;
}
// A name floating above something, as 1.7.10 draws a nametag.
export function nameTag(text, color = '#ffffff') {
  const c = document.createElement('canvas'); c.width = 384; c.height = 64;
  const g = c.getContext('2d'); g.font = '700 34px Archivo, sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle';
  let s = 34; while (g.measureText(text).width > 360 && s > 16) { s -= 2; g.font = `700 ${s}px Archivo, sans-serif`; }
  g.fillStyle = 'rgba(14,11,18,0.6)'; g.fillRect(0, 0, 384, 64);
  g.fillStyle = color; g.fillText(text, 192, 34);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace;
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: t, transparent: true, depthWrite: false, depthTest: false }));
  sp.scale.set(2.0, 0.34, 1);
  sp.renderOrder = 30;
  return sp;
}
export function heartSprite() {
  const c = document.createElement('canvas'); c.width = c.height = 32;
  const g = c.getContext('2d'); g.fillStyle = '#e8485a';
  g.beginPath(); g.moveTo(16, 28); g.bezierCurveTo(-4, 16, 2, -2, 16, 8); g.bezierCurveTo(30, -2, 36, 16, 16, 28); g.fill();
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace;
  return new THREE.Sprite(new THREE.SpriteMaterial({ map: t, transparent: true, depthWrite: false }));
}
export function labelSprite(text, o = {}) {
  const c = document.createElement('canvas'); c.width = 256; c.height = 64;
  const g = c.getContext('2d'); g.font = '800 40px Archivo, sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle';
  g.lineWidth = 7; g.strokeStyle = 'rgba(8,6,12,0.85)'; g.strokeText(text, 128, 34);
  g.fillStyle = o.color || '#ffffff'; g.fillText(text, 128, 34);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace;
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: t, transparent: true, depthWrite: false, depthTest: false }));
  const w = o.w ?? 0.62; sp.scale.set(w, w / 4, 1); sp.renderOrder = 31;
  return sp;
}

// ------------------------------------------------------------------ dropped items
// One world size for every item (a 1.7.10 dropped sprite is 0.5 of a block), a little thickness
// so it holds its shape edge-on, the glint on enchanted gear, a count label under it.
export const ITEM_SIZE = 0.5;
let POOL = [];
fetch(new URL('./data/lucky.json', import.meta.url)).then((r) => r.json()).then((d) => {
  const seen = new Set();
  for (const x of d.drops || []) if (x.icon && !seen.has(x.icon.s + ',' + x.icon.c + ',' + x.icon.r)) { seen.add(x.icon.s + ',' + x.icon.c + ',' + x.icon.r); POOL.push(x.icon); }
}).catch(() => {});
export function randomIcon() { return POOL.length ? pick(POOL) : null; }

const mysteryTex = (() => { let t = null; return () => { if (t) return t; const c = document.createElement('canvas'); c.width = c.height = 32; const g = c.getContext('2d'); g.fillStyle = '#2a2236'; g.fillRect(2, 2, 28, 28); g.strokeStyle = '#f2c14e'; g.lineWidth = 2; g.strokeRect(2, 2, 28, 28); g.fillStyle = '#f2c14e'; g.font = '800 22px sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText('?', 16, 17); t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.magFilter = THREE.NearestFilter; return t; }; })();
export function itemSprite(it, size = ITEM_SIZE) {
  const g = new THREE.Group();
  const icon = it.icon || (it.id === 'random' ? randomIcon() : null);
  const map = icon ? iconTexture(icon) : mysteryTex();
  const spin = new THREE.Group();
  for (const z of [-0.02, 0, 0.02]) {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(size, size), new THREE.MeshBasicMaterial({ map, transparent: true, alphaTest: 0.5, side: THREE.DoubleSide }));
    m.position.z = z; spin.add(m);
  }
  g.add(spin);
  g.userData.spin = spin;
  if (it.ench) {
    const gl = new THREE.Mesh(new THREE.PlaneGeometry(size * 1.5, size * 1.5), new THREE.MeshBasicMaterial({ map: glowTexture('rgba(190,120,255,0.9)'), transparent: true, opacity: 0.5, blending: THREE.AdditiveBlending, depthWrite: false }));
    g.add(gl); g.userData.glint = gl;
  }
  const hi = it.n && it.n > 1 ? it.n : 0;
  if (hi) { const lb = labelSprite('x' + hi, { w: 0.5 }); lb.position.set(0, -size * 0.78, 0); g.add(lb); }
  if (REP) REP.items++;
  return g;
}

// ------------------------------------------------------------------ rolling a drop's actions
const count = (a) => { const [lo, hi] = a || [1, 1]; return Math.round(lo + Math.random() * Math.max(0, hi - lo)); };
export { count as rollAmount };
// Resolve choices the way the mod does (pick N options at random) and turn each amount into a
// concrete n. `then` actions stay as they are, for the well and temple scenes to play.
export function roll(acts, out = []) {
  for (const a of acts || []) {
    if (a.t === 'choice') {
      const [lo, hi] = a.pick || [1, 1];
      const k = lo + Math.floor(Math.random() * (hi - lo + 1));
      const opts = (a.options || []).slice();
      for (let i = 0; i < k && opts.length; i++) roll(opts.splice(Math.floor(Math.random() * opts.length), 1)[0], out);
    } else if (a.t === 'then') out.push(a);
    else out.push({ ...a, n: a.amount ? count(a.amount) : 1, nmax: a.amount ? a.amount[1] : 1 });
  }
  return out;
}
export function itemsOf(rolled) {
  const out = [];
  for (const a of rolled) {
    if (a.t === 'item') out.push({ icon: a.icon, id: a.id, name: a.display || a.name || a.id, n: a.n, ench: a.ench && a.ench.length ? a.ench : null, where: a.where });
    else if (a.t === 'entity' && a.id === 'Item') out.push({ icon: a.icon || null, id: 'random', name: a.display || a.name || 'Item', n: a.n });
    else if (a.t === 'command' && a.gives) out.push({ icon: a.gives.icon, id: a.gives.id, name: a.gives.name, n: 1 });
  }
  return out;
}
export function mobsOf(rolled, cap = 40) {
  const acts = rolled.filter((a) => a.t === 'entity' && a.id !== 'Item');
  const share = Math.max(2, Math.ceil(cap / Math.max(1, acts.length)));
  const out = [];
  for (const a of acts) {
    for (let i = 0; i < Math.min(a.n, share) && out.length < cap; i++) out.push({ id: a.id, display: a.display, name: a.name, riding: a.riding || [], upsideDown: a.upsideDown, size: a.size, equipment: a.equipment || [], total: a.n });
  }
  return out;
}

export function cleanName(s) { return String(s || '').replace(/§./g, ''); }

// Models in this library face -z: the yaw that makes a mob face the direction (dx, dz).
export const facing = (dx, dz) => Math.atan2(-dx, -dz);
