// The reel: a row of plaques that sweeps through the foreground and settles on the winning drop.
// Every plaque's front is one painted canvas (frame in the mood colour, an inset panel, the art, a
// caption), so every tile reads crisply whatever the scene lighting is:
//   item  - the icon cell cut out of the shared sprite sheet, scaled by whole pixels (no smoothing)
//   mob   - a lit 3/4 bust of the real model, drawn once by a small offscreen renderer
//   block - a small 3D block with the real textures, drawn the same way
//   text  - the title in the site's type
// The art is painted again when its images arrive, so a tile is never left as a dark plaque.
import * as THREE from 'three';
import { makeMob, whenMobTexturesLoaded } from '../lib/mc/mobs.js';

export const MOOD_COLOR = { jackpot: 0xf2c14e, good: 0x8fd3a0, neutral: 0x9aa3b5, bad: 0xe0884a, deadly: 0xe0583a };
const hex = (n) => '#' + n.toString(16).padStart(6, '0');
const shadeHex = (n, k) => {
  const r = Math.min(255, Math.round(((n >> 16) & 255) * k)), g = Math.min(255, Math.round(((n >> 8) & 255) * k)), b = Math.min(255, Math.round((n & 255) * k));
  return `rgb(${r},${g},${b})`;
};

// ------------------------------------------------------------------ images
const urlOf = (rel) => new URL(rel, import.meta.url).href;
const imgCache = new Map();
const repaint = new Set();       // callbacks to run when any pending image lands
function loadImage(url) {
  if (imgCache.has(url)) return imgCache.get(url);
  const rec = { img: new Image(), ok: false };
  rec.img.crossOrigin = 'anonymous';
  rec.img.onload = () => { rec.ok = true; [...repaint].forEach((f) => f()); };
  rec.img.onerror = () => { rec.failed = true; };
  rec.img.src = url;
  imgCache.set(url, rec);
  return rec;
}
const ICON_SHEET = (s) => urlOf('../items/data/icons-' + s + '.png');
const blockImg = (f) => loadImage(urlOf('./tex/blocks/' + f));

// ------------------------------------------------------------------ type
export function textTexture(text, { color = '#ECE6F2', size = 64, font = 'Archivo, sans-serif', w = 256, h = 256, weight = 800 } = {}) {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  const g = c.getContext('2d');
  g.clearRect(0, 0, w, h);
  g.fillStyle = color;
  g.textAlign = 'center';
  g.textBaseline = 'middle';
  let s = size;
  g.font = `${weight} ${s}px ${font}`;
  while (g.measureText(text).width > w * 0.86 && s > 18) { s -= 2; g.font = `${weight} ${s}px ${font}`; }
  g.fillText(text, w / 2, h / 2);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}
let fontsAsked = false;
function askFonts() {
  if (fontsAsked || !document.fonts || !document.fonts.load) return;
  fontsAsked = true;
  Promise.all([document.fonts.load('800 24px Archivo'), document.fonts.load('600 16px Archivo')]).then(() => [...repaint].forEach((f) => f())).catch(() => {});
}
const TYPE = 'Archivo, system-ui, sans-serif';

// ------------------------------------------------------------------ offscreen renderer (mobs, blocks)
let off = null;
const OFF = 256;
function offscreen() {
  if (off) return off;
  try {
    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true, preserveDrawingBuffer: true });
    renderer.setPixelRatio(1);
    renderer.setSize(OFF, OFF, false);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.setClearColor(0x000000, 0);
    off = { renderer };
  } catch (e) { off = { renderer: null }; }
  return off;
}
function lights(scene, rim) {
  scene.add(new THREE.HemisphereLight(0xe8eeff, 0x5a4a66, 1.9));
  const key = new THREE.DirectionalLight(0xfff0dc, 2.4);
  key.position.set(-3, 5, -4);
  scene.add(key);
  const back = new THREE.DirectionalLight(rim, 1.2);
  back.position.set(4, 2, 3);
  scene.add(back);
}

