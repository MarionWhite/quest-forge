// Architecture and palette for every kind. kinds_a/kinds_b give each kind a palette and a rhythm; this file gives it a SHAPE
// (hall width and height, vaulted, flat or cavern ceilings, colonnades, a catwalk level, collapsed sections, a maze) and its own
// alcove frame tiles, and adds the structures that were missing: the labyrinth, the collapsed hall, the void bridge and the
// stronghold's end-portal room. applyArch() runs after kinds.js has registered the round-5 kinds, so it can reshape them too.
import * as B from "./blocks.js";
import { KINDS, def, wall, P } from "./kindreg.js";
import { F, pool, rectOf, clearer } from "./kindlib.js";
const { T_AIR, T_BRICK, T_COBBLE, T_STONE, T_BRICK_CRACK, T_BRICK_MOSSY, T_MOSSY, T_GRAVEL_FLOOR, T_DIRT, T_CARVED, T_LAVA, T_OBS, T_GLOW, T_PLANK, T_LOG, T_BEDROCK, T_NBRICK, T_NETHER } = B;
const wl = B.wool, cl = B.clay;

// ---- shape features ---------------------------------------------------------------------------------------------
// A barrel vault: the centre lanes of the roof are carved up to `rise` blocks, stepping down toward the walls.
function vault(c, rise, tile = null) {
  const { leg, y0, ht, hw } = c;
  for (let lv = c.lo; lv < c.hi + 1; lv++) for (let lu = -hw; lu < hw; lu++) {
    const up = Math.max(0, rise - Math.floor(Math.abs(lu + 0.5)));
    for (let k = 0; k < up; k++) c.L(leg, lu, lv, y0 + ht + k, T_AIR);
    if (tile && up > 0 && lv % 4 === 1) c.L(leg, lu, lv, y0 + ht + up - 1, tile);   // a rib at the crown every four rows
  }
}
// Cavern: ragged roof (stalactites and domes), bulging walls and nooks. Only the edge lanes are touched on the floor side.
function cavern(c, o = {}) {
  const { leg, y0, ht, hw } = c, clear = clearer(c), tile = o.tile || T_STONE, hang = o.hang == null ? 1 : o.hang;
  for (let lv = c.lo; lv < c.hi + 1; lv++) for (let lu = -hw; lu < hw; lu++) {
    const r = c.rnd(lu * 977 + lv, 201), edge = lu === -hw || lu === hw - 1, sd = lu < 0 ? -1 : 1;
    if (r < 0.10 * hang) c.L(leg, lu, lv, y0 + ht - 1, tile);
    else if (r < 0.15 * hang && ht >= 6) { c.L(leg, lu, lv, y0 + ht - 1, tile); c.L(leg, lu, lv, y0 + ht - 2, tile); }
    else if (r > 0.90) { c.L(leg, lu, lv, y0 + ht, T_AIR); if (r > 0.96) c.L(leg, lu, lv, y0 + ht + 1, T_AIR); }
    if (edge && clear(sd, lv, 1)) {
      const r2 = c.rnd(lu * 31 + lv * 7, 202);
      if (r2 < 0.2) for (let j = 0; j < 1 + Math.floor(c.rnd(lv, 203) * 3); j++) c.L(leg, lu, lv, y0 + j, tile);
      else if (r2 > 0.86) for (let j = 0; j < 3; j++) c.L(leg, c.wallCell(sd), lv, y0 + j, T_AIR);
    }
  }
}
// Freestanding columns down the hall.
function colonnade(c, o = {}) {
  const { leg, y0, hw } = c, { every = 4, off = 1, tile = T_BRICK, cap = null, base = null, torch = 0, I = 2.8, color = null } = o;
  const lus = o.lus || (hw >= 4 ? [-3, 2] : [-2, 1]);
  for (let lv = c.lo + off; lv < c.hi; lv += every) for (const lu of lus) {
    const h = o.h || c.ht - 1;
    c.col(lu, lv, y0, y0 + h - 1, tile);
    if (base) c.L(leg, lu, lv, y0, base);
    if (cap) c.L(leg, lu, lv, y0 + h, cap);
    if (torch) c.torchAt(leg, lu, lv, y0 + torch, lu < 0 ? 1 : -1, { I, ...(color ? { c: color } : {}) });
  }
}
// A second level: side decks four blocks up on both sides, carried by the columns, with a rail of fence on the inner edge.
function catwalk(c, o = {}) {
  const { leg, y0, hw } = c, tile = o.tile || T_PLANK, post = o.post || T_LOG, lanes = hw >= 5 ? [[-4, -3], [2, 3]] : [[-3, -2], [1, 2]];
  const yd = y0 + (o.y || 4);
  for (let lv = c.lo; lv < c.hi; lv++) for (const [a, b] of lanes) for (let lu = a; lu <= b; lu++) c.L(leg, lu, lv, yd, tile);
  for (let lv = c.lo + 1; lv < c.hi; lv += 4) for (const [a, b] of lanes) {
    const lu = Math.abs(a + 0.5) < Math.abs(b + 0.5) ? a : b; // the inner lane of the deck
    c.col(lu, lv, y0, yd - 1, post);
    c.torchAt(leg, lu, lv, y0 + 2, lu < 0 ? 1 : -1, { I: o.I || 2.8, ...(o.color ? { c: o.color } : {}) });
  }
  for (let lv = c.lo + 1; lv < c.hi; lv++) for (const [a, b] of lanes) {
    const inner = Math.abs(a + 0.5) < Math.abs(b + 0.5) ? a : b, sd = a < 0 ? 1 : -1;
    c.put("fence", inner + (sd > 0 ? 1 : 0), lv + 0.5, yd + 1, { h: 0.9, tex: o.fence || "planks_oak" });
  }
}
// Heaps of fallen rock on the edge lanes and holes in the roof above them.
function collapse(c, n = 12, tile = T_COBBLE) {
  const { leg, y0, ht, hw } = c, clear = clearer(c);
  c.scatter(n, 210, (q, r1, r2, r3) => {
    const sd = r2 < 0.5 ? -1 : 1, lv = Math.floor(c.lo + 1 + r1 * (c.hi - c.lo - 2));
    if (!clear(sd, lv, 1)) return;
    const lu = sd < 0 ? -hw + Math.floor(r3 * 2) : hw - 1 - Math.floor(r3 * 2), h = 1 + Math.floor(c.rnd(q, 211) * 3);
    for (let w = 0; w < 2; w++) for (let j = 0; j < Math.max(1, h - w); j++) c.L(leg, lu, lv + w, y0 + j, j === 0 && w === 0 ? T_GRAVEL_FLOOR : tile);
    for (let j = 0; j < 2; j++) c.L(leg, lu, lv, y0 + ht + j, T_AIR);
    c.put("rubble", lu + 0.5 - sd * 0.8, lv + 0.5, y0, { s: 0.35 + r3 * 0.3, ry: q });
  });
}
// The labyrinth: partitions across the hall every few free rows, the doorway swapping sides each time.
function maze(c, o = {}) {
  const { leg, y0, hw } = c, clear = clearer(c), tile = o.tile || T_BRICK_MOSSY;
  let i = 0;
  for (let lv = c.lo + 2; lv < c.hi - 1; lv++) {
    if (!clear(-1, lv, 0) || !clear(1, lv, 0)) continue;
    if (lv - (c._mz || -99) < 3) continue;
    c._mz = lv;
    const door = i % 2 ? [hw - 3, hw - 2] : [-hw + 1, -hw + 2];
    for (let lu = -hw; lu < hw; lu++) for (let j = y0; j < y0 + c.ht; j++) { if (door.includes(lu) && j < y0 + 3) continue; c.L(leg, lu, lv, j, (i + lu + j) % 5 === 0 ? o.alt || T_MOSSY : tile); }
    c.torchAtB(leg, door[0] - 1, lv, y0 + 2, -1, { I: 2.4 });
    i++;
  }
}

