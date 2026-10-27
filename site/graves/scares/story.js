// The Story Mode kit (round 7): the climax as a physical beat in the world, not a glitch on the lens.
// What the approved Enderman and Creeper do, and the rest now follow: the mob's own behaviour carries the scare (the
// stare and the teleport; the silent walk-up, the hiss and the swell), every sound is its own, a device such as a
// glitch is there only when the mob explains it, and the blow lands on a body standing in a place, with a mark left.
//   roar(t, own, o)            the mob's own cry at full voice with the sub hit under it (no screech, no static)
//   blow(t, o)                 a blow landing on you: the hurt, the hit, gore or a crunch
//   kick(t, hits, o)           the head knocked by blows: { yaw, pitch, back } to add to the camera, recovering
//   impactSplit(f, t, times)   the one subtle device a scare may keep: a short RGB split on a blow (no tear, no static)
//   hop(a, b, k, h)            a point along a step or a pounce between local points, with a hop arc of height h
//   faceOf(m, out)             where a mob's face is now, in world space (its head part's front)
import { THREE, clamp, lerp, pulse } from "./rig.js";

export function roar(t, own = [], { volume = 1, hit = 0.7 } = {}) {
  return [...own.map(([name, o = {}], i) => [t + 0.012 * i, name, { volume: 1.35 * volume, ...o }]), ...(hit > 0 ? [[t, "qf.scare.hit", { volume: hit * volume }]] : [])];
}
export function blow(t, { volume = 1, gore = true, hurt = true } = {}) {
  return [...(hurt ? [[t, "game.player.hurt"]] : []), [t + 0.005, "qf.scare.hit", { volume: 1.05 * volume }], [t + 0.02, gore ? "qf.scare.gore" : "qf.scare.crunch", { volume: 0.85 * volume }]];
}
// hits: [{ t, side }] (side: the way the head is thrown, +1 right). A fast knock (0.09 s), then it comes back.
export function kick(t, hits, { amp = 1 } = {}) {
  let yaw = 0, pitch = 0, back = 0;
  for (const h of hits) {
    const tt = h.t ?? h; if (t < tt) continue;
    const d = t - tt, e = Math.sin(clamp(d / 0.09) * Math.PI / 2) * Math.exp(-Math.max(0, d - 0.09) / 0.3), a = (h.amp ?? 1) * amp;
    yaw += 0.2 * a * (h.side ?? 1) * e; pitch -= 0.14 * a * e; back += 0.1 * a * e;
  }
  return { yaw, pitch, back };
}
export function impactSplit(f, t, times, { amt = 0.3, tau = 0.05 } = {}) {
  const v = amt * pulse(t, times, tau);
  if (v < 0.003) return f;
  const fx = f.fx || (f.fx = { tear: 0, split: 0, stat: 0 });
  fx.split = Math.max(fx.split, v);
  return f;
}
export function hop(a, b, k, h = 0) {
  const u = clamp(k);
  return { x: lerp(a.x, b.x, u), y: lerp(a.y ?? 0, b.y ?? 0, u) + h * 4 * u * (1 - u), z: lerp(a.z, b.z, u) };
}
const _f = new THREE.Vector3();
export function faceOf(m, box, out = new THREE.Vector3()) {
  const head = m.parts.head; if (!head || !box) return m.pivot.getWorldPosition(out);
  const [x, y, z, w, h] = box;
  m.pivot.updateMatrixWorld(true);
  return head.localToWorld(out.copy(_f.set(-(x + w / 2) / 16, -(y + h / 2) / 16, z / 16)));
}
