// Quest Forge Shader Lab feedback relay (Cloudflare Worker, module syntax).
//
// The Lab page (site/shaders/) POSTs the owner's answers here; this Worker
// turns them into a GitHub issue "Shader Lab feedback: round N" whose body ends
// in a ```json block, the format tools/shaders/review/fetch_feedback.py reads.
// The Decisions page (site/decisions/) sends sheet N as round 9000+N; that issue is
// titled "Decisions: sheet N" and read by tools/decisions/fetch_answers.py.
//
//   GET  /caps       -> 200 {ok, attachments: true, max_bytes, max_files, max_per_scene, max_file_bytes, types}
//                    The Lab shows its image-attach UI only when this answers.
//   POST /feedback   header X-QF-Passphrase, JSON body {round, scenes, overall, attachments?}
//   -> 200 {ok: true, issue_url, attachments?: {saved, failed, error?}}   or   4xx/5xx {ok: false, error}
//
// attachments (optional): [{scene, name, type, data}], scene a scene id or "_overall",
// type image/jpeg | image/png | image/webp, data plain base64. Each image is committed
// to docs/design/shaders/feedback/attachments/rNNN/ through the contents API before the
// issue is opened; the issue links them, shows them inline, and lists them in a
// <!-- qf-attachments-v1: [...] --> comment that fetch_feedback.py reads. An image that
// can't be committed doesn't stop the issue: the issue says so instead.
//
// Secrets (Worker Settings -> Variables and Secrets, type "Secret"):
//   QF_PASSPHRASE  the passphrase the Lab asks for once and keeps on the device
//   GITHUB_TOKEN   fine-grained token, this repo only: Issues read and write,
//                  Contents read and write (for the images)
// Optional plain variable, for tests only: GITHUB_API (default https://api.github.com).
//
// Never logs the request body and never echoes either secret.

const REPO = "MarionWhite/quest-forge";
const ORIGIN = "https://marionwhite.github.io";
const MAX_BYTES = 60 * 1024;              // the answers themselves (everything but attachments)
const MAX_BODY = 8 * 1024 * 1024;         // whole request, images included
const MAX_FILES = 20;
const MAX_PER_SCENE = 6;
const MAX_FILE_BYTES = 2.5 * 1024 * 1024; // one image, decoded
const TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"};
const OVERALL = "_overall";
const SHEET_BASE = 9000;   // rounds 9000+ are Decisions page sheets (site/decisions/): sheet N = round 9000+N
const isSheet = r => r >= SHEET_BASE;
const titleFor = r => isSheet(r) ? `Decisions: sheet ${r - SHEET_BASE}` : `Shader Lab feedback: round ${r}`;
const labelFor = r => isSheet(r) ? "decisions" : "shader-feedback";
const ATT_DIR = "docs/design/shaders/feedback/attachments";
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
    h["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS";
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
  const extra = Object.keys(d).filter(k => !["round", "scenes", "overall", "attachments"].includes(k));
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
  if (!ids.length && !overall.trim() && !(Array.isArray(d.attachments) && d.attachments.length)) return [null, "nothing to send"];
  return [{round: d.round, scenes, overall}, null];
}

// Returns [clean list, null, 0] or [null, reason, http status]. Only checks: it decodes
// nothing but each image's first 12 bytes, so a big post stays cheap on CPU.
function validateAttachments(list) {
  if (list == null) return [[], null, 0];
  if (!Array.isArray(list)) return [null, "attachments must be an array", 400];
  if (list.length > MAX_FILES) return [null, `too many images (${MAX_FILES} max)`, 413];
  const per = {}, out = [];
  for (const [i, a] of list.entries()) {
    const at = `image ${i + 1}`;
    if (!a || typeof a !== "object" || Array.isArray(a)) return [null, `${at}: must be an object`, 400];
    const bad = Object.keys(a).filter(k => !["scene", "name", "type", "data"].includes(k));
    if (bad.length) return [null, `${at}: unexpected field ${bad[0]}`, 400];
    const scene = a.scene == null ? OVERALL : a.scene;
    if (typeof scene !== "string" || (scene !== OVERALL && !SCENE_ID.test(scene))) return [null, `${at}: bad scene id`, 400];
    per[scene] = (per[scene] || 0) + 1;
    if (per[scene] > MAX_PER_SCENE) return [null, `too many images for one scene (${MAX_PER_SCENE} max)`, 413];
    if (!Object.prototype.hasOwnProperty.call(TYPES, a.type)) return [null, `${at}: only JPEG, PNG or WebP`, 400];
    const data = a.data;
    if (typeof data !== "string" || data.length < 16 || data.length % 4) return [null, `${at}: data is not base64`, 400];
    const bytes = data.length / 4 * 3 - (data.endsWith("==") ? 2 : data.endsWith("=") ? 1 : 0);
    if (bytes > MAX_FILE_BYTES) return [null, `${at}: too large (2.5 MB max)`, 413];
    // Native atob rejects any character outside the alphabet and a misplaced "="; it skips
    // whitespace, which then shows as a length mismatch. About six times cheaper than a regex.
    let bin;
    try { bin = atob(data); } catch { return [null, `${at}: data is not base64`, 400]; }
    if (bin.length !== bytes) return [null, `${at}: data is not base64`, 400];
    const sig = bin.slice(0, 12), head = [0, 1, 2].map(k => sig.charCodeAt(k));
    const kind = head[0] === 0xFF && head[1] === 0xD8 && head[2] === 0xFF ? "image/jpeg"
      : sig.startsWith("\x89PNG\r\n\x1a\n") ? "image/png"
      : sig.startsWith("RIFF") && sig.slice(8, 12) === "WEBP" ? "image/webp" : null;
    if (kind !== a.type) return [null, `${at}: content is not ${a.type}`, 400];
    const name = typeof a.name === "string" ? a.name.replace(/[^A-Za-z0-9 ._()-]+/g, "_").slice(0, 80).trim() : "";
    out.push({scene, name: name || `image-${i + 1}`, type: a.type, data, bytes});
  }
  return [out, null, 0];
}

