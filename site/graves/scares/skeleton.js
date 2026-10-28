// Skeleton (round 8b: the bone pile). The owner's choice: an ossuary heaped with bones and skulls; as you cross it the
// bones rattle and a skeleton stands up out of the pile; then another, and another, all round you, bows drawn.
// Something settles in the dark beside you: a doorway in the wall you had walked past (ossuary.js carved it, with the
// room behind, before the first frame, where you could not see). You go over and look in: a low room, one torch on the
// far wall, bones heaped against every wall, skulls in the niches. You go in, slowly; a bone skids from under your foot.
// A skull rolls off the far heap by itself, knocking over the stone toward you; you stop. Nothing. Then the rattle. The
// heap shifts, a hand comes up through it, and a skeleton sits up out of the bones and stands, bones sliding off it,
// its skull turned to you. You back toward the doorway. A rattle right behind you: the heap by the doorway is coming up
// too. Then the others, all round, more than you can watch, each standing where it rose, side-on, its skull on you.
// A rattle from one: your head snaps to it and its bow comes up as it squares up to you; a rattle from another, across
// the room; another. You turn back to them: the first far off, one nearer, one at the edge of sight. Silence. The
// volley: arrows thud into you and the bones and the floor round you, and you go down. The first walks up, stands over
// you and shoots you where you lie.
// 1.7.10: bone items, skull blocks, the skeleton's model, skin and bow, its sounds (say, step, random.bow, bowhit).
// Skeletons' arms hang as they come up out of the bones; the bows come up into the game's own pose (ModelSkeleton is
// ModelZombie: arms level along the body, which by then faces you).
import { THREE, clamp, lerp, sstep, pulse, tex } from "./rig.js";
import { settle, shake, hitsOf, floorFall, arrowMesh, arrowAim, mcRot } from "./common.js";
import { splitJaw, boxOf, silence, deathScream } from "./fnaf.js";
import { roar, kick } from "./story.js";
import { findRoom, buildRoom } from "./ossuary.js";

const wrap = (a) => Math.atan2(Math.sin(a), Math.cos(a));
const BOW = [{ id: "minecraft:bow", ench: false }];
const SIDE_ON = 1.0;   // how far (rad) a risen one's body is turned from you, its right side to you, before it draws

