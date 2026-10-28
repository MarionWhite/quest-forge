// Zombie (round 8: the door). In 1.7.10 a zombie breaks wooden doors (EntityAIBreakDoor: it beats on the door,
// mob.zombie.wood, the crack grows over the block, and the door goes with mob.zombie.woodbreak and a burst of its
// bits). Here a wooden door is set in the crypt wall beside and behind you, where you could not see it when you
// stopped, with a dark passage behind it.
// BANG. You flinch and turn to it: a door. It judders on its hinges with every blow, grit sifts from the lintel, the
// crack spreads over it, a groan comes through it. You back away from it, step by step, until there is no more room (or
// you are far enough to watch it); the blows come faster. It breaks: the zombie lurches straight out through the bits
// of the door, arms out, and comes at you at a zombie's pace. Its hands on your shoulders, it pulls you in and bites
// into your neck; you are dragged down, it bites again, and two more come out of the dark passage after it and close
// over you until their hands cover the view.
// (If no wall spot fits a door, it comes out of the dark of the corridor behind you: the groan, the turn, the walk.)
import { THREE, track, clamp, lerp, sstep, pulse } from "./rig.js";
import { settle, shake, hitsOf, lensLimbs, zombieArms } from "./common.js";
import { splitJaw, boxOf, silence, deathScream } from "./fnaf.js";
import { roar, blow, kick } from "./story.js";
import { wallDoor } from "./door.js";

