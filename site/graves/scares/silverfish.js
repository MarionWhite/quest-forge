// Silverfish: the wall. A dry chittering somewhere close. The head turns to the wall beside you: one block of it
// moves. Again. Cracks spread across it and its neighbours (the block-breaking overlay), and the wall bursts: the
// infested stone empties, hundreds pour across the floor at you and up your legs, the view drops to the floor among
// them, and they crawl over the lens until it is dark.
import { THREE, clamp, lerp, sstep, pulse, tex, blockTexName, blockMesh, easeOut } from "./rig.js";
import { settle, shake, hitsOf, floorFall, mulberry } from "./common.js";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";

const TAU = Math.PI * 2;
const NOT_WALL = /air|torch|web|ladder|rail|fence|door|glass|water|lava|fire|sign|chest|spawner/;

// The library's silverfish (ModelSilverfish, its segment wiggle) baked into n poses across one wiggle period
// (0.9 rad a tick, 7 ticks): one merged geometry per pose, drawn as instances, so hundreds cost n draw calls.
function silverfishPoses(R, n = 8) {
  const m = R.mob("Silverfish", { amb: [0.2, 0.2, 0.21] });
  m.pivot.visible = false;
  const inv = new THREE.Matrix4(), rel = new THREE.Matrix4(), poses = [];
  for (let k = 0; k < n; k++) {
    m.anim((k / n) * (TAU / 0.9) / 20, 0, {});
    m.pivot.updateMatrixWorld(true);
    inv.copy(m.root.matrixWorld).invert();
    const parts = [];
    m.root.traverse((o) => { if (o.isMesh && o.visible) { const g = o.geometry.clone(); g.applyMatrix4(rel.multiplyMatrices(inv, o.matrixWorld)); parts.push(g); } });
    poses.push(mergeGeometries(parts, false));
    for (const g of parts) g.dispose();
  }
  return { mat: m.mat, poses };
}

