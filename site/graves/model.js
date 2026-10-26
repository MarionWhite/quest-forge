// Builds the gravestones and statues from the mod's own cuboids (models.js, from javap) and the pack's
// textures. Model units: 16 per block, y down, feet on y = 24. A root group flips the model upright
// (a half turn about z) and scales it to blocks, so the geometry stays in the mod's coordinates.
import * as THREE from "three";
import { MODELS } from "./models.js";
import { engraveName, weather, statueSkin, canvas, baseCanvas } from "./textures.js";

const FEET = 24;

export function makeTexture(c, { repeat = false, srgb = true } = {}) {
  const t = new THREE.CanvasTexture(c);
  if (srgb) t.colorSpace = THREE.SRGBColorSpace;
  t.generateMipmaps = true;
  t.minFilter = THREE.LinearMipmapLinearFilter;
  t.magFilter = THREE.LinearFilter;
  t.anisotropy = 4;
  if (repeat) { t.wrapS = t.wrapT = THREE.RepeatWrapping; }
  return t;
}
export function imageTexture(img, { nearest = true, repeat = false } = {}) {
  const t = new THREE.Texture(img);
  t.colorSpace = THREE.SRGBColorSpace;
  t.magFilter = nearest ? THREE.NearestFilter : THREE.LinearFilter;
  t.minFilter = nearest ? THREE.NearestFilter : THREE.LinearFilter;
  t.generateMipmaps = false;
  if (repeat) t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.needsUpdate = true;
  return t;
}

// ---- geometry accumulator --------------------------------------------------------------------
function acc() { return { pos: [], nor: [], uv: [] }; }
const _p = new THREE.Vector3(), _n = new THREE.Vector3();

// One box, in bone space, transformed by matrix m into model space. The mod's UV layout:
// right (-x) at (u, v+d), front (-z) at (u+d, v+d), left (+x) at (u+d+w, v+d), back (+z) at (u+2d+w, v+d),
// top (-y) at (u+d, v) and bottom (+y) at (u+d+w, v), each face sized from the box.
function addBox(a, box, u, v, tw, th, m, { inflate = 0, fullFront = false } = {}) {
  if (!box) return;   // a bone the mod only positions, with no cuboid
  const [bx, by, bz, bw, bh, bd] = box;
  const x0 = bx - inflate, x1 = bx + bw + inflate, y0 = by - inflate, y1 = by + bh + inflate;
  const z0 = bz - inflate, z1 = bz + bd + inflate;
  const w = x1 - x0, h = y1 - y0, d = z1 - z0;
  const faces = [
    { n: [-1, 0, 0], c: (s, t) => [x0, y0 + t * h, z0 + s * d], r: [u, v + d, d, h] },
    { n: [1, 0, 0], c: (s, t) => [x1, y0 + t * h, z0 + s * d], r: [u + d + w, v + d, d, h] },
    { n: [0, -1, 0], c: (s, t) => [x0 + s * w, y0, z0 + t * d], r: [u + d, v, w, d] },
    { n: [0, 1, 0], c: (s, t) => [x0 + s * w, y1, z0 + t * d], r: [u + d + w, v, w, d] },
    { n: [0, 0, -1], c: (s, t) => [x0 + s * w, y0 + t * h, z0], r: [u + d, v + d, w, h], front: true },
    { n: [0, 0, 1], c: (s, t) => [x0 + s * w, y0 + t * h, z1], r: [u + 2 * d + w, v + d, w, h] }
  ];
  const K = [[0, 0], [1, 0], [1, 1], [0, 1]];
  for (const f of faces) {
    const P = [], U = [];
    for (const [s, t] of K) {
      const [x, y, z] = f.c(s, t);
      _p.set(x, y, z).applyMatrix4(m);
      P.push(_p.clone());
      if (fullFront && f.front) U.push([s, 1 - t]);
      else U.push([(f.r[0] + s * f.r[2]) / tw, 1 - (f.r[1] + t * f.r[3]) / th]);
    }
    _n.set(...f.n).transformDirection(m);
    const e1 = new THREE.Vector3().subVectors(P[1], P[0]), e2 = new THREE.Vector3().subVectors(P[2], P[0]);
    const flip = e1.cross(e2).dot(_n) < 0;
    const order = flip ? [0, 2, 1, 0, 3, 2] : [0, 1, 2, 0, 2, 3];
    for (const k of order) {
      a.pos.push(P[k].x, P[k].y, P[k].z);
      a.nor.push(_n.x, _n.y, _n.z);
      a.uv.push(U[k][0], U[k][1]);
    }
  }
}
// Matrix for a bone: translate to its rotation point after the mod's rotation (MC order: x, then y, then z).
function boneMatrix(piv = [0, 0, 0], rot = [0, 0, 0]) {
  const m = new THREE.Matrix4().makeRotationFromEuler(new THREE.Euler(rot[0], rot[1], rot[2], "ZYX"));
  m.setPosition(piv[0], piv[1], piv[2]);
  return m;
}
function geometryOf(a) {
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(a.pos, 3));
  g.setAttribute("normal", new THREE.Float32BufferAttribute(a.nor, 3));
  g.setAttribute("uv", new THREE.Float32BufferAttribute(a.uv, 2));
  return g;
}
// The root that turns model units into blocks, upright, feet on the ground.
function rootGroup() {
  const r = new THREE.Group();
  r.rotation.z = Math.PI;
  r.position.y = FEET / 16;
  r.scale.setScalar(1 / 16);
  return r;
}

