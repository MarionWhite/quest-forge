// The Wall of Graves, page logic: the feed, the Krypt in three.js, the walk, the focus sheet, the minimap,
// the boards and the 2D fallback. Modules beside this file: data.js, models.js, model.js, textures.js, krypt.js.
import * as THREE from "three";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { ShaderPass } from "three/addons/postprocessing/ShaderPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";
import { BokehPass } from "three/addons/postprocessing/BokehPass.js";
import {
  normalize, killerText, epitaph, epitaphParts, familyFor, ornaments, poseFor, seedFor,
  CAUSE_LABEL, CAUSE_NOUN, hash
} from "./data.js";
import { layout, buildGrid, meshGrid, torchSpots, alcoveFor, pathCurve, skyObjects, dressing, worldZ, sizeOf } from "./krypt.js";
import { buildStone, buildStatue, buildAngelFigure, makeTexture, imageTexture, statueCanvas, STONE_HEIGHT } from "./model.js";
import { loadImage, canvas, glowCanvas, dotCanvas, skyCanvas } from "./textures.js";

const $ = (s) => document.querySelector(s);
const DEMO = new URLSearchParams(location.search).has("demo");
const DUMP = new URLSearchParams(location.search).has("dump");   // verification: one rendered frame, dumped into the DOM
const QS = new URLSearchParams(location.search);
const FAMILY_FILE = { slab: "grave_stone", tomb: "grave_zerk", pillar: "grave_pillar", wood: "grave_wood", knight: "grave_knight",
  cross: "grave_stone", angel: "grave_stone", skeleton: "skeleton" };
const TEX_FILES = ["stone", "cobblestone", "cobblestone_mossy", "stonebrick", "stonebrick_mossy", "stonebrick_cracked",
  "gravel", "obsidian", "bedrock", "coal_ore", "iron_ore", "web", "vine", "netherrack", "glowstone", "iron_bars",
  "lava_still", "water_still", "torch_on", "rail_normal", "waterlily", "particles", "steve",
  "grave_stone", "grave_zerk", "grave_pillar", "grave_wood", "grave_knight", "skeleton"];

const state = {
  graves: [], updated: null, feed: "", loadError: false,
  webgl: false, reduced: matchMedia("(prefers-reduced-motion: reduce)").matches || new URLSearchParams(location.search).has("flat"),
  phone: matchMedia("(max-width: 700px)").matches || matchMedia("(pointer: coarse)").matches,
  walk: null, sheetOpen: false, focus: null
};

// ---- the scares contract ---------------------------------------------------------------------
// window.__krypt is the stable hand-off to scares.js. Fields are filled in as the Krypt starts; before that
// they are null/empty.
//   scene, camera, renderer, composer       the three.js objects (composer's last pass is the output)
//   getWalk() -> { s, speed, activeSeconds, depth }
//       s              0..1 along the path (damped, what the camera shows)
//       speed          blocks per second of walking right now (0 when standing)
//       activeSeconds  seconds the visitor has spent actually walking, not paused, not focused on a stone
//       depth          0..1, the same as s but eased: 0 at the entrance crypt, 1 in the nether depths
//   corners         [{ s, pos: Vector3, dir: Vector3, side }] where the path turns or a side passage opens:
//                   pos is the floor-level centre of the turn, dir the unit heading after it, side -1 left / +1 right
//   takeover(on)    true pauses the camera control and walk input (and own footsteps) while a scare plays;
//                   false restores them. The scare may move window.__krypt.camera while taken over.
const __kryptHold = { on: false };
window.__krypt = {
  scene: null, camera: null, renderer: null, composer: null, corners: [],
  getWalk() { return { s: 0, speed: 0, activeSeconds: 0, depth: 0 }; },
  takeover(on) { __kryptHold.on = !!on; }
};

// --- scares: begin (owned by scares.js) ---
// --- scares: end ---

// ---- helpers --------------------------------------------------------------------------------
function ago(iso) {
  const s = (Date.now() - Date.parse(iso)) / 1000;
  if (!isFinite(s)) return "";
  const a = Math.abs(s);
  for (const [name, v] of [["year", 31536000], ["month", 2592000], ["day", 86400], ["hour", 3600], ["minute", 60]]) {
    if (a >= v) { const k = Math.floor(a / v), t = `${k} ${name}${k > 1 ? "s" : ""}`; return s < 0 ? `in ${t}` : `${t} ago`; }
  }
  return "just now";
}
function absolute(iso) {
  const d = new Date(iso);
  return isNaN(d) ? iso : d.toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
}
function where(g) {
  const dim = g.dimension || "Unknown dimension";
  return g.pos ? `${dim}, ${g.pos.join(", ")}` : `${dim}; position not logged`;
}
function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text != null) e.textContent = text;
  return e;
}
function count(keyFn) {
  const m = new Map();
  for (const g of state.graves) { const k = keyFn(g); m.set(k, (m.get(k) || 0) + 1); }
  return [...m.entries()].sort((a, b) => b[1] - a[1] || String(a[0]).localeCompare(String(b[0])));
}

// ---- data -----------------------------------------------------------------------------------
async function load() {
  try {
    let url = "data/graves.json";
    if (DEMO) url = "data/demo.json";
    else {
      try { const c = await (await fetch("config.json", { cache: "no-store" })).json(); state.feed = String(c.feed || "").trim(); }
      catch { state.feed = ""; }
      if (state.feed) url = state.feed;
    }
    const r = await fetch(url, { cache: "no-store" });
    if (!r.ok) throw new Error(String(r.status));
    const n = normalize(await r.json());
    state.graves = n.graves; state.updated = n.updated;
  } catch { state.loadError = true; state.graves = []; }
  renderPage();
}

