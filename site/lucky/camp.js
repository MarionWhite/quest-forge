// Steve's campsite: crafting table, furnace (lit), chest, a netherrack campfire, a fenced wheat patch,
// a lamppost (fence + glowstone), a sign, a seat, and a small quarry of loose blocks to mine.
// Geometry is a handful of small meshes (the terrain stays one merged mesh). Steve's activities
// read the spots and obstacles in L.
import * as THREE from 'three';
import { tex, fireMaterial, glowTexture } from './stage.js';
import { boxGeometry } from './mobs.js';
import { nav } from './nav.js';

// World coordinates, ground at y = 0. A cell (cx, cz) fills [cx, cx+1] x [cz, cz+1].
export const L = {
  flat: { x0: -10, x1: 8, z0: -8, z1: 1 },        // stage.js keeps this rectangle level
  // the table, furnace and chest stand in a row facing +z (the camera side); Steve uses each from its front
  table: { cx: 3, cz: -5 }, furnace: { cx: 4, cz: -5 }, chest: { cx: 5, cz: -5 },
  tableStand: { x: 3.5, z: -3.45 }, furnaceStand: { x: 4.5, z: -3.45 }, chestStand: { x: 5.5, z: -3.45 },
  fire: { cx: -5, cz: -1 }, fireCenter: { x: -4.5, z: -0.5 },
  seat: { cx: -5, cz: -3 }, seatApproach: { x: -4.5, z: -3.55 }, seatPos: { x: -4.5, z: -2.5 },
  lamp: { x: 2.5, z: -2.5 },
  sign: { x: 7.2, z: 2.4 },
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
    [6.8, 2.0, 7.6, 2.8],
    [-4.2, 1.8, -1.85, 4.2],
    [-9.3, -5.3, -5.7, -1.7],
    [-4.3, -7.3, -0.7, -5.9],
    [-8.3, -0.3, -6.9, 1.3],
    [-8.4, -8.4, -4.8, -4.8],
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

// The chest, from 1.7.10's ModelChest: base 14 x 10 x 14, lid 14 x 5 x 14 hinged at the back, latch 2 x 4 x 1.
// Built facing -z (the legacy model orientation) and turned to face +z by the caller. Opaque, one
// material, lit like a block; the lid is a hair larger so its front never z-fights the base's top rim.
// the library's box has its winding mirrored (it draws y flipped): flip it back so FrontSide shows the outside
function outward(geo) {
  const a = geo.index.array;
  for (let i = 0; i < a.length; i += 3) { const t = a[i + 1]; a[i + 1] = a[i + 2]; a[i + 2] = t; }
  geo.index.needsUpdate = true;
  return geo;
}
function chestParts() {
  const t = tex('entity/chest.png');
  const mat = new THREE.MeshLambertMaterial({ map: t, alphaTest: 0.5, side: THREE.FrontSide });
  const root = new THREE.Group();
  const base = new THREE.Mesh(outward(boxGeometry([-7, -10, -7, 14, 10, 14], [0, 19], 64, 64)), mat);
  base.castShadow = base.receiveShadow = true;
  root.add(base);
  const hinge = new THREE.Group();
  hinge.position.set(0, 9 / 16, 7 / 16); // model y = 7 below the top of the 16-px cell
  const lid = new THREE.Mesh(outward(boxGeometry([-7, -5, -14, 14, 5, 14], [0, 0], 64, 64)), mat);
  lid.castShadow = lid.receiveShadow = true;
  lid.scale.set(1.002, 1.002, 1.002);
  const latch = new THREE.Mesh(outward(boxGeometry([-1, -2, -15, 2, 4, 1], [0, 0], 64, 64)), mat);
  latch.castShadow = true;
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

// ---------------------------------------------------------------- fences, the 1.7.10 model
// A post (6..10 px square, full height) and, toward every neighbouring fence, two rails (7..9 px thick,
// at 6..9 px and 12..15 px up) that run from the post to the cell edge. Texture coordinates come from
// the position inside the cell, like the game's per-face block bounds, so planks_oak runs unbroken
// across posts, rails and neighbouring fences.
const FACES = [
  { n: [1, 0, 0], c: [[1, 0, 0], [1, 0, 1], [1, 1, 1], [1, 1, 0]] },
  { n: [-1, 0, 0], c: [[0, 0, 0], [0, 1, 0], [0, 1, 1], [0, 0, 1]] },
  { n: [0, 1, 0], c: [[0, 1, 0], [1, 1, 0], [1, 1, 1], [0, 1, 1]] },
  { n: [0, -1, 0], c: [[0, 0, 0], [0, 0, 1], [1, 0, 1], [1, 0, 0]] },
  { n: [0, 0, 1], c: [[0, 0, 1], [0, 1, 1], [1, 1, 1], [1, 0, 1]] },
  { n: [0, 0, -1], c: [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]] },
];
// a box [ax, ay, az] .. [bx, by, bz] (cell fractions) inside the cell whose origin is (ox, oy, oz)
function pushBox(g, ox, oy, oz, a, b) {
  for (const f of FACES) {
    const base = g.p.length / 3;
    for (const c of f.c) {
      const lx = c[0] ? b[0] : a[0], ly = c[1] ? b[1] : a[1], lz = c[2] ? b[2] : a[2];
      g.p.push(ox + lx, oy + ly, oz + lz);
      g.n.push(f.n[0], f.n[1], f.n[2]);
      // u runs along the face's horizontal axis, v up the cell; top and bottom use x and z
      if (f.n[0]) g.uv.push(lz, ly); else if (f.n[2]) g.uv.push(lx, ly); else g.uv.push(lx, lz);
    }
    // wind the quad so its front faces along the normal
    const P = g.p, o = base * 3;
    const e1 = [P[o + 3] - P[o], P[o + 4] - P[o + 1], P[o + 5] - P[o + 2]], e2 = [P[o + 6] - P[o + 3], P[o + 7] - P[o + 4], P[o + 8] - P[o + 5]];
    const cr = [e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]];
    if (cr[0] * f.n[0] + cr[1] * f.n[1] + cr[2] * f.n[2] >= 0) g.i.push(base, base + 1, base + 2, base, base + 2, base + 3);
    else g.i.push(base, base + 2, base + 1, base, base + 3, base + 2);
  }
}
function fenceGeometry(cells) {
  const g = { p: [], n: [], uv: [], i: [] };
  const has = new Set(cells.map((c) => c.join(',')));
  const P0 = 6 / 16, P1 = 10 / 16, R0 = 7 / 16, R1 = 9 / 16;
  const bands = [[6 / 16, 9 / 16], [12 / 16, 15 / 16]];
  for (const [x, y, z] of cells) {
    pushBox(g, x, y, z, [P0, 0, P0], [P1, 1, P1]);
    for (const [y0, y1] of bands) {
      if (has.has([x + 1, y, z].join(','))) pushBox(g, x, y, z, [P1, y0, R0], [1, y1, R1]);
      if (has.has([x - 1, y, z].join(','))) pushBox(g, x, y, z, [0, y0, R0], [P0, y1, R1]);
      if (has.has([x, y, z + 1].join(','))) pushBox(g, x, y, z, [R0, y0, P1], [R1, y1, 1]);
      if (has.has([x, y, z - 1].join(','))) pushBox(g, x, y, z, [R0, y0, 0], [R1, y1, P0]);
    }
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(g.p, 3));
  geo.setAttribute('normal', new THREE.Float32BufferAttribute(g.n, 3));
  geo.setAttribute('uv', new THREE.Float32BufferAttribute(g.uv, 2));
  geo.setIndex(g.i);
  return geo;
}

