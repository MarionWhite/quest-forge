// More decor for the Krypt's newer kinds: carpets, banners, stained panes, plates, crossed-plane
// plants, ladders, wooden doors, block-like furniture and static mob figures. Each handler adds to the dresser's per-chunk
// batches (put) with a shared material, so a hundred of them cost one draw call per kind.
import * as THREE from "three";
import { makeMob } from "../lib/mc/mobs.js";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";
import { patchBake } from "./krypt.js";
import { CLAY_COLORS } from "./blocks.js";

// The visible meshes of a posed mob, merged per material into one group with the root's own transform; null when the
// parts can't be merged (mixed attributes, multi-material or skinned parts), and the caller keeps the rig.
const KEEP = ["position", "normal", "uv"];
function bakeFigure(root) {
  root.updateMatrixWorld(true);
  const inv = root.matrixWorld.clone().invert(), by = new Map(), m = new THREE.Matrix4();
  let ok = true;
  root.traverseVisible((o) => { if (!o.isMesh) return; if (Array.isArray(o.material) || o.isSkinnedMesh || o.isInstancedMesh || o.matrixWorld.determinant() < 0) { ok = false; return; } const l = by.get(o.material) || []; by.set(o.material, l); l.push(o); });
  if (!ok || !by.size) return null;
  const out = new THREE.Group(); out.position.copy(root.position); out.quaternion.copy(root.quaternion); out.scale.copy(root.scale);
  for (const [mat, list] of by) {
    const geos = list.map((o) => { let g = o.geometry.index ? o.geometry.toNonIndexed() : o.geometry.clone(); g.applyMatrix4(m.multiplyMatrices(inv, o.matrixWorld)); for (const k of Object.keys(g.attributes)) if (!KEEP.includes(k)) g.deleteAttribute(k); g.morphAttributes = {}; return g; });
    const names = (g) => Object.keys(g.attributes).sort().join();
    if (geos.some((g) => names(g) !== names(geos[0]) || !g.attributes.position)) { geos.forEach((g) => g.dispose()); return null; }
    const merged = mergeGeometries(geos, false); geos.forEach((g) => g.dispose());
    if (!merged) return null;
    out.add(new THREE.Mesh(merged, mat));
  }
  return out;
}

