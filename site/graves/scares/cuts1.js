// Cutscenes 1-7: Zombie, Skeleton, Creeper, Spider, Cave Spider, Enderman, Witch.
// A cutscene is built once (async: mob textures), then asked for cam(t) and update(t, f) at any t.
//   hits    seconds of the damage hits (red flash, hurt tilt, gore, hurt sound, heart drop); >= 0.4 s apart
//   sounds  [t, event, options]; '@muffle' [hz, s] is the engine call; positions are stage coordinates
import { THREE, clamp, lerp, sstep, easeOut, rngOf, getMob, pt, tint, glow, box, faceTo } from "./stage.js";

export const bob = (t) => Math.sin(t * 7.4) * 0.025;
export function limbs(m, t, amp = 0.8, arms = null, speed = 9) {
  const s = Math.sin(t * speed) * amp;
  pt(m, "rLeg").rotation.x = s; pt(m, "lLeg").rotation.x = -s;
  if (arms != null) { pt(m, "rArm").rotation.x = arms + Math.sin(t * speed + 1) * 0.12; pt(m, "lArm").rotation.x = arms + Math.sin(t * speed) * 0.12; }
}
export function pulse(t, times, tau = 0.15) {
  let v = 0;
  for (const h of times) if (t >= h) v = Math.max(v, Math.exp(-(t - h) / tau));
  return v;
}
export function addSword(m, hex, handle = 0x6a4a28) {
  const g = new THREE.Group();
  const blade = box(0.08, 0.08, 0.85, hex, false); blade.position.z = -0.5;
  const guard = box(0.3, 0.06, 0.07, handle, false); guard.position.z = -0.1;
  const grip = box(0.07, 0.07, 0.2, handle, false); grip.position.z = 0.02;
  g.add(blade, guard, grip);
  g.position.set(0, -0.62, -0.1);
  pt(m, "rArm").add(g);
  return g;
}

// A swarm of small mobs that pours from a point, runs at the camera and climbs onto the lens.
export async function makeSwarm(c, { id, n, from, t0, spread, arrive, scale, camAt, climb = 1.3, seed = 5, floorY = 0 }) {
  const R = rngOf(seed), S = c.stage, items = [];
  for (let i = 0; i < n; i++) {
    const m = await getMob(id); m.root.scale.multiplyScalar(scale * (0.8 + R() * 0.5));
    m.root.visible = false; S.scene.add(m.root);
    items.push({ m, ts: t0 + i * spread + R() * 0.1, ta: arrive + i * spread * 0.9 + R() * 0.3, ox: (R() - 0.5) * 0.9, oz: (R() - 0.5) * 0.5, curve: (R() - 0.5) * 1.4, ph: R() * 6 });
  }
  return {
    update(t) {
      for (const it of items) {
        const r = it.m.root;
        if (t < it.ts) { r.visible = false; continue; }
        r.visible = true;
        const cp = camAt(it.ta), ca = camAt(t);
        const tx = cp.x + it.ox, tz = cp.z + it.oz;
        const k = clamp((t - it.ts) / (it.ta - it.ts));
        let x = lerp(from[0], tx, k) + Math.sin(k * 6.28) * it.curve * (1 - k) * 0.5, z = lerp(from[2], tz, k), y = floorY + (1 - k) * 0.0;
        let rx = 0;
        if (t > it.ta) {
          const u = (t - it.ta) * climb;
          y = floorY + Math.min(2.0, u * 1.2);
          x = lerp(tx, ca.x + it.ox * 0.4, clamp(u * 0.8)); z = lerp(tz, ca.z - 0.38 + it.oz * 0.3, clamp(u * 0.8));
          rx = 1.0;
        }
        r.position.set(x, y, z);
        const dx = tx - from[0], dz = tz - from[2];
        r.rotation.set(rx, t > it.ta ? Math.PI : Math.atan2(dx, dz) + Math.PI, 0, "YXZ");
        it.m.anim(t * 2.2 + it.ph, 0, { walk: 1.6 });
      }
    }
  };
}

