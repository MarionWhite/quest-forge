// Magma Cube: behind you. Thump. Thump. Closer, behind, each one shaking the floor. Then nothing. The head turns,
// slowly: the corridor behind is empty. A glow grows on the floor around your feet, from above. The view snaps up
// into its underside, and it lands: the screen squashes flat in a lava glow, again, and again.
import { track, clamp, lerp, sstep, pulse, tex } from "./rig.js";
import { settle, shake, hitsOf, particles, mulberry } from "./common.js";

export default {
  death: "Steve was slain by Magma Cube",
  async build(R) {
    const partTex = await tex("particles");
    const size = R.ceil >= 5 ? 3 : 2, half = size * 0.25;   // a size-3 cube is a block and a half across
    const M = R.mob("LavaSlime", { size, amb: [0.04, 0.04, 0.04], own: true });
    const behind = Math.min(R.behind - half - 0.3, 8);
    const hops = [{ t: 1.2, z: -behind }, { t: 1.95, z: -behind * 0.62 }, { t: 2.65, z: -Math.max(half + 0.6, behind * 0.32) }];
    const T_JUMP = 2.95, T_LOOK = 3.2, T_OVER = 3.95, T_WHIP = 4.12, T_LEAP = 4.62, T_LAND = 4.84, DUR = 6.75;
    const zIn = clamp(R.ahead - half - 0.4, 1.6, 2.4);   // where it lands in front of you, behind your turned head
    const apex = Math.max(R.eye + 0.35, Math.min(R.ceil - size * 0.5 - 0.05, 3.0));
    const slams = [T_LAND, 5.6, 6.35];
    const hits = hitsOf([[slams[0], 10, 1], [slams[1], 6, -1], [slams[2], 4, 1]]);
    const back = Math.PI * (R.wallL > R.wallR ? 1 : -1) * 0.94;
    const yaw = track([[0, 0], [T_LOOK, 0], [T_OVER, back, "s"], [T_WHIP, back], [T_WHIP + 0.24, 0.05, "x"]]);
    const pitch = track([[0, 0], [T_LOOK, 0.0], [T_OVER, -0.22], [T_WHIP, -0.2], [T_WHIP + 0.24, -0.12, "x"], [T_LEAP, -0.1], [T_LAND, 0.55, "o"]]);
    const cam = (t) => {
      const s = settle(R, t, 0.9);
      const k = sstep(0.8, 1.3, t);
      const c = { x: s.x * (1 - k), y: s.y, z: s.z * (1 - k), yaw: lerp(s.yaw, yaw(t), k), pitch: lerp(s.pitch, pitch(t), k), roll: 0, fov: s.fov };
      // Crushed: down to the floor under it, the view knocked about by each slam.
      const cr = sstep(T_LAND - 0.02, T_LAND + 0.12, t);
      c.y = lerp(c.y, 0.35, cr); c.pitch = lerp(c.pitch, 0.25, cr); c.roll += cr * 0.5;
      return shake(c, t, 0.002 + 0.024 * pulse(t, [...hops.map((h) => h.t), T_OVER], 0.18) + 0.05 * pulse(t, slams, 0.15), 9);
    };
    // Where it is: hopping up behind you, the long jump over your head while you turn, in front, then onto you.
    const pos = (t) => {
      let z = -behind - 2, y = 0;
      for (let i = 0; i < hops.length; i++) {
        const h = hops[i], prevZ = i ? hops[i - 1].z : -behind - 1.2, d = 0.45;
        if (t >= h.t - d && t < h.t) { const k = (t - (h.t - d)) / d; z = lerp(prevZ, h.z, k); y = Math.sin(k * Math.PI) * 1.1; }
        else if (t >= h.t) { z = h.z; y = 0; }
      }
      if (t >= T_JUMP) { const k = clamp((t - T_JUMP) / (T_OVER - T_JUMP)); z = lerp(hops[2].z, zIn, k); y = Math.sin(k * Math.PI) * apex; }
      if (t >= T_LEAP) { const k = clamp((t - T_LEAP) / (T_LAND - T_LEAP)); z = lerp(zIn, 0.0, k); y = Math.sin(k * Math.PI) * 0.9; }
      if (t >= T_LAND) {
        z = 0; y = 0;
        for (const sl of slams.slice(1)) if (t > sl - 0.35 && t < sl) y = Math.sin((t - sl + 0.35) / 0.35 * Math.PI) * 0.6;
      }
      return { x: 0.05, y, z };
    };
    const r = mulberry(31);
    const lava = [];
    for (const [tt, lz] of [...hops.map((h) => [h.t, h.z]), [T_OVER, zIn], ...slams.map((x) => [x, 0])]) for (let i = 0; i < 8; i++) lava.push({ t0: tt + r() * 0.05, at: [(r() - 0.5) * 1.2, 0.2, lz + (r() - 0.5) * 1.2], v: [(r() - 0.5) * 1.5, 1.5 + r(), (r() - 0.5) * 1.5], life: 0.9, size: 0.09, tile: 49, color: [1, 0.6, 0.25], grav: 6, fog: false, add: true });
    const sparks = particles(R, partTex, lava);
    const glow = R.ownLight(R.light(0xff5a10, 0, 7, 1.3));
    const sounds = [
      ...hops.map((h, i) => [h.t, "mob.magmacube.big", { at: [0, 0.3, h.z], volume: 0.55 + i * 0.2, pitch: 0.8 }]),
      [hops[2].t + 0.05, "qf.scare.whisper", { volume: 0.3 }],
      [T_JUMP + 0.05, "mob.magmacube.jump", { at: [0, 1, hops[2].z], volume: 0.5, pitch: 0.7 }],
      [T_OVER, "mob.magmacube.big", { at: [0, 0.3, zIn], volume: 1, pitch: 0.7 }],
      [T_WHIP + 0.18, "qf.scare.stinger", { volume: 0.9 }], [T_WHIP + 0.2, "qf.scare.shriek", { volume: 0.6 }],
      [T_LEAP, "mob.magmacube.jump", { at: [0, 1, zIn], volume: 1, pitch: 0.8 }],
      ...slams.map((tt) => [tt, "mob.magmacube.big", { volume: 1, pitch: 0.65 }]),
      ...slams.map((tt) => [tt + 0.01, "qf.scare.crunch", { volume: 1 }]), [T_LAND + 0.02, "qf.scare.hit", { volume: 1 }],
      ...hits.map((h) => [h.t, "game.player.hurt"]), [T_LAND + 0.25, "qf.scare.scream", { volume: 0.8, pitch: 0.8 }],
      [T_LAND + 0.1, "@muffle", { hz: 300, s: 4 }], [T_LAND, "liquid.lavapop", { volume: 0.8 }], [5.9, "liquid.lava", { volume: 0.7 }],
      [DUR, "game.player.die"]
    ];
    const loops = [[0.5, DUR + 0.2, "qf.scare.heartbeat", { volume: 0.55 }], [T_JUMP, T_WHIP + 0.2, "qf.scare.drone", { volume: 0.5, fadeIn: 0.8, fadeOut: 0.05 }]];
    function update(t, f) {
      const p = pos(t);
      R.place(M, p.x, p.y, p.z, 0);
      // The squish: flattened as it lands, stretched as it leaves the ground (EntityMagmaCube's squishFactor).
      const land = Math.max(...[...hops.map((h) => h.t), T_OVER, ...slams].map((tt) => pulse(t, [tt], 0.14)));
      const sq = -0.22 * land + (p.y > 0.1 ? 0.18 : 0);
      M.anim(Math.asin(clamp(sq / 0.22, -1, 1)) / 4, 0, {});
      M.setOwn(t < T_LAND ? 0.95 : 0.3 + 0.3 * land);   // EntityMagmaCube is fullbright
      sparks(t);
      R.L(p.x, p.y + 0.2, p.z, glow.position);
      glow.intensity = 2.5 + 5 * land + 2 * sstep(T_OVER, T_LAND, t);
      const crushed = sstep(T_LAND - 0.02, T_LAND + 0.08, t);
      f.env = { squash: Math.min(1, crushed * 0.75 + 0.35 * Math.max(...slams.map((tt) => pulse(t, [tt], 0.18)))), bake: 1 - 0.25 * sstep(0.2, 1.2, t), fogMul: 1 + 0.5 * sstep(1, 3, t) };
      f.tints = [[255, 90, 10, 0.08 * sstep(T_WHIP, T_LAND, t) + 0.2 * crushed]];
      f.vig = [60, 10, 0, 0.3 + 0.45 * crushed]; f.vigR = 0.85;
      f.black = 0.3 * sstep(DUR - 0.2, DUR + 0.6, t);
    }
    return { dur: DUR, hits, cam, update, sounds, loops, deathSide: 1, notes: { size, apex } };
  }
};
