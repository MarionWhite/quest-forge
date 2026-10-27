// The original fifteen kinds (ported unchanged from rounds 1 to 5) and the registry's first entries; the strata's own
// kinds live in kinds_*.js and register themselves on import.
import {
  T_AIR, T_STONE, T_COBBLE, T_MOSSY, T_BRICK, T_BRICK_MOSSY, T_BRICK_CRACK, T_GRAVEL_FLOOR, T_COAL, T_IRON, T_OBS, T_BEDROCK,
  T_NETHER, T_GLOW, T_BRIDGE, T_WATER, T_NBRICK, T_SOUL, T_SHELF, T_PLANK, T_LOG, T_LAVA, T_DIRT, T_DISP_PX, T_DISP_NX,
  T_DISP_PZ, T_DISP_NZ, T_GOLD, T_DIAM, T_LAPIS, T_EMERALD, T_IRONB, T_CARVED, T_WALL, ih
} from "./blocks.js";
import * as B from "./blocks.js";
import { floorTop, STAIR_LANDING, STAIR_LEN, STAIR_DROP, CHASM_DEPTH, FORT_DEPTH } from "./geom.js";
import { KINDS, def, wall, P, makeCtx } from "./kindreg.js";
export { KINDS, makeCtx };
import "./kinds_a.js";
import "./kinds_b.js";
import { applyArch } from "./kinds_c.js";

// ---- the dressers of the nine original segments and the six of round 5 (ported unchanged) ----
const DRESS = {};

DRESS.crypt = (c) => {
  const { a, plan, leg, L, LG, W3, dirw, torchAt, torchAtB, pushTorch, decor, legCell, set, get, hw, y0, kind, ht, rowsFree, lo, hi, yaw, rnd, wallCell, edgeCell, dispType, webAt, freeRow } = c;
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
};

DRESS.mine = (c) => {
  const { a, plan, leg, L, LG, W3, dirw, torchAt, torchAtB, pushTorch, decor, legCell, set, get, hw, y0, kind, ht, rowsFree, lo, hi, yaw, rnd, wallCell, edgeCell, dispType, webAt, freeRow } = c;
    // Support frames: a log post at the edge of the free stretch and a plank beam across the roof.
    for (const s of leg.slots) {
      const lv = s.lvc + 4, sd = s.side;
      if (!rowsFree(sd, lv) || !rowsFree(sd, lv + 1)) continue;
      for (let j = y0; j <= y0 + 2; j++) L(leg, edgeCell(sd), lv, j, T_LOG);
      for (let lu = -hw; lu < hw; lu++) if (LG(leg, lu, lv, y0 + 3) === T_AIR) L(leg, lu, lv, y0 + 3, T_PLANK);
      torchAt(leg, wallCell(-sd), lv, y0 + 2, sd, { I: 2.9 });
      decor({ t: "web", x: W3(leg, -sd * (hw - 0.3), lv + 0.5, 0)[0], y: y0 + 3.1, z: W3(leg, -sd * (hw - 0.3), lv + 0.5, 0)[2], ry: yaw + Math.PI / 4, w: 1.5 });
    }
    // Rails down one lane, a minecart on them, a heap of rubble where the roof gave way.
    for (let lv = lo - 2; lv < hi; lv++) { const [x, y, z] = W3(leg, 0.5, lv + 0.5, y0); decor({ t: "rail", x, y: y + 0.02, z, ry: leg.h === "N" ? 0 : Math.PI / 2 }); }
    const mid = Math.round((lo + hi) / 2);
    const [cx, cy, cz] = W3(leg, 0.5, mid + 0.5, y0);
    decor({ t: "cart", x: cx, y: cy, z: cz, ry: yaw + Math.PI / 2 });
    const rub = Math.min(hi - 3, lo + 3);
    for (let lv = rub; lv < rub + 2; lv++) for (let lu = -hw; lu < -hw + 2; lu++) {
      if (rowsFree(-1, lv) && LG(leg, lu, lv, y0) === T_AIR) { L(leg, lu, lv, y0, rnd(lu + lv, 1) < 0.5 ? T_COBBLE : T_GRAVEL_FLOOR); if (lu === -hw) L(leg, lu, lv, y0 + 1, T_COBBLE); }
    }
    // A beam that has come down, one end on the floor.
    const [fx, fy, fz] = W3(leg, 1.2, hi - 2.5, y0 + 1.3);
    decor({ t: "beam", x: fx, y: fy, z: fz, ry: yaw + 0.3, rz: 0.75, len: 3.1 });
};

