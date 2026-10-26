// Beats: the reusable pieces a scene is made of (items landing on the dais, launched TNT,
// fireworks, a dud). Each returns { dur, update(t, dt) }; t is scene time, a beat may start late.
import * as THREE from 'three';
import { V, clamp01, easeOut, easeInOut, lerp, rnd, burst, puff, sfx, itemSprite, labelSprite, cleanName, watch, blockCube, facing, pointLight } from './fx.js';

// Slots for n items: one at the centre, a ring up to seven, two rings beyond.
export function ringSlots(n) {
  if (n <= 1) return [{ x: 0, z: 0, y: 0 }];
  const slots = [];
  const ring = (k, r, off, y) => { for (let i = 0; i < k; i++) { const a = off + (i / k) * Math.PI * 2; slots.push({ x: Math.cos(a) * r, z: Math.sin(a) * r, y }); } };
  if (n <= 7) ring(n, 0.55 + 0.12 * n, -Math.PI / 2, 0);
  else { const inner = Math.round(n * 0.38); ring(inner, 0.95, -Math.PI / 2, 0.12); ring(n - inner, 1.95, -Math.PI / 2 + 0.3, 0); }
  return slots;
}
export function itemsCam(O, R, extra = 0) {
  const d = 3.5 + R * 1.5 + extra;
  return () => ({ pos: V(O.x + 0.15, O.y + 1.25 + R * 0.55 + extra * 0.25, O.z + d), look: V(O.x, O.y + 0.45 - extra * 0.18, O.z), fov: 40 });
}

// Items pop out of the dais (or rain onto it) and settle in a ring at one world size, bobbing and
// spinning like dropped items. mode: 'pop' | 'rain'.
export function itemsBeat(ctx, items, o = {}) {
  const O = (o.origin || ctx.dais).clone();
  const list = items.slice(0, o.cap || 14);
  const n = list.length;
  const slots = ringSlots(n);
  const R = slots.reduce((m, s) => Math.max(m, Math.hypot(s.x, s.z)), 0);
  const rest = O.y + 0.55;
  const start = o.start ?? 0.4, step = o.step ?? (n > 8 ? 0.1 : 0.17);
  const fall = o.fall ?? 9;
  const sprites = list.map((it, i) => {
    const g = itemSprite(it);
    g.scale.setScalar(0.001);
    ctx.S.temp.add(g);
    if (n <= 3 && it.name && !/^random/i.test(it.name)) {
      const tag = labelSprite(cleanName(it.name), { color: it.ench ? '#d6b4ff' : '#ffffff', w: Math.min(1.5, 0.5 + cleanName(it.name).length * 0.06), cw: 512 });
      tag.position.set(0, 0.52, 0); g.add(tag);
    }
    const s = slots[i];
    return { g, it, i, s, t0: start + i * step, ph: rnd(0, 6.28), landed: false, tx: O.x + s.x, tz: O.z + s.z, ty: rest + s.y };
  });
  if (n) watch('items', () => V(O.x, rest, O.z), 1.2 + R);
  const mood = ctx.drop && ctx.drop.mood;
  let popped = 0, jp = false;
  return {
    dur: start + n * step + 2.4, R, O, cam: itemsCam(O, R, o.camExtra || 0),
    update(t, dt) {
      if (mood === 'jackpot' && !jp && t >= start) { jp = true; sfx('random.levelup', { volume: 0.7 }); }
      for (const s of sprites) {
        if (t < s.t0) continue;
        const age = t - s.t0;
        const sc = Math.min(1, age / 0.14);
        s.g.scale.setScalar(Math.max(0.001, sc));
        let y;
        if (o.mode === 'rain') {
          const h = Math.max(0, fall - 0.5 * 24 * age * age);
          s.g.position.x = s.tx; s.g.position.z = s.tz;
          y = s.ty + h;
          if (h <= 0 && !s.landed) { s.landed = true; s.lt = t; }
          if (s.landed) y += Math.abs(Math.sin((t - s.lt) * 9)) * 0.22 * Math.max(0, 1 - (t - s.lt) * 2.2);
        } else {
          const k = clamp01(age / 0.8);
          const e = easeOut(k);
          s.g.position.x = lerp(O.x, s.tx, e); s.g.position.z = lerp(O.z, s.tz, e);
          y = lerp(O.y + 0.6, s.ty, e) + Math.sin(k * Math.PI) * 1.15;
          if (k >= 1 && !s.landed) { s.landed = true; s.lt = t; }
        }
        if (s.landed && s.lt === t || (s.landed && !s.pop)) { s.pop = true; if (popped++ % 2 === 0 || n < 5) sfx('random.pop', { pos: { x: s.tx, y: s.ty, z: s.tz }, volume: 0.6, pitch: 0.9 + (s.i % 5) * 0.08 }); if (s.i === 0) burst(ctx, V(O.x, O.y + 0.5, O.z), { n: 24, colors: [0xffffff, 0xf2c14e], size: 0.14, speed: 1.6, up: 2.2, life: 0.8, additive: true, gravity: 4, noFloor: true }); }
        if (s.landed) y += Math.sin(t * 2.2 + s.ph) * 0.06;
        s.g.position.y = y;
        s.g.userData.spin.rotation.y = t * 2.6 + s.ph;
        if (s.g.userData.glint) s.g.userData.glint.material.opacity = 0.35 + 0.25 * Math.sin(t * 4 + s.ph);
      }
    },
  };
}