// ------------------------------------------------------------------------------------------------ Zombie
export async function zombie(c) {
  const S = c.stage, z = await getMob("Zombie");
  const pivot = new THREE.Group(); pivot.rotation.order = "YXZ"; pivot.add(z.root); S.scene.add(pivot); pivot.visible = false;
  const hits = [2.35, 3.0, 3.55, 4.1, 4.65, 5.2];
  const z0 = (t) => -1.25 * Math.min(t, 2.3);
  const feet = [-1.7, 0, -4.2], fdir = [1, 0];
  const leanAt = (t) => t < 2.3 ? 0 : (0.72 + 0.12 * pulse(t, hits.slice(1), 0.2)) * sstep(2.3, 2.9, t);
  const cam = (t) => {
    const k2 = sstep(2.5, 3.3, t), z0t = z0(t);
    const c = {
      x: lerp(0, -0.1, k2), y: lerp(1.62 + bob(t) * (1 - k2), 0.38, k2), z: z0t + lerp(0, -1.0, k2),
      yaw: 0.55 * sstep(1.7, 2.3, t) + 0.6 * sstep(2.35, 3.3, t), pitch: lerp(0, 0.85, k2) - 0.05 * sstep(2.3, 2.45, t),
      roll: 0.3 * k2, fov: lerp(72, 66, k2)
    };
    const w = sstep(2.6, 3.3, t), ln = leanAt(t), hx = feet[0] + fdir[0] * 1.65 * Math.sin(ln), hz = feet[2] + fdir[1] * 1.65 * Math.sin(ln), hy = 1.65 * Math.cos(ln);
    const ty = Math.atan2(-(hx - c.x), -(hz - c.z)), tpch = Math.atan2(hy - c.y, Math.hypot(hx - c.x, hz - c.z));
    c.yaw = lerp(c.yaw, ty, w); c.pitch = lerp(c.pitch, tpch, w);
    return c;
  };
  c.hitBurst(hits.slice(1), cam, "blood", 26, { dir: [0, 1.2, 0.2], speed: 2.6, spread: 0.9 });
  c.hitBurst([2.35], cam, "blood", 14, { dir: [0, 0.6, 0], speed: 2 });
  const L = new THREE.PointLight(0xff3010, 0, 4); S.scene.add(L);
  return {
    id: "Zombie", dur: 5.9, death: "You were slain by Zombie", hits, cam,
    shake: (t) => 0.012 + 0.03 * sstep(2.3, 2.5, t) * (1 - sstep(3.2, 3.6, t)),
    sounds: [[0.1, "qf.scare.riser"], [1.35, "mob.zombie.say", { pos: { x: -3, y: 1, z: -4 } }], [1.9, "mob.zombie.say", { pos: { x: -1.5, y: 1, z: -3.8 } }],
      [2.3, "qf.scare.hit"], [2.35, "mob.zombie.say", { pos: { x: -1, y: 1.4, z: -3.5 } }], [2.5, "qf.krypt.heartbeat"],
      [3.0, "mob.zombie.say"], [3.55, "mob.zombie.hurt"], [4.1, "mob.zombie.say"], [4.65, "mob.zombie.hurt"], [5.2, "mob.zombie.say"], [5.9, "game.player.die"]],
    update(t, f) {
      pivot.visible = t > 1.3;
      const ka = clamp((t - 1.4) / 0.95);
      const px = t < 2.35 ? lerp(-3.6, feet[0], easeOut(ka)) : feet[0], pz = t < 2.35 ? lerp(-4.6, feet[2], easeOut(ka)) : feet[2];
      pivot.position.set(px, 0, pz);
      const cp = cam(Math.min(t, 2.34));
      faceTo(pivot, px, pz, t < 2.35 ? cp.x : px + 1, t < 2.35 ? cp.z : pz);
      const bite = pulse(t, hits.slice(1), 0.2);
      pivot.rotation.x = -leanAt(t);
      if (t < 2.35) limbs(z, t, 0.7, 1.45, 12); else {
        limbs(z, 0, 0, 1.9 + Math.sin(t * 26) * 0.12, 1);
        pt(z, "head").rotation.x = 0.25 - bite * 0.3;
      }
      L.intensity = 3 * bite * sstep(2.3, 2.6, t); L.position.set(-0.1, 0.9, -3.4);
      f.vig = [90, 0, 0, 0.25 * sstep(2.3, 3.4, t)];
    }
  };
}