// The family's bones. The mod's stone cross stands its bar in depth (it reads only from the side), so the
// bar is turned to lie across the post and the cross reads from the front.
function bonesOf(family) {
  const M = MODELS[family];
  if (family !== "cross") return M.bones;
  // The post is 3 wide and the bar 12 wide, so the cross reads from the front; the bar is at the post's upper third.
  return M.bones.map((b, i) => {
    if (i === 2) return { ...b, box: [-1.5, 0, -1.5, 3, 14, 3] };
    if (i === 3) return { ...b, box: [-6, -1.5, -1.5, 12, 3, 3], piv: [0, 8, 0], rot: [0, 0, 0] };
    return b;
  });
}

// The tallest point each family is scaled to, in blocks: the slab and the cross about 1.6, the pillar, the knight
// and the angel about 2.2, so the stone is the focal point of its alcove beside a player-height statue.
export const STONE_HEIGHT = { slab: 1.6, wood: 1.6, cross: 1.6, tomb: 1.8, skeleton: 1.8, pillar: 2.2, knight: 2.2, angel: 2.2 };

// Extent of a family in model units: the top (smallest y), the bottom, and the front (smallest z).
export function bounds(bones) {
  const b = { minY: Infinity, maxY: -Infinity, minZ: Infinity, maxZ: -Infinity, minX: Infinity, maxX: -Infinity };
  for (const k of bones) {
    if (!k.box) continue;
    const [x, y, z, w, h, d] = k.box, [px, py, pz] = k.piv;
    b.minY = Math.min(b.minY, py + y); b.maxY = Math.max(b.maxY, py + y + h);
    b.minZ = Math.min(b.minZ, pz + z); b.maxZ = Math.max(b.maxZ, pz + z + d);
    b.minX = Math.min(b.minX, px + x); b.maxX = Math.max(b.maxX, px + x + w);
  }
  return b;
}

