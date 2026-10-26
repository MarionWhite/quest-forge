// Scenes that play a structure from structures.json. Each returns a scene object
// like scenes.js, or null when the structure is missing (the caller falls back).
import * as THREE from 'three';
import { structureScene, plan } from './structures.js';
import { anvilModel } from './blocks.js';
import { makeMob } from './mobs.js';
import { glowTexture } from './stage.js';
import { sfx, watch } from './fx.js';

const V = (x, y, z) => new THREE.Vector3(x, y, z);
const clamp01 = (x) => Math.max(0, Math.min(1, x));
const easeIn = (x) => clamp01(x) * clamp01(x);
const easeOut = (x) => 1 - Math.pow(1 - clamp01(x), 3);
const easeInOut = (x) => { x = clamp01(x); return x * x * (3 - 2 * x); };
const rnd = (a = 0, b = 1) => a + Math.random() * (b - a);
const FEET = { x: 3, y: 0, z: 0 }; // the player's cell: structures are player-relative

function fireTexture() {
  const c = document.createElement('canvas'); c.width = 32; c.height = 64;
  const g = c.getContext('2d');
  const grd = g.createLinearGradient(0, 64, 0, 0);
  grd.addColorStop(0, 'rgba(255,200,60,1)'); grd.addColorStop(0.5, 'rgba(255,110,20,0.95)'); grd.addColorStop(1, 'rgba(255,60,20,0)');
  g.fillStyle = grd; g.beginPath(); g.ellipse(16, 40, 14, 26, 0, 0, Math.PI * 2); g.fill();
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}
function heartTexture() {
  const c = document.createElement('canvas'); c.width = c.height = 32;
  const g = c.getContext('2d'); g.fillStyle = '#e8485a';
  g.beginPath(); g.moveTo(16, 28); g.bezierCurveTo(-4, 16, 2, -2, 16, 8); g.bezierCurveTo(30, -2, 36, 16, 16, 28); g.fill();
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}
// Particle emitter that lives in the scene's fx list.
function emit(ctx, pos, { n = 4, colors = [0xffffff], size = 0.2, up = 1.6, gravity = 2, life = 0.7, additive = true, spread = 0.3 }) {
  const pts = new Float32Array(n * 3), vel = new Float32Array(n * 3), col = new Float32Array(n * 3);
  const pal = colors.map((c) => new THREE.Color(c));
  for (let i = 0; i < n; i++) {
    pts.set([pos.x + rnd(-spread, spread), pos.y + rnd(-0.1, 0.1), pos.z + rnd(-spread, spread)], i * 3);
    vel.set([rnd(-0.3, 0.3), up * rnd(0.6, 1.2), rnd(-0.3, 0.3)], i * 3);
    const c = pal[i % pal.length]; col.set([c.r, c.g, c.b], i * 3);
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(pts, 3));
  geo.setAttribute('color', new THREE.BufferAttribute(col, 3));
  const mat = new THREE.PointsMaterial({ size, vertexColors: true, map: glowTexture(), transparent: true, depthWrite: false, blending: additive ? THREE.AdditiveBlending : THREE.NormalBlending });
  const obj = new THREE.Points(geo, mat);
  ctx.S.temp.add(obj);
  let t = 0;
  ctx.fx.push({ update(dt) { t += dt; for (let i = 0; i < n; i++) { vel[i * 3 + 1] -= gravity * dt; for (let k = 0; k < 3; k++) pts[i * 3 + k] += vel[i * 3 + k] * dt; } geo.attributes.position.needsUpdate = true; mat.opacity = clamp01(1 - t / life); if (t >= life) { ctx.S.temp.remove(obj); geo.dispose(); mat.dispose(); return true; } return false; } });
}
function light(ctx, color, intensity, dist, pos) {
  const l = new THREE.PointLight(color, intensity, dist, 1.6);
  l.position.copy(pos); ctx.S.temp.add(l); return l;
}
function landingBurst(ctx, pos, colors = [0xb8b0c4, 0x8c8698], n = 14, size = 0.4) {
  emit(ctx, pos, { n, colors, size, up: 1.1, gravity: 1.2, life: 1.1, additive: false, spread: 0.6 });
}