// ------------------------------------------------------------------------------------------------ Skeleton
export async function skeleton(c) {
  const S = c.stage, sk = await getMob("Skeleton");
  sk.root.position.set(0, 0, -7); sk.root.rotation.y = 0 + Math.PI; sk.root.visible = false; S.scene.add(sk.root);
  const bow = new THREE.Group();
  const wood = 0x6a4a28; const b1 = box(0.05, 0.5, 0.05, wood, false), b2 = box(0.05, 0.3, 0.05, wood, false), b3 = box(0.05, 0.3, 0.05, wood, false);
  b1.position.set(0, 0, 0); b2.position.set(0, 0.35, -0.1); b2.rotation.x = -0.5; b3.position.set(0, -0.35, -0.1); b3.rotation.x = 0.5;
  const str = box(0.01, 1.1, 0.01, 0xdddddd); str.position.z = 0.05;
  bow.add(b1, b2, b3, str); bow.position.set(0, -0.6, -0.5); pt(sk, "lArm").add(bow);
  const light = new THREE.PointLight(0xa0b8ff, 4, 6); light.position.set(0, 2.4, -6); S.scene.add(light);
  const hits = [2.35, 3.95];
  const cam = (t) => ({ x: 0, y: 1.62 + bob(t) * 0.6, z: -0.45 * Math.min(t, 4), yaw: 0, pitch: 0.02 * sstep(2.5, 3.9, t), roll: 0, fov: 72 - 14 * sstep(2.6, 3.95, t) });
  const arrows = [];
  const mkArrow = () => {
    const g = new THREE.Group();
    const shaft = box(0.025, 0.025, 0.75, 0x9a7a4a, false); const tip = box(0.05, 0.05, 0.1, 0x8a8a90, false); tip.position.z = 0.42;
    const fl = box(0.1, 0.01, 0.12, 0xffffff, false); fl.position.z = -0.33; const fl2 = box(0.01, 0.1, 0.12, 0xdddddd, false); fl2.position.z = -0.33;
    g.add(shaft, tip, fl, fl2); S.scene.add(g); g.visible = false; return g;
  };
  const bowPos = [0, 1.45, -6.6];
  const shots = [
    { t0: 0.95, t1: 1.4, to: [1.45, 1.9, -3.3], m: mkArrow() },
    { t0: 1.3, t1: 1.8, to: [-1.45, 1.1, -2.4], m: mkArrow() },
    { t0: 1.65, t1: 2.15, to: [0.25, 0.02, -2.0], m: mkArrow() },
    { t0: 1.9, t1: 2.35, to: null, off: [0.65, -0.35, -0.15], m: mkArrow() },
    { t0: 3.05, t1: 3.95, to: null, off: [0, 0, -0.04], m: mkArrow(), slow: true }
  ];
  for (const sh of shots) {
    const end = sh.to || (() => { const k = cam(sh.t1); return [k.x + sh.off[0], k.y + sh.off[1], k.z + sh.off[2]]; })();
    sh.end = end;
  }
  c.hitBurst([3.95], cam, "blood", 60, { dir: [0, 0.4, 1.2], speed: 3.5, spread: 1.4 });
  c.hitBurst([2.35], cam, "blood", 18, { dir: [0.7, 0.3, 0.2], speed: 2.4 });
  return {
    id: "Skeleton", dur: 4.8, death: "You were shot by Skeleton", hits, cam,
    shake: (t) => 0.01 + 0.03 * pulse(t, [1.4, 1.8, 2.15], 0.12),
    sounds: [[0.1, "qf.scare.riser"], [0.8, "mob.skeleton.say", { pos: { x: 0, y: 1.5, z: -7 } }], [0.95, "random.bow"], [1.4, "random.bowhit"], [1.3, "random.bow"], [1.8, "random.bowhit"],
      [1.65, "random.bow"], [2.15, "random.bowhit"], [1.9, "random.bow"], [3.0, "qf.scare.hit"], [3.05, "random.bow"], [3.1, "qf.krypt.heartbeat"], [3.95, "random.bowhit"], [4.8, "game.player.die"]],
    update(t, f) {
      sk.root.visible = t > 0.7;
      const draw = sstep(0.8, 1.0, t), re = pulse(t, [0.95, 1.3, 1.65, 1.9, 3.05], 0.18);
      pt(sk, "rArm").rotation.set(-1.45 - (t > 2.5 && t < 3.0 ? 0.2 : 0), -0.3 * draw, 0);
      pt(sk, "lArm").rotation.set(-1.5, 0.1, 0);
      pt(sk, "rArm").rotation.x = -(1.4 + 0.15 * (1 - re));
      pt(sk, "head").rotation.y = Math.sin(t * 2) * 0.1;
      for (const sh of shots) {
        const m = sh.m;
        if (t < sh.t0) { m.visible = false; continue; }
        m.visible = true;
        let k = clamp((t - sh.t0) / (sh.t1 - sh.t0));
        if (sh.slow) k = Math.pow(k, 2.2);
        const e = sh.end, p = [lerp(bowPos[0], e[0], k), lerp(bowPos[1], e[1], k) + 0.8 * Math.sin(k * Math.PI) * 0, lerp(bowPos[2], e[2], k)];
        m.position.set(p[0], p[1], p[2]);
        m.lookAt(e[0], e[1], e[2]);
        if (k >= 1 && !sh.slow) { const w = Math.exp(-(t - sh.t1) * 4) * Math.sin((t - sh.t1) * 60) * 0.06; m.rotation.z += w; }
        if (sh.slow && t >= sh.t1) m.visible = false;
      }
      if (t >= 3.95) f.cracks.push({ t0: 3.95, x: 0.5, y: 0.5, arms: 11, len: 150, seed: 4 });
      f.vig = [0, 0, 0, 0.5 * sstep(2.5, 3.9, t)];
    }
  };
}

