// Quest Forge Shader Lab feedback relay (Cloudflare Worker, module syntax).
//
// The Lab page (site/shaders/) POSTs the owner's answers here; this Worker
// turns them into a GitHub issue "Shader Lab feedback: round N" whose body ends
// in a ```json block, the format tools/shaders/review/fetch_feedback.py reads.
//
//   POST /feedback   header X-QF-Passphrase, JSON body {round, scenes, overall}
//   -> 200 {ok: true, issue_url}   or   4xx/5xx {ok: false, error}
//
// Secrets (Worker Settings -> Variables and Secrets, type "Secret"):
//   QF_PASSPHRASE  the passphrase the Lab asks for once and keeps on the device
//   GITHUB_TOKEN   fine-grained token, Issues: read and write, this repo only
// Optional plain variable, for tests only: GITHUB_API (default https://api.github.com).
//
// Never logs the request body and never echoes either secret.

const REPO = "MarionWhite/quest-forge";
const ORIGIN = "https://marionwhite.github.io";
const MAX_BYTES = 60 * 1024;
const RATE_MAX = 10;                 // posts ...
const RATE_WINDOW_MS = 10 * 60 * 1000; // ... per 10 minutes per IP
const SCENE_ID = /^[a-z0-9][a-z0-9-]{0,63}$/;
const CHOICE = /^[A-Za-z0-9-]{1,16}$/;
const MAX_SCENES = 100;
const MAX_NOTE = 8000;

// Best effort: one map per Worker isolate, so limits reset when it restarts.
const hits = new Map();

function rateLimited(ip, now = Date.now()) {
  const recent = (hits.get(ip) || []).filter(t => now - t < RATE_WINDOW_MS);
  const limited = recent.length >= RATE_MAX;
  if (!limited) recent.push(now);
  hits.set(ip, recent);
  if (hits.size > 5000) {                      // keep the map from growing forever
    for (const [k, v] of hits) if (!v.length || now - v[v.length - 1] >= RATE_WINDOW_MS) hits.delete(k);
  }
  return limited;
}

function cors(origin) {
  const h = {"Vary": "Origin"};
  if (origin === ORIGIN) {
    h["Access-Control-Allow-Origin"] = ORIGIN;
    h["Access-Control-Allow-Methods"] = "POST, OPTIONS";
    h["Access-Control-Allow-Headers"] = "Content-Type, X-QF-Passphrase";
    h["Access-Control-Max-Age"] = "86400";
  }
  return h;
}

function reply(status, obj, origin) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: {"Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store", ...cors(origin)},
  });
}

// Constant-time comparison: hash both sides to fixed-length digests, then
// compare every byte without an early exit.
async function sameSecret(given, expected) {
  if (typeof given !== "string" || typeof expected !== "string" || !expected) return false;
  const enc = new TextEncoder();
  const [a, b] = await Promise.all([
    crypto.subtle.digest("SHA-256", enc.encode(given)),
    crypto.subtle.digest("SHA-256", enc.encode(expected)),
  ]);
  const x = new Uint8Array(a), y = new Uint8Array(b);
  let diff = 0;
  for (let i = 0; i < x.length; i++) diff |= x[i] ^ y[i];
  return diff === 0;
}

// Returns [clean answers, null] or [null, reason].
function validate(d) {
  if (!d || typeof d !== "object" || Array.isArray(d)) return [null, "body must be a JSON object"];
  const extra = Object.keys(d).filter(k => !["round", "scenes", "overall"].includes(k));
  if (extra.length) return [null, "unexpected field: " + extra[0]];
  if (!Number.isInteger(d.round) || d.round < 0 || d.round > 9999) return [null, "round must be an integer 0-9999"];
  if (!d.scenes || typeof d.scenes !== "object" || Array.isArray(d.scenes)) return [null, "scenes must be an object"];
  const ids = Object.keys(d.scenes);
  if (ids.length > MAX_SCENES) return [null, "too many scenes"];
  const overall = d.overall == null ? "" : d.overall;
  if (typeof overall !== "string" || overall.length > MAX_NOTE) return [null, "overall must be a string"];
  const scenes = {};
  for (const id of ids) {
    if (!SCENE_ID.test(id)) return [null, "bad scene id"];
    const a = d.scenes[id];
    if (!a || typeof a !== "object" || Array.isArray(a)) return [null, `scene ${id}: must be an object`];
    const bad = Object.keys(a).filter(k => !["choice", "rating", "note"].includes(k));
    if (bad.length) return [null, `scene ${id}: unexpected field ${bad[0]}`];
    const choice = a.choice == null ? null : a.choice;
    if (choice !== null && (typeof choice !== "string" || !CHOICE.test(choice))) return [null, `scene ${id}: bad choice`];
    const rating = a.rating == null ? null : a.rating;
    if (rating !== null && (!Number.isInteger(rating) || rating < 1 || rating > 5)) return [null, `scene ${id}: rating must be 1-5`];
    const note = a.note == null ? "" : a.note;
    if (typeof note !== "string" || note.length > MAX_NOTE) return [null, `scene ${id}: bad note`];
    scenes[id] = {choice, rating, note};
  }
  if (!ids.length && !overall.trim()) return [null, "nothing to send"];
  return [{round: d.round, scenes, overall}, null];
}

