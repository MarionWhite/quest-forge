// Zombie: the look-back. A groan from the side passage (or behind); the head turns to it, slowly, and it is empty.
// Breathing, close, from where you were facing. Turning back, the zombie is at your face. It grabs, it bites, and
// more arms come out of the dark and drag you down until the view is the ceiling and hands cover it.
import { THREE, track, clamp, lerp, sstep, pulse, wobble } from "./rig.js";
import { settle, shake, hitsOf, lensLimbs } from "./common.js";

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
    // The zombie: right in front of the face when the head comes back.
    const near = clamp(R.ahead - 0.6, 0.55, 0.82);
    const z1 = R.mob("Zombie", { amb: [0.26, 0.25, 0.25] });
    // Two more, out of the dark on either side, and one from behind.
    const wl = Math.min(R.wallL, 3.2), wr = Math.min(R.wallR, 3.2);
    const others = [
      { m: R.mob("Zombie", { amb: [0.2, 0.2, 0.2] }), from: [-wl + 0.4, 3.2], to: [-1.15, -0.25], t0: 5.0, lean: -0.47 },
      { m: R.mob("Zombie", { amb: [0.2, 0.2, 0.2] }), from: [wr - 0.4, 2.6], to: [1.1, -0.55], t0: 5.25, lean: -0.47 },
      { m: R.mob("Zombie", { amb: [0.2, 0.2, 0.2] }), from: [0.3, -Math.min(R.behind - 0.5, 4)], to: [0.1, -1.6], t0: 5.5, lean: -0.5 }
    ];
    const face = R.light(0xffb070, 0, 2.2, 1.4); R.ownLight(face);   // a cold sliver of light from the corridor on its face

    const hits = hitsOf([[4.32, 5, 1], [4.86, 5, -1], [5.42, 3, 1], [6.5, 4, -1], [7.15, 3, 1]]);
    const T_BACK = 3.85, T_HIT = 4.12, T_DRAG = 5.45, DUR = 7.75;
    const yaw = track([[0, 0], [1.45, 0], [2.95, turn], [T_BACK, turn, "h"], [T_BACK + 0.001, turn], [T_HIT, 0.04 * side, "x"], [T_DRAG, 0.0], [7.0, -0.25 * side]]);
    const pitch = track([[0, 0], [1.45, -0.03], [2.95, -0.08], [T_BACK, -0.06], [T_HIT, 0.06, "x"], [4.5, 0.12], [T_DRAG, 0.05], [6.6, 1.32, "i"], [DUR, 1.42]]);
    const eyeY = track([[0, 1.62], [T_HIT, 1.62], [4.4, 1.55], [T_DRAG, 1.5], [6.3, 0.32, "i"], [DUR, 0.28]]);
    const back = track([[0, 0], [T_HIT, -0.08, "x"], [4.5, -0.02], [T_DRAG, 0], [6.3, -0.35, "i"], [DUR, -0.4]]);
    const fov = track([[0, R.start.fov], [T_BACK, R.start.fov - 2], [T_HIT, R.start.fov + 6, "x"], [4.6, R.start.fov - 4], [DUR, R.start.fov + 4]]);

    const cam = (t) => {
      const s = settle(R, t, 0.9);
      const k = sstep(0.9, 1.4, t);
      const c = { x: s.x * (1 - k), y: lerp(s.y, eyeY(t), k), z: lerp(s.z, 0, k) + back(t), yaw: lerp(s.yaw, yaw(t), k), pitch: lerp(s.pitch, pitch(t), k), roll: 0, fov: fov(t) };
      // Held breath while turning: a small tremble; the grab shakes the head hard.
      shake(c, t, 0.003 + 0.004 * sstep(1.5, 3.8, t) + 0.03 * sstep(T_HIT, T_HIT + 0.05, t) * (1 - sstep(4.4, 4.9, t)) + 0.018 * pulse(t, hits.map((h) => h.t), 0.2) + 0.012 * sstep(T_DRAG, 6.0, t), 3);
      c.roll += 0.32 * sstep(T_DRAG, 7.2, t) * -side;
      return c;
    };

    // Gore: chunks from the neck at every bite; on the floor, from the arms tearing.
    hits.forEach((h, i) => {
      const up = i < 3;
      R.burst(h.t, [0.08 * (i % 2 ? -1 : 1), up ? 1.25 : 0.2, up ? 0.42 : 0.55], 28, "blood", { dir: up ? [0, 0.6, 1.0] : [0, 1.2, 0.5], speed: 2.2, spread: 0.7, size: 0.05, life: 1.3, stick: 3 });
      R.burst(h.t + 0.02, [0, up ? 1.3 : 0.25, up ? 0.45 : 0.5], 8, "flesh", { dir: [0, 0.8, 0.8], speed: 1.6, spread: 0.6, size: 0.07, life: 1.2, stick: 3 });
    });

    const sounds = [
      [1.18, "mob.zombie.say", { at: [gx, 1.6, gz], volume: 1, pitch: 0.82 }],
      [1.9, "mob.zombie.step", { at: [gx, 0.2, gz], volume: 0.35 }],
      [3.25, "qf.scare.whisper", { volume: 0.35 }],
      [T_HIT - 0.05, "qf.scare.stinger", { volume: 1 }],
      [T_HIT - 0.02, "mob.zombie.say", { at: [0, 1.6, near], volume: 1, pitch: 0.7 }],
      [T_HIT, "qf.scare.shriek", { volume: 0.55 }],
      [T_HIT + 0.02, "qf.scare.hit", { volume: 0.9 }],
      ...hits.flatMap((h, i) => [[h.t, "game.player.hurt"], [h.t + 0.03, i % 2 ? "qf.scare.gore" : "qf.scare.crunch", { volume: 0.9 }]]),
      [4.9, "mob.zombie.hurt", { at: [0, 1.6, near], volume: 0.8, pitch: 0.75 }],
      [5.15, "mob.zombie.say", { at: [-2, 1.6, 2], volume: 0.9, pitch: 0.9 }],
      [5.5, "qf.scare.scream", { volume: 0.95 }],
      [5.6, "mob.zombie.say", { at: [2, 1.6, -1], volume: 0.9, pitch: 1.05 }],
      [6.2, "mob.zombie.say", { at: [0, 1.6, -2], volume: 0.8, pitch: 0.95 }],
      [6.55, "qf.scare.gore", { volume: 1 }],
      [7.1, "qf.scare.crunch", { volume: 1 }],
      [DUR, "game.player.die"],
      [DUR, "@muffle", { hz: 380, s: 3.5 }]
    ];
    const loops = [
      [0.55, DUR + 0.2, "qf.scare.heartbeat", { volume: 0.55 }],
      [2.9, T_HIT, "qf.scare.breath", { at: [0, 1.6, near], volume: 0.45, fadeIn: 0.8, fadeOut: 0.05 }],
      [0.2, 3.2, "qf.scare.drone", { volume: 0.4, fadeIn: 1.5, fadeOut: 0.6 }]
    ];

    // At the end, hands come into the lens from the edges and close over it.
    const hands = lensLimbs(R, others[0].m, "rightArm", [
      { from: [-0.42, -0.3], to: [-0.12, -0.04], t0: 6.75, t1: 7.5, scale: 0.5, z: -0.3, twist: 0.05 },
      { from: [0.44, -0.26], to: [0.1, -0.02], t0: 6.95, t1: 7.6, scale: 0.5, z: -0.31, twist: 0.06 },
      { from: [0.1, 0.36], to: [0.02, 0.08], t0: 7.15, t1: 7.7, scale: 0.55, z: -0.29, twist: 0.04 },
      { from: [-0.3, 0.32], to: [-0.06, 0.06], t0: 7.25, t1: 7.75, scale: 0.5, z: -0.28, twist: 0.05 }
    ], { color: 0x6a6a6a });
    function poseZombie(m, t, lean, armsUp = 1.55, bite = 0) {
      m.anim(t, 0, { walk: 0 });
      const P = m.parts;
      if (P.rightArm) { P.rightArm.rotation.x = armsUp + Math.sin(t * 9) * 0.06; P.leftArm.rotation.x = armsUp + Math.sin(t * 9 + 1) * 0.06; }   // three's +x = MC's -x: arms out
      if (P.head) P.head.rotation.x = 0.15 - bite * 0.45;
      m.pivot.rotation.x = lean;
    }

    function update(t, f) {
      // The first zombie stands behind the turned head the whole time (hidden from the camera by the turn).
      z1.pivot.visible = t >= T_BACK || Math.abs(yaw(t)) > 1.3;
      const lunge = sstep(T_HIT, T_HIT + 0.12, t) * 0.1 + 0.08 * pulse(t, hits.slice(0, 3).map((h) => h.t - 0.08), 0.12);
      const dz = near + 0.12 - lunge + 0.1 * sstep(T_DRAG, 6.4, t);
      R.place(z1, 0.02 * Math.sin(t * 3), 0, dz, Math.PI + 0.05 * Math.sin(t * 2.1));
      const bite = pulse(t, hits.slice(0, 3).map((h) => h.t - 0.06), 0.16);
      const lean = -0.04 - lunge * 0.3 - 0.45 * sstep(T_DRAG, 6.6, t);
      poseZombie(z1, t, lean, 1.45 + 0.25 * sstep(T_HIT, T_HIT + 0.1, t), bite);
      // Arms come in to the sides of the face: the grab.
      const grab = sstep(T_HIT, T_HIT + 0.18, t);
      if (z1.parts.rightArm) { z1.parts.rightArm.rotation.y = 0.1 + 0.38 * grab; z1.parts.leftArm.rotation.y = -0.1 - 0.38 * grab; z1.parts.rightArm.rotation.z = 0.05; z1.parts.leftArm.rotation.z = -0.05; }
      hands(t);
      // The others shamble in and lean over.
      for (const q of others) {
        const k = sstep(q.t0, q.t0 + 1.2, t);
        q.m.pivot.visible = t > q.t0 - 0.1;
        const x = lerp(q.from[0], q.to[0], k), z = lerp(q.from[1], q.to[1], k);
        R.place(q.m, x, 0, z, R.yawTo(x, z, 0, 0.1));
        poseZombie(q.m, t + q.t0, q.lean * sstep(q.t0 + 0.8, q.t0 + 1.6, t), 1.5 - 0.45 * sstep(q.t0 + 0.8, q.t0 + 1.6, t), 0);
        if (k < 1) { const P = q.m.parts; if (P.rightLeg) { P.rightLeg.rotation.x = Math.sin(t * 6) * 0.5; P.leftLeg.rotation.x = -Math.sin(t * 6) * 0.5; } }
      }
      R.L(-0.7 * side, 1.05, dz - 0.55, face.position); face.intensity = 0.9 * sstep(T_BACK - 0.3, T_HIT, t) * (1 - 0.6 * sstep(T_DRAG, 6.5, t));
      // Darkness gathers as they close over you.
      const closing = sstep(6.2, DUR, t);
      f.env = { bake: 1 - 0.2 * sstep(0.2, 1.2, t) - 0.25 * sstep(T_DRAG, 6.4, t) - 0.3 * closing, lights: 1 - 0.3 * sstep(T_DRAG, 6.4, t) - 0.4 * closing, fogMul: 1 + 0.6 * sstep(0.5, 3.5, t) };
      f.vig = [12, 0, 0, 0.35 * sstep(1.5, 3.8, t) + 0.25 * sstep(T_DRAG, 6.4, t) + 0.4 * closing]; f.vigR = 0.9;
      f.black = 0.85 * sstep(7.2, DUR, t);
      f.splats = hits.slice(0, 4).filter((h) => t >= h.t).map((h, i) => ({ t0: h.t, x: [0.3, 0.68, 0.45, 0.6][i], y: [0.4, 0.3, 0.62, 0.5][i], r: 14 + i * 3, seed: 11 + i }));
    }
    return { dur: DUR, hits, cam, update, sounds, loops, deathSide: -side, notes: { turn: +turn.toFixed(2), passage: !!p, opening: !!o, near } };
  }
};