// ---- the stone families ----------------------------------------------------------------------
// label = { title: the player's name, sub: the year }. The name goes on the family's own face when the
// model has a wide enough engraving rectangle, and on a plaque set into the front otherwise.
export function buildStone(family, img, g, label, S, seed, ornaments = [], extras = {}) {
  const M = MODELS[family];
  const bones = bonesOf(family);
  const B = bounds(bones);
  if (family === "cross") { B.minZ = -1.5; B.plaqueY = 8; B.plaqueW = 5; }   // the plaque goes on the crossing, in front of the post
  // Scale the family so its top is at its target height, about the feet on the ground.
  const sc = 16 * (STONE_HEIGHT[family] || 1.8) / (FEET - B.minY);
  const c = canvas(S, S), x = c.getContext("2d");
  x.imageSmoothingEnabled = false;
  x.drawImage(img, 0, 0, S, S);
  weather(x, S, seed);
  if (ornaments.includes("scorch")) {
    const g2 = x.createRadialGradient(S * .5, S * .45, 2, S * .5, S * .45, S * .42);
    g2.addColorStop(0, "rgba(10,8,8,0.5)"); g2.addColorStop(0.5, "rgba(20,14,12,0.2)"); g2.addColorStop(1, "rgba(20,14,12,0)");
    x.fillStyle = g2; x.fillRect(0, 0, S, S);
  }
  const onFace = !!(M.engrave && M.engrave[2] >= 10 && label);
  if (onFace) engraveName(x, S, M.tw, M.th, M.engrave, label.title, label.sub, seed);
  const tex = makeTexture(c);
  const root = rootGroup();
  root.scale.setScalar(sc / 16);
  root.position.y = (FEET / 16) * sc;
  // A two-step base under the stone: a wide course on the ground and a narrower one on it.
  const base = acc();
  const w1 = [B.minX - 1, 22, B.minZ - 1, B.maxX - B.minX + 2, 2, B.maxZ - B.minZ + 2];
  const w2 = [B.minX + 1, 20, B.minZ + 1, B.maxX - B.minX - 2, 2, B.maxZ - B.minZ - 2];
  addBox(base, w1, 0, 0, 1, 1, new THREE.Matrix4());
  addBox(base, w2, 0, 0, 1, 1, new THREE.Matrix4());
  const baseMesh = new THREE.Mesh(geometryOf(base), new THREE.MeshLambertMaterial({ color: 0x6d6f74 }));
  baseMesh.castShadow = true; baseMesh.receiveShadow = true;
  root.add(baseMesh);
  const a = acc();
  for (const b of bones) addBox(a, b.box, b.u, b.v, M.tw, M.th, boneMatrix(b.piv, b.rot));
  const mat = new THREE.MeshLambertMaterial({ map: tex, color: new THREE.Color(1.3, 1.28, 1.25) });
  const mesh = new THREE.Mesh(geometryOf(a), mat);
  mesh.castShadow = true; mesh.receiveShadow = true;
  root.add(mesh);
  const out = { root, textures: [tex], meshes: [mesh, baseMesh], canvas: c, ...extras };
  if (!onFace && label) addPlaque(root, out, B, label, seed);
  for (const o of ornaments) addOrnament(o, root, out, seed, { ...M, ...B, topY: B.minY, frontZ: B.minZ, midZ: (B.minZ + B.maxZ) / 2 });
  return out;
}

// A plaque set into the front of the stone, carrying the name and year.
function addPlaque(root, out, B, label, seed) {
  const pc = canvas(256, 256), px = pc.getContext("2d");
  px.fillStyle = "#6f7377"; px.fillRect(0, 0, 256, 256);
  weather(px, 256, seed + 7);
  engraveName(px, 256, 1, 1, [0.08, 0.1, 0.84, 0.8], label.title, label.sub, seed);
  const ptex = makeTexture(pc);
  const w = B.plaqueW ?? 6.4, h = B.plaqueW ? 4.6 : 6.8, cy = B.plaqueY ?? (B.minY + (B.maxY - B.minY) * 0.42);
  const pa = acc();
  addBox(pa, [-w / 2, cy - h / 2, B.minZ - 0.7, w, h, 0.7], 0, 0, 1, 1, new THREE.Matrix4(), { fullFront: true });
  const pm = new THREE.Mesh(geometryOf(pa), new THREE.MeshLambertMaterial({ map: ptex }));
  pm.castShadow = true;
  root.add(pm);
  out.textures.push(ptex); out.meshes.push(pm);
}

// ---- ornaments ------------------------------------------------------------------------------
function plainMesh(geom, color, opts = {}) {
  const m = new THREE.MeshLambertMaterial({ color, ...opts });
  const mesh = new THREE.Mesh(geom, m);
  mesh.castShadow = true;
  return mesh;
}
function place(mesh, x, y, z, rx = 0, ry = 0, rz = 0) {
  mesh.position.set(x, y, z); mesh.rotation.set(rx, ry, rz); return mesh;
}
function ground(geom, color, opts, x, z) {
  const m = new THREE.Mesh(geom, new THREE.MeshLambertMaterial({ color, ...opts }));
  m.rotation.x = -Math.PI / 2; m.position.set(x, FEET - 0.05, z);
  return m;
}

