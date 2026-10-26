// Mob scenes: a few mobs, a horde, riding stacks, pets, villagers, and the grand entrances of the
// big ones (Mobzilla, the Wither, Giants, Mothras, Hammerhead, Cephadrome, the worms, the robots,
// the dragons): the sky darkens, lightning strikes, the ground shakes, fog rolls in, and the
// creature arrives with its own roar. Steve is at ctx.pos and faces -x; mobs arrive from the fog
// on the -x side and the camera looks from +z, so the mobs are in front of Steve and in view.
import * as THREE from 'three';
import * as F from './fx.js';
import { glowTexture } from './stage.js';
import { nav } from './nav.js';
import { dudBeat } from './beats.js';
import { MOB_FEATURES } from '../lib/mc/mobs.js';
// the drop's own gear for a mob (King Bob's armour and so on), only where the library draws it
const gear = (e) => (MOB_FEATURES && MOB_FEATURES.equipment && e && e.equipment && e.equipment.length ? { equipment: e.equipment } : {});
const { V, clamp01, easeOut, easeIn, easeInOut, lerp, rnd, pick, burst, puff, pointLight, sfx, mobSay, roll, mobsOf, spawnMob, mobTick, nameTag, cleanName, heartSprite, facing, watch, strikeBolt, sky } = F;

export const MOB_SCENES = {};
// Mobs that come out of a point (the wells and temples): the same arrival, no camera of its own.
export function mobsFrom(ctx, list, from, start) { return groupScene(ctx, list.some((e) => isBig(e.id)) ? list : list, { from, start, inner: true }); }

// ------------------------------------------------------------------ what each mob is like
const STYLE = {
  Silverfish: 'pour', CaveSpider: 'pour', 'Brown Ant': 'pour', 'Red Ant': 'pour', 'Rainbow Ant': 'pour', 'Unstable Ant': 'pour', Termite: 'pour', 'Black Ant': 'pour',
  Bat: 'swarm', Bee: 'swarm', Ghast: 'hover', Blaze: 'hover', Slime: 'hop', LavaSlime: 'hop', luckyegg: 'egg', Coin: 'coin',
};
// The big ones. h is the target world height, night how dark the sky goes, bolts the strike times,
// fog [near, far], roar the sounds played when it arrives, how it enters, what it steps with.
const BIG = {
  Mobzilla: { h: 12, night: 1, bolts: [0.9, 2.3, 4.4, 5.6, 6.8], fog: [18, 56], roar: ['orespawn:godzilla_living', 'orespawn:roar3'], enter: 'walk', step: ['dig.stone', 0.45], dist: 9, tag: 'Mobzilla arrives' },
  WitherBoss: { h: 4.8, night: 1, bolts: [1.0, 2.6, 4.8], fog: [10, 44], roar: ['mob.wither.spawn'], idle: 'mob.wither.idle', enter: 'rise', fly: 3.0, dist: 7, skulls: true, tag: 'The Wither spawns' },
  Giant: { h: 10.8, night: 0.85, bolts: [1.3, 4.3], fog: [16, 52], roar: ['mob.zombie.say', 'mob.zombie.hurt'], roarPitch: 0.45, enter: 'walk', step: ['mob.zombie.step', 0.4], dist: 8, tag: 'A giant approaches' },
  Hammerhead: { h: 4.6, night: 0.7, bolts: [1.4, 4.2], fog: [12, 46], roar: ['orespawn:roar1'], enter: 'walk', step: ['dig.gravel', 0.7], dist: 6, tag: 'A Hammerhead arrives' },
  Cephadrome: { h: 9, night: 0.9, bolts: [1.0, 3.0, 5.0], fog: [14, 54], roar: ['orespawn:roar4'], enter: 'fly', fly: 8.5, dist: 10, tag: 'A Cephadrome swoops in' },
  'Large Worm': { h: 6, night: 0.7, bolts: [1.2, 3.6], fog: [12, 46], roar: ['orespawn:roar5'], enter: 'rise', dist: 5.5, dirt: true, tag: 'A Large Worm bursts out of the ground' },
  CaterKiller: { h: 4.0, night: 0.7, bolts: [1.2, 3.8], fog: [12, 46], roar: ['orespawn:roar6'], enter: 'rise', dist: 5.5, dirt: true, tag: 'A CaterKiller bursts out of the ground' },
  Mothra: { h: 4.2, night: 0.8, bolts: [1.4, 3.8], fog: [14, 50], roar: ['orespawn:MothraWings1', 'orespawn:roar2'], enter: 'fly', fly: 5.5, dist: 7, tag: 'Mothra arrives' },
  Brutalfly: { h: 3.6, night: 0.8, bolts: [1.4, 3.8], fog: [14, 50], roar: ['orespawn:roar2'], enter: 'fly', fly: 4.5, dist: 7, tag: 'A Brutalfly arrives' },
  'Robo-Pounder': { h: 5.0, night: 0.5, bolts: [2.0], fog: [14, 50], roar: ['mob.irongolem.hit'], enter: 'walk', step: ['mob.irongolem.walk', 0.8], dist: 6, tag: 'Robots march in' },
  'Robo-Gunner': { h: 4.2, night: 0.5, bolts: [2.0], fog: [14, 50], roar: ['random.anvil_land'], enter: 'walk', step: ['mob.irongolem.walk', 0.7], dist: 6, tag: 'Robots march in' },
  'Robo-Warrior': { h: 4.4, night: 0.5, bolts: [2.0], fog: [14, 50], roar: ['mob.irongolem.hit'], enter: 'walk', step: ['mob.irongolem.walk', 0.75], dist: 6, tag: 'Robots march in' },
  Dragon: { h: 3.4, night: 0.7, bolts: [1.6, 3.8], fog: [14, 52], roar: ['mob.enderdragon.growl', 'orespawn:roar4'], enter: 'fly', fly: 6, dist: 7, tag: 'Dragons arrive' },
};
const isBig = (id) => !!BIG[id];


