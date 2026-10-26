// Kinds of the deeper strata: libraries and treasuries, sandstone temples, ice, fungal and overgrown halls, the nether,
// armouries, and the end. Catalogue entries 22-60, vanilla blocks only; each kind is a palette, a rhythm and a signature.
import * as B from "./blocks.js";
import { def, wall, P } from "./kindreg.js";
import { F, FEATURES, pool, rectOf, clearer } from "./kindlib.js";
const { T_AIR, T_BRICK, T_COBBLE, T_STONE, T_BRICK_CRACK, T_BRICK_MOSSY, T_MOSSY, T_GRAVEL_FLOOR, T_CARVED, T_SLAB, T_LAVA, T_OBS, T_GLOW, T_SHELF, T_PLANK, T_LOG,
  T_SANDSTONE, T_SANDSTONE_C, T_SANDSTONE_S, T_SAND, T_PACKED_ICE, T_SNOW, T_NBRICK, T_NETHER, T_SOUL, T_ENDSTONE, T_GOLD, T_LAPIS, T_IRONB, T_COAL_BLOCK, T_REDSTONE_BLOCK } = B;
const wl = B.wool, cl = B.clay;

// ---- Stratum 4: libraries, vaults, laboratories ----------------------------------------------------------------
def("scriptorium", { style: wall([[300, T_BRICK], [560, T_PLANK], [800, T_SHELF], [1000, T_BRICK_CRACK]]), hw: [4, 4], ht: [6, 6], pre: [3, 3], m: [6, 9], branch: [0, 1], step: 6,
  floor: ({ hv, lu }) => (Math.abs(lu + 0.5) < 1.5 ? B.T_PLANK_DARK : hv < 300 ? T_PLANK : T_BRICK),
  prof: P([0.1, 0.075, 0.055], [0.044, 0.032, 0.024], 0.04, 1.2, 1.1, 0.34),
  dress(c) {
    F(c, [["pillars", { every: 6, off: 1, tile: B.T_LOG_SPRUCE, h: c.ht - 1, torch: 3, I: 3 }], ["band", { tile: T_SHELF, j0: 0, j1: 2, every: 1, sides: [-1, 1] }],
      ["ribs", { every: 6, off: 1, tile: B.T_LOG_SPRUCE, y: 1 }], ["webs", { n: 8 }]]);
    for (let lv = c.lo + 3; lv < c.hi - 2; lv += 8) c.put("cube", 0.5 - 1.2, lv + 0.5, c.y0, { side: "crafting_table_side", top: "crafting_table_top", ry: 0, h: 1 });
  } });
def("treasury", { style: wall([[360, T_BRICK], [700, T_STONE], [860, T_CARVED], [1000, T_BRICK_CRACK]]), hw: [4, 4], ht: [5, 5], pre: [3, 3], m: [6, 8], branch: [0, 1], step: 6,
  floor: ({ lu, lv, hv }) => (Math.abs(lu + 0.5) < 1.5 ? ((lv % 2) ? T_GOLD : T_LAPIS) : T_BRICK),
  prof: P([0.11, 0.1, 0.07], [0.05, 0.042, 0.03], 0.038, 1.24, 1.3, 0.42),
  dress(c) {
    F(c, [["alcoves", { style: "cap", tile: T_GOLD }], ["between", { tile: T_LAPIS, h: c.ht - 1, torch: 2, I: 3.2, cap: T_GOLD, color: [1.0, 0.8, 0.4] }], ["torches", { every: 5, off: 1, I: 3.0, y: 3, color: [1.0, 0.8, 0.4] }]]);
    for (let lv = c.lo + 2; lv < c.hi - 1; lv += 7) { for (const sd of [-1, 1]) if (clearer(c)(sd, lv, 1)) c.put("chest", sd * (c.hw - 1.1), lv + 0.5, c.y0, { ry: c.faceRy(sd) }); }
  } });
