// The Krypt's world, built as you walk: the plan (plan.js) says which legs exist and where; the world turns the legs
// near the walker into blocks, one chunk at a time. Each 48 by 48 chunk is cut from a window (the chunk and a margin of
// 16 blocks) by running the same deterministic carve, dress and bake over every leg that reaches the window, then keeping
// only what lies inside the chunk: its faces, its torches and decor, its lights. Two chunks that share a margin agree on
// every block because each leg's blocks depend on the leg alone. Chunks far behind are disposed, so memory and draw calls
// stay flat from the first grave to the ten thousandth.
import * as THREE from "three";
import {
  T_AIR, T_STONE, T_COBBLE, T_BRICK, T_OBS, T_BEDROCK, T_WATER, T_NBRICK, T_NETHER, T_LAVA, T_GRAVEL_FLOOR, T_WALL,
  T_GLOW, TEX_OF, FRONT, EMISSIVE, BLOCK_NAME, isOpen, wallType, ih, T_BRICK_MOSSY
} from "./blocks.js";
import { legMap, legLocal, legCell, legYaw, legDir, floorTop, PASSAGE_LEN, SLOT_STEP } from "./geom.js";
import { makePlan, SEED, legProfile } from "./plan.js";
import { KINDS, makeCtx } from "./kinds.js";

export { SLOT_STEP, makePlan, SEED, KINDS };
export { legMap, legLocal, legYaw, legDir };
export const CH = 48, MARGIN = 16;

// Where the stone, the statue and the camera stand for a slot.
export function slotFrame(plan, s) {
  const leg = plan.legs[s.leg];
  const b = s.lvc + 0.5, hw = leg.hw, sd = s.side;
  const at = (a, bb) => { const [x, z] = legMap(leg, a, bb); return new THREE.Vector3(x, leg.y0, z); };
  const ctr = at(0, b);
  const stone = at(sd * (hw + 1.2), b);
  const out = new THREE.Vector3().subVectors(stone, ctr).setY(0).normalize();
  return {
    leg, centre: ctr, stone, out,
    statue: at(sd * (hw + 1.55), b + 0.95),
    angel: at(sd * (hw + 1.55), b - 0.95),
    yaw: sd * Math.PI / 2 + legYaw(leg),
    camAt: (d, bb = b - 0.45) => at(sd * (hw + 1.2 - d), bb)
  };
}

// The box (world x/z) that a leg's carved hall, alcoves and passages occupy: what decides whether a chunk has anything in it.
export function legBox(leg) {
  if (leg._box) return leg._box;
  const side = leg.hw + 3 + (leg.passages.some((p) => p.ok) ? Math.max(...leg.passages.filter((p) => p.ok).map((p) => (p.len || PASSAGE_LEN) + 2)) : 0);
  let x0 = 1e9, x1 = -1e9, z0 = 1e9, z1 = -1e9;
  for (const a of [-side, side]) for (const b of [leg.cs - 2, leg.ce + 2]) { const [x, z] = legMap(leg, a, b); x0 = Math.min(x0, x); x1 = Math.max(x1, x); z0 = Math.min(z0, z); z1 = Math.max(z1, z); }
  return (leg._box = { x0, x1, z0, z1 });
}