// ------------------------------------------------------------------ walking around the camp
// Ground mobs follow a route planned around every prop (nav.js), stand on the ground as it really is
// (a one-block rise is a ramp) and are pushed apart so no two share a spot. Flyers are exempt. Big mobs
// step over soft things (leaves, benches, fences, the pond) and go round the solid ones.
const SOFT = ['leaf', 'low', 'fence', 'water'];
// what a mob of this height steps over: fences, benches and the pond from 2.4 m up, the canopy from 4.5 m
const softFor = (wh) => new Set(wh > 4.5 ? SOFT : wh >= 2.4 ? ['low', 'fence', 'water'] : []);
const FLYING = new Set(['hover', 'swarm', 'egg', 'coin']);
// The real footprint: the model's widest horizontal extent at its scene scale (width times scale), halved.
function footRadius(m) {
  if (m.rad) return m.rad;
  let r = null;
  if (m.root && m.base) {
    try {
      const keep = m.root.scale.clone();
      m.root.scale.copy(m.base);
      m.root.updateMatrixWorld(true);
      const bx = new THREE.Box3().setFromObject(m.root);
      m.root.scale.copy(keep); m.root.updateMatrixWorld(true);
      const hx = (bx.max.x - bx.min.x) / 2, hz = (bx.max.z - bx.min.z) / 2;
      if (isFinite(hx) && isFinite(hz) && hx > 0) r = Math.max(hx, hz) * 0.85;
    } catch (e) { r = null; }
  }
  if (r === null) r = m.wh * 0.3;
  m.rad = r;
  return r;
}
function mobRadius(m) { return m.footR || Math.max(0.25, Math.min(3.6, footRadius(m))); }
function routeFor(m, from, to) {
  if (m.fly || FLYING.has(m.style)) return null;
  const big = m.wh > 4.5;
  const ign = softFor(m.wh);
  if (m.style === 'pour') ign.add('dais');
  // an unlucky spawn point inside a hill or a tree starts at the nearest open ground; a footprint too wide for
  // the gaps between props is tried at 100%, 85% and 70% before giving up
  let r = mobRadius(m), pts = null, full = null;
  for (const k of [1, 0.85, 0.7]) {
    r = mobRadius(m) * k;
    const sf = nav.nearestFree(from.x, from.z, r, ign, 12);
    const f0 = { x: sf.x, z: sf.z };
    pts = nav.path(f0.x, f0.z, to.x, to.z, r, { ign, step: 0.5 });
    full = [[f0.x, f0.z], ...pts];
    if (pts.ok !== false) break;
  }
  const cum = [0];
  for (let i = 1; i < full.length; i++) cum.push(cum[i - 1] + Math.hypot(full[i][0] - full[i - 1][0], full[i][1] - full[i - 1][1]));
  if (pts.ok === false) { nav.stats.noroute = (nav.stats.noroute || []); nav.stats.noroute.push([+from.x.toFixed(1), +from.z.toFixed(1), +to.x.toFixed(1), +to.z.toFixed(1), +r.toFixed(2)]); }
  nav.stats.routes = (nav.stats.routes || []); if (nav.stats.routes.length < 8) nav.stats.routes.push({ r: +r.toFixed(2), pts: full.map((p) => [+p[0].toFixed(1), +p[1].toFixed(1)]) });
  return { pts: full, cum, len: cum[cum.length - 1] || 0.0001, r, ign, ok: pts.ok !== false };
}
function posAt(rt, k) {
  const d = clamp01(k) * rt.len;
  let i = 1;
  while (i < rt.cum.length - 1 && rt.cum[i] < d) i++;
  const a = rt.pts[i - 1], b = rt.pts[i] || a, seg = (rt.cum[i] - rt.cum[i - 1]) || 1;
  const u = clamp01((d - rt.cum[i - 1]) / seg);
  return [a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u];
}
// the nearest free spot for a ground mob's goal
function freeGoal(m, g) {
  if (m.fly || FLYING.has(m.style)) return g;
  const ign = softFor(m.wh);
  const f = nav.nearestFree(g.x, g.z, mobRadius(m), ign, 8);
  return V(f.x, g.y, f.z);
}
// push overlapping ground mobs apart, then back out of any prop the push led into
function separate(list) {
  const g = list.filter((m) => m.route && m.root.visible !== false && m.born !== null);
  for (let i = 0; i < g.length; i++) for (let j = i + 1; j < g.length; j++) {
    const a = g[i], b2 = g[j];
    const dx = b2.root.position.x - a.root.position.x, dz = b2.root.position.z - a.root.position.z;
    const need = (a.route.r + b2.route.r) * 0.85, d = Math.hypot(dx, dz);
    if (d >= need) continue;
    const nx = d > 0.001 ? dx / d : 1, nz = d > 0.001 ? dz / d : 0, push = (need - d) / 2;
    a.off.x -= nx * push; a.off.z -= nz * push; b2.off.x += nx * push; b2.off.z += nz * push;
    a.root.position.x -= nx * push; a.root.position.z -= nz * push; b2.root.position.x += nx * push; b2.root.position.z += nz * push;
  }
  for (const m of g) {
    const f = nav.resolve(m.root.position.x, m.root.position.z, m.route.r, m.route.ign);
    m.root.position.x = f.x; m.root.position.z = f.z;
    nav.track('mob', f.x, f.z, m.route.r * 0.9, m.route.ign, m.id);
  }
}
// place a mob on its route at progress k, on the ground
function stepRoute(m, k) {
  if (!m.route) return false;
  const [x, z] = posAt(m.route, k);
  m.root.position.x = x + m.off.x; m.root.position.z = z + m.off.z;
  return true;
}

