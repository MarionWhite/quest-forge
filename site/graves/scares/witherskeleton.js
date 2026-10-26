// Wither Skeleton (deep): the fog goes black and the torches sink; far down the corridor, high up, two eyes. A stone
// sword drags along the wall, and each scrape throws sparks that show it, taller, closer. It cuts you once: the
// Wither takes the hearts black and the edges of the view with them. The second swing takes the head: the view
// flies, hits the floor and rolls, and comes to rest looking up at its feet, past your own body going over.
import { THREE, clamp, lerp, sstep, pulse, tex, easeOut } from "./rig.js";
import { settle, shake, hitsOf, particles, mulberry, glowEyes, bipedSwing, swingAt } from "./common.js";

const TAU = Math.PI * 2;

export default {
  death: "Steve was slain by Wither Skeleton",
  async build(R) {
    const partTex = await tex("particles");
    const r = mulberry(R.seed * 5 + 77);
    // It comes along the wall on its sword side (its right, your left, as it faces you).
    const side = R.wallL < 3 || R.wallL <= R.wallR ? -1 : 1;
    const wall = side < 0 ? R.wallL : R.wallR;
    const sx = side * clamp(wall - 0.6, 0.35, 1.1);
    const onWall = wall - Math.abs(sx) < 1.0;
    const z0 = clamp(R.ahead - 1.2, 5, 9.5);
    const T_EYES = 1.85, T_W0 = 2.15, T_W1 = 4.05, T_SW1 = 4.18, T_HIT1 = 4.3, T_SW2 = 5.28, T_DECAP = 5.4, T_LAND = 5.85, T_REST = 6.5, DUR = 7.5;
    const z1 = 1.55;
    const hits = hitsOf([[T_HIT1, 7, -side], [4.95, 1, side], [T_DECAP, 12, side]]);
    const W = R.mob("WitherSkeleton", { amb: [0.025, 0.025, 0.03], equipment: [{ id: "minecraft:stone_sword", ench: false }] });
    // Its eye sockets (the 1.7.10 texture's black holes), lit cold: all you see of it in the black.
    const eyes = glowEyes(R, W, [[-2, -3.5, -4.06, 2, 1], [2, -3.5, -4.06, 2, 1]], [0.62, 0.66, 0.78], { halo: 0.2, glow: 0.12 });
    // Where it walks: down the corridor to you, then over to where your head comes to rest.
    const scrapes = [2.55, 3.15, 3.72];
    const wz = (t) => lerp(z0, z1, sstep(T_W0, T_W1, t)) - 0.35 * sstep(T_HIT1 + 0.3, T_SW2, t);

    // Your head's flight: off to the side away from the blade, back, down to the floor, rolling.
    const fs = -side;
    const camAlive = (t) => {
      const s = settle(R, t, 0.9);
      const k = sstep(0.8, 1.3, t);
      const zS = wz(t), look = sstep(T_W1 - 0.4, T_W1 + 0.1, t);
      const c = { x: s.x * (1 - k), y: s.y, z: s.z * (1 - k), yaw: lerp(s.yaw, 0, k), pitch: lerp(s.pitch, 0.03, k), roll: 0, fov: s.fov };
      // Glances at each scrape; then up at it as it looms.
      for (const ts of scrapes) { const g = sstep(ts, ts + 0.2, t) * (1 - sstep(ts + 0.45, ts + 0.8, t)); c.yaw += g * R.yawTo(0, 0, sx, zS) * 0.6; }
      c.yaw = lerp(c.yaw, R.yawTo(c.x, c.z, sx, zS) * 0.8, look);
      c.pitch = lerp(c.pitch, R.pitchTo(c.x, R.eye, c.z, sx, 2.05, zS) * 0.85, look);
      // The first cut: knocked back a step, the view swims.
      const kb = easeOut((t - T_HIT1) / 0.35) * (t > T_HIT1 ? 1 : 0);
      c.z -= 0.35 * kb; c.x -= side * 0.1 * kb; c.fov += 6 * pulse(t, [T_HIT1], 0.3) - 4 * sstep(T_HIT1, T_SW2, t);
      c.roll += Math.sin(t * 1.9) * 0.05 * sstep(T_HIT1, T_HIT1 + 0.5, t);
      return shake(c, t, 0.0015 + 0.003 * sstep(T_EYES, T_W1, t) + 0.02 * pulse(t, [T_HIT1, 4.95], 0.18), 6);
    };
    const S0 = camAlive(T_DECAP);
    const clampX = (x) => clamp(x, -(R.wallL - 0.3), R.wallR - 0.3);
    const L = { x: clampX(S0.x + 0.85 * fs), z: S0.z - 1.0 };
    const E = { x: clampX(L.x + 0.4 * fs), z: L.z - 0.5 };
    const feet = { x: lerp(S0.x, E.x, 0.35) - fs * 0.15, z: lerp(S0.z, E.z, 0.35) + 0.25 };   // where it stands at the end
    const yawEnd = R.yawTo(E.x, E.z, feet.x, feet.z);
    const cam = (t) => {
      if (t < T_DECAP) return camAlive(t);
      const ka = clamp((t - T_DECAP) / (T_REST - T_DECAP)), ea = easeOut(ka);
      const kf = clamp((t - T_DECAP) / (T_LAND - T_DECAP)), kr = easeOut((t - T_LAND) / (T_REST - T_LAND));
      const c = { fov: S0.fov + 6 };
      if (t < T_LAND) { c.x = lerp(S0.x, L.x, kf); c.z = lerp(S0.z, L.z, kf); c.y = lerp(S0.y, 0.22, kf * kf) + Math.sin(kf * Math.PI) * 0.4; }
      else { const bounce = Math.abs(Math.sin(kr * Math.PI * 2)) * 0.1 * (1 - kr); c.x = lerp(L.x, E.x, kr); c.z = lerp(L.z, E.z, kr); c.y = 0.22 + bounce; }
      // Tumbling: a spin and a half end over end in the air, then the roll along the floor onto its side.
      c.yaw = lerp(S0.yaw, yawEnd, ea) + Math.sin(ka * Math.PI) * 1.3 * fs;
      c.pitch = lerp(S0.pitch, 0.42, ea) + Math.sin(kf * Math.PI) * 1.6 * (t < T_LAND ? 1 : 0);
      c.roll = lerp(0, 1.32 * fs + TAU * fs, ea);
      return c;
    };

    // Your body: there once the head is off, headless, the iron sword in hand; it goes over sideways (rotateCorpse).
    const body = R.mob("Steve", { amb: [0.06, 0.06, 0.06], equipment: [{ id: "minecraft:iron_sword", ench: false }] });
    if (body.parts.head) body.parts.head.visible = false;
    const corpse = (t) => fs * Math.min(1, Math.sqrt(Math.max(0, (t - T_DECAP - 0.15) * 20) / 20 * 1.6)) * Math.PI / 2;
    const neckAt = (t) => { const ro = corpse(t), rx = Math.cos(S0.yaw), rz = Math.sin(S0.yaw); return [S0.x - rx * Math.sin(ro) * 1.45, Math.max(0.1, 1.45 * Math.cos(ro)), S0.z - rz * Math.sin(ro) * 1.45]; };
    // Gore: the cut at the neck, then the fountain while it falls.
    R.burst(T_DECAP + 0.04, [S0.x - fs * 0.1, 1.38, S0.z + 0.1], 40, "blood", { dir: [-fs * 0.8, 1.6, 0.4], speed: 3.0, spread: 0.9, size: 0.045, life: 1.6, stick: 4 });
    R.burst(T_DECAP + 0.05, [S0.x - fs * 0.1, 1.38, S0.z + 0.1], 12, "flesh", { dir: [-fs * 0.6, 1.2, 0.3], speed: 2.2, spread: 0.9, size: 0.07, life: 1.5, stick: 4 });
    R.burst(T_DECAP + 0.06, [S0.x - fs * 0.1, 1.38, S0.z + 0.1], 8, "bone", { dir: [-fs, 1, 0], speed: 2.0, spread: 0.9, size: 0.05, life: 1.4, stick: 4 });
    for (let tt = T_DECAP + 0.08; tt < T_DECAP + 1.3; tt += 0.09) { const n = neckAt(tt); R.burst(tt, n, 9, "blood", { dir: [0, 2.2, 0], speed: 2.2 * (1 - (tt - T_DECAP) / 1.6), spread: 0.45, size: 0.05, life: 1.3, stick: 3 }); }
    R.burst(T_HIT1, [0, 1.15, 0.35], 26, "blood", { dir: [side * 0.6, 0.6, 0.8], speed: 2, spread: 0.7, size: 0.05, life: 1.2, stick: 3 });

    // Sparks off the stone where the blade drags (EntityCritFX, tile 65), and the light they throw.
    const sparkSpecs = [];
    for (const ts of scrapes) for (let i = 0; i < 26; i++) {
      const tt = ts + r() * 0.32, z = wz(tt) + 0.35;
      const at = onWall ? [side * (wall - 0.04), 0.55 + r() * 0.35, z] : [sx + side * 0.75, 0.05, z];
      sparkSpecs.push({ t0: tt, at, v: [-side * (0.6 + r()), 0.8 + r() * 1.2, (r() - 0.5) * 1.2], life: 0.35 + r() * 0.3, size: 0.05 + r() * 0.04, tile: 65, color: [1, 0.75 + r() * 0.2, 0.35], grav: 7, fog: false, add: true });
    }
    const sparks = particles(R, partTex, sparkSpecs);
    const flash = R.ownLight(R.light(0xffb860, 0, 5, 1.3));
    const cold = R.ownLight(R.light(0x8090b0, 0, 5, 1.4));

    const steps = [];
    for (let tt = T_W0 + 0.15; tt < T_W1; tt += 0.42) steps.push([tt, "mob.skeleton.step", { at: [sx, 0.1, wz(tt)], volume: 0.5, pitch: 0.8 }]);
    const scrapeSnd = scrapes.flatMap((ts) => [0, 0.07, 0.15, 0.22, 0.3].map((d, i) => [ts + d, i % 2 ? "step.stone" : "dig.stone", { at: [onWall ? side * wall : sx, 0.7, wz(ts + d)], volume: 0.55, pitch: 1.6 + 0.12 * ((i * 3) % 4) }]));
    const sounds = [
      [T_EYES + 0.1, "mob.skeleton.say", { at: [sx, 2.1, z0], volume: 0.7, pitch: 0.65, reverb: 0.6 }],
      ...steps, ...scrapeSnd,
      [T_W1 - 0.3, "mob.skeleton.say", { at: [sx, 2.1, z1 + 0.3], volume: 1, pitch: 0.6 }],
      [T_SW1 - 0.05, "qf.scare.stinger", { volume: 0.9 }],
      [T_HIT1, "game.player.hurt"], [T_HIT1 + 0.01, "qf.scare.hit", { volume: 1 }], [T_HIT1 + 0.03, "qf.scare.gore", { volume: 0.8 }],
      [4.95, "game.player.hurt", { volume: 0.7, pitch: 0.8 }],
      [T_SW2, "mob.skeleton.say", { at: [sx, 2.1, z1], volume: 0.9, pitch: 0.55 }],
      [T_DECAP, "qf.scare.crunch", { volume: 1 }], [T_DECAP + 0.01, "qf.scare.gore", { volume: 1 }], [T_DECAP + 0.02, "game.player.die"],
      [T_DECAP + 0.05, "@muffle", { hz: 420, s: 4 }],
      [T_LAND, "game.player.hurt.fall.small", { volume: 0.9 }], [T_LAND + 0.22, "step.stone", { volume: 0.7, pitch: 0.7 }], [T_LAND + 0.42, "step.stone", { volume: 0.5, pitch: 0.65 }],
      [T_DECAP + 0.75, "game.player.hurt.fall.big", { at: [S0.x, 0.3, S0.z], volume: 0.8 }],
      [6.7, "mob.skeleton.step", { at: [feet.x, 0.1, feet.z], volume: 0.9, pitch: 0.75 }], [7.05, "mob.skeleton.step", { at: [feet.x, 0.1, feet.z], volume: 0.9, pitch: 0.7 }],
      [7.2, "mob.skeleton.say", { at: [feet.x, 2.1, feet.z], volume: 0.9, pitch: 0.55 }]
    ];
    const loops = [
      [0.5, T_DECAP, "qf.scare.heartbeat", { volume: 0.55, fadeOut: 0.02 }],
      [0.4, T_DECAP, "qf.scare.drone", { volume: 0.5, fadeIn: 1.8, fadeOut: 0.05, pitch: 0.7 }],
      [T_HIT1 + 0.2, T_DECAP, "qf.scare.breath", { volume: 0.45, fadeIn: 0.2, fadeOut: 0.02 }],
      [T_DECAP + 0.05, DUR + 1, "qf.scare.ringing", { volume: 0.5, fadeIn: 0.05, fadeOut: 1.5 }]
    ];

    function update(t, f) {
      // The skeleton.
      const walking = t > T_W0 && t < T_W1;
      let x = sx, z = wz(t);
      if (t > T_REST - 0.4) { const k = sstep(T_REST - 0.4, 7.1, t); x = lerp(sx, feet.x, k); z = lerp(z, feet.z, k); }
      const camNow = cam(t);
      W.pivot.visible = t > T_EYES - 0.1;
      R.place(W, x, 0, z, R.yawTo(x, z, camNow.x, camNow.z));
      W.anim(t, 0, { walk: walking || (t > T_REST - 0.4 && t < 7.1) ? 0.8 : 0, lookPitch: t > T_REST ? 0.55 : 0 });
      bipedSwing(W, swingAt(t, [T_SW1, T_SW2], 0.3));
      eyes(sstep(T_EYES, T_EYES + 0.4, t) * (t < T_DECAP ? 1 : 0.6));
      // The body.
      body.pivot.visible = t >= T_DECAP;
      if (body.pivot.visible) { R.place(body, S0.x, 0, S0.z, S0.yaw, 0, corpse(t)); body.anim(t, 0, { walk: 0, still: true }); if (body.parts.head) { body.parts.head.visible = false; if (body.parts.headwear) body.parts.headwear.visible = false; } }
      sparks(t);
      // Light: each scrape's sparks show it; a cold glimmer on it once it is close.
      const sp = Math.max(...scrapes.map((ts) => (t >= ts && t < ts + 0.42 ? (0.6 + 0.4 * Math.sin((t - ts) * 60)) * (1 - (t - ts) / 0.42) : 0)));
      R.L(onWall ? side * (wall - 0.3) : sx + side * 0.6, 0.8, wz(t) + 0.2, flash.position); flash.intensity = 5 * sp;
      // a cold light on it as it comes close, and on the floor where your head ends up
      if (t < T_DECAP) R.L(lerp(sx, 0, 0.5), 2.5, z - 0.9, cold.position); else R.L(lerp(E.x, feet.x, 0.5), 1.6, lerp(E.z, feet.z, 0.5) - 0.2, cold.position);
      cold.intensity = 2.4 * sstep(T_W1 - 0.6, T_W1, t) + 1.2 * sstep(T_LAND, T_REST, t);
      // The black: fog and the torches sink; the Wither takes the edges of the view.
      // (the black lifts a little as you die)
      const blk = sstep(0.4, 2.0, t) * (1 - 0.45 * sstep(T_DECAP + 0.3, T_REST, t)), wither = sstep(T_HIT1, T_HIT1 + 0.4, t);
      f.env = { bake: 1 - 0.65 * blk, lights: 1 - 0.7 * blk, fogMul: 1 + 2.0 * blk, fog: [0, 0, 0, blk] };
      f.hpMode = t > T_HIT1 ? "wither" : "normal";
      f.vig = [0, 0, 0, 0.3 * blk + 0.45 * wither * (0.85 + 0.15 * Math.sin(t * 5))]; f.vigR = 0.9 - 0.3 * wither;
      f.tints = [[150, 0, 0, 0.45 * pulse(t, [T_DECAP], 0.35)]];
      f.splats = hits.slice(0, 1).concat(t > T_DECAP ? [{ t: T_DECAP }] : []).filter((h) => t >= h.t).map((h, i) => ({ t0: h.t, x: [0.35, 0.6][i], y: [0.45, 0.4][i], r: [14, 22][i], seed: 41 + i }));
      f.black = 0.35 * sstep(DUR - 0.3, DUR + 0.6, t);
    }
    return { dur: DUR, hits, cam, update, sounds, loops, deathSide: fs, notes: { side, wall, onWall, z0, S0: [+S0.x.toFixed(2), +S0.z.toFixed(2)], L, E, feet } };
  }
};
