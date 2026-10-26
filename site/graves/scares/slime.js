// Slime (piston trap): the floor goes and you drop into a dark pit, into a skin of green slime water. Quiet. Up in
// the hole, the light goes out: something square is squeezing through it. It drops, lands in front of you in a
// green splash, face to face, wobbles, and hops onto you. Inside it the world is green and far away, the sound goes
// thick, the air runs out, and it squeezes. Small slimes bud off it and hop away.
import { THREE, clamp, lerp, sstep, pulse, tex, loadImg, easeOut } from "./rig.js";
import { settle, shake, hitsOf, particles, mulberry } from "./common.js";
import { pistonTrap, GRAV } from "./piston.js";

export default {
  death: "Steve was slain by Slime",
  async build(R) {
    const partTex = await tex("particles");
    const r = mulberry(R.seed * 13 + 9);
    const trap = await pistonTrap(R, { click: 1.1, open: 1.8, D: 7, ri: 3, rk: 3 });
    const { roomBox: rb, loc, hole } = trap;
    const Dp = trap.D, y0 = -Dp;
    // The slime water on the pit floor: water_still's first frame, tinted, translucent.
    const img = await loadImg("k:water_still");
    const c = document.createElement("canvas"); c.width = c.height = 16;
    if (img) c.getContext("2d").drawImage(img, 0, 0, 16, 16, 0, 0, 16, 16);
    const wt = new THREE.CanvasTexture(c); wt.colorSpace = THREE.SRGBColorSpace; wt.magFilter = wt.minFilter = THREE.NearestFilter; wt.generateMipmaps = false; wt.wrapS = wt.wrapT = THREE.RepeatWrapping;
    const p0 = loc(rb.i0, -Dp, rb.k0), p1 = loc(rb.i1, -Dp, rb.k1);
    const w = Math.abs(p1.x - p0.x) + 1, l = Math.abs(p1.z - p0.z) + 1;
    wt.repeat.set(w, l);
    const pool = new THREE.Mesh(new THREE.PlaneGeometry(w, l), new THREE.MeshBasicMaterial({ map: wt, color: 0x4f9a36, transparent: true, opacity: 0.8, depthWrite: false }));
    pool.rotation.set(-Math.PI / 2, 0, -R.yaw0);
    R.at(pool, (p0.x + p1.x) / 2, y0 + 0.14, (p0.z + p1.z) / 2); pool.visible = false; R.add(pool);

    // The slime: size 4 (two blocks across), the library's inner core and translucent outer.
    const SIZE = 4, half = SIZE * 0.25;
    const S = R.mob("Slime", { size: SIZE, amb: [0.06, 0.09, 0.05] });
    const small = [0, 1, 2].map(() => R.mob("Slime", { size: 1, amb: [0.08, 0.12, 0.07] }));
    const T_DARK = 3.05, T_DROP = 3.7, me = { x: hole.x, z: hole.z };
    const farZ = loc(rb.i0, -Dp, rb.k1).z + 0.5;   // the pit's far wall
    const front = { x: me.x + 0.1, z: me.z + clamp(farZ - half - 0.1 - me.z, 1.9, 2.4) };
    const fallD = (-0.4) - (y0);   // from just under the floor to the pit floor (its bottom)
    const T_FLOOR = T_DROP + Math.sqrt(2 * fallD / GRAV);
    const T_HOP = T_FLOOR + 0.6, T_ON = T_HOP + 0.32, DUR = T_ON + 2.1, T_SPLIT = T_ON + 0.9;
    const engulf = { x: me.x + 0.55, z: me.z + 0.62 };   // its centre once you are inside it (you are between the core and its skin)
    const hits = hitsOf([[trap.land, 4, 1], [T_ON, 4, -1], [T_ON + 0.5, 4, 1], [T_ON + 1.0, 3, -1], [T_ON + 1.5, 2, 1], [DUR, 3, -1]]);
    // Where it is (its bottom centre) and how squashed.
    const slimeAt = (t) => {
      if (t < T_DARK) return null;
      if (t < T_DROP) { const k = sstep(T_DARK, T_DROP, t); return { x: hole.x, y: lerp(0.6, -0.4, k), z: hole.z, sx: 1 - 0.1 * k, sy: 1 + 0.15 * k }; }   // squeezing through the hole
      if (t < T_FLOOR) { const d = t - T_DROP; return { x: hole.x, y: -0.4 - 0.5 * GRAV * d * d, z: hole.z, sx: 0.92, sy: 1.12 }; }
      if (t < T_HOP) { const k = sstep(T_FLOOR, T_FLOOR + 0.25, t); const sq = pulse(t, [T_FLOOR], 0.12); return { x: lerp(hole.x, front.x, k), y: y0 + Math.sin(k * Math.PI) * 0.5, z: lerp(hole.z, front.z, k), sx: 1 + 0.35 * sq, sy: 1 - 0.4 * sq + 0.08 * Math.sin(t * 9) }; }
      if (t < T_ON) { const k = (t - T_HOP) / (T_ON - T_HOP); return { x: lerp(front.x, engulf.x, k), y: y0 + Math.sin(k * Math.PI) * 0.9, z: lerp(front.z, engulf.z, k), sx: 0.9, sy: 1.15 }; }
      const b = Math.sin((t - T_ON) * 6) * 0.5 + 0.5;   // on you, squeezing
      return { x: engulf.x, y: y0, z: engulf.z, sx: 1 + 0.12 * b, sy: 1 - 0.18 * b };
    };

    const cam = (t) => {
      const s = settle(R, t, 0.9);
      const k = sstep(0.8, 1.3, t);
      let c = { x: s.x * (1 - k), y: s.y, z: s.z * (1 - k), yaw: lerp(s.yaw, 0, k), pitch: lerp(s.pitch, -0.02, k), roll: 0, fov: s.fov };
      c = trap.cam(t, c);
      if (t > trap.land + 0.3) {
        const up = sstep(trap.land + 0.4, T_DARK - 0.1, t) * (1 - sstep(T_FLOOR - 0.35, T_FLOOR + 0.1, t));
        const sl = slimeAt(t);
        const lookFace = sstep(T_FLOOR - 0.2, T_FLOOR + 0.3, t);
        c.pitch = lerp(lerp(-0.25, 1.35, up), sl ? R.pitchTo(c.x, c.y, c.z, sl.x, y0 + 1.1, sl.z) : 0, lookFace);
        c.yaw = lerp(0, sl ? R.yawTo(c.x, c.z, sl.x, sl.z) : 0, lookFace);
      }
      if (t > T_ON) {   // inside it: pressed down into the slime water
        const k2 = sstep(T_ON, T_ON + 0.25, t);
        c.y = lerp(c.y, y0 + 0.75, k2); c.pitch = lerp(c.pitch, 0.25, k2); c.yaw = lerp(c.yaw, -0.2, k2); c.roll = lerp(c.roll, -0.25, k2);
        c.fov = s.fov - 8 * k2;
      }
      return shake(c, t, 0.0015 + 0.03 * pulse(t, [T_FLOOR, T_ON], 0.2) + 0.012 * pulse(t, hits.map((h) => h.t), 0.18), 5);
    };

    const bubbles = [], drops = [];
    for (let i = 0; i < 40; i++) bubbles.push({ t0: T_ON + 0.1 + r() * (DUR - T_ON), at: [me.x + (r() - 0.2) * 0.8, y0 + 0.5 + r() * 0.5, me.z + 0.2 + r() * 0.7], v: [0, 0.6 + r() * 0.5, 0], life: 0.9, size: 0.05 + r() * 0.04, tile: 32, color: [0.75, 0.95, 0.7], grav: -0.3, fog: false });
    for (const [tt, x, z, n] of [[trap.land, me.x, me.z, 22], [T_FLOOR, hole.x, hole.z, 30], [T_ON, engulf.x, engulf.z, 26]]) for (let i = 0; i < n; i++) drops.push({ t0: tt + r() * 0.05, at: [x + (r() - 0.5) * 1.2, y0 + 0.2, z + (r() - 0.5) * 1.2], v: [(r() - 0.5) * 2, 2 + r() * 2, (r() - 0.5) * 2], life: 0.8, size: 0.06, tile: 19 + Math.floor(r() * 4), color: [0.45, 0.85, 0.35], grav: 9, fog: false });
    const fx = particles(R, partTex, [...bubbles, ...drops]);
    const sounds = [
      ...trap.sounds,
      [trap.land + 0.01, "game.player.swim.splash", { volume: 1 }],
      [trap.land + 0.6, "qf.scare.whisper", { volume: 0.25 }],
      [T_DARK - 0.2, "mob.slime.big", { at: [hole.x, 0.5, hole.z], volume: 0.7, pitch: 0.7 }],
      [T_DARK + 0.3, "mob.slime.big", { at: [hole.x, 0, hole.z], volume: 0.8, pitch: 0.6 }],
      [T_DROP, "qf.scare.stinger", { volume: 0.8 }],
      [T_FLOOR, "mob.slime.big", { at: [front.x, y0, front.z], volume: 1, pitch: 0.55 }], [T_FLOOR + 0.01, "random.splash", { volume: 1 }],
      [T_HOP, "mob.slime.big", { at: [front.x, y0, front.z], volume: 1, pitch: 0.6 }],
      [T_ON, "mob.slime.attack", { volume: 1, pitch: 0.7 }], [T_ON + 0.01, "qf.scare.hit", { volume: 1 }], [T_ON + 0.02, "random.splash", { volume: 0.8 }], [T_ON + 0.03, "qf.scare.shriek", { volume: 0.5 }],
      [T_ON + 0.05, "@muffle", { hz: 220, s: DUR - T_ON + 2 }],
      ...hits.slice(2).map((h) => [h.t, "game.player.hurt"]),
      ...hits.slice(2).map((h, i) => [h.t + 0.02, "mob.slime.attack", { volume: 0.7, pitch: 0.6 + 0.05 * i }]),
      ...[0, 1, 2].map((i) => [T_SPLIT + i * 0.18, "mob.slime.small", { at: [engulf.x, y0 + 0.5, engulf.z], volume: 0.8, pitch: 1 + 0.1 * i }]),
      [T_ON + 1.7, "qf.scare.scream", { volume: 0.6, pitch: 0.7 }],
      [DUR, "game.player.die"]
    ];
    const loops = [
      [0.5, DUR + 0.2, "qf.scare.heartbeat", { volume: 0.5 }],
      [trap.land + 0.2, T_ON, "qf.scare.breath", { volume: 0.45, fadeIn: 0.4, fadeOut: 0.05 }],
      [T_DARK, T_ON + 0.2, "qf.scare.drone", { volume: 0.5, fadeIn: 0.6, fadeOut: 0.1 }]
    ];

    function update(t, f) {
      trap.update(t, f);
      pool.visible = t >= trap.open;
      const sl = slimeAt(t), camNow = cam(t);
      S.pivot.visible = !!sl;
      if (sl) {
        R.place(S, sl.x, sl.y, sl.z, R.yawTo(sl.x, sl.z, camNow.x, camNow.z));
        S.anim(t, 0, {});
        S.pivot.scale.set(sl.sx, sl.sy, sl.sx);
      }
      // Budding: three small ones out of its sides, hopping away.
      small.forEach((m, i) => {
        const k = (t - T_SPLIT - i * 0.18) / 0.9; m.pivot.visible = k > 0;
        if (k <= 0) return;
        // (out in front of you, where you can see them go through the green)
        const fwd = { x: Math.sin(0.2), z: Math.cos(0.2) }, lat = (i - 1) * 0.55, d = 0.7 + Math.min(1, k) * 1.3;
        const x = me.x + fwd.x * d + fwd.z * lat * (0.4 + k), z = me.z + fwd.z * d - fwd.x * lat * (0.4 + k);
        R.place(m, x, y0 + Math.abs(Math.sin(k * Math.PI * 2)) * 0.45, z, R.yawTo(me.x, me.z, x, z)); m.anim(t + i, 0, {});
      });
      fx(t);
      // The hole's light goes when it fills it; inside, all green and far away.
      const blocked = sstep(T_DARK, T_DROP - 0.1, t) * (1 - sstep(T_DROP + 0.1, T_FLOOR, t));
      const inside = sstep(T_ON - 0.05, T_ON + 0.1, t);
      f.env = { bake: 1 - 0.25 * sstep(0.2, 1.2, t) - 0.3 * blocked, lights: 1 - 0.6 * blocked, fogMul: 1 + 0.4 * sstep(1, 3, t), fogAdd: 0.4 * inside, fog: [0.06, 0.19, 0.05, inside], squash: inside * 0.35 * (Math.sin((t - T_ON) * 6) * 0.5 + 0.5) };
      f.tints = [[50, 150, 40, 0.22 * inside]];
      f.vig = [10, 30, 0, 0.3 + 0.3 * blocked + 0.35 * inside]; f.vigR = 0.9;
      f.air = t > T_ON ? 1 - clamp((t - T_ON) / 1.6) : null;
      f.black = 0.4 * sstep(DUR - 0.3, DUR + 0.6, t);
    }
    return { dur: DUR, hits, cam, update, sounds, loops, deathSide: -1, notes: { fits: trap.fits, D: Dp, front, T_FLOOR: +T_FLOOR.toFixed(2) } };
  }
};
