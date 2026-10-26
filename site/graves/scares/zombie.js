// Zombie: the look-back. A groan from the side passage (or behind); the head turns to it, slowly, and it is empty.
// Every sound goes. The head comes back round, and then one of two things, a coin toss each play:
//   - it is there, at your face, and it lunges (FNAF: jaw split open, eyes lit, the screech, static);
//   - nothing is there either. A stinger with nothing behind it; you breathe out; the heartbeat slows; sometimes a
//     torch flickers and for one frame it stands far down the corridor. Silence. A wet breath at your ear: it has
//     been beside you the whole time, and it lunges in from the side.
// Then the kill: it bites, more arms come out of the dark and drag you down until hands cover the view.
import { THREE, track, clamp, lerp, sstep, pulse } from "./rig.js";
import { settle, shake, hitsOf, lensLimbs, glowEyes } from "./common.js";
import { lunge, lungeFx, screech, splitJaw, faceAnchor, boxOf, silence, deathScream, glimpse, jit } from "./fnaf.js";

export default {
  death: "Steve was slain by Zombie",
  async build(R) {
    // Where the groan comes from: the nearest side passage beside or behind, else over the shoulder.
    const p = R.passages.find((q) => q.z < 5 && q.dist < 11);
    const o = !p && R.openings.filter((q) => q.z < 3 && q.z > -6).sort((a, b) => Math.abs(a.z) - Math.abs(b.z))[0];
    let gx, gz;
    if (p) { gx = p.x + p.side * 2.5; gz = p.z; }
    else if (o) { gx = o.side * (o.wall + 1.8); gz = o.z; }
    else { gx = -0.8; gz = -Math.min(6, R.behind - 1); }
    let turn = R.yawTo(0, 0, gx, gz);
    if (Math.abs(turn) < 1.0) turn = Math.sign(turn || 1) * 1.0;
    turn = clamp(turn, -2.5, 2.5);
    const side = Math.sign(turn) || 1;
    const near = clamp(R.ahead - 0.6, 0.55, 0.82);

    // ---- the dice -------------------------------------------------------------------------------------
    const atFace = R.chance(0.38);            // it is there when the head comes back
    const glimpseFar = !atFace && R.chance(0.45);
    const tG = 0.9 + R.vary(0.7, 0.5);       // the groan
    const tT0 = tG + R.vary(0.35, 0.4), tT1 = tT0 + R.vary(1.45, 0.25);   // the turn to it
    const tB0 = tT1 + R.vary(1.2, 0.45), tB1 = tB0 + R.vary(0.85, 0.2);   // the look back
    let t0, tFake = null, tSil, tBreath = null, tGl = [];
    if (atFace) { tSil = tB0 - 0.05; t0 = tB1 - 0.12; }
    else {
      tFake = tB1 - 0.04;
      const relax = R.vary(2.0, 0.45);
      if (glimpseFar) tGl = [tFake + relax * 0.35];
      tSil = tFake + relax * 0.62; tBreath = tSil + (relax * 0.38) * R.vary(0.55, 0.3);
      t0 = tFake + relax;
    }
    const lside = atFace ? 0 : -side;          // the lunge comes from the other side
    const z1 = R.mob("Zombie", { amb: [0.26, 0.25, 0.25], own: true });
    const jaw = splitJaw(z1, [{ part: z1.parts.head, box: boxOf("zombie", "bipedHead"), rows: 2 }, { part: z1.parts.headwear, box: boxOf("zombie", "bipedHeadwear"), rows: 2 }]);
    // Pinpoint pupils in the middle of the black sockets, lit deep red.
    const eyes = glowEyes(R, z1, [[-2, -3.5, -4.07, 0.7, 0.7], [2, -3.5, -4.07, 0.7, 0.7]], [0.85, 0.02, 0.0], { halo: 0.14, glow: 0.45 });
    z1.anim(0, 0, { walk: 0 }); R.place(z1, 0, 0, 2, Math.PI);
    const anchor = faceAnchor(z1, z1.parts.head, boxOf("zombie", "bipedHead")); anchor.y -= 0.07;   // aim a little low: the open mouth mid-frame
    const start = atFace ? { x: 0.05, z: 0.95 } : { x: lside * clamp(Math.min(lside < 0 ? R.wallL : R.wallR) - 0.4, 0.55, 0.85), z: 0.1 };
    const L = lunge(R, z1, { t0, rush: R.vary(0.2, 0.15), hold: R.vary(0.62, 0.15), dist: 0.36, anchor, seed: 5, side: lside * 0.15 });
    const tK = L.t3, T_DRAG = tK + 1.25, DUR = tK + 3.4;

    // Two more, out of the dark on either side, and one from behind (the kill).
    const wl = Math.min(R.wallL, 3.2), wr = Math.min(R.wallR, 3.2);
    const others = [
      { m: R.mob("Zombie", { amb: [0.2, 0.2, 0.2] }), from: [-wl + 0.4, 3.2], to: [-1.15, -0.25], t0: tK + 0.85, lean: -0.47 },
      { m: R.mob("Zombie", { amb: [0.2, 0.2, 0.2] }), from: [wr - 0.4, 2.6], to: [1.1, -0.55], t0: tK + 1.1, lean: -0.47 },
      { m: R.mob("Zombie", { amb: [0.2, 0.2, 0.2] }), from: [0.3, -Math.min(R.behind - 0.5, 4)], to: [0.1, -1.6], t0: tK + 1.35, lean: -0.5 }
    ];
    const face = R.ownLight(R.light(0xffb070, 0, 2.4, 1.4));   // a cold sliver of light from the corridor on its face

    const hits = hitsOf([[tK + 0.02, 5, 1], [tK + 0.6, 5, -1], [tK + 1.15, 3, 1], [tK + 2.3, 4, -1], [tK + 2.95, 3, 1]]);
    // The head: the slow turn to the groan, the slow turn back; a flinch at the stinger; snapped toward the lunge.
    const yaw = track([[0, 0], [tT0, 0], [tT1, turn], [tB0, turn, "h"], [tB1, 0.0], ...(tFake ? [[tFake + 0.12, 0.1 * side, "x"], [tFake + 0.9, 0.0]] : []),
      ...(t0 > tB1 + 0.05 ? [[t0, 0]] : []), [L.t1, lside * 0.32, "x"], [tK, 0.04 * side, "h"], [T_DRAG, 0.0], [tK + 2.9, -0.25 * side]]);
    const pitch = track([[0, 0], [tT0, -0.03], [tT1, -0.08], [tB1, -0.04], ...(tFake ? [[tFake + 0.12, 0.05, "x"], [tFake + 1.2, -0.12], [t0 - 0.05, -0.1]] : []),
      [L.t1, 0.03, "x"], [tK, 0.06, "h"], [tK + 0.4, 0.12], [T_DRAG, 0.05], [tK + 2.4, 1.32, "i"], [DUR, 1.42]]);
    const eyeY = track([[0, 1.62], [tK, 1.62], [tK + 0.3, 1.55], [T_DRAG, 1.5], [tK + 2.1, 0.32, "i"], [DUR, 0.28]]);
    const back = track([[0, 0], [L.t1, -0.06, "x"], [tK, -0.08, "h"], [tK + 0.4, -0.02], [T_DRAG, 0], [tK + 2.1, -0.35, "i"], [DUR, -0.4]]);
    const fov = track([[0, R.start.fov], [tB0, R.start.fov - 2], [t0, R.start.fov - 4], [L.t1, R.start.fov + 8, "x"], [tK, R.start.fov + 2], [tK + 0.5, R.start.fov - 4], [DUR, R.start.fov + 4]]);

    const cam = (t) => {
      const s = settle(R, t, 0.9);
      const k = sstep(0.9, 1.4, t);
      const c = { x: s.x * (1 - k), y: lerp(s.y, eyeY(t), k), z: lerp(s.z, 0, k) + back(t), yaw: lerp(s.yaw, yaw(t), k), pitch: lerp(s.pitch, pitch(t), k), roll: 0, fov: fov(t), near: t >= t0 && t < tK ? 0.02 : undefined };
      // Held breath while turning; the lunge shakes the head hard; the bites jolt it.
      shake(c, t, 0.003 + 0.004 * sstep(tT0, tB0, t) + L.shake(t) + 0.018 * pulse(t, hits.map((h) => h.t), 0.2) + 0.012 * sstep(T_DRAG, T_DRAG + 0.5, t), 3);
      c.roll += 0.32 * sstep(T_DRAG, tK + 2.9, t) * -side;
      return c;
    };

    hits.forEach((h, i) => {
      const up = i < 3;
      R.burst(h.t, [0.08 * (i % 2 ? -1 : 1), up ? 1.25 : 0.2, up ? 0.42 : 0.55], 28, "blood", { dir: up ? [0, 0.6, 1.0] : [0, 1.2, 0.5], speed: 2.2, spread: 0.7, size: 0.05, life: 1.3, stick: 3 });
      R.burst(h.t + 0.02, [0, up ? 1.3 : 0.25, up ? 0.45 : 0.5], 8, "flesh", { dir: [0, 0.8, 0.8], speed: 1.6, spread: 0.6, size: 0.07, life: 1.2, stick: 3 });
    });

    const S2 = screech(L, [["mob.zombie.say", { pitch: 0.55 }], ["mob.zombie.hurt", { pitch: 0.62, volume: 1.2 }]]);
    const sounds = [
      [tG, "mob.zombie.say", { at: [gx, 1.6, gz], volume: 1, pitch: 0.82, reverb: 0.5 }],
      [tG + 0.75, "mob.zombie.step", { at: [gx, 0.2, gz], volume: 0.35 }],
      [tT1 + 0.35, "qf.scare.whisper", { volume: 0.3 }],
      ...(tFake ? [[tFake, "qf.scare.stinger", { volume: 0.95 }], [tFake + 0.02, "qf.scare.shriek", { volume: 0.35, pitch: 1.2 }]] : []),
      ...tGl.map((tt) => [tt, "random.fizz", { volume: 0.25, pitch: 1.4 }]),
      silence(tSil),
      ...(tBreath ? [[tBreath, "mob.zombie.say", { at: [lside * 0.7, 1.5, 0.05], volume: 0.22, pitch: 0.5 }]] : []),
      ...S2.sounds,
      ...hits.flatMap((h, i) => [[h.t, "game.player.hurt"], [h.t + 0.03, i % 2 ? "qf.scare.gore" : "qf.scare.crunch", { volume: 1 }]]),
      [tK + 0.55, "mob.zombie.hurt", { at: [0, 1.6, near], volume: 0.8, pitch: 0.75 }],
      ...deathScream(tK + 0.25, { volume: 1.1, under: false }),
      [tK + 0.9, "mob.zombie.say", { at: [-2, 1.6, 2], volume: 0.9, pitch: 0.9 }],
      [tK + 1.35, "mob.zombie.say", { at: [2, 1.6, -1], volume: 0.9, pitch: 1.05 }],
      [tK + 1.9, "mob.zombie.say", { at: [0, 1.6, -2], volume: 0.8, pitch: 0.95 }],
      [tK + 2.2, "qf.scare.gore", { volume: 1 }],
      ...deathScream(T_DRAG + 0.9, { volume: 1.3 }),
      [DUR - 0.4, "qf.scare.crunch", { volume: 1 }],
      [DUR, "game.player.die"],
      [DUR, "@muffle", { hz: 380, s: 3.5 }]
    ];
    const loops = [
      [0.55, tSil, "qf.scare.heartbeat", { volume: 0.6 }],
      [tT1 - 0.2, tSil, "qf.scare.breath", { volume: 0.35, fadeIn: 1.2, fadeOut: 0.1 }],
      [0.2, tB0, "qf.scare.drone", { volume: 0.45, fadeIn: 1.5, fadeOut: 0.5, bus: "sfx" }],
      ...S2.loops,
      [tK, DUR + 0.2, "qf.scare.heartbeat", { volume: 0.7, pitch: 1.35 }]
    ];

    // At the end, hands come into the lens from the edges and close over it.
    const hands = lensLimbs(R, others[0].m, "rightArm", [
      { from: [-0.42, -0.3], to: [-0.12, -0.04], t0: tK + 2.6, t1: tK + 3.15, scale: 0.5, z: -0.3, twist: 0.05 },
      { from: [0.44, -0.26], to: [0.1, -0.02], t0: tK + 2.75, t1: tK + 3.25, scale: 0.5, z: -0.31, twist: 0.06 },
      { from: [0.1, 0.36], to: [0.02, 0.08], t0: tK + 2.9, t1: tK + 3.35, scale: 0.55, z: -0.29, twist: 0.04 },
      { from: [-0.3, 0.32], to: [-0.06, 0.06], t0: tK + 3.0, t1: DUR, scale: 0.5, z: -0.28, twist: 0.05 }
    ], { color: 0x6a6a6a });
    function poseZombie(m, t, lean, armsUp = 1.55, bite = 0) {
      m.anim(t, 0, { walk: 0 });
      const P = m.parts;
      if (P.rightArm) { P.rightArm.rotation.x = armsUp + Math.sin(t * 9) * 0.06; P.leftArm.rotation.x = armsUp + Math.sin(t * 9 + 1) * 0.06; }
      if (P.head) P.head.rotation.x = 0.15 - bite * 0.3;
      if (P.headwear && P.head) P.headwear.rotation.copy(P.head.rotation);
      m.pivot.rotation.x = lean;
    }
    // Far down the corridor for one frame, while the torches flicker.
    const far = { x: R.wallR > R.wallL ? 0.4 : -0.4, z: clamp(R.ahead - 1.5, 4, 11) };

    function update(t, f) {
      const camNow = R.camera;
      const bite = pulse(t, hits.slice(0, 3).map((h) => h.t - 0.06), 0.16);
      let open = 0, lit = 0;
      if (t < t0) {
        const g = glimpse(t, tGl, 0.08);
        z1.pivot.visible = atFace ? Math.abs(yaw(t)) < 1.25 || t > tB0 : g;
        const at = g ? far : start;
        R.place(z1, at.x, 0, at.z, R.yawTo(at.x, at.z, 0, 0));
        poseZombie(z1, t, 0, 1.5);
        lit = g ? 0.4 : 0;
      } else if (t < tK) {
        // The lunge: from where it stood, into the lens.
        R.place(z1, start.x, 0, start.z, R.yawTo(start.x, start.z, 0, 0));
        poseZombie(z1, t, 0, 1.35 + 0.3 * jit(t, 9));
        if (z1.parts.head) { z1.parts.head.rotation.set(0.05 + jit(t, 21) * 0.12, jit(t, 23) * 0.15, jit(t, 25) * 0.12); z1.parts.headwear.rotation.copy(z1.parts.head.rotation); }
        L.apply(t);
        open = sstep(t0, L.t1, t) * (0.85 + 0.15 * jit(t, 31));
        lit = 1;
      } else {
        // The kill: on you, biting.
        const lunge2 = 0.08 * pulse(t, hits.slice(0, 3).map((h) => h.t - 0.08), 0.12);
        const dz = near + 0.02 - lunge2 + 0.1 * sstep(T_DRAG, T_DRAG + 0.9, t);
        z1.pivot.visible = true;
        R.place(z1, 0.02 * Math.sin(t * 3), 0, dz, Math.PI + 0.05 * Math.sin(t * 2.1));
        poseZombie(z1, t, -0.12 - lunge2 * 0.3 - 0.45 * sstep(T_DRAG, T_DRAG + 1.1, t), 1.7, bite);
        const grab = sstep(tK, tK + 0.18, t);
        if (z1.parts.rightArm) { z1.parts.rightArm.rotation.y = 0.1 + 0.38 * grab; z1.parts.leftArm.rotation.y = -0.1 - 0.38 * grab; }
        open = 0.25 + 0.75 * bite;
        lit = 0.7 * (1 - 0.6 * sstep(T_DRAG, T_DRAG + 1, t));
      }
      jaw.set(open);
      eyes(lit);
      z1.setOwn(0.1 + 0.22 * lit);
      hands(t);
      for (const q of others) {
        const k = sstep(q.t0, q.t0 + 1.2, t);
        q.m.pivot.visible = t > q.t0 - 0.1;
        const x = lerp(q.from[0], q.to[0], k), z = lerp(q.from[1], q.to[1], k);
        R.place(q.m, x, 0, z, R.yawTo(x, z, 0, 0.1));
        poseZombie(q.m, t + q.t0, q.lean * sstep(q.t0 + 0.8, q.t0 + 1.6, t), 1.5 - 0.45 * sstep(q.t0 + 0.8, q.t0 + 1.6, t), 0);
        if (k < 1) { const P = q.m.parts; if (P.rightLeg) { P.rightLeg.rotation.x = Math.sin(t * 6) * 0.5; P.leftLeg.rotation.x = -Math.sin(t * 6) * 0.5; } }
      }
      // The light on its face: off until it comes; on it hard through the lunge.
      // (a head lamp: above the eyes, so the arms reaching past the lens stay dark)
      face.position.set(0, 0.32, -0.05).applyQuaternion(camNow.quaternion).add(camNow.position); face.intensity = 0.55 * lit;
      // The corridor dims; the flicker for the glimpse; darkness gathers as they close over you.
      const fl = tGl.length ? Math.max(...tGl.map((x) => (t > x - 0.25 && t < x + 0.3 ? 0.5 + 0.5 * Math.sin((t - x) * 70) : 0))) : 0;
      const closing = sstep(tK + 1.95, DUR, t), sil = sstep(tSil, tSil + 0.6, t) * (t < t0 ? 1 : 0);
      f.env = { bake: (1 - 0.2 * sstep(0.2, 1.2, t) - 0.15 * sil - 0.25 * sstep(T_DRAG, T_DRAG + 0.9, t) - 0.3 * closing) * (1 - 0.7 * fl), lights: (1 - 0.2 * sil - 0.3 * sstep(T_DRAG, T_DRAG + 0.9, t) - 0.4 * closing) * (1 - 0.8 * fl), fogMul: 1 + 0.6 * sstep(0.5, 3.5, t) };
      f.vig = [12, 0, 0, 0.35 * sstep(1.5, tB0, t) + 0.15 * sil + 0.25 * sstep(T_DRAG, T_DRAG + 0.9, t) + 0.4 * closing]; f.vigR = 0.9;
      f.black = 0.85 * sstep(tK + 2.95, DUR, t);
      f.splats = hits.slice(0, 4).filter((h) => t >= h.t).map((h, i) => ({ t0: h.t, x: [0.3, 0.68, 0.45, 0.6][i], y: [0.4, 0.3, 0.62, 0.5][i], r: 14 + i * 3, seed: 11 + i }));
      lungeFx(L, t, f);
    }
    return { dur: DUR, hits, cam, update, sounds, loops, deathSide: -side,
      marks: { dread: tT1 + 0.4, fake: tFake != null ? tFake + 0.1 : tB1 - 0.3, lunge: L.t1 + 0.12, kill: tK + 1.0 },
      notes: { atFace, glimpseFar, turn: +turn.toFixed(2), t0: +t0.toFixed(2), tK: +tK.toFixed(2), dur: +DUR.toFixed(2) } };
  }
};
