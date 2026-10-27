// Zombie (round 7: the shamble). A groan from the side passage (or behind); the head turns to it, slowly: empty dark.
// It comes back round, and then one of two things, a coin toss each play:
//   - it is there, at arm's length, arms out: it walked up while you were looking away (the one device). It groans in
//     your face, its hands close on your shoulders, and it pulls you in to bite;
//   - nothing is there either. Silence, then one dragging step from the passage. The head goes back to it: it comes
//     out of the dark into the torchlight, arms out, at a zombie's walk, and keeps coming. You back away from it, and
//     back into another one: a groan at your ear, hands over your shoulders from behind. Held, and the first one
//     reaches you.
// Then the kill: it bites, more of them come out of the dark and drag you down until hands cover the view.
import { track, clamp, lerp, sstep, pulse } from "./rig.js";
import { settle, shake, hitsOf, lensLimbs } from "./common.js";
import { splitJaw, boxOf, silence, deathScream } from "./fnaf.js";
import { roar } from "./story.js";

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
    const fwd = (y, d) => ({ x: -Math.sin(y) * d, z: Math.cos(y) * d });
    const inX = (x) => clamp(x, -(R.wallL - 0.35), R.wallR - 0.35);

    // ---- the dice -------------------------------------------------------------------------------------
    const atFace = R.chance(0.45);            // it is there when the head comes back
    const tG = 0.9 + R.vary(0.7, 0.5);       // the groan
    const tT0 = tG + R.vary(0.35, 0.4), tT1 = tT0 + R.vary(1.35, 0.25);   // the turn to it
    const tB0 = tT1 + R.vary(0.95, 0.4), tB1 = tB0 + R.vary(0.8, 0.2);    // the look back
    const yK = atFace ? 0 : turn;             // the way the bite comes from
    const bx = Math.sin(yK), bz = -Math.cos(yK);   // backing away from it
    const retreat = atFace ? 0 : clamp(R.ray(0, 1.5, 0, bx, 0, bz, 4) - 0.8, 0, 0.75);
    const near = 1.0;    // (b) where it stops in front of you (its face is a quarter metre ahead of that)
    let tSil, tStep = null, tR0 = null, tR1 = null, tHeld = null, tGrab, tK, A = null, B = null;
    if (atFace) {
      tSil = tB0 - 0.05;
      tGrab = tB1 + R.vary(0.4, 0.25);       // a beat looking at it; then its hands
      tK = tGrab + 0.32;                     // pulled in: the bite
    } else {
      tSil = tB1 + 0.1;
      tStep = tB1 + R.vary(0.8, 0.35);       // one dragging step, out there
      tR0 = tStep + 0.25; tR1 = tR0 + 0.5;   // the head goes back to it
      const end = fwd(yK, near); end.x += bx * retreat; end.z += bz * retreat;
      const d0 = Math.hypot(gx - end.x, gz - end.z) || 1, run = Math.min(d0, 4.2);
      B = end; A = { x: end.x + (gx - end.x) / d0 * run, z: end.z + (gz - end.z) / d0 * run };
      tK = tR0 + 0.1 + run / 1.9;            // a zombie's walk
      tHeld = tK - R.vary(0.8, 0.25);        // you back into the other one
      tGrab = tK - 0.3;
    }
    const T_DRAG = tK + 1.25, DUR = tK + 3.4;
    const base = (t) => (atFace ? { x: 0, z: 0 } : { x: bx * retreat * sstep(tR1 - 0.2, tHeld, t), z: bz * retreat * sstep(tR1 - 0.2, tHeld, t) });
    const baseK = base(DUR);
    // The attack's frame: forward toward the one that bites, x to its right.
    const fK = { x: -Math.sin(yK), z: Math.cos(yK) }, rK = { x: Math.cos(yK), z: Math.sin(yK) };
    const inK = (x, z) => ({ x: inX(baseK.x + rK.x * x + fK.x * z), z: baseK.z + rK.z * x + fK.z * z });

    const z1 = R.mob("Zombie", { amb: [0.26, 0.25, 0.25], own: true });
    const jaw = splitJaw(z1, [{ part: z1.parts.head, box: boxOf("zombie", "bipedHead"), rows: 2 }, { part: z1.parts.headwear, box: boxOf("zombie", "bipedHeadwear"), rows: 2 }]);
    z1.anim(0, 0, { walk: 0 }); R.place(z1, 0, 0, 2, Math.PI);
    const start = { x: 0.05, z: clamp(R.ahead - 0.45, 0.8, 1.1) };   // (a) where it stands when you look back: arm's length

    // More, out of the dark on either side, and one from behind (in the frame of the attack).
    const wl = Math.min(R.wallL, 3.2), wr = Math.min(R.wallR, 3.2);
    const others = [
      { m: R.mob("Zombie", { amb: [0.2, 0.2, 0.2] }), from: inK(-wl + 0.4, 3.2), to: inK(-1.15, -0.25), t0: tK + 0.85, lean: -0.47 },
      { m: R.mob("Zombie", { amb: [0.2, 0.2, 0.2] }), from: inK(wr - 0.4, 2.6), to: inK(1.1, -0.55), t0: tK + 1.1, lean: -0.47 },
      atFace ? { m: R.mob("Zombie", { amb: [0.2, 0.2, 0.2] }), from: inK(0.3, -Math.min(R.behind - 0.5, 4)), to: inK(0.1, -1.6), t0: tK + 1.35, lean: -0.5 }
        : { m: R.mob("Zombie", { amb: [0.2, 0.2, 0.2] }), from: inK(0.25, -2.6), to: inK(0.08, -0.62), t0: tHeld - 1.6, lean: -0.5, holds: true }
    ];
    const face = R.ownLight(R.light(0xffb070, 0, 2.4, 1.4));   // a sliver of corridor light on its face

    const hits = hitsOf([[tK + 0.02, 5, 1], [tK + 0.6, 5, -1], [tK + 1.15, 3, 1], [tK + 2.3, 4, -1], [tK + 2.95, 3, 1]]);
    // The head: the slow turn to the groan, the slow turn back; then (a) on it, pulled in; (b) back to the passage and on
    // it as it comes, a jerk toward the groan at your ear; then the kill, dragged down.
    const yawKeys = [[0, 0], [tT0, 0], [tT1, turn], [tB0, turn, "h"], [tB1, 0.0]];
    if (!atFace) yawKeys.push([tR0, 0.0, "h"], [tR1, yK, "o"], [tHeld, yK, "h"], [tHeld + 0.12, yK - 0.3 * side, "x"], [tHeld + 0.5, yK]);
    yawKeys.push([tK, yK + 0.04 * side], [T_DRAG, yK], [tK + 2.9, yK - 0.25 * side]);
    const yaw = track(yawKeys);
    const pitchKeys = [[0, 0], [tT0, -0.03], [tT1, -0.08], [tB1, -0.04]];
    if (atFace) pitchKeys.push([tB1 + 0.15, 0.08, "o"], [tGrab, 0.1, "h"]);
    else pitchKeys.push([tR1, 0.0], [tK - 0.3, 0.06]);
    pitchKeys.push([tK, 0.06], [tK + 0.4, 0.12], [T_DRAG, 0.05], [tK + 2.4, 1.32, "i"], [DUR, 1.42]);
    const pitch = track(pitchKeys);
    const eyeY = track([[0, 1.62], [tK, 1.62], [tK + 0.3, 1.55], [T_DRAG, 1.5], [tK + 2.1, 0.32, "i"], [DUR, 0.28]]);
    // Along the attack: pulled in to it, a little back with each bite, then down and back under them.
    const pull = track([[0, 0], [tGrab, 0], [tK, atFace ? 0.14 : 0.08, "i"], [tK + 0.4, atFace ? 0.1 : 0.04], [T_DRAG, 0.1], [tK + 2.1, -0.25, "i"], [DUR, -0.3]]);
    const fov = track([[0, R.start.fov], [tB0, R.start.fov - 2], [atFace ? tB1 : tR1, R.start.fov - 4], [tK, R.start.fov + 3, "x"], [tK + 0.5, R.start.fov - 4], [DUR, R.start.fov + 4]]);

    const cam = (t) => {
      const s = settle(R, t, 0.9);
      const k = sstep(0.9, 1.4, t), b = base(t), pl = pull(t);
      const c = { x: lerp(s.x, b.x + fK.x * pl, k), y: lerp(s.y, eyeY(t), k), z: lerp(s.z, b.z + fK.z * pl, k), yaw: lerp(s.yaw, yaw(t), k), pitch: lerp(s.pitch, pitch(t), k), roll: 0, fov: fov(t), near: t >= tGrab - 0.5 ? 0.02 : undefined };
      // backing away: an unsteady step each half second
      if (!atFace && t > tR1 - 0.2 && t < tHeld) c.y -= 0.03 * Math.abs(Math.sin((t - tR1) * 6.5));
      // Held breath while turning; the grab and the bites jolt the head; dragged down, it shakes.
      shake(c, t, 0.003 + 0.004 * sstep(tT0, tB0, t) + 0.02 * pulse(t, [tGrab, ...(tHeld ? [tHeld] : []), ...hits.map((h) => h.t)], 0.2) + 0.012 * sstep(T_DRAG, T_DRAG + 0.5, t), 3);
      c.roll += 0.32 * sstep(T_DRAG, tK + 2.9, t) * -side;
      return c;
    };

    hits.forEach((h, i) => {
      const up = i < 3, at = (x, y, z) => { const q = inK(x, z); return [q.x, y, q.z]; };
      R.burst(h.t, at(0.08 * (i % 2 ? -1 : 1), up ? 1.25 : 0.2, up ? 0.42 : 0.55), 28, "blood", { dir: up ? [fK.x, 0.6, fK.z] : [fK.x * 0.5, 1.2, fK.z * 0.5], speed: 2.2, spread: 0.7, size: 0.05, life: 1.3, stick: 3 });
      R.burst(h.t + 0.02, at(0, up ? 1.3 : 0.25, up ? 0.45 : 0.5), 8, "flesh", { dir: [fK.x * 0.8, 0.8, fK.z * 0.8], speed: 1.6, spread: 0.6, size: 0.07, life: 1.2, stick: 3 });
    });

    // ---- the sound ----------------------------------------------------------------------------------------
    const posZ = (t) => {   // (b) where it is as it comes
      const k = clamp((t - tR0 - 0.1) / Math.max(0.1, tK - tR0 - 0.1));
      return { x: lerp(A.x, B.x, k), z: lerp(A.z, B.z, k) };
    };
    const walkSteps = [];
    if (!atFace) for (let s = tR0 + 0.2; s < tK - 0.1; s += 0.5) { const q = posZ(s); walkSteps.push([s, "mob.zombie.step", { at: [q.x, 0.1, q.z], volume: 0.55 }]); }
    const ear = inK(0.25, -0.35);
    const sounds = [
      [tG, "mob.zombie.say", { at: [gx, 1.6, gz], volume: 1, pitch: 0.82, reverb: 0.5 }],
      [tG + 0.75, "mob.zombie.step", { at: [gx, 0.2, gz], volume: 0.35 }],
      [tT1 + 0.35, "qf.scare.whisper", { volume: 0.25 }],
      silence(tSil),
      ...(atFace ? [
        // There: it groans in your face; its hands close on you.
        ...roar(tB1 - 0.08, [["mob.zombie.say", { at: [start.x, 1.7, start.z], pitch: 0.62 }], ["mob.zombie.hurt", { at: [start.x, 1.7, start.z], pitch: 0.6, volume: 0.9 }]], { hit: 0.6 }),
        [tGrab, "dig.cloth", { volume: 0.8, pitch: 0.7 }], [tGrab + 0.02, "mob.zombie.say", { at: [start.x, 1.7, start.z], volume: 1.1, pitch: 0.5 }]
      ] : [
        [tStep, "mob.zombie.step", { at: [gx, 0.2, gz], volume: 0.5, pitch: 0.8 }],
        [tStep + 0.4, "mob.zombie.say", { at: [A.x, 1.6, A.z], volume: 0.9, pitch: 0.7, reverb: 0.4 }],
        ...walkSteps,
        [(tR1 + tHeld) / 2, "mob.zombie.say", { at: [posZ((tR1 + tHeld) / 2).x, 1.6, posZ((tR1 + tHeld) / 2).z], volume: 1, pitch: 0.8 }],
        // backed into the other one
        ...roar(tHeld, [["mob.zombie.say", { at: [ear.x, 1.6, ear.z], pitch: 0.55 }]], { hit: 0.7 }), [tHeld + 0.02, "dig.cloth", { volume: 0.9, pitch: 0.6 }],
        [tGrab, "mob.zombie.hurt", { at: [B.x, 1.7, B.z], volume: 1.1, pitch: 0.62 }]
      ]),
      ...hits.flatMap((h, i) => [[h.t, "game.player.hurt"], [h.t + 0.01, "qf.scare.hit", { volume: i ? 0.6 : 0.9 }], [h.t + 0.03, i % 2 ? "qf.scare.gore" : "qf.scare.crunch", { volume: 1 }]]),
      [tK + 0.55, "mob.zombie.hurt", { volume: 0.8, pitch: 0.75 }],
      ...deathScream(tK + 0.25, { volume: 1.1, under: false }),
      [tK + 0.9, "mob.zombie.say", { at: [others[0].from.x, 1.6, others[0].from.z], volume: 0.9, pitch: 0.9 }],
      [tK + 1.35, "mob.zombie.say", { at: [others[1].from.x, 1.6, others[1].from.z], volume: 0.9, pitch: 1.05 }],
      [tK + 1.9, "mob.zombie.say", { at: [others[2].to.x, 1.6, others[2].to.z], volume: 0.8, pitch: 0.95 }],
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
      ...(atFace ? [] : [[tR1, tK, "qf.scare.heartbeat", { volume: 0.65, pitch: 1.25, fadeIn: 0.2 }], [tR1, tK, "qf.scare.breath", { volume: 0.4, pitch: 1.2, fadeIn: 0.4 }]]),
      [tK, DUR + 0.2, "qf.scare.heartbeat", { volume: 0.7, pitch: 1.35 }]
    ];

    // At the end, hands come into the lens from the edges and close over it; (b) the one behind holds you first.
    const hands = lensLimbs(R, others[0].m, "rightArm", [
      { from: [-0.42, -0.3], to: [-0.12, -0.04], t0: tK + 2.6, t1: tK + 3.15, scale: 0.5, z: -0.3, twist: 0.05 },
      { from: [0.44, -0.26], to: [0.1, -0.02], t0: tK + 2.75, t1: tK + 3.25, scale: 0.5, z: -0.31, twist: 0.06 },
      { from: [0.1, 0.36], to: [0.02, 0.08], t0: tK + 2.9, t1: tK + 3.35, scale: 0.55, z: -0.29, twist: 0.04 },
      { from: [-0.3, 0.32], to: [-0.06, 0.06], t0: tK + 3.0, t1: DUR, scale: 0.5, z: -0.28, twist: 0.05 },
      ...(atFace ? [] : [
        { from: [-0.66, -0.52], to: [-0.38, -0.27], t0: tHeld, t1: tHeld + 0.14, scale: 0.5, z: -0.3, twist: 0.03, t2: T_DRAG + 0.4 },
        { from: [0.68, -0.5], to: [0.38, -0.28], t0: tHeld + 0.05, t1: tHeld + 0.19, scale: 0.5, z: -0.31, twist: 0.03, t2: T_DRAG + 0.45 }
      ])
    ], { color: 0x6a6a6a });
    function poseZombie(m, t, lean, armsUp = 1.55, bite = 0) {
      m.anim(t, 0, { walk: 0 });
      const P = m.parts;
      if (P.rightArm) { P.rightArm.rotation.x = armsUp + Math.sin(t * 9) * 0.06; P.leftArm.rotation.x = armsUp + Math.sin(t * 9 + 1) * 0.06; }
      if (P.head) P.head.rotation.x = 0.15 - bite * 0.3;
      if (P.headwear && P.head) P.headwear.rotation.copy(P.head.rotation);
      m.pivot.rotation.x = lean;
    }
    const legs = (m, t, on) => { const P = m.parts; if (P.rightLeg) { const a = on ? Math.sin(t * 6) * 0.5 : 0; P.rightLeg.rotation.x = a; P.leftLeg.rotation.x = -a; } };

    function update(t, f) {
      const camNow = R.camera, cl = R.toLocal(camNow.position);
      const bite = pulse(t, hits.slice(0, 3).map((h) => h.t - 0.06), 0.16);
      const grab = sstep(tGrab, tGrab + 0.18, t);
      let open = 0, lit = 0;
      if (t < tK) {
        if (atFace) {
          // There when you look back, arms out; it leans into you as it pulls you in.
          z1.pivot.visible = Math.abs(yaw(t)) < 1.25 || t > tB0;
          R.place(z1, start.x, 0, start.z, R.yawTo(start.x, start.z, cl.x, cl.z));
          poseZombie(z1, t, -0.05 * grab, 1.5 + 0.15 * grab);
          open = 0.15 * sstep(tB1 - 0.1, tB1 + 0.1, t) + 0.5 * grab;
          lit = sstep(tB1 - 0.3, tB1, t);
        } else {
          // Out of the dark and on, at a walk.
          const q = posZ(t);
          z1.pivot.visible = t > tR0;
          R.place(z1, q.x, 0, q.z, R.yawTo(q.x, q.z, cl.x, cl.z));
          poseZombie(z1, t, -0.05 * grab, 1.55 + 0.1 * grab);
          legs(z1, t, t < tK - 0.05);
          open = 0.12 + 0.45 * grab;
          lit = sstep(tR0, tR1 + 0.6, t);
        }
        if (z1.parts.rightArm && grab > 0) { z1.parts.rightArm.rotation.y = 0.1 + 0.38 * grab; z1.parts.leftArm.rotation.y = -0.1 - 0.38 * grab; }
      } else {
        // The kill: on you, biting.
        const lunge2 = 0.08 * pulse(t, hits.slice(0, 3).map((h) => h.t - 0.08), 0.12);
        const dz = -lunge2 * 1.5 + 0.1 * sstep(T_DRAG, T_DRAG + 0.9, t), w = 0.02 * Math.sin(t * 3), Z = atFace ? start : B;
        z1.pivot.visible = true;
        R.place(z1, Z.x + rK.x * w + fK.x * dz, 0, Z.z + rK.z * w + fK.z * dz, R.yawTo(Z.x, Z.z, cl.x, cl.z) + 0.05 * Math.sin(t * 2.1));
        poseZombie(z1, t, -0.05 - lunge2 * 0.5 - 0.45 * sstep(T_DRAG, T_DRAG + 1.1, t), 1.7, bite);
        if (z1.parts.rightArm) { z1.parts.rightArm.rotation.y = 0.48; z1.parts.leftArm.rotation.y = -0.48; }
        open = 0.25 + 0.75 * bite;
        lit = 0.7 * (1 - 0.6 * sstep(T_DRAG, T_DRAG + 1, t));
      }
      jaw.set(open);
      z1.setOwn(0.08 + 0.14 * lit);
      hands(t);
      for (const q of others) {
        const k = sstep(q.t0, q.t0 + 1.2, t);
        q.m.pivot.visible = t > q.t0 - 0.1;
        const x = lerp(q.from.x, q.to.x, k), z = lerp(q.from.z, q.to.z, k);
        R.place(q.m, x, 0, z, R.yawTo(x, z, cl.x, cl.z));
        poseZombie(q.m, t + q.t0, q.lean * sstep(q.t0 + 0.8, q.t0 + 1.6, t) * (q.holds && t < T_DRAG ? 0.4 : 1), 1.5 - 0.45 * sstep(q.t0 + 0.8, q.t0 + 1.6, t), 0);
        legs(q.m, t, k < 1);
      }
      // The light on its face: a sliver from the corridor as it comes into it.
      // (a head lamp: above the eyes, so the arms reaching past the lens stay dark)
      face.position.set(0, 0.32, -0.05).applyQuaternion(camNow.quaternion).add(camNow.position); face.intensity = 0.45 * lit * clamp(z1.pivot.position.distanceTo(camNow.position) / 0.9, 0.25, 1);
      // The corridor dims; darkness gathers as they close over you.
      const closing = sstep(tK + 1.95, DUR, t), sil = sstep(tSil, tSil + 0.6, t) * (t < tK ? 1 : 0);
      f.env = { bake: 1 - 0.2 * sstep(0.2, 1.2, t) - 0.15 * sil - 0.25 * sstep(T_DRAG, T_DRAG + 0.9, t) - 0.3 * closing, lights: 1 - 0.2 * sil - 0.3 * sstep(T_DRAG, T_DRAG + 0.9, t) - 0.4 * closing, fogMul: 1 + 0.6 * sstep(0.5, 3.5, t) };
      f.vig = [12, 0, 0, 0.35 * sstep(1.5, tB0, t) + 0.15 * sil + 0.25 * sstep(T_DRAG, T_DRAG + 0.9, t) + 0.4 * closing]; f.vigR = 0.9;
      f.black = 0.85 * sstep(tK + 2.95, DUR, t);
      f.splats = hits.slice(0, 4).filter((h) => t >= h.t).map((h, i) => ({ t0: h.t, x: [0.3, 0.68, 0.45, 0.6][i], y: [0.4, 0.3, 0.62, 0.5][i], r: 14 + i * 3, seed: 11 + i }));
    }
    return { dur: DUR, hits, cam, update, sounds, loops, deathSide: -side,
      marks: { dread: tT1 + 0.4, fake: atFace ? tB1 - 0.25 : tR1 + 0.6, lunge: atFace ? tGrab + 0.12 : tHeld + 0.15, kill: tK + 1.0 },
      notes: { atFace, turn: +turn.toFixed(2), retreat: +retreat.toFixed(2), tK: +tK.toFixed(2), dur: +DUR.toFixed(2) } };
  }
};
