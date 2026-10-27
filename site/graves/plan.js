// The plan of the endless Krypt: a deterministic chain of legs (segments), laid out from a seed and the slot index, and
// only ever appended to. Nothing here touches blocks: it gives each leg its kind, size, heading, place, stratum and
// slots, the bends with their gaps, the side passages, the walker's path (a polyline measured in blocks, d) and the
// lookups the world builder and the page need. The same seed and the same slot count always give the same plan, and a
// longer plan starts with the shorter one (a grave's place depends only on its index).
import { legMap, legLocal, legDir, turnOf, floorSmooth, SLOT_STEP, STAIR_LANDING, STAIR_LEN, STAIR_DROP, PASSAGE_LEN } from "./geom.js";
import { ih } from "./blocks.js";
import { KINDS } from "./kinds.js";
import { STRATA } from "./strata.js";
const SET_AT = [4, 22, 46, 70];
const CYCLE_ORD = ["first", "second", "third", "fourth", "fifth", "sixth", "seventh"];

export const SEED = 1707;
export const CORNER_R = 2.7;
const REACH_PAD = 6;                       // beyond hw + passage length: stone styling and torches
const fr = (seed, a, b = 0, c = 0) => (ih(a, b, c, seed) * 1000 + ih(a, b, c, seed + 977)) / 1e6;   // 0..1, finer than ih
const pickInt = (r, [lo, hi]) => lo + Math.min(hi - lo, Math.floor(r * (hi - lo + 1)));

