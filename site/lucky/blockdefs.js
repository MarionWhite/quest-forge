// What every block of the Lucky Block page looks like, as plain data. No imports, so the reel,
// the block builder, the effects and the audit page can all ask the same question:
//   blockSpec(id, meta, o) -> a spec, {k:'none'} for blocks that draw nothing, or null (unknown id)
// Rules come from the decompiled 1.7.10 sources (Block.getIcon per side and metadata) and from
// RenderBlocks; the notes say which class. Texture names are relative to tex/blocks/.
//
// A cube spec: {k:'cube', f:{px,nx,py,ny,pz,nz}} - faces east, west, top, bottom, south, north -
// optional tint (hex, by face group), cut (alpha-tested), blend (alpha blended), glow (hex).
// Shapes: cake, bars, fence, stairs, slab, plate, torch, web, sign, chest, anvil, egg, brew,
// liquid, enchant, plus the few cubes that carry an extra (grass overlay).

export const DYE_NAMES = ['white', 'orange', 'magenta', 'light_blue', 'yellow', 'lime', 'pink', 'gray', 'silver', 'cyan', 'purple', 'blue', 'brown', 'green', 'red', 'black'];
const WOODS = ['oak', 'spruce', 'birch', 'jungle', 'acacia', 'big_oak'];
export const TINT = { grass: 0x91bd59, foliage: 0x8ab84a };

export const bare = (id) => String(id || '').replace(/^[A-Za-z0-9]+:/, '');

// all six faces the same
const all = (file, extra = {}) => ({ k: 'cube', f: { px: file, nx: file, py: file, ny: file, pz: file, nz: file }, ...extra });
// side / top / bottom
const stb = (side, top = side, bottom = top, extra = {}) => ({ k: 'cube', f: { px: side, nx: side, py: top, ny: bottom, pz: side, nz: side }, ...extra });
// side / top / bottom plus a front on one horizontal side (2 north, 3 south, 4 west, 5 east)
const fronted = (side, top, bottom, front, fronts) => {
  const s = stb(side, top, bottom);
  const key = { 2: 'nz', 3: 'pz', 4: 'nx', 5: 'px' };
  for (const n of fronts) s.f[key[n]] = front;
  return s;
};

// plain single-texture cubes
const CUBES = {
  stone: 'stone.png', cobblestone: 'cobblestone.png', mossy_cobblestone: 'cobblestone_mossy.png', dirt: 'dirt.png', bedrock: 'bedrock.png',
  obsidian: 'obsidian.png', netherrack: 'netherrack.png', nether_brick: 'nether_brick.png', brick_block: 'brick.png', sponge: 'sponge.png',
  gravel: 'gravel.png', sand: 'sand.png', hardened_clay: 'hardened_clay.png', snow: 'snow.png',
  coal_block: 'coal_block.png', iron_block: 'iron_block.png', gold_block: 'gold_block.png', diamond_block: 'diamond_block.png',
  emerald_block: 'emerald_block.png', lapis_block: 'lapis_block.png', redstone_block: 'redstone_block.png',
  coal_ore: 'coal_ore.png', iron_ore: 'iron_ore.png', gold_ore: 'gold_ore.png', diamond_ore: 'diamond_ore.png', emerald_ore: 'emerald_ore.png',
  lapis_ore: 'lapis_ore.png', redstone_ore: 'redstone_ore.png', quartz_ore: 'quartz_ore.png', command_block: 'command_block.png',
  // OreSpawn (OreSpawnMain registers each with its own texture name)
  OreSpawn_BlockTitaniumBlock: 'orespawn/blocktitanium.png', OreSpawn_BlockUraniumBlock: 'orespawn/blockuranium.png',
  OreSpawn_BlockRubyBlock: 'orespawn/blockruby.png', OreSpawn_BlockAmethystBlock: 'orespawn/blockamethyst.png',
  OreSpawn_OreTitaniumBlock: 'orespawn/oretitanium.png', OreSpawn_OreUraniumBlock: 'orespawn/oreuranium.png',
  OreSpawn_OreRedAntTrollBlock: 'orespawn/redanttroll.png', OreSpawn_OreTermiteTrollBlock: 'orespawn/termitetroll.png',
  OreSpawn_DungeonSpawner: 'orespawn/dungeonspawner.png', OreSpawn_KingSpawner: 'orespawn/kingspawner.png', OreSpawn_QueenSpawner: 'orespawn/queenspawner.png',
};
const OPAQUE_SHAPES = new Set(['cube']);

