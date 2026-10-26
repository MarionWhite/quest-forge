// The scenes: what the drop does in the world. Each builder returns
//   { dur, update(t, dt), cam(t) -> {pos, look, fov} }
// and gets a ctx from app.js: S (stage), drop, fx (per-frame effects), say(), chat(),
// hurt(a), tint(hex, a), shake(a), setVoxel(x,y,z,id), steve, pos (player feet), dais, name.
import * as THREE from 'three';
import { tex, glowTexture, BLOCK_TEX, iconTexture } from './stage.js';
import { makeMob } from './mobs.js';
import { BLOCK_FILE, plaque, textTexture, MOOD_COLOR } from './reel.js';
import { STRUCT_SCENES } from './structscenes.js';

const V = (x, y, z) => new THREE.Vector3(x, y, z);
const clamp01 = (x) => Math.max(0, Math.min(1, x));
const easeOut = (x) => 1 - Math.pow(1 - clamp01(x), 3);
const easeIn = (x) => clamp01(x) * clamp01(x);
const easeInOut = (x) => { x = clamp01(x); return x * x * (3 - 2 * x); };
const lerp = (a, b, k) => a + (b - a) * k;
const rnd = (a = 0, b = 1) => a + Math.random() * (b - a);

const matCache = new Map();
function blockMat(file, o = {}) {
  const key = file + JSON.stringify(o);
  if (!matCache.has(key)) matCache.set(key, new THREE.MeshLambertMaterial({ map: tex('blocks/' + file), ...o }));
  return matCache.get(key);
}
// A textured cube for a block id ("minecraft:stone"). Unknown ids use stone.
export function blockCube(id, size = 1, extra = {}) {
  const key = BLOCK_TEX[id];
  const file = (key && BLOCK_FILE[key]) || 'stone.png';
  const mat = blockMat(file, extra);
  const m = new THREE.Mesh(new THREE.BoxGeometry(size, size, size), mat);
  m.castShadow = true;
  return m;
}
const TNT_FILE = 'tnt_side.png';

// Particle burst: points that fly, fall and fade. Returns nothing; registers with ctx.fx.
function burst(ctx, pos, o = {}) {
  const n = o.n ?? 30, life = o.life ?? 0.9, gravity = o.gravity ?? 7;
  const speed = o.speed ?? 2.4, up = o.up ?? 1.6;
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
  ctx.S.temp.add(obj);
  let t = 0;
  ctx.fx.push({
    update(dt) {
      t += dt;
      for (let i = 0; i < n; i++) {
        vel[i * 3 + 1] -= gravity * dt;
        pts[i * 3] += vel[i * 3] * dt; pts[i * 3 + 1] += vel[i * 3 + 1] * dt; pts[i * 3 + 2] += vel[i * 3 + 2] * dt;
        if (pts[i * 3 + 1] < 0.02) { pts[i * 3 + 1] = 0.02; vel[i * 3 + 1] *= -0.3; vel[i * 3] *= 0.6; vel[i * 3 + 2] *= 0.6; }
      }
      geo.attributes.position.needsUpdate = true;
      mat.opacity = clamp01(1 - t / life);
      if (t >= life) { ctx.S.temp.remove(obj); geo.dispose(); mat.dispose(); return true; }
      return false;
    },
  });
}
// Smoke puff: the grey poof of a mob spawning, or a blast cloud.
function puff(ctx, pos, o = {}) {
  burst(ctx, pos, { n: o.n ?? 18, colors: o.colors ?? [0xd9d6df, 0x9d98a8, 0xbfbac8], size: o.size ?? 0.45, speed: o.speed ?? 1.2, up: 0.8, gravity: 0.5, life: o.life ?? 1.1, spread: 1.4 });
}

// A mob that appears with the poof, then idles.
function spawnMob(ctx, id, pos, o = {}) {
  const m = makeMob(id, o);
  m.root.position.copy(pos);
  if (o.rotY != null) m.root.rotation.y = o.rotY;
  m.root.traverse((x) => { if (x.isMesh) x.castShadow = true; });
  const base = m.root.scale.clone();
  m.root.scale.setScalar(0.001);
  ctx.S.temp.add(m.root);
  puff(ctx, pos.clone().setY(pos.y + 0.6), { n: 14, size: 0.5 });
  return { ...m, base, born: null };
}
// Each frame: grow in, keep the anim running.
function mobTick(m, t, dt, o = {}) {
  if (m.born === null) return;
  const k = clamp01((t - m.born) / 0.4);
  const s = easeOut(k) * (m.base ? 1 : 1);
  m.root.scale.copy(m.base).multiplyScalar(Math.max(0.001, s));
  m.anim(t, dt, o);
}

// Lights that a scene adds get removed with the temp group.
function pointLight(ctx, color, intensity, dist, pos) {
  const l = new THREE.PointLight(color, intensity, dist, 1.6);
  l.position.copy(pos);
  ctx.S.temp.add(l);
  return l;
}

// Plain solid overlay boxes/planes
function plane(w, h, color, opacity, additive = false) {
  return new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ color, transparent: true, opacity, depthWrite: false, blending: additive ? THREE.AdditiveBlending : THREE.NormalBlending, side: THREE.DoubleSide }));
}

// Sprite of an item icon, spinning like a 1.7.10 dropped item.
function itemSprite(ctx, icon, size = 0.7) {
  const g = new THREE.Group();
  const m = new THREE.Mesh(new THREE.PlaneGeometry(size, size), new THREE.MeshBasicMaterial({ map: iconTexture(icon), transparent: true, alphaTest: 0.5, side: THREE.DoubleSide }));
  g.add(m);
  // a thin edge so the flat sprite holds its shape when it turns edge-on
  g.userData.spinner = m;
  return g;
}
function textSprite(text, color = '#ECE6F2') {
  const m = new THREE.Mesh(new THREE.PlaneGeometry(1.4, 0.7), new THREE.MeshBasicMaterial({ map: textTexture(text, { color, size: 52, w: 512, h: 256 }), transparent: true, alphaTest: 0.1, side: THREE.DoubleSide }));
  return m;
}
export function nameTag(text, color = '#ffffff') {
  const c = document.createElement('canvas'); c.width = 256; c.height = 64;
  const g = c.getContext('2d'); g.font = '700 34px Archivo, sans-serif'; g.textAlign = 'center'; g.textBaseline = 'middle';
  g.fillStyle = 'rgba(14,11,18,0.6)'; g.fillRect(0, 0, 256, 64);
  g.fillStyle = color; g.fillText(text, 128, 34);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace;
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: t, transparent: true, depthWrite: false }));
  s.scale.set(1.6, 0.4, 1);
  return s;
}
function heartSprite() {
  const c = document.createElement('canvas'); c.width = c.height = 32;
  const g = c.getContext('2d'); g.fillStyle = '#e8485a';
  g.beginPath(); g.moveTo(16, 28); g.bezierCurveTo(-4, 16, 2, -2, 16, 8); g.bezierCurveTo(30, -2, 36, 16, 16, 28); g.fill();
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace;
  return new THREE.Sprite(new THREE.SpriteMaterial({ map: t, transparent: true, depthWrite: false }));
}

