// Synthetic graves for ?demo=1000 and ?demo=10000: a seeded cast of invented names and causes, in order of time.
import { rng } from "./data.js";

const NAMES = ["Mason", "Juno", "Pell", "Wren", "Tobias", "Marigold", "Kestrel", "Ansel", "Briar", "Corvin", "Delphine", "Eamon", "Fenn", "Greta",
  "Hollis", "Isolde", "Jasper", "Kit", "Linnea", "Merrow", "Nico", "Odette", "Percy", "Quill", "Rhea", "Soren", "Thea", "Ulric", "Vesper", "Wilder",
  "Xan", "Yara", "Zeb", "Alder", "Bram", "Cleo", "Dov", "Elowen", "Finch", "Gale", "Hux", "Ines", "Jory", "Kai", "Lark", "Moss", "Nell", "Orin", "Pike", "Rue"];
const MOBS = ["Zombie", "Skeleton", "Creeper", "Spider", "Cave Spider", "Enderman", "Witch", "Blaze", "Ghast", "Magma Cube", "Zombie Pigman", "Slime", "Silverfish"];
const OTHER = [
  ["lava", "tried to swim in lava", null], ["lava", "went up in flames", null], ["drown", "drowned", null], ["fall", "hit the ground too hard", null],
  ["fall", "fell from a high place", null], ["explosion", "blew up", null], ["other", "starved to death", null], ["other", "was squashed by a falling anvil", null]
];
const VERB = { Skeleton: "was shot by", Creeper: "was blown up by", Ghast: "was fireballed by", Blaze: "was fireballed by" };

export function demoGraves(n, seed = 77) {
  const r = rng(seed * 7919 + n), t0 = Date.parse("2026-01-03T18:00:00Z");
  const graves = [];
  let t = t0;
  for (let i = 0; i < n; i++) {
    t += (2 + r() * 14) * 3600 * 1000;
    const player = NAMES[Math.floor(r() * NAMES.length)] + (r() < 0.3 ? String(1 + Math.floor(r() * 9)) : "");
    const k = r(); let cause, message, killer = null;
    if (k < 0.62) { killer = MOBS[Math.floor(r() * MOBS.length)]; cause = "mob"; message = `${player} ${VERB[killer] || "was slain by"} ${killer}`; }
    else { const o = OTHER[Math.floor(r() * OTHER.length)]; cause = o[0]; message = `${player} ${o[1]}`; }
    graves.push({
      id: "x" + String(i).padStart(5, "0"), player, uuid: null, time: new Date(t).toISOString().replace(/\.\d+Z$/, "Z"), message, killer, cause,
      dimension: r() < 0.8 ? "Overworld" : r() < 0.6 ? "The Nether" : "The End", pos: [Math.floor(r() * 4000 - 2000), 20 + Math.floor(r() * 60), Math.floor(r() * 4000 - 2000)]
    });
  }
  return { updated: new Date(t).toISOString(), demo: true, graves };
}
