// Cutscenes 8-14: Slime, Silverfish, Blaze, Ghast, Magma Cube, Zombie Pigman, Wither Skeleton.
import { THREE, clamp, lerp, sstep, easeOut, rngOf, getMob, pt, tint, glow, box, faceTo } from "./stage.js";
import { bob, limbs, pulse, addSword, makeSwarm } from "./cuts1.js";

const fireball = (S, size, col = 0xff8a10) => {
  const g = new THREE.Group();
  const a = box(size, size, size, col), b = box(size * 0.62, size * 0.62, size * 0.62, 0xffe070); b.rotation.set(0.6, 0.6, 0);
  const l = new THREE.PointLight(0xff8a20, 5, 7);
  g.add(a, b, l); S.scene.add(g); g.visible = false; return g;
};

// ------------------------------------------------------------------------------------------------ Slime
export async function slime(c) {
  const S = c.stage, sl = await getMob("Slime");
  sl.root.scale.setScalar(4.2); sl.root.visible = false; S.scene.add(sl.root);
  tint(sl, 0x7ee03a, 0x1a5a08, 0.5);
  const tl = 2.05;
  const cam = (t) => ({ x: 0, y: 1.62 + bob(t) * (1 - sstep(1.2, 1.5, t)) - 0.15 * sstep(tl, tl + 0.5, t), z: -0.5 * Math.min(t, 1.5), yaw: 0, pitch: 0.35 * sstep(1.0, 1.5, t) - 0.35 * sstep(tl - 0.1, tl + 0.3, t), roll: 0.1 * sstep(tl, tl + 0.6, t), fov: 72 });
  const hits = [2.5, 3.05, 3.6, 4.15];
  c.hitBurst([1.25, 1.45, 1.7], () => ({ x: 0, y: 3.1, z: -1.1 }), "green", 10, { dir: [0, -0.2, 0], speed: 0.8, spread: 0.6, grav: 4, size: 0.06 });
  c.hitBurst([tl], cam, "green", 80, { dir: [0, 0.3, 0.5], speed: 3.6, spread: 1.3, size: 0.09 });
  c.hitBurst(hits, cam, "green", 22, { dir: [0, 0.6, 0.3], speed: 2.4, spread: 1 });
  const G = new THREE.PointLight(0x70ff40, 2, 5); S.scene.add(G);
  return {
    id: "Slime", dur: 4.7, death: "You were slain by Slime", hits, cam,
    shake: (t) => 0.008 + 0.05 * pulse(t, [tl], 0.25),
    sounds: [[0.1, "qf.scare.riser"], [1.2, "mob.slime.small"], [1.5, "mob.slime.small"], [1.8, "mob.slime.big"], [tl - 0.02, "qf.scare.hit"], [tl, "mob.slime.big"], [2.5, "mob.slime.attack"], [3.05, "mob.slime.attack"], [3.6, "mob.slime.attack"], [4.15, "mob.slime.attack"], [2.6, "qf.krypt.heartbeat"], [4.7, "game.player.die"]],
    update(t, f) {
      sl.root.visible = t > 1.55;
      const cp = cam(t), fall = easeOut((t - 1.55) / (tl - 1.55));
      const wob = t > tl ? 1 + 0.06 * Math.sin(t * 9) : 1;
      sl.root.position.set(0, lerp(4.6, 0.2, Math.pow(clamp((t - 1.55) / (tl - 1.55)), 1.6)), cp.z - 0.1);
      sl.root.scale.set(4.2 * wob, 4.2 * (t < tl ? 1 + 0.1 * sstep(1.55, tl, t) : 1 / wob), 4.2 * wob);
      G.position.set(0, 1.6, cp.z); G.intensity = t > tl ? 3 : 0;
      const e = sstep(tl - 0.1, tl + 0.4, t);
      f.tints.push([60, 190, 30, 0.42 * e]);
      f.vig = [20, 110, 10, 0.6 * e];
      f.bubbles = e;
    }
  };
}

