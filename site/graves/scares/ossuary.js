// An ossuary carved beside the corridor (round 8b, the Skeleton). A doorway one block wide and two high in the side
// wall behind and beside the visitor (out of frame when the scare takes the head, and all through the settle), a short
// cut through the wall, and a rock-cut room behind it: the corridor's own masonry for walls, a low roof, heaps of bones
// and skulls on the floor, skulls in niches in the walls, one torch on the far wall. Everything is carved with the
// Krypt's carve contract in build, before the first frame, and put back on dispose.
//   const spot = findRoom(R)       null if nowhere fits (the shell all round must be solid rock, before the cut)
//     spot.s       +1 right, -1 left: the wall the doorway is in
//     spot.T       blocks of wall between the corridor and the room
//     spot.a0, spot.Wa, spot.Dd, spot.H   the room: along the corridor from a0 (Wa blocks), Dd deep, H high
//     spot.P(a, y, d)   room coordinates -> local { x, y, z } (a along the corridor, d into the rock from the doorway
//                       block's centre, y up from the floor)
//   const O = await buildRoom(R, spot, opts)   (see below)
import { THREE, clamp, lerp, sstep, tex, loadImg } from "./rig.js";
import { mulberry } from "./common.js";
import { mcBoxGeometry as mcBox } from "../../lib/mc/mobs.js";

const wrap = (a) => Math.atan2(Math.sin(a), Math.cos(a));

export function findRoom(R, opts = {}) {
  // the near stretch first; then further back along the corridor, smaller rooms, thicker walls
  // (and in a hall, a wall further off)
  const small = [[7, 7], [6, 6], [5, 6], [5, 5], [4, 5], [5, 4], [4, 4]];
  return findRoom1(R, opts) || findRoom1(R, { zMin: -7.5, zMax: 2.5, Ts: [1, 2, 3], maxW: 14, sizes: small, ...opts }) ||
    // (last: well back along the way you came, or in a rough-hewn wall; the clatter is behind you and you go back to it)
    findRoom1(R, { zMin: -16, zMax: 2.5, Ts: [1, 2, 3], maxW: 14, sizes: small, flat: false, margin: 0.22, ...opts });
}
function findRoom1(R, { sizes = [[7, 7], [7, 6], [6, 7], [6, 6], [5, 6], [5, 5]], H = 3, zMin = -3.5, zMax = 1.5, Ts = [1, 2], maxW = 9, flat = true, margin = 0.35 } = {}) {
  const st = R.start, cam = R.camera;
  const hfov = Math.atan(Math.tan(THREE.MathUtils.degToRad(cam.fov) / 2) * (cam.aspect || 1.78));
  // In the frame at the start, or at any moment of the settle (the head swings from the start yaw to straight on).
  const seen = (x, z) => {
    const ang = Math.atan2(-(x - st.x), z - st.z);
    for (let k = 0; k <= 6; k++) if (Math.abs(wrap(ang - lerp(st.yaw, 0, k / 6))) < hfov + 0.22) return true;
    return false;
  };
  const graves = [];
  try {
    for (const g of (R.kr.gravesNear ? R.kr.gravesNear(R.O, 16) : [])) for (const p of [g.stone, g.statue]) if (p) { const l = R.toLocal(p); graves.push(l); }
  } catch (e) { /* no graves list */ }
  const clear = (a, b) => {
    const n = Math.max(1, Math.ceil(Math.hypot(b.x - a.x, b.z - a.z) / 0.2));
    for (let i = 0; i <= n; i++) {
      const x = lerp(a.x, b.x, i / n), z = lerp(a.z, b.z, i / n);
      if (R.solid(x, 0.3, z) || R.solid(x, 1.0, z) || R.solid(x, 1.8, z) || !R.solid(x, -0.5, z)) return false;
      // a body's width either side of the line (no grazing a pillar's edge on the way)
      const dl = Math.hypot(b.x - a.x, b.z - a.z) || 1, ox = -(b.z - a.z) / dl * margin, oz = (b.x - a.x) / dl * margin;
      if (R.solid(x + ox, 1.2, z + oz) || R.solid(x - ox, 1.2, z - oz)) return false;
      if (graves.some((g) => Math.hypot(g.x - x, g.z - z) < 0.75)) return false;
    }
    return true;
  };
  const torchCells = R.torches.map((t) => { const b = t.w; return [Math.floor(b.x), Math.floor(b.y), Math.floor(b.z)]; });
  const cache = new Map(), _p = new THREE.Vector3();
  let best = null;
  const why = (R.ossWhy = {}), no = (k) => { why[k] = (why[k] || 0) + 1; };
  for (const s of [-1, 1]) {
    for (let zq = zMin; zq <= zMax + 0.01; zq += 0.5) {
      const dW = R.ray(0, 1.0, zq, s, 0, 0, maxW, 0.05);
      if (dW >= maxW || dW < 0.6) { no('far'); continue; }
      // the doorway block: the first wall block on that side; its centre in local terms
      const w = R.L(s * (dW + 0.5), 0.5, zq), bx = Math.floor(w.x), bz = Math.floor(w.z);
      const c = R.toLocal(new THREE.Vector3(bx + 0.5, R.O.y + 0.5, bz + 0.5));
      const xc = c.x, zc = c.z;
      if (Math.abs(Math.abs(xc - s * 0.5) - dW) > 0.3) { no('face'); continue; }
      const S = (ai, j, di) => { const p = R.L(xc + s * di, j + 0.5, zc + ai, _p), k = Math.floor(p.x) + "," + Math.floor(p.y) + "," + Math.floor(p.z); let v = cache.get(k); if (v === undefined) { v = R.solidW(p.x, p.y, p.z); cache.set(k, v); } return v; };
      // a wall two high there, the corridor open in front of it, a floor under both
      if (!S(0, 0, 0) || !S(0, 1, 0) || !S(0, 2, 0) || S(0, 0, -1) || S(0, 1, -1) || !S(0, -1, 0) || !S(0, -1, -1)) { no('wall'); continue; }
      // flat wall either side of the doorway (not an alcove's edge or a pillar's)
      if (flat && (!S(-1, 0, 0) || !S(1, 0, 0) || !S(-1, 1, 0) || !S(1, 1, 0))) { no('flat'); continue; }
      // out of sight as the scare takes the head
      if ([[-0.5, 0], [0.5, 0], [-0.5, 2], [0.5, 2]].some(([da]) => seen(xc - s * 0.5, zc + da))) { no('seen'); continue; }
      if (graves.some((g) => Math.hypot(g.x - (xc - s * 0.6), g.z - zc) < 1.2)) { no('grave'); continue; }
      const front = { x: xc - s * 0.85, z: zc };
      if (!clear({ x: 0, z: 0 }, front)) { no('path'); continue; }
      // the rock under, round and over the room is all solid before the cut: per column (a, d), every block from the
      // floor's to the roof's; a summed table over them answers any rectangle at once
      const A0 = -9, A1 = 9, D1 = 3 + 8 + 1, NA = A1 - A0 + 1, ND = D1 + 1;
      const sum = new Int32Array((NA + 1) * (ND + 1));
      for (let ai = A0; ai <= A1; ai++) for (let di = 0; di <= D1; di++) {
        let solid = 1;
        for (let j = -1; j <= H; j++) if (!S(ai, j, di)) { solid = 0; break; }
        const i = ai - A0 + 1, k = di + 1;
        sum[i * (ND + 1) + k] = solid + sum[(i - 1) * (ND + 1) + k] + sum[i * (ND + 1) + k - 1] - sum[(i - 1) * (ND + 1) + k - 1];
      }
      const rock = (a0, a1, d0, d1) => {   // every column in [a0..a1] x [d0..d1] solid
        if (a0 < A0 || a1 > A1 || d0 < 0 || d1 > D1) return false;
        const i0 = a0 - A0, i1 = a1 - A0 + 1, k0 = d0, k1 = d1 + 1, W = ND + 1;
        return sum[i1 * W + k1] - sum[i0 * W + k1] - sum[i1 * W + k0] + sum[i0 * W + k0] === (a1 - a0 + 1) * (d1 - d0 + 1);
      };
      for (const T of Ts) {
        // no torch hangs on what the cut takes away
        let torchHit = false;
        for (let di = 0; di < T && !torchHit; di++) for (const j of [0, 1]) {
          const p = R.L(xc + s * di, j + 0.5, zc), q = [Math.floor(p.x), Math.floor(p.y), Math.floor(p.z)];
          if (torchCells.some((t) => Math.abs(t[0] - q[0]) + Math.abs(t[1] - q[1]) + Math.abs(t[2] - q[2]) <= 1)) torchHit = true;
        }
        if (torchHit) { no('torch'); continue; }
        // the wall itself, solid all through the cut
        let ok = true;
        for (let di = 0; di < T && ok; di++) for (const j of [-1, 0, 1, 2]) if (!S(0, j, di)) { ok = false; break; }
        if (!ok) continue;
        let found = false;
        for (const [Wa, Dd] of sizes) {
          if (found) break;
          for (let off = 0; off <= Wa - 1 && !found; off++) {
            const a0 = -Math.floor((Wa - 1) / 2) + (off % 2 ? 1 : -1) * Math.ceil(off / 2);
            if (a0 > 0 || a0 + Wa - 1 < 0) continue;
            // the shell: every block round the room (and the wall it sits behind) is rock before the cut
            if (!rock(a0 - 1, a0 + Wa, 0, T + Dd)) { no('shell' + Wa + 'x' + Dd); continue; }
            const ctr = a0 + (Wa - 1) / 2;
            const score = Math.abs(zc + 0.6) * 0.8 + Math.hypot(front.x, front.z) * 0.35 + (T - 1) * 0.4 + Math.abs(ctr) * 0.25 - Wa * Dd * 0.06 + (Math.sign(st.yaw) === -s ? 0 : Math.abs(st.yaw) * 0.6);
            if (!best || score < best.score) best = { s, xc, zc, T, a0, Wa, Dd, H, dW, score, front };
            found = true;
          }
        }
      }
    }
  }
  if (!best) return null;
  const { s, xc, zc } = best;
  best.P = (a, y, d) => ({ x: xc + s * d, y, z: zc + a });
  best.block = (ai, j, di) => { const p = R.L(xc + s * di, j + 0.5, zc + ai); return [Math.floor(p.x), Math.floor(p.y), Math.floor(p.z)]; };
  return best;
}

