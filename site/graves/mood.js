// The Krypt's ambient dread layer: distant echoes, scampering behind the wall, the light doing odd things, mobs
// glimpsed round corners, and (deeper down) breath at your neck. Rare, unexplained, never a clean look.
// Spec: docs/design/site/krypt-mood.md.   Modules: mood/director.js (timing), geo.js, light.js, events-*.js.
//   initMood({ enabled, reduced })   from the marked block in app.js (krypt-gen adds it)
//   window.__mood                    { busy, kinds, trigger(kind), director, ... }; the scares check .busy, and this layer
//                                    checks window.__scares / the scare's own overlay and never overlaps one
//   Shift+M                          a small test list; a click fires an event where you stand
//   ?mood=off                        the layer is off
//   ?mood=<kind>&moodat=<ms>&dump=1  render that moment of one event into #dumpshot (tools/site/dump_frames.py)
//   ?lightfx=own                     use the layer's own light effects even when __krypt.light exists
import * as THREE from "three";
import { audio } from "../lib/qfaudio.js";
import { createMoodDirector, KINDS } from "./mood/director.js";
import { createLight } from "./mood/light.js";
import { farEvent, scamperEvent, breathEvent, scrapeEvent } from "./mood/events-sound.js";
import { lightEvent } from "./mood/events-light.js";
import { peekEvent, stillEvent, eyesEvent } from "./mood/events-visual.js";
import { frameOf, clear, findPeek, findHidden, findEyesSpot } from "./mood/geo.js";

const QS = new URLSearchParams(location.search);
const MODE = QS.get("mood");
const DUMP = QS.has("dump");

const mood = window.__mood = { busy: false, kinds: Object.keys(KINDS), list: KINDS, current: null, on: MODE !== "off", director: null, log: [],
  trigger: () => false };

