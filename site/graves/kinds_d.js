// Set pieces: one open space per stratum, where the walls fall away or the scale changes (a chasm with lava both sides, a lava sea,
// a void, a flooded cistern, a two-level library, a cavern of giant mushrooms ...). Each is forced into its stratum by plan.js
// (def.set) at a few fixed legs, so it appears at least once per cycle. Graves still sit in niches along the far walls.
// Also here: the asymmetry pass (irregular rubble, broken pillars, glimpsed side rooms, ceiling dips, floor props) that
// kinds_c.js applies to every ordinary kind.
import * as B from "./blocks.js";
import { def, wall, P } from "./kindreg.js";
import { F, rectOf, clearer, pool } from "./kindlib.js";
const { T_AIR, T_BRICK, T_COBBLE, T_STONE, T_BRICK_CRACK, T_BRICK_MOSSY, T_MOSSY, T_GRAVEL_FLOOR, T_DIRT, T_CARVED, T_LAVA, T_OBS, T_GLOW, T_PLANK, T_LOG, T_BEDROCK, T_NBRICK, T_NETHER, T_WATER } = B;
const cl = B.clay;
const D = 8;                                   // depth of the open voids

// Rough, natural far walls: the hall's side walls are carved back 0..depth cells in drifting waves, never across an alcove or passage.
export function rough(c, o = {}) {
  const { leg, y0, ht, hw } = c, depth = o.depth || 3, clear = clearer(c), up = o.up == null ? ht - 1 : o.up;
  for (let lv = c.lo - 2; lv < c.hi + 3; lv++) for (const sd of [-1, 1]) {
    const k = Math.floor(lv / 3), f = (lv / 3) - k, a = c.rnd(k, 230 + sd), b = c.rnd(k + 1, 230 + sd), n = a + (b - a) * f;
    const d = Math.floor(n * (depth + 0.99));
    if (!d || !clear(sd, lv, 1)) continue;
    for (let q = 0; q < d; q++) for (let j = 0; j <= up - (q > 0 ? Math.floor(c.rnd(lv * 5 + q, 231) * 3) : 0); j++) c.L(leg, sd > 0 ? hw + q : -hw - 1 - q, lv, y0 + j, T_AIR);
  }
}
// A ragged roof: tiles hang 1..len from the ceiling at random lanes (stalactites).
export function spikes(c, tile, n, len = 3, ceil = c.ht) {
  const { leg, y0, hw } = c;
  c.scatter(n, 240, (q, r1, r2, r3) => { const lu = Math.floor(-hw + r2 * 2 * hw), lv = Math.floor(c.lo + r1 * (c.hi - c.lo)), l = 1 + Math.floor(r3 * len); for (let j = 0; j < l; j++) c.L(leg, lu, lv, y0 + ceil - 1 - j, tile); });
}
// A tunnel mouth in a side wall: w wide, h high, `depth` deep, floored, with a torch at the end and a bend.
export function opening(c, sd, lv, o = {}) {
  const { leg, y0, hw } = c, { w = 2, h = 3, depth = 6, floor = T_COBBLE, tile = null, I = 2.2, color = null } = o;
  for (let q = 0; q < depth; q++) for (let k = 0; k < w; k++) {
    const lu = sd > 0 ? hw + q : -hw - 1 - q;
    for (let j = 0; j < h; j++) c.L(leg, lu, lv + k, y0 + j, T_AIR);
    c.L(leg, lu, lv + k, y0 - 1, floor);
    if (tile && q === 0) for (const j of [h]) c.L(leg, lu, lv + k, y0 + j, tile);
  }
  if (tile) for (const k of [-1, w]) for (let j = 0; j <= h; j++) c.L(leg, sd > 0 ? hw : -hw - 1, lv + k, y0 + j, tile);
  c.torchAt(leg, sd > 0 ? hw + depth - 1 : -hw - depth, lv, y0 + 1, -sd, { I, ...(color ? { c: color } : {}) });
}

