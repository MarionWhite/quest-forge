// Wishing wells and temples. Each drop in the table is one hidden-block outcome of its own (the
// config lists every well and temple variant as its own line), so the drop that was rolled IS the
// rolled result: Steve throws in the coin the well gives him, the hidden lucky block breaks, and
// that outcome plays: gems fountain up, TNT is flung, blazes pour out, a lava rain falls, or
// nothing happens at all (a dud).
import * as THREE from 'three';
import * as F from './fx.js';
import { makeBlock } from './blocks.js';
import { structureScene } from './structures.js';
import { glowTexture } from './stage.js';
import { itemsBeat, tntBeat, fireworksBeat, dudBeat, itemsCam, ringSlots } from './beats.js';
import { mobsFrom } from './mobscenes.js';
const { V, clamp01, easeOut, easeIn, easeInOut, lerp, rnd, burst, puff, pointLight, sfx, roll, itemsOf, mobsOf, itemSprite, watch, sky, strikeBolt, blockCube } = F;

export const WELL_SCENES = {};

const luckyMaterial = () => makeBlock('lucky:lucky_block', 0, {}).obj.children[0].material;

// A beacon at a cell, its beam climbing into the sky.
function beacon(ctx, cell, start) {
  const r = makeBlock('minecraft:beacon', 0, {});
  const h = new THREE.Group();
  r.obj.position.set(-0.5, 0, -0.5); h.add(r.obj);
  h.position.set(cell.x + 0.5, cell.y, cell.z + 0.5); h.scale.setScalar(0.001);
  ctx.S.temp.add(h);
  const mat = new THREE.MeshBasicMaterial({ map: glowTexture('rgba(190,240,255,1)'), color: 0xbff4ff, transparent: true, opacity: 0, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide, fog: false });
  const b1 = new THREE.Mesh(new THREE.PlaneGeometry(0.9, 60), mat); b1.position.set(cell.x + 0.5, cell.y + 31, cell.z + 0.5);
  const b2 = b1.clone(); b2.rotation.y = Math.PI / 2;
  ctx.S.temp.add(b1, b2);
  let on = false;
  return {
    update(t) {
      if (t < start) return;
      if (!on) { on = true; sfx('random.levelup', { pos: cell, volume: 0.8, pitch: 0.7 }); }
      h.scale.setScalar(Math.max(0.001, easeOut((t - start) / 0.4)));
      mat.opacity = 0.75 * clamp01((t - start - 0.2) / 0.8) * (0.85 + 0.15 * Math.sin(t * 4));
    },
  };
}

// Falling blocks (a lava rain, a diamond block) land around Steve.
function fallingRain(ctx, blocks, start, spread) {
  const P = ctx.pos;
  const list = blocks.slice(0, 26).map((b, i) => {
    const r = makeBlock(b.id, b.meta || 0, {});
    const h = new THREE.Group(); r.obj.position.set(-0.5, 0, -0.5); h.add(r.obj);
    const x = P.x - 0.5 + rnd(-spread, spread), z = P.z + rnd(-spread, spread);
    h.position.set(x, 18, z); h.visible = false; ctx.S.temp.add(h);
    return { h, x, z, t0: start + i * 0.12, landed: false, id: b.id };
  });
  return {
    dur: start + list.length * 0.12 + 1.8,
    update(t) {
      for (const it of list) {
        if (t < it.t0 || it.landed) continue;
        it.h.visible = true;
        const s = t - it.t0, y = 18 - 0.5 * 26 * s * s;
        it.h.position.y = Math.max(0, y);
        if (y <= 0) {
          it.landed = true;
          const lava = /lava/.test(it.id);
          burst(ctx, V(it.x, 0.5, it.z), { n: 14, colors: lava ? [0xff7a2a, 0xffd27a, 0xff3a10] : [0xb8b0c4], size: 0.25, speed: 1.8, up: 2.2, life: 0.9, additive: lava, gravity: 5 });
          ctx.shake(0.08);
          sfx(lava ? 'liquid.lavapop' : 'dig.stone', { pos: { x: it.x, y: 0, z: it.z }, volume: 0.6 });
        }
      }
    },
  };
}