// ------------------------------------------------------------------------------------------------ Silverfish
export async function silverfish(c) {
  const S = c.stage;
  const tb = 1.55, hole = [1.4, 1.0, -3.2];
  const cam = (t) => ({ x: 0, y: 1.62 + bob(t) * (1 - sstep(0.5, 0.8, t)), z: -1.8 * Math.min(1, t / 0.9) * 0.5, yaw: -0.85 * sstep(0.9, 1.4, t) + 0.0, pitch: -0.2 * sstep(1.4, 2.0, t), roll: 0.1 * Math.sin(t * 3) * sstep(2.3, 3.4, t), fov: 72 });
  // infested blocks in the right wall
  const R = rngOf(31), blocks = [];
  for (let i = 0; i < 6; i++) {
    const b = box(0.6, 0.6, 0.6, 0x8c8c8c, false);
    b.position.set(1.22, 0.6 + Math.floor(i / 3) * 0.6 + 0.0, -2.6 - (i % 3) * 0.6 + 0.0);
    b.userData.o = b.position.clone(); b.userData.v = [(R() - 0.5) * 1.4 - 0.9, 1 + R() * 2.2, (R() - 0.5) * 2]; blocks.push(b); S.scene.add(b);
  }
  const sw = await makeSwarm(c, { id: "Silverfish", n: phoneN(c, 30), from: [1.3, 0, -3.2], t0: tb, spread: 0.06, arrive: tb + 1.0, scale: 2.2, camAt: cam, seed: 17, climb: 1.0 });
  c.hitBurst([tb], () => ({ x: 1.2, y: 1.0, z: -3.2 }), "stone", 80, { dir: [-1.2, 0.5, 0], speed: 3.5, spread: 1.2, size: 0.09 });
  c.hitBurst([tb], () => ({ x: 1.2, y: 1.0, z: -3.2 }), "dust", 40, { dir: [-0.6, 0.4, 0], speed: 1.8, spread: 1, size: 0.18, life: 2, grav: 0.8 });
  const hits = [2.85, 3.4, 3.95, 4.5];
  c.hitBurst(hits, cam, "blood", 22, { dir: [0, 0.6, 0.3], speed: 2.4, spread: 1 });
  return {
    id: "Silverfish", dur: 5.2, death: "You were slain by Silverfish", hits, cam,
    shake: (t) => 0.008 + 0.03 * sstep(0.9, tb, t) * (1 - sstep(tb, tb + 0.4, t)) + 0.012 * sstep(2.3, 4, t),
    sounds: [[0.1, "qf.scare.riser"], [0.9, "dig.stone"], [1.1, "dig.stone"], [1.3, "random.break"], [tb, "qf.scare.hit"], [tb, "dig.stone"], [1.7, "mob.silverfish.say"], [2.0, "mob.silverfish.say"], [2.4, "mob.silverfish.say"], [3.0, "mob.silverfish.hit"], [3.7, "mob.silverfish.say"], [4.4, "mob.silverfish.say"], [5.2, "game.player.die"]],
    update(t, f) {
      for (const b of blocks) {
        if (t < tb) { b.visible = true; b.position.copy(b.userData.o); const j = sstep(0.9, tb, t) * 0.025; b.position.x += Math.sin(t * 70 + b.userData.o.z * 9) * j; b.position.y += Math.cos(t * 83 + b.userData.o.y * 9) * j; }
        else b.visible = false;
      }
      sw.update(t);
      f.vig = [0, 0, 0, 0.45 * sstep(2.2, 4.0, t)];
    }
  };
}
function phoneN(c, n) { return c.phone ? Math.round(n * 0.6) : n; }

