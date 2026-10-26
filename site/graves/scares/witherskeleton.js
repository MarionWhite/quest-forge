// Wither Skeleton (deep, v3): the fog goes black and the torches sink; far down the corridor, high up, two eyes. A
// stone sword drags along the wall, and each scrape throws sparks that show it, taller, closer. Then the scrape stops
// in the middle of a stroke. Silence. The eyes are gone. One small tick of metal, off to the side (or behind you);
// the view drifts to it: nothing there. Turning back, its skull is inches from your face, bent down to your eyes,
// head cocked, jaw chattering. It holds there; then it lunges with the screech. After the static: you are looking down
// at the blade in your chest, its hilt in a black hand, as the Wither black creeps in from the edges. It pulls the
// blade out; the next swing takes the head. The view flies, hits the floor and rolls; from the floor you see your own
// body go over. It walks to you, bends down, and picks the head up to its face, and its jaw opens wide.
import { THREE, clamp, lerp, sstep, pulse, tex, easeOut, track } from "./rig.js";
import { settle, shake, hitsOf, particles, mulberry, glowEyes, bipedSwing, swingAt, mcRot } from "./common.js";
import { lunge, lungeFx, screech, splitJaw, faceAnchor, boxOf, silence, deathScream, jit } from "./fnaf.js";

const TAU = Math.PI * 2;