export function buildCamp(S) {
  const group = new THREE.Group();
  S.scene.add(group);
  const out = { group, quarry: [], obstacles: L.obstacles, nav };
  const c = (cx) => cx + 0.5;

  // ---- navigation: the stage's voxels (trees, rocks, dais, hills) and every prop below
  if (S.vox) nav.fromVoxels(S.vox);
  nav.add('table', L.table.cx, L.table.cz, L.table.cx + 1, L.table.cz + 1, 'solid');
  nav.add('furnace', L.furnace.cx, L.furnace.cz, L.furnace.cx + 1, L.furnace.cz + 1, 'solid');
  nav.add('chest', L.chest.cx + 1 / 16, L.chest.cz + 1 / 16, L.chest.cx + 15 / 16, L.chest.cz + 15 / 16, 'solid');
  nav.add('fire', L.fire.cx - 0.15, L.fire.cz - 0.15, L.fire.cx + 1.15, L.fire.cz + 1.15, 'solid');
  nav.add('seat', L.seat.cx, L.seat.cz, L.seat.cx + 1, L.seat.cz + 1, 'low');
  nav.add('lamp', L.lamp.x - 0.125, L.lamp.z - 0.125, L.lamp.x + 0.125, L.lamp.z + 0.125, 'solid');
  nav.add('sign', L.sign.x - 0.5, L.sign.z - 0.2, L.sign.x + 0.5, L.sign.z + 0.2, 'solid');
  nav.add('pond', -4, 2, -2, 4, 'water');

  // crafting table, furnace (off until it smelts), chest, all facing +z, the camera side
  const tp = M('planks_oak.png'), ts = M('crafting_table_side.png'), tf = M('crafting_table_front.png');
  const table = cube(faces6(ts, tf, M('crafting_table_top.png'), tp, ts, tf), c(L.table.cx), 0.5, c(L.table.cz));
  const fs = M('furnace_side.png');
  const frontOn = M('furnace_front_on.png', { emissive: 0xffffff });
  frontOn.emissiveMap = frontOn.map;
  frontOn.emissiveIntensity = 1.0;
  const frontOff = M('furnace_front_off.png');
  const furnace = cube(faces6(fs, fs, M('furnace_top.png'), M('furnace_top.png'), frontOff, fs), c(L.furnace.cx), 0.5, c(L.furnace.cz));
  const chest = chestParts();
  chest.root.position.set(c(L.chest.cx), 0, c(L.chest.cz));
  chest.root.rotation.y = Math.PI; // the latch faces +z
  group.add(table, furnace, chest.root);
  out.chest = { root: chest.root, hinge: chest.hinge, open: 0, setOpen(k) { out.chest.open = k; chest.hinge.rotation.x = k * (Math.PI / 2); } };
  out.table = table; out.furnace = furnace;

  // the furnace glow follows its state: dark and cold until Steve lights it
  const furnaceLight = new THREE.PointLight(0xff9a4a, 0.0, 3.2, 2);
  furnaceLight.position.set(c(L.furnace.cx), 0.55, c(L.furnace.cz) + 0.9);
  group.add(furnaceLight);
  out.furnaceLit = false;
  out.setFurnace = (on) => {
    out.furnaceLit = !!on;
    furnace.material[4] = on ? frontOn : frontOff;
  };

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

  // every fence in the camp is one mesh built from cells: the lamppost, the wheat ring, the sign post
  const fenceCells = [];
  const lcx = Math.floor(L.lamp.x), lcz = Math.floor(L.lamp.z);
  fenceCells.push([lcx, 0, lcz], [lcx, 1, lcz]);
  const W = L.wheat;
  const ring = [];
  for (let x = W.x0 - 1; x <= W.x0 + W.w; x++) for (let z = W.z0 - 1; z <= W.z0 + W.d; z++) {
    const edge = x === W.x0 - 1 || x === W.x0 + W.w || z === W.z0 - 1 || z === W.z0 + W.d;
    const gap = x === W.x0 + W.w && z === W.z0 + 1; // the opening on the east side
    if (edge && !gap) ring.push([x, 0, z]);
  }
  fenceCells.push(...ring);
  const scx = Math.floor(L.sign.x), scz = Math.floor(L.sign.z);
  const fenceMesh = new THREE.Mesh(fenceGeometry(fenceCells), M('planks_oak.png'));
  fenceMesh.castShadow = true; fenceMesh.receiveShadow = true;
  group.add(fenceMesh);
  // collision: a post and an arm toward every neighbouring fence, the game's 0.25-wide fence box
  const have = new Set(fenceCells.map((q) => q.join(',')));
  for (const [x, y, z] of fenceCells) {
    if (y > 0) continue;
    nav.add('fence', x + 0.375, z + 0.375, x + 0.625, z + 0.625, 'fence');
    if (have.has([x + 1, 0, z].join(','))) nav.add('fence', x + 0.625, z + 0.375, x + 1, z + 0.625, 'fence');
    if (have.has([x, 0, z + 1].join(','))) nav.add('fence', x + 0.375, z + 0.625, x + 0.625, z + 1, 'fence');
  }
  nav.add('lamp', L.lamp.x - 0.125, L.lamp.z - 0.125, L.lamp.x + 0.125, L.lamp.z + 0.125, 'solid');
  void scx; void scz;

  const gs = M('glowstone.png', { emissive: 0xffffff });
  gs.emissiveMap = gs.map; gs.emissiveIntensity = 0.9;
  const lampTop = cube(gs, lcx + 0.5, 2.5, lcz + 0.5, 1);
  group.add(lampTop);
  const lampLight = new THREE.PointLight(0xffd88a, 4.2, 9, 2);
  lampLight.position.set(lcx + 0.5, 2.6, lcz + 0.5);
  group.add(lampLight);
  out.lamp = { light: lampLight };

  // sign: a post and a board, angled to the camera
  const sign = new THREE.Group();
  sign.position.set(L.sign.x, 0, L.sign.z);
  sign.rotation.y = Math.atan2(7.6 - L.sign.x, 10.2 - L.sign.z);
  const post = new THREE.Mesh(new THREE.BoxGeometry(0.125, 1, 0.125), tp);
  post.position.y = 0.5; post.castShadow = true; post.receiveShadow = true;
  sign.add(post);
  const board = new THREE.Mesh(new THREE.BoxGeometry(0.9, 0.5, 0.09), [tp, tp, tp, tp, new THREE.MeshLambertMaterial({ map: signTexture() }), tp]);
  board.position.set(0, 1.15, 0.0);
  board.castShadow = true;
  sign.add(board);
  group.add(sign);

  // the wheat patch: farmland and hash-shaped crops inside the fence ring
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

  // the quarry: loose ore and stone, one mesh per block so Steve can mine them
  const kinds = { coal: 'coal_ore.png', stone: 'stone.png', iron: 'iron_ore.png' };
  for (const q of L.quarry) {
    const mesh = cube(M(kinds[q.kind]), q.cx + 0.5, (q.y || 0) + 0.5, q.cz + 0.5);
    group.add(mesh);
    const box = (q.y || 0) === 0 ? nav.add('quarry', q.cx, q.cz, q.cx + 1, q.cz + 1, 'solid') : null;
    out.quarry.push({ mesh, box, x: q.cx + 0.5, y: (q.y || 0) + 0.5, z: q.cz + 0.5, kind: q.kind, file: kinds[q.kind], removed: false });
  }

  // each frame: fire and lamp flicker; the furnace glows only while it is lit
  out.update = (t) => {
    fireLight.intensity = 4.6 + 0.9 * Math.sin(t * 11.3) + 0.5 * Math.sin(t * 19.7 + 1);
    fireGlow.material.opacity = 0.5 + 0.12 * Math.sin(t * 9.1);
    lampLight.intensity = 4.0 + 0.2 * Math.sin(t * 3.1);
    furnaceLight.intensity = out.furnaceLit ? 0.8 + 0.25 * Math.sin(t * 7 + 2) : 0;
    for (const q of flames.children) q.scale.y = 1 + 0.08 * Math.sin(t * 14 + q.rotation.y * 3);
  };
  return out;
}