// ------------------------------------------------------------------------------------------------ Blaze
export async function blaze(c) {
  const S = c.stage, bl = await getMob("Blaze");
  S.scene.add(bl.root); bl.root.visible = false;
  const rods = Array.isArray(bl.parts.rods) ? bl.parts.rods : [];
  const cam = (t) => ({ x: 0, y: 1.62 + bob(t) * (1 - sstep(1.0, 1.3, t)), z: -0.45 * Math.min(t, 1.2) + 0.3 * sstep(2.7, 4.5, t), yaw: 0, pitch: 0.05 + 0.1 * sstep(2.5, 3.2, t), roll: 0, fov: 72 });
  const L = new THREE.PointLight(0xff9a30, 8, 12); S.scene.add(L);
  const shots = [
    { t0: 1.1, t1: 1.8, to: [1.45, 1.6, -3.5], m: fireball(S, 0.28) },
    { t0: 1.4, t1: 2.15, to: [-1.45, 1.0, -3.0], m: fireball(S, 0.28) },
    { t0: 1.9, t1: 2.7, to: null, m: fireball(S, 0.28) }
  ];
  const blazeAt = (t) => [Math.sin(t * 1.2) * 0.3, 1.6 + Math.sin(t * 2.4) * 0.12, lerp(-7, -3.6, sstep(2.7, 4.6, t))];
  for (const sh of shots) if (!sh.to) { const k = cam(sh.t1); sh.to = [k.x, k.y, k.z - 0.05]; }
  for (const sh of shots.slice(0, 2)) c.hitBurst([sh.t1], () => ({ x: sh.to[0], y: sh.to[1], z: sh.to[2] }), "fire", 40, { dir: [0, 0.3, 0.2], speed: 3, spread: 1.2, size: 0.09, life: 0.9 });
  const hits = [2.7, 3.3, 3.9, 4.5];
  c.hitBurst([2.7], cam, "fire", 80, { dir: [0, 0.3, 0.6], speed: 3.5, spread: 1.4, size: 0.1, life: 1.1 });
  c.hitBurst(hits.slice(1), cam, "fire", 30, { dir: [0, 0.5, 0.3], speed: 2.4, spread: 1, life: 1 });
  return {
    id: "Blaze", dur: 5.2, death: "You were fireballed by Blaze", hits, cam,
    shake: (t) => 0.008 + 0.03 * pulse(t, [1.8, 2.15], 0.1) + 0.035 * pulse(t, [2.7], 0.3),
    sounds: [[0.1, "qf.scare.riser"], [0.5, "mob.blaze.breathe", { pos: { x: 0, y: 1.6, z: -7 } }], [1.1, "mob.ghast.fireball"], [1.4, "mob.ghast.fireball"], [1.9, "mob.ghast.fireball"], [1.8, "fire.ignite"], [2.15, "fire.ignite"], [2.45, "qf.scare.hit"], [2.7, "fire.ignite"], [2.75, "fire.fire"], [3.4, "mob.blaze.breathe"], [3.8, "fire.fire"], [4.4, "mob.blaze.hit"], [5.2, "game.player.die"]],
    update(t, f) {
      bl.root.visible = t > 0.45;
      const p = blazeAt(t); bl.root.position.set(p[0], 0.2, p[2]); bl.anim(t, 0, {}); bl.root.rotation.y = Math.PI;
      if (bl.kind === "blaze") {
        bl.parts.head.position.y = p[1];
        rods.forEach((r, i) => { const a = t * (2.2 + 4 * sstep(1.0, 2.7, t)) + i * (6.283 / 4); const ring = i % 3, rr = 0.55 + ring * 0.05; r.position.set(Math.cos(a) * rr, 0.9 + ring * 0.38 + Math.sin(t * 3 + i) * 0.05, Math.sin(a) * rr); });
      }
      L.position.set(p[0], p[1], p[2] + 1); L.intensity = 6 + 3 * Math.sin(t * 20) + 5 * sstep(2.7, 3.6, t);
      for (const sh of shots) {
        const m = sh.m; m.visible = t >= sh.t0 && t < sh.t1;
        if (!m.visible) continue;
        const k = clamp((t - sh.t0) / (sh.t1 - sh.t0)), q = blazeAt(sh.t0);
        m.position.set(lerp(q[0], sh.to[0], k), lerp(q[1], sh.to[1], k), lerp(q[2] + 0.4, sh.to[2], k));
        m.rotation.set(t * 11, t * 7, 0); m.scale.setScalar(1 + 2.4 * k * k);
      }
      const fi = sstep(2.7, 3.7, t);
      f.fire = 0.9 * fi;
      f.tints.push([255, 90, 0, 0.18 * fi]);
      f.vig = [255, 60, 0, 0.5 * fi];
    }
  };
}

