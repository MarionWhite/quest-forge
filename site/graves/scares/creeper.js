// Creeper: the look-back. A hiss right behind you. The head turns, slowly, and time slows with it: its face fills the
// view, flashing white and swelling. White-out, ringing, the world muffled. From the floor you see the crater it
// blew in the real floor and your hotbar scattering across it. Half a heart. Then, by your ear, a second hiss.
import { THREE, track, clamp, lerp, sstep, pulse, tex } from "./rig.js";
import { settle, shake, hitsOf, explosionFX, droppedItems, particles, smoke } from "./common.js";

export default {
  death: "Steve was blown up by Creeper",
  async build(R) {
    const [boomTex, partTex, ...itemTex] = await Promise.all(["explosion", "particles", "item_iron_sword", "item_stone_pickaxe", "k:torch_on", "item_bread", "item_apple"].map((n) => tex(n)));
    // It stands behind you; if the corridor is short behind, it is at your shoulder instead.
    const cz = R.behind > 1.5 ? -0.74 : -0.3, cx = R.behind > 1.5 ? 0.05 : (R.wallR > R.wallL ? 0.55 : -0.55);
    const side = R.wallR > R.wallL ? -1 : 1;           // the way the head turns (toward the roomier side)
    const T_HISS = 1.25, T_TURN = 1.55, T_FACE = 3.2, T_BOOM = 4.0, T_HISS2 = 6.75, DUR = 7.75;
    const back = Math.PI * side * 0.97;
    const c1 = R.mob("Creeper", { amb: [0.03, 0.03, 0.03], own: true });
    const c2 = R.mob("Creeper", { amb: [0.03, 0.03, 0.03], own: true });
    // Where the blast throws you: forward and down, onto your side, looking back at the crater.
    const land = [clamp(0.35 * -side, -R.wallL + 0.6, R.wallR - 0.6), 0.42, Math.min(2.2, R.ahead - 0.6)];
    const c2at = [land[0] + 0.85 * side, land[2] + 0.5];
    const boom = explosionFX(R, T_BOOM, [cx, 0.9, cz], boomTex, { n: 16, spread: 1.6, seed: 5 });
    const items = droppedItems(R, T_BOOM + 0.06, [0, 1.0, 0.2], itemTex, { seed: 13, speed: 3.6 });
    const glow = R.ownLight(R.light(0xffffff, 0, 5, 1.2));

    const hits = hitsOf([[T_BOOM, 17, side], [DUR - 0.05, 3, -side]]);
    // The turn: slow, slower as it comes round (time slows); the field narrows on the face.
    const yaw = track([[0, 0], [T_TURN, 0], [T_TURN + 0.5, back * 0.25, "i"], [T_FACE, back * 0.93, "s"], [T_BOOM, back, "l"]]);
    const fov = track([[0, R.start.fov], [T_FACE - 0.6, R.start.fov], [T_BOOM - 0.02, R.start.fov - 16, "s"], [T_BOOM, R.start.fov + 10, "x"], [T_BOOM + 1.2, R.start.fov + 4], [T_HISS2 + 0.6, R.start.fov - 8], [DUR, R.start.fov - 12]]);
    const camAlive = (t) => {
      const s = settle(R, t, 0.9);
      const k = sstep(0.8, 1.3, t);
      const c = { x: s.x * (1 - k), y: s.y, z: s.z * (1 - k), yaw: lerp(s.yaw, yaw(t), k), pitch: lerp(s.pitch, -0.12 * sstep(T_TURN, T_FACE, t), k), roll: 0, fov: fov(t) };
      return shake(c, t, 0.0015 + 0.004 * sstep(T_TURN, T_BOOM, t), 2);
    };
    const cam = (t) => {
      if (t < T_BOOM) return camAlive(t);
      // Thrown: a tumble through the air, then on the floor on your side, facing the crater.
      const a = camAlive(T_BOOM - 0.001), k = clamp((t - T_BOOM) / 0.55), e = 1 - Math.pow(1 - k, 2);
      const arc = Math.sin(k * Math.PI) * 0.45;
      const c = { x: lerp(a.x, land[0], e), y: lerp(a.y, land[1], k * k) + arc, z: lerp(a.z, land[2], e), yaw: a.yaw + 0.7 * side * Math.sin(k * Math.PI) + (back * 0.0), pitch: lerp(a.pitch, -0.32, e) + Math.sin(k * Math.PI) * 0.6, roll: lerp(0, 1.05 * side, e), fov: fov(t) };
      const bounce = k >= 1 ? Math.exp(-(t - T_BOOM - 0.55) * 8) * Math.sin((t - T_BOOM - 0.55) * 28) * 0.03 : 0;
      c.y += bounce;
      // Lying there, the head lolls toward the second hiss.
      const lk = sstep(T_HISS2 + 0.1, T_HISS2 + 0.9, t);
      c.yaw = lerp(c.yaw, R.yawTo(c.x, c.z, c2at[0], c2at[1]), lk); c.pitch = lerp(c.pitch, 0.12, lk);
      return shake(c, t, 0.004 * (1 - sstep(T_BOOM + 0.6, T_BOOM + 2, t)) + 0.0025, 4);
    };

    // The crater: the real floor goes, in rough layers, where it stood.
    const crater = () => {
      const zc = Math.round(cz), xc = Math.round(cx);
      R.carveL([
        [[xc - 2, -1, zc - 1], [xc + 2, -1, zc + 1]], [[xc - 1, -1, zc - 2], [xc + 1, -1, zc + 2]],
        [[xc - 1, -2, zc - 1], [xc + 1, -2, zc + 1]], [[xc, -3, zc], [xc, -3, zc]]
      ]);
    };
    R.burst(T_BOOM, [cx, 0.3, cz], 40, R.floorBlock === "gravel" ? "dust" : "stone", { dir: [0, 2.2, 0], speed: 4.5, spread: 1.4, size: 0.12, life: 1.6, stick: 4 });
    R.burst(T_BOOM, [cx, 0.8, cz], 30, "green", { dir: [0, 1.2, 0], speed: 4, spread: 1.6, size: 0.09, life: 1.4, stick: 4 });
    const puffs = particles(R, partTex, [...smoke([cx, 0.2, cz], T_BOOM + 0.1, 24, { spread: 2.2, window: 1.0, life: 2.2, size: 0.5, rise: 0.9, seed: 7 }),
      ...smoke([cx, -0.6, cz], T_BOOM + 1.3, 14, { spread: 1.2, window: 4, life: 2.4, size: 0.35, rise: 0.6, seed: 8 })]);

    const sounds = [
      [T_HISS, "creeper.primed", { at: [cx, 1.2, cz], volume: 1 }],
      [T_HISS + 0.05, "qf.scare.stinger", { volume: 0.35 }],
      [T_TURN + 0.2, "mob.creeper.say", { at: [cx, 1.2, cz], volume: 0.5, pitch: 0.6 }],
      [T_BOOM, "random.explode", { at: [cx, 1, cz], volume: 1, pitch: 0.75 }],
      [T_BOOM + 0.01, "qf.scare.hit", { volume: 1 }],
      [T_BOOM, "game.player.hurt"],
      [T_BOOM + 0.02, "@muffle", { hz: 260, s: 5.5 }],
      [T_BOOM + 0.55, "game.player.hurt.fall.big", { volume: 0.7 }],
      [T_BOOM + 0.7, "dig.stone", { at: [cx, 0, cz], volume: 0.5, pitch: 0.7 }],
      [T_HISS2, "creeper.primed", { at: [c2at[0], 0.9, c2at[1]], volume: 1, pitch: 0.92 }],
      [T_HISS2 + 0.3, "qf.scare.whisper", { volume: 0.3 }],
      [DUR - 0.05, "random.explode", { volume: 1, pitch: 0.65 }], [DUR - 0.04, "qf.scare.hit", { volume: 1 }],
      [DUR, "game.player.die"]
    ];
    const loops = [
      [0.5, T_BOOM, "qf.scare.heartbeat", { volume: 0.55, fadeOut: 0.05 }],
      [T_TURN, T_BOOM, "qf.scare.drone", { volume: 0.5, fadeIn: 1.4, fadeOut: 0.05 }],
      [T_BOOM + 0.05, DUR + 1, "qf.scare.ringing", { volume: 0.55, fadeIn: 0.1, fadeOut: 2 }],
      [T_BOOM + 1.6, DUR, "qf.scare.breath", { volume: 0.35, fadeIn: 1.5, fadeOut: 0.1 }],
      [T_BOOM + 1.6, DUR, "qf.scare.heartbeat", { volume: 0.3, fadeIn: 1.0, pitch: 0.8 }]
    ];

    function creeperAt(m, t, x, z, swell, flash) {
      m.anim(t, 0, { walk: 0, hiss: swell });
      R.place(m, x, 0, z, R.yawTo(x, z, 0, 0));
      // RenderCreeper: a white overlay on every other tenth of the fuse, stronger as it nears the end.
      const on = Math.floor(flash * 10) % 2 === 0 && flash > 0.05;
      m.setOwn(0.035 + (on ? 0.25 + flash * 0.9 : 0));
    }
    function update(t, f) {
      // The first creeper: right behind the head the whole time; gone in the blast.
      c1.pivot.visible = t < T_BOOM;
      const fuse = clamp((t - T_HISS) / (T_BOOM - T_HISS));
      if (c1.pivot.visible) creeperAt(c1, t, cx, cz, Math.pow(fuse, 1.5), fuse);
      c2.pivot.visible = t > T_HISS2 - 0.4 && t < DUR;
      if (c2.pivot.visible) { const f2 = clamp((t - T_HISS2) / (DUR - T_HISS2)); creeperAt(c2, t, c2at[0], c2at[1], Math.pow(f2, 1.5), f2); c2.pivot.rotation.y = R.yaw0 + R.yawTo(c2at[0], c2at[1], land[0], land[2]); }
      if (t >= T_BOOM) R.once("crater", crater);
      boom(t); items(t); puffs(t);
      R.L(cx, 1.4, cz + 0.6, glow.position); glow.intensity = 9 * pulse(t, [T_BOOM], 0.18);
      // The blast: white, slow to clear; the room still dim after.
      f.white = t >= T_BOOM ? 1 - sstep(T_BOOM + 0.15, T_BOOM + 1.6, t) : 0;
      if (t >= DUR - 0.06) f.white = 1 - sstep(DUR + 0.15, DUR + 1.1, t);
      f.gone = t >= T_BOOM + 0.06 ? [true, true, true, true, true] : null;
      f.env = { bake: 1 - 0.2 * sstep(0.2, 1, t) - 0.15 * sstep(T_BOOM, T_BOOM + 1, t), fogMul: 1 + 0.5 * sstep(1, 3, t) + 1.2 * sstep(T_BOOM, T_BOOM + 0.5, t) * (1 - 0.6 * sstep(T_BOOM + 0.5, T_BOOM + 3, t)) };
      f.vig = [0, 0, 0, 0.3 * sstep(T_TURN, T_FACE, t) + 0.35 * sstep(T_BOOM + 1, T_BOOM + 2, t)];
      f.tints = [[200, 210, 255, 0.06 * sstep(T_TURN, T_BOOM, t) * (t < T_BOOM ? 1 : 0)]];   // the cold, held moment
    }
    return { dur: DUR, hits, cam, update, sounds, loops, deathSide: side, notes: { side, cz, get crater() { return [R.block(cx, -0.5, cz), R.block(cx, -1.5, cz), R.block(cx + 2, -0.5, cz), R.carved]; } } };
  }
};