// Chest model with a hinged lid (chest.png 64x64)
export function buildChest(ctx) {
  const g = new THREE.Group();
  const body = new THREE.Mesh(boxGeo([-7, -10, -7, 14, 10, 14], [0, 19]), new THREE.MeshLambertMaterial({ map: tex('entity/chest.png') }));
  const lidPivot = new THREE.Group();
  lidPivot.position.set(0, 0.625, -0.4375);
  const lid = new THREE.Mesh(boxGeo([-7, -5, 0, 14, 5, 14], [0, 0]), body.material);
  lid.position.set(0, 0, 0);
  lidPivot.add(lid);
  g.add(body, lidPivot);
  g.userData.lid = lidPivot;
  return g;
}
// Box geometry from a 1.7.10 box, cached per call.
import { boxGeometry as boxGeo0 } from './mobs.js';
function boxGeo(box, uv) { return boxGeo0(box, uv, 64, 64); }

// --------------------------------------------------------------------- scenes
const SCENES = {};

// Lava trap / water trap: a shell of blocks forms around the player and fills.
function fluidTrap(ctx, fluid) {
  const P = ctx.pos.clone();
  const cx = Math.round(P.x - 0.2), cz = Math.round(P.z - 0.2);
  const cells = [];
  for (let x = -1; x <= 1; x++) for (let z = -1; z <= 1; z++) {
    for (let y = 0; y <= 2; y++) {
      const ring = Math.abs(x) === 1 || Math.abs(z) === 1;
      if (!ring && y === 0) continue;
      if (!ring) continue;
      cells.push([cx + x, y, cz + z]);
    }
  }
  const shell = [];
  cells.forEach(([x, y, z], i) => {
    const b = blockCube(fluid === 'lava' ? 'minecraft:stonebrick' : 'minecraft:cobblestone', 1);
    b.position.set(x + 0.5, y + 0.5 + 4, z + 0.5);
    ctx.S.temp.add(b);
    shell.push({ m: b, to: y + 0.5, t0: 0.4 + i * 0.07, x, y, z });
  });
  const inside = { x: cx + 0.5, z: cz + 0.5 };
  const liquid = new THREE.Mesh(new THREE.BoxGeometry(0.96, 1, 0.96),
    fluid === 'lava'
      ? new THREE.MeshLambertMaterial({ map: animTexLocal('blocks/lava_still.png'), emissive: 0xff6a1a, emissiveIntensity: 1.4, transparent: true, opacity: 0.92 })
      : new THREE.MeshLambertMaterial({ map: animTexLocal('blocks/water_still.png'), color: 0x3f7fd6, transparent: true, opacity: 0.72 }));
  liquid.position.set(inside.x, 0.5, inside.z);
  liquid.scale.y = 0.001;
  ctx.S.temp.add(liquid);
  let light = null;
  if (fluid === 'lava') light = pointLight(ctx, 0xff7a2a, 4, 7, V(inside.x, 1.5, inside.z));
  return { shell, liquid, light, inside, cx, cz };
}
import { animTex as animTexLocal } from './stage.js';

// Pit: the ground opens under the player and seals over.
function pitScene(ctx, label) {
  const P = ctx.pos.clone();
  const cx = Math.round(P.x - 0.2), cz = Math.round(P.z - 0.2);
  const removed = [];
  for (let x = -1; x <= 1; x++) for (let z = -1; z <= 1; z++) for (let y = -1; y >= -3; y--) {
    const id = ctx.S.vox.get(cx + x, y, cz + z);
    if (id) { removed.push([cx + x, y, cz + z, id]); ctx.setVoxel(cx + x, y, cz + z, null); }
  }
  const caps = [];
  for (let x = -1; x <= 1; x++) for (let z = -1; z <= 1; z++) {
    const b = blockCube('minecraft:grass', 1);
    b.position.set(cx + x + 0.5, 0.5 - 1, cz + z + 0.5 + 0);
    b.visible = false;
    ctx.S.temp.add(b);
    caps.push(b);
  }
  return {
    dur: 6.0,
    cam: (t) => ({ pos: V(ctx.pos.x + 5.5, 6.2, ctx.pos.z + 6.6), look: V(ctx.pos.x, -0.6, ctx.pos.z), fov: 40 }),
    update(t, dt) {
      const fall = clamp01((t - 1.0) / 1.0);
      const y = lerp(0, -3.0, easeIn(fall));
      ctx.steve.root.position.y = y;
      ctx.steve.anim(t, dt, { walk: 0, armRaise: 0.9 * fall });
      ctx.steve.root.rotation.z = Math.sin(t * 9) * 0.2 * fall;
      if (t > 2.0 && !ctx._hit) { ctx._hit = true; ctx.shake(0.18); puff(ctx, V(P.x, -2.9, P.z), { n: 16, size: 0.35, colors: [0x6d6878, 0x8c8698] }); }
      // the seal: grass blocks drop back over the hole
      for (let i = 0; i < caps.length; i++) {
        const b = caps[i];
        const t0 = 3.3 + i * 0.04;
        if (t < t0) continue;
        b.visible = true;
        const k = easeIn(clamp01((t - t0) / 0.35));
        b.position.y = lerp(4.5, -0.5, k * k);
        if (k >= 1 && !b.userData.landed) { b.userData.landed = true; puff(ctx, V(b.position.x, 1, b.position.z), { n: 4, size: 0.2 }); }
      }
      if (t > 3.4 && !ctx._sealed) { ctx._sealed = true; for (const [x, y, z, id] of removed) ctx.setVoxel(x, y, z, id); for (const b of caps) b.visible = false; }
      if (t > 3.1 && !ctx._say && label) { ctx._say = true; ctx.say(label, { at: 'bottom' }); }
    },
  };
}
SCENES.jens_hole = (ctx) => {
  const base = pitScene(ctx, '');
  const witch = spawnMob(ctx, 'Witch', V(ctx.pos.x - 0.6, -2.9, ctx.pos.z + 0.2), { rotY: 0.4 });
  witch.born = 0.6;
  const tag = nameTag('Jen', '#ffe9a8');
  tag.position.set(ctx.pos.x - 0.6, -1.9, ctx.pos.z + 0.2);
  ctx.S.temp.add(tag);
  const update = base.update;
  base.update = (t, dt) => {
    update(t, dt);
    mobTick(witch, t, dt, { walk: 0, lookAt: 0.2 });
    tag.position.y = -1.9 + (t > 1 ? 0 : 0);
  };
  base.dur = 6.4;
  return base;
};

