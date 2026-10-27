// Round 7: rooms with a story. Each is a place a builder made for a reason, or a place something happened, and every
// prop in it is there because of that: the chest is the smith's stock, the cauldron is the witch's, the minecart sits
// on the rails it ran on. They are rooms (def.room), and plan.js sets one between every two or three corridors.
// Vanilla 1.7.10 blocks and models only; designs studied from the catalogue (docs/design/site/krypt-structures.md)
// and the pack's mods, not copied.
import * as B from "./blocks.js";
import { def, wall, P, KINDS } from "./kindreg.js";
import { F, rectOf, clearer, pool } from "./kindlib.js";
import { rough, opening, spikes } from "./kinds_d.js";
const { T_AIR, T_BRICK, T_COBBLE, T_STONE, T_BRICK_CRACK, T_BRICK_MOSSY, T_MOSSY, T_GRAVEL_FLOOR, T_DIRT, T_CARVED, T_LAVA, T_OBS, T_GLOW, T_PLANK,
  T_LOG, T_NETHER, T_IRONB, T_GOLD, T_QUARTZ, T_QUARTZ_P, T_SOUL, T_BRICKS, T_SLAB } = B;
const cl = B.clay, wool = B.wool;
const RAIL = (leg) => (leg.h === "N" ? 0 : Math.PI / 2);
const mid = (c) => Math.round((c.lo + c.hi) / 2);
// The row on side sd with no alcove within pad rows, nearest `near` (null when the side has none).
function rowNear(c, sd, pad, near) {
  const clear = c.clr || (c.clr = clearer(c)); let best = null;
  for (let lv = c.lo; lv < c.hi; lv++) if (clear(sd, lv, pad) && (best == null || Math.abs(lv - near) < Math.abs(best - near))) best = lv;
  return best;
}
// Runs of free rows on side sd at least n long: [start, length].
function runs(c, sd, n, pad = 0) {
  const clear = c.clr || (c.clr = clearer(c)), out = []; let s = null;
  for (let lv = c.lo - 1; lv <= c.hi + 1; lv++) { const ok = lv < c.hi && clear(sd, lv, pad); if (ok && s == null) s = lv; if (!ok && s != null) { if (lv - s >= n) out.push([s, lv - s]); s = null; } }
  return out;
}
// A torch standing on the block below (a post, a table, an altar).
const stand = (c, lu, lv, j, I = 2.6, col = null) => { const [i, k] = c.legCell(c.leg, lu, lv); c.pushTorch(i, j, k, 0, 0, { I, ...(col ? { c: col } : {}) }); };
// The world facing of a block that looks across the hall from side sd (for furnaces, dispensers).
const furnFacing = (c, sd) => { const [dx, dz] = c.dirw(c.leg, -sd, 0); return dx > 0 ? B.T_FURN_PX : dx < 0 ? B.T_FURN_NX : dz > 0 ? B.T_FURN_PZ : B.T_FURN_NZ; };
const jackFacing = (c, sd) => { const [dx, dz] = c.dirw(c.leg, -sd, 0); return dx > 0 ? B.T_JACK_PX : dx < 0 ? B.T_JACK_NX : dz > 0 ? B.T_JACK_PZ : B.T_JACK_NZ; };
// A fence that runs along the leg: a post per block and the two rails joining it to the next, as the game connects them.
const fenceAlong = (c, lu, lv, y, tex = "planks_oak") => { const [bx, bz] = c.dirw(c.leg, 0, 1); c.put("fence", lu + 0.5, lv + 0.5, y, { h: 1, tex, len: 1, bx, bz, ry: c.yaw + Math.PI }); };

// ---- the spider nest: an old mine the cave spiders took ------------------------------------------------------------------------
def("spider_nest", { room: true, style: wall([[480, T_STONE], [720, T_COBBLE], [880, T_MOSSY], [1000, T_DIRT]]), hw: [6, 6], ht: [7, 7], pre: [3, 3], post: [3, 3], m: [5, 6], branch: [0, 0], step: 8, turn: 0.5,
  floor: ({ hv }) => (hv < 420 ? T_GRAVEL_FLOOR : hv < 780 ? T_DIRT : T_COBBLE), alcovePil: T_COBBLE, alcoveLin: T_MOSSY,
  prof: P([0.072, 0.076, 0.07], [0.03, 0.033, 0.03], 0.044, 1.18, 0.85, 0.3),
  dress(c) {
    const { leg, y0, hw, ht } = c, clear = clearer(c), vc = mid(c), sac = wool("white");
    rough(c, { depth: 3 }); spikes(c, T_STONE, 18, 2);
    // It was a mine first: one rail line runs in from the entrance and is lost under the webs.
    for (let lv = leg.cs + 1; lv < vc - 3; lv++) if (c.rnd(lv, 400) > 0.15) c.put("rail", -1.5, lv + 0.5, y0 + 0.02, { ry: RAIL(leg) });
    for (let lv = c.lo + 1; lv < vc - 3; lv += 4) for (const lu of [-3, 2]) if (clear(lu < 0 ? -1 : 1, lv, 0)) { c.col(lu, lv, y0, y0 + 2, T_LOG); for (let q = -3; q <= 2; q++) if (c.LG(leg, q, lv, y0 + 3) === T_AIR) c.L(leg, q, lv, y0 + 3, T_PLANK); }
    // Egg sacs: white wool bundled in web at the foot of the walls and hung in the roof, thickest near the spawner.
    c.scatter(14, 401, (q, r1, r2, r3) => { const sd = r2 < 0.5 ? -1 : 1, lv = Math.floor(vc - 8 + r1 * 16); if (lv < c.lo || lv >= c.hi || !clear(sd, lv, 1)) return; const lu = c.edgeCell(sd); c.L(leg, lu, lv, y0, sac); if (r3 < 0.4) c.L(leg, lu, lv, y0 + 1, sac); c.put("web", lu + 0.5, lv + 0.5, y0 + (r3 < 0.4 ? 1.5 : 0.6), { ry: c.yaw + q, w: 1.1 }); });
    c.scatter(9, 402, (q, r1, r2) => { const lu = Math.floor(-hw + 1 + r2 * (2 * hw - 2)), lv = Math.floor(c.lo + r1 * (c.hi - c.lo)); if (Math.abs(lu + 0.5) < 2.5) return; c.L(leg, lu, lv, y0 + ht - 1, sac); c.put("web", lu + 0.5, lv + 0.5, y0 + ht - 1.6, { ry: c.yaw + q * 0.7, w: 1 }); });
    // The heart of it: a cave spider spawner on a mound of cobble against the right wall, webbed in.
    const sv = rowNear(c, 1, 2, vc);
    if (sv != null) {
      const mu = hw - 2;
      for (let dv = -2; dv <= 2; dv++) for (let lu = mu - 2; lu <= hw - 1; lu++) { const r = Math.abs(dv) + Math.abs(lu - mu); if (r < 3) c.L(leg, lu, sv + dv, y0, r < 2 ? T_COBBLE : T_MOSSY); }
      c.put("spawner", mu + 0.5, sv + 0.5, y0 + 1, { mob: "CaveSpider" }); c.src(mu + 0.5, sv + 0.5, y0 + 1.7, [0.8, 0.5, 0.45], 2.6, 9, { dyn: true }); c.emit("spawner", mu + 0.5, sv + 0.5, y0 + 2);
      for (const [du, dv] of [[-1, -1], [-2, 1], [0, 2], [-1, 2], [0, -2]]) c.put("web", mu + du + 0.5, sv + dv + 0.5, y0 + 1.5, { ry: c.yaw + du, w: 1.2 });
    }
    // What it caught: an adventurer's skeleton against the far wall, webbed to it, a bone at its feet.
    const kv = rowNear(c, -1, 1, vc + 5);
    if (kv != null) { c.put("mob", -hw + 0.6, kv + 0.5, y0, { mob: "Skeleton", ry: c.faceRy(-1), scale: 0.9 }); c.put("web", -hw + 0.6, kv + 0.5, y0 + 1.4, { ry: c.yaw, w: 1.3 }); c.put("bone", -hw + 1.6, kv + 1.2, y0 + 0.02, { ry: 0.7 }); }
    // Webs: thick in the roof and the corners, low curtains at the sides; the walk stays open.
    F(c, [["webs", { n: 16, w: 2.2 }]]);
    c.scatter(10, 403, (q, r1, r2) => { const sd = q % 2 ? 1 : -1; c.put("web", sd * (hw - 1.2 - r2), c.lo + r1 * (c.hi - c.lo), y0 + 0.6 + r2, { ry: c.yaw + sd * 0.5, w: 1.4 }); });
  } });

