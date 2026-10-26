// The scenes: what the drop does in the world. Each builder returns
//   { dur, update(t, dt), cam(t) -> {pos, look, fov}, report() }
// and gets a ctx from app.js: S (stage), drop, fx (per-frame effects), say(), chat(), hurt(a),
// tint(hex, a), shake(a), setVoxel(x,y,z,id), explode(pos, power), flashScreen(), steve, pos
// (Steve's feet), dais (the broken block). Every scene rolls its own outcome from drop.actions
// (fx.roll) the way the mod does, so what plays is what the block would have done.
//
// Scene files: this one (items, blocks, explosions, effects, the dud), mobscenes.js (hordes,
// towers, pets, bosses and the grand entrances), wells.js (wells and temples), structscenes.js
// (structures from structures.json).
import * as THREE from 'three';
import { animTex, glowTexture, tex } from './stage.js';
import { makeBlock } from './blocks.js';
import { boxGeometry as boxGeo0 } from '../lib/mc/mobs.js';
import { plaque, MOOD_COLOR } from './reel.js';
import { STRUCT_SCENES } from './structscenes.js';
import { structureScene } from './structures.js';
import { MOB_SCENES } from './mobscenes.js';
import { WELL_SCENES } from './wells.js';
import { itemsBeat, tntBeat, fireworksBeat, dudBeat, itemsCam } from './beats.js';
import * as F from './fx.js';
const { V, clamp01, easeOut, easeIn, easeInOut, lerp, rnd, burst, puff, pointLight, sfx, roll, itemsOf, watch, blockCube, spawnMob, mobTick, nameTag, cleanName, labelSprite, facing } = F;

const SCENES = { ...STRUCT_SCENES, ...MOB_SCENES, ...WELL_SCENES };

// ------------------------------------------------------------------ chest
function boxGeo(box, uv) { return boxGeo0(box, uv, 64, 64); }
export function buildChest() {
  const g = new THREE.Group();
  const body = new THREE.Mesh(boxGeo([-7, -10, -7, 14, 10, 14], [0, 19]), new THREE.MeshLambertMaterial({ map: tex('entity/chest.png') }));
  const lidPivot = new THREE.Group();
  lidPivot.position.set(0, 0.625, -0.4375);
  const lid = new THREE.Mesh(boxGeo([-7, -5, 0, 14, 5, 14], [0, 0]), body.material);
  lidPivot.add(lid);
  g.add(body, lidPivot);
  g.userData.lid = lidPivot;
  return g;
}

// ------------------------------------------------------------------ blocks that fall or are placed
const SOUND_OF = (id) => (/glass/.test(id) ? 'dig.glass' : /wool/.test(id) ? 'dig.cloth' : /planks|bookshelf|crafting/.test(id) ? 'dig.wood' : /dirt|hay|sand/.test(id) ? 'dig.gravel' : 'dig.stone');
function cellOf(b) { return { x: b.dx || 0, y: b.dy || 0, z: b.dz || 0 }; }
function blockObj(b) {
  const r = makeBlock(b.id || 'minecraft:stone', b.meta || 0, {});
  const h = new THREE.Group();
  r.obj.position.set(-0.5, 0, -0.5);
  h.add(r.obj);
  return { h, light: r.light };
}
// Which way the camera should look at a set of cells: head-on for a flat picture (a heart, a portal).
function shapeCam(O, cells, tall) {
  const xs = cells.map((c) => c.x), zs = cells.map((c) => c.z), ys = cells.map((c) => c.y);
  const sx = Math.max(...xs) - Math.min(...xs), sz = Math.max(...zs) - Math.min(...zs);
  const top = Math.max(...ys), bot = Math.min(...ys);
  const cx = O.x + (Math.max(...xs) + Math.min(...xs)) / 2, cz = O.z + (Math.max(...zs) + Math.min(...zs)) / 2;
  const mid = O.y + (top + bot) / 2 + 0.5;
  const size = Math.max(sx, sz, top - bot + 1, 3);
  const d = 4.5 + size * 1.15;
  const down = bot < 0;
  return () => {
    if (sz === 0 && sx > 0) return { pos: V(cx + 0.5, mid + (down ? d * 0.6 : 0.4), cz + d), look: V(cx + 0.5, mid, cz + 0.5), fov: 42 };
    if (sx === 0 && sz > 0) return { pos: V(cx + d, mid + (down ? d * 0.6 : 0.4), cz + 0.5), look: V(cx + 0.5, mid, cz + 0.5), fov: 42 };
    return { pos: V(cx + d * 0.62, Math.max(2.2, mid + (down ? d * 0.75 : d * 0.18)), cz + d * 0.85), look: V(cx + 0.5, mid - (down ? 0.5 : 0), cz + 0.5), fov: 42 };
  };
}
function carve(ctx, cells, O) {
  for (const c of cells) {
    const wy = Math.floor(O.y) + c.y;
    if (wy >= -8 && wy < Math.floor(O.y)) ctx.setVoxel(Math.floor(O.x) + c.x, wy, Math.floor(O.z) + c.z, null);
  }
}
function blockList(ctx, rolled, key) {
  const a = rolled.find((x) => x.t === key) || rolled.find((x) => x.t === 'falling' || x.t === 'block');
  return ((a && a.blocks) || []).filter((b) => b.id !== 'minecraft:air' && b.id !== 'minecraft:fire').slice(0, 110);
}