// Falling column (ore poles, death pole): the blocks fall in order to their offsets.
SCENES.falling_column = (ctx) => {
  const blocks = ctx.blocks();
  const O = ctx.dais.clone(); // the broken block's cell is at (0,1,0)
  const items = blocks.slice(0, 90).map((b, i) => {
    const m = blockCube(b.id || 'minecraft:stone', 1);
    const tx = O.x - 0.5 + (b.dx || 0) + 0.5, ty = O.y - 0.5 + (b.dy || 0) + 0.5, tz = O.z - 0.5 + (b.dz || 0) + 0.5;
    m.position.set(tx, ty + 14, tz);
    ctx.S.temp.add(m);
    return { m, tx, ty, tz, t0: 0.4 + i * 0.09, landed: false, tnt: /tnt/.test(b.id || ''), id: b.id };
  });
  const top = Math.max(4, ...blocks.map((b) => (b.dy || 0) + 2));
  const last = items.length ? items[items.length - 1].t0 : 0;
  return {
    dur: Math.max(5.2, last + 1.8),
    cam: (t) => ({ pos: V(O.x + 6.4, 2.2 + top * 0.25, O.z + 7.6), look: V(O.x, 1 + top * 0.5, O.z), fov: 40 }),
    update(t, dt) {
      for (const it of items) {
        if (t < it.t0) continue;
        const s = t - it.t0;
        const y = it.ty + Math.max(0, 14 - 0.5 * 26 * s * s);
        it.m.position.y = y;
        if (y <= it.ty && !it.landed) {
          it.landed = true; it.m.position.y = it.ty;
          ctx.shake(0.07);
          puff(ctx, V(it.tx, it.ty - 0.4, it.tz), { n: 6, size: 0.25 });
          if (it.tnt) { ctx.explode(V(it.tx, it.ty, it.tz), 0.6); }
        }
      }
    },
  };
};

// Placed blocks: the rainbow, poles and patterns pop in around the origin.
SCENES.placed_blocks = (ctx) => {
  const blocks = (ctx.blocks()).slice(0, 160);
  const O = ctx.dais.clone();
  const items = blocks.map((b, i) => {
    const m = blockCube(b.id || 'minecraft:stone', 1);
    m.position.set(O.x - 0.5 + (b.dx || 0) + 0.5, O.y - 0.5 + (b.dy || 0) + 0.5, O.z - 0.5 + (b.dz || 0) + 0.5);
    m.scale.setScalar(0.001);
    ctx.S.temp.add(m);
    return { m, t0: 0.2 + (i / Math.max(1, blocks.length)) * 2.4, done: false };
  });
  return {
    dur: 5.0,
    cam: (t) => { const a = 0.8 + t * 0.12; return { pos: V(O.x + Math.sin(a) * 8.5, 5.2, O.z + Math.cos(a) * 8.5), look: V(O.x, 1.5, O.z), fov: 42 }; },
    update(t) {
      for (const it of items) {
        if (t < it.t0) continue;
        const k = clamp01((t - it.t0) / 0.28);
        it.m.scale.setScalar(0.001 + easeOut(k) * (1 + 0.1 * Math.sin(k * Math.PI)) * 0.999);
        if (k >= 1 && !it.done) { it.done = true; puff(ctx, it.m.position, { n: 3, size: 0.2 }); }
      }
    },
  };
};