def("alchemy_lab", { style: wall([[420, T_BRICK], [700, T_BRICK_MOSSY], [900, T_COBBLE], [1000, T_COAL_BLOCK]]), hw: [3, 4], ht: [5, 5], pre: [2, 2], m: [6, 9], branch: [1, 1], step: 8,
  floor: ({ hv }) => (hv < 250 ? T_BRICK_MOSSY : T_BRICK),
  prof: P([0.07, 0.1, 0.07], [0.03, 0.045, 0.03], 0.04, 1.2, 1.05, 0.34),
  dress(c) {
    const clear = clearer(c);
    for (let lv = c.lo + 2; lv < c.hi - 1; lv += 5) { const sd = (lv / 5 | 0) % 2 ? 1 : -1; if (!clear(sd, lv, 1)) continue; c.put("cauldron", sd * (c.hw - 0.9), lv + 0.5, c.y0, { water: c.rnd(lv, 80) < 0.5 }); c.src(sd * (c.hw - 0.9), lv + 0.5, c.y0 + 1.1, [0.4, 1.0, 0.5], 2.0, 6, {}); }
    F(c, [["alcoves", { style: "bars" }], ["roofLamps", { every: 7, off: 2, tile: T_GLOW, color: [0.5, 1.0, 0.55], I: 2.8, lus: [0] }], ["webs", { n: 8 }], ["torches", { every: 6, off: 1, I: 2.5 }]]);
  } });

// ---- Stratum 5: sandstone temples ------------------------------------------------------------------------------
def("sand_temple", { style: wall([[400, T_SANDSTONE], [650, T_SANDSTONE_S], [840, T_SANDSTONE_C], [1000, T_SAND]]), hw: [3, 4], ht: [5, 5], pre: [2, 3], m: [6, 9], branch: [0, 1], step: 6,
  floor: ({ hv, lu }) => (Math.abs(lu + 0.5) < 1.5 ? T_SANDSTONE_S : hv < 400 ? T_SANDSTONE : T_SAND),
  prof: P([0.14, 0.11, 0.07], [0.07, 0.055, 0.032], 0.036, 1.26, 1.2, 0.4),
  dress(c) {
    F(c, [["alcoves", { style: "cap", tile: T_SANDSTONE_C }], ["between", { tile: T_SANDSTONE_C, h: c.ht - 1, torch: 2, I: 3.0, cap: T_SANDSTONE_S, color: [1.0, 0.75, 0.4] }],
      ["band", { tile: cl("orange"), j0: 2, j1: 2, every: 1 }], ["runner", { lu0: -1, lu1: 0, tile: cl("red"), every: 4 }]]);
  } });
def("sun_hall", { style: wall([[500, T_SANDSTONE_S], [800, T_SANDSTONE], [920, cl("yellow")], [1000, T_SANDSTONE_C]]), hw: [4, 5], ht: [6, 6], pre: [3, 3], m: [5, 8], branch: [0, 0], step: 8,
  floor: ({ lu, lv }) => (((lu + lv) & 1) ? T_SANDSTONE_S : cl("yellow")),
  prof: P([0.18, 0.15, 0.1], [0.09, 0.075, 0.045], 0.03, 1.3, 0.9, 0.5),
  dress(c) {
    F(c, [["roofLamps", { every: 4, off: 1, tile: T_GLOW, color: [1.0, 0.86, 0.5], I: 3.6, R: 12, lus: [-2, 1] }], ["pillars", { every: 8, off: 2, tile: T_SANDSTONE_C, h: c.ht - 1 }], ["alcoves", { style: "banner", color: 4 }]]);
  } });

// ---- Stratum 6: ice ---------------------------------------------------------------------------------------------
def("ice_grotto", { style: wall([[420, T_PACKED_ICE], [700, T_SNOW], [850, T_STONE], [1000, T_PACKED_ICE]]), hw: [3, 5], ht: [5, 6], pre: [2, 2], m: [6, 10], branch: [0, 1], below: 0,
  floor: ({ hv }) => (hv < 600 ? T_SNOW : T_PACKED_ICE),
  prof: P([0.1, 0.14, 0.2], [0.045, 0.07, 0.1], 0.036, 1.26, 0.9, 0.45),
  dress(c) {
    F(c, [["alcoves", { style: "cap", tile: T_PACKED_ICE }], ["torches", { every: 6, off: 1, I: 2.6, color: [0.6, 0.85, 1.0] }], ["roofLamps", { every: 8, off: 3, tile: T_GLOW, color: [0.55, 0.8, 1.0], I: 2.8, lus: [0] }]]);
    c.scatter(14, 90, (q, r1, r2) => { const lu = Math.floor(-c.hw + r2 * 2 * c.hw), lv = Math.floor(c.lo + r1 * (c.hi - c.lo)); const sd = lu < 0 ? -1 : 1; if (Math.abs(lu + 0.5) > c.hw - 1.5 && !clearer(c)(sd, lv, 0)) return; c.L(c.leg, lu, lv, c.y0 + c.ht - 1, T_PACKED_ICE); c.L(c.leg, lu, lv, c.y0 + c.ht - 2, T_PACKED_ICE); });
  } });
