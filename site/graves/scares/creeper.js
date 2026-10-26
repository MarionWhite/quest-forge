// Creeper: the look-back. A hiss right behind you. The head turns, slowly, and time slows with it. Then, a coin toss:
//   - it is there, and its face comes at the lens flashing white and swelling;
//   - nothing is there. The hiss has stopped. Sometimes it stands far down the corridor in the dark, still, watching.
//     Silence. The head comes back round, slowly, and it is at your face (it cannot be: you just saw it over there),
//     strobing white, swelling into the lens with the screech.
// White-out. Ringing, the world muffled. From the floor you see the crater it blew in the real floor and your hotbar
// scattering across it. Then, by your ear, a second hiss.
import { THREE, track, clamp, lerp, sstep, pulse, tex } from "./rig.js";
import { settle, shake, hitsOf, explosionFX, droppedItems, particles, smoke } from "./common.js";
import { lunge, lungeFx, screech, faceAnchor, boxOf, silence, deathScream, jit } from "./fnaf.js";

export default {
  death: "Steve was blown up by Creeper",
  async build(R) {
    const [boomTex, partTex, ...itemTex] = await Promise.all(["explosion", "particles", "item_iron_sword", "item_stone_pickaxe", "k:torch_on", "item_bread", "item_apple"].map((n) => tex(n)));
    const side = R.wallR > R.wallL ? -1 : 1;           // the way the head turns (toward the roomier side)
    const back = Math.PI * side * 0.97;
    // ---- the dice -------------------------------------------------------------------------------------------
    const behindHit = R.chance(0.35);
    const farGlimpse = !behindHit && R.behind > 5 && R.chance(0.6);
    const T_HISS = 0.9 + R.vary(0.55, 0.5), T_TURN = T_HISS + R.vary(0.3, 0.4), T_FACE = T_TURN + R.vary(1.65, 0.2);
    let t0, tStop = null, tSil, tB0 = null, tB1 = null;
    if (behindHit) { t0 = T_FACE - 0.22; tSil = T_TURN + 0.6; }
    else { tStop = T_FACE - R.vary(0.5, 0.4); tSil = T_FACE + 0.15; tB0 = T_FACE + R.vary(1.1, 0.45); tB1 = tB0 + R.vary(1.25, 0.2); t0 = tB1 - 0.2; }
    const cz = R.behind > 1.5 ? -0.74 : -0.3, cx = R.behind > 1.5 ? 0.05 : (R.wallR > R.wallL ? 0.55 : -0.55);
    const far = { x: R.wallR > R.wallL ? 0.35 : -0.35, z: -clamp(R.behind - 1.2, 4, 10) };
    const start = behindHit ? { x: cx, z: cz } : { x: 0.05, z: clamp(R.ahead - 0.4, 0.6, 0.85) };
    const c1 = R.mob("Creeper", { amb: [0.03, 0.03, 0.03], own: true });
    const cFar = R.mob("Creeper", { amb: [0.03, 0.03, 0.03], own: true });
    const c2 = R.mob("Creeper", { amb: [0.03, 0.03, 0.03], own: true });
    c1.anim(0, 0, { walk: 0 }); R.place(c1, 0, 0, 2, Math.PI);
    const anchor = faceAnchor(c1, c1.parts.head, boxOf("creeper", "head"));
    const L = lunge(R, c1, { t0, rush: R.vary(0.22, 0.15), hold: R.vary(0.55, 0.2), cut: 0.04, dist: 0.34, anchor, seed: 11 });
    const T_BOOM = L.t2;
    const T_HISS2 = T_BOOM + R.vary(2.6, 0.15), DUR = T_HISS2 + 1.0;
    // Where it blows: right at your face, along the look at that moment.
    const lookAtBoom = behindHit ? back : 0;
    const bx = -Math.sin(lookAtBoom) * 0.55, bz = Math.cos(lookAtBoom) * 0.55;
    const bn = Math.hypot(bx, bz) || 1;
    // Thrown away from it: onto your side, looking back at the crater.
    const landZ = clamp(-bz / bn * 2.0, -(R.behind - 0.6), R.ahead - 0.6);
    const land = [clamp(-bx / bn * 0.8 + 0.35 * -side, -R.wallL + 0.6, R.wallR - 0.6), 0.42, landZ];
    const c2at = [land[0] + 0.85 * side, land[2] + (landZ >= 0 ? 0.5 : -0.5)];
    const boom = explosionFX(R, T_BOOM, [bx, 0.9, bz], boomTex, { n: 16, spread: 1.6, seed: 5 });
    const items = droppedItems(R, T_BOOM + 0.06, [0, 1.0, 0.2], itemTex, { seed: 13, speed: 3.6 });
    const glow = R.ownLight(R.light(0xffffff, 0, 5, 1.2));

    const hits = hitsOf([[T_BOOM, 17, side], [DUR - 0.05, 3, -side]]);
    // The turn: slow, slower as it comes round (time slows); the field narrows; and slowly back.
    const yk = [[0, 0], [T_TURN, 0], [T_TURN + 0.5, back * 0.25, "i"], [T_FACE, back * 0.95, "s"]];
    if (!behindHit) yk.push([tB0, back * 0.97], [tB0 + 0.4, back * 0.8, "i"], [tB1, 0.02 * side, "s"]);
    const yaw = track(yk);
    const narrow = (t) => -16 * sstep(behindHit ? T_FACE - 0.6 : tB1 - 0.7, behindHit ? T_FACE : tB1, t) * (t < T_BOOM ? 1 : 0) - 8 * sstep(T_TURN, T_FACE, t) * (behindHit ? 0 : 1 - sstep(T_FACE, tB0, t));
    const fov = (t) => R.start.fov + narrow(t) + 12 * pulse(t, [L.t1], 0.12) + (t >= T_BOOM ? 10 * Math.exp(-(t - T_BOOM) / 0.4) + 4 - 12 * sstep(T_HISS2, DUR, t) : 0);
    const camAlive = (t) => {
      const s = settle(R, t, 0.9);
      const k = sstep(0.8, 1.3, t);
      const c = { x: s.x * (1 - k), y: s.y, z: s.z * (1 - k), yaw: lerp(s.yaw, yaw(t), k), pitch: lerp(s.pitch, -0.1 * sstep(T_TURN, T_FACE, t) * (behindHit ? 1 : 1 - sstep(tB0, tB1, t)), k), roll: 0, fov: fov(t), near: t >= t0 ? 0.02 : undefined };
      return shake(c, t, 0.0015 + 0.004 * sstep(T_TURN, T_FACE, t) + L.shake(t), 2);
    };
    const cam = (t) => {
      if (t < T_BOOM) return camAlive(t);
      // Thrown: a tumble through the air, then on the floor on your side, facing the crater.
      const a = camAlive(T_BOOM - 0.001), k = clamp((t - T_BOOM) / 0.55), e = 1 - Math.pow(1 - k, 2);
      const arc = Math.sin(k * Math.PI) * 0.45;
      const faceCr = R.yawTo(land[0], land[2], bx, bz);
      const c = { x: lerp(a.x, land[0], e), y: lerp(a.y, land[1], k * k) + arc, z: lerp(a.z, land[2], e), yaw: lerp(a.yaw, faceCr + 0.25 * side, e) + 0.7 * side * Math.sin(k * Math.PI), pitch: lerp(a.pitch, -0.14, e) + Math.sin(k * Math.PI) * 0.6, roll: lerp(0, 1.05 * side, e), fov: fov(t) };
      const bounce = k >= 1 ? Math.exp(-(t - T_BOOM - 0.55) * 8) * Math.sin((t - T_BOOM - 0.55) * 28) * 0.03 : 0;
      c.y += bounce;
      const lk = sstep(T_HISS2 + 0.1, T_HISS2 + 0.9, t);
      c.yaw = lerp(c.yaw, R.yawTo(c.x, c.z, c2at[0], c2at[1]), lk); c.pitch = lerp(c.pitch, 0.12, lk);
      return shake(c, t, 0.004 * (1 - sstep(T_BOOM + 0.6, T_BOOM + 2, t)) + 0.0025, 4);
    };

    const crater = () => {
      const zc = Math.round(bz), xc = Math.round(bx);
      R.carveL([
        [[xc - 2, -1, zc - 1], [xc + 2, -1, zc + 1]], [[xc - 1, -1, zc - 2], [xc + 1, -1, zc + 2]],
        [[xc - 1, -2, zc - 1], [xc + 1, -2, zc + 1]], [[xc, -3, zc], [xc, -3, zc]]
      ]);
    };
    R.burst(T_BOOM, [bx, 0.3, bz], 40, R.floorBlock === "gravel" ? "dust" : "stone", { dir: [0, 2.2, 0], speed: 4.5, spread: 1.4, size: 0.12, life: 1.6, stick: 4 });
    R.burst(T_BOOM, [bx, 0.8, bz], 30, "green", { dir: [0, 1.2, 0], speed: 4, spread: 1.6, size: 0.09, life: 1.4, stick: 4 });
    R.burst(T_BOOM + 0.01, [bx * 0.3, 1.3, bz * 0.3], 30, "blood", { dir: [-bx, 0.8, -bz], speed: 3.5, spread: 1.0, size: 0.06, life: 1.4, stick: 4 });
    const puffs = particles(R, partTex, [...smoke([bx, 0.2, bz], T_BOOM + 0.1, 24, { spread: 2.2, window: 1.0, life: 2.2, size: 0.5, rise: 0.9, seed: 7 }),
      ...smoke([bx, -0.6, bz], T_BOOM + 1.3, 14, { spread: 1.2, window: 4, life: 2.4, size: 0.35, rise: 0.6, seed: 8 })]);

    const S2 = screech(L, [["creeper.primed", { pitch: 0.6 }], ["mob.creeper.say", { pitch: 0.5, volume: 1.2 }]]);
    const sounds = [
      [T_HISS, "creeper.primed", { at: [cx, 1.2, cz], volume: 1 }],
      [T_TURN + 0.2, "mob.creeper.say", { at: [cx, 1.2, cz], volume: 0.4, pitch: 0.6 }],
      ...(tStop ? [[tStop, "random.click", { at: [cx, 0.5, cz], volume: 0.3, pitch: 0.5 }]] : []),
      silence(tSil),
      ...(farGlimpse ? [[T_FACE + 0.5, "step.grass", { at: [far.x, 0, far.z], volume: 0.12, pitch: 0.7 }]] : []),
      ...(tB1 ? [[tB1 - 0.45, "creeper.primed", { at: [start.x, 1.2, start.z], volume: 0.25, pitch: 0.8 }]] : []),
      ...S2.sounds,
      [T_BOOM, "random.explode", { volume: 1.6, pitch: 0.7 }],
      [T_BOOM + 0.01, "qf.scare.hit", { volume: 1.2 }],
      [T_BOOM + 0.02, "@muffle", { hz: 260, s: 4.5 }],
      [T_BOOM + 0.55, "game.player.hurt.fall.big", { volume: 0.7 }],
      [T_BOOM + 0.7, "dig.stone", { at: [bx, 0, bz], volume: 0.5, pitch: 0.7 }],
      ...deathScream(T_BOOM + 1.0, { volume: 1.2, under: false }),
      [T_HISS2, "creeper.primed", { at: [c2at[0], 0.9, c2at[1]], volume: 1, pitch: 0.92 }],
      [T_HISS2 + 0.3, "qf.scare.whisper", { volume: 0.3 }],
      [DUR - 0.05, "random.explode", { volume: 1.4, pitch: 0.65 }], [DUR - 0.04, "qf.scare.hit", { volume: 1 }],
      ...deathScream(DUR - 0.02, { volume: 1.0, under: false }),
      [DUR, "game.player.die"]
    ];
    const loops = [
      [0.5, tSil, "qf.scare.heartbeat", { volume: 0.55, fadeOut: 0.05 }],
      [T_TURN, tSil, "qf.scare.drone", { volume: 0.45, fadeIn: 1.4, fadeOut: 0.05, bus: "sfx" }],
      ...S2.loops,
      [T_BOOM + 0.05, DUR + 1, "qf.scare.ringing", { volume: 0.7, fadeIn: 0.1, fadeOut: 2 }],
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
      // The one at your face (or behind); gone in the blast.
      const vis = t < T_BOOM && (behindHit ? true : t > (tB0 ?? 0) + (tB1 - tB0) * 0.45);
      c1.pivot.visible = vis;
      if (vis) {
        const fuse = t < t0 ? 0.15 : clamp((t - t0) / (T_BOOM - t0));
        // FNAF: past the rush the flashes come every frame-pair, not every tenth.
        creeperAt(c1, t, start.x, start.z, Math.pow(fuse, 1.3), t >= L.t1 ? (Math.floor(t * 24) % 2 ? 0.95 : 0.15) : fuse);
        if (t >= t0) {
          if (c1.parts.head) c1.parts.head.rotation.set(jit(t, 21) * 0.12, jit(t, 23) * 0.14, jit(t, 25) * 0.12);
          L.apply(t);
        }
      }
      cFar.pivot.visible = farGlimpse && t > T_TURN && t < tB0 + 0.6;
      if (cFar.pivot.visible) creeperAt(cFar, t, far.x, far.z, 0, 0);
      c2.pivot.visible = t > T_HISS2 - 0.4 && t < DUR;
      if (c2.pivot.visible) { const f2 = clamp((t - T_HISS2) / (DUR - T_HISS2)); creeperAt(c2, t, c2at[0], c2at[1], Math.pow(f2, 1.5), f2); c2.pivot.rotation.y = R.yaw0 + R.yawTo(c2at[0], c2at[1], land[0], land[2]); }
      if (t >= T_BOOM + 0.05) R.once("crater", crater);   // a frame after the flash: the carve costs ~50 ms, unseen under the white
      boom(t); items(t); puffs(t);
      R.L(bx, 1.4, bz, glow.position); glow.intensity = 9 * pulse(t, [T_BOOM], 0.18);
      f.white = t >= T_BOOM ? 1 - sstep(T_BOOM + 0.15, T_BOOM + 1.6, t) : 0;
      if (t >= DUR - 0.06) f.white = 1 - sstep(DUR + 0.15, DUR + 1.1, t);
      f.gone = t >= T_BOOM + 0.06 ? [true, true, true, true, true] : null;
      const sil = sstep(tSil, tSil + 0.5, t) * (t < T_BOOM ? 1 : 0);
      f.env = { bake: 1 - 0.2 * sstep(0.2, 1, t) - 0.15 * sil - 0.15 * sstep(T_BOOM, T_BOOM + 1, t), lights: 1 - 0.2 * sil, fogMul: 1 + 0.5 * sstep(1, 3, t) + 1.2 * sstep(T_BOOM, T_BOOM + 0.5, t) * (1 - 0.6 * sstep(T_BOOM + 0.5, T_BOOM + 3, t)) };
      f.vig = [0, 0, 0, 0.3 * sstep(T_TURN, T_FACE, t) + 0.15 * sil + 0.35 * sstep(T_BOOM + 1, T_BOOM + 2, t)];
      f.tints = [[200, 210, 255, 0.06 * sstep(T_TURN, T_FACE, t) * (t < T_BOOM ? 1 : 0)]];
      lungeFx(L, t, f, { stat: 0.6 });
      if (t >= L.t2) f.cut = 0;
    }
    return { dur: DUR, hits, cam, update, sounds, loops, deathSide: side,
      marks: { dread: T_FACE + (behindHit ? -0.5 : 0.35), fake: behindHit ? T_TURN + 0.7 : (tB0 + tB1) / 2, lunge: L.t1 + 0.1, kill: T_BOOM + 1.8 },
      notes: { side, behindHit, farGlimpse, t0: +t0.toFixed(2), boom: +T_BOOM.toFixed(2), dur: +DUR.toFixed(2) } };
  }
};
