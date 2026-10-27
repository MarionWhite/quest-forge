// The registry of the Krypt's segment kinds, and the dressing context every dresser gets. A kind has its geometry ranges
// (the plan picks within them), its wall style, its floor, its lighting profile and its dresser: a function that places
// torches, decor and blocks along one leg. Dressers run once per chunk window (the same leg is dressed again for every chunk
// that reaches it), so they depend only on the leg and on leg-local coordinates, never on what else has been built.
import * as B from "./blocks.js";
import { ih, defWalls, T_AIR, T_BRICK, T_STONE, T_LAVA, T_WATER, T_DISP_PX, T_DISP_NX, T_DISP_PZ, T_DISP_NZ } from "./blocks.js";
import { legYaw } from "./geom.js";

export const KINDS = {};
// Defaults for every kind; a kind lists only what differs. hw, ht, pre, post, m, branch are [min, max] ranges.
export function def(id, meta) {
  const k = { id, turn: 0.6, weight: 1, hw: [3, 3], ht: [4, 4], pre: [2, 2], post: [0, 0], m: [6, 10], branch: [0, 1], below: 4, torchEvery: 1, torchI: 3.4, step: 4, holes: null, ...meta };
  KINDS[id] = k; return k;
}
export const wall = defWalls;
export const P = (amb, fog, fogD, exposure, torch, bloom, extra = {}) => ({ amb, fog, fogD, exposure, torch, bloom, ...extra });

// The dressing context of one leg: leg-local setters, torches, decor, and the small helpers every dresser uses.
export function makeCtx(a, plan, leg, H) {
  const { L, LG, W3, dirw, torchAt, torchAtB, pushTorch, decor, legCell, set, get } = H;
  const { hw, y0, kind, ht } = leg;
  const rowsFree = (side, lv) => !leg.used[side].has(lv) && !leg.passages.some(p => p.ok && p.side === side && lv >= p.lv - 1 && lv <= p.lv + 2);
  const lo = leg.b0 + leg.pre, hi = leg.contentEnd;
  const yaw = legYaw(leg);
  const rnd = (i, s) => ih(i, leg.rid, s, 11) / 1000;
  const wallCell = (side) => (side > 0 ? hw : -hw - 1);
  const edgeCell = (side) => (side > 0 ? hw - 1 : -hw);
  const dispType = (dx, dz) => (dx > 0 ? T_DISP_PX : dx < 0 ? T_DISP_NX : dz > 0 ? T_DISP_PZ : T_DISP_NZ);
  const webAt = (aa, bb, y, ry, w, h, rep) => { const [x, , z] = W3(leg, aa, bb, 0); decor({ t: "web", x, y, z, ry, w, h, rep: !!rep }); };
  const freeRow = (lv) => rowsFree(-1, lv) && rowsFree(1, lv) && rowsFree(-1, lv + 1) && rowsFree(1, lv + 1);
  // ---- helpers for the newer kinds (leg-local a across, b along, y world) ----
  const fill = (lu0, lu1, lv0, lv1, j0, j1, t) => { for (let lv = lv0; lv <= lv1; lv++) for (let lu = lu0; lu <= lu1; lu++) for (let j = j0; j <= j1; j++) L(leg, lu, lv, j, t); };
  const col = (lu, lv, j0, j1, t) => { for (let j = j0; j <= j1; j++) L(leg, lu, lv, j, t); };
  const put = (t, aa, bb, y, o = {}) => { const [x, , z] = W3(leg, aa, bb, 0); decor({ t, x, y, z, ...o }); };
  const faceRy = (sd) => yaw - sd * Math.PI / 2;               // turns +z toward the corridor from side sd
  const acrossRy = yaw + Math.PI / 2;                          // a plane that spans along the leg (its normal across)
  const sideRy = (sd) => yaw + sd * Math.PI / 2;
  const src = (aa, bb, y, color, I, R, o = {}) => { const [x, , z] = W3(leg, aa, bb, 0); a.sources.push({ x, y, z, c: color, I, R, ...o }); };
  const emit = (k, aa, bb, y, o = {}) => { const [x, , z] = W3(leg, aa, bb, 0); a.emit.push({ k, x, y, z, ...o }); };
  const each = (step, from, to, fn) => { let i = 0; for (let lv = from; lv < to; lv += step, i++) fn(lv, i); };
  const slotsEach = (fn) => { leg.slots.forEach((s, i) => fn(s, i)); };
  const torches = (every, off, I, y, sides = [-1, 1], from = lo, to = hi) => { for (let lv = from + off; lv < to; lv += every) for (const sd of sides) if (rowsFree(sd, lv)) torchAt(leg, wallCell(sd), lv, y, -sd, { I }); };
  // A block that gives light: sets the tile and adds a bake source at its centre.
  const lamp = (lu, lv, j, t, color, I, R = 10, o = {}) => { L(leg, lu, lv, j, t); const [x, , z] = W3(leg, lu + 0.5, lv + 0.5, 0); a.sources.push({ x, y: j + 0.5, z, c: color, I, R, ...o }); };
  // Ceiling cracks, hanging webs and vines, scattered bones, rubble: the dressing every hall shares, by count.
  const scatter = (n, salt, fn) => { for (let q = 0; q < n; q++) fn(q, rnd(q, salt), rnd(q, salt + 1), rnd(q, salt + 2)); };
  const ceilWebs = (n, w = 1.6, salt = 40) => scatter(n, salt, (q, r1, r2) => { const sd = q % 2 ? 1 : -1; webAt(sd * (hw - 0.3), lo + 0.5 + r1 * (hi - lo), y0 + ht - 0.6, yaw + sd * Math.PI / 4, w); void r2; });
  const vines = (n, salt = 50, h = 1.6) => scatter(n, salt, (q, r1, r2) => { const sd = q % 2 ? 1 : -1, lv = lo + r1 * (hi - lo); if (rowsFree(sd, Math.floor(lv))) put("vine", sd * (hw - 0.04), lv, y0 + 2.2 + r2 * 0.4, { ry: sideRy(sd), w: 1.0, h }); });
  const bones = (n, salt = 60, spread = 1.7) => scatter(n, salt, (q, r1, r2, r3) => put("bone", (r2 - 0.5) * hw * spread, lo + 0.5 + r1 * (hi - lo), y0 + 0.02, { ry: r3 * 6.28 }));
  // Debris lies where it fell: heaps of two or three slabs at the foot of a wall, never loose in the middle of the walk.
  const rubble = (n, salt = 70) => scatter(Math.max(1, Math.round(n / 4)), salt, (q, r1, r2, r3) => {
    const sd = r2 < 0.5 ? -1 : 1, lv = Math.floor(lo + 1 + r1 * (hi - lo - 3));
    if (!rowsFree(sd, lv) || !rowsFree(sd, lv + 1)) return;
    const lu = edgeCell(sd);
    put("rubble", lu + 0.5, lv + 0.5, y0); put("rubble", lu + 0.5, lv + 1.5, y0);
    if (r3 < 0.5) put("rubble", lu + 0.5 - sd, lv + 0.5 + (r3 < 0.25 ? 1 : 0), y0);
  });
  return {
    a, plan, leg, L, LG, W3, dirw, torchAt, torchAtB, pushTorch, decor, legCell, set, get, hw, y0, kind, ht, rowsFree, lo, hi, yaw, rnd, wallCell, edgeCell, dispType, webAt, freeRow,
    fill, col, put, faceRy, acrossRy, sideRy, src, emit, each, slotsEach, torches, lamp, scatter, ceilWebs, vines, bones, rubble, B
  };
}