// ---- the sunken chapel: a chapel the sewer flooded, pews in the water, the altar in an apse -------------------------------------
def("sunken_chapel", { room: true, style: wall([[420, T_BRICK], [640, T_BRICK_MOSSY], [820, T_BRICK_CRACK], [1000, T_MOSSY]]), hw: [7, 7], ht: [10, 10], pre: [3, 3], post: [3, 3], m: [5, 6], branch: [0, 0], step: 9, below: 4, turn: 0.5,
  floor: ({ lu, hv, yf }) => (lu >= -2 && lu <= 1 ? (lu === -2 || lu === 1 ? T_CARVED : hv < 300 ? T_BRICK_MOSSY : T_BRICK) : { from: yf - 1, cells: [[yf - 2, T_BRICK_MOSSY]] }),
  alcoveBase: (leg) => leg.y0 - 1, alcovePil: T_CARVED, alcoveLin: T_BRICK_MOSSY,
  prof: P([0.095, 0.11, 0.13], [0.035, 0.048, 0.058], 0.034, 1.26, 1.1, 0.42),
  dress(c) {
    const { leg, y0, hw, ht } = c, clear = clearer(c);
    c.a.waterRects.push({ ...rectOf(c, -hw, hw - 1, leg.cs + 1, leg.ce - 2), y: y0 - 0.22 });
    // The altar in an apse cut into the right wall, three steps of quartz, two candles and a window of coloured glass.
    const vc = rowNear(c, 1, 3, mid(c));
    if (vc != null) {
      opening(c, 1, vc - 2, { w: 5, h: 7, depth: 4, floor: T_QUARTZ, tile: T_CARVED, I: 2.2, color: [1, 0.85, 0.6] });
      for (let dv = -1; dv <= 1; dv++) c.L(leg, hw + 2, vc + dv, y0, T_QUARTZ);
      for (const dv of [-1, 1]) stand(c, hw + 2, vc + dv, y0 + 1, 2.8, [1, 0.8, 0.5]);
      c.put("pane", hw + 3.95, vc + 0.5, y0 + 3.2, { ry: c.acrossRy, w: 3, h: 3, tex: "glass_yellow" });
      c.lamp(hw + 4, vc, y0 + 3, T_GLOW, [1, 0.85, 0.45], 2.4, 9);
      // The pews face it: two long benches of spruce stairs in the water on the left of the aisle.
      for (const lu of [-6, -4]) for (let lv = vc - 4; lv <= vc + 4; lv++) if (lv >= c.lo && lv < c.hi && lv !== vc - 1 && lv !== vc + 2) c.put("stair", lu + 0.5, lv + 0.5, y0 - 1, { tex: "planks_spruce", ry: c.faceRy(-1) });
    }
    // Windows high in both walls between the graves: stained glass with daylight that is really glowstone behind it.
    const glass = ["glass_red", "glass_blue", "glass_purple", "glass_light_blue"];
    let q = 0;
    for (const sd of [-1, 1]) for (let lv = c.lo + 1; lv < c.hi; lv += 4) if (clear(sd, lv, 0) && !(sd > 0 && vc != null && Math.abs(lv - vc) < 4)) {
      c.put("pane", sd * (hw - 0.04), lv + 0.5, y0 + 6.1, { ry: c.acrossRy, w: 1, h: 2, tex: glass[q++ % glass.length] });
      c.lamp(sd > 0 ? hw : -hw - 1, lv, y0 + 6, T_GLOW, [0.75, 0.75, 1.0], 1.6, 8);
    }
    // Chandeliers: glowstone hung on fences over the aisle.
    for (let lv = c.lo + 2; lv < c.hi; lv += 6) for (const lu of [-5, -2, 1, 4]) { c.put("fence", lu + 0.5, lv + 0.5, y0 + ht - 2, { h: 2, tex: "planks_oak" }); c.lamp(lu, lv, y0 + ht - 3, T_GLOW, [1, 0.85, 0.55], 3.0, 11); }
    c.scatter(16, 410, (q2, r1, r2) => { const lu = r2 < 0.5 ? -hw + 1 + r2 * 4 : 2.5 + (r2 - 0.5) * 6; c.put("lily", lu, c.lo + r1 * (c.hi - c.lo), y0 - 0.2, { ry: q2 }); });
    c.scatter(10, 411, (q2, r1, r2) => { const [x, , z] = c.W3(leg, (r2 - 0.5) * hw * 1.8, c.lo + r1 * (c.hi - c.lo), 0); c.a.emit.push({ k: "drip", x, y: y0 + ht - 0.3, z, floorY: y0 - 0.22 }); });
    F(c, [["vines", { n: 12, h: 2.4 }]]);
  } });

// ---- the prison block: barred cells, iron doors, the levers that work them, and who is still inside -------------------------
def("prison_block", { room: true, style: wall([[460, T_BRICK], [700, T_BRICK_CRACK], [880, T_STONE], [1000, T_BRICK_MOSSY]]), hw: [4, 4], ht: [5, 5], pre: [5, 5], post: [3, 3], m: [5, 6], branch: [0, 0], step: 11, turn: 0.5,
  floor: ({ lu, hv }) => (lu === -1 || lu === 0 ? (hv < 400 ? T_BRICK_CRACK : T_BRICK) : hv < 260 ? T_COBBLE : T_BRICK), alcovePil: T_STONE, alcoveLin: T_BRICK,
  prof: P([0.085, 0.085, 0.09], [0.035, 0.036, 0.04], 0.04, 1.2, 1.0, 0.3),
  dress(c) {
    const { leg, y0, hw } = c, clear = clearer(c);
    // The guard post at the way in: a table, the chest of what was taken from them, a torch.
    c.put("cube", -hw + 0.5, c.lo - 3.5, y0, { side: "crafting_table_side", top: "crafting_table_top", h: 1 });
    c.put("chest", -hw + 0.5, c.lo - 1.5, y0, { ry: c.faceRy(-1) });
    c.torchAt(leg, c.wallCell(-1), c.lo - 2, y0 + 2, 1, { I: 2.8 });
    // The cells: three wide, three deep, barred, an iron door in the middle and its lever beside it on the corridor side.
    const cells = [];
    for (const sd of [-1, 1]) for (let lv = c.lo; lv < c.hi - 1; lv++) if (clear(sd, lv - 1, 1) && clear(sd, lv + 1, 1) && !cells.some(([s, v]) => s === sd && Math.abs(v - lv) < 5)) cells.push([sd, lv]);
    cells.forEach(([sd, lv], q) => {
      for (let d = 0; d < 3; d++) for (let dv = -1; dv <= 1; dv++) { const lu = sd > 0 ? hw + d : -hw - 1 - d; for (let j = y0; j < y0 + 3; j++) c.L(leg, lu, lv + dv, j, T_AIR); c.L(leg, lu, lv + dv, y0 - 1, T_COBBLE); }
      const a = sd * (hw + 0.02), open = q % 4 === 2;
      for (const dv of [-1, 1]) c.put("bars", a, lv + dv + 0.5, y0 + 1.5, { ry: c.acrossRy, w: 1, h: 3 });
      if (open) c.put("idoor", sd * (hw + 0.5), lv + 0.09, y0, { ry: c.yaw + Math.PI / 2 });
      else c.put("idoor", sd * (hw + 0.09), lv + 0.5, y0, { ry: c.yaw });
      c.put("lever", sd * (hw - 0.1), lv + 2.5, y0 + 1.4, { ry: c.sideRy(sd), on: open });
      const inA = sd * (hw + 1.5), back = sd * (hw + 2.4);
      if (q % 4 === 0) { c.put("mob", back, lv + 0.5, y0, { mob: "Skeleton", ry: c.faceRy(sd), scale: 0.9 }); c.put("bone", inA, lv + 1.2, y0 + 0.02, { ry: 1.2 }); }
      else if (q % 4 === 1) c.put("bed", back, lv + 0.5, y0, { ry: c.yaw });
      else if (q % 4 === 2) { const lu = sd > 0 ? hw + 3 : -hw - 4; for (const j of [y0, y0 + 1]) c.L(leg, lu, lv, j, T_AIR); c.L(leg, sd > 0 ? hw + 2 : -hw - 3, lv, y0, T_GRAVEL_FLOOR); c.put("rubble", inA, lv - 0.5, y0); }
      else c.put("mob", back, lv + 0.5, y0, { mob: "Zombie", ry: c.faceRy(sd), scale: 0.9 });
    });
    F(c, [["torches", { every: 6, off: 3, I: 2.4 }], ["webs", { n: 5 }]]);
  } });