// Mob groups: horde (streams in from the fog), spawn (a few in front), tower (riding stacks).
function groupScene(ctx, list, mode) {
  const P = ctx.pos.clone();
  const mobs = [];
  list.forEach((e, i) => {
    // hordes come from the far side of Steve (the block side) out of the fog, 10 to 14 blocks away
    const ang = mode === 'horde' ? Math.PI + rnd(-0.9, 0.9) : rnd(-0.9, 0.9) - Math.PI / 2 + (i / list.length) * 0.5;
    const rad = mode === 'horde' ? rnd(10, 14) : rnd(4, 6);
    const spawn = V(P.x + Math.cos(ang) * rad + 1.2, 0, P.z + Math.sin(ang) * rad);
    const goal = V(P.x + Math.cos(ang) * 3.0 + 1.1, 0, P.z + Math.sin(ang) * 3.0);
    const m = spawnMob(ctx, e.id, spawn, { color: e.color, scale: 1, rotY: Math.atan2(-(goal.x - spawn.x), -(goal.z - spawn.z)) });
    m.born = (mode === 'horde' ? 0.3 : 0.4) + i * (mode === 'horde' ? 0.08 : 0.35);
    m.spawn = spawn; m.goal = goal;
    mobs.push(m);
  });
  // the tallest thing in the group (a Giant is a zombie at 6x) decides how far back the camera sits
  const tallest = Math.max(1.8, ...mobs.map((m) => (m.height || 1.8) * (m.base ? m.base.x : 1)));
  const back = Math.max(0, tallest - 2.2) * 0.9;
  return {
    dur: mode === 'horde' ? 5.8 : 4.8,
    mobs,
    cam: (t) => (mode === 'horde'
      ? { pos: V(P.x + 4.6 + back, 2.5 + back * 0.45, P.z + 0.6 + back * 0.3), look: V(P.x - 6, 1.6 + back * 0.4, P.z), fov: 52 }
      : { pos: V(P.x + 5.2 + back, 3.6 + back * 0.5, P.z + 7.2 + back), look: V(P.x + 0.4, 1.4 + back * 0.4, P.z - 0.2), fov: 40 }),
    update(t, dt) {
      for (const m of mobs) {
        if (m.born === null) continue;
        const k = easeOut(clamp01((t - m.born) / (mode === 'horde' ? 3.4 : 1.2)));
        m.root.position.lerpVectors(m.spawn, m.goal, k);
        mobTick(m, t, dt, { walk: t > m.born ? 1 : 0, creep: m.id === 'Creeper' });
        if (m.id === 'Creeper' && t > m.born + 1.0) {
          const h = clamp01((t - m.born - 1) / 1.5);
          m.anim(t, dt, { walk: 0, hiss: h });
        }
      }
    },
  };
}
SCENES.mob_horde = (ctx) => groupScene(ctx, ctx.entities(12), 'horde');
SCENES.mob_spawn = (ctx) => groupScene(ctx, ctx.entities(4), 'spawn');
SCENES.pet = (ctx) => {
  const base = groupScene(ctx, ctx.entities(1).length ? ctx.entities(1) : [{ id: 'Wolf' }], 'spawn');
  const hearts = [];
  for (let i = 0; i < 5; i++) { const h = heartSprite(); h.scale.setScalar(0.4); ctx.S.temp.add(h); hearts.push(h); }
  const up = base.update;
  base.update = (t, dt) => {
    up(t, dt);
    hearts.forEach((h, i) => {
      const k = ((t - 1.6 - i * 0.25) % 2.4 + 2.4) % 2.4;
      h.position.set(ctx.pos.x + 2.7 + i * 0.18, 1.5 + k * 0.7, ctx.pos.z + 0.4);
      h.material.opacity = clamp01(1 - k / 2.4) * (t > 1.6 ? 1 : 0);
    });
  };
  return base;
};
SCENES.mob_tower = (ctx) => {
  const P = ctx.pos.clone();
  const stacks = ctx.stacks();
  const all = [];
  const pieces = [];
  let stackH = 3;
  stacks.forEach((stack, si) => {
    const ang = -Math.PI / 2 + (si - (stacks.length - 1) / 2) * 0.9;
    const bx = P.x + Math.cos(ang) * 4.2, bz = P.z + Math.sin(ang) * 4.2;
    let y = 0;
    stack.forEach((id, li) => {
      const m = spawnMob(ctx, id, V(bx, y, bz), { rotY: -ang + Math.PI / 2 });
      m.born = 0.6 + si * 0.25 + li * 0.45;
      m.base0 = V(bx, y, bz);
      // a rider sits on the mob below it: height times the model's scale (a Giant is a zombie at 6x)
      y += (m.height || 1.8) * (m.base ? m.base.x : 1) * 0.85;
      pieces.push(m); all.push(m);
    });
    stackH = Math.max(stackH, y);
  });
  // the tallest stack sets the camera distance and the look height
  const tb = Math.max(0, stackH - 4) * 1.1;
  return {
    dur: 5.4,
    cam: (t) => ({ pos: V(P.x + 7.4 + tb, 3.2 + t * 0.2 + tb * 0.55, P.z + 8.2 + tb), look: V(P.x + 0.4, Math.min(stackH * 0.5, 3.4 + tb * 0.5), P.z - 1.2), fov: 44 }),
    update(t, dt) {
      for (const m of all) {
        if (m.born === null || t < m.born) continue;
        mobTick(m, t, dt, { walk: 0 });
        m.root.rotation.z = Math.sin(t * 3 + m.born) * 0.06;
      }
    },
  };
};
SCENES.boss = (ctx) => {
  const P = ctx.pos.clone();
  const e = ctx.entities(1)[0] || { id: 'Zombie' };
  // the boss walks in from 20 blocks out, through the fog, toward Steve (+x)
  const spawn = V(P.x - 20, 0, P.z + 0.5);
  const goal = V(P.x - 4.5, 0, P.z + 0.5);
  const m = spawnMob(ctx, e.id, spawn, { rotY: -Math.PI / 2, color: e.color });
  m.born = 0.6;
  let fogOut = true;
  const roar = pointLight(ctx, 0xff5a2a, 0, 10, V(goal.x, 3, goal.z));
  const walkT = 3.4;
  const kAt = (t) => easeOut(clamp01((t - m.born) / walkT));
  return {
    dur: 6.0,
    // the camera is low, six blocks from Steve, and tilts up as the boss nears
    cam: (t) => {
      const k = kAt(t);
      const bx = lerp(spawn.x, goal.x, k);
      return { pos: V(P.x + 17.0, 1.4, P.z + 0.3), look: V(bx, lerp(3.0, 9.0, k), 0.5), fov: 50 };
    },
    update(t, dt) {
      if (t >= m.born) {
        const k = kAt(t);
        m.root.position.lerpVectors(spawn, goal, k);
        mobTick(m, t, dt, { walk: 1 - k * 0.5 });
      }
      roar.intensity = 6 * clamp01((t - 3.9) / 0.6) * (1 - clamp01((t - 5.2) / 1.2));
      if (fogOut && t > 4.0) { fogOut = false; ctx.shake(0.4); ctx.flashScreen('#ffffff', 0.25, 0.4); puff(ctx, goal, { n: 30, size: 0.9 }); }
      if (t > 4.2 && !ctx._say) { ctx._say = true; ctx.say(ctx.bossTitle || (e.name || e.id) + ' is here', { at: 'bottom' }); }
    },
  };
};

