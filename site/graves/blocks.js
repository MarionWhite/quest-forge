// The Krypt's block palette: tile ids, the textures each shows on its sides, top and bottom, the names the scares'
// blockAt reports, the hash used for dressing, and the registry of wall styles (a style is a weighted table of tiles
// that fills the solid rock around a segment).
export const T_AIR = 0, T_STONE = 1, T_COBBLE = 2, T_MOSSY = 3, T_BRICK = 4, T_BRICK_MOSSY = 5, T_BRICK_CRACK = 6,
  T_GRAVEL_FLOOR = 7, T_COAL = 8, T_IRON = 9, T_OBS = 10, T_BEDROCK = 11, T_NETHER = 12, T_GLOW = 13, T_BRIDGE = 14,
  T_WATER = 15, T_NBRICK = 16, T_SOUL = 17, T_SHELF = 18, T_PLANK = 19, T_LOG = 20, T_LAVA = 22, T_DIRT = 23,
  T_DISP_PX = 24, T_DISP_NX = 25, T_DISP_PZ = 26, T_DISP_NZ = 27, T_GOLD = 28, T_DIAM = 29, T_LAPIS = 30, T_EMERALD = 31,
  T_IRONB = 32, T_CARVED = 33,
  T_SAND = 34, T_SANDSTONE = 35, T_SANDSTONE_C = 36, T_SANDSTONE_S = 37, T_ENDSTONE = 38, T_QUARTZ = 39, T_QUARTZ_C = 40,
  T_QUARTZ_P = 41, T_PACKED_ICE = 42, T_SNOW = 43, T_CLAY = 44, T_BRICKS = 45, T_LAMP = 46, T_PUMPKIN = 47,
  T_JACK_PX = 48, T_JACK_NX = 49, T_JACK_PZ = 50, T_JACK_NZ = 51, T_HAY = 52, T_MELON = 53, T_MYCELIUM = 54, T_PODZOL = 55,
  T_GRASS = 56, T_LEAVES_OAK = 57, T_LEAVES_JUNGLE = 58, T_LEAVES_SPRUCE = 59, T_LEAVES_BIRCH = 60, T_LOG_SPRUCE = 61,
  T_LOG_BIRCH = 62, T_LOG_JUNGLE = 63, T_PLANK_SPRUCE = 64, T_PLANK_BIRCH = 65, T_PLANK_JUNGLE = 66, T_GOLD_ORE = 67,
  T_REDSTONE_ORE = 68, T_LAPIS_ORE = 69, T_DIAM_ORE = 70, T_EMERALD_ORE = 71, T_QUARTZ_ORE = 72, T_TNT = 73, T_SPONGE = 74,
  T_COAL_BLOCK = 75, T_REDSTONE_BLOCK = 76, T_RED_SAND = 77,
  T_CLAY0 = 80,        // 16 stained hardened clays, T_CLAY0 .. T_CLAY0 + 15 in CLAY_COLORS order
  T_WOOL0 = 96,        // 16 wools, T_WOOL0 .. T_WOOL0 + 15
  T_CRAFT = 112, T_NOTE = 113, T_JUKEBOX = 114, T_FURN_PX = 115, T_FURN_NX = 116, T_FURN_PZ = 117, T_FURN_NZ = 118,
  T_MUSH_RED = 119, T_MUSH_BROWN = 120, T_MUSH_STEM = 121, T_SLAB = 122, T_PLANK_ACACIA = 123, T_PLANK_DARK = 124,
  T_WALL = 255;
export const CLAY_COLORS = ["black", "gray", "white", "red", "orange", "brown", "blue", "purple", "cyan", "lime", "yellow", "silver", "green", "pink", "magenta", "light_blue"];
export const clay = (name) => T_CLAY0 + CLAY_COLORS.indexOf(name);
export const wool = (name) => T_WOOL0 + CLAY_COLORS.indexOf(name);

