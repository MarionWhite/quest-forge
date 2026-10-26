// Pieces several scares share: the freeze (the head settles where the walk stopped), the fall to the floor,
// timing helpers, and the hearts' damage bookkeeping.
import { THREE, track, clamp, lerp, sstep, wobble } from "./rig.js";

// The freeze: from the pose the walk left (often turned to a stone) the head comes to rest looking down the corridor,
// at the 1.62 m eye. Returns a base camera at t.
export function settle(R, t, t1 = 0.9, to = {}) {
  const k = sstep(0, t1, t), s = R.start;
  return { x: lerp(s.x, to.x ?? s.x, k), y: lerp(s.y, to.y ?? R.eye, k), z: lerp(s.z, to.z ?? s.z, k), yaw: lerp(s.yaw, to.yaw ?? 0, k),
    pitch: lerp(s.pitch, to.pitch ?? -0.02, k), roll: 0, fov: lerp(s.fov, to.fov ?? s.fov, k) };
}
// Shake for a hand-held head: amp in metres (and a third of it in radians).
export function shake(c, t, amp, seed = 0) {
  if (amp <= 0) return c;
  c.x += wobble(t, seed) * amp; c.y += wobble(t, seed + 5) * amp; c.yaw += wobble(t, seed + 9) * amp * 0.35; c.pitch += wobble(t, seed + 13) * amp * 0.3;
  return c;
}
// Damage list -> hits with a total of 20 (the last one kills).
export function hitsOf(list) {
  let left = 20;
  return list.map(([t, dmg, side], i) => { const d = i === list.length - 1 ? left : Math.min(left - 1, dmg); left -= d; return { t, dmg: d, side: side ?? (i % 2 ? -1 : 1) }; });
}
// Hurt sounds for each hit (game.player.hurt), plus extras.
export function hurtSounds(hits, extra = []) {
  const out = [];
  hits.forEach((h, i) => { out.push([h.t, "game.player.hurt"]); for (const [dt, name, o] of extra) out.push([h.t + dt, typeof name === "function" ? name(i) : name, o]); });
  return out;
}
// Knocked down: the head falls to the floor (y ~0.25) and rolls onto its side over d seconds, from pose c at t0.
export function floorFall(c, t, t0, { d = 0.55, side = 1, roll = 1.25, y = 0.24, pitch = 0.1, back = 0.25 } = {}) {
  if (t <= t0) return c;
  const k = clamp((t - t0) / d), e = k * k;   // gravity: accelerating
  const bounce = k >= 1 ? Math.exp(-(t - t0 - d) * 9) * Math.sin((t - t0 - d) * 30) * 0.02 : 0;
  c.y = lerp(c.y, y, e) + bounce; c.roll = lerp(c.roll || 0, roll * side, sstep(0.15, 1, k)); c.pitch = lerp(c.pitch, pitch, sstep(0, 1, k));
  c.z -= back * e;
  return c;
}
export { track, clamp, lerp, sstep };

// Limbs that reach into the lens: copies of a mob's part (an arm, a leg) parented to the head (R.view), drawn over
// the world. specs: [{ from: [x, y], to: [x, y], z, t0, t1, scale }] in view metres (x right, y up, z forward < 0).
export function lensLimbs(R, mob, part, specs, { color = 0x8a8a8a } = {}) {
  const src = mob.parts[part];
  const out = specs.map((s) => {
    const g = src.clone(true);
    g.traverse((o) => {
      if (!o.isMesh) return;
      const m = Array.isArray(o.material) ? o.material[0] : o.material;
      o.material = new THREE.MeshBasicMaterial({ map: m.map || null, color, transparent: true, depthTest: false, depthWrite: false, side: THREE.DoubleSide, alphaTest: 0.1, fog: false });
      o.renderOrder = 2000;
    });
    g.rotation.set(0, 0, 0); g.position.set(0, 0, 0);
    const holder = new THREE.Group(); holder.add(g); holder.visible = false; R.view.add(holder);
    return { s, holder };
  });
  return (t) => {
    for (const { s, holder } of out) {
      const k = sstep(s.t0, s.t1, t);
      holder.visible = k > 0;
      if (!holder.visible) continue;
      const x = lerp(s.from[0], s.to[0], k), y = lerp(s.from[1], s.to[1], k);
      const dx = s.to[0] - s.from[0], dy = s.to[1] - s.from[1];
      holder.position.set(x, y, s.z ?? -0.32);
      const base = s.axis === "x-" ? Math.atan2(-dy, -dx) : s.axis === "x+" ? Math.atan2(dy, dx) : Math.atan2(dx, -dy);
      holder.rotation.set(s.tilt ?? 0, 0, base + (s.twist ?? 0) * Math.sin(t * 7 + (s.ph ?? 0)) + (s.curl ? s.curl * k : 0));
      holder.scale.setScalar(s.scale ?? 0.55);
    }
  };
}