// Items: pop out of the place where the block was, spin, glint if enchanted.
function itemsScene(ctx, list, o = {}) {
  const O = ctx.dais.clone();
  const items = list.slice(0, 12);
  const sprites = items.map((it, i) => {
    const g = new THREE.Group();
    const n = items.length;
    const ang = (n === 1 ? 0 : (i / (n - 1) - 0.5) * (o.fan || 2.4)) + Math.PI / 2;
    const target = V(O.x + Math.cos(ang) * (o.radius || 2.5) * 0.9, 1.6 + (i % 2) * 0.3, O.z + Math.sin(ang) * (o.radius || 2.5) * 0.9 + 1.1);
    const s = it.icon ? itemSprite(ctx, it.icon, 0.72) : textSprite(it.name || it.id || '?');
    g.add(s);
    if (it.ench) {
      const glint = new THREE.Mesh(new THREE.PlaneGeometry(0.8, 0.8), new THREE.MeshBasicMaterial({ map: glowTexture('rgba(190,120,255,0.9)'), transparent: true, opacity: 0.6, blending: THREE.AdditiveBlending, depthWrite: false }));
      glint.position.z = 0.02;
      g.add(glint);
      g.userData.glint = glint;
    }
    g.position.set(O.x, O.y + 0.4, O.z);
    g.scale.setScalar(0.001);
    ctx.S.temp.add(g);
    return { g, target, t0: 0.5 + i * 0.22, it, spin: rnd(0, 6) };
  });
  return {
    dur: Math.max(4.8, 0.5 + items.length * 0.22 + 2.2),
    cam: (t) => ({ pos: V(O.x + 0.3, 1.9, O.z + 4.9 + (o.zoom || 0)), look: V(O.x, 1.7, O.z + 0.8), fov: 40 }),
    update(t, dt) {
      for (const s of sprites) {
        if (t < s.t0) continue;
        const k = clamp01((t - s.t0) / 0.7);
        const e = easeOut(k);
        s.g.position.lerpVectors(V(O.x, O.y + 0.4, O.z), s.target, e);
        s.g.position.y += Math.sin(k * Math.PI) * 1.2;
        s.g.scale.setScalar(0.001 + e);
        const sp = s.g.children[0];
        sp.rotation.y = (t * 2.6) + s.spin;
        sp.position.y = Math.sin(t * 2.2 + s.spin) * 0.04;
        if (s.g.userData.glint) s.g.userData.glint.material.opacity = 0.35 + 0.3 * Math.sin(t * 4 + s.spin);
      }
    },
  };
}
SCENES.item_drop = (ctx) => itemsScene(ctx, ctx.items(1), { radius: 1.6, fan: 0.6 });
SCENES.item_set = (ctx) => itemsScene(ctx, ctx.items(9), { radius: 3.2, fan: 2.8 });
SCENES.fireworks_loot = (ctx) => {
  const base = itemsScene(ctx, ctx.items(6), { radius: 3.0, fan: 2.4 });
  const O = ctx.dais.clone();
  const cols = [0xff5a5a, 0xf2c14e, 0x8fd3a0, 0x9d7bff, 0x5ad2ff];
  const bursts = [0.6, 1.6, 2.6];
  const oldUpd = base.update;
  base.update = (t, dt) => {
    oldUpd(t, dt);
    bursts.forEach((bt, i) => { if (!base['b' + i] && t >= bt) { base['b' + i] = 1; burst(ctx, V(O.x + (i - 1) * 2.2, 6.5 + i * 0.4, O.z), { n: 70, colors: cols, size: 0.14, speed: 3.2, up: 1.2, life: 1.6, additive: true, gravity: 2.2 }); ctx.shake(0.06); } });
  };
  return base;
};
SCENES.chest = (ctx) => chestScene(ctx, ctx.items(6), false);
SCENES.trapped_chest = (ctx) => chestScene(ctx, ctx.items(3), true);
function chestScene(ctx, list, trapped) {
  const O = ctx.dais.clone();
  const chest = buildChest(ctx);
  chest.position.set(O.x - 0.5, O.y - 1, O.z - 0.5);
  chest.scale.setScalar(1.2);
  chest.position.set(0.5, 1, 0.5);
  chest.scale.setScalar(1.25);
  ctx.S.temp.add(chest);
  const base = itemsScene(ctx, list, { radius: 3.4, fan: 2.6 });
  const up = base.update;
  base.update = (t, dt) => {
    const k = easeOut(clamp01((t - 0.2) / 0.9));
    chest.userData.lid.rotation.x = -k * 1.9;
    up(t, dt);
  };
  if (trapped) base.dur = Math.max(base.dur, 5.6);
  return base;
}
// Sky temple: a platform high above, a beam from the block into the sky.
SCENES.sky_temple = (ctx) => {
  const O = ctx.dais.clone();
  const plat = [];
  for (let x = -3; x <= 3; x++) for (let z = -3; z <= 3; z++) {
    const edge = Math.abs(x) === 3 || Math.abs(z) === 3;
    if (!edge && !(x === 0 && z === 0)) continue;
    const m = blockCube('minecraft:stonebrick', 1);
    m.position.set(O.x + x, 26 + 6, O.z + z);
    ctx.S.temp.add(m);
    plat.push({ m, to: 26, t0: 0.4 + (Math.abs(x) + Math.abs(z)) * 0.12 });
  }
  const beamMat = new THREE.MeshBasicMaterial({ map: glowTexture('rgba(255,230,200,1)'), color: 0xffe2b8, transparent: true, opacity: 0, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide });
  const beam = new THREE.Mesh(new THREE.PlaneGeometry(1.4, 26), beamMat);
  beam.position.set(O.x, 13, O.z);
  ctx.S.temp.add(beam);
  const beam2 = beam.clone(); beam2.rotation.y = Math.PI / 2; ctx.S.temp.add(beam2);
  return {
    dur: 5.6,
    cam: (t) => ({ pos: V(O.x + 7.5, 4 + clamp01(t / 4) * 3, O.z + 8.2), look: V(O.x, 12 + clamp01(t / 4) * 6, O.z), fov: 46 }),
    update(t) {
      for (const p of plat) {
        if (t < p.t0) continue;
        const k = easeIn(clamp01((t - p.t0) / 0.7));
        p.m.position.y = lerp(p.to + 6, p.to, k * k);
      }
      beamMat.opacity = 0.7 * clamp01((t - 1.2) / 1.0) * (0.85 + 0.15 * Math.sin(t * 3));
    },
  };
};

