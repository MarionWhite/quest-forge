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
import { layout, buildGrid, meshGrid, pathCurve, finishLayout, profileAt, legAt, legDir, legMap, legYaw, slotFrame, patchBake, makeCarver } from "./krypt.js";
import { dress } from "./dress.js";
import { makeFx } from "./fx.js";
import { makeAmbience, sfxLog } from "./kaudio.js";
import { audio } from "../lib/qfaudio.js";
import { buildStone, buildStatue, buildAngelFigure, makeTexture, imageTexture, statueCanvas, STONE_HEIGHT } from "./model.js";
import { loadImage, canvas, glowCanvas, dotCanvas, skyCanvas } from "./textures.js";

const $ = (s) => document.querySelector(s);
const DEMO = new URLSearchParams(location.search).has("demo");
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
//   takeover(on)    true pauses the camera control and walk input (and own footsteps) while a scare plays;
//                   false restores them. The scare may move window.__krypt.camera while taken over.
const __kryptHold = { on: false };
window.__krypt = {
  scene: null, camera: null, renderer: null, composer: null, corners: [],
  getWalk() { return { s: 0, speed: 0, activeSeconds: 0, depth: 0, segment: "crypt" }; },
  takeover(on) { __kryptHold.on = !!on; },
  carve() { return 0; }, restore() { return 0; }, solidAt() { return false; }, blockAt() { return "air"; }
};

// --- scares: begin (owned by scares.js) ---
import("./scares.js").then((m) => m.initScares({ enabled: () => !!state.webgl && !state.reduced })).catch((e) => console.warn("scares", e));
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
  const camera = new THREE.PerspectiveCamera(58, 1, 0.05, 140);
  K.camera = camera;

  // Textures: the pack's own files, loaded once.
  const IMG = {};
  await Promise.all(TEX_FILES.map(async n => { try { IMG[n] = await loadImage(`tex/${n}.png`); } catch { /* optional */ } }));
  try { IMG.skull_tex = await loadImage("../lib/mc/tex/entity/skeleton/skeleton.png"); } catch { /* the graves' own skeleton sheet stands in */ }
  K.IMG = IMG;

  // The world: legs, path, grid, bake, dressing.
  const lay = layout(state.graves.length);
  const curve = pathCurve(lay);
  finishLayout(lay, curve);
  const grid = buildGrid(lay);
  K.lay = lay; K.curve = curve; K.grid = grid; K.length = curve.getLength();
  const gm = meshGrid(grid, IMG);
  if (!QS.has('nogrid')) scene.add(gm.group); K.gridMesh = gm; K.lightAt = gm.lightAt; K.carver = makeCarver(grid, gm);
  const dr = dress(grid, lay, IMG, gm.lightAt);
  if (!QS.has('nodress')) scene.add(dr.group); K.dress = dr;
  K.fx = makeFx(scene, grid.emit, { phone });

  // The violet sky, far above the cracks; it rides with the camera, so it has no parallax, like a real sky.
  const skyTex = makeTexture(skyCanvas(9));
  const sky = new THREE.Mesh(new THREE.PlaneGeometry(300, 300), new THREE.MeshBasicMaterial({ map: skyTex, fog: false, depthWrite: false }));
  sky.rotation.x = Math.PI / 2; sky.position.y = 70; sky.renderOrder = -1;
  scene.add(sky); K.sky = sky;

  // Light: a faint fill for the figures, and the nearest few torches, fires and seams as live point lights. The rest
  // of the light is baked into the blocks (krypt.js), so it needs no draw calls.
  const hemi = new THREE.HemisphereLight(0x7d78a8, 0x2a1d2c, 0.32);
  scene.add(hemi); K.hemi = hemi;
  K.dyn = grid.sources.filter(s => s.dyn).map((s, i) => ({ ...s, ph: (i * 1.713) % 10 }));
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

  // The camera's walk. s runs from 0 at the entrance to 1 at the deepest end.
  K.walk = { s: 0, sT: 0, yaw: 0, yawT: 0, pitch: 0, pitchT: 0, mx: 0, my: 0 };
  const walkSec = Number(QS.get("walk"));
  K.autoWalk = QS.has("walk") && walkSec > 0 ? { dur: walkSec, t0: null } : null;
  K.pos = new THREE.Vector3(); K.look = new THREE.Vector3(); K.focusAmt = 0;
  K.fYaw = 0; K.fPitch = 0; K.fOff = new THREE.Vector3(); K.speed = 0; K.activeSeconds = 0; K.held = false;
  // The alcoves and the graves. Built lazily, near the camera.
  K.anchors = state.graves.map((g, i) => {
    const slot = lay.slots[i];
    const fr = slotFrame(lay, slot);
    return { i, side: slot.side, s: slot.s, frame: fr, p: fr.stone, leg: slot.leg };
  });
  K.built = new Map(); K.queue = [];
  const at0 = QS.has("at") ? Math.min(1, Math.max(0, Number(QS.get("at")) || 0)) : 0;
  K.pos.copy(curve.getPointAt(at0));
  gm.pump(K.pos.x, K.pos.z, 44, 400);       // the blocks around the start; the rest are meshed as the walk nears them
  for (let i = 0; i < K.anchors.length && i < 80; i++) if (K.anchors[i].p.distanceTo(K.pos) < 30) buildGraveAt(i, false);
  buildEntrance(lay, IMG);

  // Sound: the gate unlocks it. Under ?dump and ?nogate there is no gate and no sound.
  K.amb = makeAmbience({ a: grid, lay });
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
  K.snap = QS.has("grave") || QS.has("at");
  if (QS.has("grave")) { const i = Number(QS.get("grave")); if (state.graves[i]) focusGrave(i, true); }
  if (QS.has("at")) { K.walk.s = K.walk.sT = at0; }
  publishKrypt();
  requestAnimationFrame(frame);
  if (DUMP) setTimeout(runDump, 2500);   // the verification frame does not wait for animation frames
  document.documentElement.dataset.graves = "ready";
}

