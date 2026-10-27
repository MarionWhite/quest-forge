// A small library of dressing features for the Krypt's kinds: columns, ribs, arches, bands, pools, channels, alcove styles,
// partitions and the like, written against the leg-local context of kindreg.js (c). A kind's dresser calls them with options,
// so most kinds are a palette, a rhythm and a signature rather than their own loops.
import * as B from "./blocks.js";
const { T_AIR, T_LAVA, T_WATER, T_OBS, T_GRAVEL_FLOOR } = B;

// Rows a side's alcoves claim: the pocket and its two pillar rows (lvc - 2 .. lvc + 2), and a side passage's mouth.
export function clearer(c) {
  const rows = { 1: [], "-1": [] };
  for (const s of c.leg.slots) rows[s.side].push(s.lvc);
  const pas = c.leg.passages.filter((p) => p.ok);
  return (sd, lv, pad = 0) => {
    for (const q of rows[sd]) if (Math.abs(lv - q) <= 2 + pad) return false;
    for (const p of pas) if (p.side === sd && lv >= p.lv - 1 - pad && lv <= p.lv + (p.w || 2) + 1 + pad) return false;
    return true;
  };
}

// World rectangle of a leg-local box (lu0..lu1 inclusive cells, lv0..lv1 inclusive rows).
export function rectOf(c, lu0, lu1, lv0, lv1) {
  const [xa, , za] = c.W3(c.leg, lu0, lv0, 0), [xb, , zb] = c.W3(c.leg, lu1 + 1, lv1 + 1, 0);
  return { x0: Math.min(xa, xb), x1: Math.max(xa, xb), z0: Math.min(za, zb), z1: Math.max(za, zb) };
}

// A pool sunk into the floor: the floor block goes, the liquid sits one block down. liquid: "water" | "lava".
export function pool(c, o) {
  const { lu0, lu1, lv0, lv1, liquid = "water", glow = true } = o, y0 = c.y0;
  const t = liquid === "lava" ? T_LAVA : T_WATER, base = liquid === "lava" ? T_OBS : T_GRAVEL_FLOOR;
  for (let lv = lv0; lv <= lv1; lv++) for (let lu = lu0; lu <= lu1; lu++) { c.L(c.leg, lu, lv, y0 - 1, T_AIR); c.L(c.leg, lu, lv, y0 - 2, t); c.L(c.leg, lu, lv, y0 - 3, base); }
  const r = rectOf(c, lu0, lu1, lv0, lv1);
  if (liquid === "lava") {
    c.a.lavaRects.push({ ...r, y: y0 - 1.13 });
    if (glow) for (let lv = lv0; lv <= lv1; lv += 3) for (let lu = lu0; lu <= lu1; lu += 3) { c.src(lu + 0.5, lv + 0.5, y0 - 0.5, [1.0, 0.36, 0.08], 5, 10, { lava: true, dyn: true }); if ((lu + lv) % 2 === 0) c.emit("lava", lu + 0.5, lv + 0.5, y0 - 1.1); }
  } else c.a.waterRects.push({ ...r, y: y0 - 1.25 });
  return r;
}

// Bars across an alcove's mouth, with a one block gap (a cell door) when gap is set.
function barAlcove(c, s, gap) {
  const sd = s.side, a = sd * (c.hw + 0.02);
  if (gap) { c.put("bars", a, s.lvc - 0.5 + 0.0, c.y0 + 1.5, { ry: c.acrossRy, w: 1, h: 3 }); c.put("bars", a, s.lvc + 1.5, c.y0 + 1.5, { ry: c.acrossRy, w: 1, h: 3 }); }
  else c.put("bars", a, s.lvc + 0.5, c.y0 + 1.5, { ry: c.acrossRy, w: 3, h: 3 });
}

