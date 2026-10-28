// Jump scares for the Krypt. Each one plays inside the real Krypt scene, where the visitor stands: the walk freezes,
// the music drops out, the build-up (different every play: lengths, fake-outs, directions) goes silent, the mob's
// face lunges into the lens with the loudest sound on the page, static, the kill, and the 1.7.10 "You died!" screen.
// Respawn puts them back exactly where they were.
//   initScares({ enabled })          from the marked block in app.js
//   J                                 the picker: every scare, approved or not; a click or its number plays it here
//   scares/approved.json              { "approved": [ids] }: the random director only ever plays these; the gap deaths
//                                     (LavaFall, DrownedGrab) take 15% of the Krypt's jumps (krypt-gap) once approved
//   ?scare=<id>                       play one as soon as the Krypt is up (testing)
//   ?scare=<id>&scareat=<ms|beat>&dump=1   render that moment into #dumpshot for tools/site/dump_frames.py;
//                                     beat: dread, fake, lunge, kill, death (+/-ms); &scareseed=N picks the dice
// Code against window.__krypt (see the contract at the top of app.js).
import { audio } from "../lib/qfaudio.js";
import { createDirector, CFG } from "./scares/director.js";
import { HELD } from "./scares/loadout.js";

export const SCARES = [
  { id: "Zombie", label: "Zombie", entry: "look-back", file: "zombie" },
  { id: "Skeleton", label: "Skeleton", entry: "lights-out", file: "skeleton" },
  { id: "Creeper", label: "Creeper", entry: "look-back", file: "creeper" },
  { id: "Spider", label: "Spider", entry: "ceiling drop", file: "spider" },
  { id: "CaveSpider", label: "Cave Spider", entry: "piston trap", file: "cavespider" },
  { id: "Enderman", label: "Enderman", entry: "teleport grab", file: "enderman" },
  { id: "Witch", label: "Witch", entry: "potions", file: "witch" },
  { id: "Slime", label: "Slime", entry: "piston trap", file: "slime" },
  { id: "Silverfish", label: "Silverfish", entry: "wall break", file: "silverfish" },
  { id: "Blaze", label: "Blaze", entry: "heat", file: "blaze" },
  { id: "Ghast", label: "Ghast", entry: "piston trap", file: "ghast", deep: true },
  { id: "MagmaCube", label: "Magma Cube", entry: "in the black", file: "magmacube" },
  { id: "PigZombie", label: "Zombie Pigman", entry: "your fault", file: "pigman" },
  { id: "WitherSkeleton", label: "Wither Skeleton", entry: "in the fog", file: "witherskeleton", deep: true },
  // Failed jumps: only at the Krypt's gaps (krypt-gap), never from the random director; the picker plays them here.
  { id: "LavaFall", label: "Lava fall", entry: "failed jump", file: "lavafall", gap: "lava" },
  { id: "DrownedGrab", label: "Drowned grab", entry: "failed jump", file: "drowned", gap: "water" }
];
const MOBS = SCARES.map((s) => s.id);
const ALIAS = { cavespider: "CaveSpider", cave_spider: "CaveSpider", magmacube: "MagmaCube", magma_cube: "MagmaCube", lavaslime: "MagmaCube", pigman: "PigZombie", zombiepigman: "PigZombie", zombie_pigman: "PigZombie", pigzombie: "PigZombie", witherskeleton: "WitherSkeleton", wither_skeleton: "WitherSkeleton",
  lava: "LavaFall", lavafall: "LavaFall", lava_fall: "LavaFall", drowned: "DrownedGrab", drownedgrab: "DrownedGrab", drowned_grab: "DrownedGrab", water: "DrownedGrab" };
