// The Krypt scares, played live the way the owner plays them (J, a click, the death screen, Enter), in one headless
// Chrome, with the checks a person would make by ear:
//   - every scare enters, runs, reaches the death screen and comes back; no exception on the page;
//   - frame pacing (fps, the worst gap, the gap around the lunge: the scare clock is wall time, so a gap is a hitch);
//   - LEAKS: at the death screen (dur + 3.3 s, after every loop's end and fade-out) no loop a scare started is still
//     sounding, and 0.9 s after Enter no sound a scare started is (qfaudio's voices(), tagged "scare" by scares.js);
//   - --mood: every mood event (Shift+M's list) fired in turn; 4 s after it ends nothing it started still loops.
// It fails loudly: a leak, an exception, a scare that never came back, exits 1 with the reason on stderr.
//
//   node tools/site/scare_flow.mjs [--base http://127.0.0.1:8000] [--page "graves/?demo&at=0.3"]
//        [--only Silverfish,Blaze] [--mood] [--out flow.json] [--size 1366,900]
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
const CHROME = process.env.CHROME || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

// ---- in the page ---------------------------------------------------------------------------------------------------
const inPage = async (ONLY, MOOD) => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const key = (k) => dispatchEvent(new KeyboardEvent("keydown", { key: k, bubbles: true, cancelable: true }));
  for (let i = 0; i < 150 && !(window.__scares && window.__krypt && window.__krypt.camera); i++) await sleep(200);
  if (!window.__scares) return { error: "no window.__scares (the Krypt did not boot)" };
  const V = () => (typeof window.__scares.voices === "function" ? window.__scares.voices() : null);
  if (!V()) return { error: "no __scares.voices(): qfaudio has no voice registry, so leaks cannot be checked" };
  await sleep(2500);
  const BED = /^(music\.|qf\.krypt\.|ambient\.)/;   // the Krypt's own beds: never a scare's or the mood's
  const out = { list: window.__scares.list.map((s) => s.id), runs: [], mood: [], sawScareVoice: false };
  for (const s of window.__scares.list) {
    const id = s.id;
    if (ONLY.length && !ONLY.some((o) => o.toLowerCase() === id.toLowerCase())) continue;
    for (let i = 0; i < 100 && window.__scares.busy; i++) await sleep(100);
    const base = new Set(V().map((v) => v.id));
    key("j"); await sleep(350);
    const btn = [...document.querySelectorAll(".qfs-pick button")].find((b) => b.textContent.includes(s.label));
    if (!btn) { out.runs.push({ id, error: "no picker button for " + s.label }); key("Escape"); continue; }
    const tClick = performance.now();
    btn.click();
    let first = null, lastF = 0, lastFAt = 0, maxGap = 0, maxGapAt = 0, lungeGap = 0, st = null, entered = false, marks = null, dur = null, frames = 0, tEnd = 0, t = 0;
    const seen = new Map(), events = [];
    let deadLoops = null;
    while (performance.now() - tClick < 80000) {
      await sleep(25);
      const now = performance.now();
      st = window.__scares.state;
      if (st) t = st.t;
      // The sound log: every voice a scare started, when it started and stopped, on the scare clock.
      const vs = V(), ids = new Set();
      for (const v of vs) {
        if (v.tag !== "scare") continue;
        ids.add(v.id);
        if (!seen.has(v.id)) { seen.set(v.id, v); events.push([+t.toFixed(2), "+", v.name, v.loop]); out.sawScareVoice = true; }
      }
      for (const [k, v] of seen) if (!ids.has(k) && !v.gone) { v.gone = true; events.push([+t.toFixed(2), "-", v.name, v.loop]); }
      if (!st) { if (first != null) break; continue; }
      if (st.frames > 0 && first == null) { first = Math.round(now - tClick); lastF = st.frames; lastFAt = now; }
      marks = st.marks; dur = st.dur;
      if (st.frames !== lastF) {
        const g = now - lastFAt;
        if (g > maxGap) { maxGap = g; maxGapAt = st.t; }
        if (marks && st.t > marks.lunge - 0.6 && st.t < marks.lunge + 0.4 && g > lungeGap) lungeGap = g;
        lastF = st.frames; lastFAt = now; frames = st.frames; tEnd = st.t;
      }
      // The death screen, after every loop's end and fade: nothing a scare started may still loop.
      if (dur != null && st.t >= dur + 3.3 && !entered) {
        deadLoops = vs.filter((v) => v.tag === "scare" && v.loop).map((v) => v.name);
        entered = true; key("Enter");
      }
    }
    await sleep(900);
    const after = V();
    const afterEnter = after.filter((v) => v.tag === "scare").map((v) => v.name + (v.loop ? " (loop)" : ""));
    const strays = after.filter((v) => v.tag !== "scare" && v.loop && !base.has(v.id) && !BED.test(v.name)).map((v) => v.name);
    const leak = (deadLoops && deadLoops.length) || afterEnter.length || strays.length;
    out.runs.push({ id, firstFrameMs: first, dur: dur && +dur.toFixed(2), frames, fps: tEnd ? +(frames / tEnd).toFixed(1) : 0,
      maxGapMs: Math.round(maxGap), maxGapAt: +maxGapAt.toFixed(2), lungeGapMs: Math.round(lungeGap), lunge: marks && +marks.lunge.toFixed(2),
      entered, back: !window.__scares.busy, voices: seen.size, deadLoops, afterEnter, strays, leak: !!leak, marks, events });
  }
  if (MOOD && window.__mood && typeof window.__mood.trigger === "function") {
    const kinds = Array.isArray(window.__mood.kinds) ? window.__mood.kinds : Object.keys(window.__mood.kinds || {});
    for (const kind of kinds) {
      for (let i = 0; i < 200 && window.__mood.busy; i++) await sleep(100);
      const base = new Set(V().map((v) => v.id));
      let ok = false;
      try { ok = !!window.__mood.trigger(kind); } catch (e) { out.mood.push({ kind, error: String(e) }); continue; }
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
ws.onmessage = (m) => {
  const d = JSON.parse(m.data);
  if (d.id && pend.has(d.id)) { pend.get(d.id)(d); pend.delete(d.id); return; }
  if (d.method === "Runtime.exceptionThrown") exc.push(d.params.exceptionDetails.exception?.description || d.params.exceptionDetails.text);
  else if (d.method === "Runtime.consoleAPICalled") {
    const txt = d.params.args.map((a) => a.value ?? a.description).join(" ");
    if (d.params.type === "error") exc.push("console.error: " + txt);
    else if (d.params.type === "warning" && /qfaudio|scare/i.test(txt)) warns.push(txt);
  }
};
const send = (method, params = {}) => new Promise((r) => { const i = ++id; pend.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
await send("Runtime.enable"); await send("Page.enable");
const [w, h] = size.split(",").map(Number);
await send("Emulation.setDeviceMetricsOverride", { width: w, height: h, deviceScaleFactor: 1, mobile: w < 700 });
await send("Page.navigate", { url: `${base}/${page}` });
await sleep(1500);
const r = await send("Runtime.evaluate", { expression: `(${inPage.toString()})(${JSON.stringify(only)}, ${mood})`, awaitPromise: true, returnByValue: true, timeout: 1500000 });
const res = r.result?.result?.value ?? { error: JSON.stringify(r.result?.exceptionDetails || r.error || r).slice(0, 400) };
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
  console.log(`${(x.id || "?").padEnd(15)} dur ${String(x.dur).padEnd(6)} fps ${String(x.fps).padEnd(5)} gap ${String(x.maxGapMs).padStart(4)} ms (lunge ${String(x.lungeGapMs).padStart(3)})  voices ${String(x.voices).padStart(3)}  ${bad.length ? "FAIL: " + bad.join("; ") : "ok"}`);
  if (bad.length) fails.push(`${x.id}: ${bad.join("; ")}`);
}
for (const m of res.mood || []) {
  const bad = m.error ? [m.error] : m.leak ? ["LEAK: " + m.loopsLeft.join(", ")] : [];
  console.log(`mood ${m.kind.padEnd(16)} ${m.fired === false ? "no place for it here" : `ran ${m.ran} s` + (m.stillSounding && m.stillSounding.length ? `, still sounding 4 s on: ${m.stillSounding.join(", ")}` : "")}  ${bad.length ? "FAIL: " + bad.join("; ") : "ok"}`);
  if (bad.length) fails.push(`mood ${m.kind}: ${bad.join("; ")}`);
}
if ((res.runs || []).length && !res.sawScareVoice) fails.push("no scare voice was ever heard: the AudioContext never ran, so the leak check proved nothing");
if (exc.length) fails.push(`${exc.length} exception(s): ${exc.slice(0, 3).join(" | ").slice(0, 600)}`);
if (warns.length) console.log("warnings: " + [...new Set(warns)].slice(0, 6).join(" | "));
if (fails.length) { console.error("\nSCARE FLOW FAILED\n  " + fails.join("\n  ")); done(1); }
console.log(`\nscare flow ok: ${(res.runs || []).length} scare(s)${mood ? `, ${(res.mood || []).length} mood event(s)` : ""}, no leaks, no exceptions`);
done(0);
