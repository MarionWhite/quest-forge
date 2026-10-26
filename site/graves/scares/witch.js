// Witch: potions. A cackle down the corridor. A bottle comes out of the dark and shatters at your feet in a purple
// splash: nausea, the 1.7.10 warp, the corridor stretching. She walks out of the haze, laughing. A second potion,
// Harming, bursts red on your chest; you drop. She stands over you and lets the last one fall.
import { THREE, track, clamp, lerp, sstep, pulse, tex, quad } from "./rig.js";
import { settle, shake, hitsOf, floorFall, particles, potionTex, spell } from "./common.js";

const NAUSEA = 0x551d4a, HARM = 0x430a09;   // Potion.confusion / Potion.harm liquid colours

export default {
  death: "Steve was killed by Witch using magic",
  async build(R) {
    const [partTex, nauseaTex, harmTex] = await Promise.all([tex("particles"), potionTex(NAUSEA), potionTex(HARM)]);
    const W = R.mob("Witch", { amb: [0.03, 0.03, 0.03], own: true });
    const zFar = clamp(R.ahead - 1.2, 4, 9), zNear = clamp(R.ahead - 0.8, 2.0, 2.4), wx = 0.15;
    const T_CACKLE = 1.15, T_T1 = 1.55, T_S1 = 2.15, T_OUT = 2.8, T_T2 = 4.4, T_S2 = 4.78, T_T3 = 6.45, DUR = 7.0;
    const hits = hitsOf([[T_S2, 16, -1], [DUR - 0.05, 4, 1]]);   // Harming II twice; the nausea bottle does no harm
    const feet = [0.05, 0.05, 0.45];
    const bottles = [
      { tx: nauseaTex, t0: T_T1, t1: T_S1, from: [wx, 1.5, zFar + 1.5], to: feet },
      { tx: harmTex, t0: T_T2, t1: T_S2, from: [wx - 0.2, 1.45, zNear], to: [0, 1.25, 0.2] },
      { tx: harmTex, t0: T_T3, t1: DUR - 0.05, from: [wx - 0.1, 1.2, 0.65], to: [0, 0.4, -0.3] }
    ].map((b) => { const q = quad(b.tx, 0.32, 0.32, { alphaTest: 0.1, color: 0xaaaaaa }); q.visible = false; R.add(q); return { ...b, q }; });
    const puffs = particles(R, partTex, [
      ...spell(feet, T_S1, 46, [0.65, 0.22, 0.6], { spread: 1.1, rise: 1.1, life: 1.8, size: 0.16, seed: 3, window: 0.25 }),
      ...spell([0, 1.1, 0.35], T_S2, 40, [0.75, 0.08, 0.06], { spread: 0.7, rise: 0.8, life: 1.3, size: 0.14, seed: 4 }),
      ...spell([0, 0.3, -0.2], DUR - 0.05, 30, [0.75, 0.08, 0.06], { spread: 0.6, rise: 0.8, life: 1.3, size: 0.14, seed: 5 })
    ]);
    R.burst(T_S1, feet, 18, "white", { dir: [0, 1.2, 0], speed: 2, spread: 0.9, size: 0.03, life: 0.7 });
    R.burst(T_S2, [0, 1.25, 0.25], 18, "white", { dir: [0, 0.8, 0.4], speed: 2, spread: 0.9, size: 0.03, life: 0.7 });
    R.burst(T_S2 + 0.02, [0, 1.2, 0.3], 30, "blood", { dir: [0, 0.6, 0.8], speed: 2.2, spread: 0.8, size: 0.05, life: 1.4, stick: 3 });
    const glow = R.ownLight(R.light(0xb040ff, 0, 7, 1.4));

    const pitch = track([[0, 0], [T_CACKLE, 0.02], [T_S1, 0.0], [T_S1 + 0.25, -0.75, "o"], [T_OUT - 0.1, -0.6], [T_OUT + 0.5, 0.0], [T_T2, 0.02]]);
    const yaw = track([[0, 0], [T_S1, 0.0], [T_S1 + 0.25, 0.12], [T_OUT + 0.5, 0.05], [T_T2, 0.0]]);
    const fov = track([[0, R.start.fov], [T_S1, R.start.fov], [T_S1 + 1.2, R.start.fov + 22], [T_OUT + 1.0, R.start.fov - 6], [T_T2, R.start.fov + 14], [T_S2 + 0.6, R.start.fov + 4]]);
    const cam = (t) => {
      const s = settle(R, t, 0.9);
      const k = sstep(0.8, 1.3, t);
      const c = { x: s.x * (1 - k), y: s.y, z: s.z * (1 - k), yaw: lerp(s.yaw, yaw(t), k), pitch: lerp(s.pitch, pitch(t), k), roll: 0, fov: fov(t) };
      // Nausea sways the head too.
      const n = sstep(T_S1 + 0.2, T_S1 + 1.0, t);
      c.roll += n * Math.sin(t * 1.7) * 0.09; c.x += n * Math.sin(t * 1.3) * 0.08; c.yaw += n * Math.sin(t * 0.9) * 0.06;
      floorFall(c, t, T_S2 + 0.05, { d: 0.5, side: -1, roll: 1.0, y: 0.25, pitch: 0.3, back: 0.3 });
      if (t > T_S2 + 0.6) {   // on the floor, she comes to stand over you; look up into her face
        const k2 = sstep(T_S2 + 0.6, T_T3 - 0.2, t), wz = witchZ(t);
        c.yaw = lerp(c.yaw, R.yawTo(c.x, c.z, wx, wz), k2); c.pitch = lerp(c.pitch, R.pitchTo(c.x, c.y, c.z, wx, 1.85, wz - 0.3), k2); c.roll = lerp(c.roll, -0.35, k2);
      }
      return shake(c, t, 0.002 + 0.02 * pulse(t, [T_S1, T_S2], 0.2), 5);
    };
    const witchZ = (t) => t < T_OUT ? zFar + 1 : t < T_T2 ? lerp(zFar, zNear, sstep(T_OUT, T_T2 - 0.2, t)) : t < T_S2 + 0.5 ? zNear : lerp(zNear, 0.85, sstep(T_S2 + 0.5, T_T3 - 0.3, t));

    const sounds = [
      [T_CACKLE, "qf.scare.cackle", { at: [wx, 1.6, zFar + 2], volume: 0.9, reverb: 0.6 }],
      [T_T1, "random.bow", { at: [wx, 1.5, zFar + 1.5], volume: 0.5, pitch: 0.5 }],
      [T_S1, "game.potion.smash", { at: feet, volume: 1 }], [T_S1 + 0.02, "qf.scare.stinger", { volume: 0.45 }],
      [T_S1 + 0.6, "portal.trigger", { volume: 0.35, pitch: 1.4 }],
      [T_OUT + 0.3, "mob.witch.idle", { at: [wx, 1.6, zFar], volume: 0.9 }],
      [T_OUT + 0.9, "qf.scare.cackle", { at: [wx, 1.6, (zFar + zNear) / 2], volume: 1 }],
      [T_T2 - 0.2, "mob.witch.idle", { at: [wx, 1.6, zNear], volume: 1, pitch: 0.85 }],
      [T_T2, "random.bow", { at: [wx, 1.5, zNear], volume: 0.6, pitch: 0.5 }],
      [T_S2, "game.potion.smash", { volume: 1 }], [T_S2, "game.player.hurt"], [T_S2 + 0.02, "qf.scare.hit", { volume: 1 }], [T_S2 + 0.04, "qf.scare.gore", { volume: 0.8 }],
      [T_S2 + 0.5, "game.player.hurt.fall.small"], [T_S2 + 0.7, "qf.scare.scream", { volume: 0.7, pitch: 0.9 }],
      [T_T3 - 0.6, "qf.scare.cackle", { at: [wx, 1.7, 0.9], volume: 1 }],
      [DUR - 0.05, "game.potion.smash", { volume: 1 }], [DUR - 0.05, "game.player.hurt"],
      [DUR, "game.player.die"], [DUR, "@muffle", { hz: 400, s: 3 }]
    ];
    const loops = [[0.5, DUR + 0.2, "qf.scare.heartbeat", { volume: 0.5 }], [T_S1 + 0.3, DUR, "qf.scare.drone", { volume: 0.55, fadeIn: 1, pitch: 0.8 }], [T_S2 + 0.8, DUR, "qf.scare.breath", { volume: 0.4, fadeIn: 0.8 }]];

    function update(t, f) {
      const wz = witchZ(t);
      W.pivot.visible = t > T_OUT - 0.4;
      const camNow = cam(t);
      R.place(W, wx, 0, wz, R.yawTo(wx, wz, camNow.x, camNow.z), t > T_S2 + 0.5 ? -0.42 * sstep(T_S2 + 0.5, T_T3 - 0.4, t) : 0);
      W.anim(t, 0, { walk: t > T_OUT && t < T_T2 - 0.2 ? 0.6 : (t > T_S2 + 0.5 && t < T_T3 - 0.3 ? 0.5 : 0) });
      W.setOwn(0.02 + 0.06 * sstep(T_OUT, T_OUT + 1.2, t));
      for (const b of bottles) {
        const k = (t - b.t0) / (b.t1 - b.t0);
        b.q.visible = k >= 0 && k < 1;
        if (!b.q.visible) continue;
        const arc = Math.sin(k * Math.PI) * 0.9 * (b.t1 - b.t0);
        R.at(b.q, lerp(b.from[0], b.to[0], k), lerp(b.from[1], b.to[1], k) + arc, lerp(b.from[2], b.to[2], k));
        b.q.quaternion.copy(R.camera.quaternion); b.q.rotateZ(t * 14);
      }
      puffs(t);
      R.L(0, 0.8, 0.6, glow.position); glow.color.setHex(t < T_S2 ? 0xb040ff : 0xff2010);
      glow.intensity = 4 * pulse(t, [T_S1], 0.5) + 3 * pulse(t, [T_S2, DUR - 0.05], 0.3) + 0.9 * sstep(T_S1, T_S1 + 1, t);
      const n = sstep(T_S1 + 0.15, T_S1 + 0.9, t);
      f.env = { nausea: n * (0.75 + 0.25 * Math.sin(t * 1.3)), bake: 1 - 0.25 * sstep(0.2, 1.2, t), fogMul: 1 + 2.2 * n, fog: [0.16, 0.04, 0.16, 0.7 * n] };
      f.tints = [[90, 20, 110, 0.12 * n], [160, 0, 0, 0.25 * pulse(t, [T_S2], 0.5)]];
      f.vig = [40, 0, 50, 0.3 + 0.3 * n]; f.vigR = 0.85;
      f.hpMode = "normal";
      f.black = 0.45 * sstep(DUR - 0.1, DUR + 0.5, t);
    }
    return { dur: DUR, hits, cam, update, sounds, loops, deathSide: -1 };
  }
};