// ---- the page's text: the count, the boards, the drawer, the 2D list ------------------------
function renderPage() {
  const G = state.graves;
  $("#demoNote").hidden = !DEMO;
  const empty = !G.length;
  $("#emptyPanel").hidden = !empty;
  if (empty) {
    $("#emptyText").textContent = state.loadError ? "The graves could not be read." : "The first grave is still unclaimed.";
    $("#emptySub").textContent = state.loadError
      ? "Try again in a minute. The page reads the server's file on every visit."
      : (state.feed || DEMO) ? "Nobody has died on the server yet." : "The server has not opened. Each death will put a stone here, in the order it happened.";
  }
  const first = G.length ? G[0].time : null;
  $("#count").textContent = G.length ? `${G.length} ${G.length === 1 ? "death" : "deaths"} since the server opened` : "No deaths yet";
  $("#countSub").textContent = G.length
    ? `First on record ${absolute(first)}` + (state.updated ? `. Written ${ago(state.updated)}.` : ".")
    : "The Krypt is ready. Each stone goes in its alcove as the server logs a death.";
  $("#source").textContent = (DEMO ? "Source: demo data" : state.feed ? "Source: published feed" : "Source: data/graves.json, written from the server log") +
    (state.updated ? ` · updated ${absolute(state.updated)}` : "");
  renderBoards();
  renderFlat();
  // The filter selects and the search list.
  const names = count(g => g.player).sort((a, b) => a[0].localeCompare(b[0]));
  const dl = $("#names"); dl.textContent = "";
  for (const [n] of names) dl.append(new Option(n, n));
  $("#stage").hidden = !state.webgl || state.reduced;
  $("#flat").hidden = !!($("#stage") && !$("#stage").hidden);
  if (!$("#stage").hidden) startKrypt();
}

function rank(ol, items) {
  ol.textContent = "";
  if (!items.length) { ol.append(el("li", "empty", "Nothing yet.")); return; }
  const max = items[0][1];
  for (const [name, n] of items.slice(0, 8)) {
    const li = el("li");
    li.append(el("span", "nm", name), el("span", "n", String(n)));
    const bar = el("span", "bar"); const i = el("i"); i.style.width = (n / max * 100).toFixed(1) + "%"; bar.append(i);
    li.append(bar); ol.append(li);
  }
}
function renderBoards() {
  rank($("#killers"), count(g => g.killer || CAUSE_NOUN[g.cause] || "Not recorded"));
  rank($("#deaths"), count(g => g.player));
}

// The 2D fallback: the same graves as a list of engraved cards.
function renderFlat() {
  const ol = $("#flatList"); ol.textContent = "";
  const list = state.graves.slice().reverse();
  if (!list.length) { ol.append(el("li", "flat-empty", "The first grave is still unclaimed.")); return; }
  for (const g of list) {
    const li = el("li", "flat-card");
    const stone = el("div", "flat-stone");
    stone.append(el("span", "flat-name", g.player), el("span", "flat-epi", epitaph(g)));
    const body = el("div", "flat-body");
    body.append(el("p", "flat-msg", g.message), el("p", "flat-meta", `${absolute(g.time)} · ${where(g)}`),
      el("p", "flat-meta", `Killer: ${killerText(g)} · death ${g.nth} for ${g.player}`));
    li.append(stone, body); ol.append(li);
  }
}

// ---- 3D: the Krypt --------------------------------------------------------------------------
let K = null;   // the running Krypt

function checkWebGL() {
  try { const c = document.createElement("canvas"); return !!(c.getContext("webgl2") || c.getContext("webgl")); }
  catch { return false; }
}