const STRUCT = {};
let _steve = null; const steve0 = () => _steve;
let luckyMat = null;
const LUCKY_MAT = () => { if (!luckyMat) luckyMat = makeBlock('lucky:lucky_block', 0, {}).obj.children[0].material; return luckyMat; };

// Anvil trap: the cage and sign placed, the eye cam looks up the shaft, two anvils from 64 blocks
// up fall with gravity. The camera cuts to a side shot on the first landing.
STRUCT.anvil_trap = (ctx) => {
  const sp = structureScene(ctx, 'anvil_trap', FEET, { start: 0.25, span: 2.2 });
  if (!sp) return null;
  const P = ctx.pos;
  const steve = ctx.steve;
  const anvils = [0, 1].map((i) => {
    const g = anvilModel();
    g.position.set(P.x + 0.3, 64 - i, P.z + 0.5);
    g.traverse((o) => { if (o.isMesh) o.castShadow = true; });
    ctx.S.temp.add(g);
    return { g, t0: 3.1 + i * 0.35, landed: false, landT: null, i };
  });
  watch('anvil', () => anvils[0].g.position.clone().setY(Math.min(anvils[0].g.position.y, 60)), 1);
  watch('steve', () => new THREE.Vector3(P.x, 1.0, P.z), 1.8, false);
  light(ctx, 0xffb070, 140, 60, V(P.x + 0.4, 10, P.z + 0.5));
  light(ctx, 0xffe0b0, 40, 30, V(P.x + 0.4, 3.5, P.z + 0.5));
  light(ctx, 0xffd9a0, 2.4, 9, V(P.x + 1.5, 1.6, P.z + 3.4));
  const G = 30;
  let tilt = null;
  let fellT = null;
  return {
    dur: 7.8,
    cam: (t) => {
      // the eye shot: from inside the head, looking up the shaft. The look point is tilted one
      // block forward so the camera's roll is defined (a target straight above the lens is not).
      if (t < 5.0) return { pos: V(P.x + 0.12, 1.62, P.z + 0.1), look: V(P.x + 0.12, 60, P.z + 1.2), fov: 64 };
      return { pos: V(P.x + 0.6, 2.2, P.z + 4.4), look: V(P.x, 1.2 + (fellT ? -0.2 : 0), P.z), fov: 42 };
    },
    update(t, dt) {
      sp.update(t);
      // while the camera sits in Steve's eyes his head would fill the lens: hide it for the shot
      if (steve.parts && steve.parts.head) steve.parts.head.visible = t >= 5.0;
      for (const a of anvils) {
        if (a.landed) continue;
        if (t < a.t0) continue;
        const s = t - a.t0;
        const y = 64 - 0.5 * G * s * s;
        const floor = 2.0 + a.i * 1.0;
        if (y <= floor) {
          a.landed = true; a.landT = t; a.g.position.y = floor;
          ctx.shake(0.5 + 0.1 * a.i);
          sfx('random.anvil_land', { pos: { x: P.x, y: 1, z: P.z }, volume: 1, pitch: 0.9 + 0.1 * a.i }); sfx('game.player.hurt', { volume: 0.8 });
          ctx.hurt(0.55);
          ctx.flashScreen('#ff2a2a', 0.45, 0.4);
          landingBurst(ctx, V(P.x + 0.5, floor, P.z + 0.5), [0xb8b0c4, 0x8f8a9c, 0xf08a3c], 26, 0.4);
          if (a.i === 1) tilt = t;
        } else a.g.position.y = y;
      }
      if (tilt !== null) {
        const k = easeInOut((t - tilt - 0.25) / 1.1);
        steve.root.rotation.z = -k * Math.PI / 2;
        steve.mat.emissive.setRGB(0.55 * clamp01((t - tilt) / 0.6), 0.02, 0.02);
        ctx.hurt(0.35 + 0.35 * k);
        if (k > 0.9 && fellT === null) fellT = t;
      } else {
        steve.anim(t, dt, { walk: 0 });
        steve.mat.emissive.setRGB(0, 0, 0);
      }
      if (t > 0.3 && !ctx._bars) { ctx._bars = true; sfx('dig.stone', { pos: { x: P.x, y: 1, z: P.z }, volume: 0.8 }); sfx('random.click', { volume: 0.6 }); }
      if (t > 3.0 && !ctx._whistle) { ctx._whistle = true; sfx('random.bow', { pos: { x: P.x, y: 20, z: P.z }, volume: 0.4, pitch: 0.5 }); }
      if (fellT && t > fellT + 0.6 && !ctx._say) { ctx._say = true; ctx.say('Steve was squashed by a falling anvil', { at: 'bottom' }); }
    },
  };
};

