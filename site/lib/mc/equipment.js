// Armour, enchantment glint and held items for the biped mobs, ported from 1.7.10 (MCP sources):
//   RenderBiped.shouldRenderPass     two ModelBiped armour models, inflate 1.0 (head, chest, boots) and 0.5
//                                    (leggings), textures models/armor/<mat>_layer_1 (layer_2 for leggings)
//   RendererLivingEntity glint       two additive passes, tint (0.38, 0.19, 0.608), blend SRC_COLOR / ONE
//   RenderBiped.renderEquippedItem   the right-hand transform, then ItemRenderer.renderItem (a 1/16 thick
//                                    extruded sprite) or the OreSpawn IItemRenderer (the Queen Battle Axe)
// OreSpawn armour textures come from ItemOreSpawnArmor.getArmorTexture ("orespawn:queen_1.png" ...).
//
// Equipment format (same as `actions[].equipment` in site/lucky/data/lucky.json): an array of item ids,
// "minecraft:diamond_sword", "OreSpawn:OreSpawn_QueenHelmet". An entry may also be {id, ench: true|false}.
// A plain string is enchanted when opts.enchanted says so (default: true for "minecraft:" ids, because
// every vanilla piece in the Lucky drops carries the #lucky...Enchantments lists; false for OreSpawn).
import * as THREE from 'three';
import { tex } from './textures.js';
import { OS_MODELS } from './orespawn-models.js';
import { VANILLA_MODELS } from './vanilla-models.js';

const D = Math.PI / 180;
const FLIP = new THREE.Matrix4().makeScale(-1, -1, 1);          // model frame <-> three frame (a half turn about z)
const gT = (x, y, z) => new THREE.Matrix4().makeTranslation(x, y, z);
const gS = (x, y = x, z = x) => new THREE.Matrix4().makeScale(x, y, z);
const gR = (deg, x, y, z) => new THREE.Matrix4().makeRotationAxis(new THREE.Vector3(x, y, z).normalize(), deg * D);
const chain = (...ms) => ms.reduce((a, m) => a.multiply(m), new THREE.Matrix4());

// ---------------------------------------------------------------------------------------- item tables
const MATS = { wooden: 'wood', wood: 'wood', stone: 'stone', iron: 'iron', gold: 'gold', golden: 'gold', diamond: 'diamond', leather: 'leather', chainmail: 'chainmail', chain: 'chainmail' };
const SLOTS = { helmet: 'head', chestplate: 'chest', leggings: 'legs', boots: 'feet' };
const OS_SLOTS = { Helmet: 'head', Body: 'chest', Legs: 'legs', Boots: 'feet', Chest: 'chest', Leggings: 'legs' };
const OS_ARMOUR = new Set(['amethyst', 'emerald', 'experience', 'lapis', 'lavaeel', 'mobzilla', 'mothscale', 'peacock', 'pink', 'queen', 'royal', 'ruby', 'tigerseye', 'ultimate']);
const OS_WEAPONS = { ultimatesword: 'ultimatesword.png', royalsword: 'royalsmall.png', royal: 'royalsmall.png', ultimateaxe: 'ultimateaxe.png' };

// -> { kind: 'armor', slot, layer1, layer2 } | { kind: 'sprite', tex, bow? } | { kind: 'queenAxe' } | null
export function classify(rawId) {
  const id = String(rawId);
  let m = /^(?:minecraft:)?(leather|chainmail|iron|diamond|gold|golden)_(helmet|chestplate|leggings|boots)$/i.exec(id);
  if (m) { const mat = MATS[m[1].toLowerCase()]; return { kind: 'armor', slot: SLOTS[m[2].toLowerCase()], layer1: `armor/${mat}_layer_1.png`, layer2: `armor/${mat}_layer_2.png`, overlay: mat === 'leather' }; }
  m = /^(?:minecraft:)?(wooden|wood|stone|iron|gold|golden|diamond)_(sword|axe|pickaxe|shovel|hoe)$/i.exec(id);
  if (m) return { kind: 'sprite', tex: `items/${MATS[m[1].toLowerCase()]}_${m[2].toLowerCase()}.png` };
  if (/^(?:minecraft:)?bow$/i.test(id)) return { kind: 'sprite', tex: 'items/bow_standby.png', bow: true };
  m = /^OreSpawn:(?:OreSpawn_)?(.+?)(Helmet|Body|Chest|Legs|Leggings|Boots)$/i.exec(id);
  if (m) {
    const name = m[1].toLowerCase().replace(/[^a-z]/g, '').replace('tigerseye', 'tigerseye');
    const slot = OS_SLOTS[m[2][0].toUpperCase() + m[2].slice(1).toLowerCase()];
    if (slot && OS_ARMOUR.has(name)) return { kind: 'armor', slot, layer1: `armor/${name}_1.png`, layer2: `armor/${name}_2.png` };
    return null;
  }
  m = /^OreSpawn:(?:OreSpawn_)?(.+)$/i.exec(id);
  if (m) {
    const n = m[1].toLowerCase().replace(/[^a-z]/g, '');
    if (n === 'queenbattleaxe') return { kind: 'queenAxe' };
    if (OS_WEAPONS[n]) return { kind: 'sprite', tex: 'items/' + OS_WEAPONS[n] };
  }
  return null;
}