async function startKrypt() {
  if (K) return;
  K = {};
  const stage = $("#stage"), cv = $("#gl");
  const phone = state.phone;
  const renderer = new THREE.WebGLRenderer({ canvas: cv, antialias: false, powerPreference: "high-performance" });
  renderer.setPixelRatio(phone ? 0.5 : Math.min(devicePixelRatio, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.1;
  renderer.shadowMap.enabled = !phone;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  K.renderer = renderer;

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0e0b12);
  scene.fog = new THREE.FogExp2(0x0e0b12, 0.035);
  K.scene = scene;
  const camera = new THREE.PerspectiveCamera(58, 1, 0.05, 160);
  K.camera = camera;

  // Textures: the pack's own files, loaded once.
  const IMG = {};
  await Promise.all(TEX_FILES.map(async n => { try { IMG[n] = await loadImage(`tex/${n}.png`); } catch { /* optional */ } }));
  K.IMG = IMG;
  const lay = layout(state.graves.length);
  K.lay = lay;
  const L = sizeOf(lay);
  K.length = L;
  const curve = pathCurve(lay);
  K.curve = curve;

  // Lights.
  const hemi = new THREE.HemisphereLight(0x8a7ab0, 0x2a1d2c, 1.1);
  scene.add(hemi); K.hemi = hemi;
  const sun = new THREE.DirectionalLight(0xcbb8ff, 0.9);
  sun.position.set(-6, 30, -8);
  sun.castShadow = !phone;
  if (sun.castShadow) {
    sun.shadow.mapSize.set(2048, 2048);
    const sc = sun.shadow.camera; sc.left = -16; sc.right = 16; sc.top = 16; sc.bottom = -16; sc.near = 1; sc.far = 80;
    sun.shadow.bias = -0.0008;
  }
  scene.add(sun, sun.target); K.sun = sun;

  // The block grid, meshed once.
  const grid = buildGrid(lay);
  const gm = meshGrid(grid, IMG, { shadows: !phone });
  scene.add(gm.group); K.gridMesh = gm;

  // Set-piece textures.
  const lavaTex = imageTexture(IMG.lava_still, { nearest: true, repeat: true });
  const barsTex = imageTexture(IMG.iron_bars, { nearest: true });
  const webTex = imageTexture(IMG.web, { nearest: true });
  const vineTex = imageTexture(IMG.vine, { nearest: true });
  const railTex = imageTexture(IMG.rail_normal, { nearest: true });
  const waterTex = imageTexture(IMG.water_still, { nearest: true, repeat: true });
  const dress = dressing(lay, IMG, { planeTex: { lava: lavaTex, bars: barsTex, web: webTex, vine: vineTex, rail: railTex, water: waterTex } });
  scene.add(dress); K.dress = dress;

  // The sky: the shattered violet, and the rays that fall through the holes.
  const skyTex = makeTexture(skyCanvas(9));
  const rc = canvas(64, 256), rx = rc.getContext("2d");
  const rg = rx.createLinearGradient(0, 0, 0, 256);
  rg.addColorStop(0, "rgba(220,200,255,0.9)"); rg.addColorStop(1, "rgba(200,180,255,0)");
  rx.fillStyle = rg; rx.fillRect(0, 0, 64, 256);
  const sky = skyObjects(lay, skyTex, makeTexture(rc), makeTexture(glowCanvas("205,176,255")));
  scene.add(sky); K.sky = sky;

  // Torches: the flame on a cross plane, a glow sprite, and a live light for the nearest few.
  const torchImg = IMG.torch_on;
  const torchTex = imageTexture(torchImg, { nearest: true });
  const glow = makeTexture(glowCanvas("255,150,60"));
  // Only the alcoves that hold a grave get a torch. The empty ones stay dark until the feed fills them.
  const spots = torchSpots(lay).filter(sp => sp.slot < 0 || sp.slot < state.graves.length);
  K.torches = [];
  const nLive = phone ? 2 : 3;
  K.lights = [];
  for (let n = 0; n < nLive; n++) {
    const pl = new THREE.PointLight(0xffa552, 0, 11, 2);
    scene.add(pl); K.lights.push(pl);
  }
  const flameMat = new THREE.MeshBasicMaterial({ map: torchTex, alphaTest: 0.4, side: THREE.DoubleSide, color: new THREE.Color(1.2, 1.1, 1.0) });
  const spriteMat = () => new THREE.SpriteMaterial({ map: glow, color: new THREE.Color(1.25, 0.7, 0.32), blending: THREE.AdditiveBlending, depthWrite: false, transparent: true });
  for (const s of spots) {
    const tg = new THREE.Group();
    const p1 = new THREE.Mesh(new THREE.PlaneGeometry(0.45, 0.9), flameMat);
    const p2 = p1.clone(); p2.rotation.y = Math.PI / 2;
    p1.position.y = 0.45; p2.position.y = 0.45;
    tg.add(p1, p2);
    tg.position.set(s.x, s.y - 0.4, s.z);
    const sp = new THREE.Sprite(spriteMat());
    sp.scale.setScalar(1.7); sp.position.set(0, 0.85, 0); tg.add(sp);
    scene.add(tg);
    K.torches.push({ s, group: tg, sprite: sp, phase: Math.random() * 10, live: null });
  }

  // Ash and embers falling through the gallery.
  const embers = pickEmber(IMG.particles);
  const NA = phone ? 220 : 480, NE = phone ? 60 : 130;
  const ashG = particleSystem(NA, makeTexture(dotCanvas("210,200,225")), 0.045, THREE.NormalBlending, 0.5);
  const emberG = particleSystem(NE, embers, 0.13, THREE.AdditiveBlending, 1);
  scene.add(ashG.points, emberG.points);
  K.ash = ashG; K.ember = emberG;

  // The focus spotlight, for the grave that is open.
  const spot = new THREE.SpotLight(0xffc27a, 0, 14, 0.5, 0.7, 1.4);
  scene.add(spot, spot.target); K.spot = spot;

  // Post: bloom on the torches and lava, a bokeh blur on desktop, vignette and film grain, output.
  const size = new THREE.Vector2();
  const composer = new EffectComposer(renderer);
  K.composer = composer;
  const render = new RenderPass(scene, camera);
  composer.addPass(render);
  const bloom = new UnrealBloomPass(new THREE.Vector2(256, 256), 0.6, 0.55, 0.72);
  composer.addPass(bloom); K.bloom = bloom;
  let bokeh = null;
  if (!phone) {
    bokeh = new BokehPass(scene, camera, { focus: 3, aperture: 0.00045, maxblur: 0.0045 });
    composer.addPass(bokeh); K.bokeh = bokeh;
  }
  const grade = new ShaderPass({
    uniforms: { tDiffuse: { value: null }, time: { value: 0 }, res: { value: new THREE.Vector2(1, 1) } },
    vertexShader: "varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }",
    fragmentShader: `uniform sampler2D tDiffuse; uniform float time; uniform vec2 res; varying vec2 vUv;
      float rnd(vec2 co){ return fract(sin(dot(co, vec2(12.9898,78.233))) * 43758.5453); }
      void main(){
        vec4 c = texture2D(tDiffuse, vUv);
        float d = distance(vUv, vec2(0.5, 0.52)) * 1.32;
        float vig = smoothstep(0.98, 0.28, d);
        c.rgb *= mix(0.42, 1.0, vig);
        float g = rnd(vUv * res + fract(time) * 91.7) - 0.5;
        c.rgb += g * 0.018;
        gl_FragColor = c;
      }`
  });
  composer.addPass(grade); K.grade = grade;
  composer.addPass(new OutputPass());

  // The camera's walk. s runs from 0 at the entrance to 1 at the deepest end.
  K.walk = { s: 0, sT: 0, yaw: 0, yawT: 0, pitch: 0, pitchT: 0, mx: 0, my: 0 };
  // ?walk=<seconds>: the walk advances by itself, from the entrance to the deepest end over that many seconds.
  const walkSec = Number(QS.get("walk"));
  K.autoWalk = QS.has("walk") && walkSec > 0 ? { dur: walkSec, t0: null } : null;
  K.pos = new THREE.Vector3(); K.look = new THREE.Vector3(); K.focusAmt = 0;
  // The alcoves and the graves. Built lazily, near the camera.
  K.anchors = state.graves.map((g, i) => {
    const slot = lay.slots[i];
    const side = slot ? slot.side : (i % 2 ? 1 : -1);
    const k = slot ? slot.k : lay.kStart - 8;
    return { side, z: worldZ(k), s: sFromZ(worldZ(k), lay), i };
  });
  K.built = new Map(); K.queue = [];
  // Prebuild the graves that the walk starts near, so the first frame already has its stones.
  K.pos.copy(K.curve.getPointAt(QS.has("at") ? Math.min(1, Math.max(0, Number(QS.get("at")) || 0)) : 0));
  for (let i = 0; i < K.anchors.length && i < 60; i++) if (Math.abs(K.anchors[i].z - K.pos.z) < 26) buildGraveAt(i, false);
  K.placeEntrance = true;
  buildEntrance(lay, IMG);
  K.bounds = { z0: worldZ(lay.kStart), z1: worldZ(lay.kEnd) };

  resize();
  new ResizeObserver(resize).observe(stage);
  K.visible = true;
  new IntersectionObserver(([e]) => { K.visible = e.isIntersecting; }).observe(stage);
  bindInput(cv);
  buildMinimap();
  setHUD();
  state.webgl = true;
  K.last = performance.now();
  K.snap = QS.has("grave") || QS.has("at");
  if (QS.has("grave")) { const i = Number(QS.get("grave")); if (state.graves[i]) focusGrave(i, true); }
  if (QS.has("at")) { const at = Math.min(1, Math.max(0, Number(QS.get("at")) || 0)); K.walk.s = K.walk.sT = at; }
  requestAnimationFrame(frame);
  if (DUMP) setTimeout(runDump, 2000);   // the verification frame does not wait for animation frames
  document.documentElement.dataset.graves = "ready";
}

function sFromZ(z, lay) { return Math.min(1, Math.max(0, (worldZ(lay.kStart) - z) / (worldZ(lay.kStart) - worldZ(lay.kEnd)))); }

function resize() {
  if (!K) return;
  const stage = $("#stage");
  const w = stage.clientWidth, h = stage.clientHeight;
  if (!w || !h) return;
  K.renderer.setSize(w, h, false);
  K.camera.aspect = w / h; K.camera.updateProjectionMatrix();
  K.composer.setSize(w * K.renderer.getPixelRatio(), h * K.renderer.getPixelRatio());
  K.bloom.resolution.set(w, h);
  K.grade.uniforms.res.value.set(w * K.renderer.getPixelRatio(), h * K.renderer.getPixelRatio());
}

// The embers come from the pack's own particle sheet: the orange spark in column 1, row 3 of particles.png.
function pickEmber(img) {
  const e = canvas(32, 32), ex = e.getContext("2d");
  ex.imageSmoothingEnabled = false;
  ex.drawImage(img, 8, 24, 8, 8, 0, 0, 32, 32);
  return makeTexture(e, true);
}

function particleSystem(n, map, size, blending, opacity) {
  const geo = new THREE.BufferGeometry();
  const pos = new Float32Array(n * 3), sp = new Float32Array(n), ph = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    pos[i * 3] = (Math.random() - 0.5) * 6; pos[i * 3 + 1] = Math.random() * 4.2; pos[i * 3 + 2] = -Math.random() * 30;
    sp[i] = 0.12 + Math.random() * 0.35; ph[i] = Math.random() * 10;
  }
  geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  const mat = new THREE.PointsMaterial({ map, size, sizeAttenuation: true, transparent: true, opacity, depthWrite: false, blending, color: blending === THREE.AdditiveBlending ? 0xffb070 : 0xd8d0e6, fog: true });
  const points = new THREE.Points(geo, mat);
  points.frustumCulled = false;
  return { points, pos, sp, ph, n };
}

