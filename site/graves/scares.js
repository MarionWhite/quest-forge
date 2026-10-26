// Jump scares for the Krypt. A director counts the seconds a visitor really spends walking and, rarely, plays one
// Minecraft-style death cutscene (one per vanilla hostile mob) on its own canvas, then returns them to the corridor.
//   initScares({ enabled: () => bool })    from the marked block in app.js
//   ?scare=<mob>               play that cutscene right away (testing), ?scare=<mob>&at=<ms> seeks inside it
//   ?scare=<mob>&at=<ms>&dump=1  renders that moment into #dumpshot for tools/site/dump_frames.py
// Code against window.__krypt = { scene, camera, getWalk(): { s, speed, activeSeconds, depth }, corners, takeover(on) }.
import { audio } from "../lib/qfaudio.js";
import { createDirector, CFG } from "./scares/director.js";

const MOBS = ["Zombie", "Skeleton", "Creeper", "Spider", "CaveSpider", "Enderman", "Witch", "Slime", "Silverfish", "Blaze", "Ghast", "MagmaCube", "PigZombie", "WitherSkeleton"];
const ALIAS = { cavespider: "CaveSpider", cave_spider: "CaveSpider", magmacube: "MagmaCube", magma_cube: "MagmaCube", lavaslime: "MagmaCube", pigman: "PigZombie", zombiepigman: "PigZombie", zombie_pigman: "PigZombie", pigzombie: "PigZombie", witherskeleton: "WitherSkeleton", wither_skeleton: "WitherSkeleton" };
const SS_KEY = "qf-scares-v1";
const QS = new URLSearchParams(location.search);
const DUMP = QS.has("dump");

function canon(s) {
  if (!s) return null;
  const k = String(s).toLowerCase();
  return ALIAS[k] || MOBS.find((m) => m.toLowerCase() === k) || null;
}
function readSession() { try { const j = JSON.parse(sessionStorage.getItem(SS_KEY) || "{}"); return Array.isArray(j.done) ? j.done : []; } catch (e) { return []; } }
function writeSession(done) { try { sessionStorage.setItem(SS_KEY, JSON.stringify({ done })); } catch (e) { /* storage blocked */ } }

const CSS = `.qfs-host{position:fixed;inset:0;z-index:99999;background:#000;overflow:hidden;cursor:none;touch-action:none;-webkit-user-select:none;user-select:none}
.qfs-host canvas{position:absolute;inset:0;width:100%;height:100%;display:block}
.qfs-fx{image-rendering:pixelated;image-rendering:crisp-edges}
.qfs-host.qfs-dead{cursor:default}
.qfs-btn{position:absolute;background:transparent;border:0;margin:0;padding:0;opacity:0;cursor:pointer;display:none}
.qfs-btn:focus-visible{opacity:1;outline:2px solid #fff;outline-offset:2px;background:rgba(255,255,255,.08)}
.qfs-host.qfs-dead .qfs-btn{display:block}
.qfs-skip{position:absolute;left:-9999px}`;

let mod = null;
async function load() {
  if (!mod) {
    const [stage, fx, c1, c2] = await Promise.all([import("./scares/stage.js"), import("./scares/fx.js"), import("./scares/cuts1.js"), import("./scares/cuts2.js")]);
    mod = { stage, fx, cuts: { Zombie: c1.zombie, Skeleton: c1.skeleton, Creeper: c1.creeper, Spider: c1.spider, CaveSpider: c1.caveSpider, Enderman: c1.enderman, Witch: c1.witch, Slime: c2.slime, Silverfish: c2.silverfish, Blaze: c2.blaze, Ghast: c2.ghast, MagmaCube: c2.magmaCube, PigZombie: c2.pigman, WitherSkeleton: c2.witherSkeleton } };
  }
  return mod;
}