export const FEATURES = {
  // Columns along the walls on rows free of alcoves. o: every, off, tile, h, sides, torch (y offset), I, cap, inset.
  pillars(c, o = {}) {
    const clear = c.clr || (c.clr = clearer(c)), { every = 6, off = 0, tile = B.T_CARVED, h = c.ht - 1, sides = [-1, 1], torch = 0, I = 2.8, cap = null, inset = 0, base = null } = o;
    for (let lv = c.lo + off; lv < c.hi; lv += every) for (const sd of sides) {
      if (!clear(sd, lv, 0)) continue;
      const lu = c.edgeCell(sd) - sd * inset;
      c.col(lu, lv, c.y0, c.y0 + h - 1, tile);
      if (base) c.L(c.leg, lu, lv, c.y0, base);
      if (cap) c.L(c.leg, lu, lv, c.y0 + h, cap);
      if (torch) c.torchAt(c.leg, lu, lv, c.y0 + torch, -sd, { I, ...(o.color ? { c: o.color } : {}) });
    }
  },
  // Cross beams under the ceiling, a row of tiles across the whole hall. o: every, off, tile, y (offset below the roof), w.
  ribs(c, o = {}) {
    const { every = 4, off = 1, tile = B.T_PLANK, y = 1, w = 1, edge = true } = o;
    for (let lv = c.lo + off; lv < c.hi + 2; lv += every) for (let q = 0; q < w; q++) for (let lu = -c.hw; lu < c.hw; lu++) {
      if (!edge && Math.abs(lu + 0.5) > c.hw - 1) continue;
      if (c.LG(c.leg, lu, lv + q, c.y0 + c.ht - y) === T_AIR) c.L(c.leg, lu, lv + q, c.y0 + c.ht - y, tile);
    }
  },
  // Arches over the walk: columns at both edges and a lintel across, with a keystone at the centre. Placed on the alcoves' own pillar rows.
  arches(c, o = {}) {
    const { tile = B.T_BRICK, key = B.T_CARVED, rise = 1, torch = 0, I = 2.7, rows = null } = o, y0 = c.y0, top = y0 + c.ht - rise;
    const list = rows || c.leg.slots.map((s) => s.lvc + 2).concat(c.leg.slots.length ? [c.leg.slots[0].lvc - 2] : []);
    for (const lv of list) {
      for (const sd of [-1, 1]) { const lu = c.edgeCell(sd); for (let j = y0; j < top; j++) if (c.LG(c.leg, lu, lv, j) === T_AIR) c.L(c.leg, lu, lv, j, tile); if (torch) c.torchAt(c.leg, lu, lv, y0 + torch, -sd, { I }); }
      for (let lu = -c.hw; lu < c.hw; lu++) if (c.LG(c.leg, lu, lv, top) === T_AIR) c.L(c.leg, lu, lv, top, (lu === -1 || lu === 0) ? key : tile);
    }
  },
  // A tile on the wall face between y j0 and j1 for the rows given (o.every / o.off): bands, friezes, inlays. sides default both.
  band(c, o = {}) {
    const { tile, j0 = 0, j1 = 0, every = 1, off = 0, sides = [-1, 1], from = c.lo, to = c.hi, mix = null } = o;
    for (let lv = from + off; lv < to; lv += every) for (const sd of sides) for (let j = c.y0 + j0; j <= c.y0 + j1; j++) {
      if (c.LG(c.leg, c.wallCell(sd), lv, j) === T_AIR) continue;
      c.L(c.leg, c.wallCell(sd), lv, j, mix ? mix(lv, j, sd) : tile);
    }
  },
  // A stripe in the floor: lanes lu0..lu1 across the whole length (or every n rows), tile or a function of (lu, lv).
  runner(c, o = {}) {
    const { lu0 = -1, lu1 = 0, tile, every = 1, from = c.leg.cs + 1, to = c.leg.ce - 1, fn = null } = o;
    for (let lv = from; lv < to; lv++) { if ((lv - from) % every) continue; for (let lu = lu0; lu <= lu1; lu++) c.L(c.leg, lu, lv, c.y0 - 1, fn ? fn(lu, lv) : tile); }
  },
  // Wall torches in a rhythm. o: every, off, I, y, color, sides.
  torches(c, o = {}) {
    const clear = c.clr || (c.clr = clearer(c)), { every = 6, off = 1, I = 2.8, y = 2, color = null, sides = [-1, 1] } = o;
    for (let lv = c.lo + off; lv < c.hi + (o.over || 0); lv += every) for (const sd of sides) if (clear(sd, lv, 0)) c.torchAt(c.leg, c.wallCell(sd), lv, c.y0 + y, -sd, { I, ...(color ? { c: color } : {}) });
  },
  // A lit block in the roof (glowstone, lamps) every n rows: o: every, off, tile, color, I, lu (list), y (below roof).
  roofLamps(c, o = {}) {
    const { every = 6, off = 2, tile = B.T_GLOW, color = [1.0, 0.82, 0.46], I = 3.0, R = 11, lus = [-1, 0], y = 1 } = o;
    for (let lv = c.lo + off; lv < c.hi; lv += every) for (const lu of lus) c.lamp(lu, lv, c.y0 + c.ht - y, tile, color, I, R);
  },
  // Cobwebs and vines and bones and rubble by count.
  webs(c, o = {}) { c.ceilWebs(o.n || 8, o.w || 1.6, o.salt || 40); },
  vines(c, o = {}) { c.vines(o.n || 10, o.salt || 50, o.h || 1.6); },
  bones(c, o = {}) { c.bones(o.n || 12, o.salt || 60, o.spread || 1.7); },
  rubble(c, o = {}) { c.rubble(o.n || 8, o.salt || 70); },
  // Alcove dressing, per slot. style: bars | cell | cap | banner | candle | none. o.tile for cap, o.color for banners, o.every to thin.
  alcoves(c, o = {}) {
    const { style = "none", tile = B.T_QUARTZ_C, pil = null, color = 3, every = 1, I = 2.4, flame = [1.0, 0.56, 0.24] } = o;
    c.leg.slots.forEach((s, i) => {
      if (i % every) return;
      const sd = s.side, p = c.edgeCell(sd), y0 = c.y0;
      if (style === "bars") barAlcove(c, s, false);
      else if (style === "cell") barAlcove(c, s, true);
      else if (style === "cap") {
        for (let lv = s.lvc - 2; lv <= s.lvc + 2; lv++) c.L(c.leg, p, lv, y0 + 3, tile);
        if (pil) for (const lv of [s.lvc - 2, s.lvc + 2]) for (let j = y0; j <= y0 + 2; j++) c.L(c.leg, p, lv, j, pil);
      } else if (style === "banner") {
        for (const q of [-1.6, 1.6]) c.put("banner", sd * (c.hw - 1 - 0.06), s.lvc + 0.5 + q, y0 + 2.0, { ry: c.acrossRy, w: 0.8, h: 2.1, color });
      }
      void I; void flame;
    });
  },
  // A partition across the hall every n rows with a two wide doorway (cells). o: every, off, tile, door (lu list), h (door height), arch tile.
  partitions(c, o = {}) {
    const clear = c.clr || (c.clr = clearer(c)), { every = 6, off = 2, tile = B.T_BRICK, doorLu = [-1, 0], dh = 3, lintel = null, thick = 1 } = o;
    for (let lv = c.lo + off; lv < c.hi - 1; lv += every) {
      if (!clear(-1, lv, 0) || !clear(1, lv, 0)) continue;
      for (let q = 0; q < thick; q++) for (let lu = -c.hw; lu < c.hw; lu++) for (let j = c.y0; j < c.y0 + c.ht; j++) {
        const door = doorLu.includes(lu) && j < c.y0 + dh;
        if (!door) c.L(c.leg, lu, lv + q, j, lintel && doorLu.includes(lu) ? lintel : tile);
      }
      if (o.torch) for (const lu of [doorLu[0] - 1, doorLu[doorLu.length - 1] + 1]) c.torchAtB(c.leg, lu, lv, c.y0 + 2, -1, { I: o.I || 2.6 });
    }
  }
};