// The entrance slab: a stone to the left of the first step in, with its line cut on it.
function buildEntrance(lay, IMG) {
  const empty = !state.graves.length;
  const label = empty ? { title: "Unclaimed", sub: "The first grave" } : { title: "The Krypt", sub: "Walk on" };
  const seed = hash(empty ? "empty" : "entrance");
  const st = buildStone("slab", IMG.grave_stone, { player: "" }, label, 1024, seed, []);
  const grp = new THREE.Group();
  grp.add(st.root);
  grp.position.set(-2.1, 0, worldZ(lay.kStart - 5));
  grp.rotation.y = Math.PI;
  K.scene.add(grp);
  K.entrance = grp;
}

// Builds a grave in its alcove: the stone with its engraving and ornaments, and the statue of the player.
function yearOf(g) { return (String(g.time).match(/\d{4}/) || [""])[0]; }
function buildGraveAt(i, hi) {
  const g = state.graves[i], a = K.anchors[i];
  const family = familyFor(g), seed = seedFor(g);
  const ornas = ornaments(g);
  const label = { title: g.player, sub: yearOf(g) };
  const extras = { lavaImg: K.IMG.lava_still, lilyImg: K.IMG.waterlily, killerName: g.killer || "" };
  const st = buildStone(family, K.IMG[FAMILY_FILE[family]], g, label, hi ? 1024 : 512, seed, ornas, extras);
  const grp = new THREE.Group();
  grp.add(st.root);
  grp.position.set(a.side * 4.2, 0, a.z);
  grp.rotation.y = a.side * Math.PI / 2;
  K.scene.add(grp);
  // The statue stands in the alcove beside the stone, turned to the corridor. It is a steve skin until the
  // player's skin arrives.
  const sk = statueCanvas(K.IMG.steve);
  // Beside the Weeping Angel the player shields the face, so the pair reads.
  // ?pose=<name> is a verification switch: it sets every statue's pose so each pose can be shot.
  const bundle = buildStatue(QS.get("pose") || (ornas.includes("angel") ? "shield" : poseFor(g)), sk);
  const sg = new THREE.Group();
  sg.add(bundle.root);
  sg.position.set(a.side * 4.55, 0, a.z - 0.95);
  sg.rotation.y = a.side * Math.PI / 2;
  K.scene.add(sg);
  const objs = [grp, sg];
  // The Weeping Angel: a pale statue in the alcove on the other side of the stone, facing the corridor so the
  // hands-over-eyes pose reads from the walk.
  if (ornas.includes("angel")) {
    const ag = new THREE.Group();
    ag.add(buildAngelFigure(K.IMG.steve).root);
    ag.position.set(a.side * 4.55, 0, a.z + 0.95);
    ag.rotation.y = a.side * Math.PI / 2;
    K.scene.add(ag); objs.push(ag);
  }
  const entry = { objs, grp, sg, st, bundle, sk, hi, seed, player: g.player };
  K.built.set(i, entry);
  loadSkin(g.player, g.uuid).then(img => { if (img) setSkin(entry, img); }).catch(() => {});
  return entry;
}
function disposeGraveAt(i) {
  const e = K.built.get(i); if (!e) return;
  for (const obj of e.objs) {
    K.scene.remove(obj);
    obj.traverse(o => { if (o.geometry) o.geometry.dispose(); if (o.material) { if (o.material.map) o.material.map.dispose(); o.material.dispose(); } });
  }
  K.built.delete(i);
}
const SKIN_CACHE = new Map();
function loadSkin(name, uuid) {
  const key = uuid || name;
  if (!SKIN_CACHE.has(key)) {
    const url = `https://api.mineatar.io/skin/${encodeURIComponent(uuid || name)}`;
    SKIN_CACHE.set(key, Promise.race([
      loadImage(url, true),
      new Promise((_, rej) => setTimeout(() => rej(new Error("timeout")), 6000))
    ]).catch(() => null));
  }
  return SKIN_CACHE.get(key);
}
function setSkin(entry, img) {
  try {
    const sk = statueCanvas(img);
    const tex = entry.bundle.textures[0];
    const target = tex.image;
    const ctx = target.getContext("2d");
    ctx.clearRect(0, 0, target.width, target.height);
    ctx.drawImage(sk, 0, 0, target.width, target.height);
    tex.needsUpdate = true;
  } catch { /* the steve fallback stays */ }
}