const gh = (env, path, method, body) => fetch(`${(env.GITHUB_API || "https://api.github.com").replace(/\/+$/, "")}${path}`, {
  method,
  headers: {
    "Authorization": `Bearer ${env.GITHUB_TOKEN}`,
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "quest-forge-shader-lab-relay",
    "Content-Type": "application/json",
  },
  body: typeof body === "string" ? body : JSON.stringify(body),
});

// UTC stamp with milliseconds, e.g. 20261023T153012123Z: sorts by time, never collides in practice.
const stamp = (d = new Date()) => d.toISOString().replace(/[-:.]/g, "");

// Commit each image, one after another (parallel commits to one branch conflict).
// -> {saved: [{scene, name, path, url, html_url}], failed: [{scene, name, status}]}
async function commitImages(env, round, atts) {
  const rid = `r${String(round).padStart(3, "0")}`;
  const saved = [], failed = [];
  if (!/^r\d{3,4}$/.test(rid)) return {saved, failed: atts.map(a => ({scene: a.scene, name: a.name, status: "bad round"}))};
  const ts = stamp(), count = {};
  for (const a of atts) {
    const scene = a.scene === OVERALL ? "overall" : a.scene;   // already SCENE_ID-clean
    const n = count[scene] = (count[scene] || 0) + 1;
    const path = `${ATT_DIR}/${rid}/${ts}-${scene}-${n}.${TYPES[a.type]}`;
    try {
      // Built by hand so the (already checked) base64 isn't scanned again by JSON.stringify.
      const body = `{"message":${JSON.stringify(`Shader Lab feedback ${rid}: reference image for ${scene} (${n})`)},"content":"${a.data}"}`;
      const r = await gh(env, `/repos/${REPO}/contents/${path}`, "PUT", body);
      if (!r.ok) { failed.push({scene: a.scene, name: a.name, status: `HTTP ${r.status}`}); continue; }
      const j = await r.json().catch(() => ({}));
      const c = j.content || {};
      saved.push({scene: a.scene, name: a.name, path,
        url: c.download_url || `https://raw.githubusercontent.com/${REPO}/main/${path}`,
        html_url: c.html_url || `https://github.com/${REPO}/blob/main/${path}`});
    } catch {
      failed.push({scene: a.scene, name: a.name, status: "unreachable"});
    }
  }
  return {saved, failed};
}

