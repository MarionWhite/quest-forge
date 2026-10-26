// Sound-only events: distant echoes, scampering behind the wall, breath and scrape close by.
// Each factory returns { dur, update(t, dt), stop() }. Sounds come from the pre-rendered qf.mood.* set when the audio
// task has landed it; until then the bank's own mob sounds are used, pitched down, far off, with runtime reverb and echoes.
import { at, farPoint } from "./geo.js";

const FAR = {
  far_groan:  { real: "qf.mood.far_groan",  bank: "mob.zombie.say",     pitch: [0.62, 0.74] },
  far_rattle: { real: "qf.mood.far_rattle", bank: "mob.skeleton.say",   pitch: [0.6, 0.72] },
  far_vwoop:  { real: "qf.mood.far_vwoop",  bank: "mob.endermen.portal", pitch: [0.55, 0.68] },
  far_cry:    { real: "qf.mood.far_cry",    bank: "mob.ghast.moan",     pitch: [0.7, 0.85] },
  far_hiss:   { real: "qf.mood.far_hiss",   bank: "mob.spider.say",     pitch: [0.6, 0.75] }
};
const lerp = (a, b, t) => a + (b - a) * t;

export function farEvent(ctx, kind) {
  const spec = FAR[kind], fr = ctx.frame();
  const pos = farPoint(ctx.kr, fr, ctx.rng);
  if (ctx.has(spec.real)) {
    ctx.play(spec.real, { pos, volume: 0.9, ref: 8, max: 400, rolloff: 0.35, reverb: 0.6 });
  } else {
    // the bank sound, low and far, with two echoes that arrive later and fainter, each from a slightly different place
    const p = spec.pitch[0] + ctx.rng() * (spec.pitch[1] - spec.pitch[0]);
    ctx.play(spec.bank, { pos, volume: 1.0, pitch: p, ref: 8, max: 400, rolloff: 0.5, reverb: 1 });
    const side = fr.right.clone().multiplyScalar((ctx.rng() - 0.5) * 6);
    ctx.play(spec.bank, { pos: pos.clone().add(side), volume: 0.42, pitch: p * 0.96, ref: 8, max: 400, rolloff: 0.5, reverb: 1, delay: 0.55 });
    ctx.play(spec.bank, { pos: pos.clone().sub(side), volume: 0.2, pitch: p * 0.92, ref: 8, max: 400, rolloff: 0.5, reverb: 1, delay: 1.25 });
  }
  return { dur: 5.5, update() { return false; }, stop() {} };
}

// Something small and fast on the far side of the wall: front-left to right, close. With `stop` it halts right beside you.
export function scamperEvent(ctx, stop) {
  const fr = ctx.frame(), rng = ctx.rng;
  const dir = rng() < 0.7 ? 1 : -1;                       // mostly left to right
  const a = at(fr, 8, -4.5 * dir, -1.2), b = stop ? at(fr, 0.6, 2.35 * dir, -1.2) : at(fr, 2.5, 4.5 * dir, -1.2);
  const run = stop ? 1.35 : 1.15;
  let h = null, steps = 0;
  const pos = a.clone();
  const real = ctx.has("qf.mood.scamper");
  if (real) h = ctx.play("qf.mood.scamper", { pos: a, volume: 0.85, ref: 3, max: 60, rolloff: 1 });
  return {
    dur: run + (stop ? 3.2 : 0.4),
    update(t) {
      const k = Math.min(1, t / run);
      pos.lerpVectors(a, b, k * k * (3 - 2 * k) * 0.35 + k * 0.65);
      if (h) h.setPos(pos);
      if (!real && t < run) {
        // claws on stone: a pair of ticks every ~70 ms, quick and uneven
        const want = Math.floor(t / 0.068);
        while (steps < want) {
          steps++;
          ctx.play(steps % 3 ? "step.stone" : "mob.spider.step", { pos: pos.clone(), volume: 0.2 + rng() * 0.12, pitch: 1.55 + rng() * 0.6, ref: 2.5, max: 60 });
        }
      }
      if (stop && t > run + 1.8 && !this.scraped) { this.scraped = true; ctx.play(ctx.has("qf.mood.scrape") ? "qf.mood.scrape" : "dig.stone", { pos: b.clone(), volume: 0.35, pitch: 0.55, ref: 1.5, max: 30, reverb: 0.4 }); }
      return false;
    },
    stop() { if (h) h.stop(0.3); }
  };
}

// Breathing right behind your head, close enough to feel it. Never repeated at the same place twice.
export function breathEvent(ctx) {
  const fr = ctx.frame();
  const pos = at(fr, -0.75, (ctx.rng() - 0.5) * 0.5, -0.12);
  const name = ctx.has("qf.mood.breath_near") ? "qf.mood.breath_near" : "qf.scare.breath";
  const h = ctx.play(name, { pos, volume: name === "qf.mood.breath_near" ? 0.8 : 0.5, pitch: name === "qf.mood.breath_near" ? 1 : 0.78, ref: 0.6, max: 12, rolloff: 1.4, reverb: 0.25 });
  return { dur: 4.5, update() { return false; }, stop() { if (h) h.stop(0.4); } };
}

// A scrape along the wall beside you, from behind to ahead, a little slower than a walk.
export function scrapeEvent(ctx) {
  const fr = ctx.frame(), side = ctx.rng() < 0.5 ? -1 : 1;
  const a = at(fr, -4, 1.7 * side, -0.9), b = at(fr, 3.5, 1.7 * side, -0.9), pos = a.clone();
  const real = ctx.has("qf.mood.scrape");
  const h = real ? ctx.play("qf.mood.scrape", { pos: a, volume: 0.9, ref: 1.5, max: 30, rolloff: 1.2, reverb: 0.2 }) : null;
  let n = 0;
  return {
    dur: 2.6,
    update(t) {
      pos.lerpVectors(a, b, Math.min(1, t / 2.3));
      if (h) h.setPos(pos);
      if (!real) { const want = Math.floor(t / 0.33); while (n < want && t < 2.2) { n++; ctx.play("dig.stone", { pos: pos.clone(), volume: 0.5, pitch: 0.42 + ctx.rng() * 0.1, ref: 1.5, max: 30, reverb: 0.3 }); } }
      return false;
    },
    stop() { if (h) h.stop(0.3); }
  };
}