DRESS.ossuary = (c) => {
  const { a, plan, leg, L, LG, W3, dirw, torchAt, torchAtB, pushTorch, decor, legCell, set, get, hw, y0, kind, ht, rowsFree, lo, hi, yaw, rnd, wallCell, edgeCell, dispType, webAt, freeRow } = c;
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
};

DRESS.flood = (c) => {
  const { a, plan, leg, L, LG, W3, dirw, torchAt, torchAtB, pushTorch, decor, legCell, set, get, hw, y0, kind, ht, rowsFree, lo, hi, yaw, rnd, wallCell, edgeCell, dispType, webAt, freeRow } = c;
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
};

DRESS.dungeon = (c) => {
  const { a, plan, leg, L, LG, W3, dirw, torchAt, torchAtB, pushTorch, decor, legCell, set, get, hw, y0, kind, ht, rowsFree, lo, hi, yaw, rnd, wallCell, edgeCell, dispType, webAt, freeRow } = c;
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
};

DRESS.library = (c) => {
  const { a, plan, leg, L, LG, W3, dirw, torchAt, torchAtB, pushTorch, decor, legCell, set, get, hw, y0, kind, ht, rowsFree, lo, hi, yaw, rnd, wallCell, edgeCell, dispType, webAt, freeRow } = c;
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
};

DRESS.chasm = (c) => {
  const { a, plan, leg, L, LG, W3, dirw, torchAt, torchAtB, pushTorch, decor, legCell, set, get, hw, y0, kind, ht, rowsFree, lo, hi, yaw, rnd, wallCell, edgeCell, dispType, webAt, freeRow } = c;
    // Parapet posts along the bridge with torches, obsidian at either end.
    // No rails: the bridge is four wide and open on both sides, so the drop and the lava read from the walk.
    a.spots.fire.push(...a.spots.lava);
};

DRESS.catacomb = (c) => {
  const { a, plan, leg, L, LG, W3, dirw, torchAt, torchAtB, pushTorch, decor, legCell, set, get, hw, y0, kind, ht, rowsFree, lo, hi, yaw, rnd, wallCell, edgeCell, dispType, webAt, freeRow } = c;
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
        if (j === y0 + 1 && ih(lv, leg.rid, sd + 3, 61) < 600) a.sources.push({ x: x + sd * -0.3, y: j + 0.6, z, c: [1.0, 0.72, 0.4], I: 2.6, R: 7 });
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
};

DRESS.spidermine = (c) => {
  const { a, plan, leg, L, LG, W3, dirw, torchAt, torchAtB, pushTorch, decor, legCell, set, get, hw, y0, kind, ht, rowsFree, lo, hi, yaw, rnd, wallCell, edgeCell, dispType, webAt, freeRow } = c;
    // A web-choked mineshaft: close timber frames, curtains of cobweb, rails under the webs, and a cave spider spawner.
    for (let lv = lo + 1; lv < hi; lv += 4) {
      for (const sd of [-1, 1]) if (rowsFree(sd, lv)) for (let j = y0; j <= y0 + 2; j++) if (LG(leg, edgeCell(sd), lv, j) === T_AIR) L(leg, edgeCell(sd), lv, j, T_LOG);
      for (let lu = -hw; lu < hw; lu++) if (LG(leg, lu, lv, y0 + 3) === T_AIR) L(leg, lu, lv, y0 + 3, T_PLANK);
      if ((lv - lo) % 8 === 1 && rowsFree(1, lv + 1)) torchAt(leg, wallCell(1), lv + 1, y0 + 2, -1, { I: 2.4 });
    }
    for (let lv = lo - 2; lv < hi; lv++) { const [x, y, z] = W3(leg, 0.5, lv + 0.5, y0); decor({ t: "rail", x, y: y + 0.02, z, ry: leg.h === "N" ? 0 : Math.PI / 2 }); }
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
};

