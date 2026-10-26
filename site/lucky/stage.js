// The stage: renderer, the voxel plateau, sky, light, post, the Lucky Block,
// the player, shatter fragments. Scenes and the reel build on this.
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { BokehPass } from 'three/addons/postprocessing/BokehPass.js';
import { buildBiped, makeAnim } from './mobs.js';
import { buildClouds, buildStars } from './sky.js';
import { makeFx } from './particles.js';

const TEX = (p) => new URL('./tex/' + p, import.meta.url).href;
const ICONS = (s) => new URL('../items/data/icons-' + s + '.png', import.meta.url).href;

// Vanilla 1.7.10 colormap tints. The greyscale textures (grass top, tall grass,
// oak leaves, water) are multiplied by these; every other texture is drawn white.
export const TINT = { grass: 0x91bd59, foliage: 0x8ab84a, water: 0x3f76e4 };

// ------------------------------------------------------------------ textures
// One loading manager for every texture, so a caller can wait for "everything requested so far
// has arrived" (the ?dump verification hook does; the page itself never blocks on it).
const manager = new THREE.LoadingManager();
let texBusy = false;
const texWaiters = [];
manager.onStart = () => { texBusy = true; };
manager.onLoad = () => { texBusy = false; while (texWaiters.length) texWaiters.shift()(); };
manager.onError = () => { /* a missing texture renders white; the load still completes */ };
export function whenTexturesLoaded() {
  return new Promise((resolve) => { if (!texBusy) resolve(); else texWaiters.push(resolve); });
}
const loader = new THREE.TextureLoader(manager);
const texCache = new Map();
export function tex(name, o = {}) {
  const key = name + '|' + JSON.stringify(o);
  if (texCache.has(key)) return texCache.get(key);
  const t = loader.load(o.url || TEX(name));
  t.colorSpace = THREE.SRGBColorSpace;
  t.magFilter = THREE.NearestFilter;
  t.minFilter = THREE.NearestFilter;
  t.generateMipmaps = false;
  if (o.wrap) { t.wrapS = t.wrapT = THREE.RepeatWrapping; }
  texCache.set(key, t);
  return t;
}
// Animated strips (lava): show the first square frame, scroll through the strip.
export function animTex(name) {
  const t = tex(name, { wrap: true });
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.userData.strip = true;
  t.userData.frames = null;
  t.onUpdate = null;
  const img = new Image();
  img.onload = () => {
    const f = Math.max(1, Math.round(img.height / img.width));
    t.userData.frames = f;
    t.repeat.set(1, 1 / f);
  };
  img.src = TEX(name);
  return t;
}
const sheetTexCache = new Map();
export function iconTexture(icon) {
  // icon {s,c,r}; the sheet is 2048x2048 of 32px cells, 64 per row.
  const s = Math.max(0, Math.min(3, Number(icon.s) || 0));
  if (!sheetTexCache.has(s)) {
    const t = loader.load(ICONS(s));
    t.colorSpace = THREE.SRGBColorSpace;
    t.magFilter = THREE.NearestFilter;
    t.minFilter = THREE.NearestFilter;
    t.generateMipmaps = false;
    sheetTexCache.set(s, t);
  }
  const base = sheetTexCache.get(s);
  const t = base.clone();
  t.needsUpdate = true;
  const n = 64;
  t.repeat.set(1 / n, 1 / n);
  t.offset.set((icon.c || 0) / n, 1 - ((icon.r || 0) + 1) / n);
  return t;
}
export function imageLoad(url) {
  return new Promise((res) => { const i = new Image(); i.crossOrigin = 'anonymous'; i.onload = () => res(i); i.onerror = () => res(null); i.src = url; });
}
// Average colour of a texture's opaque pixels (for crack particles).
export function avgColor(img) {
  if (!img) return new THREE.Color(0xa0a0a0);
  const c = document.createElement('canvas');
  c.width = img.width; c.height = img.width;
  const g = c.getContext('2d');
  g.drawImage(img, 0, 0, img.width, img.width, 0, 0, img.width, img.width);
  const d = g.getImageData(0, 0, img.width, img.width).data;
  let r = 0, gg = 0, b = 0, n = 0;
  for (let i = 0; i < d.length; i += 4) { if (d[i + 3] > 128) { r += d[i]; gg += d[i + 1]; b += d[i + 2]; n++; } }
  if (!n) return new THREE.Color(0xa0a0a0);
  return new THREE.Color(r / n / 255, gg / n / 255, b / n / 255);
}
export function colormapSample(img, x, y) {
  if (!img) return new THREE.Color(0x7fb35a);
  const c = document.createElement('canvas');
  c.width = img.width; c.height = img.height;
  const g = c.getContext('2d');
  g.drawImage(img, 0, 0);
  const d = g.getImageData(x, y, 1, 1).data;
  return new THREE.Color(d[0] / 255, d[1] / 255, d[2] / 255);
}
function glowTexture(inner = 'rgba(255,255,255,1)', outer = 'rgba(255,255,255,0)') {
  const c = document.createElement('canvas');
  c.width = c.height = 64;
  const g = c.getContext('2d');
  const grd = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  grd.addColorStop(0, inner); grd.addColorStop(0.35, 'rgba(255,255,255,0.45)'); grd.addColorStop(1, outer);
  g.fillStyle = grd; g.fillRect(0, 0, 64, 64);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

// ------------------------------------------------------------------ blocks
// Faces: `all`, or top/side/bottom. `overlay` is an alpha-tested layer drawn on the
// side in `overlayTint` (the grass fringe). `tint` multiplies the whole block.
const BLOCKS = {
  grass: { top: 'blocks/grass_top.png', side: 'blocks/grass_side.png', bottom: 'blocks/dirt.png', tintTop: TINT.grass, overlay: 'blocks/grass_side_overlay.png', overlayTint: TINT.grass },
  dirt: { all: 'blocks/dirt.png' },
  path: { top: 'blocks/gravel.png', side: 'blocks/dirt.png', bottom: 'blocks/dirt.png' },
  stone: { all: 'blocks/stone.png' },
  bedrock: { all: 'blocks/bedrock.png' },
  cobble: { all: 'blocks/cobblestone.png' },
  mossy: { all: 'blocks/cobblestone_mossy.png' },
  brick: { all: 'blocks/stonebrick.png' },
  mossybrick: { all: 'blocks/stonebrick_mossy.png' },
  planks: { all: 'blocks/planks_oak.png' },
  log: { top: 'blocks/log_oak_top.png', side: 'blocks/log_oak.png', bottom: 'blocks/log_oak_top.png' },
  leaves: { all: 'blocks/leaves_oak.png', tint: TINT.foliage, cutout: true },
  coal: { all: 'blocks/coal_ore.png' },
  ironore: { all: 'blocks/iron_ore.png' },
  obsidian: { all: 'blocks/obsidian.png' },
  tnt: { top: 'blocks/tnt_top.png', side: 'blocks/tnt_side.png', bottom: 'blocks/tnt_bottom.png' },
  gold: { all: 'blocks/gold_block.png' },
  iron: { all: 'blocks/iron_block.png' },
  diamond: { all: 'blocks/diamond_block.png' },
  diamondore: { all: 'blocks/diamond_ore.png' },
  bars: { all: 'blocks/iron_bars.png', cutout: true },
  glass: { all: 'blocks/glass.png', cutout: true },
  lava: { all: 'blocks/lava_still.png', lava: true },
};
export const BLOCK_TEX = {
  'minecraft:stone': 'stone', 'minecraft:dirt': 'dirt', 'minecraft:grass': 'grass', 'minecraft:cobblestone': 'cobble',
  'minecraft:mossy_cobblestone': 'mossy', 'minecraft:bedrock': 'bedrock', 'minecraft:obsidian': 'obsidian',
  'minecraft:tnt': 'tnt', 'minecraft:gold_block': 'gold', 'minecraft:iron_block': 'iron', 'minecraft:diamond_block': 'diamond',
  'minecraft:diamond_ore': 'diamondore', 'minecraft:iron_bars': 'bars', 'minecraft:glass': 'glass',
  'minecraft:lava': 'lava', 'minecraft:flowing_lava': 'lava', 'minecraft:log': 'log', 'minecraft:planks': 'planks',
  'minecraft:leaves': 'leaves', 'minecraft:stonebrick': 'brick', 'minecraft:brick_block': 'brick',
  'minecraft:coal_ore': 'coal', 'minecraft:iron_ore': 'ironore', 'minecraft:gravel': 'path',
};
const isOpaque = (id) => !!BLOCKS[id] && !BLOCKS[id].cutout && !BLOCKS[id].lava;

const DIRS = [
  { n: [1, 0, 0], u: [0, 0, -1], v: [0, 1, 0], face: 'side' },
  { n: [-1, 0, 0], u: [0, 0, 1], v: [0, 1, 0], face: 'side' },
  { n: [0, 1, 0], u: [1, 0, 0], v: [0, 0, -1], face: 'top' },
  { n: [0, -1, 0], u: [1, 0, 0], v: [0, 0, 1], face: 'bottom' },
  { n: [0, 0, 1], u: [1, 0, 0], v: [0, 1, 0], face: 'side' },
  { n: [0, 0, -1], u: [-1, 0, 0], v: [0, 1, 0], face: 'side' },
];

// Voxel map: Map of "x,y,z" -> block id. Voxel (x,y,z) fills the box [x,x+1]x[y,y+1]x[z,z+1].
export class Voxels {
  constructor() { this.m = new Map(); }
  set(x, y, z, id) { if (id) this.m.set(x + ',' + y + ',' + z, id); else this.m.delete(x + ',' + y + ',' + z); }
  get(x, y, z) { return this.m.get(x + ',' + y + ',' + z) || null; }
}
function faceTex(id, face) {
  const b = BLOCKS[id];
  if (b.all) return b.all;
  return b[face] || b.side || b.top;
}
// Merged geometry: one mesh per (texture, cutout, lava, tint). Few draw calls.
export function meshVoxels(vox) {
  const batches = new Map();
  const batchFor = (tn, cut, lava, tint) => {
    const key = [tn, cut ? 1 : 0, lava ? 1 : 0, tint == null ? '' : tint].join('|');
    let b = batches.get(key);
    if (!b) { b = { tn, cut, lava, tint, p: [], n: [], uv: [], i: [] }; batches.set(key, b); }
    return b;
  };
  const quad = (b, cx, cy, cz, d) => {
    const base = b.p.length / 3;
    const corners = [[-1, -1], [1, -1], [1, 1], [-1, 1]];
    for (const [a, bb] of corners) {
      b.p.push(cx + 0.5 * (d.u[0] * a + d.v[0] * bb), cy + 0.5 * (d.u[1] * a + d.v[1] * bb), cz + 0.5 * (d.u[2] * a + d.v[2] * bb));
      b.n.push(d.n[0], d.n[1], d.n[2]);
      b.uv.push((a + 1) / 2, (bb + 1) / 2);
    }
    b.i.push(base, base + 1, base + 2, base, base + 2, base + 3);
  };
  for (const [k, id] of vox.m) {
    const [x, y, z] = k.split(',').map(Number);
    const b = BLOCKS[id];
    if (!b) continue;
    for (const d of DIRS) {
      const nb = vox.get(x + d.n[0], y + d.n[1], z + d.n[2]);
      if (nb && isOpaque(nb) && !b.cutout) continue;
      if (nb && b.cutout && nb === id) continue;
      const cx = x + 0.5 + d.n[0] * 0.5, cy = y + 0.5 + d.n[1] * 0.5, cz = z + 0.5 + d.n[2] * 0.5;
      const tint = b.tint ?? (d.face === 'top' ? b.tintTop ?? null : null);
      quad(batchFor(faceTex(id, d.face), b.cutout, b.lava, tint ?? null), cx, cy, cz, d);
      if (d.face === 'side' && b.overlay) {
        const o = { ...d };
        quad(batchFor(b.overlay, true, false, b.overlayTint), cx + d.n[0] * 0.004, cy, cz + d.n[2] * 0.004, o);
      }
    }
  }
  const group = new THREE.Group();
  for (const bt of batches.values()) {
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.Float32BufferAttribute(bt.p, 3));
    geo.setAttribute('normal', new THREE.Float32BufferAttribute(bt.n, 3));
    geo.setAttribute('uv', new THREE.Float32BufferAttribute(bt.uv, 2));
    geo.setIndex(bt.i);
    const m = new THREE.MeshLambertMaterial({
      map: tex(bt.tn), color: bt.tint ?? 0xffffff, alphaTest: bt.cut ? 0.5 : 0, side: bt.cut ? THREE.DoubleSide : THREE.FrontSide,
    });
    if (bt.lava) { m.emissiveMap = m.map; m.emissive = new THREE.Color(0xff7a2a); m.emissiveIntensity = 1.4; }
    const mesh = new THREE.Mesh(geo, m);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    group.add(mesh);
  }
  return group;
}

