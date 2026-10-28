// Kinds of the first strata: the stone crypts and old mines, the catacombs and ossuaries, the sewers and drowned halls.
// Drawn from the structure catalogue (docs/design/site/krypt-structures.md), entries 1-21, with vanilla blocks only.
import * as B from "./blocks.js";
import { def, wall, P } from "./kindreg.js";
import { F, FEATURES, pool, rectOf, clearer, between } from "./kindlib.js";
const { T_AIR, T_BRICK, T_COBBLE, T_STONE, T_BRICK_CRACK, T_BRICK_MOSSY, T_MOSSY, T_GRAVEL_FLOOR, T_DIRT, T_CARVED, T_SLAB, T_QUARTZ, T_QUARTZ_P, T_QUARTZ_C, T_LAVA, T_OBS, T_COAL, T_IRON } = B;

// ---- Stratum 1: stone crypts and old mines ----------------------------------------------------------------------
// 1. Doomlike classic hall: a wide hall of stone brick with a cobble runner, carved pillars between the alcoves, a slab ceiling,
//    and sometimes a pool the path skirts.
def("classic", { style: wall([[420, T_BRICK], [600, T_COBBLE], [760, T_STONE], [900, T_BRICK_CRACK], [1000, T_BRICK_MOSSY]]), hw: [3, 4], ht: [4, 5], pre: [2, 3], m: [7, 10], branch: [0, 1], holes: [0.5],
  floor: ({ hv, centre }) => (centre ? (hv < 110 ? T_DIRT : T_BRICK) : (hv < 500 ? T_COBBLE : T_BRICK)),
  prof: P([0.085, 0.09, 0.125], [0.034, 0.038, 0.07], 0.038, 1.2, 0.95, 0.32),
  dress(c) {
    F(c, [["between", { tile: B.T_CARVED, h: c.ht - 1, torch: 2, I: 2.9 }], ["ribs", { every: 3, off: 1, tile: T_SLAB, y: 1 }], ["webs", { n: 6 }], ["alcoves", { style: "cap", tile: T_BRICK }]]);
    if (c.hw >= 4 && c.rnd(1, 3) < 0.7) { const mid = Math.round((c.lo + c.hi) / 2); pool(c, { lu0: 2, lu1: 3, lv0: mid, lv1: mid + 3, liquid: c.rnd(2, 3) < 0.5 ? "water" : "lava" }); }
  } });

// 2. Doomlike worn crypt: older and colder, cracked brick, gravel heaps, the roof sagging in patches, one torch in eight.
def("worn", { style: wall([[250, T_BRICK], [560, T_BRICK_CRACK], [700, T_COBBLE], [850, T_STONE], [940, T_BRICK_MOSSY], [1000, T_GRAVEL_FLOOR]]), hw: [3, 3], ht: [4, 4], pre: [2, 3], m: [7, 11], branch: [1, 1], torchEvery: 2, torchI: 2.4,
  floor: ({ hv }) => (hv < 130 ? T_GRAVEL_FLOOR : hv < 480 ? T_BRICK_CRACK : T_BRICK),
  prof: P([0.055, 0.062, 0.08], [0.03, 0.032, 0.046], 0.042, 1.16, 0.8, 0.28),
  dress(c) {
    const clear = clearer(c);
    // Sagging patches of roof, two wide and three long, and gravel heaps along the foot of the walls.
    c.scatter(5, 11, (q, r1, r2) => { const sd = r2 < 0.5 ? -1 : 1, lv = Math.floor(c.lo + 2 + r1 * (c.hi - c.lo - 4)); if (!clear(sd, lv, 1)) return; for (let w = 0; w < 3; w++) for (let k = 0; k < 2; k++) c.L(c.leg, c.edgeCell(sd) - sd * k, lv + w, c.y0 + c.ht - 1, T_COBBLE); });
    c.scatter(9, 12, (q, r1, r2) => { const sd = r2 < 0.5 ? -1 : 1, lv = Math.floor(c.lo + r1 * (c.hi - c.lo)); if (!clear(sd, lv, 0)) return; c.L(c.leg, c.edgeCell(sd), lv, c.y0, T_GRAVEL_FLOOR); if (r1 < 0.45) c.L(c.leg, c.edgeCell(sd), lv + 1, c.y0, T_GRAVEL_FLOOR); });
    F(c, [["webs", { n: 10, w: 1.8 }], ["rubble", { n: 8 }]]);
    c.torches(8, 3, 2.3, 2);
  } });

