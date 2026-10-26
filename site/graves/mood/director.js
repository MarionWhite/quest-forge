// The mood director: pure timing, no DOM, so a simulation can run it in node (mood/sim.mjs).
// Fed once per frame-ish tick with the seconds the visitor has really walked. Rules (docs/design/site/krypt-mood.md):
//   - one event every 25 to 60 s of active walking at the top, a little tighter with depth
//   - the same kind never twice in a row; the same family is made less likely
//   - nothing while an event or a scare is on, and nothing for 20 s of walking after a scare
//   - close calls and the big mobs only from the deeper strata
export const CFG = { GAP_MIN: 25, GAP_MAX: 60, DEEP_TIGHTEN: 0.3, FIRST_MIN: 18, FIRST_MAX: 40, AFTER_SCARE: 20, RETRY: 5 };

// fam: grouping for "not the same thing twice"; min: depth from which it can happen; w: weight;
// light / visual: needs the screen (off under reduced motion); sound: audio only.
export const KINDS = {
  far_groan:      { fam: "far",     min: 0.00, w: 3.0, label: "Distant zombie groan",      sound: true },
  far_rattle:     { fam: "far",     min: 0.08, w: 2.6, label: "Distant skeleton rattle",   sound: true },
  far_hiss:       { fam: "far",     min: 0.18, w: 2.0, label: "Distant spider hiss",       sound: true },
  far_vwoop:      { fam: "far",     min: 0.28, w: 1.8, label: "Distant enderman vwoop",    sound: true },
  far_cry:        { fam: "far",     min: 0.55, w: 2.4, label: "Distant ghast cry",         sound: true },
  scamper:        { fam: "scamper", min: 0.03, w: 3.0, label: "Scampering behind the wall", sound: true },
  scamper_stop:   { fam: "scamper", min: 0.25, w: 1.2, label: "Scampering that stops beside you", sound: true },
  light_sputter:  { fam: "light",   min: 0.00, w: 2.6, label: "Torch ahead sputters",      light: true },
  light_out:      { fam: "light",   min: 0.12, w: 1.6, label: "Torch goes out as you near", light: true },
  light_pulse:    { fam: "light",   min: 0.20, w: 1.2, label: "All lights pulse dim",      light: true },
  light_cascade:  { fam: "light",   min: 0.40, w: 1.0, label: "Flicker runs toward you",   light: true },
  peek_zombie:    { fam: "peek",    min: 0.00, w: 2.2, label: "Zombie peeks round a corner", visual: true },
  peek_skeleton:  { fam: "peek",    min: 0.08, w: 2.0, label: "Skeleton peeks",            visual: true },
  peek_creeper:   { fam: "peek",    min: 0.18, w: 1.8, label: "Creeper peeks",             visual: true },
  peek_witch:     { fam: "peek",    min: 0.35, w: 1.2, label: "Witch peeks",               visual: true },
  peek_enderman:  { fam: "peek",    min: 0.45, w: 1.4, label: "Enderman, top of a doorway", visual: true },
  eyes_spider:    { fam: "eyes",    min: 0.12, w: 1.8, label: "Spider eyes in a side passage", visual: true },
  still_creeper:  { fam: "still",   min: 0.28, w: 1.2, label: "A creeper standing still",  visual: true },
  breath:         { fam: "close",   min: 0.50, w: 1.4, label: "Breathing right behind you", sound: true },
  scrape:         { fam: "close",   min: 0.50, w: 1.4, label: "A scrape along the wall",   sound: true }
};

export function createMoodDirector({ rng = Math.random, reduced = false, cfg = CFG } = {}) {
  const d = { cfg, next: null, last: null, lastFam: null, lastScare: null, count: 0, log: [] };
  const span = (a, b) => a + rng() * (b - a);
  d.scared = (acc) => { d.lastScare = acc; if (d.next != null) d.next = Math.max(d.next, acc + cfg.AFTER_SCARE + span(4, 14)); };
  // acc: active walking seconds; depth 0..1; st: { busy, feasible(kind) -> bool }. Returns a kind or null.
  d.tick = function (acc, depth = 0, st = {}) {
    if (d.next == null) d.next = acc + span(cfg.FIRST_MIN, cfg.FIRST_MAX);
    if (acc < d.next) return null;
    if (st.busy) return null;
    if (d.lastScare != null && acc - d.lastScare < cfg.AFTER_SCARE) { d.next = d.lastScare + cfg.AFTER_SCARE + span(2, 8); return null; }
    const pool = [];
    let total = 0;
    for (const [k, v] of Object.entries(KINDS)) {
      if (k === d.last || depth < v.min) continue;
      if (reduced && (v.light || v.visual)) continue;
      if (st.feasible && !st.feasible(k)) continue;
      const w = v.w * (v.fam === d.lastFam ? 0.35 : 1);
      pool.push([k, w]); total += w;
    }
    if (!pool.length) { d.next = acc + cfg.RETRY; return null; }
    let r = rng() * total, pick = pool[0][0];
    for (const [k, w] of pool) { r -= w; if (r <= 0) { pick = k; break; } }
    d.last = pick; d.lastFam = KINDS[pick].fam; d.count++;
    d.next = acc + span(cfg.GAP_MIN, cfg.GAP_MAX) * (1 - cfg.DEEP_TIGHTEN * Math.max(0, Math.min(1, depth)));
    d.log.push([acc, pick]);
    return pick;
  };
  return d;
}