// Blocks fall out of the sky onto the dais in order and stack.
SCENES.falling_column = (ctx) => {
  const rolled = roll(ctx.drop.actions);
  const blocks = blockList(ctx, rolled, 'falling');
  const O = V(Math.floor(ctx.dais.x), 1, Math.floor(ctx.dais.z));
  const cells = blocks.map(cellOf);
  carve(ctx, cells, O);
  const n = blocks.length;
  const gap = Math.min(0.1, 3.4 / Math.max(1, n));
  const H = 15;
  const items = blocks.map((b, i) => {
    const o = blockObj(b);
    const c = cells[i];
    const tx = O.x + c.x + 0.5, ty = O.y + c.y, tz = O.z + c.z + 0.5;
    o.h.position.set(tx, ty + H, tz);
    ctx.S.temp.add(o.h);
    return { h: o.h, tx, ty, tz, t0: 0.5 + i * gap, landed: false, id: b.id, c };
  });
  const hasTnt = blocks.some((b) => /tnt/.test(b.id)) && blocks.some((b) => /redstone_block/.test(b.id));
  const last = n ? items[n - 1].t0 + Math.sqrt((2 * H) / 26) : 0;
  const chain = items.filter((i) => /tnt/.test(i.id)).sort((a, b) => a.ty - b.ty);
  const cam = shapeCam(O, cells.length ? cells : [{ x: 0, y: 0, z: 0 }], true);
  if (n) watch('blocks', () => V(O.x + 0.5, O.y + (Math.max(...cells.map((c) => c.y)) + 1) / 2, O.z + 0.5), Math.max(2, Math.max(...cells.map((c) => c.y)) + 1));
  let landSnd = 0, rumble = false;
  return {
    dur: Math.max(5.0, last + 1.6 + (hasTnt ? 3 : 0)),
    cam: (t) => { const c = cam(); if (t < 0.5) c.pos.y += (0.5 - t) * 2; return c; },
    update(t, dt) {
      for (const it of items) {
        if (t < it.t0) continue;
        const s = t - it.t0;
        const y = it.ty + Math.max(0, H - 0.5 * 26 * s * s);
        it.h.position.y = y;
        if (y <= it.ty && !it.landed) {
          it.landed = true; it.h.position.y = it.ty;
          ctx.shake(0.07);
          puff(ctx, V(it.tx, it.ty + 0.1, it.tz), { n: 6, size: 0.25 });
          if (landSnd++ % 2 === 0 || n < 6) sfx(SOUND_OF(it.id), { pos: { x: it.tx, y: it.ty, z: it.tz }, volume: 0.8 });
        }
      }
      if (hasTnt && t > last + 0.5) {
        // the redstone block powers the TNT: it blinks, then goes off from the bottom up
        if (!rumble) { rumble = true; sfx('random.fuse', { pos: ctx.dais, volume: 0.9 }); }
        chain.forEach((it, i) => {
          const tb = last + 1.4 + i * 0.16;
          const blink = t < tb && Math.floor(t * 8) % 2 === 0 ? 0.8 : 0;
          it.h.traverse((o) => { if (o.material && o.material.emissive) o.material.emissive.setRGB(blink, blink, blink); });
          if (t >= tb && !it.blew) { it.blew = true; it.h.visible = false; ctx.explode(V(it.tx, it.ty + 0.5, it.tz), 0.7); sfx('random.explode', { pos: { x: it.tx, y: it.ty, z: it.tz }, volume: 0.8 }); ctx.shake(0.2); }
        });
      }
    },
  };
};

