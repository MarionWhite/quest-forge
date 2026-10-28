// Wither Skeleton (round 8, rethought: the shadow). A torch on the wall behind you throws your shadow down the
// corridor ahead, over the floor and up the stone; the walk stops with your eyes on it. Far behind you, in the dark
// past that torch, a wither skeleton is walking up the corridor (its steps, faint). It passes the torch, and its
// shadow sweeps forward over everything and comes to stand behind yours: a head and more taller, the stone sword in
// its hand. You go still. Its steps stop. You turn round, slowly, and it does not wait: as you turn it swings (a wither
// skeleton strikes the moment you are in reach) and the blow knocks your head round to it. Your hearts go black
// (Wither). It towers over you against the torchlight, 1.2 times a skeleton, and looks down at you; it swings again
// and you go down. On your back, the Wither eats at your hearts; it steps over you, the sword goes up, and comes down.
// Vanilla throughout: the 1.2-scale model and texture, the stone sword, the skeleton's sounds (1.7.10 has no others for
// it), the Wither hearts; the one device is the shadow itself (1.7.10 draws none; the Krypt's torchlight here does).
// The torch is one of the Krypt's when one behind you throws the shadows up the wall ahead; otherwise a copy of one of
// its wall torches, moved whole blocks along to a wall block behind you, out of sight from the first frame; in a hall
// with no wall near enough, the shadows lie along the floor and you look down at them.
import { THREE, track, clamp, lerp, sstep, pulse, tex } from "./rig.js";
import { settle, shake, hitsOf, floorFall, bipedSwing, swingAt, mcRot } from "./common.js";
import { silence, deathScream } from "./fnaf.js";
import { blow, kick } from "./story.js";
import { castShadows } from "./shadow.js";

const wrap = (a) => Math.atan2(Math.sin(a), Math.cos(a));