// ------------------------------------------------------------------------------------------------ Creeper
export async function creeper(c) {
  const S = c.stage, cr = await getMob("Creeper");
  const pos = [0.15, 0, -0.1];
  tint(cr, 0x8c8c8c); cr.root.position.set(pos[0], 0, pos[2]); cr.root.visible = true; S.scene.add(cr.root);
  cr.root.rotation.y = 0;
  const cam = (t) => {
    const turn = sstep(1.55, 2.25, t);
    const back = 0.25 * sstep(2.3, 3.9, t);
    return { x: 0, y: 1.62 + bob(t) * (1 - turn), z: -0.8 * Math.min(t, 1.5) + back, yaw: Math.PI * turn + 0.02 * Math.sin(t * 40) * sstep(3.0, 3.9, t), pitch: -0.12 * sstep(2.2, 3.9, t), roll: 0, fov: 72 - 6 * sstep(2.3, 3.9, t) };
  };
  const bt = 3.92;
  c.hitBurst([bt], (t) => ({ x: 0.15, y: 0.9, z: -0.1 }), "stone", 140, { dir: [0, 0.4, 0], speed: 6.5, spread: 1.3, size: 0.1, life: 2.2 });
  c.hitBurst([bt], (t) => ({ x: 0.15, y: 0.9, z: -0.1 }), "dust", 90, { dir: [0, 0.6, 0], speed: 3, spread: 1, size: 0.16, life: 2.5, grav: 1.5 });
  c.hitBurst([bt], (t) => ({ x: 0.15, y: 0.6, z: -0.1 }), "fire", 60, { dir: [0, 0.5, 0], speed: 4.5, spread: 1, size: 0.12, life: 0.8 });
  const L = new THREE.PointLight(0xffffff, 0, 8); L.position.set(0.15, 1.2, -0.1); S.scene.add(L);
  return {
    id: "Creeper", dur: 5.2, flick: () => 0.5, death: "You were blown up by Creeper", hits: [bt], cam, silence: true,
    shake: (t) => 0.006 + 0.01 * sstep(2.3, 3.9, t) + 0.25 * pulse(t, [bt], 0.45),
    sounds: [[0.1, "qf.scare.riser", { volume: 0.6 }], [1.6, "step.stone", { volume: 0.7 }], [1.95, "mob.creeper.say", { pos: { x: 0.15, y: 1, z: -0.1 } }], [2.25, "random.fuse"], [3.5, "qf.scare.hit"],
      [bt, "random.explode"], [bt + 0.05, "@muffle", [350, 3.5]], [bt + 0.1, "qf.scare.ringing"], [5.2, "game.player.die"]],
    update(t, f) {
      const gone = t >= bt;
      cr.root.visible = !gone;
      const sw = sstep(2.3, 3.9, t), fz = t > 2.3 ? 3 + 3 * sw : 0;
      cr.root.scale.set(1 + 0.45 * sw + (t > 2.3 ? 0.05 * Math.sin(t * 22) : 0), 1 + 0.3 * sw + (t > 2.3 ? 0.04 * Math.sin(t * 22) : 0), 1 + 0.45 * sw);
      cr.root.rotation.y = Math.sin(t * 3) * 0.05;
      const flash = t > 2.3 ? (Math.floor(t * fz) % 2 ? 0.12 : 0) : 0;
      glow(cr, flash, 0xffffff);
      limbs(cr, 0, 0, null);
      L.intensity = gone ? 0 : flash * 5;
      f.white = gone ? clamp(1 - (t - bt) / 1.1) : 0;
      const sm = gone ? sstep(bt + 0.2, bt + 1.2, t) : 0;
      f.tints.push([60, 56, 52, 0.55 * sm]);
      f.vig = [20, 18, 16, 0.7 * sm];
    }
  };
}