// ---- the pieces ------------------------------------------------------------------------------------------------
// A bone item as 1.7.10 draws one in the world (ItemRenderer.renderItemIn2D): the 16 x 16 sprite, a sixteenth thick,
// with a wall of each pixel column and row along its edges. Centred, the sprite in x/y, its face along +z.
function spriteGeometry(W = 16, H = 16) {
  const pos = [], uv = [], idx = [];
  const Z = -1 / 16;
  const quad = (a, b, c, d, ua, ub, uc, ud) => { const i = pos.length / 3; [a, b, c, d].forEach((p) => pos.push(...p)); [ua, ub, uc, ud].forEach((u) => uv.push(...u)); idx.push(i, i + 1, i + 2, i, i + 2, i + 3); };
  quad([0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0], [1, 0], [1, 1], [0, 1]);
  quad([0, 1, Z], [1, 1, Z], [1, 0, Z], [0, 0, Z], [0, 1], [1, 1], [1, 0], [0, 0]);
  for (let k = 0; k < W; k++) {
    const x0 = k / W, x1 = (k + 1) / W, u = (k + 0.5) / W;
    quad([x0, 0, Z], [x0, 0, 0], [x0, 1, 0], [x0, 1, Z], [u, 0], [u, 0], [u, 1], [u, 1]);
    quad([x1, 1, Z], [x1, 1, 0], [x1, 0, 0], [x1, 0, Z], [u, 1], [u, 1], [u, 0], [u, 0]);
  }
  for (let k = 0; k < H; k++) {
    const y0 = k / H, y1 = (k + 1) / H, v = (k + 0.5) / H;
    quad([0, y1, 0], [1, y1, 0], [1, y1, Z], [0, y1, Z], [0, v], [1, v], [1, v], [0, v]);
    quad([1, y0, 0], [0, y0, 0], [0, y0, Z], [1, y0, Z], [1, v], [0, v], [0, v], [1, v]);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3)); g.setAttribute("uv", new THREE.Float32BufferAttribute(uv, 2)); g.setIndex(idx);
  g.translate(-0.5, -0.5, 1 / 32); g.computeVertexNormals();
  return g;
}
// The wall torch as the Krypt draws it (dress.js torchGeometry, 1.7.10's renderTorchAtAngle): a 2 x 2 pixel column
// leaning 0.4 off the face, its cap at ten sixteenths. Face at (fx, fz) (world, out of the wall), cell floor y.
function torchGeometry(cx, y, cz, fx, fz) {
  const pos = [], uv = [], idx = [], h = 0.0625, lean = 0.4, px = -fz, pz = fx;
  const bx = cx + fx * 0.1, by = y + 0.22, bz = cz + fz * 0.1;
  const cor = [[-1, -1], [1, -1], [1, 1], [-1, 1]].map(([u, v]) => [fx * h * u + px * h * v, fz * h * u + pz * h * v]);
  const u0 = 7 / 16, u1 = 9 / 16;
  for (let q = 0; q < 4; q++) {
    const c0 = cor[q], c1 = cor[(q + 1) % 4], base = pos.length / 3;
    pos.push(bx + c0[0], by, bz + c0[1], bx + c1[0], by, bz + c1[1], bx + c1[0] + fx * lean, by + 1, bz + c1[1] + fz * lean, bx + c0[0] + fx * lean, by + 1, bz + c0[1] + fz * lean);
    uv.push(u0, 0, u1, 0, u1, 1, u0, 1); idx.push(base, base + 1, base + 2, base, base + 2, base + 3);
  }
  const base = pos.length / 3, k = 0.625;
  for (const c of cor) pos.push(bx + c[0] + fx * lean * k, by + k, bz + c[1] + fz * lean * k);
  uv.push(u0, 1 - 8 / 16, u1, 1 - 8 / 16, u1, 1 - 6 / 16, u0, 1 - 6 / 16); idx.push(base, base + 1, base + 2, base, base + 2, base + 3);
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3)); g.setAttribute("uv", new THREE.Float32BufferAttribute(uv, 2)); g.setIndex(idx); g.computeVertexNormals();
  return { g, tip: [bx + fx * lean * k, by + k, bz + fz * lean * k] };
}