// Builds a scare (stage, overlay, cutscene) inside a host element. Nothing plays until play() is called.
async function prepare(id, { phone = false } = {}) {
  const M = await load();
  if (!document.getElementById("qfs-css")) { const s = document.createElement("style"); s.id = "qfs-css"; s.textContent = CSS; document.head.appendChild(s); }
  const host = document.createElement("div");
  host.className = "qfs-host"; host.setAttribute("role", "alert"); host.setAttribute("aria-label", "A jump scare. Press Enter on the Respawn button to return.");
  document.body.appendChild(host);
  const stage = await M.stage.createStage(host, { phone });
  const ov = M.fx.createOverlay(host);
  const btn = document.createElement("button"); btn.className = "qfs-btn"; btn.type = "button"; btn.textContent = "Respawn"; host.appendChild(btn);
  const gore = stage.gore;
  const c = {
    stage, phone,
    hitBurst(times, fn, kind, n, opts) {
      for (const t of times) {
        const p = fn(t); let o = [p.x, p.y, p.z];
        if (p.yaw !== undefined) { const cp = Math.cos(p.pitch || 0); o = [p.x - Math.sin(p.yaw) * cp * 0.5, p.y + Math.sin(p.pitch || 0) * 0.5, p.z - Math.cos(p.yaw) * cp * 0.5]; }
        gore.burst(t, o, n, kind, opts);
      }
    }
  };
  const cut = await M.cuts[id](c);
  const sr = M.stage.rngOf;
  const size = () => { const w = host.clientWidth || innerWidth, h = host.clientHeight || innerHeight; stage.size(w, h); ov.size(w, h); };
  size();
  const hits = cut.hits.slice().sort((a, b) => a - b).filter((h, i, a) => i === 0 || h - a[i - 1] >= 0.34);   // at most 3 flashes a second
  const n = hits.length, rr = sr(77);
  const splatPos = hits.map(() => [0.18 + rr() * 0.64, 0.2 + rr() * 0.5, 26 + rr() * 22]);

  // One frame of the scare at time t (seconds). Pure: the same t draws the same picture.
  function renderAt(t, score = 0) {
    const tt = Math.min(t, cut.dur), M2 = M.stage;
    const cam = cut.cam(tt);
    const amp = cut.shake ? cut.shake(tt) : 0.01;
    cam.x += (Math.sin(tt * 53) + 0.6 * Math.sin(tt * 97 + 1)) * amp; cam.y += Math.sin(tt * 61 + 2) * amp; cam.yaw = (cam.yaw || 0) + Math.sin(tt * 43) * amp * 0.5; cam.pitch = (cam.pitch || 0) + Math.sin(tt * 37 + 3) * amp * 0.3;
    let hurt = 0, hp = 20;
    hits.forEach((h, i) => {
      if (tt < h) return;
      hurt = Math.max(hurt, Math.exp(-(tt - h) / 0.14));
      const x = (tt - h) / 0.5;
      if (x < 1) { cam.roll = (cam.roll || 0) - Math.sin(Math.pow(1 - x, 4) * Math.PI) * 0.24 * (i % 2 ? -1 : 1); }
      hp = M2.lerp(20 * (1 - i / n), 20 * (1 - (i + 1) / n), M2.clamp((tt - h) / 0.3));
    });
    const f = { hud: true, hp, tints: [], splats: [], cracks: [], slashes: [], hurt, white: 0, black: 0, fire: 0, glitch: 0, bubbles: 0, vig: null, vigR: 0.95, hpMode: "normal", death: M2.clamp((t - cut.dur) / 0.9), deathLine: cut.death, score, btnHover: false };
    hits.forEach((h, i) => { if (tt >= h) f.splats.push({ t0: h, x: splatPos[i][0], y: splatPos[i][1], r: splatPos[i][2], seed: 100 + i }); });
    cut.update(tt, f);
    stage.setCam(cam);
    stage.light(tt, cut.flick ? cut.flick(tt) : 1);
    gore.update(tt);
    stage.render();
    return f;
  }
  function dispose() { host.remove(); stage.dispose(); }
  return { cut, host, stage, ov, btn, renderAt, size, dispose, hits };
}

