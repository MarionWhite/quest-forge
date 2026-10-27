// Zombie Pigman (v4, the owner's): your fault. A diamond ore glints in the floor just ahead. The walk slows, the view
// drifts down to it, you step up to it and raise the iron pickaxe; each swing the cracks spread across it. One swing
// from breaking it, you stop: silence. On the swing that would break it, a pigman steps into the gap from just out of
// view and the pick lands in him: the hurt flash, the angry squeal, and his face snaps round to yours and comes at the
// lens with the screech. After the static, every pair of eyes in the dark goes red, the head flicks from eyes to eyes,
// they come from every passage at once, and they cut you down.
import { THREE, clamp, lerp, sstep, pulse, tex, easeOut, blockMesh } from "./rig.js";
import { settle, shake, hitsOf, floorFall, heldItem, swingAt, zombieArms, mulberry, glowEyes, mcRot } from "./common.js";
import { lunge, lungeFx, screech, splitJaw, faceAnchor, boxOf, silence, deathScream, jit } from "./fnaf.js";

const SWORD = [{ id: "minecraft:golden_sword", ench: false }];
const TAU = Math.PI * 2;
const wrap = (a) => { while (a > Math.PI) a -= TAU; while (a < -Math.PI) a += TAU; return a; };

// The pigman's two eyes, lit red: the skull's socket (base layer) and the pink eye on the hat layer (inflated 0.5).
const redEyes = (R, m) => glowEyes(R, m, [[-3, -4.5, -4.06, 2, 1], [3.375, -4.56, -4.58, 2.25, 1.125]], [1, 0.1, 0.05], { halo: 0.4, glow: 0.3 });
// Up close: a red point in each eye, not two lit bars across the face.
const redEyesNear = (R, m) => glowEyes(R, m, [[-3, -4.5, -4.07, 0.9, 0.5], [3.375, -4.56, -4.59, 1, 0.55]], [0.85, 0.06, 0.03], { halo: 0.12, glow: 0.08 });

// The ore's glint: a four-point pixel star, drawn once.
let _spark = null;
function sparkTex() {
  if (_spark) return _spark;
  const c = document.createElement("canvas"); c.width = c.height = 16;
  const g = c.getContext("2d");
  g.fillStyle = "rgba(255,255,255,0.55)"; g.fillRect(7, 2, 2, 12); g.fillRect(2, 7, 12, 2);
  g.fillStyle = "#fff"; g.fillRect(7, 5, 2, 6); g.fillRect(5, 7, 6, 2);
  _spark = new THREE.CanvasTexture(c); _spark.colorSpace = THREE.SRGBColorSpace;
  _spark.magFilter = _spark.minFilter = THREE.NearestFilter; _spark.generateMipmaps = false;
  return _spark;
}