// ------------------------------------------------------------------------------------------------ Ghast
export async function ghast(c) {
  const S = c.stage, gh = await getMob("Ghast");
  gh.root.scale.setScalar(0.9); S.scene.add(gh.root); gh.root.visible = false;
  const cam = (t) => ({ x: 0, y: 1.62 + bob(t) * 0.6, z: -0.2 * Math.min(t, 2), yaw: 0.02 * Math.sin(t), pitch: 0.12 + 0.08 * sstep(0.5, 2, t) - 0.1 * sstep(3.3, 3.6, t), roll: 0, fov: 72 - 10 * sstep(1.0, 2.8, t) });
  const tl = 2.35, th = 3.55;
  const fb = fireball(S, 1.0, 0xff7a10);
  const L = new THREE.PointLight(0xc8d8ff, 5, 12); S.scene.add(L);
  const ghAt = (t) => [0, 3.0, lerp(-18, -9, sstep(0.4, 2.3, t))];
  c.hitBurst([th], cam, "fire", 120, { dir: [0, 0.3, 0.9], speed: 4.5, spread: 1.5, size: 0.14, life: 1.3 });
  const hits = [th, 4.1, 4.65];
  c.hitBurst(hits.slice(1), cam, "fire", 30, { dir: [0, 0.5, 0.3], speed: 2.4, spread: 1, life: 1 });
  return {
    id: "Ghast", dur: 5.4, death: "You were fireballed by Ghast", hits, cam,
    shake: (t) => 0.006 + 0.01 * sstep(tl, th, t) + 0.1 * pulse(t, [th], 0.5),
    sounds: [[0.1, "qf.scare.riser"], [0.45, "mob.ghast.moan", { pos: { x: 0, y: 3, z: -16 } }], [1.1, "mob.ghast.scream"], [1.9, "mob.ghast.charge"], [tl, "mob.ghast.fireball"], [3.3, "qf.scare.hit"], [th, "random.explode"], [3.7, "fire.fire"], [4.1, "mob.ghast.scream"], [5.4, "game.player.die"]],
    update(t, f) {
      gh.root.visible = t > 0.4;
      const p = ghAt(t); gh.root.position.set(p[0] + Math.sin(t * 1.1) * 0.3, p[1] - 2.5, p[2]); gh.root.rotation.y = Math.PI;
      gh.anim(t, 0, {});
      L.position.set(0, 3.5, p[2] + 2.5);
      fb.visible = t >= tl && t < th;
      if (fb.visible) {
        const k = Math.pow(clamp((t - tl) / (th - tl)), 1.7), cp = cam(th);
        fb.position.set(lerp(p[0], cp.x, k), lerp(p[1] - 0.6, cp.y - 0.05, k), lerp(p[2] + 1.5, cp.z - 0.2, k));
        fb.rotation.set(t * 9, t * 6, 0); fb.scale.setScalar(1 + 0.4 * k);
      }
      const e = t >= th ? 1 : 0;
      f.white = e ? clamp(1 - (t - th) / 0.9) : 0;
      const fi = sstep(th, th + 1.0, t);
      f.fire = 0.85 * fi;
      f.tints.push([255, 100, 10, 0.2 * fi]);
      f.vig = [255, 70, 0, 0.5 * fi];
    }
  };
}