// TNT thrown from the dais toward Steve: arc, land, blink, blow.
export function tntBeat(ctx, N, o = {}) {
  const P = ctx.pos.clone();
  const from = o.from || V(0.5, 1.8, 0.5);
  const count = Math.min(N, o.cap || 34);
  const start = o.start ?? 0.4, gap = o.gap ?? Math.min(0.2, 3.2 / Math.max(1, count));
  const tn = [];
  for (let i = 0; i < count; i++) {
    const m = blockCube('minecraft:tnt', 0.5);
    m.material = m.material.clone(); m.material.userData.keep = false;
    m.visible = false; ctx.S.temp.add(m);
    const to = V(P.x + rnd(-2.6, 0.8), 0.25, P.z + rnd(-2.2, 2.2));
    tn.push({ m, to, t0: start + i * gap, fl: rnd(0.8, 1.1), fuse: rnd(0.8, 1.5), blew: false, ph: rnd(0, 1), fused: false });
  }
  let booms = 0;
  watch('tnt', () => V(P.x - 1.2, 1.2, P.z), 3);
  return {
    dur: start + count * gap + 1.1 + 1.5 + 0.8,
    update(t, dt) {
      for (const it of tn) {
        if (t < it.t0 || it.blew) continue;
        const a = t - it.t0;
        if (!it.fused) { it.fused = true; if (it.t0 - start < 0.01 || Math.floor((it.t0 - start) / gap) % 4 === 0) sfx('random.fuse', { pos: from, volume: 0.6 }); }
        it.m.visible = true;
        const k = clamp01(a / it.fl);
        it.m.position.set(lerp(from.x, it.to.x, k), lerp(from.y, it.to.y, k) + Math.sin(k * Math.PI) * 2.4, lerp(from.z, it.to.z, k));
        it.m.rotation.x = a * 5; it.m.rotation.z = a * 3;
        if (k >= 1) { it.m.rotation.set(0, 0, 0); it.m.position.y = 0.25 + Math.abs(Math.sin((a - it.fl) * 8)) * 0.18 * Math.max(0, 1 - (a - it.fl) * 3); }
        const on = Math.floor((a * 6 + it.ph) % 2) ? 0.4 : 0;
        it.m.material.emissive.setRGB(on, on * 0.9, on * 0.8);
        if (a > it.fl + it.fuse) {
          it.blew = true; it.m.visible = false;
          ctx.explode(it.m.position.clone().setY(0.6), 0.5);
          if (booms++ % 2 === 0) sfx('random.explode', { pos: it.m.position, volume: 0.8 });
          ctx.shake(0.14);
          if (Math.hypot(it.m.position.x - P.x, it.m.position.z - P.z) < 2.2) ctx.hurt(0.2);
        }
      }
    },
  };
}