// Same layout as the page's own issue body: readable summary, then the json block,
// then (with images) a machine-readable list in an HTML comment.
function issueBody(ans, imgs) {
  const flat = s => s.replace(/\s*\n+\s*/g, " ").replace(/@/g, "@​"); // no accidental @-mentions
  const lines = [`${isSheet(ans.round) ? `Decisions page answers for sheet ${ans.round - SHEET_BASE}` : `Shader Lab feedback for round ${ans.round}`} (sent through the relay)`, ""];
  for (const [id, a] of Object.entries(ans.scenes)) {
    const pick = a.choice === "neither" ? "Neither" : a.choice ? a.choice : null;
    const bits = [pick ? `pick ${pick}` : null, a.rating ? `${a.rating}/5` : null].filter(Boolean).join(", ");
    lines.push(`- **${id}**${bits ? ": " + bits : ""}${a.note.trim() ? `\n  > ${flat(a.note.trim())}` : ""}`);
  }
  if (ans.overall.trim()) lines.push("", "**Overall:** " + flat(ans.overall.trim()));
  let tail = "";
  if (imgs && (imgs.saved.length || imgs.failed.length)) {
    lines.push("", "### Reference images");
    const groups = [...new Set([...imgs.saved, ...imgs.failed].map(a => a.scene))]
      .sort((a, b) => (a === OVERALL) - (b === OVERALL));     // scenes in sent order, overall last
    for (const g of groups) {
      const mine = imgs.saved.filter(a => a.scene === g);
      lines.push("", `**${g === OVERALL ? "Overall" : g}**${mine.length ? ` (${mine.length})` : ""}`);
      for (const a of mine) lines.push("", `[${a.name}](${a.html_url})`, `![${g === OVERALL ? "overall" : g}: ${a.name}](${a.url})`);
    }
    if (imgs.failed.length) {
      const why = [...new Set(imgs.failed.map(f => f.status))].join(", ");
      lines.push("", `**${imgs.failed.length} image${imgs.failed.length === 1 ? "" : "s"} couldn't be saved to the repo** ` +
        `(GitHub said: ${why}). Check that the relay's token has Contents: read and write.`);
    }
    if (imgs.saved.length) {
      const list = imgs.saved.map(({scene, name, path, url}) => ({scene, name, path, url}));
      tail = "\n<!-- Images for fetch_feedback.py. Please leave this line as it is. -->\n<!-- qf-attachments-v1: " +
        JSON.stringify(list).replace(/</g, "\\u003c").replace(/>/g, "\\u003e") + " -->\n";
    }
  }
  return `${lines.join("\n")}\n\n<!-- Machine-readable answers for fetch_feedback.py. Please leave this block as it is. -->\n` +
    "```json\n" + JSON.stringify(ans, null, 1) + "\n```\n" + tail;
}

async function createIssue(env, ans, imgs) {
  const post = labels => gh(env, `/repos/${REPO}/issues`, "POST",
    {title: titleFor(ans.round), body: issueBody(ans, imgs), ...(labels ? {labels} : {})});
  let r = await post([labelFor(ans.round)]);
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
    if (url.pathname === "/caps") {
      if (request.method !== "GET") return reply(405, {ok: false, error: "use GET"}, origin);
      if (origin && origin !== ORIGIN) return reply(403, {ok: false, error: "origin not allowed"}, origin);
      return reply(200, {ok: true, attachments: true, max_bytes: MAX_BODY, max_files: MAX_FILES, max_per_scene: MAX_PER_SCENE,
        max_file_bytes: MAX_FILE_BYTES, types: Object.keys(TYPES)}, origin);
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

    const tooBig = "request too large (8 MB max with images)";
    const declared = Number(request.headers.get("Content-Length") || 0);
    if (declared > MAX_BODY) return reply(413, {ok: false, error: tooBig}, origin);
    const raw = await request.arrayBuffer();
    if (raw.byteLength > MAX_BODY) return reply(413, {ok: false, error: tooBig}, origin);
    let data;
    try { data = JSON.parse(new TextDecoder().decode(raw)); } catch { return reply(400, {ok: false, error: "body is not JSON"}, origin); }
    // The answers alone keep their old 60 KB cap; only images may use the rest.
    const hasAtt = data && typeof data === "object" && !Array.isArray(data) && "attachments" in data;
    const answerBytes = hasAtt ? new TextEncoder().encode(JSON.stringify({...data, attachments: undefined})).byteLength : raw.byteLength;
    if (answerBytes > MAX_BYTES) return reply(413, {ok: false, error: "answers too large (60 KB max)"}, origin);
    const [ans, why] = validate(data);
    if (!ans) return reply(400, {ok: false, error: why}, origin);
    const [atts, whyAtt, attStatus] = validateAttachments(data.attachments);
    if (!atts) return reply(attStatus, {ok: false, error: whyAtt}, origin);

    try {
      const imgs = atts.length ? await commitImages(env, ans.round, atts) : null;
      if (imgs && imgs.failed.length) console.log(`image commit failed: ${imgs.failed.map(f => f.status).join(",")}`);
      const [issueUrl, status] = await createIssue(env, ans, imgs);
      if (!issueUrl) {
        console.log(`github issue create failed: HTTP ${status}`);
        return reply(502, {ok: false, error: `GitHub refused the issue (HTTP ${status})`}, origin);
      }
      const extra = imgs ? {attachments: {saved: imgs.saved.length, failed: imgs.failed.length,
        ...(imgs.failed.length ? {error: `GitHub refused ${imgs.failed.length} image(s) (${[...new Set(imgs.failed.map(f => f.status))].join(", ")})`} : {})}} : {};
      return reply(200, {ok: true, issue_url: issueUrl, ...extra}, origin);
    } catch (e) {
      console.log("github unreachable: " + (e && e.name));
      return reply(502, {ok: false, error: "couldn't reach GitHub"}, origin);
    }
  },
};

