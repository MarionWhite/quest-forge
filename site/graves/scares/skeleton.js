// Skeleton (round 7: the archer in the dark). The torches ahead go out one by one, coming toward you, each with a fizz
// and a curl of smoke (the one device: the lights going), all but the last one by you. In the dark, bones rattle across
// the corridor ahead, moving. A bow lets go somewhere out there and an arrow thuds into the wall by your head. Then
// nothing. Silence, longer or shorter every time. The creak of a bowstring drawn back. Either it steps out of the dark
// into the last torch's light, two blocks off, the arrow on the string aimed at your face, or the creak is beside you
// and when the head turns it is there. It holds the aim. It lets go: the arrow takes you off your feet. It walks up,
// stands over you, draws again and fires into you at point blank.
import { THREE, track, clamp, lerp, sstep, pulse, tex } from "./rig.js";
import { settle, shake, hitsOf, floorFall, arrowMesh, arrowAim, particles, smoke, mcRot } from "./common.js";
import { splitJaw, boxOf, silence, deathScream } from "./fnaf.js";
import { roar, kick } from "./story.js";

export default {
  death: "Steve was shot by Skeleton",
  async build(R) {
    const [arrowTex, partTex] = await Promise.all([tex("entity_arrow"), tex("particles")]);
    const near = R.torches.slice().sort((a, b) => Math.hypot(a.l.x, a.l.z) - Math.hypot(b.l.x, b.l.z));
    const last = R.torches.filter((t) => t.l.z > 1.5 && t.l.z < 6.5).sort((a, b) => Math.abs(a.l.x) + a.l.z * 0.3 - Math.abs(b.l.x) - b.l.z * 0.3)[0] || near[0] || null;
    let ahead = R.torches.filter((t) => t !== last && t.l.z > 0.5 && t.l.z < 22 && Math.abs(t.l.x) < 9).sort((a, b) => b.l.z - a.l.z);
    const rest = R.torches.filter((t) => t !== last && !ahead.includes(t) && Math.hypot(t.l.x, t.l.z) < 14);
    if (ahead.length > 5) ahead = ahead.slice(ahead.length - 5);
    // ---- the dice -------------------------------------------------------------------------------------------
    const T0 = 0.95, T_DARK = T0 + R.vary(2.1, 0.3);
    const outAt = ahead.map((tc, i) => T0 + (T_DARK - 0.1 - T0) * Math.pow(i / Math.max(1, ahead.length - 1), 0.8) + (R.rand() - 0.5) * 0.15);
    rest.forEach(() => outAt.push(T_DARK - 0.15));
    const dying = ahead.concat(rest);
    const tRattle = T_DARK + R.vary(0.45, 0.4);
    const tArrow = T_DARK + R.vary(1.35, 0.3);                 // the miss, into the wall by your head
    const tSil = tArrow + R.vary(0.75, 0.35);                  // then nothing
    const fromSide = R.chance(0.45);                           // the creak is beside you, not out there
    const tCreak = tSil + R.vary(0.75, 0.45);
    const t0 = tCreak + (fromSide ? 0.05 : 0.3);               // it is seen
    const T_S1 = t0 + (fromSide ? 0.35 : 0.45) + R.vary(0.7, 0.3);   // the arrow, held that long on you
    const lside = R.wallR > R.wallL ? 1 : -1;
    const sk = R.mob("Skeleton", { equipment: [{ id: "minecraft:bow", ench: false }], amb: [0.04, 0.04, 0.04], own: true });
    const jaw = splitJaw(sk, [{ part: sk.parts.head, box: boxOf("skeleton", "bipedHead"), rows: 2 }], { nTeeth: 0, max: 0.7, mouth: 0x050505, tongue: 0x140303 });
    sk.anim(0, 0, { walk: 0 }); R.place(sk, 0, 0, 3, Math.PI);
    const lx = last ? clamp(last.l.x * 0.5, -1.0, 1.0) : 0.3;
    const SZ = last ? clamp(last.l.z - 1.0, 1.5, 2.1) : clamp(R.ahead - 0.5, 1.2, 1.6);
    const dark0 = { x: clamp(lx * 0.4, -0.6, 0.6), z: clamp(R.ahead - 0.8, 3.2, 6.5) };   // out in the dark past the last light
    // Where it stands to aim: in the last light, two blocks or so off; or beside you, against the roomier wall.
    const aimAt = fromSide ? { x: lside * clamp((lside < 0 ? R.wallL : R.wallR) - 0.45, 0.6, 1.25), z: 0.35 }
      : { x: clamp(lx * 0.8, -1.2, 1.2), z: clamp(Math.max(SZ + 0.55, last ? last.l.z - 0.3 : 2.2), 1.9, R.ahead - 0.5) };
    const fromDark = fromSide ? aimAt : { x: aimAt.x * 0.6, z: Math.min(aimAt.z + 1.4, R.ahead - 0.4) };
    const T_FIRE = T_S1 + 1.3, T_LAST = T_FIRE + 0.95, DUR = T_LAST + 0.3;
    const torchGlow = R.ownLight(R.light(0xffb060, 0, 7, 1.3));
    const flash = R.ownLight(R.light(0xfff0b0, 0, 4, 1.4));

    // Arrows: the miss into the wall by the head; three into you.
    const wl = Math.min(R.wallL, 4), wr = Math.min(R.wallR, 4);
    const shotFrom = [dark0.x, 1.5, Math.min(R.ahead - 0.6, 9)];
    const missTo = lside > 0 ? [-wl + 0.02, 1.72, 0.45] : [wr - 0.02, 1.72, 0.45];
    const A = [
      { t: tArrow, to: missTo, wall: true, from: shotFrom },
      { t: T_S1, to: [0, 1.4, 0.05], you: true },
      { t: T_FIRE, to: [0, 1.25, 0.1], you: true },
      { t: T_LAST, to: [0, 0.3, 0.0], you: true }
    ];
    const arrows = A.map((a) => { const m = arrowMesh(arrowTex); m.visible = false; R.add(m); return { ...a, m }; });
    const wallA = arrows[0];
    const hits = hitsOf([[T_S1 + 0.02, 5, -lside], [T_FIRE + 0.05, 8, 1], [T_LAST + 0.05, 7, -1]]);

    // The head: follows each dying torch a little; held on the dark ahead; flinches at the thud; drawn to the creak and
    // held on the arrowhead; knocked down by the arrow; on the floor, looking up at it.
    const sideOf = (tc) => clamp(R.yawTo(0, 0, tc.l.x, tc.l.z) * 0.55, -0.6, 0.6);
    const yDark = R.yawTo(0, 0, dark0.x, dark0.z) * 0.8;
    const yk = [[0, 0], [0.9, 0]];
    const ord = ahead.map((tc, i) => [outAt[i], sideOf(tc)]).sort((a, b) => a[0] - b[0]);
    for (const [ot, y] of ord) if (ot + 0.25 > yk[yk.length - 1][0] + 0.05) yk.push([ot + 0.25, y]);
    yk.push([T_DARK + 0.35, 0], [tRattle + 0.5, yDark + 0.2], [tRattle + 1.1, yDark - 0.15]);
    yk.push([tArrow - 0.01, yDark, "h"], [tArrow + 0.12, -lside * 0.55, "x"], [tArrow + 0.7, -lside * 0.4], [tSil + 0.3, yDark * 0.6]);
    const yAim = R.yawTo(0, 0, aimAt.x, aimAt.z);
    yk.push([tCreak, yDark * 0.6, "h"], [t0 + (fromSide ? 0.3 : 0.4), yAim, fromSide ? "o" : "s"], [T_S1, yAim, "h"]);
    const yaw = track(yk.filter((k, i, a) => i === 0 || k[0] > a[i - 1][0]));
    const pAim = R.pitchTo(0, R.eye, 0, aimAt.x, 1.72, aimAt.z);
    const pitch = track([[0, 0], [0.9, -0.02], [T_DARK, 0.02], [tSil, 0.03], [tCreak, 0.0], [t0 + 0.4, pAim], [T_S1, pAim, "h"]]);
    const cam = (t) => {
      const s = settle(R, t, 0.9);
      const k = sstep(0.8, 1.3, t);
      const c = { x: s.x * (1 - k), y: s.y, z: s.z * (1 - k), yaw: lerp(s.yaw, yaw(t), k), pitch: lerp(s.pitch, pitch(t), k), roll: 0, fov: s.fov - 6 * sstep(tCreak, t0 + 0.5, t) * (1 - sstep(T_S1, T_S1 + 0.1, t)), near: t >= t0 ? 0.02 : undefined };
      c.z -= 0.08 * pulse(t, [tArrow], 0.15) + 0.06 * sstep(t0, t0 + 0.3, t);   // the flinch; a half step back from it
      const kk = kick(t, [{ t: T_S1, side: -lside, amp: 1.4 }]); c.yaw += kk.yaw; c.pitch -= kk.pitch;   // the arrow knocks the head back
      shake(c, t, 0.002 + 0.002 * sstep(1, T_DARK, t) + 0.025 * pulse(t, [tArrow], 0.12) + 0.004 * sstep(t0, T_S1, t) + 0.03 * pulse(t, hits.map((h) => h.t), 0.2), 7);
      floorFall(c, t, T_S1 + 0.08, { d: 0.55, side: lside, roll: 1.15, y: 0.26, pitch: 0.55, back: 0.45 });
      if (t > T_S1 + 0.5) {   // on the floor, looking up at it
        const k2 = sstep(T_S1 + 0.5, T_FIRE - 0.3, t), zs = SZ - 0.35;
        c.yaw = lerp(c.yaw, R.yawTo(c.x, c.z, lx, zs), k2); c.pitch = lerp(c.pitch, R.pitchTo(c.x, c.y, c.z, lx, 1.45, zs), k2); c.roll = lerp(c.roll, 0.35, k2);
      }
      return c;
    };

    const puffs = particles(R, partTex, dying.flatMap((tc, i) => smoke([tc.l.x, tc.l.y + 0.75, tc.l.z], outAt[i], 7, { spread: 0.15, window: 0.25, life: 1.4, size: 0.18, rise: 0.5, seed: 30 + i })));
    R.burst(wallA.t, wallA.to, 18, "spark", { dir: [-Math.sign(wallA.to[0]) * 0.8, 0.7, -0.4], speed: 3, spread: 0.6, size: 0.03, life: 0.45, grav: 12 });
    R.burst(wallA.t, wallA.to, 8, "stone", { dir: [-Math.sign(wallA.to[0]) * 0.6, 0.3, -0.2], speed: 1.6, spread: 0.5, size: 0.045, life: 0.9 });
    hits.forEach((h, i) => R.burst(h.t, i === 2 ? [0, 0.35, 0.25] : [0.04, 1.2, 0.35], 26, "blood", { dir: [0, 0.7, 0.9], speed: 2.3, spread: 0.7, size: 0.05, life: 1.2, stick: 3 }));

    // The rattle crosses the dark ahead, a step at a time.
    const rattle = [...Array(5)].map((_, i) => [tRattle + i * R.vary(0.34, 0.2), "mob.skeleton.step", { at: [lerp(-1.6, 1.6, i / 4) * (lside > 0 ? 1 : -1), 0.1, dark0.z + 2.5], volume: 0.4, pitch: 0.85 + 0.05 * (i % 2), reverb: 0.4 }]);
    const creakAt = fromSide ? [aimAt.x, 1.5, aimAt.z] : [fromDark.x, 1.5, fromDark.z];
    const sounds = [
      ...dying.map((tc, i) => [outAt[i], "random.fizz", { at: [tc.l.x, tc.l.y + 0.6, tc.l.z], volume: 0.75, pitch: 0.9 + (i % 3) * 0.08 }]),
      ...rattle,
      [tRattle + 0.9, "mob.skeleton.say", { at: [0, 1.6, dark0.z + 2.5], volume: 0.7, pitch: 0.85, reverb: 0.5 }],
      [tArrow - 0.07, "random.bow", { at: shotFrom, volume: 0.9 }], [tArrow, "random.bowhit", { at: wallA.to, volume: 1 }],
      silence(tSil, { fade: 0.08 }),
      // The bowstring, drawn.
      [tCreak, "random.door_open", { at: creakAt, volume: 0.42, pitch: 1.9 }],
      ...(fromSide ? [] : [[t0 + 0.08, "mob.skeleton.step", { at: [fromDark.x, 0.1, fromDark.z], volume: 0.55 }], [t0 + 0.38, "mob.skeleton.step", { at: [aimAt.x, 0.1, aimAt.z], volume: 0.6 }]]),
      ...roar(t0 + (fromSide ? 0.25 : 0.4), [["mob.skeleton.say", { at: [aimAt.x, 1.7, aimAt.z], pitch: 0.62 }]], { hit: 0.45 }),
      [T_S1 - 0.03, "random.bow", { at: [aimAt.x, 1.5, aimAt.z], volume: 1.2 }],
      [T_S1 + 0.55, "game.player.hurt.fall.small"],
      ...deathScream(T_S1 + 0.18, { volume: 1.1, under: false }),
      [T_FIRE - 0.75, "random.door_open", { at: [lx, 1.5, SZ], volume: 0.3, pitch: 2.0 }],
      [T_FIRE - 0.04, "random.bow", { at: [lx, 1.5, SZ], volume: 1 }], [T_LAST - 0.04, "random.bow", { at: [lx, 1.5, SZ], volume: 1 }],
      ...hits.flatMap((h, i) => [[h.t, "game.player.hurt"], [h.t + 0.01, "random.bowhit", { volume: 0.9 }], [h.t + 0.015, "qf.scare.hit", { volume: i ? 0.6 : 1.0 }], [h.t + 0.03, i === 1 ? "qf.scare.crunch" : "qf.scare.gore", { volume: 1 }]]),
      [T_FIRE + 0.3, "mob.skeleton.say", { at: [lx, 1.6, SZ], volume: 0.9, pitch: 0.7 }],
      ...deathScream(T_LAST + 0.06, { volume: 1.3 }),
      [DUR, "game.player.die"], [DUR, "@muffle", { hz: 420, s: 3 }]
    ];
    const loops = [
      [0.5, tSil, "qf.scare.heartbeat", { volume: 0.5, fadeOut: 0.1 }],
      [T_DARK - 0.4, tSil, "qf.scare.breath", { volume: 0.32, fadeIn: 1.2, fadeOut: 0.05 }],
      [t0, T_S1, "qf.scare.heartbeat", { volume: 0.6, pitch: 1.3, fadeIn: 0.1, fadeOut: 0.02 }],
      [T_S1, DUR + 0.2, "qf.scare.heartbeat", { volume: 0.7, pitch: 1.35 }]
    ];

    // ModelSkeleton with a bow: both arms out along the look, the bow arm steady, the string arm drawn back.
    const pose = (t, draw) => {
      const P = sk.parts;
      if (P.rightArm) {
        const hx = P.head ? -P.head.rotation.x : 0;
        mcRot(P.rightArm, -Math.PI / 2 + hx, -0.1, 0); mcRot(P.leftArm, -Math.PI / 2 + hx, 0.1 + 0.4 * draw, 0);
      }
    };
    const drawAt = (t) => sstep(tCreak - 0.1, tCreak + 0.35, t) * (1 - sstep(T_S1 - 0.02, T_S1 + 0.05, t))
      + sstep(T_FIRE - 0.75, T_FIRE - 0.35, t) * (1 - sstep(T_FIRE - 0.02, T_FIRE + 0.05, t)) + sstep(T_FIRE + 0.35, T_LAST - 0.2, t) * (1 - sstep(T_LAST - 0.02, T_LAST + 0.05, t));
    function update(t, f) {
      const camNow = R.camera, cl = R.toLocal(camNow.position);
      puffs(t);
      let gone = 0;
      dying.forEach((tc, i) => { if (t >= outAt[i]) R.snuff(tc); gone += sstep(outAt[i], outAt[i] + 0.2, t); });
      const dark = dying.length ? gone / dying.length : sstep(1, T_DARK, t);
      f.env = { bake: lerp(1, 0.12, dark) * (1 - 0.15 * sstep(0.2, 1, t)), lights: lerp(1, 0.7, dark), fogMul: 1 + 0.9 * dark, expo: 1 - 0.15 * dark };
      f.vig = [0, 0, 0, 0.25 + 0.4 * dark]; f.vigR = 0.85;
      // The last light, by you: the only one left.
      const fl = 0.9 + 0.1 * Math.sin(t * 23) + 0.05 * Math.sin(t * 61);
      if (last) { R.L(last.l.x * 0.85, last.l.y + 0.6, last.l.z, torchGlow.position); torchGlow.intensity = (1.5 + 4.5 * dark) * fl; }
      else { R.L(lx, 2.6, SZ - 0.4, torchGlow.position); torchGlow.intensity = 3.5 * dark * fl; }
      // The skeleton: out in the dark, unseen; then in the light with the bow on you; then over you.
      let open = 0;
      sk.pivot.visible = t > (fromSide ? tCreak - 0.3 : t0 - 0.05);
      if (t < T_S1 + 0.15) {
        const k = fromSide ? 1 : sstep(t0, t0 + 0.45, t), x = lerp(fromDark.x, aimAt.x, k), z = lerp(fromDark.z, aimAt.z, k);
        R.place(sk, x, 0, z, R.yawTo(x, z, cl.x, cl.z));
        sk.anim(t, 0, { walk: !fromSide && t > t0 && t < t0 + 0.45 ? 1 : 0 });
        if (sk.parts.head) sk.parts.head.rotation.x = clamp(Math.atan2(cl.y - 1.62, Math.hypot(cl.x - x, cl.z - z)) * 0.8, -0.8, 0.4);
        pose(t, drawAt(t));
        open = 0.12 * sstep(t0, t0 + 0.4, t);
        sk.setOwn(fromSide ? 0.16 : 0.04 + 0.2 * k);   // into the light
      } else {
        const kz = sstep(T_S1 + 0.25, T_S1 + 0.95, t);
        const x = lerp(aimAt.x, lx, kz), z = lerp(aimAt.z, SZ, kz) - 0.35 * sstep(T_FIRE + 0.4, T_LAST - 0.3, t);
        R.place(sk, x, 0, z, R.yawTo(x, z, cl.x, cl.z));
        sk.anim(t, 0, { walk: kz > 0 && kz < 1 ? 1 : 0 });
        if (sk.parts.head) sk.parts.head.rotation.x = clamp(Math.atan2(cl.y - 1.62, Math.hypot(cl.x - x, cl.z - z)) * 0.8, -0.8, 0.4);
        pose(t, drawAt(t));
        open = 0.15 + 0.5 * pulse(t, [T_FIRE, T_LAST], 0.25);
        sk.setOwn(0.22);
      }
      jaw.set(open);
      for (const a of arrows) {
        const from = a.from || [lx - 0.3, 1.45, SZ - 0.3];
        const k = clamp((t - (a.t - 0.1)) / 0.1);
        a.m.visible = t >= a.t - 0.1 && !a.you;
        if (!a.m.visible) continue;
        const p = [lerp(from[0], a.to[0], k), lerp(from[1], a.to[1], k), lerp(from[2], a.to[2], k)];
        R.at(a.m, p[0], p[1], p[2]);
        const d = R.dirW(a.to[0] - from[0], a.to[1] - from[1], a.to[2] - from[2]);
        arrowAim(a.m, new THREE.Vector3(d[0], d[1], d[2]));
        if (a.wall && t > a.t) a.m.rotateZ(Math.sin((t - a.t) * 60) * 0.08 * Math.exp(-(t - a.t) * 5));
      }
      { const pw = pulse(t, [wallA.t], 0.09); R.L(wallA.to[0] * 0.9, wallA.to[1], wallA.to[2], flash.position); flash.intensity = 5 * pw; }
      f.splats = hits.filter((h) => t >= h.t).map((h, i) => ({ t0: h.t, x: [0.42, 0.6, 0.5][i], y: [0.55, 0.42, 0.35][i], r: 12 + 4 * i, seed: 21 + i }));
      f.black = 0.5 * sstep(T_LAST, DUR + 0.3, t);
    }
    return { dur: DUR, hits, cam, update, sounds, loops, deathSide: -1,
      marks: { dread: tRattle + 0.6, fake: tArrow + 0.06, lunge: t0 + (fromSide ? 0.32 : 0.5), kill: T_FIRE + 0.12 },
      notes: { torches: dying.length, last: !!last, fromSide, t0: +t0.toFixed(2), shot: +T_S1.toFixed(2), dur: +DUR.toFixed(2) } };
  }
};
