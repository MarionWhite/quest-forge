// Blaze (v3): heat. The air shimmers and embers rise; an orange glow grows round the bend, and with it the blaze's
// breathing. It rises into view wreathed in smoke and throws one fireball, into the wall beside you. Then it sinks
// back out of sight and its light goes with it. Silence, embers. Either a fireball comes from behind you, past your
// ear, and you turn round to the dark it came from; or its breath is suddenly at your ear and you turn to it. Nothing.
// Turning back, it is there, its rods whirling round your head, and its face drives into yours with the screech.
// After the static it burns you at point blank: you catch fire (the 1.7.10 overlay), the hotbar burns item by item,
// the edges of the view char black, and a man screams himself out.
import { THREE, track, clamp, lerp, sstep, pulse, tex, quad } from "./rig.js";
import { settle, shake, hitsOf, floorFall, particles, smoke, fireBlocks, mulberry } from "./common.js";
import { lunge, lungeFx, screech, faceAnchor, boxOf, silence, deathScream, jit } from "./fnaf.js";

export default {
  death: "Steve was burnt to a crisp whilst fighting Blaze",
  async build(R) {
    const [partTex, ballTex] = await Promise.all([tex("particles"), tex("item_fireball")]);
    // It comes from ahead, round the side of the corridor (a passage or alcove if there is one).
    const op = R.openings.filter((o) => o.z > 2.5 && o.z < 9).sort((a, b) => a.z - b.z)[0];
    const bz = op ? op.z : clamp(R.ahead - 1.5, 3, 7), bxOut = op ? op.side * (op.wall + 1.2) : (R.wallR > R.wallL ? 1 : -1) * 2.5;
    const bx = clamp(bxOut * 0.25, -1.2, 1.2), by = 1.1;
    const B = R.mob("Blaze", { amb: [0.05, 0.05, 0.05], own: true });
    B.anim(0, 0, {}); R.place(B, 0, 0, 4, Math.PI);
    const anchor = faceAnchor(B, B.parts.blazeHead, boxOf("blaze", "blazeHead"));

    // ---- the dice -------------------------------------------------------------------------------------------
    const T_HEAT = R.vary(0.9, 0.25), T_BREATH = T_HEAT + R.vary(0.8, 0.3), T_RISE = T_BREATH + R.vary(1.2, 0.3);
    const F0 = T_RISE + R.vary(0.85, 0.3), tDuck = F0 + R.vary(0.6, 0.3), tSil = tDuck + 0.45;
    const behind = R.chance(0.5), s = R.pick([-1, 1]);
    const tCue = tSil + R.vary(1.3, 0.35);   // the fireball from behind, or the breath at your ear
    const tTurn = tCue + 0.12, turnTo = behind ? s * 2.7 : s * 1.25;
    const tBack = tTurn + (behind ? 0.75 : 0.55) + R.vary(0.9, 0.4), t0 = tBack + 0.2;
    const L = lunge(R, B, { t0, rush: R.vary(0.18, 0.2), hold: R.vary(0.62, 0.15), dist: 0.38, anchor, seed: 37 });
    const tK = L.t3, FK = [tK + 0.05, tK + 0.38, tK + 0.72], T_FALL = tK + 1.75, DUR = tK + 3.0;
    const wallX = (R.wallR > R.wallL ? -R.wallL : R.wallR) * 0.98;
    const hits = hitsOf([[FK[0] + 0.1, 4, 1], [FK[1] + 0.1, 3, -1], [FK[2] + 0.1, 3, 1], [tK + 1.3, 3, -1], [T_FALL + 0.5, 3, 1], [DUR - 0.05, 4, 1]]);
    const shots = [{ t0: F0, t1: F0 + 0.2, from: "blaze", to: [wallX, 1.7, 0.6] }];
    if (behind) shots.push({ t0: tCue - 0.12, t1: tCue + 0.2, from: [s * 0.3, 1.55, -3], to: [s * 0.05, 1.3, clamp(R.ahead - 0.3, 3, 8)] });
    for (const tt of FK) shots.push({ t0: tt - 0.08, t1: tt + 0.1, from: "blaze", to: "cam" });
    const balls = shots.map((sh) => { const q = quad(ballTex, 0.32, 0.32, { alphaTest: 0.1, fog: false }); q.visible = false; R.add(q); return { q, ...sh }; });
    const fires = await fireBlocks(R, [{ at: [wallX * 0.9, 0, 0.6], t0: F0 + 0.25, s: 0.7 }, { at: [0, 0, -0.1], t0: FK[0] + 0.15, s: 0.9 }, { at: [0.7, 0, 0.3], t0: FK[1] + 0.2, s: 0.8 }]);
    const r = mulberry(17 + R.seed);
    const embers = [];
    for (let i = 0; i < 34; i++) embers.push({ t0: T_HEAT + r() * (DUR - T_HEAT), at: [bx + (r() - 0.5) * 2.5, r() * 0.6, bz - 2 + r() * 3.5], v: [(r() - 0.5) * 0.2, 0.6 + r() * 0.8, (r() - 0.5) * 0.2], life: 1.6 + r(), size: 0.035 + r() * 0.03, tile: 49, color: [1, 0.55, 0.2], grav: -0.1, fog: false, add: true });
    for (let i = 0; i < 26; i++) embers.push({ t0: t0 + r() * 0.3, at: [(r() - 0.5) * 0.9, R.eye - 0.2 + r() * 0.5, 0.5 + r() * 0.6], v: [(r() - 0.5) * 2.5, (r() - 0.3) * 2, -1 - r() * 2], life: 0.6, size: 0.05, tile: 49, color: [1, 0.65, 0.25], grav: 3, fog: false, add: true });
    const puffs = particles(R, partTex, [...embers,
      ...[0, 1, 2, 3].flatMap((k) => smoke([bx, by + 0.6, bz], T_RISE - 0.3 + k * 0.55, 5, { spread: 0.7, window: 0.5, life: 1.5, size: 0.32, rise: 0.6, seed: 50 + k })),
      ...smoke([wallX, 1.7, 0.6], F0 + 0.2, 8, { spread: 0.4, window: 0.2, life: 1.2, size: 0.35, rise: 0.7, seed: 60 }),
      ...[0, 1, 2, 3, 4, 5].flatMap((k) => smoke([0, 0.9, 0.6], FK[0] + 0.2 + k * 0.4, 2, { spread: 0.5, window: 0.3, life: 1, size: 0.18, rise: 1.2, seed: 70 + k, dark: 0.3 }))]);
    const glow = R.ownLight(R.light(0xff7a20, 0, 9, 1.3)), hit = R.ownLight(R.light(0xffa040, 0, 6, 1.4));

    // ---- the camera ------------------------------------------------------------------------------------------
    const look = R.yawTo(0, 0, bx, bz);
    const yawK = track([[0, 0], [T_BREATH, 0], [T_RISE + 0.3, look], [F0 + 0.05, look], [F0 + 0.18, look + 0.3 * Math.sign(wallX), "x"], [tDuck, look], [tSil + 0.6, look * 0.5],
      [tTurn, look * 0.5], [tTurn + (behind ? 0.7 : 0.45), turnTo, behind ? "s" : "o"], [tBack, turnTo * 1.03, "l"], [tBack + 0.28, 0, "x"]]);
    const pitchK = track([[0, 0], [T_RISE + 0.3, R.pitchTo(0, R.eye, 0, bx, by + 0.8, bz) * 0.8], [tDuck + 0.4, 0.05], [tSil + 1, -0.08], [tTurn + 0.3, 0.02], [tBack + 0.28, 0.0, "x"]]);
    const cam = (t) => {
      const st = settle(R, t, 0.9);
      const k = sstep(0.8, 1.3, t);
      const c = { x: st.x * (1 - k), y: st.y, z: st.z * (1 - k), yaw: lerp(st.yaw, yawK(t), k), pitch: lerp(st.pitch, pitchK(t), k), roll: 0, fov: st.fov, near: t >= tBack ? 0.02 : undefined };
      if (behind) { const fl = pulse(t, [tCue - 0.02], 0.12); c.yaw += -s * 0.12 * fl; c.roll += s * 0.06 * fl; }
      // Burning: you stagger back, then go down.
      const burn = sstep(tK, tK + 0.8, t);
      c.z -= 0.5 * burn; c.yaw += burn * Math.sin(t * 2.3) * 0.25; c.roll += burn * Math.sin(t * 3.1) * 0.1; c.pitch += -0.15 * burn;
      floorFall(c, t, T_FALL, { d: 0.5, side: 1, roll: 1.1, y: 0.28, pitch: 0.2, back: 0.2 });
      c.fov += 10 * pulse(t, [L.t1], 0.12);
      return shake(c, t, 0.002 + L.shake(t) + 0.02 * pulse(t, [F0 + 0.2, ...FK.map((x) => x + 0.1)], 0.2) + 0.01 * burn, 8);
    };

    // ---- sound --------------------------------------------------------------------------------------------
    const S2 = screech(L, [["mob.blaze.hit", { pitch: 0.5 }], ["mob.blaze.breathe", { pitch: 0.6, volume: 1.3 }], ["fire.ignite", { pitch: 0.7 }]]);
    const sounds = [
      [T_HEAT, "fire.fire", { at: [bxOut, 1, bz], volume: 0.5 }],
      [T_BREATH, "mob.blaze.breathe", { at: [bxOut, 1.5, bz], volume: 0.8 }], [T_BREATH + 0.9, "mob.blaze.breathe", { at: [(bx + bxOut) / 2, 1.5, bz], volume: 1 }],
      [T_RISE, "mob.blaze.breathe", { at: [bx, by + 0.8, bz], volume: 1, pitch: 0.85 }], [T_RISE + 0.05, "qf.scare.stinger", { volume: 0.5 }],
      [F0, "mob.ghast.fireball", { at: [bx, by + 0.8, bz], volume: 1 }], [F0 + 0.2, "random.fizz", { at: [wallX, 1.7, 0.6], volume: 1 }],
      [tDuck, "mob.blaze.breathe", { at: [bxOut, 1, bz], volume: 0.7, pitch: 0.8 }],
      silence(tSil, { fade: 0.3 }),
      ...(behind ? [[tCue - 0.14, "mob.ghast.fireball", { at: [s * 0.3, 1.6, -2.5], volume: 1.1 }], [tCue - 0.02, "qf.scare.stinger", { volume: 0.85 }], [tCue + 0.2, "random.fizz", { at: [0, 1.3, clamp(R.ahead - 0.3, 3, 8)], volume: 0.9 }]]
        : [[tCue, "mob.blaze.breathe", { at: [s * 0.7, 1.6, -0.2], volume: 0.45, pitch: 0.9 }]]),
      ...S2.sounds,
      ...FK.map((tt) => [tt - 0.08, "mob.ghast.fireball", { volume: 1 }]), ...FK.map((tt) => [tt + 0.1, "fire.ignite", { volume: 1.1 }]),
      [tK + 0.15, "fire.fire", { volume: 1 }],
      ...hits.map((h) => [h.t, "game.player.hurt"]), ...deathScream(tK + 0.25), ...deathScream(T_FALL - 0.1, { volume: 1.1, under: false }),
      [DUR - 0.6, "mob.blaze.breathe", { volume: 1 }],
      [DUR, "game.player.die"], [DUR, "@muffle", { hz: 500, s: 2.5 }]
    ];
    const loops = [
      [0.5, tSil, "qf.scare.heartbeat", { volume: 0.45 }], [T_HEAT, tSil, "qf.scare.drone", { volume: 0.45, fadeIn: 1.5, fadeOut: 0.1, bus: "sfx" }],
      [tSil + 0.8, tBack, "qf.scare.heartbeat", { volume: 0.35, fadeIn: 0.6, fadeOut: 0.02 }],
      ...S2.loops,
      [tK + 0.1, DUR + 0.5, "fire.fire", { volume: 0.9, fadeIn: 0.2 }], [tK, DUR + 0.2, "qf.scare.heartbeat", { volume: 0.8, pitch: 1.5 }]
    ];

    // ---- the frame ------------------------------------------------------------------------------------------
    const _w = new THREE.Vector3();
    function update(t, f) {
      const cl = R.toLocal(R.camera.position);
      // Out from the side and up; the fireball; back down and out of sight; then in front of your face.
      let x, y, z, vis;
      if (t < tBack - 0.05) {
        const out = sstep(T_RISE - 0.5, T_RISE + 0.4, t) * (1 - sstep(tDuck, tDuck + 0.5, t)), rise = sstep(T_RISE - 0.2, T_RISE + 0.6, t) * (1 - sstep(tDuck, tDuck + 0.45, t));
        vis = t > T_RISE - 0.6 && t < tDuck + 0.55;
        x = lerp(bxOut, bx, out); y = lerp(0.2, by, rise) + Math.sin(t * 2.2) * 0.08; z = bz;
      } else {
        const fy = R.eye - 1.5;   // its head at your eyes, a metre off
        vis = true; x = cl.x; z = cl.z + 0.95; y = fy + Math.sin(t * 2.2) * 0.05;
        if (t >= tK) { z = cl.z + 1.6; y = fy + 0.1 - 0.4 * sstep(T_FALL, T_FALL + 0.6, t); }
      }
      B.pivot.visible = vis;
      R.place(B, x, y, z, R.yawTo(x, z, cl.x, cl.z));
      B.anim(t * (t >= tBack ? 2.2 : 1), 0, {});
      if (t >= t0 && t < tK) {
        L.apply(t);
        // A rod passing between the lens and the face would fill the frame: those near the lens are left out.
        B.pivot.updateMatrixWorld(true);
        for (let i = 0; i < 12; i++) { const g = B.parts["blazeSticks" + i]; if (g) { g.getWorldPosition(_w); g.visible = _w.distanceTo(R.camera.position) > 0.42; } }
      }
      B.setOwn((t >= tBack ? (t >= t0 && t < tK ? 0.42 : 0.6) : 0.6) + 0.4 * pulse(t, [F0, ...FK], 0.25));   // (dimmer in the lens: the face must read)
      R.L(x, y + 1.2, z - 0.4, glow.position);
      glow.intensity = vis ? (2.5 * sstep(T_HEAT, T_RISE, t) + 2.5 * sstep(T_RISE - 0.2, T_RISE + 0.6, t)) * (t < tBack ? 1 : 0.45) + 4 * pulse(t, [F0, ...FK], 0.2) : 0.6 * sstep(T_HEAT, T_RISE, t) * (1 - sstep(tDuck, tSil + 0.5, t));
      for (const b of balls) {
        const k = (t - b.t0) / (b.t1 - b.t0);
        b.q.visible = k >= 0 && k < 1;
        if (!b.q.visible) continue;
        const fr = b.from === "blaze" ? [x, y + 1.5, z] : b.from, to = b.to === "cam" ? [cl.x, cl.y - 0.15, cl.z + 0.15] : b.to;
        R.at(b.q, lerp(fr[0], to[0], k), lerp(fr[1], to[1], k), lerp(fr[2], to[2], k)); b.q.quaternion.copy(R.camera.quaternion);
      }
      const hb = balls.map((b) => [b, pulse(t, [b.t1], 0.25)]).sort((p, q) => q[1] - p[1])[0];
      if (hb && hb[1] > 0.01) { const to = hb[0].to === "cam" ? [cl.x, cl.y, cl.z + 0.3] : hb[0].to; R.L(to[0] * 0.9, to[1] + 0.2, to[2], hit.position); hit.intensity = 9 * hb[1]; } else hit.intensity = 0;
      fires(t); puffs(t);
      const heat = sstep(T_HEAT, T_RISE, t) * (1 - 0.5 * sstep(tDuck, tSil + 1, t) + 0.5 * sstep(tBack, tBack + 0.2, t)), burn = sstep(tK, tK + 0.25, t);
      const sil = sstep(tSil, tSil + 0.6, t) * (1 - sstep(tBack, tBack + 0.1, t));
      f.env = { nausea: 0.12 * heat + 0.15 * burn, bake: 1 - 0.2 * sstep(0.2, 1.2, t) - 0.3 * sil, lights: 1 - 0.4 * sil, fogMul: 1 + 0.6 * heat, fog: [0.12, 0.05, 0.02, 0.5 * heat] };
      f.tints = [[255, 110, 30, 0.05 * heat + 0.12 * burn]];
      f.vig = [40, 10, 0, 0.3 + 0.25 * heat + 0.2 * sil]; f.vigR = 0.9;
      f.fire = burn;
      f.burnt = [0, 1, 2, 3, 4].map((i) => t > tK + 0.5 + i * 0.35);
      f.char = 0.62 * sstep(tK + 0.6, DUR, t);
      lungeFx(L, t, f);
    }
    return { dur: DUR, hits, cam, update, sounds, loops, deathSide: 1,
      marks: { dread: T_RISE + 0.5, fake: behind ? tCue + 0.02 : tTurn + 0.5, lunge: L.t1 + 0.1, kill: tK + 0.9 },
      notes: { behind, side: s, t0: +t0.toFixed(2), dur: +DUR.toFixed(2) } };
  }
};