// Lava and water cages: the four-high cage fills, the player burns or drowns.
function cageScene(ctx, key, fluid) {
  const sp = structureScene(ctx, key, FEET, { start: 0.2, span: 2.4 });
  if (!sp) return null;
  const P = ctx.pos;
  watch('steve', () => new THREE.Vector3(P.x, 1.0, P.z), 1.8);
  const steve = ctx.steve;
  const fire = new THREE.Group();
  const fireMat = new THREE.MeshBasicMaterial({ map: fireTexture(), transparent: true, depthWrite: false, depthTest: false, opacity: 0, side: THREE.DoubleSide, blending: THREE.NormalBlending });
  for (let i = 0; i < 4; i++) {
    const p = new THREE.Mesh(new THREE.PlaneGeometry(1.1, 1.9), fireMat);
    p.position.set(0, 1.0, 0); p.rotation.y = i * Math.PI / 4; p.renderOrder = 20;
    fire.add(p);
  }
  steve.root.add(fire);
  const hearts = [];
  const heartMat = new THREE.SpriteMaterial({ map: heartTexture(), transparent: true, depthWrite: false, opacity: 0 });
  if (fluid === 'water') for (let i = 0; i < 3; i++) { const s = new THREE.Sprite(heartMat.clone()); s.scale.setScalar(0.32); ctx.S.temp.add(s); hearts.push(s); }
  let lt = null;
  if (fluid === 'lava') lt = light(ctx, 0xff7a2a, 3.5, 6, V(P.x, 1.1, P.z));
  const burnAt = fluid === 'lava' ? 2.6 : 3.0;
  return {
    dur: 6.4,
    cam: (t) => ({ pos: V(P.x + 4.3, 2.3, P.z + 4.8 + clamp01(t / 6) * 0.6), look: V(P.x - 0.1, 1.25, P.z), fov: 40 }),
    update(t, dt) {
      sp.update(t);
      if (t > 0.3 && !ctx._bars) { ctx._bars = true; sfx('dig.stone', { pos: { x: P.x, y: 1, z: P.z }, volume: 0.8 }); }
      if (t > 2.2 && !ctx._liq) { ctx._liq = true; sfx(fluid === 'lava' ? 'liquid.lava' : 'liquid.water', { pos: { x: P.x, y: 3, z: P.z }, volume: 1 }); sfx(fluid === 'lava' ? 'liquid.lavapop' : 'liquid.splash', { volume: 0.8 }); }
      if (t > burnAt && !ctx._hurt) { ctx._hurt = true; sfx('game.player.hurt', { volume: 0.9 }); sfx(fluid === 'lava' ? 'fire.fire' : 'liquid.splash', { pos: { x: P.x, y: 1, z: P.z }, volume: 0.8 }); }
      if (t > burnAt + 1.4 && !ctx._hurt2) { ctx._hurt2 = true; sfx('game.player.hurt', { volume: 0.9 }); if (fluid === 'lava') sfx('random.fizz', { volume: 0.5 }); }
      const burning = clamp01((t - burnAt) / 0.8);
      fireMat.opacity = fluid === 'lava' ? 0.7 * burning * (0.85 + 0.15 * Math.sin(t * 25)) : 0;
      fire.children.forEach((f, i) => { f.scale.y = 1 + 0.15 * Math.sin(t * 18 + i); });
      if (lt) lt.intensity = 3.5 + 1.5 * Math.sin(t * 8) * burning;
      if (fluid === 'lava') {
        steve.mat.emissive.setRGB(0.55 * burning, 0.18 * burning, 0);
        steve.anim(t, dt, { walk: 0, armRaise: 0.4 * burning });
        if (t > burnAt && Math.random() < dt * 40) emit(ctx, V(P.x + rnd(-0.2, 0.2), 0.8 + rnd(0, 1.2), P.z + rnd(-0.2, 0.2)), { n: 3, colors: [0xffd27a, 0xff7a2a, 0xff3a10], size: 0.22, up: 1.6, gravity: -0.8, life: 0.7 });
        ctx.hurt(0.25 * burning);
        ctx.tint(0x3a0f00, 0.1 * burning);
      } else {
        steve.anim(t, dt, { walk: 0 });
        steve.root.rotation.z = -easeInOut((t - 3.6) / 1.6) * 0.25;
        if (t > 2.4 && Math.random() < dt * 14) emit(ctx, V(P.x + rnd(-0.3, 0.3), 0.3, P.z + rnd(-0.3, 0.3)), { n: 2, colors: [0xbfe6ff, 0xffffff], size: 0.12, up: 1.6, gravity: -0.5, life: 1.0, additive: false });
        hearts.forEach((h, i) => {
          const k = clamp01((t - 3.6 - i * 0.3) / 1.2);
          h.position.set(P.x + 0.3, 2.0 + k * 0.6, P.z);
          h.material.opacity = k < 1 ? 0.9 * (1 - k * 0.5) : 0;
          h.scale.setScalar(0.32 * (1 - k * 0.4));
        });
        ctx.tint(0x0a3a7a, 0.18 * clamp01((t - 2.6) / 1.5));
      }
      if (t > (fluid === 'lava' ? 4.2 : 4.6) && !ctx._say) { ctx._say = true; ctx.say(fluid === 'lava' ? 'Steve tried to swim in lava' : 'Steve drowned', { at: 'bottom' }); }
    },
  };
}
STRUCT.lava_trap = (ctx) => cageScene(ctx, 'lava_trap', 'lava');
STRUCT.water_trap = (ctx) => cageScene(ctx, 'water_trap', 'water');

