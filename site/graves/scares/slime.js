// Slime (piston trap, round 7: the squish). The floor goes and you drop into a dark pit, into a skin of green slime
// water. Quiet. Up in the hole the light goes out: something square is in it. Then, a coin toss:
//   - it squeezes down through the hole, stretched long by the opening, wet; it hangs; it lets go and falls on you;
//   - the light comes back, and a squelch comes out of the dark of the pit instead: it is sitting there, in here with
//     you, wobbling. It hops toward you (down, up, the splash as it lands), and the next hop comes down on top of you.
// Then you are inside it: the world green and far away, the sound gone thick, the air running out, a drowned scream,
// and it squeezes. Small slimes bud off it and hop away.
import { THREE, clamp, lerp, sstep, pulse, tex, loadImg } from "./rig.js";
import { settle, shake, hitsOf, particles, mulberry } from "./common.js";
import { pistonTrap } from "./piston.js";
import { boxOf, silence, splitJaw } from "./fnaf.js";
import { roar, hop } from "./story.js";

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
    // The core's mouth: the bottom three rows of the inner cube drop open inside the jelly as it comes down on you.
    const jaw = splitJaw(S, [{ part: core, box: boxOf("slimeInner", "slimeBodies"), rows: 3 }], { nTeeth: 0, max: 0.9, mouth: 0x000000, tongue: 0x0b1606 });
    // ---- the dice -------------------------------------------------------------------------------------------
    const fromHole = R.chance(0.5);
    const me = { x: hole.x, z: hole.z }, eyeY = -Dp + R.eye;
    const tDark = trap.land + R.vary(1.3, 0.35);
    // Out in the dark of the pit, along its roomiest way (from the trap's room box: the room is carved when it opens).
    const { a, b } = trap;
    const cands = [[rb.i0, b], [rb.i1, b + 1], [a, rb.k0], [a + 1, rb.k1]].map(([i, k]) => { const c = loc(i, -Dp, k); const d = Math.hypot(c.x - me.x, c.z - me.z) || 1; return { d, ux: (c.x - me.x) / d, uz: (c.z - me.z) / d }; })
      .sort((p, q) => q.d - p.d + (q.uz - p.uz) * 0.3);
    const far = cands[0], sd = clamp(far.d - 0.6, 2.0, 3.2);
    const side = { x: me.x + far.ux * sd - far.uz * 0.3, z: me.z + far.uz * sd + far.ux * 0.3 };
    const mid = { x: lerp(side.x, me.x, 0.3), z: lerp(side.z, me.z, 0.3) };   // the first hop: a short one
    let tLight = null, tSil, tSq0 = null, tSq1 = null, tDrop = null, tSq = null, tHop1 = null, tLand1 = null, tHop2 = null, tK;
    if (fromHole) {
      tSq0 = tDark + R.vary(0.8, 0.35); tSq1 = tSq0 + 0.8;          // squeezing down through the hole
      tSil = tSq1; tDrop = tSq1 + R.vary(0.45, 0.4);                 // it hangs; it lets go
      tK = tDrop + Math.sqrt(2 * Math.max(1.5, -1.25 - (eyeY + 0.15)) / 32);
    } else {
      tLight = tDark + R.vary(1.0, 0.35); tSil = tLight + 0.15;
      tSq = tLight + R.vary(0.9, 0.35);                              // the squelch, out in the dark of the pit
      tHop1 = tSq + R.vary(1.1, 0.3); tLand1 = tHop1 + 0.45;
      tHop2 = tLand1 + R.vary(0.4, 0.3); tK = tHop2 + 0.42;
    }
    const DUR = tK + R.vary(2.6, 0.1), T_SPLIT = tK + 0.9;
    const engulf = { x: me.x + 0.55, z: me.z + 0.62 };
    const hits = hitsOf([[trap.land, 4, 1], [tK + 0.02, 4, -1], [tK + 0.55, 4, 1], [tK + 1.05, 3, -1], [tK + 1.6, 2, 1], [DUR, 3, -1]]);
    // Where it is (its bottom), and how it is squashed (x/z, y), up to tK.
    const slimeAt = (t) => {
      if (fromHole) {
        if (t < tSq0) return { x: hole.x, y: 0.15, z: hole.z, sx: 1, sy: 1 };
        if (t < tDrop) { const k = sstep(tSq0, tSq1, t), sag = t > tSq1 ? 0.06 * Math.sin((t - tSq1) * 9) * Math.exp(-(t - tSq1) * 3) : 0; return { x: hole.x, y: 0.15 - 1.4 * k + sag, z: hole.z, sx: 1 - 0.1 * k, sy: 1 + 0.3 * k }; }
        const d = t - tDrop; return { x: hole.x, y: -1.25 - 16 * d * d, z: hole.z, sx: 0.9 + 0.1 * clamp(d / 0.3), sy: 1.3 - 0.3 * clamp(d / 0.3) };
      }
      const wob = 0.04 * Math.sin(t * 5);
      if (t < tHop1 - 0.2) return { x: side.x, y: y0, z: side.z, sx: 1 + wob, sy: 1 - wob };
      if (t < tHop1) { const k = sstep(tHop1 - 0.2, tHop1, t); return { x: side.x, y: y0, z: side.z, sx: 1 + 0.18 * k, sy: 1 - 0.25 * k }; }   // down, to jump
      if (t < tLand1) { const u = (t - tHop1) / (tLand1 - tHop1), q = hop({ x: side.x, y: y0, z: side.z }, { x: mid.x, y: y0, z: mid.z }, u, 1.1); return { ...q, sx: 0.9, sy: 1.2 - 0.2 * u }; }
      if (t < tHop2) { const l = t - tLand1, sq = Math.exp(-l * 9) * Math.cos(l * 20); return { x: mid.x, y: y0, z: mid.z, sx: 1 + 0.25 * sq, sy: 1 - 0.35 * sq }; }   // the landing squish
      const u = (t - tHop2) / (tK - tHop2), q = hop({ x: mid.x, y: y0, z: mid.z }, { x: me.x + 0.15, y: eyeY - 0.6, z: me.z + 0.25 }, u, 2.2);
      return { ...q, sx: 0.9, sy: 1.25 };
    };

    const cam = (t) => {
      const s = settle(R, t, 0.9);
      const k = sstep(0.8, 1.3, t);
      let c = { x: s.x * (1 - k), y: s.y, z: s.z * (1 - k), yaw: lerp(s.yaw, 0, k), pitch: lerp(s.pitch, -0.02, k), roll: 0, fov: s.fov, near: t >= tK - 0.6 ? 0.02 : undefined };
      c = trap.cam(t, c);
      if (t > trap.land + 0.3 && t < tK) {
        // Up at the hole as it goes dark; (a) held on it as it comes through and falls; (b) down, to the squelch, on it.
        const up = sstep(trap.land + 0.4, tDark - 0.1, t) * (fromHole ? 1 : 1 - sstep(tLight + 0.2, tLight + 0.9, t));
        c.pitch = lerp(-0.25, fromHole ? 1.25 : 1.3, up);
        c.yaw = 0;
        if (!fromHole) {
          const q = slimeAt(t), see = sstep(tSq, tSq + 0.6, t), aim = R.pitchTo(c.x, c.y, c.z, q.x, q.y + 1.0, q.z);
          c.pitch = lerp(lerp(c.pitch, -0.1, sstep(tLight + 0.6, tSq, t)), clamp(aim, -0.5, 1.3), see);
          c.yaw = lerp(0.3 * Math.sin((t - tLight) * 0.9) * sstep(tLight + 0.6, tSq, t), R.yawTo(c.x, c.z, q.x, q.z), see);
        }
      }
      if (t >= tK) {   // inside it: pressed down into the slime water
        const k2 = sstep(tK, tK + 0.25, t);
        c.y = lerp(c.y, y0 + 0.75, k2); c.pitch = lerp(fromHole ? 1.1 : 0.6, 0.25, k2); c.yaw = lerp(fromHole ? 0 : R.yawTo(me.x, me.z, mid.x, mid.z) * 0.5, -0.2, k2); c.roll = lerp(c.roll, -0.25, k2);
        c.fov = s.fov - 8 * k2;
      }
      c.fov += 8 * pulse(t, [tK], 0.12);
      return shake(c, t, 0.0015 + (tLand1 ? 0.02 * pulse(t, [tLand1], 0.2) : 0) + 0.03 * pulse(t, [tK], 0.2) + 0.012 * pulse(t, hits.map((h) => h.t), 0.18), 5);
    };

    const bubbles = [], drops = [];
    for (let i = 0; i < 40; i++) bubbles.push({ t0: tK + 0.1 + r() * (DUR - tK), at: [me.x + (r() - 0.2) * 0.8, y0 + 0.5 + r() * 0.5, me.z + 0.2 + r() * 0.7], v: [0, 0.6 + r() * 0.5, 0], life: 0.9, size: 0.05 + r() * 0.04, tile: 32, color: [0.75, 0.95, 0.7], grav: -0.3, fog: false });
    for (const [tt, x, z, n] of [[trap.land, me.x, me.z, 22], [tK, engulf.x, engulf.z, 26], ...(tLand1 ? [[tLand1, mid.x, mid.z, 26]] : [])]) for (let i = 0; i < n; i++) drops.push({ t0: tt + r() * 0.05, at: [x + (r() - 0.5) * 1.2, y0 + 0.2, z + (r() - 0.5) * 1.2], v: [(r() - 0.5) * 2, 2 + r() * 2, (r() - 0.5) * 2], life: 0.8, size: 0.06, tile: 19 + Math.floor(r() * 4), color: [0.45, 0.85, 0.35], grav: 9, fog: false });
    for (let i = 0; i < 6; i++) drops.push({ t0: tDark + 0.2 + i * R.vary(0.25, 0.3), at: [hole.x + (r() - 0.5) * 0.6, -0.6, hole.z + (r() - 0.5) * 0.6], v: [0, -1, 0], life: 0.9, size: 0.05, tile: 19, color: [0.45, 0.85, 0.35], grav: 12, fog: false });
    const fx = particles(R, partTex, [...bubbles, ...drops]);
    const sounds = [
      ...trap.sounds,
      [trap.land + 0.01, "game.player.swim.splash", { volume: 1 }],
      [trap.land + 0.6, "qf.scare.whisper", { volume: 0.25 }],
      [tDark - 0.15, "mob.slime.big", { at: [hole.x, 0.5, hole.z], volume: 0.7, pitch: 0.7 }],
      ...(fromHole ? [
        // Squeezing through: wet, slow; it hangs; it lets go.
        [tSq0 + 0.05, "mob.slime.big", { at: [hole.x, -0.5, hole.z], volume: 0.8, pitch: 0.5 }], [tSq0 + 0.45, "mob.slime.big", { at: [hole.x, -1, hole.z], volume: 0.85, pitch: 0.45 }],
        [tSq1 + 0.1, "mob.slime.small", { at: [hole.x, -1.2, hole.z], volume: 0.5, pitch: 0.5 }],
        silence(tSil, { fade: 0.2 }),
        [tDrop, "mob.slime.attack", { at: [hole.x, -1.3, hole.z], volume: 0.7, pitch: 0.5 }]
      ] : [
        [tDark + 0.45, "mob.slime.big", { at: [hole.x, 0, hole.z], volume: 0.8, pitch: 0.6 }],
        [tLight - 0.1, "mob.slime.small", { at: [hole.x, 0.8, hole.z], volume: 0.4, pitch: 0.6 }],
        silence(tSil),
        [tSq, "mob.slime.big", { at: [side.x, y0 + 0.5, side.z], volume: 0.5, pitch: 0.55 }],
        [tHop1 - 0.05, "mob.slime.attack", { at: [side.x, y0 + 0.8, side.z], volume: 0.6, pitch: 0.55 }],
        [tLand1, "mob.slime.big", { at: [mid.x, y0, mid.z], volume: 1.2, pitch: 0.5 }], [tLand1 + 0.01, "random.splash", { at: [mid.x, y0, mid.z], volume: 0.9 }],
        [tHop2, "mob.slime.attack", { at: [mid.x, y0 + 1, mid.z], volume: 0.9, pitch: 0.55 }]
      ]),
      // On you.
      ...roar(tK - 0.02, [["mob.slime.big", { pitch: 0.42 }], ["mob.slime.attack", { pitch: 0.5, volume: 1.0 }]], { hit: 0.9 }),
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
      [fromHole ? tDrop : tSq, tK, "qf.scare.heartbeat", { volume: 0.6, pitch: 1.3, fadeIn: 0.05 }],
      [tK, DUR + 0.2, "qf.scare.heartbeat", { volume: 0.8, pitch: 1.4 }]
    ];
    function update(t, f) {
      trap.update(t, f);
      pool.visible = t >= trap.open;
      let mouth = 0;
      if (t < tK) {
        // (a) in the hole, through it, falling; (b) in the hole, then out in the dark of the pit, hopping at you.
        const q = slimeAt(t);
        S.pivot.visible = fromHole ? t >= tDark : (t >= tDark && t < tLight) || t >= tSq - 0.3;
        if (!fromHole && t < tLight) { q.x = hole.x; q.y = 0.15; q.z = hole.z; q.sx = q.sy = 1; }
        R.place(S, q.x, q.y, q.z, R.yawTo(q.x, q.z, me.x, me.z));
        S.anim(t, 0, {});
        S.pivot.scale.set(q.sx, q.sy, q.sx);
        mouth = fromHole ? 0.6 * sstep(tDrop + 0.1, tK, t) : 0.6 * sstep(tHop2 + 0.1, tK, t);
        S.setOwn(fromHole ? 0.04 + 0.05 * sstep(tSq0, tSq1, t) : t < tLight ? 0.02 : 0.07);
      } else {
        // Engulfed: you are between its core and its skin, squeezed.
        S.pivot.visible = true;
        const b = Math.sin((t - tK) * 6) * 0.5 + 0.5;
        R.place(S, engulf.x, y0, engulf.z, R.yawTo(engulf.x, engulf.z, me.x, me.z));
        S.anim(t, 0, {});
        S.pivot.scale.set(1 + 0.12 * b, 1 - 0.18 * b, 1 + 0.12 * b);
        S.setOwn(0.12);
        mouth = 0.5 + 0.3 * Math.sin((t - tK) * 6);
      }
      if (S.parts.slimeMouth) S.parts.slimeMouth.visible = mouth < 0.05;
      jaw.set(mouth);
      small.forEach((m, i) => {
        const k = (t - T_SPLIT - i * 0.18) / 0.9; m.pivot.visible = k > 0;
        if (k <= 0) return;
        const fwd = { x: Math.sin(0.2), z: Math.cos(0.2) }, lat = (i - 1) * 0.55, d = 0.7 + Math.min(1, k) * 1.3;
        const x = me.x + fwd.x * d + fwd.z * lat * (0.4 + k), z = me.z + fwd.z * d - fwd.x * lat * (0.4 + k);
        R.place(m, x, y0 + Math.abs(Math.sin(k * Math.PI * 2)) * 0.45, z, R.yawTo(me.x, me.z, x, z)); m.anim(t + i, 0, {});
      });
      fx(t);
      const blocked = fromHole ? sstep(tDark, tDark + 0.3, t) * (1 - 0.6 * sstep(tSq1, tSq1 + 0.4, t)) * (t < tK ? 1 : 0) : sstep(tDark, tDark + 0.3, t) * (1 - sstep(tLight - 0.1, tLight + 0.15, t));
      const inside = sstep(tK - 0.05, tK + 0.1, t), sil = sstep(tSil, tSil + 0.5, t) * (t < tK ? 1 : 0);
      f.env = { bake: 1 - 0.25 * sstep(0.2, 1.2, t) - 0.35 * blocked - 0.15 * sil, lights: 1 - 0.7 * blocked - 0.2 * sil, fogMul: 1 + 0.4 * sstep(1, 3, t), fogAdd: 0.4 * inside, fog: [0.06, 0.19, 0.05, inside], squash: inside * 0.35 * (Math.sin((t - tK) * 6) * 0.5 + 0.5) };
      f.tints = [[50, 150, 40, 0.22 * inside]];
      f.vig = [10, 30, 0, 0.3 + 0.3 * blocked + 0.15 * sil + 0.35 * inside]; f.vigR = 0.9;
      f.air = t > tK ? 1 - clamp((t - tK) / 1.6) : null;
      f.black = 0.4 * sstep(DUR - 0.3, DUR + 0.6, t);
    }
    return { dur: DUR, hits, cam, update, sounds, loops, deathSide: -1,
      marks: { dread: fromHole ? tSq0 + 0.5 : tDark + 0.5, fake: fromHole ? tSq1 + 0.2 : tSq + 0.7, lunge: tK - 0.14, kill: tK + 1.2 },
      notes: { fits: trap.fits, D: Dp, open: +trap.open.toFixed(2), fromHole, tK: +tK.toFixed(2), dur: +DUR.toFixed(2) } };
  }
};