// ---- one window of blocks ----------------------------------------------------------------------------------------
export function buildWindow(plan, ci, ck) {
  const bb = { x0: ci * CH, z0: ck * CH, x1: (ci + 1) * CH, z1: (ck + 1) * CH };
  const wx0 = bb.x0 - MARGIN, wz0 = bb.z0 - MARGIN, wx1 = bb.x1 + MARGIN, wz1 = bb.z1 + MARGIN;
  const legs = plan.legsIn(wx0, wz0, wx1, wz1);
  if (!legs.length) return null;
  let ymin = 1e9, ymax = -1e9;
  for (const leg of legs) { ymin = Math.min(ymin, Math.min(leg.y0, leg.yEnd) - leg.kd.below); ymax = Math.max(ymax, leg.y0 + leg.ht + 9); }
  const a = { i0: wx0, NI: wx1 - wx0, k0: wz0, NK: wz1 - wz0, j0: ymin - 2, NJ: ymax - ymin + 3, plan, bb, legs };
  a.g = new Uint8Array(a.NK * a.NJ * a.NI).fill(T_WALL);
  a.st = new Uint8Array(a.g.length);
  const inb = (i, j, k) => i >= a.i0 && i < a.i0 + a.NI && j >= a.j0 && j < a.j0 + a.NJ && k >= a.k0 && k < a.k0 + a.NK;
  const idx = (i, j, k) => ((k - a.k0) * a.NJ + (j - a.j0)) * a.NI + (i - a.i0);
  const get = (i, j, k) => (inb(i, j, k) ? a.g[idx(i, j, k)] : T_BEDROCK);
  const set = (i, j, k, t) => { if (inb(i, j, k)) a.g[idx(i, j, k)] = t; };
  a.get = get; a.set = set; a.inb = inb; a.idx = idx;
  a.solid = (i, j, k) => !isOpen(get(i, j, k));
  a.torches = []; a.decor = []; a.sources = []; a.emit = []; a.spots = { water: [], lava: [], fire: [], drip: [] };
  a.lavaRects = []; a.waterRects = []; a.holes = [];
  const decor = (o) => a.decor.push(o);
  const L = (leg, lu, lv, j, t) => { const [i, k] = legCell(leg, lu, lv); set(i, j, k, t); };
  const LG = (leg, lu, lv, j) => { const [i, k] = legCell(leg, lu, lv); return get(i, j, k); };
  const W3 = (leg, aa, bb2, y) => { const [x, z] = legMap(leg, aa, bb2); return [x, y, z]; };
  const dirw = (leg, fa, fb) => { const p = legMap(leg, fa, fb), q = legMap(leg, 0, 0); return [p[0] - q[0], p[1] - q[1]]; };
  // The rows of a leg that touch this window (leg-local b), widened by pad.
  const bRange = (leg, pad) => {
    let lo = 1e9, hi = -1e9;
    for (const [x, z] of [[wx0, wz0], [wx1, wz0], [wx0, wz1], [wx1, wz1]]) { const b = legLocal(leg, x, z)[1]; lo = Math.min(lo, b); hi = Math.max(hi, b); }
    return [Math.max(leg.cs - pad, Math.floor(lo) - 1), Math.min(leg.ce + pad, Math.ceil(hi) + 1)];
  };

  function pushTorch(i, j, k, fx, fz, opts = {}) {
    const cx = i + 0.5 + fx * 0.5, cz = k + 0.5 + fz * 0.5;
    const tip = [cx + fx * 0.35, j + (fx || fz ? 0.845 : 0.66), cz + fz * 0.35];   // a standing torch (no facing) is lower
    a.torches.push({ i, j, k, fx, fz, x: tip[0], y: tip[1], z: tip[2], cx, cz, ...opts });
    const s = opts.I != null ? opts.I : 3.4;
    a.sources.push({ x: tip[0] + fx * 0.2, y: tip[1] + 0.15, z: tip[2] + fz * 0.2, c: opts.c || [1.0, 0.56, 0.24], I: s, R: 12, dyn: true });
    a.emit.push({ k: "torch", x: tip[0], y: tip[1] + 0.02, z: tip[2] });
  }
  function torchAt(leg, lu, lv, j, faceA, opts = {}) {
    const [fx, fz] = dirw(leg, faceA, 0);
    const [i, k] = legCell(leg, lu, lv);
    if (!a.solid(i, j, k) || a.solid(i + fx, j, k + fz)) return false;
    pushTorch(i, j, k, fx, fz, opts); return true;
  }
  function torchAtB(leg, lu, lv, j, faceB, opts = {}) {
    const [fx, fz] = dirw(leg, 0, faceB);
    const [i, k] = legCell(leg, lu, lv);
    if (!a.solid(i, j, k) || a.solid(i + fx, j, k + fz)) return false;
    pushTorch(i, j, k, fx, fz, opts); return true;
  }

  // 1. The style of the stone around every leg (the first leg to claim a cell keeps it), then every leg's hall.
  for (const leg of legs) {
    const { hw, y0 } = leg, kd = leg.kd;
    const lo = Math.min(y0, leg.yEnd) - kd.below, hi = y0 + leg.ht + 3;
    const [b0, b1] = bRange(leg, 4);
    const mg = kd.margin || 4;
    for (let lv = b0; lv < b1; lv++) for (let lu = -hw - mg; lu < hw + mg; lu++) {
      const [i, k] = legCell(leg, lu, lv);
      for (let j = lo; j <= hi; j++) if (inb(i, j, k) && !a.st[idx(i, j, k)]) a.st[idx(i, j, k)] = leg.style;
    }
  }
  for (const leg of legs) {
    const { hw, ht, y0 } = leg, kd = leg.kd, gp = leg.gap;
    leg.used = { 1: new Set(), "-1": new Set() }; leg.lavaCells = [];
    const [b0, b1] = bRange(leg, 0);
    for (let lv = b0; lv < b1; lv++) {
      const yf = floorTop(leg, lv);
      const inGap = gp && lv >= gp.b && lv < gp.b + gp.w;
      for (let lu = -hw; lu < hw; lu++) {
        const hv = ih(lu, lv, leg.rid, 3), centre = lu === -1 || lu === 0;
        const spec = kd.floor ? kd.floor({ leg, lu, lv, yf, hv, centre }) : T_BRICK;
        let from = yf, cells, lava = false;
        if (typeof spec === "number") cells = [[yf - 1, spec]]; else { from = spec.from != null ? spec.from : yf; cells = spec.cells; lava = !!spec.lava; }
        if (inGap) { from = y0 - 2; cells = gp.kind === "lava" ? [[y0 - 4, T_OBS], [y0 - 3, T_LAVA]] : [[y0 - 4, T_GRAVEL_FLOOR], [y0 - 3, T_WATER]]; lava = false; }
        for (let j = from; j < yf + ht; j++) L(leg, lu, lv, j, T_AIR);
        for (const [y, t] of cells) L(leg, lu, lv, y, t);
        if (lava) leg.lavaCells.push([lu, lv]);
      }
    }
  }
  // Alcoves: a pocket two cells deep with a solid back, framed by two pillars and a lintel.
  for (const leg of legs) {
    const { hw, y0 } = leg, kd = leg.kd;
    const pb = kd.alcoveBase ? kd.alcoveBase(leg) : y0, pt = kd.alcoveTile || 0, pp = kd.alcovePil || pt, pl = kd.alcoveLin || pt;
    for (const s of leg.slots) {
      const sd = s.side, inner = sd > 0 ? [hw, hw + 1] : [-hw - 1, -hw - 2];
      const pil = sd > 0 ? hw - 1 : -hw;
      for (let lv = s.lvc - 1; lv <= s.lvc + 1; lv++) for (let j = y0; j <= y0 + 3; j++) { L(leg, inner[0], lv, j, T_AIR); L(leg, inner[1], lv, j, T_AIR); }
      for (const lv of [s.lvc - 2, s.lvc + 2]) for (let j = pb; j <= y0 + 2; j++) L(leg, pil, lv, j, pp || (j === y0 ? T_BRICK_MOSSY : T_BRICK));
      for (let lv = s.lvc - 2; lv <= s.lvc + 2; lv++) L(leg, pil, lv, y0 + 3, pl || T_BRICK);
      for (let lv = s.lvc - 3; lv <= s.lvc + 3; lv++) leg.used[sd].add(lv);
    }
  }
  // 2. Side passages (the plan decided which fit): a narrow corridor off the wall, or a wider room.
  for (const leg of legs) {
    const kd = leg.kd;
    for (const p of leg.passages) {
      if (!p.ok) continue;
      const { side, lv } = p, hw = leg.hw, y0 = leg.y0, pw = p.w || 2, ph = p.ht || 3;
      const wlo = p.w ? -Math.floor((pw - 2) / 2) : 0;
      for (let q = 0; q < p.len; q++) {
        const lu = side > 0 ? hw + q : -hw - 1 - q;
        for (let w = wlo; w < wlo + pw; w++) {
          for (let j = y0; j < y0 + ph; j++) L(leg, lu, lv + w, j, T_AIR);
          L(leg, lu, lv + w, y0 - 1, kd.passFloor || T_COBBLE);
        }
      }
      for (let q = -1; q <= p.len + 1; q++) for (let w = wlo - 2; w < wlo + pw + 2; w++) {
        const lu = side > 0 ? hw + q : -hw - 1 - q;
        const [ci2, ck2] = legCell(leg, lu, lv + w);
        for (let j = y0 - 3; j <= y0 + ph + 2; j++) if (inb(ci2, j, ck2)) { const ix = idx(ci2, j, ck2); if (a.st[ix] === 0) a.st[ix] = leg.style; }
      }
      const luEnd = side > 0 ? hw + p.len : -hw - 1 - p.len;
      if (!p.w) {
        torchAt(leg, luEnd, lv, y0 + 1, -side, { I: 2.6 });
        const [ex, , ez] = W3(leg, side * (hw + p.len - 0.5), lv + 1, y0);
        decor({ t: "web", x: ex, y: y0 + 2.5, z: ez, ry: Math.PI / 2 + legYaw(leg), w: 1.1 });
      }
    }
  }
  // 3. Holes in the ceiling: the violet sky cracks.
  for (const leg of legs) for (const hb of leg.holesAt) {
    const yTop = leg.y0 + leg.ht;
    for (let lv = hb - 1; lv <= hb + 1; lv++) for (let lu = -1; lu <= 1; lu++) for (let j = yTop; j <= a.j0 + a.NJ - 1; j++) L(leg, lu, lv, j, T_AIR);
    const [x, , z] = W3(leg, 0.5, hb + 0.5, 0);
    a.holes.push({ x, z, y: yTop, leg: leg.idx, hb });
    for (let q = 0; q < 3; q++) a.sources.push({ x: x + (q - 1) * 0.9, y: yTop + 0.6, z: z + (q % 2 ? 0.6 : -0.6), c: [0.55, 0.42, 0.95], I: 3.4, R: 12, sky: true });
  }
  // 4. Set dressing, leg by leg.
  const H = { L, LG, W3, dirw, torchAt, torchAtB, pushTorch, decor, legCell, set, get };
  for (const leg of legs) leg.kd.dress && leg.kd.dress(makeCtx(a, plan, leg, H));
  // 5. A torch for each stone: on the corridor face of the rear pillar. Fewer in the cold entrance and the ossuary.
  for (const leg of legs) for (const s of leg.slots) {
    const { hw, y0 } = leg, kd = leg.kd;
    if (s.i >= plan.count) continue;
    torchAtB(leg, s.side > 0 ? hw + 1 : -hw - 2, s.lvc + 2, y0 + 2, -1, { I: 2.4 });
    if (s.i % kd.torchEvery && !(leg.idx === 0 && s.i === 0)) continue;
    const pil = s.side > 0 ? hw - 1 : -hw;
    if (!torchAt(leg, pil, s.lvc + 2, y0 + 2, -s.side, { I: kd.torchI })) torchAt(leg, pil, s.lvc - 2, y0 + 2, -s.side, { I: kd.torchI });
  }
  // Lava: sources and planes over the open lava cells of chasm and fortress floors, and over every gap.
  for (const leg of legs) {
    const kd = leg.kd;
    if (leg.lavaCells.length && kd.lavaDepth != null) {
      const yL = leg.y0 - kd.lavaDepth + 0.9;
      for (const [lu, lv] of leg.lavaCells) if (lu % 3 === 0 && lv % 3 === 0) { const [x, , z] = W3(leg, lu + 0.5, lv + 0.5, 0); a.sources.push({ x, y: yL + 0.6, z, c: [1.0, 0.36, 0.08], I: kd.lavaI || 9, R: 14, lava: true, dyn: true }); }
      const [xa, , za] = W3(leg, -leg.hw, leg.cs, 0), [xb, , zb] = W3(leg, leg.hw, leg.ce, 0);
      a.lavaRects.push({ x0: Math.min(xa, xb), x1: Math.max(xa, xb), z0: Math.min(za, zb), z1: Math.max(za, zb), y: yL - 0.15 });
    }
    if (leg.gap) {
      const g = leg.gap, [xa, , za] = W3(leg, -leg.hw, g.b, 0), [xb, , zb] = W3(leg, leg.hw, g.b + g.w, 0);
      const r = { x0: Math.min(xa, xb), x1: Math.max(xa, xb), z0: Math.min(za, zb), z1: Math.max(za, zb) };
      if (g.kind === "lava") {
        a.lavaRects.push({ ...r, y: leg.y0 - 2.12 });
        for (let lu = -leg.hw + 1; lu < leg.hw; lu += 3) { const [x, , z] = W3(leg, lu + 0.5, g.b + g.w / 2, 0); a.sources.push({ x, y: leg.y0 - 1.4, z, c: [1.0, 0.36, 0.08], I: 7, R: 12, lava: true, dyn: true }); a.emit.push({ k: "lava", x, y: leg.y0 - 2.1, z }); }
        a.spots.lava.push(W3(leg, 0, g.b + g.w / 2, leg.y0 - 2));
      } else { a.waterRects.push({ ...r, y: leg.y0 - 2.25 }); for (let lu = -leg.hw + 1; lu < leg.hw; lu += 3) { const [x, , z] = W3(leg, lu + 0.5, g.b + g.w / 2, 0); a.sources.push({ x, y: leg.y0 - 1.6, z, c: [0.3, 0.6, 0.8], I: 3.4, R: 9 }); } }
    }
  }
  // What this chunk owns: everything whose position lies inside its box. The bake uses every source in the window.
  const inside = (x, z) => x >= bb.x0 && x < bb.x1 && z >= bb.z0 && z < bb.z1;
  const clip = (r) => { const q = { ...r, x0: Math.max(r.x0, bb.x0), x1: Math.min(r.x1, bb.x1), z0: Math.max(r.z0, bb.z0), z1: Math.min(r.z1, bb.z1) }; return q.x1 > q.x0 && q.z1 > q.z0 ? q : null; };
  a.own = {
    torches: a.torches.filter((t) => inside(t.i + 0.5, t.k + 0.5)),
    decor: a.decor.filter((d) => inside(d.x, d.z)),
    emit: a.emit.filter((e) => inside(e.x, e.z)),
    dyn: a.sources.filter((s) => s.dyn && inside(s.x, s.z)),
    spots: { fire: a.spots.fire.filter((p) => inside(p[0], p[2])), lava: a.spots.lava.filter((p) => inside(p[0], p[2])), drip: a.spots.drip.filter((p) => inside(p[0], p[2])) },
    waterRects: a.waterRects.map(clip).filter(Boolean), lavaRects: a.lavaRects.map(clip).filter(Boolean), holes: a.holes.filter((h) => inside(h.x, h.z))
  };
  return a;
}