// Named sets, as in the Lucky drops (for the lineup: ?ids=Zombie@diamond,Zombie@queen)
export const EQUIP_PRESETS = {
  diamond: ['minecraft:diamond_sword', 'minecraft:diamond_helmet', 'minecraft:diamond_chestplate', 'minecraft:diamond_leggings', 'minecraft:diamond_boots'],
  iron: ['minecraft:iron_sword', 'minecraft:iron_helmet', 'minecraft:iron_chestplate', 'minecraft:iron_leggings', 'minecraft:iron_boots'],
  queen: ['OreSpawn:OreSpawn_QueenBattleAxe', 'OreSpawn:OreSpawn_QueenHelmet', 'OreSpawn:OreSpawn_QueenBody', 'OreSpawn:OreSpawn_QueenLegs', 'OreSpawn:OreSpawn_QueenBoots'],
  queenarmor: ['OreSpawn:OreSpawn_QueenHelmet', 'OreSpawn:OreSpawn_QueenBody', 'OreSpawn:OreSpawn_QueenLegs', 'OreSpawn:OreSpawn_QueenBoots'],
  ultimate: ['OreSpawn:OreSpawn_UltimateSword', 'OreSpawn:OreSpawn_UltimateHelmet', 'OreSpawn:OreSpawn_UltimateBody', 'OreSpawn:OreSpawn_UltimateLegs', 'OreSpawn:OreSpawn_UltimateBoots'],
  royal: ['OreSpawn:OreSpawn_RoyalSword', 'OreSpawn:OreSpawn_UltimateHelmet', 'OreSpawn:OreSpawn_UltimateBody', 'OreSpawn:OreSpawn_UltimateLegs', 'OreSpawn:OreSpawn_UltimateBoots'],
  gold: ['minecraft:golden_sword', 'minecraft:golden_helmet', 'minecraft:golden_chestplate', 'minecraft:golden_leggings', 'minecraft:golden_boots'],
};

export function parseEquipment(list, opts = {}) {
  const out = { head: null, chest: null, legs: null, feet: null, hand: null };
  const enchDefault = opts.enchanted;
  for (const e of Array.isArray(list) ? list : []) {
    const id = typeof e === 'string' ? e : e && e.id;
    if (!id) continue;
    const c = classify(id);
    if (!c) continue;
    let ench = typeof e === 'object' && e.ench != null ? !!e.ench : null;
    if (ench == null) ench = typeof enchDefault === 'boolean' ? enchDefault : Array.isArray(enchDefault) ? enchDefault.includes(id) : /^minecraft:/i.test(id);
    c.id = id; c.ench = ench;
    if (c.kind === 'armor') out[c.slot] = c; else out.hand = c;
  }
  return out;
}

// ---------------------------------------------------------------------------------------- glint
const GLINT_VS = `
varying vec2 vMask; varying vec2 vG;
#ifdef GUV
attribute vec2 guv;
#endif
uniform mat3 uvm;
void main() {
  vMask = uv;
  #ifdef GUV
  vec2 g = guv;
  #else
  vec2 g = uv;
  #endif
  vG = (uvm * vec3(g, 1.0)).xy;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}`;
// 1.7.10 does its blending on encoded values, so this shader writes raw texels (no colour-space pass).
const GLINT_FS = `
varying vec2 vMask; varying vec2 vG;
uniform sampler2D mask; uniform sampler2D glint; uniform vec3 tint;
void main() {
  if (texture2D(mask, vMask).a < 0.1) discard;
  gl_FragColor = vec4(texture2D(glint, vG).rgb * tint, 1.0);
}`;