const GAP_CHANCE = 0.15;
// The mood layer (site/graves/mood*) and the scares never overlap: feature-detect its busy flag.
const moodBusy = () => { const m = window.__mood; if (!m) return false; try { return !!(typeof m.busy === "function" ? m.busy() : (m.busy ?? m.running ?? m.active)); } catch (e) { return false; } };
const DEEP_SEGMENTS = new Set(["chasm", "stairs", "deep", "fortress", "nether", "vault", "portal", "stronghold"]);
const SS_KEY = "qf-scares-v2";
const QS = new URLSearchParams(location.search);
const DUMP = QS.has("dump");

function canon(s) {
  if (!s) return null;
  const k = String(s).toLowerCase();
  return ALIAS[k] || MOBS.find((m) => m.toLowerCase() === k) || null;
}
const hashStr = (s) => { let h = 2166136261; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; };
function readSession() { try { const j = JSON.parse(sessionStorage.getItem(SS_KEY) || "{}"); return Array.isArray(j.done) ? j.done : []; } catch (e) { return []; } }
function writeSession(done) { try { sessionStorage.setItem(SS_KEY, JSON.stringify({ done })); } catch (e) { /* storage blocked */ } }
const kryptOf = () => (window.__krypt && window.__krypt.scene ? window.__krypt : null);

// ---- modules, loaded on demand ---------------------------------------------------------------------------
let RIG = null, HUD = null;
const defs = new Map();
async function loadDef(id) {
  const s = SCARES.find((x) => x.id === id);
  if (!RIG) [RIG, HUD] = await Promise.all([import("./scares/rig.js"), import("./scares/hud.js")]);
  if (!defs.has(id)) defs.set(id, import(`./scares/${s.file}.js`).then((m) => m.default));
  return defs.get(id);
}

// ---- sound: the music drops to silence for the scare, the ambience to a whisper ------------------------------------
const BUS_FULL = { music: 0.45, ambient: 0.7 };
function hush(on) {
  const ctx = audio.context(); if (!ctx) return;
  const t = ctx.currentTime;
  for (const [b, low] of [["music", 0.0], ["ambient", 0.1]]) {
    const n = audio.busNode(b); if (!n) continue;
    n.gain.cancelScheduledValues(t); n.gain.setValueAtTime(n.gain.value, t);
    n.gain.setTargetAtTime(on ? BUS_FULL[b] * low : BUS_FULL[b], t, on ? 0.12 : 0.9);
  }
}
// Every sound a scare starts goes through this (round 8): a one-shot plays one pass even of an event the manifest
// loops (the Silverfish's chitter in its roar was one, and played on forever after Enter), each is tagged "scare" for
// the leak check (audio.voices()), and stop() ends every one still sounding, one-shots included.
function scareAudio(shots) {
  const tag = (o) => ({ ...o, tag: "scare" });
  return { ...audio,
    play(name, o = {}) { const h = audio.play(name, tag({ once: !o.loop, ...o })); shots.push(h); return h; },
    loop(name, o = {}) { return audio.loop(name, tag(o)); } };
}
function soundPlayer(R, S) {
  const live = [], fired = new Set();
  const shots = [], audio = scareAudio(shots);   // (shadows the module's audio in here; see scareAudio)
  // One voice at a time: the death screams are single recorded takes of 2 to 4.5 s (round 7), so a second call while
  // one still sounds would put a second man screaming over the first. The take plays through instead. Round 8: the
  // drowning screams (underwater) are the same throat, so they share the rule (the jump screech, under 1 s, does not).
  let voice = null;
  const ONE_VOICE = new Set(["qf.scare.death_scream", "qf.scare.underwater"]);
  const pos = (o) => (o && o.at ? R.Lp(o.at[0], o.at[1], o.at[2]) : null);
  return {
    tick(prev, t) {
      (S.sounds || []).forEach((s, i) => {
        if (fired.has(i) || s[0] > t || s[0] <= prev - 0.25) return;
        fired.add(i);
        const [, name, o = {}] = s;
        try {
          if (name === "@muffle") audio.muffle(o.hz || 500, o.s || 2);
          else if (name === "@silence") {
            // Silence before the lunge: every loop out, the ambience to nothing (hush(false) brings it back).
            for (const x of live) if (!x.done) { x.done = true; try { x.h.stop(o.s ?? 0.12); } catch (e) { /* ignore */ } }
            const ctx = audio.context(), n = audio.busNode("ambient");
            if (ctx && n) { const t0 = ctx.currentTime; n.gain.cancelScheduledValues(t0); n.gain.setValueAtTime(n.gain.value, t0); n.gain.linearRampToValueAtTime(0, t0 + (o.s ?? 0.12)); }
          } else if (ONE_VOICE.has(name)) { if (!voice || voice.stopped) voice = audio.play(name, { ...o, pos: pos(o) || undefined }); }
          else audio.play(name, { ...o, pos: pos(o) || undefined });
        } catch (e) { /* audio locked */ }
      });
      (S.loops || []).forEach((l, i) => {
        const [t0, t1, name, o = {}] = l, k = "L" + i;
        const h = live.find((x) => x.k === k);
        if (!h && t >= t0 && t < t1 && !fired.has(k)) { fired.add(k); try { live.push({ k, h: audio.loop(name, { ...o, pos: pos(o) || undefined, fadeIn: o.fadeIn ?? 0.3 }), t1, fade: o.fadeOut ?? 0.4 }); } catch (e) { /* ignore */ } }
      });
      for (const x of live) if (!x.done && t >= x.t1) { x.done = true; try { x.h.stop(x.fade); } catch (e) { /* ignore */ } }
    },
    stop() {
      for (const x of live) if (!x.done) { x.done = true; try { x.h.stop(0.3); } catch (e) { /* ignore */ } }
      for (const h of shots) if (h && !h.stopped) { try { h.stop(0.2); } catch (e) { /* ignore */ } }
    }
  };
}