export default {
  death: "Steve was slain by Silverfish",
  async build(R) {
    const stages = await Promise.all([...Array(10)].map((_, i) => tex("destroy_stage_" + i)));
    const r = mulberry(R.seed * 7 + 41);
    // The wall: a flat 3-wide, 2-high face of infestable stone (stone, cobblestone, stone brick) beside you, a step
    // ahead; the nearer side first. Failing that, any flat solid face.
    const sides = R.wallL <= R.wallR ? [-1, 1] : [1, -1];
    const INFEST = /^(stone|cobblestone|mossy_cobblestone|stonebrick|mossy_stonebrick|cracked_stonebrick|chiseled_stonebrick)$/;
    const findWall = (okName, dzs) => {
      for (const zc of [1.0, 1.5, 0.5, 2.0, 0.0, 2.5, 3.0, -0.5, 3.5, 4.0]) for (const side of sides) {
        const ds = [], names = [];
        for (const dz of dzs) for (const y of [0.5, 1.5]) ds.push(R.ray(0, y, zc + dz, side, 0, 0, 5, 0.05));
        const wall = Math.min(...ds);
        if (wall > 3.5 || Math.max(...ds) - wall > 0.2) continue;
        for (const dz of dzs) for (const y of [0.5, 1.5]) names.push(R.block(side * (wall + 0.5), y, zc + dz));
        if (names.every((b) => b && okName(b))) return { side, zc, wall, name: names[names.length >> 1], wide: dzs.length };
      }
      return null;
    };
    const isInf = (b) => INFEST.test(b), isWall = (b) => !NOT_WALL.test(b);
    const W = findWall(isInf, [-1, 0, 1]) || findWall(isInf, [0]) || findWall(isWall, [-1, 0, 1]) || { side: sides[0], zc: 1.0, wall: sides[0] < 0 ? R.wallL : R.wallR, name: "stone", wide: 3 };
    const { side, zc, wall } = W;
    const wb = (lx, ly, lz) => { const p = R.L(lx, ly, lz); return [Math.floor(p.x), Math.floor(p.y), Math.floor(p.z)]; };
    const face = [];   // the six wall blocks, world block coords; [0] is the one that moves
    face.push(wb(side * (wall + 0.5), 1.5, zc));
    for (const [dz, y] of W.wide === 1 ? [[0, 0.5]] : [[-1, 1.5], [1, 1.5], [0, 0.5], [-1, 0.5], [1, 0.5]]) face.push(wb(side * (wall + 0.5), y, zc + dz));
    const span = W.wide === 1 ? 0 : 1;
    const out = new THREE.Vector3(R.r.x * -side, 0, R.r.z * -side);   // from the wall toward you, world
    const wallTex = await tex(blockTexName(W.name));
    const fc = face[0], faceN = new THREE.Vector3(out.x, 0, out.z);
    const bake = R.bakeAt(new THREE.Vector3(fc[0] + 0.5 + out.x * 0.5, fc[1] + 0.5, fc[2] + 0.5 + out.z * 0.5), faceN) || new THREE.Vector3(0.2, 0.19, 0.18);
    const jolter = blockMesh(wallTex, { lit: true, amb: bake });
    jolter.visible = false; R.add(jolter);
    const crackMats = stages.map((t) => new THREE.MeshBasicMaterial({ map: t, transparent: true, alphaTest: 0.1, blending: THREE.CustomBlending, blendSrc: THREE.DstColorFactor, blendDst: THREE.SrcColorFactor, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -3, polygonOffsetUnits: -3, fog: false }));
    const crackGeo = new THREE.BoxGeometry(1.004, 1.004, 1.004);
    const cracks = face.map((b) => { const m = new THREE.Mesh(crackGeo, crackMats[0]); m.position.set(b[0] + 0.5, b[1] + 0.5, b[2] + 0.5); m.visible = false; m.renderOrder = 3; return R.add(m); });

    const T_SAY = 0.95, T_LOOK = 1.55, T_CRACK = 2.3, T_BREAK = 3.2, T_DOWN = 3.55, T_FALL = 4.95, DUR = 6.45;
    const jolts = [1.35, 1.63, 1.82, 2.12, 2.33, 2.52, 2.66, 2.8, 2.92, 3.02, 3.1, 3.16];
    const hits = hitsOf([[3.95, 3, -side], [4.45, 3, side], [T_FALL, 3, -side], [5.45, 3, side], [5.95, 3, -side], [DUR, 5, side]]);
    // Cracks: the moving block first, then its neighbours, all at stage 9 as it breaks.
    const crackAt = (i, t) => { const t0 = i === 0 ? T_CRACK : T_CRACK + 0.25 + 0.08 * i; return t < t0 ? -1 : Math.min(9, Math.floor((t - t0) / (T_BREAK - t0) * 10)); };
    const hole = () => {
      const a = wb(side * (wall + 0.5), 0.5, zc - span), b = wb(side * (wall + 2.5), 1.5, zc + span);
      R.carveW([Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.min(a[2], b[2])], [Math.max(a[0], b[0]), Math.max(a[1], b[1]), Math.max(a[2], b[2])]);
    };
    // Break particles: the wall's own stone, from each block.
    face.forEach((b, i) => { const l = R.toLocal({ x: b[0] + 0.5, y: b[1] + 0.5, z: b[2] + 0.5 }); R.burst(T_BREAK + 0.01 * i, [l.x - side * 0.4, l.y, l.z], 14, "stone", { dir: [-side * 1.6, 1.0, 0], speed: 2.6, spread: 1.1, size: 0.09, life: 1.4, stick: 4 }); });
    const fl = R.toLocal({ x: face[0][0] + 0.5, y: face[0][1] + 0.5, z: face[0][2] + 0.5 });
    jolts.forEach((tt, i) => R.burst(tt + 0.01, [fl.x - side * 0.52, fl.y - 0.45, fl.z], 3 + (i >> 2), "dust", { dir: [-side * 0.3, -0.4, 0], speed: 0.5, spread: 0.6, size: 0.025, life: 0.9 }));
    R.burst(T_BREAK, [side * (wall - 0.3), 1.0, zc], 30, "dust", { dir: [-side, 0.6, 0], speed: 1.6, spread: 1.4, size: 0.06, life: 1.6 });

    // The swarm.
    const N = 110, { mat, poses } = silverfishPoses(R, 8);
    const ims = poses.map((g) => { const im = new THREE.InstancedMesh(g, mat, N + 8); im.count = 0; im.frustumCulled = false; return R.add(im); });
    const camEnd = { x: 0, z: -0.15 };
    const fish = [];
    for (let i = 0; i < N; i++) {
      const te = T_BREAK + 0.03 + Math.pow(i / N, 0.8) * 2.2 + r() * 0.04;
      const hy = 0.1 + r() * 1.6, hz = zc + (r() - 0.5) * 2.6, hx = side * (wall + 0.2);
      // Where it ends up: packed round your feet, nearer ones first, in layers so they lie on each other.
      const a = r() * TAU, rad = 0.5 + Math.pow(i / N, 0.6) * 1.6 + r() * 0.3;
      let tx = clamp(Math.sin(a) * rad, -(R.wallL - 0.35), R.wallR - 0.35), tz = Math.cos(a) * rad * 0.9 + 0.35;
      if (Math.hypot(tx - camEnd.x, tz - camEnd.z) < 0.8) tz += 0.8;
      const land = [side * (wall - 0.35 - r() * 0.5), hz];
      fish.push({ te, hx, hy, hz, land, tx, tz, sp: 2.2 + r() * 1.4, ph: r() * 8, wig: 0.06 + r() * 0.08, heap: (i % 3) * 0.09 + r() * 0.03 });
    }
    // Up your legs: a few climb the front of you while you look down.
    const climbers = [...Array(7)].map((_, i) => ({ t0: 3.85 + i * 0.14, th: (i / 6 - 0.5) * 1.9, ph: r() * 8 }));
    // Over the lens: copies in the head's frame, drawn over everything.
    const lensMat = new THREE.MeshBasicMaterial({ map: mat.map, color: 0x8a8a92, alphaTest: 0.1, side: THREE.DoubleSide, depthTest: false, fog: false });
    const lens = [...Array(15)].map((_, i) => {
      const m = new THREE.Mesh(poses[0], lensMat); m.renderOrder = 2100 + i; m.visible = false; R.view.add(m);
      const edge = i % 4, e = (r() - 0.5);
      const from = edge === 0 ? [e * 0.7, -0.3] : edge === 1 ? [-0.5, e * 0.4] : edge === 2 ? [0.5, e * 0.4] : [e * 0.7, 0.3];
      return { m, t0: 4.3 + Math.pow(i / 15, 0.85) * 1.9, from, to: [(r() - 0.5) * 0.6, (r() - 0.5) * 0.32], s: 0.15 + r() * 0.07, ph: r() * 8, z: -0.3 - i * 0.004 };
    });

    const pose = (t, ph) => Math.floor(((t * 20 * 0.9) / TAU * 8 + ph) % 8 + 8) % 8;
    const fishAt = (q, t) => {
      const k1 = clamp((t - q.te) / 0.28);
      if (k1 < 1) {   // out of the hole and down to the floor
        return { x: lerp(q.hx, q.land[0], k1), y: q.hy * (1 - k1 * k1) + Math.sin(k1 * Math.PI) * 0.12, z: lerp(q.hz, q.land[1], k1), yaw: R.yawTo(q.hx, q.hz, q.land[0], q.land[1]), pitch: -0.6 * k1 };
      }
      const d = Math.hypot(q.tx - q.land[0], q.tz - q.land[1]), tr = d / q.sp, s = t - q.te - 0.28;
      if (s < tr) {
        const k = s / tr, dx = (q.tx - q.land[0]) / d, dz = (q.tz - q.land[1]) / d, w = Math.sin(t * 13 + q.ph) * q.wig * (1 - k);
        return { x: lerp(q.land[0], q.tx, k) - dz * w, y: q.heap * k, z: lerp(q.land[1], q.tz, k) + dx * w, yaw: R.yawTo(0, 0, dx, dz) + Math.cos(t * 13 + q.ph) * 0.2, pitch: 0 };
      }
      // There: pressing in at you, nosing forward and back, wriggling.
      const push = Math.sin((s - tr) * 7 + q.ph) * 0.05;
      const dx = camEnd.x - q.tx, dz = camEnd.z - q.tz, n = Math.hypot(dx, dz) || 1;
      return { x: q.tx + dx / n * push, y: q.heap, z: q.tz + dz / n * push, yaw: R.yawTo(q.tx, q.tz, camEnd.x, camEnd.z) + Math.sin(t * 11 + q.ph) * 0.2, pitch: 0 };
    };

    // The head: listens, turns to the wall, flinches, looks down at them at your feet, falls among them.
    const yWall = R.yawTo(0, 0, side * wall, zc), pWall = Math.atan2(1.4 - R.eye, Math.hypot(wall, zc));
    const cam = (t) => {
      const s = settle(R, t, 0.9);
      const k = sstep(0.8, 1.3, t);
      const look = sstep(T_LOOK, T_LOOK + 0.9, t), down = sstep(T_DOWN, T_DOWN + 0.5, t), feet = sstep(3.95, 4.4, t);
      const c = { x: s.x * (1 - k), y: s.y, z: s.z * (1 - k) - 0.15 * sstep(T_BREAK, T_BREAK + 0.15, t), yaw: lerp(s.yaw, 0.05 * side + yWall * look * (1 - 0.45 * down), k),
        pitch: lerp(s.pitch, lerp(lerp(-0.02, pWall, look), -0.62, down) - 0.5 * feet, k), roll: 0, fov: s.fov - 6 * sstep(T_CRACK, T_BREAK, t) * (1 - sstep(T_BREAK, T_BREAK + 0.1, t)) + 4 * sstep(T_BREAK, T_BREAK + 0.1, t) };
      c.x += 0.06 * side * sstep(T_BREAK, T_BREAK + 0.15, t) * -1;
      floorFall(c, t, T_FALL, { d: 0.5, side: -side, roll: 0.5, y: 0.2, pitch: 0.06, back: 0.15 });
      if (t > T_FALL) { const lk = sstep(T_FALL + 0.3, T_FALL + 0.9, t); c.yaw = lerp(c.yaw, yWall * 0.6, lk); c.pitch = lerp(c.pitch, 0.05, lk); }
      return shake(c, t, 0.0015 + 0.003 * sstep(T_LOOK, T_BREAK, t) + 0.03 * pulse(t, [T_BREAK], 0.25) + 0.02 * pulse(t, hits.map((h) => h.t), 0.18) + 0.006 * sstep(T_BREAK, T_FALL, t), 4);
    };
    hits.forEach((h, i) => { const c = cam(h.t), fx = -Math.sin(c.yaw), fz = Math.cos(c.yaw); R.burst(h.t, [c.x + fx * 0.35, Math.max(0.15, c.y - 0.9), c.z + fz * 0.35], 16, "blood", { dir: [fx * 0.4, 0.8, fz * 0.4], speed: 1.6, spread: 0.8, size: 0.04, life: 1.1, stick: 3 }); });

    const bc = R.toLocal({ x: face[0][0] + 0.5, y: face[0][1] + 0.5, z: face[0][2] + 0.5 });
    const at = [bc.x, bc.y, bc.z];
    const sounds = [
      [T_SAY, "mob.silverfish.say", { at, volume: 0.35, pitch: 0.9 }],
      ...jolts.map((tt, i) => [tt, i % 3 === 2 ? "dig.stone" : "step.stone", { at, volume: 0.35 + 0.04 * i, pitch: 0.5 + 0.03 * i }]),
      [2.0, "mob.silverfish.say", { at, volume: 0.5 }], [2.7, "mob.silverfish.say", { at, volume: 0.6, pitch: 1.1 }],
      [T_BREAK, "dig.stone", { at, volume: 1, pitch: 0.8 }], [T_BREAK + 0.03, "dig.stone", { at: [bc.x, 0.5, bc.z + 1], volume: 1, pitch: 1.0 }], [T_BREAK + 0.06, "dig.stone", { at: [bc.x, 0.5, bc.z - 1], volume: 1, pitch: 0.9 }],
      [T_BREAK + 0.02, "qf.scare.stinger", { volume: 0.9 }], [T_BREAK + 0.05, "qf.scare.shriek", { volume: 0.4, pitch: 1.3 }],
      ...[...Array(10)].map((_, i) => [T_BREAK + 0.1 + i * 0.28, "mob.silverfish.say", { at: [side * (wall - 0.5 - i * 0.15), 0.3, zc + (i % 3 - 1)], volume: 0.8, pitch: 0.85 + 0.05 * (i % 5) }]),
      ...[...Array(16)].map((_, i) => [T_BREAK + 0.2 + i * 0.18, "mob.silverfish.step", { at: [side * (wall - 0.8) * (1 - i / 16), 0.1, zc * (1 - i / 16)], volume: 0.6 }]),
      ...hits.flatMap((h, i) => [[h.t, "game.player.hurt"], [h.t + 0.02, i % 2 ? "qf.scare.gore" : "qf.scare.crunch", { volume: 0.7 }]]),
      [T_FALL + 0.45, "game.player.hurt.fall.small"], [T_FALL + 0.1, "qf.scare.scream", { volume: 0.9 }],
      [DUR, "game.player.die"], [DUR, "@muffle", { hz: 300, s: 3 }]
    ];
    const loops = [
      [0.5, DUR + 0.2, "qf.scare.heartbeat", { volume: 0.5 }],
      [0.6, T_BREAK, "qf.scare.chitter", { at, volume: 0.25, fadeIn: 1.5, fadeOut: 0.05 }],
      [T_BREAK, DUR + 0.5, "qf.scare.chitter", { volume: 0.9, fadeIn: 0.1 }],
      [T_FALL + 0.4, DUR, "qf.scare.breath", { volume: 0.5, fadeIn: 0.3 }]
    ];

    const M = new THREE.Matrix4(), Q = new THREE.Quaternion(), E = new THREE.Euler(), P = new THREE.Vector3(), S1 = new THREE.Vector3(1, 1, 1);
    const put = (fi, x, y, z, yaw, pitch) => {
      const im = ims[fi]; if (im.count >= N + 8) return;
      R.L(x, y, z, P); E.set(pitch, R.yaw0 + yaw, 0, "YXZ"); Q.setFromEuler(E);
      im.setMatrixAt(im.count++, M.compose(P, Q, S1));
    };
    function update(t, f) {
      // The moving block: out of the wall on each jolt, cracked.
      const j = Math.max(...jolts.map((tt) => (t >= tt && t < tt + 0.09 ? 1 - (t - tt) / 0.09 : 0)));
      jolter.visible = j > 0 && t < T_BREAK;
      const b0 = face[0];
      if (jolter.visible) {
        const o = 0.015 + 0.09 * j;
        jolter.position.set(b0[0] + 0.5 + out.x * o, b0[1] + 0.5 + Math.sin(t * 91) * 0.006 * j, b0[2] + 0.5 + out.z * o);
        jolter.rotation.set(Math.sin(t * 73) * 0.02 * j, Math.sin(t * 59) * 0.02 * j, 0);
      }
      cracks.forEach((m, i) => {
        const s = crackAt(i, t);
        m.visible = s >= 0 && t < T_BREAK;
        if (!m.visible) return;
        m.material = crackMats[s];
        if (i === 0 && jolter.visible) m.position.copy(jolter.position); else m.position.set(face[i][0] + 0.5, face[i][1] + 0.5, face[i][2] + 0.5);
      });
      if (t >= T_BREAK) R.once("hole", hole);
      // The swarm.
      for (const im of ims) im.count = 0;
      for (const q of fish) { if (t < q.te) continue; const p = fishAt(q, t); put(pose(t, q.ph), p.x, p.y, p.z, p.yaw, p.pitch); }
      if (t < T_FALL + 0.1) for (const c of climbers) {
        if (t < c.t0) continue;
        const y = Math.min(1.25, (t - c.t0) * 0.75), x = Math.sin(c.th) * 0.2, z = Math.cos(c.th) * 0.17;
        put(pose(t, c.ph), x, y, z, R.yawTo(x, z, 0, 0), Math.PI / 2);
      }
      for (const im of ims) im.instanceMatrix.needsUpdate = true;
      // The lens.
      for (const q of lens) {
        q.m.visible = t >= q.t0;
        if (!q.m.visible) continue;
        const k = easeOut((t - q.t0) / 0.9), w = Math.sin(t * 9 + q.ph) * 0.012;
        const x = lerp(q.from[0], q.to[0], k) + w, y = lerp(q.from[1], q.to[1], k);
        const head = Math.atan2(q.to[0] - q.from[0], q.to[1] - q.from[1]);
        q.m.geometry = poses[pose(t, q.ph)];
        q.m.position.set(x, y, q.z); q.m.scale.setScalar(q.s);
        q.m.rotation.set(Math.PI / 2, 0, -head + Math.sin(t * 7 + q.ph) * 0.15, "ZYX");
      }
      const cover = sstep(4.3, DUR, t);
      f.env = { bake: 1 - 0.2 * sstep(0.2, 1.2, t) - 0.25 * cover, fogMul: 1 + 0.5 * sstep(1, 3, t) + 0.5 * sstep(T_BREAK, T_BREAK + 0.6, t) };
      f.vig = [0, 0, 0, 0.25 * sstep(T_LOOK, T_BREAK, t) + 0.55 * cover]; f.vigR = 0.9 - 0.25 * cover;
      f.splats = hits.filter((h) => t >= h.t).map((h, i) => ({ t0: h.t, x: [0.3, 0.7, 0.5, 0.4, 0.62, 0.45][i], y: [0.6, 0.55, 0.4, 0.66, 0.3, 0.5][i], r: 10 + i * 2, seed: 31 + i }));
      f.black = 0.3 * sstep(DUR - 0.6, DUR + 0.4, t);
    }
    return { dur: DUR, hits, cam, update, sounds, loops, deathSide: -side, notes: { wall: W, face, fish: N } };
  }
};
