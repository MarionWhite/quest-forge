// Drowned grab (a failed jump): the last strides; the jump lands short, in the water, with a splash. Under, everything
// is blue and thick and far away; you sink, turn, look down into the murk (and maybe, for a frame, something looks
// back). You kick up toward the light, nearly there; then a hand closes on your ankle and yanks. You look down: a
// drowned face is coming up out of the dark, and in the one moment the sound comes clear it is at your face, jaw wide,
// with the screech. It bites; it drags you down; bubbles, a man screaming under water, blood blooming in the blue, the
// light at the top getting small.
import { THREE, clamp, lerp, sstep, pulse, tex } from "./rig.js";
import { shake, hitsOf, particles, mulberry, glowEyes, mcRot } from "./common.js";
import { lunge, lungeFx, screech, splitJaw, faceAnchor, boxOf, deathScream, glimpse, jit } from "./fnaf.js";
import { gapSite, runUp } from "./gap.js";

export default {
  death: "Steve drowned",
  async build(R) {
    const partTex = await tex("particles");
    const r = mulberry(R.seed * 11 + 5);
    const DEEP = 6;
    const site = await gapSite(R, "water", { deep: DEEP });
    const { z0, z1, surf } = site;
    const bottom = surf - DEEP - 0.75;

    // The drowned: a zombie gone blue-green and soft in the water, lit eyes, the jaw that opens.
    const Z = R.mob("Zombie", { amb: [0.16, 0.16, 0.16], own: true });
    Z.root.traverse((o) => { if (o.isMesh && o.material && o.material.color) { o.material.color.setRGB(0.55, 0.85, 0.8); if (o.material.emissive) o.material.emissive.setRGB(0.5, 0.8, 0.78); } });
    Z.anim(0, 0, {}); R.place(Z, 0, -9, 4, Math.PI);
    const jaw = splitJaw(Z, [{ part: Z.parts.head, box: boxOf("zombie", "bipedHead"), rows: 2 }, { part: Z.parts.headwear, box: boxOf("zombie", "bipedHeadwear"), rows: 2 }], { mouth: 0x020806, tongue: 0x1a0606 });
    const eyes = glowEyes(R, Z, [[-2, -3.5, -4.07, 0.8, 0.8], [2, -3.5, -4.07, 0.8, 0.8]], [0.55, 1, 0.95], { halo: 0.18, glow: 0.5 });
    const anchor = faceAnchor(Z, Z.parts.head, boxOf("zombie", "bipedHead")); anchor.y -= 0.07;

    // ---- the dice -------------------------------------------------------------------------------------------
    const tTake = Math.max(0.4, (z0 - 0.3) / 3.6), tSplash = tTake + 0.42;
    const zS = z0 + Math.min(0.95, (z1 - z0) * 0.4);
    const ySink = surf - 1.7;
    const tSwim = tSplash + R.vary(1.9, 0.3);
    const peek = R.chance(0.45), tGl = tSplash + R.vary(1.25, 0.2);   // a frame of it, far down in the murk
    const tGrab = tSwim + R.vary(1.6, 0.3);
    const t0 = tGrab + R.vary(0.65, 0.35);
    const L = lunge(R, Z, { t0, rush: R.vary(0.24, 0.15), hold: R.vary(0.6, 0.15), dist: 0.36, anchor, seed: 13, rise: 0.5 });
    const tK = L.t3, tUp = tK + 0.85, DUR = tK + 3.2;
    const hits = hitsOf([[tGrab, 2, 1], [tK, 5, -1], [tK + 0.45, 4, 1], [tK + 1.0, 3, -1], [tK + 1.7, 3, 1], [DUR, 3, -1]]);

    // ---- the camera ------------------------------------------------------------------------------------------
    const S0 = runUp(R, tTake, site, { tTake });
    const yAt = (t) => {   // the eye's height under water
      if (t < tSwim) return surf - 1.7 * (1 - Math.exp(-(t - tSplash) / 0.35));
      const yS = surf - 1.7 * (1 - Math.exp(-(tSwim - tSplash) / 0.35));
      let y = lerp(yS, surf - 0.72, sstep(tSwim, tGrab + 0.2, t)) + 0.05 * Math.sin((t - tSwim) * 7) * (t < tGrab ? 1 : 0);
      if (t >= tGrab) { const yG = lerp(yS, surf - 0.72, sstep(tSwim, tGrab + 0.2, tGrab)); y = yG - 0.55 * sstep(tGrab, tGrab + 0.12, t) - 0.25 * (t - tGrab); }
      if (t >= tK) { const yk = yAt(tK - 1e-4); y = Math.max(bottom + 0.6, yk - 1.7 * (t - tK)); }
      return y;
    };
    const cam = (t) => {
      let c;
      if (t < tTake) c = runUp(R, t, site, { tTake });
      else if (t < tSplash) {   // short: the water rushing up
        const k = (t - tTake) / (tSplash - tTake);
        c = { x: lerp(S0.x, 0, k), z: lerp(S0.z, zS, k), y: lerp(S0.y, surf, k * k) + 0.35 * Math.sin(k * Math.PI) * (1 - k), yaw: S0.yaw * (1 - k), pitch: lerp(S0.pitch, -0.6, k), roll: 0, fov: S0.fov + 4 * Math.sin(k * Math.PI) };
      } else {
        const d = t - tSplash;
        c = { x: 0.15 * Math.sin(d * 0.7), y: yAt(t), z: zS + 0.1 * Math.sin(d * 0.5), yaw: 0, pitch: lerp(-0.6, -0.25, sstep(tSplash, tSplash + 0.9, t)), roll: 0.06 * Math.sin(d * 1.1), fov: S0.fov - 4 };
        // looking round in the murk, down into it
        const lk = sstep(tSplash + 0.5, tSplash + 1.0, t) * (1 - sstep(tSwim - 0.2, tSwim + 0.3, t));
        c.yaw += 0.5 * Math.sin((t - tSplash - 0.5) * 1.3) * lk; c.pitch -= 0.35 * lk;
        // up at the light, kicking
        const up = sstep(tSwim, tSwim + 0.5, t);
        c.pitch = lerp(c.pitch, 1.05 + 0.05 * Math.sin(t * 7), up);
        // the yank: down, the head snapped round to look at what has you
        if (t >= tGrab) {
          const g = 1 - Math.pow(1 - clamp((t - tGrab - 0.05) / 0.28), 5);
          c.pitch = lerp(c.pitch, -1.28, g); c.roll += 0.25 * Math.exp(-(t - tGrab) / 0.3) * Math.sin((t - tGrab) * 20);
        }
        if (t >= tUp) {   // dragged down, the head thrown back: the light at the top, going small
          const u = sstep(tUp, tUp + 0.5, t);
          c.pitch = lerp(c.pitch, 1.15, u); c.roll += 0.3 * u * Math.sin((t - tUp) * 2);
        }
      }
      c.near = 0.02;
      c.fov += 9 * pulse(t, [L.t1], 0.12);
      return shake(c, t, 0.0015 + 0.03 * pulse(t, [tSplash, tGrab], 0.2) + L.shake(t) + 0.012 * pulse(t, hits.slice(2).map((h) => h.t), 0.2), 8);
    };

    // ---- particles: the splash, bubbles, blood in the water -------------------------------------------------------
    const specs = [];
    for (let i = 0; i < 30; i++) specs.push({ t0: tSplash + r() * 0.05, at: [(r() - 0.5) * 1.0, surf + 0.05, zS + (r() - 0.5) * 1.0], v: [(r() - 0.5) * 2, 2 + r() * 2.5, (r() - 0.5) * 2], life: 0.8, size: 0.07, tile: 19 + Math.floor(r() * 4), color: [0.55, 0.7, 1], grav: 9, fog: true });
    const bubble = (tt, n, spread, at) => { for (let i = 0; i < n; i++) specs.push({ t0: tt + r() * spread, at: [at[0] + (r() - 0.5) * 0.5, at[1] + (r() - 0.5) * 0.3, at[2] + (r() - 0.5) * 0.5], v: [(r() - 0.5) * 0.3, 0.9 + r() * 0.8, (r() - 0.5) * 0.3], life: 1.6, size: 0.05 + r() * 0.05, tile: 32, color: [0.85, 0.95, 1], grav: -0.4, fog: false }); };
    bubble(tSplash, 40, 0.5, [0, surf - 0.8, zS]);
    for (let tt = tSplash + 0.6; tt < tGrab; tt += R.vary(0.7, 0.4)) bubble(tt, 3, 0.15, [0, yAt(tt) - 0.1, zS + 0.25]);
    bubble(tGrab + 0.05, 28, 0.25, [0, yAt(tGrab + 0.1) - 0.15, zS + 0.2]);
    for (const tt of [tK + 0.1, tK + 0.6, tK + 1.25, tK + 1.9]) bubble(tt, 18, 0.2, [0, yAt(tt) - 0.1, zS + 0.2]);
    for (let i = 0; i < 46; i++) { const tt = tK - 0.05 + r() * 2.6; specs.push({ t0: tt, at: [(r() - 0.5) * 1.2, yAt(tt) - 0.3 + (r() - 0.5) * 0.8, zS + 0.3 + (r() - 0.5) * 1.0], v: [(r() - 0.5) * 0.25, 0.15 + r() * 0.3, (r() - 0.5) * 0.25], life: 2.4, size: 0.18 + r() * 0.3, tile: Math.floor(r() * 8), color: [0.42, 0.0, 0.0], grav: -0.05, fog: false }); }
    const fx = particles(R, partTex, specs);
    const sky = R.ownLight(R.light(0x9cc8ff, 0, 9, 1.2));
    const lamp = R.ownLight(R.light(0x6fc0c8, 0, 3, 1.6));

    // ---- sound --------------------------------------------------------------------------------------------
    const strides = [];
    for (let s = 0.12; s < tTake - 0.1; s += 1 / 4.2) strides.push([s, "step.stone", { volume: 0.55, pitch: 0.95 + 0.1 * (strides.length % 2) }]);
    const strokes = [];
    for (let s = tSwim + 0.1; s < tGrab - 0.1; s += 0.5) strokes.push([s, "game.player.swim", { volume: 0.7, pitch: 0.8 }]);
    // Held under: muffle() ramps back open over its time, so it is struck again every 0.4 s (500-800 Hz throughout).
    const held = (a, b, hz) => { const out = []; for (let s = a; s < b; s += 0.4) out.push([s, "@muffle", { hz, s: 3 }]); return out; };
    const S2 = screech(L, [["mob.zombie.say", { pitch: 0.5 }], ["mob.zombie.hurt", { pitch: 0.55, volume: 1.2 }]]);
    const sounds = [
      ...strides,
      [tTake - 0.02, "step.stone", { volume: 0.8, pitch: 0.8 }], [tTake, "dig.stone", { volume: 0.6, pitch: 1.3 }],
      [tSplash, "game.player.swim.splash", { volume: 1.2 }], [tSplash + 0.01, "random.splash", { volume: 1 }], [tSplash + 0.02, "liquid.splash", { volume: 0.9 }],
      ...held(tSplash + 0.04, t0 - 0.1, 480),
      [t0 - 0.03, "@muffle", { hz: 19000, s: 0.05 }],   // the one moment the sound comes clear
      [tSplash + 0.5, "liquid.water", { volume: 0.6 }],
      ...(peek ? [[tGl + 0.02, "mob.zombie.say", { volume: 0.35, pitch: 0.45 }]] : []),
      ...strokes,
      [tGrab, "qf.scare.hit", { volume: 1.2 }], [tGrab + 0.01, "qf.scare.stinger", { volume: 0.9 }], [tGrab + 0.02, "game.player.hurt"],
      [tGrab + 0.06, "qf.scare.underwater", { volume: 1.4 }], [tGrab + 0.2, "mob.zombie.say", { volume: 0.8, pitch: 0.5 }],
      ...S2.sounds,
      ...held(tK + 0.02, DUR + 0.5, 420),
      [tK + 0.05, "qf.scare.crunch", { volume: 1.1 }], [tK + 0.08, "qf.scare.gore", { volume: 1 }],
      ...deathScream(tK + 0.15, { volume: 1.3 }),
      [tK + 0.45, "qf.scare.crunch", { volume: 1 }], [tK + 1.0, "qf.scare.gore", { volume: 0.9 }],
      [tK + 0.9, "qf.scare.underwater", { volume: 1.4 }], [tK + 1.9, "qf.scare.underwater", { volume: 1.2 }],
      ...hits.slice(1).map((h) => [h.t, "game.player.hurt", { volume: 0.8 }]),
      [DUR, "game.player.die"]
    ];
    const loops = [
      [tSplash + 0.1, tGrab, "qf.scare.heartbeat", { volume: 0.6, pitch: 1.1 }],
      [tSplash + 0.2, t0 - 0.05, "qf.scare.drone", { volume: 0.45, fadeIn: 1.0, fadeOut: 0.03, bus: "sfx", pitch: 0.8 }],
      [tGrab, t0 - 0.05, "qf.scare.heartbeat", { volume: 0.9, pitch: 1.5, fadeOut: 0.02 }],
      ...S2.loops,
      [tK + 0.1, DUR + 0.2, "qf.scare.heartbeat", { volume: 0.9, pitch: 1.6 }]
    ];

    // ---- the frame ------------------------------------------------------------------------------------------
    const air = (t) => (t < tSplash ? null : clamp(1 - (t - tSplash) / (tGrab - tSplash + 0.6) * 0.75 - 0.6 * sstep(tGrab, tGrab + 0.3, t) - sstep(tK, tK + 1.2, t)));
    function update(t, f) {
      if (t >= 0) R.once("drowned-carve", site.carve);
      site.animate(t);
      fx(t);
      const cl = R.toLocal(R.camera.position);
      // The drowned: far down (a frame of it), then under you holding your ankle, then in your face, then dragging.
      let vis = false, x = cl.x, y = cl.y - 3.4, z = cl.z + 0.6, open = 0, own = 0.16, armUp = true;
      const look = -0.9;
      if (peek && glimpse(t, [tGl, tGl + 0.11], 0.05)) { vis = true; y = cl.y - 3.25; z = cl.z + 2.0; own = 0.2; }   // in the murk, in view
      if (t >= tGrab && t < t0) { vis = true; y = cl.y - 1.15 - 1.75; z = cl.z + 0.3; own = 0.14 + 0.1 * sstep(tGrab, t0, t); open = 0.25 * sstep(tGrab + 0.2, t0, t) + 0.1 * Math.max(0, jit(t, 3, 12)); }
      if (t >= t0) { vis = true; y = cl.y - 1.15 - 1.75; z = cl.z + 0.3; own = 0.35; open = t < tK ? sstep(t0, L.t1, t) * (0.85 + 0.15 * jit(t, 7)) : 0.4 + 0.45 * Math.max(0, Math.sin((t - tK) * 9)); armUp = false; }
      if (t >= tUp) { y = cl.y - 2.3; z = cl.z + 0.15; own = 0.12; armUp = true; }
      Z.pivot.visible = vis;
      R.place(Z, x, y, z, R.yawTo(x, z, cl.x, cl.z));
      Z.anim(t, 0, {});
      if (Z.parts.head) mcRot(Z.parts.head, look, 0, 0);
      if (armUp) { if (Z.parts.rightArm) mcRot(Z.parts.rightArm, -2.9 + 0.1 * Math.sin(t * 5), 0, 0.1); if (Z.parts.leftArm) mcRot(Z.parts.leftArm, -2.7 + 0.1 * Math.sin(t * 4), 0, -0.1); }
      jaw.set(open);
      if (t >= t0 && t < tUp) L.apply(t);
      Z.setOwn(own);
      eyes(vis ? 1 : 0);
      // Light: from the top of the shaft (the corridor's light through the water), and a dim one on its face.
      R.L(0, surf + 0.8, (site.z0 + z1) / 2, sky.position); sky.intensity = t >= tSplash ? 2.2 * (1 - 0.6 * sstep(tK, DUR, t)) : 0;
      R.L(cl.x, cl.y - 0.4, cl.z + 0.4, lamp.position); lamp.intensity = t >= tGrab ? 0.9 : 0;
      // Under water: thick blue, far away; the blood blooming red; the light going.
      const uw = sstep(tSplash - 0.02, tSplash + 0.06, t), blood = sstep(tK, tK + 2.2, t);
      f.env = { bake: lerp(1, 0.5, uw) * (1 - 0.4 * blood), lights: 1 - 0.5 * uw, fogMul: 1, fogAdd: 0.55 * uw + 0.4 * blood, fog: uw > 0 ? [lerp(0.03, 0.2, blood), lerp(0.12, 0.02, blood), lerp(0.3, 0.04, blood), 1] : [0, 0, 0, 0] };
      f.tints = [[20, 70, 150, 0.32 * uw * (1 - blood)], [120, 0, 0, 0.42 * blood], [190, 0, 0, 0.3 * pulse(t, [tK, tK + 0.45, tK + 1.0], 0.25)]];
      f.vig = [0, 10, 30, 0.3 + 0.3 * uw + 0.3 * blood]; f.vigR = 0.9 - 0.2 * blood;
      f.air = air(t);
      f.black = 0.5 * sstep(DUR - 0.6, DUR + 0.5, t);
      lungeFx(L, t, f);
    }
    return { dur: DUR, hits, cam, update, sounds, loops, deathSide: 1,
      marks: { dread: tSplash + 1.3, fake: peek ? tGl + 0.01 : tSwim + 0.8, lunge: L.t1 + 0.1, kill: tK + 1.4 },
      notes: { own: site.own, w: site.w, z0: +z0.toFixed(2), peek, t0: +t0.toFixed(2), dur: +DUR.toFixed(2) } };
  }
};
