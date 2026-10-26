// Enderman: the stare. A tall figure at the end of the corridor, quite still, and the head will not look away from
// it. The stare. Each time the picture glitches it has teleported closer; then its face is over yours, the jaw drops
// and it screams. It takes hold of you and teleports, and you come out of it in the air beside it, on a ledge over a
// lava chasm. It lets go.
import { THREE, clamp, lerp, sstep, pulse, tex, loadImg, easeOut } from "./rig.js";
import { settle, shake, hitsOf, particles, mulberry, lensLimbs } from "./common.js";

const G = 32;   // Minecraft gravity, 0.08 blocks a tick squared, in m/s^2

// The chasm the Enderman takes you to: two jagged stone walls thirty blocks high over a lava lake, built as
// instanced blocks far under the Krypt (local y), lit only by the lava (instance colours, Minecraft face shading).
async function buildChasm(R, Y) {
  const names = ["stone", "cobblestone", "coal_ore", "iron_ore", "gravel", "obsidian"];
  const texs = await Promise.all(names.map((n) => tex("k:" + n)));
  const geo = new THREE.BoxGeometry(1, 1, 1);
  const shade = [], nrm = geo.attributes.normal;
  for (let i = 0; i < nrm.count; i++) { const ny = nrm.getY(i), nx = nrm.getX(i); const v = ny > 0.5 ? 1 : ny < -0.5 ? 0.5 : Math.abs(nx) > 0.5 ? 0.6 : 0.8; shade.push(v, v, v); }
  geo.setAttribute("color", new THREE.Float32BufferAttribute(shade, 3));
  const r = mulberry(91), cells = names.map(() => []);
  const n2 = (a, b) => { const s = Math.sin(a * 12.9898 + b * 78.233) * 43758.5453; return s - Math.floor(s); };
  for (const side of [-1, 1]) for (let z = -24; z <= 34; z++) for (let y = -2; y <= 30; y++) {
    const top = side < 0 ? 30 : 27 + Math.floor(n2(z, 7) * 3);
    if (y > top) continue;
    const d = 3 + Math.floor(n2(z * 0.5 + side * 31, y * 0.35) * 2.6);   // the face, ragged
    for (let k = 0; k < 6 - d + 1; k++) {
      const x = side * (d + k);
      const q = r(), b = y < 2 ? (q < 0.4 ? 5 : 0) : q < 0.82 ? 0 : q < 0.87 ? 1 : q < 0.92 ? 2 : q < 0.95 ? 3 : 4;
      cells[b].push([x, y, z]);
    }
  }
  // The ledge it stands on: the top of the left wall reaches out over the drop.
  for (let z = -1; z <= 3; z++) for (const x of [-2, -3]) cells[0].push([x, 30, z]);
  const group = new THREE.Group(); group.visible = false; R.add(group);
  const M = new THREE.Matrix4(), C = new THREE.Color(), P = new THREE.Vector3();
  names.forEach((n, i) => {
    const list = cells[i]; if (!list.length || !texs[i]) return;
    const mat = new THREE.MeshBasicMaterial({ map: texs[i], vertexColors: true });
    const im = new THREE.InstancedMesh(geo, mat, list.length);
    list.forEach(([x, y, z], j) => {
      R.L(x, Y + y + 0.5, z, P); P.x -= R.O.x; P.y -= R.O.y; P.z -= R.O.z;   // relative to O (the group sits at O)
      im.setMatrixAt(j, M.makeTranslation(P.x, P.y, P.z));
      const glow = 0.08 + 0.95 * Math.exp(-(y + 0.5) / 6.5) + 0.05 * n2(x, z);
      C.setRGB(0.05 + glow, 0.04 + glow * 0.5, 0.035 + glow * 0.25); im.setColorAt(j, C);
    });
    im.frustumCulled = false; group.add(im);
  });
  group.position.copy(R.O);
  // The lava lake: fullbright, the lava_still strip animated (20 frames).
  const img = await loadImg("k:lava_still");
  const frames = [];
  if (img) for (let f = 0; f < 20; f++) {
    const c = document.createElement("canvas"); c.width = c.height = 16;
    c.getContext("2d").drawImage(img, 0, f * 16, 16, 16, 0, 0, 16, 16);
    const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.magFilter = t.minFilter = THREE.NearestFilter; t.generateMipmaps = false;
    t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(16, 64); frames.push(t);
  }
  const lava = new THREE.Mesh(new THREE.PlaneGeometry(16, 64), new THREE.MeshBasicMaterial({ map: frames[0] || null, color: 0xffffff, fog: true }));
  lava.rotation.x = -Math.PI / 2; lava.rotation.z = -R.yaw0;
  const lp = R.L(0, Y + 0.875 - 0.001, 5); lava.position.set(lp.x - R.O.x, lp.y - R.O.y, lp.z - R.O.z);
  group.add(lava);
  return { group, animate(t) { if (frames.length) lava.material.map = frames[Math.floor(t * 10) % 20]; } };
}

