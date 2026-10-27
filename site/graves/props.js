// Minecraft 1.7.10 props for the Krypt, close-up correct. Each is built from the game's own model:
//   chest           ModelChest: body 14x10x14, lid 14x5x14 from 9 to 14, latch 2x4x1 on the front, the 64x64 entity texture
//   minecart        ModelMinecart: floor 20x16x2, inner floor 18x14x1, four walls 16x8x2, minecart.png (64x32)
//   cauldron        RenderBlocks.renderBlockCauldron: the shell, inner walls 2/16 in, the inner floor at 4/16, water at (6+3n)/16
//   anvil           renderBlockAnvilOrient: base 12x4x12, step 8x1x10, neck 4x5x8, top 10x6x16 with the anvil_top face
//   brewing stand   renderBlockBrewingStand: the 2x14x2 rod, three 6x2x6 bases, three arms (bottle or empty half)
//   enchanting table 12/16 tall with its top, side and bottom
//   slab            a bottom half slab (cobblestone, mossy cobblestone, stone): the debris where a roof gave way
// A builder returns parts [{ tex, geo, cut }] in block units: origin at the bottom centre of the block, front toward +z.
import * as THREE from "three";

// Face corners as seen from outside: top-left, top-right, bottom-right, bottom-left (px, the block's corner at 0).
const CORNERS = {
  south: (a, b) => [[a[0], b[1], b[2]], [b[0], b[1], b[2]], [b[0], a[1], b[2]], [a[0], a[1], b[2]]],
  north: (a, b) => [[b[0], b[1], a[2]], [a[0], b[1], a[2]], [a[0], a[1], a[2]], [b[0], a[1], a[2]]],
  east: (a, b) => [[b[0], b[1], b[2]], [b[0], b[1], a[2]], [b[0], a[1], a[2]], [b[0], a[1], b[2]]],
  west: (a, b) => [[a[0], b[1], a[2]], [a[0], b[1], b[2]], [a[0], a[1], b[2]], [a[0], a[1], a[2]]],
  up: (a, b) => [[a[0], b[1], a[2]], [b[0], b[1], a[2]], [b[0], b[1], b[2]], [a[0], b[1], b[2]]],
  down: (a, b) => [[a[0], a[1], b[2]], [b[0], a[1], b[2]], [b[0], a[1], a[2]], [a[0], a[1], a[2]]]
};
const NORMAL = { south: [0, 0, 1], north: [0, 0, -1], east: [1, 0, 0], west: [-1, 0, 0], up: [0, 1, 0], down: [0, -1, 0] };
// The default UV of a face from the box's bounds, as a 1.7.10 block face picks its part of a 16x16 texture.
const AUTO = {
  south: (a, b) => [a[0], 16 - b[1], b[0], 16 - a[1]], north: (a, b) => [16 - b[0], 16 - b[1], 16 - a[0], 16 - a[1]],
  east: (a, b) => [16 - b[2], 16 - b[1], 16 - a[2], 16 - a[1]], west: (a, b) => [a[2], 16 - b[1], b[2], 16 - a[1]],
  up: (a, b) => [a[0], a[2], b[0], b[2]], down: (a, b) => [a[0], 16 - b[2], b[0], 16 - a[2]]
};

