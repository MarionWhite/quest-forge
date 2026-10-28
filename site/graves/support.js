// "Nothing floats": what a placed prop needs to stand on or hang from. Used twice: buildWindow (krypt.js) drops a prop that
// has no support, as a safety net, and tools/site/check_krypt_support.mjs fails on every prop the net had to drop, so the
// kinds are fixed at their cause. S gives solid(i, j, k) and liquid(i, j, k) for the window's grid.
//   floor props      a solid block under the cell (or, for a pile of skulls or bones, under the pile's base)
//   wall props       a solid block on the side they face: the plane lies on a cell boundary or within 0.16 of one
//   posts            a fence post stands where it is put (not snapped): solid under any of the cells it touches
//   hanging props    webs, vines, wires: any solid block in the cell's neighbourhood or up to three above it
//   water props      a lily pad or a boat needs water under it
export const FLOOR_PROPS = new Set(["chest", "cauldron", "anvil", "brewing", "enchanting", "rubble", "slab", "bone", "skull", "rail", "cart", "plate", "carpet",
  "cube", "bed", "cross", "mob", "fire", "spawner", "dust", "idoor", "wdoor", "nfence", "frame", "stair", "ice", "pot", "portal", "wire_post", "beam_post"]);
export const WALL_PROPS = new Set(["lever", "hook", "banner", "pane", "sign", "painting"]);
// Snapped to a cell, held by whichever side wall touches it: pistons set in a wall cell, ladders, item frames, hung sheets.
export const NEIGHBOR_PROPS = new Set(["piston", "ladder", "map", "sheet"]);
export const HANGING = new Set(["web", "vine", "wire", "chain"]);
export const WATER_PROPS = new Set(["lily", "boat"]);
const SELF = new Set(["wire", "beam", "bars", "fence"]);   // handled below by their own rules

const NEAR = [[-1, 0], [1, 0], [0, -1], [0, 1]];

