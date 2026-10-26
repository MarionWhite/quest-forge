// The Krypt: a long gallery cut into stone under the pack's sky. A block grid is meshed once (one mesh per
// texture), with the set pieces, torches, lava seam, pool, chasm, roots and the sky seen through the ceiling.
// Graves stand in alcoves, one per death, in the order of the feed. The camera rides a spline through it.
import * as THREE from "three";
import { hash, rng } from "./data.js";

export const CORRIDOR_HALF = 3;          // corridor cells -3..2 (x -3..3)
export const SLOT_STEP = 4;             // rows between alcoves (whole rows: the grid is indexed by integers)
const SPECIALS = [
  { at: 0.16, kind: "chasm", len: 9 },
  { at: 0.36, kind: "mineshaft", len: 11 },
  { at: 0.56, kind: "lava", len: 7 },
  { at: 0.76, kind: "pool", len: 9 }
];
export const T_AIR = 0, T_STONE = 1, T_COBBLE = 2, T_MOSSY = 3, T_BRICK = 4, T_BRICK_MOSSY = 5,
  T_BRICK_CRACK = 6, T_GRAVEL_FLOOR = 7, T_COAL = 8, T_IRON = 9, T_OBS = 10, T_BEDROCK = 11,
  T_NETHER = 12, T_GLOW = 13, T_BRIDGE = 14, T_WATER = 15;

// The layout: where each alcove is, which set piece sits where, and where the sky opens.
export function layout(n) {
  const slots = Math.max(n, 8);
  const segs = [];
  let k = 7;                              // z of the entrance (the camera starts here)
  const entrance = { kind: "entrance", k0: k, k1: k - 6 };
  k -= 6; segs.push(entrance);
  const slotList = [];
  for (let i = 0; i < slots; i++) {
    for (const sp of SPECIALS) {
      if (Math.floor(slots * sp.at) === i && !segs.some(s => s.kind === sp.kind)) {
        segs.push({ kind: sp.kind, k0: k, k1: k - sp.len }); k -= sp.len;
      }
    }
    const side = i % 2 ? 1 : -1;
    slotList.push({ i, side, k: k - 2 });
    k -= SLOT_STEP;
  }
  const deep = { kind: "deep", k0: k, k1: k - 12 }; k -= 12; segs.push(deep);
  const kEnd = k - 4;
  // Sky holes: three, in the walk's first, middle and last thirds.
  const holes = [0.14, 0.42, 0.78].map(f => Math.round(7 - f * (7 - kEnd)));
  return { slots: slotList, segs, kStart: 7, kEnd, holes, count: n };
}

function cell(a, i, j, k) { return a.g[((k - a.k0) * a.NJ + (j - a.j0)) * a.NI + (i - a.i0)]; }
function setCell(a, i, j, k, t) { a.g[((k - a.k0) * a.NJ + (j - a.j0)) * a.NI + (i - a.i0)] = t; }

// Block at the wall: stone with the occasional ore, moss, crack or seam.
// Every wall, alcove backs and sides included, is stone brick, cracked or mossy brick, cobble or mossy cobble.
// No ore and no plain stone: the ore's speckle read as dirt under the torches.
function wallType(i, j, k) {
  const h = hash(`${i}|${j}|${k}`) % 1000;
  if (h < 160) return T_COBBLE;
  if (h < 260) return T_MOSSY;
  if (h < 560) return T_BRICK;
  if (h < 700) return T_BRICK_MOSSY;
  return T_BRICK_CRACK;
}