// Blocks pop into place around the dais (towers, rainbows, the diamond trap).
SCENES.placed_blocks = (ctx) => {
  const rolled = roll(ctx.drop.actions);
  const blocks = blockList(ctx, rolled, 'block');
  const O = V(Math.floor(ctx.dais.x), 1, Math.floor(ctx.dais.z));
  const cells = blocks.map(cellOf);
  carve(ctx, cells, O);
  const items = blocks.map((b, i) => {
    const o = blockObj(b);
    const c = cells[i];
    o.h.position.set(O.x + c.x + 0.5, O.y + c.y, O.z + c.z + 0.5);
    o.h.scale.setScalar(0.001);
    ctx.S.temp.add(o.h);
    return { h: o.h, t0: 0.3 + (i / Math.max(1, blocks.length)) * 2.6, done: false, id: b.id };
  });
  const cam = shapeCam(O, cells.length ? cells : [{ x: 0, y: 0, z: 0 }]);
  watch('blocks', () => V(O.x + 0.5, O.y + 1, O.z + 0.5), 3);
  let sn = 0;
  return {
    dur: 5.2,
    cam: (t) => { const c = cam(); const a = Math.sin(t * 0.35) * 0.9; c.pos.x += a; return c; },
    update(t) {
      for (const it of items) {
        if (t < it.t0) continue;
        const k = clamp01((t - it.t0) / 0.28);
        it.h.scale.setScalar(0.001 + easeOut(k) * (1 + 0.1 * Math.sin(k * Math.PI)) * 0.999);
        if (k >= 1 && !it.done) { it.done = true; if (sn++ % 3 === 0) sfx(SOUND_OF(it.id), { pos: it.h.position, volume: 0.6 }); }
      }
    },
  };
};