// ---- new kinds ---------------------------------------------------------------------------------------------------
const LAB = wall([[300, T_BRICK_MOSSY], [560, T_MOSSY], [760, T_BRICK_CRACK], [900, T_COBBLE], [1000, T_BRICK]]);
def("maze_hall", { style: LAB, hw: [3, 3], ht: [4, 4], pre: [2, 2], m: [8, 12], branch: [0, 1], step: 10,
  floor: ({ hv }) => (hv < 300 ? T_MOSSY : hv < 600 ? T_BRICK_MOSSY : T_COBBLE), alcovePil: T_MOSSY, alcoveLin: T_BRICK_MOSSY,
  prof: P([0.07, 0.1, 0.075], [0.03, 0.045, 0.034], 0.04, 1.2, 1.0, 0.3),
  dress(c) { maze(c); F(c, [["vines", { n: 12 }], ["webs", { n: 6 }], ["torches", { every: 9, off: 1, I: 2.4 }]]); } });

def("collapsed_hall", { style: wall([[420, T_COBBLE], [680, T_STONE], [860, T_BRICK_CRACK], [1000, T_GRAVEL_FLOOR]]), hw: [4, 5], ht: [6, 7], pre: [2, 2], m: [6, 9], branch: [1, 1], step: 8,
  floor: ({ hv }) => (hv < 300 ? T_GRAVEL_FLOOR : hv < 640 ? T_COBBLE : T_BRICK_CRACK), alcovePil: T_BRICK_CRACK, alcoveLin: T_COBBLE,
  prof: P([0.09, 0.09, 0.1], [0.04, 0.04, 0.05], 0.04, 1.2, 0.9, 0.3),
  dress(c) {
    cavern(c, { tile: T_COBBLE, hang: 1.4 }); collapse(c, 16);
    F(c, [["torches", { every: 8, off: 2, I: 2.4 }], ["webs", { n: 10, w: 2 }], ["rubble", { n: 14 }]]);
    for (let lv = c.lo + 3; lv < c.hi - 2; lv += 9) c.src(0, lv, c.y0 + c.ht - 0.5, [0.7, 0.75, 1.0], 2.6, 10, {});   // daylight through the break
  } });

