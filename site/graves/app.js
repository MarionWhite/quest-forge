// The Wall of Graves, page logic: the feed, the Krypt in three.js, the walk, the focus sheet, the minimap,
// the boards and the 2D fallback. Modules beside this file: data.js, models.js, model.js, textures.js, krypt.js.
import * as THREE from "three";
import { EffectComposer } from "three/addons/postprocessing/EffectComposer.js";
import { RenderPass } from "three/addons/postprocessing/RenderPass.js";
import { UnrealBloomPass } from "three/addons/postprocessing/UnrealBloomPass.js";
import { ShaderPass } from "three/addons/postprocessing/ShaderPass.js";
import { OutputPass } from "three/addons/postprocessing/OutputPass.js";
import {
  normalize, killerText, epitaph, epitaphParts, familyFor, ornaments, poseFor, seedFor,
  CAUSE_LABEL, CAUSE_NOUN, hash
} from "./data.js";
import { makePlan, makeWorld, slotFrame, patchBake, legDir, legMap, legYaw, KINDS } from "./krypt.js";
import { makeDresser } from "./dress.js";
import { BLOCK_TEX_FILES, DECOR_TEX, TINTED } from "./blocks.js";
import { addDecor } from "./dressx.js";
import { demoGraves } from "./demo.js";
import { makeFx } from "./fx.js";
import { makeLightFx } from "./lightfx.js";
import { makeAmbience, sfxLog } from "./kaudio.js";
import { audio } from "../lib/qfaudio.js";
import { buildStone, buildStatue, buildAngelFigure, makeTexture, imageTexture, statueCanvas, STONE_HEIGHT } from "./model.js";
import { loadImage, canvas, glowCanvas, dotCanvas, skyCanvas, tintImage } from "./textures.js";

const $ = (s) => document.querySelector(s);
const DEMO = new URLSearchParams(location.search).has("demo");
const DEMO_N = Number(new URLSearchParams(location.search).get("demo")) || 0;   // ?demo=1000 and ?demo=10000 make synthetic graves
const DUMP = new URLSearchParams(location.search).has("dump");   // verification: one rendered frame, dumped into the DOM
const QS = new URLSearchParams(location.search);
const FAMILY_FILE = { slab: "grave_stone", tomb: "grave_zerk", pillar: "grave_pillar", wood: "grave_wood", knight: "grave_knight",
  cross: "grave_stone", angel: "grave_stone", skeleton: "skeleton" };
const TEX_FILES = ["stone", "cobblestone", "cobblestone_mossy", "stonebrick", "stonebrick_mossy", "stonebrick_cracked",
  "gravel", "obsidian", "bedrock", "coal_ore", "iron_ore", "web", "vine", "netherrack", "glowstone", "iron_bars", "dirt",
  "bookshelf", "nether_brick", "soul_sand", "mob_spawner", "fire_layer_0", "bone", "planks_oak", "log_oak", "log_oak_top",
  "lava_still", "water_still", "torch_on", "rail_normal", "waterlily", "particles", "steve",
  "grave_stone", "grave_zerk", "grave_pillar", "grave_wood", "grave_knight", "skeleton",
  "furnace_side", "furnace_top", "dispenser_front_horizontal", "lever", "trip_wire", "trip_wire_source", "door_iron_lower",
  "door_iron_upper", "endframe_top", "endframe_side", "endframe_eye", "gold_block", "diamond_block", "lapis_block",
  "emerald_block", "stonebrick_carved", "iron_block", "chest", "end_sky"];
for (const f of BLOCK_TEX_FILES.concat(DECOR_TEX)) if (!TEX_FILES.includes(f)) TEX_FILES.push(f);

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
//   getWalk() -> { s, speed, activeSeconds, depth, segment }
//       s              0..1 along the path (damped, what the camera shows)
//       segment        the current segment's kind, in walk order: crypt, mine, catacomb, ossuary, flood, spidermine,
//                      temple, dungeon, library, vault, chasm, stairs, fortress, deep, stronghold (the finale)
//       speed          blocks per second of walking right now (0 when standing)
//       activeSeconds  seconds the visitor has spent actually walking, not paused, not focused on a stone
//       depth          0..1, the same as s but eased: 0 at the entrance crypt, 1 in the nether depths
//   corners         [{ s, pos: Vector3, dir: Vector3, side }] where the path turns or a side passage opens:
//                   pos is the floor-level centre of the turn, dir the unit heading after it, side -1 left / +1 right
//   carve(min, max) min/max are [x, y, z] (or Vector3) block coordinates, inclusive. Removes the blocks in that box
//                   and rebuilds only the chunks it touches (16 x 16 blocks, full height). Returns how many blocks went.
//                   The outer shell of the world never goes. Carves stack; restore() undoes all of them.
//   restore()       puts back every carved block and rebuilds those chunks. Returns how many came back.
//   solidAt(x,y,z)  true when the block holding the world point is not air, water or lava (carves included).
//   blockAt(x,y,z)  the block name there: air, stone, cobblestone, mossy_cobblestone, stonebrick, mossy_stonebrick,
//                   cracked_stonebrick, gravel, coal_ore, iron_ore, obsidian, bedrock, netherrack, glowstone, water,
//                   nether_brick, soul_sand, bookshelf, planks, log, lava, dirt (more as segments add them).
//                   Decor (torches, webs, rails) is not blocks; ask the scene for those.
//   cornersNear(s, range)  the same list for any place on the path: s is 0..1, range in blocks (default 150).
//                   `corners` itself holds the ones within 150 blocks of the walker and is replaced as the walk goes.
//   gaps            [{ s, pos: Vector3, dir: Vector3, width, kind: 'lava' | 'water', side }] the broken stretches of
//                   floor near the walker (within 150 blocks), refreshed like corners. pos is the floor-level centre
//                   of the gap's first block, dir the unit heading across it, width 2 to 3 blocks, side the bend's
//                   turn (-1 left, 0 straight on, +1 right).
//   event 'krypt-gap'  fired on window just before the walker jumps a gap: detail { gap, takeover() }. A listener that
//                   calls takeover() animates the jump itself (a failed jump, say); otherwise the normal jump plays.
//   light           { scale(k, seconds), flicker(pos, seconds), off(pos, seconds), pulse(seconds) }: effects on the
//                   Krypt's lights. Every one eases in and ends restored. pos is [x,y,z] or a Vector3; flicker and off
//                   act on the nearest torch (and return false when none is near).
//   getWalk() also gives stratum (0-based index) and stratumName.
//   takeover(on)    true pauses the camera control and walk input (and own footsteps) while a scare plays;
//                   false restores them. The scare may move window.__krypt.camera while taken over.
const __kryptHold = { on: false };
window.__krypt = {
  scene: null, camera: null, renderer: null, composer: null, corners: [],
  gaps: [], cornersNear() { return []; },
  light: { scale() {}, flicker() { return false; }, off() { return false; }, pulse() {} },
  getWalk() { return { s: 0, speed: 0, activeSeconds: 0, depth: 0, segment: "crypt", stratum: 0, stratumName: "" }; },
  takeover(on) { __kryptHold.on = !!on; },
  carve() { return 0; }, restore() { return 0; }, solidAt() { return false; }, blockAt() { return "air"; }
};

// --- scares: begin (owned by scares.js) ---
import("./scares.js").then((m) => m.initScares({ enabled: () => !!state.webgl && !state.reduced })).catch((e) => console.warn("scares", e));
// --- scares: end ---

// --- mood: begin (owned by mood.js) ---
import("./mood.js").then((m) => m.initMood()).catch((e) => console.warn("mood", e));
// --- mood: end ---

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
    let json;
    if (DEMO && DEMO_N > 25) json = demoGraves(DEMO_N);
    else { const r = await fetch(url, { cache: "no-store" }); if (!r.ok) throw new Error(String(r.status)); json = await r.json(); }
    const n = normalize(json);
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
  const names = count(g => g.player).sort((a, b) => a[0].localeCompare(b[0])).slice(0, 400);
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
  const list = state.graves.slice(-300).reverse();
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
const UP = new THREE.Vector3(0, 1, 0);
const smooth01 = (x) => { x = Math.min(1, Math.max(0, x)); return x * x * (3 - 2 * x); };

