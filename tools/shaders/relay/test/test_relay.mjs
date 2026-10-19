// Tests the relay without touching GitHub.
//   node tools/shaders/relay/test/test_relay.mjs              in-process, fetch mocked
//   node tools/shaders/relay/test/test_relay.mjs --url http://127.0.0.1:8787 --mock-port 8799
//        against `wrangler dev` whose GITHUB_API points at the mock server this script starts.
import http from "node:http";
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
function github(method, url, headers, bodyText) {
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

// label fallback
labelMode = "reject";
r = await post(good); j = await r.json();
ok(r.status === 200 && created.length === 2 && !created[1].labels, "label rejected -> retried without label");
labelMode = "ok";

// rate limit: 10 per 10 minutes per IP (the in-process run pins one IP; wrangler dev sees 127.0.0.1)
const ip = "10.9.9.9"; let codes = [];
for (let i = 0; i < 11; i++) codes.push((await post({round: 9, scenes: {}, overall: "rl " + i}, {}, ip)).status);
if (LIVE) ok(codes.includes(429), "rate limit kicks in -> 429 (" + codes.join(",") + ")");
else ok(codes.slice(0, 10).every(c => c === 200) && codes[10] === 429, "11th post in 10 min from one IP -> 429");

console.log(fails ? `${fails} failure(s)` : "all passed");
process.exit(fails ? 1 : 0);
