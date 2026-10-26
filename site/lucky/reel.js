// The reel: a row of 3D plaques that sweeps through the foreground and settles
// on the winning drop. Tiles are drawn from the real table.
// Plaques are lit by their own light (MeshBasic, no scene fog), so they read crisply.
import * as THREE from 'three';
import { tex, iconTexture, BLOCK_TEX, glowTexture } from './stage.js';
import { makeMob } from './mobs.js';

export const MOOD_COLOR = { jackpot: 0xf2c14e, good: 0x8fd3a0, neutral: 0x9aa3b5, bad: 0xe0884a, deadly: 0xe0583a };
export const BLOCK_FILE = {
  stone: 'stone.png', dirt: 'dirt.png', grass: 'grass_top.png', cobble: 'cobblestone.png', mossy: 'cobblestone_mossy.png',
  brick: 'stonebrick.png', planks: 'planks_oak.png', log: 'log_oak.png', leaves: 'leaves_oak.png', bedrock: 'bedrock.png',
  obsidian: 'obsidian.png', tnt: 'tnt_side.png', gold: 'gold_block.png', iron: 'iron_block.png', diamond: 'diamond_block.png',
  diamondore: 'diamond_ore.png', bars: 'iron_bars.png', glass: 'glass.png', lava: 'lava_still.png',
};

// A canvas plaque with text, used for text tiles and the result caption.
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

const FLAT = (o) => new THREE.MeshBasicMaterial({ fog: false, toneMapped: true, ...o });
const shade = (hex, k) => new THREE.Color(hex).multiplyScalar(k);

// Build a plaque for one drop. Returns a Group whose front faces +z.
// Bevelled stone frame in the mood's colour, a dark inset panel, the content on top.
export function plaque(drop) {
  const g = new THREE.Group();
  const mood = MOOD_COLOR[drop.mood] || MOOD_COLOR.neutral;
  const W = 1.1, H = 1.22, D = 0.12;
  const frameTex = tex('blocks/stonebrick.png');
  const body = new THREE.Mesh(new THREE.BoxGeometry(W, H, D), FLAT({ map: frameTex, color: shade(mood, 0.8) }));
  g.add(body);
  // bevel: light on the top and left, dark on the bottom and right
  const bevW = 0.05;
  const bev = (w, h, x, y, k) => {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), FLAT({ color: shade(mood, k), map: frameTex }));
    m.position.set(x, y, D / 2 + 0.003);
    g.add(m);
  };
  bev(W - bevW * 2, bevW, 0, H / 2 - bevW / 2, 1.5);
  bev(bevW, H - bevW * 2, -W / 2 + bevW / 2, 0, 1.25);
  bev(W - bevW * 2, bevW, 0, -H / 2 + bevW / 2, 0.45);
  bev(bevW, H - bevW * 2, W / 2 - bevW / 2, 0, 0.5);
  // inset panel, nearly black, the field the content sits on
  const panel = new THREE.Mesh(new THREE.PlaneGeometry(W - bevW * 2, H - bevW * 2), FLAT({ color: 0x120e18 }));
  panel.position.z = D / 2 + 0.004;
  g.add(panel);
  // content
  const c = contentFor(drop);
  c.position.z = D / 2 + 0.03;
  g.add(c);
  g.userData.mood = mood;
  g.userData.content = c;
  return g;
}

function contentFor(drop) {
  const c = new THREE.Group();
  const t = drop.tile || {};
  if (drop.icon) {
    // the item icon at full brightness, alpha-tested, no spin
    const m = new THREE.Mesh(new THREE.PlaneGeometry(0.98, 0.98), FLAT({ map: iconTexture(drop.icon), transparent: true, alphaTest: 0.5, side: THREE.DoubleSide }));
    c.add(m);
    return c;
  }
  if (t.kind === 'mob' && t.id) {
    // a lit bust: the mob's head and shoulders, framed in the panel
    const m = makeMob(t.id);
    // fit the bust inside the panel: the model is feet-at-origin, so centre its height on the panel
    const h = Math.max(0.4, m.height || 1.8);
    const k = 0.9 / Math.max(h, 1.0);
    m.root.scale.multiplyScalar(k);
    m.root.position.set(0, -(h * k) / 2, 0);
    m.root.rotation.y = 0.55;
    m.root.traverse((o) => { o.castShadow = false; });
    c.add(m.root);
    c.userData.mob = m;
    return c;
  }
  if (t.kind === 'block' && t.id) {
    const name = String(t.id).replace(/^minecraft:/, '');
    const key = BLOCK_TEX[t.id] || null;
    const file = key ? BLOCK_FILE[key] : null;
    const mat = file ? new THREE.MeshLambertMaterial({ map: tex('blocks/' + file) }) : new THREE.MeshLambertMaterial({ color: 0x8a8a8a });
    const m = new THREE.Mesh(new THREE.BoxGeometry(0.56, 0.56, 0.56), mat);
    m.rotation.set(0.45, 0.6, 0);
    m.userData.spin = true;
    c.add(m);
    if (!file) c.add(textMesh(name.slice(0, 12)));
    return c;
  }
  const text = t.kind === 'text' && t.text ? t.text : (drop.title || '?');
  c.add(textMesh(text.length > 14 ? text.slice(0, 13) + '.' : text, text.length > 10 ? 40 : 56));
  return c;
}
function textMesh(text, size = 56) {
  const m = new THREE.Mesh(new THREE.PlaneGeometry(0.9, 0.9), FLAT({ map: textTexture(text, { size }), transparent: true, alphaTest: 0.2, side: THREE.DoubleSide }));
  return m;
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
  // marker: a thin ember line with a glow, the full height of the reel
  const line = new THREE.Mesh(new THREE.PlaneGeometry(0.025, 1.7), FLAT({ color: new THREE.Color(1.0, 0.5, 0.22) }));
  line.position.set(0, 0, 0.2);
  group.add(line);
  // a soft glow about 8 px wide around the line
  const glow = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTexture('rgba(255,150,70,1)'), color: new THREE.Color(1.0, 0.5, 0.22), opacity: 0.45, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, fog: false }));
  glow.scale.set(0.16, 1.9, 1);
  glow.position.set(0, 0, 0.25);
  group.add(glow);
  const set = (p, speed) => {
    for (let i = 0; i < N; i++) {
      const tile = tiles[i];
      const x = (i - p) * pitch;
      tile.position.set(x, 0, 0);
      const dist = Math.abs(x);
      tile.visible = dist < 4.6;
      // motion blur: stretch the plaque along the strip with its speed
      const stretch = 1 + Math.min(0.55, Math.abs(speed) * 0.01);
      tile.scale.set(stretch, 1, 1);
      tile.userData.stretchAmt = stretch;
    }
  };
  // spinning busts and blocks animate by time, not by position
  const spinAll = (t) => {
    for (const tile of tiles) {
      const c = tile.userData.content;
      c.children.forEach((o) => { if (o.userData.spin) o.rotation.y = t * 1.2 + tile.userData.index; });
      if (c.userData.mob) c.userData.mob.anim(t, 0, { walk: 0 });
    }
  };
  // a dark rail under the plaques so the strip reads as one object
  const rail = new THREE.Mesh(new THREE.PlaneGeometry(14, 1.9), FLAT({ color: 0x0e0b12, transparent: true, opacity: 0.4, depthWrite: false }));
  rail.position.set(0, 0, -0.35);
  group.add(rail);
  return { group, tiles, set, spinAll, pitch, dispose() { group.traverse((o) => { if (o.geometry) o.geometry.dispose(); }); } };
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