// ---- the room ------------------------------------------------------------------------------------------------------
// const O = await buildRoom(R, spot, { seed, skull })   skull: a texture for the skulls (the skeleton's own skin)
//   O.carve()              the cut (in build, before the first frame)
//   O.heaps                [{ c: {x, z}, eu, ev, L, W, H, ... }] local: centre, long axis (a riser's head end), across
//   O.stop                 local { x, z }: the middle of the room, where the walk stops; O.mouth: inside the doorway
//   O.door                 local { x, z }: the doorway block's centre; O.front: in the corridor before it
//   O.torch                local [x, y, z]: the flame; O.light: its PointLight (the scare drives its flicker)
//   O.rollSkull(t0, to)    the skull on top of heap 0 tips and rolls off toward `to` (local {x,z}); returns its
//                          { tEdge, tFloor, tStop, knocks: [t...] }
//   O.kicks(path)          floor bones near a walk (fn t -> {x, z}, t0, t1) are kicked as the feet pass: [{t, at}]
//   O.riser(i, m, sch)     heap i's skeleton m lies in it and rises on schedule sch; returns pose(t) (until sch.stand1)
//   O.update(t)            every piece at time t (call after the risers' poses)
//   O.solid(world)         inside a heap's core now: what hides a skeleton lying in it (for sight lines)
export async function buildRoom(R, spot, { seed = 1, skull = null } = {}) {
  const { s, T, a0, Wa, Dd, H } = spot, P = spot.P;
  const rnd = mulberry(seed * 9973 + 17);
  const aMin = a0 - 0.5, aMax = a0 + Wa - 0.5, dNear = T - 0.5, dFar = T + Dd - 0.5;
  const aC = a0 + (Wa - 1) / 2, dC = T + (Dd - 1) / 2;
  const dirL = (da, dd) => ({ x: s * dd, z: da });
  const S0 = (ai, j, di) => { const b = spot.block(ai, j, di); return R.solidW(b[0] + 0.5, b[1] + 0.5, b[2] + 0.5); };
  // ---- the cut: the doorway, the room, niches in the walls (where there is rock behind them) ----------------------
  const boxes = [[[0, 0, 0], [0, 1, T - 1]], [[a0, 0, T], [a0 + Wa - 1, H - 1, T + Dd - 1]]];
  const aT = Math.round(aC);
  const niches = [];
  if (H >= 3) {
    for (let ai = a0; ai < a0 + Wa; ai++) {
      if ((ai - aT) % 2 === 0 || Math.abs(ai - aT) < 2) continue;
      if (S0(ai, 1, T + Dd + 1) && S0(ai - 1, 1, T + Dd) && S0(ai + 1, 1, T + Dd)) niches.push({ ai, di: T + Dd, n: [0, -1] });
    }
    for (const side of [-1, 1]) {
      const ai = side < 0 ? a0 - 1 : a0 + Wa;
      for (let di = T + 1; di < T + Dd - 1; di++) {
        if ((di - T) % 2 === 0) continue;
        if (S0(ai + side, 1, di) && S0(ai, 1, di - 1) && S0(ai, 1, di + 1)) niches.push({ ai, di, n: [-side, 0] });
      }
    }
  }
  for (const n of niches) boxes.push([[n.ai, 1, n.di], [n.ai, 1, n.di]]);
  const O = { spot, heaps: [], niches };
  O.carve = () => {
    for (const [p, q] of boxes) {
      const A = spot.block(p[0], p[1], p[2]), B = spot.block(q[0], q[1], q[2]);
      R.carveW([Math.min(A[0], B[0]), Math.min(A[1], B[1]), Math.min(A[2], B[2])], [Math.max(A[0], B[0]), Math.max(A[1], B[1]), Math.max(A[2], B[2])]);
    }
    // the light the room has now that it is open (its floor, in the middle): what the props are lit with
    const f = spot.block(Math.round(aC), -1, Math.round(dC)), b = R.bakeAt(new THREE.Vector3(f[0] + 0.5, f[1] + 1, f[2] + 0.5), new THREE.Vector3(0, 1, 0));
    if (b) amb.copy(b).multiplyScalar(1.1);
    O.amb = amb;
  };
  const amb = new THREE.Vector3(0.09, 0.08, 0.08);
  O.door = P(0, 0, 0); O.front = { x: spot.front.x, z: spot.front.z }; O.mouth = P(0, 0, T);
  const aS = lerp(0, aC, 0.75), dS = T + Math.min(Dd - 2.7, Dd * 0.52);
  O.stop = P(aS, 0, dS);
  // ---- the torch: on the far wall, at eye level, in the middle -----------------------------------------------------
  {
    const wb = spot.block(aT, 1, T + Dd), fW = R.dirW(-s, 0, 0);
    const fx = Math.round(fW[0]), fz = Math.round(fW[2]);
    const cxW = wb[0] + 0.5 + fx * 0.5, czW = wb[2] + 0.5 + fz * 0.5;
    const tg = torchGeometry(cxW, wb[1], czW, fx, fz);
    const tmat = R.torches.length ? R.torches[0].mesh.material : new THREE.MeshBasicMaterial({ map: await tex("k:torch_on"), alphaTest: 0.4, side: THREE.DoubleSide });
    O.torchMesh = R.add(new THREE.Mesh(tg.g, tmat));
    const tl = R.toLocal(new THREE.Vector3(tg.tip[0], tg.tip[1], tg.tip[2]));
    O.torch = [tl.x, tl.y, tl.z];
    O.light = R.ownLight(R.light(0xffa860, 0, 10, 1.4));
    R.at(O.light, tl.x - s * 0.35, tl.y + 0.05, tl.z);
  }
  // ---- the heaps -------------------------------------------------------------------------------------------------
  // Against the walls all round, the middle left clear: two along the far wall, one along each side, one either side
  // of the doorway. A skeleton lying in one is head to the room's middle end, feet to the wall's.
  const slots = [];
  const farD = dFar - 0.95, nearD = dNear + 0.92;
  if (Wa >= 6) { slots.push({ a: aC - 1.6, d: farD, ax: "a", L: 1.45 }); slots.push({ a: aC + 1.6, d: farD, ax: "a", L: 1.45 }); }
  else slots.push({ a: aC + (aC > 0 ? -0.5 : 0.5), d: farD, ax: "a", L: 1.45 });
  const sideD = lerp(nearD + 1.5, farD - 1.0, 0.45);
  slots.push({ a: aMin + 0.9, d: sideD, ax: "d", L: 1.4 }, { a: aMax - 0.9, d: sideD, ax: "d", L: 1.4 });
  for (const sg of [-1, 1]) slots.push({ a: sg * 2.15, d: nearD, ax: "a", L: 1.3, near: true });
  // (clear of the walk in, from the doorway to the stop, and of each other's middles)
  const walkSeg = [P(0, 0, T - 0.5), O.stop];
  const segDist = (p, a, b) => { const dx = b.x - a.x, dz = b.z - a.z, L2 = dx * dx + dz * dz || 1, k = clamp(((p.x - a.x) * dx + (p.z - a.z) * dz) / L2); return Math.hypot(p.x - a.x - dx * k, p.z - a.z - dz * k); };
  for (const sl of slots) {
    let L = sl.L;
    const W = 0.88, Hh = 1.15;
    // keep inside the walls
    const lim = sl.ax === "a" ? Math.min(sl.a - aMin, aMax - sl.a) : Math.min(sl.d - dNear, dFar - sl.d);
    L = Math.min(L, lim - 0.05);
    if (L < 1.1) continue;
    const c = P(sl.a, 0, sl.d);
    const axisR = sl.ax === "a" ? [1, 0] : [0, 1];
    // a skeleton lying in it: along the far and near walls feet to the room's middle line (it sits up facing across
    // the room), along the side walls feet to the doorway's end (it sits up facing the way out)
    let eu = dirL(axisR[0], axisR[1]);
    if (sl.ax === "a" && sl.a < aS) eu = { x: -eu.x, z: -eu.z };
    const ev = { x: -eu.z, z: eu.x };
    // clear of the walk: the footprint's nearest point to the walk line
    let minD = 9;
    for (let k = 0; k < 24; k++) { const an = k / 24 * Math.PI * 2, p = { x: c.x + eu.x * Math.cos(an) * L + ev.x * Math.sin(an) * W, z: c.z + eu.z * Math.cos(an) * L + ev.z * Math.sin(an) * W }; minD = Math.min(minD, segDist(p, walkSeg[0], walkSeg[1])); }
    if (minD < 0.55) continue;
    if (O.heaps.some((h) => Math.hypot(h.c.x - c.x, h.c.z - c.z) < 1.6)) continue;
    O.heaps.push({ c, eu, ev, L, W, H: Hh, near: !!sl.near, far: sl.d === farD, side: sl.ax === "d", fits: L >= 1.3, slump: [], rise: null });
  }
  // ---- materials -----------------------------------------------------------------------------------------------
  const [boneTex] = await Promise.all([tex("k:bone")]);
  const patch = (m) => { if (R.patchBake) R.patchBake(m, { fixed: amb }); return m; };
  const boneMat = patch(new THREE.MeshLambertMaterial({ map: boneTex, alphaTest: 0.3, side: THREE.DoubleSide }));
  const skullMat = patch(new THREE.MeshLambertMaterial({ map: skull || null }));
  const coreAmb = new THREE.Vector3();
  // (the skin may still be loading: wait for it a little, the pile's skull faces are drawn from it)
  for (let i = 0; i < 40 && skull && skull.image && !(skull.image.naturalWidth || skull.image.width); i++) await new Promise((r) => setTimeout(r, 50));
  const pileTex = await pileTexture(boneTex && boneTex.image, skull && skull.image && (skull.image.naturalWidth || skull.image.width) ? skull.image : null);
  const coreMat = new THREE.MeshLambertMaterial({ map: pileTex, color: 0xb8b2a8 });
  if (R.patchBake) R.patchBake(coreMat, { fixed: coreAmb });
  // ---- the pieces on each heap, on the floor, in the niches ------------------------------------------------------
  const pieces = [];
  const upW = new THREE.Vector3(0, 1, 0);
  const vW = (x, y, z) => { const d = R.dirW(x, y, z); return new THREE.Vector3(d[0], d[1], d[2]).normalize(); };
  const basisQ = (X, Y, Z) => new THREE.Quaternion().setFromRotationMatrix(new THREE.Matrix4().makeBasis(X, Y, Z));
  // a bone lying on a surface of normal n (world), turned th about it
  const boneQ = (n, th) => {
    const t0 = Math.abs(n.y) > 0.95 ? new THREE.Vector3(1, 0, 0) : new THREE.Vector3(0, 1, 0).cross(n).normalize();
    const X = t0.clone().applyAxisAngle(n, th), Y = n.clone().cross(X).normalize();
    return basisQ(X, Y, n.clone());
  };
  // a skull standing with its face toward f (world, horizontal), tipped toward the surface normal by k
  const skullQ = (f, n, k = 0.4) => {
    const Y = upW.clone().lerp(n, k).normalize(), Z = f.clone().negate(); Z.sub(Y.clone().multiplyScalar(Z.dot(Y))).normalize();
    const X = Y.clone().cross(Z).normalize();
    return basisQ(X, Y, Z);
  };
  const towardStop = (x, z) => vW(O.stop.x - x, 0, O.stop.z - z);
  O.heaps.forEach((hp, hi) => {
    const area = Math.PI * hp.L * hp.W;
    const nSk = Math.round(area * 3.6), nBo = Math.round(area * 17);
    for (let i = 0; i < nSk + nBo; i++) {
      const kind = i < nSk ? 0 : 1;
      // a point of the footprint (skulls keep off the very edge), its height on the mound and the mound's normal there
      let u, v;
      do { u = rnd() * 2 - 1; v = rnd() * 2 - 1; } while (u * u + v * v > (kind ? 0.97 : 0.8));
      u *= hp.L; v *= hp.W;
      // (a heap's profile: a slope you could pile bones to, not a dome; fuller toward its ends than a paraboloid)
      const q2 = 1 - (u / hp.L) ** 2 - (v / hp.W) ** 2, h = hp.H * PROF(q2), gk = 2 * hp.H * PEXP * Math.pow(Math.max(0.05, q2), PEXP - 1);
      const nl = { u: gk * u / (hp.L * hp.L), y: 1, v: gk * v / (hp.W * hp.W) };
      const nx = hp.eu.x * nl.u + hp.ev.x * nl.v, nz = hp.eu.z * nl.u + hp.ev.z * nl.v;
      const n = vW(nx, nl.y, nz);
      let q, y;
      if (kind === 0) {
        const lx = hp.c.x + hp.eu.x * u + hp.ev.x * v, lz = hp.c.z + hp.eu.z * u + hp.ev.z * v;
        // most look out of the heap toward the middle of the room, where you will stand
        const f = rnd() < 0.85 ? towardStop(lx, lz).applyAxisAngle(upW, (rnd() - 0.5) * 1.3) : vW(Math.cos(rnd() * 6.3), 0, Math.sin(rnd() * 6.3));
        q = skullQ(f, n, 0.12 + rnd() * 0.25); y = h + 0.25 - 0.12;
      } else {
        // most lie along the mound; some stick out of it
        q = boneQ(n, rnd() * Math.PI * 2);
        if (rnd() < 0.3) q.multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), (rnd() - 0.5) * 1.6));
        y = h + 0.01 - (rnd() < 0.3 ? 0.08 : 0);
      }
      pieces.push({ kind, hi, u, v, y, q, rel: null });
    }
  });
  // floor scatter: bones (and a skull or two) over the floor between the heaps
  for (let i = 0; i < 26 + Wa * 2; i++) {
    const a = lerp(aMin + 0.3, aMax - 0.3, rnd()), d = lerp(dNear + 0.3, dFar - 0.3, rnd());
    const p = P(a, 0, d);
    if (O.heaps.some((h) => { const du = (p.x - h.c.x) * h.eu.x + (p.z - h.c.z) * h.eu.z, dv = (p.x - h.c.x) * h.ev.x + (p.z - h.c.z) * h.ev.z; return (du / (h.L + 0.1)) ** 2 + (dv / (h.W + 0.1)) ** 2 < 1; })) continue;
    const kind = rnd() < 0.08 ? 0 : 1;
    const q = kind ? boneQ(upW.clone(), rnd() * 6.3) : skullQ(vW(rnd() - 0.5, 0, rnd() - 0.5), upW, 0);
    pieces.push({ kind, hi: -1, x: p.x, z: p.z, y: kind ? 0.035 : 0.25, q, rel: null });
  }
  // the niches: a skull looking out of each, a bone under it
  for (const nc of niches) {
    const p = P(nc.ai, 1, nc.di), f = vW(s * nc.n[1], 0, nc.n[0]);
    pieces.push({ kind: 0, hi: -1, x: p.x - f.x * 0.12 * 0, z: p.z, y: 1.25, q: skullQ(f, upW, 0), rel: null, fixed: true });
    pieces.push({ kind: 1, hi: -1, x: p.x + f.x * 0.25, z: p.z + f.z * 0.25, y: 1.035, q: boneQ(upW.clone(), rnd() * 6.3), rel: null, fixed: true });
  }
  // ---- meshes ----------------------------------------------------------------------------------------------------
  const skullGeo = (() => { const g = mcBox([-4, -8, -4, 8, 8, 8], [0, 0], 64, 32); g.computeBoundingBox(); const c = new THREE.Vector3(); g.boundingBox.getCenter(c); g.translate(-c.x, -c.y, -c.z); return g; })();
  const nSk = pieces.filter((p) => p.kind === 0).length, nBo = pieces.length - nSk;
  const imS = R.add(new THREE.InstancedMesh(skullGeo, skullMat, Math.max(1, nSk)));
  const imB = R.add(new THREE.InstancedMesh(spriteGeometry(), boneMat, Math.max(1, nBo)));
  for (const im of [imS, imB]) { im.frustumCulled = false; im.instanceMatrix.setUsage(THREE.DynamicDrawUsage); }
  { let a = 0, b = 0; for (const p of pieces) p.slot = p.kind === 0 ? a++ : b++; }
  const SIZE = [0.5, 0.5];
  const cores = O.heaps.map((hp) => {
    const g = new THREE.SphereGeometry(1, 20, 9, 0, Math.PI * 2, 0, Math.PI / 2);
    // the pile's texture at about the pieces' scale (32 texels a metre): round it, and from the top down
    const ps = g.attributes.position, uv = g.attributes.uv;
    // the dome to the heap's profile (1 - r^2 is y^2 on the unit sphere), the texture laid on from above
    for (let i = 0; i < ps.count; i++) { const x = ps.getX(i), y = ps.getY(i), z = ps.getZ(i); ps.setY(i, PROF(y * y)); uv.setXY(i, x * hp.L / 2, z * hp.W / 2); }
    // lumps (outward only, so the core that hides a skeleton is never thinner than the shape the sight lines test)
    const rl = mulberry(31 + O.heaps.indexOf(hp) * 7), bumps = [...Array(9)].map(() => [rl() * 2 - 1, rl() * 0.9, rl() * 2 - 1, 0.25 + rl() * 0.3, 0.04 + rl() * 0.08]);
    for (let i = 0; i < ps.count; i++) {
      const x = ps.getX(i), y = ps.getY(i), z = ps.getZ(i);
      let k = 1;
      for (const [bx, by, bz, br, ba] of bumps) { const d = Math.hypot(x - bx, y - by, z - bz); if (d < br) k += ba * (1 + Math.cos(Math.PI * d / br)) / 2; }
      if (y > 0.02) ps.setXYZ(i, x * k, y * k, z * k);
    }
    g.computeVertexNormals();
    const m = R.add(new THREE.Mesh(g, coreMat));
    m.rotation.order = "YXZ";
    return m;
  });
  // ---- time: slumps, releases, kicks ----------------------------------------------------------------------------
  // A heap slumps as its skeleton comes out (height down, spread out); a piece is 'released' when the body moves
  // through it: it slides off down the mound, over the edge, and skids to a stop on the floor (a function of t).
  const slumpAt = (hp, t) => {
    if (!hp.rise) return [1, 1];
    const k = sstep(hp.rise.hand0, hp.rise.stand1, t);
    return [1 - 0.42 * k, 1 + 0.08 * k];
  };
  const surf = (hp, u, v, t) => { const [hs, sp] = slumpAt(hp, t); const q2 = 1 - (u / (hp.L * sp)) ** 2 - (v / (hp.W * sp)) ** 2; return q2 > 0 ? hp.H * hs * PROF(q2) : 0; };
  const _m = new THREE.Matrix4(), _q = new THREE.Quaternion(), _q2 = new THREE.Quaternion(), _p = new THREE.Vector3(), _s = new THREE.Vector3(), _ax = new THREE.Vector3();
  const flatQ = (p) => p.flat || (p.flat = p.kind ? boneQ(upW.clone(), (p.u || 0) * 7 + (p.v || 0) * 3) : skullQ(vW(Math.cos(p.slot), 0, Math.sin(p.slot)), upW, 0));
  // where a released piece is: [x, y, z local, tumble angle, flat k, spin]
  function released(p, hp, t) {
    const r = p.rel, tau = t - r.t;
    // the path: on the mound (accelerating down it), to the footprint's edge, then on the floor (skidding to a stop)
    const sp = slumpAt(hp, t)[1];
    const eL = r.edge;
    let sd, onFloor = false, tf = 0;
    const te = (-r.v0 + Math.sqrt(r.v0 * r.v0 + 2 * r.acc * eL)) / r.acc, ve = r.v0 + r.acc * te;
    if (tau < te) sd = r.v0 * tau + 0.5 * r.acc * tau * tau;
    else { tf = tau - te; const ts = ve / r.b; const tt = Math.min(tf, ts); sd = eL + ve * tt - 0.5 * r.b * tt * tt; onFloor = true; }
    const u = (r.u0 + r.du * sd) * 1, v = (r.v0p + r.dv * sd) * 1;
    const lx = hp.c.x + (hp.eu.x * u + hp.ev.x * v) * sp, lz = hp.c.z + (hp.eu.z * u + hp.ev.z * v) * sp;
    const thick = p.kind ? 0.035 : 0.25;
    let y = onFloor ? thick : Math.max(thick, surf(hp, u, v, t) + (p.kind ? 0.01 : 0.08));
    const hopK = clamp(tau / 0.35);
    y += r.hop * 4 * hopK * (1 - hopK);
    return { x: lx, y, z: lz, ang: sd * (p.kind ? 2.2 : Math.PI), flat: onFloor ? sstep(0, 0.18, tf) : 0, sd };
  }
  O.pieces = pieces;
  O.heapSurf = surf;
  // the top of the bones at a local point (0 on the floor)
  O.heightAt = (x, z, t = 0) => {
    let h = 0;
    for (const hp of O.heaps) { const du = (x - hp.c.x) * hp.eu.x + (z - hp.c.z) * hp.eu.z, dv = (x - hp.c.x) * hp.ev.x + (z - hp.c.z) * hp.ev.z; h = Math.max(h, surf(hp, du, dv, t)); }
    return h;
  };
  // The skull on top of heap 0 rolls off it toward `to`: tips (0.25 s), down the mound, a knock as it hits the floor,
  // on over the stone, a knock at each quarter turn, slowing to a stop on a face. Returns its timing.
  O.rollSkull = (t0, to, { hi = 0 } = {}) => {
    const hp = O.heaps[hi]; if (!hp) return null;
    const dl = { x: to.x - hp.c.x, z: to.z - hp.c.z }, dn = Math.hypot(dl.x, dl.z) || 1;
    const du = (dl.x * hp.eu.x + dl.z * hp.eu.z) / dn, dv = (dl.x * hp.ev.x + dl.z * hp.ev.z) / dn;
    // the top skull nearest the side it rolls to
    const sc = (p) => p.y + 0.3 * (p.u * du + p.v * dv);
    const cands = pieces.filter((p) => p.hi === hi && p.kind === 0 && !p.rel).sort((a, b) => sc(b) - sc(a));
    const p = cands[0]; if (!p) return null;
    const edge = edgeDist(hp, p.u, p.v, du, dv);
    const floorRun = clamp(dn - Math.hypot(p.u, p.v) - edge - 0.8, 0.4, 1.3);
    p.rel = { t: t0 + 0.25, u0: p.u, v0p: p.v, du, dv, edge, v0: 0.3, acc: 3.4, b: 0, hop: 0, roll: true };
    const te = (-0.3 + Math.sqrt(0.09 + 2 * 3.4 * edge)) / 3.4, ve = 0.3 + 3.4 * te;
    p.rel.b = ve * ve / (2 * floorRun);
    const tStop = p.rel.t + te + ve / p.rel.b;
    p.tip = t0;
    const knocks = [p.rel.t + te];
    const total = edge + floorRun;
    // a knock at each quarter turn (a block tumbling face to face), quieter as it slows
    for (let k = 1; k * 0.5 < total; k++) {
      const sd = k * 0.5; if (sd <= edge) continue;
      const x = sd - edge, tt = (ve - Math.sqrt(Math.max(0, ve * ve - 2 * p.rel.b * x))) / p.rel.b;
      knocks.push(p.rel.t + te + tt);
    }
    O.rolled = p;
    return { tEdge: p.rel.t + te, tStop, knocks: [...new Set(knocks.map((x) => +x.toFixed(3)))].sort((a, b) => a - b), piece: p, to: { x: hp.c.x + (hp.eu.x * (p.u + du * total) + hp.ev.x * (p.v + dv * total)), z: hp.c.z + (hp.eu.z * (p.u + du * total) + hp.ev.z * (p.v + dv * total)) } };
  };
  function edgeDist(hp, u, v, du, dv) {
    // distance along (du, dv) from (u, v) to the footprint ellipse
    const A = (du / hp.L) ** 2 + (dv / hp.W) ** 2, B = 2 * (u * du / (hp.L * hp.L) + v * dv / (hp.W * hp.W)), C = (u / hp.L) ** 2 + (v / hp.W) ** 2 - 1;
    const disc = B * B - 4 * A * C; return disc > 0 ? Math.max(0.05, (-B + Math.sqrt(disc)) / (2 * A)) : 0.05;
  }
  // Floor bones the feet pass over skid away from them.
  O.kicks = (walk, t0, t1) => {
    const out = [];
    for (const p of pieces) {
      if (p.hi !== -1 || p.fixed || p.kind !== 1) continue;
      for (let t = t0; t <= t1; t += 0.05) {
        const w = walk(t), d = Math.hypot(w.x - p.x, w.z - p.z);
        if (d < 0.32) {
          const w2 = walk(t + 0.1), mx = w2.x - w.x, mz = w2.z - w.z, mn = Math.hypot(mx, mz) || 1;
          const side = ((p.x - w.x) * mz - (p.z - w.z) * mx) > 0 ? 1 : -1;
          p.kick = { t, dx: mx / mn * 0.8 + mz / mn * 0.6 * side, dz: mz / mn * 0.8 - mx / mn * 0.6 * side, v0: 1.4, b: 4.5, spin: side * 9 };
          out.push({ t, at: [p.x, 0.05, p.z] });
          break;
        }
      }
    }
    return out;
  };
  // ---- the risers ------------------------------------------------------------------------------------------------
  // A skeleton lying on its back in the heap, head to the heap's room end; then (sch) the heap shivers (shift), a hand
  // comes up out of it (hand0..hand1), it sits up (sit0..sit1), and stands, feet planted, leaning over them
  // (stand0..stand1). pose(t) sets the mob for t and returns { done } once it stands (the scare drives it then).
  const bows = [];   // each riser's bow: shown from .t on (O.update)
  O.bows = bows;
  O.riser = (hi, m, sch) => {
    const hp = O.heaps[hi]; if (!hp) return null;
    hp.rise = sch;
    const yawF = R.yawTo(0, 0, -hp.eu.x, -hp.eu.z);   // facing its feet's way: on its back, its head toward +eu
    const feet = { x: hp.c.x - hp.eu.x * 1.1, z: hp.c.z - hp.eu.z * 1.1 };
    const Pp = m.parts, legs = [Pp.rightLeg, Pp.leftLeg].filter(Boolean);
    const _a = new THREE.Vector3(), _b = new THREE.Vector3(), _w = new THREE.Vector3();
    const anchor = (pts) => { m.pivot.updateMatrixWorld(true); _a.set(0, 0, 0); for (const [g, y] of pts) _a.add(g.localToWorld(_b.set(0, y, 0))); return _a.multiplyScalar(1 / pts.length); };
    const head = (x, y) => { for (const g of [Pp.head, Pp.headwear]) if (g) mcRotP(g, x, y, 0); };
    const set = (th, lam, armR, armL, hx, hy) => {
      m.anim(0, 0, { walk: 0 });
      for (const g of legs) mcRotP(g, th - lam, 0, 0);
      if (Pp.rightArm) mcRotP(Pp.rightArm, armR[0], armR[1] || 0, armR[2] || 0);
      if (Pp.leftArm) mcRotP(Pp.leftArm, armL[0], armL[1] || 0, armL[2] || 0);
      head(hx, hy);
      R.place(m, feet.x, 0, feet.z, yawF, th);
    };
    // the hip, lying; the feet, sat up
    // (its skull's back a little into the floor, as a skull would settle: the rest of it as deep in the bones as it goes)
    set(Math.PI / 2, Math.PI / 2, [0], [0], 0, 0); R.L(feet.x, 0.18, feet.z, m.pivot.position);
    const hipW = anchor(legs.map((g) => [g, 0])).clone();
    // the clawing arm is the one on the room's side (the side you stand on): it reaches up and out through the heap's
    // flank, where the bones are shallow, so the hand clears them (straight up it stays under the crest)
    const sideOf = (g) => { if (!g) return 1e9; m.pivot.updateMatrixWorld(true); const q = R.toLocal(g.localToWorld(_b.set(0, 0, 0))); return Math.hypot(q.x - O.stop.x, q.z - O.stop.z); };
    const clawRight = sideOf(Pp.rightArm) <= sideOf(Pp.leftArm);
    // its bow lies in the bones: the hand comes up empty, and the bow is in it from the moment the hand is back down in
    // the heap, wholly inside it (found below), so it comes up out of the bones with it and never pops in
    const bow = { objs: Pp.rightArm ? Pp.rightArm.children.filter((c) => !c.isMesh) : [], t: sch.stand0, best: -1, of: 0 };
    if (bow.objs.length) bows.push(bow);
    const bowMeshes = []; for (const o of bow.objs) o.traverse((x) => { if (x.isMesh) { if (!x.geometry.boundingBox) x.geometry.computeBoundingBox(); bowMeshes.push(x); } });
    bow.of = bowMeshes.length * 8;
    const bowInside = (t) => {
      m.pivot.updateMatrixWorld(true); let n = 0;
      for (const x of bowMeshes) {
        const bb = x.geometry.boundingBox;
        for (let c = 0; c < 8; c++) {
          const l = R.toLocal(_b.set(c & 1 ? bb.max.x : bb.min.x, c & 2 ? bb.max.y : bb.min.y, c & 4 ? bb.max.z : bb.min.z).applyMatrix4(x.matrixWorld));
          const du = (l.x - hp.c.x) * hp.eu.x + (l.z - hp.c.z) * hp.eu.z, dv = (l.x - hp.c.x) * hp.ev.x + (l.z - hp.c.z) * hp.ev.z;
          if (l.y < 0 || l.y < surf(hp, du, dv, t) - 0.04) n++;   // under the floor or in the bones
        }
      }
      return n;
    };
    const camYaw = (t) => 0;
    let footW = null;
    const pose = (t, look = null) => {
      // look: local {x, y, z} it turns its head to once it is up
      const kh = sstep(sch.hand0, sch.hand1, t), ks = sstep(sch.sit0, sch.sit1, t), kt = sstep(sch.stand0, sch.stand1, t);
      const shiver = sch.shift != null ? Math.sin((t - sch.shift) * 40) * 0.02 * pulse1(t, sch.shift, 0.7) : 0;
      // the head toward what it looks at (look: local point), relative to its body, as far as a neck turns
      let hy = 0, up = 0;
      const kLook = look ? sstep(sch.sit0 + 0.35, sch.sit1 + 0.25, t) : 0;
      if (kLook > 0) {
        const lw = R.L(look.x, look.y, look.z, _w), fw = R.L(feet.x, 1.5, feet.z, _b);
        const yawTo = Math.atan2(-(lw.x - fw.x), -(lw.z - fw.z)), bodyYaw = R.yaw0 + yawF;
        hy = -clamp(wrapA(yawTo - bodyYaw), -1.15, 1.15) * kLook;
        up = clamp(Math.atan2(look.y - 1.5, Math.hypot(look.x - feet.x, look.z - feet.z)), -0.7, 0.6) * kLook;
      }
      if (t < sch.stand0) {
        const lift = 0.14 * kh;
        const th = lerp(Math.PI / 2 - lift, 0, easeInOut(ks)) + shiver;
        // the hand: the arm on the room's side comes up and out through the bones, clawing (ModelBiped z: + is out for
        // the right arm, - for the left); as it sits up both arms go to the floor
        const kc = easeOut3(kh), claw = Math.sin(t * 9) * 0.12 * kh * (1 - ks);
        const armC = [lerp(-0.95 * kc + claw, 0.35, ks), 0, (clawRight ? 1 : -1) * lerp(1.45 * kc + claw * 0.6, 0, ks)];
        const armO = [lerp(0, 0.25, ks), 0, 0];
        set(th, Math.PI / 2, clawRight ? armC : armO, clawRight ? armO : armC, 0.35 * Math.sin(Math.PI * ks) - up * ks, hy);
        const a = anchor(legs.map((g) => [g, 0]));
        m.pivot.position.add(_w.copy(hipW).sub(a));
        footW = null;
      } else {
        if (!footW) { const t0 = sch.stand0; const th0 = 0; set(th0, Math.PI / 2, [0.35], [0.25], 0, 0); const a = anchor(legs.map((g) => [g, 0])); m.pivot.position.add(_w.copy(hipW).sub(a)); footW = anchor(legs.map((g) => [g, -0.75])).clone(); }
        const lam = (Math.PI / 2) * (1 - easeInOut(kt));
        const th = -0.62 * Math.sin(Math.PI * Math.min(1, kt * 1.08)) * (kt < 1 ? 1 : 0);
        const arm = lerp(0.35, 0, kt) + th;
        set(th, lam, [arm], [arm * 0.9], th - up, hy);
        const a = anchor(legs.map((g) => [g, -0.75]));
        _w.set(footW.x, lerp(footW.y, R.O.y, sstep(0, 0.6, kt)), footW.z);
        m.pivot.position.add(_w.sub(a));
      }
      return { done: t >= sch.stand1, feet: R.toLocal(m.pivot.position), yaw: yawF };
    };
    // release each piece of this heap the first moment the body passes through it (sampled now)
    const segs = (out) => {
      m.pivot.updateMatrixWorld(true);
      const pt = (g, x, y, z) => (g ? g.localToWorld(new THREE.Vector3(x, y, z)) : null);
      out.length = 0;
      if (Pp.head) out.push([pt(Pp.head, 0, 0.05, 0), pt(Pp.head, 0, 0.45, 0), 0.32]);
      if (Pp.body) out.push([pt(Pp.body, 0, -0.05, 0), pt(Pp.body, 0, -0.7, 0), 0.3]);
      for (const g of [Pp.rightArm, Pp.leftArm]) if (g) out.push([pt(g, 0, 0, 0), pt(g, 0, -0.62, 0), 0.14]);
      for (const g of legs) out.push([pt(g, 0, 0, 0), pt(g, 0, -0.72, 0), 0.14]);
      return out;
    };
    const mine = pieces.filter((p) => p.hi === hi && !p.rel);
    const S1 = [], S0 = [], cl = new THREE.Vector3(), seg = new THREE.Vector3();
    let tPrev = null;
    for (let t = sch.hand0; t <= sch.stand1 + 0.2; t += 0.05) {
      pose(t); segs(S1);
      if (bowMeshes.length && t >= sch.hand1 && t <= sch.stand0 && bow.best < bowMeshes.length * 8) { const n = bowInside(t); if (n > bow.best) { bow.best = n; bow.t = t; } }
      for (const p of mine) {
        if (p.rel) continue;
        const [hs, sp] = slumpAt(hp, t);
        const lx = hp.c.x + (hp.eu.x * p.u + hp.ev.x * p.v) * sp, lz = hp.c.z + (hp.eu.z * p.u + hp.ev.z * p.v) * sp;
        const w = R.L(lx, p.y * hs, lz, _w);
        for (let si = 0; si < S1.length; si++) {
          const [a, b, rad] = S1[si];
          seg.subVectors(b, a); const k = clamp(cl.subVectors(w, a).dot(seg) / Math.max(1e-6, seg.lengthSq()));
          cl.copy(a).addScaledVector(seg, k);
          if (cl.distanceTo(w) < rad + 0.1) {
            // pushed away from the bone that came through it, down the mound
            const away = R.toLocal(new THREE.Vector3(w.x - cl.x + R.O.x, 0, w.z - cl.z + R.O.z));
            let du = away.x * hp.eu.x + away.z * hp.eu.z, dv = away.x * hp.ev.x + away.z * hp.ev.z;
            const out = p.u * 0.3 / hp.L, outv = p.v / hp.W;
            du += out * 0.4; dv += outv * 0.6;
            const n = Math.hypot(du, dv) || 1; du /= n; dv /= n;
            let speed = 0.5;
            if (S0.length === S1.length) speed = clamp(S1[si][1].distanceTo(S0[si][1]) / 0.05 * 0.6, 0.2, 1.6);
            p.rel = { t: t + rnd() * 0.06, u0: p.u, v0p: p.v, du, dv, edge: edgeDist(hp, p.u, p.v, du, dv), v0: speed, acc: 2.4 + rnd(), b: 4 + rnd() * 2, hop: clamp(speed * 0.12, 0, 0.18) * (cl.y > w.y ? 0.3 : 1) };
            break;
          }
        }
      }
      S0.length = 0; for (const x of S1) S0.push([x[0].clone(), x[1].clone(), x[2]]);
      tPrev = t;
    }
    void tPrev; void camYaw;
    return pose;
  };
  // where a piece is at t: local x, y, z and its world orientation
  const placeOf = (p, t, out = {}) => {
    let x, y, z, q = p.q;
    if (p.hi >= 0) {
      const hp = O.heaps[p.hi];
      if (p.rel && t >= p.rel.t) {
        const r = released(p, hp, t);
        x = r.x; y = r.y; z = r.z;
        const dW = R.dirW(hp.eu.x * p.rel.du + hp.ev.x * p.rel.dv, 0, hp.eu.z * p.rel.du + hp.ev.z * p.rel.dv);
        _ax.set(dW[2], 0, -dW[0]).normalize();
        if (p.rel.roll) {
          // a block tumbling face to face: its middle rises over each edge
          const a = r.ang, ph = ((a % (Math.PI / 2)) + Math.PI / 2) % (Math.PI / 2);
          y += 0.25 * (Math.SQRT2 * Math.cos(ph - Math.PI / 4) - 1);
          _q.setFromAxisAngle(_ax, a); q = _q2.copy(_q).multiply(p.q);
        } else {
          _q.setFromAxisAngle(_ax, r.ang * (1 - r.flat * 0.0)); q = _q2.copy(_q).multiply(p.q);
          if (r.flat > 0) q.slerp(flatQ(p), r.flat);
        }
      } else {
        const [hs, sp] = slumpAt(hp, t);
        let u = p.u, v = p.v, yy = p.y * hs;
        if (p.tip != null && t > p.tip) { const k = sstep(p.tip, p.tip + 0.25, t); yy += 0.04 * k; }
        if (hp.rise && hp.rise.shift != null) { const k = pulse1(t, hp.rise.shift, 0.8); u += Math.sin(p.slot * 3.1 + t * 31) * 0.025 * k; yy += Math.abs(Math.sin(p.slot * 1.7 + t * 23)) * 0.03 * k; }
        x = hp.c.x + (hp.eu.x * u + hp.ev.x * v) * sp; z = hp.c.z + (hp.eu.z * u + hp.ev.z * v) * sp; y = yy;
      }
    } else {
      x = p.x; y = p.y; z = p.z;
      if (p.kick && t > p.kick.t) {
        const tau = t - p.kick.t, ts = p.kick.v0 / p.kick.b, tt = Math.min(tau, ts), sd = p.kick.v0 * tt - 0.5 * p.kick.b * tt * tt;
        x += p.kick.dx * sd; z += p.kick.dz * sd; y += 0.06 * Math.sin(Math.min(1, tau / 0.12) * Math.PI);
        _q.setFromAxisAngle(upW, p.kick.spin * (sd / p.kick.v0)); q = _q2.copy(_q).multiply(p.q);
      }
    }
  out.x = x; out.y = y; out.z = z; out.q = q; return out;
  };
  const _pl = {};
  O.pieceAt = (p, t) => { if (!p) return null; const r = placeOf(p, t, {}); return { x: r.x, y: r.y, z: r.z }; };
  // ---- the frame -------------------------------------------------------------------------------------------------
  O.update = (t) => {
    O.heaps.forEach((hp, i) => {
      const [hs, sp] = slumpAt(hp, t), m = cores[i];
      R.at(m, hp.c.x, 0, hp.c.z);
      // the sphere's x along eu: scale (L, H, W) in the heap's frame
      const ang = Math.atan2(R.dirW(hp.eu.x, 0, hp.eu.z)[2], R.dirW(hp.eu.x, 0, hp.eu.z)[0]);
      m.rotation.set(0, -ang, 0);
      m.scale.set(hp.L * sp * 0.98, Math.max(0.02, hp.H * hs * 0.97), hp.W * sp * 0.98);
    });
    for (const p of pieces) {
      const im = p.kind === 0 ? imS : imB;
      const { x, y, z, q } = placeOf(p, t, _pl);
      R.L(x, y, z, _p);
      _s.setScalar(SIZE[p.kind]);
      _m.compose(_p, q, _s);
      im.setMatrixAt(p.slot, _m);
    }
    imS.count = nSk; imB.count = nBo;
    imS.instanceMatrix.needsUpdate = true; imB.instanceMatrix.needsUpdate = true;
    coreAmb.copy(amb).multiplyScalar(0.8);
    for (const b of bows) for (const o of b.objs) o.visible = t >= b.t;
    O.tNow = t;
  };
  O.solid = (w) => {
    const l = R.toLocal(w);
    for (let i = 0; i < O.heaps.length; i++) {
      const hp = O.heaps[i], [hs, sp] = slumpAt(hp, O.tNow ?? 0);
      const du = (l.x - hp.c.x) * hp.eu.x + (l.z - hp.c.z) * hp.eu.z, dv = (l.x - hp.c.x) * hp.ev.x + (l.z - hp.c.z) * hp.ev.z;
      if (l.y < 0) continue;
      if (l.y < hp.H * hs * 0.97 * PROF(1 - (du / (hp.L * sp * 0.98)) ** 2 - (dv / (hp.W * sp * 0.98)) ** 2)) return true;
    }
    return false;
  };
  return O;
}
// The inside of a heap, as a texture for its core: bone items (the 16 x 16 sprite, turned by quarter turns and flipped,
// so the pixels stay square) piled over a dark ground, the deeper ones darker, and a few skull faces (the skin's head
// front, 8 x 8) among them. 64 x 64, nearest, repeating.
async function pileTexture(bone, skin) {
  const c = document.createElement("canvas"); c.width = c.height = 64;
  const x = c.getContext("2d"); x.imageSmoothingEnabled = false;
  x.fillStyle = "#231e19"; x.fillRect(0, 0, 64, 64);
  const r = mulberry(77);
  const put = (img, sx, sy, sw, sh, n, dark, size) => {
    for (let i = 0; i < n; i++) {
      const px = Math.floor(r() * 64), py = Math.floor(r() * 64), rot = Math.floor(r() * 4), fl = r() < 0.5;
      for (const [ox, oy] of [[0, 0], [-64, 0], [0, -64], [-64, -64]]) {
        x.save(); x.translate(px + ox + size / 2, py + oy + size / 2); x.rotate(rot * Math.PI / 2); if (fl) x.scale(-1, 1);
        x.filter = `brightness(${dark + (1 - dark) * (i / n)})`;
        x.drawImage(img, sx, sy, sw, sh, -size / 2, -size / 2, size, size); x.restore();
      }
    }
  };
  if (bone) put(bone, 0, 0, bone.width, bone.height, 80, 0.12, 16);
  if (skin) { const k = skin.width / 64; put(skin, 8 * k, 8 * k, 8 * k, 8 * k, 10, 0.25, 8); }
  if (bone) put(bone, 0, 0, bone.width, bone.height, 20, 0.35, 16);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace; t.magFilter = t.minFilter = THREE.NearestFilter; t.generateMipmaps = false;
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  return t;
}
const PEXP = 0.8, PROF = (q2) => (q2 > 0 ? Math.pow(q2, PEXP) : 0);
const easeInOut = (k) => k * k * (3 - 2 * k);
const easeOut3 = (k) => 1 - Math.pow(1 - clamp(k), 3);
const pulse1 = (t, t0, len) => (t < t0 || t > t0 + len ? 0 : Math.sin((t - t0) / len * Math.PI));
const wrapA = (a) => Math.atan2(Math.sin(a), Math.cos(a));
const mcRotP = (g, x, y, z) => { if (g) g.rotation.set(-x, -y, z, "ZYX"); };