async function startKrypt() {
  if (K) return;
  K = {};
  const stage = $("#stage"), cv = $("#gl");
  const phone = state.phone;
  const renderer = new THREE.WebGLRenderer({ canvas: cv, antialias: false, powerPreference: "high-performance" });
  renderer.setPixelRatio(phone ? 0.5 : Math.min(devicePixelRatio, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.15;
  K.renderer = renderer;

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x07060b);
  scene.fog = new THREE.FogExp2(0x07060b, 0.04);
  K.scene = scene;
  // The End's sky: a dome of the vanilla end_sky texture around the camera, shown only where the void is open (void_bridge legs).
  try {
    const cv = document.createElement("canvas"); cv.width = 1024; cv.height = 512; const g = cv.getContext("2d");
    g.fillStyle = "#07040f"; g.fillRect(0, 0, 1024, 512);
    const tex = new THREE.CanvasTexture(cv); tex.magFilter = THREE.NearestFilter; tex.minFilter = THREE.LinearFilter;
    const star = () => { let r = 12345; const f = () => (r = (r * 1664525 + 1013904223) >>> 0) / 4294967296; for (let i = 0; i < 2200; i++) { const x = f() * 1024, y = f() * 512, b = f(); g.fillStyle = b > 0.9 ? "#ffffff" : b > 0.5 ? "#d6c4ff" : "#9a82e0"; const z = b > 0.97 ? 3 : b > 0.8 ? 2 : 1; g.fillRect(x | 0, y | 0, z, z); } tex.needsUpdate = true; };
    const im = new Image(); im.onload = () => { g.globalAlpha = 0.09; for (let x = 0; x < 1024; x += im.width * 2) for (let y = 0; y < 512; y += im.height * 2) g.drawImage(im, x, y, im.width * 2, im.height * 2); g.globalAlpha = 1; star(); }; im.onerror = star; im.src = "tex/end_sky.png"; star();
    K.endSky = new THREE.Mesh(new THREE.SphereGeometry(110, 32, 20), new THREE.MeshBasicMaterial({ map: tex, side: THREE.BackSide, fog: false, depthWrite: false }));
    K.endSky.renderOrder = -10; K.endSky.visible = false; K.endSky.frustumCulled = false; scene.add(K.endSky);
  } catch (e) { K.endSky = null; }
  const camera = new THREE.PerspectiveCamera(58, 1, 0.05, 140);
  K.camera = camera; K.baseFov = 58;

  // Textures: the pack's own files, loaded once; the tinted ones (grass, leaves) are made from their grey originals.
  const IMG = {};
  await Promise.all(TEX_FILES.map(async n => { try { IMG[n] = await loadImage(`tex/${n}.png`); } catch { /* optional */ } }));
  try { IMG.skull_tex = await loadImage("../lib/mc/tex/entity/skeleton/skeleton.png"); } catch { /* the graves' own skeleton sheet stands in */ }
  for (const [name, [src, hex, ov]] of Object.entries(TINTED)) if (IMG[src]) IMG[name] = tintImage(IMG[src], hex, ov ? IMG[ov] : null);
  K.IMG = IMG;

  // The world: the plan (every leg, from the seed and the slot count), and the chunks around the walker.
  const plan = makePlan({ n: state.graves.length, force: QS.has("kinds") ? QS.get("kinds").split(",") : null });
  K.plan = plan; K.length = plan.length;
  K.agg = { torches: [], dyn: [], emit: [], spots: { fire: [], lava: [], drip: [] }, holes: [], version: 0 };
  const dresser = makeDresser(IMG);
  addDecor(dresser, IMG);
  K.dresser = dresser;
  const world = makeWorld({ plan, images: IMG, scene, dresser, radius: phone ? 66 : 84, array: renderer.capabilities.isWebGL2 && !QS.has("noarray"), onChange: (agg) => { K.agg = agg; } });
  K.world = world;
  K.lightAt = (x, y, z, nx, ny, nz, o) => world.lightAt(x, y, z, nx, ny, nz, o);
  K.fx = makeFx(scene, () => K.agg.emit, { phone });
  K.profTmp = {}; K.prof = plan.profileAtD(0, K.profTmp); K.stratum = K.prof.stratum;

  // The violet sky, far above the cracks; it rides with the camera, so it has no parallax, like a real sky.
  const skyTex = makeTexture(skyCanvas(9));
  const sky = new THREE.Mesh(new THREE.PlaneGeometry(300, 300), new THREE.MeshBasicMaterial({ map: skyTex, fog: false, depthWrite: false }));
  sky.rotation.x = Math.PI / 2; sky.position.y = 70; sky.renderOrder = -1;
  scene.add(sky); K.sky = sky;

  // Light: a faint fill for the figures, and the nearest few torches, fires and seams as live point lights. The rest
  // of the light is baked into the blocks (krypt.js), so it needs no draw calls.
  const hemi = new THREE.HemisphereLight(0x7d78a8, 0x2a1d2c, 0.32);
  scene.add(hemi); K.hemi = hemi;
  K.lights = [];
  const nLive = phone ? 3 : 4;
  for (let n = 0; n < nLive; n++) {
    const pl = new THREE.PointLight(0xffa552, 0, 12, 2);
    scene.add(pl); K.lights.push({ pl, src: null, amt: 0 });
  }
  const spot = new THREE.SpotLight(0xffc27a, 0, 14, 0.5, 0.7, 1.4);
  scene.add(spot, spot.target); K.spot = spot;

  // Post: a restrained bloom (only what is brighter than the screen can show), vignette and grain, output.
  const composer = new EffectComposer(renderer);
  K.composer = composer;
  composer.addPass(new RenderPass(scene, camera));
  const bloom = new UnrealBloomPass(new THREE.Vector2(256, 256), 0.35, 0.45, 1.1);
  composer.addPass(bloom); K.bloom = bloom;
  if (phone) bloom.enabled = false;   // the bloom is about fifteen draws; on a phone the frame budget goes to the world
  const grade = new ShaderPass({
    uniforms: { tDiffuse: { value: null }, time: { value: 0 }, res: { value: new THREE.Vector2(1, 1) } },
    vertexShader: "varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }",
    fragmentShader: `uniform sampler2D tDiffuse; uniform float time; uniform vec2 res; varying vec2 vUv;
      float rnd(vec2 co){ return fract(sin(dot(co, vec2(12.9898,78.233))) * 43758.5453); }
      void main(){
        vec4 c = texture2D(tDiffuse, vUv);
        float d = distance(vUv, vec2(0.5, 0.52)) * 1.3;
        float vig = smoothstep(1.0, 0.3, d);
        c.rgb *= mix(0.6, 1.0, vig);
        float g = rnd(vUv * res + fract(time) * 91.7) - 0.5;
        c.rgb += g * 0.012 * (0.4 + c.rgb);
        gl_FragColor = c;
      }`
  });
  composer.addPass(grade); K.grade = grade;
  composer.addPass(new OutputPass());

  // The camera's walk. s runs from 0 at the entrance to 1 at the deepest end; d = s * length is the block count.
  K.walk = { s: 0, sT: 0, yaw: 0, yawT: 0, pitch: 0, pitchT: 0, mx: 0, my: 0 };
  const walkSec = Number(QS.get("walk"));
  K.autoWalk = QS.has("walk") && walkSec > 0 ? { dur: walkSec, t0: null } : null;
  K.pos = new THREE.Vector3(); K.look = new THREE.Vector3(); K.focusAmt = 0;
  K.fYaw = 0; K.fPitch = 0; K.fOff = new THREE.Vector3(); K.speed = 0; K.activeSeconds = 0; K.held = false;
  K.pf = { lock: -1, hold: 0, dense: 0, pace: 0, rest: 0, side: 0, yaw: 0, vel: 0, gSide: 0, gQuiet: 9, sideT: 9 };   // the passing focus (frameInner)
  if (QS.has("dbg")) window.__kdbg = { K, state };   // verification hook: the yaw metric reads K.fYaw
  K.anchorCache = new Map();
  K.built = new Map(); K.queue = [];
  // Where to start: ?at (0..1 of the whole path), ?grave=N, ?stratum=k, ?gap=g with ?jx (blocks into the jump).
  let d0 = 0;
  if (QS.has("at")) d0 = Math.min(1, Math.max(0, Number(QS.get("at")) || 0)) * plan.length;
  if (QS.has("stratum")) { const st = plan.strata[Math.min(plan.strata.length - 1, Math.max(0, Number(QS.get("stratum")) || 0))]; d0 = st.d0 + (Number(QS.get("sd")) || 8); }
  if (QS.has("gap") && plan.gaps.length) { const g = plan.gaps[Math.min(plan.gaps.length - 1, Math.max(0, Number(QS.get("gap")) || 0))]; d0 = g.d0 - 0.5 + (Number(QS.get("jx")) || 0); }
  if (QS.has("leg")) { const lg = plan.legs[Math.min(plan.legs.length - 1, Math.max(0, Number(QS.get("leg")) || 0))]; d0 = lg.dStart + (lg.dEnd - lg.dStart) * (QS.has("lf") ? Number(QS.get("lf")) : 0.45); }
  if (QS.has("grave")) { const gi = Number(QS.get("grave")); if (plan.slots[gi]) d0 = plan.slots[gi].d; }
  K.startD = Math.min(plan.length, Math.max(0, d0));
  plan.pointAt(K.startD, _pt); K.pos.set(_pt[0], _pt[1], _pt[2]);
  world.ensure(K.pos.x, K.pos.z, 56);
  for (const i of nearSlots(K.startD, 30)) if (anchorOf(i).p.distanceTo(K.pos) < 30) buildGraveAt(i, false);
  buildEntrance(plan, IMG);

  // Sound: the gate unlocks it. Under ?dump and ?nogate there is no gate and no sound.
  const aud = { get torches() { return K.agg.torches; }, get spots() { return K.agg.spots; }, get version() { return K.agg.version; }, passages: plan.spots };
  K.amb = makeAmbience({ a: aud });
  K.gateOpen = (DUMP && !QS.has("gate")) || QS.has("nogate");
  stage.dataset.gate = K.gateOpen ? "0" : "1";
  resize();
  new ResizeObserver(resize).observe(stage);
  K.visible = true;
  new IntersectionObserver(([e]) => { K.visible = e.isIntersecting; }).observe(stage);
  bindInput(cv);
  buildMinimap();
  setHUD();
  state.webgl = true;
  K.last = performance.now();
  K.snap = QS.has("grave") || QS.has("at") || QS.has("stratum") || QS.has("gap") || QS.has("leg");
  K.walk.s = K.walk.sT = K.startD / plan.length;
  if (QS.has("grave")) { const i = Number(QS.get("grave")); if (state.graves[i]) focusGrave(i, true); }
  publishKrypt();
  requestAnimationFrame(frame);
  if (DUMP) setTimeout(runDump, 2500);   // the verification frame does not wait for animation frames
  document.documentElement.dataset.graves = "ready";
}
const _pt = [0, 0, 0], _pt2 = [0, 0, 0];

// The anchor of grave i: its slot's frame (built on demand, a few hundred kept).
function anchorOf(i) {
  let a = K.anchorCache.get(i);
  if (a) return a;
  const slot = K.plan.slots[i];
  const fr = slotFrame(K.plan, slot);
  a = { i, side: slot.side, s: slot.d / K.length, d: slot.d, frame: fr, p: fr.stone, leg: slot.leg };
  // Its wall as seen walking its own stretch of path (+1 left, -1 right, the sign of a turn toward it): a corner ahead
  // can put a stone on the far side of the current heading, but it stays on the same wall.
  const p0 = [0, 0, 0], p1 = [0, 0, 0]; K.plan.pointAt(Math.max(0, slot.d - 1), p0); K.plan.pointAt(Math.min(K.length, slot.d + 1), p1);
  a.ys = (p1[0] - p0[0]) * fr.out.z - (p1[2] - p0[2]) * fr.out.x > 0 ? -1 : 1;
  K.anchorCache.set(i, a);
  if (K.anchorCache.size > 700) K.anchorCache.delete(K.anchorCache.keys().next().value);
  return a;
}
// The indices of the graves within `range` blocks of path distance d.
function nearSlots(d, range) {
  const n = Math.min(state.graves.length, K.plan.slots.length), out = [];
  if (!n) return out;
  const slots = K.plan.slots;
  for (let i = Math.max(0, K.plan.slotAtD(d - range)); i < n && slots[i].d <= d + range; i++) if (slots[i].d >= d - range) out.push(i);
  return out;
}

// Fill the scares contract (see the top of the file).
function publishKrypt() {
  const kr = window.__krypt;
  kr.scene = K.scene; kr.camera = K.camera; kr.renderer = K.renderer; kr.composer = K.composer;
  const toCorner = (c) => ({ s: c.d / K.length, pos: new THREE.Vector3(c.x, c.y, c.z), dir: new THREE.Vector3(c.dx, 0, c.dz), side: c.side, kind: c.kind });
  kr.cornersNear = (s, range = 150) => K.plan.corners.filter(c => Math.abs(c.d - s * K.length) <= range).map(toCorner);
  K.refreshNear = (force) => {
    const d = K.walk.s * K.length;
    if (!force && K.nearAt != null && Math.abs(d - K.nearAt) < 15) return;
    K.nearAt = d;
    kr.corners = K.plan.corners.filter(c => Math.abs(c.d - d) <= 150).map(toCorner);
    kr.gaps = K.plan.gaps.filter(g => Math.abs(g.d - d) <= 150).map(g => ({ s: g.d / K.length, pos: new THREE.Vector3(g.x, g.y, g.z), dir: new THREE.Vector3(g.dx, 0, g.dz), width: g.width, kind: g.kind, side: g.side }));
  };
  K.refreshNear(true);
  K.lightFx = makeLightFx({ torches: () => K.agg.torches, hemi: K.hemi });
  const asV = (v) => (Array.isArray(v) ? v : [v.x, v.y, v.z]);
  const asPos = (v) => (Array.isArray(v) ? { x: v[0], y: v[1], z: v[2] } : v);
  kr.light = {
    scale: (k, sec) => K.lightFx.scale(k, sec), flicker: (p, sec) => K.lightFx.flicker(asPos(p), sec),
    off: (p, sec) => K.lightFx.off(asPos(p), sec), pulse: (sec) => K.lightFx.pulse(sec)
  };
  kr.getWalk = () => ({ s: K.walk.s, speed: K.speed, activeSeconds: K.activeSeconds, depth: smooth01(K.walk.s), segment: (K.prof && K.prof.kind) || "crypt", stratum: K.stratum ? K.stratum.index : 0, stratumName: K.stratum ? K.stratum.name : "" });
  kr.carve = (mn, mx) => K.world.carve(asV(mn), asV(mx));
  kr.restore = () => K.world.restore();
  kr.solidAt = (x, y, z) => K.world.solidAt(x, y, z);
  kr.blockAt = (x, y, z) => K.world.blockAt(x, y, z);
  kr.takeover = (on) => {
    on = !!on; if (on === K.held) return;
    K.held = on; __kryptHold.on = on;
    if (!on) {
      // Hand the camera back: start the damped walk from wherever the scare left it.
      K.pos.copy(K.camera.position);
      const f = new THREE.Vector3(0, 0, -1).applyQuaternion(K.camera.quaternion);
      K.look.copy(K.pos).addScaledVector(f, 5);
      K.last = performance.now();
    }
  };
  window.dispatchEvent(new CustomEvent("krypt-ready"));
}

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

// The entrance slab: a stone in the first corridor with its line cut on it, turned to face the visitor.
function buildEntrance(plan, IMG) {
  const empty = !state.graves.length;
  const label = empty ? { title: "Unclaimed", sub: "The first grave" } : { title: "The Krypt", sub: "Walk on" };
  const seed = hash(empty ? "empty" : "entrance");
  const st = buildStone("slab", IMG.grave_stone, { player: "" }, label, 1024, seed, []);
  const grp = new THREE.Group();
  grp.add(st.root);
  const leg = plan.legs[0];
  const [x, z] = legMap(leg, -2.1, 6.0);
  grp.position.set(x, leg.y0, z);
  grp.rotation.y = Math.PI + legYaw(leg);
  bakeObject(grp, new THREE.Vector3(x, leg.y0 + 1.2, z), new THREE.Vector3(0, 0, 1));
  K.scene.add(grp);
  K.entrance = grp;
}

// Figures take their ambient from the same bake as the walls (as a fixed emissive-times-albedo term).
function bakeObject(root, at, normal) {
  const c = K.lightAt(at.x, at.y, at.z, normal.x, normal.y, normal.z, { omni: true });
  const v = new THREE.Vector3(c[0], c[1], c[2]);
  root.traverse(o => {
    if (!o.isMesh || !o.material) return;
    const ms = Array.isArray(o.material) ? o.material : [o.material];
    for (const m of ms) if ((m.isMeshLambertMaterial || m.isMeshStandardMaterial) && !m.onBeforeCompile.toString().includes("uBake")) patchBake(m, { fixed: v });
  });
}

// Builds a grave in its alcove: the stone with its engraving and ornaments, and the statue of the player.
function yearOf(g) { return (String(g.time).match(/\d{4}/) || [""])[0]; }
function buildGraveAt(i, hi) {
  const g = state.graves[i], a = anchorOf(i), fr = a.frame;
  const family = familyFor(g), seed = seedFor(g);
  const ornas = ornaments(g);
  const label = { title: g.player, sub: yearOf(g) };
  const extras = { lavaImg: K.IMG.lava_still, lilyImg: K.IMG.waterlily, killerName: g.killer || "" };
  const st = buildStone(family, K.IMG[FAMILY_FILE[family]], g, label, hi ? 1024 : 512, seed, ornas, extras);
  const grp = new THREE.Group();
  grp.add(st.root);
  grp.position.copy(fr.stone);
  grp.rotation.y = fr.yaw;
  const amb = new THREE.Vector3(fr.stone.x, fr.stone.y + 1.1, fr.stone.z);
  bakeObject(grp, amb, fr.out.clone().negate());
  K.scene.add(grp);
  // The statue stands in the alcove beside the stone, turned to the corridor. It is a steve skin until the
  // player's skin arrives.
  const sk = statueCanvas(K.IMG.steve);
  // Beside the Weeping Angel the player shields the face, so the pair reads.
  // ?pose=<name> is a verification switch: it sets every statue's pose so each pose can be shot.
  const bundle = buildStatue(QS.get("pose") || (ornas.includes("angel") ? "shield" : poseFor(g)), sk);
  const sg = new THREE.Group();
  sg.add(bundle.root);
  sg.position.copy(fr.statue);
  sg.rotation.y = fr.yaw;
  bakeObject(sg, new THREE.Vector3(fr.statue.x, fr.statue.y + 1, fr.statue.z), fr.out.clone().negate());
  K.scene.add(sg);
  const objs = [grp, sg];
  // The Weeping Angel: a pale statue in the alcove on the other side of the stone, facing the corridor so the
  // hands-over-eyes pose reads from the walk.
  if (ornas.includes("angel")) {
    const ag = new THREE.Group();
    ag.add(buildAngelFigure(K.IMG.steve).root);
    ag.position.copy(fr.angel);
    ag.rotation.y = fr.yaw;
    bakeObject(ag, new THREE.Vector3(fr.angel.x, fr.angel.y + 1, fr.angel.z), fr.out.clone().negate());
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

// Each frame: build the nearest graves, release the far ones, two builds a frame at most; stream the world's chunks.
function updateBuilds(cam, chunks = 1) {
  if (K.world) K.world.update(cam.x, cam.z, chunks);
  const d = K.held ? cam.distanceTo(K.pos) * 0 + K.walk.s * K.length : K.walk.s * K.length;
  for (const i of nearSlots(d, 40)) {
    const a = anchorOf(i);
    if (!K.built.has(i) && a.p.distanceTo(cam) < 30 && !K.queue.includes(i)) K.queue.push(i);
  }
  for (const [i] of K.built) { const a = anchorOf(i); if (a.p.distanceTo(cam) > 52 && K.focusI !== i) disposeGraveAt(i); }
  for (let n = 0; n < 2 && K.queue.length; n++) {
    const i = K.queue.shift();
    if (!K.built.has(i)) buildGraveAt(i, K.focusI === i);
  }
}

// ---- the walk -------------------------------------------------------------------------------
function walkStep(ds) {
  if (K.held || !K.gateOpen) return;
  K.autoWalk = null; K.rush = null;   // the visitor takes over from ?walk and from a rush
  K.walk.sT = Math.min(1, Math.max(0, K.walk.sT + ds)); if (K.focusI != null) unfocus();
}
const STEP_BLOCKS = 3;          // one wheel notch or arrow key, in blocks
function perBlock() { return 1 / K.length; }

// The stone nearest along the path, within about three blocks of the camera's place on it.
function currentIndex() {
  const n = state.graves.length;
  if (!n) return -1;
  const d = K.walk.s * K.length, slots = K.plan.slots;
  const i = Math.min(n - 1, Math.max(0, K.plan.slotAtD(d)));
  let best = -1, bd = Infinity;
  for (const j of [i - 1, i, i + 1]) if (j >= 0 && j < n) { const q = Math.abs(slots[j].d - d); if (q < bd) { bd = q; best = j; } }
  return bd < 3.4 ? best : -1;
}

function focusGrave(i, instant = false, rush = false) {
  if (!K || !state.graves[i]) return;
  const a = anchorOf(i);
  if (rush && !instant && Math.abs(a.d - K.walk.s * K.length) > 90) { rushTo(a.d, () => focusGrave(i, true)); return; }
  K.focusI = i;
  K.walk.sT = a.s; K.walk.s = a.s;
  if (instant) { K.world.ensure(a.p.x, a.p.z, 50); }
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
  K.focusI = null;
  hideSheet();
  setHUD();
  history.replaceState(null, "", location.pathname + location.search);
}
// From the walk: the stone just ahead (dir +1, deeper) or just behind (dir -1), in the order of the feed.
function nextFromWalk(dir) {
  const n = state.graves.length;
  if (!n) return -1;
  const d = K.walk.s * K.length, eps = 0.5, slots = K.plan.slots;
  if (dir > 0) { let i = Math.max(0, K.plan.slotAtD(d + eps)); while (i < n && slots[i].d <= d + eps) i++; return i < n ? i : -1; }
  let i = Math.min(n - 1, K.plan.slotAtD(d - eps)); while (i >= 0 && slots[i].d >= d - eps) i--; return i >= 0 ? i : -1;
}
function focusStep(dir) {
  if (K.focusI == null) return;
  const n = state.graves.length;
  focusGrave((K.focusI + dir + n) % n, false, true);
}
function focusCamera(i) {
  const a = anchorOf(i), fr = a.frame;
  // Back along the alcove's centre line, far enough that the stone fills about a third of the frame height
  // (about 2.4 blocks of distance per block of stone), so each family is framed by its own height.
  const H = STONE_HEIGHT[familyFor(state.graves[i])] || 1.8;
  const d = Math.max(3.4, H * 2.4);
  const y0 = fr.centre.y;
  const p = fr.camAt(d); p.y = y0 + 1.25;
  const l = fr.stone.clone(); l.y = y0 + H * 0.5;
  return { pos: p, look: l };
}

// A long way down the path is never a hard cut: the view rushes forward into fog and a blur, the world is built behind
// it, and the fog clears as the last stretch glides in. `then` runs when the walker is in place.
function rushTo(dTarget, then, lead = 26) {
  if (!K.gateOpen && !DUMP) { K.walk.sT = K.walk.s = dTarget / K.length; then && then(); return; }
  if (K.focusI != null) unfocus();
  K.autoWalk = null;
  const from = K.walk.s * K.length, dir = dTarget >= from ? 1 : -1;
  K.rush = { phase: 0, t: 0, from, to: dTarget, dir, lead, then, fog: 0 };
}
function stepRush(dt) {
  const R = K.rush; if (!R) { if (K.rushFog) { K.rushFog = 0; }; return; }
  R.t += dt;
  const L = K.length;
  if (R.phase === 0) {
    // Accelerate forward (or back) a few blocks while the fog rises.
    const T = 0.42, u = Math.min(1, R.t / T);
    K.walk.sT = K.walk.s = Math.min(1, Math.max(0, (R.from + R.dir * (u * u * 7)) / L));
    R.fog = smooth01(u);
    if (u >= 1) {
      // Fog at its thickest: jump to the lead-in point and build the world there, a chunk a frame while the fog holds.
      const d = Math.max(0, Math.min(L, R.to - R.dir * R.lead));
      K.walk.sT = K.walk.s = d / L; R.phase = 1; R.t = 0; K.snap = true;
      plan_point(d); K.pos.set(_pt[0], _pt[1], _pt[2]);
    }
  } else if (R.phase === 1) {
    R.fog = 1;
    const left = K.world.update(K.pos.x, K.pos.z, 1);
    if (left <= 0 || R.t > 3) { R.phase = 2; R.t = 0; }
  } else {
    // Glide the lead-in distance, easing out, while the fog clears.
    const T = 1.15, u = Math.min(1, R.t / T), e = 1 - (1 - u) * (1 - u);
    const d = Math.max(0, Math.min(L, R.to - R.dir * R.lead * (1 - e)));
    K.walk.sT = K.walk.s = d / L;
    R.fog = 1 - smooth01(Math.min(1, u * 1.15));
    if (u >= 1) { const f = R.then; K.rush = null; K.rushFog = 0; f && f(); return; }
  }
  K.rushFog = R.fog;
}
function plan_point(d) { K.plan.pointAt(d, _pt); }

// The jump over a gap, a function of where the walker is along it (so it works at any speed and either way): a crouch on
// the way in, an arc over the gap, a dip on landing. Returns the camera's height offset and pitch.
const JUMP = { pre: 1.5, crouch: 0.26, apex: 0.95, land: 0.34 };
function gapOffsets(d) {
  const gaps = K.plan.gaps;
  if (!gaps.length) return null;
  // The gap whose span is nearest d (binary search by its start).
  let lo = 0, hi = gaps.length - 1;
  while (lo < hi) { const mid = (lo + hi + 1) >> 1; if (gaps[mid].d0 <= d) lo = mid; else hi = mid - 1; }
  let g = gaps[lo];
  if (lo + 1 < gaps.length && Math.abs(gaps[lo + 1].d0 - d) < Math.abs(g.d1 - d)) g = gaps[lo + 1];
  const take = g.d0 - 0.5, air = (g.d1 - g.d0) + 1.0, x = d - take;
  if (x < -3.6 || x > air + 1.2) return { gap: g, x, y: 0, pitch: 0, phase: 0 };
  const sm = (v) => smooth01(v);
  let y = 0, pitch = 0, phase = 0;
  if (x < 0) { y = -JUMP.crouch * sm((x + JUMP.pre) / JUMP.pre); pitch = 0.05 * sm((x + JUMP.pre) / JUMP.pre); phase = 1; }          // crouch before the take-off
  else if (x <= air) {
    const t = x / air;
    y = JUMP.apex * 4 * t * (1 - t) - JUMP.crouch * (1 - sm(x / 0.45));                                                       // the arc, released from the crouch
    pitch = -0.1 * Math.sin(Math.PI * t) + 0.07 * sm((t - 0.6) / 0.4);                                                         // up to the far side, then down to the floor
    phase = 2;
  } else { const t = Math.min(1, (x - air) / 0.9); y = -JUMP.land * Math.sin(Math.PI * t) * (1 - 0.3 * t); pitch = 0.08 * Math.sin(Math.PI * t); phase = 3; }
  return { gap: g, x, air, y, pitch, phase };
}
// Gap events: the krypt-gap event (once per approach, before the take-off), and the sounds of the jump.
function gapEvents(go, dir, speed) {
  const S = K.gapState || (K.gapState = { idx: -1, announced: false, taken: false, ph: 0 });
  if (!go || Math.abs(go.x - (go.air || 3) / 2) > 12) { if (S.idx >= 0 && (!go || go.gap.leg !== S.idx || Math.abs(go.x) > 9)) { S.idx = -1; S.announced = false; S.taken = false; S.ph = 0; } return; }
  if (S.idx !== go.gap.leg) { S.idx = go.gap.leg; S.announced = false; S.taken = false; S.ph = 0; }
  if (!S.announced && dir > 0 && go.x > -3.4 && go.x < -0.6 && Math.abs(speed) > 0.35) {
    S.announced = true;
    const detail = { gap: { s: go.gap.d / K.length, pos: new THREE.Vector3(go.gap.x, go.gap.y, go.gap.z), dir: new THREE.Vector3(go.gap.dx, 0, go.gap.dz), width: go.gap.width, kind: go.gap.kind, side: go.gap.side }, takeover() { S.taken = true; } };
    window.dispatchEvent(new CustomEvent("krypt-gap", { detail }));
  }
  if (S.taken) return;
  if (go.phase !== S.ph) {
    const ph = go.phase;
    if (K.gateOpen && !DUMP && !K.held) {
      if ((S.ph === 1 && ph === 2) || (S.ph === 3 && ph === 2)) { audio.play("step.stone", { volume: 0.5, pitch: 0.9 }); audio.play("step.stone", { volume: 0.35, pitch: 1.1, delay: 0.07 }); }
      if ((S.ph === 2 && ph === 3) || (S.ph === 2 && ph === 1)) { audio.play("step.stone", { volume: 0.85, pitch: 0.62 }); audio.play("dig.gravel", { volume: 0.25, pitch: 0.8, delay: 0.04 }); }
    }
    S.ph = ph;
  }
}

function frame(now) {
  if (!K) return;
  requestAnimationFrame(frame);
  try { frameInner(now); } catch (e) { if (!K.logged) { K.logged = 1; console.error("frame", e && e.stack); window.__errs = (window.__errs || []).concat(String(e && e.stack || e)); document.documentElement.dataset.err = String(e && e.stack || e).slice(0, 900); } }
}
const _f = new THREE.Vector3(), _d = new THREE.Vector3(), _wp = new THREE.Vector3(), _wl = new THREE.Vector3();
function frameInner(now) {
  if (!K.visible || document.hidden) { K.last = now; return; }
  const dt = Math.max(0, Math.min(0.05, (now - K.last) / 1000)); K.last = now;
  const t = now / 1000;
  const W = K.walk;
  const L = K.length;
  stepRush(dt);
  // Damped walk, yaw and pitch.
  const sPrev = W.s;
  if (!K.rush) W.s += (W.sT - W.s) * (1 - Math.exp(-dt * 4.2));
  W.yaw += (W.yawT - W.yaw) * (1 - Math.exp(-dt * 5));
  W.pitch += (W.pitchT - W.pitch) * (1 - Math.exp(-dt * 5));
  if (K.autoWalk && K.focusI == null) {
    if (K.autoWalk.t0 == null) K.autoWalk.t0 = now;
    W.sT = Math.min(1, (now - K.autoWalk.t0) / 1000 / K.autoWalk.dur);
  }
  const vs = dt > 0 && !K.rush ? (W.s - sPrev) * L / dt : 0;
  K.speed += (vs - K.speed) * (1 - Math.exp(-dt * 6));
  if (Math.abs(K.speed) > 0.3 && !K.held && K.focusI == null && K.gateOpen) K.activeSeconds += dt;
  const u = Math.min(1, Math.max(0, W.s));
  const dW = u * L;
  const focusing = K.focusI != null && !QS.has("free");
  const prof = K.plan.profileAtD(dW, K.profTmp);
  K.prof = prof; K.stratum = prof.stratum;

  let jump = null;
  if (!K.held) {
    const bob = (focusing ? 0 : 1) * (Math.sin(t * 2.3) * 0.012 + Math.sin(t * 1.1) * 0.006);
    K.plan.pointAt(dW, _pt); _wp.set(_pt[0], _pt[1] + bob, _pt[2]);
    if (dW < L - 6.5) { K.plan.pointAt(dW + 6, _pt2); _wl.set(_pt2[0], _pt2[1], _pt2[2]); }
    else { K.plan.pointAt(L - 6.5, _pt); K.plan.pointAt(L, _pt2); _wl.copy(_wp).add(_d.set(_pt2[0] - _pt[0], 0, _pt2[2] - _pt[2]).normalize().multiplyScalar(6)); }
    const wp = _wp, wl = _wl;
    wl.y = wl.y - 0.1 + W.pitch * 1.2 + K.fPitch * 6 + (prof.pitch || 0) * 6;
    // Passing focus. Round 5 eased toward whichever stone was nearest; with stones every four blocks on alternating
    // walls that flipped sides every couple of blocks and the view swung back and forth. Now:
    //  - a lock with hysteresis picks the stone the view may turn to. It changes only after a minimum hold, and only
    //    when another stone is clearly nearer;
    //  - how far the view turns depends on spacing and pace. Where stones are sparse and each one passes in its own
    //    couple of seconds, the view eases to each as in round 5. Where they are dense, walking holds a gentle bias
    //    toward the wall the stones are on, and the view turns fully only to a stone you come to rest beside;
    //  - the yaw moves under a rate and acceleration cap, so no change of target can whip the view.
    let fyT = 0, fpT = 0, offT = null;
    const PF = K.pf;
    PF.pace += (Math.abs(K.speed) - PF.pace) * (1 - Math.exp(-dt * (Math.abs(K.speed) > PF.pace ? 4 : 1.5)));   // quick to rise, slow to fall
    if (Math.abs(K.speed) < 0.4 && Math.abs(W.sT - W.s) * L < 0.2) PF.rest += dt; else PF.rest = 0;
    if (K.snap) PF.rest = Math.max(PF.rest, 2);      // arriving by a link or a jump is arriving at rest
    K.nearI = -1;
    if (!focusing && K.gateOpen && state.graves.length) {
      _f.set(wl.x - wp.x, 0, wl.z - wp.z).normalize();
      const angTo = (p) => { _d.set(p.x - wp.x, 0, p.z - wp.z).normalize(); return Math.atan2(_f.z * _d.x - _f.x * _d.z, _f.x * _d.x + _f.z * _d.z); };
      let cand = -1, cs = Infinity, lockS = Infinity, wL = 0, wR = 0;
      for (const i of nearSlots(dW, 14)) {
        const an = anchorOf(i), sd = an.d - dW;      // sd > 0: the stone is still ahead
        const sc = sd >= 0 ? sd : -sd * 1.6;         // a stone behind counts as farther than one ahead
        if (sc < cs) { cs = sc; cand = i; }
        if (i === PF.lock) lockS = sc;
        if (sd > -2 && sd < 14) { const g = 1 - smooth01((sd - 3) / 11); if (an.ys > 0) wL += g; else wR += g; }
      }
      PF.hold += dt;
      if (cand >= 0 && (PF.lock < 0 || lockS > 9 || (cand !== PF.lock && PF.hold > 0.9 && cs + 1.2 < lockS))) { PF.lock = cand; PF.hold = 0; lockS = cs; }
      if (PF.lock >= 0 && lockS <= 9) {
        const sl = K.plan.slots, li = PF.lock, n = Math.min(state.graves.length, sl.length);
        // The spacing here: the gaps either side of the locked stone and the one after it, so the first stone of a
        // close run already counts as close.
        const gp = (j) => (j > 0 && j < n ? sl[j].d - sl[j - 1].d : 99);
        const gap = Math.min(gp(li), gp(li + 1), gp(li + 2));
        // Quick to notice close stones, slow to forget them: a corner or a short passage inside a close run does not
        // let the lean fall away and come back.
        const dT = 1 - smooth01((gap - 5) / 3.5);
        PF.dense += (dT - PF.dense) * (1 - Math.exp(-dt * (dT > PF.dense ? 1.2 : 0.15)));
        // A glance needs the stone to pass in its own time: none when the next comes within 3 s, full from 5 s. And no
        // glance to the other wall until the last one has been over for a couple of seconds: a stroll past stones on
        // alternate walls looks at one, walks on, then looks at another, never left-right-left.
        const gs = anchorOf(li).ys;
        const glance = (1 - PF.dense) * smooth01((gap / Math.max(0.3, PF.pace) - 3.0) / 2.0) * (PF.gSide === 0 || gs === PF.gSide ? 1 : smooth01((PF.gQuiet - 1.5) / 2.0));
        // Coming to rest: a mouse wheel's notches leave about a second of stillness each, so the full turn waits
        // for a real stop, about a second, before it starts.
        const rest = smooth01((PF.rest - 1.0) / 0.8);
        const an = anchorOf(li), sd = an.d - dW, th = angTo(an.p);
        // In until it is abeam, held, then a quicker release once it is behind.
        const w = sd >= 0 ? 1 - smooth01((sd - 2.6) / 5.2) : 1 - smooth01((-sd - 1.2) / 3.4);
        const turn = w * Math.max(glance, rest);
        if (w * glance > 0.15) { PF.gSide = gs; PF.gQuiet = 0; } else PF.gQuiet += dt;
        // The wall to lean toward: where the stones ahead are, held until the other wall clearly has more, and set
        // to the stone's wall when you stop to read one, so walking on keeps the view on the side you were reading.
        // A change of wall waits at least 4 s after the last, so the lean never flicks across and back.
        const side0 = PF.side; PF.sideT += dt;
        if (rest > 0.5 && w > 0.5) PF.side = an.ys;
        else if (PF.side === 0 || ((PF.side > 0 ? wL : wR) < 0.05 && PF.sideT > 4)) PF.side = wL > wR ? 1 : wR > wL ? -1 : PF.side;
        else if ((PF.side > 0 ? wR : wL) > 1.8 * (PF.side > 0 ? wL : wR) + 0.3 && PF.sideT > 4) PF.side = -PF.side;
        if (PF.side !== side0) PF.sideT = 0;
        // Only where the stones are close, and not at a run: hurrying past, you look where you are going.
        const bias = 0.13 * smooth01((PF.dense - 0.3) / 0.4) * (1 - smooth01((PF.pace - 5) / 3)) * PF.side;
        fyT = bias * (1 - turn) + Math.max(-1.5, Math.min(1.5, th)) * 0.96 * turn;
        fpT = -0.1 * turn;
        // Step a little toward the stone so its name is big enough to read.
        offT = an.frame.out.clone().multiplyScalar(1.1 * turn);
        if (turn > 0.2) K.nearI = li;
      } else {
        // No stone near (a corner, a passage): keep the lean, letting it fade as slowly as the run is forgotten.
        PF.dense += (0 - PF.dense) * (1 - Math.exp(-dt * 0.15));
        fyT = 0.13 * smooth01((PF.dense - 0.3) / 0.4) * (1 - smooth01((PF.pace - 5) / 3)) * PF.side;
      }
    }
    if (!offT) offT = new THREE.Vector3();
    if (K.snap) { PF.yaw = fyT; PF.vel = 0; K.fPitch = fpT; K.fOff.copy(offT); }
    {
      const MAXV = 1.0, MAXA = 2.0;                 // rad/s and rad/s^2
      const err = fyT - PF.yaw;
      const vDes = Math.sign(err) * Math.min(Math.abs(err) * 2.6, MAXV, Math.sqrt(2 * MAXA * Math.abs(err)));
      PF.vel += Math.max(-MAXA * dt, Math.min(MAXA * dt, vDes - PF.vel));
      PF.yaw += PF.vel * dt;
      K.fYaw = PF.yaw;
    }
    K.fPitch += (fpT - K.fPitch) * (1 - Math.exp(-dt * 2.4));
    K.fOff.lerp(offT, 1 - Math.exp(-dt * 2.4));
    const dir = new THREE.Vector3().subVectors(wl, wp);
    dir.applyAxisAngle(UP, W.yaw + K.fYaw);
    let tp = wp.clone().add(K.fOff), tl = wp.clone().add(K.fOff).add(dir);
    if (focusing) { const f = focusCamera(K.focusI); tp = f.pos; tl = f.look; }
    K.focusAmt += ((focusing ? 1 : 0) - K.focusAmt) * (1 - Math.exp(-dt * 2.2));
    const k = K.snap ? 1 : 1 - Math.exp(-dt * (focusing ? 2.4 : 3.6));
    K.pos.lerp(tp, k); K.look.lerp(tl, k);
    K.snap = false;
    // The jump over a gap: crouch, arc, landing. A listener of krypt-gap may take it over (a failed jump).
    if (!focusing && K.gateOpen) {
      jump = gapOffsets(dW);
      gapEvents(jump, Math.sign(K.speed) || 1, K.speed);
      if (K.gapState && K.gapState.taken && jump && jump.phase) jump = null;
    }
    // ?cam=x,y,z,lx,ly,lz: a verification camera, for close shots of one thing.
    if (QS.has("cam")) { const c = QS.get("cam").split(",").map(Number); K.pos.set(c[0], c[1], c[2]); K.look.set(c[3], c[4], c[5]); }
    K.camera.position.copy(K.pos);
    K.camera.lookAt(K.look);
    if (jump && jump.phase) {
      K.camera.position.y += jump.y;
      K.camera.rotateX(jump.pitch);
      K.jumpFov = jump.phase === 2 ? Math.sin(Math.PI * Math.min(1, jump.x / jump.air)) * 3.2 : 0;
    } else K.jumpFov = 0;
  }
  K.camera.updateMatrixWorld();
  // The fov follows the rush (a widening) and the jump (a small kick).
  const fov = K.baseFov + (K.rushFog || 0) * 16 + (K.jumpFov || 0);
  if (Math.abs(K.camera.fov - fov) > 0.01) { K.camera.fov = fov; K.camera.updateProjectionMatrix(); }

  // Lighting by depth: fog, exposure and bloom follow the profile; the baked light was built from the same table.
  const rf = K.rushFog || 0;
  K.scene.fog.color.setRGB(prof.fog[0] * (1 - rf) + 0.05 * rf, prof.fog[1] * (1 - rf) + 0.05 * rf, prof.fog[2] * (1 - rf) + 0.07 * rf);
  K.scene.background.copy(K.scene.fog.color);
  if (K.endSky) { const on = K.prof && K.prof.kind === "void_bridge"; K.endSky.visible = on; if (K.sky) K.sky.visible = !on; if (on) K.endSky.position.copy(K.camera.position); }
  K.scene.fog.density = prof.fogD + rf * 0.22;
  K.renderer.toneMappingExposure = prof.exposure;
  K.bloom.strength = prof.bloom;
  if (rf > 0.02 !== !!K.rushBlur) { K.rushBlur = rf > 0.02; }
  if (!state.phone) { const px = (rf * 5).toFixed(1); if (px !== K.blurPx) { K.blurPx = px; $("#gl").style.filter = rf > 0.02 ? `blur(${px}px)` : ""; } }
  K.sky.position.x = K.pos.x; K.sky.position.z = K.pos.z; K.sky.position.y = K.pos.y + 62;
  updateLights(t, dt, prof);
  K.hemi.intensity = 0.32 * (1 - 0.5 * K.focusAmt) * (K.lightFx ? K.lightFx.scaleNow() : 1);
  if (K.focusI != null) {
    const fr = anchorOf(K.focusI).frame, leg = fr.leg;
    const fw = legDir(leg);
    K.spot.position.set(fr.centre.x - fw[0] * 2.4, fr.centre.y + 3.4, fr.centre.z - fw[1] * 2.4);
    K.spot.target.position.set(fr.stone.x, fr.stone.y + 0.6, fr.stone.z);
    K.spot.intensity = 14 * K.focusAmt;
  } else K.spot.intensity = 0;
  K.dresser.update(t, dt, K.pos);
  if (K.lightFx) { K.lightFx.update(dt); K.refreshNear(false); }
  K.fx.update(dt, K.pos, K.renderer.domElement.height, K.camera.fov * Math.PI / 180, K.lightFx ? K.lightFx.factor : null);
  K.grade.uniforms.time.value = t;
  // While a scare holds the player the camera is theirs: build the chunks and the stones around it, not around K.pos.
  updateBuilds(K.held ? K.camera.position : K.pos, K.rush ? 0 : 1);
  // Sound: the walk's own steps, ambience, and the listener.
  if (K.gateOpen && !DUMP) {
    K.amb.tick(dt, K.pos, { s: W.s, speed: K.speed }, prof.kind, K.held);
    audio.updateListener(K.camera);
  }
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
  K.world.ensure(K.pos.x, K.pos.z, 60);
  if (QS.has("carve")) { const c = QS.get("carve").split(",").map(Number); window.__krypt.carve([c[0], c[1], c[2]], [c[0] + c[3] - 1, c[1] + c[4] - 1, c[2] + c[5] - 1]); }
  for (let n = 0; n < 80; n++) updateBuilds(K.pos, 0);
  // A second of particles and a settled flame, so the torches show their small fire.
  for (let q = 0; q < 40; q++) { frameInner(now + 16 + q * 30); }
  dumpShot();
}
function dumpShot() {
  K.dumped = true;
  K.renderer.info.autoReset = false; K.renderer.info.reset();
  K.composer.render();
  const png = K.renderer.domElement.toDataURL("image/png");
  const w = K.world.stats();
  const info = {
    url: location.search, focusI: K.focusI ?? null, nearI: K.nearI ?? null, walkS: K.walk.s, walkD: K.walk.s * K.length, pos: K.pos.toArray(), look: K.look.toArray(),
    fYaw: K.fYaw, fPitch: K.fPitch, kind: K.prof && K.prof.kind, stratum: K.stratum && K.stratum.name, built: K.built.size, queued: K.queue.length, graves: state.graves.length,
    torches: K.agg.torches.length, mesh: w, calls: K.renderer.info.render.calls, tris: K.renderer.info.render.triangles,
    heap: performance.memory ? Math.round(performance.memory.usedJSHeapSize / 1048576) : null, length: Math.round(K.length), legs: K.plan.legs.length, strata: K.plan.strata.length,
    carved: window.__krypt.blockAt(Math.floor(K.pos.x), Math.floor(K.pos.y), Math.floor(K.pos.z)), lights: K.lights.map(l => +l.pl.intensity.toFixed(2)), errors: window.__errs || [], sfx: sfxLog.slice(0, 40),
    jump: (() => { const g = gapOffsets(K.walk.s * K.length); return g ? { x: +g.x.toFixed(2), y: +g.y.toFixed(3), phase: g.phase, kind: g.gap.kind } : null; })()
  };
  const sc = document.createElement("script");
  sc.type = "application/json"; sc.id = "dumpshot";
  sc.textContent = JSON.stringify({ png, ...info });
  document.body.appendChild(sc);
}

// The nearest torches, fires and seams are live lights; each fades in and out as the set changes, so none pops.
function updateLights(t, dt, prof) {
  const cam = K.pos;
  const near = [];
  for (const s of K.agg.dyn) { const d2 = (s.x - cam.x) ** 2 + (s.y - cam.y) ** 2 + (s.z - cam.z) ** 2; if (d2 < 16 * 16) near.push([d2, s]); }
  near.sort((a, b) => a[0] - b[0]);
  const want = near.slice(0, K.lights.length).map(e => e[1]);
  for (const L of K.lights) {
    if (L.src && !want.includes(L.src)) { L.amt -= dt * 4; if (L.amt <= 0) { L.amt = 0; L.src = null; } }
    else if (L.src) L.amt = Math.min(1, L.amt + dt * 4);
  }
  for (const s of want) {
    if (K.lights.some(L => L.src === s)) continue;
    const free = K.lights.find(L => !L.src);
    if (free) { free.src = s; free.amt = 0; if (s.ph === undefined) s.ph = (Math.abs(Math.floor(s.x * 7 + s.z * 13)) % 100) / 10; }
  }
  for (const L of K.lights) {
    const s = L.src;
    if (!s) { L.pl.intensity = 0; continue; }
    const fl = 0.9 + 0.1 * (Math.sin(t * 9.1 + s.ph) * 0.5 + Math.sin(t * 23.7 + s.ph * 2) * 0.5) + (Math.random() - 0.5) * 0.04;
    const boost = K.focusI != null && s.dyn && anchorOf(K.focusI).p.distanceTo(_d.set(s.x, s.y, s.z)) < 5 ? 1 + 0.4 * K.focusAmt : 1;
    L.pl.position.set(s.x, s.y, s.z);
    L.pl.color.setRGB(s.c[0], s.c[1], s.c[2]);
    L.pl.intensity = s.I * 0.5 * (s.sky ? 1 : (s.lava ? 1 : prof.torch)) * fl * boost * L.amt * (K.lightFx ? K.lightFx.factor(s.x, s.y, s.z) : 1);
  }
}

// ---- input ----------------------------------------------------------------------------------
function bindInput(cv) {
  const stage = $("#stage");
  stage.addEventListener("wheel", e => {
    if (!K || !K.gateOpen) return;            // behind the gate the page scrolls as usual
    e.preventDefault();
    if (K.held) return;
    K.autoWalk = null;
    const d = e.deltaMode === 1 ? e.deltaY * 16 : e.deltaY;
    if (K.focusI != null) { unfocus(); }
    walkStep(d / 100 * STEP_BLOCKS * perBlock());
  }, { passive: false });

  let drag = null;
  stage.addEventListener("pointerdown", e => {
    if (!K.gateOpen || K.held || e.target.closest(".sheet, .hud-btn, .strip, .search, .gate")) return;
    K.rush = null; K.rushFog = 0;
    drag = { x: e.clientX, y: e.clientY, t: performance.now(), moved: 0, id: e.pointerId, sT: K.walk.sT, yaw: K.walk.yawT };
    stage.setPointerCapture?.(e.pointerId);
  });
  stage.addEventListener("pointermove", e => {
    if (!K || !K.gateOpen || K.held) return;
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
    if (!K || !K.gateOpen || K.held || e.target.closest?.("input, textarea, select")) return;
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
    if (k === "PageDown") { e.preventDefault(); goStratum(1); return; }
    if (k === "PageUp") { e.preventDefault(); goStratum(-1); return; }
    if (k === "Home") { e.preventDefault(); goTo(6, 12); return; }
    if (k === "End") { e.preventDefault(); jumpNewest(); return; }
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
  gauge();
  // Ticks.
  for (const t of document.querySelectorAll(".tick")) t.classList.toggle("on", Number(t.dataset.i) === i);
}
// The depth gauge: the stratum you are in and the number of the nearest stone.
function nearestIndex() {
  const n = state.graves.length;
  if (!n) return -1;
  const d = K.walk.s * K.length, slots = K.plan.slots;
  const i = Math.min(n - 1, Math.max(0, K.plan.slotAtD(d)));
  const j = Math.min(n - 1, i + 1);
  return Math.abs(slots[j].d - d) < Math.abs(slots[i].d - d) ? j : i;
}
function gauge() {
  const k = $("#hudK"); if (!k || !K) return;
  const st = K.stratum, i = K.focusI != null ? K.focusI : nearestIndex();
  const txt = (st ? st.name : "The Krypt") + (i >= 0 ? ` · stone ${i + 1} of ${state.graves.length}` : "");
  if (k.textContent !== txt) k.textContent = txt;
}
let hudAt = 0;
function updateHUDLive() {
  const now = performance.now();
  const pct = (K.walk.s * 100).toFixed(3) + "%";
  if (now - hudAt < 120) { $("#marker").style.left = pct; return; }
  hudAt = now;
  if (K.focusI == null) {
    const i = currentIndex();
    const cur = i >= 0 ? state.graves[i] : null;
    const name = cur ? cur.player : "Walking the Krypt";
    if ($("#hudName").textContent !== name) setHUD();
  }
  gauge();
  $("#marker").style.left = pct;
  if (K.ticks) { const d = K.walk.s * K.length; for (const t of K.ticks) t.el.classList.toggle("near", Math.abs(t.d - d) < 3); }
}
function buildMinimap() {
  const strip = $("#ticks"); strip.textContent = "";
  const track = $("#strip");
  K.ticks = null;
  if (state.graves.length <= 300) {
    K.ticks = [];
    state.graves.forEach((g, i) => {
      const a = anchorOf(i);
      const b = el("button", "tick");
      b.type = "button"; b.dataset.i = i; b.dataset.s = a.s.toFixed(4);
      b.style.left = (a.s * 100).toFixed(2) + "%";
      b.setAttribute("aria-label", `${g.player}, ${absolute(g.time)}`);
      b.title = `${g.player} · ${absolute(g.time)}`;
      b.addEventListener("click", () => focusGrave(i, false, true));
      strip.append(b); K.ticks.push({ el: b, d: a.d });
    });
  } else {
    // Too many stones for a tick each: the strata as bands along the strip.
    for (const st of K.plan.strata) {
      const b = el("i", "band");
      b.style.left = (st.d0 / K.length * 100).toFixed(3) + "%"; b.style.width = Math.max(0.15, (st.d1 - st.d0) / K.length * 100).toFixed(3) + "%";
      b.style.background = st.def.color || "rgba(150,120,200,.25)"; b.title = st.name;
      strip.append(b);
    }
  }
  const meta = document.querySelector(".strip-meta");
  if (meta) { const sp = meta.querySelectorAll("span"); if (sp.length > 1) sp[1].textContent = state.graves.length > 300 ? `Stone ${state.graves.length.toLocaleString()}` : "Newest"; }
  track.addEventListener("pointerdown", e => {
    if (e.target.closest(".tick")) return;
    const r = track.getBoundingClientRect();
    const s = Math.min(1, Math.max(0, (e.clientX - r.left) / r.width));
    if (K.focusI != null) unfocus();
    goTo(s * K.length);
  });
}
// Walk to a distance on the path: a short way as a walk, a long way as a rush.
function goTo(d, lead) {
  if (Math.abs(d - K.walk.s * K.length) > 90) rushTo(d, null, lead != null ? lead : 14);
  else K.walk.sT = d / K.length;
}
function goStratum(dir) {
  const d = K.walk.s * K.length, S = K.plan.strata;
  let k = S.findIndex(st => d >= st.d0 && d < st.d1); if (k < 0) k = d >= S[S.length - 1].d0 ? S.length - 1 : 0;
  let target;
  if (dir > 0) target = k + 1 < S.length ? S[k + 1].d0 + 8 : K.length - 4;
  else target = d - S[k].d0 > 30 ? S[k].d0 + 8 : (k > 0 ? S[k - 1].d0 + 8 : 6);
  goTo(target, 20);
}
function jumpNewest() {
  if (!state.graves.length) return;
  focusGrave(state.graves.length - 1, false, true);
}
function searchPlayer(name) {
  const idx = state.graves.map((g, i) => [g, i]).filter(([g]) => g.player.toLowerCase() === name.toLowerCase());
  if (!idx.length) { $("#searchNote").textContent = `No stone for "${name}".`; return; }
  $("#searchNote").textContent = `${idx.length} ${idx.length === 1 ? "stone" : "stones"} for ${idx[0][0].player}. Newest shown.`;
  focusGrave(idx[idx.length - 1][1], false, true);
}

// Buttons in the HUD and the sheet.
function enterKrypt() {
  if (!K || K.gateOpen) return;
  const stage = $("#stage");
  K.gateOpen = true;
  stage.dataset.gate = "opening";
  K.amb.gate();
  setTimeout(() => { K.amb.start(); }, 1400);
  setTimeout(() => { stage.dataset.gate = "0"; }, state.reduced ? 100 : 2600);
}
function bindUI() {
  $("#gateGo")?.addEventListener("click", enterKrypt);
  const sp = $("#btnSound");
  if (sp) {
    const show = () => { const m = audio.isMuted(); sp.setAttribute("aria-pressed", m ? "true" : "false"); sp.dataset.muted = m ? "1" : "0"; sp.title = m ? "Sound is off" : "Sound is on"; sp.setAttribute("aria-label", sp.title); };
    sp.addEventListener("click", () => audio.setMuted(!audio.isMuted()));
    audio.onMute(show); show();
  }
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