// ---- the live run ---------------------------------------------------------------------------------
let running = null;
function krypt() { return window.__krypt || null; }

async function play(p, { onDone, score = 0 } = {}) {
  if (running) return;
  running = p;
  const { cut, host, ov, btn, renderAt } = p;
  const kr = krypt();
  if (kr && kr.takeover) try { kr.takeover(true); } catch (e) { /* ignore */ }
  const log = (window.__scareSfx = []);
  const t0 = performance.now(); let prev = -0.001, dead = false, raf = 0, over = false;
  try { audio.duck("sfx", cut.silence ? 0.05 : 0.2, cut.dur + 0.5); } catch (e) { /* audio may be locked */ }
  const block = (e) => { if (e.target !== btn && !(e.target && e.target.closest && e.target.closest(".qfs-btn"))) { e.preventDefault(); } e.stopPropagation(); };
  const onKey = (e) => { if (dead && (e.key === "Enter" || e.key === " ") ) { e.preventDefault(); respawn(); } else if (e.key !== "Tab") { e.preventDefault(); } e.stopPropagation(); };
  host.addEventListener("wheel", block, { passive: false }); host.addEventListener("touchmove", block, { passive: false });
  addEventListener("keydown", onKey, true);
  const onResize = () => p.size(); addEventListener("resize", onResize);
  let hover = false;
  host.addEventListener("pointermove", (e) => { const r = host.getBoundingClientRect(), b = ov.btn; const x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height; hover = dead && x > b.x && x < b.x + b.w && y > b.y && y < b.y + b.h; });
  btn.addEventListener("click", respawn);
  host.addEventListener("click", (e) => { if (dead && hover) respawn(); });
  function place() { const b = ov.btn; btn.style.left = b.x * 100 + "%"; btn.style.top = b.y * 100 + "%"; btn.style.width = b.w * 100 + "%"; btn.style.height = b.h * 100 + "%"; }
  function fire(t) {
    for (const s of cut.sounds || []) {
      if (s[0] > prev && s[0] <= t) {
        log.push([+s[0].toFixed(2), s[1]]);
        try { if (s[1] === "@muffle") audio.muffle(s[2][0], s[2][1]); else audio.play(s[1], s[2] || {}); } catch (e) { /* ignore */ }
      }
    }
    prev = t;
  }
  function frame(now) {
    if (over) return;
    raf = requestAnimationFrame(frame);
    const t = (now - t0) / 1000;
    fire(t);
    const f = renderAt(t, score);
    if (!dead && t >= cut.dur + 0.9) { dead = true; host.classList.add("qfs-dead"); place(); try { btn.focus({ preventScroll: true }); } catch (e) { /* ignore */ } }
    ov.draw({ ...f, btnHover: hover }, Math.min(t, cut.dur));
    try { audio.updateListener(p.stage.camera); } catch (e) { /* ignore */ }
  }
  function respawn() {
    if (over || !dead) return;
    over = true; cancelAnimationFrame(raf);
    try { audio.play("random.orb", { volume: 0.6 }); audio.muffle(20000, 0.2); } catch (e) { /* ignore */ }
    host.style.transition = "opacity .45s"; host.style.opacity = "0";
    setTimeout(() => {
      removeEventListener("keydown", onKey, true); removeEventListener("resize", onResize);
      p.dispose(); running = null;
      if (kr && kr.takeover) try { kr.takeover(false); } catch (e) { /* ignore */ }
      if (onDone) onDone();
    }, 480);
  }
  raf = requestAnimationFrame(frame);
}