export default {
  death: "Steve was shot by Skeleton",
  async build(R) {
    const eye = R.eye;
    const spot = findRoom(R);
    if (!spot) throw new Error("Skeleton: no room for the ossuary here");
    // ---- the first skeleton (its skin is the skulls'), the room, the rest ------------------------------------------
    const mk = () => R.mob("Skeleton", { equipment: BOW, amb: [0.1, 0.1, 0.1] });
    const first = mk();
    let skullTex = null;
    if (first.parts.head) first.parts.head.traverse((o) => { if (!skullTex && o.isMesh && o.material && o.material.map) skullTex = o.material.map; });
    const O = await buildRoom(R, spot, { seed: R.seed, skull: skullTex });
    O.carve();
    const amb = O.amb.clone().multiplyScalar(1.5);   // (pale bone: a little more than the stone round it)
    const [arrowTex] = await Promise.all([tex("entity_arrow")]);

    // ---- who rises where ------------------------------------------------------------------------------------------
    const S = O.stop, M = O.mouth, F = O.front, D = O.door;
    const walkDir = (() => { const dx = S.x - M.x, dz = S.z - M.z, n = Math.hypot(dx, dz) || 1; return { x: dx / n, z: dz / n }; })();
    const ahead = (h) => ((h.c.x - S.x) * walkDir.x + (h.c.z - S.z) * walkDir.z) / (Math.hypot(h.c.x - S.x, h.c.z - S.z) || 1);
    // (only a heap long enough to hide a skeleton lying in it has one)
    const idx = O.heaps.map((h, i) => i).filter((i) => O.heaps[i].fits);
    if (!idx.length) throw new Error("Skeleton: no heap big enough in this room");
    const i1 = idx.slice().sort((a, b) => ahead(O.heaps[b]) - ahead(O.heaps[a]))[0];
    const backTo = { x: lerp(S.x, M.x, 0.45), z: lerp(S.z, M.z, 0.45) };
    const i2 = idx.filter((i) => i !== i1).sort((a, b) => Math.hypot(O.heaps[a].c.x - backTo.x, O.heaps[a].c.z - backTo.z) - Math.hypot(O.heaps[b].c.x - backTo.x, O.heaps[b].c.z - backTo.z))[0];
    const rest = idx.filter((i) => i !== i1 && i !== i2);
    const mobs = O.heaps.map((h, i) => (i === i1 ? first : idx.includes(i) ? mk() : null));
    if (!O.heaps.length) first.pivot.visible = false;
    for (const m of mobs) if (m) m.amb.copy(amb);
    const jaw = splitJaw(first, [{ part: first.parts.head, box: boxOf("skeleton", "bipedHead"), rows: 2 }], { nTeeth: 0, max: 0.55, mouth: 0x050505, tongue: 0x100303 });

    // ---- the dice -------------------------------------------------------------------------------------------------
    const T_SET = 0.9;
    const tCl = 1.05 + R.vary(0.3, 0.35);                     // something settles in the dark beside you
    const tT0 = tCl + 0.22, tT1 = tT0 + 0.65;                  // the head goes to it: a doorway
    const LA = Math.hypot(F.x, F.z), tA0 = tT1 + R.vary(0.2, 0.3), tA1 = tA0 + Math.max(0.9, LA / Math.min(3.4, 2.4 + LA * 0.08));   // (brisker over a long way)
    // in: the doorway, the room, slowly; stopped by the skull
    const path = [{ x: F.x, z: F.z }, { x: D.x, z: D.z }, { x: M.x, z: M.z }, { x: S.x, z: S.z }];
    const segL = path.slice(1).map((p, i) => Math.hypot(p.x - path[i].x, p.z - path[i].z));
    const LB = segL.reduce((a, b) => a + b, 0);
    const vB = 1.3, tB0 = tA1 + R.vary(0.15, 0.3);
    const tTip = tB0 + 0.35 + (LB * 0.78) / vB - 0.55;         // the skull tips as you near the middle
    const tStop0 = tTip + 0.3;                                 // you stop
    const along = (t) => {   // metres walked into the room
      const a = Math.max(0, t - tB0), ramp = 0.35;
      let d = a < ramp ? vB * a * a / (2 * ramp) : vB * (a - ramp / 2);
      if (t > tStop0) { const dt = Math.min(t - tStop0, 0.4); const d0 = (() => { const a0 = tStop0 - tB0; return a0 < ramp ? vB * a0 * a0 / (2 * ramp) : vB * (a0 - ramp / 2); })(); d = d0 + vB * dt - vB * dt * dt / 0.8; }
      return Math.min(d, LB);
    };
    const onPath = (d) => { let k = 0; while (k < segL.length - 1 && d > segL[k]) { d -= segL[k]; k++; } const u = clamp(d / (segL[k] || 1)); return { x: lerp(path[k].x, path[k + 1].x, u), z: lerp(path[k].z, path[k + 1].z, u) }; };
    const stopAt = onPath(along(tStop0 + 1));
    // the skull rolls toward where you stand
    const roll = O.rollSkull(tTip, stopAt, { hi: i1 }) || { tEdge: tTip + 0.6, tStop: tTip + 1.4, knocks: [], piece: null };
    const tRat = roll.tStop + R.vary(0.75, 0.3);               // nothing; then the rattle
    const tShift = tRat + 0.3;
    const sch1 = { shift: tShift, hand0: tShift + 0.45, hand1: tShift + 1.05 };
    sch1.sit0 = sch1.hand1 + R.vary(0.3, 0.3); sch1.sit1 = sch1.sit0 + 0.95; sch1.stand0 = sch1.sit1 + 0.25; sch1.stand1 = sch1.stand0 + 0.9;
    const tBk0 = sch1.sit0 + 0.5, tBk1 = sch1.stand1 + 0.4;    // backing toward the doorway
    const back = (() => { const room = Math.hypot(backTo.x - stopAt.x, backTo.z - stopAt.z); return Math.min(1.0, room); })();
    const bdir = (() => { const dx = M.x - stopAt.x, dz = M.z - stopAt.z, n = Math.hypot(dx, dz) || 1; return { x: dx / n, z: dz / n }; })();
    const tR2 = sch1.stand1 + R.vary(0.35, 0.3);               // the rattle behind you
    const sch2 = { shift: tR2 - 0.45, hand0: tR2 - 0.25, hand1: tR2 + 0.1, sit0: tR2 + 0.15, sit1: tR2 + 0.75, stand0: tR2 + 0.85, stand1: tR2 + 1.5 };
    // the rest, all round, overlapping
    const schR = rest.map((hi, k) => { const t0 = tR2 + 0.6 + k * R.vary(0.34, 0.3); return { shift: t0 - 0.35, hand0: t0 - 0.15, hand1: t0 + 0.15, sit0: t0 + 0.2, sit1: t0 + 0.75, stand0: t0 + 0.85, stand1: t0 + 1.45 }; });
    const lastUp = Math.max(sch2.stand1, ...schR.map((s) => s.stand1));
    const tBows = lastUp + 0.3;                                 // the bows come up, one after another (the ring, below)
    // ---- the risers --------------------------------------------------------------------------------------------------
    const schOf = new Map([[i1, sch1], [i2, sch2]]);
    rest.forEach((hi, k) => schOf.set(hi, schR[k]));
    const risers = O.heaps.map((h, hi) => {
      const m = mobs[hi], sch = schOf.get(hi);
      if (!m || !sch) return null;
      const pose = O.riser(hi, m, sch);
      const end = pose(sch.stand1 + 0.01);   // where it stands
      return { m, hi, sch, pose, feet: { x: end.feet.x, z: end.feet.z }, yaw0: end.yaw };
    });
    const R1 = risers[i1];
    // where you stand when they are all up (you backed toward the doorway)
    const youDown = (() => { const p = { x: stopAt.x + bdir.x * back, z: stopAt.z + bdir.z * back }; return p; })();
    // They stand where they rose, round you at their own distances (no lining up). Their bows come up one after
    // another: a rattle from one, your head snaps to it, its bow comes up and levels at you; a rattle from another...
    // The first watched is the first one up; then up to three more, in the order whose snaps are each a readable
    // turn (35 to 120 degrees: not a neighbour, not a blur), taking in the nearest. The others come up as you turn
    // back to the frame that shows the most of the ring: the first one, one at another depth, one at the edge, no two
    // side by side.
    const standsAt = (r) => r.feet;
    const archers = risers.filter(Boolean);
    const ring = archers.map((r) => ({ r, p: r.feet, yaw: R.yawTo(youDown.x, youDown.z, r.feet.x, r.feet.z), d: Math.hypot(r.feet.x - youDown.x, r.feet.z - youDown.z) }));
    const q1 = ring.find((q) => q.r === R1) || ring[0];
    const fin = (() => {
      const hf = Math.atan(Math.tan(THREE.MathUtils.degToRad(R.camera.fov) / 2) * (R.camera.aspect || 1.6)) - 0.12;
      let best = null;
      for (let k = 0; k < 144; k++) {
        const yw = -Math.PI + k * Math.PI / 72;
        const vis = ring.map((q) => ({ q, off: wrap(q.yaw - yw) })).filter((v) => Math.abs(v.off) < hf);
        const has1 = q1 && vis.some((v) => v.q === q1);
        const far = q1 && vis.some((v) => v.q !== q1 && Math.abs(v.q.d - q1.d) > 1.0);
        const edge = vis.some((v) => Math.abs(v.off) > 0.6 * hf && v.q !== q1);
        let side = 0;
        for (let a = 0; a < vis.length; a++) for (let b = a + 1; b < vis.length; b++) if (Math.abs(vis[a].off - vis[b].off) < 0.3 && Math.abs(vis[a].q.d - vis[b].q.d) < 1.0) side++;
        const sc = (has1 ? 10 : 0) + (far ? 6 : 0) + (edge ? 4 : 0) + 2 * vis.length - 8 * side - 0.4 * (q1 ? Math.abs(wrap(yw - q1.yaw)) : 0);
        if (!best || sc > best.sc) best = { yw, sc, n: vis.length, far, edge, side };
      }
      return best;
    })();
    const order = (() => {
      if (!q1) return [];
      const others = ring.filter((q) => q !== q1), m = Math.min(3, others.length);
      const pen = (a) => (a < 0.6 ? (0.6 - a) * 4 : a > 2.1 ? (a - 2.1) * 6 : 0);
      const nearest = others.slice().sort((a, b) => a.d - b.d)[0];
      let best = null;
      const go = (seq) => {
        if (seq.length === m + 1) {
          let s = 0;
          for (let i = 1; i < seq.length; i++) s -= pen(Math.abs(wrap(seq[i].yaw - seq[i - 1].yaw)));
          s -= 0.5 * Math.max(0, Math.abs(wrap(fin.yw - seq[seq.length - 1].yaw)) - 2.4);
          if (nearest && seq.includes(nearest)) s += 0.5;
          if (!best || s > best.s) best = { s, seq: seq.slice() };
          return;
        }
        for (const q of others) if (!seq.includes(q)) { seq.push(q); go(seq); seq.pop(); }
      };
      go([q1]);
      return best ? best.seq : [q1];
    })();
    const gap = R.vary(0.68, 0.2);
    order.forEach((q, k) => { q.tUp = tBows + 0.2 + k * gap; });
    const tFrame = (order.length ? order[order.length - 1].tUp : tBows) + 0.55;   // the turn to the frame
    ring.filter((q) => q.tUp == null).forEach((q, j) => { q.tUp = tFrame + 0.12 + j * 0.15; });
    for (const q of ring) q.r.tUp = q.tUp;
    const tSil = tFrame + 0.5;                                  // silence
    const tV = tSil + R.vary(1.0, 0.25);                       // the volley
    const tDown = tV + 0.12;
    const tWalk0 = tDown + 0.6, tWalk1 = tWalk0 + 1.25;         // the first walks up
    const tKill = tWalk1 + R.vary(0.6, 0.25);
    const DUR = tKill + 0.35;
    const killAt = R1 ? (() => { const dx = R1.feet.x - youDown.x, dz = R1.feet.z - youDown.z, n = Math.hypot(dx, dz) || 1; return { x: youDown.x + dx / n * 0.95, z: youDown.z + dz / n * 0.95 }; })() : youDown;

    // ---- the walk (the feet) -------------------------------------------------------------------------------------
    const posAt = (t) => {
      if (t < tA0) return { x: 0, z: 0 };
      if (t < tB0) { const k = sstep(tA0, tA1, t); return { x: F.x * k, z: F.z * k }; }
      if (t < tBk0) return onPath(along(t));
      const k = sstep(tBk0, tBk1, t);
      return { x: stopAt.x + bdir.x * back * k, z: stopAt.z + bdir.z * back * k };
    };
    const kicks = O.kicks((t) => posAt(t), tA0, tStop0 + 0.4);
    const stepsAt = (() => {   // a footstep every 0.7 m walked
      const out = []; let acc = 0, prev = posAt(0);
      for (let t = 0; t < tBk1 + 0.1; t += 0.02) { const p = posAt(t); acc += Math.hypot(p.x - prev.x, p.z - prev.z); prev = p; if (acc > (t > tBk0 ? 0.45 : 0.7)) { acc = 0; out.push([t, p]); } }
      return out;
    })();

    // ---- where the head looks ----------------------------------------------------------------------------------------
    // (a pure function of t: rising, its pose is evaluated here; up, its head is over where it stands)
    const _hv = new THREE.Vector3();
    const headOf = (r) => (t) => {
      if (t < r.sch.stand1) { r.pose(t); r.m.pivot.updateMatrixWorld(true); return R.toLocal(r.m.parts.head ? r.m.parts.head.getWorldPosition(_hv) : r.m.pivot.position); }
      const p = standPos(r, t); return { x: p.x, y: 1.72, z: p.z };
    };
    const H = (i) => O.heaps[i] ? { x: O.heaps[i].c.x, y: 0.55, z: O.heaps[i].c.z } : { x: S.x, y: 1, z: S.z + 2 };
    const sideHeaps = rest.slice().sort((a, b) => ahead(O.heaps[b]) - ahead(O.heaps[a]));
    const looks = [
      { t: 0, d: 0.01, p: () => null },
      { t: tT0, d: 0.6, e: "o", p: { x: D.x, y: 1.15, z: D.z } },
      { t: tA1 - 0.3, d: 0.7, p: { x: O.torch[0], y: 1.2, z: O.torch[2] } },
      { t: tB0 + 0.9, d: 0.8, p: O.heaps.length > 1 ? H(sideHeaps[0] ?? i2) : H(i1) },
      { t: tB0 + 1.9, d: 0.9, p: H(i1) },
      { t: roll.piece ? tTip + 0.12 : 1e9, d: 0.3, e: "o", p: (t) => O.pieceAt(roll.piece, t) },
      { t: roll.tStop + 0.35, d: 0.9, p: H(i1) },                      // where it came from: nothing
      { t: tRat - 0.05, d: 0.3, e: "o", p: { ...H(i1), y: 0.45 } },
      { t: sch1.hand0 + 0.05, d: 0.4, e: "o", p: R1 && R1.pose.outAt ? { x: R1.pose.outAt.x, y: R1.pose.outAt.y + 0.12, z: R1.pose.outAt.z } : H(i1) },   // the hand, as it breaks out
      { t: sch1.sit0 + 0.15, d: 0.5, p: (t) => (R1 ? headOf(R1)(t) : H(i1)) },
      { t: tR2 + 0.06, d: 0.42, e: "x", p: (t) => (risers[i2] ? headOf(risers[i2])(t) : H(i2)) },
      ...schR.map((s, k) => ({ t: s.sit0 + 0.1, d: 0.38, e: "x", p: (t) => headOf(risers[rest[k]])(t) })).filter((x, k) => k < 3),
      ...order.map((q, k) => ({ t: q.tUp - 0.14, d: k ? 0.24 : 0.4, e: "x", p: { x: q.p.x, y: 1.4, z: q.p.z } })),   // the snaps
      { t: tFrame, d: 0.5, p: { x: youDown.x - Math.sin(fin.yw) * 3, y: 1.5, z: youDown.z + Math.cos(fin.yw) * 3 } },
      { t: tWalk0 - 0.2, d: 0.7, p: (t) => (R1 ? headOf(R1)(t) : H(i1)) }
    ].filter((L) => L.t < 1e8).sort((a, b) => a.t - b.t);
    const EASE = { s: (k) => k * k * (3 - 2 * k), o: (k) => 1 - Math.pow(1 - k, 3), x: (k) => 1 - Math.pow(1 - k, 6) };
    const aimOf = (c, L, t) => {
      if (!L || typeof L.p === "function" && L.p(t) === null) return { yaw: 0, pitch: -0.02 };
      const q = typeof L.p === "function" ? L.p(t) : L.p;
      if (!q) return { yaw: 0, pitch: -0.02 };
      return { yaw: R.yawTo(c.x, c.z, q.x, q.z), pitch: clamp(R.pitchTo(c.x, c.y, c.z, q.x, q.y, q.z), -1.0, 0.6) };
    };
    const lookAt = (c, t, i = null) => {
      if (i == null) { i = 0; for (let k = 0; k < looks.length; k++) if (t >= looks[k].t) i = k; }
      const cur = aimOf(c, looks[i], t);
      if (i === 0) return cur;
      const k = (EASE[looks[i].e || "s"])(clamp((t - looks[i].t) / looks[i].d));
      if (k >= 1) return cur;
      const prev = lookAt(c, t, i - 1);
      return { yaw: prev.yaw + wrap(cur.yaw - prev.yaw) * k, pitch: lerp(prev.pitch, cur.pitch, k) };
    };

    // ---- the volley ------------------------------------------------------------------------------------------------
    const lside = R.rand() < 0.5 ? 1 : -1;
    const camAtV = { x: youDown.x, y: eye, z: youDown.z };
    const arrows = archers.map((r, k) => {
      const hit = k < 3 && (r === R1 || r.hi === i2 || k === 2);
      const sp = standsAt(r), from = { x: sp.x, y: 1.45, z: sp.z };
      let to;
      if (hit) to = { x: camAtV.x + (k - 1) * 0.08, y: eye - 0.25 - 0.2 * k, z: camAtV.z };
      else {
        // the misses thud into the floor and the bones in front of you, where you see them stick
        const a = fin.yw + (R.rand() - 0.5) * 1.3, d = 0.7 + R.rand() * 0.9;
        const x = camAtV.x - Math.sin(a) * d, z = camAtV.z + Math.cos(a) * d;
        to = { x, y: Math.max(0.03, O.heightAt(x, z, tV) - 0.05), z };
      }
      const t0 = tV + R.rand() * 0.09, fly = Math.hypot(to.x - from.x, to.y - from.y, to.z - from.z) / 32;
      const m = arrowMesh(arrowTex); m.visible = false; R.add(m);
      return { r, hit, from, to, t0, t1: t0 + fly, m };
    });
    const killArrow = { from: null, to: null, t0: tKill - 0.05, t1: tKill, m: R.add(arrowMesh(arrowTex)) };
    killArrow.m.visible = false;
    const hitTimes = arrows.filter((a) => a.hit).map((a) => a.t1).sort((a, b) => a - b);
    const hits = hitsOf([...hitTimes.map((t, k) => [t, 6 - k, k % 2 ? -lside : lside]), [tKill + 0.01, 9, 1]]);

    // ---- the head ----------------------------------------------------------------------------------------------------
    const cam = (t) => {
      const s0 = settle(R, t, T_SET);
      const k = sstep(0.75, 1.2, t), p = posAt(t);
      const c = { x: lerp(s0.x, p.x, k), y: lerp(s0.y, eye, k), z: lerp(s0.z, p.z, k), yaw: s0.yaw, pitch: s0.pitch, roll: 0, fov: s0.fov, near: 0.03 };
      if (t >= tT0) { const a = lookAt(c, t); c.yaw = a.yaw; c.pitch = a.pitch; }
      // walking: the 1.7.10 view bob
      const walking = (t > tA0 && t < tA1) ? 1 : (t > tB0 && t < tStop0 + 0.3) ? 0.7 : (t > tBk0 && t < tBk1) ? 0.6 : 0;
      const ph = t * 6.2;
      c.y += -Math.abs(Math.cos(ph)) * 0.035 * walking + 0.017 * walking; c.roll += Math.sin(ph) * 0.012 * walking;
      // stopped dead by the skull; the start at the rattle; a flinch as it comes up
      c.y -= 0.03 * pulse(t, [tStop0], 0.25);
      c.fov = s0.fov - 8 * sstep(tBows, tBows + 0.3, t) * (1 - sstep(tFrame, tFrame + 0.5, t))   // closer on each bow; wide for the ring
        - 6 * sstep(tSil - 0.1, tV, t) * (1 - sstep(tV, tV + 0.06, t))   // the silence closes in
        - 24 * sstep(sch1.hand0, sch1.hand0 + 0.45, t) * (1 - sstep(sch1.sit0 + 0.05, sch1.sit0 + 0.6, t));   // the eyes fix on the hand
      const kk = kick(t, hits.slice(0, -1).map((h) => ({ t: h.t, side: h.side, amp: 1.2 })));
      c.yaw += kk.yaw; c.pitch += kk.pitch;
      shake(c, t, 0.0015 + 0.0035 * sstep(tRat, tRat + 0.5, t) * (1 - sstep(tV, tV + 0.2, t)) + 0.018 * pulse(t, [tRat], 0.18) + 0.03 * pulse(t, hits.map((h) => h.t), 0.2), 7);
      floorFall(c, t, tDown, { d: 0.5, side: lside, roll: 1.05, y: 0.28, pitch: 0.35, back: 0.35 });
      if (t > tDown + 0.45) {   // on the floor, looking up at the one that walks up
        const k2 = sstep(tDown + 0.45, tWalk0 + 0.4, t), q = R1 ? headOf(R1)(t) : { x: killAt.x, y: 1.6, z: killAt.z };
        c.yaw = c.yaw + wrap(R.yawTo(c.x, c.z, q.x, q.z) - c.yaw) * k2; c.pitch = lerp(c.pitch, clamp(R.pitchTo(c.x, c.y, c.z, q.x, q.y, q.z), -0.4, 1.2), k2); c.roll = lerp(c.roll, 0.4 * lside, k2);
      }
      return c;
    };

    // ---- the frame -------------------------------------------------------------------------------------------------
    // where a risen one stands at t: where it rose; the first, after the volley, walks up to you
    function standPos(r, t) {
      let x = r.feet.x, z = r.feet.z, walk = 0;
      if (r === R1 && t > tWalk0) { const k = clamp((t - tWalk0) / (tWalk1 - tWalk0)); x = lerp(r.feet.x, killAt.x, k); z = lerp(r.feet.z, killAt.z, k); walk = k < 1 ? 1 : 0; }
      return { x, z, walk };
    }
    const stoodPose = (r, t, cl) => {
      const m = r.m;
      const { x, z, walk } = standPos(r, t);
      // up, its skull turns to you and its body follows only so far (1.7.10 lets a head lead its body by up to 75
      // degrees): it stands side-on, its right side and the bow in its hand to you, until its bow comes up; then it
      // squares up to you as it draws, and at full draw its arms point straight at you
      const turn = sstep(r.sch.stand1, r.sch.stand1 + 0.6, t), sq = sstep((r.tUp ?? tFrame) - 0.05, (r.tUp ?? tFrame) + 0.5, t);
      const yawC = R.yawTo(x, z, cl.x, cl.z), yawF = yawC + SIDE_ON * (1 - sq), yaw = r.yaw0 + wrap(yawF - r.yaw0) * turn;
      R.place(m, x, 0, z, yaw);
      m.anim(t, 0, { walk });
      const dist = Math.hypot(cl.x - x, cl.z - z);
      const hx = clamp(-Math.atan2(cl.y - 1.62, dist), -0.6, 1.3), hy = -wrap(yawC - yaw) * 0.9;
      for (const g of [m.parts.head, m.parts.headwear]) if (g) mcRot(g, hx, clamp(hy, -1, 1), 0);
      // its bow comes up into 1.7.10's pose: ModelSkeleton is ModelZombie's arms, straight out level along the body
      // (which faces you), right arm in 0.1, left out 0.1, the idle sway (cos(age * 0.09), sin(age * 0.067), age in ticks)
      const up = sstep(r.tUp ?? tFrame, (r.tUp ?? tFrame) + 0.32, t);
      const P = m.parts;
      if (P.rightArm) {
        const sz = Math.cos(t * 20 * 0.09) * 0.05 + 0.05, sx = Math.sin(t * 20 * 0.067) * 0.05, hang = 0.05 * Math.sin(t * 1.3 + r.hi);
        mcRot(P.rightArm, lerp(hang, -Math.PI / 2 + sx, up), lerp(0, -0.1, up), lerp(0.05, sz, up));
        mcRot(P.leftArm, lerp(hang, -Math.PI / 2 - sx, up), lerp(0, 0.1, up), lerp(-0.05, -sz, up));
      }
    };
    const puffs = [];
    function update(t, f) {
      const cl = R.toLocal(R.camera.position);
      for (const r of risers) {
        if (!r) continue;
        if (t < r.sch.stand1) r.pose(t, cl); else stoodPose(r, t, cl);
      }
      O.update(t);
      // the jaw: it opens at its rattle as it sits up, and over you
      jaw.set(0.35 * pulse(t, [sch1.sit1 - 0.1], 0.35) + 0.5 * pulse(t, [tWalk1 + 0.1], 0.4) + 0.4 * pulse(t, [tKill], 0.3));
      // the torch on the far wall: the room's one light, as a Krypt torch flickers
      const fl = 0.86 + 0.08 * Math.sin(t * 17.3) + 0.06 * Math.sin(t * 43.1);
      O.light.intensity = 2.6 * fl;
      // the arrows: in flight (the volley, fast), then stuck where they hit, still quivering; the ones in you are gone
      for (const a of arrows) {
        a.m.visible = t >= a.t0 && (!a.hit || t < a.t1);
        if (!a.m.visible) continue;
        const k = clamp((t - a.t0) / (a.t1 - a.t0));
        R.at(a.m, lerp(a.from.x, a.to.x, k), lerp(a.from.y, a.to.y, k), lerp(a.from.z, a.to.z, k));
        const d = R.dirW(a.to.x - a.from.x, a.to.y - a.from.y, a.to.z - a.from.z);
        arrowAim(a.m, new THREE.Vector3(d[0], d[1], d[2]));
        if (t > a.t1) a.m.rotateZ(Math.sin((t - a.t1) * 60) * 0.1 * Math.exp(-(t - a.t1) * 5));
      }
      // point blank
      if (R1 && t >= killArrow.t0 - 0.01) {
        const from = { x: killAt.x, y: 1.35, z: killAt.z }, to = { x: cl.x, y: cl.y, z: cl.z };
        const k = clamp((t - killArrow.t0) / (killArrow.t1 - killArrow.t0));
        killArrow.m.visible = k < 1;
        if (killArrow.m.visible) { R.at(killArrow.m, lerp(from.x, to.x, k), lerp(from.y, to.y, k), lerp(from.z, to.z, k)); const d = R.dirW(to.x - from.x, to.y - from.y, to.z - from.z); arrowAim(killArrow.m, new THREE.Vector3(d[0], d[1], d[2])); }
      }
      f.env = { bake: 1 - 0.12 * sstep(tB0, tB0 + 1.5, t), lights: 1, fogMul: 1 + 0.4 * sstep(tB0, tB0 + 2, t) };
      f.vig = [0, 0, 0, 0.18 + 0.32 * sstep(tB0, tRat, t) + 0.15 * sstep(tBows, tSil + 0.5, t)]; f.vigR = 0.85;
      f.splats = hits.filter((h) => t >= h.t).map((h, i) => ({ t0: h.t, x: [0.45, 0.6, 0.38, 0.52][i % 4], y: [0.55, 0.42, 0.62, 0.4][i % 4], r: 12 + 4 * i, seed: 31 + i }));
      f.black = 0.45 * sstep(tKill, DUR + 0.3, t);
    }
    hits.forEach((h, i) => R.burst(h.t, [youDown.x, 1.2 - 0.3 * i, youDown.z], 22, "blood", { dir: [0, 0.6, 0.6], speed: 2.0, spread: 0.7, size: 0.045, life: 1.1, stick: 3 }));
    arrows.filter((a) => !a.hit).forEach((a) => R.burst(a.t1, [a.to.x, a.to.y + 0.03, a.to.z], 6, "bone", { dir: [0, 0.8, 0], speed: 1.4, spread: 0.6, size: 0.035, life: 0.6 }));

    // ---- sound ---------------------------------------------------------------------------------------------------------
    const at = (p, y = 0.5) => [p.x, y, p.z];
    const room = O.heaps.length ? at(O.heaps[i1].c, 0.6) : at(S, 0.6);
    const rattles = (r, t0, n, vol = 0.45) => [...Array(n)].map((_, i) => [t0 + i * 0.13 + (i % 2) * 0.05, "mob.skeleton.step", { at: at(O.heaps[r.hi].c, 0.5), volume: vol * (1 - i * 0.1), pitch: 0.8 + 0.1 * (i % 3), reverb: 0.5 }]);
    const landings = (hi) => O.pieces.filter((p) => p.hi === hi && p.rel && !p.rel.roll).map((p) => p.rel.t + 0.35).sort((a, b) => a - b).filter((t, i, a) => i === 0 || t - a[i - 1] > 0.12).slice(0, 7);
    const sounds = [
      // the settling in the dark
      [tCl, "dig.gravel", { at: room, volume: 0.32, pitch: 0.8, reverb: 0.6 }],
      [tCl + 0.12, "mob.skeleton.step", { at: room, volume: 0.22, pitch: 0.9, reverb: 0.6 }],
      [tCl + 0.31, "mob.skeleton.step", { at: room, volume: 0.15, pitch: 1.05, reverb: 0.6 }],
      ...stepsAt.map(([t, p], i) => [t, "step.stone", { at: [p.x, 0.05, p.z], volume: t > tB0 ? 0.3 : 0.4, pitch: 0.9 + 0.1 * (i % 3) }]),
      ...kicks.flatMap((k) => [[k.t, "random.wood_click", { at: k.at, volume: 0.28, pitch: 1.5 }], [k.t + 0.02, "mob.skeleton.step", { at: k.at, volume: 0.2, pitch: 1.3 }]]),
      // the skull: it tips, it knocks down the heap and over the stone toward you
      ...(roll.piece ? [[tTip + 0.05, "dig.gravel", { at: room, volume: 0.25, pitch: 1.2 }], ...roll.knocks.map((t, i) => [t, i ? "step.stone" : "dig.stone", { at: (() => { const q = O.pieceAt(roll.piece, t) || stopAt; return [q.x, 0.1, q.z]; })(), volume: Math.max(0.15, 0.6 - i * 0.12), pitch: 0.95 + (i % 2) * 0.1 }])] : []),
      // the rattle; the heap shifts; it comes up out of it
      [tRat, "mob.skeleton.say", { at: room, volume: 0.85, pitch: 0.82, reverb: 0.5 }],
      [tShift, "dig.gravel", { at: room, volume: 0.55, pitch: 0.75 }],
      ...(R1 ? rattles(R1, tShift + 0.05, 3, 0.4) : []),
      ...(R1 ? landings(i1).map((t, i) => [t, i % 3 ? "mob.skeleton.step" : "dig.gravel", { at: room, volume: 0.42, pitch: 0.9 + 0.08 * (i % 3) }]) : []),
      ...(R1 ? roar(sch1.sit1 - 0.1, [["mob.skeleton.say", { at: room, pitch: 0.68 }]], { hit: 0.35, volume: 0.85 }) : []),
      ...(R1 ? [[sch1.stand0 + 0.2, "mob.skeleton.step", { at: room, volume: 0.55 }], [sch1.stand1 - 0.1, "mob.skeleton.step", { at: room, volume: 0.6, pitch: 0.9 }]] : []),
      // behind you
      ...(risers[i2] ? [[tR2, "mob.skeleton.say", { at: at(O.heaps[i2].c, 0.7), volume: 1.15, pitch: 0.9 }], [tR2 - 0.5, "dig.gravel", { at: at(O.heaps[i2].c), volume: 0.35 }], ...rattles(risers[i2], tR2 + 0.15, 3, 0.5), ...landings(i2).map((t) => [t, "mob.skeleton.step", { at: at(O.heaps[i2].c), volume: 0.4 }])] : []),
      ...rest.flatMap((hi, k) => [[schR[k].shift + 0.1, "dig.gravel", { at: at(O.heaps[hi].c), volume: 0.35 }], [schR[k].sit0, "mob.skeleton.say", { at: at(O.heaps[hi].c, 0.7), volume: 0.75, pitch: [1.0, 0.78, 1.12, 0.88][k % 4] }], ...rattles(risers[hi], schR[k].sit0 + 0.1, 2, 0.38)]),
      // a rattle from one, and its bow comes up; from another; the others as you turn back; silence
      ...order.flatMap((q, k) => [[q.tUp - 0.2, "mob.skeleton.step", { at: [q.p.x, 0.9, q.p.z], volume: 0.75, pitch: [0.85, 1.0, 0.78, 0.92][k % 4] }], [q.tUp - 0.08, "mob.skeleton.step", { at: [q.p.x, 1.2, q.p.z], volume: 0.5, pitch: [1.1, 0.9, 1.0, 1.2][k % 4] }]]),
      silence(tSil, { fade: 0.25 }),
      // the volley
      ...arrows.map((a) => [a.t0 - 0.02, "random.bow", { at: [a.from.x, 1.5, a.from.z], volume: 1.0, pitch: 0.95 + R.rand() * 0.15 }]),
      ...arrows.filter((a) => !a.hit).map((a) => [a.t1, "random.bowhit", { at: [a.to.x, a.to.y, a.to.z], volume: 0.9 }]),
      ...hits.slice(0, -1).flatMap((h, i) => [[h.t, "game.player.hurt"], [h.t + 0.01, "random.bowhit", { volume: 1 }], [h.t + 0.015, "qf.scare.hit", { volume: i ? 0.6 : 1.0 }], [h.t + 0.03, "qf.scare.gore", { volume: 0.8 }]]),
      [tDown + 0.45, "game.player.hurt.fall.small"],
      // (the scream is kept for the point-blank shot alone: one FNAF scream, not two in 2.5 s)
      // it walks up; stands over you; point blank
      ...(R1 ? [0, 1, 2, 3].map((i) => [tWalk0 + 0.15 + i * 0.36, "mob.skeleton.step", { at: [lerp(R1.feet.x, killAt.x, (i + 1) / 4), 0.1, lerp(R1.feet.z, killAt.z, (i + 1) / 4)], volume: 0.5 + i * 0.12 }]) : []),
      [tWalk1 + 0.1, "mob.skeleton.say", { at: [killAt.x, 1.6, killAt.z], volume: 1.1, pitch: 0.65 }],
      [tKill - 0.06, "random.bow", { at: [killAt.x, 1.4, killAt.z], volume: 1.3 }],
      [tKill + 0.01, "game.player.hurt"], [tKill + 0.015, "qf.scare.hit", { volume: 1.0 }], [tKill + 0.03, "qf.scare.crunch", { volume: 1 }],
      ...deathScream(tKill + 0.06, { volume: 1.3 }),
      [DUR, "game.player.die"], [DUR, "@muffle", { hz: 420, s: 3 }]
    ];
    const loops = [
      [tRat + 0.2, tSil, "qf.scare.heartbeat", { volume: 0.5, fadeIn: 0.6, fadeOut: 0.1 }],
      [tBk0, tSil, "qf.scare.breath", { volume: 0.3, fadeIn: 0.8, fadeOut: 0.05 }],
      [tDown + 0.3, DUR + 0.2, "qf.scare.heartbeat", { volume: 0.65, pitch: 1.35, fadeIn: 0.2 }]
    ];
    const r2 = (x) => Math.round(x * 100) / 100;
    return {
      dur: DUR, hits, cam, update, sounds, loops, deathSide: lside,
      solid: (w) => O.solid(w),
      marks: { dread: tRat, fake: tTip + 0.2, lunge: sch1.sit1, kill: tKill + 0.05, hand: sch1.hand1, sit: (sch1.sit0 + sch1.sit1) / 2, stand: sch1.stand0 + 0.5, behind: tR2 + 0.7, ...Object.fromEntries(order.map((q, k) => ["bow" + k, q.tUp + 0.17])), bows: tFrame + 0.55, volley: tV + 0.12 },
      notes: { room: [spot.s, spot.T, spot.Wa, spot.Dd, r2(spot.xc), r2(spot.zc)], heaps: O.heaps.length, niches: O.niches.length, i1, i2, tCl: r2(tCl), tB0: r2(tB0), tTip: r2(tTip), tRat: r2(tRat), sit1: r2(sch1.sit0), tR2: r2(tR2), tBows: r2(tBows), ring: ring.map((q) => [q.r.hi, r2(q.d), Math.round(THREE.MathUtils.radToDeg(wrap(q.yaw - fin.yw))), r2(q.tUp), order.indexOf(q)]), frame: { n: fin.n, far: fin.far, edge: fin.edge, side: fin.side }, bowIn: O.bows.map((b) => [r2(b.t), b.best + '/' + b.of]), stop: [r2(O.stop.x), r2(O.stop.z)], pileCover: r2(O.pileCover ?? -1), handOut: R1 && R1.pose.outAt ? [r2(R1.pose.outAt.y), r2(R1.pose.outAt.len)] : null, tV: r2(tV), tKill: r2(tKill), dur: r2(DUR) }
    };
  }
};