// The whole gallery, as a grid of blocks. Returns the meshes and the anchors for the alcoves.
export function buildGrid(lay) {
  const k0 = lay.kEnd - 6, k1 = lay.kStart + 6;
  const i0 = -8, i1 = 8, j0 = -8, j1 = 7;
  const a = { k0, NK: k1 - k0 + 1, i0, NI: i1 - i0 + 1, j0, NJ: j1 - j0 + 1 };
  a.g = new Uint8Array(a.NK * a.NJ * a.NI);
  // Fill: solid everywhere, air in the corridor.
  for (let k = k0; k <= k1; k++) for (let j = j0; j <= j1; j++) for (let i = i0; i <= i1; i++) {
    let t = wallType(i, j, k);
    if (j === 4) { const c = hash(`c${i}|${k}`) % 10; t = c < 2 ? T_BRICK_CRACK : c < 4 ? T_BRICK_MOSSY : T_BRICK; }   // the vault
    if (j === -1) t = T_BRICK;                                                   // floor base
    if (j === -8 || j === 7 || i === -8 || i === 8 || k === k0 || k === k1) t = T_BEDROCK;
    setCell(a, i, j, k, t);
  }
  const carve = (i, j, k, t = T_AIR) => setCell(a, i, j, k, t);
  for (let k = lay.kStart + 5; k >= lay.kEnd - 5; k--) {
    // Corridor: air from floor top to the ceiling, with the top-of-floor as gravel.
    for (let i = -CORRIDOR_HALF; i <= CORRIDOR_HALF - 1; i++) for (let j = 0; j <= 3; j++) carve(i, j, k);
    for (let i = -CORRIDOR_HALF; i <= CORRIDOR_HALF - 1; i++) setCell(a, i, -1, k, T_GRAVEL_FLOOR);
    // The stone-brick path down the middle of the gallery.
    setCell(a, -1, -1, k, T_BRICK); setCell(a, 0, -1, k, T_BRICK);
  }
  // Alcoves: pockets on each side for every slot, with a solid back wall.
  // A cell i spans x in [i, i+1]. The right pocket is cells 3 and 4 (x 3 to 5) with its back at cell 5;
  // the left pocket is cells -4 and -5 (x -5 to -3) with its back at cell -6. The stone stands at x = side * 4.2.
  for (const s of lay.slots) {
    const inner = s.side > 0 ? [3, 4] : [-4, -5];
    const back = s.side > 0 ? 5 : -6;
    for (let k = s.k - 1; k <= s.k + 1; k++) for (let j = 0; j <= 3; j++) {
      carve(inner[0], j, k); carve(inner[1], j, k);
      setCell(a, back, j, k, wallType(back, j, k));
    }
  }
  // Each alcove mouth is framed by two stone-brick pillars in the corridor's edge, with a slab across the top.
  for (const s of lay.slots) {
    const px = s.side > 0 ? 2 : -3;
    for (const k of [s.k - 2, s.k + 2]) {
      for (let j = 0; j <= 2; j++) setCell(a, px, j, k, j === 0 ? T_BRICK_MOSSY : T_BRICK);
    }
    for (let k = s.k - 2; k <= s.k + 2; k++) setCell(a, px, 3, k, T_BRICK);
  }
  // Holes in the ceiling for the sky.
  for (const hk of lay.holes) for (let k = hk - 1; k <= hk + 1; k++) for (let i = -1; i <= 1; i++) carve(i, 4, k);
  // Set pieces.
  for (const sg of lay.segs) {
    const kA = sg.k0, kB = sg.k1;
    if (sg.kind === "chasm") {
      for (let k = kA; k >= kB; k--) {
        for (let i = -CORRIDOR_HALF; i <= CORRIDOR_HALF - 1; i++) {
          if (i === -1 || i === 0) { setCell(a, i, -1, k, T_BRIDGE); continue; }
          for (let j = -6; j <= -1; j++) carve(i, j, k);
        }
        for (let j = -7; j <= -6; j++) for (let i = -CORRIDOR_HALF; i <= CORRIDOR_HALF - 1; i++) {
          if (i === -1 || i === 0) continue;
          setCell(a, i, j, k, j === -7 ? T_NETHER : T_BEDROCK);
        }
      }
    }
    if (sg.kind === "pool") {
      for (let k = kA; k >= kB; k--) for (let i = -2; i <= 1; i++) {
        carve(i, -1, k); setCell(a, i, -2, k, T_STONE);
      }
    }
    if (sg.kind === "lava") {
      // The seam: a pocket in the right wall, with lava behind iron bars.
      for (let k = kA - 1; k >= kB + 1; k--) for (let j = 0; j <= 2; j++) { carve(3, j, k); carve(4, j, k); }
    }
    if (sg.kind === "deep") {
      for (let k = kA; k >= kB; k--) {
        for (let i = -4; i <= 3; i++) for (let j = -1; j <= 4; j++) {
          if (i >= -3 && i <= 2 && j >= 0 && j <= 3) continue;
          const h = hash(`n${i}|${j}|${k}`) % 100;
          setCell(a, i, j, k, h < 8 ? T_GLOW : (h < 40 ? T_NETHER : cell(a, i, j, k)));
        }
      }
    }
  }
  return a;
}