// Rockets from behind the dais that burst into colour.
export function fireworksBeat(ctx, N, o = {}) {
  const O = (o.origin || ctx.dais).clone();
  const cols = [[0xff5a5a, 0xffb36b], [0xf2c14e, 0xffffff], [0x8fd3a0, 0x5ad2ff], [0x9d7bff, 0xff7be0], [0x5ad2ff, 0xffffff]];
  const k = Math.max(3, Math.min(8, Math.round(N / 8)));
  const start = o.start ?? 0.5;
  const shots = [];
  for (let i = 0; i < k; i++) shots.push({ t0: start + i * 0.55, x: O.x + (i - (k - 1) / 2) * 1.5 + rnd(-0.4, 0.4), h: 5.5 + rnd(0, 2.5), c: cols[i % cols.length], up: false, boom: false });
  return {
    dur: start + k * 0.55 + 1.6,
    update(t) {
      for (const s of shots) {
        if (t < s.t0) continue;
        if (!s.up) { s.up = true; sfx('fireworks.launch', { pos: { x: s.x, y: 2, z: O.z }, volume: 0.7 }); }
        const a = t - s.t0;
        if (a < 0.7) { burst(ctx, V(s.x, lerp(O.y, s.h, easeOut(a / 0.7)), O.z - 1.2), { n: 1, colors: [0xffd9a0], size: 0.2, speed: 0.1, up: -1, life: 0.35, additive: true, gravity: 0, noFloor: true }); }
        else if (!s.boom) {
          s.boom = true;
          burst(ctx, V(s.x, s.h, O.z - 1.2), { n: 70, colors: s.c, size: 0.16, speed: 3.4, up: 1.4, life: 1.5, additive: true, gravity: 2.4, noFloor: true });
          sfx(Math.random() < 0.5 ? 'fireworks.blast' : 'fireworks.largeBlast', { pos: { x: s.x, y: s.h, z: O.z }, volume: 0.8 });
          setTimeout && 0;
          ctx.shake(0.04);
        }
      }
    },
  };
}

// The dud: the block breaks, a sad grey puff, one fizz, Steve shrugs.
export function dudBeat(ctx, o = {}) {
  const O = ctx.dais.clone();
  const steve = ctx.steve;
  let puffed = false, said = false;
  watch('dais', () => V(O.x, O.y + 0.6, O.z), 1.4);
  return {
    dur: 4.4,
    cam: () => ({ pos: V(ctx.pos.x - 1.0, 1.9, ctx.pos.z + 5.4), look: V(ctx.pos.x - 1.3, 1.15, ctx.pos.z - 0.1), fov: 44 }),
    update(t, dt) {
      if (!puffed && t > 0.2) {
        puffed = true;
        puff(ctx, V(O.x, O.y + 0.4, O.z), { n: 22, size: 0.55, colors: [0x8c8698, 0x6c6878, 0x9d98a8], speed: 0.8, up: 0.6, gravity: -0.2, life: 1.8, noFloor: true });
        sfx('random.fizz', { pos: O, volume: 0.9 });
      }
      const k = easeInOut(clamp01((t - 0.9) / 0.6));
      const sh = Math.sin(clamp01((t - 1.5) / 1.4) * Math.PI * 3) * 0.18;
      steve.anim(t, dt, { walk: 0, armRaise: 0.55 * k * (t < 2.9 ? 1 : 1 - clamp01((t - 2.9) / 0.5)) });
      steve.root.rotation.y = lerp(Math.PI / 2, Math.PI * 0.86, k);
      if (steve.parts && steve.parts.head) steve.parts.head.rotation.z = sh;
      if (!said && t > 1.0) { said = true; ctx.say(o.say || 'The block drops nothing', { at: 'bottom' }); }
    },
  };
}