// The ornaments are built in model units, so they sit in the root with the stone. Y 24 is the ground,
// M.topY is the top of the stone, M.frontZ its front face (the path side) and M.midZ its middle.
function addOrnament(o, root, out, seed, M) {
  if (o === "anvil") {
    // An anvil resting on the top of the stone, built from the vanilla anvil's three parts.
    const g = new THREE.Group();
    const base = plainMesh(new THREE.BoxGeometry(8, 3, 6), 0x3a3d40);
    const waist = plainMesh(new THREE.BoxGeometry(5, 3, 4), 0x383b3e);
    const top = plainMesh(new THREE.BoxGeometry(13, 3, 7), 0x44484c);
    const t = M.topY, z = M.midZ;
    place(base, 0, t - 1.5, z); place(waist, 0, t - 4.5, z); place(top, -0.6, t - 7.5, z);
    g.add(base, waist, top);
    root.add(g); out.meshes.push(base, waist, top);
  }
  if (o === "arrow") {
    // An arrow shot into the front face: the head is in the stone, the shaft and fletching stick out
    // at a slant towards the path, so it reads as an arrow from the front.
    const g = new THREE.Group();
    g.position.set((M.minX + M.maxX) / 2 + 2.5, M.minY + (M.maxY - M.minY) * 0.35, M.frontZ);
    g.rotation.x = -0.6;
    const head = plainMesh(new THREE.ConeGeometry(0.9, 1.8, 6), 0x9ea3a8);
    head.rotation.x = Math.PI / 2; head.position.set(0, 0, -0.6);
    const shaft = plainMesh(new THREE.BoxGeometry(0.5, 0.5, 8), 0x8a6a45);
    shaft.position.set(0, 0, -5.2);
    const f1 = plainMesh(new THREE.BoxGeometry(0.12, 2.0, 1.5), 0xb0443a);
    const f2 = plainMesh(new THREE.BoxGeometry(0.12, 1.5, 2.0), 0xb0443a);
    f1.position.set(0, 0, -8.9); f2.position.set(0, 0, -8.9);
    g.add(head, shaft, f1, f2);
    root.add(g); out.meshes.push(head, shaft, f1, f2);
  }
  if (o === "lava") {
    // A lava pool at the foot of the stone, and a warm glow on the stone.
    const lava = imageTexture(out.lavaImg, { nearest: true, repeat: true });
    lava.repeat.set(1, 1 / 20);
    const m = new THREE.Mesh(new THREE.PlaneGeometry(4.6, 4.6), new THREE.MeshBasicMaterial({ map: lava, color: new THREE.Color(1.4, 1.1, 0.9) }));
    m.rotation.x = -Math.PI / 2; m.position.set(0, FEET - 0.05, M.frontZ - 2.5);
    root.add(m); out.meshes.push(m); out.lava = lava;
  }
  if (o === "puddle") {
    const w = ground(new THREE.CircleGeometry(3.0, 24), 0x2c5a66, { transparent: true, opacity: 0.8 }, 1.5, M.frontZ - 2.5);
    root.add(w); out.meshes.push(w);
    if (out.lilyImg) {
      const lt = imageTexture(out.lilyImg, { nearest: true });
      const l = new THREE.Mesh(new THREE.PlaneGeometry(2.4, 2.4), new THREE.MeshLambertMaterial({ map: lt, transparent: true, alphaTest: 0.5, side: THREE.DoubleSide }));
      l.rotation.x = -Math.PI / 2; l.rotation.z = 0.5; l.position.set(2.2, FEET - 0.02, M.frontZ - 2.1);
      root.add(l); out.meshes.push(l); out.textures.push(lt);
    }
  }
  if (o === "scorch") {
    // A dark scorch on the ground in front of the stone, fading out at the edge.
    const c = canvas(128, 128), x = c.getContext("2d");
    const grd = x.createRadialGradient(64, 64, 6, 64, 64, 64);
    grd.addColorStop(0, "rgba(8,6,6,0.9)"); grd.addColorStop(0.6, "rgba(20,14,12,0.55)"); grd.addColorStop(1, "rgba(20,14,12,0)");
    x.fillStyle = grd; x.fillRect(0, 0, 128, 128);
    const t = makeTexture(c);
    const m = new THREE.Mesh(new THREE.PlaneGeometry(7, 7), new THREE.MeshBasicMaterial({ map: t, transparent: true, depthWrite: false }));
    m.rotation.x = -Math.PI / 2; m.position.set(0, FEET - 0.1, M.frontZ - 1.6);
    root.add(m); out.textures.push(t); out.meshes.push(m);
  }
  if (o === "cracked") {
    // The top of the stone broke off and lies beside it.
    const piece = plainMesh(new THREE.BoxGeometry(5, 3.6, 2.2), 0x7b8084);
    place(piece, -4.5, FEET - 1.8, M.frontZ - 1.2, 0, 0.4, 0.1);
    root.add(piece); out.meshes.push(piece);
  }
  if (o === "bowl") {
    // The empty bowl at the foot of the stone, lathed.
    const pts = [];
    for (let i = 0; i <= 8; i++) { const t = i / 8; pts.push(new THREE.Vector2(2.6 * Math.sin(t * Math.PI / 2) + 0.2, -(1.6 * (1 - t) * (1 - t)))); }
    const bowl = plainMesh(new THREE.LatheGeometry(pts, 14), 0x8f9499, { side: THREE.DoubleSide });
    place(bowl, 3.2, FEET - 0.2, M.frontZ - 1.6);
    root.add(bowl); out.meshes.push(bowl);
  }
  if (o === "nametag") {
    // A brass-grey tag hung from the top corner, with the killer's name on it.
    const t = canvas(256, 96), x = t.getContext("2d");
    x.fillStyle = "#c8c3b0"; x.fillRect(0, 0, 256, 96);
    x.strokeStyle = "#5b5540"; x.lineWidth = 6; x.strokeRect(6, 6, 244, 84);
    x.fillStyle = "#2b2a22"; x.font = "bold 34px Georgia, serif"; x.textAlign = "center";
    x.fillText(out.killerName || "", 128, 60);
    const tt = makeTexture(t);
    const m = new THREE.Mesh(new THREE.PlaneGeometry(4.2, 1.6), new THREE.MeshLambertMaterial({ map: tt, side: THREE.DoubleSide }));
    m.position.set(M.maxX - 1.5, M.minY + 2.5, M.frontZ - 0.6); m.rotation.z = 0.12;
    root.add(m); out.meshes.push(m); out.textures.push(tt);
  }
}