// ---- the ravine crossing: a timber trestle with its rails, over a lava-floored ravine ------------------------------------------
const RD = 13;
def("rail_ravine", { room: true, margin: 6, style: wall([[380, T_STONE], [560, T_COBBLE], [680, T_DIRT], [780, T_GRAVEL_FLOOR], [880, B.T_COAL], [945, B.T_IRON], [975, B.T_REDSTONE_ORE], [1000, B.T_GOLD_ORE]]),
  hw: [8, 8], ht: [12, 12], pre: [3, 3], post: [3, 3], m: [4, 5], branch: [0, 0], step: 10, below: RD + 3, turn: 0.4, holes: [],
  floor: ({ lu, yf }) => (lu >= -2 && lu <= 1 ? { from: yf - RD, cells: [[yf - RD - 1, T_STONE], [yf - RD, T_LAVA], [yf - 1, lu === -2 || lu === 1 ? T_LOG : T_PLANK]], lava: true }
    : { from: yf - RD, cells: [[yf - RD - 1, T_STONE], [yf - RD, T_LAVA]], lava: true }),
  alcoveBase: (leg) => leg.y0 - 1, alcovePil: T_LOG, alcoveLin: T_PLANK, lavaI: 26, lavaDepth: RD,
  prof: P([0.1, 0.07, 0.055], [0.06, 0.032, 0.02], 0.03, 1.22, 0.9, 0.48, { pitch: -0.2 }),
  dress(c) {
    const { leg, y0, hw, ht } = c, clear = clearer(c);
    rough(c, { depth: 2 }); spikes(c, T_STONE, 30, 4);
    // A ledge of rock under every grave, so each stands on something.
    for (const s of leg.slots) for (let lv = s.lvc - 2; lv <= s.lvc + 2; lv++) for (let d = 0; d < 2; d++) c.L(leg, s.side > 0 ? hw - 1 - d : -hw + d, lv, y0 - 1, T_STONE);
    // The trestle: log trestles every five rows from the lava to the deck, braced; fence rails along both edges.
    for (let lv = leg.cs + 2; lv < leg.ce - 1; lv += 5) {
      for (const lu of [-2, 1]) c.col(lu, lv, y0 - RD + 1, y0 - 2, T_LOG);
      for (let lu = -2; lu <= 1; lu++) c.L(leg, lu, lv, y0 - 6, T_PLANK);
      if ((lv / 5 | 0) % 2) for (const lu of [-2, 1]) c.torchAt(leg, lu, lv, y0 - 3, lu < 0 ? -1 : 1, { I: 2.6 });
    }
    for (let lv = leg.cs + 1; lv < leg.ce - 2; lv++) for (const lu of [-2, 1]) fenceAlong(c, lu, lv, y0);
    // The line runs on: rails down the deck, a cart left standing on them.
    for (let lv = leg.cs; lv < leg.ce; lv++) c.put("rail", 0.5, lv + 0.5, y0 + 0.02, { ry: RAIL(leg) });
    c.put("cart", 0.5, mid(c) + 2.5, y0, { ry: c.acrossRy });
    for (let lv = c.lo; lv < c.hi; lv += 9) for (const lu of [-2, 1]) stand(c, lu, lv, y0, 2.4);
    c.scatter(8, 420, (q, r1, r2) => c.src((r2 < 0.5 ? -1 : 1) * (3 + r2 * 4), c.lo + r1 * (c.hi - c.lo), y0 - RD + 1.5, [1, 0.38, 0.1], 5, 14, { lava: true, dyn: true }));
    void clear; void ht;
  } });

// ---- the underground lake: a dock across dark water, a boat tied up, a fisherman's camp on the shore -----------------------------
def("underground_lake", { room: true, margin: 5, style: wall([[520, T_STONE], [740, T_COBBLE], [880, T_GRAVEL_FLOOR], [1000, T_MOSSY]]), hw: [10, 10], ht: [10, 10], pre: [3, 3], post: [3, 3], m: [5, 6], branch: [0, 0], step: 10, below: 7, turn: 0.4, holes: [],
  floor: ({ lu, leg, yf, hv }) => {
    if (lu <= -leg.hw + 1 || lu >= leg.hw - 2) return hv < 500 ? T_GRAVEL_FLOOR : T_STONE;
    if (lu === -1 || lu === 0) return { from: yf - 5, cells: [[yf - 6, T_GRAVEL_FLOOR], [yf - 1, B.T_PLANK_SPRUCE]] };
    return { from: yf - 5, cells: [[yf - 6, hv < 600 ? T_GRAVEL_FLOOR : T_DIRT]] };
  },
  alcovePil: T_STONE, alcoveLin: T_COBBLE,
  prof: P([0.06, 0.085, 0.11], [0.022, 0.04, 0.055], 0.034, 1.22, 1.0, 0.42),
  dress(c) {
    const { leg, y0, hw, ht } = c, clear = clearer(c), wy = y0 - 0.55;
    rough(c, { depth: 3 }); spikes(c, T_STONE, 50, 4);
    c.a.waterRects.push({ ...rectOf(c, -hw + 2, hw - 3, leg.cs + 1, leg.ce - 2), y: wy });
    // The dock's posts: spruce logs from the lake bed, one block proud of the deck, a torch on every third.
    for (let lv = leg.cs + 2, q = 0; lv < leg.ce - 1; lv += 4, q++) for (const lu of [-2, 1]) { c.col(lu, lv, y0 - 5, y0, B.T_LOG_SPRUCE); if (q % 3 === (lu < 0 ? 0 : 1)) stand(c, lu, lv, y0 + 1, 2.8); }
    // A pier off to the right, and the boat tied at its end.
    const pv = rowNear(c, 1, 2, mid(c)) ?? mid(c);
    for (let lu = 1; lu <= 5; lu++) for (const dv of [0, 1]) c.L(leg, lu, pv + dv, y0 - 1, B.T_PLANK_SPRUCE);
    c.col(5, pv, y0 - 5, y0, B.T_LOG_SPRUCE); stand(c, 5, pv, y0 + 1, 2.6);
    c.put("boat", 6.6, pv + 1.6, wy - 0.25, { ry: c.yaw + 0.25 });
    // The fisherman's camp on the left shore: a fire pit, a log to sit on, his chest.
    const fv = rowNear(c, -1, 2, mid(c) - 6) ?? c.lo + 2;
    c.L(leg, -hw + 1, fv, y0 - 1, T_NETHER); c.put("fire", -hw + 1.5, fv + 0.5, y0, {});
    c.src(-hw + 1.5, fv + 0.5, y0 + 0.6, [1.0, 0.5, 0.18], 3.2, 10, { dyn: true }); c.emit("fire", -hw + 1.5, fv + 0.5, y0 + 0.7); c.a.spots.fire.push(c.W3(leg, -hw + 1.5, fv + 0.5, y0 + 0.5));
    c.L(leg, -hw + 1, fv + 2, y0, T_LOG); c.put("chest", -hw + 0.5, fv - 1.5, y0, { ry: c.faceRy(-1) });
    c.scatter(22, 430, (q, r1, r2) => { const lu = (r2 < 0.5 ? -hw + 2.5 + r2 * 12 : 2.5 + (r2 - 0.5) * 12); c.put("lily", lu, c.lo + r1 * (c.hi - c.lo), wy + 0.02, { ry: q }); });
    c.scatter(16, 431, (q, r1, r2) => { const [x, , z] = c.W3(leg, (r2 - 0.5) * hw * 1.8, c.lo + r1 * (c.hi - c.lo), 0); c.a.emit.push({ k: "drip", x, y: y0 + ht - 0.3, z, floorY: wy }); });
    F(c, [["vines", { n: 10, h: 2.2 }]]);
    void clear;
  } });

