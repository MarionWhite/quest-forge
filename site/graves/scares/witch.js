// Witch: potions. A cackle down the corridor. A bottle comes out of the dark and shatters at your feet in a purple
// splash: nausea, the 1.7.10 warp, the corridor stretching. In the haze she is everywhere: a flash of her to the left,
// to the right, close, gone, and the cackle comes from wherever she is not. She walks out of the haze toward you, and
// comes apart into purple. The laughing stops. Only the warp, breathing. Then her face swings in from the side you are
// not watching, the nose, the jaw dropped open under it, green eyes lit, shrieking. She breaks Harming on your face;
// you drop. She stands over you and lets the last one fall.
import { THREE, track, clamp, lerp, sstep, pulse, tex, quad } from "./rig.js";
import { settle, shake, hitsOf, floorFall, particles, potionTex, spell, glowEyes } from "./common.js";
import { lunge, lungeFx, screech, splitJaw, faceAnchor, boxOf, silence, deathScream, glimpse, jit } from "./fnaf.js";

const NAUSEA = 0x551d4a, HARM = 0x430a09;   // Potion.confusion / Potion.harm liquid colours

export default {
  death: "Steve was killed by Witch using magic",
  async build(R) {
    const [partTex, nauseaTex, harmTex] = await Promise.all([tex("particles"), potionTex(NAUSEA), potionTex(HARM)]);
    const W = R.mob("Witch", { amb: [0.03, 0.03, 0.03], own: true });
    const hb = boxOf("witch", "villagerHead");
    const jaw = splitJaw(W, [{ part: W.parts.head, box: hb, rows: 2 }], { nTeeth: 3, max: 0.7 });
    const eyes = glowEyes(R, W, [[-2.5, -3.5, -4.07, 0.8, 0.8], [2.5, -3.5, -4.07, 0.8, 0.8]], [0.35, 1, 0.15], { halo: 0.14, glow: 0.45 });
    W.anim(0, 0, { walk: 0 }); R.place(W, 0, 0, 3, Math.PI);
    const anchor = faceAnchor(W, W.parts.head, hb); anchor.y -= 0.08;
    const zFar = clamp(R.ahead - 1.2, 4, 9), zNear = clamp(R.ahead - 0.8, 2.0, 2.4), wx = 0.15;
    // ---- the dice -------------------------------------------------------------------------------------------
    const T_CACKLE = 0.9 + R.vary(0.4, 0.5), T_T1 = T_CACKLE + R.vary(0.45, 0.4), T_S1 = T_T1 + 0.6;
    const nIll = 2 + Math.floor(R.rand() * 3);
    const tIll = [...Array(nIll)].map((_, i) => T_S1 + 0.9 + i * R.vary(0.55, 0.4));
    const ills = tIll.map((_, i) => { const sd = i % 2 ? 1 : -1; const x = sd * clamp((sd < 0 ? R.wallL : R.wallR) - 0.6, 0.6, 2.2) * R.vary(0.8, 0.2); return { x, z: R.vary(2.6, 0.4) + (i === nIll - 1 ? -1.1 : 0) }; });
    const tW0 = tIll[nIll - 1] + R.vary(0.7, 0.4), tGone = tW0 + R.vary(1.3, 0.25);
    const tSil = tGone + 0.05, t0 = tGone + R.vary(1.6, 0.45);
    const lside = R.pick([-1, 1]);
    const start = { x: lside * clamp((lside < 0 ? R.wallL : R.wallR) - 0.45, 0.5, 0.9), z: 0.15 };
    const L = lunge(R, W, { t0, rush: R.vary(0.21, 0.15), hold: R.vary(0.65, 0.15), dist: 0.36, anchor, seed: 23, side: lside * 0.18 });
    const tK = L.t3, T_S2 = tK + 0.12, T_T3 = T_S2 + R.vary(1.6, 0.15), DUR = T_T3 + 0.55;
    const hits = hitsOf([[T_S2, 16, -1], [DUR - 0.05, 4, 1]]);
    const feet = [0.05, 0.05, 0.45];
    const bottles = [
      { tx: nauseaTex, t0: T_T1, t1: T_S1, from: [wx, 1.5, zFar + 1.5], to: feet },
      { tx: harmTex, t0: T_T3, t1: DUR - 0.05, from: [wx - 0.1, 1.2, 0.65], to: [0, 0.4, -0.3] }
    ].map((b) => { const q = quad(b.tx, 0.32, 0.32, { alphaTest: 0.1, color: 0xaaaaaa }); q.visible = false; R.add(q); return { ...b, q }; });
    const puffs = particles(R, partTex, [
      ...spell(feet, T_S1, 46, [0.65, 0.22, 0.6], { spread: 1.1, rise: 1.1, life: 1.8, size: 0.16, seed: 3, window: 0.25 }),
      ...spell([wx, 1.0, 1.6], tGone, 40, [0.6, 0.2, 0.62], { spread: 0.6, rise: 0.7, life: 1.4, size: 0.15, seed: 8, window: 0.2 }),
      ...spell([0, 1.1, 0.35], T_S2, 40, [0.75, 0.08, 0.06], { spread: 0.7, rise: 0.8, life: 1.3, size: 0.14, seed: 4 }),
      ...spell([0, 0.3, -0.2], DUR - 0.05, 30, [0.75, 0.08, 0.06], { spread: 0.6, rise: 0.8, life: 1.3, size: 0.14, seed: 5 })
    ]);
    R.burst(T_S1, feet, 18, "white", { dir: [0, 1.2, 0], speed: 2, spread: 0.9, size: 0.03, life: 0.7 });
    R.burst(T_S2, [0, 1.45, 0.25], 18, "white", { dir: [0, 0.8, 0.4], speed: 2, spread: 0.9, size: 0.03, life: 0.7 });
    R.burst(T_S2 + 0.02, [0, 1.4, 0.3], 34, "blood", { dir: [0, 0.6, 0.8], speed: 2.4, spread: 0.8, size: 0.05, life: 1.4, stick: 3 });
    const glow = R.ownLight(R.light(0xb040ff, 0, 7, 1.4));
    const lamp = R.ownLight(R.light(0xc8ffb0, 0, 2.5, 1.4));
    const witchZ = (t) => t < tW0 ? zFar + 1 : lerp(zFar, 1.6, sstep(tW0, tGone, t));
    const yLunge = lside * 0.42;
    const pitch = track([[0, 0], [T_CACKLE, 0.02], [T_S1, 0.0], [T_S1 + 0.25, -0.75, "o"], [T_S1 + 0.9, -0.3], [tIll[0] + 0.2, 0.0], [tGone, 0.02], [t0, -0.02], [L.t1, 0.04, "x"], [tK, 0.04]]);
    const yk = [[0, 0], [T_S1, 0.0], [T_S1 + 0.25, 0.12]];
    tIll.forEach((tt, i) => yk.push([tt + 0.15, clamp(R.yawTo(0, 0, ills[i].x, ills[i].z) * 0.7, -0.7, 0.7), "o"]));
    yk.push([tW0 + 0.3, 0.02], [tGone + 0.6, -lside * 0.35], [t0, -lside * 0.25], [L.t1, yLunge, "x"], [tK, yLunge * 0.4]);
    const yaw = track(yk);
    const fov = track([[0, R.start.fov], [T_S1, R.start.fov], [T_S1 + 1.2, R.start.fov + 22], [tW0, R.start.fov + 8], [tGone, R.start.fov - 4], [t0, R.start.fov + 6], [L.t1, R.start.fov + 14, "x"], [tK, R.start.fov + 6], [T_S2 + 0.6, R.start.fov + 4]]);
    const cam = (t) => {
      const s = settle(R, t, 0.9);
      const k = sstep(0.8, 1.3, t);
      const c = { x: s.x * (1 - k), y: s.y, z: s.z * (1 - k), yaw: lerp(s.yaw, yaw(t), k), pitch: lerp(s.pitch, pitch(t), k), roll: 0, fov: fov(t), near: t >= t0 && t < tK ? 0.02 : undefined };
      const n = sstep(T_S1 + 0.2, T_S1 + 1.0, t);
      c.roll += n * Math.sin(t * 1.7) * 0.09; c.x += n * Math.sin(t * 1.3) * 0.08; c.yaw += n * Math.sin(t * 0.9) * 0.06;
      floorFall(c, t, T_S2 + 0.05, { d: 0.5, side: -1, roll: 1.0, y: 0.25, pitch: 0.3, back: 0.3 });
      if (t > T_S2 + 0.6) {
        const k2 = sstep(T_S2 + 0.6, T_T3 - 0.2, t), wz = 0.85;
        c.yaw = lerp(c.yaw, R.yawTo(c.x, c.z, wx, wz), k2); c.pitch = lerp(c.pitch, R.pitchTo(c.x, c.y, c.z, wx, 1.85, wz - 0.3), k2); c.roll = lerp(c.roll, -0.35, k2);
      }
      return shake(c, t, 0.002 + 0.02 * pulse(t, [T_S1, T_S2], 0.2) + L.shake(t), 5);
    };

    const S2 = screech(L, [["qf.scare.cackle", { pitch: 1.35 }], ["mob.witch.hurt", { pitch: 0.7, volume: 1.2 }]]);
    const sounds = [
      [T_CACKLE, "qf.scare.cackle", { at: [wx, 1.6, zFar + 2], volume: 0.9, reverb: 0.6 }],
      [T_T1, "random.bow", { at: [wx, 1.5, zFar + 1.5], volume: 0.5, pitch: 0.5 }],
      [T_S1, "game.potion.smash", { at: feet, volume: 1 }], [T_S1 + 0.02, "qf.scare.stinger", { volume: 0.45 }],
      [T_S1 + 0.6, "portal.trigger", { volume: 0.35, pitch: 1.4 }],
      // the cackle comes from where she is not
      ...tIll.map((tt, i) => [tt + 0.05, i % 2 ? "qf.scare.cackle" : "mob.witch.idle", { at: [-ills[i].x, 1.6, ills[i].z + 1], volume: 0.9, pitch: 0.9 + 0.08 * i, reverb: 0.5 }]),
      [tW0 + 0.2, "mob.witch.idle", { at: [wx, 1.6, zFar], volume: 0.9, pitch: 0.85 }],
      [tGone, "portal.trigger", { at: [wx, 1.2, 1.6], volume: 0.5, pitch: 1.8 }],
      silence(tSil, { fade: 0.3 }),
      [tSil + (t0 - tSil) * 0.6, "mob.witch.idle", { at: [start.x, 1.6, start.z], volume: 0.12, pitch: 0.6 }],
      ...S2.sounds,
      [T_S2, "game.potion.smash", { volume: 1.2 }], [T_S2 + 0.04, "qf.scare.gore", { volume: 0.9 }],
      [T_S2 + 0.5, "game.player.hurt.fall.small"],
      ...deathScream(T_S2 + 0.25, { volume: 1.15, under: false }),
      [T_T3 - 0.6, "qf.scare.cackle", { at: [wx, 1.7, 0.9], volume: 1 }],
      [DUR - 0.05, "game.potion.smash", { volume: 1 }],
      ...deathScream(DUR - 0.02, { volume: 1.25 }),
      [DUR, "game.player.die"], [DUR, "@muffle", { hz: 400, s: 3 }]
    ];
    const loops = [[0.5, tSil, "qf.scare.heartbeat", { volume: 0.5 }], [T_S1 + 0.3, tSil, "qf.scare.drone", { volume: 0.55, fadeIn: 1, pitch: 0.8, bus: "sfx" }],
      [tSil + 0.2, t0, "qf.scare.breath", { volume: 0.3, fadeIn: 0.6, fadeOut: 0.03 }], ...S2.loops,
      [tK, DUR + 0.2, "qf.scare.heartbeat", { volume: 0.7, pitch: 1.35 }]];

    function update(t, f) {
      const cl = R.toLocal(R.camera.position);
      const ill = tIll.findIndex((tt) => t >= tt && t < tt + 0.12);
      let open = 0, eyeOn = 0;
      if (t >= t0 && t < tK) {
        W.pivot.visible = true;
        R.place(W, start.x, 0, start.z, R.yawTo(start.x, start.z, cl.x, cl.z));
        W.anim(t, 0, { walk: 0 });
        if (W.parts.head) W.parts.head.rotation.set(jit(t, 21) * 0.1, jit(t, 23) * 0.12, jit(t, 25) * 0.1);
        L.apply(t);
        open = sstep(t0, L.t1, t) * (0.85 + 0.15 * jit(t, 31)); eyeOn = 1;
        W.setOwn(0.22);
      } else if (t >= tK) {
        // Over you: Harming broken on your face, then she leans in.
        W.pivot.visible = true;
        const wz = lerp(0.75, 0.85, sstep(tK, T_S2 + 0.5, t));
        R.place(W, wx, 0, wz, R.yawTo(wx, wz, cl.x, cl.z), -0.42 * sstep(T_S2 + 0.5, T_T3 - 0.4, t));
        W.anim(t, 0, { walk: 0 });
        open = 0.3 + 0.5 * pulse(t, [T_T3 - 0.6], 0.5); eyeOn = 0.8;
        W.setOwn(0.12);
      } else if (ill >= 0) {
        W.pivot.visible = true;
        const q = ills[ill];
        R.place(W, q.x, 0, q.z, R.yawTo(q.x, q.z, cl.x, cl.z));
        W.anim(t, 0, { walk: 0 }); open = 0.6; eyeOn = 1;
        W.setOwn(0.18);
      } else {
        const wz = witchZ(t);
        W.pivot.visible = t > tW0 - 0.2 && t < tGone;
        R.place(W, wx, 0, wz, R.yawTo(wx, wz, cl.x, cl.z));
        W.anim(t, 0, { walk: t > tW0 && t < tGone ? 0.5 : 0 });
        W.setOwn(0.02 + 0.08 * sstep(tW0, tW0 + 0.8, t));
        eyeOn = 0.5;
      }
      jaw.set(open); eyes(eyeOn);
      lamp.position.set(0, 0.3, -0.05).applyQuaternion(R.camera.quaternion).add(R.camera.position); lamp.intensity = t >= t0 && t < tK ? 0.3 : 0;
      for (const b of bottles) {
        const k = (t - b.t0) / (b.t1 - b.t0);
        b.q.visible = k >= 0 && k < 1;
        if (!b.q.visible) continue;
        const arc = Math.sin(k * Math.PI) * 0.9 * (b.t1 - b.t0);
        R.at(b.q, lerp(b.from[0], b.to[0], k), lerp(b.from[1], b.to[1], k) + arc, lerp(b.from[2], b.to[2], k));
        b.q.quaternion.copy(R.camera.quaternion); b.q.rotateZ(t * 14);
      }
      puffs(t);
      R.L(0, 0.8, 0.6, glow.position); glow.color.setHex(t < tK ? 0xb040ff : 0xff2010);
      glow.intensity = 4 * pulse(t, [T_S1], 0.5) + 3 * pulse(t, [T_S2, DUR - 0.05], 0.3) + 0.9 * sstep(T_S1, T_S1 + 1, t) * (t < tSil ? 1 : 0.4) + 2 * pulse(t, [tGone], 0.3);
      const n = sstep(T_S1 + 0.15, T_S1 + 0.9, t);
      f.env = { nausea: n * (0.75 + 0.25 * Math.sin(t * 1.3)), bake: 1 - 0.25 * sstep(0.2, 1.2, t) - 0.2 * sstep(tSil, tSil + 0.6, t) * (t < tK ? 1 : 0), fogMul: 1 + 2.2 * n, fog: [0.16, 0.04, 0.16, 0.7 * n] };
      f.tints = [[90, 20, 110, 0.12 * n], [160, 0, 0, 0.25 * pulse(t, [T_S2], 0.5)]];
      f.vig = [40, 0, 50, 0.3 + 0.3 * n]; f.vigR = 0.85;
      if (ill >= 0) f.fx = { tear: 0.25, split: 0.5, stat: 0.08 };
      f.black = 0.45 * sstep(DUR - 0.1, DUR + 0.5, t);
      lungeFx(L, t, f);
    }
    return { dur: DUR, hits, cam, update, sounds, loops, deathSide: -1,
      marks: { dread: tIll[0] + 0.05, fake: (tW0 + tGone) / 2 + 0.2, lunge: L.t1 + 0.12, kill: T_T3 - 0.3 },
      notes: { ills: nIll, lside, t0: +t0.toFixed(2), dur: +DUR.toFixed(2) } };
  }
};