// ------------------------------------------------------------------------------------------------ Spider
export async function spider(c) {
  const S = c.stage, sp = await getMob("Spider");
  sp.root.visible = false; sp.root.scale.setScalar(1.15); S.scene.add(sp.root);
  const thread = box(0.012, 1, 0.012, 0xdddddd); S.scene.add(thread);
  const hits = [2.35, 2.95, 3.55, 4.15];
  const camz = -0.7;
  const cam = (t) => ({ x: 0, y: 1.62 + bob(t) * (1 - sstep(1.5, 1.8, t)), z: camz * Math.min(t, 1.5), yaw: 0, pitch: 0.28 * sstep(1.0, 1.7, t) - 0.12 * sstep(2.3, 2.5, t), roll: 0, fov: 72 });
  const cz = camz * 1.5;
  const L = new THREE.PointLight(0xff3a20, 0, 4); S.scene.add(L);
  c.hitBurst(hits, cam, "blood", 22, { dir: [0, 0.5, 0.2], speed: 2.6, spread: 1 });
  return {
    id: "Spider", dur: 4.9, death: "You were slain by Spider", hits, cam,
    shake: (t) => 0.01 + 0.035 * sstep(1.7, 1.8, t) * (1 - sstep(2.2, 3.0, t)) + 0.012 * sstep(2.3, 4, t),
    sounds: [[0.1, "qf.scare.riser"], [1.0, "mob.spider.say", { pos: { x: 0, y: 2.8, z: -2 } }], [1.55, "mob.spider.say"], [1.78, "qf.scare.hit"], [1.78, "mob.spider.say"],
      [2.5, "qf.krypt.heartbeat"], [3.0, "mob.spider.say"], [3.8, "mob.spider.say"], [4.9, "game.player.die"]],
    update(t, f) {
      const dropK = easeOut((t - 1.7) / 0.13);
      const hang = t < 1.7;
      sp.root.visible = t > 0.95;
      const x = 0, hangY = lerp(3.4, 2.5, sstep(0.95, 1.5, t));
      const bite = pulse(t, hits, 0.2);
      let y, z;
      if (hang) { y = hangY; z = -2.2; }
      else { y = lerp(2.5, 1.2, dropK); z = lerp(-2.2, cz - 1.7, dropK) + 0.35 * bite; }
      sp.root.position.set(x, y, z);
      sp.root.rotation.set(hang ? 0.2 : 0.05 + 0.15 * bite, Math.PI, 0);
      thread.visible = hang && t > 0.95; thread.scale.y = Math.max(0.01, 3.2 - y); thread.position.set(0, (3.2 + y) / 2 + 0.2, z);
      sp.anim(t * (t < 1.7 ? 1 : 3), 0, { walk: t < 1.7 ? 0.3 : 1.6 });
      pt(sp, "head").rotation.x = -0.4 * bite;
      L.position.set(0, y + 0.2, z + 1.2); L.intensity = t > 1.7 ? 0.6 + 0.8 * bite : 0;
      f.vig = [70, 0, 0, 0.3 * sstep(1.8, 3, t)];
    }
  };
}