// ------------------------------------------------------------------ small helpers
function fitSmall(m) {
  if (m.wh < 0.7) { const k = Math.min(4, 0.7 / m.wh); m.base.multiplyScalar(k); m.wh = 0.7; }
}
function rainbow(m, t, ph) {
  const c = new THREE.Color().setHSL(((t * 0.25 + ph) % 1 + 1) % 1, 0.9, 0.62);
  m.root.traverse((o) => { if (o.isMesh && o.material && o.material.color) { o.material = o.material.userData.rb ? o.material : (() => { const c2 = o.material.clone(); c2.userData.rb = true; return c2; })(); o.material.color.copy(c); } });
}
function tagFor(ctx, m, e, color = '#ffffff') {
  if (!e.display) return null;
  const name = cleanName(e.display);
  if (!name || /^\s*$/.test(name)) return null;
  const tag = nameTag(name, color);
  tag.scale.set(1.5, 0.255, 1);
  m.root.add(tag);
  tag.scale.multiplyScalar(Math.max(1, m.wh / 2.2) / Math.max(0.0001, m.base.x));
  tag.position.y = (m.wh + 0.45) / Math.max(0.0001, m.base.x);
  return tag;
}
function applyFlip(m, e) {
  if (!e.upsideDown) return;
  m.root.rotation.z = Math.PI;
  m.flipY = m.wh;
  if (!m.fly) m.baseY += m.wh;
}
// A fireball from a ghast or a skull from the wither flying at Steve, then a blast.
function projectile(ctx, from, to, color, dur, cb) {
  const m = new THREE.Mesh(new THREE.SphereGeometry(0.42, 12, 8), new THREE.MeshBasicMaterial({ color, fog: false }));
  const g = new THREE.Mesh(new THREE.PlaneGeometry(2.2, 2.2), new THREE.MeshBasicMaterial({ map: glowTexture(), color, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, fog: false }));
  m.add(g);
  ctx.S.temp.add(m);
  const l = pointLight(ctx, color, 6, 9, from.clone());
  let t = 0;
  ctx.fx.push({
    update(dt) {
      t += dt; const k = clamp01(t / dur);
      m.position.lerpVectors(from, to, k); l.position.copy(m.position);
      g.quaternion.copy(ctx.S.camera.quaternion);
      if (k >= 1) { ctx.S.temp.remove(m); ctx.S.temp.remove(l); if (cb) cb(); return true; }
      return false;
    },
  });
}

// ------------------------------------------------------------------ groups: a few, a horde, pets
function arcLayout(n, P, size, small, wide) {
  const perRow = wide ? 8 : 6;
  const rows = Math.max(1, Math.ceil(n / perRow));
  const rmin = small ? 1.7 : 2.4 + size * 0.5;
  const gap = small ? 0.9 : 1.2 + size * 0.35;
  const phi = n <= 4 ? 0.6 : 1.0;
  const out = [];
  for (let i = 0; i < n; i++) {
    const row = i % rows, idx = Math.floor(i / rows), inRow = Math.ceil((n - row) / rows);
    const th = Math.PI + (inRow === 1 ? 0 : (idx / (inRow - 1) - 0.5) * 2 * phi) + rnd(-0.05, 0.05);
    const r = rmin + row * gap + rnd(-0.15, 0.15);
    out.push({ dir: V(Math.cos(th), 0, Math.sin(th)), r });
  }
  return { slots: out, rmax: rmin + (rows - 1) * gap };
}

function groupScene(ctx, list, o = {}) {
  const P = ctx.pos.clone();
  const O = ctx.dais.clone();
  const n = list.length;
  const mobs = list.map((e) => {
    const m = spawnMob(ctx, e.id, V(0, 0, 0), { quiet: true, main: false, ...gear(e) });
    fitSmall(m);
    m.e = e; m.style = STYLE[e.id] || 'walk';
    return m;
  });
  const size = Math.max(0.5, ...mobs.map((m) => m.wh));
  const style = mobs[0] ? mobs[0].style : 'walk';
  const small = size < 1.1 || style === 'pour';
  const { slots, rmax } = arcLayout(n, P, size, small, n > 12);
  const fly = style === 'hover' || style === 'swarm';
  const stagger = Math.min(0.4, 2.4 / Math.max(1, n));
  mobs.forEach((m, i) => {
    const s = slots[i];
    const goal = freeGoal(m, V(P.x + s.dir.x * s.r, 0, P.z + s.dir.z * s.r));
    let spawn;
    if (o.from) spawn = V(o.from.x + rnd(-0.3, 0.3), o.from.y, o.from.z + rnd(-0.3, 0.3));
    else if (m.style === 'pour' || m.style === 'egg' || m.style === 'coin') spawn = V(O.x + rnd(-0.3, 0.3), 1.0, O.z + rnd(-0.3, 0.3));
    else spawn = V(P.x + s.dir.x * (s.r + rnd(11, 16)), 0, P.z + s.dir.z * (s.r + rnd(11, 16)));
    m.spawn = spawn; m.goal = goal;
    m.off = { x: 0, z: 0 };
    m.born = (o.start || 0) + 0.4 + i * stagger;
    m.T = m.style === 'pour' || o.from ? (o.from ? 1.8 : 1.1) : 2.8 + spawn.distanceTo(goal) * 0.06;
    m.root.rotation.y = facing(goal.x - spawn.x, goal.z - spawn.z);
    m.root.position.copy(spawn);
    m.baseY = spawn.y;
    if (m.style === 'hover') m.fly = (FLYH[m.id] || 3.6) * (0.8 + 0.5 * ((i * 7) % 5) / 4);
    if (m.style === 'swarm') m.fly = 1.2 + rnd(0, 3.2);
    m.orbit = { r: rnd(1.2, 3.6), a: rnd(0, 6.28), s: rnd(0.8, 1.6) * (Math.random() < 0.5 ? -1 : 1) };
    m.rb = /rainbow|jeb_/i.test(String(m.e.display || '')) || /rainbow|jeb/i.test(ctx.drop.title || '');
    m.ph = rnd(0, 1);
    m.route = routeFor(m, spawn, goal);
    applyFlip(m, m.e);
    if (i < (n > 3 ? 1 : 3)) m.tag = tagFor(ctx, m, m.e);
  });
  if (mobs[0]) watch('mobs', () => V(P.x - rmax * 0.5, Math.min(2, size * 0.6) + (fly ? 1.5 : 0), P.z), size + (fly ? 3 : 0));
  const total = list[0] ? list[0].total : n;
  const camD = Math.max(6.2, rmax * 1.9 + size * 1.3);
  const cam = () => ({
    pos: V(P.x - rmax * 0.35, (small ? 2.3 : 1.9) + size * 0.35 + (fly ? 1.2 : 0), P.z + camD),
    look: V(P.x - rmax * 0.45, size * 0.5 + (fly ? 1.8 : 0.35), P.z),
    fov: small ? 50 : 46,
  });
  let fireT = null, said = false, creeperSnd = false, endTp = false;
  const fireball = mobs.find((m) => m.id === 'Ghast');
  const maxArrive = Math.max(...mobs.map((m) => m.born + m.T), 3);
  return {
    dur: Math.max(5.6, maxArrive + 2.2 + (fireball ? 1.5 : 0)),
    mobs, cam,
    update(t, dt) {
      for (const m of mobs) {
        if (t < m.born) continue;
        if (!m.puffed) {
          m.puffed = true;
          if (m.style === 'pour') puff(ctx, V(m.spawn.x, 1.1, m.spawn.z), { n: 5, size: 0.3 });
          if (m.id === 'Enderman') { burst(ctx, V(m.goal.x, 1.4, m.goal.z), { n: 14, colors: [0xb36bff, 0x6a2bd6, 0xffffff], size: 0.14, speed: 0.8, up: 1.2, life: 0.9, additive: true, gravity: -1, noFloor: true }); if (!endTp) { endTp = true; sfx('mob.endermen.portal', { pos: m.goal, volume: 0.8 }); } }
        }
        const k = easeOut(clamp01((t - m.born) / m.T));
        const arrived = k >= 1;
        if (m.style === 'swarm' && arrived) {
          const a = m.orbit.a + t * m.orbit.s;
          m.root.position.x = P.x - 1.5 + Math.cos(a) * (m.orbit.r + 1.5); m.root.position.z = P.z + Math.sin(a) * m.orbit.r;
          m.root.rotation.y = facing(-Math.sin(a) * Math.sign(m.orbit.s), Math.cos(a) * Math.sign(m.orbit.s));
        } else if (!stepRoute(m, k)) {
          m.root.position.x = lerp(m.spawn.x, m.goal.x, k); m.root.position.z = lerp(m.spawn.z, m.goal.z, k);
        }
        let by = m.spawn.y + (m.flipY && !m.fly ? 0 : 0);
        if (m.style === 'pour' || (o.from && !m.fly)) by = lerp(m.spawn.y, 0, easeIn(clamp01(k * 1.4))) + Math.sin(k * Math.PI) * 0.9;
        if (m.style === 'hop' && !arrived) by = Math.abs(Math.sin((t - m.born) * 5)) * 0.45;
        if (m.style === 'hop' && arrived) by = Math.abs(Math.sin(t * 3 + m.bob)) * 0.2;
        if (!m.fly) m.root.position.y = by + (m.flipY || 0) + (m.route && m.style !== 'pour' ? nav.groundAt(m.root.position.x, m.root.position.z) : 0);
        else m.baseY = 0;
        const opts = { walk: arrived ? 0 : 1, creep: m.id === 'Creeper' };
        if (m.id === 'Creeper' && arrived) opts.hiss = clamp01((t - m.born - m.T) / 1.6);
        mobTick(m, t, dt, opts);
        if (m.id === 'Creeper' && arrived && !creeperSnd) { creeperSnd = true; sfx('random.fuse', { pos: m.root.position, volume: 0.8 }); }
        if (m.rb) rainbow(m, t, m.ph);
        if (m.tag && m.tag.material) m.tag.material.opacity = 1;
      }
      separate(mobs);
      if (fireball && fireT === null && t > fireball.born + fireball.T + 0.6) {
        fireT = t;
        sfx('mob.ghast.scream', { pos: fireball.root.position, volume: 1 });
        const from = fireball.root.position.clone().setY(fireball.root.position.y + 0.5);
        const to = V(P.x - 0.6, 1.0, P.z);
        sfx('mob.ghast.fireball', { pos: from, volume: 0.9 });
        projectile(ctx, from, to, 0xffb25a, 0.8, () => { ctx.explode(to, 0.8); sfx('random.explode', { pos: to, volume: 0.9 }); ctx.hurt(0.35); ctx.flashScreen('#ffd9a0', 0.4, 0.3); });
      }
      if (!o.inner) {
        if (!said && t > 1.0) { said = true; ctx.say(ctx.drop.title, { at: 'bottom' }); }
        ctx.steve.anim(t, dt, { walk: 0 });
      }
    },
  };
}
const FLYH = { Ghast: 4.4, Blaze: 2.4 };

