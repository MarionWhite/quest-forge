// Wither Skeleton (round 8b, the owner's redo: "Too tall to follow"). In 1.7.10 a wither skeleton is 0.72 x 2.34: it
// cannot path through a gap two blocks high. It walks at a skeleton's pace (attack-on-collide speed 1.2, about 3 m/s),
// so a sprinting player (5.6 m/s) gets away from it; it carries a stone sword, has the skeleton's sounds, and its blow
// gives Wither (black hearts).
// Its rattle and the scrape of a sword on stone, down the corridor in the dark. It comes out of the dark, black and tall,
// coming at you. You turn and run (the sprint's FOV, the head bobbing, the breath ragged), its steps behind you; you
// look back once and it is there. A low opening in the wall, two blocks high: you dive in, turn and back away. It
// fills the opening, its skull above the lintel, grinding the stone, its arms and sword reaching in; again, and again.
// Then it stands dead still, and every sound goes. It steps back, its skull looks in at you under the lintel, and it
// turns away down the corridor; its steps go. The heartbeat slows, a breath out, nothing. You go on, deeper: the
// passage opens into a tall dark room. A scrape of stone behind you. You turn: it stands between you and the light of
// a second opening, a way round from the corridor (three blocks high), perfectly still, closer than you thought. Then
// it comes: the blow, the hearts go black, the second, on the floor, the sword comes down.
// The passage (1 x 2, four long), the room (five high) and the way round (1 x 3) are carved with the Krypt's carve
// contract in build, before the first frame, where the start view cannot see them (behind you, or behind stone), and
// restored on dispose. Vanilla throughout; the one device is the silence while it stands in the opening.
import { THREE, clamp, lerp, sstep, pulse } from "./rig.js";
import { shake, hitsOf, floorFall, bipedSwing, swingAt, mcRot } from "./common.js";
import { silence, deathScream } from "./fnaf.js";
import { blow, kick } from "./story.js";
import { poly, bez, runProfile, bob, lightOf, STEP, blocks, startView, hidden, sideSpots } from "./chase.js";

const wrap = (a) => Math.atan2(Math.sin(a), Math.cos(a));
const V_RUN = 5.4, V_MOB = 3.1, V_WALK = 1.8;
const V_OUT = 3.0, V_ON = 1.9;   // it steps out of its dark quickly, then walks at you; once you run it runs too (V_CH, 2.8-4.4: never as fast as your sprint)

