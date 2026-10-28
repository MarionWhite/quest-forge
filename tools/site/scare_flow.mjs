// The Krypt scares, played live the way the owner plays them (J, a click, the death screen, Enter), in one headless
// Chrome, with the checks a person would make by ear:
//   - every scare enters, runs, reaches the death screen and comes back; no exception on the page;
//   - frame pacing (fps, the worst gap, the gap around the lunge: the scare clock is wall time, so a gap is a hitch);
//   - LEAKS: at the death screen (dur + 3.3 s, after every loop's end and fade-out) no loop a scare started is still
//     sounding, and 0.9 s after Enter no sound a scare started is (qfaudio's voices(), tagged "scare" by scares.js).
//     Both are measured on the audio clock (a voice's age), so a loaded machine whose audio lags wall time does not
//     read as a leak: a loop gets 3 audio seconds more to finish its fade, a voice after Enter 0.9;
//   - --mood: every mood event (Shift+M's list) fired in turn; 4 s after it ends nothing it started still loops.
//   - THE J-PRESS WATCH: every frame the page renders from the click to 1.6 s into the scare (round 8b, the owner: "the
//     mob will flash on the screen in front of me, and disappear"). It fails when anything of the rig is on screen
//     before the scare's first frame; when a mob is drawn where its script did not put it (its box as drawn, from the
//     matrices the renderer used, against its box as placed); when a mob is on in the first frame or two and then gone
//     for four frames; and when any other mob (a mob texture outside the rig) is in view. --shots DIR saves those
//     frames (and a sample of the rest) as JPEGs.
// It fails loudly: a leak, an exception, a scare that never came back, exits 1 with the reason on stderr.
//
//   node tools/site/scare_flow.mjs [--base http://127.0.0.1:8000] [--page "graves/?demo&at=0.3"]
//        [--only Silverfish,Blaze] [--mood] [--out flow.json] [--size 1366,900] [--repeat 3] [--shots DIR] [--dice N]
// --dice N: every play rolls the dice N (scares.js takes them from Math.random as it builds), to replay one variant.
// The JSON (--out) holds per scare the voices it started and stopped on the scare clock: [t, "+"|"-", name, loop].
// One Chrome at a time on this machine (other agents render too). Needs a server on site/ (tools/site/serve.py).
import { spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : d; };
const base = opt("--base", "http://127.0.0.1:8000").replace(/\/$/, "");
const page = opt("--page", "graves/?demo&at=0.3");
const only = (opt("--only", "") || "").split(",").map((s) => s.trim()).filter(Boolean);
const mood = args.includes("--mood");
const outFile = opt("--out", null);
const size = opt("--size", "1366,900");
const repeat = Math.max(1, Number(opt("--repeat", "1")) || 1);
const shotsDir = opt("--shots", null);
const dice = opt("--dice", null);
const CHROME = process.env.CHROME || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