MOB_SCENES.mob_spawn = (ctx) => planGroup(ctx, 6);
MOB_SCENES.mob_horde = (ctx) => planGroup(ctx, 40);
function planGroup(ctx, cap) {
  const rolled = roll(ctx.drop.actions);
  let list = mobsOf(rolled, cap);
  if (list.length && list.every((e) => e.id === 'luckyegg')) return eggsScene(ctx, list.length);
  // stacks inside a "group" scene play as towers
  if (list.some((e) => e.riding && e.riding.length)) return towerScene(ctx, list);
  if (!list.length) list = [{ id: 'Zombie' }];
  if (list.some((e) => isBig(e.id))) return grandScene(ctx, list);
  return groupScene(ctx, list);
}

// Pets: the same arrival, with hearts rising and a tame chirp.
MOB_SCENES.pet = (ctx) => {
  const rolled = roll(ctx.drop.actions);
  let list = mobsOf(rolled, 8);
  if (!list.length) list = [{ id: 'Wolf' }];
  if (list.some((e) => isBig(e.id))) return grandScene(ctx, list, { pets: true });
  const base = groupScene(ctx, list);
  const P = ctx.pos;
  const hearts = list.map((_, i) => { const h = heartSprite(); h.scale.setScalar(0.4); ctx.S.temp.add(h); return h; });
  const up = base.update;
  base.update = (t, dt) => {
    up(t, dt);
    hearts.forEach((h, i) => {
      const m = base.mobs[i];
      const k = ((t - m.born - m.T - 0.1 - i * 0.12) % 2.2 + 2.2) % 2.2;
      const on = t > m.born + m.T;
      h.position.set(m.root.position.x, m.wh + 0.4 + k * 0.7, m.root.position.z);
      h.material.opacity = on ? clamp01(1 - k / 2.2) : 0;
      if (on && !m.loved) { m.loved = true; sfx('random.levelup', { pos: m.root.position, volume: 0.35, pitch: 1.6 }); }
    });
  };
  return base;
};

