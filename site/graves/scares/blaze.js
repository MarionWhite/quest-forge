// Blaze: heat. The air shimmers and embers rise; an orange glow grows round the bend, and with it the blaze's
// breathing. It rises into view wreathed in smoke. Three fireballs: the wall, the floor, you. You catch fire (the
// 1.7.10 burning overlay), the hotbar burns item by item, and the edges of the view char black.
import { track, clamp, lerp, sstep, pulse, tex, quad } from "./rig.js";
import { settle, shake, hitsOf, floorFall, particles, smoke, fireBlocks, mulberry } from "./common.js";

export default {
  death: "Steve was burnt to a crisp whilst fighting Blaze",
  async build(R) {
    const [partTex, ballTex] = await Promise.all([tex("particles"), tex("item_fireball")]);
    // It comes from ahead, round the side of the corridor (a passage or alcove if there is one).
    const op = R.openings.filter((o) => o.z > 2.5 && o.z < 9).sort((a, b) => a.z - b.z)[0];
    const bz = op ? op.z : clamp(R.ahead - 1.5, 3, 7), bxOut = op ? op.side * (op.wall + 1.2) : (R.wallR > R.wallL ? 1 : -1) * 2.5;
    const bx = clamp(bxOut * 0.25, -1.2, 1.2), by = 1.1;
    const B = R.mob("Blaze", { amb: [0.05, 0.05, 0.05], own: true });
    const T_HEAT = 0.9, T_BREATH = 1.7, T_RISE = 2.9, F = [3.7, 4.15, 4.6], DUR = 7.4;
    const wallX = (R.wallR > R.wallL ? -R.wallL : R.wallR) * 0.98;
    const target = [[wallX, 1.7, 0.4], [0.2, 0.05, 1.1], [0.0, 1.45, 0.05]];
    const hits = hitsOf([[F[2] + 0.18, 4, 1], [5.3, 3, -1], [5.95, 3, 1], [6.55, 3, -1], [DUR - 0.05, 4, 1]]);
    const balls = F.map((t0, i) => { const q = quad(ballTex, 0.32, 0.32, { alphaTest: 0.1, fog: false }); q.visible = false; R.add(q); return { q, t0, t1: t0 + 0.18, to: target[i] }; });
    const fires = await fireBlocks(R, [{ at: [target[1][0], 0, target[1][2]], t0: F[1] + 0.18 }, { at: [target[1][0] + 0.9, 0, target[1][2] + 0.5], t0: F[1] + 0.5, s: 0.8 }, { at: [0, 0, -0.1], t0: F[2] + 0.2, s: 0.9 }]);
    const r = mulberry(17);
    const embers = [];
    for (let i = 0; i < 28; i++) embers.push({ t0: T_HEAT + r() * 6, at: [bx + (r() - 0.5) * 2.5, r() * 0.6, bz - 1 + r() * 2.5], v: [(r() - 0.5) * 0.2, 0.6 + r() * 0.8, (r() - 0.5) * 0.2], life: 1.6 + r(), size: 0.035 + r() * 0.03, tile: 49, color: [1, 0.55, 0.2], grav: -0.1, fog: false, add: true });
    const puffs = particles(R, partTex, [...embers,
      ...[0, 1, 2, 3, 4, 5].flatMap((k) => smoke([bx, by + 0.6, bz], T_RISE - 0.3 + k * 0.6, 5, { spread: 0.7, window: 0.5, life: 1.5, size: 0.32, rise: 0.6, seed: 50 + k })),
      ...F.flatMap((t0, i) => smoke(target[i], t0 + 0.18, 8, { spread: 0.4, window: 0.2, life: 1.2, size: 0.35, rise: 0.7, seed: 60 + i })),
      ...[0, 1, 2, 3, 4, 5, 6].flatMap((k) => smoke([0, 0.9, 0.9], F[2] + 0.3 + k * 0.4, 2, { spread: 0.5, window: 0.3, life: 1, size: 0.18, rise: 1.2, seed: 70 + k, dark: 0.3 }))]);
    const glow = R.ownLight(R.light(0xff7a20, 0, 9, 1.3)), hit = R.ownLight(R.light(0xffa040, 0, 6, 1.4));

    const look = R.yawTo(0, 0, bx, bz);
    const yaw = track([[0, 0], [T_BREATH, 0], [T_RISE + 0.3, look], [F[0] + 0.05, look], [F[0] + 0.18, look + 0.3 * Math.sign(wallX), "x"], [F[1], look], [F[1] + 0.2, look - 0.1, "x"], [F[2], look]]);
    const pitch = track([[0, 0], [T_RISE + 0.3, R.pitchTo(0, R.eye, 0, bx, by + 0.8, bz) * 0.8], [F[1] + 0.15, 0.0], [F[1] + 0.3, -0.35, "x"], [F[2], -0.05]]);
    const cam = (t) => {
      const s = settle(R, t, 0.9);
      const k = sstep(0.8, 1.3, t);
      const c = { x: s.x * (1 - k), y: s.y, z: s.z * (1 - k), yaw: lerp(s.yaw, yaw(t), k), pitch: lerp(s.pitch, pitch(t), k), roll: 0, fov: s.fov };
      // Burning: you stagger back, then go down.
      const burn = sstep(F[2] + 0.2, F[2] + 1, t);
      c.z -= 0.5 * burn; c.yaw += burn * Math.sin(t * 2.3) * 0.25; c.roll += burn * Math.sin(t * 3.1) * 0.1;
      floorFall(c, t, 6.2, { d: 0.5, side: 1, roll: 1.1, y: 0.28, pitch: 0.2, back: 0.2 });
      return shake(c, t, 0.002 + 0.02 * pulse(t, F.map((x) => x + 0.18), 0.2) + 0.01 * burn, 8);
    };
    const sounds = [
      [T_HEAT, "fire.fire", { at: [bxOut, 1, bz], volume: 0.5 }],
      [T_BREATH, "mob.blaze.breathe", { at: [bxOut, 1.5, bz], volume: 0.8 }], [T_BREATH + 1.1, "mob.blaze.breathe", { at: [(bx + bxOut) / 2, 1.5, bz], volume: 1 }],
      [T_RISE, "mob.blaze.breathe", { at: [bx, by + 0.8, bz], volume: 1, pitch: 0.85 }], [T_RISE + 0.05, "qf.scare.stinger", { volume: 0.5 }],
      ...F.map((t0) => [t0, "mob.ghast.fireball", { at: [bx, by + 0.8, bz], volume: 1 }]),
      ...F.map((t0, i) => [t0 + 0.18, i === 2 ? "fire.ignite" : "random.fizz", { at: target[i], volume: 1 }]),
      [F[2] + 0.2, "qf.scare.hit", { volume: 0.9 }], [F[2] + 0.25, "fire.fire", { volume: 1 }],
      ...hits.map((h) => [h.t, "game.player.hurt"]), [F[2] + 0.5, "qf.scare.scream", { volume: 1 }], [5.9, "qf.scare.scream", { volume: 0.8, pitch: 0.85 }],
      [6.7, "mob.blaze.breathe", { at: [bx, by + 0.8, bz - 1], volume: 1 }],
      [DUR, "game.player.die"], [DUR, "@muffle", { hz: 500, s: 2.5 }]
    ];
    const loops = [[0.5, DUR + 0.2, "qf.scare.heartbeat", { volume: 0.45 }], [F[2] + 0.2, DUR + 0.5, "fire.fire", { volume: 0.9, fadeIn: 0.2 }], [T_HEAT, F[2], "qf.scare.drone", { volume: 0.45, fadeIn: 1.5, fadeOut: 0.1 }]];

    function update(t, f) {
      // It slides out from the side and rises into the corridor.
      const out = sstep(T_RISE - 0.5, T_RISE + 0.4, t), rise = sstep(T_RISE - 0.2, T_RISE + 0.6, t);
      B.pivot.visible = t > T_RISE - 0.6;
      const x = lerp(bxOut, bx, out), y = lerp(0.2, by, rise) + Math.sin(t * 2.2) * 0.08, z = bz - 0.6 * sstep(F[2] + 0.5, DUR, t);
      R.place(B, x, y, z, R.yawTo(x, z, 0, 0));
      B.anim(t, 0, {});
      B.setOwn(0.6 + 0.4 * pulse(t, F, 0.25));
      R.L(lerp(bxOut * 1.2, bx, out), y + 0.9, z - 0.2, glow.position);
      glow.intensity = 2.5 * sstep(T_HEAT, T_RISE, t) + 2.5 * rise + 4 * pulse(t, F, 0.2);
      for (const b of balls) {
        const k = (t - b.t0) / (b.t1 - b.t0);
        b.q.visible = k >= 0 && k < 1;
        if (b.q.visible) { R.at(b.q, lerp(x, b.to[0], k), lerp(y + 0.9, b.to[1], k), lerp(z, b.to[2], k)); b.q.quaternion.copy(R.camera.quaternion); }
      }
      const hb = balls.map((b) => [b, pulse(t, [b.t1], 0.25)]).sort((p, q) => q[1] - p[1])[0];
      if (hb[1] > 0.01) { R.L(hb[0].to[0] * 0.9, hb[0].to[1] + 0.2, hb[0].to[2], hit.position); hit.intensity = 9 * hb[1]; } else hit.intensity = 0;
      fires(t); puffs(t);
      const heat = sstep(T_HEAT, T_RISE, t), burn = sstep(F[2] + 0.18, F[2] + 0.4, t);
      f.env = { nausea: 0.12 * heat + 0.15 * burn, bake: 1 - 0.2 * sstep(0.2, 1.2, t), fogMul: 1 + 0.6 * heat, fog: [0.12, 0.05, 0.02, 0.5 * heat] };
      f.tints = [[255, 110, 30, 0.05 * heat + 0.12 * burn]];
      f.vig = [40, 10, 0, 0.3 + 0.25 * heat]; f.vigR = 0.9;
      f.fire = burn;
      f.burnt = [0, 1, 2, 3, 4].map((i) => t > F[2] + 0.7 + i * 0.4);
      f.char = 0.62 * sstep(F[2] + 0.8, DUR, t);
    }
    return { dur: DUR, hits, cam, update, sounds, loops, deathSide: 1 };
  }
};