// 3. Roguelike tomb gallery: every alcove is a quartz-capped tomb recess, a quartz pillar between each pair, a quartz runner down the hall.
def("tomb_gallery", { style: wall([[380, T_BRICK], [600, T_STONE], [800, T_BRICK_CRACK], [1000, T_COBBLE]]), hw: [3, 3], ht: [5, 5], pre: [3, 3], m: [6, 9], branch: [0, 1], step: 6,
  floor: ({ lu, lv, hv, centre }) => (centre ? ((lv % 2) ? T_QUARTZ : T_QUARTZ_P) : (hv < 200 ? T_BRICK_CRACK : T_BRICK)),
  prof: P([0.105, 0.115, 0.155], [0.042, 0.048, 0.075], 0.036, 1.22, 1.0, 0.36),
  dress(c) {
    F(c, [["alcoves", { style: "cap", tile: T_QUARTZ_C, pil: T_QUARTZ_P }], ["between", { tile: T_QUARTZ_P, h: c.ht - 1, torch: 2, I: 3.0, cap: T_QUARTZ_C }],
      ["band", { tile: T_QUARTZ, j0: c.ht - 1, j1: c.ht - 1, every: 1 }], ["webs", { n: 4 }]]);
  } });

// 4. Roguelike arch run: stone arches every four rows (the alcoves' own pillar rows), a keystone at the crown, torches in the insets.
def("arch_run", { style: wall([[550, T_STONE], [780, T_BRICK], [900, T_COBBLE], [1000, T_BRICK_CRACK]]), hw: [3, 3], ht: [5, 5], pre: [2, 2], m: [8, 12], branch: [1, 1],
  floor: ({ hv, lv }) => (lv % 4 === 0 ? T_BRICK : hv < 380 ? T_STONE : T_BRICK),
  prof: P([0.09, 0.088, 0.1], [0.036, 0.036, 0.046], 0.04, 1.2, 1.05, 0.3),
  dress(c) {
    F(c, [["arches", { tile: T_BRICK, key: T_CARVED, rise: 1, torch: 2, I: 2.9 }], ["webs", { n: 5 }]]);
    FEATURES.ribs(c, { every: 4, off: 3, tile: T_STONE, y: 1 });
  } });

// 7. Recurrent Complex carpet crypt: a red carpet runner, banners between the alcoves, and the only light a dim red.
def("carpet_crypt", { style: wall([[420, T_BRICK], [620, T_BRICK_CRACK], [800, T_STONE], [1000, T_COBBLE]]), hw: [3, 3], ht: [5, 5], pre: [3, 3], m: [6, 9], branch: [0, 1], step: 6,
  floor: ({ lv, hv, centre }) => (centre ? B.T_BRICK : (hv < 240 ? T_BRICK_CRACK : T_BRICK)),
  prof: P([0.105, 0.055, 0.062], [0.055, 0.026, 0.03], 0.04, 1.22, 1.05, 0.36),
  dress(c) {
    for (let lv = c.leg.cs + 2; lv < c.leg.ce - 2; lv++) if (c.floored(-1, lv, c.y0) && c.floored(0, lv, c.y0)) c.put("carpet", 0, lv + 0.5, c.y0, { w: 2, d: 1, color: 3, ry: c.yaw });   // none over a gap in the floor
    for (const s of c.leg.slots) for (const q of [-1.6, 1.6]) if (c.walled(c.edgeCell(s.side), Math.floor(s.lvc + 0.5 + q), c.y0 + 2)) c.put("banner", s.side * (c.hw - 1 - 0.06), s.lvc + 0.5 + q, c.y0 + 2.2, { ry: c.acrossRy, w: 0.8, h: 2.2, color: (s.lvc % 8 < 4) ? 3 : 2 });
    F(c, [["between", { tile: B.T_BRICK, h: c.ht - 1, torch: 2, I: 2.6, color: [1.0, 0.22, 0.12] }], ["torches", { every: 5, off: 1, I: 2.6, y: 3, color: [1.0, 0.25, 0.14] }]]);
    // Slits in the roof: coloured light falls through stained glass.
    for (let lv = c.lo + 2; lv < c.hi; lv += 6) {
      for (const lu of [-1, 0]) { c.L(c.leg, lu, lv, c.y0 + c.ht, T_AIR); c.L(c.leg, lu, lv, c.y0 + c.ht + 1, T_AIR); }
      c.put("pane", 0, lv + 0.5, c.y0 + c.ht + 1.98, { tex: "glass_red", w: 2, h: 1, ry: c.yaw, flat: true });   // a skylight under the cap of the slit, lying flat
      c.src(0, lv + 0.5, c.y0 + c.ht + 0.3, [0.95, 0.22, 0.2], 2.6, 9, {});
    }
  } });

