// Set dressing for the Krypt: wall torches on block faces (the 1.7.10 tilted shape and texture), planes and boxes
// for webs, vines, rails, bones, lily pads and bars, skulls, the minecart, the spawner with its spinning mob, fire,
// and the water and lava surfaces. Everything static is merged by material and carries its baked light.
import * as THREE from "three";
import { patchBake, patchTorch } from "./krypt.js";
import { boxGeometry, makeMob } from "../lib/mc/mobs.js";
import { tex as mcTex } from "../lib/mc/textures.js";
import { PROPS } from "./props.js";

function nearest(img, { repeat = false } = {}) {
  const t = new THREE.Texture(img);
  t.colorSpace = THREE.SRGBColorSpace; t.magFilter = THREE.NearestFilter; t.minFilter = THREE.NearestFilter;
  t.generateMipmaps = false; if (repeat) t.wrapS = t.wrapT = THREE.RepeatWrapping; t.needsUpdate = true;
  return t;
}

// The torch: four faces of a 2 by 2 pixel column that is a block tall and leans 0.4 away from the wall, plus the cap
// at ten sixteenths. Base 0.1 off the face and 0.22 above the cell floor, as in 1.7.10's renderTorchAtAngle.
function torchGeometry(list) {
  const pos = [], uv = [], idx = [];
  const h = 0.0625;
  for (const t of list) {
    const ox = t.fx, oz = t.fz, px = -t.fz, pz = t.fx;
    const bx = t.cx + ox * 0.1, by = t.j + 0.22, bz = t.cz + oz * 0.1;
    const cor = [[-1, -1], [1, -1], [1, 1], [-1, 1]].map(([u, v]) => [ox * h * u + px * h * v, oz * h * u + pz * h * v]);
    const u0 = 7 / 16, u1 = 9 / 16;
    for (let q = 0; q < 4; q++) {
      const c0 = cor[q], c1 = cor[(q + 1) % 4], base = pos.length / 3;
      pos.push(bx + c0[0], by, bz + c0[1], bx + c1[0], by, bz + c1[1],
        bx + c1[0] + ox * 0.4, by + 1, bz + c1[1] + oz * 0.4, bx + c0[0] + ox * 0.4, by + 1, bz + c0[1] + oz * 0.4);
      uv.push(u0, 0, u1, 0, u1, 1, u0, 1);
      idx.push(base, base + 1, base + 2, base, base + 2, base + 3);
    }
    const base = pos.length / 3, k = 0.625;
    for (const c of cor) pos.push(bx + c[0] + ox * 0.4 * k, by + k, bz + c[1] + oz * 0.4 * k);
    uv.push(u0, 1 - 8 / 16, u1, 1 - 8 / 16, u1, 1 - 6 / 16, u0, 1 - 6 / 16);
    idx.push(base, base + 1, base + 2, base, base + 2, base + 3);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute("uv", new THREE.Float32BufferAttribute(uv, 2));
  g.setIndex(idx);
  return g;
}

// One dresser for the whole Krypt: textures, materials and the animated canvases are shared, and build() dresses one chunk
// (its decor, torches, water and lava planes) into a group that dispose() takes back.
export function makeDresser(IMG) {
  const M = new THREE.Matrix4(), Q = new THREE.Quaternion(), E = new THREE.Euler(), P = new THREE.Vector3(), S1 = new THREE.Vector3(1, 1, 1);
  const texCache = new Map();
  const tex = (img, repeat = true) => { const k = img; if (!texCache.has(k)) texCache.set(k, nearest(img, { repeat })); return texCache.get(k); };
  const matCache = new Map();
  const shared = (key, mk) => { if (!matCache.has(key)) matCache.set(key, mk()); return matCache.get(key); };
  const plane = (w, h, ur = 1, vr = 1) => {
    const g = new THREE.PlaneGeometry(w, h); const uv = g.attributes.uv;
    for (let i = 0; i < uv.count; i++) uv.setXY(i, uv.getX(i) * ur, uv.getY(i) * vr);
    return g;
  };
  const cut = (img, o = {}) => () => patchBake(new THREE.MeshLambertMaterial({ map: tex(img), alphaTest: 0.5, side: THREE.DoubleSide, ...o }));
  const lamb = (name, o = {}) => () => patchBake(new THREE.MeshLambertMaterial({ map: tex(IMG[name]), ...o }));
  const mkWeb = cut(IMG.web), mkVine = cut(IMG.vine), mkRail = cut(IMG.rail_normal, { alphaTest: 0.3 }), mkBone = cut(IMG.bone, { alphaTest: 0.3 });
  const mkLily = cut(IMG.waterlily), mkBars = cut(IMG.iron_bars);
  const mkPlank = lamb("planks_oak"), mkCobble = lamb("cobblestone");
  const mkSkull = () => patchBake(new THREE.MeshLambertMaterial({ map: tex(IMG.skull_tex || IMG.skeleton) }));
  const mkWire = cut(IMG.trip_wire, { alphaTest: 0.2 }), mkHook = cut(IMG.trip_wire_source, { alphaTest: 0.2 });
  const propMat = (name, cutout, dbl) => () => patchBake(new THREE.MeshLambertMaterial({ map: tex(IMG[name]), ...(cutout ? { alphaTest: 0.5 } : {}), ...(dbl ? { side: THREE.DoubleSide } : {}) }));
  const mkLever = lamb("lever"), mkDoorL = lamb("door_iron_lower"), mkDoorU = lamb("door_iron_upper"), mkNBrick = lamb("nether_brick");
  const mkFrameTop = lamb("endframe_top"), mkFrameSide = lamb("endframe_side"), mkEye = () => patchBake(new THREE.MeshLambertMaterial({ map: tex(IMG.endframe_eye), color: new THREE.Color(1.0, 1.0, 1.0), emissive: new THREE.Color(0.05, 0.22, 0.14) }));
  const SKIP = (new URLSearchParams(location.search).get("skip") || "").split(",");

  // Animated canvases (water, lava, fire) are drawn once for every chunk.
  const upd = [];
  const animCanvas = (img, frames) => {
    const c = document.createElement("canvas"); c.width = c.height = 16;
    const x = c.getContext("2d"); x.imageSmoothingEnabled = false;
    const t = new THREE.CanvasTexture(c);
    t.colorSpace = THREE.SRGBColorSpace; t.magFilter = THREE.NearestFilter; t.minFilter = THREE.NearestFilter; t.wrapS = t.wrapT = THREE.RepeatWrapping; t.generateMipmaps = false;
    let last = -1;
    const set = (f) => { f = f % frames; if (f === last) return; last = f; x.clearRect(0, 0, 16, 16); x.drawImage(img, 0, f * 16, 16, 16, 0, 0, 16, 16); t.needsUpdate = true; };
    set(0);
    return { t, set };
  };
  const wa = IMG.water_still ? animCanvas(IMG.water_still, 32) : null;
  const la = IMG.lava_still ? animCanvas(IMG.lava_still, 20) : null;
  const fa = IMG.fire_layer_0 ? animCanvas(IMG.fire_layer_0, 32) : null;
  upd.push((t) => { if (wa) wa.set(Math.floor(t * 8)); if (la) la.set(Math.floor(t * 6)); if (fa) fa.set(Math.floor(t * 10)); });
  const waterMat = () => shared("water", () => patchBake(new THREE.MeshLambertMaterial({ map: wa.t, transparent: true, opacity: 0.62, color: 0x35566e, depthWrite: false })));
  const lavaMat = () => shared("lava", () => new THREE.MeshBasicMaterial({ map: la ? la.t : null, color: new THREE.Color(1.5, 1.05, 0.75) }));
  const fireMat = () => shared("fire", () => new THREE.MeshBasicMaterial({ map: fa.t, transparent: true, alphaTest: 0.2, side: THREE.DoubleSide, color: new THREE.Color(1.5, 1.25, 1.0), depthWrite: false }));
  const torchMat = () => shared("torch", () => patchTorch(new THREE.MeshBasicMaterial({ map: nearest(IMG.torch_on), alphaTest: 0.4, side: THREE.DoubleSide, color: new THREE.Color(1.35, 1.2, 1.0) })));
  // The end portal: a starfield that drifts, two layers for depth, over a deep teal.
  let portalMats = null;
  const portal = () => {
    if (portalMats) return portalMats;
    const c = document.createElement("canvas"); c.width = c.height = 128;
    const x = c.getContext("2d");
    x.fillStyle = "#06322e"; x.fillRect(0, 0, 128, 128);
    let seed = 7; const rnd = () => { seed = (seed * 16807) % 2147483647; return seed / 2147483647; };
    for (let q = 0; q < 70; q++) { const px = Math.floor(rnd() * 128), py = Math.floor(rnd() * 128), b = rnd(); x.fillStyle = b > 0.8 ? "#d6fff2" : b > 0.45 ? "#5fe0c0" : "#2b9a8c"; const sz = b > 0.9 ? 4 : 3; x.fillRect(px, py, sz, sz); }
    const mk = (sc, add) => {
      const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.magFilter = THREE.NearestFilter; t.minFilter = THREE.NearestFilter; t.wrapS = t.wrapT = THREE.RepeatWrapping; t.generateMipmaps = false; t.repeat.set(sc, sc);
      return { t, m: new THREE.MeshBasicMaterial({ map: t, color: add ? new THREE.Color(1.3, 2.0, 1.7) : new THREE.Color(1.0, 1.7, 1.5), transparent: !!add, opacity: add ? 0.65 : 1, blending: add ? THREE.AdditiveBlending : THREE.NormalBlending, depthWrite: !add }) };
    };
    const a1 = mk(1.5, false), a2 = mk(2.6, true);
    let sk = null;
    if (IMG.end_sky) { const t = nearest(IMG.end_sky, { repeat: true }); t.repeat.set(1.2, 1.2); sk = { t, m: new THREE.MeshBasicMaterial({ map: t, color: new THREE.Color(0.55, 0.9, 0.8), transparent: true, opacity: 0.8, depthWrite: false }) }; }
    upd.push((tt) => { a1.t.offset.set(tt * 0.03, tt * 0.021); a2.t.offset.set(-tt * 0.05, tt * 0.04); if (sk) sk.t.offset.set(tt * 0.012, -tt * 0.018); });
    return (portalMats = { a1, a2, sk });
  };

  const active = new Set();
  function build(own, lightAt) {
    const group = new THREE.Group();
    const batches = new Map();
    const disposers = [];
    const bakeConst = (g, x, y, z) => {
      const c = lightAt(x, y, z, 0, 0.35, 0, { omni: true });
      const n = g.attributes.position.count, arr = new Float32Array(n * 3);
      for (let i = 0; i < n; i++) { arr[i * 3] = c[0]; arr[i * 3 + 1] = c[1]; arr[i * 3 + 2] = c[2]; }
      g.setAttribute("bake", new THREE.BufferAttribute(arr, 3));
    };
    const put = (key, geo, x, y, z, ry = 0, rx = 0, rz = 0, mk = null) => {
      E.set(rx, ry, rz, "YXZ"); Q.setFromEuler(E); P.set(x, y, z);
      M.compose(P, Q, S1); geo.applyMatrix4(M);
      bakeConst(geo, x, y, z);
      if (!batches.has(key)) batches.set(key, { list: [], mk, key });
      batches.get(key).list.push(geo);
    };
    const spawners = [], portals = [], fires = [];
    const slabCells = new Set();
    // A prop is a block: it sits in one cell, square to the grid (the kinds' leg-local offsets are snapped here).
    const putProp = (kind, d) => {
      const q = Math.PI / 2;
      d = { ...d, x: Math.floor(d.x) + 0.5, z: Math.floor(d.z) + 0.5, ry: Math.round((d.ry || 0) / q) * q };
      for (const p of PROPS[kind](d)) {
        if (p.tex === "water") { if (wa) put("propWater", p.geo, d.x, d.y, d.z, d.ry || 0, 0, 0, waterMat); else p.geo.dispose(); continue; }
        if (!IMG[p.tex]) { p.geo.dispose(); continue; }
        put("prop:" + p.tex + (p.cut ? ":c" : "") + (p.double ? ":2" : ""), p.geo, d.x, d.y, d.z, d.ry || 0, 0, 0, propMat(p.tex, p.cut, p.double));
      }
    };
    const mobs = [], far = [], ups = [];
    const xctx = { group, disposers, lightAt, far, ups, mobs };
    for (const d of own.decor) {
      switch (d.t) {
        case "web": {
          // 1.7.10 draws cobweb as two crossed vertical planes (an X) with a cutout; wide webs are a grid of those.
          const nx = Math.max(1, Math.round(d.w)), ny = d.h ? Math.max(1, Math.round(d.h)) : 1, sz = d.h ? 1 : d.w;
          const cy = Math.cos(d.ry), sy = Math.sin(d.ry);
          for (let i = 0; i < nx; i++) for (let k = 0; k < ny; k++) {
            if (d.h && ((i * 7 + k * 13 + Math.floor(d.x * 3 + d.z * 5)) % 10) < 3) continue;
            const lx = d.h ? (i - (nx - 1) / 2) : 0, ly = d.h ? (k - (ny - 1) / 2) : 0;
            const wx = d.x + lx * cy, wz = d.z - lx * sy;
            for (const da of [Math.PI / 4, -Math.PI / 4]) put("web", plane(sz, sz), wx, d.y + ly, wz, d.ry + da, 0, 0, mkWeb);
          }
          break;
        }
        // The 1.7.10 models (props.js): chests, minecarts, cauldrons, anvils, brewing stands, enchanting tables.
        case "chest": putProp("chest", d); break;
        case "cauldron": putProp("cauldron", d); break;
        case "anvil": putProp("anvil", d); break;
        case "brewing": putProp("brewing", d); break;
        case "enchanting": putProp("enchanting", d); break;
        case "wire": put("wire", plane(1, 1), d.x, d.y, d.z, d.ry, -Math.PI / 2, 0, mkWire); break;
        case "hook": put("hook", plane(0.7, 0.7), d.x, d.y, d.z, d.ry, 0, 0, mkHook); break;
        case "lever": {
          put("cobble", new THREE.BoxGeometry(0.375, 0.5, 0.19), d.x, d.y, d.z, d.ry, 0, 0, mkCobble);
          const g = new THREE.BoxGeometry(0.125, 0.125, 0.56); g.translate(0, 0, 0.28 + 0.06);
          const uv = g.attributes.uv; for (let i = 0; i < uv.count; i++) uv.setXY(i, 0.4375 + uv.getX(i) * 0.125, 0.4 + uv.getY(i) * 0.5);
          put("lever", g, d.x, d.y, d.z, d.ry, d.on ? -0.75 : 0.75, 0, mkLever); break;
        }
        case "idoor": {
          for (const [dy, key, mk] of [[0.5, "idoorL", mkDoorL], [1.5, "idoorU", mkDoorU]]) put(key, new THREE.BoxGeometry(0.1875, 1, 1), d.x, d.y + dy, d.z, d.ry, 0, 0, mk);
          break;
        }
        case "nfence": {
          put("nbrick", new THREE.BoxGeometry(0.25, 1.15, 0.25), d.x, d.y + 0.575, d.z, d.ry, 0, 0, mkNBrick);
          if (d.rails) for (const hy of [0.5, 0.92]) {
            const g = new THREE.BoxGeometry(0.12, 0.16, 1.0); const uv = g.attributes.uv; for (let i = 0; i < uv.count; i++) uv.setXY(i, uv.getX(i) * 0.4 + 0.3, uv.getY(i) * 0.25 + 0.4);
            put("nbrick", g, d.x + d.bx * 0.5, d.y + hy, d.z + d.bz * 0.5, d.ry, 0, 0, mkNBrick);
          }
          break;
        }
        case "frame": {
          const hgt = 0.8125;
          put("frameTop", plane(1, 1), d.x, d.y + hgt, d.z, 0, -Math.PI / 2, 0, mkFrameTop);
          for (let q = 0; q < 4; q++) {
            const ry = q * Math.PI / 2, ox = Math.sin(ry) * 0.5, oz = Math.cos(ry) * 0.5;
            const g = plane(1, hgt); const uv = g.attributes.uv; for (let i = 0; i < uv.count; i++) uv.setY(i, uv.getY(i) * hgt);
            put("frameSide", g, d.x + ox, d.y + hgt / 2, d.z + oz, ry, 0, 0, mkFrameSide);
          }
          if (d.eye) {
            const g = new THREE.BoxGeometry(0.5, 0.1875, 0.5); const uv = g.attributes.uv; for (let i = 0; i < uv.count; i++) uv.setXY(i, 0.25 + uv.getX(i) * 0.5, 0.25 + uv.getY(i) * 0.5);
            put("eye", g, d.x, d.y + hgt + 0.09, d.z, 0, 0, 0, mkEye);
          }
          break;
        }
        case "portal": portals.push(d); break;
        case "vine": put("vine", plane(d.w, d.h), d.x, d.y, d.z, d.ry, 0, 0, mkVine); break;
        case "rail": put("rail", plane(1, 1), d.x, d.y, d.z, d.ry, -Math.PI / 2, 0, mkRail); break;
        case "bone": put("bone", plane(0.55, 0.55), d.x, d.y, d.z, d.ry, -Math.PI / 2, 0, mkBone); break;
        case "lily": put("lily", plane(0.8, 0.8), d.x, d.y, d.z, d.ry, -Math.PI / 2, 0, mkLily); break;
        case "bars": put("bars", plane(d.w, d.h, d.w, d.h), d.x, d.y, d.z, d.ry, 0, 0, mkBars); break;
        case "beam": { const g = new THREE.BoxGeometry(d.len, 0.28, 0.28); put("plank", g, d.x, d.y, d.z, d.ry, 0, d.rz || 0, mkPlank); break; }
        case "rubble": {
          // Where a roof gave way: a bottom slab of cobblestone on the block grid, one per cell (the game has no tilted blocks).
          const x = Math.floor(d.x) + 0.5, z = Math.floor(d.z) + 0.5, y = Math.floor(d.y + 0.01), k = x + "," + y + "," + z;
          if (slabCells.has(k)) break; slabCells.add(k);
          putProp("slab", { x, y, z, ry: 0, tex: (Math.floor(x) * 7 + Math.floor(z) * 3) % 3 === 0 ? "cobblestone_mossy" : "cobblestone" });
          break;
        }
        case "skull": {
          const g = boxGeometry([-4, -8, -4, 8, 8, 8], [0, 0], 64, 32);
          put("skull", g, d.x, d.y, d.z, d.ry, 0, 0, mkSkull); break;
        }
        // A minecart sits on its rail: centred, the long axis along the track, the floor an eighth above the block.
        case "cart": putProp("minecart", { ...d, y: Math.floor(d.y + 0.01) + 0.125 }); break;
        case "fire": fires.push(d); break;
        case "spawner": spawners.push(d); break;
        default: if (EXTRA[d.t]) EXTRA[d.t](d, put, xctx); break;
      }
    }
    for (const [, b] of batches) {
      if (SKIP.includes(b.key)) continue;
      let nv = 0, ni = 0;
      for (const g of b.list) { nv += g.attributes.position.count; ni += g.index.count; }
      const pos = new Float32Array(nv * 3), nor = new Float32Array(nv * 3), uv = new Float32Array(nv * 2), bk = new Float32Array(nv * 3), ix = new Uint32Array(ni);
      let ov = 0, oi = 0;
      for (const g of b.list) {
        const n = g.attributes.position.count;
        pos.set(g.attributes.position.array, ov * 3); nor.set(g.attributes.normal.array, ov * 3);
        uv.set(g.attributes.uv.array, ov * 2); bk.set(g.attributes.bake.array, ov * 3);
        for (let i = 0; i < g.index.count; i++) ix[oi + i] = g.index.array[i] + ov;
        ov += n; oi += g.index.count; g.dispose();
      }
      const geo = new THREE.BufferGeometry();
      geo.setAttribute("position", new THREE.BufferAttribute(pos, 3)); geo.setAttribute("normal", new THREE.BufferAttribute(nor, 3));
      geo.setAttribute("uv", new THREE.BufferAttribute(uv, 2)); geo.setAttribute("bake", new THREE.BufferAttribute(bk, 3));
      geo.setIndex(new THREE.BufferAttribute(ix, 1));
      group.add(new THREE.Mesh(geo, shared("d:" + b.key, b.mk)));
    }
    // Torches: one merged mesh, fullbright like the game's.
    if (own.torches.length) group.add(new THREE.Mesh(torchGeometry(own.torches), torchMat()));
    // Water and lava: the planes over each rectangle.
    for (const r of own.waterRects) {
      if (!wa) break;
      const w = r.x1 - r.x0, d = r.z1 - r.z0, sx = Math.max(1, Math.round(w)), sz = Math.max(1, Math.round(d));
      const g = new THREE.PlaneGeometry(w, d, sx, sz); g.rotateX(-Math.PI / 2); g.translate((r.x0 + r.x1) / 2, r.y, (r.z0 + r.z1) / 2);
      const uv = g.attributes.uv; for (let i = 0; i < uv.count; i++) uv.setXY(i, uv.getX(i) * w, uv.getY(i) * d);
      const p = g.attributes.position, arr = new Float32Array(p.count * 3);
      for (let i = 0; i < p.count; i++) { const c = lightAt(p.getX(i), r.y + 0.05, p.getZ(i), 0, 1, 0); arr[i * 3] = c[0]; arr[i * 3 + 1] = c[1]; arr[i * 3 + 2] = c[2]; }
      g.setAttribute("bake", new THREE.BufferAttribute(arr, 3));
      const m = new THREE.Mesh(g, waterMat()); m.renderOrder = 2; group.add(m);
    }
    for (const r of own.lavaRects) {
      const w = r.x1 - r.x0, d = r.z1 - r.z0;
      const g = new THREE.PlaneGeometry(w, d); g.rotateX(-Math.PI / 2); g.translate((r.x0 + r.x1) / 2, r.y, (r.z0 + r.z1) / 2);
      const uv = g.attributes.uv; for (let i = 0; i < uv.count; i++) uv.setXY(i, uv.getX(i) * w, uv.getY(i) * d);
      group.add(new THREE.Mesh(g, lavaMat()));
    }
    // Fire: two crossed planes of the fire strip, frame by frame.
    if (fires.length && fa) {
      const list = [];
      for (const d of fires) for (const r of [0.6, 0.6 + Math.PI / 2]) {
        const g = new THREE.PlaneGeometry(1, 1); g.translate(0, 0.5, 0); g.rotateY(r + (d.x * 7 % 1)); g.translate(d.x, d.y, d.z); list.push(g);
      }
      let nv = 0, ni = 0; for (const g of list) { nv += g.attributes.position.count; ni += g.index.count; }
      const pos = new Float32Array(nv * 3), uv = new Float32Array(nv * 2), ix = new Uint32Array(ni); let ov = 0, oi = 0;
      for (const g of list) { pos.set(g.attributes.position.array, ov * 3); uv.set(g.attributes.uv.array, ov * 2); for (let i = 0; i < g.index.count; i++) ix[oi + i] = g.index.array[i] + ov; ov += g.attributes.position.count; oi += g.index.count; g.dispose(); }
      const geo = new THREE.BufferGeometry(); geo.setAttribute("position", new THREE.BufferAttribute(pos, 3)); geo.setAttribute("uv", new THREE.BufferAttribute(uv, 2)); geo.setIndex(new THREE.BufferAttribute(ix, 1));
      group.add(new THREE.Mesh(geo, fireMat()));
    }
    // Spawners: the cage cube, a small mob turning inside.
    for (const spawner of spawners) {
      const sm = new THREE.MeshLambertMaterial({ map: tex(IMG.mob_spawner), transparent: true, alphaTest: 0.4, side: THREE.DoubleSide });
      patchBake(sm, { fixed: new THREE.Vector3(...lightAt(spawner.x, spawner.y + 0.5, spawner.z, 0, 0.3, 0, { omni: true })) });
      const cage = new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), sm);
      cage.position.set(spawner.x, spawner.y + 0.5, spawner.z);
      group.add(cage); far.push([cage, spawner, 34]);
      disposers.push(() => { sm.dispose(); cage.geometry.dispose(); });
      try {
        const mob = makeMob(spawner.mob || "Zombie", { scale: spawner.mob === "CaveSpider" ? 0.42 : 0.3 });
        mob.root.position.set(spawner.x, spawner.y + 0.12, spawner.z);
        mob.root.traverse(o => { if (o.isMesh && o.material && o.material.isMeshLambertMaterial) { o.material.emissive = new THREE.Color(0x201008); } });
        group.add(mob.root); mobs.push(mob); far.push([mob.root, spawner, 15]);
        ups.push((t, dt) => { mob.root.rotation.y = t * 2.2; try { mob.anim(t, dt, {}); } catch { /* optional */ } });
        disposers.push(() => mob.root.traverse(o => { if (o.geometry) o.geometry.dispose(); }));
      } catch { /* no mob */ }
    }
    // The end portal: a starfield that drifts, two layers for depth.
    for (const pd of portals) {
      const pm = portal();
      for (const [a, add] of [[pm.a1, false], [pm.a2, true]]) {
        const m = new THREE.Mesh(new THREE.PlaneGeometry(pd.w, pd.d), a.m);
        m.rotation.x = -Math.PI / 2; m.position.set(pd.x, pd.y + (add ? 0.02 : 0), pd.z); if (add) m.renderOrder = 3;
        group.add(m); disposers.push(() => m.geometry.dispose());
      }
      if (pm.sk) { const m = new THREE.Mesh(new THREE.PlaneGeometry(pd.w, pd.d), pm.sk.m); m.rotation.x = -Math.PI / 2; m.position.set(pd.x, pd.y + 0.01, pd.z); m.renderOrder = 2; group.add(m); disposers.push(() => m.geometry.dispose()); }
    }
    const h = {
      group, spawner: spawners[0] || null, mob: mobs[0] || null,
      tick(t, dt, cam) { for (const f of ups) f(t, dt); if (cam) for (const [o, , r] of far) o.visible = (o.position.x - cam.x) ** 2 + (o.position.z - cam.z) ** 2 < r * r; },
      dispose() {
        active.delete(h);
        group.traverse((o) => { if (o.geometry) o.geometry.dispose(); });
        for (const f of disposers) f();
      }
    };
    active.add(h);
    return h;
  }
  const EXTRA = {};
  return { build, update(t, dt, cam) { for (const f of upd) f(t, dt); for (const h of active) h.tick(t, dt, cam); }, extra: EXTRA, tex, shared, plane, lamb, cut };
}