// Same layout as the page's own issue body: readable summary, then the json block.
function issueBody(ans) {
  const flat = s => s.replace(/\s*\n+\s*/g, " ").replace(/@/g, "@​"); // no accidental @-mentions
  const lines = [`Shader Lab feedback for round ${ans.round} (sent through the relay)`, ""];
  for (const [id, a] of Object.entries(ans.scenes)) {
    const pick = a.choice === "neither" ? "Neither" : a.choice ? a.choice : null;
    const bits = [pick ? `pick ${pick}` : null, a.rating ? `${a.rating}/5` : null].filter(Boolean).join(", ");
    lines.push(`- **${id}**${bits ? ": " + bits : ""}${a.note.trim() ? `\n  > ${flat(a.note.trim())}` : ""}`);
  }
  if (ans.overall.trim()) lines.push("", "**Overall:** " + flat(ans.overall.trim()));
  return `${lines.join("\n")}\n\n<!-- Machine-readable answers for fetch_feedback.py. Please leave this block as it is. -->\n` +
    "```json\n" + JSON.stringify(ans, null, 1) + "\n```\n";
}

async function createIssue(env, ans) {
  const api = (env.GITHUB_API || "https://api.github.com").replace(/\/+$/, "");
  const post = labels => fetch(`${api}/repos/${REPO}/issues`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${env.GITHUB_TOKEN}`,
      "Accept": "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "quest-forge-shader-lab-relay",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({title: `Shader Lab feedback: round ${ans.round}`, body: issueBody(ans), ...(labels ? {labels} : {})}),
  });
  let r = await post(["shader-feedback"]);
  // A token that may not create the label gets 403/422; the label is a nicety, the issue is not.
  if (r.status === 403 || r.status === 422) r = await post(null);
  if (!r.ok) return [null, r.status];
  const j = await r.json();
  return [j.html_url, null];
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    const url = new URL(request.url);

    if (request.method === "OPTIONS") {
      return new Response(null, {status: origin === ORIGIN ? 204 : 403, headers: cors(origin)});
    }
    if (url.pathname !== "/feedback") return reply(404, {ok: false, error: "not found"}, origin);
    if (request.method !== "POST") return reply(405, {ok: false, error: "use POST"}, origin);
    if (origin && origin !== ORIGIN) return reply(403, {ok: false, error: "origin not allowed"}, origin);

    const ip = request.headers.get("CF-Connecting-IP") || "unknown";
    if (rateLimited(ip)) return reply(429, {ok: false, error: "too many posts; wait ten minutes"}, origin);

    if (!env.QF_PASSPHRASE || !env.GITHUB_TOKEN) return reply(500, {ok: false, error: "relay is not configured"}, origin);
    if (!(await sameSecret(request.headers.get("X-QF-Passphrase") || "", env.QF_PASSPHRASE))) {
      return reply(401, {ok: false, error: "wrong passphrase"}, origin);
    }

    const declared = Number(request.headers.get("Content-Length") || 0);
    if (declared > MAX_BYTES) return reply(413, {ok: false, error: "answers too large (60 KB max)"}, origin);
    const raw = await request.arrayBuffer();
    if (raw.byteLength > MAX_BYTES) return reply(413, {ok: false, error: "answers too large (60 KB max)"}, origin);
    let data;
    try { data = JSON.parse(new TextDecoder().decode(raw)); } catch { return reply(400, {ok: false, error: "body is not JSON"}, origin); }
    const [ans, why] = validate(data);
    if (!ans) return reply(400, {ok: false, error: why}, origin);

    try {
      const [issueUrl, status] = await createIssue(env, ans);
      if (!issueUrl) {
        console.log(`github issue create failed: HTTP ${status}`);
        return reply(502, {ok: false, error: `GitHub refused the issue (HTTP ${status})`}, origin);
      }
      return reply(200, {ok: true, issue_url: issueUrl}, origin);
    } catch (e) {
      console.log("github unreachable: " + (e && e.name));
      return reply(502, {ok: false, error: "couldn't reach GitHub"}, origin);
    }
  },
};