// Villagers: one steps up to Steve and says its name.
MOB_SCENES.villager_trader = (ctx) => {
  const P = ctx.pos.clone();
  const rolled = roll(ctx.drop.actions);
  const e = rolled.find((a) => a.t === 'entity') || { id: 'Villager' };
  const m = spawnMob(ctx, 'Villager', V(P.x - 7, 0, P.z + 0.5), { rotY: facing(1, 0) });
  m.born = 0.6; m.T = 2.6;
  const tag = tagFor(ctx, m, { display: e.display || ctx.drop.title }, '#ffe9a8');
  let said = false, hm = false;
  const goal = V(P.x - 2.2, 0, P.z + 0.5), spawn = V(P.x - 7, 0, P.z + 0.5);
  m.wh = m.wh || 1.9; m.style = 'walk'; m.fly = 0;
  { const f = nav.nearestFree(goal.x, goal.z, 0.45, undefined, 4); goal.x = f.x; goal.z = f.z; }
  const vroute = routeFor(m, spawn, goal);
  return {
    dur: 6.0,
    cam: () => ({ pos: V(P.x - 1.3, 1.9, P.z + 5.6), look: V(P.x - 1.3, 1.2, P.z), fov: 44 }),
    update(t, dt) {
      const k = easeOut(clamp01((t - m.born) / m.T));
      if (vroute) { const [vx, vz] = posAt(vroute, k); m.root.position.set(vx, nav.groundAt(vx, vz), vz); nav.track('mob', vx, vz, vroute.r * 0.9, vroute.ign); } else m.root.position.lerpVectors(spawn, goal, k);
      mobTick(m, t, dt, { walk: k < 1 ? 1 : 0, mute: true });
      if (k >= 1 && !hm) { hm = true; sfx('mob.villager.haggle', { pos: m.root.position, volume: 1 }); }
      if (t > m.born && !m.hi) { m.hi = true; sfx('mob.villager.idle', { pos: spawn, volume: 0.8 }); }
      if (!said && t > 3.6) { said = true; ctx.say(cleanName(e.display || ctx.drop.title), { at: 'bottom' }); }
      ctx.steve.anim(t, dt, { walk: 0 });
    },
  };
};

// Lightning with mobs: the bolt hits the group; creepers turn charged.
MOB_SCENES.lightning = (ctx) => {
  const rolled = roll(ctx.drop.actions);
  const list = mobsOf(rolled, 20);
  const base = list.length ? groupScene(ctx, list) : { dur: 4.5, mobs: [], cam: () => ({ pos: V(ctx.pos.x, 2, ctx.pos.z + 7), look: V(ctx.pos.x - 2, 1.5, ctx.pos.z), fov: 44 }), update() {} };
  const P = ctx.pos;
  let struck = false;
  const tStrike = Math.max(2.4, ...base.mobs.map((m) => m.born + m.T)) + 0.3;
  const up = base.update;
  base.update = (t, dt) => {
    up(t, dt);
    if (!struck && t >= tStrike) {
      struck = true;
      strikeBolt(ctx, P.x - 3, P.z, { shake: 0.5, flash: 0.9 });
      for (const m of base.mobs) {
        if (m.id !== 'Creeper') continue;
        m.root.traverse((o) => { if (o.isMesh && o.material) { o.material = o.material.clone(); o.material.emissive = new THREE.Color(0x2a50ff); o.material.emissiveIntensity = 0.9; } });
      }
      burst(ctx, V(P.x - 3, 1, P.z), { n: 40, colors: [0x7aa8ff, 0xffffff], size: 0.2, speed: 3, up: 3, life: 1, additive: true, gravity: 5 });
    }
    if (struck && t > tStrike + 0.2 && !base._cr) { base._cr = true; if (base.mobs.some((m) => m.id === 'Creeper')) sfx('mob.creeper.say', { pos: P, volume: 0.8 }); }
  };
  base.dur = Math.max(base.dur, tStrike + 2.6);
  return base;
};

// ------------------------------------------------------------------ riding stacks
function towerScene(ctx, list, o = {}) {
  const P = ctx.pos.clone();
  const stacks = list.map((e) => [...(e.riding || []).slice().reverse(), e.id]).slice(0, 5);
  const heads = list.slice(0, 5);
  // a stack with a big mob in it gets the grand treatment
  if (stacks.some((s) => s.some(isBig))) return grandScene(ctx, heads, { stacks });
  const pieces = [];
  let stackH = 2;
  const ns = stacks.length;
  stacks.forEach((stack, si) => {
    const ang = Math.PI + (si - (ns - 1) / 2) * 0.55;
    let y = 0;
    const bf = nav.nearestFree(P.x + Math.cos(ang) * 4.2, P.z + Math.sin(ang) * 4.2, 0.7, undefined, 6);
    const bx = bf.x, bz = bf.z;
    stack.forEach((id, li) => {
      const m = spawnMob(ctx, id, V(bx, y, bz), { rotY: facing(-Math.cos(ang), -Math.sin(ang)), quiet: li > 0, main: li === stack.length - 1 && si === 0, ...(li === stack.length - 1 ? gear(heads[si]) : {}) });
      fitSmall(m);
      m.born = 0.5 + si * 0.35 + li * Math.min(0.5, 2.2 / stack.length);
      m.bx = bx; m.bz = bz; m.y0 = y;
      if (li === stack.length - 1) m.tag = tagFor(ctx, m, heads[si]);
      if (m.fly) { m.baseY = y; }
      y += m.wh * (m.fly ? 0.9 : 0.85);
      pieces.push(m);
    });
    stackH = Math.max(stackH, y);
  });
  const camD = 7.5 + stackH * 1.15;
  const camY = 1.8 + Math.min(stackH * 0.3, 6);
  return {
    dur: 6.0,
    mobs: pieces,
    cam: (t) => ({ pos: V(P.x - 2.2, camY, P.z + camD), look: V(P.x - 3.4, stackH * 0.45, P.z), fov: 48 }),
    update(t, dt) {
      for (const m of pieces) {
        if (t < m.born) continue;
        if (!m.fly) m.root.position.y = m.y0;
        mobTick(m, t, dt, { walk: 0, hover: false });
        if (m.fly) m.root.position.y = m.y0 + 0.2 + Math.sin(t * 1.6 + m.bob) * 0.1;
        m.root.rotation.z = Math.sin(t * 3 + m.born) * 0.05;
        if (!m.landSnd) { m.landSnd = true; sfx('mob.slime.small', { pos: m.root.position, volume: 0.3 }); }
      }
      if (!ctx._tw && t > 0.9) { ctx._tw = true; ctx.say(ctx.drop.title, { at: 'bottom' }); }
      ctx.steve.anim(t, dt, { walk: 0 });
    },
  };
}
MOB_SCENES.mob_tower = (ctx) => {
  const rolled = roll(ctx.drop.actions);
  let list = mobsOf(rolled, 5);
  if (!list.length) list = [{ id: 'Zombie', riding: ['Zombie', 'Zombie'] }];
  return towerScene(ctx, list);
};