// ------------------------------------------------------------------ explosions
SCENES.explosion = (ctx) => {
  const P = ctx.pos.clone();
  const steve = ctx.steve;
  const cx = Math.round(P.x - 0.2), cz = Math.round(P.z - 0.2);
  const debris = [];
  for (let i = 0; i < 40; i++) {
    const m = blockCube(i % 3 ? 'minecraft:dirt' : 'minecraft:grass', rnd(0.2, 0.4));
    m.position.set(P.x, 0.3, P.z);
    m.visible = false;
    ctx.S.temp.add(m);
    const a = rnd(0, Math.PI * 2), s = rnd(3, 7);
    debris.push({ m, v: V(Math.cos(a) * s, rnd(5, 10), Math.sin(a) * s), w: V(rnd(-8, 8), rnd(-8, 8), rnd(-8, 8)) });
  }
  const ball = new THREE.Mesh(new THREE.SphereGeometry(1, 20, 14), new THREE.MeshBasicMaterial({ color: 0xffb04a, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false, fog: false }));
  ctx.S.temp.add(ball);
  const ring = new THREE.Mesh(new THREE.RingGeometry(0.9, 1.0, 40), new THREE.MeshBasicMaterial({ color: 0xffe9c0, transparent: true, opacity: 0, side: THREE.DoubleSide, depthWrite: false, blending: THREE.AdditiveBlending }));
  ring.rotation.x = -Math.PI / 2; ring.position.set(P.x, 0.1, P.z);
  ctx.S.temp.add(ring);
  const T0 = 0.9;
  let blast = false;
  watch('steve', () => V(P.x, 1.0, P.z), 1.8);
  return {
    dur: 5.6,
    cam: (t) => ({ pos: V(P.x - 0.5 + (t > T0 ? Math.min(1.5, (t - T0) * 0.6) : 0), 2.2, P.z + 7.6), look: V(P.x - 0.6, 1.5, P.z), fov: 48 }),
    update(t, dt) {
      if (t < T0) { steve.anim(t, dt, { walk: 0 }); return; }
      const a = t - T0;
      if (!blast) {
        blast = true;
        ctx.shake(0.9); ctx.flashScreen('#fff1c8', 1.0, 0.5);
        sfx('random.explode', { pos: P, volume: 1 });
        puff(ctx, V(P.x, 1.0, P.z), { n: 70, size: 1.0, speed: 3.6, colors: [0x2c2a31, 0x5a5560, 0x8c8698, 0xf08a3c] });
        burst(ctx, V(P.x, 1.0, P.z), { n: 90, colors: [0xffd27a, 0xf08a3c, 0xffffff], size: 0.22, speed: 7, up: 3, life: 1.0, additive: true, gravity: 4 });
        for (let x = -2; x <= 2; x++) for (let z = -2; z <= 2; z++) if (x * x + z * z <= 5) ctx.setVoxel(cx + x, -1, cz + z, null);
        ctx.explode(V(P.x, 1, P.z), 1.0);
        debris.forEach((d) => { d.m.visible = true; });
        sfx('game.player.hurt', { volume: 0.8 });
      }
      ball.material.opacity = 0.9 * clamp01(1 - a / 0.5); ball.scale.setScalar(0.5 + a * 9);
      ball.position.set(P.x, 1.0, P.z);
      ring.material.opacity = 0.8 * clamp01(1 - a / 0.8); ring.scale.setScalar(0.5 + a * 14);
      for (const d of debris) {
        d.v.y -= 16 * dt;
        d.m.position.addScaledVector(d.v, dt);
        d.m.rotation.x += d.w.x * dt; d.m.rotation.y += d.w.y * dt;
        if (d.m.position.y < 0.1) { d.m.position.y = 0.1; d.v.y *= -0.3; d.v.x *= 0.6; d.v.z *= 0.6; }
      }
      // Steve is thrown back, tumbles, lands flat
      const k = clamp01(a / 1.1);
      steve.root.position.set(P.x + 1.0 * easeOut(k), Math.sin(k * Math.PI) * 3.2, P.z);
      steve.root.rotation.z = -easeOut(k) * Math.PI * 0.5;
      steve.mat.emissive.setRGB(0.5 * clamp01(1 - a / 1.5), 0.05, 0.02);
      ctx.hurt(0.6 * clamp01(1 - a / 2));
    },
  };
};

SCENES.tnt_rain = (ctx) => {
  const rolled = roll(ctx.drop.actions);
  const a = rolled.find((x) => x.t === 'tnt') || { n: 24 };
  const P = ctx.pos.clone();
  const beat = tntBeat(ctx, a.n);
  watch('tnt', () => V(P.x - 1, 1.2, P.z), 3);
  let said = false;
  return {
    dur: beat.dur + 0.4,
    cam: () => ({ pos: V(P.x - 0.8, 3.0, P.z + 9.6), look: V(P.x - 1.2, 1.3, P.z - 0.2), fov: 48 }),
    update(t, dt) {
      beat.update(t, dt);
      ctx.steve.anim(t, dt, { walk: 0, armRaise: 0.4 });
      if (!said && t > 0.5) { said = true; ctx.say(a.n + ' TNT launched at you', { at: 'bottom' }); }
    },
  };
};

