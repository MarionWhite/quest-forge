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
import { makeBlock } from './blocks.js';
import { blockSpec } from './blockdefs.js';
import { whenTexturesLoaded } from './stage.js';
import { plan, STRUCTS_READY } from './structures.js';

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

// Blocks, structures and builds as the inventory draws them: the real models (blocks.js, so shapes and
// per-face textures are the ones the scenes use), turned 45 degrees so the south face is on the left
// and the east face on the right, lit so the top is brightest and the sides are 80% and 60% (MC's
// face shading), and zoomed to fill the frame.
const blockArt = new Map();
function iconFrom(key, makeObj, yaw = -Math.PI / 4, when = null) {
  if (blockArt.has(key)) return blockArt.get(key);
  const o = offscreen();
  if (!o.renderer) { blockArt.set(key, null); return null; }
  const rec = { canvas: null };
  blockArt.set(key, rec);
  const scene = new THREE.Scene();
  scene.add(new THREE.AmbientLight(0xffffff, 1.55));
  const sun = new THREE.DirectionalLight(0xffffff, 1.5);
  sun.position.set(0.15, 0.55, 0.35).multiplyScalar(10);
  scene.add(sun);
  const pivot = new THREE.Group();
  const build = () => {
    const obj = makeObj();
    if (!obj) return false;
    const box = new THREE.Box3().setFromObject(obj);
    obj.position.sub(box.getCenter(new THREE.Vector3()));
    pivot.add(obj);
    pivot.rotation.y = yaw;
    scene.add(pivot);
    // flames and lights belong to the world, not the icon
    pivot.traverse((x) => { if (x.userData && x.userData.billboard) x.visible = false; if (x.isLight) x.visible = false; });
    return true;
  };
  const draw = () => {
    pivot.updateMatrixWorld(true);
    // fit: project every vertex on the camera's right and up axes, centre, scale to the frame
    const el = THREE.MathUtils.degToRad(30);
    const right = new THREE.Vector3(1, 0, 0), up = new THREE.Vector3(0, Math.cos(el), -Math.sin(el));
    let x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9;
    const v = new THREE.Vector3();
    pivot.traverse((m) => {
      if (!m.isMesh || !m.visible || !m.geometry.attributes.position) return;
      const p = m.geometry.attributes.position;
      for (let i = 0; i < p.count; i++) {
        v.fromBufferAttribute(p, i).applyMatrix4(m.matrixWorld);
        const px = v.dot(right), py = v.dot(up);
        if (px < x0) x0 = px; if (px > x1) x1 = px; if (py < y0) y0 = py; if (py > y1) y1 = py;
      }
    });
    const half = Math.max(x1 - x0, y1 - y0) / 2 * 1.08, cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
    const cam = new THREE.OrthographicCamera(-half, half, half, -half, 0.1, 80);
    cam.position.set(0, Math.sin(el) * 30, Math.cos(el) * 30);
    cam.lookAt(0, 0, 0);
    cam.translateX(cx); cam.translateY(cy);
    cam.updateProjectionMatrix();
    o.renderer.render(scene, cam);
    const cv = document.createElement('canvas');
    cv.width = cv.height = OFF;
    cv.getContext('2d').drawImage(o.renderer.domElement, 0, 0);
    return cv;
  };
  const go = () => { if (!build()) { blockArt.set(key, null); return; } whenTexturesLoaded().then(() => { rec.canvas = draw(); [...repaint].forEach((f) => f()); }); };
  if (when) when.then(go); else go();
  return rec;
}
export function blockIcon(id, meta = 0, o = {}) {
  const yaw = o.yaw ?? -Math.PI / 4;
  const spec = blockSpec(id, meta, { item: true });
  if (!spec || spec.k === 'none') return null;
  return iconFrom('b|' + id + '#' + meta + '@' + yaw + (o.falling ? 'f' : '') + (o.world ? 'w' : ''),
    () => makeBlock(id, meta, { item: !o.world, quiet: true, falling: !!o.falling, lines: o.lines }).obj, yaw);
}
const blockCanvas = (id, meta) => blockIcon(id, meta);