// Each frame: build the nearest graves, release the far ones, one build a frame at most.
function updateBuilds(camZ) {
  for (let i = 0; i < K.anchors.length; i++) {
    const a = K.anchors[i];
    const d = Math.abs(a.z - camZ);
    const built = K.built.get(i);
    if (!built && d < 26 && state.graves.length && !K.queued?.has(i)) K.queue.push(i);
    if (built && d > 44 && K.focusI !== i) disposeGraveAt(i);
  }
  for (let n = 0; n < 2 && K.queue.length; n++) {
    const i = K.queue.shift();
    if (!K.built.has(i)) buildGraveAt(i, K.focusI === i);
  }
}

// ---- the walk -------------------------------------------------------------------------------
function walkStep(ds) {
  K.autoWalk = null;   // the visitor takes over from ?walk
  K.walk.sT = Math.min(1, Math.max(0, K.walk.sT + ds)); if (K.focusI != null) unfocus();
}
const STEP_BLOCKS = 3;          // one wheel notch or arrow key, in blocks
function perBlock() { return 1 / K.length; }

function currentIndex() {
  if (!state.graves.length) return -1;
  let best = -1, bd = Infinity;
  const camZ = K.pos.z;
  for (let i = 0; i < K.anchors.length; i++) {
    const d = Math.abs(K.anchors[i].z - camZ);
    if (d < bd) { bd = d; best = i; }
  }
  return bd < 3.4 ? best : -1;
}

function focusGrave(i, instant = false) {
  if (!K || !state.graves[i]) return;
  K.focusI = i;
  const a = K.anchors[i];
  K.walk.sT = a.s; K.walk.s = a.s;
  if (!K.built.has(i) || !K.built.get(i).hi) {
    if (K.built.has(i)) disposeGraveAt(i);
    buildGraveAt(i, true);
  }
  if (instant) K.focusAmt = 1;
  showSheet(i);
  setHUD();
  history.replaceState(null, "", "#grave=" + encodeURIComponent(state.graves[i].id));
}
function unfocus() {
  if (K.focusI == null) return;
  const i = K.focusI;
  K.focusI = null;
  hideSheet();
  setHUD();
  history.replaceState(null, "", location.pathname + location.search);
  // Let the stone go back to the low detail when it is far.
  void i;
}
// From the walk: the stone just ahead (dir +1, deeper) or just behind (dir -1), in the order of the feed.
function nextFromWalk(dir) {
  const n = state.graves.length;
  if (!n) return -1;
  const z = K.pos.z;
  if (dir > 0) { for (let i = 0; i < n; i++) if (K.anchors[i].z < z - 0.5) return i; return -1; }
  for (let i = n - 1; i >= 0; i--) if (K.anchors[i].z > z + 0.5) return i;
  return -1;
}
function focusStep(dir) {
  if (K.focusI == null) return;
  const n = state.graves.length;
  focusGrave((K.focusI + dir + n) % n);
}
function focusCamera(i) {
  const a = K.anchors[i];
  // Back along the alcove's centre line, far enough that the stone fills about a third of the frame height
  // (about 2.4 blocks of distance per block of stone), so each family is framed by its own height.
  const H = STONE_HEIGHT[familyFor(state.graves[i])] || 1.8;
  const d = Math.max(3.4, H * 2.4);
  return {
    pos: new THREE.Vector3(a.side * (4.2 - d), 1.25, a.z + 0.45),
    look: new THREE.Vector3(a.side * 4.2, H * 0.5, a.z)
  };
}