// 12. Recurrent Complex raw-rock tunnel: smooth stone and nothing else, but a lava moat crosses it every fourteen blocks on a
//     two wide slab bridge, and the hall ends on a skeleton's shooting range.
def("raw_tunnel", { style: wall([[740, T_STONE], [880, T_COBBLE], [940, T_COAL], [970, T_IRON], [1000, T_STONE]]), hw: [3, 3], ht: [4, 4], pre: [2, 2], m: [7, 10], branch: [0, 1], below: 6,
  floor: ({ lu, lv, leg }) => {
    const moat = (lv - leg.b0 - 6) % 14;
    if (moat >= 0 && moat < 2 && (lu < -1 || lu > 0)) return { from: leg.y0 - 1, cells: [[leg.y0 - 2, T_LAVA], [leg.y0 - 3, T_OBS]], lava: false };
    return T_STONE;
  },
  prof: P([0.07, 0.07, 0.078], [0.03, 0.03, 0.034], 0.04, 1.18, 0.9, 0.4),
  dress(c) {
    const clear = clearer(c);
    for (let lv = c.leg.b0 + 6; lv < c.leg.ce - 3; lv += 14) {
      if (lv < c.lo - 1) continue;
      c.a.lavaRects.push({ ...rectOf(c, -3, -2, lv, lv + 1), y: c.y0 - 1.13 }, { ...rectOf(c, 1, 2, lv, lv + 1), y: c.y0 - 1.13 });
      for (const lu of [-3, 2]) { c.src(lu + 0.5, lv + 1, c.y0 - 0.2, [1.0, 0.36, 0.08], 6, 11, { lava: true, dyn: true }); c.emit("lava", lu + 0.5, lv + 1, c.y0 - 1.1); }
      c.a.spots.lava.push(c.W3(c.leg, 0, lv + 1, c.y0));
      for (const lu of [-1, 0]) for (let w = 0; w < 2; w++) c.L(c.leg, lu, lv + w, c.y0 - 1, T_SLAB);
    }
    F(c, [["torches", { every: 7, off: 2, I: 2.7, y: 2 }], ["webs", { n: 3 }]]);
    void clear;
  } });

