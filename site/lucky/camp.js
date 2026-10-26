// Steve's campsite: crafting table, furnace (lit), chest, a netherrack campfire, a fenced wheat patch,
// a lamppost (fence + glowstone), a sign, a seat, and a small quarry of loose blocks to mine.
// Geometry is a handful of small meshes (the terrain stays one merged mesh). Steve's activities
// read the spots and obstacles in L.
import * as THREE from 'three';
import { tex, fireMaterial, glowTexture } from './stage.js';
import { boxGeometry } from './mobs.js';

// World coordinates, ground at y = 0. A cell (cx, cz) fills [cx, cx+1] x [cz, cz+1].
export const L = {
  flat: { x0: -10, x1: 8, z0: -8, z1: 1 },        // stage.js keeps this rectangle level
  table: { cx: 3, cz: -5 }, furnace: { cx: 4, cz: -5 }, chest: { cx: 5, cz: -5 },
  tableStand: { x: 3.5, z: -5.7 }, furnaceStand: { x: 4.5, z: -5.7 }, chestStand: { x: 5.5, z: -5.7 },
  fire: { cx: -5, cz: -1 }, fireCenter: { x: -4.5, z: -0.5 },
  seat: { cx: -5, cz: -3 }, seatApproach: { x: -4.5, z: -3.35 }, seatPos: { x: -4.5, z: -2.5 },
  lamp: { x: 2.5, z: -2.5 },
  sign: { x: 4.7, z: 1.5 },
  wheat: { x0: -9, z0: -5, w: 3, d: 3 },
  pond: { stand: { x: -1.5, z: 3.0 }, bobber: { x: -3.0, z: 3.0 } },
  quarry: [{ cx: -4, cz: -7, kind: 'coal' }, { cx: -3, cz: -7, kind: 'stone' }, { cx: -2, cz: -7, kind: 'iron' }, { cx: -3, cz: -7, y: 1, kind: 'stone' }],
  quarryStandZ: -5.45,
  tree: { cx: -8, cz: 0, stand: { x: -6.4, z: 0.5 } },
  sunset: { x: -2.4, z: -3.2 },
  build: { x: 0.5, z: -3.7, cx: 0, cz: -3 },
  dance: { x: 1.2, z: 4.6 },
  pillar: { x: -0.6, z: 5.6 },
  sneak: { x: 3.2, z: 2.6 },
  // rectangles [x0, z0, x1, z1] Steve walks around
  obstacles: [
    [-1.25, -1.25, 2.25, 2.25],
    [2.85, -5.15, 6.15, -3.85],
    [-5.2, -1.2, -3.8, 0.2],
    [-5.15, -3.15, -3.85, -1.85],
    [2.2, -2.8, 2.8, -2.2],
    [4.3, 1.1, 5.1, 1.9],
    [-4.2, 1.8, -1.85, 4.2],
    [-9.3, -5.3, -5.7, -1.7],
    [-4.3, -7.3, -0.7, -5.9],
    [-8.3, -0.3, -6.9, 1.3],
    [-8.4, -8.4, -5.6, -5.6],
  ],
};

const matCache = new Map();
function M(file, o = {}) {
  const key = file + JSON.stringify(o);
  if (!matCache.has(key)) matCache.set(key, new THREE.MeshLambertMaterial({ map: tex('blocks/' + file), ...o }));
  return matCache.get(key);
}
function cube(mats, x, y, z, s = 1) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(s, s, s), mats);
  m.position.set(x, y, z);
  m.castShadow = true; m.receiveShadow = true;
  return m;
}
// BoxGeometry face order: +x, -x, +y, -y, +z, -z
const faces6 = (px, nx, py, ny, pz, nz) => [px, nx, py, ny, pz, nz];

function chestParts() {
  const mat = new THREE.MeshLambertMaterial({ map: tex('entity/chest.png') });
  const root = new THREE.Group();
  const base = new THREE.Mesh(boxGeometry([-7, -10, -7, 14, 10, 14], [0, 19], 64, 64), mat);
  base.castShadow = base.receiveShadow = true;
  root.add(base);
  const hinge = new THREE.Group();
  hinge.position.set(0, 10 / 16, 7 / 16);
  const lid = new THREE.Mesh(boxGeometry([-7, -5, -14, 14, 5, 14], [0, 0], 64, 64), mat);
  lid.castShadow = true;
  const latch = new THREE.Mesh(boxGeometry([-1, -2, -15, 2, 4, 1], [0, 0], 64, 64), mat);
  hinge.add(lid, latch);
  root.add(hinge);
  return { root, hinge };
}

