// Block models for the structure placer, the falling columns and the reel tiles: one Object3D per
// block, origin at the block's minimum corner, one unit cube. What each block looks like is decided
// by blockdefs.js (the 1.7.10 icon and shape rules); this file turns a spec into meshes.
//
// Every box maps its texture the way RenderBlocks does: a face shows the part of the texture that
// lies at the face's place in the block, so a 14x8x14 cake takes the cake's own pixels and a pane
// shows the middle columns on its edge.
import * as THREE from 'three';
import { tex, animTex } from './stage.js';
import { boxGeometry } from './mobs.js';
import { report } from './fx.js';
import { blockSpec, bare, paneJoins, fenceJoins } from './blockdefs.js';
import { drawMcText, mcTextWidth } from './mcfont.js';

const cache = new Map();
function memo(key, make) { if (!cache.has(key)) cache.set(key, make()); return cache.get(key); }
const T = (file) => tex(file.startsWith('entity/') ? file : 'blocks/' + file);
const L = (file, o = {}) => memo('L' + file + JSON.stringify(o), () => new THREE.MeshLambertMaterial({ map: T(file), ...o }));
const HIDDEN = () => memo('hidden', () => new THREE.MeshBasicMaterial({ visible: false }));

function canvasTex(w, h, draw) {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  draw(c.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.magFilter = THREE.NearestFilter;
  t.minFilter = THREE.NearestFilter;
  t.generateMipmaps = false;
  return t;
}
const torchTex = () => memo('torchtex', () => canvasTex(8, 8, (g) => {
  const grd = g.createRadialGradient(4, 4, 0, 4, 5, 4);
  grd.addColorStop(0, '#fff3b0'); grd.addColorStop(0.5, '#ffb030'); grd.addColorStop(1, 'rgba(255,90,20,0)');
  g.fillStyle = grd; g.fillRect(0, 0, 8, 8);
}));

// The sign text, as TileEntitySignRenderer draws it: the board is 90 x 45 font pixels, line i sits at
// y = i*10 - 20 (four lines), each centred, black, in the default bitmap font. Returns a texture
// with the text only (the planks come from the board); 4 canvas pixels per font pixel.
export function signTexture(lines) {
  const px = 4;
  return canvasTex(90 * px, 45 * px, (g, w, h) => {
    const ls = (lines || []).slice(0, 4).map((s) => String(s || ''));
    ls.forEach((s, i) => { if (s) drawMcText(g, s, w / 2 - (mcTextWidth(s) * px) / 2, h / 2 + (i * 10 - 20) * px, '#000000', px); });
  });
}

// A box between two corners (block units) with the 1.7.10 position-based UVs. `mats` is one
// material or the six in BoxGeometry order (east, west, top, bottom, south, north). `uv` can set a
// face's pixel rect [u0, u1, vTop, vBottom] by hand, and `tw`/`th` the texture size in pixels.
const FACE = ['px', 'nx', 'py', 'ny', 'pz', 'nz'];
export function mcBox(x0, y0, z0, x1, y1, z1, mats, o = {}) {
  const geo = new THREE.BoxGeometry(x1 - x0, y1 - y0, z1 - z0);
  geo.translate((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2);
  const s = 16;
  const rect = {
    px: [(1 - z1) * s, (1 - z0) * s, (1 - y1) * s, (1 - y0) * s], nx: [z0 * s, z1 * s, (1 - y1) * s, (1 - y0) * s],
    py: [x0 * s, x1 * s, z0 * s, z1 * s], ny: [x0 * s, x1 * s, (1 - z1) * s, (1 - z0) * s],
    pz: [x0 * s, x1 * s, (1 - y1) * s, (1 - y0) * s], nz: [(1 - x1) * s, (1 - x0) * s, (1 - y1) * s, (1 - y0) * s],
  };
  const tw = o.tw || 16, th = o.th || 16;
  const uv = geo.attributes.uv;
  FACE.forEach((f, i) => {
    const [u0, u1, vt, vb] = (o.uv && o.uv[f]) || rect[f];
    for (let k = 0; k < 4; k++) {
      const idx = i * 4 + k;
      const u = uv.getX(idx), v = uv.getY(idx);
      uv.setXY(idx, (u0 + u * (u1 - u0)) / tw, 1 - vb / th + (v * (vb - vt)) / th);
    }
  });
  uv.needsUpdate = true;
  const mesh = new THREE.Mesh(geo, mats);
  mesh.castShadow = o.shadow !== false; mesh.receiveShadow = true;
  return mesh;
}

// ---- materials of a cube-like spec
function faceMaterial(file, spec, face) {
  const o = {};
  if (spec.cut) { o.alphaTest = 0.1; o.side = THREE.FrontSide; }
  if (spec.blend) { o.transparent = true; o.depthWrite = false; o.alphaTest = 0.02; }
  if (spec.glow) { o.emissive = spec.glow; o.emissiveIntensity = 0.5; }
  const tint = spec.tint && (spec.tint[face] ?? spec.tint.all);
  if (tint != null) o.color = tint;
  return L(file, o);
}
function cubeMats(spec) {
  const mats = FACE.map((f) => faceMaterial(spec.f[f], spec, f));
  return mats.every((m) => m === mats[0]) ? mats[0] : mats;
}

const ID = (id) => bare(id);

// A block at the origin corner. opts: {at(dx,dy,dz) -> {id,meta}|null for connections, lines for
// signs, falling (a falling cake is a cube), item (drawn as an inventory icon)}. Returns {obj, light, lid}.
export function makeBlock(id, meta = 0, opts = {}) {
  const rep = opts.item || opts.quiet ? null : report(); if (rep) rep.blocks++;
  const n = ID(id);
  const g = new THREE.Group();
  const spec = blockSpec(id, meta, opts);
  if (!spec) { if (rep && !rep.unknown.includes('block:' + id)) rep.unknown.push('block:' + id); return fallback(g); }
  const at = opts.at || (() => null);
  const joins = (fn, dx, dy, dz) => { const b = at(dx, dy, dz); return !!b && fn(b.id, b.meta || 0); };
  const add = (m) => { g.add(m); return m; };
  const mesh = (x0, y0, z0, x1, y1, z1, mats, o) => add(mcBox(x0, y0, z0, x1, y1, z1, mats, o));

  switch (spec.k) {
    case 'none': return { obj: g, light: null, lid: null };
    case 'cube': {
      mesh(0, 0, 0, 1, 1, 1, cubeMats(spec));
      if (spec.overlay) {
        // the grass fringe: the overlay texture, tinted, over the four sides
        const o = L(spec.overlay.file, { color: spec.overlay.tint, alphaTest: 0.1 });
        mesh(0, 0, 0, 1, 1, 1, [o, o, HIDDEN(), HIDDEN(), o, o], { shadow: false }).scale.setScalar(1.001);
        g.children[g.children.length - 1].position.set(-0.0005, -0.0005, -0.0005);
      }
      break;
    }
    case 'enchant': mesh(0, 0, 0, 1, 0.75, 1, cubeMats({ f: spec.f })); break;
    case 'slab': mesh(0, 0, 0, 1, 0.5, 1, cubeMats({ f: spec.f })); break;
    case 'plate': { const m = L(spec.file); mesh(0.0625, 0, 0.0625, 0.9375, 0.0625, 0.9375, m); break; }
    case 'cake': {
      if (opts.falling && spec.fallingCube) { mesh(0, 0, 0, 1, 1, 1, cubeMats({ f: spec.f, cut: true })); break; }
      // BlockCake bounds: x from (1 + 2*slices)/16 to 15/16, y 0..0.5, z 1/16..15/16
      mesh((1 + 2 * spec.slices) / 16, 0, 1 / 16, 15 / 16, 0.5, 15 / 16, cubeMats({ f: spec.f, cut: true }));
      break;
    }
    case 'stairs': {
      // meta bits 0-1: 0 ascends east, 1 west, 2 south, 3 north; bit 2: upside down
      const m = cubeMats({ f: spec.f });
      const up = (spec.meta & 4) !== 0, d = spec.meta & 3;
      const [y0, y1] = up ? [0.5, 1] : [0, 0.5], [h0, h1] = up ? [0, 0.5] : [0.5, 1];
      mesh(0, y0, 0, 1, y1, 1, m);
      if (d === 0) mesh(0.5, h0, 0, 1, h1, 1, m);
      else if (d === 1) mesh(0, h0, 0, 0.5, h1, 1, m);
      else if (d === 2) mesh(0, h0, 0.5, 1, h1, 1, m);
      else mesh(0, h0, 0, 1, h1, 0.5, m);
      break;
    }
    case 'bars': {
      // BlockPane: a 2 px post, and 2 px thick arms toward every pane, glass or opaque block next to
      // it; a lone pane shows all four arms
      const m = L(spec.file, { alphaTest: 0.5 });
      const w = joins(paneJoins, -1, 0, 0), e = joins(paneJoins, 1, 0, 0), nn = joins(paneJoins, 0, 0, -1), s = joins(paneJoins, 0, 0, 1);
      const lone = !w && !e && !nn && !s;
      const a = 7 / 16, b = 9 / 16;
      if (w || e || lone) mesh(w || lone ? 0 : a, 0, a, e || lone ? 1 : b, 1, b, m);
      if (nn || s || lone) mesh(a, 0, nn || lone ? 0 : a, b, 1, s || lone ? 1 : b, m);
      break;
    }
    case 'fence': {
      // BlockFence: post 6..10 px; two rails per neighbour at 6..9 and 12..15 px, 2 px thick
      const m = L(spec.file);
      mesh(0.375, 0, 0.375, 0.625, 1, 0.625, m);
      const dirs = [[-1, 0], [1, 0], [0, -1], [0, 1]];
      for (const [dx, dz] of dirs) {
        if (!joins(fenceJoins, dx, 0, dz)) continue;
        for (const [ya, yb] of [[0.375, 0.5625], [0.75, 0.9375]]) {
          if (dx) mesh(dx < 0 ? 0 : 0.625, ya, 0.4375, dx < 0 ? 0.375 : 1, yb, 0.5625, m);
          else mesh(0.4375, ya, dz < 0 ? 0 : 0.625, 0.5625, yb, dz < 0 ? 0.375 : 1, m);
        }
      }
      break;
    }
    case 'web': {
      const m = new THREE.MeshLambertMaterial({ map: T(spec.file), alphaTest: 0.4, side: THREE.DoubleSide });
      const a = new THREE.Mesh(new THREE.PlaneGeometry(Math.SQRT2, 1), m); a.position.set(0.5, 0.5, 0.5); a.rotation.y = Math.PI / 4; g.add(a);
      const b = new THREE.Mesh(new THREE.PlaneGeometry(Math.SQRT2, 1), m); b.position.set(0.5, 0.5, 0.5); b.rotation.y = -Math.PI / 4; g.add(b);
      break;
    }
    case 'torch': {
      // 2 x 10 x 2 px, texture columns 7..9, flame rows 6..8 on top. Wall torches (meta 1 east, 2 west,
      // 3 south, 4 north: the way the flame leans) sit against their wall and tilt out from it.
      const inner = new THREE.Group();
      inner.position.set(-0.5, 0, -0.5);
      inner.add(mcBox(0.4375, 0, 0.4375, 0.5625, 0.625, 0.5625, L(spec.file, { alphaTest: 0.1 }), { uv: { py: [7, 9, 6, 8] } }));
      const f = new THREE.Mesh(new THREE.PlaneGeometry(0.28, 0.28), new THREE.MeshBasicMaterial({ map: torchTex(), transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide }));
      f.position.set(0.5, 0.72, 0.5); f.userData.billboard = true; inner.add(f);
      const light = new THREE.PointLight(0xffa040, 1.4, 4.5, 1.6);
      light.position.set(0.5, 0.85, 0.5);
      inner.add(light);
      g.userData.light = light;
      const holder = new THREE.Group();
      holder.add(inner);
      const wall = { 1: [-1, 0], 2: [1, 0], 3: [0, -1], 4: [0, 1] }[spec.meta];   // toward the wall it hangs on
      if (wall) {
        holder.position.set(0.5 + wall[0] * 0.35, 0.22, 0.5 + wall[1] * 0.35);
        holder.rotation.z = wall[0] * 0.38;
        holder.rotation.x = -wall[1] * 0.38;
      } else holder.position.set(0.5, 0, 0.5);
      g.add(holder);
      break;
    }
    case 'sign': {
      // ModelSign scaled 2/3: board 24 x 12 x 2 px at model y -14..-2 (world 0.583..1.083), stick
      // 2 x 14 x 2 (world 0..0.583), turned meta * 22.5 degrees (meta 0 reads from the south, 8 from
      // the north). The frame below is centred on the block with +z the text side.
      const k = 2 / 3 / 16;
      const root = new THREE.Group();
      root.position.set(0.5, 0.5, 0.5);
      const sgn = L(spec.board);
      const board = mcBox(-12 * k, 0.083, -1 * k, 12 * k, 0.583, 1 * k, sgn, { tw: 64, th: 32, uv: { px: [26, 28, 2, 14], nx: [0, 2, 2, 14], pz: [2, 26, 2, 14], nz: [28, 52, 2, 14], py: [2, 26, 0, 2], ny: [26, 50, 0, 2] } });
      const stick = mcBox(-1 * k, -0.5, -1 * k, 1 * k, 0.083, 1 * k, sgn, { tw: 64, th: 32, uv: { px: [4, 6, 16, 30], nx: [0, 2, 16, 30], pz: [2, 4, 16, 30], nz: [6, 8, 16, 30], py: [2, 4, 14, 16], ny: [4, 6, 14, 16] } });
      root.add(board, stick);
      const text = new THREE.Mesh(new THREE.PlaneGeometry(1.0, 0.5), new THREE.MeshBasicMaterial({ map: signTexture(opts.lines), transparent: true, alphaTest: 0.3 }));
      text.position.set(0, 0.333, 0.0417 + 0.002);
      root.add(text);
      root.rotation.y = -(spec.meta & 15) * Math.PI / 8;
      g.add(root);
      break;
    }
    case 'chest': {
      const ch = chestModel(spec.file);
      ch.position.set(0.5, 0, 0.5);
      // meta 2 north, 3 south, 4 west, 5 east: the model's front faces south
      ch.rotation.y = { 2: Math.PI, 3: 0, 4: -Math.PI / 2, 5: Math.PI / 2 }[spec.meta] ?? 0;
      g.add(ch);
      g.userData.lid = ch.userData.lid;
      break;
    }
    case 'anvil': {
      const base = L('anvil_base.png'), top = L('anvil_top_damaged_0.png');
      // RenderBlocks.renderBlockAnvilOrient: base 0.75x0.25x0.75, neck 0.5x0.0625x0.625, waist 0.25x0.3125x0.5, top 0.625x0.375x1.0
      const box = (w, h, d, x, y, z, m) => { const q = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), m); q.position.set(x + w / 2, y + h / 2, z + d / 2); q.castShadow = true; q.receiveShadow = true; g.add(q); };
      box(0.75, 0.25, 0.75, 0.125, 0, 0.125, base);
      box(0.5, 0.0625, 0.625, 0.25, 0.25, 0.1875, base);
      box(0.25, 0.3125, 0.5, 0.375, 0.3125, 0.25, base);
      box(0.625, 0.375, 1.0, 0.1875, 0.625, 0, top);
      break;
    }
    case 'egg': {
      // RenderBlocks.renderBlockDragonEgg: eight stacked slabs, half-width and height in px
      const m = L(spec.file);
      const layers = [[2, 1], [3, 1], [4, 1], [5, 2], [6, 3], [7, 5], [6, 2], [3, 1]];
      let l = 0;
      for (const [b0, b1] of layers) {
        const f = b0 / 16, top = 1 - l / 16, bot = 1 - (l + b1) / 16;
        l += b1;
        mesh(0.5 - f, bot, 0.5 - f, 0.5 + f, top, 0.5 + f, m);
      }
      break;
    }
    case 'brew': {
      // RenderBlocks.renderBlockBrewingStand: a rod, three base slabs, three blades 120 degrees apart
      const rod = L(spec.files[0], { alphaTest: 0.1 }), base = L(spec.files[1], { alphaTest: 0.1 });
      mesh(0.4375, 0, 0.4375, 0.5625, 0.875, 0.5625, rod);
      mesh(0.5625, 0, 0.3125, 0.9375, 0.125, 0.6875, base);
      mesh(0.125, 0, 0.0625, 0.5, 0.125, 0.4375, base);
      mesh(0.125, 0, 0.5625, 0.5, 0.125, 0.9375, base);
      const bm = new THREE.MeshLambertMaterial({ map: T(spec.files[0]), alphaTest: 0.1, side: THREE.DoubleSide });
      for (let j = 0; j < 3; j++) {
        const d1 = (j * Math.PI * 2) / 3 + Math.PI / 2;
        const geo = new THREE.PlaneGeometry(0.5, 1);
        const uv = geo.attributes.uv;
        for (let i = 0; i < uv.count; i++) uv.setX(i, 0.5 + uv.getX(i) * 0.5);
        const p = new THREE.Mesh(geo, bm);
        p.position.set(0.5 + Math.sin(d1) * 0.25, 0.5, 0.5 + Math.cos(d1) * 0.25);
        p.rotation.y = d1 - Math.PI / 2;
        g.add(p);
      }
      break;
    }
    case 'liquid': {
      // lava_still.png is a 20-frame vertical strip: animTex shows one square frame and scrolls it
      if (spec.lava) {
        const m = memo('lava', () => { const t = animTex('blocks/lava_still.png'); return new THREE.MeshLambertMaterial({ map: t, emissive: 0xff6a1a, emissiveMap: t, emissiveIntensity: 1.1 }); });
        const q = new THREE.Mesh(new THREE.BoxGeometry(1, 0.89, 1), m); q.position.set(0.5, 0.445, 0.5); g.add(q);
      } else {
        const m = memo('water', () => new THREE.MeshLambertMaterial({ map: animTex('blocks/water_still.png'), transparent: true, depthWrite: false }));   // 1.7.10 water is a blue texture with its own alpha
        const q = new THREE.Mesh(new THREE.BoxGeometry(1, 0.89, 1), m); q.position.set(0.5, 0.445, 0.5); g.add(q);
      }
      break;
    }
    default: return fallback(g);
  }
  return { obj: g, light: g.userData.light || null, lid: g.userData.lid || null };
}