def("frost_hall", { style: wall([[500, T_STONE], [760, T_PACKED_ICE], [900, T_SNOW], [1000, T_BRICK_CRACK]]), hw: [3, 4], ht: [5, 5], pre: [2, 3], m: [6, 9], branch: [1, 1], step: 6,
  floor: ({ hv, lu }) => (Math.abs(lu + 0.5) < 1.5 ? T_PACKED_ICE : hv < 300 ? T_SNOW : T_BRICK),
  prof: P([0.09, 0.12, 0.18], [0.04, 0.06, 0.09], 0.04, 1.24, 0.95, 0.4),
  dress(c) {
    F(c, [["between", { tile: T_PACKED_ICE, h: c.ht - 1, torch: 2, I: 2.8, color: [0.6, 0.85, 1.0] }], ["arches", { tile: T_PACKED_ICE, key: T_SNOW, rise: 1 }], ["alcoves", { style: "bars" }]]);
  } });

// ---- Stratum 7: fungal and overgrown ---------------------------------------------------------------------------
def("mushroom_cave", { style: wall([[400, B.T_MYCELIUM], [600, T_STONE], [800, B.T_MUSH_BROWN], [1000, B.T_MUSH_RED]]), hw: [4, 5], ht: [5, 6], pre: [2, 2], m: [6, 9], branch: [1, 1],
  floor: ({ hv }) => (hv < 700 ? B.T_MYCELIUM : B.T_PODZOL),
  prof: P([0.11, 0.08, 0.13], [0.05, 0.035, 0.07], 0.04, 1.22, 1.1, 0.4),
  dress(c) {
    const clear = clearer(c);
    c.scatter(10, 95, (q, r1, r2) => { const sd = r2 < 0.5 ? -1 : 1, lv = Math.floor(c.lo + 1 + r1 * (c.hi - c.lo - 2)); if (!clear(sd, lv, 1)) return; const lu = c.edgeCell(sd); const h = 2 + (q % 2); for (let j = 0; j < h; j++) c.L(c.leg, lu, lv, c.y0 + j, B.T_MUSH_STEM); for (const du of [-1, 0, 1]) for (const dv of [-1, 0, 1]) { const cu = lu - sd * (du === 1 ? 1 : 0); if (c.LG(c.leg, cu, lv + dv, c.y0 + h) === T_AIR && !(du === 0 && dv === 0 && false)) c.L(c.leg, lu, lv + dv, c.y0 + h, q % 3 ? B.T_MUSH_RED : B.T_MUSH_BROWN); } c.src(lu + 0.5, lv + 0.5, c.y0 + h + 0.5, [0.75, 0.35, 0.9], 2.6, 7, {}); });
    F(c, [["roofLamps", { every: 7, off: 3, tile: B.T_GLOW, color: [0.7, 0.4, 1.0], I: 2.8, lus: [-1, 0] }], ["vines", { n: 10 }]]);
  } });
def("overgrown", { style: wall([[360, T_MOSSY], [600, B.T_GRASS], [800, T_BRICK_MOSSY], [1000, B.T_LEAVES_JUNGLE]]), hw: [3, 5], ht: [5, 6], pre: [2, 2], m: [6, 10], branch: [1, 1], holes: [0.5],
  floor: ({ hv, lu }) => (hv < 520 ? B.T_GRASS : hv < 760 ? B.T_PODZOL : T_BRICK_MOSSY),
  prof: P([0.1, 0.14, 0.08], [0.04, 0.065, 0.034], 0.038, 1.22, 1.1, 0.34),
  dress(c) {
    F(c, [["pillars", { every: 6, off: 1, tile: B.T_LOG_JUNGLE, h: c.ht - 1 }], ["vines", { n: 22, h: 2.4 }], ["alcoves", { style: "cap", tile: T_MOSSY }], ["roofLamps", { every: 7, off: 2, tile: B.T_GLOW, color: [0.8, 1.0, 0.5], I: 3.0, lus: [0] }]]);
    c.scatter(16, 100, (q, r1, r2) => { c.put("lily", (r2 - 0.5) * c.hw * 1.8, c.lo + r1 * (c.hi - c.lo), c.y0 + 0.05, { ry: q }); });
  } });