// ---- the live run ------------------------------------------------------------------------------------------
let running = null;
function kryptHud(hide) {
  const st = document.getElementById("stage"); if (!st) return;
  for (const el of st.querySelectorAll(".hud, .hint, .strip-wrap, .sheet, .minimap, #minimap")) {
    if (hide) { el.dataset.qfsVis = el.style.visibility; el.style.visibility = "hidden"; } else { el.style.visibility = el.dataset.qfsVis || ""; delete el.dataset.qfsVis; }
  }
}
// The Krypt's gap nearest ahead of the camera of this kind (for the picker: a failed jump where you stand uses a
// real gap only if one is right there; otherwise the scare digs its own).
function gapNear(kr, kind) {
  const gs = Array.isArray(kr.gaps) ? kr.gaps : [];
  const cam = kr.camera.position;
  let best = null, bd = 4.5;
  for (const g of gs) { if (!g || !g.pos || (kind && g.kind !== kind)) continue; const d = Math.hypot(g.pos.x - cam.x, g.pos.z - cam.z); if (d < bd) { bd = d; best = g; } }
  return best;
}
const soundNames = (S) => [...new Set([...(S.sounds || []).map((s) => s[1]), ...(S.loops || []).map((l) => l[2])].filter((n) => n && n[0] !== "@"))];