// ---- the bake ---------------------------------------------------------------------------------------------------
// A solid test along a ray through the grid (cell centres, Amanatides and Woo).
function makeVisible(a) {
  return (x0, y0, z0, x1, y1, z1) => {
    let i = Math.floor(x0), j = Math.floor(y0), k = Math.floor(z0);
    const ie = Math.floor(x1), je = Math.floor(y1), ke = Math.floor(z1);
    const dx = x1 - x0, dy = y1 - y0, dz = z1 - z0;
    const sx = dx > 0 ? 1 : -1, sy = dy > 0 ? 1 : -1, sz = dz > 0 ? 1 : -1;
    const adx = Math.abs(dx), ady = Math.abs(dy), adz = Math.abs(dz);
    let tx = adx > 1e-9 ? ((sx > 0 ? i + 1 - x0 : x0 - i) / adx) : Infinity;
    let ty = ady > 1e-9 ? ((sy > 0 ? j + 1 - y0 : y0 - j) / ady) : Infinity;
    let tz = adz > 1e-9 ? ((sz > 0 ? k + 1 - z0 : z0 - k) / adz) : Infinity;
    const ddx = adx > 1e-9 ? 1 / adx : Infinity, ddy = ady > 1e-9 ? 1 / ady : Infinity, ddz = adz > 1e-9 ? 1 / adz : Infinity;
    for (let n = 0; n < 48; n++) {
      if (i === ie && j === je && k === ke) return true;
      if (tx < ty && tx < tz) { i += sx; tx += ddx; } else if (ty < tz) { j += sy; ty += ddy; } else { k += sz; tz += ddz; }
      if (i === ie && j === je && k === ke) return true;
      if (a.solid(i, j, k)) return false;
    }
    return true;
  };
}