// Pit: the 3x3 floor drops away; Steve falls 60 blocks with the camera following; web and lava below.
STRUCT.pit_trap = (ctx) => {
  const sp = structureScene(ctx, 'pit_trap', FEET, { start: 0.1, span: 1.2 });
  if (!sp) return null;
  const P = ctx.pos;
  watch('shaft', () => new THREE.Vector3(P.x + 0.1, steve0().root.position.y - 1.2, P.z + 0.1), 2);
  const steve = ctx.steve; _steve = steve;
  const fallT0 = 2.0, fallT = 3.8, D = 60;
  let y = 0;
  // walls for the shaft below the plateau's bedrock, so the fall has something to frame
  for (let wy = -9; wy >= -60; wy--) for (let x = 1; x <= 5; x++) for (let z = -2; z <= 2; z++) {
    if (x > 1 && x < 5 && z > -2 && z < 2) continue;
    ctx.setVoxel(x, wy, z, 'stone');
  }
  light(ctx, 0xff7a2a, 70, 26, V(P.x + 0.5, -57, P.z + 0.5));
  light(ctx, 0xffb070, 10, 10, V(P.x + 0.5, -20, P.z + 0.5));
  return {
    dur: 6.8,
    cam: (t) => {
      const sy = steve.root.position.y;
      return { pos: V(P.x + 0.9, sy + 2.0, P.z + 1.3), look: V(P.x + 0.1, sy - 1.2, P.z + 0.1), fov: 52 };
    },
    update(t, dt) {
      sp.update(t);
      if (t > 0.2 && !ctx._o) { ctx._o = true; sfx('dig.stone', { pos: { x: P.x, y: 0, z: P.z }, volume: 0.9 }); }
      if (t > fallT0 + 0.2 && !ctx._yell) { ctx._yell = true; sfx('game.player.hurt', { volume: 0.7, pitch: 0.7 }); }
      if (t > fallT0 + fallT && !ctx._web) { ctx._web = true; sfx('dig.cloth', { volume: 0.9 }); sfx('liquid.lava', { volume: 0.7 }); }
      const s = clamp01((t - fallT0) / fallT);
      y = -D * s * s;
      steve.anim(t, dt, { walk: 0, armRaise: 0.9 * (s > 0 ? 1 : 0) });
      steve.root.position.y = y;
      steve.root.rotation.z = Math.sin(t * 6) * 0.05 * (s > 0 ? 1 : 0);
      if (s > 0 && Math.random() < dt * 20) emit(ctx, V(P.x, y + 1.0, P.z), { n: 2, colors: [0x9d98a8, 0x6c6878], size: 0.22, up: 0.4, gravity: -0.3, life: 1.0, additive: false });
      if (t > 4.6 && !ctx._say) { ctx._say = true; ctx.say('Steve fell into a pit', { at: 'bottom' }); }
    },
  };
};