// ---- Stratum 8: the nether passage ----------------------------------------------------------------------------
def("nether_hall", { style: wall([[420, T_NBRICK], [740, T_NETHER], [900, T_SOUL], [1000, T_NBRICK]]), hw: [3, 4], ht: [5, 5], pre: [2, 3], m: [6, 9], branch: [0, 1], step: 6,
  floor: ({ hv, lu }) => (Math.abs(lu + 0.5) < 1.5 ? T_NBRICK : hv < 400 ? T_NETHER : T_SOUL),
  prof: P([0.13, 0.05, 0.04], [0.09, 0.03, 0.02], 0.04, 1.3, 1.15, 0.5),
  dress(c) {
    F(c, [["alcoves", { style: "cap", tile: T_NBRICK }], ["between", { tile: T_NBRICK, h: c.ht - 1, torch: 2, I: 3.2, color: [1.0, 0.4, 0.15], cap: T_OBS }], ["roofLamps", { every: 9, off: 3, tile: T_GLOW, color: [1.0, 0.5, 0.2], I: 3.2, lus: [-1] }]]);
    const mid = Math.round((c.lo + c.hi) / 2); pool(c, { lu0: 2, lu1: Math.min(3, c.hw - 1), lv0: mid, lv1: mid + 2, liquid: "lava" });
  } });
def("soul_gallery", { style: wall([[480, T_NBRICK], [700, T_SOUL], [900, T_NETHER], [1000, T_OBS]]), hw: [3, 3], ht: [6, 6], pre: [3, 3], m: [6, 8], branch: [0, 0], step: 6,
  floor: ({ lu, lv }) => (((lu + lv) & 1) ? T_SOUL : T_NBRICK),
  prof: P([0.07, 0.09, 0.14], [0.03, 0.04, 0.08], 0.042, 1.26, 1.2, 0.5),
  dress(c) {
    F(c, [["pillars", { every: 5, off: 1, tile: T_OBS, h: c.ht - 1, torch: 3, I: 3.0, color: [0.4, 0.75, 1.0] }], ["alcoves", { style: "bars" }], ["webs", { n: 6 }]]);
  } });
def("obsidian_vault", { style: wall([[350, T_OBS], [650, T_COBBLE], [850, T_STONE], [1000, T_COAL_BLOCK]]), hw: [3, 4], ht: [5, 5], pre: [2, 2], m: [6, 8], branch: [1, 1], step: 6,
  floor: ({ lu, hv }) => (Math.abs(lu + 0.5) < 1.5 ? T_OBS : hv < 500 ? T_COBBLE : T_STONE),
  prof: P([0.06, 0.055, 0.09], [0.026, 0.024, 0.045], 0.044, 1.2, 1.2, 0.5),
  dress(c) {
    F(c, [["between", { tile: T_OBS, h: c.ht - 1, torch: 2, I: 3.0, color: [0.8, 0.4, 1.0] }], ["alcoves", { style: "cap", tile: T_OBS }], ["band", { tile: T_REDSTONE_BLOCK, j0: 0, j1: 0, every: 3 }]]);
  } });

