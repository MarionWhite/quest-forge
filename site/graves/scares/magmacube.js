// Magma Cube (round 8, the owner's script beat by beat): "the lights should dim, and there should be a baby magma cube
// that hops towards the player somewhat innocently, and as it gets close, the player looks down at it, and a Massive
// magma cube comes from behind and kills them."
//   The torches gutter and sink low; the far end of the corridor goes dark. A small squelch in it: a size-1 magma cube
//   hops out of the dark, bouncing high as they do, squashing flat and stretching tall on every hop, a puff of flame
//   where it lands. Hop, sit, hop: it stops at your feet, and you look down at it; it sits there, squishing, and the head
//   tilts at it. A heavy wet thud somewhere behind; the floor shivers. An orange light grows on the floor round the
//   little one, from behind you, and its face lights up. The big squelch, right behind: the head snaps round over the
//   shoulder into the face of a massive magma cube (as big as the corridor allows; Size NBT runs past 4 in the game),
//   its eyes level with yours or above. It jumps: its slices spread wide open on the blazing core, and it comes down
//   on you. Inside it is black and orange; it crushes, and a man screams himself out.
// 1.7.10: ModelMagmaCube (eight slices and the core) and its texture; EntitySlime's squish (squishAmount 1 on leaving
// the ground, -0.5 on landing, x0.9 a tick for the magma cube, squishFactor easing halfway to it each tick;
// RenderMagmaCube's scale and the slices spread 1.7 px each by it); "flame" particles on each landing
// (EntityMagmaCube.getSlimeParticle), size x 8 of them; mob.magmacube.jump / .small / .big.
import { THREE, clamp, lerp, sstep, pulse, tex, easeOut, track } from "./rig.js";
import { settle, shake, hitsOf, particles, mulberry } from "./common.js";
import { deathScream } from "./fnaf.js";
import { roar, blow, kick } from "./story.js";

const LAYERS = [0, 1, 2, 3, 4, 5, 6, 7].map((i) => "field_78109_a" + i), CORE = "field_78108_b";

// EntitySlime's squish on the 20 Hz tick, for a list of hops [[t up, t down], ...]: returns squishFactor(t).
function squishTrack(hops, t1) {
  const n = Math.ceil(t1 * 20) + 2, amt = new Float32Array(n), fac = new Float32Array(n);
  let a = 0, f = 0;
  for (let i = 0; i < n; i++) {
    const t = i / 20, t0 = (i - 1) / 20;
    for (const [up, down] of hops) { if (up > t0 && up <= t) a = 1; if (down > t0 && down <= t) a = -0.5; }
    f += (a - f) * 0.5; fac[i] = f;
    a *= 0.9;
  }
  return (t) => { const x = clamp(t * 20, 0, n - 1.001), i = Math.floor(x), k = x - i; return fac[i] + (fac[i + 1] - fac[i]) * k; };
}
// RenderMagmaCube: the body scaled (1/(f2+1), f2+1, 1/(f2+1)) for f2 = squish / (size / 2 + 1), the slices lifted apart
// (ModelMagmaCube: slice i rides (4 - i) x squish x 1.7 px up, from the squish only while it stretches).
function setSquish(m, sq, size, cap = 1) {
  m.anim(0, 0, {});   // the library's own squish is sin(0) = 0: the rest pose
  const rig = m.root.children[0]; if (!rig) return;
  const S = rig.scale.x, f2 = sq / (size * 0.5 + 1), f3 = 1 / (f2 + 1);
  rig.scale.set(S * f3, S / f3, S * f3);
  const f = Math.min(cap, Math.max(0, sq));
  LAYERS.forEach((n, i) => { const g = m.parts[n]; if (g) g.position.y += f * (4 - i) * 1.7 / 16; });
}
// A hop between two floor points with an arc of height h, as a function of 0..1 (a slime's jump: up fast, down fast).
const arc = (a, b, k, h) => ({ x: lerp(a.x, b.x, k), y: lerp(a.y || 0, b.y || 0, k) + h * 4 * k * (1 - k), z: lerp(a.z, b.z, k) });

