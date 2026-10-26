// Slime (piston trap): the floor goes and you drop into a dark pit, into a skin of green slime water. Quiet. Up in
// the hole the light goes out: something square is squeezing through. Wet sounds. Then the light comes back, and
// nothing has come down. Silence; a drip. Then its face is on you, from the hole straight down or out of the dark of
// the pit, eyes lit, mouth stretched wide, with the screech; and you are inside it. The world is green and far away,
// the sound goes thick, the air runs out, a drowned scream, and it squeezes. Small slimes bud off it and hop away.
import { THREE, clamp, lerp, sstep, pulse, tex, loadImg } from "./rig.js";
import { settle, shake, hitsOf, particles, mulberry, glowEyes } from "./common.js";
import { pistonTrap, GRAV } from "./piston.js";
import { lunge, lungeFx, screech, faceAnchor, boxOf, silence, deathScream, splitJaw, jit } from "./fnaf.js";

export default {
  death: "Steve was slain by Slime",
  async build(R) {
    const partTex = await tex("particles");
    const r = mulberry(R.seed * 13 + 9);
    const click = 0.95 + R.vary(0.3, 0.5);
    const trap = await pistonTrap(R, { click, open: click + R.vary(0.75, 0.35), D: 7, ri: 3, rk: 3 });
    const { roomBox: rb, loc, hole } = trap;
    const Dp = trap.D, y0 = -Dp;
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

    const SIZE = 4;
    const S = R.mob("Slime", { size: SIZE, amb: [0.06, 0.09, 0.05], own: true });
    const small = [0, 1, 2].map(() => R.mob("Slime", { size: 1, amb: [0.08, 0.12, 0.07] }));
    S.anim(0, 0, {}); R.place(S, 0, 0, 4, Math.PI);
    const core = S.parts.slimeBodies;
    const anchor = faceAnchor(S, core, boxOf("slimeInner", "slimeBodies")); anchor.y -= 0.2;   // eyes and maw both in
    const jelly = S.mats[1] || null, jellyOp = jelly ? jelly.opacity : 1;
    // The core's mouth: the bottom three rows of the inner cube drop open inside the jelly (the 1 px mouth goes).
    const jaw = splitJaw(S, [{ part: core, box: boxOf("slimeInner", "slimeBodies"), rows: 3 }], { nTeeth: 0, max: 0.9, mouth: 0x000000, tongue: 0x0b1606 });
    S.parts.head = core;
    const eyes = glowEyes(R, S, [[-2.25, 19, -3.52, 0.6, 0.6], [2.25, 19, -3.52, 0.6, 0.6]], [0.9, 1, 0.6], { halo: 0.9, glow: 0 });
    // ---- the dice -------------------------------------------------------------------------------------------
    const tDark = trap.land + R.vary(1.3, 0.35), tLight = tDark + R.vary(1.1, 0.35);
    const tSil = tLight + 0.15, tDrip = tLight + R.vary(0.7, 0.4), t0 = tLight + R.vary(1.7, 0.4);
    const fromHole = R.chance(0.5);
    const me = { x: hole.x, z: hole.z };
    const farZ = loc(rb.i0, -Dp, rb.k1).z + 0.5;
    const side = { x: me.x + R.pick([-1, 1]) * 0.6, z: me.z + clamp(farZ - 1.1 - me.z, 1.4, 2.0) };   // out of the dark of the pit
    const start = fromHole ? { x: hole.x, y: 0.2, z: hole.z } : { x: side.x, y: y0, z: side.z };
    const L = lunge(R, S, { t0, rush: R.vary(fromHole ? 0.26 : 0.22, 0.12), hold: R.vary(0.6, 0.15), dist: 1.45, anchor, seed: 29, rise: fromHole ? -0.6 : 0 });
    const tK = L.t3, DUR = tK + R.vary(2.6, 0.1), T_SPLIT = tK + 0.9;
    const engulf = { x: me.x + 0.55, z: me.z + 0.62 };
    const hits = hitsOf([[trap.land, 4, 1], [tK + 0.02, 4, -1], [tK + 0.55, 4, 1], [tK + 1.05, 3, -1], [tK + 1.6, 2, 1], [DUR, 3, -1]]);

    const cam = (t) => {
      const s = settle(R, t, 0.9);
      const k = sstep(0.8, 1.3, t);
      let c = { x: s.x * (1 - k), y: s.y, z: s.z * (1 - k), yaw: lerp(s.yaw, 0, k), pitch: lerp(s.pitch, -0.02, k), roll: 0, fov: s.fov, near: t >= t0 && t < tK ? 0.02 : undefined };
      c = trap.cam(t, c);
      if (t > trap.land + 0.3) {
        // Up at the hole as it goes dark; held there; the light back; down, round the dark of the pit.
        const up = sstep(trap.land + 0.4, tDark - 0.1, t) * (1 - sstep(tLight + 0.2, tLight + 0.9, t));
        const look = sstep(tLight + 0.6, t0, t);
        c.pitch = lerp(lerp(-0.25, 1.3, up), -0.1, look);
        c.yaw = lerp(0, 0.4 * Math.sin((t - tLight) * 0.9), look);
        if (t >= t0) { const kk = sstep(t0, L.t1, t); c.pitch = lerp(c.pitch, fromHole ? 0.5 : 0.0, kk); c.yaw = lerp(c.yaw, fromHole ? 0 : R.yawTo(me.x, me.z, side.x, side.z) * 0.5, kk); }
      }
      if (t >= tK) {   // inside it: pressed down into the slime water
        const k2 = sstep(tK, tK + 0.25, t);
        c.y = lerp(c.y, y0 + 0.75, k2); c.pitch = lerp(c.pitch, 0.25, k2); c.yaw = lerp(c.yaw, -0.2, k2); c.roll = lerp(c.roll, -0.25, k2);
        c.fov = s.fov - 8 * k2;
      }
      c.fov += 10 * pulse(t, [L.t1], 0.12);
      return shake(c, t, 0.0015 + L.shake(t) + 0.03 * pulse(t, [tK], 0.2) + 0.012 * pulse(t, hits.map((h) => h.t), 0.18), 5);
    };

    const bubbles = [], drops = [];
    for (let i = 0; i < 40; i++) bubbles.push({ t0: tK + 0.1 + r() * (DUR - tK), at: [me.x + (r() - 0.2) * 0.8, y0 + 0.5 + r() * 0.5, me.z + 0.2 + r() * 0.7], v: [0, 0.6 + r() * 0.5, 0], life: 0.9, size: 0.05 + r() * 0.04, tile: 32, color: [0.75, 0.95, 0.7], grav: -0.3, fog: false });
    for (const [tt, x, z, n] of [[trap.land, me.x, me.z, 22], [tK, engulf.x, engulf.z, 26]]) for (let i = 0; i < n; i++) drops.push({ t0: tt + r() * 0.05, at: [x + (r() - 0.5) * 1.2, y0 + 0.2, z + (r() - 0.5) * 1.2], v: [(r() - 0.5) * 2, 2 + r() * 2, (r() - 0.5) * 2], life: 0.8, size: 0.06, tile: 19 + Math.floor(r() * 4), color: [0.45, 0.85, 0.35], grav: 9, fog: false });
    for (let i = 0; i < 6; i++) drops.push({ t0: tDark + 0.2 + i * R.vary(0.25, 0.3), at: [hole.x + (r() - 0.5) * 0.6, -0.6, hole.z + (r() - 0.5) * 0.6], v: [0, -1, 0], life: 0.9, size: 0.05, tile: 19, color: [0.45, 0.85, 0.35], grav: 12, fog: false });
    const fx = particles(R, partTex, [...bubbles, ...drops]);
    const S2 = screech(L, [["mob.slime.big", { pitch: 0.45 }], ["mob.slime.attack", { pitch: 0.5, volume: 1.2 }]]);
    const sounds = [
      ...trap.sounds,
      [trap.land + 0.01, "game.player.swim.splash", { volume: 1 }],
      [trap.land + 0.6, "qf.scare.whisper", { volume: 0.25 }],
      [tDark - 0.15, "mob.slime.big", { at: [hole.x, 0.5, hole.z], volume: 0.7, pitch: 0.7 }],
      [tDark + 0.45, "mob.slime.big", { at: [hole.x, 0, hole.z], volume: 0.8, pitch: 0.6 }],
      [tLight - 0.1, "mob.slime.small", { at: [hole.x, 0.8, hole.z], volume: 0.4, pitch: 0.6 }],
      silence(tSil),
      [tDrip, "random.splash", { at: [side.x, y0, side.z], volume: 0.12, pitch: 1.8 }],
      ...S2.sounds,
      [tK + 0.01, "random.splash", { volume: 1 }],
      [tK + 0.05, "@muffle", { hz: 220, s: DUR - tK + 2 }],
      ...hits.slice(2).map((h) => [h.t, "game.player.hurt"]),
      ...hits.slice(2).map((h, i) => [h.t + 0.02, "mob.slime.attack", { volume: 0.7, pitch: 0.6 + 0.05 * i }]),
      ...[0, 1, 2].map((i) => [T_SPLIT + i * 0.18, "mob.slime.small", { at: [engulf.x, y0 + 0.5, engulf.z], volume: 0.8, pitch: 1 + 0.1 * i }]),
      [tK + 0.4, "qf.scare.underwater", { volume: 1.3 }],
      [DUR - 0.9, "qf.scare.underwater", { volume: 1.2 }],
      [DUR, "game.player.die"]
    ];
    const loops = [
      [0.5, tSil, "qf.scare.heartbeat", { volume: 0.5 }],
      [trap.land + 0.2, tSil, "qf.scare.breath", { volume: 0.45, fadeIn: 0.4, fadeOut: 0.05 }],
      [tDark, tSil, "qf.scare.drone", { volume: 0.5, fadeIn: 0.6, fadeOut: 0.1, bus: "sfx" }],
      ...S2.loops,
      [tK, DUR + 0.2, "qf.scare.heartbeat", { volume: 0.8, pitch: 1.4 }]
    ];
    function update(t, f) {
      trap.update(t, f);
      pool.visible = t >= trap.open;
      const cl = R.toLocal(R.camera.position);
      let sq = 1, mouth = 0;
      if (t < t0) {
        // Unseen: just above the hole while it blocks the light, then gone into the dark.
        const blocking = t >= tDark && t < tLight;
        S.pivot.visible = blocking;
        R.place(S, hole.x, 0.15, hole.z, 0);
        S.anim(t, 0, {});
        S.setOwn(0.02);
      } else if (t < tK) {
        S.pivot.visible = true;
        R.place(S, start.x, start.y, start.z, R.yawTo(start.x, start.z, cl.x, cl.z));
        S.anim(t * 2, 0, {});
        L.apply(t);
        mouth = sstep(t0, L.t1, t) * (0.8 + 0.2 * jit(t, 31));
        S.setOwn(0.09);
      } else {
        // Engulfed: you are between its core and its skin, squeezed.
        S.pivot.visible = true;
        const b = Math.sin((t - tK) * 6) * 0.5 + 0.5;
        R.place(S, engulf.x, y0, engulf.z, R.yawTo(engulf.x, engulf.z, me.x, me.z));
        S.anim(t, 0, {});
        S.pivot.scale.set(1 + 0.12 * b, 1 - 0.18 * b, 1 + 0.12 * b);
        S.setOwn(0.12);
        mouth = 0.5 + 0.3 * Math.sin((t - tK) * 6);
        sq = 0;
      }
      if (sq) S.pivot.scale.set(1, 1, 1);
      if (jelly) jelly.opacity = jellyOp * (t >= t0 && t < tK ? 0.3 : 1);   // the jelly thins so the face inside reads
      if (S.parts.slimeMouth) S.parts.slimeMouth.visible = mouth < 0.05;
      jaw.set(mouth);
      eyes(t >= t0 && t < tK ? 1 : t >= tK ? 0.25 : 0);
      small.forEach((m, i) => {
        const k = (t - T_SPLIT - i * 0.18) / 0.9; m.pivot.visible = k > 0;
        if (k <= 0) return;
        const fwd = { x: Math.sin(0.2), z: Math.cos(0.2) }, lat = (i - 1) * 0.55, d = 0.7 + Math.min(1, k) * 1.3;
        const x = me.x + fwd.x * d + fwd.z * lat * (0.4 + k), z = me.z + fwd.z * d - fwd.x * lat * (0.4 + k);
        R.place(m, x, y0 + Math.abs(Math.sin(k * Math.PI * 2)) * 0.45, z, R.yawTo(me.x, me.z, x, z)); m.anim(t + i, 0, {});
      });
      fx(t);
      const blocked = sstep(tDark, tDark + 0.3, t) * (1 - sstep(tLight - 0.1, tLight + 0.15, t));
      const inside = sstep(tK - 0.05, tK + 0.1, t), sil = sstep(tSil, tSil + 0.5, t) * (t < t0 ? 1 : 0);
      f.env = { bake: 1 - 0.25 * sstep(0.2, 1.2, t) - 0.35 * blocked - 0.15 * sil, lights: 1 - 0.7 * blocked - 0.2 * sil, fogMul: 1 + 0.4 * sstep(1, 3, t), fogAdd: 0.4 * inside, fog: [0.06, 0.19, 0.05, inside], squash: inside * 0.35 * (Math.sin((t - tK) * 6) * 0.5 + 0.5) };
      f.tints = [[50, 150, 40, 0.22 * inside]];
      f.vig = [10, 30, 0, 0.3 + 0.3 * blocked + 0.15 * sil + 0.35 * inside]; f.vigR = 0.9;
      f.air = t > tK ? 1 - clamp((t - tK) / 1.6) : null;
      f.black = 0.4 * sstep(DUR - 0.3, DUR + 0.6, t);
      lungeFx(L, t, f);
    }
    return { dur: DUR, hits, cam, update, sounds, loops, deathSide: -1,
      marks: { dread: (tDark + tLight) / 2, fake: (tLight + t0) / 2, lunge: L.t1 + 0.12, kill: tK + 1.2 },
      notes: { fits: trap.fits, D: Dp, open: +trap.open.toFixed(2), fromHole, t0: +t0.toFixed(2), dur: +DUR.toFixed(2) } };
  }
};
