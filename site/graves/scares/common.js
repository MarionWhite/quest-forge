// Pieces several scares share: the freeze (the head settles where the walk stopped), the fall to the floor,
// timing helpers, and the hearts' damage bookkeeping.
import { THREE, track, clamp, lerp, sstep, wobble, loadImg } from "./rig.js";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";

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
// the world. specs: [{ from: [x, y], to: [x, y], z, t0, t1, scale, t2? }] in view metres (x right, y up, z forward < 0);
// from t2 they withdraw again.
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
      const k = sstep(s.t0, s.t1, t) * (s.t2 != null ? 1 - sstep(s.t2, s.t2 + (s.t3 ?? 0.3), t) : 1);   // t2: let go
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

// A splash potion's item texture (ItemPotion: the overlay in the potion's colour under the bottle), as a texture.
export async function potionTex(hex) {
  const [bottle, over] = await Promise.all([loadImg("item_potion_bottle_splash"), loadImg("item_potion_overlay")]);
  const c = document.createElement("canvas"); c.width = c.height = 16;
  const x = c.getContext("2d");
  if (over) {
    x.drawImage(over, 0, 0);
    x.globalCompositeOperation = "multiply"; x.fillStyle = "#" + hex.toString(16).padStart(6, "0"); x.fillRect(0, 0, 16, 16);
    x.globalCompositeOperation = "destination-in"; x.drawImage(over, 0, 0); x.globalCompositeOperation = "source-over";
  }
  if (bottle) x.drawImage(bottle, 0, 0);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace; t.magFilter = THREE.NearestFilter; t.minFilter = THREE.NearestFilter; t.generateMipmaps = false;
  return t;
}
// The spell particles a splash potion leaves (EntitySpellParticleFX: tiles 128 to 135, counting down, in the colour).
export function spell(at, t0, n, rgb, { spread = 0.8, rise = 0.9, life = 1.2, size = 0.12, seed = 6, window = 0.15 } = {}) {
  const r = mulberry(seed), out = [];
  for (let i = 0; i < n; i++) {
    const a = r() * Math.PI * 2, d = r() * spread;
    out.push({ t0: t0 + r() * window, at: [at[0] + Math.cos(a) * d, at[1] + r() * 0.3, at[2] + Math.sin(a) * d], v: [Math.cos(a) * 0.4, rise * (0.5 + r()), Math.sin(a) * 0.4],
      life: life * (0.6 + r() * 0.7), size: size * (0.7 + r() * 0.6), tiles: [135, 134, 133, 132, 131, 130, 129, 128], color: rgb.map((c) => c * (0.75 + r() * 0.25)), grav: -0.3, fog: false });
  }
  return out;
}

// Fire blocks (RenderBlocks.renderBlockFire, simplified to its crossed planes) with the animated fire_layer_0 strip.
// spots: [{ at: [x, y, z], t0, t1? }]. Returns update(t).
export async function fireBlocks(R, spots) {
  const img = await loadImg("k:fire_layer_0");
  const c = document.createElement("canvas"); c.width = c.height = 16;
  const x = c.getContext("2d"); x.imageSmoothingEnabled = false;
  const tx = new THREE.CanvasTexture(c);
  tx.colorSpace = THREE.SRGBColorSpace; tx.magFilter = THREE.NearestFilter; tx.minFilter = THREE.NearestFilter; tx.generateMipmaps = false;
  const mat = new THREE.MeshBasicMaterial({ map: tx, transparent: true, alphaTest: 0.1, side: THREE.DoubleSide, depthWrite: false, color: 0xffffff });
  const fires = spots.map((s) => {
    const g = new THREE.Group();
    for (let i = 0; i < 4; i++) { const m = new THREE.Mesh(new THREE.PlaneGeometry(1, 1.4), mat); m.position.y = 0.7; m.rotation.y = i * Math.PI / 4; g.add(m); }
    g.visible = false; R.add(g); return { ...s, g };
  });
  let last = -1;
  return (t) => {
    const fr = Math.floor(t * 20) % 32;
    if (fr !== last && img) { last = fr; x.clearRect(0, 0, 16, 16); x.drawImage(img, 0, fr * 16, 16, 16, 0, 0, 16, 16); tx.needsUpdate = true; }
    for (const f of fires) {
      const on = t >= f.t0 && (f.t1 == null || t < f.t1);
      f.g.visible = on; if (!on) continue;
      R.at(f.g, f.at[0], f.at[1], f.at[2]); f.g.rotation.y = R.yaw0;
      f.g.scale.setScalar((f.s ?? 1) * Math.min(1, (t - f.t0) / 0.15));
    }
  };
}