export default {
  death: "Steve was slain by Wither Skeleton",
  async build(R) {
    const eye = R.eye;
    // ---- the torch behind you, and where your shadow falls ----------------------------------------------------------
    const land = (Lp, p) => { const d = [p[0] - Lp[0], p[1] - Lp[1], p[2] - Lp[2]], n = Math.hypot(...d); const u = d.map((v) => v / n); const r = R.ray(p[0], p[1], p[2], u[0], u[1], u[2], 16, 0.08); return { x: p[0] + u[0] * r, y: p[1] + u[1] * r, z: p[2] + u[2] * r, r }; };
    // Where it stands when its shadow is over yours: on the line to the light, 1.7 m from you (just out of its reach), a
    // little to one side (so its head and its sword show beside yours, not lost inside it).
    const standAt = (Lp, d, off) => { const n = Math.hypot(Lp[0], Lp[2]) || 1, u = { x: Lp[0] / n, z: Lp[2] / n }; return { x: u.x * d + u.z * off, z: u.z * d - u.x * off }; };
    const clear = (Lp, p) => { const d = [p[0] - Lp[0], p[1] - Lp[1], p[2] - Lp[2]], n = Math.hypot(...d); return R.ray(Lp[0], Lp[1], Lp[2], d[0] / n, d[1] / n, d[2] / n, n, 0.08) >= n - 0.15; };
    // A shadow reads when it is thrown up a wall (upright, a figure); along the floor, seen from above, it is a smear. So
    // the torch is the one whose shadows of you and of it climb the stone ahead of you, near enough to see whole, its
    // head above yours (a torch about a metre over your head and three to four behind does it).
    const judge = (Lp, own) => {
      const a = standAt(Lp, 1.7, 0.3);
      if (!clear(Lp, [0, 1.6, 0]) || !clear(Lp, [a.x, 2.0, a.z])) return null;
      const H = land(Lp, [0, 1.85, 0]), F = land(Lp, [0, 0.9, 0]), K = land(Lp, [a.x, 2.35, a.z]);
      if (H.r >= 15.9 || K.r >= 15.9) return null;
      const hd = Math.hypot(H.x, H.z);
      const tgt = { x: (H.x + K.x) / 2, y: (H.y + K.y) / 2 + 0.15, z: (H.z + K.z) / 2 };
      const yw = R.yawTo(0, 0, tgt.x, tgt.z), pt = R.pitchTo(0, eye, 0, tgt.x, tgt.y, tgt.z);
      const off = Math.abs(wrap(R.yawTo(0, 0, Lp[0], Lp[2]) - yw)), ld = Math.hypot(Lp[0], Lp[2]);
      const score = Math.abs(yw) * 0.6 + Math.abs(hd - 3.2) * 0.3 + Math.abs(H.y - 0.9) * 0.8 + Math.abs(ld - 3.4) * 0.25 + (own ? 0.6 : 0)
        + (H.y < 0.3 ? 2.5 : 0) + (K.y < H.y + 0.1 ? 1 : 0) + (hd < 1.8 || hd > 6 ? 1.5 : 0) + (Math.abs(yw) > 0.95 ? 3 : 0) + (off < 1.25 ? 6 : 0);
      return { Lp, H, F, K, a, tgt, yw, pt, score, own };
    };
    let best = null;
    const consider = (c) => { if (c && (!best || c.score < best.score)) best = c; };
    for (const tc of R.torches) {
      const l = tc.l;
      if (l.z > -0.9 || l.z < -8 || Math.abs(l.x) > 6 || l.y < 1.9 || l.y > 4.6) continue;
      consider(judge([l.x, l.y + 0.1, l.z], null));
    }
    // A torch of our own where none of the Krypt's will do: a copy of one of its wall torches (the same model, the same
    // height, on the same kind of wall), moved whole blocks along to a wall block behind you where the shadows work. It
    // is there from the first frame, out of sight; its light comes up as the walk stops.
    if (!best || best.score > 1.6) {
      const seen = new Set();
      for (const T of R.torches) {
        const s = Math.sign(T.l.x); if (!s || Math.abs(T.l.x) > 8) continue;
        const tb = new THREE.Vector3(Math.floor(T.w.x), Math.floor(T.w.y), Math.floor(T.w.z));
        const rr = R.dirW(s, 0, 0).map(Math.round), ab = [tb.x + rr[0], tb.y, tb.z + rr[2]];
        if (!R.solidW(ab[0] + 0.5, ab[1] + 0.5, ab[2] + 0.5)) continue;   // its wall is on our side of it
        for (let dzL = -10; dzL <= 10; dzL++) for (let dxL = -3; dxL <= 3; dxL++) {
          const dW = R.dirW(dxL, 0, dzL).map(Math.round), key = s + ":" + (tb.x + dW[0]) + ":" + (tb.z + dW[2]);
          if (seen.has(key)) continue; seen.add(key);
          const w = new THREE.Vector3(T.w.x + dW[0], T.w.y, T.w.z + dW[2]), l = R.toLocal(w);
          if (l.z > -1.4 || l.z < -5.5 || Math.abs(l.x) > 6) continue;
          if (!R.solidW(ab[0] + dW[0] + 0.5, ab[1] + 0.5, ab[2] + dW[2] + 0.5) || R.solidW(tb.x + dW[0] + 0.5, tb.y + 0.5, tb.z + dW[2] + 0.5)) continue;
          if (R.torches.some((o) => o.w.distanceTo(w) < 1.5)) continue;
          const c = judge([l.x, l.y + 0.1, l.z], { T, dW, s });
          if (c) consider(c);
        }
      }
    }
    if (!best || best.score > 2.8) {
      // A hall, its walls too far off for any shadow to climb: they lie along the floor instead, and you look down at
      // them. A wall torch is barely over your head and its floor shadows of you would run ten metres up the hall, so the
      // light they are cast from is taken a metre above the flame (nobody can tell; the figures come out near enough to read).
      let fb = null;
      for (const tc of R.torches) {
        const l = tc.l;
        if (l.z > -0.9 || l.z < -8 || Math.abs(l.x) > 6.5 || l.y < 1.9 || l.y > 4.6) continue;
        // (on the floor one shadow inside another is a blot: it stands off to one side of the line, toward the middle of
        // the way, and its shadow lies beside yours, longer, two figures)
        const Lp = [l.x, l.y + 1.1, l.z], a = [standAt(Lp, 1.7, 0.65), standAt(Lp, 1.7, -0.65)].sort((p, q) => Math.abs(p.x) - Math.abs(q.x))[0];
        if (!clear([l.x, l.y + 0.1, l.z], [0, 1.6, 0])) continue;
        const H = land(Lp, [0, 1.85, 0]), F = land(Lp, [0, 0.9, 0]), K = land(Lp, [a.x, 2.35, a.z]);
        if (H.r >= 15.9 || H.z < 1.5) continue;
        const tgt = { x: (H.x + F.x + K.x) / 3, y: (H.y + F.y + K.y) / 3, z: (H.z + F.z + K.z) / 3 };
        const yw = R.yawTo(0, 0, tgt.x, tgt.z), pt = R.pitchTo(0, eye, 0, tgt.x, tgt.y, tgt.z), ld = Math.hypot(l.x, l.z);
        const score = 3.2 + Math.abs(yw) * 1.2 + Math.abs(pt + 0.45) + Math.abs(ld - 3.5) * 0.3 + (H.r > 9 ? 1 : 0) + (Math.abs(yw) > 0.95 ? 3 : 0);
        if (!fb || score < fb.score) fb = { Lp, H, F, K, a, tgt, yw, pt, score, own: null, floor: true };
      }
      if (fb) best = fb;
    }
    let ownTorch = null;
    if (best && best.own) {
      // the copy: the template's 20 vertices (its quads), moved by whole blocks; the Krypt's own torch material
      const { T, dW } = best.own, src = T.mesh.geometry, g = new THREE.BufferGeometry();
      for (const [name, at] of Object.entries(src.attributes)) {
        const arr = new at.array.constructor(20 * at.itemSize);
        for (let q = 0; q < 20; q++) for (let c = 0; c < at.itemSize; c++) arr[q * at.itemSize + c] = at.array[(T.i + q) * at.itemSize + c];
        g.setAttribute(name, new THREE.BufferAttribute(arr, at.itemSize, at.normalized));
      }
      if (src.index) { const ix = []; const I = src.index.array; for (let k = 0; k + 2 < I.length; k += 3) if (I[k] >= T.i && I[k] < T.i + 20 && I[k + 1] >= T.i && I[k + 1] < T.i + 20 && I[k + 2] >= T.i && I[k + 2] < T.i + 20) ix.push(I[k] - T.i, I[k + 1] - T.i, I[k + 2] - T.i); g.setIndex(ix); }
      g.applyMatrix4(T.mesh.matrixWorld); g.translate(dW[0], 0, dW[2]);
      ownTorch = new THREE.Mesh(g, T.mesh.material); R.add(ownTorch);
      // its light: a torch's, a little out from the wall (as the Krypt's own torches light the stone round them)
      const pl = R.ownLight(R.light(0xffc880, 0, 8, 1.6)); R.at(pl, best.Lp[0] - best.own.s * 0.45, best.Lp[1] - 0.2, best.Lp[2]); ownTorch.userData.light = pl;
    }
    if (!best) {
      // nowhere at all (a stair, a shaft): the nearest torch behind, or a light above and behind you
      const tc = R.torches.find((t) => t.l.z < -0.9 && t.l.z > -9 && Math.abs(t.l.x) < 7);
      const Lp = tc ? [tc.l.x, tc.l.y + 0.1, tc.l.z] : [0.6, 3.0, -3];
      const H = land(Lp, [0, 1.85, 0]), F = land(Lp, [0, 0.9, 0]), a = standAt(Lp, 1.7, 0.3), K = land(Lp, [a.x, 2.35, a.z]);
      const tgt = { x: (H.x + K.x) / 2, y: (H.y + K.y) / 2, z: (H.z + K.z) / 2 };
      best = { Lp, H, F, K, a, tgt, yw: R.yawTo(0, 0, tgt.x, tgt.z), pt: R.pitchTo(0, eye, 0, tgt.x, tgt.y, tgt.z), own: null };
    }
    const Lp = best.Lp;
    // The torch's light on the stone ahead, where the shadows fall (the Krypt's baked light alone leaves it too dim for
    // a shadow to show): a soft cone from the flame, coming up as the walk stops.
    const spot = R.ownLight(new THREE.SpotLight(0xffc27a, 0, 14, 0.45, 0.9, 1.2)); R.at(spot, Lp[0], Lp[1], Lp[2]); R.add(spot);
    R.at(spot.target, best.tgt.x, best.tgt.y, best.tgt.z); R.add(spot.target);
    const yawS = clamp(best.yw, -0.95, 0.95), pitchS = clamp(best.pt, -0.55, 0.1);

    // ---- its way: from the dark past the torch to just behind you, between you and the light --------------------------
    const Sa = best.a;                         // where it stops, its shadow over yours, just out of reach
    const S1 = standAt(Lp, 1.5, 0.15);         // where it strikes from (a wither skeleton hits inside about 1.6 m)
    let S0 = { x: clamp(Lp[0] * 0.35, -(R.wallL - 0.6), R.wallR - 0.6), z: Lp[2] - 3.4 };
    for (let k = 0; k < 8 && (R.solid(S0.x, 1.0, S0.z) || R.solid(S0.x, 2.0, S0.z)); k++) S0 = { x: S0.x * 0.7, z: S0.z + 0.4 };
    const SPD = 1.9, walkL = Math.hypot(Sa.x - S0.x, Sa.z - S0.z);
    const tW0 = 1.1 + R.vary(0.3, 0.5), tArr = tW0 + walkL / SPD;
    const wAt = (t) => { const k = clamp((t - tW0) / (tArr - tW0)); return { x: lerp(S0.x, Sa.x, k), z: lerp(S0.z, Sa.z, k) }; };
    // when its shadow first comes into your view (its skull's shadow inside the middle of the frame)
    const look0 = { x: -Math.sin(yawS) * Math.cos(pitchS), y: Math.sin(pitchS), z: Math.cos(yawS) * Math.cos(pitchS) };
    let tSh = tArr - 1.0;
    // (its middle's shadow inside the middle of the frame: the skull's runs too far up the corridor to judge by)
    for (let t = tW0; t < tArr && tSh === tArr - 1.0; t += 0.02) for (const hy of [1.0, 1.5]) {
      const q = wAt(t), h = land(Lp, [q.x, hy, q.z]);
      if (h.r >= 15.9) continue;
      const v = [h.x, h.y - eye, h.z], n = Math.hypot(...v);
      if (n < 14 && (v[0] * look0.x + v[1] * look0.y + v[2] * look0.z) / n > Math.cos(0.45)) { tSh = t; break; }
    }
    tSh = clamp(tSh, tW0 + 0.6, tArr - 0.7);
    // ---- the beats ----------------------------------------------------------------------------------------------------
    const tFreeze = tSh + 0.25;                                   // you see it: still
    // It stops with its shadow over yours, lifts the sword (its shadow rises up the stone ahead), steps into reach and
    // strikes; you have begun to turn round.
    const tRaise = tArr + 0.05, tStep = tArr + 0.5, tH1 = tArr + R.vary(1.0, 0.1);
    const tTurn0 = tArr + R.vary(0.2, 0.3);
    const yawK = R.yawTo(0, 0, S1.x, S1.z);
    const dirT = Math.sign(wrap(yawK - yawS)) || 1, spanT = Math.abs(wrap(yawK - yawS));
    const tH2 = tH1 + 1.05, tFl = tH2 + 0.05, tFloor = tFl + 0.5;
    const tW1 = tFloor + 0.45, tW2 = tW1 + 0.55, tUp = tW2 + 0.1, tH3 = tUp + 0.5, DUR = tH3 + 0.15;
    const hits = hitsOf([[tH1, 7, -dirT], [tH2, 6, dirT], [tW1, 2, 1], [tW2, 2, -1], [DUR, 3, 1]]);
    const S2 = { x: S1.x * 0.55, z: S1.z * 0.55 };                   // where it stands over you on the floor
    // ---- the head -----------------------------------------------------------------------------------------------------
    const turnK = (t) => {   // the slow turn; the blow knocks the rest of the way round
      const slow = clamp((t - tTurn0) / 1.7); let k = slow * slow * (3 - 2 * slow) * 0.85;
      if (t >= tH1) { const k1 = (() => { const s0 = clamp((tH1 - tTurn0) / 1.7); return s0 * s0 * (3 - 2 * s0) * 0.85; })(); k = lerp(k1, 1, 1 - Math.pow(1 - clamp((t - tH1) / 0.22), 3)); }
      return k;
    };
    const skullAt = (t) => { const q = t < tH2 + 0.3 ? S1 : { x: lerp(S1.x, S2.x, sstep(tH2 + 0.3, tW1, t)), z: lerp(S1.z, S2.z, sstep(tH2 + 0.3, tW1, t)) }; return { x: q.x, y: 2.15, z: q.z }; };
    const cam = (t) => {
      const s = settle(R, t, 1.2, { yaw: yawS, pitch: pitchS });
      const c = { ...s, near: t >= tTurn0 ? 0.02 : undefined };
      c.y -= 0.01 * sstep(tFreeze, tFreeze + 0.2, t);
      // the turn round, slowly; then the eyes go up it to its skull
      const k = turnK(t);
      c.yaw = s.yaw + dirT * spanT * k;
      c.pitch = lerp(s.pitch, -0.02, sstep(tTurn0, tTurn0 + 1.0, t));
      const sk = skullAt(t), up = clamp(R.pitchTo(c.x, c.y, c.z, sk.x, sk.y, sk.z), -0.2, 0.75);
      c.pitch = lerp(c.pitch, up, sstep(tH1 + 0.1, tH1 + 0.6, t));
      c.z -= 0.1 * sstep(tH1, tH1 + 0.25, t);
      const kk = kick(t, hits.slice(0, 2).map((h) => ({ t: h.t, side: h.side, amp: 1.3 })).concat(hits.slice(2).map((h) => ({ t: h.t, side: h.side, amp: 0.4 }))));
      c.yaw += kk.yaw; c.pitch += kk.pitch;
      // knocked down; on your back, the eyes on it as it steps over you
      floorFall(c, t, tFl, { d: 0.5, side: dirT, roll: 0.55, y: 0.28, pitch: 0.95, back: 0.35 });
      if (t > tFloor) { const q = skullAt(t), ly = R.yawTo(c.x, c.z, q.x, q.z); c.yaw = lerp(c.yaw, c.yaw + wrap(ly - c.yaw) * 0.8, sstep(tFloor, tW1, t)); c.pitch = lerp(c.pitch, clamp(R.pitchTo(c.x, c.y, c.z, q.x, q.y, q.z) + 0.15, 0.5, 1.3), sstep(tFloor, tW1 + 0.3, t)); }
      c.fov = s.fov - 4 * sstep(tFreeze, tTurn0 + 1, t) * (1 - sstep(tH1, tH1 + 0.3, t)) + 6 * pulse(t, [tH1, tH2, DUR], 0.15);
      const amp = 0.0015 + 0.0025 * sstep(tFreeze, tH1, t) + 0.03 * pulse(t, [tH1, tH2, tFloor, DUR], 0.15) + 0.01 * pulse(t, [tW1, tW2], 0.12) + 0.004 * sstep(tH1, tH1 + 0.3, t);
      return shake(c, t, amp, 6);
    };

    // ---- the figures --------------------------------------------------------------------------------------------------
    const W = R.mob("WitherSkeleton", { amb: [0.03, 0.03, 0.035], own: true, equipment: [{ id: "minecraft:stone_sword", ench: false }] });
    W.anim(0, 0, {}); R.place(W, S0.x, 0, S0.z, 0);
    const SH = castShadows(R, { light: Lp, center: () => { const q = wAt(Math.min(R._t || 0, tArr)); return [q.x * 0.5, 1.2, q.z * 0.5]; }, strength: 0, reach: best.floor ? Math.max(10, 2.2 * Math.hypot(Lp[0], Lp[2])) : 10 });   // (a floor shadow from further off is longer and fainter: it is let reach)
    R._sh = SH;   // (for checks)
    const Wsh = SH.add(R.mob("WitherSkeleton", { amb: [0.03, 0.03, 0.035], equipment: [{ id: "minecraft:stone_sword", ench: false }] }));
    const you = SH.add(R.mob("Steve", { amb: [0.2, 0.2, 0.2] }));
    // gore: from you, where the blows land
    const at = (t, up = 1.35, fw = 0.2) => { const c = cam(t), f = { x: -Math.sin(c.yaw), z: Math.cos(c.yaw) }; return [c.x + f.x * fw, Math.min(up, c.y - 0.1), c.z + f.z * fw]; };
    for (const [i, h] of hits.entries()) {
      const p = at(h.t, i < 2 ? 1.35 : 0.3, i < 2 ? 0.3 : 0.45), side = h.side;
      const f = { x: -Math.sin(cam(h.t).yaw), z: Math.cos(cam(h.t).yaw) }, r = { x: f.z, z: -f.x };
      R.burst(h.t + 0.01, p, i < 2 || i === 4 ? 30 : 8, "blood", { dir: [r.x * side * 1.2 + f.x * 0.3, i < 2 ? 0.7 : 1.4, r.z * side * 1.2 + f.z * 0.3], speed: 2.4, spread: 0.6, size: 0.032, life: 1.3, stick: 3 });
      if (i === 0 || i === 4) R.burst(h.t + 0.02, p, 7, "bone", { dir: [r.x * side, 0.8, r.z * side], speed: 1.6, spread: 0.6, size: 0.03, life: 1.2, stick: 3 });
    }

    // ---- the sound ----------------------------------------------------------------------------------------------------
    const steps = [];
    for (let tt = tW0 + 0.2; tt < tArr - 0.05; tt += 0.45) { const q = wAt(tt), d = Math.hypot(q.x, q.z); steps.push([tt, "mob.skeleton.step", { at: [q.x, 0.1, q.z], volume: clamp(0.75 - d * 0.08, 0.12, 0.6), pitch: 0.82 }]); }
    const sounds = [
      ...steps,
      silence(tFreeze, { fade: 0.3 }),
      [tArr - 0.02, "mob.skeleton.step", { at: [Sa.x, 0.1, Sa.z], volume: 0.75, pitch: 0.75 }],
      [tArr + 0.3, "mob.skeleton.say", { at: [Sa.x, 2.2, Sa.z], volume: 1.0, pitch: 0.62 }],
      [tStep + 0.15, "mob.skeleton.step", { at: [S1.x, 0.1, S1.z], volume: 0.9, pitch: 0.75 }],
      ...blow(tH1, { volume: 1.2, gore: true }), [tH1 + 0.01, "qf.scare.crunch", { volume: 0.9 }],
      ...deathScream(tH1 + 0.12, { volume: 1.15, under: false }),
      [tH2 - 0.25, "mob.skeleton.say", { at: [S1.x, 2.2, S1.z], volume: 0.9, pitch: 0.55 }],
      ...blow(tH2, { volume: 1.1, gore: false }),
      [tFloor - 0.02, "game.player.hurt.fall.small", { volume: 1.0 }], [tFloor, "step.stone", { volume: 0.8, pitch: 0.7 }],
      [tH2 + 0.6, "mob.skeleton.step", { at: [S2.x, 0.1, S2.z], volume: 0.8, pitch: 0.75 }], [tW1 - 0.1, "mob.skeleton.step", { at: [S2.x, 0.1, S2.z], volume: 0.8, pitch: 0.7 }],
      [tW1, "game.player.hurt", { volume: 0.55 }], [tW2, "game.player.hurt", { volume: 0.55 }],
      [tUp, "mob.skeleton.say", { at: [S2.x, 2.2, S2.z], volume: 1.1, pitch: 0.5 }],
      ...blow(DUR, { volume: 1.2, gore: true }), [DUR + 0.01, "qf.scare.crunch", { volume: 1.0 }],
      [DUR, "game.player.die"], [DUR, "@muffle", { hz: 380, s: 3.2 }]
    ];
    const loops = [
      [0.5, tFreeze, "qf.scare.heartbeat", { volume: 0.5, fadeOut: 0.25 }],
      [0.4, tFreeze, "qf.scare.drone", { volume: 0.4, fadeIn: 1.5, fadeOut: 0.3, pitch: 0.7, bus: "sfx" }],
      [tTurn0, tH1, "qf.scare.heartbeat", { volume: 0.6, pitch: 1.25, fadeIn: 0.4, fadeOut: 0.05 }],
      [tH1, DUR + 0.2, "qf.scare.heartbeat", { volume: 0.7, pitch: 1.45, fadeIn: 0.05 }],
      [tFloor, DUR, "qf.scare.breath", { volume: 0.5, pitch: 0.9, fadeIn: 0.3 }]
    ];

    // ---- the frame ----------------------------------------------------------------------------------------------------
    const youAt = (t) => { const c = cam(Math.min(t, tFl)); return { x: c.x, z: c.z, yaw: c.yaw }; };
    function update(t, f) {
      R._t = t;
      const cl = R.toLocal(R.camera.position);
      // It: walking up out of the dark, past the torch, to you; it strikes; it looks down at you; it strikes again;
      // it steps over you; the sword goes up and comes down.
      let q, walk = 0, lookP = 0, sw = 0, raise = 0;
      if (t < tArr) { q = wAt(t); walk = t > tW0 ? 0.75 : 0; }
      else if (t < tH1 + 0.1) { const k = sstep(tStep, tH1 - 0.1, t); q = { x: lerp(Sa.x, S1.x, k), z: lerp(Sa.z, S1.z, k) }; walk = k > 0.02 && k < 0.98 ? 0.6 : 0; }
      else if (t < tH2 + 0.3) { q = S1; lookP = 0.55 * sstep(tH1 + 0.15, tH1 + 0.6, t); }
      else { const k = sstep(tH2 + 0.3, tW1, t); q = { x: lerp(S1.x, S2.x, k), z: lerp(S1.z, S2.z, k) }; walk = k > 0.02 && k < 0.98 ? 0.6 : 0; lookP = 0.55 + 0.35 * k; }
      sw = swingAt(t, [tH2 - 0.15], 0.3);
      // the sword up over its head, and down: behind you (the first blow) and over you on the floor (the last)
      raise = Math.max(sstep(tRaise, tRaise + 0.45, t) * (1 - sstep(tH1 - 0.14, tH1, t)), sstep(tUp, tUp + 0.3, t) * (1 - sstep(DUR - 0.14, DUR, t)));
      const chop = Math.max(t >= tH1 - 0.14 && t < tH1 + 0.35 ? 1 - sstep(tH1 + 0.1, tH1 + 0.35, t) : 0, t >= DUR - 0.14 ? 1 : 0);
      const face = t < tArr ? R.yawTo(q.x, q.z, q.x + (S1.x - S0.x), q.z + (S1.z - S0.z)) : R.yawTo(q.x, q.z, cl.x, cl.z);
      R.place(W, q.x, 0, q.z, face, 0);
      W.anim(t, 0, { walk, lookPitch: lookP });
      bipedSwing(W, sw);
      if (W.parts.rightArm && (raise > 0 || chop > 0)) mcRot(W.parts.rightArm, raise > 0.001 ? lerp(-0.3, -2.75, raise) : lerp(-0.3, -0.55, chop), 0.1, 0);
      W.pivot.visible = true;
      // its own light: a little, so the black bone reads against the torch behind it
      W.setOwn(0.03 + 0.1 * sstep(tTurn0, tH1, t) + 0.05 * sstep(tFloor, tW1, t));
      // the shadows: its copy, and your body standing where you stand (until you go down)
      SH.mirror(W, Wsh);
      const y = youAt(t);
      R.place(you, y.x, 0, y.z, y.yaw); you.anim(t, 0, { walk: 0, still: true });
      you.pivot.visible = t < tFl + 0.1;
      SH.set({ strength: 0.9 * sstep(0.2, 1.2, t) * (1 - 0.5 * sstep(tFl, tFloor + 0.5, t)) });
      if (ownTorch) ownTorch.userData.light.intensity = 0.6 * sstep(0, 1.0, t);
      spot.intensity = 11 * sstep(0.1, 1.3, t) * (1 - 0.6 * sstep(tFloor, DUR, t));
      // the Wither: black hearts from the first blow; the dark closing in from the edges on the floor
      f.hpMode = t >= tH1 ? "wither" : "normal";
      const dark = sstep(tFloor, DUR + 0.4, t);
      f.env = { bake: 1 - 0.15 * sstep(0.3, 1.5, t) - 0.35 * dark, lights: 1 - 0.4 * dark, fogMul: 1 + 0.5 * sstep(0.5, 3, t) + 1.2 * dark };
      f.vig = [0, 0, 0, Math.min(1, 0.25 + 0.15 * sstep(tFreeze, tH1, t) + 0.55 * dark)]; f.vigR = 0.9 - 0.35 * dark;
      f.tints = [[0, 0, 0, 0.18 * sstep(tH1, tH1 + 0.5, t) + 0.25 * dark]];
      f.splats = [hits[0], hits[1], hits[4]].filter((h) => t >= h.t).map((h, i) => ({ t0: h.t, x: [0.66, 0.3, 0.5][i], y: [0.42, 0.55, 0.35][i], r: [11, 10, 14][i], seed: 61 + i }));
      f.black = 0.5 * sstep(DUR - 0.1, DUR + 0.6, t);
    }
    return { dur: DUR, hits, cam, update, sounds, loops, deathSide: dirT,
      marks: { dread: tSh + 0.6, fake: tTurn0 + 0.6, lunge: tH1, kill: tH2 + 0.6 },
      notes: { score: best.score != null ? +best.score.toFixed(2) : null, H: [best.H.x, best.H.y, best.H.z].map((v) => +v.toFixed(2)), K: [best.K.x, best.K.y, best.K.z].map((v) => +v.toFixed(2)), walls: [R.wallL, R.wallR], floor: !!best.floor, ownTorch: !!ownTorch, light: Lp.map((v) => +v.toFixed(2)), yawS: +yawS.toFixed(2), pitchS: +pitchS.toFixed(2), tSh: +tSh.toFixed(2), tArr: +tArr.toFixed(2), tH1: +tH1.toFixed(2), dur: +DUR.toFixed(2) } };
  }
};