// ------------------------------------------------------------------ the grand entrances
function profileOf(id) { return BIG[id] || null; }
function grandScene(ctx, list, o = {}) {
  const P = ctx.pos.clone();
  // the stars are the big mobs; any ordinary mob in the drop arrives with them
  const stacks = o.stacks || list.map((e) => [e.id]);
  const starIds = [...new Set(stacks.flat().filter(isBig))];
  const prof = profileOf(starIds.sort((a, b) => BIG[b].h - BIG[a].h)[0]);
  const nStar = Math.min(10, stacks.filter((s) => s.some(isBig)).length);
  const actors = [];
  const pad = Math.max(1, nStar);
  let totalH = 0;
  stacks.slice(0, 12).forEach((stack, si) => {
    const star = stack.some(isBig);
    const ids = stack;
    const bp = profileOf(ids.find(isBig)) || { h: 0, enter: 'walk' };
    // lateral slot: the stars spread along z in front of Steve, the rest behind them
    const zi = (si - (stacks.length - 1) / 2);
    const enter = star ? bp.enter : 'walk';
    const goal = V(P.x - (bp.dist || 4.5) - (star ? 0 : 5 + rnd(0, 2)) - Math.abs(zi) * (stacks.length > 3 ? 0.6 : 0.3), 0, P.z + 0.5 + zi * (stacks.length > 6 ? 1.6 : (star ? 3.2 : 1.4)) * (bp.h > 8 ? 1.6 : 1));
    const gf = (enter === 'walk' || (enter === 'rise' && !bp.fly)) ? nav.nearestFree(goal.x, goal.z, Math.min(3.6, Math.max(0.5, (bp.h || 2) * 0.16)), new Set(SOFT), 12) : { x: goal.x, z: goal.z };
    goal.x = gf.x; goal.z = gf.z;
    const from = enter === 'fly' ? V(goal.x - 26 - rnd(0, 6), (bp.fly || 4) + 14, goal.z + rnd(-8, 8)) : enter === 'rise' ? goal.clone() : V(goal.x - 24 - rnd(0, 5), 0, goal.z + rnd(-1.5, 1.5));
    const mobs = [];
    let y = 0;
    ids.forEach((id, li) => {
      const p = profileOf(id);
      const m = spawnMob(ctx, id, V(from.x, 0, from.z), { quiet: true, height: p ? p.h : undefined, ...(li === ids.length - 1 ? gear(list[si]) : {}), main: star && li === ids.length - 1 && si === 0, rotY: facing(goal.x - from.x, goal.z - from.z) });
      fitSmall(m);
      m.stackY = y; m.fly = 0;
      y += m.wh * 0.88;
      mobs.push(m);
    });
    totalH = Math.max(totalH, y);
    const gRoute = enter === 'walk' ? routeFor({ wh: Math.max(y, 0.5), style: 'walk', fly: 0, footR: Math.min(3.6, Math.max(0.25, ...mobs.map((q) => footRadius(q)))) }, from, goal) : null;
    const display = stack.length === 1 ? list[si] : list[si];
    actors.push({ mobs, route: gRoute, stack: ids, from, goal, enter, p: bp, star, t0: 0.9 + si * (star && nStar > 1 ? 0.18 : 0.12), T: enter === 'walk' ? 3.6 : enter === 'rise' ? 1.6 : 3.0, flyH: bp.fly || 0, e: display || {} });
    const top = mobs[mobs.length - 1];
    if (display && display.display) top.tag = tagFor(ctx, top, display);
  });
  const H = Math.max(totalH, prof ? prof.h : 3);
  const night = prof ? prof.night : 0.7;
  const fog0 = prof ? prof.fog : [14, 50];
  const bolts = prof ? prof.bolts : [1.4, 4];
  const arrive = Math.max(...actors.map((a) => a.t0 + a.T));
  const roarAt = arrive + 0.2;
  const dur = Math.max(7.4, roarAt + 3.4);
  const camD = (H < 6 ? 6.5 + H * 1.0 : 8.5 + H * (H > 12 ? 1.5 : 1.25)) + (nStar > 3 ? 4 : 0);
  const fog = [Math.max(fog0[0], camD * 0.9), Math.max(fog0[1], camD * 2.4 + 12)];
  const camX = P.x - (prof ? prof.dist : 5) * 0.8;
  watch('boss', () => V(actors[0].goal.x, H * 0.5 + (actors[0].flyH || 0) * 0.5, actors[0].goal.z), H);
  // the lights that keep a night scene readable: cold rim light on the creature, warm on Steve
  const rim = pointLight(ctx, 0x9db4ff, 0, 60, V(actors[0].goal.x + 2, H + 4, actors[0].goal.z + 6));
  const warm = pointLight(ctx, 0xffc080, 0, 14, V(P.x - 1, 2.2, P.z + 3));
  let boltI = 0, said = false, roared = false, thunder0 = false, stepPh = 0, skullI = 0, idle = false;
  const skullTimes = prof && prof.skulls ? [roarAt + 0.6, roarAt + 1.3, roarAt + 2.0] : [];
  return {
    _grand: true,
    dur, mobs: actors.flatMap((a) => a.mobs),
    cam: (t) => {
      const push = 1.18 - 0.2 * easeInOut(clamp01(t / (roarAt + 1)));
      const tilt = easeInOut(clamp01((t - roarAt + 0.3) / 1.0));
      return {
        pos: V(camX + 1.5, (H < 6 ? 2.2 : 1.2) + Math.min(H * 0.28, 7) + (actors[0].flyH ? 1.2 : 0), P.z + camD * push),
        look: V(P.x - (prof ? prof.dist : 5) * 0.9, H * 0.4 + (actors[0].flyH ? actors[0].flyH * 0.7 : 0) + tilt * H * 0.05, P.z),
        fov: 52 + (H > 8 ? 6 : 0),
      };
    },
    update(t, dt) {
      // the sky: darkens over the first 1.4 s; fog rolls in and lifts again at the very end
      const kSky = easeInOut(clamp01(t / 1.4));
      const lift = clamp01((t - (dur - 1.4)) / 1.2);
      sky(ctx, kSky, { night, near: fog[0], far: fog[1], fog: kSky * (1 - lift) });
      rim.intensity = (60 + 25 * H) * kSky; warm.intensity = 5 * kSky;
      if (!thunder0 && t > 0.15) { thunder0 = true; sfx('ambient.weather.thunder', { volume: 0.55 }); }
      while (boltI < bolts.length && t >= bolts[boltI]) {
        const a = actors[boltI % actors.length];
        const far = boltI % 2 === 1;
        strikeBolt(ctx, a.goal.x + (far ? rnd(-9, 9) : rnd(-2, 2)) - (far ? 4 : 0), a.goal.z + (far ? rnd(-9, 9) : rnd(-2, 2)), { shake: 0.3 + 0.1 * (boltI % 2), flash: 0.55 + 0.25 * (boltI === 0), volume: 1 });
        boltI++;
      }
      for (const a of actors) {
        const m0 = a.mobs[0];
        const age = t - a.t0;
        const k = clamp01(age / a.T);
        const kk = a.enter === 'walk' ? (a.star ? k : easeOut(k)) : easeOut(k);
        let x = lerp(a.from.x, a.goal.x, kk), z = lerp(a.from.z, a.goal.z, kk), y = 0;
        if (a.route) { [x, z] = posAt(a.route, kk); nav.track('mob', x, z, a.route.r * 0.9, a.route.ign, a.stack[0]); y = nav.groundAt(x, z); }
        if (a.enter === 'fly') {
          y = lerp(a.from.y, a.flyH, easeOut(k)) + Math.sin(t * 1.3 + m0.bob) * 0.3;
          if (k >= 1) { const c = (t - a.t0 - a.T) * 0.5; x += Math.cos(c + m0.bob) * 0.8; z += Math.sin(c + m0.bob) * 1.2; }
        } else if (a.enter === 'rise') {
          y = -a.mobs.reduce((s, m) => s + m.wh, 0) * (1 - easeOut(k)) * 1.1 + (a.flyH ? a.flyH * easeIn(clamp01((age - 0.8) / 2.2)) : 0);
          if (a.flyH && k >= 1) y += Math.sin(t * 1.3 + m0.bob) * 0.25;
          if (age > 0 && !a.dug && a.p.dirt) { a.dug = true; puff(ctx, V(a.goal.x, 0.4, a.goal.z), { n: 40, size: 0.9, speed: 3, colors: [0x6b4a2e, 0x8a6a46, 0x4a3320] }); ctx.shake(0.5); sfx('dig.gravel', { pos: a.goal, volume: 1, pitch: 0.6 }); }
          if (age > 0 && !a.dug && !a.p.dirt) { a.dug = true; burst(ctx, V(a.goal.x, 0.3, a.goal.z), { n: 40, colors: [0x2a2a30, 0x8a8a95, 0x4a4a55], size: 0.3, speed: 2.6, up: 3, life: 1.4, additive: false, gravity: 2 }); }
        }
        if (age < 0) { for (const m of a.mobs) m.root.scale.setScalar(0.001); continue; }
        a.mobs.forEach((m, li) => {
          if (m.born === null) { m.born = a.t0; if (a.enter === 'walk' || a.enter === 'fly') puff(ctx, V(a.from.x, y + 1, a.from.z), { n: 14, size: 1.0, colors: [0xf2f4ff, 0xb8c4ff] }); }
          m.root.position.set(x, y + m.stackY, z);
          m.root.rotation.y = facing(a.goal.x - a.from.x, a.goal.z - a.from.z);
          const walking = a.enter === 'walk' && k < 1;
          mobTick(m, t, dt, { walk: walking ? 1 : 0, hover: false, mute: true, grow: 0.7 });
          if (m.flipY) m.root.position.y += m.flipY;
        });
        // footfalls: a shake and a thud each step while walking
        if (a.enter === 'walk' && a.star && k > 0 && k < 1 && a.p.step) {
          const ph = Math.floor(age * (a.p.h > 8 ? 1.3 : 2.0));
          if (ph !== a.stepPh) { a.stepPh = ph; ctx.shake(0.12 + 0.015 * a.p.h); sfx(a.p.step[0], { pos: m0.root.position, volume: 0.9, pitch: a.p.step[1] }); if (a.p.h > 6) puff(ctx, V(m0.root.position.x, 0.2, m0.root.position.z), { n: 6, size: 0.7 }); }
        }
      }
      if (!roared && t >= roarAt) {
        roared = true;
        const rn = prof ? prof.roar : ['mob.zombie.say'];
        rn.forEach((s, i) => sfx(s, { pos: actors[0].goal, volume: 1, pitch: prof && prof.roarPitch ? prof.roarPitch : undefined }));
        for (const a of actors) a.mobs.forEach((m) => mobSay(m.id, m.root.position, 'say', { force: true, volume: 1 }));
        ctx.shake(0.7); ctx.flashScreen('#ffffff', 0.35, 0.5);
        burst(ctx, V(actors[0].goal.x, 0.3, actors[0].goal.z), { n: 50, colors: [0xcfc8d8, 0x9d98a8], size: 0.9, speed: 4, up: 0.8, life: 1.6, gravity: -0.1, additive: false });
        strikeBolt(ctx, actors[0].goal.x - 1.5, actors[0].goal.z - 2, { shake: 0.5, flash: 0.8 });
      }
      if (prof && prof.idle && t > roarAt + 1 && !idle) { idle = true; sfx(prof.idle, { pos: actors[0].goal, volume: 0.8 }); }
      if (skullI < skullTimes.length && t >= skullTimes[skullI]) {
        const m = actors[0].mobs[actors[0].mobs.length - 1];
        const from = m.root.position.clone().setY(m.root.position.y + m.wh * 0.7);
        const to = V(P.x - 0.4, 1.2, P.z + rnd(-0.3, 0.3));
        sfx('mob.wither.shoot', { pos: from, volume: 1 });
        projectile(ctx, from, to, 0x1b1b24, 0.7, () => { ctx.explode(to, 0.8); sfx('random.explode', { pos: to, volume: 0.9 }); ctx.hurt(0.4); });
        skullI++;
      }
      ctx.steve.anim(t, dt, { walk: 0, armRaise: 0.5 * easeInOut(clamp01((t - roarAt) / 0.6)) });
      ctx.steve.root.rotation.y = Math.PI / 2;
      if (!said && t > 0.6) { said = true; ctx.say(ctx.drop.title, { at: 'bottom' }); }
      if (t > roarAt + 0.6) ctx.shake(0.05);
    },
  };
}
MOB_SCENES.boss = (ctx) => {
  const rolled = roll(ctx.drop.actions);
  const list = mobsOf(rolled, 12);
  if (!list.length) return groupScene(ctx, [{ id: 'Zombie' }]);
  const withStacks = list.some((e) => e.riding && e.riding.length);
  if (withStacks) return towerScene(ctx, list);
  return grandScene(ctx, list);
};