export async function playScare(id, { score = 0, onDone, gap = null, widen = false } = {}) {
  id = canon(id);
  const kr = kryptOf();
  if (!id || !kr || running) return false;
  const entry = SCARES.find((s) => s.id === id);
  if (entry.gap && !gap) gap = gapNear(kr, entry.gap);
  const stage = document.getElementById("stage");
  running = { id };
  try { kr.takeover(true); } catch (e) { /* ignore */ }
  hush(true); kryptHud(true);
  let R = null, hud = null, snd = null, block = null;
  const cleanup = () => {
    removeEventListener("keydown", onKey, true); removeEventListener("resize", onResize);
    if (snd) snd.stop();
    if (R) R.dispose();
    if (hud) hud.dispose();
    if (block) block.remove();
    hush(false); kryptHud(false);
    try { kr.takeover(false); } catch (e) { /* ignore */ }
    running = null;
  };
  let dead = false, over = false, hover = null;
  function respawn(to) {
    if (over || !dead) return;
    over = true;
    if (block) { block.style.transition = "opacity .25s"; block.style.background = "#000"; block.style.opacity = "1"; }
    setTimeout(() => {
      cleanup();
      if (to === "title") { try { window.scrollTo({ top: 0, behavior: "smooth" }); } catch (e) { /* ignore */ } }
      if (onDone) onDone();
    }, 260);
  }
  function onKey(e) {
    if (dead && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); respawn(hover === "title" ? "title" : "respawn"); }
    else if (e.key !== "Tab") e.preventDefault();
    e.stopPropagation();
  }
  const onResize = () => { if (hud) hud.size(); };
  try {
    const def = await loadDef(id);
    hud = await HUD.createHud(stage);
    // A new roll of the dice every play: the build-up's lengths, fake-outs and directions change each time.
    R = await RIG.createRig(kr, { seed: hashStr(id) & 0xffff, rand: (Math.random() * 4294967296) >>> 0, gap, frame: gap && gap.dir ? { dir: gap.dir } : null });
    R.widen = !!widen;   // a retry: the scare may search further for the room it needs (R.widen)
    const S = await def.build(R);
    await R.ready();
    S.death = S.death || def.death;
    if (S.held === undefined) S.held = HELD[id] ?? null;   // what the hand holds: the hotbar selects it (loadout.js)
    running.dur = S.dur; running.marks = S.marks || null; running.notes = S.notes || null; running.rig = R;
    // Every sound decoded before the freeze: a screech that starts late is no screech.
    try { await Promise.race([audio.preload(soundNames(S)), new Promise((r) => setTimeout(r, 2500))]); } catch (e) { /* play what we have */ }
    snd = soundPlayer(R, S);
    // A layer over the stage that takes the pointer while the scare plays (the Respawn button lives on it).
    block = document.createElement("div");
    block.style.cssText = "position:absolute;inset:0;z-index:10;cursor:none;background:transparent;opacity:1";
    block.setAttribute("role", "alert");
    const btn = document.createElement("button");
    btn.type = "button"; btn.textContent = "Respawn";
    btn.style.cssText = "position:absolute;left:-9999px;top:0";
    btn.addEventListener("click", () => respawn("respawn"));
    block.appendChild(btn);
    stage.appendChild(block);
    const xy = (e) => { const r = stage.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; };
    block.addEventListener("pointermove", (e) => { hover = dead ? hud.hit(...xy(e)) : null; block.style.cursor = dead ? (hover ? "pointer" : "default") : "none"; });
    block.addEventListener("click", (e) => { if (!dead) return; const b = hud.hit(...xy(e)); if (b) respawn(b); });
    block.addEventListener("wheel", (e) => e.preventDefault(), { passive: false });
    addEventListener("keydown", onKey, true); addEventListener("resize", onResize);
    let prev = 0;
    R.run(S, (f, t) => {
      snd.tick(prev, t); prev = t;
      running.t = t; running.frames = (running.frames || 0) + 1;
      f.score = score; f.deadFor = t - S.dur - 0.5; f.hover = hover;
      if (t >= S.dur) f.chat = S.death;
      if (!dead && f.deadFor >= 1) { dead = true; block.style.cursor = "default"; btn.style.cssText = "position:absolute;opacity:0;left:50%;top:50%;width:1px;height:1px"; btn.setAttribute("aria-label", "You died. Respawn"); try { btn.focus({ preventScroll: true }); } catch (e) { /* ignore */ } }
      hud.draw(f, t);
      try { audio.updateListener(kr.camera); } catch (e) { /* ignore */ }
    });
    return true;
  } catch (e) {
    console.error("scare", id, e);
    cleanup();
    return false;
  }
}