export function blockSpec(id, meta = 0, o = {}) {
  const n = bare(id);
  const m = meta | 0;
  const item = !!o.item;           // drawn as an inventory icon: furnace fronts and the like show
  if (n === 'air' || n === 'fire') return { k: 'none' };
  if (CUBES[n]) return all(CUBES[n], { opaque: true });
  const dye = DYE_NAMES[m & 15];
  switch (n) {
    case 'lucky_block': return all('lucky_block.png', { glow: 0x2a1640, opaque: true });
    case 'stonebrick': return all(['stonebrick.png', 'stonebrick_mossy.png', 'stonebrick_cracked.png', 'stonebrick_carved.png'][m & 3] || 'stonebrick.png', { opaque: true });
    case 'glowstone': return all('glowstone.png', { glow: 0x6a5a20, opaque: true });
    case 'wool': return all('wool_colored_' + dye + '.png', { opaque: true });
    case 'stained_hardened_clay': return all('hardened_clay_stained_' + dye + '.png', { opaque: true });
    case 'glass': return all('glass.png', { cut: true });
    case 'stained_glass': return all('glass_' + dye + '.png', { blend: true });
    case 'planks': return all('planks_' + (WOODS[m & 7] || 'oak') + '.png', { opaque: true });
    case 'log': { const w = ['oak', 'spruce', 'birch', 'jungle'][m & 3]; return stb('log_' + w + '.png', 'log_' + w + '_top.png', 'log_' + w + '_top.png', { opaque: true }); }
    case 'log2': { const w = ['acacia', 'big_oak'][m & 1]; return stb('log_' + w + '.png', 'log_' + w + '_top.png', 'log_' + w + '_top.png', { opaque: true }); }
    case 'leaves': return all('leaves_' + (['oak', 'spruce', 'birch', 'jungle'][m & 3]) + '_opaque.png', { tint: { all: TINT.foliage }, opaque: true });
    case 'grass': { const s = stb('grass_side.png', 'grass_top.png', 'dirt.png', { tint: { py: TINT.grass }, opaque: true }); s.overlay = { file: 'grass_side_overlay.png', tint: TINT.grass }; return s; }
    case 'mycelium': return stb('mycelium_side.png', 'mycelium_top.png', 'dirt.png', { opaque: true });
    case 'tnt': return stb('tnt_side.png', 'tnt_top.png', 'tnt_bottom.png', { opaque: true });
    case 'bookshelf': return stb('bookshelf.png', 'planks_oak.png', 'planks_oak.png', { opaque: true });
    case 'hay_block': return stb('hay_block_side.png', 'hay_block_top.png', 'hay_block_top.png', { opaque: true });
    case 'sandstone': return stb(['sandstone_normal.png', 'sandstone_carved.png', 'sandstone_smooth.png'][m % 3], 'sandstone_top.png', 'sandstone_bottom.png', { opaque: true });
    case 'quartz_block': {
      if (m === 1) return stb('quartz_block_chiseled.png', 'quartz_block_chiseled_top.png', 'quartz_block_chiseled_top.png', { opaque: true });
      if (m >= 2 && m <= 4) return stb('quartz_block_lines.png', 'quartz_block_lines_top.png', 'quartz_block_lines_top.png', { opaque: true });
      return stb('quartz_block_side.png', 'quartz_block_top.png', 'quartz_block_bottom.png', { opaque: true });
    }
    case 'pumpkin': case 'lit_pumpkin': {
      const face = n === 'lit_pumpkin' ? 'pumpkin_face_on.png' : 'pumpkin_face_off.png';
      const s = stb('pumpkin_side.png', 'pumpkin_top.png', 'pumpkin_top.png', { opaque: true });
      const at = { 0: 'pz', 1: 'nx', 2: 'nz', 3: 'px' }[m & 3];
      if (item) s.f.pz = face; else s.f[at] = face;
      return s;
    }
    case 'melon_block': return stb('melon_side.png', 'melon_top.png', 'melon_top.png', { opaque: true });
    case 'crafting_table': return fronted('crafting_table_side.png', 'crafting_table_top.png', 'planks_oak.png', 'crafting_table_front.png', item ? [3, 4] : [2, 4]);
    case 'furnace': case 'lit_furnace': {
      const front = n === 'lit_furnace' ? 'furnace_front_on.png' : 'furnace_front_off.png';
      return fronted('furnace_side.png', 'furnace_top.png', 'furnace_top.png', front, item ? [3] : (m >= 2 && m <= 5 ? [m] : []));
    }
    case 'beacon': return all('beacon.png', { blend: true, glow: 0x1a3a40 });
    case 'mob_spawner': return all('mob_spawner.png', { cut: true });
    case 'enchanting_table': return { k: 'enchant', f: { px: 'enchanting_table_side.png', nx: 'enchanting_table_side.png', py: 'enchanting_table_top.png', ny: 'enchanting_table_bottom.png', pz: 'enchanting_table_side.png', nz: 'enchanting_table_side.png' } };
    case 'cake': {
      // BlockCake: top, bottom, inner (the cut face, meta > 0) and sides. Bounds (1/16..15/16, 0..0.5).
      // A falling cake never had its bounds set, so the game draws a full cube with the side
      // texture's transparent top half; it becomes the 14x8x14 cake when it lands.
      const f = { px: 'cake_side.png', nx: m > 0 ? 'cake_inner.png' : 'cake_side.png', py: 'cake_top.png', ny: 'cake_bottom.png', pz: 'cake_side.png', nz: 'cake_side.png' };
      return { k: 'cake', f, slices: m, fallingCube: true };
    }
    case 'stone_slab': return { k: 'slab', f: stb('stone_slab_side.png', 'stone_slab_top.png', 'stone_slab_top.png').f };
    case 'light_weighted_pressure_plate': return { k: 'plate', file: 'gold_block.png' };
    case 'heavy_weighted_pressure_plate': return { k: 'plate', file: 'iron_block.png' };
    case 'wooden_pressure_plate': return { k: 'plate', file: 'planks_oak.png', inset: 1 };
    case 'stone_pressure_plate': return { k: 'plate', file: 'stone.png', inset: 1 };
    case 'sandstone_stairs': return { k: 'stairs', meta: m, f: stb('sandstone_normal.png', 'sandstone_top.png', 'sandstone_bottom.png').f };
    case 'stone_stairs': return { k: 'stairs', meta: m, f: all('cobblestone.png').f };
    case 'oak_stairs': return { k: 'stairs', meta: m, f: all('planks_oak.png').f };
    case 'brick_stairs': return { k: 'stairs', meta: m, f: all('brick.png').f };
    case 'stone_brick_stairs': return { k: 'stairs', meta: m, f: all('stonebrick.png').f };
    case 'nether_brick_stairs': return { k: 'stairs', meta: m, f: all('nether_brick.png').f };
    case 'quartz_stairs': return { k: 'stairs', meta: m, f: stb('quartz_block_side.png', 'quartz_block_top.png', 'quartz_block_bottom.png').f };
    case 'iron_bars': return { k: 'bars', file: 'iron_bars.png' };
    case 'fence': return { k: 'fence', file: 'planks_oak.png' };
    case 'nether_brick_fence': return { k: 'fence', file: 'nether_brick.png' };
    case 'web': return { k: 'web', file: 'web.png' };
    case 'torch': return { k: 'torch', file: 'torch_on.png', meta: m };
    case 'standing_sign': case 'wall_sign': return { k: 'sign', meta: m, wall: n === 'wall_sign', file: 'planks_oak.png', board: 'entity/sign.png' };
    case 'chest': return { k: 'chest', file: 'entity/chest.png', meta: m };
    case 'trapped_chest': return { k: 'chest', file: 'entity/chest_trapped.png', meta: m };
    case 'anvil': return { k: 'anvil', files: ['anvil_base.png', 'anvil_top_damaged_0.png'], meta: m };
    case 'dragon_egg': return { k: 'egg', file: 'dragon_egg.png' };
    case 'brewing_stand': return { k: 'brew', files: ['brewing_stand.png', 'brewing_stand_base.png'] };
    case 'lava': case 'flowing_lava': return { k: 'liquid', file: 'lava_still.png', lava: true };
    case 'water': case 'flowing_water': return { k: 'liquid', file: 'water_still.png', water: true };
    default: return null;
  }
}

