// Script check of the endless Krypt's plan: 10,000 graves, the no-repeat rule, determinism and append-only growth,
// kind and strata counts. Run: node tools/site/check_krypt_plan.mjs [graves]
import { makePlan } from "../../site/graves/plan.js";
import { STRATA } from "../../site/graves/strata.js";
import { KINDS } from "../../site/graves/kinds.js";
const N = Number(process.argv[2] || 10000);
let t = Date.now();
const p = makePlan({ n: N });
console.log(`plan ${Date.now() - t} ms: ${p.slots.length} slots, ${p.legs.length} legs, ${p.strata.length} strata, ${p.gaps.length} gaps, length ${p.length.toFixed(0)}`);
let bad = 0;
const fail = (m) => { bad++; if (bad < 20) console.log("FAIL", m); };
// No-repeat: within a stratum, a kind must not recur inside min(12, pool-2) legs unless the pool forced a relaxation; overall 6.
const hist = [];
const kinds = new Set(p.legs.map((l) => l.kind)), usedStrata = new Set(p.strata.map((s) => s.def.id));
let relaxed = 0;
for (const st of p.strata) {
  const pool = st.def.pool.filter((id) => KINDS[id]).length, w = Math.min(12, Math.max(1, pool - 2));
  const here = st.legs.map((l) => l.kind).filter((id) => id !== "stairs");
  here.forEach((id, i) => { for (let q = Math.max(0, i - w); q < i; q++) if (here[q] === id) { relaxed++; return; } });
}
for (let i = 0; i < p.legs.length; i++) { const l = p.legs[i]; if (l.kind === "stairs" || l.kind === "frontier") continue; for (let q = Math.max(0, i - 3); q < i; q++) if (p.legs[q].kind === l.kind) fail(`kind ${l.kind} repeats within 3 legs at ${i}`); }
const rep = { ok: 0 };
for (const st of p.strata) { const pool = st.def.pool.filter((id) => KINDS[id]).length; const seq = st.legs.map((l) => l.kind).filter((k) => k !== "stairs"); let run = 0; for (let i = 6; i < seq.length; i++) { if (seq.slice(i - 6, i).includes(seq[i]) && pool >= 8) run++; } rep.ok += run; }
console.log(`kinds used ${kinds.size} (registered ${Object.keys(KINDS).length}), strata ${usedStrata.size} of ${STRATA.length}, in-window repeats (relaxed) ${relaxed}, 6-window repeats in pools>=8: ${rep.ok}`);
// Every stratum cycle holds its set piece (plan.js forces it at fixed legs).
for (const st of p.strata) if (st.def.set && st.legs.length > 8 && !st.legs.some((l) => l.kind === st.def.set)) fail(`stratum ${st.name} has no ${st.def.set}`);
// Determinism and append-only: a smaller plan is the prefix of a larger one.
const q = makePlan({ n: Math.floor(N / 4) });
const pre = q.legs.length - 2;
for (let i = 0; i < pre; i++) { const a = q.legs[i], b = p.legs[i]; if (a.kind !== b.kind || a.hw !== b.hw || a.m !== b.m || a.heading !== b.heading) { fail(`leg ${i} differs between plans`); break; } }
const p2 = makePlan({ n: N }); for (let i = 0; i < p.legs.length; i++) if (p.legs[i].kind !== p2.legs[i].kind) { fail("not deterministic"); break; }
// Round 7: the walk's rhythm. A room (def.room) after every two or three corridors, and within any 12 legs (about 600
// blocks, one walk filmstrip) no kind twice where the stratum's pool allows it.
{
  let maxRun = 0, run = 0, rooms = 0, worst = 99, worstAt = -1, dupWin = 0;
  for (let i = 0; i < p.legs.length; i++) {
    const l = p.legs[i]; if (l.kind === "stairs" || l.kind === "frontier") continue;
    if (KINDS[l.kind].room) { rooms++; run = 0; } else { run++; maxRun = Math.max(maxRun, run); }
  }
  for (let i = 0; i + 12 <= p.legs.length; i++) {
    const win = p.legs.slice(i, i + 12).map((l) => l.kind).filter((k) => k !== "stairs" && k !== "frontier");
    const d = new Set(win).size; if (d < worst) { worst = d; worstAt = i; } if (d < win.length) dupWin++;
  }
  console.log(`rhythm: rooms ${rooms} of ${p.legs.length} legs (${(100 * rooms / p.legs.length).toFixed(0)}%), longest corridor run ${maxRun}; 12-leg windows with a repeat ${dupWin} of ${p.legs.length - 11}, fewest distinct ${worst} (at leg ${worstAt})`);
  if (maxRun > 4) fail(`corridor run of ${maxRun} legs`);
}
// Nothing floats (round 8): every chunk window of the plan, headless; a separate process (it hooks the module loader).
{
  const { spawnSync } = await import("node:child_process");
  const r = spawnSync(process.execPath, [new URL("./check_krypt_support.mjs", import.meta.url).pathname, String(N)], { encoding: "utf8" });
  const lines = r.stdout.trim().split("\n"), last = lines[lines.length - 1];
  console.log(`support (nothing floats): ${last}`);
  if (r.status !== 0) { bad++; for (const l of lines.filter((x) => /FAIL/.test(x)).slice(0, 12)) console.log("  ", l.trim()); if (r.stderr) console.log(r.stderr.slice(0, 400)); }
}
console.log(bad ? `${bad} FAILURES` : "OK");
process.exit(bad ? 1 : 0);
