// Spider: the ceiling. Clicking overhead, moving. The head tilts up, slowly. Either two red eyes look back from the
// ceiling ahead, and blink out, gone; or the ceiling is bare. The clicking stops. Silence. The head comes back down to
// the corridor, and it drops from straight above into your face, upside down, turning as it comes, fangs open, eyes
// burning, with the screech. Its legs wrap the edges of the view; it bites; you are hauled up into the dark and left
// dangling over the corridor, turning slowly on the thread.
import { THREE, track, clamp, lerp, sstep, pulse, tex, quad } from "./rig.js";
import { settle, shake, hitsOf, lensLimbs, halo } from "./common.js";
import { lunge, lungeFx, screech, splitJaw, faceAnchor, boxOf, silence, deathScream, jit } from "./fnaf.js";

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
    const anchor = faceAnchor(sp, sp.parts.head, boxOf("spider", "spiderHead")); anchor.y -= 0.04;
    const eyeGlow = [halo(R, new THREE.Color(1, 0.08, 0.04), 0.22), halo(R, new THREE.Color(1, 0.08, 0.04), 0.22)];
    // ---- the dice -------------------------------------------------------------------------------------------
    const eyesUp = R.chance(0.55);
    const T_CLICK = 0.9 + R.vary(0.3, 0.5), T_UP0 = T_CLICK + R.vary(0.9, 0.35), T_UP1 = T_UP0 + R.vary(1.25, 0.25);
    const tBlink = T_UP1 + R.vary(0.9, 0.4);              // the eyes go out (or the bare ceiling is held)
    const tSil = tBlink + 0.05, tD0 = tBlink + R.vary(0.6, 0.4), tD1 = tD0 + R.vary(0.9, 0.25);
    const t0 = tD1 + R.vary(0.85, 0.55);
    const over = { x: 0.05, z: 0.55 };                    // straight above, just ahead: out of sight
    const L = lunge(R, sp, { t0, rush: R.vary(0.2, 0.15), hold: R.vary(0.6, 0.15), dist: 0.42, anchor, seed: 13, rise: -0.25 });
    const tK = L.t3, T_HAUL = tK + 1.45, DUR = tK + 3.55;
    const hang = Math.max(2.3, ceil - 0.45);
    const hits = hitsOf([[tK + 0.05, 4, 1], [tK + 0.55, 4, -1], [tK + 1.05, 3, 1], [T_HAUL + 1.1, 4, -1], [DUR - 0.1, 5, 1]]);
    const upP = R.pitchTo(0, R.eye, 0, sx, ceil - 0.3, sz);
    const pitch = track([[0, 0], [T_UP0, -0.02], [T_UP1, upP, "s"], [tD0, upP], [tD1, -0.04, "s"], [t0, -0.02], [L.t1, 0.12, "x"], [tK, 0.2, "h"], [T_HAUL, 0.12], [T_HAUL + 0.9, -1.05, "i"], [DUR, -1.25]]);
    const yawT = track([[0, 0], [tBlink, 0], [tBlink + 0.35, eyesUp ? 0.25 : -0.2], [tD0, eyesUp ? -0.15 : 0.18], [tD1, 0]]);
    const eyeY = track([[0, R.eye], [tK, R.eye], [tK + 0.3, R.eye - 0.15], [T_HAUL, R.eye - 0.1], [T_HAUL + 1.1, hang, "i"], [DUR, hang + 0.08]]);
    const back = track([[0, 0], [L.t1, -0.08, "x"], [tK, -0.4, "h"], [T_HAUL, -0.55], [T_HAUL + 1.1, -0.2]]);
    const cam = (t) => {
      const s = settle(R, t, 0.9);
      const k = sstep(0.8, 1.3, t);
      const c = { x: s.x * (1 - k), y: lerp(s.y, eyeY(t), k), z: lerp(s.z, back(t), k), yaw: lerp(s.yaw, yawT(t), k), pitch: lerp(s.pitch, pitch(t), k), roll: 0, fov: s.fov + 10 * pulse(t, [L.t1], 0.12), near: t >= t0 && t < tK ? 0.02 : undefined };
      const d = sstep(T_HAUL + 0.4, T_HAUL + 1.4, t);
      c.yaw += d * (t - T_HAUL) * 0.55; c.roll += d * Math.sin((t - T_HAUL) * 2.1) * 0.12; c.x += d * Math.sin((t - T_HAUL) * 2.1) * 0.12;
      c.fov += 8 * sstep(T_HAUL, T_HAUL + 1, t);
      return shake(c, t, 0.002 + 0.003 * sstep(T_UP0, tBlink, t) + L.shake(t) + 0.025 * sstep(tK, tK + 0.1, t) * (1 - 0.6 * sstep(tK + 0.2, T_HAUL, t)) + 0.02 * pulse(t, hits.map((h) => h.t), 0.2), 6);
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
    const S2 = screech(L, [["mob.spider.say", { pitch: 0.55 }], ["mob.spider.death", { pitch: 0.7, volume: 1.1 }]]);
    const clicks = [];
    for (let tt = T_CLICK, i = 0; tt < tBlink - 0.1; tt += R.vary(0.42, 0.3), i++) clicks.push([tt, "mob.spider.step", { at: [sx + Math.sin(i) * 0.8, ceil, sz + 1.6 - Math.min(1.6, i * 0.3)], volume: 0.45 + 0.04 * Math.min(i, 5), pitch: 0.9 }]);
    const sounds = [
      ...clicks,
      ...(eyesUp ? [[T_UP1 + 0.2, "mob.spider.say", { at: [sx, ceil - 0.4, sz], volume: 0.45, pitch: 0.75 }]] : []),
      silence(tSil),
      [tD1 + (t0 - tD1) * 0.5, "dig.cloth", { at: [over.x, ceil - 0.2, over.z], volume: 0.18, pitch: 0.6 }],
      ...S2.sounds,
      ...hits.flatMap((h, i) => [[h.t, "game.player.hurt"], [h.t + 0.02, i % 2 ? "qf.scare.gore" : "qf.scare.crunch", { volume: 1 }], [h.t - 0.05, "mob.spider.say", { volume: 0.6, pitch: 1.1 }]]),
      ...deathScream(tK + 0.12, { volume: 1.1, under: false }),
      [T_HAUL + 0.1, "dig.cloth", { volume: 0.8, pitch: 0.6 }],
      [T_HAUL + 1.4, "mob.spider.step", { volume: 0.5 }], [T_HAUL + 1.9, "mob.spider.step", { volume: 0.5 }],
      ...deathScream(T_HAUL + 0.15, { volume: 1.3 }),
      [DUR, "game.player.die"], [DUR, "@muffle", { hz: 380, s: 3 }]
    ];
    const loops = [
      [0.6, tSil, "qf.scare.heartbeat", { volume: 0.55 }],
      [T_UP0, tSil, "qf.scare.drone", { volume: 0.4, fadeIn: 1.2, fadeOut: 0.05, bus: "sfx" }],
      ...S2.loops,
      [tK, DUR + 0.2, "qf.scare.heartbeat", { volume: 0.7, pitch: 1.35 }],
      [T_HAUL + 0.6, DUR, "qf.scare.breath", { volume: 0.5, fadeIn: 0.6 }]
    ];
    hits.forEach((h, i) => R.burst(h.t, i < 3 ? [0, 1.35, 0.25] : [0, hang - 0.25, 0], 24, "blood", { dir: i < 3 ? [0, 0.5, 0.8] : [0, -0.2, 0], speed: 1.8, spread: 0.6, size: 0.045, life: 1.8, stick: 3 }));
    for (let k = 0; k < 7; k++) R.burst(T_HAUL + 1.0 + k * 0.28, [0.02 * (k % 3), hang - 0.4, 0.02], 2, "blood", { dir: [0, -1, 0], speed: 0.3, spread: 0.05, size: 0.035, life: 1.6, stick: 4 });
    const _v = new THREE.Vector3();

    function update(t, f) {
      const camNow = R.camera, cl = R.toLocal(camNow.position);
      let open = 0, eyes = 0;
      if (t < t0) {
        // On the ceiling ahead, upside down (only if the dice say it was there), then straight overhead.
        const seen = eyesUp && t < tBlink;
        const at = seen ? { x: sx, z: sz } : over;
        R.place(sp, at.x, ceil, at.z, R.yawTo(at.x, at.z, 0, 0) + 0.1 * Math.sin(t * 0.7), -0.45, Math.PI);
        sp.anim(t, 0, { walk: t > T_CLICK && t < tBlink ? 0.6 : 0.05 });
        sp.pivot.visible = seen || t > tD1;
        eyes = seen ? 0.6 + 0.4 * Math.sin(t * 3) : 0;
        sp.setOwn(0.0);
      } else if (t < tK) {
        R.place(sp, over.x, ceil - 0.1, over.z, 0, -0.45, Math.PI);
        sp.anim(t * 3, 0, { walk: 2 });
        L.apply(t);
        open = sstep(t0, L.t1, t) * (0.85 + 0.15 * jit(t, 31)); eyes = 1;
        sp.setOwn(0.35);
      } else {
        // On your face.
        const tz = cl.z + 1.12 - 0.08 * pulse(t, hits.slice(0, 3).map((h) => h.t - 0.05), 0.1);
        R.place(sp, cl.x, cl.y - 0.5, tz, R.yawTo(sx, sz, 0, 0), -0.22, 0);
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
      const sil = sstep(tSil, tSil + 0.5, t) * (t < t0 ? 1 : 0);
      f.env = { bake: 1 - 0.3 * sstep(0.3, 1.5, t) - 0.25 * sstep(T_UP0, T_UP1, t) - 0.15 * sil - 0.25 * w, lights: 1 - 0.35 * sstep(T_UP0, T_UP1, t) - 0.2 * sil, fogMul: 1 + 0.8 * sstep(1, 3, t) };
      f.vig = [0, 0, 0, 0.3 + 0.3 * sstep(T_UP0, T_UP1, t) + 0.25 * w]; f.vigR = 0.85;
      f.splats = hits.slice(0, 3).filter((h) => t >= h.t).map((h, i) => ({ t0: h.t, x: [0.4, 0.62, 0.5][i], y: [0.5, 0.38, 0.6][i], r: 13 + i * 3, seed: 41 + i }));
      f.black = 0.6 * sstep(DUR - 0.3, DUR + 0.4, t);
      lungeFx(L, t, f);
    }
    return { dur: DUR, hits, cam, update, sounds, loops, deathSide: 1,
      marks: { dread: eyesUp ? (T_UP1 + tBlink) / 2 : T_UP1 + 0.2, fake: (tD1 + t0) / 2, lunge: L.t1 + 0.12, kill: tK + 0.7 },
      notes: { eyesUp, t0: +t0.toFixed(2), dur: +DUR.toFixed(2) } };
  }
};