// A lit 3/4 bust (or the whole mob when it is not much taller than wide).
const mobArt = new Map();
function mobCanvas(id, mood) {
  const key = id + '|' + mood;
  if (mobArt.has(key)) return mobArt.get(key);
  const o = offscreen();
  if (!o.renderer) return null;
  const m = makeMob(id, {});
  if (m.unknown) { mobArt.set(key, null); return null; }
  m.anim(0.9, 0, { walk: 0, still: true, lookAt: 0.25 });
  const scene = new THREE.Scene();
  lights(scene, MOOD_COLOR[mood] || 0xffffff);
  const pivot = new THREE.Group();
  pivot.add(m.root);
  pivot.rotation.y = 0.62;
  scene.add(pivot);
  pivot.updateMatrixWorld(true);
  const box = new THREE.Box3().setFromObject(pivot);
  const sz = box.getSize(new THREE.Vector3());
  const wide = Math.max(sz.x, sz.z);
  let top = box.max.y, bottom = box.min.y;
  if (sz.y > 1.25 * wide && sz.y > 1.0) bottom = top - Math.max(0.5 * sz.y, 1.0 * wide);
  const cy = (top + bottom) / 2, cx = (box.min.x + box.max.x) / 2, cz = (box.min.z + box.max.z) / 2;
  const half = Math.max(top - bottom, wide * 0.92) / 2 * 1.1;
  const cam = new THREE.PerspectiveCamera(26, 1, 0.05, 400);
  const dist = half / Math.tan(THREE.MathUtils.degToRad(13)) + sz.z / 2;
  const el = 0.38; // camera looks down a little so flat wings and backs read
  cam.position.set(cx, cy + Math.sin(el) * dist, cz - Math.cos(el) * dist);
  cam.lookAt(cx, cy, cz);
  const ready = () => {
    o.renderer.render(scene, cam);
    const c = document.createElement('canvas');
    c.width = c.height = OFF;
    c.getContext('2d').drawImage(o.renderer.domElement, 0, 0);
    return c;
  };
  const rec = { canvas: null, render: ready };
  mobArt.set(key, rec);
  whenMobTexturesLoaded().then(() => { rec.canvas = ready(); [...repaint].forEach((f) => f()); });
  return rec;
}