// Fort and temple: the room assembles block by block around the player, the camera cranes up.
function assemble(ctx, key, span, extra) {
  const sp = structureScene(ctx, key, FEET, { start: 0.3, span });
  if (!sp) return null;
  const P = ctx.pos;
  watch('structure', () => new THREE.Vector3(P.x, 2, P.z), 5);
  return {
    dur: sp.dur + 1.6,
    cam: (t) => ({ pos: V(P.x + 7.2, 4.0 + clamp01(t / sp.dur) * 2.4, P.z + 10.2), look: V(P.x - 0.4, 2.2, P.z), fov: 42 }),
    update(t, dt) {
      sp.update(t);
      ctx.steve.anim(t, dt, { walk: 0 });
      if (Math.floor(t * 2) !== ctx._sq && t < sp.dur) { ctx._sq = Math.floor(t * 2); sfx('dig.stone', { pos: { x: P.x, y: 2, z: P.z }, volume: 0.5, pitch: 0.9 + (ctx._sq % 3) * 0.1 }); }
      if (extra) extra(t);
    },
  };
}
STRUCT.fort = (ctx) => assemble(ctx, 'fort', 3.0);
STRUCT.temple = (ctx) => assemble(ctx, 'temple', 3.6);
STRUCT.ground_temple = (ctx) => assemble(ctx, 'temple', 3.6);

// Lucky choice: two lucky blocks with the sign between them, readable from the front.
STRUCT.lucky_choice = (ctx) => {
  const sp = structureScene(ctx, 'lucky_choice', FEET, { start: 0.3, span: 1.4 });
  if (!sp) return null;
  const P = ctx.pos;
  watch('blocks', () => new THREE.Vector3(P.x, 1.2, P.z + 2.2), 2);
  return {
    dur: sp.dur + 2.6,
    // the sign faces north, so the camera stands in front of it at eye height with both blocks and the
    // sign in frame; Steve steps to the left, out of the shot
    cam: (t) => ({ pos: V(P.x + 0.1, 1.65, P.z - 2.4), look: V(P.x, 1.1, P.z + 2.1), fov: 42 }),
    update(t, dt) {
      sp.update(t);
      ctx.steve.root.position.x = P.x - 2.6 * easeOut(t / 0.8);
      ctx.steve.anim(t, dt, { walk: 0 });
      if (t > 0.4 && !ctx._c1) { ctx._c1 = true; sfx('dig.stone', { volume: 0.8 }); sfx('random.click', { volume: 0.6 }); }
      if (t > sp.dur && !ctx._choice) { ctx._choice = true; sfx('random.orb', { volume: 0.6 }); ctx.say('One is lucky. One is not.', { at: 'bottom' }); }
    },
  };
};