// Mesh the grid: one BufferGeometry per texture key, faces only where air touches solid.
const FACE_UV = {
  "+x": (k, j, i) => [k, j], "-x": (k, j, i) => [-k, j],
  "+y": (k, j, i) => [i, k], "-y": (k, j, i) => [i, -k],
  "+z": (k, j, i) => [i, j], "-z": (k, j, i) => [-i, j]
};
const TEX_OF = {
  [T_STONE]: ["stone.png"], [T_COBBLE]: ["cobblestone.png"], [T_MOSSY]: ["cobblestone_mossy.png"],
  [T_BRICK]: ["stonebrick.png"], [T_BRICK_MOSSY]: ["stonebrick_mossy.png"], [T_BRICK_CRACK]: ["stonebrick_cracked.png"],
  [T_GRAVEL_FLOOR]: ["stone.png", "gravel.png"], [T_COAL]: ["stone.png", null, "coal_ore.png"], [T_IRON]: ["stone.png", null, "iron_ore.png"],
  [T_OBS]: ["obsidian.png"], [T_BEDROCK]: ["bedrock.png"], [T_NETHER]: ["netherrack.png"], [T_GLOW]: ["glowstone.png"],
  [T_BRIDGE]: ["stonebrick.png"]
};
export function meshGrid(a, images, { shadows = true } = {}) {
  const group = new THREE.Group();
  const bins = new Map();
  const bin = (file) => {
    if (!bins.has(file)) bins.set(file, { pos: [], nor: [], uv: [] });
    return bins.get(file);
  };
  const dirs = [[1, 0, 0, "+x"], [-1, 0, 0, "-x"], [0, 1, 0, "+y"], [0, -1, 0, "-y"], [0, 0, 1, "+z"], [0, 0, -1, "-z"]];
  for (let k = a.k0; k <= a.k0 + a.NK - 1; k++) for (let j = a.j0; j < a.j0 + a.NJ; j++) for (let i = a.i0; i < a.i0 + a.NI; i++) {
    const t = cell(a, i, j, k);
    if (!t || t === T_WATER) continue;
    const names = TEX_OF[t] || ["stone.png"];
    for (const [di, dj, dk, dir] of dirs) {
      const ni = i + di, nj = j + dj, nk = k + dk;
      if (ni < a.i0 || ni >= a.i0 + a.NI || nj < a.j0 || nj >= a.j0 + a.NJ || nk < a.k0 || nk >= a.k0 + a.NK) continue;
      if (cell(a, ni, nj, nk) !== T_AIR) continue;
      // Which face: top = +y gets names[1] (the gravel), the ore sides get names[2].
      let file = names[0];
      if (dir === "+y" && names[1]) file = names[1];
      if (names[2] && dir !== "+y" && dir !== "-y") file = names[2];
      if (!file) file = names[0];
      if (dir === "+y" && t === T_GRAVEL_FLOOR) file = "gravel.png";
      const b = bin(file);
      // The cell spans x in [i, i+1], y in [j, j+1], z in [k, k+1]. The walk goes toward -z (deeper rows
      // have smaller k), so a face toward a row at k+1 sits at z+1 and faces +z.
      const x = i, y = j, z = k;
      let quad, want;
      if (di) {
        const cx = di > 0 ? x + 1 : x;
        quad = [[cx, y, z], [cx, y + 1, z], [cx, y + 1, z + 1], [cx, y, z + 1]];
        want = [di, 0, 0];
      } else if (dj) {
        const cy = dj > 0 ? y + 1 : y;
        quad = [[x, cy, z], [x + 1, cy, z], [x + 1, cy, z + 1], [x, cy, z + 1]];
        want = [0, dj, 0];
      } else {
        const cz = dk > 0 ? z + 1 : z;
        quad = [[x, y, cz], [x + 1, y, cz], [x + 1, y + 1, cz], [x, y + 1, cz]];
        want = [0, 0, dk];
      }
      // Make the winding face outward.
      const e1 = [quad[1][0] - quad[0][0], quad[1][1] - quad[0][1], quad[1][2] - quad[0][2]];
      const e2 = [quad[2][0] - quad[0][0], quad[2][1] - quad[0][1], quad[2][2] - quad[0][2]];
      const cr = [e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]];
      const sgn = cr[0] * want[0] + cr[1] * want[1] + cr[2] * want[2];
      const order = sgn >= 0 ? [0, 1, 2, 0, 2, 3] : [0, 2, 1, 0, 3, 2];
      const uvf = FACE_UV[dir];
      for (const q of order) {
        const [px, py, pz] = quad[q];
        b.pos.push(px, py, pz);
        b.nor.push(...want);
        // Texture coordinates in block units: one tile per block.
        const uu = dir[1] === "x" ? (dir[0] === "+" ? -pz : pz) : dir[1] === "y" ? px : px;
        const vv = dir[1] === "y" ? pz : py;
        b.uv.push(uu, vv);
        void uvf;
      }
    }
  }
  const mats = [];
  for (const [file, b] of bins) {
    const img = images[file.replace(/\.png$/, "")];
    if (!img) continue;
    const tex = new THREE.Texture(img);
    tex.colorSpace = THREE.SRGBColorSpace;
    tex.magFilter = THREE.NearestFilter; tex.minFilter = THREE.NearestFilter;
    tex.wrapS = tex.wrapT = THREE.RepeatWrapping; tex.generateMipmaps = false; tex.needsUpdate = true;
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute(b.pos, 3));
    g.setAttribute("normal", new THREE.Float32BufferAttribute(b.nor, 3));
    g.setAttribute("uv", new THREE.Float32BufferAttribute(b.uv, 2));
    const m = new THREE.Mesh(g, new THREE.MeshLambertMaterial({ map: tex }));
    m.castShadow = shadows; m.receiveShadow = true;
    group.add(m); mats.push(tex, g, m);
  }
  return { group, disposables: mats };
}