// ------------------------------------------------------------------ the plateau
const N = 16; // the voxel field runs from -N to N-1; beyond it a flat ring of grass
// Ground height in blocks (0, 1 or 2 steps). The centre is flat for the dais, Steve and the path.
function heightAt(x, z) {
  if (x < -N + 3 || x > N - 4 || z < -N + 3 || z > N - 4) return 0;
  if (x >= -8 && x <= -6 && z >= -8 && z <= -6) return 0; // the outcrop sits on flat ground
  if (x >= FLAT.x0 && x < FLAT.x1 && z >= FLAT.z0 && z < FLAT.z1) return 0; // the campsite and its quarry
  const d = Math.hypot(x - 0.5, z - 0.5);
  if (d < 7.5) return 0;
  const v = Math.sin(x * 0.45 + 0.8) * 0.9 + Math.cos(z * 0.38 - 0.5) * 0.9 + Math.sin((x + z) * 0.23) * 0.6;
  if (z < -6 && v > 0.2) return v > 1.4 ? 2 : 1;
  if (x < -5 && v > 0.9) return 1;
  return 0;
}
const FLAT = { x0: -10, x1: 8, z0: -8, z1: 1 };
const PATH = { ax: 5.6, az: 11.5, bx: 3.2, bz: -1.2 };
function onPath(x, z) {
  const px = x + 0.5, pz = z + 0.5;
  const dx = PATH.bx - PATH.ax, dz = PATH.bz - PATH.az;
  const t = Math.max(0, Math.min(1, ((px - PATH.ax) * dx + (pz - PATH.az) * dz) / (dx * dx + dz * dz)));
  return Math.hypot(px - (PATH.ax + dx * t), pz - (PATH.az + dz * t)) < 0.85;
}
const POND = { x0: -4, x1: -3, z0: 2, z1: 3 };
const inPond = (x, z) => x >= POND.x0 && x <= POND.x1 && z >= POND.z0 && z <= POND.z1;
const inDais = (x, z) => x >= -1 && x <= 1 && z >= -1 && z <= 1;
const inOutcrop = (x, z) => x >= -8 && x <= -6 && z >= -8 && z <= -6;