// ---- in the page ---------------------------------------------------------------------------------------------------
const inPage = async (ONLY, MOOD, REPEAT, SHOTS, DICE) => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const key = (k) => dispatchEvent(new KeyboardEvent("keydown", { key: k, bubbles: true, cancelable: true }));
  for (let i = 0; i < 150 && !(window.__scares && window.__krypt && window.__krypt.camera); i++) await sleep(200);
  if (!window.__scares) return { error: "no window.__scares (the Krypt did not boot)" };
  const V = () => (typeof window.__scares.voices === "function" ? window.__scares.voices() : null);
  if (!V()) return { error: "no __scares.voices(): qfaudio has no voice registry, so leaks cannot be checked" };
  await sleep(2500);
  const BED = /^(music\.|qf\.krypt\.|ambient\.)/;   // the Krypt's own beds: never a scare's or the mood's
  const out = { list: window.__scares.list.map((s) => s.id), runs: [], mood: [], sawScareVoice: false, watch: true };
  // ---- the J-press watch ----------------------------------------------------------------------------------------------
  const kr = window.__krypt;
  const WT = { on: false, t0: 0, frames: [], shots: [], hit: null, n: 0 };
  let THREE = null;
  try { THREE = await import("three"); } catch (e) { out.watch = false; }
  if (THREE && kr.scene && kr.composer) {
    const fr = new THREE.Frustum(), pm = new THREE.Matrix4(), box = new THREE.Box3(), v = new THREE.Vector3();
    const shown = (o) => { for (let p = o; p; p = p.parent) { if (!p.visible) return false; if (p === kr.scene) return true; } return false; };
    // The box of what was DRAWN: each visible mesh's geometry box under the matrixWorld it was drawn with (not
    // Box3.setFromObject, which brings the matrices up to date first and so sees where the script put it, not where
    // the renderer drew it).
    const gb = new THREE.Box3();
    const drawnBox = (o) => {
      box.makeEmpty();
      o.traverseVisible((m) => {
        if (!m.isMesh || !m.geometry) return;
        if (!m.geometry.boundingBox) m.geometry.computeBoundingBox();
        if (m.isInstancedMesh) { if (!m.count) return; if (!m.boundingBox) m.computeBoundingBox(); if (!m.boundingBox) return; gb.copy(m.boundingBox); } else gb.copy(m.geometry.boundingBox);
        if (gb.isEmpty()) return;
        box.union(gb.applyMatrix4(m.matrixWorld));
      });
      return box;
    };
    // How much of the screen an object's box covers (0..1), or 0 off screen.
    const cover = (o, cam) => {
      drawnBox(o); if (box.isEmpty() || !isFinite(box.min.x) || !fr.intersectsBox(box)) return 0;
      let x0 = 1, x1 = -1, y0 = 1, y1 = -1, behind = false;
      for (let i = 0; i < 8; i++) {
        v.set(i & 1 ? box.max.x : box.min.x, i & 2 ? box.max.y : box.min.y, i & 4 ? box.max.z : box.min.z);
        v.applyMatrix4(cam.matrixWorldInverse); if (v.z > -cam.near) { behind = true; continue; }
        v.applyMatrix4(cam.projectionMatrix);
        x0 = Math.min(x0, v.x); x1 = Math.max(x1, v.x); y0 = Math.min(y0, v.y); y1 = Math.max(y1, v.y);
      }
      if (behind) { x0 = -1; x1 = 1; y0 = Math.min(y0, -1); y1 = Math.max(y1, 1); }
      const w = Math.max(0, Math.min(1, x1) - Math.max(-1, x0)), h = Math.max(0, Math.min(1, y1) - Math.max(-1, y0));
      return (w * h) / 4;
    };
    const prevAfter = kr.scene.onAfterRender;
    kr.scene.onAfterRender = function (...a) {
      if (prevAfter) prevAfter.apply(this, a);
      if (!WT.on) return;
      const st = window.__scares.state, g = kr.scene.getObjectByName("scare"), cam = kr.camera;
      const rec = { ms: Math.round(performance.now() - WT.t0), started: !!(st && st.frames > 0), t: st && st.frames > 0 ? +st.t.toFixed(3) : null, on: [] };
      if (g && shown(g)) {
        cam.updateMatrixWorld(); pm.multiplyMatrices(cam.projectionMatrix, cam.matrixWorldInverse); fr.setFromProjectionMatrix(pm);
        for (const o of [...g.children, ...((g.getObjectByName("scare-view") || {}).children || [])]) {
          if (o.name === "scare-view" || !shown(o)) continue;
          const mob = o.userData.qfMob || (o.isGroup && o.rotation.order === "YXZ" && o.children.length === 1 && o.children[0].isGroup ? "mob?" : null);
          const c = cover(o, cam);
          if (c > 0.0005) {
            // Drawn where the script put it? (the script's place: the matrices brought up to date)
            const dc = box.getCenter(v).clone(); box.setFromObject(o); const nc = box.getCenter(v);
            const stale = box.isEmpty() || !fr.intersectsBox(box) || dc.distanceTo(nc) > 0.5;
            rec.on.push([mob || o.name || o.type, +c.toFixed(4), o.uuid.slice(0, 6), !!mob, stale]);
            if (stale) rec.stale = true;
          }
        }
      }
      // Any other mob in view (the mood layer's, a leftover rig): a mob texture on a visible mesh outside this rig.
      if (!rec.started || rec.t < 0.4) {
        if (!(g && shown(g))) { cam.updateMatrixWorld(); pm.multiplyMatrices(cam.projectionMatrix, cam.matrixWorldInverse); fr.setFromProjectionMatrix(pm); }
        const seen = new Set();
        kr.scene.traverseVisible((o) => {
          if (!o.isMesh || seen.size > 6) return;
          for (let p = o; p; p = p.parent) if (p === g) return;
          const ms = Array.isArray(o.material) ? o.material : [o.material];
          const src = (ms.find((m) => m && m.map && m.map.image && /\/(entity|mobs|mobs-local)\//.test(m.map.image.src || "")) || {}).map;
          if (!src) return;
          if (!o.geometry.boundingBox) o.geometry.computeBoundingBox();
          box.copy(o.geometry.boundingBox).applyMatrix4(o.matrixWorld); if (box.isEmpty() || !fr.intersectsBox(box)) return;
          let top = o; while (top.parent && top.parent !== kr.scene) top = top.parent;
          const k = (top.name || top.type) + ":" + src.image.src.split("/").slice(-2).join("/");
          if (!seen.has(k)) { seen.add(k); rec.on.push(["other " + k, 0, top.uuid.slice(0, 6), true]); rec.other = true; }
        });
      }
      WT.frames.push(rec); WT.hit = rec;
    };
    const comp = kr.composer, orig = comp.render;
    comp.render = function (...a) {
      WT.hit = null;
      const r = orig.apply(this, a);
      const rec = WT.hit;
      if (SHOTS && WT.on && rec && WT.shots.length < 60) {
        WT.n++;
        const pre = !rec.started;
        if ((pre && (rec.on.length || WT.n % 8 === 1)) || (!pre && rec.t < 0.35 && WT.shots.filter((x) => x.started).length < 10)) {
          const gl = kr.renderer.domElement, c = document.createElement("canvas"); c.width = 384; c.height = Math.round(384 * gl.height / gl.width);
          c.getContext("2d").drawImage(gl, 0, 0, c.width, c.height);
          WT.shots.push({ ms: rec.ms, started: rec.started, t: rec.t, on: rec.on.map((x) => x[0]).join(" "), jpg: c.toDataURL("image/jpeg", 0.72) });
        }
      }
      return r;
    };
  } else out.watch = false;
  // The verdict on one run's frames: anything of the rig on screen before its first frame; a mob that blinks on and off.
  const judge = () => {
    const pre = WT.frames.filter((f) => !f.started), post = WT.frames.filter((f) => f.started && f.t <= 1.5);
    const preOn = pre.filter((f) => f.on.length);
    const others = WT.frames.filter((f) => f.other).slice(0, 4).map((f) => ({ ms: f.ms, t: f.t, on: f.on.filter((x) => /^other /.test(x[0])).map((x) => x[0]) }));
    // A mob drawn somewhere its script did not put it (a frame behind), and a mob on in the first frame or two and
    // then gone for a while (counted in frames, so a slow machine does not hide it).
    const stale = post.filter((f) => f.stale).map((f) => ({ ms: f.ms, t: f.t, on: f.on.filter((x) => x[4]).map((x) => x[0] + " " + (x[1] * 100).toFixed(1) + "%") }));
    const blinks = [];
    const ids = new Set(post.flatMap((f) => f.on.filter((x) => x[3]).map((x) => x[2])));
    for (const u of ids) {
      const on = post.map((f) => f.on.some((x) => x[2] === u));
      const i0 = on.indexOf(true); if (i0 < 0 || i0 > 1) continue;
      let i1 = i0; while (i1 < on.length && on[i1]) i1++;
      if (i1 - i0 > 2) continue;
      let i2 = i1; while (i2 < on.length && !on[i2]) i2++;
      if (i2 - i1 >= 4 && (post[Math.min(i2, post.length - 1)].t - post[i1 - 1].t) >= 0.3) blinks.push({ uuid: u, name: post[i0].on.find((x) => x[2] === u)[0], on: post[i0].t, off: post[i1 - 1].t });
    }
    const brief = (f) => ({ ms: f.ms, t: f.t, on: f.on.map((x) => x[0] + " " + (x[1] * 100).toFixed(1) + "%") });
    return { first: [...pre.slice(-4), ...post.slice(0, 12)].map(brief), others, stale: stale.slice(0, 4), preFrames: pre.length, preOn: preOn.length, preOnFirst: preOn.slice(0, 6).map((f) => ({ ms: f.ms, on: f.on })), startFrames: post.length, blinks, shots: WT.shots.slice() };
  };
  const list = [];
  for (let k = 0; k < REPEAT; k++) list.push(...window.__scares.list.map((s) => ({ s, k })));
  for (const { s, k: rep } of list) {
    const id = s.id;
    if (ONLY.length && !ONLY.some((o) => o.toLowerCase() === id.toLowerCase())) continue;
    // (a scare still running, on a slow machine: let it finish before the next J, up to two minutes)
    for (let i = 0; i < 1200 && window.__scares.busy; i++) await sleep(100);
    const base = new Set(V().map((v) => v.id));
    key("j"); await sleep(350);
    console.info("scareflow: " + id + " start");
    const btn = [...document.querySelectorAll(".qfs-pick button")].find((b) => b.textContent.includes(s.label));
    if (!btn) { out.runs.push({ id, error: "no picker button for " + s.label }); key("Escape"); continue; }
    const tClick = performance.now();
    WT.frames = []; WT.shots = []; WT.n = 0; WT.t0 = tClick; WT.on = true;
    const rnd0 = Math.random;
    if (DICE != null) Math.random = () => (DICE >>> 0) / 4294967296;
    btn.click();
    let first = null, lastF = 0, lastFAt = 0, maxGap = 0, maxGapAt = 0, lungeGap = 0, st = null, entered = false, marks = null, dur = null, frames = 0, tEnd = 0, t = 0;
    const seen = new Map(), events = [];
    let deadLoops = null, lastGapS = 0, dl = null, lastF0 = 0;
    let news = performance.now();
    while (performance.now() - tClick < 240000) {
      await sleep(25);
      const now = performance.now();
      st = window.__scares.state;
      if (st) t = st.t;
      if (now - news > 20000 && st && st.frames > lastF0) { news = now; lastF0 = st.frames; console.info("scareflow: " + id + " t=" + t.toFixed(1)); }   // alive (the stall watchdog)
      // The sound log: every voice a scare started, when it started and stopped, on the scare clock.
      const vs = V(), ids = new Set();
      for (const v of vs) {
        if (v.tag !== "scare") continue;
        ids.add(v.id);
        if (!seen.has(v.id)) { seen.set(v.id, v); events.push([+t.toFixed(2), "+", v.name, v.loop]); out.sawScareVoice = true; }
      }
      for (const [k, v] of seen) if (!ids.has(k) && !v.gone) { v.gone = true; events.push([+t.toFixed(2), "-", v.name, v.loop]); }
      if (!st) { if (first != null) break; if (now - tClick > 15000) { out.runs.push({ id, error: "the scare never started (15 s after the click)" }); break; } continue; }
      if (st.frames > 0 && first == null) { first = Math.round(now - tClick); lastF = st.frames; lastFAt = now; Math.random = rnd0; }
      if (WT.on && st.frames > 0 && st.t > 1.6) WT.on = false;
      marks = st.marks; dur = st.dur;
      if (st.frames !== lastF) {
        const g = now - lastFAt;
        lastGapS = Math.max(lastGapS * 0.8, g / 1000);
        if (g > maxGap) { maxGap = g; maxGapAt = st.t; }
        if (marks && st.t > marks.lunge - 0.6 && st.t < marks.lunge + 0.4 && g > lungeGap) lungeGap = g;
        lastF = st.frames; lastFAt = now; frames = st.frames; tEnd = st.t;
      }
      // The death screen, after every loop's end and fade: nothing a scare started may still loop.
      // (on a loaded machine the stop comes a frame late and the audio thread falls behind wall time, so a loop
      // still fading here gets up to 3 s more; one that was never stopped is still there then)
      // A loop still there is given 3 s more of AUDIO time (and of wall time) to finish its fade; one never stopped is
      // still there then.
      if (dur != null && st.t >= dur + 3.3 + Math.min(2, 2 * lastGapS) && !entered) {
        const loops = vs.filter((v) => v.tag === "scare" && v.loop);
        if (!dl) dl = { w: now, a: new Map() };
        for (const v of loops) if (!dl.a.has(v.id)) dl.a.set(v.id, v.age);
        const stuck = loops.filter((v) => v.age - dl.a.get(v.id) >= 3);
        if (!loops.length || (stuck.length && now - dl.w >= 3000) || now - dl.w > 15000) { deadLoops = (stuck.length ? stuck : loops).map((v) => v.name); entered = true; key("Enter"); }
      }
    }
    WT.on = false; Math.random = rnd0;
    const watch = judge();
    if (first == null) continue;
    // After Enter every scare voice must be gone within 0.9 s of AUDIO time (Enter stops them with a 0.2 s fade). On a
    // loaded machine the audio clock and the page's events fall behind wall time, so this waits on the audio clock
    // (a voice's age), up to 12 s of wall time: a voice still there 0.9 audio seconds on is a leak.
    const tw = performance.now(), base0 = new Map();
    let late = [];
    await sleep(900);
    for (;;) {
      const vs = V().filter((v) => v.tag === "scare");
      for (const v of vs) if (!base0.has(v.id)) base0.set(v.id, v.age);
      late = vs.filter((v) => v.age - base0.get(v.id) >= 0.9);
      if (!vs.length || (late.length && performance.now() - tw > 2500) || performance.now() - tw > 12000) { if (!late.length && vs.length) late = vs; break; }
      await sleep(100);
    }
    const after = V();
    const afterEnter = late.map((v) => v.name + (v.loop ? " (loop)" : ""));
    const strays = after.filter((v) => v.tag !== "scare" && v.loop && !base.has(v.id) && !BED.test(v.name)).map((v) => v.name);
    const leak = (deadLoops && deadLoops.length) || afterEnter.length || strays.length;
    out.runs.push({ id, rep, watch, firstFrameMs: first, dur: dur && +dur.toFixed(2), frames, fps: tEnd ? +(frames / tEnd).toFixed(1) : 0,
      maxGapMs: Math.round(maxGap), maxGapAt: +maxGapAt.toFixed(2), lungeGapMs: Math.round(lungeGap), lunge: marks && +marks.lunge.toFixed(2),
      entered, back: !window.__scares.busy, voices: seen.size, deadLoops, afterEnter, strays, leak: !!leak, marks, events });
  }
  if (MOOD && window.__mood && typeof window.__mood.trigger === "function") {
    console.info("scareflow: mood events");
    const kinds = Array.isArray(window.__mood.kinds) ? window.__mood.kinds : Object.keys(window.__mood.kinds || {});
    for (const kind of kinds) {
      for (let i = 0; i < 200 && window.__mood.busy; i++) await sleep(100);
      const base = new Set(V().map((v) => v.id));
      let ok = false;
      try { ok = !!window.__mood.trigger(kind); } catch (e) { out.mood.push({ kind, error: String(e) }); continue; }
      console.info("scareflow: mood " + kind);
      if (!ok) { out.mood.push({ kind, fired: false }); continue; }
      const t0 = performance.now();
      while (window.__mood.busy && performance.now() - t0 < 30000) await sleep(100);
      const ran = +((performance.now() - t0) / 1000).toFixed(1);
      await sleep(4000);
      const left = V().filter((v) => !base.has(v.id) && !BED.test(v.name));
      out.mood.push({ kind, fired: true, ran, loopsLeft: left.filter((v) => v.loop).map((v) => v.name), stillSounding: left.filter((v) => !v.loop).map((v) => v.name + " " + v.age + "s"), leak: left.some((v) => v.loop) });
    }
  }
  return out;
};

// ---- the driver ----------------------------------------------------------------------------------------------------
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const port = 9300 + Math.floor(Math.random() * 500);
const prof = fs.mkdtempSync(path.join(os.tmpdir(), "qf-scareflow-"));
const chrome = spawn(CHROME, ["--headless=new", "--no-first-run", "--mute-audio", `--user-data-dir=${prof}`, `--remote-debugging-port=${port}`, `--window-size=${size}`, "--autoplay-policy=no-user-gesture-required", "about:blank"], { stdio: "ignore" });
const done = (code) => { try { chrome.kill(); } catch (e) { /* gone */ } try { fs.rmSync(prof, { recursive: true, force: true }); } catch (e) { /* ignore */ } process.exit(code); };
process.on("SIGINT", () => done(130));
let tabs = [];
for (let i = 0; i < 60; i++) { try { tabs = await (await fetch(`http://127.0.0.1:${port}/json`)).json(); if (tabs.length) break; } catch (e) { /* not up */ } await sleep(200); }
const tab = tabs.find((t) => t.type === "page");
if (!tab) { console.error("scare_flow: Chrome did not start"); done(2); }
const ws = new WebSocket(tab.webSocketDebuggerUrl);
await new Promise((r) => (ws.onopen = r));
let id = 0; const pend = new Map(); const exc = [], warns = [];
// A page that stops reporting (a renderer crash, a hung frame) fails the run instead of hanging it: one scare and its
// death screen take well under two minutes even on a busy machine.
let lastNews = Date.now();
setInterval(() => { if (Date.now() - lastNews > 150000) { console.error("SCARE FLOW FAILED: the page stopped reporting for 150 s" + (exc.length ? ": " + exc.slice(-2).join(" | ") : "")); done(3); } }, 5000).unref();
ws.onmessage = (m) => {
  const d = JSON.parse(m.data);
  if (d.id && pend.has(d.id)) { pend.get(d.id)(d); pend.delete(d.id); return; }
  if (d.method === "Runtime.exceptionThrown") exc.push(d.params.exceptionDetails.exception?.description || d.params.exceptionDetails.text);
  else if (d.method === "Runtime.consoleAPICalled") {
    const txt = d.params.args.map((a) => a.value ?? a.description).join(" ");
    if (d.params.type === "error") exc.push("console.error: " + txt);
    else if (d.params.type === "warning" && /qfaudio|scare/i.test(txt)) warns.push(txt);
    else if (d.params.type === "info" && txt.startsWith("scareflow: ")) { lastNews = Date.now(); process.stderr.write(txt.slice(11) + "\n"); }   // progress
  }
};
const send = (method, params = {}) => new Promise((r) => { const i = ++id; pend.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
await send("Runtime.enable"); await send("Page.enable");
const [w, h] = size.split(",").map(Number);
await send("Emulation.setDeviceMetricsOverride", { width: w, height: h, deviceScaleFactor: 1, mobile: w < 700 });
await send("Page.navigate", { url: `${base}/${page}` });
await sleep(1500);
const r = await send("Runtime.evaluate", { expression: `(${inPage.toString()})(${JSON.stringify(only)}, ${mood}, ${repeat}, ${!!shotsDir}, ${dice == null ? "null" : Number(dice)})`, awaitPromise: true, returnByValue: true, timeout: 1500000 * repeat });
const res = r.result?.result?.value ?? { error: JSON.stringify(r.result?.exceptionDetails || r.error || r).slice(0, 400) };
// The J-press frames to disk (DIR/<scare>_<rep>_<ms>[_pre].jpg), out of the JSON.
if (shotsDir) {
  fs.mkdirSync(shotsDir, { recursive: true });
  for (const x of res.runs || []) for (const sh of (x.watch && x.watch.shots) || []) {
    const fn = `${x.id}_${x.rep}_${String(sh.ms).padStart(5, "0")}${sh.started ? "_t" + Math.round(sh.t * 1000) : "_pre"}${sh.on ? "_ON" : ""}.jpg`;
    fs.writeFileSync(path.join(shotsDir, fn), Buffer.from(sh.jpg.split(",")[1], "base64"));
  }
}
for (const x of res.runs || []) if (x.watch) x.watch.shots = (x.watch.shots || []).length;
const report = { url: `${base}/${page}`, at: new Date().toISOString(), ...res, exceptions: exc, warnings: warns };
if (outFile) fs.writeFileSync(outFile, JSON.stringify(report, null, 1));

// ---- the verdict ---------------------------------------------------------------------------------------------------
const fails = [];
if (res.error) fails.push(res.error);
for (const x of res.runs || []) {
  const bad = [];
  if (x.error) bad.push(x.error);
  if (!x.entered) bad.push("never reached the death screen");
  if (!x.back) bad.push("never came back after Enter");
  if (x.deadLoops && x.deadLoops.length) bad.push("LEAK at the death screen: " + x.deadLoops.join(", "));
  if (x.afterEnter && x.afterEnter.length) bad.push("LEAK after Enter: " + x.afterEnter.join(", "));
  if (x.strays && x.strays.length) bad.push("LEAK, a loop no scare tagged: " + x.strays.join(", "));
  const w = x.watch;
  if (w && w.preOn) bad.push(`FLASH: the rig on screen in ${w.preOn} of ${w.preFrames} frame(s) before the scare's first frame (${w.preOnFirst.map((f) => f.ms + " ms " + f.on.map((o) => o[0] + " " + (o[1] * 100).toFixed(1) + "%").join(", ")).join("; ")})`);
  if (w && w.others && w.others.length) bad.push("FLASH: another mob in view in the first frames: " + w.others.map((f) => `${f.ms} ms ${f.on.join(", ")}`).join("; "));
  if (w && w.stale && w.stale.length) bad.push("FLASH: a mob drawn where its script did not put it (a frame behind): " + w.stale.map((f) => `t ${f.t} ${f.on.join(", ")}`).join("; "));
  if (w && w.blinks.length) bad.push("FLASH: a mob on and off in the first frames: " + w.blinks.map((b) => `${b.name} ${b.on}-${b.off} s`).join(", "));
  console.log(`${(x.id || "?").padEnd(15)}${repeat > 1 ? " #" + x.rep : ""} pre ${w ? String(w.preFrames).padStart(3) : "  ?"} dur ${String(x.dur).padEnd(6)} fps ${String(x.fps).padEnd(5)} gap ${String(x.maxGapMs).padStart(4)} ms (lunge ${String(x.lungeGapMs).padStart(3)})  voices ${String(x.voices).padStart(3)}  ${bad.length ? "FAIL: " + bad.join("; ") : "ok"}`);
  if (bad.length) fails.push(`${x.id}: ${bad.join("; ")}`);
}
for (const m of res.mood || []) {
  const bad = m.error ? [m.error] : m.leak ? ["LEAK: " + m.loopsLeft.join(", ")] : [];
  console.log(`mood ${m.kind.padEnd(16)} ${m.fired === false ? "no place for it here" : `ran ${m.ran} s` + (m.stillSounding && m.stillSounding.length ? `, still sounding 4 s on: ${m.stillSounding.join(", ")}` : "")}  ${bad.length ? "FAIL: " + bad.join("; ") : "ok"}`);
  if (bad.length) fails.push(`mood ${m.kind}: ${bad.join("; ")}`);
}
if ((res.runs || []).length && res.watch === false) fails.push("the J-press watch could not hook the renderer, so flashes were not checked");
if ((res.runs || []).length && !res.sawScareVoice) fails.push("no scare voice was ever heard: the AudioContext never ran, so the leak check proved nothing");
if (exc.length) fails.push(`${exc.length} exception(s): ${exc.slice(0, 3).join(" | ").slice(0, 600)}`);
if (warns.length) console.log("warnings: " + [...new Set(warns)].slice(0, 6).join(" | "));
if (fails.length) { console.error("\nSCARE FLOW FAILED\n  " + fails.join("\n  ")); done(1); }
console.log(`\nscare flow ok: ${(res.runs || []).length} scare run(s)${mood ? `, ${(res.mood || []).length} mood event(s)` : ""}, no flashes, no leaks, no exceptions`);
done(0);
