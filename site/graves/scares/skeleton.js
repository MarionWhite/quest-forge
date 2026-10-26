// Skeleton: lights-out. The torches ahead go out one by one, coming toward you, each with a fizz and a curl of smoke.
// In the dark a bowstring creaks. Arrows thud into the walls beside your head; one finds you. Then it steps into the
// last torch's light at point blank, draws, and fires.
import { THREE, track, clamp, lerp, sstep, pulse, tex } from "./rig.js";
import { settle, shake, hitsOf, floorFall, arrowMesh, arrowAim, particles, smoke } from "./common.js";

export default {
  death: "Steve was shot by Skeleton",
  async build(R) {
    const [arrowTex, partTex] = await Promise.all([tex("entity_arrow"), tex("particles")]);
    // The torches ahead, farthest first; the nearest one stays lit for the end.
    const near = R.torches.slice().sort((a, b) => Math.hypot(a.l.x, a.l.z) - Math.hypot(b.l.x, b.l.z));
    // An island of light ahead, where it will step in: the torch 1.5 to 6 blocks ahead nearest the middle.
    const last = R.torches.filter((t) => t.l.z > 1.5 && t.l.z < 6.5).sort((a, b) => Math.abs(a.l.x) + a.l.z * 0.3 - Math.abs(b.l.x) - b.l.z * 0.3)[0] || near[0] || null;
    let ahead = R.torches.filter((t) => t !== last && t.l.z > 0.5 && t.l.z < 22 && Math.abs(t.l.x) < 9).sort((a, b) => b.l.z - a.l.z);
    // Any others close by that would keep the corridor lit go out with the nearest of these.
    const rest = R.torches.filter((t) => t !== last && !ahead.includes(t) && Math.hypot(t.l.x, t.l.z) < 14);
    if (ahead.length > 5) ahead = ahead.slice(ahead.length - 5);
    // They go out over the same two and a half seconds however many there are, faster as they come closer.
    const T0 = 0.95, T_DARK = 3.45;
    const outAt = ahead.map((tc, i) => T0 + (T_DARK - 0.1 - T0) * Math.pow(i / Math.max(1, ahead.length - 1), 0.8));
    rest.forEach(() => outAt.push(T_DARK - 0.15));
    const dying = ahead.concat(rest);

    // The skeleton: comes out of the dark into the last torch's light, in front.
    const sk = R.mob("Skeleton", { equipment: [{ id: "minecraft:bow", ench: false }], amb: [0.04, 0.04, 0.04], own: true });
    const lx = last ? clamp(last.l.x * 0.5, -1.0, 1.0) : 0.3;
    const SZ = last ? clamp(last.l.z - 1.0, 1.5, 2.1) : clamp(R.ahead - 0.5, 1.2, 1.6);
    const torchGlow = R.ownLight(R.light(0xffb060, 0, 7, 1.3));   // the last torch, stronger as the rest die
    const flash = R.ownLight(R.light(0xfff0b0, 0, 4, 1.4));         // sparks light the arrow for an instant

    // Arrows: two into the walls by the head, one into you in the dark, two at point blank.
    const wl = Math.min(R.wallL, 4), wr = Math.min(R.wallR, 4);
    const shotFrom = [lx * 0.6, 1.5, Math.min(R.ahead - 0.6, 9)];
    const A = [
      { t: T_DARK + 0.55, to: [-wl + 0.02, 1.78, 0.55], wall: true },
      { t: T_DARK + 1.05, to: [wr - 0.02, 1.42, 0.25], wall: true },
      { t: T_DARK + 1.5, to: [0.05, 1.3, 0.15], you: true },
      { t: 0, to: [0, 1.25, 0.1], you: true, close: true },
      { t: 0, to: [0, 0.3, 0.0], you: true, close: true }
    ];
    const T_STEP = T_DARK + 2.0, T_FIRE = T_STEP + 0.85, T_LAST = T_FIRE + 1.0, DUR = T_LAST + 0.25;
    A[3].t = T_FIRE; A[4].t = T_LAST;
    const arrows = A.map((a) => { const m = arrowMesh(arrowTex); m.visible = false; R.add(m); return { ...a, m }; });
    const hits = hitsOf([[A[2].t, 5, -1], [T_FIRE + 0.05, 9, 1], [T_LAST + 0.05, 6, -1]]);

    // Camera: settle, follow each dying torch a little, flinch at the thuds, look at the arrow, look ahead.
    const sideOf = (tc) => clamp(R.yawTo(0, 0, tc.l.x, tc.l.z) * 0.55, -0.6, 0.6);
    const yk = [[0, 0], [0.9, 0]];
    ahead.forEach((tc, i) => yk.push([outAt[i] + 0.25, sideOf(tc)]));
    yk.push([T_DARK + 0.3, 0], [A[0].t, 0, "h"], [A[0].t + 0.1, -0.22, "x"], [A[0].t + 0.45, 0.95], [A[1].t, 0.85], [A[1].t + 0.1, 0.55, "x"], [A[1].t + 0.42, 0.0],
      [A[2].t, 0.0], [T_STEP - 0.2, 0.05], [T_STEP + 0.25, R.yawTo(0, 0, lx, SZ)]);
    const yaw = track(yk);
    const pitch = track([[0, 0], [0.9, -0.02], [T_DARK, 0.02], [A[0].t + 0.45, 0.03], [A[2].t, 0.0], [A[2].t + 0.08, 0.16, "x"], [A[2].t + 0.6, 0.02], [T_STEP + 0.3, 0.06], [T_FIRE, 0.08]]);
    const cam = (t) => {
      const s = settle(R, t, 0.9);
      const k = sstep(0.8, 1.3, t);
      const c = { x: s.x * (1 - k), y: s.y, z: s.z * (1 - k), yaw: lerp(s.yaw, yaw(t), k), pitch: lerp(s.pitch, pitch(t), k), roll: 0, fov: s.fov };
      c.z -= 0.06 * pulse(t, [A[0].t, A[1].t], 0.15) + 0.2 * sstep(A[2].t, A[2].t + 0.08, t) * (1 - sstep(A[2].t + 0.2, A[2].t + 0.7, t));
      shake(c, t, 0.002 + 0.002 * sstep(1, T_DARK, t) + 0.025 * pulse(t, [A[0].t, A[1].t], 0.12) + 0.03 * pulse(t, hits.map((h) => h.t), 0.2), 7);
      floorFall(c, t, T_FIRE + 0.1, { d: 0.6, side: -1, roll: 1.2, y: 0.26, pitch: 0.55, back: 0.45 });
      if (t > T_FIRE + 0.5) {   // on the floor, looking up at it
        const k2 = sstep(T_FIRE + 0.5, T_LAST - 0.25, t), zs = SZ - 0.35;
        c.yaw = lerp(c.yaw, R.yawTo(c.x, c.z, lx, zs), k2); c.pitch = lerp(c.pitch, R.pitchTo(c.x, c.y, c.z, lx, 1.45, zs), k2); c.roll = lerp(c.roll, 0.35, k2);
      }
      return c;
    };

    // Smoke as each torch dies; sparks where arrows strike stone; blood where they strike you.
    const puffs = particles(R, partTex, dying.flatMap((tc, i) => smoke([tc.l.x, tc.l.y + 0.75, tc.l.z], outAt[i], 7, { spread: 0.15, window: 0.25, life: 1.4, size: 0.18, rise: 0.5, seed: 30 + i })));
    for (const a of arrows) {
      if (a.wall) R.burst(a.t, a.to, 16, "spark", { dir: [-Math.sign(a.to[0]) * 0.8, 0.7, -0.4], speed: 3, spread: 0.6, size: 0.03, life: 0.45, grav: 12 });
      if (a.wall) R.burst(a.t, a.to, 8, "stone", { dir: [-Math.sign(a.to[0]) * 0.6, 0.3, -0.2], speed: 1.6, spread: 0.5, size: 0.045, life: 0.9 });
    }
    hits.forEach((h, i) => R.burst(h.t, i === 2 ? [0, 0.35, 0.25] : [0.04, 1.2, 0.35], 26, "blood", { dir: [0, 0.7, 0.9], speed: 2.3, spread: 0.7, size: 0.05, life: 1.2, stick: 3 }));

    const sounds = [
      ...dying.map((tc, i) => [outAt[i], "random.fizz", { at: [tc.l.x, tc.l.y + 0.6, tc.l.z], volume: 0.75, pitch: 0.9 + (i % 3) * 0.08 }]),
      [T_DARK - 0.4, "mob.skeleton.say", { at: [shotFrom[0], 1.6, shotFrom[2] + 1], volume: 0.7, pitch: 0.85 }],
      [T_DARK + 0.2, "random.door_open", { at: shotFrom, volume: 0.22, pitch: 1.9 }],
      ...arrows.slice(0, 3).map((a) => [a.t - 0.07, "random.bow", { at: shotFrom, volume: 0.9, pitch: 0.95 }]),
      [A[0].t, "random.bowhit", { at: A[0].to, volume: 1 }], [A[1].t, "random.bowhit", { at: A[1].to, volume: 1 }],
      [A[0].t + 0.02, "qf.scare.stinger", { volume: 0.5 }],
      [A[2].t, "random.bowhit", { volume: 0.9 }],
      [T_STEP - 0.5, "mob.skeleton.step", { at: [lx, 0, SZ + 1.5], volume: 0.7 }], [T_STEP - 0.05, "mob.skeleton.step", { at: [lx, 0, SZ + 0.6], volume: 0.8 }],
      [T_STEP + 0.1, "mob.skeleton.say", { at: [lx, 1.6, SZ], volume: 1, pitch: 0.75 }],
      [T_STEP + 0.12, "qf.scare.shriek", { volume: 0.7 }], [T_STEP + 0.14, "qf.scare.hit", { volume: 0.8 }],
      [T_STEP + 0.4, "random.door_open", { at: [lx, 1.5, SZ], volume: 0.3, pitch: 2.0 }],
      [T_FIRE - 0.04, "random.bow", { at: [lx, 1.5, SZ], volume: 1 }], [T_LAST - 0.04, "random.bow", { at: [lx, 1.5, SZ], volume: 1 }],
      ...hits.flatMap((h, i) => [[h.t, "game.player.hurt"], [h.t + 0.01, "random.bowhit", { volume: 0.8 }], [h.t + 0.03, i === 1 ? "qf.scare.crunch" : "qf.scare.gore", { volume: 0.9 }]]),
      [T_FIRE + 0.2, "qf.scare.scream", { volume: 0.8 }],
      [T_FIRE + 0.7, "game.player.hurt.fall.small"],
      [DUR, "game.player.die"], [DUR, "@muffle", { hz: 420, s: 3 }]
    ];
    const loops = [[0.5, DUR + 0.2, "qf.scare.heartbeat", { volume: 0.5 }], [T_DARK - 0.4, T_STEP + 0.1, "qf.scare.breath", { volume: 0.4, fadeIn: 1.2, fadeOut: 0.2 }]];

    const pose = (t) => {
      sk.anim(t, 0, { walk: t < T_STEP ? 1 : 0 });
      const P = sk.parts;
      // ModelBiped.aimedBow: both arms out level, the left one turned in to hold the string.
      const draw = sstep(T_STEP + 0.2, T_STEP + 0.55, t) * (1 - sstep(T_FIRE - 0.02, T_FIRE + 0.05, t)) + sstep(T_FIRE + 0.4, T_FIRE + 0.8, t) * (1 - sstep(T_LAST - 0.02, T_LAST + 0.05, t));
      if (P.rightArm) {
        P.rightArm.rotation.x = -Math.PI / 2 + (P.head ? P.head.rotation.x : 0); P.leftArm.rotation.x = -Math.PI / 2;
        P.rightArm.rotation.y = -0.1; P.leftArm.rotation.y = 0.1 + 0.4 * draw; P.rightArm.rotation.z = 0; P.leftArm.rotation.z = 0;
      }
    };
    function update(t, f) {
      // The torches die one by one; the corridor follows them into the dark.
      puffs(t);
      let gone = 0;
      dying.forEach((tc, i) => { if (t >= outAt[i]) R.snuff(tc); gone += sstep(outAt[i], outAt[i] + 0.2, t); });
      const dark = dying.length ? gone / dying.length : sstep(1, T_DARK, t);
      f.env = { bake: lerp(1, 0.1, dark) * (1 - 0.15 * sstep(0.2, 1, t)), lights: lerp(1, 0.65, dark), fogMul: 1 + 1.5 * dark, expo: 1 - 0.15 * dark };
      f.vig = [0, 0, 0, 0.25 + 0.4 * dark]; f.vigR = 0.85;
      if (last) { R.L(last.l.x * 0.85, last.l.y + 0.6, last.l.z, torchGlow.position); torchGlow.intensity = 7 * dark * (0.9 + 0.1 * Math.sin(t * 23)); }
      else { R.L(lx, 2.6, SZ - 0.4, torchGlow.position); torchGlow.intensity = 4 * dark; }
      // The skeleton walks up out of the dark (unseen), into the light.
      const kz = sstep(T_STEP - 1.2, T_STEP, t);
      const z = lerp(SZ + 3.2, SZ, kz) + 0.35 * sstep(T_FIRE + 0.5, T_LAST - 0.3, t) * -1;
      sk.pivot.visible = t > T_STEP - 1.3;
      const camNow = cam(t);
      R.place(sk, lx, 0, z, R.yawTo(lx, z, camNow.x, camNow.z));
      sk.setOwn(0.03 + 0.07 * sstep(T_STEP - 0.4, T_STEP, t));
      pose(t);
      if (sk.parts.head) sk.parts.head.rotation.x = clamp(Math.atan2(camNow.y - 1.62, Math.hypot(camNow.x - lx, camNow.z - z)) * 0.8, -0.8, 0.4);
      // Arrows: fly for a tenth of a second, then stay where they struck (the ones that strike you vanish into you).
      for (const a of arrows) {
        const from = a.close ? [lx - 0.3, 1.45, z - 0.3] : shotFrom;
        const k = clamp((t - (a.t - 0.1)) / 0.1);
        a.m.visible = t >= a.t - 0.1 && (!a.you || t < a.t + (a.close ? 0.0 : 0.0));
        if (!a.m.visible) continue;
        const p = [lerp(from[0], a.to[0], k), lerp(from[1], a.to[1], k), lerp(from[2], a.to[2], k)];
        R.at(a.m, p[0], p[1], p[2]);
        const d = R.dirW(a.to[0] - from[0], a.to[1] - from[1], a.to[2] - from[2]);
        arrowAim(a.m, new THREE.Vector3(d[0], d[1], d[2]));
        if (a.wall && t > a.t) a.m.rotateZ(Math.sin((t - a.t) * 60) * 0.08 * Math.exp(-(t - a.t) * 5));   // the quiver
      }
      const wa = arrows.slice(0, 2).map((a) => [a, pulse(t, [a.t], 0.09)]).sort((p, q) => q[1] - p[1])[0];
      if (wa && wa[1] > 0.01) { R.L(wa[0].to[0] * 0.9, wa[0].to[1], wa[0].to[2], flash.position); flash.intensity = 5 * wa[1]; } else flash.intensity = 0;
      f.splats = hits.filter((h) => t >= h.t).map((h, i) => ({ t0: h.t, x: [0.42, 0.6, 0.5][i], y: [0.55, 0.42, 0.35][i], r: 12 + 4 * i, seed: 21 + i }));
      f.black = 0.5 * sstep(T_LAST, DUR + 0.3, t);
    }
    return { dur: DUR, hits, cam, update, sounds, loops, deathSide: -1, notes: { torches: dying.length, last: !!last, T_DARK: +T_DARK.toFixed(2) } };
  }
};
