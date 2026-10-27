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
  // the workshop: a note block, an enchanting table and a brewing stand, in the table row's line, used from the front
  note: { cx: 0, cz: -5 }, brew: { cx: 1, cz: -5 }, enchant: { cx: 7, cz: -5 },
  noteStand: { x: 0.5, z: -3.45 }, brewStand: { x: 1.5, z: -3.45 }, enchantStand: { x: 7.5, z: -3.45 },
  pen: { x0: -10, x1: -5, z0: 2, z1: 7 },   // the animals' fenced pen, west of the pond, by the wheat
  hut: { cx: 4, cz: -1 },       // a 3x3 patch of ground for the dirt hut
  hole: { cx: 1, cz: 3 },       // the cell he digs, and the one he sprint-jumps onto
  jump: { cx: 1, cz: 8 },
  shelves: [{ cx: 5, cz: -7 }, { cx: 6, cz: -7 }, { cx: 7, cz: -7 }], // two high, behind the enchanting table
  target: { x: 6.5, z: 6.5 },   // the hay bale the bow shoots at, and the spot he shoots from
  shoot: { x: 1.5, z: 6.5 },
  sapling: { cx: 5, cz: 0 },
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
    [-0.1, -5.1, 2.1, -3.9],
    [6.9, -5.1, 8.1, -3.9],
    [-10.1, 1.9, -4.9, 7.1],
    [3.9, -1.1, 7.1, 2.1],
    [6.0, 6.0, 7.0, 7.0],
    [1.0, 3.0, 2.0, 4.0],
    [0.9, 7.9, 2.1, 9.1],
    [4.9, -7.1, 8.1, -5.9],
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

