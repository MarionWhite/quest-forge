// qfaudio: the site's one sound engine (Lucky Block, the Krypt, anything later).
//
//   import { audio } from '../lib/qfaudio.js';
//   audio.play('random.explode', { pos: {x, y, z} });      // one-shot, optionally spatial
//   const h = audio.loop('ambient.cave.cave', { pos });     // looping; h.stop(0.5), h.setPos(p)
//   audio.music('music.krypt', { fade: 3 });                // crossfade; audio.music(null) stops
//   audio.updateListener(camera);                           // once per frame, after the camera moves
//   audio.setReverb({ seconds: 3.2, wet: 0.35 });           // a room for every sound with { reverb }
//   audio.setMuted(true);                                   // persisted in localStorage 'qf-sound'
//
// Event names follow Minecraft 1.7.10's sounds.json ('mob.ghast.moan', 'random.anvil_land',
// 'dig.stone', 'step.stone', 'ambient.cave.cave', 'game.player.hurt', ...). OreSpawn's are
// 'orespawn:<name>'. The site's own are 'qf.*' (qf.case_slam, qf.reveal.jackpot, ...) and the
// music cues 'music.*'. Every name resolves through sfx/manifest.json:
//
//   { "events": { "<name>": { "files": ["mob/ghast/moan1.m4a", ...], "volume": 1,
//                             "pitch": 1 | [lo, hi], "bus": "sfx|music|ambient|ui",
//                             "loopStart": s, "loopEnd": s } } }
//
// A name that is not in the manifest plays nothing and warns once, so a page never breaks on a
// missing sound. Nothing is fetched until a sound is first asked for (or preload() is called),
// and no AudioContext exists until the first user gesture: browsers refuse sound before one.

const BASE = new URL('./sfx/', import.meta.url);
const MANIFEST_URL = new URL('manifest.json', BASE).href;
const BUSES = ['sfx', 'music', 'ambient', 'ui'];
const BUS_GAIN = { sfx: 0.9, music: 0.45, ambient: 0.7, ui: 0.7 };

let ctx = null;
let master = null;
const bus = {};
let reverbIn = null;
let reverbWet = null;
let manifest = null;
let manifestP = null;
const buffers = new Map();   // file -> Promise<AudioBuffer|null>
const warned = new Set();
const pending = [];          // plays requested before the context could start
let musicNow = null;
let muted = false;
try { muted = localStorage.getItem('qf-sound') === 'off'; } catch (e) { /* storage blocked */ }
const listeners = new Set();

function loadManifest() {
  if (!manifestP) {
    manifestP = fetch(MANIFEST_URL).then((r) => (r.ok ? r.json() : { events: {} }))
      .catch(() => ({ events: {} }))
      .then((m) => { manifest = m && m.events ? m : { events: {} }; return manifest; });
  }
  return manifestP;
}

function makeContext() {
  if (ctx) return ctx;
  const AC = window.AudioContext || window.webkitAudioContext;
  if (!AC) return null;
  ctx = new AC({ latencyHint: 'interactive' });
  const comp = ctx.createDynamicsCompressor();
  comp.threshold.value = -10; comp.knee.value = 12; comp.ratio.value = 4;
  comp.attack.value = 0.004; comp.release.value = 0.2;
  master = ctx.createGain();
  master.gain.value = muted ? 0 : 1;
  master.connect(comp); comp.connect(ctx.destination);
  for (const b of BUSES) { bus[b] = ctx.createGain(); bus[b].gain.value = BUS_GAIN[b]; bus[b].connect(master); }
  reverbWet = ctx.createGain(); reverbWet.gain.value = 0;
  reverbIn = ctx.createConvolver();
  reverbIn.buffer = impulse(2.4, 2.2);
  reverbIn.connect(reverbWet); reverbWet.connect(master);
  return ctx;
}

// A synthetic room: decaying stereo noise. Cheap, and good enough for stone.
function impulse(seconds, decay) {
  const n = Math.max(1, Math.floor(ctx.sampleRate * seconds));
  const b = ctx.createBuffer(2, n, ctx.sampleRate);
  for (let c = 0; c < 2; c++) {
    const d = b.getChannelData(c);
    for (let i = 0; i < n; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / n, decay);
  }
  return b;
}