// A bridge two blocks wide across a bottomless dark, with the broken stubs of the old arches reaching out of the void.
def("void_bridge", { style: wall([[500, T_STONE], [800, T_COBBLE], [900, T_BEDROCK], [1000, T_OBS]]), hw: [6, 6], ht: [7, 7], pre: [3, 3], m: [6, 9], branch: [0, 0], holes: [0.5], below: 13, step: 8,
  floor: ({ lu, leg }) => (lu >= -1 && lu <= 0 ? T_BRIDGE_TILE : { from: leg.y0 - 10, cells: [[leg.y0 - 11, T_BEDROCK]] }),
  alcoveBase: (leg) => leg.y0 - 9, alcovePil: T_STONE, alcoveLin: T_BRICK,
  prof: P([0.05, 0.05, 0.09], [0.02, 0.02, 0.05], 0.034, 1.24, 1.1, 0.4, { pitch: -0.25 }),
  dress(c) {
    for (let lv = c.lo + 2; lv < c.hi; lv += 6) for (const sd of [-1, 1]) { c.col(sd > 0 ? 2 : -3, lv, c.y0 - 2, c.y0 + 2, T_BRICK_CRACK); c.torchAt(c.leg, sd > 0 ? 2 : -3, lv, c.y0 + 3, -sd, { I: 3.0 }); }
    for (let lv = c.lo + 1; lv < c.hi; lv++) for (const lu of [-2, 1]) c.put("fence", lu + (lu < 0 ? 0.9 : 0.1), lv + 0.5, c.y0, { h: 0.9, tex: "planks_oak" });
    c.scatter(8, 220, (q, r1, r2) => c.src((r2 - 0.5) * 8, c.lo + r1 * (c.hi - c.lo), c.y0 - 7, [0.4, 0.3, 0.9], 3.2, 12, {}));
  } });
const T_BRIDGE_TILE = B.T_BRIDGE;