// Fill the scares contract (see the top of the file).
function publishKrypt() {
  const kr = window.__krypt;
  kr.scene = K.scene; kr.camera = K.camera; kr.renderer = K.renderer; kr.composer = K.composer;
  kr.corners = K.lay.corners.map(c => ({ s: c.s, pos: new THREE.Vector3(c.x, c.y, c.z), dir: new THREE.Vector3(c.dx, 0, c.dz), side: c.side, kind: c.kind }));
  kr.getWalk = () => ({ s: K.walk.s, speed: K.speed, activeSeconds: K.activeSeconds, depth: smooth01(K.walk.s), segment: (K.prof && K.prof.kind) || "crypt" });
  const asV = (v) => (Array.isArray(v) ? v : [v.x, v.y, v.z]);
  kr.carve = (mn, mx) => K.carver.carve(asV(mn), asV(mx));
  kr.restore = () => K.carver.restore();
  kr.solidAt = (x, y, z) => K.carver.solidAt(x, y, z);
  kr.blockAt = (x, y, z) => K.carver.blockAt(x, y, z);
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
function buildEntrance(lay, IMG) {
  const empty = !state.graves.length;
  const label = empty ? { title: "Unclaimed", sub: "The first grave" } : { title: "The Krypt", sub: "Walk on" };
  const seed = hash(empty ? "empty" : "entrance");
  const st = buildStone("slab", IMG.grave_stone, { player: "" }, label, 1024, seed, []);
  const grp = new THREE.Group();
  grp.add(st.root);
  const leg = lay.legs[0];
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
  const g = state.graves[i], a = K.anchors[i], fr = a.frame;
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

// Each frame: build the nearest graves, release the far ones, two builds a frame at most.
function updateBuilds(cam) {
  if (K.gridMesh) K.gridMesh.pump(cam.x, cam.z, 56, 1);
  for (let i = 0; i < K.anchors.length; i++) {
    const a = K.anchors[i];
    const d = a.p.distanceTo(cam);
    const built = K.built.get(i);
    if (!built && d < 30 && state.graves.length && !K.queue.includes(i)) K.queue.push(i);
    if (built && d > 52 && K.focusI !== i) disposeGraveAt(i);
  }
  for (let n = 0; n < 2 && K.queue.length; n++) {
    const i = K.queue.shift();
    if (!K.built.has(i)) buildGraveAt(i, K.focusI === i);
  }
}

// ---- the walk -------------------------------------------------------------------------------
function walkStep(ds) {
  if (K.held || !K.gateOpen) return;
  K.autoWalk = null;   // the visitor takes over from ?walk
  K.walk.sT = Math.min(1, Math.max(0, K.walk.sT + ds)); if (K.focusI != null) unfocus();
}
const STEP_BLOCKS = 3;          // one wheel notch or arrow key, in blocks
function perBlock() { return 1 / K.length; }

// The stone nearest along the path, within about three blocks of the camera's place on it.
function currentIndex() {
  if (!state.graves.length) return -1;
  let best = -1, bd = Infinity;
  for (let i = 0; i < K.anchors.length; i++) {
    const d = Math.abs(K.anchors[i].s - K.walk.s) * K.length;
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
  K.focusI = null;
  hideSheet();
  setHUD();
  history.replaceState(null, "", location.pathname + location.search);
}
// From the walk: the stone just ahead (dir +1, deeper) or just behind (dir -1), in the order of the feed.
function nextFromWalk(dir) {
  const n = state.graves.length;
  if (!n) return -1;
  const s = K.walk.s, eps = 0.5 / K.length;
  if (dir > 0) { for (let i = 0; i < n; i++) if (K.anchors[i].s > s + eps) return i; return -1; }
  for (let i = n - 1; i >= 0; i--) if (K.anchors[i].s < s - eps) return i;
  return -1;
}
function focusStep(dir) {
  if (K.focusI == null) return;
  const n = state.graves.length;
  focusGrave((K.focusI + dir + n) % n);
}
function focusCamera(i) {
  const a = K.anchors[i], fr = a.frame;
  // Back along the alcove's centre line, far enough that the stone fills about a third of the frame height
  // (about 2.4 blocks of distance per block of stone), so each family is framed by its own height.
  const H = STONE_HEIGHT[familyFor(state.graves[i])] || 1.8;
  const d = Math.max(3.4, H * 2.4);
  const y0 = fr.centre.y;
  const p = fr.camAt(d); p.y = y0 + 1.25;
  const l = fr.stone.clone(); l.y = y0 + H * 0.5;
  return { pos: p, look: l };
}

function frame(now) {
  if (!K) return;
  requestAnimationFrame(frame);
  try { frameInner(now); } catch (e) { if (!K.logged) { K.logged = 1; console.error("frame", e && e.stack); window.__errs = (window.__errs || []).concat(String(e && e.stack || e)); document.documentElement.dataset.err = String(e && e.stack || e).slice(0, 900); } }
}
const _f = new THREE.Vector3(), _d = new THREE.Vector3();
function frameInner(now) {
  if (!K.visible || document.hidden) { K.last = now; return; }
  const dt = Math.min(0.05, (now - K.last) / 1000); K.last = now;
  const t = now / 1000;
  const W = K.walk;
  const L = K.length;
  // Damped walk, yaw and pitch.
  const sPrev = W.s;
  W.s += (W.sT - W.s) * (1 - Math.exp(-dt * 4.2));
  W.yaw += (W.yawT - W.yaw) * (1 - Math.exp(-dt * 5));
  W.pitch += (W.pitchT - W.pitch) * (1 - Math.exp(-dt * 5));
  if (K.autoWalk && K.focusI == null) {
    if (K.autoWalk.t0 == null) K.autoWalk.t0 = now;
    W.sT = Math.min(1, (now - K.autoWalk.t0) / 1000 / K.autoWalk.dur);
  }
  const vs = dt > 0 ? (W.s - sPrev) * L / dt : 0;
  K.speed += (vs - K.speed) * (1 - Math.exp(-dt * 6));
  if (Math.abs(K.speed) > 0.3 && !K.held && K.focusI == null && K.gateOpen) K.activeSeconds += dt;
  const u = Math.min(1, Math.max(0, W.s));
  const focusing = K.focusI != null;
  const prof = profileAt(K.lay, u);
  K.prof = prof;

  if (!K.held) {
    const bob = (focusing ? 0 : 1) * (Math.sin(t * 2.3) * 0.012 + Math.sin(t * 1.1) * 0.006);
    const wp = K.curve.getPointAt(u);
    const wl = u < 0.992 ? K.curve.getPointAt(Math.min(1, u + 6 / L)) : wp.clone().addScaledVector(K.curve.getTangentAt(u), 6);
    wp.y += bob;
    wl.y = wl.y - 0.1 + W.pitch * 1.2 + K.fPitch * 6 + (prof.pitch || 0) * 6;
    // Passing focus: as an alcove comes near the view eases toward its stone, holds while it is the nearest, and
    // eases back to the corridor as you move on. Damped, and weaker when you are flying past.
    let fyT = 0, fpT = 0, offT = null;
    if (!focusing && K.gateOpen && state.graves.length) {
      let best = -1, bd = Infinity;
      for (let i = 0; i < K.anchors.length; i++) { const d = Math.abs(K.anchors[i].s - u) * L; if (d < bd) { bd = d; best = i; } }
      if (best >= 0 && bd < 8) {
        const an = K.anchors[best];
        const sd = (an.s - u) * L;                 // positive: the stone is still ahead
        _f.set(wl.x - wp.x, 0, wl.z - wp.z).normalize();
        _d.set(an.p.x - wp.x, 0, an.p.z - wp.z).normalize();
        const th = Math.atan2(_f.z * _d.x - _f.x * _d.z, _f.x * _d.x + _f.z * _d.z);
        // In until it is abeam, held, then a quicker release once it is behind.
        const w = sd >= 0 ? 1 - smooth01((sd - 2.6) / 5.2) : 1 - smooth01((-sd - 1.2) / 3.4);
        const calm = 1 - 0.55 * smooth01((Math.abs(K.speed) - 5) / 9);
        fyT = Math.max(-1.5, Math.min(1.5, th)) * w * 0.96 * calm;
        fpT = -0.1 * w * calm;
        // Step a little toward the stone so its name is big enough to read.
        offT = an.frame.out.clone().multiplyScalar(1.1 * w * calm);
        K.nearI = best;
      } else K.nearI = -1;
    }
    if (!offT) offT = new THREE.Vector3();
    if (K.snap) { K.fYaw = fyT; K.fPitch = fpT; K.fOff.copy(offT); }
    K.fYaw += (fyT - K.fYaw) * (1 - Math.exp(-dt * 2.4));
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
    // ?cam=x,y,z,lx,ly,lz: a verification camera, for close shots of one thing.
    if (QS.has("cam")) { const c = QS.get("cam").split(",").map(Number); K.pos.set(c[0], c[1], c[2]); K.look.set(c[3], c[4], c[5]); }
    K.camera.position.copy(K.pos);
    K.camera.lookAt(K.look);
  }
  K.camera.updateMatrixWorld();

  // Lighting by depth: fog, exposure and bloom follow the profile; the baked light was built from the same table.
  K.scene.fog.color.setRGB(prof.fog[0], prof.fog[1], prof.fog[2]);
  K.scene.background.copy(K.scene.fog.color);
  K.scene.fog.density = prof.fogD;
  K.renderer.toneMappingExposure = prof.exposure;
  K.bloom.strength = prof.bloom;
  K.sky.position.x = K.pos.x; K.sky.position.z = K.pos.z;
  updateLights(t, dt, prof);
  K.hemi.intensity = 0.32 * (1 - 0.5 * K.focusAmt);
  if (K.focusI != null) {
    const fr = K.anchors[K.focusI].frame, leg = fr.leg;
    const fw = legDir(leg);
    K.spot.position.set(fr.centre.x - fw[0] * 2.4, fr.centre.y + 3.4, fr.centre.z - fw[1] * 2.4);
    K.spot.target.position.set(fr.stone.x, fr.stone.y + 0.6, fr.stone.z);
    K.spot.intensity = 14 * K.focusAmt;
  } else K.spot.intensity = 0;
  K.dress.update(t, dt, K.pos);
  K.fx.update(dt, K.pos, K.renderer.domElement.height, K.camera.fov * Math.PI / 180);
  K.grade.uniforms.time.value = t;
  updateBuilds(K.pos);
  // Sound: the walk's own steps, ambience, and the listener.
  if (K.gateOpen && !DUMP) {
    const leg = legAt(K.lay, K.pos.x, K.pos.z);
    K.amb.tick(dt, K.pos, { s: W.s, speed: K.speed }, leg ? leg.leg.kind : "crypt", K.held);
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
  K.gridMesh.pump(K.pos.x, K.pos.z, 60, 400);
  if (QS.has("carve")) { const c = QS.get("carve").split(",").map(Number); window.__krypt.carve([c[0], c[1], c[2]], [c[0] + c[3] - 1, c[1] + c[4] - 1, c[2] + c[5] - 1]); }
  for (let n = 0; n < 80; n++) updateBuilds(K.pos);
  // A second of particles and a settled flame, so the torches show their small fire.
  for (let q = 0; q < 40; q++) { frameInner(now + 16 + q * 30); }
  dumpShot();
}
function dumpShot() {
  K.dumped = true;
  K.renderer.info.autoReset = false; K.renderer.info.reset();
  K.composer.render();
  const png = K.renderer.domElement.toDataURL("image/png");
  const info = {
    url: location.search, focusI: K.focusI ?? null, nearI: K.nearI ?? null, walkS: K.walk.s, pos: K.pos.toArray(), look: K.look.toArray(),
    fYaw: K.fYaw, fPitch: K.fPitch, kind: K.prof && K.prof.kind, built: K.built.size, queued: K.queue.length, graves: state.graves.length,
    torches: K.grid.torches.length, mesh: K.gridMesh.stats(), calls: K.renderer.info.render.calls, tris: K.renderer.info.render.triangles, carved: window.__krypt.blockAt(Math.floor(K.pos.x), Math.floor(K.pos.y), Math.floor(K.pos.z)), lights: K.lights.map(l => +l.pl.intensity.toFixed(2)), errors: window.__errs || [], sfx: sfxLog.slice(0, 40)
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
  for (const s of K.dyn) { const d2 = (s.x - cam.x) ** 2 + (s.y - cam.y) ** 2 + (s.z - cam.z) ** 2; if (d2 < 16 * 16) near.push([d2, s]); }
  near.sort((a, b) => a[0] - b[0]);
  const want = near.slice(0, K.lights.length).map(e => e[1]);
  for (const L of K.lights) {
    if (L.src && !want.includes(L.src)) { L.amt -= dt * 4; if (L.amt <= 0) { L.amt = 0; L.src = null; } }
    else if (L.src) L.amt = Math.min(1, L.amt + dt * 4);
  }
  for (const s of want) {
    if (K.lights.some(L => L.src === s)) continue;
    const free = K.lights.find(L => !L.src);
    if (free) { free.src = s; free.amt = 0; }
  }
  for (const L of K.lights) {
    const s = L.src;
    if (!s) { L.pl.intensity = 0; continue; }
    const fl = 0.9 + 0.1 * (Math.sin(t * 9.1 + s.ph) * 0.5 + Math.sin(t * 23.7 + s.ph * 2) * 0.5) + (Math.random() - 0.5) * 0.04;
    const boost = K.focusI != null && s.dyn && K.anchors[K.focusI] && K.anchors[K.focusI].p.distanceTo(new THREE.Vector3(s.x, s.y, s.z)) < 5 ? 1 + 0.4 * K.focusAmt : 1;
    L.pl.position.set(s.x, s.y, s.z);
    L.pl.color.setRGB(s.c[0], s.c[1], s.c[2]);
    L.pl.intensity = s.I * 0.5 * (s.sky ? 1 : (s.lava ? 1 : prof.torch)) * fl * boost * L.amt;
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