// every texture a spec needs, for the audit and for preloading
export function specFiles(s) {
  if (!s) return [];
  const out = new Set();
  if (s.f) for (const v of Object.values(s.f)) out.add(v);
  if (s.file) out.add(s.file);
  if (s.files) s.files.forEach((f) => out.add(f));
  if (s.board) out.add(s.board);
  if (s.overlay) out.add(s.overlay.file);
  return [...out].map((f) => (f.startsWith('entity/') ? f : 'blocks/' + f));
}

// Does a block fill its cell and hide a neighbouring pane or fence from the side? (Block.isOpaqueCube)
export function isOpaque(id, meta = 0) {
  const s = blockSpec(id, meta);
  return !!(s && s.k === 'cube' && s.opaque);
}
// BlockPane / BlockFence connection: panes join other panes, glass and opaque cubes.
export function paneJoins(id, meta = 0) {
  const n = bare(id);
  if (n === 'iron_bars' || n === 'glass' || n === 'stained_glass' || n === 'glass_pane' || n === 'stained_glass_pane') return true;
  return isOpaque(id, meta);
}
export function fenceJoins(id, meta = 0) {
  const n = bare(id);
  if (n === 'fence' || n === 'fence_gate' || n === 'nether_brick_fence') return true;
  return isOpaque(id, meta);
}
export { OPAQUE_SHAPES };
