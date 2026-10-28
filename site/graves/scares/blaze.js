// Blaze (round 8: out of the nearest grave). The air shimmers and embers rise; something crackles under the floor and
// breathes. The head turns to it: the nearest grave, its plot in front of the headstone cracking, block by block, an
// orange glow seeping up through the cracks and lighting the stone, smoke curling out, the slabs knocking up from below.
// The plot bursts: the floor blocks fly, fire and smoke roar up out of the pit, and the blaze rises out of the grave,
// rods spinning, and floats out into the corridor, bobbing. (With no grave near, it comes up through the floor ahead.)
// Then as round 7, which the owner liked: it flares, smoke pouring off it, the breathing stops (its tell). Three
// fireballs, one after another: into the wall by your head, at your feet, into you. You catch fire (the 1.7.10
// overlay) and stagger back as it floats after you; it flares again and the second three come at point blank. You go
// down burning, the hotbar burns item by item, the edges of the view char black, and a man screams himself out.
import { THREE, track, clamp, lerp, sstep, pulse, tex, loadImg, quad, blockMesh, blockTexName, easeOut } from "./rig.js";
import { settle, shake, hitsOf, floorFall, particles, smoke, fireBlocks, mulberry } from "./common.js";
import { silence, deathScream } from "./fnaf.js";
import { kick, roar } from "./story.js";
import { ITEMS } from "./loadout.js";

// The grave it comes out of: the nearest whose plot (the two floor blocks in front of the headstone) is solid floor
// with air over it, not under your feet; graves behind you count as further off. Else the corridor floor ahead.
function findPlot(R) {
  const cellOf = (lx, lz) => { const p = R.L(lx, -0.5, lz); return [Math.floor(p.x), Math.floor(p.y), Math.floor(p.z)]; };
  const mid = (c) => R.toLocal({ x: c[0] + 0.5, y: c[1] + 0.5, z: c[2] + 0.5 });
  const ok = (c) => {
    const l = mid(c);
    if (!R.solid(l.x, -0.5, l.z) || R.solid(l.x, 0.5, l.z) || R.solid(l.x, 1.5, l.z) || R.solid(l.x, 2.5, l.z)) return false;
    if (/water|lava/.test(R.block(l.x, 0.5, l.z) || "")) return false;
    return Math.hypot(l.x, l.z) > 1.6;
  };
  const near = typeof R.kr.gravesNear === "function" ? R.kr.gravesNear(R.L(0, 0, 0), 16) : [];
  let best = null;
  for (const g of near) {
    const sl = R.toLocal(g.stone), o = { x: g.out.x * R.r.x + g.out.z * R.r.z, z: g.out.x * R.f.x + g.out.z * R.f.z };
    const cells = [cellOf(sl.x - o.x * 0.9, sl.z - o.z * 0.9), cellOf(sl.x - o.x * 1.9, sl.z - o.z * 1.9)];
    if (!cells.every(ok)) continue;
    const a = mid(cells[0]), b = mid(cells[1]), pc = { x: (a.x + b.x) / 2, z: (a.z + b.z) / 2 };
    const d = Math.hypot(pc.x, pc.z);
    if (d < 2.4) continue;
    const score = d + (pc.z < -1.5 ? 7 : 0);
    if (!best || score < best.score) best = { grave: g, stone: sl, out: o, cells, pc, score };
  }
  if (best) return best;
  const sd = R.wallR >= R.wallL ? 1 : -1;
  for (const z of [4.5, 3.5, 5.5, 6.5, 2.5]) for (const x of [0.6 * sd, -0.6 * sd, 0]) {
    if (z > R.ahead - 1.5) continue;
    const cells = [cellOf(x, z), cellOf(x, z + 1)];
    if (!cells.every(ok)) continue;
    const a = mid(cells[0]), b = mid(cells[1]);
    return { grave: null, stone: null, out: null, cells, pc: { x: (a.x + b.x) / 2, z: (a.z + b.z) / 2 } };
  }
  const c = cellOf(0.5, 4);
  return { grave: null, stone: null, out: null, cells: [c, cellOf(0.5, 5)], pc: { x: 0.5, z: 4.5 }, bare: true };
}