// ---- S1: the mineshaft crossing: rails run off in four directions from a timbered chamber --------------------------------
def("mine_crossing", { margin: 11, style: wall([[300, T_DIRT], [520, T_COBBLE], [700, T_STONE], [830, B.T_COAL], [900, B.T_IRON], [1000, T_GRAVEL_FLOOR]]), hw: [6, 7], ht: [7, 8], pre: [3, 3], post: [3, 3], m: [4, 5], branch: [0, 0], step: 8, holes: [0.5], turn: 0,
  floor: ({ hv, centre }) => (centre && hv < 400 ? T_DIRT : T_GRAVEL_FLOOR), alcovePil: B.T_LOG, alcoveLin: T_PLANK,
  prof: P([0.09, 0.085, 0.09], [0.04, 0.036, 0.04], 0.038, 1.2, 1.0, 0.34),
  dress(c) {
    const { leg, y0, hw, ht } = c, vc = Math.round((c.lo + c.hi) / 2), ry = leg.h === "N" ? 0 : Math.PI / 2;
    rough(c, { depth: 2 }); spikes(c, T_STONE, 16, 2);
    for (let lv = leg.cs; lv < leg.ce; lv++) if (lv !== vc) c.put("rail", 0.5, lv + 0.5, y0 + 0.02, { ry });
    for (const sd of [-1, 1]) opening(c, sd, vc - 1, { w: 3, h: 4, depth: 9, floor: T_GRAVEL_FLOOR, tile: B.T_PLANK, I: 2.8 });
    for (let lu = -hw - 9; lu < hw + 9; lu++) c.put("rail", lu + 0.5, vc + 0.5, y0 + 0.02, { ry: ry + Math.PI / 2 });
    for (const lu of [-3, 2]) for (const dv of [-3, 3]) { c.col(lu, vc + dv, y0, y0 + ht - 2, B.T_LOG); }
    for (const dv of [-3, 3]) for (let lu = -3; lu <= 2; lu++) c.L(leg, lu, vc + dv, y0 + ht - 2, T_PLANK);
    c.put("cart", 0.5, vc + 3.5, y0, { ry: c.acrossRy });
    for (const [lu, dv] of [[-3, -3], [2, -3], [-3, 3], [2, 3]]) c.torchAt(leg, lu, vc + dv, y0 + 3, lu < 0 ? 1 : -1, { I: 3.2 });
    c.src(0, vc, y0 + ht - 2, [1, 0.8, 0.5], 3.4, 12, {});
    F(c, [["torches", { every: 8, off: 2, I: 2.6 }], ["webs", { n: 8, w: 2 }], ["rubble", { n: 10 }]]);
  } });

// ---- S2: the labyrinth junction: a chamber with doorways into dark corridors on every side ------------------------------------
def("labyrinth_junction", { margin: 11, style: wall([[300, T_BRICK_MOSSY], [560, T_MOSSY], [760, T_BRICK_CRACK], [900, T_COBBLE], [1000, T_BRICK]]), hw: [5, 5], ht: [6, 6], pre: [3, 3], post: [3, 3], m: [4, 5], branch: [0, 0], step: 10,
  floor: ({ hv, lu, lv }) => (((lu >> 1) + (lv >> 1)) & 1 ? T_MOSSY : T_BRICK_MOSSY), alcovePil: T_MOSSY, alcoveLin: T_BRICK_MOSSY,
  prof: P([0.07, 0.1, 0.075], [0.03, 0.045, 0.034], 0.04, 1.2, 1.0, 0.3),
  dress(c) {
    const { leg, y0, hw, ht } = c, clear = clearer(c);
    const rows = []; for (let lv = c.lo + 1; lv < c.hi - 2; lv++) if (clear(-1, lv, 1) && clear(1, lv, 1) && clear(-1, lv + 2, 1) && clear(1, lv + 2, 1) && !rows.some((r) => Math.abs(r - lv) < 6)) rows.push(lv);
    rows.slice(0, 3).forEach((lv, i) => { for (const sd of (i % 2 ? [1] : [-1, 1])) opening(c, sd, lv, { w: 2, h: 3, depth: 7, floor: T_MOSSY, tile: T_BRICK_MOSSY, I: 2.0 + i * 0.3, color: [1.0, 0.55, 0.3] }); });
    for (const lv of [c.lo + 1, c.hi - 2]) for (let lu = -1; lu <= 0; lu++) for (let j = 0; j < 3; j++) { /* doorways at both ends are the hall's own */ }
    for (let lv = c.lo; lv < c.hi; lv += 5) for (const lu of [-3, 2]) if (clear(lu < 0 ? -1 : 1, lv, 0)) { c.col(lu, lv, y0, y0 + ht - 1, T_MOSSY); c.torchAt(leg, lu, lv, y0 + 2, lu < 0 ? 1 : -1, { I: 2.4 }); }
    F(c, [["vines", { n: 14 }], ["webs", { n: 8 }], ["rubble", { n: 6 }]]);
  } });

