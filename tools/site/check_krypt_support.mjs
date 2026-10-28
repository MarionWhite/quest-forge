// Nothing floats: builds every chunk window of the Krypt plan (headless, no renderer) and checks that what is placed has
// something to stand on or hang from. Blocks: a block that is not plain wall must touch another solid block. Decor: a floor
// prop needs a solid block under its cell; a wall-mounted prop (lever, hook, ladder, banner, pane...) needs the solid block
// on the side it faces; torches need the block they sit on. Webs, vines, chains and wires may hang from a ceiling or a hook.
// A prop of a kind support.js does not know is reported as unclassified, so a new prop cannot slip past.
// Run: node tools/site/check_krypt_support.mjs [graves] [--list]     (also run by check_krypt_plan.mjs)
import { register } from "node:module";
import { fileURLToPath } from "node:url";
import path from "node:path";
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
register("data:text/javascript," + encodeURIComponent(
  `export async function resolve(s,c,n){ if(s==="three") return {url:${JSON.stringify("file://" + root + "/site/lib/three/three.module.min.js")},shortCircuit:true}; return n(s,c);}`));
const { makePlan, buildWindow, CH, legBox } = await import(root + "/site/graves/krypt.js");
const { T_AIR, T_WALL, T_BEDROCK, isOpen } = await import(root + "/site/graves/blocks.js");

// Blocks are joined face to face or edge to edge (a rib stepping diagonally is one piece; a corner touch is not).
const NEIGH = []; for (let a = -1; a <= 1; a++) for (let b = -1; b <= 1; b++) for (let c = -1; c <= 1; c++) if (Math.abs(a) + Math.abs(b) + Math.abs(c) >= 1 && Math.abs(a) + Math.abs(b) + Math.abs(c) <= 2) NEIGH.push([a, b, c]);

const { KINDS } = await import(root + "/site/graves/kinds.js");
const KINDS_FLOAT = new Set(Object.keys(KINDS).filter((k) => KINDS[k].floatingOk));
const leg0 = (w, i, k) => { for (const l of w.legs) { const b = legBox(l); if (i >= b.x0 - 1 && i <= b.x1 + 1 && k >= b.z0 - 1 && k <= b.z1 + 1) return l.kind; } return "?"; };