// The 1.7.10 enchanting-table book (ModelBook, entity/enchanting_table_book.png 64x32): two covers, a spine,
// two page blocks and two flipping pages, hinged on the spine. spread 0 shut .. 1 open.
function bookModel() {
  const t = tex('entity/enchanting_table_book.png');
  const mat = new THREE.MeshLambertMaterial({ map: t, side: THREE.DoubleSide, emissive: 0x2a2018 });
  const mk = (box, uv) => { const m = new THREE.Mesh(outward(boxGeometry(box, uv, 64, 32)), mat); m.castShadow = true; return m; };
  const root = new THREE.Group();                 // placed on the table: translate (0.5, 0.75, 0.5)
  const lift = new THREE.Group(); root.add(lift); // bobbing, the tilt
  const body = new THREE.Group(); lift.add(body); // scaled 1/16 by boxGeometry already (units are blocks)
  const coverR = new THREE.Group(), coverL = new THREE.Group(), pagesR = new THREE.Group(), pagesL = new THREE.Group(), flipR = new THREE.Group(), flipL = new THREE.Group();
  coverR.add(mk([-6, -5, 0, 6, 10, 1], [0, 0])); coverL.add(mk([0, -5, 0, 6, 10, 1], [16, 0]));
  pagesR.add(mk([0, -4, -0.99, 5, 8, 1], [0, 10])); pagesL.add(mk([0, -4, -0.01, 5, 8, 1], [12, 10]));
  const pg = () => { const m = new THREE.Mesh(new THREE.PlaneGeometry(5 / 16, 8 / 16), mat); m.position.set(2.5 / 16, 0, 0); const uv = m.geometry.attributes.uv; const u0 = 24 / 64, u1 = 29 / 64, v0 = 1 - 18 / 32, v1 = 1 - 10 / 32; uv.setXY(0, u0, v1); uv.setXY(1, u1, v1); uv.setXY(2, u0, v0); uv.setXY(3, u1, v0); return m; };
  flipR.add(pg()); flipL.add(pg());
  const spine = mk([-1, -5, 0, 2, 10, 4], [12, 0]); spine.rotation.y = Math.PI / 2;
  coverR.position.z = -1 / 16; coverL.position.z = 1 / 16;
  body.add(coverR, coverL, pagesR, pagesL, flipR, flipL, spine);
  const api = {
    group: root,
    set(spread, fr, fl, bob, yaw, tilt) {
      const f6 = (Math.sin(spread * 6.0) * 0.1 + 1.25) * spread;
      coverR.rotation.y = Math.PI + f6; coverL.rotation.y = -f6;
      pagesR.rotation.y = f6; pagesL.rotation.y = -f6;
      flipR.rotation.y = f6 - f6 * 2 * fr; flipL.rotation.y = f6 - f6 * 2 * fl;
      const sx = Math.sin(f6) / 16;
      pagesR.position.x = pagesL.position.x = flipR.position.x = flipL.position.x = sx;
      flipR.visible = flipL.visible = spread > 0.02;
      lift.position.y = 0.1 + bob;
      lift.rotation.set(0, 0, -tilt);
      root.rotation.y = yaw;
    },
  };
  api.set(0, 0, 0, 0, 0, 1.4);
  return api;
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
  { const P = L.pen; for (let x = P.x0; x <= P.x1; x++) for (let z = P.z0; z <= P.z1; z++) { const edge = x === P.x0 || x === P.x1 || z === P.z0 || z === P.z1; if (edge && !(x === P.x1 && z === 4)) fenceCells.push([x, 0, z]); } }
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
  // crops: one small mesh per plant so he can harvest, replant and bone-meal them one by one. A plant is two
  // crossed pairs of quads (the game's hash shape) textured with the wheat stage; stage 0..7, height as the game draws it.
  const stageMats = [];
  for (let i = 0; i < 8; i++) stageMats.push(new THREE.MeshLambertMaterial({ map: tex('blocks/wheat_stage_' + i + '.png'), alphaTest: 0.5, side: THREE.DoubleSide }));
  const cropGeo = (() => {
    const wp = [], wuv = [], wi = [];
    let k = 0;
    for (const [ax, az, bx, bz] of [[-0.5, -0.25, 0.5, -0.25], [-0.5, 0.25, 0.5, 0.25], [-0.25, -0.5, -0.25, 0.5], [0.25, -0.5, 0.25, 0.5]]) {
      wp.push(ax, 0, az, bx, 0, bz, bx, 1, bz, ax, 1, az);
      wuv.push(0, 0, 1, 0, 1, 1, 0, 1);
      wi.push(k, k + 1, k + 2, k, k + 2, k + 3); k += 4;
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(wp, 3));
    g.setAttribute('uv', new THREE.Float32BufferAttribute(wuv, 2));
    g.setAttribute('normal', new THREE.Float32BufferAttribute(new Array(wp.length).fill(0).map((_, i) => (i % 3 === 1 ? 1 : 0)), 3));
    g.setIndex(wi);
    return g;
  })();
  out.crops = [];
  for (let ix = 0; ix < W.w; ix++) for (let iz = 0; iz < W.d; iz++) {
    const m = new THREE.Mesh(cropGeo, stageMats[7]);
    const cx = W.x0 + ix + 0.5, cz = W.z0 + iz + 0.5;
    m.position.set(cx, 0, cz);
    group.add(m);
    const c = { mesh: m, x: cx, z: cz, stage: 7, setStage(n) { c.stage = n; m.visible = n >= 0; if (n >= 0) m.material = stageMats[Math.min(7, n)]; } };
    out.crops.push(c);
  }
  out.cropsReset = () => { for (const c of out.crops) c.setStage(7); };

  // ---- the workshop: note block, enchanting table, brewing stand (1.7.10 models)
  const noteBlock = cube(M('noteblock.png'), c(L.note.cx), 0.5, c(L.note.cz));
  group.add(noteBlock);
  nav.add('note', L.note.cx, L.note.cz, L.note.cx + 1, L.note.cz + 1, 'solid');
  out.note = noteBlock;
  // enchanting table: a 16x12x16 block, obsidian-dark sides, and the floating book
  const et = M('enchanting_table_top.png'), es = M('enchanting_table_side.png'), eb = M('enchanting_table_bottom.png');
  const eGeo = new THREE.BoxGeometry(1, 0.75, 1);
  { // RenderBlocks with the bounds 0..0.75: v runs from row 4 (the top of the 12 px) to row 16 on the four sides
    const uv = eGeo.attributes.uv;
    for (const f of [0, 1, 4, 5]) for (let i = 0; i < 4; i++) uv.setY(f * 4 + i, uv.getY(f * 4 + i) * 0.75);
    uv.needsUpdate = true;
  }
  const enchant = new THREE.Mesh(eGeo, faces6(es, es, et, eb, es, es));
  enchant.position.set(c(L.enchant.cx), 0.375, c(L.enchant.cz));
  enchant.castShadow = enchant.receiveShadow = true;
  group.add(enchant);
  nav.add('enchant', L.enchant.cx, L.enchant.cz, L.enchant.cx + 1, L.enchant.cz + 1, 'solid');
  const book = bookModel();
  book.group.position.set(c(L.enchant.cx), 0.75, c(L.enchant.cz));
  group.add(book.group);
  out.enchant = { table: enchant, book, spread: 0, flipA: 0, flipB: 0, rot: 0, tick: 0, flipT: 0, last: null };
  // the bookshelves round the table (two high, with a gap of air between): the enchanting glyphs fly from them
  const bsS = M('bookshelf.png'), bsT = M('planks_oak.png');
  out.shelves = [];
  for (const sh of L.shelves) for (let y = 0; y < 2; y++) {
    const m = cube(faces6(bsS, bsS, bsT, bsT, bsS, bsS), c(sh.cx), y + 0.5, c(sh.cz));
    group.add(m);
    out.shelves.push({ x: sh.cx, y, z: sh.cz });
  }
  for (const sh of L.shelves) nav.add('shelf', sh.cx, sh.cz, sh.cx + 1, sh.cz + 1, 'solid');
  // the hay bale the bow shoots at: a permanent target, so nothing appears out of thin air
  const hs = M('hay_block_side.png'), ht = M('hay_block_top.png');
  const hay = cube(faces6(hs, hs, ht, ht, hs, hs), L.target.x, 0.5, L.target.z);
  group.add(hay);
  nav.add('hay', L.target.x - 0.5, L.target.z - 0.5, L.target.x + 0.5, L.target.z + 0.5, 'solid');
  out.hay = hay;
  // brewing stand: the rod and the three base plates, exactly RenderBlocks.renderBlockBrewingStand
  const brewG = new THREE.Group();
  brewG.position.set(L.brew.cx, 0, L.brew.cz);
  const bsTex = M('brewing_stand.png', { transparent: true, alphaTest: 0.2 }), bbT = M('brewing_stand_base.png', { transparent: true, alphaTest: 0.2 });
  const plate = (x0, z0, x1, z1) => { const m = new THREE.Mesh(new THREE.BoxGeometry(x1 - x0, 0.125, z1 - z0), bbT); m.position.set((x0 + x1) / 2, 0.0625, (z0 + z1) / 2); m.castShadow = m.receiveShadow = true; return m; };
  const rod = new THREE.Mesh(new THREE.BoxGeometry(0.125, 0.875, 0.125), bsTex); rod.position.set(0.5, 0.4375, 0.5); rod.castShadow = true;
  brewG.add(rod, plate(0.5625, 0.3125, 0.9375, 0.6875), plate(0.0625, 0.0625, 0.4375, 0.4375), plate(0.0625, 0.5625, 0.4375, 0.9375));
  // the blaze rod's top is the stand's burner: three bottles hang off the plates
  const bottleMat = new THREE.MeshLambertMaterial({ color: 0x3f76e4, transparent: true, opacity: 0.85 });
  out.brew = { group: brewG, bottles: [], x: L.brew.cx + 0.5, z: L.brew.cz + 0.5 };
  for (const [bx, bz] of [[0.75, 0.5], [0.25, 0.25], [0.25, 0.75]]) {
    const bm = new THREE.Mesh(new THREE.BoxGeometry(0.2, 0.34, 0.2), bottleMat);
    bm.position.set(bx, 0.3, bz); bm.visible = false; bm.castShadow = true;
    brewG.add(bm); out.brew.bottles.push(bm);
  }
  group.add(brewG);
  nav.add('brew', L.brew.cx + 0.05, L.brew.cz + 0.05, L.brew.cx + 0.95, L.brew.cz + 0.95, 'solid');
  out.brew.setBottles = (n, col) => { out.brew.bottles.forEach((m, i) => { m.visible = i < n; if (col != null) m.material.color.setHex(col); }); };

  // the quarry: loose ore and stone, one mesh per block so Steve can mine them
  const kinds = { coal: 'coal_ore.png', stone: 'stone.png', iron: 'iron_ore.png' };
  for (const q of L.quarry) {
    const mesh = cube(M(kinds[q.kind]), q.cx + 0.5, (q.y || 0) + 0.5, q.cz + 0.5);
    group.add(mesh);
    const box = (q.y || 0) === 0 ? nav.add('quarry', q.cx, q.cz, q.cx + 1, q.cz + 1, 'solid') : null;
    out.quarry.push({ mesh, box, x: q.cx + 0.5, y: (q.y || 0) + 0.5, z: q.cz + 0.5, kind: q.kind, file: kinds[q.kind], removed: false });
  }

  // The enchanting glyphs (BlockEnchantmentTable.randomDisplayTick + EntityEnchantmentTableParticleFX): every tick
  // each bookshelf round the table has a 1 in 16 chance to send one; it starts at the shelf and drifts to the
  // table top along a curve, in one of the 26 galactic letters of particles.png (cells 225..250), light blue-white.
  const glyphMat = [];
  const glyphTex = () => {
    if (glyphMat.length) return glyphMat;
    const base = tex('particle/particles.png');
    if (!(base.image && base.image.width)) return null; // still loading: a clone made now would never upload
    for (let i = 0; i < 26; i++) {
      const idx = 225 + i, col = idx % 16, row = Math.floor(idx / 16);
      const t = base.clone();
      t.repeat.set(1 / 16, 1 / 16); t.offset.set(col / 16, 1 - (row + 1) / 16); t.needsUpdate = true;
      glyphMat.push(t);
    }
    return glyphMat;
  };
  const glyphs = [];
  const ET = { x: L.enchant.cx + 0.5, y: 2.0, z: L.enchant.cz + 0.5 };
  function spawnGlyph(mx, my, mz) {
    const gm = glyphTex();
    if (!gm) return;
    const f = Math.random() * 0.6 + 0.4;
    const mat = new THREE.SpriteMaterial({ map: gm[Math.floor(Math.random() * 26)], color: new THREE.Color(f * 0.9, f * 0.9, f), transparent: true, depthWrite: false, fog: false });
    const sp = new THREE.Sprite(mat);
    const sc = (Math.random() * 0.5 + 0.2) * 0.2 * 1.7;
    sp.scale.set(sc, sc, 1);
    group.add(sp);
    glyphs.push({ sp, mx, my, mz, age: 0, max: Math.floor(Math.random() * 10) + 30 });
  }
  let glyphT = null, glyphAcc = 0;
  function stepGlyphs(t) {
    const dt = glyphT === null ? 0 : Math.min(0.1, t - glyphT);
    glyphT = t;
    glyphAcc += dt * 20;
    while (glyphAcc >= 1) {
      glyphAcc -= 1;
      for (const sh of out.shelves) if (Math.random() < 1 / 16) spawnGlyph(sh.x - L.enchant.cx + Math.random() - 0.5, sh.y - Math.random() - 1.0, sh.z - L.enchant.cz + Math.random() - 0.5);
      for (const g of glyphs) g.age++;
    }
    for (let i = glyphs.length - 1; i >= 0; i--) {
      const g = glyphs[i];
      const a = Math.min(1, (g.age + glyphAcc) / g.max), f1 = a;
      const f = 1 - (-a + a * a * 2);
      g.sp.position.set(ET.x + g.mx * f, ET.y + g.my * f + (1 - f1), ET.z + g.mz * f);
      if (g.age >= g.max) { group.remove(g.sp); g.sp.material.dispose(); glyphs.splice(i, 1); }
    }
  }
  out.glyphs = glyphs;

  // each frame: fire and lamp flicker; the furnace glows only while it is lit
  out.update = (t) => {
    stepGlyphs(t);
    fireLight.intensity = 4.6 + 0.9 * Math.sin(t * 11.3) + 0.5 * Math.sin(t * 19.7 + 1);
    fireGlow.material.opacity = 0.5 + 0.12 * Math.sin(t * 9.1);
    lampLight.intensity = 4.0 + 0.2 * Math.sin(t * 3.1);
    furnaceLight.intensity = out.furnaceLit ? 0.8 + 0.25 * Math.sin(t * 7 + 2) : 0;
    for (const q of flames.children) q.scale.y = 1 + 0.08 * Math.sin(t * 14 + q.rotation.y * 3);
    // the enchanting table's book (TileEntityEnchantmentTable.updateEntity): it opens and turns to a player within
    // three blocks, flips pages while open, and drifts shut and slowly turning when alone
    const e = out.enchant, tick = t * 20, dtk = e.last === null ? 0 : Math.min(3, tick - e.last);
    e.last = tick;
    if (dtk > 0) {
      const np = out.near;
      const dx = np ? np.x - (L.enchant.cx + 0.5) : 99, dz = np ? np.z - (L.enchant.cz + 0.5) : 99;
      const close = dx * dx + dz * dz < 9;
      const want = close ? Math.atan2(dz, dx) : null;
      e.spread += ((close ? 1 : 0) - e.spread) * Math.min(1, 0.1 * dtk) * (close ? 1 : 1.1);
      if (close) {
        let d = want - e.rot; while (d >= Math.PI) d -= Math.PI * 2; while (d < -Math.PI) d += Math.PI * 2;
        e.rot += d * Math.min(1, 0.4 * dtk);
        e.flipT += dtk;
        if (e.flipT > 40 + Math.random() * 40) { e.flipT = 0; e.flipB = (Math.random() < 0.5 ? 1 : -1) * 0.12; }
      } else e.rot += 0.02 * dtk;
      e.flipA += e.flipB * dtk; e.flipB *= Math.pow(0.9, dtk);
      e.flipA = Math.max(0, Math.min(1, e.flipA)); if (e.flipA === 0 || e.flipA === 1) e.flipB = 0;
      e.fr = Math.max(0, Math.min(1, e.flipA + (e.flipB * 0))); 
    }
    const fr = Math.max(0, Math.min(1, e.flipA + 0.15)), fl = Math.max(0, Math.min(1, e.flipA - 0.15));
    e.book.set(Math.max(0, e.spread), fr, fl, Math.sin(t * 2) * 0.01 * 2 + 0.01, -e.rot + Math.PI / 2, 1.4);
  };
  return out;
}