import { makeBlock } from './blocks.js';
import { iconTexture } from './stage.js';
function lerpN(a, b, k) { return a + (b - a) * k; }

// ---- trapped chest: the chest opens and the TNT beneath it rises, primes, then blows.
STRUCT.trapped_chest = (ctx) => {
  const O = { x: 0, y: 1, z: 0 };
  const d = ctx.drop.actions.find((a) => a.t === 'block');
  if (!d || !d.blocks) return null;
  const chestG = makeBlock('minecraft:chest', 0, {});
  chestG.obj.position.set(0.5 - 0.5, 1, 0.5 - 0.5);
  ctx.S.temp.add(chestG.obj);
  const tnts = [];
  for (const b of d.blocks) {
    if (!/tnt/.test(b.id)) continue;
    const r = makeBlock('minecraft:tnt', 0, {});
    r.obj.position.set(-0.5, 0, -0.5);
    const h = new THREE.Group(); h.add(r.obj);
    h.position.set(O.x + (b.dx || 0) + 0.5, 1 - 2.2, O.z + (b.dz || 0) + 0.5);
    ctx.S.temp.add(h);
    tnts.push({ h, t0: 0.5 + tnts.length * 0.12, boom: false });
  }
  let blown = null;
  watch('chest', chestG.obj, 1);
  return {
    dur: 6.2,
    cam: (t) => ({ pos: V(4.0, 3.2, 6.2), look: V(0.5, 1.4, 0.5), fov: 42 }),
    update(t, dt) {
      const lid = chestG.lid;
      if (lid) lid.rotation.x = -easeOut((t - 1.0) / 0.9) * 1.9;
      if (t > 1.0 && !ctx._co) { ctx._co = true; sfx('random.chestopen', { volume: 1 }); }
      if (t > 2.2 && !ctx._fz) { ctx._fz = true; sfx('random.fuse', { volume: 1 }); }
      for (const q of tnts) {
        if (t < q.t0) continue;
        const k = easeOut((t - q.t0) / 0.8);
        q.h.position.y = (1 - 2.2) + 2.2 * k;
        const blink = Math.floor((t - 2) * 6) % 2 === 0 && t > 2.2;
        q.h.children[0].traverse((o) => { if (o.material) for (const mm of [].concat(o.material)) if (mm.emissive) mm.emissive.setRGB(blink ? 0.35 : 0, blink ? 0.35 : 0, blink ? 0.35 : 0); });
      }
      if (t > 4.6 && blown === null) {
        blown = t;
        ctx.explode(V(0.5, 1.5, 0.5), 1.2); sfx('random.explode', { volume: 1 });
        ctx.shake(0.6); ctx.flashScreen('#ffe7b0', 0.8, 0.5);
        for (const q of tnts) q.h.visible = false;
      }
      ctx.steve.anim(t, dt, { walk: 0 });
      if (t > 1.0 && !ctx._tc) { ctx._tc = true; ctx.say('Trapped', { at: 'bottom' }); }
    },
  };
};

