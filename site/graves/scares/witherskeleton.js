// Wither Skeleton (round 8, rethought: the shadow). The walk stops square on to a flat wall, two or three metres off,
// with a torch on the wall behind you (your shadow sprang up the stone as you passed it): your shadow, head, shoulders
// and the sword in your hand, crisp in the torchlight; the rest of the crypt has gone dim. Its steps, faint, somewhere
// behind you. Then it steps between the torch and you: the wall goes black with it, a skull and long thin limbs spilling
// over the whole stone; it shrinks as it comes up behind you, until it stands over yours, half as tall again, and the
// sword goes up the wall. You go still. You turn round, slowly, and it does not wait: as you turn it swings (a wither
// skeleton strikes the moment you are in reach) and the blow knocks your head round to it. Your hearts go black
// (Wither). It towers over you against the torchlight, 1.2 times a skeleton, and looks down at you; it swings again
// and you go down. On your back, the Wither eats at your hearts; it steps over you, the sword goes up, and comes down.
// Vanilla throughout: the 1.2-scale model and texture, the stone sword, the skeleton's sounds (1.7.10 has no others for
// it), the Wither hearts; the one device is the shadow itself (1.7.10 draws none; this torch does).
// The torch is a copy of one of the Krypt's wall torches (its model and material), moved whole blocks to the wall
// behind the spot, at eye level as a player sets one; it is there from the first frame. The spot is the nearest one
// along the walk with a flat face (3 m wide, 2.6 m high) two to three metres off and a wall behind for the torch.
import { THREE, clamp, lerp, sstep, pulse } from "./rig.js";
import { shake, hitsOf, floorFall, bipedSwing, swingAt, mcRot } from "./common.js";
import { silence, deathScream } from "./fnaf.js";
import { blow, kick } from "./story.js";
import { castShadows } from "./shadow.js";

const wrap = (a) => Math.atan2(Math.sin(a), Math.cos(a));