SCENES.expbottle_rain = (ctx) => {
  const rolled = roll(ctx.drop.actions);
  const a = rolled.find((x) => x.t === 'expbottle') || { n: 20 };
  const P = ctx.pos.clone();
  const from = V(0.5, 1.8, 0.5);
  const N = Math.min(a.n, 34);
  const glass = new THREE.MeshLambertMaterial({ color: 0x5fe38b, emissive: 0x1d6a33, transparent: true, opacity: 0.85 });
  const bottles = [];
  for (let i = 0; i < N; i++) {
    const m = new THREE.Mesh(new THREE.BoxGeometry(0.22, 0.3, 0.22), glass);
    m.visible = false; ctx.S.temp.add(m);
    bottles.push({ m, t0: 0.4 + i * 0.1, to: V(P.x + rnd(-2.2, 0.8), 0.2, P.z + rnd(-2, 2)), fl: rnd(0.7, 1.0), landed: false });
  }
  watch('bottles', () => V(P.x - 1, 1.2, P.z), 3);
  let sn = 0;
  return {
    dur: 0.4 + N * 0.1 + 2.4,
    cam: () => ({ pos: V(P.x - 0.8, 3.0, P.z + 9.0), look: V(P.x - 1.2, 1.3, P.z), fov: 46 }),
    update(t, dt) {
      for (const b of bottles) {
        if (t < b.t0 || b.landed) continue;
        const s = t - b.t0, k = clamp01(s / b.fl);
        b.m.visible = true;
        b.m.position.set(lerp(from.x, b.to.x, k), lerp(from.y, b.to.y, k) + Math.sin(k * Math.PI) * 2.2, lerp(from.z, b.to.z, k));
        b.m.rotation.z += dt * 9;
        if (k >= 1) {
          b.landed = true; b.m.visible = false;
          burst(ctx, V(b.to.x, 0.3, b.to.z), { n: 16, colors: [0x7bff9f, 0xb8ff3a, 0xffe36a], size: 0.14, speed: 1.8, up: 2.4, life: 1.2, additive: true });
          if (sn++ % 2 === 0) sfx('random.glass', { pos: b.to, volume: 0.6, pitch: 1.2 });
          if (sn % 3 === 0) sfx('random.orb', { pos: b.to, volume: 0.6 });
        }
      }
      ctx.steve.anim(t, dt, { walk: 0 });
    },
  };
};

SCENES.xp_burst = (ctx) => {
  const P = ctx.pos.clone();
  const N = 150;
  const inst = new THREE.InstancedMesh(new THREE.SphereGeometry(0.08, 6, 4), new THREE.MeshBasicMaterial({ color: 0x9dff4a }), N);
  inst.frustumCulled = false;
  ctx.S.temp.add(inst);
  const dummy = new THREE.Object3D();
  const orbs = [];
  for (let i = 0; i < N; i++) {
    const a = rnd(0, Math.PI * 2), s = rnd(0.6, 3.0);
    orbs.push({ p: V(P.x + rnd(-1, 1), 8 + rnd(0, 4), P.z + rnd(-1, 1)), v: V(Math.cos(a) * s * 0.4, 0, Math.sin(a) * s * 0.4), t0: rnd(0, 1.6), ph: rnd(0, 6), take: 2.2 + rnd(0, 1.8), gone: false });
  }
  let absorbed = 0, lvl = false;
  const chest = V(P.x, 1.1, P.z);
  watch('steve', () => V(P.x, 1.0, P.z), 1.8);
  return {
    dur: 6.4,
    cam: () => ({ pos: V(P.x - 0.6, 2.8, P.z + 6.4), look: V(P.x - 0.3, 2.0, P.z), fov: 46 }),
    update(t, dt) {
      orbs.forEach((o, i) => {
        if (t >= o.t0 && !o.gone) {
          if (t < o.take) {
            o.v.y -= 9 * dt; o.p.addScaledVector(o.v, dt);
            if (o.p.y < 0.1) { o.p.y = 0.1; o.v.y *= -0.5; o.v.x *= 0.8; o.v.z *= 0.8; }
          } else {
            const d = chest.clone().sub(o.p); const L = d.length();
            o.v.addScaledVector(d.normalize(), 30 * dt); o.v.multiplyScalar(0.94); o.p.addScaledVector(o.v, dt);
            if (L < 0.3) { o.gone = true; absorbed++; if (absorbed % 8 === 1) sfx('random.orb', { pos: P, volume: 0.7, pitch: 0.8 + absorbed / N }); }
          }
        }
        const pulse = o.gone || t < o.t0 ? 0.0001 : 1 + 0.35 * Math.sin(t * 9 + o.ph);
        dummy.position.copy(o.p); dummy.scale.setScalar(pulse); dummy.updateMatrix();
        inst.setMatrixAt(i, dummy.matrix);
      });
      inst.instanceMatrix.needsUpdate = true;
      const g = clamp01((absorbed / N));
      ctx.steve.mat.emissive.setRGB(0.05, 0.05 + 0.4 * g, 0.05);
      if (!lvl && absorbed >= N * 0.9) { lvl = true; sfx('random.levelup', { volume: 0.9 }); ctx.say('Experience level up', { at: 'bottom' }); burst(ctx, V(P.x, 1.0, P.z), { n: 40, colors: [0x9dff4a, 0xffffff], size: 0.16, speed: 1.4, up: 3, life: 1.2, additive: true, gravity: 1 }); }
      ctx.steve.anim(t, dt, { walk: 0 });
    },
  };
};

