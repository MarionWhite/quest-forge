// The strata of the endless Krypt: bands of graves, each with its own pool of segment kinds, light and character.
// The order runs from shallow crypts toward the depths; after the last one the list starts again with a prefix
// ("Lower ...") and new variation. (A temporary one-stratum list while the engine is wired up.)
export const CYCLE_PREFIX = ["", "Lower ", "Forgotten ", "Sunken ", "Hollow ", "Endless "];
export const STRATA = [
  { id: "crypt", name: "The Crypt", band: 400, entry: "stairs", gap: { p: 0.5, lava: 0.5 }, holes: true,
    pool: ["mine", "catacomb", "ossuary", "flood", "spidermine", "temple", "dungeon", "library", "vault", "chasm", "fortress", "deep"] }
];
