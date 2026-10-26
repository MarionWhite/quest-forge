// The Krypt's sound: wind and music under everything, cave noises and groans far off, drips by the water, fire and
// lava near the torches and the seams, footsteps that walk the side passages and fade, and your own steps on the
// floor of the segment you are in. Everything spatial goes through the engine's HRTF panner; the stone room is a
// long reverb. Browsers need a click first, so start() is called from the entry gate.
import { audio } from "../lib/qfaudio.js";

const LOG = new URLSearchParams(location.search).has("sfxlog");
export const sfxLog = [];
function snd(kind, name, o) {
  if (LOG) { sfxLog.push(name); console.info("sfx", name); }
  return kind === "loop" ? audio.loop(name, o) : audio.play(name, o);
}
const rnd = (a, b) => a + Math.random() * (b - a);

export function makeAmbience({ a, lay }) {
  let on = false, t = 0;
  const next = { cave: rnd(8, 20), groan: rnd(45, 90), zombie: rnd(80, 150), steps: rnd(18, 40), drip: 1 };
  const loops = new Map();         // key -> { h, pos }
  let dist = 0, lastP = null, own = 0;

  function ringPos(cam, dmin, dmax) {
    const ang = Math.random() * Math.PI * 2, d = rnd(dmin, dmax);
    return { x: cam.x + Math.cos(ang) * d, y: cam.y + rnd(-0.5, 1), z: cam.z + Math.sin(ang) * d };
  }
  function nearest(list, cam, maxD) {
    let best = null, bd = maxD * maxD;
    for (const p of list) { const d = (p[0] - cam.x) ** 2 + (p[2] - cam.z) ** 2 + (p[1] - cam.y) ** 2; if (d < bd) { bd = d; best = p; } }
    return best;
  }
  function keepLoop(key, name, list, cam, maxD, o) {
    const p = nearest(list, cam, maxD);
    const cur = loops.get(key);
    if (!p) { if (cur) { cur.h.stop(1.2); loops.delete(key); } return; }
    const pos = { x: p[0], y: p[1], z: p[2] };
    if (cur) { cur.h.setPos(pos); return; }
    loops.set(key, { h: snd("loop", name, { pos, ...o }) });
  }

  let torchSpots = [], torchVer = -1;
  const torchList = () => { if (torchVer !== a.version) { torchVer = a.version; torchSpots = a.torches.map(q => [q.x, q.y, q.z]); } return torchSpots; };

  return {
    start() {
      if (on) return; on = true;
      audio.setReverb({ seconds: 3.6, decay: 2.3, wet: 0.3 });
      audio.music("music.krypt", { fade: 6 });
      snd("loop", "qf.krypt.wind", { volume: 0.55, fadeIn: 4 });
    },
    stop() { on = false; for (const l of loops.values()) l.h.stop(0.5); loops.clear(); audio.music(null, { fade: 1 }); },
    gate() { snd("play", "qf.krypt.gate", { volume: 1 }); },
    // Called every frame: dt seconds, the camera, the walk (s, speed), the leg kind and whether the walk is held.
    tick(dt, cam, walk, kind, held) {
      if (!on) return;
      t += dt;
      for (const k of Object.keys(next)) next[k] -= dt;
      if (next.cave < 0) { next.cave = rnd(20, 60); snd("play", "ambient.cave.cave", { pos: ringPos(cam, 12, 30), volume: 0.75, reverb: 0.5 }); }
      if (next.groan < 0) { next.groan = rnd(60, 140); snd("play", "qf.krypt.groan", { pos: ringPos(cam, 22, 36), volume: 0.55, reverb: 0.8, max: 60 }); }
      if (next.zombie < 0) { next.zombie = rnd(90, 190); snd("play", "mob.zombie.say", { pos: ringPos(cam, 28, 42), volume: 0.4, pitch: rnd(0.65, 0.85), reverb: 0.9, max: 70 }); }
      // Distant footsteps: someone walks a side passage toward the corridor and the sound thins out.
      if (next.steps < 0) {
        next.steps = rnd(35, 80);
        const ps = a.passages.filter(p => { const d = Math.hypot(p.mouth[0] - cam.x, p.mouth[2] - cam.z); return d > 9 && d < 46; });
        if (ps.length) {
          const p = ps[Math.floor(Math.random() * ps.length)];
          const n = 9, gap = rnd(0.58, 0.72), nm = kind === "mine" || kind === "crypt" || kind === "spidermine" || kind === "catacomb" ? "step.gravel" : "step.stone";
          for (let i = 0; i < n; i++) {
            const f = i / (n - 1);
            const pos = { x: p.end[0] + (p.mouth[0] - p.end[0]) * f + p.dir[0] * f * 1.5, y: p.end[1] + 1.2, z: p.end[2] + (p.mouth[2] - p.end[2]) * f + p.dir[1] * f * 1.5 };
            // Louder as they come, then gone: the last steps are the ones that turn the corner.
            const v = 0.16 + 0.5 * Math.sin(Math.PI * Math.min(1, f * 0.9 + 0.05)) * (1 - f * 0.4);
            snd("play", nm, { pos, volume: v, pitch: rnd(0.62, 0.8), reverb: 0.55, delay: i * gap, ref: 1.5, max: 34 });
          }
        }
      }
      // Water: drips near the flooded hall and anywhere with a drip emitter.
      if (next.drip < 0) {
        next.drip = rnd(0.9, 3.2);
        const p = nearest(a.spots.drip, cam, 16);
        if (p) snd("play", "qf.krypt.drip", { pos: { x: p[0], y: p[1], z: p[2] }, volume: 0.5, reverb: 0.6, ref: 1.5, max: 22 });
      }
      keepLoop("fire", "fire.fire", torchList().concat(a.spots.fire), cam, 9, { volume: 0.07, ref: 1.2, max: 12 });
      keepLoop("lava", "liquid.lava", a.spots.lava, cam, 20, { volume: 0.16, ref: 3, max: 26 });
      // Your steps, tied to how fast you walk. A held walk (a scare) is silent.
      if (held) { lastP = null; return; }
      if (lastP) dist += Math.hypot(cam.x - lastP.x, cam.z - lastP.z);
      lastP = { x: cam.x, z: cam.z };
      const stride = 1.7;
      if (dist > stride) {
        dist = 0;
        if (Math.abs(walk.speed) > 0.25) {
          const nm = (kind === "mine" || kind === "crypt" || kind === "spidermine" || kind === "catacomb") && Math.random() < 0.6 ? "step.gravel" : "step.stone";
          snd("play", nm, { volume: Math.min(0.5, 0.18 + Math.abs(walk.speed) * 0.03), pitch: rnd(0.85, 1.05), reverb: 0.25 });
          own++;
        }
      }
    }
  };
}