// Returns null when the prop is held, or a short reason.
export function decorProblem(d, S) {
  const t = d.t, i = Math.floor(d.x), k = Math.floor(d.z), j = Math.floor(d.y + 0.001);
  const raise = d.y - j;
  if (HANGING.has(t)) {
    if (t === "wire") return null;                       // a tripwire hangs between its hooks (checked as hooks)
    for (let dj = -1; dj <= 3; dj++) for (let di = -1; di <= 1; di++) for (let dk = -1; dk <= 1; dk++) if ((dj <= 1 || (!di && !dk)) && S.solid(i + di, j + dj, k + dk)) return null;
    return "hangs from nothing";
  }
  if (WATER_PROPS.has(t)) {
    // the water of a flooded hall is a plane over a lowered floor: it floats on air above a solid bed up to three down
    if (S.water && S.water(d.x, d.y, d.z)) return null;
    const jj = Math.floor(d.y - 0.05);
    for (let q = 0; q < 4; q++) if (S.liquid(i, jj - q, k) || S.solid(i, jj - q, k)) return null;
    return "no water under it";
  }
  if (t === "fence") {
    // (a rail lying half a block up between two posts is held by the stone under them: its base is tested half a block lower)
    const e = 0.12, rail = (d.h || 1) < 0.5 && d.y - j > 0.3, jb = Math.floor(d.y - 0.05 - (rail ? 0.5 : 0));
    for (const dx of [-e, e]) for (const dz of [-e, e]) if (S.solid(Math.floor(d.x + dx), jb, Math.floor(d.z + dz))) return null;
    // a chandelier chain: hangs from a block above its top
    const top = Math.floor(d.y + (d.h || 1) - 0.01);
    if (S.solid(i, top + 1, k)) return null;
    return "nothing under it";
  }
  if (t === "bars") {
    const h = d.h || 1, w = d.w || 1, r = w / 2 + 0.3, j0 = Math.floor(d.y - h / 2 + 0.01), j1 = Math.floor(d.y + h / 2 - 0.01);
    for (const dx of [-0.12, 0.12]) for (const dz of [-0.12, 0.12]) if (S.solid(Math.floor(d.x + dx), j0 - 1, Math.floor(d.z + dz)) || S.solid(Math.floor(d.x + dx), j1 + 1, Math.floor(d.z + dz))) return null;
    for (let jj = j0; jj <= j1; jj++) for (const [dx, dz] of [[r, 0], [-r, 0], [0, r], [0, -r]]) if (S.solid(Math.floor(d.x + dx), jj, Math.floor(d.z + dz))) return null;
    return "bars held by nothing";
  }
  if (t === "beam") {
    // a beam lies slanted or level between supports: any solid block near either end (len along its axis)
    const len = d.len || 1, c = Math.cos(d.ry || 0), s = Math.sin(d.ry || 0);
    for (const sgn of [-1, 1]) { const x = d.x + sgn * c * len / 2, z = d.z - sgn * s * len / 2; for (let dj = -2; dj <= 2; dj++) for (const [dx, dz] of [[0, 0], ...NEAR]) if (S.solid(Math.floor(x) + dx, j + dj, Math.floor(z) + dz)) return null; }
    return "beam held by nothing";
  }
  if (NEIGHBOR_PROPS.has(t) && !d.flat) { for (const [dx, dz] of NEAR) if (S.solid(i + dx, j, k + dz)) return null; return "no wall behind it"; }
  if (WALL_PROPS.has(t) || (NEIGHBOR_PROPS.has(t) && d.flat)) {
    const e = 0.16;
    if (d.t === "pane" && d.flat) return S.solid(i, Math.floor(d.y + 0.05), k) || S.solid(i, Math.floor(d.y - 0.05), k) ? null : "skylight under open air";
    if (d.flat) return S.solid(i, Math.floor(d.y - 0.05), k) || (S.post && S.post(d.x, d.y, d.z)) ? null : "nothing under it";
    for (const [dx, dz] of [[e, 0], [-e, 0], [0, e], [0, -e]]) if (S.solid(Math.floor(d.x + dx), j, Math.floor(d.z + dz))) {
      const ci = Math.floor(d.x + dx), ck = Math.floor(d.z + dz);
      if (ci !== i || ck !== k || S.solid(i, j, k)) return null;
    }
    return "no wall behind it";
  }
  if (FLOOR_PROPS.has(t) || t === "wire_post") {
    const jb = Math.floor(d.y - 0.05);
    if (S.solid(i, jb, k)) return null;
    if (S.post && S.post(d.x, d.y, d.z)) return null;                         // a table top on its fence posts
    if (raise >= 0.2 && raise <= 0.6 && S.solid(i, j - 1, k)) return null;   // a pile's upper layer
    return "nothing under it";
  }
  return SELF.has(t) ? null : "unclassified";
}

// The solid / liquid / water / post tests of one window's grid (a = the window of krypt.js buildWindow), for the net at the
// end of the dressing and for the kinds' own put() (a prop with nothing to hold it is not put). Posts are read from a.decor
// on demand (the last 80 entries: a table's plates and maps come right after its posts).
export function makeSupport(a, T_WATER, T_LAVA) {
  return {
    solid: a.solid, liquid: (i, j, k) => { const t = a.get(i, j, k); return t === T_WATER || t === T_LAVA; },
    water: (x, y, z) => a.waterRects.some((r) => x >= r.x0 && x <= r.x1 && z >= r.z0 && z <= r.z1 && y > r.y - 0.9 && y < r.y + 0.9),
    // a lamp hung on a chain of fence posts: a fence decor of that cell covering the cell above j and reaching a ceiling
    chain: (i, j, k) => { for (let n = a.decor.length - 1; n >= 0; n--) { const d = a.decor[n]; if (d.t === "fence" && Math.floor(d.x) === i && Math.floor(d.z) === k && Math.floor(d.y) <= j + 1 && Math.floor(d.y + (d.h || 1) - 0.01) >= j + 1 && a.solid(i, Math.floor(d.y + (d.h || 1) - 0.01) + 1, k)) return true; } return false; },
    post: (x, y, z) => {
      const ci = Math.floor(x), ck = Math.floor(z);
      for (let n = a.decor.length - 1, m = 0; n >= 0 && m < 80; n--, m++) { const d = a.decor[n]; if (d.t === "fence" && Math.floor(d.x) === ci && Math.floor(d.z) === ck && d.y <= y + 0.01 && d.y + (d.h || 1) >= y - 0.08 && d.y + (d.h || 1) <= y + 0.2) return true; }
      return false;
    }
  };
}