function frame(now) {
  if (!K) return;
  requestAnimationFrame(frame);
  try { frameInner(now); } catch (e) { if (!K.logged) { K.logged = 1; console.error("frame", e && e.stack); } }
}
function frameInner(now) {
  if (!K.visible || document.hidden) { K.last = now; return; }
  const dt = Math.min(0.05, (now - K.last) / 1000); K.last = now;
  const t = now / 1000;
  const W = K.walk;
  // Damped walk, yaw and pitch.
  W.s += (W.sT - W.s) * (1 - Math.exp(-dt * 4.2));
  W.yaw += (W.yawT - W.yaw) * (1 - Math.exp(-dt * 5));
  W.pitch += (W.pitchT - W.pitch) * (1 - Math.exp(-dt * 5));
  if (K.autoWalk && K.focusI == null) {
    if (K.autoWalk.t0 == null) K.autoWalk.t0 = now;
    W.sT = Math.min(1, (now - K.autoWalk.t0) / 1000 / K.autoWalk.dur);
  }
  const u = Math.min(1, Math.max(0, W.s));
  const focusing = K.focusI != null;
  const bob = (focusing ? 0 : 1) * (Math.sin(t * 2.3) * 0.012 + Math.sin(t * 1.1) * 0.006);
  const wp = K.curve.getPointAt(u);
  const wl = K.curve.getPointAt(Math.min(1, u + 0.05));
  wp.y = 1.5 + bob;
  wl.y = 1.4 + W.pitch * 1.2;
  // Yaw: turn the look point about the camera.
  const dir = new THREE.Vector3().subVectors(wl, wp);
  dir.applyAxisAngle(new THREE.Vector3(0, 1, 0), W.yaw);
  const walkLook = wp.clone().add(dir);
  let tp = wp, tl = walkLook;
  if (focusing) { const f = focusCamera(K.focusI); tp = f.pos; tl = f.look; }
  K.focusAmt += ((focusing ? 1 : 0) - K.focusAmt) * (1 - Math.exp(-dt * 2.2));
  const k = K.snap ? 1 : 1 - Math.exp(-dt * (focusing ? 2.4 : 3.6));
  K.pos.lerp(tp, k); K.look.lerp(tl, k);
  K.snap = false;
  K.camera.position.copy(K.pos);
  K.camera.lookAt(K.look);
  K.camera.updateMatrixWorld();
  // Lights: the nearest torches get the live lights, the rest keep their glow.
  updateLights(t);
  // Hemi and spot for focus.
  K.hemi.intensity = 1.1 * (1 - 0.5 * K.focusAmt);
  const focusSpotI = K.focusI != null ? K.focusI : -1;
  if (focusSpotI >= 0) {
    const a = K.anchors[focusSpotI];
    K.spot.position.set(a.side * 0.2, 3.4, a.z + 2.4);
    K.spot.target.position.set(a.side * 4.2, 0.6, a.z);
    K.spot.intensity = 14 * K.focusAmt;
  } else K.spot.intensity = 0;
  // Sun follows the camera, so the sky shadows stay near the walk.
  K.sun.position.set(K.pos.x - 6, K.pos.y + 28, K.pos.z - 8);
  K.sun.target.position.set(K.pos.x, 0, K.pos.z);
  // Animation: lava and water frames, ash and embers.
  const lf = Math.floor(t * 10) % 20;
  for (const o of [K.dress.userData.lavaTex, K.dress.userData.waterTex]) {
    if (!o) continue;
    if (o === K.dress.userData.lavaTex) o.offset.y = lf / 20; else o.offset.y = (Math.floor(t * 8) % 32) / 32;
  }
  updateParticles(K.ash, dt, t, K.pos, 0.55);
  updateParticles(K.ember, dt, t, K.pos, 1);
  // Film and bokeh.
  K.grade.uniforms.time.value = t;
  if (K.bokeh) K.bokeh.uniforms.focus.value = Math.max(0.5, K.pos.distanceTo(K.look));
  updateBuilds(K.pos.z);
  K.composer.render();
  updateHUDLive();
}

// The verification frame: build what the seek needs, render the seeked state, read it back in the same task,
// and append it as JSON to the body.
function runDump() {
  if (!K || K.dumped) return;
  K.visible = true;
  const now = performance.now();
  frameInner(now);
  for (let n = 0; n < 80; n++) updateBuilds(K.pos.z);
  frameInner(now + 16);
  dumpShot();
}
function dumpShot() {
  K.dumped = true;
  K.composer.render();
  const png = K.renderer.domElement.toDataURL("image/png");
  const info = {
    url: location.search, focusI: K.focusI ?? null, walkS: K.walk.s, pos: K.pos.toArray(), look: K.look.toArray(),
    built: K.built.size, queued: K.queue.length, graves: state.graves.length
  };
  const sc = document.createElement("script");
  sc.type = "application/json"; sc.id = "dumpshot";
  sc.textContent = JSON.stringify({ png, ...info });
  document.body.appendChild(sc);
}

