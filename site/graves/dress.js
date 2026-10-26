// Set dressing for the Krypt: wall torches on block faces (the 1.7.10 tilted shape and texture), planes and boxes
// for webs, vines, rails, bones, lily pads and bars, skulls, the minecart, the spawner with its spinning mob, fire,
// and the water and lava surfaces. Everything static is merged by material and carries its baked light.
import * as THREE from "three";
import { patchBake } from "./krypt.js";
import { boxGeometry, makeMob } from "../lib/mc/mobs.js";
import { tex as mcTex } from "../lib/mc/textures.js";

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

export function dress(a, lay, IMG, lightAt) {
  const group = new THREE.Group();
  const upd = [];
  const batches = new Map();
  const M = new THREE.Matrix4(), Q = new THREE.Quaternion(), E = new THREE.Euler(), P = new THREE.Vector3(), S1 = new THREE.Vector3(1, 1, 1);
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
    if (!batches.has(key)) batches.set(key, { list: [], mk });
    batches.get(key).list.push(geo);
  };
  const plane = (w, h, ur = 1, vr = 1) => {
    const g = new THREE.PlaneGeometry(w, h); const uv = g.attributes.uv;
    for (let i = 0; i < uv.count; i++) uv.setXY(i, uv.getX(i) * ur, uv.getY(i) * vr);
    return g;
  };
  const cut = (img, o = {}) => () => patchBake(new THREE.MeshLambertMaterial({ map: nearest(img, { repeat: true }), alphaTest: 0.5, side: THREE.DoubleSide, ...o }));
  const mkWeb = cut(IMG.web), mkVine = cut(IMG.vine), mkRail = cut(IMG.rail_normal, { alphaTest: 0.3 }), mkBone = cut(IMG.bone, { alphaTest: 0.3 });
  const mkLily = cut(IMG.waterlily), mkBars = cut(IMG.iron_bars);
  const mkPlank = () => patchBake(new THREE.MeshLambertMaterial({ map: nearest(IMG.planks_oak, { repeat: true }) }));
  const mkCobble = () => patchBake(new THREE.MeshLambertMaterial({ map: nearest(IMG.cobblestone, { repeat: true }) }));
  const mkCart = () => patchBake(new THREE.MeshLambertMaterial({ color: 0x80848a }));
  const mkSkull = () => patchBake(new THREE.MeshLambertMaterial({ map: nearest(IMG.skull_tex || IMG.skeleton) }));

  let spawner = null;
  const fires = [];
  for (const d of a.decor) {
    switch (d.t) {
      case "web": put("web", plane(d.w, d.w), d.x, d.y, d.z, d.ry, 0, 0, mkWeb); break;
      case "vine": put("vine", plane(d.w, d.h), d.x, d.y, d.z, d.ry, 0, 0, mkVine); break;
      case "rail": put("rail", plane(1, 1), d.x, d.y, d.z, d.ry, -Math.PI / 2, 0, mkRail); break;
      case "bone": put("bone", plane(0.55, 0.55), d.x, d.y, d.z, d.ry, -Math.PI / 2, 0, mkBone); break;
      case "lily": put("lily", plane(0.8, 0.8), d.x, d.y, d.z, d.ry, -Math.PI / 2, 0, mkLily); break;
      case "bars": put("bars", plane(d.w, d.h, d.w, d.h), d.x, d.y, d.z, d.ry, 0, 0, mkBars); break;
      case "beam": { const g = new THREE.BoxGeometry(d.len, 0.28, 0.28); put("plank", g, d.x, d.y, d.z, d.ry, 0, d.rz || 0, mkPlank); break; }
      case "rubble": put("cobble", new THREE.BoxGeometry(d.s * 1.4, d.s, d.s * 1.2), d.x, d.y + d.s * 0.5, d.z, d.ry, 0.2, 0.15, mkCobble); break;
      case "skull": {
        const g = boxGeometry([-4, -8, -4, 8, 8, 8], [0, 0], 64, 32);
        put("skull", g, d.x, d.y, d.z, d.ry, 0, 0, mkSkull); break;
      }
      case "cart": {
        const parts = [[0.95, 0.07, 0.62, 0, 0.1, 0], [0.95, 0.38, 0.06, 0, 0.3, 0.31], [0.95, 0.38, 0.06, 0, 0.3, -0.31], [0.06, 0.38, 0.62, 0.45, 0.3, 0], [0.06, 0.38, 0.62, -0.45, 0.3, 0]];
        const cy = Math.cos(d.ry), sy = Math.sin(d.ry);
        for (const [w, h, dd, ox, oy, oz] of parts) {
          // Rotate each piece about the cart's centre, tilt the whole cart a little.
          const wx = ox * cy + oz * sy, wz = -ox * sy + oz * cy;
          put("cart", new THREE.BoxGeometry(w, h, dd), d.x + wx, d.y + oy, d.z + wz, d.ry, 0, 0.06, mkCart);
        }
        break;
      }
      case "fire": fires.push(d); break;
      case "spawner": spawner = d; break;
      default: break;
    }
  }
  for (const [, b] of batches) {
    // Merge by hand: every geometry here has position, normal, uv, bake and an index.
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
    group.add(new THREE.Mesh(geo, b.mk()));
  }

  // Torches: one merged mesh, fullbright like the game's.
  const torchTex = nearest(IMG.torch_on);
  const tm = new THREE.Mesh(torchGeometry(a.torches), new THREE.MeshBasicMaterial({ map: torchTex, alphaTest: 0.4, side: THREE.DoubleSide, color: new THREE.Color(1.35, 1.2, 1.0) }));
  group.add(tm);

  // Water and lava: an animated 16 by 16 canvas, drawn from the strip, repeated over each rectangle.
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
  for (const r of a.waterRects) {
    const w = r.x1 - r.x0, d = r.z1 - r.z0, sx = Math.max(1, Math.round(w)), sz = Math.max(1, Math.round(d));
    const g = new THREE.PlaneGeometry(w, d, sx, sz); g.rotateX(-Math.PI / 2); g.translate((r.x0 + r.x1) / 2, r.y, (r.z0 + r.z1) / 2);
    const uv = g.attributes.uv; for (let i = 0; i < uv.count; i++) uv.setXY(i, uv.getX(i) * w, uv.getY(i) * d);
    const p = g.attributes.position, arr = new Float32Array(p.count * 3);
    for (let i = 0; i < p.count; i++) { const c = lightAt(p.getX(i), r.y + 0.05, p.getZ(i), 0, 1, 0); arr[i * 3] = c[0]; arr[i * 3 + 1] = c[1]; arr[i * 3 + 2] = c[2]; }
    g.setAttribute("bake", new THREE.BufferAttribute(arr, 3));
    const m = new THREE.Mesh(g, patchBake(new THREE.MeshLambertMaterial({ map: wa.t, transparent: true, opacity: 0.78, color: 0x6f95b0, depthWrite: false })));
    m.renderOrder = 2; group.add(m);
  }
  const lavaMat = new THREE.MeshBasicMaterial({ map: la ? la.t : null, color: new THREE.Color(1.5, 1.05, 0.75) });
  for (const r of a.lavaRects) {
    const w = r.x1 - r.x0, d = r.z1 - r.z0;
    const g = new THREE.PlaneGeometry(w, d); g.rotateX(-Math.PI / 2); g.translate((r.x0 + r.x1) / 2, r.y, (r.z0 + r.z1) / 2);
    const uv = g.attributes.uv; for (let i = 0; i < uv.count; i++) uv.setXY(i, uv.getX(i) * w, uv.getY(i) * d);
    group.add(new THREE.Mesh(g, lavaMat));
  }
  upd.push((t) => { if (wa) wa.set(Math.floor(t * 8)); if (la) la.set(Math.floor(t * 6)); });

  // Fire: two crossed planes of the fire strip, frame by frame.
  if (fires.length && IMG.fire_layer_0) {
    const f = animCanvas(IMG.fire_layer_0, 32);
    const fm = new THREE.MeshBasicMaterial({ map: f.t, transparent: true, alphaTest: 0.2, side: THREE.DoubleSide, color: new THREE.Color(1.5, 1.25, 1.0), depthWrite: false });
    const list = [];
    for (const d of fires) for (const r of [0.6, 0.6 + Math.PI / 2]) {
      const g = new THREE.PlaneGeometry(1, 1); g.translate(0, 0.5, 0); g.rotateY(r + (d.x * 7 % 1)); g.translate(d.x, d.y, d.z); list.push(g);
    }
    let nv = 0, ni = 0; for (const g of list) { nv += g.attributes.position.count; ni += g.index.count; }
    const pos = new Float32Array(nv * 3), uv = new Float32Array(nv * 2), ix = new Uint32Array(ni); let ov = 0, oi = 0;
    for (const g of list) { pos.set(g.attributes.position.array, ov * 3); uv.set(g.attributes.uv.array, ov * 2); for (let i = 0; i < g.index.count; i++) ix[oi + i] = g.index.array[i] + ov; ov += g.attributes.position.count; oi += g.index.count; }
    const geo = new THREE.BufferGeometry(); geo.setAttribute("position", new THREE.BufferAttribute(pos, 3)); geo.setAttribute("uv", new THREE.BufferAttribute(uv, 2)); geo.setIndex(new THREE.BufferAttribute(ix, 1));
    group.add(new THREE.Mesh(geo, fm));
    upd.push((t) => f.set(Math.floor(t * 10)));
  }

  // The spawner: the cage cube, a small mob turning inside.
  let mob = null;
  if (spawner) {
    const sm = new THREE.MeshLambertMaterial({ map: nearest(IMG.mob_spawner), transparent: true, alphaTest: 0.4, side: THREE.DoubleSide });
    patchBake(sm, { fixed: new THREE.Vector3(...lightAt(spawner.x, spawner.y + 0.5, spawner.z, 0, 0.3, 0, { omni: true })) });
    const cage = new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), sm);
    cage.position.set(spawner.x, spawner.y + 0.5, spawner.z);
    // A dark core so the cage does not read as empty glass.
    const core = new THREE.Mesh(new THREE.BoxGeometry(0.96, 0.96, 0.96), new THREE.MeshBasicMaterial({ color: 0x0b0a10, side: THREE.BackSide }));
    core.position.copy(cage.position);
    group.add(core, cage);
    try {
      mob = makeMob("Zombie", { scale: 0.3 });
      mob.root.position.set(spawner.x, spawner.y + 0.12, spawner.z);
      mob.root.traverse(o => { if (o.isMesh && o.material) { o.material.emissive = new THREE.Color(0x201008); } });
      group.add(mob.root);
      upd.push((t, dt) => { mob.root.rotation.y = t * 2.2; try { mob.anim(t, dt, {}); } catch { /* optional */ } });
    } catch { /* no mob */ }
  }

  return { group, update: (t, dt) => { for (const f of upd) f(t, dt); }, spawner, mob };
}