// ------------------------------------------------------------------------------------------------ Magma Cube
export async function magmaCube(c) {
  const S = c.stage, big = await getMob("MagmaCube");
  big.root.scale.setScalar(1.9); big.root.visible = false; S.scene.add(big.root);
  const smalls = [];
  for (let i = 0; i < 4; i++) { const m = await getMob("MagmaCube"); m.root.scale.setScalar(0.5); m.root.visible = false; S.scene.add(m.root); smalls.push(m); }
  const cz = -1.8;
  const cam = (t) => ({ x: 0, y: 1.62 + bob(t) * (1 - sstep(0.6, 0.9, t)), z: cz * Math.min(1, t / 0.9) * 0.0 - 0.6 * Math.min(t, 0.9), yaw: 0.2 * sstep(1.0, 1.9, t) , pitch: -0.12 * sstep(1.9, 2.4, t) - 0.1 * sstep(2.7, 3.2, t), roll: 0.08 * Math.sin(t * 5) * sstep(2.7, 4, t), fov: 72 });
  const hops = [[1.0, 1.45, [-4, 0, -4], [-2.4, 0, -4]], [1.45, 1.9, [-2.4, 0, -4], [-0.9, 0, -3.1]], [1.9, 2.4, [-0.9, 0, -3.1], [-0.1, 0, -1.6]]];
  const L = new THREE.PointLight(0xff6a10, 6, 9); S.scene.add(L);
  for (const h of hops) c.hitBurst([h[1]], () => ({ x: h[3][0], y: 0.1, z: h[3][2] }), "lava", 18, { dir: [0, 1, 0], speed: 2.2, spread: 0.8, size: 0.08, life: 0.9 });
  c.hitBurst([2.55], () => ({ x: -0.1, y: 1.2, z: -1.6 }), "lava", 70, { dir: [0, 0.6, 0.3], speed: 4, spread: 1.4, size: 0.1, life: 1.2 });
  const hits = [2.9, 3.45, 4.0, 4.55];
  c.hitBurst(hits, cam, "lava", 26, { dir: [0, 0.6, 0.3], speed: 2.6, spread: 1, life: 1 });
  const camP = cam(3);
  return {
    id: "MagmaCube", dur: 5.2, death: "You were slain by Magma Cube", hits, cam,
    shake: (t) => 0.007 + 0.06 * pulse(t, [1.45, 1.9, 2.4], 0.18) + 0.015 * sstep(2.7, 4, t),
    sounds: [[0.1, "qf.scare.riser"], [0.95, "mob.magmacube.jump"], [1.45, "mob.magmacube.big"], [1.45, "liquid.lavapop"], [1.5, "mob.magmacube.jump"], [1.9, "mob.magmacube.big"], [1.95, "mob.magmacube.jump"], [2.4, "qf.scare.hit"], [2.4, "mob.magmacube.big"], [2.55, "fire.ignite"], [2.7, "mob.magmacube.small"], [3.0, "mob.magmacube.small"], [3.5, "fire.fire"], [3.8, "mob.magmacube.small"], [5.2, "game.player.die"]],
    update(t, f) {
      big.root.visible = t > 0.95 && t < 2.55;
      for (const h of hops) {
        if (t >= h[0] && t < h[1]) {
          const k = (t - h[0]) / (h[1] - h[0]), a = h[2], b = h[3];
          big.root.position.set(lerp(a[0], b[0], k), 4.0 * 0 + 1.1 * Math.sin(k * Math.PI) * 1.3, lerp(a[2], b[2], k));
          big.root.rotation.y = Math.atan2(b[0] - a[0], b[2] - a[2]) + Math.PI + (-0.5);
          const sq = 1 + 0.18 * (Math.cos(k * Math.PI * 2) - 1) * -0.0;
          big.root.scale.y = 1.9 * (k < 0.15 ? 0.7 + 2 * k : k > 0.9 ? 0.75 + 2.5 * (1 - k) : 1.1);
        }
      }
      if (t >= 1.9 && t < 2.55) { const k = clamp((t - 1.9) / 0.5); const cp = cam(t); if (t > 2.4) { big.root.position.set(lerp(-0.1, 0, (t - 2.4) / 0.15), lerp(0.1, 1.3, easeOut((t - 2.4) / 0.15)), lerp(-1.6, cp.z - 0.55, easeOut((t - 2.4) / 0.15))); big.root.rotation.y = Math.PI; } }
      smalls.forEach((s, i) => {
        s.root.visible = t >= 2.5;
        if (!s.root.visible) return;
        const cp = cam(t), k = easeOut((t - 2.5) / (0.35 + i * 0.07)), ang = i * 1.57 + 0.5;
        const hopY = Math.abs(Math.sin((t - 2.5) * 6 + i)) * 0.35 * (1 - k * 0.3);
        s.root.position.set(lerp(-0.1, cp.x + Math.cos(ang) * 0.45, k), lerp(0.3, 0.5 + (i % 2) * 0.6, k) + hopY, lerp(-1.6, cp.z - 0.6 - (i > 1 ? 0.3 : 0), k));
        s.root.rotation.y = Math.PI + Math.sin(t * 3 + i) * 0.3;
      });
      L.position.set(0, 1.5, cam(t).z - 0.6); L.intensity = t > 0.95 ? 5 + 4 * sstep(2.4, 3.2, t) : 0;
      const fi = sstep(2.7, 3.7, t);
      f.fire = 0.5 * fi;
      f.tints.push([255, 90, 0, 0.18 * fi]);
      f.vig = [255, 60, 0, 0.5 * fi];
    }
  };
}