// ---- S3: the flooded cistern: pillars standing in deep water, a two wide walkway through -----------------------------------
def("flooded_cistern", { style: wall([[420, T_BRICK_MOSSY], [680, T_MOSSY], [860, T_BRICK], [1000, T_BRICK_CRACK]]), hw: [9, 9], ht: [9, 9], pre: [3, 3], post: [3, 3], m: [5, 6], branch: [0, 0], step: 8, below: 8, holes: [0.5],
  floor: ({ lu, hv, yf }) => ((lu === -1 || lu === 0) ? (hv < 300 ? T_BRICK_MOSSY : T_BRICK) : { from: yf - 1, cells: [[yf - 7, T_GRAVEL_FLOOR]] }),
  alcoveBase: (leg) => leg.y0 - 1, alcovePil: T_BRICK_MOSSY, alcoveLin: T_CARVED,
  prof: P([0.085, 0.15, 0.17], [0.025, 0.055, 0.065], 0.036, 1.26, 1.15, 0.36),
  dress(c) {
    const { leg, y0, hw, ht } = c;
    c.a.waterRects.push({ ...rectOf(c, -hw, hw - 1, leg.cs + 1, leg.ce - 2), y: y0 - 0.3 });
    for (let lv = c.lo + 1; lv < c.hi; lv += 5) for (const lu of [-7, -4, 3, 6]) {
      c.col(lu, lv, y0 - 6, y0 + ht - 2, B.T_BRICK);
      c.L(leg, lu, lv, y0 + ht - 1, T_CARVED);
      if ((lv + lu) % 3 === 0) c.src(lu + 0.5, lv + 0.5, y0 + 1, [0.4, 0.8, 0.9], 2.2, 8, {});
    }
    for (let lv = c.lo + 1; lv < c.hi; lv += 5) for (let lu = -hw; lu < hw; lu++) if (c.LG(leg, lu, lv, y0 + ht - 1) === T_AIR) c.L(leg, lu, lv, y0 + ht - 1, T_BRICK);
    for (let lv = c.lo + 1; lv < c.hi; lv += 10) c.torchAt(leg, -1, lv, y0 + 3, 1, { I: 2.2 });
    for (let lv = c.lo; lv < c.hi; lv += 3) for (const lu of [-2, 1]) c.put("fence", lu + (lu < 0 ? 0.9 : 0.1), lv + 0.5, y0, { h: 0.9, tex: "planks_oak" });
    c.scatter(24, 245, (q, r1, r2) => c.put("lily", (r2 < 0.5 ? -1 : 1) * (2 + r2 * 6), c.lo + r1 * (c.hi - c.lo), y0 - 0.28, { ry: q }));
    c.scatter(14, 246, (q, r1, r2) => { const [x, , z] = c.W3(leg, (r2 - 0.5) * hw * 1.8, c.lo + r1 * (c.hi - c.lo), 0); c.a.emit.push({ k: "drip", x, y: y0 + ht - 0.3, z, floorY: y0 - 0.3 }); });
    rough(c, { depth: 2 }); F(c, [["vines", { n: 16, h: 2.4 }]]);
  } });

// ---- S4: the two-level library with a balcony -----------------------------------------------------------------------------------
def("library_balcony", { style: wall([[300, T_BRICK], [560, B.T_PLANK_SPRUCE], [800, T_BRICK_CRACK], [1000, T_BRICK]]), hw: [7, 7], ht: [11, 11], pre: [3, 3], post: [3, 3], m: [5, 6], branch: [0, 0], step: 8,
  floor: ({ lu, hv }) => (Math.abs(lu + 0.5) < 1.5 ? B.T_PLANK_DARK : hv < 300 ? B.T_PLANK : T_BRICK), alcovePil: B.T_LOG_SPRUCE, alcoveLin: B.T_SHELF,
  prof: P([0.115, 0.082, 0.052], [0.052, 0.035, 0.022], 0.034, 1.22, 1.05, 0.38),
  dress(c) {
    const { leg, y0, hw, ht } = c, clear = clearer(c), yd = y0 + 5;
    for (let lv = c.lo; lv < c.hi; lv++) for (const sd of [-1, 1]) {
      const a = sd > 0 ? hw - 1 : -hw, b = sd > 0 ? hw - 2 : -hw + 1;
      for (const lu of [a, b]) c.L(leg, lu, lv, yd, B.T_PLANK_SPRUCE);
      if (clear(sd, lv, 0)) for (let j = 6; j <= 8; j++) c.L(leg, a, lv, y0 + j, B.T_SHELF);
      if (clear(sd, lv, 1)) for (let j = 0; j <= 3; j++) c.L(leg, a, lv, y0 + j, j === 0 ? B.T_PLANK : B.T_SHELF);
      c.put("fence", (sd > 0 ? hw - 2 : -hw + 2) + (sd > 0 ? 0 : 0) , lv + 0.5, y0 + 6, { h: 0.9, tex: "planks_spruce" });
    }
    for (let lv = c.lo + 1; lv < c.hi; lv += 4) for (const sd of [-1, 1]) { const lu = sd > 0 ? hw - 3 : -hw + 2; c.col(lu, lv, y0, yd - 1, B.T_LOG_SPRUCE); c.torchAt(leg, lu, lv, y0 + 3, sd > 0 ? 1 : -1, { I: 2.8 }); }
    for (let lv = c.lo + 1; lv < c.hi; lv += 3) for (const sd of [-1, 1]) { const lu = sd > 0 ? hw - 2 : -hw + 1; c.lamp(lu, lv, y0 + 6, T_GLOW, [1.0, 0.8, 0.45], 3.8, 13); }
    for (let lv = c.lo + 2; lv < c.hi; lv += 8) { for (const lu of [-3, 2]) { c.L(leg, lu, lv, y0 + ht - 4, T_GLOW); c.col(lu, lv, y0 + ht - 3, y0 + ht - 1, B.T_PLANK_SPRUCE); c.src(lu + 0.5, lv + 0.5, y0 + ht - 4, [1.0, 0.82, 0.5], 3.6, 12, {}); } }
    for (let lv = c.lo + 3, q = 0; lv < c.hi - 2; lv += 9, q++) c.put("enchanting", q % 2 ? 2.5 : -2.5, lv + 0.5, y0, {});   // the reason for the shelves
    for (let lv = c.leg.cs + 1; lv < c.leg.ce - 1; lv++) if (lv % 5 === 0) for (let lu = -hw; lu < hw; lu++) if (c.LG(leg, lu, lv, y0 + ht - 1) === T_AIR) c.L(leg, lu, lv, y0 + ht - 1, B.T_LOG_SPRUCE);
    F(c, [["webs", { n: 12, w: 2.2 }]]);
  } });

