// The Krypt: a gallery of nine distinct segments cut into stone under the pack's sky, joined by bends and
// side passages. The layout is a chain of straight legs (headings N, W, E; the walk goes toward -z at first).
// A block grid is carved from the legs, lit by a bake (torches, lava, glowstone, the sky cracks, with the
// shadows of the blocks and per-corner occlusion), meshed once per texture, and dressed by dress.js.
// Graves stand in alcoves all the way through, in the order of the feed.
import * as THREE from "three";
import { hash } from "./data.js";

export const SLOT_STEP = 4;
export const T_AIR = 0, T_STONE = 1, T_COBBLE = 2, T_MOSSY = 3, T_BRICK = 4, T_BRICK_MOSSY = 5, T_BRICK_CRACK = 6,
  T_GRAVEL_FLOOR = 7, T_COAL = 8, T_IRON = 9, T_OBS = 10, T_BEDROCK = 11, T_NETHER = 12, T_GLOW = 13, T_BRIDGE = 14,
  T_WATER = 15, T_NBRICK = 16, T_SOUL = 17, T_SHELF = 18, T_PLANK = 19, T_LOG = 20, T_LAVA = 22, T_DIRT = 23,
  T_DISP_PX = 24, T_DISP_NX = 25, T_DISP_PZ = 26, T_DISP_NZ = 27, T_GOLD = 28, T_DIAM = 29, T_LAPIS = 30, T_EMERALD = 31,
  T_IRONB = 32, T_CARVED = 33,
  T_WALL = 255;

// ---- the segments --------------------------------------------------------------------------------
// weight: share of the stones; hw: half width; ht: height of the air; pre/post: empty rows at either end;
// branch: side passages; holes: where the sky cracks open (fractions along the content); fixed: a set number of
// stones; sid: the segment's stable id (wall style and the seed of its random dressing).
// Headings turn only between N and W/E (never W straight to E).
const SPEC = [
  { kind: "crypt",      sid: 1,  h: "N", hw: 3, ht: 4, pre: 6, post: 0, weight: 2, branch: 0, holes: [0.6] },
  { kind: "mine",       sid: 2,  h: "W", hw: 3, ht: 4, pre: 2, post: 0, weight: 3, branch: 1, holes: [0.45] },
  { kind: "catacomb",   sid: 10, h: "N", hw: 3, ht: 4, pre: 3, post: 0, weight: 3, branch: 1, step: 8, holes: [] },
  { kind: "ossuary",    sid: 3,  h: "N", hw: 3, ht: 4, pre: 2, post: 0, weight: 3, branch: 2, holes: [] },
  { kind: "flood",      sid: 4,  h: "E", hw: 4, ht: 5, pre: 2, post: 0, weight: 3, branch: 1, holes: [0.5] },
  { kind: "spidermine", sid: 11, h: "N", hw: 3, ht: 4, pre: 2, post: 0, weight: 3, branch: 1, step: 8, holes: [] },
  { kind: "temple",     sid: 12, h: "W", hw: 3, ht: 5, pre: 3, post: 2, weight: 3, branch: 1, step: 12, holes: [] },
  { kind: "dungeon",    sid: 5,  h: "N", hw: 6, ht: 5, pre: 4, post: 4, weight: 2, branch: 0, holes: [] },
  { kind: "library",    sid: 6,  h: "W", hw: 4, ht: 6, pre: 2, post: 0, weight: 3, branch: 1, holes: [0.8] },
  { kind: "vault",      sid: 13, h: "N", hw: 4, ht: 5, pre: 6, post: 3, weight: 2, branch: 0, step: 8, holes: [] },
  { kind: "chasm",      sid: 7,  h: "N", hw: 6, ht: 6, pre: 3, post: 0, weight: 2, branch: 0, holes: [0.3, 0.75] },
  { kind: "stairs",     sid: 8,  h: "N", hw: 3, ht: 4, pre: 0, post: 0, weight: 1, branch: 0, holes: [], stairs: true, fixed: 1 },
  { kind: "fortress",   sid: 14, h: "E", hw: 5, ht: 6, pre: 3, post: 2, weight: 3, branch: 1, step: 8, holes: [] },
  { kind: "deep",       sid: 9,  h: "N", hw: 4, ht: 5, pre: 2, post: 4, weight: 4, branch: 1, holes: [] },
  { kind: "stronghold", sid: 15, h: "N", hw: 5, ht: 7, pre: 3, post: 12, weight: 2, branch: 0, step: 8, holes: [], fixed: 2 }
];
export const KINDS = SPEC.map(s => s.kind);
const STAIR_LANDING = 6, STAIR_LEN = 12, STAIR_DROP = 6, CHASM_DEPTH = 4, FORT_DEPTH = 2, PASSAGE_LEN = 9, MIN_STONES = 39;

// Lighting by depth: the bake and the page's live lighting read the same table (keyed at each segment's centre).
// amb: the baked ambient; fog: colour and density; exposure; torch: scale of torch light; hemi: live fill.
export const PROFILE = {
  crypt:   { amb: [0.060, 0.082, 0.150], fog: [0.030, 0.040, 0.075], fogD: 0.040, exposure: 1.18, torch: 0.78, bloom: 0.30 },
  mine:    { amb: [0.075, 0.075, 0.085], fog: [0.040, 0.036, 0.040], fogD: 0.040, exposure: 1.18, torch: 0.9,  bloom: 0.32 },
  ossuary: { amb: [0.080, 0.068, 0.078], fog: [0.040, 0.030, 0.038], fogD: 0.042, exposure: 1.2,  torch: 0.9,  bloom: 0.32 },
  flood:   { amb: [0.060, 0.105, 0.120], fog: [0.020, 0.045, 0.052], fogD: 0.040, exposure: 1.2,  torch: 1.0,  bloom: 0.34 },
  dungeon: { amb: [0.095, 0.082, 0.062], fog: [0.044, 0.034, 0.026], fogD: 0.036, exposure: 1.2,  torch: 1.1,  bloom: 0.36 },
  library: { amb: [0.115, 0.082, 0.052], fog: [0.052, 0.035, 0.022], fogD: 0.034, exposure: 1.2,  torch: 1.0,  bloom: 0.36 },
  chasm:   { pitch: -0.3, amb: [0.105, 0.052, 0.032], fog: [0.070, 0.028, 0.014], fogD: 0.030, exposure: 1.22, torch: 0.8,  bloom: 0.46 },
  stairs:  { amb: [0.095, 0.048, 0.028], fog: [0.066, 0.026, 0.012], fogD: 0.034, exposure: 1.22, torch: 0.75, bloom: 0.44 },
  deep:    { amb: [0.120, 0.046, 0.022], fog: [0.085, 0.024, 0.010], fogD: 0.034, exposure: 1.25, torch: 1.0, bloom: 0.55 },
  catacomb:   { amb: [0.086, 0.098, 0.116], fog: [0.036, 0.042, 0.054], fogD: 0.040, exposure: 1.22, torch: 1.1,  bloom: 0.32 },
  spidermine: { amb: [0.064, 0.058, 0.066], fog: [0.032, 0.026, 0.034], fogD: 0.046, exposure: 1.2,  torch: 0.9,  bloom: 0.30 },
  temple:     { amb: [0.098, 0.135, 0.088], fog: [0.034, 0.056, 0.032], fogD: 0.038, exposure: 1.22, torch: 1.25, bloom: 0.34 },
  vault:      { amb: [0.088, 0.086, 0.100], fog: [0.042, 0.042, 0.054], fogD: 0.034, exposure: 1.2,  torch: 1.1,  bloom: 0.40 },
  fortress:   { amb: [0.180, 0.078, 0.058], fog: [0.090, 0.030, 0.020], fogD: 0.030, exposure: 1.25, torch: 1.3,  bloom: 0.50 },
  stronghold: { amb: [0.066, 0.096, 0.092], fog: [0.028, 0.050, 0.050], fogD: 0.036, exposure: 1.24, torch: 1.0,  bloom: 0.46 }
};

// ---- leg geometry ----------------------------------------------------------------------------------
// A leg has an origin lattice point (px, pz) and a heading. Local a runs across (right is +), b along.
export function legMap(leg, a, b) {
  if (leg.h === "N") return [leg.px + a, leg.pz - b];
  if (leg.h === "W") return [leg.px - b, leg.pz - a];
  return [leg.px + b, leg.pz + a];
}
export function legLocal(leg, x, z) {
  if (leg.h === "N") return [x - leg.px, leg.pz - z];
  if (leg.h === "W") return [leg.pz - z, leg.px - x];
  return [z - leg.pz, x - leg.px];
}
export const legYaw = (leg) => (leg.h === "N" ? 0 : leg.h === "W" ? Math.PI / 2 : -Math.PI / 2);
const legCell = (leg, lu, lv) => { const [x, z] = legMap(leg, lu + 0.5, lv + 0.5); return [Math.floor(x), Math.floor(z)]; };
export const legDir = (leg) => (leg.h === "N" ? [0, -1] : leg.h === "W" ? [-1, 0] : [1, 0]);
const turnOf = (from, to) => (from === "N" ? (to === "W" ? -1 : 1) : (from === "W" ? 1 : -1));

// Floor top of leg row lv (an integer y); the stairs step down every two rows.
export function floorTop(leg, lv) {
  if (!leg.stairs) return leg.y0;
  const t = lv - leg.stairsAt;
  if (t < 0) return leg.y0;
  return leg.y0 - Math.min(STAIR_DROP, Math.floor(t / 2) + 1);
}
// Camera floor level, continuous (a ramp over the steps).
export function floorSmooth(leg, b) {
  if (!leg.stairs) return leg.y0;
  const t = (b - leg.stairsAt) / 2 - 0.5;
  return leg.y0 - Math.max(0, Math.min(STAIR_DROP, t + 0.5));
}

// ---- the layout ------------------------------------------------------------------------------------
export function layout(n) {
  const S = Math.max(n, MIN_STONES);
  const wsum = SPEC.reduce((a, s) => a + s.weight, 0);
  const wfree = SPEC.reduce((a, s) => a + (s.fixed ? 0 : s.weight), 0);
  const sfree = S - SPEC.reduce((a, s) => a + (s.fixed || 0), 0);
  const counts = SPEC.map(s => (s.fixed ? s.fixed : Math.max(2, Math.floor(sfree * s.weight / wfree))));
  let left = S - counts.reduce((a, b) => a + b, 0);
  for (let g = 0; left > 0; g = (g + 1) % SPEC.length) { const q = SPEC.length - 1 - g; if (SPEC[q].fixed) continue; counts[q] += 1; left--; }
  for (let g = 0; left < 0; g = (g + 1) % SPEC.length) { const q = g; if (SPEC[q].fixed || counts[q] <= 2) continue; counts[q] -= 1; left++; }
  const legs = [], slots = [], corners = [];
  let prev = null, gi = 0;
  SPEC.forEach((sp, idx) => {
    const leg = { ...sp, idx, m: counts[idx], slots: [], passages: [], lavaCells: [], holesAt: [], style: sp.sid, rid: sp.sid - 1, y0: 0, px: 0, pz: 0, cs: 0, b0: 0 };
    if (prev) {
      leg.y0 = prev.yEnd;
      if (prev.h !== sp.h) {
        prev.ce = prev.end + sp.hw;
        const [cx, cz] = legMap(prev, 0, prev.ce);
        leg.px = cx; leg.pz = cz; leg.cs = -prev.hw; leg.b0 = prev.hw;
        leg.turn = turnOf(prev.h, sp.h);
        const d = legDir(leg);
        corners.push({ kind: "bend", x: cx, z: cz, y: leg.y0, dx: d[0], dz: d[1], side: leg.turn, leg: idx });
      } else {
        prev.ce = prev.end;
        const [cx, cz] = legMap(prev, 0, prev.end);
        leg.px = cx; leg.pz = cz;
      }
    }
    let cur = leg.b0 + sp.pre;
    const branchAfter = new Set();
    const nb = Math.min(sp.branch, Math.max(0, leg.m - 1));
    for (let q = 0; q < nb; q++) branchAfter.add(Math.max(0, Math.floor((q + 1) * leg.m / (nb + 1)) - 1));
    for (let t = 0; t < leg.m; t++) {
      const lvc = cur + 3;
      const slot = { i: gi, side: gi % 2 ? 1 : -1, leg: idx, lvc };
      leg.slots.push(slot); slots.push(slot); gi++;
      cur += sp.step || SLOT_STEP;
      if (branchAfter.has(t)) {
        const side = slot.side, lv0 = lvc + 4;
        leg.passages.push({ side, lv: lv0, len: PASSAGE_LEN, ok: false });
        cur += 6;
      }
    }
    leg.contentEnd = cur;
    cur += 2 + sp.post;
    if (sp.stairs) {
      // The landing holds one stone; the flight starts after it. The landing keeps six rows.
      leg.stairsAt = leg.b0 + STAIR_LANDING;
      cur = leg.stairsAt + STAIR_LEN;
      leg.yEnd = leg.y0 - STAIR_DROP;
    } else leg.yEnd = leg.y0;
    leg.end = cur;
    leg.ce = leg.end;
    if (sp.kind === "stronghold") { leg.vc = leg.end - 5; leg.pathEnd = leg.vc - 5; }
    for (const f of sp.holes) leg.holesAt.push(Math.round(leg.b0 + sp.pre + (leg.contentEnd - leg.b0 - sp.pre) * f));
    legs.push(leg); prev = leg;
  });
  const lay = { legs, slots, corners, count: n, total: S };
  return lay;
}