// ---- the forge: lava run in channels down the floor, furnaces in the wall under a brick hood, anvils, a quench --------------------
def("forge", { room: true, style: wall([[560, T_BRICK], [780, T_BRICK_CRACK], [920, T_STONE], [1000, T_COBBLE]]), hw: [6, 6], ht: [7, 7], pre: [3, 3], post: [3, 3], m: [5, 6], branch: [0, 0], step: 10, below: 3, turn: 0.5,
  floor: ({ lu, yf, hv }) => (lu === -4 || lu === 3 ? { from: yf - 1, cells: [[yf - 2, T_OBS], [yf - 1, T_LAVA]], lava: true } : lu === -1 || lu === 0 ? (hv < 500 ? T_BRICK : T_BRICKS) : hv < 300 ? T_COBBLE : T_STONE),
  alcovePil: T_BRICKS, alcoveLin: T_STONE, lavaI: 12, lavaDepth: 1,
  prof: P([0.13, 0.08, 0.05], [0.06, 0.03, 0.018], 0.034, 1.22, 1.1, 0.5),
  dress(c) {
    const { leg, y0, hw, ht } = c, clear = clearer(c);
    for (let lv = leg.cs + 1; lv < leg.ce - 1; lv += 3) for (const lu of [-4, 3]) c.src(lu + 0.5, lv + 0.5, y0 + 0.2, [1, 0.4, 0.1], 2.4, 7, { lava: true, dyn: true });
    // Furnaces in the walls, a bank of three on each side, burning, under a brick hood that rises to the roof.
    for (const sd of [-1, 1]) for (const [s0, n] of runs(c, sd, 4).slice(0, 1)) {
      const lv0 = s0 + Math.floor((n - 3) / 2);
      for (let dv = 0; dv < 3; dv++) { c.L(leg, c.wallCell(sd), lv0 + dv, y0, furnFacing(c, sd)); c.src(c.edgeCell(sd) + 0.5, lv0 + dv + 0.5, y0 + 0.5, [1, 0.55, 0.2], 1.6, 6, { dyn: true }); for (let j = y0 + 2; j < y0 + ht; j++) c.L(leg, c.edgeCell(sd), lv0 + dv, j, T_BRICKS); }
      c.put("chest", c.edgeCell(sd) + 0.5, lv0 - 1.5, y0, { ry: c.faceRy(sd) });
    }
    // Anvils between the walk and the lava, each with a cauldron of water beside it to quench in.
    let q = 0;
    for (let lv = c.lo + 2; lv < c.hi - 2; lv += 7, q++) { const sd = q % 2 ? 1 : -1, lu = sd > 0 ? 1 : -3; c.put("anvil", lu + 0.5, lv + 0.5, y0, { ry: c.yaw }); c.put("cauldron", lu + 0.5, lv + 2.5, y0, { water: 2 }); }
    // The stock: iron blocks stacked at the far end, a crafting table.
    c.L(leg, -hw, c.hi, y0, T_IRONB); c.L(leg, -hw, c.hi, y0 + 1, T_IRONB); c.L(leg, -hw + 1, c.hi, y0, T_IRONB);
    c.put("cube", hw - 0.5, c.hi + 0.5, y0, { side: "crafting_table_side", top: "crafting_table_top", h: 1 });
    F(c, [["torches", { every: 7, off: 2, I: 2.4 }]]);
    void clear;
  } });

// ---- the desert tomb: sarcophagi on the floor, one broken open, offerings in pots, a roof that let the sand in -------------------
def("desert_tomb", { room: true, style: wall([[380, B.T_SANDSTONE], [640, B.T_SANDSTONE_S], [860, B.T_SANDSTONE_C], [1000, B.T_SAND]]), hw: [6, 6], ht: [7, 7], pre: [3, 3], post: [3, 3], m: [5, 6], branch: [0, 0], step: 9, turn: 0.5, holes: [],
  floor: ({ lu, lv }) => (lu === -1 || lu === 0 ? (lv % 4 === 0 ? cl("blue") : cl("orange")) : B.T_SANDSTONE_S), alcovePil: B.T_SANDSTONE_C, alcoveLin: cl("orange"),
  prof: P([0.14, 0.11, 0.075], [0.07, 0.055, 0.034], 0.036, 1.26, 1.1, 0.42),
  dress(c) {
    const { leg, y0, hw, ht } = c, clear = clearer(c);
    F(c, [["band", { tile: B.T_SANDSTONE_C, j0: 2, j1: 2 }], ["band", { tile: cl("orange"), j0: 4, j1: 4 }], ["band", { tile: cl("blue"), j0: 4, j1: 4, every: 4, off: 1 }]]);
    // Four sarcophagi between the walk and the walls: chiseled sandstone, a lid of slabs, the head toward the far end.
    let q = 0;
    for (const lu of [-4, 3]) for (let lv = c.lo + 1; lv < c.hi - 3 && q < 4; lv += 7) {
      const opened = q === 2;
      for (let dv = 0; dv < 3; dv++) {
        c.L(leg, lu, lv + dv, y0, opened && dv === 1 ? T_AIR : B.T_SANDSTONE_C);
        if (!opened) c.put("slab", lu + 0.5, lv + dv + 0.5, y0 + 1, { tex: "sandstone_smooth" });
      }
      if (opened) { c.L(leg, lu, lv + 1, y0 - 1, B.T_SANDSTONE); c.put("bone", lu + 0.5, lv + 1.5, y0 + 0.02, { ry: 0.4 }); c.put("slab", lu + (lu < 0 ? -0.5 : 1.5), lv + 1.5, y0, { tex: "sandstone_smooth" }); }
      c.put("pot", lu + 0.5 + (lu < 0 ? 1 : -1), lv + 2.5, y0, { plant: "deadbush" });
      q++;
    }
    // Where the roof gave way: a cone of sand under a crack, lit from the crack.
    const sv = rowNear(c, 1, 2, c.hi - 5);
    if (sv != null) {
      for (let dv = -2; dv <= 2; dv++) for (let lu = hw - 3; lu <= hw - 1; lu++) { const h = 3 - Math.abs(dv) - (hw - 1 - lu); for (let j = 0; j < h; j++) c.L(leg, lu, sv + dv, y0 + j, B.T_SAND); }
      for (let j = y0 + ht; j < y0 + ht + 4; j++) c.L(leg, hw - 1, sv, j, T_AIR);
      c.src(hw - 0.5, sv + 0.5, y0 + ht - 0.5, [1, 0.9, 0.7], 3.4, 11, {});
    }
    for (let lv = c.lo; lv < c.hi; lv += 6) for (const sd of [-1, 1]) if (clear(sd, lv, 0)) c.torchAt(leg, c.wallCell(sd), lv, y0 + 3, -sd, { I: 2.8, c: [1, 0.8, 0.45] });
  } });