// ---- troll ore: diamond ore falls onto a lava pool and sinks.
STRUCT.troll_ore = (ctx) => {
  const d = ctx.drop.actions.find((a) => a.t === 'falling');
  const blocks = d && d.blocks ? d.blocks.slice(0, 12) : [];
  if (!blocks.length) return null;
  const pool = [];
  for (let x = -1; x <= 1; x++) for (let z = -1; z <= 1; z++) {
    const r = makeBlock('minecraft:flowing_lava', 0, {});
    r.obj.position.set(x + 0.5 - 0.5, 1.0, z + 0.5 - 0.5);
    r.obj.position.set(x + 0.5 - 0.5 + 0.5 - 0.5, 1.0, z);
    const h = new THREE.Group(); h.add(r.obj); h.position.set(x, 1.0, z); ctx.S.temp.add(h); pool.push(h);
  }
  const ore = blocks.map((b, i) => {
    const r = makeBlock('minecraft:diamond_ore', 0, {});
    r.obj.position.set(-0.5, 0, -0.5);
    const h = new THREE.Group(); h.add(r.obj);
    const x = 0.5 + ((i % 3) - 1) * 0.9, z = 0.5 + (Math.floor(i / 3) - 1) * 0.9;
    h.position.set(x, 17, z); ctx.S.temp.add(h);
    return { h, x, z, t0: 0.6 + i * 0.25, landed: false };
  });
  const glint = light(ctx, 0xff7a2a, 2.5, 6, V(0.5, 1.6, 0.5));
  watch('ore', () => new THREE.Vector3(0.5, 3, 0.5), 3);
  return {
    dur: 5.4,
    cam: (t) => ({ pos: V(4.4, 5.6, 8.0), look: V(0.5, 3.0, 0.5), fov: 44 }),
    update(t, dt) {
      for (const o of ore) {
        if (t < o.t0) continue;
        const s = t - o.t0;
        const y = Math.max(1.5, 17 - 0.5 * 30 * s * s);
        o.h.position.y = y;
        if (y <= 1.6 && !o.landed) { o.landed = true; sfx('dig.stone', { volume: 0.7 }); sfx('liquid.lavapop', { volume: 0.7 }); landingBurst(ctx, V(o.x, 1.6, o.z), [0xff9a3a, 0xffd27a, 0xb8b0c4], 16, 0.3); ctx.shake(0.06); }
      }
      glint.intensity = 2.5 + 0.8 * Math.sin(t * 7);
      ctx.steve.anim(t, dt, { walk: 0 });
      if (t > 2.5 && !ctx._troll) { ctx._troll = true; ctx.say('Diamond ore over lava', { at: 'bottom' }); }
    },
  };
};

