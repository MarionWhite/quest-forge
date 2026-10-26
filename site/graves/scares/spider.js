// Spider: the ceiling drop. Clicking overhead. The head tilts up, slowly, to two red eyes on the ceiling. It drops onto
// your face, its legs wrapping the edges of the view, and bites. Then you are hauled up into the dark and left
// dangling over the corridor, turning slowly on the thread.
import { track, clamp, lerp, sstep, pulse, tex, quad } from "./rig.js";
import { settle, shake, hitsOf, lensLimbs } from "./common.js";

export default {
  death: "Steve was slain by Spider",
  async build(R) {
    const webTex = await tex("web");
    const ceil = R.ceil > 7 ? 4.5 : R.ceil;                 // under a sky crack it waits on the rim
    const sz = 1.9, sx = 0.1;                                 // ahead of the head, upside down, head dipped toward you
    const sp = R.mob("Spider", { amb: [0.02, 0.02, 0.02], own: true });
    const legDonor = R.mob("Spider"); legDonor.pivot.visible = false;
    const T_CLICK = 1.0, T_UP = 2.0, T_EYES = 3.2, T_DROP = 3.95, T_HAUL = 5.5, DUR = 7.7;
    const hang = Math.max(2.3, ceil - 0.45);
    const hits = hitsOf([[T_DROP + 0.28, 4, 1], [T_DROP + 0.8, 4, -1], [T_DROP + 1.3, 3, 1], [6.6, 4, -1], [DUR - 0.1, 5, 1]]);
    const upP = R.pitchTo(0, R.eye, 0, sx, ceil - 0.3, sz);
    const pitch = track([[0, 0], [T_UP, -0.02], [T_EYES, upP, "s"], [T_DROP, upP], [T_DROP + 0.18, 0.2, "x"], [T_HAUL, 0.12], [T_HAUL + 0.9, -1.05, "i"], [DUR, -1.25]]);
    const eyeY = track([[0, R.eye], [T_DROP + 0.1, R.eye], [T_DROP + 0.4, R.eye - 0.15], [T_HAUL, R.eye - 0.1], [T_HAUL + 1.1, hang, "i"], [DUR, hang + 0.08]]);
    const back = track([[0, 0], [T_DROP + 0.1, 0], [T_DROP + 0.5, -0.4, "o"], [T_HAUL, -0.55], [T_HAUL + 1.1, -0.2]]);
    const cam = (t) => {
      const s = settle(R, t, 0.9);
      const k = sstep(0.8, 1.3, t);
      const c = { x: s.x * (1 - k), y: lerp(s.y, eyeY(t), k), z: lerp(s.z, back(t), k), yaw: s.yaw * (1 - k), pitch: lerp(s.pitch, pitch(t), k), roll: 0, fov: s.fov };
      // Dangling: a slow turn on the thread and a pendulum sway.
      const d = sstep(T_HAUL + 0.4, T_HAUL + 1.4, t);
      c.yaw += d * (t - T_HAUL) * 0.55; c.roll += d * Math.sin((t - T_HAUL) * 2.1) * 0.12; c.x += d * Math.sin((t - T_HAUL) * 2.1) * 0.12;
      c.fov = s.fov + 8 * sstep(T_HAUL, T_HAUL + 1, t);
      return shake(c, t, 0.002 + 0.03 * sstep(T_DROP + 0.1, T_DROP + 0.2, t) * (1 - sstep(T_DROP + 0.3, T_HAUL, t) * 0.6) + 0.02 * pulse(t, hits.map((h) => h.t), 0.2), 6);
    };
    // Its legs around the edges of the view once it is on your face.
    const L = (fx, fy, tx, ty, t0, ph) => ({ from: [fx, fy], to: [tx, ty], t0, t1: t0 + 0.22, z: -0.26, scale: 0.42, axis: "x-", twist: 0.12, ph, curl: 0.25 * Math.sign(fx) });
    const legs = lensLimbs(R, legDonor, "spiderLeg1", [
      L(-0.62, 0.22, -0.2, 0.12, T_DROP + 0.12, 0), L(-0.62, -0.05, -0.22, -0.02, T_DROP + 0.14, 1), L(-0.6, -0.3, -0.2, -0.16, T_DROP + 0.16, 2),
      L(0.62, 0.24, 0.2, 0.13, T_DROP + 0.13, 3), L(0.62, -0.04, 0.23, -0.01, T_DROP + 0.15, 4), L(0.6, -0.3, 0.2, -0.15, T_DROP + 0.17, 5)
    ], { color: 0x5a5050 });
    // Web strands in front of the lens while you hang.
    const webs = [[-0.22, 0.12, 0.3], [0.2, -0.1, -0.4], [0.05, 0.16, 1.1], [-0.15, -0.14, 2]].map(([x, y, r], i) => {
      const q = quad(webTex, 0.17, 0.17, { transparent: true, opacity: 0.0, depthTest: false, fog: false, color: 0x4a4a4a });
      q.material.depthWrite = false; q.renderOrder = 2100; q.position.set(x, y, -0.22); q.rotation.z = r; R.view.add(q); return { q, i };
    });
    const sounds = [
      [T_CLICK, "mob.spider.step", { at: [sx, ceil, sz + 1.2], volume: 0.6 }], [T_CLICK + 0.45, "mob.spider.step", { at: [sx, ceil, sz + 0.6], volume: 0.6 }],
      [T_CLICK + 0.9, "mob.spider.step", { at: [sx, ceil, sz], volume: 0.55 }],
      [T_UP + 0.3, "mob.spider.say", { at: [sx, ceil - 0.4, sz], volume: 0.5, pitch: 0.8 }],
      [T_EYES + 0.25, "qf.scare.whisper", { volume: 0.25 }],
      [T_DROP, "mob.spider.say", { at: [sx, ceil - 0.6, sz], volume: 1, pitch: 0.9 }],
      [T_DROP + 0.08, "qf.scare.shriek", { volume: 0.8 }], [T_DROP + 0.1, "qf.scare.hit", { volume: 0.9 }], [T_DROP + 0.12, "qf.scare.stinger", { volume: 0.6 }],
      ...hits.flatMap((h, i) => [[h.t, "game.player.hurt"], [h.t + 0.02, i % 2 ? "qf.scare.gore" : "qf.scare.crunch", { volume: 0.85 }], [h.t - 0.05, "mob.spider.say", { volume: 0.6, pitch: 1.1 }]]),
      [T_HAUL + 0.05, "qf.scare.scream", { volume: 0.9 }], [T_HAUL + 0.1, "dig.cloth", { volume: 0.8, pitch: 0.6 }],
      [T_HAUL + 1.4, "mob.spider.step", { volume: 0.5 }], [T_HAUL + 1.9, "mob.spider.step", { volume: 0.5 }],
      [DUR, "game.player.die"], [DUR, "@muffle", { hz: 380, s: 3 }]
    ];
    const loops = [[0.6, DUR + 0.2, "qf.scare.heartbeat", { volume: 0.5 }], [T_HAUL + 0.6, DUR, "qf.scare.breath", { volume: 0.5, fadeIn: 0.6 }], [T_UP, T_DROP, "qf.scare.drone", { volume: 0.4, fadeIn: 1.2, fadeOut: 0.05 }]];
    hits.forEach((h, i) => R.burst(h.t, i < 3 ? [0, 1.35, 0.25] : [0, hang - 0.25, 0], 24, "blood", { dir: i < 3 ? [0, 0.5, 0.8] : [0, -0.2, 0], speed: 1.8, spread: 0.6, size: 0.045, life: 1.8, stick: 3 }));
    // Drips from you to the floor while you hang.
    for (let k = 0; k < 7; k++) R.burst(T_HAUL + 1.0 + k * 0.28, [0.02 * (k % 3), hang - 0.4, 0.02], 2, "blood", { dir: [0, -1, 0], speed: 0.3, spread: 0.05, size: 0.035, life: 1.6, stick: 4 });

    function update(t, f) {
      // On the ceiling, upside down, until it drops; then on your face; then above you, out of sight.
      const camNow = cam(t);
      if (t < T_DROP) {
        R.place(sp, sx, ceil, sz, R.yawTo(sx, sz, 0, 0) + 0.1 * Math.sin(t * 0.7), -0.45, Math.PI);
        sp.anim(t, 0, { walk: t > T_CLICK && t < T_UP + 0.5 ? 0.6 : 0.05 });
      } else {
        const k = clamp((t - T_DROP) / 0.2), e = k * k;
        const tx = camNow.x, ty = camNow.y - 0.5, tz = camNow.z + 1.12 - 0.08 * pulse(t, hits.slice(0, 3).map((h) => h.t - 0.05), 0.1);
        R.place(sp, lerp(sx, tx, e), lerp(ceil - 0.2, ty, e), lerp(sz, tz, e), R.yawTo(sx, sz, 0, 0), lerp(-0.45, -0.22, k), lerp(Math.PI, 0, k));
        sp.anim(t * 3, 0, { walk: 2 });
        sp.pivot.visible = t < T_HAUL + 0.25;
      }
      sp.setOwn(0.015 + 0.06 * sstep(T_DROP, T_DROP + 0.2, t) * (1 - sstep(T_HAUL, T_HAUL + 0.3, t)));
      legs(t);
      const w = sstep(T_HAUL + 0.3, T_HAUL + 1.4, t);
      for (const { q, i } of webs) q.material.opacity = 0.5 * w * sstep(T_HAUL + 0.3 + i * 0.15, T_HAUL + 0.8 + i * 0.15, t);
      f.env = { bake: 1 - 0.3 * sstep(0.3, 1.5, t) - 0.25 * sstep(T_UP, T_EYES, t) - 0.25 * w, lights: 1 - 0.35 * sstep(T_UP, T_EYES, t), fogMul: 1 + 0.8 * sstep(1, 3, t) };
      f.vig = [0, 0, 0, 0.3 + 0.3 * sstep(T_UP, T_EYES, t) + 0.25 * w]; f.vigR = 0.85;
      f.splats = hits.slice(0, 3).filter((h) => t >= h.t).map((h, i) => ({ t0: h.t, x: [0.4, 0.62, 0.5][i], y: [0.5, 0.38, 0.6][i], r: 13 + i * 3, seed: 41 + i }));
      f.black = 0.6 * sstep(DUR - 0.3, DUR + 0.4, t);
    }
    return { dur: DUR, hits, cam, update, sounds, loops, deathSide: 1 };
  }
};