// ---- Stratum 9: halls of arms -----------------------------------------------------------------------------------
def("armory", { style: wall([[400, T_BRICK], [700, T_STONE], [880, T_IRONB], [1000, T_BRICK_CRACK]]), hw: [4, 4], ht: [5, 5], pre: [3, 3], m: [6, 9], branch: [0, 1], step: 6,
  floor: ({ lu, hv }) => (Math.abs(lu + 0.5) < 1.5 ? T_STONE : T_BRICK),
  prof: P([0.085, 0.085, 0.1], [0.036, 0.036, 0.046], 0.038, 1.2, 1.05, 0.3),
  dress(c) {
    const clear = clearer(c);
    for (let lv = c.lo + 2; lv < c.hi - 1; lv += 5) { const sd = (lv / 5 | 0) % 2 ? 1 : -1; if (!clear(sd, lv, 1)) continue; c.put("anvil", sd * (c.hw - 0.9), lv + 0.5, c.y0, { ry: c.sideRy(sd) }); }
    F(c, [["between", { tile: T_BRICK, h: c.ht - 1, torch: 2, I: 2.8 }], ["alcoves", { style: "bars" }], ["band", { tile: T_IRONB, j0: 3, j1: 3, every: 1 }]]);
  } });
def("barracks", { style: wall([[400, T_BRICK], [650, T_PLANK], [850, T_BRICK_CRACK], [1000, T_COBBLE]]), hw: [4, 4], ht: [5, 5], pre: [3, 3], m: [6, 8], branch: [1, 1], step: 6,
  floor: ({ hv }) => (hv < 300 ? T_PLANK : T_BRICK),
  prof: P([0.08, 0.075, 0.07], [0.034, 0.032, 0.03], 0.04, 1.2, 1.0, 0.3),
  dress(c) {
    const clear = clearer(c);
    for (let lv = c.lo + 2; lv < c.hi - 2; lv += 4) for (const sd of [-1, 1]) if (clear(sd, lv, 2)) c.put("bed", sd * (c.hw - 1.0), lv + 1, c.y0, { ry: c.faceRy(sd) + Math.PI / 2 });
    F(c, [["torches", { every: 8, off: 3, I: 2.6, y: 3 }], ["ribs", { every: 4, off: 1, tile: T_LOG, y: 1 }], ["webs", { n: 5 }]]);
  } });

// ---- Stratum 11: the end ---------------------------------------------------------------------------------------
def("end_hall", { style: wall([[550, T_ENDSTONE], [800, T_OBS], [930, T_ENDSTONE], [1000, T_OBS]]), hw: [3, 5], ht: [6, 7], pre: [2, 3], m: [6, 9], branch: [0, 0], step: 8,
  floor: ({ lu, hv }) => (Math.abs(lu + 0.5) < 1.5 ? T_OBS : T_ENDSTONE),
  prof: P([0.07, 0.05, 0.09], [0.04, 0.03, 0.07], 0.034, 1.3, 1.1, 0.6),
  dress(c) {
    F(c, [["pillars", { every: 6, off: 1, tile: T_OBS, h: c.ht - 1, torch: 3, I: 3.0, color: [0.8, 0.5, 1.0] }], ["alcoves", { style: "cap", tile: T_OBS }], ["roofLamps", { every: 9, off: 3, tile: T_GLOW, color: [0.8, 0.6, 1.0], I: 3.2, lus: [0] }]]);
  } });
def("wool_hall", { style: wall([[360, T_BRICK], [700, T_STONE], [1000, T_BRICK_CRACK]]), hw: [4, 4], ht: [6, 6], pre: [2, 2], m: [5, 8], branch: [0, 1], step: 6,
  floor: ({ lu, lv, hv }) => (Math.abs(lu + 0.5) < 1.5 ? wl(["red", "blue", "green", "purple"][(lv >> 2) & 3]) : T_BRICK),
  prof: P([0.1, 0.09, 0.09], [0.044, 0.04, 0.04], 0.038, 1.22, 1.1, 0.34),
  dress(c) {
    for (const s of c.leg.slots) for (const q of [-1.6, 1.6]) c.put("banner", s.side * (c.hw - 1 - 0.06), s.lvc + 0.5 + q, c.y0 + 2.4, { ry: c.acrossRy, w: 0.8, h: 2.6, color: (s.lvc >> 3) % 16 });
    F(c, [["between", { tile: T_BRICK, h: c.ht - 1, torch: 3, I: 2.8 }], ["arches", { tile: T_BRICK, key: T_CARVED, rise: 1 }]]);
  } });
void FEATURES; void rectOf; void T_SLAB; void T_LAVA; void T_GRAVEL_FLOOR; void T_LAPIS;
