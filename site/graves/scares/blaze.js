// Blaze (round 7: the volley, as it fights in the game). The air shimmers and embers rise; an orange glow grows round
// the bend, and with it the blaze's breathing. It rises into view wreathed in smoke, rods turning, and floats out into
// the corridor, bobbing. Then it flares: smoke pours off it, it burns brighter, the breathing stops (its tell). Three
// fireballs, one after another: into the wall by your head, at your feet, into you. You catch fire (the 1.7.10
// overlay) and stagger back as it floats after you; it flares again and the second three come at point blank. You go
// down burning, the hotbar burns item by item, the edges of the view char black, and a man screams himself out.
import { THREE, track, clamp, lerp, sstep, pulse, tex, quad } from "./rig.js";
import { settle, shake, hitsOf, floorFall, particles, smoke, fireBlocks, mulberry } from "./common.js";
import { silence, deathScream } from "./fnaf.js";
import { kick } from "./story.js";

export default {
  death: "Steve was burnt to a crisp whilst fighting Blaze",
  async build(R) {
    const [partTex, ballTex] = await Promise.all([tex("particles"), tex("item_fireball")]);
    // It comes from ahead, round the side of the corridor (a passage or alcove if there is one).
    const op = R.openings.filter((o) => o.z > 2.5 && o.z < 9).sort((a, b) => a.z - b.z)[0];
    const bz = op ? op.z : clamp(R.ahead - 1.5, 3, 7), bxOut = op ? op.side * (op.wall + 1.2) : (R.wallR > R.wallL ? 1 : -1) * 2.5;
    const bx = clamp(bxOut * 0.25, -1.2, 1.2), by = 1.1;
    const B = R.mob("Blaze", { amb: [0.05, 0.05, 0.05], own: true });
    B.anim(0, 0, {}); R.place(B, 0, 0, 4, Math.PI);

    // ---- the dice -------------------------------------------------------------------------------------------
    const T_HEAT = R.vary(0.9, 0.25), T_BREATH = T_HEAT + R.vary(0.8, 0.3), T_RISE = T_BREATH + R.vary(1.2, 0.3);
    const tOut = T_RISE + 0.6, tFlare = T_RISE + R.vary(1.5, 0.3);           // floats out; flares (its tell)
    const V1 = [0, 1, 2].map((i) => tFlare + 0.5 + i * R.vary(0.3, 0.2));     // the three
    const tK = V1[2] + 0.1;                                                   // the third into you: on fire
    const tFlare2 = tK + R.vary(1.1, 0.25), FK = [0, 1, 2].map((i) => tFlare2 + 0.45 + i * 0.3);
    const T_FALL = FK[2] + 0.35, DUR = T_FALL + 1.25;
    const wallX = (R.wallR > R.wallL ? -R.wallL : R.wallR) * 0.98, side = Math.sign(wallX) || 1;
    const hits = hitsOf([[tK, 4, -side], [FK[0] + 0.1, 3, 1], [FK[1] + 0.1, 3, -1], [FK[2] + 0.1, 3, 1], [T_FALL + 0.5, 3, 1], [DUR - 0.05, 4, 1]]);
    const P1 = { x: bx * 0.6, y: by, z: Math.max(2.6, bz - 1.2) };          // where it stops to fire
    const shots = [
      { t0: V1[0] - 0.18, t1: V1[0], from: "blaze", to: [wallX, 1.75, 0.5] },
      { t0: V1[1] - 0.16, t1: V1[1], from: "blaze", to: [0.12 * -side, 0.05, 0.85] },
      { t0: V1[2] - 0.14, t1: V1[2], from: "blaze", to: "cam" },
      ...FK.map((tt) => ({ t0: tt - 0.08, t1: tt + 0.02, from: "blaze", to: "cam" }))
    ];
    const balls = shots.map((sh) => { const q = quad(ballTex, 0.32, 0.32, { alphaTest: 0.1, fog: false }); q.visible = false; R.add(q); return { q, ...sh }; });
    const fires = await fireBlocks(R, [{ at: [wallX * 0.9, 0, 0.5], t0: V1[0] + 0.1, s: 0.7 }, { at: [0.12 * -side, 0, 0.85], t0: V1[1] + 0.08, s: 0.8 }, { at: [0, 0, -0.4], t0: FK[0] + 0.15, s: 0.9 }, { at: [0.7, 0, -0.1], t0: FK[1] + 0.2, s: 0.8 }]);
    // Where it is: out from the side and up; out into the corridor to fire; after you as you burn.
    const blazeAt = (t, cl) => {
      if (t < tOut) {
        const out = sstep(T_RISE - 0.5, T_RISE + 0.4, t), rise = sstep(T_RISE - 0.2, T_RISE + 0.6, t);
        return { x: lerp(bxOut, bx, out), y: lerp(0.2, by, rise) + Math.sin(t * 2.2) * 0.08, z: bz };
      }
      const k1 = sstep(tOut, tFlare, t), k2 = sstep(tK + 0.15, tFlare2 + 0.2, t);
      const to2 = { x: cl ? cl.x * 0.5 : 0, y: R.eye - 1.4, z: (cl ? cl.z : -0.5) + 1.75 };
      return { x: lerp(lerp(bx, P1.x, k1), to2.x, k2), y: lerp(lerp(by, P1.y, k1), to2.y, k2) + Math.sin(t * 2.2) * 0.08 - 0.4 * sstep(T_FALL, T_FALL + 0.6, t), z: lerp(lerp(bz, P1.z, k1), to2.z, k2) };
    };

    const r = mulberry(17 + R.seed);
    const embers = [];
    for (let i = 0; i < 34; i++) embers.push({ t0: T_HEAT + r() * (DUR - T_HEAT), at: [bx + (r() - 0.5) * 2.5, r() * 0.6, bz - 2 + r() * 3.5], v: [(r() - 0.5) * 0.2, 0.6 + r() * 0.8, (r() - 0.5) * 0.2], life: 1.6 + r(), size: 0.035 + r() * 0.03, tile: 49, color: [1, 0.55, 0.2], grav: -0.1, fog: false, add: true });
    for (let i = 0; i < 26; i++) embers.push({ t0: tK + r() * 0.3, at: [(r() - 0.5) * 0.9, R.eye - 0.2 + r() * 0.5, 0.3 + r() * 0.4], v: [(r() - 0.5) * 2.5, (r() - 0.3) * 2, -1 - r() * 2], life: 0.6, size: 0.05, tile: 49, color: [1, 0.65, 0.25], grav: 3, fog: false, add: true });
    // Its flare: smoke pouring off it (the vanilla "on fire" before it shoots), where it is each time.
    const flareSmoke = [tFlare, tFlare2].flatMap((tf, j) => { const q = blazeAt(tf + 0.2, { x: 0, z: -0.6 }); return [0, 1, 2].flatMap((k) => smoke([q.x, q.y + 1.2, q.z], tf + k * 0.15, 5, { spread: 0.45, window: 0.2, life: 1.1, size: 0.3, rise: 0.9, seed: 80 + j * 3 + k, dark: 0.2 })); });
    const puffs = particles(R, partTex, [...embers, ...flareSmoke,
      ...[0, 1, 2, 3].flatMap((k) => smoke([bx, by + 0.6, bz], T_RISE - 0.3 + k * 0.55, 5, { spread: 0.7, window: 0.5, life: 1.5, size: 0.32, rise: 0.6, seed: 50 + k })),
      ...smoke([wallX, 1.7, 0.5], V1[0] + 0.05, 8, { spread: 0.4, window: 0.2, life: 1.2, size: 0.35, rise: 0.7, seed: 60 }),
      ...[0, 1, 2, 3, 4, 5].flatMap((k) => smoke([0, 0.9, 0.4], tK + 0.2 + k * 0.4, 2, { spread: 0.5, window: 0.3, life: 1, size: 0.18, rise: 1.2, seed: 70 + k, dark: 0.3 }))]);
    const glow = R.ownLight(R.light(0xff7a20, 0, 9, 1.3)), hit = R.ownLight(R.light(0xffa040, 0, 6, 1.4));

    // ---- the camera ------------------------------------------------------------------------------------------
    const look = R.yawTo(0, 0, bx, bz), lookP1 = R.yawTo(0, 0, P1.x, P1.z);
    const yawK = track([[0, 0], [T_BREATH, 0], [T_RISE + 0.3, look], [tFlare, lookP1]]);
    const pitchK = track([[0, 0], [T_RISE + 0.3, R.pitchTo(0, R.eye, 0, bx, by + 0.8, bz) * 0.8], [tFlare, R.pitchTo(0, R.eye, 0, P1.x, P1.y + 0.9, P1.z) * 0.8],
      [V1[1] - 0.02, R.pitchTo(0, R.eye, 0, P1.x, P1.y + 0.9, P1.z) * 0.8, "h"], [V1[1] + 0.12, -0.45, "x"], [V1[2] - 0.05, -0.1]]);
    const cam = (t) => {
      const st = settle(R, t, 0.9);
      const k = sstep(0.8, 1.3, t);
      const c = { x: st.x * (1 - k), y: st.y, z: st.z * (1 - k), yaw: lerp(st.yaw, yawK(t), k), pitch: lerp(st.pitch, pitchK(t), k), roll: 0, fov: st.fov - 5 * sstep(tFlare, V1[0], t) * (1 - sstep(tK, tK + 0.2, t)), near: t >= tK ? 0.02 : undefined };
      // The first one past your head into the wall: the head jerks away from it.
      const by1 = pulse(t, [V1[0]], 0.16); c.yaw += -side * 0.22 * by1; c.roll += side * 0.06 * by1;
      // Burning: you stagger back, beating at it, and the head stays on it as it comes after you; then you go down.
      const burn = sstep(tK, tK + 0.8, t);
      c.z -= 0.6 * burn; c.yaw += burn * Math.sin(t * 2.3) * 0.18; c.roll += burn * Math.sin(t * 3.1) * 0.08;
      if (t > tK) { const q = blazeAt(t, c), kq = sstep(tK + 0.3, tK + 0.9, t); c.yaw = lerp(c.yaw, R.yawTo(c.x, c.z, q.x, q.z) + burn * Math.sin(t * 2.3) * 0.12, kq); c.pitch = lerp(c.pitch, R.pitchTo(c.x, c.y, c.z, q.x, q.y + 1.3, q.z), kq); }
      const kk = kick(t, [{ t: tK, side: -side, amp: 1.3 }, ...FK.map((tt, i) => ({ t: tt + 0.02, side: i % 2 ? 1 : -1, amp: 0.8 }))]); c.yaw += kk.yaw; c.pitch += kk.pitch;
      floorFall(c, t, T_FALL, { d: 0.5, side: 1, roll: 1.1, y: 0.28, pitch: 0.2, back: 0.2 });
      c.fov += 6 * pulse(t, [tK], 0.12);
      return shake(c, t, 0.002 + 0.02 * pulse(t, [...V1, ...FK.map((x) => x + 0.02)], 0.2) + 0.01 * burn, 8);
    };

    // ---- sound --------------------------------------------------------------------------------------------
    const sounds = [
      [T_HEAT, "fire.fire", { at: [bxOut, 1, bz], volume: 0.5 }],
      [T_BREATH, "mob.blaze.breathe", { at: [bxOut, 1.5, bz], volume: 0.8 }], [T_BREATH + 0.9, "mob.blaze.breathe", { at: [(bx + bxOut) / 2, 1.5, bz], volume: 1 }],
      [T_RISE, "mob.blaze.breathe", { at: [bx, by + 0.8, bz], volume: 1, pitch: 0.85 }],
      [tOut + 0.4, "mob.blaze.breathe", { at: [P1.x, P1.y + 0.8, P1.z], volume: 0.9, pitch: 0.95 }],
      // The flare: the breath stops; it catches.
      silence(tFlare - 0.05, { fade: 0.1 }),
      [tFlare, "fire.ignite", { at: [P1.x, P1.y + 0.8, P1.z], volume: 1.2, pitch: 0.7 }], [tFlare + 0.02, "mob.blaze.breathe", { at: [P1.x, P1.y + 0.8, P1.z], volume: 1.3, pitch: 0.6 }],
      ...V1.map((tt) => [tt - 0.18, "mob.ghast.fireball", { at: [P1.x, P1.y + 1, P1.z], volume: 1.1 }]),
      [V1[0], "random.fizz", { at: [wallX, 1.7, 0.5], volume: 1 }], [V1[0] + 0.01, "fire.ignite", { at: [wallX, 1.7, 0.5], volume: 0.9 }],
      [V1[1], "fire.ignite", { at: [0, 0.1, 0.85], volume: 1 }],
      [tK, "fire.ignite", { volume: 1.3 }], [tK + 0.005, "qf.scare.hit", { volume: 1.0 }],
      [tFlare2, "fire.ignite", { volume: 1.1, pitch: 0.75 }], [tFlare2 + 0.02, "mob.blaze.breathe", { volume: 1.3, pitch: 0.6 }],
      ...FK.map((tt) => [tt - 0.08, "mob.ghast.fireball", { volume: 1 }]), ...FK.map((tt) => [tt + 0.1, "fire.ignite", { volume: 1.1 }]),
      [tK + 0.15, "fire.fire", { volume: 1 }],
      ...hits.map((h) => [h.t, "game.player.hurt"]), ...deathScream(tK + 0.15), ...deathScream(T_FALL - 0.1, { volume: 1.1, under: false }),
      [DUR - 0.6, "mob.blaze.breathe", { volume: 1 }],
      [DUR, "game.player.die"], [DUR, "@muffle", { hz: 500, s: 2.5 }]
    ];
    const loops = [
      [0.5, tFlare, "qf.scare.heartbeat", { volume: 0.45 }], [T_HEAT, tFlare, "qf.scare.drone", { volume: 0.45, fadeIn: 1.5, fadeOut: 0.1, bus: "sfx" }],
      [tK + 0.1, DUR + 0.5, "fire.fire", { volume: 0.9, fadeIn: 0.2 }], [tK, DUR + 0.2, "qf.scare.heartbeat", { volume: 0.8, pitch: 1.5 }]
    ];

    // ---- the frame ------------------------------------------------------------------------------------------
    const _w = new THREE.Vector3();
    const flareOf = (t) => sstep(tFlare - 0.05, tFlare + 0.2, t) * (1 - sstep(V1[2] + 0.2, V1[2] + 0.8, t)) + sstep(tFlare2 - 0.05, tFlare2 + 0.2, t) * (1 - sstep(FK[2] + 0.2, FK[2] + 0.8, t));
    function update(t, f) {
      const cl = R.toLocal(R.camera.position);
      const q = blazeAt(t, cl), vis = t > T_RISE - 0.6;
      B.pivot.visible = vis;
      R.place(B, q.x, q.y, q.z, R.yawTo(q.x, q.z, cl.x, cl.z));
      const fl = flareOf(t);
      B.anim(t * (1 + 1.2 * fl), 0, {});   // the rods spin up as it flares
      // A rod passing between the lens and you would fill the frame at point blank: those near the lens are left out.
      if (t > tK) { B.pivot.updateMatrixWorld(true); for (let i = 0; i < 12; i++) { const g = B.parts["blazeSticks" + i]; if (g) { g.getWorldPosition(_w); g.visible = _w.distanceTo(R.camera.position) > 0.42; } } }
      B.setOwn(0.5 + 0.5 * fl + 0.3 * pulse(t, [...V1, ...FK], 0.25));
      R.L(q.x, q.y + 1.2, q.z - 0.4, glow.position);
      glow.intensity = vis ? (2.5 * sstep(T_HEAT, T_RISE, t) + 2.5 * sstep(T_RISE - 0.2, T_RISE + 0.6, t)) * (t < tK ? 1 : 0.55) + 3 * fl + 4 * pulse(t, [...V1, ...FK], 0.2) : 0.6 * sstep(T_HEAT, T_RISE, t);
      for (const b of balls) {
        const k = (t - b.t0) / (b.t1 - b.t0);
        b.q.visible = k >= 0 && k < 1;
        if (!b.q.visible) continue;
        const fr = b.from === "blaze" ? [q.x, q.y + 1.5, q.z] : b.from, to = b.to === "cam" ? [cl.x, cl.y - 0.15, cl.z + 0.15] : b.to;
        R.at(b.q, lerp(fr[0], to[0], k), lerp(fr[1], to[1], k), lerp(fr[2], to[2], k)); b.q.quaternion.copy(R.camera.quaternion);
      }
      const hb = balls.map((b) => [b, pulse(t, [b.t1], 0.25)]).sort((p, q2) => q2[1] - p[1])[0];
      if (hb && hb[1] > 0.01) { const to = hb[0].to === "cam" ? [cl.x, cl.y, cl.z + 0.3] : hb[0].to; R.L(to[0] * 0.9, to[1] + 0.2, to[2], hit.position); hit.intensity = 9 * hb[1]; } else hit.intensity = 0;
      fires(t); puffs(t);
      const heat = sstep(T_HEAT, T_RISE, t) * (1 + 0.4 * fl), burn = sstep(tK, tK + 0.25, t);
      f.env = { nausea: 0.12 * Math.min(1, heat) + 0.15 * burn, bake: 1 - 0.2 * sstep(0.2, 1.2, t), fogMul: 1 + 0.6 * Math.min(1, heat), fog: [0.12, 0.05, 0.02, 0.5 * Math.min(1, heat)] };
      f.tints = [[255, 110, 30, 0.05 * heat + 0.12 * burn]];
      f.vig = [40, 10, 0, 0.3 + 0.25 * Math.min(1, heat)]; f.vigR = 0.9;
      f.fire = burn;
      f.burnt = [0, 1, 2, 3, 4].map((i) => t > tK + 0.5 + i * 0.35);
      f.char = 0.62 * sstep(tK + 0.6, DUR, t);
    }
    return { dur: DUR, hits, cam, update, sounds, loops, deathSide: 1,
      marks: { dread: T_RISE + 0.5, fake: tFlare + 0.25, lunge: V1[0] - 0.05, kill: tK + 0.9 },
      notes: { flare: +tFlare.toFixed(2), tK: +tK.toFixed(2), dur: +DUR.toFixed(2) } };
  }
};