function buildPlateau(vox, rnd, reserve = []) {
  const occupied = new Set();
  const key2 = (x, z) => x + ',' + z;
  for (let x = -N; x < N; x++) for (let z = -N; z < N; z++) {
    const t = heightAt(x, z);
    const pond = inPond(x, z);
    const path = !pond && t === 0 && onPath(x, z);
    if (!pond) vox.set(x, t - 1, z, path ? 'path' : 'grass');
    vox.set(x, t - 2, z, 'dirt');
    vox.set(x, t - 3, z, 'dirt');
    for (let y = t - 4; y >= -7; y--) vox.set(x, y, z, 'stone');
    vox.set(x, -8, z, 'bedrock');
    if (pond || path || inDais(x, z) || inOutcrop(x, z)) occupied.add(key2(x, z));
  }
  // dais: 3x3 stone brick, top at y = 1
  for (let x = -1; x <= 1; x++) for (let z = -1; z <= 1; z++) vox.set(x, 0, z, 'brick');
  // the stone outcrop, back left, with coal and iron ore on the faces that show
  const ob = heightAt(-7, -7);
  for (let x = -8; x <= -6; x++) for (let z = -8; z <= -6; z++) for (let y = ob; y < ob + 2; y++) vox.set(x, y, z, 'stone');
  for (let x = -7; x <= -6; x++) for (let z = -8; z <= -7; z++) vox.set(x, ob + 2, z, 'stone');
  vox.set(-6, ob, -7, 'coal');
  vox.set(-6, ob + 1, -8, 'coal');
  vox.set(-7, ob, -6, 'ironore');
  vox.set(-8, ob, -7, 'ironore');
  // oaks: a 4-6 block trunk and a 5-wide canopy, leaves in the foliage tint
  const oak = (tx, tz) => {
    const base = heightAt(tx, tz);
    const h = 4 + Math.floor(rnd() * 2);
    for (let y = base; y < base + h; y++) vox.set(tx, y, tz, 'log');
    const top = base + h;
    const layers = [
      { y: top - 3, r: 2, cut: true }, { y: top - 2, r: 2, cut: true }, { y: top - 1, r: 2, cut: true },
      { y: top, r: 1, cut: false }, { y: top + 1, r: 1, cut: true },
    ];
    for (const L of layers) {
      for (let dx = -L.r; dx <= L.r; dx++) for (let dz = -L.r; dz <= L.r; dz++) {
        if (L.cut && Math.abs(dx) === L.r && Math.abs(dz) === L.r && rnd() < 0.7) continue;
        if (vox.get(tx + dx, L.y, tz + dz) === 'log') continue;
        vox.set(tx + dx, L.y, tz + dz, 'leaves');
      }
    }
    for (let dx = -2; dx <= 2; dx++) for (let dz = -2; dz <= 2; dz++) occupied.add(key2(tx + dx, tz + dz));
  };
  oak(-13, -9); oak(11, -13); oak(-8, 0);
  for (const r of reserve) for (let x = Math.floor(r[0]); x <= Math.floor(r[2]); x++) for (let z = Math.floor(r[1]); z <= Math.floor(r[3]); z++) occupied.add(key2(x, z));
  // flora: red and yellow flowers, tall grass, on the open grass only
  const free = (x, z) => {
    if (x < -11 || x > 11 || z < -11 || z > 11) return false;
    return !occupied.has(key2(x, z)) && heightAt(x, z) === 0 && !inPond(x, z);
  };
  const flowers = [], grass = [];
  for (let i = 0; i < 2600 && flowers.length < 22; i++) {
    const x = Math.floor(-11 + rnd() * 22), z = Math.floor(-11 + rnd() * 22);
    if (free(x, z) && !occupied.has(key2(x, z)) && rnd() < 0.5) { flowers.push({ x, z, kind: rnd() < 0.5 ? 'rose' : 'dandelion' }); occupied.add(key2(x, z)); }
  }
  for (let i = 0; i < 4000 && grass.length < 110; i++) {
    const x = Math.floor(-11 + rnd() * 22), z = Math.floor(-11 + rnd() * 22);
    if (free(x, z) && !occupied.has(key2(x, z))) grass.push({ x: x + rnd() * 0.8 + 0.1, z: z + rnd() * 0.8 + 0.1, s: 0.7 + rnd() * 0.3 });
  }
  return { flowers, grass, pond: POND };
}