// ---- S5: the sand temple's central chamber, blue clay and the TNT pit ----------------------------------------------------------------
def("sand_chamber", { style: wall([[400, B.T_SANDSTONE], [650, B.T_SANDSTONE_S], [840, B.T_SANDSTONE_C], [1000, B.T_SAND]]), hw: [7, 7], ht: [9, 9], pre: [3, 3], post: [3, 3], m: [4, 5], branch: [0, 0], step: 8, holes: [0.5],
  floor: ({ lu, lv, hv }) => (((lu >> 1) + (lv >> 1)) & 1 ? B.T_SANDSTONE_S : cl("orange")), alcovePil: B.T_SANDSTONE_C, alcoveLin: cl("orange"),
  prof: P([0.14, 0.11, 0.075], [0.07, 0.055, 0.034], 0.036, 1.28, 1.15, 0.42),
  dress(c) {
    const { leg, y0, hw, ht } = c, vc = Math.round((c.lo + c.hi) / 2);
    // The centre: a blue clay square with the pit open beside the walk, TNT stacked below, the plate waiting on a plinth.
    for (let dv = -3; dv <= 3; dv++) for (let lu = -4; lu <= 3; lu++) c.L(leg, lu, vc + dv, y0 - 1, (Math.abs(dv) === 3 || lu === -4 || lu === 3) ? cl("blue") : cl("light_blue"));
    for (let dv = -2; dv <= 2; dv++) for (const lu of [-3, -2, 1, 2]) { c.L(leg, lu, vc + dv, y0 - 1, T_AIR); c.L(leg, lu, vc + dv, y0 - 2, B.T_TNT); c.L(leg, lu, vc + dv, y0 - 3, B.T_TNT); c.L(leg, lu, vc + dv, y0 - 4, B.T_SANDSTONE); }
    for (let dv = -3; dv <= 3; dv++) for (const lu of [-1, 0]) c.L(leg, lu, vc + dv, y0 - 1, cl("blue"));
    for (const lu of [-5, 4]) for (const dv of [-4, 4]) { c.col(lu, vc + dv, y0, y0 + ht - 2, B.T_SANDSTONE_C); c.L(leg, lu, vc + dv, y0 + ht - 1, cl("orange")); c.torchAt(leg, lu, vc + dv, y0 + 3, lu < 0 ? 1 : -1, { I: 3.2, c: [1, 0.78, 0.4] }); }
    for (const lu of [-3, 2]) c.put("plate", lu + 0.5, vc + 0.5, y0 - 0.9, {});
    for (let lv = c.lo + 1; lv < c.hi; lv += 4) for (const lu of [-2, 1]) c.lamp(lu, lv, y0 + ht - 1, B.T_GLOW, [1, 0.8, 0.45], 3.2, 12);
    for (let lv = c.lo; lv < c.hi; lv += 5) for (const sd of [-1, 1]) if (clearer(c)(sd, lv, 1)) c.put("banner", sd * (hw - 0.1), lv + 0.5, y0 + 3, { ry: c.acrossRy, w: 0.9, h: 3, color: 4 });
    rough(c, { depth: 1, up: 4 });
  } });

