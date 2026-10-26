// Light effects for the mood layer. Uses window.__krypt.light (flicker, off, pulse, scale) when krypt-gen has landed it;
// until then (or with ?lightfx=own, and always in a dump, so a frame is deterministic) a small version of its own that
// scales the Krypt's whole baked light through krypt.js's bakeUniform. Every effect eases and ends restored.
import * as KR from "../krypt.js";

const sm = (x) => { x = Math.max(0, Math.min(1, x)); return x * x * (3 - 2 * x); };
// a tiny deterministic flicker noise
const nz = (t) => Math.sin(t * 41.3) * 0.5 + Math.sin(t * 23.7 + 1.3) * 0.3 + Math.sin(t * 67.1 + 2.9) * 0.2;

// Each own effect is a function of its age (s) giving a multiplier; it is over after dur.
const SHAPES = {
  // a torch ahead: stutters, nearly out, recovers (the whole scene feels a little of it)
  flicker(dur) { return { dur, f: (a) => { const k = Math.pow(Math.sin(Math.PI * Math.min(1, a / dur)), 0.6); const st = Math.sin(a * 37) + Math.sin(a * 22.3 + 1) > -0.2 ? 1 : 0.12; return 1 - 0.5 * k * (0.25 + 0.75 * st); } }; },
  // out as you near: a quick gutter, then a held dimness until the relight
  off(dur) { return { dur, f: (a) => { const g = sm(a / 0.45), r = sm((a - (dur - 1.4)) / 1.2); const w = (1 - 0.3 * g) + 0.3 * g * r; const gut = a < 0.7 ? 0.22 * (Math.sin(a * 45) > 0 ? 1 : 0) * Math.sin(Math.PI * a / 0.7) : 0; return w - gut; } }; },
  // everything dims once for a beat
  pulse(dur) { return { dur, f: (a) => { const d = sm(a / (dur * 0.22)), u = sm((a - dur * 0.45) / (dur * 0.55)); return 1 - 0.85 * d * (1 - u); } }; },
  // a cascade of flickers: each one deeper than the last, then it stops dead and the dark holds a second
  cascade(dur) { return { dur, f: (a) => {
    const n = 6, step = (dur - 1.8) / n;
    let v = 1;
    if (a < dur - 1.8) { const i = Math.floor(a / step), p = (a - i * step) / step; v -= (0.16 + 0.1 * i) * Math.sin(Math.PI * Math.min(1, p * 1.25)); }
    else { const q = (a - (dur - 1.8)) / 1.8; v -= 0.5 * (1 - sm(q)); }
    return v; } }; },
  scale(dur, k) { return { dur, f: (a) => { const e = Math.min(sm(a / 0.6), sm((dur - a) / 0.8)); return 1 + (k - 1) * e; } }; }
};

export function createLight(kr, { own = false } = {}) {
  const real = !own && kr.light && typeof kr.light.pulse === "function" ? kr.light : null;
  const fx = [];            // own effects: { shape, t0 }
  let clock = 0, base = null, touched = false;
  const L = {
    real: !!real,
    sputter(pos, s = 2.2) { if (real) real.flicker(pos, s); else fx.push({ ...SHAPES.flicker(s), t0: clock }); },
    out(pos, s = 14) { if (real) real.off(pos, s); else fx.push({ ...SHAPES.off(Math.min(s, 12)), t0: clock }); },
    pulse(s = 1.5) { if (real) real.pulse(s); else fx.push({ ...SHAPES.pulse(s), t0: clock }); },
    scale(k, s) { if (real) real.scale(k, s); else fx.push({ ...SHAPES.scale(s, k), t0: clock }); },
    cascade(dur = 4.2) { if (!real) fx.push({ ...SHAPES.cascade(dur), t0: clock }); },   // the real one is driven by the event, torch by torch
    // own effects only: advance the clock, set the bake gain. dt in seconds.
    update(dt) {
      clock += dt;
      for (let i = fx.length - 1; i >= 0; i--) if (clock - fx[i].t0 >= fx[i].dur) fx.splice(i, 1);
      if (!KR.bakeUniform) return;
      if (!fx.length) { if (touched) { KR.bakeUniform.value = base; touched = false; base = null; } return; }
      if (!touched) { base = KR.bakeUniform.value; touched = true; }
      let m = 1; for (const e of fx) m *= e.f(clock - e.t0);
      KR.bakeUniform.value = base * Math.pow(Math.max(0.04, m), 1.5);
    },
    busy() { return fx.length > 0; },
    clear() { fx.length = 0; L.update(0); }
  };
  return L;
}