export function makePlan({ n = 0, seed = SEED, minSlots = 60, runway = 36, force = null } = {}) {
  const want = Math.max(n + runway, minSlots);
  const legs = [], slots = [], corners = [], gaps = [], strata = [];
  const hist = [];                          // kind ids in order
  let gi = 0, prev = null, stratum = null;

  const openStratum = (index) => {
    const def = STRATA[index % STRATA.length], cycle = Math.floor(index / STRATA.length);
    const band = Math.max(40, Math.round(def.band * (1 + 0.06 * Math.sin(index * 2.1)) * (cycle ? 1 : 1)));
    stratum = { index, cycle, def, name: cycle ? def.name + ", " + (CYCLE_ORD[Math.min(cycle, CYCLE_ORD.length - 1)]) + " descent" : def.name, g0: gi, g1: gi + band, legs: [], d0: 0, d1: 0, id: def.id };
    strata.push(stratum);
  };

  // The kind of leg k: the no-repeat rule. Within the stratum a kind is skipped while it is among the last
  // min(12, pool - 2) legs, and overall while it is among the last 6, relaxed step by step if nothing is left.
  const chooseKind = (k) => {
    if (k === 0) return "crypt";
    const def = stratum.def;
    if (stratum.legs.length === 0 && stratum.index > 0) return def.entry || "stairs";
    if (def.set && KINDS[def.set] && SET_AT.includes(stratum.legs.length)) return def.set;
    const pool = def.pool.filter((id) => KINDS[id]);
    const here = stratum.legs.map((l) => l.kind).filter((id) => id !== "stairs" || def.entry);
    let wStr = Math.min(12, Math.max(1, pool.length - 2)), wAll = 6;
    for (let attempt = 0; attempt < 12; attempt++) {
      const banned = new Set(here.slice(-wStr)); for (const id of hist.slice(-wAll)) banned.add(id);
      let cand = pool.filter((id) => !banned.has(id));
      if (cand.length) {
        // The rhythm: a room after every two or three corridors, and never two rooms running, so the walk keeps opening up.
        const isRoom = (id) => !!KINDS[id].room;
        let since = 99; for (let q = here.length - 1; q >= 0; q--) if (isRoom(here[q])) { since = here.length - 1 - q; break; }
        const want = since === 0 ? false : since >= 2 + (fr(seed, k, 7, 5) < 0.5 ? 0 : 1) ? true : null;
        if (want !== null) { const c2 = cand.filter((id) => isRoom(id) === want); if (c2.length) cand = c2; }
        let tot = 0; const ws = cand.map((id) => { const since = (() => { for (let q = here.length - 1; q >= 0; q--) if (here[q] === id) return here.length - q; return 99; })(); const w = (KINDS[id].weight || 1) * (1 + Math.min(1.5, since / 14)); tot += w; return w; });
        let r = fr(seed, k, 1, 5) * tot;
        for (let q = 0; q < cand.length; q++) { r -= ws[q]; if (r <= 0) return cand[q]; }
        return cand[cand.length - 1];
      }
      if (wAll > 1) wAll--; else wStr = Math.max(0, wStr - 1);
    }
    return pool[Math.floor(fr(seed, k, 2, 5) * pool.length)];
  };

  let x = 0, runLen = 0;                    // x: where the next leg starts, for the drift rule; runLen: blocks since the last bend
  for (let k = 0, fin = false; !fin; k++) {
    if (!stratum || gi >= stratum.g1) openStratum(strata.length);
    fin = gi >= want && k >= 2;
    const kind = fin ? "frontier" : (force && force.length && k > 0 ? force[(k - 1) % force.length] : chooseKind(k));
    const KD = KINDS[kind];
    const rr = (s) => fr(seed, k, s, 9);
    const hw = pickInt(rr(1), KD.hw), ht = pickInt(rr(2), KD.ht), pre = pickInt(rr(3), KD.pre), post = pickInt(rr(4), KD.post);
    const step = Array.isArray(KD.step) ? pickInt(rr(5), KD.step) : (KD.step || SLOT_STEP);
    const m = KD.stairs ? 1 : (KD.fixed || pickInt(rr(6), KD.m));
    // The heading: N may bend to W or E; W and E always return to N. Drift toward x = 0 keeps the plan in a band.
    let h = "N", prevH = prev ? prev.h : "N";
    if (prev) {
      if (prevH !== "N") h = "N";
      else {
        const wantTurn = !fin && rr(7) < KD.turn;
        if (wantTurn) h = (x > 260 ? "W" : x < -260 ? "E" : (rr(8) < 0.5 ? "W" : "E"));
      }
    }
    const leg = {
      idx: k, kind, kd: KD, m, h, hw, ht, pre, post, step, branch: Math.min(KD.branch ? pickInt(rr(10), KD.branch) : 0, Math.max(0, m - 1)),
      stairs: !!KD.stairs, slots: [], passages: [], holesAt: [], style: KD.style, rid: 7 + k * 13, y0: 0, px: 0, pz: 0, cs: 0, b0: 0,
      stratum: stratum.index, st: stratum, variant: pickInt(rr(11), [0, 3]), damage: rr(12), seed: Math.floor(rr(13) * 100000),
      tint: [(rr(14) - 0.5) * 0.18, (rr(15) - 0.5) * 0.18, (rr(16) - 0.5) * 0.18]
    };
    if (prev) {
      leg.y0 = prev.yEnd;
      if (prev.h !== h) {
        // A bend: the previous leg must be long enough to keep its neighbours apart, and room for a gap before the arc.
        const minLen = 34;
        if (runLen < minLen && prev.idx > 0) prev.end += minLen - runLen;
        prev.ce = prev.end + hw;
        const [cx, cz] = legMap(prev, 0, prev.ce);
        leg.px = cx; leg.pz = cz; leg.cs = -prev.hw; leg.b0 = prev.hw;
        leg.turn = turnOf(prev.h, h);
        const d = legDir(leg);
        corners.push({ kind: "bend", x: cx, z: cz, y: leg.y0, dx: d[0], dz: d[1], side: leg.turn, leg: k });
        // The gap: two or three blocks of lava or water across the whole hall, just before the arc.
        const gp = stratum.def.gap;
        if (gp && !prev.stairs && fr(seed, k, 3, 11) < gp.p) {
          const w = fr(seed, k, 4, 11) < 0.55 ? 3 : 2;
          const room = prev.contentEnd + w + 4;
          if (prev.end < room) prev.end = room;
          prev.ce = prev.end + hw;
          const [ncx, ncz] = legMap(prev, 0, prev.ce);
          leg.px = ncx; leg.pz = ncz; corners[corners.length - 1].x = ncx; corners[corners.length - 1].z = ncz;
          const kindL = fr(seed, k, 5, 11) < gp.lava ? "lava" : "water";
          prev.gap = { b: prev.end - 1 - w, w, kind: kindL };
        }
        runLen = 0;
      } else {
        prev.ce = prev.end;
        const [cx, cz] = legMap(prev, 0, prev.end);
        leg.px = cx; leg.pz = cz;
      }
    }
    // Slots and side passages, as the chain has always laid them: a stone every `step` rows, alternating sides.
    let cur = leg.b0 + pre;
    const branchAfter = new Set();
    for (let q = 0; q < leg.branch; q++) branchAfter.add(Math.max(0, Math.floor((q + 1) * leg.m / (leg.branch + 1)) - 1));
    for (let t = 0; t < leg.m; t++) {
      const lvc = cur + 3;
      const slot = { i: gi, side: gi % 2 ? 1 : -1, leg: k, lvc, d: 0 };
      leg.slots.push(slot); slots.push(slot); gi++;
      cur += step + (step >= 5 ? [-1, 0, 0, 1, 2][Math.floor(fr(seed, k, 40 + t, 9) * 5)] : [0, 0, 0, 1][Math.floor(fr(seed, k, 40 + t, 9) * 4)]) + (fr(seed, k, 60 + t, 9) < 0.1 ? 3 : 0);
      if (branchAfter.has(t)) { leg.passages.push({ side: slot.side, lv: lvc + 4, len: PASSAGE_LEN, ok: true }); cur += 6; }
    }
    leg.contentEnd = cur;
    cur += 2 + post;
    if (KD.stairs) {
      leg.stairsAt = leg.b0 + STAIR_LANDING;
      cur = Math.max(cur, leg.stairsAt + STAIR_LEN);
      leg.yEnd = leg.y0 - STAIR_DROP;
    } else leg.yEnd = leg.y0;
    leg.end = cur;
    leg.ce = leg.end;
    runLen += leg.end - leg.b0;
    if (KD.styles) leg.style = KD.styles[leg.variant % KD.styles.length]; else if (KD.styleOf) leg.style = KD.styleOf(leg);
    for (const f of (KD.holes ? KD.holes : [])) if (stratum.def.holes) leg.holesAt.push(Math.round(leg.b0 + pre + (leg.contentEnd - leg.b0 - pre) * f));
    if (KD.finale) { leg.vc = leg.end - 5; }
    legs.push(leg); stratum.legs.push(leg); hist.push(kind); prev = leg;
    x = legMap(leg, 0, leg.end)[0];
  }
  const last = legs[legs.length - 1]; last.ce = last.end; last.frontier = true;

  // ---- the walker's path: a polyline through the middle of every leg with a slow sway, rounded at the bends ----
  const R = CORNER_R, STEP = 1.5;
  const pts = [];                            // x, y, z triples
  const push = (px, py, pz) => pts.push(px, py, pz);
  legs.forEach((leg, li) => {
    const nxt = legs[li + 1], bend = nxt && nxt.turn;
    const bStart = li === 0 ? 0 : (leg.turn ? R : 0), bEnd = leg.ce;
    const yAt = (b) => floorSmooth(leg, b) + 1.5;
    const swayEnd = bend ? bEnd - R : bEnd;
    const sway = (b) => { const e = Math.max(0, Math.min(1, Math.min(b - bStart, swayEnd - b, 7) / 7)); return Math.sin(b / 6.5 + li * 1.7) * 0.7 * e * e * (3 - 2 * e); };
    const from = li === 0 ? 0 : (leg.turn ? R + STEP : STEP), to = bend ? bEnd - R : bEnd;
    leg.pFrom = from; leg.pIdx = pts.length / 3;
    let nb = 0;
    for (let b = from; b < to; b += STEP, nb++) { const [px, pz] = legMap(leg, sway(b), b); push(px, yAt(b), pz); }
    if (!bend) { const [px, pz] = legMap(leg, 0, to); push(px, yAt(to), pz); nb++; }
    leg.pCount = nb;
    if (bend) {
      const dA = legDir(leg), dB = legDir(nxt);
      const [cx, cz] = legMap(leg, 0, bEnd);
      for (let q = 0; q <= 6; q++) {
        const f = (q / 6) * Math.PI / 2;
        push(cx - dA[0] * R + dB[0] * R - dB[0] * R * Math.cos(f) + dA[0] * R * Math.sin(f), yAt(bEnd), cz - dA[1] * R + dB[1] * R - dB[1] * R * Math.cos(f) + dA[1] * R * Math.sin(f));
      }
    }
  });
  const NP = pts.length / 3;
  const P = new Float32Array(pts), cum = new Float64Array(NP);
  for (let i = 1; i < NP; i++) cum[i] = cum[i - 1] + Math.hypot(P[i * 3] - P[i * 3 - 3], P[i * 3 + 1] - P[i * 3 - 2], P[i * 3 + 2] - P[i * 3 - 1]);
  const length = cum[NP - 1];
  // Distance of row b of a leg along the path: the points were laid every STEP rows.
  const dAtB = (leg, b) => {
    const f = Math.max(0, Math.min(leg.pCount - 1, (b - leg.pFrom) / STEP)), i0 = Math.floor(f), t = f - i0;
    const a = cum[leg.pIdx + i0], c = cum[Math.min(NP - 1, leg.pIdx + i0 + 1)];
    return a + (c - a) * t;
  };
  for (const leg of legs) {
    leg.dStart = cum[leg.pIdx];
    leg.dMid = dAtB(leg, (leg.b0 + leg.contentEnd) / 2);
    leg.dEnd = leg.idx + 1 < legs.length ? cum[legs[leg.idx + 1].pIdx] : length;
    for (const s of leg.slots) s.d = dAtB(leg, s.lvc + 0.5);
  }
  for (const st of strata) { st.d0 = st.legs[0].dStart; st.d1 = st.legs[st.legs.length - 1].dEnd; }
  for (const c of corners) c.d = dAtB(legs[c.leg - 1], legs[c.leg - 1].ce - R);
  for (const leg of legs) if (leg.gap) {
    const g = leg.gap, [gx, gz] = legMap(leg, 0, g.b + 0.5), nx = legs[leg.idx + 1];
    gaps.push({ leg: leg.idx, d: dAtB(leg, g.b + g.w / 2), d0: dAtB(leg, g.b), d1: dAtB(leg, g.b + g.w), x: gx, y: leg.yEnd, z: gz, dx: legDir(leg)[0], dz: legDir(leg)[1], width: g.w, kind: g.kind, side: nx.turn });
  }

  // ---- reach boxes and the grid of legs, for the world builder ----
  const reach = (leg) => {
    const ext = leg.hw + PASSAGE_LEN + REACH_PAD;
    let x0 = 1e9, x1 = -1e9, z0 = 1e9, z1 = -1e9;
    for (const a of [-ext, ext]) for (const b of [leg.cs - REACH_PAD, leg.ce + REACH_PAD]) {
      const [px, pz] = legMap(leg, a, b); x0 = Math.min(x0, px); x1 = Math.max(x1, px); z0 = Math.min(z0, pz); z1 = Math.max(z1, pz);
    }
    return { x0, x1, z0, z1 };
  };
  const CELL = 64, grid = new Map();
  const gkey = (i, j) => i * 100003 + j;
  for (const leg of legs) {
    leg.reach = reach(leg);
    for (let i = Math.floor(leg.reach.x0 / CELL); i <= Math.floor(leg.reach.x1 / CELL); i++) for (let j = Math.floor(leg.reach.z0 / CELL); j <= Math.floor(leg.reach.z1 / CELL); j++) {
      const key = gkey(i, j); if (!grid.has(key)) grid.set(key, []); grid.get(key).push(leg);
    }
  }
  // Legs whose reach touches the box (world x/z), in plan order.
  const legsIn = (x0, z0, x1, z1) => {
    const out = new Set();
    for (let i = Math.floor(x0 / CELL); i <= Math.floor(x1 / CELL); i++) for (let j = Math.floor(z0 / CELL); j <= Math.floor(z1 / CELL); j++) {
      const l = grid.get(gkey(i, j)); if (!l) continue;
      for (const leg of l) if (leg.reach.x1 >= x0 && leg.reach.x0 <= x1 && leg.reach.z1 >= z0 && leg.reach.z0 <= z1) out.add(leg);
    }
    return [...out].sort((a, b) => a.idx - b.idx);
  };
  // The body of a leg (the carved hall) as a world box, for passage collision checks.
  const body = (leg, pad = 0) => {
    let x0 = 1e9, x1 = -1e9, z0 = 1e9, z1 = -1e9;
    for (const a of [-leg.hw - pad, leg.hw + pad]) for (const b of [leg.cs - pad, leg.ce + pad]) { const [px, pz] = legMap(leg, a, b); x0 = Math.min(x0, px); x1 = Math.max(x1, px); z0 = Math.min(z0, pz); z1 = Math.max(z1, pz); }
    return { x0, x1, z0, z1 };
  };
  // Passages: decided here (so every chunk agrees) by a box test against every other hall and every other passage.
  const spots = [];
  const taken = [];
  const hit = (A, B) => A.x1 > B.x0 && A.x0 < B.x1 && A.z1 > B.z0 && A.z0 < B.z1;
  for (const leg of legs) for (const p of leg.passages) {
    const lu0 = p.side > 0 ? leg.hw - 1 : -leg.hw - p.len - 2, lu1 = p.side > 0 ? leg.hw + p.len + 2 : -leg.hw + 1;
    const [xa, za] = legMap(leg, lu0, p.lv - 2), [xb, zb] = legMap(leg, lu1, p.lv + 4);
    const box = { x0: Math.min(xa, xb), x1: Math.max(xa, xb), z0: Math.min(za, zb), z1: Math.max(za, zb) };
    let ok = true;
    for (const o of legsIn(box.x0 - 6, box.z0 - 6, box.x1 + 6, box.z1 + 6)) {
      if (o === leg) continue;
      const bb = body(o, 4); if (hit(box, bb)) { ok = false; break; }
    }
    if (ok) for (const t of taken) if (hit(box, t)) { ok = false; break; }
    p.ok = ok;
    if (ok) {
      taken.push(box);
      const hw = leg.hw, y0 = leg.y0;
      const [mx, mz] = legMap(leg, p.side * (hw + 0.5), p.lv + 1), [ex, ez] = legMap(leg, p.side * (hw + p.len - 0.5), p.lv + 1);
      const [dx, dz] = (() => { const q = legMap(leg, -p.side, 0), o = legMap(leg, 0, 0); return [q[0] - o[0], q[1] - o[1]]; })();
      p.mouth = [mx, y0, mz]; p.end = [ex, y0, ez];
      p.d = dAtB(leg, p.lv + 1);
      spots.push({ mouth: p.mouth, end: p.end, dir: [dx, dz], leg: leg.idx, side: p.side, s: null, d: p.d, rowsB: p.lv + 1 });
      corners.push({ kind: "passage", x: mx, y: y0, z: mz, dx, dz, side: p.side, leg: leg.idx, d: p.d });
    }
  }
  corners.sort((a, b) => a.d - b.d);

  // ---- profiles: the lighting keyed at the middle of each leg ----
  for (const leg of legs) {
    const st = leg.st, p = Math.max(0, Math.min(1, (leg.slots.length ? leg.slots[0].i - st.g0 : 0) / Math.max(1, st.g1 - st.g0)));
    leg.depthP = p;
    leg.prof = legProfile(leg, p);
  }
  const keyD = Float64Array.from(legs, (l) => l.dMid);
  const profileAtD = (d, out = {}) => {
    let lo = 0, hi = legs.length - 1;
    if (d <= keyD[0]) lo = hi = 0; else if (d >= keyD[hi]) lo = hi; else { while (hi - lo > 1) { const mid = (lo + hi) >> 1; if (keyD[mid] <= d) lo = mid; else hi = mid; } }
    const A = legs[lo], B = legs[Math.min(legs.length - 1, lo + 1)];
    const t = A === B ? 0 : Math.max(0, Math.min(1, (d - keyD[lo]) / Math.max(1e-4, keyD[lo + 1] - keyD[lo]))), e = t * t * (3 - 2 * t);
    const a = A.prof, b = B.prof, mix = (u, v) => u + (v - u) * e;
    out.amb = out.amb || [0, 0, 0]; out.fog = out.fog || [0, 0, 0];
    for (let q = 0; q < 3; q++) { out.amb[q] = mix(a.amb[q], b.amb[q]); out.fog[q] = mix(a.fog[q], b.fog[q]); }
    out.fogD = mix(a.fogD, b.fogD); out.exposure = mix(a.exposure, b.exposure); out.torch = mix(a.torch, b.torch); out.bloom = mix(a.bloom, b.bloom);
    out.pitch = mix(a.pitch || 0, b.pitch || 0); out.kind = e < 0.5 ? A.kind : B.kind; out.leg = e < 0.5 ? A : B; out.stratum = (e < 0.5 ? A : B).st;
    return out;
  };

  // ---- lookups ----
  const binary = (arr, key, d) => { let lo = 0, hi = arr.length - 1; while (lo < hi) { const mid = (lo + hi + 1) >> 1; if (arr[mid][key] <= d) lo = mid; else hi = mid - 1; } return lo; };
  const legAtD = (d) => { let lo = 0, hi = legs.length - 1; while (lo < hi) { const mid = (lo + hi + 1) >> 1; if (legs[mid].dStart <= d) lo = mid; else hi = mid - 1; } return legs[lo]; };
  const slotAtD = (d) => binary(slots, "d", d);          // index of the last slot at or before d
  // Where the walker is on the path at distance d: position and heading (a Catmull-Rom through the polyline).
  const pt = (i) => Math.max(0, Math.min(NP - 1, i));
  const pointAt = (d, out) => {
    d = Math.max(0, Math.min(length, d));
    let lo = 0, hi = NP - 1; while (lo < hi - 1) { const mid = (lo + hi) >> 1; if (cum[mid] <= d) lo = mid; else hi = mid; }
    const seg = Math.max(1e-6, cum[hi] - cum[lo]), t = (d - cum[lo]) / seg;
    const i0 = pt(lo - 1), i1 = lo, i2 = hi, i3 = pt(hi + 1);
    const t2 = t * t, t3 = t2 * t;
    for (let c = 0; c < 3; c++) {
      const p0 = P[i0 * 3 + c], p1 = P[i1 * 3 + c], p2 = P[i2 * 3 + c], p3 = P[i3 * 3 + c];
      out[c] = 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3);
    }
    return out;
  };

  return {
    seed, n, want, legs, slots, corners, gaps, strata, spots, length, P, cum, CELL,
    dAtB, legsIn, body, legAtD, slotAtD, profileAtD, pointAt, count: n, total: slots.length,
    // The leg that holds a world point (for the bake), nearest by its hall rectangle.
    legAt(x, z, cand) {
      let best = null, bd = Infinity;
      for (const leg of cand || legsIn(x - 1, z - 1, x + 1, z + 1)) {
        const [a, b] = legLocal(leg, x, z);
        const ra = Math.max(0, Math.abs(a) - (leg.hw + 2.5)), rb = Math.max(0, leg.cs - b, b - leg.ce);
        const d = ra * ra + rb * rb;
        if (d < bd) { bd = d; best = { leg, a, b }; if (d === 0) break; }
      }
      return best;
    },
    stratumAtD(d) { return legAtD(d).st; }
  };
}

