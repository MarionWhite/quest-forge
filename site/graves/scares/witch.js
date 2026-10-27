// Witch (round 7: her potions, as she throws them in the game). A cackle somewhere down the corridor. A bottle comes
// tumbling out of the dark and smashes at your feet: Slowness, grey swirls rising round you, the view narrowing and
// heavy (what Slowness does), the legs gone to lead. She walks out of the dark, in no hurry, the nose first, and stops
// a few blocks off to look at you. A second bottle: Poison, on your chest. The hearts go green, the view pulses with it,
// and you go down on your knees. She walks up, cackling, and leans over you; her face over yours. The cackle stops.
// She breaks Harming on your face. You go over, and she watches you go.
import { track, clamp, lerp, sstep, pulse, tex, quad } from "./rig.js";
import { settle, shake, hitsOf, floorFall, particles, potionTex, spell } from "./common.js";
import { splitJaw, boxOf, silence, deathScream } from "./fnaf.js";
import { kick } from "./story.js";

const SLOW = 0x5a6c81, POISON = 0x4e9331, HARM = 0x430a09;   // Potion.moveSlowdown / poison / harm liquid colours

export default {
  death: "Steve was killed by Witch using magic",
  async build(R) {
    const [partTex, slowTex, poisonTex, harmTex] = await Promise.all([tex("particles"), potionTex(SLOW), potionTex(POISON), potionTex(HARM)]);
    const W = R.mob("Witch", { amb: [0.03, 0.03, 0.03], own: true });
    const hb = boxOf("witch", "villagerHead");
    const jaw = splitJaw(W, [{ part: W.parts.head, box: hb, rows: 2 }], { nTeeth: 3, max: 0.55 });
    W.anim(0, 0, { walk: 0 }); R.place(W, 0, 0, 3, Math.PI);
    const zFar = clamp(R.ahead - 1.2, 4, 9), wx = 0.15;
    const zStop = clamp(R.ahead - 0.8, 1.9, 2.6);           // where she stops to look at you
    const zOver = 1.05;                                     // and where she stands to lean over you
    // ---- the dice -------------------------------------------------------------------------------------------
    const zA = Math.min(zFar + 1, zStop + 3.0);              // she stands down there from the first cackle, in the half-light
    const T_CACKLE = 0.9 + R.vary(0.4, 0.5), T_T1 = T_CACKLE + R.vary(0.5, 0.4), T_S1 = T_T1 + 0.6;
    const tW0 = T_S1 + R.vary(0.7, 0.35), walkIn = (zA - zStop) / 1.5, tStop = tW0 + walkIn;
    const T_T2 = tStop + R.vary(0.55, 0.35), T_S2 = T_T2 + 0.38;
    const tW1 = T_S2 + R.vary(0.6, 0.3), tOver = tW1 + (zStop - zOver) / 1.5;
    const tSil = tOver + R.vary(0.75, 0.35);                // she stops laughing
    const T_S3 = tSil + R.vary(0.55, 0.4), DUR = T_S3 + 1.6;
    const hits = hitsOf([[T_S2, 7, 1], [T_S2 + 1.0, 1, -1], [T_S2 + 2.0, 1, 1], [T_S3, 10, -1], [DUR - 0.05, 1, 1]]);
    const feet = [0.05, 0.05, 0.45], chest = [0.02, 1.25, 0.2];
    const hand = (z) => [wx - 0.05, 1.25, z - 0.35];
    const bottles = [
      { tx: slowTex, t0: T_T1, t1: T_S1, from: [wx, 1.4, zA - 0.3], to: feet, arc: 0.9 },
      { tx: poisonTex, t0: T_T2, t1: T_S2, from: hand(zStop), to: chest, arc: 0.35 },
      { tx: harmTex, t0: T_S3 - 0.32, t1: T_S3, from: [wx - 0.05, 1.5, zOver - 0.55], to: [0, 1.0, 0.12], arc: 0.25 }
    ].map((b) => { const q = quad(b.tx, 0.32, 0.32, { alphaTest: 0.1, color: 0xaaaaaa }); q.visible = false; R.add(q); return { ...b, q }; });
    const puffs = particles(R, partTex, [
      ...spell(feet, T_S1, 46, [0.35, 0.42, 0.5], { spread: 1.1, rise: 1.1, life: 1.8, size: 0.16, seed: 3, window: 0.25 }),
      ...spell([0, 0.6, 0.4], T_S1 + 0.6, 30, [0.35, 0.42, 0.5], { spread: 0.9, rise: 0.8, life: 1.6, size: 0.13, seed: 9, window: 2.5 }),
      ...spell(chest, T_S2, 40, [0.3, 0.58, 0.2], { spread: 0.7, rise: 0.8, life: 1.5, size: 0.14, seed: 4 }),
      ...spell([0, 0.5, 0.2], T_S2 + 0.5, 30, [0.3, 0.58, 0.2], { spread: 0.7, rise: 0.6, life: 1.4, size: 0.12, seed: 6, window: 3 }),
      ...spell([0, 0.9, 0.15], T_S3, 40, [0.75, 0.08, 0.06], { spread: 0.6, rise: 0.8, life: 1.3, size: 0.14, seed: 5 })
    ]);
    R.burst(T_S1, feet, 18, "white", { dir: [0, 1.2, 0], speed: 2, spread: 0.9, size: 0.03, life: 0.7 });
    R.burst(T_S2, chest, 16, "white", { dir: [0, 0.8, -0.4], speed: 2, spread: 0.9, size: 0.03, life: 0.7 });
    R.burst(T_S3, [0, 1.05, 0.15], 18, "white", { dir: [0, 0.8, 0.4], speed: 2, spread: 0.9, size: 0.03, life: 0.7 });
    R.burst(T_S3 + 0.02, [0, 1.0, 0.2], 34, "blood", { dir: [0, 0.8, 0.6], speed: 2.4, spread: 0.8, size: 0.05, life: 1.4, stick: 3 });
    const glow = R.ownLight(R.light(0x8090a0, 0, 7, 1.4));
    const wz = (t) => (t < tW0 ? zA : t < tStop ? lerp(zA, zStop, clamp((t - tW0) / walkIn)) : t < tW1 ? zStop : lerp(zStop, zOver, clamp((t - tW1) / (tOver - tW1))));
    const walking = (t) => (t > tW0 && t < tStop) || (t > tW1 && t < tOver);
    const lean = (t) => -0.3 * sstep(tOver - 0.3, tOver + 0.4, t);
    // Her face, for the head that watches her (her height, bent over you at the end).
    const faceY = (t) => 1.75 - 0.3 * sstep(tOver - 0.3, tOver + 0.4, t), faceZ = (t) => wz(t) - 0.62 * sstep(tOver - 0.3, tOver + 0.4, t);
    // Your eye: down on your knees from the poison.
    const eyeY = track([[0, R.eye], [T_S1, R.eye], [T_S1 + 0.6, R.eye - 0.08], [T_S2 + 0.25, R.eye - 0.08], [T_S2 + 0.9, 1.0, "i"], [tOver, 0.95]]);
    const fov = track([[0, R.start.fov], [T_S1, R.start.fov], [T_S1 + 0.7, R.start.fov - 13], [T_S2, R.start.fov - 13], [T_S2 + 0.5, R.start.fov - 8], [DUR, R.start.fov - 6]]);
    const cam = (t) => {
      const s = settle(R, t, 0.9);
      const k = sstep(0.8, 1.3, t);
      const c = { x: s.x * (1 - k), y: lerp(s.y, eyeY(t), k), z: s.z * (1 - k), yaw: 0, pitch: 0, roll: 0, fov: fov(t), near: t >= tOver - 0.4 ? 0.02 : undefined };
      // The look: down the corridor at the cackle; down after the bottle to the feet; up at her as she comes; on her.
      const lookHer = R.pitchTo(0, c.y, 0, wx, faceY(t), faceZ(t)), yHer = R.yawTo(0, 0, wx, faceZ(t));
      const feetK = sstep(T_S1 - 0.15, T_S1 + 0.15, t) * (1 - sstep(T_S1 + 0.5, tW0 + 0.4, t));
      const her = Math.max(0.6 * sstep(T_CACKLE, T_CACKLE + 0.8, t) * (1 - sstep(T_T1, T_T1 + 0.2, t)), sstep(tW0 - 0.3, tW0 + 0.6, t));
      let pitch = lerp(lerp(0.02, -0.72, feetK), lookHer, her * (1 - feetK)), yaw = lerp(lerp(0, 0.1, feetK), yHer, her);
      if (t > T_S2 - 0.1 && t < T_S2 + 0.5) pitch = lerp(pitch, -0.45, sstep(T_S2 - 0.1, T_S2 + 0.1, t) * (1 - sstep(T_S2 + 0.2, T_S2 + 0.5, t)));   // at the bottle on your chest
      c.pitch = lerp(s.pitch, pitch, k); c.yaw = lerp(s.yaw, yaw, k);
      // Heavy: slow sway; the poison's pulse.
      const hv = sstep(T_S1 + 0.2, T_S1 + 1.0, t), pz = sstep(T_S2, T_S2 + 0.5, t);
      c.roll += hv * Math.sin(t * 0.9) * 0.04 + pz * Math.sin(t * 2.4) * 0.05; c.x += hv * Math.sin(t * 0.7) * 0.03;
      const kk = kick(t, [{ t: T_S2, side: 1, amp: 1.0 }, { t: T_S3, side: -1, amp: 1.6 }]); c.yaw += kk.yaw; c.pitch += kk.pitch;
      floorFall(c, t, T_S3 + 0.05, { d: 0.5, side: -1, roll: 1.0, y: 0.25, pitch: 0.3, back: 0.3 });
      if (t > T_S3 + 0.5) {
        const k2 = sstep(T_S3 + 0.5, DUR - 0.5, t);
        c.yaw = lerp(c.yaw, R.yawTo(c.x, c.z, wx, zOver), k2); c.pitch = lerp(c.pitch, R.pitchTo(c.x, c.y, c.z, wx, 1.75, zOver - 0.3), k2); c.roll = lerp(c.roll, -0.35, k2);
      }
      return shake(c, t, 0.002 + 0.02 * pulse(t, [T_S1, T_S2, T_S3], 0.2), 5);
    };

    const steps = [];
    for (let tt = tW0 + 0.2; tt < tStop; tt += 0.55) steps.push([tt, "step.stone", { at: [wx, 0, wz(tt)], volume: 0.3, pitch: 0.8 }]);
    for (let tt = tW1 + 0.2; tt < tOver; tt += 0.55) steps.push([tt, "step.stone", { at: [wx, 0, wz(tt)], volume: 0.4, pitch: 0.8 }]);
    const cackles = [tW1 + 0.15, tW1 + 0.9, tOver + 0.2].filter((x) => x < tSil - 0.2);
    const sounds = [
      [T_CACKLE, "qf.scare.cackle", { at: [wx, 1.6, zA], volume: 0.9, reverb: 0.6 }],
      [T_T1 - 0.05, "mob.witch.idle", { at: [wx, 1.6, zA], volume: 0.6, pitch: 0.9 }],
      [T_S1, "game.potion.smash", { at: feet, volume: 1.1 }],
      [T_S1 + 0.5, "qf.scare.whisper", { volume: 0.25 }],
      [tW0 + 0.4, "mob.witch.idle", { at: [wx, 1.6, wz(tW0 + 0.4)], volume: 0.8, pitch: 0.85 }],
      ...steps,
      [tStop + 0.25, "mob.witch.idle", { at: [wx, 1.6, zStop], volume: 0.9, pitch: 0.8 }],
      [T_T2 - 0.02, "random.bow", { at: hand(zStop), volume: 0.35, pitch: 0.55 }],
      [T_S2, "game.potion.smash", { at: chest, volume: 1.3 }], [T_S2 + 0.01, "qf.scare.hit", { volume: 0.8 }],
      [T_S2 + 0.6, "game.player.hurt.fall.small", { volume: 0.6 }],
      ...cackles.map((tt, i) => [tt, "qf.scare.cackle", { at: [wx, 1.6, wz(tt)], volume: 0.75 + 0.15 * i, pitch: 1.05 - 0.05 * i }]),
      silence(tSil, { fade: 0.15 }),
      [T_S3 - 0.3, "mob.witch.idle", { at: [wx, 1.5, zOver], volume: 0.35, pitch: 0.6 }],
      [T_S3, "game.potion.smash", { volume: 1.4 }], [T_S3 + 0.01, "qf.scare.hit", { volume: 1.1 }], [T_S3 + 0.04, "qf.scare.gore", { volume: 0.9 }],
      ...hits.filter((h) => h.t !== T_S3 && h.t !== T_S2).map((h) => [h.t, "game.player.hurt", { volume: 0.6 }]),
      [T_S2, "game.player.hurt"], [T_S3, "game.player.hurt"],
      ...deathScream(T_S3 + 0.2, { volume: 1.25, under: false }),
      [T_S3 + 0.9, "qf.scare.cackle", { at: [wx, 1.6, zOver], volume: 1, pitch: 0.9 }],
      [DUR, "game.player.die"], [DUR, "@muffle", { hz: 400, s: 3 }]
    ];
    const loops = [
      [0.5, tW0, "qf.scare.heartbeat", { volume: 0.5 }],
      [T_S1 + 0.3, tSil, "qf.scare.drone", { volume: 0.5, fadeIn: 1, pitch: 0.75, bus: "sfx" }],
      [tW0, tSil, "qf.scare.heartbeat", { volume: 0.55, pitch: 0.85 }],   // slowed
      [T_S2 + 0.3, tSil, "qf.scare.breath", { volume: 0.4, fadeIn: 0.6, pitch: 0.9 }],
      [tSil + 0.1, T_S3, "qf.scare.breath", { volume: 0.25, fadeOut: 0.03 }],
      [T_S3, DUR + 0.2, "qf.scare.heartbeat", { volume: 0.7, pitch: 1.35 }]
    ];

    function update(t, f) {
      const cl = R.toLocal(R.camera.position);
      const z = wz(t);
      W.pivot.visible = t > T_CACKLE - 0.3;
      R.place(W, wx, 0, z, R.yawTo(wx, z, cl.x, cl.z), lean(t));
      W.anim(t, 0, { walk: walking(t) ? 0.5 : 0 });
      if (W.parts.head) W.parts.head.rotation.x = clamp(Math.atan2(cl.y - faceY(t), Math.hypot(cl.x - wx, cl.z - z)) * 0.8 + 0.5 * sstep(tOver - 0.3, tOver + 0.4, t), -0.6, 0.9);
      // The cackle opens the mouth under the nose; shut in the silence.
      const cack = Math.max(0, ...cackles.map((c) => (t > c && t < c + 1.1 ? Math.abs(Math.sin((t - c) * 14)) * (1 - (t - c) / 1.1) : 0)), t > T_S3 + 0.9 && t < T_S3 + 2 ? Math.abs(Math.sin((t - T_S3) * 14)) * 0.8 : 0);
      jaw.set(0.6 * cack * (t < tSil || t > T_S3 ? 1 : 1 - sstep(tSil, tSil + 0.15, t)));   // shut in the silence
      W.setOwn(0.01 + 0.1 * sstep(tW0, tW0 + 1.2, t) + 0.06 * sstep(tOver - 0.5, tOver, t));
      for (const b of bottles) {
        const k = (t - b.t0) / (b.t1 - b.t0);
        b.q.visible = k >= 0 && k < 1;
        if (!b.q.visible) continue;
        const arc = Math.sin(k * Math.PI) * b.arc * (b.t1 - b.t0);
        R.at(b.q, lerp(b.from[0], b.to[0], k), lerp(b.from[1], b.to[1], k) + arc, lerp(b.from[2], b.to[2], k));
        b.q.quaternion.copy(R.camera.quaternion); b.q.rotateZ(t * 14);
      }
      puffs(t);
      // The splash light: grey at your feet, green on your chest, red in your face.
      R.L(0, 0.8, 0.5, glow.position);
      glow.color.setHex(t < T_S2 - 0.1 ? 0x8090a0 : t < T_S3 - 0.1 ? 0x60c040 : 0xff2010);
      glow.intensity = 3 * pulse(t, [T_S1], 0.5) + 3 * pulse(t, [T_S2, T_S3], 0.35) + 0.6 * sstep(T_S1, T_S1 + 1, t) * (t < tSil ? 1 : 0.4);
      const sl = sstep(T_S1 + 0.15, T_S1 + 0.9, t), po = t > T_S2 ? 0.5 + 0.5 * Math.sin((t - T_S2) * 4) : 0;
      f.hpMode = t > T_S2 && t < T_S3 ? "poison" : "normal";
      f.env = { bake: 1 - 0.25 * sstep(0.2, 1.2, t) - 0.15 * sstep(tSil, tSil + 0.6, t), fogMul: 1 + 0.6 * sl, fog: [0.2, 0.22, 0.26, 0.4 * sl] };
      f.tints = [[90, 100, 120, 0.08 * sl], [60, 140, 30, 0.12 * po * sstep(T_S2, T_S2 + 0.4, t) * (t < T_S3 ? 1 : 0)], [160, 0, 0, 0.25 * pulse(t, [T_S3], 0.5)]];
      f.vig = [20, 30, 20, 0.3 + 0.25 * sl + 0.2 * po]; f.vigR = 0.85;
      f.black = 0.45 * sstep(DUR - 0.1, DUR + 0.5, t);
    }
    return { dur: DUR, hits, cam, update, sounds, loops, deathSide: -1,
      marks: { dread: tStop + 0.3, fake: T_S2 + 0.15, lunge: T_S3 - 0.12, kill: T_S3 + 0.35 },
      notes: { zStop: +zStop.toFixed(2), tOver: +tOver.toFixed(2), T_S3: +T_S3.toFixed(2), dur: +DUR.toFixed(2) } };
  }
};
