// Magma Cube (v3): a thump somewhere ahead. Every torch dies at once: total black. Then, far off in it, a single
// orange core pulsing like a heart. Thump, it comes closer; thump, closer. The glow goes out. Silence. A pop off to
// one side; the head turns to it. Small cubes leap at your face out of the black from every side, burning, one after
// another (or the big one comes first). Black again, the heart racing. Then the big one is there: its plates open
// like a jaw on the blazing core, and it drives into the lens with the screech. The jaw closes over you; inside it
// is black and orange, it chews, and a man screams himself out.
import { THREE, clamp, lerp, sstep, pulse, tex } from "./rig.js";
import { settle, shake, hitsOf, particles, mulberry } from "./common.js";
import { lunge, lungeFx, screech, faceAnchor, boxOf, silence, deathScream, jit } from "./fnaf.js";

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
    const anchor = faceAnchor(M, coreG, boxOf("magmaCube", CORE)); anchor.y += 1.6 * px;   // between the lifted eyes and the core
    // The jaw: the four upper plates (the eyes are on them) lift off the core, fanned like a deck; the four lower ones
    // hinge down at the back of the split, the outer ones widest. The core blazes in the gap.
    const HY = -20 / 16, HZ = 4 / 16;
    const openJaw = (o) => {
      LAYERS.forEach((n, i) => {
        const g = M.parts[n]; if (!g) return;
        if (i < 4) { g.rotation.set(0.12 * o * (4 - i) / 4, 0, 0); g.position.set(0, o * (2.4 + 0.5 * (3 - i)) / 16, 0); return; }
        const th = -0.5 * o * (0.5 + 0.5 * (i - 3) / 4), c = Math.cos(th), s = Math.sin(th);
        g.rotation.set(th, 0, 0);
        g.position.set(0, HY - (HY * c - HZ * s), HZ - (HY * s + HZ * c));
      });
    };
    const small = [0, 1, 2, 3, 4].map(() => R.mob("LavaSlime", { size: 1, amb: [0.9, 0.9, 0.9], own: true }));

    // ---- the dice -------------------------------------------------------------------------------------------
    const zFar = clamp(R.ahead - half - 0.6, 4, 8.5), zNear = clamp(R.ahead - half - 0.3, 1.9, 2.6);
    const tThump = R.vary(1.25, 0.25), tOut = tThump + R.vary(1.0, 0.3), tCore = tOut + R.vary(1.4, 0.35);
    const nHop = R.chance(0.5) ? 3 : 2;
    const hopT = [], hopZ = [];
    let th = tCore + R.vary(1.2, 0.3);
    for (let i = 0; i < nHop; i++) { hopT.push(th); hopZ.push(lerp(zFar, zNear, (i + 1) / nHop)); th += R.vary(0.75, 0.3); }
    const tGone = hopT[nHop - 1] + R.vary(0.75, 0.35);
    const popSide = R.pick([-1, 1]), tPop = tGone + R.vary(1.0, 0.35);
    const early = R.chance(0.6);   // the small ones come first, as the fake-out; else they lead straight into it
    const nSmall = 3 + Math.floor(R.rand() * 3);
    const tB = early ? tPop + R.vary(0.9, 0.35) : tPop + R.vary(1.3, 0.35);
    const angs = [-1.15, 1.0, -0.45, 0.6, -0.8, 1.25].sort(() => R.rand() - 0.5).slice(0, nSmall);
    const smalls = angs.map((a, i) => {
      const t1 = tB + 0.3 + i * R.vary(0.2, 0.35) + (i ? 0 : 0.05);
      const high = R.chance(0.35) && R.ceil > 2.8;
      return { a, t0: t1 - 0.32, t1, y0: high ? Math.min(R.ceil - 0.3, 3) : 0.25, d: R.vary(2.4, 0.2), side: Math.sign(a) };
    });
    const tBend = smalls[smalls.length - 1].t1;
    const t0 = early ? tBend + R.vary(1.9, 0.35) : tBend + R.vary(0.28, 0.2);
    const fromAbove = R.ceil >= 3.4 && R.chance(0.35);
    const startP = fromAbove ? { x: 0.1, y: Math.min(R.ceil - size * 0.5, 3.2), z: 1.2 } : { x: 0.05, y: 0, z: zNear };
    const L = lunge(R, M, { t0, rush: R.vary(0.22, 0.15), hold: R.vary(0.65, 0.15), dist: 0.46 * size, anchor, seed: 43, rise: fromAbove ? -0.9 : 0 });
    const tK = L.t3, tShut = tK + 0.4, chews = [tShut + 0.05, tShut + R.vary(0.7, 0.2), tShut + 1.35], DUR = tShut + 2.3;
    const hits = hitsOf([...smalls.map((s, i) => [s.t1, i ? 1 : 2, s.side]), [tK + 0.05, 4, 1], ...chews.map((c, i) => [c, 3 - (i > 1 ? 1 : 0), i % 2 ? 1 : -1]), [DUR, 3, -1]]);
    const offYaw = early ? -smalls[smalls.length - 1].side * 0.32 : popSide * 0.2;   // knocked round, away from the last one

    // ---- the camera ------------------------------------------------------------------------------------------
    const smallHits = smalls.map((s) => s.t1);
    const cam = (t) => {
      const s = settle(R, t, 0.9);
      const k = sstep(0.8, 1.3, t);
      const c = { x: s.x * (1 - k), y: s.y, z: s.z * (1 - k), yaw: lerp(s.yaw, 0, k), pitch: lerp(s.pitch, -0.02, k), roll: 0, fov: s.fov, near: t >= t0 - 0.1 && t < DUR ? 0.02 : undefined };
      // The pop pulls the head round; the small ones knock it about and leave it looking off to a side.
      c.yaw += popSide * 0.28 * sstep(tPop + 0.1, tPop + 0.7, t) * (1 - sstep(tB, tB + 0.3, t));
      c.yaw += offYaw * sstep(tB + 0.2, tBend + 0.3, t);
      for (const sm of smalls) { const kk = t >= sm.t1 ? Math.exp(-(t - sm.t1) / 0.18) : 0; c.yaw -= sm.side * 0.16 * kk; c.pitch += 0.12 * kk; c.roll += sm.side * 0.1 * kk; }
      c.pitch += -0.06 * sstep(tGone, tGone + 1.5, t) * (1 - sstep(tB, tB + 0.3, t));   // the head drops, listening
      if (t >= tShut - 0.2) {   // swallowed: pressed down, the view jammed and chewed
        const kk = sstep(tShut - 0.2, tShut + 0.2, t);
        c.y = lerp(c.y, 0.9, kk); c.pitch = lerp(c.pitch, -0.35, kk); c.roll += 0.4 * kk;
        c.fov = s.fov - 10 * kk;
      }
      c.fov += 10 * pulse(t, [L.t1], 0.12);
      return shake(c, t, 0.0015 + L.shake(t) + 0.02 * pulse(t, hopT, 0.2) + 0.03 * pulse(t, smallHits, 0.15) + 0.05 * pulse(t, chews, 0.15), 9);
    };

    // ---- particles: lava spatter on each landing, embers off the small ones, the chew ----------------------------
    const lava = [];
    for (let h = 0; h < nHop; h++) for (let i = 0; i < 9; i++) lava.push({ t0: hopT[h] + r() * 0.04, at: [(r() - 0.5) * 1.2, 0.15, hopZ[h] + (r() - 0.5) * 1.2], v: [(r() - 0.5) * 1.6, 1.4 + r() * 1.2, (r() - 0.5) * 1.6], life: 0.9, size: 0.08, tile: 49, color: [1, 0.55, 0.2], grav: 7, fog: false, add: true });
    for (let i = 0; i < 30; i++) lava.push({ t0: L.t0 + r() * 0.3, at: [(r() - 0.5) * 0.8, R.eye - 0.3 + r() * 0.5, 0.6 + r() * 0.6], v: [(r() - 0.5) * 3, (r() - 0.2) * 2.5, -1 - r() * 2], life: 0.6, size: 0.06, tile: 49, color: [1, 0.6, 0.25], grav: 4, fog: false, add: true });
    const sparks = particles(R, partTex, lava);
    const glow = R.ownLight(R.light(0xff5a10, 0, 8, 1.4));
    const sGlow = R.ownLight(R.light(0xff6a20, 0, 5, 1.5));

    // ---- sound --------------------------------------------------------------------------------------------
    const dying = R.torches.filter((tc) => Math.hypot(tc.l.x, tc.l.z) < 26).sort((a, b) => Math.hypot(b.l.x, b.l.z) - Math.hypot(a.l.x, a.l.z));
    const outAt = dying.map((_, i) => tOut + 0.3 * i / Math.max(1, dying.length - 1) + r() * 0.03);
    const S2 = screech(L, [["mob.magmacube.big", { pitch: 0.45 }], ["mob.ghast.scream", { pitch: 0.45, volume: 1.1 }], ["fire.ignite", { pitch: 0.6 }]]);
    const late = R.chance(0.5);   // one small sound before the lunge, or none at all
    const sounds = [
      [tThump, "mob.magmacube.big", { at: [0, 0.3, zFar + 3], volume: 0.4, pitch: 0.6 }],
      [tThump + 0.02, "qf.scare.hit", { volume: 0.25 }],
      ...dying.slice(-8).map((tc, i, a) => [outAt[dying.length - a.length + i], "random.fizz", { at: [tc.l.x, tc.l.y, tc.l.z], volume: 0.45, pitch: 0.8 + 0.1 * (i % 3) }]),
      silence(tOut + 0.32, { fade: 0.08 }),
      [tCore, "liquid.lava", { at: [0, 0.4, zFar], volume: 0.6 }],
      [tCore + 0.6, "qf.scare.whisper", { volume: 0.2 }],
      ...hopT.flatMap((h, i) => [[h - 0.42, "mob.magmacube.jump", { at: [0, 0.4, i ? hopZ[i - 1] : zFar], volume: 0.5, pitch: 0.7 }], [h, "mob.magmacube.big", { at: [0, 0.2, hopZ[i]], volume: 0.75 + 0.15 * i, pitch: 0.55 }], [h + 0.01, "qf.scare.hit", { volume: 0.45 + 0.2 * i }]]),
      silence(tGone),
      [tPop, "liquid.lavapop", { at: [popSide * 2.5, 0.3, 1.2], volume: 0.4 }],
      ...smalls.flatMap((sm, i) => [
        [sm.t0, "mob.magmacube.jump", { at: [Math.sin(sm.a) * sm.d, sm.y0, Math.cos(sm.a) * sm.d], volume: 0.9, pitch: 1.3 }],
        [sm.t1, "mob.magmacube.small", { volume: 1.3, pitch: 0.8 + 0.1 * i }],
        [sm.t1 + 0.005, "qf.scare.hit", { volume: 1.0 }],
        [sm.t1 + 0.01, "fire.ignite", { volume: 0.9 }],
        [sm.t1 + 0.02, "game.player.hurt", { volume: 0.8 }]
      ]),
      [smalls[0].t1 - 0.01, "qf.scare.stinger", { volume: early ? 1.1 : 0.8 }],
      [smalls[0].t1, "qf.scare.shriek", { volume: 0.55 }],
      ...(early ? [silence(tBend + R.vary(0.9, 0.3), { fade: 0.4 }), ...(late ? [[t0 - R.vary(0.45, 0.3), "liquid.lavapop", { at: [0, 0.4, zNear], volume: 0.25, pitch: 0.7 }]] : [])] : []),
      ...S2.sounds,
      [tShut, "mob.magmacube.big", { volume: 1.3, pitch: 0.5 }], [tShut + 0.01, "qf.scare.crunch", { volume: 1.2 }],
      [tShut + 0.06, "@muffle", { hz: 260, s: DUR - tShut + 2 }],
      ...chews.flatMap((c, i) => [[c, "qf.scare.crunch", { volume: 1 }], [c + 0.02, "mob.magmacube.big", { volume: 1, pitch: 0.5 + 0.05 * i }], [c + 0.03, "liquid.lavapop", { volume: 0.8 }]]),
      ...deathScream(tK + 0.12), ...deathScream(chews[1] + 0.1, { volume: 1.1 }),
      [tShut + 0.5, "fire.fire", { volume: 1 }],
      [DUR, "game.player.die"]
    ];
    const loops = [
      [0.3, tOut + 0.3, "qf.scare.heartbeat", { volume: 0.4 }],
      [tOut + 0.6, tGone, "qf.scare.heartbeat", { volume: 0.55 }],
      [tCore, tGone, "qf.scare.drone", { volume: 0.5, fadeIn: 1.0, fadeOut: 0.05, bus: "sfx" }],
      [tPop + 0.5, smalls[0].t0, "qf.scare.breath", { volume: 0.4, fadeIn: 0.5, fadeOut: 0.05 }],
      ...(early ? [[tBend + 0.15, tBend + 0.9, "qf.scare.heartbeat", { volume: 0.8, pitch: 1.35 }]] : []),
      ...S2.loops,
      [tShut, DUR + 0.2, "qf.scare.heartbeat", { volume: 0.9, pitch: 1.5 }],
      [tShut + 0.2, DUR + 0.2, "fire.fire", { volume: 0.8 }]
    ];

    // ---- the frame ------------------------------------------------------------------------------------------
    const beatT = [];   // the core's heart: a double beat about every 0.8 s, then a flare on each landing
    for (let x = tCore; x < tGone; x += 0.8) beatT.push(x, x + 0.22);
    const _v = new THREE.Vector3(), _f = new THREE.Vector3();
    function update(t, f) {
      dying.forEach((tc, i) => { if (t >= outAt[i]) R.snuff(tc); else R.unsnuff(tc); });
      // The big one: far in the black (only its glow), hopping in, then gone dark; then the lunge and the swallow.
      let x = 0, y = 0, z = zFar, lit = 0;
      if (t >= tCore && t < tGone) {
        lit = sstep(tCore, tCore + 0.6, t) * (0.35 + 0.65 * pulse(t, beatT, 0.16) + 0.8 * pulse(t, hopT, 0.25)) * (1 - sstep(tGone - 0.12, tGone, t));
        for (let i = 0; i < nHop; i++) {
          const a = i ? hopZ[i - 1] : zFar, d = 0.42;
          if (t >= hopT[i] - d && t < hopT[i]) { const k = (t - hopT[i] + d) / d; z = lerp(a, hopZ[i], k); y = Math.sin(k * Math.PI) * 0.9; }
          else if (t >= hopT[i]) z = hopZ[i];
        }
      }
      const inLunge = t >= t0;
      M.pivot.visible = (t >= tCore && t < tGone) || inLunge;
      if (!inLunge) {
        R.place(M, x, y, z, R.yawTo(x, z, 0, 0));
        const land = pulse(t, hopT, 0.14), sq = -0.22 * land + (y > 0.1 ? 0.18 : 0);
        M.anim(Math.asin(clamp(sq / 0.22, -1, 1)) / 4, 0, {});
        M.setOwn(0.85 * lit);
        for (const m of coreMats) m.emissiveIntensity = 0;
        R.L(x, y + half, z - half - 0.3, glow.position); glow.intensity = 3.2 * lit;
      } else {
        R.place(M, startP.x, startP.y, startP.z, R.yawTo(startP.x, startP.z, 0, 0));
        M.anim(0, 0, {});
        const open = t < tK ? sstep(t0, L.t1 + 0.05, t) * (0.85 + 0.15 * jit(t, 51)) : (1 - sstep(tK + 0.05, tShut, t)) * (0.9 + 0.1 * jit(t, 51));
        openJaw(open);
        L.apply(t);
        if (t >= tK) {   // it comes on over the lens: the plates close on you
          R.camera.getWorldDirection(_f);
          M.pivot.position.addScaledVector(_f, -0.46 * size * sstep(tK, tShut, t));
        }
        const blaze = (t < tK ? 1 : 1 - 0.5 * sstep(tShut, tShut + 0.4, t)) * (0.8 + 0.2 * jit(t, 61, 14));
        M.setOwn(0.5 + 0.25 * blaze);   // EntityMagmaCube is fullbright
        for (const m of coreMats) m.emissiveIntensity = 1.15 * blaze;
        if (coreG) { M.pivot.updateMatrixWorld(true); coreG.localToWorld(_v.set(0, -20 / 16, -2.2 / 16)); glow.position.copy(_v); }
        glow.intensity = 4 * blaze * (t < tShut ? 1 : 0.4);
      }
      // The small ones: out of the black from every side, burning, into the lens; knocked off, falling, going dark.
      let nearest = null, nd = 99;
      small.forEach((m, i) => {
        const sm = smalls[i]; m.pivot.visible = !!sm && t >= sm.t0 && t < sm.t1 + 0.7;
        if (!m.pivot.visible) return;
        const cl = R.toLocal(R.camera.position);
        R.camera.getWorldDirection(_f);
        const tgt = R.toLocal(_v.copy(R.camera.position).addScaledVector(_f, 0.32));
        const sx = cl.x + Math.sin(sm.a) * sm.d, sz = cl.z + Math.cos(sm.a) * sm.d;
        let px, py, pz;
        if (t < sm.t1) {
          const u = (t - sm.t0) / (sm.t1 - sm.t0), e = u * u * (1.5 - 0.5 * u);
          px = lerp(sx, tgt.x, e); pz = lerp(sz, tgt.z, e); py = lerp(sm.y0, tgt.y - 0.25, e) + Math.sin(u * Math.PI) * 0.7;
        } else {
          const d = t - sm.t1;
          px = tgt.x + Math.sin(sm.a) * 0.6 * d; pz = tgt.z + Math.cos(sm.a) * 0.6 * d - 0.5 * d; py = Math.max(0, tgt.y - 0.25 + 1.2 * d - 9 * d * d);
        }
        R.place(m, px, py, pz, R.yawTo(px, pz, cl.x, cl.z));
        m.anim(t * 3 + i, 0, {});
        const hot = t < sm.t1 + 0.1 ? 1 : Math.exp(-(t - sm.t1 - 0.1) / 0.25);
        m.setOwn(0.9 * hot);
        const dd = Math.hypot(px - cl.x, pz - cl.z); if (dd < nd) { nd = dd; nearest = { x: px, y: py, z: pz, hot }; }
      });
      if (nearest) { R.L(nearest.x, nearest.y + 0.3, nearest.z, sGlow.position); sGlow.intensity = 2.2 * nearest.hot; } else sGlow.intensity = 0;
      sparks(t);

      // Total black: the bake and the Krypt's lights to nothing, black fog; only what burns is seen.
      const dark = sstep(tOut + 0.05, tOut + 0.4, t);
      const inside = sstep(tShut - 0.15, tShut + 0.05, t);
      f.env = { bake: lerp(1 - 0.2 * sstep(0.2, 1.2, t), 0.012, dark), lights: 1 - dark, fogMul: 1 + 1.2 * dark, fog: [0.0, 0.0, 0.0, dark], expo: 1 - 0.2 * dark, squash: inside * Math.min(1, 0.35 + 0.6 * pulse(t, chews, 0.2)) };
      const splat = pulse(t, smallHits, 0.09);
      f.tints = [[255, 110, 20, 0.45 * splat], [22, 5, 0, 0.9 * inside], [255, 80, 10, 0.3 * inside * pulse(t, chews, 0.25)]];
      f.vig = [40, 8, 0, 0.35 + 0.3 * dark + 0.3 * inside]; f.vigR = 0.85;
      f.fire = Math.max(0.9 * inside, 0.7 * pulse(t, smallHits, 0.3));
      f.hurt = Math.max(f.hurt || 0, splat);
      f.black = 0.35 * sstep(DUR - 0.25, DUR + 0.6, t);
      lungeFx(L, t, f);
    }
    return { dur: DUR, hits, cam, update, sounds, loops, deathSide: 1,
      marks: { dread: (tCore + tGone) / 2, fake: early ? smalls[0].t1 - 0.04 : tPop + 0.4, lunge: L.t1 + 0.12, kill: tShut + 0.6 },
      notes: { size, nHop, early, nSmall, fromAbove, torches: dying.length, t0: +t0.toFixed(2), dur: +DUR.toFixed(2) } };
  }
};