// ------------------------------------------------------------------ items
function itemScene(ctx, mode) {
  const rolled = roll(ctx.drop.actions);
  let items = itemsOf(rolled);
  if (!items.length) items = [{ id: 'random', name: 'Item', n: 1 }];
  const beat = itemsBeat(ctx, items, { mode });
  return { dur: beat.dur, cam: beat.cam, update: beat.update };
}
SCENES.item_drop = (ctx) => itemScene(ctx, 'pop');
SCENES.item_set = (ctx) => itemScene(ctx, 'pop');
SCENES.fireworks_loot = (ctx) => {
  const rolled = roll(ctx.drop.actions);
  const items = itemsOf(rolled);
  const fw = rolled.find((a) => a.t === 'fireworks') || { n: 10 };
  const beat = itemsBeat(ctx, items, { start: 1.0 });
  const f = fireworksBeat(ctx, fw.n, { start: 0.3 });
  return { dur: Math.max(beat.dur, f.dur), cam: () => { const c = beat.cam(); c.look.y += 0.9; c.fov = 44; return c; }, update(t, dt) { beat.update(t, dt); f.update(t, dt); } };
};
SCENES.chest = (ctx) => {
  const rolled = roll(ctx.drop.actions);
  let items = itemsOf(rolled);
  const chest = buildChest();
  const O = ctx.dais.clone();
  chest.position.set(O.x, O.y, O.z);
  chest.scale.setScalar(1.25);
  ctx.S.temp.add(chest);
  watch('chest', chest, 1.2);
  if (!items.length) items = [{ id: 'random', name: 'Loot', n: 1 }, { id: 'random', n: 1 }, { id: 'random', n: 1 }, { id: 'random', n: 1 }];
  const beat = itemsBeat(ctx, items, { start: 1.2, mode: 'pop', origin: V(O.x, O.y + 0.4, O.z) });
  let opened = false;
  return {
    dur: beat.dur,
    cam: () => { const c = beat.cam(); c.pos.y += 0.5; return c; },
    update(t, dt) {
      const k = easeOut(clamp01((t - 0.3) / 0.8));
      chest.userData.lid.rotation.x = -k * 1.9;
      if (!opened && t > 0.3) { opened = true; sfx('random.chestopen', { pos: O, volume: 0.9 }); }
      beat.update(t, dt);
    },
  };
};

// ------------------------------------------------------------------ bedrock
SCENES.bedrock_problem = (ctx) => {
  const sp = structureScene(ctx, 'bedrock_problem', { x: 0, y: 1, z: 0 }, { start: 0.5, span: 0.6 });
  const O = ctx.dais.clone();
  let said = false, snd = false;
  watch('bedrock', () => V(0.5, 1.5, 0.5), 1.5);
  return {
    dur: 5.0,
    cam: () => ({ pos: V(1.6, 2.1, 4.4), look: V(0.5, 1.5, 0.5), fov: 40 }),
    update(t, dt) {
      if (sp) sp.update(t);
      if (!snd && t > 0.5) { snd = true; sfx('dig.stone', { pos: O, volume: 1 }); sfx('random.anvil_land', { pos: O, volume: 0.5, pitch: 0.7 }); ctx.shake(0.2); puff(ctx, V(0.5, 1.2, 0.5), { n: 14, size: 0.4 }); }
      if (!said && t > 1.4) { said = true; ctx.say("Well, there's your problem.", { at: 'bottom' }); }
      ctx.steve.anim(t, dt, { walk: 0 });
    },
  };
};