// ---- the statues: the vanilla ModelBiped rig ---------------------------------------------------
// Each part is rotated about its own rotation point, as the vanilla renderer does, and never moved on its own.
// The whole figure is lowered (drop) and the whole root tilted about the feet (tilt), which is the kneel.
// Units: the figure stands on a plinth 4 units high, so its feet sit at y = 20 (lift -4).
const BIPED = {
  head: { box: [-4, -8, -4, 8, 8, 8], uv: [0, 0], piv: [0, 0, 0] },
  hat: { box: [-4, -8, -4, 8, 8, 8], uv: [32, 0], piv: [0, 0, 0] },
  body: { box: [-4, 0, -2, 8, 12, 4], uv: [16, 16], piv: [0, 0, 0] },
  jacket: { box: [-4, 0, -2, 8, 12, 4], uv: [16, 32], piv: [0, 0, 0] },
  rarm: { box: [-3, -2, -2, 4, 12, 4], uv: [40, 16], piv: [-5, 2, 0] },
  larm: { box: [-1, -2, -2, 4, 12, 4], uv: [32, 48], piv: [5, 2, 0] },
  rleg: { box: [-2, 0, -2, 4, 12, 4], uv: [0, 16], piv: [-1.9, 12, 0] },
  lleg: { box: [-2, 0, -2, 4, 12, 4], uv: [16, 48], piv: [1.9, 12, 0] }
};
const HALF_PI = Math.PI / 2;
// Angles in radians. Negative x swings a limb forward (toward the front, -z); positive x swings legs back.
// lift: the figure's height on the plinth; drop: lowering in model units; tilt: the root's forward lean.
export const POSES = {
  // Knees on the plinth: the legs turn back 90 degrees at the hip and the figure is lowered until the legs (4 units
  // thick) rest on the plinth's top at y = 20. The torso stays upright, the head is bowed, the hands are on the thighs.
  kneel: { lift: 0, drop: 4.8, head: 0.55, body: 0, rarm: [0.5, 0, -0.1], larm: [0.5, 0, 0.1], rleg: [HALF_PI, 0, 0], lleg: [HALF_PI, 0, 0] },
  pick: { lift: -4, head: 0.1, body: 0.05, rarm: [-2.7, 0, -0.3], larm: [-0.3, 0, 0.1], rleg: [0, 0, 0], lleg: [0, 0, 0], pick: true },
  arms: { lift: -4, head: -0.25, body: -0.05, rarm: [-Math.PI, 0, -0.1], larm: [-Math.PI, 0, 0.1], rleg: [0, 0, 0], lleg: [0, 0, 0] },
  flat: { lying: true, head: 0, rarm: [0, 0, 1.4], larm: [0, 0, -1.4], rleg: [0, 0, 0.15], lleg: [0, 0, -0.15] },
  shield: { lift: -4, head: 0.3, body: 0.1, rarm: [-1.6, 0, 0.7], larm: [-1.6, 0, -0.7], rleg: [0, 0, 0], lleg: [0, 0, 0] },
  angel: { lift: -4, head: 0.15, body: 0, rarm: [-1.9, 0, 0.45], larm: [-1.9, 0, -0.45], rleg: [0, 0, 0], lleg: [0, 0, 0] }
};

