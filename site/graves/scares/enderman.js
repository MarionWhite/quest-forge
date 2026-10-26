// Enderman: the stare. A tall figure at the end of the corridor, quite still, and the head will not look away from
// it. Each time the picture glitches it has teleported closer. Then, a coin toss: the cuts walk it right up to you, or
// a cut leaves the corridor empty. The view is let go and searches, left, right; one frame of static has its face in
// it. Silence. Then it is there, leaning down over you, jaw dropped, screaming into the lens. It takes hold of you and
// teleports, and you come out of it in the air beside it, on a ledge over a lava chasm. It lets go.
import { THREE, clamp, lerp, sstep, pulse, tex, loadImg, easeOut } from "./rig.js";
import { settle, shake, hitsOf, particles, mulberry, lensLimbs, halo } from "./common.js";
import { lunge, lungeFx, screech, faceAnchor, boxOf, silence, deathScream, glimpse, jit } from "./fnaf.js";

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
    E.anim(0, 0, { walk: 0 }); R.place(E, 0, 0, 4, Math.PI);
    const anchor = faceAnchor(E, E.parts.head, boxOf("enderman", "bipedHead")); anchor.y += 0.2;   // the head lifts 5 px off the jaw to scream: aim at the eyes, the jaw hanging below them
    const z0 = clamp(R.ahead - 1.3, 3.5, 14);
    // ---- the dice -------------------------------------------------------------------------------------------
    const vanish = R.chance(0.55);
    const T_IN = 1.0, T_STARE = 1.75;
    const nCuts = 2 + Math.floor(R.rand() * 3);
    const cuts = []; let tc = T_STARE + R.vary(0.7, 0.3);
    for (let i = 0; i < nCuts; i++) { cuts.push(tc); tc += R.vary(0.6, 0.45); }
    const zF = 1.9, zs = [z0, ...cuts.map((_, i) => lerp(z0, zF, (i + 1) / (nCuts + (vanish ? 1.6 : 0.4))))];
    let t0, tGone = null, tFlash = [], tSil;
    if (vanish) {
      tGone = tc;                                  // the last cut leaves the corridor empty
      tSil = tGone + 0.1;
      const search = R.vary(2.0, 0.4);
      tFlash = [tGone + search * R.vary(0.45, 0.4)];
      t0 = tGone + search;
    } else { tSil = cuts[nCuts - 1] + 0.15; t0 = tc + R.vary(0.25, 0.5); }
    const L = lunge(R, E, { t0, rush: R.vary(0.2, 0.15), hold: R.vary(0.7, 0.15), dist: 0.74, anchor, seed: 19, rise: -0.4 });
    const tK = L.t3, T_GRAB = tK + 0.02, T_TP = tK + 0.4, T_LET = T_TP + 0.4;
    const edge = { x: -2.1, y: Y + 31, z: 1.0 };
    const hang = { x: -0.95, y: Y + 31 + 1.35, z: 1.0 };
    const fallH = hang.y - (Y + 0.875 + 0.3);
    const T_LAVA = T_LET + Math.sqrt(2 * fallH / G), DUR = T_LAVA + 1.5;
    const hits = hitsOf([[T_GRAB, 7, 1], [T_LAVA, 4, -1], [T_LAVA + 0.5, 4, 1], [DUR, 5, -1]]);
    const ez = (t) => { let i = 0; for (let k = 0; k < cuts.length; k++) if (t >= cuts[k]) i = k + 1; return zs[i]; };
    const inChasm = (t) => t >= T_TP;
    const near = { x: 0, y: 0, z: 1.15 };           // where it is when it comes (out of nothing, at arm's length)
    const epos = (t) => inChasm(t) ? edge : (t >= t0 ? near : { x: 0, y: 0, z: ez(t) });
    const faceOf = (t) => { const p = epos(t); return { x: p.x, y: p.y + 2.6, z: p.z }; };
    // The look: drawn round to it and held (a little give, as if pulling away); after it vanishes, searching.
    const search = (t) => tGone == null || t < tGone ? 0 : sstep(tGone + 0.2, tGone + 0.9, t);
    const cam = (t) => {
      const s = settle(R, t, 0.9);
      if (!inChasm(t)) {
        const k = sstep(1.05, 1.9, t), f = faceOf(Math.min(t, tGone ?? t)), c0x = s.x * (1 - sstep(0.8, 1.3, t)), c0z = s.z * (1 - sstep(0.8, 1.3, t));
        const c = { x: c0x, y: s.y, z: c0z, yaw: lerp(s.yaw, R.yawTo(c0x, c0z, f.x, f.z), k), pitch: lerp(s.pitch, R.pitchTo(c0x, s.y, c0z, f.x, f.y, f.z), k), roll: 0,
          fov: s.fov - 10 * sstep(T_STARE, cuts[nCuts - 1], t) * (1 - search(t)) + 10 * pulse(t, [L.t1], 0.12), near: t >= t0 ? 0.02 : undefined };
        c.yaw += Math.sin(t * 2.3) * 0.05 * sstep(T_STARE, T_STARE + 0.6, t);
        c.pitch += Math.sin(t * 1.7 + 1) * 0.03 * sstep(T_STARE, T_STARE + 0.6, t);
        // searching: left, right, back to the middle, slowly, breathing
        const sr = search(t);
        if (sr > 0) { const u = (t - tGone) / Math.max(0.5, t0 - tGone); c.yaw = lerp(c.yaw, 0.65 * Math.sin(u * Math.PI * 1.6) * (1 - 0.5 * u), sr); c.pitch = lerp(c.pitch, -0.05, sr); }
        if (t >= t0) { const kk = sstep(t0, L.t1, t); c.pitch = lerp(c.pitch, 0.35, kk); c.yaw = lerp(c.yaw, 0, kk); }   // it is above you: the head jerks up to it
        return shake(c, t, 0.0015 + 0.004 * sstep(T_STARE, cuts[nCuts - 1], t) + L.shake(t), 8);
      }
      const dt = Math.max(0, t - T_LET), y = hang.y - 0.5 * G * dt * dt, f = faceOf(t);
      const x = lerp(hang.x, -0.2, sstep(T_LET, T_LAVA, t));
      const look = sstep(T_LET + 0.55, T_LAVA - 0.15, t);
      const drop = sstep(T_TP + 0.02, T_TP + 0.12, t) * (1 - sstep(T_TP + 0.32, T_TP + 0.44, t));
      const c = { x, y: Math.max(y, Y + 0.875 + 0.2), z: hang.z, fov: s.fov + 16 * sstep(T_LET, T_LAVA, t) };
      c.yaw = lerp(R.yawTo(hang.x, hang.z, f.x, f.z), R.yawTo(hang.x, hang.z, f.x, f.z) + 0.6, look);
      c.pitch = lerp(lerp(R.pitchTo(hang.x, hang.y, hang.z, f.x, f.y, f.z), -1.35, drop), -1.25, easeOut(look));
      c.roll = 0.25 * Math.sin(look * Math.PI);
      if (t >= T_LAVA) { c.pitch = lerp(-1.25, -0.1, sstep(T_LAVA, T_LAVA + 0.6, t)); c.y = Y + 0.875 + 0.2 - 0.25 * sstep(T_LAVA, T_LAVA + 0.4, t); }
      return shake(c, t, 0.004 + 0.02 * sstep(T_LET, T_LAVA, t) * (t < T_LAVA ? 1 : 0) + 0.03 * pulse(t, [T_TP, T_LAVA], 0.2), 8);
    };

    const portal = [];
    for (const tt of [T_IN, ...cuts, ...(tGone ? [tGone] : []), t0, T_TP]) for (let i = 0; i < 26; i++) {
      const p = tt === T_TP ? edge : tt === t0 ? near : { x: 0, y: 0, z: ez(tt - 0.01) }, q = r() * 0.8 + 0.4;
      portal.push({ t0: tt - 0.1 + r() * 0.5, at: [p.x + (r() - 0.5) * 1.1, p.y + r() * 2.9, p.z + (r() - 0.5) * 1.1], v: [(r() - 0.5) * 0.8, -0.4 + r() * 0.5, (r() - 0.5) * 0.8], life: 0.7 + r() * 0.6, size: 0.07 + r() * 0.05, tile: Math.floor(r() * 8), color: [q * 0.9, q * 0.3, q], grav: 0, fog: false });
    }
    for (let i = 0; i < 40; i++) portal.push({ t0: T_TP + r() * (DUR - T_TP), at: [(r() - 0.5) * 5, Y + 0.9, hang.z + (r() - 0.5) * 8], v: [(r() - 0.5) * 0.6, 2 + r() * 2, (r() - 0.5) * 0.6], life: 1.2, size: 0.12, tile: 49, color: [1, 0.7, 0.35], grav: 5, fog: false, add: true });
    const parts = particles(R, partTex, portal);
    const arms = lensLimbs(R, E, "rightArm", [
      { from: [-0.5, 0.45], to: [-0.16, 0.02], t0: T_GRAB, t1: T_GRAB + 0.18, scale: 0.42, z: -0.3, twist: 0.04, t2: T_LET - 0.05, t3: 0.25 },
      { from: [0.5, 0.45], to: [0.17, 0.0], t0: T_GRAB + 0.04, t1: T_GRAB + 0.22, scale: 0.42, z: -0.31, twist: 0.04, t2: T_LET - 0.03, t3: 0.25 }
    ], { color: 0x3a3a3a });
    const lavaLight = R.ownLight(R.light(0xff7a20, 0, 26, 1.0));
    const eyeGlow = [halo(R, new THREE.Color(0.85, 0.3, 1), 0.3), halo(R, new THREE.Color(0.85, 0.3, 1), 0.3)];
    const S2 = screech(L, [["mob.endermen.scream", { pitch: 0.85 }], ["mob.endermen.stare", { pitch: 0.9, volume: 1.2 }]]);
    const sounds = [
      [T_IN, "mob.endermen.portal", { at: [0, 1.5, z0], volume: 0.5, pitch: 0.9 }],
      [1.3, "mob.endermen.idle", { at: [0, 2.6, z0], volume: 0.6, pitch: 0.8, reverb: 0.6 }],
      [T_STARE, "mob.endermen.stare", { volume: 1 }],
      ...cuts.map((tt, i) => [tt, "mob.endermen.portal", { at: [0, 1.5, zs[i + 1]], volume: 0.7 + 0.08 * i, pitch: 1.1 - 0.06 * i }]),
      ...cuts.slice(1).map((tt, i) => [tt + 0.02, "qf.scare.whisper", { volume: 0.25 + 0.1 * i }]),
      ...(tGone ? [[tGone, "mob.endermen.portal", { at: [0, 1.5, zs[zs.length - 1]], volume: 1, pitch: 0.7 }]] : []),
      silence(tSil, { fade: 0.08 }),
      ...tFlash.map((tt) => [tt, "qf.scare.hit", { volume: 0.35 }]),
      ...S2.sounds,
      [T_GRAB, "game.player.hurt"],
      [T_TP - 0.02, "mob.endermen.portal", { volume: 1, pitch: 0.8 }], [T_TP, "portal.travel", { volume: 0.25, pitch: 1.6 }],
      [T_TP + 0.15, "mob.endermen.idle", { at: [edge.x, edge.y + 2.6, edge.z], volume: 0.9, pitch: 0.7 }],
      [T_LET, "qf.scare.fall", { volume: 1 }], ...deathScream(T_LET + 0.08, { volume: 1.3, under: false }),
      [T_LET + 0.4, "mob.endermen.scream", { at: [edge.x, edge.y + 2.6, edge.z], volume: 0.7, pitch: 0.8 }],
      [T_LAVA, "liquid.lavapop", { volume: 1 }], [T_LAVA + 0.01, "random.fizz", { volume: 1 }], [T_LAVA + 0.02, "qf.scare.hit", { volume: 0.9 }],
      [T_LAVA, "game.player.hurt"], [T_LAVA + 0.5, "game.player.hurt"], [T_LAVA + 0.52, "random.fizz", { volume: 0.7 }],
      ...deathScream(T_LAVA + 0.15, { volume: 1.2 }),
      [DUR, "game.player.die"], [DUR, "@muffle", { hz: 300, s: 3 }]
    ];
    const loops = [
      [0.5, tSil, "qf.scare.heartbeat", { volume: 0.55, fadeOut: 0.05 }],
      [T_STARE, tSil, "qf.scare.drone", { volume: 0.6, fadeIn: 1.5, fadeOut: 0.05, pitch: 0.75, bus: "sfx" }],
      ...(tGone ? [[tGone + 0.6, t0, "qf.scare.breath", { volume: 0.28, fadeIn: 0.6, fadeOut: 0.03 }]] : []),
      ...S2.loops,
      [T_TP, DUR + 0.5, "liquid.lava", { volume: 0.7, fadeIn: 0.3 }],
      [T_LAVA, DUR + 0.5, "fire.fire", { volume: 0.9, fadeIn: 0.05 }]
    ];
    const _v = new THREE.Vector3();

    function update(t, f) {
      const p = epos(t), cl = R.toLocal(R.camera.position);
      const gone = tGone != null && t >= tGone && t < t0, flash = glimpse(t, tFlash, 0.06);
      E.pivot.visible = t >= T_IN && (!gone || flash);
      const screaming = t >= t0 && t < T_LET + 1.2;
      if (flash) R.place(E, 0.2, -0.6, 0.85, R.yawTo(0.2, 0.85, cl.x, cl.z), -0.3);
      else R.place(E, p.x, p.y, p.z, R.yawTo(p.x, p.z, cl.x, cl.z));
      E.anim(t, 0, { walk: 0, screaming: screaming || flash, enderJitter: screaming ? 1 : 0, lookPitch: inChasm(t) ? 0.5 * sstep(T_LET, T_LET + 0.5, t) : (t > cuts[nCuts - 1] ? -0.25 : 0) });
      if ((screaming || flash) && E.parts.headwear) E.parts.headwear.position.y -= 5 / 16;
      if (t >= t0 && t < tK) { if (E.parts.head) { E.parts.head.rotation.x += jit(t, 21) * 0.1; E.parts.head.rotation.z += jit(t, 25) * 0.1; } L.apply(t); }
      if (inChasm(t)) { const a = E.parts.rightArm, b = E.parts.leftArm; const hold = 1 - sstep(T_LET, T_LET + 0.3, t); if (a) { a.rotation.x = 1.3 * hold; b.rotation.x = 1.3 * hold; } }
      E.setOwn(inChasm(t) ? 0.12 : t >= t0 || flash ? 0.45 : 0.05 + 0.08 * sstep(cuts[0], cuts[nCuts - 1], t));
      // The purple eyes burn hot when it is close.
      E.pivot.updateMatrixWorld(true);
      eyeGlow.forEach((h, i) => {
        h.visible = E.pivot.visible && !inChasm(t);
        if (!h.visible) return;
        _v.set((i ? -1 : 1) * 2 / 16, 0.25 - 4.5 / 16 + 0.25, -4.1 / 16); E.parts.head.localToWorld(_v); h.position.copy(_v);
        h.material.opacity = (t >= t0 || flash ? 0.7 : 0.35); h.scale.setScalar(Math.min(1, _v.distanceTo(R.camera.position) / 1.6));
      });
      arms(t); parts(t);
      chasm.group.visible = inChasm(t);
      if (chasm.group.visible) chasm.animate(t);
      R.L(0, Y + 3, hang.z, lavaLight.position); lavaLight.intensity = inChasm(t) ? 2.5 : 0;
      const g = Math.max(0, ...[T_IN, ...cuts, ...(tGone ? [tGone] : []), T_TP].map((tt) => (t >= tt - 0.05 && t < tt + 0.1 ? 1 - Math.abs(t - tt - 0.02) / 0.08 : 0)));
      f.glitch = Math.max(0, g);
      if (!inChasm(t)) {
        const st = sstep(T_STARE, cuts[nCuts - 1], t) * (gone ? 0.7 : 1);
        f.env = { bake: 1 - 0.25 * sstep(0.2, 1.2, t) - 0.25 * st, lights: 1 - 0.35 * st, fogMul: 1 + 0.8 * st, fog: [0.08, 0.02, 0.1, 0.5 * st] };
        f.tints = [[80, 0, 110, 0.06 * st + 0.35 * pulse(t, [T_TP - 0.05], 0.12)]];
        f.vig = [20, 0, 30, 0.3 + 0.35 * st]; f.vigR = 0.9 - 0.15 * st;
        if (flash) { f.fx = { tear: 0.15, split: 0.5, stat: 0.18 }; f.glitch = 0.5; }
      } else {
        const lv = sstep(T_LAVA, T_LAVA + 0.08, t);
        f.env = { bake: 1, lights: 0, fogMul: 0.7, fogAdd: 2.5 * lv, fog: lv > 0 ? [0.6, 0.1, 0, 1] : [0.22, 0.07, 0.02, 1], noParticles: true };
        f.tints = [[80, 0, 110, 0.4 * (1 - sstep(T_TP, T_TP + 0.25, t))], [255, 80, 0, 0.35 * lv]];
        f.vig = [40, 10, 0, 0.3 + 0.3 * lv]; f.vigR = 0.9;
        f.fire = lv;
      }
      f.black = 0.3 * sstep(DUR - 0.2, DUR + 0.6, t);
      lungeFx(L, t, f);
    }
    return { dur: DUR, hits, cam, update, sounds, loops, deathSide: 1,
      marks: { dread: cuts[0] + 0.2, fake: tGone ? (tFlash[0] ?? tGone + 0.5) + 0.02 : cuts[nCuts - 1] + 0.12, lunge: L.t1 + 0.12, kill: T_LET + 0.5 },
      notes: { vanish, cuts: cuts.length, z0, t0: +t0.toFixed(2), T_LAVA: +T_LAVA.toFixed(2), dur: +DUR.toFixed(2) } };
  }
};