// The stronghold's end-portal room: a hall of cracked and mossy brick, lava troughs along both sides, the ring of twelve frames
// with their eyes, the starfield between them. The gateway into the End.
def("portal_room", { style: wall([[300, T_BRICK], [520, T_BRICK_MOSSY], [700, T_BRICK_CRACK], [880, T_STONE], [940, T_CARVED], [1000, T_BRICK]]), hw: [5, 5], ht: [7, 7], pre: [3, 3], post: [2, 2], m: [5, 6], branch: [0, 0], step: 14, holes: [],
  floor: ({ hv }) => (hv < 560 ? T_BRICK : hv < 760 ? T_BRICK_MOSSY : hv < 900 ? T_BRICK_CRACK : T_STONE), alcovePil: T_BRICK_MOSSY, alcoveLin: T_CARVED, weight: 0.001,
  prof: P([0.066, 0.096, 0.092], [0.028, 0.05, 0.05], 0.036, 1.24, 1.0, 0.46),
  dress(c) {
    const { leg, y0, hw, ht } = c, vc = Math.round((c.lo + c.hi) / 2) + 2, rowsFree = c.rowsFree;
    for (let lv = leg.cs + 2; lv < vc - 5; lv += 5) for (const sd of [-1, 1]) if (rowsFree(sd, lv)) c.torchAt(leg, c.wallCell(sd), lv, y0 + 2, -sd, { I: 3.0 });
    F(c, [["webs", { n: 10, w: 1.8 }], ["vines", { n: 7 }]]);
    for (let lv = vc - 5; lv < leg.ce - 1; lv++) for (const lu of [-hw, -hw + 1, hw - 2, hw - 1]) {
      if (c.LG(leg, lu, lv, y0 - 1) === T_AIR) continue;
      c.L(leg, lu, lv, y0 - 1, T_LAVA); c.L(leg, lu, lv, y0 - 2, T_OBS);
      if (lv % 2 === 0 && (lu === -hw + 1 || lu === hw - 2)) c.src(lu + 0.5, lv + 0.5, y0 + 0.3, [1.0, 0.34, 0.07], 3.2, 10, { lava: true, dyn: true });
    }
    c.a.lavaRects.push({ ...rectOf(c, -hw, -hw + 1, vc - 5, leg.ce - 2), y: y0 - 0.12 }, { ...rectOf(c, hw - 2, hw - 1, vc - 5, leg.ce - 2), y: y0 - 0.12 });
    for (const sd of [-1, 1]) for (const lv of [vc - 4, vc, vc + 4]) c.torchAt(leg, c.wallCell(sd), lv, y0 + 3, -sd, { I: 3.2 });
    for (let du = -2; du <= 2; du++) for (let dv = -2; dv <= 2; dv++) {
      const edge = Math.abs(du) === 2 || Math.abs(dv) === 2;
      if (!edge || (Math.abs(du) === 2 && Math.abs(dv) === 2)) continue;
      c.put("frame", du + 0.5, vc + dv + 0.5, y0, { eye: c.rnd(du * 11 + dv + 40, 71) < 0.75 });
    }
    c.put("portal", 0.5, vc + 0.5, y0 + 0.75, { w: 3, d: 3 });
    c.src(0.5, vc + 0.5, y0 + 1.2, [0.25, 0.9, 0.72], 4.4, 13, { dyn: true });
    c.src(0.5, vc + 0.5, y0 + 1.2, [0.25, 0.9, 0.72], 3.0, 8, {});
    c.emit("portal", 0.5, vc + 0.5, y0 + 0.9);
    void ht;
  } });