// The held item in first person (ItemRenderer.renderItemInFirstPerson for a full-3D item like a sword), with the swing:
// progress 0..1 over 6 ticks. Returns update(t, swingStarts[]) that places it in the head's frame.
export function heldItem(R, tx, { color = 0x8c8c8c } = {}) {
  const geo = new THREE.PlaneGeometry(1, 1); geo.translate(0.5, 0.5, 0);
  const uv = geo.attributes.uv; for (let i = 0; i < uv.count; i++) uv.setX(i, 1 - uv.getX(i));
  const mesh = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ map: tx, transparent: true, alphaTest: 0.1, side: THREE.DoubleSide, depthTest: false, depthWrite: false, fog: false, color }));
  mesh.renderOrder = 2200; mesh.matrixAutoUpdate = false;
  R.view.add(mesh);
  const D = Math.PI / 180, M = new THREE.Matrix4(), T = new THREE.Matrix4();
  const mul = (m) => M.multiply(m);
  // The hand is drawn with its own 70 degree projection in Minecraft: keep it there whatever the camera's FOV.
  return (t, swings = [], hide = false, fov = R.camera.fov) => {
    mesh.visible = !hide; if (hide) return;
    const kf = Math.tan(fov * D / 2) / Math.tan(35 * D);
    let p = 0;
    for (const s of swings) if (t >= s && t < s + 0.3) p = (t - s) / 0.3;
    const f6a = Math.sin(p * Math.PI), f7 = Math.sin(Math.sqrt(p) * Math.PI), f6 = Math.sin(p * p * Math.PI);
    M.makeScale(kf, kf, 1);
    mul(T.makeTranslation(-f7 * 0.4, Math.sin(Math.sqrt(p) * Math.PI * 2) * 0.2, -f6a * 0.2));
    mul(T.makeTranslation(0.7 * 0.8, -0.65 * 0.8, -0.9 * 0.8));
    mul(T.makeRotationY(45 * D));
    mul(T.makeRotationY(-f6 * 20 * D)); mul(T.makeRotationZ(-f7 * 20 * D)); mul(T.makeRotationX(-f7 * 80 * D));
    mul(T.makeScale(0.4, 0.4, 0.4));
    mul(T.makeTranslation(0, -0.3, 0)); mul(T.makeScale(1.5, 1.5, 1.5));
    mul(T.makeRotationY(50 * D)); mul(T.makeRotationZ(335 * D)); mul(T.makeTranslation(-0.9375, -0.0625, 0));
    mesh.matrix.copy(M); mesh.matrixWorldNeedsUpdate = true;
  };
}

