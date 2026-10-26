// The site's Minecraft mob library. Legacy helpers (boxGeometry, buildModel, buildBiped) come first and
// keep their old orientation (blocks.js and Steve use them); makeMob below builds every mob from the
// generated 1.7.10 / OreSpawn model data. Old header: Vanilla parts use the 1.7.10 ModelBox UV layout and the
// ModelBiped / ModelCreeper / ModelPig ... geometry (model units: 16 per block,
// y points down, feet at y=24). Mods without a vanilla model get voxel stand-ins.
import * as THREE from 'three';
import { tex, whenMobTexturesLoaded } from './textures.js';
import { VANILLA_MODELS } from './vanilla-models.js';
import { OS_MODELS } from './orespawn-models.js';
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
  const pa = m.parts;
  Object.assign(pa, { head: pa.head, body: pa.body, rightArm: pa.rArm, leftArm: pa.lArm, rightLeg: pa.rLeg, leftLeg: pa.lLeg });
  return { root: m.root, parts: pa, mat: m.mat, height: 1.9 };
}


// ===================================================================== rig from model data
// Coordinates: a 1.7.10 model has y pointing down, feet at y = 24, the front at -z. The game draws
// with glScalef(-1,-1,1) then a 180 degree turn about y, which is a proper rotation; here a model
// point (x,y,z) lands at (-x,-y,z)/16 relative to its pivot and the mob faces -z. Rotations follow
// from conjugating with that map: three (x,y,z) = (-rx,-ry,rz) with Euler order ZYX, as the game
// applies Z, then Y, then X.
const FEET_UP = FEET / 16;
const W = (p) => new THREE.Vector3(-p[0] / 16, -p[1] / 16, p[2] / 16);