export default {
  death: "Steve was slain by Zombie Pigman",
  async build(R) {
    const [pickTex, oreTex, goldTex, ...stages] = await Promise.all(["mc:items/iron_pickaxe", "k:diamond_ore", "mc:items/gold_sword", ...[...Array(10)].map((_, i) => "destroy_stage_" + i)].map((n) => tex(n)));
    const rnd = mulberry(R.seed * 13 + 5);
    const ok = (x, z) => !R.solid(x, 0.5, z) && !R.solid(x, 1.5, z) && R.solid(x, -0.5, z);
    const inX = (x) => clamp(x, -(R.wallL - 0.35), R.wallR - 0.35);

    // ---- the bait: a floor block just ahead turned to diamond ore --------------------------------------------
    const roomy = R.wallR >= R.wallL ? 1 : -1;
    let spot = null;
    for (const z of [2.4, 2.8, 2.1, 3.2, 1.8]) {
      for (const x of [0.35 * roomy, 0, -0.35 * roomy, 0.75 * roomy]) if (!spot && z < R.ahead - 0.7 && x > -(R.wallL - 0.5) && x < R.wallR - 0.5 && ok(x, z)) spot = { x, z };
      if (spot) break;
    }
    if (!spot) spot = { x: 0, z: clamp(R.ahead - 0.8, 1.6, 2.4) };
    const ow = R.L(spot.x, -0.5, spot.z, new THREE.Vector3()), B = [Math.floor(ow.x), Math.floor(ow.y), Math.floor(ow.z)];
    const oc = R.toLocal({ x: B[0] + 0.5, y: B[1] + 0.5, z: B[2] + 0.5 });
    const amb = R.bakeAt(new THREE.Vector3(B[0] + 0.5, B[1] + 1.02, B[2] + 0.5), new THREE.Vector3(0, 1, 0)) || new THREE.Vector3(0.22, 0.2, 0.19);
    const oreM = blockMesh(oreTex, { lit: true, amb }); oreM.position.set(B[0] + 0.5, B[1] + 0.5, B[2] + 0.5); oreM.scale.setScalar(1.004); R.add(oreM);
    // The 1.7.10 block-breaking overlay (destroy_stage_0..9) over it.
    const crackMats = stages.map((t) => new THREE.MeshBasicMaterial({ map: t, transparent: true, alphaTest: 0.1, blending: THREE.CustomBlending, blendSrc: THREE.DstColorFactor, blendDst: THREE.SrcColorFactor, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -3, polygonOffsetUnits: -3, fog: false }));
    const crack = new THREE.Mesh(new THREE.BoxGeometry(1.01, 1.01, 1.01), crackMats[0]); crack.position.copy(oreM.position); crack.visible = false; crack.renderOrder = 3; R.add(crack);
    // Its glint: a few pixel stars on the diamonds, catching the torchlight now and then.
    const sparks = [...Array(4)].map((_, i) => {
      const m = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ map: sparkTex(), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, color: 0xc4f6ff, fog: false }));
      m.visible = false; R.add(m);
      return { m, at: [oc.x + (rnd() - 0.5) * 0.66, 0.02, oc.z + (rnd() - 0.5) * 0.66], ph: rnd() * 2, per: 0.75 + rnd() * 0.7, s: 0.07 + rnd() * 0.04 };
    });

    // Where you stand to mine it, and the look down at it.
    const C = { x: inX(oc.x * 0.4), z: Math.max(0.15, oc.z - 1.32) };
    const dd = Math.hypot(oc.x - C.x, oc.z - C.z), ux = (oc.x - C.x) / dd, uz = (oc.z - C.z) / dd;
    const lookOre = (x, z) => ({ yaw: R.yawTo(x, z, oc.x, oc.z), pitch: Math.atan2(-(R.eye - 0.05), Math.hypot(oc.x - x, oc.z - z)) });
    // The gap between you and it, where he steps in; and where he steps in from (just out of view, the roomier side).
    const P = { x: C.x + ux * 0.78, z: C.z + uz * 0.78 };
    const ax = uz, az = -ux;   // across the look, to its right
    const reach = (s) => { for (const d of [1.3, 1.1, 0.9, 0.7]) if (!R.solid(P.x + ax * s * d, 0.5, P.z + az * s * d) && !R.solid(P.x + ax * s * d, 1.5, P.z + az * s * d)) return d; return 0; };
    const rA = reach(1), rB = reach(-1), sIn = rA === rB ? roomy * Math.sign(ax || 1) : rA > rB ? 1 : -1, dIn = Math.max(rA, rB) || 0.9;
    const Pin = { x: P.x + ax * sIn * dIn, z: P.z + az * sIn * dIn };

    // ---- the dice -------------------------------------------------------------------------------------------
    const T_SEE = R.vary(0.6, 0.3);                                   // the glint catches your eye
    const T_GO = T_SEE + R.vary(0.85, 0.3), T_AT = T_GO + clamp(Math.hypot(C.x - R.start.x, C.z - R.start.z) / 1.5, 0.5, 1.6);
    const T_EQ = T_AT - 0.2, T_DIG = T_AT + R.vary(0.3, 0.3);
    const SW = 0.3, nSw = clamp(Math.round(R.vary(6, 0.3)), 4, 8);   // a swing every 6 ticks, as when you hold the button
    const digSw = [...Array(nSw)].map((_, i) => T_DIG + i * SW);
    const T_HALT = T_DIG + nSw * SW;                                  // one from breaking it: you stop
    const hold = R.vary(1.05, 0.4), T_SWING = T_HALT + hold, T_HIT = T_SWING + 0.15;
    const fakeStep = R.chance(0.5);                                   // something shifts out of view in the silence
    const T_IN = T_HIT - 0.24;                                        // he steps in
    const t0 = T_HIT + 0.09;

    const p0 = R.mob("PigZombie", { amb: [0.24, 0.22, 0.22], equipment: SWORD, own: true });
    p0.setOwn(0.12);
    const eyes0 = redEyes(R, p0), eyes0n = redEyesNear(R, p0);
    const held0 = p0.parts.rightArm && p0.parts.rightArm.children.find((o) => o.isGroup && o.matrixAutoUpdate === false);
    const jaw0 = splitJaw(p0, [{ part: p0.parts.head, box: boxOf("zombie", "bipedHead"), rows: 2 }, { part: p0.parts.headwear, box: boxOf("zombie", "bipedHeadwear"), rows: 2 }], { nTeeth: 3 });
    p0.anim(0, 0, {}); R.place(p0, 0, 0, 4, Math.PI);
    const anchor = faceAnchor(p0, p0.parts.head, boxOf("zombie", "bipedHead")); anchor.y -= 0.07;
    const L = lunge(R, p0, { t0, rush: R.vary(0.15, 0.2), hold: R.vary(0.6, 0.15), dist: 0.66, anchor, seed: 41 });
    const tK = L.t3;
    const L0 = { x: C.x + ux * 0.98, z: C.z + uz * 0.98 };             // where he stands after the static
    const F = { x: C.x + ux * 0.8, z: C.z + uz * 0.8 };                // and where he is when you look back

    // ---- the payoff: the others ---------------------------------------------------------------------------
    const spots = [];
    const push = (x, z, kind) => { if (!ok(x, z) || Math.hypot(x - C.x, z - C.z) < 1.6 || spots.some((s) => Math.hypot(s.x - x, s.z - z) < 1.3)) return; spots.push({ x, z, kind }); };
    for (const p of R.passages) if (p.dist < 14) push(p.x + p.side * 2.2, p.z, "passage");
    for (const o of R.openings) if (o.z > -9 && o.z < 13) push(o.side * (o.wall + clamp(o.depth - o.wall - 0.6, 0.4, 3)), o.z, "opening");
    if (R.ahead > 4.5) push(inX(0.3), Math.min(R.ahead - 0.7, 7.5), "ahead");
    if (R.ahead > 9) push(inX(-0.35), Math.min(R.ahead - 0.7, 12), "ahead");
    if (R.behind > 3.5) push(inX(-0.2), -Math.min(R.behind - 0.7, 5.5), "behind");
    if (R.behind > 8) push(inX(0.35), -Math.min(R.behind - 0.7, 9.5), "behind");
    const yawL0 = R.yawTo(C.x, C.z, L0.x, L0.z);
    const T_ANGRY = tK + R.vary(0.5, 0.3), T_RUSH = T_ANGRY + 0.35;
    const rest = spots.sort((a, b) => Math.abs(wrap(R.yawTo(C.x, C.z, a.x, a.z) - yawL0)) - Math.abs(wrap(R.yawTo(C.x, C.z, b.x, b.z) - yawL0))).slice(0, 6);
    // They come from all round and close in a crescent before you, round him, in the order they come from: the horde
    // is in front of you, not behind.
    const ang0 = Math.atan2(L0.x - C.x, L0.z - C.z), nR = rest.length;
    const order = rest.map((s, i) => [wrap(Math.atan2(s.x - C.x, s.z - C.z) - ang0), i]).sort((a, b) => a[0] - b[0]);
    const angles = new Array(nR);
    order.forEach(([, i], j) => { angles[i] = ang0 - lerp(-1.25, 1.25, (j + 0.5) / Math.max(1, nR)); });
    const rushers = rest.map((s, i) => {
      let tx = inX(C.x + Math.sin(angles[i]) * 1.5), tz = C.z + Math.cos(angles[i]) * 1.5;
      if (Math.hypot(tx - C.x, tz - C.z) < 1.0) tz = C.z + Math.sign(tz - C.z || 1) * Math.sqrt(Math.max(1.0 - (tx - C.x) ** 2, 0.36));
      const path = [[s.x, s.z]];
      if (s.kind === "opening" || s.kind === "passage") path.push([inX(Math.sign(s.x) * 9), s.z]);
      // Never through you: the ones from behind come round you to their place in front.
      const [lx, lz] = path[path.length - 1], sx = tx - lx, sz = tz - lz, sl = Math.hypot(sx, sz) || 1;
      const k = clamp(((C.x - lx) * sx + (C.z - lz) * sz) / (sl * sl)), cx = lx + sx * k - C.x, cz = lz + sz * k - C.z;
      if (Math.hypot(cx, cz) < 0.75 && k > 0 && k < 1) {
        const px = -sz / sl, pz = sx / sl, sg = (tx - C.x) * px + (tz - C.z) * pz >= 0 ? 1 : -1;
        path.push([inX(C.x + px * sg * 0.95), C.z + pz * sg * 0.95]);
      }
      path.push([tx, tz]);
      let len = 0; for (let q = 1; q < path.length; q++) len += Math.hypot(path[q][0] - path[q - 1][0], path[q][1] - path[q - 1][1]);
      const ts = T_RUSH + 0.08 * i;
      return { ...s, m: R.mob("PigZombie", { amb: [0.17, 0.15, 0.15], equipment: SWORD }), path, len, ts, te: ts + clamp(len / 6.5, 0.45, 1.3), ta: T_ANGRY + 0.1 + 0.075 * i, tx, tz, seed: rnd() * 10 };
    });
    for (const q of rushers) q.eyes = redEyes(R, q.m);
    for (const q of rushers) q.path = q.path.map(([x, z], i) => i === 1 ? [clamp(x, -(R.wallL - 0.4), R.wallR - 0.4), z] : [x, z]);
    // The head flicks from eyes to eyes (one each side); when it comes back, he is at your face.
    const rel = (q) => wrap(R.yawTo(C.x, C.z, q.x, q.z) - yawL0), near = (a, b) => Math.hypot(a.x - C.x, a.z - C.z) - Math.hypot(b.x - C.x, b.z - C.z);
    const darts = [rushers.filter((q) => rel(q) > 0.45 && rel(q) < 1.5).sort(near)[0], rushers.filter((q) => rel(q) < -0.45 && rel(q) > -1.5).sort(near)[0]]
      .filter(Boolean).map((q) => ({ yaw: yawL0 + rel(q), q }));
    darts.forEach((d, i) => { d.t = T_ANGRY + 0.12 + i * 0.3; d.q.ta = Math.min(d.q.ta, d.t - 0.12); });
    const tBack = (darts.length ? darts[darts.length - 1].t + 0.06 : T_ANGRY + 0.2) + R.vary(0.4, 0.4);
    const T_H1 = Math.max(tBack + 0.35, T_RUSH + 0.85), T_FALL = T_H1 + 1.0, DUR = T_FALL + 0.55;
    const byArrival = rushers.slice().sort((a, b) => a.te - b.te);
    for (const q of rushers) q.te = Math.min(q.te, T_H1 - 0.05);   // all of them there by the first blow
    const hitList = [[T_H1, 4, p0], [T_H1 + 0.5, 4, byArrival[0] || p0], [T_FALL, 5, byArrival[1] || byArrival[0] || p0], [DUR, 7, byArrival[2] || p0]];
    const hits = hitsOf(hitList.map(([t, d]) => [t, d, 1]));
    const posR = (q, t) => {
      const k = clamp((t - q.ts) / (q.te - q.ts));
      let d = k * q.len;
      for (let i = 1; i < q.path.length; i++) {
        const a = q.path[i - 1], b = q.path[i], l = Math.hypot(b[0] - a[0], b[1] - a[1]);
        if (d <= l || i === q.path.length - 1) { const u = l ? clamp(d / l) : 1; return { x: lerp(a[0], b[0], u), z: lerp(a[1], b[1], u), dir: Math.atan2(-(b[0] - a[0]), b[1] - a[1]), k }; }
        d -= l;
      }
      return { x: q.tx, z: q.tz, dir: 0, k };
    };
    // Swings: the attackers' land on the hits; the rest flail when they get there (the i-frames eat them).
    const swings = new Map([[p0, []]]);
    for (const q of rushers) {
      const s = []; for (let tt = q.te + 0.15 + rnd() * 0.25; tt < DUR + 2; tt += 0.55 + rnd() * 0.2) s.push(tt);
      swings.set(q, s);
    }
    hitList.forEach(([t, , w]) => { const s = swings.get(w); if (!s.includes(t)) s.push(t); });
    const attackerAt = (h) => { const w = hitList.find((x) => x[0] === h.t)[2]; return w === p0 ? F : { x: w.tx, z: w.tz }; };
    hits.forEach((h) => { const a = attackerAt(h); h.side = (a.x - C.x) * uz - (a.z - C.z) * ux >= 0 ? -1 : 1; });

    // ---- the camera ---------------------------------------------------------------------------------------
    const yawP = R.yawTo(C.x, C.z, P.x, P.z);
    const yawAt = (t) => {
      let y = yawL0;
      if (t > T_ANGRY && t < tBack + 0.13 && darts.length) {
        const keys = [[T_ANGRY, yawL0], ...darts.flatMap((d) => [[d.t - 0.1, null], [d.t + 0.06, d.yaw]]), [tBack, null]];
        let prevT = T_ANGRY, prevY = yawL0;
        for (const [kt, ky] of keys.slice(1)) {
          const target = ky ?? prevY;
          if (t <= kt) { y = lerp(prevY, target, sstep(prevT, kt, t)); break; }
          prevT = kt; prevY = target; y = target;
        }
        if (t > tBack) y = lerp(y, yawL0, 1 - Math.pow(1 - clamp((t - tBack) / 0.13), 4));   // back to him: snap
      }
      return y;
    };
    const knock = (t) => {
      let x = 0, z = 0;
      for (const h of hits) { if (t < h.t) break; const a = attackerAt(h), n = Math.hypot(a.x - C.x, a.z - C.z) || 1, k = 0.2 * easeOut((t - h.t) / 0.25); x -= (a.x - C.x) / n * k; z -= (a.z - C.z) / n * k; }
      return { x, z };
    };
    const camAlive = (t) => {
      const s = settle(R, t, 0.9);
      // The glint: the view drifts down to it and the walk slows; then you step up to it.
      const kw = sstep(T_GO, T_AT, t), walking = t > T_GO && t < T_AT;
      const x0 = lerp(s.x, C.x, kw), z0 = lerp(s.z, C.z, kw);
      const lo = lookOre(x0, z0), kd = sstep(T_SEE, T_SEE + 1.1, t);
      let yaw = lerp(s.yaw, lo.yaw, kd), pitch = lerp(s.pitch, lo.pitch, kd);
      // The flinch: the pick lands in him and the head comes up to his face.
      const kr = sstep(T_HIT, T_HIT + 0.13, t);
      yaw = lerp(yaw, yawP, kr); pitch = lerp(pitch, 0.12, kr);
      if (t > tK) { yaw = yawAt(t); pitch = lerp(0.12, -0.02, sstep(tK, tK + 0.6, t)); }
      const kb = knock(t);
      return { x: x0 - ux * 0.07 * kr + kb.x, y: s.y - (walking ? 0.035 * Math.abs(Math.sin((t - T_GO) * 7.2)) : 0), z: z0 - uz * 0.07 * kr + kb.z, yaw, pitch, roll: 0,
        fov: s.fov - 6 * sstep(T_HALT, T_SWING, t) * (1 - sstep(T_HIT, T_HIT + 0.1, t)) + 10 * pulse(t, [L.t1], 0.12) + 5 * sstep(T_ANGRY, T_ANGRY + 0.1, t) * (1 - sstep(T_ANGRY + 0.15, T_ANGRY + 0.5, t)),
        near: t >= T_IN - 0.1 ? 0.02 : undefined };
    };
    const fallSide = hits[2] ? -hits[2].side : 1;
    const cam = (t) => {
      const c = camAlive(Math.min(t, T_FALL + 0.001));
      if (t > T_FALL) { const a = camAlive(t); c.x = a.x; c.z = a.z; }
      floorFall(c, t, T_FALL, { d: 0.5, side: fallSide, roll: 0.55, y: 0.3, pitch: 0.2, back: 0.15 });
      // On the floor: looking up into the ring of them.
      const up = sstep(T_FALL + 0.35, T_FALL + 0.75, t);
      c.pitch = lerp(c.pitch, 1.0, up); c.fov += 8 * up; c.yaw += 0.25 * fallSide * up;
      const dig = digSw.some((s) => t >= s + 0.1 && t < s + 0.2) ? 0.0025 : 0;   // the pick biting
      return shake(c, t, 0.0015 + dig + 0.003 * sstep(T_HALT, T_SWING, t) + L.shake(t) + 0.02 * pulse(t, [T_HIT, ...hits.map((h) => h.t)], 0.18) + 0.01 * sstep(tK, tK + 0.3, t), 7);
    };

    // Gore: from your chest and neck, toward the camera, at each hit.
    hits.forEach((h) => {
      const c = cam(h.t + 0.01), fx = -Math.sin(c.yaw), fz = Math.cos(c.yaw);
      const at = [c.x + fx * 0.4, Math.max(0.25, c.y - 0.45), c.z + fz * 0.4];
      R.burst(h.t, at, 26, "blood", { dir: [fx * 0.6, 0.9, fz * 0.6], speed: 2.2, spread: 0.8, size: 0.05, life: 1.3, stick: 3 });
      R.burst(h.t + 0.02, at, 7, "flesh", { dir: [fx * 0.4, 0.8, fz * 0.4], speed: 1.6, spread: 0.7, size: 0.07, life: 1.2, stick: 3 });
    });
    // The pick in his side.
    R.burst(T_HIT + 0.01, [P.x, 1.0, P.z], 14, "blood", { dir: [-ux * 0.5, 0.7, -uz * 0.5], speed: 1.8, spread: 0.8, size: 0.04, life: 1.1, stick: 3 });
    const pick = heldItem(R, pickTex, { color: 0x9a9a9a });
    const mySwings = [...digSw, T_SWING, tK + 0.25];
    // The gold sword raised over you as he comes: a blade across the top of the view, between you and his face.
    const raised = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ map: goldTex, transparent: true, alphaTest: 0.1, side: THREE.DoubleSide, depthTest: false, depthWrite: false, fog: false, color: 0x9a8a70 }));
    raised.renderOrder = 2150; raised.visible = false; R.view.add(raised);
    const glow = R.ownLight(R.light(0xffb070, 0, 6, 1.4));
    const redLight = R.ownLight(R.light(0xff2010, 0, 9, 1.2));

    // ---- the sound ----------------------------------------------------------------------------------------
    const S2 = screech(L, [["mob.zombiepig.zpigangry", { pitch: 0.7 }], ["mob.zombiepig.zpighurt", { pitch: 0.6, volume: 1.2 }]]);
    const at0 = [oc.x, 0.2, oc.z];
    const steps = [];
    for (let s = T_GO + 0.12; s < T_AT; s += 0.4) steps.push([s, "step.stone", { volume: 0.16, pitch: 0.9 }]);
    for (const q of rushers) for (let s = q.ts + 0.12; s < q.te; s += 0.3) { const p = posR(q, s); steps.push([s, "mob.zombie.step", { at: [p.x, 0.1, p.z], volume: 0.45, pitch: 1.1 }]); }
    const sounds = [
      ...steps.slice(0, 48),
      // Mining: the block's step sound on each swing (1.7.10 plays it while you dig), a dig crunch every other one.
      ...digSw.map((s) => [s + 0.12, "step.stone", { at: at0, volume: 0.32, pitch: 0.5 }]),
      ...digSw.filter((_, i) => i % 2 === 1).map((s) => [s + 0.14, "dig.stone", { at: at0, volume: 0.22, pitch: 0.75 }]),
      silence(T_HALT + 0.02, { fade: 0.25 }),
      ...(fakeStep ? [[T_HALT + hold * 0.5, "mob.zombie.step", { at: [Pin.x, 0.1, Pin.z], volume: 0.14, pitch: 0.8 }]] : []),
      [T_IN + 0.04, "mob.zombie.step", { at: [Pin.x, 0.1, Pin.z], volume: 0.5 }], [T_IN + 0.16, "mob.zombie.step", { at: [P.x, 0.1, P.z], volume: 0.55 }],
      [T_HIT, "mob.zombiepig.zpighurt", { at: [P.x, 1.6, P.z], volume: 1.1 }],
      [T_HIT + 0.01, "qf.scare.crunch", { volume: 0.5 }],
      [T_HIT + 0.05, "mob.zombiepig.zpigangry", { at: [P.x, 1.6, P.z], volume: 1.2, pitch: 0.92 }],
      ...S2.sounds,
      [T_ANGRY, "mob.zombiepig.zpigangry", { at: [L0.x, 1.6, L0.z], volume: 1, pitch: 0.95 }],
      [T_ANGRY + 0.02, "qf.scare.stinger", { volume: 0.85 }],
      ...rushers.map((q, i) => [q.ta + 0.02, "mob.zombiepig.zpigangry", { at: [q.x, 1.6, q.z], volume: 0.9, pitch: 0.82 + 0.09 * (i % 5), reverb: 0.5 }]),
      ...hits.flatMap((h, i) => [[h.t, "game.player.hurt"], [h.t + 0.01, "qf.scare.hit", { volume: 0.9 }], [h.t + 0.03, i % 2 ? "qf.scare.gore" : "qf.scare.crunch", { volume: 0.9 }]]),
      ...[T_H1 + 0.2, T_H1 + 0.75, T_FALL + 0.2].map((tt, i) => { const q = rushers[i % Math.max(1, rushers.length)]; return [tt, "mob.zombiepig.zpigangry", { at: q ? [q.tx, 1.6, q.tz] : [L0.x, 1.6, L0.z], volume: 0.9, pitch: 0.9 + 0.12 * i }]; }),
      [T_FALL + 0.45, "game.player.hurt.fall.small"], ...deathScream(T_H1 + 0.3), ...deathScream(T_FALL + 0.1, { volume: 1.1, under: false }),
      [DUR, "game.player.die"], [DUR, "@muffle", { hz: 380, s: 3 }]
    ];
    const loops = [
      [T_DIG, T_HALT + 0.02, "qf.scare.drone", { volume: 0.22, fadeIn: 1.5, fadeOut: 0.02, bus: "sfx" }],
      ...S2.loops,
      [tK, T_ANGRY, "qf.scare.heartbeat", { volume: 0.6, pitch: 1.3, fadeIn: 0.05, fadeOut: 0.02 }],
      [T_ANGRY, DUR + 0.2, "qf.scare.heartbeat", { volume: 0.8, pitch: 1.5 }]
    ];

    function posePig(m, t, x, y, z, yaw, { walk = 0, run = false, look = 0, swing = 0, lean = 0, seed = 0 } = {}) {
      R.place(m, x, y, z, yaw, lean);
      m.anim((t + seed) * (run ? 1.6 : 1), 0, { walk, lookAt: look });
      zombieArms(m, t + seed, swing);
    }
    const yawIn = R.yawTo(Pin.x, Pin.z, P.x, P.z);
    function update(t, f) {
      const camNow = cam(t);
      const inLunge = t >= t0 && t < tK;
      // The bait.
      for (const sp of sparks) {
        const u = ((t + sp.ph) % sp.per) / sp.per, tw = t < T_HIT ? Math.max(0, Math.sin(clamp((u - 0.7) / 0.3) * Math.PI)) : 0;
        const first = sp === sparks[0] ? Math.max(0, Math.sin(clamp((t - T_SEE + 0.05) / 0.35) * Math.PI)) : 0;   // the one that catches your eye
        const k = Math.max(tw, first) * (1 - 0.6 * sstep(T_DIG, T_HALT, t));
        sp.m.visible = k > 0.02;
        if (!sp.m.visible) continue;
        R.L(sp.at[0], sp.at[1], sp.at[2], sp.m.position); sp.m.quaternion.copy(R.camera.quaternion); sp.m.scale.setScalar(sp.s * (0.4 + 0.6 * k));
        sp.m.material.opacity = 0.85 * k;
      }
      const stage = t >= T_DIG && t < T_HIT ? Math.min(8, Math.floor(clamp((t - T_DIG) / (T_HALT - T_DIG)) * 8.99)) : -1;
      crack.visible = stage >= 0; if (stage >= 0) crack.material = crackMats[stage];
      // Him: in from out of view, across the gap; the pick lands; the head snaps round; the lunge; then at your face.
      let x = Pin.x, z = Pin.z, yaw = yawIn, look = 0, walk = 0;
      const toCam = (px, pz) => R.yawTo(px, pz, camNow.x, camNow.z);
      if (t < T_IN + 0.22) { const k = clamp((t - T_IN) / 0.22); x = lerp(Pin.x, P.x, k); z = lerp(Pin.z, P.z, k); walk = 1.4; }
      else if (t < tK) {
        const kb = t > T_HIT ? 0.12 * easeOut(clamp((t - T_HIT) / 0.15)) : 0;
        x = P.x + ux * kb; z = P.z + uz * kb;
        // the head snaps round to you; as the lunge turns the whole of him to the lens, the head comes back square
        look = -clamp(wrap(toCam(x, z) - yaw), -1.4, 1.4) * sstep(T_HIT + 0.02, T_HIT + 0.08, t) * (1 - clamp((t - t0) / (L.rush * 0.55)));
      } else { const at = t < tBack - 0.04 ? L0 : F; x = at.x; z = at.z; yaw = toCam(x, z); }
      const lean0 = -0.22 * sstep(T_FALL + 0.2, T_FALL + 0.8, t);
      posePig(p0, t, x, 0, z, yaw, { walk, look, swing: swingAt(t, swings.get(p0)), lean: lean0 });
      if (inLunge && p0.parts.rightArm) p0.parts.rightArm.visible = false;   // raised out of the view: only its blade shows
      if (inLunge && p0.parts.leftArm) mcRot(p0.parts.leftArm, -0.25, 0, 0.1);   // the other hangs: nothing between you and the face
      if (t >= T_HIT && t < tK && p0.parts.head) p0.parts.head.rotation.z += 0.04 * jit(t, 3, 12);
      jaw0.set(t >= T_HIT && t < tK ? Math.max(0.15 + 0.1 * Math.max(0, jit(t, 5, 14)), sstep(t0, L.t1, t) * (0.85 + 0.15 * jit(t, 9))) : t >= tK ? 0.3 * Math.max(0, Math.sin(t * 8)) : 0);
      if (inLunge) L.apply(t);
      p0.setOwn(inLunge ? 0.16 : t >= T_HIT && t < tK ? 0.3 : 0.12);
      p0.pivot.visible = t >= T_IN;
      if (held0) held0.visible = !inLunge;
      R.flash(p0, t >= T_HIT && t < L.t1 ? 1 - sstep(t0, L.t1, t) : 0);   // the hurt flash: your pick (gone as his face lands)
      eyes0(inLunge ? 0 : t >= tK ? sstep(T_ANGRY - 0.06, T_ANGRY + 0.04, t) : 0); eyes0n(inLunge ? 0.8 : 0);
      // Everyone else: eyes in every dark place, then they come.
      for (const q of rushers) {
        q.m.pivot.visible = t >= q.ta && !inLunge;
        q.eyes(t >= q.ta && !inLunge ? sstep(q.ta, q.ta + 0.1, t) : 0);
        if (t < q.ta) continue;
        const r = posR(q, t), there = r.k >= 1, wide = 1 + 0.22 * sstep(T_FALL, T_FALL + 0.5, t);   // a step back to look at you
        if (there) { r.x = C.x + (r.x - C.x) * wide; r.z = C.z + (r.z - C.z) * wide; }
        const fy = there ? R.yawTo(q.tx, q.tz, camNow.x, camNow.z) : (t < q.ts ? R.yawTo(q.x, q.z, C.x, C.z) : r.dir);
        posePig(q.m, t, r.x, 0, r.z, fy, { walk: t > q.ts && !there ? 1.35 : 0, run: true, swing: swingAt(t, swings.get(q)), lean: -0.22 * sstep(T_FALL + 0.2, T_FALL + 0.9, t), seed: q.seed });
      }
      pick(t, mySwings, t < T_EQ || t > T_FALL + 0.05 || inLunge, camNow.fov, sstep(T_EQ, T_EQ + 0.3, t));
      raised.visible = inLunge;
      if (inLunge) {
        const h = Math.tan(R.camera.fov * Math.PI / 360) * 0.4, u = sstep(t0, L.t1, t);
        raised.scale.setScalar(h * 1.25);
        raised.position.set(-h * R.camera.aspect * 0.62 + jit(t, 51) * 0.006, h * (0.62 + 0.5 * (1 - u)) + jit(t, 53) * 0.006, -0.4);
        raised.rotation.set(0, 0, 0.35 + 0.05 * jit(t, 55, 12));
      }
      // Light: his face lit in the lunge; the corridor dims as the eyes come up; a warm glow on them as they reach you.
      if (inLunge) { const cl = R.toLocal(R.camera.position); R.L(cl.x, cl.y + 0.3, cl.z, glow.position); glow.intensity = 1.1; }
      else { R.L(C.x + ux * 0.4, 2.3, C.z + uz * 0.4, glow.position); glow.intensity = 1.6 * sstep(T_H1 - 0.6, T_H1, t); }
      R.L(C.x, 1.2, C.z, redLight.position); redLight.intensity = 0.3 * sstep(T_ANGRY, T_ANGRY + 0.3, t);
      const dim = sstep(T_ANGRY - 0.1, T_ANGRY + 0.3, t), back = sstep(T_H1 - 0.4, T_H1, t), dark = inLunge ? sstep(t0, t0 + 0.08, t) : 0;
      const hush = sstep(T_HALT, T_HALT + 0.6, t) * (1 - sstep(T_HIT, T_HIT + 0.05, t));
      f.env = { bake: (1 - 0.15 * sstep(0.2, 1.2, t) - 0.08 * hush - 0.4 * dim + 0.15 * back) * (1 - 0.8 * dark), lights: (1 - 0.15 * hush - 0.6 * dim + 0.3 * back) * (1 - 0.85 * dark), fogMul: 1 + 0.3 * sstep(1, 3, t) + 0.6 * dim + 2 * dark, fog: [0, 0, 0, dark] };
      f.tints = [[120, 0, 0, 0.05 * dim]];
      f.vig = [30, 0, 0, 0.15 * sstep(T_DIG, T_HALT, t) + 0.15 * hush + 0.3 * dim + 0.25 * sstep(T_FALL, DUR, t)]; f.vigR = 0.9;
      f.splats = hits.filter((h) => t >= h.t).map((h, i) => ({ t0: h.t, x: [0.35, 0.66, 0.5, 0.42][i], y: [0.42, 0.33, 0.6, 0.5][i], r: 13 + i * 3, seed: 21 + i }));
      f.black = 0.45 * sstep(DUR - 0.1, DUR + 0.6, t);
      lungeFx(L, t, f, { tear: 0.3 });
    }
    return { dur: DUR, hits, cam, update, sounds, loops, deathSide: fallSide,
      marks: { dread: T_SEE + 1.15, fake: digSw[nSw - 1] + 0.1, lunge: L.t1 + 0.14, kill: T_H1 + 0.3 },
      notes: { t0: +t0.toFixed(2), dur: +DUR.toFixed(2), ore: [+oc.x.toFixed(2), +oc.z.toFixed(2)], stand: [+C.x.toFixed(2), +C.z.toFixed(2)], from: sIn, nSw, hold: +hold.toFixed(2), fakeStep,
        spots: spots.map((s) => s.kind + "@" + s.x.toFixed(1) + "," + s.z.toFixed(1)), rushers: rushers.length, darts: darts.map((d) => +d.yaw.toFixed(2)) } };
  }
};