// ------------------------------------------------------------------ effects and messages
SCENES.effect = (ctx) => {
  const P = ctx.pos.clone();
  const col = new THREE.Color(ctx.effectColor || 0x9d7bff);
  const swirl = [];
  for (let i = 0; i < 90; i++) swirl.push({ a: rnd(0, 6.28), r: rnd(0.6, 2.2), y: rnd(0, 2.2), s: rnd(0.4, 1) });
  const geo = new THREE.BufferGeometry();
  const pos = new Float32Array(swirl.length * 3);
  geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  const pts = new THREE.Points(geo, new THREE.PointsMaterial({ size: 0.16, color: col, map: glowTexture(), transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }));
  pts.frustumCulled = false;
  ctx.S.temp.add(pts);
  const msg = roll(ctx.drop.actions).find((a) => a.t === 'message');
  let said = false, drank = false, chatted = false;
  watch('steve', () => V(P.x, 1.0, P.z), 1.8);
  return {
    dur: 5.4,
    cam: () => ({ pos: V(P.x - 1.2, 2.0, P.z + 5.2), look: V(P.x - 0.6, 1.1, P.z), fov: 42 }),
    update(t, dt) {
      swirl.forEach((s, i) => {
        const a = s.a + t * (1.2 + s.s);
        pos[i * 3] = P.x + Math.cos(a) * s.r; pos[i * 3 + 1] = (s.y + t * 0.5) % 2.4; pos[i * 3 + 2] = P.z + Math.sin(a) * s.r;
      });
      geo.attributes.position.needsUpdate = true;
      ctx.tint(ctx.effectColor || 0x9d7bff, 0.22 * clamp01((t - 0.8) / 1.5) * (1 - clamp01((t - 4.4) / 1)));
      if (!drank && t > 0.4) { drank = true; sfx('random.drink', { pos: P, volume: 0.9 }); sfx('random.burp', { pos: P, volume: 0.5 }); }
      if (!said && t > 1.0) { said = true; ctx.say(ctx.effectName || 'Effect', { at: 'top' }); }
      if (!chatted && msg && t > 1.6) { chatted = true; ctx.chat(msg.text); }
      ctx.steve.anim(t, dt, { walk: 0, armRaise: 0.8 * clamp01(1 - Math.abs(t - 0.8)) });
    },
  };
};
SCENES.message = (ctx) => {
  const rolled = roll(ctx.drop.actions);
  const items = itemsOf(rolled);
  const chat = STRUCT_SCENES.message(ctx);
  const O = ctx.dais.clone();
  const beat = items.length ? itemsBeat(ctx, items, { start: 1.6, cap: 1, mode: 'pop' }) : null;
  const P = ctx.pos;
  return {
    dur: Math.max(chat.dur, beat ? beat.dur : 0),
    cam: () => ({ pos: V(P.x - 0.4, 2.3, P.z + 6.2), look: V(P.x - 1.5, 1.2, P.z), fov: 46 }),
    update(t, dt) { chat.update(t, dt); if (beat) beat.update(t, dt); },
  };
};