// An iso block: top, left and right faces with the real texture, MC-style face shading.
const BLOCKS = {
  'minecraft:iron_block': { all: 'iron_block.png' }, 'lucky:lucky_block': { all: 'lucky_block.png' },
  'minecraft:tnt': { top: 'tnt_top.png', side: 'tnt_side.png' }, 'minecraft:redstone_block': { all: 'redstone_block.png' },
  'minecraft:coal_block': { all: 'coal_block.png' }, 'minecraft:diamond_block': { all: 'diamond_block.png' },
  'minecraft:diamond_ore': { all: 'diamond_ore.png' }, 'minecraft:gold_block': { all: 'gold_block.png' },
  'minecraft:emerald_block': { all: 'emerald_block.png' }, 'minecraft:lapis_block': { all: 'lapis_block.png' },
  'minecraft:coal_ore': { all: 'coal_ore.png' }, 'minecraft:iron_ore': { all: 'iron_ore.png' }, 'minecraft:gold_ore': { all: 'gold_ore.png' },
  'minecraft:obsidian': { all: 'obsidian.png' }, 'minecraft:sponge': { all: 'sponge.png' }, 'minecraft:stone': { all: 'stone.png' },
  'minecraft:cobblestone': { all: 'cobblestone.png' }, 'minecraft:dirt': { all: 'dirt.png' }, 'minecraft:bedrock': { all: 'bedrock.png' },
  'minecraft:glowstone': { all: 'glowstone.png' }, 'minecraft:netherrack': { all: 'netherrack.png' }, 'minecraft:bookshelf': { top: 'planks_oak.png', side: 'bookshelf.png' },
  'minecraft:crafting_table': { top: 'crafting_table_top.png', side: 'crafting_table_side.png', right: 'crafting_table_front.png' },
  'minecraft:enchanting_table': { top: 'enchanting_table_top.png', side: 'enchanting_table_side.png' },
  'minecraft:quartz_block': { top: 'quartz_block_top.png', side: 'quartz_block_side.png' },
  'minecraft:cake': { top: 'cake_top.png', side: 'cake_side.png' }, 'minecraft:furnace': { top: 'furnace_top.png', side: 'furnace_side.png', right: 'furnace_front_off.png' },
  'minecraft:stained_hardened_clay': { all: 'hardened_clay_stained_white.png' }, 'minecraft:hay_block': { top: 'hay_block_top.png', side: 'hay_block_side.png' },
  'minecraft:planks': { all: 'planks_oak.png' }, 'minecraft:log': { top: 'log_oak_top.png', side: 'log_oak.png' },
  'minecraft:stonebrick': { all: 'stonebrick.png' }, 'minecraft:glass': { all: 'glass.png' }, 'minecraft:gravel': { all: 'gravel.png' },
  'minecraft:grass': { top: 'grass_top.png', side: 'grass_side.png', tintTop: 0x91bd59 }, 'minecraft:leaves': { all: 'leaves_oak.png', tint: 0x8ab84a },
  'minecraft:mob_spawner': { all: 'mob_spawner.png' }, 'minecraft:web': { all: 'web.png' },
  'OreSpawn:OreSpawn_BlockTitaniumBlock': { all: 'orespawn/blocktitanium.png' }, 'OreSpawn:OreSpawn_BlockUraniumBlock': { all: 'orespawn/blockuranium.png' },
};
export const BLOCK_FILE = BLOCKS;
const blockArt = new Map();
function blockCanvas(id) {
  if (blockArt.has(id)) return blockArt.get(id);
  const spec = BLOCKS[id];
  const o = offscreen();
  if (!spec || !o.renderer) { blockArt.set(id, null); return null; }
  const faces = { top: spec.top || spec.all, left: spec.side || spec.all, right: spec.right || spec.side || spec.all };
  const rec = { canvas: null };
  const draw = () => {
    const mk = (file, k, tint) => {
      const r = blockImg(file);
      const t = new THREE.Texture(r.img);
      t.colorSpace = THREE.SRGBColorSpace;
      t.magFilter = THREE.NearestFilter; t.minFilter = THREE.NearestFilter; t.generateMipmaps = false;
      t.needsUpdate = true;
      // only the first square frame of an animated strip
      if (r.img.height > r.img.width) t.repeat.set(1, r.img.width / r.img.height), t.offset.set(0, 1 - r.img.width / r.img.height);
      const c = new THREE.Color(tint ?? 0xffffff).multiplyScalar(k);
      return new THREE.MeshBasicMaterial({ map: t, color: c, transparent: true, alphaTest: 0.4, side: THREE.DoubleSide });
    };
    const tint = spec.tint;
    const top = mk(faces.top, 1.0, spec.tintTop ?? tint), left = mk(faces.left, 0.78, tint), right = mk(faces.right, 0.6, tint);
    // BoxGeometry face order: +x, -x, +y, -y, +z, -z
    const geo = new THREE.BoxGeometry(1, 1, 1);
    const mesh = new THREE.Mesh(geo, [right, left, top, left, left, right]);
    const scene = new THREE.Scene();
    scene.add(mesh);
    mesh.rotation.y = Math.PI / 4;
    const cam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 20);
    const asp = Math.SQRT2;
    cam.left = -asp * 0.62; cam.right = asp * 0.62; cam.top = asp * 0.62; cam.bottom = -asp * 0.62;
    cam.updateProjectionMatrix();
    cam.position.set(0, Math.tan(THREE.MathUtils.degToRad(30)) * 4, 4);
    cam.lookAt(0, 0, 0);
    o.renderer.render(scene, cam);
    const c = document.createElement('canvas');
    c.width = c.height = OFF;
    c.getContext('2d').drawImage(o.renderer.domElement, 0, 0);
    [top, left, right].forEach((m2) => { m2.map.dispose(); m2.dispose(); });
    geo.dispose();
    return c;
  };
  const files = [faces.top, faces.left, faces.right].map(blockImg);
  const tryDraw = () => { if (files.every((f) => f.ok)) { rec.canvas = draw(); repaint.delete(tryDraw); [...repaint].forEach((f) => f()); } };
  repaint.add(tryDraw);
  tryDraw();
  blockArt.set(id, rec);
  return rec;
}