export default {
  death: "Steve was slain by Wither Skeleton",
  async build(R) {
    const eye = R.eye;
    const land = (Lp, p) => { const d = [p[0] - Lp[0], p[1] - Lp[1], p[2] - Lp[2]], n = Math.hypot(...d); const u = d.map((v) => v / n); const r = R.ray(p[0], p[1], p[2], u[0], u[1], u[2], 16, 0.03); return { x: p[0] + u[0] * r, y: p[1] + u[1] * r, z: p[2] + u[2] * r, r }; };
    const ray = (x, y, z, dx, dz, max) => R.ray(x, y, z, dx, 0, dz, max, 0.02);
    const clearPath = (a, b, ys = [0.5, 1.2, 2.0]) => { const n = Math.max(1, Math.ceil(Math.hypot(b.x - a.x, b.z - a.z) / 0.25)); for (let i = 0; i <= n; i++) { const x = lerp(a.x, b.x, i / n), z = lerp(a.z, b.z, i / n); if (ys.some((y) => R.solid(x, y, z)) || !R.solid(x, -0.3, z)) return false; } return true; };

    // ---- the Krypt's wall torches, the models for ours ----------------------------------------------------------------
    const temps = [];
    for (const T of R.torches) {
      const side = Math.sign(T.l.x); if (!side || Math.abs(T.l.x) > 9) continue;
      const tb = new THREE.Vector3(Math.floor(T.w.x), Math.floor(T.w.y), Math.floor(T.w.z));
      const att = R.dirW(side, 0, 0).map(Math.round);
      if (R.solidW(tb.x + att[0] + 0.5, tb.y + 0.5, tb.z + att[2] + 0.5)) temps.push({ T, side, tb });
    }
    // ---- where the walk stops: square on to a flat face, with a wall behind you for the torch -------------------------
    const st = R.start;
    const hfov = Math.atan(Math.tan(THREE.MathUtils.degToRad(R.camera.fov) / 2) * (R.camera.aspect || 1.78));
    const lookS = { x: -Math.sin(st.yaw), z: Math.cos(st.yaw) };
    const seen0 = (p) => { const v = { x: p.x - st.x, z: p.z - st.z }, n = Math.hypot(v.x, v.z) || 1; return (v.x * lookS.x + v.z * lookS.z) / n > Math.cos(hfov + 0.12); };
    const flatAt = (s, dW, zc, half) => {
      for (let dz = -half; dz <= half + 1e-6; dz += 0.4) {
        for (const y of [0.25, 0.9, 1.6, 2.3, 2.6]) if (!R.solid(s * (dW + 0.2), y, zc + dz) || R.solid(s * (dW - 0.2), y, zc + dz)) return false;
        // and open in front of it (no pillar, no recess side between it and you)
        for (const d of [0.8, 1.7]) for (const y of [0.9, 2.0]) if (R.solid(s * (dW - d), y, zc + dz)) return false;
      }
      return true;
    };
    function search({ zMax, half, dMin, pen }) {
      let best = null;
      for (let zs = 0; zs <= zMax + 1e-6; zs += 0.5) {
        if (!clearPath({ x: 0, z: 0 }, { x: 0, z: zs })) break;   // the walk goes no further
        for (const s of [-1, 1]) {
          const dW = ray(0, 1.0, zs, s, 0, 9); if (dW >= 9 || dW < dMin) continue;
          const xs = s * Math.max(0, dW - 3.0), dF = dW - Math.abs(xs);
          if (!flatAt(s, dW, zs, half) || !clearPath({ x: 0, z: zs }, { x: xs, z: zs })) continue;
          // how far the face stays flat each way along it (its shadow stands to the roomier side of yours)
          const ext = (dir) => { let e = half; for (let d = half + 0.25; d <= 3.01; d += 0.25) { if (!flatAt(s, dW, zs + dir * d, 0)) break; e = d; } return e; };
          const eP = ext(1), eN = ext(-1);
          const dO = ray(xs, 1.5, zs, -s, 0, 8); if (dO >= 8 || dO < 1.3) continue;
          const fx = xs - s * dO, tp = temps.find((q) => q.side === -s); if (!tp) continue;
          const att = R.dirW(-s, 0, 0).map(Math.round);
          for (const dz of [0, -0.5, 0.5, -1, 1, -1.5, -2]) {   // (further back along the way: out of sight as you come)
            const wb = R.L(fx + s * 0.5, 1.5, zs + dz), blk = new THREE.Vector3(Math.floor(wb.x), Math.floor(wb.y), Math.floor(wb.z));
            if (!R.solidW(blk.x + att[0] + 0.5, blk.y + 0.5, blk.z + att[2] + 0.5) || R.solidW(blk.x + 0.5, blk.y + 0.5, blk.z + 0.5)) continue;
            const dB = blk.clone().sub(tp.tb), tipW = tp.T.w.clone().add(dB);
            if (R.torches.some((o) => o.w.distanceTo(tipW) < 1.2)) continue;
            const tip = R.toLocal(tipW), Lp = [tip.x, tip.y + 0.1, tip.z];
            const rP = Math.hypot(xs - Lp[0], zs - Lp[2]), H = land(Lp, [xs, 1.85, zs]);
            const onFace = Math.abs(H.x - s * dW) < 0.12 && Math.abs(H.z - zs) < 1.2 && H.y > 0.9;
            const vis = seen0(tip) ? 1 : 0;
            // (a torch further back throws figures nearer their own size; a torch on the face itself would compete)
            const faceTorch = R.torches.some((o) => Math.abs(o.l.x - s * dW) < 0.7 && Math.abs(o.l.z - zs) < 2.3) ? 1 : 0;
            const score = zs * 0.3 + Math.abs(dF - 2.9) + Math.abs(rP - 4.3) * 0.5 + Math.abs(H.z - zs) * 0.8 + (onFace ? 0 : 5) + vis * 1.2 + faceTorch * 1.5 + Math.max(0, 2.2 - Math.max(eP, eN)) * 2 + pen;
            if (!best || score < best.score) best = { s, zs, xs, dW, dF, dO, Lp, tp, dB, rP, H, vis, score, roomZ: eP >= eN ? 1 : -1 };
          }
        }
      }
      return best;
    }
    let spot = null;
    for (const o of [{ zMax: 7, half: 1.6, dMin: 2.0, pen: 0 }, { zMax: 12, half: 1.2, dMin: 2.0, pen: 0.6 }, { zMax: 12, half: 0.8, dMin: 1.7, pen: 1.2 }]) {
      if (spot && spot.score < 2.6) break;
      const b = search(o); if (b && (!spot || b.score < spot.score)) spot = b;
    }
    if (!spot) {
      // nowhere along the walk (a stair, a shaft): the nearer wall, a light across from it at eye level
      const s = R.wallL <= R.wallR ? -1 : 1, dW = Math.min(s < 0 ? R.wallL : R.wallR, 8), dO = Math.min(s < 0 ? R.wallR : R.wallL, 3);
      const Lp = [-s * (dO - 0.3), 1.95, -0.3];
      spot = { s, zs: 0, xs: 0, dW, dF: dW, dO, Lp, tp: null, rP: Math.hypot(Lp[0], Lp[2]), H: land(Lp, [0, 1.85, 0]), vis: 0, score: 99, roomZ: 1 };
    }
    const { s, Lp } = spot, P = { x: spot.xs, z: spot.zs };
    const C = [s * spot.dW, 1.5, spot.zs];                                   // the middle of the face
    let yawS = -s * Math.PI / 2; const pitchS = 0;                                // square on to it (the floor line at the foot of the frame)
    // the torch: the template's quads moved whole blocks, the Krypt's own torch material; its light, a little out
    let ownTorch = null;
    if (spot.tp) {
      const { T } = spot.tp, src = T.mesh.geometry, g = new THREE.BufferGeometry();
      for (const [name, at] of Object.entries(src.attributes)) {
        const arr = new at.array.constructor(20 * at.itemSize);
        for (let q = 0; q < 20; q++) for (let c = 0; c < at.itemSize; c++) arr[q * at.itemSize + c] = at.array[(T.i + q) * at.itemSize + c];
        g.setAttribute(name, new THREE.BufferAttribute(arr, at.itemSize, at.normalized));
      }
      if (src.index) { const ix = [], I = src.index.array; for (let k = 0; k + 2 < I.length; k += 3) if (I[k] >= T.i && I[k] < T.i + 20 && I[k + 1] >= T.i && I[k + 1] < T.i + 20 && I[k + 2] >= T.i && I[k + 2] < T.i + 20) ix.push(I[k] - T.i, I[k + 1] - T.i, I[k + 2] - T.i); g.setIndex(ix); }
      g.applyMatrix4(T.mesh.matrixWorld); g.translate(spot.dB.x, spot.dB.y, spot.dB.z);
      ownTorch = new THREE.Mesh(g, T.mesh.material); R.add(ownTorch);
      // (if it is in sight as the scare takes the head, it comes up over the first moments rather than being there at once)
      if (spot.vis) { const fm = T.mesh.material.clone(); fm.transparent = true; fm.opacity = 0; ownTorch.userData.fade = fm; ownTorch.userData.mat = T.mesh.material; ownTorch.material = fm; }
    }
    const glow = R.ownLight(R.light(0xffc880, 0, 6, 1.6)); R.at(glow, Lp[0] + s * 0.45, Lp[1] - 0.15, Lp[2]);
    // its light on the face, where the shadows fall: a cone from the flame, the light that makes them
    const D = Math.hypot(C[0] - Lp[0], C[1] - Lp[1], C[2] - Lp[2]);
    const spotL = R.ownLight(new THREE.SpotLight(0xffc27a, 0, 0, Math.atan(3.6 / D) + 0.12, 0.35, 1.0)); R.at(spotL, Lp[0], Lp[1], Lp[2]); R.add(spotL);
    R.at(spotL.target, C[0], C[1], C[2]); R.add(spotL.target);

    // ---- its way: along the wall behind you out of the dark, in front of the torch, then up behind you ---------------
    const u = (() => { const dx = P.x - Lp[0], dz = P.z - Lp[2], n = Math.hypot(dx, dz) || 1; return { x: dx / n, z: dz / n }; })();
    const pp = { x: -u.z, z: u.x };                                           // across the line, along the wall
    const at2 = (o, du, dp) => ({ x: o.x + u.x * du + pp.x * dp, z: o.z + u.z * du + pp.z * dp });
    // (to the side where the face runs on further, so its shadow stands on flat stone beside yours)
    const side2 = Math.sign(pp.z * spot.roomZ) || 1;
    const dSa = clamp(spot.rP * 0.25, 0.95, 1.1);   // (a pace behind you: its blade, held out before it, clear of your head)
    const Sa = at2(P, -dSa, 0.35 * side2);       // where it stands over you: a pace behind, to one side (its shadow beside yours)
    const S1 = at2(P, -dSa, 0.3 * side2);               // where it strikes from (in reach: a wither skeleton hits inside ~1.6 m)
    const Sb = at2({ x: Lp[0], z: Lp[2] }, Math.min(2.2, spot.rP * 0.5), 0.3 * side2);   // in front of the torch
    let S0 = null;
    for (const x of [Sb.x, (Sb.x + P.x) / 2, P.x]) { const c = { x, z: Math.min(Sb.z - 4.5, -2.2) }; if (clearPath(c, Sb)) { S0 = c; break; } }
    if (!S0) S0 = { x: Sb.x, z: Sb.z - 1.5 };

    // ---- the beats ----------------------------------------------------------------------------------------------------
    const Lw = Math.hypot(P.x - st.x, P.z - st.z);
    const tWk = Lw > 0.3 ? 0.4 + Lw / 1.5 : 0;                                // the walk to the spot
    const tTurnS = tWk > 0 ? tWk - 0.35 : 0.35, tStop = tTurnS + 1.15;       // the turn to the wall
    const tSpill = tStop + R.vary(1.7, 0.15);                                // it steps in front of the torch
    let l0 = Math.hypot(Sb.x - S0.x, Sb.z - S0.z);
    if (tSpill - l0 / 1.6 < 0.2) { const k = ((tSpill - 0.2) * 1.6) / l0; S0 = { x: Sb.x + (S0.x - Sb.x) * k, z: Sb.z + (S0.z - Sb.z) * k }; l0 = Math.hypot(Sb.x - S0.x, Sb.z - S0.z); }
    const tW0 = tSpill - l0 / 1.6, l1 = Math.hypot(Sa.x - Sb.x, Sa.z - Sb.z);
    const tFreeze = tSpill + 0.12, tGo = tSpill + 0.25, tArr = tGo + l1 / 1.15;
    const tRaise = tArr + 0.1, tTurn0 = tArr + R.vary(0.8, 0.15), tH1 = tTurn0 + R.vary(0.7, 0.12);
    const wAt = (t) => {
      if (t < tSpill) { const k = clamp((t - tW0) / (tSpill - tW0)); return { x: lerp(S0.x, Sb.x, k), z: lerp(S0.z, Sb.z, k), walk: t > tW0 ? 0.75 : 0, dir: [Sb.x - S0.x, Sb.z - S0.z] }; }
      const k = clamp((t - tGo) / (tArr - tGo)); return { x: lerp(Sb.x, Sa.x, k), z: lerp(Sb.z, Sa.z, k), walk: k > 0.01 && k < 0.99 ? 0.6 : 0, dir: [Sa.x - Sb.x, Sa.z - Sb.z] };
    };
    // square on to the face, turned a little to frame the pair of shadows (yours and its, where it will stand)
    { const h = land(Lp, [P.x, 1.6, P.z]), k = land(Lp, [Sa.x, 2.0, Sa.z]); yawS += clamp(wrap(R.yawTo(P.x, P.z, (h.x + k.x) / 2, (h.z + k.z) / 2) - yawS), -0.3, 0.3); }
    const yawK = R.yawTo(P.x, P.z, S1.x, S1.z);
    const dirT = Math.sign(wrap(yawK - yawS)) || 1, spanT = Math.abs(wrap(yawK - yawS));
    const tH2 = tH1 + 1.05, tFl = tH2 + 0.05, tFloor = tFl + 0.5;
    const tW1 = tFloor + 0.45, tW2 = tW1 + 0.55, tUp = tW2 + 0.1, tH3 = tUp + 0.5, DUR = tH3 + 0.15;
    const hits = hitsOf([[tH1, 7, -dirT], [tH2, 6, dirT], [tW1, 2, 1], [tW2, 2, -1], [DUR, 3, 1]]);
    const kb = (() => { const dx = P.x - S1.x, dz = P.z - S1.z, n = Math.hypot(dx, dz) || 1; return { x: dx / n, z: dz / n }; })();
    const S2 = { x: P.x + kb.x * 0.25, z: P.z + kb.z * 0.25 };   // where it stands over you on the floor (you went back a step)
    // ---- the head -----------------------------------------------------------------------------------------------------
    const turnK = (t) => {   // the slow turn; the blow knocks the rest of the way round
      const slow = clamp((t - tTurn0) / 1.7); let k = slow * slow * (3 - 2 * slow) * 0.85;
      if (t >= tH1) { const k1 = (() => { const s0 = clamp((tH1 - tTurn0) / 1.7); return s0 * s0 * (3 - 2 * s0) * 0.85; })(); k = lerp(k1, 1, 1 - Math.pow(1 - clamp((t - tH1) / 0.22), 3)); }
      return k;
    };
    const skullAt = (t) => { const q = t < tH2 + 0.3 ? S1 : { x: lerp(S1.x, S2.x, sstep(tH2 + 0.3, tW1, t)), z: lerp(S1.z, S2.z, sstep(tH2 + 0.3, tW1, t)) }; return { x: q.x, y: 2.15, z: q.z }; };
    const walkYaw = Lw > 0.5 ? R.yawTo(st.x, st.z, P.x, P.z) : st.yaw;
    const yawS2 = walkYaw + wrap(yawS - walkYaw);
    const cam = (t) => {
      const kW = tWk > 0 ? sstep(0, tWk, t) : 0, walking = tWk > 0 ? sstep(0, 0.35, t) * (1 - sstep(tWk - 0.45, tWk, t)) : 0;
      let yaw = lerp(st.yaw, walkYaw, sstep(0, 0.6, t)); yaw = lerp(yaw, yawS2, sstep(tTurnS, tStop, t));
      let pitch = lerp(lerp(st.pitch, -0.03, sstep(0, 0.6, t)), pitchS, sstep(tTurnS, tStop, t));
      // the eyes go up the wall with its sword
      pitch += 0.14 * sstep(tRaise, tRaise + 0.7, t) * (1 - sstep(tTurn0, tTurn0 + 0.7, t));
      const c = { x: lerp(st.x, P.x, kW), y: lerp(st.y, eye, sstep(0, 0.6, t)) + 0.022 * Math.sin(t * 8.4) * walking, z: lerp(st.z, P.z, kW), yaw, pitch, roll: 0, fov: st.fov, near: t >= tTurn0 ? 0.02 : undefined };
      c.y -= 0.01 * sstep(tFreeze, tFreeze + 0.2, t);
      // the turn round, slowly; then the eyes go up it to its skull
      c.yaw = yaw + dirT * spanT * turnK(t);
      c.pitch = lerp(c.pitch, -0.02, sstep(tTurn0, tTurn0 + 1.0, t));
      const sk = skullAt(t), up = clamp(R.pitchTo(c.x, c.y, c.z, sk.x, sk.y, sk.z), -0.2, 0.75);
      c.pitch = lerp(c.pitch, up, sstep(tH1 + 0.1, tH1 + 0.6, t));
      const kn = 0.35 * sstep(tH1, tH1 + 0.3, t); c.x += kb.x * kn; c.z += kb.z * kn;   // (the blow knocks you back a step)
      const kk = kick(t, hits.slice(0, 2).map((h) => ({ t: h.t, side: h.side, amp: 1.3 })).concat(hits.slice(2).map((h) => ({ t: h.t, side: h.side, amp: 0.4 }))));
      c.yaw += kk.yaw; c.pitch += kk.pitch;
      // knocked down; on your back, the eyes on it as it steps over you
      floorFall(c, t, tFl, { d: 0.5, side: dirT, roll: 0.55, y: 0.28, pitch: 0.95, back: 0.35 });
      if (t > tFloor) { const q = skullAt(t), ly = R.yawTo(c.x, c.z, q.x, q.z); c.yaw = lerp(c.yaw, c.yaw + wrap(ly - c.yaw) * 0.8, sstep(tFloor, tW1, t)); c.pitch = lerp(c.pitch, clamp(R.pitchTo(c.x, c.y, c.z, q.x, q.y, q.z) + 0.15, 0.5, 1.3), sstep(tFloor, tW1 + 0.3, t)); }
      c.fov = st.fov - 4 * sstep(tTurn0, tTurn0 + 1, t) * (1 - sstep(tH1, tH1 + 0.3, t)) + 6 * pulse(t, [tH1, tH2, DUR], 0.15);
      const amp = 0.0015 + 0.0025 * sstep(tFreeze, tH1, t) + 0.03 * pulse(t, [tH1, tH2, tFloor, DUR], 0.15) + 0.01 * pulse(t, [tW1, tW2], 0.12) + 0.004 * sstep(tH1, tH1 + 0.3, t);
      return shake(c, t, amp, 6);
    };

    // ---- the figures --------------------------------------------------------------------------------------------------
    const W = R.mob("WitherSkeleton", { amb: [0.03, 0.03, 0.035], own: true, equipment: [{ id: "minecraft:stone_sword", ench: false }] });
    W.anim(0, 0, {}); R.place(W, S0.x, 0, S0.z, 0);
    // the shadows: drawn from the flame, the light's frustum fitted to the face (2048, hard-edged)
    const SH = castShadows(R, { light: Lp, center: () => C, strength: 0, size: 2048, fov: THREE.MathUtils.radToDeg(2 * Math.atan(3.6 / D)), flat: true });
    R._sh = SH;   // (for checks)
    const Wsh = SH.add(R.mob("WitherSkeleton", { amb: [0.03, 0.03, 0.035], equipment: [{ id: "minecraft:stone_sword", ench: false }] }));
    // you: the body you stand in (it casts, it is not seen), with the sword the hotbar holds
    const you = SH.add(R.mob("Steve", { amb: [0.2, 0.2, 0.2], equipment: [{ id: "minecraft:iron_sword", ench: false }] }));
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
    for (let tt = tW0 + 0.2; tt < tArr - 0.05; tt += 0.45) {
      if (tt > tSpill - 0.1 && tt < tGo + 0.1) continue;
      const q = wAt(tt), d = Math.hypot(q.x - P.x, q.z - P.z);
      steps.push([tt, "mob.skeleton.step", { at: [q.x, 0.1, q.z], volume: clamp(0.8 - d * 0.09, 0.12, 0.65), pitch: 0.82 }]);
    }
    const sounds = [
      ...steps,
      [tSpill - 0.02, "mob.skeleton.step", { at: [Sb.x, 0.1, Sb.z], volume: 0.7, pitch: 0.78 }],
      silence(tFreeze, { fade: 0.3 }),
      [tArr - 0.02, "mob.skeleton.step", { at: [Sa.x, 0.1, Sa.z], volume: 0.8, pitch: 0.75 }],
      [tArr + 0.3, "mob.skeleton.say", { at: [Sa.x, 2.2, Sa.z], volume: 1.0, pitch: 0.62 }],
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
      // It: along the wall out of the dark, in front of the torch, up behind you; it strikes; it looks down at you; it
      // strikes again; it steps over you; the sword goes up and comes down.
      let q, walk = 0, lookP = 0, face;
      if (t < tArr) { const w = wAt(t); q = w; walk = w.walk; face = R.yawTo(0, 0, w.dir[0], w.dir[1]); }
      else if (t < tH2 + 0.3) { q = t < tH1 - 0.2 ? Sa : S1; lookP = 0.55 * sstep(tH1 + 0.15, tH1 + 0.6, t); face = R.yawTo(q.x, q.z, cl.x, cl.z); }
      else { const k = sstep(tH2 + 0.3, tW1, t); q = { x: lerp(S1.x, S2.x, k), z: lerp(S1.z, S2.z, k) }; walk = k > 0.02 && k < 0.98 ? 0.6 : 0; lookP = 0.55 + 0.35 * k; face = R.yawTo(q.x, q.z, cl.x, cl.z); }
      if (t >= tArr && t < tH1 - 0.2) { const w = sstep(tArr - 0.3, tArr + 0.3, t); face = lerp(R.yawTo(0, 0, Sa.x - Sb.x, Sa.z - Sb.z), R.yawTo(Sa.x, Sa.z, P.x, P.z), w); }
      const sw = swingAt(t, [tH2 - 0.15], 0.3);
      // the sword up over its head, and down: behind you (the first blow) and over you on the floor (the last)
      const raise = Math.max(sstep(tRaise, tRaise + 0.5, t) * (1 - sstep(tH1 - 0.14, tH1, t)), sstep(tUp, tUp + 0.3, t) * (1 - sstep(DUR - 0.14, DUR, t)));
      const chop = Math.max(t >= tH1 - 0.14 && t < tH1 + 0.35 ? 1 - sstep(tH1 + 0.1, tH1 + 0.35, t) : 0, t >= DUR - 0.14 ? 1 : 0);
      R.place(W, q.x, 0, q.z, face, 0);
      W.anim(t, 0, { walk, lookPitch: lookP });
      bipedSwing(W, sw);
      // (raised out to its side as well as up, so the blade's sweep passes wide of your head)
      if (W.parts.rightArm && (raise > 0 || chop > 0)) mcRot(W.parts.rightArm, raise > 0.001 ? lerp(-0.3, -2.75, raise) : lerp(-0.3, -0.55, chop), 0.1, raise > 0.001 ? 0.5 * Math.sin(Math.PI * Math.min(1, raise * 1.4)) + 0.15 * raise : 0);
      W.pivot.visible = true;
      // its own light: a little, so the black bone reads against the torch behind it
      W.setOwn(0.03 + 0.1 * sstep(tTurn0, tH1, t) + 0.05 * sstep(tFloor, tW1, t));
      // the shadows: its copy, and your body where you stand (until you go down), the sword held up a little
      SH.mirror(W, Wsh);
      const y = youAt(t);
      R.place(you, y.x, 0, y.z, y.yaw); you.anim(t, 0, { walk: tWk > 0 && t < tWk ? 0.6 : 0, still: !(tWk > 0 && t < tWk) });
      if (you.parts.rightArm) mcRot(you.parts.rightArm, -0.3, -0.6, 0.9);   // (the sword arm out from your side, the blade clear of you)   // (the arm up before you, the blade upright beside your head)
      you.pivot.visible = t < tFl + 0.1;
      SH.set({ strength: 0.84 * sstep(0, 0.6, t) * (1 - 0.6 * sstep(tFl, tFloor + 0.5, t)) });
      // the torch (there from the first frame; its light comes up as the scare takes the head) dominates the face: the
      // crypt's own light and torches go down round it while you stand there, and come back as you turn
      glow.intensity = 0.6 * sstep(0, 0.6, t);
      if (ownTorch && ownTorch.userData.fade) { const k = sstep(0, 0.8, t); ownTorch.material = k >= 1 ? ownTorch.userData.mat : ownTorch.userData.fade; ownTorch.userData.fade.opacity = k; }
      spotL.intensity = 9 * sstep(0, 0.6, t) * (1 - 0.6 * sstep(tFloor, DUR, t));
      const beat = sstep(tTurnS, tStop + 0.3, t) * (1 - 0.65 * sstep(tTurn0 + 0.3, tH1 + 0.4, t));
      // the Wither: black hearts from the first blow; the dark closing in from the edges on the floor
      f.hpMode = t >= tH1 ? "wither" : "normal";
      const dark = sstep(tFloor, DUR + 0.4, t);
      f.env = { bake: 1 - 0.68 * beat - 0.3 * dark, lights: 1 - 0.75 * beat - 0.35 * dark, fogMul: 1 + 0.5 * sstep(0.5, 3, t) + 1.2 * dark };
      f.vig = [0, 0, 0, Math.min(1, 0.25 + 0.15 * sstep(tFreeze, tH1, t) + 0.55 * dark)]; f.vigR = 0.9 - 0.35 * dark;
      f.tints = [[0, 0, 0, 0.18 * sstep(tH1, tH1 + 0.5, t) + 0.25 * dark]];
      f.splats = [hits[0], hits[1], hits[4]].filter((h) => t >= h.t).map((h, i) => ({ t0: h.t, x: [0.66, 0.3, 0.5][i], y: [0.42, 0.55, 0.35][i], r: [11, 10, 14][i], seed: 61 + i }));
      f.black = 0.5 * sstep(DUR - 0.1, DUR + 0.6, t);
    }
    const r2 = (v) => +v.toFixed(2);
    return { dur: DUR, hits, cam, update, sounds, loops, deathSide: dirT,
      marks: { dread: tSpill + 0.3, fake: tTurn0 + 0.5, lunge: tH1, kill: tH2 + 0.6 },
      notes: { stop: [r2(P.x), r2(P.z)], side: s, face: r2(spot.dF), torchBack: r2(spot.rP), walk: r2(Lw), torch0seen: spot.vis, score: r2(spot.score), light: Lp.map(r2), tStop: r2(tStop), tSpill: r2(tSpill), tArr: r2(tArr), tTurn0: r2(tTurn0), tH1: r2(tH1), dur: r2(DUR) } };
  }
};