// The outcome of a hidden block: what the inner actions do, in the scene's world.
function innerBeat(ctx, inner, o) {
  const rolled = roll(inner);
  const items = itemsOf(rolled);
  const tnt = rolled.find((a) => a.t === 'tnt');
  const fw = rolled.find((a) => a.t === 'fireworks');
  const mobs = mobsOf(rolled, 20);
  const falls = rolled.filter((a) => a.t === 'falling').flatMap((a) => a.blocks || []);
  const blocks = rolled.filter((a) => a.t === 'block').flatMap((a) => a.blocks || []);
  const msg = rolled.find((a) => a.t === 'message');
  const start = o.start;
  const parts = [];
  let kind = 'dud';
  let cam = null;
  const P = ctx.pos;
  const wide = () => ({ pos: V(P.x - 0.8, 3.2, P.z + 9.8), look: V(P.x - 1.4, 2.0, P.z - 0.2), fov: 48 });
  if (blocks.some((b) => /beacon/.test(b.id))) parts.push(beacon(ctx, o.beaconCell, start + 0.2));
  if (items.length) {
    const b = itemsBeat(ctx, items, { origin: o.ring, start: start + 0.5, mode: o.mode || 'pop', fall: o.fall, cap: 12, camExtra: o.camExtra || 0 });
    parts.push(b); kind = 'items'; cam = o.itemsCam || b.cam;
    parts.dur = Math.max(parts.dur || 0, b.dur);
  }
  if (fw) { const f = fireworksBeat(ctx, fw.n, { origin: o.ring, start: start + 0.3 }); parts.push(f); parts.dur = Math.max(parts.dur || 0, f.dur); if (kind === 'dud') kind = 'items'; }
  if (tnt) {
    const b = tntBeat(ctx, tnt.n, { from: o.from, start: start + 0.4 });
    parts.push(b); kind = 'tnt'; cam = wide;
    parts.dur = Math.max(parts.dur || 0, b.dur);
  }
  if (mobs.length) {
    const g = mobsFrom(ctx, mobs, o.from, start + 0.3);
    parts.push(g); kind = 'mobs'; cam = () => { const c = g.cam(); return c; };
    parts.dur = Math.max(parts.dur || 0, g.dur);
  }
  if (falls.length) {
    const f = fallingRain(ctx, falls, start + 0.5, 3.4);
    parts.push(f); kind = 'rain'; cam = wide;
    parts.dur = Math.max(parts.dur || 0, f.dur);
  }
  if (kind === 'dud') { const d = dudBeat(ctx, { say: 'The coin is wasted. Nothing happens.' }); parts.push({ update: (t, dt) => d.update(t - start, dt), dur: start + d.dur }); parts.dur = start + d.dur; cam = wide; }
  return { kind, parts, cam: cam || wide, msg, dur: (parts.dur || start + 3) + 1.4, update(t, dt) { for (const p of parts) p.update(t, dt); } };
}