export function addDecor(dresser, IMG) {
  const X = dresser.extra, { tex, plane } = dresser;
  const lam = (name, o = {}) => () => patchBake(new THREE.MeshLambertMaterial({ map: tex(IMG[name]), ...o }));
  const cutm = (name, o = {}) => lam(name, { alphaTest: 0.4, side: THREE.DoubleSide, ...o });
  const box = (w, h, d, y0 = 0) => { const g = new THREE.BoxGeometry(w, h, d); g.translate(0, y0 + h / 2, 0); return g; };
  const guard = (name) => !!IMG[name];

  X.carpet = (d, put) => { const n = "wool_colored_" + (CLAY_COLORS[d.color] || "red"); if (!guard(n)) return; put("carpet:" + n, box(d.w || 1, 0.0625, d.d || 1), d.x, d.y, d.z, d.ry || 0, 0, 0, lam(n)); };
  X.banner = (d, put) => {
    const n = "wool_colored_" + (CLAY_COLORS[d.color] || "red"); if (!guard(n)) return;
    const g = plane(d.w || 0.8, d.h || 2); put("banner:" + n, g, d.x, d.y, d.z, d.ry || 0, 0, 0, cutm(n));
  };
  X.pane = (d, put) => {
    const n = d.tex || "glass_red"; if (!guard(n)) return;
    put("pane:" + n, plane(d.w || 1, d.h || 1), d.x, d.y, d.z, d.ry || 0, d.flat ? -Math.PI / 2 : 0, 0, cutm(n, { alphaTest: 0.05, transparent: true, opacity: 0.8, depthWrite: false, emissive: new THREE.Color(0.18, 0.18, 0.2) }));
  };
  X.plate = (d, put) => { if (!guard("stone")) return; put("plate", box(0.875, 0.0625, 0.875), d.x, d.y, d.z, d.ry || 0, 0, 0, lam("stone")); };
  // Two crossed planes: a flower, a mushroom, a fern, a sapling, the brewing stand.
  X.cross = (d, put) => {
    const n = d.tex; if (!guard(n)) return; const mk = cutm(n);
    for (const da of [Math.PI / 4, -Math.PI / 4]) put("cross:" + n, (() => { const g = plane(d.s || 0.7, d.s || 0.7); g.translate(0, (d.s || 0.7) / 2, 0); return g; })(), d.x, d.y, d.z, (d.ry || 0) + da, 0, 0, mk);
  };
  X.ladder = (d, put) => { if (!guard("ladder")) return; put("ladder", plane(1, d.h || 2), d.x, d.y, d.z, d.ry || 0, 0, 0, cutm("ladder")); };
  X.wdoor = (d, put) => { for (const [dy, n] of [[0.5, "door_wood_lower"], [1.5, "door_wood_upper"]]) if (guard(n)) put("wd:" + n, new THREE.BoxGeometry(0.1875, 1, 1), d.x, d.y + dy, d.z, d.ry || 0, 0, 0, lam(n)); };
  // A block-like piece of furniture: sides, a top plane.
  X.cube = (d, put) => {
    const side = d.side, top = d.top || d.side; if (!guard(side) || !guard(top)) return;
    const h = d.h || 1, w = d.w || 1, dd = d.d || w;
    put("cube:" + side, box(w, h, dd), d.x, d.y, d.z, d.ry || 0, 0, 0, lam(side));
    put("cubeTop:" + top, plane(w, dd), d.x, d.y + h + 0.003, d.z, d.ry || 0, -Math.PI / 2, 0, lam(top));
  };
  X.bed = (d, put) => {
    for (const [k, oz] of [["head", -0.5], ["feet", 0.5]]) {
      const side = "bed_" + k + "_side", top = "bed_" + k + "_top"; if (!guard(top)) continue;
      const cy = Math.cos(d.ry || 0), sy = Math.sin(d.ry || 0);
      put("bedb:" + k, box(1, 0.56, 1, 0.1), d.x + oz * sy, d.y, d.z + oz * cy, d.ry || 0, 0, 0, lam(guard(side) ? side : top));
      put("bedt:" + k, plane(1, 1), d.x + oz * sy, d.y + 0.663, d.z + oz * cy, d.ry || 0, -Math.PI / 2, 0, lam(top));
    }
  };
  // A static mob figure (a skeleton in a cell, a zombie behind bars): the real model, standing still, dimmed. glow adds a
  // flat colour (a silhouette); lit shows the skin at that brightness (a figure in lamplight or in clear ice).
  X.mob = (d, put, ctx) => {
    try {
      const mob = makeMob(d.mob || "Skeleton", { scale: d.scale || 0.9 });
      mob.root.position.set(d.x, d.y, d.z); mob.root.rotation.y = d.ry || 0;
      mob.root.traverse((o) => { if (o.isMesh && o.material) { const ms = Array.isArray(o.material) ? o.material : [o.material]; for (const m of ms) if (m.isMeshLambertMaterial) { if (d.lit) { m.emissive = new THREE.Color(d.lit); m.emissiveMap = m.map; } else m.emissive = new THREE.Color(d.glow || 0x120a08); } } });
      // A still figure needs no rig: bake it to one mesh per material (a skeleton in a cell was six draw calls, now one).
      const root = (!d.idle && bakeFigure(mob.root)) || mob.root;
      ctx.group.add(root); ctx.mobs.push(mob); ctx.far.push([root, d, d.r || 26]);
      if (d.idle) ctx.ups.push((t, dt) => { try { mob.anim(t, dt, {}); } catch { /* optional */ } });
      ctx.disposers.push(() => root.traverse((o) => { if (o.geometry) o.geometry.dispose(); }));
    } catch { /* no model */ }
  };
}