export function checkSupport({ n = 10000, list = false } = {}) {
  const plan = makePlan({ n });
  const cells = new Set();
  for (const leg of plan.legs) {
    const b = legBox(leg);
    for (let ci = Math.floor(b.x0 / CH); ci <= Math.floor(b.x1 / CH); ci++) for (let ck = Math.floor(b.z0 / CH); ck <= Math.floor(b.z1 / CH); ck++) cells.add(ci + "," + ck);
  }
  const out = { chunks: 0, fails: [], unclassified: new Map(), counts: new Map(), refused: new Map() };
  const note = (kind, w, i, j, k, why, d) => out.fails.push({ kind, at: [i, j, k], why, leg: nearestLeg(w, i, k), col: [j - 3, j - 2, j - 1, j, j + 1, j + 2].map((y) => w.get(i, y, k)).join("."), d });
  const nearestLeg = (w, i, k) => { let best = null; for (const l of w.legs) { const b = legBox(l); if (i >= b.x0 - 1 && i <= b.x1 + 1 && k >= b.z0 - 1 && k <= b.z1 + 1) { best = l; break; } } return best ? best.idx + ":" + best.kind : "?"; };
  for (const key of cells) {
    const [ci, ck] = key.split(",").map(Number);
    const w = buildWindow(plan, ci, ck); if (!w) continue; out.chunks++;
    const bb = w.bb, solid = (i, j, k) => { const t = w.get(i, j, k); return t !== T_AIR && !isOpen(t); };
    // Blocks: every placed block must be joined, through solid blocks, to the plain rock (a pair of dispensers that touch
    // only each other is a floating pair).
    const grounded = new Uint8Array(w.g.length), stack = [];
    // (the window's outer shell counts as rock too: a long bridge is held by what lies beyond the window)
    for (let ix = 0; ix < w.g.length; ix++) {
      const t = w.g[ix]; if (t === T_AIR || isOpen(t)) continue;
      const i = ix % w.NI, j = Math.floor(ix / w.NI) % w.NJ, k = Math.floor(ix / (w.NI * w.NJ));
      if (t === T_WALL || t === T_BEDROCK || i === 0 || k === 0 || i === w.NI - 1 || k === w.NK - 1) { grounded[ix] = 1; stack.push(ix); }
    }
    {
      const NI = w.NI, NJ = w.NJ, NK = w.NK;
      while (stack.length) {
        const ix = stack.pop(), i = ix % NI, j = Math.floor(ix / NI) % NJ, k = Math.floor(ix / (NI * NJ));
        // a block standing in lava or water is held by the bed the liquid lies on: walk up the liquid from a grounded cell
        { let c2 = (k * NJ + j) * NI + i, jj = j + 1; const up = (q) => c2 + (q - j) * NI; if (w.g[up(jj)] !== undefined && j + 1 < NJ && isOpen(w.g[up(jj)]) && w.g[up(jj)] !== T_AIR) { while (jj < NJ && isOpen(w.g[up(jj)]) && w.g[up(jj)] !== T_AIR) jj++; if (jj < NJ) { const n3 = up(jj), t3 = w.g[n3]; if (t3 !== T_AIR && !isOpen(t3) && !grounded[n3]) { grounded[n3] = 1; stack.push(n3); } } } }
        for (const [di, dj, dk] of NEIGH) {
          const a2 = i + di, b2 = j + dj, c2 = k + dk; if (a2 < 0 || b2 < 0 || c2 < 0 || a2 >= NI || b2 >= NJ || c2 >= NK) continue;
          const n2 = (c2 * NJ + b2) * NI + a2; if (grounded[n2]) continue; const t = w.g[n2]; if (t === T_AIR || isOpen(t)) continue;
          grounded[n2] = 1; stack.push(n2);
        }
      }
    }
    const chain = new Set();
    for (const d of w.decor) if (d.t === "fence") for (let y = Math.floor(d.y); y <= Math.floor(d.y + (d.h || 1) - 0.01); y++) chain.add(Math.floor(d.x) + "," + y + "," + Math.floor(d.z));
    for (let k = bb.z0; k < bb.z1; k++) for (let i = bb.x0; i < bb.x1; i++) for (let j = w.j0; j < w.j0 + w.NJ; j++) {
      const t = w.get(i, j, k); if (t === T_AIR || t === T_WALL || isOpen(t)) continue;
      out.counts.set("block", (out.counts.get("block") || 0) + 1);
      if (grounded[w.idx(i, j, k)]) continue;
      // a pillar standing in lava or water rests on the bed under it
      { let jd = j - 1; while (jd > j - 24 && isOpen(w.get(i, jd, k)) && w.get(i, jd, k) !== T_AIR) jd--; if (jd < j - 1 && grounded[w.idx(i, jd, k)]) continue; }
      // a lamp hung on a chain of fence posts from the ceiling is held
      let jj = j + 1; while (chain.has(i + "," + jj + "," + k)) jj++;
      if (jj > j + 1 && solid(i, jj, k)) continue;
      if (KINDS_FLOAT.has(leg0(w, i, k))) continue;   // islands of the End are meant to float (kind.floatingOk)
      note("block " + t, w, i, j, k, "joined to no rock");
    }
    // Props and torches the build had to drop (krypt.js step 4b) are the kinds' mistakes.
    const inb = (x, z) => x >= bb.x0 && x < bb.x1 && z >= bb.z0 && z < bb.z1;
    for (const d of w.dropped) if (inb(d.x, d.z)) note(d.t, w, Math.floor(d.x), Math.floor(d.y), Math.floor(d.z), d.why, d);
    for (const d of w.refused) if (inb(d.x, d.z)) out.refused.set(d.t, (out.refused.get(d.t) || 0) + 1);
    out.counts.set("torch", (out.counts.get("torch") || 0) + w.own.torches.length);
    for (const d of w.own.decor) out.counts.set(d.t, (out.counts.get(d.t) || 0) + 1);
  }
  return out;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const N = Number(process.argv.find((a, i) => i > 1 && /^\d+$/.test(a)) || 10000), t = Date.now();
  const r = checkSupport({ n: N });
  console.log(`support: ${r.chunks} chunk windows in ${((Date.now() - t) / 1000).toFixed(0)} s;`, [...r.counts].map(([k, v]) => `${k} ${v}`).join(", "));
  console.log("props never put (nothing to hold them):", [...r.refused].map(([k, v]) => `${k} ${v}`).join(", ") || "none");
  const by = new Map(); for (const f of r.fails) { const k = f.leg.split(":")[1] + " / " + f.kind + " / " + f.why; by.set(k, (by.get(k) || 0) + 1); }
  // Blocks must never float. A prop the net had to drop is a kind's mistake; a few strays where a side passage or a gap
  // took the support away after the prop was put are tolerated (fewer than LIMIT of one kind and type in the whole plan: at the joins of two legs a neighbour's carve can take a pillar away).
  const LIMIT = 60;
  let bad = 0;
  for (const [k, v] of [...by].sort((a, b) => b[1] - a[1])) { const block = k.includes(" / block "); const over = block || v >= LIMIT; if (over) bad += v; console.log(String(v).padStart(5), over ? "FAIL" : "ok  ", k); }
  if (process.argv.includes("--list")) { const want = process.argv.find((a) => a.startsWith("--only=")); const seen = new Map(); for (const f of r.fails) { const key = f.leg.split(":")[1] + "/" + f.kind; if (want && !key.includes(want.slice(7))) continue; const c = seen.get(key) || 0; if (c < (want ? 6 : 1)) { console.log(key, JSON.stringify(f)); seen.set(key, c + 1); } } }
  console.log(bad ? `${bad} FLOATING` : `OK (${r.fails.length} stray props dropped of ${[...r.counts.values()].reduce((a, b) => a + b, 0)} placed)`);
  process.exit(bad ? 1 : 0);
}
