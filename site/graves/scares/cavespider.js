// Cave Spider (piston trap): a click under your feet; the floor is yanked out and you drop into a pit strung with
// cobweb, and the web catches you short of the floor. Stuck. In the corner a spawner cage burns, its little spider
// spinning. Hissing from the walls; then they come out of the cracks, dozens, across the floor and up the strands to
// you. Each bite poisons: the hearts go green and the view pulses green until their legs close over it.
import { THREE, clamp, lerp, sstep, pulse, tex, easeOut } from "./rig.js";
import { settle, shake, hitsOf, particles, mulberry, lensLimbs, bakePoses, swarm, webs } from "./common.js";
import { pistonTrap } from "./piston.js";

export default {
  death: "Steve was slain by Cave Spider",
  async build(R) {
    const [webTex, partTex, cageTex, ...cracks] = await Promise.all([tex("web"), tex("particles"), tex("k:mob_spawner"), tex("destroy_stage_6"), tex("destroy_stage_8")]);
    const r = mulberry(R.seed * 11 + 3);
    const trap = await pistonTrap(R, { click: 1.1, open: 1.8, D: 7, web: true });
    const { roomBox: rb, loc, a, b } = trap;
    const Dp = trap.D, y0 = -Dp;   // the pit floor, local
    // Cobweb: two blocks deep under the hole (you land in it), and strung round the room.
    const W = [];
    for (const i of [a, a + 1]) for (const k of [b, b + 1]) for (const j of [-Dp, -Dp + 1]) { const p = loc(i, j, k); W.push([p.x, p.y, p.z]); }
    for (const [i, j, k] of [[rb.i0, -2, rb.k0], [rb.i1, -2, rb.k0], [rb.i0, -2, rb.k1], [rb.i1, -2, rb.k1], [rb.i0, -Dp, rb.k0], [rb.i1, -Dp + 1, rb.k0], [rb.i0, -3, rb.k1],
      [a - 1, -2, b], [a + 2, -3, b + 1], [rb.i0, -Dp, b + 1], [rb.i1, -Dp, b], [a, -2, rb.k1], [a + 1, -Dp, rb.k0]]) { const p = loc(i, j, k); W.push([p.x, p.y, p.z]); }
    webs(R, webTex, W);
    // The spawner, burning, in the far corner with its spinning spider.
    const sp = loc(rb.i1, -Dp, rb.k1);
    const cageMat = new THREE.MeshLambertMaterial({ map: cageTex, transparent: false, alphaTest: 0.1, side: THREE.DoubleSide });
    if (R.patchBake) R.patchBake(cageMat, { fixed: new THREE.Vector3(0.25, 0.2, 0.15) });
    const cage = R.add(new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), cageMat)); R.at(cage, sp.x, sp.y, sp.z); cage.rotation.y = R.yaw0;
    const mini = R.mob("CaveSpider", { amb: [0.3, 0.25, 0.2] });
    mini.pivot.scale.setScalar(0.45);
    const flames = [];
    for (let i = 0; i < 60; i++) { const t0 = trap.open + r() * 6; flames.push({ t0, at: [sp.x + (r() - 0.5) * 0.8, sp.y - 0.3 + r() * 0.6, sp.z + (r() - 0.5) * 0.8], v: [0, 0.15, 0], life: 0.5 + r() * 0.3, size: 0.07, tile: 48, color: [1, 0.85, 0.6], grav: -0.2, fog: false, add: true }); }
    for (let i = 0; i < 24; i++) { const t0 = trap.open + r() * 6; flames.push({ t0, at: [sp.x + (r() - 0.5) * 0.6, sp.y + 0.3, sp.z + (r() - 0.5) * 0.6], v: [0, 0.4, 0], life: 1.2, size: 0.18, color: [0.07, 0.07, 0.07], grav: -0.3 }); }
    const fire = particles(R, partTex, flames);
    const fireLight = R.ownLight(R.light(0xff9a40, 0, 7, 1.3));

    // The swarm: the library's cave spider walking, baked into 8 poses (one stride, 0.674 s), instanced.
    const baked = bakePoses(R, "CaveSpider", { n: 8, period: 0.674, anim: { walk: 1 }, amb: [0.14, 0.14, 0.16] });
    const N = 34, S = swarm(R, baked, N + 2);
    // Where they come out: cracks low in the walls (the overlay on the real blocks), all round the room.
    const exits = [];
    const wallAt = (i, k) => loc(i, -Dp, k);
    for (let n = 0; n < 7; n++) {
      const s = n % 4, along = r();
      const i = s === 0 ? rb.i0 - 1 : s === 1 ? rb.i1 + 1 : Math.round(lerp(rb.i0, rb.i1, along));
      const k = s === 2 ? rb.k0 - 1 : s === 3 ? rb.k1 + 1 : Math.round(lerp(rb.k0, rb.k1, along));
      const c = wallAt(i, k), j = r() < 0.5 ? 0 : 1;
      exits.push({ x: c.x, y: y0 + 0.5 + j, z: c.z, i, k, j });
    }
    const crackMats = cracks.map((t) => new THREE.MeshBasicMaterial({ map: t, transparent: true, alphaTest: 0.1, blending: THREE.CustomBlending, blendSrc: THREE.DstColorFactor, blendDst: THREE.SrcColorFactor, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -3, polygonOffsetUnits: -3, fog: false }));
    exits.forEach((e, n) => { const m = new THREE.Mesh(new THREE.BoxGeometry(1.004, 1.004, 1.004), crackMats[n % 2]); const c = trap.cen(e.i, -Dp + e.j, e.k); m.position.copy(c); R.add(m); e.m = m; });
    const me = { x: trap.hole.x, z: trap.hole.z };
    const spiders = [];
    for (let n = 0; n < N; n++) {
      const e = exits[n % exits.length], te = 3.7 + Math.pow(n / N, 0.9) * 2.4 + r() * 0.1;
      const ang = r() * Math.PI * 2, rad = 0.15 + r() * 0.5;
      spiders.push({ e, te, tx: me.x + Math.cos(ang) * rad, tz: me.z + Math.sin(ang) * rad, sp: 2.2 + r() * 1.2, ph: r() * 8, climb: n % 3 !== 2, cy: trap.stopEye - R.eye - 0.1 - r() * 0.3 });
    }
    const spiderAt = (q, t) => {
      const s = t - q.te; if (s < 0) return null;
      const ex = q.e.x, ez = q.e.z, fy = q.e.j ? Math.max(y0, q.e.y - 0.5 - s * 2) : y0;   // out of the crack, down the wall
      const d = Math.hypot(q.tx - ex, q.tz - ez), tr = d / q.sp;
      if (s < tr) { const k = s / tr; return { x: lerp(ex, q.tx, k), y: fy, z: lerp(ez, q.tz, k), yaw: R.yawTo(ex, ez, q.tx, q.tz), pitch: 0 }; }
      if (!q.climb) { const a2 = (s - tr) * 1.5 + q.ph; return { x: q.tx + Math.sin(a2) * 0.2, y: y0, z: q.tz + Math.cos(a2) * 0.2, yaw: -a2, pitch: 0 }; }
      const up = Math.min(q.cy - y0, (s - tr) * 0.9);   // up the strands to you
      return { x: q.tx * 0.85 + me.x * 0.15, y: y0 + up, z: q.tz * 0.85 + me.z * 0.15, yaw: R.yawTo(q.tx, q.tz, me.x, me.z), pitch: Math.PI / 2 * Math.min(1, (s - tr) * 4) };
    };

    // The head: down the hole and caught; up at the light; round the pit; down at them coming.
    const hits = hitsOf([[4.65, 3, 1], [5.15, 3, -1], [5.65, 3, 1], [6.15, 3, -1], [6.65, 3, 1], [7.15, 2, -1], [7.6, 3, 1]]);
    const DUR = 7.6;
    const yHole = 0, ySpawn = R.yawTo(me.x, me.z, sp.x, sp.z), pSpawn = Math.atan2(sp.y - (trap.stopEye - 0.1), Math.hypot(sp.x - me.x, sp.z - me.z));
    const e0 = exits[0], yCrack = R.yawTo(me.x, me.z, e0.x, e0.z);
    const cam = (t) => {
      const s = settle(R, t, 0.9);
      const k = sstep(0.8, 1.3, t);
      let c = { x: s.x * (1 - k), y: s.y, z: s.z * (1 - k), yaw: lerp(s.yaw, 0, k), pitch: lerp(s.pitch, -0.02, k), roll: 0, fov: s.fov };
      c = trap.cam(t, c);
      if (t > trap.land) {
        // Stuck: the head moves slowly, as if the web holds it too.
        const L = trap.land;
        const keys = [[L, c.yaw, c.pitch], [L + 0.7, yHole + 0.2, 1.2], [L + 1.5, ySpawn, pSpawn], [L + 2.2, yCrack, -0.5], [L + 3.0, yCrack * 0.4, -1.15], [DUR, 0.2, -0.9]];
        let yy = keys[0][1], pp = keys[0][2];
        for (let q = 1; q < keys.length; q++) { if (t <= keys[q][0]) { const u = sstep(keys[q - 1][0], keys[q][0], t); yy = lerp(keys[q - 1][1], keys[q][1], u); pp = lerp(keys[q - 1][2], keys[q][2], u); break; } yy = keys[q][1]; pp = keys[q][2]; }
        c.yaw = yy; c.pitch = pp;
        c.roll = 0.05 * Math.sin(t * 1.3);
      }
      return shake(c, t, 0.0015 + 0.01 * pulse(t, [trap.land], 0.2) + 0.016 * pulse(t, hits.map((h) => h.t), 0.18), 3);
    };
    // Legs over the lens at the end, and their red eyes.
    const donor = R.mob("CaveSpider"); donor.pivot.visible = false;
    const LL = (fx, fy, tx, ty, t0, ph) => ({ from: [fx, fy], to: [tx, ty], t0, t1: t0 + 0.3, z: -0.26, scale: 0.5, axis: "x-", twist: 0.12, ph, curl: 0.25 * Math.sign(fx) });
    const legs = lensLimbs(R, donor, "spiderLeg1", [LL(-0.62, -0.3, -0.24, -0.16, 6.2, 0), LL(0.62, -0.28, 0.24, -0.14, 6.35, 1), LL(-0.6, 0.0, -0.22, 0.0, 6.6, 2), LL(0.6, 0.02, 0.22, 0.02, 6.8, 3), LL(-0.6, 0.26, -0.2, 0.14, 7.0, 4), LL(0.6, 0.26, 0.2, 0.14, 7.15, 5)], { color: 0x3c4450 });

    const sounds = [
      ...trap.sounds,
      [trap.land + 0.05, "qf.scare.whisper", { volume: 0.3 }],
      [trap.land + 0.4, "fire.fire", { at: [sp.x, sp.y, sp.z], volume: 0.5 }],
      [3.3, "mob.spider.say", { at: [e0.x, y0 + 0.5, e0.z], volume: 0.7, pitch: 1.3 }],
      [3.6, "dig.stone", { at: [e0.x, y0 + 0.5, e0.z], volume: 0.5, pitch: 1.4 }],
      ...exits.map((e, n) => [3.7 + n * 0.12, "mob.spider.step", { at: [e.x, e.y, e.z], volume: 0.7, pitch: 1.3 }]),
      ...[...Array(12)].map((_, n) => [4.0 + n * 0.25, n % 3 ? "mob.spider.step" : "mob.spider.say", { at: [me.x + Math.sin(n) * 1.5, y0 + 0.3, me.z + Math.cos(n) * 1.5], volume: 0.8, pitch: 1.25 + 0.05 * (n % 4) }]),
      [4.2, "qf.scare.stinger", { volume: 0.8 }],
      ...hits.flatMap((h, i) => [[h.t, "game.player.hurt"], [h.t + 0.02, i % 2 ? "qf.scare.gore" : "qf.scare.crunch", { volume: 0.6 }]]),
      [5.0, "qf.scare.scream", { volume: 0.9 }],
      [DUR, "game.player.die"], [DUR, "@muffle", { hz: 320, s: 3 }]
    ];
    const loops = [
      [0.5, DUR + 0.2, "qf.scare.heartbeat", { volume: 0.5 }],
      [trap.land + 0.3, DUR, "fire.fire", { at: [sp.x, sp.y, sp.z], volume: 0.35, fadeIn: 0.5 }],
      [3.4, DUR + 0.4, "qf.scare.chitter", { volume: 0.7, fadeIn: 0.8 }],
      [trap.land + 0.2, DUR, "qf.scare.breath", { volume: 0.4, fadeIn: 0.6 }]
    ];

    function update(t, f) {
      trap.update(t, f);
      const open = t >= trap.open;
      R.place(mini, sp.x, sp.y - 0.3, sp.z, t * 12);   // MobSpawnerBaseLogic spins it
      mini.anim(t, 0, { walk: 1 });
      mini.pivot.visible = open; cage.visible = open;
      fire(t);
      R.L(sp.x, sp.y + 0.3, sp.z, fireLight.position); fireLight.intensity = open ? 1.6 + 0.5 * Math.sin(t * 17) * Math.sin(t * 5.3) : 0;
      for (const e of exits) e.m.visible = open && t > 3.0;
      S.begin();
      for (const q of spiders) { const p = spiderAt(q, t); if (p) S.put(Math.floor((t / 0.674 * 8 + q.ph) % 8), p.x, p.y, p.z, p.yaw, p.pitch); }
      S.end();
      legs(t);
      const poison = t > hits[0].t;
      f.hpMode = poison ? "poison" : "normal";
      const gp = poison ? 0.5 + 0.5 * Math.sin((t - hits[0].t) * 5) : 0;
      f.tints = [[60, 140, 30, 0.12 * gp * sstep(hits[0].t, hits[0].t + 0.4, t)]];
      f.vig = [10, 40, 0, 0.3 + 0.25 * sstep(trap.land, trap.land + 1, t) + 0.25 * gp * (poison ? 1 : 0) + 0.3 * sstep(6.2, DUR, t)]; f.vigR = 0.9;
      f.env = { bake: 1 - 0.2 * sstep(0.2, 1.2, t), fogMul: 1 + 0.4 * sstep(1, 3, t), nausea: poison ? 0.25 + 0.15 * gp : 0 };
      f.black = 0.35 * sstep(DUR - 0.2, DUR + 0.6, t);
    }
    return { dur: DUR, hits, cam, update, sounds, loops, deathSide: 1, notes: { fits: trap.fits, D: Dp, room: trap.room, hole: trap.hole, exits: exits.length } };
  }
};