DRESS.temple = (c) => {
  const { a, plan, leg, L, LG, W3, dirw, torchAt, torchAtB, pushTorch, decor, legCell, set, get, hw, y0, kind, ht, rowsFree, lo, hi, yaw, rnd, wallCell, edgeCell, dispType, webAt, freeRow } = c;
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
    for (let lv = lo + 5; lv < hi - 4; lv += 8) if (rowsFree(-1, lv) && rowsFree(1, lv) && lv % 12 !== (lo + 3) % 12) for (const sd of [-1, 1]) torchAt(leg, wallCell(sd), lv, y0 + 2, -sd, { I: 2.4 });
};

DRESS.vault = (c) => {
  const { a, plan, leg, L, LG, W3, dirw, torchAt, torchAtB, pushTorch, decor, legCell, set, get, hw, y0, kind, ht, rowsFree, lo, hi, yaw, rnd, wallCell, edgeCell, dispType, webAt, freeRow } = c;
    // The vault gate: a brick wall across the hall with an opening two wide and two high, the iron doors flung open;
    // inside, the hoard on the free walls and a diamond block on a pedestal.
    const g0 = leg.b0 + 3;
    for (let lv = g0; lv < g0 + 2; lv++) for (let lu = -hw; lu < hw; lu++) for (let j = y0; j < y0 + ht; j++) {
      const gap = (lu === -1 || lu === 0) && j < y0 + 2;
      L(leg, lu, lv, j, gap ? T_AIR : (j === y0 + 2 && (lu === -1 || lu === 0) ? T_IRONB : T_BRICK));
    }
    for (const lu of [-2, 1]) torchAtB(leg, lu, g0, y0 + 2, -1, { I: 3.2 });
    // The far gate, the same as the first, so the hall ends in a wall and not in the next segment's ceiling.
    const g1 = leg.ce - 2;
    for (let lv = g1; lv < g1 + 2; lv++) for (let lu = -hw; lu < hw; lu++) for (let j = y0; j < y0 + ht; j++) {
      const gap = (lu === -1 || lu === 0) && j < y0 + 2;
      L(leg, lu, lv, j, gap ? T_AIR : T_BRICK);
    }
    for (const lu of [-2, 1]) torchAtB(leg, lu, g1, y0 + 2, -1, { I: 3.2 });
    for (const sd of [-1, 1]) { const [x, y, z] = W3(leg, sd * 0.9, g1 + 1.0, y0); decor({ t: "idoor", x, y, z, ry: yaw }); }
    for (const sd of [-1, 1]) {
      const [x, y, z] = W3(leg, sd * 0.9, g0 + 1.0, y0);
      decor({ t: "idoor", x, y, z, ry: yaw });
    }
    // Ordered storage: gold block pillars three high every sixth row on each wall, a chest between them (single: two side by
    // side would join into a double chest in the game).
    let pq = 0;
    for (const sd of [-1, 1]) for (let lv = lo + 1; lv < hi + 1; lv++) {
      if (!rowsFree(sd, lv) || !rowsFree(sd, lv + 1) || !rowsFree(sd, lv - 1)) continue;
      if ((lv + (sd > 0 ? 3 : 0)) % 6 !== 0) continue;
      const lu = edgeCell(sd);
      if (LG(leg, lu, lv, y0) !== T_AIR) continue;
      for (let j = y0; j <= y0 + 2; j++) L(leg, lu, lv, j, T_GOLD);
      const [gx, , gz] = W3(leg, lu + 0.5, lv + 0.5, 0);
      a.sources.push({ x: gx, y: y0 + 3.2, z: gz, c: [1.0, 0.82, 0.38], I: 2.2, R: 8 });
      pq++;
    }
    for (const sd of [-1, 1]) for (let lv = lo + 1; lv < hi; lv++) {
      if (!rowsFree(sd, lv) || !rowsFree(sd, lv + 1)) continue;
      if ((lv + (sd > 0 ? 3 : 0)) % 6 !== 3) continue;
      const [x, y, z] = W3(leg, sd * (hw - 0.5), lv + 0.5, y0);
      decor({ t: "chest", x, y, z, ry: yaw - sd * Math.PI / 2 });
    }
    for (let lv = lo + 2; lv < hi; lv += 5) for (const sd of [-1, 1]) if (rowsFree(sd, lv)) torchAt(leg, wallCell(sd), lv, y0 + 3, -sd, { I: 3.2 });
    // The far end: a diamond block on an iron pedestal between gold pillars, behind bars.
    const pv = leg.ce - leg.post - 1;
    for (const lu of [-1, 0]) for (const lv of [pv, pv + 1]) L(leg, lu, lv, y0, T_IRONB);
    L(leg, 0, pv, y0 + 1, T_DIAM);
    for (const lu of [-3, 2]) for (const lv of [pv - 1, pv + 2]) for (let j = y0; j <= y0 + 3; j++) L(leg, lu, lv, j, T_GOLD);
    const [px, , pz] = W3(leg, 0.5, pv + 1.0, 0);
    a.sources.push({ x: px, y: y0 + 2.6, z: pz, c: [0.7, 0.96, 1.0], I: 3.6, R: 11, dyn: true });
    for (let lv = lo; lv < hi; lv += 4) { const sd = (lv / 4) % 2 ? 1 : -1; const [x, , z] = W3(leg, sd * (hw - 0.3), lv, 0); decor({ t: "web", x, y: y0 + ht - 0.6, z, ry: yaw + sd * Math.PI / 4, w: 1.2 }); }
};