// ---- S6: the ice cavern: natural, irregular, no pillars --------------------------------------------------------------------------------------
def("ice_cavern", { style: wall([[420, B.T_PACKED_ICE], [700, B.T_SNOW], [850, T_STONE], [1000, B.T_PACKED_ICE]]), hw: [9, 10], ht: [10, 12], pre: [3, 3], post: [3, 3], m: [5, 6], branch: [0, 0], step: 8, holes: [0.5],
  floor: ({ hv, lu, lv }) => (hv < 600 ? B.T_SNOW : B.T_PACKED_ICE), alcovePil: B.T_PACKED_ICE, alcoveLin: B.T_SNOW,
  prof: P([0.09, 0.13, 0.2], [0.04, 0.065, 0.1], 0.034, 1.28, 0.9, 0.5),
  dress(c) {
    const { leg, y0, hw, ht } = c, clear = clearer(c);
    rough(c, { depth: 3 });
    spikes(c, B.T_PACKED_ICE, 90, 5);
    c.scatter(40, 250, (q, r1, r2, r3) => { const lu = Math.floor(-hw + r2 * 2 * hw), lv = Math.floor(c.lo + r1 * (c.hi - c.lo)); if (Math.abs(lu + 0.5) < 2 || !clear(lu < 0 ? -1 : 1, lv, 1)) return; const h = 1 + Math.floor(r3 * (q % 5 === 0 ? 6 : 3)); for (let j = 0; j < h; j++) c.L(leg, lu, lv, y0 + j, j > h - 2 ? B.T_PACKED_ICE : B.T_SNOW); });
    c.scatter(14, 251, (q, r1, r2) => c.src((r2 - 0.5) * hw * 1.6, c.lo + r1 * (c.hi - c.lo), y0 + ht - 2.5, [0.55, 0.8, 1.0], 3.4, 13, {}));
    for (let lv = c.lo + 2; lv < c.hi; lv += 9) c.lamp(Math.round((lv % 3) - 1), lv, y0 + ht - 1, B.T_GLOW, [0.6, 0.85, 1.0], 3.0, 12);
    F(c, [["torches", { every: 8, off: 1, I: 2.6, color: [0.6, 0.85, 1.0] }]]);
  } });

// ---- S7: the cavern of giant mushrooms --------------------------------------------------------------------------------------------------------------
def("mushroom_cavern", { style: wall([[400, B.T_MYCELIUM], [600, T_STONE], [800, B.T_MUSH_BROWN], [1000, B.T_MUSH_RED]]), hw: [9, 10], ht: [11, 13], pre: [3, 3], post: [3, 3], m: [5, 6], branch: [0, 0], step: 8, holes: [0.5],
  floor: ({ hv }) => (hv < 720 ? B.T_MYCELIUM : B.T_PODZOL), alcovePil: B.T_MUSH_STEM, alcoveLin: B.T_MUSH_BROWN,
  prof: P([0.12, 0.08, 0.14], [0.055, 0.035, 0.075], 0.036, 1.26, 1.1, 0.46),
  dress(c) {
    const { leg, y0, hw, ht } = c, clear = clearer(c);
    rough(c, { depth: 3 }); spikes(c, B.T_MUSH_BROWN, 40, 3);
    let n = 0;
    c.scatter(26, 255, (q, r1, r2, r3) => {
      const lu = Math.floor(-hw + 2 + r2 * (2 * hw - 4)), lv = Math.floor(c.lo + 2 + r1 * (c.hi - c.lo - 4)), sd = lu < 0 ? -1 : 1;
      if (Math.abs(lu + 0.5) < 3.5 || !clear(sd, lv, 3)) return;
      const h = 4 + Math.floor(r3 * 5), cap = q % 2 ? B.T_MUSH_RED : B.T_MUSH_BROWN;
      for (let j = 0; j < h; j++) c.L(leg, lu, lv, y0 + j, B.T_MUSH_STEM);
      for (let du = -2; du <= 2; du++) for (let dv = -2; dv <= 2; dv++) { if (Math.abs(du) === 2 && Math.abs(dv) === 2) continue; if (Math.abs(lu + du + 0.5) > hw - 1) continue; c.L(leg, lu + du, lv + dv, y0 + h, cap); if (Math.abs(du) === 2 || Math.abs(dv) === 2) c.L(leg, lu + du, lv + dv, y0 + h - 1, cap); }
      c.src(lu + 0.5, lv + 0.5, y0 + h - 1.5, q % 2 ? [1.0, 0.4, 0.5] : [0.8, 0.5, 1.0], 3.0, 11, {}); n++;
    });
    c.scatter(18, 256, (q, r1, r2, r3) => c.put("cross", (r2 - 0.5) * hw * 1.9, c.lo + r1 * (c.hi - c.lo), y0, { tex: q % 2 ? "mushroom_red" : "mushroom_brown", s: 0.7 }));
    for (let lv = c.lo + 2; lv < c.hi; lv += 8) c.lamp(((lv >> 3) % 3) - 1, lv, y0 + ht - 1, B.T_GLOW, [0.7, 0.4, 1.0], 3.0, 12);
    void n;
  } });