// lightAt(x, y, z, nx, ny, nz) -> [r, g, b]: the ambient of the leg plus every source in reach, with occlusion.
export function makeLightAt(a) {
  const plan = a.plan, BIN = 13;
  const bins = new Map();
  const key = (i, j, k) => (i + 4096) * 16777216 + (j + 512) * 4096 + (k + 4096);
  for (const s of a.sources) {
    const kk = key(Math.floor(s.x / BIN), Math.floor(s.y / BIN), Math.floor(s.z / BIN));
    if (!bins.has(kk)) bins.set(kk, []);
    bins.get(kk).push(s);
  }
  const vis = makeVisible(a);
  const out = [0, 0, 0];
  const prof = {}, pcache = new Map();
  const profAt = (x, z) => {
    const ck = Math.floor(x / 2) * 100003 + Math.floor(z / 2);
    let p = pcache.get(ck);
    if (p) return p;
    const h = plan.legAt(x, z, a.legs);
    const d = h ? plan.dAtB(h.leg, h.b) : 0;
    plan.profileAtD(d, prof);
    p = { amb: prof.amb.slice(), torch: prof.torch };
    pcache.set(ck, p); return p;
  };
  const lightAt = (x, y, z, nx, ny, nz, o = {}) => {
    const pr = profAt(x, z);
    const hm = 1 + 0.28 * ny;
    out[0] = pr.amb[0] * hm; out[1] = pr.amb[1] * hm; out[2] = pr.amb[2] * hm;
    const bi = Math.floor(x / BIN), bj = Math.floor(y / BIN), bk = Math.floor(z / BIN);
    for (let di = -1; di <= 1; di++) for (let dj = -1; dj <= 1; dj++) for (let dk = -1; dk <= 1; dk++) {
      const list = bins.get(key(bi + di, bj + dj, bk + dk));
      if (!list) continue;
      for (const sc of list) {
        const lx = sc.x - x, ly = sc.y - y, lz = sc.z - z;
        const d2 = lx * lx + ly * ly + lz * lz;
        if (d2 > sc.R * sc.R) continue;
        const d = Math.sqrt(d2);
        let ndl = d > 1e-4 ? (nx * lx + ny * ly + nz * lz) / d : 1;
        if (o.omni) ndl = 0.7;
        if (ndl <= -0.15) continue;
        ndl = Math.max(0, ndl) * 0.85 + 0.15;
        const win = Math.max(0, 1 - (d2 / (sc.R * sc.R)) ** 2);
        const I = sc.I * (sc.sky ? 1 : (sc.lava || sc.c[2] > 0.8 ? 1 : pr.torch));
        const att = I * win * win / (d2 + 1.3);
        if (att < 0.004) continue;
        if (!vis(x, y, z, sc.x, sc.y, sc.z)) continue;
        const f = att * ndl * (sc.dyn ? 0.62 : 1);
        out[0] += sc.c[0] * f; out[1] += sc.c[1] * f; out[2] += sc.c[2] * f;
      }
    }
    return out;
  };
  return lightAt;
}