// TNT, lightning, rains and explosions
SCENES.explosion = (ctx) => {
  const O = ctx.dais.clone();
  const debris = [];
  for (let i = 0; i < 30; i++) {
    const m = blockCube(i % 3 ? 'minecraft:dirt' : 'minecraft:tnt', rnd(0.15, 0.3));
    m.position.set(O.x, O.y + 0.2, O.z);
    ctx.S.temp.add(m);
    const a = rnd(0, Math.PI * 2), s = rnd(2.5, 5);
    debris.push({ m, v: V(Math.cos(a) * s, rnd(3, 7), Math.sin(a) * s), w: V(rnd(-8, 8), rnd(-8, 8), rnd(-8, 8)) });
  }
  let blast = false;
  return {
    dur: 5.0,
    cam: (t) => ({ pos: V(O.x + 4.3, 2.4 + t * 0.05, O.z + 5.6), look: V(O.x, 1.2, O.z), fov: 46 }),
    update(t, dt) {
      if (!blast && t > 0.25) {
        blast = true;
        ctx.shake(0.7); ctx.flashScreen('#ffe7b0', 0.9, 0.45);
        puff(ctx, V(O.x, 1.4, O.z), { n: 60, size: 0.9, speed: 3.2, colors: [0x2c2a31, 0x5a5560, 0x8c8698, 0xf08a3c] });
        burst(ctx, V(O.x, 1.4, O.z), { n: 80, colors: [0xffd27a, 0xf08a3c, 0xffffff], size: 0.2, speed: 6, up: 2.2, life: 0.9, additive: true, gravity: 4 });
        for (let x = -1; x <= 1; x++) for (let z = -1; z <= 1; z++) ctx.setVoxel(x, 0, z, null);
        ctx.explode(V(O.x, 1, O.z), 1.0);
      }
      for (const d of debris) {
        if (!blast) continue;
        d.v.y -= 14 * dt;
        d.m.position.addScaledVector(d.v, dt);
        d.m.rotation.x += d.w.x * dt; d.m.rotation.y += d.w.y * dt;
        if (d.m.position.y < 0.1) { d.m.position.y = 0.1; d.v.y *= -0.3; d.v.x *= 0.6; d.v.z *= 0.6; }
      }
      if (t > 0.1 && t < 1.2 && Math.random() < dt * 9) burst(ctx, V(O.x + rnd(-1, 1), 0.5, O.z + rnd(-1, 1)), { n: 5, colors: [0x6e6a78, 0x9c97a8], size: 0.45, speed: 0.6, up: 1.6, gravity: -0.4, life: 1.8 });
    },
  };
};
SCENES.tnt_rain = (ctx) => {
  const P = ctx.pos.clone();
  const N = 36;
  const tnts = [];
  for (let i = 0; i < N; i++) {
    const m = blockCube('minecraft:tnt', 0.5);
    m.material = m.material.clone();
    m.position.set(P.x + rnd(-2.5, 2.5), 0.4, P.z + rnd(-2.5, 2.5));
    m.visible = false;
    ctx.S.temp.add(m);
    tnts.push({ m, t0: 0.4 + i * 0.07, v: V(rnd(-0.6, 0.6), rnd(5, 7.5), rnd(-0.6, 0.6)), landed: false, y: 0.4, blink: rnd(0, 1) });
  }
  return {
    dur: 5.4,
    cam: (t) => ({ pos: V(P.x + 6.4, 5.4, P.z + 9.2), look: V(P.x, 2.6, P.z), fov: 46 }),
    update(t, dt) {
      for (const it of tnts) {
        if (t < it.t0) continue;
        it.m.visible = true;
        if (!it.landed) {
          const s = t - it.t0;
          it.v.y -= 16 * dt;
          it.y = Math.max(0.25, it.y + it.v.y * dt);
          it.m.position.x += it.v.x * dt; it.m.position.z += it.v.z * dt;
          it.m.position.y = it.y;
          it.m.rotation.x += dt * 4;
          if (it.y <= 0.25 && s > 0.2) { it.landed = true; it.landTime = t; }
        }
        if (it.landTime && t - it.landTime > 0.6 && !it.blew) {
          it.blew = true; it.m.visible = false;
          ctx.explode(it.m.position.clone(), 0.5);
          ctx.shake(0.12);
          puff(ctx, it.m.position.clone().setY(0.6), { n: 14, size: 0.5 });
        }
        if (!it.landed) { const on = Math.floor((t * 5 + it.blink) % 2) ? 1 : 0; it.m.material.emissive.setRGB(on, on, on); }
      }
    },
  };
};
SCENES.expbottle_rain = (ctx) => {
  const P = ctx.pos.clone();
  const bottles = [];
  const glass = new THREE.MeshLambertMaterial({ color: 0x5fe38b, transparent: true, opacity: 0.8 });
  for (let i = 0; i < 26; i++) {
    const m = new THREE.Mesh(new THREE.BoxGeometry(0.2, 0.32, 0.2), glass);
    m.position.set(P.x + rnd(-2.2, 2.2), 7, P.z + rnd(-2.2, 2.2));
    ctx.S.temp.add(m);
    bottles.push({ m, t0: 0.3 + i * 0.08, landed: false, v: rnd(-1, 1) });
  }
  return {
    dur: 4.8,
    cam: (t) => ({ pos: V(P.x + 5.6, 4.2, P.z + 8.2), look: V(P.x, 2.4, P.z), fov: 44 }),
    update(t, dt) {
      for (const b of bottles) {
        if (t < b.t0 || b.landed) continue;
        const s = t - b.t0;
        const y = 7 - 0.5 * 18 * s * s;
        b.m.position.y = Math.max(0.2, y);
        b.m.rotation.z += b.v * dt * 6;
        if (y <= 0.2) { b.landed = true; b.m.visible = false; burst(ctx, V(b.m.position.x, 0.4, b.m.position.z), { n: 14, colors: [0x7bff9f, 0xb8ff3a, 0xffe36a], size: 0.12, speed: 1.6, up: 2, life: 1.2, additive: true }); }
      }
    },
  };
};
SCENES.xp_burst = (ctx) => {
  const P = ctx.pos.clone();
  const N = 180;
  const geo = new THREE.SphereGeometry(0.07, 6, 4);
  const mat = new THREE.MeshBasicMaterial({ color: 0x9dff4a });
  const inst = new THREE.InstancedMesh(geo, mat, N);
  ctx.S.temp.add(inst);
  const orbs = [];
  const dummy = new THREE.Object3D();
  for (let i = 0; i < N; i++) {
    const a = rnd(0, Math.PI * 2), s = rnd(0.6, 3.2);
    orbs.push({ p: V(P.x + rnd(-0.2, 0.2), 1.2, P.z + rnd(-0.2, 0.2)), v: V(Math.cos(a) * s, rnd(3, 6), Math.sin(a) * s), t0: rnd(0, 0.6), ph: rnd(0, 6) });
  }
  return {
    dur: 5.4,
    cam: (t) => ({ pos: V(P.x + 4.6, 3.6, P.z + 6.8), look: V(P.x, 1.1, P.z), fov: 44 }),
    update(t, dt) {
      orbs.forEach((o, i) => {
        if (t >= o.t0) {
          o.v.y -= 14 * dt;
          o.p.addScaledVector(o.v, dt);
          if (o.p.y < 0.07) { o.p.y = 0.07; o.v.y *= -0.55; o.v.x *= 0.8; o.v.z *= 0.8; }
        }
        const pulse = 1 + 0.35 * Math.sin(t * 9 + o.ph);
        dummy.position.copy(o.p); dummy.scale.setScalar(pulse); dummy.updateMatrix();
        inst.setMatrixAt(i, dummy.matrix);
      });
      inst.instanceMatrix.needsUpdate = true;
    },
  };
};
SCENES.lightning = (ctx) => {
  const O = ctx.dais.clone();
  const bolt = new THREE.Group();
  const boltMat = new THREE.MeshBasicMaterial({ color: 0xf4f8ff, transparent: true, opacity: 1, blending: THREE.AdditiveBlending, depthWrite: false });
  let y = 26, x = O.x, z = O.z;
  while (y > 2) {
    const ny = Math.max(2, y - rnd(2, 4)), nx = O.x + rnd(-0.6, 0.6), nz = O.z + rnd(-0.6, 0.6);
    const seg = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, Math.hypot(ny - y, nx - x, nz - z), 4), boltMat);
    seg.position.set((x + nx) / 2, (y + ny) / 2, (z + nz) / 2);
    seg.lookAt(nx, ny, nz); seg.rotateX(Math.PI / 2);
    bolt.add(seg);
    x = nx; y = ny; z = nz;
  }
  bolt.visible = false;
  ctx.S.temp.add(bolt);
  const glow = pointLight(ctx, 0xbfd6ff, 0, 14, V(O.x, 3, O.z));
  return {
    dur: 4.6,
    cam: (t) => ({ pos: V(O.x + 4.6, 2.6 + clamp01(t / 4) * 0.3, O.z + 6.2), look: V(O.x, 2.6, O.z), fov: 44 }),
    update(t) {
      const strike = t > 0.5 && t < 0.75;
      bolt.visible = strike || (t > 0.85 && t < 0.95);
      boltMat.opacity = strike ? 1 : 0.6;
      glow.intensity = (strike ? 60 : 0) + (t > 0.85 && t < 1.2 ? 8 : 0);
      if (Math.abs(t - 0.5) < 0.02 && !ctx._bolt) { ctx._bolt = 1; ctx.flashScreen('#f2f6ff', 0.95, 0.5); ctx.shake(0.5); burst(ctx, V(O.x, 1, O.z), { n: 40, colors: [0xffa040, 0xffe08a], size: 0.3, speed: 2.4, up: 2, life: 1.2, additive: true }); }
      if (t > 1.0 && Math.random() < 0.3 * 0.5) burst(ctx, V(O.x + rnd(-0.9, 0.9), 0.4, O.z + rnd(-0.9, 0.9)), { n: 3, colors: [0xff7a2a, 0xffc060], size: 0.4, speed: 0.3, up: 2.2, gravity: -1.2, life: 0.9, additive: true });
    },
  };
};
SCENES.bedrock_problem = (ctx) => {
  const O = ctx.dais.clone();
  const cells = [];
  for (let i = 0; i < 14; i++) {
    const a = (i / 14) * Math.PI * 2;
    const m = blockCube('minecraft:bedrock', 1.05);
    cells.push({ m, a, t0: 0.3 + i * 0.05 });
    ctx.S.temp.add(m);
  }
  return {
    dur: 5.0,
    cam: (t) => ({ pos: V(O.x + 4.6, 3.2, O.z + 7.2), look: V(O.x, 1.4, O.z), fov: 42 }),
    update(t) {
      for (const c of cells) {
        const k = easeOut(clamp01((t - c.t0) / 1.4));
        const r = lerp(6.5, 2.1, k);
        c.m.position.set(O.x + Math.cos(c.a) * r, lerp(0.5, 1.8 + 0.2 * Math.sin(c.a * 3), k), O.z + Math.sin(c.a) * r);
        c.m.rotation.y = c.a + k * 0.6;
      }
      if (t > 1.8 && !ctx._bed) { ctx._bed = 1; ctx.shake(0.1); }
    },
  };
};