// ---- S8: the fortress bridge out over a sea of lava ---------------------------------------------------------------------------------------------
def("fortress_bridge", { style: wall([[600, T_NBRICK], [850, T_NETHER], [940, B.T_SOUL], [1000, T_NBRICK]]), hw: [10, 10], ht: [13, 13], pre: [3, 3], post: [3, 3], m: [5, 6], branch: [0, 0], step: 8, below: D + 3, holes: [],
  floor: ({ lu, leg }) => (lu >= -1 && lu <= 0 ? T_NBRICK : { from: leg.y0 - D, cells: [[leg.y0 - D - 1, T_BEDROCK], [leg.y0 - D, T_LAVA]], lava: true }),
  alcoveBase: (leg) => leg.y0 - D + 1, alcovePil: T_NBRICK, alcoveLin: T_NBRICK, lavaI: 16, lavaDepth: D,
  prof: P([0.2, 0.08, 0.05], [0.1, 0.03, 0.02], 0.028, 1.3, 1.3, 0.55, { pitch: -0.2 }),
  dress(c) {
    const { leg, y0, hw, ht } = c;
    rough(c, { depth: 3 }); spikes(c, T_NETHER, 60, 5);
    for (let lv = c.lo; lv < c.hi + 2; lv++) for (const lu of [-2, 1]) { const [x, , z] = c.W3(leg, lu + (lu < 0 ? 0.14 : 0.86), lv + 0.5, 0), [bx, bz] = c.dirw(leg, 0, 1); c.a.decor.push({ t: "nfence", x: x - bx * 0.5, y: y0, z: z - bz * 0.5, ry: c.yaw, bx, bz, rails: true }); }
    for (let lv = c.lo + 2; lv < c.hi; lv += 8) { for (const lu of [-3, 2]) { c.col(lu, lv, y0 - D + 1, y0 + 3, T_NBRICK); c.torchAt(leg, lu, lv, y0 + 3, lu < 0 ? 1 : -1, { I: 3.4, c: [1, 0.45, 0.15] }); } for (let lu = -3; lu <= 2; lu++) c.L(leg, lu, lv, y0 + 3, T_NBRICK); }
    for (let lv = c.lo + 1; lv < c.hi; lv += 6) c.lamp(((lv * 7) % 9) - 4, lv, y0 + ht - 1, T_GLOW, [1, 0.5, 0.2], 3.4, 13);
    c.scatter(8, 260, (q, r1, r2) => c.a.emit.push({ k: "lava", ...(() => { const [x, , z] = c.W3(leg, (r2 - 0.5) * hw * 1.7, c.lo + r1 * (c.hi - c.lo), 0); return { x, z }; })(), y: y0 - D + 1 }));
  } });

// ---- S9: the arena: pits to both sides of a causeway, tiers of seats rising to the niches --------------------------------------------------------------
def("arena", { style: wall([[400, T_BRICK], [650, T_STONE], [860, T_BRICK_CRACK], [1000, B.T_IRONB]]), hw: [8, 8], ht: [9, 9], pre: [3, 3], post: [3, 3], m: [5, 6], branch: [0, 0], step: 8, below: 5,
  floor: ({ lu, lv, leg, hv }) => ((lu === -1 || lu === 0 || lv < leg.b0 + 7 || lv > leg.ce - 8) ? (hv < 250 ? T_BRICK_CRACK : T_BRICK) : (Math.abs(lu + 0.5) < 5 ? { from: leg.y0 - 3, cells: [[leg.y0 - 4, B.T_SAND]] } : T_BRICK)),
  alcoveBase: (leg) => leg.y0, alcovePil: B.T_IRONB, alcoveLin: T_STONE,
  prof: P([0.09, 0.085, 0.095], [0.04, 0.038, 0.046], 0.036, 1.22, 1.15, 0.36),
  dress(c) {
    const { leg, y0, hw, ht } = c;
    for (let lv = c.lo + 2; lv < c.hi - 1; lv++) for (const lu of [-2, 1]) c.put("bars", lu + (lu < 0 ? 1 : 0), lv + 0.5, y0 + 1, { ry: c.yaw, w: 1, h: 2 });
    for (let lv = c.lo + 2; lv < c.hi - 1; lv++) for (const sd of [-1, 1]) for (let t = 0; t < 3; t++) { const lu = sd > 0 ? 5 + t : -6 - t; for (let j = 0; j <= t; j++) c.L(leg, lu, lv, y0 + j, T_STONE); }
    for (let lv = c.lo + 4; lv < c.hi - 3; lv += 7) { c.put("mob", -3.5, lv + 0.5, y0 - 3, { mob: "Skeleton", ry: 1.57, scale: 0.9 }); c.put("mob", 3.5, lv + 3.5, y0 - 3, { mob: "Zombie", ry: -1.57, scale: 0.9 }); c.put("bone", 3.0, lv + 0.5, y0 - 2.95, { ry: lv }); }
    for (let lv = c.lo + 3; lv < c.hi - 1; lv += 8) for (const lu of [-1, 0]) { c.col(lu === -1 ? -3 : 2, lv, y0, y0 + ht - 2, B.T_IRONB); }
    for (let lv = c.lo + 3; lv < c.hi - 1; lv += 8) for (const lu of [-3, 2]) c.torchAt(leg, lu, lv, y0 + 4, lu < 0 ? 1 : -1, { I: 3.2 });
    for (let lv = c.lo + 1; lv < c.hi; lv += 6) c.lamp(((lv >> 2) % 2) - 1, lv, y0 + ht - 1, B.T_GLOW, [1, 0.85, 0.55], 3.4, 12);
    c.a.sources.push(...[]);
    c.scatter(8, 262, (q, r1, r2) => c.put("rubble", (r2 < 0.5 ? -1 : 1) * (2.5 + r2 * 2), c.lo + 3 + r1 * (c.hi - c.lo - 6), y0 - 3, { s: 0.4, ry: q }));
    F(c, [["webs", { n: 6, w: 2 }]]);
  } });

