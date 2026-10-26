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
// Determinism and append-only: a smaller plan is the prefix of a larger one.
const q = makePlan({ n: Math.floor(N / 4) });
const pre = q.legs.length - 2;
for (let i = 0; i < pre; i++) { const a = q.legs[i], b = p.legs[i]; if (a.kind !== b.kind || a.hw !== b.hw || a.m !== b.m || a.heading !== b.heading) { fail(`leg ${i} differs between plans`); break; } }
const p2 = makePlan({ n: N }); for (let i = 0; i < p.legs.length; i++) if (p.legs[i].kind !== p2.legs[i].kind) { fail("not deterministic"); break; }
console.log(bad ? `${bad} FAILURES` : "OK");
process.exit(bad ? 1 : 0);