// World z of the centre of grid row k. The walk goes toward -z: deeper rows have smaller k and smaller z.
export const worldZ = (k) => k + 0.5;

// Torches are placed beside each alcove, on the corridor side of the wall, and at the entrance.
// Each torch stands on the corridor face of its alcove's pillar, level with the alcove's mouth.
export function torchSpots(lay) {
  const out = [];
  for (const s of lay.slots) {
    out.push({ x: s.side * 1.5, y: 2.15, z: worldZ(s.k), side: s.side, slot: s.i, live: true });
  }
  out.push({ x: -1.5, y: 2.15, z: worldZ(lay.kStart - 2), side: -1, slot: -1, live: true });
  out.push({ x: 1.5, y: 2.15, z: worldZ(lay.kStart - 2), side: 1, slot: -1, live: true });
  return out;
}

export function alcoveFor(lay, s) {
  return { x: s.side * 4.15, y: 0, z: worldZ(s.k), rot: s.side * Math.PI / 2 };
}

// The camera's path: the same as the gallery's centre, swaying a block either side.
export function pathCurve(lay) {
  const pts = [];
  const z0 = worldZ(lay.kStart - 0.5), z1 = worldZ(lay.kEnd + 1);
  for (let z = z0; z >= z1; z -= 1.5) pts.push(new THREE.Vector3(0.85 * Math.sin(-z / 17), 1.5, z));
  pts.push(new THREE.Vector3(0.85 * Math.sin(-z1 / 17), 1.5, z1));
  return new THREE.CatmullRomCurve3(pts, false, "centripetal");
}

// Sky: the shattered violet sky above the ceiling, and god-rays down through each hole.
export function skyObjects(lay, skyTex, rayTex, floorTex = rayTex) {
  const g = new THREE.Group();
  const sky = new THREE.Mesh(new THREE.PlaneGeometry(260, 260), new THREE.MeshBasicMaterial({ map: skyTex, fog: false, depthWrite: false }));
  sky.rotation.x = Math.PI / 2; sky.position.set(0, 42, -60);
  g.add(sky);
  for (const hk of lay.holes) {
    for (let r = 0; r < 3; r++) {
      const ray = new THREE.Mesh(new THREE.PlaneGeometry(1.6 + r * 0.7, 9.5),
        new THREE.MeshBasicMaterial({ map: rayTex, transparent: true, opacity: 0.2 - r * 0.05, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide, fog: true, color: new THREE.Color(0.9, 0.8, 1.0) }));
      ray.position.set((r - 1) * 0.9, 2.6, worldZ(hk));
      ray.rotation.z = (r - 1) * 0.12; ray.rotation.x = 0.08;
      g.add(ray);
    }
    // The lavender that falls through the crack, pooled on the stone-brick floor under it.
    const pool = new THREE.Mesh(new THREE.CircleGeometry(2.4, 32),
      new THREE.MeshBasicMaterial({ map: floorTex, transparent: true, opacity: 0.55, blending: THREE.AdditiveBlending, depthWrite: false, fog: true, color: new THREE.Color(0.85, 0.7, 1.0) }));
    pool.rotation.x = -Math.PI / 2; pool.position.set(0, 0.04, worldZ(hk));
    g.add(pool);
    // Roots coming through the ceiling around the hole.
    const rr = rng(hash("roots" + hk));
    for (let n = 0; n < 4; n++) {
      const len = 1.2 + rr() * 1.8;
      const root = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.07, len, 5),
        new THREE.MeshLambertMaterial({ color: 0x3f2a1b }));
      root.position.set((rr() - 0.5) * 2.2, 4 - len / 2, worldZ(hk) + (rr() - 0.5) * 2.2);
      root.rotation.set((rr() - 0.5) * 0.5, 0, (rr() - 0.5) * 0.6);
      g.add(root);
    }
  }
  return g;
}

