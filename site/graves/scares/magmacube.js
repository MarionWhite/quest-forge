// Magma Cube (round 7: the accordion). A thump somewhere ahead. Every torch dies at once: total black (its one
// device). Then, far off in it, a single orange core pulsing like a heart. Thump: it hops closer, and in the air its
// slices spread apart as they do in the game, the core blazing between them and the corridor lit for a moment; thump,
// closer. It sits there in front of you, pulsing. A pop off to one side: small ones leap at you out of the black,
// burning. Then the big one squats, and leaps: high over you, its slices fanned wide open on the blazing core, and it
// comes down on top of you. The slices close over you; inside it is black and orange, it crushes, and a man screams
// himself out.
import { THREE, clamp, lerp, sstep, pulse, tex } from "./rig.js";
import { settle, shake, hitsOf, particles, mulberry } from "./common.js";
import { silence, deathScream } from "./fnaf.js";
import { roar, blow, kick, hop } from "./story.js";

const LAYERS = [0, 1, 2, 3, 4, 5, 6, 7].map((i) => "field_78109_a" + i), CORE = "field_78108_b";

export default {
  death: "Steve was slain by Magma Cube",
  async build(R) {
    const partTex = await tex("particles");
    const r = mulberry(R.seed * 17 + 5);
    const size = R.ceil >= 4 ? 3 : 2, half = size * 0.25, px = size / 16;
    const M = R.mob("LavaSlime", { size, amb: [0.0, 0.0, 0.0], own: true });
    M.anim(0, 0, {}); R.place(M, 0, 0, 4, Math.PI);
    // The core gets its own material so it can blaze while the plates stay dark.
    const coreG = M.parts[CORE];
    const coreMats = [];
    if (coreG) coreG.traverse((o) => { if (o.isMesh) { o.material = o.material.clone(); o.material.emissive = new THREE.Color(1, 0.75, 0.45); o.material.emissiveMap = o.material.map; o.material.emissiveIntensity = 0; o.material.userData.noFlash = true; coreMats.push(o.material); } });
    // The accordion (ModelMagmaCube: slice i rides (4 - i) * squish * 1.7 px up), past what the game's squish reaches.
    const spread = (o) => LAYERS.forEach((n, i) => { const g = M.parts[n]; if (g) g.position.y += o * (4 - i) * 1.7 / 16; });
    const small = [0, 1, 2, 3, 4].map(() => R.mob("LavaSlime", { size: 1, amb: [0.9, 0.9, 0.9], own: true }));

    // ---- the dice -------------------------------------------------------------------------------------------
    const zNear = clamp(R.ahead - half - 1.5, 2.4, 3.4), zFar = clamp(R.ahead - half - 0.6, zNear + 2, 9);
    const tThump = R.vary(1.2, 0.25), tOut = tThump + R.vary(0.95, 0.3), tCore = tOut + R.vary(1.3, 0.35);
    const nHop = R.chance(0.5) ? 3 : 2;
    const hopT = [], hopZ = [];
    let th = tCore + R.vary(1.0, 0.3);
    for (let i = 0; i < nHop; i++) { hopT.push(th); hopZ.push(lerp(zFar, zNear, (i + 1) / nHop)); th += R.vary(0.7, 0.3); }
    const tSit = hopT[nHop - 1];                                   // there, in front of you, pulsing
    const popSide = R.pick([-1, 1]), tPop = tSit + R.vary(0.95, 0.35);
    const withSmalls = R.chance(0.7);                              // or the pop is nothing, and you look back at it
    const nSmall = withSmalls ? 2 + Math.floor(R.rand() * 2) : 0;
    const tB = tPop + R.vary(0.5, 0.35);
    // The first comes out of the black where you are looking (a +yaw looks toward -x), the next from the other side.
    const pools = [[-1.1, -0.55, -0.85], [1.0, 0.6, 1.25]].map((p) => p.sort(() => R.rand() - 0.5));
    const angs = [0, 1, 2].map((i) => pools[(popSide > 0 ? 0 : 1) ^ (i % 2)][i >> 1]).slice(0, nSmall);
    const smalls = angs.map((a, i) => {
      const t1 = tB + 0.3 + i * R.vary(0.3, 0.3);
      const high = R.chance(0.35) && R.ceil > 2.8;
      return { a, t0: t1 - 0.36, t1, y0: high ? Math.min(R.ceil - 0.3, 2.6) : 0.2, d: R.vary(2.3, 0.2), side: Math.sign(a) };
    });
    const tBend = nSmall ? smalls[nSmall - 1].t1 : tPop + 0.7;
    // The leap: you look back (tBack), it squats (tJ - 0.35), leaps (tJ), comes down on you (tK); the slices shut (tShut).
    const tBack = tBend + 0.25, tJ = tBack + R.vary(0.85, 0.3), tK = tJ + 0.66, tShut = tK + 0.32;
    const chews = [tShut + 0.05, tShut + R.vary(0.7, 0.2), tShut + 1.35], DUR = tShut + 2.3;
    const startP = { x: 0.05, y: 0, z: zNear }, onYou = { x: 0, y: R.eye - half, z: 0.55 };
    const SP_LEAP = 0.85;   // the slices at the top of the leap (vanilla tops out at 1)
    const spanUp = (sp) => half * 2 + 4 * 1.7 * sp * size / 16;
    const leapH = clamp(R.ceil - 0.2 - spanUp(SP_LEAP) - (startP.y + onYou.y) / 2, 0.15, 1.0);
    const hits = hitsOf([...smalls.map((s, i) => [s.t1, i ? 1 : 2, s.side]), [tK + 0.02, 4, 1], ...chews.map((c, i) => [c, 3 - (i > 1 ? 1 : 0), i % 2 ? 1 : -1]), [DUR, 3, -1]]);
    const offYaw = nSmall ? smalls[nSmall - 1].side * 0.3 : popSide * 0.3;   // where the head is left looking
    // Where the big one is: its feet (x, y, z), how far its slices are spread (sp, in the game's squish) and how hard
    // it is squashed on a landing (land).
    const bigAt = (t) => {
      if (t < tSit + 0.2) {
        let z = zFar, y = 0, sp = 0;
        for (let i = 0; i < nHop; i++) {
          const a0 = i ? hopZ[i - 1] : zFar, d = 0.44;
          if (t >= hopT[i] - d && t < hopT[i]) { const k = (t - hopT[i] + d) / d; z = lerp(a0, hopZ[i], k); y = Math.sin(k * Math.PI) * 0.95; sp = 0.7 * Math.sin(Math.min(1, k * 1.3) * Math.PI * 0.5) * (1 - sstep(0.75, 1, k)); }
          else if (t >= hopT[i]) z = hopZ[i];
        }
        if (t < hopT[0] - 0.44) z = zFar;
        return { x: 0, y, z, sp, land: pulse(t, hopT, 0.14) };
      }
      if (t < tJ) { const sq = sstep(tJ - 0.4, tJ - 0.06, t); return { ...startP, sp: 0.06 * Math.sin(t * 7.5) * (1 - sq), land: 0.9 * sq }; }   // pulsing; the squat
      if (t < tK) {
        const u = (t - tJ) / (tK - tJ), q = hop(startP, onYou, u * u * (1.6 - 0.6 * u), leapH);
        return { ...q, sp: SP_LEAP * Math.sin(Math.min(1, u * 1.6) * Math.PI * 0.5), land: 0 };
      }
      const k = sstep(tK, tShut, t);
      return { ...onYou, y: lerp(onYou.y, 0, k), z: lerp(onYou.z, 0.25, k), sp: lerp(SP_LEAP, -0.2, k), land: 0 };
    };
    const coreOf = (B) => ({ x: B.x, y: B.y + half, z: B.z });

    // ---- the camera ------------------------------------------------------------------------------------------
    const smallHits = smalls.map((s) => ({ t: s.t1, side: s.side, amp: 0.8 }));   // knocked away from it
    const cam = (t) => {
      const s = settle(R, t, 0.9);
      const k = sstep(0.8, 1.3, t);
      const c = { x: s.x * (1 - k), y: s.y, z: s.z * (1 - k), yaw: lerp(s.yaw, 0, k), pitch: lerp(s.pitch, -0.02, k), roll: 0, fov: s.fov, near: t >= tJ - 0.1 && t < DUR + 1 ? 0.02 : undefined };
      // The pop pulls the head round; the small ones knock it about and leave it looking off to a side; then back.
      const away = sstep(tPop + 0.1, tPop + 0.7, t) * (1 - sstep(tBack, tBack + 0.45, t));
      c.yaw += lerp(popSide * 0.32, offYaw, sstep(tB + 0.2, tBend + 0.2, t)) * away;
      const kk = kick(t, smallHits);
      c.yaw += kk.yaw; c.pitch += kk.pitch; c.z -= kk.back;
      // Watching it: the eyes go to the core while it hops in, sits, squats, and comes over you.
      const B = bigAt(t), C = coreOf(B);
      const look = Math.atan2(C.y - c.y, Math.max(0.35, C.z - c.z));
      const watch = t < tPop ? 0.5 * sstep(tCore, tCore + 1, t) : t < tBack ? 0.5 * (1 - away) : sstep(tBack, tBack + 0.45, t) * (t < tJ ? 0.75 : 1);
      c.pitch = lerp(c.pitch, clamp(look, -0.5, 0.85), watch);
      c.z -= 0.35 * sstep(tJ - 0.1, tK, t); c.y -= 0.08 * sstep(tJ + 0.25, tK, t);   // backing away from it
      if (t >= tK) {   // it lands on you: crushed down to the floor under it, the head forced down
        const kc = sstep(tK, tShut, t);
        const h = kick(t, [{ t: tK, side: 1, amp: 1.4 }]);
        c.yaw += h.yaw; c.pitch += h.pitch;
        c.y = lerp(c.y, 0.9, kc); c.pitch = lerp(c.pitch, -0.35, kc); c.roll += 0.4 * kc;
        c.fov = s.fov - 10 * kc;
      }
      return shake(c, t, 0.0015 + 0.02 * pulse(t, hopT, 0.2) * (0.6 + 0.2 * hopT.findIndex((h) => h > t - 0.3)) + 0.03 * pulse(t, smalls.map((x) => x.t1), 0.15) + 0.07 * pulse(t, [tK], 0.2) + 0.05 * pulse(t, chews, 0.15), 9);
    };

    // ---- particles: lava spatter on each landing, embers off the small ones, the landing on you, the crush --------
    const lava = [];
    for (let h = 0; h < nHop; h++) for (let i = 0; i < 10; i++) lava.push({ t0: hopT[h] + r() * 0.04, at: [(r() - 0.5) * 1.2, 0.15, hopZ[h] + (r() - 0.5) * 1.2], v: [(r() - 0.5) * 1.8, 1.4 + r() * 1.3, (r() - 0.5) * 1.8], life: 0.9, size: 0.08, tile: 49, color: [1, 0.55, 0.2], grav: 7, fog: false, add: true });
    for (let i = 0; i < 12; i++) lava.push({ t0: tJ + r() * 0.05, at: [startP.x + (r() - 0.5) * 1.2, 0.1, startP.z + (r() - 0.5) * 1.2], v: [(r() - 0.5) * 2, 1.2 + r() * 1.4, (r() - 0.5) * 2], life: 0.8, size: 0.08, tile: 49, color: [1, 0.55, 0.2], grav: 7, fog: false, add: true });
    for (let i = 0; i < 26; i++) lava.push({ t0: tK + r() * 0.08, at: [(r() - 0.5) * 0.9, R.eye - 0.5 + r() * 0.5, 0.35 + r() * 0.5], v: [(r() - 0.5) * 3.2, (r() - 0.1) * 2.5, (r() - 0.3) * 2.4], life: 0.7, size: 0.065, tile: 49, color: [1, 0.6, 0.25], grav: 5, fog: false, add: true });
    smalls.forEach((sm) => { for (let i = 0; i < 8; i++) lava.push({ t0: sm.t1 + r() * 0.04, at: [Math.sin(sm.a) * 0.3, R.eye - 0.35, 0.4 + Math.cos(sm.a) * 0.1], v: [Math.sin(sm.a) * 1.4 + (r() - 0.5) * 1.6, (r() - 0.2) * 2, (r() - 0.5) * 1.4], life: 0.55, size: 0.055, tile: 49, color: [1, 0.6, 0.25], grav: 6, fog: false, add: true }); });
    const sparks = particles(R, partTex, lava);
    const glow = R.ownLight(R.light(0xff5a10, 0, 9, 1.4));
    const sGlow = R.ownLight(R.light(0xff6a20, 0, 5, 1.5));

    // ---- sound: its own, all of it (the slap of a landing, the jump, the pop of lava), and your voice -------------
    const dying = R.torches.filter((tc) => Math.hypot(tc.l.x, tc.l.z) < 26).sort((a, b) => Math.hypot(b.l.x, b.l.z) - Math.hypot(a.l.x, a.l.z));
    const outAt = dying.map((_, i) => tOut + 0.3 * i / Math.max(1, dying.length - 1) + r() * 0.03);
    const sounds = [
      [tThump, "mob.magmacube.big", { at: [0, 0.3, zFar + 3], volume: 0.4, pitch: 0.6 }],
      [tThump + 0.02, "qf.scare.hit", { volume: 0.25 }],
      ...dying.slice(-8).map((tc, i, a) => [outAt[dying.length - a.length + i], "random.fizz", { at: [tc.l.x, tc.l.y, tc.l.z], volume: 0.45, pitch: 0.8 + 0.1 * (i % 3) }]),
      silence(tOut + 0.32, { fade: 0.08 }),
      [tCore, "liquid.lava", { at: [0, 0.4, zFar], volume: 0.6 }],
      [tCore + 0.7, "liquid.lavapop", { at: [0, 0.4, zFar], volume: 0.35, pitch: 0.8 }],
      ...hopT.flatMap((h, i) => [[h - 0.44, "mob.magmacube.jump", { at: [0, 0.4, i ? hopZ[i - 1] : zFar], volume: 0.55, pitch: 0.7 }], [h, "mob.magmacube.big", { at: [0, 0.2, hopZ[i]], volume: 0.8 + 0.15 * i, pitch: 0.55 }], [h + 0.01, "qf.scare.hit", { volume: 0.45 + 0.2 * i }]]),
      [tSit + 0.5, "liquid.lavapop", { at: [0, 0.6, zNear], volume: 0.3, pitch: 0.7 }],
      [tPop, "liquid.lavapop", { at: [popSide * 2.5, 0.3, 1.2], volume: 0.45 }],
      ...smalls.flatMap((sm, i) => [
        [sm.t0, "mob.magmacube.jump", { at: [Math.sin(sm.a) * sm.d, sm.y0, Math.cos(sm.a) * sm.d], volume: 0.9, pitch: 1.35 }],
        [sm.t1, "mob.magmacube.small", { volume: 1.3, pitch: 0.8 + 0.1 * i }],
        ...blow(sm.t1 + 0.005, { volume: i ? 0.8 : 1, gore: false }),
        [sm.t1 + 0.01, "fire.ignite", { volume: 0.9 }]
      ]),
      ...(withSmalls ? [] : [silence(tPop + 0.5, { fade: 0.3 })]),
      [tJ - 0.4, "liquid.lavapop", { at: [startP.x, 0.5, startP.z], volume: 0.5, pitch: 0.6 }],
      [tJ, "mob.magmacube.jump", { at: [startP.x, 0.5, startP.z], volume: 1.3, pitch: 0.5 }],
      ...roar(tK, [["mob.magmacube.big", { pitch: 0.45 }], ["fire.ignite", { pitch: 0.6 }]], { hit: 1 }),
      ...blow(tK + 0.01, { volume: 1.1 }),
      [tShut, "mob.magmacube.big", { volume: 1.3, pitch: 0.5 }], [tShut + 0.01, "qf.scare.crunch", { volume: 1.2 }],
      [tShut + 0.06, "@muffle", { hz: 260, s: DUR - tShut + 2 }],
      ...chews.flatMap((c, i) => [[c, "qf.scare.crunch", { volume: 1 }], [c + 0.02, "mob.magmacube.big", { volume: 1, pitch: 0.5 + 0.05 * i }], [c + 0.03, "liquid.lavapop", { volume: 0.8 }]]),
      ...deathScream(tK + 0.12), ...deathScream(chews[1] + 0.1, { volume: 1.1 }),
      [tShut + 0.5, "fire.fire", { volume: 1 }],
      [DUR, "game.player.die"]
    ];
    const loops = [
      [0.3, tOut + 0.3, "qf.scare.heartbeat", { volume: 0.4 }],
      [tOut + 0.6, tJ, "qf.scare.heartbeat", { volume: 0.55 }],
      [tPop + 0.5, tJ, "qf.scare.breath", { volume: 0.4, fadeIn: 0.5, fadeOut: 0.05 }],
      [tShut, DUR + 0.2, "qf.scare.heartbeat", { volume: 0.9, pitch: 1.5 }],
      [tShut + 0.2, DUR + 0.2, "fire.fire", { volume: 0.8 }]
    ];

    // ---- the frame ------------------------------------------------------------------------------------------
    const beatT = [];   // the core's heart: a double beat about every 0.8 s
    for (let x = tCore; x < DUR; x += 0.8) beatT.push(x, x + 0.22);
    const _v = new THREE.Vector3(), _f = new THREE.Vector3();
    function update(t, f) {
      dying.forEach((tc, i) => { if (t >= outAt[i]) R.snuff(tc); else R.unsnuff(tc); });
      // The big one: far in the black, its glow and the plates it lights; each hop it opens and blazes.
      const B = bigAt(t);
      M.pivot.visible = t >= tCore;
      R.place(M, B.x, B.y, B.z, R.yawTo(B.x, B.z, 0, 0));
      const sq = clamp(0.22 * Math.min(1, B.sp) - 0.22 * B.land, -0.22, 0.22);
      M.anim(Math.asin(sq / 0.22) / 4, 0, {});
      spread(B.sp - sq);
      const air = clamp(B.sp / 0.7);
      const heart = sstep(tCore, tCore + 0.6, t) * (0.35 + 0.65 * pulse(t, beatT, 0.16));
      const blaze = t < tK ? Math.max(heart, air, 0.9 * B.land) : (1 - 0.5 * sstep(tShut, tShut + 0.4, t)) * (0.85 + 0.15 * pulse(t, chews, 0.2));
      M.setOwn(t < tK ? 0.25 + 0.6 * blaze : 0.5 + 0.25 * blaze);   // EntityMagmaCube is fullbright
      for (const m of coreMats) m.emissiveIntensity = 1.15 * Math.max(air, t >= tJ ? 1 : 0.6 * heart) * (t >= tK ? blaze : 1);
      if (coreG) { M.pivot.updateMatrixWorld(true); coreG.localToWorld(_v.set(0, -20 / 16, -2.4 / 16)); glow.position.copy(_v); }
      glow.intensity = (t < tK ? 1.2 * heart + 3.4 * air + (t >= tJ - 0.4 ? 1.2 : 0) : 4 * blaze * (t < tShut ? 1 : 0.4)) * sstep(tCore, tCore + 0.3, t);
      // The small ones: out of the black from a side, burning, into your chest; knocked off, falling, going dark.
      let nearest = null, nd = 99;
      small.forEach((m, i) => {
        const sm = smalls[i]; m.pivot.visible = !!sm && t >= sm.t0 && t < sm.t1 + 0.9;
        if (!m.pivot.visible) return;
        const sx = Math.sin(sm.a) * sm.d, sz = Math.cos(sm.a) * sm.d + 0.2;
        const tx = Math.sin(sm.a) * 0.18, tz = 0.45, ty = R.eye - 0.55;
        let px, py, pz;
        if (t < sm.t1) {
          const u = (t - sm.t0) / (sm.t1 - sm.t0), e = u * u * (1.5 - 0.5 * u);
          px = lerp(sx, tx, e); pz = lerp(sz, tz, e); py = lerp(sm.y0, ty, e) + Math.sin(u * Math.PI) * 0.6;
        } else {
          const d = t - sm.t1;
          px = tx + Math.sin(sm.a) * 1.1 * d; pz = tz + 0.9 * d; py = Math.max(0, ty + 1.0 * d - 9 * d * d);
        }
        R.place(m, px, py, pz, R.yawTo(px, pz, 0, 0));
        m.anim(t * 3 + i, 0, {});
        const hot = t < sm.t1 + 0.1 ? 1 : Math.exp(-(t - sm.t1 - 0.1) / 0.3);
        m.setOwn(0.9 * hot);
        const dd = Math.hypot(px, pz); if (dd < nd) { nd = dd; nearest = { x: px, y: py, z: pz, hot }; }
      });
      if (nearest) { R.L(nearest.x, nearest.y + 0.3, nearest.z, sGlow.position); sGlow.intensity = 2.2 * nearest.hot; } else sGlow.intensity = 0;
      sparks(t);

      // Total black: the bake and the Krypt's lights to nothing, black fog; only what burns is seen.
      const dark = sstep(tOut + 0.05, tOut + 0.4, t);
      const inside = sstep(tShut - 0.15, tShut + 0.05, t);
      f.env = { bake: lerp(1 - 0.2 * sstep(0.2, 1.2, t), 0.012, dark), lights: 1 - dark, fogMul: 1 + 1.2 * dark, fog: [0.0, 0.0, 0.0, dark], expo: 1 - 0.2 * dark, squash: inside * Math.min(1, 0.35 + 0.6 * pulse(t, chews, 0.2)) };
      const splat = pulse(t, smalls.map((x) => x.t1), 0.09), slam = pulse(t, [tK], 0.12);
      f.tints = [[255, 110, 20, 0.4 * splat + 0.5 * slam], [22, 5, 0, 0.75 * inside], [255, 80, 10, 0.3 * inside * pulse(t, chews, 0.25)]];
      f.vig = [40, 8, 0, 0.35 + 0.3 * dark + 0.3 * inside]; f.vigR = 0.85;
      f.fire = Math.max(0.6 * inside, 0.6 * sstep(tK, tK + 0.15, t));
      f.hurt = Math.max(f.hurt || 0, splat, slam);
      f.black = 0.35 * sstep(DUR - 0.25, DUR + 0.6, t);
    }
    return { dur: DUR, hits, cam, update, sounds, loops, deathSide: 1,
      marks: { dread: hopT[0] - 0.2, fake: nSmall ? smalls[0].t1 - 0.1 : tPop + 0.5, lunge: tJ + 0.42, kill: tShut + 0.6 },
      notes: { size, nHop, nSmall, popSide, a0: nSmall ? smalls[0].a : 0, leapH: +leapH.toFixed(2), torches: dying.length, tJ: +tJ.toFixed(2), dur: +DUR.toFixed(2) } };
  }
};