function unlock() {
  if (!makeContext()) return;
  if (ctx.state === 'suspended') ctx.resume().catch(() => {});
  loadManifest();
  while (pending.length) { const [n, o] = pending.shift(); play(n, o); }
}
['pointerdown', 'keydown', 'touchend', 'click'].forEach((ev) => addEventListener(ev, unlock, { capture: true, passive: true }));

function decode(file) {
  if (!buffers.has(file)) {
    const url = new URL(file, BASE).href;
    buffers.set(file, fetch(url).then((r) => (r.ok ? r.arrayBuffer() : null))
      .then((ab) => (ab ? new Promise((res) => ctx.decodeAudioData(ab, res, () => res(null))) : null))
      .catch(() => null));
  }
  return buffers.get(file);
}

function pick(v) { return Array.isArray(v) ? v[0] + Math.random() * (v[1] - v[0]) : (v ?? 1); }

function spatial(node, pos, o) {
  const p = ctx.createPanner();
  p.panningModel = 'HRTF';
  p.distanceModel = 'inverse';
  p.refDistance = o.ref ?? 2;
  p.maxDistance = o.max ?? 48;
  p.rolloffFactor = o.rolloff ?? 1;
  setPannerPos(p, pos);
  node.connect(p);
  return p;
}
function setPannerPos(p, v) {
  if (p.positionX) { p.positionX.value = v.x; p.positionY.value = v.y; p.positionZ.value = v.z; } else p.setPosition(v.x, v.y, v.z);
}

// play(name, { pos, volume, pitch, loop, reverb (0..1), delay (s), ref, max, rolloff, bus })
export function play(name, o = {}) {
  if (!ctx || ctx.state === 'closed') { if (pending.length < 8) pending.push([name, o]); return nullHandle(); }
  const h = { stopped: false, src: null, gain: null, panner: null,
    stop(fade = 0.05) { this.stopped = true; if (!this.gain) return; const t = ctx.currentTime; this.gain.gain.cancelScheduledValues(t); this.gain.gain.setValueAtTime(this.gain.gain.value, t); this.gain.gain.linearRampToValueAtTime(0, t + fade); try { this.src.stop(t + fade + 0.02); } catch (e) { /* not started */ } },
    setPos(v) { if (this.panner) setPannerPos(this.panner, v); },
  };
  loadManifest().then((m) => {
    const ev = m.events[name];
    if (!ev || !ev.files || !ev.files.length) { if (!warned.has(name)) { warned.add(name); console.warn('qfaudio: no sound for', name); } return; }
    const file = ev.files[Math.floor(Math.random() * ev.files.length)];
    return decode(file).then((buf) => {
      if (!buf || h.stopped) return;
      const src = ctx.createBufferSource();
      src.buffer = buf;
      src.playbackRate.value = pick(o.pitch ?? ev.pitch ?? 1);
      if (o.loop || ev.loop) { src.loop = true; if (ev.loopStart != null) src.loopStart = ev.loopStart; if (ev.loopEnd != null) src.loopEnd = ev.loopEnd; }
      const g = ctx.createGain();
      const vol = (o.volume ?? 1) * (ev.volume ?? 1);
      g.gain.value = o.fadeIn ? 0 : vol;
      if (o.fadeIn) g.gain.linearRampToValueAtTime(vol, ctx.currentTime + o.fadeIn);
      src.connect(g);
      const out = o.pos ? spatial(g, o.pos, o) : g;
      out.connect(bus[o.bus || ev.bus || 'sfx'] || bus.sfx);
      if (o.reverb) { const s = ctx.createGain(); s.gain.value = o.reverb; out.connect(s); s.connect(reverbIn); }
      h.src = src; h.gain = g; h.panner = o.pos ? out : null;
      src.start(ctx.currentTime + (o.delay || 0));
      src.onended = () => { h.stopped = true; };
    });
  });
  return h;
}
function nullHandle() { return { stopped: true, stop() {}, setPos() {} }; }

export function loop(name, o = {}) { return play(name, { ...o, loop: true }); }

// music(name | null, { fade, volume }): one track at a time, crossfaded
export function music(name, o = {}) {
  const fade = o.fade ?? 2;
  if (musicNow && musicNow.name === name) return musicNow.h;
  if (musicNow) { musicNow.h.stop(fade); musicNow = null; }
  if (!name) return null;
  const h = play(name, { loop: true, bus: 'music', volume: o.volume ?? 1, fadeIn: fade });
  musicNow = { name, h };
  return h;
}