export default {
  death: "Steve tried to swim in lava",
  async build(R) {
    const partTex = await tex("particles");
    const r = mulberry(R.seed * 3 + 17);
    const Y = -140;   // the lava, far under the Krypt
    const chasm = await buildChasm(R, Y);
    const E = R.mob("Enderman", { amb: [0.05, 0.05, 0.06], own: true });
    const z0 = clamp(R.ahead - 1.3, 3.5, 14);
    const T_IN = 1.0, T_STARE = 1.75, cuts = [2.45, 3.1, 3.65, 4.15], T_SCREAM = 4.22, T_GRAB = 4.55, T_TP = 4.9, T_LET = 5.3;
    const zF = 1.9, zs = [z0, lerp(z0, zF, 0.35), lerp(z0, zF, 0.62), lerp(z0, zF, 0.85), zF];
    const LEAN = 0.55, lean = (t) => (t >= T_SCREAM - 0.05 && t < T_TP ? LEAN * sstep(T_SCREAM - 0.05, T_SCREAM + 0.12, t) : 0);
    const edge = { x: -2.1, y: Y + 31, z: 1.0 };   // where it stands on the ledge
    const hang = { x: -0.95, y: Y + 31 + 1.35, z: 1.0 };   // where you hang in its hands
    const fallH = hang.y - (Y + 0.875 + 0.3);
    const T_LAVA = T_LET + Math.sqrt(2 * fallH / G), DUR = T_LAVA + 1.5;
    const hits = hitsOf([[4.62, 7, 1], [T_LAVA, 4, -1], [T_LAVA + 0.5, 4, 1], [DUR, 5, -1]]);
    const ez = (t) => { let i = 0; for (let k = 0; k < cuts.length; k++) if (t >= cuts[k]) i = k + 1; return zs[i]; };
    const inChasm = (t) => t >= T_TP;
    const epos = (t) => inChasm(t) ? edge : { x: 0, y: 0, z: ez(t) };

    // The head: drawn round to it and held there (a little give, as if pulling away); in the chasm, falling.
    // (its face: over you when it leans down to scream)
    const faceOf = (t) => { const p = epos(t), l = lean(t), d = Math.hypot(p.x, p.z) || 1; return { x: p.x - p.x / d * 2.6 * Math.sin(l), y: p.y + 2.6 * Math.cos(l), z: p.z - p.z / d * 2.6 * Math.sin(l) }; };
    const cam = (t) => {
      const s = settle(R, t, 0.9);
      if (!inChasm(t)) {
        const k = sstep(1.05, 1.9, t), f = faceOf(t), c0x = s.x * (1 - sstep(0.8, 1.3, t)), c0z = s.z * (1 - sstep(0.8, 1.3, t));
        const back = 0.12 * sstep(T_SCREAM, T_GRAB, t);
        const c = { x: c0x, y: s.y, z: c0z - back, yaw: lerp(s.yaw, R.yawTo(c0x, c0z, f.x, f.z), k), pitch: lerp(s.pitch, R.pitchTo(c0x, s.y, c0z - back, f.x, f.y, f.z), k), roll: 0,
          fov: s.fov - 10 * sstep(T_STARE, cuts[3], t) + 14 * sstep(T_SCREAM, T_SCREAM + 0.1, t) };
        c.yaw += Math.sin(t * 2.3) * 0.05 * sstep(T_STARE, T_STARE + 0.6, t);   // trying to look away
        c.pitch += Math.sin(t * 1.7 + 1) * 0.03 * sstep(T_STARE, T_STARE + 0.6, t);
        return shake(c, t, 0.0015 + 0.004 * sstep(T_STARE, cuts[3], t) + 0.03 * sstep(T_SCREAM, T_SCREAM + 0.05, t), 8);
      }
      // In the chasm: held, then let go; the drop (Minecraft gravity), the head tipping from its face to the lava.
      const dt = Math.max(0, t - T_LET), y = hang.y - 0.5 * G * dt * dt, f = faceOf(t);
      const x = lerp(hang.x, -0.2, sstep(T_LET, T_LAVA, t));
      const look = sstep(T_LET + 0.55, T_LAVA - 0.15, t);
      const drop = sstep(T_TP + 0.02, T_TP + 0.12, t) * (1 - sstep(T_TP + 0.32, T_TP + 0.44, t));   // a look straight down first
      const c = { x, y: Math.max(y, Y + 0.875 + 0.2), z: hang.z, fov: s.fov + 16 * sstep(T_LET, T_LAVA, t) };
      c.yaw = lerp(R.yawTo(hang.x, hang.z, f.x, f.z), R.yawTo(hang.x, hang.z, f.x, f.z) + 0.6, look);
      c.pitch = lerp(lerp(R.pitchTo(hang.x, hang.y, hang.z, f.x, f.y, f.z), -1.35, drop), -1.25, easeOut(look));
      c.roll = 0.25 * Math.sin(look * Math.PI);
      if (t >= T_LAVA) { c.pitch = lerp(-1.25, -0.1, sstep(T_LAVA, T_LAVA + 0.6, t)); c.y = Y + 0.875 + 0.2 - 0.25 * sstep(T_LAVA, T_LAVA + 0.4, t); }
      return shake(c, t, 0.004 + 0.02 * sstep(T_LET, T_LAVA, t) * (t < T_LAVA ? 1 : 0) + 0.03 * pulse(t, [T_TP, T_LAVA], 0.2), 8);
    };

    // Portal particles (EntityPortalFX: tiles 0-7, purple) round it at each teleport.
    const portal = [];
    for (const tt of [T_IN, ...cuts, T_TP]) for (let i = 0; i < 26; i++) {
      const p = tt === T_TP ? edge : { x: 0, y: 0, z: ez(tt) }, q = r() * 0.8 + 0.4;
      portal.push({ t0: tt - 0.1 + r() * 0.5, at: [p.x + (r() - 0.5) * 1.1, p.y + r() * 2.9, p.z + (r() - 0.5) * 1.1], v: [(r() - 0.5) * 0.8, -0.4 + r() * 0.5, (r() - 0.5) * 0.8], life: 0.7 + r() * 0.6, size: 0.07 + r() * 0.05, tile: Math.floor(r() * 8), color: [q * 0.9, q * 0.3, q], grav: 0, fog: false });
    }
    // Lava pops (tile 49) rising off the lake.
    for (let i = 0; i < 40; i++) portal.push({ t0: T_TP + r() * (DUR - T_TP), at: [(r() - 0.5) * 5, Y + 0.9, hang.z + (r() - 0.5) * 8], v: [(r() - 0.5) * 0.6, 2 + r() * 2, (r() - 0.5) * 0.6], life: 1.2, size: 0.12, tile: 49, color: [1, 0.7, 0.35], grav: 5, fog: false, add: true });
    const parts = particles(R, partTex, portal);
    // Its arms close over the lens as it takes hold; they let go over the drop.
    const arms = lensLimbs(R, E, "rightArm", [
      { from: [-0.5, 0.45], to: [-0.16, 0.02], t0: T_GRAB, t1: T_GRAB + 0.18, scale: 0.42, z: -0.3, twist: 0.04, t2: T_LET - 0.05, t3: 0.25 },
      { from: [0.5, 0.45], to: [0.17, 0.0], t0: T_GRAB + 0.04, t1: T_GRAB + 0.22, scale: 0.42, z: -0.31, twist: 0.04, t2: T_LET - 0.03, t3: 0.25 }
    ], { color: 0x3a3a3a });
    const lavaLight = R.ownLight(R.light(0xff7a20, 0, 26, 1.0));
    const sounds = [
      [T_IN, "mob.endermen.portal", { at: [0, 1.5, z0], volume: 0.5, pitch: 0.9 }],
      [1.3, "mob.endermen.idle", { at: [0, 2.6, z0], volume: 0.6, pitch: 0.8, reverb: 0.6 }],
      [T_STARE, "mob.endermen.stare", { volume: 1 }],
      ...cuts.map((tt, i) => [tt, "mob.endermen.portal", { at: [0, 1.5, zs[i + 1]], volume: 0.7 + 0.08 * i, pitch: 1.1 - 0.06 * i }]),
      ...cuts.slice(1).map((tt, i) => [tt + 0.02, "qf.scare.whisper", { volume: 0.25 + 0.1 * i }]),
      [T_SCREAM, "mob.endermen.scream", { at: [0, 2.6, 0.72], volume: 1 }], [T_SCREAM + 0.01, "qf.scare.shriek", { volume: 0.8 }], [T_SCREAM, "qf.scare.stinger", { volume: 1 }],
      [4.62, "game.player.hurt"], [4.63, "qf.scare.hit", { volume: 0.9 }],
      [T_TP - 0.02, "mob.endermen.portal", { volume: 1, pitch: 0.8 }], [T_TP, "portal.travel", { volume: 0.25, pitch: 1.6 }],
      [T_TP + 0.15, "mob.endermen.idle", { at: [edge.x, edge.y + 2.6, edge.z], volume: 0.9, pitch: 0.7 }],
      [T_LET, "qf.scare.fall", { volume: 1 }], [T_LET + 0.1, "qf.scare.scream", { volume: 1 }],
      [T_LET + 0.4, "mob.endermen.scream", { at: [edge.x, edge.y + 2.6, edge.z], volume: 0.7, pitch: 0.8 }],
      [T_LAVA, "liquid.lavapop", { volume: 1 }], [T_LAVA + 0.01, "random.fizz", { volume: 1 }], [T_LAVA + 0.02, "qf.scare.hit", { volume: 0.9 }],
      [T_LAVA, "game.player.hurt"], [T_LAVA + 0.5, "game.player.hurt"], [T_LAVA + 0.52, "random.fizz", { volume: 0.7 }],
      [T_LAVA + 0.3, "qf.scare.scream", { volume: 0.9, pitch: 1.1 }],
      [DUR, "game.player.die"], [DUR, "@muffle", { hz: 300, s: 3 }]
    ];
    const loops = [
      [0.5, T_TP, "qf.scare.heartbeat", { volume: 0.55, fadeOut: 0.05 }],
      [T_STARE, T_TP, "qf.scare.drone", { volume: 0.6, fadeIn: 1.5, fadeOut: 0.05, pitch: 0.75 }],
      [T_TP, DUR + 0.5, "liquid.lava", { volume: 0.7, fadeIn: 0.3 }],
      [T_LAVA, DUR + 0.5, "fire.fire", { volume: 0.9, fadeIn: 0.05 }]
    ];

    function update(t, f) {
      const p = epos(t), camNow = cam(t);
      E.pivot.visible = t >= T_IN;
      const screaming = t >= T_SCREAM && t < T_LET + 1.2;
      R.place(E, p.x, p.y, p.z, R.yawTo(p.x, p.z, camNow.x, camNow.z), -lean(t));
      E.anim(t, 0, { walk: 0, screaming, enderJitter: screaming ? 1 : 0, lookPitch: inChasm(t) ? 0.5 * sstep(T_LET, T_LET + 0.5, t) : (t > cuts[3] ? -0.25 + 0.75 * sstep(T_SCREAM - 0.05, T_SCREAM + 0.12, t) : 0) });
      // ModelEnderman lifts only the top of the head when it screams; the jaw (the hat layer) stays.
      if (screaming && E.parts.headwear) E.parts.headwear.position.y -= 5 / 16;
      if (inChasm(t)) { const a = E.parts.rightArm, b = E.parts.leftArm; const hold = 1 - sstep(T_LET, T_LET + 0.3, t); if (a) { a.rotation.x = 1.3 * hold; b.rotation.x = 1.3 * hold; } }
      E.setOwn(inChasm(t) ? 0.12 : 0.05 + 0.08 * sstep(cuts[2], T_SCREAM, t));
      arms(t); parts(t);
      chasm.group.visible = inChasm(t);
      if (chasm.group.visible) chasm.animate(t);
      R.L(0, Y + 3, hang.z, lavaLight.position); lavaLight.intensity = inChasm(t) ? 2.5 : 0;
      const g = Math.max(...[T_IN, ...cuts, T_TP].map((tt) => (t >= tt - 0.05 && t < tt + 0.1 ? 1 - Math.abs(t - tt - 0.02) / 0.08 : 0)));
      f.glitch = Math.max(0, g);
      if (!inChasm(t)) {
        const st = sstep(T_STARE, cuts[3], t);
        f.env = { bake: 1 - 0.25 * sstep(0.2, 1.2, t) - 0.25 * st, lights: 1 - 0.35 * st, fogMul: 1 + 0.8 * st, fog: [0.08, 0.02, 0.1, 0.5 * st] };
        f.tints = [[80, 0, 110, 0.06 * st + 0.35 * pulse(t, [T_TP - 0.05], 0.12)]];
        f.vig = [20, 0, 30, 0.3 + 0.35 * st]; f.vigR = 0.9 - 0.15 * st;
      } else {
        const lv = sstep(T_LAVA, T_LAVA + 0.08, t);
        f.env = { bake: 1, lights: 0, fogMul: 0.7, fogAdd: 2.5 * lv, fog: lv > 0 ? [0.6, 0.1, 0, 1] : [0.22, 0.07, 0.02, 1], noParticles: true };
        f.tints = [[80, 0, 110, 0.4 * (1 - sstep(T_TP, T_TP + 0.25, t))], [255, 80, 0, 0.35 * lv]];
        f.vig = [40, 10, 0, 0.3 + 0.3 * lv]; f.vigR = 0.9;
        f.fire = lv;
      }
      f.black = 0.3 * sstep(DUR - 0.2, DUR + 0.6, t);
    }
    return { dur: DUR, hits, cam, update, sounds, loops, deathSide: 1, notes: { z0, T_LAVA: +T_LAVA.toFixed(2), fallH: +fallH.toFixed(1) } };
  }
};