DRESS.fortress = (c) => {
  const { a, plan, leg, L, LG, W3, dirw, torchAt, torchAtB, pushTorch, decor, legCell, set, get, hw, y0, kind, ht, rowsFree, lo, hi, yaw, rnd, wallCell, edgeCell, dispType, webAt, freeRow } = c;
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
};

DRESS.stairs = (c) => {
  const { a, plan, leg, L, LG, W3, dirw, torchAt, torchAtB, pushTorch, decor, legCell, set, get, hw, y0, kind, ht, rowsFree, lo, hi, yaw, rnd, wallCell, edgeCell, dispType, webAt, freeRow } = c;
    for (let lv = leg.stairsAt + 1; lv < leg.stairsAt + STAIR_LEN; lv += 4) for (const sd of [-1, 1]) {
      const yf = floorTop(leg, lv);
      torchAt(leg, wallCell(sd), lv, yf + 2, -sd, { I: 3.4 });
    }
    for (const sd of [-1, 1]) torchAt(leg, wallCell(sd), leg.b0 + 1, y0 + 2, -sd, { I: 2.9 });
};

DRESS.deep = (c) => {
  const { a, plan, leg, L, LG, W3, dirw, torchAt, torchAtB, pushTorch, decor, legCell, set, get, hw, y0, kind, ht, rowsFree, lo, hi, yaw, rnd, wallCell, edgeCell, dispType, webAt, freeRow } = c;
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
};