// The light a leg carries: its kind's profile, bent toward its stratum's palette, warmer and brighter with depth in the
// stratum (p, 0 at its first stone and 1 at its last), and a little different from leg to leg (tint).
export function legProfile(leg, p) {
  const kp = leg.kd.prof, sd = leg.st.def.light || {}, tn = leg.tint, cyc = Math.min(leg.st.cycle, 3);
  const am = sd.amb || [1, 1, 1], fm = sd.fog || [1, 1, 1];
  const warm = [1 + 0.22 * p, 1 + 0.04 * p, 1 - 0.14 * p];
  const amb = kp.amb.map((v, i) => v * am[i] * warm[i] * (1 + tn[i] * 0.6) * (1 + 0.06 * p));
  const fog = kp.fog.map((v, i) => v * fm[i] * (1 + 0.1 * p * (i === 0 ? 1 : -0.4)));
  return {
    amb, fog, fogD: kp.fogD * (sd.fogD || 1) * (1 + 0.04 * cyc), exposure: kp.exposure * (sd.exposure || 1) * (1 + 0.05 * p),
    torch: kp.torch * (0.9 + 0.3 * p) * (sd.torch || 1), bloom: kp.bloom * (sd.bloom || 1), pitch: kp.pitch || 0, kind: leg.kind
  };
}