function updateLights(t) {
  const cam = K.pos;
  const list = K.torches.map(tc => ({ tc, d: tc.group.position.distanceTo(cam) }));
  list.sort((a, b) => a.d - b.d);
  const focusI = K.focusI;
  for (let n = 0; n < K.lights.length; n++) {
    const pl = K.lights[n];
    const e = list[n];
    if (!e || e.d > 22) { pl.intensity = 0; continue; }
    const tc = e.tc;
    const flick = 0.88 + 0.12 * (Math.sin(t * 9.1 + tc.phase) * 0.5 + Math.sin(t * 23.7 + tc.phase * 2) * 0.5);
    const boost = focusI != null && tc.s.slot === focusI ? 1 + 0.4 * K.focusAmt : 1;
    pl.position.set(tc.s.x * 1.1, tc.s.y + 0.5, tc.group.position.z);
    pl.intensity = 9 * flick * boost;
    tc.sprite.material.opacity = 0.9 * flick;
  }
  for (const tc of K.torches) {
    const flick = 0.9 + 0.1 * Math.sin(t * 13 + tc.phase);
    tc.sprite.scale.setScalar(1.7 * flick);
  }
}

function updateParticles(sys, dt, t, cam, power) {
  const { pos, sp, ph, n } = sys;
  const cz = cam.z;
  for (let i = 0; i < n; i++) {
    const j = i * 3;
    pos[j + 1] -= sp[i] * dt * (power > 0.6 ? 0.7 : 0.9);
    pos[j] += Math.sin(t * 0.7 + ph[i]) * 0.09 * dt;
    if (pos[j + 1] < 0.05) pos[j + 1] = 3.8 + Math.random() * 0.4;
    if (pos[j + 2] > cz + 6 || pos[j + 2] < cz - 26) {
      pos[j + 2] = cz - Math.random() * 22 + 4;
      pos[j] = (Math.random() - 0.5) * 6;
    }
  }
  sys.points.geometry.attributes.position.needsUpdate = true;
}