// A box from `a` to `b` in pixels. faces: { south: [u0, v0, u1, v1] | true (auto) , ... } in texture pixels; faces left out
// are not drawn. inward flips every face to look into the box (the cauldron's inner walls).
export function mcBox(a, b, faces, tw = 16, th = 16, inward = false) {
  const pos = [], nrm = [], uv = [], idx = [];
  for (const f of Object.keys(faces)) {
    const r = faces[f] === true ? AUTO[f](a, b) : faces[f];
    if (!r) continue;
    const c = CORNERS[f](a, b), n = NORMAL[f], base = pos.length / 3;
    const uvs = [[r[0], r[1]], [r[2], r[1]], [r[2], r[3]], [r[0], r[3]]];
    for (let q = 0; q < 4; q++) {
      pos.push((c[q][0] - 8) / 16, c[q][1] / 16, (c[q][2] - 8) / 16);
      nrm.push(inward ? -n[0] : n[0], inward ? -n[1] : n[1], inward ? -n[2] : n[2]);
      uv.push(uvs[q][0] / tw, 1 - uvs[q][1] / th);
    }
    if (inward) idx.push(base, base + 2, base + 3, base, base + 1, base + 2);
    else idx.push(base, base + 3, base + 2, base, base + 2, base + 1);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute("normal", new THREE.Float32BufferAttribute(nrm, 3));
  g.setAttribute("uv", new THREE.Float32BufferAttribute(uv, 2));
  g.setIndex(idx);
  return g;
}
// The six faces of a 1.7.10 model box with its texture offset (u, v) and size (w, h, d), as ModelBox lays them out.
function boxUV(u, v, w, h, d) {
  return {
    up: [u + d, v, u + d + w, v + d], down: [u + d + w, v, u + d + 2 * w, v + d],
    west: [u, v + d, u + d, v + d + h], south: [u + d, v + d, u + d + w, v + d + h],
    east: [u + d + w, v + d, u + 2 * d + w, v + d + h], north: [u + 2 * d + w, v + d, u + 2 * d + 2 * w, v + d + h]
  };
}
const ALL = { south: true, north: true, east: true, west: true, up: true, down: true };
const merge = (list) => { const out = new THREE.BufferGeometry(); let nv = 0, ni = 0; for (const g of list) { nv += g.attributes.position.count; ni += g.index.count; }
  const p = new Float32Array(nv * 3), n = new Float32Array(nv * 3), t = new Float32Array(nv * 2), ix = new Uint32Array(ni); let ov = 0, oi = 0;
  for (const g of list) { p.set(g.attributes.position.array, ov * 3); n.set(g.attributes.normal.array, ov * 3); t.set(g.attributes.uv.array, ov * 2); for (let i = 0; i < g.index.count; i++) ix[oi + i] = g.index.array[i] + ov; ov += g.attributes.position.count; oi += g.index.count; g.dispose(); }
  out.setAttribute("position", new THREE.BufferAttribute(p, 3)); out.setAttribute("normal", new THREE.BufferAttribute(n, 3)); out.setAttribute("uv", new THREE.BufferAttribute(t, 2)); out.setIndex(new THREE.BufferAttribute(ix, 1));
  return out; };

export const PROPS = {
  // The chest faces +z: the latch and the front of the texture toward the room.
  chest() {
    const e = 0.02;   // the lid sits a hair proud of the body, so their shared pixel row never flickers
    return [{ tex: "chest", geo: merge([
      mcBox([1, 0, 1], [15, 10, 15], boxUV(0, 19, 14, 10, 14), 64, 64),
      mcBox([1 - e, 9, 1 - e], [15 + e, 14, 15 + e], boxUV(0, 0, 14, 5, 14), 64, 64),
      mcBox([7, 7, 15], [9, 11, 16], boxUV(0, 0, 2, 4, 1), 64, 64)
    ]) }];
  },
  // The minecart, its long axis along x. Walls show their inner face (u 2..18) inward and the outer (20..36) outward.
  minecart() {
    const W = (a, b, inner, along) => {
      // along: "x" for the side walls, "z" for the end walls; which face is inner depends on the wall's side.
      const f = along === "x" ? (inner > 0 ? { south: [2, 2, 18, 10], north: [20, 2, 36, 10] } : { north: [2, 2, 18, 10], south: [20, 2, 36, 10] })
        : (inner > 0 ? { east: [2, 2, 18, 10], west: [20, 2, 36, 10] } : { west: [2, 2, 18, 10], east: [20, 2, 36, 10] });
      const top = along === "x" ? { up: [2, 0, 18, 2] } : { up: [2, 0, 18, 2] };
      const ends = along === "x" ? { east: [18, 2, 20, 10], west: [0, 2, 2, 10] } : { south: [18, 2, 20, 10], north: [0, 2, 2, 10] };
      return mcBox(a, b, { ...f, ...top, ...ends }, 64, 32);
    };
    return [{ tex: "minecart", cut: true, geo: merge([
      mcBox([-2, 0, 0], [18, 2, 16], { down: [2, 12, 22, 28], south: [2, 10, 22, 12], north: [2, 10, 22, 12], east: [0, 12, 2, 28], west: [0, 12, 2, 28] }, 64, 32),
      mcBox([-1, 2, 1], [17, 2.02, 15], { up: [45, 11, 63, 25] }, 64, 32),
      W([0, 2, 14], [16, 10, 16], -1, "x"), W([0, 2, 0], [16, 10, 2], 1, "x"),
      W([16, 2, 0], [18, 10, 16], -1, "z"), W([-2, 2, 0], [0, 10, 16], 1, "z")
    ]) }];
  },
  // The cauldron: water 0 (dry) to 3 (full).
  cauldron(d) {
    const parts = [
      { tex: "cauldron_side", cut: true, geo: merge([mcBox([0, 0, 0], [16, 16, 16], { south: true, north: true, east: true, west: true }),
        mcBox([2, 0, 2], [14, 16, 14], { south: true, north: true, east: true, west: true }, 16, 16, true)]) },
      { tex: "cauldron_top", cut: true, geo: mcBox([0, 0, 0], [16, 16, 16], { up: true }) },
      { tex: "cauldron_bottom", cut: true, geo: mcBox([0, 0, 0], [16, 16, 16], { down: true }) },
      { tex: "cauldron_inner", geo: merge([mcBox([0, 4, 0], [16, 4, 16], { up: true }), mcBox([0, 4, 0], [16, 4, 16], { down: true })]) }
    ];
    const n = d.water === true ? 3 : d.water | 0;
    if (n > 0) parts.push({ tex: "water", geo: mcBox([2, 0, 2], [14, 6 + 3 * Math.min(3, n), 14], { up: [2, 2, 14, 14] }) });
    return parts;
  },
  anvil() {
    return [
      { tex: "anvil_base", geo: merge([mcBox([2, 0, 2], [14, 4, 14], ALL), mcBox([4, 4, 3], [12, 5, 13], ALL), mcBox([6, 5, 4], [10, 10, 12], ALL),
        mcBox([3, 10, 0], [13, 16, 16], { south: true, north: true, east: true, west: true, down: true })]) },
      { tex: "anvil_top_damaged_0", geo: mcBox([3, 10, 0], [13, 16, 16], { up: true }) }
    ];
  },
  brewing(d) {
    const fins = [];
    for (let q = 0; q < 3; q++) {
      const a = q * Math.PI * 2 / 3 + Math.PI / 2, full = d.bottles ? (d.bottles >> q) & 1 : 1;
      const g = new THREE.PlaneGeometry(0.5, 1); g.translate(0.25, 0.5, 0);
      // From the rod (u 8) outward: to u 16 for an empty arm, mirrored to u 0 for an arm that holds a bottle.
      const uv = g.attributes.uv; for (let i = 0; i < uv.count; i++) uv.setX(i, full ? 0.5 - uv.getX(i) * 0.5 : 0.5 + uv.getX(i) * 0.5);
      g.rotateY(a); fins.push(g);
    }
    const fin = merge(fins);
    return [
      { tex: "brewing_stand", cut: true, geo: mcBox([7, 0, 7], [9, 14, 9], ALL) },
      { tex: "brewing_stand", cut: true, double: true, geo: fin },
      { tex: "brewing_stand_base", geo: merge([mcBox([9, 0, 5], [15, 2, 11], ALL), mcBox([2, 0, 1], [8, 2, 7], ALL), mcBox([2, 0, 9], [8, 2, 15], ALL)]) }
    ];
  },
  enchanting() {
    return [
      { tex: "enchanting_table_side", geo: mcBox([0, 0, 0], [16, 12, 16], { south: true, north: true, east: true, west: true }) },
      { tex: "enchanting_table_top", geo: mcBox([0, 0, 0], [16, 12, 16], { up: true }) },
      { tex: "enchanting_table_bottom", geo: mcBox([0, 0, 0], [16, 12, 16], { down: true }) }
    ];
  },
  slab(d) { return [{ tex: d.tex || "cobblestone", geo: mcBox([0, 0, 0], [16, 8, 16], ALL) }]; },
  // Stairs (a pew, a step): the bottom half and the back half, the back toward -z. d.tex: the material.
  stair(d) { return [{ tex: d.tex || "planks_oak", geo: merge([mcBox([0, 0, 0], [16, 8, 16], ALL), mcBox([0, 8, 0], [16, 16, 8], ALL)]) }]; },
  // A piston facing +z: the block, or extended (base 12 deep, the arm and the head in the next block).
  piston(d) {
    if (!d.out) return [
      { tex: "piston_side", geo: mcBox([0, 0, 0], [16, 16, 16], { east: true, west: true, up: [0, 0, 16, 16], down: [0, 0, 16, 16] }) },
      { tex: "piston_top_normal", geo: mcBox([0, 0, 0], [16, 16, 16], { south: true }) },
      { tex: "piston_bottom", geo: mcBox([0, 0, 0], [16, 16, 16], { north: true }) }];
    return [
      { tex: "piston_side", geo: merge([mcBox([0, 0, 0], [16, 16, 12], { east: [4, 0, 16, 16], west: [0, 0, 12, 16], up: [0, 4, 16, 16], down: [0, 4, 16, 16] }),
        mcBox([6, 6, 12], [10, 10, 28], { east: [0, 0, 16, 4], west: [0, 0, 16, 4], up: [0, 0, 16, 4], down: [0, 0, 16, 4] }),
        mcBox([0, 0, 28], [16, 16, 32], { east: [0, 0, 4, 16], west: [12, 0, 16, 16], up: [0, 0, 16, 4], down: [0, 0, 16, 4] })]) },
      { tex: "piston_top_normal", geo: merge([mcBox([0, 0, 28], [16, 16, 32], { south: true, north: true })]) },
      { tex: "piston_bottom", geo: mcBox([0, 0, 0], [16, 16, 12], { north: true, south: true }) }];
  },
  // ModelBoat's hull (bottom 24x16x4, sides 6 high), in oak planks: the 1.7.10 boat texture is plank-like.
  boat() {
    return [{ tex: "planks_oak", geo: merge([mcBox([-4, 0, 0], [20, 4, 16], ALL), mcBox([-2, 4, -1], [18, 10, 1], ALL), mcBox([-2, 4, 15], [18, 10, 17], ALL),
      mcBox([-4, 4, 0], [-2, 10, 16], ALL), mcBox([18, 4, 0], [20, 10, 16], ALL)]) }];
  },
  // A block of ice around something frozen: translucent, h blocks tall.
  ice(d) { return [{ tex: "ice", glass: true, geo: mcBox([0, 0, 0], [16, 16 * (d.h || 1), 16], { south: [0, 0, 16, 16 * (d.h || 1)], north: [0, 0, 16, 16 * (d.h || 1)], east: [0, 0, 16, 16 * (d.h || 1)], west: [0, 0, 16, 16 * (d.h || 1)], up: true }, 16, 16) }]; },
  // The flower pot (6x6x6 at the bottom centre) with a red mushroom, as the swamp hut keeps it.
  pot(d) {
    const parts = [{ tex: "flower_pot", cut: true, geo: mcBox([5, 0, 5], [11, 6, 11], { south: [5, 10, 11, 16], north: [5, 10, 11, 16], east: [5, 10, 11, 16], west: [5, 10, 11, 16], down: [5, 5, 11, 11] }) },
      { tex: "dirt", geo: mcBox([6, 4, 6], [10, 4, 10], { up: true }) }];
    const pl = d.plant || "mushroom_red", x = new THREE.PlaneGeometry(0.75, 0.75); x.translate(0, 0.25 + 0.375, 0);
    const y = x.clone(); x.rotateY(Math.PI / 4); y.rotateY(-Math.PI / 4);
    parts.push({ tex: pl, cut: true, double: true, geo: merge([x, y]) });
    return parts;
  },
  // A filled map in an item frame on the wall behind the cell (it covers the whole block face): d.cell picks the map.
  map(d) { const g = new THREE.PlaneGeometry(d.flat ? 0.9 : 1, d.flat ? 0.9 : 1); if (d.flat) g.rotateX(-Math.PI / 2); else g.translate(0, 0.5, -0.47); const c = (d.cell | 0) % 16, uv = g.attributes.uv;
    for (let i = 0; i < uv.count; i++) uv.setXY(i, ((c % 4) + uv.getX(i)) / 4, 1 - (Math.floor(c / 4) + 1 - uv.getY(i)) / 4);
    return [{ tex: "@maps", geo: g }]; },
  // Redstone dust, a straight line along z, in the red of a powered wire (the texture is grey; the game tints it).
  dust() { return [{ tex: "redstone_dust_line", cut: true, tint: 0xd02010, geo: mcBox([0, 0.25, 0], [16, 0.25, 16], { up: true }) }]; },
  // A trapdoor lying shut on the floor (3 px).
  trapdoor() { return [{ tex: "trapdoor", cut: true, geo: mcBox([0, 0, 0], [16, 3, 16], ALL) }]; }
};
// A fence post (4x16x4, h blocks tall) and, with len, the two bars (2x3 at 6..9 and 12..15) that join it to the next post
// len blocks along local +z, as the game joins neighbouring fences. Placed where the caller puts it (not snapped).
PROPS.fence = (d) => {
  const h = (d.h || 1) * 16, list = [mcBox([6, 0, 6], [10, h, 10], ALL)];
  if (d.len) for (const y of [6, 12]) if (y + 3 <= h + 0.01) list.push(mcBox([7, y, 10], [9, y + 3, 16 * d.len + 6], { east: true, west: true, up: true, down: true }));
  return [{ tex: d.tex || "planks_oak", geo: merge(list) }];
};
PROPS.boat.free = true; PROPS.fence.free = true;
// The textures the props use beyond the block set (blocks.js DECOR_TEX takes these).
export const PROP_TEX = ["chest", "minecart", "cauldron_side", "cauldron_top", "cauldron_bottom", "cauldron_inner", "anvil_base", "anvil_top_damaged_0",
  "brewing_stand", "brewing_stand_base", "enchanting_table_side", "enchanting_table_top", "enchanting_table_bottom", "cobblestone", "cobblestone_mossy", "stone_slab_top",
  "piston_side", "piston_top_normal", "piston_bottom", "ice", "flower_pot", "redstone_dust_line", "trapdoor", "planks_oak", "planks_spruce", "dirt", "mushroom_red"];