// Call once per frame with a THREE camera (or anything with matrixWorld).
const _v = { x: 0, y: 0, z: 0 };
export function updateListener(cam) {
  if (!ctx || !cam || !cam.matrixWorld) return;
  const e = cam.matrixWorld.elements;
  const L = ctx.listener;
  const px = e[12], py = e[13], pz = e[14];
  const fx = -e[8], fy = -e[9], fz = -e[10];   // camera looks down -Z
  const ux = e[4], uy = e[5], uz = e[6];
  if (L.positionX) {
    const t = ctx.currentTime;
    L.positionX.setTargetAtTime(px, t, 0.02); L.positionY.setTargetAtTime(py, t, 0.02); L.positionZ.setTargetAtTime(pz, t, 0.02);
    L.forwardX.setTargetAtTime(fx, t, 0.02); L.forwardY.setTargetAtTime(fy, t, 0.02); L.forwardZ.setTargetAtTime(fz, t, 0.02);
    L.upX.setTargetAtTime(ux, t, 0.02); L.upY.setTargetAtTime(uy, t, 0.02); L.upZ.setTargetAtTime(uz, t, 0.02);
  } else {
    L.setPosition(px, py, pz);
    L.setOrientation(fx, fy, fz, ux, uy, uz);
  }
  _v.x = px; _v.y = py; _v.z = pz;
}

export function setReverb({ seconds = 2.4, decay = 2.2, wet = 0.3 } = {}) {
  if (!makeContext()) return;
  reverbIn.buffer = impulse(seconds, decay);
  reverbWet.gain.setTargetAtTime(wet, ctx.currentTime, 0.1);
}

// Duck everything but one bus for a moment (a jump scare, a jackpot): duck('sfx', 0.3, 1.5)
export function duck(keep = 'sfx', to = 0.25, seconds = 1.2) {
  if (!ctx) return;
  const t = ctx.currentTime;
  for (const b of BUSES) {
    if (b === keep) continue;
    const g = bus[b].gain;
    g.cancelScheduledValues(t); g.setValueAtTime(g.value, t);
    g.linearRampToValueAtTime(BUS_GAIN[b] * to, t + 0.06);
    g.linearRampToValueAtTime(BUS_GAIN[b], t + seconds);
  }
}

// Muffle the whole mix (ears ringing after an explosion): muffle(400, 2.5)
let muffleNode = null;
export function muffle(hz = 500, seconds = 2) {
  if (!ctx) return;
  if (!muffleNode) {
    muffleNode = ctx.createBiquadFilter(); muffleNode.type = 'lowpass'; muffleNode.frequency.value = 20000;
    master.disconnect(); master.connect(muffleNode);
    const comp = ctx.createDynamicsCompressor(); muffleNode.connect(comp); comp.connect(ctx.destination);
  }
  const f = muffleNode.frequency, t = ctx.currentTime;
  f.cancelScheduledValues(t); f.setValueAtTime(hz, t); f.exponentialRampToValueAtTime(20000, t + seconds);
}

export function preload(names) {
  if (!makeContext()) return Promise.resolve();
  return loadManifest().then((m) => Promise.all(names.flatMap((n) => (m.events[n] ? m.events[n].files : [])).map(decode)));
}

export function setMuted(v) {
  muted = !!v;
  try { if (muted) localStorage.setItem('qf-sound', 'off'); else localStorage.removeItem('qf-sound'); } catch (e) { /* storage blocked */ }
  if (master) master.gain.setTargetAtTime(muted ? 0 : 1, ctx.currentTime, 0.05);
  listeners.forEach((f) => f(muted));
}
export function isMuted() { return muted; }
export function onMute(f) { listeners.add(f); return () => listeners.delete(f); }
export function context() { return ctx; }   // for synthesized sounds (oscillators) on the same graph
export function busNode(name = 'sfx') { return bus[name] || null; }
export function has(name) { return !!(manifest && manifest.events[name]); }
export function ready() { return loadManifest(); }

export const audio = { play, loop, music, updateListener, setReverb, duck, muffle, preload, setMuted, isMuted, onMute, context, busNode, has, ready, unlock };
export default audio;