// ---- the frozen hall: a built hall the cold took; mobs that walked in and never walked out stand in ice; one column is empty ----
def("frozen_hall", { room: true, style: wall([[560, T_BRICK], [760, T_BRICK_CRACK], [930, B.T_PACKED_ICE], [1000, B.T_SNOW]]), hw: [6, 6], ht: [8, 8], pre: [3, 3], post: [3, 3], m: [5, 6], branch: [0, 0], step: 9, turn: 0.5,
  floor: ({ hv }) => (hv < 900 ? B.T_SNOW : B.T_PACKED_ICE), alcovePil: B.T_PACKED_ICE, alcoveLin: B.T_SNOW,
  prof: P([0.06, 0.08, 0.11], [0.03, 0.045, 0.07], 0.036, 1.2, 1.0, 0.4),
  dress(c) {
    const { leg, y0, hw, ht } = c, clear = clearer(c);
    spikes(c, B.T_PACKED_ICE, 50, 3);
    const MOBS = [["Zombie", 2], ["Skeleton", 2], ["Creeper", 2], ["Villager", 2], ["Enderman", 3], ["Zombie", 2], ["Skeleton", 2]];
    let q = 0;
    for (let lv = c.lo; lv < c.hi; lv++) for (const sd of [-1, 1]) {
      if (!clear(sd, lv, 0) || (lv - c.lo) % 4 !== (sd > 0 ? 2 : 0)) continue;
      const lu = c.edgeCell(sd) - sd, [mob, h] = MOBS[(q + leg.variant) % MOBS.length];
      if (q === 3) { c.put("ice", lu + 0.5, lv + 0.5, y0, { h: 1 }); c.L(leg, lu + sd, lv + 1, y0, B.T_PACKED_ICE); c.put("slab", lu - sd + 0.5, lv - 0.5, y0, { tex: "ice_packed" }); }
      else { c.put("mob", lu + 0.5, lv + 0.5, y0, { mob, ry: c.faceRy(sd), scale: 0.95, lit: 0x8a96a8 }); c.put("ice", lu + 0.5, lv + 0.5, y0, { h }); }
      q++;
    }
    c.scatter(16, 440, (q2, r1, r2) => { const sd = r2 < 0.5 ? -1 : 1, lv = Math.floor(c.lo + r1 * (c.hi - c.lo)); if (clear(sd, lv, 0)) c.L(leg, c.edgeCell(sd), lv, y0, B.T_SNOW); });
    c.scatter(8, 441, (q2, r1, r2) => c.src((r2 - 0.5) * hw * 1.6, c.lo + r1 * (c.hi - c.lo), y0 + ht - 1.5, [0.55, 0.8, 1.0], 2.6, 11, {}));
  } });

// ---- the piston trap: a narrow hall whose walls are pistons; the plate in the middle; it has gone off before ----------------------
def("piston_trap", { room: true, style: wall([[480, T_BRICK], [720, T_BRICK_CRACK], [880, T_BRICK_MOSSY], [1000, T_COBBLE]]), hw: [3, 3], ht: [5, 5], pre: [4, 4], post: [3, 3], m: [4, 5], branch: [0, 0], step: 11, turn: 0.5,
  floor: ({ hv }) => (hv < 200 ? T_BRICK_CRACK : T_BRICK), alcovePil: T_CARVED, alcoveLin: T_BRICK,
  prof: P([0.085, 0.08, 0.08], [0.035, 0.032, 0.032], 0.04, 1.2, 0.95, 0.32),
  dress(c) {
    const { leg, y0, hw } = c, clear = clearer(c), vc = mid(c);
    // A tripwire at the way in, its hooks on both walls.
    const tv = c.lo - 2;
    for (let lu = -hw; lu < hw; lu++) c.put("wire", lu + 0.5, tv + 0.5, y0 + 0.07, { ry: c.yaw + Math.PI / 2 });
    for (const sd of [-1, 1]) c.put("hook", sd * (hw - 0.05), tv + 0.5, y0 + 0.4, { ry: c.sideRy(sd) });
    // The walls: pistons on every free row, two high, facing the walk, their faces flush with the wall.
    for (const sd of [-1, 1]) for (let lv = c.lo; lv < c.hi; lv++) {
      if (!clear(sd, lv, 0)) continue;
      const sprung = Math.abs(lv - vc) <= 0;
      for (const j of [y0, y0 + 1]) { c.L(leg, c.wallCell(sd), lv, j, T_AIR); c.put("piston", c.wallCell(sd) + 0.5, lv + 0.5, j, { ry: c.faceRy(sd), out: sprung }); }
    }
    // The plate in the middle of the walk, the dust that runs from it to the walls.
    c.put("plate", -0.5, vc + 0.5, y0, {}); c.put("plate", 0.5, vc + 0.5, y0, {});
    for (let lu = -hw + 1; lu < hw - 1; lu++) if (lu !== -1 && lu !== 0) c.put("dust", lu + 0.5, vc + 0.5, y0, { ry: c.yaw + Math.PI / 2 });
    for (let lv = c.lo; lv < c.hi; lv++) if (lv !== vc) for (const lu of [-hw + 1, hw - 2]) c.put("dust", lu + 0.5, lv + 0.5, y0, { ry: c.yaw });
    // Who set it off: under the sprung head on the left, bones and a skull.
    c.put("bone", -hw + 1.5, vc + 1.3, y0 + 0.02, { ry: 2.1 }); c.put("skull", -hw + 1.4, vc - 0.6, y0, { ry: c.faceRy(-1) + 0.4 });
    // Dispensers at the far end, aimed down the hall; the lever that should have made it safe, still off.
    c.L(leg, -1, c.hi + 1, y0 + 1, c.dispType(...c.dirw(leg, 0, -1))); c.L(leg, 0, c.hi + 1, y0 + 1, c.dispType(...c.dirw(leg, 0, -1)));
    c.put("lever", hw - 0.1, c.lo - 3.5, y0 + 1.4, { ry: c.sideRy(1), on: false });
    c.torchAt(leg, c.wallCell(-1), c.lo - 3, y0 + 2, 1, { I: 2.6 });
  } });