// ModelBox, vertex for vertex: eight corners, six quads, per-quad texture rectangles, mirror flips
// the quads' vertex order. Returns a BufferGeometry in block units about the part's pivot.
const QUADS = [[5, 1, 2, 6], [0, 4, 7, 3], [5, 4, 0, 1], [2, 3, 7, 6], [1, 0, 3, 2], [4, 5, 6, 7]];
export function mcBoxGeometry(b, uv, tw, th, mirror) {
  const [x, y, z, w, h, d] = b;
  const e = b[6] || 0;
  const [u, v] = uv;
  let x1 = x - e, y1 = y - e, z1 = z - e, x2 = x + w + e, y2 = y + h + e, z2 = z + d + e;
  if (mirror) { const s = x2; x2 = x1; x1 = s; }
  const V = [[x1, y1, z1], [x2, y1, z1], [x2, y2, z1], [x1, y2, z1], [x1, y1, z2], [x2, y1, z2], [x2, y2, z2], [x1, y2, z2]];
  const R = [
    [u + d + w, v + d, u + d + w + d, v + d + h],
    [u, v + d, u + d, v + d + h],
    [u + d, v, u + d + w, v + d],
    [u + d + w, v + d, u + d + w + w, v],
    [u + d, v + d, u + d + w, v + d + h],
    [u + d + w + d, v + d, u + d + w + d + w, v + d + h],
  ];
  const cx = (x1 + x2) / 2, cy = (y1 + y2) / 2, cz = (z1 + z2) / 2;
  const pos = [], nrm = [], uvs = [], idx = [];
  QUADS.forEach((q, qi) => {
    const [u1, v1, u2, v2] = R[qi];
    let vs = q.map((k, i) => ({ p: V[k], t: [[u2, v1], [u1, v1], [u1, v2], [u2, v2]][i] }));
    if (mirror) vs = vs.slice().reverse();
    const P3 = vs.map((o) => W(o.p));
    const a = new THREE.Vector3().subVectors(P3[1], P3[0]);
    const c = new THREE.Vector3().subVectors(P3[1], P3[2]);
    let n = new THREE.Vector3().crossVectors(c, a);
    if (n.lengthSq() === 0) n.set(0, 1, 0);
    n.normalize();
    // make the normal point away from the box centre (the sign differs per face after the map)
    const fc = vs.reduce((s, o) => s.add(W(o.p)), new THREE.Vector3()).multiplyScalar(0.25);
    if (n.dot(fc.sub(W([cx, cy, cz]))) < 0) n.negate();
    const base = pos.length / 3;
    P3.forEach((p, i) => { pos.push(p.x, p.y, p.z); nrm.push(n.x, n.y, n.z); uvs.push(vs[i].t[0] / tw, 1 - vs[i].t[1] / th); });
    // wind counter-clockwise about the normal
    const t1 = new THREE.Vector3().crossVectors(new THREE.Vector3().subVectors(P3[1], P3[0]), new THREE.Vector3().subVectors(P3[2], P3[0]));
    if (t1.dot(n) >= 0) idx.push(base, base + 1, base + 2, base, base + 2, base + 3);
    else idx.push(base, base + 2, base + 1, base, base + 3, base + 2);
  });
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('normal', new THREE.Float32BufferAttribute(nrm, 3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
  g.setIndex(idx);
  return g;
}

const geoCache = new Map();
// box: [x, y, z, w, h, d, inflate, u, v, mirror, texW, texH]
function boxGeo(b) {
  const key = b.join(',');
  if (!geoCache.has(key)) geoCache.set(key, mcBoxGeometry(b.slice(0, 7), [b[7], b[8]], b[10], b[11], !!b[9]));
  return geoCache.get(key);
}

function setRot(g, x, y, z) {
  const r = g.userData.rest.rot;
  g.rotation.set(-(x ?? r[0]), -(y ?? r[1]), (z ?? r[2]), 'ZYX');
}
function setPivot(g, x, y, z) {
  const p = g.userData.rest.pivot;
  g.position.copy(W([x ?? p[0], y ?? p[1], z ?? p[2]]));
}

// Build one layer of a model: a Group per ModelRenderer (children nested), meshes per box.
// o: skip [names], texture, color, additive, transparent, emissive, alphaTest, texSize override
function buildRig(data, texture, o = {}) {
  const root = new THREE.Group();
  root.position.y = FEET_UP;
  const parts = {};
  const skip = new Set(o.skip || []);
  const matOpts = { map: texture, side: THREE.DoubleSide, color: o.color ?? 0xffffff, alphaTest: o.alphaTest ?? 0.1 };
  let mat;
  if (o.additive) mat = new THREE.MeshBasicMaterial({ map: texture, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide, color: o.color ?? 0xffffff, fog: false });
  else {
    mat = new THREE.MeshLambertMaterial(matOpts);
    if (o.transparent) { mat.transparent = true; mat.depthWrite = false; mat.alphaTest = 0; if (o.opacity != null) mat.opacity = o.opacity; }
    if (o.emissive) { mat.emissive = new THREE.Color(o.emissive); mat.emissiveIntensity = o.emissiveIntensity ?? 0.6; }
  }
  const make = (name, parent) => {
    const p = data.parts[name];
    if (!p || skip.has(name)) return;
    const g = new THREE.Group();
    g.name = name;
    g.rotation.order = 'ZYX';
    g.userData.rest = { pivot: p.pivot.slice(), rot: (p.rot || [0, 0, 0]).slice() };
    p.boxes.forEach((b) => {
      const m = new THREE.Mesh(boxGeo(b), mat);
      m.castShadow = true;
      g.add(m);
    });
    setPivot(g, ...p.pivot);
    setRot(g, ...g.userData.rest.rot);
    parent.add(g);
    parts[name] = g;
    (p.children || []).forEach((c) => make(c, g));
  };
  data.roots.forEach((n) => make(n, root));
  return { root, parts, mat };
}

function resetRig(parts) {
  for (const k in parts) {
    const g = parts[k];
    const r = g.userData.rest;
    if (!r) continue;
    g.position.copy(W(r.pivot));
    g.rotation.set(-r.rot[0], -r.rot[1], r.rot[2], 'ZYX');
    g.visible = true;
  }
}

// ===================================================================== vanilla specs
// layers: [{ model, tex, skip, ... }]; the first layer is the one the animation drives, the others
// copy its rotations (wool, slime outer, glowing eyes). anim: key into ANIMS.
const T = (p) => 'entity/' + p;
const BIPED_SKIP = ['bipedCloak', 'bipedEars'];
const FLEECE = [0xffffff, 0xd9801f, 0xb34dd9, 0x6699d9, 0xe6e633, 0x80cc1a, 0xf280a6, 0x4d4d4d, 0x999999, 0x4d8099, 0x8040b3, 0x334db3, 0x664d33, 0x667f33, 0x993333, 0x1a1a1a];
export const MOB_SPECS = {
  Zombie: { layers: [{ model: 'zombie', tex: T('zombie/zombie.png'), skip: BIPED_SKIP }], anim: 'zombie', kind: 'biped' },
  Giant: { layers: [{ model: 'zombie', tex: T('zombie/zombie.png'), skip: BIPED_SKIP }], anim: 'zombie', kind: 'biped', scale: 6 },
  PigZombie: { layers: [{ model: 'zombie', tex: T('zombie_pigman.png'), skip: BIPED_SKIP }], anim: 'zombie', kind: 'biped' },
  ZombieVillager: { layers: [{ model: 'zombie', tex: T('zombie/zombie_villager.png'), skip: BIPED_SKIP }], anim: 'zombie', kind: 'biped' },
  Skeleton: { layers: [{ model: 'skeleton', tex: T('skeleton/skeleton.png'), skip: BIPED_SKIP }], anim: 'biped', kind: 'biped' },
  WitherSkeleton: { layers: [{ model: 'skeleton', tex: T('skeleton/wither_skeleton.png'), skip: BIPED_SKIP }], anim: 'biped', kind: 'biped', scale: 1.2 },
  Steve: { layers: [{ model: 'biped', tex: T('steve.png'), skip: BIPED_SKIP }], anim: 'biped', kind: 'biped' },
  Creeper: { layers: [{ model: 'creeper', tex: T('creeper/creeper.png'), skip: ['field_78133_b'] }], anim: 'creeper', kind: 'quad' },
  Spider: { layers: [{ model: 'spider', tex: T('spider/spider.png') }, { model: 'spider', tex: T('spider_eyes.png'), additive: true }], anim: 'spider', kind: 'quad' },
  CaveSpider: { layers: [{ model: 'spider', tex: T('spider/cave_spider.png') }, { model: 'spider', tex: T('spider_eyes.png'), additive: true }], anim: 'spider', kind: 'quad', scale: 0.7 },
  Enderman: { layers: [{ model: 'enderman', tex: T('enderman/enderman.png') }, { model: 'enderman', tex: T('enderman/enderman_eyes.png'), additive: true }], anim: 'enderman', kind: 'biped' },
  Silverfish: { layers: [{ model: 'silverfish', tex: T('silverfish.png') }], anim: 'silverfish', kind: 'quad' },
  Slime: { layers: [{ model: 'slimeInner', tex: T('slime/slime.png') }, { model: 'slimeOuter', tex: T('slime/slime.png'), transparent: true }], anim: 'slime', kind: 'quad', sized: true },
  LavaSlime: { layers: [{ model: 'magmaCube', tex: T('slime/magmacube.png'), emissive: 0xaa3300, emissiveIntensity: 0.7 }], anim: 'magma', kind: 'quad', sized: true },
  Blaze: { layers: [{ model: 'blaze', tex: T('blaze.png'), emissive: 0xffaa33, emissiveIntensity: 0.9 }], anim: 'blaze', kind: 'quad', hover: 0.9 },
  Ghast: { layers: [{ model: 'ghast', tex: T('ghast/ghast.png') }], anim: 'ghast', kind: 'quad', scale: 4.5, hover: 2.0 },
  Witch: { layers: [{ model: 'witch', tex: T('witch.png') }], anim: 'villager', kind: 'biped', scale: 0.9375 },
  Villager: { layers: [{ model: 'villager', tex: T('villager/villager.png') }], anim: 'villager', kind: 'biped' },
  Pig: { layers: [{ model: 'pig', tex: T('pig/pig.png') }], anim: 'quad', kind: 'quad' },
  Cow: { layers: [{ model: 'cow', tex: T('cow/cow.png') }], anim: 'quad', kind: 'quad' },
  Chicken: { layers: [{ model: 'chicken', tex: T('chicken.png') }], anim: 'chicken', kind: 'quad' },
  Sheep: { layers: [{ model: 'sheepBody', tex: T('sheep/sheep.png') }, { model: 'sheepWool', tex: T('sheep/sheep_fur.png'), fleece: true }], anim: 'quad', kind: 'quad' },
  Wolf: { layers: [{ model: 'wolf', tex: T('wolf/wolf.png') }], anim: 'wolf', kind: 'quad' },
  Ozelot: { layers: [{ model: 'ocelot', tex: T('cat/ocelot.png') }], anim: 'ocelot', kind: 'quad' },
  Horse: { layers: [{ model: 'horse', tex: T('horse/horse_white.png'), skip: ['muleLeftEar', 'muleRightEar', 'muleLeftChest', 'muleRightChest', 'horseSaddleBottom', 'horseSaddleFront', 'horseSaddleBack', 'horseLeftSaddleMetal', 'horseLeftSaddleRope', 'horseRightSaddleMetal', 'horseRightSaddleRope', 'horseLeftFaceMetal', 'horseRightFaceMetal', 'horseLeftRein', 'horseRightRein', 'horseFaceRopes'] }], anim: 'horse', kind: 'quad' },
  Bat: { layers: [{ model: 'bat', tex: T('bat.png') }], anim: 'bat', kind: 'quad', scale: 0.35, hover: 0.9 },
  Squid: { layers: [{ model: 'squid', tex: T('squid.png') }], anim: 'squid', kind: 'quad', hover: 0.6 },
  IronGolem: { layers: [{ model: 'ironGolem', tex: T('iron_golem.png') }], anim: 'golem', kind: 'biped' },
  SnowMan: { layers: [{ model: 'snowMan', tex: T('snowman.png') }], anim: 'snowman', kind: 'biped' },
  WitherBoss: { layers: [{ model: 'wither', tex: T('wither/wither.png') }], anim: 'wither', kind: 'quad', scale: 2, hover: 0.3 },
  EnderDragon: { layers: [{ model: 'dragon', tex: T('enderdragon/dragon.png') }, { model: 'dragon', tex: T('enderdragon/dragon_eyes.png'), additive: true }], anim: 'none', kind: 'quad', scale: 0.5, hover: 1.5 },
  MagmaCubeSmall: null,
};
delete MOB_SPECS.MagmaCubeSmall;

// OreSpawn mobs: model class, texture (assets/orespawn/<file>), target height in blocks, and how
// the Techne export is oriented (flipZ turns a model that faces +z). Heights are the site's own.
const OS = (model, file, h, o = {}) => ({ os: model, tex: 'orespawn/' + file, h, ...o });
export const OS_SPECS = {
  Mantis: OS('Mantis', 'Mantistexture.png', 2.0),
  Bee: OS('Bee', 'Beetexture.png', 0.9, { hover: 0.8, flap: true }),
  Brutalfly: OS('Brutalfly', 'Brutalflytexture.png', 1.6, { hover: 0.8, flap: true, lift: 0.3, tilt: 0.9 }),
  CaterKiller: OS('CaterKiller', 'CaterKillertexture.png', 1.4),
  Cephadrome: OS('Cephadrome', 'Cephadrome.png', 1.5, { hover: 0.8, flap: true }),
  CloudShark: OS('CloudShark', 'CloudShark.png', 2.0, { hover: 0.8, flap: true }),
  Coin: OS('Coin', 'Cointexture.png', 0.4, { spin: true }),
  Dragon: OS('Dragon', 'Dragon.png', 3.0, { hover: 0.8, flap: true }),
  EasterBunny: OS('EasterBunny', 'EasterBunnytexture.png', 1.6),
  Hammerhead: OS('Hammerhead', 'Hammerheadtexture.png', 2.2),
  Robot1: OS('Robot1', 'Robot1.png', 2.6),
  Robot2: OS('Robot2', 'Robot2.png', 2.6, { glow: 0x30343f }),
  Robot3: OS('Robot3', 'Robot3.png', 2.6, { glow: 0x30343f }),
  Robot4: OS('Robot4', 'Robot4.png', 2.6, { glow: 0x30343f }),
  Robot5: OS('Robot5', 'Robot5texture.png', 2.0),
  Ant: OS('Ant', 'ant.png', 0.9),
  RedAnt: OS('Ant', 'red_ant.png', 0.9),
  RainbowAnt: OS('Ant', 'rainbow_ant.png', 0.9),
  UnstableAnt: OS('Ant', 'unstableant.png', 0.9),
  Termite: OS('Ant', 'termite.png', 0.9),
  Rotator: OS('Rotator', 'Rotatortexture.png', 1.6, { hover: 0.8, spin: true, glow: 0x30343f }),
  LargeWorm: OS('WormLarge', 'WormLargetexture.png', 1.2),
  Mobzilla: OS('Godzilla', 'Godzillatexture.png', 4),
  Mothra: OS('Butterfly', 'lunamoth.png', 2.4, { hover: 0.8, flap: true, lift: 0.3, tilt: 0.9, mothra: true }),
  GoldenAppleCow: { layers: [{ model: 'cow', tex: 'orespawn/gold_cow.png' }], anim: 'quad', kind: 'quad' },
  RedAppleCow: { layers: [{ model: 'cow', tex: 'orespawn/red_cow.png' }], anim: 'quad', kind: 'quad' },
  CrystalCow: { layers: [{ model: 'cow', tex: 'orespawn/crystal_cow.png' }], anim: 'quad', kind: 'quad' },
};

// Loose ids (entity names, the table's titles) to a spec key.
const ALIAS = {
  zombie: 'Zombie', giant: 'Giant', giantzombie: 'Giant', pigzombie: 'PigZombie', zombiepigman: 'PigZombie', zombievillager: 'ZombieVillager',
  skeleton: 'Skeleton', witherskeleton: 'WitherSkeleton', steve: 'Steve', creeper: 'Creeper', spider: 'Spider', cavespider: 'CaveSpider',
  enderman: 'Enderman', silverfish: 'Silverfish', slime: 'Slime', lavaslime: 'LavaSlime', magmacube: 'LavaSlime', blaze: 'Blaze',
  ghast: 'Ghast', witch: 'Witch', villager: 'Villager', pig: 'Pig', cow: 'Cow', chicken: 'Chicken', sheep: 'Sheep', wolf: 'Wolf',
  ozelot: 'Ozelot', ocelot: 'Ozelot', cat: 'Ozelot', horse: 'Horse', entityhorse: 'Horse', bat: 'Bat', squid: 'Squid',
  irongolem: 'IronGolem', villagergolem: 'IronGolem', snowman: 'SnowMan', snowgolem: 'SnowMan', witherboss: 'WitherBoss', wither: 'WitherBoss',
  enderdragon: 'EnderDragon', mantis: 'Mantis', bee: 'Bee', brutalfly: 'Brutalfly', caterkiller: 'CaterKiller', cephadrome: 'Cephadrome',
  cloudshark: 'CloudShark', coin: 'Coin', dragon: 'Dragon', easterbunny: 'EasterBunny', bunny: 'EasterBunny', hammerhead: 'Hammerhead',
  robopounder: 'Robot1', robot1: 'Robot1', robogunner: 'Robot2', robot2: 'Robot2', robowarrior: 'Robot3', robot3: 'Robot3', robot4: 'Robot4', robot5: 'Robot5',
  ant: 'Ant', brownant: 'Ant', redant: 'RedAnt', rainbowant: 'RainbowAnt', unstableant: 'UnstableAnt', termite: 'Termite',
  rotator: 'Rotator', largeworm: 'LargeWorm', wormlarge: 'LargeWorm', mobzilla: 'Mobzilla', godzilla: 'Mobzilla', mothra: 'Mothra',
  enchantedgoldenapplecow: 'GoldenAppleCow', goldenapplecow: 'GoldenAppleCow', redapplecow: 'RedAppleCow', goldencow: 'GoldenAppleCow', goldcow: 'GoldenAppleCow', redcow: 'RedAppleCow', crystalcow: 'CrystalCow',
};
export function mobKey(id) {
  const k = String(id).toLowerCase().replace(/^entity/, (m, o, s) => (s === 'entityhorse' ? m : '')).replace(/[^a-z0-9]/g, '');
  if (MOB_SPECS[id] || OS_SPECS[id]) return String(id);
  return ALIAS[k] || ALIAS[k.replace(/^entity/, '')] || null;
}
export function mobNames() { return Object.keys(MOB_SPECS).concat(Object.keys(OS_SPECS)); }

// ===================================================================== animations
// Each animation gets the primary layer's parts and the frame: ls (limb swing), lsa (limb swing
// amount), age (ticks), hy/hp (head yaw and pitch in radians), o (the caller's options).
const PI = Math.PI;
const cos = Math.cos, sin = Math.sin;
const rot = (g, x, y, z) => g && setRot(g, x, y, z);
const addRot = (g, dx = 0, dy = 0, dz = 0) => {
  if (!g) return;
  const r = g.userData.rest.rot;
  // current mc angles from the three rotation
  setRot(g, -g.rotation.x + dx, -g.rotation.y + dy, g.rotation.z + dz);
};
const mcx = (g) => -g.rotation.x, mcy = (g) => -g.rotation.y, mcz = (g) => g.rotation.z;

function bipedBase(P, c) {
  const { head, headwear, rightArm, leftArm, rightLeg, leftLeg } = BP(P);
  rot(head, c.hp, c.hy); rot(headwear, c.hp, c.hy);
  if (c.o.still) { rot(rightArm, 0, 0, 0); rot(leftArm, 0, 0, 0); } else {
    rot(rightArm, cos(c.ls * 0.6662 + PI) * c.lsa, 0, 0);
    rot(leftArm, cos(c.ls * 0.6662) * c.lsa, 0, 0);
  }
  if (rightArm) { rightArm.userData.raise = c.o.armRaise || 0; if (c.o.armRaise) { addRot(rightArm, -c.o.armRaise); addRot(leftArm, -c.o.armRaise); } }
  rot(rightLeg, cos(c.ls * 0.6662) * 1.4 * c.lsa, 0, 0);
  rot(leftLeg, cos(c.ls * 0.6662 + PI) * 1.4 * c.lsa, 0, 0);
  if (c.o.still) { rot(rightLeg, 0, 0, 0); rot(leftLeg, 0, 0, 0); }
  // idle sway
  if (rightArm) {
    addRot(rightArm, sin(c.age * 0.067) * 0.05, 0, cos(c.age * 0.09) * 0.05 + 0.05);
    addRot(leftArm, -sin(c.age * 0.067) * 0.05, 0, -(cos(c.age * 0.09) * 0.05 + 0.05));
  }
}
const BP = (P) => ({ head: P.bipedHead, headwear: P.bipedHeadwear, body: P.bipedBody, rightArm: P.bipedRightArm, leftArm: P.bipedLeftArm, rightLeg: P.bipedRightLeg, leftLeg: P.bipedLeftLeg });
const quadLegs = (P, c, k = 1.4) => {
  rot(P.leg1, cos(c.ls * 0.6662) * k * c.lsa); rot(P.leg2, cos(c.ls * 0.6662 + PI) * k * c.lsa);
  rot(P.leg3, cos(c.ls * 0.6662 + PI) * k * c.lsa); rot(P.leg4, cos(c.ls * 0.6662) * k * c.lsa);
};

const ANIMS = {
  none() {},
  biped(P, c) { bipedBase(P, c); },
  zombie(P, c) {
    const { rightArm, leftArm } = BP(P);
    bipedBase(P, c);
    const raise = c.o.armRaise != null ? 0 : 1;
    if (!raise) return;
    const a = c.age;
    rot(rightArm, -PI / 2 + sin(a * 0.067) * 0.05, -0.1, cos(a * 0.09) * 0.05 + 0.05);
    rot(leftArm, -PI / 2 - sin(a * 0.067) * 0.05, 0.1, -(cos(a * 0.09) * 0.05 + 0.05));
  },
  creeper(P, c) {
    rot(P.head, c.hp, c.hy);
    quadLegs(P, c);
  },
  spider(P, c) {
    rot(P.spiderHead, c.hp, c.hy);
    const f6 = PI / 4, f8 = 0.3926991;
    const L = [P.spiderLeg1, P.spiderLeg2, P.spiderLeg3, P.spiderLeg4, P.spiderLeg5, P.spiderLeg6, P.spiderLeg7, P.spiderLeg8];
    const z0 = [-f6, f6, -f6 * 0.74, f6 * 0.74, -f6 * 0.74, f6 * 0.74, -f6, f6];
    const y0 = [f8 * 2, -f8 * 2, f8, -f8, -f8, f8, -f8 * 2, f8 * 2];
    const ph = [0, PI, PI / 2, PI * 3 / 2];
    const ls = c.ls, a = c.lsa;
    for (let i = 0; i < 4; i++) {
      const fy = -(cos(ls * 0.6662 * 2 + ph[i]) * 0.4) * a;
      const fz = Math.abs(sin(ls * 0.6662 + ph[i]) * 0.4) * a;
      const sgn = (j) => (j % 2 ? -1 : 1);
      rot(L[i * 2], 0, y0[i * 2] + fy, z0[i * 2] + fz);
      rot(L[i * 2 + 1], 0, y0[i * 2 + 1] - fy, z0[i * 2 + 1] - fz);
    }
  },
  enderman(P, c) {
    bipedBase(P, c);
    const { head, headwear, body, rightArm, leftArm, rightLeg, leftLeg } = BP(P);
    const f6 = -14;
    rot(body, 0); setPivot(body, null, f6, 0);
    const cl = (g) => { const v = Math.max(-0.4, Math.min(0.4, mcx(g) * 0.5)); rot(g, v); };
    [rightArm, leftArm, rightLeg, leftLeg].forEach(cl);
    if (c.o.carrying) { rot(rightArm, -0.5, 0, 0.05); rot(leftArm, -0.5, 0, -0.05); }
    setPivot(rightArm, null, null, 0); setPivot(leftArm, null, null, 0);
    setPivot(rightLeg, null, 9 + f6, 0); setPivot(leftLeg, null, 9 + f6, 0);
    setPivot(head, null, f6 + 1 - (c.o.screaming ? 5 : 0), 0);
    setPivot(headwear, null, f6 + 1 - (c.o.screaming ? 5 : 0), 0);
    rot(headwear, mcx(head), mcy(head), mcz(head));
    if (c.o.enderJitter) c.rig.position.x += sin(c.t * 60) * 0.01 * c.o.enderJitter;
  },
  silverfish(P, c) {
    const B = [0, 1, 2, 3, 4, 5, 6].map((i) => P['silverfishBodyParts' + i]);
    const Wg = [0, 1, 2].map((i) => P['silverfishWings' + i]);
    B.forEach((g, i) => {
      const a = c.age * 0.9 * 0.3 + i * 0.15 * PI;
      rot(g, null, cos(a) * PI * 0.05 * (1 + Math.abs(i - 2)));
      setPivot(g, sin(a) * PI * 0.2 * Math.abs(i - 2), null, null);
    });
    rot(Wg[0], null, mcy(B[2])); rot(Wg[1], null, mcy(B[4])); rot(Wg[2], null, mcy(B[1]));
    setPivot(Wg[1], g0(B[4]), null, null); setPivot(Wg[2], g0(B[1]), null, null);
    function g0(g) { return -g.position.x * 16; }
  },
  slime(P, c) { /* squish is applied to the rig */ },
  magma(P, c) {
    const f = c.squish || 0;
    for (let i = 0; i < 8; i++) setPivot(P['field_78109_a' + i], null, -(4 - i) * f * 1.7 + P['field_78109_a' + i].userData.rest.pivot[1], null);
  },
  blaze(P, c) {
    let f6 = c.age * PI * -0.1;
    const S = (i) => P['blazeSticks' + i];
    const place = (g, y, x, z) => setPivot(g, x, y, z);
    for (let i = 0; i < 4; i++) { place(S(i), -2 + cos((i * 2 + c.age) * 0.25), cos(f6) * 9, sin(f6) * 9); f6 += 1; }
    f6 = PI / 4 + c.age * PI * 0.03;
    for (let i = 4; i < 8; i++) { place(S(i), 2 + cos((i * 2 + c.age) * 0.25), cos(f6) * 7, sin(f6) * 7); f6 += 1; }
    f6 = 0.47123894 + c.age * PI * -0.05;
    for (let i = 8; i < 12; i++) { place(S(i), 11 + cos((i * 1.5 + c.age) * 0.5), cos(f6) * 5, sin(f6) * 5); f6 += 1; }
    rot(P.blazeHead, c.hp, c.hy);
  },
  ghast(P, c) {
    for (let i = 0; i < 9; i++) rot(P['tentacles' + i], 0.2 * sin(c.age * 0.3 + i) + 0.4);
  },
  villager(P, c) {
    rot(P.villagerHead, c.hp, c.hy);
    rot(P.villagerArms, -0.75); setPivot(P.villagerArms, null, 3, -1);
    rot(P.rightVillagerLeg, cos(c.ls * 0.6662) * 1.4 * c.lsa * 0.5, 0);
    rot(P.leftVillagerLeg, cos(c.ls * 0.6662 + PI) * 1.4 * c.lsa * 0.5, 0);
    const nose = P.villagerNose;
    if (nose) rot(nose, sin(c.age * 0.05) * 4.5 * PI / 180, 0, cos(c.age * 0.05) * 2.5 * PI / 180);
  },
  quad(P, c) {
    rot(P.head, c.hp, c.hy);
    rot(P.body, PI / 2);
    quadLegs(P, c);
  },
  chicken(P, c) {
    rot(P.head, c.hp, c.hy); rot(P.bill, c.hp, c.hy); rot(P.chin, c.hp, c.hy);
    rot(P.body, PI / 2);
    rot(P.rightLeg, cos(c.ls * 0.6662) * 1.4 * c.lsa); rot(P.leftLeg, cos(c.ls * 0.6662 + PI) * 1.4 * c.lsa);
    const w = c.o.flap != null ? c.o.flap : sin(c.age * 0.12) * 0.04;
    rot(P.rightWing, null, null, w); rot(P.leftWing, null, null, -w);
  },
  wolf(P, c) {
    rot(P.wolfTail, c.o.sit ? null : 0.9 + sin(c.age * 0.1) * 0.05, cos(c.ls * 0.6662) * 1.4 * c.lsa);
    setPivot(P.wolfBody, 0, 14, 2); rot(P.wolfBody, PI / 2);
    setPivot(P.wolfMane, -1, 14, -3); rot(P.wolfMane, PI / 2);
    setPivot(P.wolfTail, -1, 12, 8);
    setPivot(P.wolfLeg1, -2.5, 16, 7); setPivot(P.wolfLeg2, 0.5, 16, 7); setPivot(P.wolfLeg3, -2.5, 16, -4); setPivot(P.wolfLeg4, 0.5, 16, -4);
    rot(P.wolfLeg1, cos(c.ls * 0.6662) * 1.4 * c.lsa); rot(P.wolfLeg2, cos(c.ls * 0.6662 + PI) * 1.4 * c.lsa);
    rot(P.wolfLeg3, cos(c.ls * 0.6662 + PI) * 1.4 * c.lsa); rot(P.wolfLeg4, cos(c.ls * 0.6662) * 1.4 * c.lsa);
    rot(P.wolfHeadMain, c.hp, c.hy, 0);
  },
  ocelot(P, c) {
    rot(P.ocelotHead, c.hp, c.hy);
    setPivot(P.ocelotBody, 0, 12, -10); rot(P.ocelotBody, PI / 2);
    setPivot(P.ocelotHead, 0, 15, -9);
    setPivot(P.ocelotTail, 0, 15, 8); setPivot(P.ocelotTail2, 0, 20, 14);
    for (const n of ['ocelotFrontLeftLeg', 'ocelotFrontRightLeg']) setPivot(P[n], null, 13.8, -5);
    for (const n of ['ocelotBackLeftLeg', 'ocelotBackRightLeg']) setPivot(P[n], null, 18, 5);
    rot(P.ocelotTail, 0.9);
    rot(P.ocelotBackLeftLeg, cos(c.ls * 0.6662) * c.lsa); rot(P.ocelotBackRightLeg, cos(c.ls * 0.6662 + PI) * c.lsa);
    rot(P.ocelotFrontLeftLeg, cos(c.ls * 0.6662 + PI) * c.lsa); rot(P.ocelotFrontRightLeg, cos(c.ls * 0.6662) * c.lsa);
    rot(P.ocelotTail2, 1.7278761 + 0.47123894 * cos(c.ls) * c.lsa);
  },
  horse(P, c) {
    // ModelHorse sets its walking pose in setLivingAnimations from a gait function; this is the
    // plain walk: diagonal pairs swing, head nods, tail sways.
    const sw = cos(c.ls * 0.6662) * 0.9 * c.lsa, sw2 = cos(c.ls * 0.6662 + PI) * 0.9 * c.lsa;
    rot(P.frontLeftLeg, sw2); rot(P.frontRightLeg, sw); rot(P.backLeftLeg, sw); rot(P.backRightLeg, sw2);
    for (const [s, l] of [['frontLeftShin', sw2], ['frontRightShin', sw], ['backLeftShin', sw], ['backRightShin', sw2]]) rot(P[s], l);
    for (const [s, l] of [['frontLeftHoof', sw2], ['frontRightHoof', sw], ['backLeftHoof', sw], ['backRightHoof', sw2]]) rot(P[s], l);
    rot(P.tailBase, 0.5235988 + 0.1 * sin(c.age * 0.12));
  },
  bat(P, c) {
    const a = c.age;
    rot(P.batHead, c.hp, c.hy, 0);
    rot(P.batBody, PI / 4 + cos(a * 0.1) * 0.15, 0);
    const wy = cos(a * 1.3 * 0.5) * PI * 0.25;
    rot(P.batRightWing, null, wy); rot(P.batLeftWing, null, -wy);
    rot(P.batOuterRightWing, null, wy * 0.5); rot(P.batOuterLeftWing, null, -wy * 0.5);
  },
  squid(P, c) {
    const ang = 0.5 + 0.5 * sin(c.age * 0.12);
    for (let i = 0; i < 8; i++) rot(P['squidTentacles' + i], ang);
  },
  golem(P, c) {
    const tri = (a, b) => (Math.abs(a % b - b * 0.5) - b * 0.25) / (b * 0.25);
    rot(P.ironGolemHead, c.hp, c.hy);
    rot(P.ironGolemLeftLeg, -1.5 * tri(c.ls, 13) * c.lsa, 0); rot(P.ironGolemRightLeg, 1.5 * tri(c.ls, 13) * c.lsa, 0);
    rot(P.ironGolemRightArm, (-0.2 + 1.5 * tri(c.ls, 13)) * c.lsa); rot(P.ironGolemLeftArm, (-0.2 - 1.5 * tri(c.ls, 13)) * c.lsa);
  },
  snowman(P, c) {
    rot(P.head, c.hp, c.hy);
    const by = c.hy * 0.25;
    rot(P.body, null, by);
    rot(P.rightHand, null, by, 1); rot(P.leftHand, null, PI + by, -1);
    setPivot(P.rightHand, cos(by) * 5, null, -sin(by) * 5); setPivot(P.leftHand, -cos(by) * 5, null, sin(by) * 5);
  },
  wither(P, c) {
    const f6 = cos(c.age * 0.1);
    const A = [0, 1, 2].map((i) => P['field_82905_a' + i]);
    const H = [0, 1, 2].map((i) => P['field_82904_b' + i]);
    rot(A[1], (0.065 + 0.05 * f6) * PI);
    const r = mcx(A[1]);
    setPivot(A[2], -2, 6.9 + cos(r) * 10, -0.5 + sin(r) * 10);
    rot(A[2], (0.265 + 0.1 * f6) * PI);
    rot(H[0], c.hp, c.hy);
    rot(H[1], 0, 0.3 * sin(c.age * 0.05)); rot(H[2], 0, -0.3 * sin(c.age * 0.05));
  },
};
// models whose parts are named differently from the table above (generated field names)
function aliasParts(P, key) {
  const A = (a, b) => { if (P[b] && !P[a]) P[a] = P[b]; };
  if (P.bipedHead) {
    A('head', 'bipedHead'); A('headwear', 'bipedHeadwear'); A('body', 'bipedBody'); A('rightArm', 'bipedRightArm'); A('leftArm', 'bipedLeftArm');
    A('rightLeg', 'bipedRightLeg'); A('leftLeg', 'bipedLeftLeg'); A('rArm', 'bipedRightArm'); A('lArm', 'bipedLeftArm'); A('rLeg', 'bipedRightLeg'); A('lLeg', 'bipedLeftLeg');
  }
  if (P.villagerHead) { A('head', 'villagerHead'); A('body', 'villagerBody'); A('arms', 'villagerArms'); A('rightLeg', 'rightVillagerLeg'); A('leftLeg', 'leftVillagerLeg'); A('nose', 'villagerNose'); }
  if (P.spiderHead) { A('head', 'spiderHead'); A('body', 'spiderBody'); for (let i = 1; i <= 8; i++) A('leg' + i, 'spiderLeg' + i); }
  if (P.ironGolemHead) { A('head', 'ironGolemHead'); A('body', 'ironGolemBody'); A('rightArm', 'ironGolemRightArm'); A('leftArm', 'ironGolemLeftArm'); A('rightLeg', 'ironGolemRightLeg'); A('leftLeg', 'ironGolemLeftLeg'); }
  if (P.wolfHeadMain) { A('head', 'wolfHeadMain'); A('body', 'wolfBody'); for (let i = 1; i <= 4; i++) A('leg' + i, 'wolfLeg' + i); A('tail', 'wolfTail'); }
  if (P.ocelotHead) { A('head', 'ocelotHead'); A('body', 'ocelotBody'); }
  if (P.batHead) { A('head', 'batHead'); A('body', 'batBody'); }
  if (P.blazeHead) A('head', 'blazeHead');
  if (P.squidBody) A('body', 'squidBody');
  if (P.silverfishBodyParts0) A('body', 'silverfishBodyParts2');
  if (P.slimeBodies) A('body', 'slimeBodies');
  if (P.field_82904_b0) { A('head', 'field_82904_b0'); }
  if (P.frontLeftLeg) { A('leg1', 'backLeftLeg'); A('leg2', 'backRightLeg'); A('leg3', 'frontLeftLeg'); A('leg4', 'frontRightLeg'); }
}

// ===================================================================== makeMob
const SOUND_KEYS = ['say', 'hurt', 'death', 'step'];
const loadTex = (p) => tex(p);

function buildVanilla(key, spec, opts) {
  const group = new THREE.Group();             // outer: callers place and scale this
  const rig = new THREE.Group();               // inner: the animation moves and squishes this
  group.add(rig);
  const layers = spec.layers.map((L, i) => {
    const data = VANILLA_MODELS[L.model];
    const texture = loadTex(L.tex);
    const color = L.fleece ? FLEECE[opts.dye ?? 0] : (opts.color ?? 0xffffff);
    const r = buildRig(data, texture, { ...L, color });
    rig.add(r.root);
    return r;
  });
  const primary = layers[0];
  aliasParts(primary.parts, key);
  return { group, rig, layers, primary };
}

function buildOreSpawn(key, spec, opts) {
  const group = new THREE.Group();
  const rig = new THREE.Group();
  group.add(rig);
  const data = OS_MODELS[spec.os];
  const r = buildRig(data, loadTex(spec.tex), { color: opts.color ?? 0xffffff, emissive: spec.glow, emissiveIntensity: 1 });
  // fit: ground the model and scale it to its target height
  rig.add(r.root);
  rig.updateMatrixWorld(true);
  const box = new THREE.Box3().setFromObject(r.root);
  const bw = box.max.x - box.min.x, bd = box.max.z - box.min.z;
  const hgt = Math.max(0.01, box.max.y - box.min.y, 0.4 * Math.max(bw, bd));
  const k = spec.h / hgt;
  r.root.scale.setScalar(k);
  r.root.position.y = -box.min.y * k;
  r.root.position.x = -((box.min.x + box.max.x) / 2) * k;
  r.root.position.z = -((box.min.z + box.max.z) / 2) * k;
  r.fit = k;
  return { group, rig, layers: [r], primary: r };
}

function sizeOf(root) {
  root.updateMatrixWorld(true);
  const b = new THREE.Box3().setFromObject(root);
  return { h: b.max.y - b.min.y, min: b.min.y, box: b };
}

const OS_FLAP = /wing|fan|membrane/i;
function osAnim(spec, P, c) {
  const names = Object.keys(P);
  names.forEach((n, i) => {
    const g = P[n];
    if (!g || !g.userData.rest) return;
    const left = /left/i.test(n) || (/^l[a-z]*(wing|leg|arm|foot|fin)/i.test(n) && !/^leg/i.test(n));
    const sgn = left ? 1 : -1;
    if (OS_FLAP.test(n) && !/tail/i.test(n)) {
      const base = spec.lift || 0;
      // the wings of Brutalfly and Mothra are flat plates: lift them into a V so they read in 3/4
      if (spec.flap) addRot(g, 0, 0, sgn * (base + sin(c.t * 14) * 0.45));
      else addRot(g, 0, 0, sgn * sin(c.t * 2) * 0.05);
    } else if (/leg|foot|toe|thigh/i.test(n) && !/spike/i.test(n)) addRot(g, sin(c.t * 5 * (c.o.walk ?? 1) + (left ? 0 : PI)) * 0.3 * (c.o.walk ?? 1));
    else if (/arm|claw|hand|jaw|mouth|pincer/i.test(n)) addRot(g, sin(c.t * 2.2 + i) * 0.08);
    else if (/tail|neck|seg|head\d|worm|abdomen/i.test(n)) addRot(g, 0, sin(c.t * 2.5 + i * 0.45) * 0.1, 0);
  });
}

export function makeMob(id, opts = {}) {
  let key = mobKey(id);
  const spec = key ? (MOB_SPECS[key] || OS_SPECS[key]) : null;
  let built, kind = 'quad';
  const unknown = !spec;
  if (!spec) {
    key = 'Zombie';
  }
  const sp = spec || MOB_SPECS.Zombie;
  built = sp.os ? buildOreSpawn(key, sp, opts) : buildVanilla(key, sp, opts);
  kind = sp.kind || (sp.os ? 'os' : 'quad');
  const { group, rig, layers, primary } = built;
  const size = opts.size ?? (sp.sized ? (key === 'Slime' ? 2 : 2) : 1);
  const baseScale = sp.scale || 1;
  rig.scale.setScalar(baseScale);
  if (opts.colorHex) group.traverse((o) => { if (o.isMesh && o.material && o.material.color) o.material.color.setHex(opts.colorHex); });
  const mats = layers.map((l) => l.mat);
  const out = { root: group, parts: primary.parts, mat: primary.mat, mats, kind, key, unknown, float: 0, hover: sp.hover || 0, flying: !!(sp.hover || sp.flap) };
  // height: measured at rest, then fixed
  resetRig(primary.parts);
  if (sp.anim === 'slime' || sp.sized) rig.scale.set(baseScale * size, baseScale * size, baseScale * size);
  const hb = sizeOf(rig);
  out.height = Math.max(0.1, sp.os ? sp.h : hb.h - Math.min(0, hb.min) * 0);
  out.baseY = rig.position.y;
  if (opts.scale) group.scale.multiplyScalar(opts.scale);

  const animFn = ANIMS[sp.anim] || null;
  const P = primary.parts;
  out.anim = function (t, dt, o = {}) {
    const age = t * 20;
    const walk = o.walk ?? 1;
    const ctx = {
      t, age, o, rig,
      ls: t * 7 * (walk > 0 ? 1 : 0), lsa: 0.45 * walk,
      hy: o.lookAt ?? 0, hp: o.lookPitch ?? 0,
      squish: 0,
    };
    if (sp.os) {
      resetRig(P);
      osAnim(sp, P, ctx);
      if (sp.spin) rig.rotation.y = t * 3;
      // a resting moth shows its wings to the viewer: pitch the whole body so the plates face the camera
      if (sp.tilt) rig.rotation.x = -sp.tilt;
      rig.position.y = Math.sin(t * (sp.flap ? 4 : 1.6)) * (sp.flap ? 0.1 : 0.0);
      return;
    }
    resetRig(P);
    if (sp.anim === 'slime' || sp.anim === 'magma') {
      const sq = Math.sin(t * 4) * 0.22;
      ctx.squish = sq;
      const f2 = sq / (size * 0.5 + 1);
      const f3 = 1 / (f2 + 1);
      rig.scale.set(f3 * size * baseScale, (1 / f3) * size * baseScale, f3 * size * baseScale);
    }
    if (animFn) animFn(P, ctx);
    // copy the primary's pose onto the other layers
    for (let i = 1; i < layers.length; i++) {
      const Q = layers[i].parts;
      for (const n in Q) {
        const s = P[n];
        if (!s) continue;
        Q[n].position.copy(s.position);
        Q[n].rotation.copy(s.rotation);
      }
    }
    // body-wide effects
    let sx = 1, sy = 1;
    if (key === 'Creeper' && o.hiss) {
      let f = Math.max(0, Math.min(1, o.hiss));
      const f2 = 1 + Math.sin(f * 100) * f * 0.01; f = f * f; f *= f;
      sx = (1 + f * 0.4) * f2; sy = (1 + f * 0.1) / f2;
      rig.scale.set(sx * baseScale, sy * baseScale, sx * baseScale);
    } else if (!sp.sized) rig.scale.setScalar(baseScale);
    // the caller places the mob (and lifts the flyers: out.hover is the height the pack uses); the
    // rig only bobs a little inside its own group
    rig.position.y = sp.hover ? Math.sin(t * 1.4) * 0.1 * baseScale : 0;
  };
  out.mobSounds = mobSounds(id, size);
  return out;
}

// The animation for a rig made by buildBiped (Steve): swinging limbs and a small bob, as before.
export function makeAnim(m) {
  if (m.anim) return m.anim;
  const { root, parts } = m;
  return function (t, dt, o = {}) {
    const sw = (o.walk ?? 1) * Math.sin(t * 5.2);
    if (parts.rLeg) { parts.rLeg.rotation.x = sw * 0.9; parts.lLeg.rotation.x = -sw * 0.9; }
    if (parts.rArm && !o.still) { parts.rArm.rotation.x = -sw * 0.7 + (o.armRaise || 0); parts.lArm.rotation.x = sw * 0.7 + (o.armRaise || 0); }
    if (parts.head && o.lookAt) parts.head.rotation.y = o.lookAt;
    if (o.enderJitter) root.position.x += Math.sin(t * 60) * 0.01 * o.enderJitter;
    root.position.y = Math.abs(Math.sin(t * 5.2)) * 0.02;
  };
}
export function biped(opts) { return buildBiped(opts); }
export function mobFromSpec(id, opts) { return makeMob(id, opts); }
export { TEXP, P };

// ===================================================================== sounds
// 1.7.10 event names: the entity classes' getLivingSound / getHurtSound / getDeathSound / step sounds
// (read from the decompiled sources), and OreSpawn's own sounds.json names for its mobs.
const S = (say, hurt, death, step, extra = {}) => ({ say, hurt, death, step, ...extra });
const SND = {
  Zombie: S('mob.zombie.say', 'mob.zombie.hurt', 'mob.zombie.death', 'mob.zombie.step'),
  Giant: S('mob.zombie.say', 'mob.zombie.hurt', 'mob.zombie.death', 'mob.zombie.step'),
  ZombieVillager: S('mob.zombie.say', 'mob.zombie.hurt', 'mob.zombie.death', 'mob.zombie.step'),
  PigZombie: S('mob.zombiepig.zpig', 'mob.zombiepig.zpighurt', 'mob.zombiepig.zpigdeath', 'mob.zombie.step', { angry: 'mob.zombiepig.zpigangry' }),
  Skeleton: S('mob.skeleton.say', 'mob.skeleton.hurt', 'mob.skeleton.death', 'mob.skeleton.step', { shoot: 'random.bow' }),
  WitherSkeleton: S('mob.skeleton.say', 'mob.skeleton.hurt', 'mob.skeleton.death', 'mob.skeleton.step'),
  Steve: S(null, 'game.player.hurt', 'game.player.die', 'step.grass'),
  Creeper: S('mob.creeper.say', 'mob.creeper.say', 'mob.creeper.death', 'step.grass', { fuse: 'random.fuse', explode: 'random.explode' }),
  Spider: S('mob.spider.say', 'mob.spider.say', 'mob.spider.death', 'mob.spider.step'),
  CaveSpider: S('mob.spider.say', 'mob.spider.say', 'mob.spider.death', 'mob.spider.step'),
  Enderman: S('mob.endermen.idle', 'mob.endermen.hit', 'mob.endermen.death', 'step.stone', { scream: 'mob.endermen.scream', portal: 'mob.endermen.portal', stare: 'mob.endermen.stare' }),
  Silverfish: S('mob.silverfish.say', 'mob.silverfish.hit', 'mob.silverfish.kill', 'mob.silverfish.step'),
  Slime: S(null, 'mob.slime.big', 'mob.slime.big', 'mob.slime.big', { small: 'mob.slime.small' }),
  LavaSlime: S(null, 'mob.magmacube.big', 'mob.magmacube.big', 'mob.magmacube.big', { small: 'mob.magmacube.small' }),
  Blaze: S('mob.blaze.breathe', 'mob.blaze.hit', 'mob.blaze.death', null, { fire: 'mob.ghast.fireball' }),
  Ghast: S('mob.ghast.moan', 'mob.ghast.scream', 'mob.ghast.death', null, { scream: 'mob.ghast.scream', fireball: 'mob.ghast.fireball', charge: 'mob.ghast.charge' }),
  Witch: S('mob.witch.idle', 'mob.witch.hurt', 'mob.witch.death', 'step.grass', { drink: 'random.drink' }),
  Villager: S('mob.villager.idle', 'mob.villager.hit', 'mob.villager.death', 'step.grass', { yes: 'mob.villager.yes', no: 'mob.villager.no', haggle: 'mob.villager.haggle' }),
  Pig: S('mob.pig.say', 'mob.pig.say', 'mob.pig.death', 'mob.pig.step'),
  Cow: S('mob.cow.say', 'mob.cow.hurt', 'mob.cow.hurt', 'mob.cow.step'),
  Chicken: S('mob.chicken.say', 'mob.chicken.hurt', 'mob.chicken.hurt', 'mob.chicken.step', { egg: 'mob.chicken.plop' }),
  Sheep: S('mob.sheep.say', 'mob.sheep.say', 'mob.sheep.say', 'mob.sheep.step', { shear: 'mob.sheep.shear' }),
  Wolf: S('mob.wolf.growl', 'mob.wolf.hurt', 'mob.wolf.death', 'mob.wolf.step', { bark: 'mob.wolf.bark', whine: 'mob.wolf.whine', pant: 'mob.wolf.panting', shake: 'mob.wolf.shake' }),
  Ozelot: S('mob.cat.meow', 'mob.cat.hitt', 'mob.cat.hitt', 'step.grass', { purr: 'mob.cat.purr', purreow: 'mob.cat.purreow' }),
  Horse: S('mob.horse.idle', 'mob.horse.hit', 'mob.horse.death', 'mob.horse.gallop', { angry: 'mob.horse.angry', jump: 'mob.horse.jump', land: 'mob.horse.land', breathe: 'mob.horse.breathe' }),
  Bat: S('mob.bat.idle', 'mob.bat.hurt', 'mob.bat.death', null),
  Squid: S(null, 'liquid.splash', 'liquid.splash', null),
  IronGolem: S(null, 'mob.irongolem.hit', 'mob.irongolem.death', 'mob.irongolem.walk', { throw: 'mob.irongolem.throw' }),
  SnowMan: S(null, 'dig.cloth', 'dig.cloth', 'step.snow', { shoot: 'random.bow' }),
  WitherBoss: S('mob.wither.idle', 'mob.wither.hurt', 'mob.wither.death', null, { spawn: 'mob.wither.spawn', shoot: 'mob.wither.shoot' }),
  EnderDragon: S('mob.enderdragon.growl', 'mob.enderdragon.hit', 'mob.enderdragon.end', null, { wings: 'mob.enderdragon.wings' }),
  // OreSpawn (assets/orespawn/sounds.json)
  Mantis: S('orespawn:Beebuzz', 'orespawn:dragonfly_hurt', 'orespawn:alo_death', 'step.grass'),
  Bee: S('orespawn:Beebuzz', 'orespawn:dragonfly_hurt', 'orespawn:alo_death', null),
  Brutalfly: S('orespawn:MothraWings1', 'orespawn:dragonfly_hurt', 'orespawn:dragonfly_death', null),
  CaterKiller: S('orespawn:caterkiller_living', 'orespawn:caterkiller_hit', 'orespawn:caterkiller_death', 'step.gravel'),
  Cephadrome: S('orespawn:roar', 'orespawn:alo_hurt', 'orespawn:alo_death', null),
  CloudShark: S('orespawn:hover', 'orespawn:little_splat', 'orespawn:big_splat', null),
  Coin: S('random.orb', 'random.orb', 'random.pop', null),
  Dragon: S('orespawn:roar', 'orespawn:alo_hurt', 'orespawn:alo_death', null, { wings: 'orespawn:MothraWings2' }),
  EasterBunny: S('orespawn:duck_hurt', 'orespawn:duck_hurt', 'orespawn:duck_hurt', 'step.grass'),
  Hammerhead: S('orespawn:hammerhead_living', 'orespawn:alo_hurt', 'orespawn:hammerhead_death', 'step.stone'),
  Robot1: S('orespawn:kyuubi_living', 'orespawn:scorpion_hit', 'orespawn:robot1_death', 'step.stone'),
  Robot2: S('orespawn:robot_living', 'orespawn:robot_hurt', 'orespawn:robot_death', 'step.stone'),
  Robot3: S('orespawn:robot_living', 'orespawn:robot_hurt', 'orespawn:robot_death', 'step.stone'),
  Robot4: S('orespawn:robot_living', 'orespawn:robot_hurt', 'orespawn:robot_death', 'step.stone'),
  Robot5: S('orespawn:robot_living', 'orespawn:robot_hurt', 'orespawn:robot_death', 'step.stone'),
  Ant: S('orespawn:cricket', 'orespawn:crunch', 'orespawn:crunch', 'step.grass'),
  Rotator: S('orespawn:hover', 'orespawn:glasshit', 'orespawn:glassdead', null),
  LargeWorm: S('orespawn:little_splat', 'orespawn:alo_hurt', 'orespawn:big_splat', null),
  Mobzilla: S('orespawn:godzilla_living', 'orespawn:alo_hurt', 'orespawn:godzilla_death', 'step.stone', { roar: 'orespawn:roar' }),
  Mothra: S('orespawn:MothraWings1', 'orespawn:MothraWings2', 'orespawn:MothraWings3', null),
  GoldenAppleCow: S('mob.cow.say', 'mob.cow.hurt', 'mob.cow.hurt', 'mob.cow.step'),
  RedAppleCow: S('mob.cow.say', 'mob.cow.hurt', 'mob.cow.hurt', 'mob.cow.step'),
  CrystalCow: S('mob.cow.say', 'mob.cow.hurt', 'mob.cow.hurt', 'mob.cow.step'),
};
SND.Termite = SND.RedAnt = SND.RainbowAnt = SND.UnstableAnt = SND.Ant;
export const MOB_SOUNDS = SND;
export function mobSounds(id, size) {
  const key = mobKey(id);
  const s = SND[key] || S(null, null, null, null);
  const out = { ...s };
  if ((key === 'Slime' || key === 'LavaSlime') && size != null && size <= 1) { out.hurt = out.death = out.step = s.small; }
  return out;
}
