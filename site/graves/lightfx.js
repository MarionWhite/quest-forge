// The light effects of the contract (window.__krypt.light): scale, flicker, off, pulse. Every effect eases in and
// ends restored. The baked light of the walls cannot change per torch, so a dim sphere in the shaders (krypt.js
// patchBake / patchTorch) darkens the stone and the torch around the one that flickers or goes out; the flame
// particles and the live point light follow the same factor.
import * as THREE from "three";
import { lightScale, torchGain, dimU } from "./krypt.js";

const ease = (x) => { x = Math.min(1, Math.max(0, x)); return x * x * (3 - 2 * x); };

export function makeLightFx({ torches, hemi }) {
  const fx = [];            // { kind, t, dur, k, torch, seed }
  const now = () => performance.now() / 1000;
  const nearestTorch = (pos) => {
    const p = Array.isArray(pos) ? { x: pos[0], y: pos[1], z: pos[2] } : pos;
    let best = null, bd = 1e12;
    for (const t of torches()) { const d = (t.x - p.x) ** 2 + (t.y - p.y) ** 2 + (t.z - p.z) ** 2; if (d < bd) { bd = d; best = t; } }
    return best;
  };
  const api = {
    // Every light scaled by k for `seconds` (eased in over the first fifth, out over the last third), then restored.
    scale(k, seconds = 2) { fx.push({ kind: "scale", t0: now(), dur: Math.max(0.2, seconds), k }); },
    // The nearest torch to pos stutters for `seconds` and settles back. Returns true when there was a torch.
    flicker(pos, seconds = 2) { const t = nearestTorch(pos); if (!t) return false; fx.push({ kind: "flicker", t0: now(), dur: Math.max(0.2, seconds), torch: t, seed: Math.random() * 100 }); return true; },
    // The nearest torch to pos is snuffed, and relights after `seconds`.
    off(pos, seconds = 4) { const t = nearestTorch(pos); if (!t) return false; fx.push({ kind: "off", t0: now(), dur: Math.max(0.4, seconds), torch: t }); return true; },
    // All the lights dim once, quickly, and come back slowly.
    pulse(seconds = 1.6) { fx.push({ kind: "pulse", t0: now(), dur: Math.max(0.3, seconds) }); },
    active() { return fx.length; }
  };
  let dims = [];            // the torches under a dim sphere this frame: { t, amt }
  let S = 1;
  api.update = (dtUnused, extraScale = 1) => {
    const t = now();
    S = 1; dims = [];
    for (let i = fx.length - 1; i >= 0; i--) {
      const e = fx[i], u = (t - e.t0) / e.dur;
      if (u >= 1) { fx.splice(i, 1); continue; }
      if (e.kind === "scale") {
        const w = u < 0.2 ? ease(u / 0.2) : u > 0.67 ? 1 - ease((u - 0.67) / 0.33) : 1;
        S *= 1 + (e.k - 1) * w;
      } else if (e.kind === "pulse") {
        const w = u < 0.12 ? ease(u / 0.12) : 1 - ease((u - 0.12) / 0.88);
        S *= 1 - 0.78 * w;
      } else if (e.kind === "off") {
        const w = u < 0.08 ? ease(u / 0.08) : u > 0.9 ? 1 - ease((u - 0.9) / 0.1) : 1;
        // a stutter on the way back
        const st = u > 0.84 && u < 0.97 ? (Math.sin(t * 38 + e.torch.x) > 0.2 ? 0.55 : 0) : 0;
        dims.push({ t: e.torch, amt: Math.max(w, st) * 0.95 });
      } else if (e.kind === "flicker") {
        const env = u < 0.1 ? u / 0.1 : u > 0.85 ? (1 - u) / 0.15 : 1;
        const n = 0.5 + 0.5 * Math.sin(t * 31 + e.seed) * Math.sin(t * 17.3 + e.seed * 2.1);
        dims.push({ t: e.torch, amt: Math.min(0.9, Math.max(0, n * 1.25 - 0.1)) * env });
      }
    }
    S *= extraScale;
    lightScale.value = S;
    torchGain.value = Math.max(0.25, Math.min(1.4, S));
    for (let i = 0; i < 4; i++) {
      const d = dims[i];
      if (d) { dimU.P.value[i].set(d.t.x, d.t.y, d.t.z, 7.5); dimU.A.value[i] = d.amt; } else { dimU.P.value[i].set(0, -999, 0, 1); dimU.A.value[i] = 0; }
    }
    if (hemi) hemi.userData.lightScale = S;
  };
  // Multiplier for a live light or a flame at (x, y, z): the global scale and any dim sphere over it.
  api.factor = (x, y, z) => {
    let f = Math.min(1.4, S);
    for (const d of dims) {
      const dd = Math.hypot(x - d.t.x, y - d.t.y, z - d.t.z);
      if (dd < 1.5) f *= 1 - d.amt;
    }
    return f;
  };
  api.scaleNow = () => S;
  return api;
}