// ------------------------------------------------------------------ Jen's hole
function animLiquid(name, extra) { return new THREE.MeshLambertMaterial({ map: animTex(name), ...extra }); }
SCENES.jens_hole = (ctx) => {
  const P = ctx.pos.clone();
  const D = V(0.5, 0, 0.5);
  const cx = 0, cz = 0;
  const removed = [];
  for (let y = 0; y >= -3; y--) {
    const id = ctx.S.vox.get(cx, y, cz);
    if (id) { removed.push([cx, y, cz, id]); ctx.setVoxel(cx, y, cz, null); }
  }
  const rolled = roll(ctx.drop.actions);
  const msg = rolled.find((a) => a.t === 'message');
  const ent = rolled.find((a) => a.t === 'entity') || { id: 'Witch', display: 'Jen' };
  const witch = spawnMob(ctx, 'Witch', V(D.x, -2.9, D.z), { rotY: facing(1, 0.2), scale: 1.0 });
  witch.born = 1.2; witch.baseY = -2.9;
  const tag = nameTag(cleanName(ent.display || 'Jen'), '#ffe9a8');
  tag.position.set(D.x, -0.55, D.z);
  ctx.S.temp.add(tag);
  const peek = pointLight(ctx, 0xffe0b0, 3, 7, V(D.x, 0.2, D.z));
  let chat = false, laugh = false;
  return {
    dur: 6.4,
    cam: () => ({ pos: V(D.x + 2.8, 3.4, D.z + 4.4), look: V(D.x, -1.2, D.z), fov: 46 }),
    update(t, dt) {
      mobTick(witch, t, dt, { walk: 0, mute: true });
      witch.root.position.y = -2.9 + easeOut(clamp01((t - 1.6) / 1.6)) * 2.2;
      tag.position.y = witch.root.position.y + 2.5;
      if (!chat && t > 0.4) { chat = true; if (msg) ctx.chat(msg.text); }
      if (!laugh && t > 1.8) { laugh = true; sfx('mob.witch.laugh', { pos: D, volume: 1 }); sfx('mob.witch.idle', { pos: D, volume: 0.6 }); }
      ctx.steve.anim(t, dt, { walk: 0 });
    },
  };
};

// ------------------------------------------------------------------ the dud
SCENES.dud = (ctx) => dudBeat(ctx);

// The crash guard: only reached when a scene throws, so the page still ends.
SCENES.generic = (ctx) => {
  const O = ctx.dais.clone();
  const plq = plaque(ctx.drop);
  plq.position.set(O.x, 2.0, O.z + 1.0);
  plq.scale.setScalar(0.6);
  ctx.S.temp.add(plq);
  F.fail('generic fallback');
  return { dur: 3.0, cam: () => ({ pos: V(O.x + 0.4, 2.2, O.z + 4.4), look: V(O.x, 2.0, O.z), fov: 40 }), update(t) { plq.rotation.y = Math.sin(t * 1.4) * 0.3; } };
};

// ------------------------------------------------------------------ registry
export const SCENE_KEYS = Object.keys(SCENES);

// Scene reports for tools/site/vet_lucky.py: ?dump writes the latest one into the page.
function writeReport(rep) {
  try {
    let el = document.getElementById('qf-scene-report');
    if (!el) { el = document.createElement('script'); el.type = 'application/json'; el.id = 'qf-scene-report'; document.body.appendChild(el); }
    el.textContent = JSON.stringify(rep);
  } catch (e) { /* the report is optional */ }
}
function wrap(sc, key, ctx) {
  const rep = F.report();
  const update = sc.update;
  let lastT = 0;
  sc.update = (t, dt) => { lastT = t; if (update) update.call(sc, t, dt); if (F.DUMP) writeReport(sc.report()); };
  sc.report = () => F.finishReport(rep, sc.cam(lastT), ctx.S.camera.aspect, lastT, sc.dur);
  return sc;
}
export function buildScene(key, ctx) {
  F.resetFog(ctx);
  F.newReport(key, ctx.drop);
  let sc;
  try {
    const f = SCENES[key];
    if (!f) throw new Error('no scene ' + key);
    sc = f(ctx);
    if (!sc) throw new Error('scene returned nothing');
  } catch (e) {
    console.warn('scene', key, e);
    F.newReport(key, ctx.drop);
    F.fail(String(e && e.message || e));
    sc = SCENES.generic(ctx);
  }
  if (ctx.drop && ctx.drop.mood === 'deadly' && sc.dur && !sc._grand) { /* deadly scenes carry their own treatment */ }
  return wrap(sc, key, ctx);
}
export { MOOD_COLOR, puff, burst, blockCube as cube, pointLight, nameTag };