// ------------------------------------------------------------------------------------------------ Cave Spider
export async function caveSpider(c) {
  const S = c.stage;
  const cam = (t) => {
    const sway = Math.sin(t * 2.2) * 0.01;
    return { x: 0, y: 1.62 + bob(t) * (1 - sstep(0.5, 0.8, t)) - 0.35 * sstep(2.4, 3.4, t), z: -0.5 * Math.min(t, 0.7) - 0.4 * sstep(0.6, 0.9, t) * 0, yaw: -0.5 * sstep(0.8, 1.5, t) + sway, pitch: -0.3 * sstep(1.2, 2.0, t) + 0.55 * sstep(2.4, 3.6, t), roll: 0.12 * Math.sin(t * 3) * sstep(2.4, 3.4, t), fov: 72 };
  };
  const crack = box(0.02, 1.0, 0.5, 0x000000); crack.position.set(1.49, 0.5, -3.6); S.scene.add(crack);
  const hole = box(0.03, 0.5, 0.35, 0x66ff33); hole.position.set(1.48, 0.25, -3.6); S.scene.add(hole);
  const sw = await makeSwarm(c, { id: "CaveSpider", n: phoneN(c, 26), from: [1.2, 0, -3.6], t0: 0.95, spread: 0.07, arrive: 1.9, scale: 1.1, camAt: cam, seed: 11 });
  const hits = [2.5, 3.05, 3.6, 4.15, 4.7];
  const G = new THREE.PointLight(0x40ff20, 3, 5); G.position.set(1.0, 0.3, -3.6); S.scene.add(G);
  c.hitBurst(hits, cam, "green", 20, { dir: [0, 0.8, 0.3], speed: 2.4, spread: 1 });
  return {
    id: "CaveSpider", dur: 5.4, death: "You were slain by Cave Spider", hits, cam,
    shake: (t) => 0.008 + 0.025 * sstep(2.0, 2.6, t),
    sounds: [[0.1, "qf.scare.riser"], [0.7, "dig.stone"], [0.95, "random.break"], [1.1, "mob.spider.say"], [1.5, "mob.spider.say"], [1.9, "qf.scare.hit"], [2.2, "mob.spider.say"], [2.6, "mob.spider.say"], [3.2, "mob.spider.say"], [3.8, "mob.spider.say"], [4.4, "mob.spider.say"], [5.4, "game.player.die"]],
    update(t, f) {
      sw.update(t);
      crack.visible = hole.visible = t > 0.6; hole.material.color.setHex(t < 0.95 ? 0x103008 : 0x66ff33);
      f.vig = [60, 190, 30, 0.7 * sstep(2.3, 4.2, t)];
      f.tints.push([40, 120, 20, 0.22 * sstep(2.3, 4.5, t)]);
      f.hpMode = t >= hits[0] ? "poison" : "normal";
    }
  };
}
function phoneN(c, n) { return c.phone ? Math.round(n * 0.6) : n; }

