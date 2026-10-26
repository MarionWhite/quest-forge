// Zombie Pigman: your fault. A pigman wanders out of a side passage, grunting, minding its own business, close by.
// Your hand twitches: the sword swings and catches it. Silence. It turns its head. Every eye in the dark goes red,
// the angry squeal comes from everywhere at once, and they rush you from every passage.
import { THREE, clamp, lerp, sstep, pulse, tex, easeOut } from "./rig.js";
import { settle, shake, hitsOf, floorFall, heldItem, halo, swingAt, zombieArms, mulberry } from "./common.js";

const SWORD = [{ id: "minecraft:golden_sword", ench: false }];
const TAU = Math.PI * 2;
const wrap = (a) => { while (a > Math.PI) a -= TAU; while (a < -Math.PI) a += TAU; return a; };

// The pigman's two eyes, lit red: the skull's socket (base layer) and the pink eye on the hat layer (inflated 0.5).
// In the head part's frame (metres; x and y a half turn from Minecraft's), plus a halo in the scene.
function redEyes(R, m) {
  const head = m.parts.head;
  const mat = new THREE.MeshBasicMaterial({ color: 0x000000, fog: false, side: THREE.DoubleSide, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2 });
  mat.userData.noFlash = true;
  const mk = (x, y, z, w, h) => { const q = new THREE.Mesh(new THREE.PlaneGeometry(w / 16, h / 16), mat); q.position.set(-x / 16, -y / 16, z / 16); q.visible = false; if (head) head.add(q); return q; };
  const eyes = [mk(-3, -4.5, -4.06, 2, 1), mk(3.375, -4.56, -4.58, 2.25, 1.125)];
  const glow = halo(R, 0xff1808, 0.4);
  const hp = new THREE.Vector3();
  return (on) => {
    const vis = on > 0.01 && !!head;
    for (const e of eyes) e.visible = vis;
    glow.visible = vis;
    if (!vis) return;
    mat.color.setRGB(on, 0.1 * on, 0.05 * on);
    glow.material.opacity = 0.3 * on;
    m.pivot.updateMatrixWorld(true);
    head.localToWorld(hp.set(0, 4.5 / 16, -0.3));
    glow.position.copy(hp);
  };
}