// ---- the ruined portal: someone built a way out to the Nether down here; it broke, and the Nether is leaking in --------------------
def("ruined_portal", { room: true, style: wall([[600, T_STONE], [850, T_COBBLE], [1000, T_MOSSY]]), hw: [7, 7], ht: [9, 9], pre: [3, 3], post: [3, 3], m: [5, 6], branch: [0, 0], step: 9, turn: 0.5,
  floor: ({ lu, lv, hv, leg }) => { const vc = Math.round((leg.b0 + leg.pre + leg.contentEnd) / 2), d = Math.hypot(lu + 0.5, lv - vc); return d < 4.5 + hv / 280 ? (hv < 120 ? T_SOUL : T_NETHER) : hv < 300 ? T_GRAVEL_FLOOR : T_STONE; },
  alcovePil: T_COBBLE, alcoveLin: T_STONE,
  prof: P([0.14, 0.08, 0.075], [0.055, 0.028, 0.03], 0.032, 1.24, 1.05, 0.5),
  dress(c) {
    const { leg, y0, hw, ht } = c, clear = clearer(c), vc = Math.round((leg.b0 + leg.pre + leg.contentEnd) / 2);
    // The frame across the walk: obsidian, four wide inside, the top right corner gone, one block patched with cobble.
    for (const lu of [-3, 2]) for (let j = y0; j <= y0 + 4; j++) c.L(leg, lu, vc, j, T_OBS);
    for (let lu = -3; lu <= 2; lu++) c.L(leg, lu, vc, y0 + 5, T_OBS);
    c.L(leg, 2, vc, y0 + 5, T_AIR); c.L(leg, 2, vc, y0 + 4, T_AIR); c.L(leg, 1, vc, y0 + 5, T_AIR); c.L(leg, -3, vc, y0 + 2, T_COBBLE);
    c.L(leg, 3, vc + 1, y0, T_OBS); c.L(leg, 4, vc - 2, y0, T_OBS);
    // The Nether creeping in: netherrack in the walls around it, fire on the floor, a lava seep.
    for (let lv = vc - 4; lv <= vc + 4; lv++) for (const sd of [-1, 1]) if (clear(sd, lv, 0)) for (let j = y0; j <= y0 + 3; j++) if (c.rnd(lv * 7 + j, 450 + sd) < 0.6) c.L(leg, c.wallCell(sd), lv, j, T_NETHER);
    for (const [lu, dv] of [[-5, -2], [4, 2], [-4, 3], [3, -3], [-2, 1], [1, -1]]) { c.put("fire", lu + 0.5, vc + dv + 0.5, y0, {}); c.src(lu + 0.5, vc + dv + 0.5, y0 + 0.6, [1.0, 0.48, 0.16], 2.8, 9, { dyn: true }); c.emit("fire", lu + 0.5, vc + dv + 0.5, y0 + 0.7); c.a.spots.fire.push(c.W3(leg, lu + 0.5, vc + dv + 0.5, y0 + 0.5)); }
    pool(c, { lu0: 4, lu1: 5, lv0: vc + 3, lv1: vc + 4, liquid: "lava" });
    // Their camp, before it: a bed, a crafting table, a chest, a torch on the wall.
    const cv = rowNear(c, -1, 2, vc - 6);
    if (cv != null) {
      c.put("bed", -hw + 1, cv + 0.5, y0, { ry: c.yaw });
      c.put("cube", -hw + 0.5, cv + 2.5, y0, { side: "crafting_table_side", top: "crafting_table_top", h: 1 });
      c.put("chest", -hw + 0.5, cv - 1.5, y0, { ry: c.faceRy(-1) });
      c.torchAt(leg, c.wallCell(-1), cv + 1, y0 + 2, 1, { I: 2.8 });
    }
    void ht;
  } });

// ---- the giant's bones: the skeleton of something huge, ribs arched over the walk, its skull at the far end ------------------------
// Bone in quartz pillar, the nearest thing the game had to bone block then.
def("giant_bones", { room: true, margin: 5, style: wall([[480, T_STONE], [700, T_COBBLE], [860, T_GRAVEL_FLOOR], [1000, T_DIRT]]), hw: [9, 9], ht: [12, 12], pre: [3, 3], post: [3, 3], m: [5, 6], branch: [0, 0], step: 10, turn: 0.4, holes: [0.45],
  floor: ({ hv }) => (hv < 450 ? T_GRAVEL_FLOOR : hv < 800 ? T_STONE : T_DIRT), alcovePil: T_STONE, alcoveLin: T_COBBLE,
  prof: P([0.075, 0.075, 0.085], [0.03, 0.03, 0.038], 0.036, 1.22, 0.95, 0.36),
  dress(c) {
    const { leg, y0, hw, ht } = c, BONE = T_QUARTZ_P, CAP = T_QUARTZ;
    rough(c, { depth: 3 }); spikes(c, T_STONE, 40, 4);
    // The spine, half buried along the left floor.
    for (let lv = c.lo; lv < c.hi - 5; lv++) { c.L(leg, -6, lv, y0, BONE); if (lv % 3 === 0) c.L(leg, -6, lv, y0 + 1, CAP); }
    // The ribs: arcs from the spine over the walk to the right floor, every third row, two of them broken.
    let r = 0;
    for (let lv = c.lo + 1; lv < c.hi - 7; lv += 3, r++) {
      let jp = null;
      for (let lu = -6; lu <= 6; lu++) {
        if ((r === 2 && lu > 1) || (r === 4 && lu > -1 && lu < 4)) { jp = null; continue; }
        const j = y0 + Math.round(Math.sin(Math.PI * (lu + 6) / 12) * 8);
        const lo = jp == null ? j : Math.min(j, jp + 1), hi = jp == null ? j : Math.max(j, jp - 1);
        for (let y = lo; y <= hi; y++) c.L(leg, lu, lv, y, BONE);
        jp = j;
      }
    }
    // The skull at the far end on the left, its jaw on the floor, the sockets dark.
    const sv = c.hi - 4;
    for (let lv = sv; lv < sv + 5; lv++) for (let lu = -8; lu <= -4; lu++) for (let j = y0; j <= y0 + 3; j++) {
      const shell = lv === sv || lv === sv + 4 || lu === -8 || lu === -4 || j === y0 + 3;
      c.L(leg, lu, lv, j, shell ? CAP : T_AIR);
    }
    for (const lu of [-7, -5]) c.L(leg, lu, sv, y0 + 2, B.T_COAL_BLOCK);
    c.L(leg, -6, sv, y0 + 1, T_AIR); for (const lu of [-7, -5]) c.L(leg, lu, sv, y0, T_AIR);
    // For scale: a man's skeleton beside a rib, and bones scattered.
    const kv = rowNear(c, 1, 1, c.lo + 5); if (kv != null) c.put("mob", 4.5, kv + 0.5, y0, { mob: "Skeleton", ry: c.faceRy(1), scale: 0.9 });
    F(c, [["bones", { n: 8 }]]);
    void hw; void ht;
  } });