// ------------------------------------------------------------------------------------------------ Enderman
export async function enderman(c) {
  const S = c.stage, en = await getMob("Enderman");
  const tp = 2.2;
  S.scene.add(en.root); en.root.visible = false;
  const cam = (t) => ({
    x: 0, y: 1.62 + bob(t) * (1 - sstep(1.2, 1.6, t)), z: -0.5 * Math.min(t, 1.6), yaw: 0.0,
    pitch: 0.2 * sstep(0.6, 1.4, t) + 0.3 * sstep(tp, tp + 0.5, t), roll: 0, fov: 72 - 12 * sstep(0.6, 2.1, t) + 8 * sstep(tp, tp + 0.3, t)
  });
  const L = new THREE.PointLight(0xb040ff, 4, 9); S.scene.add(L);
  for (let k = 0; k < 14; k++) c.hitBurst([0.5 + k * 0.12], () => ({ x: (k % 3 - 1) * 0.3, y: 0.3 + (k % 5) * 0.5, z: -14 }), "purple", 8, { dir: [0, 0.4, 0], speed: 0.6, spread: 1, size: 0.07, life: 1.6, grav: -0.5 });
  c.hitBurst([tp], () => ({ x: 0, y: 1.2, z: -14 }), "purple", 40, { speed: 1.4, spread: 1.2, life: 1.3, grav: -1 });
  c.hitBurst([tp], () => ({ x: 0, y: 1.2, z: -2.4 }), "purple", 60, { speed: 2.4, spread: 1.4, life: 1.3, grav: -0.5 });
  const hits = [3.0, 3.6, 4.2, 4.8];
  c.hitBurst(hits, cam, "blood", 22, { dir: [0, 0.6, 0.3], speed: 2.4, spread: 1 });
  return {
    id: "Enderman", dur: 5.6, death: "You were slain by Enderman", hits, cam,
    shake: (t) => 0.008 + 0.02 * sstep(1.4, 2.2, t) + 0.03 * sstep(tp, tp + 0.2, t) * (1 - sstep(tp + 0.2, tp + 0.8, t)),
    sounds: [[0.1, "qf.scare.riser"], [0.5, "mob.endermen.stare"], [1.6, "mob.endermen.idle"], [tp - 0.05, "mob.endermen.portal"], [tp, "qf.scare.hit"], [tp + 0.1, "mob.endermen.scream"], [2.8, "qf.krypt.heartbeat"], [3.6, "mob.endermen.scream"], [4.5, "mob.endermen.hit"], [5.6, "game.player.die"]],
    update(t, f) {
      en.root.visible = t > 0.5;
      const near = t >= tp;
      const k = sstep(tp, tp + 0.9, t);
      const jx = Math.sin(t * 90) * 0.015 * sstep(0.8, 2.2, t), jz = near ? 0.012 * Math.sin(t * 70) : 0;
      en.root.position.set(jx, 0, near ? lerp(-3.0, -1.95, k) : -14 + jz);
      en.root.rotation.set(near ? -0.25 * k : 0, Math.PI, 0, "YXZ");
      limbs(en, t, near ? 0 : 0.0, near ? 2.1 + Math.sin(t * 40) * 0.2 : 0.1, 1);
      pt(en, "head").rotation.x = near ? -0.55 * k : 0;
      pt(en, "headwear").rotation.x = near ? 0.75 * sstep(tp, tp + 0.4, t) + 0.12 * Math.sin(t * 30) : 0;
      L.position.set(0, 2.2, near ? -1.5 : -13); L.intensity = near ? 2 : 3;
      f.glitch = near ? 0.12 + 0.3 * pulse(t, hits, 0.25) : sstep(1.3, tp, t) * 0.6;
      f.tints.push([160, 60, 255, 0.5 * pulse(t, [tp], 0.12)]);
      f.vig = [60, 0, 100, 0.3 * sstep(1.0, 3.0, t)];
    }
  };
}