// Crossed billboards for flowers and tall grass: merged per texture.
function crossMesh(list, texName, color, sizeOf) {
  const pos = [], uv = [], idx = [];
  let k = 0;
  for (const it of list) {
    const s = sizeOf(it);
    const x = it.x, z = it.z, y = it.y ?? 0;
    const a = (it.rot ?? 0);
    for (const ang of [a, a + Math.PI / 2]) {
      const dx = Math.cos(ang) * 0.5, dz = Math.sin(ang) * 0.5;
      pos.push(x - dx, y, z - dz, x + dx, y, z + dz, x + dx, y + s, z + dz, x - dx, y + s, z - dz);
      uv.push(0, 0, 1, 0, 1, 1, 0, 1); // bottom edge v=0, top edge v=1: upright
      // both windings, so the front-facing material never flips the upward normal on a back face
      idx.push(k, k + 1, k + 2, k, k + 2, k + 3, k, k + 2, k + 1, k, k + 3, k + 2); k += 4;
    }
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  geo.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  geo.setIndex(idx);
  geo.setAttribute('normal', new THREE.Float32BufferAttribute(new Array((pos.length / 3) * 3).fill(0).map((_, i) => (i % 3 === 1 ? 1 : 0)), 3));
  const mat = new THREE.MeshLambertMaterial({ map: tex(texName), alphaTest: 0.5, side: THREE.FrontSide, color });
  const mesh = new THREE.Mesh(geo, mat);
  mesh.receiveShadow = false;
  return mesh;
}

// ------------------------------------------------------------------ sky
const SKY_VERT = `varying vec3 vP; void main(){ vP = position; vec4 p = modelViewMatrix*vec4(position,1.0); gl_Position = projectionMatrix*p; }`;
const SKY_FRAG = `
uniform vec3 uTop; uniform vec3 uDusk; uniform vec3 uHorizon; uniform vec3 uLow; uniform vec3 uSunDir; uniform vec3 uSunCol;
uniform float uNight; uniform float uStars;
varying vec3 vP;
float h2(vec2 p){ return fract(sin(dot(p, vec2(127.1,311.7)))*43758.5453); }
float vn(vec2 p){ vec2 i=floor(p), f=fract(p); f=f*f*(3.0-2.0*f);
  return mix(mix(h2(i),h2(i+vec2(1,0)),f.x), mix(h2(i+vec2(0,1)),h2(i+vec2(1,1)),f.x), f.y); }
float h3(vec3 p){ return fract(sin(dot(p, vec3(12.9898,78.233,37.719)))*43758.5453); }
void main(){
  vec3 d = normalize(vP);
  float h = d.y;
  vec3 col;
  if (h >= 0.0) {
    col = mix(uHorizon, uDusk, smoothstep(0.0, 0.11, h));
    col = mix(col, uTop, smoothstep(0.1, 0.55, h));
  } else {
    col = mix(uHorizon, uLow, smoothstep(0.0, -0.12, h));
  }
  // the sun's glow, toward its disc
  float sd = max(dot(d, normalize(uSunDir)), 0.0);
  col += uSunCol * (pow(sd, 6.0)*0.2 + pow(sd, 120.0)*0.45) * (1.0 - uNight*0.7);
  gl_FragColor = vec4(col, 1.0);
}`;

// ------------------------------------------------------------------ the stage
export async function createStage(canvas, opts = {}) {
  const quality = opts.quality || 'high';
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: quality === 'high', powerPreference: 'high-performance' });
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.1;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, quality === 'high' ? 2 : 1));
  renderer.setClearColor(0x1a1030, 1);

  const HORIZON = 0xd9703a;
  const scene = new THREE.Scene();
  scene.fog = new THREE.Fog(HORIZON, 30, 96);
  const camera = new THREE.PerspectiveCamera(38, 1, 0.05, 400);
  camera.position.set(7, 3.4, 12.5);

  // the sun: low, warm, from the camera's right and a little behind it, so the faces that
  // show are modelled rather than flat-lit
  const SUN = new THREE.Vector3(0.8, 0.55, 0.45).normalize();
  // the visible sun disc: low, left of the view, behind the trees (the key light is SUN)
  const DISC = new THREE.Vector3(-0.30, 0.05, -0.95).normalize();
  const skyMat = new THREE.ShaderMaterial({
    vertexShader: SKY_VERT, fragmentShader: SKY_FRAG, side: THREE.BackSide, depthWrite: false, fog: false,
    uniforms: {
      uTop: { value: new THREE.Color(0x1a1030) }, uDusk: { value: new THREE.Color(0x4a2a5a) },
      uHorizon: { value: new THREE.Color(HORIZON) }, uLow: { value: new THREE.Color(0xa33f17) },
      uNight: { value: 0 }, uStars: { value: 0 }, uSunDir: { value: DISC.clone() }, uSunCol: { value: new THREE.Color(0xffd2a0) },
    },
  });
  const sky = new THREE.Mesh(new THREE.SphereGeometry(220, 40, 20), skyMat);
  sky.renderOrder = -10;
  scene.add(sky);

  // sun disc, low (environment/sun.png), drawn hot so it blooms
  const sunSprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex('environment/sun.png'), color: new THREE.Color(1.5, 1.15, 0.7), transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, fog: false }));
  sunSprite.scale.set(22, 22, 1);
  sunSprite.position.copy(DISC).multiplyScalar(190);
  scene.add(sunSprite);

  // lights
  const hemi = new THREE.HemisphereLight(0x6a58a6, 0x3a2a1a, 0.95);
  scene.add(hemi);
  // a dim warm fill from the camera's side so Steve's face reads (no shadows)
  const camFill = new THREE.DirectionalLight(0xffc89a, 0.6);
  camFill.position.copy(camera.position).normalize().multiplyScalar(40).add(new THREE.Vector3(0.5, 0, 0.5));
  camFill.target.position.set(0.5, 0.5, 0.5);
  scene.add(camFill, camFill.target);
  const target = new THREE.Vector3(0.5, 0.5, 0.5);
  const sun = new THREE.DirectionalLight(0xffd2a0, 3.4);
  sun.position.copy(target).addScaledVector(SUN, 40);
  sun.target.position.copy(target);
  sun.castShadow = true;
  const sz = quality === 'high' ? 2048 : 1024;
  sun.shadow.mapSize.set(sz, sz);
  Object.assign(sun.shadow.camera, { left: -13, right: 13, top: 13, bottom: -13, near: 8, far: 90 });
  sun.shadow.bias = -0.0005;
  sun.shadow.normalBias = 0.025;
  sun.shadow.radius = 2;
  scene.add(sun, sun.target);
  // an ember fill low by the dais, so its front catches the fire
  const emberFill = new THREE.PointLight(0xf08a3c, 5, 9, 2);
  emberFill.position.set(0.5, 0.9, 3.4);
  scene.add(emberFill);
  // the rainbow rim: slow hue shift behind the block
  const rainbow = new THREE.PointLight(0xffffff, 2.2, 6, 2);
  rainbow.position.set(0.5, 2.5, -0.9);
  scene.add(rainbow);

  // the flash light: the whole dais takes the mood colour when the reel lands
  const flashLight = new THREE.PointLight(0xffffff, 0, 11, 2);
  flashLight.position.set(0.5, 2.6, 0.9);
  scene.add(flashLight);

  // world
  const world = new THREE.Group();
  scene.add(world);
  const vox = new Voxels();
  const rnd = mulberry(7);
  const plateau = buildPlateau(vox, rnd, opts.reserve || []);
  let terrain = meshVoxels(vox);
  world.add(terrain);

  // the flat ring beyond the field, so the horizon is not a cliff: grass tinted, huge, under the fog
  const ringShape = new THREE.Shape();
  const R = 300;
  ringShape.moveTo(-R, -R); ringShape.lineTo(R, -R); ringShape.lineTo(R, R); ringShape.lineTo(-R, R); ringShape.lineTo(-R, -R);
  const hole = new THREE.Path();
  hole.moveTo(-N, -N); hole.lineTo(N, -N); hole.lineTo(N, N); hole.lineTo(-N, N); hole.lineTo(-N, -N);
  ringShape.holes.push(hole);
  const ringGeo = new THREE.ShapeGeometry(ringShape);
  ringGeo.rotateX(-Math.PI / 2);
  const ringTex = tex('blocks/grass_top.png', { wrap: true });
  const ring = new THREE.Mesh(ringGeo, new THREE.MeshLambertMaterial({ map: ringTex, color: TINT.grass }));
  ring.receiveShadow = true;
  world.add(ring);

  // the pond: animated water, tinted, two blocks by two, sunk one block
  const waterTex = tex('blocks/water_still.png', { wrap: true });
  waterTex.repeat.set(2, 2);
  const water = new THREE.Mesh(new THREE.PlaneGeometry(POND.x1 - POND.x0 + 1, POND.z1 - POND.z0 + 1),
    new THREE.MeshLambertMaterial({ map: waterTex, color: TINT.water, transparent: true, opacity: 0.88 }));
  water.rotation.x = -Math.PI / 2;
  water.position.set((POND.x0 + POND.x1 + 1) / 2, -0.25, (POND.z0 + POND.z1 + 1) / 2);
  water.receiveShadow = true;
  world.add(water);

  // flowers and tall grass: merged billboards
  const roses = plateau.flowers.filter((f) => f.kind === 'rose').map((f) => ({ x: f.x + 0.5, z: f.z + 0.5, y: heightAt(f.x, f.z), rot: f.x * 1.3, s: 0.55 }));
  const dand = plateau.flowers.filter((f) => f.kind !== 'rose').map((f) => ({ x: f.x + 0.5, z: f.z + 0.5, y: heightAt(f.x, f.z), rot: f.z * 0.7, s: 0.55 }));
  world.add(crossMesh(roses, 'blocks/flower_rose.png', 0xffffff, (it) => it.s));
  world.add(crossMesh(dand, 'blocks/flower_dandelion.png', 0xffffff, (it) => it.s));
  const tallAll = plateau.grass.map((g, i) => ({ x: g.x, z: g.z, y: heightAt(Math.floor(g.x), Math.floor(g.z)), rot: g.x * 2.1, s: g.s, fern: i % 4 === 3 }));
  world.add(crossMesh(tallAll.filter((g) => !g.fern), 'blocks/tallgrass.png', TINT.grass, (it) => it.s * 0.9));
  world.add(crossMesh(tallAll.filter((g) => g.fern), 'blocks/fern.png', TINT.grass, (it) => it.s * 0.9));

  // torches on two corners of the dais, warm point lights that flicker
  const torches = [];
  const stickMat = new THREE.MeshLambertMaterial({ color: 0x6b4a2a });
  const flameMat = new THREE.MeshBasicMaterial({ color: new THREE.Color(2.2, 1.2, 0.5) });
  for (const [tx, tz] of [[-0.7, -0.7], [1.7, 1.7]]) {
    const stick = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.5, 0.1), stickMat);
    stick.position.set(tx, 1.25, tz);
    stick.castShadow = true;
    const flame = new THREE.Mesh(new THREE.BoxGeometry(0.14, 0.14, 0.14), flameMat);
    flame.position.set(tx, 1.56, tz);
    const glow = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTexture('rgba(255,170,90,1)'), color: 0xffa050, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }));
    glow.position.set(tx, 1.6, tz);
    glow.scale.set(0.7, 0.7, 1);
    const light = new THREE.PointLight(0xffa552, 4, 6, 2);
    light.position.set(tx, 1.9, tz);
    world.add(stick, flame, glow);
    scene.add(light);
    torches.push({ light, glow, base: 1.0 + torches.length * 0.2, ph: torches.length * 2.1 });
  }

  // embers and ash, risen around the dais
  const EMBERS = quality === 'high' ? 240 : 110;
  const emberPos = new Float32Array(EMBERS * 3), emberSeed = new Float32Array(EMBERS * 3);
  for (let i = 0; i < EMBERS; i++) {
    emberPos[i * 3] = (rnd() - 0.5) * 16 + 0.5; emberPos[i * 3 + 1] = rnd() * 14 - 1; emberPos[i * 3 + 2] = (rnd() - 0.5) * 16 + 0.5;
    emberSeed[i * 3] = rnd(); emberSeed[i * 3 + 1] = rnd(); emberSeed[i * 3 + 2] = rnd();
  }
  const emberGeo = new THREE.BufferGeometry();
  emberGeo.setAttribute('position', new THREE.BufferAttribute(emberPos, 3));
  const emberMat = new THREE.PointsMaterial({ map: glowTexture('rgba(255,170,90,1)'), color: new THREE.Color(1.8, 0.9, 0.45), size: 0.26, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, sizeAttenuation: true });
  const embers = new THREE.Points(emberGeo, emberMat);
  scene.add(embers);
  const ASH = quality === 'high' ? 140 : 60;
  const ashPos = new Float32Array(ASH * 3);
  for (let i = 0; i < ASH; i++) { ashPos[i * 3] = (rnd() - 0.5) * 30; ashPos[i * 3 + 1] = rnd() * 16; ashPos[i * 3 + 2] = (rnd() - 0.5) * 30; }
  const ashGeo = new THREE.BufferGeometry();
  ashGeo.setAttribute('position', new THREE.BufferAttribute(ashPos, 3));
  const ash = new THREE.Points(ashGeo, new THREE.PointsMaterial({ map: glowTexture('rgba(220,210,230,0.9)'), color: 0xc9c2d4, size: 0.1, transparent: true, opacity: 0.4, depthWrite: false, sizeAttenuation: true }));
  scene.add(ash);
  // square pixel stars, overhead first (sky.js)
  const stars = buildStars({ scene }, rnd);
  stars.setPx(2.4 * Math.min(window.devicePixelRatio || 1, quality === 'high' ? 2 : 1));
  const clouds = buildClouds({ scene });

  // the Lucky Block: real texture on all six faces, centred at (0.5, 1.5, 0.5)
  const lbMat = new THREE.MeshLambertMaterial({ map: tex('blocks/lucky_block.png'), emissive: 0x2a1640, emissiveIntensity: 0.5 });
  const lb = new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), lbMat);
  lb.position.set(0.5, 1.5, 0.5);
  lb.castShadow = true; lb.receiveShadow = true;
  lb.visible = false;
  scene.add(lb);
  // crack overlay (destroy_stage_0..9)
  const crackMat = new THREE.MeshBasicMaterial({ map: tex('blocks/destroy_stage_0.png'), transparent: true, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -4, opacity: 0.95 });
  const crack = new THREE.Mesh(new THREE.BoxGeometry(1.012, 1.012, 1.012), crackMat);
  crack.position.copy(lb.position);
  crack.visible = false;
  scene.add(crack);
  // a faint rainbow halo under and around the block
  const halo = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTexture('rgba(255,255,255,1)'), color: 0xb89cff, transparent: true, opacity: 0.22, depthWrite: false, blending: THREE.AdditiveBlending }));
  halo.position.set(0.5, 1.5, 0.5);
  halo.scale.set(4.4, 4.4, 1);
  halo.visible = false;
  scene.add(halo);

  // the player: vanilla Steve, 64x32, feet at (3.2, 0, 0.5), facing the block
  const steve = buildBiped({ texture: tex('entity/steve.png'), texW: 64, texH: 32 });
  steve.root.position.set(3.2, 0, 0.5);
  steve.root.rotation.y = Math.PI / 2;
  steve.anim = makeAnim({ kind: 'biped', root: steve.root, parts: steve.parts });
  steve.root.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
  steve.mat.emissive.setRGB(0.3, 0.3, 0.3); steve.mat.emissiveMap = steve.mat.map; // self-lit by his own texture: colours stay, shadows lift // no face goes fully black
  scene.add(steve.root);

  // the dais edge: a low violet ring on the top
  const ringMat = new THREE.MeshBasicMaterial({ color: 0x9d7bff, transparent: true, opacity: 0.12, blending: THREE.AdditiveBlending, depthWrite: false });
  const ringMesh = new THREE.Mesh(new THREE.RingGeometry(2.6, 2.7, 64), ringMat);
  ringMesh.rotation.x = -Math.PI / 2; ringMesh.position.set(0.5, 1.02, 0.5);
  scene.add(ringMesh);

  // post: bloom only on the hot things (threshold 0.9), a barely visible grain, a vignette, output last
  const composer = new EffectComposer(renderer);
  const renderPass = new RenderPass(scene, camera);
  composer.addPass(renderPass);
  // only the truly hot things bloom (sun, lava, torches, TNT flash); the threshold sits just under
  // white so lit sprites and pale blocks stay crisp
  const bloom = new UnrealBloomPass(new THREE.Vector2(256, 256), quality === 'high' ? 0.42 : 0.3, 0.45, 0.96);
  composer.addPass(bloom);
  const grade = new ShaderPass({
    uniforms: { tDiffuse: { value: null }, uTime: { value: 0 }, uVignette: { value: 0.5 }, uGrain: { value: 0.012 } },
    vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0); }`,
    fragmentShader: `uniform sampler2D tDiffuse; uniform float uTime; uniform float uVignette; uniform float uGrain; varying vec2 vUv;
      float rnd(vec2 p){ return fract(sin(dot(p, vec2(12.9898,78.233)) + uTime*0.37)*43758.5453); }
      void main(){ vec4 c = texture2D(tDiffuse, vUv); vec2 q = vUv-0.5; float v = 1.0 - uVignette*dot(q*vec2(1.0,1.1), q*vec2(1.0,1.1))*1.9;
        float g = (rnd(vUv*1000.0)-0.5)*uGrain; c.rgb = c.rgb*v + g; gl_FragColor = c; }`,
  });
  composer.addPass(grade);
  // the reel renders in its own layer on top, after the grain: the plaques stay crisp
  const reelScene = new THREE.Scene();
  const reelLayer = new THREE.Group();
  reelScene.add(reelLayer);
  reelScene.add(new THREE.HemisphereLight(0xffffff, 0x3a2a1a, 1.2));
  const reelKey = new THREE.DirectionalLight(0xffd2a0, 1.6);
  reelKey.position.set(5, 6, 8);
  reelScene.add(reelKey);
  const reelPass = new RenderPass(reelScene, camera);
  reelPass.clear = false;
  reelPass.clearDepth = true;
  composer.addPass(reelPass);
  composer.addPass(new OutputPass());
  let bokeh = null;

  const S = {
    quality, renderer, scene, camera, composer, bloom, grade, sun, hemi, lb, lbMat, crack, crackMat, halo, steve, world, water, waterTex,
    embers, emberMat, ash, stars: stars.points, starsApi: stars, clouds, sky, skyMat, ring: ringMesh, torches, reelLayer, reelScene, rainbow, emberFill, temp: new THREE.Group(), vox, rnd, plateau,
    target: new THREE.Vector3(0.5, 1.1, 0.5), dofOn: false, night: 0, rig: null, fragments: [], sunSprite,
    rbMix: 0, blockHere: false, torchFx: null,
    time: 0, lbBase: new THREE.Vector3(0.5, 1.5, 0.5), _bokeh: null, sunDir: SUN,
  };
  scene.add(S.temp);

  S.setSize = (w, h) => {
    renderer.setSize(w, h, false);
    composer.setPixelRatio(renderer.getPixelRatio());
    composer.setSize(w, h);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    bloom.setSize(w, h);
    if (S._bokeh) S._bokeh.setSize(w, h);
  };
  S.enableDof = (on) => {
    if (on && quality === 'high') {
      if (!S._bokeh) {
        S._bokeh = new BokehPass(scene, camera, { focus: 9.0, aperture: 0.00012, maxblur: 0.006 });
        composer.insertPass(S._bokeh, composer.passes.indexOf(grade));
      }
      S._bokeh.enabled = true;
    } else if (S._bokeh) S._bokeh.enabled = false;
  };
  // the sky state from time-of-day (0 dusk, 1 night)
  const MOON = new THREE.Vector3(-0.45, 0.62, -0.5).normalize();
  const NIGHT = { top: 0x03030a, dusk: 0x0c0a1e, horizon: 0x1a1430, low: 0x07060f, fog: 0x0c0a1e };
  const ease01 = (x) => { x = Math.max(0, Math.min(1, x)); return x * x * (3 - 2 * x); };
  // f: 0 dusk, 1 night. Call it every frame with a ramp to animate; every value is a pure function of f.
  S.setNight = (f) => {
    f = Math.max(0, Math.min(1, f));
    S.night = f;
    const u = S.skyMat.uniforms;
    const mix = (a, b) => new THREE.Color(a).lerp(new THREE.Color(b), f);
    u.uNight.value = f;
    u.uTop.value.copy(mix(0x1a1030, NIGHT.top));
    u.uDusk.value.copy(mix(0x4a2a5a, NIGHT.dusk));
    u.uHorizon.value.copy(mix(HORIZON, NIGHT.horizon));
    u.uLow.value.copy(mix(0xa33f17, NIGHT.low));
    S.scene.fog.color.copy(mix(HORIZON, NIGHT.fog));
    // the sun sinks below the horizon; the key light turns to moonlight and dims
    const sunD = SUN.clone(); sunD.y = THREE.MathUtils.lerp(SUN.y, -0.4, f); sunD.normalize();
    const k = ease01((f - 0.3) / 0.6);
    const keyD = sunD.clone().lerp(MOON, k).normalize();
    S.sun.position.copy(target).addScaledVector(keyD, 40);
    const discD = DISC.clone(); discD.y = THREE.MathUtils.lerp(DISC.y, -0.4, f); discD.normalize();
    S.skyMat.uniforms.uSunDir.value.copy(discD);
    sunSprite.position.copy(discD).multiplyScalar(190);
    sunSprite.material.opacity = 1 - ease01(f / 0.5);
    S.sun.color.copy(new THREE.Color(0xffd2a0).lerp(new THREE.Color(0x8a9bd0), k));
    S.sun.intensity = THREE.MathUtils.lerp(3.4, 1.1, k) + 0.02;
    S.hemi.intensity = THREE.MathUtils.lerp(0.95, 0.25, f);
    S.hemi.color.copy(new THREE.Color(0x6a58a6).lerp(new THREE.Color(0x222845), f));
    stars.mat.uniforms.uOpacity.value = 0.45 + 0.55 * f;
    clouds.setNight(f, S.scene.fog.color);
  };

  // the sun as the scene pivots: 'sunset' moves the sun down toward the horizon
  S.sunDrop = (f) => {
    const d = SUN.clone();
    d.y = THREE.MathUtils.lerp(d.y, -0.2, f);
    d.normalize();
    S.sun.position.copy(target).addScaledVector(d, 40);
    const discD = DISC.clone(); discD.y = THREE.MathUtils.lerp(DISC.y, -0.2, f); discD.normalize();
    S.skyMat.uniforms.uSunDir.value.copy(discD);
    sunSprite.position.copy(discD).multiplyScalar(190);
    sunSprite.material.opacity = Math.max(0, 1 - f * 1.1);
  };

  // shatter: fragments of the Lucky Block with gravity and bounce
  const fragGeo = new THREE.BoxGeometry(1, 1, 1);
  const fragMat = new THREE.MeshLambertMaterial({ map: tex('blocks/lucky_block.png') });
  S.shatter = (count = 56, strength = 1) => {
    const out = [];
    for (let i = 0; i < count; i++) {
      const s = 0.12 + rnd() * 0.2;
      const m = new THREE.Mesh(fragGeo, fragMat.clone());
      m.material.transparent = true;
      m.scale.setScalar(s);
      m.castShadow = true;
      const p = lb.position.clone().add(new THREE.Vector3((rnd() - 0.5) * 0.9, (rnd() - 0.5) * 0.9, (rnd() - 0.5) * 0.9));
      m.position.copy(p);
      const a = rnd() * Math.PI * 2, sp = (2.2 + rnd() * 3.2) * strength;
      out.push({ m, v: new THREE.Vector3(Math.cos(a) * sp * 0.6, 3.2 + rnd() * 3.2 * strength, Math.sin(a) * sp * 0.6), w: new THREE.Vector3(rnd() * 12 - 6, rnd() * 12 - 6, rnd() * 12 - 6), life: 0, s });
      S.temp.add(m);
    }
    S.fragments.push(...out);
    lb.visible = false;
    crack.visible = false;
    halo.visible = false;
    return out;
  };
  // Like Minecraft's block particles: they tumble and settle, then shrink and fade from about 1.5 s
  S.stepFragments = (dt) => {
    for (let i = S.fragments.length - 1; i >= 0; i--) {
      const f = S.fragments[i];
      f.life += dt;
      f.v.y -= 16 * dt;
      f.m.position.addScaledVector(f.v, dt);
      f.m.rotation.x += f.w.x * dt; f.m.rotation.y += f.w.y * dt; f.m.rotation.z += f.w.z * dt;
      const floor = (f.m.position.x >= -1 && f.m.position.x < 2 && f.m.position.z >= -1 && f.m.position.z < 2 ? 1 : 0) + f.s * 0.5;
      if (f.m.position.y < floor) {
        f.m.position.y = floor;
        if (f.v.y < 0) f.v.y *= -0.38;
        f.v.x *= 0.7; f.v.z *= 0.7; f.w.multiplyScalar(0.7);
      }
      if (f.life > 1.5) {
        const k = Math.min(1, (f.life - 1.5) / 0.9);
        f.m.scale.setScalar(f.s * (1 - k * k));
        f.m.material.opacity = 1 - k;
        if (k >= 1) { S.temp.remove(f.m); f.m.material.dispose(); S.fragments.splice(i, 1); }
      }
    }
  };
  S.clearFragments = () => {
    for (const f of S.fragments) { S.temp.remove(f.m); f.m.material.dispose(); }
    S.fragments.length = 0;
    lb.visible = S.blockHere;
    halo.visible = S.blockHere;
  };

  S.fx = makeFx(scene);
  // the torch flash: colour is a hex or Color; pulses at `freq` Hz, falls off over `dur` seconds
  S.flashTorches = (color, o = {}) => {
    S.torchFx = { color: new THREE.Color(color), t0: (o.now ?? S.time) + (o.delay || 0), dur: o.dur ?? 2.4, amp: o.amp ?? 1, freq: o.freq ?? 3, tint: o.tint ?? 1 };
  };
  S.setBlockHere = (on) => { S.blockHere = !!on; lb.visible = !!on; halo.visible = !!on; };
  // hooks for scenes
  S.clearTemp = () => {
    for (const f of S.fragments) f.m.material.dispose();
    for (const ch of [...S.temp.children]) {
      S.temp.remove(ch);
      ch.traverse((o) => { if (o.geometry && o.geometry !== fragGeo) o.geometry.dispose(); if (o.material && o.material !== fragMat && !o.material.userData?.keep) { if (o.material.map?.userData?.clone) o.material.map.dispose(); o.material.dispose(); } });
    }
    S.fragments.length = 0;
    lb.visible = S.blockHere;
    halo.visible = S.blockHere;
    crack.visible = false;
  };
  S.dispose = () => { renderer.dispose(); };
  // rebuild the merged terrain after a scene edits voxels (pits, craters, shells)
  S.rebuildTerrain = () => {
    world.remove(terrain);
    terrain.traverse((o) => { if (o.geometry) o.geometry.dispose(); if (o.material) o.material.dispose(); });
    terrain = meshVoxels(vox);
    world.add(terrain);
  };

  // render: the clock drives the water, the embers, the flicker and the rainbow
  S.frame = (t, dt, opts2 = {}) => {
    S.time = t;
    waterTex.offset.y = (t * 0.03) % 1;
    tickFire(t);
    lbMat.emissiveIntensity = 0.5 + 0.12 * Math.sin(t * 1.7);
    const hue = (t * 0.06) % 1;
    rainbow.color.setHSL(hue, 0.9, 0.6);
    rainbow.intensity = 2.0 + 0.4 * Math.sin(t * 0.9);
    halo.material.color.setHSL(hue, 0.85, 0.7);
    // torch flash: the mood colour with a pulse, then it settles back to flame (S.flashTorches)
    let boost = 0, cw = 0;
    const tf = S.torchFx;
    if (tf) {
      const a = t - tf.t0;
      if (a >= tf.dur) S.torchFx = null;
      else if (a >= 0) {
        const k = 1 - a / tf.dur;
        boost = tf.amp * k * (tf.freq ? 0.55 + 0.45 * Math.cos(a * tf.freq * Math.PI * 2) : 1);
        cw = Math.min(1, k * 1.8) * (tf.tint ?? 1);
      }
    }
    flameMat.color.setRGB(2.2, 1.2, 0.5);
    if (cw > 0) flameMat.color.lerp(tf.color.clone().multiplyScalar(2.2), cw);
    for (const tc of torches) {
      tc.light.intensity = (tc.base * 3.6 + 0.6 * Math.sin(t * 13.1 + tc.ph) + 0.35 * Math.sin(t * 23.7 + tc.ph * 2)) * (S.blockHere ? 1 : 0.8) + boost * 16;
      tc.light.color.setHex(0xffa552);
      tc.glow.material.color.setHex(0xffa050);
      if (cw > 0) { tc.light.color.lerp(tf.color, cw); tc.glow.material.color.lerp(tf.color, cw); }
      tc.glow.material.opacity = Math.min(1, 0.7 + 0.3 * Math.sin(t * 11 + tc.ph) + boost * 0.5);
      tc.glow.scale.setScalar(0.7 * (1 + boost * 3.2));
    }
    flashLight.intensity = boost * 26;
    if (tf && cw > 0) flashLight.color.copy(tf.color);
    // the rainbow rim and the halo belong to the block: off while the dais is empty
    const rb = S.blockHere ? 1 : 0;
    S.rbMix += (rb - S.rbMix) * Math.min(1, dt * 6);
    rainbow.intensity *= S.rbMix;
    halo.material.opacity = 0.22 * S.rbMix;
    const ep = emberGeo.attributes.position.array;
    for (let i = 0; i < EMBERS; i++) {
      const sd = emberSeed[i * 3];
      ep[i * 3 + 1] += (0.4 + sd * 0.6) * dt;
      ep[i * 3] += Math.sin(t * (0.6 + sd) + i) * 0.004;
      if (ep[i * 3 + 1] > 15) { ep[i * 3 + 1] = -1; ep[i * 3] = (emberSeed[i * 3 + 1] - 0.5) * 16 + 0.5; ep[i * 3 + 2] = (emberSeed[i * 3 + 2] - 0.5) * 16 + 0.5; }
    }
    emberGeo.attributes.position.needsUpdate = true;
    const ap = ashGeo.attributes.position.array;
    for (let i = 0; i < ASH; i++) {
      ap[i * 3 + 1] -= 0.3 * dt;
      ap[i * 3] += Math.sin(t * 0.5 + i) * 0.004;
      if (ap[i * 3 + 1] < -1) ap[i * 3 + 1] = 16;
    }
    ashGeo.attributes.position.needsUpdate = true;
    grade.uniforms.uTime.value = t;
    stars.mat.uniforms.uTime.value = t;
    clouds.update(t);
    if (opts2.cam) {
      camera.position.copy(opts2.cam.pos);
      camera.lookAt(opts2.cam.look);
      if (opts2.cam.fov && camera.fov !== opts2.cam.fov) { camera.fov = opts2.cam.fov; camera.updateProjectionMatrix(); }
    }
    S.composer.render(dt);
  };
  // full-frame flash is a DOM overlay owned by the page (see app.js); the stage only reports the time
  S.flashAt = () => null;
  S.glow = (x) => glowTexture(x);
  return S;
}

// Shared fire: vanilla fire_layer_0 is a 32-frame strip (16x512). One additive, unlit,
// alpha-tested material for every burning thing; tickFire(t) scrolls the frames.
let fireMat = null;
export function fireMaterial() {
  if (!fireMat) {
    const t = tex('blocks/fire_layer_0.png', { wrap: true });
    t.repeat.set(1, 1 / 32);
    fireMat = new THREE.MeshBasicMaterial({
      map: t, color: new THREE.Color(2.0, 1.1, 0.45), transparent: true, alphaTest: 0.1,
      depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide,
    });
  }
  return fireMat;
}
export function tickFire(t) {
  if (fireMat) fireMat.map.offset.y = (Math.floor(t * 20) % 32) / 32;
}

export function mulberry(a) {
  return function () {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
// Module-level entry for the scenes: the same as S.setNight(amount).
export function setNight(S, amount) { S.setNight(amount); }
export { glowTexture, BLOCKS, THREE };