function glintTexture() {
  const t = tex('misc/enchanted_item_glint.png', { wrap: true });
  t.colorSpace = THREE.NoColorSpace;
  return t;
}
function glintMaterial(mask, guv) {
  return new THREE.ShaderMaterial({
    uniforms: { mask: { value: mask }, glint: { value: glintTexture() }, uvm: { value: new THREE.Matrix3() }, tint: { value: new THREE.Vector3(0.5 * 0.76, 0.25 * 0.76, 0.8 * 0.76) } },
    defines: guv ? { GUV: 1 } : {},
    vertexShader: GLINT_VS, fragmentShader: GLINT_FS,
    transparent: true, depthWrite: false, side: THREE.DoubleSide,
    blending: THREE.CustomBlending, blendEquation: THREE.AddEquation, blendSrc: THREE.SrcColorFactor, blendDst: THREE.OneFactor,
  });
}
// the texture matrix is S * R * T applied to the uv, as the GL calls stack up
function uvm(m, scale, rotDeg, tx, ty, translateFirst) {
  const S = new THREE.Matrix3().set(scale, 0, 0, 0, scale, 0, 0, 0, 1);
  const c = Math.cos(rotDeg * D), s = Math.sin(rotDeg * D);
  const R = new THREE.Matrix3().set(c, -s, 0, s, c, 0, 0, 0, 1);
  const T = new THREE.Matrix3().set(1, 0, tx, 0, 1, ty, 0, 0, 1);
  // armour: scale, rotate, translate   -> S R T       item: scale, translate, rotate -> S T R
  m.copy(S).multiply(translateFirst ? R : T).multiply(translateFirst ? T : R);
  return m;
}

// Add the two glint passes on top of every mesh under `root`.
function addGlint(root, mask, kind, glints) {
  const meshes = [];
  root.traverse((o) => { if (o.isMesh) meshes.push(o); });
  for (let k = 0; k < 2; k++) {
    const mat = glintMaterial(mask, kind === 'item');
    glints.push({ mat, kind, k });
    for (const m of meshes) {
      const g = new THREE.Mesh(m.geometry, mat);
      g.renderOrder = 5;
      m.add(g);
    }
  }
}
function updateGlints(glints, t) {
  for (const { mat, kind, k } of glints) {
    const u = mat.uniforms.uvm.value;
    if (kind === 'armor') {
      const ticks = t * 20;
      uvm(u, 0.33333334, 30 - k * 60, 0, ticks * (0.001 + k * 0.003) * 20, false);
    } else {
      const ms = t * 1000;
      if (k === 0) uvm(u, 0.125, -50, ((ms % 3000) / 3000) * 8, 0, true);
      else uvm(u, 0.125, 10, -((ms % 4873) / 4873) * 8, 0, true);
    }
  }
}

// ---------------------------------------------------------------------------------------- armour
const ARMOUR_ROOTS = {
  head: ['bipedHead', 'bipedHeadwear'],
  chest: ['bipedBody', 'bipedRightArm', 'bipedLeftArm'],
  legs: ['bipedBody', 'bipedRightLeg', 'bipedLeftLeg'],
  feet: ['bipedRightLeg', 'bipedLeftLeg'],
};
const armourData = new Map();
// ModelBiped(f): the same parts with every box inflated by f (headwear by f + 0.5, already in the data)
function armourModel(slot) {
  const f = slot === 'legs' ? 0.5 : 1.0;
  const key = slot;
  if (!armourData.has(key)) {
    const base = VANILLA_MODELS.biped;
    const parts = {};
    for (const n of ARMOUR_ROOTS[slot]) {
      const p = JSON.parse(JSON.stringify(base.parts[n]));
      p.boxes.forEach((b) => { b[6] += f; });
      parts[n] = p;
    }
    armourData.set(key, { tex: base.tex, parts, roots: ARMOUR_ROOTS[slot].slice() });
  }
  return armourData.get(key);
}

