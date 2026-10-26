// Light events. Uses ctx.light (the Krypt's __krypt.light or the mood layer's own, see light.js).
import { at } from "./geo.js";

export function lightEvent(ctx, kind) {
  const L = ctx.light, fr = ctx.frame(), rng = ctx.rng;
  const speed = Math.max(3, Math.abs(ctx.kr.getWalk().speed || 0));
  if (kind === "light_sputter") {
    const p = at(fr, 10 + rng() * 6, (rng() - 0.5) * 3, 0);
    L.sputter(p, 2.4);
    return { dur: 2.6, update() { return false; }, stop() {} };
  }
  if (kind === "light_out") {
    const d = 13 + rng() * 5, p = at(fr, d, (rng() - 0.5) * 2, 0);
    const s = Math.min(26, d / speed + 7);       // out until a few seconds after you have passed it
    L.out(p, s);
    return { dur: Math.min(s, 12), update() { return false; }, stop() {} };
  }
  if (kind === "light_pulse") {
    L.pulse(1.5);
    ctx.play("qf.krypt.groan", { volume: 0.28, pitch: 0.7 });
    return { dur: 1.8, update() { return false; }, stop() {} };
  }
  // cascade: a run of flickers down the corridor toward you, torch by torch, that stops short
  const dur = 4.2, n = 6;
  if (L.real) {
    const sched = []; for (let i = 0; i < n; i++) sched.push([i * 0.5, at(fr, 30 - i * 4.2, 0, 0)]);
    let k = 0;
    return { dur, update(t) { while (k < sched.length && t >= sched[k][0]) { L.sputter(sched[k][1], 0.9); k++; } return false; }, stop() {} };
  }
  L.cascade(dur);
  return { dur, update() { return false; }, stop() {} };
}