// ---- meshing ----------------------------------------------------------------------------------------------------
export function blockNameAt(a, x, y, z) {
  const i = Math.floor(x), j = Math.floor(y), k = Math.floor(z);
  if (!a.inb(i, j, k)) return "bedrock";
  const ix = a.idx(i, j, k), t = a.g[ix];
  return BLOCK_NAME[t === T_WALL ? wallType(a.st[ix], i, j, k) : t] || "stone";
}

// Materials and textures, shared by every chunk.
export function makeMats(images) {
  const texs = {}, mats = {};
  const texOf = (file) => {
    if (texs[file] !== undefined) return texs[file];
    const img = images[file];
    if (!img) return (texs[file] = null);
    const tex = new THREE.Texture(img);
    tex.colorSpace = THREE.SRGBColorSpace; tex.magFilter = THREE.NearestFilter; tex.minFilter = THREE.NearestFilter;
    tex.wrapS = tex.wrapT = THREE.RepeatWrapping; tex.generateMipmaps = false; tex.needsUpdate = true;
    return (texs[file] = tex);
  };
  const matOf = (file) => mats[file] || (mats[file] = patchBake(new THREE.MeshLambertMaterial({ map: texOf(file) })));
  return { texOf, matOf };
}

const DIRS = [[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]];
const CORNERS = [[0, 0], [1, 0], [1, 1], [0, 1]];
// The faces of one chunk (the window's blocks inside its box), one mesh per texture, with the bake in a vertex colour.
export function meshChunk(win, mm) {
  const a = win, bb = win.bb, group = new THREE.Group();
  const lightAt = win.lightAt || (win.lightAt = makeLightAt(a));
  const bins = new Map();
  const bin = (file) => { if (!bins.has(file)) bins.set(file, { pos: [], nor: [], uv: [], bake: [] }); return bins.get(file); };
  const iLo = Math.max(a.i0 + 1, bb.x0), iHi = Math.min(a.i0 + a.NI - 1, bb.x1), kLo = Math.max(a.k0 + 1, bb.z0), kHi = Math.min(a.k0 + a.NK - 1, bb.z1);
  const NIJ = a.NI * a.NJ;
  for (let k = kLo; k < kHi; k++) for (let j = a.j0 + 1; j < a.j0 + a.NJ - 1; j++) for (let i = iLo; i < iHi; i++) {
    const ix = ((k - a.k0) * a.NJ + (j - a.j0)) * a.NI + (i - a.i0);
    const raw = a.g[ix];
    if (raw === T_AIR || raw === T_WATER || raw === T_LAVA) continue;
    let tt = null;
    for (const [di, dj, dk] of DIRS) {
      const n = a.g[ix + di + dj * a.NI + dk * NIJ];
      if (n !== T_AIR && n !== T_WATER && n !== T_LAVA) continue;
      if (tt === null) tt = raw === T_WALL ? wallType(a.st[ix], i, j, k) : raw;
      const names = TEX_OF[tt] || TEX_OF[T_STONE];
      const top = dj > 0, bot = dj < 0;
      const fr = FRONT[tt];
      const file = fr && fr[0] === di && fr[1] === dk ? fr[2] : top ? (names[1] || names[0]) : bot ? (names[2] || (names[1] && tt !== 7 ? names[1] : names[0])) : names[0];
      const b = bin(file);
      const ax = di ? 0 : dj ? 1 : 2, sn = di + dj + dk;
      const t1 = (ax + 1) % 3, t2 = (ax + 2) % 3;
      const base = [i, j, k]; base[ax] += sn > 0 ? 1 : 0;
      const verts = CORNERS.map(([c1, c2]) => { const p = base.slice(); p[t1] += c1; p[t2] += c2; return p; });
      const e1 = [verts[1][0] - verts[0][0], verts[1][1] - verts[0][1], verts[1][2] - verts[0][2]];
      const e2 = [verts[2][0] - verts[0][0], verts[2][1] - verts[0][1], verts[2][2] - verts[0][2]];
      const cr = [e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]];
      const order = (cr[0] * di + cr[1] * dj + cr[2] * dk) >= 0 ? [0, 1, 2, 0, 2, 3] : [0, 2, 1, 0, 3, 2];
      const em = EMISSIVE[tt];
      const bl = em || lightAt(i + 0.5 + di * 0.52, j + 0.5 + dj * 0.52, k + 0.5 + dk * 0.52, di, dj, dk);
      const bkr = bl[0], bkg = bl[1], bkb = bl[2];
      const aos = CORNERS.map(([c1, c2]) => {
        const s1 = c1 ? 1 : -1, s2 = c2 ? 1 : -1;
        const p = [i + di, j + dj, k + dk];
        const q1 = p.slice(); q1[t1] += s1; const q2 = p.slice(); q2[t2] += s2; const q3 = p.slice(); q3[t1] += s1; q3[t2] += s2;
        const o1 = a.solid(q1[0], q1[1], q1[2]) ? 1 : 0, o2 = a.solid(q2[0], q2[1], q2[2]) ? 1 : 0, o3 = a.solid(q3[0], q3[1], q3[2]) ? 1 : 0;
        return AO[(o1 && o2) ? 0 : 3 - (o1 + o2 + o3)];
      });
      for (const q of order) {
        const [px, py, pz] = verts[q];
        b.pos.push(px, py, pz); b.nor.push(di, dj, dk);
        b.uv.push(di ? (di > 0 ? -pz : pz) : px, dj ? pz : py);
        const ao = em ? 1 : aos[q];
        b.bake.push(bkr * ao, bkg * ao, bkb * ao);
      }
    }
  }
  for (const [file, b] of bins) {
    if (!mm.texOf(file) || !b.pos.length) continue;
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute(b.pos, 3));
    g.setAttribute("normal", new THREE.Float32BufferAttribute(b.nor, 3));
    g.setAttribute("uv", new THREE.Float32BufferAttribute(b.uv, 2));
    g.setAttribute("bake", new THREE.Float32BufferAttribute(b.bake, 3));
    const m = new THREE.Mesh(g, mm.matOf(file));
    m.matrixAutoUpdate = false;
    group.add(m);
  }
  return group;
}