export default {
  death: "Steve was slain by Wither Skeleton",
  async build(R) {
    const st = R.start, eye = R.eye;
    // ---- the blocks round you, and what the first frame sees (the carve must not show in it) ---------------------------
    const B = blocks(R), { y0, wB, S, cL, clear, wallAt } = B, seen0 = startView(R);
    const asp = R.camera.aspect || 16 / 9;
    const mouthHidden = (face, zc, h, s) => { for (const dz of [-0.46, 0, 0.46]) for (const y of [0.05, h / 2, h - 0.05]) if (seen0(face - s * 0.04, y, zc + dz)) return false; return true; };
    let graves = [];
    try { graves = (R.kr.gravesNear ? R.kr.gravesNear(R.O, 26) : []).map((g) => R.toLocal(g.stone)); } catch (e) { graves = []; }

    // ---- where: a passage A (1 x 2) off the corridor ahead of your flight, a tall room behind the wall, a way round B
    // (1 x 3) further along; all in solid rock with a solid shell, the corridor open in front of both mouths ------------
    const why = {};
    const no = (k) => { why[k] = (why[k] || 0) + 1; };
    // (each carve rebuilds every chunk it touches, light and all: fewer chunks, a shorter wait before the first frame)
    const remeshes = (boxes) => boxes.reduce((n, [lo, hi]) => n + (Math.floor((hi[0] + 1) / 16) - Math.floor((lo[0] - 1) / 16) + 1) * (Math.floor((hi[2] + 1) / 16) - Math.floor((lo[2] - 1) / 16) + 1), 0);
    const box = (a0, a1, b0, b1, ya, yb) => { const p = wB(a0, b0), q = wB(a1, b1); return [[Math.min(p[0], q[0]), ya, Math.min(p[1], q[1])], [Math.max(p[0], q[0]), yb, Math.max(p[1], q[1])]]; };
    function search({ LA, RW, RH, kMin, kMax, dBs }) {
      const out = [];
      for (const d of [-1, 1]) {
        let run = 0; for (let k = 1; k <= kMax + 4 && clear(0, d * k); k++) run = k;
        if (!clear(0, 0)) continue;
        let kM = 0; for (let k = 1; k <= 16 && clear(0, -d * k); k++) kM = k;   // the way it comes
        for (const s of [-1, 1]) for (let kA = kMin; kA <= Math.min(kMax, run); kA++) {
          const rowA = d * kA, aw = wallAt(s, rowA); if (aw < 1) { no("wallA"); continue; }
          let ok = true; for (let i = 0; i < aw; i++) if (!clear(s * i, rowA)) ok = false;
          if (!ok) { no("toA"); continue; }
          for (const dB of dBs) {
            // the way round: its mouth wherever the wall is on that row (a step in or out of the wall is fine)
            const rowB = rowA + d * dB, awB = wallAt(s, rowB);
            if (awB < 1 || Math.abs(awB - aw) > 2 || awB > aw + LA - 2) { no("wallB"); continue; }
            // the corridor along the wall from one mouth to the other (a column further in where the wall stands out)
            const aF = Math.min(aw, awB) - 1;
            let aMid = -1;
            for (const am of [aF, aF - 1]) {
              if (am < 0) continue;
              let ok3 = true;
              for (let k = 1; ok3 && k < dB; k++) if (!clear(s * am, rowA + d * k)) ok3 = false;
              for (let i = am; ok3 && i < aw; i++) if (!clear(s * i, rowA)) ok3 = false;
              for (let i = am; ok3 && i < awB; i++) if (!clear(s * i, rowB)) ok3 = false;
              if (ok3) { aMid = am; break; }
            }
            if (aMid < 0) { no("front"); continue; }
            const cells = new Map(), key = (a, y, b) => a + "," + y + "," + b, add = (a, y, b) => cells.set(key(a, y, b), [a, y, b]);
            for (let i = aw; i < aw + LA; i++) for (let y = y0; y < y0 + 2; y++) add(s * i, y, rowA);
            for (let i = awB; i < aw + LA; i++) for (let y = y0; y < y0 + 3; y++) add(s * i, y, rowB);
            const bLo = Math.min(rowA, rowB) - 1, bHi = Math.max(rowA, rowB) + 1;
            for (let i = aw + LA; i < aw + LA + RW; i++) for (let b = bLo; b <= bHi; b++) for (let y = y0; y < y0 + RH; y++) add(s * i, y, b);
            let good = true;
            for (const [a, y, b] of cells.values()) if (!S(a, y, b)) { good = false; break; }
            if (!good) { no("rock"); continue; }
            const mouth = new Set([key(s * (aw - 1), y0, rowA), key(s * (aw - 1), y0 + 1, rowA), key(s * (awB - 1), y0, rowB), key(s * (awB - 1), y0 + 1, rowB), key(s * (awB - 1), y0 + 2, rowB)]);
            for (const [a, y, b] of cells.values()) {
              for (const [da, dy, db] of [[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]]) {
                const k2 = key(a + da, y + dy, b + db);
                if (cells.has(k2) || mouth.has(k2)) continue;
                // (the mouth block may stand at a step in the wall: the corridor beside it, not a way in)
                if (db !== 0 && (a === s * aw && b === rowA || a === s * awB && b === rowB) && !S(a + da - s, y + dy, b + db)) continue;
                if (!S(a + da, y + dy, b + db)) { good = false; break; }
              }
              if (!good) break;
            }
            if (!good) { no("shell"); continue; }
            const fA = cL(s * aw, rowA), faceX = fA.x - s * 0.5, zA = fA.z, fBc = cL(s * awB, rowB), faceB = fBc.x - s * 0.5, zB = fBc.z;
            if (!mouthHidden(faceX, zA, 2, s) || !mouthHidden(faceB, zB, 3, s)) { no("seen"); continue; }
            // no torch on the wall where a mouth goes; no grave in the way along the wall between them
            if (R.torches.some((T) => (Math.abs(T.l.x - faceX) < 0.9 && Math.abs(T.l.z - zA) < 0.9) || (Math.abs(T.l.x - faceB) < 0.9 && Math.abs(T.l.z - zB) < 0.9))) { no("torch"); continue; }
            const zLo = Math.min(zA, zB) - 0.9, zHi = Math.max(zA, zB) + 0.9;
            if (graves.some((g) => Math.abs(g.x - faceX) < 1.7 && g.z > zLo && g.z < zHi)) { no("grave"); continue; }
            const boxes = [box(s * aw, s * (aw + LA - 1), rowA, rowA, y0, y0 + 1), box(s * awB, s * (aw + LA - 1), rowB, rowB, y0, y0 + 2), box(s * (aw + LA), s * (aw + LA + RW - 1), bLo, bHi, y0, y0 + RH - 1)];
            const nm = remeshes(boxes);
            const score = Math.abs(kA - 8) * 0.35 + (dB - 3) * 0.3 + Math.max(0, 9 - kM) * 0.3 + (aw > 3 ? 0.5 : 0) + 0.2 * Math.abs(awB - aw) + 0.7 * (nm - 3);
            out.push({ d, s, kA, rowA, rowB, dB, aw, awB, aMid, kM, faceX, faceB, zA, zB, xMid: cL(s * aMid, rowA).x, LA, RW, RH, cells: [...cells.values()], boxes, nm, score });
          }
        }
      }
      return out.sort((p, q) => p.score - q.score);
    }
    let Lay = null, tries = 0;
    const carveT = [];
    for (const o of [{ LA: 4, RW: 5, RH: 5, kMin: 4, kMax: 10, dBs: [3, 4] }, { LA: 3, RW: 4, RH: 4, kMin: 3, kMax: 11, dBs: [3, 4, 2] }]) {
      for (const c of search(o).slice(0, 3)) {
        for (const [mn, mx] of c.boxes) {
          const t0 = performance.now(); R.carveW(mn, mx); carveT.push(Math.round(performance.now() - t0));
          // (a frame between the carves: the Krypt draws on while this builds, out of sight of all of it)
          await new Promise((r) => { const to = setTimeout(r, 40); requestAnimationFrame(() => { clearTimeout(to); r(); }); });
        }
        tries++;
        if (c.cells.every(([a, y, b]) => !S(a, y, b))) { Lay = c; break; }
        try { R.kr.restore(); } catch (e) { /* ignore */ }   // (a chunk there has no blocks to carve: the next one)
      }
      if (Lay) break;
    }
    if (!Lay) throw new Error("witherskeleton: no rock for the passage and the room here " + JSON.stringify(why));
    const { d, s, faceX, faceB, zA, zB, LA, RW, RH } = Lay;

    // ---- the places (local metres) -------------------------------------------------------------------------------------
    const xRun = cL(0, 0).x;
    const yawTo = (a, b) => R.yawTo(a.x, a.z, b.x, b.z);
    const yawMob = R.yawTo(0, 0, 0, -d), yawOut = R.yawTo(0, 0, -s, 0), yawIn = R.yawTo(0, 0, s, 0);
    const inA = (D) => ({ x: faceX + s * D, z: zA });                   // D metres into the passage from the wall face
    const FA2 = { x: faceX - s * 0.42, z: zA };                         // it, square in the opening
    const FA3 = { x: faceX - s * 1.0, z: zA };                          // stepped back from it
    const D1 = 1.6, D2 = 2.9;                                           // where you stop inside; where you back to
    // the room: you go in to PR (straight on, looking up); it waits by the mouth of the way round (K), in the corridor's
    // light that comes down it, behind you and to the side: out of sight of the passage you came by and of the walk
    const PR = { x: faceX + s * (LA + Math.min(1.9, RW - 2.0)), z: zA - d * 0.3 };
    // (K: the first of these from which no part of it, the sword held out before it included, shows anywhere along the
    // walk in: tested from the passage and the room at the walk's heading, with the frame's width and a margin)
    const hf = Math.atan(Math.tan(THREE.MathUtils.degToRad(st.fov) / 2) * asp) + 0.14;
    const walkPts = [inA(D2), inA(LA - 0.6), inA(LA + 0.2), { x: (inA(LA + 0.2).x + PR.x) / 2, z: (zA + PR.z) / 2 }, PR];
    const showsAt = (k) => {
      const fy = R.yawTo(k.x, k.z, PR.x, PR.z), f = { x: -Math.sin(fy), z: Math.cos(fy) };
      const pts = [[k.x, 1.2, k.z], [k.x + 0.3, 2.3, k.z], [k.x - 0.3, 0.3, k.z], [k.x + f.x * 0.75, 0.8, k.z + f.z * 0.75], [k.x + f.x * 0.75 + f.z * 0.35, 0.9, k.z + f.z * 0.75 - f.x * 0.35], [k.x + f.x * 0.75 - f.z * 0.35, 0.9, k.z + f.z * 0.75 + f.x * 0.35]];
      for (let i = 0; i + 1 < walkPts.length; i++) {
        const a = walkPts[i], b = walkPts[i + 1], yw = i === 0 ? yawIn : R.yawTo(a.x, a.z, b.x, b.z);
        for (let q = 0; q <= 1; q += 0.25) {
          const cx = lerp(a.x, b.x, q), cz = lerp(a.z, b.z, q);
          for (const [x, y, z] of pts) {
            if (Math.abs(wrap(R.yawTo(cx, cz, x, z) - yw)) > hf) continue;
            const n = Math.hypot(x - cx, y - eye, z - cz); let open = true;
            for (let r = 0.1; r < n - 0.1; r += 0.08) if (R.solid(cx + (x - cx) * r / n, eye + (y - eye) * r / n, cz + (z - cz) * r / n)) { open = false; break; }
            if (open) return true;
          }
        }
      }
      return false;
    };
    let K = null;
    for (const [ox, oz] of [[0.7, 0.45], [0.55, 0.3], [0.45, 0.15], [0.35, 0], [1.0, 0.0]]) { const k = { x: faceX + s * (LA + ox), z: zB - d * oz }; if (!showsAt(k)) { K = k; break; } }
    if (!K) K = { x: faceX + s * (LA + 0.35), z: zB };
    const toK = { x: K.x - PR.x, z: K.z - PR.z }, lK = Math.hypot(toK.x, toK.z), uK = { x: toK.x / lK, z: toK.z / lK };
    const S1 = { x: PR.x + uK.x * 1.0, z: PR.z + uK.z * 1.0 };          // where it strikes from
    const kb = { x: -uK.x, z: -uK.z };
    const S2 = { x: PR.x + uK.x * 0.62, z: PR.z + uK.z * 0.62 };        // over you on the floor
    // ---- its way to you: down the corridor out of the dark (or out of a side way round the bend) -----------------------
    // It stands out of sight when the head is taken (in an alcove or a side way off the corridor, the way it comes),
    // and steps out of it; else round the bend at the end; else far down the corridor, in the dark.
    const bodyHidden = (p) => hidden(seen0, p);
    let pre = [];
    const best = sideSpots(R, B, seen0, { dir: -d, kMin: 5, kMax: Math.min(13, Lay.kM), want: 9 })[0] || null;
    let kE = Math.min(Lay.kM, 13);
    if (best) { kE = best.k; pre = [best.c]; }
    else if (kE < 13) for (const sd of [-1, 1]) { let j = 0; while (j < 6 && clear(sd * (j + 1), -d * kE)) j++; if (j >= 2 && (!pre.length || j > pre.j)) { pre = [cL(sd * j, -d * kE)]; pre.j = j; } }
    const zE = cL(0, -d * kE).z;
    const chase = poly([...pre, { x: xRun, z: zE }, { x: xRun, z: zA - d * 1.0 }, FA2]);
    const hid0 = bodyHidden(chase.at(0));

    // ---- your flight: turn, sprint, round into the passage ------------------------------------------------------------
    const zCorner = zA - d * Math.min(1.5, Math.abs(zA) - 0.6);
    const runP = poly([{ x: 0, z: 0 }, { x: xRun * 0.6, z: d * 0.7 }, { x: xRun, z: zCorner }, ...bez({ x: xRun, z: zCorner }, { x: xRun, z: zA }, { x: faceX - s * 0.2, z: zA }, 12).slice(1), inA(D1)]);
    const straight = Math.abs(zCorner) - 0.4;

    // ---- the beats -----------------------------------------------------------------------------------------------------
    const tSay = R.vary(0.6, 0.2);                                        // its rattle, far off in the dark
    const tLook = tSay + 0.15, tLook1 = tLook + (Math.abs(wrap(yawMob - st.yaw)) > 1.6 ? 1.0 : 0.6);
    // It steps out after the rattle, squares up to you and walks at you. You freeze a moment, then back away from it
    // (unsteady steps, the eyes on it, the breath coming), and turn and run while it is still 6-7 m off.
    // (in its hiding place it stands turned away, into the dark, its sword with it; it turns at the rattle and comes)
    const tM0 = tSay + 0.2, tMw = tM0 + (pre.length ? 0.35 : 0);
    const uSq = pre.length ? Math.hypot(pre[0].x - xRun, pre[0].z - zE) : 0;   // out of its hiding place, square to you
    const tF0 = Math.max(tLook1, tMw + uSq / V_OUT);                     // you see it come at you: frozen
    const tB0 = tF0 + R.vary(0.5, 0.2);                                   // then backing away
    const uBmax = clamp(straight - 3.2, 0.35, 1.3);                       // (room left to run before the corner)
    const bSteps = [];
    { let u = 0, t = tB0; for (let i = 0; i < 8; i++) { const l = R.vary(0.4, 0.2), dt = R.vary(0.5, 0.15); bSteps.push({ t, dt, u0: u, l }); u += l; t += dt; } }
    const backU = (t) => { let u = 0; for (const b of bSteps) { if (t <= b.t) break; u = b.u0 + b.l * sstep(0, 0.75, (t - b.t) / b.dt); } return Math.min(u, uBmax); };
    const uOn = (t) => { const e = Math.max(0, t - tMw), e1 = uSq / V_OUT; return Math.min(chase.L, e <= e1 ? e * V_OUT : uSq + (e - e1) * V_ON); };
    const gapAt = (t) => { const m = chase.at(uOn(t)), p = runP.at(backU(t)); return Math.hypot(m.x - p.x, m.z - p.z); };
    const gapR = R.vary(6.5, 0.07);
    // (two steps back at least, unless it is on you sooner: then you run when it is 5.2 m off)
    let tRun = tB0 + 0.45;
    while (tRun < tB0 + 2.4 && gapAt(tRun) > (tRun < tB0 + 0.95 ? 5.2 : gapR)) tRun += 0.05;
    const uP0 = backU(tRun);
    const prof = runProfile(runP.L - uP0, { v: V_RUN }), runDur = prof.dur, uRunAt = (dt) => uP0 + prof.u(dt);
    const tGo = tRun + 0.15, tIn = tGo + runDur;                         // the sprint; in the passage
    // It runs when you do: slower than your sprint (it never gains on you), and you are in and turned round about
    // 1.3 s before it is at the opening (a 0.4 s pick-up from its walk).
    const uR = Math.min(chase.L - 0.3, uOn(tRun)), Lr = chase.L - uR, aC = 0.4, T1 = tIn + 1.3 - tRun;
    const V_CH = clamp((Lr - V_ON * aC / 2) / Math.max(0.5, T1 - aC / 2), 2.8, 4.4);
    const tMA = tRun + (Lr + (V_CH - V_ON) * aC / 2) / V_CH;            // it reaches the opening
    const uMob = (t) => { if (t < tRun) return uOn(t); const e = t - tRun; return Math.min(chase.L, uR + V_ON * e + (V_CH - V_ON) * (e < aC ? e * e / (2 * aC) : e - aC / 2)); };
    // the look back: once, on the straight
    const sR = straight - uP0;
    const tGl = tGo + prof.tAt(Math.max(0.45, Math.min(sR * 0.18, sR - 3.6))), glLen = 0.72;
    const tTurnA = tIn - 0.05, tTurnA1 = tTurnA + 0.55, tBk1 = tTurnA1 + 0.75;   // round to face the opening; backing away
    // in the opening: its tries, the stillness, the step back and the look in, the turn away
    const shoves = [tMA + 0.15]; const nSh = R.chance(0.5) ? 4 : 3;
    for (let i = 1; i < nSh; i++) shoves.push(shoves[i - 1] + R.vary(0.78 - 0.08 * i, 0.12));
    const tStill = shoves[nSh - 1] + 0.5, tBack = tStill + R.vary(1.6, 0.12), tPeek = tBack + 0.45, tAway = tPeek + R.vary(0.6, 0.15);
    const away = poly([FA3, { x: Lay.xMid, z: zA + d * 0.8 }, { x: Lay.xMid, z: zB - d * 0.8 }, { x: faceB - s * 0.5, z: zB - d * 0.3 }, { x: faceB + s * 0.3, z: zB }, { x: faceX + s * (LA + 0.2), z: zB }, K]);
    const tAw0 = tAway + 0.35, tKarr = tAw0 + away.L / V_MOB;
    const tGone = tAw0 + 0.7;                                             // out of sight of the opening
    // the calm, then deeper
    const tDeep = tGone + R.vary(2.2, 0.12), tDeep1 = tDeep + 0.9;
    const walkP = poly([inA(D2 + 0.12), inA(LA + 0.2), PR]);
    const tWalk0 = tDeep1 - 0.1, tWalk1 = tWalk0 + walkP.L / V_WALK + 0.35;
    const tRoom = tWalk0 + (LA + 0.2 - D2) / V_WALK;                      // out into the room: the ceiling goes up
    const tUp1 = tRoom + 1.0, tDown = tUp1 + 0.25, tDown1 = tDown + 0.6;
    const tCue = Math.max(tDown1, tWalk1) + 0.2, tTurnK = tCue + 0.25, tRev = tTurnK + 0.8;   // the scrape; the turn; it
    const tGoK = tRev + R.vary(0.55, 0.15), tH1 = tGoK + 0.42;            // still for a moment; then two steps and the blow
    const tH2 = tH1 + 1.0, tFl = tH2 + 0.05, tFloor = tFl + 0.5;
    const tW1 = tFloor + 0.45, tW2 = tW1 + 0.55, tUp = tW2 + 0.1, tH3 = tUp + 0.5, DUR = tH3 + 0.15;
    const yawK = R.yawTo(PR.x, PR.z, K.x, K.z);
    const dirT = Math.sign(wrap(yawK - yawIn)) || 1;
    const hits = hitsOf([[tH1, 7, -dirT], [tH2, 6, dirT], [tW1, 2, 1], [tW2, 2, -1], [DUR, 3, 1]]);

    // ---- it -------------------------------------------------------------------------------------------------------------
    // where it is, which way it faces, how far it has walked (its legs swing with distance, as limbSwing does)
    const mobAt = (t) => {
      if (t < tMA) { const u = uMob(t), p = chase.at(u); return { x: p.x, z: p.z, yaw: R.yawTo(0, 0, p.dx, p.dz) + (pre.length ? Math.PI * (1 - sstep(tM0, tMw, t)) : 0), dist: u, moving: t > tMw }; }
      if (t < tBack) return { x: FA2.x, z: FA2.z, yaw: yawIn, dist: chase.L, moving: false };
      if (t < tAw0) { const k = sstep(tBack, tPeek, t); return { x: lerp(FA2.x, FA3.x, k), z: lerp(FA2.z, FA3.z, k), yaw: t < tAway ? yawIn : lerp(yawIn, yawIn + wrap(yawTo(FA3, away.at(0.6)) - yawIn), sstep(tAway, tAw0, t)), dist: chase.L + 0.58 * k + (t > tAway ? (t - tAway) * 0.4 : 0), moving: t > tBack && t < tPeek }; }
      if (t < tKarr) { const u = (t - tAw0) * V_MOB, p = away.at(u), q = away.at(u + 0.5); return { x: p.x, z: p.z, yaw: yawTo(p, q), dist: chase.L + 0.8 + u, moving: true }; }
      const toP = R.yawTo(K.x, K.z, PR.x, PR.z);
      if (t < tGoK) return { x: K.x, z: K.z, yaw: toP, dist: 0, moving: false };
      const k = sstep(tGoK, tH1 - 0.05, t);
      if (t < tH2 + 0.3) return { x: lerp(K.x, S1.x, k), z: lerp(K.z, S1.z, k), yaw: toP, dist: k * 1.2, moving: k > 0.01 && k < 0.99 };
      const k2 = sstep(tH2 + 0.3, tW1, t);
      return { x: lerp(S1.x, S2.x, k2), z: lerp(S1.z, S2.z, k2), yaw: toP, dist: 1.2 + k2 * 0.4, moving: k2 > 0.02 && k2 < 0.98 };
    };
    const W = R.mob("WitherSkeleton", { amb: [0.03, 0.03, 0.035], own: true, equipment: [{ id: "minecraft:stone_sword", ench: false }] });
    W.anim(0, 0, {}); { const m = mobAt(0); R.place(W, m.x, 0, m.z, m.yaw); }
    // its light: the Krypt's own bake where it stands (the floor under it), sampled along its ways
    const lp = [];
    for (let u = 0; u <= chase.L; u += 1.0) lp.push(chase.at(u));
    for (let u = 0; u <= away.L; u += 1.0) lp.push(away.at(u));
    const lightAt = lightOf(R, lp.concat([K, PR]));

    // ---- the head ---------------------------------------------------------------------------------------------------------
    const walkU = (t) => { const T = walkP.L / V_WALK; const k = clamp((t - tWalk0) / (T + 0.35)); return walkP.L * (k < 0.15 ? 0.5 * k * k / 0.15 / 0.85 : k > 0.85 ? 1 - 0.5 * (1 - k) * (1 - k) / 0.15 / 0.85 : (k - 0.075) / 0.85); };
    const runYaw0 = yawMob + (Math.PI - 0.001) * -s * d;                  // the whip round (toward the far side of the corridor)
    const glS = s * d;                                                   // the look back, over the shoulder away from the wall
    const glK = (t) => sstep(tGl, tGl + 0.2, t) * (1 - sstep(tGl + glLen - 0.2, tGl + glLen, t));
    const pathYaw = (u) => { const p = runP.at(u), q = runP.at(Math.min(runP.L, u + 0.8)); return Math.hypot(q.x - p.x, q.z - p.z) > 0.05 ? yawTo(p, q) : yawIn; };
    const skull = (t) => { const m = mobAt(t); return { x: m.x, y: t < tH2 + 0.3 ? 2.2 : 2.15, z: m.z }; };
    const cam = (t) => {
      // the start pose settles to the 1.62 m eye; the sound turns you toward the dark it came out of
      const k0 = sstep(0, 0.8, t);
      const c = { x: lerp(st.x, 0, k0), y: lerp(st.y, eye, k0), z: lerp(st.z, 0, k0), yaw: st.yaw, pitch: lerp(st.pitch, -0.03, k0), roll: 0, fov: st.fov, near: undefined };
      const yM = st.yaw + wrap(yawMob - st.yaw);
      c.yaw = lerp(st.yaw, yM, sstep(tLook, tLook1, t));
      // the eyes on it as it comes (a little)
      // backing away from it, a step at a time (the head dips and rocks with each), the eyes on it more
      if (t > tB0 && t < tRun + 0.2) {
        const p = runP.at(backU(Math.min(t, tRun))); c.x = p.x; c.z = p.z;
        for (const [i, b] of bSteps.entries()) { const k = (t - b.t) / b.dt; if (k > 0 && k < 1 && b.u0 < uBmax && b.t < tRun) { c.y -= 0.045 * Math.sin(Math.PI * k); c.roll += (i % 2 ? 1 : -1) * 0.022 * Math.sin(Math.PI * k); } }
        c.y += 0.006 * Math.sin((t - tB0) * Math.PI * 2 / 0.6) * sstep(tB0, tB0 + 0.5, t);   // (the breath)
      }
      if (t > tLook1 - 0.2 && t < tGo + 0.4) { const m = mobAt(t), ly = R.yawTo(c.x, c.z, m.x, m.z); const w = 0.5 * sstep(tLook1 - 0.2, tLook1 + 0.6, t) + 0.35 * sstep(tB0 - 0.1, tB0 + 0.5, t); c.yaw += w * wrap(ly - yM); c.pitch += 0.6 * w * (R.pitchTo(c.x, c.y, c.z, m.x, 1.8, m.z) + 0.03); }
      // the flight
      if (t >= tRun) {
        const u = uRunAt(t - tGo), p = runP.at(u);
        c.x = p.x; c.z = p.z;
        const yP = pathYaw(u), wy = sstep(tRun, tRun + 0.38, t);
        const base = c.yaw;
        const whip = lerp(base, runYaw0, wy);
        c.yaw = whip + wrap(yP - runYaw0) * sstep(tRun + 0.2, tGo + 0.5, t);
        c.pitch = lerp(c.pitch, -0.06, wy);
        const v = Math.min(V_RUN, (uRunAt(t - tGo + 0.05) - uRunAt(t - tGo - 0.05)) / 0.1);
        bob(c, u, 0.1 * clamp(v / 2));
        // the look back over the shoulder
        // (over the shoulder, and onto it: it is there, in the dark behind you)
        // the eyes find the low opening before you turn into it (not while you look back)
        const g = glK(t);
        const wM = sstep(straight - 2.6, straight - 1.2, u) * (1 - sstep(straight + 0.6, straight + 1.4, u)) * (1 - g);
        if (wM > 0) { const ly = R.yawTo(c.x, c.z, faceX, zA); c.yaw += 0.55 * wM * wrap(ly - c.yaw); c.pitch -= 0.08 * wM; }
        if (g > 0) { const m = mobAt(t), yb = c.yaw + glS * 2.7, ym = R.yawTo(c.x, c.z, m.x, m.z); c.yaw += g * (glS * 2.7 + clamp(wrap(ym - yb), -0.5, 0.5)); c.pitch += g * (clamp(R.pitchTo(c.x, c.y, c.z, m.x, 1.9, m.z), -0.2, 0.2) - c.pitch) * 0.7; }
        c.fov = st.fov + 9 * clamp(v / V_RUN);
      }
      // in: round to face the opening, and back away from it
      if (t >= tTurnA) {
        const k = sstep(tTurnA, tTurnA1, t), yA = pathYaw(runP.L - 0.01);
        c.yaw = lerp(yA, yA + wrap(yawOut - yA - 0.001 * d), k);
        const D = lerp(D1, D2, sstep(tTurnA1 - 0.1, tBk1, t)) + 0.12 * sstep(shoves[0], shoves[0] + 0.3, t), p = inA(D);
        c.x = p.x; c.z = p.z;
        c.pitch = lerp(c.pitch, -0.1, k);
        if (t > tTurnA1 - 0.1 && t < tBk1 + 0.1) c.y -= 0.03 * Math.abs(Math.sin((t - tTurnA1) * Math.PI / 0.38));
        // the eyes after it as it goes, a little; then the head goes down (relief)
        const m = mobAt(t);
        if (t > tAway) { const ly = R.yawTo(c.x, c.z, m.x, m.z); c.yaw += clamp(wrap(ly - c.yaw), -0.25, 0.25) * sstep(tAway, tAw0 + 0.3, t) * (1 - sstep(tGone, tGone + 0.6, t)); }
        c.pitch -= 0.2 * sstep(tGone, tGone + 1.2, t) * (1 - sstep(tDeep - 0.5, tDeep, t));
        c.y -= 0.05 * sstep(tGone, tGone + 1.2, t) * (1 - sstep(tDeep - 0.5, tDeep, t));
        c.fov = st.fov + 9 * (1 - sstep(tIn - 0.4, tIn + 0.3, t)) - 3 * sstep(shoves[0], tStill, t) * (1 - sstep(tGone, tGone + 1, t));
      }
      // deeper: round again, along the passage and out into the room; the ceiling goes up out of sight
      if (t >= tDeep) {
        const k = sstep(tDeep, tDeep1, t);
        const yOut = c.yaw;
        const u = t >= tWalk0 ? walkU(t) : 0, p = walkP.at(u), q = walkP.at(Math.min(walkP.L, u + 0.8));
        const yW = Math.hypot(q.x - p.x, q.z - p.z) > 0.05 ? yawTo(p, q) : yawTo(walkP.at(walkP.L - 0.9), walkP.at(walkP.L));
        c.yaw = lerp(yOut, yOut + wrap(yW - yOut + 0.001 * d), k);
        c.x = p.x; c.z = p.z;
        c.pitch = lerp(-0.1, -0.04, k) + 0.55 * sstep(tRoom - 0.2, tUp1, t) * (1 - sstep(tDown, tDown1, t));
        const v = t > tWalk0 && t < tWalk1 ? V_WALK : 0;
        bob(c, u, 0.07 * clamp(v));
        c.fov = st.fov;
      }
      // the scrape behind; the turn, onto it; it is there
      if (t >= tTurnK) {
        const e = 1 - Math.pow(1 - clamp((t - tTurnK) / (tRev - tTurnK)), 2.2);
        const y1 = c.yaw;
        c.yaw = y1 + wrap(yawK - y1) * e;
        const kh = sstep(tRev - 0.15, tRev + 0.4, t);
        c.x += kb.x * 0.1 * kh; c.z += kb.z * 0.1 * kh;   // (a start back from it)
        const sk = skull(t), lp = clamp(R.pitchTo(c.x, c.y, c.z, sk.x, sk.y, sk.z), -0.2, 0.75);
        c.pitch = lerp(c.pitch, lp - 0.05, sstep(tRev - 0.2, tRev + 0.5, t));
        c.near = 0.02;
      }
      // the blows: the head knocked round, back a step; down on the floor, the eyes on it
      if (t >= tH1 - 0.2) {
        const sk = skull(t), up2 = clamp(R.pitchTo(c.x, c.y, c.z, sk.x, sk.y, sk.z), -0.2, 0.75);
        c.pitch = lerp(c.pitch, up2, sstep(tH1 + 0.1, tH1 + 0.6, t));
        const kn = 0.35 * sstep(tH1, tH1 + 0.3, t); c.x += kb.x * kn; c.z += kb.z * kn;
        const kk = kick(t, hits.slice(0, 2).map((h) => ({ t: h.t, side: h.side, amp: 1.3 })).concat(hits.slice(2).map((h) => ({ t: h.t, side: h.side, amp: 0.4 }))));
        c.yaw += kk.yaw; c.pitch += kk.pitch;
        floorFall(c, t, tFl, { d: 0.5, side: dirT, roll: 0.55, y: 0.28, pitch: 0.95, back: 0.35 });
        if (t > tFloor) { const q = skull(t), ly = R.yawTo(c.x, c.z, q.x, q.z); c.yaw = lerp(c.yaw, c.yaw + wrap(ly - c.yaw) * 0.8, sstep(tFloor, tW1, t)); c.pitch = lerp(c.pitch, clamp(R.pitchTo(c.x, c.y, c.z, q.x, q.y, q.z) + 0.15, 0.5, 1.3), sstep(tFloor, tW1 + 0.3, t)); }
        c.fov = st.fov + 6 * pulse(t, [tH1, tH2, DUR], 0.15);
      }
      if (t >= tIn) c.near = 0.02;
      const amp = 0.0015 + 0.003 * sstep(tLook1, tRun, t) * (1 - sstep(tRun, tRun + 0.3, t)) + 0.012 * pulse(t, shoves, 0.14) * (t < tStill ? 1 : 0)
        + 0.002 * sstep(shoves[0], shoves[0] + 0.3, t) * (1 - sstep(tStill - 0.05, tStill, t)) - 0.0012 * sstep(tStill - 0.05, tStill, t) * (1 - sstep(tBack, tBack + 0.3, t))
        + 0.004 * sstep(tRev, tRev + 0.2, t) * (1 - sstep(tH1, tH1 + 0.1, t)) + 0.03 * pulse(t, [tH1, tH2, tFloor, DUR], 0.15) + 0.01 * pulse(t, [tW1, tW2], 0.12) + 0.004 * sstep(tH1, tH1 + 0.3, t);
      return shake(c, t, Math.max(0, amp), 6);
    };

    // ---- gore: from you, where the blows land ---------------------------------------------------------------------------
    const atC = (t, upY = 1.35, fwd = 0.2) => { const c = cam(t), f = { x: -Math.sin(c.yaw), z: Math.cos(c.yaw) }; return [c.x + f.x * fwd, Math.min(upY, c.y - 0.1), c.z + f.z * fwd]; };
    for (const [i, h] of hits.entries()) {
      const p = atC(h.t, i < 2 ? 1.35 : 0.3, i < 2 ? 0.3 : 0.45), side = h.side;
      const f = { x: -Math.sin(cam(h.t).yaw), z: Math.cos(cam(h.t).yaw) }, r = { x: f.z, z: -f.x };
      R.burst(h.t + 0.01, p, i < 2 || i === 4 ? 30 : 8, "blood", { dir: [r.x * side * 1.2 + f.x * 0.3, i < 2 ? 0.7 : 1.4, r.z * side * 1.2 + f.z * 0.3], speed: 2.4, spread: 0.6, size: 0.032, life: 1.3, stick: 3 });
      if (i === 0 || i === 4) R.burst(h.t + 0.02, p, 7, "bone", { dir: [r.x * side, 0.8, r.z * side], speed: 1.6, spread: 0.6, size: 0.03, life: 1.2, stick: 3 });
    }
    // grit off the lintel as its skull grinds it
    shoves.forEach((b, i) => R.burst(b + 0.03, [faceX + s * 0.08, 1.97, zA], 5 + 2 * i, "stone", { dir: [s * 0.3, -0.3, 0], speed: 0.4, spread: 0.4, size: 0.018, life: 1.1, grav: 9, stick: 0.6 }));

    // ---- the sound --------------------------------------------------------------------------------------------------------
    const lint = [faceX - s * 0.1, 2.15, zA];
    const sounds = [
      [tSay, "qf.mood.far_rattle", { at: (() => { const m = mobAt(tSay); return [m.x, 1.8, m.z]; })(), volume: 0.75 }],
      [tSay + 0.08, "mob.skeleton.say", { at: (() => { const m = mobAt(tSay); return [m.x, 2.0, m.z]; })(), volume: 0.6, pitch: 0.7 }],
      [tSay + 0.55, "qf.mood.scrape", { at: (() => { const m = mobAt(tSay + 0.55); return [m.x, 0.2, m.z]; })(), volume: 0.5, pitch: 0.85 }]
    ];
    // its steps (one each 1.67 m it walks, as an entity's) while it walks to the opening; the sword dragging on stone
    const tOfU = (u) => { if (u <= uR) return u <= uSq ? tMw + u / V_OUT : tMw + uSq / V_OUT + (u - uSq) / V_ON; let t = tRun; while (t < tMA && uMob(t) < u) t += 0.01; return t; };
    for (let u = STEP; u < chase.L - 0.2; u += STEP) { const t = tOfU(u); if (t < 0.05) continue; const p = chase.at(u); sounds.push([t, "mob.skeleton.step", { at: [p.x, 0.1, p.z], volume: clamp(0.55 + 0.4 * sstep(tRun, tMA, t), 0, 1), pitch: 0.82 }]); }
    // your steps back from it
    for (const b of bSteps) if (b.t < tRun - 0.1 && b.u0 < uBmax) sounds.push([b.t + b.dt * 0.6, "step.stone", { volume: 0.22, pitch: 0.9 }]);
    for (let t = Math.max(tM0 + 0.5, tSay + 1.4); t < tMA - 0.3; t += R.vary(1.15, 0.2)) { const p = mobAt(t); sounds.push([t, "qf.mood.scrape", { at: [p.x, 0.15, p.z], volume: 0.45 + 0.35 * sstep(tRun, tMA, t), pitch: 0.8 }]); }
    // your sprint: a step each 1.67 m
    for (let u = STEP * 0.5; u < runP.L - uP0 - 0.3; u += STEP) sounds.push([tGo + prof.tAt(u), "step.stone", { volume: 0.45, pitch: 1.0 }]);
    sounds.push(
      [tGl + 0.12, "mob.skeleton.say", { at: (() => { const m = mobAt(tGl + 0.12); return [m.x, 2.1, m.z]; })(), volume: 1.0, pitch: 0.62 }],
      [tIn - 0.35, "step.stone", { volume: 0.6, pitch: 0.85 }],
      [tBk1 - 0.4, "step.stone", { volume: 0.35, pitch: 0.9 }], [tBk1, "step.stone", { volume: 0.3, pitch: 0.9 }],
      [tMA - 0.05, "mob.skeleton.step", { at: [FA2.x, 0.1, FA2.z], volume: 0.9, pitch: 0.78 }]
    );
    shoves.forEach((b, i) => {
      sounds.push([b, "dig.stone", { at: lint, volume: 1.1, pitch: 0.5 + 0.04 * (i % 2) }], [b + 0.03, "qf.mood.scrape", { at: lint, volume: 0.85, pitch: 0.7 + 0.05 * i }], [b - 0.05, "mob.skeleton.step", { at: [FA2.x, 0.1, FA2.z], volume: 0.7, pitch: 0.8 }]);
      if (i === 1 || i === nSh - 1) sounds.push([b + 0.18, "mob.skeleton.say", { at: [FA2.x, 2.2, FA2.z], volume: 1.1, pitch: 0.55 }]);
    });
    sounds.push(silence(tStill, { fade: 0.25 }));
    sounds.push([tBack + 0.1, "mob.skeleton.step", { at: [FA3.x, 0.1, FA3.z], volume: 0.6, pitch: 0.8 }]);
    // its steps away: along the corridor, fainter; once it is in the way round, nothing
    for (let u = 0.6; u < away.L; u += STEP) { const p = away.at(u); if (s * (p.x - faceB) > 0.25) break; sounds.push([tAw0 + u / V_MOB, "mob.skeleton.step", { at: [p.x, 0.1, p.z], volume: 0.5 * (1 - u / 6), pitch: 0.82 }]); }
    // the calm: a breath out; your steps on, deeper
    for (let u = STEP * 0.5; u < walkP.L; u += STEP) { const T = walkP.L / V_WALK; let tt = tWalk0; for (let k = 0; k <= 200; k++) { const x = tWalk0 + (T + 0.35) * k / 200; if (walkU(x) >= u) { tt = x; break; } } sounds.push([tt, "step.stone", { volume: 0.22, pitch: 0.95 }]); }
    sounds.push(
      [tCue, "qf.mood.scrape", { at: [K.x, 0.2, K.z], volume: 0.3, pitch: 0.75 }],
      [tGoK, "mob.skeleton.say", { at: [K.x, 2.2, K.z], volume: 1.25, pitch: 0.58 }],
      [tGoK + 0.12, "mob.skeleton.step", { at: [K.x, 0.1, K.z], volume: 0.9, pitch: 0.75 }], [tH1 - 0.1, "mob.skeleton.step", { at: [S1.x, 0.1, S1.z], volume: 0.9, pitch: 0.75 }],
      ...blow(tH1, { volume: 1.2, gore: true }), [tH1 + 0.01, "qf.scare.crunch", { volume: 0.9 }],
      ...deathScream(tH1 + 0.12, { volume: 1.15, under: false }),
      [tH2 - 0.25, "mob.skeleton.say", { at: [S1.x, 2.2, S1.z], volume: 0.9, pitch: 0.55 }],
      ...blow(tH2, { volume: 1.1, gore: false }),
      [tFloor - 0.02, "game.player.hurt.fall.small", { volume: 1.0 }], [tFloor, "step.stone", { volume: 0.8, pitch: 0.7 }],
      [tH2 + 0.6, "mob.skeleton.step", { at: [S2.x, 0.1, S2.z], volume: 0.8, pitch: 0.75 }], [tW1 - 0.1, "mob.skeleton.step", { at: [S2.x, 0.1, S2.z], volume: 0.8, pitch: 0.7 }],
      [tW1, "game.player.hurt", { volume: 0.55 }], [tW2, "game.player.hurt", { volume: 0.55 }],
      [tUp, "mob.skeleton.say", { at: [S2.x, 2.2, S2.z], volume: 1.1, pitch: 0.5 }],
      ...blow(DUR, { volume: 1.2, gore: true }), [DUR + 0.01, "qf.scare.crunch", { volume: 1.0 }],
      [DUR, "game.player.die"], [DUR, "@muffle", { hz: 380, s: 3.2 }]
    );
    const loops = [
      [0.3, tStill, "qf.scare.drone", { volume: 0.4, fadeIn: 1.5, fadeOut: 0.3, pitch: 0.7, bus: "sfx" }],
      [tSay + 0.3, tRun, "qf.scare.heartbeat", { volume: 0.5, fadeIn: 0.4, fadeOut: 0.2 }],
      [tRun, tStill, "qf.scare.heartbeat", { volume: 0.7, pitch: 1.4, fadeIn: 0.1 }],
      [tB0 - 0.1, tRun + 0.35, "qf.scare.breath", { volume: 0.45, pitch: 1.12, fadeIn: 0.5, fadeOut: 0.3 }],   // (it comes on you)
      [tRun + 0.2, tStill, "qf.scare.breath", { volume: 0.6, pitch: 1.3, fadeIn: 0.3 }],
      // the calm: the heart slows, the breath goes out of you and settles
      [tGone + 0.2, tDeep + 0.4, "qf.scare.breath", { volume: 0.42, pitch: 0.8, fadeIn: 0.5, fadeOut: 1.2 }],
      [tGone, tRev, "qf.scare.heartbeat", { volume: 0.32, pitch: 0.88, fadeIn: 0.8, fadeOut: 0.05 }],
      [tRev, DUR + 0.2, "qf.scare.heartbeat", { volume: 0.7, pitch: 1.45, fadeIn: 0.05 }],
      [tFloor, DUR, "qf.scare.breath", { volume: 0.5, pitch: 0.9, fadeIn: 0.3 }]
    ];

    // ---- the frame ------------------------------------------------------------------------------------------------------
    // the corridor's torchlight down the way round, behind it (it reads black against it)
    const lightB = R.ownLight(R.light(0xffb070, 0, 7, 1.2)); R.at(lightB, faceX + s * (LA - 1.1), 2.2, zB);
    function update(t, f) {
      const cl = R.toLocal(R.camera.position);
      const m = mobAt(t);
      let lookP = 0, face = m.yaw, walk = m.moving ? 1.4 : 0;
      // in the opening: its body pushed into the gap, its skull against the lintel, the arms and the sword in at you
      let push = 0, reach = 0, raise = 0, chop = 0;
      if (t >= tMA && t < tBack) {
        push = shoves.reduce((a, b) => a + (t >= b ? Math.sin(Math.min(1, (t - b) / 0.1) * Math.PI / 2) * Math.exp(-Math.max(0, t - b - 0.1) / 0.22) : 0), 0);
        reach = sstep(tMA - 0.1, tMA + 0.25, t);
        const ph = shoves.map((b) => clamp((t - b + 0.3) / 0.6)).find((k) => k > 0 && k < 1) ?? 0;
        raise = ph > 0 ? Math.sin(Math.PI * Math.min(1, ph * 1.6)) * (ph < 0.62 ? 1 : 0) : 0;
        chop = ph >= 0.5 ? 1 - sstep(0.62, 1, ph) : 0;
      }
      const still = t >= tStill && t < tBack;
      let x = m.x + (t >= tMA && t < tBack ? s * 0.12 * Math.min(1, push) : 0), z = m.z;
      if (t >= tBack && t < tAway) lookP = 0.5 * sstep(tBack + 0.1, tPeek, t);
      if (t >= tAway && t < tAw0) lookP = 0.5 * (1 - sstep(tAway, tAw0, t));
      if (t >= tKarr && t < tGoK) { walk = 0; }
      if (t >= tGoK) { face = R.yawTo(m.x, m.z, cl.x, cl.z); lookP = t < tH1 ? 0.25 : 0.55 * sstep(tH1 + 0.15, tH1 + 0.6, t) + (t > tH2 + 0.3 ? 0.35 * sstep(tH2 + 0.3, tW1, t) : 0); }
      R.place(W, x, 0, z, face, t >= tMA && t < tBack ? 0.08 * Math.min(1, push) : 0);
      // (its legs swing with the distance it walks; frozen while it stands still)
      const animT = t >= tKarr && t < tGoK ? 0 : m.dist * 0.57;
      W.anim(animT, 0, { walk: still || (t >= tKarr && t < tGoK) ? 0 : walk, lookPitch: lookP, still: t >= tKarr && t < tGoK });
      if (t >= tMA && t < tBack && W.parts.rightArm) {
        // both arms in through the opening; the sword arm hacks with each shove (frozen where it was in the stillness)
        const tt = still ? tStill : t;
        const rp = still ? 0 : raise, cp2 = still ? 0.5 : chop;
        mcRot(W.parts.leftArm, lerp(0, -1.45, reach) + 0.05 * Math.sin(tt * 9), -0.1, 0);
        mcRot(W.parts.rightArm, rp > 0.001 ? lerp(-1.3, -2.6, rp) : lerp(-1.3, -0.9, cp2) * reach + (1 - reach) * -0.3, 0.1, 0);
      }
      const sw = swingAt(t, [tH2 - 0.15], 0.3);
      const raise2 = Math.max(sstep(tGoK, tH1 - 0.14, t) * (1 - sstep(tH1 - 0.14, tH1, t)), sstep(tUp, tUp + 0.3, t) * (1 - sstep(DUR - 0.14, DUR, t)));
      const chop2 = Math.max(t >= tH1 - 0.14 && t < tH1 + 0.35 ? 1 - sstep(tH1 + 0.1, tH1 + 0.35, t) : 0, t >= DUR - 0.14 ? 1 : 0);
      if (t >= tGoK) {
        bipedSwing(W, sw);
        if (W.parts.rightArm && (raise2 > 0 || chop2 > 0)) mcRot(W.parts.rightArm, raise2 > 0.001 ? lerp(-0.3, -2.75, raise2) : lerp(-0.3, -0.55, chop2), 0.1, raise2 > 0.001 ? 0.5 * Math.sin(Math.PI * Math.min(1, raise2 * 1.4)) + 0.15 * raise2 : 0);
      }
      W.pivot.visible = true;
      // its light: the bake where it stands (black bone; a little more on it when it is on you)
      const env = envAt(t);
      W.setOwn(clamp(0.55 * lightAt(m.x, m.z) * env.bake + (t >= tH1 - 0.2 ? 0.05 : 0), 0.012, 0.4));
      // the torchlight of the corridor down the way round
      lightB.intensity = 2.2 * sstep(tGone, tDeep, t) * (1 - 0.5 * sstep(tFloor, DUR, t));
      f.env = env;
      f.hpMode = t >= tH1 ? "wither" : "normal";
      const dark = sstep(tFloor, DUR + 0.4, t), room = sstep(tRoom - 0.5, tRoom + 1.5, t);
      f.vig = [0, 0, 0, Math.min(1, 0.22 + 0.12 * sstep(tLook1, tRun, t) + 0.15 * sstep(shoves[0], tStill, t) * (1 - sstep(tGone, tDeep, t)) + 0.15 * room + 0.4 * dark)];
      f.vigR = 0.9 - 0.35 * dark;
      f.tints = [[0, 0, 0, 0.18 * sstep(tH1, tH1 + 0.5, t) + 0.25 * dark]];
      f.splats = [hits[0], hits[1], hits[4]].filter((h) => t >= h.t).map((h, i) => ({ t0: h.t, x: [0.66, 0.3, 0.5][i], y: [0.42, 0.55, 0.35][i], r: [11, 10, 14][i], seed: 61 + i }));
      f.black = 0.5 * sstep(DUR - 0.1, DUR + 0.6, t);
    }
    function envAt(t) {
      const dark = sstep(tFloor, DUR + 0.4, t), room = sstep(tRoom - 0.5, tRoom + 1.5, t), dread = sstep(0.3, tRun, t);
      return { bake: 1 - 0.12 * dread * (1 - sstep(tRun, tIn, t)) - 0.1 * room - 0.3 * dark, lights: 1 - 0.1 * dread - 0.15 * room - 0.35 * dark, fogMul: 1 + 0.4 * dread + 0.3 * room + 1.2 * dark };
    }
    const r2 = (v) => +v.toFixed(2);
    // (held: the hand is not drawn in this one, so the hotbar has the empty slot selected; loadout.js, round 8b)
    return { dur: DUR, hits, cam, update, sounds, loops, deathSide: dirT, held: null,
      marks: { dread: tRun - 0.4, fake: tGone + 1.2, lunge: tH1, kill: tH2 + 0.6, see: tLook1 + 0.5, freeze: tF0 + 0.25, back: tB0 + 0.55, run: tRun, glance: tGl + 0.3, dive: tIn, push: shoves[1] ?? shoves[0], still: tStill + 0.6, peek: tPeek + 0.2, away: tAw0 + 0.3, room: tUp1, cue: tCue, reveal: tRev, go: tGoK },
      notes: { d, s, hid0, kA: Lay.kA, dB: Lay.dB, aw: Lay.aw, awB: Lay.awB, kM: Lay.kM, room: [LA, RW, RH], tries, remesh: Lay.nm, carveT, face: r2(faceX), zA: r2(zA), zB: r2(zB), pre: pre.length ? 1 : 0, gapF: r2(gapAt(tF0)), gapRun: r2(gapAt(tRun)), uBack: r2(uP0), vCh: r2(V_CH), lead: r2(tMA - tIn), tF0: r2(tF0), tB0: r2(tB0),
        K: [r2(K.x), r2(K.z)], PR: [r2(PR.x), r2(PR.z)], carveMs: Math.round(R.carveMs || 0), tRun: r2(tRun), tGl: r2(tGl), tIn: r2(tIn), tMA: r2(tMA), tStill: r2(tStill), tBack: r2(tBack), tAway: r2(tAway), tGone: r2(tGone), tKarr: r2(tKarr), tRoom: r2(tRoom), tCue: r2(tCue), tRev: r2(tRev), tH1: r2(tH1), dur: r2(DUR) } };
  }
};
