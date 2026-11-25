// Tests the relay without touching GitHub.
//   node tools/shaders/relay/test/test_relay.mjs              in-process, fetch mocked
//   node tools/shaders/relay/test/test_relay.mjs --url http://127.0.0.1:8787 --mock-port 8799
//        against `wrangler dev` whose GITHUB_API points at the mock server this script starts.
import http from "node:http";
import fs from "node:fs";
import os from "node:os";
import {spawnSync} from "node:child_process";
import {fileURLToPath, pathToFileURL} from "node:url";
import path from "node:path";

const args = process.argv.slice(2);
const at = k => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : null; };
const LIVE = at("--url");
const MOCK_PORT = Number(at("--mock-port") || 8799);
const PASS = "test-passphrase-123";
const ORIGIN = "https://marionwhite.github.io";
const here = path.dirname(fileURLToPath(import.meta.url));

let created = [];          // issues the mock GitHub received
let labelMode = "ok";      // "ok" | "reject" (422 when labels are sent)
let committed = [];        // files the mock contents API received: {path, message, content}
let contentsMode = "ok";   // "ok" | "deny" (403, a token without Contents: write)
const CONTENTS = /\/repos\/MarionWhite\/quest-forge\/contents\/(.+)$/;
function github(method, url, headers, bodyText) {
  const cm = CONTENTS.exec(url);
  if (method === "PUT" && cm) {
    if (headers.authorization !== "Bearer dummy-token") return [401, {message: "Bad credentials"}];
    if (contentsMode === "deny") return [403, {message: "Resource not accessible by personal access token"}];
    const b = JSON.parse(bodyText);
    committed.push({path: cm[1], message: b.message, content: b.content});
    return [201, {content: {path: cm[1], html_url: `https://github.com/MarionWhite/quest-forge/blob/main/${cm[1]}`,
      download_url: `https://raw.githubusercontent.com/MarionWhite/quest-forge/main/${cm[1]}`}}];
  }
  if (method !== "POST" || !url.endsWith("/repos/MarionWhite/quest-forge/issues")) return [404, {message: "Not Found"}];
  if (headers.authorization !== "Bearer dummy-token") return [401, {message: "Bad credentials"}];
  const b = JSON.parse(bodyText);
  if (b.labels && labelMode === "reject") return [422, {message: "Validation Failed"}];
  created.push(b);
  return [201, {number: created.length, html_url: `https://github.com/MarionWhite/quest-forge/issues/${created.length}`}];
}

let call;
if (LIVE) {
  const srv = http.createServer((req, res) => {
    let s = ""; req.on("data", c => s += c); req.on("end", () => {
      const [st, j] = github(req.method, req.url, req.headers, s);
      res.writeHead(st, {"Content-Type": "application/json"}); res.end(JSON.stringify(j));
    });
  });
  await new Promise(r => srv.listen(MOCK_PORT, "127.0.0.1", r));
  let m = 0;
  call = async (p, init, ip) => { const h = new Headers(init.headers || {}); h.set("CF-Connecting-IP", ip || `10.1.0.${++m}`); return fetch(LIVE + p, {...init, headers: h}); };
  process.on("exit", () => srv.close());
} else {
  const worker = (await import(pathToFileURL(path.join(here, "..", "worker.js")).href)).default;
  globalThis.fetch = async (u, init) => {
    const hdr = {}; for (const [k, v] of Object.entries(init.headers || {})) hdr[k.toLowerCase()] = v;
    const [st, j] = github(init.method, u, hdr, init.body);
    return new Response(JSON.stringify(j), {status: st, headers: {"Content-Type": "application/json"}});
  };
  const env = {QF_PASSPHRASE: PASS, GITHUB_TOKEN: "dummy-token", GITHUB_API: "https://mock.invalid"};
  let n = 0;
  call = async (p, init, ip) => {
    const h = new Headers(init.headers || {}); h.set("CF-Connecting-IP", ip || `10.0.0.${++n}`);
    return worker.fetch(new Request("https://relay.example" + p, {...init, headers: h}), env);
  };
}

let fails = 0;
const ok = (cond, what) => { console.log((cond ? "PASS " : "FAIL ") + what); if (!cond) fails++; };
const good = {round: 3, scenes: {golden: {choice: "B", rating: 4, note: "Warmer please.\nBut not orange. @someone"},
                                  night: {choice: "neither", rating: null, note: ""}}, overall: "Close.\n```json\n{\"scenes\":{}}\n```"};
const post = (body, extra = {}, ip) => call("/feedback", {method: "POST",
  headers: {"Content-Type": "application/json", "Origin": ORIGIN, "X-QF-Passphrase": PASS, ...extra},
  body: typeof body === "string" ? body : JSON.stringify(body)}, ip);