// ---- Stratum 2: catacombs and ossuaries -------------------------------------------------------------------------
// 9. Roguelike dark hall: a vault of spruce beams and logs over a gravel-floored hall of cracked brick, one torch to a beam.
def("vaulted_hall", { style: wall([[380, T_BRICK], [640, T_BRICK_CRACK], [820, T_COBBLE], [940, T_BRICK_MOSSY], [1000, T_GRAVEL_FLOOR]]), hw: [3, 4], ht: [6, 6], pre: [2, 2], m: [6, 9], branch: [1, 1], step: 6,
  floor: ({ hv }) => (hv < 220 ? T_GRAVEL_FLOOR : hv < 500 ? T_BRICK_CRACK : T_BRICK),
  prof: P([0.092, 0.082, 0.075], [0.04, 0.034, 0.03], 0.038, 1.2, 1.05, 0.3),
  dress(c) {
    const { hw, y0, ht, leg } = c;
    // The stepped vault: planks on the upper edge cells, rising toward a ridge of logs along the roof.
    for (let lv = leg.cs + 1; lv < leg.ce - 1; lv++) {
      for (const sd of [-1, 1]) { c.L(leg, sd > 0 ? hw - 1 : -hw, lv, y0 + ht - 1, B.T_PLANK_SPRUCE); c.L(leg, sd > 0 ? hw - 2 : -hw + 1, lv, y0 + ht - 1, B.T_PLANK_SPRUCE); c.L(leg, sd > 0 ? hw - 1 : -hw, lv, y0 + ht - 2, B.T_PLANK_SPRUCE); }
    }
    for (let lv = c.lo + 1; lv < c.hi + 2; lv += 6) {
      for (let lu = -hw; lu < hw; lu++) c.L(leg, lu, lv, y0 + ht - 1, B.T_LOG_SPRUCE);
      for (const sd of [-1, 1]) if (c.leg.slots.every((s) => s.side !== sd || Math.abs(s.lvc - lv) > 3)) { for (let j = y0; j < y0 + ht - 2; j++) c.L(leg, c.edgeCell(sd), lv, j, B.T_LOG_SPRUCE); c.torchAt(leg, c.edgeCell(sd), lv, y0 + 2, -sd, { I: 3.0 }); }
    }
    F(c, [["webs", { n: 8, w: 1.8 }]]);
  } });

// 11. Recurrent Complex meso maze: a chain of small cells joined by doorways; each cell dressed differently.
def("cell_chain", { style: wall([[460, T_BRICK], [720, T_BRICK_CRACK], [860, T_STONE], [1000, T_BRICK_MOSSY]]), hw: [3, 3], ht: [4, 4], pre: [2, 2], m: [6, 9], branch: [0, 1], step: 4,
  floor: ({ hv }) => (hv < 240 ? T_BRICK_CRACK : T_BRICK),
  prof: P([0.105, 0.09, 0.09], [0.042, 0.036, 0.036], 0.04, 1.22, 1.0, 0.3),
  dress(c) {
    const clear = clearer(c);
    const cells = [];
    for (let lv = c.lo + 2; lv < c.hi - 1; lv += 7) cells.push(lv);
    cells.forEach((lv, i) => {
      if (!clear(-1, lv, 0) || !clear(1, lv, 0)) return;
      for (let lu = -c.hw; lu < c.hw; lu++) for (let j = c.y0; j < c.y0 + c.ht; j++) if (!((lu === -1 || lu === 0) && j < c.y0 + 3)) c.L(c.leg, lu, lv, j, i % 3 === 0 ? T_BRICK_CRACK : T_BRICK);
      c.torchAtB(c.leg, -2, lv, c.y0 + 2, -1, { I: 2.7 }); c.torchAtB(c.leg, 1, lv, c.y0 + 2, -1, { I: 2.7 });
      // The cell behind the doorway: a table, a collapse, a spawner stub or a shelf, chosen by dice.
      const r = c.rnd(i, 30), mid = lv + 3;
      if (r < 0.25) { c.put("cube", -2.5, mid + 0.5, c.y0, { side: "crafting_table_side", top: "crafting_table_top", ry: 0, h: 1 }); c.put("chest", 2.2, mid + 0.5, c.y0, { ry: c.faceRy(1) }); }
      else if (r < 0.5) { for (const lu of [-3, -2, 1, 2]) for (let w = 0; w < 2; w++) if (c.rnd(lu * 7 + w, 31 + i) < 0.7) c.L(c.leg, lu, mid + w, c.y0, T_GRAVEL_FLOOR); c.put("rubble", 1.8, mid + 1, c.y0, { s: 0.5, ry: i }); c.put("rubble", -2.2, mid, c.y0, { s: 0.4, ry: i + 2 }); }
      else if (r < 0.75) { c.put("web", -2.3, mid + 1, c.y0 + 1.2, { ry: c.yaw + 0.4, w: 2 }); c.put("web", 2.2, mid + 2, c.y0 + 1.3, { ry: c.yaw - 0.3, w: 2 }); c.put("spawner", -2.4, mid + 1.5, c.y0 + 1, { mob: "CaveSpider" }); c.src(-2.4, mid + 1.5, c.y0 + 1.7, [0.8, 0.5, 0.45], 2.6, 9, { dyn: true }); c.emit("spawner", -2.4, mid + 1.5, c.y0 + 2); }
      else { for (const sd of [-1, 1]) for (let j = c.y0; j <= c.y0 + 2; j++) if (clear(sd, mid, 1)) c.L(c.leg, c.edgeCell(sd), mid, j, B.T_SHELF); }
    });
    F(c, [["alcoves", { style: "none" }], ["webs", { n: 6 }]]);
  } });