// ---- S10: the lava chasm: a bridge with open drops on both sides --------------------------------------------------------------------------------------
def("chasm_open", { style: wall([[420, T_STONE], [700, T_COBBLE], [880, T_BEDROCK], [1000, T_OBS]]), hw: [10, 10], ht: [12, 12], pre: [3, 3], post: [3, 3], m: [5, 6], branch: [0, 0], step: 8, below: D + 3, holes: [0.4, 0.8],
  floor: ({ lu, leg }) => (lu >= -2 && lu < 2 ? B.T_BRIDGE : { from: leg.y0 - D, cells: [[leg.y0 - D - 1, T_BEDROCK], [leg.y0 - D, T_LAVA]], lava: true }),
  alcoveBase: (leg) => leg.y0 - D + 1, alcovePil: T_STONE, alcoveLin: T_BRICK, lavaI: 40, lavaDepth: D,
  prof: P([0.12, 0.05, 0.03], [0.075, 0.028, 0.014], 0.028, 1.24, 0.85, 0.5, { pitch: -0.3 }),
  dress(c) {
    const { leg, y0, hw, ht } = c;
    rough(c, { depth: 3 }); spikes(c, T_STONE, 70, 6);
    for (let lv = c.lo + 3; lv < c.hi; lv += 10) { for (const lu of [-3, 2]) { c.col(lu, lv, y0 - D + 1, y0 + 4, T_STONE); c.torchAt(leg, lu, lv, y0 + 3, lu < 0 ? 1 : -1, { I: 3.2 }); } for (let lu = -3; lu <= 2; lu++) { c.L(leg, lu, lv, y0 + 5, T_BRICK); } for (const lu of [-3, 2]) c.L(leg, lu, lv, y0 + 5, T_CARVED); }
    // Pillars of rock standing out of the lava.
    c.scatter(14, 265, (q, r1, r2, r3) => { const lu = Math.floor(-hw + 1 + r2 * (2 * hw - 2)); if (Math.abs(lu + 0.5) < 4) return; const lv = Math.floor(c.lo + r1 * (c.hi - c.lo)), h = D - 1 + Math.floor(r3 * 6); for (let j = 1; j < h; j++) c.L(leg, lu, lv, y0 - D + j, T_STONE); });
    c.scatter(10, 266, (q, r1, r2) => c.src((r2 - 0.5) * hw * 1.7, c.lo + r1 * (c.hi - c.lo), y0 - D + 2.5, [1, 0.36, 0.08], 6, 16, { lava: true, dyn: true }));
  } });

// ---- S11: the void bridge: no walls, a starfield, islands of end stone ----------------------------------------------------------------------------------------
def("void_bridge", { margin: 3, style: wall([[600, B.T_ENDSTONE], [850, T_OBS], [1000, B.T_ENDSTONE]]), hw: [10, 10], ht: [14, 14], pre: [3, 3], post: [3, 3], m: [5, 6], branch: [0, 0], step: 8, below: D + 4, holes: [],
  floor: ({ lu, leg }) => ((lu === -1 || lu === 0) ? T_OBS : { from: leg.y0 - D - 2, cells: [[leg.y0 - D - 3, T_BEDROCK]] }),
  alcoveBase: (leg) => leg.y0 - 2, alcovePil: T_OBS, alcoveLin: B.T_ENDSTONE,
  prof: P([0.075, 0.05, 0.12], [0.04, 0.03, 0.09], 0.03, 1.32, 1.2, 0.65, { pitch: -0.2 }),
  dress(c) {
    const { leg, y0, hw, ht } = c;
    for (let lv = leg.cs; lv < leg.ce; lv++) for (let lu = -hw - 4; lu < hw + 4; lu++) for (let j = 0; j < 12; j++) c.L(leg, lu, lv, y0 + ht - 3 + j, T_AIR);
    c.scatter(22, 270, (q, r1, r2, r3) => {
      const lu = Math.floor(-hw + 1 + r2 * (2 * hw - 2)); if (Math.abs(lu + 0.5) < 3) return;
      const lv = Math.floor(c.lo + r1 * (c.hi - c.lo)), yy = y0 - 3 - Math.floor(r3 * 6), rr = 1 + (q % 3);
      for (let du = -rr; du <= rr; du++) for (let dv = -rr; dv <= rr; dv++) if (du * du + dv * dv <= rr * rr + 1 && Math.abs(lu + du + 0.5) < hw) { c.L(c.leg, lu + du, lv + dv, yy, B.T_ENDSTONE); if (du * du + dv * dv < rr * rr) c.L(c.leg, lu + du, lv + dv, yy - 1, B.T_ENDSTONE); }
      if (q % 4 === 0) for (let j = 1; j < 5; j++) c.L(leg, lu, lv, yy + j, T_OBS);
      c.src(lu + 0.5, lv + 0.5, yy + 2, [0.7, 0.45, 1.0], 3.0, 11, {});
    });
    for (let lv = c.lo + 1; lv < c.hi; lv += 6) for (const lu of [-2, 1]) { c.col(lu, lv, y0, y0 + 1, T_OBS); c.src(lu + 0.5, lv + 0.5, y0 + 1.8, [0.8, 0.5, 1.0], 2.8, 9, {}); c.L(leg, lu, lv, y0 + 2, B.T_GLOW); }
    for (let lv = c.lo + 3; lv < c.hi; lv += 12) { for (const lu of [-3, 2]) c.col(lu, lv, y0 - 2, y0 + 5, T_OBS); for (let lu = -3; lu <= 2; lu++) c.L(leg, lu, lv, y0 + 6, T_OBS); }
    void ht;
  } });

