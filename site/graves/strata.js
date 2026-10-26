// The strata of the endless Krypt: bands of graves, each with its own pool of segment kinds, light and character.
// The order runs from shallow crypts toward the depths; after the last one the list starts again with a prefix
// ("Lower ...") and new variation. 
export const CYCLE_PREFIX = ["", "Lower ", "Forgotten ", "Sunken ", "Hollow ", "Endless "];
export const STRATA = [
  { id: "crypt", name: "The Crypt", band: 720, entry: "stairs", gap: { p: 0.5, lava: 0.5 }, holes: true, color: "rgba(150,140,130,.28)",
    pool: ["classic", "worn", "tomb_gallery", "arch_run", "carpet_crypt", "raw_tunnel", "mine", "crypt"] },
  { id: "catacombs", name: "The Catacombs", band: 760, gap: { p: 0.55, lava: 0.3 }, holes: true, color: "rgba(170,160,130,.28)", light: { amb: [0.92, 0.92, 0.95], fog: [0.95, 0.95, 1], torch: 0.95 },
    pool: ["catacomb", "ossuary", "maze_hall", "collapsed_hall", "vaulted_hall", "cell_chain", "barred_cells", "cell_block", "spidermine"] },
  { id: "sewers", name: "The Drowned Sewers", band: 740, gap: { p: 0.6, lava: 0.05 }, holes: true, color: "rgba(90,150,130,.3)", light: { amb: [0.9, 1.1, 1.0], fog: [0.9, 1.15, 1.05] },
    pool: ["sewer_walk", "drain_gallery", "plank_causeway", "drowned_hall", "pressure_flood", "flood"] },
  { id: "library", name: "The Archives", band: 680, gap: { p: 0.45, lava: 0.35 }, holes: false, color: "rgba(160,120,70,.3)", light: { amb: [1.1, 1.0, 0.85], torch: 1.1 },
    pool: ["library", "scriptorium", "treasury", "alchemy_lab", "vault"] },
  { id: "sands", name: "The Sunken Sands", band: 700, gap: { p: 0.5, lava: 0.6 }, holes: true, color: "rgba(220,190,110,.3)", light: { amb: [1.2, 1.1, 0.9], exposure: 1.05 },
    pool: ["sand_temple", "sun_hall", "temple", "treasury", "raw_tunnel"] },
  { id: "ice", name: "The Frozen Halls", band: 700, gap: { p: 0.55, lava: 0.15 }, holes: true, color: "rgba(140,190,230,.3)", light: { amb: [0.85, 1.0, 1.25], fog: [0.85, 1.0, 1.3] },
    pool: ["ice_grotto", "frost_hall", "collapsed_hall", "chasm", "mine", "spidermine", "catacomb"] },
  { id: "fungal", name: "The Fungal Deep", band: 720, gap: { p: 0.55, lava: 0.2 }, holes: true, color: "rgba(150,90,170,.3)", light: { amb: [1.05, 0.9, 1.15] },
    pool: ["mushroom_cave", "overgrown", "spidermine", "flood", "catacomb", "mine"] },
  { id: "nether", name: "The Ember Passage", band: 760, gap: { p: 0.65, lava: 0.9 }, holes: true, color: "rgba(200,80,40,.3)", light: { amb: [1.2, 0.9, 0.8], torch: 1.1, bloom: 1.1 },
    pool: ["nether_hall", "soul_gallery", "obsidian_vault", "dungeon", "fortress"] },
  { id: "arms", name: "The Barracks", band: 700, gap: { p: 0.5, lava: 0.4 }, holes: false, color: "rgba(130,130,150,.3)",
    pool: ["armory", "barracks", "dungeon", "fortress", "cell_block", "barred_cells", "vault"] },
  { id: "deep", name: "The Great Deep", band: 760, gap: { p: 0.6, lava: 0.6 }, holes: true, color: "rgba(60,70,110,.3)", light: { amb: [0.85, 0.9, 1.1], fogD: 1.1 },
    pool: ["chasm", "deep", "void_bridge", "vault", "obsidian_vault", "raw_tunnel", "mine", "fortress"] },
  { id: "end", name: "The Pale Reach", entry: "portal_room", band: 700, gap: { p: 0.6, lava: 0.3 }, holes: false, color: "rgba(190,170,220,.3)", light: { amb: [1.0, 0.95, 1.2], exposure: 1.05 },
    pool: ["end_hall", "wool_hall", "void_bridge", "obsidian_vault", "treasury", "soul_gallery"] },
  { id: "abyss", name: "The Abyss", band: 760, gap: { p: 0.7, lava: 0.5 }, holes: true, color: "rgba(40,40,60,.4)", light: { amb: [0.8, 0.8, 0.9], torch: 1.15 },
    pool: ["deep", "chasm", "fortress", "end_hall", "nether_hall", "drowned_hall"] }
];
