// Skeleton: power out. The torches ahead go out one by one, coming toward you, each with a fizz and a curl of smoke.
// In the dark a music box starts (a note-block waltz), winding down, and with every note two pinprick eyes blink in
// the black ahead. Sometimes a bowstring creaks mid-tune and an arrow thuds into the wall by your head. The tune stops
// mid-phrase (never at the same note). The eyes go out. Silence, longer or shorter every time. Then the skull is in
// your face, jaw dropping, from where the eyes were or from beside you. It throws you down, stands over you, draws,
// and fires into you at point blank.
import { THREE, track, clamp, lerp, sstep, pulse, tex } from "./rig.js";
import { settle, shake, hitsOf, floorFall, arrowMesh, arrowAim, particles, smoke, mcRot, glowEyes } from "./common.js";
import { lunge, lungeFx, screech, splitJaw, faceAnchor, boxOf, silence, deathScream, musicBox, jit } from "./fnaf.js";

// A descending minor waltz, arpeggios sinking a semitone a bar: note-block steps (12 = F#4).
const TUNE = [24, 19, 15, 24, 19, 15, 22, 18, 15, 22, 18, 14, 20, 17, 13, 19, 15, 12, 18, 15, 11, 17, 14, 10];

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
    const T0 = 0.95, T_DARK = T0 + R.vary(2.4, 0.3);
    const outAt = ahead.map((tc, i) => T0 + (T_DARK - 0.1 - T0) * Math.pow(i / Math.max(1, ahead.length - 1), 0.8) + (R.rand() - 0.5) * 0.15);
    rest.forEach(() => outAt.push(T_DARK - 0.15));
    // the last one goes too, on the last note (power out)
    const dying = ahead.concat(rest);
    const tTune = T_DARK + R.vary(0.9, 0.4);
    const stopAt = 6 + Math.floor(R.rand() * 7);               // the tune stops somewhere between the 6th and 12th note
    const box = musicBox(tTune, TUNE, { step: R.vary(0.32, 0.12), wind: 0.09, sag: 0.008, stopAt, volume: 0.6 });
    const noteTimes = box.sounds.map((s) => s[0]);
    const tEnd = box.end - 0.05;
    const arrowFake = R.chance(0.55);
    const tArrow = arrowFake ? noteTimes[Math.max(2, Math.floor(noteTimes.length * R.vary(0.55, 0.25)))] + 0.12 : null;
    const fromSide = R.chance(0.45);                         // the lunge from beside you, not from where the eyes were
    const t0 = tEnd + R.vary(1.35, 0.5);
    const lside = (R.wallR > R.wallL ? 1 : -1) * (arrowFake ? -1 : 1);

    const sk = R.mob("Skeleton", { equipment: [{ id: "minecraft:bow", ench: false }], amb: [0.04, 0.04, 0.04], own: true });
    const jaw = splitJaw(sk, [{ part: sk.parts.head, box: boxOf("skeleton", "bipedHead"), rows: 2 }], { nTeeth: 0, max: 0.7, mouth: 0x050505, tongue: 0x140303 });
    const eyes = glowEyes(R, sk, [[-1.5, -3.5, -4.07, 1, 1], [1.5, -3.5, -4.07, 1, 1]], [1, 0.95, 0.85], { halo: 0.16, glow: 0.5 });
    sk.anim(0, 0, { walk: 0 }); R.place(sk, 0, 0, 3, Math.PI);
    const anchor = faceAnchor(sk, sk.parts.head, boxOf("skeleton", "bipedHead")); anchor.y -= 0.06;
    const lx = last ? clamp(last.l.x * 0.5, -1.0, 1.0) : 0.3;
    const SZ = last ? clamp(last.l.z - 1.0, 1.5, 2.1) : clamp(R.ahead - 0.5, 1.2, 1.6);
    const eyesAt = { x: clamp(lx * 0.4, -0.6, 0.6), z: clamp(R.ahead - 0.8, 3.2, 6.5) };   // in the dark past the last light
    const start = fromSide ? { x: lside * clamp((lside < 0 ? R.wallL : R.wallR) - 0.4, 0.5, 0.85), z: 0.05 } : eyesAt;
    const L = lunge(R, sk, { t0, rush: fromSide ? 0.17 : R.vary(0.24, 0.12), hold: R.vary(0.6, 0.15), dist: 0.36, anchor, seed: 7, side: fromSide ? lside * 0.2 : 0 });
    const tK = L.t3;
    const T_FIRE = tK + 1.05, T_LAST = T_FIRE + 0.95, DUR = T_LAST + 0.3;
    const torchGlow = R.ownLight(R.light(0xffb060, 0, 7, 1.3));
    const flash = R.ownLight(R.light(0xfff0b0, 0, 4, 1.4));
    const cold = R.ownLight(R.light(0xb8c4d8, 0, 3, 1.4));

    // Arrows: one into the wall by the head (the fake), two into you at point blank.
    const wl = Math.min(R.wallL, 4), wr = Math.min(R.wallR, 4);
    const shotFrom = [lx * 0.6, 1.5, Math.min(R.ahead - 0.6, 9)];
    const A = [
      ...(arrowFake ? [{ t: tArrow, to: lside > 0 ? [-wl + 0.02, 1.72, 0.45] : [wr - 0.02, 1.72, 0.45], wall: true }] : []),
      { t: T_FIRE, to: [0, 1.25, 0.1], you: true, close: true },
      { t: T_LAST, to: [0, 0.3, 0.0], you: true, close: true }
    ];
    const arrows = A.map((a) => { const m = arrowMesh(arrowTex); m.visible = false; R.add(m); return { ...a, m }; });
    const hits = hitsOf([[tK + 0.05, 4, lside], [T_FIRE + 0.05, 9, 1], [T_LAST + 0.05, 7, -1]]);
    const wallA = arrows.find((a) => a.wall);

    // The head: follows each dying torch a little; held on the dark ahead through the tune; flinches at the thud;
    // snapped toward the lunge; thrown down; looks up at it.
    const sideOf = (tc) => clamp(R.yawTo(0, 0, tc.l.x, tc.l.z) * 0.55, -0.6, 0.6);
    const yk = [[0, 0], [0.9, 0]];
    const ord = ahead.map((tc, i) => [outAt[i], sideOf(tc)]).sort((a, b) => a[0] - b[0]);
    for (const [ot, y] of ord) if (ot + 0.25 > yk[yk.length - 1][0] + 0.05) yk.push([ot + 0.25, y]);
    yk.push([T_DARK + 0.35, 0], [tTune + 0.4, R.yawTo(0, 0, eyesAt.x, eyesAt.z) * 0.8]);
    if (wallA) yk.push([tArrow - 0.01, R.yawTo(0, 0, eyesAt.x, eyesAt.z) * 0.8, "h"], [tArrow + 0.12, -lside * 0.55, "x"], [tArrow + 0.7, -lside * 0.4], [tArrow + 1.6, R.yawTo(0, 0, eyesAt.x, eyesAt.z) * 0.6]);
    yk.push([tEnd + 0.2, R.yawTo(0, 0, eyesAt.x, eyesAt.z) * 0.6], [t0, 0.05 * lside], [L.t1, fromSide ? lside * 0.35 : 0, "x"], [tK, 0, "h"]);
    const yaw = track(yk.filter((k, i, a) => i === 0 || k[0] > a[i - 1][0]));
    const pitch = track([[0, 0], [0.9, -0.02], [T_DARK, 0.02], [tEnd, 0.03], [t0, 0.0], [L.t1, 0.04, "x"], [tK, 0.05, "h"]]);
    const cam = (t) => {
      const s = settle(R, t, 0.9);
      const k = sstep(0.8, 1.3, t);
      const c = { x: s.x * (1 - k), y: s.y, z: s.z * (1 - k), yaw: lerp(s.yaw, yaw(t), k), pitch: lerp(s.pitch, pitch(t), k), roll: 0, fov: s.fov - 4 * sstep(tTune, tEnd, t) + 8 * pulse(t, [L.t1], 0.15), near: t >= t0 && t < tK ? 0.02 : undefined };
      if (wallA) c.z -= 0.08 * pulse(t, [tArrow], 0.15);
      shake(c, t, 0.002 + 0.002 * sstep(1, T_DARK, t) + (wallA ? 0.025 * pulse(t, [tArrow], 0.12) : 0) + L.shake(t) + 0.03 * pulse(t, hits.map((h) => h.t), 0.2), 7);
      floorFall(c, t, tK + 0.02, { d: 0.55, side: -lside || -1, roll: 1.15, y: 0.26, pitch: 0.55, back: 0.45 });
      if (t > tK + 0.45) {   // on the floor, looking up at it
        const k2 = sstep(tK + 0.45, T_FIRE - 0.3, t), zs = SZ - 0.35;
        c.yaw = lerp(c.yaw, R.yawTo(c.x, c.z, lx, zs), k2); c.pitch = lerp(c.pitch, R.pitchTo(c.x, c.y, c.z, lx, 1.45, zs), k2); c.roll = lerp(c.roll, 0.35, k2);
      }
      return c;
    };

    const puffs = particles(R, partTex, dying.flatMap((tc, i) => smoke([tc.l.x, tc.l.y + 0.75, tc.l.z], outAt[i], 7, { spread: 0.15, window: 0.25, life: 1.4, size: 0.18, rise: 0.5, seed: 30 + i }))
      .concat(last ? smoke([last.l.x, last.l.y + 0.75, last.l.z], tEnd, 8, { spread: 0.15, window: 0.25, life: 1.6, size: 0.2, rise: 0.5, seed: 29 }) : []));
    if (wallA) { R.burst(wallA.t, wallA.to, 18, "spark", { dir: [-Math.sign(wallA.to[0]) * 0.8, 0.7, -0.4], speed: 3, spread: 0.6, size: 0.03, life: 0.45, grav: 12 }); R.burst(wallA.t, wallA.to, 8, "stone", { dir: [-Math.sign(wallA.to[0]) * 0.6, 0.3, -0.2], speed: 1.6, spread: 0.5, size: 0.045, life: 0.9 }); }
    hits.forEach((h, i) => R.burst(h.t, i === 2 ? [0, 0.35, 0.25] : [0.04, 1.2, 0.35], 26, "blood", { dir: [0, 0.7, 0.9], speed: 2.3, spread: 0.7, size: 0.05, life: 1.2, stick: 3 }));

    const S2 = screech(L, [["mob.skeleton.say", { pitch: 0.5 }], ["mob.skeleton.hurt", { pitch: 0.55, volume: 1.2 }]]);
    const sounds = [
      ...dying.map((tc, i) => [outAt[i], "random.fizz", { at: [tc.l.x, tc.l.y + 0.6, tc.l.z], volume: 0.75, pitch: 0.9 + (i % 3) * 0.08 }]),
      ...box.sounds.map(([tt, n, o]) => [tt, n, { ...o, at: [eyesAt.x, 1.6, eyesAt.z + 0.5] }]),
      ...(wallA ? [[tArrow - 0.55, "random.door_open", { at: shotFrom, volume: 0.22, pitch: 1.9 }], [tArrow - 0.07, "random.bow", { at: shotFrom, volume: 0.9 }], [tArrow, "random.bowhit", { at: wallA.to, volume: 1 }], [tArrow + 0.02, "qf.scare.stinger", { volume: 0.7 }]] : []),
      ...(last ? [[tEnd, "random.fizz", { at: [last.l.x, last.l.y + 0.6, last.l.z], volume: 0.7, pitch: 0.8 }]] : []),
      silence(tEnd + 0.02, { fade: 0.05 }),
      [tEnd + (t0 - tEnd) * 0.55, "mob.skeleton.step", { at: [start.x, 0, start.z + 0.3], volume: 0.18, pitch: 0.8 }],
      ...S2.sounds,
      [tK + 0.45, "game.player.hurt.fall.small"],
      ...deathScream(tK + 0.15, { volume: 1.1, under: false }),
      [T_FIRE - 0.75, "random.door_open", { at: [lx, 1.5, SZ], volume: 0.3, pitch: 2.0 }],
      [T_FIRE - 0.04, "random.bow", { at: [lx, 1.5, SZ], volume: 1 }], [T_LAST - 0.04, "random.bow", { at: [lx, 1.5, SZ], volume: 1 }],
      ...hits.slice(1).flatMap((h, i) => [[h.t, "game.player.hurt"], [h.t + 0.01, "random.bowhit", { volume: 0.9 }], [h.t + 0.03, i === 0 ? "qf.scare.crunch" : "qf.scare.gore", { volume: 1 }]]),
      [T_FIRE + 0.3, "mob.skeleton.say", { at: [lx, 1.6, SZ], volume: 0.9, pitch: 0.7 }],
      ...deathScream(T_LAST + 0.06, { volume: 1.3 }),
      [DUR, "game.player.die"], [DUR, "@muffle", { hz: 420, s: 3 }]
    ];
    const loops = [
      [0.5, tTune, "qf.scare.heartbeat", { volume: 0.5, fadeOut: 1.2 }],
      [T_DARK - 0.4, tEnd, "qf.scare.breath", { volume: 0.32, fadeIn: 1.2, fadeOut: 0.05 }],
      ...S2.loops,
      [tK, DUR + 0.2, "qf.scare.heartbeat", { volume: 0.7, pitch: 1.35 }]
    ];

    const pose = (t) => {
      const P = sk.parts;
      const draw = sstep(T_FIRE - 0.75, T_FIRE - 0.35, t) * (1 - sstep(T_FIRE - 0.02, T_FIRE + 0.05, t)) + sstep(T_FIRE + 0.35, T_LAST - 0.2, t) * (1 - sstep(T_LAST - 0.02, T_LAST + 0.05, t));
      if (P.rightArm) {
        const hx = P.head ? -P.head.rotation.x : 0;
        mcRot(P.rightArm, -Math.PI / 2 + hx, -0.1, 0); mcRot(P.leftArm, -Math.PI / 2 + hx, 0.1 + 0.4 * draw, 0);
      }
    };
    function update(t, f) {
      const camNow = R.camera;
      puffs(t);
      let gone = 0;
      dying.forEach((tc, i) => { if (t >= outAt[i]) R.snuff(tc); gone += sstep(outAt[i], outAt[i] + 0.2, t); });
      // The last torch dies with the tune; after the lunge it sputters back on over you.
      const relit = t >= tK + 0.25 && (t > tK + 0.75 || Math.sin((t - tK) * 47) > -0.2);
      if (last) { if (t >= tEnd && !relit) R.snuff(last); else R.unsnuff(last); }
      const dark = dying.length ? gone / dying.length : sstep(1, T_DARK, t);
      const black = sstep(tEnd, tEnd + 0.1, t) * (t < tK + 0.25 ? 1 : 1 - sstep(tK + 0.25, tK + 0.8, t));   // power out: nothing but the lunge
      f.env = { bake: lerp(1, 0.1, dark) * (1 - 0.15 * sstep(0.2, 1, t)) * (1 - 0.85 * black), lights: lerp(1, 0.65, dark) * (1 - black), fogMul: 1 + 1.5 * dark + 2 * black, expo: 1 - 0.15 * dark };
      f.vig = [0, 0, 0, 0.25 + 0.4 * dark]; f.vigR = 0.85;
      if (last) { R.L(last.l.x * 0.85, last.l.y + 0.6, last.l.z, torchGlow.position); torchGlow.intensity = (7 * dark + (t > tK ? 4 : 0)) * (0.9 + 0.1 * Math.sin(t * 23)) * (t < tEnd || relit ? 1 : 0); }
      else { R.L(lx, 2.6, SZ - 0.4, torchGlow.position); torchGlow.intensity = 4 * dark * (t < tEnd || relit ? 1 : 0); }
      // The skeleton: in the dark ahead through the tune (only its eyes); the lunge; then over you.
      let open = 0, lit = 0, eyeOn = 0;
      sk.pivot.visible = t > tTune - 0.2;
      if (t < t0) {
        R.place(sk, start.x, 0, start.z, R.yawTo(start.x, start.z, 0, 0));
        sk.anim(t, 0, { walk: 0 }); pose(t);
        eyeOn = t < tEnd ? Math.max(...noteTimes.map((n) => (t >= n && t < n + 0.16 ? 1 - (t - n) / 0.3 : 0)), 0.04) : 0;
        if (fromSide) eyeOn = 0;
        if (fromSide && t < tEnd) { R.place(sk, eyesAt.x, 0, eyesAt.z, R.yawTo(eyesAt.x, eyesAt.z, 0, 0)); eyeOn = Math.max(...noteTimes.map((n) => (t >= n && t < n + 0.16 ? 1 - (t - n) / 0.3 : 0)), 0.04); }
        sk.setOwn(0.0);
      } else if (t < tK) {
        R.place(sk, start.x, 0, start.z, R.yawTo(start.x, start.z, 0, 0));
        sk.anim(t, 0, { walk: 0 });
        // Arms out wide and low, reaching past the lens (the bow out of the way).
        const P = sk.parts; if (P.rightArm) { mcRot(P.rightArm, -1.15 + jit(t, 41) * 0.2, 0.5, 0.35); mcRot(P.leftArm, -1.15 + jit(t, 43) * 0.2, -0.5, -0.35); }
        if (P.head) P.head.rotation.set(0.04 + jit(t, 21) * 0.08, jit(t, 23) * 0.1, jit(t, 25) * 0.09);
        L.apply(t);
        open = sstep(t0, L.t1, t) * (0.85 + 0.15 * jit(t, 31)); lit = 1; eyeOn = 1;
        sk.setOwn(0.6);
      } else {
        const kz = sstep(tK, tK + 0.6, t), cl = R.toLocal(camNow.position);
        const x = lerp(0, lx, kz), z = lerp(0.9, SZ, kz) + 0.35 * sstep(T_FIRE + 0.4, T_LAST - 0.3, t) * -1;
        R.place(sk, x, 0, z, R.yawTo(x, z, cl.x, cl.z));
        sk.anim(t, 0, { walk: t < tK + 0.6 ? 1 : 0 });
        if (sk.parts.head) sk.parts.head.rotation.x = clamp(Math.atan2(cl.y - 1.62, Math.hypot(cl.x - lx, cl.z - z)) * 0.8, -0.8, 0.4);
        pose(t);
        open = 0.15 + 0.5 * pulse(t, [T_FIRE, T_LAST], 0.25); eyeOn = 0.8;
        sk.setOwn(relit ? 0.32 : 0.12);
      }
      jaw.set(open); eyes(eyeOn);
      cold.position.set(0, 0.05, -0.1).applyQuaternion(camNow.quaternion).add(camNow.position); cold.intensity = 0.6 * lit;
      for (const a of arrows) {
        const from = a.close ? [lx - 0.3, 1.45, SZ - 0.3] : shotFrom;
        const k = clamp((t - (a.t - 0.1)) / 0.1);
        a.m.visible = t >= a.t - 0.1 && !a.you;
        if (!a.m.visible) continue;
        const p = [lerp(from[0], a.to[0], k), lerp(from[1], a.to[1], k), lerp(from[2], a.to[2], k)];
        R.at(a.m, p[0], p[1], p[2]);
        const d = R.dirW(a.to[0] - from[0], a.to[1] - from[1], a.to[2] - from[2]);
        arrowAim(a.m, new THREE.Vector3(d[0], d[1], d[2]));
        if (a.wall && t > a.t) a.m.rotateZ(Math.sin((t - a.t) * 60) * 0.08 * Math.exp(-(t - a.t) * 5));
      }
      if (wallA) { const pw = pulse(t, [wallA.t], 0.09); R.L(wallA.to[0] * 0.9, wallA.to[1], wallA.to[2], flash.position); flash.intensity = 5 * pw; }
      f.splats = hits.filter((h) => t >= h.t).map((h, i) => ({ t0: h.t, x: [0.42, 0.6, 0.5][i], y: [0.55, 0.42, 0.35][i], r: 12 + 4 * i, seed: 21 + i }));
      f.black = 0.5 * sstep(T_LAST, DUR + 0.3, t);
      lungeFx(L, t, f);
    }
    return { dur: DUR, hits, cam, update, sounds, loops, deathSide: -1,
      marks: { dread: tTune + (tEnd - tTune) * 0.3 + 0.02, fake: wallA ? tArrow + 0.06 : noteTimes[Math.max(0, noteTimes.length - 2)] + 0.02, lunge: L.t1 + 0.12, kill: T_FIRE + 0.12 },
      notes: { torches: dying.length, last: !!last, notes: noteTimes.length, arrowFake, fromSide, t0: +t0.toFixed(2), dur: +DUR.toFixed(2) } };
  }
};