// ---- S12: the hollow hill: an earthen dome with a mound, bushes and lights in the leaves ------------------------------------------------------------------------
def("hollow_hill", { style: wall([[420, T_DIRT], [680, B.T_GRASS], [860, T_STONE], [1000, B.T_LEAVES_OAK]]), hw: [9, 9], ht: [10, 10], pre: [3, 3], post: [3, 3], m: [5, 6], branch: [0, 0], step: 8, holes: [0.5],
  floor: ({ hv }) => (hv < 600 ? B.T_GRASS : hv < 800 ? B.T_PODZOL : T_DIRT), alcovePil: B.T_LOG, alcoveLin: B.T_LEAVES_OAK,
  prof: P([0.09, 0.13, 0.08], [0.04, 0.07, 0.035], 0.036, 1.22, 1.1, 0.4),
  dress(c) {
    const { leg, y0, hw, ht } = c, vc = Math.round((c.lo + c.hi) / 2), clear = clearer(c);
    rough(c, { depth: 2 }); spikes(c, T_DIRT, 50, 3);
    // The mound: a dome of grass and dirt, a doorway into it, with a glow inside.
    for (let du = -4; du <= 4; du++) for (let dv = -4; dv <= 4; dv++) { const r = Math.sqrt(du * du + dv * dv), h = Math.round(4.5 - r); const lu = 4 + du; if (h <= 0 || lu >= hw || lu < 2) continue; for (let j = 0; j < h; j++) c.L(leg, lu, vc + dv, y0 + j, j === h - 1 ? B.T_GRASS : T_DIRT); }
    for (let j = 0; j < 2; j++) c.L(leg, 2, vc, y0 + j, T_AIR); c.src(3.5, vc + 0.5, y0 + 1, [1, 0.8, 0.45], 3.0, 9, {});
    c.scatter(26, 275, (q, r1, r2, r3) => { const lu = Math.floor(-hw + r2 * 2 * hw), lv = Math.floor(c.lo + r1 * (c.hi - c.lo)); if (lu >= 0 || Math.abs(lu + 0.5) < 2 || !clear(-1, lv, 1)) return; const h = 1 + (q % 3); for (let j = 0; j < h; j++) c.L(leg, lu, lv, y0 + j, B.T_LEAVES_OAK); if (q % 4 === 0) c.lamp(lu, lv, y0 + h, T_GLOW, [1, 0.9, 0.5], 2.8, 9); });
    for (let lv = c.lo + 2; lv < c.hi; lv += 7) { c.col(-5, lv, y0, y0 + ht - 2, B.T_LOG); for (let du = -2; du <= 0; du++) c.L(leg, -5 + du, lv, y0 + ht - 2, B.T_LEAVES_OAK); }
    c.scatter(30, 276, (q, r1, r2) => c.put("cross", (r2 - 0.5) * hw * 1.8, c.lo + r1 * (c.hi - c.lo), y0, { tex: ["tallgrass", "fern", "flower_tulip_red", "flower_blue_orchid"][q % 4], s: 0.8 }));
    for (let lv = c.lo + 2; lv < c.hi; lv += 8) c.lamp(((lv >> 3) % 3) - 2, lv, y0 + ht - 1, T_GLOW, [1, 0.9, 0.55], 3.2, 12);
    F(c, [["vines", { n: 18, h: 2.4 }]]);
  } });

void pool; void T_WATER; void T_LOG; void T_MOSSY; void T_NETHER;