// ---- the witch's hut: a swamp in a cave, a hut on stilts, her cauldron, her pot, her ------------------------------------------------
def("witch_hut", { room: true, margin: 5, style: wall([[440, T_DIRT], [660, T_STONE], [820, T_MOSSY], [1000, T_COBBLE]]), hw: [9, 9], ht: [10, 10], pre: [3, 3], post: [3, 3], m: [5, 6], branch: [0, 0], step: 10, below: 3, turn: 0.4, holes: [],
  floor: ({ lu, hv, yf }) => (lu >= -2 && lu <= 1 ? (hv < 500 ? B.T_PODZOL : T_DIRT) : hv < 260 ? B.T_GRASS : { from: yf - 1, cells: [[yf - 2, T_DIRT]] }),
  alcoveBase: (leg) => leg.y0 - 1, alcovePil: B.T_LOG, alcoveLin: T_MOSSY,
  prof: P([0.085, 0.115, 0.075], [0.03, 0.048, 0.03], 0.036, 1.22, 1.0, 0.4),
  dress(c) {
    const { leg, y0, hw, ht } = c;
    rough(c, { depth: 2 });
    c.a.waterRects.push({ ...rectOf(c, -hw, hw - 1, leg.cs + 1, leg.ce - 2), y: y0 - 0.2 });
    // The hut, on the right: spruce logs for stilts and corners, spruce plank floor and walls, a plank roof that overhangs.
    const vc = rowNear(c, 1, 3, mid(c)) ?? mid(c), u0 = 3, u1 = 7;
    for (let lu = u0; lu <= u1; lu++) for (let dv = -2; dv <= 2; dv++) {
      const edge = lu === u0 || lu === u1 || Math.abs(dv) === 2, corner = (lu === u0 || lu === u1) && Math.abs(dv) === 2;
      if (corner) c.col(lu, vc + dv, y0 - 1, y0 + 4, B.T_LOG_SPRUCE);
      else { c.L(leg, lu, vc + dv, y0 + 1, B.T_PLANK_SPRUCE); if (edge) c.col(lu, vc + dv, y0 + 2, y0 + 4, B.T_PLANK_SPRUCE); else c.col(lu, vc + dv, y0 + 2, y0 + 4, T_AIR); }
      for (let j = y0 - 1; j <= y0; j++) if (!corner) c.L(leg, lu, vc + dv, j, T_AIR);
    }
    for (let lu = u0 - 1; lu <= u1 + 1; lu++) for (let dv = -3; dv <= 3; dv++) c.L(leg, lu, vc + dv, y0 + 5, B.T_PLANK_SPRUCE);
    c.L(leg, u0, vc, y0 + 2, T_AIR); c.L(leg, u0, vc, y0 + 3, T_AIR); c.L(leg, u0 - 1, vc, y0, B.T_PLANK_SPRUCE);
    c.L(leg, u0, vc - 1, y0 + 3, T_AIR); c.put("fence", u0 + 0.5, vc - 0.5, y0 + 3, { h: 1, tex: "planks_spruce" });
    // Inside: her cauldron, her brewing stand, the crafting table, the flower pot with its red mushroom; and her.
    c.put("cauldron", 6.5, vc - 0.5, y0 + 2, { water: 3 }); c.src(6.5, vc - 0.5, y0 + 3.6, [0.62, 0.9, 0.55], 1.3, 6, {});
    c.put("brewing", 4.5, vc - 0.5, y0 + 2, { bottles: 5 });
    c.put("cube", 6.5, vc + 1.5, y0 + 2, { side: "crafting_table_side", top: "crafting_table_top", h: 1 });
    c.put("pot", 4.5, vc + 1.5, y0 + 2, { plant: "mushroom_red" });
    c.put("mob", 5.5, vc + 0.5, y0 + 2, { mob: "Witch", ry: c.faceRy(1), scale: 0.95, lit: 0xa89480 });   // lit by her lamp, not a silhouette
    // Jack o'lanterns on posts along the track to her door: the only warm light in the swamp.
    for (const dv of [2, -7, 9]) { const lv = vc + dv; if (lv < c.lo - 2 || lv > c.hi + 1) continue; c.L(leg, 2, lv, y0, B.T_LOG_SPRUCE); c.lamp(2, lv, y0 + 1, jackFacing(c, 1), [1, 0.7, 0.35], 3.2, 12); }
    c.src(5.5, vc + 0.5, y0 + 3.5, [1, 0.75, 0.45], 2.2, 7, {});
    // The swamp: trees grown to the roof, leaves hanging, lily pads, mushrooms on the hummocks, vines.
    for (const [lu, dv] of [[-6, -8], [-5, 6], [6, -9], [-7, 1]]) { const lv = vc + dv; if (lv < c.lo || lv >= c.hi) continue; c.col(lu, lv, y0, y0 + ht - 1, T_LOG); for (let du = -2; du <= 2; du++) for (let dw = -2; dw <= 2; dw++) if (Math.abs(du) + Math.abs(dw) < 4 && c.LG(leg, lu + du, lv + dw, y0 + ht - 1) === T_AIR) { c.L(leg, lu + du, lv + dw, y0 + ht - 1, B.T_LEAVES_OAK); if ((du + dw) % 2 === 0 && Math.abs(lu + du + 0.5) > 2) c.L(leg, lu + du, lv + dw, y0 + ht - 2, B.T_LEAVES_OAK); } }
    c.scatter(24, 460, (q, r1, r2) => { const lu = r2 < 0.5 ? -hw + 0.5 + r2 * 13 : 2.5 + (r2 - 0.5) * 13; c.put("lily", lu, c.lo + r1 * (c.hi - c.lo), y0 - 0.18, { ry: q }); });
    c.scatter(12, 461, (q, r1, r2, r3) => { const lu = Math.floor(-hw + r2 * 2 * hw), lv = Math.floor(c.lo + r1 * (c.hi - c.lo)); if (Math.abs(lu + 0.5) < 3 || c.LG(leg, lu, lv, y0 - 1) !== B.T_GRASS) return; c.put("cross", lu + 0.5, lv + 0.5, y0, { tex: r3 < 0.5 ? "mushroom_red" : "mushroom_brown", s: 0.6 }); });
    F(c, [["vines", { n: 18, h: 2.6 }]]);
    c.torchAt(leg, u0, vc + 1, y0 + 3, -1, { I: 2.2 });
  } });

// ---- the cartographer's room: whoever mapped the Krypt worked here; the survey is on the walls ----------------------------------------
def("cartographer", { room: true, style: wall([[700, T_BRICK], [900, T_BRICK_CRACK], [1000, T_BRICK_MOSSY]]), hw: [5, 5], ht: [6, 6], pre: [3, 3], post: [3, 3], m: [5, 6], branch: [0, 0], step: 10, turn: 0.5,
  floor: ({ lu }) => (lu === -1 || lu === 0 ? wool("red") : B.T_PLANK_SPRUCE), alcovePil: B.T_LOG_SPRUCE, alcoveLin: B.T_PLANK_SPRUCE,
  prof: P([0.115, 0.09, 0.06], [0.05, 0.038, 0.024], 0.036, 1.24, 1.05, 0.38),
  dress(c) {
    const { leg, y0, hw, ht } = c;
    F(c, [["band", { tile: B.T_PLANK_SPRUCE, j0: 0, j1: 0 }], ["band", { tile: B.T_LOG_SPRUCE, j0: 3, j1: 3 }]]);
    // The survey: on each free stretch of wall, a block of maps three wide and two high that join into one map.
    let g = 0;
    for (const sd of [-1, 1]) for (const [s0, n] of runs(c, sd, 3)) {
      if (g > 1) break;
      const lv0 = s0 + Math.floor((n - 3) / 2);
      for (let k = 0; k < 3; k++) for (let r = 0; r < 2; r++) { const col = sd > 0 ? k : 2 - k; c.put("map", c.edgeCell(sd) + 0.5, lv0 + k + 0.5, y0 + 2 - r, { ry: c.faceRy(sd), cell: g * 6 + r * 3 + col }); }
      g++;
    }
    // The table: fence posts with pressure plates for a top, the way the game's builders made tables, maps laid on it.
    const tv = rowNear(c, 1, 0, mid(c)) ?? mid(c);
    for (let dv = -2; dv <= 2; dv++) { c.put("fence", 2.5, tv + dv + 0.5, y0, { h: 0.94, tex: "planks_spruce" }); c.put("plate", 2.5, tv + dv + 0.5, y0 + 0.94, {}); }
    for (const [dv, cell] of [[-1, 12], [1, 13]]) c.put("map", 2.5, tv + dv + 0.5, y0 + 1.01, { flat: true, cell });
    c.put("fence", 2.5, tv + 0.5, y0 + ht - 2, { h: 2, tex: "planks_oak" }); c.lamp(2, tv, y0 + ht - 3, T_GLOW, [1, 0.85, 0.55], 3.0, 10);
    // The archive: chests at either end of the room, apart (two side by side would be one double chest), shelves around them.
    for (const [lv, sd] of [[c.lo - 2, -1], [c.hi + 1, 1]]) { c.put("chest", sd * (hw - 0.5), lv + 0.5, y0, { ry: c.faceRy(sd) }); for (const dv of [-1, 1]) for (let j = y0; j <= y0 + 2; j++) c.L(leg, c.edgeCell(sd), lv + dv, j, B.T_SHELF); }
    F(c, [["torches", { every: 6, off: 2, I: 2.6 }]]);
  } });

