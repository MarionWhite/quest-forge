// Lava fall (a failed jump): the last strides to the edge; the take-off catches your toes on the lip and the jump goes
// short and low. You slam into the far wall of the gap and your hands catch the rim, the lava glaring below. You hang.
// A look down at it. Maybe a pull, and the floor beyond comes into view; then the rim crumbles and one hand goes.
// Silence; a pop below; the last fingers slide off the edge. You fall looking up at the rim and your own hands still
// reaching for it, into the lava: the fire, a man screaming for his life, and the view sinks into orange.
import { THREE, clamp, lerp, sstep, pulse, tex } from "./rig.js";
import { shake, hitsOf, particles, mulberry } from "./common.js";
import { silence, deathScream, jit } from "./fnaf.js";
import { gapSite, runUp, firstArms, camBasis } from "./gap.js";

export default {
  death: "Steve tried to swim in lava",
  async build(R) {
    const partTex = await tex("particles");
    const r = mulberry(R.seed * 7 + 3);
    const site = await gapSite(R, "lava");
    const arms = await firstArms(R, { emissive: 0.1 });
    const { z0, z1, surf } = site;

    // ---- the dice -------------------------------------------------------------------------------------------
    const tTake = Math.max(0.4, (z0 - 0.3) / 3.6), tGrab = tTake + 0.42;
    const tLook = tGrab + R.vary(0.9, 0.3);
    const pull = R.chance(0.6);
    const tPull = tLook + R.vary(1.25, 0.25);
    const tCrumb = pull ? tPull + R.vary(0.75, 0.2) : tLook + R.vary(1.4, 0.3);
    const tSil = tCrumb + 0.4, tSlip = tCrumb + R.vary(1.3, 0.35);
    const side = R.pick([-1, 1]);   // the hand that goes first
    const hang = { x: 0, y: -0.32, z: z1 - 0.36 };
    const fallD = hang.y - (surf + 0.15);
    const tLava = tSlip + 0.1 + Math.sqrt(2 * fallD / 32), DUR = tLava + 2.7;
    const hits = hitsOf([[tGrab, 2, side], [tCrumb, 1, side], [tLava, 6, 1], [tLava + 0.45, 4, -1], [tLava + 0.95, 4, 1], [DUR, 3, -1]]);

    // ---- the camera ------------------------------------------------------------------------------------------
    const S0 = runUp(R, tTake, site, { tTake });
    const cam = (t) => {
      let c;
      if (t < tTake) c = runUp(R, t, site, { tTake });
      else if (t < tGrab) {   // the clipped jump: short, low, pitching forward at the far wall
        const k = (t - tTake) / (tGrab - tTake);
        c = { x: lerp(S0.x, hang.x, k), z: lerp(S0.z, hang.z, k), y: lerp(S0.y, hang.y, k * k) + 0.3 * Math.sin(k * Math.PI) * (1 - k), yaw: S0.yaw * (1 - k), pitch: lerp(S0.pitch, -0.35, k), roll: 0.12 * Math.sin(k * Math.PI) * side, fov: S0.fov + 5 * Math.sin(k * Math.PI) };
      } else if (t < tSlip) {   // hanging off the rim
        c = { x: hang.x, y: hang.y, z: hang.z, yaw: 0, pitch: 0.32, roll: 0, fov: S0.fov };
        c.pitch = lerp(0.32, -0.4, Math.exp(-(t - tGrab) / 0.16));   // the slam, then up at the hands
        const ld = sstep(tLook, tLook + 0.35, t) * (1 - sstep(tLook + 0.85, tLook + 1.15, t));
        c.pitch = lerp(c.pitch, -1.2, ld);   // the look down
        if (pull) { const pk = sstep(tPull, tCrumb - 0.05, t) * (1 - sstep(tCrumb, tCrumb + 0.1, t)); c.y += 0.36 * pk; c.pitch -= 0.3 * pk; c.z += 0.08 * pk; }
        const one = sstep(tCrumb, tCrumb + 0.15, t), sw = Math.sin((t - tCrumb) * 3.2);
        c.y -= 0.14 * one; c.roll += one * (0.2 * side + 0.07 * sw); c.x += one * side * 0.06 * sw; c.yaw += one * 0.1 * side * Math.sin((t - tCrumb) * 2.1); c.pitch += 0.12 * one;
        c.y -= 0.05 * sstep(tSlip - 0.5, tSlip, t);   // the fingers sliding
      } else {   // the fall, looking up at the rim and your hands; then in it
        const d = t - tSlip;
        c = { x: hang.x, y: Math.max(hang.y - 0.06 - 16 * Math.max(0, d - 0.1) ** 2, surf + 0.15), z: hang.z - 0.3 * clamp(d / 0.45), yaw: 0.1 * side, pitch: lerp(0.45, 1.1, sstep(tSlip, tSlip + 0.3, t)), roll: 0.22 * side, fov: S0.fov + 7 * sstep(tSlip, tLava, t) };
        if (t >= tLava) {
          const sk = t - tLava;
          c.y = surf + 0.15 - 0.32 * Math.min(1, sk / 0.25) - 0.22 * sk;
          c.pitch = lerp(1.1, 0.3, sstep(tLava, tLava + 1.6, t)) + 0.08 * jit(t, 3, 7);
          c.roll = 0.22 * side + 0.22 * Math.sin(sk * 1.4);
          c.fov = S0.fov - 5 * sstep(tLava, tLava + 2, t);
        }
      }
      c.near = 0.02;
      return shake(c, t, 0.0015 + 0.035 * pulse(t, [tGrab, tLava], 0.18) + 0.015 * pulse(t, [tCrumb, tTake], 0.15) + 0.006 * sstep(tGrab, tGrab + 0.3, t) * (t < tSlip ? 1 : 0) + 0.02 * (t > tLava ? 1 : 0), 4);
    };

    // ---- particles: embers off the lava, gravel off the crumbling rim, the splash ----------------------------------
    const specs = [];
    for (let i = 0; i < 46; i++) specs.push({ t0: r() * DUR, at: [site.x0 + r() * (site.x1 - site.x0), surf + 0.05, site.z0 + r() * (z1 - site.z0)], v: [(r() - 0.5) * 0.3, 0.8 + r() * 0.8, (r() - 0.5) * 0.3], life: 1.4, size: 0.05, tile: 49, color: [1, 0.55, 0.15], grav: -0.2, fog: false, add: true });
    for (let i = 0; i < 18; i++) specs.push({ t0: tCrumb + r() * 0.15, at: [side * 0.28 + (r() - 0.5) * 0.2, 0.0, z1 + (r() - 0.5) * 0.1], v: [(r() - 0.5) * 0.6, 0.3 + r() * 0.5, -0.4 - r() * 0.4], life: 0.9, size: 0.04 + r() * 0.03, tile: Math.floor(r() * 4), color: [0.45, 0.42, 0.4], grav: 12, fog: true });
    for (let i = 0; i < 40; i++) specs.push({ t0: tLava + r() * 0.06, at: [(r() - 0.5) * 0.8, surf + 0.05, hang.z - 0.3 + (r() - 0.5) * 0.8], v: [(r() - 0.5) * 2.5, 2 + r() * 2.5, (r() - 0.5) * 2.5], life: 0.8, size: 0.07, tile: 49, color: [1, 0.6, 0.2], grav: 9, fog: false, add: true });
    const fx = particles(R, partTex, specs);
    const glow = R.ownLight(R.light(0xff6a10, 0, 9, 1.3));

    // ---- sound --------------------------------------------------------------------------------------------
    const strides = [];
    for (let s = 0.12; s < tTake - 0.1; s += 1 / 4.2) strides.push([s, "step.stone", { volume: 0.55, pitch: 0.95 + 0.1 * (strides.length % 2) }]);
    const pops = [];
    for (let s = tTake; s < tSil; s += R.vary(0.8, 0.4)) pops.push([s, "liquid.lavapop", { at: [r() * 2 - 1, surf, (site.z0 + z1) / 2], volume: 0.4 }]);
    const sounds = [
      ...strides,
      [tTake - 0.02, "step.stone", { volume: 0.8, pitch: 0.8 }], [tTake, "dig.stone", { volume: 0.7, pitch: 1.3 }],
      [tTake + 0.25, "liquid.lava", { at: [0, surf, (site.z0 + z1) / 2], volume: 0.8 }],
      [tGrab, "qf.scare.hit", { volume: 0.9 }], [tGrab + 0.01, "game.player.hurt"], [tGrab + 0.02, "dig.stone", { volume: 1, pitch: 0.8 }], [tGrab + 0.05, "step.gravel", { volume: 0.7 }],
      ...pops,
      [tLook + 0.2, "liquid.lava", { at: [0, surf, hang.z], volume: 0.9 }],
      ...(pull ? [[tPull + 0.1, "step.stone", { volume: 0.5, pitch: 0.7 }], [tPull + 0.45, "dig.stone", { volume: 0.4, pitch: 1.1 }]] : []),
      [tCrumb - 0.02, "qf.scare.stinger", { volume: 0.9 }], [tCrumb, "dig.gravel", { volume: 1.1 }], [tCrumb + 0.03, "step.gravel", { volume: 0.9, pitch: 0.8 }], [tCrumb + 0.05, "game.player.hurt", { volume: 0.6 }],
      silence(tSil, { fade: 0.25 }),
      [tSil + R.vary(0.45, 0.3), "liquid.lavapop", { at: [0, surf, hang.z], volume: 0.3, pitch: 0.8 }],
      [tSlip - 0.45, "dig.stone", { volume: 0.35, pitch: 1.7 }], [tSlip - 0.2, "dig.stone", { volume: 0.45, pitch: 1.6 }],
      [tSlip, "qf.scare.fall", { volume: 1.1 }], [tSlip + 0.01, "qf.scare.stinger", { volume: 1.3 }], [tSlip + 0.02, "qf.scare.jumpscreech", { volume: 0.9 }],
      [tLava, "qf.scare.hit", { volume: 1.3 }], [tLava + 0.01, "random.fizz", { volume: 1.5 }], [tLava + 0.02, "fire.ignite", { volume: 1.3 }], [tLava + 0.03, "liquid.lavapop", { volume: 1.2 }],
      ...deathScream(tLava + 0.04, { volume: 1.45 }),
      ...hits.slice(3).map((h) => [h.t, "game.player.hurt"]),
      [tLava + 0.35, "@muffle", { hz: 380, s: DUR - tLava + 2 }],
      ...deathScream(tLava + 1.25, { volume: 1.2, under: false }),
      [DUR, "game.player.die"]
    ];
    const loops = [
      [tGrab, tSil, "qf.scare.heartbeat", { volume: 0.7, pitch: 1.25 }],
      [tGrab + 0.1, tSil, "qf.scare.breath", { volume: 0.6, fadeIn: 0.2, fadeOut: 0.1 }],
      [tLava, DUR + 0.3, "fire.fire", { volume: 1 }],
      [tLava + 0.1, DUR + 0.3, "qf.scare.heartbeat", { volume: 0.9, pitch: 1.6 }]
    ];

    // ---- the frame ------------------------------------------------------------------------------------------
    const rim = (sx, slide = 0) => R.L(sx * 0.26, 0.04 - 0.12 * slide, z1 + 0.13 - 0.2 * slide, new THREE.Vector3());
    function update(t, f) {
      if (t >= 0) R.once("lavafall-carve", site.carve);
      site.animate(t);
      fx(t);
      // The arms: up and out as you go short; on the rim; one slides off; the other; reaching up as you fall.
      const B = camBasis(R);
      const sh = (s) => B.p.clone().addScaledVector(B.r, s * 0.3).addScaledVector(B.u, -0.3).addScaledVector(B.f, 0.08);
      for (const [i, s] of [[0, -1], [1, 1]]) {
        const first = s === side;
        if (t < tGrab - 0.22) { arms.set(i, null); continue; }
        const S = sh(s);
        if (t < tGrab) { const k = sstep(tGrab - 0.22, tGrab, t); arms.set(i, S, S.clone().addScaledVector(B.f, 0.4).addScaledVector(B.u, 0.2).lerp(rim(s), k)); continue; }
        const goes = first ? tCrumb : tSlip;
        if (t < goes) {
          const slide = first ? 0 : 0.6 * sstep(tSlip - 0.6, tSlip, t);
          const H = rim(s, slide); H.y += 0.02 * jit(t, 7 + i, 9) * (t > tCrumb ? 1 : 0.3);
          arms.set(i, S, H); continue;
        }
        // gone: reaching up after the rim (flailing), until it sinks
        if (t > tLava + 0.5) { arms.set(i, null); continue; }
        const H = S.clone().addScaledVector(B.u, 0.62).addScaledVector(B.f, 0.25).addScaledVector(B.r, s * 0.12 + 0.08 * jit(t, 11 + i, 6));
        arms.set(i, S, H);
      }
      // Light: the lava's glare from below, flickering; inside it, everything.
      const hk = sstep(tTake, tGrab, t), inL = sstep(tLava - 0.02, tLava + 0.1, t);
      R.L(0, surf + 0.7, (site.z0 + z1) / 2, glow.position);
      glow.intensity = (1.6 + 1.6 * hk + 0.5 * jit(t, 21, 6)) * (1 - 0.6 * inL);
      arms.mat.emissiveIntensity = 0.08 + 0.2 * hk;
      const sil = sstep(tSil, tSil + 0.3, t) * (1 - inL);
      f.env = { bake: (1 - 0.15 * sstep(0.2, 1, t) - 0.25 * sil) * (1 - 0.6 * inL), lights: (1 - 0.25 * sil) * (1 - inL), fogMul: 1 + 0.5 * hk, fogAdd: 2.6 * inL, fog: inL > 0 ? [0.8, 0.25, 0.02, 1] : [0.3, 0.09, 0.02, 0.35 * hk] };
      f.tints = [[255, 120, 30, 0.06 * hk * (1 - inL)], [255, 70, 0, (0.3 + 0.25 * sstep(tLava, DUR, t)) * inL]];
      f.vig = [60, 12, 0, 0.3 + 0.25 * hk + 0.35 * sil + 0.3 * inL]; f.vigR = 0.9 - 0.15 * sil;
      f.fire = inL;
      f.black = 0.45 * sstep(DUR - 0.5, DUR + 0.6, t);
    }
    return { dur: DUR, hits, cam, update, sounds, loops, deathSide: side,
      marks: { dread: tLook + 0.5, fake: pull ? tCrumb - 0.1 : tCrumb + 0.05, lunge: tSlip + 0.2, kill: tLava + 0.5 },
      notes: { own: site.own, w: site.w, z0: +z0.toFixed(2), z1: +z1.toFixed(2), pull, t0: +tSlip.toFixed(2), dur: +DUR.toFixed(2) } };
  }
};