function breakHidden(ctx, center, t0) {
  const LM = luckyMaterial();
  const frags = [];
  for (let i = 0; i < 26; i++) {
    const m = new THREE.Mesh(new THREE.BoxGeometry(0.2, 0.2, 0.2), LM);
    m.visible = false; ctx.S.temp.add(m);
    frags.push({ m, v: V(rnd(-2.4, 2.4), rnd(2, 5.5), rnd(-2.4, 2.4)) });
  }
  const r = makeBlock('lucky:lucky_block', 0, {});
  const h = new THREE.Group(); r.obj.position.set(-0.5, 0, -0.5); h.add(r.obj); h.visible = false; ctx.S.temp.add(h);
  const glow = pointLight(ctx, 0xffd9a0, 0, 8, center.clone());
  let up = false, shattered = false;
  return {
    breakAt: t0 + 1.4,
    update(t, dt) {
      if (t < t0) return;
      const a = t - t0;
      if (!up) { up = true; sfx('random.chestopen', { pos: center, volume: 0.5, pitch: 0.6 }); sfx('ambient.cave.cave', { volume: 0.4 }); }
      if (a < 1.4) {
        h.visible = true;
        h.position.set(center.x, center.y - 1 + easeOut(a / 1.1) * 1.6, center.z);
        h.rotation.y = a * 2.2; h.rotation.z = Math.sin(a * 22) * 0.06 * clamp01(a - 0.6);
        glow.intensity = 5 * clamp01(a / 1.0);
        if (a > 0.7) ctx.shake(0.05);
      } else if (!shattered) {
        shattered = true; h.visible = false;
        ctx.shake(0.3); ctx.flashScreen('#ffe2b8', 0.55, 0.45);
        sfx('dig.glass', { pos: center, volume: 0.9 }); sfx('random.pop', { pos: center, volume: 0.8, pitch: 0.7 });
        for (const f of frags) { f.m.visible = true; f.m.position.copy(center); }
        glow.intensity = 14;
      }
      if (shattered) {
        if (t - t0 > 1.4 + 2.4) for (const f of frags) f.m.visible = false;
        glow.intensity = Math.max(0, glow.intensity - dt * 20);
        for (const f of frags) { f.v.y -= 16 * dt; f.m.position.addScaledVector(f.v, dt); if (f.m.position.y < 0.1) { f.m.position.y = 0.1; f.v.y *= -0.3; f.v.x *= 0.6; f.v.z *= 0.6; } }
      }
    },
  };
}

// ------------------------------------------------------------------ the wishing well
WELL_SCENES.wishing_well = (ctx) => {
  const rolled = roll(ctx.drop.actions);
  const then = rolled.find((a) => a.t === 'then');
  const inner = then ? then.actions : [];
  const give = rolled.find((a) => a.t === 'command' && a.gives);
  const intro = rolled.find((a) => a.t === 'message');
  const P = ctx.pos;
  const steve = ctx.steve;
  const sp = structureScene(ctx, 'wishing_well', { x: 0, y: 1, z: 0 }, { start: 0.3, span: 2.4 });
  const C = V(0.5, 2.2, 0.5);
  // the coin the well gives: a gold nugget, shown at half the size of a dropped item stack
  const coin = itemSprite({ icon: (give && give.gives.icon) || null, id: 'gold_nugget' }, 0.4);
  coin.visible = false; ctx.S.temp.add(coin);
  const T_THROW = 3.4, T_FLIGHT = 0.9;
  const hidden = breakHidden(ctx, V(0.5, 1.5, 0.5), T_THROW + T_FLIGHT + 0.6);
  const out = innerBeat(ctx, inner, { start: hidden.breakAt + 0.2, ring: V(0.5, 5.3, 0.5), beaconCell: V(0, 4, 0), from: V(0.5, 3.4, 0.5), mode: 'pop', camExtra: 3.0, itemsCam: () => ({ pos: V(4.2, 4.6, 8.2), look: V(0.9, 4.0, 0.5), fov: 46 }) });
  watch('well', () => V(0.5, 3, 0.5), 5);
  let chat1 = false, chat2 = false, splashed = false, said = false, tossed = false;
  const tEnd = out.dur;
  return {
    dur: tEnd + 1.0,
    cam: (t) => {
      if (t < hidden.breakAt + 0.2) return { pos: V(4.6, 3.3, 6.9), look: V(1.0, 2.4, 0.5), fov: 44 };
      const c = out.cam();
      return c;
    },
    update(t, dt) {
      if (sp) sp.update(t);
      if (!chat1 && t > 1.8) { chat1 = true; if (intro) ctx.chat(intro.text); }
      steve.anim(t, dt, { walk: 0 });
      // the throw: the arm swings up and over
      const arm = steve.parts && (steve.parts.rightArm || steve.parts.rArm);
      if (arm) {
        const a = clamp01((t - (T_THROW - 0.5)) / 0.5), b = clamp01((t - T_THROW) / 0.35);
        arm.rotation.x = lerp(0, -2.5, easeOut(a)) + lerp(0, 1.6, easeIn(b));
      }
      if (t >= T_THROW) {
        const k = clamp01((t - T_THROW) / T_FLIGHT);
        coin.visible = k < 1;
        coin.position.set(lerp(3.0, C.x, k), lerp(1.5, C.y, k) + Math.sin(k * Math.PI) * 2.0, lerp(0.5, C.z, k));
        coin.userData.spin.rotation.y = t * 14;
        if (!tossed) { tossed = true; sfx('random.bow', { pos: P, volume: 0.35, pitch: 1.6 }); }
        if (k >= 1 && !splashed) {
          splashed = true;
          burst(ctx, V(C.x, 1.8, C.z), { n: 36, colors: [0x9ad7ff, 0xffffff, 0x6fb8ff], size: 0.14, speed: 1.4, up: 3, life: 1.0, additive: true, gravity: 8, noFloor: true });
          sfx('liquid.splash', { pos: C, volume: 0.8 }); sfx('random.orb', { pos: C, volume: 0.7, pitch: 1.8 });
          ctx.shake(0.1);
        }
      }
      hidden.update(t, dt);
      if (t >= hidden.breakAt && !chat2) { chat2 = true; if (out.msg) ctx.chat(out.msg.text); }
      out.update(t, dt);
      if (!said && t > hidden.breakAt + 0.5) { said = true; ctx.say(ctx.drop.title.replace(/^Wishing well, ?/, '').replace(/^./, (c) => c.toUpperCase()) || 'The wish', { at: 'bottom' }); }
    },
  };
};

