// Cave Spider (piston trap): a click under your feet; the floor is yanked out and you drop into a pit strung with
// cobweb, and the web catches you short of the floor. Stuck. In the corner a spawner cage burns, its little spider
// spinning. Hissing from the walls; then they come out of the cracks, dozens, across the floor and up the strands.
// Then everything stops. Every one of them, frozen where it is, all their red eyes on you; the hissing gone, the fire
// low (the one device: the swarm gone still). Silence, longer or shorter each time. One click, close: the head turns to
// it. One of them on a strand just below you rises on its legs, hisses, and leaps off the web onto your face (round 7:
// a body in the air, not a face on the lens); and the rest move again, all at once, up over you. Each bite poisons:
// the hearts go green and the view pulses green until their legs close over it.
import { THREE, clamp, lerp, sstep, pulse, tex } from "./rig.js";
import { settle, shake, hitsOf, particles, mulberry, lensLimbs, bakePoses, swarm, webs } from "./common.js";
import { pistonTrap } from "./piston.js";
import { splitJaw, boxOf, silence, deathScream } from "./fnaf.js";
import { hop } from "./story.js";

export default {
  death: "Steve was slain by Cave Spider",
  async build(R) {
    const [webTex, partTex, cageTex, ...cracks] = await Promise.all([tex("web"), tex("particles"), tex("k:mob_spawner"), tex("destroy_stage_6"), tex("destroy_stage_8")]);
    const r = mulberry(R.seed * 11 + 3);
    const click = 0.95 + R.vary(0.3, 0.5);
    const trap = await pistonTrap(R, { click, open: click + R.vary(0.75, 0.35), D: 7, web: true });
    const { roomBox: rb, loc, a, b } = trap;
    const Dp = trap.D, y0 = -Dp;
    const W = [];
    for (const i of [a, a + 1]) for (const k of [b, b + 1]) for (const j of [-Dp, -Dp + 1]) { const p = loc(i, j, k); W.push([p.x, p.y, p.z]); }
    for (const [i, j, k] of [[rb.i0, -2, rb.k0], [rb.i1, -2, rb.k0], [rb.i0, -2, rb.k1], [rb.i1, -2, rb.k1], [rb.i0, -Dp, rb.k0], [rb.i1, -Dp + 1, rb.k0], [rb.i0, -3, rb.k1],
      [a - 1, -2, b], [a + 2, -3, b + 1], [rb.i0, -Dp, b + 1], [rb.i1, -Dp, b], [a, -2, rb.k1], [a + 1, -Dp, rb.k0]]) { const p = loc(i, j, k); W.push([p.x, p.y, p.z]); }
    webs(R, webTex, W);
    const sp = loc(rb.i1, -Dp, rb.k1);
    const cageMat = new THREE.MeshLambertMaterial({ map: cageTex, transparent: false, alphaTest: 0.1, side: THREE.DoubleSide });
    if (R.patchBake) R.patchBake(cageMat, { fixed: new THREE.Vector3(0.25, 0.2, 0.15) });
    const cage = R.add(new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), cageMat)); R.at(cage, sp.x, sp.y, sp.z); cage.rotation.y = R.yaw0;
    const mini = R.mob("CaveSpider", { amb: [0.3, 0.25, 0.2] });
    mini.pivot.scale.setScalar(0.45);

    // ---- the dice -------------------------------------------------------------------------------------------
    const tOut = trap.land + R.vary(1.35, 0.4);                 // the first ones out of the cracks
    const tF = tOut + R.vary(2.2, 0.25);                        // they all stop
    const tClick = tF + R.vary(1.0, 0.45), t0 = tClick + R.vary(0.55, 0.5);
    const lungeSide = R.pick([-1, 1]);
    // The frozen clock: the swarm's own time stands still from tF to t0, then runs on.
    const sw = (t) => (t < tF ? t : t < t0 ? tF : t - (t0 - tF));

    const flames = [];
    for (let i = 0; i < 60; i++) { const tt = trap.open + r() * 9; flames.push({ t0: tt, at: [sp.x + (r() - 0.5) * 0.8, sp.y - 0.3 + r() * 0.6, sp.z + (r() - 0.5) * 0.8], v: [0, 0.15, 0], life: 0.5 + r() * 0.3, size: 0.07, tile: 48, color: [1, 0.85, 0.6], grav: -0.2, fog: false, add: true }); }
    const fire = particles(R, partTex, flames.filter((p) => p.t0 < tF || p.t0 > t0));
    const fireLight = R.ownLight(R.light(0xff9a40, 0, 7, 1.3));

    const baked = bakePoses(R, "CaveSpider", { n: 8, period: 0.674, anim: { walk: 1 }, amb: [0.14, 0.14, 0.16] });
    const N = 34, S = swarm(R, baked, N + 2);
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
      const e = exits[n % exits.length], te = tOut + Math.pow(n / N, 0.9) * 2.0 + r() * 0.1;
      const ang = r() * Math.PI * 2, rad = 0.15 + r() * 0.5;
      spiders.push({ e, te, tx: me.x + Math.cos(ang) * rad, tz: me.z + Math.sin(ang) * rad, sp: 2.2 + r() * 1.2, ph: r() * 8, climb: n % 3 !== 2, cy: trap.stopEye - R.eye - 0.1 - r() * 0.3 });
    }
    const spiderAt = (q, t) => {
      const s = t - q.te; if (s < 0) return null;
      const ex = q.e.x, ez = q.e.z, fy = q.e.j ? Math.max(y0, q.e.y - 0.5 - s * 2) : y0;
      const d = Math.hypot(q.tx - ex, q.tz - ez), tr = d / q.sp;
      if (s < tr) { const k = s / tr; return { x: lerp(ex, q.tx, k), y: fy, z: lerp(ez, q.tz, k), yaw: R.yawTo(ex, ez, q.tx, q.tz), pitch: 0 }; }
      if (!q.climb) { const a2 = (s - tr) * 1.5 + q.ph; return { x: q.tx + Math.sin(a2) * 0.2, y: y0, z: q.tz + Math.cos(a2) * 0.2, yaw: -a2, pitch: 0 }; }
      const up = Math.min(q.cy - y0, (s - tr) * 0.9);
      return { x: q.tx * 0.85 + me.x * 0.15, y: y0 + up, z: q.tz * 0.85 + me.z * 0.15, yaw: R.yawTo(q.tx, q.tz, me.x, me.z), pitch: Math.PI / 2 * Math.min(1, (s - tr) * 4) };
    };

    // The one that comes for your face: on a strand just below and to one side of you, then off the web at the lens.
    const eye = trap.stopEye - 0.4;
    const cs = R.mob("CaveSpider", { amb: [0.05, 0.05, 0.06], own: true });
    const jaw = splitJaw(cs, [{ part: cs.parts.head, box: boxOf("spider", "spiderHead"), rows: 2 }], { nTeeth: 0, max: 0.75, mouth: 0x050000, tongue: 0x1a0202 });
    cs.anim(0, 0, { walk: 0 }); R.place(cs, 0, 0, 3, Math.PI);
    // The one that comes: on the pit wall across from you at about head height (spiders cling to walls), where the
    // spawner's fire catches it. The head turns to its click; it pushes off the wall toward you; the leap; on your face.
    const camY = trap.stopEye - 0.5;
    // (the room is carved when the floor opens, so its walls come from the trap's room box, not from the blocks now)
    const cands = [[rb.i0, b], [rb.i1, b + 1], [a, rb.k0], [a + 1, rb.k1]].map(([i, k]) => { const c = loc(i, -Dp, k); const d = Math.hypot(c.x - me.x, c.z - me.z) || 1; return { c, d, ux: (c.x - me.x) / d, uz: (c.z - me.z) / d }; });
    const pref = cands.filter((q) => q.d >= 1.25).sort((p, q) => (q.ux * lungeSide) - (p.ux * lungeSide))[0] || cands.slice().sort((p, q) => q.d - p.d)[0];
    const pd = Math.min(pref.d + 0.3, 2.2);
    const perch = { x: me.x + pref.ux * pd, y: camY - 0.3, z: me.z + pref.uz * pd };
    const tRear = tClick + 0.22, tK = t0 + 0.22, DUR = tK + R.vary(2.9, 0.1);
    const faceAt = { x: lerp(me.x, perch.x, 0.42), y: camY - 0.12, z: lerp(me.z, perch.z, 0.42) };
    const hits = hitsOf([[tK + 0.05, 3, 1], [tK + 0.45, 3, -1], [tK + 0.9, 3, 1], [tK + 1.35, 3, -1], [tK + 1.8, 3, 1], [tK + 2.3, 2, -1], [DUR, 3, 1]]);

    // The head: down the hole and caught; up at the light; round the pit; down at them coming; held still in the
    // freeze, turning slowly from one frozen spider to the next; snapped to the one that comes.
    const ySpawn = R.yawTo(me.x, me.z, sp.x, sp.z), pSpawn = Math.atan2(sp.y - (trap.stopEye - 0.1), Math.hypot(sp.x - me.x, sp.z - me.z));
    const e0 = exits[0], yCrack = R.yawTo(me.x, me.z, e0.x, e0.z);
    const yPerch = R.yawTo(me.x, me.z, perch.x, perch.z), pPerch = R.pitchTo(me.x, camY, me.z, perch.x, perch.y + 0.15, perch.z);
    const cam = (t) => {
      const s = settle(R, t, 0.9);
      const k = sstep(0.8, 1.3, t);
      let c = { x: s.x * (1 - k), y: s.y, z: s.z * (1 - k), yaw: lerp(s.yaw, 0, k), pitch: lerp(s.pitch, -0.02, k), roll: 0, fov: s.fov, near: t >= t0 - 0.1 ? 0.02 : undefined };
      c = trap.cam(t, c);
      if (t > trap.land) {
        const Lt = trap.land;
        const keys = [[Lt, c.yaw, c.pitch], [Lt + 0.7, 0.2, 1.2], [Lt + 1.4, ySpawn, pSpawn], [tOut + 0.2, yCrack, -0.5], [tOut + 1.2, yCrack * 0.4, -1.1], [tF, 0.2, -0.95],
          [tF + (tClick - tF) * 0.5, -0.5 * lungeSide, -0.85], [tClick, -0.45 * lungeSide, -0.85], [tRear, yPerch, pPerch, 1], [t0, yPerch, pPerch], [tK, yPerch * 0.9, pPerch * 0.45, 1], [tK + 0.7, 0.15, -0.6], [DUR, 0.2, -0.9]];
        let yy = keys[0][1], pp = keys[0][2];
        for (let q = 1; q < keys.length; q++) { if (t <= keys[q][0]) { const u = keys[q][3] ? 1 - Math.pow(1 - clamp((t - keys[q - 1][0]) / (keys[q][0] - keys[q - 1][0])), 4) : sstep(keys[q - 1][0], keys[q][0], t); yy = lerp(keys[q - 1][1], keys[q][1], u); pp = lerp(keys[q - 1][2], keys[q][2], u); break; } yy = keys[q][1]; pp = keys[q][2]; }
        c.yaw = yy; c.pitch = pp;
        c.roll = 0.05 * Math.sin(t * 1.3);
        c.fov += 6 * pulse(t, [tK], 0.12);
      }
      return shake(c, t, 0.0015 + 0.01 * pulse(t, [trap.land], 0.2) + 0.02 * pulse(t, [tK], 0.15) + 0.016 * pulse(t, hits.map((h) => h.t), 0.18), 3);
    };
    const donor = R.mob("CaveSpider"); donor.pivot.visible = false;
    const LL = (fx, fy, tx, ty, t1, ph) => ({ from: [fx, fy], to: [tx, ty], t0: t1, t1: t1 + 0.3, z: -0.26, scale: 0.5, axis: "x-", twist: 0.12, ph, curl: 0.25 * Math.sign(fx) });
    const LQ = (fx, fy, tx, ty, t1, ph) => ({ from: [fx, fy], to: [tx, ty], t0: t1, t1: t1 + 0.1, z: -0.25, scale: 0.46, axis: "x-", twist: 0.14, ph, curl: 0.3 * Math.sign(fx) });   // the leaper's, as it lands
    const legs = lensLimbs(R, donor, "spiderLeg1", [LQ(-0.62, -0.12, -0.27, -0.08, tK - 0.04, 6), LQ(0.62, -0.1, 0.27, -0.06, tK - 0.02, 7), LQ(-0.6, 0.18, -0.25, 0.1, tK, 8), LL(-0.62, -0.3, -0.24, -0.16, tK + 0.7, 0), LL(0.62, -0.28, 0.24, -0.14, tK + 0.85, 1), LL(-0.6, 0.0, -0.22, 0.0, tK + 1.1, 2), LL(0.6, 0.02, 0.22, 0.02, tK + 1.3, 3), LL(-0.6, 0.26, -0.2, 0.14, tK + 1.5, 4), LL(0.6, 0.26, 0.2, 0.14, tK + 1.65, 5)], { color: 0x3c4450 });

    const sounds = [
      ...trap.sounds,
      [trap.land + 0.05, "qf.scare.whisper", { volume: 0.3 }],
      [trap.land + 0.4, "fire.fire", { at: [sp.x, sp.y, sp.z], volume: 0.5 }],
      [tOut - 0.4, "mob.spider.say", { at: [e0.x, y0 + 0.5, e0.z], volume: 0.7, pitch: 1.3 }],
      [tOut - 0.1, "dig.stone", { at: [e0.x, y0 + 0.5, e0.z], volume: 0.5, pitch: 1.4 }],
      ...exits.map((e, n) => [tOut + n * 0.12, "mob.spider.step", { at: [e.x, e.y, e.z], volume: 0.7, pitch: 1.3 }]),
      ...[...Array(9)].map((_, n) => [tOut + 0.3 + n * 0.22, n % 3 ? "mob.spider.step" : "mob.spider.say", { at: [me.x + Math.sin(n) * 1.5, y0 + 0.3, me.z + Math.cos(n) * 1.5], volume: 0.8, pitch: 1.25 + 0.05 * (n % 4) }]).filter((s) => s[0] < tF - 0.05),
      silence(tF, { fade: 0.04 }),
      [tClick, "mob.spider.step", { at: [perch.x, perch.y, perch.z], volume: 0.35, pitch: 1.5 }],
      [tRear, "mob.spider.say", { at: [perch.x, perch.y, perch.z], volume: 0.75, pitch: 1.45 }],
      [t0, "mob.spider.say", { at: [perch.x, perch.y + 0.3, perch.z], volume: 1.35, pitch: 1.3 }], [t0 + 0.005, "qf.scare.hit", { volume: 0.5 }],
      ...hits.flatMap((h, i) => [[h.t, "game.player.hurt"], ...(i ? [] : [[h.t + 0.01, "qf.scare.hit", { volume: 0.9 }]]), [h.t + 0.02, i % 2 ? "qf.scare.gore" : "qf.scare.crunch", { volume: 0.7 }]]),
      ...[...Array(8)].map((_, n) => [tK + 0.1 + n * 0.2, n % 3 ? "mob.spider.step" : "mob.spider.say", { at: [me.x + Math.sin(n * 2) * 1.2, eye - 0.5, me.z + Math.cos(n * 2) * 1.2], volume: 0.9, pitch: 1.3 + 0.05 * (n % 4) }]),
      ...deathScream(tK + 0.3, { volume: 1.1, under: false }),
      ...deathScream(DUR - 0.9, { volume: 1.25 }),
      [DUR, "game.player.die"], [DUR, "@muffle", { hz: 320, s: 3 }]
    ];
    const loops = [
      [0.5, tF, "qf.scare.heartbeat", { volume: 0.5 }],
      [trap.land + 0.3, tF, "fire.fire", { at: [sp.x, sp.y, sp.z], volume: 0.35, fadeIn: 0.5 }],
      [tOut - 0.3, tF, "qf.scare.chitter", { volume: 0.7, fadeIn: 0.8 }],
      [trap.land + 0.2, tF, "qf.scare.breath", { volume: 0.4, fadeIn: 0.6 }],
      [tK, DUR + 0.4, "qf.scare.chitter", { volume: 1.0, fadeIn: 0.05 }],
      [tK, DUR + 0.2, "qf.scare.heartbeat", { volume: 0.7, pitch: 1.35 }]
    ];
    const _v = new THREE.Vector3();
    function update(t, f) {
      trap.update(t, f);
      const open = t >= trap.open, st = sw(t);
      R.place(mini, sp.x, sp.y - 0.3, sp.z, st * 12);
      mini.anim(st, 0, { walk: 1 });
      mini.pivot.visible = open; cage.visible = open;
      fire(t);
      const frozen = t >= tF && t < t0;
      R.L(sp.x, sp.y + 0.3, sp.z, fireLight.position); fireLight.intensity = open ? (frozen ? 0.5 : 1.6 + 0.5 * Math.sin(t * 17) * Math.sin(t * 5.3)) : 0;
      for (const e of exits) e.m.visible = open && t > tOut - 0.7;
      S.begin();
      for (const q of spiders) { const p = spiderAt(q, st); if (p) S.put(Math.floor((st / 0.674 * 8 + q.ph) % 8), p.x, p.y, p.z, p.yaw, p.pitch); }
      S.end();
      // The one that comes.
      let jo = 0;
      cs.pivot.visible = t > tOut;
      if (t < tK) {
        // On its strand, climbing; at the click it rises on its legs toward you; then the leap.
        const rear = sstep(tRear - 0.1, t0, t), u = clamp((t - t0) / (tK - t0)), q = t < t0 ? perch : hop(perch, faceAt, u * u * (1.6 - 0.6 * u), 0.2);
        R.place(cs, q.x, q.y, q.z, R.yawTo(q.x, q.z, me.x, me.z), lerp(lerp(-1.25, -0.5, rear), -0.15, u), 0);
        cs.anim(t < t0 ? st : t * 3, 0, { walk: t < tF ? 1 : t >= t0 ? 2 : 0.2 * rear });
        jo = 0.35 * rear + 0.5 * u;
        cs.setOwn(0.1 + 0.14 * rear);
      } else cs.pivot.visible = false;
      jaw.set(jo);
      legs(t);
      const poison = t > hits[0].t;
      f.hpMode = poison ? "poison" : "normal";
      const gp = poison ? 0.5 + 0.5 * Math.sin((t - hits[0].t) * 5) : 0;
      const sil = frozen ? sstep(tF, tF + 0.4, t) : 0;
      f.tints = [[60, 140, 30, 0.12 * gp * sstep(hits[0].t, hits[0].t + 0.4, t)]];
      f.vig = [10, 40, 0, 0.3 + 0.25 * sstep(trap.land, trap.land + 1, t) + 0.15 * sil + 0.25 * gp * (poison ? 1 : 0) + 0.3 * sstep(tK + 1.6, DUR, t)]; f.vigR = 0.9;
      f.env = { bake: 1 - 0.2 * sstep(0.2, 1.2, t) - 0.25 * sil, fogMul: 1 + 0.4 * sstep(1, 3, t), nausea: poison ? 0.25 + 0.15 * gp : 0 };
      f.black = 0.35 * sstep(DUR - 0.2, DUR + 0.6, t);
    }
    return { dur: DUR, hits, cam, update, sounds, loops, deathSide: 1,
      marks: { dread: tOut + 1.3, fake: (tF + tClick) / 2, lunge: t0 + 0.12, kill: tK + 1.6 },
      notes: { fits: trap.fits, D: Dp, open: +trap.open.toFixed(2), exits: exits.length, tF: +tF.toFixed(2), t0: +t0.toFixed(2), dur: +DUR.toFixed(2) } };
  }
};