// Lucky block family and the sprite-only scenes that stay simple
// Message: a Minecraft chat line over the scene.
SCENES.message = (ctx) => {
  const P = ctx.pos.clone();
  ctx.chat(ctx.chatText || '');
  return {
    dur: 4.2,
    cam: (t) => ({ pos: V(P.x + 4.8, 2.8, P.z + 7.6), look: V(P.x, 1.6, P.z), fov: 42 }),
    update(t, dt) { ctx.steve.anim(t, dt, { walk: 0 }); ctx.steve.root.rotation.y = Math.PI / 2 + Math.sin(t * 1.2) * 0.25; },
  };
};
SCENES.effect = (ctx) => {
  const P = ctx.pos.clone();
  const col = new THREE.Color(ctx.effectColor || 0x9d7bff);
  const swirl = [];
  for (let i = 0; i < 90; i++) swirl.push({ a: rnd(0, 6.28), r: rnd(0.6, 2.6), y: rnd(0, 2.2), s: rnd(0.4, 1) });
  const geo = new THREE.BufferGeometry();
  const pos = new Float32Array(swirl.length * 3);
  geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  const mat = new THREE.PointsMaterial({ size: 0.16, color: col, map: glowTexture(), transparent: true, depthWrite: false, blending: THREE.AdditiveBlending });
  const pts = new THREE.Points(geo, mat);
  ctx.S.temp.add(pts);
  let said = false;
  return {
    dur: 5.0,
    cam: (t) => ({ pos: V(P.x + 4.6, 2.4, P.z + 6.0), look: V(P.x, 1.1, P.z), fov: 42 }),
    update(t, dt) {
      swirl.forEach((s, i) => {
        const a = s.a + t * (1.2 + s.s);
        pos[i * 3] = P.x + Math.cos(a) * s.r; pos[i * 3 + 1] = (s.y + t * 0.5) % 2.4; pos[i * 3 + 2] = P.z + Math.sin(a) * s.r;
      });
      geo.attributes.position.needsUpdate = true;
      ctx.tint(ctx.effectColor || 0x9d7bff, 0.22 * clamp01(t / 1.5) * (1 - clamp01((t - 4) / 1)));
      if (!said) { said = true; ctx.say(ctx.effectName || 'Effect', { at: 'top' }); }
      ctx.steve.anim(t, dt, { walk: 0 });
    },
  };
};
SCENES.time = (ctx) => {
  const O = ctx.dais.clone();
  return {
    dur: 5.0,
    cam: (t) => ({ pos: V(O.x + 6.4, 3.4 + t * 0.12, O.z + 8.4), look: V(O.x, 2.6 + t * 0.2, O.z), fov: 44 }),
    update(t, dt) {
      const k = easeInOut(clamp01(t / 2.0));
      ctx.S.setNight(k);
      ctx.S.sunDrop(k);
      ctx.S.stars.material.size = 1.2 + k * 0.6;
      if (!ctx._t) { ctx._t = 1; ctx.say('The time is set to night', { at: 'bottom' }); }
    },
  };
};
SCENES.apocalypse = (ctx) => {
  const O = ctx.dais.clone();
  const P = ctx.pos.clone();
  const sword = itemsScene(ctx, ctx.items(1), { radius: 1.2, fan: 0 });
  const hordeList = ctx.entities(14);
  const hordeMobs = [];
  hordeList.forEach((e, i) => {
    const ang = (i / Math.max(1, hordeList.length)) * Math.PI * 2 + 0.2;
    const spawn = V(P.x + Math.cos(ang) * 14, 0, P.z + Math.sin(ang) * 14);
    const goal = V(P.x + Math.cos(ang) * 3.2, 0, P.z + Math.sin(ang) * 3.2);
    const m = spawnMob(ctx, e.id, spawn, { color: e.color });
    m.born = 6.2 + i * 0.12; m.spawn = spawn; m.goal = goal; hordeMobs.push(m);
  });
  let hit = false;
  return {
    dur: 12.0,
    mobs: hordeMobs,
    cam: (t) => {
      if (t < 2.0) return { pos: V(O.x + 4.5, 3.8, O.z + 6.6), look: V(O.x, 1.2, O.z), fov: 42 };
      if (t < 6.0) return { pos: V(P.x + 6.8, 3.2, P.z + 8.2), look: V(P.x, 1.4, P.z), fov: 44 };
      return { pos: V(P.x + 7.6, 5.2 - (t - 6) * 0.2, P.z + 11.4), look: V(P.x + 0.4, 1.2, P.z), fov: 48 };
    },
    update(t, dt) {
      const k = easeInOut(clamp01(t / 2.0));
      ctx.S.setNight(k); ctx.S.sunDrop(k);
      if (t > 2.6 && !ctx._sword) { ctx._sword = 1; }
      if (t > 2.1) sword.update(t - 2.1, dt);
      if (t > 3.6) ctx.tint(0x000000, 0.34 * clamp01((t - 3.6) / 1.4));
      if (t > 5.2) ctx.tint(0x8b5cf6, 0.16 * clamp01((t - 5.2) / 1.0));
      ctx.steve.anim(t, dt, { walk: 0 });
      ctx.steve.root.rotation.y = Math.PI / 2 + Math.sin(t * 1.4) * 0.3;
      hordeMobs.forEach((m) => {
        if (t < m.born) return;
        const kk = easeOut(clamp01((t - m.born) / 3.0));
        m.root.position.lerpVectors(m.spawn, m.goal, kk);
        mobTick(m, t, dt, { walk: 1 });
      });
      if (t > 2.2 && !ctx._apoc1) { ctx._apoc1 = 1; ctx.say('Night, and the sword drops', { at: 'bottom' }); }
      if (t > 5.4 && !ctx._apoc2) { ctx._apoc2 = 1; ctx.say('Blindness and slowness', { at: 'bottom' }); }
      if (t > 6.4 && !ctx._apoc3) { ctx._apoc3 = 1; ctx.say('The hordes close in from the fog', { at: 'bottom' }); ctx.shake(0.2); }
    },
  };
};