export default {
  death: "Steve was burnt to a crisp whilst fighting Blaze",
  async build(R) {
    const [partTex, ballTex] = await Promise.all([tex("particles"), tex("item_fireball")]);
    const stages = await Promise.all([...Array(10)].map((_, i) => tex("destroy_stage_" + i)));
    const stageImgs = await Promise.all([...Array(10)].map((_, i) => loadImg("destroy_stage_" + i)));
    const plot = findPlot(R), pc = plot.pc;
    const B = R.mob("Blaze", { amb: [0.05, 0.05, 0.05], own: true });
    B.anim(0, 0, {}); R.place(B, pc.x, -2.2, pc.z, Math.PI);
    const by = 1.1;

    // ---- the dice -------------------------------------------------------------------------------------------
    const T_HEAT = R.vary(0.9, 0.25), T_CRACK = T_HEAT + R.vary(0.55, 0.3), T_TURN = T_CRACK + 0.25;
    const T_BURST = T_CRACK + R.vary(2.3, 0.15), T_RISE = T_BURST + 0.08;
    const tOut = T_RISE + 1.25, tFlare = tOut + R.vary(1.0, 0.25);           // floats out; flares (its tell)
    const V1 = [0, 1, 2].map((i) => tFlare + 0.5 + i * R.vary(0.3, 0.2));     // the three
    const tK = V1[2] + 0.1;                                                   // the third into you: on fire
    const tFlare2 = tK + R.vary(1.1, 0.25), FK = [0, 1, 2].map((i) => tFlare2 + 0.45 + i * 0.3);
    const T_FALL = FK[2] + 0.35, DUR = T_FALL + 1.25;
    const wallX = (R.wallR > R.wallL ? -R.wallL : R.wallR) * 0.98, side = Math.sign(wallX) || 1;
    const hits = hitsOf([[tK, 4, -side], [FK[0] + 0.1, 3, 1], [FK[1] + 0.1, 3, -1], [FK[2] + 0.1, 3, 1], [T_FALL + 0.5, 3, 1], [DUR - 0.05, 4, 1]]);
    // Where it stops to fire: out of the alcove into the corridor, ahead of you.
    const gc = { x: clamp(pc.x * 0.35, -1.2, 1.2), z: pc.z };
    const P1 = { x: gc.x * 0.6, y: by, z: clamp(pc.z < 2.6 ? 2.6 : pc.z - 1.2, 2.6, 7) };

    // ---- the grave's plot: carved now (the remesh is no frame of the scare), held up by stand-ins until it bursts --
    const cellsL = plot.cells.map((c) => R.toLocal({ x: c[0] + 0.5, y: c[1] + 0.5, z: c[2] + 0.5 }));
    const names = plot.cells.map((c) => R.blockW(c[0] + 0.5, c[1] + 0.5, c[2] + 0.5) || "stone");
    const up = new THREE.Vector3(0, 1, 0);
    const bakes = plot.cells.map((c) => R.bakeAt(new THREE.Vector3(c[0] + 0.5, c[1] + 1, c[2] + 0.5), up) || new THREE.Vector3(0.2, 0.19, 0.18));
    const ftex = await Promise.all(names.map((n) => tex(blockTexName(n))));
    const standins = plot.cells.map((c, i) => { const m = blockMesh(ftex[i], { lit: true, amb: bakes[i] }); m.position.set(c[0] + 0.5, c[1] + 0.5, c[2] + 0.5); return R.add(m); });
    if (!plot.bare) {
      const a = plot.cells[0], b = plot.cells[1];
      R.carveW([Math.min(a[0], b[0]), Math.min(a[1], b[1]) - 1, Math.min(a[2], b[2])], [Math.max(a[0], b[0]), Math.max(a[1], b[1]), Math.max(a[2], b[2])]);
    }
    // The cracks (the block-breaking overlay) and the glow seeping up through them (the same cracks, lit orange).
    const crackMats = stages.map((t) => new THREE.MeshBasicMaterial({ map: t, transparent: true, alphaTest: 0.1, blending: THREE.CustomBlending, blendSrc: THREE.DstColorFactor, blendDst: THREE.SrcColorFactor, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -3, polygonOffsetUnits: -3, fog: false }));
    const glowTexs = stageImgs.map((im) => {
      const c = document.createElement("canvas"); c.width = c.height = 16; const x = c.getContext("2d");
      if (im) { x.drawImage(im, 0, 0); x.globalCompositeOperation = "source-in"; x.fillStyle = "#fff"; x.fillRect(0, 0, 16, 16); }
      const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.magFilter = t.minFilter = THREE.NearestFilter; t.generateMipmaps = false; return t;
    });
    const crackGeo = new THREE.BoxGeometry(1.004, 1.004, 1.004);
    const cracks = plot.cells.map(() => { const m = new THREE.Mesh(crackGeo, crackMats[0]); m.visible = false; m.renderOrder = 3; return R.add(m); });
    const glows = plot.cells.map(() => {
      const m = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ map: glowTexs[0], color: 0xff7a20, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, fog: false, polygonOffset: true, polygonOffsetFactor: -4, polygonOffsetUnits: -4 }));
      m.rotation.x = -Math.PI / 2; m.visible = false; m.renderOrder = 4; return R.add(m);
    });
    // The slabs knock up from below, faster and harder as it comes.
    const knocks = [];
    for (let tt = T_CRACK + 0.35, gap = 0.55; tt < T_BURST - 0.15; tt += gap, gap = Math.max(0.16, gap * 0.8)) knocks.push(tt);
    const crackAt = (i, t) => { const c0 = T_CRACK + 0.35 * i; return t < c0 ? -1 : Math.min(9, Math.floor((t - c0) / (T_BURST - 0.1 - c0) * 10)); };
    const fireIn = await fireBlocks(R, cellsL.map((c, i) => ({ at: [c.x, -2, c.z], t0: T_BURST + 0.02 * i, s: 1 })));
    const pitLight = R.ownLight(R.light(0xff6a20, 0, 8, 1.5));
    plot.cells.forEach((c, i) => R.burst(T_BURST + 0.01 * i, [cellsL[i].x, 0.1, cellsL[i].z], 22, "stone", { dir: [0, 2.6, 0], speed: 4.2, spread: 1.3, size: 0.1, life: 1.6, stick: 4 }));
    R.burst(T_BURST + 0.02, [pc.x, 0.1, pc.z], 26, "fire", { dir: [0, 3, 0], speed: 3.5, spread: 1.2, size: 0.05, life: 1.0 });
    knocks.forEach((tt, i) => R.burst(tt + 0.01, [pc.x, 0.05, pc.z], 2 + (i >> 1), "dust", { dir: [0, 0.8, 0], speed: 0.8, spread: 0.8, size: 0.03, life: 0.8 }));

    // Where it is: in the pit; up out of it over the plot; out into the corridor to fire; after you as you burn.
    const blazeAt = (t, cl) => {
      if (t < tOut) { const k = easeOut(sstep(T_RISE, T_RISE + 1.15, t)); return { x: pc.x, y: lerp(-2.2, by, k) + Math.sin(t * 2.2) * 0.08 * k, z: pc.z }; }
      const k1 = sstep(tOut, tFlare, t), k2 = sstep(tK + 0.15, tFlare2 + 0.2, t);
      const to2 = { x: cl ? cl.x * 0.5 : 0, y: R.eye - 1.4, z: (cl ? cl.z : -0.5) + 1.75 };
      return { x: lerp(lerp(pc.x, P1.x, k1), to2.x, k2), y: lerp(by, to2.y, k2) + Math.sin(t * 2.2) * 0.08 - 0.4 * sstep(T_FALL, T_FALL + 0.6, t), z: lerp(lerp(pc.z, P1.z, k1), to2.z, k2) };
    };
    const shots = [
      { t0: V1[0] - 0.18, t1: V1[0], from: "blaze", to: [wallX, 1.75, 0.5] },
      { t0: V1[1] - 0.16, t1: V1[1], from: "blaze", to: [0.12 * -side, 0.05, 0.85] },
      { t0: V1[2] - 0.14, t1: V1[2], from: "blaze", to: "cam" },
      ...FK.map((tt) => ({ t0: tt - 0.08, t1: tt + 0.02, from: "blaze", to: "cam" }))
    ];
    const balls = shots.map((sh) => { const q = quad(ballTex, 0.32, 0.32, { alphaTest: 0.1, fog: false }); q.visible = false; R.add(q); return { q, ...sh }; });
    const fires = await fireBlocks(R, [{ at: [wallX * 0.9, 0, 0.5], t0: V1[0] + 0.1, s: 0.7 }, { at: [0.12 * -side, 0, 0.85], t0: V1[1] + 0.08, s: 0.8 }, { at: [0, 0, -0.4], t0: FK[0] + 0.15, s: 0.9 }, { at: [0.7, 0, -0.1], t0: FK[1] + 0.2, s: 0.8 }]);
    const r = mulberry(17 + R.seed);
    const embers = [];
    for (let i = 0; i < 34; i++) embers.push({ t0: T_HEAT + r() * (DUR - T_HEAT), at: [pc.x + (r() - 0.5) * 1.6, r() * 0.4, pc.z + (r() - 0.5) * 1.6], v: [(r() - 0.5) * 0.2, 0.6 + r() * 0.8, (r() - 0.5) * 0.2], life: 1.6 + r(), size: 0.035 + r() * 0.03, tile: 49, color: [1, 0.55, 0.2], grav: -0.1, fog: false, add: true });
    for (let i = 0; i < 26; i++) embers.push({ t0: tK + r() * 0.3, at: [(r() - 0.5) * 0.9, R.eye - 0.2 + r() * 0.5, 0.3 + r() * 0.4], v: [(r() - 0.5) * 2.5, (r() - 0.3) * 2, -1 - r() * 2], life: 0.6, size: 0.05, tile: 49, color: [1, 0.65, 0.25], grav: 3, fog: false, add: true });
    // Its flare: smoke pouring off it (the vanilla "on fire" before it shoots), where it is each time.
    const flareSmoke = [tFlare, tFlare2].flatMap((tf, j) => { const q = blazeAt(tf + 0.2, { x: 0, z: -0.6 }); return [0, 1, 2].flatMap((k) => smoke([q.x, q.y + 1.2, q.z], tf + k * 0.15, 5, { spread: 0.45, window: 0.2, life: 1.1, size: 0.3, rise: 0.9, seed: 80 + j * 3 + k, dark: 0.2 })); });
    const puffs = particles(R, partTex, [...embers, ...flareSmoke,
      // smoke curling out of the cracks; then the burst: smoke rolling up out of the pit, and a column of flame
      ...[0, 1, 2, 3].flatMap((k) => smoke([pc.x, 0.12, pc.z], T_CRACK + 0.4 + k * 0.45, 2 + k, { spread: 0.9, window: 0.4, life: 1.4, size: 0.16, rise: 0.45, seed: 90 + k, dark: 0.3 })),
      ...[0, 1, 2, 3].flatMap((k) => smoke([pc.x, 0.3 + k * 0.45, pc.z], T_BURST + k * 0.25, 6, { spread: 1.0, window: 0.45, life: 1.6, size: 0.42, rise: 1.0, seed: 50 + k })),
      ...[...Array(36)].map(() => ({ t0: T_BURST + r() * 0.7, at: [pc.x + (r() - 0.5) * 1.1, -0.6 + r() * 0.4, pc.z + (r() - 0.5) * 1.1], v: [(r() - 0.5) * 0.6, 3 + r() * 4, (r() - 0.5) * 0.6], life: 0.45 + r() * 0.45, size: 0.14 + r() * 0.16, tile: 48, color: [1, 0.85, 0.6], grav: 0, fog: false, add: true })),
      ...smoke([wallX, 1.7, 0.5], V1[0] + 0.05, 8, { spread: 0.4, window: 0.2, life: 1.2, size: 0.35, rise: 0.7, seed: 60 }),
      ...[0, 1, 2, 3, 4, 5].flatMap((k) => smoke([0, 0.9, 0.4], tK + 0.2 + k * 0.4, 2, { spread: 0.5, window: 0.3, life: 1, size: 0.18, rise: 1.2, seed: 70 + k, dark: 0.3 }))]);
    const glow = R.ownLight(R.light(0xff7a20, 0, 9, 1.3)), hit = R.ownLight(R.light(0xffa040, 0, 6, 1.4));

    // ---- the camera ------------------------------------------------------------------------------------------
    // The crackle and the breath under the floor turn the head to the grave; it watches the plot crack; it follows the
    // blaze up out of the pit and out into the corridor.
    const yPlot = R.yawTo(0, 0, pc.x, pc.z), lookP1 = R.yawTo(0, 0, P1.x, P1.z);
    const pPlot = R.pitchTo(0, R.eye, 0, pc.x, 0, pc.z) * 0.85, pRise = R.pitchTo(0, R.eye, 0, pc.x, by + 1.4, pc.z) * 0.85;
    const yawK = track([[0, 0], [T_TURN, 0], [T_TURN + 0.85, yPlot], [tOut, yPlot], [tFlare, lookP1]]);
    const pitchK = track([[0, 0], [T_TURN, 0], [T_TURN + 0.85, pPlot], [T_BURST, pPlot], [T_BURST + 0.12, pPlot + 0.1, "x"], [T_RISE + 0.8, pRise, "o"], [tOut, pRise], [tFlare, R.pitchTo(0, R.eye, 0, P1.x, P1.y + 0.9, P1.z) * 0.8],
      [V1[1] - 0.02, R.pitchTo(0, R.eye, 0, P1.x, P1.y + 0.9, P1.z) * 0.8, "h"], [V1[1] + 0.12, -0.45, "x"], [V1[2] - 0.05, -0.1]]);
    const cam = (t) => {
      const st = settle(R, t, 0.9);
      const k = sstep(0.8, 1.3, t);
      const c = { x: st.x * (1 - k), y: st.y, z: st.z * (1 - k), yaw: lerp(st.yaw, yawK(t), k), pitch: lerp(st.pitch, pitchK(t), k), roll: 0, fov: st.fov - 5 * sstep(tFlare, V1[0], t) * (1 - sstep(tK, tK + 0.2, t)), near: t >= tK ? 0.02 : undefined };
      // The plot bursts: the head jerks back from it.
      c.z -= 0.22 * sstep(T_BURST, T_BURST + 0.25, t) * (1 - sstep(tOut, tFlare, t)); c.fov += 4 * pulse(t, [T_BURST], 0.2);
      // The first one past your head into the wall: the head jerks away from it.
      const by1 = pulse(t, [V1[0]], 0.16); c.yaw += -side * 0.22 * by1; c.roll += side * 0.06 * by1;
      // Burning: you stagger back, beating at it, and the head stays on it as it comes after you; then you go down.
      const burn = sstep(tK, tK + 0.8, t);
      c.z -= 0.6 * burn; c.yaw += burn * Math.sin(t * 2.3) * 0.18; c.roll += burn * Math.sin(t * 3.1) * 0.08;
      if (t > tK) { const q = blazeAt(t, c), kq = sstep(tK + 0.3, tK + 0.9, t); c.yaw = lerp(c.yaw, R.yawTo(c.x, c.z, q.x, q.z) + burn * Math.sin(t * 2.3) * 0.12, kq); c.pitch = lerp(c.pitch, R.pitchTo(c.x, c.y, c.z, q.x, q.y + 1.3, q.z), kq); }
      const kk = kick(t, [{ t: tK, side: -side, amp: 1.3 }, ...FK.map((tt, i) => ({ t: tt + 0.02, side: i % 2 ? 1 : -1, amp: 0.8 }))]); c.yaw += kk.yaw; c.pitch += kk.pitch;
      floorFall(c, t, T_FALL, { d: 0.5, side: 1, roll: 1.1, y: 0.28, pitch: 0.2, back: 0.2 });
      c.fov += 6 * pulse(t, [tK], 0.12);
      return shake(c, t, 0.002 + 0.02 * pulse(t, [...V1, ...FK.map((x) => x + 0.02)], 0.2) + 0.016 * pulse(t, [T_BURST], 0.25) + 0.004 * pulse(t, knocks, 0.12) + 0.01 * burn, 8);
    };

    // ---- sound --------------------------------------------------------------------------------------------
    const sounds = [
      // Under the grave: a crackle, the stone cracking, its breath from below, the slabs knocking.
      [T_HEAT, "fire.fire", { at: [pc.x, 0.2, pc.z], volume: 0.45, pitch: 0.8 }],
      [T_CRACK, "dig.stone", { at: [pc.x, 0.2, pc.z], volume: 0.6, pitch: 0.6 }], [T_CRACK + 0.05, "mob.blaze.breathe", { at: [pc.x, -0.6, pc.z], volume: 0.55, pitch: 0.8 }],
      ...knocks.map((tt, i) => [tt, i % 2 ? "dig.stone" : "step.stone", { at: [pc.x, 0.2, pc.z], volume: Math.min(1, 0.45 + 0.07 * i), pitch: Math.min(0.95, 0.55 + 0.05 * i) }]),
      [T_CRACK + 1.0, "fire.fire", { at: [pc.x, 0.2, pc.z], volume: 0.7 }], [T_CRACK + 1.35, "mob.blaze.breathe", { at: [pc.x, -0.6, pc.z], volume: 0.85, pitch: 0.85 }],
      // The burst, and it rises out of the grave.
      ...roar(T_BURST, [["dig.stone", { at: [pc.x, 0.3, pc.z], pitch: 0.7 }], ["fire.ignite", { at: [pc.x, 0.3, pc.z], pitch: 0.6 }], ["mob.blaze.breathe", { at: [pc.x, 0.3, pc.z], pitch: 0.75 }]], { hit: 0.75 }),
      [T_BURST + 0.04, "dig.stone", { at: [cellsL[1].x, 0.3, cellsL[1].z], volume: 1.1, pitch: 0.85 }],
      [T_RISE + 0.75, "mob.blaze.breathe", { at: [pc.x, by + 0.8, pc.z], volume: 1, pitch: 0.95 }],
      [tOut + 0.4, "mob.blaze.breathe", { at: [P1.x, P1.y + 0.8, P1.z], volume: 0.9, pitch: 0.95 }],
      // The flare: the breath stops; it catches.
      silence(tFlare - 0.05, { fade: 0.1 }),
      [tFlare, "fire.ignite", { at: [P1.x, P1.y + 0.8, P1.z], volume: 1.2, pitch: 0.7 }], [tFlare + 0.02, "mob.blaze.breathe", { at: [P1.x, P1.y + 0.8, P1.z], volume: 1.3, pitch: 0.6 }],
      ...V1.map((tt) => [tt - 0.18, "mob.ghast.fireball", { at: [P1.x, P1.y + 1, P1.z], volume: 1.1 }]),
      [V1[0], "random.fizz", { at: [wallX, 1.7, 0.5], volume: 1 }], [V1[0] + 0.01, "fire.ignite", { at: [wallX, 1.7, 0.5], volume: 0.9 }],
      [V1[1], "fire.ignite", { at: [0, 0.1, 0.85], volume: 1 }],
      [tK, "fire.ignite", { volume: 1.3 }], [tK + 0.005, "qf.scare.hit", { volume: 1.0 }],
      [tFlare2, "fire.ignite", { volume: 1.1, pitch: 0.75 }], [tFlare2 + 0.02, "mob.blaze.breathe", { volume: 1.3, pitch: 0.6 }],
      ...FK.map((tt) => [tt - 0.08, "mob.ghast.fireball", { volume: 1 }]), ...FK.map((tt) => [tt + 0.1, "fire.ignite", { volume: 1.1 }]),
      [tK + 0.15, "fire.fire", { volume: 1 }],
      ...hits.map((h) => [h.t, "game.player.hurt"]), ...deathScream(tK + 0.15), ...deathScream(T_FALL - 0.1, { volume: 1.1, under: false }),
      [DUR - 0.6, "mob.blaze.breathe", { volume: 1 }],
      [DUR, "game.player.die"], [DUR, "@muffle", { hz: 500, s: 2.5 }]
    ];
    const loops = [
      [0.5, tFlare, "qf.scare.heartbeat", { volume: 0.45 }], [T_HEAT, tFlare, "qf.scare.drone", { volume: 0.45, fadeIn: 1.5, fadeOut: 0.1, bus: "sfx" }],
      [T_BURST, DUR + 0.3, "fire.fire", { at: [pc.x, -1, pc.z], volume: 0.55, fadeIn: 0.05 }],
      [tK + 0.1, DUR + 0.5, "fire.fire", { volume: 0.9, fadeIn: 0.2 }], [tK, DUR + 0.2, "qf.scare.heartbeat", { volume: 0.8, pitch: 1.5 }]
    ];

    // ---- the frame ------------------------------------------------------------------------------------------
    const _w = new THREE.Vector3();
    const flareOf = (t) => sstep(tFlare - 0.05, tFlare + 0.2, t) * (1 - sstep(V1[2] + 0.2, V1[2] + 0.8, t)) + sstep(tFlare2 - 0.05, tFlare2 + 0.2, t) * (1 - sstep(FK[2] + 0.2, FK[2] + 0.8, t));
    function update(t, f) {
      const cl = R.toLocal(R.camera.position);
      const q = blazeAt(t, cl), vis = t > T_BURST - 0.02;
      // The plot: the stand-ins knock up from below and crack, the glow seeping through, until it bursts.
      const j = Math.max(0, ...knocks.map((tt) => (t >= tt && t < tt + 0.1 ? 1 - (t - tt) / 0.1 : 0)));
      const crackK = sstep(T_CRACK, T_BURST, t), fl0 = 0.85 + 0.15 * Math.sin(t * 23) * Math.sin(t * 7.3);
      plot.cells.forEach((c, i) => {
        const on = t < T_BURST, st0 = crackAt(i, t);
        standins[i].visible = on;
        standins[i].position.set(c[0] + 0.5, c[1] + 0.5 + 0.035 * j * (i ? 0.7 : 1), c[2] + 0.5);
        cracks[i].visible = glows[i].visible = on && st0 >= 0;
        if (!cracks[i].visible) return;
        cracks[i].material = crackMats[st0]; cracks[i].position.copy(standins[i].position);
        glows[i].material.map = glowTexs[st0]; glows[i].position.set(c[0] + 0.5, standins[i].position.y + 0.503, c[2] + 0.5);
        glows[i].material.opacity = (0.3 + 0.7 * st0 / 9) * fl0;
      });
      R.L(pc.x, 0.35, pc.z, pitLight.position);
      pitLight.intensity = (t < T_BURST ? 3.2 * crackK * fl0 : 1.7 * fl0) + 10 * pulse(t, [T_BURST], 0.3) + 0.8 * j;
      fireIn(t);
      B.pivot.visible = vis;
      R.place(B, q.x, q.y, q.z, R.yawTo(q.x, q.z, cl.x, cl.z));
      const fl = flareOf(t);
      B.anim(t * (1 + 1.2 * fl), 0, {});   // the rods spin up as it flares
      // A rod passing between the lens and you would fill the frame at point blank: those near the lens are left out.
      if (t > tK) { B.pivot.updateMatrixWorld(true); for (let i = 0; i < 12; i++) { const g = B.parts["blazeSticks" + i]; if (g) { g.getWorldPosition(_w); g.visible = _w.distanceTo(R.camera.position) > 0.42; } } }
      B.setOwn(0.5 + 0.5 * fl + 0.3 * pulse(t, [...V1, ...FK], 0.25));
      R.L(q.x, q.y + 1.2, q.z - 0.4, glow.position);
      glow.intensity = vis ? (2.5 * sstep(T_HEAT, T_RISE, t) + 2.5 * sstep(T_RISE - 0.2, T_RISE + 0.6, t)) * (t < tK ? 1 : 0.55) + 3 * fl + 4 * pulse(t, [...V1, ...FK], 0.2) : 0.6 * sstep(T_HEAT, T_RISE, t);
      for (const b of balls) {
        const k = (t - b.t0) / (b.t1 - b.t0);
        b.q.visible = k >= 0 && k < 1;
        if (!b.q.visible) continue;
        const fr = b.from === "blaze" ? [q.x, q.y + 1.5, q.z] : b.from, to = b.to === "cam" ? [cl.x, cl.y - 0.15, cl.z + 0.15] : b.to;
        R.at(b.q, lerp(fr[0], to[0], k), lerp(fr[1], to[1], k), lerp(fr[2], to[2], k)); b.q.quaternion.copy(R.camera.quaternion);
      }
      const hb = balls.map((b) => [b, pulse(t, [b.t1], 0.25)]).sort((p, q2) => q2[1] - p[1])[0];
      if (hb && hb[1] > 0.01) { const to = hb[0].to === "cam" ? [cl.x, cl.y, cl.z + 0.3] : hb[0].to; R.L(to[0] * 0.9, to[1] + 0.2, to[2], hit.position); hit.intensity = 9 * hb[1]; } else hit.intensity = 0;
      fires(t); puffs(t);
      const heat = sstep(T_HEAT, T_RISE, t) * (1 + 0.4 * fl), burn = sstep(tK, tK + 0.25, t);
      f.env = { nausea: 0.12 * Math.min(1, heat) + 0.15 * burn, bake: 1 - 0.2 * sstep(0.2, 1.2, t), fogMul: 1 + 0.6 * Math.min(1, heat), fog: [0.12, 0.05, 0.02, 0.5 * Math.min(1, heat)] };
      f.tints = [[255, 110, 30, 0.05 * heat + 0.12 * burn]];
      f.vig = [40, 10, 0, 0.3 + 0.25 * Math.min(1, heat)]; f.vigR = 0.9;
      f.fire = burn;
      f.burnt = ITEMS.map((_, i) => t > tK + 0.5 + i * 0.35);   // the loadout's items, one by one
      f.char = 0.62 * sstep(tK + 0.6, DUR, t);
    }
    return { dur: DUR, hits, cam, update, sounds, loops, deathSide: 1,
      marks: { crack: T_CRACK + 1.2, burst: T_BURST + 0.15, dread: T_RISE + 0.5, fake: tFlare + 0.25, lunge: V1[0] - 0.05, kill: tK + 0.9 },
      notes: { grave: plot.grave ? plot.grave.i : null, family: plot.grave ? plot.grave.family : null, plot: [+pc.x.toFixed(2), +pc.z.toFixed(2)], bare: !!plot.bare, burst: +T_BURST.toFixed(2), flare: +tFlare.toFixed(2), tK: +tK.toFixed(2), dur: +DUR.toFixed(2) } };
  }
};