// 13. Vanilla stronghold cell row: stone brick, and each alcove behind iron bars with a one block door.
def("barred_cells", { style: wall([[360, T_BRICK], [620, T_BRICK_MOSSY], [840, T_BRICK_CRACK], [960, T_STONE], [1000, T_CARVED]]), hw: [3, 4], ht: [5, 5], pre: [3, 3], m: [6, 9], branch: [0, 1], step: 6, torchEvery: 3,
  floor: ({ hv }) => (hv < 200 ? T_BRICK_CRACK : hv < 420 ? T_BRICK_MOSSY : T_BRICK),
  prof: P([0.078, 0.085, 0.1], [0.034, 0.038, 0.05], 0.036, 1.2, 0.9, 0.3),
  dress(c) {
    F(c, [["alcoves", { style: "cell" }], ["between", { tile: B.T_BRICK, h: c.ht - 1, torch: 2, I: 2.4 }], ["torches", { every: 12, off: 1, I: 2.5, y: 3 }]]);
    for (let lv = c.lo + 4; lv < c.hi - 2; lv += 11) { for (const lu of [-1, 0]) { c.L(c.leg, lu, lv, c.y0 + c.ht - 1, T_BRICK); } }
  } });

// 14. Roguelike cell block: the hall has a cell niche between every two alcoves, barred, and something pale standing in it.
def("cell_block", { style: wall([[380, T_BRICK], [640, T_BRICK_CRACK], [820, T_COBBLE], [1000, T_BRICK_MOSSY]]), hw: [3, 3], ht: [4, 4], pre: [3, 3], m: [6, 8], branch: [0, 0], step: 8,
  floor: ({ hv }) => (hv < 260 ? T_BRICK_CRACK : T_BRICK),
  prof: P([0.07, 0.075, 0.095], [0.032, 0.036, 0.05], 0.04, 1.18, 0.95, 0.3),
  dress(c) {
    const { hw, y0 } = c;
    c.leg.slots.forEach((s, i) => {
      for (const q of [-4, 4]) {
        const lv = s.lvc + q, sd = s.side;
        if (lv < c.leg.cs + 3 || lv > c.leg.ce - 3) continue;
        // A niche two deep, three high, two wide, behind bars, with a figure inside.
        for (let w = 0; w < 2; w++) for (let k = 0; k < 2; k++) for (let j = y0; j < y0 + 3; j++) c.L(c.leg, sd > 0 ? hw + k : -hw - 1 - k, lv + w, j, T_AIR);
        for (let w = -1; w < 3; w++) c.L(c.leg, sd > 0 ? hw - 1 : -hw, lv + w, y0 + 3, T_BRICK);
        c.put("bars", sd * (hw + 0.02), lv + 1, y0 + 1.5, { ry: c.acrossRy, w: 2, h: 3 });
        const r = c.rnd(i * 2 + (q > 0 ? 1 : 0), 33);
        if (r < 0.6) c.put("mob", sd * (hw + 1.2), lv + 1, y0, { mob: r < 0.3 ? "Skeleton" : "Zombie", ry: c.faceRy(sd), scale: 0.92, r: 24 });
        else { c.put("bone", sd * (hw + 0.8), lv + 0.8, y0 + 0.02, { ry: 1 }); c.put("skull", sd * (hw + 1.1), lv + 1.2, y0, { ry: c.faceRy(sd) }); c.put("web", sd * (hw + 0.5), lv + 1, y0 + 2.4, { ry: c.acrossRy, w: 1.2 }); }
      }
    });
    F(c, [["torches", { every: 8, off: 0, I: 2.5, y: 3 }], ["webs", { n: 4 }], ["bones", { n: 6 }]]);
  } });