// A block the table does not know: a loud magenta cube so it cannot hide (the audit lists these).
function fallback(g) {
  const q = new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), memo('fallback', () => new THREE.MeshLambertMaterial({ color: 0xff00ff })));
  q.position.set(0.5, 0.5, 0.5); g.add(q);
  return { obj: g, light: null, lid: null, fallback: true };
}

// ModelChest (base 14 x 10 x 14, lid 14 x 5 x 14 hinged at the back, latch 2 x 4 x 1) drawn from
// entity/chest.png (or the trapped chest's). The front faces +z; g.userData.lid is the hinge, and
// a negative rotation.x opens it (the chest scenes rely on that).
export function chestModel(file = 'entity/chest.png') {
  const g = new THREE.Group();
  const m = memo('chestmat' + file, () => new THREE.MeshLambertMaterial({ map: tex(file), side: THREE.DoubleSide }));   // the library's boxes wind inward
  const base = new THREE.Mesh(boxGeometry([-7, -10, -7, 14, 10, 14], [0, 19], 64, 64), m);
  base.rotation.y = Math.PI;                      // the library builds models facing -z
  base.castShadow = base.receiveShadow = true;
  const pivot = new THREE.Group();
  pivot.position.set(0, 9 / 16, -7 / 16);         // model y = 7 below the top, at the back
  const inner = new THREE.Group();
  inner.rotation.y = Math.PI;
  const lid = new THREE.Mesh(boxGeometry([-7, -5, -14, 14, 5, 14], [0, 0], 64, 64), m);
  lid.scale.setScalar(1.002);                     // a hair larger so its front never z-fights the base's rim
  const latch = new THREE.Mesh(boxGeometry([-1, -2, -15, 2, 4, 1], [0, 0], 64, 64), m);
  lid.castShadow = latch.castShadow = true;
  inner.add(lid, latch);
  pivot.add(inner);
  g.add(base, pivot);
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

export function blockHasLight(id) { return ID(id) === 'torch'; }