// ---- verification: one frame of a scare into the dump -------------------------------------------------
async function dumpMode(id, atMs) {
  const p = await prepare(id, {});
  const t = (atMs || 0) / 1000;
  const log = [];
  for (const s of p.cut.sounds || []) if (s[0] <= t) log.push([s[0], s[1]]);
  const f = p.renderAt(t, 37);
  p.ov.draw(f, Math.min(t, p.cut.dur));
  const out = document.createElement("canvas"); out.width = p.stage.canvas.width; out.height = p.stage.canvas.height;
  const x = out.getContext("2d"); x.drawImage(p.stage.canvas, 0, 0); x.imageSmoothingEnabled = false; x.drawImage(p.ov.canvas, 0, 0, out.width, out.height);
  const png = out.toDataURL("image/png");
  const info = { scare: id, at: atMs, dur: p.cut.dur, hits: p.hits, sfx: log, hp: f.hp };
  const put = (tries) => {
    const old = document.getElementById("dumpshot");
    if (!old && tries < 60) { setTimeout(() => put(tries + 1), 250); return; }
    let base = {};
    if (old) { try { base = JSON.parse(old.textContent); } catch (e) { base = {}; } old.remove(); }
    const sc = document.createElement("script"); sc.type = "application/json"; sc.id = "dumpshot";
    sc.textContent = JSON.stringify({ ...base, png, ...info });
    document.body.appendChild(sc);
  };
  put(0);
}

// ---- the director's loop --------------------------------------------------------------------------------
export function initScares(opts = {}) {
  const enabled = opts.enabled || (() => true);
  const forced = canon(QS.get("scare"));
  const phone = matchMedia("(max-width: 700px)").matches || matchMedia("(pointer: coarse)").matches;
  if (forced) {
    if (DUMP) dumpMode(forced, Number(QS.get("at")) || 0).catch((e) => { console.error("scare dump", e); });
    else setTimeout(async () => { try { await play(await prepare(forced, { phone }), { score: 0 }); } catch (e) { console.error("scare", e); } }, 1200);
    return;
  }
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;   // accessibility: never trigger
  const director = createDirector({ done: readSession() });
  let acc = 0, lastSec = 0, lastS = null, lastInput = 0, last = performance.now(), pending = null, waited = 0, busy = false;
  const poke = () => { lastInput = performance.now(); };
  addEventListener("wheel", poke, { passive: true }); addEventListener("keydown", poke); addEventListener("pointermove", (e) => { if (e.buttons) poke(); }, { passive: true }); addEventListener("touchmove", poke, { passive: true });
  window.__scares = { director, force: (m) => { const id = canon(m); if (id) prepare(id, { phone }).then((p) => play(p)); }, get active() { return acc; } };

  async function arm() {
    const id = director.pick(MOBS);
    if (!id) return;
    busy = true; waited = 0;
    try { pending = { id, p: await prepare(id, { phone }) }; pending.p.host.style.display = "none"; }
    catch (e) { console.error("scare prepare", e); pending = null; busy = false; }
  }
  function cornerNear(kr, s) {
    if (!kr || !kr.corners) return true;
    return kr.corners.some((k) => k.s > s && k.s - s < 0.015) || false;
  }
  setInterval(() => {
    const now = performance.now(), dt = Math.min(0.5, (now - last) / 1000); last = now;
    if (running || document.hidden || !enabled()) return;
    const kr = krypt(); let moving, depth;
    if (kr && kr.getWalk) {
      const w = kr.getWalk(); moving = lastS != null && Math.abs(w.s - lastS) > 0.00003; lastS = w.s; depth = w.depth != null ? w.depth : w.s;
    } else { moving = now - lastInput < 500; depth = Math.min(1, acc / 120); }
    if (moving) acc += dt;
    if (!pending && !busy) {
      const sec = Math.floor(acc);
      if (sec > lastSec) { lastSec = sec; if (director.second(sec, depth)) arm(); }
    } else if (pending && moving) {
      waited += dt;
      const s = kr && kr.getWalk ? kr.getWalk().s : 0;
      if (cornerNear(kr, s) || waited > 8) {
        const { id, p } = pending; pending = null; busy = false;
        director.fired(acc, id); writeSession(director.done);
        p.host.style.display = ""; p.size();
        play(p, { score: Math.floor(acc), onDone: () => { lastS = null; } });
      }
    }
  }, 100);
}

export { MOBS, CFG };