// ------------------------------------------------------------------ temples
// A temple holds a hidden lucky block. Sky: it hangs 50 blocks up; earth and hell: in the ground.
function templeScene(ctx) {
  const rolled = roll(ctx.drop.actions);
  const then = rolled.find((a) => a.t === 'then');
  const inner = then ? then.actions : [];
  const msg = rolled.find((a) => a.t === 'message');
  const timeA = rolled.find((a) => a.t === 'time');
  const blocks = rolled.filter((a) => a.t === 'block').flatMap((a) => a.blocks || []).filter((b) => b.id !== 'minecraft:air');
  const sky_ = blocks.some((b) => (b.dy || 0) >= 30);
  const hell = !sky_ && !!timeA;
  const O = V(0, 1, 0);
  const cells = blocks.slice(0, 90).map((b, i) => ({ b, c: { x: b.dx || 0, y: b.dy || 0, z: b.dz || 0 }, i }));
  const lucky = cells.find((x) => /lucky/.test(x.b.id));
  const LY = lucky ? lucky.c.y : 0;
  // underground cells are carved out so they show
  if (!sky_) for (const { c } of cells) { const wy = 1 + c.y; if (wy >= -8 && wy < 1) ctx.setVoxel(c.x, wy, c.z, null); }
  const objs = cells.map(({ b, c, i }) => {
    const r = makeBlock(b.id, b.meta || 0, {});
    const h = new THREE.Group(); r.obj.position.set(-0.5, 0, -0.5); h.add(r.obj);
    const wy = O.y + c.y;
    h.position.set(c.x + 0.5, sky_ ? wy + 18 : wy, c.z + 0.5);
    if (!sky_) h.scale.setScalar(0.001);
    ctx.S.temp.add(h);
    return { h, wy, x: c.x + 0.5, z: c.z + 0.5, t0: 0.5 + (sky_ ? (c.y - 50) * 0.1 + Math.hypot(c.x, c.z) * 0.12 : i / cells.length * 2.2), landed: false, lucky: /lucky/.test(b.id), id: b.id };
  });
  const luckyObj = objs.find((o) => o.lucky);
  const center = luckyObj ? V(luckyObj.x, luckyObj.wy + 0.5, luckyObj.z) : V(0.5, 1.5, 0.5);
  const T_BUILD = sky_ ? 4.0 : 3.0;
  const hidden = breakHidden(ctx, center, T_BUILD + 0.8);
  const P = ctx.pos;
  const ringO = V(0.5, 2.3, 0.5);
  const out = innerBeat(ctx, inner, { start: hidden.breakAt + 0.2, ring: ringO, beaconCell: V(0, 1, 0), from: sky_ ? V(center.x, center.y, center.z) : V(0.5, 1.5, 0.5), mode: sky_ ? 'rain' : 'pop', fall: sky_ ? 14 : 9 });
  const tBreak = hidden.breakAt + 0.2;
  let chat = false, chat2 = false, glowL = null, said = false, snd = 0;
  if (hell) glowL = pointLight(ctx, 0xff5a1a, 4, 12, V(0.5, -1, 0.5));
  watch('temple', () => (sky_ ? V(0.5, 52, 0.5) : V(0.5, 0.5, 0.5)), 6, false);
  watch('dais', () => V(0.5, 1.5, 0.5), 2, false);
  const down = (t) => {
    // the ground temple: look into the cutaway from above, then back to the dais
    const k = easeInOut(clamp01((t - tBreak + 0.6) / 1.4));
    const a = { pos: V(4.6, 6.4, 7.2), look: V(0.5, LY < 0 ? 0.0 : 1.5, 0.5), fov: 48 };
    const b = out.cam();
    return { pos: a.pos.clone().lerp(b.pos, k), look: a.look.clone().lerp(b.look, k), fov: lerp(a.fov, b.fov, k) };
  };
  return {
    dur: out.dur + 1.0,
    cam: (t) => {
      if (!sky_) return down(t);
      // the sky temple: tilt up the 50 blocks to the temple, hold on the hidden block, then drop with the rain
      const up = easeInOut(clamp01(t / 2.4));
      const fall = easeInOut(clamp01((t - tBreak - 0.2) / 1.8));
      const A = { pos: V(5.0, lerp(3.0, 40, up), lerp(7.5, 16, up)), look: V(0.5, lerp(3, 50, up), 0.5), fov: lerp(46, 52, up) };
      const B = out.cam();
      return { pos: A.pos.clone().lerp(B.pos, fall), look: A.look.clone().lerp(B.look, fall), fov: lerp(A.fov, B.fov, fall) };
    },
    update(t, dt) {
      if (!chat && t > 0.3) { chat = true; if (msg) ctx.chat(msg.text); }
      for (const o of objs) {
        if (t < o.t0) continue;
        if (sky_) {
          const s = t - o.t0;
          const y = o.wy + Math.max(0, 18 - 0.5 * 26 * s * s);
          o.h.position.y = y;
          if (y <= o.wy && !o.landed) { o.landed = true; ctx.shake(0.03); if (snd++ % 3 === 0) sfx('dig.stone', { pos: { x: o.x, y: o.wy, z: o.z }, volume: 0.5 }); }
        } else {
          const k = clamp01((t - o.t0) / 0.3);
          o.h.scale.setScalar(0.001 + easeOut(k) * (1 + 0.1 * Math.sin(k * Math.PI)));
          if (k >= 1 && !o.landed) { o.landed = true; if (snd++ % 4 === 0) sfx('dig.stone', { pos: { x: o.x, y: o.wy, z: o.z }, volume: 0.6 }); }
        }
      }
      if (t > T_BUILD && sky_) { sky(ctx, easeInOut(clamp01((t - T_BUILD) / 1.5)) * 0.5, { night: 0.5, fog: 0 }); }
      if (hell) { const k = easeInOut(clamp01(t / 2)); sky(ctx, k, { night: 1, near: 14, far: 46, fog: k * 0.6 }); ctx.tint(0xff3a10, 0.1 * k); if (glowL) glowL.intensity = 4 + Math.sin(t * 7) * 0.8; }
      if (luckyObj && t >= T_BUILD + 0.8) luckyObj.h.visible = false;
      hidden.update(t, dt);
      if (t >= hidden.breakAt && !chat2) { chat2 = true; if (out.msg) ctx.chat(out.msg.text); }
      out.update(t, dt);
      ctx.steve.anim(t, dt, { walk: 0 });
      if (!said && t > tBreak + 0.6) { said = true; ctx.say(ctx.drop.title, { at: 'bottom' }); }
    },
  };
}
WELL_SCENES.sky_temple = templeScene;
WELL_SCENES.ground_temple = templeScene;