// Villager trader, troll ore, and the generic fallback
SCENES.villager_trader = (ctx) => {
  const P = ctx.pos.clone();
  const v = spawnMob(ctx, 'Villager', V(P.x + 2.4, 0, P.z - 0.8), { rotY: Math.PI });
  v.born = 0.5;
  return {
    dur: 4.4,
    cam: (t) => ({ pos: V(P.x + 5.6, 2.8, P.z + 6.8), look: V(P.x + 1.2, 1.5, P.z), fov: 40 }),
    update(t, dt) { mobTick(v, t, dt, { walk: 0 }); },
  };
};
SCENES.troll_ore = (ctx) => {
  const O = ctx.dais.clone();
  const lava = fluidTrap(ctx, 'lava');
  const ore = blockCube('minecraft:diamond_ore', 1);
  ore.position.set(O.x, 6, O.z);
  ctx.S.temp.add(ore);
  return {
    dur: 4.8,
    cam: (t) => ({ pos: V(O.x + 4.2, 3.6, O.z + 6.4), look: V(O.x, 2.0, O.z), fov: 42 }),
    update(t, dt) {
      const k = easeIn(clamp01((t - 0.8) / 1.0));
      ore.position.y = lerp(6, 3.2, k * k);
      ore.rotation.y = t * 0.3;
      const fill = clamp01((t - 0.4) / 1.6);
      lava.liquid.scale.y = Math.max(0.001, easeOut(fill) * 1.7);
      lava.liquid.position.y = 0.5 * lava.liquid.scale.y;
      if (lava.shell) for (const s of lava.shell) { s.m.visible = false; }
      if (t > 2.0 && !ctx._troll) { ctx._troll = 1; ctx.say('Diamond ore over lava', { at: 'bottom' }); }
    },
  };
};
SCENES.generic = (ctx) => {
  const O = ctx.dais.clone();
  const plq = plaque(ctx.drop);
  plq.position.set(O.x, 2.8, O.z + 1.0);
  plq.scale.setScalar(1.6);
  ctx.S.temp.add(plq);
  return {
    dur: 4.0,
    cam: (t) => ({ pos: V(O.x + 0.6, 2.5, O.z + 5.4), look: V(O.x, 2.2, O.z), fov: 40 }),
    update(t) { plq.rotation.y = Math.sin(t * 1.4) * 0.3; plq.position.y = 2.8 + Math.sin(t * 2) * 0.08; },
  };
};

// Keys the engine implements explicitly; anything else falls back to generic.
Object.assign(SCENES, STRUCT_SCENES);
export const SCENE_KEYS = Object.keys(SCENES);
export function buildScene(key, ctx) {
  const f = SCENES[key] || SCENES.generic;
  try {
    return f(ctx) || SCENES.generic(ctx);
  } catch (e) {
    console.warn('scene', key, e);
    return SCENES.generic(ctx);
  }
}
export { MOOD_COLOR, puff, burst, blockCube as cube, pointLight };