// A soft round glow (additive halos: eyes in the dark, embers).
let _glow = null;
export function glowTex() {
  if (_glow) return _glow;
  const c = document.createElement("canvas"); c.width = c.height = 64;
  const g = c.getContext("2d"), gr = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  gr.addColorStop(0, "rgba(255,255,255,1)"); gr.addColorStop(0.2, "rgba(255,255,255,0.45)"); gr.addColorStop(0.55, "rgba(255,255,255,0.08)"); gr.addColorStop(1, "rgba(255,255,255,0)");
  g.fillStyle = gr; g.fillRect(0, 0, 64, 64);
  _glow = new THREE.CanvasTexture(c);
  return _glow;
}
// A camera-facing additive halo in the scene (world space), placed each frame by the caller.
export function halo(R, color, size = 0.5) {
  const m = new THREE.Mesh(new THREE.PlaneGeometry(size, size), new THREE.MeshBasicMaterial({ map: glowTex(), color, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, fog: false, opacity: 0 }));
  m.onBeforeRender = function (r, s, cam) { this.quaternion.copy(cam.quaternion); this.updateMatrixWorld(); };
  m.renderOrder = 5;
  return R.add(m);
}
// Swing progress 0..1 of an arm swing (6 ticks) started at any of the given times, else 0.
export function swingAt(t, starts, len = 0.3) {
  for (const s of starts) if (t >= s && t < s + len) return (t - s) / len;
  return 0;
}
// Set a model part's rotation from Minecraft angles (the library's parts are a half turn about z from MC's).
export const mcRot = (g, x, y, z) => { if (g) g.rotation.set(-x, -y, z, "ZYX"); };
// ModelZombie.setRotationAngles (zombies and pigmen): arms out, the swing pulls both down and in; ModelBiped's swing
// twists the body and moves the shoulders. p is the swing progress (onGround), t the age clock.
export function zombieArms(m, t, p = 0) {
  const P = m.parts; if (!P.rightArm) return;
  const age = t * 20, body = Math.sin(Math.sqrt(p) * Math.PI * 2) * 0.2;
  if (P.body) mcRot(P.body, 0, body, 0);
  P.rightArm.position.set(Math.cos(body) * 5 / 16, -2 / 16, Math.sin(body) * 5 / 16);
  P.leftArm.position.set(-Math.cos(body) * 5 / 16, -2 / 16, -Math.sin(body) * 5 / 16);
  const f6 = Math.sin(p * Math.PI), f7 = Math.sin((1 - (1 - p) * (1 - p)) * Math.PI);
  const bx = Math.sin(age * 0.067) * 0.05, bz = Math.cos(age * 0.09) * 0.05 + 0.05;
  const ax = -Math.PI / 2 - (f6 * 1.2 - f7 * 0.4);
  mcRot(P.rightArm, ax + bx, -(0.1 - f6 * 0.6), bz);
  mcRot(P.leftArm, ax - bx, 0.1 - f6 * 0.6, -bz);
}

// Eyes that glow in the dark: pixel quads on a mob's head part (Minecraft model units: x, y, z, w, h on the face,
// y down, front -z) plus a halo in the scene. Returns set(on 0..1). rgb is the lit colour.
export function glowEyes(R, m, px, rgb = [1, 0.1, 0.05], { halo: hs = 0.4, glow = 0.3, scale = 1 } = {}) {
  const head = m.parts.head;
  const mat = new THREE.MeshBasicMaterial({ color: 0x000000, fog: false, side: THREE.DoubleSide, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2 });
  mat.userData.noFlash = true;
  const eyes = px.map(([x, y, z, w, h]) => { const q = new THREE.Mesh(new THREE.PlaneGeometry(w / 16, h / 16), mat); q.position.set(-x / 16, -y / 16, z / 16); q.visible = false; if (head) head.add(q); return q; });
  const hl = halo(R, new THREE.Color(rgb[0], rgb[1], rgb[2]), hs);
  const cy = -px.reduce((a, e) => a + e[1], 0) / px.length / 16, cz = Math.min(...px.map((e) => e[2])) / 16 - 0.05;
  const hp = new THREE.Vector3();
  return (on) => {
    const vis = on > 0.01 && !!head && m.pivot.visible;
    for (const e of eyes) e.visible = vis;
    hl.visible = vis;
    if (!vis) return;
    mat.color.setRGB(rgb[0] * on, rgb[1] * on, rgb[2] * on);
    hl.material.opacity = glow * on;
    m.pivot.updateMatrixWorld(true);
    head.localToWorld(hp.set(0, cy, cz));
    hl.position.copy(hp); hl.scale.setScalar(scale);
  };
}
// ModelBiped's arm swing (onGround p 0..1) on top of the pose the library's anim left: the body twists, the right arm
// chops down and across.
export function bipedSwing(m, p) {
  const P = m.parts; if (!P.rightArm || p <= 0) return;
  const body = Math.sin(Math.sqrt(p) * Math.PI * 2) * 0.2;
  if (P.body) mcRot(P.body, 0, body, 0);
  P.rightArm.position.set(Math.cos(body) * 5 / 16, -2 / 16, Math.sin(body) * 5 / 16);
  P.leftArm.position.set(-Math.cos(body) * 5 / 16, -2 / 16, -Math.sin(body) * 5 / 16);
  const mx = (g) => -g.rotation.x, my = (g) => -g.rotation.y;
  let f6 = 1 - p; f6 *= f6; f6 *= f6; f6 = 1 - f6;
  const f7 = Math.sin(f6 * Math.PI), hx = P.head ? -P.head.rotation.x : 0, f8 = Math.sin(p * Math.PI) * -(hx - 0.7) * 0.75;
  mcRot(P.rightArm, mx(P.rightArm) - (f7 * 1.2 + f8), my(P.rightArm) + body * 3, Math.sin(p * Math.PI) * -0.4);
  mcRot(P.leftArm, mx(P.leftArm) + body, my(P.leftArm) + body, P.leftArm.rotation.z);
}