const bone = (piv, rot) => {
  const m = new THREE.Matrix4().makeRotationFromEuler(new THREE.Euler(rot[0] || 0, rot[1] || 0, rot[2] || 0, "ZYX"));
  return new THREE.Matrix4().makeTranslation(piv[0], piv[1], piv[2]).multiply(m);
};
// The cool stone tint: the statues read as a different stone from the warm floor.
const STATUE_TINT = new THREE.Color(0.84, 0.92, 1.06);
const STATUE_EMIT = 0x2a3440;

// The statue is exactly player height: 2 blocks of model at 0.9 scale, 1.8 blocks, about the feet.
export function buildStatue(pose, skinCanvas, { wings = false, scale = 0.9 } = {}) {
  const P = POSES[pose] || POSES.kneel;
  const root = rootGroup();
  const tex = makeTexture(skinCanvas);
  const pivot = new THREE.Group();          // turns about the feet, so the tilt and scale keep the feet in place
  pivot.position.set(0, FEET, 0);
  pivot.rotation.x = P.tilt || 0;
  pivot.scale.setScalar(scale);
  const figure = new THREE.Group();
  // The offset is divided by the scale, so the feet stay at lift + drop above the pivot whatever the scale.
  figure.position.y = -FEET + ((P.lift ?? -4) + (P.drop || 0)) / scale;
  if (P.lying) {
    // Fallen on its back: turned about the feet, with the back on the ground (the pivot sits 2 units up from the
    // feet's line so the back touches y = 24).
    pivot.position.set(0, 22, 0);
    pivot.rotation.x = -HALF_PI;
    figure.position.y = 0;
  }
  pivot.add(figure);
  root.add(pivot);
  const M = {
    head: bone(BIPED.head.piv, [P.head || 0, 0, 0]),
    body: bone(BIPED.body.piv, [P.body || 0, 0, 0]),
    rarm: bone(BIPED.rarm.piv, P.rarm || [0, 0, 0]),
    larm: bone(BIPED.larm.piv, P.larm || [0, 0, 0]),
    rleg: bone(BIPED.rleg.piv, P.rleg || [0, 0, 0]),
    lleg: bone(BIPED.lleg.piv, P.lleg || [0, 0, 0])
  };
  const skin = acc(), jacket = acc(), props = acc();
  addBox(skin, BIPED.head.box, 0, 0, 64, 64, M.head);
  addBox(skin, BIPED.body.box, 16, 16, 64, 64, M.body);
  addBox(skin, BIPED.rarm.box, 40, 16, 64, 64, M.rarm);
  addBox(skin, BIPED.larm.box, 32, 48, 64, 64, M.larm);
  addBox(skin, BIPED.rleg.box, 0, 16, 64, 64, M.rleg);
  addBox(skin, BIPED.lleg.box, 16, 48, 64, 64, M.lleg);
  addBox(jacket, BIPED.hat.box, 32, 0, 64, 64, M.head, { inflate: 0.5 });
  addBox(jacket, BIPED.jacket.box, 16, 32, 64, 64, M.body, { inflate: 0.25 });
  if (P.pick) {
    // A pickaxe in the raised right hand: a wooden handle and a stone head.
    addBox(props, [-3.5, 8, -0.6, 1, 11, 1], 0, 0, 16, 16, M.rarm);
    addBox(props, [-6.5, 6.5, -1, 7, 1.6, 2], 0, 0, 16, 16, M.rarm);
  }
  const stoneOpts = { map: tex, alphaTest: 0.4, side: THREE.DoubleSide, color: STATUE_TINT, emissive: new THREE.Color(STATUE_EMIT) };
  const skinMesh = new THREE.Mesh(geometryOf(skin), new THREE.MeshLambertMaterial(stoneOpts));
  const jacketMesh = new THREE.Mesh(geometryOf(jacket), new THREE.MeshLambertMaterial(stoneOpts));
  skinMesh.castShadow = true; jacketMesh.castShadow = true;
  figure.add(skinMesh, jacketMesh);
  const meshes = [skinMesh, jacketMesh];
  const textures = [tex];
  if (props.pos.length) {
    const pt = makeTexture(propCanvas());
    const pm = new THREE.Mesh(geometryOf(props), new THREE.MeshLambertMaterial({ map: pt }));
    figure.add(pm); meshes.push(pm); textures.push(pt);
  }
  if (wings) {
    // Two flat wing planes behind the shoulders, feathered stone.
    const wt = makeTexture(wingCanvas());
    const wmat = new THREE.MeshLambertMaterial({ map: wt, side: THREE.DoubleSide, emissive: new THREE.Color(0x1a2430) });
    for (const s of [-1, 1]) {
      const w = new THREE.Mesh(new THREE.PlaneGeometry(9, 16), wmat);
      w.position.set(s * 8, -5, 3.5);
      w.rotation.y = -s * 0.35;
      w.castShadow = true;
      figure.add(w); meshes.push(w);
    }
    textures.push(wt);
  }
  // A plinth under the figure. Lying figures lie on the ground with no plinth.
  if (!P.lying) {
    const pl = acc();
    addBox(pl, [-6, 20, -4, 12, 4, 8], 0, 0, 1, 1, new THREE.Matrix4());
    const plinth = new THREE.Mesh(geometryOf(pl), new THREE.MeshLambertMaterial({ color: 0x7d8088 }));
    plinth.castShadow = true; plinth.receiveShadow = true;
    root.add(plinth); meshes.push(plinth);
  }
  return { root, meshes, textures };
}