// ---- the world: chunks streamed around the walker ----------------------------------------------------------------
export function makeWorld({ plan, images, scene, dresser, onChange = null, radius = 84 }) {
  const mm = makeMats(images);
  const chunks = new Map();                       // key -> { ci, ck, win, terrain, dress, bb }
  const carves = [];                               // boxes carved so far, applied to every window built later
  const saved = new Map();                         // window -> Map(grid index -> original)
  const timing = { n: 0, ms: 0, max: 0 };
  const root = new THREE.Group(); scene.add(root);
  const keyOf = (ci, ck) => ci + "," + ck;
  const agg = { torches: [], dyn: [], emit: [], spots: { fire: [], lava: [], drip: [] }, holes: [], version: 0 };
  let changed = false;
  const reagg = () => {
    agg.torches = []; agg.dyn = []; agg.emit = []; agg.holes = []; agg.spots = { fire: [], lava: [], drip: [] };
    for (const c of chunks.values()) {
      if (!c.win) continue;
      const o = c.win.own;
      agg.torches.push(...o.torches); agg.dyn.push(...o.dyn); agg.emit.push(...o.emit); agg.holes.push(...o.holes);
      agg.spots.fire.push(...o.spots.fire); agg.spots.lava.push(...o.spots.lava); agg.spots.drip.push(...o.spots.drip);
    }
    agg.version++; changed = false;
    if (onChange) onChange(agg);
  };
  const clampBox = (mn, mx) => [
    [Math.floor(Math.min(mn[0], mx[0])), Math.floor(Math.min(mn[1], mx[1])), Math.floor(Math.min(mn[2], mx[2]))],
    [Math.floor(Math.max(mn[0], mx[0])), Math.floor(Math.max(mn[1], mx[1])), Math.floor(Math.max(mn[2], mx[2]))]];
  // Empty the blocks of a box in one window (never its outer shell). Returns how many changed.
  const carveWin = (win, lo, hi) => {
    let n = 0, core = 0;
    const sv = saved.get(win) || new Map(); saved.set(win, sv);
    for (let k = Math.max(lo[2], win.k0 + 1); k <= Math.min(hi[2], win.k0 + win.NK - 2); k++)
      for (let j = Math.max(lo[1], win.j0 + 1); j <= Math.min(hi[1], win.j0 + win.NJ - 2); j++)
        for (let i = Math.max(lo[0], win.i0 + 1); i <= Math.min(hi[0], win.i0 + win.NI - 2); i++) {
          const ix = win.idx(i, j, k);
          if (win.g[ix] === T_AIR) continue;
          if (!sv.has(ix)) sv.set(ix, win.g[ix]);
          win.g[ix] = T_AIR; n++;
          if (i >= win.bb.x0 && i < win.bb.x1 && k >= win.bb.z0 && k < win.bb.z1) core++;
        }
    return [n, core];
  };
  const overlaps = (c, lo, hi, pad) => c.bb.x0 - pad <= hi[0] && c.bb.x1 + pad > lo[0] && c.bb.z0 - pad <= hi[2] && c.bb.z1 + pad > lo[2];

  function disposeTerrain(c) { if (!c.terrain) return; root.remove(c.terrain); c.terrain.traverse((o) => { if (o.geometry) o.geometry.dispose(); }); c.terrain = null; }
  function build(ci, ck) {
    const key = keyOf(ci, ck);
    if (chunks.has(key)) return chunks.get(key);
    const t0 = performance.now();
    const c = { key, ci, ck, bb: { x0: ci * CH, z0: ck * CH, x1: (ci + 1) * CH, z1: (ck + 1) * CH }, win: null, terrain: null, dress: null };
    chunks.set(key, c);
    const win = buildWindow(plan, ci, ck);
    if (win) {
      c.win = win;
      for (const [lo, hi] of carves) carveWin(win, lo, hi);
      c.terrain = meshChunk(win, mm); root.add(c.terrain);
      c.dress = dresser.build(win.own, win.lightAt || (win.lightAt = makeLightAt(win)));
      root.add(c.dress.group);
    }
    changed = true;
    timing.n++; timing.ms += performance.now() - t0; timing.max = Math.max(timing.max, performance.now() - t0);
    return c;
  }
  function unload(c) {
    disposeTerrain(c);
    if (c.dress) { root.remove(c.dress.group); c.dress.dispose(); c.dress = null; }
    if (c.win) saved.delete(c.win);
    chunks.delete(c.key); changed = true;
  }
  // The chunks (ci, ck) holding anything near (x, z): those whose box meets a leg's hall box and lies within r of the point.
  function wanted(x, z, r) {
    const out = new Map();
    for (const leg of plan.legsIn(x - r, z - r, x + r, z + r)) {
      const bx = legBox(leg);
      const c0 = Math.floor(Math.max(bx.x0, x - r) / CH), c1 = Math.floor(Math.min(bx.x1, x + r) / CH), k0 = Math.floor(Math.max(bx.z0, z - r) / CH), k1 = Math.floor(Math.min(bx.z1, z + r) / CH);
      for (let ci = c0; ci <= c1; ci++) for (let ck = k0; ck <= k1; ck++) {
        const cx = Math.max(ci * CH, Math.min(x, (ci + 1) * CH)), cz = Math.max(ck * CH, Math.min(z, (ck + 1) * CH));
        const d = Math.hypot(cx - x, cz - z);
        if (d > r) continue;
        // The chunk must meet the hall box itself, not just the leg's wide reach.
        if ((ci + 1) * CH <= bx.x0 || ci * CH >= bx.x1 || (ck + 1) * CH <= bx.z0 || ck * CH >= bx.z1) continue;
        const key = keyOf(ci, ck); if (!out.has(key) || out.get(key).d > d) out.set(key, { ci, ck, d });
      }
    }
    return out;
  }
  const world = {
    plan, chunks, agg, root,
    // Build up to n of the nearest missing chunks around (x, z), and drop the ones that are far behind.
    update(x, z, n = 1) {
      const want = wanted(x, z, radius);
      for (const c of [...chunks.values()]) { const cx = Math.max(c.bb.x0, Math.min(x, c.bb.x1)), cz = Math.max(c.bb.z0, Math.min(z, c.bb.z1)); if (Math.hypot(cx - x, cz - z) > radius + 40) unload(c); }
      const todo = [...want.values()].filter((w) => !chunks.has(keyOf(w.ci, w.ck))).sort((p, q) => p.d - q.d);
      let built = 0;
      for (const w of todo) { if (built >= n) break; build(w.ci, w.ck); built++; }
      if (changed) reagg();
      return todo.length - built;
    },
    // Everything within r, now (the verification frame and the jump to a far grave).
    ensure(x, z, r = radius) { let left = 0; for (const w of wanted(x, z, r).values()) if (!chunks.has(keyOf(w.ci, w.ck))) build(w.ci, w.ck); if (changed) reagg(); return left; },
    chunkAt(x, z) { return chunks.get(keyOf(Math.floor(x / CH), Math.floor(z / CH))) || null; },
    lightAt(x, y, z, nx, ny, nz, o) {
      const c = world.chunkAt(x, z);
      if (c && c.win) { c.win.lightAt = c.win.lightAt || makeLightAt(c.win); return c.win.lightAt(x, y, z, nx, ny, nz, o); }
      for (const q of chunks.values()) if (q.win && x >= q.win.i0 && x < q.win.i0 + q.win.NI && z >= q.win.k0 && z < q.win.k0 + q.win.NK) { q.win.lightAt = q.win.lightAt || makeLightAt(q.win); return q.win.lightAt(x, y, z, nx, ny, nz, o); }
      return [0.1, 0.1, 0.12];
    },
    stats() {
      let meshes = 0, built = 0;
      for (const c of chunks.values()) if (c.win) { built++; meshes += (c.terrain ? c.terrain.children.length : 0) + (c.dress ? c.dress.group.children.length : 0); }
      return { chunks: built, loaded: chunks.size, meshes, builds: timing.n, buildMs: Math.round(timing.ms), maxMs: Math.round(timing.max) };
    },
    // The scares' contract.
    carve(mn, mx) {
      const [lo, hi] = clampBox(mn, mx);
      let n = 0;
      const touched = [];
      for (const c of chunks.values()) {
        const w = c.win; if (!w) continue;
        if (w.i0 > hi[0] || w.i0 + w.NI <= lo[0] || w.k0 > hi[2] || w.k0 + w.NK <= lo[2]) continue;
        const [m, core] = carveWin(w, lo, hi);
        n += core;
        if (m && c.bb.x0 - 1 <= hi[0] && c.bb.x1 + 1 > lo[0] && c.bb.z0 - 1 <= hi[2] && c.bb.z1 + 1 > lo[2]) touched.push(c);
      }
      carves.push([lo, hi]);
      for (const c of touched) { disposeTerrain(c); c.terrain = meshChunk(c.win, mm); root.add(c.terrain); }
      return n;
    },
    restore() {
      let n = 0; const touched = [];
      for (const [win, sv] of saved) {
        if (!sv.size) continue;
        for (const [ix, v] of sv) { win.g[ix] = v; const i = ix % win.NI + win.i0, k = Math.floor(ix / (win.NI * win.NJ)) + win.k0; if (i >= win.bb.x0 && i < win.bb.x1 && k >= win.bb.z0 && k < win.bb.z1) n++; }
        sv.clear(); touched.push(win);
      }
      carves.length = 0;
      for (const win of touched) { const c = chunks.get(keyOf(win.bb.x0 / CH, win.bb.z0 / CH)); if (c && c.win === win) { disposeTerrain(c); c.terrain = meshChunk(c.win, mm); root.add(c.terrain); } }
      return n;
    },
    solidAt(x, y, z) {
      const c = world.chunkAt(x, z); if (!c || !c.win) return true;
      return c.win.solid(Math.floor(x), Math.floor(y), Math.floor(z));
    },
    blockAt(x, y, z) {
      const c = world.chunkAt(x, z); if (!c || !c.win) return "stone";
      return blockNameAt(c.win, x, y, z);
    }
  };
  return world;
}