// ---- verification: one moment of a scare into the dump ------------------------------------------------------------
async function dumpMode(id) {
  let ms = 0;
  const wait = async (fn, max = 120000) => { const t0 = performance.now(); while (!fn() && performance.now() - t0 < max) await new Promise((r) => setTimeout(r, 120)); return fn(); };
  await wait(() => kryptOf());
  await wait(() => document.getElementById("dumpshot"));   // the Krypt's own verification frame: its blocks are built
  const kr = kryptOf();
  const errors = [];
  // The Krypt's dump frames run with timestamps ahead of the clock, so its next live frame damps backwards and throws
  // the camera far off (a negative dt). Put the camera back where the Krypt's own frame had it, and restart its clock.
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
  let info = { scare: id };
  let png = "";
  try {
    const def = await loadDef(id);
    const stage = document.getElementById("stage");
    const hud = await HUD.createHud(stage);
    try { kr.takeover(true); } catch (e) { /* ignore */ }
    const entry = SCARES.find((s) => s.id === id), gap = entry.gap ? gapNear(kr, entry.gap) : null;
    // ?scareseed=N picks the play's dice (the same N gives the same build-up); the default is fixed per scare.
    const rand = QS.get("scareseed") != null ? Number(QS.get("scareseed")) >>> 0 : (hashStr(id) & 0xffff) * 7919 + 13;
    const R = await RIG.createRig(kr, { seed: hashStr(id) & 0xffff, rand, gap, frame: gap && gap.dir ? { dir: gap.dir } : null });
    const S = await def.build(R);
    await R.ready();
    if (S.held === undefined) S.held = HELD[id] ?? null;
    R.noFx = QS.has("nofx");   // checking a pose without the tear and static
    // ?scareat=<ms> or a beat by name (dread, fake, lunge, kill, death; +ms/-ms after it): the scare's own marks.
    // A comma list renders each in turn (in time order) into `pngs` as well; `png` is the first.
    const M = { ...(S.marks || {}), death: S.dur + 1.25 };
    // (a "+" in a query string arrives as a space)
    const toMs = (a) => { const mm = a.replace(/ (\d)/, "+$1").match(/^([a-z]+)([+-]\d+)?$/i); return mm ? ((M[mm[1]] ?? 0) * 1000) + Number(mm[2] || 0) : Number(a) || 0; };
    const ats = String(QS.get("scareat") ?? "0").split(",").map((a) => a.trim()).filter(Boolean);
    const pngs = [];
    const sc = QS.get("scarecam") ? QS.get("scarecam").split(",").map(Number) : null;   // x,y,z,yaw,pitch[,roll] local
    let f = null, t = 0;
    for (const a of ats) {
      ms = toMs(a); t = ms / 1000;
      f = R.renderAt(S, t, { ...(sc ? { cam: { x: sc[0], y: sc[1], z: sc[2], yaw: sc[3], pitch: sc[4], roll: sc[5] || 0 } } : {}), pull: Number(QS.get("scarepull")) || 0 });
      if (sc) { f.white = 0; f.black = 0; f.vig = null; f.tints = []; }
      if (R.noFx) f.cut = 0;
      const gl = kr.renderer.domElement;
      const out = document.createElement("canvas"); out.width = gl.width; out.height = gl.height;
      const x = out.getContext("2d"); x.drawImage(gl, 0, 0);
      f.score = 37; f.deadFor = t - S.dur - 0.5; if (t >= S.dur) f.chat = S.death || def.death;
      hud.size(); hud.draw(f, t);
      x.imageSmoothingEnabled = false; x.drawImage(hud.canvas, 0, 0, hud.canvas.width * hud.scale * (out.width / Math.max(1, stage.clientWidth)), hud.canvas.height * hud.scale * (out.height / Math.max(1, stage.clientHeight)));
      const p = out.toDataURL("image/png");
      if (!png) png = p;
      if (ats.length > 1) pngs.push({ at: a, t: +t.toFixed(3), png: p, fx: f.fx || null, cut: f.cut || 0 });
    }
    if (pngs.length) info.pngs = pngs;
    await audio.ready();
    const names = new Set([...(S.sounds || []).map((s) => s[1]), ...(S.loops || []).map((l) => l[2])].filter((n) => n[0] !== "@"));
    info = { ...info, segment: R.seg, depth: +(R.depth || 0).toFixed(3), dur: S.dur, hits: (S.hits || []).map((h) => h.t), hp: f.hp,
      floorY: R.O.y, ceil: R.ceil, wallL: +R.wallL.toFixed(2), wallR: +R.wallR.toFixed(2), ahead: +R.ahead.toFixed(1), behind: +R.behind.toFixed(1),
      openings: R.openings.map((o) => [o.side, o.z0, o.z1, +o.depth.toFixed(1)]), torches: R.torches.length, notes: S.notes || null, debug: R.debug,
      at: +t.toFixed(3), marks: S.marks || null, fx: f.fx || null, cut: f.cut || 0, gap: gap ? { kind: gap.kind, width: gap.width } : null,
      sfx: (S.sounds || []).filter((s) => s[0] <= t && s[0] > t - 1.5).map((s) => [+s[0].toFixed(2), s[1]]), missingSounds: [...names].filter((n) => !audio.has(n)) };
  } catch (e) { errors.push(String(e && e.stack || e)); console.error("scare dump", e); }
  const old = document.getElementById("dumpshot");
  let base = {};
  if (old) { try { base = JSON.parse(old.textContent); } catch (e) { base = {}; } old.remove(); }
  const sc = document.createElement("script"); sc.type = "application/json"; sc.id = "dumpshot";
  sc.textContent = JSON.stringify({ ...base, png: png || base.png, ...info, errors: (base.errors || []).concat(errors, window.__errs || []) });
  document.body.appendChild(sc);
}

