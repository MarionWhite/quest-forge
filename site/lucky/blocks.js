// Block models for the structure placer: one Object3D per block, origin at the
// block's minimum corner, one unit cube. Textures come from tex/ and small canvases.
import * as THREE from 'three';
import { tex, animTex } from './stage.js';
import { boxGeometry } from './mobs.js';

const cache = new Map();
function memo(key, make) { if (!cache.has(key)) cache.set(key, make()); return cache.get(key); }
const L = (file, o = {}) => memo('L' + file + JSON.stringify(o), () => new THREE.MeshLambertMaterial({ map: tex('blocks/' + file), ...o }));
const Lc = (color, o = {}) => memo('C' + color + JSON.stringify(o), () => new THREE.MeshLambertMaterial({ color, ...o }));

function canvasTex(w, h, draw) {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  draw(c.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.magFilter = THREE.NearestFilter;
  t.minFilter = THREE.NearestFilter;
  return t;
}
const webTex = () => memo('webtex', () => canvasTex(16, 16, (g, w, h) => {
  g.strokeStyle = 'rgba(240,240,240,1)'; g.lineWidth = 1;
  for (let i = 0; i < 4; i++) { g.beginPath(); g.moveTo(8, 8); g.lineTo(i * 5 + 1, 0); g.stroke(); g.beginPath(); g.moveTo(8, 8); g.lineTo(16, i * 5 + 1); g.stroke(); }
  g.beginPath(); g.arc(8, 8, 4, 0, Math.PI * 2); g.stroke();
  g.beginPath(); g.arc(8, 8, 8, 0, Math.PI * 2); g.stroke();
}));
const torchTex = () => memo('torchtex', () => canvasTex(8, 8, (g) => {
  const grd = g.createRadialGradient(4, 4, 0, 4, 5, 4);
  grd.addColorStop(0, '#fff3b0'); grd.addColorStop(0.5, '#ffb030'); grd.addColorStop(1, 'rgba(255,90,20,0)');
  g.fillStyle = grd; g.fillRect(0, 0, 8, 8);
}));
// The sign text: black on a planks board, drawn in the site's mono face.
export function signTexture(lines) {
  return canvasTex(128, 64, (g, w, h) => {
    g.fillStyle = '#b48a4e'; g.fillRect(0, 0, w, h);
    g.fillStyle = '#2a1c0c'; g.font = '13px "JetBrains Mono", monospace'; g.textAlign = 'center'; g.textBaseline = 'middle';
    (lines || []).slice(0, 4).forEach((ln, i) => g.fillText(String(ln || '').slice(0, 16), w / 2, 12 + i * 14));
  });
}

const ID = (id) => String(id || '').replace(/^[a-z]+:/, '');

// A block at the origin corner. opts: {facing, has(dx,dy,dz)->bool} for connections.
// Returns {obj, light?}
export function makeBlock(id, meta = 0, opts = {}) {
  const n = ID(id);
  const g = new THREE.Group();
  const box = (w, h, d, x, y, z, m, shadow = true) => {
    const mesh = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), m);
    mesh.position.set(x + w / 2, y + h / 2, z + d / 2);
    mesh.castShadow = shadow; mesh.receiveShadow = true;
    g.add(mesh);
    return mesh;
  };
  const cube = (file, o) => box(1, 1, 1, 0, 0, 0, L(file, o));
  switch (n) {
    case 'stonebrick': cube('stonebrick.png'); break;
    case 'lucky_block': cube('lucky_block.png', { emissive: 0x2a1640, emissiveIntensity: 0.5 }); break;
    case 'obsidian': cube('obsidian.png'); break;
    case 'bedrock': cube('bedrock.png'); break;
    case 'cobblestone': cube('cobblestone.png'); break;
    case 'mossy_cobblestone': cube('cobblestone_mossy.png'); break;
    case 'gold_block': cube('gold_block.png'); break;
    case 'iron_block': cube('iron_block.png'); break;
    case 'planks': case 'wooden_pressure_plate': cube('planks_oak.png'); break;
    case 'sandstone': cube('stone.png', { color: 0xe6d6a0 }); break;
    case 'sandstone_stairs': case 'stone_stairs': {
      const m = n === 'stone_stairs' ? L('cobblestone.png') : L('stone.png', { color: 0xe6d6a0 });
      box(1, 0.5, 1, 0, 0, 0, m); box(1, 0.5, 0.5, 0, 0.5, 0, m);
      break;
    }
    case 'glass': box(1, 1, 1, 0, 0, 0, L('glass.png', { transparent: true, opacity: 0.45, depthWrite: false }), false); break;
    case 'iron_bars': {
      // crossed panes that connect to neighbours
      const m = L('iron_bars.png', { alphaTest: 0.5, side: THREE.DoubleSide });
      const h = opts.has || (() => false);
      const t = 1 / 16;
      box(t, 1, t, 0.5 - t / 2, 0, 0.5 - t / 2, m);
      if (h(1, 0, 0) || h(-1, 0, 0)) box(0.5, 1, t, h(-1, 0, 0) ? 0 : 0.5, 0, 0.5 - t / 2, m);
      if (h(0, 0, 1) || h(0, 0, -1)) box(t, 1, 0.5, 0.5 - t / 2, 0, h(0, 0, -1) ? 0 : 0.5, m);
      if (!h(-1, 0, 0) && !h(1, 0, 0) && !h(0, 0, 1) && !h(0, 0, -1)) { box(1, 1, t, 0, 0, 0.5 - t / 2, m); }
      break;
    }
    case 'fence': {
      const m = L('planks_oak.png');
      box(0.25, 1, 0.25, 0.375, 0, 0.375, m);
      box(1, 0.125, 0.125, 0, 0.375, 0.4375, m); box(1, 0.125, 0.125, 0, 0.75, 0.4375, m);
      break;
    }
    case 'web': {
      const m = new THREE.MeshLambertMaterial({ map: webTex(), transparent: true, alphaTest: 0.4, side: THREE.DoubleSide });
      const a = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), m); a.position.set(0.5, 0.5, 0.5); a.rotation.y = Math.PI / 4; g.add(a);
      const b = a.clone(); b.rotation.y = -Math.PI / 4; g.add(b);
      break;
    }
    case 'torch': {
      box(0.125, 0.625, 0.125, 0.4375, 0, 0.4375, L('planks_oak.png'));
      const f = new THREE.Mesh(new THREE.PlaneGeometry(0.25, 0.25), new THREE.MeshBasicMaterial({ map: torchTex(), transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide }));
      f.position.set(0.5, 0.75, 0.5); f.userData.billboard = true; g.add(f);
      const light = new THREE.PointLight(0xffa040, 1.4, 4.5, 1.6);
      light.position.set(0.5, 0.85, 0.5);
      g.userData.light = light; g.add(light);
      break;
    }
    case 'standing_sign': {
      box(0.125, 0.9, 0.125, 0.4375, 0, 0.4375, L('planks_oak.png'));
      const sign = signTexture(opts.lines);
      const side = L('planks_oak.png');
      const mats = [side, side, side, side, new THREE.MeshLambertMaterial({ map: sign }), side];
      box(0.9, 0.5, 0.1, 0.05, 0.5, 0.45, mats);
      break;
    }
    case 'flowing_lava': case 'lava': {
      // lava_still.png is a 20-frame vertical strip: animTex shows one square frame and scrolls it
      const m = memo('lava', () => { const t = animTex('blocks/lava_still.png'); return new THREE.MeshLambertMaterial({ map: t, emissive: 0xff6a1a, emissiveMap: t, emissiveIntensity: 1.1, transparent: true, opacity: 0.94 }); });
      box(1, 0.9, 1, 0, 0, 0, m, false);
      break;
    }
    case 'flowing_water': case 'water': {
      box(1, 0.9, 1, 0, 0, 0, memo('water', () => new THREE.MeshLambertMaterial({ map: animTex('blocks/water_still.png'), color: 0x3f7fd6, transparent: true, opacity: 0.72 })), false);
      break;
    }
    case 'chest': {
      const ch = chestModel();
      ch.position.set(0.5, 0, 0.5); g.add(ch);
      g.userData.lid = ch.userData.lid;
      break;
    }
    case 'anvil': {
      const base = L('anvil_base.png'), top = L('anvil_top_damaged_0.png');
      // RenderBlocks.renderBlockAnvilOrient: base 0.75x0.25x0.75, neck 0.5x0.0625x0.625, waist 0.25x0.3125x0.5, top 0.625x0.375x1.0
      box(0.75, 0.25, 0.75, 0.125, 0, 0.125, base);
      box(0.5, 0.0625, 0.625, 0.25, 0.25, 0.1875, base);
      box(0.25, 0.3125, 0.5, 0.375, 0.3125, 0.25, base);
      box(0.625, 0.375, 1.0, 0.1875, 0.625, 0, top);
      break;
    }
    default: cube('stone.png');
  }
  return { obj: g, light: g.userData.light || null, lid: g.userData.lid || null };
}

export function chestModel() {
  const g = new THREE.Group();
  const m = memo('chestmat', () => new THREE.MeshLambertMaterial({ map: tex('entity/chest.png') }));
  const body = new THREE.Mesh(boxGeometry([-7, -10, -7, 14, 10, 14], [0, 19], 64, 64), m);
  const pivot = new THREE.Group();
  pivot.position.set(0, 0.625, -0.4375);
  const lid = new THREE.Mesh(boxGeometry([-7, -5, 0, 14, 5, 14], [0, 0], 64, 64), m);
  pivot.add(lid);
  body.position.set(0, 0.625, 0.0);
  g.add(body, pivot);
  g.userData.lid = pivot;
  return g;
}

// the anvil as a standalone model (the anvil scene drops these)
export function anvilModel() {
  const g = new THREE.Group();
  const r = makeBlock('minecraft:anvil', 0);
  r.obj.position.set(-0.5, 0, -0.5);
  g.add(r.obj);
  return g;
}

// Sign text is part of the placed block; the lines come from the structure's nbt.
export function blockHasLight(id) { return ID(id) === 'torch'; }