// ------------------------------------------------------------------ the painted front
const TW = 256, TH = 280;
function wrapTitle(g, text, maxW, maxLines) {
  const words = String(text).split(/\s+/);
  const lines = [];
  let cur = '';
  for (const w of words) {
    const t = cur ? cur + ' ' + w : w;
    if (g.measureText(t).width <= maxW || !cur) cur = t; else { lines.push(cur); cur = w; }
  }
  if (cur) lines.push(cur);
  if (lines.length > maxLines) { lines.length = maxLines; lines[maxLines - 1] = lines[maxLines - 1].replace(/\s*\S*$/, '') + '...'; }
  return lines;
}
function cleanTitle(s) { return String(s || '').replace(/#[0-9a-fk-or]/gi, ''); }

function paintFront(g, drop, mood) {
  const col = MOOD_COLOR[mood] || MOOD_COLOR.neutral;
  g.clearRect(0, 0, TW, TH);
  // stone-ish frame in the mood colour: dark body, light top/left edge, dark bottom/right edge
  g.fillStyle = shadeHex(col, 0.5);
  g.fillRect(0, 0, TW, TH);
  const b = 10;
  g.fillStyle = shadeHex(col, 1.05); g.fillRect(0, 0, TW, b); g.fillRect(0, 0, b, TH);
  g.fillStyle = shadeHex(col, 0.3); g.fillRect(0, TH - b, TW, b); g.fillRect(TW - b, 0, b, TH);
  g.fillStyle = shadeHex(col, 0.75); g.fillRect(b, b, TW - 2 * b, 3); g.fillRect(b, b, 3, TH - 2 * b);
  // inset panel with a soft glow of the mood colour behind the art
  const px = 20, py = 20, pw = TW - 40, ph = TH - 40 - 52;
  const grd = g.createRadialGradient(TW / 2, py + ph * 0.55, 6, TW / 2, py + ph * 0.55, pw * 0.75);
  grd.addColorStop(0, shadeHex(col, 0.34)); grd.addColorStop(1, '#14101b');
  g.fillStyle = grd; g.fillRect(px, py, pw, ph);
  g.strokeStyle = 'rgba(0,0,0,.55)'; g.lineWidth = 2; g.strokeRect(px, py, pw, ph);
  // caption strip
  g.fillStyle = '#0e0b12'; g.fillRect(px, py + ph + 6, pw, 40);
  g.strokeStyle = shadeHex(col, 0.55); g.lineWidth = 2; g.strokeRect(px, py + ph + 6, pw, 40);
  return { px, py, pw, ph };
}

function paintArt(g, drop, area, mood) {
  const { px, py, pw, ph } = area;
  const t = drop.tile || {};
  const cx = px + pw / 2, cy = py + ph / 2;
  g.imageSmoothingEnabled = false;
  if (drop.icon) {
    const s = Math.max(0, Math.min(3, Number(drop.icon.s) || 0));
    const rec = loadImage(ICON_SHEET(s));
    if (rec.ok) {
      const size = 32 * 5; // whole-pixel scale
      const x = Math.round(cx - size / 2), y = Math.round(cy - size / 2);
      g.globalAlpha = 0.45; g.filter = 'brightness(0)';
      g.drawImage(rec.img, (drop.icon.c || 0) * 32, (drop.icon.r || 0) * 32, 32, 32, x + 6, y + 8, size, size);
      g.filter = 'none'; g.globalAlpha = 1;
      g.drawImage(rec.img, (drop.icon.c || 0) * 32, (drop.icon.r || 0) * 32, 32, 32, x, y, size, size);
    }
    return true;
  }
  if (t.kind === 'mob' && t.id) {
    const a = mobCanvas(t.id, mood);
    if (a && a.canvas) { g.imageSmoothingEnabled = true; g.drawImage(a.canvas, cx - ph * 0.5, py + (ph - ph) / 2, ph, ph); return true; }
    if (a === null) return false;
    return true;
  }
  if (t.kind === 'block' && t.id) {
    const a = blockCanvas(t.id);
    if (a && a.canvas) { g.imageSmoothingEnabled = true; g.drawImage(a.canvas, cx - ph * 0.5, py, ph, ph); return true; }
    if (a === null) return false;
    return true;
  }
  return false;
}

function paintText(g, area, text, big) {
  const { px, py, pw, ph } = area;
  g.fillStyle = '#ECE6F2';
  g.textAlign = 'center'; g.textBaseline = 'middle';
  let s = big ? 84 : 40;
  g.font = `800 ${s}px ${TYPE}`;
  while (g.measureText(text).width > pw - 20 && s > 16) { s -= 2; g.font = `800 ${s}px ${TYPE}`; }
  g.fillText(text, px + pw / 2, py + ph / 2);
}

const frontCache = new Map();
function frontTexture(drop) {
  const key = drop.index != null ? 'i' + drop.index : drop.title + '|' + drop.mood;
  if (frontCache.has(key)) return frontCache.get(key);
  askFonts();
  const mood = drop.mood || 'neutral';
  const c = document.createElement('canvas');
  c.width = TW; c.height = TH;
  const g = c.getContext('2d');
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.magFilter = THREE.LinearFilter; tex.minFilter = THREE.LinearFilter; tex.generateMipmaps = false;
  const t = drop.tile || {};
  const title = cleanTitle(drop.title);
  const paint = () => {
    const area = paintFront(g, drop, mood);
    let drawn = paintArt(g, drop, area, mood);
    if (!drawn) {
      // text tile, or art we have no picture for: the words, in the site's type
      const word = t.kind === 'text' && t.text && t.text !== '?' ? t.text : null;
      if (t.kind === 'text' && t.text === '?') {
        const a = blockCanvas('lucky:lucky_block');
        if (a && a.canvas) { g.imageSmoothingEnabled = true; g.drawImage(a.canvas, area.px + area.pw / 2 - area.ph * 0.5, area.py, area.ph, area.ph); }
      } else if (word) paintText(g, area, word, word.length < 6);
      else {
        const lines = wrapTitle(g, title, area.pw - 24, 3);
        g.font = `800 30px ${TYPE}`;
        g.fillStyle = '#ECE6F2'; g.textAlign = 'center'; g.textBaseline = 'middle';
        lines.forEach((l, i) => g.fillText(l, area.px + area.pw / 2, area.py + area.ph / 2 + (i - (lines.length - 1) / 2) * 34));
      }
    }
    // caption
    g.font = `700 19px ${TYPE}`;
    g.textAlign = 'center'; g.textBaseline = 'middle';
    const lines = wrapTitle(g, title, area.pw - 16, 2);
    if (lines.length === 1) { g.fillStyle = '#ECE6F2'; g.fillText(lines[0], area.px + area.pw / 2, area.py + area.ph + 26); }
    else { g.font = `700 15px ${TYPE}`; g.fillStyle = '#ECE6F2'; lines.forEach((l, i) => g.fillText(l, area.px + area.pw / 2, area.py + area.ph + 19 + i * 17)); }
    tex.needsUpdate = true;
  };
  paint();
  repaint.add(paint);
  const rec = { tex, paint };
  frontCache.set(key, rec);
  return rec;
}

// ------------------------------------------------------------------ the plaque
const W = 1.1, H = 1.2, D = 0.12;
const bodyGeo = new THREE.BoxGeometry(W, H, D);
const frontGeo = new THREE.PlaneGeometry(W, H);
const bodyMats = {};
const FLAT = (o) => new THREE.MeshBasicMaterial({ fog: false, toneMapped: true, ...o });

// Build a plaque for one drop. Returns a Group whose front faces +z.
export function plaque(drop) {
  const g = new THREE.Group();
  const mood = drop.mood || 'neutral';
  if (!bodyMats[mood]) bodyMats[mood] = FLAT({ color: new THREE.Color(MOOD_COLOR[mood] || MOOD_COLOR.neutral).multiplyScalar(0.28) });
  g.add(new THREE.Mesh(bodyGeo, bodyMats[mood]));
  const f = frontTexture(drop);
  const front = new THREE.Mesh(frontGeo, FLAT({ map: f.tex, transparent: false }));
  front.position.z = D / 2 + 0.002;
  g.add(front);
  // the back wears the same frame so the plaque is not a hollow shell when it turns
  const back = new THREE.Mesh(frontGeo, FLAT({ color: new THREE.Color(MOOD_COLOR[mood] || MOOD_COLOR.neutral).multiplyScalar(0.4) }));
  back.position.z = -D / 2 - 0.002; back.rotation.y = Math.PI;
  g.add(back);
  g.userData.mood = MOOD_COLOR[mood] || MOOD_COLOR.neutral;
  g.userData.content = g; // older callers read tile.userData.content.children
  g.userData.spinChildren = [];
  return g;
}

function glowTex() {
  const c = document.createElement('canvas');
  c.width = c.height = 64;
  const g = c.getContext('2d');
  const grd = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  grd.addColorStop(0, 'rgba(255,255,255,1)'); grd.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = grd; g.fillRect(0, 0, 64, 64);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

// Reel: N plaques along x, spaced `pitch`, the marker at x = 0 (camera's centre).
export function buildReel(S, drops, winnerDrop, N, winIndex) {
  const group = new THREE.Group();
  const pitch = 1.22;
  const tiles = [];
  for (let i = 0; i < N; i++) {
    const d = i === winIndex ? winnerDrop : drops[i];
    const p = plaque(d);
    p.userData.index = i;
    p.userData.drop = d;
    tiles.push(p);
    group.add(p);
  }
  // marker: a thin ember line with a soft glow, the full height of the reel
  const line = new THREE.Mesh(new THREE.PlaneGeometry(0.025, 1.7), FLAT({ color: new THREE.Color(1.0, 0.5, 0.22) }));
  line.position.set(0, 0, 0.2);
  group.add(line);
  const glow = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex(), color: new THREE.Color(1.0, 0.5, 0.22), opacity: 0.45, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, fog: false }));
  glow.scale.set(0.16, 1.9, 1);
  glow.position.set(0, 0, 0.25);
  group.add(glow);
  const set = (p, speed) => {
    for (let i = 0; i < N; i++) {
      const tile = tiles[i];
      const x = (i - p) * pitch;
      tile.position.set(x, 0, 0);
      tile.visible = Math.abs(x) < 4.6;
      // motion blur: stretch the plaque along the strip with its speed
      const stretch = 1 + Math.min(0.55, Math.abs(speed) * 0.01);
      tile.scale.set(stretch, 1, 1);
      tile.userData.stretchAmt = stretch;
    }
  };
  const spinAll = () => {};
  // a dark rail under the plaques so the strip reads as one object
  const rail = new THREE.Mesh(new THREE.PlaneGeometry(14, 1.9), FLAT({ color: 0x0e0b12, transparent: true, opacity: 0.4, depthWrite: false }));
  rail.position.set(0, 0, -0.35);
  group.add(rail);
  return { group, tiles, set, spinAll, pitch, dispose() { group.traverse((o) => { if (o.geometry && o.geometry !== bodyGeo && o.geometry !== frontGeo) o.geometry.dispose(); }); } };
}

// Choose a list of random filler drops weighted like the mod (caller passes a weighted picker).
export function fillerDrops(pick, N, winIndex, drops) {
  const out = [];
  for (let i = 0; i < N; i++) out.push(i === winIndex ? null : drops[pick()]);
  return out;
}

// CS:GO style curve. p runs from 0 to the winner index. A fast start and a long
// ease-out carry it past the marker by `over` tiles; the last 10% nudges it back.
export function reelCurve(u, target, over = 0.34) {
  const ease = (x) => 1 - Math.pow(1 - x, 4);
  if (u < 0.9) return (target + over) * ease(u / 0.9);
  const k = Math.min(1, (u - 0.9) / 0.1);
  const s = k * k * (3 - 2 * k);
  return (target + over) + (target - (target + over)) * s;
}