// Textures: [side, top, bottom]; a single entry is used for all faces.
export const TEX_OF = {
  [T_STONE]: ["stone"], [T_COBBLE]: ["cobblestone"], [T_MOSSY]: ["cobblestone_mossy"], [T_BRICK]: ["stonebrick"],
  [T_BRICK_MOSSY]: ["stonebrick_mossy"], [T_BRICK_CRACK]: ["stonebrick_cracked"], [T_GRAVEL_FLOOR]: ["stone", "gravel"],
  [T_COAL]: ["coal_ore"], [T_IRON]: ["iron_ore"], [T_OBS]: ["obsidian"], [T_BEDROCK]: ["bedrock"], [T_NETHER]: ["netherrack"],
  [T_GLOW]: ["glowstone"], [T_BRIDGE]: ["stonebrick"], [T_NBRICK]: ["nether_brick"], [T_SOUL]: ["soul_sand"],
  [T_SHELF]: ["bookshelf", "planks_oak", "planks_oak"], [T_PLANK]: ["planks_oak"], [T_LOG]: ["log_oak", "log_oak_top", "log_oak_top"],
  [T_DIRT]: ["dirt"],
  [T_DISP_PX]: ["furnace_side", "furnace_top", "furnace_top"], [T_DISP_NX]: ["furnace_side", "furnace_top", "furnace_top"],
  [T_DISP_PZ]: ["furnace_side", "furnace_top", "furnace_top"], [T_DISP_NZ]: ["furnace_side", "furnace_top", "furnace_top"],
  [T_GOLD]: ["gold_block"], [T_DIAM]: ["diamond_block"], [T_LAPIS]: ["lapis_block"], [T_EMERALD]: ["emerald_block"],
  [T_IRONB]: ["iron_block"], [T_CARVED]: ["stonebrick_carved"],
  [T_SAND]: ["sand"], [T_RED_SAND]: ["red_sand"], [T_SANDSTONE]: ["sandstone_normal", "sandstone_top", "sandstone_bottom"],
  [T_SANDSTONE_C]: ["sandstone_carved", "sandstone_top", "sandstone_bottom"], [T_SANDSTONE_S]: ["sandstone_smooth", "sandstone_top", "sandstone_bottom"],
  [T_ENDSTONE]: ["end_stone"], [T_QUARTZ]: ["quartz_block_side", "quartz_block_top", "quartz_block_bottom"],
  [T_QUARTZ_C]: ["quartz_block_chiseled", "quartz_block_chiseled_top", "quartz_block_chiseled_top"],
  [T_QUARTZ_P]: ["quartz_block_lines", "quartz_block_lines_top", "quartz_block_lines_top"],
  [T_PACKED_ICE]: ["ice_packed"], [T_SNOW]: ["snow"], [T_CLAY]: ["hardened_clay"], [T_BRICKS]: ["brick"], [T_LAMP]: ["redstone_lamp_on"],
  [T_PUMPKIN]: ["pumpkin_side", "pumpkin_top", "pumpkin_top"],
  [T_JACK_PX]: ["pumpkin_side", "pumpkin_top", "pumpkin_top"], [T_JACK_NX]: ["pumpkin_side", "pumpkin_top", "pumpkin_top"],
  [T_JACK_PZ]: ["pumpkin_side", "pumpkin_top", "pumpkin_top"], [T_JACK_NZ]: ["pumpkin_side", "pumpkin_top", "pumpkin_top"],
  [T_HAY]: ["hay_block_side", "hay_block_top", "hay_block_top"], [T_MELON]: ["melon_side", "melon_top", "melon_top"],
  [T_MYCELIUM]: ["mycelium_side", "mycelium_top", "dirt"], [T_PODZOL]: ["dirt_podzol_side", "dirt_podzol_top", "dirt"],
  [T_GRASS]: ["grass_side_t", "grass_top_t", "dirt"],
  [T_LEAVES_OAK]: ["leaves_oak_t"], [T_LEAVES_JUNGLE]: ["leaves_jungle_t"], [T_LEAVES_SPRUCE]: ["leaves_spruce_t"], [T_LEAVES_BIRCH]: ["leaves_birch_t"],
  [T_LOG_SPRUCE]: ["log_spruce", "log_spruce_top", "log_spruce_top"], [T_LOG_BIRCH]: ["log_birch", "log_birch_top", "log_birch_top"],
  [T_LOG_JUNGLE]: ["log_jungle", "log_jungle_top", "log_jungle_top"],
  [T_PLANK_SPRUCE]: ["planks_spruce"], [T_PLANK_BIRCH]: ["planks_birch"], [T_PLANK_JUNGLE]: ["planks_jungle"], [T_PLANK_ACACIA]: ["planks_acacia"], [T_PLANK_DARK]: ["planks_big_oak"],
  [T_GOLD_ORE]: ["gold_ore"], [T_REDSTONE_ORE]: ["redstone_ore"], [T_LAPIS_ORE]: ["lapis_ore"], [T_DIAM_ORE]: ["diamond_ore"],
  [T_EMERALD_ORE]: ["emerald_ore"], [T_QUARTZ_ORE]: ["quartz_ore"], [T_TNT]: ["tnt_side", "tnt_top", "tnt_bottom"], [T_SPONGE]: ["sponge"],
  [T_COAL_BLOCK]: ["coal_block"], [T_REDSTONE_BLOCK]: ["redstone_block"],
  [T_CRAFT]: ["crafting_table_side", "crafting_table_top", "planks_oak"], [T_NOTE]: ["noteblock"], [T_JUKEBOX]: ["jukebox_side", "jukebox_top", "jukebox_side"],
  [T_FURN_PX]: ["furnace_side", "furnace_top", "furnace_top"], [T_FURN_NX]: ["furnace_side", "furnace_top", "furnace_top"],
  [T_FURN_PZ]: ["furnace_side", "furnace_top", "furnace_top"], [T_FURN_NZ]: ["furnace_side", "furnace_top", "furnace_top"],
  [T_MUSH_RED]: ["mushroom_block_skin_red"], [T_MUSH_BROWN]: ["mushroom_block_skin_brown"], [T_MUSH_STEM]: ["mushroom_block_skin_stem"],
  [T_SLAB]: ["stone_slab_side", "stone_slab_top", "stone_slab_top"]
};
CLAY_COLORS.forEach((c, i) => { TEX_OF[T_CLAY0 + i] = ["hardened_clay_stained_" + c]; TEX_OF[T_WOOL0 + i] = ["wool_colored_" + c]; });
// Blocks with one special face: the world direction (x, z) that shows it, and its texture.
export const FRONT = {
  [T_DISP_PX]: [1, 0, "dispenser_front_horizontal"], [T_DISP_NX]: [-1, 0, "dispenser_front_horizontal"],
  [T_DISP_PZ]: [0, 1, "dispenser_front_horizontal"], [T_DISP_NZ]: [0, -1, "dispenser_front_horizontal"],
  [T_JACK_PX]: [1, 0, "pumpkin_face_on"], [T_JACK_NX]: [-1, 0, "pumpkin_face_on"], [T_JACK_PZ]: [0, 1, "pumpkin_face_on"], [T_JACK_NZ]: [0, -1, "pumpkin_face_on"],
  [T_FURN_PX]: [1, 0, "furnace_front_on"], [T_FURN_NX]: [-1, 0, "furnace_front_on"], [T_FURN_PZ]: [0, 1, "furnace_front_on"], [T_FURN_NZ]: [0, -1, "furnace_front_on"],
  [T_CRAFT]: [0, 0, null]
};
delete FRONT[T_CRAFT];
// Blocks that glow in the bake: the colour their faces carry.
export const EMISSIVE = {
  [T_GLOW]: [1.7, 1.45, 0.9], [T_LAMP]: [1.6, 1.35, 0.95], [T_JACK_PX]: [1.3, 0.9, 0.45], [T_JACK_NX]: [1.3, 0.9, 0.45],
  [T_JACK_PZ]: [1.3, 0.9, 0.45], [T_JACK_NZ]: [1.3, 0.9, 0.45], [T_REDSTONE_BLOCK]: [1.0, 0.45, 0.4]
};
export const BLOCK_NAME = {
  [T_AIR]: "air", [T_STONE]: "stone", [T_COBBLE]: "cobblestone", [T_MOSSY]: "mossy_cobblestone", [T_BRICK]: "stonebrick",
  [T_BRICK_MOSSY]: "mossy_stonebrick", [T_BRICK_CRACK]: "cracked_stonebrick", [T_GRAVEL_FLOOR]: "gravel", [T_COAL]: "coal_ore",
  [T_IRON]: "iron_ore", [T_OBS]: "obsidian", [T_BEDROCK]: "bedrock", [T_NETHER]: "netherrack", [T_GLOW]: "glowstone",
  [T_BRIDGE]: "stonebrick", [T_WATER]: "water", [T_NBRICK]: "nether_brick", [T_SOUL]: "soul_sand", [T_SHELF]: "bookshelf",
  [T_PLANK]: "planks", [T_LOG]: "log", [T_LAVA]: "lava", [T_DIRT]: "dirt",
  [T_DISP_PX]: "dispenser", [T_DISP_NX]: "dispenser", [T_DISP_PZ]: "dispenser", [T_DISP_NZ]: "dispenser",
  [T_GOLD]: "gold_block", [T_DIAM]: "diamond_block", [T_LAPIS]: "lapis_block", [T_EMERALD]: "emerald_block",
  [T_IRONB]: "iron_block", [T_CARVED]: "chiseled_stonebrick",
  [T_SAND]: "sand", [T_RED_SAND]: "sand", [T_SANDSTONE]: "sandstone", [T_SANDSTONE_C]: "chiseled_sandstone", [T_SANDSTONE_S]: "smooth_sandstone",
  [T_ENDSTONE]: "end_stone", [T_QUARTZ]: "quartz_block", [T_QUARTZ_C]: "chiseled_quartz_block", [T_QUARTZ_P]: "quartz_pillar",
  [T_PACKED_ICE]: "packed_ice", [T_SNOW]: "snow", [T_CLAY]: "hardened_clay", [T_BRICKS]: "brick_block", [T_LAMP]: "lit_redstone_lamp",
  [T_PUMPKIN]: "pumpkin", [T_JACK_PX]: "lit_pumpkin", [T_JACK_NX]: "lit_pumpkin", [T_JACK_PZ]: "lit_pumpkin", [T_JACK_NZ]: "lit_pumpkin",
  [T_HAY]: "hay_block", [T_MELON]: "melon_block", [T_MYCELIUM]: "mycelium", [T_PODZOL]: "dirt", [T_GRASS]: "grass",
  [T_LEAVES_OAK]: "leaves", [T_LEAVES_JUNGLE]: "leaves", [T_LEAVES_SPRUCE]: "leaves", [T_LEAVES_BIRCH]: "leaves",
  [T_LOG_SPRUCE]: "log", [T_LOG_BIRCH]: "log", [T_LOG_JUNGLE]: "log", [T_PLANK_SPRUCE]: "planks", [T_PLANK_BIRCH]: "planks",
  [T_PLANK_JUNGLE]: "planks", [T_PLANK_ACACIA]: "planks", [T_PLANK_DARK]: "planks", [T_GOLD_ORE]: "gold_ore",
  [T_REDSTONE_ORE]: "redstone_ore", [T_LAPIS_ORE]: "lapis_ore", [T_DIAM_ORE]: "diamond_ore", [T_EMERALD_ORE]: "emerald_ore",
  [T_QUARTZ_ORE]: "quartz_ore", [T_TNT]: "tnt", [T_SPONGE]: "sponge", [T_COAL_BLOCK]: "coal_block", [T_REDSTONE_BLOCK]: "redstone_block",
  [T_CRAFT]: "crafting_table", [T_NOTE]: "noteblock", [T_JUKEBOX]: "jukebox", [T_FURN_PX]: "lit_furnace", [T_FURN_NX]: "lit_furnace",
  [T_FURN_PZ]: "lit_furnace", [T_FURN_NZ]: "lit_furnace", [T_MUSH_RED]: "red_mushroom_block", [T_MUSH_BROWN]: "brown_mushroom_block",
  [T_MUSH_STEM]: "brown_mushroom_block", [T_SLAB]: "double_stone_slab"
};
CLAY_COLORS.forEach((c, i) => { BLOCK_NAME[T_CLAY0 + i] = "stained_hardened_clay"; BLOCK_NAME[T_WOOL0 + i] = "wool"; });