// ---- Stratum 3: sewers and the drowned deep ---------------------------------------------------------------------
const SEWER = wall([[400, T_BRICK_MOSSY], [620, T_MOSSY], [820, T_BRICK], [940, T_BRICK_CRACK], [1000, T_COBBLE]]);
// 15. Roguelike sewer: a channel of water down the left side behind a curb, glowstone lamps with a green cast, grated alcoves.
def("sewer_walk", { style: SEWER, hw: [3, 4], ht: [4, 5], pre: [2, 2], m: [7, 11], branch: [1, 1], holes: [0.5], below: 5,
  floor: ({ hv, lu, leg }) => (lu === -leg.hw + 1 || lu === -leg.hw ? T_GRAVEL_FLOOR : hv < 300 ? T_BRICK_MOSSY : T_BRICK),
  prof: P([0.085, 0.13, 0.1], [0.03, 0.05, 0.04], 0.04, 1.22, 1.05, 0.3),
  dress(c) {
    const { hw, y0, leg } = c, lu0 = -hw, lu1 = -hw + 1;
    // The channel: the two left lanes sink one block, the curb stays at the lane beside.
    for (let lv = leg.cs + 1; lv < leg.ce - 1; lv++) for (let lu = lu0; lu <= lu1; lu++) { c.L(leg, lu, lv, y0 - 1, T_AIR); c.L(leg, lu, lv, y0 - 2, T_GRAVEL_FLOOR); }
    c.a.waterRects.push({ ...rectOf(c, lu0, lu1, leg.cs + 1, leg.ce - 2), y: y0 - 0.32 });
    for (let lv = leg.cs + 1; lv < leg.ce - 1; lv++) c.L(leg, lu1 + 1, lv, y0 - 1, T_STONE);
    for (let lv = c.lo; lv < c.hi; lv += 3) c.scatter(0, 1, () => {});
    F(c, [["alcoves", { style: "bars" }], ["roofLamps", { every: 6, off: 2, tile: B.T_GLOW, color: [0.8, 1.0, 0.55], I: 3.0, lus: [1] }], ["vines", { n: 10 }], ["webs", { n: 4 }]]);
    for (let q = 0; q < 12; q++) { const lv = c.lo + 1 + c.rnd(q, 14) * (c.hi - c.lo - 2); const [x, , z] = c.W3(leg, lu0 + 0.5 + c.rnd(q, 15), lv, 0); c.a.emit.push({ k: "drip", x, y: y0 + c.ht - 0.1, z, floorY: y0 - 1.3 }); c.a.spots.drip.push([x, y0, z]); }
    for (let lv = c.lo + 2; lv < c.hi; lv += 6) c.put("lily", lu0 + 0.5 + (lv % 2), lv, y0 - 0.34, { ry: lv });
  } });