// ---- wall styles of the original kinds ----
const W = {
  crypt: wall([[150, T_COBBLE], [230, T_MOSSY], [560, T_BRICK], [700, T_BRICK_MOSSY], [1000, T_BRICK_CRACK]]),
  mine: wall([[320, T_COBBLE], [600, T_STONE], [670, T_MOSSY], [790, T_DIRT], [900, T_COAL], [925, T_IRON], [1000, T_COBBLE]]),
  ossuary: wall([[330, T_BRICK], [700, T_BRICK_CRACK], [850, T_COBBLE], [960, T_BRICK_MOSSY], [1000, T_OBS]]),
  flood: wall([[420, T_BRICK_MOSSY], [650, T_MOSSY], [880, T_BRICK], [1000, T_BRICK_CRACK]]),
  dungeon: wall([[700, T_MOSSY], [1000, T_COBBLE]]),
  library: wall([[620, T_BRICK], [740, T_BRICK_CRACK], [840, T_BRICK_MOSSY], [1000, T_COBBLE]]),
  chasm: wall([[300, T_STONE], [550, T_COBBLE], [700, T_OBS], [880, T_NETHER], [1000, T_BEDROCK]]),
  stairs: wall([[400, T_BRICK], [650, T_COBBLE], [1000, T_BRICK_CRACK]]),
  deep: wall([[380, T_NBRICK], [840, T_NETHER], [880, T_GLOW], [940, T_OBS], [1000, T_NETHER]]),
  catacomb: wall([[260, T_BRICK], [520, T_BRICK_CRACK], [700, T_STONE], [820, T_BRICK_MOSSY], [940, T_COBBLE], [1000, T_BRICK_CRACK]]),
  spidermine: wall([[260, T_DIRT], [450, T_COBBLE], [620, T_STONE], [800, T_COAL], [880, T_IRON], [960, T_GRAVEL_FLOOR], [1000, T_COBBLE]]),
  temple: wall([[470, T_MOSSY], [940, T_COBBLE], [1000, T_BRICK_MOSSY]]),
  vault: wall([[470, T_BRICK], [740, T_STONE], [900, T_BRICK_CRACK], [1000, T_BRICK]]),
  fortress: wall([[640, T_NBRICK], [920, T_NBRICK], [960, T_NETHER], [1000, T_NBRICK]]),
  stronghold: wall([[300, T_BRICK], [520, T_BRICK_MOSSY], [700, T_BRICK_CRACK], [880, T_STONE], [940, T_CARVED], [1000, T_BRICK]])
};
export { W as WALL_STYLES };

// ---- the original kinds: geometry, floor, light ----
// A floor spec is a tile (the block under the walk), or { from, cells, lava }: air from y `from`, then these [y, tile] cells.
def("crypt", { style: W.crypt, hw: [3, 3], ht: [4, 4], pre: [6, 6], m: [5, 7], branch: [0, 0], holes: [0.6], weight: 2, torchEvery: 2, torchI: 2.6,
  floor: ({ hv, centre }) => (centre ? (hv < 250 ? T_BRICK_CRACK : hv < 420 ? T_BRICK_MOSSY : T_BRICK) : T_GRAVEL_FLOOR),
  prof: P([0.060, 0.082, 0.150], [0.030, 0.040, 0.075], 0.040, 1.18, 0.78, 0.30), dress: DRESS.crypt });
def("mine", { style: W.mine, hw: [3, 3], ht: [4, 4], pre: [2, 2], m: [7, 11], branch: [1, 1], holes: [0.45],
  floor: ({ hv, centre }) => (centre && hv < 500 ? T_DIRT : T_GRAVEL_FLOOR), step: 4,
  prof: P([0.075, 0.075, 0.085], [0.040, 0.036, 0.040], 0.040, 1.18, 0.9, 0.32), dress: DRESS.mine });
def("catacomb", { style: W.catacomb, hw: [3, 3], ht: [4, 4], pre: [3, 3], m: [5, 8], branch: [1, 1], step: 8,
  floor: ({ hv, centre }) => (centre ? (hv < 220 ? T_BRICK_CRACK : T_BRICK) : (hv < 500 ? T_COBBLE : T_GRAVEL_FLOOR)),
  prof: P([0.115, 0.128, 0.150], [0.036, 0.042, 0.054], 0.040, 1.22, 1.1, 0.32), dress: DRESS.catacomb });
def("ossuary", { style: W.ossuary, hw: [3, 3], ht: [4, 4], pre: [2, 2], m: [8, 12], branch: [2, 2], torchEvery: 2,
  floor: ({ hv }) => (hv < 300 ? T_BRICK_CRACK : hv < 420 ? T_GRAVEL_FLOOR : T_BRICK),
  prof: P([0.150, 0.125, 0.140], [0.050, 0.038, 0.046], 0.038, 1.24, 1.1, 0.32), dress: DRESS.ossuary });
