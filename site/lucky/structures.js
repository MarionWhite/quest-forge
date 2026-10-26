// Structure placer: renders the voxel lists in data/structures.json around an origin.
// Terrain-layer cells (below the grass) become voxels at once; the rest drop in,
// one by one in tick order, each with a dust puff on landing.
import * as THREE from 'three';
import { makeBlock } from './blocks.js';
import { glowTexture } from './stage.js';

const DATA_URL = new URL('./data/structures.json', import.meta.url).href;
let DATA = null;
export const STRUCTS_READY = fetch(DATA_URL).then((r) => (r.ok ? r.json() : {})).catch(() => ({})).then((d) => { DATA = d; return d; });
export function structuresLoaded() { return DATA !== null; }

const ID = (id) => String(id || '').replace(/^[a-z]+:/, '');
// block id -> the stage's voxel key (for the terrain layer); null leaves the cell empty
const VOXEL = {
  stonebrick: 'brick', obsidian: 'obsidian', gold_block: 'gold', iron_block: 'iron', planks: 'planks',
  bedrock: 'bedrock', cobblestone: 'cobble', mossy_cobblestone: 'mossy', sandstone: 'stone', stone_stairs: 'stone',
  sandstone_stairs: 'stone', iron_bars: 'bars', glass: 'glass', flowing_lava: 'lava', lava: 'lava', stone: 'stone',
  dirt: 'dirt', grass: 'grass',
};

// Plan a structure: the cells to place and the air boxes to clear. by_facing "0" is used as-is.
export function plan(key) {
  const s = DATA && DATA[key];
  if (!s) return null;
  let list = s.blocks || [];
  if (s.by_facing && s.by_facing['0']) list = s.by_facing['0'];
  const cells = [], clears = [];
  for (const b of list) {
    const air = b.id === 'minecraft:air';
    if (b.from && b.to) {
      if (air) clears.push({ from: b.from, to: b.to });
      else for (let x = b.from[0]; x <= b.to[0]; x++) for (let y = b.from[1]; y <= b.to[1]; y++) for (let z = b.from[2]; z <= b.to[2]; z++) cells.push({ x, y, z, id: b.id, meta: b.meta || 0, tick: b.tick || 0 });
      continue;
    }
    if (air) continue;
    cells.push({ x: b.dx || 0, y: b.dy || 0, z: b.dz || 0, id: b.id, meta: b.meta || 0, tick: b.tick || 0, lines: b.nbt && b.nbt.lines, luck: b.nbt && b.nbt.luck });
  }
  return { key, name: s.name, cells, clears, notes: s.notes || '' };
}

function dustPuff(ctx, p, n = 7, size = 0.22) {
  const pts = new Float32Array(n * 3), vel = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) {
    pts.set([p.x + (Math.random() - 0.5) * 0.4, p.y + Math.random() * 0.2, p.z + (Math.random() - 0.5) * 0.4], i * 3);
    const a = Math.random() * Math.PI * 2, s = 0.6 + Math.random();
    vel.set([Math.cos(a) * s, 0.5 + Math.random(), Math.sin(a) * s], i * 3);
  }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(pts, 3));
  const mat = new THREE.PointsMaterial({ size, color: 0xb8b0c4, map: glowTexture(), transparent: true, depthWrite: false, sizeAttenuation: true });
  const obj = new THREE.Points(geo, mat);
  ctx.S.temp.add(obj);
  let t = 0;
  ctx.fx.push({
    update(dt) {
      t += dt;
      for (let i = 0; i < n; i++) { vel[i * 3 + 1] -= 1.5 * dt; for (let k = 0; k < 3; k++) pts[i * 3 + k] += vel[i * 3 + k] * dt; }
      geo.attributes.position.needsUpdate = true;
      mat.opacity = Math.max(0, 1 - t / 0.9);
      if (t > 0.9) { ctx.S.temp.remove(obj); geo.dispose(); mat.dispose(); return true; }
      return false;
    },
  });
}

const easeOutBack = (k) => { const c1 = 1.70158, c3 = c1 + 1; k = Math.max(0, Math.min(1, k)); return 1 + c3 * Math.pow(k - 1, 3) + c1 * Math.pow(k - 1, 2); };

// Place a planned structure at world cell `origin` ({x,y,z}). Returns {update(t), dur, anims}.
// opts.start: time of the first block; opts.span: seconds over which all blocks drop in.
export function placeStructure(ctx, pl, origin, opts = {}) {
  const start = opts.start ?? 0.2, span = opts.span ?? 2.6;
  const ox = origin.x, oy = origin.y, oz = origin.z;
  for (const c of pl.clears) {
    for (let x = c.from[0]; x <= c.to[0]; x++) for (let y = c.from[1]; y <= c.to[1]; y++) for (let z = c.from[2]; z <= c.to[2]; z++) {
      const wy = oy + y;
      if (wy >= -8) ctx.setVoxel(ox + x, wy, oz + z, null);
    }
  }
  const occ = new Set(pl.cells.map((c) => c.x + ',' + c.y + ',' + c.z));
  const has = (dx, dy, dz) => occ.has(dx + ',' + dy + ',' + dz);
  // assembly order: by tick, then bottom up, then out from the centre
  const order = pl.cells.slice().sort((a, b) => (a.tick - b.tick) || (a.y - b.y) || ((a.x * a.x + a.z * a.z) - (b.x * b.x + b.z * b.z)));
  const anims = [];
  for (const c of order) {
    const wx = ox + c.x, wy = oy + c.y, wz = oz + c.z;
    const vk = VOXEL[ID(c.id)];
    if (wy < 0) { ctx.setVoxel(wx, wy, wz, vk || null); continue; }
    const r = makeBlock(c.id, c.meta, { has, lines: c.lines });
    const holder = new THREE.Group();
    r.obj.position.set(-0.5, 0, -0.5);
    holder.add(r.obj);
    holder.position.set(wx + 0.5, wy, wz + 0.5);
    holder.scale.setScalar(0.001);
    ctx.S.temp.add(holder);
    anims.push({ holder, wx, wy, wz, t0: 0, landed: false, light: r.light, lid: r.lid });
  }
  // the terrain changed under the structure
  const n = anims.length;
  const step = n ? Math.min(0.1, span / n) : 0;
  anims.forEach((a, i) => { a.t0 = start + i * step; });
  return {
    dur: start + n * step + 0.4,
    anims,
    update(t) {
      for (const a of anims) {
        if (t < a.t0) continue;
        const k = (t - a.t0) / 0.32;
        a.holder.scale.setScalar(Math.max(0.001, easeOutBack(k)));
        a.holder.position.y = a.wy + (1 - Math.min(1, k)) * (1 - Math.min(1, k)) * 1.8;
        if (k >= 1 && !a.landed) { a.landed = true; dustPuff(ctx, new THREE.Vector3(a.wx + 0.5, a.wy + 0.1, a.wz + 0.5)); }
        if (a.light) a.light.intensity = 1.2 + 0.25 * Math.sin(t * 9 + a.wx);
      }
    },
    cells: n,
  };
}

// Plan by key, placed at the given feet cell; null when the structure is not in the data.
export function structureScene(ctx, key, origin, opts) {
  const pl = plan(key);
  if (!pl) return null;
  return placeStructure(ctx, pl, origin, opts);
}
