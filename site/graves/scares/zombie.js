// Zombie (round 8: the door; round 8b: and you run). In 1.7.10 a zombie breaks wooden doors (EntityAIBreakDoor: it
// beats on the door, mob.zombie.wood, the crack grows over the block, and the door goes with mob.zombie.woodbreak and a
// burst of its bits). Here a wooden door is set in the crypt wall beside and behind you, where you could not see it
// when you stopped, with a dark passage behind it.
// BANG. You flinch and turn to it: a door. It judders on its hinges with every blow, grit sifts from the lintel, the
// crack spreads over it, a groan comes through it. You back away from it, step by step; the blows come faster. It
// breaks: the zombie lurches out through the bits of the door, arms out. You stumble back, turn and run (the owner,
// round 8b: "the player should try to back up and run from the zombies instead of just standing still"): the sprint,
// the head bobbing, the breath ragged; you look back once and it is coming. A zombie is slower than a running man, so
// it does not catch you: the corridor does. Zombies come in numbers: two more step out of the dark ahead, out of a side
// way or round the corner, and you skid to a stop between them (or, with nowhere to run, the corridor ends and your
// back is to the wall). You turn back and it is on you: its hands on your shoulders, it pulls you in and bites into
// your neck; you are dragged down, it bites again, and the others close over you until their hands cover the view.
// (If no wall spot fits a door, it comes out of the dark of the corridor behind you: the groan, the turn, the walk.)
import { THREE, track, clamp, lerp, sstep, pulse } from "./rig.js";
import { settle, shake, hitsOf, lensLimbs, zombieArms } from "./common.js";
import { splitJaw, boxOf, silence, deathScream } from "./fnaf.js";
import { roar, blow, kick } from "./story.js";
import { wallDoor } from "./door.js";
import { blocks, startView, sideSpots, poly, runProfile, bob, STEP } from "./chase.js";

const V_RUN = 5.2, V_Z = 2.3, V_O = 1.9;