// Where the stone, the statue and the camera stand for a slot.
export function slotFrame(lay, s) {
  const leg = lay.legs[s.leg];
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

// The camera's path: the centre of every leg with a slow sway, rounded at the bends, rising and falling with the floor.
export function pathCurve(lay) {
  const pts = [];
  const R = 2.7;
  const push = (x, y, z) => pts.push(new THREE.Vector3(x, y, z));
  lay.legs.forEach((leg, li) => {
    const nxt = lay.legs[li + 1];
    const bend = nxt && nxt.turn;
    const bStart = li === 0 ? 0 : (leg.turn ? R : 0);
    const bEnd = leg.pathEnd != null ? leg.pathEnd : leg.ce;
    const yAt = (b) => floorSmooth(leg, b) + 1.5;
    const swayEnd = bend ? bEnd - R : bEnd;
    const sway = (b) => {
      const edge = Math.min(b - bStart, swayEnd - b, 7) / 7;
      const e = Math.max(0, Math.min(1, edge));
      return Math.sin(b / 6.5 + li * 1.7) * 0.7 * e * e * (3 - 2 * e);
    };
    // Start of the leg: its corner point was already pushed by the previous leg's arc; start just after it.
    const from = li === 0 ? 0 : (leg.turn ? R + 1.5 : 1.5);
    const to = bend ? bEnd - R : bEnd;
    for (let b = from; b < to; b += 1.5) { const [x, z] = legMap(leg, sway(b), b); push(x, yAt(b), z); }
    if (!bend) { const [x, z] = legMap(leg, 0, to); push(x, yAt(to), z); }
    if (bend) {
      // The arc, from heading A to heading B around the corner point C.
      const dA = legDir(leg), dB = legDir(nxt);
      const [cx, cz] = legMap(leg, 0, bEnd);
      for (let q = 0; q <= 4; q++) {
        const f = (q / 4) * Math.PI / 2;
        const x = cx - dA[0] * R + dB[0] * R - dB[0] * R * Math.cos(f) + dA[0] * R * Math.sin(f);
        const z = cz - dA[1] * R + dB[1] * R - dB[1] * R * Math.cos(f) + dA[1] * R * Math.sin(f);
        push(x, yAt(bEnd), z);
      }
    }
  });
  return new THREE.CatmullRomCurve3(pts, false, "centripetal", 0.5);
}

// After the curve exists: every slot, corner and leg gets its s (0..1 along the path), and the profile keys.
export function finishLayout(lay, curve) {
  const N = Math.max(400, Math.round(curve.getLength() * 3));
  const pts = curve.getSpacedPoints(N);
  const sOf = (x, y, z, hint = null) => {
    let best = 0, bd = Infinity;
    const lo = hint != null ? Math.max(0, Math.floor((hint - 0.2) * N)) : 0, hi = hint != null ? Math.min(N, Math.ceil((hint + 0.2) * N)) : N;
    for (let i = lo; i <= hi; i++) {
      const p = pts[i], d = (p.x - x) ** 2 + (p.z - z) ** 2 + ((p.y - y) * 0.5) ** 2;
      if (d < bd) { bd = d; best = i; }
    }
    return best / N;
  };
  lay.sOf = sOf; lay.length = curve.getLength();
  for (const leg of lay.legs) {
    const [x0, z0] = legMap(leg, 0, Math.max(leg.cs, leg.b0));
    const [x1, z1] = legMap(leg, 0, leg.ce);
    leg.s0 = sOf(x0, leg.y0 + 1.5, z0); leg.s1 = sOf(x1, leg.yEnd + 1.5, z1);
    if (leg.s1 < leg.s0) leg.s1 = Math.min(1, leg.s0 + 0.01);
    const [xm, zm] = legMap(leg, 0, (leg.b0 + leg.contentEnd) / 2);
    leg.sMid = sOf(xm, leg.y0 + 1.5, zm);
    for (const s of leg.slots) { const f = slotFrame(lay, s); s.s = sOf(f.centre.x, leg.y0 + 1.5, f.centre.z, leg.sMid); }
  }
  for (const c of lay.corners) c.s = sOf(c.x, c.y + 1.5, c.z);
  lay.keys = lay.legs.map(l => ({ s: l.sMid, p: PROFILE[l.kind], kind: l.kind }));
  return lay;
}

// Profile values at s (smoothly blended between the segment keys).
export function profileAt(lay, s) {
  const K = lay.keys;
  if (s <= K[0].s) return { ...K[0].p, kind: K[0].kind, depth: 0 };
  let i = 0;
  while (i < K.length - 2 && s > K[i + 1].s) i++;
  const A = K[i], B = K[Math.min(K.length - 1, i + 1)];
  const t = Math.max(0, Math.min(1, (s - A.s) / Math.max(1e-4, B.s - A.s)));
  const e = t * t * (3 - 2 * t);
  const mix = (x, y) => x + (y - x) * e;
  const v3 = (x, y) => [mix(x[0], y[0]), mix(x[1], y[1]), mix(x[2], y[2])];
  return {
    amb: v3(A.p.amb, B.p.amb), fog: v3(A.p.fog, B.p.fog), fogD: mix(A.p.fogD, B.p.fogD), exposure: mix(A.p.exposure, B.p.exposure),
    torch: mix(A.p.torch, B.p.torch), bloom: mix(A.p.bloom, B.p.bloom), pitch: mix(A.p.pitch || 0, B.p.pitch || 0), kind: e < 0.5 ? A.kind : B.kind
  };
}
// The leg that holds a world point, and its path fraction (for the bake, which has no curve at hand).
export function legAt(lay, x, z) {
  let best = null, bd = Infinity;
  for (const leg of lay.legs) {
    const [a, b] = legLocal(leg, x, z);
    const ra = Math.max(0, Math.abs(a) - (leg.hw + 2.5)), rb = Math.max(0, leg.cs - b, b - leg.ce);
    const d = ra * ra + rb * rb;
    if (d < bd) { bd = d; best = { leg, a, b }; if (d === 0) break; }
  }
  return best;
}
function sApprox(lay, x, z) {
  const h = legAt(lay, x, z);
  const { leg, b } = h;
  const t = Math.max(0, Math.min(1, (b - leg.b0) / Math.max(1, leg.ce - leg.b0)));
  return leg.s0 + (leg.s1 - leg.s0) * t;
}

// ---- the grid --------------------------------------------------------------------------------------
const ih = (i, j, k, s = 0) => {
  let h = (i * 374761393 + j * 668265263 + k * 2147483647 + s * 1274126177) | 0;
  h = Math.imul(h ^ (h >>> 13), 1274126177); h ^= h >>> 16;
  return (h >>> 0) % 1000;
};
const pickW = (h, table) => { for (const [lim, t] of table) if (h < lim) return t; return table[table.length - 1][1]; };
const WALLS = {
  1: [[150, T_COBBLE], [230, T_MOSSY], [560, T_BRICK], [700, T_BRICK_MOSSY], [1000, T_BRICK_CRACK]],
  2: [[320, T_COBBLE], [600, T_STONE], [670, T_MOSSY], [790, T_DIRT], [900, T_COAL], [925, T_IRON], [1000, T_COBBLE]],
  3: [[330, T_BRICK], [700, T_BRICK_CRACK], [850, T_COBBLE], [960, T_BRICK_MOSSY], [1000, T_OBS]],
  4: [[420, T_BRICK_MOSSY], [650, T_MOSSY], [880, T_BRICK], [1000, T_BRICK_CRACK]],
  5: [[700, T_MOSSY], [1000, T_COBBLE]],
  6: [[620, T_BRICK], [740, T_BRICK_CRACK], [840, T_BRICK_MOSSY], [1000, T_COBBLE]],
  7: [[300, T_STONE], [550, T_COBBLE], [700, T_OBS], [880, T_NETHER], [1000, T_BEDROCK]],
  8: [[400, T_BRICK], [650, T_COBBLE], [1000, T_BRICK_CRACK]],
  9: [[380, T_NBRICK], [840, T_NETHER], [880, T_GLOW], [940, T_OBS], [1000, T_NETHER]],
  10: [[260, T_BRICK], [520, T_BRICK_CRACK], [700, T_STONE], [820, T_BRICK_MOSSY], [940, T_COBBLE], [1000, T_BRICK_CRACK]],
  11: [[260, T_DIRT], [450, T_COBBLE], [620, T_STONE], [800, T_COAL], [880, T_IRON], [960, T_GRAVEL_FLOOR], [1000, T_COBBLE]],
  12: [[470, T_MOSSY], [940, T_COBBLE], [1000, T_BRICK_MOSSY]],
  13: [[440, T_BRICK], [700, T_STONE], [840, T_BRICK_CRACK], [880, T_IRONB], [1000, T_BRICK]],
  14: [[640, T_NBRICK], [920, T_NBRICK], [960, T_NETHER], [1000, T_NBRICK]],
  15: [[300, T_BRICK], [520, T_BRICK_MOSSY], [700, T_BRICK_CRACK], [880, T_STONE], [940, T_CARVED], [1000, T_BRICK]]
};
function wallType(style, i, j, k) { return pickW(ih(i, j, k, 7), WALLS[style] || WALLS[1]); }

export const isOpen = (t) => t === T_AIR || t === T_WATER || t === T_LAVA;
const TEX_OF = {
  [T_STONE]: ["stone"], [T_COBBLE]: ["cobblestone"], [T_MOSSY]: ["cobblestone_mossy"], [T_BRICK]: ["stonebrick"],
  [T_BRICK_MOSSY]: ["stonebrick_mossy"], [T_BRICK_CRACK]: ["stonebrick_cracked"], [T_GRAVEL_FLOOR]: ["stone", "gravel"],
  [T_COAL]: ["coal_ore"], [T_IRON]: ["iron_ore"], [T_OBS]: ["obsidian"], [T_BEDROCK]: ["bedrock"], [T_NETHER]: ["netherrack"],
  [T_GLOW]: ["glowstone"], [T_BRIDGE]: ["stonebrick"], [T_NBRICK]: ["nether_brick"], [T_SOUL]: ["soul_sand"],
  [T_SHELF]: ["bookshelf", "planks_oak", "planks_oak"], [T_PLANK]: ["planks_oak"], [T_LOG]: ["log_oak", "log_oak_top", "log_oak_top"],
  [T_DIRT]: ["dirt"],
  [T_DISP_PX]: ["furnace_side", "furnace_top", "furnace_top"], [T_DISP_NX]: ["furnace_side", "furnace_top", "furnace_top"],
  [T_DISP_PZ]: ["furnace_side", "furnace_top", "furnace_top"], [T_DISP_NZ]: ["furnace_side", "furnace_top", "furnace_top"],
  [T_GOLD]: ["gold_block"], [T_DIAM]: ["diamond_block"], [T_LAPIS]: ["lapis_block"], [T_EMERALD]: ["emerald_block"],
  [T_IRONB]: ["iron_block"], [T_CARVED]: ["stonebrick_carved"]
};
// Blocks with one special face: the world direction (x, z) that shows it, and its texture.
const FRONT = { [T_DISP_PX]: [1, 0], [T_DISP_NX]: [-1, 0], [T_DISP_PZ]: [0, 1], [T_DISP_NZ]: [0, -1] };

export function buildGrid(lay) {
  // Bounds from every leg's corners, with room for pockets and passages.
  let xmin = 1e9, xmax = -1e9, zmin = 1e9, zmax = -1e9, ymin = 0, ymax = 0;
  for (const leg of lay.legs) {
    const ext = leg.hw + 14;
    for (const a of [-ext, ext]) for (const b of [leg.cs - 2, leg.ce + 2]) {
      const [x, z] = legMap(leg, a, b);
      xmin = Math.min(xmin, x); xmax = Math.max(xmax, x); zmin = Math.min(zmin, z); zmax = Math.max(zmax, z);
    }
    ymin = Math.min(ymin, Math.min(leg.y0, leg.yEnd) - (leg.kind === "chasm" ? CHASM_DEPTH + 3 : leg.kind === "fortress" ? FORT_DEPTH + 3 : 4));
    ymax = Math.max(ymax, leg.y0 + leg.ht + 9);
  }
  const i0 = Math.floor(xmin) - 2, i1 = Math.ceil(xmax) + 2, k0 = Math.floor(zmin) - 2, k1 = Math.ceil(zmax) + 2;
  const j0 = ymin - 2, j1 = ymax;
  const a = { i0, NI: i1 - i0 + 1, k0, NK: k1 - k0 + 1, j0, NJ: j1 - j0 + 1 };
  a.g = new Uint8Array(a.NK * a.NJ * a.NI).fill(T_WALL);
  a.st = new Uint8Array(a.g.length);
  a.lay = lay;
  const inb = (i, j, k) => i >= a.i0 && i < a.i0 + a.NI && j >= a.j0 && j < a.j0 + a.NJ && k >= a.k0 && k < a.k0 + a.NK;
  const idx = (i, j, k) => ((k - a.k0) * a.NJ + (j - a.j0)) * a.NI + (i - a.i0);
  const get = (i, j, k) => (inb(i, j, k) ? a.g[idx(i, j, k)] : T_BEDROCK);
  const set = (i, j, k, t) => { if (inb(i, j, k)) a.g[idx(i, j, k)] = t; };
  a.get = get; a.set = set; a.inb = inb;
  a.solid = (i, j, k) => !isOpen(get(i, j, k));
  a.torches = []; a.decor = []; a.sources = []; a.emit = []; a.spots = { water: [], lava: [], fire: [], drip: [], passages: [] };
  a.lavaCells = []; a.waterRects = []; a.lavaRects = []; a.holes = [];

  const decor = (o) => a.decor.push(o);
  // Local cell setter: leg, local cell (lu, lv), height j.
  const L = (leg, lu, lv, j, t) => { const [i, k] = legCell(leg, lu, lv); set(i, j, k, t); };
  const LG = (leg, lu, lv, j) => { const [i, k] = legCell(leg, lu, lv); return get(i, j, k); };
  const W3 = (leg, aa, bb, y) => { const [x, z] = legMap(leg, aa, bb); return [x, y, z]; };
  const dirw = (leg, fa, fb) => { const p = legMap(leg, fa, fb), q = legMap(leg, 0, 0); return [p[0] - q[0], p[1] - q[1]]; };

  // A wall torch on a block face: the wall cell (local), and the side it faces (local a direction +-1).
  function torchAt(leg, lu, lv, j, faceA, opts = {}) {
    const [fx, fz] = dirw(leg, faceA, 0);
    const [i, k] = legCell(leg, lu, lv);
    if (!a.solid(i, j, k) || a.solid(i + fx, j, k + fz)) return false;
    pushTorch(i, j, k, fx, fz, opts);
    return true;
  }
  function torchAtB(leg, lu, lv, j, faceB, opts = {}) {
    const [fx, fz] = dirw(leg, 0, faceB);
    const [i, k] = legCell(leg, lu, lv);
    if (!a.solid(i, j, k) || a.solid(i + fx, j, k + fz)) return false;
    pushTorch(i, j, k, fx, fz, opts);
    return true;
  }
  function pushTorch(i, j, k, fx, fz, opts = {}) {
    const cx = i + 0.5 + fx * 0.5, cz = k + 0.5 + fz * 0.5;
    const tip = [cx + fx * 0.35, j + 0.845, cz + fz * 0.35];
    a.torches.push({ i, j, k, fx, fz, x: tip[0], y: tip[1], z: tip[2], cx, cz, ...opts });
    const s = opts.I != null ? opts.I : 3.4;
    a.sources.push({ x: tip[0] + fx * 0.2, y: tip[1] + 0.15, z: tip[2] + fz * 0.2, c: [1.0, 0.56, 0.24], I: s, R: 12, dyn: true });
    a.emit.push({ k: "torch", x: tip[0], y: tip[1] + 0.02, z: tip[2] });
  }

  // 1. Carve every leg's corridor, with its floor, ceiling and the style of its walls.
  for (const leg of lay.legs) {
    const { hw, ht, y0 } = leg;
    // Style of the surrounding stone, marked before carving.
    for (let lv = leg.cs - 4; lv < leg.ce + 4; lv++) for (let lu = -hw - 4; lu < hw + 4; lu++) {
      const [i, k] = legCell(leg, lu, lv);
      const lo = leg.kind === "chasm" ? y0 - CHASM_DEPTH - 3 : leg.kind === "fortress" ? y0 - FORT_DEPTH - 3 : Math.min(y0, leg.yEnd) - 4, hi = y0 + ht + 3;
      for (let j = lo; j <= hi; j++) if (inb(i, j, k) && !a.st[idx(i, j, k)]) a.st[idx(i, j, k)] = leg.style;
    }
  }
  for (const leg of lay.legs) {
    const { hw, ht, y0, kind } = leg;
    for (let lv = leg.cs; lv < leg.ce; lv++) {
      const yf = floorTop(leg, lv);
      for (let lu = -hw; lu < hw; lu++) {
        let floorT = T_BRICK, airFrom = yf;
        const hv = ih(lu, lv, leg.rid, 3);
        const centre = lu === -1 || lu === 0;
        if (kind === "crypt") floorT = centre ? (hv < 250 ? T_BRICK_CRACK : hv < 420 ? T_BRICK_MOSSY : T_BRICK) : T_GRAVEL_FLOOR;
        else if (kind === "mine") floorT = centre && hv < 500 ? T_DIRT : T_GRAVEL_FLOOR;
        else if (kind === "ossuary") floorT = hv < 300 ? T_BRICK_CRACK : hv < 420 ? T_GRAVEL_FLOOR : T_BRICK;
        else if (kind === "flood") {
          if (lu >= -1 && lu <= 0) floorT = hv < 300 ? T_BRICK_MOSSY : T_BRICK;
          else { floorT = T_GRAVEL_FLOOR; airFrom = yf - 1; }
        } else if (kind === "dungeon") floorT = hv < 650 ? T_MOSSY : T_COBBLE;
        else if (kind === "library") floorT = hv < 160 ? T_BRICK_CRACK : T_BRICK;
        else if (kind === "chasm") {
          if (lu >= -2 && lu < 2) floorT = T_BRIDGE;
          else { floorT = T_AIR; airFrom = y0 - CHASM_DEPTH; }
        } else if (kind === "fortress") {
          if (lu >= -2 && lu < 2) floorT = T_NBRICK;
          else { floorT = T_AIR; airFrom = y0 - FORT_DEPTH; }
        } else if (kind === "catacomb") floorT = centre ? (hv < 220 ? T_BRICK_CRACK : T_BRICK) : (hv < 500 ? T_COBBLE : T_GRAVEL_FLOOR);
        else if (kind === "spidermine") floorT = hv < 420 ? T_GRAVEL_FLOOR : hv < 700 ? T_DIRT : T_COBBLE;
        else if (kind === "temple") floorT = hv < 520 ? T_MOSSY : hv < 560 ? T_BRICK_MOSSY : T_COBBLE;
        else if (kind === "vault") floorT = centre && lv % 4 === 0 ? T_IRONB : (hv < 250 ? T_BRICK_CRACK : T_BRICK);
        else if (kind === "stronghold") floorT = hv < 560 ? T_BRICK : hv < 760 ? T_BRICK_MOSSY : hv < 900 ? T_BRICK_CRACK : T_STONE;
        else if (kind === "stairs") floorT = hv < 200 ? T_BRICK_CRACK : T_BRICK;
        else if (kind === "deep") {
          if (lu === -hw || lu === hw - 1) { floorT = T_LAVA; airFrom = yf - 1; }
          else floorT = hv < 560 ? T_SOUL : hv < 840 ? T_NETHER : T_NBRICK;
        }
        for (let j = airFrom; j < yf + ht; j++) L(leg, lu, lv, j, T_AIR);
        if ((kind === "chasm" || kind === "fortress") && floorT === T_AIR) {
          const dp = kind === "chasm" ? CHASM_DEPTH : FORT_DEPTH;
          L(leg, lu, lv, y0 - dp - 1, T_BEDROCK);
          L(leg, lu, lv, y0 - dp, T_LAVA);
          leg.lavaCells.push([lu, lv]);
        } else if (kind === "deep" && floorT === T_LAVA) {
          L(leg, lu, lv, yf - 1, T_LAVA); L(leg, lu, lv, yf - 2, T_OBS);
        } else {
          L(leg, lu, lv, airFrom - 1, floorT === T_AIR ? T_BRICK : floorT);
          if (kind === "flood" && airFrom < yf) { L(leg, lu, lv, yf - 1, T_AIR); L(leg, lu, lv, airFrom - 1, T_GRAVEL_FLOOR); }
        }
      }
    }
  }

  // Alcoves: a pocket two cells deep with a solid back, framed by two pillars and a lintel.
  const free = (leg) => ({ 1: new Set(), "-1": new Set() }); // rows used on each side
  for (const leg of lay.legs) {
    leg.used = free(leg);
    const { hw, y0, kind } = leg;
    for (const s of leg.slots) {
      const sd = s.side, inner = sd > 0 ? [hw, hw + 1] : [-hw - 1, -hw - 2];
      const pil = sd > 0 ? hw - 1 : -hw;
      for (let lv = s.lvc - 1; lv <= s.lvc + 1; lv++) for (let j = y0; j <= y0 + 3; j++) { L(leg, inner[0], lv, j, T_AIR); L(leg, inner[1], lv, j, T_AIR); }
      const pb = kind === "chasm" ? y0 - CHASM_DEPTH + 1 : kind === "fortress" ? y0 - FORT_DEPTH + 1 : kind === "flood" ? y0 - 1 : kind === "deep" ? y0 - 1 : y0;
      for (const lv of [s.lvc - 2, s.lvc + 2]) for (let j = pb; j <= y0 + 2; j++) {
        L(leg, pil, lv, j, kind === "deep" || kind === "fortress" ? T_NBRICK : (j === y0 ? T_BRICK_MOSSY : T_BRICK));
      }
      for (let lv = s.lvc - 2; lv <= s.lvc + 2; lv++) L(leg, pil, lv, y0 + 3, kind === "deep" || kind === "fortress" ? T_NBRICK : T_BRICK);
      for (let lv = s.lvc - 3; lv <= s.lvc + 3; lv++) leg.used[sd].add(lv);
      // The torch: on the corridor face of the rear pillar, level with the lintel's underside.
      s.torch = false;
    }
  }

  // 2. Passages: a narrow corridor off the wall, checked against everything already carved.
  for (const leg of lay.legs) {
    for (const p of leg.passages) {
      const { side, lv } = p, hw = leg.hw, y0 = leg.y0;
      const a0 = side > 0 ? hw : -hw - 1;
      let clear = true;
      for (let q = 0; q <= p.len + 1 && clear; q++) for (let w = -1; w <= 2 && clear; w++) for (let j = y0 - 1; j <= y0 + 3 && clear; j++) {
        const lu = side > 0 ? hw + q : -hw - 1 - q;
        if (LG(leg, lu, lv + w, j) !== T_WALL) clear = false;
      }
      if (!clear) continue;
      p.ok = true;
      for (let q = 0; q < p.len; q++) {
        const lu = side > 0 ? hw + q : -hw - 1 - q;
        for (let w = 0; w < 2; w++) {
          for (let j = y0; j <= y0 + 2; j++) L(leg, lu, lv + w, j, T_AIR);
          L(leg, lu, lv + w, y0 - 1, leg.kind === "deep" ? T_NETHER : T_COBBLE);
        }
      }
      for (let q = -1; q <= p.len + 1; q++) for (let w = -2; w <= 3; w++) {
        const lu = side > 0 ? hw + q : -hw - 1 - q;
        const [ci, ck] = legCell(leg, lu, lv + w);
        for (let j = y0 - 3; j <= y0 + 5; j++) if (inb(ci, j, ck)) { const ix = idx(ci, j, ck); if (a.st[ix] === 0 || a.st[ix] === leg.style) a.st[ix] = leg.style; }
      }
      const [mx, my, mz] = W3(leg, side * (hw + 0.5), lv + 1, y0);
      const [ex, , ez] = W3(leg, side * (hw + p.len - 0.5), lv + 1, y0);
      p.mouth = [mx, my, mz]; p.end = [ex, my, ez];
      const dd = dirw(leg, -side, 0);
      a.spots.passages.push({ mouth: [mx, my, mz], end: [ex, my, ez], dir: dd, leg: leg.idx, side, s: null, rowsB: lv + 1 });
      // A torch at the far end, on its wall, and a cobweb or two.
      const luEnd = side > 0 ? hw + p.len : -hw - 1 - p.len;
      torchAt(leg, luEnd, lv, y0 + 1, -side, { I: 2.6 });
      decor({ t: "web", x: ex, y: y0 + 2.5, z: ez, ry: Math.PI / 2 + legYaw(leg), w: 1.1 });
      lay.corners.push({ kind: "passage", x: mx, y: y0, z: mz, dx: dd[0], dz: dd[1], side, leg: leg.idx });
    }
  }

  // 3. Holes in the ceiling: the violet sky cracks.
  for (const leg of lay.legs) {
    for (const hb of leg.holesAt) {
      const yTop = leg.y0 + leg.ht;
      for (let lv = hb - 1; lv <= hb + 1; lv++) for (let lu = -1; lu <= 1; lu++) for (let j = yTop; j <= a.j0 + a.NJ - 1; j++) L(leg, lu, lv, j, T_AIR);
      const [x, , z] = W3(leg, 0.5, hb + 0.5, 0);
      a.holes.push({ x: x - 0.0, z, y: yTop, leg: leg.idx, hb });
      for (let q = 0; q < 3; q++) a.sources.push({ x: x + (q - 1) * 0.9, y: yTop + 0.6, z: z + (q % 2 ? 0.6 : -0.6), c: [0.55, 0.42, 0.95], I: 3.4, R: 12, sky: true });
    }
  }

  // 4. Set dressing, segment by segment.
  for (const leg of lay.legs) dressLeg(a, lay, leg, { L, LG, W3, dirw, torchAt, torchAtB, pushTorch, decor, legCell, set, get });

  // 5. A torch for each stone: on the corridor face of the rear pillar. Fewer in the cold entrance and the ossuary.
  for (const leg of lay.legs) for (const s of leg.slots) {
    const { hw, y0, kind } = leg;
    const every = kind === "crypt" ? 2 : kind === "ossuary" ? 2 : 1;
    if (s.i >= lay.count) continue;
    // The alcove's own torch, on the side wall of the pocket beside the stone.
    torchAtB(leg, s.side > 0 ? hw + 1 : -hw - 2, s.lvc + 2, y0 + 2, -1, { I: 2.4 });
    if (s.i % every && !(kind === "crypt" && s.i === 0)) continue;
    const pil = s.side > 0 ? hw - 1 : -hw;
    const I = kind === "crypt" ? 2.6 : 3.4;
    if (torchAt(leg, pil, s.lvc + 2, y0 + 2, -s.side, { I })) s.torch = true;
    else if (torchAt(leg, pil, s.lvc - 2, y0 + 2, -s.side, { I })) s.torch = true;
  }

  // Lava sources and lava planes from the cells recorded by the legs.
  for (const leg of lay.legs) {
    if (leg.kind === "chasm" || leg.kind === "fortress") {
      const yL = leg.y0 - (leg.kind === "chasm" ? CHASM_DEPTH : FORT_DEPTH) + 0.9;
      const xs = [];
      for (const [lu, lv] of leg.lavaCells) if (lu % 3 === 0 && lv % 3 === 0) xs.push([lu, lv]);
      for (const [lu, lv] of xs) { const [x, , z] = W3(leg, lu + 0.5, lv + 0.5, 0); a.sources.push({ x, y: yL + 0.6, z, c: [1.0, 0.36, 0.08], I: leg.kind === "fortress" ? 14 : 9, R: 14, lava: true, dyn: true }); }
      const [xa, , za] = W3(leg, -leg.hw, leg.cs, 0), [xb, , zb] = W3(leg, leg.hw, leg.ce, 0);
      a.lavaRects.push({ x0: Math.min(xa, xb), x1: Math.max(xa, xb), z0: Math.min(za, zb), z1: Math.max(za, zb), y: yL - 0.15 });
      a.spots.lava.push([ (xa + xb) / 2, yL, (za + zb) / 2 ]);
    }
  }
  if (lay.sOf) { for (const c of lay.corners) if (c.s == null) c.s = lay.sOf(c.x, c.y + 1.5, c.z); for (const p of a.spots.passages) p.s = lay.sOf(p.mouth[0], p.mouth[1] + 1.5, p.mouth[2]); }
  return a;
}

// ---- the dressing of each segment (grid blocks, torches, decor lists) ----------------------------------
function dressLeg(a, lay, leg, H) {
  const { L, LG, W3, dirw, torchAt, torchAtB, decor, legCell, set, get } = H;
  const { hw, y0, kind, ht } = leg;
  const rowsFree = (side, lv) => !leg.used[side].has(lv) && !leg.passages.some(p => p.ok && p.side === side && lv >= p.lv - 1 && lv <= p.lv + 2);
  const lo = leg.b0 + leg.pre, hi = leg.contentEnd;
  const yaw = legYaw(leg);
  const rnd = (i, s) => ih(i, leg.rid, s, 11) / 1000;
  const wallCell = (side) => (side > 0 ? hw : -hw - 1);
  const edgeCell = (side) => (side > 0 ? hw - 1 : -hw);

  if (kind === "crypt") {
    // The gate arch at the entrance: iron bars between two brick piers and a lintel.
    for (const lu of [-hw, hw - 1]) for (let j = y0; j <= y0 + 2; j++) { L(leg, lu, 3, j, T_BRICK); L(leg, lu, 4, j, T_BRICK); }
    for (let lu = -hw; lu < hw; lu++) { L(leg, lu, 3, y0 + 3, T_BRICK); L(leg, lu, 4, y0 + 3, T_BRICK); }
    for (const sd of [-1, 1]) torchAt(leg, edgeCell(sd), 4, y0 + 2, -sd, { I: 3.0 });
    // The two pier torches face the corridor; the lintel and the piers frame the first view.
    const [bx, by, bz] = W3(leg, 0, 4.0, y0);
    decor({ t: "bars", x: bx, y: by + 2.5, z: bz, ry: yaw, w: hw * 2 - 0.3, h: 1.0 });
    for (let q = 0; q < 6; q++) decor({ t: "web", x: W3(leg, (q % 2 ? 1 : -1) * (hw - 0.2), 4 + q * 3.2, 0)[0], y: y0 + 3.4, z: W3(leg, (q % 2 ? 1 : -1) * (hw - 0.2), 4 + q * 3.2, 0)[2], ry: yaw + (q % 2 ? -1 : 1) * Math.PI / 4, w: 1.4 });
    for (let lv = lo; lv < hi; lv += 3) {
      const sd = lv % 2 ? 1 : -1;
      if (rowsFree(sd, lv)) { const [x, y, z] = W3(leg, sd * (hw - 0.04), lv + 0.5, y0 + 2.2); decor({ t: "vine", x, y, z, ry: yaw + sd * Math.PI / 2, w: 1.0, h: 1.4 }); }
    }
  }

  if (kind === "mine") {
    // Support frames: a log post at the edge of the free stretch and a plank beam across the roof.
    for (const s of leg.slots) {
      const lv = s.lvc + 4, sd = s.side;
      if (!rowsFree(sd, lv) || !rowsFree(sd, lv + 1)) continue;
      for (let j = y0; j <= y0 + 2; j++) L(leg, edgeCell(sd), lv, j, T_LOG);
      for (let lu = -hw; lu < hw; lu++) if (LG(leg, lu, lv, y0 + 3) === T_AIR) L(leg, lu, lv, y0 + 3, T_PLANK);
      torchAt(leg, wallCell(-sd), lv, y0 + 2, sd, { I: 2.9 });
      decor({ t: "web", x: W3(leg, -sd * (hw - 0.3), lv + 0.5, 0)[0], y: y0 + 3.1, z: W3(leg, -sd * (hw - 0.3), lv + 0.5, 0)[2], ry: yaw + Math.PI / 4, w: 1.5 });
    }
    // Rails down the middle, a minecart, a heap of rubble where the roof gave way.
    for (let lv = lo - 2; lv < hi; lv++) { const [x, y, z] = W3(leg, 0, lv + 0.5, y0); decor({ t: "rail", x, y: y + 0.02, z, ry: leg.h === "N" ? 0 : Math.PI / 2 }); }
    const mid = Math.round((lo + hi) / 2);
    const [cx, cy, cz] = W3(leg, 0.25, mid + 0.5, y0);
    decor({ t: "cart", x: cx, y: cy + 0.06, z: cz, ry: yaw + 0.12 });
    const rub = Math.min(hi - 3, lo + 3);
    for (let lv = rub; lv < rub + 2; lv++) for (let lu = -hw; lu < -hw + 2; lu++) {
      if (rowsFree(-1, lv) && LG(leg, lu, lv, y0) === T_AIR) { L(leg, lu, lv, y0, rnd(lu + lv, 1) < 0.5 ? T_COBBLE : T_GRAVEL_FLOOR); if (lu === -hw) L(leg, lu, lv, y0 + 1, T_COBBLE); }
    }
    for (let q = 0; q < 5; q++) { const lv = lo + 1 + q * 3; const sd = q % 2 ? 1 : -1; const [x, y, z] = W3(leg, sd * 1.6, lv + 0.5, y0); decor({ t: "rubble", x, y, z, s: 0.35 + rnd(q, 2) * 0.3, ry: q }); }
    // A beam that has come down, one end on the floor.
    const [fx, fy, fz] = W3(leg, 1.2, hi - 2.5, y0 + 1.3);
    decor({ t: "beam", x: fx, y: fy, z: fz, ry: yaw + 0.3, rz: 0.75, len: 3.1 });
  }

  if (kind === "ossuary") {
    // Wall niches with skulls and bones, two high, in the free stretches.
    for (const sd of [-1, 1]) for (let lv = lo + 1; lv < hi; lv++) {
      if (!rowsFree(sd, lv) || !rowsFree(sd, lv - 1) || !rowsFree(sd, lv + 1)) continue;
      if ((lv + (sd > 0 ? 1 : 0)) % 2) continue;
      const lu = wallCell(sd), [ci, ck] = legCell(leg, lu, lv);
      for (let j = y0 + 1; j <= y0 + 2; j++) if (a.solid(ci, j, ck)) L(leg, lu, lv, j, T_AIR);
      for (let j = y0 + 1; j <= y0 + 2; j++) {
        const [x, y, z] = W3(leg, sd * (hw + 0.5), lv + 0.5, y0);
        const r = rnd(lv * 3 + j, sd + 5);
        if (r < 0.78) decor({ t: "skull", x, y: j, z, ry: yaw + sd * Math.PI / 2 + (r - 0.4) * 0.8 });
        if (r > 0.45) decor({ t: "bone", x: x + (r - 0.6) * 0.2, y: j + 0.02, z: z + 0.1, ry: r * 6 });
      }
      const [wx, wy, wz] = W3(leg, sd * (hw + 0.95), lv + 0.5, y0 + 2.5);
      if (rnd(lv, 9) < 0.5) decor({ t: "web", x: W3(leg, sd * (hw + 0.1), lv + 0.5, 0)[0], y: y0 + 2.7, z: W3(leg, sd * (hw + 0.1), lv + 0.5, 0)[2], ry: yaw + sd * Math.PI / 2, w: 0.9 });
      void wx; void wy; void wz;
    }
    // Bones across the floor, cobwebs in the roof.
    for (let q = 0; q < 26; q++) {
      const lv = lo + 0.5 + rnd(q, 3) * (hi - lo), lu = (rnd(q, 4) - 0.5) * (hw * 1.7);
      const [x, y, z] = W3(leg, lu, lv, y0);
      decor({ t: "bone", x, y: y + 0.02, z, ry: rnd(q, 5) * 6.28 });
    }
    for (let q = 0; q < 8; q++) {
      const lv = lo + 1 + q * ((hi - lo) / 8), sd = q % 2 ? 1 : -1; const [x, , z] = W3(leg, sd * (hw - 0.3), lv, 0);
      decor({ t: "web", x, y: y0 + 3.4, z, ry: yaw + sd * Math.PI / 4, w: 1.6 });
    }
    // A heap of skulls on the floor by the middle of the hall.
    const [hx, hy, hz] = W3(leg, -1.9, (lo + hi) / 2 + 2, y0);
    for (let q = 0; q < 7; q++) decor({ t: "skull", x: hx + (rnd(q, 6) - 0.5) * 0.9, y: hy + (q > 3 ? 0.46 : 0), z: hz + (rnd(q, 7) - 0.5) * 0.9, ry: rnd(q, 8) * 6.28 });
  }

  if (kind === "flood") {
    // Water on the sides of the causeway, lily pads, free columns, drips from the roof.
    const [xa, , za] = W3(leg, -hw, leg.cs + 1, 0), [xb, , zb] = W3(leg, hw, leg.ce - 1, 0);
    a.waterRects.push({ x0: Math.min(xa, xb), x1: Math.max(xa, xb), z0: Math.min(za, zb), z1: Math.max(za, zb), y: y0 - 0.3 });
    a.spots.water.push(W3(leg, 0, (lo + hi) / 2, y0));
    for (let lv = lo + 1; lv < hi; lv += 6) for (const lu of [-3, 2]) {
      const sd = lu < 0 ? -1 : 1;
      if (!rowsFree(sd, lv) || !rowsFree(sd, lv + 1)) continue;
      for (let j = y0 - 1; j < y0 + ht; j++) L(leg, lu, lv, j, j === y0 - 1 ? T_BRICK_MOSSY : (rnd(lv + j, lu) < 0.3 ? T_BRICK_MOSSY : T_BRICK));
      torchAt(leg, lu, lv, y0 + 3, lu < 0 ? 1 : -1, { I: 3.0 });
    }
    for (let q = 0; q < 34; q++) {
      const lv = lo + rnd(q, 12) * (hi - lo), lu = (rnd(q, 13) < 0.5 ? -1 : 1) * (1.3 + rnd(q, 14) * (hw - 2.0));
      const [x, y, z] = W3(leg, lu, lv, y0 - 0.28); decor({ t: "lily", x, y, z, ry: rnd(q, 15) * 6.28 });
    }
    for (let q = 0; q < 14; q++) {
      const lv = lo + 1 + rnd(q, 16) * (hi - lo - 2), lu = (rnd(q, 17) - 0.5) * 2 * (hw - 1.4);
      const [x, , z] = W3(leg, lu, lv, 0);
      a.emit.push({ k: "drip", x, y: y0 + ht - 0.1, z, floorY: y0 - 0.3 });
      a.spots.drip.push([x, y0 + 1, z]);
    }
    for (let q = 0; q < 8; q++) { const sd = q % 2 ? 1 : -1; const lv = lo + 1 + q * ((hi - lo) / 8); const [x, , z] = W3(leg, sd * (hw - 0.2), lv, 0); decor({ t: "vine", x, y: y0 + 3.3, z, ry: yaw + sd * Math.PI / 2, w: 1.0, h: 1.8 }); }
  }

  if (kind === "dungeon") {
    // The spawner on a mossy pedestal, free columns, four torches on the walls.
    const mid = Math.round((leg.b0 + leg.ce) / 2) - 1;
    for (const lu of [-3, -2]) for (const lv of [mid, mid + 1]) L(leg, lu, lv, y0, T_MOSSY);
    const [sx, sy, sz] = W3(leg, -2.0, mid + 1.0, y0 + 1);
    decor({ t: "spawner", x: sx, y: sy, z: sz });
    a.sources.push({ x: sx, y: sy + 0.8, z: sz, c: [1.0, 0.52, 0.22], I: 3.4, R: 11, dyn: true });
    a.emit.push({ k: "spawner", x: sx, y: sy + 1.0, z: sz });
    a.spots.fire.push([sx, sy + 0.5, sz]);
    for (let lv = leg.b0 + leg.pre + 3, q = 0; lv < leg.contentEnd; lv += 4, q++) for (const lu of [-4, 3]) {
      for (let j = y0; j < y0 + ht; j++) L(leg, lu, lv, j, ih(lu, lv, j, 5) < 300 ? T_MOSSY : T_COBBLE);
      if (q % 2 === 0) torchAt(leg, lu, lv, y0 + 2, lu < 0 ? 1 : -1, { I: 3.0 });
    }
    for (const sd of [-1, 1]) for (const lv of [leg.b0 + 1, leg.contentEnd + 2]) torchAt(leg, wallCell(sd), lv, y0 + 2, -sd, { I: 3.4 });
    for (let q = 0; q < 10; q++) {
      const lv = lo + 1 + q * ((hi - lo) / 10), sd = q % 2 ? 1 : -1; const [x, , z] = W3(leg, sd * (hw - 0.25), lv, 0);
      decor({ t: "vine", x, y: y0 + 2.2 + (q % 3) * 0.2, z, ry: yaw + sd * Math.PI / 2, w: 1.2, h: 1.6 });
      decor({ t: "web", x: W3(leg, -sd * (hw - 0.3), lv + 1, 0)[0], y: y0 + ht - 0.6, z: W3(leg, -sd * (hw - 0.3), lv + 1, 0)[2], ry: yaw + Math.PI / 4, w: 1.6 });
    }
  }

  if (kind === "library") {
    // Bookshelves three high along the free walls, beams across the roof, bars over the passage mouth.
    for (const sd of [-1, 1]) for (let lv = lo; lv < hi + 1; lv++) {
      if (!rowsFree(sd, lv)) continue;
      if (leg.passages.some(p => p.ok && p.side === sd && lv >= p.lv - 2 && lv <= p.lv + 3)) continue;
      const lu = edgeCell(sd);
      for (let j = y0; j <= y0 + 2; j++) if (LG(leg, lu, lv, j) === T_AIR) L(leg, lu, lv, j, T_SHELF);
      if (lv % 5 === 2) torchAt(leg, wallCell(sd), lv, y0 + 3, -sd, { I: 3.4 });
    }
    for (let lv = lo + 1; lv < hi; lv += 4) {
      const [x, y, z] = W3(leg, 0, lv + 0.5, y0 + ht - 0.2);
      decor({ t: "beam", x, y, z, ry: yaw, rz: 0, len: hw * 2 - 0.3 });
    }
    for (const p of leg.passages) if (p.ok) {
      const [x, y, z] = W3(leg, p.side * (hw + 0.1), p.lv + 1, y0);
      decor({ t: "bars", x, y: y + 1.0, z, ry: yaw + Math.PI / 2, w: 2.0, h: 2.0 });
    }
    for (let q = 0; q < 9; q++) {
      const lv = lo + q * ((hi - lo) / 9), sd = q % 2 ? 1 : -1; const [x, , z] = W3(leg, sd * (hw - 0.3), lv, 0);
      decor({ t: "web", x, y: y0 + ht - 0.6, z, ry: yaw + sd * Math.PI / 4, w: 1.6 });
    }
  }

  if (kind === "chasm") {
    // Parapet posts along the bridge with torches, obsidian at either end.
    // No rails: the bridge is four wide and open on both sides, so the drop and the lava read from the walk.
    a.spots.fire.push(...a.spots.lava);
  }


  // ---- the six segments of round 5 ----
  const dispType = (dx, dz) => (dx > 0 ? T_DISP_PX : dx < 0 ? T_DISP_NX : dz > 0 ? T_DISP_PZ : T_DISP_NZ);
  const webAt = (aa, bb, y, ry, w, h, rep) => { const [x, , z] = W3(leg, aa, bb, 0); decor({ t: "web", x, y, z, ry, w, h, rep: !!rep }); };
  const freeRow = (lv) => rowsFree(-1, lv) && rowsFree(1, lv) && rowsFree(-1, lv + 1) && rowsFree(1, lv + 1);

  if (kind === "catacomb") {
    // Loculi: three niches high, two deep, in every second row of the free walls; each holds a skull and bones, the
    // upper ones a cobweb. Brick arches across the hall every nine rows.
    for (const sd of [-1, 1]) for (let lv = lo; lv < hi; lv++) {
      if (!rowsFree(sd, lv) || !rowsFree(sd, lv - 1) || !rowsFree(sd, lv + 1)) continue;
      if ((lv + (sd > 0 ? 1 : 0)) % 2) continue;
      const lu = wallCell(sd), lu2 = lu + sd;
      for (let j = y0; j <= y0 + 2; j++) { L(leg, lu, lv, j, T_AIR); L(leg, lu2, lv, j, T_AIR); }
      for (let j = y0; j <= y0 + 2; j++) {
        const [x, , z] = W3(leg, sd * (hw + 0.5), lv + 0.5, y0);
        const r = rnd(lv * 7 + j, sd + 20);
        if (r < 0.7) decor({ t: "skull", x, y: j, z, ry: yaw + sd * Math.PI / 2 + (r - 0.35) * 0.9 });
        if (r > 0.3) decor({ t: "bone", x: x + (r - 0.6) * 0.3, y: j + 0.02, z: z + 0.15, ry: r * 7 });
        if (j === y0 + 1 && ih(lv, leg.rid, sd + 3, 61) < 400) a.sources.push({ x: x + sd * -0.3, y: j + 0.6, z, c: [1.0, 0.72, 0.4], I: 1.5, R: 6 });
        if (j === y0 + 2 && r > 0.55) { const [wx, , wz] = W3(leg, sd * (hw + 0.1), lv + 0.5, 0); decor({ t: "web", x: wx, y: j + 0.7, z: wz, ry: yaw + sd * Math.PI / 2, w: 0.9 }); }
      }
    }
    for (const sd of [-1, 1]) for (let lv = lo + 1; lv < hi; lv += 6) if (lv % 2 !== (sd > 0 ? 0 : 1) && rowsFree(sd, lv) && rowsFree(sd, lv - 1) && rowsFree(sd, lv + 1)) torchAt(leg, wallCell(sd), lv, y0 + 2, -sd, { I: 2.6 });
    for (let lv = lo + 4; lv < hi - 2; lv += 9) {
      for (const sd of [-1, 1]) if (rowsFree(sd, lv)) {
        for (let j = y0; j <= y0 + 2; j++) if (LG(leg, edgeCell(sd), lv, j) === T_AIR) L(leg, edgeCell(sd), lv, j, j === y0 ? T_BRICK_MOSSY : T_BRICK);
        torchAt(leg, edgeCell(sd), lv, y0 + 2, -sd, { I: 2.7 });
      }
      for (let lu = -hw; lu < hw; lu++) if (LG(leg, lu, lv, y0 + 3) === T_AIR) L(leg, lu, lv, y0 + 3, T_BRICK);
      for (const sd of [-1, 1]) webAt(sd * (hw - 0.8), lv + 0.5, y0 + 2.45, yaw, 1.3);
    }
    for (let q = 0; q < 16; q++) { const lv = lo + 0.5 + rnd(q, 3) * (hi - lo), lu = (rnd(q, 4) - 0.5) * hw * 1.6; const [x, y, z] = W3(leg, lu, lv, y0); decor({ t: "bone", x, y: y + 0.02, z, ry: rnd(q, 5) * 6.28 }); }
    for (let q = 0; q < 10; q++) { const lv = lo + 1 + q * ((hi - lo) / 10), sd = q % 2 ? 1 : -1; const [x, , z] = W3(leg, sd * (hw - 0.3), lv, 0); decor({ t: "web", x, y: y0 + ht - 0.6, z, ry: yaw + sd * Math.PI / 4, w: 1.6 }); }
  }

  if (kind === "spidermine") {
    // A web-choked mineshaft: close timber frames, curtains of cobweb, rails under the webs, and a cave spider spawner.
    for (let lv = lo + 1; lv < hi; lv += 4) {
      for (const sd of [-1, 1]) if (rowsFree(sd, lv)) for (let j = y0; j <= y0 + 2; j++) if (LG(leg, edgeCell(sd), lv, j) === T_AIR) L(leg, edgeCell(sd), lv, j, T_LOG);
      for (let lu = -hw; lu < hw; lu++) if (LG(leg, lu, lv, y0 + 3) === T_AIR) L(leg, lu, lv, y0 + 3, T_PLANK);
      if ((lv - lo) % 8 === 1 && rowsFree(1, lv + 1)) torchAt(leg, wallCell(1), lv + 1, y0 + 2, -1, { I: 2.4 });
    }
    for (let lv = lo - 2; lv < hi; lv++) { const [x, y, z] = W3(leg, 0, lv + 0.5, y0); decor({ t: "rail", x, y: y + 0.02, z, ry: leg.h === "N" ? 0 : Math.PI / 2 }); }
    // The curtains: half the hall each, so the walk always has a way through.
    for (let q = 0, lv = lo + 3; lv < hi - 2; lv += 5, q++) {
      const sd = q % 2 ? 1 : -1;
      webAt(sd * (hw / 2), lv + 0.5, y0 + 1.6, yaw + (q % 3 - 1) * 0.12, hw + 0.2, 3.2, true);
    }
    for (let q = 0; q < 34; q++) {
      const lv = lo + rnd(q, 30) * (hi - lo), sd = rnd(q, 31) < 0.5 ? -1 : 1;
      const lu = sd * (hw - 0.4 - rnd(q, 32) * 1.2), y = y0 + 0.5 + rnd(q, 33) * 3;
      webAt(lu, lv, y, yaw + rnd(q, 34) * 3.14, 1.3 + rnd(q, 35) * 0.5, undefined);
    }
    for (let q = 0; q < 6; q++) { const lv = lo + 1 + q * ((hi - lo) / 6), sd = q % 2 ? 1 : -1; const [x, , z] = W3(leg, sd * (hw - 0.3), lv, 0); decor({ t: "web", x, y: y0 + ht - 0.5, z, ry: yaw + sd * Math.PI / 4, w: 1.7 }); }
    const mid = Math.round((lo + hi) / 2) + 1;
    for (const lu of [-hw, -hw + 1]) for (const lv of [mid, mid + 1]) if (LG(leg, lu, lv, y0) === T_AIR) L(leg, lu, lv, y0, T_COBBLE);
    const [sx, sy, sz] = W3(leg, -hw + 1.0, mid + 1.0, y0 + 1);
    decor({ t: "spawner", x: sx, y: sy, z: sz, mob: "CaveSpider" });
    a.sources.push({ x: sx, y: sy + 0.8, z: sz, c: [0.8, 0.5, 0.45], I: 3.0, R: 10, dyn: true });
    a.emit.push({ k: "spawner", x: sx, y: sy + 1.0, z: sz });
    // The web tunnel: the side passage is full of cobweb.
    for (const p of leg.passages) if (p.ok) for (let q = 0; q < p.len; q += 1) {
      const lu = p.side * (hw + q + 0.5);
      webAt(lu, p.lv + 1, y0 + 1.1 + (q % 2) * 0.5, yaw + Math.PI / 2, 1.7, 2.1);
      if (q % 3 === 0) webAt(lu, p.lv + 1, y0 + 2.5, yaw, 1.6, undefined);
    }
  }

  if (kind === "temple") {
    // The trap hall: a tripwire across the hall between two hooks, dispensers on both walls to fire on it, three
    // stations along the way; a lever wall at the end; vines and moss everywhere.
    let lastSt = -99;
    for (let lv = lo + 2; lv < hi - 6; lv++) {
      if (lv - lastSt < 9 || !freeRow(lv - 1) || !freeRow(lv + 1) || !freeRow(lv + 2)) continue;
      lastSt = lv;
      for (const sd of [-1, 1]) {
        const wl = wallCell(sd), [dx, dz] = dirw(leg, -sd, 0);
        L(leg, wl, lv, y0 + 2, dispType(dx, dz));
        L(leg, wl, lv + 2, y0 + 1, dispType(dx, dz));
        const [hx, , hz] = W3(leg, sd * (hw - 0.05), lv + 0.5 + 0.0, 0);
        decor({ t: "hook", x: hx, y: y0 + 1.25, z: hz, ry: yaw + sd * Math.PI / 2 });
        torchAt(leg, wl, lv, y0 + 3, -sd, { I: 2.6 });
      }
      for (let lu = -hw; lu < hw; lu++) { const [x, , z] = W3(leg, lu + 0.5, lv + 0.5, 0); decor({ t: "wire", x, y: y0 + 1.22, z, ry: leg.h === "N" ? 0 : Math.PI / 2 }); }
    }
    // The levers: three on the right wall near the end, one pulled the other way.
    const lvw = hi - 3;
    for (let q = 0; q < 3; q++) {
      const lv = lvw + q;
      if (!rowsFree(1, lv)) continue;
      const [x, , z] = W3(leg, hw - 0.04, lv + 0.5, 0);
      decor({ t: "lever", x, y: y0 + 1.5, z, ry: yaw + Math.PI / 2, on: q !== 1 });
    }
    torchAt(leg, wallCell(1), lvw + 1, y0 + 3, -1, { I: 2.8 });
    for (let q = 0; q < 14; q++) {
      const lv = lo + q * ((hi - lo) / 14), sd = q % 2 ? 1 : -1; const [x, , z] = W3(leg, sd * (hw - 0.04), lv + 0.3, 0);
      if (rowsFree(sd, Math.floor(lv))) decor({ t: "vine", x, y: y0 + 2.0 + (q % 3) * 0.3, z, ry: yaw + sd * Math.PI / 2, w: 1.1, h: 1.7 });
    }
    for (let q = 0; q < 8; q++) { const lv = lo + 1 + q * ((hi - lo) / 8), sd = q % 2 ? 1 : -1; const [x, , z] = W3(leg, sd * (hw - 0.3), lv, 0); decor({ t: "vine", x, y: y0 + ht - 0.9, z, ry: yaw + sd * Math.PI / 4, w: 1.0, h: 1.6 }); }
    for (let q = 0; q < 5; q++) { const lv = lo + 1 + q * 5, sd = q % 2 ? 1 : -1; if (rowsFree(sd, lv)) { const [x, y, z] = W3(leg, sd * 2.2, lv + 0.5, y0); decor({ t: "rubble", x, y, z, s: 0.3 + rnd(q, 40) * 0.3, ry: q }); } }
    for (let lv = lo + 5; lv < hi - 4; lv += 8) if (rowsFree(-1, lv) && rowsFree(1, lv) && lv % 12 !== (lo + 3) % 12) for (const sd of [-1, 1]) torchAt(leg, wallCell(sd), lv, y0 + 2, -sd, { I: 2.4 });
  }

  if (kind === "vault") {
    // The vault gate: a brick wall across the hall with an opening two wide and two high, the iron doors flung open;
    // inside, the hoard on the free walls and a diamond block on a pedestal.
    const g0 = leg.b0 + 3;
    for (let lv = g0; lv < g0 + 2; lv++) for (let lu = -hw; lu < hw; lu++) for (let j = y0; j < y0 + ht; j++) {
      const gap = (lu === -1 || lu === 0) && j < y0 + 2;
      L(leg, lu, lv, j, gap ? T_AIR : (j === y0 + 2 && (lu === -1 || lu === 0) ? T_IRONB : T_BRICK));
    }
    for (const lu of [-2, 1]) torchAtB(leg, lu, g0, y0 + 2, -1, { I: 3.2 });
    for (const sd of [-1, 1]) {
      const [x, y, z] = W3(leg, sd * 0.9, g0 + 1.0, y0);
      decor({ t: "idoor", x, y, z, ry: yaw });
    }
    // The hoard.
    const hoard = [T_GOLD, T_GOLD, T_IRONB, T_LAPIS, T_GOLD, T_DIAM, T_EMERALD, T_GOLD];
    let q = 0;
    for (const sd of [-1, 1]) for (let lv = lo + 1; lv < hi + 1; lv++) {
      if (!rowsFree(sd, lv)) continue;
      const r = rnd(lv * 3 + (sd > 0 ? 1 : 0), 50);
      if (r > 0.55) continue;
      const t = hoard[(lv + q++) % hoard.length], lu = edgeCell(sd);
      if (LG(leg, lu, lv, y0) !== T_AIR) continue;
      L(leg, lu, lv, y0, t);
      if (r < 0.2 && LG(leg, lu, lv, y0 + 1) === T_AIR) L(leg, lu, lv, y0 + 1, t === T_GOLD ? T_GOLD : T_IRONB);
      const [x, , z] = W3(leg, lu + 0.5, lv + 0.5, 0);
      a.sources.push({ x, y: y0 + 1.6, z, c: t === T_DIAM ? [0.55, 0.95, 1.0] : t === T_EMERALD ? [0.4, 1.0, 0.55] : [1.0, 0.82, 0.38], I: 1.6, R: 7 });
    }
    for (let lv = lo + 2; lv < hi; lv += 5) for (const sd of [-1, 1]) if (rowsFree(sd, lv)) torchAt(leg, wallCell(sd), lv, y0 + 3, -sd, { I: 3.0 });
    // The pedestal at the far end.
    const pv = leg.ce - leg.post - 1 + 1;
    for (const lu of [-3, -2]) for (const lv of [pv, pv + 1]) { L(leg, lu, lv, y0, T_IRONB); L(leg, lu, lv, y0 + 1, T_GOLD); }
    L(leg, -3, pv, y0 + 2, T_DIAM);
    const [px, , pz] = W3(leg, -2.0, pv + 1.0, 0);
    a.sources.push({ x: px, y: y0 + 3.2, z: pz, c: [0.7, 0.96, 1.0], I: 3.6, R: 11, dyn: true });
    for (let lv = lo; lv < hi; lv += 4) { const sd = (lv / 4) % 2 ? 1 : -1; const [x, , z] = W3(leg, sd * (hw - 0.3), lv, 0); decor({ t: "web", x, y: y0 + ht - 0.6, z, ry: yaw + sd * Math.PI / 4, w: 1.2 }); }
  }

  if (kind === "fortress") {
    // Nether brick arches over the walkway, fence rails along its edges, glowstone in the roof, lava all round.
    for (let lv = lo + 1; lv < hi + 2; lv++) if (lv % 6 === 3) {
      for (const lu of [-3, 2]) for (let j = y0 - FORT_DEPTH + 1; j <= y0 + 3; j++) L(leg, lu, lv, j, T_NBRICK);
      for (let lu = -3; lu <= 2; lu++) { L(leg, lu, lv, y0 + 4, T_NBRICK); L(leg, lu, lv, y0 + 5, lu === -3 || lu === 2 ? T_NBRICK : T_AIR); }
      torchAt(leg, -3, lv, y0 + 2, 1, { I: 2.8 }); torchAt(leg, 2, lv, y0 + 2, -1, { I: 2.8 });
      if (lv % 12 === 3) {
        const [gx, , gz] = W3(leg, 0.5, lv + 0.5, 0);
        a.sources.push({ x: gx, y: y0 + 3.6, z: gz, c: [1.0, 0.82, 0.46], I: 3.0, R: 11 });
        L(leg, 0, lv, y0 + 4, T_GLOW);
      }
    }
    for (let lv = leg.cs + 1; lv < leg.ce - 1; lv++) for (const e of [-2, 1]) {
      if (LG(leg, e, lv, y0) !== T_AIR) continue;
      const [x, , z] = W3(leg, e + (e < 0 ? 0.14 : 0.86), lv + 0.5, 0);
      const [bx, bz] = dirw(leg, 0, 1);
      decor({ t: "nfence", x: x - bx * 0.5, y: y0, z: z - bz * 0.5, ry: yaw, bx, bz, rails: lv < leg.ce - 2 });
    }
    for (let q = 0; q < 8; q++) { const lv = lo + q * ((hi - lo) / 8), sd = q % 2 ? 1 : -1; const [x, , z] = W3(leg, sd * 2.8, lv, 0); a.spots.fire.push([x, y0 - FORT_DEPTH + 1, z]); }
  }

  if (kind === "stronghold") {
    // Cracked and mossy brick, a hall of torches and cobwebs, and at the end the portal: twelve frames each holding
    // an eye, the starfield between them, lava in the troughs on both sides.
    const vc = leg.vc;
    for (let lv = leg.cs + 2; lv < vc - 5; lv += 5) for (const sd of [-1, 1]) if (rowsFree(sd, lv)) torchAt(leg, wallCell(sd), lv, y0 + 2, -sd, { I: 3.0 });
    for (let q = 0; q < 10; q++) { const lv = lo + 1 + q * ((vc - 5 - lo) / 10), sd = q % 2 ? 1 : -1; const [x, , z] = W3(leg, sd * (hw - 0.3), lv, 0); decor({ t: "web", x, y: y0 + ht - 0.6, z, ry: yaw + sd * Math.PI / 4, w: 1.8 }); }
    for (let q = 0; q < 7; q++) { const lv = lo + 2 + q * 4, sd = q % 2 ? 1 : -1; if (rowsFree(sd, lv)) { const [x, , z] = W3(leg, sd * (hw - 0.04), lv + 0.5, 0); decor({ t: "vine", x, y: y0 + 2.4, z, ry: yaw + sd * Math.PI / 2, w: 1.0, h: 1.5 }); } }
    for (let lv = vc - 5; lv < leg.ce; lv++) for (const lu of [-hw, -hw + 1, hw - 2, hw - 1]) {
      L(leg, lu, lv, y0 - 1, T_LAVA); L(leg, lu, lv, y0 - 2, T_OBS);
      if (lv % 2 === 0 && (lu === -hw + 1 || lu === hw - 2)) {
        const [x, , z] = W3(leg, lu + 0.5, lv + 0.5, 0);
        a.sources.push({ x, y: y0 + 0.3, z, c: [1.0, 0.34, 0.07], I: 3.2, R: 10, lava: true, dyn: true });
      }
    }
    { const [xa, , za] = W3(leg, -hw, vc - 5, 0), [xb, , zb] = W3(leg, -hw + 2, leg.ce, 0); a.lavaRects.push({ x0: Math.min(xa, xb), x1: Math.max(xa, xb), z0: Math.min(za, zb), z1: Math.max(za, zb), y: y0 - 0.12 }); }
    { const [xa, , za] = W3(leg, hw - 2, vc - 5, 0), [xb, , zb] = W3(leg, hw, leg.ce, 0); a.lavaRects.push({ x0: Math.min(xa, xb), x1: Math.max(xa, xb), z0: Math.min(za, zb), z1: Math.max(za, zb), y: y0 - 0.12 }); }
    for (const sd of [-1, 1]) for (const lv of [vc - 4, vc, vc + 4]) torchAt(leg, wallCell(sd), lv, y0 + 3, -sd, { I: 3.2 });
    // The frame ring: cells at the border of a 5 by 5, corners left out; the portal fills the 3 by 3 inside.
    for (let du = -2; du <= 2; du++) for (let dv = -2; dv <= 2; dv++) {
      const edge = Math.abs(du) === 2 || Math.abs(dv) === 2;
      if (!edge || (Math.abs(du) === 2 && Math.abs(dv) === 2)) continue;
      const [x, , z] = W3(leg, du + 0.5, vc + dv + 0.5, 0);
      // The frame faces inward: its yaw follows the side it is on.
      decor({ t: "frame", x, y: y0, z, eye: true });
    }
    const [cx, , cz] = W3(leg, 0.5, vc + 0.5, 0);
    decor({ t: "portal", x: cx, y: y0 + 0.75, z: cz, w: 3, d: 3 });
    a.sources.push({ x: cx, y: y0 + 1.2, z: cz, c: [0.25, 0.9, 0.72], I: 4.4, R: 13, dyn: true });
    a.sources.push({ x: cx, y: y0 + 1.2, z: cz, c: [0.25, 0.9, 0.72], I: 3.0, R: 8 });
    a.emit.push({ k: "portal", x: cx, y: y0 + 0.9, z: cz });
  }

  if (kind === "stairs") {
    for (let lv = leg.stairsAt + 1; lv < leg.stairsAt + STAIR_LEN; lv += 4) for (const sd of [-1, 1]) {
      const yf = floorTop(leg, lv);
      torchAt(leg, wallCell(sd), lv, yf + 2, -sd, { I: 3.4 });
    }
    for (const sd of [-1, 1]) torchAt(leg, wallCell(sd), leg.b0 + 1, y0 + 2, -sd, { I: 2.9 });
  }

  if (kind === "deep") {
    // Glowstone in the roof, fire on the netherrack, torches thin: the lava does the lighting.
    for (let lv = leg.cs + 1; lv < leg.ce - 1; lv++) for (let lu = -hw + 1; lu < hw - 1; lu++) {
      const h = ih(lu, lv, leg.rid, 21);
      const yf = floorTop(leg, lv);
      if (h < 55) { L(leg, lu, lv, yf + ht, T_GLOW); a.sources.push({ ...(() => { const [x, , z] = W3(leg, lu + 0.5, lv + 0.5, 0); return { x, y: yf + ht - 0.3, z }; })(), c: [1.0, 0.82, 0.46], I: 3.2, R: 11 }); }
      else if (h < 70 && LG(leg, lu, lv, yf + ht - 1) === T_AIR && lv > lo) { L(leg, lu, lv, yf + ht - 1, T_GLOW); const [x, , z] = W3(leg, lu + 0.5, lv + 0.5, 0); a.sources.push({ x, y: yf + ht - 1, z, c: [1.0, 0.82, 0.46], I: 3.2, R: 11 }); }
    }
    for (let lv = lo; lv < hi + 3; lv++) for (let lu = -hw + 1; lu < hw - 1; lu++) {
      if (LG(leg, lu, lv, y0 - 1) !== T_NETHER) continue;
      if (ih(lu, lv, leg.rid, 31) < 70 && Math.abs(lu + 0.5) > 1.2) {
        const [x, y, z] = W3(leg, lu + 0.5, lv + 0.5, y0);
        decor({ t: "fire", x, y, z });
        a.sources.push({ x, y: y + 0.6, z, c: [1.0, 0.48, 0.16], I: 2.6, R: 9, dyn: true });
        a.emit.push({ k: "fire", x, y: y + 0.7, z });
        a.spots.fire.push([x, y + 0.5, z]);
      }
    }
    for (let lv = leg.cs; lv < leg.ce; lv++) for (const lu of [-hw, hw - 1]) {
      if (LG(leg, lu, lv, y0 - 1) === T_LAVA && lv % 3 === 0) {
        const [x, , z] = W3(leg, lu + 0.5, lv + 0.5, 0);
        a.sources.push({ x, y: y0 + 0.3, z, c: [1.0, 0.34, 0.07], I: 3.4, R: 10, lava: true, dyn: true });
        a.lavaRects.push({ x0: x - 0.5, x1: x + 0.5, z0: z - 0.5, z1: z + 0.5, y: y0 - 0.12 });
        if (lv % 6 === 0) { a.spots.lava.push([x, y0, z]); a.emit.push({ k: "lava", x, y: y0 - 0.05, z }); }
      }
    }
    for (const sd of [-1, 1]) for (let lv = lo + 3; lv < hi; lv += 8) if (rowsFree(sd, lv)) torchAt(leg, wallCell(sd), lv, y0 + 2, -sd, { I: 3.0 });
  }
}

// ---- the bake ---------------------------------------------------------------------------------------
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

// lightAt(x, y, z, nx, ny, nz) -> [r, g, b]: the ambient of the segment plus every source in reach, with occlusion.
export function makeLightAt(a) {
  const lay = a.lay, BIN = 13;
  const bins = new Map();
  const key = (i, j, k) => (i + 512) * 1048576 + (j + 512) * 1024 + (k + 512);
  for (const s of a.sources) {
    const kk = key(Math.floor(s.x / BIN), Math.floor(s.y / BIN), Math.floor(s.z / BIN));
    if (!bins.has(kk)) bins.set(kk, []);
    bins.get(kk).push(s);
  }
  const vis = makeVisible(a);
  const out = [0, 0, 0];
  const lightAt = (x, y, z, nx, ny, nz, o = {}) => {
    const s = sApprox(lay, x, z);
    const pr = profileAt(lay, s);
    out[0] = pr.amb[0]; out[1] = pr.amb[1]; out[2] = pr.amb[2];
    // A touch of hemisphere: faces that look up are brighter than those looking down.
    const hm = 1 + 0.28 * ny;
    out[0] *= hm; out[1] *= hm; out[2] *= hm;
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
        let I = sc.I * (sc.sky ? 1 : (sc.lava || sc.c[2] > 0.8 ? 1 : pr.torch));
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

// ---- meshing -----------------------------------------------------------------------------------------
const AO = [0.42, 0.62, 0.8, 1.0];
export const bakeUniform = { value: 1 };

// Adds the baked light to a Lambert or Standard material as emissive-times-albedo from a per-vertex 'bake' attribute
// (or a fixed vec3 when the object has none).
export function patchBake(mat, { fixed = null } = {}) {
  mat.onBeforeCompile = (sh) => {
    sh.uniforms.uBakeGain = bakeUniform;
    if (fixed) sh.uniforms.uBakeFixed = { value: fixed };
    sh.vertexShader = sh.vertexShader
      .replace("#include <common>", fixed ? "#include <common>" : "#include <common>\nattribute vec3 bake;\nvarying vec3 vBake;")
      .replace("#include <begin_vertex>", fixed ? "#include <begin_vertex>" : "#include <begin_vertex>\nvBake = bake;");
    sh.fragmentShader = sh.fragmentShader
      .replace("#include <common>", (fixed ? "#include <common>\nuniform vec3 uBakeFixed;" : "#include <common>\nvarying vec3 vBake;") + "\nuniform float uBakeGain;")
      .replace("#include <emissivemap_fragment>", "#include <emissivemap_fragment>\ntotalEmissiveRadiance += diffuseColor.rgb * " + (fixed ? "uBakeFixed" : "vBake") + " * uBakeGain;");
  };
  mat.customProgramCacheKey = () => (fixed ? "bakeF" : "bakeV");
  return mat;
}

// Chunks of CH x CH blocks (full height) are meshed lazily: the page asks for the ones near the walker (pump) and
// carve() rebuilds only the chunks a box touches. Textures are shared between chunks.
export const CH = 32;
export const BLOCK_NAME = {
  [T_AIR]: "air", [T_STONE]: "stone", [T_COBBLE]: "cobblestone", [T_MOSSY]: "mossy_cobblestone", [T_BRICK]: "stonebrick",
  [T_BRICK_MOSSY]: "mossy_stonebrick", [T_BRICK_CRACK]: "cracked_stonebrick", [T_GRAVEL_FLOOR]: "gravel", [T_COAL]: "coal_ore",
  [T_IRON]: "iron_ore", [T_OBS]: "obsidian", [T_BEDROCK]: "bedrock", [T_NETHER]: "netherrack", [T_GLOW]: "glowstone",
  [T_BRIDGE]: "stonebrick", [T_WATER]: "water", [T_NBRICK]: "nether_brick", [T_SOUL]: "soul_sand", [T_SHELF]: "bookshelf",
  [T_PLANK]: "planks", [T_LOG]: "log", [T_LAVA]: "lava", [T_DIRT]: "dirt",
  [T_DISP_PX]: "dispenser", [T_DISP_NX]: "dispenser", [T_DISP_PZ]: "dispenser", [T_DISP_NZ]: "dispenser",
  [T_GOLD]: "gold_block", [T_DIAM]: "diamond_block", [T_LAPIS]: "lapis_block", [T_EMERALD]: "emerald_block",
  [T_IRONB]: "iron_block", [T_CARVED]: "chiseled_stonebrick"
};
export function blockNameAt(a, x, y, z) {
  const i = Math.floor(x), j = Math.floor(y), k = Math.floor(z);
  if (!a.inb(i, j, k)) return "bedrock";
  const ix = ((k - a.k0) * a.NJ + (j - a.j0)) * a.NI + (i - a.i0);
  const t = a.g[ix];
  return BLOCK_NAME[t === T_WALL ? wallType(a.st[ix], i, j, k) : t] || "stone";
}

export function meshGrid(a, images) {
  const group = new THREE.Group();
  const lightAt = makeLightAt(a);
  const texs = {};
  const texOf = (file) => {
    if (texs[file] !== undefined) return texs[file];
    const img = images[file];
    if (!img) return (texs[file] = null);
    const tex = new THREE.Texture(img);
    tex.colorSpace = THREE.SRGBColorSpace; tex.magFilter = THREE.NearestFilter; tex.minFilter = THREE.NearestFilter;
    tex.wrapS = tex.wrapT = THREE.RepeatWrapping; tex.generateMipmaps = false; tex.needsUpdate = true;
    return (texs[file] = tex);
  };
  const mats = {};
  const matOf = (file) => mats[file] || (mats[file] = patchBake(new THREE.MeshLambertMaterial({ map: texOf(file) })));
  const nci = Math.ceil(a.NI / CH), nck = Math.ceil(a.NK / CH);
  const chunks = new Map();   // "ci,ck" -> { group, built }
  const cOf = (i, k) => [Math.floor((i - a.i0) / CH), Math.floor((k - a.k0) / CH)];
  const AX = null; void AX;
  const dirs = [[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]];
  const resolve = (i, j, k) => {
    const t = a.g[((k - a.k0) * a.NJ + (j - a.j0)) * a.NI + (i - a.i0)];
    return t === T_WALL ? wallType(a.st[((k - a.k0) * a.NJ + (j - a.j0)) * a.NI + (i - a.i0)], i, j, k) : t;
  };
  function buildChunk(ci, ck) {
    const key = ci + "," + ck;
    let ch = chunks.get(key);
    if (!ch) { ch = { group: new THREE.Group(), built: false }; ch.group.matrixAutoUpdate = false; chunks.set(key, ch); group.add(ch.group); }
    for (const m of [...ch.group.children]) { ch.group.remove(m); m.geometry.dispose(); }
    ch.built = true;
    const bins = new Map();
    const bin = (file) => { if (!bins.has(file)) bins.set(file, { pos: [], nor: [], uv: [], bake: [] }); return bins.get(file); };
    const iLo = Math.max(a.i0 + 1, a.i0 + ci * CH), iHi = Math.min(a.i0 + a.NI - 1, a.i0 + (ci + 1) * CH);
    const kLo = Math.max(a.k0 + 1, a.k0 + ck * CH), kHi = Math.min(a.k0 + a.NK - 1, a.k0 + (ck + 1) * CH);
    for (let k = kLo; k < kHi; k++) for (let j = a.j0 + 1; j < a.j0 + a.NJ - 1; j++) for (let i = iLo; i < iHi; i++) {
      const raw = a.g[((k - a.k0) * a.NJ + (j - a.j0)) * a.NI + (i - a.i0)];
      if (raw === T_AIR || raw === T_WATER || raw === T_LAVA) continue;
      let tt = null;
      for (const [di, dj, dk] of dirs) {
        const n = a.g[((k + dk - a.k0) * a.NJ + (j + dj - a.j0)) * a.NI + (i + di - a.i0)];
        if (n !== T_AIR && n !== T_WATER && n !== T_LAVA) continue;
        if (tt === null) tt = resolve(i, j, k);
        const names = TEX_OF[tt] || TEX_OF[T_STONE];
        const top = dj > 0, bot = dj < 0;
        const fr = FRONT[tt];
        const file = fr && fr[0] === di && fr[1] === dk ? "dispenser_front_horizontal" : top ? (names[1] || names[0]) : bot ? (names[2] || names[1] && tt !== T_GRAVEL_FLOOR ? (names[2] || names[1]) : names[0]) : names[0];
        const b = bin(file);
        const ax = di ? 0 : dj ? 1 : 2, sn = di + dj + dk;
        const t1 = (ax + 1) % 3, t2 = (ax + 2) % 3;
        const base = [i, j, k]; base[ax] += sn > 0 ? 1 : 0;
        const corners = [[0, 0], [1, 0], [1, 1], [0, 1]];
        const verts = corners.map(([c1, c2]) => { const p = base.slice(); p[t1] += c1; p[t2] += c2; return p; });
        const e1 = [verts[1][0] - verts[0][0], verts[1][1] - verts[0][1], verts[1][2] - verts[0][2]];
        const e2 = [verts[2][0] - verts[0][0], verts[2][1] - verts[0][1], verts[2][2] - verts[0][2]];
        const cr = [e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]];
        const order = (cr[0] * di + cr[1] * dj + cr[2] * dk) >= 0 ? [0, 1, 2, 0, 2, 3] : [0, 2, 1, 0, 3, 2];
        const cxm = i + 0.5 + di * 0.52, cym = j + 0.5 + dj * 0.52, czm = k + 0.5 + dk * 0.52;
        const bl = tt === T_GLOW ? [1.7, 1.45, 0.9] : lightAt(cxm, cym, czm, di, dj, dk);
        const bkr = bl[0], bkg = bl[1], bkb = bl[2];
        const aos = corners.map(([c1, c2]) => {
          const s1 = c1 ? 1 : -1, s2 = c2 ? 1 : -1;
          const p = [i + di, j + dj, k + dk];
          const q1 = p.slice(); q1[t1] += s1; const q2 = p.slice(); q2[t2] += s2; const q3 = p.slice(); q3[t1] += s1; q3[t2] += s2;
          const o1 = a.solid(q1[0], q1[1], q1[2]) ? 1 : 0, o2 = a.solid(q2[0], q2[1], q2[2]) ? 1 : 0, o3 = a.solid(q3[0], q3[1], q3[2]) ? 1 : 0;
          return AO[(o1 && o2) ? 0 : 3 - (o1 + o2 + o3)];
        });
        for (const q of order) {
          const [px, py, pz] = verts[q];
          b.pos.push(px, py, pz); b.nor.push(di, dj, dk);
          const uu = di ? (di > 0 ? -pz : pz) : px, vv = dj ? pz : py;
          b.uv.push(uu, vv);
          const ao = tt === T_GLOW ? 1 : aos[q];
          b.bake.push(bkr * ao, bkg * ao, bkb * ao);
        }
      }
    }
    for (const [file, b] of bins) {
      if (!texOf(file) || !b.pos.length) continue;
      const g = new THREE.BufferGeometry();
      g.setAttribute("position", new THREE.Float32BufferAttribute(b.pos, 3));
      g.setAttribute("normal", new THREE.Float32BufferAttribute(b.nor, 3));
      g.setAttribute("uv", new THREE.Float32BufferAttribute(b.uv, 2));
      g.setAttribute("bake", new THREE.Float32BufferAttribute(b.bake, 3));
      const m = new THREE.Mesh(g, matOf(file));
      m.matrixAutoUpdate = false;
      ch.group.add(m);
    }
  }
  const isBuilt = (ci, ck) => { const c = chunks.get(ci + "," + ck); return !!(c && c.built); };
  // Builds the nearest unbuilt chunk within `radius` blocks of (x, z); returns true when it built one.
  function pump(x, z, radius = 56, n = 1) {
    let built = 0;
    for (; built < n; built++) {
      let best = null, bd = radius * radius;
      const c0 = cOf(x - radius, z - radius), c1 = cOf(x + radius, z + radius);
      for (let ci = Math.max(0, c0[0]); ci <= Math.min(nci - 1, c1[0]); ci++) for (let ck = Math.max(0, c0[1]); ck <= Math.min(nck - 1, c1[1]); ck++) {
        if (isBuilt(ci, ck)) continue;
        const cx = a.i0 + (ci + 0.5) * CH, cz = a.k0 + (ck + 0.5) * CH;
        const d = (cx - x) ** 2 + (cz - z) ** 2;
        if (d < bd) { bd = d; best = [ci, ck]; }
      }
      if (!best) break;
      buildChunk(best[0], best[1]);
    }
    return built > 0;
  }
  // Rebuilds the built chunks that a block box (inclusive) touches, with a one block margin for faces and occlusion.
  function rebuildBox(mn, mx) {
    const c0 = cOf(mn[0] - 1, mn[2] - 1), c1 = cOf(mx[0] + 1, mx[2] + 1);
    for (let ci = Math.max(0, c0[0]); ci <= Math.min(nci - 1, c1[0]); ci++) for (let ck = Math.max(0, c0[1]); ck <= Math.min(nck - 1, c1[1]); ck++) if (isBuilt(ci, ck)) buildChunk(ci, ck);
  }
  function buildAll() { for (let ci = 0; ci < nci; ci++) for (let ck = 0; ck < nck; ck++) if (!isBuilt(ci, ck)) buildChunk(ci, ck); }
  const stats = () => { let meshes = 0, built = 0; for (const c of chunks.values()) if (c.built) { built++; meshes += c.group.children.length; } return { chunks: built, total: nci * nck, meshes }; };
  return { group, disposables: [], lightAt, pump, rebuildBox, buildAll, stats };
}

// ---- carving (the scares' contract) -----------------------------------------------------------------------
// carve(min, max): empties the blocks in the box (inclusive, world block coords) and rebuilds the chunks it touches.
// restore(): puts every carved block back. solidAt / blockAt read the grid as it is now.
export function makeCarver(a, gm) {
  const saved = new Map();   // grid index -> original value
  const clampBox = (mn, mx) => [
    [Math.floor(Math.min(mn[0], mx[0])), Math.floor(Math.min(mn[1], mx[1])), Math.floor(Math.min(mn[2], mx[2]))],
    [Math.floor(Math.max(mn[0], mx[0])), Math.floor(Math.max(mn[1], mx[1])), Math.floor(Math.max(mn[2], mx[2]))]];
  return {
    carve(mn, mx) {
      const [lo, hi] = clampBox(mn, mx);
      let n = 0;
      for (let k = lo[2]; k <= hi[2]; k++) for (let j = lo[1]; j <= hi[1]; j++) for (let i = lo[0]; i <= hi[0]; i++) {
        // Never the outermost shell of the grid: it stays a wall.
        if (i <= a.i0 || i >= a.i0 + a.NI - 1 || k <= a.k0 || k >= a.k0 + a.NK - 1 || j <= a.j0 || j >= a.j0 + a.NJ - 1) continue;
        const ix = ((k - a.k0) * a.NJ + (j - a.j0)) * a.NI + (i - a.i0);
        if (a.g[ix] === T_AIR) continue;
        if (!saved.has(ix)) saved.set(ix, a.g[ix]);
        a.g[ix] = T_AIR; n++;
      }
      if (n) gm.rebuildBox(lo, hi);
      return n;
    },
    restore() {
      if (!saved.size) return 0;
      let mn = [1e9, 1e9, 1e9], mx = [-1e9, -1e9, -1e9];
      for (const [ix, v] of saved) {
        const i = ix % a.NI + a.i0, j = Math.floor(ix / a.NI) % a.NJ + a.j0, k = Math.floor(ix / (a.NI * a.NJ)) + a.k0;
        a.g[ix] = v;
        mn = [Math.min(mn[0], i), Math.min(mn[1], j), Math.min(mn[2], k)]; mx = [Math.max(mx[0], i), Math.max(mx[1], j), Math.max(mx[2], k)];
      }
      const n = saved.size; saved.clear();
      gm.rebuildBox(mn, mx);
      return n;
    },
    solidAt: (x, y, z) => a.solid(Math.floor(x), Math.floor(y), Math.floor(z)),
    blockAt: (x, y, z) => blockNameAt(a, x, y, z)
  };
}

export const sizeOf = (lay) => lay.length;