// ------------------------------------------------------------------------------------------------ Zombie Pigman
export async function pigman(c) {
  const S = c.stage, R = rngOf(41), horde = [];
  const N = c.phone ? 6 : 9;
  for (let i = 0; i < N; i++) {
    const m = await getMob("PigZombie"); S.scene.add(m.root); m.root.visible = false;
    const sword = addSword(m, 0xf0c030, 0x6a4a28);
    const row = i % 3, ang = (i / N) * 2.2 - 1.1;
    horde.push({ m, sword, ts: 0.7 + i * 0.12, ta: 2.3 + i * 0.1 + R() * 0.15, x0: (row - 1) * 0.8 + (R() - 0.5) * 0.4, fx: Math.sin(ang) * 1.15 + (R() - 0.5) * 0.2, fz: -Math.cos(ang) * 1.0 - 0.5, ph: R() * 6 });
  }
  const hits = [3.2, 3.75, 4.3, 4.85];
  const cam = (t) => ({ x: 0, y: 1.62 + bob(t) * (1 - sstep(0.6, 0.9, t)), z: -0.4 * Math.min(t, 0.9) + 0.45 * sstep(2.4, 4.2, t), yaw: 0.05 * Math.sin(t * 1.3) + 0.12 * Math.sin(t * 6) * sstep(2.5, 4, t), pitch: 0.0 + 0.1 * sstep(2.5, 3.2, t), roll: 0, fov: 72 + 6 * sstep(2.3, 3.4, t) });
  const L = new THREE.PointLight(0xff8040, 4, 6); S.scene.add(L);
  c.hitBurst(hits, cam, "blood", 28, { dir: [0, 0.6, 0.3], speed: 2.8, spread: 1.1 });
  const sl = [[3.2, 0.3, 0.38, 0.9], [3.75, 0.7, 0.4, -0.7], [4.3, 0.4, 0.5, 0.55], [4.85, 0.55, 0.45, -1.0]];
  return {
    id: "PigZombie", dur: 5.6, death: "You were slain by Zombie Pigman", hits, cam,
    shake: (t) => 0.008 + 0.02 * sstep(1.2, 2.4, t) + 0.015 * sstep(2.4, 4, t),
    sounds: [[0.1, "qf.scare.riser"], [0.7, "mob.zombiepig.zpigangry", { pos: { x: 0, y: 1.6, z: -14 } }], [1.3, "mob.zombiepig.zpig"], [1.7, "mob.zombiepig.zpigangry"], [2.2, "qf.scare.hit"], [2.3, "mob.zombiepig.zpigangry"], [3.2, "mob.zombiepig.zpighurt"], [3.75, "mob.zombiepig.zpigangry"], [4.3, "mob.zombiepig.zpig"], [4.85, "mob.zombiepig.zpigangry"], [5.6, "game.player.die"],
      ...Array.from({ length: 14 }, (_, i) => [1.0 + i * 0.17, "mob.zombie.step", { volume: 0.4 + i * 0.04 }])],
    update(t, f) {
      const cp = cam(t);
      for (const h of horde) {
        const r = h.m.root;
        r.visible = t > h.ts;
        if (!r.visible) continue;
        const k = clamp((t - h.ts) / (h.ta - h.ts)), run = t < h.ta;
        const x = lerp(h.x0, h.fx, easeOut(k * 0.0 + k)), z = lerp(-16, cp.z + h.fz, k);
        r.position.set(x, 0, z); faceTo(r, x, z, cp.x, cp.z);
        const swing = pulse(t, [3.2, 3.75, 4.3, 4.85], 0.12);
        limbs(h.m, t + h.ph, run ? 0.9 : 0.15, null, 14);
        pt(h.m, "lArm").rotation.x = 1.4 + Math.sin(t * 14 + h.ph) * 0.1;
        pt(h.m, "rArm").rotation.x = t > h.ta ? 2.5 - 2.2 * swing + Math.sin(t * 6 + h.ph) * 0.1 : 1.5 + Math.sin(t * 14) * 0.1;
        r.position.y = run ? Math.abs(Math.sin(t * 14 + h.ph)) * 0.08 : 0;
      }
      L.position.set(0, 2.3, cp.z - 0.5);
      for (const s of sl) if (t >= s[0]) f.slashes.push({ t0: s[0], x: s[1], y: s[2], ang: s[3], len: 300 });
      f.vig = [80, 0, 0, 0.35 * sstep(2.3, 4, t)];
    }
  };
}

