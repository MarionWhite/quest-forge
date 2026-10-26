// node site/graves/mood/sim.mjs [minutes] [seed]: 30 minutes of walking through the mood director, with fake scares, a timeline out.
import { createMoodDirector, KINDS } from "./director.js";
const minutes = Number(process.argv[2] || 30), seed0 = Number(process.argv[3] || 7);
let a = seed0 >>> 0;
const rng = () => { a |= 0; a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
const d = createMoodDirector({ rng });
const total = minutes * 60;
let busyUntil = 0, scareAt = [], events = [], violations = [];
const nextScare = () => 150 + rng() * 240;
let scareNext = nextScare();
for (let t = 0; t < total; t += 0.25) {
  const depth = Math.min(1, t / total);
  if (t >= scareNext) {      // a scare: the walk is held, so no walking time passes; the director is told
    scareAt.push(t); d.scared(t); scareNext = t + nextScare(); busyUntil = Math.max(busyUntil, t);
  }
  const k = d.tick(t, depth, { busy: t < busyUntil, feasible: (kk) => !(KINDS[kk].visual && rng() < 0.15) });
  if (k) {
    const dur = KINDS[k].light ? 3 + rng() * 5 : KINDS[k].visual ? 4 + rng() * 6 : 2 + rng() * 5;
    busyUntil = t + dur; events.push([t, k, dur]);
  }
}
const mmss = (s) => `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
let prevK = null, prevEnd = 0;
for (const [t, k, dur] of events) {
  if (k === prevK) violations.push(`${mmss(t)} repeats ${k}`);
  for (const s of scareAt) if (t >= s && t - s < 20) violations.push(`${mmss(t)} ${k} only ${(t - s).toFixed(1)}s after a scare`);
  if (t < prevEnd) violations.push(`${mmss(t)} overlaps the previous event`);
  prevK = k; prevEnd = t + dur;
}
const merged = [...events.map(([t, k]) => [t, k]), ...scareAt.map((t) => [t, "** SCARE **"])].sort((x, y) => x[0] - y[0]);
console.log(`seed ${seed0}: ${events.length} events in ${minutes} min (${(total / events.length).toFixed(0)} s apart), ${scareAt.length} scares`);
for (const [t, k] of merged) console.log(mmss(t), k);
const gaps = events.slice(1).map((e, i) => e[0] - events[i][0]);
console.log(`gap min ${Math.min(...gaps).toFixed(0)} s, max ${Math.max(...gaps).toFixed(0)} s, mean ${(gaps.reduce((x, y) => x + y, 0) / gaps.length).toFixed(0)} s`);
const byKind = {}; for (const [, k] of events) byKind[k] = (byKind[k] || 0) + 1;
console.log(JSON.stringify(byKind));
console.log(violations.length ? "VIOLATIONS:\n" + violations.join("\n") : "rules: no repeats, no overlaps, 20 s after every scare clear");