// 16. Roguelike drain gallery: alcoves alternate with iron-barred drains that pour sheets of water into a channel along the wall.
def("drain_gallery", { style: SEWER, hw: [3, 3], ht: [4, 4], pre: [2, 2], m: [6, 9], branch: [0, 1], step: 8, below: 5,
  floor: ({ hv, lu, leg }) => (lu === -leg.hw ? T_GRAVEL_FLOOR : hv < 280 ? T_BRICK_MOSSY : T_BRICK),
  prof: P([0.08, 0.125, 0.105], [0.028, 0.05, 0.044], 0.04, 1.22, 1.1, 0.3),
  dress(c) {
    const { hw, y0, leg } = c;
    for (let lv = leg.cs + 1; lv < leg.ce - 1; lv++) { c.L(leg, -hw, lv, y0 - 1, T_AIR); c.L(leg, -hw, lv, y0 - 2, T_GRAVEL_FLOOR); }
    c.a.waterRects.push({ ...rectOf(c, -hw, -hw, leg.cs + 1, leg.ce - 2), y: y0 - 0.32 });
    // Drains between the alcoves: a bars-fronted recess in the right wall (the alcoves sit alternately on both sides).
    for (const s of leg.slots) {
      for (const q of [-4, 4]) {
        const lv = s.lvc + q, sd = s.side;
        if (lv < leg.cs + 3 || lv > leg.ce - 3) continue;
        for (let w = 0; w < 2; w++) for (let j = y0 + 1; j <= y0 + 2; j++) c.L(leg, c.wallCell(sd), lv + w, j, T_AIR);
        c.put("bars", sd * (hw + 0.02), lv + 1, y0 + 2, { ry: c.acrossRy, w: 2, h: 2 });
        if (sd < 0) c.put("sheet", -hw - 0.3, lv + 1, y0 + 1.5, { ry: c.acrossRy, w: 1.4, h: 2.4 });
        else c.put("sheet", hw + 0.3, lv + 1, y0 + 1.5, { ry: c.acrossRy, w: 1.4, h: 2.4 });
        c.src(sd * (hw + 0.5), lv + 1, y0 + 1.4, [0.5, 0.9, 0.7], 1.6, 6, {});
        c.emit("drip", sd * (hw + 0.5), lv + 1, y0 + 2.8, { floorY: y0 - 0.3 });
      }
    }
    F(c, [["between", { tile: T_BRICK_MOSSY, h: c.ht - 1, torch: 2, I: 2.7 }], ["vines", { n: 8 }]]);
  } });

// 17. Doomlike dank swamp hall: the floor is water, a two wide plank causeway with fence rails runs through, logs under it.
def("plank_causeway", { style: wall([[460, T_MOSSY], [700, T_BRICK_MOSSY], [860, T_COBBLE], [1000, T_BRICK]]), hw: [4, 4], ht: [5, 5], pre: [2, 2], m: [6, 10], branch: [1, 1], holes: [0.6], below: 5,
  floor: ({ lu, hv, yf }) => ((lu === -1 || lu === 0) ? B.T_PLANK : { from: yf - 1, cells: [[yf - 2, T_GRAVEL_FLOOR]] }),
  alcoveBase: (leg) => leg.y0 - 1,
  prof: P([0.085, 0.125, 0.085], [0.028, 0.05, 0.034], 0.038, 1.22, 1.15, 0.32),
  dress(c) {
    const { hw, y0, leg } = c;
    c.a.waterRects.push({ ...rectOf(c, -hw, -2, leg.cs + 1, leg.ce - 2), y: y0 - 0.3 }, { ...rectOf(c, 1, hw - 1, leg.cs + 1, leg.ce - 2), y: y0 - 0.3 });
    c.a.spots.water.push(c.W3(leg, 0, (c.lo + c.hi) / 2, y0));
    for (let lv = c.lo; lv < c.hi + 2; lv += 5) for (const lu of [-2, 1]) { c.put("fence", lu + (lu < 0 ? 0.9 : 0.1), lv, y0, { h: 1.2, tex: "planks_oak", len: 0 }); }
    for (let lv = c.lo + 1; lv < c.hi + 2; lv++) for (const lu of [-2, 1]) if (lv % 5 !== 0) c.put("fence", lu + (lu < 0 ? 0.9 : 0.1), lv + 0.5, y0 + 0.5, { h: 0.1, tex: "planks_oak" });
    for (let q = 0; q < 30; q++) { const lv = c.lo + c.rnd(q, 22) * (c.hi - c.lo), lu = (c.rnd(q, 23) < 0.5 ? -1 : 1) * (1.6 + c.rnd(q, 24) * (hw - 2.4)); c.put("lily", lu, lv, y0 - 0.28, { ry: q }); }
    for (let lv = c.lo + 2; lv < c.hi; lv += 8) for (const lu of [-3, 2]) { c.col(lu, lv, y0 - 1, y0 + c.ht - 1, B.T_LOG); c.torchAt(leg, lu, lv, y0 + 3, lu < 0 ? 1 : -1, { I: 3.0 }); }
    F(c, [["vines", { n: 14 }], ["webs", { n: 6 }]]);
  } });

