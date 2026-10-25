/* Quest Forge items index: offline copy and update notices.
   Bump VERSION whenever this file's logic changes; activate deletes older caches. */
"use strict";

const VERSION = "v1";
const PREFIX = "qf-items-";
const CACHE = PREFIX + VERSION;

const SCOPE = new URL("./", self.location.href).href;     // .../quest-forge/items/
const SCOPE_PATH = new URL(SCOPE).pathname;
const PRECACHE = [SCOPE, new URL("manifest.webmanifest", SCOPE).href];
const META = new URL("__qf-meta", SCOPE).href;            // { sheets, ready } kept in the cache
const DATA_RE = /\/data\/(items\.json|recipes\.json|descriptions\.json|icons-\d+\.png)$/;
const FRESH_RE = /\/data\/freshness\.json$/;
const FONT_ORIGINS = ["https://fonts.googleapis.com", "https://fonts.gstatic.com"];

// Cache calls never throw into a fetch: a broken cache just means no cache.
async function openCache() {
  try { return await caches.open(CACHE); } catch (e) { return null; }
}
async function matchOf(key) {
  try { const c = await openCache(); return c ? await c.match(key) : undefined; } catch (e) { return undefined; }
}
async function store(key, res) {
  try { const c = await openCache(); if (c) await c.put(key, res); } catch (e) { /* ignore */ }
}
function storable(res) {
  return !!res && (res.ok || res.type === "opaque");   // cross-origin font CSS is opaque
}

function dataUrls(n) {
  const list = ["items.json", "recipes.json", "descriptions.json"].map(f => new URL("data/" + f, SCOPE).href);
  for (let i = 0; i < n; i++) list.push(new URL("data/icons-" + i + ".png", SCOPE).href);
  return list;
}

async function broadcast(msg) {
  try {
    const list = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
    list.forEach(c => c.postMessage(msg));
  } catch (e) { /* no pages to tell */ }
}

// Two responses differ when a validator both have and they disagree. Missing headers count as unchanged.
function changed(a, b) {
  return ["ETag", "Last-Modified", "Content-Length"].some(h => {
    const x = a.headers.get(h), y = b.headers.get(h);
    return x != null && y != null && x !== y;
  });
}

async function readMeta() {
  const hit = await matchOf(META);
  if (!hit) return {};
  try { return await hit.json(); } catch (e) { return {}; }
}

async function cacheComplete(n) {
  for (const u of dataUrls(n)) {
    if (!(await matchOf(u))) return false;
  }
  return true;
}

// offline-ready goes to every page once (meta.ready), then to any page that asks (source).
async function announceIfComplete(n, source) {
  if (!(await cacheComplete(n))) return;
  const meta = await readMeta();
  if (meta.ready) {
    if (source) source.postMessage({ type: "offline-ready" });
    return;
  }
  await store(META, new Response(JSON.stringify(Object.assign({}, meta, { sheets: n, ready: true }))));
  await broadcast({ type: "offline-ready" });
}

async function setSheets(n, source) {
  const meta = await readMeta();
  meta.sheets = n;
  await store(META, new Response(JSON.stringify(meta)));
  for (const u of dataUrls(n)) {                     // fill in anything not yet cached
    if (await matchOf(u)) continue;
    try {
      const res = await fetch(u, { cache: "no-cache" });
      if (res.ok) await store(u, res.clone());
    } catch (e) { /* offline: try again on the next visit */ }
  }
  await announceIfComplete(n, source);
}

async function revalidate(url, old, isData) {
  try {
    const res = await fetch(url, { cache: "no-cache" });
    if (!res.ok) return;
    await store(url, res.clone());
    if (isData && old && changed(old, res)) await broadcast({ type: "updated", url });
  } catch (e) { /* offline: keep what we have */ }
}

async function staleWhileRevalidate(event, req, url) {
  const hit = await matchOf(req.url);
  const isData = DATA_RE.test(url.pathname);
  if (hit) {
    event.waitUntil(revalidate(req.url, hit, isData));
    return hit;
  }
  const res = await fetch(req);
  if (storable(res)) {
    event.waitUntil(store(req.url, res.clone()).then(async () => {
      if (!isData) return;
      const meta = await readMeta();
      if (Number.isInteger(meta.sheets)) await announceIfComplete(meta.sheets);
    }));
  }
  return res;
}

async function networkFirst(req) {
  try {
    const res = await fetch(req);
    if (res.ok) store(req.url, res.clone());
    return res;
  } catch (e) {
    const hit = await matchOf(req.url);
    if (hit) return hit;
    throw e;
  }
}

async function fontCacheFirst(event, req) {
  const hit = await matchOf(req.url);
  if (hit) {
    event.waitUntil(fetch(req).then(res => (storable(res) ? store(req.url, res.clone()) : undefined)).catch(() => {}));
    return hit;
  }
  const res = await fetch(req);
  if (storable(res)) store(req.url, res.clone());
  return res;
}

self.addEventListener("install", event => {
  self.skipWaiting();
  event.waitUntil((async () => {
    for (const u of PRECACHE) {
      try {
        const c = await openCache();
        if (c) await c.add(new Request(u, { cache: "reload" }));
      } catch (e) { /* a failed precache must not block install */ }
    }
  })());
});

self.addEventListener("activate", event => {
  event.waitUntil((async () => {
    try {
      const names = await caches.keys();
      await Promise.all(names.filter(n => n.startsWith(PREFIX) && n !== CACHE).map(n => caches.delete(n)));
    } catch (e) { /* ignore */ }
    await self.clients.claim();
  })());
});

self.addEventListener("message", event => {
  const d = event.data;
  if (!d || d.type !== "sheets" || !Number.isInteger(d.n) || d.n < 0 || d.n > 64) return;
  event.waitUntil(setSheets(d.n, event.source).catch(() => {}));
});

self.addEventListener("fetch", event => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin === self.location.origin && url.pathname.startsWith(SCOPE_PATH)) {
    if (FRESH_RE.test(url.pathname)) { event.respondWith(networkFirst(req)); return; }
    event.respondWith(staleWhileRevalidate(event, req, url));
    return;
  }
  if (FONT_ORIGINS.includes(url.origin)) {
    event.respondWith(fontCacheFirst(event, req));
  }
});