// preflight
let r = await call("/feedback", {method: "OPTIONS", headers: {Origin: ORIGIN, "Access-Control-Request-Method": "POST",
  "Access-Control-Request-Headers": "content-type,x-qf-passphrase"}});
ok(r.status === 204 && r.headers.get("access-control-allow-origin") === ORIGIN &&
   /x-qf-passphrase/i.test(r.headers.get("access-control-allow-headers") || ""), "OPTIONS preflight from the Lab origin -> 204 + CORS");
r = await call("/feedback", {method: "OPTIONS", headers: {Origin: "https://evil.example"}});
ok(r.status === 403 && !r.headers.get("access-control-allow-origin"), "OPTIONS from another origin -> 403, no CORS header");
r = await post(good, {Origin: "https://evil.example"});
ok(r.status === 403, "POST from another origin -> 403");

// auth
r = await post(good, {"X-QF-Passphrase": "wrong"});
let j = await r.json();
ok(r.status === 401 && !JSON.stringify(j).includes(PASS) && !JSON.stringify(j).includes("dummy-token"), "wrong passphrase -> 401, no secret echoed");
r = await post(good, {"X-QF-Passphrase": ""});
ok(r.status === 401, "missing passphrase -> 401");

// validation
for (const [bad, what] of [["not json", "non-JSON"], [{round: "3", scenes: {}}, "round as string"],
    [{round: 1, scenes: []}, "scenes as array"], [{round: 1, scenes: {"Bad Id!": {}}}, "bad scene id"],
    [{round: 1, scenes: {a: {rating: 9}}}, "rating out of range"], [{round: 1, scenes: {a: {choice: "<script>"}}}, "bad choice"],
    [{round: 1, scenes: {}, overall: ""}, "empty answers"], [{round: 1, scenes: {}, extra: 1}, "unknown field"]]) {
  r = await post(bad); ok(r.status === 400, `${what} -> 400`);
}
r = await post({round: 1, scenes: {}, overall: "x".repeat(61 * 1024)});
ok(r.status === 413, "61 KB body -> 413");
ok(created.length === 0, "no issue created by any rejected request");

// success
r = await post(good); j = await r.json();
ok(r.status === 200 && j.ok === true && /\/issues\/1$/.test(j.issue_url), "valid post -> 200 {ok, issue_url}");
ok(r.headers.get("access-control-allow-origin") === ORIGIN, "response carries the CORS header");
const iss = created[0] || {};
ok(iss.title === "Shader Lab feedback: round 3", "issue title");
ok(JSON.stringify(iss.labels) === '["shader-feedback"]', "issue label");

// the body must parse with the real fetch_feedback.py
const py = `import json,sys,importlib.util
spec=importlib.util.spec_from_file_location("ff",sys.argv[1]);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
print(json.dumps(m.parse(sys.stdin.read())))`;
const ff = path.join(here, "..", "..", "review", "fetch_feedback.py");
const pr = spawnSync("py", ["-3.10", "-I", "-c", py, ff], {input: iss.body || "", encoding: "utf8"});
let parsed = null; try { parsed = JSON.parse(pr.stdout); } catch {}
ok(parsed && JSON.stringify(parsed) === JSON.stringify(good), "fetch_feedback.parse() returns exactly the posted answers" + (parsed ? "" : `: ${pr.stderr || pr.stdout}`));
ok(!(iss.body || "").split("```json")[0].includes("@someone"), "summary notes can not @-mention anyone (code block is inert)");

// ---- reference images ----
r = await call("/caps", {method: "GET", headers: {Origin: ORIGIN}}); j = await r.json();
ok(r.status === 200 && j.attachments === true && j.max_files === 20 && j.max_bytes === 8 * 1024 * 1024 &&
   r.headers.get("access-control-allow-origin") === ORIGIN, "GET /caps from the Lab -> 200 caps + CORS");
r = await call("/caps", {method: "GET", headers: {Origin: "https://evil.example"}});
ok(r.status === 403 && !r.headers.get("access-control-allow-origin"), "GET /caps from another origin -> 403, no CORS header");
r = await call("/caps", {method: "GET", headers: {}});
ok(r.status === 200, "GET /caps without Origin (curl) -> 200");
r = await call("/feedback", {method: "OPTIONS", headers: {Origin: ORIGIN, "Access-Control-Request-Method": "GET"}});
ok(/GET/.test(r.headers.get("access-control-allow-methods") || ""), "preflight allows GET");