// Every texture file the blocks name, so the page can load them (the tinted ones are made from their grey originals).
export const TINTED = { grass_top_t: ["grass_top", "#7bbd5c"], grass_side_t: ["grass_side", "#7bbd5c", "grass_side_overlay"],
  leaves_oak_t: ["leaves_oak_opaque", "#5fa332"], leaves_jungle_t: ["leaves_jungle_opaque", "#3f9d1c"],
  leaves_spruce_t: ["leaves_spruce_opaque", "#618f61"], leaves_birch_t: ["leaves_birch_opaque", "#80a755"] };
export const BLOCK_TEX_FILES = (() => {
  const set = new Set();
  for (const v of Object.values(TEX_OF)) for (const n of v) set.add(n);
  for (const v of Object.values(FRONT)) if (v[2]) set.add(v[2]);
  const out = [];
  for (const n of set) { if (TINTED[n]) { out.push(TINTED[n][0]); if (TINTED[n][2]) out.push(TINTED[n][2]); } else out.push(n); }
  return [...new Set(out)];
})();

export const isOpen = (t) => t === T_AIR || t === T_WATER || t === T_LAVA;

// A hash of three ints and a salt, 0..999: the dressing's dice.
export const ih = (i, j, k, s = 0) => {
  let h = (i * 374761393 + j * 668265263 + k * 2147483647 + s * 1274126177) | 0;
  h = Math.imul(h ^ (h >>> 13), 1274126177); h ^= h >>> 16;
  return (h >>> 0) % 1000;
};
export const pickW = (h, table) => { for (const [lim, t] of table) if (h < lim) return t; return table[table.length - 1][1]; };

// Wall styles: id -> weighted table. A table is [[limit, tile], ...] with limits rising to 1000.
export const WALLS = {};
let nextStyle = 1;
export function defWalls(table) { const id = nextStyle++; WALLS[id] = table; return id; }
export function wallType(style, i, j, k) { return pickW(ih(i, j, k, 7), WALLS[style] || WALLS[1]); }