// 18. Doomlike oceanic hall: a plain brick corridor under the sea: the roof is a sheet of water, the fog blue, the light caustic.
def("drowned_hall", { style: wall([[430, T_BRICK], [650, T_BRICK_MOSSY], [830, T_BRICK_CRACK], [940, T_MOSSY], [1000, B.T_SPONGE]]), hw: [3, 4], ht: [5, 5], pre: [2, 2], m: [7, 10], branch: [1, 1],
  floor: ({ hv }) => (hv < 300 ? T_GRAVEL_FLOOR : hv < 500 ? T_BRICK_MOSSY : T_BRICK),
  prof: P([0.07, 0.14, 0.18], [0.02, 0.06, 0.085], 0.046, 1.26, 1.1, 0.34),
  dress(c) {
    const { hw, y0, ht, leg } = c;
    c.a.waterRects.push({ ...rectOf(c, -hw, hw - 1, leg.cs + 1, leg.ce - 2), y: y0 + ht - 0.3, ds: true });
    F(c, [["between", { tile: T_BRICK_MOSSY, h: c.ht - 1, torch: 2, I: 3.2, color: [0.6, 0.95, 1.0] }], ["alcoves", { style: "cap", tile: T_BRICK_MOSSY }], ["vines", { n: 12, h: 2 }]]);
    for (let q = 0; q < 16; q++) { const lv = c.lo + c.rnd(q, 14) * (c.hi - c.lo), lu = (c.rnd(q, 15) - 0.5) * hw * 1.6; c.a.emit.push({ k: "drip", x: c.W3(leg, lu, lv, 0)[0], y: y0 + ht - 0.2, z: c.W3(leg, lu, lv, 0)[2], floorY: y0 }); }
    c.a.sources.push(...[]);
    for (let lv = c.lo; lv < c.hi; lv += 6) c.src(0, lv, y0 + ht - 0.8, [0.45, 0.85, 1.0], 2.4, 10, {});
  } });

// 19. Roguelike pit trap: a stone plate in the floor and red torches in the wall, two outlets of water above the hall.
def("pressure_flood", { style: wall([[440, T_BRICK], [700, T_STONE], [860, T_BRICK_MOSSY], [1000, T_BRICK_CRACK]]), hw: [3, 3], ht: [5, 5], pre: [2, 2], m: [6, 8], branch: [0, 1], step: 6,
  floor: ({ hv }) => (hv < 200 ? T_BRICK_MOSSY : T_BRICK),
  prof: P([0.09, 0.105, 0.115], [0.036, 0.044, 0.05], 0.038, 1.2, 1.0, 0.32),
  dress(c) {
    const { y0, ht } = c, clear = clearer(c);
    for (let lv = c.lo + 3; lv < c.hi - 1; lv += 8) {
      if (!clear(-1, lv, 1) || !clear(1, lv, 1)) continue;
      for (const lu of [-1, 0]) c.put("plate", lu + 0.5, lv + 0.5, y0, {});
      for (const sd of [-1, 1]) { c.torchAt(c.leg, c.wallCell(sd), lv, y0 + 1, -sd, { I: 1.8, c: [1.0, 0.18, 0.1] }); for (let j = y0 + ht - 2; j < y0 + ht; j++) c.L(c.leg, c.wallCell(sd), lv + 1, j, T_AIR); c.put("bars", sd * (c.hw + 0.02), lv + 1.5, y0 + ht - 1.2, { ry: c.acrossRy, w: 1, h: 2 }); }
    }
    F(c, [["between", { tile: T_BRICK, h: c.ht - 1, torch: 2, I: 2.7 }], ["alcoves", { style: "bars" }], ["webs", { n: 4 }]]);
  } });