// ---- per-kind shape, alcove frame ------------------------------------------------------------------------------------
// [hw, ht, pillar tile, lintel tile, shape]  shape: array of [feature, args...]
const S = (f, ...a) => [f, ...a];
const TABLE = {
  classic: [[4, 4], [5, 5], T_CARVED, T_BRICK, [S("vault", 1, T_BRICK)]],
  worn: [[3, 4], [5, 5], T_BRICK_CRACK, T_COBBLE, [S("cavern", { tile: T_COBBLE, hang: 0.9 }), S("collapse", 9)]],
  tomb_gallery: [[3, 3], [6, 6], B.T_QUARTZ_P, B.T_QUARTZ_C, [S("vault", 2, B.T_QUARTZ_C)]],
  arch_run: [[3, 3], [5, 5], T_STONE, T_CARVED, []],
  carpet_crypt: [[4, 4], [5, 5], T_BRICK, cl("red"), [S("vault", 1)]],
  raw_tunnel: [[3, 3], [4, 4], T_STONE, T_COBBLE, [S("cavern", { tile: T_STONE, hang: 0.8 })]],
  vaulted_hall: [[4, 5], [6, 6], B.T_LOG_SPRUCE, B.T_PLANK_SPRUCE, [S("vault", 2, B.T_LOG_SPRUCE)]],
  cell_chain: [[3, 3], [4, 4], T_BRICK, T_BRICK_CRACK, []],
  barred_cells: [[5, 5], [5, 5], T_BRICK_MOSSY, T_CARVED, [S("colonnade", { every: 6, off: 3, tile: T_BRICK_MOSSY, lus: [-3, 2] })]],
  cell_block: [[4, 4], [5, 5], T_BRICK_CRACK, T_BRICK, [S("vault", 1)]],
  sewer_walk: [[3, 4], [4, 5], T_MOSSY, T_BRICK_MOSSY, [S("vault", 1)]],
  drain_gallery: [[3, 3], [4, 4], T_MOSSY, T_BRICK_MOSSY, []],
  plank_causeway: [[5, 6], [6, 7], B.T_LOG, T_PLANK, [S("cavern", { tile: T_MOSSY, hang: 1 })]],
  drowned_hall: [[5, 6], [5, 5], T_BRICK_MOSSY, B.T_SPONGE, [S("colonnade", { every: 5, off: 2, tile: T_BRICK_MOSSY, torch: 2, I: 3.0, color: [0.6, 0.95, 1.0] })]],
  pressure_flood: [[3, 3], [7, 7], T_BRICK, T_CARVED, [S("vault", 2, T_STONE)]],
  scriptorium: [[5, 5], [8, 8], B.T_LOG_SPRUCE, B.T_SHELF, [S("catwalk", { tile: B.T_PLANK_SPRUCE, post: B.T_LOG_SPRUCE, fence: "planks_spruce" })]],
  treasury: [[5, 5], [6, 6], B.T_LAPIS, B.T_GOLD, [S("colonnade", { every: 5, off: 2, tile: B.T_LAPIS, cap: B.T_GOLD, torch: 3, I: 3.2, color: [1, 0.8, 0.4] }), S("vault", 1)]],
  alchemy_lab: [[3, 3], [4, 4], T_BRICK_MOSSY, B.T_COAL_BLOCK, []],
  sand_temple: [[4, 4], [6, 6], B.T_SANDSTONE_C, cl("orange"), [S("colonnade", { every: 4, off: 2, tile: B.T_SANDSTONE_C, cap: cl("orange"), lus: [-2, 1], torch: 3, I: 3, color: [1, 0.75, 0.4] })]],
  sun_hall: [[6, 7], [8, 8], B.T_SANDSTONE_S, cl("yellow"), [S("vault", 1)]],
  ice_grotto: [[5, 6], [6, 7], B.T_PACKED_ICE, B.T_SNOW, [S("cavern", { tile: B.T_PACKED_ICE, hang: 1.6 })]],
  frost_hall: [[6, 6], [6, 6], B.T_PACKED_ICE, B.T_PACKED_ICE, [S("colonnade", { every: 5, off: 2, tile: B.T_PACKED_ICE, cap: B.T_SNOW })]],
  mushroom_cave: [[5, 6], [6, 7], B.T_MUSH_STEM, B.T_MUSH_BROWN, [S("cavern", { tile: B.T_MUSH_BROWN, hang: 1.2 })]],
  overgrown: [[4, 6], [5, 7], B.T_LOG_JUNGLE, B.T_LEAVES_JUNGLE, [S("cavern", { tile: B.T_LEAVES_JUNGLE, hang: 1.4 })]],
  nether_hall: [[5, 5], [8, 8], T_NBRICK, T_NBRICK, [S("catwalk", { tile: T_NBRICK, post: T_NBRICK, fence: "nether_brick", color: [1, 0.4, 0.15] })]],
  soul_gallery: [[3, 3], [9, 9], T_OBS, T_NBRICK, [S("vault", 3, T_OBS)]],
  obsidian_vault: [[6, 6], [5, 5], T_OBS, T_OBS, [S("colonnade", { every: 6, off: 3, tile: T_OBS, cap: B.T_REDSTONE_BLOCK, torch: 2, I: 3, color: [0.8, 0.4, 1] })]],
  armory: [[4, 4], [6, 6], B.T_IRONB, T_STONE, [S("vault", 1, B.T_IRONB)]],
  barracks: [[5, 5], [5, 5], B.T_LOG, T_PLANK, []],
  end_hall: [[5, 5], [9, 9], T_OBS, B.T_ENDSTONE, [S("colonnade", { every: 6, off: 2, tile: T_OBS, cap: B.T_ENDSTONE, torch: 3, I: 3.0, color: [0.8, 0.5, 1] })]],
  wool_hall: [[5, 5], [6, 6], wl("red"), wl("blue"), []],
  // round 5
  mine: [null, null, B.T_LOG, T_PLANK, []],
  catacomb: [null, null, T_BRICK_CRACK, T_BRICK, []],
  ossuary: [null, null, T_BRICK_CRACK, T_STONE, []],
  spidermine: [null, null, B.T_LOG, T_COBBLE, []],
  temple: [null, null, T_MOSSY, T_BRICK_MOSSY, []],
  dungeon: [null, null, T_COBBLE, T_MOSSY, []],
  library: [null, null, B.T_LOG_SPRUCE, B.T_SHELF, []],
  vault: [null, null, T_STONE, B.T_IRONB, []],
  crypt: [null, null, 0, 0, []],
  chasm: [null, null, T_STONE, T_BRICK, []]
};
const SHAPES = { vault, cavern, colonnade, catwalk, collapse, maze };

export function applyArch() {
  for (const [id, [hw, ht, pil, lin, shape]] of Object.entries(TABLE)) {
    const kd = KINDS[id]; if (!kd) continue;
    if (hw) kd.hw = hw; if (ht) kd.ht = ht;
    if (pil) kd.alcovePil = pil; if (lin) kd.alcoveLin = lin;
    if (shape.length) {
      const old = kd.dress;
      kd.dress = (c) => { for (const [f, ...a] of shape) SHAPES[f](c, ...a); if (old) old(c); };
    }
  }
}
void T_GLOW; void T_PLANK; void T_DIRT; void pool; void T_NETHER;