// ------------------------------------------------------------------ the apocalypse
// Night, a sword, blindness; zombies, creepers and spiders close in from every side out of the fog.
MOB_SCENES.apocalypse = (ctx) => {
  const P = ctx.pos.clone();
  const rolled = roll(ctx.drop.actions);
  const list = mobsOf(rolled, 44);
  if (!list.length) return dudBeat(ctx);
  const mobs = list.map((e, i) => {
    const m = spawnMob(ctx, e.id, V(0, 0, 0), { quiet: true, main: i === 0, ...gear(e) });
    fitSmall(m);
    const ang = (i / list.length) * Math.PI * 2 + rnd(-0.1, 0.1);
    const r = 3.0 + (i % 3) * 1.4;
    m.goal = freeGoal(m, V(P.x + Math.cos(ang) * r, 0, P.z + Math.sin(ang) * r));
    m.spawn = V(P.x + Math.cos(ang) * (r + 13), 0, P.z + Math.sin(ang) * (r + 13));
    m.off = { x: 0, z: 0 }; m.style = m.style || 'walk';
    m.route = routeFor(m, m.spawn, m.goal);
    m.born = 1.4 + i * 0.07; m.T = 3.2;
    m.root.rotation.y = facing(m.goal.x - m.spawn.x, m.goal.z - m.spawn.z);
    return m;
  });
  let said = false, bolt = 0, thunder = false;
  return {
    dur: 9.0, mobs,
    cam: (t) => ({ pos: V(P.x - 1.0, 3.2 + t * 0.12, P.z + 11.5), look: V(P.x - 1.2, 1.1, P.z), fov: 52 }),
    update(t, dt) {
      const k = easeInOut(clamp01(t / 1.6));
      sky(ctx, k, { night: 1, near: 8, far: 34, fog: k * (1 - clamp01((t - 7.8) / 1.0)) });
      if (!thunder) { thunder = true; sfx('ambient.weather.thunder', { volume: 0.7 }); }
      if (t > 0.5 && bolt === 0) { bolt = 1; strikeBolt(ctx, P.x - 5, P.z + 3, { shake: 0.3 }); }
      if (t > 3.5 && bolt === 1) { bolt = 2; strikeBolt(ctx, P.x + 3, P.z - 5, { shake: 0.3 }); }
      if (t > 1.0) ctx.tint(0x8b5cf6, 0.12 * clamp01((t - 1.0) / 1.2));
      for (const m of mobs) {
        if (t < m.born) continue;
        const kk = easeOut(clamp01((t - m.born) / m.T));
        if (stepRoute(m, kk)) m.root.position.y = nav.groundAt(m.root.position.x, m.root.position.z); else m.root.position.lerpVectors(m.spawn, m.goal, kk);
        mobTick(m, t, dt, { walk: kk < 1 ? 1 : 0, creep: m.id === 'Creeper' });
        if (m.id === 'Creeper' && kk >= 1) m.anim(t, dt, { walk: 0, hiss: clamp01((t - m.born - m.T) / 1.5) });
      }
      separate(mobs);
      if (!said && t > 1.2) { said = true; ctx.say(ctx.drop.title, { at: 'bottom' }); }
      ctx.steve.anim(t, dt, { walk: 0, armRaise: 0.25 });
    },
  };
};