function signTexture() {
  const c = document.createElement('canvas');
  c.width = 64; c.height = 32;
  const g = c.getContext('2d');
  g.fillStyle = '#a7834a'; g.fillRect(0, 0, 64, 32);
  g.fillStyle = '#8a6a38'; for (let i = 0; i < 64; i += 4) g.fillRect(i, 0, 1, 32);
  g.strokeStyle = '#5a4222'; g.lineWidth = 2; g.strokeRect(1, 1, 62, 30);
  g.fillStyle = '#1b130a'; g.font = 'bold 9px monospace'; g.textAlign = 'center';
  g.fillText('QUEST FORGE', 32, 13); g.font = 'bold 8px monospace'; g.fillText('camp', 32, 25);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace; t.magFilter = THREE.NearestFilter; t.minFilter = THREE.NearestFilter;
  return t;
}

export function buildCamp(S) {
  const group = new THREE.Group();
  S.scene.add(group);
  const out = { group, quarry: [], obstacles: L.obstacles };
  const c = (cx) => cx + 0.5;

  // crafting table, furnace (front lit), chest, all facing the camera side (+z)
  const tp = M('planks_oak.png'), ts = M('crafting_table_side.png'), tf = M('crafting_table_front.png');
  const table = cube(faces6(ts, ts, M('crafting_table_top.png'), tp, tf, tf), c(L.table.cx), 0.5, c(L.table.cz));
  const fs = M('furnace_side.png');
  const frontOn = M('furnace_front_on.png', { emissive: 0xffffff, emissiveIntensity: 0.0 });
  frontOn.emissiveMap = frontOn.map;
  frontOn.emissiveIntensity = 0.85;
  const furnace = cube(faces6(fs, fs, M('furnace_top.png'), M('furnace_top.png'), frontOn, fs), c(L.furnace.cx), 0.5, c(L.furnace.cz));
  const chest = chestParts();
  chest.root.position.set(c(L.chest.cx), 0, c(L.chest.cz));
  chest.root.rotation.y = Math.PI;
  chest.root.scale.setScalar(1);
  group.add(table, furnace, chest.root);
  out.chest = { root: chest.root, hinge: chest.hinge, open: 0, setOpen(k) { out.chest.open = k; chest.hinge.rotation.x = k * 1.15; } };
  out.table = table; out.furnace = furnace;

  // the furnace glow
  const furnaceLight = new THREE.PointLight(0xff9a4a, 0.9, 3.2, 2);
  furnaceLight.position.set(c(L.furnace.cx), 0.5, c(L.furnace.cz) + 0.9);
  group.add(furnaceLight);

  // campfire: netherrack, flames, a seat log
  const nr = M('netherrack.png');
  const fireBlock = cube(nr, L.fireCenter.x, 0.5, L.fireCenter.z);
  group.add(fireBlock);
  const flames = new THREE.Group();
  for (const a of [0, Math.PI / 2]) {
    const q = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), fireMaterial());
    q.position.set(L.fireCenter.x, 1.5, L.fireCenter.z);
    q.rotation.y = a + Math.PI / 4;
    flames.add(q);
  }
  group.add(flames);
  const fireLight = new THREE.PointLight(0xff8a30, 5, 9, 2);
  fireLight.position.set(L.fireCenter.x, 1.7, L.fireCenter.z + 0.4);
  group.add(fireLight);
  const fireGlow = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTexture('rgba(255,160,70,1)'), color: 0xff9040, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, opacity: 0.55 }));
  fireGlow.position.set(L.fireCenter.x, 1.5, L.fireCenter.z);
  fireGlow.scale.set(2.6, 2.6, 1);
  group.add(fireGlow);
  const logT = M('log_oak_top.png'), logS = M('log_oak.png');
  const seat = new THREE.Mesh(new THREE.BoxGeometry(1, 0.5, 1), faces6(logS, logS, logT, logT, logS, logS));
  seat.position.set(c(L.seat.cx), 0.25, c(L.seat.cz));
  seat.castShadow = seat.receiveShadow = true;
  group.add(seat);
  out.fire = { light: fireLight, pos: new THREE.Vector3(L.fireCenter.x, 1.2, L.fireCenter.z) };

  // lamppost: two fence pieces and a glowstone block
  const fence = (x, y, z, h) => { const m = new THREE.Mesh(new THREE.BoxGeometry(0.25, h, 0.25), tp); m.position.set(x, y, z); m.castShadow = true; m.receiveShadow = true; return m; };
  group.add(fence(L.lamp.x, 1, L.lamp.z, 2));
  const gs = M('glowstone.png', { emissive: 0xffffff });
  gs.emissiveMap = gs.map; gs.emissiveIntensity = 0.9;
  const lampTop = cube(gs, L.lamp.x, 2.5, L.lamp.z, 0.8);
  group.add(lampTop);
  const lampLight = new THREE.PointLight(0xffd88a, 4.2, 9, 2);
  lampLight.position.set(L.lamp.x, 2.6, L.lamp.z);
  group.add(lampLight);
  out.lamp = { light: lampLight };

  // sign: a post and a board, angled to the camera
  const sign = new THREE.Group();
  sign.position.set(L.sign.x, 0, L.sign.z);
  sign.rotation.y = Math.atan2(7.6 - L.sign.x, 10.2 - L.sign.z);
  sign.add(fence(0, 0.5, 0, 1));
  const board = new THREE.Mesh(new THREE.BoxGeometry(0.9, 0.5, 0.09), [tp, tp, tp, tp, new THREE.MeshLambertMaterial({ map: signTexture() }), tp]);
  board.position.set(0, 1.15, 0.0);
  board.castShadow = true;
  sign.add(board);
  group.add(sign);

  // the wheat patch: farmland, hash-shaped crops, fence with a gap on the east
  const W = L.wheat;
  const farm = new THREE.Mesh(new THREE.PlaneGeometry(W.w, W.d), M('farmland_wet.png'));
  farm.material = farm.material.clone(); farm.material.map = farm.material.map.clone(); farm.material.map.repeat.set(W.w, W.d); farm.material.map.wrapS = farm.material.map.wrapT = THREE.RepeatWrapping; farm.material.map.needsUpdate = true;
  farm.rotation.x = -Math.PI / 2;
  farm.position.set(W.x0 + W.w / 2, 0.012, W.z0 + W.d / 2);
  farm.receiveShadow = true;
  group.add(farm);
  const wp = [], wuv = [], wi = [];
  let k = 0;
  for (let ix = 0; ix < W.w; ix++) for (let iz = 0; iz < W.d; iz++) {
    const cx = W.x0 + ix + 0.5, cz = W.z0 + iz + 0.5, h = 0.8 + ((ix * 7 + iz * 3) % 3) * 0.06;
    for (const [ax, az, bx, bz] of [[-0.5, -0.25, 0.5, -0.25], [-0.5, 0.25, 0.5, 0.25], [-0.25, -0.5, -0.25, 0.5], [0.25, -0.5, 0.25, 0.5]]) {
      wp.push(cx + ax, 0, cz + az, cx + bx, 0, cz + bz, cx + bx, h, cz + bz, cx + ax, h, cz + az);
      wuv.push(0, 0, 1, 0, 1, 1, 0, 1);
      wi.push(k, k + 1, k + 2, k, k + 2, k + 3, k, k + 2, k + 1, k, k + 3, k + 2); k += 4;
    }
  }
  const wg = new THREE.BufferGeometry();
  wg.setAttribute('position', new THREE.Float32BufferAttribute(wp, 3));
  wg.setAttribute('uv', new THREE.Float32BufferAttribute(wuv, 2));
  wg.setAttribute('normal', new THREE.Float32BufferAttribute(new Array(wp.length).fill(0).map((_, i) => (i % 3 === 1 ? 1 : 0)), 3));
  wg.setIndex(wi);
  group.add(new THREE.Mesh(wg, new THREE.MeshLambertMaterial({ map: tex('blocks/wheat_stage_7.png'), alphaTest: 0.5, side: THREE.DoubleSide })));
  // fence round the patch
  const x0 = W.x0 - 0.5, x1 = W.x0 + W.w + 0.5, z0 = W.z0 - 0.5, z1 = W.z0 + W.d + 0.5;
  const posts = [];
  for (let x = x0; x <= x1 + 0.01; x += 1) for (const z of [z0, z1]) posts.push([x, z]);
  for (let z = z0 + 1; z < z1 - 0.01; z += 1) for (const x of [x0, x1]) posts.push([x, z]);
  const geoms = [];
  const addBox = (w, h, d, x, y, z) => { const g = new THREE.BoxGeometry(w, h, d); g.translate(x, y, z); geoms.push(g); };
  for (const [x, z] of posts) addBox(0.25, 1.1, 0.25, x, 0.55, z);
  const rail = (ax, az, bx, bz) => {
    const len = Math.hypot(bx - ax, bz - az) - 0.25;
    for (const y of [0.45, 0.85]) {
      const horiz = Math.abs(bz - az) < 0.01;
      addBox(horiz ? len : 0.1, 0.12, horiz ? 0.1 : len, (ax + bx) / 2, y, (az + bz) / 2);
    }
  };
  for (let x = x0; x < x1 - 0.01; x += 1) { rail(x, z0, x + 1, z0); rail(x, z1, x + 1, z1); }
  for (let z = z0; z < z1 - 0.01; z += 1) { rail(x0, z, x0, z + 1); if (Math.abs(z - (W.z0 + 1)) > 0.6) rail(x1, z, x1, z + 1); }
  const fg = mergeBoxes(geoms);
  const fenceMesh = new THREE.Mesh(fg, tp);
  fenceMesh.castShadow = true; fenceMesh.receiveShadow = true;
  group.add(fenceMesh);

  // the quarry: loose ore and stone, one mesh per block so Steve can mine them
  const kinds = { coal: 'coal_ore.png', stone: 'stone.png', iron: 'iron_ore.png' };
  for (const q of L.quarry) {
    const mesh = cube(M(kinds[q.kind]), q.cx + 0.5, (q.y || 0) + 0.5, q.cz + 0.5);
    group.add(mesh);
    out.quarry.push({ mesh, x: q.cx + 0.5, y: (q.y || 0) + 0.5, z: q.cz + 0.5, kind: q.kind, file: kinds[q.kind], removed: false });
  }

  // each frame: fire and lamp flicker
  out.update = (t) => {
    fireLight.intensity = 4.6 + 0.9 * Math.sin(t * 11.3) + 0.5 * Math.sin(t * 19.7 + 1);
    fireGlow.material.opacity = 0.5 + 0.12 * Math.sin(t * 9.1);
    lampLight.intensity = 4.0 + 0.2 * Math.sin(t * 3.1);
    furnaceLight.intensity = 0.8 + 0.25 * Math.sin(t * 7 + 2);
    for (const q of flames.children) q.scale.y = 1 + 0.08 * Math.sin(t * 14 + q.rotation.y * 3);
  };
  return out;
}

function mergeBoxes(list) {
  let n = 0, ni = 0;
  for (const g of list) { n += g.attributes.position.count; ni += g.index.count; }
  const pos = new Float32Array(n * 3), nor = new Float32Array(n * 3), uv = new Float32Array(n * 2), idx = new Uint32Array(ni);
  let o = 0, oi = 0;
  for (const g of list) {
    pos.set(g.attributes.position.array, o * 3); nor.set(g.attributes.normal.array, o * 3); uv.set(g.attributes.uv.array, o * 2);
    for (let i = 0; i < g.index.count; i++) idx[oi + i] = g.index.array[i] + o;
    o += g.attributes.position.count; oi += g.index.count;
  }
  const r = new THREE.BufferGeometry();
  r.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  r.setAttribute('normal', new THREE.BufferAttribute(nor, 3));
  r.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
  r.setIndex(new THREE.BufferAttribute(idx, 1));
  return r;
}