const b64 = bytes => Buffer.from(bytes).toString("base64");
const jpeg = (n = 600) => b64([0xFF, 0xD8, 0xFF, 0xE0, ...new Uint8Array(n).map((_, i) => i & 255), 0xFF, 0xD9]);
const png = b64([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, ...Array(64).fill(7)]);
const webp = b64([...Buffer.from("RIFF"), 1, 0, 0, 0, ...Buffer.from("WEBPVP8 "), ...Array(64).fill(3)]);
const img = (scene, data = jpeg(), type = "image/jpeg", name = "grab.jpg") => ({scene, name, type, data});
const withImgs = (atts, base = good) => ({...base, attachments: atts});
const before = created.length;
const big = n => { const b = Buffer.alloc(n, 1); b[0] = 0xFF; b[1] = 0xD8; b[2] = 0xFF; return b.toString("base64"); };

r = await post(withImgs([img("golden")]), {"X-QF-Passphrase": "wrong"});
ok(r.status === 401 && committed.length === 0, "images + wrong passphrase -> 401, nothing committed");
for (const [atts, code, what] of [
    [[img("golden", jpeg(), "image/gif")], 400, "gif type"],
    [[img("golden", "not base64!!xxxxxxxx")], 400, "bad base64"],
    [[img("golden", jpeg().slice(0, -1))], 400, "base64 with bad length"],
    [[img("golden", png, "image/jpeg")], 400, "PNG bytes declared as JPEG"],
    [[img("golden", b64(Array(40).fill(65)), "image/png")], 400, "no magic bytes"],
    [[img("../../etc")], 400, "scene id with a path"],
    [[{...img("golden"), extra: 1}], 400, "unknown image field"],
    ["nope", 400, "attachments not an array"],
    [Array.from({length: 7}, () => img("golden")), 413, "7 images on one scene"],
    [Array.from({length: 21}, (_, i) => img(`s${i}`)), 413, "21 images"],
    [[img("golden", big(Math.round(2.6 * 1024 * 1024)))], 413, "2.6 MB image"]]) {
  r = await post(withImgs(atts)); ok(r.status === code, `${what} -> ${code}`);
}
r = await post(withImgs(Array.from({length: 4}, (_, i) => img(`s${i}`, big(Math.round(2.2 * 1024 * 1024))))));
ok(r.status === 413, "8.8 MB request -> 413");
r = await post(withImgs([img("golden")], {round: 1, scenes: {}, overall: "x".repeat(61 * 1024)}));
ok(r.status === 413, "61 KB of answers plus an image -> 413 (answers keep their cap)");
ok(committed.length === 0 && created.length === before, "no commit and no issue from any rejected image post");

r = await post(withImgs([img("golden"), img("golden", png, "image/png", "screen <shot>.png"), img(null, webp, "image/webp", "mood.webp")],
  {...good, round: 4})); j = await r.json();
ok(r.status === 200 && j.ok && j.attachments && j.attachments.saved === 3 && j.attachments.failed === 0, "3 images -> 200, saved 3");
const P = /^docs\/design\/shaders\/feedback\/attachments\/r004\/\d{8}T\d{9}Z-(golden|overall)-\d\.(jpg|png|webp)$/;
ok(committed.length === 3 && committed.every(c => P.test(c.path)), "committed under attachments/r004/<stamp>-<scene>-<n>.<ext>: " + committed.map(c => c.path.split("/").pop()).join(" "));
ok(committed.length === 3 && committed[0].path.endsWith("-golden-1.jpg") && committed[1].path.endsWith("-golden-2.png") &&
   committed[2].path.endsWith("-overall-1.webp"), "numbered per scene, overall named overall");
ok(committed.length === 3 && committed[0].content === jpeg() && committed[2].content === webp, "committed content is the posted base64, unchanged");
const ib = created[created.length - 1].body;
ok(/### Reference images/.test(ib) && /\*\*golden\*\* \(2\)/.test(ib) && /\*\*Overall\*\* \(1\)/.test(ib) &&
   ib.indexOf("**golden** (2)") < ib.indexOf("**Overall** (1)"), "issue groups images per scene, overall last");