def("flood", { style: W.flood, hw: [4, 4], ht: [5, 5], pre: [2, 2], m: [7, 11], branch: [1, 1], holes: [0.5], below: 5,
  floor: ({ lu, hv, yf }) => (lu >= -1 && lu <= 0 ? (hv < 300 ? T_BRICK_MOSSY : T_BRICK) : { from: yf - 1, cells: [[yf - 2, T_GRAVEL_FLOOR]] }),
  alcoveBase: (leg) => leg.y0 - 1,
  prof: P([0.100, 0.165, 0.185], [0.026, 0.055, 0.064], 0.036, 1.24, 1.15, 0.34), dress: DRESS.flood });
def("spidermine", { style: W.spidermine, hw: [3, 3], ht: [4, 4], pre: [2, 2], m: [5, 8], branch: [1, 1], step: 8,
  floor: ({ hv }) => (hv < 420 ? T_GRAVEL_FLOOR : hv < 700 ? T_DIRT : T_COBBLE),
  prof: P([0.115, 0.100, 0.112], [0.040, 0.032, 0.040], 0.040, 1.24, 1.15, 0.30), dress: DRESS.spidermine });
def("temple", { style: W.temple, hw: [3, 3], ht: [5, 5], pre: [3, 3], post: [2, 2], m: [4, 6], branch: [1, 1], step: 12,
  floor: ({ hv }) => (hv < 520 ? T_MOSSY : hv < 560 ? T_BRICK_MOSSY : T_COBBLE),
  prof: P([0.098, 0.135, 0.088], [0.034, 0.056, 0.032], 0.038, 1.22, 1.25, 0.34), dress: DRESS.temple });
def("dungeon", { style: W.dungeon, hw: [6, 6], ht: [5, 5], pre: [4, 4], post: [4, 4], m: [4, 6], branch: [0, 0],
  floor: ({ hv }) => (hv < 650 ? T_MOSSY : T_COBBLE),
  prof: P([0.095, 0.082, 0.062], [0.044, 0.034, 0.026], 0.036, 1.2, 1.1, 0.36), dress: DRESS.dungeon });
def("library", { style: W.library, hw: [4, 4], ht: [6, 6], pre: [2, 2], m: [6, 10], branch: [1, 1], holes: [0.8],
  floor: ({ hv }) => (hv < 160 ? T_BRICK_CRACK : T_BRICK),
  prof: P([0.115, 0.082, 0.052], [0.052, 0.035, 0.022], 0.034, 1.2, 1.0, 0.36), dress: DRESS.library });
def("vault", { style: W.vault, hw: [4, 4], ht: [6, 6], pre: [6, 6], post: [3, 3], m: [5, 8], branch: [0, 0], step: 8,
  floor: ({ hv, centre, lv }) => (centre && lv % 4 === 0 ? T_IRONB : (hv < 250 ? T_BRICK_CRACK : T_BRICK)),
  prof: P([0.088, 0.086, 0.100], [0.042, 0.042, 0.054], 0.034, 1.2, 1.1, 0.40), dress: DRESS.vault });
def("chasm", { style: W.chasm, hw: [6, 6], ht: [6, 6], pre: [3, 3], m: [6, 10], branch: [0, 0], holes: [0.3, 0.75], below: CHASM_DEPTH + 3,
  floor: ({ lu, leg }) => (lu >= -2 && lu < 2 ? T_BRIDGE : { from: leg.y0 - CHASM_DEPTH, cells: [[leg.y0 - CHASM_DEPTH - 1, T_BEDROCK], [leg.y0 - CHASM_DEPTH, T_LAVA]], lava: true }),
  alcoveBase: (leg) => leg.y0 - CHASM_DEPTH + 1, lavaI: 9, lavaDepth: CHASM_DEPTH,
  prof: P([0.105, 0.052, 0.032], [0.070, 0.028, 0.014], 0.030, 1.22, 0.8, 0.46, { pitch: -0.3 }), dress: DRESS.chasm });
