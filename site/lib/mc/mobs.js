// Mob models. Vanilla parts use the 1.7.10 ModelBox UV layout and the
// ModelBiped / ModelCreeper / ModelPig ... geometry (model units: 16 per block,
// y points down, feet at y=24). Mods without a vanilla model get voxel stand-ins.
import * as THREE from 'three';
import { tex, whenMobTexturesLoaded } from './textures.js';
export { whenMobTexturesLoaded };

const TEXP = (p) => new URL('./tex/' + p, import.meta.url).href;
const FEET = 24;

// Face orientation (three space) for each of the six faces of a box.
const FACE = {
  top: { n: [0, 1, 0], R: [1, 0, 0], U: [0, 0, -1] },
  bottom: { n: [0, -1, 0], R: [1, 0, 0], U: [0, 0, 1] },
  right: { n: [-1, 0, 0], R: [0, 0, 1], U: [0, 1, 0] },
  left: { n: [1, 0, 0], R: [0, 0, -1], U: [0, 1, 0] },
  front: { n: [0, 0, -1], R: [-1, 0, 0], U: [0, 1, 0] },
  back: { n: [0, 0, 1], R: [1, 0, 0], U: [0, 1, 0] },
};

// A 1.7.10 box at (x,y,z,w,h,d) in model units relative to its pivot, UV at (u,v).
// Returns a BufferGeometry in pivot-local block units.
export function boxGeometry(box, uv, texW, texH) {
  const [x, y, z, w, h, d] = box;
  const [u, v] = uv;
  const x0 = x / 16, x1 = (x + w) / 16;
  const y1 = -y / 16, y0 = -(y + h) / 16; // flip y: model down -> three up
  const z0 = z / 16, z1 = (z + d) / 16;
  const rects = {
    top: [u + d, v, w, d], bottom: [u + d + w, v, w, d],
    right: [u, v + d, d, h], left: [u + d + w, v + d, d, h],
    front: [u + d, v + d, w, h], back: [u + d + w + d, v + d, w, h],
  };
  const pos = [], nrm = [], uvs = [], idx = [];
  for (const name of Object.keys(FACE)) {
    const f = FACE[name];
    const [ru, rv, rw, rh] = rects[name];
    const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2, cz = (z0 + z1) / 2;
    let center, hw, hh;
    if (name === 'top' || name === 'bottom') { center = [cx, name === 'top' ? y1 : y0, cz]; hw = (x1 - x0) / 2; hh = (z1 - z0) / 2; }
    else if (name === 'right' || name === 'left') { center = [name === 'right' ? x0 : x1, cy, cz]; hw = (z1 - z0) / 2; hh = (y1 - y0) / 2; }
    else { center = [cx, cy, name === 'front' ? z0 : z1]; hw = (x1 - x0) / 2; hh = (y1 - y0) / 2; }
    const base = pos.length / 3;
    const corners = [
      [f.U[0] * hh - f.R[0] * hw, f.U[1] * hh - f.R[1] * hw, f.U[2] * hh - f.R[2] * hw, ru, rv],
      [f.U[0] * hh + f.R[0] * hw, f.U[1] * hh + f.R[1] * hw, f.U[2] * hh + f.R[2] * hw, ru + rw, rv],
      [-f.U[0] * hh + f.R[0] * hw, -f.U[1] * hh + f.R[1] * hw, -f.U[2] * hh + f.R[2] * hw, ru + rw, rv + rh],
      [-f.U[0] * hh - f.R[0] * hw, -f.U[1] * hh - f.R[1] * hw, -f.U[2] * hh - f.R[2] * hw, ru, rv + rh],
    ];
    for (const c of corners) {
      pos.push(center[0] + c[0], center[1] + c[1], center[2] + c[2]);
      nrm.push(f.n[0], f.n[1], f.n[2]);
      uvs.push(c[3] / texW, 1 - c[4] / texH);
    }
    idx.push(base, base + 1, base + 2, base, base + 2, base + 3);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('normal', new THREE.Float32BufferAttribute(nrm, 3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
  g.setIndex(idx);
  return g;
}

// Model pivot (model units, y down) to a three position in blocks, feet at the origin.
function P(px, py, pz) { return new THREE.Vector3(px / 16, -(py - FEET) / 16, pz / 16); }

// Build a model from parts [{name, pivot:[x,y,z], box:[x,y,z,w,h,d], uv:[u,v], rot:[rx,ry,rz], mirror}]
export function buildModel(parts, opts = {}) {
  const root = new THREE.Group();
  const byName = {};
  const texW = opts.texW || 64, texH = opts.texH || 32;
  const mat = new THREE.MeshLambertMaterial({ map: opts.texture, side: THREE.DoubleSide, alphaTest: 0.5, color: opts.color ?? 0xffffff });
  if (opts.emissive) { mat.emissive = new THREE.Color(opts.emissive); mat.emissiveIntensity = opts.emissiveIntensity ?? 0.4; }
  for (const p of parts) {
    const g = new THREE.Group();
    const pv = P(p.pivot[0], p.pivot[1], p.pivot[2]);
    g.position.copy(pv);
    // model rotations are y-down: three negates each angle
    const r = p.rot || [0, 0, 0];
    g.rotation.set(-r[0], -r[1], -r[2]);
    const mesh = new THREE.Mesh(boxGeometry(p.box, p.uv, texW, texH), mat);
    mesh.castShadow = true;
    g.add(mesh);
    g.userData.rest = { x: g.rotation.x, y: g.rotation.y, z: g.rotation.z };
    root.add(g);
    byName[p.name] = g;
  }
  return { root, parts: byName, mat };
}

// Vanilla humanoid, ModelBiped geometry.
export function buildBiped(opts = {}) {
  const texW = opts.texW || 64, texH = opts.texH || 64;
  const parts = [
    { name: 'head', pivot: [0, 0, 0], box: [-4, -8, -4, 8, 8, 8], uv: [0, 0] },
    { name: 'body', pivot: [0, 0, 0], box: [-4, 0, -2, 8, 12, 4], uv: [16, 16] },
    { name: 'rArm', pivot: [-5, 2, 0], box: [-3, -2, -2, 4, 12, 4], uv: [40, 16] },
    { name: 'lArm', pivot: [5, 2, 0], box: [-1, -2, -2, 4, 12, 4], uv: [40, 16] },
    { name: 'rLeg', pivot: [-1.9, 12, 0], box: [-2, 0, -2, 4, 12, 4], uv: [0, 16] },
    { name: 'lLeg', pivot: [1.9, 12, 0], box: [-2, 0, -2, 4, 12, 4], uv: [0, 16] },
  ];
  const m = buildModel(parts, { texture: opts.texture, texW, texH, color: opts.color });
  // the body sits on the legs: the whole rig is built about the vanilla origin, feet at 24
  m.root.name = 'biped';
  return { root: m.root, parts: m.parts, mat: m.mat, height: 1.9 };
}

const POSES = {};

// Vanilla specs for the mobs the mod drops most often.
export const VANILLA = {
  Creeper: { tex: 'entity/creeper.png', texW: 64, texH: 32, parts: [
    { name: 'head', pivot: [0, 6, 0], box: [-4, -8, -4, 8, 8, 8], uv: [0, 0] },
    { name: 'body', pivot: [0, 6, 0], box: [-4, 0, -2, 8, 12, 4], uv: [16, 16] },
    { name: 'leg1', pivot: [-2, 18, 4], box: [-2, 0, -2, 4, 6, 4], uv: [0, 16] },
    { name: 'leg2', pivot: [2, 18, 4], box: [-2, 0, -2, 4, 6, 4], uv: [0, 16] },
    { name: 'leg3', pivot: [-2, 18, -4], box: [-2, 0, -2, 4, 6, 4], uv: [0, 16] },
    { name: 'leg4', pivot: [2, 18, -4], box: [-2, 0, -2, 4, 6, 4], uv: [0, 16] },
  ], height: 1.7 },
  Pig: { tex: 'entity/pig.png', texW: 64, texH: 32, parts: [
    { name: 'head', pivot: [0, 12, -6], box: [-4, -4, -8, 8, 8, 8], uv: [0, 0] },
    { name: 'body', pivot: [0, 11, 2], rot: [Math.PI / 2, 0, 0], box: [-5, -10, -7, 10, 16, 8], uv: [28, 8] },
    { name: 'leg1', pivot: [-3, 18, 7], box: [-2, 0, -2, 4, 6, 4], uv: [0, 16] },
    { name: 'leg2', pivot: [3, 18, 7], box: [-2, 0, -2, 4, 6, 4], uv: [0, 16] },
    { name: 'leg3', pivot: [-3, 18, -5], box: [-2, 0, -2, 4, 6, 4], uv: [0, 16] },
    { name: 'leg4', pivot: [3, 18, -5], box: [-2, 0, -2, 4, 6, 4], uv: [0, 16] },
  ], height: 0.9 },
  Cow: { tex: 'entity/cow.png', texW: 64, texH: 32, parts: [
    { name: 'head', pivot: [0, 4, -8], box: [-4, -4, -6, 8, 8, 6], uv: [0, 0] },
    { name: 'body', pivot: [0, 5, 2], rot: [Math.PI / 2, 0, 0], box: [-6, -10, -7, 12, 18, 10], uv: [18, 4] },
    { name: 'leg1', pivot: [-4, 12, 7], box: [-2, 0, -2, 4, 12, 4], uv: [0, 16] },
    { name: 'leg2', pivot: [4, 12, 7], box: [-2, 0, -2, 4, 12, 4], uv: [0, 16] },
    { name: 'leg3', pivot: [-4, 12, -6], box: [-2, 0, -2, 4, 12, 4], uv: [0, 16] },
    { name: 'leg4', pivot: [4, 12, -6], box: [-2, 0, -2, 4, 12, 4], uv: [0, 16] },
  ], height: 1.4 },
  Sheep: { tex: 'entity/sheep.png', texW: 64, texH: 32, parts: [
    { name: 'head', pivot: [0, 6, -8], box: [-3, -4, -6, 6, 6, 8], uv: [0, 0] },
    { name: 'body', pivot: [0, 5, 2], rot: [Math.PI / 2, 0, 0], box: [-4, -10, -7, 8, 16, 6], uv: [28, 8] },
    { name: 'leg1', pivot: [-3, 12, 7], box: [-2, 0, -2, 4, 12, 4], uv: [0, 16] },
    { name: 'leg2', pivot: [3, 12, 7], box: [-2, 0, -2, 4, 12, 4], uv: [0, 16] },
    { name: 'leg3', pivot: [-3, 12, -5], box: [-2, 0, -2, 4, 12, 4], uv: [0, 16] },
    { name: 'leg4', pivot: [3, 12, -5], box: [-2, 0, -2, 4, 12, 4], uv: [0, 16] },
  ], height: 1.3 },
  Chicken: { tex: 'entity/chicken.png', texW: 64, texH: 32, parts: [
    { name: 'head', pivot: [0, 15, -4], box: [-2, -6, -2, 4, 6, 3], uv: [0, 0] },
    { name: 'body', pivot: [0, 16, 0], rot: [Math.PI / 2, 0, 0], box: [-3, -4, -3, 6, 8, 6], uv: [0, 9] },
    { name: 'leg1', pivot: [-2, 19, 1], box: [-1, 0, -1, 2, 5, 3], uv: [26, 0] },
    { name: 'leg2', pivot: [1, 19, 1], box: [-1, 0, -1, 2, 5, 3], uv: [26, 0] },
  ], height: 0.7 },
  Wolf: { tex: 'entity/wolf.png', texW: 64, texH: 32, parts: [
    { name: 'head', pivot: [-1, 13.5, -7], box: [-3, -3, -2, 6, 6, 4], uv: [0, 0] },
    { name: 'body', pivot: [0, 14, 2], rot: [Math.PI / 2, 0, 0], box: [-4, -3, -3, 6, 9, 6], uv: [18, 14] },
    { name: 'leg1', pivot: [-2.5, 16, 7], box: [-1, 0, -1, 2, 8, 2], uv: [0, 18] },
    { name: 'leg2', pivot: [0.5, 16, 7], box: [-1, 0, -1, 2, 8, 2], uv: [0, 18] },
    { name: 'leg3', pivot: [-2.5, 16, -4], box: [-1, 0, -1, 2, 8, 2], uv: [0, 18] },
    { name: 'leg4', pivot: [0.5, 16, -4], box: [-1, 0, -1, 2, 8, 2], uv: [0, 18] },
  ], height: 0.85 },
  Spider: { tex: 'entity/spider.png', texW: 64, texH: 32, parts: [
    { name: 'head', pivot: [0, 9, -3], box: [-4, -4, -8, 8, 8, 8], uv: [32, 4] },
    { name: 'abdomen', pivot: [0, 9, 9], box: [-5, -4, -6, 10, 8, 12], uv: [0, 12] },
    { name: 'thorax', pivot: [0, 9, 0], box: [-3, -3, -3, 6, 6, 6], uv: [0, 0] },
  ], height: 0.9 },
  Ghast: { tex: 'entity/ghast.png', texW: 64, texH: 32, parts: [
    { name: 'body', pivot: [0, 0, 0], box: [-8, -8, -8, 16, 16, 16], uv: [0, 0] },
  ], height: 2.1, float: 1.2 },
  Slime: { tex: 'entity/slime.png', texW: 64, texH: 32, parts: [
    { name: 'body', pivot: [0, 18, 0], box: [-4, -4, -4, 8, 8, 8], uv: [0, 0] },
  ], height: 0.5 },
  Silverfish: { tex: 'entity/silverfish.png', texW: 64, texH: 32, parts: [
    { name: 'a', pivot: [0, 22, -2], box: [-1.5, -3, -1.5, 3, 3, 3], uv: [0, 0] },
    { name: 'b', pivot: [0, 22, 1], box: [-1.5, -3, -1.5, 3, 3, 3], uv: [0, 12] },
  ], height: 0.25 },
  Bat: { tex: 'entity/bat.png', texW: 64, texH: 64, parts: [
    { name: 'body', pivot: [0, 6, 0], box: [-3, -3, -3, 6, 6, 6], uv: [0, 0] },
  ], height: 0.8 },
  Villager: { tex: 'entity/villager.png', texW: 64, texH: 64, biped: true, height: 1.9 },
  Zombie: { tex: 'entity/zombie.png', texW: 64, texH: 64, biped: true, height: 1.9, arms: 'raised' },
  Skeleton: { tex: 'entity/skeleton.png', texW: 64, texH: 32, biped: true, height: 1.9 },
  Witch: { tex: 'entity/witch.png', texW: 64, texH: 128, biped: true, height: 1.9 },
  Enderman: { tex: 'entity/enderman.png', texW: 64, texH: 32, biped: true, height: 2.9, legScale: 1.9 },
  Steve: { tex: 'entity/steve.png', texW: 64, texH: 32, biped: true, height: 1.9 },
};
VANILLA.CaveSpider = { ...VANILLA.Spider, scale: 0.7, color: 0x99aabb };
// Exact layouts from the decompiled ModelSpider, ModelEnderman, ModelBat, ModelGhast,
// ModelSlime and ModelWither (pivots and boxes as the sources set them; feet at 24).
Object.assign(VANILLA, {
  Spider: { tex: 'entity/spider.png', texW: 64, texH: 32, height: 0.9, parts: [
    { name: 'head', pivot: [0, 15, -3], box: [-4, -4, -8, 8, 8, 8], uv: [32, 4] },
    { name: 'neck', pivot: [0, 15, 0], box: [-3, -3, -3, 6, 6, 6], uv: [0, 0] },
    { name: 'body', pivot: [0, 15, 9], box: [-5, -4, -6, 10, 8, 12], uv: [0, 12] },
    { name: 'leg1', pivot: [-4, 15, 2], box: [-15, -1, -1, 16, 2, 2], uv: [18, 0] },
    { name: 'leg2', pivot: [4, 15, 2], box: [-1, -1, -1, 16, 2, 2], uv: [18, 0] },
    { name: 'leg3', pivot: [-4, 15, 1], box: [-15, -1, -1, 16, 2, 2], uv: [18, 0] },
    { name: 'leg4', pivot: [4, 15, 1], box: [-1, -1, -1, 16, 2, 2], uv: [18, 0] },
    { name: 'leg5', pivot: [-4, 15, 0], box: [-15, -1, -1, 16, 2, 2], uv: [18, 0] },
    { name: 'leg6', pivot: [4, 15, 0], box: [-1, -1, -1, 16, 2, 2], uv: [18, 0] },
    { name: 'leg7', pivot: [-4, 15, -1], box: [-15, -1, -1, 16, 2, 2], uv: [18, 0] },
    { name: 'leg8', pivot: [4, 15, -1], box: [-1, -1, -1, 16, 2, 2], uv: [18, 0] },
  ] },
  Enderman: { tex: 'entity/enderman.png', texW: 64, texH: 32, height: 2.9, feetY: 42, parts: [
    { name: 'head', pivot: [0, 0, 0], box: [-4, -8, -4, 8, 8, 8], uv: [0, 0] },
    { name: 'body', pivot: [0, 0, 0], box: [-4, 0, -2, 8, 12, 4], uv: [32, 16] },
    { name: 'rArm', pivot: [-3, 2, 0], box: [-1, -2, -1, 2, 30, 2], uv: [56, 0] },
    { name: 'lArm', pivot: [5, 2, 0], box: [-1, -2, -1, 2, 30, 2], uv: [56, 0] },
    { name: 'leg1', pivot: [-2, 12, 0], box: [-1, 0, -1, 2, 30, 2], uv: [56, 0] },
    { name: 'leg2', pivot: [2, 12, 0], box: [-1, 0, -1, 2, 30, 2], uv: [56, 0] },
  ] },
  Bat: { tex: 'entity/bat.png', texW: 64, texH: 64, height: 0.8, feetY: 16, parts: [
    { name: 'head', pivot: [0, -2, 0], box: [-3, -3, -3, 6, 6, 6], uv: [0, 0] },
    { name: 'body', pivot: [0, 0, 0], box: [-3, 4, -3, 6, 12, 6], uv: [0, 16] },
    { name: 'earL', pivot: [0, 0, 0], box: [-4, -6, -2, 3, 4, 1], uv: [24, 0] },
    { name: 'earR', pivot: [0, 0, 0], box: [1, -6, -2, 3, 4, 1], uv: [24, 0] },
    { name: 'wingR', pivot: [-3, 0, 3], box: [-12, 1, 1.5, 10, 16, 1], uv: [42, 0] },
    { name: 'wingL', pivot: [3, 0, 3], box: [2, 1, 1.5, 10, 16, 1], uv: [42, 0] },
  ] },
  Ghast: { tex: 'entity/ghast.png', texW: 64, texH: 32, height: 2.1, float: 1.2, parts: [
    { name: 'body', pivot: [0, 0, 0], box: [-8, -8, -8, 16, 16, 16], uv: [0, 0] },
    ...[8, 10, 6, 9, 7, 11, 8, 10, 6].map((j, i) => ({ name: 'leg' + (i + 1), pivot: [((i % 3) - 1) * 5, 8, (Math.floor(i / 3) - 1) * 5], box: [-1, 0, -1, 2, j, 2], uv: [0, 0] })),
  ] },
  Slime: { tex: 'entity/slime.png', texW: 64, texH: 32, height: 0.5, parts: [
    { name: 'body', pivot: [0, 0, 0], box: [-4, 16, -4, 8, 8, 8], uv: [0, 0] },
    { name: 'core', pivot: [0, 0, 0], box: [-3, 17, -3, 6, 6, 6], uv: [0, 0] },
    { name: 'eyeR', pivot: [0, 0, 0], box: [-3.25, 18, -3.5, 2, 2, 2], uv: [32, 0] },
    { name: 'eyeL', pivot: [0, 0, 0], box: [1.25, 18, -3.5, 2, 2, 2], uv: [32, 4] },
    { name: 'mouth', pivot: [0, 0, 0], box: [0, 21, -3.5, 1, 1, 1], uv: [32, 8] },
  ] },
  Wither: { tex: 'entity/skeleton.png', texW: 64, texH: 32, color: 0x2a2a2e, height: 3.2, parts: [
    { name: 'spine', pivot: [0, 0, 0], box: [-10, 3.9, -0.5, 20, 3, 3], uv: [0, 16] },
    { name: 'ribs', pivot: [-2, 6.9, -0.5], box: [0, 0, 0, 3, 10, 3], uv: [0, 22] },
    { name: 'tail', pivot: [-2, 6.9, -0.5], box: [0, 10, 0, 3, 6, 3], uv: [12, 22] },
    { name: 'headC', pivot: [0, -8, 0], box: [-4, -4, -4, 8, 8, 8], uv: [0, 0] },
    { name: 'headL', pivot: [-10, -4, 0], box: [-4, -4, -4, 6, 6, 6], uv: [32, 0] },
    { name: 'headR', pivot: [10, -4, 0], box: [-4, -4, -4, 6, 6, 6], uv: [32, 0] },
  ] },
});

// Horse (ModelHorse), silverfish (ModelSilverfish: seven segments, pivots from its f-walk), witch (a villager
// with the hat and nose from ModelWitch), cave spider (ModelSpider on cave_spider.png, 0.7 scale).
const SF_LEN = [[3, 2, 2], [4, 3, 2], [6, 4, 3], [3, 3, 3], [2, 2, 3], [2, 1, 2], [1, 1, 2]];
const SF_UV = [[0, 0], [0, 4], [0, 9], [0, 16], [0, 22], [11, 0], [13, 4]];
const SF_Z = (() => { const z = []; let f = -3.5; for (let i = 0; i < 7; i++) { z.push(f); if (i < 6) f += (SF_LEN[i][2] + SF_LEN[i + 1][2]) * 0.5; } return z; })();
Object.assign(VANILLA, {
  Horse: { tex: 'entity/horse/horse_white.png', texW: 64, texH: 64, height: 1.9, parts: [
    { name: 'body', pivot: [0, 11, 9], box: [-5, -8, -19, 10, 10, 24], uv: [0, 34] },
    { name: 'tailBase', pivot: [0, 3, 14], box: [-1, -1, 0, 2, 2, 3], uv: [44, 0] },
    { name: 'tailMiddle', pivot: [0, 3, 14], box: [-1.5, -2, 3, 3, 4, 7], uv: [38, 7] },
    { name: 'tailTip', pivot: [0, 3, 14], box: [-1.5, -4.5, 9, 3, 4, 7], uv: [24, 3] },
    { name: 'legBL', pivot: [4, 9, 11], box: [-2.5, -2, -2.5, 4, 9, 5], uv: [78, 29] },
    { name: 'shinBL', pivot: [4, 16, 11], box: [-2, 0, -1.5, 3, 5, 3], uv: [78, 43] },
    { name: 'hoofBL', pivot: [4, 16, 11], box: [-2.5, 5.1, -2, 4, 3, 4], uv: [78, 51] },
    { name: 'legBR', pivot: [-4, 9, 11], box: [-1.5, -2, -2.5, 4, 9, 5], uv: [96, 29] },
    { name: 'shinBR', pivot: [-4, 16, 11], box: [-1, 0, -1.5, 3, 5, 3], uv: [96, 43] },
    { name: 'hoofBR', pivot: [-4, 16, 11], box: [-1.5, 5.1, -2, 4, 3, 4], uv: [96, 51] },
    { name: 'legFL', pivot: [4, 9, -8], box: [-1.9, -1, -2.1, 3, 8, 4], uv: [44, 29] },
    { name: 'shinFL', pivot: [4, 16, -8], box: [-1.9, 0, -1.6, 3, 5, 3], uv: [44, 41] },
    { name: 'hoofFL', pivot: [4, 16, -8], box: [-2.4, 5.1, -2.1, 4, 3, 4], uv: [44, 51] },
    { name: 'legFR', pivot: [-4, 9, -8], box: [-1.1, -1, -2.1, 3, 8, 4], uv: [60, 29] },
    { name: 'shinFR', pivot: [-4, 16, -8], box: [-1.1, 0, -1.6, 3, 5, 3], uv: [60, 41] },
    { name: 'hoofFR', pivot: [-4, 16, -8], box: [-1.6, 5.1, -2.1, 4, 3, 4], uv: [60, 51] },
    { name: 'head', pivot: [0, 4, -10], box: [-2.5, -10, -1.5, 5, 5, 7], uv: [0, 0] },
    { name: 'mouthTop', pivot: [0, 3.95, -10], box: [-2, -10, -7, 4, 3, 6], uv: [24, 18] },
    { name: 'mouthBottom', pivot: [0, 4, -10], box: [-2, -7, -6.5, 4, 2, 5], uv: [24, 27] },
  ] },
  Silverfish: { tex: 'entity/silverfish.png', texW: 64, texH: 32, height: 0.5, parts: SF_LEN.map((d, i) => ({
    name: 'seg' + i, pivot: [0, 24 - d[1], SF_Z[i]], box: [-d[0] / 2, 0, -d[2] / 2, d[0], d[1], d[2]], uv: SF_UV[i] })) },
  Witch: { tex: 'entity/witch.png', texW: 64, texH: 128, height: 1.9, parts: [
    { name: 'head', pivot: [0, 0, 0], box: [-4, -10, -4, 8, 10, 8], uv: [0, 0] },
    { name: 'nose', pivot: [0, -2, 0], box: [-1, -1, -6, 2, 4, 2], uv: [24, 0] },
    { name: 'body', pivot: [0, 0, 0], box: [-4, 0, -3, 8, 12, 6], uv: [16, 20] },
    { name: 'arms', pivot: [0, 3, -1], box: [-8, -2, -2, 16, 4, 4], uv: [40, 38] },
    { name: 'leg1', pivot: [-2, 12, 0], box: [-2, 0, -2, 4, 12, 4], uv: [0, 22] },
    { name: 'leg2', pivot: [2, 12, 0], box: [-2, 0, -2, 4, 12, 4], uv: [0, 22] },
    { name: 'hatBrim', pivot: [-5, -10, -5], box: [0, 0, 0, 10, 2, 10], uv: [0, 64] },
    { name: 'hatCone', pivot: [-3, -12, -3], box: [0, 0, 0, 6, 6, 6], uv: [0, 76] },
  ] },
  CaveSpider: { tex: 'entity/cave_spider.png', texW: 64, texH: 32, height: 0.6, scale: 0.7, parts: VANILLA.Spider.parts },
});

// Stylised stand-ins for mods: lists of coloured boxes in block units (feet at 0).
const STAND_IN = {
  Mobzilla: { tex: 'orespawn/mobzilla_1.png', h: 4, eyes: 0xff4a1a, parts: [[-1.2, 1.4, -1.6, 2.4, 1.4, 3.6, 0x4b6b3a], [-0.8, 2.7, 0.2, 1.6, 1.2, 1.4, 0x4b6b3a], [-0.4, 3.4, 0.6, 1.0, 0.6, 0.8, 0x6d8a4f], [-1.0, 0.0, -1.2, 0.7, 1.5, 0.8, 0x3b4e2a], [0.4, 0.0, -1.2, 0.7, 1.5, 0.8, 0x3b4e2a], [-1.0, 0.0, 0.8, 0.7, 1.4, 0.8, 0x3b4e2a], [0.4, 0.0, 0.8, 0.7, 1.4, 0.8, 0x3b4e2a], [-0.5, 1.2, 2.2, 1.0, 1.0, 2.0, 0x4b6b3a], [-0.2, 1.6, 4.2, 0.4, 0.4, 0.4, 0x2c2c2c]] },
  Mothra: { tex: 'orespawn/mothscale_1.png', h: 2.4, eyes: 0xffe08a, flying: true, parts: [[-0.12, 0.6, -0.8, 0.24, 0.24, 1.7, 0x7a6a50], [-3.4, 0.6, -1.4, 3.2, 0.1, 2.6, 0xd8cdb0], [0.2, 0.6, -1.4, 3.2, 0.1, 2.6, 0xd8cdb0], [-3.0, 0.6, -0.2, 2.4, 0.08, 1.6, 0xb7a68a], [0.6, 0.6, -0.2, 2.4, 0.08, 1.6, 0xb7a68a]] },
  Brutalfly: { tex: 'orespawn/Brutalflytexture.png', h: 1.6, eyes: 0xff3030, parts: [[-0.6, 0.5, -0.5, 1.2, 0.9, 1.2, 0x3a3a3a], [-0.5, 1.0, -0.9, 1.0, 0.8, 0.8, 0x2d2d2d], [-1.6, 0.8, 0, 1.6, 0.05, 1.0, 0x9ad8ff], [0.0, 0.8, 0, 1.6, 0.05, 1.0, 0x9ad8ff]] },
  Hammerhead: { tex: 'orespawn/Hammerheadtexture.png', h: 2.2, eyes: 0x000000, parts: [[-0.4, 0.8, -1.5, 0.8, 0.8, 3.0, 0x6d7a88], [-1.6, 0.9, -1.6, 3.2, 0.25, 0.4, 0x6d7a88], [-0.4, 1.4, 0.6, 0.8, 0.9, 0.2, 0x5c6878]] },
  Cephadrome: { tex: 'orespawn/Cephadrome.png', h: 1.5, eyes: 0xffb0ff, flying: true, parts: [[-2.0, 0.8, -1.2, 4.0, 0.18, 2.4, 0x2a2b44], [-0.5, 0.8, -1.5, 1.0, 0.25, 0.6, 0x3d3f63]] },
  Robo: { tex: 'orespawn/Robot1.png', h: 2.6, eyes: 0xff3a3a, parts: [[-0.5, 0.0, -0.5, 0.4, 1.0, 0.4, 0x9aa3ad], [0.1, 0.0, -0.5, 0.4, 1.0, 0.4, 0x9aa3ad], [-0.9, 1.0, -0.9, 1.8, 1.1, 1.8, 0x7e8794], [-0.7, 2.1, -0.7, 1.4, 0.7, 1.4, 0xb8c0ca]] },
  Ant: { tex: 'orespawn/ant.png', h: 0.9, eyes: 0xffffff, parts: [[-0.3, 0.1, -0.7, 0.6, 0.5, 0.6, 0x2b1d12], [-0.25, 0.1, -0.1, 0.5, 0.45, 0.6, 0x3a2716], [-0.3, 0.1, 0.45, 0.6, 0.5, 0.8, 0x2b1d12]] },
  Bunny: { tex: 'orespawn/EasterBunnytexture.png', h: 1.6, eyes: 0x222222, parts: [[-0.4, 0.2, -0.4, 0.8, 0.7, 0.9, 0xf2eee6], [-0.35, 0.8, -0.6, 0.7, 0.6, 0.5, 0xf6f2ea], [-0.15, 1.2, -0.7, 0.2, 0.7, 0.14, 0xf6f2ea], [0.05, 1.2, -0.7, 0.2, 0.7, 0.14, 0xf6f2ea]] },
  LargeWorm: { tex: 'orespawn/WormLargetexture.png', h: 1.2, eyes: 0xffe0a0, worm: true, parts: [] },
  Coin: { tex: 'orespawn/Cointexture.png', h: 0.4, eyes: 0xffd24a, parts: [[-0.3, 0.1, -0.3, 0.6, 0.12, 0.6, 0xf2c14e]] },
  CaterKiller: { tex: 'orespawn/CaterKillertexture.png', h: 1.4, eyes: 0xff9a40, parts: [[-0.5, 0.1, -2.4, 1.0, 0.8, 1.0, 0x9a6a3a], [-0.5, 0.1, -1.2, 1.0, 0.8, 1.0, 0x8a5a30], [-0.5, 0.1, 0.0, 1.0, 0.8, 1.0, 0x7a4e2a], [-0.45, 0.5, 0.9, 0.9, 0.7, 0.8, 0x6a4424]] },
  CloudShark: { tex: 'orespawn/CloudShark.png', h: 2.0, eyes: 0xa0e0ff, flying: true, parts: [[-0.7, 0.8, -1.6, 1.4, 0.9, 3.2, 0xdfe8f2], [-0.2, 1.6, -0.2, 0.2, 0.8, 0.8, 0xc8d6e6], [-0.4, 0.6, 1.4, 0.8, 0.6, 1.2, 0xb8c8dc]] },
  Mantis: { tex: 'orespawn/Mantistexture.png', h: 2.0, eyes: 0xff5a3a, parts: [[-0.4, 0.4, -0.6, 0.8, 0.8, 1.6, 0x6b8a3a], [-0.7, 0.6, -1.2, 0.4, 0.4, 1.0, 0x7a9a48], [0.3, 0.6, -1.2, 0.4, 0.4, 1.0, 0x7a9a48], [-0.2, 1.1, -0.4, 0.4, 0.5, 0.4, 0x5b7a2a]] },
  Rotator: { tex: 'orespawn/Rotatortexture.png', h: 1.6, eyes: 0xffdc60, flying: true, parts: [[-0.6, 0.6, -0.6, 1.2, 0.3, 1.2, 0x9aa0aa], [-1.8, 0.7, -0.1, 3.6, 0.08, 0.2, 0xb0b6c0]] },
  Dragon: { tex: 'orespawn/Dragon.png', h: 3.0, eyes: 0xff8a2a, flying: true, parts: [[-1.0, 0.8, -1.4, 2.0, 1.0, 3.0, 0x6a2a2a], [-0.6, 1.4, 1.6, 1.2, 0.8, 1.2, 0x7a3434], [-2.8, 0.9, -0.5, 1.8, 0.2, 2.2, 0x8a3a3a], [1.0, 0.9, -0.5, 1.8, 0.2, 2.2, 0x8a3a3a]] },
  Bee: { tex: 'orespawn/Beetexture.png', h: 0.9, eyes: 0x111111, flying: true, parts: [[-0.4, 0.3, -0.5, 0.8, 0.7, 1.0, 0xe0b020], [-0.4, 0.3, 0.5, 0.8, 0.7, 0.4, 0x202020], [-0.9, 0.8, -0.2, 1.8, 0.04, 0.6, 0xc8e8ff]] },
};
function standinKeyFor(id) {
  const k = String(id).toLowerCase();
  if (k.includes('mobzilla')) return 'Mobzilla';
  if (k.includes('mantis')) return 'Mantis';
  if (k.includes('caterkiller')) return 'CaterKiller';
  if (k.includes('cloudshark') || k.includes('cloud shark')) return 'CloudShark';
  if (k.includes('mothra')) return 'Mothra';
  if (k.includes('brutalfly')) return 'Brutalfly';
  if (k.includes('hammerhead')) return 'Hammerhead';
  if (k.includes('cephadrome')) return 'Cephadrome';
  if (k.includes('robo')) return 'Robo';
  if (k.includes('ant')) return 'Ant';
  if (k.includes('bunny')) return 'Bunny';
  if (k.includes('robo')) return 'Robo';
  if (k.includes('worm')) return 'LargeWorm';
  if (k.includes('coin')) return 'Coin';
  if (k.includes('caterkiller')) return 'CaterKiller';
  if (k.includes('cloudshark') || k.includes('cloud shark')) return 'CloudShark';
  if (k.includes('mantis')) return 'Mantis';
  if (k.includes('rotator')) return 'Rotator';
  if (k.includes('dragon')) return 'Dragon';
  if (k === 'bee' || k.includes('bee')) return 'Bee';
  return null;
}

// Build a mob by its entity id. Returns {root, height, anim(t, dt, opts), parts, kind}.
export function makeMob(id, opts = {}) {
  const key = String(id);
  const isApple = /apple/i.test(key) && /cow/i.test(key);
  const vanilla = isApple ? { ...VANILLA.Cow, tex: 'orespawn/red_cow.png' } : (VANILLA[key] || (key === 'Giant' ? VANILLA.Zombie : null));
  let out;
  if (vanilla) {
    const texture = tex(vanilla.tex, { wrap: false });
    if (vanilla.biped) {
      const b = buildBiped({ texture, texW: vanilla.texW, texH: vanilla.texH, color: opts.color ?? 0xffffff });
      if (vanilla.arms === 'raised') { b.parts.rArm.rotation.x = Math.PI / 2; b.parts.lArm.rotation.x = Math.PI / 2; }
      if (key === 'Enderman') { b.root.scale.y = vanilla.legScale || 1; }
      if (key === 'Witch') { const hat = new THREE.Mesh(new THREE.ConeGeometry(0.5, 0.8, 12), new THREE.MeshLambertMaterial({ color: 0x3a2a4a })); hat.position.set(0, 0.5, 0); b.parts.head.add(hat); }
      out = { root: b.root, parts: b.parts, height: vanilla.height, kind: 'biped' };
    } else {
      const m = buildModel(vanilla.parts, { texture, texW: vanilla.texW, texH: vanilla.texH, color: opts.color ?? 0xffffff });
      out = { root: m.root, parts: m.parts, height: vanilla.height, kind: 'quad', float: vanilla.float || 0 };
      if (vanilla.color != null) m.mat.color.setHex(vanilla.color);
      if (vanilla.feetY) m.root.position.y = -(vanilla.feetY - FEET) / 16;
    }
    if (vanilla.scale) out.root.scale.setScalar(vanilla.scale);
    if (key === 'Giant') out.root.scale.setScalar(6);
    out.root.traverse((o) => { if (o.isMesh) { o.castShadow = true; } });
  } else {
    out = standin(key, opts);
  }
  if (opts.scale) out.root.scale.multiplyScalar(opts.scale);
  if (opts.colorHex && out.root) out.root.traverse((o) => { if (o.isMesh && o.material) o.material.color.setHex(opts.colorHex); });
  out.anim = makeAnim(out);
  out.eyeGlow = null;
  return out;
}

function standin(key, opts) {
  const sk = standinKeyFor(key);
  const spec = STAND_IN[sk] || { h: 1.8, eyes: 0xff7a7a, parts: [[-0.4, 0, -0.4, 0.8, 1.2, 0.8, 0x6b6378], [-0.3, 1.2, -0.3, 0.6, 0.6, 0.6, 0x7b7388]] };
  const root = new THREE.Group();
  const parts = {};
  const eyeMat = new THREE.MeshBasicMaterial({ color: spec.eyes });
  spec.parts.forEach((p, i) => {
    const mat = spec.tex ? new THREE.MeshLambertMaterial({ map: tex(spec.tex), color: 0xffffff, emissive: new THREE.Color(spec.glow || 0x000000), emissiveIntensity: spec.glow ? 0.25 : 0 }) : new THREE.MeshLambertMaterial({ color: p[6] });
    const m = new THREE.Mesh(new THREE.BoxGeometry(p[3], p[4], p[5]), mat);
    m.position.set(p[0] + p[3] / 2, p[1] + p[4] / 2, p[2] + p[5] / 2);
    m.castShadow = true;
    root.add(m);
    parts['p' + i] = m;
  });
  if (spec.worm) {
    for (let i = 0; i < 7; i++) {
      const s = new THREE.Mesh(new THREE.SphereGeometry(0.42 - i * 0.02, 12, 8), new THREE.MeshLambertMaterial({ color: 0xa35f6a }));
      s.position.set(i * 0.5, 0.42, Math.sin(i) * 0.2);
      root.add(s);
      parts['w' + i] = s;
    }
  }
  // glowing eyes on the front
  const eyeL = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.1, 0.05), eyeMat);
  const eyeR = eyeL.clone();
  eyeL.position.set(spec.h * 0.25, spec.h * 0.8, -0.1);
  eyeR.position.set(spec.h * 0.25, spec.h * 0.8, 0.1);
  root.add(eyeL, eyeR);
  parts.eyes = [eyeL, eyeR];
  root.scale.setScalar(opts.scale || 1);
  if (spec.h > 0) { /* stand-in height is the spec height */ }
  return { root, parts, height: spec.h, kind: 'standin', eyeMat, flying: !!spec.flying, worm: !!spec.worm };
}

// Idle animation: walk cycle for quadrupeds and bipeds, breathing, the creeper hiss
// and enderman jitter, and head tracking on bipeds.
export function makeAnim(m) {
  const { root, parts } = m;
  return function (t, dt, o = {}) {
    if (m.kind === 'biped') {
      const sw = (o.walk ?? 1) * Math.sin(t * 5.2);
      if (parts.rLeg) { parts.rLeg.rotation.x = sw * 0.9; parts.lLeg.rotation.x = -sw * 0.9; }
      if (parts.rArm && !o.still) { parts.rArm.rotation.x = -sw * 0.7 + (o.armRaise || 0); parts.lArm.rotation.x = sw * 0.7 + (o.armRaise || 0); }
      if (parts.head && o.lookAt) parts.head.rotation.y = o.lookAt;
      if (o.enderJitter) root.position.x += Math.sin(t * 60) * 0.01 * o.enderJitter;
      root.position.y = Math.abs(Math.sin(t * 5.2)) * 0.02;
    } else if (m.kind === 'quad') {
      const sw = (o.walk ?? 1) * Math.sin(t * 6.0);
      const legs = Object.keys(parts).filter((k) => k.startsWith('leg'));
      legs.forEach((k, i) => { parts[k].rotation.x = (i % 2 ? -1 : 1) * sw * 0.7; });
      if (m.float) root.position.y = Math.sin(t * 1.4) * 0.15 + m.float;
      if (o.hiss) {
        const s = 1 + 0.12 * Math.sin(t * 40) * o.hiss;
        parts.body.scale.setScalar(s); parts.body.rotation.z = 0;
      }
    } else {
      // stand-ins bob and breathe; flying ones hover
      const bob = Math.sin(t * (m.flying ? 4 : 2)) * (m.flying ? 0.18 : 0.04);
      root.position.y = bob + (m.flying ? 0.8 : 0);
      if (m.worm) Object.keys(parts).filter((k) => k[0] === 'w').forEach((k, i) => { parts[k].position.y = 0.42 + Math.sin(t * 5 - i * 0.6) * 0.12; });
      if (m.eyeMat) m.eyeMat.color.setHex(0xffffff).lerp(new THREE.Color(0xffffff), 0);
    }
  };
}

export function biped(opts) { return buildBiped(opts); }
export function mobFromSpec(id, opts) { return makeMob(id, opts); }
export const MOB_SPECS = VANILLA;
export { TEXP, P };

// Sound events (stub, replaced by the full table).
export function mobSounds(id) { const k = String(id).toLowerCase(); return { say: 'mob.' + k + '.say', hurt: 'mob.' + k + '.hurt', death: 'mob.' + k + '.death', step: 'mob.' + k + '.step' }; }