// The Weeping Angel: the plain skin in greyscale, with stone folds drawn on the body and arms, the hands
// over the eyes, two wing planes, slightly larger than a player, and a faint cold edge.
export function buildAngelFigure(img) {
  const c = statueSkin(img, 512), x = c.getContext("2d"), u = 8;
  x.save();
  x.strokeStyle = "rgba(38,42,50,0.45)"; x.lineWidth = 2;
  for (let n = 0; n < 6; n++) {
    x.beginPath(); x.moveTo((17 + n * 2.4) * u, 16 * u);
    x.quadraticCurveTo((23 + n * 2.4) * u, 24 * u, (18 + n * 2.4) * u, 32 * u); x.stroke();
  }
  x.restore();
  return buildStatue("angel", c, { wings: true, scale: 0.95 });
}
// The feathered stone of a wing: rows of feather arcs and fold lines, in greyscale.
function wingCanvas() {
  const c = canvas(128, 256), x = c.getContext("2d");
  const g = x.createLinearGradient(0, 0, 0, 256);
  g.addColorStop(0, "#9da2aa"); g.addColorStop(1, "#4d5259");
  x.fillStyle = g; x.fillRect(0, 0, 128, 256);
  x.strokeStyle = "rgba(232,236,242,0.32)"; x.lineWidth = 2;
  for (let row = 0; row < 9; row++) for (let n = 0; n < 4; n++) {
    x.beginPath(); x.arc(16 + n * 32 + (row % 2) * 12, 20 + row * 26, 18, Math.PI * 0.15, Math.PI * 0.85); x.stroke();
  }
  x.strokeStyle = "rgba(20,22,26,0.4)"; x.lineWidth = 2;
  for (let n = 0; n < 6; n++) { x.beginPath(); x.moveTo(n * 22, 0); x.lineTo(n * 22 + 40, 256); x.stroke(); }
  return c;
}
function propCanvas() {
  const c = canvas(16, 16), x = c.getContext("2d");
  x.fillStyle = "#7a6446"; x.fillRect(0, 0, 16, 16);
  x.fillStyle = "#5a4530"; x.fillRect(0, 0, 16, 2); x.fillRect(0, 14, 16, 2);
  x.fillStyle = "#8d8f92"; x.fillRect(4, 4, 8, 8);
  return c;
}

// The skin, in the statue's stone range.
export function statueCanvas(img) { return statueSkin(img, 512); }

// Frees everything the grave built, when it leaves the view.
export function disposeGroup(obj) {
  obj.traverse(o => {
    if (o.geometry) o.geometry.dispose();
    if (o.material) {
      const arr = Array.isArray(o.material) ? o.material : [o.material];
      for (const m of arr) { if (m.map && !m.map.userData?.keep) m.map.dispose(); m.dispose(); }
    }
  });
}
export { baseCanvas };