// ---- the flooded ossuary: the water came up through the floor; skulls on the shelves, bones under the water, a drowned one below -----
def("flooded_ossuary", { room: true, style: wall([[360, T_BRICK_MOSSY], [600, T_MOSSY], [800, T_BRICK_CRACK], [1000, T_BRICK]]), hw: [5, 5], ht: [6, 6], pre: [3, 3], post: [3, 3], m: [6, 7], branch: [0, 0], step: 7, below: 6, turn: 0.5,
  floor: ({ lu, hv, yf, leg, lv }) => {
    if (lu === -1 || lu === 0) return hv < 500 ? T_MOSSY : T_COBBLE;
    const vc = Math.round((leg.b0 + leg.pre + leg.contentEnd) / 2);
    if (lu >= 2 && lu <= 3 && Math.abs(lv - vc) <= 1) return { from: yf - 5, cells: [[yf - 6, T_GRAVEL_FLOOR]] };
    return { from: yf - 1, cells: [[yf - 2, T_GRAVEL_FLOOR]] };
  },
  alcoveBase: (leg) => leg.y0 - 1, alcovePil: T_BRICK_MOSSY, alcoveLin: T_CARVED,
  prof: P([0.07, 0.09, 0.08], [0.028, 0.04, 0.034], 0.04, 1.2, 0.95, 0.32),
  dress(c) {
    const { leg, y0, hw, ht } = c, clear = clearer(c), vc = Math.round((leg.b0 + leg.pre + leg.contentEnd) / 2);
    c.a.waterRects.push({ ...rectOf(c, -hw, hw - 1, leg.cs + 1, leg.ce - 2), y: y0 - 0.3 });
    // Skull shelves: the walls between the graves are cut into niches, three tiers, every niche a skull.
    for (const sd of [-1, 1]) for (let lv = c.lo; lv < c.hi; lv++) if (clear(sd, lv, 0)) for (const j of [y0 + 1, y0 + 2, y0 + 3]) {
      if (c.rnd(lv * 5 + j, 470 + sd) < 0.2) continue;
      c.L(leg, c.wallCell(sd), lv, j, T_AIR); c.put("skull", c.wallCell(sd) + 0.5 - sd * 0.1, lv + 0.5, j, { ry: c.faceRy(sd) });
    }
    // Bones lying under the water, and where the floor fell into the crypt below, a drowned body at the bottom.
    c.scatter(18, 471, (q, r1, r2) => { const lu = (r2 < 0.5 ? -hw + 0.6 + r2 * 6 : 1.4 + (r2 - 0.5) * 6); c.put("bone", lu, c.lo + r1 * (c.hi - c.lo), y0 - 0.98, { ry: q * 1.3 }); });
    c.put("mob", 3, vc + 0.5, y0 - 5, { mob: "Zombie", ry: c.faceRy(1) + 0.6, scale: 0.9, glow: 0x061010 });
    c.src(2.5, vc + 0.5, y0 - 3, [0.3, 0.6, 0.7], 1.6, 6, {});
    // Where the water came in: barred drains low in the walls, still trickling.
    for (const sd of [-1, 1]) { const lv = rowNear(c, sd, 0, sd > 0 ? c.lo + 2 : c.hi - 3); if (lv == null) continue; c.L(leg, c.wallCell(sd), lv, y0, T_AIR); c.put("bars", sd * (hw + 0.02), lv + 0.5, y0 + 0.5, { ry: c.acrossRy, w: 1, h: 1 }); const [x, , z] = c.W3(leg, sd * (hw - 0.3), lv + 0.5, 0); c.a.emit.push({ k: "drip", x, y: y0 + 0.9, z, floorY: y0 - 0.3 }); }
    F(c, [["vines", { n: 8, h: 1.8 }], ["webs", { n: 4 }]]);
    void ht;
  } });

// ---- the crypt of iron doors: family tombs sealed behind iron; one of them has been opened ----------------------------------------
def("iron_crypt", { room: true, style: wall([[440, T_BRICK], [700, T_CARVED], [860, T_BRICK_CRACK], [1000, T_BRICK_MOSSY]]), hw: [4, 4], ht: [6, 6], pre: [3, 3], post: [3, 3], m: [5, 6], branch: [0, 0], step: 11, turn: 0.5,
  floor: ({ lu, lv }) => (lu === -1 || lu === 0 ? (lv % 2 ? T_BRICK : T_SLAB) : T_BRICK), alcovePil: T_CARVED, alcoveLin: T_BRICK_CRACK,
  prof: P([0.085, 0.085, 0.095], [0.034, 0.034, 0.04], 0.04, 1.22, 1.0, 0.34),
  dress(c) {
    const { leg, y0, hw } = c;
    let q = 0;
    for (const sd of [-1, 1]) for (const [s0, n] of runs(c, sd, 4)) {
      const lv = s0 + Math.floor((n - 4) / 2) + 1, opened = q === 1;
      // The tomb: a chamber three deep behind a two-wide doorway framed in chiseled stone brick.
      for (let d = 1; d <= 3; d++) for (let dv = -1; dv <= 2; dv++) for (let j = y0; j < y0 + 3; j++) c.L(leg, sd > 0 ? hw + d : -hw - 1 - d, lv + dv, j, T_AIR);
      for (const dv of [0, 1]) for (let j = y0; j < y0 + 2; j++) c.L(leg, c.wallCell(sd), lv + dv, j, T_AIR);
      for (const dv of [-1, 2]) for (let j = y0; j <= y0 + 2; j++) c.L(leg, c.wallCell(sd), lv + dv, j, T_CARVED);
      for (const dv of [0, 1]) c.L(leg, c.wallCell(sd), lv + dv, y0 + 2, T_CARVED);
      if (opened) {
        for (const [dv, h] of [[0, 0.09], [1, 0.91]]) c.put("idoor", sd * (hw + 0.5), lv + dv + h, y0, { ry: c.yaw + Math.PI / 2 });
        c.put("slab", sd * (hw + 2.5), lv + 0.5, y0, { tex: "stone_slab_top" }); c.put("slab", sd * (hw + 2.5), lv + 1.5, y0, { tex: "stone_slab_top" });
        c.put("skull", sd * (hw + 2.5), lv + 1, y0 + 0.5, { ry: c.faceRy(sd) }); c.put("web", sd * (hw + 3), lv + 2, y0 + 2, { ry: c.yaw, w: 1.2 });
        c.put("lever", sd * (hw - 0.1), lv + 2.5, y0 + 1.2, { ry: c.sideRy(sd), on: true });
        c.src(sd * (hw + 2), lv + 1, y0 + 1.5, [0.9, 0.6, 0.4], 1.4, 5, {});
      } else for (const dv of [0, 1]) c.put("idoor", sd * (hw + 0.09), lv + dv + 0.5, y0, { ry: c.yaw });
      c.torchAt(leg, c.wallCell(sd), lv - 1, y0 + 3, -sd, { I: 2.4 });
      q++;
    }
  } });

// The set pieces are rooms too, for the rhythm.
for (const id of ["mine_crossing", "labyrinth_junction", "flooded_cistern", "library_balcony", "sand_chamber", "ice_cavern", "mushroom_cavern", "fortress_bridge", "arena", "chasm_open", "void_bridge", "hollow_hill", "portal_room"]) if (KINDS[id]) KINDS[id].room = true;