// ---- the picker (J) ---------------------------------------------------------------------------------------------
let approved = [];
const PCSS = `.qfs-pick{position:fixed;left:14px;bottom:14px;z-index:100000;min-width:290px;background:rgba(16,16,16,.92);border:2px solid #000;outline:2px solid #555;
 font:13px/1.25 "JetBrains Mono",ui-monospace,Menlo,monospace;color:#e0e0e0;padding:8px 6px 6px;box-shadow:0 6px 24px rgba(0,0,0,.6)}
.qfs-pick h3{margin:0 4px 6px;font:inherit;color:#ffff55;letter-spacing:.04em}
.qfs-pick h3 span{color:#aaa}
.qfs-pick ol{list-style:none;margin:0;padding:0;max-height:min(60vh,420px);overflow:auto}
.qfs-pick button{display:grid;grid-template-columns:2.2em 1fr auto;gap:6px;width:100%;text-align:left;font:inherit;color:#e0e0e0;background:transparent;border:0;padding:3px 6px;cursor:pointer}
.qfs-pick button:hover,.qfs-pick button:focus-visible,.qfs-pick button[aria-current=true]{background:#2f2f50;color:#ffffa0;outline:0}
.qfs-pick .n{color:#aaa}.qfs-pick .e{color:#888;font-size:11px}.qfs-pick .ok{color:#55ff55}.qfs-pick .no{color:#aaaaaa}
.qfs-pick p{margin:6px 4px 0;color:#888;font-size:11px}`;
let picker = null;
function openPicker() {
  if (picker) return;
  if (!document.getElementById("qfs-pcss")) { const s = document.createElement("style"); s.id = "qfs-pcss"; s.textContent = PCSS; document.head.appendChild(s); }
  const el = document.createElement("div");
  el.className = "qfs-pick"; el.setAttribute("role", "dialog"); el.setAttribute("aria-label", "Scares");
  el.innerHTML = `<h3>Scares <span>J or Esc closes</span></h3><ol></ol><p>A number or a click plays it where you stand.</p>`;
  const ol = el.querySelector("ol");
  SCARES.forEach((s, i) => {
    const li = document.createElement("li"), b = document.createElement("button");
    b.type = "button";
    const ok = approved.includes(s.id);
    b.innerHTML = `<span class="n">${i + 1}</span><span>${s.label} <span class="e">${s.entry}</span></span><span class="${ok ? "ok" : "no"}">${ok ? "approved" : "not yet"}</span>`;
    b.addEventListener("click", () => { closePicker(); pickPlay(s.id); });
    li.appendChild(b); ol.appendChild(li);
  });
  document.body.appendChild(el);
  picker = { el, buf: "", timer: 0, sel: -1 };
}
// A picked scare that cannot be staged where you stand (its build throws: the Skeleton's ossuary or the Wither's
// passage found no rock to carve) is tried once more with a wider search and new dice; if that fails too another scare
// plays (and the console says why), so a press never gives nothing.
function pickPlay(id) {
  const why = (x) => console.warn(`[scares] ${x}`);
  playScare(id).then((ok) => {
    if (ok || running) return;
    why(`${id} could not be staged here; trying once more, searching wider`);
    return playScare(id, { widen: true }).then((ok2) => {
      if (ok2 || running) return;
      const pool = SCARES.filter((q) => q.id !== id && !q.gap).map((q) => q.id), ap = pool.filter((q) => approved.includes(q));
      const tryNext = (left) => {
        if (!left.length || running) return;
        const next = left[Math.floor(Math.random() * left.length)];
        why(`${id} could not be staged here; playing ${next} instead`);
        playScare(next, { widen: true }).then((ok3) => { if (!ok3 && !running) tryNext(left.filter((q) => q !== next)); });
      };
      tryNext(ap.length ? ap : pool);
    });
  });
}
function closePicker() { if (!picker) return; clearTimeout(picker.timer); picker.el.remove(); picker = null; }
function pickerKey(e) {
  if (e.target && e.target.closest && e.target.closest("input, textarea, select")) return;
  if (running) return;
  if (e.key === "j" || e.key === "J") { e.preventDefault(); if (picker) closePicker(); else openPicker(); return; }
  if (!picker) return;
  if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); closePicker(); return; }
  const btns = [...picker.el.querySelectorAll("button")];
  if (e.key === "ArrowDown" || e.key === "ArrowUp") {
    e.preventDefault(); e.stopPropagation();
    picker.sel = (picker.sel + (e.key === "ArrowDown" ? 1 : -1) + btns.length) % btns.length;
    btns.forEach((b, i) => b.setAttribute("aria-current", i === picker.sel ? "true" : "false")); btns[picker.sel].focus();
    return;
  }
  if (/^[0-9]$/.test(e.key)) {
    e.preventDefault(); e.stopPropagation();
    picker.buf += e.key; clearTimeout(picker.timer);
    const go = () => { const n = Number(picker.buf); picker.buf = ""; if (n >= 1 && n <= SCARES.length) { const id = SCARES[n - 1].id; closePicker(); pickPlay(id); } };
    // "1" may start 10 to 14: wait a moment for a second digit.
    if (picker.buf === "1") picker.timer = setTimeout(go, 650); else go();
  }
}