ok(/!\[golden: grab\.jpg\]\(https:\/\/raw\.githubusercontent\.com\/MarionWhite\/quest-forge\/main\/docs\/design\/shaders\/feedback\/attachments\/r004\//.test(ib) &&
   /\[grab\.jpg\]\(https:\/\/github\.com\/MarionWhite\/quest-forge\/blob\/main\//.test(ib), "issue has inline image + blob link");
ok(ib.includes("screen _shot_.png") && !ib.includes("<shot>"), "file names are sanitised");
const pyA = `import json,sys,importlib.util
spec=importlib.util.spec_from_file_location("ff",sys.argv[1]);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
t=sys.stdin.read();print(json.dumps({"answers":m.parse(t),"att":m.attachments(t)}))`;
const pa = spawnSync("py", ["-3.10", "-I", "-c", pyA, ff], {input: ib, encoding: "utf8"});
let pj = null; try { pj = JSON.parse(pa.stdout); } catch {}
ok(pj && JSON.stringify(pj.answers) === JSON.stringify({...good, round: 4}), "answers block still parses exactly" + (pj ? "" : `: ${pa.stderr}`));
ok(pj && pj.att.length === 3 && pj.att.map(a => a.scene).join() === "golden,golden,_overall" &&
   pj.att.every((a, i) => a.path === committed[i].path && a.url.endsWith(a.path)), "fetch_feedback.attachments() lists all 3 with path, url, scene");

r = await post(withImgs([img("night")], {round: 4, scenes: {}, overall: ""})); j = await r.json();
ok(r.status === 200 && j.attachments && j.attachments.saved === 1, "images alone (no answers) are enough to send");

contentsMode = "deny"; const nIss = created.length;
r = await post(withImgs([img("golden"), img("night")], {...good, round: 4})); j = await r.json();
const fb = (created[nIss] || {}).body || "";
ok(r.status === 200 && j.ok && j.issue_url && j.attachments.saved === 0 && j.attachments.failed === 2 && /403/.test(j.attachments.error || ""),
   "contents API refuses -> issue still filed, response reports 2 failed");
ok(/2 images couldn't be saved to the repo\*\* \(GitHub said: HTTP 403\)/.test(fb) && !fb.includes("qf-attachments-v1"), "issue notes the failure, lists no images");
contentsMode = "ok";

// label fallback
labelMode = "reject"; const nLab = created.length;
r = await post(good); j = await r.json();
ok(r.status === 200 && created.length === nLab + 1 && !created[nLab].labels, "label rejected -> retried without label");
labelMode = "ok";

// Decisions page sheets ride the same relay as rounds 9000+
const nDec = created.length;
const sheetAns = {round: 9001, scenes: {"act1-01": {choice: "A", rating: null, note: "yes, as planned"}, "srv-pvp": {choice: "later", rating: null, note: ""}}, overall: "Add a card on voice chat."};
r = await post(sheetAns); j = await r.json();
const dec = created[nDec] || {};
ok(r.status === 200 && created.length === nDec + 1 && dec.title === "Decisions: sheet 1" && JSON.stringify(dec.labels) === '["decisions"]',
   "round 9001 -> issue 'Decisions: sheet 1' labelled decisions");
ok(/Decisions page answers for sheet 1 \(sent through the relay\)/.test(dec.body || ""), "decisions issue body names the sheet");
{
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "qf-dec-"));
  const issuesFile = path.join(tmp, "issues.json");
  fs.writeFileSync(issuesFile, JSON.stringify([{number: 77, html_url: "https://github.com/MarionWhite/quest-forge/issues/77", title: dec.title,
    body: dec.body, state: "open", created_at: "2026-10-25T12:00:00Z", user: {login: "owner"}}]));
  const fa = path.join(here, "..", "..", "..", "decisions", "fetch_answers.py");
  const pr2 = spawnSync("py", ["-3.10", "-I", fa, "--issues-json", issuesFile, "--out", tmp, "--no-mark"], {encoding: "utf8"});
  let out = null; try { out = JSON.parse(fs.readFileSync(path.join(tmp, "s001.json"), "utf8")); } catch {}
  ok(out && out.sheet === 1 && out.resolved["act1-01"] && out.resolved["act1-01"].choice === "A" && out.resolved["act1-01"].followed === true &&
     out.resolved["srv-pvp"].choice === "later" && out.open.includes("srv-pvp") && !out.open.includes("act1-01"),
     "fetch_answers.py resolves the sheet answers (A followed, srv-pvp later)" + (out ? "" : `: ${pr2.stderr || pr2.stdout}`));
  ok(/\| act1-01 Act boundaries \| \*\*A\*\* Yes, split as planned/.test(pr2.stdout), "fetch_answers.py prints the Markdown table");
  fs.rmSync(tmp, {recursive: true, force: true});
}
const pr3 = spawnSync("py", ["-3.10", "-I", "-c", py, ff], {input: dec.body || "", encoding: "utf8"});
let parsed9 = null; try { parsed9 = JSON.parse(pr3.stdout); } catch {}
ok(parsed9 && parsed9.round === 9001, "fetch_feedback.parse() still reads the block (collect() then skips rounds 9000+)");

// rate limit: 10 per 10 minutes per IP (the in-process run pins one IP; wrangler dev sees 127.0.0.1)
const ip = "10.9.9.9"; let codes = [];
for (let i = 0; i < 11; i++) codes.push((await post({round: 9, scenes: {}, overall: "rl " + i}, {}, ip)).status);
if (LIVE) ok(codes.includes(429), "rate limit kicks in -> 429 (" + codes.join(",") + ")");
else ok(codes.slice(0, 10).every(c => c === 200) && codes[10] === 429, "11th post in 10 min from one IP -> 429");

console.log(fails ? `${fails} failure(s)` : "all passed");
process.exit(fails ? 1 : 0);