export default {
  death: "Steve was slain by Zombie",
  async build(R) {
    const eye = R.eye;
    // ---- the door: beside and behind you, out of frame at the freeze ---------------------------------------------
    let D = await wallDoor(R, { zMin: -1.5, zMax: -0.3, avoidTorch: 0.55 });
    if (!D) D = await wallDoor(R, { zMin: -2.6, zMax: 0.4, avoidTorch: 0.55 });
    const hasDoor = !!D;
    // without a door: the dark of the corridor behind you
    const G = hasDoor ? { x: D.face, z: D.z } : { x: -0.6, z: -Math.min(7, R.behind - 1) };
    const side = hasDoor ? D.side : -1;
    let turn = R.yawTo(0, 0, G.x, G.z * (hasDoor ? 1 : 0.4));
    turn = clamp(turn, -2.6, 2.6);
    const inX = (x) => clamp(x, -(R.wallL - 0.35), R.wallR - 0.35);

    // ---- the dice -----------------------------------------------------------------------------------------------
    const b1 = 1.05 + R.vary(0.35, 0.4);
    const bangs = [b1, b1 + R.vary(1.15, 0.12)];
    for (const gap of [0.85, 0.68, 0.52, 0.42]) bangs.push(bangs[bangs.length - 1] + R.vary(gap, 0.15));
    if (!hasDoor) bangs.length = 1;   // (no door: the one groan out of the dark)
    const tBreak = hasDoor ? bangs[bangs.length - 1] + R.vary(0.38, 0.2) : b1 + 3.0;
    const tT0 = b1 + 0.1, tT1 = tT0 + 0.5;                          // the startled turn to the door
    // Backing away from it: away from the door, as far as the corridor lets you (at most 1.5 m).
    const ax = -G.x, az = -G.z * 0.35, an = Math.hypot(ax, az) || 1;
    const bx = ax / an, bz = az / an;
    const room = R.ray(0, 1.0, 0, bx, 0, bz, 4);
    // (near the door you back off further; far from it, a step or two)
    const dd = Math.hypot(G.x, G.z), want = clamp(4.3 - dd, 0.45, 1.5);
    const back = clamp(Math.min(room - 0.55, want), 0, 1.5), pinned = room - 0.55 < want;
    const tBk0 = (bangs[1] ?? b1 + 1.2) + 0.3, tBk1 = Math.min(tBreak - 0.1, tBk0 + 0.55 * Math.max(1, Math.ceil(back / 0.45)));
    const P1 = { x: bx * back, z: bz * back };                      // where you end up
    // The zombie's way: out of the passage, through the doorway, at you (or out of the dark behind).
    const A0 = hasDoor ? D.in(1.9) : { x: G.x, z: G.z }, A1 = hasDoor ? D.in(-0.35) : { x: G.x * 0.6, z: G.z + 0.8 };
    const toP = { x: P1.x - A1.x, z: P1.z - A1.z }, dP = Math.hypot(toP.x, toP.z) || 1;
    const reach = 0.85;
    const A2 = { x: P1.x - toP.x / dP * reach, z: P1.z - toP.z / dP * reach };
    const L1 = Math.hypot(A1.x - A0.x, A1.z - A0.z), L2 = Math.max(0, dP - reach), SPD = 2.8;
    const tOut = tBreak + 0.05, tA1 = tOut + L1 / (SPD * 0.85), tGrab = tA1 + L2 / SPD;
    const tK = tGrab + 0.3, T_DRAG = tK + 1.25, DUR = tK + 3.4;
    const zAt = (t) => {   // the first one's floor position
      if (t <= tOut) return { x: A0.x, z: A0.z };
      if (t <= tA1) { const k = (t - tOut) / (tA1 - tOut); return { x: lerp(A0.x, A1.x, k), z: lerp(A0.z, A1.z, k) }; }
      const k = clamp((t - tA1) / Math.max(0.05, tGrab - tA1)); return { x: lerp(A1.x, A2.x, k), z: lerp(A1.z, A2.z, k) };
    };
    // The attack's frame: forward toward it at the grab, x to its right.
    const yK = R.yawTo(P1.x, P1.z, A2.x, A2.z);
    const fK = { x: -Math.sin(yK), z: Math.cos(yK) }, rK = { x: Math.cos(yK), z: Math.sin(yK) };
    const inK = (x, z) => ({ x: inX(P1.x + rK.x * x + fK.x * z), z: P1.z + rK.z * x + fK.z * z });

    // ---- the mobs -----------------------------------------------------------------------------------------------
    const z1 = R.mob("Zombie", { amb: [0.2, 0.2, 0.2], own: true });
    const jaw = splitJaw(z1, [{ part: z1.parts.head, box: boxOf("zombie", "bipedHead"), rows: 2 }, { part: z1.parts.headwear, box: boxOf("zombie", "bipedHeadwear"), rows: 2 }]);
    // (the jaw's teeth, tongue and mouth are flat colours: lit here like the rest of its head, or they glow in the dark)
    const jawBase = Object.fromEntries(Object.entries(jaw.mats).map(([k, m]) => [k, m.color.clone()]));
    const lightJaw = (k) => { for (const [n, m] of Object.entries(jaw.mats)) m.color.copy(jawBase[n]).multiplyScalar(k); };
    z1.anim(0, 0, { walk: 0 }); R.place(z1, A0.x, 0, A0.z, 0);
    // two more, behind it in the passage (in the dark), out after it
    const others = [
      { m: R.mob("Zombie", { amb: [0.2, 0.2, 0.2] }), from: hasDoor ? D.in(2.45) : { x: G.x + 0.5, z: G.z - 1.2 }, to: inK(-0.8, 0.4), t0: tBreak + 0.9, lean: -0.5 },
      { m: R.mob("Zombie", { amb: [0.2, 0.2, 0.2] }), from: hasDoor ? D.in(3.3) : { x: G.x - 0.4, z: G.z - 2.2 }, to: inK(0.85, 0.25), t0: tBreak + 1.7, lean: -0.5 }
    ];
    // they walk out at a zombie's pace (a little slower than the first), in the dark until they reach the doorway
    for (const q of others) {
      q.mid = hasDoor ? D.in(-0.4) : q.from;
      q.l1 = Math.hypot(q.mid.x - q.from.x, q.mid.z - q.from.z); q.l2 = Math.hypot(q.to.x - q.mid.x, q.to.z - q.mid.z);
      q.tArr = q.t0 + (q.l1 + q.l2) / 2.5; q.tOut = q.t0 + q.l1 / 2.5;
    }
    const faceL = R.ownLight(R.light(0xffb070, 0, 2.4, 1.4));

    // ---- the head -----------------------------------------------------------------------------------------------
    const hits = hitsOf([[tK + 0.02, 5, 1], [tK + 0.6, 5, -1], [tK + 1.15, 3, 1], [tK + 2.3, 4, -1], [tK + 2.95, 3, 1]]);
    const doorC = { x: G.x - side * 0.1, y: 1.05, z: G.z };
    const neck = (t) => sstep(tGrab, tK - 0.05, t) * (1 - sstep(T_DRAG, T_DRAG + 0.6, t));   // its teeth in your neck
    const posAt = (t) => { const k = sstep(tBk0, tBk1, t); return { x: P1.x * k, z: P1.z * k }; };
    const headZ = (t, out = {}) => { const q = zAt(t); out.x = q.x; out.y = 1.62; out.z = q.z; return out; };
    const yawTo2 = (c, q) => R.yawTo(c.x, c.z, q.x, q.z);
    const wrap = (a) => Math.atan2(Math.sin(a), Math.cos(a));
    const cam = (t) => {
      const s = settle(R, t, 0.9);
      const k = sstep(0.8, 1.3, t), p = posAt(t);
      const c = { x: lerp(s.x, p.x, k), y: lerp(s.y, eye, k), z: lerp(s.z, p.z, k), yaw: lerp(s.yaw, 0, k), pitch: lerp(s.pitch, -0.02, k), roll: 0, fov: s.fov, near: t >= tBreak ? 0.02 : undefined };
      // the turn to the door, and the eyes on it while you back away
      const ty = sstep(tT0, tT1, t), aimD = { y: yawTo2(c, doorC), p: R.pitchTo(c.x, c.y, c.z, doorC.x, doorC.y, doorC.z) };
      c.yaw = lerp(c.yaw, c.yaw + wrap(aimD.y - c.yaw), ty); c.pitch = lerp(c.pitch, clamp(aimD.p, -0.45, 0.2), ty);
      // backing: a step every ~0.5 s, the head dipping with each
      if (t > tBk0 && t < tBk1 + 0.1) c.y -= 0.035 * Math.abs(Math.sin((t - tBk0) * Math.PI / 0.5));
      // the bump: backed into the wall
      if (pinned) c.y -= 0.02 * pulse(t, [tBk1], 0.12);
      // From the break: on it as it comes; at the grab, square to it.
      if (t >= tBreak - 0.05) {
        const q = headZ(Math.min(t, tGrab)), w = sstep(tBreak - 0.05, tBreak + 0.35, t);
        const ly = yawTo2(c, q), lp = clamp(R.pitchTo(c.x, c.y, c.z, q.x, 1.55, q.z), -0.3, 0.25);
        c.yaw = lerp(c.yaw, c.yaw + wrap(ly - c.yaw), w); c.pitch = lerp(c.pitch, lp, w);
      }
      // the kill: pulled in, bitten, dragged down under them
      if (t >= tGrab) {
        const nb = neck(t);
        // the head thrown back and aside as it goes for the throat: its face low in the view, biting down
        c.yaw += 0.14 * nb; c.pitch += 0.2 * nb + 0.08 * pulse(t, hits.slice(0, 3).map((h) => h.t), 0.15); c.roll -= 0.08 * nb;
        const kk = kick(t, hits.map((h) => ({ t: h.t, side: h.side, amp: 0.9 })));
        const pl = track([[tGrab, 0], [tK, 0.06, "i"], [tK + 0.4, 0.03], [T_DRAG, 0.05], [tK + 2.1, -0.3, "i"], [DUR, -0.35]])(t);
        c.x += fK.x * pl; c.z += fK.z * pl; c.yaw += kk.yaw; c.pitch += kk.pitch;
        c.y = lerp(c.y, 0.3, sstep(T_DRAG, tK + 2.15, t) ** 1.6);
        c.pitch = lerp(c.pitch, 1.25, sstep(T_DRAG + 0.2, tK + 2.3, t));
        c.roll += 0.32 * sstep(T_DRAG, tK + 2.9, t) * -side;
        c.near = 0.02;
      }
      c.fov = s.fov + 4 * pulse(t, [tBreak], 0.2) + 3 * pulse(t, [tK], 0.12) - 3 * sstep(tT1, tBreak, t) * (1 - sstep(tBreak, tBreak + 0.3, t));
      const amp = 0.002 + 0.004 * sstep(b1, tBreak, t) + 0.018 * pulse(t, bangs, 0.14) * (t < tBreak + 0.1 ? 1 : 0) + 0.03 * pulse(t, [b1, tBreak], 0.16) + 0.02 * pulse(t, [tGrab, ...hits.map((h) => h.t)], 0.2) + 0.012 * sstep(T_DRAG, T_DRAG + 0.5, t);
      return shake(c, t, amp, 3);
    };

    // ---- gore -------------------------------------------------------------------------------------------------
    hits.forEach((h, i) => {
      const up = i < 3, at = (x, y, z) => { const q = inK(x, z); return [q.x, y, q.z]; };
      R.burst(h.t, at(up ? 0.28 : 0.1 * (i % 2 ? -1 : 1), up ? 1.4 : 0.25, up ? 0.45 : 0.5), 30, "blood", { dir: up ? [rK.x * 1.0 + fK.x * 0.4, 0.9, rK.z * 1.0 + fK.z * 0.4] : [fK.x * 0.4, 1.3, fK.z * 0.4], speed: 2.3, spread: 0.6, size: 0.03, life: 1.3, stick: 3 });
      R.burst(h.t + 0.02, at(up ? 0.25 : 0, up ? 1.38 : 0.3, up ? 0.5 : 0.5), 8, "flesh", { dir: [fK.x * 0.6, 0.9, fK.z * 0.6], speed: 1.6, spread: 0.6, size: 0.06, life: 1.2, stick: 3 });
    });
    // grit off the lintel with the blows, and the door's own bits when it goes
    if (hasDoor) {
      bangs.forEach((b, i) => { const q = D.in(-0.12); R.burst(b + 0.02, [q.x, 2.0, q.z], 3 + i, "stone", { dir: [0, -0.3, 0], speed: 0.3, spread: 0.35, size: 0.016, life: 1.1, grav: 9, stick: 0.5 }); });
      const q = D.in(-0.3); R.burst(tBreak, [q.x, 1.4, q.z], 26, "dust", { dir: [-side * 1.0, 0.3, 0], speed: 1.4, spread: 0.7, size: 0.05, life: 0.9, stick: 1.2 });
    }
    const bits = hasDoor ? D.breakAt(tBreak, { out: 2.4, n: 72 }) : null;
    if (hasDoor) D.carve();

    // ---- the sound ------------------------------------------------------------------------------------------------
    const dW = hasDoor ? [D.face, 1.0, D.z] : [G.x, 1.6, G.z], inside = hasDoor ? [D.in(1.6).x, 1.6, D.in(1.6).z] : [G.x, 1.6, G.z - 1];
    const steps = [];
    for (let s = tOut + 0.15; s < tGrab - 0.05; s += 0.42) { const q = zAt(s); steps.push([s, "mob.zombie.step", { at: [q.x, 0.1, q.z], volume: 0.8 }]); }
    const sounds = [
      ...(hasDoor ? [
        ...bangs.map((b, i) => [b, "mob.zombie.wood", { at: dW, volume: 1.0 + 0.06 * i, pitch: 0.95 + 0.05 * ((i * 7) % 3) }]),
        [bangs[1] + 0.4, "mob.zombie.say", { at: inside, volume: 0.65, pitch: 0.8, reverb: 0.5 }],
        [bangs[3] + 0.25, "mob.zombie.say", { at: inside, volume: 0.8, pitch: 0.72, reverb: 0.4 }],
        [tBreak, "mob.zombie.woodbreak", { at: dW, volume: 1.35 }], [tBreak + 0.01, "dig.wood", { at: dW, volume: 1.0, pitch: 0.8 }],
        [tBk1 + 0.02, pinned ? "step.stone" : "step.gravel", { volume: 0.7, pitch: 0.8 }]
      ] : [
        [b1, "mob.zombie.say", { at: dW, volume: 1.0, pitch: 0.82, reverb: 0.5 }], [b1 + 1.4, "mob.zombie.step", { at: [G.x, 0.1, G.z], volume: 0.5 }]
      ]),
      ...roar(tBreak + 0.22, [["mob.zombie.say", { at: [A1.x, 1.7, A1.z], pitch: 0.75 }]], { hit: 0.5 }),
      ...steps,
      [(tA1 + tGrab) / 2, "mob.zombie.say", { at: [zAt((tA1 + tGrab) / 2).x, 1.7, zAt((tA1 + tGrab) / 2).z], volume: 1.0, pitch: 0.68 }],
      [tGrab, "dig.cloth", { volume: 0.9, pitch: 0.7 }], [tGrab + 0.02, "mob.zombie.hurt", { at: [A2.x, 1.7, A2.z], volume: 1.1, pitch: 0.6 }],
      ...hits.flatMap((h, i) => blow(h.t, { volume: i ? 0.9 : 1.15, gore: i % 2 === 1 })),
      ...deathScream(tK + 0.2, { volume: 1.2, under: false }),
      [tK + 0.55, "mob.zombie.hurt", { volume: 0.8, pitch: 0.75 }],
      [others[0].tOut, "mob.zombie.say", { at: [others[0].mid.x, 1.6, others[0].mid.z], volume: 0.9, pitch: 0.9 }],
      [others[1].tOut, "mob.zombie.say", { at: [others[1].mid.x, 1.6, others[1].mid.z], volume: 0.9, pitch: 1.05 }],
      ...others.flatMap((q) => [0.5, 1.0, 1.5].map((d) => q.tOut + d).filter((x) => x < q.tArr).map((x) => [x, "mob.zombie.step", { at: [q.to.x, 0.1, q.to.z], volume: 0.5 }])),
      [T_DRAG + 0.85, "game.player.hurt.fall.small", { volume: 0.9 }],
      [tK + 2.2, "qf.scare.gore", { volume: 1 }],
      [DUR - 0.4, "qf.scare.crunch", { volume: 1 }],
      [DUR, "game.player.die"], [DUR, "@muffle", { hz: 380, s: 3.5 }]
    ];
    const loops = [
      [0.55, tBreak, "qf.scare.heartbeat", { volume: 0.55, fadeOut: 0.1 }],
      [tBk0 - 0.2, tBreak, "qf.scare.breath", { volume: 0.4, pitch: 1.15, fadeIn: 0.4, fadeOut: 0.2 }],
      [0.3, tBreak, "qf.scare.drone", { volume: 0.35, fadeIn: 1.5, fadeOut: 0.3, bus: "sfx" }],
      [tBreak, DUR + 0.2, "qf.scare.heartbeat", { volume: 0.7, pitch: 1.4, fadeIn: 0.05 }]
    ];

    // At the end, hands come into the lens from the edges and close over it.
    const hands = lensLimbs(R, others[0].m, "rightArm", [
      { from: [-0.42, -0.3], to: [-0.12, -0.04], t0: tK + 2.6, t1: tK + 3.15, scale: 0.5, z: -0.3, twist: 0.05 },
      { from: [0.44, -0.26], to: [0.1, -0.02], t0: tK + 2.75, t1: tK + 3.25, scale: 0.5, z: -0.31, twist: 0.06 },
      { from: [0.1, 0.36], to: [0.02, 0.08], t0: tK + 2.9, t1: tK + 3.35, scale: 0.55, z: -0.29, twist: 0.04 },
      { from: [-0.3, 0.32], to: [-0.06, 0.06], t0: tK + 3.0, t1: DUR, scale: 0.5, z: -0.28, twist: 0.05 },
      // its hands on your shoulders, at the grab
      { from: [-0.66, -0.52], to: [-0.4, -0.3], t0: tGrab, t1: tGrab + 0.14, scale: 0.5, z: -0.3, twist: 0.03, t2: T_DRAG + 0.4 },
      { from: [0.68, -0.5], to: [0.4, -0.3], t0: tGrab + 0.03, t1: tGrab + 0.17, scale: 0.5, z: -0.31, twist: 0.03, t2: T_DRAG + 0.45 }
    ], { color: 0x6a6a6a });
    function poseZombie(m, t, lean, armsUp = 1.55, bite = 0, swing = 0) {
      m.anim(t, 0, { walk: 0 });
      zombieArms(m, t, swing);
      const P = m.parts;
      if (P.rightArm && armsUp !== 1.55) { P.rightArm.rotation.x = armsUp + Math.sin(t * 9) * 0.06; P.leftArm.rotation.x = armsUp + Math.sin(t * 9 + 1) * 0.06; }
      if (P.head) P.head.rotation.x = 0.15 - bite * 0.3;
      if (P.headwear && P.head) P.headwear.rotation.copy(P.head.rotation);
      m.pivot.rotation.x = lean;
    }
    const legs = (m, t, on, rate = 7) => { const P = m.parts; if (P.rightLeg) { const a = on ? Math.sin(t * rate) * 0.55 : 0; P.rightLeg.rotation.x = a; P.leftLeg.rotation.x = -a; } };

    function update(t, f) {
      const cl = R.toLocal(R.camera.position);
      const bite = pulse(t, hits.slice(0, 3).map((h) => h.t - 0.06), 0.16);
      const grab = sstep(tGrab, tGrab + 0.18, t);
      let open = 0, lit = 0;
      if (hasDoor) {
        // The door: each blow bows it out and back; the crack, stage by stage; gone at the break.
        const bul = Math.max(0, ...bangs.map((b) => (t >= b ? Math.exp(-(t - b) / 0.07) * Math.sin(Math.min(1, (t - b) / 0.04) * Math.PI / 2) : 0)));
        const crack = bangs.reduce((a, b, i) => a + (t >= b ? (i ? 0.17 : 0.08) : 0), 0);
        D.update(t, { crack: Math.min(0.95, crack), bulge: bul, gone: t >= tBreak });
        bits(t);
      }
      if (t < tGrab) {
        // Behind the door, beating on it (its swing); then out through it and at you, lurching.
        const q = zAt(t), moving = t > tOut && t < tGrab;
        const target = t < tOut ? (hasDoor ? D.in(-1) : { x: 0, z: 0 }) : cl;
        R.place(z1, q.x, 0, q.z, R.yawTo(q.x, q.z, target.x, target.z) + (moving ? 0.06 * Math.sin(t * 7) : 0));
        const sw = hasDoor && t < tBreak ? Math.max(0, ...bangs.map((b) => (t >= b - 0.15 && t < b + 0.15 ? (t - b + 0.15) / 0.3 : 0))) : 0;
        poseZombie(z1, t, (moving ? -0.12 : 0) - 0.05 * grab, 1.55 + (grab > 0 ? 0.1 * grab + 0.01 : 0), 0, sw);
        legs(z1, t, moving, 8);
        z1.pivot.visible = true;
        open = 0.12 + 0.2 * sstep(tBreak, tBreak + 0.3, t) + 0.45 * grab;
        lit = hasDoor ? sstep(tBreak + 0.1, tA1 + 0.2, t) : sstep(b1 + 1, tA1, t);
        if (z1.parts.rightArm && grab > 0) { z1.parts.rightArm.rotation.y = 0.1 + 0.38 * grab; z1.parts.leftArm.rotation.y = -0.1 - 0.38 * grab; }
      } else {
        // The kill: on you, biting; it goes down with you.
        const lunge2 = 0.08 * pulse(t, hits.slice(0, 3).map((h) => h.t - 0.08), 0.12) * sstep(tGrab, tK - 0.1, t);
        // its head in at the side of your neck (the head pushed away from it); then down with you
        const nb = neck(t);
        const dz = -lunge2 * 0.6 + 0.1 * sstep(T_DRAG, T_DRAG + 0.9, t), w = 0.02 * Math.sin(t * 3) + 0.06 * nb, Z = A2;
        z1.pivot.visible = true;
        R.place(z1, Z.x + rK.x * w + fK.x * dz, 0, Z.z + rK.z * w + fK.z * dz, R.yawTo(Z.x, Z.z, cl.x, cl.z) + 0.05 * Math.sin(t * 2.1) - 0.25 * nb);
        poseZombie(z1, t, -0.05 - lunge2 * 0.6 - 0.06 * nb - 0.45 * sstep(T_DRAG, T_DRAG + 1.1, t), 1.55 + 0.15 * grab, bite + 0.5 * nb);
        if (z1.parts.rightArm) { z1.parts.rightArm.rotation.y = 0.1 + 0.38 * grab; z1.parts.leftArm.rotation.y = -0.1 - 0.38 * grab; }
        open = (0.12 + 0.45 * grab) * (1 - sstep(tGrab, tK, t)) + (0.25 + 0.75 * bite) * sstep(tGrab, tK, t);
        lit = 0.7 * (1 - 0.6 * sstep(T_DRAG, T_DRAG + 1, t));
      }
      jaw.set(open);
      z1.setOwn(0.03 + 0.17 * lit);
      hands(t);
      for (const q of others) {
        // out of the passage after it (dark in there), into the light and over you
        const u = Math.max(0, t - q.t0) * 2.5;
        let x, z;
        if (u < q.l1) { const k = u / q.l1; x = lerp(q.from.x, q.mid.x, k); z = lerp(q.from.z, q.mid.z, k); }
        else { const k = Math.min(1, (u - q.l1) / Math.max(0.01, q.l2)); x = lerp(q.mid.x, q.to.x, k); z = lerp(q.mid.z, q.to.z, k); }
        q.m.amb.setScalar(hasDoor ? lerp(0.025, 0.2, sstep(q.l1 - 1.2, q.l1 + 0.2, u)) : 0.2);
        q.m.pivot.visible = true;
        R.place(q.m, x, 0, z, R.yawTo(x, z, cl.x, cl.z));
        poseZombie(q.m, t + q.t0, q.lean * sstep(q.tArr, q.tArr + 0.8, t), 1.55 - 0.45 * sstep(q.tArr, q.tArr + 0.8, t), 0);
        legs(q.m, t, t > q.t0 && t < q.tArr, 8);
      }
      // a sliver of corridor light on its face as it comes out of the doorway (a lamp above the eyes)
      faceL.position.set(0, 0.32, -0.05).applyQuaternion(R.camera.quaternion).add(R.camera.position);
      faceL.intensity = 0.3 * lit * clamp(z1.pivot.position.distanceTo(R.camera.position) / 0.9, 0.25, 1);
      lightJaw(0.6 * clamp(z1.amb.x + 0.03 + 0.17 * lit + 0.8 * faceL.intensity, 0.12, 1));   // (bone in shadow: under the skin's brightness)
      const closing = sstep(tK + 1.95, DUR, t);
      f.env = { bake: 1 - 0.2 * sstep(0.2, 1.2, t) - 0.25 * sstep(T_DRAG, T_DRAG + 0.9, t) - 0.3 * closing, lights: 1 - 0.3 * sstep(T_DRAG, T_DRAG + 0.9, t) - 0.4 * closing, fogMul: 1 + 0.6 * sstep(0.5, 3.5, t) };
      f.vig = [12, 0, 0, 0.3 * sstep(b1, tBreak, t) + 0.25 * sstep(T_DRAG, T_DRAG + 0.9, t) + 0.4 * closing]; f.vigR = 0.9;
      f.black = 0.85 * sstep(tK + 2.95, DUR, t);
      f.splats = [hits[0], hits[1], hits[3]].filter((h) => t >= h.t).map((h, i) => ({ t0: h.t, x: [0.3, 0.7, 0.5][i], y: [0.38, 0.3, 0.6][i], r: [12, 11, 14][i], seed: 11 + i }));
    }
    return { dur: DUR, hits, cam, update, sounds, loops, deathSide: -side, solid: hasDoor ? (w) => D.solid(w) : undefined,
      marks: { dread: bangs[2] + 0.2, fake: tBreak + 0.25, lunge: tGrab + 0.1, kill: tK + 1.0 },
      notes: { door: hasDoor, side, face: hasDoor ? +D.face.toFixed(2) : null, dz: hasDoor ? +D.z.toFixed(2) : null, back: +back.toFixed(2), pinned, tBreak: +tBreak.toFixed(2), tK: +tK.toFixed(2), dur: +DUR.toFixed(2) } };
  }
};
