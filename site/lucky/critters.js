// The camp's animals: a tame wolf that trots along with Steve, a sheep and a cow that graze on the pasture.
// They are ambient life, and Steve's activities borrow them (feed the dog, shear the sheep, milk the cow):
// hold(c, true) switches the wanderer off, go(c, x, z) walks it along a route that goes around every prop.
// Every one of them keeps out of the props (nav.js) and out of Steve.
import * as THREE from 'three';
import { makeMob } from './mobs.js';
import { tex as mobTex } from '../lib/mc/textures.js';
import { mulberry } from './stage.js';
import { nav, followPath } from './nav.js';

const TAU = Math.PI * 2;
const wrapA = (a) => { a = (a + Math.PI) % TAU; if (a < 0) a += TAU; return a - Math.PI; };
const yawFor = (dx, dz) => Math.atan2(-dx, -dz); // front is -z at yaw 0, the same as Steve
const PASTURE = { x0: -8.6, x1: -5.7, z0: 3.4, z1: 6.6 }; // the fenced pen (camp.js L.pen), well off the camera's line to the dais

export function makeCritters({ world, play, fx, seed = 5 }) {
  const rng = mulberry(seed);
  const R = (a = 0, b = 1) => a + rng() * (b - a);
  const list = [];
  const SPEC = {
    // r: body radius for routing; walk: cruising speed in m/s; step: the game's step sound; voice: ambient call
    Sheep: { r: 0.4, walk: 0.62, voice: 'mob.sheep.say', pitch: [0.95, 1.1], every: [9, 22] },
    Cow: { r: 0.5, walk: 0.58, voice: 'mob.cow.say', pitch: [0.95, 1.05], every: [11, 26] },
    Wolf: { r: 0.3, walk: 1.5, voice: null, every: [6, 12] },
    Creeper: { r: 0.32, walk: 0.95, voice: null, every: [999, 999] },
  };
  const ign = new Set(['low']);

  function tame(m) {
    // RenderWolf: the tame skin, and the collar pass in the collar colour (red) over the same geometry
    m.mats[0].map = mobTex('entity/wolf/wolf_tame.png');
    m.mats[0].needsUpdate = true;
    const collar = new THREE.MeshLambertMaterial({ map: mobTex('entity/wolf/wolf_collar.png'), color: 0xb33333, transparent: true, alphaTest: 0.1, polygonOffset: true, polygonOffsetFactor: -2 });
    const meshes = [];
    m.root.traverse((o) => { if (o.isMesh && o.material === m.mats[0]) meshes.push(o); });
    for (const o of meshes) { const c = new THREE.Mesh(o.geometry, collar); c.castShadow = false; o.add(c); }
  }
  function add(kind, x, z, o = {}) {
    const m = makeMob(kind, o.mob || {});
    m.root.traverse((q) => { if (q.isMesh) q.castShadow = true; });
    if (kind === 'Wolf') tame(m);
    // pale skins bloom to white under the sunset lights: tone them down
    if (kind === 'Sheep' && m.mats[1]) m.mats[1].color.multiplyScalar(0.62);
    if (kind === 'Sheep' || kind === 'Wolf') m.mats[0].color.multiplyScalar(0.7);
    const sp = SPEC[kind];
    const c = {
      kind, m, sp, x, z, yaw: R(0, TAU), y: 0, path: null, i: 0, state: 'stand', wait: R(1, 4), clock: R(0, 9), moving: false, speed: 0,
      pitch: 0, pitchT: 0, headYaw: 0, hold: false, voiceT: R(...sp.every), sheared: false, home: o.home || PASTURE, bob: 0, sit: 0,
    };
    m.root.position.set(x, 0, z);
    world.add(m.root);
    list.push(c);
    return c;
  }
  const api = { list, add, hold, go, face, shear, setVisible, update, reset, spawn, remove };

  // a visitor for one activity (a creeper): driven by the activity, not by the wanderer
  function spawn(kind, x, z) { const c = add(kind, x, z); c.hold = true; c.temp = true; c.hiss = 0; return c; }
  function remove(c) { const i = list.indexOf(c); if (i >= 0) list.splice(i, 1); world.remove(c.m.root); }
  function hold(c, on) { c.hold = !!on; if (on) { c.path = null; c.state = 'stand'; c.pitchT = 0; } else { c.wait = R(1, 3); } }
  // walk to a point along a planned route: returns a function(dt) -> done for a generator to yield
  function go(c, x, z, speed) {
    const f = nav.nearestFree(x, z, c.sp.r, ign, 3);
    const pts = nav.path(c.x, c.z, f.x, f.z, c.sp.r, { ign });
    c.path = pts; c.i = 0; c.speed = speed ?? c.sp.walk; c.state = 'walk';
    let stuck = 0;
    return (dt) => {
      if (!c.path) return true;
      const before = c.x + c.z;
      step(c, dt);
      if (!c.path) return true;
      stuck = Math.abs(c.x + c.z - before) < 1e-5 ? stuck + dt : 0;
      if (stuck > 1.5) { c.path = null; c.moving = false; return true; }
      return false;
    };
  }
  function face(c, x, z, rate = 6) { return (dt) => { const d = wrapA(yawFor(x - c.x, z - c.z) - c.yaw); c.yaw += d * Math.min(1, dt * rate); return Math.abs(d) < 0.05; }; }
  function shear(c, on) {
    c.sheared = !!on;
    c.m.root.traverse((o) => { if (o.isMesh && o.material === c.m.mats[1]) o.visible = !on; });
  }
  function step(c, dt) {
    const h = followPath(c, dt, c.speed, nav, c.sp.r * 0.8, ign);
    if (!h) { c.path = null; c.moving = false; return; }
    c.moving = true;
    c.yaw += wrapA(yawFor(h.dx, h.dz) - c.yaw) * Math.min(1, dt * 5);
    c.clock += h.step * 1.35 * (c.kind === 'Wolf' ? 1.2 : 1);
  }
  const inHome = (c) => ({ x: R(c.home.x0, c.home.x1), z: R(c.home.z0, c.home.z1) });

  function think(c, dt, sx, sz) {
    c.wait -= dt;
    c.voiceT -= dt;
    if (c.voiceT <= 0) {
      c.voiceT = R(...c.sp.every);
      if (c.sp.voice) play(c.sp.voice, { pos: { x: c.x, y: 1, z: c.z }, volume: 0.5, pitch: c.sp.pitch, ref: 6, rolloff: 0.6 });
      else if (c.kind === 'Wolf' && !c.moving) play('mob.wolf.panting', { pos: { x: c.x, y: 0.6, z: c.z }, volume: 0.4, ref: 5, rolloff: 0.6 });
    }
    if (c.kind === 'Wolf') {
      // a dog that keeps company: it trots when he is more than four blocks off, and idles about two blocks back
      const d = Math.hypot(sx - c.x, sz - c.z);
      if (c.state === 'walk') { if (!c.path) { c.state = 'stand'; c.wait = R(1.5, 4); } else if (d < 2.6) { c.path = null; c.moving = false; c.state = 'stand'; c.wait = R(2, 5); } }
      if (c.state !== 'walk' && (d > 4.6 || (c.wait <= 0 && d > 1.6 && rng() < 0.5))) {
        // the dog waits on the far side of him from the lens, so it never stands between camera and Steve
        let a = R(0, TAU); const k = d > 4.6 ? 2.4 : R(1.8, 3.2);
        if (camAt) a = Math.atan2(sz - camAt.z, sx - camAt.x) + R(-0.9, 0.9);
        const g = nav.nearestFree(sx + Math.cos(a) * k, sz + Math.sin(a) * k, c.sp.r, ign, 3);
        c.path = nav.path(c.x, c.z, g.x, g.z, c.sp.r, { ign }); c.i = 0; c.state = 'walk';
        c.speed = d > 7 ? 3.4 : d > 4.6 ? 2.4 : 1.1;
      } else if (c.state === 'stand' && c.wait <= 0) {
        // a look around, a sniff at the ground
        c.pitchT = c.pitchT > 0.2 ? 0 : 0.5; c.headYaw = R(-0.6, 0.6); c.wait = R(1.5, 4);
      }
      return;
    }
    if (c.state === 'walk') { if (!c.path) { c.state = 'stand'; c.wait = R(1.5, 4); } return; }
    if (c.wait > 0) return;
    const r = rng();
    if (r < 0.45) { c.state = 'graze'; c.pitchT = c.kind === 'Sheep' ? 0.95 : 0.8; c.wait = R(3, 6.5); c.headYaw = 0; }
    else if (r < 0.8) {
      const g = inHome(c), f = nav.nearestFree(g.x, g.z, c.sp.r, ign, 3);
      c.path = nav.path(c.x, c.z, f.x, f.z, c.sp.r, { ign }); c.i = 0; c.speed = c.sp.walk; c.state = 'walk'; c.pitchT = 0;
    } else { c.state = 'stand'; c.pitchT = 0; c.wait = R(2, 5); c.headYaw = R(-0.5, 0.5); }
    if (c.state === 'graze' && c.kind === 'Sheep') c.eatT = R(2.5, 5);
  }

  let clock = 0, camAt = null;
  function update(dt, sx, sz, cam) {
    camAt = cam || null;
    clock += dt;
    for (const c of list) {
      if (!c.hold) {
        think(c, dt, sx, sz);
        if (c.state === 'walk' && c.path) step(c, dt); else c.moving = false;
        // a sheared sheep eats grass and the wool grows back
        if (c.sheared && c.regrowT > 0) {
          c.regrowT -= dt;
          if (c.regrowT <= 0) { c.state = 'graze'; c.pitchT = 0.95; c.wait = 3.2; c.path = null; c.eatT = 2.4; }
        }
        if (c.sheared && c.eatT > 0 && c.state === 'graze') {
          c.eatT -= dt;
          if (c.eatT <= 0) { shear(c, false); play('dig.grass', { pos: { x: c.x, y: 0.3, z: c.z }, volume: 0.4, pitch: 1.2, ref: 5 }); fx.chips({ x: c.x, y: 0.4, z: c.z }, [0xf0f0f0], 6, { speed: 0.4, up: 0.4 }); }
        }
        // keep clear of Steve and of each other
        for (const o of list) {
          if (o === c) continue;
          const dx = c.x - o.x, dz = c.z - o.z, d = Math.hypot(dx, dz), need = c.sp.r + o.sp.r;
          if (d < need && d > 0.001) { c.x += (dx / d) * (need - d) * 0.5; c.z += (dz / d) * (need - d) * 0.5; }
        }
        if (!(c.kind === 'Wolf' && c.state === 'stand')) {
          const dx = c.x - sx, dz = c.z - sz, d = Math.hypot(dx, dz), need = c.sp.r + 0.5;
          if (d < need && d > 0.001) { c.x += (dx / d) * (need - d); c.z += (dz / d) * (need - d); }
        }
      }
      const f = nav.resolve(c.x, c.z, c.sp.r * 0.8, ign);
      c.x = f.x; c.z = f.z;
      nav.track('critter', c.x, c.z, c.sp.r * 0.7, ign, c.kind);
      c.pitch += (c.pitchT - c.pitch) * Math.min(1, dt * 4);
      c.y = nav.groundAt(c.x, c.z);
      const m = c.m;
      m.root.position.set(c.x, c.y, c.z);
      m.root.rotation.y = c.yaw;
      if (m.anim) m.anim(c.clock, dt, { walk: c.moving ? Math.min(1.6, 0.7 + (c.speed || 1) * 0.4) : 0, lookPitch: c.pitch, lookAt: c.headYaw, sit: c.sit > 0.5, hiss: c.hiss || 0 });
    }
  }
  function setVisible(v) { for (const c of list) c.m.root.visible = v; }
  function reset() {
    for (const c of list) { shear(c, false); c.hold = false; c.path = null; c.moving = false; c.state = 'stand'; c.wait = R(1, 3); c.pitchT = c.pitch = 0; }
    const place = [['Sheep', -7.4, 4.6], ['Cow', -6.4, 5.8], ['Wolf', 4.2, 1.6]];
    list.forEach((c, i) => { const p = place.find((q) => q[0] === c.kind) || place[i]; c.x = p[1]; c.z = p[2]; });
  }
  // the herd
  add('Sheep', -7.4, 4.6, { mob: { dye: 0 } });
  add('Cow', -6.4, 5.8);
  add('Wolf', 4.2, 1.6, { home: { x0: 2, x1: 6, z0: 0, z1: 3 } });
  return api;
}