// Lucky eggs are thrown projectiles, not mobs: they fountain out of the block, land around it
// and each pops into a small burst of colour.
function eggsScene(ctx, n) {
  const O = ctx.dais.clone();
  const G = 18, y0 = O.y + 0.7;
  const eggs = [];
  for (let i = 0; i < n; i++) {
    const hue = i / n;
    const m = new THREE.Mesh(new THREE.SphereGeometry(0.17, 12, 9), new THREE.MeshLambertMaterial({ color: new THREE.Color().setHSL(hue, 0.85, 0.68), emissive: new THREE.Color().setHSL(hue, 0.9, 0.3) }));
    m.scale.set(1.4, 1.8, 1.4); m.visible = false; ctx.S.temp.add(m);
    const spot = new THREE.Mesh(new THREE.SphereGeometry(0.06, 6, 5), new THREE.MeshBasicMaterial({ color: 0xffffff }));
    spot.position.set(0.1, 0.08, 0.1); m.add(spot);
    if (F.report()) F.report().items++;
    const a = rnd(0, Math.PI * 2), sp = rnd(0.9, 2.3), vy = rnd(6.5, 8.5);
    eggs.push({ m, t0: 0.4 + i * 0.12, v: V(Math.cos(a) * sp, vy, Math.sin(a) * sp), tl: (vy + Math.sqrt(vy * vy + 2 * G * (y0 - 0.15))) / G, done: false, hue });
  }
  watch('eggs', () => V(O.x, O.y + 2, O.z), 4);
  let said = false;
  return {
    dur: 0.4 + n * 0.12 + 2.4,
    cam: () => ({ pos: V(O.x + 0.6, 3.0, O.z + 5.4), look: V(O.x, 3.0, O.z), fov: 50 }),
    update(t, dt) {
      eggs.forEach((e, i) => {
        if (t < e.t0 || e.done) return;
        const s = t - e.t0;
        e.m.visible = true;
        e.m.position.set(O.x + e.v.x * s, y0 + e.v.y * s - 0.5 * G * s * s, O.z + e.v.z * s);
        e.m.rotation.z += dt * 9; e.m.rotation.x += dt * 5;
        if (s === 0 || (i % 3 === 0 && !e.snd)) { e.snd = true; sfx('random.bow', { pos: O, volume: 0.35, pitch: 1.5 + (i % 5) * 0.08 }); }
        if (s >= e.tl) {
          e.done = true; e.m.visible = false;
          burst(ctx, V(e.m.position.x, 0.25, e.m.position.z), { n: 16, colors: [new THREE.Color().setHSL(e.hue, 0.9, 0.6).getHex(), 0xffffff, 0xf2c14e], size: 0.13, speed: 1.6, up: 2.4, life: 0.9, additive: true });
          if (i % 2 === 0) sfx('random.pop', { pos: e.m.position, volume: 0.6, pitch: 1.2 + (i % 4) * 0.1 });
        }
      });
      if (!said && t > 0.8) { said = true; ctx.say(ctx.drop.title, { at: 'bottom' }); }
      ctx.steve.anim(t, dt, { walk: 0 });
    },
  };
}