export default {
  death: "Steve was slain by Wither Skeleton",
  async build(R) {
    const [partTex, swordTex] = await Promise.all([tex("particles"), tex("mc:items/stone_sword")]);
    const r = mulberry(R.seed * 5 + 77);
    // It comes along the wall on its sword side (its right, your left, as it faces you).
    const side = R.wallL < 3 || R.wallL <= R.wallR ? -1 : 1;
    const wall = side < 0 ? R.wallL : R.wallR;
    const sx = side * clamp(wall - 0.6, 0.35, 1.1);
    const onWall = wall - Math.abs(sx) < 1.0;
    const z0 = clamp(R.ahead - 1.2, 5, 9.5);

    // ---- the dice ---------------------------------------------------------------------------------------------
    const tEyes = R.vary(1.8, 0.2), tW0 = tEyes + 0.3;
    const nScr = 2 + Math.floor(R.rand() * 3);
    const scrapes = [];
    for (let i = 0, ts = tW0 + R.vary(0.45, 0.3); i < nScr; i++) { scrapes.push(ts); ts += R.vary(0.62, 0.3); }
    const tStop = scrapes[nScr - 1] + R.vary(0.17, 0.3);   // cut off in the middle of a stroke
    const zStop = clamp(R.vary(3.3, 0.2), 2.4, z0 - 0.8);
    const wz = (t) => lerp(z0, zStop, sstep(tW0, tStop, t));
    const tEyesOut = tStop + R.vary(0.45, 0.4);
    const behind = R.chance(0.45);   // the tick comes from behind you (a look over the shoulder) or from the empty side
    const tDrift = tStop + R.vary(1.05, 0.3), dDrift = behind ? 0.5 : 1.5;
    const tBack = tDrift + dDrift + R.vary(1.1, 0.4), tFace = tBack + 0.22;
    const t0 = tFace + R.vary(0.5, 0.45);

    const W = R.mob("WitherSkeleton", { amb: [0.025, 0.025, 0.03], own: true, equipment: [{ id: "minecraft:stone_sword", ench: false }] });
    W.anim(0, 0, {}); R.place(W, 0, 0, 4, Math.PI);
    const heldG = (W.parts.rightArm || {}).children ? W.parts.rightArm.children.find((o) => o.isGroup && o.matrixAutoUpdate === false) : null;
    const jaw = splitJaw(W, [{ part: W.parts.head, box: boxOf("skeleton", "bipedHead"), rows: 2 }], { nTeeth: 0, max: 0.75, mouth: 0x030303, tongue: 0x100202 });
    // Its eye sockets (the 1.7.10 texture's black holes), lit cold: all you see of it in the black.
    const eyes = glowEyes(R, W, [[-2, -3.5, -4.06, 2, 1], [2, -3.5, -4.06, 2, 1]], [0.62, 0.66, 0.78], { halo: 0.2, glow: 0.12 });
    const anchor = faceAnchor(W, W.parts.head, boxOf("skeleton", "bipedHead"));
    const L = lunge(R, W, { t0, rush: R.vary(0.17, 0.2), hold: R.vary(0.62, 0.15), dist: 0.42, anchor, seed: 23 });
    const tK = L.t3, tPull = tK + R.vary(1.65, 0.12), tDecap = tPull + 0.55, tLand = tDecap + 0.45, tRest = tDecap + 1.1;
    const tPick = tRest + R.vary(1.0, 0.2), tLift = tPick + 0.75, tFat = tLift + 0.8, DUR = tFat + 1.6;
    const hits = hitsOf([[tK, 8, -side], [tPull, 3, side], [tDecap, 12, side]]);

    // ---- the camera while you have a head ------------------------------------------------------------------------
    const away = side * (behind ? 2.5 : 0.95);   // to the empty side (positive yaw looks to -x), or on round over the shoulder
    const fwd = (yaw) => ({ x: -Math.sin(yaw), z: Math.cos(yaw) });
    const yawK = track([[0, 0], [tDrift, 0], [tDrift + dDrift, away, behind ? "s" : "l"], [tBack, away * 1.05, "l"], [tBack + 0.3, 0, "x"]]);
    const camAlive = (t) => {
      const s = settle(R, t, 0.9);
      const k = sstep(0.8, 1.3, t);
      const c = { x: s.x * (1 - k), y: s.y, z: s.z * (1 - k), yaw: lerp(s.yaw, 0, k), pitch: lerp(s.pitch, 0.03, k), roll: 0, fov: s.fov, near: t >= tBack ? 0.02 : undefined };
      for (const ts of scrapes) { const g = sstep(ts, ts + 0.2, t) * (1 - sstep(ts + 0.45, ts + 0.8, t)); c.yaw += g * R.yawTo(0, 0, sx, wz(ts)) * 0.6; }
      c.yaw += yawK(t);
      c.pitch += -0.07 * sstep(tStop, tStop + 1, t) * (1 - sstep(tBack, tBack + 0.3, t));
      if (t >= L.t2) {   // after the static: looking down the blade to where it goes into your chest
        const d = sstep(tK - 0.02, tK + 0.16, t), p = sstep(tPull, tPull + 0.15, t);
        c.pitch = lerp(lerp(c.pitch, -0.7, d) + 0.025 * Math.sin(t * 23) * d, -0.15, 0.9 * p);
        c.yaw -= 0.2 * d * (1 - p);   // its sword arm is on your right: the blade runs up the middle of the view
        c.y -= 0.12 * sstep(tK + 0.3, tPull, t);   // (the body sinks with it)
        c.roll += 0.07 * Math.sin(t * 2.1) * d;
        c.fov -= 6 * d;
      }
      c.fov += 10 * pulse(t, [L.t1], 0.12);
      return shake(c, t, 0.0015 + 0.003 * sstep(tEyes, tStop, t) + L.shake(t) + 0.025 * pulse(t, [tK, tPull], 0.18), 6);
    };
    const Cf = camAlive(tFace), Bc = camAlive(tK - 0.03);
    const ff = fwd(Cf.yaw), face = { x: Cf.x + ff.x * 1.05, z: Cf.z + ff.z * 1.05 };   // where it stands, bent to your eyes
    const fb = fwd(Bc.yaw), stab = { x: Bc.x + fb.x * 1.25, z: Bc.z + fb.z * 1.25 };   // where it stands with the blade in you (arm + blade)
    const chest = { x: Bc.x + fb.x * 0.06, y: 1.18, z: Bc.z + fb.z * 0.06 };

    // ---- the head's flight (v2), then the lift ----------------------------------------------------------------
    const S0 = camAlive(tDecap), fs = -side;
    const clampX = (x) => clamp(x, -(R.wallL - 0.3), R.wallR - 0.3);
    const Ld = { x: clampX(S0.x + 0.85 * fs), z: S0.z - 1.0 };
    const E = { x: clampX(Ld.x + 0.4 * fs), z: Ld.z - 0.5 };
    const feet = { x: lerp(S0.x, E.x, 0.35) - fs * 0.15, z: lerp(S0.z, E.z, 0.35) + 0.25 };   // where it stands at the end
    const yawEnd = R.yawTo(E.x, E.z, feet.x, feet.z);
    const flight = (t) => {
      const ka = clamp((t - tDecap) / (tRest - tDecap)), ea = easeOut(ka);
      const kf = clamp((t - tDecap) / (tLand - tDecap)), kr = easeOut((t - tLand) / (tRest - tLand));
      const c = { fov: S0.fov + 6 };
      if (t < tLand) { c.x = lerp(S0.x, Ld.x, kf); c.z = lerp(S0.z, Ld.z, kf); c.y = lerp(S0.y, 0.22, kf * kf) + Math.sin(kf * Math.PI) * 0.4; }
      else { const bounce = Math.abs(Math.sin(kr * Math.PI * 2)) * 0.1 * (1 - kr); c.x = lerp(Ld.x, E.x, kr); c.z = lerp(Ld.z, E.z, kr); c.y = 0.22 + bounce; }
      // Tumbling: a spin and a half end over end in the air, then the roll along the floor onto its side.
      c.yaw = lerp(S0.yaw, yawEnd, ea) + Math.sin(ka * Math.PI) * 1.3 * fs;
      c.pitch = lerp(S0.pitch, 0.42, ea) + Math.sin(kf * Math.PI) * 1.6 * (t < tLand ? 1 : 0);
      c.roll = lerp(0, 1.32 * fs + TAU * fs, ea);
      return c;
    };
    // Picked up: the head held up in front of its face, off-kilter, shaken.
    const toE = { x: E.x - feet.x, z: E.z - feet.z }, nE = Math.hypot(toE.x, toE.z) || 1;
    const H = { x: feet.x + toE.x / nE * 1.0, y: 1.86, z: feet.z + toE.z / nE * 1.0 };
    const yawH = R.yawTo(H.x, H.z, feet.x, feet.z);
    const cam = (t) => {
      if (t < tDecap) return camAlive(t);
      if (t < tLift) return flight(t);
      const rest = flight(tRest), k = easeOut(clamp((t - tLift) / (tFat - tLift))), up = Math.sin(k * Math.PI) * 0.25;
      let dy = yawH - rest.yaw; dy = Math.atan2(Math.sin(dy), Math.cos(dy));
      const sh = sstep(tFat, tFat + 0.15, t) * (1 - 0.6 * sstep(DUR - 0.6, DUR, t));
      const c = { x: lerp(rest.x, H.x, k), y: lerp(rest.y, H.y, k) + up, z: lerp(rest.z, H.z, k), yaw: rest.yaw + dy * k, pitch: lerp(rest.pitch, 0.1, k), roll: lerp(1.32 * fs, 0.3 * fs, k), fov: rest.fov, near: 0.02 };
      c.yaw += jit(t, 71, 12) * 0.07 * sh; c.pitch += jit(t, 73, 12) * 0.06 * sh; c.roll += jit(t, 79, 10) * 0.12 * sh;
      return shake(c, t, 0.002 + 0.02 * pulse(t, [tFat], 0.2), 7);
    };

    // ---- your body, the blade, the gore ------------------------------------------------------------------------
    const body = R.mob("Steve", { amb: [0.2, 0.2, 0.2], own: true, equipment: [{ id: "minecraft:iron_sword", ench: false }] });
    const corpse = (t) => fs * Math.min(1, Math.sqrt(Math.max(0, (t - tDecap - 0.15) * 20) / 20 * 1.6)) * Math.PI / 2;
    const neckAt = (t) => { const ro = corpse(t), rx = Math.cos(S0.yaw), rz = Math.sin(S0.yaw); return [S0.x - rx * Math.sin(ro) * 1.45, Math.max(0.1, 1.45 * Math.cos(ro)), S0.z - rz * Math.sin(ro) * 1.45]; };
    // The stone sword through you: the item sprite gripped in its fist like a spike, the blade running on along the
    // arm (the arm aims at your chest), so hand, hilt and blade line up into you.
    const swordGeo = new THREE.PlaneGeometry(0.62, 0.62); swordGeo.rotateZ(-3 * Math.PI / 4); swordGeo.translate(0, -0.36, 0);
    // The blade is bloody from the middle to the tip (the part that has been through you).
    let bladeTex = swordTex;
    if (swordTex && swordTex.image) {
      const cv = document.createElement("canvas"); cv.width = cv.height = 16;
      const g = cv.getContext("2d"); g.drawImage(swordTex.image, 0, 0, 16, 16);
      const id = g.getImageData(0, 0, 16, 16), rr = mulberry(91);
      for (let y = 0; y < 16; y++) for (let x = 0; x < 16; x++) {
        const i = (y * 16 + x) * 4, u = (x + 15 - y) / 30;
        if (id.data[i + 3] < 10 || u < 0.42) continue;
        const k = Math.min(1, (u - 0.42) * 4) * (0.55 + 0.45 * rr());
        id.data[i] = lerp(id.data[i], 120, k); id.data[i + 1] = lerp(id.data[i + 1], 6, k); id.data[i + 2] = lerp(id.data[i + 2], 6, k);
      }
      g.putImageData(id, 0, 0);
      bladeTex = new THREE.CanvasTexture(cv); bladeTex.colorSpace = THREE.SRGBColorSpace; bladeTex.magFilter = bladeTex.minFilter = THREE.NearestFilter; bladeTex.generateMipmaps = false;
    }
    const sword = new THREE.Mesh(swordGeo, new THREE.MeshBasicMaterial({ map: bladeTex, alphaTest: 0.1, side: THREE.DoubleSide, color: 0xb4b4b4 }));
    sword.visible = false; sword.position.set(0, -0.6, 0);
    if (W.parts.rightArm) W.parts.rightArm.add(sword);
    R.burst(tK - 0.02, [chest.x + fb.x * 0.15, chest.y, chest.z + fb.z * 0.15], 22, "blood", { dir: [fb.x * 0.9, 0.5, fb.z * 0.9], speed: 2.0, spread: 0.7, size: 0.035, life: 1.3, stick: 4 });
    for (let tt = tK + 0.2; tt < tPull; tt += 0.22) R.burst(tt, [chest.x, chest.y - 0.05, chest.z], 4, "blood", { dir: [0, -0.5, 0], speed: 0.6, spread: 0.4, size: 0.04, life: 1.0, stick: 3 });
    R.burst(tPull + 0.03, [chest.x, chest.y, chest.z], 30, "blood", { dir: [fb.x * 1.2, 0.5, fb.z * 1.2], speed: 2.6, spread: 0.6, size: 0.05, life: 1.3, stick: 4 });
    R.burst(tDecap + 0.04, [S0.x - fs * 0.1, 1.38, S0.z + 0.1], 40, "blood", { dir: [-fs * 0.8, 1.6, 0.4], speed: 3.0, spread: 0.9, size: 0.045, life: 1.6, stick: 4 });
    R.burst(tDecap + 0.05, [S0.x - fs * 0.1, 1.38, S0.z + 0.1], 12, "flesh", { dir: [-fs * 0.6, 1.2, 0.3], speed: 2.2, spread: 0.9, size: 0.07, life: 1.5, stick: 4 });
    R.burst(tDecap + 0.06, [S0.x - fs * 0.1, 1.38, S0.z + 0.1], 8, "bone", { dir: [-fs, 1, 0], speed: 2.0, spread: 0.9, size: 0.05, life: 1.4, stick: 4 });
    for (let tt = tDecap + 0.08; tt < tDecap + 1.3; tt += 0.09) { const n = neckAt(tt); R.burst(tt, n, 9, "blood", { dir: [0, 2.2, 0], speed: 2.2 * (1 - (tt - tDecap) / 1.6), spread: 0.45, size: 0.05, life: 1.3, stick: 3 }); }

    // Sparks off the stone where the blade drags (EntityCritFX, tile 65), and the light they throw. The last stroke
    // is cut off where the scrape stops.
    const sparkSpecs = [];
    for (const ts of scrapes) for (let i = 0; i < 26; i++) {
      const tt = ts + r() * 0.32; if (tt > tStop) continue;
      const z = wz(tt) + 0.35;
      const at = onWall ? [side * (wall - 0.04), 0.55 + r() * 0.35, z] : [sx + side * 0.75, 0.05, z];
      sparkSpecs.push({ t0: tt, at, v: [-side * (0.6 + r()), 0.8 + r() * 1.2, (r() - 0.5) * 1.2], life: 0.35 + r() * 0.3, size: 0.05 + r() * 0.04, tile: 65, color: [1, 0.75 + r() * 0.2, 0.35], grav: 7, fog: false, add: true });
    }
    const sparks = particles(R, partTex, sparkSpecs);
    const flash = R.ownLight(R.light(0xffb860, 0, 5, 1.3));
    const cold = R.ownLight(R.light(0x8090b0, 0, 5, 1.4));

    // ---- sound --------------------------------------------------------------------------------------------
    const steps = [];
    for (let tt = tW0 + 0.15; tt < tStop; tt += 0.42) steps.push([tt, "mob.skeleton.step", { at: [sx, 0.1, wz(tt)], volume: 0.5, pitch: 0.8 }]);
    const scrapeSnd = scrapes.flatMap((ts) => [0, 0.07, 0.15, 0.22, 0.3].filter((d) => ts + d < tStop).map((d, i) => [ts + d, i % 2 ? "step.stone" : "dig.stone", { at: [onWall ? side * wall : sx, 0.7, wz(ts + d)], volume: 0.55, pitch: 1.6 + 0.12 * ((i * 3) % 4) }]));
    const tick = behind ? [-side * 0.3, 0.7, -1.6] : [-side * 1.6, 0.9, 1.4];
    const S2 = screech(L, [["mob.skeleton.death", { pitch: 0.5 }], ["mob.wither.hurt", { pitch: 0.6, volume: 1.2 }]]);
    const sounds = [
      [tEyes + 0.1, "mob.skeleton.say", { at: [sx, 2.1, z0], volume: 0.7, pitch: 0.65, reverb: 0.6 }],
      ...steps, ...scrapeSnd,
      silence(tStop, { fade: 0.04 }),
      [tDrift - 0.3, "dig.stone", { at: tick, volume: 0.3, pitch: 1.9 }],
      [tFace + 0.12, "random.click", { at: [face.x, R.eye, face.z], volume: 0.18, pitch: 0.55 }],
      ...S2.sounds,
      [tK - 0.1, "qf.scare.gore", { volume: 1.2 }], [tK - 0.08, "qf.scare.crunch", { volume: 1.0 }], [tK, "game.player.hurt"],
      ...deathScream(tK + 0.06),
      [tPull, "qf.scare.gore", { volume: 1 }], [tPull + 0.02, "game.player.hurt", { volume: 0.9 }],
      ...deathScream(tPull + 0.1, { volume: 1.1, under: false }),
      [tDecap - 0.15, "mob.skeleton.say", { at: [stab.x, 2.1, stab.z], volume: 0.9, pitch: 0.55 }],
      [tDecap, "qf.scare.crunch", { volume: 1 }], [tDecap + 0.01, "qf.scare.gore", { volume: 1 }], [tDecap + 0.02, "game.player.die"],
      [tDecap + 0.05, "@muffle", { hz: 420, s: DUR - tDecap + 2 }],
      [tLand, "game.player.hurt.fall.small", { volume: 0.9 }], [tLand + 0.22, "step.stone", { volume: 0.7, pitch: 0.7 }], [tLand + 0.42, "step.stone", { volume: 0.5, pitch: 0.65 }],
      [tDecap + 0.75, "game.player.hurt.fall.big", { at: [S0.x, 0.3, S0.z], volume: 0.8 }],
      [tRest + 0.1, "mob.skeleton.step", { at: [feet.x, 0.1, feet.z], volume: 0.9, pitch: 0.75 }], [tRest + 0.5, "mob.skeleton.step", { at: [feet.x, 0.1, feet.z], volume: 0.9, pitch: 0.7 }],
      [tPick + 0.2, "mob.skeleton.say", { at: [feet.x, 1.6, feet.z], volume: 0.9, pitch: 0.5 }],
      [tLift + 0.1, "qf.scare.gore", { volume: 0.6 }],
      [tFat, "mob.skeleton.death", { volume: 1.5, pitch: 0.45 }], [tFat + 0.01, "mob.wither.idle", { volume: 1.1, pitch: 0.7 }], [tFat + 0.02, "qf.scare.hit", { volume: 1 }],
      [tFat + 0.03, "qf.scare.jumpscreech", { volume: 0.9 }]
    ];
    const loops = [
      [0.5, tStop, "qf.scare.heartbeat", { volume: 0.55, fadeOut: 0.02 }],
      [0.4, tStop, "qf.scare.drone", { volume: 0.5, fadeIn: 1.8, fadeOut: 0.04, pitch: 0.7, bus: "sfx" }],
      [tDrift + 0.4, tBack, "qf.scare.heartbeat", { volume: 0.35, fadeIn: 0.8, fadeOut: 0.02 }],
      ...S2.loops,
      [tK + 0.35, tPull, "qf.scare.breath", { volume: 0.6, fadeIn: 0.2, fadeOut: 0.02 }],
      [tDecap + 0.05, DUR + 1, "qf.scare.ringing", { volume: 0.5, fadeIn: 0.05, fadeOut: 1.5 }]
    ];

    // ---- the frame ------------------------------------------------------------------------------------------
    function update(t, f) {
      const cl = R.toLocal(R.camera.position);
      let x = sx, y = 0, z = wz(t), yaw = R.yawTo(sx, z, cl.x, cl.z), pitch = 0, vis = t > tEyes - 0.1 && t < tEyesOut + 0.1;
      let open = 0, own = 0.025, eyeOn = sstep(tEyes, tEyes + 0.4, t) * (1 - sstep(tEyesOut, tEyesOut + 0.08, t)), walk = t > tW0 && t < tStop ? 0.8 : 0;
      let armX = null, armY = 0, armL = null, cock = 0, swingP = 0, heldOn = true;
      if (t >= tBack && t < tK) {
        // Inches away: bent down to your eyes, the head cocked, the jaw chattering.
        vis = true; x = face.x; z = face.z; y = R.eye - 2.06; yaw = R.yawTo(face.x, face.z, Cf.x, Cf.z);
        open = 0.1 + 0.16 * Math.max(0, jit(t, 5, 15)); cock = 0.32 * (1 - sstep(t0, L.t1, t)); eyeOn = 0.8 - 0.25 * sstep(t0, L.t1, t); own = 0.12 + 0.2 * sstep(t0, L.t1, t); walk = 0;
        if (t >= t0) open = Math.max(open, sstep(t0, L.t1, t) * (0.8 + 0.2 * jit(t, 9)));
      } else if (t >= tK && t < tDecap + 0.35) {
        // The blade in you; out; the swing.
        vis = true; x = stab.x; z = stab.z; yaw = R.yawTo(stab.x, stab.z, Bc.x, Bc.z); eyeOn = 0.7; own = 0.1; walk = 0;
        open = 0.15 * (1 - sstep(tK, tK + 0.6, t)) + 0.2 * Math.max(0, jit(t, 15, 6)) * (t > tPull ? 1 : 0);
        const out = sstep(tPull, tPull + 0.25, t);
        armX = t < tPull + 0.25 ? lerp(-Math.PI / 2 + 0.39 - 0.05 * sstep(tK, tPull, t), -0.2, out) : null; armY = -0.33 * (1 - out);
        heldOn = t >= tPull + 0.22; swingP = swingAt(t, [tDecap - 0.15], 0.3);
      } else if (t >= tDecap + 0.35) {
        // To the head on the floor; bends; lifts it to its face in its left hand (the sword stays in the right).
        vis = true; const kw = sstep(tDecap + 0.35, tPick, t);
        x = lerp(stab.x, feet.x, kw); z = lerp(stab.z, feet.z, kw);
        const look = t < tLift ? E : H;
        yaw = R.yawTo(x, z, look.x, look.z); walk = kw > 0.02 && kw < 0.98 ? 0.8 : 0; eyeOn = 0.55 + 0.35 * sstep(tFat, tFat + 0.1, t); own = 0.1 + 0.18 * sstep(tPick, tLift, t);
        const bend = sstep(tPick, tPick + 0.5, t) * (1 - sstep(tLift, tLift + 0.6, t));
        pitch = -0.6 * bend;
        armL = t >= tPick ? lerp(-0.9 * sstep(tPick, tPick + 0.5, t), -Math.PI / 2 - 0.25, sstep(tLift, tLift + 0.6, t)) : null;
        open = sstep(tFat, tFat + 0.12, t) * (0.85 + 0.15 * jit(t, 19)) + 0.12 * Math.max(0, jit(t, 21, 8)) * sstep(tLift, tFat, t);
      }
      W.pivot.visible = vis;
      R.place(W, x, y, z, yaw, pitch);
      W.anim(t, 0, { walk });
      bipedSwing(W, swingP);
      if (armX != null && W.parts.rightArm) mcRot(W.parts.rightArm, armX, armY, 0);
      if (armL != null && W.parts.leftArm) mcRot(W.parts.leftArm, armL, 0, 0);
      if (cock && W.parts.head) W.parts.head.rotation.z += cock;
      if (heldG) heldG.visible = heldOn;
      jaw.set(open);
      if (t >= t0 && t < tK) L.apply(t);
      W.setOwn(own);
      eyes(vis ? eyeOn : 0);
      // The blade: in its fist, through your chest; drawn back out with the arm after the pull.
      sword.visible = t >= tK - 0.12 && t < tPull + 0.22;
      // The body: headless once the head is off, going over (while the head is on, the view does not show it).
      const bodyOn = t >= tDecap;
      body.pivot.visible = bodyOn;
      if (bodyOn) {
        R.place(body, S0.x, 0, S0.z, S0.yaw, 0, corpse(t));
        body.anim(t, 0, { walk: 0, still: true });
        if (body.parts.head) { body.parts.head.visible = false; if (body.parts.headwear) body.parts.headwear.visible = false; }
      }
      sparks(t);
      // Light: each scrape's sparks show it; a cold glimmer on its skull up close and at the end.
      const sp = Math.max(0, ...scrapes.map((ts) => (t >= ts && t < Math.min(ts + 0.42, tStop) ? (0.6 + 0.4 * Math.sin((t - ts) * 60)) * (1 - (t - ts) / 0.42) : 0)));
      R.L(onWall ? side * (wall - 0.3) : sx + side * 0.6, 0.8, wz(t) + 0.2, flash.position); flash.intensity = 5 * sp;
      if (t < tBack) { R.L(lerp(sx, 0, 0.5), 2.5, wz(t) - 0.9, cold.position); cold.intensity = 0; }
      else if (t < tDecap) { R.L(lerp(cl.x, face.x, 0.4), R.eye + 0.5, lerp(cl.z, face.z, 0.4), cold.position); cold.intensity = t < tK ? 1.3 : 1.0; }
      else { R.L(lerp(H.x, feet.x, 0.3), 2.6, lerp(H.z, feet.z, 0.3), cold.position); cold.intensity = 1.2 * sstep(tLand, tRest, t) + 0.6 * sstep(tLift, tFat, t); }
      // The black: fog and the torches sink; the Wither takes the edges of the view, creeping in while you look down.
      const blk = sstep(0.4, 2.0, t) * (1 - 0.45 * sstep(tDecap + 0.3, tRest, t)), wither = sstep(tK, tPull + 0.3, t);
      f.env = { bake: 1 - 0.65 * blk, lights: 1 - 0.7 * blk, fogMul: 1 + 2.0 * blk, fog: [0, 0, 0, blk] };
      f.hpMode = t > tK ? "wither" : "normal";
      f.vig = [0, 0, 0, 0.3 * blk + 0.6 * wither * (0.9 + 0.1 * Math.sin(t * 5))]; f.vigR = 0.95 - 0.3 * wither * (1 - 0.6 * sstep(tDecap, tRest, t)); f.vigIn = 0.25 - 0.1 * wither;
      f.tints = [[150, 0, 0, 0.35 * pulse(t, [tK, tDecap], 0.35)], [0, 0, 0, 0.12 * wither * (1 - sstep(tDecap, tRest, t))]];
      f.splats = [tK, tDecap].filter((h) => t >= h).map((h, i) => ({ t0: h, x: [0.35, 0.6][i], y: [0.45, 0.4][i], r: [14, 22][i], seed: 41 + i }));
      f.black = 0.4 * sstep(DUR - 0.3, DUR + 0.6, t);
      lungeFx(L, t, f);
    }
    return { dur: DUR, hits, cam, update, sounds, loops, deathSide: fs,
      marks: { dread: scrapes[Math.min(1, nScr - 1)] + 0.12, fake: tDrift + dDrift + 0.3, lunge: L.t1 + 0.1, kill: tK + 0.9 },
      notes: { held: !!heldG, side, onWall, nScr, behind, t0: +t0.toFixed(2), tFat: +tFat.toFixed(2), dur: +DUR.toFixed(2) } };
  }
};