function mulberry(a) { return () => { a |= 0; a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
const kryptOf = () => { const k = window.__krypt; return k && k.scene && k.camera && k.composer ? k : null; };
const scareActive = () => {
  const s = window.__scares;
  if (s && (s.busy || s.running || s.active)) return true;
  return !!document.querySelector('#stage [role="alert"]');
};
const NULL_HANDLE = { stopped: true, stop() {}, setPos() {} };

function makeCtx(kr, { dump = false, seed = 1, own = false } = {}) {
  const rng = mulberry(seed);
  const ctx = {
    kr, THREE, rng, dump, scene: kr.scene, sfx: [], now: 0,
    frame: () => frameOf(kr),
    has: (n) => { try { return audio.has(n); } catch (e) { return false; } },
    play(name, o = {}) {
      ctx.sfx.push([+ctx.now.toFixed(2), name, o.pos ? o.pos.toArray().map((v) => +v.toFixed(1)) : null, o.volume ?? null, o.pitch ?? null]);
      if (dump) return NULL_HANDLE;
      const c = audio.context();
      if (!c || c.state !== "running") return NULL_HANDLE;     // before the first gesture: never queue a sound for later
      try { return audio.play(name, o); } catch (e) { return NULL_HANDLE; }
    },
    light: createLight(kr, { own: own || dump || QS.get("lightfx") === "own" })
  };
  return ctx;
}

// kind -> event (or null when the place has no spot for it)
function build(ctx, kind) {
  const v = KINDS[kind];
  if (!v) return null;
  if (kind.startsWith("far_")) return farEvent(ctx, kind);
  if (kind === "scamper") return scamperEvent(ctx, false);
  if (kind === "scamper_stop") return scamperEvent(ctx, true);
  if (kind === "breath") return breathEvent(ctx);
  if (kind === "scrape") return scrapeEvent(ctx);
  if (v.light) return lightEvent(ctx, kind);
  if (kind.startsWith("peek_")) return peekEvent(ctx, kind);
  if (kind === "eyes_spider") return eyesEvent(ctx);
  if (kind === "still_creeper") return stillEvent(ctx);
  return null;
}

// ---- the live loop -------------------------------------------------------------------------------------------------
let ctx = null, cur = null, picker = null, hud = null;

function endEvent(why) {
  if (!cur) return;
  try { cur.ev.stop(); } catch (e) { /* ignore */ }
  mood.log.push([+cur.t.toFixed(1), cur.kind, why]);
  if (mood.log.length > 60) mood.log.shift();
  cur = null; mood.busy = false; mood.current = null;
}
function start(kind) {
  if (cur) return false;
  let ev = null;
  try { ev = build(ctx, kind); } catch (e) { console.warn("mood", kind, e); }
  if (!ev) return false;
  cur = { kind, ev, t: 0 };
  mood.busy = true; mood.current = kind;
  return true;
}
mood.trigger = (kind) => {
  if (!ctx) return false;
  if (cur) endEvent("replaced");
  return start(kind);
};

export function initMood(opts = {}) {
  if (!mood.on) return;
  const enabled = opts.enabled || (() => true);
  const reducedNow = () => (typeof opts.reduced === "function" ? !!opts.reduced() : matchMedia("(prefers-reduced-motion: reduce)").matches || QS.has("flat"));
  const forced = MODE && MODE !== "off" && KINDS[MODE] ? MODE : null;
  if (forced && DUMP) { dumpMode(forced, Number(QS.get("moodat") ?? 0) || 0).catch((e) => console.error("mood dump", e)); return; }
  const boot = () => {
    const kr = kryptOf(); if (!kr) return;
    ctx = makeCtx(kr, { seed: (Math.random() * 1e9) | 0 });
    mood.director = createMoodDirector({ rng: Math.random, reduced: reducedNow() });
    try { audio.ready(); } catch (e) { /* ignore */ }
    addEventListener("keydown", pickerKey, true);
    loop();
    if (forced) setTimeout(() => mood.trigger(forced), 1500);
  };
  if (kryptOf()) boot(); else addEventListener("krypt-ready", boot, { once: true });

  let last = performance.now(), lastAcc = null, acc = 0, wasScare = false, tickAt = 0, memo = null;
  function loop() {
    requestAnimationFrame(loop);
    const now = performance.now(), dt = Math.min(0.1, (now - last) / 1000); last = now;
    const kr = kryptOf(); if (!kr) return;
    ctx.now += dt;
    ctx.light.update(dt);
    const sc = scareActive();
    if (sc) { if (cur) endEvent("scare"); ctx.light.clear(); wasScare = true; return; }
    if (wasScare) { wasScare = false; mood.director.scared(acc); }
    if (cur) {
      cur.t += dt;
      let done = false;
      try { done = cur.ev.update(cur.t, dt) || cur.t >= cur.ev.dur; } catch (e) { console.warn("mood update", e); done = true; }
      if (done) endEvent("done");
      return;
    }
    if (document.hidden || !enabled() || picker) return;
    const w = kr.getWalk();
    if (lastAcc == null) lastAcc = w.activeSeconds;
    acc += Math.max(0, Math.min(1, w.activeSeconds - lastAcc)); lastAcc = w.activeSeconds;
    if (now - tickAt < 250) return;
    tickAt = now;
    const depth = w.depth ?? w.s ?? 0;
    memo = {};
    const kind = mood.director.tick(acc, depth, {
      busy: false,
      feasible: (k) => {
        const v = KINDS[k];
        if (!v.visual) return true;
        const key = k.startsWith("peek_") ? "peek" : k;
        if (memo[key] === undefined) {
          const fr = frameOf(kr);
          memo[key] = key === "peek" ? !!findPeek(kr, fr, Math.random) : key === "eyes_spider" ? !!findEyesSpot(kr, fr, Math.random) : !!findHidden(kr, fr, Math.random, 12, 28);
        }
        return memo[key];
      }
    });
    if (kind && !start(kind)) mood.director.next = acc + 4;
  }
}

// ---- the test list (Shift+M) -------------------------------------------------------------------------------------
const PCSS = `.qfm-pick{position:fixed;right:14px;bottom:14px;z-index:100000;min-width:300px;background:rgba(16,16,16,.92);border:2px solid #000;outline:2px solid #555;
 font:13px/1.25 "JetBrains Mono",ui-monospace,Menlo,monospace;color:#e0e0e0;padding:8px 6px 6px;box-shadow:0 6px 24px rgba(0,0,0,.6)}
.qfm-pick h3{margin:0 4px 6px;font:inherit;color:#ff8a55;letter-spacing:.04em}.qfm-pick h3 span{color:#aaa}
.qfm-pick ol{list-style:none;margin:0;padding:0;max-height:min(60vh,440px);overflow:auto}
.qfm-pick button{display:grid;grid-template-columns:1fr auto;gap:6px;width:100%;text-align:left;font:inherit;color:#e0e0e0;background:transparent;border:0;padding:3px 6px;cursor:pointer}
.qfm-pick button:hover,.qfm-pick button:focus-visible{background:#2f2f50;color:#ffffa0;outline:0}
.qfm-pick .e{color:#888;font-size:11px}.qfm-pick p{margin:6px 4px 0;color:#888;font-size:11px;min-height:1.2em}`;
function openPicker() {
  if (picker || !ctx) return;
  if (!document.getElementById("qfm-pcss")) { const s = document.createElement("style"); s.id = "qfm-pcss"; s.textContent = PCSS; document.head.appendChild(s); }
  const el = document.createElement("div");
  el.className = "qfm-pick"; el.setAttribute("role", "dialog"); el.setAttribute("aria-label", "Mood events");
  el.innerHTML = `<h3>Mood <span>Shift+M or Esc closes</span></h3><ol></ol><p></p>`;
  const ol = el.querySelector("ol"), msg = el.querySelector("p");
  for (const [k, v] of Object.entries(KINDS)) {
    const li = document.createElement("li"), b = document.createElement("button");
    b.type = "button";
    b.innerHTML = `<span>${v.label}</span><span class="e">${v.sound ? "sound" : v.light ? "light" : "sight"} · ${v.min ? "from " + Math.round(v.min * 100) + "%" : "any depth"}</span>`;
    b.addEventListener("click", () => { const ok = mood.trigger(k); msg.textContent = ok ? `${k} fired` : `${k}: no place for it here (turn toward a corner or a side passage)`; });
    li.appendChild(b); ol.appendChild(li);
  }
  document.body.appendChild(el);
  picker = el;
}
function closePicker() { if (picker) { picker.remove(); picker = null; } }
function pickerKey(e) {
  if (e.target && e.target.closest && e.target.closest("input, textarea, select")) return;
  if (e.key === "M" && e.shiftKey) { e.preventDefault(); picker ? closePicker() : openPicker(); }
  else if (e.key === "Escape" && picker) { e.preventDefault(); e.stopPropagation(); closePicker(); }
}

// ---- verification: one moment of one event into the dump ---------------------------------------------------------
async function dumpMode(kind, ms) {
  const wait = async (fn, max = 20000) => { const t0 = performance.now(); while (!fn() && performance.now() - t0 < max) await new Promise((r) => setTimeout(r, 120)); return fn(); };
  await wait(() => kryptOf());
  await wait(() => document.getElementById("dumpshot"));
  const kr = kryptOf();
  const errors = [];
  let info = { mood: kind, at: ms }, png = "";
  try {
    const b = JSON.parse(document.getElementById("dumpshot").textContent);
    if (b.pos && b.look) {
      kr.camera.position.fromArray(b.pos); kr.camera.lookAt(b.look[0], b.look[1], b.look[2]); kr.camera.updateMatrixWorld(true);
      kr.takeover(true); kr.takeover(false);
      await new Promise((r) => setTimeout(r, 300));
      kr.takeover(true);
      kr.camera.position.fromArray(b.pos); kr.camera.lookAt(b.look[0], b.look[1], b.look[2]); kr.camera.updateMatrixWorld(true);
    }
  } catch (e) { errors.push("camera reset: " + e); }
  try {
    await audio.ready();
    const seed = Number(QS.get("moodseed") ?? 11) || 11;
    const c = makeCtx(kr, { dump: true, seed, own: true });
    { const fr = frameOf(kr); info.corners = (kr.corners || []).length; info.dbg = {};
      { const rows = [], R = 20, e = fr.eye; for (let dz = -R; dz <= R; dz++) { let r = ""; for (let dx = -R; dx <= R; dx++) { const x = Math.round(e.x) + dx, z = Math.round(e.z) + dz;
          let ch = kr.solidAt(x, e.y, z) ? "#" : ".";
          if (dx === 0 && dz === 0) ch = "@"; for (const k of kr.corners || []) if (Math.round(k.pos.x) === x && Math.round(k.pos.z) === z) ch = k.kind === "bend" ? "B" : "P";
          r += ch; } rows.push(r); } info.map = rows; info.fwd = [+fr.fwd.x.toFixed(2), +fr.fwd.z.toFixed(2)]; } findPeek(kr, fr, () => 0.5, 18, 30, info.dbg);
      info.near = (kr.corners || []).map((k) => { const d = k.pos.clone().sub(fr.eye); d.y = 0; const L = d.length(); return [k.kind, +L.toFixed(1), +(d.normalize().dot(fr.fwd)).toFixed(2), k.pos.toArray().map((x) => +x.toFixed(1))]; }).filter((a) => a[1] < 60).sort((a, b) => a[1] - b[1]).slice(0, 8); }
    let ev = build(c, kind);
    if (!ev) {   // dump only: walk the camera round the corners in view until the event has a place (the dump's own frame may stand in a bare corridor)
      const cams = [], f0 = frameOf(kr), c0 = f0.eye.clone();
      for (const k of kr.corners || []) for (const sg of [1, -1]) for (const D of [20, 23, 26, 29]) for (const lat of [0, -1, 1]) {
        const f = f0.fwd.clone().multiplyScalar(sg), r = new THREE.Vector3(-f.z, 0, f.x);
        const u0 = k.pos.clone().sub(c0).dot(f);
        const p = c0.clone().addScaledVector(f, u0 - D).addScaledVector(r, lat);
        if (kr.solidAt(p.x, p.y, p.z) || !kr.solidAt(p.x, k.pos.y - 0.4, p.z)) continue;
        cams.push([p, new THREE.Vector3(p.x + f.x * 10, p.y, p.z + f.z * 10), k]);
      }
      info.seek = cams.length; info.dbg2 = {};
      for (const [p, look] of cams.slice(0, 12)) { kr.camera.position.copy(p); kr.camera.lookAt(look.x, p.y - 0.1, look.z); kr.camera.updateMatrixWorld(true); findPeek(kr, frameOf(kr), () => 0.5, 18, 30, info.dbg2); }
      for (const [p, look] of cams.slice(0, 60)) {
        kr.camera.position.copy(p); kr.camera.lookAt(look.x, p.y - 0.1, look.z); kr.camera.updateMatrixWorld(true);
        ev = build(c, kind);
        if (ev) { info.seekCam = p.toArray().map((x) => +x.toFixed(1)); break; }
      }
    }
    if (!ev) errors.push("no place for " + kind + " from this camera (try another &at=)");
    else {
      if (ev.ready) await ev.ready;
      await new Promise((r) => setTimeout(r, 400));
      let ended = false;
      for (let t = 0; t <= ms / 1000 + 1e-6 && !ended; t += 1 / 30) { c.now = t; ended = !!ev.update(t, 1 / 30); c.light.update(1 / 30); }
      kr.camera.updateMatrixWorld(true);
      kr.composer.render();
      const gl = kr.renderer.domElement;
      const out = document.createElement("canvas"); out.width = gl.width; out.height = gl.height;
      out.getContext("2d").drawImage(gl, 0, 0);
      png = out.toDataURL("image/png");
      const fr = frameOf(kr);
      info = { ...info, ended, sfx: c.sfx, spot: ev.spot ? Object.fromEntries(Object.entries(ev.spot).filter(([, v]) => v && v.isVector3).map(([k, v]) => [k, v.toArray().map((x) => +x.toFixed(1))])) : null,
        eye: fr.eye.toArray().map((x) => +x.toFixed(1)), realSounds: Object.keys(KINDS).length && ["far_groan", "scamper", "scrape", "breath_near"].map((n) => [n, audio.has("qf.mood." + n)]),
        mob: ev.mob ? ev.mob.pivot.position.toArray().map((x) => +x.toFixed(2)) : null };
      if (ev.stop) ev.stop();
      c.light.clear();
    }
  } catch (e) { errors.push(String(e && e.stack || e)); console.error("mood dump", e); }
  const old = document.getElementById("dumpshot");
  let base = {};
  if (old) { try { base = JSON.parse(old.textContent); } catch (e) { base = {}; } old.remove(); }
  const sc = document.createElement("script"); sc.type = "application/json"; sc.id = "dumpshot";
  sc.textContent = JSON.stringify({ ...base, png: png || base.png, ...info, errors: (base.errors || []).concat(errors, window.__errs || []) });
  document.body.appendChild(sc);
}
