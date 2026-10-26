// Pieces several scares share: the freeze (the head settles where the walk stopped), the fall to the floor,
// timing helpers, and the hearts' damage bookkeeping.
import { THREE, track, clamp, lerp, sstep, wobble } from "./rig.js";

// The freeze: from the pose the walk left (often turned to a stone) the head comes to rest looking down the corridor,
// at the 1.62 m eye. Returns a base camera at t.
export function settle(R, t, t1 = 0.9, to = {}) {
  const k = sstep(0, t1, t), s = R.start;
  return { x: lerp(s.x, to.x ?? s.x, k), y: lerp(s.y, to.y ?? R.eye, k), z: lerp(s.z, to.z ?? s.z, k), yaw: lerp(s.yaw, to.yaw ?? 0, k),
    pitch: lerp(s.pitch, to.pitch ?? -0.02, k), roll: 0, fov: lerp(s.fov, to.fov ?? s.fov, k) };
}
// Shake for a hand-held head: amp in metres (and a third of it in radians).
export function shake(c, t, amp, seed = 0) {
  if (amp <= 0) return c;
  c.x += wobble(t, seed) * amp; c.y += wobble(t, seed + 5) * amp; c.yaw += wobble(t, seed + 9) * amp * 0.35; c.pitch += wobble(t, seed + 13) * amp * 0.3;
  return c;
}
// Damage list -> hits with a total of 20 (the last one kills).
export function hitsOf(list) {
  let left = 20;
  return list.map(([t, dmg, side], i) => { const d = i === list.length - 1 ? left : Math.min(left - 1, dmg); left -= d; return { t, dmg: d, side: side ?? (i % 2 ? -1 : 1) }; });
}
// Hurt sounds for each hit (game.player.hurt), plus extras.
export function hurtSounds(hits, extra = []) {
  const out = [];
  hits.forEach((h, i) => { out.push([h.t, "game.player.hurt"]); for (const [dt, name, o] of extra) out.push([h.t + dt, typeof name === "function" ? name(i) : name, o]); });
  return out;
}
// Knocked down: the head falls to the floor (y ~0.25) and rolls onto its side over d seconds, from pose c at t0.
export function floorFall(c, t, t0, { d = 0.55, side = 1, roll = 1.25, y = 0.24, pitch = 0.1, back = 0.25 } = {}) {
  if (t <= t0) return c;
  const k = clamp((t - t0) / d), e = k * k;   // gravity: accelerating
  const bounce = k >= 1 ? Math.exp(-(t - t0 - d) * 9) * Math.sin((t - t0 - d) * 30) * 0.02 : 0;
  c.y = lerp(c.y, y, e) + bounce; c.roll = lerp(c.roll || 0, roll * side, sstep(0.15, 1, k)); c.pitch = lerp(c.pitch, pitch, sstep(0, 1, k));
  c.z -= back * e;
  return c;
}
export { track, clamp, lerp, sstep };

// Limbs that reach into the lens: copies of a mob's part (an arm, a leg) parented to the head (R.view), drawn over
// the world. specs: [{ from: [x, y], to: [x, y], z, t0, t1, scale }] in view metres (x right, y up, z forward < 0).
export function lensLimbs(R, mob, part, specs, { color = 0x8a8a8a } = {}) {
  const src = mob.parts[part];
  const out = specs.map((s) => {
    const g = src.clone(true);
    g.traverse((o) => {
      if (!o.isMesh) return;
      const m = Array.isArray(o.material) ? o.material[0] : o.material;
      o.material = new THREE.MeshBasicMaterial({ map: m.map || null, color, transparent: true, depthTest: false, depthWrite: false, side: THREE.DoubleSide, alphaTest: 0.1, fog: false });
      o.renderOrder = 2000;
    });
    g.rotation.set(0, 0, 0); g.position.set(0, 0, 0);
    const holder = new THREE.Group(); holder.add(g); holder.visible = false; R.view.add(holder);
    return { s, holder };
  });
  return (t) => {
    for (const { s, holder } of out) {
      const k = sstep(s.t0, s.t1, t);
      holder.visible = k > 0;
      if (!holder.visible) continue;
      const x = lerp(s.from[0], s.to[0], k), y = lerp(s.from[1], s.to[1], k);
      const dx = s.to[0] - s.from[0], dy = s.to[1] - s.from[1];
      holder.position.set(x, y, s.z ?? -0.32);
      holder.rotation.set(s.tilt ?? 0, 0, Math.atan2(dx, -dy) + (s.twist ?? 0) * Math.sin(t * 7));
      holder.scale.setScalar(s.scale ?? 0.55);
    }
  };
}