// ------------------------------------------------------------------------------------------------ Witch
export async function witch(c) {
  const S = c.stage, w = await getMob("Witch");
  S.scene.add(w.root); w.root.visible = false;
  const cam = (t) => ({ x: 0, y: 1.62 + bob(t) * (1 - sstep(1.2, 1.5, t)), z: -0.4 * Math.min(t, 1.4), yaw: 0.04 * Math.sin(t * 1.5), pitch: -0.02, roll: 0.14 * Math.sin(t * 3.1) * sstep(2.95, 3.6, t), fov: 72 + 9 * Math.sin(t * 4.4) * sstep(2.95, 3.6, t) });
  const bottle = new THREE.Group();
  const glass = box(0.14, 0.18, 0.14, 0xff4fb0); const cork = box(0.07, 0.06, 0.07, 0x8a6a3a, false); cork.position.y = 0.12;
  bottle.add(glass, cork); S.scene.add(bottle); bottle.visible = false;
  const tH = 1.5, tHit = 2.95;
  const throwFrom = [-0.2, 1.6, -4.4];
  const L = new THREE.PointLight(0xd040ff, 0, 6); S.scene.add(L);
  const WL = new THREE.PointLight(0xffa060, 2.5, 6); S.scene.add(WL);
  const hits = [tHit, 3.5, 4.05];
  c.hitBurst([tHit], cam, "purple", 60, { dir: [0, 0.6, 0.8], speed: 3.2, spread: 1.2 });
  c.hitBurst([tHit], cam, "white", 30, { dir: [0, 0.4, 0.8], speed: 3.5, spread: 1.2, size: 0.03 });
  c.hitBurst(hits.slice(1), cam, "purple", 20, { dir: [0, 0.6, 0.3], speed: 2.4, spread: 1 });
  return {
    id: "Witch", dur: 5.0, death: "You were killed by Witch using magic", hits, cam,
    shake: (t) => 0.008 + 0.04 * pulse(t, [tHit], 0.3),
    sounds: [[0.1, "qf.scare.riser"], [0.6, "mob.villager.idle", { pitch: 0.55, pos: { x: 0, y: 1.8, z: -6 } }], [1.2, "mob.villager.idle", { pitch: 0.5 }], [tH, "random.bow", { pitch: 0.6 }], [2.7, "qf.scare.hit"],
      [tHit, "random.glass"], [tHit, "random.splash"], [3.3, "mob.villager.idle", { pitch: 0.5 }], [3.5, "random.fizz"], [4.1, "mob.villager.idle", { pitch: 0.45 }], [5.0, "game.player.die"]],
    update(t, f) {
      w.root.visible = t > 0.55;
      const approach = sstep(3.0, 4.8, t);
      const wz = lerp(-4.6, -2.2, approach);
      w.root.position.set(-0.2, 0, wz); WL.position.set(-0.2, 2.4, wz + 1.2); w.root.rotation.set(0, Math.PI, 0);
      const wind = sstep(1.1, tH, t), thr = sstep(tH, tH + 0.12, t);
      pt(w, "rArm").rotation.x = t < tH ? -2.6 * wind : lerp(-2.6, -0.5, thr);
      pt(w, "lArm").rotation.x = Math.sin(t * 9) * 0.3;
      pt(w, "head").rotation.z = Math.sin(t * 12) * 0.08 * (t > 0.6 ? 1 : 0); pt(w, "head").rotation.x = 0.1 * Math.sin(t * 20) * sstep(0.6, 1.1, t) ;
      const k = clamp((t - tH) / (tHit - tH));
      bottle.visible = t >= tH && t < tHit;
      const cp = cam(t);
      bottle.position.set(lerp(throwFrom[0], cp.x, k), lerp(throwFrom[1], cp.y - 0.05, k) + 1.4 * Math.sin(k * Math.PI), lerp(throwFrom[2], cp.z - 0.1, k));
      bottle.rotation.set(t * 14, t * 9, 0);
      bottle.scale.setScalar(1 + k * 2.2);
      L.position.set(cp.x, cp.y, cp.z - 0.4); L.intensity = t >= tHit ? 4 * (1 - 0.5 * sstep(tHit, 4.5, t)) : 0;
      if (t >= tHit) {
        f.splats.push({ t0: tHit, x: 0.5, y: 0.45, r: 70, seed: 21, col: "#b43cd8", dk: "#6a1a90", hl: "#e49cff" });
        f.splats.push({ t0: tHit + 0.04, x: 0.3, y: 0.5, r: 40, seed: 22, col: "#b43cd8", dk: "#6a1a90", hl: "#e49cff" });
        f.cracks.push({ t0: tHit, x: 0.52, y: 0.44, arms: 8, len: 110, seed: 8 });
        f.bubbles = 0.7 * sstep(tHit, tHit + 0.8, t); f.bubbleCol = "#d070ff";
        f.hpMode = "poison";
      }
      f.vig = [150, 30, 200, 0.55 * sstep(tHit, 3.8, t)];
      f.tints.push([150, 40, 200, 0.2 * sstep(tHit, 4, t)]);
    }
  };
}
