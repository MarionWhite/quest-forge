// Data and rules for the Wall of Graves: the feed, the names, the epitaphs, the models and poses.
// No DOM here, so the page and the tests can share it.

export const CAUSE_LABEL = {
  mob: "Killed by a mob", player: "Killed by another player", explosion: "Blown up",
  lava: "Lava", drown: "Drowned", fall: "A fall", other: "Something else"
};
export const CAUSE_NOUN = {
  mob: "Unnamed mob", player: "Another player", explosion: "Explosions", lava: "Lava",
  drown: "Drowning", fall: "Falling", other: "Everything else"
};

export function hash(str) {
  let h = 2166136261;
  for (const c of String(str)) { h ^= c.charCodeAt(0); h = Math.imul(h, 16777619); }
  return h >>> 0;
}
export function rng(seed) {
  let s = (seed >>> 0) || 1;
  return () => (s = (Math.imul(s, 1664525) + 1013904223) >>> 0) / 4294967296;
}

// Read the feed: { updated, graves: [...] }. Unknown fields are ignored; missing ones are null.
export function normalize(d) {
  const list = Array.isArray(d && d.graves) ? d.graves : [];
  const graves = list
    .filter(g => g && typeof g.player === "string" && typeof g.time === "string")
    .map((g, i) => ({
      id: String(g.id || `g${i}`),
      player: g.player,
      uuid: typeof g.uuid === "string" && g.uuid ? g.uuid : null,
      time: g.time,
      message: String(g.message || `${g.player} died`),
      killer: g.killer || null,
      cause: CAUSE_LABEL[g.cause] ? g.cause : "other",
      dimension: g.dimension || null,
      pos: Array.isArray(g.pos) && g.pos.length === 3 ? g.pos.map(Number) : null,
      level: Number.isFinite(g.level) ? g.level : null
    }))
    .sort((a, b) => a.time.localeCompare(b.time) || a.id.localeCompare(b.id));
  // Per-player counts, and the nth death of that player.
  const seen = new Map(), total = new Map();
  for (const g of graves) total.set(g.player, (total.get(g.player) || 0) + 1);
  for (const g of graves) {
    const n = (seen.get(g.player) || 0) + 1;
    seen.set(g.player, n);
    g.nth = n;
    g.totalFor = total.get(g.player);
  }
  return { updated: d && d.updated || null, graves };
}

// The 1.7.10 death line is the message itself. The killer and cause come from the log parser.
export function killerText(g) {
  return g.killer || "No killer named in the log";
}

// Epitaphs: the mod's own lines (grave.* in en_US.lang), with the pronouns kept neutral,
// plus a few in the site's voice. Chosen by hash of the name, so the same stone always reads the same.
const MOD_EPITAPHS = [
  ["Here rests ", ". May they rest in peace."],
  ["Our Dearest Friend ", " rests here. May they rest in peace."],
  ["People die, but heroes live on. In memorial of ", "."],
  ["Here rests in honored glory ", ". You will always be remembered."],
  ["In your travels, pause a while to remember ", ", who passed away at this spot."],
  ["Please keep a moment of silence for ", ", who died at this very place."],
  ["In memory of ", " who died here."],
  ["Ye frail mortals who gaze upon this sight, forget not the fate of ", ", once mighty, now surrendered to the inescapable grasp of destiny. Requiescat in pace."],
  ["Here lies ", ", a Knight of First Order. Great in life, glorious in death."],
  ["Here lies ", ". They really liked barrels."]
];
const OWN_EPITAPHS = [
  "The log remembers what the ground does not.",
  "Went out with the lantern. The ground kept the rest.",
  "Someone will come back for the gear. Someone always does.",
  "Here, the night is longer than the day.",
  "No stone here was carved in a hurry."
];
export function epitaph(g) {
  const h = hash(g.player + "|" + g.time);
  if (h % 4 === 0) return OWN_EPITAPHS[(h >>> 3) % OWN_EPITAPHS.length];
  const [a, b] = MOD_EPITAPHS[(h >>> 3) % MOD_EPITAPHS.length];
  return a + g.player + b;
}
// The epitaph split around the player's name, so the name can be set in bold. Null when it is not there.
export function epitaphParts(g) {
  const t = epitaph(g);
  const i = t.indexOf(g.player);
  return i < 0 ? null : [t.slice(0, i), t.slice(i + g.player.length)];
}

// Family of stone: the mod's designs (ModelGraveStone, ModelTomb, ModelPillar, ModelWoodenGrave,
// ModelKnight, ModelStoneCross, the angel and the skeleton grave). Unlocks follow the mod's rule of one new
// design every five levels when the feed has a level.
export const FAMILIES = ["slab", "tomb", "pillar", "wood", "knight", "cross", "angel", "skeleton"];
export function familyFor(g) {
  // The FNV hash's low bits are uneven for a small modulus, so mix them before choosing.
  let h = hash(g.player);
  h = Math.imul(h ^ (h >>> 16), 0x45d9f3b) >>> 0;
  h = (h ^ (h >>> 13)) >>> 0;
  const unlocked = g.level == null ? FAMILIES.length : Math.min(FAMILIES.length, 1 + Math.floor(g.level / 5));
  return FAMILIES[h % unlocked];
}

// Ornaments keyed to the cause. Returns a small set of keys, most specific first.
export function ornaments(g) {
  const out = [];
  const m = g.message, k = g.killer || "";
  if (/squashed by a falling anvil/.test(m)) out.push("anvil");
  if (/Weeping Angel/i.test(k) || /Weeping Angel/i.test(m)) out.push("angel");
  if (g.cause === "explosion") out.push("scorch");
  if (/shot by/.test(m)) out.push("arrow");
  if (g.cause === "lava" || /went up in flames|burn|fire/i.test(m)) out.push("lava");
  if (g.cause === "drown") out.push("puddle");
  if (g.cause === "fall") out.push("cracked");
  if (/starved/.test(m)) out.push("bowl");
  if (/^Infernal/i.test(k)) out.push("nametag");
  return out.slice(0, 2);
}

// Pose of the statue, from the cause and place of death.
export function poseFor(g) {
  if (/Weeping Angel/i.test(g.killer || "") || /Weeping Angel/i.test(g.message)) return "angel";
  if (g.cause === "explosion") return "arms";
  if (g.cause === "fall") return "flat";
  if (/went up in flames|burn|fire|walked into fire/i.test(g.message) || g.cause === "lava") return "shield";
  if (g.pos && g.pos[1] < 40 && g.dimension !== "The Nether" && !g.killer) return "pick";
  return "kneel";
}

// Stable tint and weathering seeds for each player.
export function seedFor(g) { return hash(g.player + "|weather"); }

export function sameDay(a, b) { return a.slice(0, 10) === b.slice(0, 10); }