def("stairs", { styleOf: (leg) => leg.st.def.stairWalls || W.stairs, hw: [3, 3], ht: [4, 4], pre: [0, 0], m: [1, 1], branch: [0, 0], stairs: true,
  floor: ({ hv }) => (hv < 200 ? T_BRICK_CRACK : T_BRICK),
  prof: P([0.095, 0.048, 0.028], [0.066, 0.026, 0.012], 0.034, 1.22, 0.75, 0.44), dress: DRESS.stairs });
def("fortress", { style: W.fortress, hw: [5, 5], ht: [6, 6], pre: [3, 3], post: [2, 2], m: [5, 8], branch: [1, 1], step: 8, below: FORT_DEPTH + 3,
  floor: ({ lu, leg }) => (lu >= -2 && lu < 2 ? T_NBRICK : { from: leg.y0 - FORT_DEPTH, cells: [[leg.y0 - FORT_DEPTH - 1, T_BEDROCK], [leg.y0 - FORT_DEPTH, T_LAVA]], lava: true }),
  alcoveBase: (leg) => leg.y0 - FORT_DEPTH + 1, alcoveTile: T_NBRICK, lavaI: 14, lavaDepth: FORT_DEPTH,
  prof: P([0.180, 0.078, 0.058], [0.090, 0.030, 0.020], 0.030, 1.25, 1.3, 0.50), dress: DRESS.fortress });
def("deep", { style: W.deep, hw: [4, 4], ht: [5, 5], pre: [2, 2], post: [4, 4], m: [7, 12], branch: [1, 1],
  floor: ({ lu, lv, hv, leg, yf }) => ((lu === -leg.hw || lu === leg.hw - 1) ? { from: yf - 1, cells: [[yf - 1, T_LAVA], [yf - 2, T_OBS]] } : (hv < 560 ? T_SOUL : hv < 840 ? T_NETHER : T_NBRICK)),
  alcoveBase: (leg) => leg.y0 - 1, alcoveTile: T_NBRICK, passFloor: T_NETHER,
  prof: P([0.120, 0.046, 0.022], [0.085, 0.024, 0.010], 0.034, 1.25, 1.0, 0.55), dress: DRESS.deep });
// The last leg: the Krypt is still being dug. Raw rock, scaffolds, and the tunnel simply ends.
def("frontier", { style: W.mine, hw: [3, 3], ht: [4, 4], pre: [3, 3], post: [14, 14], m: [2, 2], branch: [0, 0], turn: 0,
  floor: ({ hv }) => (hv < 500 ? T_GRAVEL_FLOOR : hv < 800 ? T_DIRT : T_COBBLE),
  prof: P([0.075, 0.068, 0.070], [0.038, 0.034, 0.036], 0.042, 1.18, 0.9, 0.30),
  dress: (c) => {
    const { leg, L, torchAt, W3, decor, y0, hw, lo, hi, rowsFree, rnd, wallCell } = c;
    for (let lv = lo; lv < hi + 8; lv += 5) for (const sd of [-1, 1]) if (rowsFree(sd, lv)) torchAt(leg, wallCell(sd), lv, y0 + 2, -sd, { I: 2.6 });
    for (let q = 0; q < 6; q++) { const lv = hi + 1 + q * 2.2, sd = q % 2 ? 1 : -1; const [x, y, z] = W3(leg, sd * 1.6, lv, y0); decor({ t: "rubble", x, y, z, s: 0.35 + rnd(q, 2) * 0.35, ry: q }); }
    for (let lv = hi + 2; lv < leg.end - 3; lv += 4) { for (const sd of [-1, 1]) for (let j = y0; j <= y0 + 2; j++) L(leg, sd > 0 ? hw - 1 : -hw, lv, j, B.T_LOG); for (let lu = -hw; lu < hw; lu++) L(leg, lu, lv, y0 + 3, B.T_PLANK); }
  } });
applyArch();