export default {
  death: "Steve was slain by Magma Cube",
  async build(R) {
    const partTex = await tex("particles");
    const r = mulberry(R.seed * 17 + 5);

    // ---- the massive one: as big as the corridor behind you allows (its stretch in the air under the ceiling) ------
    const wl = Math.min(R.ray(0, 1, -2.5, -1, 0, 0, 16), R.ray(0, 1, -4, -1, 0, 0, 16)), wr = Math.min(R.ray(0, 1, -2.5, 1, 0, 0, 16), R.ray(0, 1, -4, 1, 0, 0, 16));
    const xB = clamp((wr - wl) / 2, -1.5, 1.5) * 0.5;   // the middle of the corridor behind, a little
    let size = 12;
    const tallest = (s) => 0.5 * s * (1 + 1 / (s * 0.5 + 1));
    while (size > 4 && (tallest(size) > R.ceil - 0.15 || 0.25 * size > Math.min(wl + xB, wr - xB) - 0.05 || 0.5 * size + 1.4 > R.behind)) size--;
    const half = 0.25 * size;
    // (its slices fan out (4 - i) x 1.7 px x size in a jump: up to the ceiling here, past it no further)
    const spreadCap = clamp((R.ceil - 2 * half) / (0.425 * size), 0.3, 1);
    const M = R.mob("LavaSlime", { size, amb: [0.0, 0.0, 0.0], own: true });
    M.anim(0, 0, {}); R.place(M, 0, 0, -8, 0);
    const coreG = M.parts[CORE], coreMats = [];
    if (coreG) coreG.traverse((o) => { if (o.isMesh) { o.material = o.material.clone(); o.material.emissive = new THREE.Color(1, 0.75, 0.45); o.material.emissiveMap = o.material.map; o.material.emissiveIntensity = 0; o.material.userData.noFlash = true; coreMats.push(o.material); } });
    // ---- the baby: size 1 ----
    const baby = R.mob("LavaSlime", { size: 1, amb: [0.9, 0.9, 0.9], own: true });
    baby.anim(0, 0, {}); R.place(baby, 0, 0, 6, Math.PI);

    // ---- the dice -------------------------------------------------------------------------------------------
    const T_DIM = R.vary(0.6, 0.25);
    // The baby: out of the dark at the far end once the light has sunk (it is only a dark shape there, its glow comes
    // up as it nears the light), a few high bouncy hops toward you (magma cubes jump high: motionY 0.42 + 0.1 x size),
    // a pause on the ground between them, the last one small, to your feet.
    const zB0 = clamp(R.ahead - 0.8, 3.5, 10), zEnd = 1.0, xB0 = R.pick([-0.35, 0.3, 0.15]);
    const nHop = Math.max(2, Math.ceil((zB0 - zEnd - 0.75) / 2.3)) + 1;
    const T_SEEN = T_DIM + 1.0;   // there in the dark from here (the light is down)
    const bHops = [];   // [tUp, tDown, from, to, h]
    let tt = T_SEEN + R.vary(0.45, 0.2), from = { x: xB0, z: zB0 };
    for (let i = 0; i < nHop; i++) {
      const last = i === nHop - 1;
      const to = last ? { x: 0.04, z: zEnd } : { x: lerp(xB0, 0.04, (i + 1) / nHop), z: lerp(zB0, zEnd + 0.75, (i + 1) / (nHop - 1)) };
      const air = last ? 0.4 : R.vary(0.56, 0.08), h = last ? 0.35 : R.vary(1.05, 0.15);
      bHops.push([tt, tt + air, from, to, h]);
      from = to; tt += air + (last ? 0 : R.vary(0.38, 0.35));
    }
    const tSitB = bHops[nHop - 1][1];                        // at your feet
    const tBounce = tSitB + R.vary(0.75, 0.15);              // a little hop on the spot
    bHops.push([tBounce, tBounce + 0.3, from, { x: from.x, z: from.z }, 0.22]);
    const tTilt = tSitB + 0.3;
    // The massive one: behind you in the dark; a hop, a heavy landing (tG0); a hop, the big squelch right behind (tG1);
    // it jumps (tJ) and comes down on you (tK); the slices close (tShut).
    // (behind it is the corridor you came along; where a bend or a wall is close behind, it comes from just there)
    const zG1 = -Math.min(half + 2.4, Math.max(half + 0.9, R.behind - half - 0.4)), zA = -Math.min(11, Math.max(-zG1 + 0.01, R.behind - half - 0.3)), zG0 = lerp(zA, zG1, 0.5);
    const tG0 = tBounce + R.vary(0.9, 0.15), tG1 = tG0 + R.vary(1.05, 0.12);
    const tJ = tG1 + R.vary(0.75, 0.12), tK = tJ + 0.55, tShut = tK + 0.3;
    const gHops = [[tG0 - 0.7, tG0, { x: xB, z: zA }, { x: xB, z: zG0 }, 0], [tG1 - 0.7, tG1, { x: xB, z: zG0 }, { x: xB, z: zG1 }, 0], [tJ, tK, { x: xB, z: zG1 }, { x: 0, z: 0.35, y: 0 }, 0]];
    for (const g of gHops) g[4] = clamp(R.ceil - 0.15 - tallest(size), 0.05, 1.4);
    const chews = [tShut + 0.05, tShut + R.vary(0.7, 0.2), tShut + 1.35], DUR = tShut + 2.3;
    const hits = hitsOf([[tK + 0.02, 6, 1], ...chews.map((c, i) => [c, 3 - (i > 1 ? 1 : 0), i % 2 ? 1 : -1]), [DUR, 3, -1]]);
    const sqB = squishTrack(bHops.map((h) => [h[0], h[1]]), DUR + 3), sqG = squishTrack(gHops.map((h) => [h[0], h[1]]), DUR + 3);
    const turn = wl > wr ? 1 : -1;   // over the shoulder with more room

    const hopAt = (hops, t, p0) => {
      let p = p0;
      for (const [up, down, a, b, h] of hops) {
        if (t < up) break;
        p = t < down ? arc(a, b, (t - up) / (down - up), h) : { x: b.x, y: b.y || 0, z: b.z };
      }
      return p;
    };
    const babyAt = (t) => hopAt(bHops, t, { x: xB0, y: 0, z: zB0 });
    const bigAt = (t) => {
      if (t >= tK) { const k = sstep(tK, tShut, t); return { x: 0, y: 0, z: lerp(0.35, 0.2, k), crush: k }; }
      return { ...hopAt(gHops, t, { x: xB, y: 0, z: zA }), crush: 0 };
    };

    // ---- the camera ------------------------------------------------------------------------------------------
    // (the eyes follow where it is, not every bounce)
    const lookB = (t) => { const p = babyAt(Math.max(0, t - 0.12)); return { yaw: R.yawTo(0, 0, p.x, p.z), pitch: R.pitchTo(0, R.eye, 0, p.x, 0.3 * p.y + 0.25, p.z) }; };
    // Over the shoulder (the side with more room) to its face: the yaw to it, wound the way the head turns.
    let yFace = R.yawTo(0, 0, xB, zG1);
    if (turn > 0 && yFace < 0) yFace += 2 * Math.PI; else if (turn < 0 && yFace > 0) yFace -= 2 * Math.PI;
    const cam = (t) => {
      const s = settle(R, t, 0.9);
      const k = sstep(0.8, 1.3, t);
      const c = { x: s.x * (1 - k), y: s.y, z: s.z * (1 - k), yaw: lerp(s.yaw, 0, k), pitch: lerp(s.pitch, -0.06, k), roll: 0, fov: s.fov, near: t >= tJ ? 0.02 : undefined };
      // The baby: the eyes find it as it comes out of the dark and follow it in; it gets close and you look down at it.
      const b = lookB(t), see = sstep(bHops[0][0] + 0.2, bHops[0][0] + 1.0, t);
      c.yaw = lerp(c.yaw, b.yaw * 0.8, see); c.pitch = lerp(c.pitch, b.pitch * (0.75 + 0.25 * sstep(bHops[nHop - 2][0], tSitB, t)), see);
      c.pitch -= 0.12 * sstep(tSitB - 0.2, tSitB + 0.5, t);   // right down at it
      c.roll += 0.13 * sstep(tTilt, tTilt + 0.6, t) * (1 - sstep(tG0, tG0 + 0.4, t));   // the head tilts at it
      // The thud behind: a start, the head lifts a little, then back down to it as the light grows.
      c.pitch += 0.07 * pulse(t, [tG0 + 0.05], 0.3);
      // The big squelch right behind: the head snaps round over the shoulder into its face, and up as it jumps.
      const tn = sstep(tG1 + 0.06, tG1 + 0.5, t);
      const big = bigAt(t), faceY = big.y + half * 1.3;   // its eyes
      const toFace = R.pitchTo(0, R.eye, 0, big.x, faceY, Math.min(-0.4, big.z + half));
      // (as it jumps, the eyes stay on the middle of it coming at you: the face, the slices opening on the core)
      const toMid = R.pitchTo(0, R.eye, 0, big.x, big.y + half, Math.min(-0.4, big.z + half));
      c.yaw = lerp(c.yaw, yFace, tn); c.pitch = lerp(c.pitch, clamp(lerp(toFace, toMid, sstep(tJ, tJ + 0.3, t)), -0.2, 0.4), tn);
      c.z -= 0.25 * sstep(tG1, tG1 + 0.4, t) * (1 - sstep(tJ, tK, t));   // a step back, away from it (toward the little one)
      if (t >= tK) {   // it comes down on you: crushed to the floor under it, the head forced down
        const kc = sstep(tK, tShut, t);
        const h = kick(t, [{ t: tK, side: turn, amp: 1.5 }]);
        c.yaw += h.yaw; c.pitch += h.pitch;
        c.y = lerp(c.y, 0.9, kc); c.pitch = lerp(c.pitch, -0.35, kc); c.roll += 0.4 * kc * turn;
        c.fov = s.fov - 10 * kc;
      }
      const lands = bHops.map((h) => h[1]);
      return shake(c, t, 0.0012 + 0.003 * pulse(t, lands, 0.12) + 0.012 * pulse(t, [tG0], 0.25) + 0.035 * pulse(t, [tG1], 0.25) + 0.07 * pulse(t, [tK], 0.2) + 0.05 * pulse(t, chews, 0.15), 9);
    };

    // ---- particles: "flame" on every landing (size x 8 of them), lava spatter as it lands on you ---------------------
    const fl = [];
    for (const [, down, , to] of bHops) for (let i = 0; i < 8; i++) {
      const a = r() * Math.PI * 2, d = 0.15 + r() * 0.15;
      fl.push({ t0: down + r() * 0.03, at: [to.x + Math.cos(a) * d, 0.05, to.z + Math.sin(a) * d], v: [Math.cos(a) * 0.3, 0.15 + r() * 0.2, Math.sin(a) * 0.3], life: 0.5 + r() * 0.3, size: 0.06, tile: 48, color: [1, 0.85, 0.6], grav: -0.05, fog: false, add: true });
    }
    gHops.slice(0, 2).forEach(([, down, , to]) => { for (let i = 0; i < Math.min(48, size * 8); i++) {
      const a = r() * Math.PI * 2, d = half * (0.8 + r() * 0.5);
      fl.push({ t0: down + r() * 0.05, at: [to.x + Math.cos(a) * d, 0.05, to.z + Math.sin(a) * d], v: [Math.cos(a) * 0.6, 0.2 + r() * 0.4, Math.sin(a) * 0.6], life: 0.6 + r() * 0.4, size: 0.11, tile: 48, color: [1, 0.85, 0.6], grav: -0.05, fog: false, add: true });
    } });
    for (let i = 0; i < 26; i++) fl.push({ t0: tK + r() * 0.08, at: [(r() - 0.5) * 0.9, R.eye - 0.5 + r() * 0.5, 0.35 + r() * 0.5], v: [(r() - 0.5) * 3.2, (r() - 0.1) * 2.5, (r() - 0.3) * 2.4], life: 0.7, size: 0.065, tile: 49, color: [1, 0.6, 0.25], grav: 5, fog: false, add: true });
    const sparks = particles(R, partTex, fl);
    const glow = R.ownLight(R.light(0xff5a10, 0, 22, 1.0));
    const bGlow = R.ownLight(R.light(0xff6a20, 0, 3.5, 1.5));

    // ---- sound: its own, all of it, and your voice -----------------------------------------------------------------
    const near = R.torches.filter((tc) => Math.hypot(tc.l.x, tc.l.z) < 12).slice(0, 3);
    const pz = (z) => [0, 0.3, z];
    const sounds = [
      ...near.map((tc, i) => [T_DIM + 0.1 + 0.15 * i, "random.fizz", { at: [tc.l.x, tc.l.y, tc.l.z], volume: 0.18, pitch: 0.7 + 0.1 * i }]),
      // the baby: a little hop up, a little squelch down
      ...bHops.flatMap(([up, down, a, b], i) => [
        [up, "mob.magmacube.jump", { at: pz(a.z), volume: 0.28, pitch: 1.6 + 0.05 * (i % 3) }],
        [down, "mob.magmacube.small", { at: pz(b.z), volume: i === bHops.length - 1 ? 0.45 : 0.55, pitch: 1.2 + 0.07 * ((i * 5) % 3) }]
      ]),
      // the massive one, behind you
      [gHops[0][0], "mob.magmacube.jump", { at: [xB, 1, zA], volume: 0.35, pitch: 0.55 }],
      [tG0, "mob.magmacube.big", { at: [xB, 0.5, zG0], volume: 0.75, pitch: 0.5 }], [tG0 + 0.01, "qf.scare.hit", { volume: 0.35 }],
      [tG0 + 0.4, "liquid.lavapop", { at: [xB, 1, zG0], volume: 0.4, pitch: 0.6 }],
      [gHops[1][0], "mob.magmacube.jump", { at: [xB, 1, zG0], volume: 0.5, pitch: 0.5 }],
      ...roar(tG1, [["mob.magmacube.big", { at: [xB, 0.8, zG1], pitch: 0.42 }]], { hit: 0.9 }),
      [tG1 + 0.02, "liquid.lavapop", { at: [xB, 1.2, zG1], volume: 0.8, pitch: 0.5 }],
      [tJ, "mob.magmacube.jump", { at: [xB, 1.5, zG1], volume: 1.3, pitch: 0.45 }],
      ...roar(tK, [["mob.magmacube.big", { pitch: 0.4 }], ["fire.ignite", { pitch: 0.6 }]], { hit: 1 }),
      ...blow(tK + 0.01, { volume: 1.1 }),
      [tShut, "mob.magmacube.big", { volume: 1.3, pitch: 0.45 }], [tShut + 0.01, "qf.scare.crunch", { volume: 1.2 }],
      [tShut + 0.06, "@muffle", { hz: 260, s: DUR - tShut + 2 }],
      ...chews.flatMap((c, i) => [[c, "qf.scare.crunch", { volume: 1 }], [c + 0.02, "mob.magmacube.big", { volume: 1, pitch: 0.45 + 0.05 * i }], [c + 0.03, "liquid.lavapop", { volume: 0.8 }]]),
      ...deathScream(tK + 0.12), ...deathScream(chews[1] + 0.1, { volume: 1.1 }),
      [tShut + 0.5, "fire.fire", { volume: 1 }],
      [DUR, "game.player.die"]
    ];
    const loops = [
      [0.3, tG1, "qf.scare.heartbeat", { volume: 0.32, fadeOut: 0.05 }],
      [T_DIM + 0.3, tG1, "qf.scare.drone", { volume: 0.32, fadeIn: 1.5, fadeOut: 0.05, pitch: 0.8, bus: "sfx" }],
      [tG0 + 0.1, tK, "qf.scare.heartbeat", { volume: 0.6, pitch: 1.3, fadeIn: 0.2, fadeOut: 0.02 }],
      [tShut, DUR + 0.2, "qf.scare.heartbeat", { volume: 0.9, pitch: 1.5 }],
      [tShut + 0.2, DUR + 0.2, "fire.fire", { volume: 0.8 }]
    ];

    // ---- the frame ------------------------------------------------------------------------------------------
    const _v = new THREE.Vector3();
    function update(t, f) {
      // The baby.
      const b = babyAt(t);
      baby.pivot.visible = t >= T_SEEN && t < tK;
      R.place(baby, b.x, b.y, b.z, R.yawTo(b.x, b.z, 0, 0), t >= tSitB && t < tG0 ? -0.12 * sstep(tTilt, tTilt + 0.4, t) : 0);
      setSquish(baby, sqB(t), 1);
      const lit = 1 - sstep(5, 10.5, Math.hypot(b.x, b.z));   // it comes up out of the dark as it nears the light
      baby.setOwn(lit);   // EntityMagmaCube is fullbright
      R.L(b.x, b.y + 0.35, b.z - 0.15, bGlow.position); bGlow.intensity = 1.1 * lit * (0.85 + 0.15 * Math.sin(t * 5));
      // The massive one.
      const B = bigAt(t);
      M.pivot.visible = t >= gHops[0][0] - 0.6;
      R.place(M, B.x, B.y, B.z, R.yawTo(B.x, B.z, 0, 0));
      const sq = t < tK ? sqG(t) : lerp(1, -0.25, B.crush);
      setSquish(M, sq, size, spreadCap);
      const air = clamp(sq);
      M.setOwn(t < tK ? 1 : 0.6);   // EntityMagmaCube is fullbright
      for (const m of coreMats) m.emissiveIntensity = 0.7 + 0.8 * air;
      if (coreG) { M.pivot.updateMatrixWorld(true); coreG.getWorldPosition(_v); _v.y = Math.min(_v.y, R.O.y + half * 1.2); glow.position.copy(_v); }
      // The glow it throws ahead of it onto the floor round the little one, growing as it comes.
      const come = sstep(gHops[0][0], tG0, t) * 0.35 + sstep(tG0 + 0.2, tG1, t) * 0.4 + sstep(tG1, tJ, t) * 0.25;
      glow.intensity = t < tK ? (3 + 24 * come + 4 * air) * (0.9 + 0.1 * Math.sin(t * 9)) : 0;
      sparks(t);

      // The lights: guttering, then low; the dark at the end of the corridor.
      const dim = sstep(T_DIM, T_DIM + 1.0, t), gut = dim > 0 && dim < 1 ? 0.25 * Math.sin(t * 37) * Math.sin(t * 13) : 0;
      const inside = sstep(tShut - 0.15, tShut + 0.05, t);
      f.env = { bake: (1 - 0.2 * sstep(0.2, 1.2, t)) * lerp(1, 0.3, dim) * (1 + gut), lights: lerp(1, 0.28, dim) * (1 + gut), fogMul: 1 + 0.8 * dim, fog: [0.01, 0.005, 0.0, 0.6 * dim], squash: inside * Math.min(1, 0.35 + 0.6 * pulse(t, chews, 0.2)) };
      const slam = pulse(t, [tK], 0.12);
      f.tints = [[255, 110, 20, 0.5 * slam + 0.08 * come * (t < tK ? 1 : 0)], [22, 5, 0, 0.75 * inside], [255, 80, 10, 0.3 * inside * pulse(t, chews, 0.25)]];
      f.vig = [40, 8, 0, 0.3 + 0.25 * dim + 0.3 * inside]; f.vigR = 0.88;
      f.fire = Math.max(0.6 * inside, 0.6 * sstep(tK, tK + 0.15, t));
      f.hurt = Math.max(f.hurt || 0, slam);
      f.black = 0.35 * sstep(DUR - 0.25, DUR + 0.6, t);
    }
    return { dur: DUR, hits, cam, update, sounds, loops, deathSide: turn,
      marks: { dim: T_DIM + 0.8, seen: bHops[1][1], dread: tSitB + 0.3, fake: tTilt + 0.5, thud: tG0 + 0.3, turn: tG1 + 0.45, lunge: tJ + 0.3, kill: tShut + 0.6 },
      notes: { size, half, ceil: R.ceil, behind: +R.behind.toFixed(1), zA: +zA.toFixed(2), zG1: +zG1.toFixed(2), nHop, zB0: +zB0.toFixed(2), turn, tSitB: +tSitB.toFixed(2), tG1: +tG1.toFixed(2), dur: +DUR.toFixed(2) } };
  }
};