export default {
  death: "Steve was slain by Zombie",
  async build(R) {
    const eye = R.eye;
    // ---- the door: beside and behind you, out of frame at the freeze ---------------------------------------------
    let D = await wallDoor(R, { zMin: -1.5, zMax: -0.3, avoidTorch: 0.55 });
    if (!D) D = await wallDoor(R, { zMin: -2.6, zMax: 0.4, avoidTorch: 0.55 });
    const hasDoor = !!D;
    // without a door: the dark of the corridor behind you
    const G = hasDoor ? { x: D.face, z: D.z } : { x: -0.6, z: -Math.min(7, R.behind - 1) };
    const side = hasDoor ? D.side : -1;
    const inX = (x) => clamp(x, -(R.wallL - 0.35), R.wallR - 0.35);
    const wrap = (a) => Math.atan2(Math.sin(a), Math.cos(a));

    // ---- the dice -----------------------------------------------------------------------------------------------
    const b1 = 1.05 + R.vary(0.35, 0.4);
    const bangs = [b1, b1 + R.vary(1.15, 0.12)];
    for (const gap of [0.85, 0.68, 0.52, 0.42]) bangs.push(bangs[bangs.length - 1] + R.vary(gap, 0.15));
    if (!hasDoor) bangs.length = 1;   // (no door: the one groan out of the dark)
    const tBreak = hasDoor ? bangs[bangs.length - 1] + R.vary(0.38, 0.2) : b1 + 3.0;
    const tT0 = b1 + 0.1, tT1 = tT0 + 0.5;                          // the startled turn to the door
    // Backing away from it: away from the door, as far as the corridor lets you (at most 1.2 m).
    const ax = -G.x, az = -G.z * 0.35, an = Math.hypot(ax, az) || 1;
    const bx = ax / an, bz = az / an;
    const room = R.ray(0, 1.0, 0, bx, 0, bz, 4);
    const dd = Math.hypot(G.x, G.z), want = clamp(4.0 - dd, 0.45, 1.2);
    const back = clamp(Math.min(room - 0.6, want), 0, 1.2), pinned = room - 0.6 < want;
    const tBk0 = (bangs[1] ?? b1 + 1.2) + 0.3, tBk1 = Math.min(tBreak - 0.1, tBk0 + 0.55 * Math.max(1, Math.ceil(back / 0.45)));
    const P1 = { x: bx * back, z: bz * back };                      // where the backing leaves you

    // ---- the flight: a stumble back as it comes through, then down the corridor away from the door ---------------
    const B = blocks(R), seen0 = startView(R);
    const stumble = clamp(R.ray(P1.x, 1.0, P1.z, bx, 0, bz, 2) - 0.45, 0, 0.45);
    const run0 = { x: P1.x + bx * stumble, z: P1.z + bz * stumble };
    const xr = clamp(run0.x * 0.4, -(R.wallL - 0.6), R.wallR - 0.6);
    const free = R.ray(xr, 1.0, run0.z, 0, 0, 1, 20);
    // where it ends: the others step out ahead of you (out of a side way, an alcove, round the corner), or come out of
    // the dark of a long corridor; with nowhere to run, the corridor's end (your back to the wall)
    let mode = "end", spot = null, PS = null;
    // (and out of sight of you as you run, until they move: they step out in front of you, they do not stand waiting)
    const hfz = Math.atan(Math.tan(THREE.MathUtils.degToRad(R.start.fov) / 2) * (R.camera.aspect || 16 / 9)) + 0.12;
    // (from px,pz with the yaw anywhere in [y0, y1]: in frame and in line of sight; a zombie faces you, so its arms
    // reach 0.7 m out toward the eye)
    const armTo = (c, px, pz) => { const n = Math.hypot(px - c.x, pz - c.z) || 1; return [c.x + (px - c.x) / n * 0.7, 1.35, c.z + (pz - c.z) / n * 0.7]; };
    const outline = (c, px, pz) => {   // (its edges as the eye sees them: either side, head to foot, and the arms)
      const n = Math.hypot(px - c.x, pz - c.z) || 1, ux = (px - c.x) / n, uz = (pz - c.z) / n, ex = -uz * 0.3, ez = ux * 0.3;
      const pts = [[c.x, 1.0, c.z]];
      for (const y of [0.3, 1.1, 1.9]) pts.push([c.x + ex, y, c.z + ez], [c.x - ex, y, c.z - ez]);
      for (const k of [-0.8, 0, 0.8]) pts.push([c.x + ux * 0.7 + ex * k, 1.35, c.z + uz * 0.7 + ez * k]);
      return pts;
    };
    const sees = (px, pz, c, y0, y1) => {
      for (const [x, y, z] of outline(c, px, pz)) {
        const a = R.yawTo(px, pz, x, z);
        if (a < Math.min(y0, y1) - hfz || a > Math.max(y0, y1) + hfz) continue;
        const n = Math.hypot(x - px, y - eye, z - pz); let open = true;
        for (let r = 0.1; r < n - 0.1; r += 0.05) if (R.solid(px + (x - px) * r / n, eye + (y - eye) * r / n, pz + (z - pz) * r / n)) { open = false; break; }
        if (open) return true;
      }
      return false;
    };
    // backing off with the eyes on the door, the whip round from it to the run, the run itself
    const seenRunning = (c, z1, late = true) => {
      const yD = R.yawTo(P1.x, P1.z, G.x, G.z), yR = R.yawTo(run0.x, run0.z, G.x, G.z), y0 = R.start.yaw || 0;
      if (sees(0, 0, c, Math.min(y0, 0) - 0.05, Math.max(y0, 0) + 0.05)) return true;   // (the opening settle)
      if (sees(0, 0, c, yD - 0.2, yD + 0.2) || sees(P1.x, P1.z, c, yD - 0.2, yD + 0.2)) return true;
      if (sees(run0.x, run0.z, c, yR + 0.15 * Math.sign(yR), 0)) return true;
      for (const cz of late ? [run0.z, (run0.z + z1) / 2, z1] : [run0.z, (run0.z + z1) / 2]) if (sees(xr, cz, c, 0, 0)) return true;
      return false;
    };
    // how far out of its hiding place a zombie walks before it could be seen before you come level
    const hidLen = (a, b, z1) => {
      const L = Math.hypot(b.x - a.x, b.z - a.z);
      for (let l = 0.15; l < L; l += 0.15) if (seenRunning({ x: lerp(a.x, b.x, l / L), z: lerp(a.z, b.z, l / L) }, z1, false)) return l - 0.15;
      return L;
    };
    for (const q of sideSpots(R, B, seen0, { dir: 1, kMin: Math.max(3, Math.ceil(run0.z + 4.2)), kMax: 11, want: run0.z + 6.5 })) {
      const zS = q.c.z - 2.4;
      if (zS - run0.z < 2.0 || free < zS - run0.z + 0.6) continue;
      if (seenRunning(q.c, zS - 2.6) || (q.c2 && seenRunning(q.c2, zS - 2.6))) continue;
      if ([q.c, q.c2].some((c) => c && seen0(...armTo(c, 0, 0)))) continue;   // (its arms in the first frame)
      spot = q; PS = { x: xr, z: zS }; mode = "ahead"; break;
    }
    if (!spot) {
      // (down a long corridor they are there as you turn: a stride or two and you pull up)
      if (free >= 9) { mode = "dark"; PS = { x: xr, z: run0.z + Math.min(1.8, free - 4.5) }; }
      else PS = { x: xr, z: run0.z + Math.max(0.6, free - 0.75) };
    }
    const runP = poly([run0, { x: lerp(run0.x, xr, 0.7), z: run0.z + Math.min(0.8, (PS.z - run0.z) * 0.4) }, PS]);
    const prof = runProfile(runP.L, { v: V_RUN, accel: 0.4, brake: mode === "ahead" ? 10 : 8 });
    const tSt1 = tBreak + 0.5;                                        // the stumble
    const tTurnR = tBreak + R.vary(0.72, 0.1), tGo = tTurnR + 0.12, tStop = tGo + prof.dur;
    const tGlz = tGo + prof.tAt(Math.min(1.1, runP.L * 0.3)), glLen = 0.6;
    const tSee = mode === "ahead" ? tGo + prof.tAt(Math.max(0, runP.L - 2.6)) : mode === "dark" ? tGo + 0.15 : tStop - 0.4;   // you see them
    const tBackR = tStop + (mode === "end" ? 0.15 : 0.5), tBackR1 = tBackR + 0.42;   // you turn back to it

    // The zombie's way: out of the passage, through the doorway, after you (or out of the dark behind).
    const A0 = hasDoor ? D.in(1.9) : { x: G.x, z: G.z }, A1 = hasDoor ? D.in(-0.35) : { x: G.x * 0.6, z: G.z + 0.8 };
    // (where you stand when it takes you: half a step back from the ones ahead)
    const PK = { x: PS.x, z: PS.z - (mode === "end" ? 0 : 0.3) };
    const toP = { x: PK.x - A1.x, z: PK.z - A1.z }, dP = Math.hypot(toP.x, toP.z) || 1;
    const reach = 0.85;
    const A2 = { x: PK.x - toP.x / dP * reach, z: PK.z - toP.z / dP * reach };
    const L1 = Math.hypot(A1.x - A0.x, A1.z - A0.z), L2 = Math.max(0, dP - reach), SPD = 2.8;
    const tOut = tBreak + 0.05, tA1 = tOut + L1 / (SPD * 0.85);
    // it does not catch a running man: it reaches you when you have stopped and turned back to it
    const tGrab = Math.max(tA1 + L2 / V_Z, tBackR1 + 0.12);
    const tK = tGrab + 0.3, T_DRAG = tK + 1.25, DUR = tK + 3.4;
    const zAt = (t) => {   // the first one's floor position
      if (t <= tOut) return { x: A0.x, z: A0.z };
      if (t <= tA1) { const k = (t - tOut) / (tA1 - tOut); return { x: lerp(A0.x, A1.x, k), z: lerp(A0.z, A1.z, k) }; }
      const k = clamp((t - tA1) / Math.max(0.05, tGrab - tA1)); return { x: lerp(A1.x, A2.x, k), z: lerp(A1.z, A2.z, k) };
    };
    // The attack's frame: forward toward it at the grab, x to its right.
    const yK = R.yawTo(PK.x, PK.z, A2.x, A2.z);
    const fK = { x: -Math.sin(yK), z: Math.cos(yK) }, rK = { x: Math.cos(yK), z: Math.sin(yK) };
    const inK = (x, z) => ({ x: inX(PK.x + rK.x * x + fK.x * z), z: PK.z + rK.z * x + fK.z * z });

    // ---- the mobs -----------------------------------------------------------------------------------------------
    const z1 = R.mob("Zombie", { amb: [0.2, 0.2, 0.2], own: true });
    const jaw = splitJaw(z1, [{ part: z1.parts.head, box: boxOf("zombie", "bipedHead"), rows: 2 }, { part: z1.parts.headwear, box: boxOf("zombie", "bipedHeadwear"), rows: 2 }]);
    // (the jaw's teeth, tongue and mouth are flat colours: lit here like the rest of its head, or they glow in the dark)
    const jawBase = Object.fromEntries(Object.entries(jaw.mats).map(([k, m]) => [k, m.color.clone()]));
    const lightJaw = (k) => { for (const [n, m] of Object.entries(jaw.mats)) m.color.copy(jawBase[n]).multiplyScalar(k); };
    z1.anim(0, 0, { walk: 0 }); R.place(z1, A0.x, 0, A0.z, 0);
    // two more: ahead of you (out of their side way, or out of the dark down the corridor), or after it out of the passage
    const mk = () => R.mob("Zombie", { amb: [0.2, 0.2, 0.2] });
    let others;
    if (mode === "ahead") {
      const c2 = spot.c2 || spot.c, mid = (c, dx) => ({ x: clamp(xr + dx, -(R.wallL - 0.5), R.wallR - 0.5), z: c.z - 0.3 });
      others = [
        // (they step out as you come level: out of their dark into your way; from deep in a side way they were already
        // coming at the noise, out of sight until then)
        { m: mk(), from: spot.c, mid: mid(spot.c, 0.45 * spot.sd), to: inK(-0.75, -0.7), t0: tSee - 0.2, lean: -0.5, vis0: 0 },
        { m: mk(), from: c2, mid: mid(c2, -0.4 * spot.sd), to: inK(0.8, -0.55), t0: tSee + (spot.c2 ? 0.25 : 0.9), lean: -0.5, vis0: 0 }
      ];
      for (const q of others) { q.hid = Math.max(0, hidLen(q.from, q.mid, PS.z - 2.6) - 0.3); q.t0 -= q.hid / V_O; }   // (a margin: no sliver of them before)
    } else if (mode === "dark") {
      // far down the corridor in the dark, where the first frame could not make them out; they are only drawn once the
      // head has turned to the door (they were further off still, walking up)
      const zF = (dz) => ({ x: xr + dz, z: PS.z + 2.6 + V_O * 0.75 * (tStop - tT1 - 0.2) });
      others = [
        { m: mk(), from: zF(0.45), mid: { x: xr + 0.45, z: PS.z + 2.6 }, to: inK(-0.75, -0.7), t0: tT1 + 0.2, lean: -0.5, vis0: tT1 + 0.2, slow: 0.75 },
        { m: mk(), from: zF(-0.5), mid: { x: xr - 0.5, z: PS.z + 3.3 }, to: inK(0.8, -0.55), t0: tT1 + 0.2, lean: -0.5, vis0: tT1 + 0.2, slow: 0.75 }
      ];
    } else {
      others = [
        { m: mk(), from: hasDoor ? D.in(2.45) : { x: G.x + 0.5, z: G.z - 1.2 }, mid: hasDoor ? D.in(-0.4) : null, to: inK(-0.8, 0.4), t0: tBreak + 0.9, lean: -0.5, vis0: 0 },
        { m: mk(), from: hasDoor ? D.in(3.3) : { x: G.x - 0.4, z: G.z - 2.2 }, mid: hasDoor ? D.in(-0.4) : null, to: inK(0.85, 0.25), t0: tBreak + 1.7, lean: -0.5, vis0: 0 }
      ];
      for (const q of others) if (!q.mid) q.mid = q.from;
    }
    others.forEach((q, i) => {
      const v = V_O * (q.slow || 1);
      q.l1 = Math.hypot(q.mid.x - q.from.x, q.mid.z - q.from.z); q.l2 = Math.hypot(q.to.x - q.mid.x, q.to.z - q.mid.z);
      q.v = v; q.tOut = q.t0 + q.l1 / v;
      // (they close in once it has you, not before: a zombie's shamble, slower if they are early)
      q.v2 = mode === "end" ? V_O : Math.min(V_O, q.l2 / Math.max(0.3, tGrab + 0.55 + 0.5 * i - q.tOut));
      q.tArr = q.tOut + q.l2 / q.v2;
    });
    // (out of the passage they are in its dark until the doorway; ahead, in the dark of their side way)
    const othersAt = (q, t) => {
      const u = Math.max(0, t - q.t0);
      if (u * q.v < q.l1) { const k = (u * q.v) / Math.max(0.01, q.l1); return { x: lerp(q.from.x, q.mid.x, k), z: lerp(q.from.z, q.mid.z, k), out: k }; }
      const k = Math.min(1, (u - q.l1 / q.v) * q.v2 / Math.max(0.01, q.l2)); return { x: lerp(q.mid.x, q.to.x, k), z: lerp(q.mid.z, q.to.z, k), out: 1 };
    };
    const faceL = R.ownLight(R.light(0xffb070, 0, 2.4, 1.4));

    // ---- the head -----------------------------------------------------------------------------------------------
    const hits = hitsOf([[tK + 0.02, 5, 1], [tK + 0.6, 5, -1], [tK + 1.15, 3, 1], [tK + 2.3, 4, -1], [tK + 2.95, 3, 1]]);
    const doorC = { x: G.x - side * 0.1, y: 1.05, z: G.z };
    const neck = (t) => sstep(tGrab, tK - 0.05, t) * (1 - sstep(T_DRAG, T_DRAG + 0.6, t));   // its teeth in your neck
    const posAt = (t) => { const k = sstep(tBk0, tBk1, t); return { x: P1.x * k, z: P1.z * k }; };
    const headZ = (t, out = {}) => { const q = zAt(t); out.x = q.x; out.y = 1.62; out.z = q.z; return out; };
    const yawTo2 = (c, q) => R.yawTo(c.x, c.z, q.x, q.z);
    const pathYaw = (u) => { const p = runP.at(u), q = runP.at(Math.min(runP.L, u + 0.8)); return Math.hypot(q.x - p.x, q.z - p.z) > 0.05 ? R.yawTo(p.x, p.z, q.x, q.z) : 0; };
    // (a dash too short for it: the look back is the turn back to it at the stop)
    const glK = (t) => (runP.L < 2.5 ? 0 : sstep(tGlz, tGlz + 0.18, t) * (1 - sstep(tGlz + glLen - 0.18, tGlz + glLen, t)));
    const glS = side > 0 ? 1 : -1;   // (over the shoulder on the door's side: where it is)
    // a half step back from the ones ahead, as you turn
    const stepBack = (t) => (mode === "end" ? 0 : 0.3 * sstep(tStop + 0.1, tBackR1, t));
    const cam = (t) => {
      const s = settle(R, t, 0.9);
      const k = sstep(0.8, 1.3, t), p = posAt(t);
      const c = { x: lerp(s.x, p.x, k), y: lerp(s.y, eye, k), z: lerp(s.z, p.z, k), yaw: lerp(s.yaw, 0, k), pitch: lerp(s.pitch, -0.02, k), roll: 0, fov: s.fov, near: t >= tBreak ? 0.02 : undefined };
      // the turn to the door, and the eyes on it while you back away
      const ty = sstep(tT0, tT1, t), aimD = { y: yawTo2(c, doorC), p: R.pitchTo(c.x, c.y, c.z, doorC.x, doorC.y, doorC.z) };
      c.yaw = lerp(c.yaw, c.yaw + wrap(aimD.y - c.yaw), ty); c.pitch = lerp(c.pitch, clamp(aimD.p, -0.45, 0.2), ty);
      // backing: a step every ~0.5 s, the head dipping with each
      if (t > tBk0 && t < tBk1 + 0.1) c.y -= 0.035 * Math.abs(Math.sin((t - tBk0) * Math.PI / 0.5));
      if (pinned) c.y -= 0.02 * pulse(t, [tBk1], 0.12);
      // From the break: on it as it comes through; a stumble back from it
      let fov = 0;
      if (t >= tBreak - 0.05) {
        const q = headZ(Math.min(t, tTurnR + 0.1)), w = sstep(tBreak - 0.05, tBreak + 0.3, t);
        const ly = yawTo2(c, q), lp = clamp(R.pitchTo(c.x, c.y, c.z, q.x, 1.55, q.z), -0.3, 0.25);
        c.yaw = lerp(c.yaw, c.yaw + wrap(ly - c.yaw), w); c.pitch = lerp(c.pitch, lp, w);
        const ks = sstep(tBreak, tSt1, t); c.x = lerp(c.x, run0.x, ks); c.z = lerp(c.z, run0.z, ks);
        c.y -= 0.05 * Math.sin(Math.PI * clamp((t - tBreak) / 0.5)) + 0.03 * Math.sin(Math.PI * clamp((t - tBreak - 0.22) / 0.3));
      }
      // the flight: turn, sprint; one look back at it; the ones ahead; the stop
      if (t >= tTurnR) {
        const u = prof.u(t - tGo), p = runP.at(u);
        c.x = p.x; c.z = p.z;
        const wy = sstep(tTurnR, tTurnR + 0.32, t), yP = pathYaw(u);
        c.yaw = lerp(c.yaw, c.yaw + wrap(yP - c.yaw), wy);
        c.pitch = lerp(c.pitch, -0.05, wy);
        const v = Math.min(V_RUN, (prof.u(t - tGo + 0.05) - prof.u(t - tGo - 0.05)) / 0.1);
        bob(c, u, 0.1 * clamp(v / 2));
        fov += 9 * clamp(v / V_RUN);
        const g = glK(t);
        if (g > 0) { const q = zAt(t), yb = c.yaw + glS * 2.7, ym = R.yawTo(c.x, c.z, q.x, q.z); c.yaw += g * (glS * 2.7 + clamp(wrap(ym - yb), -0.5, 0.5)); }
        // the braking: the head goes on a little and comes back
        c.pitch -= 0.1 * pulse(t, [tStop - 0.12], 0.18);
        // ahead: the eyes on them as they come out
        if (mode !== "end") {
          const q = othersAt(others[0], Math.max(t, tSee)), w2 = sstep(tSee, tSee + 0.3, t) * (1 - sstep(tBackR, tBackR1, t));
          c.yaw += 0.7 * w2 * wrap(R.yawTo(c.x, c.z, q.x, q.z) - c.yaw);
        }
      }
      // round to it: it is there
      if (t >= tStop) {
        c.z -= stepBack(t);
        const q = headZ(Math.min(t, tGrab)), w3 = sstep(tBackR, tBackR1, t);
        c.yaw = lerp(c.yaw, c.yaw + wrap(yawTo2(c, q) - c.yaw), w3);
        c.pitch = lerp(c.pitch, clamp(R.pitchTo(c.x, c.y, c.z, q.x, 1.55, q.z), -0.3, 0.25), w3);
      }
      // the kill: pulled in, bitten, dragged down under them
      if (t >= tGrab) {
        const nb = neck(t);
        // the head thrown back and aside as it goes for the throat: its face low in the view, biting down
        c.yaw += 0.14 * nb; c.pitch += 0.2 * nb + 0.08 * pulse(t, hits.slice(0, 3).map((h) => h.t), 0.15); c.roll -= 0.08 * nb;
        const kk = kick(t, hits.map((h) => ({ t: h.t, side: h.side, amp: 0.9 })));
        const pl = track([[tGrab, 0], [tK, 0.06, "i"], [tK + 0.4, 0.03], [T_DRAG, 0.05], [tK + 2.1, -0.3, "i"], [DUR, -0.35]])(t);
        c.x += fK.x * pl; c.z += fK.z * pl; c.yaw += kk.yaw; c.pitch += kk.pitch;
        c.y = lerp(c.y, 0.3, sstep(T_DRAG, tK + 2.15, t) ** 1.6);
        c.pitch = lerp(c.pitch, 1.25, sstep(T_DRAG + 0.2, tK + 2.3, t));
        c.roll += 0.32 * sstep(T_DRAG, tK + 2.9, t) * -side;
        c.near = 0.02;
      }
      c.fov = s.fov + fov + 4 * pulse(t, [tBreak], 0.2) + 3 * pulse(t, [tK], 0.12) - 3 * sstep(tT1, tBreak, t) * (1 - sstep(tBreak, tBreak + 0.3, t)) + 3 * pulse(t, [tSee + 0.15], 0.25);
      const amp = 0.002 + 0.004 * sstep(b1, tBreak, t) * (1 - sstep(tGo, tGo + 0.3, t)) + 0.018 * pulse(t, bangs, 0.14) * (t < tBreak + 0.1 ? 1 : 0) + 0.03 * pulse(t, [b1, tBreak], 0.16)
        + 0.004 * sstep(tStop, tStop + 0.2, t) + 0.02 * pulse(t, [tGrab, ...hits.map((h) => h.t)], 0.2) + 0.012 * sstep(T_DRAG, T_DRAG + 0.5, t);
      return shake(c, t, amp, 3);
    };

    // ---- gore -------------------------------------------------------------------------------------------------
    hits.forEach((h, i) => {
      const up = i < 3, at = (x, y, z) => { const q = inK(x, z); return [q.x, y, q.z]; };
      R.burst(h.t, at(up ? 0.28 : 0.1 * (i % 2 ? -1 : 1), up ? 1.4 : 0.25, up ? 0.45 : 0.5), 30, "blood", { dir: up ? [rK.x * 1.0 + fK.x * 0.4, 0.9, rK.z * 1.0 + fK.z * 0.4] : [fK.x * 0.4, 1.3, fK.z * 0.4], speed: 2.3, spread: 0.6, size: 0.03, life: 1.3, stick: 3 });
      R.burst(h.t + 0.02, at(up ? 0.25 : 0, up ? 1.38 : 0.3, up ? 0.5 : 0.5), 8, "flesh", { dir: [fK.x * 0.6, 0.9, fK.z * 0.6], speed: 1.6, spread: 0.6, size: 0.06, life: 1.2, stick: 3 });
    });
    // grit off the lintel with the blows, and the door's own bits when it goes
    if (hasDoor) {
      bangs.forEach((b, i) => { const q = D.in(-0.12); R.burst(b + 0.02, [q.x, 2.0, q.z], 3 + i, "stone", { dir: [0, -0.3, 0], speed: 0.3, spread: 0.35, size: 0.016, life: 1.1, grav: 9, stick: 0.5 }); });
      const q = D.in(-0.3); R.burst(tBreak, [q.x, 1.4, q.z], 26, "dust", { dir: [-side * 1.0, 0.3, 0], speed: 1.4, spread: 0.7, size: 0.05, life: 0.9, stick: 1.2 });
    }
    const bits = hasDoor ? D.breakAt(tBreak, { out: 2.4, n: 72 }) : null;
    if (hasDoor) D.carve();

    // ---- the sound ------------------------------------------------------------------------------------------------
    const dW = hasDoor ? [D.face, 1.0, D.z] : [G.x, 1.6, G.z], inside = hasDoor ? [D.in(1.6).x, 1.6, D.in(1.6).z] : [G.x, 1.6, G.z - 1];
    const steps = [];
    for (let s = tOut + 0.15; s < tGrab - 0.05; s += 0.42) { const q = zAt(s); steps.push([s, "mob.zombie.step", { at: [q.x, 0.1, q.z], volume: 0.8 }]); }
    const runSteps = [];
    for (let u = STEP * 0.5; u < runP.L - 0.2; u += STEP) runSteps.push([tGo + prof.tAt(u), "step.stone", { volume: 0.45 }]);
    const sounds = [
      ...(hasDoor ? [
        ...bangs.map((b, i) => [b, "mob.zombie.wood", { at: dW, volume: 1.0 + 0.06 * i, pitch: 0.95 + 0.05 * ((i * 7) % 3) }]),
        [bangs[1] + 0.4, "mob.zombie.say", { at: inside, volume: 0.65, pitch: 0.8, reverb: 0.5 }],
        [bangs[3] + 0.25, "mob.zombie.say", { at: inside, volume: 0.8, pitch: 0.72, reverb: 0.4 }],
        [tBreak, "mob.zombie.woodbreak", { at: dW, volume: 1.35 }], [tBreak + 0.01, "dig.wood", { at: dW, volume: 1.0, pitch: 0.8 }],
        [tBk1 + 0.02, pinned ? "step.stone" : "step.gravel", { volume: 0.7, pitch: 0.8 }]
      ] : [
        [b1, "mob.zombie.say", { at: dW, volume: 1.0, pitch: 0.82, reverb: 0.5 }], [b1 + 1.4, "mob.zombie.step", { at: [G.x, 0.1, G.z], volume: 0.5 }]
      ]),
      ...roar(tBreak + 0.22, [["mob.zombie.say", { at: [A1.x, 1.7, A1.z], pitch: 0.75 }]], { hit: 0.5 }),
      [tBreak + 0.18, "step.stone", { volume: 0.6, pitch: 0.8 }], [tBreak + 0.42, "step.stone", { volume: 0.5, pitch: 0.85 }],   // the stumble
      ...runSteps,
      [tStop - 0.1, "step.gravel", { volume: 0.8, pitch: 0.75 }],   // the skid
      ...steps,
      [tGlz + 0.15, "mob.zombie.say", { at: (() => { const q = zAt(tGlz + 0.15); return [q.x, 1.7, q.z]; })(), volume: 1.0, pitch: 0.7 }],
      ...(mode !== "end" ? [
        [tSee - 0.15, "mob.zombie.say", { at: (() => { const q = othersAt(others[0], tSee); return [q.x, 1.7, q.z]; })(), volume: 1.1, pitch: 0.85 }],
        [tSee + 0.5, "mob.zombie.say", { at: (() => { const q = othersAt(others[1], tSee + 0.5); return [q.x, 1.7, q.z]; })(), volume: 1.0, pitch: 1.0 }]
      ] : []),
      [(tA1 + tGrab) / 2, "mob.zombie.say", { at: [zAt((tA1 + tGrab) / 2).x, 1.7, zAt((tA1 + tGrab) / 2).z], volume: 1.0, pitch: 0.68 }],
      [tGrab, "dig.cloth", { volume: 0.9, pitch: 0.7 }], [tGrab + 0.02, "mob.zombie.hurt", { at: [A2.x, 1.7, A2.z], volume: 1.1, pitch: 0.6 }],
      ...hits.flatMap((h, i) => blow(h.t, { volume: i ? 0.9 : 1.15, gore: i % 2 === 1 })),
      ...deathScream(tK + 0.2, { volume: 1.2, under: false }),
      [tK + 0.55, "mob.zombie.hurt", { volume: 0.8, pitch: 0.75 }],
      ...(mode === "end" ? [
        [others[0].tOut, "mob.zombie.say", { at: [others[0].mid.x, 1.6, others[0].mid.z], volume: 0.9, pitch: 0.9 }],
        [others[1].tOut, "mob.zombie.say", { at: [others[1].mid.x, 1.6, others[1].mid.z], volume: 0.9, pitch: 1.05 }]
      ] : []),
      ...others.flatMap((q) => [0.5, 1.0, 1.5, 2.0].map((d) => q.tOut + d).filter((x) => x < q.tArr).map((x) => [x, "mob.zombie.step", { at: [q.to.x, 0.1, q.to.z], volume: 0.5 }])),
      [T_DRAG + 0.85, "game.player.hurt.fall.small", { volume: 0.9 }],
      [tK + 2.2, "qf.scare.gore", { volume: 1 }],
      [DUR - 0.4, "qf.scare.crunch", { volume: 1 }],
      [DUR, "game.player.die"], [DUR, "@muffle", { hz: 380, s: 3.5 }]
    ];
    const loops = [
      [0.55, tBreak, "qf.scare.heartbeat", { volume: 0.55, fadeOut: 0.1 }],
      [tBk0 - 0.2, tBreak, "qf.scare.breath", { volume: 0.4, pitch: 1.15, fadeIn: 0.4, fadeOut: 0.2 }],
      [0.3, tBreak, "qf.scare.drone", { volume: 0.35, fadeIn: 1.5, fadeOut: 0.3, bus: "sfx" }],
      [tBreak, DUR + 0.2, "qf.scare.heartbeat", { volume: 0.7, pitch: 1.4, fadeIn: 0.05 }],
      [tGo, tGrab + 0.2, "qf.scare.breath", { volume: 0.6, pitch: 1.32, fadeIn: 0.2, fadeOut: 0.2 }]   // (ragged, running)
    ];

    // At the end, hands come into the lens from the edges and close over it.
    const hands = lensLimbs(R, others[0].m, "rightArm", [
      { from: [-0.42, -0.3], to: [-0.12, -0.04], t0: tK + 2.6, t1: tK + 3.15, scale: 0.5, z: -0.3, twist: 0.05 },
      { from: [0.44, -0.26], to: [0.1, -0.02], t0: tK + 2.75, t1: tK + 3.25, scale: 0.5, z: -0.31, twist: 0.06 },
      { from: [0.1, 0.36], to: [0.02, 0.08], t0: tK + 2.9, t1: tK + 3.35, scale: 0.55, z: -0.29, twist: 0.04 },
      { from: [-0.3, 0.32], to: [-0.06, 0.06], t0: tK + 3.0, t1: DUR, scale: 0.5, z: -0.28, twist: 0.05 },
      // its hands on your shoulders, at the grab
      { from: [-0.66, -0.52], to: [-0.4, -0.3], t0: tGrab, t1: tGrab + 0.14, scale: 0.5, z: -0.3, twist: 0.03, t2: T_DRAG + 0.4 },
      { from: [0.68, -0.5], to: [0.4, -0.3], t0: tGrab + 0.03, t1: tGrab + 0.17, scale: 0.5, z: -0.31, twist: 0.03, t2: T_DRAG + 0.45 }
    ], { color: 0x6a6a6a });
    function poseZombie(m, t, lean, armsUp = 1.55, bite = 0, swing = 0) {
      m.anim(t, 0, { walk: 0 });
      zombieArms(m, t, swing);
      const P = m.parts;
      if (P.rightArm && armsUp !== 1.55) { P.rightArm.rotation.x = armsUp + Math.sin(t * 9) * 0.06; P.leftArm.rotation.x = armsUp + Math.sin(t * 9 + 1) * 0.06; }
      if (P.head) P.head.rotation.x = 0.15 - bite * 0.3;
      if (P.headwear && P.head) P.headwear.rotation.copy(P.head.rotation);
      m.pivot.rotation.x = lean;
    }
    const legs = (m, t, on, rate = 7) => { const P = m.parts; if (P.rightLeg) { const a = on ? Math.sin(t * rate) * 0.55 : 0; P.rightLeg.rotation.x = a; P.leftLeg.rotation.x = -a; } };

    function update(t, f) {
      const cl = R.toLocal(R.camera.position);
      const bite = pulse(t, hits.slice(0, 3).map((h) => h.t - 0.06), 0.16);
      const grab = sstep(tGrab, tGrab + 0.18, t);
      let open = 0, lit = 0;
      if (hasDoor) {
        // The door: each blow bows it out and back; the crack, stage by stage; gone at the break.
        const bul = Math.max(0, ...bangs.map((b) => (t >= b ? Math.exp(-(t - b) / 0.07) * Math.sin(Math.min(1, (t - b) / 0.04) * Math.PI / 2) : 0)));
        const crack = bangs.reduce((a, b, i) => a + (t >= b ? (i ? 0.17 : 0.08) : 0), 0);
        D.update(t, { crack: Math.min(0.95, crack), bulge: bul, gone: t >= tBreak });
        bits(t);
      }
      if (t < tGrab) {
        // Behind the door, beating on it (its swing); then out through it and after you, lurching.
        const q = zAt(t), moving = t > tOut && t < tGrab;
        const target = t < tOut ? (hasDoor ? D.in(-1) : { x: 0, z: 0 }) : cl;
        R.place(z1, q.x, 0, q.z, R.yawTo(q.x, q.z, target.x, target.z) + (moving ? 0.06 * Math.sin(t * 7) : 0));
        const sw = hasDoor && t < tBreak ? Math.max(0, ...bangs.map((b) => (t >= b - 0.15 && t < b + 0.15 ? (t - b + 0.15) / 0.3 : 0))) : 0;
        poseZombie(z1, t, (moving ? -0.12 : 0) - 0.05 * grab, 1.55 + (grab > 0 ? 0.1 * grab + 0.01 : 0), 0, sw);
        legs(z1, t, moving, 8);
        z1.pivot.visible = true;
        open = 0.12 + 0.2 * sstep(tBreak, tBreak + 0.3, t) + 0.45 * grab;
        lit = hasDoor ? sstep(tBreak + 0.1, tA1 + 0.2, t) : sstep(b1 + 1, tA1, t);
        if (z1.parts.rightArm && grab > 0) { z1.parts.rightArm.rotation.y = 0.1 + 0.38 * grab; z1.parts.leftArm.rotation.y = -0.1 - 0.38 * grab; }
      } else {
        // The kill: on you, biting; it goes down with you.
        const lunge2 = 0.08 * pulse(t, hits.slice(0, 3).map((h) => h.t - 0.08), 0.12) * sstep(tGrab, tK - 0.1, t);
        // its head in at the side of your neck (the head pushed away from it); then down with you
        const nb = neck(t);
        const dz = -lunge2 * 0.6 + 0.1 * sstep(T_DRAG, T_DRAG + 0.9, t), w = 0.02 * Math.sin(t * 3) + 0.06 * nb, Z = A2;
        z1.pivot.visible = true;
        R.place(z1, Z.x + rK.x * w + fK.x * dz, 0, Z.z + rK.z * w + fK.z * dz, R.yawTo(Z.x, Z.z, cl.x, cl.z) + 0.05 * Math.sin(t * 2.1) - 0.25 * nb);
        poseZombie(z1, t, -0.05 - lunge2 * 0.6 - 0.06 * nb - 0.45 * sstep(T_DRAG, T_DRAG + 1.1, t), 1.55 + 0.15 * grab, bite + 0.5 * nb);
        if (z1.parts.rightArm) { z1.parts.rightArm.rotation.y = 0.1 + 0.38 * grab; z1.parts.leftArm.rotation.y = -0.1 - 0.38 * grab; }
        open = (0.12 + 0.45 * grab) * (1 - sstep(tGrab, tK, t)) + (0.25 + 0.75 * bite) * sstep(tGrab, tK, t);
        lit = 0.7 * (1 - 0.6 * sstep(T_DRAG, T_DRAG + 1, t));
      }
      jaw.set(open);
      z1.setOwn(0.03 + 0.17 * lit);
      hands(t);
      for (const q of others) {
        // out of their dark (the passage, their side way, the far corridor), into the light and over you
        const p = othersAt(q, t), moving = t > q.t0 && t < q.tArr;
        q.m.amb.setScalar(mode === "end" && hasDoor ? lerp(0.025, 0.2, sstep(0, 1, p.out * 1.4 - 0.4)) : mode === "dark" ? lerp(0.05, 0.2, sstep(q.tOut - 0.5, q.tArr, t)) : lerp(0.06, 0.2, sstep(0.3, 1, p.out)));
        q.m.pivot.visible = t >= q.vis0;
        R.place(q.m, p.x, 0, p.z, R.yawTo(p.x, p.z, cl.x, cl.z));
        poseZombie(q.m, t + q.t0, q.lean * sstep(q.tArr, q.tArr + 0.8, t), 1.55 - 0.45 * sstep(q.tArr, q.tArr + 0.8, t), 0);
        legs(q.m, t, moving, 8);
      }
      // a sliver of corridor light on its face as it comes on (a lamp above the eyes)
      faceL.position.set(0, 0.32, -0.05).applyQuaternion(R.camera.quaternion).add(R.camera.position);
      faceL.intensity = 0.3 * lit * clamp(z1.pivot.position.distanceTo(R.camera.position) / 0.9, 0.25, 1);
      lightJaw(0.6 * clamp(z1.amb.x + 0.03 + 0.17 * lit + 0.8 * faceL.intensity, 0.12, 1));   // (bone in shadow: under the skin's brightness)
      const closing = sstep(tK + 1.95, DUR, t);
      f.env = { bake: 1 - 0.2 * sstep(0.2, 1.2, t) - 0.25 * sstep(T_DRAG, T_DRAG + 0.9, t) - 0.3 * closing, lights: 1 - 0.3 * sstep(T_DRAG, T_DRAG + 0.9, t) - 0.4 * closing, fogMul: 1 + 0.6 * sstep(0.5, 3.5, t) };
      f.vig = [12, 0, 0, 0.3 * sstep(b1, tBreak, t) + 0.15 * sstep(tSee, tStop, t) + 0.25 * sstep(T_DRAG, T_DRAG + 0.9, t) + 0.4 * closing]; f.vigR = 0.9;
      f.black = 0.85 * sstep(tK + 2.95, DUR, t);
      f.splats = [hits[0], hits[1], hits[3]].filter((h) => t >= h.t).map((h, i) => ({ t0: h.t, x: [0.3, 0.7, 0.5][i], y: [0.38, 0.3, 0.6][i], r: [12, 11, 14][i], seed: 11 + i }));
    }
    const r2 = (v) => +v.toFixed(2);
    return { dur: DUR, hits, cam, update, sounds, loops, deathSide: -side, solid: hasDoor ? (w) => D.solid(w) : undefined,
      marks: { dread: bangs[2] ?? b1 + 0.2, fake: tBreak + 0.25, lunge: tGrab + 0.1, kill: tK + 1.0, brk: tBreak + 0.3, run: tGo + 0.3, glance: tGlz + 0.3, see: tSee + 0.3, stop: tStop + 0.1, turn: tBackR1 },
      notes: { door: hasDoor, side, mode, face: hasDoor ? r2(D.face) : null, dz: hasDoor ? r2(D.z) : null, back: r2(back), pinned, run: r2(runP.L), PS: [r2(PS.x), r2(PS.z)], spot: spot ? [r2(spot.c.x), r2(spot.c.z), spot.c2 ? 1 : 0] : null, hid: others.map((q) => r2(q.hid ?? 0)),
        tBreak: r2(tBreak), tGo: r2(tGo), tStop: r2(tStop), tGrab: r2(tGrab), natural: r2(tA1 + L2 / V_Z), tK: r2(tK), dur: r2(DUR) } };
  }
};