// A library mob's animation baked into n poses over one period (anim time), one merged geometry per material layer
// per pose, so a swarm of it costs (layers x n) draw calls. Returns { layers: [{ mat, poses }], mob }.
export function bakePoses(R, id, { n = 8, period = 1, anim = {}, amb = [0.2, 0.2, 0.2], mob = {} } = {}) {
  const m = R.mob(id, { amb, ...mob });
  m.pivot.visible = false;
  const inv = new THREE.Matrix4(), rel = new THREE.Matrix4(), layers = new Map();
  for (let k = 0; k < n; k++) {
    m.anim((k / n) * period, 0, anim);
    m.pivot.updateMatrixWorld(true);
    inv.copy(m.root.matrixWorld).invert();
    const byMat = new Map();
    m.root.traverse((o) => {
      if (!o.isMesh || !o.visible) return;
      const mat = Array.isArray(o.material) ? o.material[0] : o.material;
      const g = o.geometry.clone(); g.applyMatrix4(rel.multiplyMatrices(inv, o.matrixWorld));
      if (!byMat.has(mat)) byMat.set(mat, []);
      byMat.get(mat).push(g);
    });
    for (const [mat, gs] of byMat) { if (!layers.has(mat)) layers.set(mat, []); layers.get(mat).push(mergeGeometries(gs, false)); for (const g of gs) g.dispose(); }
  }
  return { layers: [...layers].map(([mat, poses]) => ({ mat, poses })), mob: m };
}
// Instanced copies of baked poses: begin() each frame, put(pose, x, y, z, yaw, pitch, roll, scale) in local terms, end().
export function swarm(R, baked, cap) {
  const ims = baked.layers.map((L) => L.poses.map((g) => { const im = new THREE.InstancedMesh(g, L.mat, cap); im.count = 0; im.frustumCulled = false; return R.add(im); }));
  const M = new THREE.Matrix4(), Q = new THREE.Quaternion(), E = new THREE.Euler(), P = new THREE.Vector3(), S = new THREE.Vector3();
  const n = baked.layers[0] ? baked.layers[0].poses.length : 0;
  return {
    n,
    begin() { for (const row of ims) for (const im of row) im.count = 0; },
    put(pose, x, y, z, yaw = 0, pitch = 0, roll = 0, scale = 1) {
      R.L(x, y, z, P); E.set(pitch, R.yaw0 + yaw, roll, "YXZ"); Q.setFromEuler(E); S.setScalar(scale); M.compose(P, Q, S);
      for (const row of ims) { const im = row[pose % row.length]; if (im.count < cap) im.setMatrixAt(im.count++, M); }
    },
    end() { for (const row of ims) for (const im of row) im.instanceMatrix.needsUpdate = true; }
  };
}
// Cobweb blocks as the 1.7.10 draws them (RenderBlocks crossed squares), web.png, at local block centres.
export function webs(R, webTex, spots, { color = 0xb0b0b0 } = {}) {
  const mat = new THREE.MeshLambertMaterial({ map: webTex, side: THREE.DoubleSide, alphaTest: 0.1, color });
  if (R.patchBake) R.patchBake(mat, { fixed: new THREE.Vector3(0.12, 0.12, 0.12) });
  const g = new THREE.PlaneGeometry(1.41, 1);
  for (const p of spots) {
    for (const a of [Math.PI / 4, -Math.PI / 4]) { const q = new THREE.Mesh(g, mat); R.at(q, p[0], p[1], p[2]); q.rotation.y = R.yaw0 + a; R.add(q); }
  }
}