// ---- input ----------------------------------------------------------------------------------
function bindInput(cv) {
  const stage = $("#stage");
  stage.addEventListener("wheel", e => {
    if (!K) return;
    e.preventDefault();
    K.autoWalk = null;
    const d = e.deltaMode === 1 ? e.deltaY * 16 : e.deltaY;
    if (K.focusI != null) { unfocus(); }
    walkStep(d / 100 * STEP_BLOCKS * perBlock());
  }, { passive: false });

  let drag = null;
  stage.addEventListener("pointerdown", e => {
    if (e.target.closest(".sheet, .hud-btn, .strip, .search")) return;
    drag = { x: e.clientX, y: e.clientY, t: performance.now(), moved: 0, id: e.pointerId, sT: K.walk.sT, yaw: K.walk.yawT };
    stage.setPointerCapture?.(e.pointerId);
  });
  stage.addEventListener("pointermove", e => {
    if (!K) return;
    const r = stage.getBoundingClientRect();
    if (!drag) {
      K.walk.pitchT = -((e.clientY - r.top) / r.height - 0.5) * 0.08;
      K.walk.yawT = ((e.clientX - r.left) / r.width - 0.5) * 0.14;
      return;
    }
    const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
    drag.moved = Math.max(drag.moved, Math.hypot(dx, dy));
    if (K.focusI != null) return;
    K.walk.sT = Math.min(1, Math.max(0, drag.sT - dy * 0.034 * perBlock()));
    K.walk.yawT = Math.max(-0.6, Math.min(0.6, drag.yaw + dx * 0.0035));
  });
  const end = e => {
    if (!drag) return;
    const moved = drag.moved, quick = performance.now() - drag.t < 350;
    drag = null;
    if (moved < 8 && (quick || e.type === "pointerup")) pick(e);
  };
  stage.addEventListener("pointerup", end);
  stage.addEventListener("pointercancel", () => { drag = null; });

  document.addEventListener("keydown", e => {
    if (!K || e.target.closest?.("input, textarea, select")) return;
    const k = e.key;
    K.autoWalk = null;
    if (k === "Escape") { if (K.focusI != null) { unfocus(); e.preventDefault(); } return; }
    if (k === "ArrowLeft" || k === "ArrowRight") {
      e.preventDefault();
      const dir = k === "ArrowRight" ? 1 : -1;
      if (K.focusI != null) focusStep(dir);
      else { const n = nextFromWalk(dir); if (n >= 0) focusGrave(n); }
      return;
    }
    if (k === "ArrowDown" || k === "s" || k === "S") { e.preventDefault(); walkStep(STEP_BLOCKS * perBlock()); return; }
    if (k === "ArrowUp" || k === "w" || k === "W") { e.preventDefault(); walkStep(-STEP_BLOCKS * perBlock()); return; }
    if (k === "Enter") {
      if (K.focusI == null) { const c = currentIndex(); if (c >= 0) { e.preventDefault(); focusGrave(c); } }
    }
  });
}
function pick(e) {
  if (!K) return;
  const stage = $("#stage"), r = stage.getBoundingClientRect();
  const ndc = new THREE.Vector2(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
  const ray = new THREE.Raycaster();
  ray.setFromCamera(ndc, K.camera);
  const roots = [];
  for (const [i, v] of K.built) for (const o of v.objs) roots.push([i, o]);
  const hits = ray.intersectObjects(roots.map(r => r[1]), true);
  if (hits.length) {
    const within = (o, root) => { for (let p = o; p; p = p.parent) if (p === root) return true; return false; };
    const hit = roots.find(([, root]) => within(hits[0].object, root));
    if (hit) { focusGrave(hit[0]); return; }
  }
  if (K.focusI != null) { unfocus(); return; }
  const c = currentIndex();
  if (c >= 0) focusGrave(c);
}

// ---- the sheet, the HUD, the minimap ----------------------------------------------------------
function showSheet(i) {
  const g = state.graves[i];
  const sh = $("#sheet");
  sh.hidden = false;
  $("#sheetName").textContent = g.player;
  $("#sheetMsg").textContent = g.message;
  const when = $("#sheetWhen"); when.textContent = "";
  when.append(el("span", "ago", ago(g.time)), document.createTextNode(` · ${absolute(g.time)}`));
  $("#sheetWhere").textContent = where(g);
  $("#sheetKiller").textContent = killerText(g);
  $("#sheetNth").textContent = `Death ${g.nth} of ${g.totalFor} for ${g.player}`;
  const parts = epitaphParts(g);
  const ep = $("#sheetEpitaph"); ep.textContent = "";
  if (parts) ep.append(document.createTextNode(parts[0]), el("b", "", g.player), document.createTextNode(parts[1]));
  else ep.textContent = epitaph(g);
  $("#sheetIndex").textContent = `${i + 1} of ${state.graves.length}`;
  $("#sheetCause").textContent = CAUSE_LABEL[g.cause] || "";
  // The cause row only repeats the killer when a mob or another player is named, so it goes then.
  const repeats = !!g.killer && (g.cause === "mob" || g.cause === "player");
  $("#sheetCauseRow").hidden = repeats;
  $("#sheetCause").hidden = repeats;
  state.sheetOpen = true;
}
function hideSheet() {
  $("#sheet").hidden = true;
  state.sheetOpen = false;
}
function setHUD() {
  const hud = $("#hud");
  if (!K) return;
  if (!state.graves.length) { $("#hudName").textContent = "The Krypt"; $("#hudSub").textContent = "No stones yet. The first will be cut here."; }
  const i = K.focusI != null ? K.focusI : currentIndex();
  const g = i >= 0 ? state.graves[i] : null;
  $("#hudName").textContent = g ? g.player : "Walking the Krypt";
  $("#hudSub").textContent = g ? `${g.message}` : (state.graves.length ? "Scroll to walk. Click a stone to read it." : "");
  hud.dataset.focus = K.focusI != null ? "1" : "0";
  // Ticks.
  for (const t of document.querySelectorAll(".tick")) t.classList.toggle("on", Number(t.dataset.i) === i);
}
let hudAt = 0;
function updateHUDLive() {
  const now = performance.now();
  if (now - hudAt < 120) { $("#marker").style.left = (K.walk.s * 100).toFixed(2) + "%"; return; }
  hudAt = now;
  if (K.focusI == null) {
    const i = currentIndex();
    const cur = i >= 0 ? state.graves[i] : null;
    const name = cur ? cur.player : "Walking the Krypt";
    if ($("#hudName").textContent !== name) setHUD();
  }
  $("#marker").style.left = (K.walk.s * 100).toFixed(2) + "%";
  for (const t of document.querySelectorAll(".tick")) t.classList.toggle("near", Math.abs(Number(t.dataset.s) - K.walk.s) < 0.012);
}
function buildMinimap() {
  const strip = $("#ticks"); strip.textContent = "";
  state.graves.forEach((g, i) => {
    const a = K.anchors[i];
    const b = el("button", "tick");
    b.type = "button"; b.dataset.i = i; b.dataset.s = a.s.toFixed(4);
    b.style.left = (a.s * 100).toFixed(2) + "%";
    b.setAttribute("aria-label", `${g.player}, ${absolute(g.time)}`);
    b.title = `${g.player} · ${absolute(g.time)}`;
    b.addEventListener("click", () => focusGrave(i));
    strip.append(b);
  });
  const track = $("#strip");
  track.addEventListener("pointerdown", e => {
    if (e.target.closest(".tick")) return;
    const r = track.getBoundingClientRect();
    const s = Math.min(1, Math.max(0, (e.clientX - r.left) / r.width));
    if (K.focusI != null) unfocus();
    K.walk.sT = s;
  });
}
function jumpNewest() {
  if (!state.graves.length) return;
  focusGrave(state.graves.length - 1);
}
function searchPlayer(name) {
  const idx = state.graves.map((g, i) => [g, i]).filter(([g]) => g.player.toLowerCase() === name.toLowerCase());
  if (!idx.length) { $("#searchNote").textContent = `No stone for "${name}".`; return; }
  $("#searchNote").textContent = `${idx.length} ${idx.length === 1 ? "stone" : "stones"} for ${idx[0][0].player}. Newest shown.`;
  focusGrave(idx[idx.length - 1][1]);
}

// Buttons in the HUD and the sheet.
function bindUI() {
  $("#btnNewest")?.addEventListener("click", jumpNewest);
  $("#btnPrev")?.addEventListener("click", () => focusStep(-1));
  $("#btnNext")?.addEventListener("click", () => focusStep(1));
  $("#btnBack")?.addEventListener("click", () => unfocus());
  $("#btnHere")?.addEventListener("click", () => { const c = currentIndex(); if (c >= 0) focusGrave(c); });
  const s = $("#search");
  s.addEventListener("change", () => { if (s.value.trim()) searchPlayer(s.value.trim()); });
  s.addEventListener("keydown", e => { if (e.key === "Enter") { e.preventDefault(); if (s.value.trim()) searchPlayer(s.value.trim()); } });
  // The flat list and the drawer always exist; the drawer is for the boards.
}

// ---- start ----------------------------------------------------------------------------------
window.addEventListener("error", e => console.error("ERR", e.message, e.error && e.error.stack));
bindUI();
state.webgl = checkWebGL();
load().then(() => {
  if (state.webgl && !state.reduced && state.graves.length >= 0) { /* the Krypt starts from renderPage */ }
});