// ---- the director's loop ---------------------------------------------------------------------------------------------
export function initScares(opts = {}) {
  const enabled = opts.enabled || (() => true);
  const forced = canon(QS.get("scare"));
  fetch(new URL("./scares/approved.json", import.meta.url), { cache: "no-store" }).then((r) => (r.ok ? r.json() : {})).then((j) => {
    approved = (Array.isArray(j.approved) ? j.approved : []).map(canon).filter(Boolean);
  }).catch(() => { approved = []; });
  if (forced && DUMP) { dumpMode(forced).catch((e) => console.error("scare dump", e)); return; }
  addEventListener("keydown", pickerKey, true);
  window.__scares = { play: (m) => playScare(m), list: SCARES, get approved() { return approved.slice(); }, get busy() { return !!running; },
    // (for the leak check: every sound sounding now, tagged "scare" if a scare started it)
    voices: () => (audio.voices ? audio.voices() : null),
    // (for the real-time check: where the playing scare's clock is)
    get state() { return running ? { id: running.id, t: running.t ?? -1, frames: running.frames || 0, dur: running.dur ?? null, marks: running.marks || null, notes: running.notes || null, carveMs: running.rig ? Math.round(running.rig.carveMs || 0) : 0 } : null; } };
  // Failed jumps: before each jump the Krypt asks (krypt-gap, { gap, takeover }); an approved gap death of that kind
  // takes 15% of them. Feature-detected: without the event nothing happens.
  addEventListener("krypt-gap", (e) => {
    const d = (e && e.detail) || {}, g = d.gap;
    if (!g || running || picker || document.hidden || !enabled() || moodBusy()) return;
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const ids = SCARES.filter((s) => s.gap && s.gap === g.kind && approved.includes(s.id)).map((s) => s.id);
    if (!ids.length || Math.random() >= GAP_CHANCE) return;
    try { if (typeof d.takeover === "function") d.takeover(); } catch (err) { return; }
    playScare(ids[Math.floor(Math.random() * ids.length)], { gap: g });
  });
  if (forced) {
    const go = () => setTimeout(() => playScare(forced), 1200);
    if (kryptOf()) go(); else addEventListener("krypt-ready", go, { once: true });
    return;
  }
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;   // accessibility: the director never fires
  const director = createDirector({ done: readSession() });
  window.__scares.director = director;
  let acc = 0, lastSec = 0, lastS = null, last = performance.now(), pending = null, waited = 0;
  setInterval(() => {
    const now = performance.now(), dt = Math.min(0.5, (now - last) / 1000); last = now;
    if (running || picker || document.hidden || !enabled() || !approved.length || moodBusy()) return;
    const kr = kryptOf(); if (!kr || !kr.getWalk) return;
    const w = kr.getWalk();
    const moving = lastS != null && Math.abs(w.s - lastS) > 0.00003; lastS = w.s;
    if (moving) acc += dt;
    const deep = DEEP_SEGMENTS.has(w.segment) || (w.depth ?? w.s) > 0.62;
    if (!pending) {
      const sec = Math.floor(acc);
      if (sec > lastSec) {
        lastSec = sec;
        if (director.second(sec, w.depth ?? w.s)) {
          const pool = approved.filter((id) => { const s = SCARES.find((q) => q.id === id); return s && !s.gap && (!s.deep || deep); });
          const id = director.pick(pool);
          if (id) { pending = id; waited = 0; loadDef(id).catch(() => { pending = null; }); }
        }
      }
    } else {
      // Fire mid-stride, a beat after the walk was moving: the freeze has to interrupt something.
      waited += dt;
      if (moving && waited > 0.6) {
        const fire = (id, tried) => {
          director.fired(acc, id); writeSession(director.done);
          playScare(id, { score: Math.floor(acc), onDone: () => { lastS = null; } }).then((ok) => {
            if (ok || running) return;
            // it could not be staged here (its build threw): it never played, so it stays in the pool, and another plays
            console.warn(`[scares] ${id} could not be staged here; the director picks another`);
            const i = director.done.lastIndexOf(id); if (i >= 0) director.done.splice(i, 1); writeSession(director.done);
            const pool = approved.filter((q) => { const s = SCARES.find((x) => x.id === q); return s && !s.gap && (!s.deep || deep) && q !== id && !tried.includes(q); });
            const next = director.pick(pool);
            if (next) fire(next, [...tried, id]);
          });
        };
        const id = pending; pending = null;
        fire(id, []);
      } else if (waited > 30) pending = null;
    }
  }, 100);
}

export { MOBS, CFG };