const AO = [0.42, 0.62, 0.8, 1.0];
export const bakeUniform = { value: 1 };
// The light effects of the contract (window.__krypt.light, lightfx.js): a global scale for every light, and up to four
// dim spheres (position and radius, amount) that darken the baked light and the torches around one point.
export const lightScale = { value: 1 };
export const dimU = { P: { value: [new THREE.Vector4(0, -999, 0, 1), new THREE.Vector4(0, -999, 0, 1), new THREE.Vector4(0, -999, 0, 1), new THREE.Vector4(0, -999, 0, 1)] }, A: { value: [0, 0, 0, 0] } };
export const torchGain = { value: 1 };
const DIM_GLSL = "uniform vec4 uDimP[4]; uniform float uDimA[4]; uniform float uLightScale;\n" +
  "float dimAt(vec3 p){ float f = 1.0; for (int i = 0; i < 4; i++) { float d = distance(p, uDimP[i].xyz); f *= 1.0 - uDimA[i] * (1.0 - smoothstep(uDimP[i].w * 0.3, uDimP[i].w, d)); } return f; }";
const hookDim = (sh) => { sh.uniforms.uDimP = dimU.P; sh.uniforms.uDimA = dimU.A; sh.uniforms.uLightScale = lightScale; };

// Adds the baked light to a Lambert or Standard material as emissive-times-albedo from a per-vertex 'bake' attribute
// (or a fixed vec3 when the object has none).
export function patchBake(mat, { fixed = null } = {}) {
  mat.onBeforeCompile = (sh) => {
    sh.uniforms.uBakeGain = bakeUniform;
    hookDim(sh);
    if (fixed) sh.uniforms.uBakeFixed = { value: fixed };
    sh.vertexShader = sh.vertexShader
      .replace("#include <common>", "#include <common>\nvarying vec3 vWP;" + (fixed ? "" : "\nattribute vec3 bake;\nvarying vec3 vBake;"))
      .replace("#include <begin_vertex>", "#include <begin_vertex>\nvWP = (modelMatrix * vec4(transformed, 1.0)).xyz;" + (fixed ? "" : "\nvBake = bake;"));
    sh.fragmentShader = sh.fragmentShader
      .replace("#include <common>", (fixed ? "#include <common>\nuniform vec3 uBakeFixed;" : "#include <common>\nvarying vec3 vBake;") + "\nvarying vec3 vWP;\nuniform float uBakeGain;\n" + DIM_GLSL)
      .replace("#include <emissivemap_fragment>", "#include <emissivemap_fragment>\ntotalEmissiveRadiance += diffuseColor.rgb * " + (fixed ? "uBakeFixed" : "vBake") + " * uBakeGain * uLightScale * dimAt(vWP);");
  };
  mat.customProgramCacheKey = () => (fixed ? "bakeF2" : "bakeV2");
  return mat;
}
// The torch's own material: fullbright, but it follows the light scale and goes dark inside a dim sphere.
export function patchTorch(mat) {
  mat.onBeforeCompile = (sh) => {
    hookDim(sh); sh.uniforms.uTorchGain = torchGain;
    sh.vertexShader = sh.vertexShader.replace("#include <common>", "#include <common>\nvarying vec3 vWP;").replace("#include <begin_vertex>", "#include <begin_vertex>\nvWP = (modelMatrix * vec4(transformed, 1.0)).xyz;");
    sh.fragmentShader = sh.fragmentShader.replace("#include <common>", "#include <common>\nvarying vec3 vWP;\nuniform float uTorchGain;\n" + DIM_GLSL)
      .replace("#include <color_fragment>", "#include <color_fragment>\ndiffuseColor.rgb *= uTorchGain * (0.12 + 0.88 * dimAt(vWP));");
  };
  mat.customProgramCacheKey = () => "torchDim";
  return mat;
}