// Set-piece dressing: rails and fence posts in the mineshaft, cobwebs, vines, the bars and lava of the seam,
// the water of the pool. The walls are the grid; these are the decor on it.
export function dressing(lay, images, { planeTex }) {
  const g = new THREE.Group();
  const r = rng(hash("dress"));
  const mk = (tex, w, h, x, y, z, ry = 0, rx = 0, opts = {}) => {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshLambertMaterial({ map: tex, alphaTest: 0.5, side: THREE.DoubleSide, ...opts }));
    m.position.set(x, y, z); m.rotation.set(rx, ry, 0); g.add(m);
    return m;
  };
  const { lava, bars, web, vine, rail, water } = planeTex;
  for (const sg of lay.segs) {
    const zc = worldZ((sg.k0 + sg.k1) / 2);
    if (sg.kind === "mineshaft") {
      // Rails along the floor, fence posts (logs) on both sides, a collapse of gravel.
      for (let z = sg.k0; z >= sg.k1; z -= 1) {
        const m = mk(rail, 1, 1, 0, 0.02, worldZ(z), 0, -Math.PI / 2, { alphaTest: 0.3 });
        m.rotation.z = Math.PI / 2;   // the rail texture runs along the corridor
      }
      for (let z = sg.k0; z >= sg.k1; z -= 2) {
        for (const x of [-2.6, 2.6]) {
          const post = new THREE.Mesh(new THREE.BoxGeometry(0.22, 3.1, 0.22), new THREE.MeshLambertMaterial({ color: 0x6b4b2e }));
          post.position.set(x, 1.55, worldZ(z)); post.castShadow = true; g.add(post);
          const beam = new THREE.Mesh(new THREE.BoxGeometry(5.4, 0.22, 0.22), new THREE.MeshLambertMaterial({ color: 0x6b4b2e }));
          beam.position.set(0, 3.2, worldZ(z)); beam.castShadow = true;
          if (x > 0) g.add(beam);
        }
      }
      for (let n = 0; n < 9; n++) {
        const gr = new THREE.Mesh(new THREE.BoxGeometry(0.7, 0.7, 0.7), new THREE.MeshLambertMaterial({ color: 0x7d7a76 }));
        gr.position.set((r() - 0.5) * 4, 0.35, zc + (r() - 0.5) * 6);
        gr.castShadow = true; g.add(gr);
      }
    }
    if (sg.kind === "lava") {
      // Iron bars across the pocket mouth, lava behind.
      const zl = worldZ((sg.k0 + sg.k1) / 2);
      mk(bars, 5.2, 2.6, 3.35, 1.4, zl, Math.PI / 2, 0, { color: 0xffffff });
      const lt = lava.clone(); lt.repeat.set(5, 2.6 / 20); lt.needsUpdate = true;
      const L = new THREE.Mesh(new THREE.PlaneGeometry(5, 2.6), new THREE.MeshBasicMaterial({ map: lt, color: new THREE.Color(1.6, 0.8, 0.35), side: THREE.DoubleSide }));
      L.position.set(4.8, 1.3, zl); L.rotation.y = Math.PI / 2; g.add(L);
      g.userData.lavaTex = lt;
    }
    if (sg.kind === "pool") {
      const wt = water.clone(); wt.repeat.set(1, 1 / 32); wt.needsUpdate = true;
      const W = new THREE.Mesh(new THREE.PlaneGeometry(4.6, Math.abs(sg.k0 - sg.k1)),
        new THREE.MeshLambertMaterial({ map: wt, transparent: true, opacity: 0.62, color: 0x5d8799 }));
      W.rotation.x = -Math.PI / 2; W.position.set(-0.5, -0.4, worldZ((sg.k0 + sg.k1) / 2)); g.add(W);
      g.userData.waterTex = wt;
    }
  }
  // Cobwebs in the top corners, and vines hanging from the walls.
  for (const s of lay.slots) {
    if (s.i % 2 === 0) {
      mk(web, 1.2, 1.2, s.side * 1.95, 3.4, worldZ(s.k) + 1.4, s.side * Math.PI / 2);
    }
    mk(vine, 1.0, 1.4, s.side * 1.97, 2.3, worldZ(s.k) - 1.6, s.side * Math.PI / 2, 0, { color: 0xffffff });
  }
  for (const sg of lay.segs) {
    for (let n = 0; n < 2; n++) mk(web, 1.6, 1.6, (r() < 0.5 ? -1 : 1) * 2.9, 3.5, worldZ(sg.k0 - 1 - n * 4), r() * 3);
  }
  return g;
}

export function sizeOf(lay) { return Math.abs(lay.kEnd - lay.kStart); }