export default {
  death: "Steve was slain by Zombie Pigman",
  async build(R) {
    const swordTex = await tex("item_iron_sword");
    const rnd = mulberry(R.seed * 13 + 5);
    const ok = (x, z) => !R.solid(x, 0.5, z) && !R.solid(x, 1.5, z) && R.solid(x, -0.5, z);
    const inX = (x) => clamp(x, -(R.wallL - 0.35), R.wallR - 0.35);
    // Where pigmen can be: the side passages and alcoves around you, and the corridor far ahead and behind.
    const spots = [];
    const push = (x, z, kind) => { if (!ok(x, z) || spots.some((s) => Math.hypot(s.x - x, s.z - z) < 1.3)) return; spots.push({ x, z, kind }); };
    for (const p of R.passages) if (p.dist < 14) push(p.x + p.side * 2.2, p.z, "passage");
    for (const o of R.openings) if (o.z > -9 && o.z < 13) push(o.side * (o.wall + clamp(o.depth - o.wall - 0.6, 0.4, 3)), o.z, "opening");
    if (R.ahead > 3.5) push(inX(0.3), Math.min(R.ahead - 0.7, 6.5), "ahead");
    if (R.ahead > 8) push(inX(-0.35), Math.min(R.ahead - 0.7, 11), "ahead");
    if (R.behind > 3.5) push(inX(-0.2), -Math.min(R.behind - 0.7, 5.5), "behind");
    if (R.behind > 8) push(inX(0.35), -Math.min(R.behind - 0.7, 9.5), "behind");
    // The one you hit: out of a side passage in front of you if there is one, else from down the corridor.
    const side0 = spots.filter((s) => s.kind !== "ahead" && s.kind !== "behind" && s.z > 0.3 && s.z < 6).sort((a, b) => Math.hypot(a.x, a.z) - Math.hypot(b.x, b.z))[0];
    const A = side0 || spots.find((s) => s.kind === "ahead") || { x: inX(0.4), z: clamp(R.ahead - 0.8, 2.5, 5), kind: "ahead" };
    const sideB = A.kind === "ahead" ? (R.wallR >= R.wallL ? 1 : -1) : Math.sign(A.x) || 1;
    const B = { x: inX(A.kind === "ahead" ? 0.45 * sideB : clamp(A.x * 0.3, -0.7, 0.7)), z: clamp(A.z, 1.6, 2.0) };
    const dAB = Math.hypot(B.x - A.x, B.z - A.z);
    if (dAB > 2.6) { const k = 1 - 2.6 / dAB; A.x = lerp(A.x, B.x, k); A.z = lerp(A.z, B.z, k); }
    const away = Math.hypot(B.x, B.z), K = { x: inX(B.x + (B.x / away) * 0.6), z: B.z + (B.z / away) * 0.6 };
    const L0 = { x: K.x * 0.8 / Math.hypot(K.x, K.z), z: K.z * 0.8 / Math.hypot(K.x, K.z) };

    const T_W0 = 0.4, T_W1 = T_W0 + clamp(Math.hypot(B.x - A.x, B.z - A.z) / 1.3, 0.8, 2.0);
    const T_SW = 2.95, T_TURN0 = 3.25, T_TURN1 = 3.85, T_ANGRY = 4.0, T_RUSH = 4.6, T_FALL = 5.9, DUR = 6.4;
    const walkYaw = R.yawTo(A.x, A.z, B.x, B.z);
    const idleYaw = A.kind === "ahead" ? -sideB * Math.PI / 2 : walkYaw;
    const p0 = R.mob("PigZombie", { amb: [0.24, 0.22, 0.22], equipment: SWORD });
    const eyes0 = redEyes(R, p0);
    const pos0 = (t) => {
      if (t < T_W0) return { x: A.x, y: 0, z: A.z };
      if (t < T_W1) { const k = (t - T_W0) / (T_W1 - T_W0); return { x: lerp(A.x, B.x, k), y: 0, z: lerp(A.z, B.z, k) }; }
      if (t < T_SW) return { x: B.x, y: 0, z: B.z };
      if (t < T_SW + 0.35) { const k = (t - T_SW) / 0.35, e = easeOut(k); return { x: lerp(B.x, K.x, e), y: Math.sin(k * Math.PI) * 0.22, z: lerp(B.z, K.z, e) }; }
      const k = sstep(T_RUSH, T_RUSH + 0.26, t), out = 1 + 1.05 * sstep(T_FALL, T_FALL + 0.5, t);   // it steps back into the ring
      return { x: lerp(K.x, L0.x * out, k), y: 0, z: lerp(K.z, L0.z * out, k) };
    };

    // The others: eyes open in every dark place around you, then they come.
    const rest = spots.filter((s) => s !== A).sort((a, b) => Math.abs(R.yawTo(0, 0, a.x, a.z)) - Math.abs(R.yawTo(0, 0, b.x, b.z))).slice(0, 6);
    // Ring slots round you, evenly spaced from the first one's, kept in the order they come from.
    const ang0 = Math.atan2(L0.x, L0.z), nR = rest.length;
    const order = rest.map((s, i) => [((Math.atan2(s.x, s.z) - ang0) % TAU + TAU) % TAU, i]).sort((a, b) => a[0] - b[0]);
    const angles = new Array(nR);
    order.forEach(([, i], j) => { angles[i] = ang0 + (j + 1) * TAU / (nR + 1); });
    const rushers = rest.map((s, i) => {
      let tx = inX(Math.sin(angles[i]) * 1.35), tz = Math.cos(angles[i]) * 1.35;
      if (Math.hypot(tx, tz) < 1.0) tz = Math.sign(tz || 1) * Math.sqrt(Math.max(1.0 - tx * tx, 0.36));
      const path = [[s.x, s.z]];
      if (s.kind === "opening" || s.kind === "passage") path.push([inX(Math.sign(s.x) * 9), s.z]);
      path.push([tx, tz]);
      let len = 0; for (let q = 1; q < path.length; q++) len += Math.hypot(path[q][0] - path[q - 1][0], path[q][1] - path[q - 1][1]);
      const ts = T_RUSH + 0.04 * i;
      return { ...s, m: R.mob("PigZombie", { amb: [0.17, 0.15, 0.15], equipment: SWORD }), path, len, ts, te: ts + clamp(len / 6.5, 0.45, 1.3), ta: T_ANGRY + 0.1 + 0.075 * i, tx, tz, seed: rnd() * 10 };
    });
    for (const q of rushers) q.eyes = redEyes(R, q.m);
    const byArrival = rushers.slice().sort((a, b) => a.te - b.te);
    if (byArrival[0]) byArrival[0].te = Math.min(byArrival[0].te, 5.2);
    if (byArrival[1]) byArrival[1].te = Math.min(byArrival[1].te, 5.7);
    const hitList = [[4.9, 4, p0], [5.4, 4, byArrival[0] || p0], [T_FALL, 5, byArrival[1] || byArrival[0] || p0], [DUR, 7, byArrival[2] || p0]];
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
    for (const q of rushers) q.path = q.path.map(([x, z], i) => i === 1 ? [clamp(x, -(R.wallL - 0.4), R.wallR - 0.4), z] : [x, z]);
    // Swings: the attackers' land on the hits; the rest flail when they get there (the i-frames eat them).
    const swings = new Map([[p0, [4.9]]]);
    for (const q of rushers) {
      const s = []; for (let tt = q.te + 0.15 + rnd() * 0.25; tt < DUR + 2; tt += 0.55 + rnd() * 0.2) s.push(tt);
      swings.set(q, s);
    }
    hitList.forEach(([t, , w]) => { const s = swings.get(w); if (!s.includes(t)) s.push(t); });
    const attackerAt = (h) => { const w = hitList.find((x) => x[0] === h.t)[2]; return w === p0 ? L0 : { x: w.tx, z: w.tz }; };
    hits.forEach((h) => { const a = attackerAt(h); h.side = a.x >= 0 ? -1 : 1; });

    // The head: follows the pigman as it wanders past; frozen after the hit; flicks to the eyes; knocked down.
    const yq = (q) => R.yawTo(0, 0, q.x, q.z), near = (a, b) => Math.hypot(a.x, a.z) - Math.hypot(b.x, b.z);
    const darts = [rushers.filter((q) => yq(q) > 0.45 && yq(q) < 1.5).sort(near)[0], rushers.filter((q) => yq(q) < -0.45 && yq(q) > -1.5).sort(near)[0]]
      .filter(Boolean).map((q) => ({ yaw: yq(q), q }));
    darts.forEach((d, i) => { d.t = 4.12 + i * 0.26; d.q.ta = Math.min(d.q.ta, d.t - 0.12); });
    const follow = (t) => { const p = pos0(Math.max(0, t - 0.22)); return clamp(R.yawTo(0, 0, p.x, p.z), -1.45, 1.45); };
    const yawAt = (t) => {
      let y = follow(t);
      if (t > 4.0 && t < 4.75 && darts.length) {
        const keys = [[4.0, follow(4.0)], ...darts.flatMap((d) => [[d.t - 0.1, null], [d.t + 0.06, d.yaw]]), [4.62, follow(4.62)]];
        let prevT = 4.0, prevY = follow(4.0);
        for (const [kt, ky] of keys.slice(1)) {
          const target = ky ?? prevY;
          if (t <= kt) { y = lerp(prevY, target, sstep(prevT, kt, t)); break; }
          prevT = kt; prevY = target; y = target;
        }
        if (t > 4.62) y = lerp(y, follow(t), sstep(4.62, 4.75, t));
      }
      return y;
    };
    const knock = (t) => {
      let x = 0, z = 0;
      for (const h of hits) { if (t < h.t) break; const a = attackerAt(h), n = Math.hypot(a.x, a.z) || 1, k = 0.2 * easeOut((t - h.t) / 0.25); x -= a.x / n * k; z -= a.z / n * k; }
      return { x, z };
    };
    const camAlive = (t) => {
      const s = settle(R, t, 0.9);
      const k = sstep(0.75, 1.3, t);
      const kb = knock(t);
      const c = { x: s.x * (1 - k) + kb.x, y: s.y, z: s.z * (1 - k) + kb.z, yaw: lerp(s.yaw, yawAt(t), k), pitch: lerp(s.pitch, -0.04, k), roll: 0,
        fov: s.fov - 7 * sstep(T_TURN0, T_ANGRY, t) * (1 - sstep(T_ANGRY, T_ANGRY + 0.15, t)) + 5 * sstep(T_ANGRY, T_ANGRY + 0.1, t) };
      return c;
    };
    const fallSide = hits[2] ? -hits[2].side : 1;
    const cam = (t) => {
      const c = camAlive(Math.min(t, T_FALL + 0.001));
      if (t > T_FALL) { c.x = camAlive(t).x; c.z = camAlive(t).z; }
      floorFall(c, t, T_FALL, { d: 0.5, side: fallSide, roll: 0.55, y: 0.3, pitch: 0.2, back: 0.15 });
      // On the floor: looking up into the ring of them.
      const up = sstep(T_FALL + 0.35, T_FALL + 0.75, t);
      c.pitch = lerp(c.pitch, 1.0, up); c.fov += 8 * up; c.yaw += 0.25 * fallSide * up;
      return shake(c, t, 0.002 + 0.004 * sstep(T_TURN0, T_ANGRY, t) + 0.02 * pulse(t, hits.map((h) => h.t), 0.18) + 0.01 * sstep(T_RUSH, T_RUSH + 0.3, t), 7);
    };

    // Gore: from your chest and neck, toward the camera, at each hit.
    hits.forEach((h, i) => {
      const c = cam(h.t + 0.01), fx = -Math.sin(c.yaw), fz = Math.cos(c.yaw);
      const at = [c.x + fx * 0.4, Math.max(0.25, c.y - 0.45), c.z + fz * 0.4];
      R.burst(h.t, at, 26, "blood", { dir: [fx * 0.6, 0.9, fz * 0.6], speed: 2.2, spread: 0.8, size: 0.05, life: 1.3, stick: 3 });
      R.burst(h.t + 0.02, at, 7, "flesh", { dir: [fx * 0.4, 0.8, fz * 0.4], speed: 1.6, spread: 0.7, size: 0.07, life: 1.2, stick: 3 });
    });
    const sword = heldItem(R, swordTex);
    const mySwings = [T_SW, 5.12];
    const glow = R.ownLight(R.light(0xffb070, 0, 6, 1.4));
    const redLight = R.ownLight(R.light(0xff2010, 0, 9, 1.2));

    const steps = [];
    for (let s = T_W0 + 0.2; s < T_W1; s += 0.42) { const p = pos0(s); steps.push([s, "mob.zombie.step", { at: [p.x, 0.1, p.z], volume: 0.32 }]); }
    for (const q of rushers) for (let s = q.ts + 0.12; s < q.te; s += 0.3) { const p = posR(q, s); steps.push([s, "mob.zombie.step", { at: [p.x, 0.1, p.z], volume: 0.45, pitch: 1.1 }]); }
    const sounds = [
      [T_W0 + 0.1, "mob.zombiepig.zpig", { at: [A.x, 1.6, A.z], volume: 0.9 }],
      [T_W1 + 0.25, "mob.zombiepig.zpig", { at: [B.x, 1.6, B.z], volume: 0.75, pitch: 0.95 }],
      ...steps.slice(0, 40),
      [T_SW + 0.01, "mob.zombiepig.zpighurt", { at: [B.x, 1.6, B.z], volume: 1 }],
      [T_ANGRY, "mob.zombiepig.zpigangry", { at: [K.x, 1.6, K.z], volume: 1, pitch: 0.95 }],
      [T_ANGRY + 0.02, "qf.scare.stinger", { volume: 0.85 }],
      ...rushers.map((q, i) => [q.ta + 0.02, "mob.zombiepig.zpigangry", { at: [q.x, 1.6, q.z], volume: 0.9, pitch: 0.82 + 0.09 * (i % 5), reverb: 0.5 }]),
      [T_RUSH - 0.35, "qf.scare.riser", { volume: 0.55 }],
      [T_RUSH + 0.2, "mob.zombiepig.zpigangry", { at: [L0.x, 1.6, L0.z], volume: 1, pitch: 1.1 }],
      ...hits.flatMap((h, i) => [[h.t, "game.player.hurt"], [h.t + 0.01, "qf.scare.hit", { volume: 0.9 }], [h.t + 0.03, i % 2 ? "qf.scare.gore" : "qf.scare.crunch", { volume: 0.9 }]]),
      ...[5.05, 5.6, 6.1].map((tt, i) => { const q = rushers[i % Math.max(1, rushers.length)]; return [tt, "mob.zombiepig.zpigangry", { at: q ? [q.tx, 1.6, q.tz] : [0, 1.6, 1], volume: 0.9, pitch: 0.9 + 0.12 * i }]; }),
      [T_FALL + 0.45, "game.player.hurt.fall.small"], [T_FALL + 0.1, "qf.scare.scream", { volume: 0.9 }],
      [DUR, "game.player.die"], [DUR, "@muffle", { hz: 380, s: 3 }]
    ];
    const loops = [
      [0.5, T_SW + 0.02, "qf.scare.heartbeat", { volume: 0.5, fadeOut: 0.02 }],
      [T_ANGRY, DUR + 0.2, "qf.scare.heartbeat", { volume: 0.6, pitch: 1.3, fadeIn: 0.05 }],
      [T_TURN0, DUR, "qf.scare.drone", { volume: 0.45, fadeIn: 1.2 }]
    ];

    function posePig(m, t, x, y, z, yaw, { walk = 0, run = false, look = 0, swing = 0, lean = 0, seed = 0 } = {}) {
      R.place(m, x, y, z, yaw, lean);
      m.anim((t + seed) * (run ? 1.6 : 1), 0, { walk, lookAt: look });
      zombieArms(m, t + seed, swing);
    }
    function update(t, f) {
      // The one you hit.
      const p = pos0(t), camNow = cam(t);
      const toCam = R.yawTo(p.x, p.z, camNow.x, camNow.z);
      let yaw = t < T_W1 ? walkYaw : lerp(walkYaw, idleYaw, sstep(T_W1, T_W1 + 0.5, t));
      let look = Math.sin(t * 0.9) * 0.25 * (t < T_SW ? 1 : 0);
      if (t > T_SW) {   // the head turns first, then the body
        const want = wrap(toCam - yaw);
        const hk = sstep(T_TURN0, T_TURN1, t), bk = sstep(T_TURN1 - 0.15, T_ANGRY + 0.1, t);
        yaw = yaw + want * bk;
        look = -clamp(want * (1 - bk), -1.3, 1.3) * hk;
      }
      const lean0 = -0.22 * sstep(T_FALL + 0.2, T_FALL + 0.8, t);
      posePig(p0, t, p.x, p.y, p.z, yaw, { walk: t > T_W0 && t < T_W1 ? 0.7 : (t > T_RUSH && t < T_RUSH + 0.26 ? 1.2 : 0), look, swing: swingAt(t, swings.get(p0)), lean: lean0 });
      R.flash(p0, t > T_SW && t < T_SW + 0.5 ? 1 : 0);
      eyes0(sstep(T_ANGRY - 0.06, T_ANGRY + 0.04, t));
      // Everyone else.
      for (const q of rushers) {
        q.m.pivot.visible = t >= q.ta;
        q.eyes(t >= q.ta ? sstep(q.ta, q.ta + 0.1, t) : 0);
        if (t < q.ta) continue;
        const r = posR(q, t), there = r.k >= 1, wide = 1 + 0.22 * sstep(T_FALL, T_FALL + 0.5, t);   // a step back to look at you
        r.x *= there ? wide : 1; r.z *= there ? wide : 1;
        const fy = there ? R.yawTo(q.tx, q.tz, camNow.x, camNow.z) : (t < q.ts ? R.yawTo(q.x, q.z, 0, 0) : r.dir);
        posePig(q.m, t, r.x, 0, r.z, fy, { walk: t > q.ts && !there ? 1.35 : 0, run: true, swing: swingAt(t, swings.get(q)), lean: -0.22 * sstep(T_FALL + 0.2, T_FALL + 0.9, t), seed: q.seed });
      }
      sword(t, mySwings, t > T_FALL + 0.05, camNow.fov);
      // Light: the corridor dims as the eyes come up; a warm glow on them as they reach you.
      R.L(0, 2.3, 0.4, glow.position); glow.intensity = 1.6 * sstep(T_RUSH, T_RUSH + 0.6, t);
      R.L(0, 1.2, 0, redLight.position); redLight.intensity = 0.3 * sstep(T_ANGRY, T_ANGRY + 0.3, t);
      const dim = sstep(T_ANGRY - 0.1, T_ANGRY + 0.3, t), back = sstep(T_RUSH, T_RUSH + 0.5, t);
      f.env = { bake: 1 - 0.2 * sstep(0.2, 1.2, t) - 0.4 * dim + 0.15 * back, lights: 1 - 0.6 * dim + 0.3 * back, fogMul: 1 + 0.5 * sstep(1, 3, t) + 0.6 * dim };
      f.tints = [[120, 0, 0, 0.05 * dim]];
      f.vig = [30, 0, 0, 0.25 * sstep(1, 2.5, t) + 0.3 * dim + 0.25 * sstep(T_FALL, DUR, t)]; f.vigR = 0.9;
      f.splats = hits.filter((h) => t >= h.t).map((h, i) => ({ t0: h.t, x: [0.35, 0.66, 0.5, 0.42][i], y: [0.42, 0.33, 0.6, 0.5][i], r: 13 + i * 3, seed: 21 + i }));
      f.black = 0.45 * sstep(DUR - 0.1, DUR + 0.6, t);
    }
    return { dur: DUR, hits, cam, update, sounds, loops, deathSide: fallSide,
      notes: { A, B, K, spots: spots.map((s) => s.kind + "@" + s.x.toFixed(1) + "," + s.z.toFixed(1)), rushers: rushers.map((q) => [+q.tx.toFixed(2), +q.tz.toFixed(2), +q.ta.toFixed(2), +q.te.toFixed(2)]), darts: darts.map((d) => +d.yaw.toFixed(2)) } };
  }
};