// ---- message: the chat line typed in letter by letter in the Minecraft font, bottom-left of the stage.
const MC_COL = { 0: '#000000', 1: '#0000AA', 2: '#00AA00', 3: '#00AAAA', 4: '#AA0000', 5: '#AA00AA', 6: '#FFAA00', 7: '#AAAAAA', 8: '#555555', 9: '#5555FF', a: '#55FF55', b: '#55FFFF', c: '#FF5555', d: '#FF55FF', e: '#FFFF55', f: '#FFFFFF' };
let fontImg = null;
const FONT_URL = new URL('./tex/font/ascii.png', import.meta.url).href;
STRUCT.message = (ctx) => {
  const raw = String(ctx.chatText || ctx.drop.title || '').replace(/\{player\}|#playerName/g, 'Steve').replace(/#([0-9a-fk-or])/g, '§$1');
  // segments: [{text, color}]
  const segs = [];
  let color = '#FFFFFF';
  for (const part of raw.split(/(§.)/)) {
    if (/^§./.test(part)) { const c = part[1].toLowerCase(); if (MC_COL[c]) color = MC_COL[c]; else if (c === 'r') color = '#FFFFFF'; continue; }
    if (part) segs.push({ text: part, color });
  }
  const chars = segs.flatMap((sg) => [...sg.text].map((ch) => ({ ch, color: sg.color })));
  const S = ctx.S;
  if (!S.camera.parent) S.scene.add(S.camera);
  const SC = 4; // 8px glyphs at 4x
  // the canvas is as wide as the line needs; the plane is sized from the camera's view at its
  // distance so the whole line sits inside the frame, bottom-left, whatever the aspect
  const W = Math.max(640, 28 + chars.length * 8 * SC), H = 8 * SC + 24;
  const cv = document.createElement('canvas'); cv.width = W; cv.height = H;
  const g = cv.getContext('2d');
  const hudTex = new THREE.CanvasTexture(cv); hudTex.colorSpace = THREE.SRGBColorSpace; hudTex.magFilter = THREE.NearestFilter; hudTex.minFilter = THREE.NearestFilter;
  const dist = 1.2;
  const hh = Math.tan(THREE.MathUtils.degToRad(42) / 2) * dist;
  const hw = hh * (S.camera.aspect || 1.5);
  const pw = Math.min(hw * 1.84, (W / H) * 0.085);
  const ph = pw * H / W;
  const hud = new THREE.Mesh(new THREE.PlaneGeometry(pw, ph), new THREE.MeshBasicMaterial({ map: hudTex, transparent: true, depthTest: false, depthWrite: false }));
  hud.renderOrder = 999;
  hud.position.set(-hw + 0.05 + pw / 2, -hh + 0.07 + ph / 2, -dist);
  S.camera.add(hud);
  if (!fontImg) { fontImg = new Image(); fontImg.src = FONT_URL; }
  const glyph = (x, y, color, ch) => {
    const code = ch.charCodeAt(0);
    if (code < 32 || code > 127) return x + 8 * SC;
    if (!fontImg || !fontImg.complete || !fontImg.naturalWidth) { g.fillStyle = color; g.fillRect(x, y, 6 * SC, 8 * SC); return x + 8 * SC; }
    const sx = (code % 16) * 8, sy = Math.floor(code / 16) * 8;
    const tmp = document.createElement('canvas'); tmp.width = 8; tmp.height = 8;
    const tg = tmp.getContext('2d');
    tg.imageSmoothingEnabled = false;
    tg.drawImage(fontImg, sx, sy, 8, 8, 0, 0, 8, 8);
    tg.globalCompositeOperation = 'source-in'; tg.fillStyle = color; tg.fillRect(0, 0, 8, 8);
    g.imageSmoothingEnabled = false;
    g.drawImage(tmp, x + SC / 2, y + SC / 2, 8 * SC, 8 * SC);
    return x + 8 * SC;
  };
  const CPS = 0.05; // seconds per character
  const t0 = 0.5;
  let shown = -1;
  const draw = (n) => {
    g.clearRect(0, 0, W, H);
    g.fillStyle = 'rgba(0,0,0,0.38)'; g.fillRect(0, 0, W, H);
    let x = 14, y = 16;
    for (let i = 0; i < Math.min(n, chars.length); i++) {
      const c = chars[i];
      // the shadow is the darker tone, offset by one glyph pixel
      glyph(x + SC, y + SC, '#2a2a2a', c.ch);
      x = glyph(x, y, c.color, c.ch);
    }
    if (n < chars.length && Math.floor(n) % 2 === 0) { g.fillStyle = '#ffffff'; g.fillRect(x + 4, y, 8, 8 * SC); }
    hudTex.needsUpdate = true;
  };
  const tEnd = t0 + chars.length * CPS + 1.6;
  const P = ctx.pos;
  return {
    dur: tEnd + 0.8,
    cam: () => ({ pos: V(P.x + 4.6, 1.9, P.z + 5.6), look: V(P.x - 0.3, 1.4, P.z), fov: 40 }),
    update(t, dt) {
      const n = Math.max(0, (t - t0) / CPS);
      const k = Math.floor(Math.min(n, chars.length));
      if (k !== shown || Math.floor(t * 2) !== shown) { shown = k; draw(n); }
      ctx.steve.anim(t, dt, { walk: 0 });
    },
  };
};

export const STRUCT_SCENES = STRUCT;
export { plan };