// The rows midway between neighbouring alcoves of one side (and at the leg's ends): [sd, lv] pairs, for pillars and lamps.
export function between(c) {
  const out = [];
  for (const sd of [-1, 1]) {
    const rows = c.leg.slots.filter((s) => s.side === sd).map((s) => s.lvc);
    if (!rows.length) continue;
    for (let i = 0; i + 1 < rows.length; i++) out.push([sd, Math.round((rows[i] + rows[i + 1]) / 2)]);
    out.push([sd, rows[rows.length - 1] + Math.round((rows.length > 1 ? rows[1] - rows[0] : 8) / 2)]);
    out.push([sd, rows[0] - Math.round((rows.length > 1 ? rows[1] - rows[0] : 8) / 2)]);
  }
  return out;
}
// Columns (and their torches) in the gaps between alcoves on each side: the commonest rhythm of a hall.
FEATURES.between = (c, o = {}) => {
  const { tile = B.T_CARVED, h = c.ht - 1, torch = 0, I = 2.8, cap = null, color = null, inset = 0, base = null, w = 1 } = o;
  for (const [sd, lv] of between(c)) {
    if (lv < c.leg.cs + 1 || lv > c.hi + 1) continue;
    const lu = c.edgeCell(sd) - sd * inset;
    for (let q = 0; q < w; q++) {
      c.col(lu, lv + q, c.y0, c.y0 + h - 1, tile);
      if (base) c.L(c.leg, lu, lv + q, c.y0, base);
      if (cap) c.L(c.leg, lu, lv + q, c.y0 + h, cap);
    }
    if (torch) c.torchAt(c.leg, lu, lv, c.y0 + torch, -sd, { I, ...(color ? { c: color } : {}) });
  }
};

export function F(c, list) { for (const f of list) FEATURES[f[0]](c, f[1] || {}); }