// ------------------------------------------------------------------------------------------------ Wither Skeleton
export async function witherSkeleton(c) {
  const S = c.stage, ws = await getMob("WitherSkeleton");
  S.scene.add(ws.root); ws.root.visible = false;
  const sword = addSword(ws, 0x5a5a5e, 0x2a2018);
  const cam = (t) => ({ x: 0, y: 1.62 + bob(t) * (1 - sstep(1.0, 1.3, t)), z: -0.35 * Math.min(t, 1.2), yaw: 0.05 * Math.sin(t), pitch: 0.12 * sstep(1.5, 2.2, t), roll: 0, fov: 72 });
  const hits = [2.45, 3.4], swings = [2.35, 3.3];
  const L = new THREE.PointLight(0x6a3a9a, 2, 6); S.scene.add(L);
  c.hitBurst(hits, cam, "bone", 30, { dir: [0, 0.4, 0.4], speed: 2.6, spread: 1.2, size: 0.05 });
  c.hitBurst(hits, cam, "blood", 40, { dir: [0, 0.5, 0.5], speed: 3, spread: 1.2 });
  return {
    id: "WitherSkeleton", dur: 4.9, death: "You were slain by Wither Skeleton", hits, cam,
    flick: (t) => 1 - 0.92 * sstep(0.9, 2.1, t),
    shake: (t) => 0.007 + 0.05 * pulse(t, hits, 0.2),
    sounds: [[0.1, "qf.scare.riser"], [0.8, "mob.skeleton.say", { pitch: 0.7, pos: { x: 0, y: 1.6, z: -4.5 } }], [1.5, "mob.wither.idle"], [2.0, "qf.scare.hit"], [2.3, "mob.wither.shoot", { pitch: 1.4 }], [3.25, "mob.wither.shoot", { pitch: 1.4 }], [3.5, "mob.wither.hurt"], [4.2, "mob.wither.death", { volume: 0.6 }], [4.9, "game.player.die"]],
    update(t, f) {
      ws.root.visible = t > 0.7;
      const cp = cam(t), k = sstep(0.7, 2.2, t);
      const z = lerp(-5.5, cp.z - 1.5, k);
      ws.root.position.set(lerp(-0.3, 0, k), 0, z); ws.root.rotation.y = Math.PI;
      limbs(ws, t, k < 1 ? 0.5 : 0.1, null, 6);
      let ax = 0.3;
      for (const s of swings) {
        if (t < s - 0.5) continue;
        ax = t < s - 0.08 ? lerp(0.3, -2.9, sstep(s - 0.5, s - 0.08, t)) : t < s + 0.07 ? lerp(-2.9, 1.2, sstep(s - 0.08, s + 0.07, t)) : lerp(1.2, 0.3, sstep(s + 0.3, s + 0.7, t));
      }
      pt(ws, "rArm").rotation.x = ax;
      pt(ws, "lArm").rotation.x = 0.4;
      L.position.set(0, 2, cp.z - 1); L.intensity = 2 * (1 - sstep(2.5, 4, t));
      for (const s of swings) if (t >= s + 0.08) f.slashes.push({ t0: s + 0.08, x: 0.5, y: 0.45, ang: s < 3 ? 0.55 : -0.55, len: 330, col: "rgba(190,190,200,0.85)" });
      f.hpMode = t >= hits[0] ? "wither" : "normal";
      const wv = sstep(2.45, 4.4, t);
      f.vig = [10, 0, 14, 0.45 + 0.5 * wv];
      f.vigR = 0.95 - 0.55 * wv;
      f.black = sstep(3.5, 4.6, t);
      f.tints.push([20, 10, 30, 0.35 * sstep(2.4, 3.4, t)]);
    }
  };
}