// ---------------------------------------------------------------------------------------- held items
// ItemRenderer.renderItemIn2D: a 1x1 sprite, 1/16 thick, edge walls per pixel column and row.
// Three-space uv: front (1 - x, y); walls take the colour of their pixel column/row.
const spriteGeoCache = new Map();
function spriteGeometry(W, H) {
  const key = W + 'x' + H;
  if (spriteGeoCache.has(key)) return spriteGeoCache.get(key);
  const pos = [], uv = [], idx = [];
  const Z = -0.0625;
  const quad = (a, b, c, d, ua, ub, uc, ud) => {
    const i = pos.length / 3;
    [a, b, c, d].forEach((p) => pos.push(...p));
    [ua, ub, uc, ud].forEach((u) => uv.push(...u));
    idx.push(i, i + 1, i + 2, i, i + 2, i + 3);
  };
  quad([0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [1, 0], [0, 0], [0, 1], [1, 1]);
  quad([0, 1, Z], [1, 1, Z], [1, 0, Z], [0, 0, Z], [1, 1], [0, 1], [0, 0], [1, 0]);
  for (let k = 0; k < W; k++) {
    const x0 = k / W, x1 = (k + 1) / W, u = 1 - (k + 0.5) / W;
    quad([x0, 0, Z], [x0, 0, 0], [x0, 1, 0], [x0, 1, Z], [u, 0], [u, 0], [u, 1], [u, 1]);
    quad([x1, 1, Z], [x1, 1, 0], [x1, 0, 0], [x1, 0, Z], [u, 1], [u, 1], [u, 0], [u, 0]);
  }
  for (let k = 0; k < H; k++) {
    const y0 = k / H, y1 = (k + 1) / H, v = (k + 0.5) / H;
    quad([0, y1, 0], [1, y1, 0], [1, y1, Z], [0, y1, Z], [1, v], [0, v], [0, v], [1, v]);
    quad([1, y0, 0], [0, y0, 0], [0, y0, Z], [1, y0, Z], [0, v], [1, v], [1, v], [0, v]);
  }
  // glint uv: the whole glint texture across the sprite (renderItemIn2D(0, 0, 1, 1, ...))
  const g = [];
  for (let i = 0; i < pos.length; i += 3) g.push(pos[i], 1 - pos[i + 1]);
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  geo.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  geo.setAttribute('guv', new THREE.Float32BufferAttribute(g, 2));
  geo.setIndex(idx);
  geo.computeVertexNormals();
  spriteGeoCache.set(key, geo);
  return geo;
}

// RenderBiped.renderEquippedItem, right arm. C is applied in the model frame; the holder sits under the arm
// group (arm pivot + rotation are the postRender), so its matrix is FLIP * C.
function heldChain(item) {
  const base = gT(-0.0625, 0.4375, 0.0625);
  if (item.bow) return chain(base, gT(0, 0.125, 0.3125), gR(-20, 0, 1, 0), gS(0.625, -0.625, 0.625), gR(-100, 1, 0, 0), gR(45, 0, 1, 0));
  // isFull3D (swords and tools)
  return chain(base, gT(0, 0.1875, 0), gS(0.625, -0.625, 0.625), gR(-100, 1, 0, 0), gR(45, 0, 1, 0));
}
// ItemRenderer.renderItem for a sprite item (EQUIPPED)
const SPRITE_ITEM = chain(gT(0, -0.3, 0), gS(1.5), gR(50, 0, 1, 0), gR(335, 0, 0, 1), gT(-0.9375, -0.0625, 0));
// ForgeHooksClient.renderEquippedItem + RenderQueenBattleAxe.renderSwordF5 (the model renders at scale 1.0: units are blocks)
const QUEEN_AXE = chain(gT(-0.5, -0.5, -0.5), gR(180, 1, 0.25, 0), gS(0.35), gT(3, -8, -2));

function holderFor(item, kit, glints) {
  const holder = new THREE.Group();
  holder.matrixAutoUpdate = false;
  if (item.kind === 'queenAxe') {
    const r = kit.buildRig(OS_MODELS.QueenBattleAxe, tex('orespawn/QueenBattleAxetexture.png'), {});
    r.root.position.set(0, 0, 0);
    r.root.scale.setScalar(16);
    holder.matrix.copy(chain(FLIP, heldChain({}), QUEEN_AXE, FLIP));
    holder.add(r.root);
    return holder;
  }
  const t = tex(item.tex);
  const mat = new THREE.MeshLambertMaterial({ map: t, side: THREE.DoubleSide, alphaTest: 0.1 });
  const mesh = new THREE.Mesh(spriteGeometry(16, 16), mat);
  holder.matrix.copy(chain(FLIP, heldChain(item), SPRITE_ITEM));
  holder.add(mesh);
  if (item.ench) addGlint(holder, t, 'item', glints);
  return holder;
}

// ---------------------------------------------------------------------------------------- attach
// kit: { buildRig } from mobs.js. P: the primary layer's parts. Returns { slots, held, update(P, t), hasHand }.
export function attachEquipment(parts, list, opts, kit) {
  const eq = parseEquipment(list, opts);
  const glints = [];
  const pieces = [];
  for (const slot of ['head', 'chest', 'legs', 'feet']) {
    const it = eq[slot];
    if (!it) continue;
    const texPath = slot === 'legs' ? it.layer2 : it.layer1;
    const t = tex(texPath);
    const r = kit.buildRig(armourModel(slot), t, {});
    pieces.push({ slot, r, ench: it.ench });
    if (it.ench) addGlint(r.root, t, 'armor', glints);
  }
  const hand = eq.hand ? holderFor(eq.hand, kit, glints) : null;
  return {
    slots: pieces.map((p) => p.slot),
    held: eq.hand ? eq.hand.id : null,
    hasHand: !!hand,
    pieces, hand, glints,
    mount(rig, parts) {
      // buildRig puts every root at the feet (y = 24 / 16), like the main model's root
      for (const p of pieces) rig.add(p.r.root);
      if (hand && parts.bipedRightArm) parts.bipedRightArm.add(hand);
    },
    update(P, t) {
      for (const p of pieces) {
        for (const n in p.r.parts) {
          const s = P[n], q = p.r.parts[n];
          if (!s) continue;
          q.rotation.copy(s.rotation);
        }
      }
      updateGlints(glints, t);
    },
  };
}
