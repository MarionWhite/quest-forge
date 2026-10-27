// Spider (round 7: the ceiling). Clicking overhead, moving. The head tilts up, slowly. Either it is up there, crawling
// upside down across the ceiling toward you, and it stops right above, its red eyes (they glow, as in the game) on
// you; or the ceiling is bare. The clicking stops. Silence. The neck gives and the head comes back down to the
// corridor. Then it drops off the ceiling in front of you, turning over as it falls, and lands with a thump, legs
// splayed. It rears and hisses, and leaps: the whole of it comes at your face and its legs close round the view. It
// bites; you are hauled up into the dark and left dangling over the corridor, turning slowly on the thread.
import { THREE, track, clamp, lerp, sstep, pulse, tex, quad } from "./rig.js";
import { settle, shake, hitsOf, lensLimbs, halo } from "./common.js";
import { splitJaw, boxOf, silence, deathScream } from "./fnaf.js";
import { roar, hop } from "./story.js";

export default {
  death: "Steve was slain by Spider",
  async build(R) {
    const webTex = await tex("web");
    const ceil = R.ceil > 7 ? 4.5 : R.ceil;
    const sz = 1.9, sx = 0.1;
    const sp = R.mob("Spider", { amb: [0.02, 0.02, 0.02], own: true });
    const jaw = splitJaw(sp, [{ part: sp.parts.head, box: boxOf("spider", "spiderHead"), rows: 2 }], { nTeeth: 0, max: 0.7, mouth: 0x0a0000, tongue: 0x2a0404 });
    const legDonor = R.mob("Spider"); legDonor.pivot.visible = false;
    sp.anim(0, 0, { walk: 0 }); R.place(sp, 0, 0, 3, Math.PI);
    const eyeGlow = [halo(R, new THREE.Color(1, 0.08, 0.04), 0.22), halo(R, new THREE.Color(1, 0.08, 0.04), 0.22)];
    // ---- the dice -------------------------------------------------------------------------------------------
    const eyesUp = R.chance(0.55);
    const T_CLICK = 0.9 + R.vary(0.3, 0.5), T_UP0 = T_CLICK + R.vary(0.9, 0.35), T_UP1 = T_UP0 + R.vary(1.25, 0.25);
    const landX = 0.08, landZ = clamp(R.ahead - 0.9, 1.25, 1.85);       // where it comes down: just ahead
    const KZ = 1.3;                                                     // on your face: its body that far out, the head and fangs nearer
    const farZ = clamp(Math.min(sz + 2.2, R.ahead - 0.5), landZ + 0.5, 6);
    const T_CR0 = T_UP1 - 0.6, T_CR1 = T_UP1 + 0.9;                     // (a) crawling over the ceiling to above it
    const tSil = eyesUp ? T_CR1 + R.vary(0.7, 0.4) : T_UP1 + R.vary(0.6, 0.4);
    const tD0 = tSil + R.vary(0.5, 0.4), tD1 = tD0 + R.vary(0.9, 0.25);
    const tDrop = tD1 + R.vary(0.7, 0.5), fallT = Math.sqrt(2 * Math.max(1.5, ceil) / 32), tLand = tDrop + fallT;
    const tLeap = tLand + R.vary(0.55, 0.3), tK = tLeap + 0.24;         // it lands on you at tK
    const T_HAUL = tK + 1.45, DUR = tK + 3.55;
    const hang = Math.max(2.3, ceil - 0.45);
    const hits = hitsOf([[tK + 0.05, 4, 1], [tK + 0.55, 4, -1], [tK + 1.05, 3, 1], [T_HAUL + 1.1, 4, -1], [DUR - 0.1, 5, 1]]);
    const upP = R.pitchTo(0, R.eye, 0, sx, ceil - 0.3, sz), upFar = R.pitchTo(0, R.eye, 0, sx, ceil - 0.3, farZ), upLand = R.pitchTo(0, R.eye, 0, landX, ceil - 0.3, landZ - 0.4);
    const pLand = R.pitchTo(0, R.eye, 0, landX, 0.45, landZ - 0.6), pRear = R.pitchTo(0, R.eye, 0, landX, 0.75, landZ - 0.6);
    const pk = [[0, 0], [T_UP0, -0.02]];
    if (eyesUp) pk.push([T_CR0, upFar, "s"], [T_CR1, Math.min(upLand, 1.15)], [tD0, Math.min(upLand, 1.15) - 0.05]);
    else pk.push([T_UP1, upP, "s"], [tD0, upP]);
    pk.push([tD1, -0.04, "s"], [tDrop + 0.05, -0.04, "h"], [tLand + 0.08, pLand, "x"], [tLeap, pRear], [tK, 0.15, "x"], [tK + 0.2, 0.2], [T_HAUL, 0.12], [T_HAUL + 0.9, -1.05, "i"], [DUR, -1.25]);
    const pitch = track(pk);
    const yawT = track([[0, 0], [tSil, 0], [tSil + 0.35, eyesUp ? 0.25 : -0.2], [tD0, eyesUp ? -0.15 : 0.18], [tD1, 0], [tDrop + 0.05, 0, "h"], [tLand + 0.08, R.yawTo(0, 0, landX, landZ) , "x"]]);
    const eyeY = track([[0, R.eye], [tK, R.eye], [tK + 0.3, R.eye - 0.15], [T_HAUL, R.eye - 0.1], [T_HAUL + 1.1, hang, "i"], [DUR, hang + 0.08]]);
    const back = track([[0, 0], [tLand, 0], [tLand + 0.15, -0.12, "o"], [tK - 0.01, -0.12, "h"], [tK + 0.15, -0.4, "o"], [T_HAUL, -0.55], [T_HAUL + 1.1, -0.2]]);
    // Where it is from the landing to your face (the leap aims at where your head will be when it lands).
    const killAt0 = { x: 0, y: R.eye - 0.5, z: -0.12 + KZ };
    const leapAt = (t) => {
      const bounce = 0.07 * Math.exp(-(t - tLand) * 14) * Math.abs(Math.sin((t - tLand) * 22)), u = clamp((t - tLeap) / (tK - tLeap));
      const p0 = { x: landX, y: bounce, z: landZ };
      return t < tLeap ? p0 : hop(p0, killAt0, u * u * (1.5 - 0.5 * u), 0.3);
    };
    const cam = (t) => {
      const s = settle(R, t, 0.9);
      const k = sstep(0.8, 1.3, t);
      const c = { x: s.x * (1 - k), y: lerp(s.y, eyeY(t), k), z: lerp(s.z, back(t), k), yaw: lerp(s.yaw, yawT(t), k), pitch: lerp(s.pitch, pitch(t), k), roll: 0, fov: s.fov + 6 * pulse(t, [tK], 0.12), near: t >= tLeap - 0.1 ? 0.02 : undefined };
      if (t > tLand && t < tK + 0.2) {   // the eyes stay on it as it rears and comes
        const q = leapAt(Math.min(t, tK)), hz = q.z - 0.55, hy = q.y + 0.45 + 0.25 * sstep(tLand + 0.12, tLeap, t);
        const kq = sstep(tLand, tLand + 0.08, t) * (1 - sstep(tK, tK + 0.2, t));
        c.pitch = lerp(c.pitch, clamp(R.pitchTo(c.x, c.y, c.z, q.x, hy, hz), -1.2, 0.3), kq);
      }
      const d = sstep(T_HAUL + 0.4, T_HAUL + 1.4, t);
      c.yaw += d * (t - T_HAUL) * 0.55; c.roll += d * Math.sin((t - T_HAUL) * 2.1) * 0.12; c.x += d * Math.sin((t - T_HAUL) * 2.1) * 0.12;
      c.fov += 8 * sstep(T_HAUL, T_HAUL + 1, t);
      return shake(c, t, 0.002 + 0.003 * sstep(T_UP0, tSil, t) + 0.03 * pulse(t, [tLand], 0.15) + 0.025 * sstep(tK, tK + 0.1, t) * (1 - 0.6 * sstep(tK + 0.2, T_HAUL, t)) + 0.02 * pulse(t, hits.map((h) => h.t), 0.2), 6);
    };
    const Lg = (fx, fy, tx, ty, t1, ph) => ({ from: [fx, fy], to: [tx, ty], t0: t1, t1: t1 + 0.18, z: -0.26, scale: 0.42, axis: "x-", twist: 0.12, ph, curl: 0.25 * Math.sign(fx) });
    const legs = lensLimbs(R, legDonor, "spiderLeg1", [
      Lg(-0.62, 0.22, -0.2, 0.12, tK - 0.02, 0), Lg(-0.62, -0.05, -0.22, -0.02, tK, 1), Lg(-0.6, -0.3, -0.2, -0.16, tK + 0.02, 2),
      Lg(0.62, 0.24, 0.2, 0.13, tK - 0.01, 3), Lg(0.62, -0.04, 0.23, -0.01, tK + 0.01, 4), Lg(0.6, -0.3, 0.2, -0.15, tK + 0.03, 5)
    ], { color: 0x5a5050 });
    const webs = [[-0.22, 0.12, 0.3], [0.2, -0.1, -0.4], [0.05, 0.16, 1.1], [-0.15, -0.14, 2]].map(([x, y, r], i) => {
      const q = quad(webTex, 0.17, 0.17, { transparent: true, opacity: 0.0, depthTest: false, fog: false, color: 0x4a4a4a });
      q.material.depthWrite = false; q.renderOrder = 2100; q.position.set(x, y, -0.22); q.rotation.z = r; R.view.add(q); return { q, i };
    });
    const clicks = [];
    const crawlAt = (t) => ({ x: lerp(sx, landX, sstep(T_CR0, T_CR1, t)), z: lerp(farZ, landZ, sstep(T_CR0, T_CR1, t)) });
    for (let tt = T_CLICK, i = 0; tt < tSil - 0.1; tt += R.vary(0.42, 0.3), i++) {
      const q = eyesUp && tt > T_CR0 ? crawlAt(tt) : { x: sx + Math.sin(i) * 0.8, z: sz + 1.6 - Math.min(1.6, i * 0.3) };
      clicks.push([tt, "mob.spider.step", { at: [q.x, ceil, q.z], volume: 0.45 + 0.04 * Math.min(i, 5), pitch: 0.9 }]);
    }
    const sounds = [
      ...clicks,
      ...(eyesUp ? [[T_CR1 + 0.15, "mob.spider.say", { at: [landX, ceil - 0.4, landZ], volume: 0.5, pitch: 0.75 }]] : []),
      silence(tSil),
      [tDrop - 0.02, "dig.cloth", { at: [landX, ceil - 0.2, landZ], volume: 0.25, pitch: 0.6 }],
      // It lands: the thump; then it rears and hisses; the leap.
      [tLand, "mob.spider.step", { at: [landX, 0, landZ], volume: 1.2, pitch: 0.7 }], [tLand + 0.005, "game.hostile.hurt.fall.small", { at: [landX, 0, landZ], volume: 0.9 }], [tLand + 0.01, "qf.scare.hit", { volume: 0.55 }],
      ...roar(tLand + 0.14, [["mob.spider.say", { at: [landX, 0.6, landZ - 0.5], pitch: 0.6 }]], { hit: 0 }),
      [tLeap, "mob.spider.say", { at: [landX, 0.6, landZ - 0.5], volume: 1.3, pitch: 0.85 }],
      ...hits.flatMap((h, i) => [[h.t, "game.player.hurt"], [h.t + 0.01, "qf.scare.hit", { volume: i ? 0.55 : 1.0 }], [h.t + 0.02, i % 2 ? "qf.scare.gore" : "qf.scare.crunch", { volume: 1 }], [h.t - 0.05, "mob.spider.say", { volume: 0.6, pitch: 1.1 }]]),
      ...deathScream(tK + 0.12, { volume: 1.1, under: false }),
      [T_HAUL + 0.1, "dig.cloth", { volume: 0.8, pitch: 0.6 }],
      [T_HAUL + 1.4, "mob.spider.step", { volume: 0.5 }], [T_HAUL + 1.9, "mob.spider.step", { volume: 0.5 }],
      ...deathScream(T_HAUL + 0.15, { volume: 1.3 }),
      [DUR, "game.player.die"], [DUR, "@muffle", { hz: 380, s: 3 }]
    ];
    const loops = [
      [0.6, tSil, "qf.scare.heartbeat", { volume: 0.55 }],
      [T_UP0, tSil, "qf.scare.drone", { volume: 0.4, fadeIn: 1.2, fadeOut: 0.05, bus: "sfx" }],
      [tLand, tK, "qf.scare.heartbeat", { volume: 0.6, pitch: 1.3, fadeIn: 0.05 }],
      [tK, DUR + 0.2, "qf.scare.heartbeat", { volume: 0.7, pitch: 1.35 }],
      [T_HAUL + 0.6, DUR, "qf.scare.breath", { volume: 0.5, fadeIn: 0.6 }]
    ];
    hits.forEach((h, i) => R.burst(h.t, i < 3 ? [0, 1.35, 0.25] : [0, hang - 0.25, 0], 24, "blood", { dir: i < 3 ? [0, 0.5, 0.8] : [0, -0.2, 0], speed: 1.8, spread: 0.6, size: 0.045, life: 1.8, stick: 3 }));
    for (let k = 0; k < 7; k++) R.burst(T_HAUL + 1.0 + k * 0.28, [0.02 * (k % 3), hang - 0.4, 0.02], 2, "blood", { dir: [0, -1, 0], speed: 0.3, spread: 0.05, size: 0.035, life: 1.6, stick: 4 });
    const _v = new THREE.Vector3();

    function update(t, f) {
      const camNow = R.camera, cl = R.toLocal(camNow.position);
      let open = 0, eyes = 0;
      const killAt = { x: cl.x, y: cl.y - 0.5, z: cl.z + KZ }, faceYaw = R.yawTo(sx, sz, 0, 0);
      if (t < tDrop) {
        // On the ceiling: (a) crawling over it toward you and stopping above, eyes on you; (b) out of sight up there.
        const q = eyesUp ? crawlAt(t) : { x: landX, z: landZ };
        R.place(sp, q.x, ceil, q.z, R.yawTo(q.x, q.z, 0, 0) + 0.1 * Math.sin(t * 0.7), -0.45, Math.PI);
        sp.anim(t, 0, { walk: eyesUp && t > T_CR0 && t < T_CR1 ? 0.8 : 0.05 });
        sp.pivot.visible = eyesUp && t > T_CR0 - 0.3;
        eyes = sp.pivot.visible ? 0.8 + 0.2 * Math.sin(t * 3) : 0;
        sp.setOwn(ceil > 4.6 ? 0.07 : 0.03);
      } else if (t < tLand) {
        // The drop: it lets go and turns over as it falls.
        const u = (t - tDrop) / fallT, y = Math.max(0, ceil - 16 * (t - tDrop) ** 2);
        R.place(sp, landX, y, landZ, R.yawTo(landX, landZ, cl.x, cl.z), lerp(-0.45, 0.1, u), lerp(Math.PI, 0, sstep(0.1, 0.9, u)));
        sp.anim(t * 3, 0, { walk: 1.5 });
        sp.pivot.visible = true; eyes = 0.8;
        sp.setOwn(0.08);
      } else if (t < tK) {
        // Down: a bounce, legs splayed; it rears and hisses; the leap, the whole of it, at your face.
        const rear = sstep(tLand + 0.12, tLeap, t), u = clamp((t - tLeap) / (tK - tLeap)), q = leapAt(t);
        R.place(sp, q.x, q.y, q.z, lerp(R.yawTo(landX, landZ, cl.x, cl.z), faceYaw, sstep(0, 1, u)), lerp(-0.32 * rear, -0.22, u), 0);
        sp.anim(t * (t < tLeap ? 1.5 : 3), 0, { walk: t < tLand + 0.15 || t > tLeap ? 2 : 0.3 });
        sp.pivot.visible = true;
        open = 0.15 + 0.55 * sstep(tLand + 0.1, tLand + 0.25, t) * (1 - 0.5 * sstep(tLand + 0.4, tLeap, t)) + 0.5 * u;
        eyes = 0.9;
        sp.setOwn(0.08 + 0.12 * rear);
      } else {
        // On your face.
        const tz = killAt.z - 0.08 * pulse(t, hits.slice(0, 3).map((h) => h.t - 0.05), 0.1);
        R.place(sp, killAt.x, killAt.y, tz, faceYaw, -0.22, 0);
        sp.anim(t * 3, 0, { walk: 2 });
        sp.pivot.visible = t < T_HAUL + 0.25;
        open = 0.3 + 0.7 * pulse(t, hits.slice(0, 3).map((h) => h.t - 0.05), 0.15); eyes = 0.8;
        sp.setOwn(0.06 * (1 - sstep(T_HAUL, T_HAUL + 0.3, t)));
      }
      jaw.set(open);
      // The two big eyes burn.
      sp.pivot.updateMatrixWorld(true);
      eyeGlow.forEach((h, i) => {
        h.visible = eyes > 0.01 && sp.pivot.visible;
        if (!h.visible) return;
        _v.set((i ? -1 : 1) * 1.5 / 16, 0.5 / 16, -8.1 / 16); sp.parts.head.localToWorld(_v); h.position.copy(_v);
        h.material.opacity = 0.55 * eyes; h.scale.setScalar(Math.min(1, _v.distanceTo(camNow.position) / 1.6));
      });
      legs(t);
      const w = sstep(T_HAUL + 0.3, T_HAUL + 1.4, t);
      for (const { q, i } of webs) q.material.opacity = 0.5 * w * sstep(T_HAUL + 0.3 + i * 0.15, T_HAUL + 0.8 + i * 0.15, t);
      const sil = sstep(tSil, tSil + 0.5, t) * (t < tDrop ? 1 : 0);
      f.env = { bake: 1 - 0.3 * sstep(0.3, 1.5, t) - 0.25 * sstep(T_UP0, T_UP1, t) - 0.15 * sil - 0.25 * w, lights: 1 - 0.35 * sstep(T_UP0, T_UP1, t) - 0.2 * sil, fogMul: 1 + 0.8 * sstep(1, 3, t) };
      f.vig = [0, 0, 0, 0.3 + 0.3 * sstep(T_UP0, T_UP1, t) + 0.25 * w]; f.vigR = 0.85;
      f.splats = hits.slice(0, 3).filter((h) => t >= h.t).map((h, i) => ({ t0: h.t, x: [0.4, 0.62, 0.5][i], y: [0.5, 0.38, 0.6][i], r: 13 + i * 3, seed: 41 + i }));
      f.black = 0.6 * sstep(DUR - 0.3, DUR + 0.4, t);
    }
    return { dur: DUR, hits, cam, update, sounds, loops, deathSide: 1,
      marks: { dread: eyesUp ? T_CR1 + 0.2 : T_UP1 + 0.2, fake: tLand + 0.3, lunge: tLeap + 0.14, kill: tK + 0.7 },
      notes: { eyesUp, ceil: +ceil.toFixed(2), landZ: +landZ.toFixed(2), drop: +tDrop.toFixed(2), tK: +tK.toFixed(2), dur: +DUR.toFixed(2) } };
  }
};