// A set of cells {x, y, z, id, meta, lines?} as one model (structures and temples).
function cellsObject(cells) {
  const real = cells.filter((c) => c.id !== 'minecraft:air' && c.id !== 'minecraft:fire').slice(0, 260);
  if (!real.length) return null;
  const byPos = new Map(real.map((c) => [c.x + ',' + c.y + ',' + c.z, c]));
  const g = new THREE.Group();
  for (const c of real) {
    const r = makeBlock(c.id, c.meta || 0, { quiet: true, lines: c.lines, at: (dx, dy, dz) => byPos.get((c.x + dx) + ',' + (c.y + dy) + ',' + (c.z + dz)) || null });
    r.obj.position.set(c.x, c.y, c.z);
    g.add(r.obj);
  }
  return g;
}
// the blocks a 'build' tile draws: the first block action with a real building in it
export function buildCells(drop) {
  const from = (drop.tile && drop.tile.from) || 'top';
  const pools = from === 'then' ? (drop.actions || []).filter((a) => a.t === 'then').map((a) => a.actions) : [drop.actions || []];
  for (const acts of pools) for (const a of acts) {
    if (a.t === 'block' && (a.blocks || []).filter((b) => b.id !== 'minecraft:air' && b.id !== 'minecraft:fire').length >= 10) return a.blocks.map((b) => ({ x: b.dx || 0, y: b.dy || 0, z: b.dz || 0, id: b.id, meta: b.meta || 0 }));
  }
  return null;
}
function buildIcon(drop) {
  const cells = buildCells(drop);
  if (!cells) return null;
  return iconFrom('build|' + drop.index, () => cellsObject(cells), -Math.PI / 4 + 0.25);
}
function structureIcon(key) {
  return iconFrom('struct|' + key, () => { const pl = plan(key); return pl ? cellsObject(pl.cells) : null; }, -Math.PI / 4 + 0.25, STRUCTS_READY);
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
    const a = blockCanvas(t.id, t.meta || 0);
    if (a && a.canvas) { g.imageSmoothingEnabled = true; g.drawImage(a.canvas, cx - ph * 0.5, py, ph, ph); return true; }
    if (a === null) return false;
    return true;
  }
  if (t.kind === 'build' || t.kind === 'structure') {
    const a = t.kind === 'build' ? buildIcon(drop) : structureIcon(t.id);
    if (a && a.canvas) { g.imageSmoothingEnabled = true; g.drawImage(a.canvas, cx - ph * 0.5, py, ph, ph); return true; }
    if (a === null) return false;
    return true;
  }
  return false;
}

// What the reel draws for a drop, decided with the same checks paintArt uses; the audit page reads it.
//   {kind, id, ok, art}: art is 'icon' | 'mob' | 'block' | 'text'; ok=false means the tile falls back to
//   the words (no picture exists for it).
export function tileInfo(drop) {
  const t = drop.tile || {};
  if (drop.icon) return { kind: t.kind || 'item', id: t.id || null, ok: true, art: 'icon' };
  if (t.kind === 'mob' && t.id) {
    const m = makeMob(t.id, {});
    return { kind: 'mob', id: t.id, ok: !m.unknown, art: m.unknown ? 'text' : 'mob' };
  }
  if (t.kind === 'block' && t.id) {
    const s = blockSpec(t.id, t.meta || 0, { item: true });
    const ok = !!s && s.k !== 'none';
    return { kind: 'block', id: t.id, ok, art: ok ? 'block' : 'text' };
  }
  if (t.kind === 'build') { const c = buildCells(drop); return { kind: 'build', id: t.from || 'top', ok: !!c, art: c ? 'build' : 'text', cells: c ? c.length : 0 }; }
  if (t.kind === 'structure') { const pl = plan(t.id); const ok = !!pl && pl.cells.length > 0; return { kind: 'structure', id: t.id, ok, art: ok ? 'structure' : 'text' }; }
  if (t.kind === 'item') return { kind: 'item', id: t.id || null, ok: false, art: 'text' };
  return { kind: t.kind || 'text', id: t.text || null, ok: true, art: t.text === '?' ? 'block' : 'text' };
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
  const rec = { tex, paint, canvas: c };
  frontCache.set(key, rec);
  return rec;
}

// the painted front of a drop's plaque as a plain canvas (the tile contact sheets draw these)
export function frontCanvas(drop) { return frontTexture(drop).canvas; }

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