// The 1.7.10 arrow (RenderArrow): two crossed 16 x 4 quads from entity/arrow.png at 0.05625 a unit, tip at +x.
// Returns a group whose +x is the flight direction; aim it with arrowAim.
export function arrowMesh(tex) {
  const g = new THREE.Group();
  const mat = new THREE.MeshBasicMaterial({ map: tex, side: THREE.DoubleSide, alphaTest: 0.1, color: 0xb0b0b0 });
  for (let i = 0; i < 2; i++) {
    const geo = new THREE.PlaneGeometry(0.9, 0.225);
    const uv = geo.attributes.uv;
    for (let k = 0; k < uv.count; k++) uv.setXY(k, uv.getX(k) * 0.5, 1 - (1 - uv.getY(k)) * 5 / 32);
    const m = new THREE.Mesh(geo, mat);
    m.position.x = -0.225 + 0.45;   // the tip sits at the group's origin side + 0.225
    m.rotation.x = i * Math.PI / 2;
    g.add(m);
  }
  const holder = new THREE.Group(); holder.add(g); g.position.x = -0.68;   // the tip at the origin, so a stuck arrow's origin is the hit point
  return holder;
}
// Points an arrow group (tip at origin, shaft along -x behind it) along a world direction.
const _a = new THREE.Vector3(), _x = new THREE.Vector3(1, 0, 0);
export function arrowAim(arrow, dir) { _a.copy(dir).normalize(); arrow.quaternion.setFromUnitVectors(_x, _a); }

// The 1.7.10 explosion (EntityHugeExplodeFX -> EntityLargeExplodeFX): grey puffs from entity/explosion.png, 16 frames
// in a 4 by 4 sheet, each about two blocks across, gone in a third of a second. Returns update(t).
export function explosionFX(R, t0, at, tx, { n = 14, spread = 2.2, seed = 3 } = {}) {
  const rnd = mulberry(seed), puffs = [];
  for (let i = 0; i < n; i++) {
    const t = tx.clone(); t.needsUpdate = true; t.repeat.set(0.25, 0.25);
    const g = 0.6 + rnd() * 0.4;
    const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: t, color: new THREE.Color(g, g, g), transparent: true, depthWrite: false, fog: false }));
    sp.visible = false; R.add(sp);
    puffs.push({ sp, t, at: [at[0] + (rnd() - 0.5) * spread * 2, at[1] + (rnd() - 0.2) * spread, at[2] + (rnd() - 0.5) * spread * 2], d: t0 + (i / n) * 0.35, life: 0.3 + rnd() * 0.2, s: 1.6 + rnd() * 1.4 });
  }
  return (t) => {
    for (const p of puffs) {
      const k = (t - p.d) / p.life;
      p.sp.visible = k >= 0 && k < 1;
      if (!p.sp.visible) continue;
      const fr = Math.min(15, Math.floor(k * 16));
      p.t.offset.set((fr % 4) * 0.25, 0.75 - Math.floor(fr / 4) * 0.25);
      R.at(p.sp, p.at[0], p.at[1], p.at[2]); p.sp.scale.setScalar(p.s * (1 - k * 0.2));
    }
  };
}
export function mulberry(seed) { let a = seed >>> 0; return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }

// Dropped items (EntityItem): sprites that pop out, fall, bounce and then spin and bob on the floor.
export function droppedItems(R, t0, from, texs, { seed = 9, speed = 3.2 } = {}) {
  const rnd = mulberry(seed);
  const items = texs.filter(Boolean).map((tx, i) => {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(0.3, 0.3), new THREE.MeshBasicMaterial({ map: tx, transparent: true, alphaTest: 0.1, side: THREE.DoubleSide, color: 0xb8b8b8 }));
    m.visible = false; R.add(m);
    const a = rnd() * Math.PI * 2, v = speed * (0.5 + rnd() * 0.6);
    return { m, d: t0 + i * 0.03, vx: Math.cos(a) * v, vz: Math.sin(a) * v, vy: 3 + rnd() * 2.5, ph: rnd() * 6 };
  });
  return (t) => {
    for (const it of items) {
      const dt = t - it.d;
      it.m.visible = dt >= 0;
      if (!it.m.visible) continue;
      // fly until it lands at y 0.1 (one small bounce), with drag
      const tl = (it.vy + Math.sqrt(it.vy * it.vy + 2 * 9.8 * (from[1] - 0.1))) / 9.8;
      const td = Math.min(dt, tl), drag = (1 - Math.exp(-td * 1.6)) / 1.6;
      let x = from[0] + it.vx * drag, z = from[2] + it.vz * drag, y = from[1] + it.vy * td - 4.9 * td * td;
      if (dt > tl) { const b = dt - tl; y = 0.1 + Math.max(0, 1.2 * b - 4.9 * b * b) + (b > 0.3 ? 0.1 + Math.sin((t + it.ph) * 3) * 0.05 : 0); }
      R.at(it.m, x, Math.max(0.1, y) + 0.12, z);
      it.m.rotation.set(0, R.yaw0 + (t + it.ph) * 2.2, 0);
    }
  };
}

// Billboard particles from particle/particles.png (16 x 16 tiles of 8 px): the 1.7.10 smoke (tiles 7 down to 0 as it
// ages, grey), spell swirls (row 8), crit, flame (tile 48), lava (49)... specs: { t0, at, v, life, size, tile|tiles,
// color, grav }. Returns update(t). Everything is a function of t.
export function particles(R, tx, specs) {
  const list = specs.map((p) => {
    const t = tx.clone(); t.needsUpdate = true; t.repeat.set(1 / 16, 1 / 16);
    const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: t, color: new THREE.Color(...(p.color || [0.6, 0.6, 0.6])), transparent: true, depthWrite: false, alphaTest: 0.05, fog: p.fog ?? true, blending: p.add ? THREE.AdditiveBlending : THREE.NormalBlending }));
    sp.visible = false; R.add(sp);
    return { ...p, sp, t };
  });
  return (t) => {
    for (const p of list) {
      const a = t - p.t0, k = a / p.life;
      p.sp.visible = k >= 0 && k < 1;
      if (!p.sp.visible) continue;
      const tile = p.tiles ? p.tiles[Math.min(p.tiles.length - 1, Math.floor(k * p.tiles.length))] : p.tile ?? Math.max(0, 7 - Math.floor(k * 8));
      p.t.offset.set((tile % 16) / 16, 1 - (Math.floor(tile / 16) + 1) / 16);
      const g = p.grav ?? -0.4, v = p.v || [0, 0, 0], drag = (1 - Math.exp(-a * 2)) / 2;
      R.at(p.sp, p.at[0] + v[0] * drag, p.at[1] + v[1] * drag - 0.5 * g * a * a, p.at[2] + v[2] * drag);
      p.sp.scale.setScalar(p.size * (p.grow ? 1 + k * p.grow : 1));
    }
  };
}
// A cloud of 1.7.10 smoke: n puffs around a point over a time window.
export function smoke(at, t0, n, { spread = 0.4, window = 0.4, life = 1.6, size = 0.3, rise = 0.6, seed = 4, dark = 0 } = {}) {
  const r = mulberry(seed), out = [];
  for (let i = 0; i < n; i++) {
    const g = (0.035 + r() * 0.08) * (1 - dark);   // linear: dark grey, as EntitySmokeFX (rand * 0.3, sRGB)
    out.push({ t0: t0 + r() * window, at: [at[0] + (r() - 0.5) * spread, at[1] + (r() - 0.5) * spread * 0.5, at[2] + (r() - 0.5) * spread], v: [(r() - 0.5) * 0.3, rise * (0.6 + r() * 0.6), (r() - 0.5) * 0.3], life: life * (0.7 + r() * 0.6), size: size * (0.7 + r() * 0.6), color: [g, g, g], grav: -0.15, grow: 0.6 });
  }
  return out;
}
